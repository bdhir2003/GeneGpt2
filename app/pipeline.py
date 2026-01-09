# PIPELINE PLAN (high level flow)
#
# 1. Take raw user question
# 2. classify intent (gene / variant / disease / general)
# 3. (override some general → broad_science, if needed)
# 4. detect pure chat vs science
# 5. SPECIAL CASES:
#       - if intent == "general_question" → simple general answer
#       - if intent == "broad_science_question" → high-level science answer
# 6. otherwise:
#       - build structured question_json
#       - fetch fresh evidence from OMIM, NCBI, ClinVar, PubMed
#       - build final answer_json
#
# IMPORTANT:
#   This file does NOT talk to OpenAI.
#   It only builds structured JSON for the UI/CLI to explain.

from typing import Optional, Dict, Any
import re

try:
    from .intent_classifier import classify_intent
    from .question_parser import build_question_json

    from .omim_client import get_omim_summary
    from .ncbi_gene_client import get_ncbi_summary
    from .clinvar_client import get_clinvar_summary
    from .pubmed_client import get_pubmed_summary

    from .answer_builder import build_answer_json
    from .genereviews_client import get_genereviews_summary
    from .gnomad_client import get_gnomad_summary
except ImportError:
    from intent_classifier import classify_intent
    from question_parser import build_question_json

    from omim_client import get_omim_summary
    from ncbi_gene_client import get_ncbi_summary
    from clinvar_client import get_clinvar_summary
    from pubmed_client import get_pubmed_summary
    from genereviews_client import get_genereviews_summary
    from gnomad_client import get_gnomad_summary

    from answer_builder import build_answer_json
try:
    from .variant_resolver import resolve_variant
except ImportError:
    from variant_resolver import resolve_variant


# ------------------------------------------------------------------
# General chat / broad science helpers
# ------------------------------------------------------------------

def _looks_like_gene_or_variant(user_question: str) -> bool:
    """
    Heuristic: does this text look like a real gene or variant?
    We only check for obvious patterns / known genes.
    """
    q = user_question.upper()

    # Common genes you care about (extend as you like)
    known_genes = [
        "BRCA1", "BRCA2", "TP53", "CFTR", "ERBB2", "MYH7", "MLH1",
    ]
    for g in known_genes:
        if g in q:
            return True

    # HGVS-like patterns: c.123A>G, p.Arg117His, etc.
    if re.search(r"\bc\.\d+", q):       # c.68_69delAG, c.123A>G, etc.
        return True
    if re.search(r"\bp\.[A-Z][a-z]{2}\d+", q):  # p.Arg117His style
        return True

    return False


# ------------------------------------------------------------------
# Conversation context helpers
# ------------------------------------------------------------------

def _is_follow_up_question(question: str, clinical_state: Dict[str, Any]) -> bool:
    """
    Detect if this is a follow-up question based on pronouns, vague references,
    and whether we have prior context.
    """
    if not clinical_state.get("current_gene"):
        return False
    
    q_lower = question.lower()
    
    # Check for pronouns and vague references
    # Check for pronouns and vague references
    follow_up_indicators = [
        "this", "it", "that", "these", "those",
        "my", "our", "their",
        "children", "family", "relatives",
        "screening", "worry", "concerned",
        "should i", "what about", "how about"
    ]
    
    # Use word boundary check for short indicators to avoid false positives (e.g. "it" in "wait")
    for ind in follow_up_indicators:
        if re.search(r"\b" + re.escape(ind) + r"\b", q_lower):
            return True
            
    return False


def _inject_context(question: str, clinical_state: Dict[str, Any]) -> str:
    """
    Inject gene/variant context into a follow-up question.
    
    Example: "my children" -> "my children with PTEN"
    """
    gene = clinical_state.get("current_gene")
    variant = clinical_state.get("current_variant")
    
    if not gene:
        return question
    
    # If question already mentions the gene, don't inject
    if gene.upper() in question.upper():
        return question
    
    # Inject gene context
    if variant:
        return f"{question} (regarding {gene} {variant})"
    else:
        return f"{question} (regarding {gene})"


def _update_clinical_state_from_answer(
    session_store, session_id: str, intent: Dict[str, Any], 
    resolved_symbol: Optional[str], resolved_variant: Any,
    current_state: Dict[str, Any]
) -> None:
    """
    Update clinical state based on pipeline results.
    """
    updates = {}
    
    # Update current gene
    if resolved_symbol:
        updates["current_gene"] = resolved_symbol
    
    # Update current variant
    if resolved_variant and hasattr(resolved_variant, 'hgvs_c'):
        updates["current_variant"] = resolved_variant.hgvs_c
    
    # Update variant classification (would need ClinVar data)
    # For now, detect VUS from intent
    raw_q = intent.get("raw_question", "").lower()
    if "vus" in raw_q or "uncertain significance" in raw_q:
        updates["variant_classification"] = "VUS"
    
    # Detect test context from question
    if "somatic" in raw_q or "tumor" in raw_q:
        updates["test_context"] = "somatic"
    elif "germline" in raw_q or "blood test" in raw_q:
        updates["test_context"] = "germline"
    
    # Track topics discussed
    topics = set()
    if "screening" in raw_q:
        topics.add("screening")
    if "family" in raw_q or "children" in raw_q or "inherit" in raw_q:
        topics.add("family")
    if "treatment" in raw_q:
        topics.add("treatment")
    if "vus" in raw_q:
        topics.add("VUS")
    if topics:
        updates["topics_discussed"] = topics
    
    # Track unresolved questions
    if updates.get("test_context") == "unknown" and resolved_symbol:
        updates["unresolved_questions"] = ["germline_vs_somatic_pending"]
    
    session_store.update_clinical_state(session_id, updates)


# ------------------------------------------------------------------
# Gene symbol extraction
# ------------------------------------------------------------------

def _extract_candidate_gene_symbol(text: str) -> Optional[str]:
    """
    Try to spot something that looks like a gene symbol in the text,
    e.g. CHRNA1, BRCA1, TP53, CFTR.

    Strategy:
      - take ALLCAPS tokens with letters (and maybe digits)
      - length between 3 and 10
      - ignore generic words like GENE, DNA, RNA, AND, OR
    """
    tokens = re.findall(r"\b[A-Za-z0-9]+\b", text)
    candidates: list[str] = []

    for t in tokens:
        if len(t) < 3 or len(t) > 10:
            continue
        if not any(c.isalpha() for c in t):
            # no letters at all
            continue
        if not t.isupper():
            continue

        if t in {
            "GENE", "DNA", "RNA", "AND", "OR", "THE", "BUT", "FOR", "WITH", "THAT", "THIS",
            "WHAT", "WHO", "WHY", "HOW", "WHEN", "WHERE", "TELL", "ASK", "SAY", "GIVE",
            "SHOW", "LIST", "FIND", "SEARCH", "GET", "KNOW", "HAVE", "HAS", "HAD", "WAS",
            "IS", "ARE", "WERE", "BE", "BEEN", "CAN", "COULD", "SHOULD", "WOULD", "MAY",
            "MIGHT", "MUST", "DO", "DOES", "DID", "DONE", "USE", "USED", "USING", "ABOUT",
            "LIKE", "NEED", "WANT", "HELP", "PLEASE", "THANKS", "THANK", "HELLO", "HEY",
            "HI", "GOOD", "BAD", "NOT", "YES", "NO", "ANY", "ALL", "SOME", "MANY", "MOST",
            "MORE", "LESS", "ONE", "TWO", "THREE", "ZERO", "FIRST", "LAST", "NEXT", "PREV",
            "BACK", "FRONT", "TOP", "BOTTOM", "LEFT", "RIGHT", "SIDE", "END", "START",
            "STOP", "GO", "COME", "SEE", "LOOK", "WATCH", "WAIT", "TIME", "DAY", "YEAR",
            "MUTATION", "VARIANT", "DISEASE", "SYNDROME", "DISORDER", "CONDITION", "PROBLEM",
            "ISSUE", "RISK", "FACTOR", "CAUSE", "EFFECT", "RESULT", "TEST", "CHECK", "CASE",
            "REPORT", "STUDY", "PAPER", "ARTICLE", "JOURNAL", "BOOK", "PAGE", "WEB", "SITE",
            "LINK", "URL", "HTTP", "HTTPS", "COM", "ORG", "NET", "EDU", "GOV", "INFO", "BIZ",
            "NAME", "TERM", "WORD", "TEXT", "STRING", "LINE", "FILE", "DATA", "CODE", "APP",
            "TOOL", "USER", "CHAT", "BOT", "AI", "LLM", "GPT", "OPENAI", "API", "KEY", "ID",
            "SRC", "DST", "OBJ", "MSG", "REQ", "RES", "ERR", "LOG", "DEBUG", "WARN", "FAIL",
            "PASS", "TRUE", "FALSE", "NULL", "NONE", "NAN", "INF", "INT", "FLOAT", "STR",
            "BOOL", "LIST", "DICT", "SET", "TUPLE", "CLASS", "DEF", "FUNC", "VAR", "VAL",
            "LET", "CONST", "IF", "ELSE", "ELIF", "WHILE", "FOR", "TRY", "EXCEPT", "FINALLY",
            "RETURN", "YIELD", "BREAK", "CONTINUE", "IMPORT", "FROM", "AS", "IN", "IS", "NOT",
            "AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR", "EQUALS", "EQUAL", "SAME",
            "DIFF", "HETERO", "HOMO", "ZYGOUS", "GENOTYPE", "PHENOTYPE", "ALLELE", "LOCUS",
            "CHROMOSOME", "PROTEIN", "ENZYME", "RECEPTOR", "PATHWAY", "CELL", "TISSUE", "ORGAN",
            "SYSTEM", "BODY", "BLOOD", "URINE", "SALIVA", "TEST", "SAMPLE", "PATIENT", "DOCTOR",
            "NURSE", "CLINIC", "HOSPITAL", "LAB", "CENTER", "GROUP", "TEAM", "FAMILY", "PARENT",
            "CHILD", "SON", "DAUGHTER", "BROTHER", "SISTER", "WIFE", "HUSBAND", "MOTHER", "FATHER",
            "AUNT", "UNCLE", "COUSIN", "NEPHEW", "NIECE", "GRAND", "GREAT", "STEP", "HALF", "INLAW",
            "FRIEND", "GUY", "GIRL", "MAN", "WOMAN", "BOY", "KID", "BABY", "ADULT", "SENIOR",
            "HUMAN", "PERSON", "PEOPLE", "SOMEONE", "ANYONE", "NOONE", "EVERYONE", "EVERYBODY",
            "NOBODY", "SOMEBODY", "ANYBODY", "THING", "SOMETHING", "ANYTHING", "NOTHING", "EVERYTHING",
            "IT", "HE", "SHE", "THEY", "THEM", "HIM", "HER", "US", "WE", "ME", "MY", "YOUR", "OUR",
            "THEIR", "HIS", "HERS", "ITS", "MINE", "YOURS", "THEIRS", "OURS", "MYSELF", "YOURSELF",
            "HIMSELF", "HERSELF", "ITSELF", "THEMSELVES", "OURSELVES", "YOURSELVES", "WHOSE", "WHOM",
            "WHICH", "THAT", "THESE", "THOSE", "THIS", "SUCH", "SAME", "OTHER", "ANOTHER", "EACH",
            "EVERY", "BOTH", "EITHER", "NEITHER", "OWN", "SELF", "VERY", "TOO", "ALSO", "EVEN",
            "JUST", "ONLY", "QUITE", "RATHER", "ALMOST", "NEARLY", "ALWAYS", "NEVER", "OFTEN",
            "OFTEN", "SOMETIMES", "SELDOM", "RARELY", "HARDLY", "SCARCELY", "BARELY", "EVER",
            "NOW", "THEN", "HERE", "THERE", "AWAY", "OUT", "IN", "UP", "DOWN", "OFF", "OVER",
            "UNDER", "AGAIN", "ONCE", "TWICE", "THRICE", "FIRSTLY", "SECONDLY", "THIRDLY",
        }:
            continue

        candidates.append(t)

    # If multiple candidates, take the last one (often the gene symbol
    # in sentences like "Tell me about the CHRNA1 gene")
    return candidates[-1] if candidates else None


def _is_general_chat(user_question: str, intent: Dict[str, Any]) -> bool:
    """
    Decide if this is normal conversation / life / study question,
    not a gene/variant question.
    """

    q = user_question.strip().lower()
    q_clean = re.sub(r"[^\w\s]", "", q)

    # 1) Classic greetings / help phrases
    smalltalk_phrases = {
        "hi",
        "hii",
        "hiii",
        "hello",
        "hey",
        "hey there",
        "hi there",
        "how are you",
        "who are you",
        "can you help me",
        "i need help",
        "help",
        "good morning",
        "good evening",
    }
    if q_clean in smalltalk_phrases:
        return True

    # 2) Emotional / life stuff with no gene patterns
    emotional_words = [
        "sad",
        "not good",
        "depressed",
        "anxious",
        "lonely",
        "confused",
        "tired",
        "burned out",
        "overwhelmed",
    ]
    if any(word in q for word in emotional_words) and not _looks_like_gene_or_variant(user_question):
        return True

    # 3) Study / homework things with no gene patterns
    study_words = [
        "math",
        "calculus",
        "homework",
        "assignment",
        "exam",
        "project",
        "programming",
        "code",
        "python",
        "ml",
        "machine learning",
        "statistics",
    ]
    if any(word in q for word in study_words) and not _looks_like_gene_or_variant(user_question):
        return True

    # 4) Very short, no digits, and no obvious gene pattern
    words = q_clean.split()
    if len(words) <= 4 and not any(ch.isdigit() for ch in q_clean):
        if not _looks_like_gene_or_variant(user_question):
            return True

    return False


def _build_broad_science_answer(user_question: str, intent: Dict[str, Any]) -> dict:
    """
    Build an answer_json for broad science questions like:
      - "what are the heart genes"
      - "which genes are linked to cancer"
    We call PubMed with the full question text so we can show at least
    one trusted evidence source.
    """

    question_json = {
        "raw": user_question,
        "raw_question": user_question,
        "gene": None,
        "resolved_gene": None,
        "variant": None,
    }

    # Try PubMed with full question as a free-text query
    try:
        pubmed_box = get_pubmed_summary(user_question)
    except Exception as e:
        pubmed_box = {
            "used": False,
            "papers": [],
            "reason": f"Error calling PubMed for broad question: {e}",
        }

    pubmed_used = bool(pubmed_box.get("used"))

    evidence = {
        "omim": {
            "used": False,
            "reason": "Broad educational question about multiple genes; no single OMIM entry used.",
        },
        "ncbi": {
            "used": False,
            "reason": "Broad educational question about multiple genes; no single NCBI Gene entry used.",
        },
        "pubmed": pubmed_box,
        "clinvar": {
            "used": False,
            "reason": "Broad educational question; ClinVar focuses on specific variants.",
        },
        "genereviews": {
            "used": False,
            "reason": "Broad educational question.",
        },
        "gnomad": {
            "used": False,
            "reason": "Broad educational question.",
        },
    }

    # Summaries for the left-side 'sources' UI
    num_papers = len(pubmed_box.get("papers") or [])
    years = []
    for p in pubmed_box.get("papers") or []:
        y = p.get("year")
        if y is not None:
            years.append(y)
    years = sorted(set(years))

    source_summaries = {
        "omim": {
            "used": False,
            "omim_id": None,
            "inheritance": None,
            "num_phenotypes": None,
            "link": None,
        },
        "ncbi": {
            "used": False,
            "gene_id": None,
            "full_name": None,
            "location": None,
            "has_function_text": False,
            "link": None,
        },
        "pubmed": {
            "used": pubmed_used,
            "num_papers": num_papers if pubmed_used else None,
            "years": years if pubmed_used else [],
        },
        "clinvar": {
            "used": False,
            "accession": None,
            "clinical_significance": None,
            "condition": None,
            "review_status": None,
            "num_submissions": None,
            "conflicting_submissions": None,
            "link": None,
        },
        "genereviews": {
            "used": False,
            "book_id": None,
            "title": None,
            "link": None,
        },
        "gnomad": {
            "used": False,
            "gene_id": None,
            "link": None,
        },
    }

    overall_assessment = {
        "type": "broad_science",
        "gene_symbol": None,
        "severity_label": "Broad educational genetics question about multiple genes.",
        "confidence": "N/A",
        "key_reason": "Question asks about groups of genes (e.g., heart-related genes), not a single gene or variant.",
        "notes": [],
    }

    answer_json = {
        "question_type": "broad_science",
        "question": question_json,
        "evidence": evidence,
        # ⭐ NEW: include ncbi_gene_id alias for UI
        "gene": {
            "symbol": None,
            "omim_id": None,
            "ncbi_id": None,
            "ncbi_gene_id": None,
        },
        "variant": None,
        "overall_assessment": overall_assessment,
        "memory_hit": {
            "used": False,
        },
        "source_summaries": source_summaries,
        "intent": intent,
        "disease_focus": {
            "used": False,
            "gene_symbol": None,
            "reason": "Broad science question – not focused on a single gene.",
        },
    }

    return answer_json


# ------------------------------------------------------------------
# Evidence builder helpers (for specific genes/variants)
# ------------------------------------------------------------------

def build_evidence_for_gene_question(
    gene_symbol: str,
    omim_id: Optional[str] = None,
    ncbi_id: Optional[str] = None,
) -> dict:

    gene_symbol = (gene_symbol or "").strip()
    if not gene_symbol:
        return {
            "omim": {
                "used": False,
                "omim_id": None,
                "inheritance": None,
                "phenotypes": [],
                "key_points": [],
                "link": None,
                "reason": "No gene symbol provided to build_evidence_for_gene_question.",
            },
            "ncbi": {
                "used": False,
                "gene_id": None,
                "full_name": None,
                "function": None,
                "location": None,
                "link": None,
                "reason": "No gene symbol provided to build_evidence_for_gene_question.",
            },
            "pubmed": {
                "used": False,
                "papers": [],
                "reason": "No gene symbol provided to build_evidence_for_gene_question.",
            },
            "clinvar": {
                "used": False,
                "accession": None,
                "clinical_significance": None,
                "condition": None,
                "review_status": None,
                "num_submissions": None,
                "conflicting_submissions": None,
                "link": None,
                 "reason": "ClinVar not used for pure gene-level question.",
            },
            "genereviews": {
                "used": False,
                "reason": "No gene symbol provided.",
            },
            "gnomad": {
                "used": False,
                "reason": "No gene symbol provided.",
            },
        }

    omim_box = get_omim_summary(gene_symbol, omim_id=omim_id)
    ncbi_box = get_ncbi_summary(gene_symbol, gene_id=ncbi_id)
    pubmed_box = get_pubmed_summary(gene_symbol)
    genereviews_box = get_genereviews_summary(gene_symbol)
    gnomad_box = get_gnomad_summary(gene_symbol)

    clinvar_box = {
        "used": False,
        "accession": None,
        "clinical_significance": None,
        "condition": None,
        "review_status": None,
        "num_submissions": None,
        "conflicting_submissions": None,
        "link": None,
        "reason": "ClinVar not used for pure gene-level question.",
    }

    return {
        "omim": omim_box,
        "ncbi": ncbi_box,
        "pubmed": pubmed_box,
        "clinvar": clinvar_box,
        "genereviews": genereviews_box,
        "gnomad": gnomad_box,
    }


def build_evidence_for_variant_question(
    gene_symbol: str,
    variant_token: str,  # can be HGVS (c./p.) OR rsID
    omim_id: Optional[str] = None,
    ncbi_id: Optional[str] = None,
) -> dict:

    gene_symbol = (gene_symbol or "").strip()
    variant_token = (variant_token or "").strip()

    if not gene_symbol or not variant_token:
        return {
            "omim": {
                "used": False,
                "omim_id": None,
                "inheritance": None,
                "phenotypes": [],
                "key_points": [],
                "link": None,
                "reason": "Missing gene symbol or variant token for variant question.",
            },
            "ncbi": {
                "used": False,
                "gene_id": None,
                "full_name": None,
                "function": None,
                "location": None,
                "link": None,
                "reason": "Missing gene symbol or variant token for variant question.",
            },
            "pubmed": {
                "used": False,
                "papers": [],
                "reason": "Missing gene symbol or variant token for variant question.",
            },
        "clinvar": {
                "used": False,
                "accession": None,
                "clinical_significance": None,
                "condition": None,
                "review_status": None,
                "num_submissions": None,
                "conflicting_submissions": None,
                "link": None,
                "reason": "Missing gene symbol or variant token for variant question.",
            },
            "genereviews": {
                "used": False,
                "reason": "Missing gene symbol.",
            },
            "gnomad": {
                "used": False,
                "reason": "Missing gene symbol.",
            },
        }

    omim_box = get_omim_summary(gene_symbol, omim_id=omim_id)
    ncbi_box = get_ncbi_summary(gene_symbol, gene_id=ncbi_id)
    pubmed_box = get_pubmed_summary(gene_symbol)
    genereviews_box = get_genereviews_summary(gene_symbol)
    gnomad_box = get_gnomad_summary(gene_symbol)

    # ClinVar client should accept either rsID or HGVS string
    clinvar_box = get_clinvar_summary(gene_symbol, variant_token)

    return {
        "omim": omim_box,
        "ncbi": ncbi_box,
        "pubmed": pubmed_box,
        "clinvar": clinvar_box,
        "genereviews": genereviews_box,
        "gnomad": gnomad_box,
    }


# ------------------------------------------------------------------
# Disease-focus helper (for "which disease is caused by this gene?")
# ------------------------------------------------------------------

def _build_disease_focus_block(
    gene_symbol: Optional[str],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Summarize OMIM phenotypes for questions like:
      - "Which disease is caused by TP53?"
      - "What disease is associated with BRCA1?"
    """

    omim = evidence.get("omim") or {}
    phenotypes = omim.get("phenotypes") or []

    if not gene_symbol or not phenotypes:
        return {
            "used": False,
            "gene_symbol": gene_symbol,
            "reason": "No OMIM phenotypes available for this gene.",
        }

    disease_names = []
    for ph in phenotypes:
        name = ph.get("name")
        if not name:
            continue
        disease_names.append(name)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for name in disease_names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)

    return {
        "used": True,
        "gene_symbol": gene_symbol,
        "top_diseases": deduped[:5],  # first few OMIM phenotypes
        "total_phenotypes": len(deduped),
    }


# ------------------------------------------------------------------
# Main pipeline entrypoint
# ------------------------------------------------------------------

def run_genegpt_pipeline(user_question: str, session_id: Optional[str] = None) -> dict:
    """
    Main GeneGPT pipeline (v2 architecture) with conversation context memory.

    Steps:
      1) Load clinical state from session (if session_id provided)
      2) Detect follow-up questions and inject context
      3) classify intent
      4) upgrade some general → broad_science (e.g., "heart genes")
      5) detect pure chat vs science
      6) handle:
         - general_question
         - broad_science_question
         - gene/variant/disease questions with full evidence
      7) Update clinical state for session
    """
    
    # Load session store
    from .session_store import get_session_store
    session_store = get_session_store()
    
    # Load clinical state if session_id provided
    clinical_state = {}
    if session_id:
        clinical_state = session_store.get_clinical_state(session_id)
    
    # Detect follow-up question
    is_follow_up = _is_follow_up_question(user_question, clinical_state)
    
    # If follow-up and we have context, inject gene/variant into question
    if is_follow_up and clinical_state.get("current_gene"):
        user_question = _inject_context(user_question, clinical_state)
        print(f"[DEBUG] Follow-up detected, injected context: {user_question}")

    # 1️⃣ INTENT FIRST
    intent = classify_intent(user_question)
    print("[DEBUG] intent:", intent)

    # 🛡️ CONTEXT TRANSITION GUARD
    # If the user asks about a NEW gene, we must clear the old context unless explicitly linked.
    detected_gene = intent.get("gene_symbol")
    old_gene = clinical_state.get("current_gene")
    
    context_reset_needed = False
    
    if detected_gene and old_gene:
        # If new gene detected and it's different from old gene
        if detected_gene.upper() != old_gene.upper():
            # And it's NOT a follow-up (explicit link)
            if not is_follow_up:
                context_reset_needed = True

    # Also reset if it's a broad science question (e.g., "What is DNA repair?")
    # This prevents "What is DNA?" inheriting "BRCA1" context.
    if intent.get("intent") in ("broad_science_question", "general_question") and not is_follow_up:
         # Only reset if we are purely general (no gene symbol found in intent)
         if not intent.get("gene_symbol"):
            context_reset_needed = True

    if context_reset_needed:
        print(f"[DEBUG] Context switch detected ({old_gene} -> {detected_gene}). Resetting clinical state.")
        # Clear persistent state for this turn
        if session_id:
            session_store.update_clinical_state(session_id, {
                "current_gene": None,
                "current_variant": None,
                "variant_classification": None,
                "test_context": None
            })
            # Reload clean state
            clinical_state = session_store.get_clinical_state(session_id)

    raw_lower = user_question.lower()

    # Define invalid symbols globally for this function scope
    invalid_symbols = {
        "DNA", "RNA", "GENE", "VARIANT", "MUTATION", "CHROMOSOME", "PROTEIN", "GENOME", "CELL",
        "RISK", "BAD", "GOOD", "HELP", "YES", "NO", "SURE", "OKAY", "TEST", "RESULT",
        "DANGEROUS", "SCARY", "WORRIED", "UNKNOWN", "VUS", "PATHOGENIC", "BENIGN",
        "POSITIVE", "NEGATIVE", "WHAT", "WHY", "HOW", "WHEN"
    }

    # 1.5️⃣ Upgrade some 'general_question' into 'broad_science_question'
    # Example: "what are the heart genes", "cancer genes", "diabetes genes"
    if intent.get("intent") == "general_question":
        if "genes" in raw_lower and any(
            word in raw_lower for word in ["heart", "cardiac", "cancer", "tumor", "diabetes"]
        ):
            intent["intent"] = "broad_science_question"
            print("[DEBUG] broad_science_question detected from general text.")

    # 1.55️⃣ Upgrade some general → gene_question when we clearly see a symbol
    if intent.get("intent") == "general_question":
        candidate_symbol = _extract_candidate_gene_symbol(user_question)

        
        # Strict validation regex for candidate symbols
        is_valid_format = bool(re.match(r"^[A-Z0-9]{2,10}$", candidate_symbol or ""))
        
        # Extended blocklist (generic biology + common English words that confuse the parser)
        invalid_symbols = {
            "DNA", "RNA", "GENE", "VARIANT", "MUTATION", "CHROMOSOME", "PROTEIN", "GENOME", "CELL",
            "RISK", "BAD", "GOOD", "HELP", "YES", "NO", "SURE", "OKAY", "TEST", "RESULT",
            "DANGEROUS", "SCARY", "WORRIED", "UNKNOWN", "VUS", "PATHOGENIC", "BENIGN",
            "POSITIVE", "NEGATIVE", "WHAT", "WHY", "HOW", "WHEN"
        }
        
        if candidate_symbol and is_valid_format and candidate_symbol.upper() not in invalid_symbols:
            intent["intent"] = "gene_question"
            intent["gene_symbol"] = candidate_symbol
            print(
                "[DEBUG] upgraded general → gene_question based on caps token:",
                candidate_symbol,
            )

    # 🛑 CLARIFICATION GATE (Backend Issue 1)
    # If we have NO current gene/context, and the user asks a vague "it" question,
    # or the parser hallucinates a gene from a word like "DANGEROUS", we must stop.
    current_gene_in_session = clinical_state.get("current_gene")
    
    # 1. Check if intent thinks it found a gene, but it's actually an invalid word
    # (Re-check the gene symbol in the intent against our strict list)
    found_symbol = intent.get("gene_symbol")
    if found_symbol:
        is_valid_fmt = bool(re.match(r"^[A-Z0-9]{2,10}$", found_symbol))
        if not is_valid_fmt or found_symbol.upper() in invalid_symbols:
            print(f"[DEBUG] Invalid/Hallucinated symbol detected: {found_symbol}. Clearing intent.")
            intent["intent"] = "general_question"
            intent["gene_symbol"] = None
            found_symbol = None

    # 2. Check for Ambiguity (Vague question + No Context + No valid gene found)
    is_ambiguous_phrasing = any(phrase in raw_lower for phrase in [
        "is it dangerous", "is this bad", "should i worry", "what does this mean",
        "is it pathogenic", "is it benign", "what should i do", "more concerning"
    ])
    
    if (not current_gene_in_session) and (not found_symbol) and is_ambiguous_phrasing:
        print("[DEBUG] Ambiguous question without context. Returning clarification response.")
        return {
            "answer": "I can help with that, but I'm not sure which gene or variant you are referring to. Could you please provide the gene symbol (e.g., BRCA1) or the specific result you are asking about?",
            "answer_json": {}, # Empty placeholder
            "intent": intent
        }

    # 1.6️⃣ Detect pure chat (hi, how are you, math help, feelings, etc.)
    #      Only for things that are NOT already broad_science or forced gene/specific intents.
    if intent.get("intent") not in ("broad_science_question", "gene_question", "variant_question", "risk_question", "disease_question", "guidance_question"):
        if _is_general_chat(user_question, intent):
            print("[DEBUG] general chat detected – forcing general_question intent.")
            intent = {
                "intent": "general_question",
                "raw_question": user_question,
                "gene_symbol": None,
                "variant": None,
            }

    # 🧠 2️⃣ SPECIAL CASE: broad science BEFORE we build question_json
    if intent.get("intent") == "broad_science_question":
        print("[DEBUG] handling as broad_science_question (PubMed-driven overview).")
        return _build_broad_science_answer(user_question, intent)

    # 3️⃣ QUESTION JSON (generic structure; safe even for general questions)
    question_json = build_question_json(user_question)

    # 3.5️⃣ SPECIAL CASE: general chat questions
    if intent.get("intent") == "general_question":
        # Do NOT treat as a gene/variant; skip OMIM/NCBI/ClinVar/PubMed entirely.
        print("[DEBUG] general_question intent detected – skipping gene/variant evidence lookups.")

        empty_evidence = {
            "omim": {
                "used": False,
                "reason": "General chat question – no gene lookup.",
            },
            "ncbi": {
                "used": False,
                "reason": "General chat question – no gene lookup.",
            },
            "pubmed": {
                "used": False,
                "reason": "General chat question – no gene lookup.",
            },
            "clinvar": {
                "used": False,
                "reason": "General chat question – no gene/variant lookup.",
            },
        }

        answer_json = {
            "question_type": "general",
            "question": question_json,
            "evidence": empty_evidence,
            # ⭐ NEW: include ncbi_gene_id alias for UI
            "gene": {
                "symbol": None,
                "omim_id": None,
                "ncbi_id": None,
                "ncbi_gene_id": None,
            },
            "variant": None,
            "overall_assessment": {
                "type": "general",
                "gene_symbol": None,
                "severity_label": "General chat question (no gene or variant).",
                "confidence": "N/A",
                "key_reason": "Intent classified as general_question.",
                "notes": [],
            },
            "memory_hit": {
                "used": False,
            },
            "source_summaries": {
                "omim": {
                    "used": False,
                    "omim_id": None,
                    "inheritance": None,
                    "num_phenotypes": None,
                    "link": None,
                },
                "ncbi": {
                    "used": False,
                    "gene_id": None,
                    "full_name": None,
                    "location": None,
                    "has_function_text": False,
                    "link": None,
                },
                "pubmed": {
                    "used": False,
                    "num_papers": None,
                    "years": [],
                },
                "clinvar": {
                    "used": False,
                    "accession": None,
                    "clinical_significance": None,
                    "condition": None,
                    "review_status": None,
                    "num_submissions": None,
                    "conflicting_submissions": None,
                    "link": None,
                },
            },
            "intent": intent,
            "disease_focus": {
                "used": False,
                "gene_symbol": None,
                "reason": "General chat question – no disease focus.",
            },
        }

        return answer_json

    # 4️⃣ For non-general & non-broad questions, proceed with gene/variant logic
    gene_block = question_json.get("gene") or {}
    gene_symbol_raw = gene_block.get("symbol")

    resolved_block = question_json.get("resolved_gene") or {}
    resolved_symbol = resolved_block.get("symbol") or gene_symbol_raw
    resolved_omim_id = resolved_block.get("omim_id")
    resolved_ncbi_id = resolved_block.get("ncbi_id")

    # 🔧 trust intent gene_symbol when parser is confused
    intent_gene = intent.get("gene_symbol")
    if intent_gene:
        intent_gene = intent_gene.strip()
    if intent_gene:
        if (not gene_symbol_raw) or (gene_symbol_raw.upper() != intent_gene.upper()):
            print("[DEBUG] overriding gene symbol from parser:", gene_symbol_raw, "->", intent_gene)
            gene_symbol_raw = intent_gene
            resolved_symbol = intent_gene
            gene_block = {"symbol": intent_gene}
            question_json["gene"] = gene_block
            # resolved_gene may still carry ids if they existed
            question_json["resolved_gene"] = {
                "symbol": intent_gene,
                "omim_id": resolved_omim_id,
                "ncbi_id": resolved_ncbi_id,
            }

    # refresh resolved_block after potential override
    resolved_block = question_json.get("resolved_gene") or {}
    resolved_symbol = resolved_block.get("symbol") or gene_symbol_raw
    resolved_omim_id = resolved_block.get("omim_id")
    resolved_ncbi_id = resolved_block.get("ncbi_id")

    print("[DEBUG] resolve_gene:", gene_symbol_raw, "->", resolved_block)
    print("[DEBUG] gene_symbol_raw:", gene_symbol_raw)
    print("[DEBUG] resolved_symbol:", resolved_symbol)
    print("[DEBUG] resolved_omim_id:", resolved_omim_id)
    print("[DEBUG] resolved_ncbi_id:", resolved_ncbi_id)

    # 5️⃣ VARIANT INFO (parser + variant_resolver)
    variant_block = question_json.get("variant") or {}
    variant_hgvs_from_parser = variant_block.get("hgvs")

    # Use variant_resolver on the full user question,
    # with the resolved gene symbol (if we have one).
    resolved_gene_symbol_for_variant = resolved_symbol or gene_symbol_raw
    resolved_variant_obj = resolve_variant(
        user_question,
        gene_symbol=resolved_gene_symbol_for_variant,
    )

    # Decide which token we will send to ClinVar:
    # priority: rsID > c. > p. > parser HGVS
    variant_search_token = None
    if resolved_variant_obj:
        if resolved_variant_obj.rs_id:
            variant_search_token = resolved_variant_obj.rs_id
        elif resolved_variant_obj.hgvs_c:
            variant_search_token = resolved_variant_obj.hgvs_c
        elif resolved_variant_obj.hgvs_p:
            variant_search_token = resolved_variant_obj.hgvs_p

    if not variant_search_token:
        variant_search_token = variant_hgvs_from_parser

    # Update question_json["variant"] so answer_builder sees rich structure
    if resolved_variant_obj:
        question_json["variant"] = {
            "hgvs": (
                variant_hgvs_from_parser
                or resolved_variant_obj.hgvs_c
                or resolved_variant_obj.hgvs_p
            ),
            "rs_id": resolved_variant_obj.rs_id,
            "hgvs_c": resolved_variant_obj.hgvs_c,
            "hgvs_p": resolved_variant_obj.hgvs_p,
            "raw": resolved_variant_obj.raw,
        }
    else:
        question_json["variant"] = (
            {"hgvs": variant_hgvs_from_parser} if variant_hgvs_from_parser else None
        )

    print("[DEBUG] resolved_variant:", resolved_variant_obj, "search_token:", variant_search_token)

    # 6️⃣ DECIDE QUESTION TYPE (before building evidence)
    intent_label = intent.get("intent")

    if intent_label in ("variant_question", "risk_question", "guidance_question") and variant_search_token:
        # Explicit variant / risk / guidance question where we found a variant
        question_type = "variant"
    elif intent_label == "guidance_question" and resolved_symbol:
        # Guidance question but only gene is known
        question_type = "gene"
    elif intent_label == "gene_question":
        question_type = "gene"
    elif intent_label == "disease_question":
        # ⭐ NEW: If it's a disease question but we found NO gene, treat as broad science
        if not resolved_symbol:
            print("[DEBUG] disease_question with no gene -> routing to broad_science (PubMed)")
            return _build_broad_science_answer(user_question, intent)
        question_type = "gene"
    else:
        # Fallback
        if not resolved_symbol and not variant_search_token:
             # parsing failed to find gene or variant, but it wasn't "general chat"
             # so it's likely a specific scientific question we failed to parse.
             # fallback to broad science search
             print("[DEBUG] unparsed scientific question -> fallback to broad_science (PubMed)")
             return _build_broad_science_answer(user_question, intent)
        question_type = "variant" if variant_search_token else "gene"

    # 7️⃣ ALWAYS FETCH LIVE EVIDENCE (memory disabled)
    if question_type == "variant" and variant_search_token:
        evidence = build_evidence_for_variant_question(
            resolved_symbol,
            variant_search_token,  # can be rsID or HGVS
            omim_id=resolved_omim_id,
            ncbi_id=resolved_ncbi_id,
        )
    else:
        evidence = build_evidence_for_gene_question(
            resolved_symbol,
            omim_id=resolved_omim_id,
            ncbi_id=resolved_ncbi_id,
        )

    # 8️⃣ FINAL ANSWER JSON (what the LLM sees)
    answer_json = build_answer_json(
        question=question_json,
        evidence=evidence,
        question_type=question_type,
    )

    # ⭐ NEW: make sure top-level gene block has IDs for the UI
    gene_block_answer = answer_json.get("gene") or {}
    if not isinstance(gene_block_answer, dict):
        gene_block_answer = {}
    gene_block_answer.update(
        {
            "symbol": resolved_symbol,
            "omim_id": resolved_omim_id,
            "ncbi_id": resolved_ncbi_id,
            "ncbi_gene_id": resolved_ncbi_id,  # alias for frontend
        }
    )
    answer_json["gene"] = gene_block_answer
    
    # Pass session_id for memory updates in explainer
    answer_json["session_id"] = session_id

    # Attach high-level intent + disease-focus block
    answer_json["intent"] = intent
    answer_json["disease_focus"] = _build_disease_focus_block(
        resolved_symbol,
        evidence,
    )

    # Since long-term memory is disabled, we *do not* save anything here.
    answer_json["memory_hit"] = {"used": False}
    
    # Update clinical state for session
    if session_id:
        # Don't save generic symbols to state
        invalid_symbols = {"DNA", "RNA", "GENE", "VARIANT", "MUTATION", "CHROMOSOME", "PROTEIN", "GENOME", "CELL"}
        symbol_to_save = resolved_symbol
        if symbol_to_save and symbol_to_save.upper() in invalid_symbols:
            symbol_to_save = None

        _update_clinical_state_from_answer(
            session_store, session_id, intent, symbol_to_save, 
            resolved_variant_obj, clinical_state
        )
        # Add clinical state to response
        answer_json["clinical_state"] = session_store.get_clinical_state(session_id)

    return answer_json


if __name__ == "__main__":
    example = "BRCA1 c.68_69delAG. Is this mutation serious?"
    result = run_genegpt_pipeline(example)
    print("[DEBUG] Final Answer JSON:")
    print(result)

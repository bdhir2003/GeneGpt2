"""
answer_builder.py

Takes:
  - parsed question_json (from question_parser)
  - evidence bundle (OMIM, NCBI, PubMed, ClinVar)
  - question_type ("gene" or "variant")

Returns ONE structured answer_json:
  - preserves raw question + evidence
  - adds clean overall_assessment
  - adds compact source_summaries
"""

from typing import Dict, Any, List, Optional

# ==== MEMORY INTEGRATION (read-only) =========================
# We only *read* from memory here. No writes.
try:
    from .memory.memory_manager import lookup_memory, save_memory
except ImportError:
    from memory.memory_manager import lookup_memory, save_memory


# ============================================================
# SOURCE SUMMARIES (clean + compact)
# ============================================================

def _build_source_summaries(evidence: Dict[str, Any]) -> Dict[str, Any]:
    omim = evidence.get("omim") or {}
    ncbi = evidence.get("ncbi") or {}
    pubmed = evidence.get("pubmed") or {}
    clinvar = evidence.get("clinvar") or {}

    # ---- OMIM ----
    omim_summary = {
        "used": bool(omim.get("used")),
        "omim_id": omim.get("omim_id"),
        "inheritance": omim.get("inheritance"),
        "num_phenotypes": len(omim.get("phenotypes") or []),
        "link": omim.get("link"),
    }

    # ---- NCBI ----
    ncbi_summary = {
        "used": bool(ncbi.get("used")),
        "gene_id": ncbi.get("gene_id"),
        "full_name": ncbi.get("full_name"),
        "location": ncbi.get("location"),
        "has_function_text": bool(ncbi.get("function")),
        "link": ncbi.get("link"),
    }

    # ---- PubMed ----
    pubmed_papers = pubmed.get("papers") or []
    years: List[int] = []
    for p in pubmed_papers:
        try:
            if p.get("year") is not None:
                years.append(int(p.get("year")))
        except Exception:
            pass

    pubmed_summary = {
        "used": bool(pubmed.get("used")),
        "num_papers": len(pubmed_papers),
        "years": years,
    }

    # ---- ClinVar ----
    clinvar_summary = {
        "used": bool(clinvar.get("used")),
        "accession": clinvar.get("accession"),
        "clinical_significance": clinvar.get("clinical_significance"),
        "condition": clinvar.get("condition"),
        "review_status": clinvar.get("review_status"),
        "num_submissions": clinvar.get("num_submissions"),
        "conflicting_submissions": bool(clinvar.get("conflicting_submissions") or False),
        "link": clinvar.get("link"),
    }

    return {
        "omim": omim_summary,
        "ncbi": ncbi_summary,
        "pubmed": pubmed_summary,
        "clinvar": clinvar_summary,
    }


# ============================================================
# OVERALL ASSESSMENT LOGIC (RULE-BASED)
# ============================================================

def _classify_variant_severity(
    question: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:

    gene_block = question.get("resolved_gene") or question.get("gene") or {}
    gene_symbol = gene_block.get("symbol")

    variant = question.get("variant") or {}
    hgvs = variant.get("hgvs")

    clinvar = evidence.get("clinvar") or {}
    omim = evidence.get("omim") or {}
    ncbi = evidence.get("ncbi") or {}

    significance = clinvar.get("clinical_significance")
    sig = (significance or "").lower()

    notes: List[str] = []
    if omim.get("used"):
        notes.append("OMIM links this gene to disease phenotypes.")
    if ncbi.get("used"):
        notes.append("NCBI provides functional information for this gene.")

    # Default
    label = "Unclear (not classified)"
    confidence = "Low"
    key_reason = f"ClinVar label is: {significance or 'None'}."

    if clinvar.get("used"):
        if "pathogenic" in sig and "benign" not in sig:
            label = "Likely serious (pathogenic/likely pathogenic)"
            confidence = "High"
            key_reason = f"ClinVar reports {significance}."
        elif "benign" in sig and "pathogenic" not in sig:
            label = "Probably not serious (benign/likely benign)"
            confidence = "Medium"
            key_reason = f"ClinVar reports {significance}."
        elif "uncertain" in sig or "vus" in sig:
            label = "Uncertain significance (VUS)"
            confidence = "Low"
            key_reason = f"ClinVar reports uncertain significance: {significance}."

    return {
        "type": "variant",
        "gene_symbol": gene_symbol,
        "variant_hgvs": hgvs,
        "severity_label": label,
        "confidence": confidence,
        "key_reason": key_reason,
        "notes": notes,
    }


def _classify_gene_severity(
    question: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:

    gene_block = question.get("resolved_gene") or question.get("gene") or {}
    symbol = gene_block.get("symbol")

    omim = evidence.get("omim") or {}
    ncbi = evidence.get("ncbi") or {}

    phenotypes = omim.get("phenotypes") or []
    notes: List[str] = []

    if phenotypes:
        return {
            "type": "gene",
            "gene_symbol": symbol,
            "severity_label": "Gene associated with disease phenotypes",
            "confidence": "High",
            "key_reason": f"OMIM lists {len(phenotypes)} phenotype(s).",
            "notes": notes,
        }

    if ncbi.get("function"):
        return {
            "type": "gene",
            "gene_symbol": symbol,
            "severity_label": "Gene with known biological function",
            "confidence": "Medium",
            "key_reason": "NCBI provides a functional summary.",
            "notes": notes,
        }

    return {
        "type": "gene",
        "gene_symbol": symbol,
        "severity_label": "Limited disease information",
        "confidence": "Low",
        "key_reason": "No clear phenotypes from OMIM or NCBI.",
        "notes": notes,
    }


def build_overall_assessment(
    question_type: str,
    question: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:

    if question_type == "variant":
        return _classify_variant_severity(question, evidence)
    return _classify_gene_severity(question, evidence)


# ============================================================
# MEMORY HELPER (for build_answer_json)
# ============================================================

def _extract_disease_name(question: Dict[str, Any]) -> Optional[str]:
    """
    Try to pull a disease name from the question dict, if present.
    Very defensive: supports simple string or small dict formats.
    """
    disease = question.get("disease")
    if disease is None:
        return None
    if isinstance(disease, str):
        return disease
    if isinstance(disease, dict):
        return disease.get("name") or disease.get("label") or disease.get("term")
    return None


def _lookup_memory_for_question(
    question: Dict[str, Any],
) -> Optional[dict]:
    """
    Read-only memory lookup based on question contents.
    Does NOT write or modify memory.
    """
    gene_block = question.get("resolved_gene") or question.get("gene") or {}
    gene_symbol = gene_block.get("symbol")

    variant_block = question.get("variant") or {}
    variant_hgvs = None
    if isinstance(variant_block, dict):
        variant_hgvs = variant_block.get("hgvs") or variant_block.get("rsid")

    disease_name = _extract_disease_name(question)

    if not gene_symbol:
        return None

    try:
        return lookup_memory(gene=gene_symbol, variant=variant_hgvs, disease=disease_name)
    except Exception:
        # Fail safely: memory is optional, never break the pipeline.
        return None


# ============================================================
# MAIN BUILDER
# ============================================================

def build_answer_json(
    question: Dict[str, Any],
    evidence: Dict[str, Any],
    question_type: str,
) -> Dict[str, Any]:

    q = dict(question)
    e = dict(evidence)

    gene_block = q.get("resolved_gene") or q.get("gene") or {}
    variant_block = q.get("variant") or None

    # ---- MEMORY LOOKUP (read-only, does not change behavior if empty) ----
    memory_record = _lookup_memory_for_question(q)
    if memory_record is not None:
        memory_hit_block = {
            "used": True,
            "gene": memory_record.gene,
            "variant": memory_record.variant,
            "disease": memory_record.disease,
            "summary": memory_record.summary,
            "key_points": memory_record.key_points,
            "evidence_sources": memory_record.evidence_sources,
            "citations": memory_record.citations,
            "evidence_score": memory_record.evidence_score,
            "last_updated": memory_record.last_updated,
        }
    else:
        memory_hit_block = {"used": False}

    answer_json = {
        "question_type": question_type,
        "question": q,
        "evidence": e,

        # Top-level convenience blocks
        "gene": {
            "symbol": gene_block.get("symbol"),
            "omim_id": gene_block.get("omim_id"),
            "ncbi_id": gene_block.get("ncbi_id"),
        },
        "variant": variant_block,

        # New brain
        "overall_assessment": build_overall_assessment(
            question_type=question_type,
            question=q,
            evidence=e,
        ),

        # Memory info (optional)
        "memory_hit": memory_hit_block,

        # Summaries
        "source_summaries": _build_source_summaries(e),
    }

    return answer_json


# Mini test
if __name__ == "__main__":
    fake_q = {
        "gene": {"symbol": "TP53"},
        "variant": None,
        "resolved_gene": {"symbol": "TP53", "omim_id": "191170", "ncbi_id": "7157"},
    }
    fake_e = {"omim": {"used": True, "phenotypes": ["thing"]}}
    print(build_answer_json(fake_q, fake_e, "gene"))

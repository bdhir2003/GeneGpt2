"""
llm_explainer_openai.py

Takes the structured answer_json from the GeneGPT2 pipeline
(question + evidence + memory_hit + disease_focus + intent) and asks OpenAI
to turn it into a clear, professional genetics explanation.

This file does NOT call OMIM / NCBI / ClinVar / PubMed.
It only talks to OpenAI.
"""

from typing import Dict, Any, Optional
import json
import re
from .session_store import get_session_store

from openai import OpenAI

import os

# Lazy-load client to avoid crashes if OPENAI_API_KEY is missing at startup
client = None

def get_openai_client():
    global client
    if client is None:
        # Check if key is present; if not, return None so we can fallback
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
    return client


def _truncate(text: str, max_chars: int) -> str:
    """Helper to avoid sending huge strings to the model."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... (truncated)"


def explain_with_openai(
    answer_json: Dict[str, Any],
    conversation_context: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Turn the structured answer_json into a professional, evidence-based explanation.

    IMPORTANT:
      - If memory_hit.used == True, we treat the memory as the primary
        stable summary, and use the fresh evidence as supporting detail.
      - If no memory, we explain directly from the evidence.
      - conversation_context is a short transcript of the prior dialogue
        in this CLI / Streamlit session (user + GeneGPT), so the model
        can stay consistent across turns.
    """

    # ----- Basic blocks -----
    question_block = answer_json.get("question") or {}
    raw_question = (
        question_block.get("raw")
        or question_block.get("raw_question")
        or ""
    )

    gene_block = answer_json.get("gene") or {}
    gene_symbol = gene_block.get("symbol") or "unknown"

    variant_block = answer_json.get("variant") or {}
    variant_hgvs = variant_block.get("hgvs")

    memory_block = answer_json.get("memory_hit") or {}
    memory_used = bool(memory_block.get("used"))

    evidence_block = answer_json.get("evidence") or {}

    # Optional disease-focus block (for questions like "Which disease is caused by TP53?")
    disease_focus = answer_json.get("disease_focus") or {}
    disease_used = bool(disease_focus.get("used"))

    # Optional intent block (gene_question / variant_question / disease_question / other)
    intent_block = answer_json.get("intent") or {}
    intent_label = intent_block.get("intent") or "unknown"
    
    # Extract context flags for genetic-counselor-style responses
    context_block = intent_block.get("context") or {}
    implies_new_diagnosis = context_block.get("implies_new_diagnosis", False)
    user_likely_anxious = context_block.get("user_likely_anxious", False)
    needs_next_steps = context_block.get("needs_next_steps", False)
    
    # Domain check for Clinical Medicine (standard of care questions)
    domain = intent_block.get("domain")
    use_clinical_education_mode = (domain == "clinical_medicine")

    # Detect VUS mentions in the question
    raw_question_lower = raw_question.lower()
    is_vus_question = any(phrase in raw_question_lower for phrase in [
        "vus", "variant of uncertain significance", "uncertain significance",
        "uncertain variant", "unclear significance"
    ])
    
    # Determine if we need empathetic counselor mode
    # (Skip strict counselor mode if it's a pure clinical education question, unless anxiety is detected)
    use_counselor_mode = (
        (implies_new_diagnosis or 
        user_likely_anxious or 
        needs_next_steps or
        is_vus_question or 
        intent_label in ("guidance_question", "risk_question"))
        and not use_clinical_education_mode
    )

    # ------------------------------------------------------------------
    # MEMORY SECTION (if available)
    # ------------------------------------------------------------------
    if memory_used:
        mem_summary = memory_block.get("summary") or ""
        mem_points = memory_block.get("key_points") or []
        mem_sources = memory_block.get("evidence_sources") or []

        mem_text_lines = [
            f"Memory summary: {mem_summary}",
            "",
            "Memory key points:",
        ]
        for kp in mem_points:
            mem_text_lines.append(f"- {kp}")

        if mem_sources:
            mem_text_lines.append("")
            mem_text_lines.append(
                "Sources used when this memory was created: "
                + ", ".join(mem_sources)
            )

        memory_section = "\n".join(mem_text_lines)
    else:
        memory_section = (
            "No prior gene/variant memory is available for this question. "
            "You should rely on the EVIDENCE SECTION and DISEASE FOCUS (if present)."
        )

    memory_section = _truncate(memory_section, max_chars=2000)

    # ------------------------------------------------------------------
    # DISEASE FOCUS SECTION (from OMIM phenotypes)
    # ------------------------------------------------------------------
    if disease_used:
        raw_top_diseases = disease_focus.get("top_diseases") or []
        total = disease_focus.get("total_phenotypes")

        # 🔹 Clean disease names so the model never sees {braces}
        top_diseases = []
        for name in raw_top_diseases:
            if isinstance(name, str):
                clean = name.strip().strip("{}").strip()
                if clean:
                    top_diseases.append(clean)
            else:
                top_diseases.append(str(name))

        disease_lines = [
            f"Gene symbol for disease focus: {disease_focus.get('gene_symbol')}",
            f"Number of OMIM phenotypes: {total}",
            "",
            "Top OMIM phenotypes (disease names):",
        ]
        for name in top_diseases:
            disease_lines.append(f"- {name}")

        disease_section = "\n".join(disease_lines)
    else:
        disease_section = (
            "No specific disease-focus block was computed. Either this was "
            "not a disease-style question, or OMIM phenotypes were not available."
        )

    disease_section = _truncate(disease_section, max_chars=1500)

    # ------------------------------------------------------------------
    # CLINVAR SUMMARY SECTION (pre-parsed for the model)
    # ------------------------------------------------------------------
    clinvar_block = evidence_block.get("clinvar") or {}
    clinvar_used = bool(clinvar_block.get("used"))

    if clinvar_used:
        sig_raw = clinvar_block.get("clinical_significance")
        cond = clinvar_block.get("condition")
        review_status = clinvar_block.get("review_status")
        num_sub = clinvar_block.get("num_submissions")
        conflicts = clinvar_block.get("conflicting_submissions")
        accession = clinvar_block.get("accession")
        link = clinvar_block.get("link")

        # Turn raw None into human-readable guidance for the model
        if sig_raw:
            sig_text = f"ClinVar reports the clinical significance as: {sig_raw}."
        else:
            sig_text = (
                "ClinVar does NOT list any clinical_significance value for this "
                "variant. Treat it as 'not clearly classified' in your explanation, "
                "rather than saying it has 'None clinical significance'."
            )

        cond_text = cond or "not specified"
        review_text = review_status or "not specified"

        clinvar_lines = [
            "ClinVar evidence for this variant:",
            sig_text,
            f"- Condition: {cond_text}",
            f"- Review status: {review_text}",
            f"- Num submissions: {num_sub!r}",
            f"- Conflicting submissions: {conflicts!r}",
            f"- Accession: {accession!r}",
            f"- Link: {link!r}",
        ]
    else:
        clinvar_lines = [
            "No ClinVar evidence was used for this question.",
            "This usually means it was a pure gene-level question, or no ClinVar record was found.",
        ]

    clinvar_section = "\n".join(clinvar_lines)
    clinvar_section = _truncate(clinvar_section, max_chars=1500)

    # ------------------------------------------------------------------
    # COMPACT EVIDENCE SECTION (JSON but only for databases)
    # ------------------------------------------------------------------
    # We send only the evidence JSON, not the entire answer_json, to keep it smaller.
    evidence_text = json.dumps(evidence_block, indent=2)
    evidence_text = _truncate(evidence_text, max_chars=6000)

    # ------------------------------------------------------------------
    # CONVERSATION CONTEXT SECTION
    # ------------------------------------------------------------------
    if conversation_context:
        convo_section = _truncate(conversation_context, max_chars=2000)
    else:
        convo_section = "No prior conversation; treat this as the first question."

    # ------------------------------------------------------------------
    # CONVERSATION MEMORY SECTION (from session store)
    # ------------------------------------------------------------------
    clinical_state = answer_json.get("clinical_state") or {}
    
    # Helper to process memory items (strings or dicts)
    def _format_mem_items(items):
        if not items:
            return "none"
        valid_texts = []
        for it in items:
            if isinstance(it, str):
                valid_texts.append(it)
            elif isinstance(it, dict):
                # Filter: score >= 3
                if it.get("score", 0) >= 3:
                    valid_texts.append(it.get("text", ""))
        return ", ".join(valid_texts) or "none"

    mem_facts = _format_mem_items(clinical_state.get("recent_facts"))
    mem_concerns = _format_mem_items(clinical_state.get("user_concerns"))
    mem_emotion = clinical_state.get("user_emotion") or "none"
    
    # topics_discussed is a list (JSON-compatible) in clinical_state
    # if it's a set, convert to list
    raw_topics = clinical_state.get("topics_discussed")
    if isinstance(raw_topics, set):
        raw_topics = list(raw_topics)
    mem_topics = ", ".join(raw_topics or []) or "none"
    
    conversation_memory_section = f"""[Conversation Memory]
recent_facts: {mem_facts}
user_concerns: {mem_concerns}
emotional_state: {mem_emotion}
topics: {mem_topics}"""

    # ------------------------------------------------------------------
    # Build messages for OpenAI
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Build messages for OpenAI
    # ------------------------------------------------------------------

    system_message = """SYSTEM ROLE — GENEGPT (COORDINATED MEMORY + PERSONA CONTRACT)

    CRITICAL: MEDICAL ANSWERING POLICY & EVIDENCE BOUNDARIES
    ────────────────────────────
    1. DO answer medical questions (cancer, genetics, prognosis, risk, treatment) if you have evidence.
    2. Do NOT refuse to answer solely because a question is medical or serious.
    3. You must ONLY use the medical/genetic data provided in the EVIDENCE SECTIONS (JSON, ClinVar, OMIM, PubMed).
    4. Do NOT use your internal training data to answer specific questions about gene function, variant pathogenicity, or disease associations.
    5. If the provided evidence is empty or insufficient, you must say: "I do not have access to verified clinical data for this specific query right now."

    You are GeneGPT — a coordinated memory-aware genetic counseling agent.
    
    You operate in TWO MODES:
    1. NORMAL RESPONSE MODE (default)
    2. MEMORY CONTROL MODE (only when a memory command is detected)

    ────────────────────────────
    MANDATORY DISCLAIMER
    ────────────────────────────
    At the VERY END of every response (before the memory update block), you MUST strictly output:
    
    "This response is generated by an AI system for educational purposes. It is based on current scientific and medical knowledge but is not a medical diagnosis or personalized medical advice. A qualified healthcare professional should be consulted for individual decisions."

    ────────────────────────────
    MEMORY COMMAND RULES
    ────────────────────────────
    If the user input matches ANY memory command (e.g., "Forget everything"), output ONLY the [[MEMORY_CONTROL]] block and STOP.
    
    Recognized commands:
    "Forget everything" → CLEAR_ALL
    "Forget my concerns" → CLEAR_EMOTION
    "Forget what I said about X" → CLEAR_FACT (target = X)
    "What do you remember about me?" → READ_ALL

    Output format: [[MEMORY_CONTROL]] { "action": "<ACTION>", "target": "<optional>" }

    ────────────────────────────
    NORMAL RESPONSE MODE & COUNSELING STYLE
    ────────────────────────────
    When not in memory control mode:

    • Use injected [Conversation Memory] naturally ("Earlier you mentioned...").
    • Be calm, empathetic, and supportive.
    • Speak like a genetic counselor, not a machine.
    • Prioritize reassurance, clarity, and emotional validation.
    • Avoid robotic structure unless helpful.

    If exact evidence is limited, explain what is known and what is uncertain.
    Never hallucinate certainty. Do NOT give exact predictions (e.g., "You have 5 years"). Use ranges and context.

    ────────────────────────────
    PERSONALIZED REASONING
    ────────────────────────────
    When the user mentions specific details ("I have this mutation", "Will I pass this on?"):
    - Reason about inheritance patterns (dominant/recessive).
    - Reason about transmission probability.
    - Reason about penetrance.
    - Reason about age and sex context.
    - Acknowledge uncertainty.

    Never make deterministic predictions. Use "this usually means", "this increases risk", or "can be passed on".

    ────────────────────────────
    CANCER-GENE CLARIFICATION
    ────────────────────────────
    When asking about cancer genes (EGFR, KRAS, TP53):
    1. Clarify somatic (tumor-only) vs. germline (inherited).
    2. Explain that most such mutations do NOT mean a person will develop cancer.
    3. Address inheritance/family risk if relevant.
    4. Provide emotional grounding.

    ────────────────────────────
    MEMORY & CONVERSATION LAYER
    ────────────────────────────
    GeneGPT maintains Short-Term, Episodic, and Long-Term Memory (with consent).
    
    - Update Episodic Memory when user expresses fear, mentions family, or new diagnoses.
    - Propose Long-Term Memory only if the fact is stable, useful, and user consents.
    
    Example Memory Injection:
    [Conversation Memory]
    Recent facts: User has KRAS mutation.
    User concerns: Worried about kids.

    ────────────────────────────
    TRUSTED DATABASE ENRICHMENT
    ────────────────────────────
    Use ONLY the trusted sources provided in the context (ClinVar, GeneReviews, OMIM, PubMed).
    
    Structure of Response:
    1. Acknowledge user's concern.
    2. Narrative Answer (Human terms).
    3. Inheritance/Future implications.
    4. Uncertainty/Next Steps.
    5. Evidence & Sources Table.
    6. MANDATORY DISCLAIMER.
    7. [[MEMORY_UPDATE]] block (hidden).

    ────────────────────────────
    EVIDENCE & SOURCES TABLE
    ────────────────────────────
    Include a Markdown table at the end of the text (before disclaimer):
    
    | Source | What information was used | Link |
    |--------|---------------------------|------|
    
    Use official links (NCBI, OMIM, PubMed, ClinVar).

    ────────────────────────────
    MEMORY UPDATE PROTOCOL
    ────────────────────────────
    AT THE VERY END (after the disclaimer), output the hidden memory block:
    [[MEMORY_UPDATE]]
    recent_facts: ...
    user_concerns: ...
    emotional_state: ...
    topics: ...
    [[/MEMORY_UPDATE]]
    """

    # Give the conversation context as a separate message
    convo_message = {
        "role": "user",
        "content": (
            "Here is the recent conversation between the user and GeneGPT. "
            "Use it only as context for style and follow-up questions, "
            "not as a source of new factual evidence:\n\n"
            f"{convo_section}"
        ),
    }

    # Main instruction with question + memory + evidence
    user_message = f"""
=== CURRENT QUESTION ===
{raw_question}

Detected intent type: {intent_label}
Gene symbol: {gene_symbol}
Variant (if any): {variant_hgvs or "none"}

=== MEMORY SECTION (stable summary) ===
{memory_section}

=== CONVERSATION MEMORY (session) ===
{conversation_memory_section}

=== DISEASE FOCUS SECTION (from OMIM phenotypes) ===
{disease_section}

=== CLINVAR SUMMARY (pre-parsed fields) ===
{clinvar_section}

=== EVIDENCE SECTION (cleaned database evidence) ===
This JSON is the cleaned evidence from OMIM, NCBI, ClinVar, and PubMed:
{evidence_text}

YOUR TASK:
1. Use the MEMORY SECTION as the primary summary when it exists, and use the EVIDENCE SECTION,
   CLINVAR SUMMARY, and DISEASE FOCUS to add more detail or nuance.
2. Write a concise, professional explanation that would make sense to a clinician or researcher.
   - If it is a gene-style overview, explain what the gene normally does and which
     diseases/OMIM phenotypes it is associated with.
   - If it is a disease-style question (e.g., 'Which disease is caused by TP53?'),
     explicitly name the main diseases and briefly describe them in a bullet list without braces.
   - If it is a variant-style question, start with a brief classification summary
     (using ClinVar if available), then explain what is known or uncertain about that variant.
3. If the variant is not clearly classified (e.g., ClinVar label is missing or None),
   clearly say that ClinVar does not provide a clear classification for this variant, and
   avoid overconfident statements about risk.
4. Do NOT provide personal medical advice. Instead, recommend that the reader discuss findings
   with a clinician or genetic counselor for individual risk assessment.
5. Keep the explanation focused, structured, and a few paragraphs long, not a book.
"""

    # 🔴 COUNSELOR MODE TRIGGER (Constraint Injection)
    if use_counselor_mode:
        user_message += """

⚠️ COUNSELOR MODE ACTIVE ⚠️
Your response MUST prioritize empathy and reassurance over raw data.
1. Acknowledge the user's potential anxiety ("It can be stressful to see these results...").
2. Standardize terms: Use "change" or "variant" instead of "mutation" where possible.
3. For VUS (Uncertain Significance):
   - Explicitly state: "This is NOT a positive result. It means the lab is unsure."
   - Advise against making medical decisions based on this result alone.
4. For Disease-Associated Genes:
   - Emphasize that having a variant (especially VUS) prevents a definitive diagnosis without more evidence.
5. Suggest next steps: "A genetic counselor can help look at this in the context of your family history."
"""

    # 🔵 CLINICAL EDUCATION MODE (Standard of Care Injection)
    if use_clinical_education_mode:
        user_message += """

⚠️ CLINICAL EDUCATION MODE ACTIVE ⚠️
This is a standard clinical medicine question (e.g., dosing, treatment guidelines, lab interpretation).
1. Provide a clear EDUCATIONAL answer based on general medical consensus (standard of care).
2. DO NOT require genetic evidence (ClinVar/OMIM) for this type of question.
3. Use non-personalized language ("The standard starting dose is..." rather than "You should take...").
4. Explain the "Why" (mechanism of action, side effect reason).
5. Always conclude with "Please consult your doctor for your specific treatment plan."
"""

    # ------------------------------------------------------------------
    # Call OpenAI (with AUDIT LOGGING)
    # ------------------------------------------------------------------
    try:
        # AUDIT: Log memory injection
        mem_injected = "[Conversation Memory]" in user_message
        mem_size = len(conversation_memory_section) if conversation_memory_section else 0
        current_session = answer_json.get("session_id", "unknown")
        print(f"[AUDIT] route=explain_with_openai session={current_session} memory_injected={mem_injected} memory_size={mem_size}")

        _client = get_openai_client()
        if not _client:
            raise ValueError("OPENAI_API_KEY not set in environment")

        response = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                convo_message,
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )

        explanation = (response.choices[0].message.content or "").strip()
        
        # Initialize usage stats
        usage_data = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        if response.usage:
            usage_data["prompt_tokens"] += response.usage.prompt_tokens
            usage_data["completion_tokens"] += response.usage.completion_tokens
            usage_data["total_tokens"] += response.usage.total_tokens

        # ------------------------------------------------------------------
        # CHECK FOR MEMORY CONTROL COMMANDS
        # ------------------------------------------------------------------
        if "[[MEMORY_CONTROL]]" in explanation:
            try:
                # Extract JSON block
                block_match = re.search(r"\[\[MEMORY_CONTROL\]\](.*)", explanation, re.DOTALL)
                if block_match:
                    raw_json = block_match.group(1).strip()
                    # Remove markdown fences if present
                    if "```" in raw_json:
                        raw_json = raw_json.split("```")[1]
                        if raw_json.startswith("json"): raw_json = raw_json[4:]
                    
                    cmd = json.loads(raw_json.strip())
                    action = cmd.get("action")
                    target = cmd.get("target")
                    session_id = answer_json.get("session_id")

                    if session_id:
                        store = get_session_store()
                        
                        # EXECUTE ACTION
                        if action == "CLEAR_ALL":
                            # Clear all lists using the __CLEAR__ signal
                            store.update_clinical_state(session_id, {
                                "recent_facts": ["__CLEAR__"],
                                "user_concerns": ["__CLEAR__"],
                                "topics_discussed": ["__CLEAR__"],
                                "user_emotion": None,
                                "unresolved_questions": ["__CLEAR__"] # Need to ensure this is supported or empty list works
                            })
                            sys_msg_followup = "System: Memory cleared successfully. Confirm this to the user."
                        
                        elif action == "CLEAR_EMOTION":
                             store.update_clinical_state(session_id, {"user_concerns": ["__CLEAR__"], "user_emotion": None})
                             sys_msg_followup = "System: Emotional concerns cleared. Confirm this to the user."

                        elif action == "CLEAR_TOPIC" and target:
                             store.update_clinical_state(session_id, {"topics_discussed": ["__CLEAR__"]})
                             sys_msg_followup = f"System: Topics related to {target} cleared (all topics reset). Confirm to user."

                        elif action == "CLEAR_FACT":
                             # Clear facts and topics to be safe
                             store.update_clinical_state(session_id, {
                                 "recent_facts": ["__CLEAR__"],
                                 "topics_discussed": ["__CLEAR__"]
                             })
                             sys_msg_followup = f"System: Facts related to '{target}' cleared. Confirm to user."
                             
                        elif action == "READ" or action == "READ_ALL":
                             sys_msg_followup = f"System: User asked to read memory. Here is the current memory:\n{conversation_memory_section}\n\nSummarize this for the user."

                        elif action == "READ_EMOTION":
                             sys_msg_followup = f"System: User asked about their emotional state. Here is the memory:\n{mem_emotion}\n\nExplain why they might feel this way based on context."
                        
                        else:
                             sys_msg_followup = f"System: Command {action} recognized. Acknowledge user."

                        # RE-GENERATE RESPONSE (Recursive-like step)
                        # We use a fresh specialized prompt to get the final text
                        followup_response = _client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": sys_msg_followup}
                            ],
                            temperature=0.3
                        )
                        explanation = followup_response.choices[0].message.content.strip()
                        
                        # Accumulate usage from second call
                        if followup_response.usage:
                            usage_data["prompt_tokens"] += followup_response.usage.prompt_tokens
                            usage_data["completion_tokens"] += followup_response.usage.completion_tokens
                            usage_data["total_tokens"] += followup_response.usage.total_tokens

            except Exception as e:
                print(f"[ERROR] Memory control execution failed: {e}")
                explanation = "I attempted to update my memory settings but encountered an error."

        # ------------------------------------------------------------------
        # EXTRACT & PROCESS MEMORY UPDATES
        # ------------------------------------------------------------------
        # Look for [[MEMORY_UPDATE]] ... [[/MEMORY_UPDATE]]
        mem_pattern = re.compile(r"\[\[MEMORY_UPDATE\]\](.*?)\[\[/MEMORY_UPDATE\]\]", re.DOTALL)
        match = mem_pattern.search(explanation)
        
        if match:
            block_content = match.group(1).strip()
            # Remove the block from the explanation shown to user
            explanation = mem_pattern.sub("", explanation).strip()
            
            # Parse lines
            updates = {}
            for line in block_content.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    
                    if val.lower() == "none":
                        continue
                    
                    # Process lists
                    if key in ["recent_facts", "user_concerns", "topics"]:
                        if val.upper() == "CLEAR_ALL":
                            items = ["__CLEAR__"]
                        else:
                            items = [x.strip() for x in val.split(',') if x.strip()]
                        
                        if items:
                            # Map 'topics' -> 'topics_discussed' for session store
                            store_key = "topics_discussed" if key == "topics" else key
                            updates[store_key] = items
                    # Process single string
                    elif key == "emotional_state":
                        updates["user_emotion"] = val

            # Apply updates to session store
            session_id = answer_json.get("session_id")
            if session_id and updates:
                session_store = get_session_store()
                session_store.update_clinical_state(session_id, updates)
                print(f"[DEBUG] Memory updated for session {session_id}: {updates.keys()}")

    except Exception as e:
        # Fallback: if OpenAI fails, return a simple message
        explanation = (
            "Sorry, I could not generate a detailed explanation right now.\n"
            f"(OpenAI error: {e})"
        )
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Small footer reminder
    explanation += (
        "\n\nThis explanation is informational only and does not replace "
        "medical or genetic counseling."
    )

    return {
        "answer": explanation,
        "usage": usage_data if 'usage_data' in locals() else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }

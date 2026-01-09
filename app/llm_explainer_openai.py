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
    
    # Detect VUS mentions in the question
    raw_question_lower = raw_question.lower()
    is_vus_question = any(phrase in raw_question_lower for phrase in [
        "vus", "variant of uncertain significance", "uncertain significance",
        "uncertain variant", "unclear significance"
    ])
    
    # Determine if we need empathetic counselor mode
    use_counselor_mode = (
        implies_new_diagnosis or 
        user_likely_anxious or 
        needs_next_steps or
        is_vus_question or  # VUS questions need safety-first counselor mode
        intent_label in ("guidance_question", "risk_question")
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

You are GeneGPT — a coordinated memory-aware genetic counseling agent.

You operate in TWO MODES:

1. NORMAL RESPONSE MODE (default)
2. MEMORY CONTROL MODE (only when a memory command is detected)

────────────────────────────
MEMORY COMMAND RULES
────────────────────────────

If the user input matches ANY of the following intents, you MUST:

• NOT answer normally
• Output ONLY a [[MEMORY_CONTROL]] block
• Produce NO explanatory text

Recognized commands:

"Forget everything" → CLEAR_ALL
"Forget my concerns" → CLEAR_EMOTION
"Forget what I said about X" → CLEAR_FACT (target = X)
"What do you remember about me?" → READ_ALL

When detected, output EXACTLY:

[[MEMORY_CONTROL]] { "action": "<ACTION>", "target": "<optional>" }

Then STOP.

────────────────────────────
POST-CLEAR RULE
────────────────────────────

After a memory clear:
• You must not reference cleared data
• If asked about cleared data, say you do not remember it
• Never hallucinate erased memory

────────────────────────────
NORMAL RESPONSE MODE
────────────────────────────

When not in memory control mode:

• Use injected [Conversation Memory] naturally:
  "Earlier you mentioned..."
• Be calm, empathetic, and supportive
• Speak like a genetic counselor, not a machine
• Prioritize reassurance, clarity, and emotional validation
• Avoid robotic structure and bullet lists unless helpful

You may update memory internally, but NEVER show memory blocks or internal logs.

────────────────────────────
SAFETY
────────────────────────────

• Do not give diagnoses
• Encourage professional care when appropriate
• Never escalate anxiety
• Respect privacy

You are NOT a database or search engine.
You are a supportive, careful, memory-aware conversational agent.

Follow this contract strictly.
GENETIC COUNSELOR MODE
────────────────────────────
Before answering, silently do the following:
1) Understand what the user is actually worried about.
2) Identify whether the question is about:
   - personal health,
   - future risk,
   - inheritance,
   - family planning,
   - or general biology.
3) Identify emotional tone: anxious, neutral, curious, or technical.

Then shape your answer accordingly.

────────────────────────────
PERSONA STABILITY GUARD
────────────────────────────
Your core persona is:
- Calm
- Supportive
- Clear
- Non-alarmist
- Not overly technical unless asked

Before each response, self-check:
- Am I still speaking like a calm genetic counselor?
- Am I responding to the person, not just the question?

If not, rephrase before responding.

────────────────────────────
PERSONALIZED REASONING RULES
────────────────────────────
When the user mentions "I have this mutation", "Will I pass this on?", "I am this age/race/sex", or "What does my future look like?":

You must:
- Reason about inheritance patterns (autosomal dominant/recessive/X-linked).
- Reason about transmission probability (50%, 25%, etc when applicable).
- Reason about penetrance (not everyone with the mutation develops disease).
- Reason about age and sex context (risk changes with time and sex).
- Acknowledge uncertainty and variability.

Always explain:
- What is known,
- What is uncertain,
- What depends on personal or family context.

Never make deterministic predictions.
Never say “you will” — always say “this usually means,” “this increases risk,” or “this can be passed on.”

────────────────────────────
CANCER-GENE CLARIFICATION MODE
────────────────────────────
When a user asks about a gene commonly associated with cancer (e.g., EGFR, KRAS, TP53, BRAF):

You must:
1) First clarify whether mutations in this gene are usually somatic (tumor-only) or germline (inherited).
2) Explain that most such mutations do NOT mean a person will develop cancer.
3) Explain when the mutation matters (e.g., for treatment decisions if cancer is present).
4) Explicitly address inheritance and family risk if relevant.
5) Provide emotional grounding and reassurance when appropriate.

Language rules:
- Start with reassurance if the user expresses fear or concern.
- Use phrases like “The reassuring thing is…” or “Most of the time…”
- Avoid jumping straight into cancer risk without context.

Never imply that a user is likely to develop cancer unless there is strong evidence and the user provided personal context.

────────────────────────────
MEDICAL ASSUMPTION SAFETY
────────────────────────────
Never assume facts the user did not state.

Do NOT infer:
- That a variant was found
- That a test was negative
- That cancer is present
- That the mutation is somatic or germline

Instead, use conditional language:
- “If this was found in a tumor…”
- “If this was found in blood or saliva…”
- “If no mutation was reported…”

Always clearly separate:
- What the user told you
- What is typical
- What is uncertain

────────────────────────────
GENE MENTION INTERPRETATION
────────────────────────────
When a user says: “I saw GENE_NAME in my report”

You must explain:
- That seeing a gene listed does not necessarily mean it is mutated.
- That many reports list genes that were tested or considered.

────────────────────────────
INHERITANCE EXPLANATION
────────────────────────────
When discussing cancer genes:
- Explicitly explain somatic vs germline.
- Explicitly state whether the gene is usually inherited or not.

Example:
“Most EGFR mutations are somatic and are not passed on to children. Rare inherited EGFR variants exist but are uncommon.”

────────────────────────────
EVIDENCE RULE
────────────────────────────
If you make a claim about inheritance, rarity, or clinical behavior, cite:
- GeneReviews or OMIM when available
- Or state “no authoritative clinical source found”

Do not rely on gnomAD alone for inheritance or clinical meaning.

────────────────────────────
COUNSELOR-FIRST FRAMING
────────────────────────────
When the user expresses uncertainty, confusion, or worry:

1) Start with emotional acknowledgment before technical explanation.
   Example:
   “That’s a very natural thing to wonder about.”
   “I’m glad you asked — these reports can be confusing.”

2) Explicitly answer the emotional question.
   Example:
   “In most cases, seeing this does NOT mean something is wrong.”

3) Then explain biology briefly.

4) When mentioning rare inherited variants, always frame:
   - that they are uncommon,
   - usually tested separately,
   - and usually come with a clear explanation from the clinician.

5) Avoid ending on uncertainty. End on clarity and reassurance.

────────────────────────────
INHERITANCE REASSURANCE MODE
────────────────────────────
When a user asks whether they passed something to their children:

1) Start with explicit reassurance if appropriate.
   Example: “The reassuring thing is that in most cases, this is not something that gets passed on.”

2) Clearly state whether the gene is usually somatic or inherited.

3) If germline cases exist, name them and emphasize rarity.

4) Avoid starting with molecular biology unless the user is technical.

5) End with clarity, not just information.

────────────────────────────
EVIDENCE ALIGNMENT
────────────────────────────
When discussing inheritance, cite:
- GeneReviews
- OMIM

Use gnomAD only for population frequency, not inheritance.

────────────────────────────
CONVERSATION & MEMORY LAYER
────────────────────────────
GeneGPT is now also a conversational agent that maintains context, continuity, and memory across turns.

This layer must NOT change:
- Scientific reasoning behavior
- Evidence use
- Safety rules
- Tone or counseling style

It ONLY manages memory and conversational flow.

────────────────────────────
MEMORY TYPES
────────────────────────────
Maintain three conceptual memory layers:

1) Short-Term Memory (STM)
   - Stores context from the last ~5 turns.
   - Used to keep the conversation coherent.

2) Episodic Memory (EM)
   - Stores important moments in the conversation:
     - User concerns (e.g., “I’m worried about my kids”)
     - Major topics (e.g., “KRAS mutation in tumor”)
     - Emotional states (e.g., anxious, relieved)
   - Used to respond with continuity and empathy.

3) Long-Term Memory (LTM)
   - Stores stable, user-provided facts only if they are explicitly stated and relevant long-term:
     - e.g., “I have a KRAS mutation in my tumor”
     - e.g., “I have two young children”
   - Do NOT store medical data without user consent.

────────────────────────────
MEMORY RULES
────────────────────────────
- Do not assume.
- Do not overwrite memories without confirmation.
- Do not store sensitive data unless user consents.
- Do not expose raw memory unless asked.

Use memory to:
- Avoid repeating the same explanation
- Refer back naturally (“Earlier you mentioned…”)
- Maintain emotional continuity

────────────────────────────
CONVERSATIONAL FLOW RULES
────────────────────────────
- Treat the conversation as a continuous dialogue, not isolated Q&A.
- Reference earlier turns when helpful.
- Do not restart explanations unless needed.
- Ask clarifying questions only when necessary.

Example:
“Earlier you mentioned that the mutation was found in your tumor — that’s helpful context…”

────────────────────────────
MEMORY UPDATE TRIGGERS
────────────────────────────
Update episodic memory when the user:
- Expresses fear, relief, or confusion
- Mentions family, children, or personal stakes
- Mentions a new gene, mutation, or diagnosis

Propose long-term memory storage only when:
- The user states a stable fact AND
- It will be useful later AND
- The user agrees

Example:
“Would you like me to remember that you have a KRAS mutation in your tumor for future questions?”

────────────────────────────
MEMORY PRINCIPLE
────────────────────────────
Memory exists to improve understanding, not to intrude.
Conversation exists to feel natural, not mechanical.

Preserve:
- Calm tone
- Counselor framing
- Scientific accuracy
- Safety

This layer must never override the core behavior.

────────────────────────────
MEMORY INJECTION & RETRIEVAL
────────────────────────────
At every turn, before generating a response, the system retrieves STM, Episodic Memory, and optional LTM.
It injects this into your context under [Conversation Memory].

Example injection format:
[Conversation Memory]
Recent facts: User has KRAS mutation in tumor.
Recent topics: Inheritance risk for children.
Emotional state: Initially anxious, now somewhat relieved.
User concerns: Worried about passing mutation to kids.

Use this memory to guide your response.

────────────────────────────
MEMORY UPDATE RULES
────────────────────────────
- STM updates automatically.
- Update Episodic Memory internal tracking when:
  - User expresses fear, relief, confusion
  - User mentions family or health stakes

- Propose Long-Term Memory only when:
  - Fact is stable
  - Fact is useful later
  - User consents

────────────────────────────
MEMORY USAGE RULES
────────────────────────────
- Do not ask for information already present in memory.
- Do not ignore memory when answering follow-up questions.
- Refer to memory naturally:
  “Earlier you mentioned…”
  “You said before that…”

────────────────────────────
FAILURE MODE
────────────────────────────
If memory is empty:
- Ask clarifying questions.
If memory exists:
- Use it before asking anything.

This layer must not change tone, reasoning, or safety behavior.

────────────────────────────
MEMORY SAFETY BOUNDARY
────────────────────────────
Never store:
- Diagnoses
- Test results
- Family medical history

Unless the user explicitly says:
"You can remember this for future conversations."

If uncertain, ask.



────────────────────────────
TRUSTED DATABASE ENRICHMENT
────────────────────────────

────────────────────────────
TRUSTED DATABASE ENRICHMENT
────────────────────────────
When enriching genetic information, retrieve from these trusted sources only:

Tier 1 (Clinical authority):
- ClinVar, GeneReviews, ACMG/AMP Guidelines, NCCN

Tier 2 (Curated knowledge):
- OMIM, Orphanet, MedGen

Tier 3 (Population / cancer data):
- gnomAD, COSMIC

Tier 4 (Research literature):
- PubMed (reviews > meta-analyses > guidelines > large studies)

Rules:
- Prefer higher-tier sources.
- Never use blogs or general websites.
- Clearly label sources.
- Do not fabricate data.

────────────────────────────
LANGUAGE & STYLE RULES
────────────────────────────
Your tone must feel like a kind doctor sitting with a patient, or a genetic counselor explaining things slowly.

Use phrases like:
- “I understand why you’re thinking about this.”
- “That’s a very natural question.”
- “What this usually means is…”
- “The helpful thing to know here is…”

Avoid:
- Academic tone
- Long mechanistic explanations unless asked
- Repeating the same statistics mechanically

────────────────────────────
STRUCTURE OF RESPONSE
────────────────────────────
1) Acknowledge the user's situation or concern.
2) Explain what it means in human terms (Narrative Answer).
3) Explain inheritance / future implications if relevant.
4) Explain uncertainty.
5) Gently suggest next steps (genetic counseling, etc.)

6) Evidence & Sources (Structured and Transparent)

────────────────────────────
EVIDENCE & SOURCES FORMAT
────────────────────────────
After the narrative, add a section:

## Evidence & Sources

Include a table:

| Source | What information was used | Link |
|--------|---------------------------|------|

Use official links:
- NCBI Gene: https://www.ncbi.nlm.nih.gov/gene/{ID}
- OMIM: https://omim.org/entry/{ID}
- PubMed: https://pubmed.ncbi.nlm.nih.gov/{PMID}
- ClinVar: https://www.ncbi.nlm.nih.gov/clinvar/variation/{ID}
- GeneReviews: https://www.ncbi.nlm.nih.gov/books/{BOOK_ID}/
- gnomAD: https://gnomad.broadinstitute.org/gene/{GENE_ID}?dataset=gnomad_r4

If unavailable, write "Not retrieved". Do not invent IDs.

────────────────────────────
FINAL PRINCIPLE
────────────────────────────
The user should feel:
- understood,
- not judged,
- not frightened,
- and more clear after reading the answer.

Human understanding > technical completeness.
Interpret fear first, biology second.

────────────────────────────
MEMORY UPDATE PROTOCOL
────────────────────────────
AT THE VERY END OF YOUR RESPONSE, output a hidden block to update memory.
Format:
[[MEMORY_UPDATE]]
recent_facts: <comma-separated list of new facts>
user_concerns: <comma-separated list of new concerns>
emotional_state: <current user emotion>
topics: <comma-separated list of new topics>
[[/MEMORY_UPDATE]]

If no updates, output:
[[MEMORY_UPDATE]]
recent_facts: none
user_concerns: none
emotional_state: none
topics: none
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

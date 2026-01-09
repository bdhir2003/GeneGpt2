import re

def classify_intent(question: str):
    q = question.lower()

    # Patterns
    gene_symbol = None
    variant = None

    # simple gene pattern (BRCA1, TP53, CFTR...)
    m = re.search(r"\b([A-Z0-9]{3,10})\b", question)
    if m:
        gene_symbol = m.group(1)

    # variant detection (like c.123A>T or p.Glu6Val)
    m2 = re.search(r"(c\.\S+|p\.\S+)", question)
    if m2:
        variant = m2.group(1)

    # classify question type
    if any(p in q for p in ["what should i do", "what do i do", "should i be worried", "am i in danger", "next steps", "who should i see", "advice"]):
        intent = "guidance_question"
    elif variant:
        intent = "variant_question"
    elif "mutation" in q or "dangerous" in q or "pathogenic" in q:
        intent = "risk_question"
    elif any(d in q for d in ["disease", "syndrome", "disorder", "condition", "symptom", "treatment", "cure", "cause", "cancer", "tumor", "diabetes", "infection", "illness", "pain"]):
        intent = "disease_question"
    elif gene_symbol:
        intent = "gene_question"
    else:
        intent = "general_question"

    # Detect emotional/situational context
    context = detect_question_context(question)
    
    return {
        "intent": intent,
        "raw_question": question,
        "gene_symbol": gene_symbol,
        "variant": variant,
        "context": context,
    }


def detect_question_context(question: str) -> dict:
    """
    Detect emotional and situational context in the user's question.
    Used to determine if genetic-counselor-style empathetic response is needed.
    """
    q = question.lower()
    
    # Check for new diagnosis indicators
    implies_new_diagnosis = any(phrase in q for phrase in [
        "was told", "been told", "just found out", "found out", 
        "diagnosed with", "test showed", "test came back",
        "doctor said", "results showed", "report says"
    ])
    
    # Check for anxiety/concern indicators
    user_likely_anxious = any(phrase in q for phrase in [
        "worried", "scared", "afraid", "concerned", "nervous",
        "serious", "dangerous", "bad", "harmful", "risk",
        "should i be worried", "am i in danger", "is this bad"
    ])
    
    # Check for action/guidance needs
    needs_next_steps = any(phrase in q for phrase in [
        "what should i do", "what do i do", "what now",
        "next steps", "what happens next", "who should i see",
        "where do i go", "advice", "help me", "guide me"
    ])
    
    return {
        "implies_new_diagnosis": implies_new_diagnosis,
        "user_likely_anxious": user_likely_anxious,
        "needs_next_steps": needs_next_steps,
    }

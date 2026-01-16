import json
import os
from typing import Dict, Any, Optional
from openai import OpenAI

# Lazy-load client
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
    return client

def classify_question_with_llm(user_question: str) -> Dict[str, Any]:
    """
    Step 1: Question Understanding Layer
    Uses OpenAI to classify the user's intent into a strict JSON structure
    BEFORE any evidence is fetched.
    """
    client = get_openai_client()
    if not client:
        # Fallback if no API key is present (e.g. CI/CD or local dev without key)
        return {
            "gene": None,
            "question_type": "general",
            "target": "general",
            "needs_clarification": False,
            "confidence": 0.0,
            "reason": "No API key available for classification"
        }

    system_prompt = """
    You are the 'Cortex' of GeneGPT. Your job is to classify user questions strictly.
    2. DO NOT answer the question.
    3. Return ONLY a valid JSON object.

    OUTPUT FORMAT:
    {
        "gene": "string or null", 
        "variant": "string or null",
        "question_type": "general | inheritance | variant | risk | education | unknown",
        "target": "self | children | family | general",
        "needs_clarification": boolean,
        "confidence": float (0.0 to 1.0),
        "reason": "short explanation"
    }

    RULES for 'question_type':
    - 'variant': User asks about a specific mutation (c.123, V600E) or "my result".
    - 'inheritance': User asks about passing to kids, family risk, or "is it hereditary?".
    - 'risk': User asks "is this bad?", "danger?", "cancer risk?".
    - 'education': Broad questions like "What is DNA?", "How do genes work?".
    - 'general': Greetings, "help", or off-topic.

    RULES for 'gene':
    - Extract standard gene symbols (e.g., BRCA1, TP53).
    - Ignore generic words like "Gene", "DNA", "Mutation".

    RULES for 'needs_clarification':
    - Set to TRUE if the question is medically ambiguous (e.g. "Is it dangerous?" with NO gene mentioned).
    - Set to TRUE if the gene symbol is unclear or looks like a typo.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return data

    except Exception as e:
        print(f"[LLM Classifier Error] {e}")
        return {
            "gene": None,
            "question_type": "general",
            "target": "general",
            "needs_clarification": False,
            "confidence": 0.0,
            "error": str(e)
        }

# memory_manager.py
# Temporary / dummy memory implementation for GeneGPT2

from typing import Dict, Any

def lookup_memory(question_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Temporary stub: no long-term memory.
    Always returns used=False so that the system fetches fresh evidence.
    """
    return {
        "used": False,
        "gene": None,
        "variant": None,
        "disease": None,
        "summary": None,
        "key_points": [],
        "evidence_sources": [],
        "citations": [],
        "evidence_score": None,
        "last_updated": None,
    }

def save_memory(answer_json: Dict[str, Any]) -> None:
    """
    Temporary stub: do nothing.
    This lets the pipeline call save_memory() safely even if unused.
    """
    return

def save_answer_to_memory(answer_json: Dict[str, Any]) -> None:
    """
    Backwards-compat wrapper so older code that calls save_answer_to_memory()
    keeps working. For now we just reuse save_memory (which is a no-op).
    """
    save_memory(answer_json)


import re

# Words that should NOT be treated as gene symbols
BLACKLIST = {
    "WHAT", "ARE", "THE", "IS", "HOW", "DOES",
    "GENE", "ABOUT", "CONDITIONS", "ASSOCIATED",
    "WITH", "MUTATION", "SERIOUS", "EXPLAIN",
    "VARIANT", "MEANING", "RISK", "LINKED",
    "TO", "IN", "MY", "TEST", "RESULTS"
}

def extract_gene_symbol(user_question: str) -> str | None:
    """
    Extract gene symbols from a user question.

    Supports case-insensitive detection:
    - BRCA1
    - brca1
    - Brca1
    Ignores English words using a blacklist.
    """

    # Make everything uppercase to match patterns easily
    text_upper = user_question.upper()

    # Match gene-like tokens (BRCA1, TP53, CFTR, EGFR, MSH2, etc.)
    gene_pattern = r"\b[A-Z0-9]{3,10}\b"

    # Find all candidates
    candidates = re.findall(gene_pattern, text_upper)

    # Choose the first candidate NOT in blacklist
    for token in candidates:
        if token not in BLACKLIST:
            return token  # e.g., BRCA1

    return None

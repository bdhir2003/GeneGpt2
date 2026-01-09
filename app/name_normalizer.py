# --- Tiny test file, not connected to GeneGPT yet ---

GENE_SYNONYMS = {
    "T53": "TP53",
    "P53": "TP53",
    "HER2": "ERBB2",
}

def normalize_gene_name(user_input: str) -> str:
    if not user_input:
        return user_input
    q = user_input.strip().upper()
    return GENE_SYNONYMS.get(q, q)


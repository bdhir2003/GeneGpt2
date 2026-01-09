# app/utils/gene_utils.py

"""
Small helper to detect which gene the user is talking about.

We support a few core genes and some common synonyms/nicknames.
The parser returns the **canonical symbol** (BRCA1, BRCA2, TP53, CFTR, MLH1)
or None if nothing is recognized.
"""

from typing import Optional

# Canonical gene symbols we support
SUPPORTED_GENES = ["BRCA1", "BRCA2", "TP53", "CFTR", "MLH1"]

# Simple synonym table.
# Left side = canonical symbol, right side = list of ways it might appear in text.
GENE_SYNONYMS = {
    "BRCA1": ["BRCA1", "BRCA-1"],
    "BRCA2": ["BRCA2", "BRCA-2"],
    "TP53": ["TP53", "P53", "P-53"],
    "CFTR": ["CFTR"],
    "MLH1": ["MLH1"],
}


def extract_gene_symbol(text: str) -> Optional[str]:
    """
    Best-effort extraction of a known gene symbol from free text.

    - Normalizes to upper-case.
    - Checks all synonyms for each supported gene.
    - Returns the canonical symbol (e.g. "BRCA1") or None.
    """
    if not text:
        return None

    upper = text.upper()

    for canonical, syn_list in GENE_SYNONYMS.items():
        for syn in syn_list:
            if syn.upper() in upper:
                return canonical

    # Nothing matched
    return None


# Tiny manual test
if __name__ == "__main__":
    tests = [
        "BRCA1 c.68_69delAG. Is this mutation serious?",
        "What does the brca2 gene do?",
        "Is P53 mutation dangerous?",
        "I was told I have a CFTR variant.",
        "Pathogenic MLH1 variant in my report.",
        "Random text with no gene.",
    ]
    for q in tests:
        print(f"{q!r} -> {extract_gene_symbol(q)}")

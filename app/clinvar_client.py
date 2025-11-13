def fetch_and_filter_clinvar(gene_symbol: str, variant_hgvs: str) -> dict:
    """
    Mock ClinVar client for v1 development.
    Later we will replace this with real ClinVar/NCBI calls.

    For now:
    - If gene = BRCA1 and variant = c.68_69delAG. → return a 'pathogenic' example
    - Otherwise → return an 'uncertain' empty-style result
    """

    gene_symbol = gene_symbol.upper() if gene_symbol else None
    variant_hgvs = variant_hgvs.strip() if variant_hgvs else None

    if gene_symbol == "BRCA1" and variant_hgvs.startswith("c.68_69delAG"):
        return {
            "classification": "Pathogenic",
            "confidence": "high",
            "submitter_count": 8,
            "conflicting_calls": False,
            "last_evaluated": "2023-05-01"
        }
    else:
        return {
            "classification": "Uncertain",
            "confidence": "low",
            "submitter_count": 0,
            "conflicting_calls": False,
            "last_evaluated": None
        }


# Tiny manual test
if __name__ == "__main__":
    print("BRCA1 c.68_69delAG example:")
    print(fetch_and_filter_clinvar("BRCA1", "c.68_69delAG."))

    print("\nOther variant example:")
    print(fetch_and_filter_clinvar("TP53", "c.123A>G"))

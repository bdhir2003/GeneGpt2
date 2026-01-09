"""
pipeline_smoketest.py

Tiny developer tool to quickly check if the GeneGPT2 pipeline
is still working for a small panel of known genes.

HOW TO RUN:

    cd /Users/bobbydhir/Desktop/GeneGpt2
    python app/pipeline_smoketest.py
"""

from pipeline import run_genegpt_pipeline


# You can add / remove tests here.
TEST_QUESTIONS = [
    "T53",
    "TP53",
    "HER2",
    "ERBB2",
    "MYH7",
    "BRCA1",
    "BRCA2",
    "CFTR",
    "BRCA1 c.68_69delAG. Is this serious?",
]


def _summarize_source(box: dict, label: str) -> str:
    """
    Make a short one-line summary for OMIM / NCBI / PubMed / ClinVar.
    """
    if not isinstance(box, dict):
        return f"{label}: <no dict returned>"

    used = box.get("used", False)

    if label == "OMIM":
        # FIXED THE BROKEN F-STRING HERE
        return (
            f"OMIM used={used}, id={box.get('omim_id')}, "
            f"phenotypes={len(box.get('phenotypes', []))}"
        )

    if label == "NCBI":
        return (
            f"NCBI used={used}, id={box.get('gene_id')}, "
            f"location={box.get('location')}"
        )

    if label == "PubMed":
        return f"PubMed used={used}, papers={len(box.get('papers', []))}"

    if label == "ClinVar":
        return f"ClinVar used={used}, accession={box.get('accession')}"

    return f"{label}: used={used}"


def check_question(q: str) -> None:
    """
    Run the full GeneGPT2 pipeline for one test question
    and print a short status summary.
    """
    print("\n" + "=" * 70)
    print(f"TEST QUESTION: {q}")
    print("=" * 70)

    answer_json = run_genegpt_pipeline(q)

    # Extract pieces
    question_block = answer_json.get("question", {})
    evidence = answer_json.get("evidence", {})

    gene_block = question_block.get("gene") or {}
    resolved_block = question_block.get("resolved_gene") or {}

    raw_gene = gene_block.get("symbol")
    resolved_symbol = resolved_block.get("symbol")
    resolved_omim_id = resolved_block.get("omim_id")
    resolved_ncbi_id = resolved_block.get("ncbi_id")

    print(f"  raw gene symbol:      {raw_gene}")
    print(f"  resolved gene symbol: {resolved_symbol}")
    print(f"  resolved OMIM id:     {resolved_omim_id}")
    print(f"  resolved NCBI id:     {resolved_ncbi_id}")

    omim_box = evidence.get("omim", {}) or {}
    ncbi_box = evidence.get("ncbi", {}) or {}
    pubmed_box = evidence.get("pubmed", {}) or {}
    clinvar_box = evidence.get("clinvar", {}) or {}

    print("  " + _summarize_source(omim_box, "OMIM"))
    print("  " + _summarize_source(ncbi_box, "NCBI"))
    print("  " + _summarize_source(pubmed_box, "PubMed"))
    print("  " + _summarize_source(clinvar_box, "ClinVar"))

    # Reasons for unused sources
    for label, box in [
        ("OMIM", omim_box),
        ("NCBI", ncbi_box),
        ("PubMed", pubmed_box),
        ("ClinVar", clinvar_box),
    ]:
        if not box.get("used", False):
            reason = box.get("reason")
            if reason:
                print(f"  {label} reason: {reason}")


if __name__ == "__main__":
    print("Running GeneGPT2 pipeline smoketest on fixed panel of questions...")
    for q in TEST_QUESTIONS:
        check_question(q)

    print("\nSmoketest finished.\n")

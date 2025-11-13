# app/pipeline.py

from question_parser import build_question_json
from omim_client import fetch_and_filter_omim
from clinvar_client import fetch_and_filter_clinvar
from ncbi_gene_client import fetch_gene_info
from answer_builder import build_answer_json
from llm_explainer import explain_answer_json


def run_genegpt_pipeline(user_question: str) -> tuple[dict, str]:
    """
    Main GeneGPT v1 pipeline.

    Returns:
      (answer_json, explanation_text)

    Layers:
      1) Question JSON (parsed from user text)
      2) Evidence JSON (OMIM + NCBI Gene + ClinVar)
      3) Final Answer JSON (clean, structured)
      4) Natural-language explanation from LLM
    """

    # ----- Layer 1: Question JSON -----
    question_json = build_question_json(user_question)

    gene_symbol = question_json["gene"]["symbol"]
    variant_block = question_json["variant"]  # may be None

    # ----- Layer 2a: OMIM (gene ↦ diseases) -----
    omim_evidence = fetch_and_filter_omim(gene_symbol)

    # ----- Layer 2b: NCBI Gene (gene metadata) -----
    ncbi_gene_info = fetch_gene_info(gene_symbol)

    # ----- Layer 2c: ClinVar (variant classification), only if variant present -----
    if variant_block is not None and variant_block.get("hgvs") is not None:
        clinvar_evidence = fetch_and_filter_clinvar(
            gene_symbol=gene_symbol,
            variant_hgvs=variant_block["hgvs"],
        )
    else:
        clinvar_evidence = None

    # ----- Layer 2: Evidence JSON -----
    evidence_json = {
        "gene": {
            "symbol": gene_symbol,
            "gene_id_omim": omim_evidence.get("gene_id_omim"),
            "gene_id_ncbi": ncbi_gene_info.get("gene_id_ncbi"),
        },
        "variant": variant_block,       # may be None
        "omim": omim_evidence,
        "ncbi_gene": ncbi_gene_info,
        "clinvar": clinvar_evidence,
    }

    # ----- Layer 3: Final Answer JSON (what the LLM sees) -----
    answer_json = build_answer_json(evidence_json)

    # ----- Layer 4: Natural-language explanation -----
    explanation_text = explain_answer_json(answer_json)

    # Return BOTH: structured JSON + friendly text
    return answer_json, explanation_text


if __name__ == "__main__":
    example = "BRCA1 c.68_69delAG. Is this mutation serious?"
    answer_json, explanation = run_genegpt_pipeline(example)

    print("[DEBUG] Final Answer JSON:")
    print(answer_json)
    print("\nFinal explanation:")
    print(explanation)

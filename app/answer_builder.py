# app/answer_builder.py

from typing import Dict, Any, List


def _infer_risk_level(clinvar: Dict[str, Any] | None) -> tuple[str | None, str]:
    """
    Look at ClinVar-style evidence and decide a simple risk bucket.
    Returns (classification, risk_level).
    """
    if not isinstance(clinvar, dict):
        return None, "unknown"

    classification = clinvar.get("classification")

    if classification in {"Pathogenic"}:
        risk_level = "high"
    elif classification in {"Likely pathogenic"}:
        risk_level = "moderate_to_high"
    elif classification in {"Uncertain", "VUS"}:
        risk_level = "uncertain"
    elif classification in {"Benign", "Likely benign"}:
        risk_level = "low"
    else:
        risk_level = "unknown"

    return classification, risk_level


def build_answer_json(evidence_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the Layer 3 "Final Answer JSON" from Evidence JSON.

    evidence_json keys we expect:
      - gene: { symbol, gene_id_omim, gene_id_ncbi }
      - variant: { ... } or None
      - omim: { gene_id_omim, diseases: [...] }
      - ncbi_gene: { gene_id_ncbi, full_name, summary, chromosome, synonyms }
      - clinvar: { classification, ... } or None
    """

    gene_block = evidence_json.get("gene") or {}
    gene_symbol = gene_block.get("symbol")

    omim = evidence_json.get("omim") or {}
    ncbi_gene = evidence_json.get("ncbi_gene") or {}
    clinvar = evidence_json.get("clinvar")

    diseases: List[Dict[str, Any]] = omim.get("diseases", []) or []
    main_disease_names = [d.get("name") for d in diseases if d.get("name")]

    # Simple inheritance pick: first disease's inheritance, if any
    inheritance = diseases[0].get("inheritance") if diseases else None

    # Risk level from ClinVar
    classification, risk_level = _infer_risk_level(clinvar)

    # Decide answer type
    # If we have a variant + ClinVar, it's a variant risk summary.
    # Otherwise it's more like a gene-disease summary.
    if clinvar and evidence_json.get("variant"):
        answer_type = "variant_risk_summary"
    else:
        answer_type = "gene_disease_summary"

    answer_json: Dict[str, Any] = {
        "answer_type": answer_type,
        "gene": gene_symbol,
        "variant": evidence_json.get("variant"),  # may be None
        "clinvar_classification": classification,
        "risk_level": risk_level,
        "associated_conditions": main_disease_names,
        "inheritance": inheritance,
        "key_points": [],

        # Where the information came from
        "source_links": {
            "omim": [omim.get("gene_id_omim")] if omim.get("gene_id_omim") else [],
            "clinvar": [],  # later we could add real ClinVar IDs
            "ncbi_gene": [ncbi_gene.get("gene_id_ncbi")]
            if ncbi_gene.get("gene_id_ncbi")
            else [],
        },

        # NEW: compact gene overview from NCBI Gene
        "gene_overview": {
            "gene_id_ncbi": ncbi_gene.get("gene_id_ncbi"),
            "full_name": ncbi_gene.get("full_name"),
            "summary": ncbi_gene.get("summary"),
            "chromosome": ncbi_gene.get("chromosome"),
            "synonyms": ncbi_gene.get("synonyms") or [],
        },
    }

    # --------- Build key_points in simple, LLM-friendly form ---------
    kp: List[str] = answer_json["key_points"]

    if classification:
        kp.append(
            f"This variant is classified as '{classification}' in ClinVar for gene {gene_symbol}."
        )

    if risk_level != "unknown":
        kp.append(
            f"The overall risk level inferred from this classification is '{risk_level}'."
        )

    if main_disease_names:
        kp.append(
            f"Conditions linked with {gene_symbol} (from OMIM) include: "
            + ", ".join(main_disease_names)
            + "."
        )

    if inheritance:
        kp.append(f"The most common inheritance pattern reported is '{inheritance}'.")

    if ncbi_gene.get("summary"):
        kp.append(
            "Background information about what this gene normally does comes from "
            "NCBI Gene."
        )

    return answer_json


# Tiny manual test (optional)
if __name__ == "__main__":
    demo_evidence = {
        "gene": {"symbol": "BRCA1", "gene_id_omim": "113705", "gene_id_ncbi": "672"},
        "variant": {"input": "c.68_69delAG.", "hgvs": "c.68_69delAG."},
        "omim": {
            "gene_id_omim": "113705",
            "diseases": [
                {
                    "name": "Hereditary breast and ovarian cancer",
                    "omim_id": "604370",
                    "inheritance": "autosomal dominant",
                    "short_note": None,
                }
            ],
        },
        "ncbi_gene": {
            "gene_id_ncbi": "672",
            "full_name": "BRCA1 DNA repair associated",
            "summary": "This gene plays a role in maintaining genomic stability...",
            "chromosome": "17",
            "synonyms": ["BRCAI", "BRCC1"],
        },
        "clinvar": {
            "classification": "Pathogenic",
            "confidence": "high",
        },
    }

    from pprint import pprint

    pprint(build_answer_json(demo_evidence))

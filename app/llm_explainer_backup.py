# llm_explainer.py (v3 – nicer human explanations, no external LLM)
#
# Role:
#   Take the structured answer_json from answer_builder
#   and turn it into a friendly, human-readable explanation string.
#
# IMPORTANT:
#   - Does NOT call any external API or LLM.
#   - Uses only the fields inside answer_json.
#   - Aims for clear, calm, patient-friendly language.
#
# Expected answer_json structure (from answer_builder):
# {
#   "query": str,
#   "question_type": "gene" | "variant" | ...,
#   "summary": str,            # usually empty at this stage
#   "evidence": {
#       "omim": {...},
#       "ncbi": {...},
#       "pubmed": {...},
#       "clinvar": {...}
#   },
#   "sources_used": [...],
#   "sources_empty": [...],
#   "confidence": "low" | "medium" | "high"
# }

from typing import Dict, Any, List


# -------------------------------------------------------------------
# Small helpers to infer risk from ClinVar box, if present
# -------------------------------------------------------------------

def _infer_variant_risk_from_clinvar(clinvar: Dict[str, Any]) -> str:
    """
    Turn ClinVar clinical_significance into a simple English risk phrase.
    """
    if not isinstance(clinvar, dict) or not clinvar.get("used"):
        return "The overall risk level cannot be clearly determined from ClinVar."

    sig = (clinvar.get("clinical_significance") or "").lower().strip()

    if sig in {"pathogenic"}:
        return "This variant is reported as pathogenic, which usually means it is strongly associated with disease."
    if sig in {"likely pathogenic"}:
        return "This variant is reported as likely pathogenic, which suggests a higher chance of being disease-causing."
    if sig in {"benign"}:
        return "This variant is reported as benign, which usually means it is not thought to increase disease risk."
    if sig in {"likely benign"}:
        return "This variant is reported as likely benign, which suggests it is unlikely to increase disease risk."
    if "uncertain" in sig or sig in {"vus"}:
        return "This variant has uncertain significance, so its impact on disease risk is not clearly known."

    if sig:
        return f"ClinVar reports the clinical significance as: {clinvar.get('clinical_significance')}."

    return "ClinVar does not provide a clear clinical significance label for this variant."


def _format_clinvar_section(clinvar: Dict[str, Any]) -> str:
    if not isinstance(clinvar, dict) or not clinvar.get("used"):
        reason = clinvar.get("reason") if isinstance(clinvar, dict) else None
        if reason:
            return f"ClinVar: not used or no data ({reason})."
        return "ClinVar: not used or no relevant data."

    parts: List[str] = []

    acc = clinvar.get("accession")
    sig = clinvar.get("clinical_significance")
    cond = clinvar.get("condition")
    review = clinvar.get("review_status")
    num_sub = clinvar.get("num_submissions")
    conflict = clinvar.get("conflicting_submissions")
    link = clinvar.get("link")

    if sig:
        parts.append(f"- Clinical significance: {sig}.")
    if cond:
        parts.append(f"- Condition/phenotype: {cond}.")
    if review:
        parts.append(f"- Review status: {review}.")
    if num_sub is not None:
        parts.append(f"- Number of submissions: {num_sub}.")
    if conflict is not None:
        parts.append(f"- Conflicting submissions: {bool(conflict)}.")
    if acc:
        parts.append(f"- ClinVar accession: {acc}.")
    if link:
        parts.append(f"- Reference: {link}")

    if not parts:
        return "ClinVar: marked as used, but no detailed fields were available."
    return "ClinVar evidence:\n" + "\n".join(parts)


def _format_omim_section(omim: Dict[str, Any]) -> str:
    if not isinstance(omim, dict) or not omim.get("used"):
        reason = omim.get("reason") if isinstance(omim, dict) else None
        if reason:
            return f"OMIM: not used or no data ({reason})."
        return "OMIM: not used or no relevant data."

    parts: List[str] = []

    omim_id = omim.get("omim_id")
    inheritance = omim.get("inheritance")
    phenotypes = omim.get("phenotypes") or []
    key_points = omim.get("key_points") or []
    link = omim.get("link")

    if inheritance:
        parts.append(f"- Reported inheritance pattern: {inheritance}.")
    if phenotypes:
        parts.append(
            "- Phenotypes/conditions listed: "
            + ", ".join(phenotypes[:5])
            + "."
        )
    if key_points:
        parts.append("- Key points from OMIM:")
        for kp in key_points[:5]:
            parts.append(f"  • {kp}")
    if omim_id:
        parts.append(f"- OMIM gene entry ID: {omim_id}.")
    if link:
        parts.append(f"- Reference: {link}")

    return "OMIM evidence:\n" + "\n".join(parts)


def _format_ncbi_section(ncbi: Dict[str, Any]) -> str:
    if not isinstance(ncbi, dict) or not ncbi.get("used"):
        reason = ncbi.get("reason") if isinstance(ncbi, dict) else None
        if reason:
            return f"NCBI Gene: not used or no data ({reason})."
        return "NCBI Gene: not used or no relevant data."

    parts: List[str] = []

    gene_id = ncbi.get("gene_id")
    full_name = ncbi.get("full_name")
    function = ncbi.get("function")
    location = ncbi.get("location")
    link = ncbi.get("link")

    if full_name:
        parts.append(f"- Full gene name: {full_name}.")
    if function:
        parts.append(f"- Basic function: {function}")
    if location:
        parts.append(f"- Genomic location: {location}.")
    if gene_id:
        parts.append(f"- NCBI Gene ID: {gene_id}.")
    if link:
        parts.append(f"- Reference: {link}")

    return "NCBI Gene evidence:\n" + "\n".join(parts)


def _format_pubmed_section(pubmed: Dict[str, Any]) -> str:
    if not isinstance(pubmed, dict) or not pubmed.get("used"):
        reason = pubmed.get("reason") if isinstance(pubmed, dict) else None
        if reason:
            return f"PubMed: not used or no data ({reason})."
        return "PubMed: not used or no relevant data."

    papers = pubmed.get("papers") or []
    if not papers:
        return "PubMed: marked as used, but no specific papers were available."

    lines: List[str] = ["PubMed evidence (key papers):"]
    for p in papers[:3]:
        pmid = p.get("pmid")
        title = p.get("title")
        year = p.get("year")
        art_type = p.get("article_type")
        summary = p.get("short_summary")
        link = p.get("link")

        line = "- "
        if year:
            line += f"[{year}] "
        if title:
            line += title
        if art_type:
            line += f" ({art_type})"
        if pmid:
            line += f" [PMID: {pmid}]"
        lines.append(line)

        if summary:
            lines.append(f"  • Summary: {summary}")
        if link:
            lines.append(f"  • Reference: {link}")

    return "\n".join(lines)


# -------------------------------------------------------------------
# Main public function
# -------------------------------------------------------------------

def explain_answer_json(answer_json: Dict[str, Any]) -> str:
    """
    Turn the structured answer_json into a human-readable explanation string.

    Style:
      - Calm, clear, and patient-friendly.
      - No new facts are invented.
      - Everything comes from answer_json.evidence.
    """

    query = answer_json.get("query") or ""
    question_type = answer_json.get("question_type") or "unknown"
    evidence = answer_json.get("evidence") or {}
    sources_used = answer_json.get("sources_used") or []
    sources_empty = answer_json.get("sources_empty") or []
    confidence = answer_json.get("confidence") or "medium"

    omim_box = evidence.get("omim") or {}
    ncbi_box = evidence.get("ncbi") or {}
    pubmed_box = evidence.get("pubmed") or {}
    clinvar_box = evidence.get("clinvar") or {}

    lines: List[str] = []

    # ---- 1) Header: what question was asked? ----
    if query:
        lines.append(f"User question: {query}")
    else:
        lines.append("User question: (not available)")

    if question_type == "variant":
        lines.append("Interpreted as: a question about a specific genetic variant.")
    elif question_type == "gene":
        lines.append("Interpreted as: a question about a gene in general.")
    else:
        lines.append(f"Interpreted as: {question_type} question.")

    lines.append(f"Overall confidence in this summary: {confidence}.")
    lines.append("")

    # ---- 2) High-level summary in plain English ----
    # Keep this short, 2–4 lines max.
    if clinvar_box.get("used") and clinvar_box.get("clinical_significance"):
        sig = clinvar_box.get("clinical_significance")
        cond = clinvar_box.get("condition")
        risk_sentence = _infer_variant_risk_from_clinvar(clinvar_box)

        lines.append("🔹 High-level interpretation")
        if cond:
            lines.append(
                f"- ClinVar links this variant to: {cond}."
            )
        lines.append(f"- ClinVar clinical significance: {sig}.")
        lines.append(f"- Summary of risk: {risk_sentence}")
    elif omim_box.get("used") and omim_box.get("phenotypes"):
        phenos = omim_box.get("phenotypes") or []
        lines.append("🔹 High-level interpretation")
        lines.append(
            "- OMIM reports that this gene is associated with: "
            + ", ".join(phenos[:3])
            + "."
        )
    elif ncbi_box.get("used") and ncbi_box.get("function"):
        lines.append("🔹 High-level interpretation")
        lines.append(
            "- NCBI Gene provides a functional summary for this gene "
            "and describes its role in the cell."
        )
    else:
        lines.append("🔹 High-level interpretation")
        lines.append(
            "- A structured evidence-based summary is provided below, "
            "but no strong clinical statements can be made from the available data."
        )

    lines.append("")
    lines.append(
        "⚠️ This explanation is informational only and does not replace "
        "professional medical or genetic counseling."
    )
    lines.append("")

    # ---- 3) Evidence sections ----
    lines.append("========== Evidence by Source ==========\n")

    lines.append(_format_clinvar_section(clinvar_box))
    lines.append("")
    lines.append(_format_omim_section(omim_box))
    lines.append("")
    lines.append(_format_ncbi_section(ncbi_box))
    lines.append("")
    lines.append(_format_pubmed_section(pubmed_box))
    lines.append("")

    # ---- 4) Source summary ----
    lines.append("========== Source Summary ==========")
    if sources_used:
        lines.append("Sources used in this summary: " + ", ".join(sources_used) + ".")
    else:
        lines.append(
            "Sources used in this summary: none (no usable evidence was available)."
        )

    if sources_empty:
        lines.append(
            "Sources with no relevant or usable data: " + ", ".join(sources_empty) + "."
        )

    return "\n".join(lines)


# Tiny manual test
if __name__ == "__main__":
    demo_answer = {
        "query": "BRCA1 c.68_69delAG. Is this mutation serious?",
        "question_type": "variant",
        "summary": "",
        "evidence": {
            "omim": {
                "used": True,
                "omim_id": "113705",
                "inheritance": "Autosomal dominant",
                "phenotypes": ["Hereditary breast and ovarian cancer"],
                "key_points": [
                    "OMIM gene entry 113705 is available for BRCA1.",
                    "Inheritance pattern reported in OMIM phenotypes: Autosomal dominant.",
                ],
                "link": "https://omim.org/entry/113705",
            },
            "ncbi": {
                "used": True,
                "gene_id": "672",
                "full_name": "BRCA1, DNA repair associated",
                "function": "BRCA1 is involved in DNA damage repair and tumor suppression.",
                "location": "17q21.31",
                "link": "https://www.ncbi.nlm.nih.gov/gene/672",
            },
            "pubmed": {
                "used": True,
                "papers": [
                    {
                        "pmid": "30209387",
                        "title": "Management of hereditary breast and ovarian cancer: BRCA1/2 mutation carriers.",
                        "year": 2018,
                        "article_type": "review",
                        "short_summary": "Review article discussing risk, surveillance, and preventive options.",
                        "link": "https://pubmed.ncbi.nlm.nih.gov/30209387/",
                    }
                ],
            },
            "clinvar": {
                "used": True,
                "accession": "RCV000031180",
                "clinical_significance": "Pathogenic",
                "condition": "Hereditary breast and ovarian cancer syndrome",
                "review_status": "reviewed_by_expert_panel",
                "num_submissions": 10,
                "conflicting_submissions": False,
                "link": "https://www.ncbi.nlm.nih.gov/clinvar/RCV000031180/",
            },
        },
        "sources_used": ["omim", "ncbi", "pubmed", "clinvar"],
        "sources_empty": [],
        "confidence": "medium",
    }

    print(explain_answer_json(demo_answer))

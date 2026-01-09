
import os
import json
from dotenv import load_dotenv

# Load env vars first
load_dotenv(override=True)
print(f"DEBUG: OMIM_API_KEY from env: {os.environ.get('OMIM_API_KEY')}")

from app.clinvar_client import get_clinvar_summary
from app.omim_client import get_omim_summary
from app.pubmed_client import get_pubmed_summary
from app.genereviews_client import get_genereviews_summary
from app.gnomad_client import get_gnomad_summary

def run_test():
    results = []

    # 1. ClinVar
    try:
        # Use a real variant known to exist: BRCA1 c.68_69delAG (NM_007294.3:c.68_69delAG)
        # Note: function sig is (gene_symbol, variant_token)
        res = get_clinvar_summary("BRCA1", "c.68_69delAG")
        if res.get("used"):
            summary = f"Accession: {res.get('accession')}, Sig: {res.get('clinical_significance')}"
            status = "OK"
            error = ""
        else:
            summary = "No data returned (used=False)"
            status = "No data returned"
            error = res.get("reason", "")
        
        results.append(["ClinVar", 'BRCA1 c.68_69delAG', status, summary, error])
    except Exception as e:
        results.append(["ClinVar", 'BRCA1 c.68_69delAG', "Error", "", str(e)])

    # 2. GeneReviews
    try:
        res = get_genereviews_summary("BRCA1")
        if res.get("used"):
            summary = f"Title: {res.get('title')}, ID: {res.get('book_id')}"
            status = "OK"
            error = ""
        else:
            summary = "No data returned (used=False)"
            status = "No data returned"
            error = res.get("reason", "")
        results.append(["GeneReviews", "BRCA1", status, summary, error])
    except Exception as e:
        results.append(["GeneReviews", "BRCA1", "Error", "", str(e)])

    # 3. OMIM
    try:
        res = get_omim_summary("BRCA1")
        if res.get("used"):
            # phenotypes is a list
            phenos = res.get("phenotypes", [])
            count = len(phenos)
            summary = f"OMIM ID: {res.get('omim_id')}, Phenotypes: {count}"
            status = "OK"
            error = ""
        else:
            summary = "No data returned (used=False)"
            status = "No data returned"
            error = res.get("reason", "")
        results.append(["OMIM", "BRCA1", status, summary, error])
    except Exception as e:
        results.append(["OMIM", "BRCA1", "Error", "", str(e)])

    # 4. Orphanet
    results.append(["Orphanet", "BRCA1", "Tool not connected", "", ""])

    # 5. gnomAD
    try:
        res = get_gnomad_summary("BRCA1")
        if res.get("used"):
            summary = f"Gene ID: {res.get('gene_id')}, Chrom: {res.get('chrom')}"
            status = "OK"
            error = ""
        else:
            summary = "No data returned (used=False)"
            status = "No data returned"
            error = res.get("reason", "")
        results.append(["gnomAD", "BRCA1", status, summary, error])
    except Exception as e:
        results.append(["gnomAD", "BRCA1", "Error", "", str(e)])

    # 6. COSMIC
    results.append(["COSMIC", "BRCA1", "Tool not connected", "", ""])

    # 7. PubMed
    try:
        res = get_pubmed_summary("BRCA1", max_results=1)
        if res.get("used"):
            papers = res.get("papers", [])
            count = len(papers)
            first_title = papers[0].get("title")[:30] + "..." if papers else "N/A"
            summary = f"Papers found: {count}, First: {first_title}"
            status = "OK"
            error = ""
        else:
            summary = "No data returned (used=False)"
            status = "No data returned"
            error = res.get("reason", "")
        results.append(["PubMed", "BRCA1", status, summary, error])
    except Exception as e:
        results.append(["PubMed", "BRCA1", "Error", "", str(e)])

    # 8. Guidelines
    results.append(["Guidelines", "BRCA1", "Tool not connected", "", ""])

    # Print Table
    print("| Source | Query used | Status | Response summary | Error (if any) |")
    print("|---|---|---|---|---|")
    for row in results:
        # source, query, status, summary, error
        # clean newlines
        row = [str(x).replace("\n", " ") for x in row]
        print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")

if __name__ == "__main__":
    run_test()

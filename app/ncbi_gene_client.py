# app/ncbi_gene_client.py
import requests


NCBI_GENE_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def fetch_gene_info(gene_symbol: str) -> dict:
    """
    Fetch basic gene metadata from NCBI Gene using the gene symbol.

    Returns a dict like:
    {
        "gene_id_ncbi": "672",
        "symbol": "BRCA1",
        "full_name": "...",
        "summary": "...",
        "chromosome": "17",
        "synonyms": [...],
        "organism": "Homo sapiens",
    }

    If anything fails → returns a safe empty structure.
    """

    if not gene_symbol:
        return {
            "gene_id_ncbi": None,
            "symbol": None,
            "full_name": None,
            "summary": None,
            "chromosome": None,
            "synonyms": [],
            "organism": None,
        }

    # 1) Search for the gene ID by symbol (human only)
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "gene",
        "term": f"{gene_symbol}[sym] AND Homo sapiens[orgn]",
        "retmode": "json",
    }

    try:
        search_resp = requests.get(search_url, params=search_params, timeout=10)
        search_resp.raise_for_status()
        search_data = search_resp.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            # No gene found
            return {
                "gene_id_ncbi": None,
                "symbol": gene_symbol,
                "full_name": None,
                "summary": None,
                "chromosome": None,
                "synonyms": [],
                "organism": None,
            }
        gene_id = id_list[0]
    except Exception as e:
        print(f"[NCBI] Error searching gene ID for {gene_symbol}: {e}")
        return {
            "gene_id_ncbi": None,
            "symbol": gene_symbol,
            "full_name": None,
            "summary": None,
            "chromosome": None,
            "synonyms": [],
            "organism": None,
        }

    # 2) Fetch summary for that gene ID
    params = {
        "db": "gene",
        "id": gene_id,
        "retmode": "json",
    }

    try:
        resp = requests.get(NCBI_GENE_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[NCBI] Error fetching gene summary for {gene_symbol}: {e}")
        return {
            "gene_id_ncbi": gene_id,
            "symbol": gene_symbol,
            "full_name": None,
            "summary": None,
            "chromosome": None,
            "synonyms": [],
            "organism": None,
        }

    # NCBI structure: result -> {gene_id: {...}}
    result = data.get("result", {})
    record = result.get(gene_id, {})

    full_name = record.get("description")
    summary = record.get("summary")
    chromosome = record.get("chromosome")
    synonyms = record.get("otheraliases", "").split(", ") if record.get("otheraliases") else []
    organism = record.get("organism", {}).get("scientificname")

    return {
        "gene_id_ncbi": gene_id,
        "symbol": gene_symbol,
        "full_name": full_name,
        "summary": summary,
        "chromosome": chromosome,
        "synonyms": synonyms,
        "organism": organism,
    }


# Tiny manual test
if __name__ == "__main__":
    print("Testing NCBI Gene client for BRCA1...")
    print(fetch_gene_info("BRCA1"))

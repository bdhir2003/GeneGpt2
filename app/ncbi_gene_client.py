# ncbi_gene_client.py
#
# Small NCBI Gene client for GeneGPT2.
#
# Public API:
#     get_ncbi_summary(gene_symbol: str, gene_id: Optional[str] = None) -> Dict[str, Any]
#
# Returns a dict like:
# {
#   "used": True/False,
#   "gene_id": str | None,
#   "full_name": str | None,
#   "function": str | None,
#   "location": str | None,
#   "link": str | None,
#   "reason": str,
# }

import os
import requests
from typing import Optional, Dict, Any

NCBI_GENE_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Old fallback mapping (kept for safety)
GENE_TO_NCBI_ID: Dict[str, str] = {
    "BRCA1": "672",
    "BRCA2": "675",
    "TP53": "7157",
    "CFTR": "1080",
    "MLH1": "4292",
}


def _get_ncbi_api_key() -> Optional[str]:
    """Read NCBI API key from env if available."""
    return os.environ.get("NCBI_API_KEY")


def fetch_ncbi_gene_raw(
    gene_symbol: str,
    gene_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Low-level NCBI Gene fetcher.

    Priority:
    1. If gene_id is provided -> use that directly (best)
    2. Else try old v1 mapping (GENE_TO_NCBI_ID)
    3. Else return None (no ID)
    """

    if not gene_symbol:
        return None

    gene_symbol_up = gene_symbol.upper()

    # 1) Best: use ID passed from mini-brain / resolver
    if gene_id:
        final_gene_id = gene_id
    else:
        # 2) Fallback to old mapping
        final_gene_id = GENE_TO_NCBI_ID.get(gene_symbol_up)
        if not final_gene_id:
            print(f"[NCBI] No Gene ID available for symbol {gene_symbol_up}")
            return None

    api_key = _get_ncbi_api_key()

    params: Dict[str, Any] = {
        "db": "gene",
        "id": final_gene_id,
        "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key

    try:
        resp = requests.get(NCBI_GENE_BASE_URL, params=params, timeout=10)
        print(f"[NCBI] Request URL: {resp.url}")
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[NCBI] HTTP error fetching gene {gene_symbol_up}: {e}")
        return None

    data = resp.json()
    result = data.get("result", {})
    gene_entry = result.get(str(final_gene_id))

    if not gene_entry:
        print(f"[NCBI] No entry data for gene ID {final_gene_id}")
        return None

    return gene_entry


def _clean_ncbi_entry(entry: Optional[Dict[str, Any]], gene_symbol: str) -> Dict[str, Any]:
    """
    Convert a raw NCBI Gene entry into the compact evidence format.
    """
    if not isinstance(entry, dict):
        return {
            "used": False,
            "gene_id": None,
            "full_name": None,
            "function": None,
            "location": None,
            "link": None,
            "reason": f"No NCBI Gene entry found for symbol {gene_symbol}.",
        }

    gene_id = entry.get("uid") or entry.get("geneid")
    full_name = entry.get("description") or entry.get("nomenclaturename")
    location = entry.get("chromosome") or entry.get("maplocation")
    summary = entry.get("summary")
    function_text = summary.strip() if summary else None
    link = f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}" if gene_id else None

    return {
        "used": True,
        "gene_id": str(gene_id) if gene_id else None,
        "full_name": full_name,
        "function": function_text,
        "location": location,
        "link": link,
        # For memory / debug: explain where this came from
        "reason": "Fetched from NCBI Gene API.",
    }


def get_ncbi_summary(gene_symbol: str, gene_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main public function.

    Example:
        get_ncbi_summary("ERBB2", gene_id="2064")
    """

    gene_symbol = (gene_symbol or "").strip()
    if not gene_symbol:
        return {
            "used": False,
            "gene_id": None,
            "full_name": None,
            "function": None,
            "location": None,
            "link": None,
            "reason": "No gene symbol provided.",
        }

    try:
        raw = fetch_ncbi_gene_raw(gene_symbol, gene_id=gene_id)
    except Exception as e:
        return {
            "used": False,
            "gene_id": None,
            "full_name": None,
            "function": None,
            "location": None,
            "link": None,
            "reason": f"Error calling NCBI: {e}",
        }

    if not raw:
        return {
            "used": False,
            "gene_id": None,
            "full_name": None,
            "function": None,
            "location": None,
            "link": None,
            "reason": f"No NCBI Gene entry found for symbol {gene_symbol}.",
        }

    return _clean_ncbi_entry(raw, gene_symbol)


# Manual test (will NOT run when imported)
if __name__ == "__main__":
    tests = [
        ("TP53", "7157"),
        ("ERBB2", "2064"),
        ("MYH7", "4625"),
        ("BRCA1", "672"),
        ("BRCA2", "675"),
    ]
    for symbol, gid in tests:
        print(f"\nTesting NCBI for {symbol} with ID {gid}:")
        print(get_ncbi_summary(symbol, gene_id=gid))

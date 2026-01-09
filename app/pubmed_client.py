# pubmed_client.py
#
# Small PubMed client for GeneGPT2.
# Uses NCBI E-utilities:
#   - esearch.fcgi  → find PubMed IDs (PMIDs)
#   - esummary.fcgi → fetch metadata for those PMIDs
#
# Returned format (evidence box used by pipeline.py):
#
# {
#   "used": True/False,
#   "papers": [
#       {
#           "pmid": "12345678",
#           "title": "Title of the paper",
#           "journal": "Journal Name",
#           "year": 2024,
#           "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
#       },
#       ...
#   ],
#   "link": "https://pubmed.ncbi.nlm.nih.gov/?term=encoded+query",
#   "reason": str (optional, when used=False)
# }

import os
import requests
from typing import List, Dict, Any, Optional

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _get_ncbi_key() -> Optional[str]:
    """Return NCBI API key if set."""
    return os.environ.get("NCBI_API_KEY")


# ------------------------------------------------------------
# 1️⃣ Search PubMed (esearch)
# ------------------------------------------------------------
def _search_pubmed(term: str, max_results: int = 5) -> List[str]:
    params: Dict[str, Any] = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    key = _get_ncbi_key()
    if key:
        params["api_key"] = key

    resp = requests.get(EUTILS_BASE + "esearch.fcgi", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids or []


# ------------------------------------------------------------
# 2️⃣ Fetch summaries (esummary)
# ------------------------------------------------------------
def _fetch_pubmed_summaries(pmids: List[str]) -> Dict[str, Any]:
    if not pmids:
        return {}

    params: Dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    key = _get_ncbi_key()
    if key:
        params["api_key"] = key

    resp = requests.get(EUTILS_BASE + "esummary.fcgi", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", {}) or {}


# ------------------------------------------------------------
# 3️⃣ Public function used by the pipeline
# ------------------------------------------------------------
def get_pubmed_summary(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    High-level PubMed helper.

    query:
        - For gene questions: usually the gene symbol (e.g., "TP53")
        - For broad questions: full user question (e.g., "heart genes")

    Returns:
        {
            "used": True/False,
            "papers": [...],
            "link": "https://pubmed.ncbi.nlm.nih.gov/?term=...",
            "reason": "..."  # only when used=False
        }
    """
    query = (query or "").strip()
    if not query:
        return {
            "used": False,
            "papers": [],
            "link": None,
            "reason": "No query provided to PubMed client.",
        }

    # URL for the generic PubMed search page (for UI 'link' field)
    encoded = requests.utils.quote(query)
    search_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded}"

    # Step 1: search for PMIDs
    try:
        pmids = _search_pubmed(query, max_results=max_results)
    except Exception as e:
        return {
            "used": False,
            "papers": [],
            "link": search_url,
            "reason": f"Error searching PubMed: {e}",
        }

    if not pmids:
        return {
            "used": False,
            "papers": [],
            "link": search_url,
            "reason": "No PubMed results found for this query.",
        }

    # Step 2: fetch summaries for those PMIDs
    try:
        summaries = _fetch_pubmed_summaries(pmids)
    except Exception as e:
        return {
            "used": False,
            "papers": [],
            "link": search_url,
            "reason": f"Error fetching PubMed summaries: {e}",
        }

    papers = []
    for pmid in pmids:
        entry = summaries.get(str(pmid))
        if not isinstance(entry, dict):
            continue

        title = entry.get("title")
        journal = entry.get("fulljournalname") or entry.get("source")
        pubdate = entry.get("pubdate") or ""
        year: Optional[int] = None

        # try to extract a 4-digit year from pubdate
        for part in pubdate.split():
            if part.isdigit() and len(part) == 4:
                year = int(part)
                break

        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        papers.append(
            {
                "pmid": str(pmid),
                "title": title,
                "journal": journal,
                "year": year,
                "url": url,
            }
        )

    return {
        "used": True,
        "papers": papers,
        # this 'link' is what shows up in the “Sources used” box
        "link": search_url,
    }


if __name__ == "__main__":
    # Tiny manual test
    print(get_pubmed_summary("alpha-1 antitrypsin deficiency"))

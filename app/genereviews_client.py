"""
genereviews_client.py

Client for NCBI Bookshelf (GeneReviews).
Uses NCBI E-utilities to find the GeneReviews chapter for a specific gene.

Method:
1. esearch: db=books, term="{gene_symbol}[Title] AND GeneReviews[Book]"
2. If found, construct link: https://www.ncbi.nlm.nih.gov/books/{ID}/

Returns a dict with:
{
    "used": True/False,
    "book_id": "NBK...",
    "title": "...",
    "link": "...",
    "reason": "..."
}
"""

import os
import requests
from typing import Dict, Any, Optional

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def _get_ncbi_key() -> Optional[str]:
    return os.environ.get("NCBI_API_KEY")

def get_genereviews_summary(gene_symbol: str) -> Dict[str, Any]:
    gene_symbol = (gene_symbol or "").strip()
    if not gene_symbol:
        return {"used": False, "reason": "No gene symbol provided."}

    # "gene[book]" restricts to the GeneReviews book
    term = f"{gene_symbol}[Title] AND gene[book]"
    
    params = {
        "db": "books",
        "term": term,
        "retmode": "json",
        "retmax": "10"
    }
    key = _get_ncbi_key()
    if key:
        params["api_key"] = key

    try:
        resp = requests.get(EUTILS_BASE + "esearch.fcgi", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return {
                "used": False, 
                "reason": f"No GeneReviews chapter found for {gene_symbol}."
            }
        
        # We need to find the actual CHAPTER, not a table or figure
        # Fetch summaries for all candidates
        summary_params = {
            "db": "books",
            "id": ",".join(id_list),
            "retmode": "json"
        }
        if key:
            summary_params["api_key"] = key
            
        sum_resp = requests.get(EUTILS_BASE + "esummary.fcgi", params=summary_params, timeout=10)
        sum_resp.raise_for_status()
        sum_data = sum_resp.json()
        result_dict = sum_data.get("result", {})
        
        # Determine the best hit
        # Priority: rtype="chapter"
        best_hit = None
        
        # Clean uids list (remove "uids" key itself if present in iteration)
        uids = result_dict.get("uids", id_list)
        
        for uid in uids:
            doc = result_dict.get(str(uid), {})
            if doc.get("rtype") == "chapter":
                best_hit = doc
                break
        
        # Fallback: if no chapter found, use the first hit
        if not best_hit and id_list:
            best_hit = result_dict.get(str(id_list[0]))
            
        if not best_hit:
             return {
                "used": False, 
                "reason": "GeneReviews ID found but summary fetch failed."
            }

        # "accessionid": "NBK1247" (used for linking)
        acc = best_hit.get("accessionid")
        title = best_hit.get("title", "")
        
        if not acc:
             return {
                "used": False, 
                "reason": f"GeneReviews entry found ({best_hit.get('uid')}) but missing accession."
            }

        link = f"https://www.ncbi.nlm.nih.gov/books/{acc}/"

        return {
            "used": True,
            "book_id": acc,
            "title": title,
            "link": link,
            "reason": f"Found GeneReviews chapter: {title}"
        }

    except Exception as e:
        return {
            "used": False,
            "reason": f"Error querying GeneReviews: {e}"
        }

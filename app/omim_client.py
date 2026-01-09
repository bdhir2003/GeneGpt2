"""
omim_client.py

Small, clean OMIM client for GeneGPT2.

DATA PLAN (what we keep from OMIM):
-----------------------------------
For each gene, we only keep:

1. omim_id
2. inheritance
   - Single string summarizing inheritance patterns seen in phenotypeMap
     (e.g., "Autosomal dominant; Autosomal recessive")
3. phenotypes (list of small dicts)
   Each item:
      {
          "name": str | None,
          "mim_number": str | None,
          "inheritance": str | None,
          "mapping_key": str | None,
      }
4. link
   - Public OMIM entry link, e.g. "https://www.omim.org/entry/113705"

Everything else is ignored.

This module exposes ONE high-level function:

    get_omim_summary(gene_symbol: str, omim_id: str | None = None) -> dict

which returns a dict shaped like:

    {
        "used": True/False,
        "omim_id": str | None,
        "inheritance": str | None,
        "phenotypes": list,
        "key_points": list,   # reserved for future use
        "link": str | None,
        "reason": str (optional, when used=False or to describe source)
    }
"""

import os
from typing import Dict, Any, Optional, List
import requests

# Base URL for OMIM API
OMIM_BASE_URL = "https://api.omim.org/api/entry"

# -------------------------------------------------------------------
# Temporary gene_symbol -> OMIM ID mapping for v1 demo
# (Question parser ALSO has mappings; this is fine for now)
# -------------------------------------------------------------------
GENE_TO_OMIM_ID: Dict[str, str] = {
    "TP53": "191170",
    "ERBB2": "164870",
    "MYH7": "160760",
    "BRCA1": "113705",
    "BRCA2": "600185",
    "CFTR": "602421",
    # add more as needed
}


def _get_omim_api_key() -> Optional[str]:
    """
    Read OMIM API key from environment variable OMIM_API_KEY.
    If not set, we return None and the API call will fail with auth error.
    """
    return os.environ.get("OMIM_API_KEY")


# -------------------------------------------------------------------
# Low-level OMIM fetch
# -------------------------------------------------------------------

def fetch_omim_entry_raw(
    gene_symbol: str,
    omim_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    """
    Low-level OMIM client.

    Steps:
      1) Decide OMIM ID:
           - if omim_id is provided, use that (preferred)
           - else gene_symbol -> omim_id using GENE_TO_OMIM_ID
      2) Call OMIM entry endpoint with ?mimNumber=...&include=geneMap
      3) Return the raw 'entry' dict, or None on failure
    """
    if not gene_symbol and not omim_id:
        return None

    gene_symbol_up = (gene_symbol or "").upper()

    # Prefer the ID passed from the resolver if available
    effective_omim_id = omim_id or GENE_TO_OMIM_ID.get(gene_symbol_up)

    if not effective_omim_id:
        print(f"[OMIM] No OMIM mapping/id for symbol {gene_symbol_up}, returning None.")
        return None

    api_key = _get_omim_api_key()
    if not api_key:
        print("[OMIM] OMIM_API_KEY not set; cannot call OMIM API.")
        return None

    params: Dict[str, Any] = {
        "mimNumber": effective_omim_id,
        "format": "json",
        "include": "geneMap",
        "apiKey": api_key,
    }

    try:
        resp = requests.get(OMIM_BASE_URL, params=params, timeout=15)
        print(f"[OMIM] Request URL: {resp.url}")
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[OMIM] Error fetching data for {gene_symbol_up} (OMIM {effective_omim_id}): {e}")
        return None

    data = resp.json()
    omim_root = data.get("omim", {})
    entry_list = omim_root.get("entryList") or []

    if not entry_list:
        print(f"[OMIM] No entryList for OMIM id {effective_omim_id}")
        return None

    first = entry_list[0] or {}
    # OMIM usually nests entry under "entry"
    entry = first.get("entry") or first

    if not isinstance(entry, dict):
        print(f"[OMIM] Unexpected entry structure for OMIM id {effective_omim_id}")
        return None

    # Attach omim_id explicitly so cleaner can always see it
    entry.setdefault("mimNumber", effective_omim_id)
    return entry


# -------------------------------------------------------------------
# Helpers to parse phenotype / inheritance
# -------------------------------------------------------------------

def _extract_gene_map(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Try to find the geneMap object within an OMIM entry.
    We make this robust because OMIM JSON can vary a bit.
    """
    # Most common pattern: entry["geneMap"]
    gene_map = entry.get("geneMap")
    if isinstance(gene_map, dict):
        return gene_map

    # Some responses use a list wrapper
    gene_map_list = entry.get("geneMapList")
    if isinstance(gene_map_list, list) and gene_map_list:
        first = gene_map_list[0] or {}
        if isinstance(first, dict):
            inner = first.get("geneMap") or first
            if isinstance(inner, dict):
                return inner

    return None


def _extract_phenotypes_and_inheritance(
    entry: Dict[str, Any],
) -> (List[Dict[str, Any]], Optional[str]):
    """
    From an OMIM 'entry', extract:

      - phenotypes: list of small dicts
      - inheritance_summary: single string summarizing inheritance patterns

    using geneMap.phenotypeMapList.
    """
    phenotypes: List[Dict[str, Any]] = []
    inheritance_labels = set()

    gene_map = _extract_gene_map(entry)
    if not gene_map:
        return phenotypes, None

    pheno_list = gene_map.get("phenotypeMapList") or []
    if not isinstance(pheno_list, list):
        return phenotypes, None

    for item in pheno_list:
        if not isinstance(item, dict):
            continue
        pm = item.get("phenotypeMap") or item
        if not isinstance(pm, dict):
            continue

        name = pm.get("phenotype")
        pheno_mim = pm.get("phenotypeMimNumber")
        inh = pm.get("phenotypeInheritance")
        mapping_key = pm.get("mappingKey")

        if inh:
            inheritance_labels.add(inh)

        if name or pheno_mim or inh:
            phenotypes.append(
                {
                    "name": name,
                    "mim_number": str(pheno_mim) if pheno_mim else None,
                    "inheritance": inh,
                    "mapping_key": str(mapping_key) if mapping_key is not None else None,
                }
            )

    if inheritance_labels:
        # Join distinct inheritance patterns into a single readable string
        inheritance_summary = "; ".join(sorted(inheritance_labels))
    else:
        inheritance_summary = None

    return phenotypes, inheritance_summary


# -------------------------------------------------------------------
# Cleaner: raw OMIM entry -> small evidence box
# -------------------------------------------------------------------

def _clean_omim_entry(entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert a raw OMIM 'entry' dict into the small, clean evidence format.
    """
    if not isinstance(entry, dict):
        return {
            "used": False,
            "omim_id": None,
            "inheritance": None,
            "phenotypes": [],
            "key_points": [],
            "link": None,
            "reason": "No OMIM entry found.",
        }

    omim_id = entry.get("mimNumber")
    if omim_id is not None:
        omim_id = str(omim_id)

    phenotypes, inheritance_summary = _extract_phenotypes_and_inheritance(entry)

    link = f"https://www.omim.org/entry/{omim_id}" if omim_id else None

    return {
        "used": True,
        "omim_id": omim_id,
        "inheritance": inheritance_summary,
        "phenotypes": phenotypes,
        "key_points": [],  # reserved for future hand-written nuggets
        "link": link,
        # NEW: explicit reason field so memory can later say
        # "this originally came from OMIM API"
        "reason": "Fetched from OMIM API.",
    }


# -------------------------------------------------------------------
# High-level helper (ONLY function used by other files)
# -------------------------------------------------------------------

def get_omim_summary(gene_symbol: str, omim_id: str | None = None) -> Dict[str, Any]:
    """
    Get a clean OMIM summary for a gene.

    If omim_id is provided (from the mini-brain / resolver), we trust it
    and call OMIM by ID. Otherwise we fall back to local mapping
    GENE_TO_OMIM_ID using the gene_symbol.

    Returns a dict like:
    {
        "used": True/False,
        "omim_id": str | None,
        "inheritance": str | None,
        "phenotypes": list,
        "key_points": list,
        "link": str | None,
        "reason": str (optional, when used=False or to describe source)
    }
    """
    gene_symbol = (gene_symbol or "").strip()
    if not gene_symbol and not omim_id:
        return {
            "used": False,
            "omim_id": None,
            "inheritance": None,
            "phenotypes": [],
            "key_points": [],
            "link": None,
            "reason": "No gene symbol or OMIM ID provided.",
        }

    try:
        raw_entry = fetch_omim_entry_raw(gene_symbol, omim_id=omim_id)
    except Exception as e:
        # Fail-safe: never crash the app because of OMIM
        return {
            "used": False,
            "omim_id": omim_id,
            "inheritance": None,
            "phenotypes": [],
            "key_points": [],
            "link": None,
            "reason": f"Error calling OMIM: {e}",
        }

    if not raw_entry:
        return {
            "used": False,
            "omim_id": omim_id,
            "inheritance": None,
            "phenotypes": [],
            "key_points": [],
            "link": None,
            "reason": f"No OMIM entry found for gene symbol {gene_symbol} (omim_id={omim_id}).",
        }

    return _clean_omim_entry(raw_entry)


# Tiny manual test (optional)
if __name__ == "__main__":
    for g in ["TP53", "ERBB2", "MYH7", "BRCA1", "BRCA2", "CFTR"]:
        print(f"\nTesting OMIM client for {g}...\n")
        summary = get_omim_summary(g)
        print(f"get_omim_summary({g}):")
        print("  used:", summary.get("used"))
        print("  omim_id:", summary.get("omim_id"))
        print("  inheritance:", summary.get("inheritance"))
        print("  #phenotypes:", len(summary.get("phenotypes") or []))
        print("  link:", summary.get("link"))
        print("  reason:", summary.get("reason"))

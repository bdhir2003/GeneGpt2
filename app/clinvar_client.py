# clinvar_client.py — REAL NCBI ClinVar API client (HGVS or rsID search)
#
# Uses NCBI's E-utilities:
#   esearch → get ClinVar record ID
#   esummary → fetch structured variant info
#
# Returns CLEAN data in the exact evidence format your pipeline expects:
# {
#   "used": True/False,
#   "accession": str or None,
#   "clinical_significance": str or None,
#   "condition": str or None,
#   "review_status": str or None,
#   "num_submissions": int or None,
#   "conflicting_submissions": bool or None,
#   "link": str or None,
#   "reason": str (explains why / where data came from)
# }

import os
import requests
from typing import Dict, Any, Optional


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _get_ncbi_key():
    """Return NCBI API key if set."""
    return os.environ.get("NCBI_API_KEY")


# ------------------------------------------------------------
# Helper: build a good ClinVar search term
# ------------------------------------------------------------
def _build_clinvar_term(gene_symbol: str, variant_token: str) -> str:
    """
    Make a smart search term for ClinVar.

    - If rsID (rs12345)      -> just use rsID
    - If HGVS (has 'c.'/'p') -> combine gene + HGVS
    - Else                   -> fallback to raw token
    """
    gene_symbol = (gene_symbol or "").strip()
    variant_token = (variant_token or "").strip()

    vt_lower = variant_token.lower()

    # rsID pattern like rs121913529
    if vt_lower.startswith("rs") and vt_lower[2:].isdigit():
        return variant_token  # ClinVar understands rsIDs directly

    # HGVS-like: c. or p. present
    if "c." in variant_token or "p." in variant_token:
        if gene_symbol:
            # e.g. BRCA1[gene] AND c.68_69delAG
            return f"{gene_symbol}[gene] AND {variant_token}"
        else:
            return variant_token

    # fallback
    if gene_symbol:
        return f"{gene_symbol}[gene] AND {variant_token}"
    return variant_token


# ------------------------------------------------------------
# 1️⃣ — Search ClinVar (esearch) using our term
# ------------------------------------------------------------
def _clinvar_esearch(term: str) -> Optional[str]:
    params = {
        "db": "clinvar",
        "term": term,
        "retmode": "json",
    }
    key = _get_ncbi_key()
    if key:
        params["api_key"] = key

    try:
        resp = requests.get(EUTILS_BASE + "esearch.fcgi", params=params, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None

    return ids[0]   # first ClinVar ID


# ------------------------------------------------------------
# 2️⃣ — Fetch summary (esummary) for ClinVar ID
# ------------------------------------------------------------
def _clinvar_esummary(cv_id: str) -> Optional[Dict[str, Any]]:
    params = {
        "db": "clinvar",
        "id": cv_id,
        "retmode": "json",
    }
    key = _get_ncbi_key()
    if key:
        params["api_key"] = key

    try:
        resp = requests.get(EUTILS_BASE + "esummary.fcgi", params=params, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    return data.get("result", {}).get(str(cv_id))


# ------------------------------------------------------------
# 3️⃣ — Extract clean fields and build evidence dict
# ------------------------------------------------------------
def get_clinvar_summary(gene_symbol: str, variant_token: str) -> Dict[str, Any]:
    """
    Main entrypoint: called from the pipeline.

    gene_symbol: e.g. "BRCA1"
    variant_token: can be HGVS (c.68_69delAG), protein HGVS, or rsID
    """
    variant_token = (variant_token or "").strip()
    if not variant_token:
        return {
            "used": False,
            "accession": None,
            "clinical_significance": None,
            "condition": None,
            "review_status": None,
            "num_submissions": None,
            "conflicting_submissions": None,
            "link": None,
            "reason": "No variant token provided to ClinVar client.",
        }

    # Step 1: Build a smart ClinVar search term
    term = _build_clinvar_term(gene_symbol, variant_token)
    print(f"[ClinVar] Search term: {term}")  # DEBUG

    # Step 2: Search ClinVar for the variant
    cv_id = _clinvar_esearch(term)
    print(f"[ClinVar] esearch ID: {cv_id}")  # DEBUG

    if not cv_id:
        return {
            "used": False,
            "accession": None,
            "clinical_significance": None,
            "condition": None,
            "review_status": None,
            "num_submissions": None,
            "conflicting_submissions": None,
            "link": None,
            "reason": f"No ClinVar match found for term '{term}'.",
        }

    # Step 3: Fetch summary for the ClinVar entry
    summary = _clinvar_esummary(cv_id)
    if not summary:
        print("[ClinVar] No summary returned")  # DEBUG
        return {
            "used": False,
            "accession": None,
            "clinical_significance": None,
            "condition": None,
            "review_status": None,
            "num_submissions": None,
            "conflicting_submissions": None,
            "link": None,
            "reason": f"ClinVar summary not available for ID {cv_id}.",
        }

    # ---- DEBUG: print raw summary keys ----
    try:
        print(f"[ClinVar] Summary keys: {list(summary.keys())}")
        print(f"[ClinVar] Raw clinical_significance: {summary.get('clinical_significance')}")
        print(f"[ClinVar] Raw trait_set: {summary.get('trait_set')}")
    except Exception:
        pass

    # ---- Extract fields safely ----
    cs = summary.get("clinical_significance") or {}
    sig = cs.get("description")
    review_status = cs.get("review_status")
    conflicts = cs.get("conflicting_data")

    # Trait / condition name
    condition = None
    trait_set = summary.get("trait_set")
    # trait_set can be a list or dict depending on ClinVar JSON
    if isinstance(trait_set, list) and trait_set:
        trait = trait_set[0].get("trait") or {}
        if isinstance(trait, dict):
            # 'name' can be a string or list
            name = trait.get("name")
            if isinstance(name, list) and name:
                condition = name[0]
            elif isinstance(name, str):
                condition = name
    elif isinstance(trait_set, dict):
        trait = trait_set.get("trait") or {}
        if isinstance(trait, dict):
            name = trait.get("name")
            if isinstance(name, list) and name:
                condition = name[0]
            elif isinstance(name, str):
                condition = name

    num_sub = summary.get("submission_count")
    accession = summary.get("accession")

    # Try to build a simple ClinVar link. Accession might be RCV... or VCV...
    link = f"https://www.ncbi.nlm.nih.gov/clinvar/{accession}" if accession else None

    # ---- DEBUG: print extracted clean fields ----
    print("[ClinVar] Extracted fields:")
    print(f"  accession: {accession}")
    print(f"  clinical_significance: {sig}")
    print(f"  condition: {condition}")
    print(f"  review_status: {review_status}")
    print(f"  num_submissions: {num_sub}")
    print(f"  conflicting_submissions: {bool(conflicts) if conflicts is not None else None}")
    print(f"  link: {link}")

    return {
        "used": True,
        "accession": accession,
        "clinical_significance": sig,
        "condition": condition,
        "review_status": review_status,
        "num_submissions": num_sub,
        "conflicting_submissions": bool(conflicts) if conflicts is not None else None,
        "link": link,
        "reason": f"Fetched from NCBI ClinVar API using term '{term}'.",
    }

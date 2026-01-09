# gene_resolver.py
# -----------------
# Mini brain v3 (ID-aware, OMIM-universal version):
#  - normalize synonyms (T53 -> TP53, HER2 -> ERBB2)
#  - look up NCBI Gene ID via NCBI esearch
#  - look up OMIM ID from:
#       1) small static mapping (common genes)
#       2) FULL mim2gene.txt mapping (if available)
#
# This means: if you download mim2gene.txt from OMIM,
# GeneGPT can resolve OMIM IDs for basically ALL human genes.
#
# To enable full OMIM support:
#   1) Download mim2gene.txt from OMIM (requires login/license):
#        https://omim.org/static/omim/data/mim2gene.txt
#   2) Save it as, for example:
#        app/data/mim2gene.txt
#   3) (Optional) Or set an env var:
#        OMIM_MIM2GENE_PATH=/full/path/to/mim2gene.txt
#
# The resolver will automatically detect and load it.

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import requests

try:
    from .name_normalizer import normalize_gene_name
except ImportError:
    from name_normalizer import normalize_gene_name

NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

# 🔹 Static mapping: gene symbol -> OMIM MIM number
# Fast path for very common genes (kept as a fallback).
GENE_TO_OMIM_ID: Dict[str, str] = {
    "TP53":  "191170",
    "BRCA1": "113705",
    "BRCA2": "600185",
    "CFTR":  "602421",
    "MLH1":  "120436",
    "ERBB2": "164870",  # HER2
    "MYH7":  "160760",
}

# 🔹 Lazy-loaded cache from mim2gene.txt
_MIM2GENE_CACHE: Optional[Dict[str, str]] = None


def _find_mim2gene_path() -> Optional[Path]:
    """
    Try to locate mim2gene.txt.

    Priority:
      1) Env var OMIM_MIM2GENE_PATH
      2) app/data/mim2gene.txt   (relative to this file)
    """
    env_path = os.getenv("OMIM_MIM2GENE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # Default: /app/data/mim2gene.txt
    # gene_resolver.py is in app/, so go to app/data/
    default_path = Path(__file__).parent / "data" / "mim2gene.txt"
    if default_path.exists():
        return default_path

    return None


def _load_mim2gene_mapping() -> Dict[str, str]:
    """
    Load mim2gene.txt once into memory.

    File format example (tab-separated):

    # MIM Number    MIM Entry Type   Entrez Gene ID   Approved Gene Symbol   Ensembl Gene ID
    100640         gene             216              ALDH1A1                 ENSG00000165092
    100650         gene/phenotype   217              ALDH2                   ENSG00000111275

    We keep only rows where MIM Entry Type contains 'gene', and map:
        SYMBOL (upper case) -> MIM Number (string)
    """
    global _MIM2GENE_CACHE
    if _MIM2GENE_CACHE is not None:
        return _MIM2GENE_CACHE

    path = _find_mim2gene_path()
    mapping: Dict[str, str] = {}

    if not path:
        # No file, we just stay with the static dict.
        print("[WARN] mim2gene.txt not found - OMIM ID lookup limited to static mapping.")
        _MIM2GENE_CACHE = mapping
        return mapping

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                # Expect at least: MIM, EntryType, EntrezID, Symbol
                if len(parts) < 4:
                    continue
                mim_number, entry_type, _, symbol = parts[:4]
                if "gene" not in entry_type.lower():
                    # skip purely phenotype entries
                    continue
                symbol_u = symbol.strip().upper()
                if not symbol_u:
                    continue
                # If multiple MIMs per symbol, keep the first one (simple rule)
                if symbol_u not in mapping:
                    mapping[symbol_u] = mim_number.strip()

        print(f"[DEBUG] Loaded mim2gene mapping from {path} with {len(mapping)} symbols.")
    except Exception as e:
        print(f"[WARN] Failed to load mim2gene.txt from {path}: {e}")
        mapping = {}

    _MIM2GENE_CACHE = mapping
    return mapping


def _fetch_omim_id_for_symbol(symbol: str) -> str | None:
    """
    Get OMIM ID for a gene symbol.

    Order:
      1) Try small static dict (fast, works even without mim2gene.txt)
      2) Try full mim2gene.txt mapping (if available)
    """
    if not symbol:
        return None

    sym_u = symbol.upper()

    # 1) Small static mapping
    if sym_u in GENE_TO_OMIM_ID:
        return GENE_TO_OMIM_ID[sym_u]

    # 2) Full mapping from mim2gene.txt
    mapping = _load_mim2gene_mapping()
    return mapping.get(sym_u)


def _fetch_ncbi_gene_id_for_symbol(symbol: str) -> str | None:
    """
    Use NCBI Gene esearch API to get a Gene ID for a symbol.
    Restrict to human genes (Homo sapiens).
    Returns a string like "7157" (TP53) or None if not found/failed.
    """
    api_key = os.getenv("NCBI_API_KEY")
    if not symbol:
        return None

    try:
        params = {
            "db": "gene",
            "term": f"{symbol}[sym] AND Homo sapiens[orgn]",
            "retmode": "json",
        }
        if api_key:
            params["api_key"] = api_key

        resp = requests.get(NCBI_ESEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return None

        gene_id = id_list[0]
        if gene_id:
            return str(gene_id)

    except Exception as e:
        print(f"[WARN] NCBI Gene ID lookup failed for {symbol}: {e}")

    return None


def resolve_gene(user_input: str) -> dict:
    """
    Mini brain entrypoint.

    Input: raw gene name from the user.
    Output: cleaned symbol + IDs.

    Example:
      "HER2" ->
      {
        "symbol": "ERBB2",
        "omim_id": "164870",
        "ncbi_id": "2064",
      }
    """
    if not user_input:
        return {"symbol": None, "omim_id": None, "ncbi_id": None}

    # 1) Normalize synonym / case (HER2 -> ERBB2, t53 -> TP53)
    symbol = normalize_gene_name(user_input)

    # 2) Look up IDs
    omim_id = _fetch_omim_id_for_symbol(symbol)
    ncbi_id = _fetch_ncbi_gene_id_for_symbol(symbol)

    resolved = {
        "symbol": symbol,
        "omim_id": omim_id,
        "ncbi_id": ncbi_id,
    }

    print("[DEBUG] resolve_gene:", user_input, "->", resolved)
    return resolved


# Tiny self-test (optional)
if __name__ == "__main__":
    for g in ["t53", "TP53", "HER2", "ERBB2", "MYH7", "BRCA1", "BRCA2", "CFTR", "ALDH1A1"]:
        print(g, "->", resolve_gene(g))

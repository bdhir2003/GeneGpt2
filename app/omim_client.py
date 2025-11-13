import os
import requests

# Base endpoint (no /search here)
OMIM_BASE_URL = "https://api.omim.org/api/entry"

# Temporary gene → OMIM ID mapping for v1 demo
# We can expand this later.
GENE_TO_MIM = {
    "BRCA1": "113705",
}


def _get_omim_api_key() -> str:
    """
    Read OMIM API key from environment variable OMIM_API_KEY.
    Do NOT hard-code your key in this file.
    """
    key = os.environ.get("OMIM_API_KEY")
    if not key:
        raise RuntimeError(
            "OMIM_API_KEY environment variable not set. "
            "Run in this terminal: export OMIM_API_KEY='your_real_key_here'"
        )
    return key


def fetch_and_filter_omim(gene_symbol: str) -> dict:
    """
    Real-ish OMIM client for v1.

    For now:
    - Map gene_symbol -> mimNumber using GENE_TO_MIM.
    - Call /api/entry?mimNumber=...&include=geneMap&format=json&apiKey=...
    - Parse gene_id_omim + a short diseases list.

    Returns structure like:
    {
        "gene_id_omim": "113705",
        "diseases": [
            {
                "name": "...",
                "omim_id": "113705",
                "inheritance": "autosomal dominant",
                "short_note": "..."
            },
            ...
        ]
    }
    """

    if not gene_symbol:
        return {"gene_id_omim": None, "diseases": []}

    gene_symbol_up = gene_symbol.upper()

    mim_number = GENE_TO_MIM.get(gene_symbol_up)
    if not mim_number:
        # For genes we don't know yet, just return safe empty structure
        print(f"[OMIM] No MIM mapping for gene {gene_symbol_up}, returning empty result.")
        return {"gene_id_omim": None, "diseases": []}

    api_key = _get_omim_api_key()

    params = {
        "mimNumber": mim_number,
        "include": "geneMap",
        "format": "json",
        "apiKey": api_key,
    }

    try:
        resp = requests.get(OMIM_BASE_URL, params=params, timeout=10)
        print(f"[OMIM] Request URL: {resp.url}")
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[OMIM] Error fetching data for {gene_symbol_up}: {e}")
        return {"gene_id_omim": None, "diseases": []}

    data = resp.json()

    # ---- Parse OMIM JSON safely ----
    entry_list = data.get("omim", {}).get("entryList", [])
    if not entry_list:
        return {"gene_id_omim": None, "diseases": []}

    entry = entry_list[0].get("entry", {})
    gene_mim_number = entry.get("mimNumber")

    diseases = []
    gene_map = entry.get("geneMap", {})
    phen_list = gene_map.get("phenotypeMapList", [])

    for phen_item in phen_list:
        phen = phen_item.get("phenotypeMap", {})

        name = phen.get("phenotype")
        phen_mim = phen.get("phenotypeMimNumber")
        inheritance = phen.get("phenotypeInheritance")

        diseases.append(
            {
                "name": name,
                "omim_id": str(phen_mim) if phen_mim else None,
                "inheritance": inheritance,
                "short_note": None,
            }
        )

    diseases = diseases[:5]

    return {
        "gene_id_omim": str(gene_mim_number) if gene_mim_number else None,
        "diseases": diseases,
    }


# Tiny manual test
if __name__ == "__main__":
    print("Testing OMIM client for BRCA1...\n")
    result = fetch_and_filter_omim("BRCA1")
    print(result)

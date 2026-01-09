from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import csv


@dataclass
class GeneRecord:
    symbol: str
    entrez_id: Optional[int] = None          # NCBI Gene / Entrez ID
    hgnc_id: Optional[str] = None
    omim_gene_id: Optional[str] = None       # OMIM gene / phenotype number
    ensembl_id: Optional[str] = None
    aliases: List[str] = None


class GeneRegistry:
    """
    Simple in-memory registry of all human genes + aliases.

    We can load from:
      - a small TSV (human_genes_example.tsv), or
      - the big OMIM mapping file (mim2gene.txt)

    Once loaded, you can look up by symbol or alias.
    """

    def __init__(self) -> None:
        self._by_symbol: Dict[str, GeneRecord] = {}
        self._by_alias: Dict[str, GeneRecord] = {}

    # --------------------------------------------------------------
    # Loader for your own TSV format (small examples, optional)
    # --------------------------------------------------------------
    def load_tsv(self, path: Path) -> None:
        """
        TSV columns (example):
        symbol  entrez_id   hgnc_id omim_gene_id ensembl_id aliases
        BRCA1   672         HGNC:1100 113705      ENSG00000012048  BRCC1;FANCS
        """
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                aliases = (
                    [a.strip() for a in row.get("aliases", "").split(";") if a.strip()]
                    or []
                )
                record = GeneRecord(
                    symbol=row["symbol"].strip(),
                    entrez_id=int(row["entrez_id"]) if row.get("entrez_id") else None,
                    hgnc_id=row.get("hgnc_id") or None,
                    omim_gene_id=row.get("omim_gene_id") or None,
                    ensembl_id=row.get("ensembl_id") or None,
                    aliases=aliases,
                )
                self._by_symbol[record.symbol.upper()] = record
                for alias in aliases:
                    self._by_alias[alias.upper()] = record

    # --------------------------------------------------------------
    # ⭐ NEW: loader for OMIM mim2gene.txt (full human gene universe)
    # --------------------------------------------------------------
    def load_mim2gene(self, path: Path) -> None:
        """
        Load OMIM's mim2gene.txt file.

        Typical columns (tab-separated):
        # MIM_Number  MIM_Entry_Type  Entrez_Gene_ID  Approved_Gene_Symbol  Gene_Name  Ensembl_Gene_ID  Comments

        We mainly care about:
          - MIM_Number         -> omim_gene_id
          - Entrez_Gene_ID     -> entrez_id
          - Approved_Gene_Symbol -> symbol
        """
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                # Skip comments / blank lines
                if not line.strip() or line.startswith("#"):
                    continue

                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue

                mim_number = parts[0].strip() or None
                entrez_raw = parts[2].strip() if len(parts) > 2 else ""
                symbol = parts[3].strip() if len(parts) > 3 else ""

                if not symbol:
                    continue  # nothing useful

                # Convert Entrez ID to int if present
                entrez_id: Optional[int]
                if entrez_raw and entrez_raw != "-":
                    try:
                        entrez_id = int(entrez_raw)
                    except ValueError:
                        entrez_id = None
                else:
                    entrez_id = None

                record = GeneRecord(
                    symbol=symbol,
                    entrez_id=entrez_id,
                    hgnc_id=None,
                    omim_gene_id=mim_number,
                    ensembl_id=None,
                    aliases=[],
                )

                self._by_symbol[symbol.upper()] = record
                # no aliases in mim2gene, but we keep structure consistent

    # --------------------------------------------------------------
    # Lookups
    # --------------------------------------------------------------
    def get_by_symbol(self, symbol: str) -> Optional[GeneRecord]:
        return self._by_symbol.get(symbol.upper())

    def get_by_alias(self, alias: str) -> Optional[GeneRecord]:
        return self._by_alias.get(alias.upper())

    def lookup(self, name: str) -> Optional[GeneRecord]:
        """Try symbol first, then alias."""
        name_u = name.upper()
        rec = self._by_symbol.get(name_u)
        if rec:
            return rec
        return self._by_alias.get(name_u)


# ---- global singleton you can import anywhere ----

gene_registry = GeneRegistry()


def init_default_registry() -> None:
    """
    Call this once at startup.

    Priority:
      1) If app/data/mim2gene.txt exists -> load full OMIM mapping.
      2) Else, if registry/data/human_genes_example.tsv exists -> load small example.
    """
    # project root: .../GENEGPT2/
    root = Path(__file__).resolve().parents[1]

    mim_path = root / "app" / "data" / "mim2gene.txt"
    if mim_path.exists():
        print(f"[GeneRegistry] Loading OMIM mapping from {mim_path}")
        gene_registry.load_mim2gene(mim_path)
        return

    # fallback: small example TSV (optional)
    tsv_path = Path(__file__).parent / "data" / "human_genes_example.tsv"
    if tsv_path.exists():
        print(f"[GeneRegistry] Loading example genes from {tsv_path}")
        gene_registry.load_tsv(tsv_path)
    else:
        print("[GeneRegistry] WARNING: no gene mapping file found.")


# Optionally initialize immediately when this module is imported
init_default_registry()

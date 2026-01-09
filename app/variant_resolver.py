"""
variant_resolver.py
-------------------

Small "mini-brain" to parse variants mentioned in user questions.

Goals:
  - Detect common variant formats:
      * rsID:        rs12345
      * HGVS cDNA:   c.68_69delAG, c.458C>G, c.35delG, c.1521_1523delCTT
      * HGVS protein: p.R175H, p.Arg175His
  - Normalize into a simple ResolvedVariant dict that the pipeline
    and clinvar_client can use.

This module does NOT call any external APIs. It only parses text.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


# -------------------------------
# Models
# -------------------------------

@dataclass
class ResolvedVariant:
    gene_symbol: Optional[str] = None  # e.g. "TP53"
    rs_id: Optional[str] = None        # e.g. "rs12345"
    hgvs_c: Optional[str] = None       # e.g. "c.68_69delAG"
    hgvs_p: Optional[str] = None       # e.g. "p.R175H"
    raw: Optional[str] = None          # original text that was parsed


# -------------------------------
# Regex patterns
# -------------------------------

# rsID: rs followed by digits
RSID_PATTERN = re.compile(r"\brs(\d+)\b", re.IGNORECASE)

# HGVS c. patterns (very approximate but works well for most queries)
# Examples:
#   c.68_69delAG
#   c.458C>G
#   c.35delG
HGVS_C_PATTERN = re.compile(
    r"\bc\.\s*[\d_]+[ACGTacgt]*\s*(del|dup|ins|delins|>)[ACGTacgt]*\b"
)

# HGVS protein patterns:
#   p.R175H
#   p.Arg175His
HGVS_P_PATTERN = re.compile(
    r"\bp\.\s*([A-Z][a-z]{2}|\w)\d+([A-Z][a-z]{2}|\w)\b"
)

# Simple protein change without p.:
#   R175H, E6V, etc. (only used if a gene is already known)
SIMPLE_PROT_PATTERN = re.compile(r"\b[A-Z]\d+[A-Z]\b")


# -------------------------------
# Core parsing helpers
# -------------------------------

def _extract_rsid(text: str) -> Optional[str]:
    m = RSID_PATTERN.search(text)
    if not m:
        return None
    return "rs" + m.group(1)


def _extract_hgvs_c(text: str) -> Optional[str]:
    m = HGVS_C_PATTERN.search(text)
    if not m:
        return None
    # Normalize spaces (remove spaces after "c.")
    hgvs = m.group(0)
    hgvs = hgvs.replace(" ", "").rstrip(".,;!?")
    return hgvs


def _extract_hgvs_p(text: str) -> Optional[str]:
    m = HGVS_P_PATTERN.search(text)
    if not m:
        return None
    return m.group(0).replace(" ", "")


def _extract_simple_protein_change(text: str) -> Optional[str]:
    m = SIMPLE_PROT_PATTERN.search(text)
    if not m:
        return None
    return m.group(0)


# -------------------------------
# Public API
# -------------------------------

def resolve_variant(
    user_text: str,
    gene_symbol: Optional[str] = None,
) -> ResolvedVariant | None:
    """
    Try to parse a variant description from user_text.

    Parameters
    ----------
    user_text : str
        The full user question or the part identified as a variant.
    gene_symbol : Optional[str]
        If the gene is already known (from gene_resolver / intent classifier),
        pass it here. This helps interpret simple patterns like "R175H".

    Returns
    -------
    ResolvedVariant | None
        Parsed variant information, or None if nothing is found.

    Examples
    --------
    resolve_variant("BRCA1 c.68_69delAG", "BRCA1")
    resolve_variant("Is rs113488022 in CFTR pathogenic?", "CFTR")
    resolve_variant("TP53 p.R175H", "TP53")
    resolve_variant("TP53 R175H", "TP53")  # simple format
    """
    if not user_text:
        return None

    text = user_text.strip()

    rs_id = _extract_rsid(text)
    hgvs_c = _extract_hgvs_c(text)
    hgvs_p = _extract_hgvs_p(text)

    # If no explicit p. notation, but a simple protein change is present
    # AND we know the gene, treat it as a protein-level change.
    if not hgvs_p and gene_symbol:
        simple_prot = _extract_simple_protein_change(text)
        if simple_prot:
            hgvs_p = f"p.{simple_prot}"

    if not any([rs_id, hgvs_c, hgvs_p]):
        # Nothing variant-like found
        return None

    return ResolvedVariant(
        gene_symbol=gene_symbol,
        rs_id=rs_id,
        hgvs_c=hgvs_c,
        hgvs_p=hgvs_p,
        raw=text,
    )


# -------------------------------
# Tiny self-test
# -------------------------------

if __name__ == "__main__":
    tests = [
        ("BRCA1 c.68_69delAG", "BRCA1"),
        ("Is rs113488022 in CFTR serious?", "CFTR"),
        ("TP53 p.R175H", "TP53"),
        ("TP53 R175H mutation", "TP53"),
        ("c.458C>G in CHRNA1", "CHRNA1"),
        ("no mutation here", "TP53"),
    ]

    for txt, gene in tests:
        v = resolve_variant(txt, gene)
        print(f"Input: {txt!r} (gene={gene}) -> {v}")

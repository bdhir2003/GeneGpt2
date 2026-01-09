import re
try:
    from .utils.gene_utils import extract_gene_symbol
    from .gene_resolver import resolve_gene
except ImportError:
    from utils.gene_utils import extract_gene_symbol
    from gene_resolver import resolve_gene

HGVS_PATTERN = re.compile(
    r"(c\.[0-9_]+[ACGTacgt]+>[ACGTacgt]+|c\.[0-9_]+del[ACGTacgt]+|c\.[0-9_]+ins[ACGTacgt]+)"
)


def build_question_json(user_question: str) -> dict:
    """
    Extract gene symbol + variant from user question.

    Returns a dict like:
    {
        "raw": "<original question>",
        "raw_question": "<original question>",

        "gene": {
            "symbol": "BRCA1"
        },

        "resolved_gene": {
            "symbol": "BRCA1",
            "omim_id": None,
            "ncbi_id": "672",
        },

        "variant": {
            "hgvs": "c.68_69delAG",
            "type": "DNA"
        } or None
    }
    """

    user_question = (user_question or "").strip()

    # --- 1) Extract raw gene symbol from text ---
    gene_symbol_raw = extract_gene_symbol(user_question)

    # --- 2) Run mini-brain resolver (normalizes + adds IDs) ---
    if gene_symbol_raw:
        resolved_gene = resolve_gene(gene_symbol_raw)
    else:
        resolved_gene = {"symbol": None, "omim_id": None, "ncbi_id": None}

    # --- 3) Extract HGVS variant ---
    hgvs_match = HGVS_PATTERN.search(user_question)

    variant_block = None
    if hgvs_match:
        variant_block = {
            "hgvs": hgvs_match.group(0),
            "type": "DNA",
        }

    return {
        # 🔹 what answer_builder reads as "query"
        "raw": user_question,
        "raw_question": user_question,

        # raw gene block (what was literally in the question)
        "gene": {
            "symbol": gene_symbol_raw,
        },

        # ✅ normalized + ID-enriched gene info from mini-brain
        "resolved_gene": resolved_gene,

        # optional variant info
        "variant": variant_block,
    }

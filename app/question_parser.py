import re
from utils.gene_utils import extract_gene_symbol

HGVS_PATTERN = re.compile(
    r"(c\.[0-9_]+[ACGTacgt]+>[ACGTacgt]+|c\.[0-9_]+del[ACGTacgt]+|c\.[0-9_]+ins[ACGTacgt]+)"
)

def build_question_json(user_question: str) -> dict:
    """
    Extract gene symbol + variant from user question.
    """

    user_question = user_question.strip()

    # --- 1) Extract gene ---
    gene_symbol = extract_gene_symbol(user_question)

    # --- 2) Extract HGVS variant ---
    hgvs_match = HGVS_PATTERN.search(user_question)

    variant_block = None
    if hgvs_match:
        variant_block = {
            "hgvs": hgvs_match.group(0),
            "type": "DNA"
        }

    return {
        "raw_question": user_question,
        "gene": {
            "symbol": gene_symbol
        },
        "variant": variant_block
    }

import re

# Words that should NOT be treated as gene symbols
BLACKLIST = {
    "GENE", "DNA", "RNA", "AND", "OR", "THE", "BUT", "FOR", "WITH", "THAT", "THIS",
    "WHAT", "WHO", "WHY", "HOW", "WHEN", "WHERE", "TELL", "ASK", "SAY", "GIVE", "TOLD", "SAID", "ASKED", "GIVEN",
    "SHOW", "LIST", "FIND", "SEARCH", "GET", "KNOW", "HAVE", "HAS", "HAD", "WAS",
    "IS", "ARE", "WERE", "BE", "BEEN", "CAN", "COULD", "SHOULD", "WOULD", "MAY",
    "MIGHT", "MUST", "DO", "DOES", "DID", "DONE", "USE", "USED", "USING", "ABOUT",
    "LIKE", "NEED", "WANT", "HELP", "PLEASE", "THANKS", "THANK", "HELLO", "HEY",
    "HI", "GOOD", "BAD", "NOT", "YES", "NO", "ANY", "ALL", "SOME", "MANY", "MOST",
    "MORE", "LESS", "ONE", "TWO", "THREE", "ZERO", "FIRST", "LAST", "NEXT", "PREV",
    "BACK", "FRONT", "TOP", "BOTTOM", "LEFT", "RIGHT", "SIDE", "END", "START",
    "STOP", "GO", "COME", "SEE", "LOOK", "WATCH", "WAIT", "TIME", "DAY", "YEAR",
    "MUTATION", "VARIANT", "DISEASE", "SYNDROME", "DISORDER", "CONDITION", "PROBLEM",
    "ISSUE", "RISK", "FACTOR", "CAUSE", "EFFECT", "RESULT", "TEST", "CHECK", "CASE",
    "REPORT", "STUDY", "PAPER", "ARTICLE", "JOURNAL", "BOOK", "PAGE", "WEB", "SITE",
    "LINK", "URL", "HTTP", "HTTPS", "COM", "ORG", "NET", "EDU", "GOV", "INFO", "BIZ",
    "NAME", "TERM", "WORD", "TEXT", "STRING", "LINE", "FILE", "DATA", "CODE", "APP",
    "TOOL", "USER", "CHAT", "BOT", "AI", "LLM", "GPT", "OPENAI", "API", "KEY", "ID",
    "DIABETES", "HEART", "CANCER", "TUMOR", "BRAIN", "LIVER", "KIDNEY", "LUNG",
    "BLOOD", "BONE", "SKIN", "EYE", "EAR", "NOSE", "MOUTH", "TOOTH", "TEETH",
    "HEAD", "NECK", "ARM", "LEG", "FOOT", "HAND", "FINGER", "TOE", "BODY",
    "SRC", "DST", "OBJ", "MSG", "REQ", "RES", "ERR", "LOG", "DEBUG", "WARN", "FAIL",
    "PASS", "TRUE", "FALSE", "NULL", "NONE", "NAN", "INF", "INT", "FLOAT", "STR",
    "BOOL", "LIST", "DICT", "SET", "TUPLE", "CLASS", "DEF", "FUNC", "VAR", "VAL",
    "LET", "CONST", "IF", "ELSE", "ELIF", "WHILE", "FOR", "TRY", "EXCEPT", "FINALLY",
    "RETURN", "YIELD", "BREAK", "CONTINUE", "IMPORT", "FROM", "AS", "IN", "IS", "NOT",
    "AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR", "EQUALS", "EQUAL", "SAME",
    "DIFF", "HETERO", "HOMO", "ZYGOUS", "GENOTYPE", "PHENOTYPE", "ALLELE", "LOCUS",
    "CHROMOSOME", "PROTEIN", "ENZYME", "RECEPTOR", "PATHWAY", "CELL", "TISSUE", "ORGAN",
    "SYSTEM", "BODY", "BLOOD", "URINE", "SALIVA", "TEST", "SAMPLE", "PATIENT", "DOCTOR",
    "NURSE", "CLINIC", "HOSPITAL", "LAB", "CENTER", "GROUP", "TEAM", "FAMILY", "PARENT",
    "CHILD", "SON", "DAUGHTER", "BROTHER", "SISTER", "WIFE", "HUSBAND", "MOTHER", "FATHER",
    "AUNT", "UNCLE", "COUSIN", "NEPHEW", "NIECE", "GRAND", "GREAT", "STEP", "HALF", "INLAW",
    "FRIEND", "GUY", "GIRL", "MAN", "WOMAN", "BOY", "KID", "BABY", "ADULT", "SENIOR",
    "HUMAN", "PERSON", "PEOPLE", "SOMEONE", "ANYONE", "NOONE", "EVERYONE", "EVERYBODY",
    "NOBODY", "SOMEBODY", "ANYBODY", "THING", "SOMETHING", "ANYTHING", "NOTHING", "EVERYTHING",
    "IT", "HE", "SHE", "THEY", "THEM", "HIM", "HER", "US", "WE", "ME", "MY", "YOUR", "OUR",
    "THEIR", "HIS", "HERS", "ITS", "MINE", "YOURS", "THEIRS", "OURS", "MYSELF", "YOURSELF",
    "HIMSELF", "HERSELF", "ITSELF", "THEMSELVES", "OURSELVES", "YOURSELVES", "WHOSE", "WHOM",
    "WHICH", "THAT", "THESE", "THOSE", "THIS", "SUCH", "SAME", "OTHER", "ANOTHER", "EACH",
    "EVERY", "BOTH", "EITHER", "NEITHER", "OWN", "SELF", "VERY", "TOO", "ALSO", "EVEN",
    "JUST", "ONLY", "QUITE", "RATHER", "ALMOST", "NEARLY", "ALWAYS", "NEVER", "OFTEN",
    "OFTEN", "SOMETIMES", "SELDOM", "RARELY", "HARDLY", "SCARCELY", "BARELY", "EVER",
    "NOW", "THEN", "HERE", "THERE", "AWAY", "OUT", "IN", "UP", "DOWN", "OFF", "OVER",
    "UNDER", "AGAIN", "ONCE", "TWICE", "THRICE", "FIRSTLY", "SECONDLY", "THIRDLY",
}

def extract_gene_symbol(user_question: str) -> str | None:
    """
    Extract gene symbols from a user question.

    Supports case-insensitive detection:
    - BRCA1
    - brca1
    - Brca1
    Ignores English words using a blacklist.
    """

    # Make everything uppercase to match patterns easily
    text_upper = user_question.upper()

    # Match gene-like tokens (BRCA1, TP53, CFTR, EGFR, MSH2, etc.)
    gene_pattern = r"\b[A-Z0-9]{3,10}\b"

    # Find all candidates
    candidates = re.findall(gene_pattern, text_upper)

    # Choose the first candidate NOT in blacklist
    for token in candidates:
        if token not in BLACKLIST:
            return token  # e.g., BRCA1

    return None

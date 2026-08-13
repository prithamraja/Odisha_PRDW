"""
Query normalisation for RETRIEVAL only.

The output feeds the embedding lookup, so expansions here exist to close the
vocabulary gap between how officials speak ("apmip", "msp") and how the catalog
questions are written ("micro-irrigation", "procurement"). Entity extraction
still sees the user's original text, so nothing here can corrupt a bound value.
"""
import re

ABBREVIATIONS: dict[str, str] = {
    "what's":  "what is",
    "how's":   "how is",
    "govt":    "government",
    "dist":    "district",
    "agri":    "agriculture",
    "hort":    "horticulture",
    "benef":   "beneficiary",
    "ben":     "beneficiary",
    "pmk":     "pm-kisan",
    "pmkisan": "pm-kisan",
    "apmip":   "micro-irrigation",
    "apcnf":   "natural farming",
    "cnf":     "natural farming",
    "msp":     "procurement",
    "dbt":     "direct benefit transfer",
    "slr":     "survey and land records",
}

# Colloquial / pre-reorganisation district names → the roster spelling.
DISTRICT_ALIASES: dict[str, str] = {
    "vizag":        "visakhapatnam",
    "cuddapah":     "ysr kadapa",
    "kadapa":       "ysr kadapa",
    "ananthapur":   "anantapur",
    "anantapuram":  "anantapur",
}


def normalize(query: str) -> str:
    """
    1. Strip whitespace & collapse spaces
    2. Lowercase
    3. Remove trailing punctuation
    4. Expand abbreviations
    5. Apply district aliases
    """
    text = query.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.lower()
    text = re.sub(r"[?.!]+$", "", text).strip()

    # Abbreviation expansion (word-boundary aware)
    for abbr, expansion in ABBREVIATIONS.items():
        text = re.sub(r"\b" + re.escape(abbr) + r"\b", expansion, text)

    # District alias normalisation
    for alias, canonical in DISTRICT_ALIASES.items():
        text = re.sub(r"\b" + re.escape(alias) + r"\b", canonical, text)

    return text

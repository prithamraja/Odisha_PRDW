"""
Query normalisation for RETRIEVAL only.

The output feeds the embedding lookup, so expansions here exist to close the
vocabulary gap between how officials speak ("GPDP", "SBM", "IHHL") and how the
catalogue questions are written. Entity extraction still sees the user's
original text, so nothing here can corrupt a bound value — this is a retrieval
aid, not a resolver.

NOT the place for entity aliases. `entity_validator`'s per-entity alias tables
are where "khurda" becomes "Khordha", because they resolve a value that gets
BOUND. Anything expanded here only ever changes what gets embedded.
"""
import re

ABBREVIATIONS: dict[str, str] = {
    "what's":  "what is",
    "how's":   "how is",
    "govt":    "government",
    "dist":    "district",
    # The programme vocabulary an officer types in short form.
    "gpdp":    "gram panchayat development plan",
    "sbm":     "swachh bharat mission sanitation",
    "swm":     "solid waste management",
    "lwm":     "liquid waste management",
    "gwm":     "grey water management",
    "fsm":     "faecal sludge management",
    "pwm":     "plastic waste management",
    "ihhl":    "individual household latrine toilet",
    "csc":     "community sanitary complex",
    "odf":     "open defecation free sanitation",
    "o&m":     "operation and maintenance",
    "cfc":     "central finance commission",
    "sfc":     "state finance commission",
    "fc":      "finance commission",
    "lsdg":    "localised sustainable development goals theme",
    "aa":      "administrative approval",
    "ta":      "technical approval",
    "ps":      "panchayat samiti block",
    "zp":      "zilla parishad district",
    "gp":      "gram panchayat",
    "gps":     "gram panchayats",
    "awc":     "anganwadi centre",
}

# Colloquial / pre-reorganisation DISTRICT spellings → the roster spelling.
# Retrieval-side only, and deliberately a copy of the same few names the
# validator aliases: a question that says "khurda" should embed near the
# catalogue questions that say "Khordha", quite apart from how the value binds.
DISTRICT_ALIASES: dict[str, str] = {
    "khurda":      "khordha",
    "khorda":      "khordha",
    "khurdha":     "khordha",
    "cuttak":      "cuttack",
    "sundergarh":  "sundargarh",
    "phulbani":    "kandhamal",
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

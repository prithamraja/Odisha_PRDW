"""Context-preserving handling of follow-up FRAGMENTS.

The defect this module exists for: a state-wide question on screen ("What is the
average landholding by social category?", Q027, no parameters) followed by the
fragment "in kurnool?".

The follow-up classifier reads that as a district edit, correctly refuses it —
Q027 has no district slot to swap — and the message then falls through to
standard catalog matching **on its own**. The only retrievable signal left in
"in kurnool?" is the district name, so the reranker picks an essentially
arbitrary district-parameterised template (observed: G14-D MARKFED procurement,
G01-D beneficiary counts). Confident, and about the wrong subject.

Three deterministic pieces live here, all pure — no LLM, no I/O:

  DRILL_MAP / drill_target   the state-wide → geo sibling map (item 2). Derived
                             from the catalog's own -S/-D/-M id convention, plus
                             a short authored list for the pairs that convention
                             cannot express.
  combined_question          the frame's question + the fragment, so matching
                             sees the subject the fragment omits (item 1).
  templates_share_subject    the datasets/theme overlap test behind the guard
  is_slot_only_fragment      "is this message nothing but a place and/or a date?"
                             (item 3)

Serving is in router.py (serve_drill_hop / ambiguous_fragment_clarify); the
wiring — hop, then re-route, then guard — is in main.py's /query handler.
"""
from __future__ import annotations

import re

from .template_catalog import TEMPLATE_CATALOG

# Deepest first: the slot a hop is keyed on is the narrowest geography the
# target adds, which is what the user actually named.
GEO_SLOTS: tuple[str, ...] = ("village", "mandal", "district")


# ── Item 2: the state-wide → geo drill map ───────────────────────────────────

def _geo_slots_of(query_id: str) -> set[str]:
    template = TEMPLATE_CATALOG.get(query_id)
    if template is None:
        return set()
    return {s["name"] for s in template["param_slots"] if s["name"] in GEO_SLOTS}


def _build_drill_map() -> dict[str, dict[str, str]]:
    """{wider template id: {geo slot named: narrower sibling id}}.

    Derived from the id suffixes rather than hand-copied: the AP catalog has 46
    Gnn families, each with an -S (state), -D (district) and -M (mandal) member,
    and that convention IS the drill relationship. A hop is keyed on the deepest
    geography the sibling adds — G01-S → G01-M adds district AND mandal, and the
    user who said "in Peddapuram?" named the mandal.
    """
    drill: dict[str, dict[str, str]] = {}
    for query_id in TEMPLATE_CATALOG:
        match = re.match(r"^(.+)-([SD])$", query_id)
        if match is None:
            continue
        base = match.group(1)
        wider = _geo_slots_of(query_id)
        for suffix in ("D", "M"):
            sibling = f"{base}-{suffix}"
            if sibling == query_id or sibling not in TEMPLATE_CATALOG:
                continue
            added = _geo_slots_of(sibling) - wider
            if not added:
                continue
            deepest = next(slot for slot in GEO_SLOTS if slot in added)
            drill.setdefault(query_id, {})[deepest] = sibling
    return drill


# Pairs the id convention cannot express: two state-wide PM-KISAN landholding
# questions whose district/mandal reading is the G04 equity family, not a
# same-named sibling (they have none — they are Qnnn ids).
_AUTHORED_DRILL: dict[str, dict[str, str]] = {
    # "What is the average landholding by social category?"
    "Q027": {"district": "G04-D", "mandal": "G04-M"},
    # "What is the average landholding per district?"
    "Q019": {"district": "G04-D"},
}

DRILL_MAP: dict[str, dict[str, str]] = _build_drill_map()
for _wider, _targets in _AUTHORED_DRILL.items():
    DRILL_MAP.setdefault(_wider, {}).update(_targets)


def drill_target(query_id: str | None, slot: str | None) -> str | None:
    """The sibling that answers `query_id` narrowed to `slot`, or None."""
    if not query_id or not slot:
        return None
    return DRILL_MAP.get(query_id, {}).get(slot)


# ── Item 1: the combined question ────────────────────────────────────────────

def combined_question(frame_question: str | None, fragment: str) -> str:
    """'What is the average landholding by social category?' + 'in kurnool?'
    -> 'What is the average landholding by social category? in kurnool'.

    Deterministic by construction: the frame's canonical question, one space,
    the fragment with its trailing punctuation dropped so the result carries a
    single question mark.
    """
    base = (frame_question or "").strip()
    tail = (fragment or "").strip().rstrip("?.! ")
    if not base:
        return tail
    if not tail:
        return base
    if not base.endswith(("?", ".", "!")):
        base += "?"
    return f"{base} {tail}"


# ── Item 3: is the routed template plausibly the same subject? ───────────────

# 'All 8', 'All 6 AP schemes', 'All 7 Aadhaar-bearing datasets' — a collective
# that covers every dataset, so it cannot tell two subjects apart.
_WILDCARD_DATASETS = re.compile(r"^(all\b|\d+\s+ap\s+schemes\b)", re.IGNORECASE)


def _dataset_tokens(spec: str | None) -> set[str] | None:
    """{'pm-kisan', 'agriculture'} for 'PM-KISAN + Agriculture'.

    None means "a collective that spans everything" — it overlaps with anything,
    so it can never be evidence that two templates are about different things.
    """
    tokens: set[str] = set()
    for part in re.split(r"\s*\+\s*", spec or ""):
        name = part.strip().lower()
        if not name:
            continue
        if _WILDCARD_DATASETS.match(name):
            return None
        name = name.replace("_", " ")
        name = re.sub(r"\bhorticulture apmip\b", "horticulture", name)
        tokens.add(name)
    return tokens or None


def templates_share_subject(a_id: str | None, b_id: str | None) -> bool:
    """True when two catalog templates are plausibly about the same thing.

    The test is `datasets AND theme`, not "either one". Both halves are needed:

      - theme alone is too coarse — 40 templates share 'Targeting & equity';
      - datasets alone is too coarse in the other direction — the observed
        Q027 → G01-D misroute shares 'PM-KISAN' with its frame, and two of the
        catalog's dataset strings are collectives that match everything, which
        would make the guard unfireable exactly where it is needed (Q067's
        'All 7 Aadhaar-bearing datasets').

    Unknown ids (dashboards, anything not in the catalog) are treated as sharing
    — the guard only ever fires on evidence, never on a lookup miss.
    """
    a = TEMPLATE_CATALOG.get(a_id or "")
    b = TEMPLATE_CATALOG.get(b_id or "")
    if a is None or b is None:
        return True
    if (a.get("theme") or "") != (b.get("theme") or ""):
        return False
    a_sets = _dataset_tokens(a.get("datasets"))
    b_sets = _dataset_tokens(b.get("datasets"))
    if a_sets is None or b_sets is None:
        return True
    return bool(a_sets & b_sets)


# ── Item 3: is the message nothing but a place and/or a period? ──────────────

# Words that carry no measure: articles, prepositions, the geographic unit nouns
# that trail a place name ("in kurnool district"), and the handful of verbs a
# user puts in front of a bare scope ("show me kurnool").
_FUNCTION_WORDS = {
    "a", "about", "again", "also", "an", "and", "are", "as", "at", "back",
    "be", "but", "by", "did", "do", "does", "district", "districts", "for",
    "from", "give", "here", "how", "in", "into", "is", "it", "its", "just",
    "many", "mandal", "mandals", "me", "much", "now", "of", "ok", "okay", "on",
    "one", "only", "or", "our", "please", "same", "show", "so", "some",
    "something", "that", "the", "then", "there", "these", "this", "those",
    "to", "us", "village", "villages", "was", "were", "what", "which", "with",
    "s",
}

# Anything that reads as a period rather than a measure. Kept in step with
# date_phrase.py's vocabulary, which is what actually sets the SQL window.
_DATE_WORDS = {
    "jan", "january", "feb", "february", "mar", "march", "apr", "april", "may",
    "jun", "june", "jul", "july", "aug", "august", "sep", "sept", "september",
    "oct", "october", "nov", "november", "dec", "december",
    "kharif", "rabi", "season", "year", "years", "fy", "month", "months",
    "last", "quarter",
}

_YEARISH = re.compile(r"^(19|20)\d{2}$")
_TOKEN = re.compile(r"[a-z0-9']+")


def geo_vocabulary_tokens(*value_lists: list[str]) -> set[str]:
    """Every word that occurs in a district / mandal / village name, lowercased.

    Token-level rather than whole-name matching so multi-word places ("East
    Godavari", "Pedda Nandipadu") are recognised without an O(vocabulary) scan
    of every message.
    """
    tokens: set[str] = set()
    for values in value_lists:
        for value in values or []:
            tokens.update(_TOKEN.findall(str(value).lower()))
    return tokens


def fragment_place_phrase(message: str, geo_tokens: set[str]) -> str | None:
    """The place a fragment names: 'in east godavari district' -> 'east godavari'.

    Every word that belongs to the place vocabulary, in order. Nothing else is
    kept, so the function words and any period wording fall away. A message
    naming two places joins them into one phrase that will simply fail to
    validate — which is the right outcome: one slot cannot hold two values.
    """
    words = [w for w in _TOKEN.findall((message or "").lower()) if w in geo_tokens]
    return " ".join(words) or None


def is_slot_only_fragment(message: str, geo_tokens: set[str]) -> bool:
    """True for 'in kurnool?', 'for Guntur', 'what about 2024 in Kurnool?'.

    False the moment the message contains a content word that is neither a place
    nor a period — that word is the measure, and a message with a measure is a
    question in its own right, not a fragment leaning on the frame.
    """
    words = _TOKEN.findall((message or "").lower())
    if not words:
        return False
    named_something = False
    for word in words:
        if word in _FUNCTION_WORDS:
            continue
        if word in _DATE_WORDS or _YEARISH.match(word):
            named_something = True
            continue
        if word in geo_tokens:
            named_something = True
            continue
        return False
    return named_something

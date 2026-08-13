"""Context-preserving handling of follow-up FRAGMENTS.

The defect this module exists for: a state-wide question on screen ("How many
activities are abandoned?") followed by the fragment "in Ganjam?".

The follow-up classifier reads that as a district edit, refuses it when the
frame has no district bound, and the message then falls through to standard
catalog matching **on its own**. The only retrievable signal left in "in Ganjam?"
is the district name, so the reranker picks an essentially arbitrary
district-mentioning template. Confident, and about the wrong subject.

Three deterministic pieces live here, all pure — no LLM, no I/O:

  drill_target               the state-wide → narrowed mapping (item 2). Under
                             decision D2 this is the SAME template with an
                             optional slot filled, not a different one.
  combined_question          the frame's question + the fragment, so matching
                             sees the subject the fragment omits (item 1).
  templates_share_subject    the bracket/module overlap test behind the guard
  is_slot_only_fragment      "is this message nothing but a place and/or a date?"
                             (item 3)

Serving is in router.py (serve_drill_hop / ambiguous_fragment_clarify); the
wiring — hop, then re-route, then guard — is in main.py's /query handler.
"""
from __future__ import annotations

import re

from .template_catalog import TEMPLATE_CATALOG

# Deepest first: the slot a hop is keyed on is the narrowest geography the
# target adds, which is what the user actually named. These are the WORKBOOK'S
# BIND NAMES, which is what param_slots carries.
GEO_SLOTS: tuple[str, ...] = ("gp_name", "block_name", "district_name")


# ── Item 2: the state-wide → narrowed drill hop ──────────────────────────────
#
# THE AP DRILL MAP IS GONE, and nothing replaces it, because there is nothing
# left to map. That map existed to find a NARROWER SIBLING TEMPLATE: the AP
# catalogue spelled scope into the id (G01-S state / -D district / -M mandal),
# so "in Peddapuram?" after a state-wide answer meant hopping G01-S → G01-M.
#
# Decision D2 removed the siblings. One PR&DW template answers at every scope,
# and narrowing it means BINDING ITS OPTIONAL GEOGRAPHY SLOT — the same template
# id, one more parameter. So the hop target is the frame's own template whenever
# that template has the named tier as an optional slot, which is what
# `drill_target` now returns.

def _geo_slots_of(query_id: str) -> set[str]:
    template = TEMPLATE_CATALOG.get(query_id)
    if template is None:
        return set()
    return {s["name"] for s in template["param_slots"] if s["name"] in GEO_SLOTS}


def drill_target(query_id: str | None, slot: str | None) -> str | None:
    """The template that answers `query_id` narrowed to `slot`, or None.

    Returns `query_id` ITSELF when that template can take the slot — under D2
    the narrowed question is the same entry with one more optional parameter
    bound. None when the template has no such slot, which is the honest answer:
    there is no narrower form of that question to hop to, and the caller falls
    through to ordinary matching rather than inventing one.
    """
    if not query_id or not slot:
        return None
    return query_id if slot in _geo_slots_of(query_id) else None


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

def templates_share_subject(a_id: str | None, b_id: str | None) -> bool:
    """True when two catalog templates are plausibly about the same thing.

    The test is `bracket AND module`, the workbook's own two-level
    classification. Both halves are needed, for the reason the AP version needed
    both of its own:

      - the BRACKET alone is far too coarse — 'Planning' holds 66 templates and
        'Sanitation (SBM)' 85, so a guard keyed on it would almost never fire;
      - the MODULE alone is too coarse in the other direction — 'GPDP' spans
        Planning, Budgeting, Expenditure and Implementation, which are exactly
        the subjects a stray fragment slides between.

    Together they are the level at which "is this still the same subject?" has a
    sensible answer: Planning/GPDP against Expenditure/GPDP is a real change of
    subject, and Planning/GPDP against Planning/GPDP is not.

    Unknown ids (dashboards, known-unanswerables, anything not in the catalogue)
    are treated as sharing — the guard only ever fires on evidence, never on a
    lookup miss.
    """
    a = TEMPLATE_CATALOG.get(a_id or "")
    b = TEMPLATE_CATALOG.get(b_id or "")
    if a is None or b is None:
        return True
    return (a.get("bracket"), a.get("module")) == (b.get("bracket"), b.get("module"))


# ── Item 3: is the message nothing but a place and/or a period? ──────────────

# Words that carry no measure: articles, prepositions, the geographic unit nouns
# that trail a place name ("in kurnool district"), and the handful of verbs a
# user puts in front of a bare scope ("show me kurnool").
_FUNCTION_WORDS = {
    "a", "about", "again", "also", "an", "and", "are", "as", "at", "back",
    "be", "but", "by", "did", "do", "does", "for",
    "from", "give", "here", "how", "in", "into", "is", "it", "its", "just",
    "many", "me", "much", "now", "of", "ok", "okay", "on",
    "one", "only", "or", "our", "please", "same", "show", "so", "some",
    "something", "that", "the", "then", "there", "these", "this", "those",
    "to", "us", "was", "were", "what", "which", "with", "s",
    # The unit nouns that trail a place name in PR&DW: "in Ganjam district",
    # "for Barpali block", "Andhrua GP", "Bhubaneswar panchayat samiti".
    "district", "districts", "zilla", "parishad", "zp",
    "block", "blocks", "samiti", "samitis", "panchayat", "panchayats",
    "gram", "gp", "gps", "village", "villages",
}

# Anything that reads as a period rather than a measure. Kept in step with
# date_phrase.py's vocabulary, which is what actually sets the SQL window.
# The agricultural seasons are gone — kharif and rabi are not PR&DW concepts —
# and the fiscal wording an officer uses is in.
_DATE_WORDS = {
    "jan", "january", "feb", "february", "mar", "march", "apr", "april", "may",
    "jun", "june", "jul", "july", "aug", "august", "sep", "sept", "september",
    "oct", "october", "nov", "november", "dec", "december",
    "year", "years", "fy", "financial", "fiscal", "month", "months",
    "last", "quarter", "quarters", "q1", "q2", "q3", "q4",
}

_YEARISH = re.compile(r"^(19|20)\d{2}$")
_TOKEN = re.compile(r"[a-z0-9']+")


def geo_vocabulary_tokens(*value_lists: list[str]) -> set[str]:
    """Every word that occurs in a district / block / GP name, lowercased.

    Token-level rather than whole-name matching so multi-word places ("Tangi
    Choudwar") are recognised without an O(vocabulary) scan of every message.
    """
    tokens: set[str] = set()
    for values in value_lists:
        for value in values or []:
            tokens.update(_TOKEN.findall(str(value).lower()))
    return tokens


def fragment_place_phrase(message: str, geo_tokens: set[str]) -> str | None:
    """The place a fragment names: 'in tangi choudwar block' -> 'tangi choudwar'.

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

# -*- coding: utf-8 -*-
"""Turn classification: retrieve / navigate / lookup / why (D5.2).

**The decision is logged per turn**, which the brief requires, and it is logged
with its REASON and its source — so a turn routed by the rule layer and a turn
routed by the model are told apart in the log rather than blended.

**Two layers, rules first.** The rule layer is not an optimisation; it is what
makes three of the four gate behaviours deterministic. A gate that asserts "a
why-question always gets the reframe" cannot rest on a model that flips ~3% of
identical replays — the bootstrap's own lesson about routing non-determinism.
So the constructions that unambiguously mark a why-question or a record lookup
are matched deterministically, and the model is asked only about what is left.

**The model gets the context brief** (D42 ruling 8), so it classifies knowing
who is asking and what the system holds.

**Ambiguity resolves toward the honest answer, not the impressive one.** If the
model gives no clear verdict, the turn is treated as RETRIEVE, which is the move
that can end in "the analysis has nothing on this". Defaulting to LOOKUP would
route a real question away to another product; defaulting to WHY would refuse a
question that could have been answered.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from . import config, context_brief, llm

RETRIEVE, NAVIGATE, LOOKUP, WHY = "retrieve", "navigate", "lookup", "why"
# WP-D6 D6.1. Not a fifth kind of answer: a DECOMPOSE turn retrieves exactly as
# a RETRIEVE turn does, over one corpus that holds findings and decompositions
# together. What the move records is the officer's INTENT, which is worth
# logging, and -- the reason it has to exist at all -- it is what keeps
# "who is driving the shortfall" off the causal reframe.
DECOMPOSE = "decompose"


@dataclass
class Routing:
    move: str
    source: str            # "rule" | "model" | "default"
    reason: str
    raw: str = ""

    def as_dict(self) -> dict:
        return {"move": self.move, "source": self.source, "reason": self.reason}


# ── The rule layer ───────────────────────────────────────────────────────────
# WHY. Only constructions that ask for a cause. "What is the reason for" counts;
# a bare "how come" counts; "why not show me X" does not, and is left to the
# model rather than guessed at.
_WHY_PATTERNS = [
    (re.compile(r"^\s*why\b", re.IGNORECASE), "opens with 'why'"),
    (re.compile(r"\bwhy (?:is|are|was|were|do|does|did|has|have|so)\b", re.IGNORECASE),
     "asks why something is the case"),
    (re.compile(r"\bwhat(?:'s| is| are)? (?:the )?(?:reason|cause|causes|root cause)\b",
                re.IGNORECASE), "asks for the reason or cause"),
    (re.compile(r"\bwhat(?:'s| is)? (?:causing|driving|behind)\b", re.IGNORECASE),
     "asks what is causing or driving something"),
    (re.compile(r"\bhow come\b", re.IGNORECASE), "asks how come"),
    (re.compile(r"\bexplain why\b", re.IGNORECASE), "asks for an explanation of why"),
]

# LOOKUP. A request for a value, a record or a roster entry out of the database.
# These are Ask's questions, and this product must route rather than improvise.
_LOOKUP_PATTERNS = [
    (re.compile(r"\bhow (?:much|many)\b", re.IGNORECASE),
     "asks for a quantity"),
    (re.compile(r"\bwhat (?:is|was) the (?:total|amount|figure|number|count|balance)\b",
                re.IGNORECASE), "asks for a specific figure"),
    (re.compile(r"\b(?:give|show|list|get) me the (?:list|names?|records?|details)\b",
                re.IGNORECASE), "asks for a list of records"),
    (re.compile(r"\bwho (?:is|are|was|were) the\b", re.IGNORECASE),
     "asks who holds a post or role"),
    (re.compile(r"\bwhich (?:activities|works|vouchers|records|files) (?:are|were|have)\b",
                re.IGNORECASE), "asks which records match a condition"),
    (re.compile(r"\btop \d+\b", re.IGNORECASE), "asks for a ranked list of records"),
]


# ── DECOMPOSE. The vocabulary is data (`decompose_triggers.json`) ────────────
with open(config.DATA_DECOMPOSE_TRIGGERS, encoding="utf-8") as _fh:
    _TRIGGERS = json.load(_fh)

_DECOMPOSE_PATTERNS = [(re.compile(p, re.IGNORECASE), why)
                       for p, why in _TRIGGERS["share_of_total"]]
_DECOMPOSE_CAUSAL = [(re.compile(p, re.IGNORECASE), why)
                     for p, why in _TRIGGERS["causal_phrasing"]]
_ACCOUNTING_NOUN = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _TRIGGERS["accounting_nouns"])
    + r")\b", re.IGNORECASE)


def decompose_route(message: str) -> Routing | None:
    """A question about where an amount sits, or None.

    The causal half is gated on an accounting noun; the data file's
    `why_the_nouns_gate_the_causal_half` gives the reasoning at length. In
    short: "who is driving the shortfall" names an additive quantity and has an
    arithmetic answer, "what is causing the year-end spike" names a shape and
    keeps the D41 reframe.
    """
    for pattern, reason in _DECOMPOSE_PATTERNS:
        if pattern.search(message):
            return Routing(DECOMPOSE, "rule", reason)
    for pattern, reason in _DECOMPOSE_CAUSAL:
        if pattern.search(message) and _ACCOUNTING_NOUN.search(message):
            return Routing(DECOMPOSE, "rule",
                           f"{reason}, and the thing named is an amount that "
                           f"adds up, so it has an arithmetic answer")
    return None


def asked_causally(message: str) -> bool:
    """Did a DECOMPOSE turn arrive in causal wording?

    The answer then carries a deterministic note saying the breakdown shows
    where the amount sits and not what produced it — because the officer asked
    "who is driving this", and handing back a split without that line lets the
    split be read as the causal answer D41 forbids.
    """
    return any(p.search(message) for p, _ in _DECOMPOSE_CAUSAL)


def rule_route(message: str) -> Routing | None:
    # DECOMPOSE is tested FIRST, and the ordering is load-bearing rather than
    # arbitrary: two of the constructions the D6.1 brief names are already
    # caught by the rules below, and caught wrongly. "Who is driving the
    # shortfall" matches the WHY rule and would be refused with the causal
    # reframe although the sidecar holds its arithmetic answer; "which blocks
    # account for the gap" sits next to the LOOKUP family. Tested last, this
    # rule would never fire on either.
    routed = decompose_route(message)
    if routed is not None:
        return routed
    # WHY before LOOKUP. "Why is spending so much higher in X" contains "how
    # much"-adjacent wording and would otherwise be read as a quantity request,
    # and a why-question misrouted to LOOKUP loses the D41 reframe entirely.
    for pattern, reason in _WHY_PATTERNS:
        if pattern.search(message):
            return Routing(WHY, "rule", reason)
    for pattern, reason in _LOOKUP_PATTERNS:
        if pattern.search(message):
            return Routing(LOOKUP, "rule", reason)
    return None


# ── The model layer ──────────────────────────────────────────────────────────
_PROMPT = """{context}

Reply with JSON only, no other text:

{{"move": "RETRIEVE" | "NAVIGATE" | "LOOKUP" | "WHY" | "DECOMPOSE", "reason": "<one short sentence>"}}

{history}The officer's message:
{message}
"""


def _history_block(history: list) -> str:
    if not history:
        return ("There is nothing earlier in this conversation, so NAVIGATE is "
                "not available.\n\n")
    lines = ["Earlier in this conversation, the system showed these findings:"]
    for item in history[-6:]:
        lines.append(f"  - {item}")
    return "\n".join(lines) + "\n\n"


def classify(message: str, history: list | None = None, *, turn_id=None,
             allow_model: bool = True) -> Routing:
    """Route one turn. Rules first, model for the remainder."""
    routed = rule_route(message)
    if routed is not None:
        return routed
    if not allow_model:
        return Routing(RETRIEVE, "default", "rules did not match; model disabled")

    prompt = _PROMPT.format(context=context_brief.for_classifier(),
                            history=_history_block(history or []),
                            message=message)
    try:
        record = llm.call(config.CLASSIFIER_MODEL, prompt,
                          config.CLASSIFIER_MAX_COMPLETION, "classify",
                          turn_id=turn_id)
    except Exception as exc:
        return Routing(RETRIEVE, "default",
                       f"classifier unavailable ({type(exc).__name__}); "
                       f"treated as a retrieve turn")

    parsed = _parse(record["response_text"])
    if parsed is None:
        return Routing(RETRIEVE, "default",
                       "classifier gave no clear verdict; treated as a retrieve "
                       "turn", raw=record["response_text"][:200])
    move, reason = parsed
    return Routing(move, "model", reason, raw=record["response_text"][:200])


def _parse(text: str):
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None
    move = str(obj.get("move", "")).strip().lower()
    if move not in (RETRIEVE, NAVIGATE, LOOKUP, WHY, DECOMPOSE):
        return None
    return move, str(obj.get("reason", "")).strip()

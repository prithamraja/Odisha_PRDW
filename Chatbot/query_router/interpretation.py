"""What the system did with the message — REPORTED, never predicted.

Five paths in `/query` bind a message to the question already on screen, and
until this module existed only one of them said so:

    frame edit          swaps a slot and re-queries the SAME template
    operation           computes on the table already on screen
    fragment re-route   re-routes a subject-less fragment ("in ganjam?")
                        together with the prior question — including the drill
                        hop, the tier clarification and the ambiguous-fragment
                        clarification, which are readings of the fragment
                        against the frame just as much as a served answer is
    scope inheritance   a genuinely new question narrowed to the frame's
                        geography — the one path that already announced itself
    clarification reply a short reply resumes the question the router paused on

A frame edit returns an ordinary successful answer, byte-for-byte
indistinguishable from a fresh question that happened to match that template,
so no frontend can infer any of this. It is a backend field first.

TWO RULES GOVERN THE WHOLE MECHANISM

1. REPORT, NEVER PREDICT. The marker describes what already happened. Nothing
   may claim in advance that the next message will be read as a follow-up — a
   frame is live after every answered question, while the reading is decided per
   message, so any always-on "following up on…" chrome would be asserting
   something the system has not decided yet.

2. GENERATED TEXT IS NEVER A FOLLOW-UP. A tapped chip and a word-for-word
   catalogue question bypass the follow-up classifier by construction
   (`main.query_endpoint` drops the frame for both), so they report
   `new_question` and the UI draws nothing. A false marker on a chip tap teaches
   the user to distrust the true ones.

THE DEFAULT IS THE STANDALONE READING. Any path that does not bind is correct by
omission, and a path someone forgets to stamp reports no marker rather than a
wrong one.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from .models import ContextFrame, OperationResult, PendingClarification

# `detail` is a short human phrase — "district → Khordha", "sum of
# actual_expenditure", "answered: district_name". Never a debug dump: it rides
# on an answer an officer reads, and the cap is enforced here rather than
# trusted at the call sites so no future path can widen it by accident.
MAX_DETAIL_CHARS = 60

InterpretationKind = Literal[
    "new_question",          # routed standalone — the UI renders nothing
    "frame_edit",
    "operation",
    "fragment_reroute",
    "scope_inherited",
    "clarification_reply",
]

BOUND_KINDS: frozenset[str] = frozenset(
    {"frame_edit", "operation", "fragment_reroute",
     "scope_inherited", "clarification_reply"}
)


class Interpretation(BaseModel):
    """Which question the answer answers, and how the message got there."""

    kind:               InterpretationKind = "new_question"
    anchor_question:    Optional[str] = None   # the earlier question it was read against
    anchor_template_id: Optional[str] = None
    detail:             Optional[str] = None   # short phrase, e.g. "district → Khordha"

    @field_validator("detail")
    @classmethod
    def _cap_detail(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = " ".join(str(value).split())
        if not text:
            return None
        if len(text) <= MAX_DETAIL_CHARS:
            return text
        return text[: MAX_DETAIL_CHARS - 1].rstrip() + "…"


def against_frame(
    kind: InterpretationKind,
    frame: ContextFrame | None,
    detail: str | None = None,
) -> Interpretation:
    """A reading against the frame the message was CLASSIFIED against.

    Pass the frame read off the store BEFORE the handler replaces it. Read it
    afterwards and every marker reports the answer's own question as the question
    it followed up on — self-referential, and always wrong.

    No frame means nothing to anchor to, and a marker with nothing to anchor to
    is a UI with nothing to draw, so the reading degrades to standalone rather
    than being reported half-built.
    """
    if frame is None:
        return Interpretation()
    return Interpretation(
        kind=kind,
        anchor_question=frame.template_question or frame.template_id,
        anchor_template_id=frame.template_id,
        detail=detail,
    )


def against_pending(
    pending: PendingClarification | None,
    detail: str | None = None,
) -> Interpretation:
    """A reply read against the question the router PAUSED on.

    The anchor is the user's own paused wording rather than the catalogue
    phrasing: it is what they see above the clarification they are answering.
    """
    if pending is None:
        return Interpretation()
    return Interpretation(
        kind="clarification_reply",
        anchor_question=pending.original_query or pending.query_id,
        anchor_template_id=pending.query_id,
        detail=detail,
    )


# ── detail phrasings ─────────────────────────────────────────────────────────

def readable_slot(slot: str | None) -> str:
    """`district_name` → "district". The bind name is the workbook's, not a
    word an officer uses."""
    text = str(slot or "").strip()
    if text.endswith("_name"):
        text = text[: -len("_name")]
    return text.replace("_", " ") or "value"


def slot_detail(slot: str | None, value: str | None) -> str | None:
    """"district → Khordha"."""
    if not slot or value in (None, ""):
        return None
    return f"{readable_slot(slot)} → {value}"


def period_detail(start: str | None, end: str | None) -> str | None:
    if not start or not end:
        return None
    return f"period → {start} to {end}"


def operation_detail(result: OperationResult | None) -> str | None:
    """"sum of actual_expenditure", or just "sort" where no column applies."""
    if result is None or not result.operation:
        return None
    if result.column:
        return f"{result.operation} of {result.column}"
    return str(result.operation)

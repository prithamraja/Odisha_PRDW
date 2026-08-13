"""
Three-way follow-up classification against the current context frame
(spec Section 4): every utterance with an active frame is exactly one of

  frame_edit   — an edit to the frame (entity swap, time-range change)
                 within the current template; executed as a re-query
  operation    — a computation on the current result table (Section 2)
  new_question — reset to standard catalog matching

The LLM only classifies and names slots/values from what the user said;
execution and arithmetic are deterministic code.
"""
import json
import re
from datetime import date
from typing import Iterable

from openai import OpenAI
from pydantic import BaseModel

from .config import RERANK_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT_SECONDS, REASONING_MODELS
from .models import ColumnMetadata, ContextFrame, OperationRequest
from .operations import OPERATIONS, _match_column_name, filter_type_error
from .template_catalog import TEMPLATE_CATALOG

# Every parameter name any catalog template declares. A "frame_edit" naming one
# of these is a real edit the CURRENT question happens not to support; a
# "frame_edit" naming anything else ("hospital") is the model hallucinating a
# slot, and there is nothing to preserve context for.
CATALOG_SLOT_NAMES: frozenset[str] = frozenset(
    slot["name"].lower()
    for template in TEMPLATE_CATALOG.values()
    for slot in template["param_slots"]
)


class FrameEdit(BaseModel):
    slot:       str | None = None   # bound parameter to swap (e.g. "district")
    value:      str | None = None   # new raw value (e.g. "Guntur")
    start_date: str | None = None   # YYYY-MM-DD; set for time-range edits
    end_date:   str | None = None


class FollowupDecision(BaseModel):
    # frame_edit | operation | new_question | unexecutable_edit
    #
    # "unexecutable_edit" is a frame_edit the CURRENT template cannot execute:
    # the user named a real catalog slot ("in kurnool?") that this question has
    # no parameter for. It used to collapse into "new_question", which sent the
    # bare fragment through matching on its own — and a fragment carries no
    # subject, so it landed wherever the district name pointed. Keeping the
    # distinction is what lets the caller re-route it WITH its context; `edit`
    # carries the slot/value the user tried to set.
    kind:      str
    operation: OperationRequest | None = None
    edit:      FrameEdit | None        = None


# ── Catalog-question guard ────────────────────────────────────────────────────
# A message that is word-for-word a catalog question (a tapped chip, or a user
# typing exactly what a chip would send) must never be eaten by the follow-up
# classifier — it routes straight to matching, no LLM judgment involved.

def _norm_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip("?.! ").lower())


def catalog_question_patterns(questions: Iterable[str]) -> list[re.Pattern]:
    """Compile each catalog question ('What is the crop mix in {district}?') into
    a shape pattern with slots as wildcards. Built once at startup."""
    patterns = []
    for question in questions:
        escaped = re.escape(_norm_question(question))
        patterns.append(re.compile(re.sub(r"\\\{\w+\\\}", ".+?", escaped) + r"\Z"))
    return patterns


def matches_catalog_question(message: str, patterns: list[re.Pattern]) -> bool:
    normalized = _norm_question(message)
    return any(p.match(normalized) for p in patterns)


_SYS = """\
You classify a user's follow-up message against the question they are currently looking at, for the Andhra Pradesh Department of Agriculture "RTGS Decision Aid" assistant. It answers questions about the PM-KISAN farmer roster and the state's Agriculture, Horticulture/APMIP, Fisheries, Sericulture, MARKFED and RySS schemes, plus Survey & Land Records.

Classify into exactly one kind:

1. "frame_edit" — the message changes ONE aspect of the current question and keeps the rest:
   - entity swap: "what about Guntur?", "and Kurnool?" → set "slot" to the parameter being changed and "value" to the new value
   - time change: "for 2024", "last 6 months", "this Kharif" → set "start_date" and "end_date" (YYYY-MM-DD), computed from today's date given below
   Only parameters the current question actually has can be swapped. A message naming a parameter the question doesn't have is a "new_question".
   A frame_edit REPLACES the current value — the old one disappears. A message asking to COMPARE, or to see two values side by side ("compare with Guntur", "vs Kurnool", "how does that compare to Krishna?"), keeps BOTH and is therefore the "compare" operation, never a frame_edit.
   A frame_edit is a FRAGMENT that is meaningless without the current question. A complete question that names its own measure or subject ("How much input subsidy went to Guntur district?") is a "new_question" even if it mentions the same district, entity, or time period as the current question.

2. "operation" — a computation on the current result table:
   sum ("total?"), average, min, max ("which mandal is highest?"), count, share_of_total (set "label" if a row is named), sort (set "direction"), top_n / bottom_n (set "n"), percent_change, filter_rows — narrowing the rows on screen, e.g. "only rows above 900", "just the ones over 1000", "only Peddapuram", "mandals containing kota", "drop the empty ones" (set filter_column, filter_operator: = != > >= < <= contains, filter_value), compare ("compare with Krishna" — set "comparator" to the named value(s) and "comparator_slot" to the parameter being compared), median, mode ("most common crop" — works on category columns like cropname too; set "column"), stdev ("how much do they vary?", "spread"), percentile (set "n" to the percentile, e.g. "90th percentile" → n=90), range ("spread from lowest to highest"), count_distinct ("how many different crops?" — set "column").
   Set "column" when the user names a table column; omit it for the default.
   An operation computes over the rows currently displayed. "count" counts those rows — a "how many X?" question where X is not what the table's rows represent (e.g. "how many farmers are in PM-KISAN?" over a procurement table) is a "new_question", not a count. The same restriction applies to every other operation; see THE SUBJECT RULE below.

3. "new_question" — a different question, a change of subject, or anything you are not sure about. When in doubt, choose "new_question": the standard matcher will handle it.

THE SUBJECT RULE (applies to EVERY operation, not just count)
   An operation can only ever describe the table that is already on screen. When the message has a "which X / per X / by X / how many X" form, set "subject" to that X — the dimension or entity the question is about ("Which district received the highest single input subsidy?" → "district"; "which mandal is highest?" → "mandal"; "how many small or marginal farmers" → "farmers"). Set "subject" to null when the message names no subject ("total?", "sort it", "top 5").
   Words for the table itself — "rows", "records", "entries", "results" — are NOT subjects; leave "subject" null for those ("only rows above 900" has no subject, it is a filter).
   If the subject is not one of the table's columns, the message is a "new_question" — the answer the user wants is not in these rows, and labelling some other column's winner with it would silently answer about the wrong thing. A farmer-level table of subsidies cannot answer "which DISTRICT received the highest single input subsidy": that is a new_question.

FILTER VALUES MUST BELONG TO THEIR COLUMN
   For "filter_rows", the value has to be a plausible value OF the named column. A numeric column holds numbers, so "how many small or marginal farmers" over a procurement-by-mandal table (columns GEOGRAPHY, farmers, total_quantity) is a "new_question", not a filter of "farmers" contains "small or marginal" — land-size categories are not in the table at all.

Return ONLY a JSON object:
{"kind": "frame_edit|operation|new_question",
 "slot": null, "value": null, "start_date": null, "end_date": null,
 "operation": null, "subject": null, "column": null, "label": null, "n": null, "direction": null,
 "filter_column": null, "filter_operator": null, "filter_value": null,
 "comparator": null, "comparator_slot": null}"""


def classify_followup(
    utterance: str,
    frame: ContextFrame,
    client: OpenAI,
) -> FollowupDecision:
    columns = ", ".join(
        f"{c.name} ({c.column_type.value})" for c in frame.result_set.columns
    )
    params = ", ".join(f"{k}={v}" for k, v in frame.bound_params.items()) or "none"
    time_range = (
        f"{frame.time_range.start} to {frame.time_range.end}"
        if frame.time_range.start else frame.time_range.grain
    )
    user_msg = (
        f"Today's date: {date.today().isoformat()}\n"
        f"Current question: {frame.template_question or frame.template_id}\n"
        f"Its parameters: {params}\n"
        f"Its time range: {time_range}\n"
        f"Table columns: {columns} ({frame.result_set.row_count} rows shown)\n\n"
        f'User message: "{utterance}"\nJSON:'
    )

    try:
        kwargs = dict(
            model=RERANK_MODEL,
            timeout=LLM_TIMEOUT_SECONDS,
            messages=[
                {"role": "system", "content": _SYS},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
        )
        if RERANK_MODEL in REASONING_MODELS:
            kwargs["max_completion_tokens"] = 500
            kwargs["extra_body"] = {"reasoning_effort": "low"}
        else:
            kwargs["temperature"] = LLM_TEMPERATURE
            kwargs["max_tokens"] = 250

        resp = client.chat.completions.create(**kwargs)
        data = json.loads(resp.choices[0].message.content.strip())
    except Exception:
        return FollowupDecision(kind="new_question")

    return parse_decision(data, frame)


# ── Deterministic backstops ───────────────────────────────────────────────────
# The architecture contract is "the LLM only classifies; code is deterministic".
# That only holds if code checks the classification is EXECUTABLE against this
# table — otherwise a plausible-looking operation runs against the wrong column
# and narrates a confident wrong answer. These two guards are that check.

# What a user calls a dimension vs what the SQL called the column. Loose column
# matching (exact → substring) gets "district" → "DISTRICT" but not
# "farmer" → "FARMERNAME" or "mandal" → "sub_district".
# Every Gnn-D / -M template labels its grouping column "geography" rather than
# "mandal" or "village", so the geo subjects must reach it or the guard fires on
# perfectly good operations ("only Peddapuram" over a procurement-by-mandal
# table). It is safe: a table with no geography column — the farmer-level
# subsidy table this guard was written for — still refuses "which district".
_GEOGRAPHY_COLUMNS = ["geography", "geo", "area_name", "region"]

_SUBJECT_ALIASES: dict[str, list[str]] = {
    "farmer":   ["farmername", "farmer_name", "name"],
    "mandal":   ["sub_district", "mandal", "subdistrict"] + _GEOGRAPHY_COLUMNS,
    "crop":     ["cropname", "crop_name", "crop"],
    "village":  ["village"] + _GEOGRAPHY_COLUMNS,
    "district": ["district", "dist_name"] + _GEOGRAPHY_COLUMNS,
    "scheme":   ["scheme"],
}

# Words naming the TABLE rather than anything in it. "only rows above 900" is a
# filter with no subject at all, but the model sometimes fills "rows" in anyway;
# treating that as an unresolvable subject would reject a legitimate operation.
_META_SUBJECTS = {
    "row", "rows", "record", "records", "entry", "entries",
    "result", "results", "table", "data", "value", "values", "item", "items",
}


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def resolve_subject(subject: str, columns: list[ColumnMetadata]) -> str | None:
    """The column the question's subject refers to, or None if this table has no
    such column — in which case the question is about something not on screen."""
    text = str(subject).strip().lower()
    if not text:
        return None
    for candidate in (text, _singular(text)):
        matched = _match_column_name(candidate, columns)
        if matched is not None:
            return matched
        for alias in _SUBJECT_ALIASES.get(candidate, []):
            matched = _match_column_name(alias, columns)
            if matched is not None:
                return matched
    return None


def parse_decision(data: dict, frame: ContextFrame) -> FollowupDecision:
    """Pure, testable projection of the LLM's JSON onto a safe decision."""
    kind = str(data.get("kind", "")).strip().lower()

    if kind == "frame_edit":
        slot = data.get("slot")
        value = data.get("value")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        bound = bool(slot and value and slot in frame.bound_params)
        has_swap = bound
        if bound and (
            str(frame.bound_params[slot]).strip().lower() == str(value).strip().lower()
        ):
            # No-op swap: the "new" value is what's already bound. Executing it
            # could only re-serve the same answer, so the LLM misread — a full
            # question mentioning the current entity is a new question.
            has_swap = False
        has_time = bool(start_date and end_date)
        if not has_swap and not has_time:
            # The edit named a slot this question has no parameter for. Say WHY
            # it can't run rather than collapsing to new_question: a slot the
            # catalog knows ("district", "crop") is a fragment leaning on the
            # current question, and routing it alone loses the subject — that is
            # how "in kurnool?" over a state-wide landholding question came back
            # as MARKFED procurement. A slot the catalog has never heard of is
            # the LLM inventing one, and a no-op swap is it latching onto an
            # entity in a complete question; both of those really are new
            # questions.
            if (
                not bound
                and slot and value
                and str(slot).strip().lower() in CATALOG_SLOT_NAMES
            ):
                return FollowupDecision(
                    kind="unexecutable_edit",
                    edit=FrameEdit(slot=str(slot).strip().lower(), value=str(value)),
                )
            return FollowupDecision(kind="new_question")
        return FollowupDecision(
            kind="frame_edit",
            edit=FrameEdit(
                slot=str(slot) if has_swap else None,
                value=str(value) if has_swap else None,
                start_date=str(start_date) if has_time else None,
                end_date=str(end_date) if has_time else None,
            ),
        )

    if kind == "operation":
        operation = str(data.get("operation") or "").strip().lower()
        if operation not in OPERATIONS:
            return FollowupDecision(kind="new_question")

        columns = frame.result_set.columns

        # The question names a subject this table has no column for — so no
        # computation over these rows can answer it, whatever the LLM chose.
        # Routing it as a new question finds the template that CAN.
        subject = data.get("subject")
        if (
            subject
            and str(subject).strip().lower() not in _META_SUBJECTS
            and resolve_subject(subject, columns) is None
        ):
            return FollowupDecision(kind="new_question")

        # A filter whose value can't belong to its column is not a filter of
        # this table — it is a question about something the table doesn't hold.
        # On this path the message still has somewhere to go, so route it as a
        # new question rather than answering with a rejection.
        if operation == "filter_rows" and filter_type_error(
            data.get("filter_column"),
            data.get("filter_operator"),
            data.get("filter_value"),
            columns,
        ):
            return FollowupDecision(kind="new_question")

        comparator = data.get("comparator")
        if isinstance(comparator, str):
            comparator = [comparator]
        if comparator is not None and not (
            isinstance(comparator, list) and all(isinstance(v, str) for v in comparator)
        ):
            comparator = None

        def _opt_str(key: str) -> str | None:
            value = data.get(key)
            return str(value) if value is not None else None

        n = data.get("n")
        return FollowupDecision(
            kind="operation",
            operation=OperationRequest(
                operation=operation,
                column=_opt_str("column"),
                label=_opt_str("label"),
                n=int(n) if isinstance(n, (int, float, str)) and str(n).isdigit() else None,
                direction=_opt_str("direction"),
                filter_column=_opt_str("filter_column"),
                filter_operator=_opt_str("filter_operator"),
                filter_value=_opt_str("filter_value"),
                comparator=comparator,
                comparator_slot=_opt_str("comparator_slot"),
            ),
        )

    return FollowupDecision(kind="new_question")

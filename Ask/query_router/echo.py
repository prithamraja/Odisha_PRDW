"""Echo-back rendering: the resolved question, standing alone. Spec invariant 4
called for appending inherited context (filters + explicit time range) too,
but that's dropped here by explicit product decision — the breadcrumb already
shows filters and period as chips, so repeating them in prose read as
redundant. Same decision applies to the "Back to: ..." pop message in
main.py.

The one thing that IS added is an explicit empty-result sentence. A large part
of the AP catalog is integrity checks whose good outcome is zero rows ("which
Aadhaar numbers in Sericulture are missing from PM-KISAN?"). Echoing only the
question above an empty table leaves the user to guess whether nothing was
found or something broke, and that guess is exactly where a reader starts
inventing rows.
"""
from .models import ContextFrame, OperationMode, OperationResult, RouteResult

# The blank line between the echoed question and what follows it — the same
# separator `append_caveat` puts above a caveat.
_PARAGRAPH_BREAK = "\n\n"

_NO_ROWS = "No records matched — nothing was found for this question."

# Decision D3. 296 of the 346 PR&DW templates carry a caveat, because 251 of the
# signed-off questions are only PARTIALLY answerable: approval tables cover ~17%
# of activities, scheme_name is 82% null, SBM subjects are found by searching
# free text, and every percentage divides by the GPs actually loaded rather than
# the official roster. An answer served without its caveat is not a slightly
# worse answer — it is the confidently-wrong failure mode.
_CAVEAT_PREFIX = "Note: "


def append_caveat(answer: str, caveat: str | None) -> str:
    """Put the caveat under the answer, VERBATIM.

    Two properties matter and both are structural rather than stylistic:

    IT IS CONCATENATED, NOT PROMPTED. `answer` is built here, deterministically,
    from the resolved question — no LLM is involved on this path. The caveat is
    appended to that finished string, so there is no step at which a model could
    soften it, shorten it or drop it. Putting the caveat into a generation prompt
    instead would make it advisory, and the whole point is that it is not.

    IT IS ALSO STILL A SEPARATE FIELD. `QueryResponse.caveat` carries the same
    text unchanged, so a frontend can render it distinctly. This function exists
    because a caveat that ONLY lives in a field is one an unaware client silently
    drops — and the client here is a separate workstream.
    """
    if not (caveat or "").strip():
        return answer
    return f"{answer}\n\n{_CAVEAT_PREFIX}{caveat.strip()}"


def echo_answer_without_caveat(result: RouteResult) -> str:
    """The echoed question and the empty-result sentence, and nothing else.

    Split out for callers that have to insert a line BETWEEN the question and
    the caveat. The one such caller — the scope-inheritance note — was retired
    when `Interpretation` shipped (the reading is reported beside the answer
    now, not inside it), so nothing outside this module composes an answer this
    way today. Anything that starts to should still prefer `echo_answer`, which
    cannot forget the caveat.
    """
    question = result.query_description or result.query_id or "Query matched."
    if result.result is not None and len(result.result) == 0:
        return f"{question}\n\n{_NO_ROWS}"
    return question


def echo_answer(result: RouteResult) -> str:
    return append_caveat(echo_answer_without_caveat(result), result.caveat)


# ── The echo an operations answer never had (WP-4c §5.2, decision D31.2) ──────
#
# THE GAP THIS CLOSES. Every other serving path restates the question it
# answered — that is what `echo_answer` is for, and it is the disclosure D3
# rests on. The operations path emitted a COMPUTED SENTENCE instead and left
# `query_description` as None: measured at 1 / 4 / 3 served answers per WP-4c
# replay with no echo at all, and the truncated-table rows were among them.
#
# It is what made #1404 the worst-behaved defect in the run. Every other
# confidently-wrong row in that eval at least printed the question it actually
# answered — #1016 says "in 2024-2025", which an attentive reader catches. Here
# the only disclosure the design provides was simply absent, so the wrong
# superlative arrived with nothing at all beside it.
#
# DETERMINISTIC, like every other echo in this module. No LLM builds this
# sentence; it is assembled from the operation, the column it ran on, the scope
# it ran over and the period the frame carries, so it cannot describe an
# operation other than the one that ran.

_OPERATION_PHRASE = {
    "sum":            "Total",
    "average":        "Average",
    "min":            "Lowest",
    "max":            "Highest",
    "count":          "Row count",
    "share_of_total": "Share of total",
    "sort":           "Sorted by",
    "filter_rows":    "Filtered by",
    "percent_change": "Change in",
    "top_n":          "Highest",
    "bottom_n":       "Lowest",
    "compare":        "Comparison of",
    "median":         "Median",
    "mode":           "Most common",
    "stdev":          "Spread (standard deviation) of",
    "percentile":     "Percentile of",
    "range":          "Range of",
    "count_distinct": "Distinct values of",
}

# Slots that describe WHEN rather than WHERE, named separately so the period
# lands at the end of the sentence where a reader expects it.
_PERIOD_SLOTS = ("date_range_2", "date_range")


def _readable(name: str | None) -> str:
    """'planned_cost' -> 'planned cost'. Column and slot names are the only
    vocabulary available here, and they are the catalogue's own."""
    return (name or "").strip().strip('"').replace("_", " ").strip().lower()


def operation_description(
    frame: ContextFrame, result: OperationResult
) -> str:
    """The one-line restatement of what an operation answered.

    'Lowest planned cost among all focus area, 2024-2025:' — the operation, the
    measure, the SCOPE and the period. The scope clause is the load-bearing
    half: `among all …` is only ever written after the guard has re-queried over
    the full population, and a client-side computation says `among the rows
    shown` instead, so the sentence distinguishes the two cases the defect
    conflated.
    """
    phrase = _OPERATION_PHRASE.get(result.operation, result.operation.replace("_", " "))
    measure = _readable(result.column)
    head = f"{phrase} {measure}".strip() if measure else phrase

    scope = ""
    dimension = _readable(frame.grouping_dimension)
    if result.mode is OperationMode.REQUERY:
        scope = f" among all {dimension}" if dimension else " over the full result"
    elif result.mode is OperationMode.CLIENT:
        scope = f" among the {dimension} shown" if dimension else " among the rows shown"

    period = ""
    years = [v for slot in _PERIOD_SLOTS
             if (v := (frame.bound_params or {}).get(slot))]
    if years:
        period = ", " + " to ".join(dict.fromkeys(reversed(years)))

    return f"{head}{scope}{period}:"


def operation_answer(
    frame: ContextFrame, result: OperationResult, caveat: str | None
) -> str:
    """The echo, the computed sentence, and the frame's caveat.

    THE CAVEAT TRAVELS WITH THE RECOMPUTATION, not only with the original
    answer. An operation recomputes over the same question's rows, so whatever
    qualifies those rows qualifies the number taken from them: a share of a
    population covered at 17% is exactly as misleading as the count it came
    from. A REJECTED result is an explanation rather than an answer, so it gets
    no echo — restating a question above a sentence saying why it was not
    answered reads as though it had been.
    """
    if result.mode is OperationMode.REJECTED:
        return append_caveat(result.answer, caveat)
    return append_caveat(
        operation_description(frame, result)
        + _PARAGRAPH_BREAK
        + result.answer, caveat)

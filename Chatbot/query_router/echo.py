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
from .models import RouteResult

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

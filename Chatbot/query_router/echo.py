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


def echo_answer(result: RouteResult) -> str:
    question = result.query_description or result.query_id or "Query matched."
    if result.result is not None and len(result.result) == 0:
        return f"{question}\n\n{_NO_ROWS}"
    return question

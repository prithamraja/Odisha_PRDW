# -*- coding: utf-8 -*-
"""The causal-verb ban — D41, enforced deterministically.

D41: **correlations only, no causal analysis anywhere in Discover-facing prose
or chat.** The operator's stated reason is that none of the outcome variables
are reliable enough to support causal claims. A verifier can be argued with; a
word list cannot, which is why the ban is mechanical and runs on every piece of
generated text before it is shown.

THIS MODULE IS NOW A THIN ADAPTER. The vocabulary lives in
`Insights/src/prose_gate.py` (WP-D6 D6.2 item 1) and this file imports it.

WP-D5 wrote the ban here because `prose_gate.py` was outside its writable set,
and said so in this docstring, and named the consequence: prose_gate's own entry
point did not run the ban, so the executive and gamma REPORTS were never covered
by D41 — only DiscoverChat was. It also named the fix: "folding this vocabulary
into prose_gate proper is a one-function change for whoever owns that file
next." WP-D6 owns it, and this is that change, from the other end.

WHY AN ADAPTER RATHER THAN A DELETION. `scan`, `check` and `failure_reason` are
called from `checks.py`, `gates.py` and the writer's regeneration path. Keeping
the three names costs nine lines and means the unification cannot break a call
site; what it must NOT do is keep a second copy of the list, which is the drift
the consolidation exists to prevent. There is no list below.

ONE BEHAVIOURAL CHANGE, AND IT IS A TIGHTENING. prose_gate's list catches bare
"explain" where this file's caught only "explains"/"explained by", and it pairs
that with an exemption for the recommendation construction ("ask the districts
to explain their unspent sanctions"), which is a report telling an officer what
to do next rather than a claim about the data. Both halves now apply to chat
output as well.
"""
from __future__ import annotations

from prose_gate import (                                       # noqa: F401
    ASSOCIATION_VOCABULARY,
    CAUSAL_PATTERNS,
    NEGATION_WINDOW,
    causal_failure_reason,
    check_causal,
    scan_causal,
)


def scan(text: str) -> list:
    """Every causal construction in `text`, as (surface, meaning, position)."""
    return scan_causal(text)


def check(text: str) -> dict:
    return check_causal(text)


def failure_reason(result: dict) -> str:
    """Plain-English reason, fed back on the single regeneration."""
    return causal_failure_reason(result)

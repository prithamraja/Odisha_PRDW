# -*- coding: utf-8 -*-
"""The causal-verb ban — D41, enforced deterministically.

D41: **correlations only, no causal analysis anywhere in Discover-facing prose
or chat.** The operator's stated reason is that none of the outcome variables
are reliable enough to support causal claims. A verifier can be argued with; a
word list cannot, which is why the ban is mechanical and runs on every piece of
generated text before it is shown.

WHY THIS LIVES HERE AND NOT IN `Insights/src/prose_gate.py`
-----------------------------------------------------------
The brief says D5.2 "extends its vocabulary with the causal-verb ban".
`prose_gate.py` is an EXISTING file under `Insights/src/`, which this WP may
import but must not edit, so the extension is written here and prose_gate is
imported for the part that is genuinely shared. Two consequences, both reported
rather than papered over:

  - prose_gate's own entry point does not yet run this ban, so the executive and
    gamma REPORTS are not covered by it. Only DiscoverChat is. Folding this
    vocabulary into prose_gate proper is a one-function change for whoever owns
    that file next.
  - prose_gate is section-and-report-shaped (it splits a markdown file on '## '
    headings and checks reading notes). A chat turn has neither, so its
    `check_report` is not reusable here; what IS reused is its shape — a list of
    printable problems, empty when clean.

WHAT IS BANNED, AND WHAT REPLACES IT
------------------------------------
Banned: the constructions that assert one thing produced another. The
replacements are association vocabulary — the sanctioned alternative named in
the brief — and they are offered in the failure message so a regeneration knows
what to reach for rather than only what to avoid.

DELIBERATE NON-CATCHES. "because" is banned as a causal connective, but the
phrase "we cannot say because of what" is a statement of a limit, not a claim,
and the negation guard below lets it through. A ban that fires on honest
hedging would push the writer away from stating limits, which is the opposite
of what D41 wants.
"""
from __future__ import annotations

import re

# Each entry: (compiled pattern, what it asserts). The patterns are written
# against whole words so 'causes' does not fire inside 'because'.
_CAUSAL_PATTERNS = [
    (r"\bcaus(?:e|es|ed|ing)\b",                    "asserts a cause"),
    (r"\bcausal(?:ly)?\b",                          "asserts a cause"),
    (r"\bdrives?\b|\bdriving\b|\bdriven by\b",      "asserts one thing drives another"),
    (r"\bexplains?\b|\bexplained by\b",             "asserts one thing explains another"),
    (r"\bleads? to\b|\bled to\b|\bleading to\b",    "asserts one thing leads to another"),
    (r"\bresults? in\b|\bresulted in\b|\bresulting in\b", "asserts a result"),
    (r"\bdue to\b",                                 "attributes a cause"),
    (r"\bbecause of\b|\bbecause\b",                 "attributes a cause"),
    (r"\bowing to\b|\bon account of\b",             "attributes a cause"),
    (r"\bas a result\b|\bconsequently\b|\bthereby\b", "asserts a consequence"),
    (r"\btherefore\b|\bhence\b",                    "asserts a consequence"),
    (r"\bresponsible for\b|\bblame[ds]?\b",         "assigns responsibility for an outcome"),
    (r"\bstems? from\b|\barises? from\b|\bcomes? down to\b", "attributes an origin"),
    (r"\bimpact(?:s|ed|ing)? (?:on )?(?:the )?\w+",  "asserts an effect"),
    (r"\baffect(?:s|ed|ing)?\b|\binfluenc(?:e|es|ed|ing)\b", "asserts an effect"),
    (r"\btriggers?\b|\btriggered\b",                "asserts a trigger"),
    (r"\bthe reason\b|\bthe root cause\b|\bwhy this (?:is|happens)\b", "offers a reason"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), meaning) for p, meaning in _CAUSAL_PATTERNS]

# The association vocabulary that replaces it. Offered on failure so the
# regeneration is told what to say, not only what not to say.
ASSOCIATION_VOCABULARY = (
    "is associated with; occurs alongside; moves together with; is concentrated "
    "in; coincides with; the same places also show; where X is high, Y tends to "
    "be high; the analysis does not establish which way this runs"
)

# A causal word inside an explicit denial is a statement of a LIMIT, not a claim.
# 'The analysis cannot say what causes this' must pass, or the ban would push
# the writer away from stating exactly the limit D41 wants stated.
_NEGATION_WINDOW = 60
_NEGATIONS = re.compile(
    r"\b(?:cannot|can't|does not|doesn't|do not|don't|not able to|no way to|"
    r"unable to|never|without)\b", re.IGNORECASE)


def _is_denied(text: str, start: int) -> bool:
    window = text[max(0, start - _NEGATION_WINDOW):start]
    return bool(_NEGATIONS.search(window))


def scan(text: str) -> list:
    """Every causal construction in `text`, as (surface, meaning, position)."""
    problems = []
    for pattern, meaning in _COMPILED:
        for m in pattern.finditer(text or ""):
            if _is_denied(text, m.start()):
                continue
            problems.append({"surface": m.group(0), "asserts": meaning,
                             "position": m.start()})
    # One report per surface form, at its first position — a word used three
    # times is one problem to fix, not three.
    seen, unique = set(), []
    for p in sorted(problems, key=lambda p: p["position"]):
        key = p["surface"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def check(text: str) -> dict:
    problems = scan(text)
    return {"pass": not problems, "problems": problems}


def failure_reason(result: dict) -> str:
    """Plain-English reason, fed back on the single regeneration."""
    if result["pass"]:
        return ""
    words = ", ".join(f"'{p['surface']}'" for p in result["problems"])
    return (
        f"It used causal wording: {words}. This analysis finds patterns and "
        f"associations and cannot establish what causes what, so say how things "
        f"go together rather than what produced what. Wording that works: "
        f"{ASSOCIATION_VOCABULARY}."
    )

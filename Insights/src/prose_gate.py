# =============================================================================
# Prose gate: per-view vocabulary and reading-note checks
# =============================================================================
# The prose gate has been a read-through checklist. Two of its items are
# mechanical, and this makes those two automatic.
#
# 1. VOCABULARY. Every view has its own pipeline and its own words for it.
#    view4 is MARKFED procurement: crop is delivered and the farmer is PAID or
#    UNPAID. view6 is the horticulture subsidy: money is SANCTIONED and then
#    RELEASED, and a file that has released almost nothing is STALLED. Neither
#    view has the other's columns, so neither may borrow the other's words.
#    The gamma 0.5 report of 2026-07-30 carried
#        "Chittoor and East Godavari are the payment hold-up districts, with
#         release rates near 22.1%"
#    in the horticulture section -- a release stall described as a payment
#    hold-up. Both halves are about real figures; the sentence still sends an
#    officer to the wrong pipeline. That is the class of error this catches.
#
# 2. READING NOTES. Methodology caveats are emitted deterministically by
#    phase5b_report.reading_note_block, not written by the model. This checks
#    that each note that should be there is, exactly once, and that the model
#    has not written a rival one of its own.
#
# Run from Metainsights_anomalies/:
#   python src/prose_gate.py reports/gamma_0.5_report.md
#   python src/prose_gate.py reports/*.md
# Exits 1 if anything is flagged, so it can gate a run.
# =============================================================================

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase5b_report import (
    VIEW_DESCRIPTIONS, VIEW_VOCABULARY, READING_NOTES, READING_NOTE_MARKER,
)


# A model-authored methodology block, under whatever heading it reaches for.
_RIVAL_NOTE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*\s*)?"
    r"(reading note|note on the data|note on these figures|coverage note|"
    r"caveat|important assumption|how to read|methodology)\b",
    re.IGNORECASE,
)

_TITLE_TO_VIEW = {info["title"]: view for view, info in VIEW_DESCRIPTIONS.items()}


# =============================================================================
# 3. THE CAUSAL-VERB BAN  (D41, added by WP-D6 §D6.2)
# =============================================================================
# D41: correlations only, no causal analysis anywhere in Discover. The
# operator's stated reason is that none of the outcome variables are reliable
# enough to support causal claims.
#
# THIS IS THE CANONICAL COPY. WP-D5 wrote the ban in `DiscoverChat/causal_gate.py`
# because `prose_gate.py` was outside its writable set, which left the executive
# and gamma REPORTS uncovered by D41 (WPD5_REPORT §4 item 3 -- "the one item
# here with a live consequence"). The vocabulary now lives here, next to the
# other two report checks, and `DiscoverChat/causal_gate.py` IMPORTS it. Two
# copies of a word list drift; one copy in the file that gates the reports does
# not.
#
# A verifier can be argued with; a word list cannot. That is the point.
#
# THREE DELIBERATE NON-CATCHES, each measured against the committed reports
# rather than imagined:
#
#   1. A CAUSAL WORD INSIDE A DENIAL is a statement of a LIMIT, not a claim.
#      "The data identifies the timing but not the reason" (executive report,
#      §Ganjam) is exactly the sentence D41 wants written. A ban that fires on
#      it would push the writer away from stating limits.
#
#   2. A REQUEST THAT SOMEBODY ELSE EXPLAIN SOMETHING is a recommended action,
#      not an analytical claim. "Ask each of the 9 districts to explain its
#      unspent recorded sanctions" is the report telling an officer what to do
#      next; five of the fifteen hits on the first scan of the committed
#      reports were this construction, and every one of them was correct prose.
#
#   3. THE DETERMINISTIC READING NOTE is fixed content emitted by
#      `phase5b_report.reading_note_block`, not model prose. `check_vocabulary`
#      already exempts it for the same reason; four more of those fifteen hits
#      were one "therefore" inside one such note, repeated across the gamma
#      editions.
#
# What is left after those three is real, and it is reported rather than
# exempted: a report that says one thing produced another has made a claim this
# analysis cannot support, whatever it was talking about.

CAUSAL_PATTERNS = [
    (r"\bcaus(?:e|es|ed|ing)\b",                    "asserts a cause"),
    (r"\bcausal(?:ly)?\b",                          "asserts a cause"),
    (r"\bdrives?\b|\bdriving\b|\bdriven by\b",      "asserts one thing drives another"),
    (r"\bexplains?\b|\bexplain\b|\bexplained by\b", "asserts one thing explains another"),
    (r"\bleads? to\b|\bled to\b|\bleading to\b",    "asserts one thing leads to another"),
    (r"\bresults? in\b|\bresulted in\b|\bresulting in\b", "asserts a result"),
    (r"\bdue to\b",                                 "attributes a cause"),
    (r"\bbecause of\b|\bbecause\b",                 "attributes a cause"),
    (r"\bowing to\b|\bon account of\b",             "attributes a cause"),
    (r"\bas a result\b|\bconsequently\b|\bthereby\b", "asserts a consequence"),
    (r"\btherefore\b|\bhence\b",                    "asserts a consequence"),
    (r"\bresponsible for\b|\bblame[ds]?\b",         "assigns responsibility for an outcome"),
    (r"\bstems? from\b|\barises? from\b|\bcomes? down to\b", "attributes an origin"),
    (r"\bimpact(?:s|ed|ing)? (?:on )?(?:the )?\w+", "asserts an effect"),
    (r"\baffect(?:s|ed|ing)?\b|\binfluenc(?:e|es|ed|ing)\b", "asserts an effect"),
    (r"\btriggers?\b|\btriggered\b",                "asserts a trigger"),
    (r"\bthe reason\b|\bthe root cause\b|\bwhy this (?:is|happens)\b", "offers a reason"),
]

_CAUSAL_COMPILED = [(re.compile(p, re.IGNORECASE), meaning)
                    for p, meaning in CAUSAL_PATTERNS]

# The association vocabulary that replaces it. Offered on failure so a rewrite
# is told what to say, not only what not to say.
ASSOCIATION_VOCABULARY = (
    "is associated with; occurs alongside; moves together with; is concentrated "
    "in; coincides with; the same places also show; where X is high, Y tends to "
    "be high; the analysis does not establish which way this runs"
)

# Non-catch 1: the denial window.
#
# Bare `not` is in the list, and that is a WIDENING of what WP-D5 shipped, made
# on a measured case. The executive report's "The data identifies the timing but
# not the reason" is a statement of a limit that the old list -- which carried
# `does not`, `do not`, `cannot` and `not able to` but never `not` on its own --
# fired on. Every phrase the old list held already contained `not`, so this
# makes the rule shorter rather than looser. The construction it now also admits
# ("X, not Y, caused the gap") is contrived; the one it stops rejecting is in a
# shipped report.
NEGATION_WINDOW = 60
NEGATIONS_RE = re.compile(
    r"\b(?:not|cannot|can't|doesn't|don't|no way to|unable to|never|without)\b",
    re.IGNORECASE)

# Non-catch 2: a request that somebody else explain something. Two shapes, both
# taken from the committed reports rather than imagined: the recommendation line
# that OPENS with a request verb ("4. Ask each of the 9 districts to explain
# ..."), and the "have <someone> explain" construction buried mid-sentence
# ("Obtain descriptions ... and have Boipariguda explain its allocation").
_REQUEST_VERBS = re.compile(
    r"^\s*(?:[-*>]\s*|\d+[.)]\s*|\*\*\s*)*"
    r"(?:ask|asks|require|requires|request|requests|instruct|instructs|"
    r"direct|directs|press|call on|calls on)\b",
    re.IGNORECASE)
_HAVE_SOMEONE_EXPLAIN = re.compile(
    r"\b(?:have|had|get|gets|got)\s+(?:\*\*)?[A-Z][\w'-]*(?:\s+[\w'-]+){0,3}?"
    r"(?:\*\*)?\s+explain\b")
_EXPLAIN_SURFACE = re.compile(r"^explain(?:s|ed|ing)?$", re.IGNORECASE)


def _is_denied(text: str, start: int) -> bool:
    return bool(NEGATIONS_RE.search(text[max(0, start - NEGATION_WINDOW):start]))


def _sentence_around(text: str, position: int) -> str:
    """The sentence `position` falls in, for the request-verb test."""
    left = max((text.rfind(mark, 0, position) for mark in (". ", "\n", "! ", "? ")),
               default=-1)
    right = min((i for i in (text.find(mark, position)
                             for mark in (". ", "\n", "! ", "? ")) if i != -1),
                default=len(text))
    return text[left + 1:right]


def _is_request_for_explanation(text: str, surface: str, position: int) -> bool:
    if not _EXPLAIN_SURFACE.match(surface):
        return False
    sentence = _sentence_around(text, position)
    return bool(_REQUEST_VERBS.match(sentence)
                or _HAVE_SOMEONE_EXPLAIN.search(sentence))


def scan_causal(text: str) -> list:
    """Every causal construction in `text`, as dicts with surface and meaning.

    One report per surface form, at its first position: a word used three times
    is one thing to fix, not three.
    """
    problems = []
    for pattern, meaning in _CAUSAL_COMPILED:
        for match in pattern.finditer(text or ""):
            if _is_denied(text, match.start()):
                continue
            if _is_request_for_explanation(text, match.group(0), match.start()):
                continue
            problems.append({"surface": match.group(0), "asserts": meaning,
                             "position": match.start()})
    seen, unique = set(), []
    for problem in sorted(problems, key=lambda p: p["position"]):
        key = problem["surface"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(problem)
    return unique


def check_causal(text: str) -> dict:
    problems = scan_causal(text)
    return {"pass": not problems, "problems": problems}


def causal_failure_reason(result: dict) -> str:
    """Plain-English reason, fed back on a regeneration."""
    if result["pass"]:
        return ""
    words = ", ".join(f"'{p['surface']}'" for p in result["problems"])
    return (
        f"It used causal wording: {words}. This analysis finds patterns and "
        f"associations and cannot establish what causes what, so say how things "
        f"go together rather than what produced what. Wording that works: "
        f"{ASSOCIATION_VOCABULARY}."
    )


# =============================================================================
# CHECKS
# =============================================================================

def split_sections(md: str) -> list:
    """The report's "## " sections as (view_name|None, title, [(lineno, text)])."""
    sections = []
    current = None
    for lineno, line in enumerate(md.split("\n"), start=1):
        if line.startswith("## ") and not line.startswith("### "):
            title = line[3:].strip()
            current = (_TITLE_TO_VIEW.get(title), title, [])
            sections.append(current)
        elif current is not None:
            current[2].append((lineno, line))
    return sections


def check_vocabulary(view_name: str, lines: list) -> list:
    """Denied vocabulary in a view's prose. The reading note is exempt: it is
    fixed content, and it names the base rather than the pipeline."""
    rules = VIEW_VOCABULARY.get(view_name)
    if not rules:
        return []

    problems = []
    for lineno, line in lines:
        if line.startswith(">"):
            continue
        for pattern, belongs_to in rules["deny"]:
            hit = re.search(pattern, line, re.IGNORECASE)
            if hit:
                problems.append(
                    f"line {lineno}: {hit.group(0)!r} belongs to {belongs_to}; "
                    f"this view is {rules['pipeline']}\n      {line.strip()[:140]}"
                )
    return problems


def check_reading_note(view_name: str, lines: list) -> list:
    """Exactly the deterministic note, and no model-written rival."""
    problems = []
    body = [line for _, line in lines]

    found = sum(1 for line in body if line.startswith(READING_NOTE_MARKER))
    expected = 1 if view_name in READING_NOTES else 0
    if found != expected:
        problems.append(
            f"{found} deterministic reading note(s), expected {expected}. "
            f"The marker is {READING_NOTE_MARKER!r}; it is emitted by "
            f"phase5b_report.reading_note_block, never by the model."
        )

    for lineno, line in lines:
        if line.startswith(READING_NOTE_MARKER):
            continue
        if _RIVAL_NOTE_RE.match(line):
            problems.append(
                f"line {lineno}: the model wrote its own methodology block -- "
                f"{line.strip()[:100]!r}"
            )
    return problems


def check_causal_lines(lines: list) -> list:
    """The causal-verb ban over a report's prose lines (D41, WP-D6 §D6.2).

    Scanned LINE BY LINE rather than over the whole file, so a position is a
    line number the writer can go to, and so the reading-note exemption is one
    `startswith` rather than an offset calculation.

    The deterministic reading note is skipped for the same reason
    `check_vocabulary` skips it: it is fixed content emitted by
    `phase5b_report.reading_note_block`, not model prose, and this gate exists to
    check what the model wrote. One "therefore" inside one such note accounted
    for four of the fifteen hits on the first scan of the committed reports.
    """
    problems = []
    for lineno, line in lines:
        if line.startswith(">"):
            continue
        for problem in scan_causal(line):
            problems.append(
                f"line {lineno}: {problem['surface']!r} {problem['asserts']} "
                f"(D41: correlations only)\n      {line.strip()[:140]}"
                f"\n      instead: {ASSOCIATION_VOCABULARY}"
            )
    return problems


def check_report(path: str) -> list:
    """All findings for one report file, as printable strings."""
    with open(path, encoding="utf-8") as f:
        md = f.read()

    problems = []
    seen_views = set()
    for view_name, title, lines in split_sections(md):
        if view_name is None:
            continue
        seen_views.add(view_name)
        for problem in check_vocabulary(view_name, lines):
            problems.append(f"  [{title}] {problem}")
        for problem in check_reading_note(view_name, lines):
            problems.append(f"  [{title}] {problem}")

    # THE CAUSAL BAN RUNS OVER THE WHOLE FILE, not per view section, and that is
    # not a convenience. The vocabulary and reading-note checks are per-view by
    # nature -- they are about a view's own words and its own note -- but a
    # causal claim is the same claim wherever it sits, and the places it most
    # wants to sit are exactly the ones no view section covers: the executive
    # summary, the headline, the recommendation list, and any file (like
    # global_feed.md) whose headings are not view titles at all. Scanning
    # per-section would have left every one of those unchecked.
    #
    # Operator decision, 2026-09-01: DEFAULT-ON, over the committed reports as
    # they stand, in the knowledge that some of them go red.
    for problem in check_causal_lines(list(enumerate(md.split("\n"), start=1))):
        problems.append(f"  [D41] {problem}")

    for view_name in READING_NOTES:
        if view_name not in seen_views:
            problems.append(
                f"  [{VIEW_DESCRIPTIONS[view_name]['title']}] section is missing "
                f"from the report, so its reading note is missing too"
            )
    return problems


def main(paths: list) -> int:
    if not paths:
        raise SystemExit("usage: python src/prose_gate.py <report.md> [report.md ...]")

    failed = 0
    for path in paths:
        problems = check_report(path)
        if problems:
            failed += 1
            print(f"FAIL {os.path.basename(path)} -- {len(problems)} problem(s)")
            for problem in problems:
                print(problem)
        else:
            print(f"PASS {os.path.basename(path)}")
    print(f"\n{len(paths) - failed}/{len(paths)} report(s) clean.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

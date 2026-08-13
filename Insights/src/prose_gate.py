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

"""WP-6 T2: the hand edits M1 could not make mechanically. One-shot, reviewed.

    python tools/migrations/m1_hand_edits.py

M1 (`m1_universal_slots.py`) injects the universal filters wherever a SELECT
reading an activity view has an insertion point. These templates have none — the
activity read sits inside a NOT EXISTS against the GP roster, or in a correlated
subquery under a plan row — so each is edited here, by hand, one statement at a
time, and recorded as a hand edit rather than a scripted one.

Every edit keeps the D2 idiom, so with the new slots absent each statement is
unchanged; `validate_catalog.py` proves it against the Test Report counts.

TWO TEMPLATES DELIBERATELY GET NO ACTIVITY FILTERS — ALR-012 and ALR-013. Their
question is "which GPs have NO data at all, in any module" (activities,
vouchers, and for ALR-013 plans). A filter on the activity side alone would
narrow one module of three and answer a question nobody asked ("no ongoing
activities AND no vouchers of any kind").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402


def _pred(indent: str, alias: str, slot: str, column: str) -> str:
    return f"{indent}AND (${slot} IS NULL OR {alias}.{column} = ${slot})"


COLUMN = {"plan_type": "plan_type", "status": "status_label",
          "focus_area": "focus_area_name", "theme": "theme",
          "scheme": "scheme_name", "tied_untied": "tied_untied"}
ETYPE = {"plan_type": "plan_type", "status": "status", "focus_area": "focus_area",
         "theme": "theme", "scheme": "scheme", "tied_untied": "tied_untied"}


def inside_not_exists(anchor_line: str, slots: list[str]) -> tuple[str, str]:
    """Rewrite the closing predicate of a NOT EXISTS so the new ones follow it.

    `          AND v.theme = $theme)` -> the same line without its `)`, then one
    line per slot, the last carrying the `)`.
    """
    indent = anchor_line[:len(anchor_line) - len(anchor_line.lstrip())]
    body = anchor_line.rstrip()
    assert body.endswith(")"), anchor_line
    lines = [body[:-1]] + [_pred(indent, "v", s, COLUMN[s]) for s in slots]
    lines[-1] += ")"
    return anchor_line, "\n".join(lines)


GP_RUN_V = "  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)"

EDITS = {
    # Plan-status lookups: plan type is a property of the plan row itself.
    "PLN-012": ([(GP_RUN_V, GP_RUN_V + "\n" + _pred("  ", "v", "plan_type", "plan_type"))],
                ["plan_type"]),
    "PLU-001": ([(GP_RUN_V, GP_RUN_V + "\n" + _pred("  ", "v", "plan_type", "plan_type"))],
                ["plan_type"]),
    "ALR-009": ([("  AND ($block_name    IS NULL OR p.block_name    = $block_name)",
                  "  AND ($block_name    IS NULL OR p.block_name    = $block_name)\n"
                  + _pred("  ", "p", "plan_type", "plan_type"))],
                ["plan_type"]),
    # Roster shapes: the filters belong INSIDE the NOT EXISTS, so "no activity
    # under X" becomes "no activity under X matching the filters". The subject
    # slot of each (theme / focus area / scheme) is left as it is; PLN-032's
    # theme is relaxed separately in WP-6 T5 (operator ruling 2026-09-12).
    "PLN-032": ([inside_not_exists("          AND v.theme = $theme)",
                                   ["plan_type", "status", "scheme", "tied_untied"])],
                ["plan_type", "status", "scheme", "tied_untied"]),
    "PLN-059": ([inside_not_exists("          AND v.focus_area_name = $focus_area)",
                                   ["plan_type", "status", "scheme", "tied_untied"])],
                ["plan_type", "status", "scheme", "tied_untied"]),
    "SCH-006": ([inside_not_exists("          AND v.scheme_name = $scheme)",
                                   ["plan_type", "status", "focus_area", "theme",
                                    "tied_untied"])],
                ["plan_type", "status", "focus_area", "theme", "tied_untied"]),
    "AST-009": ([inside_not_exists("          AND v.asset_category_label <> 'Uncategorised')",
                                   ["plan_type", "status", "focus_area", "theme"])],
                ["plan_type", "status", "focus_area", "theme"]),
}


def main() -> int:
    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))
    for qid, (pairs, slots) in EDITS.items():
        lines = source.split("\n")
        spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
        start, end = spans[qid]
        head, entry, tail = ("\n".join(lines[:start]), "\n".join(lines[start:end + 1]),
                             "\n".join(lines[end + 1:]))
        for old, new in pairs:
            assert entry.count(old) == 1, f"{qid}: {entry.count(old)}x {old!r}"
            entry = entry.replace(old, new)
        closer = entry.index('        "param_slots": [')
        slots_end = entry.index("\n        ],", closer)
        entry = (entry[:slots_end]
                 + "".join(f"\n            {dc.py({'name': s, 'entity_type': ETYPE[s], 'optional': True})},"
                           for s in slots)
                 + entry[slots_end:])
        source = head + "\n" + entry + "\n" + tail
        for slot in slots:
            oracle[qid]["params"][slot] = None
        print(f"HAND   {qid:<10} + " + ", ".join(f"${s}" for s in slots))
    dc.TEMPLATE_PATH.write_text(source, encoding="utf-8")
    dc.ORACLE_PATH.write_text(json.dumps(oracle, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    print("NONE   ALR-012, ALR-013 — 'no data in any module'; see the docstring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

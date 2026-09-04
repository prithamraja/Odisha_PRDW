#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D9 D9.1 — the 15 narratives side by side, old judge vs new judge.

    python DiscoverChat/experiments/build_judge_narratives.py

NOT the same comparison `run_answer_compare.py` prints. That script's two arms
are whole SERVICE configurations (pre-D7 vs D7). This one holds the service
fixed -- same writer, same writer prompt, same model ids -- and varies only the
judge instruction, which is the single variable WP-D9 changes.

It reads two `--only new` runs that were saved side by side rather than
re-running anything: the narratives are expensive and already paid for.

The operator reads this file. Nothing here scores prose (D7's rule: narrative
quality is the operator's acceptance, not a suite's); it prints what the judge
kept, what the writer made of it, and the mechanical checks, and stops.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE / "answer_compare_BASELINE_minimal_newwriter.json"
NEW = HERE / "answer_compare_D91_complete.json"
OUT = HERE / "WPD9_narratives_side_by_side.md"


def rows(path: Path) -> dict:
    payload = json.load(io.open(path, encoding="utf-8"))
    return {r["question"]: r for r in payload["results"]["new"]}


def fmt(row) -> str:
    if row is None:
        return "_(not in this run)_"
    if not row.get("text"):
        return "_(no findings kept — nothing written)_"
    prose = row.get("prose") or {}
    flag = " **[fell back to bare sentences]**" if prose.get("fell_back") else ""
    return f"{row['text'].strip()}{flag}"


def main() -> int:
    for p in (OLD, NEW):
        if not p.exists():
            print(f"missing run file: {p}", file=sys.stderr)
            return 1
    old, new = rows(OLD), rows(NEW)

    lines = [
        "# WP-D9 D9.1 — the 15 narratives, old judge instruction vs new",
        "",
        "Same writer, same writer prompt, same model ids, same questions. The",
        "**only** difference between the columns is the judge's instruction:",
        "the left keeps the smallest sufficient set, the right keeps every",
        "finding that adds distinct information.",
        "",
        "`ANSWER_CAP` is 20 in the right-hand column and 12 in the left. Neither",
        "column binds against it (see the report's matrix), so the cap is not",
        "what is moving these answers — the instruction is.",
        "",
        "**This file is for reading, not for scoring.** Narrative quality is the",
        "operator's acceptance (the D7 rule); the mechanical checks are in the",
        "report's matrix.",
        "",
        "---",
        "",
    ]

    for i, question in enumerate(
            [r["question"] for r in json.load(
                io.open(NEW, encoding="utf-8"))["results"]["new"]], start=1):
        o, n = old.get(question), new.get(question)
        lines += [
            f"## {i}. {question}",
            "",
            f"| | old judge (`minimal`) | new judge (`complete`) |",
            f"|---|---:|---:|",
            f"| findings kept | {o['n_findings'] if o else '—'} "
            f"| {n['n_findings'] if n else '—'} |",
            f"| seconds | {o['seconds'] if o else '—'} "
            f"| {n['seconds'] if n else '—'} |",
            f"| numerals bound | "
            f"{(str(o.get('numerals_bound')) + '/' + str(o.get('numerals_total'))) if o else '—'} "
            f"| {(str(n.get('numerals_bound')) + '/' + str(n.get('numerals_total'))) if n else '—'} |",
            "",
            "**old judge —**",
            "",
            fmt(o),
            "",
            "**new judge —**",
            "",
            fmt(n),
            "",
            "---",
            "",
        ]

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print(f"  written to {OUT}")
    print(f"  {len(new)} questions, {sum(1 for r in new.values() if r.get('text'))} "
          f"with prose")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""WP-D5 D5.1 — the operator labelling sheet.

The brief asks the operator to label the FULL set of relevant findings per
question, not just the top hit, so that a broad question gets a measurable
recall rather than a top-1 check. This emits that sheet.

Two properties it is built to have:

**Arm-blind.** Every candidate is POOLED across the three arms and sorted by
finding id, not by any arm's score, and the sheet never says which arm found
what. A sheet ordered by the hybrid arm's ranking would collect labels that
agree with the hybrid arm.

**Complete enough to be a recall denominator.** Everything any arm put above a
generous collection floor is listed, so a finding no arm ranked highly can still
be marked relevant — which is the only way a miss becomes visible.

Run:  python DiscoverChat/experiments/label_sheet.py
Out:  DiscoverChat/experiments/LABEL_SHEET.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from DiscoverChat import corpus as corpus_mod          # noqa: E402

RESULTS = HERE / "arm_results.json"
OUT = HERE / "LABEL_SHEET.md"

# Generous on purpose: the sheet is a recall denominator, not an answer.
COLLECT_FLOOR = 0.55
MAX_PER_QUESTION = 25


def main() -> int:
    corpus = corpus_mod.load()
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

    kinds_to_label = {"vague", "open", "why"}
    lines = [
        "# WP-D5 D5.1 — operator labelling sheet",
        "",
        f"Corpus `{payload['candidate_set_id']}`, {payload['corpus_records']:,} "
        f"findings. Generated from `arm_results.json`.",
        "",
        "## What to do",
        "",
        "For each question below, mark **every** finding that a senior officer "
        "asking it would count as part of a good answer — not just the best one. "
        "The count matters: a broad question whose honest answer is six findings "
        "should be scored against six, and a question the analysis has nothing "
        "useful for should end up with none ticked, which is a real and useful "
        "label.",
        "",
        "Write `R` (relevant), `-` (not relevant) or `?` in the box. A `?` is "
        "read as not-relevant when the numbers are computed, and is flagged "
        "separately so it can be discussed.",
        "",
        "The candidates are **pooled across all three retrieval arms and sorted "
        "by finding id**, so the ordering carries no hint about which arm found "
        "what. Nothing here is the system's answer; it is the pool the answer "
        "will be scored against.",
        "",
        "The three other question kinds — place questions, measure questions "
        "and out-of-scope questions — are scored mechanically against the "
        "corpus itself and need no labels. They are listed at the end for "
        "reference only.",
        "",
    ]

    by_kind = {}
    for q in questions["questions"]:
        by_kind.setdefault(q["kind"], []).append(q)

    for kind in ("vague", "open", "why"):
        lines += [f"## {kind.title()} questions", ""]
        for q in by_kind.get(kind, []):
            row = next(r for r in payload["questions"] if r["id"] == q["id"])
            pooled = {}
            for arm_hits in row["arms"].values():
                for hit in arm_hits:
                    if hit["score"] >= COLLECT_FLOOR:
                        pooled[hit["id"]] = max(pooled.get(hit["id"], 0), 1)
            ids = sorted(pooled)[:MAX_PER_QUESTION]

            lines += [f"### {q['id']} — {q['text']}", ""]
            if kind == "why":
                lines += [
                    "*A 'why' question is never answered from the corpus "
                    "(D41: correlations only). It is here so the reframe can be "
                    "judged at D5.3; label the findings the reframe should "
                    "legitimately POINT AT.*", "",
                ]
            if not ids:
                lines += ["*No candidate cleared the collection floor. If that "
                          "is wrong, say which finding is missing.*", ""]
                continue
            lines += ["| ? | finding | coverage | sentence |",
                      "|---|---|---|---|"]
            for fid in ids:
                finding = corpus.get(fid)
                sentence = finding.sentence.replace("|", "\\|")
                lines.append(f"|   | `{fid}` | {finding.coverage_line()} | "
                             f"{sentence} |")
            lines.append("")

    lines += ["---", "", "## Mechanically scored — reference only, no labels needed", ""]
    for kind in ("geo", "measure", "none"):
        lines.append(f"**{kind}** ({len(by_kind.get(kind, []))} questions): "
                     + "; ".join(q["text"] for q in by_kind.get(kind, [])[:4])
                     + " ...")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    n = sum(len(by_kind.get(k, [])) for k in kinds_to_label)
    print(f"  wrote {OUT} — {n} questions needing labels")
    return 0


if __name__ == "__main__":
    sys.exit(main())

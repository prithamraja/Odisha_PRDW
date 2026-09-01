#!/usr/bin/env python
"""WP-D5 D5.2 — measure the writer's safety net on real turns.

The gate proves the deterministic behaviours. This measures the one thing the
gate deliberately does not depend on: how the free writer actually behaves under
the net, and how often the ratified two-attempts-then-fall-back rule fires.

What it reports per turn: which check failed on which attempt, the verifier's
verdict, and whether the answer fell back. What it is FOR: the numbers that go
in the report, so the fallback rate is a measurement rather than an impression,
and so the D5.3 operator gate knows what it is looking at.

Run:  python DiscoverChat/experiments/measure_prose.py
Out:  DiscoverChat/experiments/prose_measurements.json
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import assemble, config, writer as writer_mod   # noqa: E402
from DiscoverChat.retrieval import Retriever                       # noqa: E402

OUT = HERE / "prose_measurements.json"

# Turns that actually reach the writer: broad enough to clear FULL_RENDER_MAX.
TURNS = [
    "Is spending on track?",
    "Which places are behaving differently from the rest?",
    "Where is money planned but not spent?",
    "What should I raise at the next review meeting?",
    "Is money moving steadily or in year-end bursts?",
    "Anything worth my attention this quarter?",
    "How is GPDP implementation going under XV FC?",
    "What does the analysis say about photo evidence?",
]


def main() -> int:
    retriever = Retriever()
    assembler = assemble.Assembler(retriever, allow_model=True)

    records = []
    for i, question in enumerate(TURNS, start=1):
        result = retriever.score(question)
        findings = [h.finding for h in result.hits]
        if len(findings) <= config.FULL_RENDER_MAX:
            records.append({"question": question, "findings": len(findings),
                            "reached_writer": False,
                            "note": "rendered directly; too few findings to "
                                    "need connective prose"})
            print(f"  {i}/{len(TURNS)} {question[:44]:<44} "
                  f"{len(findings)} findings, no writer")
            continue

        prose = writer_mod.write(question, findings,
                                 corpus_roster=assembler._roster,
                                 turn_id=f"measure-{i}", fallback="")
        per_attempt = []
        for n, check_result in enumerate(prose.check_results, start=1):
            failed = [k for k, v in check_result.items()
                      if k != "all_pass" and not v["pass"]]
            per_attempt.append({
                "attempt": n, "checks_failed": failed,
                "causal_words": [p["surface"] for p in
                                 check_result["e_causal"]["problems"]],
                "sentences": check_result["d_shape"]["sentences"],
                "words": check_result["d_shape"]["words"],
                "numerals_checked": check_result["a_numerals"]["checked"],
                "numerals_unsupported": check_result["a_numerals"]["unsupported"],
            })
        records.append({
            "question": question, "findings": len(findings),
            "reached_writer": True,
            "fell_back": prose.fell_back, "attempts": prose.attempts,
            "attempt_detail": per_attempt,
            "verdicts": [v.get("verdict") for v in prose.verdicts],
            "final_reason": prose.reason[:400],
            "prose": prose.text,
        })
        print(f"  {i}/{len(TURNS)} {question[:44]:<44} "
              f"{len(findings)} findings, fell_back={prose.fell_back}, "
              f"attempts={prose.attempts}")

    reached = [r for r in records if r.get("reached_writer")]
    fell_back = [r for r in reached if r["fell_back"]]
    invented_numbers = sum(
        len(a["numerals_unsupported"]) for r in reached
        for a in r["attempt_detail"])
    numerals_checked = sum(
        a["numerals_checked"] for r in reached for a in r["attempt_detail"])
    causal_attempts = sum(
        1 for r in reached for a in r["attempt_detail"] if a["causal_words"])
    total_attempts = sum(len(r["attempt_detail"]) for r in reached)

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "writer_model": config.WRITER_MODEL,
        "verifier_model": config.VERIFIER_MODEL,
        "turns": len(TURNS),
        "reached_writer": len(reached),
        "fell_back": len(fell_back),
        "writer_attempts": total_attempts,
        "attempts_with_causal_wording": causal_attempts,
        "numerals_checked": numerals_checked,
        "numerals_invented": invented_numbers,
    }
    OUT.write_text(json.dumps({"summary": summary, "turns": records}, indent=1),
                   encoding="utf-8")

    print(f"\n  reached the writer: {len(reached)}/{len(TURNS)}")
    print(f"  fell back to bare sentences: {len(fell_back)}/{len(reached)}")
    print(f"  numerals written {numerals_checked}, invented {invented_numbers}")
    print(f"  attempts using causal wording: {causal_attempts}/{total_attempts}")
    print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

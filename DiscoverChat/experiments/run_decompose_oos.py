#!/usr/bin/env python
"""WP-D6 D6.1 — does the judge still refuse out-of-scope questions with the
decomposition sidecar loaded?

WHY THIS HAD TO BE MEASURED
---------------------------
WP-D5 §2.4a established the one number that matters -- the false-answer rate on
questions the analysis holds nothing about -- and established it at 0.0% over
four independent runs. That evidence was gathered over 4,239 findings.

D6 adds 36,218 decompositions, and they are not neutral for this: a depth-1
decomposition NAMES ITS SLICE in its opening clause ("Within district Cuttack,
planned cost totals ..."), so every place-naming question now has thousands of
short, place-led records to be close to, whatever the question is actually
about. Measured on the threshold path, "What is the price of onions in Cuttack
market?" reaches cosine 0.6256 against such a record -- above the 0.62 floor on
cosine alone, before any structural boost -- where the same question reached
0.488 over findings alone.

So the threshold path's out-of-scope guarantee is weaker than it was, by
construction and not by accident. Production does not run the threshold path;
it runs the judge. Whether the JUDGE still refuses is a different question and
the only one that decides whether this is safe, and it cannot be reasoned out
from the above -- it has to be run.

    python DiscoverChat/experiments/run_decompose_oos.py [--repeats 4]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import assemble, classifier, config, judge   # noqa: E402
from DiscoverChat.retrieval import Retriever            # noqa: E402

OUT = HERE / "decompose_oos_results.json"

# The five WP-D5 used, unchanged, so the number is comparable to its 0.0%.
OUT_OF_SCOPE = [
    "What is the price of onions in Cuttack market?",
    "What is the rainfall forecast for Koraput next week?",
    "How many teachers are posted in the block primary schools?",
    "Give me the list of pending court cases against the panchayat.",
    "Who is the current Sarpanch of Chikilli?",
]

# In-scope controls. A guard that refuses everything is not a guard, it is an
# outage, so the same run has to show the decompose questions still answered.
IN_SCOPE = [
    "Where does the gap sit?",
    "Which blocks account for the shortfall?",
    "Break down spending by block",
    "How is Chikilli doing?",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=4)
    args = ap.parse_args(argv)

    retriever = Retriever()
    corpus = retriever.corpus
    assembler = assemble.Assembler(retriever, allow_model=True)
    print(f"  corpus: {corpus.meta['findings']:,} findings + "
          f"{corpus.meta['decompositions']:,} decompositions")
    print(f"  judge: {config.JUDGE_MODEL}  floor {config.CANDIDATE_FLOOR} "
          f"pool {config.CANDIDATE_POOL}\n")

    rows, answered, runs = [], 0, 0
    t0 = time.time()
    for run in range(args.repeats):
        for question in OUT_OF_SCOPE:
            answer = assembler.answer(question)
            judged = answer.retrieval.get("judge", {})
            declined = (answer.move == classifier.LOOKUP) or not answer.findings
            runs += 1
            answered += 0 if declined else 1
            n_dec = sum(1 for f in answer.findings if f.is_decomposition)
            rows.append({"run": run, "kind": "out_of_scope", "q": question,
                         "move": answer.move, "shown": len(answer.findings),
                         "decompositions_shown": n_dec,
                         "pool": judged.get("pool"),
                         "judge_source": judged.get("source")})
            print(f"  [{run}] {'REFUSED ' if declined else '*ANSWERED*'} "
                  f"shown={len(answer.findings):2} ({n_dec} decomp) "
                  f"pool={judged.get('pool', '-')} {question[:46]}")

    for question in IN_SCOPE:
        answer = assembler.answer(question)
        judged = answer.retrieval.get("judge", {})
        n_dec = sum(1 for f in answer.findings if f.is_decomposition)
        rows.append({"run": 0, "kind": "in_scope", "q": question,
                     "move": answer.move, "shown": len(answer.findings),
                     "decompositions_shown": n_dec,
                     "pool": judged.get("pool"),
                     "judge_source": judged.get("source")})
        print(f"  [control] {answer.move:10} shown={len(answer.findings):2} "
              f"({n_dec} decomp) {question[:46]}")

    rate = answered / runs if runs else 0.0
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "judge_model": config.JUDGE_MODEL,
        # WP-D9: the wording is evidence too, not just the id.
        "judge_prompt_variant": config.JUDGE_PROMPT_VARIANT,
        "judge_prompt_sha256": judge.prompt_sha256(),
        "candidate_floor": config.CANDIDATE_FLOOR,
        "candidate_pool": config.CANDIDATE_POOL,
        "corpus": {"findings": corpus.meta["findings"],
                   "decompositions": corpus.meta["decompositions"]},
        "repeats": args.repeats,
        "out_of_scope_runs": runs,
        "out_of_scope_answered": answered,
        "false_answer_rate": round(rate, 4),
        "elapsed_seconds": round(time.time() - t0, 1),
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\n  FALSE ANSWER RATE {rate:.1%} over {runs} runs "
          f"(WP-D5 arm D, findings only: 0.0%)")
    print(f"  wrote {OUT}")
    return 0 if answered == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

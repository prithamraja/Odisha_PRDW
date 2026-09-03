#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D7 D7.0 — qualifying a nano classifier, four independent times.

    python DiscoverChat/experiments/run_classifier_nano.py
    python DiscoverChat/experiments/run_classifier_nano.py --repeats 4
    DISCOVERCHAT_CLASSIFIER_MODEL=gpt-5.5 python .../run_classifier_nano.py

THE GATE HAS TO EXERCISE THE MODEL, AND THE OBVIOUS VERSION OF IT DOES NOT.
All 22 questions in the routing suite are caught by the RULE layer — that is the
point of the rule layer, and D7.0 leaves it unchanged. So a gate that only ran
those 22 end to end would make zero calls to the classifier and come back green
on a model that returns nothing at all. That is not a hypothetical: it is
exactly how Ask's F1 hid for a whole work package, a small model returning
all-null structured output on ~25% of calls while every caller read the null as
"no verdict" and fell through to a safe default.

So this runs three passes, and each proves something the others cannot:

  A  ROUTING, END TO END, rules included, with the nano configured. Proves the
     model swap changed no route an officer can reach. Deterministic; it is the
     brief's 8/8, 6/6, 6/6, 2/2, and it is repeated because "deterministic"
     should be demonstrated rather than asserted.

  B  THE SAME 22, MODEL-FORCED, rules bypassed. Proves the model is alive,
     answers in the shape asked for, and is not returning nulls. Agreement with
     the rule labels is REPORTED, NOT GATED — production never asks the model
     these, the rules answer first, and failing the gate on a disagreement that
     no officer can reach would be gating on a number that means nothing.

  C  THE QUESTIONS THE RULES ACTUALLY MISS — the classifier's real production
     job. Selected by asking the rule layer which of a wider set it does not
     match, so the list cannot drift out of date as rules are added. Non-empty
     output is gated; the routes themselves are reported with their stability
     across runs, because routing is nondeterministic (~3% flip on identical
     replays, per the bootstrap) and a gate that pinned them would go red for
     reasons nobody changed.

GATE CONDITION, and it is only these two things:
  1. Pass A green on every repeat.
  2. ZERO empty or unparseable classifications across every call in B and C.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from DiscoverChat import classifier, config                       # noqa: E402
from DiscoverChat.gates import (                                  # noqa: E402
    DECOMPOSE_QUESTIONS, LOOKUP_QUESTIONS, NO_MATCH_QUESTIONS, WHY_QUESTIONS,
)

OUT_PATH = config.HERE / "experiments" / "classifier_nano_results.json"

# The two "shape" questions the brief counts separately: a question about a
# SHAPE keeps the D41 reframe where a question about a SUM goes to decompose.
# Taken from `gates._decompose_vs_why`, which is where they were first written.
SHAPE_QUESTIONS = ["What is causing the year-end payment spike?",
                   "What is driving the change in status?"]

# The brief's routing suite: 8 + 6 + 6 + 2 = 22.
SUITE = ([(q, classifier.DECOMPOSE) for q in DECOMPOSE_QUESTIONS]
         + [(q, classifier.WHY) for q in WHY_QUESTIONS]
         + [(q, classifier.LOOKUP) for q in LOOKUP_QUESTIONS]
         + [(q, classifier.WHY) for q in SHAPE_QUESTIONS])

# Candidates for pass C. Only those the RULE LAYER MISSES are used, computed
# below, so adding a rule removes a question from here automatically rather
# than leaving the pass quietly testing something the rules now answer.
FALLTHROUGH_CANDIDATES = NO_MATCH_QUESTIONS + [
    "How is Chikilli doing?",
    "Is spending on track?",
    "Where is money planned but not spent?",
    "How is Barpali block doing?",
    "Which places are behaving differently from the rest?",
    "Anything I should be looking at in Ganjam?",
    "Tell me about untied grants.",
    "What about the other blocks?",
]
FALLTHROUGH = [q for q in FALLTHROUGH_CANDIDATES
               if classifier.rule_route(q) is None]


def _pass_a(run: int) -> dict:
    """End to end, rules included. The brief's 8/8, 6/6, 6/6, 2/2."""
    by_family, failures = {}, []
    for question, expected in SUITE:
        routing = classifier.classify(question, turn_id=f"d70-a{run}")
        family = expected
        got = routing.move
        # A shape question is counted in the why family; both are WHY.
        by_family.setdefault(family, [0, 0])
        by_family[family][1] += 1
        if got == expected:
            by_family[family][0] += 1
        else:
            failures.append({"question": question, "expected": expected,
                             "got": got, "source": routing.source,
                             "reason": routing.reason})
    return {"run": run,
            "by_family": {k: f"{v[0]}/{v[1]}" for k, v in by_family.items()},
            "green": not failures, "failures": failures}


def _model_call(question: str, run: int, tag: str) -> dict:
    started = time.time()
    routing = classifier.classify(question, turn_id=f"d70-{tag}{run}",
                                  allow_rules=False)
    return {"question": question, "move": routing.move,
            "source": routing.source, "reason": routing.reason,
            "model_empty": routing.model_empty,
            "model_unparseable": routing.model_unparseable,
            "raw": routing.raw[:160],
            "seconds": round(time.time() - started, 1)}


def _pass_b(run: int) -> list:
    out = []
    for question, expected in SUITE:
        call = _model_call(question, run, "b")
        call["rule_label"] = expected
        call["agrees_with_rule"] = (call["move"] == expected)
        out.append(call)
    return out


def _pass_c(run: int) -> list:
    return [_model_call(q, run, "c") for q in FALLTHROUGH]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="WP-D7 D7.0 classifier gate")
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--out", default=str(OUT_PATH))
    args = parser.parse_args(argv)

    print(f"  WP-D7 D7.0 — classifier gate on {config.CLASSIFIER_MODEL}")
    print(f"  budget {config.CLASSIFIER_MAX_COMPLETION} completion tokens")
    print(f"  {len(SUITE)} suite questions, {len(FALLTHROUGH)} rule-miss "
          f"questions, {args.repeats} independent runs\n")

    runs_a, runs_b, runs_c = [], [], []
    for run in range(1, args.repeats + 1):
        a = _pass_a(run)
        runs_a.append(a)
        print(f"  run {run}  A routing  "
              + "  ".join(f"{k} {v}" for k, v in sorted(a["by_family"].items()))
              + ("  GREEN" if a["green"] else "  RED"))
        b = _pass_b(run)
        runs_b.append(b)
        c = _pass_c(run)
        runs_c.append(c)
        nulls = sum(1 for call in b + c
                    if call["model_empty"] or call["model_unparseable"])
        agree = sum(1 for call in b if call["agrees_with_rule"])
        print(f"  run {run}  B model-forced {agree}/{len(b)} agree with rules "
              f"| C rule-miss {len(c)} routed | nulls {nulls}")

    every_call = [call for run in runs_b for call in run] + \
                 [call for run in runs_c for call in run]
    empties = [c for c in every_call if c["model_empty"]]
    unparseable = [c for c in every_call if c["model_unparseable"]]
    seconds = [c["seconds"] for c in every_call]

    # Pass C stability: the same question across runs, how many distinct routes.
    stability = {}
    for question in FALLTHROUGH:
        moves = [call["move"] for run in runs_c for call in run
                 if call["question"] == question]
        stability[question] = {"routes": sorted(set(moves)),
                               "stable": len(set(moves)) == 1, "seen": moves}

    green_a = all(a["green"] for a in runs_a)
    no_nulls = not (empties or unparseable)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "classifier_model": config.CLASSIFIER_MODEL,
        "classifier_max_completion": config.CLASSIFIER_MAX_COMPLETION,
        "repeats": args.repeats,
        "suite_size": len(SUITE),
        "fallthrough_size": len(FALLTHROUGH),
        "gate": {
            "routing_green_every_run": green_a,
            "zero_null_classifications": no_nulls,
            "passed": green_a and no_nulls,
        },
        "calls_to_the_model": len(every_call),
        "empty_replies": len(empties),
        "unparseable_replies": len(unparseable),
        "median_seconds": statistics.median(seconds) if seconds else 0.0,
        "p90_seconds": (sorted(seconds)[max(0, int(len(seconds) * 0.9) - 1)]
                        if seconds else 0.0),
        "pass_a_routing": runs_a,
        "pass_b_model_forced": runs_b,
        "pass_c_rule_miss": runs_c,
        "pass_c_stability": stability,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"\n  {len(every_call)} calls to {config.CLASSIFIER_MODEL}: "
          f"{len(empties)} empty, {len(unparseable)} unparseable, "
          f"median {report['median_seconds']}s, p90 {report['p90_seconds']}s")
    print(f"  A routing green every run: {green_a}")
    print(f"  zero null classifications:  {no_nulls}")
    print(f"\n  GATE D7.0 {'PASS' if report['gate']['passed'] else 'FAIL'}")
    print(f"  written to {args.out}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

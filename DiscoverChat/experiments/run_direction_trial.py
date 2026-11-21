#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D13 Fix 1 T3 -- the direction check, measured live before it blocks.

    python DiscoverChat/experiments/run_direction_trial.py

THE QUESTION. Step 5 of `checks.check_citations` (R1: a negative signed figure
must say "below plan") is strict, and a correct sentence in other words --
"Rs 98.42 lakh of this shortfall", "under plan" -- fails it. How often the
writer does that is a fact about the writer model, so it is measured here
before the check is allowed to throw an answer away.

THE DESIGN (brief §1.5).
  * Twelve questions whose answers cite signed records. Chosen from the
    recorded question sets in this folder by their RETRIEVAL POOLS (no model:
    the query embedding only) -- the recorded answers predate the current
    corpus, so which of them cited a signed record then says little about now.
    Ranked by signed records in the top 20 of the pool; "why" questions (they
    get a reframe, not a written answer) and a context-dependent follow-up
    ("What about the other blocks?") skipped; "What should I know about
    Cuttack?" added, as the brief requires.
  * Retrieval and the judge ONCE per question (`Assembler._retrieve`, the
    production path; the classifier is not called -- it does not change what is
    retrieved, and its call would buy nothing here).
  * Then `writer.consolidate` -- the production function, unmodified -- on the
    same findings twice: once with DISCOVERCHAT_DIRECTION_CHECK=log, once with
    block. Parallel within each arm; the arms run one after the other because
    the mode is a module setting read at call time.
  * "Before" for the Cuttack question: the writer handed the PRE-FIX display
    sentences ("Rs -3.18 crore", the sign-convention sentence kept) with the
    direction step off -- what the service did before Fix 1.
  * Every model call counted and costed; hard cap 80.

Output: DiscoverChat/experiments/direction_trial_results.json. The
classification of each direction failure (true catch / false alarm) is made by
hand afterwards and recorded in handoffs/WPD13_REPORT.md, with every failing
sentence, so the operator can overrule it.
"""
from __future__ import annotations

import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import (assemble, checks, config, glossary, llm,      # noqa: E402
                          writer as writer_mod)
from DiscoverChat import corpus as corpus_mod                            # noqa: E402
from DiscoverChat.retrieval import Retriever                             # noqa: E402
from phase5f_decompose import _SIGNED_DIRECTION                          # noqa: E402

OUT = config.HERE / "experiments" / "direction_trial_results.json"

QUESTIONS = [
    "Is spending on track?",
    "What makes up the underspend?",
    "What should I raise at the next review meeting?",
    "Where does the gap sit?",
    "Which blocks account for the shortfall?",
    "Which places are behaving differently from the rest?",
    "Who is driving the shortfall?",
    "Where is money planned but not spent?",
    "Anything worth my attention this quarter?",
    "How is Barpali block doing?",
    "Anything I should be looking at in Ganjam?",
    "What should I know about Cuttack?",
]
CUTTACK = "What should I know about Cuttack?"
CAP = 80

# USD per 1M tokens (input, output). gpt-5.6-sol at its promotional price,
# recorded as running through at least 2026-11-21 -- the day of this run.
PRICES = {"gpt-5.6-sol": (4.0, 20.0)}

# ── every model call, counted and costed ─────────────────────────────────────
_real_call = llm.call
_lock = threading.Lock()
CALLS = []


def _counted(model, prompt, max_completion, purpose, *, turn_id=None,
             attempt=None):
    with _lock:
        if len(CALLS) >= CAP:
            raise RuntimeError(f"model-call cap of {CAP} reached")
        slot = len(CALLS)
        CALLS.append(None)
    record = _real_call(model, prompt, max_completion, purpose,
                        turn_id=turn_id, attempt=attempt)
    usage = record["usage"]
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    cost = (usage["prompt_tokens"] * price_in
            + usage["completion_tokens"] * price_out) / 1e6
    with _lock:
        CALLS[slot] = {"model": model, "purpose": purpose, "turn_id": turn_id,
                       "attempt": attempt, "seconds": record["seconds"],
                       "prompt_tokens": usage["prompt_tokens"],
                       "completion_tokens": usage["completion_tokens"],
                       "usd": round(cost, 5),
                       "response_text": record["response_text"]}
    return record


llm.call = _counted


def _signed(finding) -> bool:
    return (finding.is_decomposition
            and finding.data.get("measure") in _SIGNED_DIRECTION)


def retrieve(assembler, n, question):
    started = time.time()
    result, meta = assembler._retrieve(question, turn_id=f"dir-judge-{n}")
    findings = [h.finding for h in result.hits]
    return {"n": n, "question": question,
            "judge_used": bool(meta.get("used")),
            "seconds": round(time.time() - started, 1),
            "findings": [f.id for f in findings],
            "signed_findings": [f.id for f in findings if _signed(f)]}, findings


def _attempt_prose(turn_id):
    return [c["response_text"] for c in CALLS
            if c and c["turn_id"] == turn_id and c["purpose"] == "write"]


def write(arm, n, question, findings, stamp):
    turn_id = f"dir-{arm}-{n}"
    started = time.time()
    out = writer_mod.consolidate(question, findings, run_date=stamp,
                                 turn_id=turn_id)
    prose = _attempt_prose(turn_id)
    attempts = []
    for index, result in enumerate(out.check_results):
        failing = [k for k, v in result.items()
                   if k != "all_pass" and not v["pass"]]
        direction = result.get("5_direction")
        attempts.append({
            "attempt": index + 1,
            "prose": prose[index] if index < len(prose) else None,
            "all_pass": result["all_pass"],
            "failing_steps": failing,
            "counting_failures": [k for k in failing
                                  if not (k == "5_direction"
                                          and not direction["counts"])],
            "direction": direction,
        })
    fell_back_on = attempts[-1]["counting_failures"] if out.fell_back and attempts else []
    return {"arm": arm, "n": n, "question": question,
            "seconds": round(time.time() - started, 1),
            "attempts": out.attempts, "fell_back": out.fell_back,
            "fell_back_on": fell_back_on, "reason": out.reason,
            "final_text": out.text, "final_tagged": out.tagged,
            "checks": attempts}


def run_arm(arm, prepared, stamp):
    config.DIRECTION_CHECK = arm
    with ThreadPoolExecutor(len(prepared)) as pool:
        futures = [pool.submit(write, arm, entry["n"], entry["question"],
                               findings, stamp)
                   for entry, findings in prepared]
        return [f.result() for f in futures]


def main() -> int:
    retriever = Retriever()
    assembler = assemble.Assembler(retriever, allow_model=True)
    stamp = config.run_stamp_line()

    print(f"retrieval + judge, {len(QUESTIONS)} questions in parallel")
    with ThreadPoolExecutor(len(QUESTIONS)) as pool:
        prepared = list(pool.map(lambda nq: retrieve(assembler, *nq),
                                 enumerate(QUESTIONS, start=1)))
    for entry, _ in prepared:
        print(f"  {entry['n']:>2} {len(entry['findings']):>2} findings, "
              f"{len(entry['signed_findings'])} signed  {entry['question']}")
    writable = [(e, f) for e, f in prepared if f]

    arms = {}
    for arm in ("log", "block"):
        print(f"writer, arm {arm}")
        arms[arm] = run_arm(arm, writable, stamp)
        for r in arms[arm]:
            print(f"  {r['n']:>2} attempts={r['attempts']} "
                  f"fell_back={r['fell_back']} {r['fell_back_on']}")

    # Before Fix 1, for the Cuttack answer only: the pre-fix display sentence
    # (column translation alone) and no direction step.
    before = None
    cuttack = next(((e, f) for e, f in writable if e["question"] == CUTTACK),
                   None)
    if cuttack:
        print("writer, Cuttack before Fix 1")
        saved_display = corpus_mod.Finding.display_sentence
        corpus_mod.Finding.display_sentence = (
            lambda self: glossary.render(self.sentence, self.view))
        try:
            before = run_arm("off", [cuttack], stamp)[0]
            before["arm"] = "before_fix1"
        finally:
            corpus_mod.Finding.display_sentence = saved_display

    calls = [c for c in CALLS if c]
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stamp": stamp,
        "writer_model": config.WRITER_MODEL, "judge_model": config.JUDGE_MODEL,
        "questions": [e for e, _ in prepared],
        "arms": arms,
        "cuttack_before_fix1": before,
        "calls": {"n": len(calls),
                  "by_purpose": {p: sum(1 for c in calls if c["purpose"] == p)
                                 for p in sorted({c["purpose"] for c in calls})},
                  "usd": round(sum(c["usd"] for c in calls), 4),
                  "query_embeddings": len(QUESTIONS),
                  "log": [{k: v for k, v in c.items() if k != "response_text"}
                          for c in calls]},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1,
                              default=str), encoding="utf-8")
    print(f"{len(calls)} model calls, ${out['calls']['usd']:.4f} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

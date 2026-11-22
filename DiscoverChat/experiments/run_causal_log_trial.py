#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D13 Fix 6 T4 -- the cause-and-effect check in `log` mode, measured live.

    python DiscoverChat/experiments/run_causal_log_trial.py

THE DESIGN (handoffs/WPD13_report_fixes.md §6.7).
  * The fifteen WP-D13b questions, each with the findings the judge picked for
    it in the WP-D13b BASELINE arm (handoffs/WPD13b_headline_trial/
    trial_results.json). Same questions, same findings, same production
    writer wording -- so the only differences from that arm are the two check
    modes: causal `log` (Fix 6) and direction `block` (Fix 1b). No retrieval
    and no judge call.
  * The production `writer.consolidate`, unmodified, all fifteen in parallel.
  * Every model call counted and costed; hard cap 45.
  * The log lines the writer keeps in `log` mode are read back and matched to
    the answers that were shown.

Output: DiscoverChat/experiments/causal_log_trial_results.json
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

from DiscoverChat import config, llm, writer as writer_mod                  # noqa: E402
from DiscoverChat import corpus as corpus_mod                               # noqa: E402

BASELINE = REPO / "handoffs" / "WPD13b_headline_trial" / "trial_results.json"
OUT = config.HERE / "experiments" / "causal_log_trial_results.json"
CAP = 45

# USD per 1M tokens (input, output): the gpt-5.6-sol price used for the
# WP-D13 trials (its promotional price, recorded as running through at least
# 2026-11-21). Not re-checked for this run.
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
                       "finish_reason": record["finish_reason"],
                       "prompt_tokens": usage["prompt_tokens"],
                       "completion_tokens": usage["completion_tokens"],
                       "usd": round(cost, 5),
                       "response_text": record["response_text"]}
    return record


llm.call = _counted


def _counting(results: dict) -> list:
    return [k for k, v in results.items()
            if k != "all_pass" and not v["pass"] and v.get("counts", True)]


def run(row: dict, corpus, stamp: str) -> dict:
    n, question = row["n"], row["question"]
    findings = [corpus.get(i) for i in row["findings"]]
    turn_id = f"f6-live-{n}"
    started = time.time()
    out = writer_mod.consolidate(question, findings, run_date=stamp,
                                 turn_id=turn_id)
    seconds = round(time.time() - started, 1)
    writes = {c["attempt"]: c["response_text"] for c in CALLS
              if c and c["turn_id"] == turn_id and c["purpose"] == "write"}
    results = iter(out.check_results)
    attempts = []
    for attempt in range(1, out.attempts + 1):
        prose = (writes.get(attempt) or "").strip()
        if not prose:
            attempts.append({"attempt": attempt, "prose": "", "empty": True})
            continue
        r = next(results)
        causal = r.get("3_causal") or {}
        attempts.append({
            "attempt": attempt, "prose": prose,
            "counting_failures": _counting(r),
            "causal": {"pass": causal.get("pass"), "mode": causal.get("mode"),
                       "counts": causal.get("counts", True),
                       "words": [p["surface"] for p in causal.get("problems", [])],
                       "sentences": causal.get("sentences", [])},
            "direction": r.get("5_direction"),
        })
    return {"n": n, "question": question, "findings": row["findings"],
            "seconds": seconds, "attempts": out.attempts,
            "fell_back": out.fell_back, "reason": out.reason,
            "fell_back_on": (attempts[-1].get("counting_failures", [])
                             if out.fell_back and attempts else []),
            "tagged": out.tagged, "checks": attempts,
            "baseline": {"attempts": row["baseline"]["attempts"],
                         "fell_back": row["baseline"]["fell_back"],
                         "failed_on": [c["failed_on"]
                                       for c in row["baseline"]["checks"]]}}


def _log_lines(turn_ids: set, offset: int) -> list:
    path = llm.LOG_DIR / "citation_failures.jsonl"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        fh.seek(offset)
        lines = [json.loads(line) for line in fh if line.strip()]
    return [line for line in lines if line.get("turn_id") in turn_ids]


def main() -> int:
    assert config.CAUSAL_CHECK == "log", config.CAUSAL_CHECK
    with open(BASELINE, encoding="utf-8") as fh:
        baseline = json.load(fh)
    rows = baseline["results"]
    assert len(rows) == 15
    corpus = corpus_mod.load()
    stamp = config.run_stamp_line()
    log_path = llm.LOG_DIR / "citation_failures.jsonl"
    offset = log_path.stat().st_size if log_path.exists() else 0
    print(f"15 questions; writer {config.WRITER_MODEL}; causal "
          f"{config.CAUSAL_CHECK}; direction {config.DIRECTION_CHECK}")

    with ThreadPoolExecutor(len(rows)) as pool:
        answers = list(pool.map(lambda r: run(r, corpus, stamp), rows))

    shown = {f"f6-live-{a['n']}" for a in answers if not a["fell_back"]}
    log = _log_lines({f"f6-live-{a['n']}" for a in answers}, offset)
    causal_lines = [line for line in log
                    if line.get("kind") == "causal_words_shown"]

    calls = [c for c in CALLS if c]
    lost = [a for a in answers if a["fell_back"]]
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stamp": stamp,
        "writer_model": config.WRITER_MODEL,
        "causal_mode": config.CAUSAL_CHECK,
        "direction_mode": config.DIRECTION_CHECK,
        "baseline_source": str(BASELINE.relative_to(REPO)),
        "baseline_writer_model": baseline["writer_model"],
        "baseline_direction_mode": baseline["direction_mode"],
        "summary": {
            "answers": len(answers),
            "lost_narrative": len(lost),
            "lost_on_causal": sum(1 for a in lost
                                  if "3_causal" in a["fell_back_on"]),
            "lost_on": {a["n"]: a["fell_back_on"] for a in lost},
            "writer_attempts": sum(a["attempts"] for a in answers),
            "baseline_attempts": sum(r["baseline"]["attempts"] for r in rows),
            "baseline_lost": sum(1 for r in rows if r["baseline"]["fell_back"]),
            "attempts_with_causal_words": sum(
                1 for a in answers for c in a["checks"]
                if c.get("causal", {}).get("pass") is False),
            "shown_answers_with_causal_words": sum(
                1 for a in answers if not a["fell_back"]
                and a["checks"][-1].get("causal", {}).get("pass") is False),
            "causal_log_lines": len(causal_lines),
            "causal_log_lines_all_for_shown_answers": all(
                line["turn_id"] in shown for line in causal_lines),
        },
        "results": answers,
        "causal_log_lines": causal_lines,
        "calls": {"n": len(calls),
                  "by_purpose": {p: sum(1 for c in calls if c["purpose"] == p)
                                 for p in sorted({c["purpose"] for c in calls})},
                  "usd": round(sum(c["usd"] for c in calls), 4),
                  "log": [{k: v for k, v in c.items() if k != "response_text"}
                          for c in calls]},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    for a in answers:
        print(f"  {a['n']:>2} attempts={a['attempts']} fell_back="
              f"{a['fell_back']} on={a['fell_back_on']}  "
              f"[baseline {a['baseline']['attempts']}, "
              f"{'fell back' if a['baseline']['fell_back'] else 'kept'}]  "
              f"{a['question']}")
    print(json.dumps(out["summary"], indent=1))
    print(f"{len(calls)} model calls, ${out['calls']['usd']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

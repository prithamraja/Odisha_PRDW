#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D7 D7.1 — the offline prose audit, and its drift rate.

    python DiscoverChat/experiments/run_prose_audit.py
    python DiscoverChat/experiments/run_prose_audit.py --logs <path> --limit 20

WHY THIS EXISTS. D7.1 takes the verifier out of the turn: it cost a median
28.7 s of a ~60 s answer and an officer waited for it on every question. What
the verifier BOUGHT, though, was measured and is not nothing — WP-D4 found 3
qualitative drifts in 15 packets that no mechanical check could see: a
limitation narrowed, a sample-wide total pinned to a subset, a claim about the
analysis itself. The D7.3 citation check covers numbers. It does not cover any
of those.

So the verifier moves here, offline, over logged writer output, and reports a
RATE rather than a verdict. **The rate is a number in the gate output, not a
pass/fail** — the brief is explicit that the operator judges it, and the reason
is that there is no defensible threshold to set: 1 drift in 40 might be
acceptable for a decision aid whose every figure is separately checkable and
hoverable, and 1 in 4 plainly is not, and nothing in this code can tell those
apart on the operator's behalf.

WHAT IT AUDITS. Logged `purpose="write"` calls in `calls.jsonl`. Below
`FULL_AUDIT_BELOW` every one of them; above it, an evenly-spaced deterministic
sample whose size is stated in the output. Deterministic and not random,
because a rate that moves when nobody changed anything is a rate nobody trusts.

THE SOURCES IT JUDGES AGAINST are read out of the logged prompt, never
re-retrieved. A turn's findings are recorded in that turn's prompt; going back
to the corpus today would audit a different answer than the one that ran.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from DiscoverChat import config, llm, verifier            # noqa: E402

# Below this many logged writer calls, audit all of them. The threshold is a
# cost bound, not a statistical one: each audit call is a full verifier call.
FULL_AUDIT_BELOW = int(os.getenv("DISCOVERCHAT_AUDIT_FULL_BELOW", "60"))

DEFAULT_LOGS = [
    config.HERE / "experiments" / "logs" / "calls.jsonl",
    config.HERE / "logs" / "calls.jsonl",
]
OUT_PATH = config.HERE / "experiments" / "prose_audit_results.json"

# The two writer prompt shapes this project has produced. The audit has to read
# both, because the log spans the change: everything before WP-D7 is the D5
# connective writer ("FINDING 1 / <sentence> / From: ..."), everything after is
# the D7.3 consolidating writer ("FINDINGS / [id] <sentence>").
_CONNECTIVE_BLOCK = re.compile(
    r"^The analysis holds \d+ finding\(s\) that bear on it:\s*$", re.M)
_CONSOLIDATED_BLOCK = re.compile(r"^FINDINGS\s*$", re.M)


def _load(paths: list) -> list:
    """Every logged writer call with something to judge, newest last."""
    records = []
    for path in paths:
        if not Path(path).exists():
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("purpose") != "write":
                    continue
                if not (record.get("response_text") or "").strip():
                    continue        # a starved call wrote nothing to audit
                records.append(record)
    return records


def _sources(record: dict) -> tuple:
    """(the findings block, whether this was a consolidating writer call).

    The blocks are located by their own headers rather than by slicing at fixed
    offsets, so a prompt that grows a line does not silently shift what the
    verifier is told the sources were.
    """
    prompt = record.get("prompt", "")
    match = _CONSOLIDATED_BLOCK.search(prompt)
    if match:
        return prompt[match.end():].strip(), True
    match = _CONNECTIVE_BLOCK.search(prompt)
    if match:
        tail = prompt[match.end():]
        cut = tail.find("Write the connective prose")
        return (tail[:cut] if cut > 0 else tail).strip(), False
    return prompt.strip(), False


def _prose(record: dict, consolidated: bool) -> str:
    """The text an officer would have seen, from the writer's raw reply."""
    text = (record.get("response_text") or "").strip()
    if consolidated:
        return text
    # The D5 writer answered in two delimited parts; audit what was displayed.
    from DiscoverChat import writer
    opening, closing = writer.parse(text)
    return "\n\n".join(p for p in (opening, closing) if p).strip() or text


def sample(records: list, limit: int | None) -> tuple:
    """(the records to audit, a sentence saying how they were chosen)."""
    total = len(records)
    size = limit or (total if total < FULL_AUDIT_BELOW else FULL_AUDIT_BELOW)
    if size >= total:
        return records, f"all {total} logged writer calls"
    step = total / size
    picked = [records[int(i * step)] for i in range(size)]
    return picked, (f"an evenly-spaced sample of {len(picked)} of {total} "
                    f"logged writer calls (every {step:.1f}th, deterministic)")


def audit(records: list) -> dict:
    results, elapsed = [], []
    for index, record in enumerate(records, start=1):
        source_material, consolidated = _sources(record)
        prose = _prose(record, consolidated)
        prompt = verifier.build_audit_prompt(
            prose, source_material, record.get("prompt", ""),
            consolidated=consolidated)
        started = time.time()
        try:
            reply = llm.call(config.VERIFIER_MODEL, prompt,
                             config.VERIFIER_MAX_COMPLETION, "audit",
                             turn_id=f"audit-{index}")
            verdict = verifier.parse_verdict(reply["response_text"])
        except Exception as exc:                       # a call that never ran
            verdict = {"verdict": "fail_to_verify",
                       "problems": [{"drifted_claim": "(none quoted)",
                                     "missing_or_contradicted_fact":
                                     f"{type(exc).__name__}: {exc}"}]}
        elapsed.append(round(time.time() - started, 1))
        results.append({
            "n": index,
            "source_turn_id": record.get("turn_id"),
            "source_ts": record.get("ts"),
            "writer_model": record.get("model"),
            "shape": "consolidated" if consolidated else "connective",
            "verdict": verdict["verdict"],
            "prose": prose,
            "problems": verdict.get("problems", []),
            "seconds": elapsed[-1],
        })
        print(f"  {index:>3}/{len(records)}  {verdict['verdict']:<15} "
              f"{elapsed[-1]:>5}s  {prose[:70]!r}")

    drifted = [r for r in results if r["verdict"] == "fail"]
    unverified = [r for r in results if r["verdict"] == "fail_to_verify"]
    passed = [r for r in results if r["verdict"] == "pass"]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "verifier_model": config.VERIFIER_MODEL,
        "audited": len(results),
        "passed": len(passed),
        "drifted": len(drifted),
        "fail_to_verify": len(unverified),
        # The rate the operator judges. Denominator is everything audited,
        # INCLUDING the unverifiable — a verdict nobody could get is not
        # evidence of soundness and must not be quietly dropped from the base.
        "drift_rate": (len(drifted) / len(results)) if results else 0.0,
        "drift_rate_of_verified": (len(drifted) / (len(drifted) + len(passed)))
                                  if (drifted or passed) else 0.0,
        "median_seconds": statistics.median(elapsed) if elapsed else 0.0,
        "results": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="WP-D7 D7.1 prose drift audit")
    parser.add_argument("--logs", action="append", default=None,
                        help="a calls.jsonl to read (repeatable)")
    parser.add_argument("--limit", type=int, default=None,
                        help="audit at most this many, evenly spaced")
    parser.add_argument("--out", default=str(OUT_PATH))
    args = parser.parse_args(argv)

    paths = [Path(p) for p in (args.logs or DEFAULT_LOGS)]
    records = _load(paths)
    if not records:
        print("  no logged writer calls found in: "
              + ", ".join(str(p) for p in paths))
        return 2

    picked, how = sample(records, args.limit)
    print(f"  WP-D7 D7.1 prose audit — {how}")
    print(f"  verifier: {config.VERIFIER_MODEL}\n")
    report = audit(picked)
    report["sampling"] = how
    report["log_paths"] = [str(p) for p in paths]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"\n  audited {report['audited']}  |  pass {report['passed']}  |  "
          f"drift {report['drifted']}  |  could not verify "
          f"{report['fail_to_verify']}")
    print(f"  DRIFT RATE {report['drift_rate']:.1%} "
          f"({report['drift_rate_of_verified']:.1%} of the verifiable)")
    print("  This is a number for the operator to judge, not a pass/fail.")
    for result in report["results"]:
        if result["verdict"] == "fail":
            print(f"\n  FLAGGED  turn {result['source_turn_id']} "
                  f"({result['shape']})")
            print(f"    {result['prose'][:400]}")
            for problem in result["problems"][:3]:
                print(f"    -> {problem.get('drifted_claim')}")
                print(f"       {problem.get('missing_or_contradicted_fact')}")
    print(f"\n  written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

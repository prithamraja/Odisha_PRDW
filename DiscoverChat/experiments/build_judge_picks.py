#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hold the judge's picks: run search and the judge ONCE per question, keep it.

    python DiscoverChat/experiments/build_judge_picks.py           # hold what is not held yet
    python DiscoverChat/experiments/build_judge_picks.py --list    # the routes only: no network, no cost
    python DiscoverChat/experiments/build_judge_picks.py --check   # do the held picks still match the corpus?
    python DiscoverChat/experiments/build_judge_picks.py --redo L03 T01
    python DiscoverChat/experiments/build_judge_picks.py --redo ALL

WHY. Every writer test starts from the same thing: a question and the findings
the judge picked for it. Search and the judge are the slow, costly part of a
turn and they are not what a writer test is testing, so they are run once and
the result is held in `judge_picks.json`. A writer test then costs writer
calls only, and two tests are compared on exactly the same findings.

WHAT IS HELD. For each question in `writer_trial_questions.json`:
  * the route the rules give it. A question the rules send to Ask (lookup) or
    to the "why" reply never reaches the writer in the live service, so it is
    recorded with no findings and no judge call. The model classifier is not
    asked: it does not change what is retrieved.
  * the judge's picks, through `Assembler._retrieve` -- the live path, with
    the configured judge model, judge prompt and answer cap -- as record ids in
    the order the service hands them to the writer, each with its stored
    sentence so a later corpus rebuild is noticed.

A question is held only when the judge itself answered. If the judge could not
be reached and the service fell back to the plain cut-off, nothing is saved for
that question and it is named at the end; run the script again to retry it.

Questions already held are left alone, so adding a question to the file and
re-running costs one judge call, not fifty.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import assemble, classifier, config, judge, llm          # noqa: E402
from DiscoverChat import corpus as corpus_mod                              # noqa: E402
from DiscoverChat.experiments import held_picks                            # noqa: E402
from DiscoverChat.retrieval import Retriever                               # noqa: E402

NOT_FOR_WRITER = (classifier.LOOKUP, classifier.WHY)


def route_of(question: str) -> dict:
    routed = classifier.rule_route(question)
    if routed is None:
        return {"move": classifier.RETRIEVE, "by": "no rule matched",
                "reason": "treated as an ordinary search; the model "
                          "classifier was not asked"}
    return {"move": routed.move, "by": "rule", "reason": routed.reason}


def hold(assembler, item: dict) -> dict:
    """One question -> its held entry. `failed` is set when the judge did not
    answer, and such an entry is never written to the file."""
    entry = {"id": item["id"], "source": item.get("source", ""),
             "question": item["question"], "route": route_of(item["question"]),
             "held_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if entry["route"]["move"] in NOT_FOR_WRITER:
        entry["reaches_writer"] = False
        entry["findings"] = []
        return entry

    turn_id = f"held-{item['id']}"
    try:
        result, meta = assembler._retrieve(item["question"], turn_id=turn_id)
    except Exception as exc:
        entry["failed"] = f"{type(exc).__name__}: {exc}"
        return entry
    if not meta.get("used"):
        entry["failed"] = (f"the judge did not answer "
                           f"({meta.get('reason') or meta.get('why')})")
        return entry

    findings = [hit.finding for hit in result.hits]
    entry["reaches_writer"] = bool(findings)
    entry["judge"] = {
        "model": config.JUDGE_MODEL,
        "prompt_variant": config.JUDGE_PROMPT_VARIANT,
        "prompt_sha256": judge.prompt_sha256(),
        "attempts": meta.get("attempts"),
        "pool": meta.get("pool"),
        "kept": meta.get("kept"),
        "shown": len(findings),
        "capped_at": config.ANSWER_CAP if result.capped else None,
        "hallucinated_ids": meta.get("hallucinated_ids", []),
        "note": meta.get("reason", ""),
    }
    entry["findings"] = [
        {"id": f.id,
         "kind": "breakdown" if f.is_decomposition else "pattern",
         "sentence": f.sentence}
        for f in findings]
    return entry


def summary_line(entry: dict) -> str:
    if entry.get("failed"):
        what = f"NOT HELD - {entry['failed']}"
    elif entry["route"]["move"] in NOT_FOR_WRITER:
        what = f"not for the writer ({entry['route']['move']})"
    else:
        kinds = [f["kind"] for f in entry["findings"]]
        what = (f"{len(kinds):>2} findings ({kinds.count('pattern')} patterns, "
                f"{kinds.count('breakdown')} breakdowns)")
        if entry["judge"]["capped_at"]:
            what += f", judge kept {entry['judge']['kept']}"
    return f"  {entry['id']:<7} {what}  | {entry['question']}"


def write(held: dict) -> None:
    text = json.dumps(held, ensure_ascii=False, indent=1)
    tmp = held_picks.PICKS_PATH.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(held_picks.PICKS_PATH)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true",
                        help="print each question's route and stop (no cost)")
    parser.add_argument("--check", action="store_true",
                        help="check the held picks against the corpus and stop")
    parser.add_argument("--redo", nargs="+", default=[], metavar="ID",
                        help="hold these question ids again (ALL for every one)")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args(argv)

    questions = held_picks.load_questions()
    held = held_picks.load_held()

    if args.list:
        for item in questions:
            route = route_of(item["question"])
            print(f"  {item['id']:<7} {route['move']:<9} ({route['by']})  "
                  f"| {item['question']}")
        return 0

    corpus = corpus_mod.load()
    if args.check:
        found = held_picks.problems(held, corpus)
        ready = held_picks.usable(held, corpus) if not found else []
        print(f"{len(held['entries'])} held, {len(ready)} reach the writer, "
              f"{len(found)} problem(s)")
        for line in found[:20]:
            print("  " + line)
        return 1 if found else 0

    # A rebuilt corpus makes every old pick suspect, so they are not mixed.
    if held["entries"] and held_picks.problems(held, corpus) \
            and "ALL" not in args.redo:
        print("The held picks no longer match the corpus. Rebuild all of them "
              "with --redo ALL.")
        return 1

    redo = set(args.redo)
    kept = {e["id"]: e for e in held["entries"]
            if "ALL" not in redo and e["id"] not in redo}
    todo = [q for q in questions if q["id"] not in kept]
    if not todo:
        print(f"Nothing to do: all {len(questions)} questions are held.")
        return 0

    counter = held_picks.CallCounter(llm, cap=2 * len(todo))
    assembler = assemble.Assembler(Retriever(), allow_model=True, use_judge=True)
    print(f"Holding {len(todo)} question(s); judge {config.JUDGE_MODEL}, "
          f"prompt '{config.JUDGE_PROMPT_VARIANT}', answer cap "
          f"{config.ANSWER_CAP}")
    with ThreadPoolExecutor(max(1, min(args.workers, len(todo)))) as pool:
        new = list(pool.map(lambda q: hold(assembler, q), todo))

    for entry in new:
        print(summary_line(entry))
        if not entry.get("failed"):
            kept[entry["id"]] = entry

    out = {
        "what_this_is": (
            "Judge picks held for writer tests. Built by build_judge_picks.py "
            "from writer_trial_questions.json; read through held_picks.py. "
            "Each entry is one question and the findings the judge picked for "
            "it, in the order the service hands them to the writer."),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": {"candidate_set_id": held_picks.candidate_set_id(corpus),
                   "run_stamp": config.run_stamp_line(),
                   "records": len(corpus)},
        "entries": [kept[q["id"]] for q in questions if q["id"] in kept],
    }
    write(out)

    for_writer = [e for e in out["entries"] if e.get("reaches_writer")]
    sizes = sorted(len(e["findings"]) for e in for_writer)
    failed = [e["id"] for e in new if e.get("failed")]
    print(f"\n{len(out['entries'])} of {len(questions)} questions held in "
          f"{held_picks.PICKS_PATH.name}; {len(for_writer)} reach the writer")
    if sizes:
        print(f"findings per question: least {sizes[0]}, middle "
              f"{sizes[len(sizes) // 2]}, most {sizes[-1]}")
    if failed:
        print(f"NOT held (run again to retry): {', '.join(failed)}")
    print(counter.spend_line())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

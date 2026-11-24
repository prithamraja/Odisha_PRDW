# -*- coding: utf-8 -*-
"""The held judge picks: reading them, and checking they still fit the corpus.

Shared by `build_judge_picks.py` (which writes the file) and by every writer
test that starts from it. Nothing here calls a model.

    judge_picks.json    one entry per question: the question and the findings
                        the judge picked for it, in the order the service hands
                        them to the writer

A HELD SET GOES STALE WHEN THE CORPUS IS REBUILT. Record ids are positions in
one build, so after a rebuild an id can point at a different record (this is
what happened to `answer_compare.json` after WP-D11b). Each held finding
therefore keeps its stored sentence, and `problems()` compares it with the
corpus: a writer test refuses to run on picks that no longer match.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUESTIONS_PATH = HERE / "writer_trial_questions.json"
PICKS_PATH = HERE / "judge_picks.json"


class StaleHeldSet(Exception):
    """The held picks do not match the corpus this process loaded."""


def load_questions() -> list:
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        questions = json.load(fh)["questions"]
    ids = [q["id"] for q in questions]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"repeated question ids in {QUESTIONS_PATH.name}: "
                         f"{repeated}")
    return questions


def load_held() -> dict:
    """The held file, or an empty one when nothing has been held yet."""
    if not PICKS_PATH.exists():
        return {"entries": []}
    with open(PICKS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def candidate_set_id(corpus) -> str:
    """Which mining run the loaded corpus is from."""
    return str(corpus.stamp.get("candidate_set_id")
               or corpus.meta.get("candidate_set_id") or "")


def problems(held: dict, corpus) -> list:
    """Every way the held picks disagree with the loaded corpus. [] = usable."""
    found = []
    held_set = (held.get("corpus") or {}).get("candidate_set_id")
    if held.get("entries") and held_set != candidate_set_id(corpus):
        found.append(f"held picks are from candidate set {held_set}, the "
                     f"corpus is {candidate_set_id(corpus)}")
    for entry in held.get("entries", []):
        for item in entry.get("findings", []):
            record = corpus.get(item["id"])
            if record is None:
                found.append(f"{entry['id']}: record {item['id']} is not in "
                             f"the corpus")
            elif record.sentence != item["sentence"]:
                found.append(f"{entry['id']}: record {item['id']} now holds a "
                             f"different sentence")
    return found


def usable(held: dict, corpus, *, min_findings: int = 1) -> list:
    """[(entry, [Finding, ...])] for every held question that reaches the
    writer, in file order. Raises StaleHeldSet rather than hand back picks
    that no longer match the corpus."""
    found = problems(held, corpus)
    if found:
        raise StaleHeldSet(
            f"{len(found)} problem(s), first: {found[0]}. Rebuild the held "
            f"set: python DiscoverChat/experiments/build_judge_picks.py "
            f"--redo ALL")
    out = []
    for entry in held.get("entries", []):
        if len(entry.get("findings", [])) < min_findings:
            continue
        out.append((entry, [corpus.get(item["id"])
                            for item in entry["findings"]]))
    return out


# ── every model call counted, capped and costed ──────────────────────────────
# USD per 1M tokens (input, output). A model with no price here is never costed
# at $0: its tokens are reported and its cost reads "price not set" (WP-D13
# Fix 9 T4). The operator supplies prices; none is guessed.
PRICES = {"gpt-5.6-sol": (4.0, 20.0)}


class CallCounter:
    """Wraps `llm.call` so a script can cap, count and cost its model calls.

        counter = CallCounter(llm, cap=120)
        ...
        print(counter.spend_line())
    """

    def __init__(self, llm_module, cap: int):
        self.cap = cap
        self.calls = []
        self._lock = threading.Lock()
        self._real = llm_module.call
        llm_module.call = self._counted

    def _counted(self, model, prompt, max_completion, purpose, *,
                 turn_id=None, attempt=None):
        with self._lock:
            if len(self.calls) >= self.cap:
                raise RuntimeError(f"model-call cap of {self.cap} reached")
            slot = len(self.calls)
            self.calls.append(None)
        record = self._real(model, prompt, max_completion, purpose,
                            turn_id=turn_id, attempt=attempt)
        usage = record["usage"]
        with self._lock:
            self.calls[slot] = {
                "model": model, "purpose": purpose, "turn_id": turn_id,
                "attempt": attempt, "seconds": record["seconds"],
                "finish_reason": record["finish_reason"],
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "reasoning_tokens": usage.get("reasoning_tokens"),
                "response_text": record["response_text"]}
        return record

    def done(self) -> list:
        return [c for c in self.calls if c]

    def for_turn(self, turn_id: str, purpose: str) -> list:
        return sorted((c for c in self.done()
                       if c["turn_id"] == turn_id and c["purpose"] == purpose),
                      key=lambda c: c["attempt"] or 0)

    def spend(self) -> dict:
        calls = self.done()
        by_model = {}
        for call in calls:
            row = by_model.setdefault(call["model"], {
                "calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
            row["calls"] += 1
            row["prompt_tokens"] += call["prompt_tokens"]
            row["completion_tokens"] += call["completion_tokens"]
        for model, row in by_model.items():
            price = PRICES.get(model)
            row["usd"] = (None if price is None else round(
                (row["prompt_tokens"] * price[0]
                 + row["completion_tokens"] * price[1]) / 1e6, 4))
        return {"calls": len(calls), "by_model": by_model}

    def spend_line(self) -> str:
        parts = []
        for model, row in self.spend()["by_model"].items():
            cost = (f"${row['usd']:.2f}" if row["usd"] is not None
                    else "price not set")
            parts.append(f"{model}: {row['calls']} calls, "
                         f"{row['prompt_tokens']:,} tokens in, "
                         f"{row['completion_tokens']:,} out, {cost}")
        return "; ".join(parts) or "no model calls"

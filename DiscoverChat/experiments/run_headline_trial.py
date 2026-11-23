#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D13b -- short answer and section headlines: a TRIAL the operator marks.

    python DiscoverChat/experiments/run_headline_trial.py

NOTHING THE LIVE SERVICE IMPORTS IS CHANGED BY THIS SCRIPT. It builds its own
writer prompt from the existing pieces and runs its own copy of the writer's
two-attempt loop; `context_brief.py`, `writer.py` and `checks.py` are read, not
edited.

THE DESIGN (brief handoffs/WPD13b_headline_trial.md).
  * The fifteen questions recorded in `answer_compare.json`.
  * Retrieval and the judge ONCE per question (`Assembler._retrieve`, the
    production path; the classifier is not called -- it does not change what is
    retrieved).
  * Two writer arms on the same findings, in parallel:
      baseline  `writer.consolidate`, the production function, unmodified
      headline  the same prompt with the operator-approved wording (§2) added
                immediately before its last line, "Return only the finished
                prose." -- run through `consolidate_with_headlines` below, A
                COPY of `writer.consolidate`'s loop with one addition: each
                headline and the short answer is also checked on its own (§3).
  * The code-written suggestion (§4) over the cited records.
  * Every model call counted and costed; hard cap 90.

Output: handoffs/WPD13b_headline_trial/trial_results.json and REVIEW_SHEET.md.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import (assemble, checks, config, context_brief, glossary,  # noqa: E402
                          llm, writer as writer_mod)
from DiscoverChat import corpus as corpus_mod                                  # noqa: E402
from DiscoverChat.retrieval import Retriever                                   # noqa: E402
from phase5f_decompose import format_measure, _num, _pct                       # noqa: E402

OUT_DIR = REPO / "handoffs" / "WPD13b_headline_trial"
CAP = 90

# The operator-approved wording, §2, verbatim.
ADDED_WORDING = (
    'Begin with a short answer: one or two sentences giving the most important '
    'facts for this question, on a line starting "SHORT ANSWER:". Then write the '
    'narrative in short sections. Start each section with a one-line headline '
    'that states that section\'s main fact in plain words, on a line starting '
    '"## ". The short answer and the headlines follow the same rules as the '
    'rest: tag every figure, state facts only, and give no advice.')
LAST_LINE = "Return only the finished prose."

# USD per 1M tokens (input, output). gpt-5.6-sol at its promotional price,
# recorded as running through at least 2026-11-21 -- the day of this run.
# A model with no price here is NEVER costed at $0 (WP-D13 Fix 9 T4): its
# tokens are reported and its cost reads "price not set for <id>". The
# operator supplies the prices of the new models; none is guessed here.
PRICES = {"gpt-5.6-sol": (4.0, 20.0)}


def _usd(model: str, usage: dict):
    """The call's cost in USD, or None when the model has no price on file."""
    price = PRICES.get(model)
    if price is None:
        return None
    return round((usage["prompt_tokens"] * price[0]
                  + usage["completion_tokens"] * price[1]) / 1e6, 5)


def spend(calls: list) -> dict:
    """Tokens and cost over the counted calls. `usd` is None (never 0) when
    any call's model has no price; `text` is the line to print."""
    unpriced = sorted({c["model"] for c in calls if c["usd"] is None})
    priced = [c for c in calls if c["usd"] is not None]
    out = {"prompt_tokens": sum(c["prompt_tokens"] for c in calls),
           "completion_tokens": sum(c["completion_tokens"] for c in calls),
           "usd": (None if unpriced
                   else round(sum(c["usd"] for c in priced), 4)),
           "price_not_set": unpriced}
    if unpriced:
        text = (f"{out['prompt_tokens']:,} tokens in, "
                f"{out['completion_tokens']:,} out; "
                + "; ".join(f"price not set for {m}" for m in unpriced))
        if priced:
            text += (f"; ${sum(c['usd'] for c in priced):.4f} for the "
                     f"{len(priced)} priced calls")
    else:
        text = f"${out['usd']:.4f}"
    out["text"] = text
    return out


def _questions() -> list:
    with open(config.HERE / "experiments" / "answer_compare.json",
              encoding="utf-8") as fh:
        recorded = json.load(fh)
    questions = [r["question"] for r in recorded["results"]["new"]]
    assert len(questions) == recorded["questions"] == 15, questions
    return questions


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
    with _lock:
        CALLS[slot] = {"model": model, "purpose": purpose, "turn_id": turn_id,
                       "attempt": attempt, "seconds": record["seconds"],
                       "finish_reason": record["finish_reason"],
                       "prompt_tokens": usage["prompt_tokens"],
                       "completion_tokens": usage["completion_tokens"],
                       "usd": _usd(model, usage),
                       "response_text": record["response_text"]}
    return record


llm.call = _counted


# ── the prompt: the production prompt, with the §2 wording added ─────────────
def headline_prompt(question, findings, *, run_date="", reason=""):
    base = writer_mod.build_consolidation_prompt(
        question, findings, run_date=run_date, reason=reason)
    task = context_brief.CONSOLIDATING_WRITER_PROMPT
    assert task.rstrip().endswith(LAST_LINE), (
        "the writer task no longer ends with its last line; §2 cannot be placed")
    head = task.rstrip()[:-len(LAST_LINE)].rstrip()
    added = f"{head}\n\n{ADDED_WORDING}\n\n{LAST_LINE}"
    assert base.count(task) == 1
    return base.replace(task, added)


# ── parsing (forgiving: no markers = today's prose, shown as today) ──────────
_SHORT = re.compile(r"^\W*SHORT ANSWER:\W*\s*", re.I)
_HEAD = re.compile(r"^\s*##\s+")


def parse(prose: str) -> dict:
    """{"short_answer", "sections": [{"headline", "body"}], "lead"}."""
    short, sections, lead = None, [], []
    current = None
    for line in (prose or "").splitlines():
        if short is None and not sections and _SHORT.match(line):
            short = _SHORT.sub("", line).strip()
            continue
        if _HEAD.match(line):
            current = {"headline": _HEAD.sub("", line).strip().strip("*").strip(),
                       "body": []}
            sections.append(current)
            continue
        (current["body"] if current else lead).append(line)
    for s in sections:
        s["body"] = "\n".join(s["body"]).strip()
    return {"short_answer": short, "sections": sections,
            "lead": "\n".join(lead).strip()}


def unmarked(prose: str) -> str:
    """The markers stripped, so they are never read as content (§3)."""
    out = []
    for line in (prose or "").splitlines():
        if _SHORT.match(line):
            line = _SHORT.sub("", line)
        elif _HEAD.match(line):
            line = _HEAD.sub("", line)
        out.append(line)
    return "\n".join(out)


def item_checks(parsed: dict, findings, run_date, mode) -> list:
    """Steps 1, 2, 3 and 5 on the short answer and on each headline alone."""
    items = []
    if parsed["short_answer"]:
        items.append(("short answer", parsed["short_answer"]))
    items += [("headline", s["headline"]) for s in parsed["sections"]]
    out = []
    for kind, text in items:
        r = checks.check_citations(text, findings, run_date=run_date,
                                   direction_mode=mode)
        steps = ["1_ids_known", "2_numerals_cited", "3_causal"]
        if "5_direction" in r and r["5_direction"]["counts"]:
            steps.append("5_direction")
        failing = [s for s in steps if not r[s]["pass"]]
        reason = ""
        if failing:
            trimmed = {k: v for k, v in r.items()}
            trimmed["4_all_findings_cited"] = {"pass": True, "dropped": [],
                                               "of": 0}
            reason = (f'In the {kind} "{checks.strip_tags(text)}": '
                      + checks.citation_failure_reason(trimmed))
        out.append({"kind": kind, "text": text, "pass": not failing,
                    "failing_steps": failing, "reason": reason,
                    "direction": r.get("5_direction")})
    return out


def consolidate_with_headlines(question, findings, *, run_date="",
                               turn_id=None) -> dict:
    """A COPY of `writer.consolidate`'s loop (two attempts, then the bare
    sentences), with the §2 prompt and the §3 per-item checks added. The
    whole-output check is `check_citations` unchanged, run on the prose with
    its markers stripped; a per-item failure also counts as a failed attempt.
    """
    mode = config.DIRECTION_CHECK
    out = {"fell_back": True, "attempts": 0, "reason": "", "tagged": "",
           "checks": []}
    reason = ""
    for attempt in (1, 2):
        out["attempts"] = attempt
        prompt = headline_prompt(question, findings, run_date=run_date,
                                 reason=reason)
        try:
            record = llm.call(config.WRITER_MODEL, prompt,
                              config.WRITER_MAX_COMPLETION, "write",
                              turn_id=turn_id, attempt=attempt)
        except Exception as exc:
            out["reason"] = f"writer call failed: {type(exc).__name__}: {exc}"
            return out
        prose = (record["response_text"] or "").strip()
        if not prose:
            reason = ""
            out["reason"] = ("writer returned nothing (finish_reason=%s)"
                             % record["finish_reason"])
            out["checks"].append({"attempt": attempt, "prose": "",
                                  "empty": True})
            continue
        whole = checks.check_citations(unmarked(prose), findings,
                                       run_date=run_date)
        parsed = parse(prose)
        items = item_checks(parsed, findings, run_date, mode)
        whole_failing = [k for k, v in whole.items()
                         if k != "all_pass" and not v["pass"]
                         and not (k == "5_direction" and not v["counts"])]
        items_failing = [i for i in items if not i["pass"]]
        out["checks"].append({
            "attempt": attempt, "prose": prose,
            "whole_all_pass": whole["all_pass"],
            "whole_failing_steps": whole_failing,
            "whole_direction": whole.get("5_direction"),
            "items": items,
            "failed_on": whole_failing + [f"{i['kind']}:{s}"
                                          for i in items_failing
                                          for s in i["failing_steps"]]})
        if whole["all_pass"] and not items_failing:
            out.update(fell_back=False, reason="", tagged=prose)
            return out
        bits = []
        if not whole["all_pass"]:
            bits.append(checks.citation_failure_reason(whole))
        bits += [i["reason"] for i in items_failing]
        reason = " ".join(b for b in bits if b)
        out["reason"] = reason
    return out


# ── the code-written suggestion (§4) ─────────────────────────────────────────
SUGGESTION = ("Suggested first step: {rows} rows have no {dimension} on file "
              "and account for {share} of {measure}. Check those records "
              "before drawing conclusions from this figure.")


def suggestion(findings) -> dict | None:
    """Pure function over the cited records: the decomposition whose "not
    recorded" member holds the largest share, if that share is 50% or more."""
    best = None
    for f in findings:
        if not f.is_decomposition:
            continue
        for m in corpus_mod.members_of(f.data):
            if m.get("is_null") and m["share"] >= 0.5:
                if best is None or m["share"] > best[1]["share"]:
                    best = (f, m)
    if best is None:
        return None
    f, m = best
    data = f.data
    amount = glossary.signed_money(
        format_measure(f.view, data["measure"], m["value"]), data["measure"])
    return {
        "record": f.id,
        "text": SUGGESTION.format(rows=_num(m["rows"], 0),
                                  dimension=data["dimension_phrase"],
                                  share=_pct(m["share"]),
                                  measure=data["measure_phrase"]),
        "triggered_by": {"rows": m["rows"], "share": m["share"],
                         "amount": amount, "of_total": glossary.signed_money(
                             data.get("total_display", ""), data["measure"]),
                         "dimension": data["dimension_phrase"],
                         "measure": data["measure_phrase"],
                         "scope": data.get("subspace_phrase", "")},
    }


# ── reported, not blocking (§3) ──────────────────────────────────────────────
_ADVICE = re.compile(r"\b(should|must|needs? to|recommend\w*)\b", re.I)
_IMPERATIVE = {
    "check", "review", "ensure", "focus", "prioritise", "prioritize",
    "consider", "look", "verify", "investigate", "follow", "confirm", "start",
    "address", "examine", "use", "make", "take", "monitor", "track", "raise",
    "ask", "treat", "fix", "clean", "correct", "reconcile", "update", "begin",
    "avoid", "keep", "note", "watch", "target", "compare", "audit", "resolve",
}


def advice(text: str) -> list:
    hits = []
    lines = checks.strip_tags(unmarked(text)).splitlines()
    for sentence in [s for line in lines for s in checks._sentences(line)]:
        found = [m.group(0) for m in _ADVICE.finditer(sentence)]
        first = re.sub(r"^[^A-Za-z]+", "", sentence).split(" ", 1)[0].lower()
        if first in _IMPERATIVE:
            found.append(f"imperative opening '{first}'")
        if found:
            hits.append({"sentence": sentence, "words": found})
    return hits


def structure_counts(parsed: dict) -> dict:
    short = parsed["short_answer"]
    short_sentences = (len(checks._sentences(checks.strip_tags(short)))
                       if short else 0)
    long_heads = [s["headline"] for s in parsed["sections"]
                  if len(checks.strip_tags(s["headline"]).split()) > 14]
    return {"has_short_answer": bool(short),
            "headlines": len(parsed["sections"]),
            "structured": bool(short) and bool(parsed["sections"]),
            "short_answer_sentences": short_sentences,
            "short_answer_over_two": short_sentences > 2,
            "headlines_over_14_words": long_heads}


# ── the run ──────────────────────────────────────────────────────────────────
def retrieve(assembler, n, question):
    result, meta = assembler._retrieve(question, turn_id=f"hl-judge-{n}")
    findings = [h.finding for h in result.hits]
    return {"n": n, "question": question, "judge_used": bool(meta.get("used")),
            "findings": [f.id for f in findings]}, findings


def _writes(turn_id):
    return [c["response_text"] for c in CALLS
            if c and c["turn_id"] == turn_id and c["purpose"] == "write"]


def baseline(n, question, findings, stamp):
    turn_id = f"hl-base-{n}"
    out = writer_mod.consolidate(question, findings, run_date=stamp,
                                 turn_id=turn_id)
    prose = _writes(turn_id)
    attempts = []
    for i, r in enumerate(out.check_results):
        attempts.append({
            "attempt": i + 1, "prose": prose[i] if i < len(prose) else None,
            "failed_on": [k for k, v in r.items()
                          if k != "all_pass" and not v["pass"]
                          and not (k == "5_direction" and not v["counts"])]})
    return {"fell_back": out.fell_back, "attempts": out.attempts,
            "reason": out.reason, "tagged": out.tagged, "checks": attempts,
            "advice": advice(out.tagged) if out.tagged else []}


def headline(n, question, findings, stamp):
    out = consolidate_with_headlines(question, findings, run_date=stamp,
                                     turn_id=f"hl-new-{n}")
    parsed = parse(out["tagged"]) if out["tagged"] else None
    out["parsed"] = parsed
    out["structure"] = structure_counts(parsed) if parsed else None
    out["advice"] = advice(out["tagged"]) if out["tagged"] else []
    return out


def main() -> int:
    questions = _questions()
    retriever = Retriever()
    assembler = assemble.Assembler(retriever, allow_model=True)
    stamp = config.run_stamp_line()
    mode = config.DIRECTION_CHECK
    print(f"{len(questions)} questions; direction mode {mode}")

    with ThreadPoolExecutor(len(questions)) as pool:
        prepared = list(pool.map(lambda nq: retrieve(assembler, *nq),
                                 enumerate(questions, start=1)))
    for e, f in prepared:
        print(f"  {e['n']:>2} {len(f):>2} findings  {e['question']}")

    jobs = {}
    with ThreadPoolExecutor(2 * len(prepared)) as pool:
        for e, f in prepared:
            if not f:
                continue
            jobs[(e["n"], "baseline")] = pool.submit(baseline, e["n"],
                                                     e["question"], f, stamp)
            jobs[(e["n"], "headline")] = pool.submit(headline, e["n"],
                                                     e["question"], f, stamp)
        results = {k: v.result() for k, v in jobs.items()}

    rows = []
    for e, f in prepared:
        row = dict(e)
        row["baseline"] = results.get((e["n"], "baseline"))
        row["headline"] = results.get((e["n"], "headline"))
        row["suggestion"] = suggestion(f)
        rows.append(row)
        b, h = row["baseline"] or {}, row["headline"] or {}
        print(f"  {e['n']:>2} base fell_back={b.get('fell_back')} "
              f"({b.get('attempts')})  new fell_back={h.get('fell_back')} "
              f"({h.get('attempts')}) structured="
              f"{(h.get('structure') or {}).get('structured')}")

    answered = [r for r in rows if r["baseline"]]
    fb_base = sum(1 for r in answered if r["baseline"]["fell_back"])
    fb_new = sum(1 for r in answered if r["headline"]["fell_back"])
    structured = sum(1 for r in answered
                     if (r["headline"]["structure"] or {}).get("structured"))
    calls = [c for c in CALLS if c]
    cost = spend(calls)
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stamp": stamp, "direction_mode": mode,
        "writer_model": config.WRITER_MODEL, "judge_model": config.JUDGE_MODEL,
        "added_wording": ADDED_WORDING,
        "pass_marks": {
            "fallbacks_baseline": fb_base, "fallbacks_headline": fb_new,
            "fallbacks_pass": (fb_new - fb_base) <= 2,
            "structured": structured, "of": len(answered),
            "structured_pass": structured >= 12,
        },
        "results": rows,
        "calls": {"n": len(calls),
                  "by_purpose": {p: sum(1 for c in calls if c["purpose"] == p)
                                 for p in sorted({c["purpose"] for c in calls})},
                  "usd": cost["usd"],
                  "prompt_tokens": cost["prompt_tokens"],
                  "completion_tokens": cost["completion_tokens"],
                  "price_not_set": cost["price_not_set"],
                  "query_embeddings": len(questions),
                  "log": [{k: v for k, v in c.items() if k != "response_text"}
                          for c in calls]},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "trial_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print(f"{len(calls)} model calls, {cost['text']}; pass marks "
          f"{out['pass_marks']}")
    write_sheet(out)
    return 0


# ── the review sheet (§5) ────────────────────────────────────────────────────
STEP_WORDS = {
    "1_ids_known": "cited a finding it was not given",
    "2_numerals_cited": "a figure not tagged with, or not found in, the "
                        "finding it cites",
    "3_causal": "cause-and-effect wording",
    "4_all_findings_cited": "left out a finding it was given",
    "5_direction": "a spending figure without 'below plan' / 'below "
                   "sanction' (or with a minus sign)",
}
MARK = "[ ] correct  [ ] misleading  [ ] wrong"


def _plain_failure(code: str) -> str:
    if ":" in code:
        kind, step = code.split(":", 1)
        return f"in the {kind} on its own: {STEP_WORDS.get(step, step)}"
    return STEP_WORDS.get(code, code)


def _attempt_line(checks_list, fell_back) -> str:
    bits = []
    for c in checks_list:
        if c.get("empty"):
            bits.append(f"attempt {c['attempt']}: the writer returned nothing")
        elif c.get("failed_on"):
            bits.append(f"attempt {c['attempt']} failed ("
                        + "; ".join(_plain_failure(x) for x in c["failed_on"])
                        + ")")
        else:
            bits.append(f"attempt {c['attempt']} passed")
    tail = (" - so it FELL BACK to the plain finding sentences"
            if fell_back else "")
    return (", ".join(bits) or "no attempt recorded") + tail


def _strip(text: str) -> str:
    return checks.strip_tags(text or "")


def write_sheet(out: dict) -> None:
    rows = out["results"]
    pm = out["pass_marks"]
    L = []
    L.append("# Review sheet: short answers and section headlines")
    L.append("")
    L.append("WP-D13b trial, run " + out["generated_at"][:10] + ". Data "
             + out["stamp"] + ".")
    L.append("")
    L.append("**What this is.** Each of the fifteen questions was answered "
             "twice from the same findings: once as the service writes today, "
             "and once with the writer asked to open with a SHORT ANSWER and "
             "to put a one-line headline over each section. This sheet shows "
             "the second version. Nothing here is live.")
    L.append("")
    L.append("**What to mark.** Under every short answer and every headline, "
             "tick one box: *correct*, *misleading* (true but gives the wrong "
             "impression) or *wrong* (states something the findings do not "
             "say). Use the comment line for anything else. Under every "
             "suggestion, tick *warranted* or *not*. At the end of each "
             "question, list any words an officer would not understand; that "
             "list becomes the word list for Fix 3. Nothing is pre-ticked.")
    L.append("")
    L.append("**About the suggestions.** These are not written by the model. "
             "A fixed rule adds one when a finding shows that rows with a "
             "field left blank hold half or more of a figure; the sentence is "
             "fixed text with the record's own numbers filled in.")
    L.append("")
    L.append("Tags such as [d1-00248] are removed from the text below. The "
             "direction check from Fix 1 ran in **" + out["direction_mode"]
             + "** mode.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| # | Question | Short answer | Headlines | Fell back: new / today "
             "| Suggestion |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        h, b = r["headline"], r["baseline"]
        if not h:
            L.append(f"| {r['n']} | {r['question']} | - | - | no findings | - |")
            continue
        s = h["structure"] or {}
        L.append(f"| {r['n']} | {r['question']} | "
                 f"{'yes' if s.get('has_short_answer') else 'no'} | "
                 f"{s.get('headlines', 0)} | "
                 f"{'yes' if h['fell_back'] else 'no'} / "
                 f"{'yes' if b['fell_back'] else 'no'} | "
                 f"{'yes' if r['suggestion'] else 'no'} |")
    L.append("")
    L.append("**The two pass marks the code can compute:**")
    L.append("")
    L.append(f"- Fall-backs: {pm['fallbacks_headline']} of {pm['of']} with the "
             f"new wording, against {pm['fallbacks_baseline']} for today's "
             f"writer. Pass if no more than 2 above: "
             f"**{'PASS' if pm['fallbacks_pass'] else 'FAIL'}**.")
    L.append(f"- Answers with a short answer and at least one headline: "
             f"{pm['structured']} of {pm['of']}. Pass at 12 or more: "
             f"**{'PASS' if pm['structured_pass'] else 'FAIL'}**.")
    L.append("")
    L.append("The other three pass marks are yours: no *wrong* marks; no more "
             "than 1 in 10 items *misleading*; no suggestion *not warranted*.")
    L.append("")

    for r in rows:
        h = r["headline"]
        L.append("---")
        L.append("")
        L.append(f"## {r['n']}. {r['question']}")
        L.append("")
        if not h:
            L.append("No findings were selected for this question, so there "
                     "was nothing to write. Nothing to mark.")
            L.append("")
            L.append("Words an officer would not understand:")
            L.append("")
            continue
        parsed = h.get("parsed")
        if h["fell_back"]:
            L.append("**This answer fell back** to the plain finding sentences "
                     "after two attempts, so an officer would see no short "
                     "answer or headlines. Nothing to mark for the layout.")
            L.append("")
        elif not (h["structure"] or {}).get("structured"):
            L.append("The writer did not use the short answer / headline "
                     "layout here, so it is shown as today's prose would be.")
            L.append("")
        if parsed and not h["fell_back"]:
            if parsed["short_answer"]:
                L.append("**Short answer:** " + _strip(parsed["short_answer"]))
                L.append("")
                L.append(MARK)
                L.append("")
                L.append("Comment:")
                L.append("")
            if parsed["lead"]:
                L.append("> " + _strip(parsed["lead"]).replace("\n", "\n> "))
                L.append("")
            for section in parsed["sections"]:
                L.append("### " + _strip(section["headline"]))
                L.append("")
                L.append(MARK)
                L.append("")
                L.append("Comment:")
                L.append("")
                if section["body"]:
                    L.append("> " + _strip(section["body"]).replace("\n", "\n> "))
                    L.append("")
        sug = r["suggestion"]
        if sug:
            t = sug["triggered_by"]
            L.append("**Suggestion (written by a fixed rule, not the model):** "
                     + sug["text"])
            L.append("")
            L.append(f"Triggered by record {sug['record']}: within "
                     f"{t['scope']}, the rows with no {t['dimension']} hold "
                     f"{_pct(t['share'])} of {t['measure']} "
                     f"({t['amount']}, of a total of {t['of_total']}).")
            L.append("")
            L.append("[ ] warranted  [ ] not")
            L.append("")
        L.append("**Checks:** new wording: "
                 + _attempt_line(h["checks"], h["fell_back"]) + ". Today's "
                 "writer: " + _attempt_line(
                     [{"attempt": c["attempt"], "failed_on": c["failed_on"]}
                      for c in r["baseline"]["checks"]],
                     r["baseline"]["fell_back"]) + ".")
        notes = []
        s = h["structure"] or {}
        if s.get("short_answer_over_two"):
            notes.append(f"the short answer is {s['short_answer_sentences']} "
                         f"sentences (asked for one or two)")
        for head in s.get("headlines_over_14_words", []):
            notes.append(f"headline over 14 words: \"{_strip(head)}\"")
        for a in h.get("advice", []):
            notes.append("advice wording (" + ", ".join(a["words"]) + "): \""
                         + a["sentence"] + "\"")
        if notes:
            L.append("")
            L.append("Noted, not blocking: " + "; ".join(notes) + ".")
        L.append("")
        L.append("Words an officer would not understand:")
        L.append("")
    (OUT_DIR / "REVIEW_SHEET.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--sheet"]:
        with open(OUT_DIR / "trial_results.json", encoding="utf-8") as fh:
            write_sheet(json.load(fh))
    else:
        sys.exit(main())

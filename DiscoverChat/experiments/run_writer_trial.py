#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A writer test on the held judge picks: writer calls only.

    # the live prompt, as the "before"
    python DiscoverChat/experiments/run_writer_trial.py --label current

    # a candidate prompt, from a text file
    python DiscoverChat/experiments/run_writer_trial.py --label plain_v1 \
        --prompt-file DiscoverChat/experiments/writer_prompts/plain_v1.txt

    # fewer questions: named ones, or N spread from few findings to many
    python DiscoverChat/experiments/run_writer_trial.py --label try --only T01 L07
    python DiscoverChat/experiments/run_writer_trial.py --label try --sample 12

    # two or more finished runs, side by side (no model call)
    python DiscoverChat/experiments/run_writer_trial.py --compare current plain_v1

WHAT IT DOES. For each held question (`judge_picks.json`, built once by
`build_judge_picks.py`) it calls `writer.consolidate` -- the live function, with
the live checks, the live retry and the live fall-back -- on the held findings.
No search, no judge. So a run costs writer calls only, and two runs are compared
on exactly the same findings.

WHAT CAN BE VARIED, for this process only -- no file the service reads is edited:
  --prompt-file   the writer's instructions (in place of
                  `context_brief.CONSOLIDATING_WRITER_PROMPT`). The background
                  brief, the question and the findings are added around it
                  exactly as the service adds them.
  --model         the writer model
  --max-tokens    the writer's answer budget
  --allow-unused-findings
                  the rule "every finding the judge picked must be mentioned"
                  is switched off: the writer chooses which findings to use.
                  The report says how many it used.

WHAT IT REPORTS, per answer and as middle values over the run:
  kept or lost    lost = both attempts failed a check and the officer would get
                  the plain stored sentences; the failing check is named
  length          words, sentences, words per sentence, the longest sentence
  figures         how many, per sentence, the most in one sentence
  coverage        of the different figures the writer was handed, the share
                  that appear in its answer

Output: experiments/writer_trials/<label>.json and <label>.md (the answers, to
read). --compare writes <a>_vs_<b>[_vs_<c>...].md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import checks, config, context_brief, llm                # noqa: E402
from DiscoverChat import corpus as corpus_mod, writer as writer_mod        # noqa: E402
from DiscoverChat.experiments import held_picks                            # noqa: E402

OUT_DIR = held_picks.HERE / "writer_trials"
LONG_SENTENCE_WORDS = 25
MANY_FIGURES = 2


# ── measures: code only, on the text an officer would read ───────────────────

def _variants(tokens) -> set:
    out = set()
    for token in tokens:
        out |= checks._num_variants(token)
    return out


def measure(tagged: str, findings: list) -> dict:
    """Length, figure load and figure coverage of one answer."""
    text = checks.strip_tags(tagged)
    sentences = checks._sentences(text)
    words = [len(s.split()) for s in sentences]
    figures = [len(checks.numerals(s)) for s in sentences]
    handed = set()
    for finding in findings:
        handed |= set(checks.numerals(finding.display_sentence()))
    written = _variants(checks.numerals(text))
    covered = {t for t in handed if checks._num_variants(t) & written}
    ids = {f.id for f in findings}
    n = max(1, len(sentences))
    return {
        "findings_handed": len(ids),
        "findings_used": len(set(checks.cited_ids(tagged)) & ids),
        "words": sum(words),
        "sentences": len(sentences),
        "words_per_sentence": round(sum(words) / n, 1),
        "longest_sentence_words": max(words, default=0),
        "long_sentences": sum(1 for w in words if w > LONG_SENTENCE_WORDS),
        "figures": sum(figures),
        "figures_per_sentence": round(sum(figures) / n, 1),
        "most_figures_in_a_sentence": max(figures, default=0),
        "sentences_with_many_figures": sum(1 for f in figures
                                           if f > MANY_FIGURES),
        "semicolons": text.count(";"),
        "figures_handed": len(handed),
        "figures_covered": len(covered),
        "coverage": round(len(covered) / len(handed), 3) if handed else None,
    }


def _failed_on(results: dict) -> list:
    return [k for k, v in results.items()
            if k != "all_pass" and not v["pass"] and v.get("counts", True)]


def let_the_writer_choose() -> None:
    """FOR THIS PROCESS ONLY: an answer that leaves out some of the findings is
    not rejected.

    Step 4 of the citation check ("every finding the judge picked is cited")
    still runs and still records which findings were left out, but it does not
    count and is not fed back on a retry. Every other step is unchanged. The
    service's own check is not edited; this wraps it for the test.
    """
    real = checks.check_citations

    def relaxed(prose, findings, **kwargs):
        results = real(prose, findings, **kwargs)
        step = results["4_all_findings_cited"]
        step["pass_if_enforced"] = step["pass"]
        step["pass"] = True
        step["counts"] = False
        results["all_pass"] = all(
            v["pass"] for k, v in results.items()
            if k != "all_pass" and v.get("counts", True))
        return results

    checks.check_citations = relaxed


# ── one question ─────────────────────────────────────────────────────────────

def run_one(entry: dict, findings: list, stamp: str, label: str,
            counter) -> dict:
    turn_id = f"wt-{label}-{entry['id']}"
    started = time.time()
    out = writer_mod.consolidate(entry["question"], findings, run_date=stamp,
                                 turn_id=turn_id)
    seconds = round(time.time() - started, 1)

    calls = counter.for_turn(turn_id, "write")
    results = iter(out.check_results)
    attempts = []
    for call in calls:
        prose = (call["response_text"] or "").strip()
        item = {"attempt": call["attempt"], "seconds": call["seconds"],
                "finish_reason": call["finish_reason"],
                "completion_tokens": call["completion_tokens"],
                "reasoning_tokens": call["reasoning_tokens"],
                "prose": prose}
        if prose:
            item["failed_on"] = _failed_on(next(results, {}))
        else:
            item["failed_on"] = ["empty reply"]
        attempts.append(item)

    last = attempts[-1]["prose"] if attempts else ""
    return {
        "id": entry["id"], "question": entry["question"],
        "findings": len(findings),
        "seconds": seconds,
        "attempts": out.attempts,
        "lost": out.fell_back,
        "lost_on": (attempts[-1]["failed_on"] if out.fell_back and attempts
                    else []),
        "reason": out.reason,
        "tagged": out.tagged,
        # What was written, measured even when it was lost: a lost answer is
        # still evidence of how the wording made the model write.
        "measures": measure(out.tagged or last, findings) if (out.tagged
                                                             or last) else None,
        "checks": [{k: v for k, v in a.items() if k != "prose"}
                   for a in attempts],
        "attempt_prose": [a["prose"] for a in attempts],
    }


# ── the run ──────────────────────────────────────────────────────────────────

def pick(rows: list, only: list, sample: int | None) -> list:
    if only:
        wanted = set(only)
        missing = wanted - {e["id"] for e, _ in rows}
        if missing:
            raise SystemExit(f"not held, or held with no findings: "
                             f"{sorted(missing)}")
        return [r for r in rows if r[0]["id"] in wanted]
    if sample and sample < len(rows):
        # Spread from the fewest findings to the most, so a small run still
        # covers a one-finding answer and a twenty-finding one.
        by_size = sorted(rows, key=lambda r: (len(r[1]), r[0]["id"]))
        if sample == 1:
            return [by_size[len(by_size) // 2]]
        step = (len(by_size) - 1) / (sample - 1)
        chosen = {by_size[round(i * step)][0]["id"] for i in range(sample)}
        return [r for r in rows if r[0]["id"] in chosen]
    return rows


def _mid(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def summarise(results: list) -> dict:
    shown = [r for r in results if not r["lost"]]
    lost = [r for r in results if r["lost"]]
    m = [r["measures"] for r in shown if r["measures"]]
    sentences = sum(x["sentences"] for x in m) or 1
    return {
        "questions": len(results),
        "kept": len(shown),
        "lost": len(lost),
        "lost_on": dict(Counter(k for r in lost for k in r["lost_on"])),
        "lost_ids": [r["id"] for r in lost],
        "passed_first_try": sum(1 for r in shown if r["attempts"] == 1),
        "writer_calls": sum(r["attempts"] for r in results),
        "middle_seconds": _mid(r["seconds"] for r in results),
        "of_the_kept_answers": {
            "middle_findings_handed": _mid(x.get("findings_handed")
                                           for x in m),
            "middle_findings_used": _mid(x.get("findings_used") for x in m),
            "middle_words": _mid(x["words"] for x in m),
            "most_words": max((x["words"] for x in m), default=None),
            "middle_sentences": _mid(x["sentences"] for x in m),
            "middle_words_per_sentence": _mid(x["words_per_sentence"]
                                              for x in m),
            "share_of_long_sentences": round(
                sum(x["long_sentences"] for x in m) / sentences, 3),
            "middle_figures": _mid(x["figures"] for x in m),
            "middle_figures_per_sentence": _mid(x["figures_per_sentence"]
                                                for x in m),
            "share_of_sentences_with_many_figures": round(
                sum(x["sentences_with_many_figures"] for x in m) / sentences,
                3),
            "middle_coverage": _mid(x["coverage"] for x in m),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--label", help="name of this run (its output files)")
    parser.add_argument("--prompt-file",
                        help="writer instructions to test; default is the "
                             "live prompt")
    parser.add_argument("--model", help="writer model; default the configured")
    parser.add_argument("--max-tokens", type=int,
                        help="writer answer budget; default the configured")
    parser.add_argument("--allow-unused-findings", action="store_true",
                        help="test only: do not reject an answer for leaving "
                             "out some of the findings")
    parser.add_argument("--only", nargs="+", default=[], metavar="ID")
    parser.add_argument("--sample", type=int, metavar="N")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--compare", nargs="+", metavar="LABEL",
                        help="write one file putting two or more finished "
                             "runs side by side, and stop")
    args = parser.parse_args(argv)

    if args.compare:
        if len(args.compare) < 2:
            parser.error("--compare needs two or more run labels")
        path = write_comparison(args.compare)
        print(f"wrote {path}")
        return 0
    if not args.label or not re.fullmatch(r"[A-Za-z0-9_.-]+", args.label):
        parser.error("--label is needed: letters, digits, _ . - only")

    prompt_source = "the live prompt (context_brief.py)"
    if args.prompt_file:
        text = Path(args.prompt_file).read_text(encoding="utf-8").strip()
        if not text:
            parser.error(f"{args.prompt_file} is empty")
        context_brief.CONSOLIDATING_WRITER_PROMPT = text
        prompt_source = str(args.prompt_file)
    if args.model:
        config.WRITER_MODEL = args.model
    if args.max_tokens:
        config.WRITER_MAX_COMPLETION = args.max_tokens
    if args.allow_unused_findings:
        let_the_writer_choose()
    prompt_text = context_brief.CONSOLIDATING_WRITER_PROMPT

    corpus = corpus_mod.load()
    held = held_picks.load_held()
    try:
        rows = held_picks.usable(held, corpus)
    except held_picks.StaleHeldSet as exc:
        print(f"STOP: {exc}")
        return 1
    rows = pick(rows, args.only, args.sample)
    if not rows:
        print("STOP: no held question to run. Build the held set first.")
        return 1
    stamp = config.run_stamp_line()

    counter = held_picks.CallCounter(llm, cap=2 * len(rows))
    print(f"{len(rows)} question(s); writer {config.WRITER_MODEL}; prompt: "
          f"{prompt_source}; budget {config.WRITER_MAX_COMPLETION}; causal "
          f"{config.CAUSAL_CHECK}, direction {config.DIRECTION_CHECK}; "
          f"every-finding rule "
          f"{'OFF (test only)' if args.allow_unused_findings else 'on'}")
    with ThreadPoolExecutor(max(1, min(args.workers, len(rows)))) as pool:
        results = list(pool.map(
            lambda row: run_one(row[0], row[1], stamp, args.label, counter),
            rows))

    out = {
        "label": args.label,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "writer_model": config.WRITER_MODEL,
        "max_completion_tokens": config.WRITER_MAX_COMPLETION,
        "prompt_source": prompt_source,
        "prompt_sha256": hashlib.sha256(
            prompt_text.encode("utf-8")).hexdigest(),
        "prompt_text": prompt_text,
        "every_finding_rule": ("off (test only)" if args.allow_unused_findings
                               else "on"),
        "causal_mode": config.CAUSAL_CHECK,
        "direction_mode": config.DIRECTION_CHECK,
        "held_set": {"updated_at": held.get("updated_at"),
                     "corpus": held.get("corpus")},
        "summary": summarise(results),
        "spend": counter.spend(),
        "results": results,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{args.label}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    report = write_report(out)

    for r in results:
        m = r["measures"] or {}
        state = f"LOST on {r['lost_on']}" if r["lost"] else "kept"
        print(f"  {r['id']:<7} used {m.get('findings_used', 0):>2} of "
              f"{r['findings']:>2} findings  "
              f"{m.get('words', 0):>4} words  "
              f"{m.get('words_per_sentence', 0):>4} per sentence  "
              f"coverage {m.get('coverage')}  tries {r['attempts']}  {state}")
    print(json.dumps(out["summary"], indent=1))
    print(counter.spend_line())
    print(f"wrote {report}")
    return 0


# ── the files to read ────────────────────────────────────────────────────────

def _pct(value) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def _summary_rows(out: dict) -> list:
    s, k = out["summary"], out["summary"]["of_the_kept_answers"]
    lost_on = ", ".join(f"{n} on {c}" for c, n in s["lost_on"].items())
    return [
        ("Writer model", out["writer_model"]),
        ("Prompt", out["prompt_source"]),
        ("Every finding must be mentioned", out.get("every_finding_rule", "on")),
        ("Questions", s["questions"]),
        ("Answers kept", s["kept"]),
        ("Answers lost (plain sentences shown instead)",
         f"{s['lost']}" + (f" ({lost_on})" if lost_on else "")),
        ("Passed on the first try", s["passed_first_try"]),
        ("Writer calls", s["writer_calls"]),
        ("Seconds per answer, middle", s["middle_seconds"]),
        ("Findings used, of those handed (middle)",
         f"{k.get('middle_findings_used', '-')} of "
         f"{k.get('middle_findings_handed', '-')}"),
        ("Words per answer, middle", k["middle_words"]),
        ("Words per answer, most", k["most_words"]),
        ("Sentences per answer, middle", k["middle_sentences"]),
        ("Words per sentence, middle", k["middle_words_per_sentence"]),
        (f"Sentences over {LONG_SENTENCE_WORDS} words",
         _pct(k["share_of_long_sentences"])),
        ("Figures per answer, middle", k["middle_figures"]),
        ("Figures per sentence, middle", k["middle_figures_per_sentence"]),
        (f"Sentences with more than {MANY_FIGURES} figures",
         _pct(k["share_of_sentences_with_many_figures"])),
        ("Share of the handed figures that appear, middle",
         _pct(k["middle_coverage"])),
    ]


def _answer_block(r: dict) -> list:
    m = r["measures"] or {}
    lines = [f"- used {m.get('findings_used', '-')} of {r['findings']} "
             f"findings, {m.get('words', 0)} words, "
             f"{m.get('sentences', 0)} sentences, "
             f"{m.get('words_per_sentence', 0)} words per sentence, "
             f"{m.get('figures', 0)} figures, "
             f"{_pct(m.get('coverage'))} of the handed figures, "
             f"{r['attempts']} tries"]
    if r["lost"]:
        why = ", ".join(r["lost_on"]) or r["reason"] or "no reply"
        lines.append(f"- **LOST** on {why}. "
                     f"The officer would see the plain stored sentences. "
                     f"What the writer wrote on its last try:")
        text = checks.strip_tags(r["attempt_prose"][-1]
                                 if r["attempt_prose"] else "")
    else:
        text = checks.strip_tags(r["tagged"])
    lines += ["", text or "(nothing written)", ""]
    return lines


def write_report(out: dict) -> Path:
    lines = [f"# Writer test: {out['label']}", "",
             f"Run {out['generated_at']} on the held judge picks "
             f"(held {out['held_set']['updated_at']}).", "",
             "| | |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in _summary_rows(out)]
    lines += ["", "## The instructions the writer was given", "",
              "```", out["prompt_text"], "```", "", "## The answers", ""]
    for r in out["results"]:
        lines += [f"### {r['id']} - {r['question']}", ""] + _answer_block(r)
    path = OUT_DIR / f"{out['label']}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_comparison(labels: list) -> Path:
    runs = []
    for label in labels:
        path = OUT_DIR / f"{label}.json"
        if not path.exists():
            raise SystemExit(f"no finished run called {label} ({path})")
        runs.append(json.loads(path.read_text(encoding="utf-8")))
    lines = [f"# Writer tests side by side: {', '.join(labels)}", "",
             "| | " + " | ".join(labels) + " |",
             "|---|" + "---|" * len(labels)]
    tables = [_summary_rows(run) for run in runs]
    for i, (name, _) in enumerate(tables[0]):
        lines.append(f"| {name} | "
                     + " | ".join(str(t[i][1]) for t in tables) + " |")
    by_id = [{r["id"]: r for r in run["results"]} for run in runs]
    shared = [r["id"] for r in runs[0]["results"]
              if all(r["id"] in ids for ids in by_id)]
    lines += ["", f"## The {len(shared)} questions every run answered", ""]
    for qid in shared:
        lines += [f"### {qid} - {by_id[0][qid]['question']}", ""]
        for label, ids in zip(labels, by_id):
            lines += [f"**{label}**", ""] + _answer_block(ids[qid])
    path = OUT_DIR / ("_vs_".join(labels) + ".md")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(main())

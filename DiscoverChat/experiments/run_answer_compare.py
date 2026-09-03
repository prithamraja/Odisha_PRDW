#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D7 D7.3 — before/after over 15 answers, and the latency that goes with it.

    python DiscoverChat/experiments/run_answer_compare.py
    python DiscoverChat/experiments/run_answer_compare.py --only new

TWO ARMS, EACH THE WHOLE CONFIGURATION RATHER THAN ONE SWITCH.

  OLD  the pre-WP-D7 service exactly: classifier `gpt-5.5`, no consolidation
       (so an answer is its bare glossary-translated sentences, and connective
       prose only above FULL_RENDER_MAX), inline verifier ON.
  NEW  the D7 service: classifier `gpt-5.4-nano`, the consolidating writer with
       checkable citations, inline verifier OFF.

Comparing one switch at a time would measure something nobody will ever run.
The operator's question is "what does the officer get, and how long do they
wait, before and after", and that is a comparison of two whole configurations.

EACH ARM GETS ITS OWN `Retriever`, and this matters more than it looks.
`Retriever` memoises query embeddings per instance, so a second arm reusing the
first one's retriever would embed nothing and post a latency that no user will
ever see. Two instances share the loaded corpus (it is cached at module level)
and nothing else.

THE TABLE IS FOR THE OPERATOR TO READ. Narrative quality is their acceptance,
not this suite's: nothing here scores the prose. What the suite asserts is the
mechanical part -- every citation checks out, every selected finding is cited,
the causal scan is green -- and what it PRINTS is the two answers side by side.
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

import logging                                                    # noqa: E402
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import assemble, checks, config, render          # noqa: E402
from DiscoverChat.retrieval import Retriever                       # noqa: E402

OUT_JSON = config.HERE / "experiments" / "answer_compare.json"
OUT_MD = config.HERE / "experiments" / "answer_compare.md"

# Fifteen, and the brief's coverage conditions are met by construction rather
# than by hoping: six route to DECOMPOSE (so at least three will carry
# decompositions), one is aimed at an evenly-spread decomposition, and one is
# the causally-worded decompose turn that must carry the scope note.
QUESTIONS = [
    ("Is spending on track?", "the broad sweep"),
    ("How is Chikilli doing?", "one Gram Panchayat by name"),
    ("Where is money planned but not spent?", "the underspend question"),
    ("How is Barpali block doing?", "one block by name"),
    ("Which places are behaving differently from the rest?", "exceptions"),
    ("Which blocks account for the shortfall?", "decompose"),
    ("Where does the gap sit?", "decompose"),
    ("Break down spending by block", "decompose"),
    ("How is the total split across districts?", "decompose"),
    ("Who is driving the shortfall?", "decompose, causally worded — scope note"),
    ("How is tied grant planned split across fiscal years?",
     "decompose, aimed at an evenly-spread record"),
    ("Break it down by fiscal year", "decompose"),
    ("Tell me about untied grants.", "a measure, no place"),
    ("Anything I should be looking at in Ganjam?", "open-ended, one district"),
    ("What is the position on abandoned works?", "a status question"),
]

ARMS = {
    "old": {"classifier": "gpt-5.5", "consolidate": False, "inline_verify": True},
    "new": {"classifier": "gpt-5.4-nano", "consolidate": True,
            "inline_verify": False},
}


def _apply(arm: dict) -> None:
    """The arm's configuration, set where the code actually reads it.

    Every one of these is read at CALL time rather than captured at import, so
    setting the module attribute is the whole of what a deployment would do
    with an environment variable.
    """
    config.CLASSIFIER_MODEL = arm["classifier"]
    config.CONSOLIDATE = arm["consolidate"]
    config.INLINE_VERIFY = arm["inline_verify"]


def run_arm(name: str, retriever) -> list:
    _apply(ARMS[name])
    assembler = assemble.Assembler(retriever, allow_model=True)
    out = []
    for index, (question, why) in enumerate(QUESTIONS, start=1):
        started = time.time()
        answer = assembler.answer(question, turn_id=f"cmp-{name}-{index}")
        elapsed = round(time.time() - started, 1)
        entry = {
            "n": index, "question": question, "why_in_the_set": why,
            "seconds": elapsed,
            "move": answer.move,
            "findings": [f.id for f in answer.findings],
            "n_findings": len(answer.findings),
            "decompositions": sum(1 for f in answer.findings
                                  if f.is_decomposition),
            "evenness": sum(1 for f in answer.findings
                            if f.is_decomposition
                            and f.data.get("shape") == "even"),
            "prose": answer.prose,
            "text": answer.text,
            "tagged_text": answer.tagged_text,
            "words": len(answer.text.split()),
        }
        if answer.tagged_text:
            result = checks.check_citations(answer.tagged_text, answer.findings,
                                            run_date=answer.stamp)
            bindings = checks.bind_numerals(answer.tagged_text, answer.findings,
                                            run_date=answer.stamp)
            entry["citation_check"] = {
                k: v for k, v in result.items() if k != "3_causal"}
            entry["citation_check"]["causal_pass"] = result["3_causal"]["pass"]
            entry["numerals_bound"] = sum(1 for b in bindings if b["matched"])
            entry["numerals_total"] = len(bindings)
            entry["numerals_uncited"] = [b["token"] for b in bindings
                                         if b["matched"] is None
                                         and not b["exempt"]]
            entry["html"] = render.to_html(answer.tagged_text, answer.findings,
                                           run_date=answer.stamp)
        print(f"  {name:<3} {index:>2}/{len(QUESTIONS)}  {elapsed:>5}s  "
              f"{entry['n_findings']:>2} findings  "
              f"prose={entry['prose'].get('used')}  {question[:44]}")
        out.append(entry)
    return out


def _percentiles(values: list) -> dict:
    if not values:
        return {"p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    ordered = sorted(values)
    return {"p50": statistics.median(ordered),
            "p90": ordered[max(0, int(len(ordered) * 0.9) - 1)],
            "min": ordered[0], "max": ordered[-1]}


def _table(old: list, new: list) -> str:
    lines = ["# WP-D7 D7.3 — before and after, 15 answers", "",
             "`old` is the pre-D7 service (classifier `gpt-5.5`, bare "
             "glossary-translated sentences, inline verifier on). `new` is the "
             "consolidating writer with checked citations and no inline "
             "verifier. Narrative quality is the operator's acceptance; "
             "nothing here scores it.", ""]
    lines += ["| # | question | old s | new s | findings | old (bare sentences) | new (narrative) |",
              "|---|---|---|---|---|---|---|"]
    for a, b in zip(old, new):
        def cell(text):
            return (text or "").replace("\n", "<br>").replace("|", "\\|")
        lines.append(
            f"| {a['n']} | {cell(a['question'])} | {a['seconds']} | "
            f"{b['seconds']} | {a['n_findings']} -> {b['n_findings']} | "
            f"{cell(a['text'])} | {cell(b['text'])} |")
    lines.append("")
    lines.append("## The same answers at length")
    for a, b in zip(old, new):
        lines += [f"### {a['n']}. {a['question']}",
                  f"*In the set for: {a['why_in_the_set']}*", "",
                  f"**OLD** ({a['seconds']} s, {a['n_findings']} findings, "
                  f"{a['words']} words)", "", "```", a["text"], "```", "",
                  f"**NEW** ({b['seconds']} s, {b['n_findings']} findings, "
                  f"{b['words']} words, fell_back="
                  f"{b['prose'].get('fell_back')})", "", "```", b["text"], "```",
                  ""]
        if b.get("tagged_text"):
            lines += ["**NEW, with the citation tags the officer never sees**",
                      "", "```", b["tagged_text"], "```", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="WP-D7 D7.3 before/after")
    parser.add_argument("--only", choices=["old", "new"], default=None)
    args = parser.parse_args(argv)

    print(f"  WP-D7 D7.3 — {len(QUESTIONS)} questions, two whole configurations\n")
    arms = {}
    for name in ("old", "new"):
        if args.only and args.only != name:
            continue
        print(f"  --- arm {name}: {ARMS[name]} ---")
        arms[name] = run_arm(name, Retriever())
        print()

    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "arms": ARMS, "questions": len(QUESTIONS), "results": arms}
    for name, results in arms.items():
        report[f"latency_{name}"] = _percentiles([r["seconds"] for r in results])

    if "new" in arms:
        new = arms["new"]
        narratives = [r for r in new if r.get("tagged_text")]
        failures = [r for r in narratives
                    if not r["citation_check"]["all_pass"]]
        fallbacks = [r for r in new if r["n_findings"]
                     and not r.get("tagged_text")]
        report["citations"] = {
            "answers_with_findings": sum(1 for r in new if r["n_findings"]),
            "narratives": len(narratives),
            "fallbacks": len(fallbacks),
            "fallback_rate": (len(fallbacks) / max(1, sum(1 for r in new
                                                          if r["n_findings"]))),
            "regenerated_once": sum(1 for r in narratives
                                    if r["prose"].get("attempts", 1) > 1),
            "failing_narratives_shown_to_user": len(failures),
            "numerals_bound": sum(r.get("numerals_bound", 0) for r in narratives),
            "numerals_total": sum(r.get("numerals_total", 0) for r in narratives),
            "uncited_numerals": [t for r in narratives
                                 for t in r.get("numerals_uncited", [])],
            "answers_with_decompositions": sum(1 for r in new
                                               if r["decompositions"]),
            "answers_with_evenness": sum(1 for r in new if r["evenness"]),
        }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    if "old" in arms and "new" in arms:
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write(_table(arms["old"], arms["new"]))

    for name in arms:
        p = report[f"latency_{name}"]
        print(f"  {name}: p50 {p['p50']}s  p90 {p['p90']}s  "
              f"(min {p['min']}s, max {p['max']}s)")
    if "citations" in report:
        c = report["citations"]
        print(f"\n  narratives {c['narratives']} | fallbacks {c['fallbacks']} "
              f"({c['fallback_rate']:.1%}) | regenerated once "
              f"{c['regenerated_once']} | failing narratives shown "
              f"{c['failing_narratives_shown_to_user']}")
        print(f"  numerals bound {c['numerals_bound']}/{c['numerals_total']}, "
              f"uncited {len(c['uncited_numerals'])}")
        print(f"  answers carrying decompositions "
              f"{c['answers_with_decompositions']}, evenness "
              f"{c['answers_with_evenness']}")
    print(f"\n  written to {OUT_JSON}" + ("" if args.only else f" and {OUT_MD}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

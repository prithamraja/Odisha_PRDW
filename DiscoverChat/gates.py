#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The D5.2 gate: a deterministic behaviour suite, green as ONE command.

    python DiscoverChat/gates.py            offline checks only (no model calls)
    python DiscoverChat/gates.py --live     the same, plus the live turn checks

In the spirit of `Ask/prdw_gates.py`: one command, one exit code, every check
naming what it proves rather than only whether it passed.

WHY THE DEFAULT IS OFFLINE. Routing is nondeterministic — the bootstrap's own
lesson is that identical replays flip about 3% of questions — so a gate whose
green depends on a model call is a gate that goes red for reasons nobody
changed. Every behaviour the brief names as a gate condition is therefore
checked on a deterministic path:

  number-lookup -> decline + Ask route      the RULE layer decides these, so the
                                            check is on rules, not on a model
  why-question  -> reframe with limits      likewise
  no-match      -> honest "nothing on this" a floor comparison, no model
  numerals traceable                        the mechanical check itself
  causal-verb scan green                    a word list over every output
  run stamp present                         string containment

`--live` then runs real turns end to end, including the writer and the verifier.
It is the mode to run before a deploy; it is not what keeps the suite green.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.ERROR)

from DiscoverChat import (                                     # noqa: E402
    assemble, causal_gate, checks, classifier, config, corpus as corpus_mod,
)
from DiscoverChat.retrieval import Retriever                    # noqa: E402

RESULTS = []


def check(name: str, proves: str):
    def decorator(fn):
        RESULTS.append((name, proves, fn))
        return fn
    return decorator


# ── 1. The corpus is the one that was built ──────────────────────────────────
@check("corpus-pin", "the corpus is served under the pin it was embedded with")
def _corpus_pin(ctx):
    stamp = config.assert_pin_matches_corpus()
    corpus = ctx["corpus"]
    assert len(corpus) == stamp["records"], (
        f"{len(corpus)} records loaded, stamp says {stamp['records']}")
    assert corpus.vectors.shape == (len(corpus), config.EMBED_DIMS)
    return f"{len(corpus):,} findings, pin {stamp['embedding_pin_fingerprint']}"


@check("corpus-deterministic-text",
       "every displayed sentence comes from the engine, not from a model")
def _sentences_are_engine(ctx):
    """The engine's sentences have a fixed opening. A model-written sentence
    would not, so this is a cheap standing check that nothing has started
    generating finding text."""
    corpus = ctx["corpus"]
    bad = [f.id for f in corpus.all()
           if not (f.sentence.startswith("Across ") or f.sentence == "(no commonness)")]
    assert not bad, f"{len(bad)} findings do not read like engine output: {bad[:5]}"
    return f"{len(corpus):,} sentences all in the engine's template form"


# ── 2. Number-lookup declines and routes to Ask ──────────────────────────────
LOOKUP_QUESTIONS = [
    "How much was spent in Khordha last year?",
    "How many activities are ongoing in Barpali block?",
    "What is the total sanctioned amount for 2024-2025?",
    "Give me the list of abandoned works.",
    "Who is the current Sarpanch of Chikilli?",
    "Show me the top 10 GPs by expenditure.",
]


@check("lookup-declines", "a number-lookup declines and names Ask, deterministically")
def _lookup(ctx):
    for question in LOOKUP_QUESTIONS:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.LOOKUP, (
            f"not routed to Ask by rule: {question!r} -> {routing}")
    answer = ctx["assembler"].answer(LOOKUP_QUESTIONS[0])
    assert answer.move == classifier.LOOKUP
    assert "Ask" in answer.text, "the decline does not name Ask"
    assert not answer.findings, "a decline showed findings"
    return f"{len(LOOKUP_QUESTIONS)} lookup questions, all declined by rule"


@check("lookup-never-proxied", "the decline contains no figure of its own")
def _lookup_no_numbers(ctx):
    answer = ctx["assembler"].answer("How much was spent in Khordha last year?")
    stripped = answer.text.replace(answer.stamp, "")
    found = checks.numerals(stripped)
    assert not found, f"the decline carried figures: {found}"
    return "no numeral in the decline text"


# ── 3. Why-questions get the reframe ─────────────────────────────────────────
WHY_QUESTIONS = [
    "Why is spending low in Chikilli?",
    "What is causing the year-end payment spike?",
    "Why do so many activities have no asset category?",
    "What is the reason for the drop in sanctions?",
    "Explain why Boipariguda is different.",
    "How come Ganjam is an exception?",
]


@check("why-reframes", "a why-question is reframed, never answered with a cause")
def _why(ctx):
    for question in WHY_QUESTIONS:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.WHY, (
            f"not routed to the reframe by rule: {question!r} -> {routing}")
    answer = ctx["assembler"].answer(WHY_QUESTIONS[0])
    assert answer.move == classifier.WHY
    assert "cannot establish what causes what" in answer.text, (
        "the reframe does not state the limit")
    assert "next" in answer.text.lower(), "the reframe offers no next step"
    return f"{len(WHY_QUESTIONS)} why-questions, all reframed by rule"


# ── 4. No-match is honest ────────────────────────────────────────────────────
NO_MATCH_QUESTIONS = [
    "What is the price of onions in Cuttack market?",
    "What is the rainfall forecast for Koraput next week?",
    "How many teachers are posted in the block primary schools?",
    "Give me the list of pending court cases against the panchayat.",
]


@check("no-match-honest", "nothing above the floor produces an honest miss")
def _no_match(ctx):
    assembler = ctx["assembler"]
    for question in NO_MATCH_QUESTIONS:
        answer = assembler.answer(question)
        if answer.move == classifier.LOOKUP:
            continue        # declining to Ask is also an honest non-answer
        assert not answer.findings, (
            f"out-of-scope question was answered with {len(answer.findings)} "
            f"findings: {question!r}")
        assert "nothing on this" in answer.text, (
            f"the miss is not stated honestly: {question!r}")
    return f"{len(NO_MATCH_QUESTIONS)} out-of-scope questions, none answered"


@check("floor-not-topn", "the floor is a floor: no answer is manufactured")
def _floor(ctx):
    result = ctx["retriever"].score(
        "What is the price of onions in Cuttack market?")
    assert not result.hits, "a below-floor question produced hits"
    assert result.best_cosine < result.threshold, (
        f"best cosine {result.best_cosine} is above the threshold "
        f"{result.threshold} — the fixture no longer tests the floor")
    return (f"best cosine {result.best_cosine:.3f} < threshold "
            f"{result.threshold}, zero shown")


# ── 5. Every numeral traceable ───────────────────────────────────────────────
@check("numerals-traceable",
       "every numeral in every answer traces to a corpus sentence")
def _numerals(ctx):
    assembler = ctx["assembler"]
    corpus = ctx["corpus"]
    questions = (LOOKUP_QUESTIONS + WHY_QUESTIONS + NO_MATCH_QUESTIONS
                 + ["How is Chikilli doing?", "Is spending on track?",
                    "Where is money planned but not spent?",
                    "How is Barpali block doing?"])
    checked = 0
    for question in questions:
        answer = assembler.answer(question)
        allowed = set()
        for finding in answer.findings:
            allowed |= set(checks.numerals(checks.supplied_text([finding])))
        allowed |= set(checks.numerals(assemble.ASK_ROUTE_MESSAGE))
        allowed |= set(checks.numerals(answer.stamp))
        allowed |= {str(config.ANSWER_CAP)}
        for token in checks.numerals(answer.text):
            checked += 1
            assert token in allowed, (
                f"answer to {question!r} used {token!r}, which is in none of "
                f"its findings")
    return f"{checked} numerals across {len(questions)} answers, all traceable"


# ── 6. The causal-verb scan ──────────────────────────────────────────────────
@check("causal-scan", "no answer asserts a cause (D41)")
def _causal(ctx):
    assembler = ctx["assembler"]
    questions = (LOOKUP_QUESTIONS + WHY_QUESTIONS + NO_MATCH_QUESTIONS
                 + ["How is Chikilli doing?", "Is spending on track?",
                    "Which places are behaving differently from the rest?"])
    for question in questions:
        answer = assembler.answer(question)
        result = causal_gate.check(answer.text)
        assert result["pass"], (
            f"answer to {question!r} asserts a cause: "
            f"{[p['surface'] for p in result['problems']]}")
    return f"{len(questions)} answers scanned, none causal"


@check("causal-gate-catches", "the ban actually fires on causal wording")
def _causal_catches(ctx):
    """A gate that never fires proves nothing. These must FAIL."""
    must_fail = [
        "The underspend is caused by late sanctions.",
        "Weak evidence uploads are driving the gap.",
        "Spending fell because of the approval backlog.",
        "This explains the year-end spike.",
        "The delay led to lower expenditure.",
        "Late approvals result in unspent funds.",
    ]
    for text in must_fail:
        assert not causal_gate.check(text)["pass"], f"ban missed: {text!r}"
    must_pass = [
        "The analysis cannot say what causes this.",
        "Underspend and weak evidence occur in the same places.",
        "Nothing here establishes which way this runs.",
        "These blocks are associated with lower spending.",
    ]
    for text in must_pass:
        assert causal_gate.check(text)["pass"], (
            f"ban fired on honest wording: {text!r} -> "
            f"{causal_gate.check(text)['problems']}")
    return (f"{len(must_fail)} causal constructions caught, "
            f"{len(must_pass)} honest sentences passed")


# ── 7. The run stamp ─────────────────────────────────────────────────────────
@check("run-stamp", "every answer carries the run stamp")
def _stamp(ctx):
    assembler = ctx["assembler"]
    stamp = config.run_stamp_line()
    questions = (LOOKUP_QUESTIONS[:2] + WHY_QUESTIONS[:2]
                 + NO_MATCH_QUESTIONS[:2]
                 + ["How is Chikilli doing?", "Is spending on track?"])
    for question in questions:
        answer = assembler.answer(question)
        assert stamp in answer.text, f"no run stamp on the answer to {question!r}"
    return f"{stamp!r} present on {len(questions)} answers"


# ── 8. Findings are shown verbatim ───────────────────────────────────────────
@check("findings-verbatim", "a shown finding's sentence is the corpus's, byte for byte")
def _verbatim(ctx):
    assembler = ctx["assembler"]
    for question in ("How is Chikilli doing?", "Is spending on track?",
                     "Where is money planned but not spent?"):
        answer = assembler.answer(question)
        for finding in answer.findings:
            assert finding.sentence in answer.text, (
                f"finding {finding.id} was not shown verbatim")
            assert (ctx["corpus"].get(finding.id).sentence == finding.sentence)
    return "every shown sentence identical to the corpus record"


# ── 9. Coverage is stated for unranked findings ──────────────────────────────
@check("coverage-stated",
       "a finding that failed ranking says so when it is shown (D42 question 4)")
def _coverage(ctx):
    answer = ctx["assembler"].answer("Is spending on track?")
    unranked = [f for f in answer.findings if not f.in_feed and not f.view_rank]
    for finding in unranked:
        assert finding.coverage_line() in answer.text, (
            f"{finding.id} shown without its coverage line")
    return (f"{len(unranked)} of {len(answer.findings)} shown findings are "
            f"outside the ranked shortlist, each labelled")


# ── live-only ────────────────────────────────────────────────────────────────
def live_checks(ctx) -> list:
    """Real turns on the JUDGED path — writer and verifier included.

    This is where the out-of-scope check has to live once the judge is on. The
    offline suite proves it against a threshold, which is a comparison and
    cannot be talked round; in production the floor is 0.50 and 4 of these 5
    questions reach the judge with a non-empty pool, so **the judge is the only
    thing standing between them and a confidently-wrong answer**. It is the
    single most important number in the whole system and it is measured here,
    with repeats, because one pass of a nondeterministic component is not
    evidence.
    """
    out = []
    assembler = assemble.Assembler(ctx["retriever"], allow_model=True)

    repeats = int(os.getenv("DISCOVERCHAT_GATE_REPEATS", "2"))
    false_answers, runs = 0, 0
    for _ in range(repeats):
        for question in NO_MATCH_QUESTIONS + ["Who is the current Sarpanch of Chikilli?"]:
            answer = assembler.answer(question)
            runs += 1
            if answer.move != classifier.LOOKUP and answer.findings:
                false_answers += 1
    out.append(("live:out-of-scope-silent",
                f"{runs} runs over {len(NO_MATCH_QUESTIONS) + 1} out-of-scope "
                f"questions, {false_answers} answered "
                f"({false_answers / runs:.1%} false-answer rate)",
                false_answers == 0))

    for question in ("Is spending on track?",
                     "Which places are behaving differently from the rest?",
                     "How is Chikilli doing?"):
        answer = assembler.answer(question)
        judged = answer.retrieval.get("judge", {})
        result = checks.check_prose(answer.text, answer.findings,
                                    corpus_roster=assembler._roster)
        ok = (result["e_causal"]["pass"]
              and not judged.get("hallucinated_ids")
              and len(answer.findings) <= config.ANSWER_CAP)
        out.append((f"live:{question[:26]}",
                    f"judge kept {len(answer.findings)} of "
                    f"{judged.get('pool', '?')} pooled "
                    f"[{judged.get('source')}] | prose used="
                    f"{answer.prose.get('used')} | causal_pass="
                    f"{result['e_causal']['pass']} | invented ids="
                    f"{len(judged.get('hallucinated_ids', []))}",
                    ok))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="DiscoverChat D5.2 gate")
    parser.add_argument("--live", action="store_true",
                        help="also run real turns through the writer/verifier")
    args = parser.parse_args(argv)

    retriever = Retriever()
    ctx = {
        "corpus": corpus_mod.load(),
        "retriever": retriever,
        # allow_model=False forces the THRESHOLD path, so the default suite is
        # deterministic by construction. The judged path is production; it is
        # gated under --live, where the out-of-scope check is repeated.
        "assembler": assemble.Assembler(retriever, allow_model=False),
    }

    failures = 0
    print(f"  DiscoverChat gate — {len(ctx['corpus']):,} findings, "
          f"candidate set {ctx['corpus'].meta.get('candidate_set_id')}\n")
    for name, proves, fn in RESULTS:
        try:
            detail = fn(ctx)
            print(f"  PASS  {name:<26} {proves}")
            print(f"        {detail}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {name:<26} {proves}")
            print(f"        {exc}")
        except Exception as exc:                              # pragma: no cover
            failures += 1
            print(f"  ERROR {name:<26} {type(exc).__name__}: {exc}")

    if args.live:
        print("\n  ---- live turns (model calls) ----")
        for name, detail, ok in live_checks(ctx):
            print(f"  {'PASS ' if ok else 'FAIL '} {name:<26} {detail}")
            failures += 0 if ok else 1

    total = len(RESULTS)
    print(f"\n  {total - failures}/{total} checks green"
          + ("" if not failures else f" — {failures} FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

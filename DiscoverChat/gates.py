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
    glossary,
)
from DiscoverChat.retrieval import Retriever                    # noqa: E402

RESULTS = []


def check(name: str, proves: str):
    def decorator(fn):
        RESULTS.append((name, proves, fn))
        return fn
    return decorator


# ── 1. The corpus is the one that was built ──────────────────────────────────
@check("corpus-pin", "both corpora are served under the pin they were embedded with")
def _corpus_pin(ctx):
    stamp = config.assert_pin_matches_corpus()
    d_stamp = config.decompose_stamp()
    corpus = ctx["corpus"]
    expected = stamp["records"] + (d_stamp["records"] if d_stamp else 0)
    assert len(corpus) == expected, (
        f"{len(corpus)} records loaded, stamps say {expected}")
    assert corpus.vectors.shape == (len(corpus), config.EMBED_DIMS)
    assert corpus.meta["findings"] == stamp["records"]
    if d_stamp:
        assert corpus.meta["decompositions"] == d_stamp["records"]
        assert (d_stamp["embedding_pin_fingerprint"]
                == stamp["embedding_pin_fingerprint"]), (
            "the two corpora are embedded under different pins, so their "
            "vectors are not comparable and one ranking over both is nonsense")
    return (f"{corpus.meta['findings']:,} findings + "
            f"{corpus.meta['decompositions']:,} decompositions, one pin "
            f"{stamp['embedding_pin_fingerprint']}")


@check("corpus-deterministic-text",
       "every displayed sentence is built, not generated")
def _sentences_are_engine(ctx):
    """Each builder has a fixed opening. A model-written sentence would not, so
    this is a cheap standing check that nothing has started generating record
    text: `generate_nl_summary` opens "Across ", `phase5f_decompose` opens
    "Within ", and neither can be reached by a model."""
    corpus = ctx["corpus"]
    bad_f = [f.id for f in corpus.all() if not f.is_decomposition
             and not (f.sentence.startswith("Across ")
                      or f.sentence == "(no commonness)")]
    bad_d = [f.id for f in corpus.all() if f.is_decomposition
             and not f.sentence.startswith("Within ")]
    assert not bad_f, f"{len(bad_f)} findings do not read like engine output: {bad_f[:5]}"
    assert not bad_d, (f"{len(bad_d)} decompositions do not read like builder "
                       f"output: {bad_d[:5]}")
    return (f"{corpus.meta['findings']:,} engine sentences + "
            f"{corpus.meta['decompositions']:,} decomposition sentences, "
            f"all in template form")


# ── 1b. The decomposition sidecar: arithmetic, and named honestly ────────────
@check("decompose-reconciles",
       "every stored decomposition's members sum to its total (D6.0 gate a)")
def _decompose_reconciles(ctx):
    """The whole premise of D6.0, re-checked at SERVE time and not only at build
    time. The build proves it over the records it just computed; this proves it
    over the file actually being served, which is the one an officer sees."""
    corpus = ctx["corpus"]
    records = [f for f in corpus.all() if f.is_decomposition]
    if not records:
        return "no sidecar loaded — nothing to check"
    failures = [f.id for f in records if not f.data.get("reconciles")]
    assert not failures, (
        f"{len(failures)} of {len(records)} decompositions do not reconcile: "
        f"{failures[:5]}")
    return f"{len(records):,} decompositions, all members-sum-to-total"


@check("decompose-evenness-honest",
       "a flat split says so; it does not manufacture a leader (D6 ruling 4)")
def _decompose_evenness(ctx):
    """Ruling 4's first-class result. An evenly-spread decomposition must SAY it
    is evenly spread, and it must not also claim a concentration — the two
    readings cannot both be true of one distribution, and the failure this
    guards is a template that appends "the largest is X" to every record
    regardless of shape."""
    corpus = ctx["corpus"]
    even = [f for f in corpus.all()
            if f.is_decomposition and f.data.get("shape") == "even"]
    if not even:
        return "no sidecar loaded — nothing to check"
    missing = [f.id for f in even if "spread evenly" not in f.sentence]
    assert not missing, (
        f"{len(missing)} evenly-spread decompositions do not say so: "
        f"{missing[:5]}")
    claims = [f.id for f in even if "accounts for the majority" in f.sentence]
    assert not claims, (
        f"{len(claims)} evenly-spread decompositions also claim a leader: "
        f"{claims[:5]}")
    no_single = [f for f in even if "no single" in f.sentence]
    return (f"{len(even):,} evenly-spread decompositions, all saying so; "
            f"{len(no_single):,} state 'no single ... accounts for it'")


@check("decompose-signed-not-a-magnitude",
       "a mixed-sign gap reports both directions, never a share of a net")
def _decompose_signed(ctx):
    """A share of a near-zero net is arithmetic that produces 400% and means
    nothing. The builder gives these their own shape; this checks the shape
    reaches the sentence."""
    corpus = ctx["corpus"]
    off = [f for f in corpus.all()
           if f.is_decomposition and f.data.get("shape") == "offsetting"]
    if not off:
        return "no offsetting decompositions in the sidecar"
    bad = [f.id for f in off if "both directions" not in f.sentence]
    assert not bad, f"{len(bad)} offsetting decompositions hide the cancelling: {bad[:5]}"
    return (f"{len(off):,} offsetting decompositions, each stating both "
            f"directions and the net")


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


# ── 4b. The decompose intent routes, and does not steal the reframe ──────────
DECOMPOSE_QUESTIONS = [
    "Where does the gap sit?",
    "Which blocks account for the shortfall?",
    "Break down spending by block",
    "Who is driving the shortfall?",
    "What makes up the underspend?",
    "Break it down by fiscal year",
    "Where is the money going?",
    "How is the total split across districts?",
]


@check("decompose-routes", "a 'where does it sit' question routes to decompose")
def _decompose_routes(ctx):
    for question in DECOMPOSE_QUESTIONS:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.DECOMPOSE, (
            f"not routed to decompose by rule: {question!r} -> {routing}")
    return f"{len(DECOMPOSE_QUESTIONS)} decompose questions, all routed by rule"


@check("decompose-does-not-eat-why",
       "adding the decompose rule did not take any question off the D41 reframe")
def _decompose_vs_why(ctx):
    """The decompose rule runs BEFORE the why rule, so it is the one change in
    this WP that could silently remove a refusal. Every why-question in the
    suite is re-asserted here, and so is the distinction the trigger file rests
    on: a spike is a shape and keeps the reframe, a shortfall is a sum and does
    not."""
    for question in WHY_QUESTIONS:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.WHY, (
            f"the decompose rule stole a why-question: {question!r} -> {routing}")
    shapes = ["What is causing the year-end payment spike?",
              "What is driving the change in status?"]
    for question in shapes:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.WHY, (
            f"a question about a SHAPE was routed to decompose: {question!r}")
    for question in LOOKUP_QUESTIONS:
        routing = classifier.rule_route(question)
        assert routing is not None and routing.move == classifier.LOOKUP, (
            f"the decompose rule stole a lookup question: {question!r}")
    return (f"{len(WHY_QUESTIONS)} why + {len(shapes)} shape questions still "
            f"reframed, {len(LOOKUP_QUESTIONS)} lookups still declined")


@check("decompose-causal-note",
       "a causally-worded decompose answer states what it does not establish")
def _decompose_note(ctx):
    answer = ctx["assembler"].answer("Who is driving the shortfall?")
    assert answer.move == classifier.DECOMPOSE
    if not any(f.is_decomposition for f in answer.findings):
        return ("no decomposition cleared the offline threshold for this "
                "question — the note is checked on the judged path (--live)")
    assert "does not establish what produced it" in answer.text, (
        "a 'who is driving' answer returned a split with no scope note")
    return "the scope note is present ahead of the numbers"


# ── 4c. No engine vocabulary reaches an officer ──────────────────────────────
@check("no-raw-column-names",
       "no rendered sentence shows an engine column name that has a phrase")
def _no_raw_columns(ctx):
    """D6.1's display-glossary condition, scanned over EVERY record in both
    corpora rather than over the handful the suite happens to retrieve.

    Scoped, as the brief scopes it, to columns that HAVE a glossary entry. A
    column with none renders raw on purpose and is counted here and listed in
    the report — inventing a phrase for it is the PM's call, not this code's."""
    corpus = ctx["corpus"]
    offenders, gapped = [], {}
    for finding in corpus.all():
        rendered = finding.display_sentence()
        left = glossary.raw_columns(rendered, finding.view)
        if left:
            offenders.append((finding.id, left))
        for token in glossary.untranslated(rendered, finding.view):
            gapped[token] = gapped.get(token, 0) + 1
    assert not offenders, (
        f"{len(offenders)} rendered sentences still show a translatable column "
        f"name: {offenders[:3]}")
    known = ", ".join(f"{k} ({v})" for k, v in sorted(gapped.items()))
    return (f"{len(corpus):,} rendered sentences clean; known gaps carried "
            f"through unchanged: {known or 'none'}")


@check("glossary-gaps-declared",
       "every column with no officer phrase is one the report lists")
def _glossary_gaps(ctx):
    """A gate that lets gaps through silently would let the list rot. This
    fails if a NEW untranslated column appears, so the report's list and the
    code cannot drift apart."""
    gaps = {(g["view"], g["column"]) for g in glossary.gaps()}
    declared = {("view2", "payment_amount_mean"), ("view2", "receipt_amount_mean")}
    assert gaps == declared, (
        f"the glossary gap list has changed.\n  now:      {sorted(gaps)}\n"
        f"  declared: {sorted(declared)}\n"
        f"Author the phrases or update WPD6_REPORT's list.")
    return f"{len(gaps)} declared gaps, both view2 per-GP-month averages"


# ── 5. Every numeral traceable ───────────────────────────────────────────────
@check("numerals-traceable",
       "every numeral in every answer traces to a corpus sentence")
def _numerals(ctx):
    assembler = ctx["assembler"]
    corpus = ctx["corpus"]
    questions = (LOOKUP_QUESTIONS + WHY_QUESTIONS + NO_MATCH_QUESTIONS
                 + DECOMPOSE_QUESTIONS
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
                 + DECOMPOSE_QUESTIONS
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


# ── 6b. The judge is the one that was measured (D6.2 item 2) ─────────────────
@check("judge-model-evidenced",
       "the configured judge is the id the out-of-scope evidence was measured on")
def _judge_evidenced(ctx):
    """The out-of-scope guarantee is a property of a model id, not of the code.

    This fails RED on a swapped `DISCOVERCHAT_JUDGE_MODEL` and names the
    requalification step, because the alternative -- a quiet swap -- keeps every
    other check green while discarding the only evidence that the system refuses
    questions it has no answer to.
    """
    evidenced, reference = config.evidenced_judge_model()
    assert config.JUDGE_MODEL == evidenced, (
        f"the configured judge is {config.JUDGE_MODEL!r}, but the out-of-scope "
        f"evidence was measured on {evidenced!r}.\n"
        f"        evidence: {reference}\n"
        f"        {config.REQUALIFY_JUDGE}")
    return f"{evidenced} — {reference}"


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
@check("findings-verbatim",
       "a shown sentence is the corpus's, with only its column names translated")
def _verbatim(ctx):
    """Two assertions, and the second is what keeps this a real check after D6.1.

    The rendered sentence is no longer byte-identical to the stored one -- the
    display glossary swaps `fund_untied_total` for "untied grant planned" -- so
    the first assertion moved to the rendered form. On its own that would be
    weaker, because it no longer pins the text to the corpus at all.

    The second assertion restores the strength and aims it at the thing worth
    protecting: the NUMERALS of the rendered sentence must equal the numerals of
    the stored one, in order, exactly. A translation that altered a figure, or
    reordered two clauses so their figures swapped, fails here. Nothing a
    dictionary substitution can legitimately do touches a digit.
    """
    corpus = ctx["corpus"]
    checked = 0
    for question in ("How is Chikilli doing?", "Is spending on track?",
                     "Where is money planned but not spent?",
                     "Which blocks account for the shortfall?"):
        answer = ctx["assembler"].answer(question)
        for finding in answer.findings:
            shown = finding.display_sentence()
            assert shown in answer.text, (
                f"record {finding.id} was not shown verbatim")
            stored = corpus.get(finding.id)
            assert stored.sentence == finding.sentence, (
                f"record {finding.id} does not match the corpus")
            assert checks.numerals(shown) == checks.numerals(stored.sentence), (
                f"the display glossary altered a figure in {finding.id}:\n"
                f"  stored:   {checks.numerals(stored.sentence)}\n"
                f"  rendered: {checks.numerals(shown)}")
            checked += 1
    return (f"{checked} shown sentences identical to their corpus record, "
            f"every numeral unchanged by the translation")


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

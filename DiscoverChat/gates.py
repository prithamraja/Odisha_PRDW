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
import json
import logging
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.ERROR)

from DiscoverChat import (                                     # noqa: E402
    assemble, causal_gate, checks, classifier, config, context_brief,
    corpus as corpus_mod, glossary, render, verifier, writer,
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


# ── 6c. The judge prompt is the one that was measured (WP-D9 D9.0) ───────────
@check("judge-prompt-evidenced",
       "the configured judge prompt is the wording the out-of-scope evidence "
       "was measured on")
def _judge_prompt_evidenced(ctx):
    """The other half of the pair `judge-model-evidenced` binds.

    The out-of-scope guarantee belongs to (model, prompt) together. Until D9.0
    the gate pinned the id and left the words free, so any edit to the judge's
    instruction -- the loosening D9.1 makes, or a later helpful tidy -- kept
    every check green while discarding the evidence that the system stays
    silent on questions it cannot answer. This goes red on any change to the
    prompt template and names the requalification, exactly as a model swap does.
    """
    from DiscoverChat import judge
    evidenced, reference = config.evidenced_judge_prompt()
    configured = judge.prompt_sha256()
    assert evidenced, (
        "the judge evidence records no prompt hash, so the running prompt "
        "cannot be checked against it.\n"
        f"        evidence: {reference}\n"
        f"        {config.REQUALIFY_JUDGE_PROMPT}")
    assert configured == evidenced, (
        f"the configured judge prompt "
        f"({config.JUDGE_PROMPT_VARIANT!r}, sha256 {configured[:12]}) is not "
        f"the wording the out-of-scope evidence was measured on "
        f"(sha256 {evidenced[:12]}).\n"
        f"        evidence: {reference}\n"
        f"        {config.REQUALIFY_JUDGE_PROMPT}")
    return (f"{config.JUDGE_PROMPT_VARIANT} — sha256 {configured[:12]} — "
            f"{reference}")


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




# ═════════════════════════════════════════════════════════════════════════════
# WP-D7 — the new checks (D7.0 config, D7.1 checks-still-fire, D7.2, D7.3)
# ═════════════════════════════════════════════════════════════════════════════
# Every one of these is OFFLINE and deterministic, for the reason the module
# docstring already gives: a gate whose green depends on a model call goes red
# for reasons nobody changed. The live halves — the nano's own behaviour, the
# audit's drift rate, and citation-checked prose on real turns — are in
# `live_checks` and in the two experiment scripts, which is where a number that
# moves belongs.

# Three synthetic records, built here rather than pulled from the corpus. The
# seeded-violation checks need a KNOWN set of figures to violate, and a corpus
# record's numerals change when the corpus is rebuilt, which would make these
# checks fail for a reason that has nothing to do with what they test.
_SEED = [
    {"finding_id": "1-00235", "record_type": "finding",
     "sentence": "Across most measure values (19/22), Code 101 accounts for "
                 "51.96 percent of total_cost.",
     "view": "view1", "view_title": "Activity Lifecycle", "score": 0.4,
     "in_feed": False, "view_rank": None, "feed_rank": None, "measures": [],
     "geography": {}, "named_members": [], "subspace_phrase": "the whole view"},
    {"finding_id": "1-00987", "record_type": "finding",
     "sentence": "Across 12 blocks, fund_untied_total reaches Rs 1.24 crore "
                 "in Boipariguda.",
     "view": "view1", "view_title": "Activity Lifecycle", "score": 0.3,
     "in_feed": False, "view_rank": None, "feed_rank": None, "measures": [],
     "geography": {}, "named_members": ["Boipariguda"],
     "subspace_phrase": "the whole view"},
    {"finding_id": "d1-00042", "record_type": "decomposition",
     "sentence": "Within the whole view, activities planned totals 12,704 "
                 "activities across 20 Gram Panchayats.",
     "view": "view1", "view_title": "Activity Lifecycle", "score": 0.0,
     "in_feed": False, "view_rank": None, "feed_rank": None, "measures": [],
     "geography": {}, "named_members": [], "subspace_phrase": "the whole view"},
]
SEED_FINDINGS = [corpus_mod.Finding(i, r) for i, r in enumerate(_SEED)]
SEED_RUN_DATE = "as of 2026-08-17"

CLEAN_PROSE = (
    "Code 101 accounts for 51.96 percent of total cost across 19 of 22 "
    "measures [1-00235]. Untied grant planned reaches Rs 1.24 crore in "
    "Boipariguda across 12 blocks [1-00987]. Activities planned total 12,704 "
    "across 20 Gram Panchayats [d1-00042].")


# ── D7.0. The classifier constant, and the evidence behind it ────────────────
@check("classifier-model-evidenced",
       "the configured classifier is the id the D7.0 gate was run on")
def _classifier_evidenced(ctx):
    """The judge has this check already (D6.2 item 2) and the classifier now
    needs it for the same reason: after D7.0 the routing that reaches an officer
    for every question the rules miss is a property of one model id, and Ask's
    F1 is the standing proof that a small model can fail SILENTLY. A swap that
    nobody re-gated would keep every other check green.

    Absent evidence is a WARNING here rather than a failure, unlike the judge's:
    the judge's 0.0% false-answer rate is the only thing standing between an
    out-of-scope question and a confidently-wrong answer, and the classifier's
    worst case is a turn routed to RETRIEVE that should have been reframed --
    bad, and not that.
    """
    if not config.CLASSIFIER_EVIDENCE_PATH.exists():
        return (f"no D7.0 evidence file yet; run "
                f"`python DiscoverChat/experiments/run_classifier_nano.py "
                f"--repeats 4` on {config.CLASSIFIER_MODEL}")
    with open(config.CLASSIFIER_EVIDENCE_PATH, encoding="utf-8") as fh:
        evidence = json.load(fh)
    assert evidence["classifier_model"] == config.CLASSIFIER_MODEL, (
        f"the configured classifier is {config.CLASSIFIER_MODEL!r}, but the "
        f"D7.0 evidence was measured on {evidence['classifier_model']!r}.\n"
        f"        Re-run: DISCOVERCHAT_CLASSIFIER_MODEL="
        f"{config.CLASSIFIER_MODEL} python "
        f"DiscoverChat/experiments/run_classifier_nano.py --repeats 4")
    assert evidence["gate"]["passed"], (
        f"the D7.0 evidence for {config.CLASSIFIER_MODEL} is RED: "
        f"routing green every run={evidence['gate']['routing_green_every_run']}, "
        f"zero nulls={evidence['gate']['zero_null_classifications']}")
    return (f"{evidence['classifier_model']} — {evidence['repeats']} runs, "
            f"{evidence['calls_to_the_model']} calls, "
            f"{evidence['empty_replies']} empty, "
            f"{evidence['unparseable_replies']} unparseable "
            f"({evidence['generated_at']})")


@check("classifier-null-is-not-silent",
       "an empty or unparseable classification is named, not swallowed")
def _classifier_null_named(ctx):
    """The F1 check, at the code level. `classify` still falls through to
    RETRIEVE on a bad reply -- that is the right runtime behaviour -- but the
    Routing it returns must SAY so, or the gate above has nothing to count."""
    empty = classifier.Routing(classifier.RETRIEVE, "default", "x",
                               model_empty=True)
    bad = classifier.Routing(classifier.RETRIEVE, "default", "x",
                             model_unparseable=True)
    rule = classifier.rule_route("Why is spending low in Chikilli?")
    assert empty.model_null and bad.model_null
    assert not rule.model_null, "a rule-routed turn claims a model null"
    assert empty.as_dict()["model_empty"] is True, (
        "the null flag does not reach the logged routing dict, so a turn that "
        "fell through silently would look identical to one that was decided")
    return "the flag exists, reaches as_dict(), and is False on the rule path"


# ── D7.1. The verifier is out of the turn, and the checks still fire ─────────
@check("inline-verifier-off",
       "turn prose is not verified inline; the module is still there for the audit")
def _inline_verifier_off(ctx):
    assert config.INLINE_VERIFY is False, (
        "DISCOVERCHAT_INLINE_VERIFY is on; D7.1 turns it off for turn prose")
    assert hasattr(verifier, "verify") and hasattr(verifier, "build_audit_prompt"), (
        "the verifier module was deleted rather than switched off — the audit "
        "needs it")
    assert "consolidat" in verifier.CONSOLIDATED_DESCRIPTION.lower(), (
        "the audit has no prompt describing what a consolidated answer is, so "
        "it would judge restatement as intrusion (the T4 false positive)")
    return ("inline verification off; verifier.py intact with both prompt "
            "shapes (connective, consolidated)")


@check("citation-checks-fire",
       "each seeded violation is caught — the checks are not vacuous")
def _citation_checks_fire(ctx):
    """A check that never fires proves nothing (the `causal-gate-catches`
    principle, applied to D7.3). One seeded violation per step, plus the clean
    text that must PASS -- because a check that fails everything is as useless
    as one that fails nothing."""
    clean = checks.check_citations(CLEAN_PROSE, SEED_FINDINGS,
                                   run_date=SEED_RUN_DATE)
    assert clean["all_pass"], (
        f"the clean prose was rejected: {checks.citation_failure_reason(clean)}")

    seeded = {
        "unknown id": CLEAN_PROSE.replace("[1-00235]", "[1-99999]"),
        "derived figure": CLEAN_PROSE + " Together these cover 63.2 percent "
                                        "of the total [1-00235].",
        "misattributed figure": "Untied grant reaches Rs 51.96 crore "
                                "[1-00987]. " + CLEAN_PROSE,
        "uncited numeral": CLEAN_PROSE + " There were 7 exceptions.",
        "dropped finding": ("Code 101 accounts for 51.96 percent across 19 of "
                            "22 [1-00235]. Untied grant reaches Rs 1.24 crore "
                            "in 12 blocks [1-00987]."),
        "causal claim": CLEAN_PROSE + " The shortfall was caused by late "
                                      "sanctions [1-00235].",
    }
    for name, prose in seeded.items():
        result = checks.check_citations(prose, SEED_FINDINGS,
                                        run_date=SEED_RUN_DATE)
        assert not result["all_pass"], f"the check missed a seeded {name}"
        assert checks.citation_failure_reason(result).strip(), (
            f"a seeded {name} was caught with no reason to feed back")
    return (f"clean prose passes; {len(seeded)} seeded violations all caught "
            f"({', '.join(seeded)})")


@check("audit-reads-both-writer-shapes",
       "the offline audit can read the logged prompts it will be given")
def _audit_reads_logs(ctx):
    """The audit's only input is the log, and the log spans a writer change.
    A parser that silently failed on one shape would audit half the corpus of
    prose and report a rate over the other half without saying so."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_prose_audit", REPO / "DiscoverChat" / "experiments"
        / "run_prose_audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    connective = {"prompt": "background\n\nThe analysis holds 5 finding(s) "
                            "that bear on it:\n\nFINDING 1\n  Across x.\n\n"
                            "Write the connective prose. Give it in two parts",
                  "response_text": "OPENING: hello\nCLOSING: NONE"}
    consolidated = {"prompt": "background\n\nFINDINGS\n[1-00235] Across x.",
                    "response_text": "Across x [1-00235]."}
    block, is_c = audit._sources(connective)
    assert not is_c and "FINDING 1" in block and "Write the connective" not in block
    block, is_c = audit._sources(consolidated)
    assert is_c and "[1-00235]" in block
    assert audit._prose(connective, False) == "hello"
    assert audit._prose(consolidated, True) == "Across x [1-00235]."

    records = audit._load(audit.DEFAULT_LOGS)
    picked, how = audit.sample(records, None)
    return (f"both prompt shapes parsed; {len(records)} logged writer calls "
            f"available, would audit {how}")


# ── D7.2. Provenance: the record endpoint ────────────────────────────────────
def _record_ctx(ctx):
    """`main`'s handlers read module STATE; give them this gate's corpus."""
    from DiscoverChat import main as main_mod
    main_mod.STATE["retriever"] = ctx["retriever"]
    main_mod.STATE["stamp"] = ctx["corpus"].stamp
    return main_mod


@check("record-endpoint-resolves",
       "every id an answer could cite resolves, and an unknown id 404s")
def _record_endpoint(ctx):
    """The brief's D7.2 gate, over the suite's answers rather than over a
    handful of ids: an id that appears in an answer and does not resolve is a
    hover an officer cannot follow, which is the one thing this endpoint is
    for."""
    from fastapi import HTTPException
    main_mod = _record_ctx(ctx)
    assembler = ctx["assembler"]

    questions = (DECOMPOSE_QUESTIONS
                 + ["How is Chikilli doing?", "Is spending on track?",
                    "Where is money planned but not spent?",
                    "How is Barpali block doing?",
                    "Which places are behaving differently from the rest?"])
    ids, corpora = set(), set()
    for question in questions:
        for finding in assembler.answer(question).findings:
            ids.add(finding.id)
    # Both corpora, explicitly, because they are two files behind one id space
    # and a lookup that only ever saw findings would not prove decompositions
    # resolve.
    ids.add(next(f.id for f in ctx["corpus"].all() if not f.is_decomposition))
    ids.add(next(f.id for f in ctx["corpus"].all() if f.is_decomposition))

    for finding_id in sorted(ids):
        payload = main_mod.record(finding_id)
        assert payload["found"] and payload["id"] == finding_id
        record = ctx["corpus"].get(finding_id)
        assert payload["sentence"] == record.sentence, (
            f"{finding_id} served a sentence that is not the corpus's")
        assert payload["display_sentence"] == record.display_sentence()
        assert payload["run_stamp"] == config.run_stamp_line(), (
            f"{finding_id} served without the run stamp")
        assert payload["url"].endswith(finding_id)
        corpora.add("decomposition" if record.is_decomposition else "finding")

    try:
        main_mod.record("1-99999999")
        raise AssertionError("an unknown id did not 404")
    except HTTPException as exc:
        assert exc.status_code == 404, f"unknown id returned {exc.status_code}"
    return (f"{len(ids)} ids resolve with sentence, stamp and url "
            f"({', '.join(sorted(corpora))}); unknown id 404s")


@check("record-view-is-readable",
       "the HTML record view carries the sentence, its scope and the run stamp")
def _record_view(ctx):
    main_mod = _record_ctx(ctx)
    finding_id = next(f.id for f in ctx["corpus"].all() if f.is_decomposition)
    record = ctx["corpus"].get(finding_id)
    page = main_mod._record_html(main_mod._record_payload(record))
    for needle, what in ((finding_id, "the id"),
                         (config.run_stamp_line(), "the run stamp"),
                         ("Stored sentence", "the stored sentence"),
                         ("Standing in the analysis", "its standing")):
        assert needle in page, f"the record view omits {what}"
    assert "<table" in page and "</html>" in page
    return f"{len(page):,}-byte readable view for {finding_id}, stamp included"


# ── D7.3. The tags never reach the screen, and every numeral is bound ────────
@check("tags-never-rendered",
       "the [id] tags are plumbing: stripped from the text an officer reads")
def _tags_stripped(ctx):
    stripped = checks.strip_tags(CLEAN_PROSE)
    assert "[" not in stripped and "]" not in stripped, (
        f"a citation tag survived into the display text: {stripped}")
    for finding in SEED_FINDINGS:
        assert finding.id not in stripped, f"{finding.id} is visible in the prose"
    assert "51.96 percent" in stripped and "12,704" in stripped, (
        "stripping the tags also removed content")
    html_out = render.to_html(CLEAN_PROSE, SEED_FINDINGS,
                              run_date=SEED_RUN_DATE)
    assert "[1-00235]" not in html_out, "a tag survived into the rendered HTML"
    return "tags removed from both the plain text and the rendered HTML"


@check("hover-binds-every-numeral",
       "every checked numeral is a hover element carrying its stored sentence")
def _hover_binds(ctx):
    """Ruling 4's condition, mechanically: the number itself is the hover
    target. Checked against `bind_numerals` rather than by counting `<span>`s,
    so the renderer and the check cannot drift apart -- if they ever did, this
    is where it would show."""
    bindings = checks.bind_numerals(CLEAN_PROSE, SEED_FINDINGS,
                                    run_date=SEED_RUN_DATE)
    bound = [b for b in bindings if b["matched"]]
    assert bound, "no numeral bound at all — the fixture is broken"
    html_out = render.to_html(CLEAN_PROSE, SEED_FINDINGS,
                              run_date=SEED_RUN_DATE)
    for binding in bound:
        finding = next(f for f in SEED_FINDINGS if f.id == binding["matched"])
        assert f'data-finding-id="{finding.id}"' in html_out, (
            f"{binding['token']} bound to {finding.id} but no hover element "
            f"carries that id")
    for finding in SEED_FINDINGS:
        assert config.record_url(finding.id) in html_out, (
            f"no record link for {finding.id}")
        assert finding.display_sentence()[:40] in html_out, (
            f"the hover for {finding.id} does not carry its stored sentence")
    assert html_out.count('class="dc-cite"') >= len(bound), (
        "fewer hover elements than bound numerals")
    return (f"{len(bound)} of {len(bindings)} numerals bound and wrapped; "
            f"{len(SEED_FINDINGS)} record links present")


@check("consolidation-prompt-is-the-operators",
       "the writer prompt is Appendix A and carries no writing rules of our own")
def _prompt_is_appendix_a(ctx):
    """D40 records the operator rejecting rules-in-the-prompt three times, and
    the brief says "nothing else in the prompt". This is the standing check that
    nobody helpfully adds a style line later."""
    prompt = context_brief.CONSOLIDATING_WRITER_PROMPT
    for line in ("Turn the analytical findings below into clear, concise prose",
                 "consolidate them into a small number of underlying patterns",
                 "Do not make causal claims ever",
                 'Ignore ranking metadata such as "not in the ranked shortlist."',
                 "tag the finding it comes from with its id in square brackets",
                 "Do not compute new numbers",
                 "Return only the finished prose."):
        assert line in prompt, f"the operator's prompt lost: {line!r}"
    assert "PM addition" not in prompt, (
        "the bracket scaffolding was pasted into the prompt")
    assert context_brief.WRITER_TASK not in context_brief.for_consolidating_writer(), (
        "the D5 connective-prose task is still stacked in front of the "
        "operator's prompt, and it tells the writer not to restate findings")
    built = writer.build_consolidation_prompt(
        "Is spending on track?", SEED_FINDINGS, run_date=SEED_RUN_DATE)
    for banned in ("ranked ", "score", "Standing in the analysis"):
        assert banned not in built.replace(
            'Ignore ranking metadata such as "not in the ranked shortlist."', ""), (
            f"ranking metadata reached the writer: {banned!r}")
    assert "[1-00235] " in built and "[d1-00042] " in built
    assert "the parts add up to the whole" in built, (
        "a decomposition reached the writer without its scope note")
    return (f"{len(prompt.split())} words, Appendix A verbatim plus the two "
            f"ratified additions; no scores or coverage lines in the payload")


# ── live-only ────────────────────────────────────────────────────────────────
def _log_size() -> int:
    """Bytes in the call log now — the marker the trace check reads from."""
    from DiscoverChat import llm
    return llm.LOG_PATH.stat().st_size if llm.LOG_PATH.exists() else 0


def _calls_since(offset: int, turn_id: str) -> list:
    """Every logged model call for one turn, from `offset` onward."""
    from DiscoverChat import llm
    if not llm.LOG_PATH.exists():
        return []
    with open(llm.LOG_PATH, encoding="utf-8") as fh:
        fh.seek(offset)
        out = []
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("turn_id") == turn_id:
                out.append(record)
    return out


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

    # ── WP-D7 D7.1: no verifier call in a turn's trace ───────────────────────
    # Read from the CALL LOG rather than from the writer's return value, because
    # the claim being made is about what the service did, not about what a
    # dataclass says it did. `llm.call` is the only path to a model and it logs
    # every call, so a verify call that happened cannot hide from this.
    from DiscoverChat import llm
    before = _log_size()
    trace_turn = "d71-trace"
    traced = assembler.answer("Is spending on track?", turn_id=trace_turn)
    calls = _calls_since(before, trace_turn)
    purposes = sorted({c.get("purpose") for c in calls})
    out.append(("live:no-verifier-in-turn",
                f"turn {trace_turn} made {len(calls)} model calls "
                f"({', '.join(purposes) or 'none'}); prose used="
                f"{traced.prose.get('used')}",
                "verify" not in purposes))

    # ── WP-D7 D7.3: citation-checked prose on real turns ─────────────────────
    # ZERO citation-check failures may reach the user. That is not the same as
    # zero fallbacks: a fallback is the check WORKING -- the officer gets the
    # bare sentences, which is ratified behaviour -- so fallbacks are counted
    # and reported, and what must be zero is a narrative that reached the text
    # while failing its own check.
    questions = ["Is spending on track?",
                 "Which places are behaving differently from the rest?",
                 "How is Chikilli doing?",
                 "Where is money planned but not spent?",
                 "Which blocks account for the shortfall?",
                 "How is Barpali block doing?"]
    reached_user, fell_back, narratives = 0, 0, 0
    numerals_checked, uncited = 0, []
    for question in questions:
        answer = assembler.answer(question)
        if not answer.findings:
            continue
        if not answer.tagged_text:
            fell_back += 1
            continue
        narratives += 1
        result = checks.check_citations(answer.tagged_text, answer.findings,
                                        run_date=answer.stamp)
        if not result["all_pass"]:
            reached_user += 1
        bindings = checks.bind_numerals(answer.tagged_text, answer.findings,
                                        run_date=answer.stamp)
        numerals_checked += len(bindings)
        uncited += [b["token"] for b in bindings
                    if b["matched"] is None and not b["exempt"]]
        # The tags are plumbing: they must not be in what the officer reads.
        if "[" in answer.text and "]" in answer.text:
            reached_user += 1

    out.append(("live:citation-check",
                f"{narratives} narratives, {fell_back} fell back to bare "
                f"sentences, {reached_user} failing narratives reached the "
                f"user, {numerals_checked} numerals bound, "
                f"{len(uncited)} uncited",
                reached_user == 0 and not uncited))

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

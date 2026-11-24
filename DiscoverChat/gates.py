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
    corpus as corpus_mod, glossary, layout, render, verifier, writer,
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


GIT_FILE_LIMIT_BYTES = 100_000_000      # GitHub refuses a file over 100 MB


@check("vector-parts-under-limit",
       "every vector file is a stamped part under 100 MB; no unsplit .npy is left")
def _vector_parts(ctx):
    """WP-D11b T1 (D61 ruling 1). The deployed service reads its corpus from
    git, and git's host refuses any file over 100 MB -- which the decomposition
    matrix became in WP-D11 (136.8 MB). The split fixes that; this keeps it
    fixed. Both stamps are read from disk directly, whether or not the sidecar is
    switched on for serving, because a file that cannot be pushed is a problem
    either way."""
    stamps = {"findings": config.load_stamp()}
    if config.DECOMPOSE_STAMP_PATH.exists():
        with open(config.DECOMPOSE_STAMP_PATH, encoding="utf-8") as fh:
            stamps["decompositions"] = json.load(fh)
    named, lines = set(), []
    for what, stamp in stamps.items():
        manifest = stamp.get("vector_storage") or {}
        parts = manifest.get("parts") or []
        assert parts, f"the {what} stamp names no vector parts"
        for part in parts:
            path = config.METAINSIGHTS / part["file"]
            assert path.exists(), f"{part['file']} is named by the {what} stamp and missing"
            size = path.stat().st_size
            assert size < GIT_FILE_LIMIT_BYTES, (
                f"{part['file']} is {size:,} bytes, over git's 100 MB file limit")
            named.add(part["file"])
        lines.append(f"{what}: {len(parts)} part(s), largest "
                     f"{max(p['bytes'] for p in parts) / 1e6:.1f} MB")
    every = sorted(p.name for p in config.METAINSIGHTS.glob("*.npy"))
    big = [n for n in every
           if (config.METAINSIGHTS / n).stat().st_size >= GIT_FILE_LIMIT_BYTES]
    assert not big, f".npy files over the 100 MB limit: {big}"
    for unsplit in (config.VECTORS_PATH, config.DECOMPOSE_VECTORS_PATH):
        assert not unsplit.exists(), (
            f"{unsplit.name}, the unsplit spelling, is back on disk -- nothing "
            f"writes it any more, so it is stale, and at decompose size it is "
            f"over the limit")
    stray = [n for n in every if n not in named]
    assert not stray, f"vector files no stamp names (stale parts?): {stray}"
    return "; ".join(lines) + f"; {len(every)} .npy file(s), all stamped, all under 100 MB"


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
        # WP-D15: a place turn shows sheet lines, each a stored sentence of
        # the profile sheet store; their numerals trace to that record the
        # way a finding's trace to the corpus. The capped line names the
        # sheet turn's insight cap.
        shown = set((answer.place or {}).get("lines_used", []))
        for fact in answer.place_facts:
            if fact.id in shown:
                allowed |= set(checks.numerals(fact.sentence))
        if answer.place:
            allowed |= {str(config.PROFILE_INSIGHT_CAP)}
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
    flagged = []
    for question in questions:
        answer = assembler.answer(question)
        result = causal_gate.check(answer.text)
        if not result["pass"]:
            flagged.append((question,
                            [p["surface"] for p in result["problems"]]))
    # WP-D13 Fix 6 (D68): this gates under DISCOVERCHAT_CAUSAL_CHECK=block;
    # under log or off it reports the count and does not fail.
    if config.CAUSAL_CHECK == "block":
        assert not flagged, (f"answer to {flagged[0][0]!r} asserts a cause: "
                             f"{flagged[0][1]}" if flagged else "")
        return f"{len(questions)} answers scanned, none causal"
    return (f"{len(questions)} answers scanned, {len(flagged)} with "
            f"cause-and-effect words (mode {config.CAUSAL_CHECK}: reported, "
            f"not gated)"
            + ("" if not flagged else
               ": " + "; ".join(f"{q!r} {w}" for q, w in flagged)))


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
    # The causal step is pinned to block (WP-D13 Fix 6): the gate proves the
    # step fires, whatever the configured default -- as for direction below.
    clean = checks.check_citations(CLEAN_PROSE, SEED_FINDINGS,
                                   run_date=SEED_RUN_DATE, causal_mode="block")
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
    # Step 4 is pinned to block too (WP-D15c): the seeded "dropped finding"
    # proves the old rule still fires when it is switched back on.
    for name, prose in seeded.items():
        result = checks.check_citations(prose, SEED_FINDINGS,
                                        run_date=SEED_RUN_DATE,
                                        causal_mode="block",
                                        every_insight_mode="block")
        assert not result["all_pass"], f"the check missed a seeded {name}"
        assert checks.citation_failure_reason(result).strip(), (
            f"a seeded {name} was caught with no reason to feed back")

    # WP-D13 Fix 1: a reversed direction, on a real signed record (d1-00248,
    # Rs 51.96 crore BELOW plan). Pinned to block mode: the gate proves the
    # step fires, whatever the configured default.
    signed = ctx["corpus"].get("d1-00248")
    right = checks.check_citations(
        "Recorded spending is Rs 51.96 crore below plan [d1-00248].",
        [signed], direction_mode="block")
    assert right["all_pass"], (
        f"the true direction was rejected: "
        f"{checks.citation_failure_reason(right)}")
    reversed_ = checks.check_citations(
        "Recorded spending is Rs 51.96 crore above plan [d1-00248].",
        [signed], direction_mode="block")
    assert not reversed_["all_pass"] and not reversed_["5_direction"]["pass"], (
        "the check missed a reversed direction")
    assert "below plan" in checks.citation_failure_reason(reversed_)
    seeded["reversed direction"] = None
    return (f"clean prose passes; {len(seeded)} seeded violations all caught "
            f"({', '.join(seeded)})")


@check("signed-direction-in-words",
       "every negative signed figure an officer or the writer sees says 'below plan', never a minus")
def _signed_direction(ctx):
    """WP-D13 Fix 1 T1, swept over every signed decomposition. The display
    sentence keeps every digit, carries no "Rs -", adds one "below" phrase per
    minus-sign figure, and drops the sign-convention sentence exactly when
    every figure is negative. Every other record's display sentence is the
    column translation alone, as before."""
    from phase5f_decompose import _SIGNED_DIRECTION
    import re
    signed = minus_total = added_total = other = 0
    problems = []
    for record in ctx["corpus"].all():
        shown = record.display_sentence()
        before = glossary.render(record.sentence, record.view)
        if not (record.is_decomposition
                and record.data.get("measure") in _SIGNED_DIRECTION):
            other += 1
            if shown != before:
                problems.append((record.id, "unsigned record changed"))
            continue
        signed += 1
        measure, signs = record.data["measure"], record.data["signs"]
        below = glossary.signed_below(measure)
        note = glossary.signed_note(measure)
        if note not in before:
            problems.append((record.id, "builder's sign sentence not found"))
            continue
        minus = len(re.findall(r"Rs -\d", record.sentence))
        dropped = note.count(below) if signs == "all_negative" else 0
        added = shown.count(below) - (before.count(below) - dropped)
        minus_total += minus
        added_total += added
        if ("Rs -" in shown or added != minus
                or checks.numerals(shown) != checks.numerals(record.sentence)
                or (note in shown) == (signs == "all_negative")):
            problems.append((record.id, signs))
    assert not problems, f"{len(problems)} records wrong: {problems[:5]}"
    return (f"{signed:,} signed records: {minus_total:,} minus-sign figures, "
            f"{added_total:,} 'below' phrases added, digits unchanged; "
            f"{other:,} other records unchanged")


check("layout-formatter-parity", "every figure a report card, chart or warning shows is a stored figure through the stored formatter (WP-D12)")(lambda ctx: layout.parity_check(ctx["corpus"]))


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
                 # The operator's own sentence, 2026-09-11 (D61 ruling 2). It
                 # replaced "Do not make causal claims ever" and its banned-word
                 # list; the gate pins the operator's text, so it pins this.
                 "It is very important that you do not make causal claims - "
                 "none of our data can be used to determine causality.",
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
    # Ratified addition 3 (D78, ruling R18): the place-facts paragraph. It is
    # NOT part of the standing prompt; it is added on a place turn only, and
    # `place-prompt-ratified` pins its words and its position.
    assert context_brief.PLACE_FACTS_PARAGRAPH == R18_PARAGRAPH, (
        "the R18 paragraph (D78) is not the operator's text")
    assert R18_PARAGRAPH not in prompt, (
        "the R18 paragraph was pasted into the standing prompt; it belongs "
        "only to a turn that hands place facts")
    return (f"{len(prompt.split())} words, Appendix A verbatim plus the two "
            f"ratified additions; the R18 place-facts paragraph (D78) is "
            f"added on place turns only; no scores or coverage lines in the "
            f"payload")


# ── WP-D14: the place profile sheets (spec §9) ───────────────────────────────
# The checks that need no view parquet. Checks 1 and 6 read the views and run
# in `python Insights/src/phase5g_profile_sheets.py --check` only. The store is
# read through the reader, bound to the findings corpus's candidate set.
def _profile(ctx):
    if "profile" not in ctx:
        import phase5g_profile_sheets as p5g
        from DiscoverChat import profile_store
        ctx["profile"] = (p5g, profile_store.default_store())
    return ctx["profile"]


@check("profile-sheets-stamp", "the profile sheet store is the one built beside this corpus: same candidate set and view parquets, every file verified (WP-D14)")
def _profile_stamp(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_stamp(store, config.load_stamp(), config.decompose_stamp())


@check("profile-sheets-add-up", "every profile sheet sum equals the sum of its member places' (spec §9 check 2)")
def _profile_add_up(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_parts_add_up(store)


@check("profile-sheets-shares", "every profile sheet share is re-derived from its own parts, never averaged (spec §9 check 3)")
def _profile_shares(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_shares(store)


@check("profile-sheets-insights", "every profile sheet figure a breakdown also states equals it, at every level (spec §9 check 4)")
def _profile_insights(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_insights(
        store, [f.data for f in ctx["corpus"].all() if f.is_decomposition])


@check("profile-sheets-formatter-parity", "every numeral in a profile sheet sentence is a stored figure through the stored formatter (spec §9 check 5)")
def _profile_sentences(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_sentences(store)


@check("profile-sheets-places", "the profile sheet name table agrees with every sheet, and find() returns every sheet's code (WP-D14b)")
def _profile_places(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_places(store)


@check("profile-sheets-reference","the spec §13 figures and the Appendix A sentences are reproduced exactly (spec §9 check 7)")
def _profile_reference(ctx):
    p5g, store = _profile(ctx)
    return p5g.check_reference(store)


# ── WP-D15: the place profile sheets in the chat (D78) ───────────────────────
# The operator's paragraph, ruling R18, as approved on 2026-11-24 (D78). Held
# HERE as a literal, so an edit to context_brief.py alone turns the gate red.
R18_PARAGRAPH = ("Some answers also come with PLACE FACTS: standard figures "
                 "about the place the officer asked about, each with an id "
                 "starting p-. Start from the place facts that answer the "
                 "question, then bring in the findings. You do not have to use "
                 "every place fact. Tag them the same way as findings.")

# The brief's T1 table: text -> (answered [(level, code)], mode, alternatives
# [(level, code)], note expected).
PLACE_TABLE = [
    ("What should I know about Kalimela?", [("block", "3843")], "full",
     [("gp", "119936")], True),
    # WP-D15c (R27): the officer's own words named the level -- no note; the
    # alternative is kept for the page's switch.
    ("What should I know about Kalimela GP?", [("gp", "119936")], "full",
     [("block", "3843")], False),
    ("How is Kalimela Gram Panchayat doing", [("gp", "119936")], "full",
     [("block", "3843")], False),
    ("the panchayat of Kalimela", [("gp", "119936")], "full",
     [("block", "3843")], False),
    ("How is Kalimela block doing", [("block", "3843")], "full",
     [("gp", "119936")], False),
    ("Compare Kalimela GP and Bheden", [("gp", "119936"), ("block", "3678")],
     "main", [("block", "3843"), ("gp", "116438")], True),
    ("Kalyansinghpur", [("block", "3914")], "full", [("gp", "121162")], True),
    ("How is Chikilli doing?", [("gp", "117835")], "full", [], False),
    ("How is Barpali block doing?", [("block", "3676")], "full", [], False),
    ("How is Khordha district doing overall?", [("district", "321")], "full",
     [], False),
    ("How is Itipur doing in Bhubaneswar block", [("gp", "119605")], "full",
     [], False),
    ("Compare Kalimela and Bheden", [("block", "3843"), ("block", "3678")],
     "main", [("gp", "119936"), ("gp", "116438")], True),
    ("Compare Kalimela, Bheden, Laxmipur and Boipariguda", [], "", [], False),
    ("Which blocks stand out on expenditure?", [], "", [], False),
]


def _place_store(ctx):
    if "place_store" not in ctx:
        from DiscoverChat import place
        store, why = place.open_store()
        assert store is not None, f"the profile sheet store is refused: {why}"
        ctx["place_store"] = store
    return ctx["place_store"]


def _resolve(ctx, text):
    from DiscoverChat import place
    geo = ctx["retriever"].extractor.geography(text)
    return place.resolve(text, geo["mentions"], _place_store(ctx),
                         max_places=config.PROFILE_MAX_PLACES)


@check("place-resolution",
       "a question's place names become the brief's places, levels, alternatives and note (WP-D15 T1)")
def _place_resolution(ctx):
    store = _place_store(ctx)
    for text, answered, mode, alternatives, has_note in PLACE_TABLE:
        plan = _resolve(ctx, text)
        got = [(p["level"], p["code"]) for p in plan.places]
        assert got == answered, f"{text!r}: answered {got}, expected {answered}"
        assert plan.mode == mode, f"{text!r}: mode {plan.mode!r}, expected {mode!r}"
        alts = [(a["level"], a["code"]) for a in plan.alternatives]
        assert alts == alternatives, f"{text!r}: alternatives {alts}"
        assert bool(plan.note) == has_note, f"{text!r}: note {plan.note!r}"
        # Rule 5: the quoted words resolve, by the same rules, to the
        # alternative.
        for alt in plan.alternatives:
            again = _resolve(ctx, alt["ask"])
            assert [(p["level"], p["code"]) for p in again.places] == [
                (alt["level"], alt["code"])], (
                f"{text!r}: the note's {alt['ask']!r} does not resolve to "
                f"the alternative")
    first = _resolve(ctx, PLACE_TABLE[0][0])
    assert first.note == ('This answer is about Kalimela block. For the Gram '
                          'Panchayat, ask about "Kalimela GP".'), first.note
    mixed = _resolve(ctx, "Compare Kalimela GP and Bheden")
    assert mixed.note == ('This answer is about Bheden block. For the Gram '
                          'Panchayat, ask about "Bheden GP".'), mixed.note
    full = len(store.sentences("block", "3843"))
    return (f"{len(PLACE_TABLE)} rows of the T1 table reproduced; every "
            f"note's quoted words resolve to its alternative; Kalimela block "
            f"hands {full} lines")


def _place_fixture(ctx, level="block", code="3843"):
    from DiscoverChat import place
    store = _place_store(ctx)
    info = store.place(level, code)
    plan = place.Plan(places=[{k: info[k] for k in ("level", "code", "name",
                                                       "label")}], mode="full")
    groups = place.groups_for(plan, store)
    return {f.row: f for f in place.all_facts(groups) if f.row[:1] in "AEFG"}


@check("place-facts-optional",
       "a place fact is never required: an answer that cites none passes step 4; a mined insight is, under DISCOVERCHAT_EVERY_INSIGHT_CHECK=block (WP-D15 T3, WP-D15c)")
def _place_facts_optional(ctx):
    rows = _place_fixture(ctx)
    facts = list(rows.values())
    prose_no_fact = CLEAN_PROSE
    result = checks.check_citations(prose_no_fact, SEED_FINDINGS,
                                    run_date=SEED_RUN_DATE, place_facts=facts,
                                    causal_mode="block")
    assert result["4_all_findings_cited"]["pass"] and result["all_pass"], (
        f"an answer citing no place fact was refused: "
        f"{checks.citation_failure_reason(result)}")
    with_fact = ("Kalimela block has 852 planned activities "
                 f"[{rows['A1'].id}]. " + CLEAN_PROSE)
    result = checks.check_citations(with_fact, SEED_FINDINGS,
                                    run_date=SEED_RUN_DATE, place_facts=facts,
                                    causal_mode="block")
    assert result["all_pass"], checks.citation_failure_reason(result)
    dropped = ("Kalimela block has 852 planned activities "
               f"[{rows['A1'].id}]. Code 101 accounts for 51.96 percent of "
               "total cost across 19 of 22 measures [1-00235].")
    # Pinned to block (WP-D15c): under the default `log` a left-out insight
    # is recorded and does not fail; this asserts the old rule still holds.
    result = checks.check_citations(dropped, SEED_FINDINGS,
                                    run_date=SEED_RUN_DATE, place_facts=facts,
                                    every_insight_mode="block")
    assert not result["all_pass"] and not result["4_all_findings_cited"]["pass"], (
        "a dropped mined insight passed step 4 on a place turn")
    unhanded = "Kalimela has 852 planned activities [p-block-9999-A1]."
    result = checks.check_citations(unhanded, [], place_facts=facts)
    assert not result["1_ids_known"]["pass"], "an id not handed passed step 1"
    return (f"{len(facts)} Kalimela block lines handed: an answer citing none "
            f"passes; citing one passes; a dropped insight fails step 4 under "
            f"block; an id not handed fails step 1")


@check("place-standing-check",
       "a rank or quarter in a sentence citing a place fact must be the one the cited line states (WP-D15 T3 step 6)")
def _place_standing(ctx):
    """WP-D15c T4: the five correct sentences step 6 refused in the WP-D15
    trial (report §4.5) pass; the four kinds of real mistake are still caught.
    Pinned to block so the gate proves the step fires, whatever the default."""
    from DiscoverChat import place
    store = _place_store(ctx)

    def lines(*places):
        facts = []
        for level, code in places:
            info = store.place(level, code)
            plan = place.Plan(places=[{k: info[k] for k in ("level", "code",
                                                              "name", "label")}],
                              mode="full")
            facts += place.all_facts(place.groups_for(plan, store))
        return facts

    trial = [   # (sentence, places handed) -- report §4.5, the tags as written
        ("Barpali has the most planned activities in the sample: 1,447 across "
         "its 2 Gram Panchayats, the highest of 16 blocks "
         "[p-block-3676-A1][p-block-3676-I4].", [("block", "3676")]),
        ("Its 808 planned activities rank 7th highest, but its planned cost of "
         "Rs 3.36 crore is the 7th lowest; 447 activities (55.3%) have no cost "
         "attached [p-block-3838-A1][p-block-3838-A2][p-block-3838-A3].",
         [("block", "3838")]),
        ("The main status issue is that 167 works are marked ongoing, the 4th "
         "highest count among 16 blocks, while no works are marked completed "
         "[p-block-3838-E1][p-block-3838-E2].", [("block", "3838")]),
        ("Khordha has 1,316 planned activities; its activity count is the 4th "
         "highest among 9 districts. [p-district-321-A1]",
         [("district", "321")]),
        ("Their planned costs are also among the highest in the comparison: Rs "
         "7.65 crore in Kalimela and Rs 7.22 crore in Bheden "
         "[p-block-3843-A3][p-block-3678-A3].",
         [("block", "3843"), ("block", "3678")]),
    ]
    caught = [  # Kalimela block: A1 "5th most", A6 "4th lowest"
        "Spending is 23.0% of the planned cost, the 4th highest of 16 blocks [p-block-3843-A6].",
        "Kalimela block has 852 planned activities, the most of 16 blocks [p-block-3843-A1].",
        "Kalimela block has 852 planned activities, the 3rd most of 16 blocks [p-block-3843-A1].",
        "Spending is 23.0% of the planned cost, in the lowest quarter of blocks [p-block-3843-A6].",
    ]
    kalimela = lines(("block", "3843"))
    cases = ([(s, lines(*p), True) for s, p in trial]
             + [(s, kalimela, False) for s in caught]
             + [(f"Kalimela block has 852 planned activities, the 5th highest "
                 f"of 16 blocks [p-block-3843-A1].", kalimela, True),
                ("Spending is the 4th highest of all blocks [1-00235].",
                 kalimela, True)])
    for prose, facts, should_pass in cases:
        result = checks.check_citations(
            prose, SEED_FINDINGS[:1] if "1-00235" in prose else [],
            place_facts=facts, standing_mode="block")
        step = result.get("6_standing")
        assert step is not None, "step 6 did not run on a place turn"
        assert step["pass"] == should_pass, (
            f"step 6 gave {step['pass']} for {prose!r}: {step['failures']}")
        if not should_pass:
            assert "these ranks" in checks.citation_failure_reason(result).lower()
    return (f"the 5 correct sentences refused in the WP-D15 trial pass; the "
            f"other end, a first place not held, a rank not given and a "
            f"quarter not stated are caught; highest = most; a sentence citing "
            f"no place fact is not checked ({len(cases)} cases; mode "
            f"{config.STANDING_CHECK})")


@check("place-prompt-ratified",
       "the R18 paragraph is the operator's text, character for character (D78), and only a place turn carries it")
def _place_prompt(ctx):
    from DiscoverChat import place
    assert context_brief.PLACE_FACTS_PARAGRAPH == R18_PARAGRAPH, (
        "context_brief.PLACE_FACTS_PARAGRAPH is not the D78 text")
    rows = _place_fixture(ctx)
    group = place.Group(place={"level": "block", "code": "3843",
                               "name": "Kalimela", "label": "Kalimela block"},
                        facts=list(rows.values()))
    with_place = writer.build_consolidation_prompt(
        "What should I know about Kalimela?", SEED_FINDINGS,
        run_date=SEED_RUN_DATE, place_groups=[group])
    plain = writer.build_consolidation_prompt(
        "What should I know about Kalimela?", SEED_FINDINGS,
        run_date=SEED_RUN_DATE)
    assert (R18_PARAGRAPH + "\n\nReturn only the finished prose.") in with_place, (
        "the paragraph is not directly before the prompt's last line")
    assert with_place.count(R18_PARAGRAPH) == 1
    assert R18_PARAGRAPH not in plain, "a turn with no place facts carries R18"
    assert plain == writer._build_plain(
        "What should I know about Kalimela?", SEED_FINDINGS,
        run_date=SEED_RUN_DATE)
    assert with_place.index("PLACE FACTS — Kalimela block") < with_place.index("FINDINGS")
    return ("R18 identical to the D78 text; directly before \"Return only the "
            "finished prose.\" on a place turn; absent on any other")


SWITCH_OFF_BASELINE = (REPO / "handoffs" / "WPD15_trial"
                       / "offline_baseline_answers.json.gz")
SWITCH_OFF_VECTORS = REPO / "handoffs" / "WPD15_trial" / "offline_baseline_vectors.npy"


@check("place-switch-off-identical",
       "with DISCOVERCHAT_PROFILE_SHEETS=0 every offline answer is byte-identical to the service before WP-D15; with it on, every answer that names no place is too (pass mark 3)")
def _place_switch_off(ctx):
    """Replays the baseline's own query vectors, so the comparison sees code
    changes only -- never the embedding endpoint's drift between calls."""
    import copy
    import gzip
    import numpy as np
    assert SWITCH_OFF_BASELINE.exists(), f"no baseline at {SWITCH_OFF_BASELINE}"
    with gzip.open(SWITCH_OFF_BASELINE, "rt", encoding="utf-8") as fh:
        base = json.load(fh)
    here = config.load_stamp()["candidate_set_id"]
    assert base["candidate_set_id"] == here, (
        f"the baseline was made on candidate set {base['candidate_set_id']}, "
        f"this corpus is {here}: it no longer describes this service. "
        f"Re-make it on the service before WP-D15, as WPD15_REPORT §5 says")
    vectors = np.load(SWITCH_OFF_VECTORS)
    pinned = copy.copy(ctx["retriever"])
    pinned._query_cache = {t: vectors[i]
                           for i, t in enumerate(base["vector_texts"])}

    def answers(sheets_on: bool) -> dict:
        saved = config.PROFILE_SHEETS
        config.PROFILE_SHEETS = sheets_on
        try:
            assembler = assemble.Assembler(pinned, allow_model=False)
            out = {}
            for question in base["questions"]:
                a = assembler.answer(question)
                d = json.loads(json.dumps(a.as_dict(), ensure_ascii=False,
                                          sort_keys=True))
                d["citations_full"] = json.loads(json.dumps(a.citations))
                out[question] = (d, bool(a.place))
            return out
        finally:
            config.PROFILE_SHEETS = saved

    off = answers(False)
    differ = [q for q in base["questions"] if off[q][0] != base["answers"][q]]
    assert not differ, (f"{len(differ)} answers differ with the switch off, "
                        f"first {differ[0]!r}")
    on = answers(True)

    def without_place_log(d):
        # A turn that named places but got no sheet (more than three) logs
        # why under retrieval["place"]; nothing else may differ.
        d = dict(d)
        d["retrieval"] = {k: v for k, v in d["retrieval"].items()
                          if k != "place"}
        return d

    changed_no_place = [q for q in base["questions"]
                        if not on[q][1]
                        and without_place_log(on[q][0])
                        != without_place_log(base["answers"][q])]
    assert not changed_no_place, (
        f"a no-place answer changed with the switch on: {changed_no_place[0]!r}")
    with_place = sum(1 for q in base["questions"] if on[q][1])
    return (f"switch off: {len(base['questions'])} of "
            f"{len(base['questions'])} answers byte-identical to the "
            f"pre-WP-D15 service; switch on: {with_place} answers carry place "
            f"facts, the other {len(base['questions']) - with_place} unchanged")


# ── WP-D15c: the every-insight rule is a mode (R25, D82) ─────────────────────
@check("every-insight-check-mode",
       "under log a left-out insight is recorded, does not fail the answer and is not in the retry reason; under block it fails as before (WP-D15c, R25)")
def _every_insight_mode(ctx):
    left_out = ("Code 101 accounts for 51.96 percent of total cost across 19 of "
                "22 measures [1-00235]. Untied grant planned reaches Rs 1.24 "
                "crore in Boipariguda across 12 blocks [1-00987].")
    logged = checks.check_citations(left_out, SEED_FINDINGS,
                                    run_date=SEED_RUN_DATE, causal_mode="block",
                                    every_insight_mode="log")
    step = logged["4_all_findings_cited"]
    assert step["dropped"] == ["d1-00042"] and step["pass"] is False, step
    assert step["counts"] is False and logged["all_pass"], (
        "under log a left-out insight failed the answer")
    assert "never cited" not in checks.citation_failure_reason(logged)
    both = checks.check_citations(left_out + " There were 7 more.",
                                  SEED_FINDINGS, run_date=SEED_RUN_DATE,
                                  every_insight_mode="log")
    reason = checks.citation_failure_reason(both)
    assert not both["all_pass"] and "7" in reason and "never cited" not in reason, (
        "a draft retried for another reason was told to add the left-out insight")
    blocked = checks.check_citations(left_out, SEED_FINDINGS,
                                     run_date=SEED_RUN_DATE, causal_mode="block",
                                     every_insight_mode="block")
    assert not blocked["all_pass"] and "never cited" in checks.citation_failure_reason(blocked)
    assert set(blocked["4_all_findings_cited"]) == {"pass", "dropped", "of"}, (
        "block mode no longer returns the old step's keys")
    nothing = checks.check_citations("The records do not cover onion prices.",
                                     SEED_FINDINGS, every_insight_mode="log")
    assert nothing["all_pass"], "an answer citing no insight failed under log (no floor)"
    return (f"log: left-out d1-00042 recorded, answer passes, retry reason "
            f"silent on it; block: fails as before with its old keys; no floor "
            f"(configured mode {config.EVERY_INSIGHT_CHECK})")


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
        # WP-D13 Fix 6 (D68): the causal scan gates under block only; under
        # log or off it is reported (scanned here directly under off, where
        # check_prose leaves the key out).
        causal_pass = (result["e_causal"]["pass"] if "e_causal" in result
                       else causal_gate.check(answer.text)["pass"])
        ok = ((causal_pass or config.CAUSAL_CHECK != "block")
              and not judged.get("hallucinated_ids")
              and len(answer.findings) <= config.ANSWER_CAP)
        out.append((f"live:{question[:26]}",
                    f"judge kept {len(answer.findings)} of "
                    f"{judged.get('pool', '?')} pooled "
                    f"[{judged.get('source')}] | prose used="
                    f"{answer.prose.get('used')} | causal_pass="
                    f"{causal_pass} (mode {config.CAUSAL_CHECK}) | invented "
                    f"ids={len(judged.get('hallucinated_ids', []))}",
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) T4 -- the AI verifier.

MODEL. A DIFFERENT model from the writer. The writer is `gpt-5.6-sol`, pinned by
D17 through discover_config. The verifier is `gpt-5.5` -- a different model
generation, same vendor. The id was checked against the LIVE model list before
this run (D17 discipline), which returned both `gpt-5.5` and `gpt-5.5-2026-04-23`.
Same vendor is a DISCLOSED LIMITATION, permitted by the brief: Insights/.env
serves one vendor's completion key, so a cross-vendor verifier was not available
without a new credential. It also keeps the comparison with round 1 honest --
round 1's verifier was the same model, so the change measured here is the
wording, not the judge.

WHAT IT SEES. The packet, the instantiated context, and the rendering. Never the
writing task's output format, never the code checks, never the other findings.

THE TWO-PART QUESTION. Round 1 ran the single, stricter reading -- "does the
writing claim anything the sources do not support" -- and 7 of its 8 failures
were one repeated false positive: it flagged the "what to check at the next
review" sentence, the very sentence the context ASKS the writer to produce, as an
unsupported claim, because a source never *states* a recommendation. The brief's
revised T4 splits the question, and that split is implemented here:

  FACTUAL CLAIMS      must each be supported by the packet or the context.
                      Mapped on pass; quoted on fail.
  SUGGESTED ACTIONS   judged for consistency only. They must not assert new
  and review questions facts and must not contradict the sources, but they need
                      no source that recommends them.

A vague verdict is a fail-to-verify, never a pass (brief T4), and a pass without
a complete claim mapping is a fail-to-verify too -- that is the rubber-stamp
guard.
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prompts import render_packet
from context import CONTEXT

VERIFIER_MODEL = "gpt-5.5"

TEMPLATE = """You are checking one short piece of writing against the source material it was written from. You are not judging its style, its tone, or the order it makes its points in. You are judging one thing only: whether it is supported.

SOURCE MATERIAL 1 -- the finding, its variable definitions and its reference figures:
{packet}

SOURCE MATERIAL 2 -- the context the writer was given:
{context}

THE WRITING TO CHECK:
LEAD: {lead}
DETAIL: {detail}

Sort what the writing says into two kinds, and judge each kind by its own standard.

FACTUAL CLAIMS -- anything the writing states about the data: a number, a place, a category, a comparison, a scope, a direction, a cause, or a degree of certainty. Every factual claim must be supported by SOURCE MATERIAL 1 or 2. Judge these strictly. A figure attached to the wrong group, a scope quietly widened or narrowed, a limitation the sources state that the writing drops or weakens, a cause asserted where the sources show only a pattern -- each of those is a failure even when every digit is correct.

SUGGESTED ACTIONS AND REVIEW QUESTIONS -- what the writing proposes an official should check, ask, reconcile or look into. The writer was asked to end with what is worth checking or asking at the next review, so a suggestion is expected and is NOT an unsupported claim merely because no source recommends it. Do not fail the writing for proposing something. Judge a suggestion on consistency only: it fails if it asserts a new fact ("payments are missing", "statuses are not being updated") or if it contradicts the sources. A suggestion that asserts a fact is making that factual claim, and you check it like any other.

Then answer:
1. Does the writing make any factual claim the source material does not support?
2. Does any suggested action assert a new fact or contradict the sources?

Reply with JSON only, no other text, in exactly this shape:

{{"verdict": "pass", "claim_map": [{{"claim": "<a core factual claim from the writing, quoted>", "supported_by": "<the exact packet line or context sentence that supports it>"}}]}}

or

{{"verdict": "fail", "problems": [{{"drifted_claim": "<the unsupported, misattributed or weakened claim, quoted exactly from the writing>", "missing_or_contradicted_fact": "<what the source says instead, or what is absent from it>"}}]}}

Rules for your reply:
- If you answer "pass", claim_map must list EVERY core factual claim the writing makes, each mapped to a specific source line. A pass with an empty or partial claim_map is not acceptable.
- If anything is unclear or you cannot map a factual claim, answer "fail" and say so in missing_or_contradicted_fact. Do not guess.
"""


def build_verifier_prompt(packet, lead, detail):
    return TEMPLATE.format(packet=render_packet(packet), context=CONTEXT,
                           lead=lead, detail=detail)


def parse_verdict(text):
    """Parse the verifier's JSON. Anything unparseable or vague is a
    FAIL-TO-VERIFY, never a pass (brief T4: 'Vague verdict = fail-to-verify')."""
    raw = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              "verifier returned no parseable JSON: " + raw[:200]}]}
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              "verifier JSON did not parse (%s): %s" % (e, raw[:200])}]}

    v = str(obj.get("verdict", "")).lower().strip()
    if v == "pass":
        cm = obj.get("claim_map") or []
        if not cm or not all(c.get("claim") and c.get("supported_by") for c in cm):
            # Rubber-stamp guard: a pass without a real claim mapping is not a pass.
            return {"verdict": "fail_to_verify", "claim_map": cm,
                    "problems": [{"drifted_claim": "(none quoted)",
                                  "missing_or_contradicted_fact":
                                  "verifier passed without a complete claim mapping"}]}
        return {"verdict": "pass", "claim_map": cm}
    if v == "fail":
        probs = obj.get("problems") or []
        if not probs or not all(p.get("drifted_claim") for p in probs):
            return {"verdict": "fail_to_verify", "problems": probs or
                    [{"drifted_claim": "(none quoted)",
                      "missing_or_contradicted_fact": "verifier failed without quoting a claim"}]}
        return {"verdict": "fail", "problems": probs}
    return {"verdict": "fail_to_verify",
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact":
                          "verifier gave no clear verdict: %r" % v}]}


def verifier_reason(res):
    bits = []
    for p in res.get("problems", []):
        bits.append('A reviewer flagged this claim: "%s". The source says: %s'
                    % (p.get("drifted_claim"), p.get("missing_or_contradicted_fact")))
    return " ".join(bits)

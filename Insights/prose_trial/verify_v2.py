#!/usr/bin/env python
"""WP-D4 T4 -- verifier variant 2, run as a MEASUREMENT, not a replacement.

v1 (verify.py) implements the brief's T4 literally: packet + Appendix A's
background + rendering, "does it claim anything the sources do not support".
Running it produced a systematic false-positive class: it flags the
"what to check at the next review" sentence -- which Appendix A explicitly
ASKS the writer for -- as an unsupported claim, because the background bullets
alone never "state" a recommendation.

v2 changes exactly one thing: it separates a FACTUAL claim about the data from
a SUGGESTED ACTION, and only support-checks the former. It is still failed by
an action that smuggles in a fact ("payments are missing"), and still failed by
a lost or weakened limitation. Everything else -- model, inputs, output shape,
the no-rubber-stamp rule -- is identical to v1.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prompts import APPENDIX_A, render_packet
from verify import VERIFIER_MODEL, parse_verdict, _BACKGROUND  # noqa: F401

TEMPLATE = """You are checking one short piece of writing against the source material it was written from. You are not judging its style, its tone, or the order it makes its points in. You are judging one thing only: whether it is supported.

SOURCE MATERIAL -- the finding and its reference figures:
{packet}

SOURCE MATERIAL -- background facts about how these records are known to be incomplete:
{background}

THE WRITING TO CHECK:
LEAD: {lead}
DETAIL: {detail}

The writing was asked to end with what is worth checking or asking at the next review. A suggested action is therefore expected, and a suggestion is NOT by itself an unsupported claim -- do not fail the writing merely because the sources do not "state" the recommendation. But a suggestion that asserts a fact ("payments are missing", "statuses are not being updated") IS making that factual claim, and you must check it like any other.

Answer these two questions:
1. Does the writing state anything about the data -- a number, a place, a comparison, a scope, a cause, or a degree of certainty -- that the source material does not support?
2. Does the writing lose or weaken a limitation that the source material states -- for example presenting a figure as established when the background says the underlying records are partial, or applying a sample-wide total to a subset?

Reply with JSON only, no other text, in exactly this shape:

{{"verdict": "pass", "claim_map": [{{"claim": "<a core factual claim from the writing, quoted>", "supported_by": "<the exact packet line or background bullet that supports it>"}}]}}

or

{{"verdict": "fail", "problems": [{{"drifted_claim": "<the unsupported or weakened claim, quoted exactly from the writing>", "missing_or_contradicted_fact": "<what the source says instead, or what is absent from it>"}}]}}

Rules for your reply:
- If you answer "pass", claim_map must list EVERY core factual claim the writing makes, each mapped to a specific source line. A pass with an empty or partial claim_map is not acceptable.
- If anything is unclear or you cannot map a factual claim, answer "fail" and say so in missing_or_contradicted_fact. Do not guess.
"""


def build_prompt(packet, lead, detail):
    return TEMPLATE.format(packet=render_packet(packet), background=_BACKGROUND,
                           lead=lead, detail=detail)

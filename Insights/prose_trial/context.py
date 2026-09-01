#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) -- Appendix A, instantiated.

Appendix A of the brief is a TEMPLATE with four named slots. The writer must
receive the INSTANTIATED text verbatim and never the slot names. This module
holds the template exactly as the operator authored it, the four slot values
from the PR&DW pack, and the one composition rule the instantiation needs.

Composition note (decide-and-document, T1/T2 "packet field details"):
DATA_DESCRIPTION is two sentences and opens an em-dash parenthetical, so a
literal splice into the template's first sentence produces "... percentages
describe the sample, not the state and surfaces patterns worth an official's
attention." -- ungrammatical, with the parenthetical never closed. Two
punctuation-only fixes are applied: the parenthetical is closed with an em dash
before the template's "and surfaces ...", and the slot's second sentence is
placed after the template sentence closes. No word of either the template or the
slot value is changed, added or dropped; only punctuation and a sentence boundary
move. Nothing else in Appendix A is touched.

There is NO background-facts block in this version. The v1 template carried a
nine-bullet domain-facts list; the operator's 2026-08-31 revision removed it
("The template contains no list of domain facts") and dropped Appendix B (the
caution library) outright. The writer works from the packet alone.
"""

AUDIENCE = ("government officials in Odisha's Department of Panchayati Raj & "
            "Drinking Water")

DATA_DESCRIPTION_MAIN = (
    "village-level planning and spending records — development plans, "
    "sanctions, payments, works and photo evidence from Gram Panchayats, "
    "blocks, and districts")
DATA_DESCRIPTION_TAIL = (
    "The current data is a 20-Gram-Panchayat sample; percentages describe the "
    "sample, not the state.")

READERS = "busy block-, district- and state-level officials"

ATTENTION_EXAMPLES = ("which districts to question, which records to reconcile, "
                      "which local practices to check at the next review")

CONTEXT = f"""You are writing for a decision-aid system used by {AUDIENCE}. The system automatically analyses {DATA_DESCRIPTION_MAIN} — and surfaces patterns worth an official's attention. {DATA_DESCRIPTION_TAIL}

Your readers are {READERS}, not data analysts. They read these insights to decide where to direct attention: {ATTENTION_EXAMPLES}.

Below are findings from the analysis engine, each written in the engine's internal style — accurate but full of database language — along with reference figures for each. Rewrite each finding as an insight a senior officer would find clear and actionable:

- a one-to-two-sentence lead the officer sees first. This should be interesting enough to catch a reader's attention and easy enough to understand that the officer doesn't need to read the subsequent paragraph simply to understand it. Lead with what the officer would act on — usually the size and direction of the issue — rather than with the statistical pattern.
- a short detail paragraph explaining what was found, which places are exceptions and in what way, and what is worth checking or asking at the next review.

Write naturally, in plain English. Use the reference figures where they strengthen the point; use no number that is not provided. Be direct about what the data can and cannot establish — an insight that overstates certainty could send an official after the wrong problem."""

SLOT_VALUES = {
    "AUDIENCE": AUDIENCE,
    "DATA_DESCRIPTION": DATA_DESCRIPTION_MAIN + ". " + DATA_DESCRIPTION_TAIL,
    "READERS": READERS,
    "ATTENTION_EXAMPLES": ATTENTION_EXAMPLES,
}

# -*- coding: utf-8 -*-
"""The domain context brief, per D42 ruling 8.

**Who gets it:** the connective-prose writer, the turn classifier, and the
verifier. All three, and the verifier for a measured reason — WP-D4's T4 lesson
was that a verifier without the writer's context flags what the context itself
asked for. Seven of round 1's eight failures were that one false positive.

**Who does NOT get it:** the embedder. Ruling 7 is explicit — identical text on
every vector blurs the distinctions retrieval depends on, so domain background
belongs to the generative components and nowhere else.

**Provenance.** The four slot values below are `handoffs/WPD4_prose_trial.md`
Appendix A, "This deployment's slot values (from the PR&DW pack)", transcribed
VERBATIM. Not paraphrased, not summarised, not extended with a fact of our own.
They are transcribed rather than imported because `Insights/prose_trial/` is the
frozen record of a closed trial, and WP-D4b is porting the same values into a
production module of its own; two importers of a trial directory is a coupling
neither WP wants.

**What is different here, and why that is not a paraphrase.** Appendix A's
TEMPLATE ends with a task — "Below are findings from the analysis engine ...
Rewrite each finding as an insight" — which is the feed-prose job, not this one.
DiscoverChat's writer has a narrower job: connective prose around finding
sentences it may not touch. So the BACKGROUND paragraphs are Appendix A word for
word, and the task paragraph is this product's own, stated below where the
difference is visible rather than blended in.
"""

# ── Appendix A slot values, verbatim ─────────────────────────────────────────
AUDIENCE = ("government officials in Odisha's Department of Panchayati Raj & "
            "Drinking Water")

DATA_DESCRIPTION = (
    "village-level planning and spending records — development plans, "
    "sanctions, payments, works and photo evidence from Gram Panchayats, "
    "blocks, and districts. The current data is a 20-Gram-Panchayat sample; "
    "percentages describe the sample, not the state")

READERS = "busy block-, district- and state-level officials"

ATTENTION_EXAMPLES = ("which districts to question, which records to reconcile, "
                      "which local practices to check at the next review")

# The composition note WP-D4 recorded still applies: DATA_DESCRIPTION opens an
# em-dash parenthetical and carries a second sentence, so a literal splice into
# one sentence is ungrammatical. The same two punctuation-only fixes are made —
# the parenthetical is closed before the template's "and surfaces ...", and the
# slot's second sentence follows the template sentence. No word is changed.
_DESCRIPTION_MAIN, _DESCRIPTION_TAIL = DATA_DESCRIPTION.split(". The current data is a ")
_DESCRIPTION_TAIL = "The current data is a " + _DESCRIPTION_TAIL + "."

BACKGROUND = f"""You are writing for a decision-aid system used by {AUDIENCE}. The system automatically analyses {_DESCRIPTION_MAIN} — and surfaces patterns worth an official's attention. {_DESCRIPTION_TAIL}

Your readers are {READERS}, not data analysts. They read these insights to decide where to direct attention: {ATTENTION_EXAMPLES}."""


# ── This product's task paragraph ────────────────────────────────────────────
# Deliberately not written as rules. D40 records that the operator rejected
# rules-in-the-prompt three times; the safety net is post-hoc and invisible to
# the writer (checks.py, verifier.py, causal_gate.py). The one thing stated here
# is the DIVISION OF LABOUR, which is not a style rule but the shape of the job:
# the finding sentences are fixed text this writer does not own.
WRITER_TASK = """An officer has asked a question. Below is the officer's question and the findings the analysis already holds that bear on it, each written in the engine's internal style — accurate but full of database language.

Write the connective prose that turns those findings into an answer: an opening that says what the officer asked about and what the analysis holds on it, and, where several findings belong together, the sentences that group them and say how they relate. The findings' own sentences are shown to the officer exactly as they are written; you are writing what goes around them, not a rewrite of them.

Write naturally, in plain English. Use no number that is not in the findings you were given. Be direct about what the analysis can and cannot establish — an answer that overstates certainty could send an official after the wrong problem. The analysis finds patterns and associations; it is not able to establish what causes what."""

CLASSIFIER_TASK = """An officer has sent a message to this system. Decide which of four things the system should do with it.

RETRIEVE — the officer is asking what the analysis has found about something: a place, a kind of spending, a pattern, or a general "what should I look at". This is the ordinary case.

NAVIGATE — the officer is following up on something already shown in this conversation: asking about one of the exceptions named, about the same measure somewhere else, or for more on a finding already on screen. Only choose this when there IS something earlier in the conversation to follow up on.

LOOKUP — the officer wants a specific number, list or record out of the database: how much was spent, how many activities, which works are pending, who holds a post. This system does not hold the database and must not improvise an answer; a different system answers those.

WHY — the officer is asking for a cause or an explanation: why something happened, what is driving it, what is behind it. This system finds patterns and associations and is not able to establish what causes what, so these get an honest reframe rather than an answer."""

VERIFIER_TASK = """You are checking one short piece of connective prose against the source material it was written from. You are not judging its style, its tone, or the order it makes its points in. You are judging whether it is supported."""


def for_writer() -> str:
    return BACKGROUND + "\n\n" + WRITER_TASK


def for_classifier() -> str:
    return BACKGROUND + "\n\n" + CLASSIFIER_TASK


def for_verifier() -> str:
    """The verifier sees the writer's FULL context — the T4 lesson.

    Round 1 of WP-D4 gave the verifier only the background and it flagged the
    "what to check at the next review" sentence as an unsupported claim, because
    no source states a recommendation — the very sentence the context asks for.
    Seven of eight failures were that. The verifier therefore reads exactly what
    the writer was asked to do, and judges against it.
    """
    return BACKGROUND + "\n\n" + WRITER_TASK

# -*- coding: utf-8 -*-
"""The relevance judge: an LLM decides which candidates actually answer the question.

WHY THIS EXISTS (operator proposal, 2026-09-01, measured before building).

The single-threshold design leaves 15 of 34 place questions with nothing to
show. The reason is not that the analysis holds nothing — it is that the
relevant findings sit at cosine 0.54–0.61, just under a bar set at 0.62. The bar
cannot come down on its own: at 0.60 an out-of-scope question starts getting
answered, because a flat floor cannot tell "How is Chikilli doing?" from "Who is
the Sarpanch of Chikilli?" — both name a Gram Panchayat and both get the same
structural boost.

So the floor drops to 0.50 and a judge decides. Measured before a line was
written: at 0.50, taking the top 100 after the diversity collapse, **all 34
place questions have at least one genuinely relevant finding in the pool**, and
the candidate list costs a median 8,589 tokens against the 16k cap.

WHAT THE JUDGE MAY AND MAY NOT DO
---------------------------------
It may only ever **reject**. It selects from the pool by id; it cannot promote a
finding that scored below 0.50, cannot invent an id, and cannot write a finding
sentence. Ids it returns that are not in the pool are dropped and counted. So
D42 ruling 5 still holds — there is still a floor, nothing below it is ever
reachable, and a weak match is still never stretched. What changes is that the
last step of "is this actually an answer?" is a judgment rather than a
comparison, which is the shape of the question.

**Returning nothing is a correct and expected outcome**, and the prompt says so
in as many words. A judge that feels obliged to keep something is the failure
mode that matters here: 4 of the 5 out-of-scope questions now reach it with a
non-empty pool, and it is the only thing standing between them and a
confidently-wrong answer. The floor used to do that job with a 0% failure rate.

**It gets the context brief** (D42 ruling 8), because deciding what an officer
would count as an answer needs to know who the officer is.

BUDGET. `JUDGE_MAX_COMPLETION` is large on purpose. This is a reasoning model
ruling on up to 100 items at once, and WP-D5 has already been bitten twice by
the same failure: a reasoning model spends its whole completion budget on
reasoning, returns an empty string with `finish_reason='length'`, and nothing
errors. Retry-on-empty (D43) applies here too.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import config, context_brief, llm


@dataclass
class Selection:
    kept_ids: list = field(default_factory=list)
    considered: int = 0
    attempts: int = 0
    source: str = "judge"          # "judge" | "fallback-threshold"
    reason: str = ""
    hallucinated_ids: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"kept": len(self.kept_ids), "considered": self.considered,
                "attempts": self.attempts, "source": self.source,
                "reason": self.reason,
                "hallucinated_ids": self.hallucinated_ids}


PROMPT = """{context}

An officer asked:
{question}

Below are {n} findings from the analysis, the closest matches to that question out of {corpus_size}. They are ordered by how close the match is, but closeness is not the same as usefulness — many of them will have nothing to do with what was asked.

Choose the ones an officer asking this question would count as part of the answer. Most of these will not be; choosing well means leaving most of them out.

{candidates}

How to choose:
- Keep a finding only if it genuinely bears on what was asked. A finding about a different place, a different measure or a different question is not an answer merely because it was among the closest matches.
- **Keep the smallest set that fully answers the question.** How many that is depends on the question — a narrow one may have a single answer, a broad one several — but it is a judgement, not a sweep. You are choosing what a busy officer should read, not everything that is on topic.
- **Where several findings make the same point over different slices of the data, keep the clearest one or two rather than all of them.** The engine mines the same pattern over many overlapping slices, so near-repetition is common and is not extra evidence. A list of forty is not a better answer than a list of six; it is a worse one, because the officer has to find the six.
- If the officer named a place, a finding that is about that place in its own right is more of an answer than one that lists it among twenty others following a general pattern.
- **Returning nothing is a correct answer and is often the right one.** These findings come from one analysis run that looked for particular shapes of pattern. If the question is about something the analysis simply did not look at — a person, a forecast, a record, a price, a roster — then none of these is an answer, and saying so is right. Do not keep a finding because something ought to be said.

Reply with JSON only, no other text:

{{"keep": ["<finding id>", "<finding id>", ...], "note": "<one short sentence on what you kept and why, or why you kept nothing>"}}

Use the finding ids exactly as they appear above. An empty list is a valid reply.
"""


def render_candidates(findings: list) -> str:
    lines = []
    for finding in findings:
        lines.append(f"[{finding.id}] {finding.sentence}")
        lines.append(f"    ({finding.coverage_line()})")
    return "\n".join(lines)


def build_prompt(question: str, findings: list, corpus_size: int) -> str:
    return PROMPT.format(context=context_brief.for_classifier(),
                         question=question, n=len(findings),
                         corpus_size=f"{corpus_size:,}",
                         candidates=render_candidates(findings))


def select(question: str, findings: list, *, corpus_size: int,
           turn_id=None) -> Selection:
    """Which of the pooled candidates actually answer the question."""
    result = Selection(considered=len(findings))
    if not findings:
        result.reason = "no candidate cleared the candidate floor"
        return result

    valid = {f.id for f in findings}
    prompt = build_prompt(question, findings, corpus_size)

    for attempt in (1, 2):
        try:
            record = llm.call(config.JUDGE_MODEL, prompt,
                              config.JUDGE_MAX_COMPLETION, "judge",
                              turn_id=turn_id, attempt=attempt)
        except Exception as exc:
            result.attempts = attempt
            result.source = "fallback-threshold"
            result.reason = f"judge call failed: {type(exc).__name__}"
            return result

        result.attempts = attempt
        parsed = _parse(record["response_text"])
        if parsed is None:
            # Retry only the starvation case, once (D43).
            if llm.starved(record) and attempt == 1:
                continue
            result.source = "fallback-threshold"
            result.reason = ("judge returned nothing parseable"
                             if llm.starved(record)
                             else "judge reply did not parse")
            return result

        kept, note = parsed
        # An id that is not in the pool is dropped, never resolved. The judge
        # selects; it does not get to name a finding it was not shown.
        result.hallucinated_ids = [i for i in kept if i not in valid]
        result.kept_ids = [i for i in kept if i in valid]
        result.reason = note
        return result

    result.source = "fallback-threshold"
    result.reason = "judge returned nothing twice"
    return result


def _parse(text: str):
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None
    keep = obj.get("keep")
    if not isinstance(keep, list):
        return None
    return [str(k).strip() for k in keep], str(obj.get("note", "")).strip()

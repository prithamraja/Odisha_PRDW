# -*- coding: utf-8 -*-
"""The AI verifier for connective prose — WP-D4's T4, ported.

MODEL. A DIFFERENT model from the writer (config.VERIFIER_MODEL vs the D17 pin).
Same vendor is a DISCLOSED LIMITATION carried over from the trial:
`Insights/.env` serves one completion vendor, so a cross-vendor judge is not
available without a new credential.

WHAT IT SEES. The findings it was written from, the writer's FULL context — the
T4 lesson — and the prose. Never the code checks, never the other turns.

THE TWO-PART QUESTION, unchanged from the trial's round-2 wording, because that
wording is what took first-pass renderings from 2/15 to 11/15. Round 1 ran the
single stricter reading and 7 of its 8 failures were one repeated false
positive: the verifier flagged the "what to check next" sentence — the very
sentence the context asks for — as an unsupported claim.

RETRY-ON-EMPTY (D43). A verdict that returns nothing parseable is retried ONCE
before it counts as a fail-to-verify. Round 2 lost a sound rendering to a
one-off token starvation; the model spent its whole completion budget on
reasoning and returned an empty string with no error. A vague verdict is still
a fail-to-verify, and a pass without a complete claim mapping is still not a
pass — that is the rubber-stamp guard.
"""
from __future__ import annotations

import json
import re

from . import config, context_brief, llm

TEMPLATE = """{task}

SOURCE MATERIAL 1 — the findings the writing was given, exactly as the analysis holds them:
{findings}

SOURCE MATERIAL 2 — the context the writer was given:
{context}

THE WRITING TO CHECK — {prose_description}:
{prose}

Sort what the writing says into two kinds, and judge each kind by its own standard.

FACTUAL CLAIMS — anything the writing states about the data: a number, a place, a category, a comparison, a scope, a direction, or a degree of certainty. Every factual claim must be supported by SOURCE MATERIAL 1 or 2. Judge these strictly. A figure attached to the wrong group, a scope quietly widened or narrowed, a count of findings that does not match how many were supplied, a limitation the sources state that the writing drops or weakens — each of those is a failure even when every digit is correct.

SUGGESTED ACTIONS AND REVIEW QUESTIONS — what the writing proposes an official should check, ask, reconcile or look into. The writer was asked to help an officer decide where to direct attention, so a suggestion is expected and is NOT an unsupported claim merely because no source recommends it. Do not fail the writing for proposing something. Judge a suggestion on consistency only: it fails if it asserts a new fact or contradicts the sources.

CAUSE. This analysis finds patterns and associations and cannot establish what causes what. Writing that says one thing caused, drove, explains or produced another is making a factual claim the sources cannot support, whatever words it uses to say it.

Then answer:
1. Does the writing make any factual claim the source material does not support?
2. Does any suggested action assert a new fact or contradict the sources?
3. Does the writing assert a cause?

Reply with JSON only, no other text, in exactly this shape:

{{"verdict": "pass", "claim_map": [{{"claim": "<a core factual claim from the writing, quoted>", "supported_by": "<the exact finding line or context sentence that supports it>"}}]}}

or

{{"verdict": "fail", "problems": [{{"drifted_claim": "<the unsupported, misattributed or causal claim, quoted exactly from the writing>", "missing_or_contradicted_fact": "<what the source says instead, or what is absent from it>"}}]}}

Rules for your reply:
- If you answer "pass", claim_map must list EVERY core factual claim the writing makes, each mapped to a specific source line. A pass with an empty or partial claim_map is not acceptable.
- If anything is unclear or you cannot map a factual claim, answer "fail" and say so in missing_or_contradicted_fact. Do not guess.
"""


def render_findings(findings: list) -> str:
    lines = []
    for i, finding in enumerate(findings, start=1):
        lines.append(f"FINDING {i} [{finding.id}]")
        lines.append(f"  Sentence: {finding.sentence}")
        lines.append(f"  Analysis table: {finding.view_title}")
        lines.append(f"  Records covered: {finding.data.get('subspace_phrase', '')}")
        lines.append(f"  Standing in the analysis: {finding.coverage_line()}")
        names = finding.data.get("named_members", [])
        if names:
            lines.append("  Names in this finding: " + ", ".join(map(str, names[:30])))
    return "\n".join(lines)


# WP-D7 D7.1. The one sentence in TEMPLATE that describes WHAT THE WRITING IS
# has to be true of the writing, and after D7.3 there are two kinds.
#
# The connective-prose description is false of a consolidated narrative in the
# way that matters most: it tells the verifier the finding sentences are shown
# verbatim beside the prose and are not the writer's work. A consolidated
# answer restates them and they are NOT shown. A verifier told otherwise would
# judge restatement as intrusion — the same shape of false positive as WP-D4's
# T4, where the verifier flagged the sentence its own context had asked for.
CONNECTIVE_DESCRIPTION = (
    "this is the connective prose only. The finding sentences above are shown "
    "to the officer verbatim and are not this writer's work")

CONSOLIDATED_DESCRIPTION = (
    "this is the whole answer. The writer was asked to consolidate the findings "
    "above into one narrative for an official, so it restates and merges them "
    "on purpose; the finding sentences are NOT shown to the officer separately. "
    "Restating a finding is the job and is not a fault. Square-bracketed ids "
    "such as [1-00235] are citations to the findings above and are removed "
    "before the officer sees the text; judge the sentences, not the tags")


def build_prompt(prose: str, findings: list) -> str:
    return TEMPLATE.format(task=context_brief.VERIFIER_TASK,
                           findings=render_findings(findings),
                           context=context_brief.for_verifier(),
                           prose_description=CONNECTIVE_DESCRIPTION,
                           prose=prose)


def build_audit_prompt(prose: str, source_material: str, writer_context: str,
                       *, consolidated: bool) -> str:
    """The offline audit's prompt (D7.1).

    Built from strings rather than from `Finding` objects because the audit
    reads LOGGED calls: the findings a past turn was written from are recorded
    in that turn's prompt and nowhere else, and re-retrieving them today would
    audit a different answer. `writer_context` is the writer's own logged
    prompt, in full — the T4 lesson, applied to the strongest available form of
    it, which is not a reconstruction but the exact bytes the writer read.
    """
    return TEMPLATE.format(
        task=context_brief.VERIFIER_TASK,
        findings=source_material,
        context=writer_context,
        prose_description=(CONSOLIDATED_DESCRIPTION if consolidated
                           else CONNECTIVE_DESCRIPTION),
        prose=prose)


def verify(prose: str, findings: list, *, turn_id=None) -> dict:
    """One verdict. Retries once on an unparseable/empty reply (D43)."""
    prompt = build_prompt(prose, findings)
    attempts = []
    for attempt in (1, 2):
        try:
            record = llm.call(config.VERIFIER_MODEL, prompt,
                              config.VERIFIER_MAX_COMPLETION, "verify",
                              turn_id=turn_id, attempt=attempt)
        except Exception as exc:
            return {"verdict": "fail_to_verify", "attempts": attempt,
                    "problems": [{"drifted_claim": "(none quoted)",
                                  "missing_or_contradicted_fact":
                                  f"verifier call failed: {type(exc).__name__}"}]}
        attempts.append(record)
        verdict = parse_verdict(record["response_text"])
        # Retry ONLY the starvation case. A verifier that returned a clear
        # 'fail' must not be asked again until it says something nicer.
        if not (llm.starved(record) and attempt == 1):
            verdict["attempts"] = attempt
            return verdict
    return {"verdict": "fail_to_verify", "attempts": 2,
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact":
                          "verifier returned nothing twice"}]}


def parse_verdict(text: str) -> dict:
    """Anything unparseable or vague is a FAIL-TO-VERIFY, never a pass."""
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              "verifier returned no parseable JSON: " + raw[:200]}]}
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              f"verifier JSON did not parse ({exc}): {raw[:200]}"}]}

    verdict = str(obj.get("verdict", "")).lower().strip()
    if verdict == "pass":
        claim_map = obj.get("claim_map") or []
        if not claim_map or not all(c.get("claim") and c.get("supported_by")
                                    for c in claim_map):
            return {"verdict": "fail_to_verify", "claim_map": claim_map,
                    "problems": [{"drifted_claim": "(none quoted)",
                                  "missing_or_contradicted_fact":
                                  "verifier passed without a complete claim mapping"}]}
        return {"verdict": "pass", "claim_map": claim_map}
    if verdict == "fail":
        problems = obj.get("problems") or []
        if not problems or not all(p.get("drifted_claim") for p in problems):
            return {"verdict": "fail_to_verify",
                    "problems": problems or
                    [{"drifted_claim": "(none quoted)",
                      "missing_or_contradicted_fact":
                      "verifier failed without quoting a claim"}]}
        return {"verdict": "fail", "problems": problems}
    return {"verdict": "fail_to_verify",
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact":
                          f"verifier gave no clear verdict: {verdict!r}"}]}


def failure_reason(result: dict) -> str:
    bits = []
    for problem in result.get("problems", []):
        bits.append('A reviewer flagged this: "%s". The source says: %s'
                    % (problem.get("drifted_claim"),
                       problem.get("missing_or_contradicted_fact")))
    return " ".join(bits)

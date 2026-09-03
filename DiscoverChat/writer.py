# -*- coding: utf-8 -*-
"""The connective-prose writer and its safety net (WP-D4 pattern, end to end).

The writer is FREE: it gets the context brief and the findings, and no writing
rules of any kind. D40 records that the operator rejected rules-in-the-prompt
three times; every constraint lives after the writer and is invisible to it.

The net, in order, exactly as ratified at D40 item 11 and extended by D41:

    write  ->  mechanical checks (numerals, names, db tokens, length, CAUSAL)
           ->  different-model verifier
           ->  regenerate ONCE with the reason
           ->  re-check and re-verify
           ->  fall back to the bare finding sentences

The fallback is not a failure mode; it is designed behaviour (D40 item 11,
explicitly ratified). It costs the officer nothing that matters: the finding
sentences are the deterministic text either way, and what is lost is only the
prose around them.

WHAT THE WRITER MAY NOT DO, ENFORCED BY SHAPE RATHER THAN BY INSTRUCTION:
it never sees a request to restate a finding, because the finding sentences are
rendered by `assemble.py` from the corpus and the model's output is only ever
inserted around them. There is no code path by which a model-written sentence
can replace a finding sentence.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from . import checks, config, context_brief, llm, verifier


@dataclass
class Prose:
    text: str
    fell_back: bool
    attempts: int = 0
    check_results: list = field(default_factory=list)
    verdicts: list = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict:
        return {"fell_back": self.fell_back, "attempts": self.attempts,
                "reason": self.reason,
                "verdicts": [v.get("verdict") for v in self.verdicts]}


def _render_findings_for_writer(findings: list) -> str:
    lines = []
    for i, finding in enumerate(findings, start=1):
        lines.append(f"FINDING {i}")
        lines.append(f"  {finding.sentence}")
        lines.append(f"  From: {finding.view_title}")
        lines.append(f"  Covers: {finding.data.get('subspace_phrase', '')}")
        lines.append(f"  Standing in the analysis: {finding.coverage_line()}")
        lines.append("")
    return "\n".join(lines)


def build_prompt(question: str, findings: list, reason: str = "") -> str:
    parts = [context_brief.for_writer(), ""]
    parts.append("The officer asked:")
    parts.append(question)
    parts.append("")
    parts.append(f"The analysis holds {len(findings)} finding(s) that bear on it:")
    parts.append("")
    parts.append(_render_findings_for_writer(findings))
    if reason:
        parts.append("A previous attempt at this answer was rejected. "
                     "The reason given was:")
        parts.append(reason)
        parts.append("")
    parts.append("Write the connective prose. Give it in two parts, delimited "
                 "exactly like this:")
    parts.append("")
    parts.append("OPENING: <what goes before the findings>")
    parts.append("CLOSING: <what goes after them, or the single word NONE>")
    return "\n".join(parts)


def parse(text: str) -> tuple:
    """('opening', 'closing'). A reply that gives neither is not usable."""
    opening, closing = "", ""
    current = None
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("OPENING:"):
            current = "opening"
            opening = stripped[len("OPENING:"):].strip()
        elif stripped.upper().startswith("CLOSING:"):
            current = "closing"
            closing = stripped[len("CLOSING:"):].strip()
        elif current == "opening":
            opening = (opening + " " + stripped).strip()
        elif current == "closing":
            closing = (closing + " " + stripped).strip()
    if closing.strip().upper() in ("NONE", "(NONE)", ""):
        closing = ""
    return opening, closing


def write(question: str, findings: list, *, corpus_roster: set,
          turn_id=None, fallback: str = "") -> Prose:
    """One piece of connective prose, or the honest fallback."""
    reason = ""
    result = Prose(text=fallback, fell_back=True)

    for attempt in (1, 2):
        try:
            record = llm.call(config.WRITER_MODEL,
                              build_prompt(question, findings, reason),
                              config.WRITER_MAX_COMPLETION, "write",
                              turn_id=turn_id, attempt=attempt)
        except Exception as exc:
            result.reason = f"writer call failed: {type(exc).__name__}: {exc}"
            result.attempts = attempt
            return result

        result.attempts = attempt
        opening, closing = parse(record["response_text"])
        prose = "\n\n".join(p for p in (opening, closing) if p).strip()
        if not prose:
            reason = ("The reply did not contain an OPENING line. Give the "
                      "answer in the two delimited parts.")
            result.reason = "writer returned nothing usable"
            continue

        check_result = checks.check_prose(prose, findings,
                                          corpus_roster=corpus_roster)
        result.check_results.append(check_result)
        if not check_result["all_pass"]:
            reason = checks.failure_reason(check_result)
            result.reason = reason
            continue

        # WP-D7 D7.1: OFF by default, as a config default and not a deletion.
        # `verifier.py` is untouched and the audit runs the same module over the
        # same prose; what changed is that an officer no longer waits a median
        # 28.7 s for a verdict on every turn.
        if not config.INLINE_VERIFY:
            return Prose(text=prose, fell_back=False, attempts=attempt,
                         check_results=result.check_results,
                         verdicts=result.verdicts)

        verdict = verifier.verify(prose, findings, turn_id=turn_id)
        result.verdicts.append(verdict)
        if verdict["verdict"] == "pass":
            return Prose(text=prose, fell_back=False, attempts=attempt,
                         check_results=result.check_results,
                         verdicts=result.verdicts)
        reason = verifier.failure_reason(verdict)
        result.reason = reason

    # Two attempts spent. Fall back to the deterministic text — ratified
    # behaviour, not a defect (D40 item 11).
    result.text = fallback
    result.fell_back = True
    return result


# ═════════════════════════════════════════════════════════════════════════════
# WP-D7 D7.3 — the consolidating writer
# ═════════════════════════════════════════════════════════════════════════════
# REVISES D42 ruling 6. Ruling 6 said "the LLM writes only connective prose" and
# the module docstring above still describes the shape that enforced it: finding
# sentences rendered by `assemble.py`, model output only ever inserted around
# them, no code path by which a model sentence could replace a finding sentence.
#
# That shape is gone on this path, deliberately, and it is worth being exact
# about what replaces it — because "the model may now restate findings" is a
# real loosening and the three guards are the whole of what makes it safe:
#
#   (a) CITATIONS.  Every figure and every claim carries the id of the finding
#       it came from, in square brackets, exactly as given.
#   (b) THE CITATION CHECK.  `checks.check_citations` — every cited id is in the
#       answer set, every numeral appears in the stored sentence of a finding
#       cited in the same sentence, the causal scan, and every supplied finding
#       is cited at least once. Blocking, all four.
#   (c) NO DERIVED FIGURES.  The writer may not compute percentages, sums or
#       differences. Asked in the prompt; enforced by (b), because a computed
#       number is by definition in no finding's stored sentence.
#
# And the fourth thing, which is not a guard but the reason the guards can be
# trusted by an officer rather than only by us: HOVER-TO-SOURCE (D7.2, ruling
# 4). Every number in the answer is bound to the stored sentence it came from
# and the officer can see that sentence, its scope and its run stamp without
# leaving the answer. That is why the citations have to be mechanically
# checkable rather than decorative — a citation nobody can follow is a claim.
#
# WHAT IS NOT GUARDED, STATED HERE SO IT IS NOT DISCOVERED LATER. None of the
# above sees MEANING. A limitation narrowed, a subset total generalised to the
# whole, a hedge dropped — every one of those passes all four steps with every
# digit correct. WP-D4 measured that class at 3 in 15 packets and the inline
# verifier was what caught them; D7.1 moved it offline. The sampled audit's
# drift rate is now the only measurement of this, and it is a number in the
# gate output rather than a pass/fail, for the operator to judge.


@dataclass
class Consolidated:
    """One consolidated narrative, or the honest fallback."""
    tagged: str = ""          # the prose WITH [id] tags — the API's payload
    text: str = ""            # tags stripped — what a plain client displays
    fell_back: bool = True
    attempts: int = 0
    reason: str = ""
    check_results: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"mode": "consolidated", "fell_back": self.fell_back,
                "attempts": self.attempts, "reason": self.reason,
                "citation_checks": [
                    {k: v for k, v in r.items() if k != "3_causal"}
                    for r in self.check_results]}


def _render_findings_for_consolidation(findings: list) -> str:
    """`[id] glossary-translated sentence` — and, for a decomposition, its scope
    note. Nothing else.

    NO SCORES, NO COVERAGE LINES, NO "not in the ranked shortlist". The brief's
    belt is the prompt line telling the writer to ignore ranking metadata; the
    braces are here — the metadata is never sent, so there is nothing to ignore.

    A DECOMPOSITION CARRIES ITS SCOPE NOTE and nothing more of its standing. It
    is on equal footing with a finding in every other respect, but a breakdown
    read as a mined pattern is the one confusion that changes what an officer
    concludes, so the one line that says which it is travels with it.
    """
    lines = []
    for finding in findings:
        lines.append(f"[{finding.id}] {finding.display_sentence()}")
        if finding.is_decomposition:
            lines.append(f"    ({finding.coverage_line()})")
    return "\n".join(lines)


def build_consolidation_prompt(question: str, findings: list, *,
                               run_date: str = "", reason: str = "") -> str:
    """Context brief, then the operator's prompt, then the findings.

    ORDER IS THE OPERATOR'S TEXT'S OWN. Appendix A opens "Turn the analytical
    findings below into...", so the findings go below it. The context brief
    precedes the whole thing, verbatim, per ruling 8.

    THE QUESTION IS INCLUDED, and that is a reading of the brief rather than a
    quotation of it. "Input to the writer: the judge's selected findings ...
    nothing else" is enumerating the per-finding annotations that must not
    travel — scores, coverage notes, ranking metadata — in the same breath as it
    says the context brief and the run date ARE supplied. A narrative written
    without knowing what was asked would consolidate the right findings into an
    answer to no question. Flagged in WPD7_REPORT for the operator to strike.
    """
    parts = [context_brief.for_consolidating_writer(), ""]
    parts.append(context_brief.CONSOLIDATING_WRITER_PROMPT)
    parts.append("")
    if run_date:
        parts.append(f"The analysis was run {run_date}.")
    parts.append(f"The officer asked: {question}")
    parts.append("")
    parts.append("FINDINGS")
    parts.append(_render_findings_for_consolidation(findings))
    if reason:
        parts.append("")
        parts.append("A previous attempt at this answer was rejected. The "
                     "reason given was:")
        parts.append(reason)
    return "\n".join(parts)


def _log_failure(turn_id, question: str, prose: str, reason: str,
                 results: dict) -> None:
    """The failed prose, with its reason, kept (D7.3).

    A fallback is a silent event for the officer — they get the bare sentences
    and nothing says a narrative was thrown away — so the only place the failure
    can be seen is here. The fallback RATE is reported from this file.
    """
    path = llm.LOG_DIR / "citation_failures.jsonl"
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "turn_id": turn_id,
              "question": question, "prose": prose, "reason": reason,
              "checks": {k: v for k, v in (results or {}).items()
                         if k != "3_causal"}}
    try:
        llm.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        # A log that cannot be written must never take an answer down with it.
        pass


def consolidate(question: str, findings: list, *, run_date: str = "",
                turn_id=None) -> Consolidated:
    """One consolidated narrative. Two attempts, then the bare sentences.

    NO VERIFIER ON THIS PATH, by D7.1 — and none is wired in even when
    `INLINE_VERIFY` is on, because the inline verifier's prompt is built for
    connective prose ("this is the connective prose only; the finding sentences
    above are shown to the officer verbatim and are not this writer's work"),
    which is false of a consolidated narrative. Running it here would ask a
    model to judge writing against a description of a different job — the exact
    shape of the T4 false positive WP-D4 spent a round discovering. The audit
    (`experiments/run_prose_audit.py`) runs a verifier whose prompt matches what
    the writer actually did.
    """
    result = Consolidated()
    reason = ""

    for attempt in (1, 2):
        result.attempts = attempt
        prompt = build_consolidation_prompt(question, findings,
                                            run_date=run_date, reason=reason)
        try:
            record = llm.call(config.WRITER_MODEL, prompt,
                              config.WRITER_MAX_COMPLETION, "write",
                              turn_id=turn_id, attempt=attempt)
        except Exception as exc:
            result.reason = f"writer call failed: {type(exc).__name__}: {exc}"
            return result

        prose = (record["response_text"] or "").strip()
        if not prose:
            # The starvation case (D43): budget spent on reasoning, nothing
            # returned, no error. Worth one more attempt and no more.
            reason = ""
            result.reason = ("writer returned nothing (finish_reason=%s)"
                             % record["finish_reason"])
            continue

        results = checks.check_citations(prose, findings, run_date=run_date)
        result.check_results.append(results)
        if results["all_pass"]:
            result.tagged = prose
            result.text = checks.strip_tags(prose)
            result.fell_back = False
            result.reason = ""
            return result

        reason = checks.citation_failure_reason(results)
        result.reason = reason
        _log_failure(turn_id, question, prose, reason, results)

    return result

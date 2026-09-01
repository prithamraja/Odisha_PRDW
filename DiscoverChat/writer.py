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

# -*- coding: utf-8 -*-
"""Mechanical nothing-invented checks on the connective prose (WP-D4 pattern).

The finding sentences are deterministic and are shown verbatim; this checks only
what the model WROTE AROUND them. Five checks:

  (a) every numeral in the connective prose appears in the supplied findings or
      in the context brief
  (b) every place / category name it uses belongs to one of the supplied
      findings
  (c) no raw database token
  (d) length bounds
  (e) the causal-verb ban (D41), delegated to causal_gate

NO STYLE CHECKS. D40 is explicit and the operator rejected rules-in-the-prompt
three times: whether the prose reads well is the operator's call at the gate,
not code's.

The normalisations are TIGHT, carried over from the trial: numerals are compared
as whole TOKENS against the token set of the supplied material, so '51.96' can
never match '5,196' and '893' can never match inside '6,893'.
"""
from __future__ import annotations

import re

from . import causal_gate
from .context_brief import for_writer

# Engine pattern-type enums and other raw database tokens — check (c).
ENGINE_ENUMS = [
    "EVENNESS", "TREND", "TOP_TWO", "OUTSTANDING_1", "OUTSTANDING_LAST",
    "ATTRIBUTION", "SEASONALITY", "NO_PATTERN", "TYPE_CHANGE",
    "HIGHLIGHT_CHANGE", "CHANGE_POINT", "OUTLIER", "UNIMODALITY",
    "INCREASING", "DECREASING", "EVEN", "LAST_TWO",
]

_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_PERIOD = re.compile(r"PERIOD_\d+")
_VARIES = "(varies)"

# A numeral token: a fiscal-year span, or a digit run with internal , or .
_NUM = re.compile(r"\d{4}-\d{2,4}|\d+(?:[.,]\d+)*")

# The shape bounds. WP-D4's analogue was "lead <= 2 sentences, detail <= ~200
# words" for a single rewritten finding; connective prose over as many as twelve
# findings comes in two parts and needs more room than that. WORDS are the bound
# that carries the intent -- the prose frames the findings, it does not replace
# them -- so the word count is tight and the sentence count is only a guard
# against a wall of one-clause lines. Measured first: a sentence bound of 7 was
# failing renderings whose word count was well inside 220, which is the bound
# doing something other than what it is for.
MAX_SENTENCES = 10
MAX_TOTAL_WORDS = 220


def numerals(text: str) -> list:
    return _NUM.findall(text or "")


def _num_variants(token: str) -> set:
    """Exact value, plus the one formatting-only variant: a trailing '.0'
    dropped (100.0 -> 100). Rounding is NOT allowed — 48.3 -> 48 changes the
    claim — and commas are never stripped."""
    out = {token}
    if token.endswith(".0"):
        out.add(token[:-2])
    return out


def _sentences(text: str) -> list:
    """Sentence split that does not break on the '.' inside 'Rs 1.24 crore'."""
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text or "")
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", protected) if p.strip()]
    return [p.replace("\x00", ".") for p in parts]


def supplied_text(findings: list) -> str:
    """Everything the writer was legitimately given, as one blob.

    A finding's whole record is in scope, not just its sentence: the writer is
    handed the sentence, the coverage line and the named members, so a name or a
    count drawn from any of those is supported. Nothing outside the supplied
    findings is.
    """
    parts = []
    for finding in findings:
        parts.append(finding.sentence)
        parts.append(finding.view_title)
        parts.append(finding.coverage_line())
        parts.append(finding.data.get("subspace_phrase", ""))
        parts.extend(str(n) for n in finding.data.get("named_members", []))
        parts.extend(str(m) for m in finding.data.get("measures", []))
    return "\n".join(parts)


def _context_vocabulary() -> set:
    """Names the context brief itself uses, which the writer may therefore use.

    Singular and plural both, so 'Gram Panchayats' in the brief licenses 'Gram
    Panchayat' in the prose.
    """
    text = for_writer()
    vocabulary = set()
    for match in re.finditer(r"\b[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*\b", text):
        phrase = match.group(0)
        vocabulary.add(phrase)
        if phrase.endswith("s"):
            vocabulary.add(phrase[:-1])
    return vocabulary


def name_roster(findings: list) -> set:
    """The place / category names these findings actually name."""
    roster = set()
    for finding in findings:
        for name in finding.data.get("named_members", []):
            text = str(name).strip()
            if text and not text.isdigit():
                roster.add(text)
    return roster


def check_prose(prose: str, findings: list, *, corpus_roster: set | None = None) -> dict:
    """Run every check over one piece of connective prose."""
    allowed = supplied_text(findings) + "\n" + for_writer()
    allowed_nums = set()
    for token in numerals(allowed):
        allowed_nums |= _num_variants(token)

    body = (prose or "").strip()
    results = {}

    # (a) numerals
    bad_nums = [t for t in numerals(body) if not (_num_variants(t) & allowed_nums)]
    results["a_numerals"] = {"pass": not bad_nums,
                             "unsupported": sorted(set(bad_nums)),
                             "checked": len(numerals(body))}

    # (b) names. Checked against the WHOLE corpus's vocabulary, not just this
    # answer's: the failure to catch is the writer naming a real place that is
    # not in these findings, and a roster built only from these findings could
    # not see it.
    #
    # The context brief EXEMPTS a name, on the same rule numerals already use.
    # Measured: 'Gram Panchayat' is a value of `sanction_authority`, so it sits
    # in the corpus roster as a category name -- and the check was failing prose
    # for the phrase "Gram Panchayat", which the context brief itself uses and
    # which no writer about panchayats can avoid. A check that forbids the
    # subject's own name is not catching invention, it is catching English.
    roster = corpus_roster if corpus_roster is not None else set()
    here = name_roster(findings) | _context_vocabulary()
    bad_names = []
    for name in roster:
        if name in here:
            continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", body):
            bad_names.append(name)
    results["b_names"] = {"pass": not bad_names, "not_in_findings": sorted(bad_names)}

    # (c) raw database tokens
    hits = list(_SNAKE.findall(body)) + _PERIOD.findall(body)
    if _VARIES in body.lower():
        hits.append(_VARIES)
    for enum in ENGINE_ENUMS:
        if re.search(r"\b" + enum + r"\b", body):
            hits.append(enum)
    results["c_db_tokens"] = {"pass": not hits, "tokens": sorted(set(hits))}

    # (d) shape
    n_sentences = len(_sentences(body))
    n_words = len(body.split())
    results["d_shape"] = {"pass": n_sentences <= MAX_SENTENCES
                          and n_words <= MAX_TOTAL_WORDS,
                          "sentences": n_sentences, "words": n_words}

    # (e) the causal-verb ban (D41)
    results["e_causal"] = causal_gate.check(body)

    results["all_pass"] = all(v["pass"] for k, v in results.items()
                              if k != "all_pass")
    return results


def failure_reason(results: dict) -> str:
    """Plain-English reason, fed back on the single regeneration."""
    bits = []
    if not results["a_numerals"]["pass"]:
        bits.append("It used numbers that were not in the findings supplied: "
                    + ", ".join(results["a_numerals"]["unsupported"])
                    + ". Use only figures that appear in those findings, exactly "
                      "as written.")
    if not results["b_names"]["pass"]:
        bits.append("It named places or categories that do not belong to these "
                    "findings: " + ", ".join(results["b_names"]["not_in_findings"])
                    + ". Only name the ones these findings name.")
    if not results["c_db_tokens"]["pass"]:
        bits.append("It contained raw database wording: "
                    + ", ".join(results["c_db_tokens"]["tokens"])
                    + ". Write it the way an official would say it.")
    if not results["d_shape"]["pass"]:
        bits.append("Length: %d sentences and %d words, against a bound of %d "
                    "and %d. Keep the connective prose short — it frames the "
                    "findings, it does not replace them."
                    % (results["d_shape"]["sentences"],
                       results["d_shape"]["words"],
                       MAX_SENTENCES, MAX_TOTAL_WORDS))
    if not results["e_causal"]["pass"]:
        bits.append(causal_gate.failure_reason(results["e_causal"]))
    return " ".join(bits)

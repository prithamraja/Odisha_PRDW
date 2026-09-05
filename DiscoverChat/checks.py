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

# `corpus` first: it imports `config`, which is what puts Insights/src on the
# path for `causal_gate`'s own import of `prose_gate`.
from . import corpus as corpus_mod
from . import causal_gate
from .context_brief import for_consolidating_writer, for_writer

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

    A record's whole entry is in scope, not just its sentence: the writer is
    handed the sentence, the coverage line and the named members, so a name or a
    count drawn from any of those is supported. Nothing outside the supplied
    records is.

    BOTH SENTENCES are included -- the stored one and the rendered one (D6.1).
    They carry the same digits but different words, and the officer sees the
    rendered one, so a phrase like "untied grant planned" has to be allowed
    where `fund_untied_total` was.

    A DECOMPOSITION additionally supplies its member figures (D6.1: "the
    nothing-invented check learns the decompose records as an allowed numeral
    source"). Every one is a build-time artefact of `phase5f_decompose`, exactly
    as a finding's figures are artefacts of the engine -- and a member value
    that appears in the record but not in the truncated sentence is still a
    number this system computed, not one a model invented.
    """
    parts = []
    for finding in findings:
        parts.append(finding.sentence)
        parts.append(finding.display_sentence())
        parts.append(finding.view_title)
        parts.append(finding.coverage_line())
        parts.append(finding.data.get("subspace_phrase", ""))
        parts.extend(str(n) for n in finding.data.get("named_members", []))
        parts.extend(str(m) for m in finding.data.get("measures", []))
        if finding.is_decomposition:
            data = finding.data
            parts.append(str(data.get("total_display", "")))
            parts.append(str(data.get("measure_phrase", "")))
            parts.append(str(data.get("dimension_phrase", "")))
            parts.append(str(data.get("n_members", "")))
            for member in corpus_mod.members_of(data):
                parts.append(str(member.get("member", "")))
                parts.append(str(member.get("value", "")))
                parts.append(str(member.get("share", "")))
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


# ═════════════════════════════════════════════════════════════════════════════
# WP-D7 D7.3 — the citation check
# ═════════════════════════════════════════════════════════════════════════════
# This is the check that replaces the inline verifier for NUMBERS. It does not
# replace it for MEANING, and the README says so in those words: a limitation
# quietly narrowed or a subset total generalised passes every line below.
#
# It is stricter than check (a) above in the one way that matters. Check (a)
# asks "is this numeral anywhere in the supplied material?" — which a writer
# that only introduced findings could not really get wrong, because the findings
# were printed underneath it. D7.3's writer RESTATES findings and the sentences
# are no longer printed, so the question becomes "is this numeral in the finding
# this sentence says it came from?", and a figure attached to the wrong district
# is now a failure rather than a match.
#
# THE FOUR STEPS ARE THE BRIEF'S, IN THE BRIEF'S ORDER, and all four are
# blocking. Order matters for the reported reason, not for the verdict: an
# unknown id makes every downstream answer meaningless, so it is named first.
#
# ON THE NUMERAL NORMALISER. The brief asks for Rs / crore / lakh / percent
# spellings to be normalised and for the existing normaliser to be reused. The
# existing one already is that normaliser: `_NUM` tokenises DIGITS only, so
# "Rs 1.24 crore", "1.24 crore" and "1.24" all reduce to the token 1.24, and
# "51.96%" and "51.96 percent" both to 51.96. The unit words never enter the
# comparison, so there is nothing further to normalise and nothing new to write.

# Deliberately permissive about what may sit inside the brackets. A tight
# `\[\d+-\d+\]` would silently ignore an invented `[Finding 3]` or `[view1]`
# rather than failing on it, and an ignored invention is the failure mode this
# whole check exists to prevent.
_TAG = re.compile(r"\[([^\[\]\n]{1,60})\]")


def cited_ids(prose: str) -> list:
    """Every id tagged in the prose, in order, duplicates kept."""
    return [m.strip() for m in _TAG.findall(prose or "")]


def strip_tags(text: str) -> str:
    """The prose as an officer reads it. The tags are plumbing (D7.3)."""
    out = _TAG.sub("", text or "")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([.,;:!?])", r"\1", out)
    return out.strip()


def _tagged_sentences(prose: str) -> list:
    """Sentences, with a sentence-leading tag moved back onto the previous one.

    A writer that puts its citation after the full stop — "...totals 12,704
    activities. [d1-00000] The largest share..." — is citing the sentence it
    just finished, and every reader including the model itself understands it
    that way. Splitting naively would strand the tag on the FOLLOWING sentence
    and fail a correct answer, so a run of tags at the head of a sentence is
    re-attached to the one before it. This is the only latitude in the check
    and it is one-directional: a tag never travels forwards.
    """
    out = []
    for sentence in _sentences(prose):
        match = re.match(r"^((?:\s*\[[^\[\]\n]{1,60}\])+)\s*(.*)$", sentence, re.S)
        if match and out:
            out[-1] = (out[-1] + " " + match.group(1).strip()).strip()
            rest = match.group(2).strip()
            if rest:
                out.append(rest)
        else:
            out.append(sentence)
    return out


def _stored_numerals(finding) -> set:
    """The numeral tokens of a finding's STORED sentence, with variants.

    The stored sentence, not the rendered one, exactly as the brief specifies.
    The two carry identical digits by construction — the display glossary
    substitutes whole column-name tokens only, and `findings-verbatim` in the
    gate asserts `numerals(rendered) == numerals(stored)` element by element —
    so this is the same set either way and the stored form is the auditable one.
    """
    out = set()
    for token in numerals(finding.sentence):
        out |= _num_variants(token)
    return out


def supplied_numerals(run_date: str = "") -> set:
    """Numerals the writer was handed that belong to no finding.

    Two sources, and both are things the writer was GIVEN rather than figures it
    produced:

      the context brief   "a 20-Gram-Panchayat sample" — the writer is told
                          this and an answer that repeats it is quoting its
                          own instructions. Check (a) already exempts these.
      the run date        supplied so the prose can say "as of 2026-08-17"
                          (D42's presentation rule puts the run stamp on every
                          answer). A date is not a finding and can be cited to
                          none.

    Nothing else is exempt. In particular no figure the writer computed is
    reachable here, which is what makes "no derived figures" enforceable rather
    than merely requested.
    """
    out = set()
    for token in numerals(for_consolidating_writer()) + numerals(run_date or ""):
        out |= _num_variants(token)
    return out


def bind_numerals(prose: str, findings: list, *, run_date: str = "") -> list:
    """Every numeral in the prose, bound to the finding it is cited to.

    Returns one entry per numeral occurrence:
        {"token", "sentence_index", "cited": [ids in that sentence],
         "matched": <finding id or None>, "exempt": bool}

    `matched` is the binding the RENDERER uses for hover-to-source (D7.3: "the
    number itself is the hover target"), and it is computed here rather than in
    the renderer so that the number an officer hovers is bound by the same rule
    the check passed on. Two implementations would be two rules.
    """
    exempt = supplied_numerals(run_date)
    by_id = {f.id: f for f in findings}
    stored = {f.id: _stored_numerals(f) for f in findings}

    bindings = []
    for index, sentence in enumerate(_tagged_sentences(prose)):
        tags = [t.strip() for t in _TAG.findall(sentence)]
        bare = _TAG.sub(" ", sentence)
        for token in numerals(bare):
            variants = _num_variants(token)
            matched = None
            for tag in tags:
                if tag in by_id and (variants & stored[tag]):
                    matched = tag
                    break
            bindings.append({"token": token, "sentence_index": index,
                             "cited": tags, "matched": matched,
                             "exempt": bool(variants & exempt)})
    return bindings


def check_citations(prose: str, findings: list, *, run_date: str = "") -> dict:
    """The four blocking steps of D7.3, in the brief's order."""
    body = (prose or "").strip()
    answer_ids = {f.id for f in findings}
    tagged = cited_ids(body)
    results = {}

    # 1. Every id tagged must be one of the findings this answer was built from.
    unknown = sorted({t for t in tagged if t not in answer_ids})
    results["1_ids_known"] = {"pass": not unknown, "unknown": unknown,
                              "cited": len(tagged)}

    # 2. Every numeral must appear in the stored sentence of a finding cited in
    #    the SAME sentence of the prose. An uncited numeral is a failure — the
    #    brief is explicit — and so is one cited to a finding that does not
    #    contain it, which is the misattribution case check (a) cannot see.
    bindings = bind_numerals(body, findings, run_date=run_date)
    unmatched = [b for b in bindings if b["matched"] is None and not b["exempt"]]
    results["2_numerals_cited"] = {
        "pass": not unmatched,
        "checked": len(bindings),
        "exempt": sum(1 for b in bindings if b["exempt"]),
        "unsupported": [
            {"numeral": b["token"],
             "cited": b["cited"],
             "why": ("no finding cited in this sentence" if not b["cited"]
                     else "not in the stored sentence of "
                          + ", ".join(b["cited"]))}
            for b in unmatched],
    }

    # 3. The causal scan, unchanged and blocking.
    results["3_causal"] = causal_gate.check(strip_tags(body))

    # 4. A finding the judge selected and the writer silently dropped is LOSS,
    #    not concision: the judge already picked the smallest sufficient set.
    dropped = sorted(answer_ids - set(tagged))
    results["4_all_findings_cited"] = {"pass": not dropped, "dropped": dropped,
                                       "of": len(answer_ids)}

    results["all_pass"] = all(v["pass"] for k, v in results.items()
                              if k != "all_pass")
    return results


def citation_failure_reason(results: dict) -> str:
    """Plain-English reason, fed back on the single regeneration."""
    bits = []
    if not results["1_ids_known"]["pass"]:
        bits.append("It cited finding ids that were not among the findings "
                    "supplied: " + ", ".join(results["1_ids_known"]["unknown"])
                    + ". Use only the ids given, exactly as given.")
    if not results["2_numerals_cited"]["pass"]:
        detail = "; ".join(
            f"{u['numeral']} ({u['why']})"
            for u in results["2_numerals_cited"]["unsupported"][:8])
        bits.append("Every figure must be tagged with the finding it came from, "
                    "and must appear in that finding. These do not: " + detail
                    + ". Do not compute new numbers; use the figures exactly as "
                      "the findings state them, and tag each one.")
    if not results["3_causal"]["pass"]:
        bits.append(causal_gate.failure_reason(results["3_causal"]))
    if not results["4_all_findings_cited"]["pass"]:
        bits.append("These findings were supplied but never cited: "
                    + ", ".join(results["4_all_findings_cited"]["dropped"])
                    + ". Every finding supplied belongs in the answer.")
    return " ".join(bits)

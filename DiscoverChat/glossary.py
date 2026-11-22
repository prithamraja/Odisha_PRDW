# -*- coding: utf-8 -*-
"""Render-time column translation (WP-D6 D6.1, operator-approved scope addition).

THE PROBLEM, MEASURED. Every one of the 4,239 finding sentences in the retrieval
corpus contains at least one raw engine column name -- `fund_untied_total`,
`gp_name`, `is_completed`, `output_type_label`. Not a long tail: 100%. That is
acceptable in a labelling sheet, where the reader is calibrating the engine, and
it is not acceptable in an answer to a Block Development Officer, who has never
seen the schema and should not have to.

WHAT THIS IS AND IS NOT
-----------------------
DETERMINISTIC. A dictionary and a regular expression. No model is involved at
any point in this path, so a rendered sentence is a pure function of the corpus
record and cannot drift between two runs.

TWO SUBSTITUTIONS, NEITHER TOUCHING A DIGIT. Every figure, every place name,
every clause and the order of them all survive untouched -- `findings-verbatim`
in the gate still passes because the comparison it makes is against the same
translation, and `numerals-traceable` still passes because no substitution here
can add, remove or reformat a digit.

  1. Whole-token column names become officer phrases (`render`, D6.1).
  2. On the two SIGNED measures only (`overspend_vs_plan`,
     `overspend_vs_sanction`), a negative money figure states its direction in
     words: "Rs -3.18 crore" becomes "Rs 3.18 crore below plan" (`signed_money`,
     WP-D13 Fix 1, D63). The minus sign goes, the stored "below" words from
     `phase5f_decompose._SIGNED_DIRECTION` are appended, the digits stay. And
     where every figure in a decomposition is negative, the sentence explaining
     the sign convention is dropped, because each figure now says its own
     direction (`direction_in_words`). This is a rewrite of WORDING, at display
     time only: the stored sentence, its embedding and the corpus files are
     unchanged.

ONE SOURCE FOR THE VOCABULARY (D6.1, "do not fork the dicts")
-------------------------------------------------------------
Nothing is authored here. The words come from where they were already written:

  measures    `phase5f_decompose.measure_phrase` -- the per-view table the
              decomposition builder writes its own sentences from, so a
              measure reads identically in a finding and in a decomposition
  dimensions  `phase5d_retrieval_corpus.display_name` -- the map the corpus
              builder's enriched embedding text has used since D5.0
  plurals     `phase5f_decompose.dimension_plural`, for the engine's own
              "across most <dim> values" construction

A column reachable by none of them is left RAW and reported by `gaps()`. That is
deliberate: a missing entry is PM/operator content to author, and rendering it
raw makes it visible and countable, where a guessed phrase would be neither.
"""
from __future__ import annotations

import re
from functools import lru_cache

from . import config                                   # noqa: F401  (sys.path)
from phase5d_retrieval_corpus import display_name, _DISPLAY   # noqa: E402
from phase5f_decompose import (                        # noqa: E402
    measure_phrase, dimension_plural, _MEASURE_PHRASE, _SIGNED_DIRECTION,
)
from phase2_engine import VIEW1_CONFIG, VIEW4_CONFIG   # noqa: E402
from phase4a_engine import VIEW2_CONFIG, VIEW3_CONFIG  # noqa: E402
# WP-D11b. Two display rules owned by the report layer and READ here, so the
# chat and the reports cannot say a thing two ways: the size-band unit (T3, D61
# ruling 3 -- "2,500 to 5,000 people", never the bare label the pack stores),
# and the grain an averaged twin is averaged over (T4).
from phase5b_report import BAND_DISPLAY, AVERAGED_GRAIN  # noqa: E402

# WP-D11 added view4 (GP Profile). Its sixty measures are in
# phase5f_decompose._MEASURE_PHRASE and its seven profile dimensions are in
# phase5d_retrieval_corpus._DISPLAY, so `gaps()` should report none of them --
# and if it ever does, that is the signal that a column reached a finding
# sentence with nobody having written down what to call it.
_CONFIGS = {"view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG,
            "view4": VIEW4_CONFIG}

# The engine's own vocabulary for a measure-extending finding, which is not a
# column and appears in no view config: `(varies)` is its measure field and
# `measure` is its extending dimension. Both reach the sentence, and
# `dimension_plural` renders the second as "measure values", which is the
# schema talking. Handled here, at RENDER time only: the stored corpus keeps
# the engine's wording, and the decomposition sidecar -- whose sentences were
# built from `dimension_plural` and whose embeddings are keyed on their SHA --
# is untouched by anything in this file.
_LITERALS = {
    "(varies)": display_name("(varies)"),
    "measure values": "measures",
}


def _dimensions(view: str) -> list:
    config = _CONFIGS[view]
    seen, out = set(), []
    for dim in list(config.dimensions) + list(config.temporal_dimensions):
        if dim not in seen:
            seen.add(dim)
            out.append(dim)
    return out


def _measures(view: str) -> list:
    return [m.name for m in _CONFIGS[view].measures]


def _phrase(view: str, col: str) -> str | None:
    """The officer phrase for one column, or None if no dictionary holds one.

    MEMBERSHIP in an authored dictionary is the test, not whether the resulting
    string looks different from the column name. The first draft compared the
    phrase against a mechanical de-snake-case of the column and called them
    untranslated when they matched -- which reported `block_name` -> "block" and
    `sanctioned_amount` -> "sanctioned amount" as GAPS, when both are entries
    somebody wrote on purpose and both are exactly right. A dictionary hit is a
    translation even when the dictionary agrees with the obvious.
    """
    if col in _MEASURE_PHRASE.get(view, {}):
        return measure_phrase(view, col)
    # WP-D11b T4: an averaged twin on view3 / view4 is its total's phrase at the
    # view's grain -- "average planned cost per Gram Panchayat-year". DERIVED
    # from the total's authored entry, so it is a translation somebody wrote,
    # not a guess. Scoped to the two views WP-D11b authored a grain for: view2's
    # two older twins stay the declared gaps until their grain is authored too.
    if col.endswith("_mean") and view in AVERAGED_GRAIN:
        base = col[:-len("_mean")]
        if base in _MEASURE_PHRASE.get(view, {}):
            return f"average {measure_phrase(view, base)} {AVERAGED_GRAIN[view]}"
    if col in _DISPLAY:
        return display_name(col)
    return None


# Every token the engine can emit that looks like a column, so the gate's scan
# and the renderer agree on what "a raw column name" means.
_SNAKE = re.compile(r"(?<![A-Za-z0-9_])[a-z]+(?:_[a-z0-9]+)+(?![A-Za-z0-9_])")


def render(text: str, view: str) -> str:
    """One sentence, with its column names in officer language.

    ONE PASS, and that is the whole trick. Substituting column by column feeds
    each replacement back into the next column's search: `theme` renders as
    "LSDG theme", the plural rule had already written "LSDG theme values", and
    the bare rule then found `theme` inside its own output and produced "LSDG
    LSDG theme values". `temporal_grain` failed the same way, its expansion
    "time unit (month, quarter or fiscal year)" having `month` and `quarter`
    rewritten inside it. Alternation with a replacement function reads every
    token from the ORIGINAL string exactly once, so no output can be rescanned.

    Longest alternative first, so `gp_name values` is matched as the two-token
    plural form before `gp_name` alone -- "Gram Panchayat values" is
    half-translated and reads worse than the raw name.

    ALREADY TRANSLATED TEXT IS LEFT ALONE (WP-D13 Fix 7 T1, D66). The
    decomposition builder stores its sentences in officer words already, so
    "across 7 LSDG theme values" contains the key `theme values`, and one pass
    still turned it into "LSDG LSDG theme values" (5,414 sentences), "reported
    households" into "reported reported households" (1,240), and two
    "calendar calendar". The rule: a replacement is skipped where the text at
    that place already reads as the replacement -- the match sits inside a
    copy of its own replacement, at the replacement's own offset.
    """
    if not text or view not in _CONFIGS:
        return text
    table, pattern = _substitution(view)

    def replace(match):
        found = match.group(0)
        shown = table[found]
        if _already_reads_as(match.string, match.start(), found, shown):
            return found
        return shown
    return pattern.sub(replace, text)


def _already_reads_as(text: str, start: int, found: str, shown: str) -> bool:
    """True when `found`, at `start` in `text`, is part of a copy of `shown`
    that is already there -- whole words, at the offset `found` has in
    `shown`."""
    offset = shown.find(found)
    while offset != -1:
        begin = start - offset
        end = begin + len(shown)
        if (begin >= 0 and text[begin:end] == shown
                and (begin == 0 or not text[begin - 1].isalnum())
                and (end == len(text) or not text[end].isalnum())):
            return True
        offset = shown.find(found, offset + 1)
    return False


@lru_cache(maxsize=None)
def _substitution(view: str):
    """The view's substitution table and its one-pass pattern, built once.

    Built from module constants only, so remembering it changes no output; it
    used to be rebuilt on every call (48 s for a corpus sweep, WP-D12 §7)."""
    table = {}
    for col in set(_measures(view)) | set(_dimensions(view)) | set(_DISPLAY):
        phrase = _phrase(view, col)
        if not phrase:
            continue
        table[col] = phrase
        if col in _dimensions(view) or col in _DISPLAY:
            table[f"{col} values"] = dimension_plural(col)
    for literal, phrase in _LITERALS.items():
        table[literal] = phrase
    # WP-D11b T3: size-band VALUES carry their unit on screen. In the same single
    # pass as the column names, for the reason given above; no band label
    # contains a column name or the reverse, and the digits are untouched, so
    # `findings-verbatim`'s numeral comparison still holds.
    for label, shown in BAND_DISPLAY.items():
        table[label] = shown

    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:"
        + "|".join(re.escape(k) for k in sorted(table, key=len, reverse=True))
        + r")(?![A-Za-z0-9_])")
    return table, pattern


def raw_columns(text: str, view: str) -> list:
    """Column-shaped tokens still in `text` THAT HAVE A PHRASE AVAILABLE.

    The gate's condition, exactly: a token with no entry is a known gap and is
    listed by `gaps()`, not failed here. Anything else surviving a render is a
    bug in the substitution.
    """
    return sorted({token for token in _SNAKE.findall(text or "")
                   if _phrase(view, token)})


def untranslated(text: str, view: str) -> list:
    """Column-shaped tokens in `text` with no phrase -- the known gaps, in situ."""
    return sorted({token for token in _SNAKE.findall(text or "")
                   if (token in _measures(view) or token in _dimensions(view))
                   and not _phrase(view, token)})


def gaps() -> list:
    """Every column of every view with no officer phrase. For the report.

    These are the entries the brief reserves to the PM/operator to author. The
    implementer's job is to make the list visible and to leave the column
    rendering raw until somebody writes the words.
    """
    out = []
    for view in _CONFIGS:
        for col in _measures(view) + _dimensions(view):
            if not _phrase(view, col):
                out.append({"view": view, "column": col})
    return out


# =============================================================================
# WP-D13 Fix 1 (D63) -- the direction of a signed figure, in words
# =============================================================================
# THE PROBLEM. The two signed measures store their figures with a sign: "Rs
# -51.96 crore" is spending Rs 51.96 crore BELOW plan. The stored sentence says
# so once, in a separate sentence ("This measure is signed: ..."), and leaves
# the reader -- and the writer model -- to apply that rule to every figure. The
# writer then repeats "Rs -51.96 crore" or "the signed measure", and an officer
# reads a minus sign in front of a rupee amount.
#
# THE FIX IS IN WHAT THE WRITER IS HANDED, NOT WHAT IT IS TOLD (D62 ruling 7).
# Every negative money figure carries its direction in the same words the
# builder already uses for the measure. The digits are untouched, so the
# citation check -- which compares digit tokens against the STORED sentence --
# sees exactly what it saw before.
#
# The three shapes are the only ones the corpus holds (measured 2026-11-21 over
# all 5,717 signed decompositions: 18,984 tokens, no other shape): "Rs -N",
# "Rs -N lakh", "Rs -N crore". The digit group is `_NUM`'s own shape in
# `checks`, so a figure is one token in both places.

_NEG_MONEY = re.compile(r"Rs -(\d+(?:[.,]\d+)*)( lakh| crore)?(?![A-Za-z0-9])")


def signed_below(measure: str) -> str | None:
    """'below plan' / 'below sanction' for a signed measure, else None."""
    words = _SIGNED_DIRECTION.get(measure)
    return words[1] if words else None


def signed_above(measure: str) -> str | None:
    """'above plan' / 'above sanction' for a signed measure, else None."""
    words = _SIGNED_DIRECTION.get(measure)
    return words[0] if words else None


def signed_money(text: str, measure: str) -> str:
    """Every "Rs -N[ lakh| crore]" in `text` as "Rs N[ lakh| crore] below plan".

    Works on a whole sentence or on one bare formatted value
    ("Rs -51.96 crore" -> "Rs 51.96 crore below plan"), so WP-D12's cards and
    charts produce the same words from the same function. A measure that is not
    signed returns `text` unchanged; so does text with no negative figure.
    """
    below = signed_below(measure)
    if not below or not text:
        return text
    return _NEG_MONEY.sub(
        lambda m: f"Rs {m.group(1)}{m.group(2) or ''} {below}", text)


def signed_note(measure: str) -> str | None:
    """The sign-convention sentence the decomposition builder writes for a
    signed measure, rebuilt from the same `_SIGNED_DIRECTION` words.

    The builder (`phase5f_decompose.build_sentence`) does not export the
    sentence as a constant, so its frame is restated here. The corpus sweep in
    `tests/test_direction.py` and the gate check `signed-direction-in-words`
    assert it is found, verbatim, in every one of the 5,717 signed records -- a
    change to the builder's wording fails there, loudly, rather than leaving the
    sentence silently in place.
    """
    words = _SIGNED_DIRECTION.get(measure)
    if not words:
        return None
    above, below = words
    return (f"This measure is signed: a positive figure is spending {above} "
            f"and a negative figure is spending {below}.")


def direction_in_words(text: str, measure: str, signs: str) -> str:
    """A signed decomposition's display sentence with each figure's direction
    stated in words.

    1. Every negative money figure -> "Rs N ... below plan" (`signed_money`).
    2. The sign-convention sentence is REMOVED only when `signs ==
       "all_negative"`: every figure then states its own direction and the
       rule has nothing left to explain. For `mixed` and `all_positive` it is
       KEPT unchanged -- there it is still what tells the reader how to read an
       unmarked figure ("1 of them add Rs 1.73 lakh").
    """
    if measure not in _SIGNED_DIRECTION or not text:
        return text
    out = signed_money(text, measure)
    if signs == "all_negative":
        note = signed_note(measure)
        out = out.replace(" " + note, "").replace(note + " ", "").replace(note, "")
    return out

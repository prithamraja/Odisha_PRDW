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

NOT A REWRITE. Only whole-token column names are substituted. Every figure,
every place name, every clause and the order of them all survive untouched --
`findings-verbatim` in the gate still passes because the comparison it makes is
against the same translation, and `numerals-traceable` still passes because no
substitution here can add, remove or reformat a digit.

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

from . import config                                   # noqa: F401  (sys.path)
from phase5d_retrieval_corpus import display_name, _DISPLAY   # noqa: E402
from phase5f_decompose import (                        # noqa: E402
    measure_phrase, dimension_plural, _MEASURE_PHRASE,
)
from phase2_engine import VIEW1_CONFIG                 # noqa: E402
from phase4a_engine import VIEW2_CONFIG, VIEW3_CONFIG  # noqa: E402

_CONFIGS = {"view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG}

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
    """
    if not text or view not in _CONFIGS:
        return text

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

    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:"
        + "|".join(re.escape(k) for k in sorted(table, key=len, reverse=True))
        + r")(?![A-Za-z0-9_])")
    return pattern.sub(lambda m: table[m.group(0)], text)


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

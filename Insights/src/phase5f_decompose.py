# =============================================================================
# Phase 5f: Decomposition corpus (WP-D6, stage D6.0)
# =============================================================================
# "Where does the gap sit?" -- answered by ARITHMETIC, precomputed.
#
# This builds a sidecar of deterministic decompositions: for a (measure,
# dimension, subspace) triple, how the measure's total divides among that
# dimension's values. DiscoverChat retrieves these exactly as it retrieves
# findings; it computes nothing at question time, so nothing it says can be
# arithmetically wrong at runtime (D6 ruling 1).
#
# EVERY RECORD IS AN ACCOUNTING IDENTITY, AND THE GATE PROVES IT (ruling 2).
# The total is summed over the ungrouped slice; the members are summed by
# `groupby(..., dropna=False)`. Those are two independent passes over the same
# rows, so `sum(members) == total` is a real check rather than a tautology --
# and it is the check that catches the one bug this file could plausibly have,
# which is pandas silently dropping the null-key group. Nothing here correlates,
# infers or explains: D41 (correlations only) is the project ceiling and this
# file sits well below it, at bookkeeping.
#
# Inputs (read-only):
#   Insights/views_prdw/view{1,2,3}*.parquet   the view data -- BUILD FIRST
#   phase2_engine / phase4a_engine             the view configs (measures, dims,
#                                              min_impact, excluded_pairs)
#   phase5b_report                             column_glossary, format_measure,
#                                              volume_share, utilization_companion
#   phase5d_retrieval_corpus                   the embedding pin and recipe
#   metainsights/global_feed_source_set.json   the run stamp
#
# Outputs (new files; the findings corpus, the feed and every pinned file are
# untouched):
#   metainsights/decompose_corpus.json
#   metainsights/decompose_corpus.npy
#   metainsights/decompose_corpus_stamp.json
#
# Run from the LOCAL MIRROR (D6), repo root:
#   python Insights/src/build_views.py --pack Insights/domain_pack_prdw \
#          --data-dir Data --views-dir Insights/views_prdw \
#          --reports-dir Insights/reports_prdw --strict
#   python Insights/src/phase5f_decompose.py [--no-embed] [--views view1]
#
# =============================================================================
# THE THREE THINGS THIS FILE REFUSES TO DO
# =============================================================================
# 1. IT NEVER RANKS A PLACE BY ITS SIZE AND CALLS THAT A FINDING. Calibration
#    session 1 labelled two of view1's own findings spurious for exactly this
#    -- "Activity Approved has the LOWEST overspend_vs_plan among status
#    values" is mostly a statement that most activities sit in that status. A
#    decomposition is that error's natural habitat: "Chikilli accounts for 11%
#    of the shortfall" is a headcount fact wearing a performance sentence. So
#    every decomposition of a total by a categorical dimension carries the
#    VOLUME SHARE of its top member in the same sentence, from phase5b's own
#    `volume_share` -- the rule the report calls 2b, applied here at build time
#    instead of being asked of a model.
#
# 2. IT NEVER TREATS A SIGNED MEASURE AS IF IT WERE A MAGNITUDE.
#    `overspend_vs_plan` is spent-minus-planned: members can point in both
#    directions, and a "share of the total" against a near-zero net is
#    arithmetic that produces 500% and -300% and means nothing. Mixed-sign
#    distributions get their own shape (`offsetting`), their own sentence, and
#    shares computed against the GROSS (sum of absolute values), with the
#    sentence saying which base it used.
#
# 3. IT NEVER INVENTS A CONCENTRATION. The shape of a distribution is decided by
#    the ENGINE'S OWN evaluators -- `evaluate_attribution` and
#    `evaluate_evenness`, imported and called, not re-implemented -- so
#    "concentrated" here means exactly what ATTRIBUTION means in a finding, and
#    "spread evenly" means exactly what EVENNESS means. Where they both decline,
#    the sentence says the total is spread without claiming either. D6 ruling 4:
#    "no single member accounts for it" is a first-class result.
# =============================================================================

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Insights/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase2_engine import (                                    # noqa: E402
    Subspace, ImpactCalculator, apply_subspace,
)
from phase4a_engine import (                                   # noqa: E402
    VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG,
    evaluate_evenness, evaluate_attribution,
)
from phase5b_report import (                                   # noqa: E402
    format_measure, volume_share, utilization_companion,
    _VOLUME_MEASURE, _num,
)
from phase5c_global_feed import VIEW_TITLES                    # noqa: E402
from phase5d_retrieval_corpus import (                         # noqa: E402
    display_name, glossary_snippet, long_view_title,
    Embedder, embedding_pin, pin_fingerprint, sha256_of,
    open_ask_validator, resolve_geography, GEO_DIMS,
    MAX_NAMED_IN_TEXT,
)

MI_DIR = os.path.join(BASE_DIR, "metainsights")
VIEWS_DIR = os.path.join(BASE_DIR, "views_prdw")
VIEWS = ("view1", "view2", "view3")
CONFIGS = {"view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG}

CORPUS_PATH = os.path.join(MI_DIR, "decompose_corpus.json")
VECTORS_PATH = os.path.join(MI_DIR, "decompose_corpus.npy")
STAMP_PATH = os.path.join(MI_DIR, "decompose_corpus_stamp.json")

# The label a null dimension value carries. It is a MEMBER, never a silent drop
# (D6.0: "an explicit row for null/unknown members"). `tied_untied` is null on
# the 10,603 activities with no sanction, and a decomposition of sanctioned
# money by tied/untied that quietly omitted them would be missing most of its
# rows and would still add up, because pandas would have removed them from both
# sides. That is precisely why the total is summed separately.
NULL_LABEL = "(not recorded)"

# Reconciliation tolerance. The members and the total are two float64 sums over
# the same rows in a different order, so they differ by accumulated rounding and
# nothing else. Taken relative to the GROSS, not the net: a signed measure's net
# can be near zero while its parts are crores, and a relative tolerance on the
# net would then be tighter than float64 can deliver.
RECONCILE_REL = 1e-9
RECONCILE_ABS = 1e-6


# =============================================================================
# MEASURE VOCABULARY
# =============================================================================
# Presentation only, exactly as `phase5d_retrieval_corpus._DISPLAY` is for
# dimensions: the DEFINITION behind every one of these is phase5b's
# `column_glossary` (the signed WP-D2 Appendix A), which travels on the record
# and into the embedded text unchanged. Nothing is authored about the data here
# -- these are the words the reports already use for these columns, so a
# decomposition sentence and a report sentence name the same thing the same way.
#
# `display_name`'s generic fallback is not usable for measures: it renders
# `n_activities` as "n activities" and `is_ongoing` as "is ongoing".
_MEASURE_PHRASE = {
    "view1": {
        "n_activities":           "activities planned",
        "total_cost":             "planned cost",
        "fund_tied_total":        "tied grant planned",
        "fund_untied_total":      "untied grant planned",
        "fund_abandoned_total":   "planned money on abandoned works",
        "work_proposed_cost":     "proposed cost at sanction",
        "fund_sanctioned_total":  "sanctioned amount",
        "total_expenditure":      "voucher-linked spending",
        "gen_amount":             "spending, general component",
        "sc_amount":              "spending, SC-labelled component",
        "st_amount":              "spending, ST-labelled component",
        "overspend_vs_plan":      "spending measured against plan",
        "overspend_vs_sanction":  "spending measured against sanction",
        "is_started":             "activities started",
        "is_completed":           "activities completed",
        "is_ongoing":             "activities ongoing",
        "is_abandoned":           "activities abandoned",
        "is_under_approval":      "activities under approval",
        "is_admin_approved":      "activities with administrative approval",
        "has_technical_approval": "activities with technical approval",
        "has_progress_evidence":  "activities with photo evidence",
        "evidence_uploads":       "geotagged photo uploads",
        "trainees_total":         "trainees",
        "beneficiaries_expected": "expected beneficiaries",
    },
    "view2": {
        "payment_amount":              "cashbook money paid out",
        "receipt_amount":              "cashbook money received",
        "payment_count":               "payment vouchers",
        "receipt_count":               "receipt vouchers",
        "activity_linked_expenditure": "spending linked to a planned activity",
        "sanctions_count":             "sanction records",
        "sanctioned_amount":           "sanctioned amount",
    },
    "view3": {
        "n_plans":               "GPDP plans",
        "n_activities":          "activities planned",
        "n_costed":              "costed activities",
        "n_costless":            "costless activities",
        "planned_cost":          "planned cost",
        "sanctioned_total":      "sanctioned amount",
        "expenditure_total":     "spending",
        "overspend_vs_plan":     "spending measured against plan",
        "overspend_vs_sanction": "spending measured against sanction",
        "payment_amount":        "cashbook money paid out",
        "receipt_amount":        "cashbook money received",
        "n_admin_approvals":     "administrative approval records",
        "n_tech_approvals":      "technical approval records",
        "n_completed":           "activities completed",
        "n_ongoing":             "activities ongoing",
        "n_abandoned":           "activities abandoned",
        "n_with_evidence":       "activities with photo evidence",
        "evidence_uploads":      "geotagged photo uploads",
    },
}

# Caveats that belong to the MEASURE and must travel with any figure taken from
# it. Every one is the glossary's own statement, compressed to a sentence -- the
# reports emit these deterministically (phase5b's reading notes) and a
# decomposition quoted without them is the same figure without its warning.
_MEASURE_CAVEAT = {
    "sc_amount": ("A swap between the SC and ST components is suspected and "
                  "unconfirmed; do not read one against the other."),
    "st_amount": ("A swap between the SC and ST components is suspected and "
                  "unconfirmed; do not read one against the other."),
    "overspend_vs_sanction": ("The sanctioned basis covers only the activities "
                              "with a sanction record on file, about one in six."),
    "fund_sanctioned_total": ("The sanctioned basis covers only the activities "
                              "with a sanction record on file, about one in six."),
    "work_proposed_cost": ("The sanctioned basis covers only the activities "
                           "with a sanction record on file, about one in six."),
    "is_completed": ("Only 17 completions are recorded in the whole sample, so "
                     "this splits a near-empty column."),
    "n_completed": ("Only 17 completions are recorded in the whole sample, so "
                    "this splits a near-empty column."),
    "activity_linked_expenditure": (
        "A rise here is a rise in recording completeness unless the cashbook "
        "total rises with it; the linked share went from 2.7% to 53.2% across "
        "these six years."),
}

# The two signed money measures need their direction stated once, in words, or a
# minus sign in front of a crore figure is left to the reader to interpret.
_SIGNED_DIRECTION = {
    "overspend_vs_plan":     ("above plan", "below plan"),
    "overspend_vs_sanction": ("above sanction", "below sanction"),
}


def measure_phrase(view: str, measure: str) -> str:
    return _MEASURE_PHRASE.get(view, {}).get(measure) or display_name(measure)


def measure_kind(view: str, measure: str) -> str:
    """'gap' for the signed differences, 'total' for everything else.

    D6.0 asks for the gap measures and the additive volume/amount measures. They
    decompose identically -- the arithmetic does not care about the sign -- so
    the distinction is carried as a field the chatbot can route on rather than
    as two code paths that could drift.
    """
    return "gap" if measure in _SIGNED_DIRECTION else "total"


def dimension_plural(dim: str) -> str:
    """'Gram Panchayats', 'activity status values'.

    No lookup table beyond the irregulars: everything else takes "values", which
    is the engine's own wording in `generate_nl_summary` ("across all gp_name
    values"), so the two sentence families read as one voice.
    """
    name = display_name(dim)
    irregular = {
        "Gram Panchayat": "Gram Panchayats",
        "block": "blocks",
        "district": "districts",
        "fiscal year": "fiscal years",
        "calendar month": "calendar months",
        "calendar quarter": "calendar quarters",
    }
    return irregular.get(name, f"{name} values")


def dimension_singular(dim: str) -> str:
    """The counterpart of `dimension_plural`, for "no single ___ accounts for it".

    A dimension whose display name is already a noun for a thing takes it bare;
    everything else takes "value", because "no single activity status accounts
    for it" reads as a claim about a status rather than about one of its values.
    """
    name = display_name(dim)
    bare = ("Gram Panchayat", "block", "district",
            "fiscal year", "calendar month", "calendar quarter")
    return name if name in bare else f"{name} value"


# =============================================================================
# THE DECOMPOSITION ITSELF
# =============================================================================

def scope_phrase(view: str, subspace_pairs: list) -> str:
    """The slice, in words. Depth 0 names the view; depth 1 names the filter."""
    if not subspace_pairs:
        return f"the whole of {long_view_title(view)}"
    return "; ".join(f"{display_name(dim)} {value}" for dim, value in subspace_pairs)


def decompose(sub: pd.DataFrame, column: str, dimension: str) -> tuple:
    """(members, total). Two independent sums over the same rows.

    `total` is summed over the UNGROUPED slice and `members` by
    `groupby(dropna=False)`. They are equal by arithmetic, and the gate checks it
    on every record -- which is the only way the one failure this function can
    have (a null-key group silently dropped) shows up as a failure rather than as
    a smaller, entirely plausible total.
    """
    total = float(sub[column].sum())
    grouped = sub.groupby(dimension, dropna=False)[column].sum()
    counts = sub.groupby(dimension, dropna=False)[column].size()
    null_mask = pd.isna(grouped.index)

    members = []
    for i, (key, value) in enumerate(grouped.items()):
        is_null = bool(null_mask[i])
        members.append({
            "member": NULL_LABEL if is_null else str(key),
            "is_null": is_null,
            "value": float(value),
            "rows": int(counts.iloc[i]),
        })
    # Descending by magnitude, then by label -- a stable order that does not
    # depend on the parquet's row order or on pandas' group ordering.
    members.sort(key=lambda m: (-abs(m["value"]), m["member"]))
    return members, total


def shares(members: list) -> tuple:
    """(gross, sign class). Shares are added to `members` in place.

    A share is a fraction OF THE GROSS -- the sum of the absolute member values
    -- not of the net. On an all-one-sign distribution the two are identical, so
    nothing changes for a volume or an amount. On a signed measure whose parts
    point both ways the net can be near zero, and a share of the net is how you
    get "this Gram Panchayat accounts for 480% of the gap". The gross keeps every
    share in [0, 1] and the sentence says which base it used.
    """
    gross = sum(abs(m["value"]) for m in members)
    positives = sum(1 for m in members if m["value"] > 0)
    negatives = sum(1 for m in members if m["value"] < 0)
    if positives and negatives:
        signs = "mixed"
    elif negatives:
        signs = "all_negative"
    elif positives:
        signs = "all_positive"
    else:
        signs = "all_zero"
    for m in members:
        m["share"] = round(abs(m["value"]) / gross, 6) if gross > 0 else 0.0
    return gross, signs


def shape_of(members: list, signs: str) -> dict:
    """The engine's own verdict on this distribution -- not a second opinion.

    `evaluate_attribution` and `evaluate_evenness` are imported and called on the
    magnitudes, so ATTRIBUTION here is ATTRIBUTION in a finding and EVENNESS here
    is EVENNESS in a finding, thresholds included (>50% of the total and >=2x the
    second-highest; CV < 0.15 and no member above 2/n). Where neither fires the
    answer is `spread`, which claims nothing.

    Mixed signs short-circuit BOTH. Feeding a series that sums to near zero to an
    evaluator that divides by its mean or by its sum produces a verdict about a
    denominator, not about the data.

    Both evaluators need three members; with two, neither engine pattern is
    defined, so the shape is decided by ATTRIBUTION's own two conditions applied
    directly (>50% and >=2x), and by nothing else invented for the occasion.
    """
    if signs == "mixed":
        return {"shape": "offsetting", "attribution_member": None, "evenness": False}
    if signs == "all_zero":
        return {"shape": "empty", "attribution_member": None, "evenness": False}

    magnitudes = pd.Series({m["member"]: abs(m["value"]) for m in members})
    if len(members) < 3:
        top, second = members[0], members[1]
        gross = sum(abs(m["value"]) for m in members)
        if (gross > 0 and abs(top["value"]) / gross > 0.5
                and (second["value"] == 0
                     or abs(top["value"]) / abs(second["value"]) >= 2.0)):
            return {"shape": "concentrated",
                    "attribution_member": top["member"], "evenness": False}
        return {"shape": "spread", "attribution_member": None, "evenness": False}

    attribution = evaluate_attribution(magnitudes)
    if attribution is not None:
        return {"shape": "concentrated",
                "attribution_member": str(attribution.values[0]),
                "evenness": False}
    if evaluate_evenness(magnitudes) is not None:
        return {"shape": "even", "attribution_member": None, "evenness": True}
    return {"shape": "spread", "attribution_member": None, "evenness": False}


# =============================================================================
# THE DETERMINISTIC SENTENCE
# =============================================================================
# Template-generated at build time, in the glossary's vocabulary (D6 ruling 3).
# It passes the prose gate's causal-verb ban by construction: it says what
# ACCOUNTS FOR what, which is bookkeeping, and never what caused, drove,
# explained or led to anything. `check_decompose_sentences` in the gate scans
# every stored sentence with the ban rather than trusting that claim.

def _fmt(view: str, measure: str, value: float) -> str:
    return format_measure(view, measure, value)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def build_sentence(view, measure, dimension, subspace_pairs, members, total,
                   gross, signs, shape, volume, utilization) -> str:
    phrase = measure_phrase(view, measure)
    scope = scope_phrase(view, subspace_pairs)
    plural = dimension_plural(dimension)
    n = len(members)
    top = members[0]
    verb = "nets to" if signs == "mixed" else "totals"

    lines = [f"Within {scope}, {phrase} {verb} {_fmt(view, measure, total)} "
             f"across {n} {plural}."]

    if measure in _SIGNED_DIRECTION:
        above, below = _SIGNED_DIRECTION[measure]
        lines.append(f"This measure is signed: a positive figure is spending "
                     f"{above} and a negative figure is spending {below}.")

    if shape["shape"] == "offsetting":
        pos = [m for m in members if m["value"] > 0]
        neg = [m for m in members if m["value"] < 0]
        lines.append(
            f"The parts run in both directions, so this net figure is not a "
            f"size: {len(pos)} of them add "
            f"{_fmt(view, measure, sum(m['value'] for m in pos))} and "
            f"{len(neg)} subtract "
            f"{_fmt(view, measure, -sum(m['value'] for m in neg))}. "
            f"The largest single contribution is {top['member']} at "
            f"{_fmt(view, measure, top['value'])}, which is "
            f"{_pct(top['share'])} of the {_fmt(view, measure, gross)} "
            f"moving in total.")
    elif shape["shape"] == "empty":
        lines.append("Every one of them is zero, so there is nothing to divide up.")
    elif shape["shape"] == "concentrated":
        lines.append(
            f"It is concentrated: {top['member']} accounts for "
            f"{_pct(top['share'])} of it ({_fmt(view, measure, top['value'])}).")
        lines.append(_remainder_clause(view, measure, members, 1))
    elif shape["shape"] == "even":
        lines.append(
            f"It is spread evenly across them -- no single "
            f"{dimension_singular(dimension)} accounts for it. The largest, "
            f"{top['member']}, holds {_pct(top['share'])} "
            f"({_fmt(view, measure, top['value'])}), against an even share of "
            f"{_pct(1.0 / n)}.")
    else:
        second = members[1] if n > 1 else None
        text = (f"It is spread across them without one standing out: the "
                f"largest is {top['member']} at {_pct(top['share'])} "
                f"({_fmt(view, measure, top['value'])})")
        if second is not None:
            text += (f", then {second['member']} at {_pct(second['share'])} "
                     f"({_fmt(view, measure, second['value'])})")
        lines.append(text + ".")
        lines.append(_remainder_clause(view, measure, members, 2 if second else 1))

    null_member = next((m for m in members if m["is_null"]), None)
    if null_member is not None:
        lines.append(
            f"{_num(null_member['rows'], 0)} rows carry no "
            f"{display_name(dimension)} on file; they are counted here as "
            f"{NULL_LABEL} and account for "
            f"{_fmt(view, measure, null_member['value'])}.")

    if volume:
        lines.append(volume)
    if utilization:
        lines.append(utilization)

    caveat = _MEASURE_CAVEAT.get(measure)
    if caveat:
        lines.append(caveat)

    return " ".join(line for line in lines if line)


def _remainder_clause(view, measure, members, shown: int) -> str:
    """"The remaining 12 together account for Rs X." -- ruling 4's aggregated tail.

    Empty when nothing is left, and singular when one thing is: a sentence that
    says "the remaining 1 values" is the kind of seam that makes a reader stop
    trusting the rest of the number.
    """
    rest = members[shown:]
    if not rest:
        return ""
    amount = _fmt(view, measure, sum(m["value"] for m in rest))
    if len(rest) == 1:
        return f"The one remaining, {rest[0]['member']}, accounts for {amount}."
    return f"The remaining {_num(len(rest), 0)} together account for {amount}."


def volume_clause(view, measure, dimension, subspace_pairs, members) -> str:
    """The size companion (phase5b rule 2b), attached at build time.

    A decomposition of a TOTAL by a categorical dimension ranks its members
    partly by how big they are. The report solved this by putting each group's
    share of the VOLUME beside its share of the money and requiring the writer to
    quote both; here there is no writer to require it of, so the sentence carries
    it itself. Returns "" where the comparison does not apply -- a temporal
    breakdown, or a decomposition OF the volume measure, where the share would
    restate the figure it is meant to check.
    """
    block = volume_share(view, dimension, measure, [list(p) for p in subspace_pairs])
    if not block:
        return ""
    top = members[0]
    if top["is_null"]:
        return ""
    vshare = block["share_of_volume"].get(top["member"])
    if vshare is None:
        return ""
    return (f"For size: {top['member']} holds {vshare} of the "
            f"{block['volume_in_scope']} behind these totals, against "
            f"{_pct(top['share'])} of {measure_phrase(view, measure)} -- a "
            f"group's total grows with how much of the work it holds.")


def utilization_clause(view, measure, dimension, subspace_pairs, members) -> str:
    """Spend as a share of what was planned or sanctioned (phase5b A8).

    Offered only where phase5b offers it: the two signed overspend measures, on a
    categorical non-fiscal-year breakdown, on a view that carries both sides of
    the ratio. An absolute shortfall ranks groups by size; the ratio does not,
    and the operator asked for the ratio at calibration session 2.
    """
    top = members[0]
    if top["is_null"]:
        return ""
    block = utilization_companion(view, dimension, measure,
                                  [list(p) for p in subspace_pairs],
                                  groups=[top["member"]])
    if not block:
        return ""
    values = _first_mapping(block, top["member"])
    if values is None:
        return ""
    return f"As a ratio rather than an amount, {top['member']} is {values}."


def _first_mapping(block: dict, key: str):
    """The companion's per-group figure for one group, whatever it named the map.

    `utilization_companion` is phase5b's and its output shape is phase5b's
    business; reading it by duck-typing rather than by a hard-coded key means a
    rename there degrades this clause to absent rather than to wrong.
    """
    for value in block.values():
        if isinstance(value, dict) and key in value:
            found = value[key]
            if isinstance(found, str):
                return found
    return None


# =============================================================================
# THE ENRICHED RETRIEVAL TEXT
# =============================================================================
# Same recipe and same pin as the findings corpus (WP-D5 ruling 7, applied
# verbatim): sentence, view title, glossary-expanded measure and dimension,
# subspace label, named members. Documents are embedded plain; the one query
# instruction lives on the query side and is imported, not restated.
#
# NO SHARED DOMAIN PREAMBLE. The one constant string here is the field label
# "Where it sits:", which is scaffolding of the same kind as phase5d's
# "Measure:" and "Within" -- four words naming what KIND of record this is, so a
# question shaped "where does the gap sit" has something to match on that a
# finding sentence does not carry. It is deliberately short, for the reason
# ruling 7 gives: text identical on every vector moves them all the same distance
# and blurs exactly the distinctions retrieval depends on.

def build_embed_text(view, measure, dimension, subspace_pairs, members,
                     sentence) -> str:
    lines = [sentence, long_view_title(view) + "."]
    lines.append(_clause("Measure:", measure_phrase(view, measure),
                         glossary_snippet(view, measure)))
    lines.append(_clause("Broken down by", display_name(dimension),
                         glossary_snippet(view, dimension)))
    lines.append("Within " + scope_phrase(view, subspace_pairs) + ".")
    lines.append(f"Where it sits: which {dimension_plural(dimension)} account "
                 f"for {measure_phrase(view, measure)}.")
    names = [m["member"] for m in members][:MAX_NAMED_IN_TEXT]
    tail = "" if len(members) <= MAX_NAMED_IN_TEXT else \
        f" and {len(members) - MAX_NAMED_IN_TEXT} more"
    lines.append("Named: " + ", ".join(names) + tail + ".")
    return "\n".join(lines)


def _clause(prefix: str, name: str, gloss: str) -> str:
    text = prefix + " " + name
    if gloss:
        text += " -- " + gloss
    return text.rstrip(".") + "."


# =============================================================================
# GEOGRAPHY -> LGD CODES, THROUGH ASK'S REGISTRY
# =============================================================================
# The same resolution the findings corpus uses, imported rather than rewritten
# (WP-D5's `resolve_geography`), so a Gram Panchayat is the same identity on a
# decomposition as on a finding and the retriever's one structural boost fires
# on both. Codes, not transliterated text (WP-4a).
#
# The ROLES differ from a finding's, and the difference carries meaning the
# boost uses:
#
#   subspace   the decomposition is OF this place -- "within Chikilli, where
#              does the shortfall sit". `GEO_SUBSPACE_BONUS` is for exactly this.
#   member     the place is one of the parts the total divides into -- "the
#              shortfall across all 20 Gram Panchayats, of which Chikilli is
#              13.9%". A real hit for "how is my GP doing", a weaker one.
#
# A decomposition BY a geography dimension names every place in the view, so
# nearly all of them resolve. That is not noise: it is the literal answer to
# "which Gram Panchayats account for this", and the role tells the two apart.

def geography_candidates(dimension: str, subspace_pairs: list,
                         members: list) -> dict:
    """Which places this decomposition may be ABOUT. Candidates, not conclusions.

    `resolve_geography` confirms each against Ask's registry and drops what does
    not resolve, so nothing reaches the corpus on the strength of the column it
    sat under.
    """
    geo = {"gp_name": [], "block_name": [], "district_name": []}
    roles = {}

    def add(dim, value, role):
        text = str(value).strip()
        if not text or text == NULL_LABEL:
            return
        if text not in geo[dim]:
            geo[dim].append(text)
        roles.setdefault(text, role)

    for dim, value in subspace_pairs:
        if dim in GEO_DIMS:
            add(dim, value, "subspace")
    if dimension in GEO_DIMS:
        for member in members:
            add(dimension, member["member"], "member")
    return {"gp_names": geo["gp_name"], "blocks": geo["block_name"],
            "districts": geo["district_name"], "roles": roles}


# =============================================================================
# ENUMERATION
# =============================================================================

def decomposable_measures(config) -> list:
    """The additive measures, in config order. An AVERAGE IS NOT DECOMPOSABLE.

    D6.0 asks for "each view's additive volume/amount measures". The test is the
    engine's own `agg`: a SUM decomposes -- the members add to the total, which
    is the whole identity this file is built on -- and a MEAN does not. view2's
    `payment_amount_mean` and `receipt_amount_mean` are the same rupees as their
    totals, averaged over GP-months (WP-D2c A4), so the money is not lost: it is
    decomposable through `payment_amount`, and only the per-unit framing is
    absent. Including them would put a record in the corpus whose members
    provably do not sum to its total, which is the one thing the gate forbids.
    """
    return [m.name for m in config.measures if m.agg == "sum"]


def breakdown_dimensions(config) -> list:
    """Categorical dimensions, then temporal-only ones, in config order.

    Temporal dimensions are breakdowns here for the reason D6.0 gives -- a gap by
    fiscal year is a legitimate decomposition -- and they are never filters,
    which is the engine's own rule (`generate_subspaces` uses categorical
    dimensions only).
    """
    return list(config.dimensions) + [
        d for d in config.temporal_dimensions if d not in config.dimensions
    ]


def subspaces_for(config, df) -> list:
    """Depth 0, plus every depth-1 subspace clearing the engine's 1% impact floor.

    The floor is `config.min_impact` read off the view's own config and applied
    through the engine's own `ImpactCalculator`, so "clears the 1% floor" means
    here exactly what it means in a mining run. Sorted by (dimension, value) so
    the record ids do not depend on the parquet's row order.
    """
    impact = ImpactCalculator(df, config.impact_measures)
    out = [(Subspace(frozenset()), 0.0)]
    pairs = []
    for dim in config.dimensions:
        for value in df[dim].dropna().unique():
            pairs.append((dim, str(value)))
    for dim, value in sorted(pairs):
        subspace = Subspace(frozenset([(dim, value)]))
        max_impact = impact.max_impact(subspace)
        if max_impact >= config.min_impact:
            out.append((subspace, float(max_impact)))
    return out


def build_records(views: tuple, validator=None) -> tuple:
    """Every valid decomposition, as a record. No embeddings.

    THREE THINGS ARE SKIPPED, AND NONE OF THEM IS A BUDGET DECISION.

      definitional pairs   the engine's own `excluded_pairs` (WP-D2c A1). A
                           decomposition of `is_ongoing` by `status_label` is
                           100% in WORK ONGOING because that is how the column
                           was built. The engine removes these at scope
                           generation; removing them here too keeps the
                           decompose space inside the space the engine already
                           ruled minable.
      an all-zero measure  there is no total to divide up. `is_completed` has 17
                           events sample-wide and `st_amount` two non-zero rows,
                           so most of their slices are empty.
      a single member      a decomposition into one part is the total restated.
                           Within a Gram Panchayat, "by block" has one member,
                           by construction.

    Every skip is counted and reported.
    """
    records, counts = [], {}

    for view in views:
        config = CONFIGS[view]
        df = pd.read_parquet(config.parquet_path)
        measures = decomposable_measures(config)
        dimensions = breakdown_dimensions(config)
        skipped = {"definitional": 0, "zero_total": 0, "single_member": 0}
        made = 0

        for subspace, impact in subspaces_for(config, df):
            pairs = sorted(subspace.filters)
            sub = apply_subspace(df, subspace)
            filtered_dims = {dim for dim, _ in pairs}
            for dimension in dimensions:
                if dimension in filtered_dims:
                    continue
                for measure in measures:
                    if config.is_excluded(measure, dimension):
                        skipped["definitional"] += 1
                        continue
                    column = config.get_column(measure)
                    members, total = decompose(sub, column, dimension)
                    if len(members) < 2:
                        skipped["single_member"] += 1
                        continue
                    gross, signs = shares(members)
                    if gross == 0:
                        skipped["zero_total"] += 1
                        continue

                    shape = shape_of(members, signs)
                    volume = volume_clause(view, measure, dimension, pairs, members)
                    utilization = utilization_clause(view, measure, dimension,
                                                     pairs, members)
                    sentence = build_sentence(
                        view, measure, dimension, pairs, members, total, gross,
                        signs, shape, volume, utilization)
                    embed_text = build_embed_text(
                        view, measure, dimension, pairs, members, sentence)

                    residual = total - sum(m["value"] for m in members)
                    geo = resolve_geography(
                        validator,
                        geography_candidates(dimension, pairs, members))
                    records.append({
                        # `finding_id`, not `decompose_id`, and the name is the
                        # design. DiscoverChat's `corpus.Finding` reads this key,
                        # and a decomposition that arrives under a different one
                        # would need a parallel record class, a parallel judge
                        # prompt and a parallel numeral check -- three places for
                        # the two corpora to drift apart. The `d` prefix and
                        # `record_type` keep them distinguishable where it
                        # matters, and identical everywhere it does not.
                        "finding_id": f"d{view[-1]}-{made:05d}",
                        "record_type": "decomposition",
                        "view": view,
                        "view_title": VIEW_TITLES[view],
                        "view_title_long": long_view_title(view),
                        "geography": geo,
                        "named_members": [m["member"] for m in members],
                        "measures": [measure],
                        "subspace_phrase": scope_phrase(view, pairs),
                        # No engine score: a decomposition is not a mined
                        # candidate and was never ranked against one. Zero keeps
                        # it above `QUALITY_FLOOR` (0.0) without pretending to a
                        # rank it does not have; `coverage_line` says what it is.
                        "score": 0.0,
                        "in_feed": False,
                        "feed_rank": None,
                        "view_rank": None,
                        "measure": measure,
                        "measure_phrase": measure_phrase(view, measure),
                        "measure_kind": measure_kind(view, measure),
                        "dimension": dimension,
                        "dimension_phrase": display_name(dimension),
                        "dimension_is_temporal":
                            dimension in config.temporal_dimensions,
                        "subspace": [list(p) for p in pairs],
                        "subspace_depth": len(pairs),
                        "subspace_impact": round(impact, 6),
                        "rows_in_scope": int(len(sub)),
                        "total": total,
                        "total_display": _fmt(view, measure, total),
                        "gross": gross,
                        "signs": signs,
                        "shape": shape["shape"],
                        "attribution_member": shape["attribution_member"],
                        "evenness": shape["evenness"],
                        "n_members": len(members),
                        "has_null_member": any(m["is_null"] for m in members),
                        "members": members,
                        "residual": residual,
                        "reconciles": _reconciles(total, members, gross),
                        "sentence": sentence,
                        "embed_text": embed_text,
                    })
                    made += 1

        counts[view] = {
            "rows": int(len(df)),
            "measures": len(measures),
            "dimensions": len(dimensions),
            "subspaces": len(subspaces_for(config, df)),
            "records": made,
            "skipped": skipped,
        }

    for record in records:
        record["embed_text_sha256"] = hashlib.sha256(
            record["embed_text"].encode("utf-8")).hexdigest()
    return records, counts


def _reconciles(total: float, members: list, gross: float) -> bool:
    residual = abs(total - sum(m["value"] for m in members))
    return residual <= max(RECONCILE_ABS, RECONCILE_REL * gross)


# =============================================================================
# BUILD
# =============================================================================

def load_stamp() -> dict:
    with open(os.path.join(MI_DIR, "global_feed_source_set.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


# =============================================================================
# EMBEDDING: CHUNKED, TIMED OUT, AND RESUMABLE
# =============================================================================
# MEASURED, on the first attempt at this build. `Embedder.documents()` embeds the
# whole list in one call, which is right for the findings corpus (4,239 texts,
# ~8 minutes) and wrong here: 36,218 texts is 566 requests, and the first attempt
# opened a connection to the endpoint at 15:34:56 and was still holding it fifty
# minutes later -- one CPU-second consumed in that time, one ESTABLISHED socket,
# no response, no error. The endpoint hung, and the client's default timeout did
# not fire.
#
# Three consequences, and each fixes something that attempt got wrong:
#
#   A TIMEOUT.  Set on a copy of the imported client via the SDK's own
#               `with_options`. `phase5d_retrieval_corpus` is import-only for
#               this WP, so its Embedder is not edited -- what changes is the
#               client this build hands it.
#   CHUNKS.     Progress is printed per chunk, so a stall is visible within a
#               chunk rather than after an hour of silence.
#   RESUMABLE.  Each chunk's vectors are appended to a partial cache on disk. A
#               build killed at 80% resumes from 80% instead of re-spending
#               ~5.6M embedding tokens, which at this size is the difference
#               between a retry and a decision.
EMBED_CHUNK = 640                  # ten of the Embedder's own 64-text batches
EMBED_TIMEOUT = float(os.getenv("DISCOVER_EMBED_TIMEOUT", "120"))
EMBED_HTTP_RETRIES = int(os.getenv("DISCOVER_EMBED_HTTP_RETRIES", "3"))
PARTIAL_CACHE_PATH = os.path.join(MI_DIR, "decompose_corpus.partial.npz")


def _timed_out_embedder():
    """`Embedder`, with a request timeout its own construction does not set."""
    embedder = Embedder()
    embedder._client = embedder._client.with_options(
        timeout=EMBED_TIMEOUT, max_retries=EMBED_HTTP_RETRIES)
    return embedder


def load_partial_cache() -> dict:
    if not os.path.exists(PARTIAL_CACHE_PATH):
        return {}
    try:
        with np.load(PARTIAL_CACHE_PATH) as data:
            return {key: data[key] for key in data.files}
    except Exception:
        return {}


def save_partial_cache(cache: dict) -> None:
    tmp = PARTIAL_CACHE_PATH + ".tmp"
    np.savez(tmp, **cache)
    os.replace(tmp, PARTIAL_CACHE_PATH)


# How much re-work a kill is allowed to cost. Rewriting the partial cache is a
# whole-file write of up to 148 MB, so saving after every chunk would spend more
# time on disk than on the endpoint; saving after this many new vectors bounds
# the loss to about a minute of embedding and the writes to a handful.
PARTIAL_SAVE_EVERY = 4000


def embed_missing(records: list, cache: dict) -> tuple:
    """Embed every text not already in `cache`, in chunks, saving as it goes.

    Returns (cache, embedder) -- the embedder carries the call counts the stamp
    records, and is None when nothing needed embedding.
    """
    need, seen = [], set()
    for record in records:
        key = record["embed_text_sha256"]
        if key in cache or key in seen:
            continue
        seen.add(key)
        need.append(record)
    print(f"  vectors: {len(records) - len(need):,} reused from cache, "
          f"{len(need):,} to embed", flush=True)
    if not need:
        return cache, None

    embedder = _timed_out_embedder()
    started = time.time()
    unsaved = 0
    for i in range(0, len(need), EMBED_CHUNK):
        chunk = need[i:i + EMBED_CHUNK]
        vectors = embedder.documents([r["embed_text"] for r in chunk])
        for record, vector in zip(chunk, vectors):
            cache[record["embed_text_sha256"]] = vector
        unsaved += len(chunk)
        if unsaved >= PARTIAL_SAVE_EVERY:
            save_partial_cache(cache)
            unsaved = 0
        done = min(i + EMBED_CHUNK, len(need))
        rate = done / max(time.time() - started, 1e-9)
        print(f"    embedded {done:,}/{len(need):,} "
              f"({rate:.0f} texts/s, "
              f"{(len(need) - done) / max(rate, 1e-9) / 60:.1f} min left, "
              f"{embedder.rate_limit_waits} rate-limit waits)", flush=True)
    save_partial_cache(cache)
    return cache, embedder


def load_vector_cache() -> dict:
    """sha256(embed_text) -> vector, from the PREVIOUS build.

    The same device phase5d uses, for the same reason: the embedding endpoint is
    NOT bit-deterministic (1.2e-3 per component, measured in WP-D5), so a build
    that re-embedded everything could never be byte-identical to the last one.
    Reuse is keyed on the exact text, so a change to the sentence or to the
    enrichment recipe invalidates exactly the records it changed.
    """
    if not (os.path.exists(CORPUS_PATH) and os.path.exists(VECTORS_PATH)):
        return {}
    try:
        with open(CORPUS_PATH, encoding="utf-8") as fh:
            old = json.load(fh)
        vectors = np.load(VECTORS_PATH)
    except Exception:
        return {}
    old_records = old.get("records", [])
    if len(old_records) != len(vectors):
        return {}
    if old.get("embedding_pin_fingerprint") != pin_fingerprint():
        return {}
    return {r["embed_text_sha256"]: vectors[i] for i, r in enumerate(old_records)}


def parquet_provenance(views: tuple) -> dict:
    """SHA and row count of every view parquet this build read.

    The findings corpus is built from the frozen candidate JSONs; this one is
    built from the view parquets, which are a rebuild output. The two must
    describe the same data or a decomposition and a finding about the same slice
    could disagree, so the parquet identity is recorded here and the gate
    compares it. `candidate_set_id` alone would not catch a rebuilt view.
    """
    out = {}
    for view in views:
        path = CONFIGS[view].parquet_path
        if os.path.exists(path):
            out[os.path.basename(path)] = {
                "sha256": sha256_of(path),
                "bytes": os.path.getsize(path),
            }
    return out


def write_outputs(records, counts, stamp, vectors, embedder, elapsed, views):
    reconciled = sum(1 for r in records if r["reconciles"])
    payload = {
        "what_this_is": (
            "WP-D6 decomposition corpus. One record per (measure, dimension, "
            "subspace) triple: how a measure's total divides among a "
            "dimension's values, precomputed. Every record is an accounting "
            "identity -- its members sum to its total -- and the D6.0 gate "
            "checks all of them. Nothing here correlates, infers or explains "
            "(D41); it is bookkeeping. Vectors live beside this file in "
            "decompose_corpus.npy, row-aligned with `records`."
        ),
        "candidate_set_id": stamp["candidate_set_id"],
        "source_generated_at": stamp["generated_at"],
        "embedding_pin": embedding_pin(),
        "embedding_pin_fingerprint": pin_fingerprint(),
        "reconciliation": {
            "records": len(records),
            "reconciled": reconciled,
            "failed": len(records) - reconciled,
            "relative_tolerance": RECONCILE_REL,
            "absolute_tolerance": RECONCILE_ABS,
        },
        "counts": counts,
        "view_parquets": parquet_provenance(views),
        "records": records,
    }
    with open(CORPUS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")

    if vectors is not None:
        np.save(VECTORS_PATH, vectors)

    with open(STAMP_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "what_this_is": (
                "Provenance for decompose_corpus.json/.npy. The `generated_at` "
                "line is the ONLY field expected to differ between two "
                "consecutive builds (D6.0 gate); everything else, vectors "
                "included, is reproduced from the cache."
            ),
            "artefacts": ["metainsights/decompose_corpus.json",
                          "metainsights/decompose_corpus.npy"],
            "candidate_set_id": stamp["candidate_set_id"],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "build_seconds": round(elapsed, 1),
            "embedding_pin": embedding_pin(),
            "embedding_pin_fingerprint": pin_fingerprint(),
            "embedding_calls": getattr(embedder, "calls", 0),
            "texts_embedded": getattr(embedder, "texts_embedded", 0),
            "records": len(records),
            "reconciled": reconciled,
            "counts": counts,
            "view_parquets": parquet_provenance(views),
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WP-D6 D6.0 decomposition corpus build")
    ap.add_argument("--no-embed", action="store_true",
                    help="build the records and skip the vectors (structure check)")
    ap.add_argument("--force-embed", action="store_true",
                    help="ignore the vector cache and re-embed everything")
    ap.add_argument("--views", default=",".join(VIEWS),
                    help="comma-separated subset, for a faster structure check")
    args = ap.parse_args(argv)

    views = tuple(v.strip() for v in args.views.split(",") if v.strip())
    for view in views:
        path = CONFIGS[view].parquet_path
        if not os.path.exists(path):
            raise SystemExit(
                f"STOP: no view parquet at {path}. Build the views first:\n"
                f"  python Insights/src/build_views.py --pack "
                f"Insights/domain_pack_prdw --data-dir Data "
                f"--views-dir Insights/views_prdw "
                f"--reports-dir Insights/reports_prdw --strict"
            )

    t0 = time.time()
    stamp = load_stamp()

    # A missing registry is a STOP, not a degradation -- phase5d's lesson,
    # unchanged. Ask's adapter fails SOFTLY when it has no views: registries
    # load empty and everything downstream passes vacuously. Here that would
    # build a decompose corpus with no geography at all, which still embeds,
    # still reconciles, still gates green, and answers no "where does the gap
    # sit in my Gram Panchayat" question.
    validator, why = open_ask_validator()
    if validator is None:
        raise SystemExit(
            f"STOP: Ask's entity registry could not be opened ({why}). "
            f"Geography resolution is load-bearing for the structural boost; "
            f"building without it would produce a corpus that looks complete "
            f"and answers no own-place question.")
    n_gp = len(validator.registry_values("gp"))
    if n_gp == 0:
        raise SystemExit(
            "STOP: Ask's GP registry loaded EMPTY. That is the soft-failure "
            "mode db_factory.open_analytical_db exists to prevent.")
    print(f"  Ask registry: {n_gp} GPs, "
          f"{len(validator.registry_values('block'))} blocks, "
          f"{len(validator.registry_values('district'))} districts")

    records, counts = build_records(views, validator)

    failed = [r["decompose_id"] for r in records if not r["reconciles"]]
    print(f"  {len(records):,} decompositions "
          + ", ".join(f"{v}={counts[v]['records']:,}" for v in views))
    for view in views:
        skipped = counts[view]["skipped"]
        print(f"    {view}: {counts[view]['subspaces']} subspaces x "
              f"{counts[view]['dimensions']} dimensions x "
              f"{counts[view]['measures']} measures; skipped "
              f"{skipped['definitional']:,} definitional, "
              f"{skipped['zero_total']:,} all-zero, "
              f"{skipped['single_member']:,} single-member")
    shapes = {}
    for r in records:
        shapes[r["shape"]] = shapes.get(r["shape"], 0) + 1
    print("  shapes: " + ", ".join(f"{k}={v:,}" for k, v in sorted(shapes.items())))
    print(f"  reconciliation: {len(records) - len(failed):,} of "
          f"{len(records):,} exact, {len(failed):,} failed")
    if failed:
        # A reconciliation failure is not a warning. A stored record whose
        # members do not sum to its total is a wrong answer waiting to be
        # retrieved, and ruling 2 is the whole basis of this capability.
        raise SystemExit(
            f"STOP: {len(failed)} record(s) do not reconcile: {failed[:5]}")

    distinct = len({r["embed_text_sha256"] for r in records})
    print(f"  distinct enriched texts: {distinct:,} of {len(records):,}")
    with_gp = sum(1 for r in records if r["geography"]["gp_lgd_codes"])
    rejected = sum(len(r["geography"]["rejected"]) for r in records)
    print(f"  geography: {with_gp:,} records name a registry-confirmed Gram "
          f"Panchayat; {rejected:,} candidate names rejected")

    embedder, vectors = None, None
    if not args.no_embed:
        # Three sources, in order of authority: the previous BUILD's vectors
        # (byte-identity between two builds rests on these), then a partial
        # cache left behind by a build that did not finish, then the endpoint.
        cache = {} if args.force_embed else load_vector_cache()
        if not args.force_embed:
            for key, vector in load_partial_cache().items():
                cache.setdefault(key, vector)
        cache, embedder = embed_missing(records, cache)
        # NOT re-normalised here -- `Embedder.documents` normalises once, at the
        # moment of embedding, and float32 L2-normalisation is not idempotent
        # (WP-D5 defect 1: a second pass moves the last bit of some components
        # and the byte-identity gate fails with nothing re-embedded).
        vectors = np.stack([cache[r["embed_text_sha256"]] for r in records])

    write_outputs(records, counts, stamp, vectors, embedder,
                  time.time() - t0, views)
    # The partial cache exists to survive a kill. Once `decompose_corpus.npy` is
    # written it holds the same vectors and `load_vector_cache` will find them
    # there, so leaving it behind would be a second 148 MB copy of the same
    # numbers in a Drive-synced directory.
    if vectors is not None and os.path.exists(PARTIAL_CACHE_PATH):
        os.remove(PARTIAL_CACHE_PATH)
    print(f"  wrote {CORPUS_PATH} "
          f"({os.path.getsize(CORPUS_PATH) / 1e6:.1f} MB)")
    if vectors is not None:
        print(f"  wrote {VECTORS_PATH}  shape={vectors.shape} "
              f"({os.path.getsize(VECTORS_PATH) / 1e6:.1f} MB)")
    print(f"  wrote {STAMP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

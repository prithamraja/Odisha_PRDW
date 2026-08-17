# =============================================================================
# Phase 2: MetaInsight Engine - Single View, Single Pattern Type
# =============================================================================
# Implements the core MetaInsight mining pipeline on View 1 (Claims Lifecycle)
# using a single pattern type: Outstanding #1.
#
# Architecture:
#   Module A - View configuration and data scope enumeration
#   Module B - Pattern detector (Outstanding #1 evaluator + caches)
#   Module C - HDP construction and MetaInsight identification
#   Module D - Scorer (conciseness + impact)
#   Module E - Engine orchestrator and output
#
# Outputs:
#   metainsights/view1_candidates.json  - all scored MetaInsight candidates
#   reports/engine_diagnostics.txt      - search space stats, cache hit rates, timing
#
# Run from project root:
#   python src/phase2_engine.py
# =============================================================================

import os
import sys
import math
import json
import time
import heapq
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# MODULE A: VIEW CONFIGURATION & DATA SCOPE ENUMERATION
# =============================================================================

@dataclass
class MeasureConfig:
    """A measure with its aggregation type (sum or avg).

    `column` lets a measure NAME differ from the parquet COLUMN it reads. An
    intensity measure is the same rupee column as its total, aggregated
    differently -- `payment_amount_mean` is `payment_amount` averaged over
    GP-months (WP-D2c A4). Carrying that as an alias keeps the pack's view SQL
    untouched: the column already exists, and what changes is how the engine
    aggregates it. `None` means the measure reads the column of its own name,
    which is every measure that shipped before this.
    """
    name: str
    agg: str = "sum"   # "sum" or "avg"
    column: Optional[str] = None

    @property
    def source_column(self) -> str:
        return self.column or self.name


@dataclass
class ViewConfig:
    """Configuration for a single analytical view passed to the engine."""
    name: str
    parquet_path: str

    dimensions: list            # categorical dimension columns
    temporal_dimensions: list   # temporal dimension columns (breakdown only)
    measures: list              # list[MeasureConfig] - numeric measure columns
    impact_measures: list       # subset of measure names used for impact scoring (always SUM)

    max_subspace_depth: int = 2  # max number of filters in a subspace
    tau: float = 0.5             # commonness proportion threshold
    min_impact: float = 0.01     # prune subspaces below this impact
    min_hdp_size: int = 3        # minimum HDP members to form a MetaInsight

    # --- WP-D2c A1: definitional (measure, breakdown) pairs ---------------
    # Calibration session 1, ruling 1: some measure x dimension pairs are
    # circular by construction, and breaking that measure down by that
    # dimension can only ever rediscover how the column was built. Four of
    # view1's fifteen top-ranked findings were of this class ("New/Fresh has
    # the highest trainees_total among work_type_label values" -- training
    # detail attaches only to New/Fresh activities).
    #
    # The pair is skipped at SCOPE GENERATION, which is the only place that
    # removes it everywhere at once: the scope never exists, so no pattern, no
    # HDP member and no measure-extending sibling can carry it. A dimension in
    # an excluded pair remains fully minable as a FILTER -- "within New/Fresh
    # activities, how do trainee numbers fall across Gram Panchayats" is a real
    # question, and it is the breakdown, not the slice, that is circular.
    excluded_pairs: tuple = ()   # tuple of (measure, breakdown) pairs

    # --- WP-D2c A7: minimum non-zero support for temporal patterns --------
    # A trend over a series that is almost all zeros is a statement about
    # recording, not about the programme. view3's top two findings were TRENDs
    # on `n_completed`, a column carrying 17 non-zero events in the whole
    # sample: 18 of its 20 per-Gram-Panchayat series have at most two non-zero
    # years out of six, and an all-zero series makes Spearman's rho undefined,
    # which the evaluator was reading as a decreasing trend.
    #
    # Both thresholds are read off this drop by sweeping them (WPD2c_REPORT
    # §1, A7), not chosen by taste:
    #
    #   the FLOOR of 4 is the longest minimum any temporal evaluator imposes on
    #   its own input (TREND needs 4 points), so a series with fewer real
    #   observations than that is being read by an evaluator that would have
    #   refused it outright had the zeros been absent rather than recorded.
    #
    #   the FRACTION was swept at 0.50, 1/3 and 0.25 on view2. At 0.50 twelve
    #   candidates are displaced, and all twelve are single-Gram-Panchayat
    #   monthly cash series carrying 34 to 56 non-zero months out of 72 -- real
    #   series, wrongly caught. At 1/3 and at 0.25 the number is zero and the
    #   candidate set is identical, so the data is flat across that range and
    #   1/3 is the top of the flat. `n_completed` fails at every value tried,
    #   because 18 of its 20 per-Gram-Panchayat series have at most two
    #   non-zero years and cannot clear the floor at any fraction.
    #
    # Candidates whose members mostly fail are not dropped: they are marked and
    # routed to the run's data-quality list (operator ruling, session 1 item 7).
    min_temporal_nonzero: int = 4              # absolute non-zero points required
    min_temporal_nonzero_frac: float = 1 / 3   # ... and as a share of the series

    # How far the extremum evaluators require the extreme value to stand clear
    # of its nearest neighbour. OUTSTANDING_LAST takes it directly (the minimum
    # must be at most `extremum_ratio` x the second-lowest); OUTSTANDING_1 takes
    # its reciprocal (the maximum must be at least 1/extremum_ratio x the
    # second-highest). Both were hard-coded at 0.67 / 1.5, i.e. "a third clear",
    # which is the right bar for volumetric extremes and the wrong one for
    # proportional measures: a social category drawing three-quarters of its
    # numerical share of a programme is a decisive equity finding at 0.75, and
    # 0.75 does not clear 0.67. Views built on rates raise it; the default is
    # unchanged, so no existing deployment moves.
    extremum_ratio: float = 0.67

    @property
    def measure_names(self) -> list:
        """All measure names for iteration."""
        return [m.name for m in self.measures]

    def get_agg(self, measure_name: str) -> str:
        """Return the aggregation type ('sum' or 'avg') for a measure."""
        for m in self.measures:
            if m.name == measure_name:
                return m.agg
        return "sum"

    def get_column(self, measure_name: str) -> str:
        """The parquet column a measure reads. Its own name unless aliased."""
        for m in self.measures:
            if m.name == measure_name:
                return m.source_column
        return measure_name

    def is_excluded(self, measure: str, breakdown: str) -> bool:
        """Is this (measure, breakdown) pair definitional? See excluded_pairs."""
        return (measure, breakdown) in self._excluded_set

    @property
    def _excluded_set(self) -> frozenset:
        # built once, on first use; the tuple is fixed at construction
        cached = self.__dict__.get("_excluded_cache")
        if cached is None:
            cached = frozenset(tuple(p) for p in self.excluded_pairs)
            self.__dict__["_excluded_cache"] = cached
        return cached


# =============================================================================
# DISCOVER SCALE SWITCH — sample (20 GPs) vs statewide (~6,800 GPs)
# =============================================================================
# D15 / DISCOVER_VIEW_MAPPING.md §6. This drop is a 20-GP sample; the statewide
# drop is ~6,800 Gram Panchayats across 314 blocks and 30 districts. Everything
# that differs between the two is a dimension list or a subspace depth — the
# measures, the impact measures and every threshold are identical — so the
# difference is carried HERE, in one module-level switch read from the
# environment, in the same shape as the Ask adapter's `_DB_SOURCES`:
#
#     DISCOVER_SCALE=statewide python src/phase4b_engine.py
#
# The statewide branches ship now and are UNTESTED: no statewide drop exists
# yet. Each carries the §6 reason it differs. Switching scale must never become
# a code edit — that is the whole promise D15 makes — so the branches live in
# the configs and nowhere else. `expected_rows` / `post_view` counts are the
# pack's business (sources.yaml, validation.yaml), not the engine's.
DISCOVER_SCALE = os.getenv("DISCOVER_SCALE", "sample")
_STATEWIDE = DISCOVER_SCALE == "statewide"


# --- View 1 configuration ---
# Domain: Odisha Panchayati Raj & Drinking Water. Built by
# domain_pack_prdw/views/view1_activity_lifecycle.sql — one row per planned
# activity (12,704 in this sample), from plan through sanction and spending to
# status and photo evidence.
#
# Wide by design: 17 dimensions x 24 measures. Every dimension here is a NAME
# column. The view also carries the LGD code for each geography because the
# frontend contract needs it, and a code is the same dimension as its name —
# mining both would find every geographic pattern twice and rank the duplicate
# next to the original. Codes stay out of every config.
#
# No temporal dimension: D22 / §5 routes ALL temporal mining to view2, whose
# cashbook axis is free of the 2023-24 reporting artifact. `fiscal_year` is
# here as a CATEGORICAL dimension only.
#
# The geography names are dimensions at sample scale and drop out statewide:
# 6,800 GP values and 314 block values put every depth-2 GP subspace far below
# the 1% impact prune (§6), so they would cost the whole enumeration budget and
# return nothing rankable. GP remains the GRAIN either way — findings still
# name individual GPs as HDP members and as exceptions.
_VIEW1_GEO_DIMS = ["district_name"] if _STATEWIDE else [
    "gp_name", "block_name", "district_name",
]

VIEW1_CONFIG = ViewConfig(
    name="Activity Lifecycle",
    parquet_path=os.path.join(BASE_DIR, "views_prdw", "view1_activity_lifecycle.parquet"),

    dimensions=_VIEW1_GEO_DIMS + [
        "theme",                   # 7 values  — 6 LSDG themes + 'Unmapped theme'
        "focus_area_name",         # 30 values — roads, drinking water, sanitation, ...
        "work_type_label",         # 4 values
        "activity_for_label",      # 4 values
        "activity_type_label",     # 2 values
        "output_type_label",       # 8 values  — 'Code 101'..'Code 110', no decode on file
        "status_label",            # 6 values  — Activity Approved dominates (10,108)
        "is_costless",             # 2 values  — Costed / Costless
        "tied_untied",             # 3 values, null on the 10,603 without a sanction
        "sanction_authority",      # 14 values (5 cleaned offices + 10 free-text residues)
        "sanctioned_scheme_name",  # 5 values, sanctioned subset only
        "fund_component_name",     # 8 values, sanctioned subset only
        "asset_category_label",    # 28 values — 27 named + 'Uncategorised' (8,439 rows)
        "fiscal_year",             # 6 values  — CATEGORICAL here; see §5 above
    ],

    temporal_dimensions=[],

    # Every PR&DW measure is a SUM (mapping doc §3): volumes, rupee amounts,
    # counted flags and the two signed overspend differences all add up across
    # rows. There is no rate or per-unit measure in v1 — the view is at activity
    # grain, so a rate would have to be assembled at query time, which the
    # engine cannot do. That is also why `extremum_ratio` is left at its 0.67
    # default below.
    measures=[
        MeasureConfig("n_activities",           "sum"),  # activities, 1 per row
        MeasureConfig("total_cost",             "sum"),  # PLANNED rupees
        MeasureConfig("fund_tied_total",        "sum"),  # PLANNED rupees, tied
        MeasureConfig("fund_untied_total",      "sum"),  # PLANNED rupees, untied
        MeasureConfig("fund_abandoned_total",   "sum"),  # PLANNED rupees on abandoned works
        MeasureConfig("work_proposed_cost",     "sum"),  # SANCTIONED rupees, proposed
        MeasureConfig("fund_sanctioned_total",  "sum"),  # SANCTIONED rupees
        MeasureConfig("total_expenditure",      "sum"),  # SPENT rupees, voucher-linked
        MeasureConfig("gen_amount",             "sum"),  # SPENT rupees, general component
        MeasureConfig("sc_amount",              "sum"),  # SPENT rupees — SUSPECTED LABEL SWAP
        MeasureConfig("st_amount",              "sum"),  # SPENT rupees — see WP-D1 §5.5
        MeasureConfig("overspend_vs_plan",      "sum"),  # SIGNED: spent minus planned
        MeasureConfig("overspend_vs_sanction",  "sum"),  # SIGNED: spent minus sanctioned
        MeasureConfig("is_started",             "sum"),  # counted flags, activities
        MeasureConfig("is_completed",           "sum"),  # 17 sample-wide — near-degenerate
        MeasureConfig("is_ongoing",             "sum"),
        MeasureConfig("is_abandoned",           "sum"),
        MeasureConfig("is_under_approval",      "sum"),
        MeasureConfig("is_admin_approved",      "sum"),
        MeasureConfig("has_technical_approval", "sum"),
        MeasureConfig("has_progress_evidence",  "sum"),
        MeasureConfig("evidence_uploads",       "sum"),  # geotagged photo uploads
        MeasureConfig("trainees_total",         "sum"),  # people, training subset
        MeasureConfig("beneficiaries_expected", "sum"),  # people, community-service subset
    ],

    impact_measures=[
        "n_activities",  # volume signal
        "total_cost",    # financial exposure (PLANNED basis, the only near-complete one)
    ],

    # D25 (WP-D2b): the SAMPLE runs at depth 1; statewide keeps depth 2.
    #
    # WP-D2 measured this view at depth 2 rather than estimating it. 13,322 of
    # the 13,495 enumerated subspaces are depth-2, and at 20 GPs those two-filter
    # slices average ~37 rows — statistically fragile, and the source of nothing
    # this sample can support. The full queue behind them is 880,752 data scopes,
    # which breaks two things at once: the never-evict QueryCache/PatternCache
    # (3.94 GB of process memory at 1.7% of the queue, on a 15.7 GB machine) and
    # the ranker (~800k projected candidates against a 5,000 pre-filter). Depth 1
    # is 127 subspaces / 48,792 scopes — an 18x cut, and the only knob on this
    # view with an order of magnitude in it. What it costs is every two-filter
    # slice ("within Bargarh district, among costless activities ..."); all 17
    # dimensions and all 24 measures are kept.
    #
    # STATEWIDE KEEPS DEPTH 2 and is compute-gated: at ~6,800 GPs a two-filter
    # subspace is populated and specific rather than fragile, and the geography
    # dimensions drop to district_name (see _VIEW1_GEO_DIMS), which is most of
    # the enumeration. It must not be run before the statewide checklist is
    # cleared — the engine-scaling WP and its provisioning — because the cache
    # and ranker walls above are scale walls, not sample walls.
    max_subspace_depth=2 if _STATEWIDE else 1,
    tau=0.5,
    min_impact=0.01,
    min_hdp_size=3,

    # WP-D2c A1. Thirty-two definitional pairs, of which six come from
    # calibration session 1 (marked) and the rest from the audit the brief asks
    # for -- the same class, found by measurement rather than by eye.
    #
    # THE TEST, run over the built view (WPD2c_REPORT §1 carries the table).
    # A pair qualifies under either of two measured rules:
    #
    #   (a) THE MEASURE IS THE DIMENSION VALUE, RESTATED. It is non-zero on at
    #       least 99% of the rows carrying one dimension value and on at most
    #       1% of every other row, so the column is that value's indicator with
    #       a number attached. `is_ongoing` is 1 exactly when status_label is
    #       WORK ONGOING; `fund_abandoned_total` is the money on abandoned
    #       works. The 1% tolerance is not slack for its own sake: 19 rupees of
    #       `fund_abandoned_total` sit on WORK ONGOING rows, which is a data
    #       defect and not a reason to keep mining the tautology.
    #
    #   (b) A CHILD TABLE CONFINED TO ONE VALUE. Every non-zero value of the
    #       measure sits in ONE dimension value, and at least 100 rows carry it
    #       -- training detail exists only for New/Fresh activities, on 1,034
    #       of them. Coverage inside that value is low, which is what makes it
    #       a child table rather than rule (a), and the breakdown is circular
    #       all the same.
    #
    # WHAT THE TEST DELIBERATELY LEAVES MINABLE. Nineteen further pairs have
    # single-value support on a near-empty column -- `st_amount` has two
    # non-zero rows in the whole sample and therefore looks "confined" to
    # whichever value those two rows happen to hold. That is sparsity, not
    # construction, and excluding it would hide a data-quality signal behind a
    # rule about definitions. It is reported instead (§1). Eighteen more sit at
    # 99.5-99.9% of mass in one value without being confined to it: real
    # concentration, and the finding is the concentration.
    #
    # And the rule does NOT reach the size artifact next door to it. "Activity
    # Approved has the lowest overspend_vs_plan among status values" holds 80%
    # of the shortfall in a status holding 79.6% of the activities -- that is
    # arithmetic, not a definition, and the answer to it is the volume share
    # the report now attaches to every total (phase5b, rule 2b), not a silent
    # deletion from the search space.
    #
    # The two `fund_untied_total` pairs are the one entry the audit does NOT
    # support on its own -- untied money spreads across seven fund components
    # (49.6% in the largest). They are in on the session's authority: a measure
    # named for one side of a classification, broken down BY that
    # classification, is circular whatever the residue looks like.
    excluded_pairs=(
        # --- child tables that attach to exactly one dimension value ---
        ("trainees_total",         "work_type_label"),        # session 1
        ("trainees_total",         "output_type_label"),
        ("trainees_total",         "asset_category_label"),
        ("beneficiaries_expected", "work_type_label"),        # session 1
        ("beneficiaries_expected", "output_type_label"),
        ("beneficiaries_expected", "asset_category_label"),
        # --- the tied/untied classification, broken down by itself ---
        ("fund_tied_total",        "fund_component_name"),    # session 1
        ("fund_tied_total",        "tied_untied"),            # session 1
        ("fund_tied_total",        "sanctioned_scheme_name"),
        ("fund_untied_total",      "fund_component_name"),    # session 1
        ("fund_untied_total",      "tied_untied"),            # session 1
        # --- measures that ARE a status, broken down by the status column ---
        ("is_completed",           "status_label"),
        ("is_ongoing",             "status_label"),
        ("is_started",             "status_label"),   # started = ongoing + completed
        ("is_abandoned",           "status_label"),
        ("is_under_approval",      "status_label"),
        ("fund_abandoned_total",   "status_label"),   # the money on abandoned works
        # --- money and evidence against the costed/costless split: a costless
        #     activity has no cost, no sanction, no voucher and no photograph,
        #     so every one of these ranks 'Costed' first by construction
        ("total_cost",             "is_costless"),
        ("fund_tied_total",        "is_costless"),
        ("fund_untied_total",      "is_costless"),
        ("fund_abandoned_total",   "is_costless"),
        ("work_proposed_cost",     "is_costless"),
        ("fund_sanctioned_total",  "is_costless"),
        ("total_expenditure",      "is_costless"),
        ("gen_amount",             "is_costless"),
        ("overspend_vs_plan",      "is_costless"),
        ("overspend_vs_sanction",  "is_costless"),
        ("is_abandoned",           "is_costless"),
        ("is_admin_approved",      "is_costless"),
        ("has_technical_approval", "is_costless"),
        ("has_progress_evidence",  "is_costless"),
        ("evidence_uploads",       "is_costless"),
    ),

    # extremum_ratio is deliberately NOT set: it stays at the 0.67 default.
    # AP raised every view to 0.80 because its findings were proportional (an
    # equity index at 0.75 of parity was being rejected by a bar built for
    # volumetric extremes). Every measure here is volumetric, so the loosened
    # bar would buy nothing and would lower the evidence standard.
)


# --- Core data structures ---

@dataclass(frozen=True)
class Subspace:
    """
    A set of dimension=value filters defining a slice of the data.
    Empty frozenset represents the full dataset (no filter applied).
    """
    filters: frozenset  # frozenset of (dim_name, value) tuples

    @property
    def depth(self) -> int:
        return len(self.filters)

    def __repr__(self):
        if not self.filters:
            return "{*}"
        return "{" + ", ".join(f"{k}:{v}" for k, v in sorted(self.filters)) + "}"


@dataclass(frozen=True)
class DataScope:
    """
    A 3-tuple (subspace, breakdown, measure) defining a specific analytical query.
    Corresponds to: SELECT breakdown, SUM(measure) ... WHERE subspace GROUP BY breakdown
    """
    subspace: Subspace
    breakdown: str   # dimension used for group-by
    measure: str     # column to aggregate

    def __repr__(self):
        return f"DS({self.subspace}, {self.breakdown}, {self.measure})"


@dataclass(frozen=True)
class Highlight:
    """
    Encodes the essential characteristic of a pattern.
    For Outstanding #1: the single breakdown value with the highest aggregate.
    """
    values: tuple  # tuple for hashability

    def __repr__(self):
        return str(self.values)


@dataclass(frozen=True)
class BasicDataPattern:
    """
    The result of evaluating one pattern type on one data scope.
    pattern_type is 'NO_PATTERN' when the pattern criteria are not met.
    """
    data_scope: DataScope
    pattern_type: str
    highlight: Optional[Highlight]


def apply_subspace(df: pd.DataFrame, subspace: Subspace) -> pd.DataFrame:
    """Filter df by all dimension=value conditions in the subspace."""
    result = df
    for dim, val in subspace.filters:
        result = result[result[dim] == val]
    return result


def generate_subspaces(config: ViewConfig, df: pd.DataFrame) -> list:
    """
    Generate all subspaces from depth 0 to max_subspace_depth.
    Only categorical dimensions (not temporal) are used as filters.
    Temporal dimensions are reserved for breakdowns only.
    """
    subspaces = [Subspace(frozenset())]  # depth 0: full dataset

    # Depth 1: one filter per (dimension, value) pair
    depth1 = []
    for dim in config.dimensions:
        for val in df[dim].dropna().unique():
            depth1.append(Subspace(frozenset([(dim, val)])))
    subspaces.extend(depth1)

    # Depth 2: combine pairs of depth-1 subspaces from different dimensions
    if config.max_subspace_depth >= 2:
        for i, s1 in enumerate(depth1):
            dim1 = next(iter(s1.filters))[0]
            for s2 in depth1[i + 1:]:
                dim2 = next(iter(s2.filters))[0]
                if dim1 != dim2:
                    subspaces.append(Subspace(s1.filters | s2.filters))

    return subspaces


def generate_data_scopes(subspace: Subspace, config: ViewConfig) -> list:
    """
    For a given subspace, enumerate all valid (breakdown, measure) combinations.
    Breakdown dimensions that are already used as filters are excluded, and so
    are the view's definitional (measure, breakdown) pairs (A1).
    """
    filtered_dims = {dim for dim, _ in subspace.filters}
    available_breakdowns = [
        d for d in config.dimensions + config.temporal_dimensions
        if d not in filtered_dims
    ]
    return [
        DataScope(subspace, breakdown, measure)
        for breakdown in available_breakdowns
        for measure in config.measure_names
        if not config.is_excluded(measure, breakdown)
    ]


class ImpactCalculator:
    """
    Lazily computes and caches subspace-level impact values.
    Impact(subspace, measure) = SUM(measure in subspace) / SUM(measure in full df).
    """

    def __init__(self, df: pd.DataFrame, impact_measures: list):
        self._df = df
        self._totals = {m: df[m].sum() for m in impact_measures}
        self._impact_measures = impact_measures
        self._cache: dict = {}

    def get(self, subspace: Subspace) -> dict:
        if subspace in self._cache:
            return self._cache[subspace]
        filtered = apply_subspace(self._df, subspace)
        impacts = {}
        for m in self._impact_measures:
            total = self._totals[m]
            impacts[m] = filtered[m].sum() / total if total > 0 else 0.0
        self._cache[subspace] = impacts
        return impacts

    def max_impact(self, subspace: Subspace) -> float:
        return max(self.get(subspace).values())


def build_priority_queue(
    subspaces: list,
    impact_calc: ImpactCalculator,
    min_impact: float,
) -> list:
    """
    Build a max-heap of (neg_impact, tiebreaker, subspace) tuples.
    Subspaces below min_impact are pruned entirely.
    The tiebreaker counter avoids comparing Subspace objects (which don't
    implement __lt__, so heapq would raise TypeError without it).
    """
    queue = []
    counter = 0
    for subspace in subspaces:
        max_imp = impact_calc.max_impact(subspace)
        if max_imp >= min_impact:
            heapq.heappush(queue, (-max_imp, counter, subspace))
            counter += 1
    return queue


# =============================================================================
# MODULE B: PATTERN DETECTOR
# =============================================================================

def query_data_scope(df: pd.DataFrame, data_scope: DataScope, config: ViewConfig) -> pd.Series:
    """
    Execute a grouped aggregation respecting the measure's configured agg type.
    SUM for additive measures; AVG for rates and durations.
    Returns a Series indexed by breakdown values, sorted by index.
    """
    filtered = apply_subspace(df, data_scope.subspace)
    if len(filtered) == 0:
        return pd.Series(dtype=float)
    agg_type = config.get_agg(data_scope.measure)
    column   = config.get_column(data_scope.measure)
    if agg_type == "avg":
        result = filtered.groupby(data_scope.breakdown)[column].mean()
    else:
        result = filtered.groupby(data_scope.breakdown)[column].sum()
    return result.sort_index()


class QueryCache:
    """Cache for groupby query results keyed by DataScope.

    WP-D2c T3 gives it a bound. It was never-evict, and never-evict is what put
    3.94 GB of process memory behind 1.7% of view1's depth-2 queue (WP-D2 §2) --
    the wall that stopped that run, and a wall that arrives with scale rather
    than with time. `max_entries=None` keeps the original behaviour exactly, so
    every measurement taken before this change still reproduces; a number turns
    on least-recently-used eviction, and `evictions` records what it cost.
    """

    def __init__(self, max_entries: Optional[int] = None):
        self._cache: "OrderedDict" = OrderedDict()
        self._aug_cache: "OrderedDict" = OrderedDict()  # augmented 2-col groupby
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _evict(self):
        if self.max_entries is None:
            return
        while len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
            self.evictions += 1
        # the augmented cache holds far fewer, far larger frames; it gets an
        # eighth of the budget so one wide two-column groupby cannot hold the
        # whole allowance on its own
        aug_cap = max(16, self.max_entries // 8)
        while len(self._aug_cache) > aug_cap:
            self._aug_cache.popitem(last=False)
            self.evictions += 1

    def get(self, data_scope: DataScope) -> Optional[pd.Series]:
        key = (data_scope.subspace, data_scope.breakdown, data_scope.measure)
        if key in self._cache:
            self.hits += 1
            if self.max_entries is not None:
                self._cache.move_to_end(key)
            return self._cache[key]
        self.misses += 1
        return None

    def peek(self, data_scope: DataScope) -> Optional[pd.Series]:
        """The cached series without counting a hit or a miss.

        The A7 support guard reads series the pattern evaluators have already
        fetched. Counting those reads as cache hits would inflate the hit rate
        the diagnostics report -- the guard is not doing the mining's work.
        """
        return self._cache.get(
            (data_scope.subspace, data_scope.breakdown, data_scope.measure)
        )

    def put(self, data_scope: DataScope, result: pd.Series):
        key = (data_scope.subspace, data_scope.breakdown, data_scope.measure)
        self._cache[key] = result
        self._evict()

    def prefetch_subspace_hdp(
        self,
        df: pd.DataFrame,
        hdp_scopes: list,
        ext_dim: str,
        config: ViewConfig,
    ):
        """
        Augmented-query optimisation (paper Section 4.2.2).

        For a subspace-extending HDP, all members differ only in the value of
        ext_dim. Instead of one filter+groupby per member, we do a single
        two-column groupby over (breakdown, ext_dim) on the base-filtered data,
        then slice per ext_dim value. This gives an N-fold speedup where N is
        the number of HDP members (up to 75 for the district dimension).
        """
        if not hdp_scopes:
            return
        ref_ds   = hdp_scopes[0]
        breakdown = ref_ds.breakdown
        measure   = ref_ds.measure

        # Base subspace: all filters except the varying ext_dim
        base_filters  = frozenset(
            (k, v) for k, v in ref_ds.subspace.filters if k != ext_dim
        )
        base_subspace = Subspace(base_filters)
        aug_key       = (base_subspace, breakdown, ext_dim, measure)

        if aug_key not in self._aug_cache:
            filtered = apply_subspace(df, base_subspace)
            if len(filtered) == 0 or ext_dim not in filtered.columns:
                return
            agg_type = config.get_agg(measure)
            column   = config.get_column(measure)
            if agg_type == "avg":
                self._aug_cache[aug_key] = (
                    filtered.groupby([breakdown, ext_dim])[column].mean()
                )
            else:
                self._aug_cache[aug_key] = (
                    filtered.groupby([breakdown, ext_dim])[column].sum()
                )

        aug_result = self._aug_cache[aug_key]

        # Slice per member and populate the individual scope cache
        for ds in hdp_scopes:
            scope_key = (ds.subspace, breakdown, measure)
            if scope_key in self._cache:
                continue  # already cached from prior evaluation
            ext_val = next(
                (v for k, v in ds.subspace.filters if k == ext_dim), None
            )
            if ext_val is None:
                continue
            try:
                member_series = aug_result.xs(ext_val, level=ext_dim)
            except KeyError:
                member_series = pd.Series(dtype=float)
            self._cache[scope_key] = member_series
            # Count as a hit since the augmented query did the work
            self.hits += 1
        self._evict()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class PatternCache:
    """Cache for pattern evaluation results keyed by (DataScope, pattern_type).

    Bounded the same way as QueryCache, and for the same reason. Its entries
    are small (a pattern type and a highlight tuple), so it is not the memory
    wall the query cache is -- but at 880,752 scopes x 11 pattern types the
    key tuples alone are hundreds of megabytes.
    """

    def __init__(self, max_entries: Optional[int] = None):
        self._cache: "OrderedDict" = OrderedDict()
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, data_scope: DataScope, pattern_type: str) -> Optional[BasicDataPattern]:
        key = (data_scope, pattern_type)
        if key in self._cache:
            self.hits += 1
            if self.max_entries is not None:
                self._cache.move_to_end(key)
            return self._cache[key]
        self.misses += 1
        return None

    def put(self, data_scope: DataScope, pattern_type: str, pattern: BasicDataPattern):
        self._cache[(data_scope, pattern_type)] = pattern
        if self.max_entries is not None:
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
                self.evictions += 1

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# =============================================================================
# WP-D2c A7 — non-zero support behind a temporal series
# =============================================================================
# A time series that is almost entirely zeros will still hand a trend detector
# something to fit. `n_completed` is the case that produced the ruling: 17
# non-zero events in 120 GP-years, and 17 of view3's 20 per-GP series were
# reported as DECREASING because Spearman's rho on an all-zero series is NaN
# and NaN fails every rejection test it is compared against.
#
# The guard is applied at the HDP, not at the scope: a finding is displaced
# when the members that BOTH carry the common pattern AND have enough non-zero
# points no longer make a commonness set. That keeps a genuine pattern with a
# few thin members, and drops a pattern that exists only because its members
# are empty.

def temporal_support(distribution: pd.Series) -> tuple:
    """(points, non-zero points) in a series, NaN excluded."""
    dist = distribution.dropna()
    return len(dist), int((dist != 0).sum())


def temporal_support_ok(distribution: pd.Series, config: ViewConfig) -> bool:
    """Does this series carry enough non-zero points to be read as a series?"""
    n, nz = temporal_support(distribution)
    if n == 0:
        return False
    return (nz >= config.min_temporal_nonzero
            and nz >= config.min_temporal_nonzero_frac * n)


def evaluate_outstanding_1(
    distribution: pd.Series, extremum_ratio: float = 0.67
) -> Optional[Highlight]:
    """
    Outstanding #1: one breakdown value has a significantly higher aggregate
    than all others.

    Criteria:
      1. At least 3 breakdown values with a non-zero total.
      2. Top value's z-score relative to the rest >= 2.0.
      3. Top value is at least 1/extremum_ratio x the second-highest value
         (1.49x at the 0.67 default; the view config may loosen it).

    Returns Highlight((top_label,)) if criteria are met, else None.
    """
    dist = distribution.dropna()
    if len(dist) < 3 or dist.sum() == 0:
        return None

    max_val   = dist.max()
    max_label = dist.idxmax()
    rest      = dist.drop(max_label)

    # Condition 1: z-score of the top value vs the rest
    rest_mean = rest.mean()
    rest_std  = rest.std()
    if rest_std > 0:
        if (max_val - rest_mean) / rest_std < 2.0:
            return None
    else:
        # All others are identical; max must be strictly greater
        if max_val <= rest_mean:
            return None

    # Condition 2: dominance ratio vs second-highest
    second_max = rest.max()
    if second_max > 0 and max_val / second_max < 1.0 / extremum_ratio:
        return None

    return Highlight(values=(max_label,))


evaluate_outstanding_1.uses_extremum_ratio = True


def call_evaluator(fn, distribution: pd.Series, config: "ViewConfig"):
    """Run one evaluator, handing it the view's extremum ratio if it takes one.

    Evaluators are looked up by name out of a registry and most of them need
    nothing but the distribution, so the threshold is passed by opt-in: an
    evaluator that reads it sets `uses_extremum_ratio` on itself. That keeps
    the registry's uniform one-argument contract for everything else.
    """
    if getattr(fn, "uses_extremum_ratio", False):
        return fn(distribution, config.extremum_ratio)
    return fn(distribution)


# Pattern evaluator registry (Phase 4 adds more types here)
PATTERN_EVALUATORS = {
    "OUTSTANDING_1": evaluate_outstanding_1,
}

# Temporal-only types: only valid when the breakdown is a temporal dimension
TEMPORAL_ONLY_TYPES = {"TREND", "OUTLIER", "SEASONALITY", "CHANGE_POINT", "UNIMODALITY"}


def detect_pattern(
    df: pd.DataFrame,
    data_scope: DataScope,
    pattern_type: str,
    query_cache: QueryCache,
    config: ViewConfig,
) -> BasicDataPattern:
    """
    Detect a specific pattern type in a data scope, using the query cache.
    Returns BasicDataPattern with NO_PATTERN if criteria are not met.
    """
    # Temporal-only patterns require a temporal breakdown
    if pattern_type in TEMPORAL_ONLY_TYPES:
        if data_scope.breakdown not in config.temporal_dimensions:
            return BasicDataPattern(data_scope, "NO_PATTERN", None)

    # Query (cached)
    distribution = query_cache.get(data_scope)
    if distribution is None:
        distribution = query_data_scope(df, data_scope, config)
        query_cache.put(data_scope, distribution)

    if len(distribution) == 0:
        return BasicDataPattern(data_scope, "NO_PATTERN", None)

    highlight = call_evaluator(PATTERN_EVALUATORS[pattern_type], distribution, config)
    if highlight is not None:
        return BasicDataPattern(data_scope, pattern_type, highlight)

    return BasicDataPattern(data_scope, "NO_PATTERN", None)


# =============================================================================
# MODULE C: HDP CONSTRUCTION & METAINSIGHT IDENTIFICATION
# =============================================================================

def extend_subspace(
    data_scope: DataScope,
    df: pd.DataFrame,
    config: ViewConfig,
) -> list:
    """
    Generate sibling HDP groups by varying a filter dimension.

    Strategy 1 (vary existing filter):
      For each dimension already in the subspace, replace its value with every
      possible value in that dimension's domain. Sibling scopes share the same
      non-varying filters, breakdown, and measure.
      Example: ({specialty:OBG, gender:M}, district, cases)
        -> vary specialty -> ({specialty:OBG,...}, district, cases) x 11 siblings

    Strategy 2 (add a new filter dimension):
      For subspaces below max depth, introduce each unused dimension as a new
      filter, creating siblings for each value.
      Example: ({*}, district, cases)
        -> add specialty -> ({specialty:OBG}, district, cases) x 11 siblings

    Returns list of (strategy, extending_dimension, [DataScope...]).
    """
    results = []
    breakdown = data_scope.breakdown
    measure   = data_scope.measure
    current_filters = dict(data_scope.subspace.filters)

    # Strategy 1: vary each dimension already in the subspace
    for filter_dim in current_filters:
        base_filters = frozenset(
            (k, v) for k, v in current_filters.items() if k != filter_dim
        )
        siblings = [
            DataScope(Subspace(base_filters | frozenset([(filter_dim, val)])), breakdown, measure)
            for val in df[filter_dim].dropna().unique()
        ]
        if len(siblings) >= config.min_hdp_size:
            results.append(("subspace", filter_dim, siblings))

    # Strategy 2: add a new filter dimension (only when below max depth)
    if data_scope.subspace.depth < config.max_subspace_depth:
        excluded = set(current_filters.keys()) | {breakdown}
        for extend_dim in config.dimensions:
            if extend_dim in excluded:
                continue
            siblings = [
                DataScope(
                    Subspace(data_scope.subspace.filters | frozenset([(extend_dim, val)])),
                    breakdown, measure,
                )
                for val in df[extend_dim].dropna().unique()
            ]
            if len(siblings) >= config.min_hdp_size:
                results.append(("subspace", extend_dim, siblings))

    return results


def extend_measure(data_scope: DataScope, config: ViewConfig) -> list:
    """
    Generate a sibling HDP group by varying the measure while keeping
    subspace and breakdown fixed. Definitional pairs (A1) are not siblings:
    the excluded scope does not exist, so it cannot be an HDP member either.
    """
    siblings = [
        DataScope(data_scope.subspace, data_scope.breakdown, m)
        for m in config.measure_names
        if not config.is_excluded(m, data_scope.breakdown)
    ]
    if len(siblings) >= config.min_hdp_size:
        return [("measure", "measure", siblings)]
    return []


def extend_breakdown(data_scope: DataScope, config: ViewConfig) -> list:
    """
    Generate a sibling HDP group by varying the breakdown across all
    temporal dimensions, keeping subspace and measure fixed.
    (With only 3 temporal dimensions this yields size-3 HDPs - small but valid.)
    """
    siblings = [
        DataScope(data_scope.subspace, b, data_scope.measure)
        for b in config.temporal_dimensions
        if not config.is_excluded(data_scope.measure, b)
    ]
    if len(siblings) >= config.min_hdp_size:
        return [("breakdown", "temporal_grain", siblings)]
    return []


def _member_label(
    data_scope: DataScope,
    extending_strategy: str,
    extending_dimension: str,
) -> str:
    """Extract the label that identifies this member within its HDP."""
    if extending_strategy == "subspace":
        for dim, val in data_scope.subspace.filters:
            if dim == extending_dimension:
                return str(val)
        return "?"
    elif extending_strategy == "measure":
        return data_scope.measure
    elif extending_strategy == "breakdown":
        return data_scope.breakdown
    return "?"


@dataclass
class MetaInsightCandidate:
    """A candidate MetaInsight with HDP definition, partition results, and scores."""
    extending_strategy: str   # "subspace", "measure", or "breakdown"
    extending_dimension: str  # which dimension was varied to form the HDP
    pattern_type: str
    breakdown: str            # shared breakdown, or "(varies)" for breakdown-extending
    measure: str              # shared measure, or "(varies)" for measure-extending
    base_subspace: Subspace   # the subspace portion NOT varied across the HDP

    commonness_sets: list     # [{highlight, pattern_type, members, count, proportion}]
    exceptions: list          # [{member_label, category, highlight, pattern_type}]
    hdp_size: int

    hdp_member_subspaces: list = field(default_factory=list)  # excluded from JSON

    # Filled by Module D
    conciseness: float = 0.0
    impact: float = 0.0
    score: float = 0.0
    impact_measure_used: str = ""

    # WP-D2c A7: set when the temporal series behind this candidate's
    # commonness are too sparse to read as series. The candidate is NOT
    # discarded -- run_engine routes it to the run's data-quality list.
    low_temporal_support: bool = False
    support_note: str = ""

    # WP-D2c A2: twin merge (phase5_ranking). The label of the candidate this
    # one absorbed, so the merge is visible on the finding rather than only in
    # a log.
    merged_twins: list = field(default_factory=list)

    # WP-D2c T3: the identity the mining loop deduplicates on -- the HDP's
    # member subspaces, its pattern type, breakdown and measure. It used to
    # live only in run_engine's local `evaluated_hdps` set, which works while
    # there is one loop; with the queue sharded across processes each shard has
    # its own set, so the key travels ON the candidate and the merge does the
    # last deduplication pass. Never serialised.
    dedup_key: Optional[int] = None

    def to_dict(self) -> dict:
        d = {
            "extending_strategy":  self.extending_strategy,
            "extending_dimension": self.extending_dimension,
            "pattern_type":        self.pattern_type,
            "breakdown":           self.breakdown,
            "measure":             self.measure,
            "base_subspace":       [list(f) for f in self.base_subspace.filters],
            "hdp_size":            self.hdp_size,
            "commonness_sets":     self.commonness_sets,
            "exceptions":          self.exceptions,
            "conciseness":         round(self.conciseness, 6),
            "impact":              round(self.impact, 6),
            "score":               round(self.score, 6),
            "impact_measure_used": self.impact_measure_used,
        }
        if self.low_temporal_support:
            d["low_temporal_support"] = True
            d["support_note"] = self.support_note
        if self.merged_twins:
            d["merged_twins"] = self.merged_twins
        return d

    def canonical_key(self) -> str:
        """A stable, content-derived identity for this candidate.

        Two candidates that say the same thing produce the same key whatever
        order they were mined in, and the key orders ties in the output file.
        Everything in it is sorted: the base subspace is a frozenset, and the
        member lists come out of a partition whose order follows the order the
        HDP was enumerated in -- which is exactly what parallel mining is
        allowed to change.
        """
        subspace = ";".join(sorted(f"{k}={v}" for k, v in self.base_subspace.filters))
        commonness = "|".join(sorted(
            f"{cs['pattern_type']}~{cs['highlight']}~"
            + ",".join(sorted(str(m) for m in cs["members"]))
            for cs in self.commonness_sets
        ))
        exceptions = "|".join(sorted(
            f"{e['member_label']}~{e['category']}~{e['highlight']}"
            for e in self.exceptions
        ))
        return "||".join([
            self.extending_strategy, self.extending_dimension, self.pattern_type,
            self.breakdown, self.measure, subspace, str(self.hdp_size),
            commonness, exceptions,
        ])


def evaluate_hdp(
    hdp_scopes: list,
    pattern_type: str,
    extending_strategy: str,
    extending_dimension: str,
    df: pd.DataFrame,
    config: ViewConfig,
    query_cache: QueryCache,
    pattern_cache: PatternCache,
) -> Optional[MetaInsightCandidate]:
    """
    Evaluate all data scopes in an HDP.
    Partitions results into commonness sets and exceptions.
    Returns MetaInsightCandidate if at least one commonness set is found, else None.

    Includes early-termination pruning: if enough members have been evaluated
    that no group can possibly reach the tau threshold with remaining members,
    we abort and return None immediately.
    """
    n       = len(hdp_scopes)
    tau     = config.tau
    patterns = []

    for ds in hdp_scopes:
        cached = pattern_cache.get(ds, pattern_type)
        if cached is not None:
            patterns.append(cached)
        else:
            p = detect_pattern(df, ds, pattern_type, query_cache, config)
            pattern_cache.put(ds, pattern_type, p)
            patterns.append(p)

        # Early termination: check if any group can still reach tau
        j         = len(patterns)
        remaining = n - j
        if j > n * (1 - tau):
            valid = [
                (p.pattern_type, p.highlight)
                for p in patterns
                if p.pattern_type not in ("NO_PATTERN", "OTHER_PATTERN")
            ]
            if not valid:
                if remaining / n < tau:
                    return None
            else:
                max_count = Counter(valid).most_common(1)[0][1]
                if (max_count + remaining) / n < tau:
                    return None

    # Partition by (pattern_type, highlight)
    groups: dict = {}
    no_pattern_list    = []
    other_pattern_list = []

    for p in patterns:
        if p.pattern_type == "NO_PATTERN":
            no_pattern_list.append(p)
        elif p.pattern_type == "OTHER_PATTERN":
            other_pattern_list.append(p)
        else:
            key = (p.pattern_type, p.highlight)
            groups.setdefault(key, []).append(p)

    # Identify commonness sets (proportion > tau)
    commonness_sets   = []
    exception_patterns = []

    for (ptype, highlight), members in groups.items():
        proportion = len(members) / n
        if proportion > tau:
            commonness_sets.append({
                "highlight":    str(highlight),
                "pattern_type": ptype,
                "members":      [_member_label(m.data_scope, extending_strategy, extending_dimension)
                                 for m in members],
                "count":        len(members),
                "proportion":   round(proportion, 4),
            })
        else:
            exception_patterns.extend(members)

    if not commonness_sets:
        return None

    exception_patterns.extend(no_pattern_list)
    exception_patterns.extend(other_pattern_list)

    # Categorise exceptions
    exceptions = []
    for ep in exception_patterns:
        label = _member_label(ep.data_scope, extending_strategy, extending_dimension)
        if ep.pattern_type == "NO_PATTERN":
            category = "NO_PATTERN"
        elif ep.pattern_type == "OTHER_PATTERN":
            category = "TYPE_CHANGE"
        else:
            category = "HIGHLIGHT_CHANGE"
        exceptions.append({
            "member_label": label,
            "category":     category,
            "highlight":    str(ep.highlight) if ep.highlight else None,
            "pattern_type": ep.pattern_type,
        })

    # Derive base_subspace: the subspace portion not varied across the HDP
    ref_scope = hdp_scopes[0]
    if extending_strategy == "subspace":
        base_filters = frozenset(
            (k, v) for k, v in ref_scope.subspace.filters
            if k != extending_dimension
        )
        base_subspace = Subspace(base_filters)
    else:
        base_subspace = ref_scope.subspace

    # -- A7: is the commonness carried by series with real non-zero support? --
    low_support, support_note = False, ""
    if pattern_type in TEMPORAL_ONLY_TYPES:
        supported = {}
        for p in patterns:
            series = query_cache.peek(p.data_scope)
            if series is None:
                # the pattern came from the pattern cache and the query cache
                # has since evicted its series. Recomputing is the only honest
                # answer: treating a missing series as unsupported would let
                # cache pressure decide which findings are data-quality items.
                series = query_data_scope(df, p.data_scope, config)
                query_cache.put(p.data_scope, series)
            supported[p.data_scope] = temporal_support_ok(series, config)
        top = max(commonness_sets, key=lambda cs: cs["count"])
        common_scopes = [
            p.data_scope for p in patterns
            if p.pattern_type == top["pattern_type"]
            and str(p.highlight) == top["highlight"]
        ]
        n_supported = sum(1 for ds in common_scopes if supported.get(ds))
        if n_supported / n <= config.tau:
            low_support = True
            nonzeros = sorted(
                temporal_support(query_cache.peek(ds))[1]
                for ds in common_scopes if query_cache.peek(ds) is not None
            )
            support_note = (
                f"{n_supported} of the {top['count']} members carrying this "
                f"pattern have at least {config.min_temporal_nonzero} non-zero "
                f"points and at least "
                f"{config.min_temporal_nonzero_frac:.0%} of their series "
                f"non-zero; non-zero points per member run "
                f"{nonzeros[0] if nonzeros else 0}-"
                f"{nonzeros[-1] if nonzeros else 0}"
            )

    return MetaInsightCandidate(
        extending_strategy=extending_strategy,
        extending_dimension=extending_dimension,
        pattern_type=pattern_type,
        breakdown=ref_scope.breakdown if extending_strategy != "breakdown" else "(varies)",
        measure=ref_scope.measure    if extending_strategy != "measure"    else "(varies)",
        base_subspace=base_subspace,
        commonness_sets=commonness_sets,
        exceptions=exceptions,
        hdp_size=n,
        hdp_member_subspaces=[ds.subspace for ds in hdp_scopes],
        low_temporal_support=low_support,
        support_note=support_note,
    )


# =============================================================================
# MODULE D: SCORER
# =============================================================================

def compute_conciseness(candidate: MetaInsightCandidate, config: ViewConfig) -> float:
    """
    Entropy-based conciseness score (paper equations 13-16).

    S = -(sum(alpha_i * log2(alpha_i)) + r * sum(beta_j * log2(beta_j)))

    Where:
      alpha_i = proportion of each commonness set
      beta_j  = proportion of each exception category
      r       = 1.0  (balance between commonness and exception entropy)
      k       = 3    (exception categories: HIGHLIGHT_CHANGE, TYPE_CHANGE, NO_PATTERN)
      gamma   = 0.1  (actionability penalty when there are no exceptions)

    Conciseness = 1 - (S + gamma * I(no_exceptions)) / S*

    S* (upper bound, Lemma 4.1) for tau=0.5, r=1.0, k=3:
      threshold = (1 - tau) * e / tau^(1/r) = 0.5 * e / 0.5 = e ~ 2.718
      k=3 >= e, so: S* = -tau*log2(tau) - r*(1-tau)*log2((1-tau)/k) ~ 1.792
    """
    n     = candidate.hdp_size
    tau   = config.tau
    r     = 1.0
    k     = 3
    gamma = 0.5

    # Commonness proportions (alpha)
    alphas = [cs["proportion"] for cs in candidate.commonness_sets]

    # Exception category proportions (beta)
    exc_cats: dict = {}
    for exc in candidate.exceptions:
        exc_cats[exc["category"]] = exc_cats.get(exc["category"], 0) + 1
    betas = [count / n for count in exc_cats.values()]

    # Entropy S
    s = 0.0
    for a in alphas:
        if a > 0:
            s -= a * math.log2(a)
    for b in betas:
        if b > 0:
            s -= r * b * math.log2(b)

    # Actionability regularisation: penalise when there are no exceptions
    has_exceptions = len(candidate.exceptions) > 0
    s_reg = s + gamma * (0.0 if has_exceptions else 1.0)

    # S* upper bound
    tau_r     = tau ** (1.0 / r)
    threshold = (1 - tau) * math.e / tau_r

    if k < threshold:
        s_star = (
            -math.log2(tau)
            + r * (k * tau_r / math.e) * math.log2(math.e / (k * tau_r))
        )
    else:
        s_star = (
            -tau * math.log2(tau)
            - r * (1 - tau) * math.log2((1 - tau) / k)
        )

    return max(0.0, 1.0 - s_reg / s_star) if s_star > 0 else 1.0


def compute_impact(
    candidate: MetaInsightCandidate,
    impact_calc: ImpactCalculator,
    config: ViewConfig,
) -> tuple:
    """
    Impact = sum of subspace-level impacts across HDP members (paper eq. 17).
    For measure/breakdown-extending, all members share one subspace.
    Selects the impact measure that yields the highest value.
    Returns (impact_value, impact_measure_name).
    """
    best_impact  = 0.0
    best_measure = config.impact_measures[0]

    for impact_m in config.impact_measures:
        if candidate.extending_strategy == "subspace":
            # Sum across all member subspaces, capped at 1.0
            total = min(
                1.0,
                sum(
                    impact_calc.get(s).get(impact_m, 0.0)
                    for s in candidate.hdp_member_subspaces
                ),
            )
        else:
            total = impact_calc.get(candidate.base_subspace).get(impact_m, 0.0)

        if total > best_impact:
            best_impact  = total
            best_measure = impact_m

    return best_impact, best_measure


def score_candidate(
    candidate: MetaInsightCandidate,
    impact_calc: ImpactCalculator,
    config: ViewConfig,
) -> MetaInsightCandidate:
    """Compute and attach conciseness, impact, and combined score. Returns candidate."""
    candidate.conciseness = compute_conciseness(candidate, config)
    candidate.impact, candidate.impact_measure_used = compute_impact(
        candidate, impact_calc, config
    )
    candidate.score = candidate.conciseness * candidate.impact
    return candidate


# =============================================================================
# MODULE E: ENGINE ORCHESTRATOR & OUTPUT
# =============================================================================

def run_engine(config: ViewConfig, time_budget_seconds: int = 600) -> tuple:
    """
    Main MetaInsight mining loop. Returns (candidates, diagnostics).

    Flow:
      1. Load view parquet
      2. Enumerate subspaces (depth 0-2)
      3. Build impact-ordered priority queue; prune low-impact subspaces
      4. For each subspace (high-impact first):
           a. Generate data scopes (breakdown x measure)
           b. Detect Outstanding #1 pattern on each scope
           c. On pattern hit, extend into HDPs via subspace/measure/breakdown strategies
           d. Evaluate and score each HDP
      5. Sort all candidates by score descending
    """
    print("=" * 70)
    print("PHASE 2: MetaInsight Engine")
    print("=" * 70)
    print(f"Loading {config.parquet_path} ...")
    df = pd.read_parquet(config.parquet_path)
    print(f"  {len(df):,} rows x {len(df.columns)} cols")

    query_cache   = QueryCache()
    pattern_cache = PatternCache()
    impact_calc   = ImpactCalculator(df, config.impact_measures)
    candidates: list = []

    # Step 1: subspace enumeration
    print("\nGenerating subspaces ...")
    subspaces = generate_subspaces(config, df)
    d0 = 1
    d1 = sum(1 for s in subspaces if s.depth == 1)
    d2 = sum(1 for s in subspaces if s.depth == 2)
    print(f"  depth-0: {d0}  depth-1: {d1}  depth-2: {d2}  total: {len(subspaces):,}")

    # Step 2: priority queue
    print("Building priority queue ...")
    queue = build_priority_queue(subspaces, impact_calc, config.min_impact)
    print(f"  {len(queue):,} subspaces retained after impact pruning (min={config.min_impact})")

    # Step 3: mining loop
    pattern_type = "OUTSTANDING_1"
    start_time        = time.time()
    scopes_evaluated  = 0
    patterns_found    = 0
    hdps_evaluated    = 0
    metainsights_found = 0

    print(f"\nMining (budget: {time_budget_seconds}s) ...")

    while queue and (time.time() - start_time) < time_budget_seconds:
        neg_impact, _, subspace = heapq.heappop(queue)
        data_scopes = generate_data_scopes(subspace, config)

        for ds in data_scopes:
            # Check budget inside the inner loop so we don't overshoot on large subspaces
            if (time.time() - start_time) >= time_budget_seconds:
                break
            scopes_evaluated += 1

            pattern = detect_pattern(df, ds, pattern_type, query_cache, config)
            pattern_cache.put(ds, pattern_type, pattern)

            if pattern.pattern_type == pattern_type:
                patterns_found += 1

                # Generate all extending strategies for this data scope
                extensions = []
                extensions.extend(extend_subspace(ds, df, config))
                extensions.extend(extend_measure(ds, config))
                extensions.extend(extend_breakdown(ds, config))

                for ext_strategy, ext_dim, hdp_scopes in extensions:
                    hdps_evaluated += 1
                    # Pre-populate query cache for all HDP members in one shot
                    # (augmented-query optimisation; measure/breakdown HDPs share
                    # one subspace so they're already cached from scope detection)
                    if ext_strategy == "subspace":
                        query_cache.prefetch_subspace_hdp(df, hdp_scopes, ext_dim, config)
                    candidate = evaluate_hdp(
                        hdp_scopes, pattern_type,
                        ext_strategy, ext_dim,
                        df, config, query_cache, pattern_cache,
                    )
                    if candidate is not None:
                        score_candidate(candidate, impact_calc, config)
                        if candidate.score > 0:
                            candidates.append(candidate)
                            metainsights_found += 1

            if scopes_evaluated % 5000 == 0:
                elapsed = time.time() - start_time
                print(f"  {scopes_evaluated:,} scopes | {patterns_found:,} patterns | "
                      f"{metainsights_found:,} MetaInsights | {elapsed:.1f}s elapsed")

    elapsed = time.time() - start_time
    candidates.sort(key=lambda c: c.score, reverse=True)

    print(f"\nMining complete in {elapsed:.1f}s")
    print(f"  Scopes evaluated:      {scopes_evaluated:,}")
    print(f"  Patterns found:        {patterns_found:,}")
    print(f"  HDPs evaluated:        {hdps_evaluated:,}")
    print(f"  MetaInsights found:    {metainsights_found:,}")
    print(f"  Query cache hit rate:  {query_cache.hit_rate:.1%}")
    print(f"  Pattern cache rate:    {pattern_cache.hit_rate:.1%}")
    if candidates:
        print(f"  Top score:             {candidates[0].score:.4f}")

    # Verify S* value for default params (validation checklist item)
    tau, r, k = config.tau, 1.0, 3
    tau_r     = tau ** (1.0 / r)
    threshold = (1 - tau) * math.e / tau_r
    s_star    = (
        -tau * math.log2(tau) - r * (1 - tau) * math.log2((1 - tau) / k)
        if k >= threshold else
        -math.log2(tau) + r * (k * tau_r / math.e) * math.log2(math.e / (k * tau_r))
    )
    print(f"  S* (tau={tau}, r={r}, k={k}): {s_star:.4f}  (expected ~1.792)")

    diagnostics = {
        "elapsed":          elapsed,
        "scopes_evaluated": scopes_evaluated,
        "patterns_found":   patterns_found,
        "hdps_evaluated":   hdps_evaluated,
        "query_cache":      query_cache,
        "pattern_cache":    pattern_cache,
    }
    return candidates, diagnostics


# The ranking stage keeps only this many candidates by score before it runs the
# greedy selector (phase5_ranking.prefilter_candidates). It lives here because
# the mining stage now bounds its own candidate store to the same number: at
# this K the bound is LOSSLESS, since the ranker was never going to look below
# it. One constant, so the two cannot drift apart and quietly start discarding
# candidates the ranker would have read.
RANKING_PREFILTER_CAP = 5000

# WP-D2c A3. Measures that are a SIGNED difference between two money bases:
# negative means unspent, positive means spent beyond. They need their own
# EVENNESS wording, because "evenly distributed" reads as a compliment on a
# measure whose whole magnitude is a shortfall. Named here, next to the
# configs, so the ranker's template and the report's framing rule cannot drift
# apart on which measures they mean.
SIGNED_MONEY_MEASURES = frozenset({"overspend_vs_plan", "overspend_vs_sanction"})


class TopKStore:
    """The mining loop's candidate store: the best K by score, deduplicated.

    WP-D2c T3. The store was a plain list that grew for as long as the queue
    ran -- 14,172 candidates and climbing when view1's depth-2 run was stopped,
    against a projection of ~800,000. Two things then break at once: the list
    itself, and the ranker behind it, which reads only the top 5,000 by score
    and never looks lower.

    So the bound is set AT the ranker's own prefilter (RANKING_PREFILTER_CAP)
    and at that value it is LOSSLESS: every candidate this store drops is one
    `prefilter_candidates` would have dropped a step later, so the ranked
    top-15 is provably the same list. Lower values are allowed and are NOT
    lossless -- raw-score top ranks cluster near-twins (calibration session 1),
    and the greedy ranker needs breadth below them to find diverse candidates.

    Eviction is by (score, canonical_key), so which candidate goes when scores
    tie is a property of the findings and not of the order they arrived in.
    Deduplication is by `dedup_key`: one loop can keep a set of every HDP it
    has evaluated, but several sharded loops each keep their own, and the same
    HDP reached from two shards must still produce one candidate.
    """

    def __init__(self, k: int = RANKING_PREFILTER_CAP):
        self.k = k
        self._by_key: dict = {}
        self._heap: list = []
        self.dropped = 0
        self.duplicates = 0

    def add(self, candidate) -> None:
        # a candidate mined outside run_engine carries no HDP key; its own
        # content is then its identity, which is the same test one step later
        key = (candidate.dedup_key if candidate.dedup_key is not None
               else candidate.canonical_key())
        if key in self._by_key:
            self.duplicates += 1
            return
        entry = (candidate.score, candidate.canonical_key(), key)
        self._by_key[key] = candidate
        heapq.heappush(self._heap, entry)
        if self.k is not None and len(self._heap) > self.k:
            _, _, evicted = heapq.heappop(self._heap)
            self._by_key.pop(evicted, None)
            self.dropped += 1

    def items(self) -> list:
        """Everything held, in canonical order."""
        return canonical_sort(list(self._by_key.values()))

    def __len__(self) -> int:
        return len(self._by_key)


def canonical_sort(candidates: list) -> list:
    """Score-descending, ties broken by content. See canonical_key.

    `sort` on score alone is stable, which means the output order carries the
    order the candidates were mined in -- and that is exactly what parallel
    mining, cache eviction and a re-ordered parquet are allowed to change.
    Ordering ties by content makes the candidate file a function of the
    findings and nothing else.
    """
    return sorted(candidates, key=lambda c: (-c.score, c.canonical_key()))


def candidates_content_hash(candidates: list) -> str:
    """SHA-256 over the canonical keys and scores, order-independent."""
    import hashlib
    h = hashlib.sha256()
    for c in canonical_sort(candidates):
        h.update(f"{c.score:.9f}|{c.canonical_key()}\n".encode("utf-8"))
    return h.hexdigest()


def save_candidates(candidates: list, output_path: str):
    """Serialise all MetaInsight candidates to JSON, in canonical order."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([c.to_dict() for c in canonical_sort(candidates)], f,
                  indent=2, default=str)
    print(f"Saved {len(candidates):,} candidates -> {output_path}")


def load_candidates(path: str) -> list:
    """Load candidates from JSON and reconstruct MetaInsightCandidate objects."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    candidates = []
    for d in data:
        base_subspace = Subspace(frozenset(tuple(f) for f in d["base_subspace"]))
        c = MetaInsightCandidate(
            extending_strategy=d["extending_strategy"],
            extending_dimension=d["extending_dimension"],
            pattern_type=d["pattern_type"],
            breakdown=d["breakdown"],
            measure=d["measure"],
            base_subspace=base_subspace,
            commonness_sets=d["commonness_sets"],
            exceptions=d["exceptions"],
            hdp_size=d["hdp_size"],
            conciseness=d["conciseness"],
            impact=d["impact"],
            score=d["score"],
            impact_measure_used=d["impact_measure_used"],
            low_temporal_support=d.get("low_temporal_support", False),
            support_note=d.get("support_note", ""),
            merged_twins=list(d.get("merged_twins", [])),
        )
        candidates.append(c)
    return candidates


def save_diagnostics(candidates: list, diagnostics: dict, output_path: str):
    """Write a human-readable diagnostics report."""
    qc = diagnostics["query_cache"]
    pc = diagnostics["pattern_cache"]

    lines = [
        "=" * 70,
        "METAINSIGHT ENGINE DIAGNOSTICS",
        "=" * 70,
        f"Time elapsed:     {diagnostics['elapsed']:.1f}s",
        f"Scopes evaluated: {diagnostics['scopes_evaluated']:,}",
        f"Patterns found:   {diagnostics['patterns_found']:,}",
        f"HDPs evaluated:   {diagnostics['hdps_evaluated']:,}",
        f"MetaInsights:     {len(candidates):,}",
        f"Query cache:      {qc.hits:,} hits / {qc.misses:,} misses ({qc.hit_rate:.1%})",
        f"Pattern cache:    {pc.hits:,} hits / {pc.misses:,} misses ({pc.hit_rate:.1%})",
        "",
        "--- Score Distribution ---",
    ]

    if candidates:
        lines += [
            f"  Max:    {candidates[0].score:.4f}",
            f"  Median: {candidates[len(candidates) // 2].score:.4f}",
            f"  Min:    {candidates[-1].score:.4f}",
            f"  Total above 0.1: {sum(1 for c in candidates if c.score >= 0.1)}",
        ]
    else:
        lines.append("  (no candidates)")

    lines += ["", "--- Top 20 MetaInsights ---"]

    for i, c in enumerate(candidates[:20]):
        lines.append(f"\n  #{i + 1}  score={c.score:.4f}  "
                     f"(conciseness={c.conciseness:.4f}, impact={c.impact:.4f} "
                     f"via {c.impact_measure_used})")
        lines.append(f"    Strategy:    {c.extending_strategy} on '{c.extending_dimension}'")
        lines.append(f"    Pattern:     {c.pattern_type}")
        lines.append(f"    Breakdown:   {c.breakdown}   Measure: {c.measure}")
        lines.append(f"    Base scope:  {c.base_subspace}")
        lines.append(f"    HDP size:    {c.hdp_size}")
        for cs in c.commonness_sets:
            members_str = ", ".join(cs["members"][:8])
            if len(cs["members"]) > 8:
                members_str += f" ... (+{len(cs['members']) - 8})"
            lines.append(f"    Commonness:  {cs['highlight']}  "
                         f"({cs['count']}/{c.hdp_size} = {cs['proportion']:.0%})")
            lines.append(f"      Members:   {members_str}")
        if c.exceptions:
            lines.append(f"    Exceptions ({len(c.exceptions)}):")
            for exc in c.exceptions[:5]:
                lines.append(f"      - {exc['member_label']}: {exc['category']} "
                             f"(highlight={exc['highlight']})")
            if len(c.exceptions) > 5:
                lines.append(f"      ... and {len(c.exceptions) - 5} more")
        else:
            lines.append("    Exceptions:  none (all commonness)")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Diagnostics saved -> {output_path}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    candidates, diagnostics = run_engine(VIEW1_CONFIG, time_budget_seconds=600)

    save_candidates(
        candidates,
        os.path.join(BASE_DIR, "metainsights", "view1_candidates.json"),
    )
    save_diagnostics(
        candidates,
        diagnostics,
        os.path.join(BASE_DIR, "reports", "engine_diagnostics.txt"),
    )

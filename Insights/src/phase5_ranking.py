# =============================================================================
# Phase 5: Intra-View Ranking & Presentation (Layers 3 + 3P)
# =============================================================================
# Takes raw MetaInsight candidates from each view (Phase 4b output) and
# produces a ranked top-k list per view using the paper's greedy second-order
# approximation of TotalUse maximisation (Section 4.3).
#
# Selects candidates with high individual scores and low inter-MetaInsight
# redundancy. Also generates Layer 2P (raw explorer) and Layer 3P (ranked
# dashboard) presentation reports.
#
# Inputs:
#   metainsights/view{1-9}_candidates.json
#
# Outputs:
#   metainsights/view{1-9}_ranked.json
#   reports/layer2p_raw_explorer.txt
#   reports/layer3p_ranked_dashboard.txt
#
# Run from project root:
#   python src/phase5_ranking.py
# =============================================================================

import os
import sys
import ast
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase2_engine import (
    MetaInsightCandidate, Subspace, load_candidates,
    RANKING_PREFILTER_CAP, SIGNED_MONEY_MEASURES,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# All pattern types (for zero-count reporting)
ALL_PATTERN_TYPES = [
    "OUTSTANDING_1", "OUTSTANDING_LAST", "TOP_TWO", "LAST_TWO",
    "EVENNESS", "ATTRIBUTION",
    "TREND", "OUTLIER", "SEASONALITY", "CHANGE_POINT", "UNIMODALITY",
]


# =============================================================================
# PART 2: INTER-METAINSIGHT OVERLAP (Paper Section 4.3 + Appendix 9.4)
# =============================================================================

def _subspace_overlap_coefficient(
    mi1: MetaInsightCandidate, mi2: MetaInsightCandidate
) -> float:
    """Overlap coefficient of base subspace filters."""
    filters1 = set(mi1.base_subspace.filters)
    filters2 = set(mi2.base_subspace.filters)

    if len(filters1) == 0 and len(filters2) == 0:
        return 1.0   # both are {*}
    if len(filters1) == 0 or len(filters2) == 0:
        return 0.0   # one is {*}, other has filters

    intersection = len(filters1 & filters2)
    return intersection / min(len(filters1), len(filters2))


def _subspace_overlap(mi1: MetaInsightCandidate, mi2: MetaInsightCandidate) -> float:
    """Overlap for subspace-extending MetaInsights."""
    w1, w2, w3, w4 = 0.4, 0.3, 0.15, 0.15
    sub = _subspace_overlap_coefficient(mi1, mi2)
    ext = 1.0 if mi1.extending_dimension == mi2.extending_dimension else 0.0
    msr = 1.0 if mi1.measure == mi2.measure else 0.0
    bkd = 1.0 if mi1.breakdown == mi2.breakdown else 0.0
    return w1 * sub + w2 * ext + w3 * msr + w4 * bkd


def _measure_overlap(mi1: MetaInsightCandidate, mi2: MetaInsightCandidate) -> float:
    """Overlap for measure-extending MetaInsights."""
    w1, w2 = 0.6, 0.4
    sub = _subspace_overlap_coefficient(mi1, mi2)
    bkd = 1.0 if mi1.breakdown == mi2.breakdown else 0.0
    return w1 * sub + w2 * bkd


def _breakdown_overlap(mi1: MetaInsightCandidate, mi2: MetaInsightCandidate) -> float:
    """Overlap for breakdown-extending MetaInsights."""
    w1, w2 = 0.6, 0.4
    sub = _subspace_overlap_coefficient(mi1, mi2)
    msr = 1.0 if mi1.measure == mi2.measure else 0.0
    return w1 * sub + w2 * msr


def _shares_any_content(
    mi1: MetaInsightCandidate, mi2: MetaInsightCandidate
) -> bool:
    """Do these two candidates have any analytical content in common at all?

    Sharing a SUBSPACE means both are restricted to a slice and those slices
    intersect. Two candidates that both describe the whole view are not sharing
    a subspace, they are simply both unfiltered — and treating that as shared
    content would make this test pass for almost every pair at depth 0, which
    is where most high-scoring candidates live, leaving the term as loose as it
    was before. `_subspace_overlap_coefficient` deliberately returns 1.0 for two
    empty subspaces because it is measuring similarity, not sharing; that is the
    right answer for the weighted formula and the wrong one for this gate.
    """
    if mi1.measure == mi2.measure or mi1.breakdown == mi2.breakdown:
        return True
    f1 = set(mi1.base_subspace.filters)
    f2 = set(mi2.base_subspace.filters)
    return bool(f1 and f2 and (f1 & f2))


def compute_overlap_ratio(
    mi1: MetaInsightCandidate, mi2: MetaInsightCandidate
) -> float:
    """
    Overlap ratio between two MetaInsights in [0, 1].

    ITERATION 3 — the eligibility test is tightened by ONE added requirement:
    two candidates overlap only if, on top of sharing the extending strategy and
    the pattern type as before, they also share at least one of {measure,
    breakdown, a non-trivial subspace}.

    Why. The gate used to be strategy + pattern type alone, and the formulas
    below then paid out 0.30 (subspace strategy) or 0.40 (measure and breakdown
    strategies) for a bare extending-dimension match. That is enough to remove a
    real finding on its own: in iteration 2 the eKYC backlog scored 0.5474
    against view2's rank-15 line of 0.5032 — it earned its place — and was
    dropped by a single 0.3832 overlap with a candidate that shared nothing with
    it but a pattern type and the dimension it was extended along, over a
    different measure, a different breakdown and a disjoint subspace. Two
    findings that share only the axis they were sliced along are not saying the
    same thing to a reader, so they are no longer charged for it.

    Formula BEFORE:
        eligible  <- strategy match AND pattern-type match
        subspace  : 0.40*sub + 0.30*ext + 0.15*msr + 0.15*bkd
        measure   : 0.60*sub + 0.40*bkd
        breakdown : 0.60*sub + 0.40*msr
    Formula AFTER:
        eligible  <- the BEFORE test, AND _shares_any_content(mi1, mi2)
        the three weighted formulas are unchanged.

    WHAT THIS DELIBERATELY DOES NOT DO, because a first pass at it did and the
    result was measurably worse: it does not require the extending dimensions to
    MATCH. Two candidates with the same pattern type, the same measure, the same
    breakdown and the same subspace, differing only in which dimension the HDP
    was extended along, are about as redundant as two candidates can be — they
    are one finding written three ways. Gating on an extending-dimension match
    scores exactly those pairs at ZERO overlap, and the top-15s fill with them:
    with that gate in place view4's ranked list spent six of its fifteen slots
    on two findings repeated across three extending dimensions each, and three
    patterns that iteration 2 had recovered were pushed out of the list
    altogether. The requirement that belongs here is shared CONTENT, which is
    what removed P4's phantom overlap; an extending-dimension gate addresses
    nothing and costs real findings.

    Only the gate moved. Nothing that overlapped substantively before overlaps
    less now, and detection is untouched — this is a ranking term.
    """
    if mi1.extending_strategy != mi2.extending_strategy:
        return 0.0
    if mi1.pattern_type != mi2.pattern_type:
        return 0.0
    if not _shares_any_content(mi1, mi2):
        return 0.0

    strategy = mi1.extending_strategy
    if strategy == "subspace":
        return _subspace_overlap(mi1, mi2)
    if strategy == "measure":
        return _measure_overlap(mi1, mi2)
    if strategy == "breakdown":
        return _breakdown_overlap(mi1, mi2)
    return 0.0


def compute_pairwise_overlap(
    mi1: MetaInsightCandidate, mi2: MetaInsightCandidate
) -> float:
    """
    |I1 ∩ I2| = min(|I1|, |I2|) × r(I1, I2)
    Where |I| = score, r = overlap ratio.  (Paper Equation 20)
    """
    r = compute_overlap_ratio(mi1, mi2)
    return min(mi1.score, mi2.score) * r


# =============================================================================
# PART 3: GREEDY RANKING (Paper Section 4.3)
# =============================================================================

def compute_total_use_approx(selected: list) -> float:
    """
    TotalUse_approx = sum(|Ii|) - sum(|Ii ∩ Ij|) for all pairs i < j
    (Paper Equation 22)
    """
    total = sum(mi.score for mi in selected)
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            total -= compute_pairwise_overlap(selected[i], selected[j])
    return total


def prefilter_candidates(candidates: list, max_candidates: int = RANKING_PREFILTER_CAP) -> list:
    """Keep only top-N by score. Low scorers have near-zero chance of selection.

    The mining stage now bounds its own store at this same number
    (phase2_engine.RANKING_PREFILTER_CAP), which is why that bound is lossless:
    everything the store drops, this would have dropped.
    """
    if len(candidates) <= max_candidates:
        return candidates
    return sorted(candidates, key=lambda c: c.score, reverse=True)[:max_candidates]


# =============================================================================
# PART 2b: TWIN MERGE (WP-D2c A2)
# =============================================================================
# Calibration session 1, ruling 2. OUTSTANDING_1 and ATTRIBUTION are different
# tests -- one is a z-score against the rest of the distribution, the other a
# share of the total -- and on a concentrated distribution both fire on the
# same value. The reader then meets the same sentence twice:
#
#   "... New/Fresh has the highest trainees_total among work_type_label values"
#   "... New/Fresh accounts for the majority of trainees_total among ..."
#
# Four such pairs sat in the 33 findings the operator labelled, and in each
# case the second one was labelled a twin of the first. They are ONE finding
# and they are merged here, before ranking: the higher-scored survives, carries
# the other's pattern type in `merged_twins`, and the loser is gone -- so it
# cannot take a second slot in the top-15 and cannot be charged an overlap
# penalty against its own twin either.
#
# The merge is deliberately narrow. It requires the same subspace family (same
# base subspace, same extending strategy and dimension), the same breakdown and
# measure, the same highlight, and the same member set -- the four things that
# make two candidates the same sentence. Near-twins that differ in measure or
# breakdown (view1 ranks 1/2, view2 ranks 1/15) tell one story to a reader but
# are not identical findings; collapsing those is a presentation decision, and
# the overlap term already prices them. NO overlap weight was changed by this
# WP: the ranking math is untouched, and this is a deduplication in front of it.

_TWIN_TYPES = frozenset({"OUTSTANDING_1", "ATTRIBUTION"})


def _twin_key(mi: MetaInsightCandidate):
    """What makes two candidates the same sentence. See above."""
    commonness = tuple(sorted(
        (cs["highlight"], tuple(sorted(str(m) for m in cs["members"])))
        for cs in mi.commonness_sets
    ))
    return (
        frozenset(mi.base_subspace.filters),
        mi.extending_strategy,
        mi.extending_dimension,
        mi.breakdown,
        mi.measure,
        commonness,
    )


def merge_twin_candidates(candidates: list) -> tuple:
    """Collapse OUTSTANDING_1/ATTRIBUTION twins. Returns (kept, n_merged)."""
    best: dict = {}
    passthrough = []
    for mi in candidates:
        if mi.pattern_type not in _TWIN_TYPES:
            passthrough.append(mi)
            continue
        key = _twin_key(mi)
        incumbent = best.get(key)
        if incumbent is None:
            best[key] = mi
            continue
        winner, loser = (
            (incumbent, mi) if incumbent.score >= mi.score else (mi, incumbent)
        )
        winner.merged_twins = sorted(set(
            list(winner.merged_twins) + list(loser.merged_twins) + [loser.pattern_type]
        ))
        best[key] = winner
    merged = len(candidates) - len(passthrough) - len(best)
    return passthrough + list(best.values()), merged


def rank_metainsights(candidates: list, k: int = 15) -> list:
    """
    Greedy algorithm to select top-k MetaInsights maximising TotalUse_approx.

    1. Start with the highest-scoring candidate.
    2. At each step, add the candidate that gives the highest marginal gain
       (score minus overlap penalties with already-selected candidates).
    3. Stop when k candidates selected or no candidate improves TotalUse.
    """
    if not candidates:
        return []

    sorted_cands = sorted(candidates, key=lambda c: c.score, reverse=True)
    selected = [sorted_cands[0]]
    remaining = set(range(1, len(sorted_cands)))

    for _ in range(1, k):
        if not remaining:
            break

        best_marginal = -float("inf")
        best_idx = None

        for idx in remaining:
            candidate = sorted_cands[idx]
            marginal = candidate.score
            for sel in selected:
                marginal -= compute_pairwise_overlap(candidate, sel)
            if marginal > best_marginal:
                best_marginal = marginal
                best_idx = idx

        if best_marginal <= 0:
            break

        selected.append(sorted_cands[best_idx])
        remaining.remove(best_idx)

    return selected


def merge_prefilter_rank(
    candidates: list,
    k: int = 15,
    max_candidates: int = RANKING_PREFILTER_CAP,
) -> tuple:
    """THE ranking path. Twin merge (A2) -> pre-filter -> greedy rank.

    WP-D3b §4.3. This function exists because the three steps were previously
    assembled TWICE, in two files, and the two assemblies disagreed. This file's
    `__main__` -- the executive-report path -- merged twins first. The gamma
    editions' path in `phase5c_gamma_reports.py` called `prefilter` and `rank`
    directly and so never merged at all, and the operator comparing the two
    suites was reading 2-3 pairs of near-duplicate view1 findings per edition
    that the calibrated pipeline removes. Neither path was wrong about its own
    three lines; there simply was no shared path for A2 to live in. There is now,
    and a third caller cannot repeat the omission without deliberately
    reassembling the steps by hand.

    ORDER IS LOAD-BEARING, and it is the reason this is a function rather than a
    call moved into `rank_metainsights`. A2 runs BEFORE the pre-filter so that a
    twin cannot occupy one of the `max_candidates` slots its own survivor already
    holds -- merging after the cut would let a loser displace a real finding and
    then be discarded, which costs the top-k a slot for nothing.

    Callers that rescore first (the gamma path) merge their RESCORED candidates,
    not the raw ones, which is deliberate: `merge_twin_candidates` keeps the
    higher-scored twin, and at a given gamma "higher-scored" has to mean higher
    at that gamma. The gamma penalty falls on findings with no exceptions, so
    which of an OUTSTANDING_1/ATTRIBUTION pair survives is exactly the kind of
    actionability trade-off the knob is there to express.

    Returns (ranked, n_merged, merged) -- the top-k, how many twins were
    collapsed, and the post-merge candidate pool, which the layer-2P/3P reports
    need because it is the pool the ranking actually saw.
    """
    merged, n_merged = merge_twin_candidates(candidates)
    filtered = prefilter_candidates(merged, max_candidates=max_candidates)
    return rank_metainsights(filtered, k=k), n_merged, merged


# =============================================================================
# PART 4: NATURAL LANGUAGE SUMMARIES
# =============================================================================

def _pattern_type_to_text(
    pattern_type: str, highlight: str, breakdown: str, measure: str
) -> str:
    """Convert pattern type + highlight string into readable text."""
    try:
        hl = ast.literal_eval(highlight) if highlight else ()
    except (ValueError, SyntaxError):
        hl = (highlight,) if highlight else ()

    templates = {
        "OUTSTANDING_1":    lambda: f"{hl[0]} has the highest {measure} among {breakdown} values",
        "OUTSTANDING_LAST": lambda: f"{hl[0]} has the lowest {measure} among {breakdown} values",
        "TOP_TWO":          lambda: f"{hl[0]} and {hl[1]} lead in {measure} among {breakdown} values",
        "LAST_TWO":         lambda: f"{hl[0]} and {hl[1]} are lowest in {measure} among {breakdown} values",
        # WP-D2c A3. A signed money measure gets its own wording. "Evenly
        # distributed" is a neutral sentence about a shape, and on
        # overspend_vs_plan -- Rs 51.96 crore of it, all negative -- the reader
        # is being told that a shortfall is SYSTEMIC, which is the opposite of
        # neutral. The operator's instruction was to make the text pop: lead
        # with the fact that there is no concentration to chase, because that
        # is what changes what an officer does about it.
        "EVENNESS":         lambda: (
            f"{measure} is spread evenly across {breakdown} values -- it belongs "
            f"to all of them and no single {breakdown} accounts for it"
            if measure in SIGNED_MONEY_MEASURES else
            f"{measure} is evenly distributed across {breakdown} values"
        ),
        "ATTRIBUTION":      lambda: f"{hl[0]} accounts for the majority of {measure} among {breakdown} values",
        "TREND":            lambda: f"{measure} is {hl[0].lower()} over {breakdown}",
        "OUTLIER":          lambda: (
            f"{measure} has an outlier at {hl[0][0]} ({hl[0][1].lower()}) in {breakdown}"
            if len(hl) == 1
            else f"{measure} has outliers at {', '.join(h[0] for h in hl)} in {breakdown}"
        ),
        "SEASONALITY":      lambda: f"{measure} shows seasonal pattern ({hl[0]}) over {breakdown}",
        "CHANGE_POINT":     lambda: f"{measure} has a significant shift at {hl[0]} in {breakdown}",
        "UNIMODALITY":      lambda: f"{measure} forms a {hl[0].lower()} at {hl[1]} over {breakdown}",
    }

    try:
        return templates.get(pattern_type, lambda: f"{pattern_type} pattern on {measure}")()
    except (IndexError, TypeError):
        return f"{pattern_type} pattern on {measure} across {breakdown}"


def generate_nl_summary(candidate: MetaInsightCandidate) -> str:
    """
    Generate a natural language summary.
    Template: "Across most [dim], [commonness]. Exception: [entity] ([detail])."
    """
    if not candidate.commonness_sets:
        return "(no commonness)"

    cs = candidate.commonness_sets[0]
    pattern_desc = _pattern_type_to_text(
        cs["pattern_type"], cs["highlight"],
        candidate.breakdown, candidate.measure,
    )

    ext_dim    = candidate.extending_dimension
    proportion = cs["proportion"]
    count      = cs["count"]
    hdp_size   = candidate.hdp_size

    if proportion >= 1.0:
        prefix = f"Across all {ext_dim} values"
    elif proportion >= 0.9:
        prefix = f"Across nearly all {ext_dim} values ({count}/{hdp_size})"
    else:
        prefix = f"Across most {ext_dim} values ({count}/{hdp_size})"

    summary = f"{prefix}, {pattern_desc}"

    if candidate.exceptions:
        n_exc = len(candidate.exceptions)
        # WP-D2c A3, second half. On an EVENNESS finding the exceptions are
        # about the SHAPE of the distribution and nothing else. Written as
        # "Exception: Banking Facilities (no clear pattern)" beside a systemic
        # shortfall, they read as "Banking Facilities is fine" -- the operator
        # flagged exactly that sentence. The excepted member is one where the
        # measure is NOT evenly spread; whether it is high or low is not in
        # this finding.
        even = cs["pattern_type"] == "EVENNESS"
        exc_descs = []
        for e in candidate.exceptions[:3]:
            if e["category"] == "HIGHLIGHT_CHANGE":
                exc_text = _pattern_type_to_text(
                    e["pattern_type"], e["highlight"],
                    candidate.breakdown, candidate.measure,
                )
                exc_descs.append(f"{e['member_label']} ({exc_text})")
            elif e["category"] == "TYPE_CHANGE":
                exc_descs.append(
                    f"{e['member_label']} (a different shape of distribution)"
                    if even else f"{e['member_label']} (different pattern)"
                )
            else:
                exc_descs.append(
                    f"{e['member_label']} (not evenly spread)"
                    if even else f"{e['member_label']} (no clear pattern)"
                )

        label = "Uneven only in" if even else "Exception"
        plural = "Uneven only in" if even else "Exceptions"
        if n_exc <= 3:
            summary += f". {label}: {'; '.join(exc_descs)}"
        else:
            summary += f". {plural}: {'; '.join(exc_descs)} and {n_exc - 3} others"
        if even:
            summary += (
                " -- this is about how the total is spread, not about how much "
                "any one of them spends"
            )

    return summary


# =============================================================================
# PART 5: LAYER 2P — RAW METAINSIGHT EXPLORER
# =============================================================================

def generate_layer2p_report(
    all_candidates: dict,
    output_path: str,
):
    """Generate diagnostic report of all raw candidates per view."""
    lines = [
        "=" * 70,
        "LAYER 2P -- RAW METAINSIGHT EXPLORER",
        "=" * 70, "",
    ]

    for view_name, candidates in all_candidates.items():
        lines += [
            "=" * 70,
            f"VIEW: {view_name}  |  Total candidates: {len(candidates):,}",
            "=" * 70,
        ]

        if not candidates:
            lines += ["  (no candidates)", ""]
            continue

        scores = [c.score for c in candidates]
        lines += [
            "",
            "Score distribution:",
            f"  Max={max(scores):.4f}  Median={sorted(scores)[len(scores)//2]:.4f}  "
            f"Min={min(scores):.4f}  Mean={sum(scores)/len(scores):.4f}",
        ]

        type_counts: dict = {}
        type_actionable: dict = {}
        for c in candidates:
            type_counts[c.pattern_type] = type_counts.get(c.pattern_type, 0) + 1
            if c.exceptions:
                type_actionable[c.pattern_type] = type_actionable.get(c.pattern_type, 0) + 1

        lines += [
            "",
            f"  {'Pattern Type':<25} {'Total':>8} {'Actionable':>12} {'Top Score':>10}",
            f"  {'-'*57}",
        ]
        for pt in sorted(type_counts, key=lambda x: -type_counts[x]):
            top = max(c.score for c in candidates if c.pattern_type == pt)
            lines.append(
                f"  {pt:<25} {type_counts[pt]:>8,} "
                f"{type_actionable.get(pt, 0):>12,} {top:>10.4f}"
            )
        zero_types = [pt for pt in ALL_PATTERN_TYPES if pt not in type_counts]
        if zero_types:
            lines.append(f"\n  Zero candidates: {zero_types}")

        strat_counts: dict = {}
        for c in candidates:
            strat_counts[c.extending_strategy] = strat_counts.get(c.extending_strategy, 0) + 1
        lines += ["", "Extending strategies:"]
        for s, n in sorted(strat_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {s}: {n:,}")

        universal = sum(1 for c in candidates if not c.exceptions)
        lines += [
            "",
            f"Universal: {universal:,}  |  Actionable: {len(candidates)-universal:,}",
            "",
        ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Layer 2P report -> {output_path}")


# =============================================================================
# PART 6: LAYER 3P — RANKED PER-VIEW DASHBOARD
# =============================================================================

def generate_layer3p_report(
    all_ranked: dict,
    all_candidates: dict,
    output_path: str,
):
    """Generate the ranked dashboard with full detail and NL summaries."""
    lines = [
        "=" * 70,
        "LAYER 3P -- RANKED PER-VIEW DASHBOARD",
        "=" * 70, "",
    ]

    for view_name in all_ranked:
        ranked = all_ranked[view_name]
        total  = len(all_candidates[view_name])

        lines += [
            "=" * 70,
            f"VIEW: {view_name}  |  Selected {len(ranked)} from {total:,} candidates",
            "=" * 70,
        ]

        # Diversity profile
        types_repr    = sorted(set(c.pattern_type        for c in ranked))
        dims_repr     = sorted(set(c.extending_dimension  for c in ranked))
        measures_repr = sorted(set(c.measure for c in ranked if c.measure != "(varies)"))

        lines += [
            "",
            "Diversity:",
            f"  Pattern types ({len(types_repr)}): {', '.join(types_repr)}",
            f"  Extending dims ({len(dims_repr)}): {', '.join(dims_repr)}",
            f"  Measures ({len(measures_repr)}): {', '.join(measures_repr[:8])}"
            + (f" +{len(measures_repr)-8} more" if len(measures_repr) > 8 else ""),
        ]

        # TotalUse stats
        total_use  = compute_total_use_approx(ranked)
        sum_scores = sum(c.score for c in ranked)
        lines += [
            "",
            f"TotalUse: {total_use:.4f}  |  Sum of scores: {sum_scores:.4f}  "
            f"|  Redundancy penalty: {sum_scores - total_use:.4f}",
            "",
            "--- Ranked MetaInsights ---",
            "",
        ]

        for rank, c in enumerate(ranked, 1):
            lines += [
                f"  #{rank}  score={c.score:.4f}  "
                f"(conciseness={c.conciseness:.4f}, impact={c.impact:.4f})",
                f"    {c.extending_strategy} on {c.extending_dimension}  |  "
                f"{c.pattern_type}  |  breakdown={c.breakdown}  |  measure={c.measure}",
                f"    Subspace: {c.base_subspace}  |  HDP: {c.hdp_size}",
            ]

            for cs in c.commonness_sets:
                members = ", ".join(str(m) for m in cs["members"][:6])
                more = f" +{len(cs['members'])-6} more" if len(cs["members"]) > 6 else ""
                lines += [
                    f"    Commonness: [{cs['pattern_type']}] {cs['highlight']}  "
                    f"({cs['count']}/{c.hdp_size} = {cs['proportion']:.0%})",
                    f"      Members: {members}{more}",
                ]

            if c.exceptions:
                lines.append(f"    Exceptions ({len(c.exceptions)}):")
                for exc in c.exceptions[:4]:
                    lines.append(
                        f"      {str(exc['member_label']):<25} {exc['category']:<20} "
                        f"{exc['highlight'] or ''}"
                    )
                if len(c.exceptions) > 4:
                    lines.append(f"      ... +{len(c.exceptions)-4} more")

            nl = generate_nl_summary(c)
            lines += [f"    >> {nl}", ""]

        lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Layer 3P report -> {output_path}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # The three PR&DW views. The nine-view list this replaced was the last stale
    # Andhra Pradesh registry in the pipeline; deleting the six dead entries is
    # authorised by D-12 / D25 (WP-D2b), and retires
    # handoffs/WPD2_calibration/run_phase5_prdw.py, the driver that existed only
    # to work around it. Ranking behaviour is unchanged.
    views = ["view1", "view2", "view3"]
    k = 15

    all_candidates: dict = {}
    all_ranked: dict = {}

    for view_name in views:
        path = os.path.join(BASE_DIR, "metainsights", f"{view_name}_candidates.json")
        print(f"\nLoading {path} ...")
        candidates = load_candidates(path)
        print(f"  {len(candidates):,} candidates loaded")

        # The three steps live in `merge_prefilter_rank` now, so the gamma path
        # runs the same ones in the same order (WP-D3b). This path's output is
        # unchanged -- byte-identical `*_ranked.json` is the done-check.
        ranked, n_merged, candidates = merge_prefilter_rank(
            candidates, k=k, max_candidates=RANKING_PREFILTER_CAP)
        print(f"  {n_merged:,} OUTSTANDING_1/ATTRIBUTION twins merged (A2) "
              f"-> {len(candidates):,}")
        print(f"  {min(len(candidates), RANKING_PREFILTER_CAP):,} after pre-filter")
        print(f"  {len(ranked)} selected for top-{k}")

        all_candidates[view_name] = candidates
        all_ranked[view_name]     = ranked

        ranked_path = os.path.join(BASE_DIR, "metainsights", f"{view_name}_ranked.json")
        os.makedirs(os.path.dirname(ranked_path), exist_ok=True)
        with open(ranked_path, "w", encoding="utf-8") as fout:
            json.dump([c.to_dict() for c in ranked], fout, indent=2, default=str)

    generate_layer2p_report(
        all_candidates,
        os.path.join(BASE_DIR, "reports", "layer2p_raw_explorer.txt"),
    )
    generate_layer3p_report(
        all_ranked,
        all_candidates,
        os.path.join(BASE_DIR, "reports", "layer3p_ranked_dashboard.txt"),
    )

    print(f"\n{'=' * 70}")
    print("Phase 5 Summary")
    print(f"{'=' * 70}")
    for view_name in views:
        ranked = all_ranked[view_name]
        total  = len(all_candidates[view_name])
        types  = sorted(set(c.pattern_type for c in ranked))
        tu     = compute_total_use_approx(ranked)
        print(f"  {view_name}: {len(ranked)} selected from {total:,}  "
              f"| TotalUse={tu:.4f}  | types: {', '.join(types)}")

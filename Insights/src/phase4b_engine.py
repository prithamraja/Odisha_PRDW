# =============================================================================
# Phase 4b: All Four Views
# =============================================================================
# Runs the MetaInsight engine (all 11 pattern types, HDP deduplication,
# SUM/AVG aggregation) independently on all four analytical views.
#
# Engine unchanged from Phase 4a + dedup:
#   - Pandas query layer with augmented-query prefetch
#   - All 11 pattern evaluators (6 categorical, 5 temporal)
#   - HDP deduplication set (skip exact duplicate HDPs)
#   - MeasureConfig-driven SUM/AVG dispatch
#
# Outputs:
#   metainsights/view1_candidates.json
#   metainsights/view2_candidates.json
#   metainsights/view3_candidates.json
#   metainsights/view4_candidates.json
#   reports/engine_diagnostics_all_views.txt
#
# Run from project root:
#   python src/phase4b_engine.py
# =============================================================================

import os
import sys
import json
import math
import time
import heapq
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Import everything from Phase 4a (pandas query layer, all 11 evaluators,
# HDP construction, scoring, output). Phase 4a already patches phase2_engine
# with the full pattern registry and updated detect_pattern on import.
# ---------------------------------------------------------------------------
from phase4a_engine import (
    # Config
    MeasureConfig, ViewConfig, VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG, VIEW4_CONFIG,
    VIEW5_CONFIG, VIEW6_CONFIG, VIEW7_CONFIG, VIEW8_CONFIG, VIEW9_CONFIG,
    # Data structures
    Subspace, DataScope, MetaInsightCandidate,
    # Enumeration
    generate_subspaces, generate_data_scopes,
    # Priority queue
    build_priority_queue,
    # Query layer (pandas, with augmented-query prefetch)
    QueryCache, PatternCache,
    # Impact (pandas)
    ImpactCalculator,
    # Pattern detection
    detect_pattern, PATTERN_EVALUATORS, TEMPORAL_ONLY_TYPES, CATEGORICAL_ONLY_TYPES,
    # HDP construction
    extend_subspace, extend_measure, extend_breakdown, evaluate_hdp,
    # Scoring
    score_candidate,
    # Output
    save_candidates,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# RUN_ENGINE — all 11 pattern types + HDP deduplication
# =============================================================================

def run_engine(config: ViewConfig, time_budget_seconds: int = 900) -> tuple:
    """
    MetaInsight mining loop with all 11 pattern types and HDP deduplication.

    Before calling evaluate_hdp, checks whether the exact same HDP
    (same member subspaces, pattern type, breakdown, measure) was already
    evaluated. If so, skips it — the candidate would be identical.
    """
    print(f"\n{'=' * 70}")
    print(f"VIEW: {config.name}")
    print(f"{'=' * 70}")

    print(f"Loading {config.parquet_path} ...")
    df = pd.read_parquet(config.parquet_path)
    print(f"  {len(df):,} rows x {len(df.columns)} cols")

    # Pattern type partitions
    pattern_types_categorical = [pt for pt in PATTERN_EVALUATORS if pt not in TEMPORAL_ONLY_TYPES]
    pattern_types_temporal    = [pt for pt in PATTERN_EVALUATORS if pt not in CATEGORICAL_ONLY_TYPES]
    print(f"\nPattern types: {len(pattern_types_categorical)} categorical, "
          f"{len(pattern_types_temporal)} temporal  ({len(PATTERN_EVALUATORS)} total)")

    # Initialise
    query_cache    = QueryCache()
    pattern_cache  = PatternCache()
    impact_calc    = ImpactCalculator(df, config.impact_measures)
    candidates: list = []
    evaluated_hdps: set = set()   # dedup set
    hdps_skipped   = 0

    # Subspace enumeration
    print("\nGenerating subspaces ...")
    subspaces = generate_subspaces(config, df)
    d0 = 1
    d1 = sum(1 for s in subspaces if s.depth == 1)
    d2 = sum(1 for s in subspaces if s.depth == 2)
    print(f"  depth-0: {d0}  depth-1: {d1}  depth-2: {d2}  total: {len(subspaces):,}")

    # Priority queue
    print("Building priority queue ...")
    queue = build_priority_queue(subspaces, impact_calc, config.min_impact)
    print(f"  {len(queue):,} subspaces retained after impact pruning (min={config.min_impact})")

    # Mining loop
    start_time         = time.time()
    scopes_evaluated   = 0
    patterns_found     = 0
    hdps_evaluated     = 0
    metainsights_found = 0

    print(f"\nMining (budget: {time_budget_seconds}s) ...")

    while queue and (time.time() - start_time) < time_budget_seconds:
        neg_impact, _, subspace = heapq.heappop(queue)
        data_scopes = generate_data_scopes(subspace, config)

        for ds in data_scopes:
            if (time.time() - start_time) >= time_budget_seconds:
                break

            scopes_evaluated += 1
            is_temporal  = ds.breakdown in config.temporal_dimensions
            active_types = pattern_types_temporal if is_temporal else pattern_types_categorical

            for pattern_type in active_types:
                cached = pattern_cache.get(ds, pattern_type)
                if cached is not None:
                    pattern = cached
                else:
                    pattern = detect_pattern(df, ds, pattern_type, query_cache, config)
                    pattern_cache.put(ds, pattern_type, pattern)

                if pattern.pattern_type == pattern_type:
                    patterns_found += 1

                    extensions = []
                    extensions.extend(extend_subspace(ds, df, config))
                    extensions.extend(extend_measure(ds, config))
                    extensions.extend(extend_breakdown(ds, config))

                    for ext_strategy, ext_dim, hdp_scopes in extensions:
                        # --- HDP deduplication ---
                        hdp_key = (
                            frozenset(s.subspace for s in hdp_scopes),
                            pattern_type,
                            hdp_scopes[0].breakdown if ext_strategy != "breakdown" else "(varies)",
                            hdp_scopes[0].measure   if ext_strategy != "measure"   else "(varies)",
                        )
                        if hdp_key in evaluated_hdps:
                            hdps_skipped += 1
                            continue
                        evaluated_hdps.add(hdp_key)
                        # --- end dedup ---

                        hdps_evaluated += 1
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

    total_hdps = hdps_evaluated + hdps_skipped
    dedup_rate = hdps_skipped / total_hdps if total_hdps > 0 else 0.0

    print(f"\nMining complete in {elapsed:.1f}s")
    print(f"  Scopes evaluated:      {scopes_evaluated:,}")
    print(f"  Patterns found:        {patterns_found:,}")
    print(f"  HDPs evaluated:        {hdps_evaluated:,}")
    print(f"  HDPs skipped (dedup):  {hdps_skipped:,}")
    print(f"  HDP dedup hit rate:    {dedup_rate:.1%}")
    print(f"  MetaInsights found:    {metainsights_found:,}")
    print(f"  Query cache hit rate:  {query_cache.hit_rate:.1%}")
    print(f"  Pattern cache rate:    {pattern_cache.hit_rate:.1%}")
    if candidates:
        print(f"  Top score:             {candidates[0].score:.4f}")

    type_counts: dict = {}
    for c in candidates:
        type_counts[c.pattern_type] = type_counts.get(c.pattern_type, 0) + 1
    print("\n  Candidates by pattern type:")
    for pt, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {pt:20s}: {cnt:,}")

    diagnostics = {
        "elapsed":          elapsed,
        "scopes_evaluated": scopes_evaluated,
        "patterns_found":   patterns_found,
        "hdps_evaluated":   hdps_evaluated,
        "hdps_skipped":     hdps_skipped,
        "query_cache":      query_cache,
        "pattern_cache":    pattern_cache,
        "type_counts":      type_counts,
    }
    return candidates, diagnostics


# =============================================================================
# COMBINED DIAGNOSTICS
# =============================================================================

def save_all_view_diagnostics(all_diagnostics: dict, output_path: str):
    """Write a combined diagnostics report across all views."""
    lines = [
        "=" * 70,
        "METAINSIGHT ENGINE DIAGNOSTICS -- ALL VIEWS",
        "=" * 70,
        "",
    ]

    total_candidates = 0
    total_scopes     = 0
    total_patterns   = 0
    total_hdps       = 0
    total_skipped    = 0

    for view_name, diag in all_diagnostics.items():
        candidates_path = os.path.join(BASE_DIR, "metainsights", f"{view_name}_candidates.json")
        with open(candidates_path, encoding="utf-8") as f:
            n_candidates = len(json.load(f))

        total_candidates += n_candidates
        total_scopes     += diag["scopes_evaluated"]
        total_patterns   += diag["patterns_found"]
        total_hdps       += diag["hdps_evaluated"]
        total_skipped    += diag["hdps_skipped"]

        hdps_all   = diag["hdps_evaluated"] + diag["hdps_skipped"]
        dedup_rate = diag["hdps_skipped"] / hdps_all if hdps_all > 0 else 0.0
        qc = diag["query_cache"]
        pc = diag["pattern_cache"]
        tc = diag["type_counts"]

        lines += [
            f"--- {view_name} ---",
            f"  Time:             {diag['elapsed']:.1f}s",
            f"  Scopes evaluated: {diag['scopes_evaluated']:,}",
            f"  Patterns found:   {diag['patterns_found']:,}",
            f"  HDPs evaluated:   {diag['hdps_evaluated']:,}",
            f"  HDPs skipped:     {diag['hdps_skipped']:,}  ({dedup_rate:.1%} dedup rate)",
            f"  Candidates:       {n_candidates:,}",
            f"  Query cache HR:   {qc.hit_rate:.1%}",
            f"  Pattern cache HR: {pc.hit_rate:.1%}",
            "  Candidates by pattern type:",
        ]
        for pt, cnt in sorted(tc.items(), key=lambda x: -x[1]):
            lines.append(f"    {pt:20s}: {cnt:,}")
        zero_types = [pt for pt in PATTERN_EVALUATORS if pt not in tc]
        if zero_types:
            lines.append(f"  Zero-candidate types: {zero_types}")
        lines.append("")

    all_hdps = total_hdps + total_skipped
    lines += [
        "--- TOTALS ---",
        f"  Total candidates: {total_candidates:,}",
        f"  Total scopes:     {total_scopes:,}",
        f"  Total patterns:   {total_patterns:,}",
        f"  Total HDPs eval:  {total_hdps:,}",
        f"  Total HDPs skip:  {total_skipped:,}  ({total_skipped/all_hdps:.1%} overall dedup rate)" if all_hdps > 0 else "",
    ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nCombined diagnostics -> {output_path}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Test budgets: ~10 minutes total
    # For production runs increase to 900/600/600/900
    #
    # view4 was raised from 60s to 120s in iteration 2. Its queue was measured
    # to drain at ~103s; at 60s the cap fell in a machine-dependent place
    # (661 vs 863 candidates across two runs) while leaving the top-15
    # identical entry for entry. This is a reproducibility fix, not a results
    # one — see DISCOVER_CALIBRATION_SCORECARD.md 4.6.
    #
    # ITERATION 3: view4 goes to 600s. At 120s it EXHAUSTED the budget and
    # returned 590 candidates — fewer than iteration 1's 661 and 863 at 60s —
    # because `unpaid_share` is a sixth measure and throughput fell to ~20.4
    # scopes/s. A full drain was projected at 450s+; the actual drain time is
    # recorded in the iteration-3 report. Views 6-8 get 300s: none is wider
    # than view4 and view8 has only four dimensions, but a truncated queue is
    # the one failure mode that silently changes what a new view can find, so
    # they start generous and the report says what each actually used.
    ALL_CONFIGS = [
        ("view1", VIEW1_CONFIG, 300),
        # ITERATION 5: view2 goes to 600s, for the same reason view4 did in
        # iteration 3. At 120s its queue TRUNCATED on this run — 523 of roughly
        # 11,000 scopes, 1,301s of wall clock against a 120s budget, because the
        # machine was heavily loaded while view2 was mining (view1 ran 2.8x its
        # iteration-4 time in the same window; every view after view2 ran within
        # 1.1-1.7x). A truncated queue silently changes what a view can find,
        # which is the one failure mode that must never be scored, so the budget
        # is raised and the report states it. This is a reproducibility fix, not
        # a results one: at 120s on an unloaded machine view2 drained in 49.8s
        # in iteration 4.
        ("view2", VIEW2_CONFIG, 600),
        ("view3", VIEW3_CONFIG, 120),
        ("view4", VIEW4_CONFIG, 600),
        ("view5", VIEW5_CONFIG, 120),
        ("view6", VIEW6_CONFIG, 300),
        ("view7", VIEW7_CONFIG, 300),
        ("view8", VIEW8_CONFIG, 300),
        # ITERATION 5: view9 is 91 rows over two dimensions. Its queue is a few
        # dozen scopes, so 60s is generous rather than tight — the budget exists
        # to bound the run, not to truncate it, and the report states the drain
        # time as it does for every other view.
        ("view9", VIEW9_CONFIG, 60),
    ]

    os.makedirs(os.path.join(BASE_DIR, "metainsights"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "reports"),      exist_ok=True)

    all_diagnostics = {}

    for view_name, config, budget in ALL_CONFIGS:
        candidates, diagnostics = run_engine(config, time_budget_seconds=budget)
        save_candidates(
            candidates,
            os.path.join(BASE_DIR, "metainsights", f"{view_name}_candidates.json"),
        )
        all_diagnostics[view_name] = diagnostics

    save_all_view_diagnostics(
        all_diagnostics,
        os.path.join(BASE_DIR, "reports", "engine_diagnostics_all_views.txt"),
    )

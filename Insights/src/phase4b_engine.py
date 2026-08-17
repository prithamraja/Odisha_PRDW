# =============================================================================
# Phase 4b: All Views
# =============================================================================
# Runs the MetaInsight engine (all 11 pattern types, HDP deduplication,
# SUM/AVG aggregation) independently on each analytical view in ALL_CONFIGS.
#
# Engine unchanged from Phase 4a + dedup:
#   - Pandas query layer with augmented-query prefetch
#   - All 11 pattern evaluators (6 categorical, 5 temporal)
#   - HDP deduplication set (skip exact duplicate HDPs)
#   - MeasureConfig-driven SUM/AVG dispatch
#
# WP-D2c T3 adds three things to the same loop, none of which changes what a
# drained queue finds:
#   - the queue is sharded across worker PROCESSES, each with its own caches
#   - the candidate store is a bounded top-K heap instead of a growing list
#   - candidate output is canonically ordered, and the loaded frame is sorted
#     into a canonical row order, so the run is reproducible byte for byte
#
# Outputs:
#   metainsights/view1_candidates.json
#   metainsights/view2_candidates.json
#   metainsights/view3_candidates.json
#   metainsights/view{1,2,3}_data_quality.json
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
import hashlib
import warnings
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor

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
    MeasureConfig, ViewConfig, VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG,
    DISCOVER_SCALE,
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
    # Output + WP-D2c determinism and bounding
    save_candidates, canonical_sort, candidates_content_hash,
    TopKStore, RANKING_PREFILTER_CAP,
    temporal_support, temporal_support_ok,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import psutil
    _PROC = psutil.Process()
except Exception:                                  # psutil is optional
    _PROC = None


def peak_rss_gb() -> float:
    """Process resident memory in GB, or 0.0 where psutil is unavailable."""
    if _PROC is None:
        return 0.0
    return _PROC.memory_info().rss / 1e9


# =============================================================================
# DETERMINISM: the frame the engine mines
# =============================================================================
# D26c. view2's candidate file hashed differently on every run while view1's
# and view3's reproduced exactly. The cause is not in the engine: DuckDB writes
# view2's zero-filled cross join in whatever order its parallel hash join
# finishes, so `view2_geo_month_cube.parquet` comes out of two identical builds
# with identical CONTENT in a different ROW ORDER (measured: sorting both
# frames by the view's grain makes them equal; the raw frames are not). Group
# sums then accumulate in a different order, floats land a few ulps apart, and
# candidates that tie on score swap places in a stable sort.
#
# The fix is applied HERE rather than in the pack's SQL, which this WP may not
# touch, and it is the stronger place for it: the engine now cannot depend on
# the row order of its input at all, whoever writes it. Sorting by every
# dimension column in config order is a total order on rows for all three
# views (each view's grain is a subset of its dimensions).

def load_view_frame(config: ViewConfig) -> pd.DataFrame:
    """The view's parquet, in a canonical row order. See above."""
    df = pd.read_parquet(config.parquet_path)
    sort_cols = [c for c in list(config.dimensions) + list(config.temporal_dimensions)
                 if c in df.columns]
    if sort_cols:
        df = (df.sort_values(sort_cols, kind="mergesort", na_position="last")
                .reset_index(drop=True))
    return df


def frame_fingerprint(df: pd.DataFrame) -> str:
    """A hash of the canonicalised frame, for the run transcript."""
    return hashlib.sha256(
        pd.util.hash_pandas_object(df, index=False).values.tobytes()
    ).hexdigest()[:16]


# =============================================================================
# SHARDING — how the priority queue is split across workers
# =============================================================================
# "Shard the priority queue; per-worker caches" (WP-D2c T3). The shape of the
# split decides the cache hit rate, which is what decides throughput: WP-D2b
# measured 185.9 scopes/s at depth 1 against 25.6 at depth 2, and §2 of that
# report traced the whole difference to how much of the queue was
# cache-resident (79.3% HDP dedup, 97.4% query cache).
#
# So subspaces are NOT dealt round-robin. They are grouped by the set of
# dimensions they filter on -- every `gp_name=...` subspace in one group, every
# `theme=... x fiscal_year=...` in another -- and whole groups are assigned to
# workers longest-first. Members of a group share their augmented-query
# prefetches and most of their pattern cache, so a group kept together in one
# process keeps the locality a single loop had. Longest-first is the standard
# greedy makespan heuristic and it is deterministic, which matters more here
# than optimality: the same config must always produce the same shards.

def shard_queue(queue: list, n_shards: int) -> list:
    """Split an impact-ordered queue into n_shards lists, preserving locality."""
    groups: dict = {}
    for entry in queue:
        subspace = entry[2]
        key = tuple(sorted(dim for dim, _ in subspace.filters))
        groups.setdefault(key, []).append(entry)
    # sort groups by size (descending), then by key, so the assignment is a
    # function of the config and nothing else
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    shards = [[] for _ in range(n_shards)]
    for key, entries in ordered:
        target = min(range(n_shards), key=lambda i: (len(shards[i]), i))
        shards[target].extend(sorted(entries))
    return [s for s in shards if s]


# =============================================================================
# RUN_ENGINE — all 11 pattern types + HDP deduplication
# =============================================================================

def mine_shard(
    config: ViewConfig,
    subspaces: list,
    time_budget_seconds: float,
    top_k,
    cache_max_entries,
    dedup_max_entries,
    df: pd.DataFrame = None,
) -> tuple:
    """Mine one shard of the priority queue. The whole engine loop lives here.

    Single-process mining is this function called once with the whole queue, so
    the sequential and parallel paths are not two implementations that have to
    be kept in agreement -- they are one implementation called differently.
    Returns (TopKStore, data-quality candidates, diagnostics dict).
    """
    if df is None:
        df = load_view_frame(config)

    pattern_types_categorical = [pt for pt in PATTERN_EVALUATORS if pt not in TEMPORAL_ONLY_TYPES]
    pattern_types_temporal    = [pt for pt in PATTERN_EVALUATORS if pt not in CATEGORICAL_ONLY_TYPES]

    query_cache   = QueryCache(max_entries=cache_max_entries)
    pattern_cache = PatternCache(max_entries=cache_max_entries)
    impact_calc   = ImpactCalculator(df, config.impact_measures)
    store         = TopKStore(k=top_k)
    data_quality  = TopKStore(k=top_k)
    evaluated_hdps: OrderedDict = OrderedDict()
    hdps_skipped  = 0

    queue = list(subspaces)
    heapq.heapify(queue)

    start_time         = time.time()
    scopes_evaluated   = 0
    patterns_found     = 0
    hdps_evaluated     = 0
    metainsights_found = 0
    peak_rss           = peak_rss_gb()

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
                        # The key is hashed rather than held whole: at depth 2
                        # the raw keys (a frozenset of Subspaces each) are a
                        # large part of the never-evict memory this WP is here
                        # to bound. The set is an LRU when a bound is set, and
                        # a re-evaluated HDP is a cost, never a wrong answer --
                        # the store deduplicates on the same key.
                        hdp_key = _hdp_key(hdp_scopes, pattern_type, ext_strategy)
                        if hdp_key in evaluated_hdps:
                            hdps_skipped += 1
                            continue
                        evaluated_hdps[hdp_key] = None
                        if dedup_max_entries is not None:
                            while len(evaluated_hdps) > dedup_max_entries:
                                evaluated_hdps.popitem(last=False)
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
                                candidate.dedup_key = hdp_key
                                # A7: a candidate whose commonness rests on
                                # series with no non-zero support is not a
                                # finding and is not silently dropped either.
                                if candidate.low_temporal_support:
                                    data_quality.add(candidate)
                                else:
                                    store.add(candidate)
                                    metainsights_found += 1

            if scopes_evaluated % 5000 == 0:
                peak_rss = max(peak_rss, peak_rss_gb())
                elapsed = time.time() - start_time
                print(f"  {scopes_evaluated:,} scopes | {patterns_found:,} patterns | "
                      f"{len(store):,} MetaInsights | {elapsed:.1f}s elapsed",
                      flush=True)

    peak_rss = max(peak_rss, peak_rss_gb())
    diagnostics = {
        "elapsed":          time.time() - start_time,
        "scopes_evaluated": scopes_evaluated,
        "patterns_found":   patterns_found,
        "hdps_evaluated":   hdps_evaluated,
        "hdps_skipped":     hdps_skipped,
        "metainsights":     metainsights_found,
        "queue_drained":    not queue,
        "queue_left":       len(queue),
        "peak_rss_gb":      peak_rss,
        "query_hits":       query_cache.hits,
        "query_misses":     query_cache.misses,
        "query_evictions":  query_cache.evictions,
        "pattern_hits":     pattern_cache.hits,
        "pattern_misses":   pattern_cache.misses,
        "pattern_evictions": pattern_cache.evictions,
        "store_dropped":    store.dropped,
        "store_duplicates": store.duplicates,
    }
    return store, data_quality, diagnostics


def _hdp_key(hdp_scopes: list, pattern_type: str, ext_strategy: str) -> int:
    """The deduplication identity of one HDP, as a 64-bit digest.

    An INT rather than the tuple-of-frozensets the sequential loop used to
    hold, and rather than its hex string. At depth 2 this set reaches millions
    of entries in each worker and it was a large part of the never-evict memory
    WP-D2 measured; an int key costs about a third of a hex string's and the
    collision risk over a few million HDPs is around one in ten million.
    """
    members = "|".join(sorted(repr(s.subspace) for s in hdp_scopes))
    breakdown = hdp_scopes[0].breakdown if ext_strategy != "breakdown" else "(varies)"
    measure   = hdp_scopes[0].measure   if ext_strategy != "measure"   else "(varies)"
    return int.from_bytes(hashlib.blake2b(
        f"{members}~{pattern_type}~{breakdown}~{measure}".encode("utf-8"),
        digest_size=8,
    ).digest(), "big")


def _mine_shard_worker(payload: tuple) -> tuple:
    """Process-pool entry point: mine one shard, return picklable results."""
    (config, subspaces, budget, top_k, cache_max, dedup_max) = payload
    store, dq, diag = mine_shard(config, subspaces, budget, top_k, cache_max, dedup_max)
    # the member subspaces are only needed while scoring; dropping them here
    # keeps the pickled payload to the findings themselves
    out, out_dq = store.items(), dq.items()
    for c in out + out_dq:
        c.hdp_member_subspaces = []
    return out, out_dq, diag


def run_engine(
    config: ViewConfig,
    time_budget_seconds: int = 900,
    workers: int = 1,
    top_k=RANKING_PREFILTER_CAP,
    cache_max_entries=None,
    dedup_max_entries=None,
    subspace_limit=None,
) -> tuple:
    """
    MetaInsight mining loop with all 11 pattern types and HDP deduplication.

    Before calling evaluate_hdp, checks whether the exact same HDP
    (same member subspaces, pattern type, breakdown, measure) was already
    evaluated. If so, skips it — the candidate would be identical.

    `workers` > 1 shards the priority queue across processes (T3). A drained
    queue produces the same candidates either way: sharding changes the ORDER
    subspaces are visited in, and the only thing order decided was which of two
    identical HDPs was evaluated first and how ties were laid out in the file.
    Both are now settled by content -- the store deduplicates on the HDP key
    and orders on the canonical key.
    """
    print(f"\n{'=' * 70}")
    print(f"VIEW: {config.name}")
    print(f"{'=' * 70}")

    print(f"Loading {config.parquet_path} ...")
    df = load_view_frame(config)
    print(f"  {len(df):,} rows x {len(df.columns)} cols  "
          f"(canonical row order, fingerprint {frame_fingerprint(df)})")

    pattern_types_categorical = [pt for pt in PATTERN_EVALUATORS if pt not in TEMPORAL_ONLY_TYPES]
    pattern_types_temporal    = [pt for pt in PATTERN_EVALUATORS if pt not in CATEGORICAL_ONLY_TYPES]
    print(f"\nPattern types: {len(pattern_types_categorical)} categorical, "
          f"{len(pattern_types_temporal)} temporal  ({len(PATTERN_EVALUATORS)} total)")
    if config.excluded_pairs:
        print(f"Excluded (measure, breakdown) pairs: {len(config.excluded_pairs)}  (A1)")

    print("\nGenerating subspaces ...")
    subspaces = generate_subspaces(config, df)
    d0 = 1
    d1 = sum(1 for s in subspaces if s.depth == 1)
    d2 = sum(1 for s in subspaces if s.depth == 2)
    print(f"  depth-0: {d0}  depth-1: {d1}  depth-2: {d2}  total: {len(subspaces):,}")

    print("Building priority queue ...")
    impact_calc = ImpactCalculator(df, config.impact_measures)
    queue = build_priority_queue(subspaces, impact_calc, config.min_impact)
    if subspace_limit is not None and len(queue) > subspace_limit:
        # A FIXED SUBSET, for the determinism gate: the highest-impact N
        # subspaces, taken in the order the sequential loop would pop them. The
        # subset is a function of the config, so the single-process and
        # parallel runs it compares are mining exactly the same work.
        queue = heapq.nsmallest(subspace_limit, queue)
        heapq.heapify(queue)
        print(f"  SUBSET: the {len(queue):,} highest-impact subspaces only")
    n_scopes = sum(len(generate_data_scopes(e[2], config)) for e in queue)
    print(f"  {len(queue):,} subspaces retained after impact pruning "
          f"(min={config.min_impact}); {n_scopes:,} data scopes behind them")

    start_time = time.time()
    print(f"\nMining (budget: {time_budget_seconds}s, workers: {workers}, "
          f"top-K: {top_k}) ...", flush=True)

    if workers <= 1:
        store, dq_store, diag = mine_shard(
            config, queue, time_budget_seconds, top_k,
            cache_max_entries, dedup_max_entries, df=df,
        )
        candidates = store.items()
        data_quality = dq_store.items()
        shard_diags = [diag]
    else:
        shards = shard_queue(queue, workers)
        print(f"  queue sharded {len(shards)} ways: "
              f"{[len(s) for s in shards]} subspaces per worker", flush=True)
        payloads = [
            (config, shard, time_budget_seconds, top_k,
             cache_max_entries, dedup_max_entries)
            for shard in shards
        ]
        merged, merged_dq, shard_diags = TopKStore(k=top_k), TopKStore(k=top_k), []
        with ProcessPoolExecutor(max_workers=len(shards)) as pool:
            for cands, dq, diag in pool.map(_mine_shard_worker, payloads):
                for c in cands:
                    merged.add(c)
                for c in dq:
                    merged_dq.add(c)
                shard_diags.append(diag)
        candidates = merged.items()
        data_quality = merged_dq.items()

    elapsed = time.time() - start_time

    def total(key):
        return sum(d[key] for d in shard_diags)

    scopes_evaluated = total("scopes_evaluated")
    patterns_found   = total("patterns_found")
    hdps_evaluated   = total("hdps_evaluated")
    hdps_skipped     = total("hdps_skipped")
    total_hdps = hdps_evaluated + hdps_skipped
    dedup_rate = hdps_skipped / total_hdps if total_hdps > 0 else 0.0
    q_hits, q_miss = total("query_hits"), total("query_misses")
    p_hits, p_miss = total("pattern_hits"), total("pattern_misses")
    query_hit_rate   = q_hits / (q_hits + q_miss) if (q_hits + q_miss) else 0.0
    pattern_hit_rate = p_hits / (p_hits + p_miss) if (p_hits + p_miss) else 0.0
    drained = all(d["queue_drained"] for d in shard_diags)
    peak_rss = max([d["peak_rss_gb"] for d in shard_diags] + [peak_rss_gb()])

    print(f"\nMining complete in {elapsed:.1f}s")
    print(f"  Queue drained:         {drained}"
          + ("" if drained else f"  ({total('queue_left'):,} subspaces left)"))
    print(f"  Scopes evaluated:      {scopes_evaluated:,}")
    print(f"  Throughput:            {scopes_evaluated / elapsed:,.1f} scopes/s")
    print(f"  Patterns found:        {patterns_found:,}")
    print(f"  HDPs evaluated:        {hdps_evaluated:,}")
    print(f"  HDPs skipped (dedup):  {hdps_skipped:,}")
    print(f"  HDP dedup hit rate:    {dedup_rate:.1%}")
    print(f"  MetaInsights found:    {len(candidates):,}")
    print(f"  Data-quality (A7):     {len(data_quality):,}")
    print(f"  Query cache hit rate:  {query_hit_rate:.1%}")
    print(f"  Pattern cache rate:    {pattern_hit_rate:.1%}")
    print(f"  Cache evictions:       {total('query_evictions'):,} query / "
          f"{total('pattern_evictions'):,} pattern")
    print(f"  Store dropped / dup:   {total('store_dropped'):,} / "
          f"{total('store_duplicates'):,}")
    print(f"  Peak worker memory:    {peak_rss:.2f} GB")
    if candidates:
        print(f"  Top score:             {candidates[0].score:.4f}")
    print(f"  Candidate hash:        {candidates_content_hash(candidates)[:32]}")

    type_counts: dict = {}
    for c in candidates:
        type_counts[c.pattern_type] = type_counts.get(c.pattern_type, 0) + 1
    print("\n  Candidates by pattern type:")
    for pt, cnt in sorted(type_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {pt:20s}: {cnt:,}")

    diagnostics = {
        "elapsed":          elapsed,
        "scopes_evaluated": scopes_evaluated,
        "patterns_found":   patterns_found,
        "hdps_evaluated":   hdps_evaluated,
        "hdps_skipped":     hdps_skipped,
        "queue_drained":    drained,
        "workers":          workers,
        "top_k":            top_k,
        "peak_rss_gb":      peak_rss,
        "throughput":       scopes_evaluated / elapsed if elapsed else 0.0,
        "query_hit_rate":   query_hit_rate,
        "pattern_hit_rate": pattern_hit_rate,
        "query_evictions":  total("query_evictions"),
        "pattern_evictions": total("pattern_evictions"),
        "store_dropped":    total("store_dropped"),
        "store_duplicates": total("store_duplicates"),
        "data_quality":     data_quality,
        "support_profile":  temporal_support_profile(df, config),
        "content_hash":     candidates_content_hash(candidates),
        "type_counts":      type_counts,
    }
    return candidates, diagnostics


# =============================================================================
# A7, second half — the measures whose temporal series cannot carry a pattern
# =============================================================================
# The displacement path above catches a candidate that was BUILT on thin
# series. It cannot catch the case the operator actually raised, because that
# candidate is no longer built at all: `n_completed`'s series are all-zero, and
# an all-zero series now returns no trend rather than a NaN-derived DECREASING
# one (phase4a, evaluate_trend). Nothing is displaced because nothing is
# produced -- which would make the finding disappear silently, and the ruling
# was that it stays visible as data quality.
#
# So the profile is measured directly off the view, deterministically, whatever
# the mining produced: for every (measure, temporal breakdown), how many of the
# series the engine would read clear the support guard. A measure where most of
# them fail is a recording observation, and it is reported as one, with the
# numbers that make it one.

def temporal_support_profile(df: pd.DataFrame, config: ViewConfig) -> list:
    """Measures whose temporal series are mostly too sparse to read. See above."""
    profile = []
    for breakdown in config.temporal_dimensions:
        for measure in config.measure_names:
            if config.is_excluded(measure, breakdown):
                continue
            column = config.get_column(measure)
            if column not in df.columns or breakdown not in df.columns:
                continue
            slices = [("the whole view", df)]
            for dim in config.dimensions:
                if dim == breakdown or dim not in df.columns:
                    continue
                for val in sorted(df[dim].dropna().unique().tolist()):
                    slices.append((f"{dim}={val}", df[df[dim] == val]))

            passed, failed, nonzeros = 0, 0, []
            for _, sub in slices:
                if len(sub) == 0:
                    continue
                series = sub.groupby(breakdown)[column].sum().sort_index()
                n, nz = temporal_support(series)
                nonzeros.append(nz)
                if temporal_support_ok(series, config):
                    passed += 1
                else:
                    failed += 1
            total = passed + failed
            if total == 0 or failed <= passed:
                continue
            nonzeros.sort()
            profile.append({
                "measure":            measure,
                "breakdown":          breakdown,
                "series_examined":    total,
                "series_below_guard": failed,
                "nonzero_points_min": nonzeros[0],
                "nonzero_points_max": nonzeros[-1],
                "guard": (f"at least {config.min_temporal_nonzero} non-zero points "
                          f"and at least {config.min_temporal_nonzero_frac:.0%} of "
                          f"the series non-zero"),
                "measure_total_nonzero_rows": int(
                    (df[column].fillna(0) != 0).sum()
                ),
            })
    return sorted(profile, key=lambda p: (p["measure"], p["breakdown"]))


def save_data_quality(data_quality: list, support_profile: list, output_path: str):
    """The A7 data-quality record: displaced findings + the support profile.

    Operator ruling (session 1, item 7): a trend on a column with almost no
    non-zero events is a data-quality observation, not a performance finding,
    and it stays VISIBLE as one. phase5b_report renders this file as the
    report's data-quality annex.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    displaced = []
    for c in canonical_sort(data_quality):
        d = c.to_dict()
        d["support_note"] = c.support_note
        displaced.append(d)
    payload = {
        "displaced_findings":  displaced,
        "sub_support_measures": support_profile,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"Saved {len(displaced):,} displaced findings and "
          f"{len(support_profile):,} sub-support measures -> {output_path}")


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
        tc = diag["type_counts"]
        n_candidates = sum(tc.values())

        total_candidates += n_candidates
        total_scopes     += diag["scopes_evaluated"]
        total_patterns   += diag["patterns_found"]
        total_hdps       += diag["hdps_evaluated"]
        total_skipped    += diag["hdps_skipped"]

        hdps_all   = diag["hdps_evaluated"] + diag["hdps_skipped"]
        dedup_rate = diag["hdps_skipped"] / hdps_all if hdps_all > 0 else 0.0

        lines += [
            f"--- {view_name} ---",
            f"  Time:             {diag['elapsed']:.1f}s"
            f"   ({diag['throughput']:,.1f} scopes/s, {diag['workers']} worker(s))",
            f"  Queue drained:    {diag['queue_drained']}",
            f"  Scopes evaluated: {diag['scopes_evaluated']:,}",
            f"  Patterns found:   {diag['patterns_found']:,}",
            f"  HDPs evaluated:   {diag['hdps_evaluated']:,}",
            f"  HDPs skipped:     {diag['hdps_skipped']:,}  ({dedup_rate:.1%} dedup rate)",
            f"  Candidates:       {n_candidates:,}  (store bound K={diag['top_k']}, "
            f"{diag['store_dropped']:,} dropped, {diag['store_duplicates']:,} duplicates)",
            f"  Data-quality (A7):{len(diag['data_quality']):,}",
            f"  Query cache HR:   {diag['query_hit_rate']:.1%}"
            f"   ({diag['query_evictions']:,} evictions)",
            f"  Pattern cache HR: {diag['pattern_hit_rate']:.1%}"
            f"   ({diag['pattern_evictions']:,} evictions)",
            f"  Peak worker RSS:  {diag['peak_rss_gb']:.2f} GB",
            f"  Candidate hash:   {diag['content_hash']}",
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
    import argparse

    # A TRUNCATED QUEUE IS THE ONE UNSCOREABLE FAILURE. Every other outcome is
    # a result; a budget that cuts the queue silently changes what a view is
    # able to find, and the run then looks like a smaller answer rather than a
    # broken one. The AP deployment learned this three times: view4 at 60s
    # produced 661 candidates on one run and 863 on the next with an identical
    # top-15 (iteration 2); view4 at 120s EXHAUSTED its budget and returned
    # fewer candidates than it had at 60s (iteration 3); view2 at 120s
    # truncated at 523 of ~11,000 scopes because the machine was loaded, having
    # drained in 49.8s on the same budget a week earlier (iteration 5).
    #
    # So budgets start generous, the loop's exit condition is the proof, and
    # the report states each view's ACTUAL drain time. `run_engine` leaves the
    # loop only when the queue is empty or the budget is gone, so an elapsed
    # time strictly under the budget IS the drain proof — and a view that ends
    # at its budget is a FAIL to be re-run higher, never a smaller result.
    #
    # PR&DW budgets. The two cheap views run FIRST, deliberately: they drain in
    # about two minutes between them, which proves the ranking and the report's
    # prompt path on real candidates before anything longer is committed to
    # view1. Their candidate files are written as each view finishes, so an
    # interrupted run still leaves them behind.
    #
    # view1's budget was 18,000s, which was the right number for ONE run and is
    # now stale in both directions (D26 authorises this edit; WP-D2b E-1
    # flagged it). It was set when view1 ran at subspace depth 2, where the
    # measurement was 880,752 data scopes at ~150 scopes/s of detection alone.
    # D25 then ratified depth 1 for the sample -- 48,792 scopes, drained in
    # 262.5 s at 185.9 scopes/s -- and WP-D2c's A1 exclusions and worker pool
    # take it well below that again. 3,600s is twelve times the measured drain
    # and still generous enough that a loaded machine cannot truncate the
    # queue. The escalation argument the 18,000 carried is superseded, not
    # forgotten: it is in WPD2_REPORT.md §2 and in D25, which reversed it.
    #
    # --depth2 restores depth 2 on view1 for the sample run WP-D2c T4 makes,
    # with the budget the depth-2 arithmetic actually needs. It is a flag and
    # not a config edit because DISCOVER_SCALE owns the sample/statewide split
    # (D15) and this is neither: it is one deliberate deep run of the sample.
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default="view2,view3,view1")
    ap.add_argument("--workers", type=int, default=1,
                    help="processes to shard the priority queue across (T3)")
    ap.add_argument("--top-k", type=int, default=RANKING_PREFILTER_CAP,
                    help="candidate store bound; the ranker's prefilter cap")
    ap.add_argument("--cache-max-entries", type=int, default=None,
                    help="per-worker cache bound; unset means never evict")
    ap.add_argument("--dedup-max-entries", type=int, default=None)
    ap.add_argument("--subspace-limit", type=int, default=None,
                    help="mine only the N highest-impact subspaces (a probe, or "
                         "the determinism gate's fixed subset)")
    ap.add_argument("--depth2", action="store_true",
                    help="mine view1 at subspace depth 2 (WP-D2c T4)")
    ap.add_argument("--budget", type=int, default=None,
                    help="override every view's time budget, in seconds")
    ap.add_argument("--suffix", default="",
                    help="write to view{N}{suffix}_candidates.json")
    args = ap.parse_args()

    BUDGETS = {"view1": 3600, "view2": 300, "view3": 120}
    CONFIGS = {"view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG}

    if args.depth2:
        VIEW1_CONFIG.max_subspace_depth = 2
        BUDGETS["view1"] = 36000
        print("view1 at subspace DEPTH 2 (WP-D2c T4)")

    print(f"DISCOVER_SCALE={DISCOVER_SCALE}")

    os.makedirs(os.path.join(BASE_DIR, "metainsights"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "reports"),      exist_ok=True)

    all_diagnostics = {}

    for view_name in args.views.split(","):
        config = CONFIGS[view_name]
        budget = args.budget or BUDGETS[view_name]
        candidates, diagnostics = run_engine(
            config,
            time_budget_seconds=budget,
            workers=args.workers,
            top_k=args.top_k,
            cache_max_entries=args.cache_max_entries,
            dedup_max_entries=args.dedup_max_entries,
            subspace_limit=args.subspace_limit,
        )
        save_candidates(
            candidates,
            os.path.join(BASE_DIR, "metainsights",
                         f"{view_name}{args.suffix}_candidates.json"),
        )
        save_data_quality(
            diagnostics["data_quality"],
            diagnostics["support_profile"],
            os.path.join(BASE_DIR, "metainsights",
                         f"{view_name}{args.suffix}_data_quality.json"),
        )
        all_diagnostics[view_name] = diagnostics

    save_all_view_diagnostics(
        all_diagnostics,
        os.path.join(BASE_DIR, "reports", "engine_diagnostics_all_views.txt"),
    )

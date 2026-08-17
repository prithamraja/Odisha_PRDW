# =============================================================================
# Phase 5c: the cross-view global feed (top-50)
# =============================================================================
# Phase 5 ranks WITHIN a view. The Discover surface in the frontend is a single
# flat feed, so something has to decide what the front page shows across all the
# views (nine in the AP deployment this design was written for, three in PR&DW —
# `VIEWS` below is the registry). This script does that, and it is NOT an engine
# change: it reads
# the candidates phase 4b already produced and phase 5 already scores, and
# re-orders them. Detection, scoring and the per-view rankings are untouched.
#
# Inputs:
#   metainsights/view{N}_ranked.json      (the pool; see build_pool)
#   metainsights/view{N}_candidates.json  (for the raw count in the header only)
#   views_prdw/*.parquet                  (for the measured GP coverage figure)
#
# Outputs:
#   metainsights/global_feed.json         <- the frontend contract (D16)
#   reports_prdw/global_feed.md           <- its readable twin
#
# Run from the repo root:
#   python Insights/src/phase5c_global_feed.py
#
# -----------------------------------------------------------------------------
# WHY RAW SCORES CANNOT BE POOLED
# -----------------------------------------------------------------------------
# A candidate's score is conciseness x impact, and impact is normalised to its
# OWN view's total: a subspace holding 30% of view8's 1,100 farmers and one
# holding 30% of view1's 5,818 payments both score 0.30. Pooling raw scores
# therefore does not rank findings by how much of the programme they concern —
# it ranks them by how concentrated they are inside whatever view they came
# from, which systematically favours the narrowest view. The observed spread
# makes this concrete: the top scores in every view cluster in a band roughly
# 0.72-0.78 wide apart, so an unweighted pool is close to arbitrary.
#
# ITERATION 3 applied one explicit multiplier per view:
#
#     global_score = conciseness x (view_coverage_weight x impact)
#
# and that was not enough. It gives every finding its view's FULL weight, so it
# cannot tell a view's best finding from its twelfth; with weights spreading
# 2.6x against a within-view score spread of 1.08x, view size ordered the page.
# view1 took 12 of 35 slots, slots 1-9 were eight view1 findings and one view5,
# and view6's rank-1 finding — the clearest result in the whole run — did not
# appear at all while view1's twelfth did. Only 2 of 11 injected patterns
# reached the feed.
#
# ITERATION 4 makes the ordering rank-aware, in two parts:
#
#   1. SEED. Each view's best surviving finding enters unconditionally. One
#      guaranteed slot per view. This is what stops a question family being
#      silently dropped because its view is small: every family's best answer is
#      on the page by construction, and the report says so.
#
#   2. DECAY. The remaining slots are filled greedily on
#
#          global_score = view_weight x score x RANK_DECAY^(rank - 1)
#
#      where `rank` is the finding's own position in its view's ranked list.
#      Rank decay makes a view spend its weight on its best findings first, so a
#      large view no longer converts its size into a long tail of mediocre
#      entries. `score` is the within-view score phase5 already computed — it
#      carries the greedy ranker's post-redundancy judgement, which the raw
#      conciseness x impact product does not.
#
# THE WEIGHTS AND THE KNOBS ARE EDITORIAL CHOICES AND ARE PRINTED, NOT HIDDEN.
# They are stated in the output header of both artefacts so a reader can
# disagree with them.
#
# WHICH WEIGHT, AND WHY NOT RUPEES — AP's answer, SUPERSEDED FOR PR&DW by D24
# (equal weights; the reasoning is at compute_coverage_weights below). Kept
# because the frontend contract this file emits is the AP one (D16) and the
# `reach`/`weights` block it prints exists because of the argument below.
#
# The iteration-3 spec offered benefit rupees
# or farmer count. This implementation uses FARMER COUNT: the number of distinct
# PM-KISAN roster farmers each view's source rows can say something about, as a
# share of the sum across views. Rupees were rejected for a structural reason,
# not a tuning one — view8 reads the land records, which carry no money column
# at all, so a rupee weight would send an entire view's findings to weight ~0
# and the land-integrity question could never reach the front page whatever it
# found. Farmer count is also the more honest reading of "coverage": how much of
# the farming population does this view speak for.
#
# ITERATION 5 fixes two defects that iteration 4's run exposed and measured.
# Both are in this file; nothing about detection, scoring or the per-view
# rankings moves, and phase5's k = 15 behaviour is untouched.
#
#   FIX 1 — `pair_overlap`'s cross-view branch scored subspace similarity 1.0
#   when BOTH subspaces were empty, so any two depth-0 findings sharing a
#   pattern type collected 0.4 of penalty-eligible overlap for free, plus 0.3
#   more if their extending dimensions mapped to the same concept. Nearly every
#   high-scoring finding is depth-0. Measured consequence: a land-discrepancy
#   finding was charged 0.07064 against a programme-money finding at r = 0.7,
#   which is more than its own base score of 0.10091, and it was rejected while
#   a finding scoring 0.00242 was selected. Iteration 3 fixed exactly this
#   inside the WITHIN-view gate (`_shares_any_content`) and the reasoning was
#   never carried across. It is carried now: see `pair_overlap`.
#
#   FIX 2 — the fill stage charged the SUM of overlaps against the selected set.
#   For a high scorer `min(item, selected)` picks the other item's score, so the
#   penalty grows with the selected set without bound; for a low scorer it is
#   bounded by the low scorer's own tiny score. The higher a finding scored, the
#   likelier it was to be rejected, and at k = 50 that dominated — the feed
#   stopped at 39. The fill stage now charges the SINGLE WORST overlap, the
#   standard MMR shape: see `select_top`.
# =============================================================================

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402

from phase2_engine import MetaInsightCandidate, load_candidates  # noqa: E402
from phase5_ranking import (  # noqa: E402
    compute_overlap_ratio, generate_nl_summary,
)
# The view configs, from the engine that owns them — the same import phase5b_report
# makes, so a parquet path is written down in exactly one place. Deliberately NOT
# imported from phase5b_report: that module loads `.env` and the OpenAI client at
# import time, and this file makes no API call and needs no key.
from phase4a_engine import VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG  # noqa: E402

VIEW_CONFIGS = {
    "view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG,
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# WP-D3 NOTE — WHAT WAS PORTED, AND WHAT WAS DELIBERATELY NOT
# =============================================================================
# WP-D2 left this file deliberately unrunnable: it had updated the two view
# registries below to the three Odisha PR&DW views and emptied LINEAGE, but the
# coverage weighting was still the AP deployment's — FARMER_REACH_SQL weighting
# each view by how many PM-KISAN roster farmers it could speak about, over CSVs
# in `rtgs_csv/` that this deployment does not have. PR&DW carries no
# beneficiary identity anywhere in its drop (mapping doc §4.4), so the weighting
# had to be designed rather than translated, and D16 forbade WP-D2 touching the
# shape to do it.
#
# WP-D3 makes that call, ratified as D24: THE WEIGHTS ARE EQUAL. The reasoning
# is in compute_coverage_weights() below. Three consequences here:
#
#   1. FARMER_REACH_SQL and the `rtgs_csv/` dependency are GONE, not ported. The
#      AP queries counted roster Aadhaars; there is no such column and no such
#      file in this deployment, and a weight nothing can compute is worse than
#      one stated plainly. `duckdb` was imported for those queries only and goes
#      with them — this file now reads nothing but the ranked candidate JSONs.
#   2. The `reach` figure the weights were derived from is kept and is now the
#      GP coverage each view has: all three cover all 20 sample Gram Panchayats
#      by construction (the zero-fill design rule), which is exactly why the
#      weights are equal. It stays in the JSON and in both artefact headers
#      because a reader has to be able to check the arithmetic and disagree.
#   3. Output paths move to this deployment's: `Insights/metainsights/` for the
#      JSON and `Insights/reports_prdw/` for the markdown twin (Facts 7).
#
# THE EMITTED JSON STRUCTURE IS UNCHANGED (D16). Every key the AP writer emitted
# is emitted here, with the same nesting and the same types; only the values and
# the descriptive strings inside them are PR&DW's. The frontend is the AP
# frontend ported, so its parser is the contract and no key may move.
VIEWS = ["view1", "view2", "view3"]

VIEW_TITLES = {
    "view1": "Activity Lifecycle",
    "view2": "Geo-Month Cash Cube",
    "view3": "GP Performance",
}

# Where each view's rows live, read off the engine's own configs rather than
# spelled out again — the coverage figure printed in both artefacts has to come
# from the same parquet the findings came from, and there must be exactly one
# place a parquet path is written down.
VIEW_PARQUET = {v: c.parquet_path for v, c in VIEW_CONFIGS.items()}

# The geography key every PR&DW view carries. The LGD code, not the name: it is
# the identifier the government roster assigns and the one the frontend contract
# needs, and two Gram Panchayats may share a name.
GP_KEY = "gp_lgd_code"

TOP_K = 50

# ── ITERATION 4: the rank-aware knobs ────────────────────────────────────────
# These are EDITORIAL CONSTANTS fixed by AP_DISCOVER_ITERATION4_HANDOFF.md, not
# tuning parameters. They are printed in both output artefacts and must not be
# adjusted after a score has been seen — the one-scored-run rule covers the feed.
RANK_DECAY = 0.85    # global_score = view_weight x score x RANK_DECAY^(rank-1)
SEEDS_PER_VIEW = 1   # each view's best finding is guaranteed a slot

# -----------------------------------------------------------------------------
# Coverage weights — EQUAL for PR&DW (D24).
# -----------------------------------------------------------------------------
# The AP deployment weighted each view by the number of distinct PM-KISAN roster
# farmers its source rows could speak about, as a share of the sum across views.
# That weight did real editorial work there: nine views over seven programme
# files reached genuinely different populations, spanning 2.6x, and the land
# records reached farmers no money column could see.
#
# PR&DW has no such spread and no such column. Every one of the three views
# covers EVERY Gram Panchayat in the drop by construction — the zero-fill design
# rule (D15) puts a row in for a Gram Panchayat that planned nothing, wrote no
# voucher and spent nothing, so a GP absent from a view is not possible. There
# is no beneficiary identity anywhere in the drop (mapping doc §4.4), so there
# is nothing finer than a Gram Panchayat to count. Population coverage therefore
# CANNOT distinguish these three views: any honest count of it returns the same
# number three times, and equality is that answer stated rather than dressed up.
#
# The alternatives were considered and rejected for the same reason AP rejected
# rupees. Row count would weight view1 (12,704 activity rows) at 88x view3 (120
# GP-year rows) — a statement about grain, not about coverage. Rupees would
# weight the cashbook view above the performance view, which reads the same money
# at a different grain. Both would let an arithmetic accident order the front
# page, which is precisely what the seed-and-decay mechanism exists to prevent.
#
# WHAT STILL DOES THE EDITORIAL WORK: seed-one-per-view (every view's best
# finding on the page by construction) and RANK_DECAY (a view spends its weight
# on its best findings first). With equal weights the ordering is decided by
# within-view score and within-view rank, which is the judgement phase5 already
# made and the only judgement in this pipeline that was calibrated against an
# SME. That is the honest outcome, not a degraded one.
#
# THE WEIGHTS STAY PRINTED, in the JSON header and in the markdown header, as
# the AP design requires: they are an editorial choice and a reader must be able
# to disagree with them.

# -----------------------------------------------------------------------------
# Lineage — which SOURCE column a view column ultimately came from.
# -----------------------------------------------------------------------------
# Two candidates from two different views can be the same finding wearing two
# names: view1's "Scheduled Tribe farmers receive the least benefit_amount" and
# view5's "Scheduled Tribe has the lowest rupees_per_capita" are both reading
# the same rupees out of the same seven files. Pooling without dedup would put
# the same story on the front page twice.
#
# The dedup key is therefore built from where the numbers CAME FROM, not from
# what the view called them. This map is the same lineage the crosswalk records
# in `used_in_views`, read in the useful direction: the crosswalk says which
# views consume a source column, this says which source concept a view column
# came from. A view column missing from the map falls back to its own name,
# which can only make dedup miss a merge, never invent one.
LINEAGE: dict = {
    # EMPTY, WP-D2. The AP map that lived here named AP columns (`cropnameeng`,
    # `ekyc_status`, `benefit_amount`); none of them exists in a PR&DW view, so
    # every lookup would have fallen through anyway — and any that did NOT fall
    # through would have merged two findings on a name collision rather than on
    # shared lineage. The PR&DW map is WP-D3's to write, from
    # `domain_pack_prdw/crosswalk.csv`, which already records the direction this
    # needs (`used_in_views` per source column). Until then `_lineage` maps every
    # column to itself: dedup can miss a merge, which is the safe failure.
}

def _lineage(view: str, column: str) -> str:
    """The source concept a view column reads. Unknown names map to themselves,
    which is the conservative direction: it can only make dedup miss a merge,
    never invent one."""
    return LINEAGE.get(view, {}).get(column, column)


# =============================================================================
# STEP 0: THE SOURCE-SET IDENTITY (WP-D3 T3)
# =============================================================================
# The stale-editions lesson, made mechanical. A feed and a gamma edition are two
# renderings of ONE mined run, and the failure mode is not that either is wrong
# — it is that they were rendered from different runs and nothing on either file
# says so. The AP deployment shipped a suite where two editions disagreed and it
# took a re-read of every mining log to work out which was stale.
#
# So every artefact this WP publishes carries the same two things in its header:
# a RUN STAMP and a CANDIDATE-SET ID. The ID is a hash over the hashes of the
# candidate files the artefacts were built from, so two files carrying the same
# ID were provably built from the same mined output, and a file carrying a
# different one is stale on sight.
#
# The stamp is read from `DISCOVER_RUN_STAMP` when set, the same
# environment-switch idiom as DISCOVER_SCALE, because the gamma suite and the
# feed are two processes and a per-process clock would give them two different
# stamps for one run. Set it once and export it for both:
#
#     export DISCOVER_RUN_STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
#     python Insights/src/phase5c_gamma_reports.py
#     python Insights/src/phase5c_global_feed.py
#
# Unset, it falls back to this process's own UTC clock, which is right for a
# one-artefact run and wrong for a suite; the header says which it was.
#
# WHY THIS IS NOT IN THE FEED JSON. D16 freezes the emitted JSON structure
# field-by-field, and the frontend parser is the contract. The identity
# therefore goes in the markdown twin's header, in every gamma edition's header,
# and in a SIDECAR file beside the JSON (`global_feed_source_set.json`) — a new
# file rather than a new key, so machine-readable provenance exists without a
# shape change. Adding a `provenance` block to the contract itself is an
# operator decision and is flagged as one in the WP report.

SOURCE_SET_SIDECAR = "global_feed_source_set.json"


def run_stamp() -> tuple[str, bool]:
    """(UTC stamp, was it supplied). See the STEP 0 note on why it is shared."""
    supplied = os.environ.get("DISCOVER_RUN_STAMP")
    if supplied:
        return supplied, True
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"), False)


def _sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_set_identity() -> dict:
    """Every candidate file the published artefacts read, with its hash.

    Covers BOTH families: `view{N}_candidates.json`, which the gamma suite
    re-scores, and `view{N}_ranked.json`, which the feed pools. An artefact built
    from one but not the other is still built from this run, and the ID has to
    say so, so both are hashed and both go into it.
    """
    import hashlib

    files = {}
    for view in VIEWS:
        for kind in ("candidates", "ranked"):
            name = f"{view}_{kind}.json"
            path = os.path.join(BASE_DIR, "metainsights", name)
            if os.path.exists(path):
                files[name] = {
                    "sha256": _sha256(path),
                    "bytes": os.path.getsize(path),
                }

    # The ID is over the (name, hash) pairs in sorted order, so it does not
    # depend on filesystem order and a missing file changes it rather than being
    # quietly skipped.
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(f"{name}:{files[name]['sha256']}\n".encode())

    stamp, supplied = run_stamp()
    return {
        "candidate_set_id": digest.hexdigest()[:16],
        "generated_at": stamp,
        "stamp_source": "DISCOVER_RUN_STAMP" if supplied else "this process's clock",
        "files": files,
    }


def identity_header_line(identity: dict) -> str:
    """The one line every published artefact carries, so a stale file is
    visible without opening a log."""
    return (
        f"*Generated {identity['generated_at']} from candidate set "
        f"`{identity['candidate_set_id']}` "
        f"({len(identity['files'])} candidate files).*"
    )


# =============================================================================
# STEP 1: coverage weights
# =============================================================================

def compute_coverage_weights() -> tuple[dict, dict]:
    """(reach, weights) — the GP coverage of each view, and the equal weights.

    `reach` is read off the view parquet the findings themselves came from, not
    asserted: it is the number of distinct Gram Panchayats each view holds a row
    for. The zero-fill rule makes it the same number for all three, and that
    measured equality is the whole argument for the equal weights — so it is
    MEASURED, and a future drop where it stops being true will say so here
    instead of silently keeping weights that no longer follow from anything.

    Shape note (D16): the return is the AP function's return, both dicts keyed by
    view name, so `write_outputs` and the JSON header are untouched.
    """
    import pandas as pd

    reach = {}
    for view in VIEWS:
        parquet = VIEW_PARQUET[view]
        if not os.path.exists(parquet):
            raise SystemExit(
                f"{parquet} is missing — build the views before the feed. The "
                "coverage figure printed in both artefacts is measured off the "
                "same parquet the findings came from, never assumed."
            )
        df = pd.read_parquet(parquet, columns=[GP_KEY])
        reach[view] = int(df[GP_KEY].nunique())

    n = len(VIEWS)
    weights = {v: 1.0 / n for v in VIEWS}

    distinct = set(reach.values())
    if len(distinct) > 1:
        print(
            "  NOTE: the three views no longer cover the same number of Gram "
            f"Panchayats ({reach}). The equal weights are D24's ruling and are "
            "unchanged, but the argument for them — coverage cannot distinguish "
            "these views — no longer follows from the data. Take it back to the "
            "operator before publishing this feed."
        )
    return reach, weights


# =============================================================================
# STEP 2: pool, weight, dedup
# =============================================================================

def _highlight_key(c: MetaInsightCandidate) -> tuple:
    if not c.commonness_sets:
        return ()
    cs = c.commonness_sets[0]
    return (cs.get("pattern_type", ""), str(cs.get("highlight", "")))


def lineage_key(view: str, c: MetaInsightCandidate) -> tuple:
    """(source concepts, pattern type, subspace, highlight).

    The subspace is translated concept-by-concept too, so view1's
    {category: ST} and view5's {category: ST} collapse to the same filter even
    though one column is called `category` and the other `social_status`
    upstream."""
    concepts = frozenset(
        _lineage(view, x) for x in (c.measure, c.breakdown, c.extending_dimension)
        if x and x != "(varies)"
    )
    subspace = frozenset(
        (_lineage(view, dim), val) for dim, val in c.base_subspace.filters
    )
    return (concepts, c.pattern_type, subspace, _highlight_key(c))


def build_pool(weights: dict) -> tuple[list, dict]:
    """Load every view's RANKED findings, weight them, dedup by lineage keeping
    the highest global score of each lineage.

    The pool is the views' ranked top-15 lists, not their raw candidate
    files. A raw candidate that phase5 did not rank was already judged
    redundant or unimportant WITHIN its own view, by the engine's own criteria,
    and promoting it here would overrule that judgement using nothing but a
    view-level weight. Pooling the ranked lists also makes the dedup statistic
    mean something: merges among 120 findings are duplicate stories, whereas
    merges among 7,813 raw candidates are mostly noise.
    """
    pool = []
    stats = {"loaded": 0, "eligible": 0, "merged": 0}

    for view in VIEWS:
        raw_path = os.path.join(BASE_DIR, "metainsights", f"{view}_candidates.json")
        path = os.path.join(BASE_DIR, "metainsights", f"{view}_ranked.json")
        if not os.path.exists(path):
            print(f"  WARNING: {path} missing — {view} contributes nothing")
            continue
        if os.path.exists(raw_path):
            stats["loaded"] += len(load_candidates(raw_path))
        eligible = load_candidates(path)
        stats["eligible"] += len(eligible)
        for rank, c in enumerate(eligible, 1):
            pool.append({
                "view": view,
                "candidate": c,
                "view_rank": rank,
                "global_score": (weights[view] * c.score
                                 * (RANK_DECAY ** (rank - 1))),
            })
        print(f"  {view}: {len(eligible):,} ranked findings, "
              f"weight {weights[view]:.4f}")

    # cross-view dedup by lineage — highest global score of each lineage wins
    best: dict = {}
    for item in pool:
        key = lineage_key(item["view"], item["candidate"])
        if key not in best or item["global_score"] > best[key]["global_score"]:
            best[key] = item
    stats["merged"] = len(pool) - len(best)
    stats["deduped"] = len(best)
    return list(best.values()), stats


# =============================================================================
# STEP 3: greedy diversity selection (the same TotalUse shape as phase5)
# =============================================================================

def pair_overlap(a: dict, b: dict) -> float:
    """Redundancy between two pooled candidates, within or across views.

    WITHIN a view this is the engine's own overlap term, unchanged.

    ACROSS views it is the same formula read in the SOURCE vocabulary. That
    translation is the whole point: view1 calls the social category `category`
    and view3 calls it `social_status`, but they are the same column upstream,
    so two findings about Scheduled Tribe farmers' money are redundant with each
    other whichever view produced them. Comparing the raw column names would
    score them as unrelated.

    The weights are `_subspace_overlap`'s (0.4 subspace / 0.3 extending
    dimension / 0.15 measure / 0.15 breakdown), not a new set.

    WHY THIS IS NEEDED AT ALL. The coverage weights span 2.6x while the
    within-view scores span 1.08x, so the weight alone orders the pool: without
    a cross-view redundancy term the heaviest views take every one of the fifty
    slots and the rest are excluded arithmetically rather than on merit — their
    BEST candidate scores below the heaviest view's fiftieth. Charging
    redundancy across views is what makes this a diversity selection rather
    than a weighted sort, and it is the only lever in the design that can push
    back on the weights.

    ITERATION 5 — THE CONTENT GATE, CARRIED ACROSS VIEWS.
    ----------------------------------------------------
    Iteration 3 established inside `compute_overlap_ratio` that two candidates
    overlap only if they share at least one of {measure, breakdown, a
    NON-TRIVIAL subspace}, because "two candidates that both describe the whole
    view are not sharing a subspace, they are simply both unfiltered". That
    reasoning was never carried into this cross-view formula, and the formula
    below scores `sub = 1.0` for two empty subspaces. Nearly every high-scoring
    finding is depth-0, so almost any cross-view pair sharing a pattern type
    collected 0.4 for free and 0.3 more if their extending dimensions mapped to
    the same concept.

    Measured, iteration 4: `TOP_TWO over_declared_flag by district` (land
    discrepancy, view8) was charged 0.07064 against `TOP_TWO benefit_amount by
    scheme` (programme money, view1) at r = 0.7 — more than its own base score
    of 0.10091 — and was rejected while a finding scoring 0.00242 was selected.
    Those two findings have nothing in common but the word TOP_TWO and a
    caste-extending dimension.

        BEFORE:  eligible <- pattern-type match
                 r = 0.40*sub + 0.30*ext + 0.15*msr + 0.15*bkd
                 with sub = 1.0 when BOTH subspaces are empty

        AFTER:   eligible <- pattern-type match
                             AND ( msr lineage match
                                   OR bkd lineage match
                                   OR both subspaces non-empty and intersecting )
                 r unchanged, sub unchanged

    Only the gate moves, exactly as in iteration 3. The similarity formula
    still answers "how alike are these two", which is the right question for the
    weights; the gate answers "do they share any content at all", which is the
    right question for eligibility, and two unfiltered findings share none.
    Nothing that overlapped substantively before overlaps less now.
    """
    ca, cb = a["candidate"], b["candidate"]
    if ca.pattern_type != cb.pattern_type:
        return 0.0
    if a["view"] == b["view"]:
        return compute_overlap_ratio(ca, cb)

    va, vb = a["view"], b["view"]
    sub_a = {(_lineage(va, d), v) for d, v in ca.base_subspace.filters}
    sub_b = {(_lineage(vb, d), v) for d, v in cb.base_subspace.filters}

    msr = float(_lineage(va, ca.measure) == _lineage(vb, cb.measure))
    bkd = float(_lineage(va, ca.breakdown) == _lineage(vb, cb.breakdown))

    # ── the content gate — two empty subspaces share nothing ────────────────
    if not (msr or bkd or (sub_a and sub_b and (sub_a & sub_b))):
        return 0.0

    if not sub_a and not sub_b:
        sub = 1.0                      # both describe the whole view
    elif not sub_a or not sub_b:
        sub = 0.0
    else:
        sub = len(sub_a & sub_b) / min(len(sub_a), len(sub_b))

    ext = float(_lineage(va, ca.extending_dimension)
                == _lineage(vb, cb.extending_dimension))
    return 0.4 * sub + 0.3 * ext + 0.15 * msr + 0.15 * bkd


def marginal_gain(item: dict, selected: list) -> tuple[float, float]:
    """ITERATION 5 — the fill stage's marginal gain, MMR-shaped.

        BEFORE (iteration 3-4, phase5's k = 15 formula applied at k = 50):
            gain = global_score - SUM over selected of min(item, sel) x r

        AFTER:
            worst = MAX over selected of min(item, sel) x r
            gain  = global_score - min(global_score, worst)

    WHY THE SUM HAD TO GO. `min(item, sel)` picks the SMALLER of the two scores.
    For a high-scoring candidate that is almost always the selected item's
    score, so each redundancy charge is set by the OTHER finding's size and the
    total grows without bound as the selected set fills. For a low-scoring
    candidate `min` is its own tiny score, so its whole penalty is bounded by
    `own_score x SUM(r)` and can barely push the gain negative. The higher a
    finding scores, the likelier it is to be rejected — the ordering inverts.
    At phase5's k = 15 this rarely binds; at k = 50 with 39 already selected it
    dominated, which is why iteration 4's feed stopped at 39 and why a finding
    scoring 0.00242 was selected ahead of one scoring 0.10091.

    Charging the single worst overlap is the standard MMR shape and fixes the
    growth directly: the penalty is bounded by one pairwise term at any k, so
    two candidates cannot swap order because the selected set got bigger. The
    `min(global_score, worst)` clamp keeps the gain non-negative — a finding is
    never worse than useless, only redundant.

    Returns (gain, worst) so callers can report both.

    NOT CHANGED: `phase5_ranking.rank_metainsights`, which still uses the
    paper's summed TotalUse approximation at k = 15. That is the published
    algorithm at the size it was published for, and it is what produces the
    per-view rankings this file consumes.
    """
    worst = 0.0
    for sel in selected:
        r = pair_overlap(item, sel)
        if r:
            worst = max(worst, min(item["global_score"], sel["global_score"]) * r)
    return item["global_score"] - min(item["global_score"], worst), worst


def select_top(pool: list, k: int = TOP_K) -> tuple[list, list, list]:
    """Seed each view's best finding, then fill greedily for diversity.

    The pool is already lineage-deduped, so a seed is a distinct finding: if a
    view's rank-1 merged into another view's, that view seeds whatever of its
    findings survived highest instead, and there are always as many seeds as
    views with anything to say.

    Returns (selected, seeds, rejected) — `rejected` carries the highest-scoring
    candidates the fill stage did NOT take, with the numbers behind the
    decision, so a reader can check the redundancy term rather than trust it.
    """
    if not pool:
        return [], [], []

    ordered = sorted(pool, key=lambda x: x["global_score"], reverse=True)

    # ── 1. seeds: the best surviving finding of each view, by its own rank ──
    seeds: list = []
    for view in VIEWS:
        theirs = [x for x in pool if x["view"] == view]
        if not theirs:
            print(f"  note: {view} has no surviving finding to seed")
            continue
        theirs.sort(key=lambda x: x["view_rank"])
        seeds.extend(theirs[:SEEDS_PER_VIEW])

    selected = sorted(seeds, key=lambda x: x["global_score"], reverse=True)
    chosen = {id(x) for x in selected}

    # ── 2. fill: greedy marginal gain over the rank-decayed score ──────────
    remaining = [x for x in ordered if id(x) not in chosen][:2000]

    while len(selected) < k and remaining:
        best_gain, best_idx = -float("inf"), None
        for idx, item in enumerate(remaining):
            gain, _ = marginal_gain(item, selected)
            if gain > best_gain:
                best_gain, best_idx = gain, idx
        if best_idx is None or best_gain <= 0:
            break
        selected.append(remaining.pop(best_idx))

    # ── 3. what was left behind, and why ───────────────────────────────────
    rejected = []
    for item in sorted(remaining, key=lambda x: x["global_score"],
                       reverse=True)[:15]:
        gain, worst = marginal_gain(item, selected)
        rejected.append({
            "view": item["view"],
            "view_rank": item["view_rank"],
            "global_score": round(item["global_score"], 6),
            "worst_overlap": round(worst, 6),
            "marginal_gain": round(gain, 6),
            "summary": generate_nl_summary(item["candidate"]),
        })

    return selected, seeds, rejected


# =============================================================================
# STEP 4: emit
# =============================================================================

def _row_dict(rank: int, item: dict, seed_ids: set) -> dict:
    c = item["candidate"]
    return {
        "rank": rank,
        "view": item["view"],
        "view_title": VIEW_TITLES[item["view"]],
        "view_rank": item["view_rank"],
        "is_seed": id(item) in seed_ids,
        "global_score": round(item["global_score"], 6),
        "within_view_score": round(c.score, 6),
        "conciseness": round(c.conciseness, 6),
        "impact": round(c.impact, 6),
        "pattern_type": c.pattern_type,
        "extending_strategy": c.extending_strategy,
        "extending_dimension": c.extending_dimension,
        "breakdown": c.breakdown,
        "measure": c.measure,
        "base_subspace": [list(f) for f in c.base_subspace.filters],
        "hdp_size": c.hdp_size,
        "commonness_sets": c.commonness_sets,
        "exceptions": c.exceptions,
        "summary": generate_nl_summary(c),
    }


def write_outputs(selected: list, seeds: list, rejected: list, reach: dict,
                  weights: dict, stats: dict, identity: dict) -> list:
    seed_ids = {id(x) for x in seeds}
    rows = [_row_dict(i, item, seed_ids) for i, item in enumerate(selected, 1)]

    json_path = os.path.join(BASE_DIR, "metainsights", "global_feed.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "weighting": {
                "basis": "EQUAL across views (D24). Every view covers every "
                         "Gram Panchayat in the drop by construction, so "
                         "population coverage cannot distinguish them; `reach` "
                         "is the distinct Gram Panchayats each view holds rows "
                         "for, measured, and it is the same for all three",
                "formula": "global_score = view_weight x within_view_score x "
                           f"{RANK_DECAY}^(view_rank - 1); each view's best "
                           "finding is seeded unconditionally",
                "redundancy": "fill-stage marginal gain = global_score - "
                              "min(global_score, worst), worst = max over the "
                              "selected set of min(item, selected) x r; r is "
                              "gated on shared measure / breakdown / non-trivial "
                              "subspace lineage",
                "rank_decay": RANK_DECAY,
                "seeds_per_view": SEEDS_PER_VIEW,
                "reach": reach,
                "weights": {v: round(w, 6) for v, w in weights.items()},
            },
            "dedup": stats,
            "feed": rows,
            "highest_scoring_rejected": rejected,
        }, f, indent=2, default=str)
    print(f"\nGlobal feed JSON -> {json_path}")

    # The provenance sidecar. A NEW FILE, not a new key: the JSON above is the
    # frozen frontend contract (D16) and nothing may be added to it, but a
    # consumer still has to be able to check that the feed and the gamma edition
    # beside it came from one mined run. See the STEP 0 note.
    sidecar_path = os.path.join(BASE_DIR, "metainsights", SOURCE_SET_SIDECAR)
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump({
            "what_this_is": (
                "provenance for global_feed.json and for the gamma editions "
                "generated in the same run. It is a sidecar and not a block "
                "inside the feed because the feed's JSON structure is a frozen "
                "frontend contract (D16); adding a key to it is an operator "
                "decision, not an implementation one."
            ),
            "artefacts": [
                "metainsights/global_feed.json",
                "reports_prdw/global_feed.md",
                "reports_prdw/gamma_{0.1,0.3,0.5,0.7,0.9}_report.md",
            ],
            **identity,
        }, f, indent=2)
    print(f"Source-set sidecar -> {sidecar_path}")

    lines = [
        "# Top findings across the programme",
        "",
        identity_header_line(identity),
        "",
        f"The {len(VIEWS)} analytical views are ranked internally, each against "
        "its own total. This table is the cross-view feed: one ordering of "
        "everything the analysis found, so the front page is not decided by "
        "which view a finding happened to come from.",
        "",
        "## How the ordering was decided",
        "",
        "Two rules, both editorial, both stated here rather than buried.",
        "",
        f"**Every area's best finding is on this page by construction.** The "
        f"top finding from each of the {len(VIEWS)} areas is seeded into the "
        f"list unconditionally, so no question family can be dropped just "
        f"because another area happened to score higher.",
        "",
        "**The remaining places are filled by**",
        "",
        f"`global_score = area weight x within-area score x "
        f"{RANK_DECAY}^(position in its own area - 1)`",
        "",
        "The decay term is what makes an area spend its weight on its best "
        "findings first: without it, a large area converts its size into a long "
        "tail of middling entries and crowds out smaller areas' strongest "
        "results. The weights are below.",
        "",
        "**A finding is dropped only if another finding already on the page "
        "says the same thing.** Each candidate is charged for its single "
        "closest overlap with what is already selected, not for the sum of its "
        "overlaps with all of them, and two findings count as overlapping only "
        "if they share a measure, a breakdown, or an actual filter — two "
        "findings that both describe the whole programme are not saying the "
        "same thing, they are simply both unfiltered.",
        "",
        "| view | | Gram Panchayats covered | weight |",
        "|---|---|---:|---:|",
    ]
    for v in VIEWS:
        lines.append(f"| {v} | {VIEW_TITLES[v]} | {reach.get(v, 0):,} | "
                     f"{weights.get(v, 0):.4f} |")
    lines += [
        "",
        f"**The weights are equal, and that is a decision.** Coverage is counted "
        f"as the distinct Gram Panchayats each area holds rows for, and it is the "
        f"same {reach.get(VIEWS[0], 0):,} for all {len(VIEWS)} of them: a Gram "
        f"Panchayat that planned nothing, wrote no voucher and spent nothing is "
        f"still present in every area as a row of zeros, so no area covers more "
        f"of the state than another. Two alternatives were rejected. Weighting by "
        f"row count would put the activity area at 88 times the performance area, "
        f"which is a statement about how finely each one is cut and not about how "
        f"much of the programme it speaks for. Weighting by rupees would rank the "
        f"cashbook above the areas that read the same money at a different grain. "
        f"With equal weights the ordering below is decided by each finding's own "
        f"score and its own position in its area — the judgements the analysis "
        f"actually made.",
        "",
        f"Knobs, fixed in the specification and not adjusted after the fact: "
        f"rank decay **{RANK_DECAY}**, seeds per area **{SEEDS_PER_VIEW}**.",
        "",
        f"Pooled {stats['eligible']:,} ranked-eligible candidates from "
        f"{stats['loaded']:,} raw candidates across the {len(VIEWS)} views. "
        f"{stats['merged']:,} were merged as duplicates of another view's "
        f"finding — same source columns, same pattern type, same subspace, same "
        f"highlight — leaving {stats['deduped']:,} distinct findings, of which "
        f"the {len(rows)} below were selected for diversity.",
        "",
        "## The feed",
        "",
        "`seed` marks the findings guaranteed a place as their area's best; "
        "`in area` is the finding's own position within its area.",
        "",
        "| # | | view | in area | finding | pattern | global score |",
        "|---:|---|---|---:|---|---|---:|",
    ]
    for r in rows:
        summary = r["summary"].replace("|", "/")
        lines.append(
            f"| {r['rank']} | {'**seed**' if r['is_seed'] else ''} | "
            f"{r['view_title']} | {r['view_rank']} | {summary} | "
            f"{r['pattern_type']} | {r['global_score']:.4f} |"
        )

    md_path = os.path.join(BASE_DIR, "reports_prdw", "global_feed.md")
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Global feed markdown -> {md_path}")
    return rows


def main() -> int:
    print("=" * 70)
    print("PHASE 5c — CROSS-VIEW GLOBAL FEED")
    print("=" * 70)

    identity = source_set_identity()
    if not identity["files"]:
        raise SystemExit(
            f"No candidate files in {os.path.join(BASE_DIR, 'metainsights')} — "
            "mine and rank before building the feed."
        )
    print(f"\nCandidate set {identity['candidate_set_id']}, stamped "
          f"{identity['generated_at']} (from {identity['stamp_source']}):")
    for name in sorted(identity["files"]):
        print(f"  {name}  {identity['files'][name]['sha256'][:16]}")

    reach, weights = compute_coverage_weights()
    print("\nCoverage weights — EQUAL (D24); coverage measured, not assumed:")
    for v in VIEWS:
        print(f"  {v}: {reach[v]:>5,} Gram Panchayats  ->  weight {weights[v]:.4f}")

    print("\nPooling candidates:")
    pool, stats = build_pool(weights)
    print(f"\n  {stats['loaded']:,} raw -> {stats['eligible']:,} ranked-eligible "
          f"-> {stats['deduped']:,} distinct lineages "
          f"({stats['merged']:,} merged)")

    print(f"\nKnobs (fixed by spec): rank decay {RANK_DECAY}, "
          f"seeds per view {SEEDS_PER_VIEW}")
    print("  redundancy: content-gated r; fill charges the single WORST "
          "overlap, not the sum")
    selected, seeds, rejected = select_top(pool, TOP_K)
    print(f"  {len(seeds)} seeds + {len(selected) - len(seeds)} filled "
          f"= {len(selected)} of a top-{TOP_K}")

    rows = write_outputs(selected, seeds, rejected, reach, weights, stats,
                         identity)

    if rejected:
        print("\nHighest-scoring candidates NOT selected "
              "(score / worst overlap / gain):")
        for r in rejected[:10]:
            print(f"  {r['view']} #{r['view_rank']:<3} "
                  f"{r['global_score']:.5f} / {r['worst_overlap']:.5f} / "
                  f"{r['marginal_gain']:.5f}  {r['summary'][:70]}")

    by_view: dict = {}
    for r in rows:
        by_view[r["view"]] = by_view.get(r["view"], 0) + 1
    print("\nFeed composition by view:")
    for v in VIEWS:
        seeded = any(r["view"] == v and r["is_seed"] for r in rows)
        print(f"  {v}: {by_view.get(v, 0):>2}  {'(seeded)' if seeded else ''}")

    missing = [v for v in VIEWS if not any(r["view"] == v and r["is_seed"]
                                           for r in rows)]
    print(f"\n  seed check: {len(VIEWS) - len(missing)}/{len(VIEWS)} views "
          f"seeded" + (f" — MISSING {missing}" if missing else " (all present)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

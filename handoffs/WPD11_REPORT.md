# WP-D11 report — `gp_profile`: GP attributes on every view, plus `view4_gp_profile`

**Workstream:** Discover. **Nature:** BUILD, gated. **Executed:** 2026-09-07 by the
implementation agent, against `handoffs/WPD11_gp_profile.md` and the
operator-signed Amendment B (`Insights/DISCOVER_VIEW_MAPPING.md` §12, B1–B5 all
signed 2026-09-07). **Decision block:** D60–D69.

Nothing is committed and nothing is pushed. No Railway operation was performed.
`Data/` was not written to.

---

## §0 Status — the six gate items

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | `--strict` build green from `Data/` alone; crosswalk 281/281 with the `X-pii` check passing | **PASS** | `Done. 0 failed check(s).` on all four views; `crosswalk.csv` 281 rows / 20 tables, five gate checks all clean — §1 |
| 2 | T5 reconciliation complete; views 1–3 pre-existing columns byte-identical; view4 ↔ view3 SUM equality | **PASS** | 113 of 113 pre-existing columns identical on every row; 18/18 shared measures equal — 13 bit-exact, 5 equal to the paise and within 2 ULP — §2 |
| 3 | Seven dimension splits reproduce fact 2 exactly | **PASS** | 2/3/15, 2/9/7/2, 14/6, 10/10, 14/6, 12/8, 18/2 — all seven exact, on all four views — §3 |
| 4 | Four views mined and ranked; five-worker output identical to single-process on view2; regression gate 0 re-entries; view1 cost measured against the 92-minute baseline | **PASS** | all four drained; view1 1,785,956 scopes in 8,629 s at 207.0/s — *faster* per scope than the 146.0/s baseline; determinism identical; regression gate 0 failures — §4, §5 |
| 5 | Every published artefact regenerated from one candidate set; prose checker and DiscoverChat gates green; calibration package delivered | **PARTIAL — 1 gate red** | every artefact on candidate set `d619a72e4fe98d5f`; feed contract, `check_insight_prose` (29/29), DiscoverChat offline (33/33) and 93 unit tests all pass; calibration package delivered. **`check_editions_prdw` FAILS: the prose gate is 0/5 on D41 causal connectives, a WP-D11 regression** — §6, §9.A |
| 6 | **Operator calibration session on the new top-15s** | **PENDING — operator** | package in `handoffs/WPD11_calibration/`; this gate is not the agent's to close |

---

## §1 Build

### Command

```bash
python Insights/src/build_views.py \
    --pack Insights/domain_pack_prdw \
    --data-dir Data \
    --views-dir Insights/views_prdw \
    --reports-dir Insights/reports_prdw \
    --strict
```

### Environment

Run from a **local mirror at `C:\dev\odisha-d11`**, never from the Drive mount
(the pack README's rule; DuckDB spills temp files Drive cannot take). The mirror
was created fresh from the repo at the start of the WP and holds `Data/`,
`Insights/`, `DiscoverChat/` and `handoffs/`.

| | |
|---|---|
| Platform | Windows 11 (10.0.22621), 16 logical cores, 16.8 GB RAM |
| Python | 3.14.0 |
| duckdb | 1.5.1 |
| pandas / numpy / scipy | 2.3.3 / 2.4.0 / 1.16.3 |

### `--strict` outcome

**0 failed checks**, both before the amendment (baseline) and after.

```
  registered gp_profile: 20 rows x 99 cols
  built view1_activity_lifecycle: 12,704 rows
  built view2_geo_month_cube:      1,440 rows
  built view3_gp_performance:        120 rows
  built view4_gp_profile:             20 rows
  [PASSED] CHECK 1: Row counts
  [PASSED] CHECK 2: Primary-key uniqueness      (+ gp_profile, stg_gp_profile)
  [PASSED] CHECK 3: Foreign-key integrity       (+ gp_profile -> gram_panchayat, 0 orphans)
  [PASSED] CHECK 5: Categorical value domains   (+ the seven derived bands)
  [PASSED] CHECK 6: Date ranges
  [PASSED] POST-VIEW: view1 / view2 / view3 / view4
  Done. 0 failed check(s).
```

`check_ask_parity.py` was re-run after the pack edits and still reports
**41 columns compared, 0 mismatching, identical on all 12,704 activities**, with
no excluded-by-role column in view1. Discover and Ask still agree.

### The crosswalk gate

`python Insights/domain_pack_prdw/build_crosswalk.py` →
`wrote crosswalk.csv: 281 column rows across 20 tables` (182 pre-existing + 99
`gp_profile`).

```
  X-* roles naming an output column: 0
  output_columns not found in their claimed view: 0
  view1_activity_lifecycle: 77 columns, unclaimed (non-derived): []
  view2_geo_month_cube:     24 columns, unclaimed (non-derived): []
  view3_gp_performance:     33 columns, unclaimed (non-derived): []
  view4_gp_profile:         73 columns, unclaimed (non-derived): []
  X-pii column names found in a view schema: 0
    (checked 4 X-pii columns against 4 views)
  every CSV column has exactly one crosswalk row; no phantom rows
  total staged columns: 281
```

The **fifth check is new** and is the operator's ruling made mechanical. Check 1
already asserts that the crosswalk *claims* no output for an `X-pii` column;
check 5 reads the **built Parquet schemas** instead, so a column that reached a
view under its own name would be caught even if this file had been edited to
look innocent.

### The 99 `gp_profile` columns by role

| Role | n | What |
|---|---|---|
| `join` | 1 | `basic_info_lgd`, the spine |
| `dim` | 9 | the sources of the seven derived bands (three of them are also view4 measures) |
| `meas` | 41 | view4's profile measure family (the three sports columns collapse into one output, so 41 sources → 39 outputs; with the three dim-sourced population columns that is the 42 profile measures) |
| `X-sparse` | 22 | the 19 PLC detail columns + 3 sparse location/connection columns |
| `X-derived` | 10 | geography the master is authoritative for |
| `X-const` | 4 | |
| `X-pii` | 4 | operator ruling |
| `X-multi` | 3 | comma-separated multi-value strings |
| `X-unreliable` | 1 | `panchayat_area_total_area` |
| `X-deferred` | 4 | **new role** — see §9 |
| **total** | **99** | |

`X-deferred` is a role this WP had to introduce. Four `gp_profile` columns fall
through *both* of Amendment B's tables: §12.2 gives "every remaining count" the
`meas` role but then enumerates the counts, and the enumeration omits
`general_no_of_destitue_homes_old_age_homes`; and three yes/no amenity columns
(`..._renewable_source_of_energy...`, `..._rooftop_rainwater_harvesting_system...`,
`basic_amenities_panchayat_library`) are neither counts nor among §12.3's six
derived dimensions, and appear in no §12.4 column list. Rather than invent a
role or a view4 column the signed spec does not carry, all four are held out of
every view and raised in §9. All four are fully populated and are live statewide
candidates.

---

## §2 Reconciliation table (T5)

The pre-change pack was built first into `Insights/views_baseline/` and kept.
The amended pack was then built and compared against it. Script and full output:
`handoffs/WPD11_calibration/t5_reconcile.py` and `t5_reconciliation_output.txt`.

| Check | Target | Actual | Δ |
|---|---|---|---|
| view1 rows | 12,704 | **12,704** | 0 |
| view2 rows | 1,440 | **1,440** | 0 |
| view3 rows | 120 | **120** | 0 |
| view4 rows / distinct `gp_lgd_code` | 20 / 20 | **20 / 20** | 0 |
| view1 pre-existing columns identical to baseline | 70 | **70 / 70, every row** | 0 |
| view2 pre-existing columns identical to baseline | 17 | **17 / 17, every row** | 0 |
| view3 pre-existing columns identical to baseline | 26 | **26 / 26, every row** | 0 |
| columns added to views 1–3 | the 7 bands, nothing else | **exactly the 7**, no dtype change on any pre-existing column | 0 |
| seven dimension splits on view4 | fact 2 | **all seven exact** | 0 |
| `SUM(view4.m) == SUM(view3.m)`, 18 shared measures | equal | **13 bit-exact, 5 equal to the paise (1–2 ULP)** | see below |
| view4 Σ`population_total` | 115,246 | **115,246** | 0 |
| view4 Σ`households` | 26,132 | **26,132** | 0 |
| `X-pii` names in any Parquet schema | 0 | **0** (4 names × 4 views) | 0 |
| view4 Chikilli `n_admin_approvals` | 0, row present | **row present, `n_admin_approvals = 0`**, profile populated (5,896 people, Mixed, 5,000–10,000) | 0 |
| `'Not reported'` cells on any view | — | **0** (every sample GP has a profile row) | — |
| the string `'NA'` in any VARCHAR column of any view | 0 | **0** | 0 |

Column counts: view1 **70 → 77**, view2 **17 → 24**, view3 **26 → 33**, view4
**73** (6 geography + 7 dimensions + 42 profile measures + 18 lifetime measures).

### The one non-exact delta, and why it is not a defect

Five of the eighteen shared measures — `expenditure_total`, `overspend_vs_plan`,
`overspend_vs_sanction`, `payment_amount`, `receipt_amount` — are **not
bit-identical** between view3 and view4:

| measure | view3 | view4 | Δ | relative | ULP | equal to the paise |
|---|---|---|---|---|---|---|
| `expenditure_total` | 253475090.46000001 | 253475090.45999998 | 3.0e-08 | 1.2e-16 | 1 | yes |
| `overspend_vs_plan` | -519613445.53999996 | -519613445.54000002 | 6.0e-08 | 1.2e-16 | 1 | yes |
| `overspend_vs_sanction` | -50235982.54000001 | -50235982.53999999 | 1.5e-08 | 3.0e-16 | 2 | yes |
| `payment_amount` | 685750811.28999984 | 685750811.28999996 | 1.2e-07 | 1.7e-16 | 1 | yes |
| `receipt_amount` | 664791435.88999987 | 664791435.89000010 | 2.4e-07 | 3.6e-16 | 2 | yes |

This traces to **neither a §12.6 defect nor a §8 one**. It is IEEE-754:
floating-point addition is not associative, view3 sums 120 GP-year cells and
view4 sums 20 GP cells built from the same addends in a different order, so two
correct totals can differ in the last bit of a double. The thirteen count
measures ARE bit-identical, because integers of that size are held exactly.
Per-GP the two agree to within 7.5e-09 on every one of the twenty rows, and two
of the five agree exactly per-GP.

The gate as written in the brief ("`SUM(view4) == SUM(view3)` exactly") cannot be
met bit-for-bit by any correct implementation, so the check enforces the strongest
rule that *is* achievable and is what the brief means: **exact on every count
measure, and equal to the paise AND within 2 ULP on every money measure**. A
proposed wording amendment is in §9.

### §12.6 defects against the declared checks

The brief asks, for each §12.6 defect, whether any declared check would trip on
it. **None does, and the green `--strict` build is the proof.** Explicitly:

| §12.6 | Defect | Would a declared check trip? |
|---|---|---|
| 10 | `panchayat_area_total_area` mixed units | No — no check reads it; it is `X-unreliable` and no band is built on it |
| 11 | Karuabahal 12 households | No — a value inside a count column, not a key or domain violation |
| 12 | `household_toilets > households` (5), `households_tap_water > households` (2) | No — a cross-column comparison, which the runner has no check type for |
| 13 | children = 0 (9), ST = 0 (3, not 5 — see §8) | No — values inside count columns |
| 14 | destitute-homes column mixes homes and residents | No — meaning, not form; and the column is `X-deferred`, so it reaches no view |
| 15 | `no_of_computer` constant 1 | No — `X-const`, projected nowhere |
| 16 | email / mobile / address present in the source | No — `X-pii`; check 5 asserts they reach no view, and they do not |

`validation.yaml`'s header now carries this list, so a future reader finds the
answer where the constraints are declared rather than only in this report.

---

## §3 Dimension splits

Measured on the built `view4_gp_profile.parquet`, and separately as
`count(DISTINCT gp_lgd_code)` per band on views 1, 2 and 3 — all four agree, on
all seven bands.

| Dimension | Split (measured) | Expected (fact 2) | Match |
|---|---|---|---|
| `social_composition` | ST-majority 2 / SC-majority 3 / Mixed 15 | 2 / 3 / 15 | ✅ |
| `gp_size` | Under 2,500 **2** / 2,500–5,000 **9** / 5,000–10,000 **7** / 10,000+ **2** | 2 / 9 / 7 / 2 | ✅ |
| `remoteness` | Near 14 / Far 6 | 14 / 6 | ✅ |
| `digital_readiness` | Ready 10 / Not ready 10 | 10 / 10 | ✅ |
| `has_panchayat_bhawan` | Yes 14 / No 6 | 14 / 6 | ✅ |
| `has_csc` | Yes 12 / No 8 | 12 / 8 | ✅ |
| `plc_available` | No 18 / Yes 2 | 18 / 2 | ✅ |

`'Not reported'` is produced **zero times**: no dimension source column is null
on this drop. The value exists in every declared domain so that a statewide GP
with no profile row lands on it rather than failing CHECK 5.

### GPs whose band depended on a boundary or a null

- **`remoteness` is the boundary-sensitive one.** Itipur and Hirlipali both
  report **exactly 5 km**, and §12.3's cut ("under 5 km Near / 5 km or more
  Far") puts both in **Far**. Reading the cut the other way — "5 km or less is
  Near" — would make the split **16 / 4** instead of 14 / 6. Bheden reports
  **0 km** and is Near.
- **`social_composition`: Kalimela is the only GP near the cut**, at ST 50.9%
  against SC 49.1%. It is ST-majority because 50.9 > 50. Had the test been
  "≥ 50%" nothing would change; had it been "> 51%" Kalimela would fall to
  Mixed and the split would be 1 / 3 / 16.
- **`gp_size`: no GP sits on a boundary.** The closest are Barimunda at 4,924
  (band 2) and Bandhpali at 5,741 (band 3) around the 5,000 cut, and Kalimela at
  10,681 above the 10,000 cut. Sharagada at 11,767 is the largest.
- **`digital_readiness`: Boipariguda is the only GP the AND separates** — it
  reports internet and no computer, so it is Not ready. Without the AND (internet
  alone) the split would be 11 / 9.
- **No band depended on a null**, because there are none.

### The `'NA'` trap (T1)

The brief's warning was correct and the trap is live. The CSV holds **379 literal
`'NA'` tokens and zero empty cells**, and the runner's `all_varchar=true` read
returns the four-character string, not a NULL. `_cast` in `build_views.py` emits
a plain `CAST`, which raises on `'NA'`, so declaring an `int` cast on an affected
column fails registration outright.

Seven numeric columns are affected —
`basic_amenities_no_of_{computer,laptop,printer,scanner}` (2 rows each) and
`panchayat_learning_centre_details_{number_of_computers_laptops,seating_capacity,year_of_establishment}`
(18 each). They are **left uncast in `sources.yaml`** and cast in
`derived_columns.sql` behind `NULLIF(col, 'NA')`; the other 43 counts carry no
`'NA'` and are cast at registration as the brief asks. Verified: `'NA'` appears
in **no VARCHAR column of any of the four Parquets**, and no `'NA'` band exists.
A general fix (a `try_int` cast type on the runner) is proposed in §9.

## §4 Mining

```bash
python Insights/src/phase4b_engine.py --views view2,view3,view4,view1 --workers 6 \
       --cache-max-entries 60000 --dedup-max-entries 600000
```

**All four views drained.** Candidate set **`d619a72e4fe98d5f`**.

| | view1 | view2 | view3 | view4 (new) |
|---|---|---|---|---|
| dimensions (sample) | 23 | 10 + 3 temporal | 9 + 1 temporal | 9 |
| measures | 24 | 9 | 18 | **60** |
| depth | 2 | 1 | 1 | 1 |
| subspaces after the 1% prune | 3,759 of 16,182 | — | — | 61 of 61 |
| data scopes | **1,785,956** | 7,191 | 9,900 | 29,340 |
| **elapsed / budget** | **8,629.0 s** / 36,000 | 45.0 s / 300 | 21.7 s / 120 | **44.2 s** / 120 |
| queue drained | ✅ | ✅ | ✅ | ✅ |
| throughput, 6 workers | **207.0/s** | 159.7/s | 455.6/s | 664.0/s |
| peak worker RSS | 0.60 GB | 0.18 GB | 0.18 GB | 0.22 GB |
| candidates | 5,000 (156,595 dropped) | 322 | 45 | 32 |
| cache evictions | 11.3 M query / 22.8 M pattern | 0 / 0 | 0 / 0 | 0 / 0 |

**view1 cost, against the ~92-minute baseline: it is FASTER, not slower.**
WP-D2c drained 809,554 scopes in 5,544 s at 146.0 scopes/s on five workers with
17 dimensions. WP-D11 drained **1,785,956 scopes — 2.21× as many — in 8,629 s
at 207.0 scopes/s** on six workers with 23 dimensions. Per-scope cost went
*down*. The amendment's real cost on view1 is the scope count, and it is
**1.56× the wall time** (2.40 h against 1.54 h) for 2.21× the work.

**No B4 escalation is required.** The full seven-dimension depth-2 run fits the
36,000 s budget with 76% of it unused, so the subspace-filter-only fallback is
not needed and the operator has nothing to choose between.

### The false alarm, recorded because it nearly cost the WP

The first view1 attempt ran at **36–38 scopes/s** and was projected to miss its
budget by 40%. Its slowest shard projected 23 hours. That measurement was
written up as a B4 escalation and the run was stopped at 5.9%.

**It was wrong, and the cause was the command, not the amendment.** The run was
launched without `--cache-max-entries` / `--dedup-max-entries`. Those default
to `None`, which means **never evict** — the configuration WP-D2 measured at
25.6 scopes/s and 3.94 GB in one process, and which `QueryCache`'s own docstring
calls "the wall that stopped that run". WP-D2c's 146.0 scopes/s baseline passed
`60000` / `600000`, and its §4 command block records them. The observed 36–38
scopes/s sat beside WP-D2's failed number, not beside the baseline, and that
should have been the tell.

Re-run with the bounds, the same view on the same machine reached 207.0
scopes/s. **The bounds change speed and memory only, never results**: both
caches are memoisation with LRU eviction, and views 2, 3 and 4 reproduced
candidate-for-candidate across the two runs (322 / 45 / 32, identical content
hashes). The abandoned log is kept at
`handoffs/WPD11_calibration/view1_mine_partial.log`, and
`WPD11_calibration/README.md` now leads with the command so the next person
does not repeat it.

Two further facts from the failed run are worth keeping, because they are true
of the bounded run as well: the **shards are unbalanced** (in the 6-worker
bounded run the fastest worker ran at 19.7 scopes/s and the slowest at 8.6),
and the **candidate store is at its 5,000 bound from ~820 s onward** in every
worker. Neither threatens the budget now. Both are the first things to look at
if a statewide run does not fit.

### `RANKING_PREFILTER_CAP` and view1's missing temporal patterns

- **The cap binds, and it is lossless as WP-D2c says.** view1's merged store
  kept 5,000 and dropped **156,595** below the cap (the baseline dropped
  60,488). `prefilter_candidates` would have dropped the same candidates one
  step later.
- **view1's kept candidates still carry NO temporal pattern type** — `TREND`,
  `OUTLIER`, `SEASONALITY`, `CHANGE_POINT` and `UNIMODALITY` are all zero — and
  **the cause is no longer unknown.** `VIEW1_CONFIG.temporal_dimensions` is
  `[]` by design: D22 / §5 routes all temporal mining to view2, and
  `fiscal_year` sits on view1 as a *categorical* dimension. The temporal
  evaluators have no temporal breakdown to dispatch on, so they cannot fire.
  This is configuration, not a defect, and nothing was changed in passing.
  Views 2 and 3 produce temporal candidates normally on this build (view2: 104
  SEASONALITY, 85 TREND, 16 OUTLIER, 6 UNIMODALITY, 5 CHANGE_POINT; view3:
  4 TREND, 3 UNIMODALITY), which is the evidence that the evaluators work.

### Determinism (T6.4)

`check_determinism.py --views view2 --workers 5`: **five workers byte-identical
to one process** — content hash `e79d83500a05c3c5` both ways, 322 candidates
both ways, 0 failures.

That check ran under the *unbounded* cache default. It is not re-run under the
bounds because the bounded production run independently reproduced views 2, 3
and 4 candidate-for-candidate against the unbounded run — so the two cache
policies are shown to give identical results by a second route, and the
determinism claim holds under both.

### view4's shape, against the §12.4 expectation

32 candidates from 29,340 scopes, **no temporal pattern types** (the view has no
time axis), and the mix is `OUTSTANDING_1` 10, `ATTRIBUTION` 9, `EVENNESS` 6,
`TOP_TWO` 4, `LAST_TWO` 3. On 20 rows across 9 districts that is the "few
rankable findings" §12.4 asked to be judged against, and it is not a failure.

---

## §5 What changed in the top-15s

Diff tool and full output: `handoffs/WPD11_calibration/profile_diff.py` and
`profile_dimension_diff.md`. A finding is "the same finding" across the two runs
on the WP-D2 signature — pattern type, measure, breakdown, slice and extending
dimension. Score is deliberately not part of it.

| view | new | dropped | unchanged | new findings using a profile band |
|---|---|---|---|---|
| view1 | 1 | 1 | 14 | 1 |
| view2 | 12 | 12 | 3 | 12 |
| view3 | 15 | 2 | 0 | 15 |
| view4 | 15 | 0 | 0 | 15 |
| **total** | **43** | **15** | **17** | **43** |

**view1 barely moved** — 14 of 15 findings unchanged. It already carried 17
dimensions and ranks 15 out of 4,028 surviving candidates, so six more
dimensions displace almost nothing at the top.

**The GP-grain views changed completely.** view3 went from **2 ranked findings
to 15**: before the amendment it had only geography to break down by, and the
ranker could not fill a top-15 from 2 candidates. view2 replaced 12 of 15.

**Every one of the 43 new findings uses a profile band.** That is close to
logically necessary — the search space only grew — and it is the sanity check
that the diff is measuring what it claims.

### The regression gate

`check_calibration_regression.py --views view1,view2,view3,view4`: **0
failures**, all four class checks green on all four views (A1 definitional
pairs, A2 twins, A7 sub-support temporal, A4/2b size-total rankings).

**The gate caught a real omission before it passed.** On its first run it failed
view4's check 4 — three findings (`overspend_vs_plan` by `block_name`,
`overspend_vs_sanction` by `district_name`, `overspend_vs_plan` by `gp_name`)
reached the top-15 with no volume context. The cause was a per-view registry
this WP had missed: `phase5b_report._VOLUME_MEASURE` had no `view4` entry, so
`volume_share()` returned `None` for every view4 finding. **The fix was to wire
view4 in, not to suppress the findings** — they still rank, and now carry the
size shares rule 2b requires. `n_activities` was chosen over `population_total`
for the reason recorded at the registry: the volume behind an overspend total is
the activity count, and it has to be the base view3 already quotes for the same
two measures.

### The labelled baseline, reported not gated

Of the 11 findings calibration session 1 labelled **spurious**, **one still says
the same thing**: view1 #11, `OUTSTANDING_LAST overspend_vs_plan by
status_label` — *"Activity Approved has the lowest overspend_vs_plan among
status values"*. **This is by design.** WP-D2c considered and declined to
exclude it: its `excluded_pairs` comment says the pair "holds 80% of the
shortfall in a status holding 79.6% of the activities — that is arithmetic, not
a definition, and the answer to it is the volume share the report now attaches
to every total, not a silent deletion from the search space." The size-share
check that mitigates it passes. Not a regression.

2 of 15 labelled-real findings and 2 of 7 labelled-already-known still say the
same thing; the rest were displaced by the new candidates, which is what a
re-mine of this size does and is the calibration session's business.

---

## §6 Editions

Every artefact below carries candidate set **`d619a72e4fe98d5f`**, verified by
`check_editions_prdw` ("the sidecar names the same candidate set — d619a72e4fe98d5f
vs d619a72e4fe98d5f").

| artefact | result |
|---|---|
| `view{1,2,3,4}_ranked.json` | 15 findings each |
| `global_feed.json` + `global_feed_source_set.json` | 50 findings; view1 15, view2 13, view3 9, view4 13; 4/4 views seeded; weights 0.25 each (was 1/3) |
| `reports_prdw/global_feed.md` | written |
| 5 gamma editions (0.1–0.9) | written; per-gamma sources view1 30, view2 30, view3 23, view4 16 |
| `executive_metainsight_report.md` + `.pdf` | written, carries the "Gram Panchayat Profile" section |
| `insight_prose.json` | **50 findings, 4 sections** |
| `insight_feed.md` | 50 findings, 4 sections, reading notes OFF (D48-1) |
| `retrieval_corpus.json.gz` / `.npy` / `_stamp.json` | **4,397 records** (view1 4,028, view2 301, view3 38, view4 30); 2,270 embedded, 2,127 reused; `(4397, 1024)` float16, 9.0 MB |
| `decompose_corpus.json.gz` / `.npy` / `_stamp.json` | **66,779 records**; 26,081 embedded; 12.0 MB + 136.8 MB |

All in the WP-D10 spellings.

### API spend

| step | calls | tokens |
|---|---|---|
| insight prose | **124** (WP cap 150) | 371,371 |
| prose, wasted before the archive | 86 | — |
| gamma editions + executive report | not separately metered by those scripts | — |
| embeddings (Novita) | 2,270 + 26,081 texts | not counted against the prose cap |

**The prose cap needed an operator ruling to clear.** `MAX_CALLS_TOTAL = 150` is
counted across *every* `calls_*.jsonl` in `run_log_dir`, and `run_log_dir` is
hardcoded to `reports_prdw/wpd4c_run`. WP-D11's build therefore inherited
WP-D4c's 64 spent calls, and stopped at 150/150 with 13 of 50 findings unwritten.
On the operator's ruling of 2026-09-08 the prior logs were **archived, not
deleted**, into `wpd4c_run/archive_pre_wpd11/` with a README recording whose
spend each log was — including the 86 WP-D11 calls that bought nothing (5 from
an agent error that launched the build twice, 81 from the run that hit the cap).
See §9 for the durable fix.

### Checkers and gates

| gate | result |
|---|---|
| `check_feed_contract` | **PASS** — the emitted schema is field-for-field the frozen contract, by both methods |
| `check_insight_prose` | **PASS** — 29 checks, 0 failed |
| DiscoverChat `gates.py` (offline) | **PASS** — 33/33 |
| DiscoverChat unit tests | **PASS** — 93 tests |
| DiscoverChat `gates.py --live` | **PASS** — 33/33, including 6 live turns; `causal_pass=True` on every one, 0 invented ids, 146 numerals bound, 0 uncited, 0 narratives fell back |
| `check_editions_prdw` | **FAIL — 1 failure: "prose gate clean on all editions", 0/5** |

**The chat writer passes its causal check while the editions writer fails D41.**
Both write about the same profile-dimension findings from the same corpus. They
are different prompts — `DiscoverChat`'s consolidating writer is Appendix A
verbatim plus two ratified additions, and the gate confirms it carries "no
writing rules of our own" — so the divergence localises the problem to the
report writer's prompt rather than to the findings or the glossary. That is
useful evidence for §9.A.

### The editions prose gate fails, and it is a WP-D11 regression

The five gamma editions carry **D41 violations** — causal connectives asserting
a consequence:

> line 293: *"Mixed-composition Gram Panchayats carry 76.0% of the 12,704
> activities, compared with 12.7% in SC-majority and 11.3% in ST-majority Gram
> Panchayats … **therefore** …"*
>
> line 333: *"Mixed-composition Gram Panchayats account for 81.1% of activities
> in this slice and **consequently** hold most absolute plan-to-evidence
> totals"*

**The offending sentences are about `social_composition`.** This is §12.5's
"correlation only" paragraph materialising exactly where it warned: *"A profile
dimension makes a finding about a kind of GP; it never makes it because of that
kind."*

It is a regression and not a pre-existing condition. Running `prose_gate.py`
against the **pre-WP-D11** gamma editions still on the Drive tree produces only
one complaint each — *"[Gram Panchayat Profile] section is missing from the
report"* — and **no D41 problems at all**. The connectives that do appear in the
baseline editions are not in a construction the gate flags.

**Not fixed here, deliberately.** The remedies are a writer-prompt change
(`phase5b_report`'s prompt / the D41 rule text), which this WP is forbidden to
touch, or regenerating the editions until a draft comes out clean — which is the
re-roll the one-scored-run rule exists to prevent. It goes to the operator as a
gate failure. §9 carries the proposal.

### The prose fallback rate

16 first-pass / 22 regenerated / **12 fell-back** across 50 findings, against
WP-D4c's 24/8/0 and 21/10/1 across 32. First-pass fell from ~75% to 32%.

**No section is empty** — a fallback ships the deterministic engine sentence —
so the brief's stop condition ("the prose step's verifier shows silently empty
sections") is **not** met. But the drop is real, and its cause is specific:

| profile dimension | in findings | fell back | rate |
|---|---|---|---|
| `social_composition` | 18 | **0** | **0%** |
| `gp_size` | 14 | **8** | **57%** |
| findings with no profile dimension | 18 | 4 | 22% |

Profile findings as a class fall back no more often than anything else (25% vs
22%) and have a *better* first-pass rate. The regression is **`gp_size` alone**,
and the verifier gives the same reason three times:

> claim: *"GPs with **populations** of 10,000 and above show the shift later"*
> missing: *the source identifies the exception only as the gp_size category
> '10,000 and above'; it does not define gp_size as population*

The writer is right — `gp_size` is banded population and this WP's glossary says
so. The verifier is right too — its Source Material carries the band **label**,
not the glossary. They disagree because of a choice made in this WP: **the band
labels are bare numbers.** `'Under 2,500'` names no unit, so any writer
describing it must supply one, and whatever it supplies is unverifiable.
`social_composition`'s labels are self-describing and produce no fallbacks at
all — that contrast is the evidence. Full analysis:
`handoffs/WPD11_calibration/prose_status.md`. Proposed fix in §9.

---

## §7 Decision journal

Decision / options / choice and reason / reversal cost. The first six are pack
decisions, the rest arose in execution.

**1. The `'NA'` columns are cast in staging, not at registration.** (a) cast all
50 counts as T1's text says; (b) cast the 43 that are `'NA'`-free and handle the
other seven with `NULLIF` in `derived_columns.sql`; (c) cast nothing at
registration. **Chose (b)** — (a) does not work, `CAST('NA' AS BIGINT)` raises
and registration fails; (c) discards the crosswalk's record of what is cast
where. (b) keeps `'NA'` out of every band and makes a statewide `'NA'` in a
currently-clean column fail loudly. *Reversal: two YAML lines and a `NULLIF`.*

**2. `VIEW2_CONFIG` / `VIEW3_CONFIG` were edited in `phase4a_engine.py`, which
the brief's file list does not name.** The brief says to edit "the
`VIEW*_CONFIG` block" in `phase2_engine.py`, but only `VIEW1_CONFIG` is there —
views 2 and 3 have lived in `phase4a_engine.py` since WP-D2, so the task is
impossible as written. Edited where they live; the change is confined to two
`dimensions=` lines and the block comment that claimed "there is no view 4-9".
*Reversal: trivial.*

**3. `VIEW4_CONFIG` is authored in `phase2_engine.py` and re-exported from
`phase4a_engine.py`.** The re-export is **required**, not tidiness:
`phase5c_gamma_reports.discover_views()` finds reportable views by scanning
`phase4a_engine` for `VIEW\d+_CONFIG`, so without the import view4 would mine,
rank, and then vanish from all five gamma editions with nothing failing. The
four-view config gate now asserts the import exists. *Reversal: one line.*

**4. `work_proposed_cost` is not on view4.** §12.4's lifetime list has eighteen
entries and this is not one, and the brief says "columns exactly per §12.4".
Whether that is deliberate is asked in §9. *Reversal: four lines.*

**5. Four unplaced columns get a new `X-deferred` role.** (a) role them `meas`
and extend §12.4's column list; (b) `meas` with no output column; (c) a role
that says "the signed spec does not place this". **Chose (c)** — (a) invents
approved columns; (b) would file a column the spec *forgot* alongside columns it
*considered and declined*, which is the distinction the crosswalk exists to
record. Keeps the `X-` prefix so gate check 1 still covers it. *Reversal: four
dict entries.*

**6. view4's profile measures are zero-filled at the grid, including the three
`'NA'` columns.** The zero-fill rule belongs to the grid; a partial exemption
would make three of sixty measures behave unlike the other fifty-seven for a
reason invisible at the call site. Cost stated in the view header, the crosswalk
note and the glossary: for `laptops` / `printers` / `scanners`, "reported none"
and "did not report" are indistinguishable on 2 GPs each. *Reversal: three
`COALESCE`s.*

**7. The view4 ↔ view3 SUM equality is enforced to the paise and 2 ULP.**
Bit equality is unachievable — the two views sum the same rupees in different
orders and IEEE-754 addition is not associative. Count measures are still
required bit-exact and are. *Reversal: none; the check reports both forms.*

**8. `excluded_pairs=()` on view4, from measurement not taste.** WP-D2c's two
rules were run over the built view and caught nothing. The pairs that *look*
circular are not under SUM: `gp_size` is banded `population_total`, but the
5,000–10,000 band (7 GPs) totals more people than the 10,000-and-above band (2),
so the ordering is driven by band size, not the cut — the volume artifact
WPD2c_REPORT §1 deliberately leaves in the search space. §9 records the exact
condition under which this must change. *Reversal: one tuple.*

**9. `plc_available`'s glossary entry is conditional on scale**, built from the
engine's own `_PROFILE_DIMS`, so "every config column glossed and no glossary
entry without a config column" holds at either scale without a second list.

**10. Thirteen new measure units, each with a formatter.** No measure may reach
a prompt as a bare number, and "activities" had to keep meaning an activity
count because `activity_count_measures()` reads `_UNITS` to scope the FY 2023-24
caveat.

**11. view4's budget stayed at view3's 120 s.** It drained in 44.2 s.

**12. view4 runs before view1 in the default `--views` order.** A brand-new view
is the strongest argument for proving the ranking and prompt path cheaply first.

**13. The ST-zero count was corrected from five to three** in the code comments,
the config comment and the glossary. Shipping a number the build disproves is
worse than a documented divergence from the signed text. *Reversal: four
strings.*

**14. `handoffs/WPD2_calibration/verify_configs_prdw.py` was NOT edited.** It
asserts three views and no `VIEW4_CONFIG`, so it now fails by design. That
directory is outside this WP's write scope and the file is WP-D2's record of
what was true then. A four-view copy ships as
`WPD11_calibration/verify_configs_prdw_d11.py`.

**15. view1 was first mined WITHOUT the cache bounds, and a B4 escalation was
raised on the result. That was an error of mine, not a property of the
amendment.** The bounds are the difference between 36 scopes/s and 207. The
false measurement, the reasoning that produced it and the correction are all in
§4 rather than quietly dropped, because the failure mode — reading a
misconfigured run as a cost of the work — is the one most likely to recur, and
because the operator was told the WP might need a fallback it did not need.
*Reversal: n/a; the corrected run is the shipped one.*

**16. `view4` was added to `phase5b_report._VOLUME_MEASURE` after the regression
gate failed on it.** (a) accept the three findings without volume context;
(b) exclude them; (c) wire view4 into the registry. **Chose (c)** — this was a
missed enumeration, not a finding to suppress, and rule 2b's whole design is
that a size-total ranking carries its base rather than being deleted.
`n_activities` over `population_total`, for the reason recorded at the registry.
*Reversal: one dict entry.*

**17. A crash in `phase5f_decompose.save_partial_cache` was fixed, and that is
OUTSIDE this WP's declared write scope.** The brief scopes that file to "the
place a fourth view is enumerated, nothing else". `np.savez` appends `.npz` to
a path that lacks it, so a tmp of `"…partial.npz.tmp"` is written as
`"…partial.npz.tmp.npz"` and the following `os.replace` fails on a file that was
never created. It triggers only past `PARTIAL_SAVE_EVERY = 4000` newly embedded
texts, which no prior WP reached — WP-D6 and WP-D10 both served every vector
from cache. It killed the corpus build 3,840 vectors into 30,561. **Fixed
because the WP cannot complete otherwise and the change alters no output**; the
orphaned 181 MB checkpoint was salvaged so the re-run resumed. Flagged in §9 for
ratification. *Reversal: one line.*

**18. The prose build and the feed-markdown emit are two invocations, not one.**
The first T7 script passed `--emit-feed-md` on the build call; that flag renders
the *shipped* sidecar and exits, so the old 32-finding / 3-section prose was
re-rendered and no new sidecar was written. Caught by comparing the sidecar's
mtime and its hash against the baseline, not by any gate. The script now carries
the trap in a comment. *Reversal: n/a.*

**19. Prior call logs were archived, on the operator's ruling.** Options were
archiving, editing `MAX_CALLS_TOTAL`, or repointing `run_log_dir` — the last two
are in `insight_prose_config.py`, outside scope. The operator chose archiving.
**My own 86 wasted calls were archived too**, because the build could not
otherwise fit, and they are itemised in the archive README and in §6 rather than
folded away. *Reversal: move four files back.*

**20. The gamma editions were NOT regenerated to clear the D41 gate.**
Regenerating until a draft comes out clean is the re-roll the one-scored-run
rule exists to prevent, and the remedy is a prompt change this WP may not make.
Reported as a gate failure instead.

**21. `Ask/` was copied into the mirror** (`data/panchayat_1.duckdb`, the 23
top-level modules, `query_router/`, `sql/`). The retrieval corpus refuses to
build without Ask's entity registry — "geography resolution is load-bearing for
D5.1" — and it is right to refuse. Mirror-only; nothing in `Ask/` was modified.

**22. `dimension_singular` gained irregulars for the seven bands.** The generic
"<name> value" renders "no single panchayat bhawan value accounts for it", which
reads as a claim about a building.

---

## §8 Data oddities in `gp_profile` beyond §12.6

Logged, never fixed — the §8 discipline, extended.

**17. §12.6.13's ST-zero count is wrong.** It says ST population is 0 in five
Gram Panchayats and names them. Measured: **0 in three** — Biswamathpur and
Mendarajpur (Ganjam), Itipur (Khordha). The other two it names are not zero:
**Sharagada reports 16** against a population of 11,767, and **Barimunda reports
1** against 4,924. The districts §12.6 attributes are correct. The point the
entry makes — "plausible for some, unlikely for all" — is unaffected and if
anything is strengthened: 1 and 16 are less plausible than 0.

**18. The household count is unreliable across the whole column, not in one
Gram Panchayat.** §12.6.11 flags Karuabahal's 12 households against 3,208
people. Implied household size across all twenty runs from **0.51 to 267**:

| Gram Panchayat | population | households | people per household |
|---|---|---|---|
| Kalyansinghpur | 2,049 | 4,051 | **0.51** |
| Dadhapatna | 1,734 | 1,056 | 1.64 |
| … fifteen between 2.19 and 6.97 … | | | |
| Bandhpali | 5,741 | 541 | 10.61 |
| Kalimela | 10,681 | 200 | **53.4** |
| Karuabahal | 3,208 | 12 | **267.3** |

Four are visibly wrong, in both directions. Kalyansinghpur reports **more
households (4,051) than people (2,049)**, and also **2,559 job-card holders
against 2,049 people** — the only Gram Panchayat where job-card holders exceed
the population. This matters more than Karuabahal alone did: §12.4's whole
argument for view4's grain is that a per-household figure is honest there, and
it is honest *arithmetically* while the denominator remains this unreliable at
Gram-Panchayat level. The column glossary and view4's reading note now say so
explicitly, and no rate is materialised.

**19. `has_csc` and `common_service_centres` contradict each other.** The
reported yes/no flag says 12 Yes / 8 No. The reported count says **the eight
"No" Gram Panchayats hold 25 common service centres between them**, across seven
of the eight, while **two of the twelve "Yes" Gram Panchayats report zero**
(Govindapur, Haldikudar). The two columns are different questions on the same
form — "is one available in the panchayat" versus "how many are there" — and
they cannot both be right for fifteen of the twenty. Neither is repaired: the
band is built from the flag, as §12.3 specifies, and the count ships as a view4
measure. The column glossary for both now warns against presenting one as
corroborating the other.

**20. `demographic_details_transgender_population` is 0 on all twenty rows.**
§12.2 roles it `X-const`, which is the right mechanical treatment, but a
constant zero across twenty Gram Panchayats is a reporting property worth
recording rather than a demographic finding. It reaches no view.

**21. `villages_mapped_lgd` and `revenue_villages` disagree in nine of twenty** —
seven report more villages mapped to an LGD code than revenue villages, two
report fewer. Both ship as separate view4 measures and neither is derived from
the other; the glossary notes they are not necessarily equal.

**22. `osr_collected` is zero in six of twenty** (Dadhapatna, Govindapur,
Sharagada, Dutimendi, Kalyansinghpur, Haldikudar), and runs to ₹285,000 at the
top. Whether zero means "collected nothing" or "did not report" is not
recoverable from the file.

**23. `basic_amenities` has 18 columns, not the 17 §12.1 counts.** A tally
correction, not a defect; the family counts in §12.1 sum to 99 only because this
one is out by one in a way another is out the other way.

**Confirmed, not contradicted:** §12.1's internal-consistency claim holds
exactly — `male + female = total` on all 20 rows, and
`general + OBC + SC + ST = total` on all 20. `children_population = 0` in nine
(§12.6.13) is exact. `household_toilets > households` in five and
`households_tap_water > households` in two (§12.6.12) are exact, and the two
named Gram Panchayats are Chikilli and Haldikudar as stated. `no_of_computer`
is 1 on all 18 non-null rows (§12.6.15). `panchayat_area_total_area` runs 1.11
to 3,000 with three values two orders of magnitude off (§12.6.10).

---
## §9 Proposed amendments

Ordered by what blocks publication first.

**A. The editions D41 failure needs a writer-prompt change (BLOCKS GATE 5).**
All five gamma editions assert consequences on `social_composition` sentences
("carry 76.0% of activities … therefore"). The pre-WP-D11 editions have no D41
problems, so this is new. §12.5 named this exact risk. The fix is in the report
writer's prompt — a stronger correlation-only instruction naming the profile
dimensions — which this WP is forbidden to touch. Until it lands, the editions
should not be published.

**B. `gp_size`'s band labels should carry their unit.** `'Under 2,500'` →
`'Under 2,500 people'`, and so on. The bare numbers cause a 57% prose fallback
rate on that dimension against 0% for `social_composition` (§6). §12.3 fixes the
*cut points*, not the label strings, so this is a labelling change and not a
change to a signed definition — but the label IS the categorical domain value,
so it lives in `derived_columns.sql`, `validation.yaml` CHECK 5, `crosswalk.csv`
and every mined candidate. Changing it invalidates the candidate set and costs a
rebuild, a full re-mine (view1 alone 2.4 h), a re-rank and another ~124-call
prose build. Operator's call.

**C. `run_log_dir` should be per-WP.** `insight_prose_config.py` hardcodes it to
`reports_prdw/wpd4c_run`, so `MAX_CALLS_TOTAL` — documented as guarding *a WP* —
had begun guarding two, and blocked WP-D11's build at 150/150 with 13 findings
unwritten. A `wpd11_run` directory is a one-line change. The archive of
2026-09-08 is a workaround, not the fix.

**D. §12.6.13's ST-zero count is wrong.** "0 in 5" should be "0 in 3
(Biswamathpur, Mendarajpur, Itipur), and 1 and 16 in two more (Barimunda,
Sharagada)". The entry's point — "plausible for some, unlikely for all" — is
strengthened, not weakened.

**E. §12.2 leaves four columns with no role.**
`general_no_of_destitue_homes_old_age_homes`, `basic_amenities_panchayat_library`,
and the renewable-energy and rainwater-harvesting attributes are assigned by
neither §12.2's role table nor §12.4's column list. They are `X-deferred` and
reach no view. All four are fully populated statewide dimension candidates.

**F. Ratify (or revert) the `phase5f_decompose` checkpoint fix.** One line,
outside this WP's scope, made because the WP could not complete otherwise
(§7.17). It changes no output and every prior WP would have hit it on any run
embedding more than 4,000 new texts.

**G. §12.4 — is `work_proposed_cost` deliberately off view4?** view3 carries it.
If an oversight, adding it makes the SUM-equality gate cover nineteen measures.

**H. The SUM-equality wording.** "`SUM(view4) == SUM(view3)` exactly" is
unachievable for the five money measures. Proposed: *exact on every count
measure; equal to the paise and within 2 ULP on every money measure.*

**I. The three `'NA'` equipment columns lose information at the zero-fill.**
`laptops` / `printers` / `scanners` read 0 for 2 GPs each that reported nothing.
Options: leave it documented, exempt the three, or add a `profile_reported`
flag. Matters more statewide.

**J. The runner needs a `try_int` / `try_float` cast type.** One `'NA'` in a
declared-`int` column fails registration with a DuckDB conversion error rather
than a named check. First item on the statewide checklist.

**K. §12.3 — `has_csc` contradicts `common_service_centres`** in fifteen of
twenty rows (§8). Which is authoritative? Rebuilding the band on `count > 0`
would move the split from 12/8 to 13/7.

**L. §12.3 — record `remoteness`'s boundary sensitivity.** Two GPs report
exactly 5 km; the signed cut gives 14/6, the other reading 16/4.

**M. §12.6 — add the household-unreliability entry.** §12.6.11 flags one GP; the
column is unusable as a per-GP denominator in at least four (§8). This is the
entry that most directly qualifies §12.4's "a per-household figure is honest
here".

**N. When the engine gains ratio measures, view4 needs `excluded_pairs`.**
Nothing qualifies today. The moment a per-capita measure exists,
`population-per-capita × gp_size` is circular by construction.

**O. Housekeeping.** §12.1's `basic_amenities` family count is 17 and should be
18. `WPD2_calibration/verify_configs_prdw.py` now fails by design; the operator
should say which copy is the standing gate. And the mining command's cache flags
belong in the pack README, not only in WP-D2c's §4 — their omission cost this WP
a day and a false escalation.

---

## §10 Self-audit

**Verified by running it, evidence in `handoffs/WPD11_calibration/`:**

- `--strict` green from `Data/` alone, four views, both before and after the
  amendment; crosswalk 281/281 across 20 tables with all five gate checks
  including the new `X-pii` one; Ask parity 41 columns identical on 12,704
  activities.
- Every pre-existing column of views 1–3 identical to the pre-change baseline,
  value by value, on every row — 70 + 17 + 26 columns.
- The seven dimension splits, on all four views, against fact 2.
- view4 ↔ view3 SUM equality on all 18 shared measures.
- No `X-pii` name and no `'NA'` string in any of the four Parquet schemas.
- Four views mined and drained; determinism on view2; the four-view config gate
  (219 checks); the WP-D2c regression gate (0 failures, four views).
- Every edition regenerated from one candidate set, confirmed by
  `check_editions_prdw`'s own sidecar comparison.

**Not verified, and the PM should not assume it:**

- **Gate 5 is not met.** The editions prose gate fails 0/5 on D41. Everything
  else in gate 5 passes.
- **Gate 6 is the operator's** and is untouched: no finding has been labelled.
  The calibration package is delivered, not consumed.
- **The statewide branches remain untested.** `_PROFILE_DIMS` adds
  `plc_available` at statewide scale, view4 goes to depth 2, and the geography
  lists change. The config gate asserts the *flip*; no statewide data exists to
  mine.
- **view4's findings are not evidence about kinds of Gram Panchayat.** 20 rows,
  bands of 2 and 3. §12.4 said so in advance and the reading note says it to the
  reader.
- **The prose fallback diagnosis is inference from 12 records.** The `gp_size`
  labelling explanation fits every one of the eight and fits
  `social_composition`'s zero, but it has not been tested by changing a label
  and re-running — that costs a full rebuild (§9.B).

**What the PM should replay first:**

1. `bash handoffs/WPD11_calibration/sync_back.sh` was run WITHOUT `--editions`
   or with it — check which, and that `Insights/metainsights/` in the repo
   matches the candidate set you expect.
2. The build and the two gates:
   `python Insights/src/build_views.py --pack Insights/domain_pack_prdw --data-dir Data --views-dir Insights/views_prdw --reports-dir Insights/reports_prdw --strict`,
   then `t5_reconcile.py`, `build_crosswalk.py`, `verify_configs_prdw_d11.py`.
   All four are re-runnable and none needs an API key.
3. The mining command **with its cache flags** (README, first section). Without
   them you will reproduce the false escalation, not the 8,629 s drain.

**Corrections made during the WP, so the record is not read as a clean run:**
the B4 escalation (§7.15) was raised on a misconfigured run and withdrawn; the
prose step was reported as run when it had not been (§7.18); and an early
diagnosis blaming the profile dimensions for the prose fallbacks was wrong —
the measurement in §6 replaced it.

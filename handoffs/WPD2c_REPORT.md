# WP-D2c report — calibration actions, engine scaling, the depth-2 run

Executing `handoffs/WPD2c_engine_scaling.md` (Discover workstream). Run date
**2026-08-15**. Nothing was staged, committed or otherwise written to git —
that remains the operator's. One **read-only** `git show HEAD:…` was used, to
recover a file this run had overwritten; it is E-12 and it is the only git
command that ran.

**Headline:** the seven calibration actions are in, and the depth-1 re-mine
passes the new regression gate — **WP-D2's workstream gate closes**. The engine
now shards its queue across worker processes, bounds its caches and holds its
candidates in a top-K heap; **five workers produce byte-identical candidates to
one process**, and D26c is fixed at the root: two different builds of view2's
Parquet, with different row orders, now mine the same candidates.
**And the depth-2 sample run drained**: 809,554 data scopes in 5,544 s across five workers, peak 0.57 GB per worker, all 17 dimensions and 24 measures kept — the run D25 deferred for want of an engine that could hold it. Nine of view1's fifteen findings are new at that depth, and they are flagged for calibration session 2.

The thing worth the operator's eye first: **four of the eleven findings labelled
spurious in session 1 still say the same thing** (§2). The four *classes* the
actions target are gone, which is what the gate tests; what remains are size
artifacts that now arrive framed rather than deleted, and one view3 finding that
survives because view3 has almost no candidates at sample scale. Whether framing
is enough is a calibration decision, and it is the first item for session 2.

---

## §0 Gate self-assessment

| # | Gate item | Verdict | Evidence |
|---|---|---|---|
| 1 | Actions 1–7 in, with evidence for each | **PASS** | §1, one subsection per action, each with the measurement behind it |
| 2 | Regression + the four WP-D2b checks green on the depth-1 re-mine | **PASS** | §2 |
| 3 | Determinism proven; hash stability across two runs, all views | **PASS** | §3.4 — 14 checks, 0 failures, in one run: 6 stability, 6 single-vs-parallel, and the two-build test that reproduces D26c's actual cause |
| 4 | Depth-2 drains, with metrics | **PASS** | §4 |
| 5 | Packages v3 / v4 delivered | **PASS** | §5 |
| 6 | No out-of-scope file touched, no git | **PASS with one disclosure** | file list in §7; one read-only `git show` recovered a file this run overwrote (E-12). Nothing staged, committed or written |

**Preconditions.** `Insights/.env` present and used, never read out or written.
Local mirror throughout: nothing was executed against the Drive mount, and the
Parquet views were rebuilt there from `Data/` + the pack (`0 failed checks`).
**The tree was not committed** before this run — WP-D2b's E-6 disclosure stands
unchanged, and the same seven `Insights/src` files were still working-tree
modifications when this WP started.

---

## §1 The seven calibration actions

### A1 — `excluded_pairs`: 32 definitional (measure, dimension) pairs

`ViewConfig.excluded_pairs` is a tuple of (measure, breakdown) pairs skipped in
`generate_data_scopes`, and therefore skipped everywhere: the scope never
exists, so no pattern, no HDP member and no measure-extending sibling can carry
it. A dimension in an excluded pair stays fully minable as a **filter** —
"within New/Fresh activities, how do trainee numbers fall across Gram
Panchayats" is a real question, and it is the breakdown that was circular.

The list was not written by eye. Two measured rules were run over the built
view, and a pair qualifies under either:

| rule | test | what it catches |
|---|---|---|
| **A — the measure IS the dimension value, restated** | non-zero on ≥99% of the rows carrying one dimension value and on ≤1% of all other rows | `is_ongoing × status_label`; `fund_abandoned_total × status_label` |
| **B — a child table confined to one value** | every non-zero value sits in ONE dimension value, and ≥100 rows carry it | `trainees_total × work_type_label` (1,034 rows, 9.4% coverage inside New/Fresh) |

Rule A finds 11 pairs, rule B 19, and the six the session named are inside
them — except `fund_untied_total × fund_component_name` and `× tied_untied`,
which the audit does **not** support on its own (untied money spreads over seven
fund components, the largest holding 49.6%). Those two are in on the session's
authority: a measure named for one side of a classification, broken down BY that
classification, is circular whatever the residue looks like. **32 pairs in
total**, all on view1; view2 and view3 have none, measured, not assumed.

The 1% tolerance in rule A is load-bearing and was added after the first
re-mine. A strict "all non-zero mass in one value" test missed
`fund_abandoned_total × status_label` because 19 rupees of it sit on WORK
ONGOING rows — a data defect, not a reason to keep mining the tautology — and
that finding then came back at **rank 5** of the new top-15. Adding rule A
removed it and `is_started × status_label` with it.

**What the audit deliberately leaves minable**, and why the report says so
rather than the config:

- **19 sparse pairs.** `st_amount` has two non-zero rows in the whole sample, so
  it looks "confined" to whichever value those two rows happen to hold. That is
  sparsity, not construction. Excluding it would hide a data-quality signal
  behind a rule about definitions. (`sc_amount` ×4, `st_amount` ×13,
  `is_completed`/`is_under_approval` × `activity_type_label` and × `is_costless`.)
- **18 near-definitional pairs** at 99.5–99.9% of mass in one value without
  being confined to it — mostly `× activity_type_label`, where Public Works
  holds 99.6% of everything. Real concentration; the concentration is the
  finding.
- **The size artifact next door.** "Activity Approved has the lowest
  overspend_vs_plan among status values" holds 80.07% of the shortfall in a
  status holding 79.6% of the activities. That is arithmetic, not a definition,
  and the answer to it is the volume share now attached to every total (A4/2b
  below), not a silent deletion from the search space.

**Measured effect.** view1's queue falls from 48,792 data scopes to **44,846**
(−8.1%) at depth 1, and from 880,752 to **809,554** at depth 2. All four
definitional findings the operator labelled spurious (view1 #3–#6) are
unreachable: the regression gate re-checks this against whatever is currently
ranked, including HDP member measures and member breakdowns, so the pair cannot
return through a measure-extending side door.

### A2 — twin deduplication before ranking

`merge_twin_candidates` in `phase5_ranking.py` collapses OUTSTANDING_1 and
ATTRIBUTION candidates that are the same sentence: same base subspace, same
extending strategy and dimension, same breakdown, same measure, same highlight
and same member set. The higher-scored survives and records the other on
`merged_twins`, which reaches the ranked JSON, the labelling sheet
(`merged_twin` column) and the per-view findings pages.

It runs **before** the pre-filter, so a twin cannot occupy one of the 5,000
slots its survivor already holds. Measured on this re-mine: **489 merges in
view1** (2,969 → 2,480 candidates), **1 in view2**, none in view3. One survives
into view1's top-15 — rank 5, `ATTRIBUTION gen_amount by status_label`, carrying
`merged_twins: ['OUTSTANDING_1']`.

The merge is deliberately narrow, and near-twins are NOT collapsed: view1's
ranks 1 and 2 differ in measure and breakdown, and view2's ranks 1 and 15 differ
in subspace. Those tell one story to a reader but they are not the same finding,
and collapsing them is a presentation decision rather than a deduplication.
**No overlap weight was changed** — the ranking math is untouched, and this is a
deduplication in front of it.

### A3 — the EVENNESS template for signed money measures

Two changes, both deterministic, keyed on one shared constant
(`phase2_engine.SIGNED_MONEY_MEASURES`, read by the ranker and by the report so
they cannot drift):

1. **The template** (`phase5_ranking._pattern_type_to_text`). Before:
   `overspend_vs_plan is evenly distributed across gp_name values`. After:
   `overspend_vs_plan is spread evenly across block_name values -- it belongs to
   all of them and no single block_name accounts for it`.
2. **The exception clause** (`generate_nl_summary`). Before:
   `Exception: Banking Facilities (no clear pattern)`. After:
   `Uneven only in: Banking Facilities (not evenly spread) -- this is about how
   the total is spread, not about how much any one of them spends`.

The framing rule that goes with them (`EVENNESS_FOR_PROMPT`) reaches the writer
inside the finding's own stats and tells it to lead with the magnitude from
`stats.total` and then with the absence of concentration, and never to write an
exception here as good or bad behaviour. Two of view1's fifteen findings carry
it — ranks 1 and 2, the Rs 51.96 crore systemic-underspend pair the operator
called the most interesting in the set.

### A4 — the two intensity measures, and what they showed

`payment_amount_mean` and `receipt_amount_mean` are added to view2 as
AVG-aggregated **aliases**: `MeasureConfig` gained a `column` field, so the
measure name differs from the Parquet column it reads and the pack's view SQL is
untouched. No number is recomputed anywhere — `payment_amount_mean` is
`payment_amount`, averaged over the view's own GP-month grain. The glossary
entries are transcribed verbatim from the brief's appendix.

They are already earning their place. view2's rank 11, "Ganjam has the highest
(varies) among district_name values" — labelled **spurious** in session 1 as
size-driven, Ganjam holding 4 of the sample's 20 Gram Panchayats — now carries
`payment_amount_mean` and `receipt_amount_mean` among its **exceptions**. The
finding now contains the evidence against its own reading.

**The `extremum_ratio` implication, reported rather than acted on.** The
measures produce no OUTSTANDING_1, OUTSTANDING_LAST, TOP_TWO or LAST_TWO
findings at all as a sole measure — 3 SEASONALITY and 2 TREND only. That is not
the 0.67 bar starving them; it is that there is no extremum left to find:

| measure | breakdown | top ÷ second | clears 1.49? |
|---|---|---|---|
| `payment_amount` | block_name | **1.84** | yes — Bhubaneswar |
| `payment_amount_mean` | block_name | **1.01** | no — and the leader changes to Sheragada |
| `receipt_amount` | block_name | **1.94** | yes — Bhubaneswar |
| `receipt_amount_mean` | block_name | **1.10** | no — and the leader changes to Bheden |

Per Gram Panchayat per month the blocks are within 1–10% of each other. The
extremum in the totals **was** the size. Lowering `extremum_ratio` would
manufacture an outstanding block out of a 1% difference, which is the opposite
of what the denominator was added for, so **0.67 stays** and no escalation is
raised. (At `gp_name` the total and the mean give identical ratios, because
every Gram Panchayat has the same 72 months; the denominator only bites where
the group sizes differ.)

Alongside them, the enrichment now offers an **intensity companion**: where a
money total is ranked by a group and the same column exists as a per-GP-month
mean, `stats.intensity_companion` carries the size-free figures, and prompt rule
2c requires the report to prefer it when it says which place stands out.

### A5 — `known_events.csv`

New pack file, `Insights/domain_pack_prdw/known_events.csv`, four columns
(`event`, `start_month`, `end_month`, `note`), seeded with the COVID-19
first-wave lockdown 2020-03..2020-06 and two `TODO(SME)` template rows the
loader skips. The pack README gained a section explaining the format and that
adding events is an operator/SME job.

A finding earns a citation on a **date test**, never on a resemblance: a
CHANGE_POINT, OUTLIER or UNIMODALITY highlight whose month, quarter or fiscal
year falls inside an event window **or within the three months after it**, or a
finding whose own subspace pins a period overlapping the window. The three-month
recovery window is not slack — the operator's own example, the Ganjam shift at
2020-08, sits two months after a window that closes at 2020-06, and a resumption
is as dated as an interruption.

The citation joins the section's deterministic reading note, prints the `note`
column verbatim and ends with the sentence that keeps it honest: *"The dates
coincide; this analysis does not establish that one produced the other."* It is
never model-generated, and the writer is not told about it, so it cannot be
paraphrased. Firing on this run: view2, on the 2020-08 change point.

Four checks in the config gate cover it: the TODO rows are skipped, a change
point in the recovery window cites the event, a change point three years later
cites nothing, and a finding pinned to FY 2020-2021 cites it.

### A6 — the linkage framing rule

Keyed to `activity_linked_expenditure` on any temporal reading of it (a temporal
pattern type, or a temporal breakdown), and only where the measure is in the
finding's **commonness** members — a finding where linked expenditure is the odd
one out is not a finding about linked expenditure.

The deterministic sentence in the reading note carries the figures, all measured
on this drop: the cashbook's total outflow did **not** grow across the six years
(Rs 15.60 crore in 2020-21 against Rs 11.12 crore in 2025-26), while the share
of it carrying an activity link rose from **2.7% to 53.2%**, and the number of
recorded activity-voucher links rose from **30 to 2,122**. The prompt rule tells
the writer to present a rise as recording completeness, not as growth in
spending or delivery, and not to write its own version of the sentence. Seven of
view2's fifteen findings carry it.

### A7 — the degenerate-measure guard

**The threshold, from the data.** A temporal series must carry at least **4**
non-zero points and at least **one third** of its points non-zero. The floor of
4 is the longest minimum any temporal evaluator imposes on its own input
(`TREND` needs 4 points), so a series with fewer real observations than that is
being read by an evaluator that would have refused it outright had the zeros
been absent rather than recorded. The fraction was **swept**:

| fraction | view2 candidates displaced | what they were |
|---|---|---|
| 0.50 | 12 | single-GP monthly cash series carrying 34–56 non-zero months of 72 — real series, wrongly caught |
| **1/3** | **0** | — |
| 0.25 | 0 | identical candidate set to 1/3 |

The data is flat between 0.25 and 1/3, so 1/3 is the top of the flat. `n_completed`
fails at every value tried: 18 of its 20 per-Gram-Panchayat series have at most
two non-zero years and cannot clear the floor at any fraction.

**Two mechanisms, because one was not enough.** The guard displaces a candidate
whose commonness rests on sub-support series — measured at the HDP inside
`evaluate_hdp`, marked on the candidate, and routed to the run's data-quality
list instead of the findings. But the case the operator actually raised is not
displaced, it is never built: `n_completed`'s series are all zeros, and
`scipy.stats.spearmanr` on a constant series returns **NaN**, which fails every
rejection test in `evaluate_trend` because every comparison against NaN is
False. That is how 17 of view3's 20 Gram Panchayats came to have a "declining
completion trend" on a column with 17 events in it. `evaluate_trend` now rejects
NaN explicitly, so those three candidates no longer exist — and nothing would
have been logged.

So the data-quality record has a second half, measured directly off the view
whatever the mining produced: for every (measure, temporal breakdown), how many
of the series the engine would read clear the guard. Three measures in view3
fail on a majority of their series and are reported with their numbers:

| measure | series below the guard | non-zero rows in the view |
|---|---|---|
| `n_completed` | 42 of 46 | 7 |
| `n_abandoned` | 28 of 46 | 54 |
| `n_costless` | 46 of 46 | 60 |

Both halves are written to `metainsights/{view}_data_quality.json` and rendered
by `phase5b_report.data_quality_annex` as a **Data-Quality Annex** at the end of
the report — deterministic, not model-authored, and present only when a run
actually displaced something. view3's reading note also now states the
completion fact from the counts rather than from a pattern: *"Completion
recording effectively ceased after 2022-23: the 17 activities ever marked WORK
COMPLETED fall 3 / 6 / 6 across 2020-21 to 2022-23, then 0, 2 and 0 across the
three years since."*

---

## §2 The depth-1 re-mine and the regression gate

### 2.1 What the re-mine produced

All three views re-mined from a freshly built pack, then re-ranked and
re-reported in one run.

| | view1 | view2 | view3 |
|---|---|---|---|
| data scopes | **44,846** (48,792 in v2, −8.1% from A1) | **2,763** (2,149; +2 measures) | 2,502 |
| drain time / budget | **212.1 s** / 3,600 s | **32.0 s** / 300 s | **7.2 s** / 120 s |
| throughput | 212.7 scopes/s | 86.3 scopes/s | 347.5 scopes/s |
| peak memory | 0.62 GB | 0.18 GB | 0.18 GB |
| candidates | **2,969** (3,139) | **122** (110) | **2** (5) |
| after twin merge (A2) | 2,480 | 121 | 2 |
| ranked | **15** | **15** | **2** |
| A7 displaced / sub-support measures | 0 / 0 | 0 / 0 | 0 / **3** |

Every queue drained — elapsed well inside budget in all three cases, which is
the loop's own exit condition and therefore the drain proof.

view3 falls from 5 candidates to 2 and from 3 findings to 2. That is A7 working:
its three highest-ranked candidates were `n_completed` trends whose members were
series of six zeros. The completion story is not lost — it is in view3's reading
note, stated from the counts, and in the report's data-quality annex.

### 2.2 The four class checks — the regression gate

`handoffs/WPD2_calibration/check_calibration_regression.py`, **15 checks, 0
failures**, run against the current ranked output rather than against a copy of
what was true when it was written:

| # | class | check | result |
|---|---|---|---|
| 1 | definitional pairs (A1) | no ranked finding uses an excluded pair — as a breakdown, as an HDP member measure, or as an HDP member breakdown | PASS, all three views |
| 2 | twins (A2) | no top-15 carries an OUTSTANDING_1 and an ATTRIBUTION that are the same sentence | PASS, all three views |
| 3 | sub-support temporal (A7) | every ranked temporal finding's member series **re-measured from the Parquet** and re-tested against the guard — the check does not read the flag it is checking | PASS, all three views |
| 4 | size-total rankings (A4 / 2b) | every ranked total over a group carries either its volume shares or a per-unit companion | PASS, all three views |

### 2.3 The four WP-D2b report checks

`check_report_prdw.py`, **13 checks, 0 failures**:

- **(a) prose gate** — `1/1 report(s) clean`, exit 0, zero vocabulary violations,
  zero rival methodology blocks, exactly one deterministic reading note per
  section.
- **(b) no hollow sections** — 721 / 624 / 574 words against a 400–800
  instruction; every registered view has a section.
- **(c) the FY 2023-24 caveat is exact in both directions** — it qualifies on
  view1 ranks 12 and 13 and appears there, and on nothing in view2 or view3,
  where it does not appear. It sits inside the deterministic note, never in
  model prose.
- **(d) every figure traces** — **89 of 89**.

The config gate (`verify_configs_prdw.py`) is **176 checks, 0 failures**, up
from 99: the new checks cover the exclusion list, the AVG-measure aliasing rule,
the support thresholds, and the four A5 date tests.

### 2.4 The labelled baseline, row by row — and what still survives

The gate above tests classes, because a class is what a fix can remove. The
sheet is the other half of the answer, and it is reported rather than gated:

| session-1 label | still says the same thing | still occupies the same slot |
|---|---|---|
| spurious (11) | **4** | 5 |
| real (15) | 8 | 9 |
| already-known (7) | 4 | 4 |

"Same slot" means the same pattern type, measure, breakdown and extending axis;
"same thing" adds the highlight. The distinction earns its keep immediately:
view2's "Bhubaneswar has the highest (varies) among block_name values", labelled
spurious, still occupies its slot but now says **Bheden**, because the two
intensity measures joined the HDP and changed which value the majority of
members point at.

**The four that still say the same thing, and what happened to each:**

1. **view1 #11 — "Activity Approved has the lowest overspend_vs_plan among
   status values"** (now rank 3). A size artifact, not a definitional pair:
   80.07% of the shortfall sits in a status holding 79.6% of the activities. It
   now arrives with those two figures attached, and the report wrote it as
   *"The largest status-linked balance sat with activities still labelled
   'Activity Approved': Rs -41.61 crore, alongside 79.6% of all activities"* —
   the arithmetic is on the page. Deleting the finding instead would need a rule
   that removes any total whose ranking tracks volume, which would remove real
   findings with it.
2. **view2 #7 — seasonality period variants on activity-linked expenditure by
   quarter.** This is the one label that is a **PM proposal pending operator
   confirmation** (session record, tally note), not an operator ruling. It is
   not a support failure — those district series carry 17 to 22 non-zero
   quarters of 24 — so A7 does not reach it. If the operator confirms the label,
   the mechanism it needs is a rule about competing seasonal periods, which no
   action in this brief provides.
3. **view2 #10 — "Ganjam has the highest (varies) among district_name
   values."** Survives, but changed: `payment_amount_mean` and
   `receipt_amount_mean` are now among its **exceptions**, and the enrichment
   attaches Ganjam's share of the vouchers and the per-GP-month figures. The
   report used them: *"a typical Gram Panchayat month recorded outflows of Rs
   7.78 lakh in Ganjam, close to Rs 7.58 lakh in Cuttack"*. The finding now
   carries the evidence against its own naive reading.
4. **view3 #3 — "(varies) is evenly distributed across gp_name values."** The
   abstract meta-finding the operator called unreadable. It survives because
   view3 has **two candidates in total** at sample scale, so the ranker has
   nothing to prefer over it. This is WP-D2b's open question 5 arriving with a
   sharper edge, and it is a view-design question, not a ranking one.

**Set against that, the top of view1 changed a great deal.** Twelve of its
fifteen findings occupy a slot no v2 finding held (view2: 1 of 15; view3: 1 of 2). Ranks 1 and 2 are still the EVENNESS pair the operator
called the most interesting, now reworded; the four definitional pairs that
occupied ranks 3–6 are gone; and the block that replaced them is a mixture of
real findings (the theme concentration, the output-code concentration) and size
artifacts that now carry their volume context.

**Gate verdict: the WP-D2 workstream gate closes.** Its wording is "no nonsense
findings in top ranks", and the classes the session named as nonsense are gone
from the search space or merged or displaced. Four labelled rows persist; three
of them are now framed with the figures that make them readable, and one is a
consequence of view3 having almost nothing to rank. Session 2 should price
exactly those four.

---

## §3 Engine scaling

### 3.1 The design, and why each piece is shaped the way it is

**One loop, called two ways.** The mining loop moved into `mine_shard`, and
single-process mining is that function called once with the whole queue.
Parallel mining is the same function called once per shard, in a worker process.
The sequential and parallel paths are not two implementations that have to be
kept in agreement.

**Sharding preserves locality, because locality is the throughput.** WP-D2b
measured 185.9 scopes/s at depth 1 against 25.6 at depth 2 and traced the whole
difference to how much of the queue was cache-resident. So subspaces are not
dealt round-robin: they are grouped by the SET OF DIMENSIONS they filter on —
every `gp_name=…` subspace in one group, every `theme=… × fiscal_year=…` in
another — and whole groups are assigned longest-first. Members of a group share
their augmented-query prefetches and most of their pattern cache. Longest-first
is the standard greedy makespan heuristic and, more importantly here, it is
deterministic: the same config always produces the same shards. view1's depth-2
queue shards five ways as 487 / 488 / 488 / 488 / 487 subspaces.

**Bounded caches.** `QueryCache` and `PatternCache` take a `max_entries` and
become LRUs above it; `max_entries=None` is the shipped never-evict behaviour,
so every measurement taken before this WP still reproduces exactly. The
augmented-query cache gets an eighth of the budget, because one wide two-column
groupby would otherwise hold the whole allowance. The HDP deduplication set is
bounded the same way, and a re-evaluated HDP is a cost rather than a wrong
answer — the candidate store deduplicates on the same key.

**The candidate store is a top-K heap, and at K = 5,000 it is lossless.**
`TopKStore` keeps the best K by `(score, canonical_key)` and deduplicates by HDP
key. K defaults to `RANKING_PREFILTER_CAP`, the ranker's own prefilter, now
defined once in `phase2_engine` and imported by `phase5_ranking` so the two
cannot drift. At that value every candidate the store drops is one
`prefilter_candidates` would have dropped a step later, so the ranked top-15 is
provably the same list — while the unbounded accumulation that produced "14,172
candidates and climbing, unscoreable" disappears. It is deliberately not lower:
raw-score top ranks cluster near-twins (session 1), and the greedy ranker needs
breadth below them. In parallel mode each worker keeps its own top-K and the
merge takes the global top-K, which is correct because a candidate in the global
top-K is necessarily in its own worker's.

**Two orderings had to become content-derived**, or none of the above would be
reproducible:

- `canonical_key()` on a candidate — strategy, dimension, pattern type,
  breakdown, measure, sorted subspace, sorted commonness and sorted exceptions.
  Candidates are sorted by `(-score, canonical_key)` before they are written, so
  ties are broken by what the finding says rather than by when it was mined.
- The **frame itself** is sorted into a canonical row order on load. See §3.3.

### 3.2 Throughput and memory

| | WP-D2 depth 2 (unbounded, 1 process) | WP-D2b depth 1 | **WP-D2c depth 1** | **WP-D2c depth 2** |
|---|---|---|---|---|
| data scopes | 880,752 | 48,792 | **44,846** | **809,554** |
| workers | 1 | 1 | 1 | **5** |
| caches | never evict | never evict | never evict | **60,000 entries each** |
| elapsed | stopped at 585.6 s, 1.7% done | 262.5 s | **212.1 s** | **5,544.0 s, drained** |
| throughput | 25.6 scopes/s | 185.9 scopes/s | **212.7 scopes/s** | **146.0 scopes/s** |
| peak memory | **3.94 GB**, 0.38 GB machine free | 0.60 GB | **0.62 GB** | **0.57 GB per worker** |
| candidates | 14,172 and climbing | 3,139 | **2,969** | **5,000 of 65,488 scored** |

**The eviction cost, measured on a like-for-like pair.** view1 at depth 1, same
queue, same single process, caches unbounded and then bounded to 60,000 entries:

| | unbounded | bounded to 60,000 |
|---|---|---|
| query cache hit rate | 97.8% | **98.2%** (0 evictions — it never reached the bound) |
| pattern cache hit rate | 43.7% | **27.8%** (314,522 evictions) |
| peak memory | 0.62 GB | **0.53 GB** |
| candidates | 2,969 | 2,969 |
| **candidate hash** | `e440595e…` | **`e440595e…` — identical** |

So the price of the bound at depth 1 is **15.9 points of pattern-cache hit
rate**, and the query cache pays nothing because view1's distinct scopes fit
inside the bound. What it buys is a hard ceiling instead of a growth curve.
The important column is the last one: **eviction changes cost, not answers.**
(The elapsed time of the bounded run is not quoted, because it was measured
while the depth-2 run held five cores; the hit rates and the hash are not
affected by that, and the timing would be.)

At depth 2 the same bound is doing much heavier work — 7.0 million query
evictions and 12.7 million pattern evictions, and a pattern-cache hit rate of
14.8% — and that is the trade the machine required: 0.57 GB per worker over the
whole queue, against the 3.94 GB one unbounded process reached over 1.7% of it.

**Parallel throughput.** view1 at depth 2 sustained **146.0 scopes/s across five
workers** where one unbounded process had managed 25.6, and the five workers
finished within 8% of each other on a queue sharded 487/488/488/488/487 — the
longest-first grouping did its job. The comparison is not a clean speedup
measurement, because the depth-2 run changes three things at once against every
earlier figure (worker count, cache bound and depth); what it establishes is
that the configuration drains, which is what T4 asked for.

### 3.3 D26c — found, and fixed at the root

**The cause is not in the engine.** Two builds of the pack, run back to back
from the same `Data/`, produce `view2_geo_month_cube.parquet` files with
different SHA-256 hashes and **different row orders**; sorting both frames by
the view's grain makes them equal, and the unsorted frames are not equal.
view1's and view3's Parquet files are byte-identical across builds. DuckDB
writes view2's zero-filled cross join in whatever order its parallel hash join
finishes; group sums then accumulate in a different order, floats land a few
ulps apart, and candidates that tie on score swap places in a stable sort. That
is exactly the signature D26c describes — a candidate file that hashes
differently while the ranked output is byte-identical.

Two things were ruled out first, by measurement rather than by reading:
`PYTHONHASHSEED` was varied over three values with no effect on the candidate
hash, and two mines from the *same* Parquet file were already stable.

**The fix** is `load_view_frame`: the engine sorts the frame by every dimension
column in config order before mining, which is a total order on rows for all
three views. It is applied in the engine rather than in the view SQL because the
pack's views are outside this brief's writable set (E-8) — and it is the
stronger place for it, since the engine now cannot depend on its input's row
order whoever writes it.

### 3.4 The determinism gate

`handoffs/WPD2_calibration/check_determinism.py`, **all green**:

| stage | what it proves | result |
|---|---|---|
| 1. two runs, same view | content hash AND candidate-file bytes identical, all three views | 6/6 PASS |
| 2. 4 workers vs 1 process | identical content hash and candidate count; view1 on the fixed subset of its 40 highest-impact subspaces (2,240 candidates), view2 and view3 whole | 6/6 PASS |
| 3. two BUILDS of view2 | different Parquet files (`aa5cf4aa…` vs `830f5ba8…`), identical candidates (`007731eb…`) | 2/2 PASS |

Stage 3 is the one that closes D26c: it reproduces the actual cause rather than
the symptom. Stage 1 alone would have passed before the fix.

---

## §4 The depth-2 sample run — it drained

The operator's standing ask, run on the local machine with the A1 exclusions and
the T3 scaling in place:

```
python Insights/src/phase4b_engine.py --views view1 --depth2 --workers 5 \
       --cache-max-entries 60000 --dedup-max-entries 600000 --suffix _depth2
```

| | WP-D2's depth-2 attempt | **WP-D2c** |
|---|---|---|
| subspaces enumerated | 13,495 | **13,495** (1 + 172 + 13,322) |
| retained after the 1% impact prune | 2,438 | **2,438** |
| **data scopes behind them** | 880,752 | **809,554** — A1 removes 71,198 (−8.1%) |
| budget | 18,000 s (escalated) | 36,000 s |
| **elapsed** | stopped at 585.6 s, 1.7% done | **5,544.0 s — the queue emptied** |
| throughput | 25.6 scopes/s | **146.0 scopes/s** across 5 workers |
| patterns found | 17,290 at 15,000 scopes | **623,023** |
| HDPs evaluated / skipped | — | 1,249,810 / 1,101,938 (46.9% dedup) |
| query / pattern cache hit rate | — | 96.2% / 14.8% |
| cache evictions | n/a (never evict) | 6,997,130 query / 12,713,115 pattern |
| **peak memory** | **3.94 GB in one process**, 0.38 GB machine free | **0.57 GB per worker**, ~2.85 GB across five |
| candidates | 14,172 and climbing, unscoreable | **5,000 kept, 60,488 dropped below the cap** |
| top score | — | **0.8760** |
| candidate hash | — | `2bfbc790281a695cbb16c1a108b79abe` |

**The drain proof** is the loop's own exit condition — `Queue drained: True`,
809,554 of 809,554 scopes, 5,544 s against a 36,000 s budget. All 17 dimensions
and all 24 measures were kept.

**Both of D25's walls are gone, and the memory one was the larger of the two.**
The 3.94 GB that stopped WP-D2 was one process holding never-evict caches over
1.7% of the queue; five bounded workers held 0.57 GB each over 100% of it, on a
machine with **2.3 GB free at launch and 0.37 GB at its tightest** — this run
would not have fitted without the bound. And the "~800,000 projected candidates
against a 5,000 pre-filter" turns out to be 65,488 scored candidates, of which
the store keeps exactly the 5,000 the ranker reads.

**The candidate store is at its bound**, which is where the losslessness
argument has to be exact rather than approximate. Each worker kept its own top
5,000; the merge took the global top 5,000; the ranker's prefilter is 5,000. A
candidate in the global top 5,000 is necessarily in its own worker's top 5,000,
so the merge loses nothing, and the prefilter would have discarded everything
the store did. The 60,488 dropped candidates could not have reached the ranked
list.

### 4.1 The findings that are new at depth 2

Ranking the depth-2 candidates (4,116 after 884 twin merges) gives a top-15 of
which **nine are new** — they are not in the depth-1 top-15 by pattern type,
measure, breakdown, extending axis, subspace and highlight. They are flagged
`new_in_this_run = yes` in `v4_depth2/labeling_sheet.csv` and marked **NEW IN
THIS RUN** on the findings pages. view2 and view3 are unchanged (their configs
are depth-1 at both scales).

**These are the three-way findings the operator asked for.** A depth-2 data
scope carries two filters, one of which is the dimension the HDP varies along,
so what a reader sees is a slice, a dimension varied inside it, and a breakdown:

| rank | new finding | the three-way shape |
|---|---|---|
| 1 | `overspend_vs_plan` spread evenly across blocks, in 27 of 28 asset categories | **within costed activities** |
| 3 | Codes 101 and 105 lead untied funding across output types, in 19 of 20 GPs | **within Public Works** |
| 4 | Uncategorised is the largest asset category in 19 of 20 GPs | **within Public Works** |
| 5 | Activity Approved has the lowest overspend against plan, in 18 of 20 GPs | **within costed activities** |
| 6 | WORK ONGOING takes the majority of general-component spending, in 18 of 20 GPs | **within costed activities** |
| 8 | Theme 6 leads untied funding in 18 of 20 GPs | **within costed activities** |
| 9 | Code 101 has the lowest overspend against sanction, in 19 of 20 GPs | **within New/Fresh works** |
| 10 | Code 101 takes the majority of photo uploads, in 19 of 20 GPs | **within New/Fresh works** |
| 12 | Drinking water and sanitation lead tied funding across all beneficiary categories | **within costed activities** |

Six of the nine restrict to `is_costless = Costed` or `activity_type_label =
Public Works` — which is the honest first observation about them. Those two
slices are where the money is, so conditioning on them sharpens a finding
(19 of 20 Gram Panchayats rather than 18) without changing its subject. **Two
are genuinely new subjects**: rank 9 and rank 10, both restricted to New/Fresh
works and both about output Code 101, which the department has still not
decoded. Whether the extra specificity is worth the depth is a calibration
question, and it is the question v4 exists to put.

**The gates hold on the depth-2 output.** The regression gate is green on all
four classes (`v4_depth2/regression_output.txt`), and the four report checks are
green over a regenerated three-section report — 680 / 633 / 571 words, prose
gate clean, caveat exact both ways, **85 of 85 figures traced**. The four
labelled-spurious findings that survived at depth 1 survive at depth 2 as well,
in the same form; depth changes what else is available, not that.

---

## §5 The packages

**v3 — `handoffs/WPD2_calibration/`** — the depth-1 run, and what the committed
configuration reproduces. 32 findings (15 / 15 / 2) against v2's 33 (15 / 15 /
3). The sheet gains three columns: `merged_twin`, `framing_applied` and
`new_in_this_run`. Across the 32 findings the deterministic rules fired 16 times
for size shares, 5 for the linkage framing, 3 for the EVENNESS reframing, 2 for
the per-GP-month companion, 2 for the FY 2023-24 caveat and once for a twin
merge. Two new re-runnable checks ship with it —
`check_calibration_regression.py` and `check_determinism.py` — alongside the
archived outputs of all four gates.

**v4 — `handoffs/WPD2_calibration/v4_depth2/`** — the depth-2 run, complete and
self-contained: its own README, sheet (nine rows flagged `new_in_this_run`),
findings pages, regenerated report in both formats, mining and ranking
transcripts, and its own regression and report-check outputs. view2 and view3
are unchanged there and are included so the package can be read on its own.

The split is deliberate and is E-13: the main directory has to be the one a
reader can regenerate from the tree, and `--depth2` is a flag rather than the
shipped configuration.

**Also delivered:** `Insights/domain_pack_prdw/known_events.csv` (new pack
input, with a README section) and the regenerated
`Insights/reports_prdw/executive_metainsight_report.{md,pdf}` at depth 1.

---

## §6 Decision journal

**E-1 · `evaluate_trend` returned a direction it had not measured, and fixing
that emptied A7's displacement list.** `scipy.stats.spearmanr` on a constant
series returns NaN for both rho and p. Every comparison against NaN is False, so
`if p >= 0.05 or abs(rho) < 0.5: return None` never fired, and `rho > 0` was
also False, so the evaluator returned **DECREASING**. That is the whole
mechanism behind "n_completed is decreasing across 17 of 20 Gram Panchayats" on
a column with 17 events in it. The brief did not ask for this fix; A7 asked for
a support guard, and the guard would have displaced those candidates into the
data-quality list, which is literally what the ruling describes.

I fixed it anyway, and the consequence had to be handled: with the NaN hole
closed, the three candidates are never built, so nothing is displaced and the
data-quality list would have been **empty** — the finding would have vanished
silently, which is the one thing the operator ruled against. So the data-quality
record has two halves (§1, A7): the displacement path, and a support profile
measured directly off the view whatever the mining produced. The second half is
what surfaces `n_completed`, and it does so with counts rather than with a
NaN-derived trend direction. *Reversal cost:* four lines in `evaluate_trend`;
the profile stands either way.

**E-2 · The A1 audit was widened after the first re-mine, because the first
version let a definitional pair into rank 5.** The initial rule was "all
non-zero mass in ONE dimension value". `fund_abandoned_total × status_label`
failed it — 19 rupees of abandoned-work funding sit on WORK ONGOING rows — and
"WORK ABANDONED accounts for the majority of fund_abandoned_total" duly appeared
at rank 5 of the new top-15. Rule A (§1) replaced the strict test with a
coverage test carrying a 1% tolerance, which caught it and `is_started ×
status_label`, taking the list from 30 pairs to 32. The re-mine was repeated.
*Reversal cost:* two entries and a re-mine.

**E-3 · The A7 fraction moved from 0.5 to 1/3 after a sweep, not before it.**
0.5 was my first guess and it displaced twelve view2 candidates that were single
Gram Panchayat monthly cash series with 34 to 56 non-zero months out of 72 —
real series. The sweep (§1, A7) showed the answer is flat between 0.25 and 1/3
at zero displacements, and that `n_completed` fails at every value because it
cannot clear the absolute floor. 1/3 is the top of the flat range. *Reversal
cost:* one constant; the sweep is in the config comment and re-runnable.

**E-4 · The size-share block was generalised from geography to every categorical
breakdown, which is more than A1 asked for.** Session 1 labelled two view1
findings spurious with the note "size artifact: unspent money sits where most
activities sit" — `overspend_vs_plan` by `status_label` and by
`work_type_label`. Those are the geography confound exactly, on a non-geography
axis, and the machinery to show it already existed and was switched off for
them. The alternative was to leave the reader with a total and no denominator on
precisely the findings the operator had already flagged. In scope: the brief
lists `phase5b_report.py` (templates, framing rules) as writable, and this is a
framing rule. **16 of the 32 findings now carry it.** *Reversal cost:* one
predicate; the rule text mentions groups rather than places and would need a
sentence back.

**E-5 · The intensity companion is attached to measure-extending findings too.**
`stats` for a measure-extending HDP is a note rather than a distribution,
because the aggregation is ambiguous across members. The size confound is not
ambiguous — "Ganjam has the highest (varies) among district_name values" is a
place ranking whatever it ranks on — so the volume shares and, where a member
has one, the per-GP-month companion are attached even there. Without this, the
one finding A4 was written for would have reached the writer with no figures at
all. *Reversal cost:* one block in `enrich_candidates_with_stats`.

**E-6 · `phase4b_engine.py`'s stale view1 budget is fixed, and the file gained a
command line.** D26 authorised the edit (WP-D2b E-1). `("view1", VIEW1_CONFIG,
18000)` is now a 3,600 s budget — twelve times the measured drain — and the
thirty-line escalation comment is replaced by one that records that D25 reversed
the decision it argued for, with a pointer to where the argument lives. The
run-list also became `--views`, `--workers`, `--top-k`, `--cache-max-entries`,
`--dedup-max-entries`, `--subspace-limit`, `--depth2`, `--budget` and
`--suffix`, because T3 and T4 need to vary those without editing a config. That
is more than "one line and one comment block", and it is what stops the next WP
from needing another authorised edit to run the same file differently. *Reversal
cost:* the defaults reproduce the previous behaviour exactly.

**E-7 · `--depth2` is a flag, not a config edit.** `DISCOVER_SCALE` owns the
sample/statewide split (D15) and the depth-2 sample run is neither: it is one
deliberate deep run of the sample, which D25 defers rather than rejects.
Encoding it as a scale would have made the statewide branch mean two things.
*Reversal cost:* none; the flag is off by default.

**E-8 · D26c is fixed in the engine, not at its source.** The cause is measured
and it is not in the engine: two builds of `view2_geo_month_cube.parquet` hold
identical content in a different **row order** (proved — the raw frames differ,
the sorted frames are equal), because DuckDB writes that view's zero-filled
cross join in whatever order its parallel hash join finishes. The brief says
"fix with explicit sorts at the source". The source is the pack's view SQL,
which this brief also says DO NOT TOUCH. So the sort is applied where the engine
loads the frame, which is in scope and is the stronger place for it: the engine
can no longer depend on the row order of its input at all, whoever writes it,
and the two-build test in `check_determinism.py` proves it. A sort in the view
SQL remains worth adding when the pack is next opened. *Reversal cost:* one
function.

**E-9 · The HDP deduplication key became a 64-bit integer.** It was a tuple of a
frozenset of Subspaces, held in a set that reaches millions of entries per
worker at depth 2 — a large part of the never-evict memory this WP is bounding.
Collision risk over a few million HDPs is about one in ten million, and a
collision would drop one candidate, not corrupt one. The change is
output-neutral and was verified as such: all three candidate files hash
identically before and after it. *Reversal cost:* one function.

**E-10 · The executive report was generated twice, and only the second is
shipped.** The first run showed the A5 citation printing the COVID note twice in
view2's reading note — once for the change point, once for the fiscal-year
slice. The citation now emits one sentence per event. Rather than patch the
finished file, the whole report was regenerated, for WP-D2b E-4's reason: a
report no single run produced is one whose checks were run over two
generations. The depth-1 report was then generated a third time, because assembling package
v3 copied the depth-2 report over it — the same class of mistake as E-12, caught
by running the report checks against the shipped file rather than trusting the
copy. Every generation passed all four checks; the shipped depth-1 report is the
third (721 / 624 / 574 words, 89/89 figures traced) and the shipped depth-2 one
is its own (680 / 633 / 571 words, 85/85 traced). *Reversal cost:* two API calls.

**E-11 · Package v3 overwrote v2 in place, and two scripts joined it.**
`handoffs/WPD2_calibration/**` is in scope to regenerate and the operator needs
one labelling sheet, not three. `check_calibration_regression.py` and
`check_determinism.py` are new package tooling, following D-12's precedent that
re-runnable evidence ships beside the artefacts it verifies. `verify_configs_prdw.py`
and `build_labeling_sheet.py` were extended rather than replaced. *Reversal
cost:* re-run the README's steps 2–7.

**E-12 · I overwrote the operator's labelled sheet, and the fix is structural
rather than an apology.** `build_labeling_sheet.py` writes `labeling_sheet.csv`
with an empty `label` column, and it writes it into the directory where session
1's labelled copy lived. Rebuilding the package destroyed those labels. They
were recovered with a **read-only `git show HEAD:…`** — the only git command
this WP ran, no staging, no commit, no working-tree change — and the labelled
copy now lives beside the session record as
`CALIBRATION_SESSION_1_labels.csv`, which nothing writes.
`check_calibration_regression.py` reads THAT by default, so the baseline and the
working sheet are different files and a package rebuild cannot take the
baseline with it. The regression outputs shipped in both packages were
regenerated against the recovered file. *Reversal cost:* none; the recovery is
verified — 33 rows, 15 real / 7 already-known / 11 spurious, matching the
session record's tally exactly.

**E-13 · v3 is the main package and v4 sits inside it.** Two packages, one
directory, and the brief asks for both. `handoffs/WPD2_calibration/` holds
**v3**, the depth-1 run, because that is what the committed configuration
reproduces: D25 sets the sample to depth 1 and nothing here changes it, so the
main sheet and the shipped `executive_metainsight_report.md` must be the ones a
reader can regenerate from the tree. **v4** — the depth-2 run — is complete in
`v4_depth2/`, with its own README, its own report and its own gate outputs. The
alternative, v4 in the main directory, would have shipped a report and a sheet
that no command in the README produces. *Reversal cost:* a directory move.

**E-14 · Proceeded on an uncommitted tree, again.** WP-D2b's E-6 disclosure
stands: the `Insights/src` edits from WP-D2/WP-D2b were still working-tree
modifications when this WP started, so this run builds on an uncommitted base.
Nothing here depends on the commit. Disclosure, not a decision. *Reversal cost:*
none.

**E-15 · The `.env` was used, not created or read out.** `Insights/.env` exists
(operator, D-2) and was copied into the mirror so the report step could load it
there. The key was never printed, echoed or written anywhere, and `Chatbot/.env`
was not touched. *Reversal cost:* none.

---

## §7 Self-audit

**Verified by running it:**

- The three view builds, from `Data/` + the pack, `--strict`, 0 failed checks.
- All three mines, twice each, plus the parallel runs — every number in §2 and
  §3 is read from a transcript, and the memory figures come from `psutil` inside
  the mining processes.
- The determinism gate, whole: 6 stability checks, 6 single-versus-parallel
  checks, and the two-build test that reproduces D26c's actual cause.
- The ranking, including the twin merge, over all three views.
- The report generation, one run, three sections plus the deterministic annex.
- The four report checks (13 checks), the config gate (176 checks) and the
  regression gate (15 checks), all archived in the package and re-runnable.
- The A1 audit and the A7 sweep, as scripts over the built views; both tables in
  §1 are their output.
- The A4 extremum table, computed directly from view2's Parquet.
- The labelling sheet: 32 rows, 15 / 15 / 2 by view, `label` empty on every row,
  the FY caveat flag on exactly the two findings the predicate fires on.

**Not verified — relied on prior work:**

- WP-D1's reconciliation and `check_ask_parity`. Not re-run.
- That `Data/` equals the DuckDB the Ask chatbot serves (PM-validated, plan §5.5).
- The statewide branches. They are constructed at import and asserted by the
  config gate at both scales, and they have never seen statewide data.
- WP-D2's model probe. `gpt-5.6-sol` used as pinned; no new probe.
- The prose of the report is one generation. Its figures are checked
  mechanically (89/89) but its sentences are not re-derived by hand as WP-D2b
  did for fifteen view1 claims.

**Known weaknesses in what was delivered:**

- **Four labelled-spurious findings still say the same thing** (§2.4). Three are
  framed rather than removed; one is view3's near-empty candidate pool.
- **view3 has two findings.** At sample scale, after A7, this view supports
  almost nothing. WP-D2b's open question 5 is now sharper, not answered.
- **The A1 exclusion list is a sample-scale measurement.** The two rules are
  general, but the 32 pairs were audited against a 20-GP drop; some may be
  artefacts of it (`fund_tied_total × sanctioned_scheme_name` is confined to one
  scheme here and might not be statewide). The audit is a script and should be
  re-run when the statewide drop lands.
- **The two intensity measures produce no extremum findings**, for the measured
  reason in §1 (there is no extremum per GP-month). They earn their place as
  exceptions and as a companion figure rather than as findings of their own.
- **`n_abandoned` appears in the data-quality annex** on a majority-of-series
  test. It is a weaker case than `n_completed` and a reader may find it noise.
- **Eviction is measured on this drop only.** The hit-rate cost quoted in §3 is
  view1's; a view with a different subspace-to-scope ratio would pay differently.
- `phase5c_gamma_reports.py` and `gamma_sensitivity.py` still carry AP prompt
  text, unchanged and unrun — WP-D3's to convert.

**Files this WP touched, and no others:**

```
Insights/src/phase2_engine.py            (config fields, A1/A3/A7 machinery,
                                          TopKStore, canonical ordering, bounded caches)
Insights/src/phase4a_engine.py           (A4 measures, the NaN trend fix, re-exports)
Insights/src/phase4b_engine.py           (parallel mining, data-quality record,
                                          canonical frame load, the E-6 budget fix, CLI)
Insights/src/phase5_ranking.py           (A2 twin merge, A3 template)
Insights/src/phase5b_report.py           (A3/A4/A5/A6/A7 framing, glossary, annex)
Insights/domain_pack_prdw/known_events.csv   (new; A5)
Insights/domain_pack_prdw/README.md          (the known_events section)
Insights/reports_prdw/executive_metainsight_report.{md,pdf}   (depth 1)
handoffs/WPD2_calibration/**             (package v3, regenerated in place;
                                          v4_depth2/ added; check_calibration_
                                          regression.py and check_determinism.py
                                          added; CALIBRATION_SESSION_1_labels.csv
                                          added — the recovered baseline, E-12;
                                          verify_configs_prdw.py and
                                          build_labeling_sheet.py extended)
handoffs/WPD2c_REPORT.md                 (this file)
```

`git status` at the end of the run shows exactly those, plus three files that
were already modified when this WP started and are not mine: `.claude/settings.json`,
`PROJECT_PLAN.md` and the untracked `handoffs/WP4c_fix_and_rerun.md`.
`CALIBRATION_SESSION_1.md` is unmodified.

Everything else executed in a local mirror under the session scratchpad. No git
state was changed; the one `git show` was read-only (E-12). `prose_gate.py`, the pack's views / validation /
crosswalk, `Data/`, `Chatbot/`, `eval/`, `.env` contents, `discover_config.py`
and `phase5c_*` were not touched.

**What the PM should decide:**

1. **The four surviving labelled-spurious findings** (§2.4) — is the framing
   enough, or should a size-artifact suppression rule be written? That is a
   ranking change and it needs authority.
2. **view2 #7's label.** It is a PM proposal the operator has not confirmed, and
   the mechanism it would need (competing seasonal periods) is not in this WP.
3. **view3 at sample scale**, now with two findings. Open question 5, third time
   of asking.
4. **Whether depth 2 becomes the sample default.** It drains in 92 minutes on
   this machine and the numbers are in §4. D25 deferred rather than rejected
   it, and the two reasons it gave — the memory wall and the candidate volume
   — are both measured away. What is left is the calibration question of
   whether a conditional finding is worth more than an unconditional one, and
   `v4_depth2/` exists so that session 2 can answer it from the findings
   rather than from the arithmetic.
5. **The statewide depth-2 question** (D26 (d)). This run says the engine can
   hold 809,554 scopes on a loaded 16 GB laptop. Statewide is a different
   order of magnitude and this is evidence, not a green light; the honest next
   step is to run the same probe against a statewide drop when one exists.

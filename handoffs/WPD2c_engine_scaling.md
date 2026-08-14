# WP-D2c — Calibration actions, engine scaling, the depth-2 run (handoff brief)

**Workstream:** Discover. **For:** the operator-controlled implementation agent.
**Precondition:** tree committed (incl. the labeled `labeling_sheet.csv` and
`CALIBRATION_SESSION_1.md` — they are this brief's specification); local mirror;
`Insights/.env` present. **Read first:** `handoffs/WPD2_calibration/CALIBRATION_SESSION_1.md`
(actions 1–7 — the operator-ratified spec), `handoffs/WPD2b_REPORT.md` (§2 measured
rates, E-1), `PROJECT_PLAN.md` D25–D27.

**Files in scope:** `Insights/src/phase2_engine.py`, `phase4a_engine.py`,
`phase4b_engine.py` (now writable — incl. the stale view1 budget line, E-1/D26),
`phase5_ranking.py` (dedup/overlap only — ranking math otherwise untouched),
`phase5b_report.py` (templates, framing rules, glossary additions),
`Insights/domain_pack_prdw/known_events.csv` + a README note (new reference
input — authorized pack addition, D5 pattern: events as data, not code),
`Insights/reports_prdw/**`, `handoffs/WPD2_calibration/**` (package v3),
`handoffs/WPD2c_REPORT.md`.
**DO NOT TOUCH:** `prose_gate.py`, pack views/validation/crosswalk, `Data/`,
`Chatbot/`, `eval/`, `.env` contents, `discover_config.py`, `phase5c_*` (WP-D3).

## Objective

The seven calibration actions are engineered in; a depth-1 re-mine passes the
new **regression gate** against the labeled baseline (this closes WP-D2's
workstream gate); the engine then scales (parallel mining, bounded memory,
streamed candidates); and the **full depth-2 sample run for view1 completes** —
the operator's standing ask. Output: calibration package v3 + regenerated
report.

## Tasks

### T1 — Calibration actions (session record actions 1–7; that doc is the spec)

- **A1 `excluded_pairs`** on `ViewConfig`: list of (measure, dimension) pairs
  skipped at scope generation. Populate from the session + your own audit of
  the same class (child-table measures structurally tied to one dimension
  value): at minimum `trainees_total`/`training_days`/`beneficiaries_expected`
  × `work_type_label`, `fund_tied_total`/`fund_untied_total` ×
  `fund_component_name` and × `tied_untied`. Report the full audited list.
- **A2 twin dedup**: OUTSTANDING_1 + ATTRIBUTION candidates with identical
  (subspace-family, highlight, member set) merge into one before ranking
  (keep the higher-scored; record the merge on the candidate). Document any
  overlap-weight change separately — ranking math changes are otherwise out.
- **A3 EVENNESS template**: for signed money measures, lead with magnitude and
  absence-of-concentration ("the shortfall belongs to everyone — no
  {breakdown} stands out"); the exception clause must state it is about the
  *spread*, not behavior. Deterministic template + one phase5b framing rule.
- **A4 intensity measures**: add AVG-agg variants to view2
  (`payment_amount_mean`, `receipt_amount_mean` per GP-month row) with the
  Appendix glossary entries below; report (don't silently change) the
  `extremum_ratio` implication — 0.67 stays unless you can show it starves
  the new measures, in which case escalate with numbers.
- **A5 known-events table**: `known_events.csv` (event, start_month,
  end_month, note) seeded with COVID first-wave lockdown 2020-03..2020-06 and
  a `TODO(SME)` row format for more (cyclones, elections — operator supplies).
  Reading notes cite an event deterministically when a CHANGE_POINT date or
  trend window overlaps it. Never model-generated.
- **A6 linkage framing rule**: findings on `activity_linked_expenditure`
  trends carry the recording-completeness framing (links grew 30 → 2,122/FY
  while payments stayed flat) — deterministic rule keyed to the measure.
- **A7 degenerate guard**: temporal patterns require minimum non-zero support
  (propose the threshold from the data; `n_completed`'s 17 events must fail
  it). Displaced findings are LOGGED to a data-quality list in the report
  output, not silently dropped — the operator ruled these stay visible as
  data-quality, so the executive report's reading note for view3 keeps the
  completion-recording-ceased statement.

### T2 — Depth-1 re-mine + regression gate  *(closes WP-D2's workstream gate)*

- Re-mine all three views (depth-1 view1), re-rank, regenerate the report,
  re-run the four WP-D2b checks. Write `check_calibration_regression.py`
  (lives in `WPD2_calibration/`): reads the labeled sheet, asserts no
  labeled-spurious **class** appears in any top-15 (excluded pairs absent,
  ATTRIBUTION twins merged, sub-support temporal findings absent, size-total
  place rankings carry the intensity companion or the size-share framing).
- **Done when:** regression green + four checks green + package v3 built.

### T3 — Engine scaling

- Parallelize mining across subspaces (process pool; shard the priority queue;
  per-worker caches — sharding preserves locality); bound memory (eviction or
  spill — measure the hit-rate cost and report it). **Candidate store: a
  score-ordered top-K heap, K defaulting to the ranking prefilter's existing
  5,000 cap (configurable; operator may lower it).** At K = the prefilter cap
  this is LOSSLESS — ranking already reads only the top 5,000 by score, so the
  final top-15 is provably identical while the unbounded candidate
  accumulation (the ~800k-pile wall) disappears. Do not default lower: raw-
  score top ranks cluster near-twins (calibration session 1), and the greedy
  ranker needs breadth below them to find diverse candidates. In parallel
  mode, per-worker heaps merge at the end (K per worker, then global top-K).
  Start from the measured 185.9 scopes/s single-core figure (WP-D2b §2), not
  WP-D2's 15/s.
- **Determinism is the gate:** identical candidates (canonical ordering,
  content hash) between single-process and parallel runs on a fixed subset;
  and **find + pin the view2 hash nondeterminism** (D26c — suspects:
  collection iteration order, Parquet row order; fix with explicit sorts at
  the source, and prove all three views now hash stably across two runs).
- Fix `phase4b_engine.py`'s stale view1 budget line + escalation comment
  (E-1, authorized).

### T4 — The depth-2 sample run (view1)

- With T1's exclusions and T3's scaling: run view1 at
  `max_subspace_depth = 2`, full 17-dimension config, on the local machine.
  Report queue size (exclusions will have shrunk the 880,752), wall time,
  peak memory, candidate count; rank via the prefilter cap; regenerate report
  + package **v4** marking which top-15 entries are new-at-depth-2 (these are
  the three-way findings the operator asked for — flag them for calibration
  session 2).
- **Done when:** queue drains, determinism holds, regression gate still green,
  and the depth-2-only findings are separately listed for the operator.

## Cut-line

T1+T2 are the core — WP-D2's gate must close even if scaling slips. T3+T4 are
one unit (the depth-2 run without the determinism gate is not shippable).
Never ship T4 output that fails T2's regression gate.

## Escalation / gate / report

- **STOP:** regression gate fails after T1 (a spurious class survives its own
  fix); determinism cannot be established; depth-2 exceeds machine memory even
  with eviction (report the measured ceiling — the cloud decision returns to
  the operator with real numbers).
- **Gate:** (1) actions 1–7 in with evidence each; (2) regression + four
  checks green on the depth-1 re-mine; (3) determinism proven, hash stability
  across two runs on all views; (4) depth-2 drains with metrics; (5) packages
  v3/v4 delivered; (6) no out-of-scope file touched, no git.
- **Report:** `handoffs/WPD2c_REPORT.md` — §0 gate table · §1 actions 1–7
  evidence · §2 re-mine + regression results · §3 scaling design + measured
  determinism/memory/throughput · §4 depth-2 run metrics + the new-findings
  list · §5 decision journal · §6 self-audit.

## Appendix — glossary entries for the intensity measures (transcribe verbatim)

- `payment_amount_mean`: UNIT: rupees, AVERAGED per GP-month. The same rupee
  column as payment_amount, normalised by GP-months: the typical monthly
  outflow of one Gram Panchayat in the group, independent of how many GPs or
  months the group contains. Use this, not the total, to compare places of
  different size.
- `receipt_amount_mean`: UNIT: rupees, AVERAGED per GP-month. As
  payment_amount_mean, for inflows.

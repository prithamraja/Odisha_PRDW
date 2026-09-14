# WP-D11 brief — `gp_profile`: GP attributes on every view, plus `view4_gp_profile`

**Workstream:** Discover. **Nature: BUILD, gated — a pack extension, a new
view, a re-mine, and a full edition regeneration.** **Authored:** PM,
2026-09-07, executing the operator-signed **Amendment B**
(`Insights/DISCOVER_VIEW_MAPPING.md` §12, decisions B1–B5 all signed
2026-09-07). Decision number for the sign-off: **D60** (block D60–D69
claimed in the D30 governance row). Not yet registered as a row in
`PROJECT_PLAN.md` §4.

**For:** the operator-controlled implementation agent.

**Files in scope (you may write ONLY these):**
`Insights/domain_pack_prdw/**` (extend), `Insights/src/phase2_engine.py`
(the `VIEW*_CONFIG` block and a new `VIEW4_CONFIG` only), the view-list /
title / glossary / description tables in `Insights/src/phase4b_engine.py`,
`phase5_ranking.py`, `phase5b_report.py`, `phase5c_global_feed.py`,
`phase5e_insight_prose.py`, `phase5d_retrieval_corpus.py`,
`phase5f_decompose.py`, and `DiscoverChat/glossary.py` (each: the place a
fourth view is enumerated, nothing else), `Insights/metainsights/**`,
`Insights/reports_prdw/**`, `handoffs/WPD11_REPORT.md`,
`handoffs/WPD11_calibration/**` (new).

**DO NOT TOUCH:** `Data/**` (read-only input; `gp_profile.csv` is untracked
— leave it, the operator commits it), `Insights/DISCOVER_VIEW_MAPPING.md`
(signed spec — propose amendments in your report), `handoffs/PROJECT_PLAN.md`,
`Ask/**`, `frontend/**`, `deploy/**`, `.env`, any `.duckdb`, engine
*algorithms* (pattern evaluators, ranking, caches — config only), the
`CONSOLIDATING_WRITER_PROMPT` and judge prompts in `DiscoverChat/`.

**Preconditions — verify all; if any fail, STOP and flag in your report:**

- [ ] `Data/gp_profile.csv` present: 20 rows, 99 columns, `basic_info_lgd`
      matches `gram_panchayat.gp_lgd_code` 1:1 (PM-verified 2026-09-07).
- [ ] `Insights/DISCOVER_VIEW_MAPPING.md` §12 present with B1–B5 marked
      approved/ruled. The two files the PM edited on 2026-09-07 (the mapping
      doc and `PROJECT_PLAN.md`) may still be uncommitted — that is expected
      and not a blocker; any OTHER uncommitted change in `Insights/`,
      `DiscoverChat/` or `handoffs/` is: ask the operator.
- [ ] **Sweep `C:\dev\odisha-*` first.** Earlier WPs found finished work
      living only in un-copied-back mirrors (WP-D6 lesson). Confirm nothing
      profile-related already exists there before writing a line.
- [ ] Local mirror of `Insights/`, `Data/`, `DiscoverChat/` outside the
      Drive mount; DuckDB and the engine never run from the Drive path.
- [ ] `Insights/.env` carries a live `OPENAI_API_KEY` and `NOVITA_API_KEY`
      (both were found dead once; probe with one call before the prose step).
- [ ] The current candidate set `a7f991c1df3771f9` and its stamps are what
      `Insights/metainsights/` holds — record their hashes before you
      overwrite anything (T7 regenerates everything).

**Read first — each earns its place:**

| Document | Why |
|---|---|
| `Insights/DISCOVER_VIEW_MAPPING.md` **§12** | The spec. §12.2 roles, §12.3 dimension definitions and cut points, §12.4 view4 columns, §12.6 defects you must expect. Where it is specific you have no design freedom. |
| `Insights/DISCOVER_VIEW_MAPPING.md` §§3–7, §11 | The standing rules the amendment extends: money bases, no materialised rates, dimensions never zero-filled, the crosswalk roles, the sample↔statewide switch (§6). |
| `Insights/domain_pack_prdw/README.md` + `Insights/domain_pack/README.md` | Pack format, runner contract, the `--strict` rule ("declare only constraints that hold"). |
| `Insights/domain_pack_prdw/views/view3_gp_performance.sql` | The pattern view4 copies: master-first grid, LEFT JOINs, zero-filled measures, the Chikilli guard. |
| `Insights/domain_pack_prdw/build_crosswalk.py` | The crosswalk generator and its four gate checks — you extend `SPEC`, you do not hand-edit `crosswalk.csv`. |
| `handoffs/WPD1_domain_pack.md`, `handoffs/WPD2_mining_calibration.md` (+ Appendix A), `handoffs/WPD2c_engine_scaling.md` | How the pack, configs, glossaries and calibration gate were built. Your glossary entries follow Appendix A's form exactly. |
| `handoffs/WPD2_calibration/` | The labelled sheet that is the regression gate (T6). |
| `handoffs/WPD3_feed_editions.md`, `WPD4b_prose_production.md`, `WPD5_retrieval_chatbot.md`, `WPD6_decompose.md`, `WPD10_corpus_footprint.md` | The downstream steps you regenerate in T7, and their determinism / budget rules. |
| `ODISHA_PRDW_METAINSIGHTS_HANDOFF.md` §4 | The inherited lessons: Drive temp files, token budgets, regenerate-all-editions-together, "is the measure wrong or the target unreachable". |

---

## Objective

`domain_pack_prdw` stages `gp_profile`, derives seven GP attribute
dimensions, appends them to views 1–3, and builds a fourth GP-grain view —
all under `--strict`, with the crosswalk gate proving no excluded column
reaches any Parquet. The engine mines all four views with the new
dimensions, the ranked findings pass the regression gate, a calibration
package is delivered for the operator, and every published artefact (feed,
gamma editions, insight prose, both retrieval corpora) is regenerated from
the one new candidate set. Nothing is committed and nothing is pushed.

## Non-goals

- No engine capability work. In particular **no ratio measures**: the
  engine's measures are SUM or AVG of one column, and Amendment B §12.4
  explicitly defers per-capita *mining* to a separate engine WP. view4
  ships numerators and denominators.
- No leadership / elected-representative dimension (dropped, §12 preamble).
- No Ask-side `v_gp_profile` (§12.7 — Ask workstream item, logged only).
- No frontend change: the Discover page discovers sections from `## `
  headings, so a fourth section needs nothing from you. Do not touch
  `frontend/`.
- No data fixes. §12.6's defects are logged and reported, never repaired.
- No git operations; no Railway operations.

## Facts you need (provenance in parens)

1. **Join key:** `basic_info_lgd` (int in the CSV) ↔ `gram_panchayat.gp_lgd_code`
   (VARCHAR after the pack's cast). Cast the profile key to VARCHAR at
   staging; join on the VARCHAR form. 1:1, zero orphans either side (PM).
2. **Dimension definitions are fixed and signed** (§12.3): `social_composition`
   (ST > 50% → ST-majority; else SC > 50% → SC-majority; else Mixed),
   `gp_size` (population: < 2,500 / 2,500 to under 5,000 / 5,000 to under
   10,000 / 10,000 and above — lower bound inclusive), `remoteness` (bus stop
   < 5 km Near / ≥ 5 km Far), `digital_readiness` (internet AND computer at
   the bhawan both 'Yes' → Ready), `has_panchayat_bhawan`, `has_csc`,
   `plc_available` (materialised, mined statewide only). Null source →
   `'Not reported'`. Expected sample splits: 2/3/15, 2/9/7/2, 14/6, 10/10,
   14/6, 12/8, 18/2 — **reproduce these exactly** in your report; a
   different split means a boundary or a null was handled differently from
   the spec.
3. **Excluded columns** (§12.2): `basic_info_email_address`, `basic_info_mobile`,
   `basic_info_address`, `basic_info_gp_attractions` are `X-pii` — operator
   ruling; `panchayat_area_total_area` is `X-unreliable`; the three
   comma-separated multi-value columns are `X-multi`; the 19 PLC detail
   columns and three sparse location/connection columns are `X-sparse`;
   geography duplicates are `X-derived`; four constants are `X-const`. None
   reaches a Parquet.
4. **No profile measure on views 1–3** (§12.4). Population is a GP constant
   and would be summed once per activity / month / fiscal year. view4 is the
   only view carrying profile counts as measures.
5. **view4 grain = GP**, materialised from `stg_gram_panchayat` with LEFT
   JOINs only; lifetime performance measures are view3's expressions summed
   over the fiscal-year domain, so `SUM(view4.col) == SUM(view3.col)` for
   every shared column — that equality is a gate check. Post-view pin: 20
   rows, `unique_grain: [gp_lgd_code]`.
6. **Sample scale lives only in `sources.yaml` `expected_rows` and
   `validation.yaml` `post_view`** (D15). No literal 20 in any SQL.
7. **Engine facts that bite** (WP-D2c, WP-D10): view1 depth 2 drained in
   ~92 min on five workers with 17 dimensions; the candidate store cap
   `RANKING_PREFILTER_CAP` (5,000) already drops most depth-2 candidates —
   check it before blaming depth; view1's kept candidates carried NO temporal
   pattern types, cause unknown — do not "fix" it in passing, report whether
   it persists. Five workers must remain byte-identical to one.
8. **The regression gate** (WP-D2c): no class labelled spurious in
   `handoffs/WPD2_calibration/` may re-enter any top-15. The 32-pair
   definitional exclusion list, twin merge, EVENNESS/linkage/size framing and
   the degenerate-measure guard all still apply and must not be bypassed by a
   new dimension.
9. **Regenerate all editions together** (handoff §4; WP-D3b): feed, the five
   gamma editions, `insight_prose.json` + `insight_feed.md`, and both
   retrieval sidecars (`retrieval_corpus.*`, `decompose_corpus.*`) derive
   from one candidate set hash. A mixed set is a defect. The sidecars are
   committed artefacts in the WP-D10 spellings (`.json.gz` / `.npy` /
   `_stamp.json`) — produce exactly those.
10. **Prose budgets** (D17 / WP-D4b/c): verifier retry-on-empty exists;
    `verifier_budget_check` output must be read on the first build; the
    120-call cap per prose build stands. Every glossary entry for a new
    column must exist BEFORE the prose step, or the writer sees raw column
    names — WP-D6 measured that every finding sentence contains one.
11. **Known profile defects** (§12.6, expected — log them): area units
    mixed; Karuabahal 12 households; toilets > households in 5 GPs; tap
    connections > households in 2; children = 0 in 9; ST = 0 in 5; the
    destitute-homes column mixes homes and residents; `no_of_computer`
    constant 1.

## Tasks

### T1 — Stage the source (`sources.yaml`, `derived_columns.sql`)

- **Do:** add `gp_profile` to `sources.yaml` (`file: gp_profile.csv`,
  `expected_rows: 20`, explicit casts: every count column `int`,
  `basic_amenities_osr_collected_so_far` `float`,
  `panchayat_area_total_area` `float`, key columns VARCHAR). Write
  `stg_gp_profile` in `derived_columns.sql`: the join key cast to VARCHAR,
  the seven derived dimensions per fact 2, and the measure columns renamed
  to the §12.4 names. **Project no `X-*` column.**
- **Done when:** `SELECT * FROM stg_gp_profile` has 20 rows, 1 + 7 + ~44
  columns, and the seven dimension splits match fact 2.
- **Trap:** the CSV's sparse cells (379 of them, mostly the PLC block) are
  literal `NA` tokens that pandas reads as NULL by default — the runner's
  `all_varchar=true` read may NOT, leaving the string `'NA'`. Verify which
  you get and cast so that `'Not reported'` comes from a NULL, never from
  text, and no `'NA'` band appears anywhere.

### T2 — Views 1–3: append the dimensions

- **Do:** in each of the three view SQL files, LEFT JOIN `stg_gp_profile` on
  `gp_lgd_code` and project the seven dimension columns (and only those),
  with `COALESCE(..., 'Not reported')` so a GP without a profile row still
  carries a band. Place them after the geography block, before the domain
  dimensions. Update each file's header comment.
- **Done when:** row counts are unchanged (12,704 / 1,440 / 120), every
  existing column is byte-identical to the pre-change build (T5 checks
  this), and the seven new columns are present on all three.
- **Trap:** a fan-out. `stg_gp_profile` must be unique on the key — declare
  it as a PK in `validation.yaml` (T4) so a duplicate profile row statewide
  fails the build instead of doubling view1.

### T3 — `views/view4_gp_profile.sql`

- **Do:** master-first grid (`stg_gram_panchayat`), LEFT JOIN
  `stg_gp_profile`, LEFT JOIN a lifetime aggregate CTE built from the same
  `stg_*` expressions view3 uses (copy view3's `activity`, `plans`, `cash`
  CTEs without the fiscal-year key). Columns exactly per §12.4: six
  geography columns, seven dimensions, the profile measure family, the
  lifetime performance family. Measures zero-filled; dimensions never.
  Header comment states the grain, the no-ratio rule, and the SUM-equality
  guarantee against view3.
- **Done when:** 20 rows; `gp_lgd_code` unique; for every shared measure
  `SUM(view4) == SUM(view3)` exactly; Chikilli shows `n_admin_approvals = 0`
  with its profile populated.
- **Trap:** `n_plans` and cashbook amounts are attributed by their own
  fiscal year in view3 — sum them over the SAME fiscal-year domain, not over
  the raw tables, or the phantom `2026-2027` rows leak in.

### T4 — `validation.yaml` + crosswalk

- **Do:** PK `gp_profile: basic_info_lgd` and `stg_gp_profile: gp_lgd_code`;
  FK `gp_profile.basic_info_lgd → gram_panchayat.gp_lgd_code` (holds, zero
  orphans); categorical domains for the seven derived dimensions (closed by
  your own CASE construction — `'Not reported'` included); `post_view`
  entry for view4 (20 rows, `[gp_lgd_code]`). **Declare only constraints
  that hold**; for each §12.6 defect, decide whether any declared check
  would trip on it and record the answer. Extend `build_crosswalk.py`'s
  `SPEC` with all 99 `gp_profile` columns and the new output columns of all
  four views; add a fifth gate check: **no `X-pii` column name appears in
  any view's output columns** (operator ruling). Regenerate `crosswalk.csv`.
- **Done when:** `--strict` green; crosswalk 281/281 columns (182 + 99)
  with all five checks passing.

### T5 — Build + reconciliation gate

- **Do:** build the pre-change pack once and keep its four Parquets (three,
  plus nothing) as a baseline; then build the amended pack. Reconcile:

| Check | Target | Tolerance |
|---|---|---|
| view1 / view2 / view3 rows | 12,704 / 1,440 / 120 | exact |
| every pre-existing column of views 1–3 | identical to baseline (values and dtype) | exact |
| seven dimension splits on view4 | fact 2's splits | exact |
| view4 rows / distinct `gp_lgd_code` | 20 / 20 | exact |
| `SUM(view4.m) == SUM(view3.m)` for every shared measure | equal | exact |
| view4 Σ`population_total` / Σ`households` | 115,246 / 26,132 | exact (PM-measured from the CSV, 2026-09-07) |
| `X-pii` names in any Parquet schema | 0 | exact |
| view4 Chikilli `n_admin_approvals` | 0, row present | exact |
- Sync `reports_prdw/` (validation report + view profiles) back to
  `Insights/reports_prdw/`; Parquets stay local (gitignored).
- **Done when:** the table is filled with actuals; every non-exact delta
  traces to a §12.6 or §8 defect.
- **Escalate if:** any pre-existing column of views 1–3 changed. That is a
  regression in the base views, not a profile feature.

### T6 — Configs, glossaries, re-mine, re-rank, regression gate

- **Do:**
  1. `phase2_engine.py`: add the seven dimensions to `VIEW1_CONFIG`,
     `VIEW2_CONFIG`, `VIEW3_CONFIG` (sample: all except `plc_available`;
     statewide branch of the `_STATEWIDE` switch: all seven) and author
     `VIEW4_CONFIG` per §12.4 (depth 1 sample / 2 statewide; impact
     `population_total`, `n_activities`; every measure SUM). Comment each
     dimension with its definition and sample split, in the file's existing
     style.
  2. Enumerate view4 wherever the pipeline lists views: `phase4b_engine.py`
     (run list + a budget — start at view3's 120 s and raise only on a
     measured need), `phase5_ranking.py` `views`, `phase5c_global_feed.py`
     `VIEWS` + `VIEW_TITLES` (`"GP Profile"`), `phase5b_report.py`
     `VIEW_DESCRIPTIONS` (title, description, audience context, column
     glossary — PM-form as in WP-D2 Appendix A; **write the description
     from §12.4, no invented facts**), `DiscoverChat/glossary.py` `_CONFIGS`,
     and `phase5d` / `phase5e` / `phase5f` if they hold a view list.
     Glossary entries for all seven dimensions go into every view's glossary
     that carries them, and the ~60 view4 measures into view4's.
  3. Re-mine all four views with five workers. Record wall time per view and
     the depth-2 view1 cost against the ~92 min baseline. If view1 exceeds
     the available budget, **stop mining, report the measurement, and
     escalate** (B4: operator chooses the subspace-filter-only fallback);
     do not silently lower depth or drop dimensions.
  4. Determinism: one view (view2) mined single-process must be
     byte-identical to the five-worker output.
  5. Re-rank; run the WP-D2c regression gate against the labelled sheet.
- **Done when:** four ranked top-15s exist; regression gate reports 0
  re-entries; the run is reproducible (hash recorded).
- **Escalate if:** the gate fails on a class the new dimensions created —
  that is the calibration session's business, not yours to tune away.

### T7 — Calibration package + edition regeneration

- **Do:** `handoffs/WPD11_calibration/` with, per view, the top-15 findings
  in the WP-D2 labelling format (real / already-known / spurious columns
  blank for the operator), plus a one-page "what the profile dimensions
  changed" diff: which prior top-15 findings dropped, which new ones entered,
  and how many of the new ones involve a profile dimension. Then regenerate
  **everything** from the new candidate set: global feed, all five gamma
  editions, `insight_prose.json` + `insight_feed.md` (reading notes OFF, per
  D48-1), executive report + PDF, both retrieval sidecars in WP-D10
  spellings. Run `DiscoverChat/gates.py` (offline, then `--live`) and the
  unittest modules.
- **Done when:** every regenerated artefact carries the same candidate-set
  hash in its stamp/header; prose checker green; DiscoverChat gates green;
  API call and token counts recorded against the caps.
- **Trap:** `numerals-traceable` in the DiscoverChat gate is noisy
  (±15 across identical trees, WP-D10) — do not chase it.

### T8 — Report

- **Do:** `handoffs/WPD11_REPORT.md` per the spec below. No git operations.

## Cut-line

T1–T5 are one unit: a pack that does not build under `--strict` with the
crosswalk gate green is not a partial delivery. If T6's view1 re-mine must
be escalated on cost, deliver T1–T5 complete, the view2/3/4 re-mines, the
measurement, and STOP before T7 — a mixed edition set is worse than the
current one. Never regenerate a subset of editions.

## Escalation protocol

- **STOP and end the run:** preconditions fail; a pre-existing column of
  views 1–3 changes; the profile splits cannot be made to match fact 2
  without deviating from §12.3; the view1 re-mine exceeds budget (report
  and stop, B4); any `X-pii` column reaches a Parquet; the prose step's
  verifier shows silently empty sections.
- **Decide-and-document** (report §7 journal: decision / options / choice /
  reversal cost): cast micro-choices; column ordering; view4 budget;
  glossary wording; how a `'NA'` string is handled at staging.
- **Never:** fix data; add a ratio or per-capita measure; touch engine
  algorithms; mine with a subset of the signed dimensions without an
  operator ruling; commit; push; touch Railway.

## Gate (definition of done)

1. `--strict` build green from `Data/` alone; crosswalk 281/281 with the
   `X-pii` check passing.
2. T5 reconciliation table complete; views 1–3 pre-existing columns
   byte-identical to baseline; view4 ↔ view3 SUM equality exact.
3. Seven dimension splits reproduce fact 2 exactly.
4. Four views mined and ranked; five-worker output identical to
   single-process on view2; regression gate 0 re-entries; view1 cost
   measured and reported against the 92-minute baseline.
5. Every published artefact regenerated from one candidate set; prose
   checker and DiscoverChat gates green; calibration package delivered.
6. **Operator calibration session on the new top-15s** (labels real /
   already-known / spurious). Closes the WP. Thin bands on
   `social_composition` producing few or no findings in the sample is
   EXPECTED (B2) and is not a gate failure.

Gate holder: PM replays the build and the gate checks; operator holds
gate 6.

## Report spec — `handoffs/WPD11_REPORT.md`

- **§0 Status** — the six gate items, PASS / FAIL / PARTIAL / PENDING, one
  line of evidence each.
- **§1 Build** — command, environment, runtime, `--strict` outcome, the
  crosswalk gate output.
- **§2 Reconciliation table** (T5, actuals and deltas).
- **§3 Dimension splits** — the seven, sample counts, and any GP whose band
  depended on a boundary or a null.
- **§4 Mining** — per-view wall time, candidate counts, view1 cost vs
  baseline, determinism check, `RANKING_PREFILTER_CAP` effect, whether
  view1's missing temporal patterns persist.
- **§5 What changed in the top-15s** — the diff from T7; count of new
  findings that use a profile dimension; regression-gate output.
- **§6 Editions** — candidate-set hash, every regenerated file with its
  stamp, prose first-pass / regenerated / fallback counts, API calls and
  tokens against caps, DiscoverChat gate results.
- **§7 Decision journal.**
- **§8 Data oddities** — anything in `gp_profile` beyond §12.6.
- **§9 Proposed amendments** to the mapping doc, if the build taught
  something the spec got wrong (you do not edit the spec).
- **§10 Self-audit** — verified / not verified / what the PM should replay.

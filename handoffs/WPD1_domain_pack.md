# WP-D1 — `domain_pack_prdw/` (handoff brief)

**Workstream:** Discover (parallel to Ask — D14). **For:** the operator-controlled implementation agent.
**Files in scope (you may write ONLY these):** `Insights/domain_pack_prdw/**` (new — you author this), `Insights/reports_prdw/**` (build/validation reports synced back from the mirror), `handoffs/WPD1_REPORT.md`, `.gitignore` (add `views_prdw/` build-output entries only).
**DO NOT TOUCH:** `Insights/src/**` (the engine — WP-D2's problem, and even then config blocks only), `Insights/domain_pack/` and `Insights/domain_pack_rtgs/` (reference packs — deleted only after WP-D3, not by you), `Chatbot/`, `eval/`, `Data/` (read-only input), `Insights/DISCOVER_VIEW_MAPPING.md` (the signed spec — propose amendments in your report, never edit it), `PROJECT_PLAN.md`, `.env`, any `.duckdb`.

**Preconditions — verify all; if any fail, STOP and flag in your report:**

- [ ] Working tree clean; `Insights/DISCOVER_VIEW_MAPPING.md` is committed (it is the operator-signed spec, D22).
- [ ] `Data/` holds 19 CSVs; `gram_panchayat.csv` has 20 rows; `planned_activity.csv` has 12,704 data rows.
- [ ] You can create a **local mirror** (copy of `Insights/` + `Data/`) outside the Drive mount and run Python + duckdb there. DuckDB cannot spill temp files on Drive — never execute the build from the Drive path.
- [ ] No other agent is live on this working tree (the Ask workstream runs in parallel but is file-disjoint; if you see uncommitted `Chatbot/`/`eval/` changes, ask the operator before proceeding).

**Read first — each earns its place:**

| Document | Why |
|---|---|
| `Insights/DISCOVER_VIEW_MAPPING.md` | **The signed spec.** §4 = the three views you build; §3 = measures with bases; §5 = temporal rules; §7 = the column crosswalk you materialize; §8 = defects you must expect. |
| `Insights/domain_pack/README.md` | The pack format and runner contract, cast semantics, reproducibility rules. Binding. |
| `Insights/domain_pack_rtgs/` | Worked example: crosswalk mechanics, derived-columns style, validation.yaml shape. |
| `Data/create_views.sql` | The `v_*` definitions whose **semantics you re-express verbatim** in `derived_columns.sql` (D22; Ask↔Discover number agreement is the point of this workstream). |
| `ODISHA_PRDW_METAINSIGHTS_HANDOFF.md` §§2–4 | Pipeline context and the inherited lessons. |
| `PROJECT_PLAN.md` D14–D17, D19–D22 | The decisions this brief implements. |

---

## Objective

`Insights/domain_pack_prdw/` exists and builds three Parquet views under
`build_views.py --strict` from `Data/`, reproducing the signed mapping doc
exactly: same grains, same columns, same derivation semantics as
`create_views.sql`, reconciliation targets hit. The validation report (defects
logged, never fixed) is delivered. After this WP, WP-D2 needs only engine
config — no pack changes.

## Non-goals

- No `VIEW*_CONFIG` edits, no engine runs, no `discover_config.py` changes (WP-D2).
- No staging script — `Data/` per-table CSVs are the direct `--data-dir` input.
- No data fixes, ever. A wrong-looking number gets logged and reported, not repaired.
- No feed/report generation (WP-D3).

## Facts you need (provenance in parens)

1. **The mapping doc is operator-signed (D22).** Where it is specific, you have no design freedom; where it is silent, decide-and-document (see Escalation).
2. Derivation semantics come **verbatim** from `create_views.sql`: status flags via the dim_code decode (`variable` predicate + VARCHAR cast, TRIM/`chr(9)` cleaning), `authority_clean` CASE, `tied_untied` mapping (4249 Tied / 4211+4250 Untied / else Other), the `v_exp` per-activity rollup, the `ARG_MAX` scheme rollup. One deliberate delta: **`days_since_sanction` is dropped** — it computes against CURRENT_DATE and is non-reproducible (mapping doc §3).
3. **No wall-clock values anywhere** in the pack: dataset-derived reference points are scalar subqueries (pack README). This is why the view2 calendar is *derived*, not hardcoded (T3).
4. Cast rules: pack README table. IDs and unlisted columns stay VARCHAR; dates → `date`, money → `float`, counts/years → `int`. Read with `all_varchar=true` + explicit casts (the runner does this from `sources.yaml`).
5. `--strict` exits non-zero if **any** declared validation check fails. Known data defects therefore need care in `validation.yaml` (T4's trap).
6. Statewide arrives later in the same CSV format (D15): every sample-scale number lives ONLY in `sources.yaml` `expected_rows` / `validation.yaml` `post_view` — never inside view SQL.
7. Known defects you will meet — **expected, log them, don't fix** (mapping doc §8): ≥20 `activity_expenditure.activity_code`s absent from `planned_activity` (12,724 distinct vs 12,704); 488 `activity_voucher` rows with NULL `voucher_pk` in phantom FY `2026-2027` (dates 2026-04+); one future-dated sanction (2026-08-19); the 'Buildings' status mis-decode (13 rows); `'\t'`-prefixed WORK COMPLETED (17 rows); 233/717 dim_code rows without descriptions; `theme` trailing space; `plan.plan_code_status` always null.
8. Audited reconciliation targets (mapping doc §3, PM-verified from `Data/`):
   Σ`total_cost` = **773,088,536** (= Σ`fund_amount_total`); Σ`activity_expenditure.total_expenditure` = **253,475,090.46** (== linked voucher sums, exact on all 12,730 rows); Σ`fund_sanctioned_total` = **288,438,745**; voucher payments = **685,750,812** / receipts = **664,791,436** (total 1,350,542,247.18); admin approvals = **2,101** (Chikilli GP: **0**); technical approvals = 2,134.

## Tasks

### T1 — `sources.yaml`

- **Do:** All 19 tables (yes, including empty `activity_nsap` and all-null `activity_delegation` — staged-but-unused is a crosswalk-visible fact), with explicit casts per the mapping doc's roles and `expected_rows` from the audit (12,704 / 12,730 / 12,440 / 8,267 / 2,101 / 2,107 / 2,134 / 5,976 / 204 / 20 / 717 / 17 / 12 / 12,704×5 child tables / 0).
- **Done when:** every staged column's cast matches its §7 role (measures float, dates date, decode codes VARCHAR-compatible).
- **Trap:** don't cast decode-joining codes to types that break the dim_code VARCHAR join (fact 2).

### T2 — `derived_columns.sql`

- **Do:** `stg_*` view per table (pass-through where nothing derives). Re-express the `create_views.sql` building blocks: `stg_exp_rollup` (the v_exp GROUP BY), `stg_approval` (the v_approval join incl. authority_clean, tied_untied, scheme ARG_MAX rollup), decode helpers, and the geography spine from `gram_panchayat` (all six name+code columns). Consume join keys here; person-free by construction (§7 roles).
- **Done when:** every expression traces to `create_views.sql` or the mapping doc; the one delta (dropped `days_since_sanction`) is comment-marked; zero wall-clock references (fact 3).
- **Escalate if:** re-expressing any `v_*` semantic requires *changing* it — that risks Ask↔Discover divergence and is an operator decision (STOP class).

### T3 — the three views (`views/*.sql`)

Build exactly the mapping doc §4 specs. All three: geography-complete (six
name+code columns), output columns cast to stable logical types, no
sample-scale literals.

- **`view1_activity_lifecycle.sql`** — one row per `planned_activity` row (12,704). Folds: exp rollup, approval block, asset labels, fund splits, training, community service, evidence counts, both overspend differences. Dimensions/measures per §4.1 + §3.
- **`view2_geo_month_cube.sql`** — full **GP × month calendar cross-join**, zero-filled measures. **Calendar derivation rule (do not hardcode):** months from `DATE_TRUNC('month', MIN(voucher.date))` to `DATE_TRUNC('month', MAX(voucher.date))` — on the sample this yields 2020-04..2026-03, 72 months, 1,440 rows, and structurally excludes the phantom-FY orphan links (their dates start 2026-04, beyond the cashbook). Measures per §4.2.
- **`view3_gp_performance.sql`** — **GP × fiscal_year grid from the `gram_panchayat` master** (LEFT JOINs only; fiscal years = distinct values observed in `planned_activity`∪`plan`∪`voucher`, excluding the phantom `2026-2027`), zero-filled: 20 × 6 = 120 rows. Chikilli's approval zeros must survive. Measures per §4.3.
- **Done when:** row counts 12,704 / 1,440 / 120; every §4 column present; no personal/free-text/document-number column in any output (§7 excluded roles).
- **Traps:** inner joins deleting zero rows (view3); averages-of-averages (materialize nothing rate-like — num+denom columns only); the two `fund_overflow_json` multi-scheme activities lose their split (accepted, §8.8).

### T4 — `validation.yaml`

- **Do:** PKs (activity_code, voucher_pk, plan_code, gp_lgd_code, expenditure_id…), FKs, categoricals (`direction` [payment, receipt], `plan_type`, `tec_approval_required` [R, N]), date ranges, and `post_view` grains: view1 `[activity_code]` 12,704; view2 `[gp_lgd_code, month]` 1,440; view3 `[gp_lgd_code, fiscal_year]` 120 (+ tolerance).
- **The trap — known-defect handling under `--strict`:** declaring `activity_expenditure.activity_code → planned_activity` as an FK will fail the build on the ≥20 known orphans (fact 7), and `--strict` would then always be red. Rule: **declare only constraints that actually hold; every known violation is instead quantified in your report and the validation report**, with a pack-README note listing which constraints were deliberately not declared and why. If you find a *new* violation the mapping doc doesn't list — that's a finding; log it, don't fix it, don't quietly un-declare it without recording.
- **Done when:** `--strict` is green AND the report lists every undeclared-because-violated constraint with its measured count.

### T5 — `crosswalk.csv`

- **Do:** Materialize mapping doc §7 as `Insights/domain_pack_prdw/crosswalk.csv` (AP `demo_crosswalk.csv` mechanics): one row per column of every staged table, its role, and for excluded roles the reason.
- **Done when:** 100% of staged columns present; machine-checkable agreement with what the views actually expose (spot-check: no `X-*`-role column appears in any Parquet).

### T6 — Build + reconciliation gate

- **Do:** On the local mirror: `python src/build_views.py --pack domain_pack_prdw --data-dir <mirror>/Data --views-dir views_prdw --reports-dir reports_prdw --strict`. Then reconcile against fact 8, reading the Parquet outputs:

| Check | Target | Tolerance |
|---|---|---|
| view1 rows / Σtotal_cost | 12,704 / 773,088,536 | exact |
| view1 Σtotal_expenditure | ≤ 253,475,090.46 | delta = the orphan-code amounts; **quantify the delta and its row count** |
| view1 Σfund_sanctioned_total | 288,438,745 minus any orphan approvals | quantify |
| view2 rows / Σpayment_amount / Σreceipt_amount | 1,440 / 685,750,812 / 664,791,436 | exact |
| view3 rows / Σn_activities / Σn_admin_approvals | 120 / 12,704 / 2,101 | exact |
| view3 Chikilli approval rows | 0 in every FY, rows present | exact |
- Sync `reports_prdw/` (validation report + view profiles) back to `Insights/reports_prdw/`; Parquet outputs stay local (gitignored).
- **Done when:** the table above is filled with actuals; every non-exact delta has a one-line explanation traced to a §8 defect.
- **Escalate if:** a delta has **no** known-defect explanation — that is either a pack bug or a new data finding; do not hand-wave it.

### T7 — Report

- **Do:** `handoffs/WPD1_REPORT.md` per the spec below. No git operations — staging and committing are the operator's.

## Cut-line

T1–T4 and T6 are one unit — there is no meaningful partial delivery of a pack
that doesn't build. T5 (crosswalk) is required for the gate but can be the last
thing authored. If the run degrades, deliver a failing-but-honest T6 table over
a silent success claim, always.

## Escalation protocol

- **STOP and end the run:** preconditions fail; `Data/` contradicts the mapping doc's audited numbers (fact 8) beyond the known deltas; a `v_*` semantic can't be re-expressed without change (T2).
- **Decide-and-document** (report §6 journal: decision / options / choice / reversal cost): cast micro-choices, stg naming, calendar-derivation edge cases, an undeclarable validation constraint (T4 rule), column ordering.
- **Never:** fix data, touch out-of-scope files, run the mining engine, call any LLM API (nothing here needs one), commit.

## Gate (definition of done)

1. `--strict` build green on the local mirror from `Data/` alone.
2. T6 reconciliation table complete; all deltas explained by documented defects.
3. Three Parquet views match the signed §4 specs: grains, columns, geography completeness, zero-row survival (Chikilli check).
4. `crosswalk.csv` covers 100% of staged columns; no excluded role reaches a view.
5. Validation report delivered to `Insights/reports_prdw/`; report complete.

Gate holder: PM reviews the report and replays the build; operator (SME) confirms the reconciliation table.

## Report spec — `handoffs/WPD1_REPORT.md`

- **§0 Status** — the five gate items, PASS/FAIL/PARTIAL + one line of evidence each.
- **§1 Build transcript summary** — command, environment, runtime, `--strict` outcome.
- **§2 Reconciliation table** (T6, with actuals and deltas).
- **§3 Validation summary** — checks declared, checks deliberately not declared (with measured violation counts), defects logged.
- **§4 Pack design notes** — every delta from `create_views.sql` semantics (expected: only `days_since_sanction`), calendar/FY derivation choices.
- **§5 Data oddities** — new findings beyond mapping doc §8, if any.
- **§6 Decision journal** (decide-and-document entries).
- **§7 Self-audit** — what you verified, what you did not, what the PM should replay.

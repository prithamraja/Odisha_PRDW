# Discover view mapping — Odisha PR&DW (WP-D0 deliverable)

Authored by the PM session per D21 (2026-08-13), executing
`handoffs/WPD0_view_mapping.md`. Data source: local scratch copy of `Data/`
(19 CSVs, PM-verified identical to `panchayat_1.duckdb`), profiled read-only
with DuckDB 1.5.1. **Gate: operator-as-SME sign-off (D20) on §9's decisions.**
Per D21 no separate agent report exists; §§2–8 carry the audit evidence a
report would, and §10 is the self-audit.

---

## 0. Summary

Three views are proposed (§4): an **activity lifecycle** view extending
`v_activity` (assets, funding splits, training and community-service columns
folded in — no separate asset view), a **GP × month cash cube** built from the
voucher tables (the only measure family with a clean, artifact-free monthly
signal across the full 72-month window), and a **GP × fiscal-year performance**
view materialized from the `gram_panchayat` master so zero-activity rows
survive. An equity/journey view is **not supportable in v1** (§4.4). Temporal
mining is routed to the cash cube; activity-count comparisons across the
2023-24 boundary get a deterministic caveat (§5). Every view carries the full
geography hierarchy — names and LGD codes for GP, block, district — sourced
from `gram_panchayat`, which the audit confirms is fully populated (§2).

## 1. Inputs and method

Profiled: all 19 `Data/*.csv` (row counts match the data dictionary),
`Data/create_views.sql` (all seven `v_*` definitions read in full). Profiling
scripts ran on a local scratch copy (D6); their outputs are transcribed into
this document, which is the durable record. The Ask catalogue's view usage was
taken from PROJECT_PLAN §5.1 and the WP-3 brief's Path-B appendix (not
re-derived from the workbook).

## 2. Geography and dimension audit

**Geography (from `gram_panchayat`, fully populated, zero nulls):**

| Level | Sample values | Statewide | Sample notes |
|---|---|---|---|
| District (`zp_name`, `district_code`) | 9 | 30 | Ganjam & Bargarh 4 GPs each; Kandhamal/Malkangiri/Rayagada 1 each |
| Block (`block_name`, `block_code`) | 16 | 314 | Bhubaneswar 3 GPs, Barpali & Rangeilunda 2; 13 blocks have 1 GP |
| GP (`gp_name`, `gp_lgd_code`) | 20 | ~6,800 | All 20 active in every core table |

Nine districts / sixteen blocks give the engine real sibling sets even in the
sample — block/district dimensions are thin but *not* degenerate. The known
`Kalyansinghpur` (GP) vs `Kalyansingpur` (block) spelling split is visible in
the master. `state_name`/`state_code` are constant (excluded from mining
dimensions; staged for statewide continuity).

**Candidate categorical dimensions** (sample cardinality | null/unknown rate |
source):

| Dimension | Card. | Notes |
|---|---|---|
| `district_name`, `block_name`, `gp_name` (+codes) | 9 / 16 / 20 | zero nulls |
| `fiscal_year` | 6 | `'2020-2021'`…`'2025-2026'`; a 7th (`2026-2027`) only in 488 orphan voucher links (§8) |
| `theme` (LSDG, via focus_area) | 6 + Unmapped | 986 activities (7.8%) unmapped |
| `focus_area_name` | 30 | decode complete |
| `work_type_label` | 4 | |
| `activity_for_label` | 4 | |
| `activity_type_label` | 2 | |
| `output_type` (decode exists) | 8 | |
| `status_label` | 6 | **heavily skewed**: Activity Approved 10,108; WORK ONGOING 2,110; ABANDONED 420; UNDER APPROVAL 36; WORK COMPLETED **17**; 'Buildings' mis-decode 13 (§8) |
| `is_costless` (Costed/Costless) | 2 | 7,074 costless — all post-2022-23 (§5) |
| `tied_untied` (sanction stage) | 3 | Tied 960 / Untied 1,089 / Other 58 sanction-scheme rows |
| `sanction_authority` (authority_clean) | ~8 | approval subset only (2,101 activities) |
| `sanctioned_scheme_name`, `fund_component_name` | ≤18 / ≤25 | approval subset; some decodes fall back to 'Code N' (§8) |
| `asset_category_label` | 36 + Uncategorised | 4,286 activities carry asset data (1:1 rows) |
| `plan_type` | 2 | Main 120 / Supplementary 84 plans |
| `voucher direction` / `type` | 2 / 7 | cashbook |
| `scheme_name` (expenditure) | 5 | **82% null — not a dimension**; superseded by sanctioned_scheme_name |

All `activity_*` child tables are **1:1 with `planned_activity`** (12,704 rows,
12,704 distinct activity_codes each) — they are additional columns of the
lifecycle grain, not separate grains. `activity_delegation` is entirely null
(excluded); `activity_nsap` has zero rows (§4.4).

## 3. The money funnel and measure census

The audit reconciled the money layers exactly:

```
PLANNED    total_cost (planned_activity)            ₹773.1M  = activity_fund.fund_amount_total
SANCTIONED fund_sanctioned_total (approval schemes) ₹288.4M  (2,101 approved activities)
SPENT      total_expenditure (activity_expenditure) ₹253.5M  = Σ linked voucher_cost, EXACT on all 12,730 rows
CASHBOOK   voucher.amount                           ₹685.7M payments / ₹664.8M receipts (all flows, incl. non-activity)
```

Every money measure is labeled with one of these bases; a Discover finding must
never mix bases silently. "Expenditure" unqualified = **SPENT** (activity-linked
cash), matching the Ask catalogue's convention of stating the basis per answer.

| Measure | Basis | Agg | Source | Notes |
|---|---|---|---|---|
| `n_activities` (ones column) | — | SUM | planned_activity | impact measure |
| `total_cost` | PLANNED | SUM | planned_activity | null ⇔ costless |
| `fund_tied_total`, `fund_untied_total` | PLANNED | SUM | activity_fund | tied+untied gen/sc/st components also available |
| `fund_abandoned_total` | PLANNED | SUM | activity_fund | ₹61.7M in sample |
| `work_proposed_cost` | SANCTIONED | SUM | admin_approval | |
| `fund_sanctioned_total` (+ gen/sc/st) | SANCTIONED | SUM | admin_approval_scheme | sc ₹3.2M / st ₹0.4M — thin (§4.4) |
| `tec_approval_cost` | SANCTIONED | SUM | technical_approval | |
| `total_expenditure` (+ gen/sc/st) | SPENT | SUM | activity_expenditure | == linked vouchers, proven |
| `overspend_vs_plan` (= total_expenditure − total_cost) | SPENT−PLANNED | SUM | derived | signed difference — sums roll up honestly where ratios cannot; the utilisation/overspend detector |
| `overspend_vs_sanction` (= total_expenditure − fund_sanctioned_total) | SPENT−SANCTIONED | SUM | derived | approval subset only (17%); absence of a sanction record ≠ unsanctioned spend |
| `payment_amount`, `receipt_amount` | CASHBOOK | SUM | voucher | by direction |
| `payment_count`, `receipt_count` | CASHBOOK | SUM | voucher | |
| flags: `is_completed`, `is_ongoing`, `is_abandoned`, `is_started`, `is_under_approval` | — | SUM (num) / `n_activities` (denom) | v_activity logic | completion near-degenerate in sample (17!) — §9.5 |
| `is_admin_approved`, `has_technical_approval`, `has_progress_evidence` | — | SUM (num) / `n_activities` (denom) | v_activity logic | approval coverage ~17% is a *data* property, absence ≠ unapproved |
| `evidence_uploads` | — | SUM | physical_progress rollup | 8,267 uploads on 1,675 activities |
| `trainees_total`, `training_days` | — | SUM | activity_training | 1,034 activities |
| `beneficiaries_expected` | — | SUM | activity_community_service | 763 activities |

Rates are **never materialized**: each rate ships as its numerator (a SUM-able
flag or amount) with `n_activities` (or the relevant amount) as denominator,
so block/district roll-ups aggregate correctly (D15). The two signed
**overspend differences** above are the one sanctioned cross-basis mix — each
is labeled with both bases, and being differences they aggregate honestly. `days_since_sanction` is
excluded everywhere — it computes against CURRENT_DATE and is not reproducible.

## 4. View designs

Derivation logic (status flags, approval semantics, `authority_clean`,
`tied_untied`, all dim_code decodes incl. the double-cast, the v_exp and
scheme 1:1 rollups) is **taken verbatim from `create_views.sql`** — the pack's
`derived_columns.sql` re-expresses those definitions over `stg_*` tables, so
Ask and Discover cannot disagree (handoff §1). Deviations are noted per view.

### 4.1 `view1_activity_lifecycle` — one row per planned activity

Extends `v_activity` (verbatim semantics) plus 1:1 folds the views don't carry:
`asset_category_label`/`asset_type_label` (from activity_asset, decode per
`v_asset`), `fund_tied_total`/`fund_untied_total`/`fund_abandoned_total`
(activity_fund), `trainees_total`/`training_days` (activity_training),
`beneficiaries_expected` (activity_community_service), `output_type` decode.

- **Grain:** planned activity. Rows: 12,704 sample; statewide unknown —
  ~4.3M if density holds (6,800/20 × sample). Flag for engine time budgets.
- **Dimensions:** district/block/gp (names + codes), theme, focus_area_name,
  work_type_label, activity_for_label, activity_type_label, output_type_label,
  status_label, is_costless, tied_untied, sanction_authority,
  sanctioned_scheme_name, fund_component_name, asset_category_label,
  fiscal_year *(categorical — see §5)*.
- **Temporal dimensions:** none in v1 (§5 routes temporal mining to view2;
  sanction_month exists only for the 17% approval subset).
- **Measures:** §3's activity-grain rows (n_activities, total_cost,
  fund_* splits, sanction amounts, total_expenditure + gen/sc/st, both
  overspend differences, all flags, evidence_uploads, trainees,
  beneficiaries).
- **Impact measures:** n_activities, total_cost.
- **Join note:** `v_activity` inner-joins gram_panchayat (safe: every activity
  has a GP); zero-activity GPs are view3's job.

### 4.2 `view2_geo_month_cube` — GP × month, cash basis

Built from `voucher` (+ `activity_voucher` for activity-linked spend), on a
**full GP × month calendar cross-join** so silent months survive as zeros — a
GP with no payments for a quarter is a finding, not a missing row.

- **Grain:** gp × calendar month, 2020-04..2026-03. Rows: 20 × 72 = 1,440
  sample; ~490k statewide. Zero-fill measures, not dimensions.
- **Dimensions:** district/block/gp (names + codes), fiscal_year.
- **Temporal dimensions:** month (`YYYY-MM`), quarter, fiscal_year.
- **Measures:** payment_amount, receipt_amount, payment_count, receipt_count,
  activity_linked_expenditure (voucher_cost by voucher_date month),
  sanctions_count, sanctioned_amount (admin_approval by sanction month).
- **Impact measures:** payment_amount, payment_count.
- **Expected known finding:** March fiscal-year-end spikes (March 2026: 784
  vouchers vs ~130 typical months) — real, calibrate as "already-known".

### 4.3 `view3_gp_performance` — GP × fiscal year

Materialized **from the `gram_panchayat` master LEFT-JOINed** onto per-GP-FY
aggregates of everything (grid: every GP × every FY). The sample proves why:
Chikilli has 640 activities and **zero approvals** — an inner join on
approvals would silently delete the most interesting row in the table.

- **Grain:** gp × fiscal_year. Rows: 120 sample; ~41k statewide.
- **Dimensions:** district/block/gp (names + codes).
- **Temporal dimensions:** fiscal_year.
- **Measures:** n_plans, n_activities, n_costed, n_costless, planned_cost,
  sanctioned_total, expenditure_total (SPENT), overspend_vs_plan,
  overspend_vs_sanction, payment_amount, receipt_amount,
  n_admin_approvals, n_tech_approvals, n_completed, n_ongoing, n_abandoned,
  n_with_evidence, evidence_uploads.
- **Impact measures:** n_activities, expenditure_total.

### 4.4 Equity / journey view — **not supportable in v1**

Evidence: `activity_nsap` has zero rows (confirming the 13 dropped Ask
questions); expenditure SC/ST components are near-empty (19 and 2 non-null
rows); sanctioned SC/ST funds total ₹3.6M of ₹288M. No beneficiary-grain data
exists anywhere in the drop. The SC/ST fund-component measures are carried in
views 1 and 3 so statewide data can light them up; if statewide NSAP/beneficiary
tables arrive, an equity view becomes a pack addition, not a redesign.
**No separate asset view either:** activity_asset is 1:1 with activities, so
asset dimensions fold into view1 (`v_asset` remains an Ask-side serving view).

## 5. Temporal scope (the 2023-24 step-change, decomposed)

The audit *decomposed* the dictionary's known step-change: activity rows jump
609 → 4,607 in 2023-24 **entirely because costless activities begin appearing**
(0 costless before FY 2023-24; 2,780 / 2,367 / 1,927 after). Costed activities
(571/580/609/1,827/1,056/987) still jump ~3×. Meanwhile the **cashbook is
smooth across the boundary** (payments ₹156M/138M/92M/93M/96M/111M) and
approvals are steady (~280–430/yr). The artifact lives in planning-data
completeness, not in money flows.

**Proposal:**

1. **Temporal pattern mining runs on view2 only** (cash + sanction measures),
   over the full 72-month window — it is artifact-free.
2. view1/view3 keep `fiscal_year` as a *categorical* dimension, and any finding
   whose subspace or breakdown involves fiscal_year **with a count-based
   measure** spanning the 2023-24 boundary gets a deterministic reading-note
   caveat: *"Activity-count comparisons across FY 2023-24 reflect a change in
   reporting completeness (costless activities begin being recorded), not a
   change in activity."* Money-measure findings need no caveat.
3. **FY 2026-2027 is excluded from all views**: it exists only as 488
   activity_voucher rows with NULL voucher_pk and dates beyond the cashbook's
   coverage (§8) — a partial-year fragment that would poison every
   current-year comparison.

## 6. Sample vs statewide switch plan

One marked block per `VIEW*_CONFIG` (the `_DB_SOURCES` pattern), differing
only in dimension lists and depth:

| | Sample | Statewide |
|---|---|---|
| view1 dims | gp, block, district + all §4.1 categoricals; depth 2 | **drop gp and block from dimensions** (6,800 / 314 values; GP subspaces all fall under the 1% impact prune anyway); district + categoricals; depth 2 |
| view2 dims | gp, block, district; depth 1 | district, block; depth 1 (GP rows remain the grain — exceptions still name GPs via the cube's rows) |
| view3 dims | gp, block, district; depth 1 | district, block; depth 2 |
| validation | `expected_rows`: sample values | one-file update of `expected_rows`/`post_view` (D15) |

GP remains the *grain* everywhere statewide — findings still name individual
GPs as exceptions — it just stops being a breakdown dimension. `expected_rows`
and `post_view` numbers live only in `sources.yaml`/`validation.yaml`.

## 7. Column crosswalk (every staged column → role)

Roles: `dim` (dimension source), `meas` (measure source), `temp` (temporal),
`grain` (row identity), `join` (consumed in derivations, appears in no view),
`decode` (dim_code machinery), `X-empty` (all/near-all null — staged, unused),
`X-const` (constant), `X-id` (document/system identifier, no analytical role),
`X-derived` (redundant with another column), `X-nonrepro` (not reproducible).
**No column anywhere carries a personal beneficiary identifier; free-text
authority fields are consumed into `authority_clean` and their raw forms stay
out of views (§9.6).**

| Table | Columns → roles |
|---|---|
| `gram_panchayat` | gp_lgd_code/gp_name/block_code/block_name/district_code/zp_name **dim**; state_code/state_name **X-const** (staged for statewide) |
| `planned_activity` | activity_code **grain**; plan_code/gp_lgd_code **join**; fiscal_year **dim**; activity_name/activity_desc **join** (search_text; glossary examples only); focus_area/work_type/activity_for/activity_type/output_type/activity_status **decode→dim**; is_costless_activity **dim**; total_cost **meas**; source_file **X-id**; operation_type/operation_remarks **X-empty** (97%+ null) |
| `activity_expenditure` | expenditure_id **grain**(rollup); activity_code/plan_code/gp_lgd_code **join**; fiscal_year **dim**; scheme_name **X-empty** (82% null); approved_cost_action_plan/technical_approved_cost/admin_approved_cost/general/sc/st/total_expenditure **meas**; s_no **X-id** |
| `voucher` | voucher_pk **grain**; gp_lgd_code **join**; fiscal_year **dim**; date **temp**; direction/type **dim**; amount **meas**; voucher_no/voucher_id **X-id**; month **X-derived** |
| `activity_voucher` | expenditure_id/voucher_pk **join**; gp_lgd_code **join**; fiscal_year **dim**; voucher_date **temp**; voucher_cost **meas**; voucher_no **X-id** |
| `admin_approval` | activity_code/gp_lgd_code **join**; plan_year **temp** (→fiscal_year form); adm_approval_sanction_date **temp**; work_proposed_cost **meas**; adm_approval_authority **join**→authority_clean **dim** (raw excluded); adm_approval_no **X-id**; row_id/doc_type/source_file/gp_name/work_plan_year **X-id/X-derived** |
| `admin_approval_scheme` | activity_code **join**; scheme_code/scheme_component_code **decode→dim** (tied_untied); fund_sanctioned_general/sc/st/total **meas**; row_id/parent_row_id/pos **X-id** |
| `technical_approval` | activity_code/gp_lgd_code **join**; tec_approval_required **dim**; tec_approval_cost **meas**; tec_approval_order_date **temp**; tec_approval_authority **join** (raw excluded); tec_approval_order_no/row_id/doc_type/source_file/gp_name/plan_year **X-id/X-derived** |
| `plan` | plan_code **grain**; gp_lgd_code **join**; fiscal_year **dim**; plan_type **dim**; approval_date **temp** (is_approved); plan_code_status **X-empty** (always null) |
| `physical_progress` | activity_code **join**; file_upload_id → evidence_uploads **meas**; longitude/latitude/longitude_raw/latitude_raw/n_coords **X-id** (evidence coordinates; Ask's v_progress serves them); row_id/parent_row_id/pos **X-id**; plan_unit_type_code **X-const** |
| `activity_asset` | activity_code **join**; asset_type/asset_category **decode→dim**; asset_subcategory/main_asset_* /asset_parameter_type/asset_loc_code/asset_unit_* **X-empty or too sparse for v1** (66–90% null; revisit statewide); asset_name/asset_details_raw/asset_loc_unit_type/asset_loc_unit_code/asset_loc_unit_cost_total **X-empty**; asset_coverage_code **X-const**; asset_unit_cost **meas** (candidate, 30% populated); asset_loc_overflow_json **X-empty** |
| `activity_fund` | activity_code **join**; fund_scheme_code/fund_component_code **decode→dim** (candidate); fund_tied_general/sc/st + fund_untied_general/sc/st + fund_amount_total + 4 abandoned splits **meas**; fund_overflow_json **X-empty** |
| `activity_training` | activity_code **join**; training_category_code/training_organiser_code **decode→dim** (candidate; 8% populated); training_subject **X-id** (free text); training_trainees_total/training_duration_days **meas**; training_capacity_raw **X-empty** |
| `activity_community_service` | activity_code **join**; community_service_code **decode→dim** (candidate; 6% populated); community_service_duration/community_beneficiaries_expected **meas**; community_service_raw **X-empty** |
| `activity_delegation` | all 8 columns **X-empty** (is_shareable constant False; rest fully null) — table staged, feeds nothing |
| `activity_nsap` | all 6 columns **X-empty** (zero rows) — table staged, feeds nothing; the evidence for §4.4 |
| `dim_code` | variable/code/description **decode**; source/confidence **X-id** (decode provenance — drives §8 logging) |
| `dim_lsdg_theme` | focus_area_name/lsdg_theme **decode**; distinct_themes/n_rows **X-derived** |
| `dim_welfare_scheme` | scheme_code/scheme_name **decode** (currently unreferenced by any populated column — welfare tagging arrives with NSAP data, if ever) |

## 8. Data oddities observed (log, never fix — additions to the running list)

1. **488 `activity_voucher` rows: fiscal_year `2026-2027`, NULL `voucher_pk`**,
   voucher_date up to 2026-08-03 — beyond the voucher table's coverage
   (ends 2026-03-31). Orphan links; excluded via §5.3.
2. **`admin_approval` max sanction date 2026-08-19 — six days in the future**
   at audit time (2026-08-13). At least one future-dated sanction.
3. `activity_status` decode: the known 'Buildings' mis-decode (code 173) covers
   13 activities; the `'\t'`-prefixed WORK COMPLETED (code 178) covers 17.
4. **Only 17 activities sample-wide are WORK COMPLETED (0.13%)** — completion
   measures are near-degenerate in the sample (§9.5).
5. `dim_code`: 233/717 codes have no description (238 'Unresolved', 4
   'Conflict') — 'Code N' / 'Unknown' / 'Uncategorised' labels will surface in
   findings; the column glossary (WP-D2) must explain them.
6. `plan.plan_code_status` is always null (known: generated placeholder).
7. `voucher.month` (name strings) is redundant with `date`; March concentration
   (3,579 of 12,440) is the fiscal year-end pattern, not an error.
8. Two `planned_activity` rows carry `fund_overflow_json` (multi-scheme
   funding squeezed into one row) — the 1:1 fund fold loses that split for
   exactly 2 activities; accepted, logged.
9. `admin_approval`/`technical_approval` carry `gp_name` denormalized (19
   values) — consistent with the master; joins use codes regardless.

## 9. Open decisions — SME sign-off requested (D20)

| # | Decision | Recommendation |
|---|---|---|
| 1 | **View slate**: the three views of §4, assets folded into view1, no equity view in v1 | Approve as specified |
| 2 | **Money funnel naming + default**: PLANNED / SANCTIONED / SPENT / CASHBOOK; unqualified "expenditure" = SPENT; plus the two signed cross-basis overspend measures (§3) as the deliberate exception to no-basis-mixing | Approve; matches Ask's per-answer basis convention; overspend differences added on SME question 2026-08-13 |
| 3 | **Temporal scope** (§5): temporal mining on view2 only; deterministic caveat on count-measures crossing FY 2023-24; FY 2026-27 excluded | Approve |
| 4 | **view3 grain**: GP × fiscal_year (recommended — enables year-over-year institution comparisons) vs GP-lifetime | GP × FY |
| 5 | **Completion measures**: keep `is_completed` etc. despite 17 completed works sample-wide (findings will be trivially "nobody completes"), or hold until statewide | Keep — sample calibration treats them as known-degenerate; statewide is the real test |
| 6 | **Excluded free text**: `authority_raw`, `tec_approval_authority` raw, `training_subject`, document numbers stay out of all Discover views | Approve (noise + name-bearing risk) |
| 7 | **Sparse candidate dimensions** (asset subcategory, training category, community-service code, fund scheme: 6–34% populated): stage them, mine them only statewide | Approve — sample-phase configs omit them |

## 10. Self-audit

**Verified directly:** all 19 CSV loads; every cardinality/null figure in §§2–3;
the money-funnel reconciliations (plan=fund total, expenditure=voucher links,
exact on all rows); the step-change decomposition; Chikilli's zero approvals;
geography code completeness; `create_views.sql` read in full.
**Not verified / relied on prior PM validation:** the CSV↔DuckDB identity
(plan §5.5), the workbook's view-usage counts (WP-3 appendix), the data
dictionary docx (plan §2 summary). **Not done:** no engine run, no pack file,
no statewide extrapolation beyond row-count arithmetic. Profiling scripts were
session-scratch and are disposable; every number they produced is in this
document.

---

## 11. Amendments log (post-signature — D22 signed §9 on 2026-08-13)

Corrections measured by WP-D1 (report §§4–5, PM-replayed). The signed text
above is unedited; where this log and §§2–8 disagree, this log wins.

1. §7 `asset_loc_overflow_json`: roled `X-empty`; measured 54 non-null rows
   (99.6% null). Role stands on the null rate; the label was literally wrong.
2. §2 `sanction_authority` "~8": measured **14** — ten free-text residues
   (15 rows) pass through `authority_clean`'s ELSE branch. Statewide-arrival
   checklist item (plan §5.6e).
3. §2 `asset_category_label` "36 + Uncategorised": **27 named labels +
   'Uncategorised'** reach view1 (8 codes undescribed, several share one);
   'Uncategorised' spans 8,439 rows incl. 21 description-less codes.
4. §3/§4 `output_type` "decode exists": the 8 codes exist in dim_code with
   **NULL descriptions** — labels are 'Code 101'…'Code 110'. Team ask open.
5. §3 sanctioned sc/st parenthetical ("sc ₹3.2M / st ₹0.4M"): the two source
   tables carry these values **swapped relative to each other**
   (`admin_approval_scheme` sc=₹0.44M/st=₹3.23M; `activity_expenditure`
   sc=₹3.23M/st=₹0.44M). Possible column transposition at source — team ask
   open; §4.4's too-thin-for-equity conclusion unaffected either way.
6. §4.3 implicit tech-approval count: view3 `n_tech_approvals` totals
   **2,095**, not 2,134 — 39 technical approvals sit on activities with no
   administrative approval and are invisible to `v_approval`, hence to Ask
   and Discover alike. Kept deliberately for Ask↔Discover agreement (D23);
   team ask open on whether TA-without-AA is legitimate.
7. §7 `activity_delegation`: `is_shareable` is 'False' on 11,289 rows and
   NULL on 1,415 (not constant-false); `is_delegated` is 100% null. The
   feeds-nothing conclusion stands.
8. Additions the pack made within T2's rules, accepted by D23: five
   TIMESTAMP twin columns in staging (runner CHECK 6 compatibility, never
   projected); `stg_activity_voucher.voucher_pk_norm` (float-text key
   normalisation — the `v_asset` double-cast idiom; FK declared on it);
   view1 carries `sanction_scheme_rows` and the five statewide-staged sparse
   dimension columns; view2 additionally carries `work_proposed_amount`.

---

## 12. Amendment B — `gp_profile` (2026-09-07; operator sign-off requested)

A new source, `Data/gp_profile.csv`, arrived 2026-09-07: one row per Gram
Panchayat, 99 columns, 20 rows. Operator decisions taken in the 2026-09-07
PM session, before this text was written:

- **Leadership comparisons are dropped for now.** The profile carries no
  elected-representative field (no sarpanch gender, no seat reservation);
  the only "sarpanch" in the drop is an approving authority. Revisit if the
  department supplies a representative or seat-reservation table.
- **Shape approved:** profile attributes join the three existing views as
  dimensions, AND a fourth GP-grain view is added (§12.4).
- **Cut points are fixed, declared in the pack**, not quantiles (§12.3).
- **GP size is banded on population at 2,500 / 5,000 / 10,000** (operator
  ruling, replacing the PM's household proposal).
- **Email, mobile and address are excluded from every view** — not needed
  for anything (operator ruling; §12.2 `X-pii`).
- **Design for statewide scale, not for the 20-GP sample.** Social
  composition stays a three-way ST / SC / Mixed split at every scale; the
  PM's proposed two-way sample workaround is dropped (operator ruling on B2).
  Thin sample bands are accepted as a sample property, not designed around.

The signed text of §§1–11 is unedited. Where this section and §4.4 disagree
("no equity view in v1"), this section wins: the beneficiary-grain conclusion
stands, but a **GP-composition equity lens** is now supportable.

### 12.1 Source audit

| Property | Measured |
|---|---|
| Rows / columns | 20 / 99 |
| Join key | `basic_info_lgd` = `gram_panchayat.gp_lgd_code` — 1:1, all 20 match, zero orphans either side |
| Column families | `param__*` (8, keys the master already carries), `basic_info_*` (11), `basic_amenities_*` (17), `demographic_details_*` (9), `general_*` (5), `education_*` (4), `health_*` (5), `infrastructure_*` (13), `panchayat_area_*` (4), `panchayat_learning_centre_details_*` (20), `sports_*` (3) |
| Internal consistency | male+female = total and general+obc+sc+st = total on all 20 rows |
| Sparse block | the 19 PLC detail columns are populated on the 2 GPs that have a learning centre; `plc_available` itself is complete (18 No / 2 Yes) |

This is **self-reported** GP data. It is staged as-is; defects are logged
(§12.6), never fixed.

### 12.2 Crosswalk roles (extends §7)

New role **`X-pii`**: personal or contact data — registered by the runner
(the CSV loads whole) but projected by no `stg_*` view and reaching no
Parquet file, on the operator's ruling that email, mobile and address are
needed for nothing. Same mechanics as the raw authority text of §9.6; the
WP's crosswalk gate check asserts that no `X-pii` column name appears in any
view's output columns.

| Columns | Role |
|---|---|
| `basic_info_lgd` | **join** (the spine) |
| `param__label1/label11/label111`, `param__bp_name/zp_name/gp_name`, `basic_info_block/district/state/village` | **X-derived** — the master is authoritative for geography; never re-projected |
| `param__localbodytypecode`, `param__stateid`, `demographic_details_transgender_population` (all 0), `basic_amenities_no_of_computer` (constant 1 where present) | **X-const** |
| `basic_info_email_address`, `basic_info_mobile`, `basic_info_address`, `basic_info_gp_attractions` | **X-pii** |
| `basic_amenities_common_service_centre_situated_in` (free text, 9 rows), `basic_amenities_location_of_common_service_centre` (12 rows), `basic_amenities_types_of_connection` (11 rows), the 19 PLC detail columns (2 rows) | **X-sparse** — staged, unused in v1; statewide candidates |
| `basic_amenities_alternate_source_of_water_*`, `basic_amenities_sources_of_internet_*`, `basic_amenities_sources_of_power_supply_*` | **X-multi** — comma-separated multi-value strings; not a dimension without an unnest, deferred |
| `panchayat_area_total_area` | **X-unreliable** — values 1.11 to 3,000 with no consistent unit (§12.6); no band is built on it |
| `basic_info_distance_from_nearest_bus_stop`, `demographic_details_{sc,st,total_gender_wise}_population`, `basic_amenities_{internet_service_available…, computer_laptop…, panchayat_bhawan, is_common_service_centre_available…}`, `panchayat_learning_centre_details_panchayat_learning_centre_available` | **dim** (source of a derived band, §12.3) |
| every remaining count: population by gender / social category / children, households, job-card holders, SHGs, schools ×4, health facilities ×5, infrastructure ×13, wards, revenue villages, villages mapped to LGD, OSR collected so far, laptops / printers / scanners, sports courts ×3 | **meas** — view4 only (§12.4) |

### 12.3 Derived GP dimensions (`stg_gp_profile`)

Six categorical dimensions, computed once in `derived_columns.sql` with
**fixed cut points**. A GP's band means the same thing in the sample and
statewide; quantile bands were declined because a GP that is "large" among
20 would be re-labelled among 6,800 and sample findings could not be
compared with statewide ones. Any null source yields `'Not reported'` —
dimensions are never zero-filled (§4.2 rule). Yes/no attributes need no cut.

| Dimension | Values | Definition | Sample split |
|---|---|---|---|
| `social_composition` | ST-majority / SC-majority / Mixed | ST share of population > 50%; else SC share > 50%; else Mixed | 2 / 3 / 15 — thin in the sample, by design (statewide is the target) |
| `gp_size` | Under 2,500 / 2,500 to 5,000 / 5,000 to 10,000 / 10,000 and above | total population; each band includes its lower bound and excludes its upper (2,500 is the second band, 5,000 the third, 10,000 the fourth) | 2 / 9 / 7 / 2 — the two outer bands are thin in the sample |
| `remoteness` | Near / Far | nearest bus stop under 5 km / 5 km or more | 14 / 6 |
| `digital_readiness` | Ready / Not ready | internet **and** computer both available at the panchayat bhawan | 10 / 10 |
| `has_panchayat_bhawan` | Yes / No | as reported | 14 / 6 |
| `has_csc` | Yes / No | common service centre available in the panchayat | 12 / 8 |

`social_composition` is mined as-is at both scales. A two-way "SC + ST
together more than half" variant was proposed for the sample (7 / 13) and
**declined by the operator**: the design targets statewide data, and two
cuts of one fact would in any case have produced definitional-pair twins
(WP-D2c exclusion class). The sample will find little on this dimension;
that is expected, and is not a calibration failure. `plc_available` (2 of 20
Yes) is materialised on every view but mined only statewide, like the §9.7
sparse dimensions.

The population cuts (2,500 / 5,000 / 10,000) and the 5 km remoteness cut
are both operator rulings of 2026-09-07. Everything else is a reported
yes/no or a majority test.

### 12.4 View changes

**Views 1–3 (`view1_activity_lifecycle`, `view2_geo_month_cube`,
`view3_gp_performance`).** Each gains the seven `stg_gp_profile` dimension
columns (§12.3's six plus `plc_available`) by LEFT JOIN on `gp_lgd_code`
through the geography spine every view already carries. No measure is added
to these views: population and household counts are GP constants and would
be summed once per activity (view1), once per month (view2) or once per
fiscal year (view3) — a wrong denominator in every case. Grain pins are
unchanged: 12,704 / 1,440 / 120. Statewide GPs with no profile row read
`'Not reported'` on every band.

**New `view4_gp_profile` — one row per Gram Panchayat** (20 sample; ~6,800
statewide). Materialised from the `gram_panchayat` master, LEFT JOIN
`stg_gp_profile`, LEFT JOIN the lifetime aggregates — the same discipline as
view3, so a GP with a profile and no activity survives as a row.

- **Grain:** GP. Post-view pin: 20 rows, `gp_lgd_code` unique.
- **Dimensions:** district / block / gp (names + codes, the §6 switch
  applies) + the seven profile dimensions.
- **Temporal dimensions:** none.
- **Measures, profile family (all SUM):** `population_total`,
  `population_male`, `population_female`, `population_children`,
  `population_sc`, `population_st`, `population_obc`, `population_general`,
  `households`, `job_card_holders`, `shgs`, `wards`, `revenue_villages`,
  `villages_mapped_lgd`, `anganwadi_centres`, `schools_pre_primary`,
  `schools_primary`, `schools_secondary`, `schools_higher_secondary`,
  `health_sub_centres`, `primary_health_centres`, `wellbeing_centres`,
  `dispensaries`, `ayurvedic_clinics`, `drinking_water_sources`,
  `households_tap_water`, `household_toilets`, `community_sanitary_complexes`,
  `solid_waste_centres`, `common_service_centres`, `banks`, `atms`,
  `rural_libraries`, `children_parks`, `disaster_rescue_centres`,
  `bus_stands_with_water`, `seed_centres`, `osr_collected`, `laptops`,
  `printers`, `scanners`, `sports_courts` (badminton + football + volleyball).
- **Measures, lifetime performance (all SUM, view3's expressions summed over
  the fiscal-year domain, so each equals the matching view3 column total):**
  `n_activities`, `n_costed`, `n_costless`, `planned_cost`,
  `sanctioned_total`, `expenditure_total`, `overspend_vs_plan`,
  `overspend_vs_sanction`, `n_admin_approvals`, `n_tech_approvals`,
  `n_completed`, `n_ongoing`, `n_abandoned`, `n_with_evidence`,
  `evidence_uploads`, `payment_amount`, `receipt_amount`, `n_plans`.
- **Impact measures:** `population_total`, `n_activities`.
- **No rate is materialised** (§3). Because the grain is GP, a SUM over any
  scope gives a correct numerator and a correct denominator at once —
  spend per household or approvals per activity are honest at block and
  district roll-up here and nowhere else. **The engine cannot form that
  ratio itself**: its measures are SUM or AVG of one column (WP-D2c's
  intensity measures are AVG-of-a-column, not a quotient). So v1 of view4
  ships numerators and denominators only; per-capita *mining* needs an
  engine ratio-measure extension, which is a separate engine WP and not
  part of Amendment B. The prose and decomposition layers can still state
  a per-household figure from the two columns.
- **Depth:** 1 at sample scale, 2 statewide (as view3).
- **Sample-scale expectation, stated in advance:** 20 rows, 9 districts.
  The engine will produce few rankable findings. The view is built,
  validated and mined now so the machinery and the glossary exist; it
  becomes a live signal statewide. Do not tune toward a sample gate on this
  view (handoff §4, "measure wrong or target unreachable").

### 12.5 Engine and calibration consequences

- Seven more dimensions on view1 at depth 2 enlarge the subspace
  enumeration. WP-D2c measured the current 17-dimension run at ~92 minutes
  on five workers; the WP re-measures before and after and reports the
  cost. If the re-mine exceeds the available budget, the fallback is to
  mine the profile dimensions on view1 as **subspace filters only** — the
  operator decides, not the agent.
- Every profile dimension is a new **extending dimension**, so findings of
  the form "holds in every ST-majority GP except X" become possible.
  That is the point of the amendment, and it is also where new spurious
  classes will appear. The WP-D2c labelled sheet remains the regression
  gate (no labelled-spurious class re-enters a top-15) and a calibration
  session on the new findings is required before any edition is published.
- **Regenerate all editions together** (handoff §4): feed, gamma editions,
  insight prose, retrieval and decomposition corpora all derive from one
  candidate set. A profile re-mine is a new candidate set.
- Column glossary entries for the seven dimensions and the ~60 view4
  measures are WP content; the prose layer must be able to say "GPs where
  Scheduled Tribes are more than half the population" rather than
  `social_composition = ST-majority`.
- **Correlation only, stated for the record.** A profile dimension makes a
  finding *about* a kind of GP; it never makes it *because of* that kind.
  Rule 4b of the report prompt and D41 apply unchanged.

### 12.6 Data oddities in `gp_profile` (log, never fix — extends §8)

10. `panchayat_area_total_area`: 1.11 to 3,000 across 20 GPs; three values
    (1,450 / 1,400 / 3,000) are two orders of magnitude off the rest —
    mixed units (hectares vs acres vs km²?). Excluded from every band.
11. Karuabahal reports **12 households** against 3,208 population, 1,256
    toilets and 1,658 job-card holders. Size banding uses population, so
    the band is unaffected; the WP-D2c degenerate guard should flag any
    per-household figure it produces.
12. `household_toilets > households` in 5 GPs; `households_tap_water >
    households` in 2 (Chikilli, Haldikudar). Coverage ratios from these
    columns are candidates, not headline measures, until statewide data
    shows whether this is systematic.
13. `children_population` = 0 in 9 of 20 GPs; ST population = 0 in 5
    (Biswamathpur, Sharagada, Mendarajpur in Ganjam; Barimunda, Itipur in
    Khordha): plausible for some, unlikely for all.
14. `general_no_of_destitue_homes_old_age_homes` = 110 in one GP; the
    column mixes a count of homes with a count of residents.
15. `basic_amenities_no_of_computer` is 1 on all 18 non-null rows; the
    laptop/printer/scanner counts vary. Likely a form default.
16. Email, mobile (already masked `977XXX7120`) and address are present in
    the source — X-pii, excluded from every view by operator ruling.

### 12.7 Ask parity

The §1 principle — views are the single source of numbers — means Ask needs
the same derived bands if it is ever to answer "how do ST-majority GPs
compare". That is an Ask-workstream item (a `v_gp_profile` serving view over
the same `stg_gp_profile` definitions), **not part of this WP**; logged here
so the two products do not drift.

### 12.8 Decisions for sign-off

| # | Decision | Recommendation |
|---|---|---|
| B1 | The six dimensions and their definitions (§12.3), incl. population cuts 2,500 / 5,000 / 10,000 and the 5 km remoteness cut | **APPROVED 2026-09-07** |
| B2 | Social composition: one three-way ST / SC / Mixed dimension at every scale; the two-way sample workaround is dropped | **RULED 2026-09-07** — design for statewide, not for the sample |
| B3 | view4 measure list (§12.4) — profile counts + lifetime performance, impact = population + activities | **APPROVED 2026-09-07** |
| B4 | view1 re-mine cost: full seven-dimension depth-2 run, with the subspace-filter-only fallback decided on measurement | **APPROVED 2026-09-07** — agent reports the measurement, operator picks |
| B5 | Decision numbering: Discover's D50–D59 block is exhausted at D59; this amendment needs a new block claimed in the PROJECT_PLAN governance row | **APPROVED 2026-09-07** — D60–D69 claimed in the D30 row |

**All five signed 2026-09-07 — Amendment B is the spec.** The work is one
WP (brief to follow): stage the
source, extend the crosswalk, write `stg_gp_profile` and `view4_gp_profile`,
append the dimension columns to views 1–3, extend `validation.yaml`, build
under `--strict`, write the configs and glossary, re-mine, re-rank,
calibration session, then regenerate every edition from the new candidate
set.

### 12.9 Post-signature corrections and rulings (WP-D11 / WP-D11b, 2026-09-11)

Measured by WP-D11 (`handoffs/WPD11_REPORT.md` §§8–9) and ruled by the
operator on 2026-09-11. The signed text of §12 is unedited; where this log
and §§12.1–12.8 disagree, this log wins.

1. §12.6.13: ST population is 0 in **three** GPs (Biswamathpur, Mendarajpur,
   Itipur), not five. Sharagada reports 16 and Barimunda 1 — the PM's table
   rounded both to zero. The entry's point stands.
2. §12.6: add — the **household count is unreliable across the column**, not
   in one GP: implied household size runs 0.51 to 267 across the twenty;
   Kalyansinghpur reports more households than people. A per-household
   figure on view4 is arithmetically honest and substantively unreliable
   at GP level until statewide data shows otherwise.
3. §12.4: the SUM-equality guarantee reads *exact on every count measure;
   equal to the paise and within 2 ULP on every money measure*. Bit
   equality is unachievable under IEEE-754 summation order.
4. §12.2: four columns had no role (`general_no_of_destitue_homes_old_age_homes`,
   `basic_amenities_panchayat_library`, the renewable-energy and
   rainwater-harvesting flags). Roled **`X-deferred`** — held out of every
   view, statewide candidates. §12.1's `basic_amenities` count is 18, not 17.
5. §12.3: `remoteness` is boundary-sensitive — two GPs report exactly 5 km
   and the signed "5 km or more is Far" gives 14/6; the other reading gives
   16/4. `has_csc` contradicts the CSC *count* in fifteen of twenty rows; the
   band is built from the flag as signed, and the glossary warns the two do
   not corroborate each other.
6. **Ruling (D61, 2026-09-11): size-band labels stay bare in the pack and are
   given their unit ("people") at prose time only.** No pack change; no
   view1 re-mine.
7. **Ruling (D61): views 3 and 4 gain averaged twins** (`_mean`, per GP /
   per GP-year) of the main measures, so bands of unequal membership are
   compared by the typical GP rather than by headcount. This is the
   WP-D2c intensity mechanism, not a ratio measure; §12.4's deferral of
   per-capita mining stands.
8. **Ruling (D61): causal wording is governed by one general sentence in
   every writer prompt, with no banned-word list**, outcome to be measured
   against the editions' word-scan gate (WP-D11b).
9. Open, not yet ruled: whether `work_proposed_cost` joins view4 (§9.G).

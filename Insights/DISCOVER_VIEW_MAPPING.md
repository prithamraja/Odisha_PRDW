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

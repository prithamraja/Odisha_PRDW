# WP-D1 report — `domain_pack_prdw/`

Executing `handoffs/WPD1_domain_pack.md` (Discover workstream, parallel to Ask).
Build date **2026-08-14**. No git operations performed — staging and committing
are the operator's.

---

## §0 Status

| # | Gate item | Verdict | Evidence |
|---|---|---|---|
| 1 | `--strict` build green on the local mirror from `Data/` alone | **PASS** | exit code 0, `0 failed check(s)`, 53.4 s; all six pre-view checks and all three post-view checks `[PASSED]` |
| 2 | T6 reconciliation complete; every delta explained by a documented defect | **PASS** | §2 — all eleven brief-specified targets hit exactly; five further deltas quantified, each traced to a named defect or to `v_approval`'s shape |
| 3 | Three Parquet views match the signed §4 specs | **PASS** | 12,704 / 1,440 / 120 rows; grains unique; zero geography nulls in any view; Chikilli keeps all six rows with `n_admin_approvals = 0` |
| 4 | `crosswalk.csv` covers 100% of staged columns; no excluded role reaches a view | **PASS** | 182 rows / 182 CSV columns, no phantoms; 0 `X-*` roles name an output column; 0 unclaimed view columns across all 113 output columns |
| 5 | Validation report delivered; report complete | **PASS** | `Insights/reports_prdw/validation_report.txt` (11.8 KB) and `view_summaries.txt` (10.0 KB); this document |

One item beyond the gate, because it is the workstream's actual purpose:
**Ask↔Discover parity is measured, not asserted.** `check_ask_parity.py` runs
`Data/create_views.sql` unmodified over the same CSVs and diffs the resulting
`v_activity` against `view1_activity_lifecycle.parquet`: **41 columns, 0
mismatching, all 12,704 activities**, with `days_since_sanction` and every
excluded-by-role column confirmed absent.

**Preconditions.** Three of four were met as written. `Data/` holds 19 CSVs,
`gram_panchayat` 20 rows, `planned_activity` 12,704 data rows;
`Insights/DISCOVER_VIEW_MAPPING.md` is committed and unmodified against `HEAD`;
no other *agent* was live on the tree. The working tree was **not** clean: two
PM-owned paths were dirty at start — ` M PROJECT_PLAN.md` and
`?? handoffs/WPD1_domain_pack.md` (the brief itself). Neither is in this WP's
scope and neither is a `Chatbot/` or `eval/` change, so I proceeded rather than
stopping; see decision journal D-14.

> **The tree moved under this run.** Three commits landed while WP-D1 was in
> progress — `84bf7c1` (track the DuckDB file and frontend, edits `.gitignore`),
> `73c9e1c` (frontend workstream) and `074dfc9` ("WP-D0 gate green (D22);
> domain_pack_prdw in progress"), which also added
> `handoffs/WPD2_mining_calibration.md`. I performed **no** git operation; the
> operator did. Two consequences worth knowing before staging:
>
> 1. `074dfc9` committed a **mid-flight snapshot** of this pack — `sources.yaml`,
>    `derived_columns.sql` and the three view files as they stood at that moment,
>    with no `validation.yaml`, `crosswalk.csv`, `README.md` or scripts. **A build
>    from that commit alone crashes**: the runner loads `validation.yaml`
>    unconditionally. The gate-green state is the working tree as it stands now,
>    which adds those four files plus one change to `derived_columns.sql` (the
>    `voucher_pk_norm` block of §5.1). Everything in this report describes the
>    current tree, rebuilt clean from it.
> 2. My `.gitignore` edit sits on top of `84bf7c1`'s version and preserves it —
>    the diff is purely the added `views_prdw/` block.

---

## §1 Build transcript summary

**Command** (run from the local mirror; `<M>` below is the mirror root):

```
python <M>/Insights/src/build_views.py \
    --pack       <M>/Insights/domain_pack_prdw \
    --data-dir   <M>/Data \
    --views-dir  <M>/Insights/views_prdw \
    --reports-dir <M>/Insights/reports_prdw \
    --strict
```

| | |
|---|---|
| Environment | Windows 11 Pro 22621, Python 3.14.0, DuckDB 1.5.1, PyYAML |
| Mirror | a local copy of `Data/` + `Insights/src/` + the pack, outside the Drive mount — DuckDB cannot spill temp files onto Drive |
| Runtime | **53.4 s** wall clock, clean run from an emptied `views_prdw/` and `reports_prdw/` |
| `--strict` outcome | **exit code 0**, `Done. 0 failed check(s).` |
| Sources registered | 19 / 19, every row count within the 1% tolerance at 0.0% diff |
| Outputs | `view1_activity_lifecycle.parquet` 320 KB, `view2_geo_month_cube.parquet` 36 KB, `view3_gp_performance.parquet` 14 KB |

Parquet outputs stay local and are gitignored (`.gitignore` now carries
`Insights/views_prdw/` and `views_prdw/`). The two reports are synced to
`Insights/reports_prdw/` and are committed. The report transcript contains the
mirror's absolute paths — that is the honest record of where the gate build ran.

---

## §2 Reconciliation table (T6)

All figures read back from the built Parquet files. Rupee sums are float sums, so
they carry ≤3 × 10⁻⁷ of summation-order noise against a differently-ordered sum
of the same values; "exact" below means exact to the paisa.

| Check | Target | **Actual** | Delta | Explanation |
|---|---|---|---|---|
| view1 rows | 12,704 | **12,704** | 0 | exact |
| view1 Σ`total_cost` | 773,088,536 | **773,088,536.00** | 0 | exact; equals Σ`activity_fund.fund_amount_total`, the §3 identity |
| view1 Σ`total_expenditure` | ≤ 253,475,090.46 | **253,475,090.46** | **0.00 across 20 rows** | the 20 orphan `activity_expenditure.activity_code`s (§8) carry ₹0.00 of `total_expenditure` between them, so the activity grain loses no SPENT rupees |
| view1 Σ`fund_sanctioned_total` | 288,438,745 − orphan approvals | **288,438,745.00** | 0 | there are **no** orphan approvals: `admin_approval` and `admin_approval_scheme` both have zero `activity_code` orphans against `planned_activity` |
| view2 rows | 1,440 | **1,440** | 0 | 20 GPs × 72 derived months (2020-04 … 2026-03) |
| view2 Σ`payment_amount` | 685,750,812 | **685,750,811.29** | 0 | exact |
| view2 Σ`receipt_amount` | 664,791,436 | **664,791,435.89** | 0 | exact |
| view3 rows | 120 | **120** | 0 | 20 GPs × 6 derived fiscal years |
| view3 Σ`n_activities` | 12,704 | **12,704** | 0 | exact |
| view3 Σ`n_admin_approvals` | 2,101 | **2,101** | 0 | exact |
| view3 Chikilli approval rows | 0 in every FY, rows present | **6 rows present, `n_admin_approvals` = 0 and `n_tech_approvals` = 0 in all six** | 0 | LEFT JOINs only; Chikilli carries 640 activities, ₹13,871,980 spent and ₹27,697,255 of payments across those six rows |

### Further deltas, quantified

Not in the brief's table, but each is a real subtraction a reader could trip over.

| Measure | View total | Source total | Delta | Cause |
|---|---|---|---|---|
| view1 Σ`approved_cost_action_plan` | 773,967,690.00 | 777,060,544.00 | **3,092,854.00** | the same 20 orphan expenditure codes — they carry ₹0 of `total_expenditure` but do carry action-plan cost |
| view1 Σ`tec_approval_cost` | 275,192,886.00 | 279,393,388.00 | **4,200,502.00** | 39 technical approvals sit on activities with **no administrative approval**; `v_approval` joins the technical approval onto the admin one, so they are invisible to `v_activity` too |
| view1 Σ`has_technical_approval` / view3 Σ`n_tech_approvals` | 2,095 | 2,134 rows | **39** | same cause. Ask reports the same 2,095 — see §4 |
| view2 Σ`activity_linked_expenditure` | 239,961,574.41 | 253,475,090.46 | **13,513,516.05** | exactly the 488 phantom-FY `activity_voucher` rows (§8.1), whose dates start 2026-04-09, past the cashbook's last month. Structural, not filtered |
| view2 Σ`sanctions_count` | 2,040 | 2,101 | **61** | 61 approvals are dated outside the cashbook window — 14 before 2020-04 (twelve of them on 2019-10-02) and 47 from 2026-04 on, including the single future-dated sanction of §8.2 |
| view2 Σ`sanctioned_amount` | 282,516,643.00 | 288,438,745.00 | **5,922,102.00** | the same 61 approvals |
| view2 Σ`work_proposed_amount` | 282,850,819.00 | 288,772,921.00 | **5,922,102.00** | the same 61 approvals |

**Every delta above has a named cause; none is unexplained.** view3 counts
approvals by fiscal year rather than by sanction month and therefore reconciles
to the full 2,101 — the two views disagree on purpose, because their time axes
differ, and both are labelled.

### Cross-view agreement

view1 and view3 are re-expressed over the same `stg_*` layer, never off each
other. They nevertheless agree to float noise on every shared measure:

| | Σ view1 − Σ view3 |
|---|---|
| `n_activities` | 0.0 |
| `total_cost` / `planned_cost` | 0.0 |
| `total_expenditure` / `expenditure_total` | 1.5 × 10⁻⁷ |
| `fund_sanctioned_total` / `sanctioned_total` | 0.0 |
| `overspend_vs_plan` | −3.0 × 10⁻⁷ (both −519,613,445.54) |
| `overspend_vs_sanction` | −7.5 × 10⁻⁹ (both −50,235,982.54) |
| `evidence_uploads` | 0.0 (both 8,267) |

### Structural checks

- **Geography completeness:** zero nulls across all six name+code columns in all
  three views. view1 spans 9 districts / 16 blocks / 20 GPs.
- **Zero-fill is doing work:** 1,181 of view2's 1,440 cells carry cashbook
  activity; 259 rows exist only because the grid is a full cross join. Those are
  the silent months a missing-row model would have hidden.
- **Other view1 totals against source:** `evidence_uploads` 8,267 on 1,675
  activities; `trainees_total` 127,588; `training_days` 18,704;
  `beneficiaries_expected` 206,929; `is_completed` 17; `is_ongoing` 2,110;
  `is_abandoned` 420; `is_under_approval` 36; `has_approval_cost_only` 140;
  `fund_tied_total` 176,648,427; `fund_untied_total` 596,440,109;
  `fund_abandoned_total` 61,747,975. All match the WP-D0 audit.

---

## §3 Validation summary

### Declared and passing

| Check | Declared | Result |
|---|---|---|
| 1 Row counts | 18 tables with `expected_rows`, 1% tolerance | all at 0.0% diff |
| 2 Primary keys | 16 | all unique |
| 3 Foreign keys | 20 | all **0 orphans** |
| 4 Null rates | logging only, >20% threshold | 68 columns logged; never fails |
| 5 Categoricals | 6 closed domains | all clean |
| 6 Date ranges | 5 columns, 1–10 yr window | 6.0 / 5.7 / 6.9 / 7.3 / 6.7 yrs |
| Post-view | 3 views, rows + grain | all three exact and grain-unique |

The 20 foreign keys are the whole geography spine (7), the planning spine (1),
all six activity-grain child links, all four approval links, and both money links
including the recovered voucher key. Every one holds at zero orphans, which is
what makes view1's folds safe and view3's LEFT JOINs honest.

### Deliberately NOT declared, with measured violation counts

Per T4's rule — `--strict` must be able to stay green, so a known-violated
constraint is measured here rather than declared and permanently red.

| Not declared | Measured violation |
|---|---|
| FK `activity_expenditure.activity_code → planned_activity.activity_code` | **20 orphan rows / 20 distinct codes** (12,724 expenditure codes vs 12,704 activities). ₹0.00 of `total_expenditure`, ₹3,092,854.00 of `approved_cost_action_plan` |
| FK `activity_voucher.voucher_pk → voucher.voucher_pk` (raw form) | **488 NULL** + **5,488 non-matching**: the non-null values are float text (`'186.0'`) against `voucher`'s integer text (`'1'`), so they match on **zero** rows as VARCHAR |
| PK `admin_approval_scheme.activity_code` | **6 duplicates** (2,107 rows / 2,101 activities) — the multi-scheme approvals `v_approval`'s `ARG_MAX` collapses. `row_id` is unique and is declared instead |
| PK `dim_code.code` | 717 rows / **463 distinct**. The real key is `(variable, code)`, which holds with zero duplicates; the runner's CHECK 2 takes a single column. A runner limitation, not a data defect |
| CATEGORICAL `status_label`, `theme`, `voucher.type`, district names | Observed domains, not closed. Asserting them would fail CHECK 5 on the statewide drop merely for arriving with more values, breaking D15's one-file-update promise. They are profiled in `view_summaries.txt` every build |

The `voucher_pk` mismatch is **new in WP-D1** (§5.1). It is not left as a silent
gap: `stg_activity_voucher.voucher_pk_norm` applies `v_asset`'s own double-cast
idiom, recovers all 5,488 links, and the FK **is** declared on that normalised
form — so the recovery itself is now pinned by a passing check. Nothing in the
data is repaired and no measure depends on the column.

### Defects logged and carried through, never fixed

All of mapping doc §8, re-measured: 488 phantom-FY voucher links (₹13,513,516.05,
dates 2026-04-09 → 2026-08-03); one future-dated sanction (2026-08-19); the
`'Buildings'` status mis-decode (13 activities) and the tab-prefixed
`WORK COMPLETED` (17, cleaned by `v_activity`'s own `TRIM`/`chr(9)` and therefore
correctly bucketed); only 17 completed activities sample-wide;
**233 of 717** `dim_code` rows without a description; `plan.plan_code_status`
always null; `voucher.month` redundant with `date`; 2 activities losing their
multi-scheme funding split; `gp_name` denormalised on both approval tables.
`'Theme 5 - Clean and Green Village '` keeps its trailing space in view1 —
verified present in the Parquet, length 34, on 2,127 rows.

---

## §4 Pack design notes

### Deltas from `create_views.sql` semantics

**Exactly one, as expected.** `v_activity.days_since_sanction` is not
re-expressed: it is `DATE_DIFF('day', sanction_day, CURRENT_DATE)`, so its value
depends on when the build runs (mapping doc §3). It is comment-marked as
`-- DELTA` in `derived_columns.sql` and its absence from view1 is asserted by
`check_ask_parity.py`.

Everything else that a `v_*` view carries and this pack does not is a
**projection** decision from §7, not a change of meaning: `activity_name`,
`activity_desc`, `search_text`, `plan_code`, `expenditure_id`,
`v_exp.scheme_name` (82% null), `sanction_authority_raw`,
`tec_approval_authority`, `adm_approval_no`, `tec_approval_order_no`, the raw
decode codes, and the sanction date columns (§4.1 gives view1 no temporal
dimension). All are consumed inside `derived_columns.sql` and cannot reach a
Parquet file.

**No `v_*` semantic required changing, so nothing was escalated under T2's STOP
clause.** The parity diff is the evidence: 41 columns identical on 12,704 rows.

**One semantic worth the operator's eye, carried unchanged.**
`v_approval` starts `FROM admin_approval` and LEFT JOINs `technical_approval`, so
a technical approval on an activity with no administrative approval is invisible.
That is 39 approvals and ₹4,200,502. view3's `n_tech_approvals` therefore totals
**2,095**, not the 2,134 rows in `technical_approval`. Ask reports the same
2,095, which is exactly why I did not "fix" it — counting them would split Ask
and Discover on a headline number. If the operator wants view3 to report 2,134,
that is a mapping-doc amendment (§3 / §4.3) plus a matching change on the Ask
side, not a pack edit. Flagged, not decided.

### Calendar and fiscal-year derivation

Both spines derive themselves; no literal, no wall-clock value, nothing
sample-scaled appears in any view SQL.

- `stg_month_calendar` = `DATE_TRUNC('month', MIN(voucher.date))` …
  `DATE_TRUNC('month', MAX(voucher.date))`, stepped monthly. On this drop:
  **2020-04 … 2026-03, 72 months**, giving 20 × 72 = 1,440 view2 rows. Because
  the window ends where the cashbook ends, the 488 phantom-FY links are excluded
  **structurally** — there is no calendar row for 2026-04 for them to attach to
  — rather than by a filter that would have to be rewritten statewide.
- The same rule clips sanctions: 61 approvals fall outside the window (§2). This
  is a genuine consequence of routing view2's time axis through the cashbook, and
  the arithmetic is stated in the view's own header comment.
- `stg_fiscal_year_domain` = the union of fiscal years observed in
  `planned_activity`, `plan` and `voucher` — six here. `activity_voucher` is
  deliberately outside the union because it is the only table carrying
  `2026-2027`, on the 488 orphan rows. Excluding the *source* rather than
  filtering a literal keeps §5.3's exclusion true when statewide data arrives.
- view2's `fiscal_year` is derived from the calendar month (April–March) rather
  than read off `voucher.fiscal_year`, so a zero-filled cell still has one. The
  two agree on all 12,440 voucher rows and all 5,976 activity_voucher rows —
  verified, not assumed.

### Attribution rule in view3

Everything hanging off an activity is attributed to that **activity's** GP and
fiscal year, approvals included. Verified rather than assumed:
`admin_approval`'s own fiscal year (`plan_year` + 1) equals
`planned_activity.fiscal_year` on **all 2,101** approvals, and
`activity_expenditure.fiscal_year` equals it on every matched row. Cashbook
payments and receipts use `voucher.fiscal_year` because they are GP-level flows,
many belonging to no activity; plans use `plan.fiscal_year`.

### Sample → statewide

Sample-scale numbers exist in exactly two places, as D15 requires:
`sources.yaml` `expected_rows` (18 tables) and `validation.yaml` `post_view`
(3 views). The five sparse candidate dimensions of §9.7 are **carried in view1**
so that switching to statewide stays a `VIEW*_CONFIG` edit and not a pack change,
as §6's switch plan promises.

---

## §5 Data oddities — new findings beyond mapping doc §8

Logged, not fixed. Ordered by how much they could mislead a reader.

1. **`activity_voucher.voucher_pk` never matches `voucher.voucher_pk` as text.**
   `activity_voucher` stores the key in float form (`'186.0'`, lengths 4–7),
   `voucher` in integer form (`'1'`, lengths 1–5). A VARCHAR join returns **0 of
   5,488** rows; a numeric normalisation returns all 5,488. §8.1 describes the
   488 NULL-`voucher_pk` rows as "orphan links" and is right about those, but the
   *other* 5,488 are also unusable without normalising. No number in this pack
   depends on the join — view2 reads `activity_voucher.voucher_cost` directly —
   so nothing is wrong in the outputs, but any future work that joins the
   cashbook to activity spend must normalise first. Recovered as
   `stg_activity_voucher.voucher_pk_norm`; the FK is declared on it.

2. **39 technical approvals have no administrative approval**, carrying
   ₹4,200,502 of `tec_approval_cost`. Invisible to `v_approval`, therefore to
   `v_activity`, therefore to view1 and view3. See §4 — carried unchanged and
   flagged for a mapping-doc decision.

3. **`output_type` is a dimension with no labels.** All eight `output_type` codes
   are present in `dim_code` with a **NULL description**, so
   `output_type_label` is `'Code 101'` … `'Code 110'` for every one of the 12,704
   activities. §4.1 lists it as a view1 dimension; it will mine as eight opaque
   codes until the decode is supplied. Same for all three
   `community_service_code` values.

4. **`dim_code` has no `training_category_code` or `training_organiser_code`
   rows at all** — the decode target for two of §7's `decode→dim` columns simply
   does not exist, so both labels are `'Code N'` throughout. Consistent with
   §9.7's "mine them only statewide", but worth recording that the gap is a
   missing decode table, not a sparse one.

5. **`activity_expenditure.sc` and `.st` are swapped in the source data.**
   Diagnosed rather than merely observed — the first framing of this finding left
   open which of two tables was wrong, and it is resolvable.

   The symptom: `admin_approval_scheme.fund_sanctioned_sc` = **₹440,000** (2 rows)
   and `_st` = **₹3,226,802** (19 rows), while `activity_expenditure.sc` =
   **₹3,226,802** (19 rows) and `.st` = **₹440,000** (2 rows). The row *counts*
   swap too, which already rules out coincidence.

   Read at activity grain it is exact. Twenty-one activities carry a non-null
   SC or ST value on either side. **All 21 are crosswise equal — same activity,
   same rupee amount, opposite label. Zero are straight-equal.**

   Three independent sources agree with `admin_approval_scheme` and against
   `activity_expenditure`:

   | Evidence | Says |
   |---|---|
   | `planned_activity.activity_for` (the beneficiary-category code: 112 = sc, 113 = st) | the 2 activities are `112`/SC and the 19 are `113`/ST — matching `fund_sanctioned_sc` / `_st` |
   | `activity_fund.fund_tied_sc/_st` and `fund_untied_sc/_st` (the PLANNED split) | same orientation as the sanctioned columns on all 21 |
   | `admin_approval_scheme` itself | as above |

   Example: activity `48344875` is `activity_for = 112` (SC), has
   `fund_tied_sc = 350,000` and `fund_sanctioned_sc = 350,000` — and
   `activity_expenditure.st = 350,000`. Three tables call it SC; expenditure
   alone calls it ST.

   **Not introduced by this pack, and not by Ask.** Verified against the raw CSVs
   as pure text: both files' header lines match their column positions, so there
   is no shifted-column ingestion bug. `sources.yaml` casts the columns to float
   under their own names and nothing renames or reorders them; `v_exp` does
   `SUM(sc) AS sc_amount, SUM(st) AS st_amount`. Both systems pass the defect
   through faithfully, which is the correct behaviour — **and it means Ask has the
   same inversion**: `v_activity.sc_amount` / `st_amount` are label-swapped for
   these 21 activities, so any Ask answer distinguishing SC from ST expenditure is
   currently inverted. That is a Chatbot-workstream finding, out of this WP's
   scope to act on, but the operator should know it did not originate here.

   **A caveat on the reading.** A genuine reallocation — sanctioned under ST,
   spent under SC — is conceivable in principle. It is not what this looks like:
   a reallocation would not produce exact per-activity value equality on 21 of 21
   with none straight, and would not put the *planned* funding split on the
   sanctioned side too. Calling it a column-labelling error upstream is the
   reading the evidence supports; ruling on it is the SME's call, and **nothing
   has been changed either way**.

   Scope of the impact is small and bounded: 21 activities, ₹3,666,802 combined,
   and the combined total plus §4.4's conclusion — too thin for an equity view —
   hold under either reading. It matters because it is exactly the class of
   defect that silently inverts an equity finding once statewide data makes these
   columns non-trivial.

   **Tracked for the data provider** as Q1 in
   `handoffs/DATA_PROVIDER_QUESTIONS.md`, opened from this finding.

   Separately, **mapping doc §3's parenthetical is transposed**: it annotates
   `fund_sanctioned_total (+ gen/sc/st)` with "sc ₹3.2M / st ₹0.4M", which is the
   expenditure orientation, not the sanctioned one. Measured on the sanctioned
   columns it is sc ₹0.44M / st ₹3.23M.

   **Proposed replacement for `DISCOVER_VIEW_MAPPING.md` §11 item 5.** The
   amendments log the PM opened while this report was being written records the
   symptom ("the two source tables carry these values swapped relative to each
   other … possible column transposition at source") from the first pass, before
   the direction was resolved. It is now resolvable, so item 5 can say which
   table is wrong. Proposed text — the doc is not edited here:

   > 5. §3 sanctioned sc/st parenthetical ("sc ₹3.2M / st ₹0.4M"): measured on
   >    the sanctioned columns it is **sc ₹0.44M / st ₹3.23M** — the
   >    parenthetical carries the *expenditure* orientation.
   >    `activity_expenditure.sc`/`.st` are **transposed at source**, not merely
   >    "swapped relative to" the sanctioned table: on all 21 affected activities
   >    the values are crosswise equal with none straight, and
   >    `planned_activity.activity_for` (112 = sc, 113 = st) **and**
   >    `activity_fund`'s planned splits both side with `admin_approval_scheme`.
   >    Three sources against one. Ask carries the same inversion via
   >    `v_exp`, so this is a data-provider question, not a pack or catalogue
   >    defect — tracked as Q1 in `handoffs/DATA_PROVIDER_QUESTIONS.md`.
   >    §4.4's too-thin-for-equity conclusion is unaffected either way.

6. **`authority_clean`'s `ELSE` branch passes raw free text through.** Four
   families collapse cleanly (Sarpanch 1,319 / BDO 347 / Engineer 250 / Gram
   Panchayat 170), but 15 rows across ten values fall through to
   `TRIM(adm_approval_authority)` — `'12'`, `'S'`, `'sar'`, `'SWARPANCH'`,
   `'GRAMPANCHAYATKS'`, `'KALYANSINGHPUR'`, `'14'`, `'15'`. None is a personal
   name in this sample, so §9.6 holds here, but the *mechanism* means a personal
   name in a statewide `adm_approval_authority` would reach a Discover dimension
   verbatim. Sample cardinality is 14, not the "~8" §2 estimates. Recommend WP-D2
   either bucket the residue as `'Other'` or have the SME confirm the branch.

7. **`asset_loc_overflow_json` is not empty.** §7 roles it `X-empty`; it has 54
   non-null rows (99.6% null). The role stands on the null rate; the label
   `X-empty` is literally wrong. Recorded in `crosswalk.csv` with the measurement.

8. **`asset_category_label` has 28 distinct values, not "36 + Uncategorised".**
   All 36 codes are in use, but 8 carry no description and several share one, so
   27 named labels plus `'Uncategorised'` reach view1. `'Uncategorised'` covers
   8,439 activities — 8,418 with no asset row at all, plus 21 with a
   description-less code. A reader must not read it as an asset category.

9. **`plan.approval_date` is non-null on all 204 rows**, so `v_plan`'s
   `is_approved` is constant 1 in this drop. No Discover view carries it (§4.3
   takes only `n_plans`), but the glossary should not promise an approval-rate
   measure that the data cannot vary.

10. **`activity_delegation` is emptier than §7 implies, in a different place.**
    §7 says "is_shareable constant False; rest fully null". Measured:
    `is_shareable` is `'False'` on 11,289 rows and NULL on 1,415;
    `is_delegated` is **100% null**, as are the other six columns. The
    conclusion — the table feeds nothing — is unchanged.

---

## §6 Decision journal

Decide-and-document entries. Everything here was within the brief's
decide-and-document class; nothing hit the STOP class.

**D-1 · `date` casts vs the runner's CHECK 6.**
*Decision:* how to satisfy both "§7 dates → `date`" (T1) and "declare date
ranges" (T4), when the runner's `_check_date_ranges` calls `.date()` on the
min/max it reads back — which `datetime.date` does not have, so a DATE column
aborts the build with `AttributeError`.
*Options:* (a) cast the five dated columns as `timestamp`, the documented
`domain_pack_rtgs` precedent — but that breaks T1's cast rule; (b) drop CHECK 6
entirely — but that abandons a whole declared check class; (c) keep the `date`
casts and expose TIMESTAMP twins in the staging layer for the check to read.
*Choice:* (c). Five `<col>_ts` columns in `stg_voucher`,
`stg_activity_voucher`, `stg_admin_approval`, `stg_technical_approval`,
`stg_plan`, each commented as existing only for the runner. No view projects
them. §7's roles stay intact and the date-range check runs for real.
*Reversal cost:* five lines; or one line each in `sources.yaml` for option (a).

**D-2 · Absence handling in the two overspend measures.**
*Decision:* whether `total_cost` and `fund_sanctioned_total` coalesce to 0 in the
signed differences.
*Options:* coalesce both; coalesce neither; split them.
*Choice:* split, on what the null *means*. `total_cost` is null **iff** the
activity is costless — i.e. planned at zero — so `overspend_vs_plan` coalesces:
an activity spending against no planned cost must surface as overspend, not
vanish into NULL. `fund_sanctioned_total` is null because no approval record
exists, and §3 says explicitly that absence of a record is not a sanction of
zero, so `overspend_vs_sanction` stays null on the 10,603 unapproved activities.
Measured on this drop the two are indistinguishable — costless activities carry
₹0.00 of expenditure, so both conventions give −519,613,445.54 — which means the
choice pins *statewide* behaviour, not this build's numbers.
*Reversal cost:* one `COALESCE` per view, two views.

**D-3 · view2 carries two SANCTIONED amounts.**
*Decision:* §4.2 names a measure `sanctioned_amount` and sources it "(admin_approval
by sanction month)", but the approval record has two money columns on the
SANCTIONED basis: `admin_approval.work_proposed_cost` and the scheme rollup's
`fund_sanctioned_total`.
*Options:* pick one and risk picking the wrong one; carry both, named
unambiguously.
*Choice:* both — `sanctioned_amount` = Σ`fund_sanctioned_total` (the §3 headline
measure) and `work_proposed_amount` = Σ`work_proposed_cost`. Neither substitutes
for the other and a reader must never have to guess which is which. Both are §3
measures at the §4.2 grain, so neither is an invention.
*Reversal cost:* delete one `SELECT` line.

**D-4 · `is_costless` exposed as a label, raw 0/1 not carried.**
*Decision:* §2 names the dimension `is_costless` with values Costed/Costless;
§7 roles the column `is_costless_activity` as `dim`; `v_activity` exposes the raw
`'0'`/`'1'`.
*Choice:* view1 carries `is_costless` (Costed/Costless) only. The raw flag would
be an `X-derived` duplicate and mines as two meaningless strings. The parity check
compares the derived label against `v_activity`'s raw flag, so the mapping is
verified rather than assumed.
*Reversal cost:* one `SELECT` line.

**D-5 · Sparse candidate dimensions carried into view1.**
*Decision:* §9.7 says stage the sparse candidates and mine them only statewide;
§4.1's dimension list omits them.
*Options:* leave them out of the view (statewide then needs a *view* change);
carry them (five extra mostly-null columns nobody mines in v1).
*Choice:* carry `planned_fund_scheme_name`, `planned_fund_component_name`,
`training_category_label`, `training_organiser_label`, `community_service_label`.
§6's switch plan promises statewide is a config edit — that is only true if the
columns exist. `crosswalk.csv` records each as staged-for-statewide.
*Reversal cost:* five `SELECT` lines and five stg_ derivations.

**D-6 · view3 re-expresses off `stg_*`, not off view1.**
*Decision:* view3 could read `view1_activity_lifecycle` directly — the runner
creates views as temp views in sorted filename order in one connection, so view1
exists when view3 runs.
*Choice:* re-express off `stg_*`. Reading view1 would make view3 depend on
filename ordering, which a rename could silently break; the shared staging layer
is the real guarantee of agreement. Verified: every shared measure agrees to
≤3 × 10⁻⁷ (§2).
*Reversal cost:* rewrite view3's `activity` CTE; the risk of divergence is what
the §2 cross-view table exists to catch.

**D-7 · view3 attributes approvals by the activity's fiscal year.**
*Decision:* `admin_approval` carries its own `plan_year`; `planned_activity`
carries `fiscal_year`. Which does `n_admin_approvals` use?
*Choice:* the activity's, so that `n_admin_approvals`, `sanctioned_total`,
`overspend_vs_sanction` and `n_tech_approvals` all sit on the same rows. Safe
rather than assumed: the two agree on **all 2,101** approvals (measured), so the
choice changes no number in this drop and only fixes the semantics if they ever
diverge.
*Reversal cost:* a separate CTE keyed on `stg_admin_approval.fiscal_year`.

**D-8 · `sanction_scheme_rows` carried in view1.**
*Decision:* whether to expose `v_approval.scheme_rows` (machinery, absent from
§3's measure census) or drop it.
*Choice:* carry it, as `sanction_scheme_rows`. The `ARG_MAX` rollup silently
collapses six multi-scheme approvals; this column is the only trace of that
collapse inside the Parquet, and it is a count that sums honestly (Σ = 2,107 vs
2,101 approvals). It traces to `create_views.sql`, so T2's rule is satisfied.
*Reversal cost:* one `SELECT` line.

**D-9 · `voucher_pk_norm` added, and the FK declared on it.**
*Decision:* what to do about the float-text/integer-text key mismatch (§5.1) —
"no data fixes, ever".
*Options:* record it in the report only; add a normalised key in the staging
layer.
*Choice:* add it. A normalising cast in a `stg_` view is a *derivation*, not a
repair — it is literally the same double-cast idiom `v_asset` already applies to
the same class of problem in `create_views.sql`. Nothing is written back, no
measure depends on it, no view projects it. It exists so the constraint can be
declared and checked rather than sitting silently between two tables.
*Reversal cost:* one line in `derived_columns.sql`, one FK entry.

**D-10 · view2's `quarter` is the calendar quarter, formatted `YYYY-Qn`.**
*Decision:* §4.2 says "quarter" without saying calendar or fiscal, or what shape.
*Choice:* calendar quarter, matching `v_approval`'s `QUARTER(...)`, rendered
`'2020-Q2'` so it sorts in calendar order without parsing. `month` gets the same
treatment (`'YYYY-MM'`). `fiscal_year` is on the same row for anyone who wants
the April–March frame.
*Reversal cost:* one expression.

**D-11 · CHECK 5 limited to closed domains.**
*Decision:* which categoricals to assert, given `--strict` and D15's promise that
statewide is a one-file update.
*Choice:* the four structurally closed source domains the brief names
(`direction`, `plan_type`, `tec_approval_required`, `is_costless_activity`) plus
the two closed by this pack's own `CASE` construction (`is_costless`,
`tied_untied`). `status_label`, `theme`, `voucher.type` and district names are
*observed* domains — asserting them would fail statewide for the wrong reason.
They are profiled in `view_summaries.txt` every build.
*Reversal cost:* one YAML block; the reasoning is in the file's header so a future
reader does not re-litigate it.

**D-12 · Two maintenance `.py` scripts ship inside the pack.**
*Decision:* the pack format is "declarative YAML + SQL — no Python".
*Choice:* ship `build_crosswalk.py` and `check_ask_parity.py` anyway, both
prominently marked as not-pipeline in their docstrings and in the README. The
rule is about what the *runner* executes; these generate and verify delivered
artefacts. The alternative — a hand-maintained `crosswalk.csv` and a parity claim
nobody can re-run — trades a format purity point for two guarantees going stale.
`build_views.py` reads neither.
*Reversal cost:* delete both; `crosswalk.csv` then becomes hand-maintained and
the parity claim becomes an assertion.

**D-13 · `row_count_tolerance_pct: 1`.**
*Decision:* the pack default is 20.
*Choice:* 1. These are exact known counts, not estimates; a 1% drift is a real
change in the drop and should stop a `--strict` build. Same tolerance on all
three `post_view` blocks.
*Reversal cost:* one line.

**D-14 · Proceeded with a not-quite-clean working tree.**
*Decision:* the precondition asks for a clean tree; ` M PROJECT_PLAN.md` and the
untracked brief were present at start.
*Choice:* proceeded. Both paths are PM-owned and explicitly out of this WP's
scope, neither is a `Chatbot/` or `eval/` change (the case the brief says to ask
about), and `DISCOVER_VIEW_MAPPING.md` — the signed input that actually matters —
is committed and unmodified against `HEAD`. Recorded here rather than silently.
*Reversal cost:* none; this is a disclosure, not a change.

---

## §7 Self-audit

**Verified directly, by running it:**

- The `--strict` build, end to end, from an emptied output tree: exit 0, 0 failed
  checks, 53.4 s. Re-run from a fresh copy of the committed pack after the final
  edits, so the transcript matches what is in the repo.
- Every figure in §2, read back from the built Parquet files rather than from the
  build log.
- **Ask↔Discover parity by run-and-diff**, not by reading: `create_views.sql`
  executed unmodified over the same CSVs, `v_activity` diffed against
  `view1_activity_lifecycle.parquet` across 41 columns — every decode, both
  authority and scheme derivations, all nine flags, the whole expenditure rollup
  — **0 mismatches on 12,704 activities**. Replayable:
  `python Insights/domain_pack_prdw/check_ask_parity.py`.
- The T5 gate checks, mechanically: 182 crosswalk rows against 182 CSV columns
  with no phantoms either way; 0 `X-*` roles naming an output column; 0 stale
  output-column claims; 0 unclaimed view columns across all 113.
- Every §8 defect count, and every new finding in §5, measured from `Data/`.
- The two derived spines behaving as designed: 72 months from the cashbook's own
  span, 6 fiscal years from the three-table union with `2026-2027` structurally
  absent.
- That `voucher.fiscal_year` and `activity_voucher.fiscal_year` agree with their
  own dates' April–March fiscal year on every row (12,440 and 5,976), and that
  `admin_approval`'s derived fiscal year equals `planned_activity.fiscal_year` on
  all 2,101 approvals — the assumptions D-7 and the view2 FY derivation rest on.
- That all 48 declared numeric/date casts parse without silently nulling a value:
  cast-non-null equals raw-non-null on every cast column. `longitude_raw` /
  `latitude_raw` were tested and **fail** a float cast (they hold comma-joined
  coordinate lists), which is why they stay VARCHAR.

**Not verified — relied on prior work:**

- The `Data/` CSVs ↔ `panchayat_1.duckdb` identity (PM-validated, plan §5.5). The
  parity check compares Discover against Ask's *SQL* run over the CSVs; it does
  not prove the CSVs equal the database the Ask chatbot actually queries.
- The data dictionary and the workbook's view-usage counts.
- WP-D0's §2 cardinality figures beyond the ones §2/§5 above re-measure.

**Not done, by scope:**

- No engine run, no `VIEW*_CONFIG`, no `discover_config.py` (WP-D2). No feed or
  report generation (WP-D3). No LLM API call. No git operation. No file touched
  outside `Insights/domain_pack_prdw/**`, `Insights/reports_prdw/**`,
  `handoffs/WPD1_REPORT.md` and `.gitignore`. `DISCOVER_VIEW_MAPPING.md` is
  unedited — the amendments §5 proposes are proposals.
- No statewide extrapolation. Every number here is the 20-GP sample.

**What the PM should replay:**

1. `python Insights/src/build_views.py --pack Insights/domain_pack_prdw --data-dir Data --views-dir Insights/views_prdw --reports-dir Insights/reports_prdw --strict`
   from a **local** copy — expect exit 0 and 12,704 / 1,440 / 120.
2. `python Insights/domain_pack_prdw/check_ask_parity.py` — expect
   `41 columns compared, 0 mismatching` and exit 0. This is the one check that
   would catch a silent Ask↔Discover divergence, and it should run after any
   future edit to `derived_columns.sql` or `views/view1_*.sql`.
3. `python Insights/domain_pack_prdw/build_crosswalk.py` — expect four zeros and
   `182 column rows`, with `crosswalk.csv` unchanged afterwards.
4. §2's "further deltas" table — the five non-brief deltas are where a reviewer
   is most likely to disagree with my reading, especially the 39 technical
   approvals (§4) and view2's 61 clipped sanctions.

**What the operator (SME) should confirm:**

1. The T6 table in §2.
2. **§5.5 — `activity_expenditure.sc` / `.st` are swapped in the source data**,
   on all 21 affected activities, against three corroborating sources. Two
   consequences to rule on: whether to raise it with the data provider, and that
   **Ask carries the same inversion** in `v_activity.sc_amount` / `st_amount` —
   a Chatbot-workstream item, not a pack defect.
3. **§4 / §5.2 — `n_tech_approvals` = 2,095 rather than 2,134**, carried
   unchanged to keep Ask and Discover agreeing. Changing it is a mapping-doc
   amendment, not a pack edit.
4. **§5.6 — `authority_clean`'s pass-through `ELSE` branch**, which would let a
   personal name in `adm_approval_authority` reach a Discover dimension verbatim
   in statewide data.

---

## §8 Filling WP-D2's `⟦PENDING-WPD1⟧` slots

`handoffs/WPD2_mining_calibration.md` appeared in the tree during this run
(commit `074dfc9`) and was drafted before these views existed, so its fact 9
carries two slots the PM fills from here. Both are now measurable.

**Slot 1 — view1 column count:** view1 is **12,704 × 70**. view2 is 1,440 × 17;
view3 is 120 × 26.

**Slot 2 — column names / renames: there are none.** Every column named in
WP-D2's T1 config table exists **verbatim** in the built Parquet files —
checked mechanically, not by eye:

| | dimensions | temporal | measures | impact | missing |
|---|---|---|---|---|---|
| view1 | 17 | 0 | 24 | 2 | **0** |
| view2 | 4 | 3 | 7 | 2 | **0** |
| view3 | 3 | 1 | 18 | 2 | **0** |

Appendix A can be transcribed verbatim with no name adjustments. The columns
present in the views but *not* named by WP-D2's configs are all intentional and
should stay out of the configs: the six LGD code columns (WP-D2 fact 2 — the
frontend contract keeps them, mining must not), the §7 `meas`-roled columns not
on the mining list (`approved_cost_action_plan`, `technical_approved_cost`,
`admin_approved_cost`, `tec_approval_cost`, the gen/sc/st fund splits,
`asset_unit_cost`, `training_days`, `community_service_days`,
`sanction_scheme_rows`, `has_approval_cost_only`), the five sparse candidate
dimensions staged for statewide per §9.7, `asset_type_label`,
`tec_approval_required`, and view2/view3's `work_proposed_amount` /
`work_proposed_cost` (decision journal D-3).

**Six glossary corrections Appendix A needs**, all from §5 above — content, not
column names, so T2 can still transcribe and then patch these lines:

0. `sc_amount` / `st_amount` (view1) — Appendix A calls them "SPENT basis, by
   social-category component". Per §5.5 the two labels are **swapped at source**:
   `sc_amount` holds the ST rupees and vice versa, on all 21 affected activities.
   The glossary must say so, because "a near-zero here is data coverage, not a
   finding" is not enough — the non-zero values are on the wrong label. This is
   the one glossary line where the current wording could produce a *confidently
   wrong* equity statement rather than a vague one.

1. `output_type_label` — Appendix A says "8 values" and that "'Unknown' means the
   code has no decode on file". For `output_type` **every** code lacks a decode,
   and the fallback string is `'Code 101'`…`'Code 110'`, not `'Unknown'`. As
   written the glossary implies eight meaningful categories (§5.3).
2. `sanction_authority` — Appendix A lists five cleaned offices. The measured
   cardinality is **14**: the five, plus ten low-count free-text residues
   totalling 15 rows that fall through `authority_clean`'s `ELSE` branch (§5.6).
3. `asset_category_label` — Appendix A says "36 categories". **28 distinct labels**
   reach view1 (27 named + `'Uncategorised'`), and `'Uncategorised'` covers 8,439
   rows: 8,418 activities with no asset row plus 21 with a description-less code
   (§5.8). "the two-thirds of activities without asset data" is right.
4. view3 `n_tech_approvals` — should carry the §4 note that it totals **2,095**,
   not the 2,134 rows in `technical_approval`, because `v_approval` hangs the
   technical approval off the administrative one. Ask reports the same 2,095.
5. view2 `sanctions_count` / `sanctioned_amount` — should note that view2 counts
   **2,040** of the 2,101 sanctions, because its time axis is the cashbook's and
   61 approvals are dated outside it (§2). view3 counts by fiscal year and
   reconciles to the full 2,101. Two views, two numbers, both correct.

Everything else in Appendix A checks out against the build: costless at 56% of
rows (7,074 / 12,704), the ~8× count jump at FY 2023-24 (609 → 4,607), 986
unmapped-theme activities, 8,267 uploads on 1,675 activities, 1,034 training and
763 community-service subsets, ₹61.7M of abandoned funding, and the status_label
distribution (10,108 / 2,110 / 420 / 36 / 17 / 13) exactly as printed.

WP-D2's precondition "WP-D1 is gate-green and committed" is **not yet met on the
committed tree** — see the §0 note. It becomes true once the operator commits the
current working tree.

# `domain_pack_prdw` — Odisha Panchayati Raj & Drinking Water

The Discover domain pack for the Odisha PR&DW dataset. Format and runner
contract are `../domain_pack/README.md`; this file records only what is specific
to this domain — what the pack builds, the one deviation from the Ask views, and
the constraints it deliberately does not declare.

Built and gate-checked in **WP-D1**; the reconciliation evidence is
`../../handoffs/WPD1_REPORT.md`, and the design it implements is
`../DISCOVER_VIEW_MAPPING.md` (operator-signed, D22). Where the mapping doc is
specific, this pack has no design freedom.

```
domain_pack_prdw/
├── sources.yaml          19 tables, explicit casts, sample-scale expected_rows
├── derived_columns.sql   stg_* layer: create_views.sql re-expressed, + 2 spines
├── views/                the three §4 views -> three Parquet files
├── validation.yaml       checks + post-view grains (the 2nd sample-scale file)
├── crosswalk.csv         §7 materialised: 182 staged columns -> role
├── known_events.csv      dated real-world events the reading notes may cite
├── build_crosswalk.py    regenerates crosswalk.csv + runs the T5 gate checks
├── check_ask_parity.py   diffs view1 against Ask's own v_activity
└── README.md             this file
```

## `known_events.csv` — context the data does not carry

Added in **WP-D2c (A5)**, on calibration session 1 ruling 5. The operator read
view2's August 2020 change point and its FY 2020-21 ramp and said one word:
COVID. Nothing in this dataset knows that. The engine can find a shift in a
month; it cannot know what else was happening that month, and the report's
hardest rule (`phase5b_report.py`, prompt rule 4b) forbids the model from
supplying a cause — a rule that exists because an earlier deployment invented
one and was wrong.

So the events are **data, not prose**: four columns — `event`, `start_month`
(`YYYY-MM`), `end_month`, `note` — read by `phase5b_report.known_events()`. A
finding earns a citation only on a date test, never on a resemblance:

- a `CHANGE_POINT`, `OUTLIER` or `UNIMODALITY` highlight whose month, quarter or
  fiscal year falls inside an event window, **or within three months after it**
  (a resumption is as dated as an interruption, and the Ganjam shift is at
  2020-08 against a window that closes in 2020-06); or
- a finding whose own subspace pins a month, quarter or fiscal year overlapping
  the window.

The citation is appended to the section's deterministic reading note, states
the overlap as an overlap of dates, and prints the `note` column verbatim. It
never says the event caused the pattern, and the model never writes it.

**Adding events is an operator/SME job, not an engine change.** The file ships
with the COVID first-wave window and two `TODO(SME)` template rows, which the
loader skips: any row whose `event` begins `TODO(SME)`, or whose months are not
`YYYY-MM`, is ignored, so a half-filled row cannot reach a report. Cyclones and
election dates are the obvious next entries and the department has them.

The two `.py` files are **maintenance scripts, not pipeline**: `build_views.py`
never reads them, and the pack itself stays declarative YAML + SQL. They exist
because two of this pack's guarantees are claims that ought to be measured rather
than asserted — that `crosswalk.csv` still describes the views it ships with, and
that Discover's numbers still equal Ask's. Run both after any pack edit:

```bash
python Insights/domain_pack_prdw/build_crosswalk.py    # 4 gate checks, rewrites crosswalk.csv
python Insights/domain_pack_prdw/check_ask_parity.py   # exits non-zero on any divergence
```

## Run it

```bash
python Insights/src/build_views.py \
    --pack Insights/domain_pack_prdw \
    --data-dir Data \
    --views-dir Insights/views_prdw \
    --reports-dir Insights/reports_prdw \
    --strict
```

`Data/` is the input as distributed — 19 per-table CSVs, no staging step.
`views_prdw/` is build output and is gitignored; `reports_prdw/` is committed.

> **Run it from a local disk, not from the Drive mount.** DuckDB spills temp
> files that cannot be written to Google Drive. The runner already redirects
> `temp_directory`, but the WP-D1 gate build was run against a local mirror of
> `Data/` + `Insights/` and that remains the recommended way to reproduce it.

## The three views

| View | Grain | Rows | What it is for |
|---|---|---|---|
| `view1_activity_lifecycle` | planned activity | 12,704 | the workhorse: `v_activity` plus the 1:1 folds (assets, fund splits, training, community service). 70 columns. |
| `view2_geo_month_cube` | GP × calendar month | 1,440 | the cash cube — 20 GPs × 72 months, full cross join, zero-filled. **All temporal mining runs here.** |
| `view3_gp_performance` | GP × fiscal year | 120 | the institution view — 20 GPs × 6 FYs from the `gram_panchayat` master, LEFT JOINs only. |

Both grids are **full cross joins on purpose**. A GP with no payments in a month
and a GP with no approvals in a year are findings; if their rows were absent they
would read as "no data" and never be mined. Chikilli is the proof: 640 planned
activities, **zero** administrative approvals, and it keeps all six view3 rows.

## The contract with Ask

Every derivation in `derived_columns.sql` is re-expressed **verbatim** from
`Data/create_views.sql`, the same definitions the Ask chatbot queries: the
dim_code decodes with their `CAST(... AS VARCHAR)` and double-cast forms, the
`TRIM`/`chr(9)` status cleaning, `authority_clean`, the `tied_untied` mapping,
the `v_exp` rollup, the `ARG_MAX` scheme rollup. A number that differs between an
Ask answer and a Discover finding is a bug in this pack, not a modelling choice.

**There is exactly one deliberate deviation.** `v_activity.days_since_sanction`
is not re-expressed: it is `DATE_DIFF('day', sanction_day, CURRENT_DATE)`, so its
value depends on when the build runs. Mapping doc §3 excludes it everywhere.

This is **measured, not asserted**. `check_ask_parity.py` runs
`Data/create_views.sql` unmodified over the same CSVs and diffs the resulting
`v_activity` against `view1_activity_lifecycle.parquet`: 41 columns — every
decode, both authority and scheme derivations, all nine flags, the whole
expenditure rollup — are **identical on all 12,704 activities**.

Everything else that a `v_*` view carries and this pack does not is a
**projection** decision from §7, not a change of meaning — free-text names and
descriptions, document numbers, raw authority strings, raw decode codes,
`v_exp.scheme_name` (82% null). They are consumed in `derived_columns.sql` and
never reach a Parquet file. No output column anywhere carries a personal
identifier or free text.

## Money bases

Four bases, never mixed silently (§3). Unqualified "expenditure" means **SPENT**.

```
PLANNED    total_cost / fund_amount_total          ₹773,088,536
SANCTIONED fund_sanctioned_total                   ₹288,438,745   (2,101 activities)
SPENT      total_expenditure                       ₹253,475,090.46 == linked vouchers, exactly
CASHBOOK   voucher.amount                          ₹685,750,811.29 paid / ₹664,791,435.89 received
```

`overspend_vs_plan` and `overspend_vs_sanction` are the single sanctioned
cross-basis mix. Both are signed differences, which roll up honestly where a
ratio cannot. They differ deliberately in how they treat absence:

- `overspend_vs_plan` **coalesces** `total_cost` to 0. Null there means costless,
  i.e. planned at zero, so an activity that spends against no planned cost must
  surface as overspend. (On this drop costless activities carry ₹0 of
  expenditure, so the coalesce changes no number — it pins statewide behaviour.)
- `overspend_vs_sanction` is **null** where no approval exists. Absence of a
  sanction record is not a sanction of zero (§3). Defined on 2,101 rows only.

**No rate is materialised.** Every rate ships as numerator + denominator, so
block and district roll-ups re-derive it instead of averaging averages.

## Sample → statewide

Sample-scale numbers live in exactly two places: `sources.yaml` `expected_rows`
and `validation.yaml` `post_view`. No view SQL contains a scale literal, a date
literal or a wall-clock reference. The two spines derive themselves:

- `stg_month_calendar` runs from `DATE_TRUNC('month', MIN(voucher.date))` to the
  month of `MAX(voucher.date)` — 2020-04 .. 2026-03, 72 months here.
- `stg_fiscal_year_domain` is the union of the fiscal years observed in
  `planned_activity`, `plan` and `voucher` — six here. `activity_voucher` is
  deliberately outside that union: it is the only table carrying `2026-2027`, on
  488 orphan rows with no voucher (§8.1). Excluding the *source* rather than
  filtering a literal keeps the exclusion true when statewide data arrives.

Sparse candidate dimensions (§9.7) — planned fund scheme/component, training
category/organiser, community-service code — are **carried in view1** even though
the sample-phase configs will not mine them, so that switching to statewide is a
`VIEW*_CONFIG` edit and not a pack change (§6).

## Constraints deliberately NOT declared

`--strict` fails the build on any declared check that fails, so a pack that
declares a known-violated constraint is permanently red and teaches everyone to
ignore it. The rule here is **declare only constraints that actually hold**;
every known violation is measured and reported instead. The full list with counts
is in `validation.yaml`'s header and in WPD1_REPORT §3. In brief:

| Not declared | Measured violation |
|---|---|
| FK `activity_expenditure.activity_code → planned_activity` | 20 orphan rows / 20 codes; ₹0.00 of `total_expenditure`, ₹3,092,854.00 of `approved_cost_action_plan` |
| FK `activity_voucher.voucher_pk → voucher.voucher_pk` (raw) | 488 nulls **and** 5,488 float-text values that match zero rows as VARCHAR |
| PK `admin_approval_scheme.activity_code` | 6 duplicates — the multi-scheme approvals `ARG_MAX` collapses (`row_id` is declared instead) |
| PK `dim_code.code` | real key is `(variable, code)`; the runner's CHECK 2 takes one column |
| CATEGORICAL `status_label`, `theme`, `voucher.type`, district names | observed domains, not closed ones — asserting them would fail statewide for arriving with more values |

The `voucher_pk` mismatch is **new in WP-D1** and not in mapping doc §8:
`activity_voucher` stores the key as float text (`'186.0'`), `voucher` as integer
text (`'1'`). `stg_activity_voucher.voucher_pk_norm` applies `v_asset`'s own
double-cast idiom and recovers all 5,488 links, and the FK **is** declared on
that normalised form so the recovery is pinned by a check. Nothing in the data is
repaired and no measure depends on it.

## Known defects carried through, never fixed

**`activity_expenditure.sc` and `.st` are swapped at source** (found in WP-D1,
not in §8). All 21 activities carrying an SC or ST value are crosswise equal
against `admin_approval_scheme`, and `planned_activity.activity_for` (112 = sc,
113 = st) plus `activity_fund`'s planned splits both side with the sanctioned
columns. `sc_amount` / `st_amount` in view1 therefore carry the inversion —
faithfully, because `v_exp` does too, so Ask and Discover still agree. 21
activities, ₹3,666,802. See WPD1_REPORT §5.5; not fixed, and not fixable here.

Logged, exposed, and left alone (mapping doc §8, all re-measured in WP-D1):
the `'Buildings'` status mis-decode (13 activities) and the tab-prefixed
`WORK COMPLETED` (17); only 17 activities are complete sample-wide, so completion
measures are known-degenerate; 233 of 717 `dim_code` rows have no description, so
`Code N` / `Unknown` / `Uncategorised` labels reach findings — including **all
eight** `output_type` codes and **all three** `community_service_code` codes;
`'Theme 5 - Clean and Green Village '` keeps its trailing space; `plan_code_status`
is always null; two activities lose their multi-scheme funding split to the 1:1
fund fold; one sanction is dated in the future.

## Reading notes the glossary must carry (WP-D2)

1. **FY 2023-24 count caveat.** Activity rows jump 609 → 4,607 *entirely* because
   costless activities begin being recorded. Any finding whose subspace involves
   `fiscal_year` with a **count** measure across that boundary needs the §5
   caveat. Money-measure findings do not.
2. **Approval coverage is 17%, and that is a data property.** Absence of an
   approval record is not evidence the activity was unapproved.
3. **A zero in view3's `overspend_vs_sanction` means "nothing sanctioned in this
   cell"**, not "spent exactly what was sanctioned". Read it against
   `n_admin_approvals`, which is 0 in the same rows.
4. **view3's `n_tech_approvals` totals 2,095, not the 2,134 rows in
   `technical_approval`.** That is `v_approval`'s shape: the technical approval
   is joined onto the *administrative* approval, so 39 technical approvals on
   activities with no admin approval are not counted. Ask reports the same 2,095.
   Changing it would split Ask and Discover, so it is flagged for the operator
   rather than altered here.
5. **view2 counts 2,040 of the 2,101 sanctions.** Its time axis is the cashbook's,
   and 61 approvals are dated outside it (14 before 2020-04, 47 from 2026-04).
   view3 counts approvals by fiscal year and reconciles to the full 2,101.

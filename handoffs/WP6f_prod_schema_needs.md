# WP-6f — What the remaining refusals need from the production schema

**For:** the operator, checking the production schema; and whoever writes the
package that gives these questions SQL.

**Status:** these 15 entries are still refusals in
`Ask/query_router/unanswerable_catalog.py`, unchanged by WP-6f (operator ruling
2026-09-29: "let's leave it as is with the refusal"). This file changes no
behaviour. It lists, for each one, what the sample schema lacks, so the
production schema can be checked against it.

The brief counted 14. BEN-010 is the fifteenth: the brief moved it only if
`activity_nsap.category` holds the pension scheme, and nothing in the sample
decodes that column (`dim_code` has no `category` entry), so it stayed.

## How to use this

For each row, check whether the production schema has the column(s) in the
third column. Where it does, the question can become a template the way M7
(`Ask/tools/migrations/m7_refusals_to_templates.py`) did for the other fifteen:
same id, the question becomes the template's question, SQL against the named
columns, executed on the data before it is written.

## The 15

| id | question (short) | what it needs that the sample schema does not have |
|---|---|---|
| **SCH-004** | fund allocated under a scheme at ZP, block and GP tiers in a district | Rows for the **zilla parishad and block tiers**. `gram_panchayat` holds GP rows only, and every plan, activity and voucher belongs to a GP. Needs a tier column on plans or activities (or ZP / block plan tables) with scheme-wise allocations. |
| **PHY-002** | stage-wise completion dates for an asset | A **stage** per asset and the **date each stage was completed**. `physical_progress` holds geotagged photo uploads (coordinates, file id), with no stage name and no stage date. |
| **PHY-005** | assets in a block that have not advanced a stage in N days | The same **stage and stage-date** history as PHY-002, so the time since the last stage change can be measured. |
| **SBM-SWM-033** | how many (waste collection) vehicles have been repaired in a year | A **repair flag or repair event** on an activity or asset. `work_type = Maintenance` combined with a vehicle keyword returns no rows in any year. |
| **ALR-006** | suspended activities with payment vouchers dated after suspension | A **suspended status** and a **suspension date** per activity. The nearest status is WORK ABANDONED, which carries no date. |
| **ALR-007** | activities ongoing longer than their planned duration | A **planned duration**, or a **planned start and end date**, per activity. `planned_activity` has neither. |
| **ALR-010** | GPs with a resource-envelope allocation but no uploaded plan | A **resource envelope (allocation) per GP per year**. No allocation table exists. |
| **DSS-004** | GPs that could reach the next PAI grade with the smallest improvement | **Panchayat Advancement Index scores and grades** per GP (and per theme). Not present anywhere. |
| **BEN-002** | village-wise count of beneficiaries in a GP under a scheme | A **village** on each beneficiary record. `activity_nsap` has category, age band, gender and a count, and no village. |
| **BEN-004** | cash versus kind split of benefits in a GP | A **benefit form (cash / kind)** on each beneficiary record. |
| **BEN-005** | total cash benefit distributed under a scheme in a GP | A **cash amount** per beneficiary record. `activity_nsap` holds a head count only. |
| **BEN-006** | beneficiaries in a GP per stated purpose | A **purpose** on each beneficiary record. |
| **BEN-009** | list of a scheme's beneficiaries in a GP with village and benefit | **Beneficiary names (or ids), village and benefit details** per beneficiary. `activity_nsap` holds aggregated counts, not people. |
| **BEN-010** | beneficiaries under each pension scheme in a block | Either a **decode for `activity_nsap.category`** showing it holds the pension scheme (then the SQL is BEN-007's with `category` as the grouping), or a **welfare scheme code** on each record (`dim_welfare_scheme` already lists the NSAP pension schemes, codes 102–105, but no populated column refers to it). |
| **DQY-005** | beneficiary records in a GP missing the village field | A **village field** on beneficiary records (as BEN-002). |

## What M7 found along the way

- Four "100% NULL" reasons were wrong. `activity_asset.asset_unit_count`,
  `asset_unit_cost`, `asset_loc_code` and `asset_loc_unit_count` are filled for
  about a third of the rows in the sample (unit cost on 3,841 of 12,704). AST-004,
  AST-005, AST-010 and AST-011 answer with real figures today.
  `asset_loc_unit_code`, `asset_loc_unit_type` and `asset_loc_unit_cost_total` are
  genuinely empty.
- `activity_delegation` has 12,704 rows and every delegation column is empty, so
  PLU-005 answers 0 on the sample. `delegated_unit_level` and
  `delegated_unit_type` are shown as codes because nothing decodes them. The
  production schema should say what the codes mean.
- `activity_nsap` has 0 rows. The six beneficiary templates M7 wrote (BEN-001,
  003, 007, 008, 011, 012) join it to the activity's GP, block and **funding
  scheme** (`v_activity.scheme_name`) through `activity_code`. If production
  records the welfare scheme on the NSAP row itself, "under a scheme" should
  read that column instead. Check this before the pilot relies on the scheme
  filter.

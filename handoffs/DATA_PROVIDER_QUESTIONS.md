# Questions for the data provider (PR&DW / government)

Things only the people who produce the data can answer. Everything here was
**observed and measured in this repo, logged, and deliberately not fixed** — the
standing discipline is that a wrong-looking number gets reported, never repaired,
so each item below is a question, not a change request.

Running list: append, don't replace. Each entry states what we measured, what is
genuinely uncertain, the question to put, and what stays blocked until it is
answered. Evidence is a pointer, so nobody has to take this file's word for it.

| | |
|---|---|
| Opened | 2026-08-14 (WP-D1) |
| Scope of evidence | the 20-GP sample drop, `Data/` (19 CSVs) |
| Status key | **OPEN** · **ASKED** *(date)* · **ANSWERED** *(date + ruling)* |

---

## Q1 — Are `activity_expenditure.sc` and `.st` mislabelled? · **OPEN**

**Priority: highest.** This is the one item that can make a report state an
equity conclusion that is confidently backwards.

**Measured.** Twenty-one activities carry a value in an SC or ST column.
On every one of them, `activity_expenditure`'s SC/ST labels are the **opposite**
of what three other sources say — same activity, same rupee amount, flipped
label. 21 of 21 crosswise; **zero** straight.

| Source | Orientation |
|---|---|
| `admin_approval_scheme.fund_sanctioned_sc` / `_st` | SC = ₹440,000 (2 activities), ST = ₹3,226,802 (19) |
| `planned_activity.activity_for` (112 = sc, 113 = st) | the 2 are coded SC, the 19 are coded ST — agrees |
| `activity_fund.fund_tied_sc/_st`, `fund_untied_sc/_st` | agrees |
| `activity_expenditure.sc` / `.st` | **SC = ₹3,226,802 (19), ST = ₹440,000 (2) — disagrees** |

Cleanest single case: activity `48344875` is `activity_for = 112` (SC), with
`fund_tied_sc = 350,000` and `fund_sanctioned_sc = 350,000` — and
`activity_expenditure.st = 350,000`.

**Ruled out on our side.** Not introduced by any code here. The raw CSV header
lines match their column positions, so it is not a shifted-column ingestion bug;
the Discover pack casts the columns under their own names without reordering,
and Ask's `v_exp` does `SUM(sc) AS sc_amount, SUM(st) AS st_amount`. Both
systems pass the source through faithfully.

**The question.** Are these two columns transposed somewhere in the extract that
produces `activity_expenditure` — or is this a genuine reallocation, where money
sanctioned under one social category was spent under the other?

We think mislabelling: a real reallocation would not produce exact per-activity
value equality on 21 of 21 with none straight, and would not put the *planned*
funding split on the sanctioned side as well. But that is inference, and the
provider can settle it directly.

**Blocked until answered.** Any SC-vs-ST statement from either system. Today the
amounts are small (₹3,666,802 across 21 activities of ₹288M sanctioned) so no
current conclusion turns on it — the risk is statewide, where these columns stop
being trivial and an inverted equity finding would look entirely plausible.

**Also affects Ask, not just Discover.** `v_activity.sc_amount` / `st_amount`
carry the same inversion, so any Ask answer distinguishing SC from ST
expenditure is currently backwards. Not a defect either workstream introduced.

**Evidence.** `handoffs/WPD1_REPORT.md` §5.5; reproducible via
`Insights/reports_prdw/scst_diagnosis.py` (output saved alongside it as
`scst_diagnosis.txt`).

---

## Everything else worth putting in the same conversation

Swept from the WP-D1 findings for things that are **questions for them rather
than decisions for us**. Q1 is the one that was explicitly flagged for this list;
the rest are here because they belong in the same meeting. Trim freely.

### Q2 — Can we have the missing code descriptions? · **OPEN**

**233 of 717 `dim_code` rows carry no description**, so `Code 101`, `Unknown` and
`Uncategorised` reach findings as if they were categories. Three specific gaps:

- **all eight `output_type` codes** are description-less, so a dimension the
  signed view spec asks for (`output_type_label`) is currently eight opaque
  numbers across all 12,704 activities;
- **all three `community_service_code` values**;
- `training_category_code` and `training_organiser_code` have **no `dim_code`
  rows at all** — the decode table for them does not exist, rather than being
  sparse.

**Question.** Can the master code lists behind these fields be supplied?
**Blocked:** these dimensions can be mined but not *read* — a finding about
"Code 109" is not reportable to an officer.

### Q3 — What are the 488 FY 2026-2027 voucher links? · **OPEN**

488 `activity_voucher` rows carry `fiscal_year = '2026-2027'`, a **NULL
`voucher_pk`**, dates from 2026-04-09 to 2026-08-03, and **₹13,513,516.05** of
`voucher_cost` — but the `voucher` cashbook ends 2026-03-31, so there is no
voucher for them to point at.

**Question.** Is this a later cashbook extract that simply was not included in
this drop, or are the rows themselves wrong?
**Currently:** excluded from the monthly cube structurally (its calendar ends
where the cashbook ends). If a fuller cashbook exists, we want it.

### Q4 — Twenty expenditure rows for activities that do not exist · **OPEN**

`activity_expenditure` holds **12,724 distinct activity codes against 12,704
activities**: 20 codes have no `planned_activity` parent. They carry ₹0.00 of
`total_expenditure` but ₹3,092,854.00 of `approved_cost_action_plan`.

**Question.** Were those activities deleted or superseded after their expenditure
rows were written, or are the codes wrong?

### Q5 — Is completion status actually maintained? · **OPEN**

**17 of 12,704 activities (0.13%) are marked WORK COMPLETED**, against 2,110
ongoing and 10,108 "Activity Approved". Six years of data.

**Question.** Is the completion status genuinely updated in the field system, or
does the field go stale after entry? This is not a data-cleaning question — it
decides whether "completion rate" is a metric this programme can report at all,
in either system.

### Q6 — What is `activity_status` code 173? · **OPEN**

Code 173 decodes to **`'Buildings'`** — a category name sitting in a status
field — on 13 activities. Known and logged since the dictionary work.
Relatedly, code 178 (`WORK COMPLETED`) is stored with a leading tab character.

**Question.** What status did 173 mean? Can the tab be cleaned at source?

### Q7 — A fuller focus-area → LSDG theme mapping? · **OPEN**

**986 activities (7.8%)** fall to `'Unmapped theme'` because their focus area has
no row in `dim_lsdg_theme` (17 mappings for 30 focus areas).
Minor and cosmetic: `'Theme 5 - Clean and Green Village '` carries a **trailing
space** in the source, preserved deliberately.

**Question.** Is there an authoritative full mapping, and should the stray space
be cleaned upstream?

### Q8 — Thirty-nine technical approvals with no administrative approval · **OPEN**

39 activities have a technical approval (₹4,200,502) but no `admin_approval`
record. Both serving layers hang the technical approval off the administrative
one, so these are invisible in both.

**Question.** Is "technically approved, not administratively approved" a real
workflow state, or are those 39 administrative records missing?

### Q9 — One sanction dated in the future; 47 past the cashbook · **OPEN**

Max `adm_approval_sanction_date` is **2026-08-19**, five days after the audit
date. 47 sanctions fall after 2026-03; 14 fall before the cashbook opens
(twelve of them on 2019-10-02).

**Question.** Data entry, or genuine forward-dated sanction orders?

### Q10 — Two identifier-hygiene items · **OPEN**

- **`voucher_pk` format mismatch.** `activity_voucher` stores it as float text
  (`'186.0'`); `voucher` stores it as integer text (`'1'`). Compared as text
  they match on **zero** of 5,488 rows. We normalise numerically and recover all
  5,488, so nothing is wrong in our outputs — but anyone else joining these two
  tables will silently get nothing.
- **Two activities carry `fund_overflow_json`**, multi-scheme funding squeezed
  into one row. The 1:1 fund model loses that split for exactly those two.

**Question.** Can the key be emitted in one consistent form, and is there a
normalised multi-scheme funding table?

### Q11 — Will `activity_nsap` and `activity_delegation` ever carry data? · **OPEN**

`activity_nsap` has **zero rows**; `activity_delegation` has 12,704 rows and no
populated analytical column. `dim_welfare_scheme` lists 12 welfare schemes that
no populated column references.

**Question.** Are these modules unused in this state, not yet extracted, or
retired? **This is the blocker on equity analysis** — with no beneficiary-grain
data anywhere in the drop, the equity/journey view was ruled out for v1, and
NSAP is the table that would change that.

---

## Suggested `PROJECT_PLAN.md` §5 entry

`PROJECT_PLAN.md` is PM-owned and was not edited. If §5 (Blockers & asks) should
carry a pointer, this is the line:

> **Data-provider questions (opened 2026-08-14, WP-D1).** Eleven items in
> `handoffs/DATA_PROVIDER_QUESTIONS.md`. Q1 (`activity_expenditure.sc`/`.st`
> transposed at source — affects Ask and Discover alike) blocks any SC/ST
> statement; Q2 (missing code descriptions) blocks reporting on `output_type`;
> Q5 (is completion status maintained?) decides whether completion is a reportable
> metric at all; Q11 (NSAP empty) is the standing blocker on equity analysis.

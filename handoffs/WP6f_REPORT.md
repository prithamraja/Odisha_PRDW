# WP-6f — Three reranker fixes, and no refusals where the data exists: REPORT

> ## Where everything is
>
> ```
> Ask/tools/derive_catalog.py                  T1–T3 notes in _DISAMBIGUATION; T3 PLAIN_COUNT_TOTAL
>                                              (declared by id, written onto PLN-024's $group_by, refused elsewhere);
>                                              T4 notes on PLN-007/022/023/041/042
> Ask/query_router/breakdown.py                T3 plain_count_total(), declares_plain_count_total()
> Ask/query_router/router.py                   T3 binds group_by='total' after the comparison step;
>                                              T4 "By what date should the GPDP have been approved?"
> Ask/tools/migrations/m7_refusals_to_templates.py   T4 migration M7 (apply / --check)
> Ask/query_router/template_catalog.py         358 templates (343 + 15)
> Ask/query_router/unanswerable_catalog.py     15 refusals, byte-identical to e865c52
> Ask/tests/data/workbook_test_report.json     +15 lines, executed against the sample
> Ask/tests/test_wp6f_notes_and_refusals.py    27 tests (T1–T4)
> Ask/grade_eval1.py                           T1 `accept`, T3 `one_figure`, T5 grade_wp6f (sixth group)
> eval/gold/*.jsonl, coverage.json             the 8 moved gold rows; G1613 carried into the source
> handoffs/WP6c_pilot_questions.json           accept / one_figure on 1005–1009, 1039–1044; rows 1045–1059
> handoffs/WP6f_prod_schema_needs.md           what the 15 remaining refusals need from production
> handoffs/WP6f_stage1.csv/.jsonl              T5.2 — the 35 targeted rows
> handoffs/WP6f_eval1_replay.csv/.jsonl        T5.3 — Eval_1, graded, diffed against WP-6e
> handoffs/WP6f_pilot_replay.csv/.jsonl        T5.3 — the 59 pilot rows (44 + 15 new)
> handoffs/WP6f_gold_replay_run1.csv/.jsonl    T5.3 — gold, WP-6e's verdict (re-graded on the new gold) beside each row
> handoffs/WP6f_rerank_calls.jsonl             every reranker call in the four runs
> ```
>
> **Committed, not pushed**, one commit per task: `15e29d8` T1 (with the brief),
> `67b6ab8` T2, `6c8eb18` T3, `39f0b5d` T4, and T5's commit carrying this report
> and the runs. The "found by" switch stays at 4. Left for the operator as
> before: the PM's `handoffs/PROJECT_PLAN.md` edit, the untracked
> `handoffs/WP6b_eval1_replay_notes_off.csv`, and `Ask/bench/`.
>
> Mirror: `C:\dev\odisha-wp6f`, a plain copy of `Ask/` at `e865c52` plus WP-6e's
> search index, re-embedded once after M7.

---

## 0. For the PM — what this package found

1. **All four items landed, and every targeted row answers.** In the full runs,
   1005 / 1007 / 1009 answer on the sanctioned measure (BUD-003, BUD-005, BUD-003),
   all six plain counts answer PLN-024 as one figure, Eval_1 42 and 44 answer
   EXP-009 (49 answered its twin EXP-011 in stage 1 and asked, with EXP-009 on
   the chips, in the full run), and 14 of the 15 former refusals answer with
   their own template.
2. **The numbers moved the right way everywhere.**

   | run | WP-6e | WP-6f |
   |---|---|---|
   | Eval_1 (302 gradable): correct / asked, right chip / asked, wrong chips / wrong | 286 / 14 / 0 / 2 | **298 / 3 / 0 / 1** |
   | gold (275): behaving correctly / confidently wrong | 249 (90.5%) / 6 as graded then; 245 (89.1%) / 6 on the new gold | **250 (90.9%) / 6** |
   | pilot, the 44 old rows: correct / asked / wrong | 40 / 3 / 1 as graded then; **37 / 3 / 4** under the narrowed grading | **43 / 1 / 0** (1002 asks: the known search gap, out of scope) |
   | pilot, the 15 new rows (one per former refusal) | — | **14 correct / 1 asked** |

3. **No moved entry was ever served as a refusal.** Every refusal served in
   any run (10, all in gold) was a gold row that expects exactly that refusal.
   Eval_1 and the pilot served none.
4. **The 15th refusal.** The brief moved BEN-010 ("each pension scheme") only if
   `activity_nsap.category` holds the pension scheme. `dim_code` has no decode
   for that column, so by the brief's rule it stays a refusal: **15 refusals
   remain, not 14**, and 358 templates, not 359.
5. **Four refusal reasons were wrong.** The asset columns M7 reads are not
   "100% NULL": unit cost is filled on 3,841 of 12,704 rows, unit count and
   location on 4,286. AST-004 / 005 / 010 / 011 answer with real figures today.
6. **Two things to know, neither caused here** (§7): BEN-008 asked instead of
   answering, twice; and the year reader turns "from 2022-23 to 2024-25" into
   the two end years, dropping the middle one.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | M7 applied and idempotent; `UNANSWERABLE_CATALOG` holds exactly the group-c entries, unchanged; new templates execute with counts in the oracle; derive `--check` green; `validate_catalog.py` 343 + N / 0 | **PASS**, with 15 (the brief's own "or 343 + 15" branch): `m7 --check` applied, a second apply does nothing; the 15 refusals equal `e865c52`'s (test `test_the_kept_refusals_are_unchanged`, run in the repo); **358 templates · 26 legitimately return no rows · 0 problems** |
| 2 | Full suite and `prdw_gates.py` green, gates 6 and 8 over the remaining refusals; refusal recall no lower | **PASS**: **GATE GREEN 9/9, 788 tests** (28 skipped without a live key), gate 5 against the live model list. Refusal recall on the 11 gold rows that are still refusals: English 10/10 before and after, same ranks (§5.4) |
| 3 | T3 changes the breakdown on no row outside the expected set | **PASS**: 3 of 633 rows, all expected (§4) |
| 4 | 1005 / 1009 on BUD-003 or SAN-013 and 1007 on BUD-005 in at least one run; 42 / 44 / 49 on EXP-009 or asked with EXP-009 first; plain counts on PLN-024 as one figure | **PASS**: 1005 / 1007 / 1009 and the six plain counts in both stage 1 and the full run; 42 and 44 on EXP-009 in both; 49 on EXP-011 (EXP-009's family) in stage 1, asked in the full run with EXP-009 as the second chip (§2, §3, §4) |
| 5 | None of the moved entries ever served as a refusal; every refusal served listed; any served to an answerable question flagged | **PASS**: 0 moved entries served as refusals; 10 refusals served, all correct (§5.5) |
| 6 | Eval_1, gold and pilot diffed against WP-6e; gold confidently wrong beside WP-6e's 6 | **PASS**: 6 against 6 (§6) |
| 7 | Brief, `WP6f_prod_schema_needs.md` and report committed, one commit per task, not pushed | **PASS** |

---

## 2. T1 — BUD-003 / BUD-005: the sanctioned amount by scheme

**Built.** Notes on BUD-003 (sanctioned amount by scheme), BUD-005 (its share)
and BUD-002 (the cashbook, pointing the other two away), exactly as briefed.

**Grading narrowed.** A pilot row's `expect` may now carry `accept`: 1005 and
1009 accept BUD-003 or SAN-013, 1007 only BUD-005. Re-graded under it:

| run | 1005 | 1007 | 1009 | 44 old pilot rows |
|---|---|---|---|---|
| WP-6d | wrong (BUD-002) | asked | asked | 36 / 5 / 3 |
| WP-6e stage 1 | — | asked | **wrong (BUD-002)**, graded correct at the time | — |
| WP-6e full run | correct | **wrong (BUD-003, the amount not the share)**, graded correct at the time | asked | **39 / 3 / 2** (was 40 / 3 / 1) |
| **WP-6f stage 1** | **BUD-003, per scheme** | **BUD-005, per scheme** | **BUD-003, SFC bound** | — |
| **WP-6f full run** | **correct** | **correct** | **correct** | **43 / 1 / 0** |

The corrected WP-6e baseline, with T3's grading applied too, is **37 / 3 / 4**
(1041 / 1043 answered PLN-024 per theme, which is now wrong; 1044 the PLU-005
refusal). The echo reads, for 1007: "What percentage of the sanctioned budget is
tied and untied in 2024-2025 (5th State Finance Commission (SFC) and 15th Finance
Commission (CFC))? (broken down by scheme)". The question wording still says
"tied and untied" while the table is per scheme; that is the catalogue question,
not changed here.

## 3. T2 — EXP-009: comparing tied spend across focus areas

**Built.** The note sits on EXP-009's family, which EXP-011 shares (identical
SQL, so one family and one note). TRD-008 gained "A question about TIED funds
is EXP-009, even when it says 'sector-wise'." TRD-002 is unchanged. No file
serving "sector" or "Sankalp" changed.

| row | question | WP-6d | WP-6e | WP-6f stage 1 | WP-6f full |
|---|---|---|---|---|---|
| 42 | Compare tied fund spending between water and sanitation for 2024 to 2026 | TRD-002 wrong | asked, EXP-009 first | **EXP-009** | **EXP-009** |
| 44 | What is the sector-wise expenditure of tied funds for water and sanitation … | correct | **TRD-008 wrong** | **EXP-009** | **EXP-009** |
| 49 | Compare tied fund spending … for 2022 to 2023 | TRD-002 wrong | asked | **EXP-011** (same family) | asked; chips: an unmatched wording, then EXP-009 |

Every answer binds both focus areas and gives one row per focus area. Row 49
still wavers between answering and asking, but it no longer goes to TRD-002.

## 4. T3 — a plain count answers as one figure

**Built, scoped to PLN-024.** `derive_catalog.PLAIN_COUNT_TOTAL = {"PLN-024"}`
writes `"plain_count_total": True` onto PLN-024's `$group_by`, and the contract
refuses it on any other template. After the list-comparison step, the router
binds `group_by = 'total'` when (a) the template declares it, (b) the phrase
reader found no breakdown, (c) the question asks for a count / number of / how
many (planned) activities, and (d) no ranking word is present (which, highest,
most, lowest, least, fewest, top, bottom, rank…, largest, smallest, maximum,
minimum). Two named places still get a row each (tested). The reranker note on
PLN-024 names the plain count.

**The offline proof (free)**, over all 633 WP-6e replay questions with their
recorded served template:

| run | row | question | served | breakdown before → after |
|---|---|---|---|---|
| Eval_1 | 151 | Count of all planned activities inside main GPDPs for 2021 to 2022. | PLN-024 | per theme → one total |
| pilot | 1041 | What is the count of planned activities in Bheden in 2024? | PLN-024 | per theme → one total |
| pilot | 1043 | What is the count of planned activities in Barpali in 2024-25? | PLN-024 | per theme → one total |

**Nothing else changes.** Rows 141–149 were already one total: "total",
"overall", "aggregate" and "sum of" are read by the phrase reader. Row 151 is
the one member of that group worded "count of all". For scale: the phrase alone
("count of / how many activities", no ranking word) matches 32 of the 633
questions. Most are served by PLN-049, STS-003 or IMP-002, and that is why the
rule is declared on one template.

**Grading.** 1039–1044 carry `one_figure`: an answer must be PLN-024 with
`group_by = total` and one row. A chip-tap row whose question now answers on
turn 1 (so there is no chip to tap) is graded on turn 1.

**Result: 6 / 6 in stage 1 and 6 / 6 in the full run.** All bind the place at
the right tier (Kalimela, Bheden and Barpali as blocks, Laxmipur as a GP, per
WP-6d's ruling), `group_by = total`, one row. The echo reads "How many
activities are planned under each GPDP theme in all GPs in 2024-2025 (Barpali
block)? (as one total)". "(as one total)" is there as briefed, but the catalogue
question's "under each GPDP theme" still reads oddly beside it (§8).

## 5. T4 — no refusals where the data or definition exists

### 5.1 M7

`python tools/migrations/m7_refusals_to_templates.py` (apply) / `--check`. It
builds the 15 entries, runs `derive_catalog.contract_problems` on them, executes
every statement against the sample, and refuses to write if any old template or
any kept refusal would change, or if the two catalogues would not hold exactly
what it says. Then it writes both files and the oracle. Ids are kept; each
refusal's question becomes the template's `abstract_question` with placeholders;
hand paraphrases carry over unchanged (the derived block is rebuilt). For the
four group-b entries, the refusal's own question is kept as a hand paraphrase,
because their new question names the deadline or the rule.

### 5.2 Every new template

"Filters" means the universal optional slots M1 added: geography, plus plan
type, status, focus area, theme, scheme and tied/untied on `v_activity`, the
first four on `v_asset`.

| id | type | what the SQL does | sample (Test Report params) | rows |
|---|---|---|---|--:|
| PLU-005 | Count | `v_activity` ⋈ `activity_delegation` where `is_delegated = 1`, one row per delegated unit level × type (codes: nothing decodes them), activities and GPs; filters | Attabira, 2025-26 | 0 (renders "0") |
| AST-004 | Lookup | `v_asset` for one `$activity_code`: sub-category, location code, units at the location | 50378563 | 1 |
| AST-005 | Lookup | `v_asset` for one `$activity_code`: unit count, cost per unit | 50378563 | 1 |
| AST-010 | Aggregation | per sub-category: assets with a unit cost, average / min / max cost per unit; optional `$asset_sub_category`; filters | Road CC, Bargarh, 2021-22 | 1 |
| AST-011 | Listing | assets whose unit cost is more than `$threshold` % above the average for their district and sub-category (the average over the whole district; block / GP narrow only the list); required threshold, **derived `above` / `percent`** by WP-6c's rule | Bargarh, 2021-22, 50 % | 9 |
| BEN-001 | Count | `activity_nsap` ⋈ `v_activity` on `activity_code`: SUM(beneficiary_count), activities; one summary row, `$group_by` (M2 GROUPING SETS) | 2024-25 | 1 (zero) |
| BEN-003 | Count | the same, one row per GP (block beside), `$group_by` | Barpali, 2024-25 | 0 (renders "0") |
| BEN-007 | Ranking | the same, per `v_activity.scheme_name`, top `$top_n` (default 10) | Barpali, 2024-25 | 0 |
| BEN-008 | Listing | **absence from the GP roster** (PLN-032 shape): GPs with no NSAP row with a count > 0 | Barpali, 2024-25 | 2 (every GP) |
| BEN-011 | Comparison | the same totals for `$block_name` and `$block_name_2` (TRD-011 shape), `$group_by` | Barpali vs Attabira, 2024-25 | 0 |
| BEN-012 | Trend | the same totals per fiscal year over `$date_range` | 2022-23 to 2024-25 | 0 |
| PLN-022 | Ranking | per block: GPs with a **main** plan, GPs whose main plan was approved after `$deadline`, % late, years counted, years in which more than half its GPs were late; highest % late first, top 10. Each earlier year's deadline is the same date that many years before (`to_years`), anchored on the latest year asked | 2024-25, deadline 30 June 2024 | 10 |
| PLN-023 | Ranking | the same per district | same | 9 |
| PLN-041 | Ranking | every theme × the five most recent fiscal years in the data (2021-22 to 2025-26), planned cost 0 where nothing was planned, RANK() per year; years in the top 3, years counted, period, planned cost; 'Unmapped theme' excluded | — | 6 |
| PLN-042 | Ranking | the same, bottom 3 | — | 6 |

Output column names were chosen so `column_types.json` types them without a new
rule: `cost_per_unit` is a ratio (never summed), the delegation codes are
identifiers, and `years_counted` is a count.

### 5.3 Decisions I made that the brief did not

1. **PLN-022/023 count the MAIN plan only.** The brief says "GPs whose plan
   `approval_date` is after the deadline". Supplementary plans are approved
   mid-year by design (2024-25: April 2024 to June 2026). Counting them would
   make "consistently delayed" measure who files a supplementary plan. So the
   statement fixes `plan_type = 'Main'`, and PLN-022/023 carry no `$plan_type`
   slot.
2. **One deadline for a span.** The officer gives one date for the latest year
   asked; each earlier year uses the same day that many years before. For a
   single year, the date is used as given.
3. **The deadline ask.** The brief said PLN-010 already asks "By what date
   should the GPDP have been approved?"; it asked "For which deadline?". Every
   `$deadline` in the catalogue (PLN-008/009/010, and now PLN-022/023) is
   compared with a plan's approval date, so the router now asks every missing
   deadline in those words. This changes the wording of PLN-008/009/010's ask.
4. **Reranker notes beyond T1–T3.** PLN-022/023 (approval delays against a
   deadline; "behind / delayed on submission" is PLN-007), PLN-041/042 (a rule;
   the series is PLN-038), and PLN-007 (the other side of that line). These are
   there so that "districts delayed on GPDP submission", which WP-6e fixed,
   does not drift to PLN-023. It did not: Eval_1's group "districts behind on
   GPDP submission" is 11 / 11 on PLN-007.
5. **PLN-041/042's question states the rule** ("… (top 3 by planned cost, in how
   many of the last 5 years)?"), so the echo says it, as briefed.
6. **Beneficiary "scheme" is the activity's funding scheme** (`v_activity.scheme_name`),
   as briefed ("joined through `activity_code` to the activity's GP, block and
   scheme"). If production records the welfare scheme on the NSAP row, that is
   the column to use. This is flagged in `WP6f_prod_schema_needs.md`.
7. **G1613 carried into the gold source.** Rebuilding the harness file
   (`build_eval_questions.py --install`) reverted WP-6d's G1613 change, because
   WP-6d had edited `Ask/eval_questions_full.json` and not
   `eval/gold/implementation_progress.jsonl`. The change is now in the source,
   so rebuilds keep it. The rebuilt harness file differs from WP-6e's only on
   the 8 moved rows.
8. **The harness-format check** (`eval/gold/check_harness_format.py`) now counts
   `clarify_as_ratified` as a pass in its synthetic ambiguity test. Its
   synthetic prompt's reason is `missing_parameter`, which is G1039's ratified
   outcome.

### 5.4 The refusal machinery, now over 15

`_refusal_precedence`, `_serve_unanswerable`, the "Why I can't answer" chip and
the reranker's "CANNOT answer" rule are unchanged. Gates 6 and 8 run over what
remains:

* **Gate 6** iterates the catalogue: 15 entries, `result is None` on all.
* **Gate 8** measures the gold rows whose gold is still a refusal: **11**
  (8 of the 19 are now answered questions). Its pinned row was BEN-001, now a
  template, so the pin moved to **BEN-002**. That is the Dropped beneficiary
  refusal still in the catalogue, and it depends on the same scope-free line.

**Refusal recall, before (WP-6e index) and after (WP-6f index), on the 11:**

| register | before | after |
|---|---|---|
| English (asserted) | 10 / 10: SCH-004, PHY-002, PHY-005, ALR-006, ALR-010, ALR-007, DQY-005, DSS-004, BEN-002 at rank 0; SBM-SWM-033 rank 1 | **10 / 10, identical ranks** |
| Odia (deferred) | BEN-010 rank 354 | rank 354 |
| pin | BEN-001 rank 5 | BEN-002 rank 0 |
| crowding | 32.2 / 146 | 32.4 / 145 |

### 5.5 Every refusal served in any run

| run | rows | refusals served | genuinely one of the 15? |
|---|--:|---|---|
| stage 1 | 35 | none | — |
| Eval_1 | 314 | none | — |
| pilot | 59 | none | — |
| gold | 275 | 10: #1233 SBM-SWM-033, #1421 SCH-004, #1621 PHY-002, #1622 PHY-005, #1712 ALR-006, #1713 ALR-010, #1714 ALR-007, #1715 DQY-005, #1956 DSS-004, #1973 BEN-002 | **yes, all 10**: each is the gold row for that refusal |

None of the 15 moved ids was served as a refusal. Pilot 1044 ("count of
planned activities in Attabira"), which the PLU-005 refusal took in WP-6d and
WP-6e, now answers PLN-024 as one figure. Of the 11 gold rows that still expect a
refusal, the one not listed above is #1974 (BEN-010, Odia script), declined
generically, as before.

### 5.6 The 19 known-unanswerable gold rows

| gold row | entry | group | expectation now | WP-6f |
|---|---|---|---|---|
| G1039 (Odia translit.) | PLN-022 | b | template; no deadline in the question, so **asking for it** (`missing_parameter`) is ratified | **PLN-020, wrong**, as in WP-6d and WP-6e (PLN-022 was rank 18 as a refusal; not among the reranker's top candidates) |
| G1040 | PLN-041 | b | template, answered | **hit**, 6 rows |
| G1041 (code-mixed) | PLU-005 | a | template, answered | **hit** (0 delegated) |
| G1857 | AST-010 | a | template, answered | **hit** |
| G1858 | AST-005 | a | template, answered | **hit** (activity 125711758 is not in the sample: no rows) |
| G1859 | AST-004 | a | template, answered | **hit** (same) |
| G1971 | BEN-001 | a | template, answered | **hit** (0) |
| G1972 (code-mixed) | BEN-003 | a | template, answered | asked ("What would you like to know about Bhubaneswar?"), as it asked in WP-6e |
| G1233 | SBM-SWM-033 | c | refusal | refusal ✓ |
| G1421 | SCH-004 | c | refusal | refusal ✓ |
| G1621 | PHY-002 | c | refusal | refusal ✓ |
| G1622 | PHY-005 | c | refusal | refusal ✓ |
| G1712 | ALR-006 | c | refusal | refusal ✓ |
| G1713 | ALR-010 | c | refusal | refusal ✓ |
| G1714 | ALR-007 | c | refusal | refusal ✓ |
| G1715 | DQY-005 | c | refusal | refusal ✓ |
| G1956 | DSS-004 | c | refusal | refusal ✓ |
| G1973 | BEN-002 | c | refusal | refusal ✓ |
| G1974 (Odia) | BEN-010 | c (15th) | refusal | declined generically, as before |

The 8 moved rows lost `unanswerable_ref` and became `case_type: standard`, each
with a note citing the operator's ruling.

### 5.7 Tests rewritten

| test | was | now |
|---|---|---|
| `test_refusal_precedence` (whole module) | its example refusal was BEN-001 (and a PLN-022-shaped case) | the example is **BEN-010**, still a refusal; every assertion kept |
| `test_catalog_execution` — catalogue size | 346 − retired + added | + the 15 moved (358) |
| `test_catalog_execution` — zero-row set | 21 | 26 (PLU-005, BEN-003, BEN-007, BEN-011, BEN-012 added, named) |
| `test_wp6b_eval1_fixes` — Test Report zero rows | 21 | 26 |
| `test_param_binding` — `$top_n` carriers | 91 | 94 (BEN-007, PLN-022, PLN-023) |
| `test_param_binding` — threshold templates | 15 | 16 (AST-011) |
| `test_wp6c_pilot_feedback` — derived threshold meta | 15 entries | + AST-011 (above, percent) |
| `test_wp6e_reranker_examples.RealIndexTests` | — | unchanged; passes once the index is rebuilt for the new catalogue |
| `test_wp6d_ranking_floor` G1613 | — | unchanged; passes once G1613 is in the gold source (§5.3.7) |
| `test_served_refusal` | "all 30" | docstring only |

## 6. Full runs, diffed against WP-6e

### 6.1 Eval_1 (`WP6f_eval1_replay.csv`, 10 parallel parts, 0 errors)

| outcome | WP-6e | WP-6f |
|---|--:|--:|
| correct | 286 | **298** |
| asked, right template offered | 14 | **3** |
| asked, right template NOT offered | 0 | 0 |
| incorrect | 2 | **1** |
| defective row | 12 | 12 |

**Every row that moved (16):**

| row | WP-6e → WP-6f | served | reading |
|---|---|---|---|
| 42, 44 | asked / wrong → correct | EXP-009 | T2 |
| 141, 144, 145, 148, 149 | asked → correct | PLN-024 as one total | T3's note; WP-6e §3.2's "per-theme" asks |
| 7, 174 | asked → correct | BUD-006 | not targeted; the same WP-6e §3.2 shape |
| 12, 186, 188, 193 | asked → correct | PLU-008 | not targeted; same |
| 281 | wrong → correct | (asked about "sector") | the "sector" group, ruled to ask |
| 5 | correct → asked | chips BUD-006 first | run-to-run |
| **289** | correct → **wrong** | IMP-005 | the "sector" group again: "…sector…" slipped past the sector question and was answered. The same known slip as 281 in WP-6e (WP-6c brief §0); out of scope |

By group: "total activities in main GPDPs" 7 → **12 / 12**, "GPs with zero-cost
activities" 14 → **18 / 18**, "tied spend water vs sanitation" 9 → **11 / 12**
(49 asked, as in WP-6e),
"districts behind on GPDP submission" **11 / 11** (held). Nine asks returned to
answers in rows T1–T3 never targeted (7, 12, 174, 186–193). WP-6e measured
about a quarter of Eval_1 rows flipping between answering and asking from run
to run, so part of that is noise.

### 6.2 Gold (`WP6f_gold_replay_run1.csv`, 8 parallel parts, cut only where a row starts a fresh session, 0 errors)

| | WP-6 runs 1 / 2 / 3 | WP-6e as graded then | WP-6e on the new gold | **WP-6f** |
|---|---|---|---|---|
| behaving correctly | 90.5 / 90.9 / 89.8% | 249 (90.5%) | 245 (89.1%) | **250 (90.9%)** |
| confidently wrong | 5 / 5 / 6 | 6 | 6 | **6** |

"On the new gold" re-grades WP-6e's own records against this package's gold
file, so the 8 moved rows count the same way in both columns.

**Confidently wrong, row by row:**

| WP-6e (new gold) | WP-6f |
|---|---|
| #1016 wrong values (PLN-012) | #1016 wrong values (PLN-012) |
| #1039 PLN-020 for PLN-022 | #1039 PLN-020 for PLN-022 |
| #1214 SBM-SI-013 for SI-014 (Odia "sarichi") | — now a **hit** |
| #1415 BUD-005 for FND-001 | #1415 BUD-005 for FND-001 |
| #1616 STS-003 for IMP-011 (Odia) | — now asks |
| #1852 AST-006 for AST-002 (gold not among the 30) | #1852 AST-006 for AST-002 |
| — | **#1020** PLN-014 for PLN-020 (Odia script: "which block has the most GPDP approvals pending") |
| — | **#1624** STS-013 with wrong values ("and for 2023-24?", a follow-up; extractor variation, as WP-6d §8.3 noted) |

**Every row that moved (12):** the 6 moved gold rows answered (G1040, G1041,
G1857, G1858, G1859, G1971: WP-6e served refusals that are no longer the
expectation), #1214 hit, #1616 wrong → asked, #1020 asked → wrong, #1521
asked with the gold chip → asked without it, #1605 hit → asked with the gold chip, #1624 hit →
wrong values. None of the six non-moved changes involves a template or note
this package touched.

### 6.3 Pilot (`WP6f_pilot_replay.csv`, 59 rows)

**The 44 old rows: 43 correct, 1 asked** (WP-6e re-graded: 37 / 3 / 4). The
rows that moved are 1007 and 1009 (T1) and 1040, 1041, 1043 and 1044 (T3). The
one ask is 1002 ("Own Funds vs SFC in Khordha"), which asked in WP-6e too:
BUD-003 / BUD-002 are not among its 30 candidates, a search gap the brief keeps
out of scope.

**The 15 new rows (1045–1059, sixth standing group, one per former refusal,
graded by `grade_wp6f`):**

| row | template | stage 1 | full run | note |
|---|---|---|---|---|
| 1045 | PLU-005 | ✓ | ✓ | "0" |
| 1046 | AST-004 | ✓ | ✓ | 1 row |
| 1047 | AST-005 | ✓ | ✓ | 1 row |
| 1048 | AST-010 | ✓ | ✓ | Road CC, Bargarh: avg ₹3.07 lakh over 4 assets |
| 1049 | AST-011 | ✓ | ✓ | threshold 50 read, `above` |
| 1050 | BEN-001 | ✓ | ✓ | "0" |
| 1051 | BEN-003 | ✓ | ✓ | SFC bound |
| 1052 | BEN-007 | ✓ | ✓ | no rows (empty table) |
| **1053** | **BEN-008** | asked | asked | chips BEN-001 / BEN-003 / SCH-001; BEN-008 not among them (§7) |
| 1054 | BEN-011 | ✓ | ✓ | both blocks bound |
| 1055 | BEN-012 | ✓ | ✓ | years read as 2022-23 and 2024-25 only (§7) |
| 1056 | PLN-022 | ✓ | ✓ | deadline 2024-06-30 read; 3 Bargarh blocks |
| 1057 | PLN-023 | ✓ | ✓ | deadline 2025-06-30; years 2023-24 and 2025-26 only (§7) |
| 1058 | PLN-041 | ✓ | ✓ | 6 themes |
| 1059 | PLN-042 | ✓ | ✓ | 6 themes |

## 7. Found, not fixed

1. **BEN-008 ("Which GPs in Barpali have no recorded beneficiaries under …")
   asked in both runs**, and its chips did not offer BEN-008. The reranker
   declined in favour of the counting questions. One more phrasing ("GPs with no
   beneficiaries") or a note would likely settle it. That is outside this brief.
2. **"from 2022-23 to 2024-25" reads as the two end years.** 1055 bound
   `['2022-2023', '2024-2025']` and 1057 `['2023-2024', '2025-2026']`, dropping
   the middle year. PLN-023 then counted 2 years, not 3. WP-6b fixed "2023-2025"
   and WP-6 "2024 to 2026". The hyphenated-fiscal-year form "X-YY to Z-WW" is
   not read as a span. This affects every template with a year list, not just
   these.
3. **G1039** (Odia transliterated, "consistently delayed approvals") is PLN-020
   in all three packages. Now that PLN-022 is a template, an Odia phrasing on
   PLN-022 would be the fix. Odia is deferred.
4. **The plain-count echo** reads "…under each GPDP theme in all GPs … (as one
   total)". The words are right and the combination is clumsy.
5. **1007's echo** still says "tied and untied" over a per-scheme table (the
   catalogue question, unchanged).

## 8. Spend

All paid runs went through `confirm_spend`. Gold is metered (`llm_usage`); the
custom runs are counted from the records, as WP-6b..6e did.

| | calls |
|---|--:|
| offline: T3 proof, re-grading, M7 execution | 0 |
| catalogue index re-embedded after M7 (the first attempt failed on an empty account before any call was charged; the operator topped up) | 9 |
| gate 5 live model list | 1 |
| stage 1, 35 rows | ~110 (35 reranks) |
| Eval_1, 314 rows | ~950 (306 reranks) |
| pilot, 59 rows | ~190 (59 reranks) |
| gold, 275 rows in 8 parts | **784 (metered)**, 2.41 M prompt tokens |
| **total** | **~2,050** |

The brief estimated about 2,050. Reranker prompts averaged 7,355 tokens over
651 calls, WP-6e's size (the switch is at 4 as before).

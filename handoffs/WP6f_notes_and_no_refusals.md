# WP-6f — Three reranker fixes, and no more refusals (handoff brief)

**For:** the operator-controlled implementation agent.

**Read first:**
- `handoffs/WP6e_REPORT.md` (§2 stage 1, §3.2, §8) and `handoffs/WP6d_REPORT.md` §9;
- `Ask/tools/derive_catalog.py` (`_DISAMBIGUATION` ~L1144, `RANKING_FLOOR_DEFAULTS`);
- `Ask/query_router/breakdown.py` (`group_by_from_text`, `_TOTAL`);
- `Ask/query_router/router.py` (`_refusal_precedence` and its comment block, `_serve_unanswerable`, `_reading_chips`);
- `Ask/query_router/reranker.py` (`_RERANK_SYS`, the "CANNOT answer" rule);
- `Ask/query_router/unanswerable_catalog.py`;
- `Ask/refusal_recall.py` and `Ask/prdw_gates.py` (gates 6 and 8);
- `Ask/tools/migrations/m6_ranking_floor.py` (the pattern M7 follows);
- `Ask/eval_questions_full.json` (the 19 known-unanswerable gold rows);
- `Ask/grade_eval1.py` (`grade_pilot`, `grade_wp6d`).

**Sequencing:** WP-6e has landed (`a8072b7`..`e865c52`). Build on `e865c52`, in a fresh mirror (`C:\dev\odisha-wp6f`). **The "found by" switch stays at 4**; this package does not touch it.

**Scope — four items, all ruled by the operator on 2026-09-28:**
1. a reranker note so "sanctioned amount from SFC / Own Funds" reaches BUD-003 / BUD-005 (T1);
2. a reranker note so "compare / sector-wise tied spending, water vs sanitation" stays on EXP-009 (T2);
3. a plain count of planned activities in a place answers as **one figure** (T3);
4. **no refusals where the data exists.** The operator's reason: *"We are working on sample data, in prod, this data is there. We should not have any refusals"* (T4). **Amended 2026-09-29:** *"let's not remove the 14 questions — let's leave it as is with the refusal."* So the 16 refusals whose data or definition exists become real questions, and the 14 with no column in the schema **stay refusals, unchanged**.

**Not in scope:**
- skipping WP-6 filter variants in the "found by" lines (WP-6e §8);
- "sector" and "Sankalp" (parked, D33 stands);
- Odia (#1214);
- search gaps where the right template is not among the 30 (#1852, pilot 1002);
- the 14 refusals whose data has **no column anywhere in the schema** (T4c) — they stay exactly as they are, and SQL for them waits for the production schema;
- the refusal-precedence rule, the reranker's "CANNOT answer" instruction and the refusal gates — they stay, now covering 14 entries.

## 0. Why this package exists

### What WP-6e left open

| row | question | after WP-6e | cause |
|---|---|---|---|
| 1005 / 1007 / 1009 | "split the sanctioned funds into SFC and Own Funds", "What share of the sanctioned budget came from SFC and 15th FC", "How much of the sanctioned amount is from the SFC" | about half the time answered | BUD-003 / BUD-005's "↳" says tied/untied; the reranker weighs that against the scheme phrasings and flips run to run. When it did answer 1009 it chose **BUD-002**, which is funding *recorded* in the **cashbook**, a different measure from the *sanctioned* amount — yet `grade_pilot` graded it correct |
| Eval_1 42 / 49 | "Compare tied fund spending between water and sanitation for …" | asked (42), TRD-002 once (49) | the redirect sentence exists, but only on the **wrong** templates (TRD-002 and TRD-008 each say "…water vs sanitation is EXP-009"); EXP-009's own "↳" says nothing |
| Eval_1 44 | "What is the sector-wise expenditure of tied funds for water and sanitation" | **wrong**, TRD-008 | TRD-008's question reads "approved cost and expenditure **sector-wise** in a district" |
| pilot 1043 / 1044 | "What is the count of planned activities in Barpali / Attabira in …" | 1043 answered once in two runs, per theme; 1044 served the PLU-005 refusal | no plain-count statement; PLN-024 is per theme; 1044's refusal is D28.5 rank-0 precedence firing after the reranker declined |

**Measured by the PM, offline, free.** A global "count of / number of / how many activities means one total" rule would change the breakdown of **42 of 633** replayed questions. That includes every "Which GP has the **highest number** of planned activities?" ranking and every status count ("How many activities are in progress…"). **So T3 is scoped to PLN-024, not global.**

### The refusals — what the 30 actually are

The PM checked every refusal's stated blocker against the DuckDB schema (19 tables):

| group | entries | blocker | what T4 does |
|---|---|---|---|
| **a. the data is empty, the columns exist** (12) | **PLU-005** (`activity_delegation.is_delegated`, `delegated_unit_*`); **AST-004, AST-005, AST-010, AST-011** (`activity_asset.asset_loc_*`, `asset_unit_count`, `asset_unit_cost`); **BEN-001, BEN-003, BEN-007, BEN-008, BEN-010, BEN-011, BEN-012** (`activity_nsap`: `nsap_id, activity_code, category, age_band, gender, beneficiary_count` — the table exists, 0 rows) | 100% NULL or 0 rows **in the sample** | becomes a real template with SQL; in the sample it answers 0 / no rows, in production it answers from the data |
| **b. a definition is missing, the data exists** (4) | **PLN-022, PLN-023** ("blocks / districts consistently delayed in GPDP approvals"); **PLN-041, PLN-042** ("themes consistently among the top / lowest priorities over the last five years") | no rule for "consistently", and no deadline | becomes a template built to the definition in T4b |
| **c. no column anywhere in the schema** (14) | **SCH-004** (ZP / block tier funds — `gram_panchayat` is GP rows only); **PHY-002, PHY-005** (stage dates); **ALR-006** (suspension status and date); **ALR-007** (planned duration / start date); **ALR-010** (resource envelope); **DSS-004** (PAI grades); **SBM-SWM-033** (repair flag); **BEN-002** (village), **BEN-004** (cash vs kind), **BEN-005** (cash amount), **BEN-006** (purpose), **BEN-009** (beneficiary names, village, benefit), **DQY-005** (village field) | the sample schema has nothing to query | **stays a refusal, unchanged** (operator, 2026-09-29); listed for the production schema so a later package can author SQL |

### What stays the same

A refusal exists to stop a near-miss from answering a different question confidently. WP-4's PLN-020 served a table of zeros for "which blocks are consistently delayed". Groups a and b get real SQL, so they need no refusal. Group c keeps its refusal, so those 14 questions keep their protection.

One consequence worth knowing. The refusal-precedence rule stays too, and it is what served the PLU-005 refusal to pilot row 1044, "count of planned activities in Attabira". PLU-005 becomes a real template here, so that particular misfire cannot recur through PLU-005. The rule can still serve one of the remaining 14 to an answerable question, as it did with PLN-022 / PLN-023 on row 315 in WP-6b and WP-6d. T5 reports any such row.

## 1. Hard constraints

- **Catalogue changes only through `Ask/tools/migrations/`:**
  - **M7** moves the 16 group-a and group-b entries out of `unanswerable_catalog.py` and adds them as templates with their SQL (T4). The 14 group-c entries are not touched;
  - reranker notes go in `_DISAMBIGUATION` (T1–T3);
  - no other template's SQL text changes.
- `derive_catalog.py --check` and `validate_catalog.py` stay green. The Test Report / oracle gains the new templates, **executed against the sample** with their row counts recorded; "legitimately return no rows" grows accordingly.
- The "found by" switch stays at 4.
- Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched; every paid run through `confirm_spend`; Ask stays on `gpt-5.4-mini`.
- No file that serves "sector" or "Sankalp" changes (`sector_clarification`, `_THEME_ALIASES`, `EXPECTED_TO_ASK`, the PLN-049 / PLN-032 notes). T2's note names "sector-wise" only as wording on EXP-009.

## 2. T1 — BUD-003 / BUD-005: sanctioned amount by scheme

Add to `_DISAMBIGUATION`:

- **BUD-003:** *"Also the SANCTIONED AMOUNT BY SCHEME: 'how much of the sanctioned amount came from SFC / Own Funds / the 15th Finance Commission', 'split the sanctioned funds into SFC and Own Funds' is THIS — `$scheme` for one scheme, the per-scheme breakdown for several. Funding RECORDED per source in the cashbook is BUD-002, a different measure."*
- **BUD-005:** the same, for a **share** or **percentage** of the sanctioned budget.
- **BUD-002:** one line the other way round: *"CASHBOOK funding recorded per source. A question about the SANCTIONED amount is BUD-003 (amount) or BUD-005 (share)."*

**Grading fix.** `grade_pilot` currently accepts any per-scheme answer for rows 1005 / 1007 / 1009. Narrow them to the measure asked:
- 1005 and 1009: BUD-003 or SAN-013 (sanctioned);
- 1007: BUD-005.

Re-grade WP-6e's pilot file with the narrowed rule and report the corrected baseline beside the new run.

## 3. T2 — EXP-009 family: comparing focus areas, not years or sectors-in-a-district

Add to `_DISAMBIGUATION` for EXP-009 and its identical twin EXP-011:

> *"Comparing tied-fund spending ACROSS FOCUS AREAS in one year or span — 'compare tied fund spending between water and sanitation', 'sector-wise expenditure of tied funds for water and sanitation' — is THIS with a focus-area list: one row per focus area. Two different years side by side is TRD-002; approved cost against expenditure per sector in one district, not restricted to tied funds, is TRD-008."*

TRD-002 and TRD-008 keep their existing sentences. Sharpen TRD-008's to name the tied-fund point: *"…A question about TIED funds is EXP-009, even when it says 'sector-wise'."*

## 4. T3 — A plain count of planned activities answers as one figure

**a) The reranker note on PLN-024:**

> *"Also the PLAIN COUNT of planned activities in a place — 'count of / number of planned activities in Barpali', 'how many activities are planned in <block / GP / district> in <year>' — answered as ONE total (the 'total' breakdown)."*

**b) The breakdown, scoped to PLN-024 only.** When the served template is PLN-024, and the question asks for a count of (planned) activities, and it has **no** breakdown cue (the phrase reader returns None), and it has **no** ranking word (which / highest / most / lowest / top / rank), bind `group_by = 'total'`. Declare it on the template, in the `RANKING_FLOOR_DEFAULTS` pattern (for example `"plain_count_total": True`), not as a global cue.

**Prove (offline, free).** Run the new rule over all 633 questions of the WP-6e Eval_1 / gold / pilot replays with their recorded served template. List every row whose breakdown changes. **Expected:** only the pilot plain-count rows and the Eval_1 "total activities in main GPDPs" group (rows 141–149) when served PLN-024. **Stop and report if anything else changes.** The echo reads "(as one total)".

**Grading.** The plain-count rows (1039–1044 and their chip taps) expect PLN-024 **with one figure** (`group_by = total`), not "answered at all".

## 5. T4 — No refusals where the data or definition exists

### a) Group a — 12 templates with real SQL (M7)

- **Ids.** Each entry keeps its id (PLU-005, AST-004, …, BEN-012), so every gold row and every reference still resolves.
- **Questions and phrasings.** `question` becomes `abstract_question` with `{slot}` placeholders, and `paraphrases` carry over unchanged.
- **Slots.** The universal optional slots are added the way M1 did, `$group_by` where the statement is a single aggregate (M2 pattern).
- **SQL** reads the `v_*` views where they carry the columns, and the base tables otherwise:
  - **PLU-005:** activities in a block whose delegation is recorded (`is_delegated = 1`), by delegated unit level / type.
  - **AST-004 / AST-005:** asset locations and unit counts; unit count and unit cost for one activity.
  - **AST-010 / AST-011:** average unit cost per sub-category in a district; assets more than a threshold percent above the district average — this is a real threshold, required, `unit: percent`, `direction: above`, derived by WP-6c's rule.
  - **BEN-001 / 003 / 007 / 008 / 010 / 011 / 012:** `SUM(beneficiary_count)` from `activity_nsap` joined through `activity_code` to the activity's GP, block and scheme. BEN-008 is an **absence** question and reads the GP roster (PLN-032 pattern). BEN-010 "each pension scheme" groups by `activity_nsap.category` **only if** `category` holds the pension scheme. **Check the column's `dim_code` decode; if it does not, BEN-010 moves to group c** and the report says why.
- **Execution.** M7 executes every new statement against the sample before writing, and records its row counts in the oracle. Expect 0 rows, or a zero row for Count templates (WP-6b T4 rendering).

### b) Group b — 4 templates built to a definition

The PM's recommended definitions. **The operator confirms or changes them before dispatch**; build what is ruled.

- **PLN-022 / PLN-023** ("blocks / districts consistently delayed in GPDP approvals"):
  - a required `$deadline` date, asked with WP-6c's plain-words ask ("By what date should the GPDP have been approved?"), as PLN-010 already does;
  - per block / district over the chosen year(s): GPs, GPs whose plan `approval_date` is after the deadline, share late, and — for a span — the number of years in which more than half its GPs were late;
  - ordered by share late, highest first; `top_n` default 10.
- **PLN-041 / PLN-042** ("themes consistently among the top / lowest priorities over the last five years"):
  - per theme, the number of the five most recent fiscal years in the data in which it ranked in the **top 3 / bottom 3 by planned cost**;
  - listed with that count, highest first;
  - the echo states the rule: "(top 3 by planned cost, in how many of the last 5 years)".

### c) Group c — 14 entries stay refusals, unchanged

M7 does not touch them: same ids, questions, reasons, phrasings and alternatives. `handoffs/WP6f_prod_schema_needs.md` lists each one with the column(s) it would need, so the operator can check them against the production schema and a later package can author SQL. That file changes no behaviour.

### d) The refusal machinery stays, over 14 entries

With `UNANSWERABLE_CATALOG` down from 30 entries to 14:
- `_refusal_precedence`, `_serve_unanswerable`, the "Why I can't answer" chip label and the reranker's "CANNOT answer" rule are **unchanged**;
- **gates 6 and 8** keep running over the 14 remaining entries. Their expectations change only where they named one of the 16 moved entries. Refusal recall must stay at its current level on the 14; report it before and after;
- **tests** that pinned one of the 16 moved entries as a refusal are rewritten to expect the template. List each one in the report.

### e) Gold expectations

For each of the 19 known-unanswerable gold rows:
- **group a or b:** the expectation becomes the new template, answered;
- **group c:** unchanged — still the refusal.

Give the mapping row by row in the report.

## 6. T5 — Measure, then report

1. **Offline:**
   - M7 `--check`;
   - the T3 row-change list;
   - every new template executed against the sample (row counts);
   - derive / validate / the full suite / `prdw_gates.py` green, with gates 6 and 8 over the 14 remaining refusals.
2. **Targeted rows (~60 calls):**
   - pilot 1005, 1007, 1009, 1039–1044 with their chip taps;
   - Eval_1 42, 44, 49, 141–149;
   - **one question per group-a and group-b template** (16 new rows in `handoffs/WP6c_pilot_questions.json` as a sixth standing group: the entry's own question, a place and a year filled in).
3. **Eval_1** (314 rows), **gold** (275 rows, in parallel parts as the operator prefers, follow-up rows kept with their predecessor), and **the 44 pilot rows**, each diffed row by row against WP-6e's runs.
4. **Report** `handoffs/WP6f_REPORT.md`:
   - per-row outcomes for T1–T3's rows;
   - the corrected 1005 / 1007 / 1009 baseline;
   - the T3 change list;
   - every new template's SQL summary and sample row count;
   - **every refusal served in any run**, with whether the question was genuinely one of the 14;
   - refusal recall on the 14, before and after;
   - the gold mapping for the 19;
   - rewritten tests;
   - spend.

**Expected spend:** about 2,050 calls, all through `confirm_spend`.

| run | calls |
|---|--:|
| targeted rows | ~60 |
| new rows | ~50 |
| Eval_1 | ~1,000 |
| gold | ~800 |
| pilot | ~150 |

## Gate (definition of done)

1. M7 applied and idempotent. `UNANSWERABLE_CATALOG` holds exactly the 14 group-c entries, unchanged (15 if BEN-010 moves to group c). The new templates execute against the sample with their counts in the oracle. `derive_catalog.py --check` is green, and `validate_catalog.py` reads 343 + 16 templates (or 343 + 15) with 0 problems.
2. The full suite and `prdw_gates.py` are green, with gates 6 and 8 over the 14; refusal recall on the 14 no lower than before.
3. T3 changes the breakdown on no row outside the expected set.
4. T1–T3's rows: 1005 / 1009 on BUD-003 or SAN-013 and 1007 on BUD-005 in at least one run of each; 42 / 44 / 49 on EXP-009 or asked with EXP-009 first; plain counts on PLN-024 as one figure.
5. None of the 16 moved entries is ever served as a refusal. Every refusal served in any run is listed, and any served to an answerable question is flagged.
6. Eval_1, gold and pilot are diffed against WP-6e. Confidently wrong on gold is reported beside WP-6e's 6.
7. This brief, `WP6f_prod_schema_needs.md` and the report committed, one commit per task, not pushed.

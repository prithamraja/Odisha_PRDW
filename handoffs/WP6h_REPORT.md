# WP-6h — Chips keep every year the officer named: REPORT

> ## Where everything is
>
> ```
> Ask/query_router/router.py            T1 _extract_fill_values reads the year slot as a list
>                                       T2 _chip_years (new), _reading_chips(..., template_map),
>                                          the three call sites pass the template map
> Ask/tests/test_wp6h_chip_years.py     T3 13 tests; T4 +2 harness tests (15 in all)
> Ask/run_custom_eval.py                T4 "chip": N taps the chip in place N
> Ask/grade_eval1.py                    T4 the eighth standing group (grade_wp6h)
> handoffs/WP6h_offline_proof.json      T1/T2 chip change lists (sections t1, t2)
> handoffs/WP6c_pilot_questions.json    T4 rows 1070–1076, group "WP-6h chip years"
> handoffs/WP6h_live_questions.json     T4 the 7 live rows
> handoffs/WP6h_live_check.jsonl/.csv   T4 their records, graded
> handoffs/WP6h_live_1072_three_turns.jsonl  T4 row 1072 carried to its answer
> handoffs/WP6h_rerank_calls.jsonl      T4 every reranker call of the main run (10)
> ```
>
> **Committed, not pushed**, one commit per task: `a908e74` T1 (with the brief
> and the proof), `897eb78` T2, `df348bf` T3, `837227b` T4, and T5's commit
> carrying this report. Left for the operator as before: the PM's
> `handoffs/PROJECT_PLAN.md` edit.
>
> Mirror: `C:\dev\odisha-wp6h`, a plain copy of `C:\dev\odisha-wp6g` (so of
> `Ask/` at `0fa2c9c`, byte-identical on every tracked file outside `bench/`,
> with WP-6g's search index; the catalogue did not change, so nothing was
> re-embedded). `C:\dev\odisha-wp6h-t1` is a throwaway copy holding T1's router
> alone, used only to produce the T1 proof.

---

## 0. For the PM — what this package found

1. **Every gate item passes.** A chip on a multi-year question now carries
   every year ("…in 2022-2023, 2023-2024 and 2024-2025?"), and a tap binds them
   all. A chip that cannot hold them is dropped. If no other chip remains, it
   is offered with the narrowing marked: "(2024-25 only)" for a one-year
   template, "(2022-23 and 2024-25 only)" for a comparison.
2. **Only multi-year questions change.** Over the 607 questions of the
   WP-6e/6f/6g replays, the chip pre-fill changes on 80. Every one names more
   than one year, and only the year slot moves. Of the 79 chip turns rebuilt
   from their recorded candidates, 19 change, all multi-year. **0 of 1,201
   answered turns bind differently.**
3. **Live, every tap answered with every year named.** 1071 (Khordha,
   FND-010, three years), 1075 (TRD-001, the pair 2022-23 / 2024-25), and
   1072 (PLN-023, three years, once the deadline was given). On 1071 the
   three-year TRD-004 comparison chip was dropped, as designed (log: "chip
   dropped: TRD-004 cannot hold every year named").
4. **Three rows did not reach a chip this time.** The reranker picked a
   template on the first turn for 1070, 1073 and 1076, which WP-6g saw it
   decline. Each answered with every year. The reranker was not touched, so
   this is ordinary run-to-run variation.
5. **One new finding, outside this package's scope: the same silent narrowing
   on the answer path.** 1074 ("Activities planned 2022-23 – 2024-25") was
   answered on the first turn by TRD-001, a two-year comparison. It compares
   2022-23 with 2024-25 and drops 2023-24, and nothing on the answer says so
   (§7.1). The brief froze the answer path, so this is reported, not changed.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | Multi-year chips carry every year on list-capable templates; a tap binds every year; one-year templates dropped or marked "(… only)"; single-year chips unchanged | **PASS**: `test_wp6h_chip_years` covers all three forms ("2022 to 2025", "2023-2025", "from 2022-23 to 2024-25"), each carried and bound on tap. It also covers all five comparison templates (pair filled in order, tap binds it), drop and mark for the comparisons and for a one-year stand-in, and single-year and no-year chips equal to the old rendering |
| 2 | T1's change list holds only multi-year questions | **PASS**: 80 of 607 questions and 19 of 79 chip turns change, every one naming more than one year; the only slot that moves is `date_range` (§2) |
| 3 | Answer path byte-identical; WP-6d chip tests unchanged; suite and gates green; catalogue checks untouched (358 / 0) | **PASS**: 0 of 1,201 answered turns bind differently (offline). Answer bindings are pinned in `AnswerPathTests`, and the router diff touches only `_extract_fill_values`, `_reading_chips` and their three call sites. **No existing test changed.** **GATE GREEN 9/9, 833 tests** (818 + 15; 28 skipped without a live key), gate 5 against the live model list. `validate_catalog.py` 358 templates · 0 problems; `derive_catalog.py --check` in step |
| 4 | Live taps answer with every year named, or visibly narrower | **PASS for every tap** (1071, 1072, 1075); three rows answered with every year before any chip; 1074 is the answer-path case in §0.5 |
| 5 | Brief and report committed, one commit per task, not pushed | **PASS** (header) |

---

## 2. T1 — the chip pre-fill reads years as a list

`_extract_fill_values` passes `list_slots` to `_extract_slot_values`. That is
the union of the candidates' list-capable slots (`_list_slots`), as the brief
asks, **plus the `fiscal_year` slot itself** (my addition, §5.1). The list
value is kept and validated item by item by the existing WP-6d code, as schemes
already were.

**The proof** (`WP6h_offline_proof.json`, section `t1` for T1's code alone,
section `t2` for the final code; the counts are identical). How it was run:
- **What was compared:** the WP-6g mirror (old) against the new code.
- **Questions:** every question and second turn of `WP6e_{eval1_replay,
  gold_replay_run1, pilot_replay, stage1}`, `WP6f_{same}` and
  `WP6g_live_check`: 607 distinct questions.
- **Extractor:** stubbed to return nothing. The replays do not record what it
  gave the chip pre-fill, so only the deterministic readers fill.
- **Candidates:** from the reranker call logs (its near misses, or all 30 on
  the miss path). For the ambiguous-zone rows, which make no reranker call,
  they come from retrieval over the cached gold query vectors.
- **Not rebuilt:** 3 chip questions (6 turns) have neither a call log nor a
  cached vector: "road works … for 2020-2021", the weather question and the
  leave application. None names more than one year, so none can change.

- **Pre-fill with every catalogue template as candidate** (so it covers every
  question whatever its chips): 80 of 607 change, **all `date_range`, all
  naming two or more years** — "for 2024 to 2026" (the Eval_1 wordings),
  "over the last five years", "between 2023-24 and 2024-25", and the WP-6g span
  rows.
- **Rebuilt chip turns**: 19 of 79 change. The old code's rebuild matches the
  recorded chips exactly on 42 of 79. The rest differ only because the stubbed
  extractor leaves out places and schemes the live one supplied.

| question | turns | year fill before → after | chips | first chip now |
|---|---|---|---|---|
| Provide the sum of the planned budget outlay across main GPDPs for 2024 to 2026. | 6e Eval_1 #7 | 2025-26 → 2024-25, 2025-26 | 2→2 | How much planned expenditure is allocated to each GPDP theme in 2024-2025 and 2025-2026 (main GPDP; as one total)? |
| Show me the GPs whose planned activities have an estimated cost of zero for 2024 to 2026. | 6e Eval_1 #12 | same | 3→3 | How many no-cost activities are planned in a block for 2024-2025 and 2025-2026? |
| Compare tied fund spending between water and sanitation for 2024 to 2026. | 6e Eval_1 #42, 6e stage 1 #42 | same | 3→3 | How much tied-fund expenditure was incurred under a focus area in 2024-2025 and 2025-2026? |
| Provide the aggregate number of activities planned across main GPDPs for 2024 to 2026. | 6e Eval_1 #145 | same | 3→3 | How many activities are planned under each GPDP theme in a gram panchayat in 2024-2025 and 2025-2026 (main GPDP; as one total)? |
| Provide the overall expected cost of planned activities in the state for 2024 to 2026. | 6e Eval_1 #174 | same | 3→3 | How much planned expenditure is allocated to each GPDP theme in 2024-2025 and 2025-2026 (as one total)? |
| Which GPs proposed activities costing zero rupees for 2024 to 2026? | 6e Eval_1 #188 | same | 3→3 | How many no-cost activities are planned in a block for 2024-2025 and 2025-2026 (broken down by gram panchayat)? |
| Show the sector with the highest completion rate of activities for 2024 to 2026. | 6e/6f Eval_1 #283 | same | 3→3 | Which focus area has the lowest completion rate in 2024-2025 and 2025-2026? |
| Identify the sector with the highest percentage of completed activities for 2024 to 2026. | 6e/6f gold #2042, 6f Eval_1 #281 | same | 3→3 | What is the completion rate under each theme and focus area in 2024-2025 and 2025-2026? |
| Blocks consistently delayed in GPDP approvals from 2023-24 to 2025-26 | 6g #1062 | 2025-26 → three years | 3→3 | Which Blocks consistently experience delays … in 2023-2024, 2024-2025 and 2025-2026? |
| How many activities were planned from 2022-23 to 2024-25? | 6g #1060 | 2024-25 → three years | 3→3 | How many activities are planned under each GPDP theme in a gram panchayat in 2022-2023, 2023-2024 and 2024-2025? |
| Beneficiary trend in Barpali from 2022-23 till 2024-25 | 6g #1063 | 2024-25 → three years | 3→3 | How many beneficiaries are recorded across GPs of a block under a scheme for 2022-2023, 2023-2024 and 2024-2025? |
| Planned cost between 2022-23 and 2024-25 | 6g #1066 | 2024-25 → 2022-23, 2024-25 | 3→3 | How much planned expenditure is allocated to each GPDP theme in 2022-2023 and 2024-2025? (the two comparison chips were already right and are unchanged) |
| Total expenditure from FY 2021-22 to FY 2023-24 in Khordha | 6g #1061 | 2023-24 → three years | **3→2** | TRD-004 dropped (§3); the other two carry the three years |
| Activities planned 2022-23 – 2024-25 | 6g #1064 | 2024-25 → three years | **3→2** | TRD-001 dropped (§3); the other two carry the three years |
| Planned activities in 2023-2025 | 6g #1067 | 2024-25 → 2023-24, 2024-25 | 3→3 | How many activities are planned under each GPDP theme in a gram panchayat in 2023-2024 and 2024-2025? |

With T1's code alone, the comparison chips beside a list read "between
2022-2023 and 2022-2023 and 2024-2025". T2 is what renders them right; the T1
commit message says so.

---

## 3. T2 — each chip rendered for what its template can hold

`_chip_years(template, fill)` returns the fill one chip renders with, and a
note when that chip holds fewer years than were named. `_reading_chips` drops
the noted chips, unless no answerable chip would remain. In that case it offers
them with the note in brackets: `f"{text.rstrip('?. ')} ({note})?"`, the same
ending rule `_with_appended` uses. `send_text` is the label, as before.
The catalogue has 329 list-capable year slots, 5 two-year comparisons and 24
templates with no year. **No template takes exactly one year**, so the
one-year rule is pinned on a stand-in template in the tests.

**The five comparison templates** all read "between {date_range_2} and
{date_range}", so the earlier year goes in `$date_range_2`, the SQL's year1.
That is the catalogue's convention (`_validate_fiscal_year`,
`test_paired_year_direction`).

| template | question | 2 years named | 3+ years named, beside another chip | 3+ years, nothing else answerable |
|---|---|---|---|---|
| PLN-039 | Which themes have shown the greatest increase in planned activities between {date_range_2} and {date_range}? | pair filled, earlier → `$date_range_2` | dropped | the two end years, "(2022-23 and 2024-25 only)" |
| PLN-040 | … greatest decline … between {date_range_2} and {date_range}? | same | dropped | same |
| TRD-001 | Compare the activities planned and started theme-wise between {date_range_2} and {date_range}. | same | dropped | same |
| TRD-002 | Compare the approved cost and expenditure theme-wise between {date_range_2} and {date_range}. | same | dropped | same |
| TRD-004 | How did the total expenditure of {block_name} change between {date_range_2} and {date_range}? | same | dropped | same |

Each tap re-reads its chip. Two years bind `date_range_2` = earlier and
`date_range` = later, tested on all five; TRD-004 is checked at the reader
because it also needs a block. A marked chip binds exactly the years it
names: "(2024-25 only)" adds no year, since the reader reads 2024-2025 and
2024-25 as one year (tested).

One year named, or none: the fill is returned unchanged, and the chips equal
the pre-WP-6h rendering (tested on four questions against a copy of the old
function).

---

## 4. T3 — tests

`tests/test_wp6h_chip_years.py`, 13 tests for T1–T3. (The T3 commit message
says 15; that count is true only after T4's two harness tests were added.)

- `ListChipTests`: the three forms, carried and bound on tap; the operator's
  row 1060.
- `ComparisonChipTests`: the five templates' wording; pair order and tap on
  all five; two years also fill a list chip beside them, with no "and
  2022-2023 and"; three years drop the comparison (and log it); a lone
  comparison is marked "(2022-23 and 2024-25 only)" and its tap binds that pair.
- `OneYearChipTests` (stand-in template): dropped beside a list chip; alone,
  "How many activities are planned in 2024-2025 (2024-25 only)?", tap reads
  one year; a refusal alone does not hide the marked chip.
- `SingleYearUnchangedTests`: four single-year / no-year questions equal the
  old rendering; one pinned.
- `AnswerPathTests`: five answer-path bindings pinned (the span, "2023-2025",
  one year, the TRD-002 pair from "between" and from "from … to").
- `HarnessTests` (T4): tap by number; `grade_wp6h` on four synthetic records.

WP-6d's chip tests ran unchanged and green.

---

## 5. Decisions I made

1. **The year is read as a list whenever a candidate has a year slot, not only
   when a candidate takes a list.** With the brief's union alone, a chip set
   made only of comparisons (row 1064's shape, or a lone TRD-001) read one
   year. The chip could not tell three years had been named, and narrowed
   silently. This is exactly what the test for "only candidate → marked"
   caught. It is chip-only: the answer path's `list_slots` is untouched.
2. **A comparison left alone with 3+ years names both end years:** "(2022-23
   and 2024-25 only)". The brief's "(2024-25 only)" is written for a one-year
   chip; a comparison needs two years to answer at all.
3. **"Every candidate dropped" counts answerable chips.** A refusal chip ("Why
   I can't answer: …") is never dropped, since it has no year slot. If it
   alone remained, the officer would get no answerable chip, so the marked
   chips are offered beside it.
4. **`$date_range_2` is left off every non-comparison chip when several years
   are named.** It is read only for a comparison candidate. On a chip with no
   template (a refusal) it would otherwise be appended as an extra year.
5. **Harness:** `"chip": 1` taps the first chip (the chip's wording is not
   known before the run); `grade_wp6h` grades the eighth group.

---

## 6. T4 — live check

The 7 rows (`WP6h_live_questions.json`, also rows 1070–1076 of
`WP6c_pilot_questions.json`) were run through `confirm_spend` in one process,
one fresh session each, tapping the first chip. Every reranker call was logged.
Row 1072 was also run as three turns (ask, tap, "30 June 2025") in its own
session.

| row (from) | question | first turn | chips shown | tap → answer | years bound | graded |
|---|---|---|---|---|---|---|
| 1070 (1060) | How many activities were planned from 2022-23 to 2024-25? | **answered**: PLN-024, 3 rows, "(broken down by year)" | none | — | 2022-23, 2023-24, 2024-25 | correct |
| 1071 (1061) | Total expenditure from FY 2021-22 to FY 2023-24 in Khordha | asks (reranker no_match: FND-010, TRD-004, TRD-012) | "What is the total amount recorded per scheme across Khordha district in 2021-2022, 2022-2023 and 2023-2024 (as one total)?" · "How does Khordha district compare with the state average on expenditure per GP and completion rate for 2021-2022, 2022-2023 and 2023-2024 (as one total)?" (**TRD-004 dropped**) | **FND-010**, Khordha, 3 scheme rows (XV FC ₹1.22 crore spent, 70.65%; SFC ₹50.7 lakh; …), "(… combined)" | **2021-22, 2022-23, 2023-24** | correct |
| 1072 (1062) | Blocks consistently delayed in GPDP approvals from 2023-24 to 2025-26 | asks (no_match: PLN-023, PLN-022, PLN-020) | "Which Districts consistently experience delays in GPDP approvals after the deadline a deadline in 2023-2024, 2024-2025 and 2025-2026?" · the Blocks one · "Which Blocks have the highest number of pending GPDP approvals in 2023-2024, 2024-2025 and 2025-2026?" | asks "By what date should the GPDP have been approved?"; three-turn run, reply "30 June 2025" → **PLN-023**, 9 districts, Kandhamal 33.33% late, Cuttack 16.67% | **2023-24, 2024-25, 2025-26** (turn 3) | clarify (2-turn row); three-turn run answers with all three |
| 1073 (1063) | Beneficiary trend in Barpali from 2022-23 till 2024-25 | **answered**: BEN-012, Barpali block, 0 rows (`activity_nsap` is empty in the sample) | none | — | 2022-23, 2023-24, 2024-25 | correct |
| 1074 (1064) | Activities planned 2022-23 – 2024-25 | **answered**: TRD-001, 7 theme rows | none | — | **2022-23, 2024-25 only**: the answer path's pair (§7.1) | incorrect |
| 1075 (1066) | Planned cost between 2022-23 and 2024-25 | asks (no_match: TRD-001, TRD-002, BUD-006) | "Compare the activities planned and started theme-wise between 2022-2023 and 2024-2025." · "Compare the approved cost and expenditure theme-wise between 2022-2023 and 2024-2025." · "How much planned expenditure is allocated to each GPDP theme in 2022-2023 and 2024-2025?" | **TRD-001**, 7 theme rows (Theme 6: 131 planned in 2022-23 → 1,173 in 2024-25) | **2022-23 → `$date_range_2`, 2024-25 → `$date_range`** | correct |
| 1076 (1067) | Planned activities in 2023-2025 | **answered**: PLN-024, 2 rows | none | — | 2023-24, 2024-25 | correct |

Graded (`WP6h_live_check.csv`, the new `grade_wp6h`): **5 correct, 1 clarify
(1072, which completes in the three-turn run), 1 incorrect (1074, answer
path).** No chip seen live was marked "(… only)": no live chip set was made
only of templates that could not hold the years. That case is proved in the
tests and offline only.

Two things the table shows that are not about years:
- 1072's first chip is the **Districts** template for a question about
  Blocks. That is the reranker's order, and a tap answers about districts.
- The PLN-022/023 chips read "after the deadline a deadline", an older
  stand-in wording.

---

## 7. Found, not fixed

1. **The answer path narrows a span silently on a two-year comparison.**
   Asked a three-year span, a comparison template is served on the first
   turn. It binds the two end years (`$date_range` the latest, `$date_range_2`
   the earliest) and says nothing about the middle year. Live: 1074, TRD-001,
   2023-24 dropped, echo "…between 2022-2023 and 2024-2025." This is the same
   defect this package removed from chips, on the other path. Worth a small
   package: on a comparison template with more than two years named, either
   ask, or add the same "(2022-23 and 2024-25 only)" to the echo.
2. **"after the deadline a deadline"** on PLN-022/023 chips (the `$deadline`
   stand-in follows the word "deadline"). Older than WP-6h.
3. **The reranker's chip order can put the wrong tier first** (1072: Districts
   for a Blocks question). A tap then answers a different question at the right
   years.

---

## 8. Changed test pins

None. All 818 existing tests pass unchanged, WP-6d's chip tests included; 15
tests were added.

---

## 9. Spend

- **Live check:** `confirm_spend` estimated **~50 calls** for the 7 two-turn
  rows and **~10** for row 1072's three-turn run, a ceiling of ~60 against the
  brief's ~40. These are ceilings: three rows answered on the first turn and
  never used their second-turn allowance. Metered reranker calls: **10** in the
  main run (68,639 prompt tokens, 1,717 completion), plus 2 unlogged in the
  three-turn run.
- **Gates:** one model-list call (gate 5, final run).
- **T1 / T2 proofs and all tests:** free (no model, no network; retrieval for
  ambiguous-zone rows from cached vectors).

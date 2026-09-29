# WP-6g — "From 2022-23 to 2024-25" means every year in between; the "refusal wins" rule is removed: REPORT

> ## Where everything is
>
> ```
> Ask/query_router/date_phrase.py        T1 _FY_TO_FY_RE, _BARE_TO_FY_RE, _one_fiscal_year,
>                                        _MAX_LABELLED_SPAN_YEARS = 10; claimed first in resolve_fiscal_years
> Ask/query_router/router.py             T1b _refusal_precedence and its call site removed (history note in
>                                        its place); T1c the year ask in _fill_slots_or_clarify, "year" in
>                                        officer-facing slot wording, serve_pending_answer keeps year lists
> Ask/query_router/year_ask.py           T1c new: the ask, the chips, slot_words, is_year_chip
> Ask/query_router/pending_resolver.py   T1c a year chip tap resumes; the re-ask says "year" with the chips
> Ask/query_router/interpretation.py     T1c readable_slot("date_range") -> "year"
> Ask/tests/test_date_phrase.py          T2  +21 tests (span forms, links, guards, mixed forms, §0 pins)
> Ask/tests/test_refusal_precedence.py   T1b rewritten for the new behaviour
> Ask/tests/test_wp6g_year_span.py       T1c 18 tests
> Ask/grade_eval1.py                     T4  the seventh standing group (grade_wp6g)
> Ask/run_full_eval.py                   docstring only
> handoffs/WP6c_pilot_questions.json     T4  rows 1060–1067, group "WP-6g year span"
> handoffs/WP6g_offline_proof.json       T3.1, T3.2, T1b offline lists
> handoffs/WP6g_live_questions.json      T4  the 27 live rows
> handoffs/WP6g_live_check.jsonl         T4  their records;  WP6g_live_summary.json  per-row digest
> handoffs/WP6g_rerank_calls.jsonl       T4  every reranker call (29)
> ```
>
> **Committed, not pushed**, one commit per task: `d9f6562` T1 (with the brief),
> `8952acc` T2, `8978f8e` T1b, `cc6b3eb` T1c, `7eca804` T3, `cc72f8c` T1c
> follow-up (§4.4), `3a111c4` T4, and T5's commit carrying this report. Left for
> the operator as before: the PM's `handoffs/PROJECT_PLAN.md` edit, the
> untracked `handoffs/WP6b_eval1_replay_notes_off.csv`, and `Ask/bench/`.
>
> Mirror: `C:\dev\odisha-wp6g`, a plain copy of `C:\dev\odisha-wp6f` (so of
> `Ask/` at `3374475`, byte-identical on all 132 tracked files, with WP-6f's
> search index; the catalogue did not change, so it was not re-embedded).

---

## 0. For the PM — what this package found

1. **All three changes landed and every gate item passes**, with one live
   shortfall that is not caused here (point 4).
2. **The span now reads every year.** "from 2022-23 to 2024-25", with any end
   form, any label, any of the five link words or a spaced dash, binds
   2022-23, 2023-24 and 2024-25. Nothing else the reader reads changed: over
   all 695 questions of the four WP-6f replays exactly **two** questions change
   (pilot 1055 and 1057, each also in stage 1), and both are "from/to" spans.
   **Zero Eval_1 or gold rows change.**
3. **The fix changes a real answer.** Pilot 1057 ("districts consistently
   delayed … from 2023-24 to 2025-26") now counts 2024-25 as well, and that is
   the year with the late GPs: Kandhamal goes from 0% to **33.33%** late (1 of 3
   GPs), Cuttack from 0% to **16.67%** (1 of 6). Before, every district read 0%.
4. **Most of the eight new pilot rows ask instead of answering — not because of
   the years.** Seven of the eight end in "I couldn't match that exactly. Did
   you mean one of these?": the reranker declines these short wordings ("Activities
   planned 2022-23 – 2024-25"), and the year reader has no part in that choice.
   The one control that routed (1065, "Compare expenditure in 2022-23 and
   2024-25") answers with its two years. **Separately, and older than WP-6g:
   the chips on such a question carry only ONE year** (§7.1) — so a tap on
   them loses the span. Found, not fixed.
5. **The rule removal loses nothing.** Offline, the rule forced one refusal in
   WP-6e (pilot 1044, wrong) and none in WP-6f. Live, 10 of the 11 gold refusal
   rows end in their refusal, **every one the reranker's own pick**; G1974 (Odia)
   asks, exactly as it did in WP-6f. The two Barimunda phrasings that the rule
   had turned into the ALR-007 refusal now answer on PLN-024.
6. **A missing year is asked in plain words, with chips, and a tap answers.**
   "Andhrua untied-fund expenditure" → "Which year? For example 2024-25."
   [2025-26] [2024-25] [2023-24] → tap 2024-25 → EXP-008, Andhrua, untied,
   2024-25: **12 activities, ₹19.06 lakh spent** (₹19,05,636 of ₹19,36,848
   sanctioned, 98.39%).
7. **I fixed one older defect the T4 rows would have hit** (§4.4): a year span
   bound on the first turn collapsed to its latest year whenever a second slot
   (e.g. the deadline) had to be asked. The same weakness remains for
   non-year lists (two focus areas); reported, not changed.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | "from X to Y" between fiscal years reads every year X..Y inclusive, every T1 form; every §0 form that is not a "to" span reads as before | **PASS**: `test_date_phrase` `FiscalYearSpanTests` (each end form and label, every link word, spaced en/em dash, "from" present and absent, 10-year span, 11-year and reversed spans logged and unchanged, money guard at either end, Odia digits) and `UnchangedYearFormTests` (the §0 table, single and relative years). Offline over 695 replay questions: only "to" spans changed (§5) |
| 2 | Full suite and `prdw_gates.py` green; catalogue checks untouched (358 / 0) | **PASS**: **GATE GREEN 9/9, 818 tests** (28 skipped without a live key), gate 5 against the live model list; `validate_catalog.py` **358 templates · 0 problems**; `derive_catalog.py --check` in step. No catalogue, SQL, note or phrasing change |
| 3 | T3's change list holds only "to" spans; every changed row re-executed and reported | **PASS**: 2 distinct rows, both "from/to" fiscal spans, both re-executed (§5) |
| 4 | Pilot 1055 and 1057 bind three years; the eight new rows behave as listed, controls unchanged | **PASS for 1055/1057** (live and offline). **The eight rows: the reader reads each as listed** (pinned in T2 and in the offline proof), and 1065 answers with its two years live; **seven ask** because the reranker declines their wording, which the reader does not touch (§6.3). Controls unchanged: 1065 binds 2022-23 + 2024-25; 1066's chips carry 2022-2023 and 2024-2025; 1067 reads 2023-24 + 2024-25 |
| 5 | `_refusal_precedence` gone; both Barimunda phrasings answer on PLN-024; every refusal served was the reranker's pick; gold refusal rows still end in their refusal, or listed | **PASS**: removed (test `test_the_rule_is_gone`); 2011 and 2012 answer PLN-024 (per theme — acceptable per the brief); 10 refusals served live, 10 reranker picks; **G1974 asks** (the broad "What would you like to know about Andhrua?", as in WP-6f) — listed |
| 6 | "Which year? For example …" with the three latest years as chips; a chip tap and a typed reply both resume and answer; no officer-facing "date range" | **PASS**: live rows 2001–2003 (§4); every typed form in the brief resumes in tests; §4.3 lists each wording changed |
| 7 | Brief and report committed, one commit per task, not pushed | **PASS** (header) |

---

## 2. T1 — the year reader

### 2.1 What it reads

Two new patterns, claimed **before** everything else in `resolve_fiscal_years`
(before the bare-year span too — see 2.3):

- **`_FY_TO_FY_RE`**: `<fiscal year> <link> <fiscal year>`. Each end is any form
  a single pattern reads ("2022-2023", "2022-23", "22-23", also "/" and an
  unspaced en dash inside an end), each with the optional "FY" / "F.Y." /
  "financial year" / "fiscal year" / "plan year" label, and each must name
  exactly **one** fiscal year. The link is to / till / until / through / thru,
  or an en or em dash **with spaces round it**. A leading "from" is neither
  needed nor read.
- **`_BARE_TO_FY_RE`**: a bare head and a fiscal tail (mixed form, 2.2).

Both ends are included. Up to **10** fiscal years; wider, or a tail before its
head, is left to the existing patterns (today's reading) and logged at INFO
("year span '…' left to the single-year patterns: wider than 10 fiscal years" /
"its tail is before its head"). The money and quantity guards apply to each
end: "Rs 2022-23 to 2024-25" and "2022-23 to 2024-25 lakh" keep their old
readings.

Not links, by the brief: "and", "vs", "compare … and …", "between … and …" —
unchanged. Also not links, because they are not in the ruled shape: a spaced
**hyphen** ("2022-23 - 2024-25") and an **unspaced** dash ("2022-23–2024-25");
both keep reading as the two end years. Say if either should join.

### 2.2 Mixed forms — decisions

| form | read as | why |
|---|---|---|
| "from 2022 to 2024-25" (bare head, fiscal tail) | **span**: 2022-23, 2023-24, 2024-25 | Unambiguous: a bare year at the head of a span is the fiscal year that starts in it under both readings the reader already has ("in 2022" and "2022 to …" both start at 2022-23). Before, the bare-year span took "2022 to 2024" out of it and the tail's own year was **lost** (2022-23, 2023-24). The head may carry the label ("FY 2022 to FY 2024-25"), as the bare span's head already could |
| "from 2022-23 to 2025" (fiscal head, bare tail) | **left alone**: 2022-23 and 2025-26, as before | Ambiguous: a bare tail ends the span at 2024-25 under the "2022 to 2025" reading, but names 2025-26 under the "in 2025" reading — and which year "FY 2025" means is exactly the naming question awaiting the operator. Guessing would bind a year the officer may not mean |
| "from 2022-2023 to 2025" (full-form head, bare tail) | left alone: 2022-23, 2023-24, 2024-25, as before | same rule; today's reading happens to be the span (the bare span reads "2023 to 2025" out of the middle) |

### 2.3 An older misreading this also fixes

With both ends in the full stored form, the reader used to read a year nobody
named. "from 2022-2023 to 2024-2025": the bare-year span claimed "2023 to 2024"
out of the middle (→ 2023-24), which blocked both full-form ends, and the
bare-year scan then read 2022 and **2025** → **2022-23, 2023-24, 2025-26**. The
catalogue's own paraphrase "How did Bhubaneswar's expenditure change from
2023-2024 to 2024-2025?" read as 2023-24, 2024-25 and **2025-26** — on a
two-year comparison, whose `$date_range` takes the latest, so it would have
compared against 2025-26. Now: 2023-24 and 2024-25. No replay question used
this form, so it does not appear in §5.

### 2.4 The calendar-window half

`extract_date_window` needs no change: it spans every period it reads (earliest
start to latest end), so "from 2022-23 to 2024-25" already gives 2022-04-01 to
2025-03-31 — exactly the three fiscal years. Pinned
(`test_the_calendar_window_reads_the_span_the_same_way`), and no window changed
over the 695 replay questions. (A bare head in a mixed form starts that window
on 1 January, as "2022 to 2025" always has; no template uses the window, D34.6.)

---

## 3. T1b — the "refusal wins" rule is removed

`_refusal_precedence`, all three cases, and its one call site in `_route_vector`
are gone; the `CLARIFY_SCORE_MARGIN` / `NO_MATCH_LOWER_THRESHOLD` imports only it
used went with it. The D28.5 comment block is replaced by a short note (the
history, the ruling of 2026-09-29, the evidence table). The reranker's decision
is final: a template it picks is served; a refusal it picks goes through
`_serve_query_id` → `_serve_unanswerable` exactly as before; a decline goes to
the ordinary chips, where a refusal among the near misses is still labelled
"Why I can't answer: …" and sends its own question.

**Tests.** `test_refusal_precedence` rewritten: the rule-in-isolation class is
gone; kept unchanged are the retrieval-surface tests and the chip tests (one
docstring updated); new route-level tests: the rule is gone; a reranker pick
stands against a rank-0 refusal three margins ahead (the Barimunda shape); a
no-match with a rank-0 refusal asks, the refusal the first chip and labelled;
a refusal the reranker picks is served (at rank 0 and below it); the ambiguous
zone still asks. **`test_served_refusal` and gates 6 and 8 needed no change.**

**Offline proof** (`WP6g_offline_proof.json` → `t1b_served_refusals`): every
refusal served in the four runs of each package, matched to the reranker calls
for the same question.

| package | refusals served | the reranker's pick | not its pick |
|---|--:|--:|---|
| WP-6e | 18 (16 gold + pilot 1044 twice) | 16 | **pilot 1044**, PLU-005, in both the pilot run and stage 1 (the reranker said `no_match`) |
| WP-6f | 10 (gold) | 10 | none |

This matches the PM's count (WP-6e 1 row, WP-6f 0). The WP-6e router logs agree:
one "refusal precedence: serving PLU-005" line; the WP-6f gold logs have none.

**Live** (§6): 10 refusals served, all 10 the reranker's own pick.

---

## 4. T1c — a missing year, in plain words

### 4.1 The ask, exactly as shown

| missing slot | ask | chips (label = what is sent) |
|---|---|---|
| `$date_range` | **Which year? For example 2024-25.** | 2025-26 · 2024-25 · 2023-24 |
| `$date_range_2`, `$date_range` = 2024-25 | **Compared with which year? For example 2023-24.** | 2025-26 · 2023-24 · 2022-23 |
| `$date_range_2`, `$date_range` = 2025-26 | Compared with which year? For example 2023-24. | 2024-25 · 2023-24 · 2022-23 |
| re-ask after an unusable reply | **I still need a year to answer "Andhrua untied-fund expenditure". Which year? For example 2024-25.** | the same three + 'Ask "…" instead' |

The chips are the three latest years in the validator's registry
(`validator.fiscal_years()`), never hard-coded — a stubbed registry gives other
chips (tested). **My reading of "the example":** the brief says the example is
"the second-latest year in the data" and shows "2023-24" for `$date_range_2`.
Both hold with one rule: **the example is the second chip offered.** With
nothing bound that is the second-latest year (2024-25); for `$date_range_2` the
bound year is left out first, which gives 2023-24 whether 2024-25 or 2025-26 is
bound. It is always a year that exists and never the one already chosen.

### 4.2 A chip tap and a typed reply resume

`pending_resolver.admits_reply` now admits a chip tap on a fiscal-year pending
when the message is exactly what a year chip sends ("2024-25"); a full-question
chip still routes as a new question (tested). Typed replies go through the
ordinary validator: "2024-25", "FY 2024-25", "2024", "last year" (→ 2024-25) and
"from 2022-23 to 2024-25" all resume in tests; the span binds all three years on
a list-capable slot (`serve_pending_answer`). A threshold pending's ask, chips,
re-ask, and its refusal of a year chip are unchanged (tested).

Live (rows 2001–2003):

| row | turn 1 | turn 2 | result |
|---|---|---|---|
| 2001 | "Andhrua untied-fund expenditure" → the ask, chips 2025-26 · 2024-25 · 2023-24 | tap **2024-25** | **EXP-008**, Andhrua GP, untied, 2024-2025: 12 activities, ₹19,36,848 sanctioned, **₹19,05,636 spent** (98.39%) |
| 2002 | "Barimunda planned activities count" → the ask | tap **2025-26** | **PLN-024**, Barimunda, 2025-2026, 7 theme rows (Theme 6: 53 activities …) |
| 2003 | "Andhrua untied-fund expenditure" → the ask | type **"FY 2024-25"** | EXP-008, same answer as 2001 |

The echo read: "How much actual expenditure has been incurred under tied and
untied funds in 2024-2025 (Andhrua GP; untied funds)?"

### 4.3 "date range" → "year", officer-facing only

Slot names are unchanged. Wording changed (via `year_ask.slot_words`, which
returns "year" for `date_range` / `date_range_2` and the old `slot.replace("_",
" ")` for everything else, so no other slot's wording moved):

- the missing-slot ask ("For which date range?" → §4.1);
- "I can answer that for one date range at a time" → "one year at a time";
- "I couldn't find a date range called '…'. Which date range did you mean?" →
  "year";
- the re-ask "I still need a date range …" → "year";
- the scope-widening re-ask "answered one date range at a time — which date
  range?" → "year";
- the "answered: / still needs:" note beside a resumed answer
  (`readable_slot`) → "year";
- the unreachable `date_kind: serial` error "Ask the question without a date
  range." → "without a year".

Not changed: the catalogue's search phrasings "… over a given Date Range?" (four
templates) — the brief freezes phrasings, and they are search-only, never shown.

### 4.4 My decision: a year span now survives a second question

Found while preparing T4, **older than WP-6g**: a year list bound on the first
turn is stored in the pending state joined into one string ("2023-2024,
2024-2025, 2025-2026"), and on resume that string was validated as one value,
which binds only its **latest** year. So "Blocks consistently delayed in GPDP
approvals from 2023-24 to 2025-26", asked for its deadline, answered about
2025-26 alone. It would have defeated brief row 1062 and every span on a
template with a second missing slot. `serve_pending_answer` now reads a
fiscal-year value on a list-capable slot back as its years — the same rule as a
typed span reply (commit `cc72f8c`, test
`test_a_span_on_the_first_turn_survives_another_ask`). **Non-year lists carry
the same weakness** ("water and sanitation", then a missing year, resumes with
"Drinking water, Sanitation" as one string); splitting those on commas is not
safe for every registry value, so it is reported, not changed.

---

## 5. T3 — offline proof

**T3.1** — old vs new reader (the `3374475` `date_phrase.py` against this one)
over every question and second turn of `WP6f_eval1_replay`,
`WP6f_gold_replay_run1`, `WP6f_pilot_replay`, `WP6f_stage1`: **695 questions, 4
change, 2 distinct, 0 in Eval_1, 0 in gold.** Every change is a "from/to" span
between fiscal years; no calendar window changed.

| row | question | old years | new years |
|---|---|---|---|
| pilot 1055 (also stage 1) | How has the beneficiary count under XV Finance Commission in Andhrua changed **from 2022-23 to 2024-25**? | 2022-23, 2024-25 | 2022-23, **2023-24**, 2024-25 |
| pilot 1057 (also stage 1) | Which districts consistently experience delays in GPDP approvals after 30 June 2025 **from 2023-24 to 2025-26**? | 2023-24, 2025-26 | 2023-24, **2024-25**, 2025-26 |

**T3.2 / T3.3** — each re-executed on the sample DuckDB through the router's own
fill-and-serve code, with its recorded template and filters, old years then
new. "Before" reproduces the recorded WP-6f result in both cases.

| row | template | rows before → after | key figure before → after | echo after |
|---|---|---|---|---|
| 1055 | BEN-012 (Andhrua, XV FC) | 0 → 0 | none — `activity_nsap` is empty in the sample | "How has the beneficiary count under 15th Finance Commission (CFC) in Andhrua changed over 2022-2023, 2023-2024 and 2024-2025?" |
| 1057 | PLN-023 (deadline 2025-06-30, top 10) | 9 → 9 | every district 0% late, `years_counted` 2 → **Kandhamal 33.33% (1 of 3 GPs), Cuttack 16.67% (1 of 6)**, the rest 0%, `years_counted` 3 | "Which Districts consistently experience delays in GPDP approvals after the deadline 2025-06-30 in 2023-2024, 2024-2025 and 2025-2026 (top 10)?" |

**The echo.** Neither of these adds the years together — both report per year
(`years_counted`), so no "(… combined)" suffix is added and the three years are
named in the question itself. Where a template does add them, or breaks them
down, the existing wording applies to the span unchanged (run offline, free):

- EXP-008, "Total expenditure from FY 2021-22 to FY 2023-24 in Khordha": "…in
  2021-2022, 2022-2023 and 2023-2024 (Khordha district)? **(2021-2022, 2022-2023
  and 2023-2024 combined)**"
- PLN-024, "How many activities were planned from 2022-23 to 2024-25?": "…in
  2022-2023, 2023-2024 and 2024-2025? **(broken down by year)**"

---

## 6. T4 — live check

27 rows (`WP6g_live_questions.json`), one fresh session each, through
`confirm_spend`, in three parallel parts, every reranker call logged. The three
T1c rows hit a transient "Connection error" (HTTP 500) on their very first call
— the three parts started at the same instant — and were re-run on their own;
the records keep the re-run.

### 6.1 T1c — §4.2

### 6.2 T1b rows

| row | question | ended in | reranker |
|---|---|---|---|
| 2011 | Barimunda planned activities 2025-2026 — count? | **PLN-024**, Barimunda, 2025-2026, 7 theme rows | picked PLN-024 |
| 2012 | Barimunda planned activities 2025-26 count | **PLN-024**, same | picked PLN-024 |
| 315 | Identify districts with delayed GPDP submissions for 2024 to 2026. | **PLN-007**, 9 districts; echo "…in 2024-2025 and 2025-2026 (bottom 10)? (2024-2025 and 2025-2026 combined)" | picked PLN-007 |
| G1233 SBM-SWM-033 · G1421 SCH-004 · G1621 PHY-002 · G1622 PHY-005 · G1712 ALR-006 · G1713 ALR-010 · G1714 ALR-007 · G1715 DQY-005 · G1956 DSS-004 · G1973 BEN-002 | the gold wordings | **each its own refusal** | **each picked by the reranker** |
| G1974 BEN-010 (Odia) | 2024-2025 ରେ ଆନ୍ଧ୍ରୁଆରେ କେତେ ହିତାଧିକାରୀ ପେନସନ ପାଇଛନ୍ତି? | **asks**: "What would you like to know about Andhrua?" with four Andhrua chips | — (the broad-question path; the same outcome as WP-6f) |

The two Barimunda rows answer per theme, not as one figure: the one-number rule
does not catch "…count", which the brief accepts here.

### 6.3 The span rows

| row | question | ended in | years |
|---|---|---|---|
| 1055 | …changed from 2022-23 to 2024-25? | BEN-012, 0 rows | **2022-23, 2023-24, 2024-25** |
| 1057 | …after 30 June 2025 from 2023-24 to 2025-26? | PLN-023, 9 rows (Kandhamal 33.33% first) | **2023-24, 2024-25, 2025-26** |
| 1060 | How many activities were planned from 2022-23 to 2024-25? | asks — first chip "How many activities are planned under each GPDP theme in a gram panchayat in 2024-2025?" (PLN-024), all three "in 2024-2025" | (chips: one year, §7.1) |
| 1061 | Total expenditure from FY 2021-22 to FY 2023-24 in Khordha | asks — first chip "How did the total expenditure of Khordha district change between 2021-2022 and 2023-2024 (as one total)?" | (chips) |
| 1062 | Blocks consistently delayed in GPDP approvals from 2023-24 to 2025-26 → "30 June 2025" | asks on turn 1 — first chip PLN-022 "…after the deadline a deadline in 2025-2026?"; the reply then routes as a new question and asks | (chips: one year) |
| 1063 | Beneficiary trend in Barpali from 2022-23 till 2024-25 | asks — three Barpali beneficiary chips, each "in 2024-2025" | (chips: one year) |
| 1064 | Activities planned 2022-23 – 2024-25 | asks — chips "…in 2024-2025", and "Compare the activities planned and started theme-wise between 2022-2023 and 2024-2025." | (chips) |
| 1065 | Compare expenditure in 2022-23 and 2024-25 *(control)* | **TRD-002**, 7 theme rows | **2022-23, 2024-25** — unchanged |
| 1066 | Planned cost between 2022-23 and 2024-25 *(control)* | asks — chips carry "between 2022-2023 and 2024-2025" | two years — unchanged |
| 1067 | Planned activities in 2023-2025 *(control, D33.7)* | asks — chips "…in 2024-2025" | (chips: one year) |

Graded by the new seventh group (`grade_wp6g`: answered with exactly the
expected years, and the named template where one is named): **1 correct, 7
asked, 0 wrong.** The reader reads every one of these eight as the brief lists
(pinned in `test_date_phrase`, and confirmed on the exact wordings). **Why they
ask:** the reranker returned `no_match` on all seven (the log has each call);
its input is the question text, which the year reader does not touch, and none
had a refusal at search rank 0 or among its near misses, so the old rule would
not have fired either: neither T1 nor T1b bears on it. Row 1062's own shape
(the span kept through the deadline ask) is covered by the §4.4 test.

---

## 7. Found, not fixed

1. **Chips on a multi-year question carry one year.** The chip pre-fill
   (`_extract_fill_values`) calls the slot reader without the list-capable
   slots, so every year slot is read as ONE year (the latest). A span question
   that the reranker declines therefore offers chips "…in 2024-2025", and a tap
   answers about 2024-25 alone. This predates WP-6g and applies equally to "2022
   to 2025" and "2023-2025". It is not a one-line fix: chips mix templates that
   take a list with ones that take one year, and a three-year chip on a one-year
   template would silently bind the latest year. Worth a small package: the
   seven asking rows in §6.3 are where it shows.
2. **Non-year lists through a pause** (§4.4): "water and sanitation" is carried
   as one joined string.
3. **The eight rows' reranker declines** (§6.3): short wordings with no measure
   named ("Activities planned …", "Planned cost …") — a phrasing question, out
   of scope here.
4. **A spaced hyphen or an unspaced dash between two fiscal years** is not a
   link (§2.1) — say if it should be.

---

## 8. Changed test pins

- `test_followup_visibility`: `readable_slot("date_range")` was **"date range"**,
  now **"year"** (T1c, officer-facing).
- `test_refusal_precedence`: rewritten (§3) — the 12 tests of the rule in
  isolation and the three route tests of the old behaviour are replaced by six
  route tests of the new behaviour.
- `test_date_phrase`: **no existing pin asserted the old two-year reading** of a
  "to" span between fiscal years, so none changed; 21 tests added.

---

## 9. Spend

- Live check: `confirm_spend` estimates **~123 calls** for the three parts and
  **~22** for the T1c re-run — a ceiling of ~145, inside the brief's ~150.
  Metered reranker calls: **29**.
- Gates: one model-list call (gate 5, final run).
- T3 and T1b: free (no model, no network).

# WP-6g — "From 2022-23 to 2024-25" means every year in between; the "refusal wins" rule is removed (handoff brief)

**For:** the operator-controlled implementation agent.

**Read first:**
- `Ask/query_router/date_phrase.py` — `_FY_SPAN_RE` ~L127, `_FY_FULL_RE` / `_FY_SHORT_RE` / `_FY_TWO_RE` ~L111–120, `_fiscal_pair` ~L199, `resolve_fiscal_years` ~L265, `_MAX_SPAN_YEARS`, and the calendar-window half (`extract_date_window`) below it;
- `Ask/tests/test_date_phrase.py`;
- `handoffs/WP6f_REPORT.md` §7.2;
- `PROJECT_PLAN.md` D33.7 (the hyphen span "2023-2025" ruling);
- `Ask/query_router/router.py` — `_refusal_precedence` and its D28.5 comment block, its call sites in `_route_vector`, `_serve_unanswerable`, `_reading_chips` (the "Why I can't answer" label);
- `Ask/tests/test_refusal_precedence.py`, `Ask/tests/test_served_refusal.py`, `Ask/refusal_recall.py`, `Ask/prdw_gates.py` gates 6 and 8.

**Sequencing:** WP-6f has landed (`15e29d8`..`3374475`). Build on `3374475`, in a fresh mirror (`C:\dev\odisha-wp6g`). The "found by" switch stays at 4.

**Scope:** three changes — the year reader's "from X to Y" span (T1–T3), the removal of the "refusal wins" rule (T1b), and a plain-words missing-year question with year chips (T1c). **Not in scope:**
- "between X and Y" — **unchanged**, still the two named years; the operator has not ruled on it;
- "X and Y", "X vs Y", "compare X and Y" — unchanged, the two named years, as today;
- the other year-reader gaps the PM found on 2026-09-29 ("FY25" read as no year; "FY 2025" and "March 2025" read as 2025-26) — awaiting the operator's ruling on the fiscal-year naming convention;
- the one-number rule catching "…— count?" (operator: not for now);
- BEN-008, the echo wordings, and everything else WP-6f §7 lists.

## 0. Why this package exists

WP-6f's pilot rows 1055 and 1057 bound `['2022-2023', '2024-2025']` for "from 2022-23 to 2024-25", dropping 2023-24. "Blocks consistently delayed from 2023-24 to 2025-26" therefore counted two years instead of three.

The PM checked the reader offline, 2026-09-29. **The same three-year span reads differently depending only on how the years are written:**

| written as | years read today |
|---|---|
| "from 2022 to 2025" / "for 2022 to 2025" | 2022-23, 2023-24, 2024-25 |
| "in 2022-2025" (D33.7) | 2022-23, 2023-24, 2024-25 |
| **"from 2022-23 to 2024-25"** | **2022-23, 2024-25** |
| **"from FY 2022-23 to FY 2024-25"** | **2022-23, 2024-25** |
| "between 2022-23 and 2024-25" | 2022-23, 2024-25 |
| "compare 2022-23 and 2024-25" | 2022-23, 2024-25 |

**The cause.** `_FY_SPAN_RE` recognises a span only between two **bare** years ("2022 to 2025"). When each end is written as a fiscal year, the fiscal-year patterns claim each end on its own as a single year, and nothing joins them.

**Operator ruling, 2026-09-29:** *"'from X to Y' should be the span."*

### The "refusal wins" rule (D28.5)

`_refusal_precedence` overrides the reranker and serves a **refusal** in three cases:
1. the reranker declines, and search's rank-0 entry is a refusal;
2. the reranker declines, but names a refusal among its near misses;
3. the reranker picks an answerable template, but search's rank-0 entry is a refusal, ahead by more than `CLARIFY_SCORE_MARGIN`.

It was added in WP-4c, when the reranker kept declining genuinely unanswerable questions. Since then it has only misfired:

| package | officer asked | rule served | case |
|---|---|---|---|
| WP-6b | "districts behind on GPDP submission" | PLN-022 | 1 |
| WP-6d | "districts with delayed GPDP submissions" | PLN-023 | 2 |
| WP-6d, WP-6e | "count of planned activities in Attabira" | PLU-005 | 1 |
| tester, 2026-09-29 | "Barimunda planned activities 2025-2026 — count?" | ALR-007 ("ongoing longer than planned duration") | **3** |

The PM traced the last one on the WP-6f code, in the `C:\dev\odisha-wp6f` mirror with `router.rerank` wrapped. **The reranker picked PLN-024, correctly, on both phrasings tried.** Case 3 then replaced that pick with the ALR-007 refusal, which was search's rank 0 for this short wording. "How many activities are planned in Barimunda in 2025-2026?" answers correctly, because ALR-007 is no longer rank 0.

**The evidence that removing it loses nothing**, from the reranker call logs:

| run | refusals chosen by the reranker itself | refusals forced by the rule |
|---|--:|--:|
| WP-6e, all four runs | 16 (all correct) | 1 (pilot 1044, wrong) |
| WP-6f, all four runs | 10 (all correct) | 0 |

**Operator ruling, 2026-09-29:** *"yes remove the rule."* A refusal is served only when the reranker picks it.

### The missing-year question

332 of the 358 templates require `$date_range`, and 5 require `$date_range_2`. When the question names no year, the router asks **"For which date range?"** with **no chips** (`_fill_slots_or_clarify`, the `missing` branch). The tester read that as the bot giving no answer: "Andhrua untied-fund expenditure" and "Barimunda planned activities count" both stop there. If the officer then fails to answer, the re-ask reads "I still need a date range to answer …".

**Operator ruling, 2026-09-29:** ask *"Which year? For example 2024-25"*, with the latest years as chips.

## 1. Hard constraints

- **Only the year reader and the refusal rule change.** No catalogue, SQL, note or phrasing change; `derive_catalog.py --check` and `validate_catalog.py` (358 / 0) stay green untouched. The 15 refusal entries stay exactly as they are, and stay in the search index.
- **Every existing reading in the table above that is not a "to" span stays byte-identical.** That covers single years, hyphen spans, "and", "vs", "compare", "between", relative phrases, and the money and quantity guards. Tests pin it.
- Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched; every paid run through `confirm_spend`; Ask stays on `gpt-5.4-mini`.

## 2. Tasks

### T1 — A span between two fiscal years

In `resolve_fiscal_years`, claimed **before** the single fiscal-year patterns, exactly as `_FY_SPAN_RE` is today:

- **Shape.** `<fiscal year> <link> <fiscal year>`. Each end may be any form the single patterns accept: "2022-2023", "2022-23", "22-23", each with the optional "FY" / "financial year" / "plan year" label. The link is "to", "till", "until", "through" or "thru", or an en / em dash **with spaces around it** ("2022-23 – 2024-25"). A leading "from" is allowed and not required.
- **Meaning.** Both ends are **included**: "2022-23 to 2024-25" gives the start years 2022..2024, which is 2022-23, 2023-24, 2024-25. This matches what "2022 to 2025" already gives.
- **Width.** Allow up to **10** fiscal years; the data holds six. A labelled span is not the figure-range risk that `_MAX_SPAN_YEARS` guards for bare hyphen pairs. Wider than 10, or a tail before its head: leave the text to the existing patterns (today's reading), and **log it**.
- **Mixed forms** ("from 2022-23 to 2025", "from 2022 to 2024-25"). Read as a span when the meaning is unambiguous. Say in the report which you read, which you left alone, and why.
- **Guards.** The money and quantity guards (`_passes_guards`) apply to both ends, as they do today.
- **The calendar-window half** (`extract_date_window`) has no template using it (D34.6). Make it read the same span the same way, so the two halves cannot disagree, or state in the report why that is unnecessary.

### T1b — Remove the "refusal wins" rule

- **Remove** `_refusal_precedence`, all three cases, and every call site. The reranker's decision is final:
  - it picks a template → that template is served;
  - it picks a refusal → the refusal is served through `_serve_unanswerable`, exactly as today;
  - it declines → the ordinary chip path, as today.
- **Keep** the "Why I can't answer: …" label in `_reading_chips`. A refusal the reranker names as a near miss still shows as a labelled chip, and a tap sends the refusal's own question, which the reranker then picks.
- **Replace** the D28.5 comment block with a short note: the rule's history, the operator's ruling of 2026-09-29, and the evidence table above.
- **Tests.** `test_refusal_precedence` is rewritten to assert the new behaviour:
  - a reranker pick stands even when a refusal is search rank 0 and far ahead;
  - a reranker `no_match` with a refusal at rank 0 goes to chips, the refusal labelled;
  - a refusal the reranker picks is served.

  `test_served_refusal` and gates 6 and 8 keep asserting what they assert today — refusals execute no SQL, and the 15 are retrievable — and should need no change. If any do change, list them.
- **Offline proof (free).** From `handoffs/WP6e_rerank_calls.jsonl` and `WP6f_rerank_calls.jsonl` matched to their result files, list every row whose served answer was a refusal the reranker did **not** pick. The PM's count is WP-6e 1 (pilot 1044) and WP-6f 0. Those are the only past rows the removal can change.

### T1c — Ask for a missing year in plain words, with chips

- **The ask.** When `$date_range` is the missing slot: *"Which year? For example 2024-25."* When `$date_range_2` is missing (the 5 two-year comparisons): *"Compared with which year? For example 2023-24."* The example is the second-latest year in the data, so it is always a year that exists.
- **The chips.** The **three latest fiscal years in the data**, newest first, read from the validator's fiscal-year registry, never hard-coded. Each is labelled and sent in short form ("2025-26", "2024-25", "2023-24"). For `$date_range_2`, leave out the year already bound in `$date_range`.
- **A chip tap resumes the paused question.** Today `pending_resolver.admits_reply` admits a chip tap only for a disambiguation or a threshold chip; every other tap routes as a new question. Extend it to a year chip on a fiscal-year pending, the way WP-6c did for threshold figures.
- **Typed replies keep working.** "2024-25", "FY 2024-25", "2024", "last year", and a span such as "from 2022-23 to 2024-25" (T1) must all resume through the ordinary validator. A span binds a list; `$date_range` is list-capable.
- **The re-ask.** `_unusable_reply`'s "I still need a date range to answer …" becomes "I still need a year to answer …", with the same chips.
- **Officer-facing only.** Any other prompt that shows the words "date range" to an officer uses "year" instead. The slot names in the code are unchanged.
- **Tests:**
  - the ask text and chips for a date-range pending and a date-range-2 pending;
  - chips follow the registry: a stubbed registry with other years gives other chips;
  - a chip tap resumes and answers;
  - each typed reply above resumes;
  - a threshold pending's asks and chips are unchanged.

### T2 — Tests

- `tests/test_date_phrase.py` gains the new forms, each end form, every link word, the spaced dash, "from" present and absent, a reversed pair, an 11-year span and a money guard.
- The unchanged forms in §0's table get explicit pins, if they have none today.
- Any existing pin that asserted the old two-year reading of a "to" span between fiscal years is changed. List each one in the report.

### T3 — Offline proof (free)

1. **Every question, every replay.** Run the old and new reader over every question in `handoffs/WP6f_eval1_replay.*`, `WP6f_gold_replay_run1.*`, `WP6f_pilot_replay.*` and `WP6f_stage1.*`. List every question whose years change, with old and new years. **Expected: only "from / to" spans between fiscal years. Stop and report if anything else changes.**
2. **Re-execute every changed row.** Take its recorded served template and bound filters, swap in the new years, and run it against the DuckDB. Report the row count and the key figure before and after. No model calls.
3. **The echo.** Show the echo for each changed row. A span of three years reads "(2022-2023, 2023-2024 and 2024-2025 combined)", or "(broken down by year)" where the question asks for that.

### T4 — Live check, small

Run through `confirm_spend`, about 150 calls:
- **for T1c**, two two-turn rows using the runner's chip-tap turn:
  - "Andhrua untied-fund expenditure" → the new ask with three year chips → tap "2024-25" → EXP-008, Andhrua, untied, 2024-25 (12 activities, ₹19.06 lakh spent);
  - "Barimunda planned activities count" → the new ask → tap "2025-26" → PLN-024, Barimunda, 2025-26;
  - one row where the reply is typed instead: "Andhrua untied-fund expenditure", then "FY 2024-25";
- every changed row from T3.1;
- pilot rows 1055 and 1057;
- **for T1b:** the tester's two phrasings, "Barimunda planned activities 2025-2026 — count?" and "Barimunda planned activities 2025-26 count", added as new rows (expected: PLN-024 answered — per theme is acceptable here, since the one-number rule does not yet catch "…— count?"); Eval_1 row 315's wording; and every gold row that still expects a refusal (the 10 served in WP-6f plus G1974). Those must still end in their refusal, now chosen by the reranker. Report any that end in chips instead;
- **8 new rows** in `handoffs/WP6c_pilot_questions.json` as a seventh standing group:
  - "How many activities were planned from 2022-23 to 2024-25?"
  - "Total expenditure from FY 2021-22 to FY 2023-24 in Khordha"
  - "Blocks consistently delayed in GPDP approvals from 2023-24 to 2025-26" (deadline 30 June 2025)
  - "Beneficiary trend in Barpali from 2022-23 till 2024-25"
  - "Activities planned 2022-23 – 2024-25"
  - "Compare expenditure in 2022-23 and 2024-25" — control: still two years
  - "Planned cost between 2022-23 and 2024-25" — control: still two years
  - "Planned activities in 2023-2025" — control: D33.7, unchanged

No full Eval_1 or gold replay:
- the reader is deterministic and does not affect which template is chosen, only which years are bound, so T3's offline list and re-execution cover every row it can affect;
- the rule removal can only change a row where the rule forced a refusal, and T1b's offline proof lists those.

**If T3.1 lists more than 20 changed Eval_1 or gold rows, or T1b's list finds any WP-6f row, stop and report instead of guessing.**

### T5 — Report

`handoffs/WP6g_REPORT.md`:
- the T3 change list with before / after years, row counts and echoes;
- T1b's offline list, and every refusal served in the live check with whether the reranker chose it;
- the T1c ask exactly as shown, its chips, and the two chip-tap results;
- the live results;
- the mixed-form decisions;
- the changed test pins;
- spend.

## Gate (definition of done)

1. "from X to Y" between fiscal years reads as every year from X to Y inclusive, in every form listed in T1. Every §0 form that is not a "to" span reads exactly as before.
2. The full suite and `prdw_gates.py` are green; catalogue checks untouched (358 / 0).
3. T3's change list holds only "to" spans between fiscal years. Every changed row is re-executed and reported.
4. Pilot 1055 and 1057 bind three years; the eight new rows behave as listed, controls unchanged.
5. `_refusal_precedence` is gone. The two Barimunda phrasings answer on PLN-024. Every refusal served anywhere in the live check was the reranker's own pick. The gold refusal rows still end in their refusal, or any that do not are listed.
6. A missing year is asked as "Which year? For example …" with the three latest years as chips. A chip tap and a typed reply both resume and answer. No officer-facing text says "date range".
7. This brief and the report committed, one commit per task, not pushed.

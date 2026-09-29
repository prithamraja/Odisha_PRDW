# WP-6g — "From 2022-23 to 2024-25" means every year in between (handoff brief)

**For:** the operator-controlled implementation agent.

**Read first:**
- `Ask/query_router/date_phrase.py` — `_FY_SPAN_RE` ~L127, `_FY_FULL_RE` / `_FY_SHORT_RE` / `_FY_TWO_RE` ~L111–120, `_fiscal_pair` ~L199, `resolve_fiscal_years` ~L265, `_MAX_SPAN_YEARS`, and the calendar-window half (`extract_date_window`) below it;
- `Ask/tests/test_date_phrase.py`;
- `handoffs/WP6f_REPORT.md` §7.2;
- `PROJECT_PLAN.md` D33.7 (the hyphen span "2023-2025" ruling).

**Sequencing:** WP-6f has landed (`15e29d8`..`3374475`). Build on `3374475`, in a fresh mirror (`C:\dev\odisha-wp6g`). The "found by" switch stays at 4.

**Scope:** one change to the year reader. **Not in scope:**
- "between X and Y" — **unchanged**, still the two named years; the operator has not ruled on it;
- "X and Y", "X vs Y", "compare X and Y" — unchanged, the two named years, as today;
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

## 1. Hard constraints

- **Only the year reader changes.** No catalogue, SQL, note or phrasing change; `derive_catalog.py --check` and `validate_catalog.py` (358 / 0) stay green untouched.
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

### T2 — Tests

- `tests/test_date_phrase.py` gains the new forms, each end form, every link word, the spaced dash, "from" present and absent, a reversed pair, an 11-year span and a money guard.
- The unchanged forms in §0's table get explicit pins, if they have none today.
- Any existing pin that asserted the old two-year reading of a "to" span between fiscal years is changed. List each one in the report.

### T3 — Offline proof (free)

1. **Every question, every replay.** Run the old and new reader over every question in `handoffs/WP6f_eval1_replay.*`, `WP6f_gold_replay_run1.*`, `WP6f_pilot_replay.*` and `WP6f_stage1.*`. List every question whose years change, with old and new years. **Expected: only "from / to" spans between fiscal years. Stop and report if anything else changes.**
2. **Re-execute every changed row.** Take its recorded served template and bound filters, swap in the new years, and run it against the DuckDB. Report the row count and the key figure before and after. No model calls.
3. **The echo.** Show the echo for each changed row. A span of three years reads "(2022-2023, 2023-2024 and 2024-2025 combined)", or "(broken down by year)" where the question asks for that.

### T4 — Live check, small

Run through `confirm_spend`, about 60 calls:
- every changed row from T3.1;
- pilot rows 1055 and 1057;
- **8 new rows** in `handoffs/WP6c_pilot_questions.json` as a seventh standing group:
  - "How many activities were planned from 2022-23 to 2024-25?"
  - "Total expenditure from FY 2021-22 to FY 2023-24 in Khordha"
  - "Blocks consistently delayed in GPDP approvals from 2023-24 to 2025-26" (deadline 30 June 2025)
  - "Beneficiary trend in Barpali from 2022-23 till 2024-25"
  - "Activities planned 2022-23 – 2024-25"
  - "Compare expenditure in 2022-23 and 2024-25" — control: still two years
  - "Planned cost between 2022-23 and 2024-25" — control: still two years
  - "Planned activities in 2023-2025" — control: D33.7, unchanged

No full Eval_1 or gold replay. The reader is deterministic and does not affect which template is chosen, only which years are bound, so T3's offline list and re-execution cover every row it can affect. **If T3.1 lists more than 20 changed Eval_1 or gold rows, stop and report instead of guessing.**

### T5 — Report

`handoffs/WP6g_REPORT.md`:
- the T3 change list with before / after years, row counts and echoes;
- the live results;
- the mixed-form decisions;
- the changed test pins;
- spend.

## Gate (definition of done)

1. "from X to Y" between fiscal years reads as every year from X to Y inclusive, in every form listed in T1. Every §0 form that is not a "to" span reads exactly as before.
2. The full suite and `prdw_gates.py` are green; catalogue checks untouched (358 / 0).
3. T3's change list holds only "to" spans between fiscal years. Every changed row is re-executed and reported.
4. Pilot 1055 and 1057 bind three years; the eight new rows behave as listed, controls unchanged.
5. This brief and the report committed, one commit per task, not pushed.

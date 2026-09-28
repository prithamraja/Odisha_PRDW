# WP-6c — Two pilot-feedback fixes: threshold replies and the fund split by scheme: REPORT

> ## Where everything is
>
> ```
> Ask/query_router/threshold_reply.py        T1 — the reply reader, the unit-worded ask, the direction check
> Ask/query_router/pending_resolver.py       T1 — numeric pendings; admits_reply (what main.py resumes)
> Ask/query_router/entity_extractor.py       T1 — read_figure, the one model call for number words
> Ask/query_router/router.py                 T1 — the ask + first-turn direction check; T2 — _rehome_and_guard
> Ask/tools/derive_catalog.py                T1 — threshold direction/unit derived onto the slots
> Ask/query_router/subject_reader.py         T2 — VOCABULARY_GUARDED, written_values
> Ask/tools/migrations/m5_scheme_breakdown.py T2 — M5 (operator ruling, see §3.2)
> Ask/prdw_gates.py                          T1 — gate 9 (j): unit and direction on every threshold slot
> Ask/run_custom_eval.py, Ask/grade_eval1.py T3 — two-turn rows, retrieval trace, the pilot group
> Ask/tests/test_wp6c_pilot_feedback.py      40 tests, grouped by task
> handoffs/WP6c_pilot_questions.json         T3 — the 22 pilot rows
> handoffs/WP6c_pilot_replay.csv/.jsonl      T3.1 — the pilot run, graded
> handoffs/WP6c_eval1_replay.csv/.jsonl      T3.2 — the Eval_1 replay, graded
> ```
>
> **Committed, not pushed**, one commit per task: `414930a` T1, `a271c8f` T2,
> and T3's commit carrying this report, the brief, the question file and both
> graded runs. Left for the operator as before: the PM's `handoffs/PROJECT_PLAN.md`
> edit, the untracked baseline `handoffs/WP6b_eval1_replay_notes_off.csv`, and
> `Ask/bench/`.
>
> Re-run from a local mirror (`C:\dev\odisha-wp6c`, a plain copy of `Ask/`):
> ```
> cd Ask && python prdw_gates.py --yes --repo <the Drive repo>
> cd Ask && python run_custom_eval.py --questions ../handoffs/WP6c_pilot_questions.json --out pilot.jsonl --yes
> cd Ask && python grade_eval1.py pilot.jsonl
> cd Ask && python grade_eval1.py eval1.jsonl --baseline ../handoffs/WP6b_eval1_replay_notes_off.csv
> ```

---

## 0. For the PM — what this package did

1. **A threshold reply is read, not re-asked.** "above ₹20,000", "activities
   above 20,000", "more than 20,000 rupees", "the threshold is 20000",
   "20,000 and above" all answer with ₹20,000 bound; "twenty thousand" and
   "two and a half lakh" answer through one model call. The loop is gone: a
   reply with a figure in it never falls through to a new question.
2. **A reply the other way round is asked about, never answered.** "under
   2 lakhs" to an "above" question gets *"This question looks for results above
   a planned cost. Did you mean above ₹2 lakhs, or do you want the ones below
   ₹2 lakhs?"* with those two chips. The SQL operator is never flipped.
3. **The ask names its unit**: "Above what planned cost? For example ₹50,000
   or 1 lakh." / "Below what percentage?" / "How many days?" / "At least how
   many activities?", each with three example chips that resume on a tap.
4. **A scheme is never a tied/untied value.** A scheme the extractor puts in
   `$tied_untied` moves to `$scheme`; a tied/untied value the question never
   says is dropped. The "Tied / Untied / Other" chip set appeared **0 times** in
   either run.
5. **The four tied/untied questions can now answer per scheme** — by operator
   ruling the same day, a scheme-only breakdown was added to their SQL (M5,
   §3.2). This lifts the brief's "no SQL change" for those four statements only.

**The measured result.** Pilot rows: **all 12 threshold rows behave as
designed** (10 answer with the right figure, 2 ask `direction_mismatch`); **6 of
10 fund-split rows answer per scheme** — the other 4 are asked about by the
reranker before any slot is read (§4.1), so gate item 2 is **partly met**.
Eval_1: **290 correct / 10 asked with the right chip / 0 / 2 wrong** of 302, against
292 / 6 / 1 / 3 — the target (no group loses more than one row, incorrect ≤ 3)
is met. The vocabulary guard fired once in it, and on an invented filter.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | Gates green incl. unit/direction; `derive_catalog.py --check` green | **PASS** — 9/9 with `--yes` (live model list), 715 tests; gate 9 (j) "unit and direction on all 15 threshold slots"; crowding 32.2 / 146 (unchanged) |
| 2 | Pilot rows: thresholds answer or `direction_mismatch` exactly where due; no Tied/Untied/Other chips; fund-split rows answer per scheme | **PARTLY** — thresholds 12/12; Tied/Untied/Other chips 0 in both runs; fund split **6/10** answer per scheme, 4 ask (reranker no-match, §4.1) |
| 3 | Eval_1 meets T3.2; CSV committed; #1423 / #1402 / #1522 as in T2's proof | **PASS** — 290 / 10 / 0 / 2 of 302 (baseline 292 / 6 / 1 / 3); no group lost more than one row; incorrect 2 ≤ 3; `handoffs/WP6c_eval1_replay.csv` beside the baseline. #1423 / #1402 / #1522 pinned offline (§3.3) — they are gold rows, and the gold replay stays with D34.2 |
| 4 | No catalogue SQL changed, no migration; `validate_catalog.py` 343 / 0 | **CHANGED BY RULING** — M5 changes four statements (operator, 2026-09-28, §3.2); `validate_catalog.py` 343 templates, 0 binding / 0 execution / 0 row-count problems; every Test Report count holds |
| 5 | Sector, Sankalp, ranking-floor default untouched; brief and report committed, one commit per task, not pushed | **PASS** |

---

## 2. T1 — threshold replies

### 2.1 What the catalogue now says about each threshold

`tools/derive_catalog.py` reads each threshold slot's comparison operator and
what it compares, and writes `direction` and `unit` onto the slot declaration.
Only the 15 slot lines changed; no SQL text. `--check` pins them, a threshold
the SQL does not state plainly breaks the contract (`HAND_THRESHOLD_META`), and
gate 9 (j) asserts all 15 carry both.

| direction | unit | templates |
|---|---|---|
| above | rupees | EXP-033, IMP-013 |
| above | activities | IMP-009, IMP-019, IMP-020 |
| above | days | ALR-001, ALR-008 |
| above | percent | ALR-003 (read by hand: `> v.total_cost * (1 + $threshold / 100.0)`) |
| below | rupees | PLU-006, PLU-009 |
| below | activities | PLN-045, PLN-069 |
| below | percent | ALR-011, DSS-001, DSS-005 |

Exactly the brief's list.

### 2.2 How a reply is read

1. **Deterministic.** `router.amount_from_text`, then one plain number (for
   percent / days / counts), with fiscal years masked out ("above 1 lakh for
   2024-25"). The direction is read **beside the figure only** — the last
   direction word before it, with only filler words ("a planned cost of ₹")
   in between, or "and above" / "or more" / "+" after it. That keeps "under
   SFC with a cost of 20000" from reading as *below*. Nothing else is stripped;
   the figure goes through `parse_amount` and the range check as before.
2. **Model, only when there is no digit but there is a number word.**
   `entity_extractor.read_figure`: one `gpt-5.4-mini` call, metered as
   `threshold_reply`, returning the figure in digits with the officer's unit
   word kept ("2.5 lakh", never "250000") and the direction. Its output goes
   through the same validation.
3. **Direction check.** Matches or absent → bind and answer. Contradicts →
   `direction_mismatch`, two chips: chip 1 sends the bare figure and resumes the
   paused question; chip 2 sends the paused question the other way round as a
   new question ("Which low-value activities have no expenditure in 2024-25
   (below ₹2 lakhs)?").

### 2.3 Never losing the paused question

`pending_resolver.admits_reply` (what `main.py` now calls) reads a typed reply
against a threshold pause whenever it has a digit or a number word, however
long; a chip tap is read when it is a bare figure (our example chips, chip 1).
For a numeric pause: a reply with a figure resumes or asks — it never falls
through; a figure that fails validation re-asks in the unit's words; a reply
with no number re-asks once with the unit sentence, the example chips and an
"Ask … instead" chip, and a second such reply, or one of **six or more** words,
falls through. The categorical one-shot is unchanged.

### 2.4 Three things the brief did not say, decided here

* **The first turn is checked too.** "Which activities under 2 lakhs have no
  expenditure?" retrieved onto EXP-033 had its figure prefilled by the rupee
  reader and was answered *above* 2 lakh — the same defect on the question
  path, and chip 2's new question would have walked straight into it. The
  vector path now runs the same check (`check_direction=True`); a resumed reply
  is not re-checked against the original question.
* **On the first turn, there is only chip 1.** The officer's own question
  already says "under" and was retrieved onto this statement, so a chip 2
  would resend it and come straight back. The prompt says so: *"The closest
  question I have looks for results above a planned cost, not below. Did you
  mean above ₹2 lakhs?"*
* **"Six or more words" falls through, not "more than six".** The brief's own
  proof case "hello there how are you today" is six words, and its T1c text
  says "more than six"; the proof was followed.

---

## 3. T2 — a scheme is never a tied/untied value

### 3.1 The three layers

`router._rehome_and_guard`, right after extraction and before any validation:

1. **Re-home.** An extractor `$tied_untied` value that does not resolve as
   tied/untied but does as a scheme moves to `$scheme`, merging with anything
   there (deduplicated by resolved value). Logged `rehomed tied_untied→scheme`.
2. **Per-scheme comparison.** A scheme list then takes the breakdown by the
   WP-6 T4 rule (`comparison_breakdown`), echo "(broken down by scheme)", and
   the `unbound_subject` guard sees `$scheme` bound. **This needed M5** (§3.2).
3. **The vocabulary guard.** What is left of an extractor `$tied_untied` value
   stands only if the question says it in tied/untied words (a registry value
   or an `_TIED_UNTIED_ALIASES` key, via `subject_reader.written_values`);
   otherwise it is dropped and logged. Table-driven
   (`subject_reader.VOCABULARY_GUARDED`) so D34.4's plan-type guard can join;
   only tied/untied is wired.

### 3.2 M5 — the ruling, and why scheme only

The brief's layer 2 assumed BUD-003, BUD-005, EXP-008 and FND-001 could switch
to one row per scheme. They could not: M2 had skipped them (window functions,
FND-001's two-column GROUP BY), so they had no `$group_by`, and the brief
forbade SQL changes. Put to the operator, who ruled on 2026-09-28 to **change
the SQL**, and — after the trade-off was explained — to allow **only
`scheme`**: any other breakdown would replace the tied/untied column these four
questions exist to show ("district-wise tied and untied" would come back as
district totals with no split).

`tools/migrations/m5_scheme_breakdown.py` replaces each statement's first
column with `CASE $group_by WHEN 'scheme' THEN v.scheme_name ELSE v.tied_untied
-- absent: tied_untied END AS group_label`, and blanks FND-001's fund component
when a breakdown is chosen. It executes each statement before writing: absent
gives the Test Report's 3 / 3 / 3 / 5 rows, `'scheme'` gives 2 each. The Test
Report records `group_by: None` for the four. `rerank_context` was regenerated —
four lines, which now say "one row per scheme on request" (a statement offering
one breakdown names it rather than promising "other breakdowns").

### 3.3 The brief's proof, offline

On BUD-005 with the extractor stubbed: `{"tied_untied": "Own Funds"}` answers
with `scheme = Own Funds`, no clarification; `{"tied_untied": ["SFC", "Own
Funds"]}` answers one row per scheme on all four statements, echo "(broken down
by scheme)"; BUD-002 with `{"scheme": [...]}` unchanged; "tied" in the question
still binds Tied; `Tied` on a question with no tied/untied word is dropped and
logged; gold #1423 answers on SCH-002 and BUD-005; #1402 / #1522 answer the
split with no scheme breakdown. "district-wise tied and untied" keeps its
tied/untied table.

---

## 4. T3.1 — the pilot rows (`handoffs/WP6c_pilot_questions.json`)

Graded by `grade_eval1.py`'s fourth standing group (rows from 1001): a fund-split
row is correct when answered per scheme (a scheme column) or, for a one-scheme
question, with that scheme bound; a threshold row needs turn 1 to ask for the
threshold and turn 2 to answer the expected template with the expected figure,
or to ask `direction_mismatch` where the reply contradicts.

### 4.1 Fund split by scheme — 6 of 10

| # | question | rank 0 (retrieval) | outcome |
|---|---|---|---|
| 1001 | fund breakdown by SFC, CFC and own funds 2024-25 | SCH-011 (other) | **BUD-002** (per-source), the three schemes bound — correct |
| 1002 | how much came from Own Funds vs SFC in Khordha in 2024-25 | SCH-009 (other) | asked: reranker no-match; chips SCH-010 / FND-004 / FND-010 (per scheme) |
| 1003 | scheme-wise sanctioned amount 2024-25 | SAN-013 (per-source) | **SAN-013**, per sanctioned scheme — correct |
| 1004 | funding source wise expenditure 2025-26 | EXP-007 (per-source) | **EXP-006** (per-source) — correct |
| 1005 | split the sanctioned funds into SFC and Own Funds for 2024-25 | SAN-013 (per-source) | asked: reranker no-match; chips BUD-003 / BUD-004 / FND-005 |
| 1006 | how much was funded from Own Funds in Andhrua 2024-25 | BUD-001 (other) | **BUD-002**, Andhrua + Own Funds bound — correct (0 rows: no Own Funds activity there that year) |
| 1007 | What share of the sanctioned budget came from SFC and 15th Finance Commission in 2024-25? | SCH-011 (other) | asked: reranker no-match; chips BUD-003 / FND-001 / BUD-004 |
| 1008 | Show expenditure under SFC and CFC funds for 2024-25 | SCH-011 (other) | **EXP-006**, both schemes bound — correct |
| 1009 | How much of the 2024-25 sanctioned amount is from the State Finance Commission? | SCH-011 (other) | asked: reranker no-match; chips BUD-003 / BUD-002 / BUD-004 |
| 1010 | Compare Own Funds and SFC spending in 2023-24 | SCH-008 (other) | **SCH-008**, the two-scheme comparison — correct |

**What this says.** Retrieval's rank 0 is a per-funding-source template in 3
rows, SCH-011 ("district-wise activity count under a scheme") in 4, and SCH-009,
SCH-008, BUD-001 once each — never a tied/untied one. No row was answered with the tied/untied table, and no row
reached the re-home: the four misses are the reranker declining all 30
candidates ("I couldn't match that exactly"), which happens **before any slot
is read**, so T2 cannot reach them. Three of the four are *sanctioned*-amount
questions naming one or two schemes (1005, 1007, 1009); the catalogue has no
"sanctioned amount per scheme" statement other than SAN-013 (three-level) and,
since M5, BUD-003 with the scheme breakdown — the reranker chose neither.
Tapping the BUD-003 chip in 1005/1007/1009 routes the chip's own wording, which
does not carry the schemes. **Not fixed here** (paraphrases or a reranker note
are outside this package); see §8.

### 4.2 Threshold replies — 12 of 12

Turn 1 asked for the threshold in its own unit on all 12 rows.

| # | question → reply | outcome |
|---|---|---|
| 1011 | EXP-033 → "above ₹20,000" | EXP-033, 20000 |
| 1012 | EXP-033 → "activities above 20,000" | EXP-033, 20000 |
| 1013 | IMP-013 → "more than 20,000 rupees" | IMP-013, 20000 |
| 1014 | PLU-006 → "the threshold is 50000" | PLU-006, 50000 |
| 1015 | IMP-013 → "20,000 and above" | IMP-013, 20000 |
| 1016 | EXP-033 → "under 2 lakhs" | `direction_mismatch`: Above ₹2 lakhs / Below ₹2 lakhs instead |
| 1017 | PLU-006 → "above 2 lakh" | `direction_mismatch`: Below ₹2 lakh / Above ₹2 lakh instead |
| 1018 | EXP-033 → "twenty thousand" | EXP-033, 20000 (model read "20 thousand") |
| 1019 | PLU-006 → "two and a half lakh" | PLU-006, 250000 (model read "2.5 lakh") |
| 1020 | EXP-033 → "1 lakh" | EXP-033, 100000 |
| 1021 | PLU-006 → "₹50,000" | PLU-006, 50000 |
| 1022 | IMP-013 → "5 lakh" | IMP-013, 500000 |

**Model-fallback calls (T1 step 2): 2 in the pilot run**, both correct:
`'twenty thousand' -> {'amount': '20 thousand', 'direction': None}`,
`'two and a half lakh' -> {'amount': '2.5 lakh', 'direction': None}`.
In the Eval_1 replay: **0** (it has no threshold replies).

---

## 5. T3.2 — the Eval_1 replay

314 rows through `run_custom_eval.py` in ten parallel processes on the final
T2 state (0 errors), graded by `grade_eval1.py` unchanged, diffed against
`handoffs/WP6b_eval1_replay_notes_off.csv`.

| outcome | baseline (notes off) | WP-6c | share of 302 |
|---|--:|--:|--:|
| correct | 292 | **290** | 96.0% |
| asked, right template offered | 6 | 10 | 3.3% |
| asked, right template NOT offered | 1 | **0** | 0.0% |
| incorrect | 3 | **2** | 0.7% |
| defective row (Eval_1's own) | 12 | 12 | |

**Against T3.2: met.** No group lost more than one row (five groups lost one
each); incorrect 2 ≤ 3.

**The 12 rows that moved:**

| row | baseline → now | served / chips | reading |
|---|---|---|---|
| 13, 14, 188 | correct → asked | reranker no-match; PLU-008 on the chips | zero-cost group |
| 118 | correct → asked | no-match; PLN-002 on the chips | supplementary plans |
| 145 | correct → asked | no-match; PLN-024 on the chips | activities in main GPDPs |
| 173 | correct → asked | no-match; BUD-006 on the chips | total estimated cost |
| 212 | correct → **wrong** | PLN-038 (five-year trend) for "planned activities for each theme for 2022 to 2023" | reranker pick |
| 12, 187 | asked → correct | DQY-007, PLU-008 | zero-cost group |
| 254 | wrong → correct | PLN-014 | the baseline's new wrong answer, recovered |
| 281 | wrong → correct | asks "sector" as ruled | the baseline's other new wrong answer, recovered |
| 351 | clarify-incorrect → correct | TRD-003 | five-year utilisation |

**None of these templates has a threshold slot or a scheme / tied-untied
reading in play**, and the one change WP-6c made to the reranker's input is four
description lines on BUD-003, BUD-005, EXP-008 and FND-001. The movement is the
answer↔ask flipping D33 disclosed for Eval_1 (one run, so it cannot be
separated from noise row by row; the brief allows one).

**The rows that bind tied/untied are the tied-spend group, exactly** — eleven of
its twelve rows (40–52; row 42 asks) bind Tied in both runs. The baseline also bound `tied_untied = Untied` on
**row 190** ("Identify Gram Panchayats with cost-free planned activities"),
graded correct there although the answer was filtered to untied activities; this
run that filter is gone on 190, and the guard dropped the same invention on
row 197 (§6).

**Clarifications by reason:** ambiguous_templates 13, ambiguous_term 7 (the
"sector" group, as ruled), no_match 1; **unbound_subject 0**; **Tied / Untied /
Other chip sets 0**.

---

## 6. Every guard line, both runs

Every `rehomed` and `dropped` line the two runs logged (`*.router.log`
beside each result file):

| run | line |
|---|---|
| Eval_1 | `dropped tied_untied=['Untied']: the question does not say it in tied/untied words query='Identify Gram Panchayats with cost-free planned activities for 2022 to 2023.'` (row 197) |
| pilot | — none |

* **Re-home (`rehomed tied_untied→scheme`): 0 in both runs.** On the pilot's
  fund-split rows the reranker either chose a per-funding-source statement,
  where the extractor put the schemes in `$scheme` itself, or asked before
  extraction. The path is proved offline (§3.3) and not yet seen live.
* **Vocabulary guard: 1**, above — an invented filter, which is the case it was
  built for. It did not fire on any of the eleven tied-spend rows that bind Tied.
* **T2b's reader drop ("the subject reader already bound that phrase"): 0.**
* **`direction_mismatch`: 2** (pilot rows 1016, 1017) — exactly the two rows
  written to contradict.
* **Model fallback: 2** (pilot rows 1018, 1019), both read correctly (§4.2).

---

## 7. Spend

| | calls |
|---|--:|
| catalogue index rebuild (`refusal_recall.py --yes`; M5 changed four entries) | ~15 |
| `recall_eval.py --yes` (recall@30 96.6%, crowding 32.2 / 146 — unchanged) | ~15 |
| gate 5 live model list, twice | 2 |
| pilot rows: 22 × (embed + rerank + extraction), 4 chip pre-fills, 2 model reads | ~72 |
| Eval_1: 307 routed rows × 3 (the 7 "sector" rows ask before retrieval), 14 chip pre-fills | ~935 |
| **total** | **~1,040**, all through `confirm_spend` |

The runner has no meter, so the two replay lines are counted from the records,
as WP-6b did.

---

## 8. What the next package should know

1. **The fund-split misses are the reranker's, not the slots'.** Four pilot
   questions naming schemes and a *sanctioned* amount were declined outright.
   The cheapest next step is two or three hand paraphrases on BUD-003
   ("split the sanctioned funds into SFC and Own Funds", "how much of the
   sanctioned amount came from SFC") — measured by re-running the 22 pilot
   rows (~70 calls). Not done here: the operator scoped this package to the two
   changes.
2. **The echo shows raw slot values in brackets** — "(scheme)", "(10)",
   "(20000)" — wherever a slot has no placeholder in the question text (e.g.
   "…in 2024-2025 (5TH STATE FINANCE COMMISSION and Own Funds) (scheme)?
   (broken down by scheme)"). This predates WP-6c (the WP-6b replay shows
   "(gp)" the same way); it reads badly to an officer.
3. **The first-turn direction check reads only a figure the question states.**
   "high-value" / "low-cost" with no figure is not a direction and is not read.
4. **D34 conditions are still owed** (PLN-007 paraphrase, plan-type invention
   guard — the table in `subject_reader.VOCABULARY_GUARDED` is ready for it —
   and the HEAD gold replay).
5. **Migration numbering: M5 is taken.** `tools/migrations/m5_scheme_breakdown.py`
   is WP-6c's (committed in `a271c8f`). The WP-6d brief drafted the same
   afternoon (`handoffs/WP6d_ranking_floor.md`) calls its ranking-floor
   migration "m5"; it should be M6. WP-6d also touches IMP-009 / IMP-019 /
   IMP-020, which WP-6c now asks for as "At least how many activities?" — if
   they stop asking, that sentence simply stops being reached.

---

## 9. Compliance with the brief

| constraint | status |
|---|---|
| No catalogue SQL change, no migration | **Lifted by operator ruling for four statements** (M5, §3.2); nothing else |
| `derive_catalog.py` gains derived slot metadata only; `--check` green | Yes — `unit`/`direction` on 15 slots; plus the one-breakdown wording in `rerank_context` |
| Test Report row counts hold | Yes — gate 2, and M5 checks its four before writing |
| Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched | Yes — everything ran from `C:\dev\odisha-wp6c` |
| Every paid run through `confirm_spend` | Yes — `run_custom_eval.py` estimate now counts second turns |
| Retrieval thresholds untouched; Ask on `gpt-5.4-mini` | Yes |
| No file serving "sector" or "Sankalp" changed | Yes — `sector_clarification`, `_THEME_ALIASES`, `EXPECTED_TO_ASK`, the PLN-049 / PLN-032 notes untouched |
| Ranking-floor default (IMP-009/019/020) untouched | Yes — only asked in plainer words ("At least how many activities?") |

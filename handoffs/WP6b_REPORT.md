# WP-6b — Eval_1 fixes and the D33 clean-up: REPORT

> ## Where everything is
>
> ```
> Ask/query_router/subject_reader.py        T2 — the subject reader, and what the guard reads
> Ask/query_router/router.py                T2 prefill + unbound_subject guard; T3 echo; T2b
> Ask/query_router/breakdown.py             T3 — which list takes the breakdown
> Ask/query_router/echo.py, Ask/main.py     T4 — a count of nothing renders 0
> Ask/tools/derive_catalog.py               T5 — the _DISAMBIGUATION notes (rerank_context.py regenerated)
> Ask/query_router/date_phrase.py           T1 — the hyphen span
> Ask/refusal_recall.py, Ask/recall_eval.py T1 — the crowding line in gate 8
> Ask/grade_eval1.py                        T6 — the Eval_1 grader, with --baseline
> Ask/run_custom_eval.py                    T6 — the runner, now spend-guarded
> Ask/tests/test_wp6b_eval1_fixes.py        26 tests, grouped by task
> handoffs/WP6b_eval1_replay.csv/.jsonl     T7 — the Eval_1 replay, graded (PM's CSV shape)
> handoffs/WP6b_gold_replay_run1.csv/.jsonl T7 — the gold replay, one run, beside WP-6's three verdicts
> handoffs/archive/Eval_1.xlsx              T1 — archived, with its README line
> ```
>
> **Committed, not pushed** — one commit per task, as for WP-6: `65419ba` T1,
> `d2591c3` T2, `ce193d7` T3, `c61cf2f` T4, `916fe2d` T5, `751995f` T6,
> `54c0344` T5b (the brief's conditional paraphrases), the T2b fix (§8.3), and
> T7's commit carrying this report. Left for the operator, as with WP-6: the
> PM's `handoffs/PROJECT_PLAN.md` edit and this package's brief.
>
> Re-run anything, from a local mirror (bootstrap §6):
> ```
> cd Ask && python prdw_gates.py --yes --repo <the Drive repo>
> cd Ask && python run_custom_eval.py --questions ../handoffs/WP6_eval1_questions.json --out eval1.jsonl --yes
> cd Ask && python grade_eval1.py eval1.jsonl --baseline ../handoffs/WP6b_eval1_replay.csv
> cd Ask && python run_consistency_eval.py --runs 3 --tag <tag> --yes
> ```

---

## 0. For the PM — what this package did, in six lines

1. **A subject the officer names now binds, or the bot asks.** "Road
   construction" reaches the Roads focus area, read straight off the question
   the way the year is; a named subject still unbound after extraction is asked
   about, never answered as if it had not been said.
2. **Water vs sanitation over two years comes back as water and sanitation**,
   each summed over the two years, and the answer says the years were added.
3. **A count of nothing says 0**, not "No records matched". A list of nothing
   still says nothing matched.
4. **The reranker is told the distinctions the replay caught it missing.**
5. **Eval_1 is a standing regression**: one command replays it, one grades it
   exactly the way the PM did, and prints what moved.
6. **The D33 clean-up is done**: "2023-2025" is 2023-24 and 2024-25, crowding is
   a gate line, `Eval_1.xlsx` is archived, and the WP-6 report is in order.

**The measured result.** On Eval_1's 302 gradable rows: **289 correct (from
201), 3 incorrect (from 28), 4 asked without the right template (from 15), 6
asked with it (from 58).** The road group went from 0 to 10 correct of 11, with
no wrong answer left in it. On the gold set, one replay (not three — see §8.2)
behaved correctly on 89.5%, against WP-6's 89.8–90.9%, and it found one
regression this package caused, which is fixed (§8.3).

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | Gates green, with the crowding line and the updated date pins | **PASS** — 9/9 with the live model check (`--yes`), on `54c0344`; the suite again after the T2b fix, 674 tests |
| 2 | Eval_1 replay meets every T7.1 target; CSV committed beside the baseline | **PARTLY** — 3 of 6 targets met cleanly, 3 missed narrowly (§8.1); CSV committed |
| 3 | Gold replay at or above WP-6, no majority-of-three regression | **NOT MEASURED AS SPECIFIED** — one replay, not three (operator: no further runs); 89.5% vs 89.8–90.9%, one caused regression found and fixed (§8.2) |
| 4 | No catalogue SQL changed; `derive_catalog.py --check` green | **PASS** — two hand paraphrases added (T5's own conditional step), no SQL |
| 5 | `Eval_1.xlsx` archived; WP-6 report reordered | **PASS** |

**What the replays measured, exactly.** Both replays ran on the T1–T6 state
(`751995f`). Two later changes are pinned by tests and gates but **not by any
replay**: T5b (`54c0344`: the two paraphrases T5's own condition called for,
and three sharpened notes) and the T2b fix. A second Eval_1 replay and a 3×
gold replay on the final state were started and stopped on the operator's
instruction.

---

## 2. T1 — the D33 clean-up

**The hyphen span (D33.7).** `_fiscal_pair` now returns the fiscal years a pair
names rather than one: `2024-2025` is still one year; `2023-2025` is 2023-24 and
2024-25, exactly what "2023 to 2025" already read as after WP-6 T4. Still
refused, and left to the bare-year scan as before: a tail before its head
(`2025-2023`), a span wider than five years (`2019-2025`), and any wider pair
with a two-digit head — "10-15 activities" is a range of figures, not 2010 to
2015. The short form follows the long one (`2023-25` is the same span).

| test | was | is |
|---|---|---|
| `resolve_fiscal_years("…2023-2025")` | 2023-24, 2025-26 | 2023-24, 2024-25 — and equal to the "2023 to 2025" reading |
| `fiscal_year_window("2023-2025")` | None | 1 Apr 2023 – 31 Mar 2025 |
| `extract_date_window("approvals 2023-2025")` | 1 Jan 2023 – 31 Dec 2025 | 1 Apr 2023 – 31 Mar 2025 |

Five pins were added: the direction (a span runs head to tail−1), a consecutive
pair is still one year, the short form, the two fall-through cases, and the
two-digit guard.

> **One inconsistency left as it was, and named.** `extract_date_window` is the
> CALENDAR-window reader, for a genuine date column only (no template uses it:
> `date_filter` is unset on all 343). There "2023 to 2025" still reads as 1 Jan
> 2023 – 31 Dec 2025, while "2023-2025" now reads as the two fiscal years. The
> fiscal-year SLOT — what every answer binds — reads both spellings identically.

**Crowding as a gate line (D33.9).** Gate 8 now prints, beneath the refusal
ranks, with no API call (from the gold-topic vectors `recall_eval.py` now
caches), reported and never asserted:

```
crowding (reported, not asserted): mean 32.2, max 146 raw vectors beyond 30 to
reach 30 distinct ids over 237 gold topics  [WP-6: 32.2 / 145]
```

That is after T5b's two paraphrases (before them: 32.1 / 146). Recall@30 is
unchanged at 96.6%, English 100%, Odia script 52.9%.

**`Eval_1.xlsx`** is in `handoffs/archive/` with a README line naming it as the
source of the 52 T6 gold rows and of `WP6_eval1_questions.json`.
**`WP6_REPORT.md`** §9 now comes before §10; nothing else changed.

---

## 3. T2 — the subject an officer names binds, or the bot asks

### 3.1 The reader

`query_router/subject_reader.py` scans the question for the vocabulary of every
subject slot the template offers — focus area, work status, scheme, LSDG theme,
plan type — and binds what it finds **before the extractor is asked**, beside
the year and rupee readers (the D30.4 promotion, for the same reason). Its
vocabulary is the loaded registry values plus the alias tables, compared
case-folded, with spaces and hyphens read alike ("in-progress" is "in
progress"), word-bounded. Three rules keep it narrow:

* **Longest reading wins, across slots.** "Water sufficient village" is the
  LSDG theme, not the water focus area; "GP office infrastructure" is a focus
  area, not Theme 6.
* **One value, or it stands aside.** "Water vs sanitation" is a comparison, and
  the extractor's list reading handles it, as before.
* **Three words are never read deterministically**: "approved" (also "approved
  cost"), "done" ("work done") and "main" ("the main reasons"). The extractor
  still reads them.

It binds the table's own phrase and lets the validator resolve it, so "Swachh
Bharat" still carries its lossy caveat. Tied/untied is deliberately not read
(the WP-6 §8.1 split), and geography has its own path.

### 3.2 The guard

If, after extraction, the question names a subject for a slot the template
offers and that slot is still unbound, the answer is not served: "Did you mean
the Roads focus area?" (or "Which focus area did you mean — Roads or Drinking
water?"), reason **`unbound_subject`**, the value(s) as chips; a tap resumes the
same question. A subject the template cannot filter on is not asked about.

### 3.3 The disagreement evidence

Once the reader fires the extractor is not asked for that slot, so a live run
cannot show both readings. The comparison was made **offline and for free**, by
running the reader over every answered question of the four replays WP-6 had
already paid for (the PM's Eval_1 replay and WP-6's three gold replays) and
comparing with what the extractor bound on those very answers:

| | slot readings | what it means |
|---|--:|---|
| agree | 199 | the reader binds exactly what the extractor bound |
| **reader only** | **17** | the extractor bound nothing: 16 Roads on road-works rows, 1 "completed" (row 291) — every one a fix |
| reader stood aside, extractor bound a list | 18 | "water vs sanitation", left to the extractor as designed |
| extractor only | 40 | unchanged behaviour: the reader read nothing, the extractor is still asked |
| **differ** | **0** | never a different value |

The 40 "extractor only" readings include `plan_type = Main` bound on four
questions that never say "main" (#253, #1006, #1014, #2035) — the extractor
inventing a filter, out of scope here (§9).

**Live, in the Eval_1 replay**, the reader bound 145 slots on 314 questions
(focus area 52, plan type 50, status 43), and the guard fired **0 times** —
matching the offline prediction. What the offline comparison could not see is
the one interaction the gold replay did (§8.3).

---

## 4. T3 — the subject wins the comparison, the years combine

**A list on a non-year dimension takes the breakdown; the year list is used
only when no other list exists**, and when a year list is thereby added up the
echo names it — "(2024-2025 and 2025-2026 combined)". That path now also speaks
when a breakdown the officer chose leaves a list summed; a total says nothing
extra. "Year-wise" in the question still keeps the year breakdown.

Proved by execution on both templates rows 42 and 44 used (EXP-011, TRD-008):
exactly two rows, Drinking water and Sanitation, every additive column equal to
the two single-year calls; the WP-6 T4 proof still passes. **In the replay, rows
42 and 44 both returned the two rows** (EXP-009: water 148 activities / ₹1.44 cr,
sanitation 167 / ₹0.83 cr, tied, 2024-26).

---

## 5. T4 — a count of nothing is 0

For the 105 Count templates an empty result **renders** as one row with 0 in
each count column, named from the statement's own SELECT list via
`column_metadata`; the caveat still appends. Listing, Ranking and Lookup keep
"No records matched". It is drawn in `main.py` after the context frame is
stored, so the frame, every follow-up and the Test Report oracle keep the rows
the statement returned; the oracle's 21 zero-row statements still execute to
zero rows (tested). **In the replay rows 19 and 246 answered 0** (`activities:
0`, `gps_awaiting_approval: 0`); row 257 went to a different template (§8.1).

---

## 6. T5 — the reranker's confidence on templates it has already found

Every note in the brief's table is in `_DISAMBIGUATION` (STS-003, the SBM
families, PLN-031, PLN-002/PLU-004, AST-001, TRD-003/EXP-002), and so are notes
on the siblings the baseline's wrong answers went to — PLN-072, SCH-003,
BUD-001, TRD-002, TRD-008, STS-013, STS-001, PLU-003, PLN-025, PLN-032, PLU-008,
AST-002/003, EXP-003/023 — because the incorrect-≤-8 target could not be reached
by the table alone. `rerank_context.py` regenerated; no SQL touched.

**T5b, the brief's conditional step (`54c0344`).** After the notes, rows 182
(BUD-006) and 348 (TRD-003) still did not offer their template as a chip, so
each template got one hand paraphrase, and crowding was re-measured (32.2 / 146).
The same commit corrects the SBM family line, which pointed every sanitation
question at STS-003 and cost row 216 its PLN-049 chip, and sharpens TRD-002 (row
49) and PLN-021 (row 257). **Unmeasured by replay.**

---

## 7. T6 — the Eval_1 file becomes a standing regression

`Ask/grade_eval1.py` is the PM's grading, lifted: accepted ids per row range,
the Roads filter check, the "sector" group correct when it asks, chips read back
to template ids, and the 12 two-years-named rows kept as `defective row`.
**It reproduces the PM's outcome on all 314 baseline rows** (201 / 58 / 15 / 28
/ 12), held there by a test; `--baseline` prints per-group movement. Two things
it had to learn: the no-match path asks on the *fallback* tier, which the PM
rightly read as a clarification; and an id counts for its family (identical SQL
and slots). Chip notes differ on four rows only in which family member is named.

`run_custom_eval.py` gained `--questions` / `--out` and now goes through
`confirm_spend` — it had no guard, so the PM's replay was unmetered. Gate 9
counts it among the paid harnesses (4).

---

## 8. T7 — measured

### 8.1 The Eval_1 replay (314 rows, on `751995f`)

| outcome | baseline 2026-09-14 | WP-6b | share of 302 |
|---|--:|--:|--:|
| correct | 201 | **289** | 95.7% |
| asked, right template offered | 58 | 6 | 2.0% |
| asked, right template NOT offered | 15 | 4 | 1.3% |
| incorrect | 28 | **3** | 1.0% |
| defective row (Eval_1's own) | 12 | 12 | |

| group | n | correct | asked (offered) | asked (not offered) | wrong |
|---|--:|--:|--:|--:|--:|
| total planned budget, main GPDPs | 14 | 12→14 | 2→0 | 0 | 0 |
| GPs with zero-cost activities | 18 | 9→18 | 9→0 | 0 | 0 |
| Swachh Bharat sanitation completed | 18 | 10→18 | 1→0 | 7→0 | 0 |
| total unspent statewide | 6 | 6→6 | 0 | 0 | 0 |
| tied spend, water vs sanitation | 12 | 9→11 | 0 | 0 | 3→1 |
| allocation to Sankalp themes | 12 | 12→12 | 0 | 0 | 0 |
| GPs with nothing under Sankalp themes | 12 | 10→12 | 1→0 | 1→0 | 0 |
| GPs not uploaded GPDP | 12 | 12→12 | 0 | 0 | 0 |
| supplementary plans approved | 12 | 0→12 | 10→0 | 0 | 2→0 |
| GPs with a supplementary plan in Ganjam | 12 | 12→12 | 0 | 0 | 0 |
| total activities in main GPDPs | 12 | 9→10 | 3→2 | 0 | 0 |
| GP with most planned activities | 12 | 0→12 | 11→0 | 1→0 | 0 |
| total estimated cost statewide | 12 | 0→9 | 7→1 | 1→2 | 4→0 |
| planned activities by theme | 12 | 8→12 | 0 | 0 | 4→0 |
| activities under sanitation | 12 | 12→11 | 0 | 0→1 | 0 |
| GP with most piped-water activities | 12 | 9→12 | 3→0 | 0 | 0 |
| GPs pending GPDP approval | 12 | 12→11 | 0 | 0 | 0→1 |
| completed activities statewide | 11 | 7→11 | 1→0 | 0 | 3→0 |
| activities in progress | 11 | 11→11 | 0 | 0 | 0 |
| sector with best completion rate (ask) | 11 | 10→11 | 0 | 0 | 1→0 |
| **road works in progress** | 11 | **0→10** | 1→1 | 0 | **10→0** |
| districts behind on GPDP submission | 11 | 9→10 | 1→0 | 0 | 1→1 |
| GPs with spend but no physical progress | 11 | 11→11 | 0 | 0 | 0 |
| district-wise asset creation | 11 | 4→11 | 4→0 | 3→0 | 0 |
| five-year fund utilisation | 13 | 7→10 | 4→2 | 2→1 | 0 |

**Against the T7.1 targets:**

| target | result | |
|---|---|---|
| incorrect ≤ 8 | **3** | met |
| correct ≥ 240 | **289** | met |
| rows 42 / 44 two rows | both two rows, water and sanitation | met |
| clarify-incorrect ≤ 3 | **4** | missed by one |
| road group 11/11 | **10/11** — no wrong answer left; #311 asks, with STS-003 on the chips | missed |
| rows 19 / 246 / 257 answer 0 | 19 and 246 answer 0; **257** went to PLN-021 (districts ranked by pending approvals — its figures are also 0, but it is the wrong template) | missed |

**The ten rows still not answered correctly, and why:**

| row | outcome | cause |
|---|---|---|
| 49 | wrong: TRD-002, same year twice | reranker; TRD-002 note sharpened in T5b (unmeasured) |
| 257 | wrong: PLN-021 | reranker sibling; PLN-021 note added in T5b (unmeasured) |
| 315 | wrong: served refusal PLN-022 | the refusal was rank 0 in retrieval, so it takes precedence (D28.5); not touched |
| 175, 182 | asked, BUD-006 not offered | the case T5b's BUD-006 paraphrase is for (unmeasured) |
| 348 | asked, TRD-003 not offered | the case T5b's TRD-003 paraphrase is for (unmeasured) |
| 216 | asked, PLN-049 not offered (was correct) | the SBM line said "sanitation → STS-003"; corrected in T5b (unmeasured) |
| 311 | asked, STS-003 offered | retrieval's top two within the margin, so it asks BEFORE the reranker or the subject reader runs — as in the baseline |
| 143, 145, 171, 351, 355 | asked, right template offered | reranker declined to choose |

**Clarifications by reason:** ambiguous_templates 14, ambiguous_term 7 (the
"sector" group, as ruled), known_unanswerable 1, **unbound_subject 0** — the
guard did not fire anywhere, which is what it should do on this file: every
subject was bound.

### 8.2 The gold replay (one of three, on `751995f`)

| | WP-6 run 1 / 2 / 3 | WP-6b (one run) |
|---|--:|--:|
| behaving correctly, all 275 | 90.5% / 90.9% / 89.8% | **89.5%** (246) |
| confidently wrong | 5 / 5 / 6 | **7** (2.5%) |
| the 52 Eval_1 gold rows | 50 / 51 / 50 | **51** |

**The majority-of-three comparison was not possible**: the second and third
replays were stopped on the operator's instruction. Against WP-6's majority,
this single run fails five rows WP-6 got right and passes one it got wrong:

| row | WP-6 | this run | reading |
|---|---|---|---|
| #1008 (Odia) | hit / hit / wrong | wrong_template | flipped in WP-6 too — noise on one run |
| #1624 "and for 2023-24?" | hit / hit / wrong_entities | wrong_entities | flipped in WP-6 too — noise on one run |
| #1202 "and household ones?" | offered ×3 | asks for the year | a follow-up fragment asking, not a wrong answer |
| **#1423** "funded under Own Funds" | **hit ×3** | asks "which tied/untied is 'Own Funds'?" | **caused by T2 — fixed, §8.3** |
| #2024 "overall number of activities in main GPDPs" | hit / offered / offered | wrong_template: BUD-006 | BUD-006 carries the activity count too, but it is the wrong template; plausibly the BUD-006 note's reach |
| #2005 Swachh Bharat completed | hit / clarify / clarify | **hit** | recovered — the WP-6 residual |

**#1402 and #1522** (tied and untied) both still answer, on BUD-005 and EXP-008.

### 8.3 The one regression, and its fix

Gold #1423 — "Which activities of Andhrua are funded under Own Funds in
2024-25?" — was answered three times out of three by WP-6. Here the subject
reader correctly bound `scheme = Own Funds`; with the scheme no longer on its
list, the extractor put the same words into `tied_untied`, and validation then
asked which tied/untied value "Own Funds" was. The offline comparison could not
have seen this: it compared the two readings of a slot, not what the extractor
does with a slot taken away. **The fix (commit "WP-6b T2b")**: an extractor
value that repeats a phrase the reader bound is dropped and logged. Pinned by a
test; the full suite is green with it (674 tests); **not replayed.**

### 8.4 Spend

| | calls |
|---|--:|
| Eval_1 replay, 314 rows | ~1,000 (the runner has no meter; ~3 per row plus chip pre-fill) |
| gold replay run 1 | 778 (metered) |
| replays stopped part-way (a superseded gold run 2, and the final Eval_1 and gold runs) | ~550, estimated |
| recall_eval ×2, refusal_recall index rebuild, gate 5 | 26 |
| **total** | **~2,350**, all through `confirm_spend` |

The ~550 stopped calls are the cost of running T7 before T5's conditional step:
that ordering was mine, and the lesson is in §9.

---

## 9. What the next package should know

1. **Replay T5b and T2b before the pilot.** Both are tested and gated, neither
   is replayed. The two cost one Eval_1 replay (~1,000 calls) and, for the gate
   item this package could not close, a 3× gold replay (~2,400).
2. **A deterministic reader changes the extractor's job, not just its inputs.**
   Taking a slot off the extractor's list moved its words into a neighbour
   (#1423). The offline reader-vs-extractor comparison is the right cheap check
   for *disagreement*, but it cannot see this; only a replay can.
3. **Run a brief's conditional steps before its measurement.** T7 ran before
   T5's "if rows still lack their template, add paraphrases" check had been
   applied, and one replay had to be stopped half-way.
4. **Row 311's class**: when retrieval's top two are within the margin the bot
   asks before the reranker or any reader runs, so no note and no reader can
   help; only retrieval (a paraphrase) can.
5. **The extractor invents `plan_type = Main`** on questions that never say
   "main" (#253, #1006, #1014, #2035 in WP-6's replays). Out of scope here; the
   reader deliberately does not read "main".
6. **The calendar-window reader** still reads "2023 to 2025" as calendar years
   while "2023-2025" is fiscal (§2); nothing served depends on it today.
7. **Crowding is 32.2 / 146** after two paraphrases; the line is in gate 8 now,
   so the next batch is measured against it rather than argued.

---

## 10. Compliance with the brief

| constraint | status |
|---|---|
| Catalogue SQL edited only through migrations (none expected) | Yes — no SQL changed; two hand paraphrases, per T5's own condition |
| Derived artefacts regenerated by `derive_catalog.py` | Yes — `rerank_context.py`; `--check` green |
| Test Report row counts hold | Yes — gate 2, 343 statements |
| Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched | Yes — everything ran from `C:\dev\odisha-wp6b` |
| Every paid replay through `confirm_spend` | Yes — and `run_custom_eval.py` now has the guard it lacked |
| Thresholds untouched | Yes |
| Out of scope: two-level breakdowns, Odia, catalogue options 5/6, SME calls | Not touched |

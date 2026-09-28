# WP-6d — Bottom-10 rankings, the D34 conditions, and three pilot polish fixes: REPORT

> ## Where everything is
>
> ```
> Ask/tools/migrations/m6_ranking_floor.py   T1 — M6, slot declarations only, idempotent, --check
> Ask/tools/derive_catalog.py                T1 — RANKING_FLOOR_DEFAULTS; the contract refuses any other threshold default
> Ask/query_router/router.py                 T2 — superlative_list_slots / number_in_question; T4 guard log; T6 _block_first,
>                                                  list pre-fill, no unwritten list length on chips; T7 echo values as lists
> Ask/query_router/subject_reader.py         T4 — plan_type in VOCABULARY_GUARDED; guard_vocabulary (full word list)
> Ask/query_router/template_catalog.py       T1 M6 slots; T4 PLN-007 phrasings; T5 BUD-003 / PLN-024 phrasings
> Ask/query_router/zones.py                  T6 + T7 — one renderer for chips and the answer echo
> Ask/eval_questions_full.json               T3 — G1613 expects an answer
> Ask/run_custom_eval.py, Ask/grade_eval1.py T8 — chip-tap second turn; the fifth standing group (1023-1044)
> Ask/tests/test_wp6d_ranking_floor.py       29 tests, grouped by task
> handoffs/WP6c_pilot_questions.json         T8 — 22 new rows (1023-1044) after WP-6c's 22
> handoffs/WP6d_pilot_replay.csv/.jsonl      T8.2 — all 44 pilot rows, graded
> handoffs/WP6d_eval1_replay.csv/.jsonl      T8.3 — Eval_1, graded, diffed against WP-6c
> handoffs/WP6d_gold_replay_run1.csv/.jsonl  T8.4 — the one gold replay, beside WP-6's three verdicts and WP-6b's
> ```
>
> **Committed, not pushed.** `2c2c7bf` T1 (with the brief), `cd32e2b` T2, `03c82fd` T3,
> `f0c0ad5` T4, `26117f6` T5, `e877bac` T6+T7, `cf9e1e1` T6 follow-up, and T8's commit
> carrying this report and the runs. Left for the operator as before: the PM's
> `handoffs/PROJECT_PLAN.md` edit, the untracked `handoffs/WP6b_eval1_replay_notes_off.csv`,
> and `Ask/bench/`.
>
> Re-run from a local mirror (`C:\dev\odisha-wp6d`, a plain copy of `Ask/`):
> ```
> cd Ask && python tools/migrations/m6_ranking_floor.py --check
> cd Ask && PRDW_REPO=<the Drive repo> python -m unittest tests.test_wp6d_ranking_floor
> cd Ask && python prdw_gates.py --yes --repo <the Drive repo>
> cd Ask && python run_custom_eval.py --questions ../handoffs/WP6c_pilot_questions.json --out pilot.jsonl --yes
> cd Ask && python grade_eval1.py pilot.jsonl
> ```

---

## 0. For the PM — what this package did

1. **Rankings answer with the bottom 10.** "Which focus area has the lowest
   completion rate in FY 2025-26?" — all four operator phrasings — now answer
   IMP-009 with ten rows, lowest first, echo "(bottom 10)". No "At least how many
   activities?". "Bottom 3" gives three; "the single lowest" still gives ten; a
   floor the officer writes ("with at least 50 activities") is bound and shown.
   "Which GP spent the most?"-style rankings elsewhere still answer one row.
2. **D34 is closed on the code side**: PLN-007 has the "behind / lagging on GPDP
   submission" phrasings, and an invented `plan_type = Main` is dropped (the
   guard reads "main", so "main GPDPs" still binds). The HEAD gold replay (D34.2)
   is §8.3: **90.2% behaving correctly, inside WP-6's range, 6 confidently wrong**.
   **Row 315 still does not reach PLN-007** — it says "delayed", which neither
   phrasing covers (§8.2).
6. **Eval_1 misses its target**: 293 correct (up 3) but 4 wrong where the target
   was ≤ 2 — two reranker picks (TRD-002), one retrieval shift (PLN-072), row 315.
3. **Chips keep what the officer named.** "count of planned activities in
   Kalimela in 2024" now offers "…each GPDP theme in **Kalimela block** in
   2024-2025?", and the tap answers for the block. A scheme list survives into
   the chip ("…(5th State Finance Commission (SFC) and Own Funds)?").
4. **The echo reads as English**: no "(total)", "(fiscal_year)", "(10)", "(Main)"
   or "5TH STATE FINANCE COMMISSION" in any of 330 echoes across both live runs.
5. **Two things did not work and are yours to decide** (§9): pilot rows
   1007 / 1009 are still declined by the reranker after the BUD-003 phrasings
   (the brief's stop condition — the operator chose to continue with T6–T8), and
   the plain count "count of planned activities in Barpali in 2024-25" reaches
   neither PLN-024 nor PLN-049 live.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | M6 applied and idempotent; `derive --check` green with the new phrasings; `validate_catalog.py` 343 / 0; no SQL text changed; gate 9 (j) holds | **PASS** — `m6 --check` "applied", a second apply writes nothing; derive in step; 343 / 0 / 0 / 0; M6 refuses to write if SQL text changes and proves the oracle first; gate 9 (j) "unit and direction on all 15 threshold slots" |
| 2 | T8.1 offline cases pass; full suite green; changed echo pins listed, bound values unchanged | **PASS** — 744 tests (22 skipped without the live key; `prdw_gates.py` 9/9 GREEN at 742, before the two T8 grader tests); the pins are in §7.3 — no answer-echo pin changed, two chip pins and two T1 pins did |
| 3 | New rows pass: rankings / plan-type / Kalimela / plain count | **PARTLY** — rankings 11/12 (1032 declined by the reranker this run, answered in the first), plan-type 4/4, block-and-GP 4/4, **plain count 0/2** (§8.1) |
| 4 | Eval_1 meets T8.3; gold replay meets T8.4; G1613 answers | **PARTLY** — Eval_1 **misses** T8.3: 293 / 5 / 0 / **4**, incorrect 4 > 2, row 315 not on PLN-007 (§8.2); gold **meets** T8.4: 90.2%, inside WP-6's 89.8–90.9%, the four majority-right rows it loses re-asked or explained and ruled noise (§8.3); **G1613 answers** (IMP-009, 10 rows) |
| 5 | No echo in either replay has a raw `$group_by` value, a bare list length or a raw scheme label | **PASS** — 0 of 297 Eval_1 echoes, 0 of 33 pilot echoes, 0 of 222 gold echoes |
| 6 | Brief and report committed, one commit per task, not pushed | **PASS, one exception** — T6 and T7 share one commit (§7.4) |

---

## 2. T1 + T2 — the bottom 10

### 2.1 M6

`tools/migrations/m6_ranking_floor.py` names IMP-009, IMP-019 and IMP-020 and
writes, on each:

* `$threshold`: `"optional": True, "default": "1"`, beside WP-6c's `unit:
  activities` / `direction: above`, which are kept (M6 refuses to write if either
  is lost). A default, not merely optional: `HAVING COUNT(*) >= NULL` drops every
  row, and `COUNT(*) >= 1` is true of every group.
* `$top_n`: keeps `default: "10"`, gains `superlative_means_one: False`.

Before writing it runs each statement with the Test Report's recorded
`threshold: 50, top_n: 10` (10 / 7 / 10 rows, as recorded) and with the default
floor (10 / 7 / 10). `derive_catalog.contract_problems` needed one change: it
refused a default on any slot but `$top_n` and an `optional` flag on a slot the
SQL does not guard with `IS NULL OR`. It now accepts both **only** for the
three `(qid, "threshold")` pairs in `RANKING_FLOOR_DEFAULTS`, requires their SQL
to read `HAVING COUNT(*) >= $threshold`, and requires `superlative_means_one:
False` on exactly those three `$top_n` slots. Any other threshold with a default
still breaks the build (tested with PLN-045).

WP-6c's "At least how many activities?" is no longer reached by any statement
(the other activity-count thresholds, PLN-045 / PLN-069, are "fewer than"). It
is left in place, as the brief says.

### 2.2 The router

In `_extract_slot_values`, for a `$top_n` declaring `superlative_means_one:
False`, the extractor's value stands only if the question writes that number —
digits, or a number word one to twenty. Years are masked first ("FY 2025-26" is
not 25), and "which one" / "the one" / "one of" are not counts. Otherwise it is
dropped, logged `top_n: superlative read as list (declared)`, and the default 10
binds. The extractor prompt is unchanged.

**One addition the brief did not name:** a defaulted value is no longer run
through WP-6c's first-turn direction check — the floor of 1 is not a figure the
officer wrote, so there is nothing in the question to compare it with.

### 2.3 Ties at the bottom (reported, not acted on)

IMP-009, no floor, all focus areas:

| year | focus areas | at the bottom rate (0%) |
|---|--:|--:|
| FY 2024-25 | 25 | **23** |
| FY 2025-26 | 26 | **26** — every one |

So the ten rows are ten of 23 (or 26) tied at zero, ordered by planned
activities; the officer sees the ten largest of the ties.

---

## 3. T3 — G1613

`expected_behavior` "clarify" → "answer", `case_type` "ambiguity" → "standard",
notes gain "Operator ruling 2026-09-28 (WP-6d): no floor by default, bottom 10."
G2041 / G2042 untouched (tested). Live: §8.3.

---

## 4. T4 — the D34 conditions

**D34.3.** PLN-007 gains "Which districts are behind on GPDP submission in a
given year?" and "…lagging on GPDP submission…". Index rebuilt; recall@30 96.6%,
English 100% (158/158), **crowding 32.2 / 146 — unchanged**, the gate 8 line.

**D34.4.** `plan_type` joins `subject_reader.VOCABULARY_GUARDED`. The trap the
brief named is real and is avoided: the prefill's word list removes `_NOT_READ`,
which holds "main", so the guard now reads its own list —
`subject_reader.guard_vocabulary`, i.e. `_vocabulary(full=True)` — the whole alias
table plus registry values. A test asserts the two lists differ by exactly
`_NOT_READ["plan_type"]`. Proved offline on both sides: with the extractor
stubbed to `plan_type = Main`, the phrasings of #253, #1006 (Odia), #1014 and
#2035 each drop it and log `dropped plan_type=['Main']: the question does not
say it in plan type words`; every Eval_1 row that says "main" or
"supplementary" (20+, rows 1-2 included) still binds its plan type.

**Live, the guard did not fire** — in the pilot run the extractor did not invent
"Main" on those four questions this time (all four answered with no plan type),
and nothing in Eval_1 tripped it.

---

## 5. T5 — example phrasings, and the stop condition

BUD-003 gains the three phrasings the brief lists; PLN-024 gains "How many
activities are planned in a given block in a given year?". Index rebuilt;
recall and crowding unchanged (96.6%, 32.2 / 146). All new phrasings are in
the index (vector counts checked per template).

**The stop condition triggered.** Rows 1005 / 1007 / 1009 were run first on
their own (3 rows, 13 calls): retrieval now ranks **BUD-003 first on all three**
(it did on none in WP-6c), but the reranker still declined 1007 and 1009; 1005
answered, on BUD-002 with both schemes bound. I stopped and asked; **the
operator chose to continue T6–T8 with no further phrasings or reranker notes.**
The re-run of the 22 WP-6c rows (§8.1) confirms it.

**What PLN-024 returns for a plain count** (offline, served on PLN-024 with the
block bound — live it was never reached, §8.1): "How many activities are planned
under each GPDP theme in all GPs in 2024-2025 (Barpali block)?", **seven rows,
one per theme** (139, 136, 109, 29, 26, 21, 9), no single figure — the 469 total
is never shown. Kalimela the same: seven rows, 268 in all. As predicted: without
a "total" cue the breakdown reader leaves PLN-024 on its own per-theme grain.

---

## 6. T6 — chips

**a) Block first** (`router._block_first`, called only from
`_extract_fill_values`): an extracted `gp_name` that is also an **exact** block
name, with no GP cue beside it ("GP", "G.P.", "gram panchayat", "panchayat",
either side), moves to `block_name`; the same name in both keeps the block; a
different block also named leaves both alone. Logged `chip fill: X read as
block (also a GP)`. The answer path does not come through here.

**b) Nothing the fill knows is dropped.** `readable_question` now:
* puts a place named at another tier into an unfilled geography gap, with its
  noun — PLN-024 / PLN-049 with `block_name = Kalimela` render "…in Kalimela
  block in 2024-2025?" (exact strings tested);
* appends every other filled slot the question has no gap for, in the T7 words;
  a breakdown the officer named reads "(broken down by district)" on a chip,
  since no suffix says it there;
* keeps `send_text` equal to the label.

**Found on the way, and fixed:**
* The chip pre-fill handed a **list** value (two schemes) to `validate()` whole,
  which failed and silently dropped it — the second reason the BUD-003 chip lost
  the schemes. It now validates each value.
* **Found by the T8 pilot run, fixed in `cf9e1e1`:** (1) six questions offer two
  tiers side by side ("in {gp_name}/{block_name}"), and the chip read "in a gram
  panchayat/Bheden" — now only the named tier shows ("in Bheden block"); (2) a
  gap filled with a place name on a chip now carries its tier noun ("in Laxmipur
  GP"), because Kalimela, Laxmipur, Bheden and Boipariguda are each both a block
  and a GP and a tap sends only the text; (3) the chip pre-fill no longer shows a
  list length the officer did not write — chips for "…with at least 50
  activities … lowest" read "(the lowest, …)" while the ranking answers ten.
  The pilot run in `WP6d_pilot_replay.*` is on the code **before** (3); (1) and (2)
  are in it.

Proved offline: the operator's question, reranker stubbed to no-match with
PLN-024 / PLN-049 / PLN-025, gives three chips all naming "Kalimela block" and
none "a gram panchayat"; the per-theme chip, routed back with the extractor
stubbed to read "Kalimela block", binds `block_name = Kalimela` and no GP;
"Kalimela GP" and "Kalimela gram panchayat" stay a GP; Andhrua (GP only) is
unchanged; the BUD-003 chip carries both schemes and the subject reader reads
both back from its text; every display name reads back as its database label.

`grade_eval1.chip_ids` reads a chip without its appended bracket when the full
text matches no catalogue question — the grading rules are unchanged; without
this every appended chip would have graded "clarify-incorrect".

---

## 7. T7 — the echo

### 7.1 What changed

One renderer in `zones.py` for `resolved_question` (answers) and
`readable_question` (chips). Display only; SQL parameters are the database's own
labels (tested: `bound_filters` and the bound SQL values for a case with two
schemes, a plan type and a focus area are unchanged by the echo).

1. `$group_by` is never appended; `breakdown.describe` says it once.
2. The list length reads from the first key of the ORDER BY that `LIMIT $top_n`
   limits: "(top 10)", "(bottom 10)", `top_n = 1` "(the highest)" / "(the
   lowest)". Checked against `derive_catalog`'s own reading on every ranking
   template: 0 disagreements.
3. Filters carry their noun and share one bracket: "main GPDP" / "supplementary
   plan", "tied funds", "Sanitation focus area", the theme as stored, "ongoing
   work" / "work awaiting approval", schemes by display name.
4. `DISPLAY_NAMES` (the brief's table) applies to filled placeholders as well as
   appended values — "in WORK ONGOING status" reads "in ongoing status".
5. Ranking floor: "(bottom 10)"; an officer's floor "(bottom 10, focus areas with
   at least 50 activities)"; the default 1 is never shown. Other thresholds with
   no gap read "above ₹20000" / "below 50%" — never a bare number (the brief's
   table did not cover them; IMP-013's "(20000) (10)" was one of the tallied
   fragments).

### 7.2 Ten before/after pairs (re-rendered from the WP-6c replays)

All 309 served echoes of the WP-6c Eval_1 and pilot replays were re-served
offline from their recorded template and bound values: **190 change, 0 have a
raw breakdown value, a bare number, a raw scheme label or a noun-less plan /
tied-untied value, and every bound filter is still named** (pinned by
`T7EchoTests.test_every_served_eval1_echo_re_renders_clean`).

| # | before | after |
|---|---|---|
| 303 | How many activities in all blocks are in WORK ONGOING status for 2024-2025 and 2025-2026 (Roads) (fiscal_year)? (broken down by year) | How many activities in all blocks are in ongoing status for 2024-2025 and 2025-2026 (Roads focus area)? (broken down by year) |
| 1 | …allocated to each GPDP theme in 2024-2025 (Main) (total)? (as one total) | …allocated to each GPDP theme in 2024-2025 (main GPDP)? (as one total) |
| 12 | …recorded in 2024-2025 and 2025-2026 (10)? (2024-2025 and 2025-2026 combined) | …recorded in 2024-2025 and 2025-2026 (top 10)? (2024-2025 and 2025-2026 combined) |
| 17 | …in all blocks are in WORK COMPLETED status for 2025-2026 (Sanitation)? | …in all blocks are in completed status for 2025-2026 (Sanitation focus area)? |
| 40 | …under Drinking water and Sanitation in 2025-2026 (Tied)? | …under Drinking water and Sanitation in 2025-2026 (tied funds)? |
| 49 | …between 2022-2023 and 2022-2023 (Drinking water and Sanitation) (Tied) (focus_area)? (broken down by focus area) | …between 2022-2023 and 2022-2023 (Drinking water and Sanitation focus areas; tied funds)? (broken down by focus area) |
| 83 | …uploaded the GPDP in 2024-2025 and 2025-2026 (Main) (fiscal_year)? (broken down by year) | …uploaded the GPDP in 2024-2025 and 2025-2026 (main GPDP)? (broken down by year) |
| 155 | Which Gram Panchayats have planned the highest number of activities under all themes in 2024-2025 (1)? | …under all themes in 2024-2025 (the highest)? |
| 1001 | …from each funding source in 2024-2025 (5TH STATE FINANCE COMMISSION, XV Finance Commission and Own Funds)? | …(5th State Finance Commission (SFC), 15th Finance Commission (CFC) and Own Funds)? |
| 1013 | Which high-expenditure activities have not yet started in 2024-2025 (20000) (10)? | …in 2024-2025 (top 10; above ₹20000)? |

Live, the new rows read e.g. "Which focus area has the lowest completion rate
in 2025-2026 (bottom 10)?" and "…(bottom 10, focus areas with at least 50
activities)?".

One re-render artefact, not a change: #1019 "below 2.5 lakh (₹250000) rupees"
re-renders as "below 250000 rupees" only because the offline re-render feeds
back the stored figure, not the officer's words; live it still echoes "2.5 lakh
(₹250000)".

### 7.3 Changed test pins

| test | before → after | why |
|---|---|---|
| `test_param_binding::test_judgement_thresholds_stay_required_and_undefaulted` | all 15 thresholds required → the 12 outside `RANKING_FLOOR_DEFAULTS` | T1 |
| `test_wp6c_pilot_feedback::T1AskTests` (IMP-009 "At least how many activities?") | → PLN-045 "Fewer than how many activities?" | T1: IMP-009 no longer asks |
| `test_pending_clarification::test_unknown_slots_stay_readable` | "…of a mandal?" → "…of a mandal (Krishna)?" | T6b: the fill is appended, not dropped |
| `test_router_miss_path::test_the_users_name_reaches_the_chip` | "…for Naugaon in a year?" → "…for Naugaon GP in a year?" | T6 follow-up: a place carries its tier on a chip |

**No answer-echo (`query_description`) pin changed**: the existing ones assert
with `assertIn` on the "(broken down by …)" suffix, which T7 keeps. There were
therefore no pinned echo cases whose `bound_filters` could move; the new T7 test
asserts the bound values directly.

### 7.4 One commit for T6 and T7

The brief ties them ("appended in the T7 form"): chips and the echo share the
renderer, so splitting `zones.py` across two commits would have left the first
one half-built. `e877bac` carries both; `cf9e1e1` is the follow-up the pilot run
found.

---

## 8. T8 — measured

### 8.1 The pilot rows — `WP6d_pilot_replay.csv` (44 rows)

**The 22 WP-6c rows, re-run:** thresholds **12 / 12** (unchanged); fund split
**7 / 10** (WP-6c 6 / 10) — 1005 now answers (BUD-002, both schemes bound);
1002 / 1007 / 1009 still ask, **now with the schemes on every chip**; the
Tied / Untied / Other chip set appeared 0 times.

**The 22 new rows (the fifth standing group, `grade_eval1.grade_wp6d`):**

| # | question | outcome |
|---|---|---|
| 1023–1026 | the four operator phrasings | **IMP-009, 10 rows** each, "(bottom 10)" |
| 1027 | Which themes should be prioritised for implementation support in 2025-26? | IMP-019, 7 rows (seven themes that year) |
| 1028 | Which LSDG theme most needs implementation support in 2024-25? | IMP-019, 7 rows |
| 1029 | Which focus areas should be prioritised … 2025-26? | IMP-020, 10 rows |
| 1030 | Which focus area needs the most implementation support in 2024-25? | IMP-020, 10 rows |
| 1031 | Show the bottom 3 focus areas by completion rate in 2025-26 | IMP-009, **3 rows** |
| 1032 | Which focus areas with at least 50 activities have the lowest completion rate in 2025-26? | **asked** — reranker no-match, IMP-009 first chip. In the first pilot run it answered IMP-009, 10 rows, floor 50, "(bottom 10, focus areas with at least 50 activities)" |
| 1033 | What is the single lowest focus area … ? | IMP-009, **10 rows** |
| 1034 | Which GPDP theme has the highest actual expenditure in 2024-25? (control) | EXP-015, **1 row**, "(the highest)" |
| 1035–1038 | the D34.4 phrasings | answered, **no plan type bound** on any |
| 1039 | What is the count of planned activities in Kalimela in 2024? | asked; all three chips name "**Kalimela block**", none "a gram panchayat" |
| 1040 | same, then tap the per-theme chip | chip "…each GPDP theme in Kalimela block in 2024-2025?" → **PLN-024, block Kalimela, 7 rows** |
| 1041 | …in Bheden in 2024? | asked; chips "…in Bheden block…" |
| 1042 | …in Laxmipur GP in 2024? | asked; chips "…in Laxmipur GP…" (stays a GP) |
| 1043 | What is the count of planned activities in Barpali in 2024-25? | **asked** — chips PLN-027 / PLN-028 (highest / lowest theme) and PLN-044, all "in Barpali block" |
| 1044 | count of planned activities in Attabira in 2025-26 | **wrong** — served the PLU-005 refusal ("delegated to another panchayat tier") |

In the first pilot run (before `cf9e1e1`) 1029 answered on IMP-019 broken down
by focus area — the same numbers as IMP-020, since the two differ only in their
default breakdown, but an echo reading "Which themes … (broken down by focus
area)". Rows 1029 and 1032 flipping between two runs of the same code is the
reranker's run-to-run variation.

**Every guard line, pilot run:** `top_n: superlative read as list (declared)` × 7
— on 1023, 1024, 1025, 1026, 1028, 1030, 1033, exactly the singular rankings.
`dropped plan_type` × 0 and `chip fill: … read as block` × 0: the extractor
neither invented "Main" nor read the four places as GPs this time, so both rules
are proved offline only (§4, §6). No `dropped tied_untied` / `rehomed` lines.

### 8.2 Eval_1 — `WP6d_eval1_replay.csv`

314 rows, ten parallel processes, 0 errors, graded by `grade_eval1.py` (grading
unchanged; `chip_ids` reads appended chips, §6), diffed against
`WP6c_eval1_replay.csv`:

| outcome | WP-6c | WP-6d | share of 302 |
|---|--:|--:|--:|
| correct | 290 | **293** | 97.0% |
| asked, right template offered | 10 | 5 | 1.7% |
| asked, right template NOT offered | 0 | 0 | |
| incorrect | 2 | **4** | 1.3% |
| defective row (Eval_1's own) | 12 | 12 | |

**Against T8.3: not met.** No group lost more than one row, but incorrect is 4
(target ≤ 2) and **row 315 does not answer on PLN-007**.

| row | WP-6c → WP-6d | served | reading |
|---|---|---|---|
| 13, 118, 145, 173, 188 | asked → correct | PLU-008, PLN-002, PLN-024, BUD-006, PLU-008 | |
| 212 | wrong → correct | PLN-024 | WP-6c's new wrong answer, recovered |
| 45, 171 | correct → asked | chips offer EXP-009 / BUD-006 | right template on the chips |
| 42 | asked → **wrong** | TRD-002 | retrieval rank 0 is EXP-009 (right); the reranker picks TRD-002 — as it already did on row 49 in WP-6c |
| 49 | wrong → wrong | TRD-002 | unchanged from WP-6c |
| 211 | correct → **wrong** | PLN-072 "Are the planned activities balanced across themes" | "thematic distribution of planned activities" — retrieval now ranks PLN-072 first |
| 315 | asked → **wrong** | the PLN-023 refusal | "Identify districts with **delayed** GPDP submissions"; top 3 retrieved PLN-005 / PLN-019 / PLN-023, PLN-007 not among them; the reranker named PLN-023 as a near miss and D28.5 precedence served it |

Nothing this package changed is in the reranker's input for rows 42 / 49 / 211
(`rerank_context.py` is byte-identical to WP-6c's; paraphrases never reach the
reranker). What did change is retrieval, through the six new phrasings; 211's
new rank 0 may be that, or the D33 answer↔ask variation — one run cannot tell.
Row 315 is a phrasing gap: "delayed" is neither "behind" nor "lagging". **Not
patched** — see §9.

**Guard lines, Eval_1:** none of any kind (no superlative, plan-type, block,
tied/untied or re-home line). Clarifications by reason: ambiguous_templates 8,
ambiguous_term 7 ("sector", as ruled), no_match 1. Echoes: 0 of 297 with a raw
breakdown value, a bare number or a raw scheme label.

### 8.3 The gold replay — `WP6d_gold_replay_run1.csv`

One replay (D34.2), 275 rows, sequential (its follow-up rows lean on the row
before), on the final code, graded by `grade_full_eval.py` unchanged, compared
row by row with WP-6's three verdicts and WP-6b's one (`wp6_verdicts`,
`wp6b_verdict` columns in the CSV, as WP-6b's file had).

| | WP-6 run 1 / 2 / 3 | WP-6b (one run) | **WP-6d (one run)** |
|---|--:|--:|--:|
| behaving correctly (hit + asked with the gold chip + asked as ratified), all 275 | 90.5% / 90.9% / 89.8% | 89.5% (246) | **90.2% (248)** |
| confidently wrong (wrong template + wrong values) | 5 / 5 / 6 | 7 | **6** |

**G1613 answers**: IMP-009, 10 rows, "Which focus area has the lowest completion
rate in 2024-2025 (bottom 10)?", with the one `superlative read as list` line
of the run. **#1423** answers on SCH-002 (WP-6b asked — T2b's fix, now replayed);
**#1402** BUD-005 and **#1522** EXP-008 answer the tied/untied split, as in WP-6c.

**WP-6 majority right, this run not — 4 rows, all ruled noise:**

| row | WP-6 | WP-6b | this run | ruling |
|---|---|---|---|---|
| #1701 "…zero expenditure 90 days after sanction?" | hit ×3 | hit | wrong_entities: `threshold = 0` | **re-asked three times live: 90 bound all three times.** The extractor read "zero" once; nothing in this package touches a days threshold |
| #1232 "2024-25 me kitne compost pit complete hue?" | hit ×3 | hit | partial: asked, the gold template (SBM-SWM-005) the first chip | **re-asked three times: answered twice, asked once** — the D33 answer↔ask variation |
| #1202 "and household ones?" | gold offered ×3 | clarify | clarify (chips name IHHL questions, not SBM-GWM-008) | a follow-up fragment; WP-6b failed it the same way |
| #1624 "and for 2023-24?" | hit / hit / wrong_entities | wrong_entities | wrong_entities | split inside WP-6 itself; WP-6b the same |

**WP-6 majority not right, this run right — 3:** G1613 (the ruling), #1415
(Odia-transliterated tied/untied, FND-001), #2005 (Swachh Bharat completed —
WP-6's residual, answered in WP-6b too).

The gold row that mirrors Eval_1 row 315, **#2046** "Identify districts with
delayed GPDP submissions", asked with PLN-007 on the chips
(clarify_gold_offered) — in Eval_1 the same words were served the PLN-023
refusal. One more sign that "delayed" sits on the edge of PLN-007's reach.

The two replays were run in the same hour; the ~20 re-ask calls above are
extra to the brief's estimate.

### 8.4 Gates

`prdw_gates.py --yes --repo <Drive repo>` from the mirror: **GATE GREEN 9/9** —
742 tests; Test Report row counts; derived artefacts in step; gold set format;
model identity; served-refusal invariant; paired-year pins; refusal recall
(crowding 32.2 / 146); static invariants incl. "unit and direction on all 15
threshold slots".

---

## 9. For the PM — open, and seen but left alone

**Decisions this package hands back:**
1. **Fund split, rows 1007 / 1009** — retrieval now finds BUD-003 first; the
   reranker still declines. The chips now carry the schemes, so a tap no longer
   loses them. More phrasings or a `_DISAMBIGUATION` note were out of bounds.
2. **Plain count** — "count of planned activities in <block>" reaches neither
   PLN-024 nor PLN-049 live (Barpali asks; Attabira is served the PLU-005
   refusal), and PLN-024 would give per-theme counts, not one figure, if reached
   (§5). Your call whether "count of …" should read as a total, or whether the
   catalogue needs a plain count statement.
3. **Row 315** — a "delayed GPDP submissions" phrasing on PLN-007 would likely fix
   it; not added without you, and it needs an Eval_1 run to measure.
4. **Rows 42 / 49** — the reranker prefers TRD-002 for "compare tied fund spending
   between water and sanitation" although retrieval ranks EXP-009 first.

**Seen and deliberately left, as the brief says:**
* the block-versus-GP reading on the **answer** path (the pilot's Kalimela rows
  asked, so it was not exercised);
* the repeated year "between 2022-2023 and 2022-2023" — still in row 49's echo;
* Eval_1 row 212 — it answered correctly this run (PLN-024).

---

## 10. Spend

All through `confirm_spend`. The runners have no meter; the replay lines are
counted from the records, as WP-6b and WP-6c did.

| | calls |
|---|--:|
| index rebuilds (`refusal_recall.py --yes`) × 2 and `recall_eval.py --yes` × 2 (+1 cached read) | ~60 |
| T5 stop-condition check, rows 1005 / 1007 / 1009 | ~13 |
| pilot rows, 44 × 2 runs (the second after the chip fixes) | ~300 |
| gate 5 live model list | 2 |
| Eval_1, 314 rows | ~1,000 |
| gold replay, 275 rows | 779 (metered, `WP6d_gold_replay_run1.usage.json`) |
| re-asking gold #1701 and #1232 three times each | ~20 |
| **total** | **~2,170** |

The second pilot run (~150) was not in the brief's estimate: it re-measured the
chip fixes the first run found, so that the committed record is one clean run.

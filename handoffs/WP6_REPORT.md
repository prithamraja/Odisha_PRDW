# WP-6 — Catalogue dimensions: filters, breakdowns, lists, and the Eval_1 gaps: REPORT

> ## Where everything is
>
> ```
> Ask/tools/derive_catalog.py                  the derivation half, and the contract (T0)
> Ask/tools/import_workbook.py                 the import half; only ever CREATES (T0)
> Ask/tools/migrations/m0_mark_derived.py      the one-shot that marked the derived blocks
> Ask/tools/migrations/m1_universal_slots.py   T2 — the universal filters
> Ask/tools/migrations/m1_hand_edits.py        T2 — the nine M1 could not script
> Ask/tools/migrations/m2_group_by.py          T3 — $group_by, and the folds
> Ask/tools/migrations/m3_list_filters.py      T4 — list-valued filters and year spans
> Ask/query_router/breakdown.py                T3/T4 at run time, and the "sector" question
> Ask/query_router/template_catalog.py         THE SOURCE OF TRUTH since T0
> Ask/tests/data/retired_templates.json        the four folded ids, with their proof
> Ask/tests/test_wp6_catalog_dimensions.py     45 tests, grouped by task
> eval/gold/eval1_officer.jsonl                T6 — Eval_1's 26 questions, 52 rows
> handoffs/archive/AI_Chatbot_Questions.xlsx   the 2026-08-13 sign-off, archived
> handoffs/WP6_REPORT.md                       this file
> ```
>
> **Committed, not pushed** (operator's instruction, 2026-09-12): one commit per
> task — `088c469` T0, `2381071` T1, `5926be5` T2, `b722478` T3, `bc13e48` T4,
> `26f6543` T5, `bb71a41` T6, and T7's commit carrying this report.
>
> Re-run anything:
> ```
> cd Ask && python prdw_gates.py --repo <the Drive repo>     # THE gate, 9 checks
> cd Ask && python tools/derive_catalog.py --check           # the derived parts
> cd Ask && python validate_catalog.py                       # 343 statements, row counts
> python eval/gold/build_eval_questions.py --check           # the gold set
> cd Ask && python recall_eval.py --yes --k 30               # retrieval
> ```
> Run from a local mirror, never the Drive path (bootstrap §6).

---

## 0. For the PM — what this package did, in six lines

1. **The catalogue file is the source of truth.** The workbook is archived; a
   fresh import of it reproduces the committed catalogue exactly, and nothing in
   the build or the gates reads it any more.
2. **Every activity question now takes six filters it did not have** — plan type,
   status, focus area, theme, scheme, tied/untied — written as the same optional
   idiom, so an absent filter leaves the signed-off statement untouched.
3. **Almost two thirds of the catalogue can be broken down on request** —
   district-wise, per theme, year-wise, or as one plain total — and four
   duplicate templates were folded into their twins.
4. **A filter can hold several values**, so "tied spend, water vs sanitation"
   comes back as two rows rather than one summed figure, and "2024 to 2026" is
   read as the span it is.
5. **A live wrong answer was found and fixed on the way**: "for 2024 to 2025"
   was read as two years and answered for **2025-2026**.
6. **Every Eval_1 question now retrieves its template**, English recall is
   100%, and the catalogue is 343 templates — three fewer than it started with.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | `python prdw_gates.py` exits 0 with the three new checks | **PASS** — §7 |
| 2 | `derive_catalog.py --check` green; every changed statement absent-safe; workbook archived and unread | **PASS** — §2, §7 |
| 3 | All Eval_1 questions retrieve their expected id within K=30; English recall ≥ 95.4% | **PASS** — 52/52 in window, English **100%** (158/158) — §6 |
| 4 | 3× replay at or above WP-5's numbers; every Eval_1 row served or correctly clarified | **PASS, with one residual** — no row WP-5 got right regressed, three recovered, Eval_1 96.2-98.1%; #2005 is a hit in 1 of 3 replays — §8 |
| 5 | Template count reported, not higher than 346 + the T5 additions | **PASS** — 346 → **343** — §5 |

---

## 2. T0 — the catalogue file became the source of truth

`tools/build_catalog.py` is split in two and deleted:

* **`tools/derive_catalog.py`** — everything that must be DERIVED from the
  statements: the paraphrase block at the foot of every entry (between
  `# ── derived …` markers), `grouped_geo`, and `rerank_context.py`. It also
  refuses slot declarations that disagree with their own SQL, which is the
  check that replaces "the workbook said so".
* **`tools/import_workbook.py`** — the import half, which can only ever CREATE a
  fresh copy: it refuses the live directories and opens every output with
  exclusive-create. No gate and no test runs it.

`tools/migrations/m0_mark_derived.py` put the markers in, once. It adds comment
lines only, and asserts the executed catalogue dict is identical before and
after — so the embedded texts, the retrieval index and every statement were
unchanged by the switch, and the recall and row-count baselines carried across.

**The switch was proved rather than asserted.** A fresh import of the archived
workbook produced a catalogue equal to the committed one, entry for entry, and
an identical Test Report. Gate green 9/9 immediately after T0, with zero SQL
changes.

`AI_Chatbot_Questions.xlsx` now lives in `handoffs/archive/` with a README line
naming it as the 2026-08-13 sign-off. `eval/gold/check_harness_format.py` was
the one tool outside the backend still opening it; it now reads the catalogue.

> **The SME note, as the brief asked for it:** the ministry now audits the
> committed catalogue file and its git history rather than a spreadsheet. That
> file is the artefact that actually runs.

---

## 3. T1 — plan type, and T2 — the universal filters

### 3.1 `plan_type` (T1)

`v_activity` gains `plan_type` from `plan` via `plan_code`; `v_asset` and
`v_progress` inherit it the way they inherit `fiscal_year`. All 12,704
activities join (12,223 Main, 481 Supplementary), `plan_code` is unique, and the
column is appended last so no existing column moves. It is a validated
categorical loaded from the view, with the officer phrasings ("main GPDP",
"primary GPDP", "supplementary plan"), and it is **never defaulted**: absent
means both plan types, which is the signed-off row count.

### 3.2 M1, and what it decided (T2)

| outcome | count | what it means |
|---|--:|---|
| scripted | 238 | the six filters injected where the statement does not already use them |
| hand-edited | 7 | the roster shapes and the plan-status lookups — §3.3 |
| deliberately none | 2 | ALR-012, ALR-013 — §3.3 |
| nothing to add | 2 | PLU-003, PLU-004 already fix their own plan type |
| out of scope | 97 | the 85 SBM keyword templates (constraint 6), single-activity lookups, cashbook- and roster-only reads |

A dimension is skipped where the statement already uses it: in a predicate,
inside an aggregate, or **through a derived status flag** — `is_completed`,
`is_ongoing` and their siblings are `status_label` by another name, so IMP-005's
completion rate keeps meaning what it says (48 skips), a slot the template
already declares (24), an existing predicate on the column (9).

**One extension beyond the brief's letter, and why.** The brief scopes M1 to the
activity views. Three Eval_1 questions are plan-grain and name a plan type
("GPs that uploaded their main GPDP", "approved supplementary plans", "GPs with
a supplementary plan in Ganjam"), so `v_plan` templates get `$plan_type` — the
one of these six dimensions a plan row carries.

**A placement bug was caught before the commit.** An anchor line that also
closes its subquery (`… = $gp_name))`) put the new predicates OUTSIDE it;
PLN-043 and PLN-068 failed to bind, and a quieter version of the same mistake
could have landed a filter outside a subquery that still executed. The script
now moves the closing bracket, and the migration was re-run from the committed
T1 state so the committed script reproduces the committed result.

### 3.3 The nine M1 could not script

| id | what was done, by hand |
|---|---|
| PLN-012, PLU-001 | plan-status lookups: `$plan_type` on the plan row |
| ALR-009 | approved plan vs approved activities: `$plan_type` on the plan side |
| PLN-032, PLN-059, SCH-006 | "GPs with nothing under X": the filters go INSIDE the `NOT EXISTS`, so the question stays "no activity matching the filters" |
| AST-009 | the same, on the asset side |
| ALR-012, ALR-013 | **deliberately none.** They ask which GPs have no data in ANY module (activities, vouchers, and for ALR-013 plans); an activity-side filter would narrow one module of three and answer a question nobody asked |

### 3.4 Tied or untied

`tied_untied` is a new validated categorical (Tied / Untied / Other, loaded from
`v_activity`), with the officer phrasings "tied grant(s)", "untied funds",
"basic grant". Only the 2,101 administratively approved activities carry a
value, which is what "tied-fund expenditure" means anyway.

---

## 4. T3 — the breakdown slot

`$group_by` is written into each qualifying statement as a CASE over a FIXED
whitelist of that view's columns, so choosing a breakdown is binding a value and
never editing SQL.

| outcome | count |
|---|--:|
| scripted | 223 |
| left alone, each printed with its reason | 123 |

The three shapes that qualify: one whitelisted column (the column becomes the
CASE's ELSE, so absent the statement groups exactly as signed off), a run of
geography columns (the finest becomes the CASE; the others blank only when a
breakdown is chosen), and a plain total.

**Two findings the brief did not anticipate.**

1. **`grouped_geo` has 36 carriers, not 9.** 25 migrated; the 11 left are JOINs,
   a cashbook read and non-geographic groupings. So `grouped_geo` is **not
   retired**: it stays as the absent-slot reading, and a chosen breakdown is
   resolved at run time (`breakdown.effective_grouped_geo`).
2. **T3 and T5.3 contradict each other.** T3 says a template with a fixed
   breakdown keeps it when the slot is absent (which is what preserves its Test
   Report count); T5.3 says the same template with the slot absent gives the
   plain total. Both cannot hold, and constraint 2 (the row counts) is the
   harder one. So **`'total'` is an explicit whitelist value**, read from
   "total"/"overall" wording — and a question that names a dimension ("totals
   across all districts") still breaks down by it.

**A plain total keeps its single row over no rows at all.** The first run used
`GROUP BY 1`, and PLN-014 and two SBM counts lost their row — a count over
nothing answered "no records" where it used to answer "0". They now group by
`GROUPING SETS ((group_label), ())` with a HAVING that keeps exactly one of the
two sets.

### 4.1 The folds

| retired | survives as | with | rows, both ways |
|---|---|---|--:|
| BUD-018 | BUD-006 | `$group_by = 'focus_area'` | 25 |
| PLN-050 | PLN-024 | `$group_by = 'focus_area'` | 25 |
| PLN-051 | PLN-024 | `$group_by = 'focus_area'` | 25 |
| EXP-025 | EXP-014 | `$group_by = 'focus_area'` | 25 |

Each survivor was executed with the retired id's own Test Report parameters
BEFORE anything was written; `tests/data/retired_templates.json` records the
proof and the suite re-executes it. The retired questions and their hand
paraphrases moved into the survivor's hand block, so the phrasing still
retrieves.

### 4.2 At run time

The breakdown is read from a short phrase table ("district-wise", "by block",
"per theme", "for each focus area", "year-wise", "across districts", "which
GPs", "total"), never sent to the extractor — the same promotion WP-5 gave
`$date_range`, for the same reason: a model guessing a breakdown would silently
regroup a correct answer. `group_label` is renamed back to the column it holds,
a breakdown the statement cannot honour is dropped rather than faked, and the
echo names the breakdown that ran.

### 4.3 "Sector" (operator ruling, 2026-09-12)

Not an alias. Used as the BREAKDOWN with no value named — "which sector has the
best completion rate?" — the bot asks "focus area or LSDG theme?", before any
retrieval, with a chip for each reading (new clarification reason
`ambiguous_term`). A named value already says which dimension is meant, so "the
sanitation sector" and "water vs sanitation by sector" just answer.

---

## 5. T4 — lists and spans, and T5 — the new template

### 5.1 M3

| slot | list-capable on |
|---|--:|
| `$district_name` | 331 |
| `$date_range` | 317 |
| `$block_name` | 311 |
| `$plan_type` | 241 |
| `$theme` | 221 |
| `$focus_area` | 219 |
| `$scheme` | 207 |
| `$status` | 177 |

A slot is marked list-capable only where EVERY use of it was converted. The five
paired-year templates keep scalar years (their direction is pinned, D30.3), and
a required subject slot (PLN-049's focus area) stays scalar — both printed. A
scalar binds as a one-element list in all three binders, so every Test Report
sample still binds.

### 5.2 The year span, and the wrong answer it fixes

"2024 to 2026" is now the two fiscal years starting in 2024 and 2025; "2024 to
2025" is the single year 2024-2025. **Before this, "for 2024 to 2025" produced
2024-2025 AND 2025-2026, and a one-year slot took the LATER one — so Eval_1's
own phrasing was answered for 2025-2026.** Every Eval_1 row uses that phrasing.

A span naming a year the data does not hold binds nothing, so it is refused by
name rather than answered about the loaded half.

> **Left for the PM, not fixed.** The hyphen form has the same defect and a
> different history: `2023-2025` reads as 2023-24 **and 2025-26**, skipping
> 2024-25, and `tests/test_date_phrase.py` pins that reading. It is a deliberate
> WP-2 decision, so this package left it alone. If the span reading is right for
> "2024 to 2026" it is right for "2023-2025" too, and that is a one-line change
> plus a test update.

### 5.3 Several values

The extractor may return an array; each element is validated through the same
path and **one bad element refuses the whole list**, with the offending value —
not the one that happened to resolve — going to the ordinary "I couldn't find…"
question. A statement that takes one value at a time asks, with the values as
chips. A list of two values on one dimension sets the breakdown automatically,
so "water vs sanitation" lands in two rows; where nothing can separate them the
echo says "(the values combined)", and it always names both values.

Proved by execution: EXP-009 with the two-value list returns exactly what the
two scalar calls return, and PLN-001 with a two-year span equals the two
single-year calls.

### 5.4 T5 — the one new template, and the glossary

**PHY-006** — "which Gram Panchayats have expenditure recorded but no physical
progress" — is roster-shaped (LEFT JOIN from `gram_panchayat`), so the grain is
panchayats rather than activity rows. **11 GPs for 2024-2025.** Its caveat is
first-class: progress here is photo/GPS evidence uploaded against an activity,
not a stage model, and only 1,675 of 12,704 activities carry any upload.

The other T5 items needed no new template: the district-wise asset summary and
the plain totals both fall out of T3 (`$group_by = 'district'` / `'total'`).

Operator rulings of 2026-09-12, as built:

| question | ruling | as built |
|---|---|---|
| does *sector* mean focus area? | no — ask | §4.3 |
| *Sankalp themes* | answer from the six present, **no caveat** | the collective name never becomes one theme; it is a breakdown cue |
| *Swachh Bharat* | alias for Sanitation **with a caveat** | appended verbatim beside the template's own caveat (D3) |
| which required slots relax | PLN-031 **and** PLN-032 | "which GP planned the most activities?" answers across all themes; PLN-032 with no theme lists the GPs with nothing under ANY LSDG theme, excluding the activities that map to no theme |

**Template count: 346 → 342 (four folded) → 343 (PHY-006).**

---

## 6. T6 and T7.1 — the gold set, and retrieval

`eval/gold/eval1_officer.jsonl` holds the 26 distinct Eval_1 questions, each as
its canonical phrasing and as the phrasing with the lowest lexical overlap to
its template's wording: **52 rows**, gold set 223 → 275, recall CSV 185 → 237.

> The brief says 28 questions. The file holds 371 rows in 28 blocks, and two
> blocks repeat an earlier question, so 26 are distinct. **No 2026-09-12
> matching table exists anywhere in the repo**, so the expected ids were rebuilt
> from the catalogue; each row records the gap it came from. The two authoring
> defects the brief names were fixed first.

### 6.1 Recall@30, before T2 and after T4

| | before | after |
|---|--:|--:|
| index | 376 entries, 2,197 vectors | 373 entries, 3,457 vectors |
| **overall recall@30** | 93.6% (220/235) | **96.6% (229/237)** |
| **English** | 100% (106/106) + 86.0% (43/50) Eval_1 | **100% (158/158)** |
| code-mixed | 100% (49/49) | 100% (49/49) |
| Odia transliterated | 100% (13/13) | 100% (13/13) |
| Odia script | 52.9% (9/17) | 52.9% (9/17) |
| **Eval_1 rows in window** | 43/50 (86.0%) | **52/52 (100%)** |
| gold rank p90 | 18 | **9** |
| crowding: extra vectors walked to reach 30 ids | mean 22.4, max 94 | mean 32.2, max 145 |

Five Eval_1 rows were still outside the window after T4, on three templates, and
each was the case the brief predicted: **a universal slot is invisible to
retrieval unless a paraphrase mentions it.** STS-003 never said "Swachh Bharat"
or "sanitation", PLN-002 never said "supplementary", PLN-024 never said
"breakdown". Six hand paraphrases — two per template — put all five in window.

**The crowding rose, and that is the price paid.** Every template now carries a
line per dimension it can filter on, so the retriever walks ~32 raw vectors
instead of ~22 to collect 30 distinct templates. Recall improved on every
register that was measured, and the gold rank at p90 halved, so the extra
vectors are buying more than they cost — but this is the number to watch if the
catalogue grows again. The duplicate-question crowding the harness was written
to watch is unchanged: 4 groups, 9 entries where 4 would do.

Odia script is unchanged and remains operator-deferred (F2): these paraphrases
are English, and they do nothing for it.

---

## 7. T7.3 — the gates

`python prdw_gates.py` exits 0 with 9 checks. Check 3 is now
`derive_catalog.py --check` in place of the workbook drift check, and check 9
gained the three the brief asks for:

```
  [PASS] 9. Static invariants
          date_filter unset on all 343 templates
          no $tag$ dollar quoting in any sql_template
          all 252 Partial templates carry a caveat
          extraction sentinel distinguishes failure from empty
          spend guard present on 3 paid harnesses
          pmkisan_gates.py deleted
          WP-6 slots bound ABSENT in the Test Report: 669
          $group_by whitelisted on all 219 templates that offer it
          plan_type present on v_activity, v_asset and v_progress
```

`tests/test_wp6_catalog_dimensions.py` carries 45 tests grouped by task, so a
failure names the promise it broke.

---

## 8. T7.2 — the replay, and the two defects it found

### 8.1 What the first replay found, which the tests did not

Three replays ran on the finished package (275 questions each, 2,349 calls).
Two rows that WP-5 answered now ASKED, stably, 3 of 3 — and both were WP-6's
own doing rather than retrieval drift:

```
#1402  "What percentage of the sanctioned budget is tied and untied in 2024-25?"
       WP-5: hit (BUD-005)      WP-6: clarify — "Tied or Untied?"
#1522  "Tied aur untied fund se 2024-25 me kitna kharcha hua?"
       WP-5: hit (EXP-008)      WP-6: clarify — "Tied or Untied?"
```

**The cause is T2 and T4 meeting.** T2 gave these templates a `$tied_untied`
slot, so the extractor — which had nothing to fill before — now reads "tied and
untied" and returns BOTH values. `$tied_untied` is not list-capable, so T4's
"this question takes one value at a time" question fired. Both templates
**report the split**: BUD-005 gives the tied and the untied share side by side,
EXP-008 the expenditure under each. The bot was asking which half of an answer
it already had.

**The fix, in one rule.** A multi-value list on a slot that CANNOT hold a list,
where the statement already reports one row per value of that column, is not a
filter and not a question: the slot is left unbound and the statement answers as
it always did. A list-capable slot never reaches that rule — "water vs
sanitation" still binds both values, which is the comparison T4 exists for. (The
first version of this fix was too broad and swallowed exactly that comparison;
the custom replay caught it before the final run.)

Two Eval_1 rows failed for a different reason, and it is the one the brief
predicted in its §3: **the reranker never sees paraphrases.** A hand paraphrase
put STS-003's "completed sanitation activities under Swachh Bharat" into the
candidate window, and the reranker — which sees a template's own question and
its "↳" description — passed it over for three SBM entries. Same for "activities
within the sanitation category", which went to PLN-052 (a RANKING across focus
areas) instead of PLN-049 (a count for one). Both now carry a
`_DISAMBIGUATION` note, which is what that table is for.

> **The lesson worth keeping.** 639 tests, three gates and a recall harness all
> passed on a build where two ordinary questions had started asking instead of
> answering. Only the replay sees the extractor and the reranker doing their
> jobs together, which is exactly why the brief puts it at the end.

One more thing the replay showed, fixed the same way: seven pre-existing
questions echoed a breakdown they already had ("Which blocks have the most
pending approvals? (broken down by block)"). The answers were identical; the
echo now says it only when the breakdown differs from the statement's own.

### 8.2 The numbers

Three replays of the 275-row gold set, on the finished package (`--tag wp6b`).

| behaving correctly | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| **all 275 rows** | **90.5%** | **90.9%** | **89.8%** |
| the 223 rows WP-5 ran | 89.2% | 89.2% | 88.3% |
| WP-5, same rows, as reported | 88.3% | 88.8% | 89.2% |
| **the 52 Eval_1 rows** | **96.2%** | **98.1%** | **96.2%** |
| confidently wrong | 1.8% (5) | 1.8% (5) | 2.2% (6) |
| asked or declined | 7.6% (21) | 7.3% (20) | 8.0% (22) |

**Gate item 4, honestly.** Run for run the two packages are inside each other's
noise (WP-6 is ahead on two replays and 0.9 points behind on the third; the mean
is 88.9% against 88.8%). The number that is not noise is the row-by-row one:
**on a majority-of-three basis no row that WP-5 got right is now wrong, and
three that it got wrong are now right** —

```
#1026  "Sanitation ke under 2024-25 me Andhrua me kitni activities plan hui?"
       clarify / wrong_template / hit   ->  hit 3/3
#1202  "and household ones?"            ->  clarify_gold_offered 3/3
#1624  "and for 2023-24?"               ->  hit / hit / wrong_entities
```

The confidently-wrong rate is at or below WP-5's on every replay, which is the
number the pilot decision rests on.

**Every Eval_1 row is served or correctly clarified except one**, and that one
is unstable rather than wrong:

```
#2005  "How many sanitation activities have been completed under Swachh Bharat
        for 2025 to 2026?"     hit (STS-003) / clarify / clarify
```

Its template is in the candidate window on every run; the reranker takes it once
in three and otherwise offers three SBM entries. This is the same shape WP-5
reported for BEN-003 and named exactly: **in-window is not the same as served.**
It is a selection question rather than a retrieval one, the outcome is a
clarification rather than a wrong answer, and the fix would be more
`_DISAMBIGUATION` wording — measured on a replay, not argued.

**Spend.** 2,349 calls for the first replay, 2,342 for the final one, ~67
embedding calls across the index rebuilds and the two recall runs, and ~40 calls
for two custom replays of the affected rows. Every one through `confirm_spend`.

---

### 8.3 Stability

| | verdict flips across the three replays | route flips |
|---|--:|--:|
| all 275 rows | 9.1% (25) | 10.2% (28) |
| the 223 rows WP-5 ran | **5.4% (12)** | 5.8% (13) |
| the 52 Eval_1 rows | 25.0% (13) | 28.8% (15) |

WP-5 measured 4.5% verdict flips on its own rows, so **the catalogue's existing
questions are about as stable as they were** (5.4%). The instability is
concentrated in the NEW rows: a quarter of the Eval_1 phrasings flip between an
answer and a clarification between runs. That is what one would expect of
questions chosen for being unlike the catalogue's wording — they sit near the
ambiguity threshold — and it is the honest reading of the Eval_1 numbers above:
96-98% correct, but not the same 96-98% each time.

---

## 10. What the next package should know

1. **The hyphen year form has the same defect T4 fixed.** `2023-2025` reads as
   2023-24 **and 2025-26**, skipping 2024-25, and `tests/test_date_phrase.py`
   pins that reading as a WP-2 decision. If the span reading is right for "2024
   to 2026" it is right here too — a one-line change plus a test update, and a
   PM ruling first.
2. **Crowding is the number to watch.** Every template now carries a line per
   dimension it can filter on: the retriever walks ~32 raw vectors instead of
   ~22 to gather 30 templates (max 145). Recall improved anyway and the gold
   rank at p90 halved, so the lines earn their place today — but the margin is
   thinner than it was, and the next batch of paraphrases should be measured
   against this number rather than added on the argument that more surface
   cannot hurt.
3. **In-window is not the same as served, still.** #2005 retrieves STS-003 every
   run and is served it once in three. The lever is `_DISAMBIGUATION` wording,
   and the measurement is a replay.
4. **`grouped_geo` is not retired.** 25 of its 36 carriers migrated to
   `$group_by`; the remaining 11 are JOINs, a cashbook read and non-geographic
   groupings. Both mechanisms are live, and `breakdown.effective_grouped_geo`
   is where they meet.
5. **The "sector" question is a ruling, not a measurement.** It asks before any
   retrieval, so it costs nothing and can never answer about the wrong
   dimension — but whether officers find it helpful or pedantic is a pilot
   question.
6. **Odia script is untouched** (52.9%, F2, operator-deferred): these
   paraphrases are English and do nothing for it.
7. **The replay is the only thing that sees the whole machine.** 639 tests,
   nine gates and a recall harness all passed on a build where "what percentage
   of the budget is tied and untied?" had started asking which one the officer
   meant. Budget for a replay after any package that touches slots or
   paraphrases.

---

## 9. Compliance with the brief

| constraint | status |
|---|---|
| The catalogue file is the source of truth after T0 | Yes — §2 |
| The Test Report row counts remain the regression contract | Yes — 343 statements, 0 mismatches, on every task |
| Derived artefacts stay generated from the SQL | Yes — paraphrase blocks, `grouped_geo`, `rerank_context.py`; `--check` is gate 3 |
| Bound values never interpolated into SQL | Yes — every filter binds a parameter; `$group_by` is a CASE over a fixed whitelist |
| `$p IS NULL OR` is the only optional idiom (D2) | Yes, extended to `IN (SELECT UNNEST($p))` for list slots, with the same guard |
| SBM excluded from the universal-slot migration | Yes — 85 templates, asserted by a test |
| Ask-side paths only (D14); Drive `.duckdb` read-only; `.env` untouched | Yes — everything ran from `C:\dev\odisha-wp6` |
| LLM spend only in T7 | **Disclosed exception:** the index had to be rebuilt after each catalogue change for gate 8 to be measurable — 9 embedding calls a time, 27 in total, plus 40 for the two recall runs. Every one through `confirm_spend` |

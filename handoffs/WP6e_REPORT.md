# WP-6e — The reranker sees the phrasings that found each candidate: REPORT

> ## Where everything is
>
> ```
> Ask/query_router/vector_retriever.py        T1 — retrieve_with_examples; vec_examples (the phrasing as written, None for the question)
> Ask/query_router/reranker.py                T2 — build_messages; the "found by:" block; _EXAMPLES_RULE (only when examples are passed)
> Ask/query_router/config.py                  T2 — RERANK_EXAMPLES_PER_CANDIDATE = 4 (0 = WP-6d)
> Ask/query_router/router.py                  T2 — _route_vector reads the switch at call time
> Ask/rerank_eval.py                          T2 — --examples N
> Ask/run_custom_eval.py                      T2 — the top-3 trace also wraps retrieve_with_examples
> Ask/tests/test_wp6e_reranker_examples.py    T3 — 17 tests; two older test stubs accept the new keyword
> handoffs/WP6e_stage1.csv/.jsonl             T4 stage 1 — the 12 rows
> handoffs/WP6e_eval1_replay.csv/.jsonl       T4.1 — Eval_1, graded, diffed against WP-6d
> handoffs/WP6e_gold_replay_run1.csv/.jsonl   T4.2 — gold, with WP-6d's verdict and WP-6's three beside each row
> handoffs/WP6e_pilot_replay.csv/.jsonl       T4.3 — the 44 pilot rows
> handoffs/WP6e_rerank_calls.jsonl            every reranker call in the four runs: candidates, the phrasings shown,
>                                             pick, near-misses, prompt tokens (llm_usage), wall time
> handoffs/WP6e_paired_latency.json           the paired switch-0 / switch-4 timing check (§6)
> ```
>
> **Committed, not pushed.** `a8072b7` T1 (with the brief), `1d849cb` T2, `a446d12` T3,
> and T5's commit carrying this report and the runs. **The switch is committed at 4**:
> neither stop rule tripped (gold confidently wrong 6, not above WP-6d's 6; Eval_1
> incorrect 2, not above 4). **The operator decides adoption**; rollback is
> `RERANK_EXAMPLES_PER_CANDIDATE = 0`. Left for the operator as before: the PM's
> `handoffs/PROJECT_PLAN.md` edit, the untracked `handoffs/WP6b_eval1_replay_notes_off.csv`, and `Ask/bench/`.
>
> Mirror: `C:\dev\odisha-wp6e`, a plain copy of `Ask/` at `3721862` plus WP-6d's search
> index (byte-identical to the WP-6d mirror apart from its run outputs).

---

## 0. For the PM — what this package found

1. **Built as briefed.** With the switch at 0 the reranker input is WP-6d's byte for
   byte (checked on all 237 cached recall queries against the WP-6d mirror's own code,
   and pinned by a test over every indexed id). The 30 candidates, their order and
   scores are identical with the switch on or off (same 237 queries; also tested).
2. **Cost is as the PM measured; speed does not change.** +1,121 prompt tokens per
   reranker call in the gold replay (the PM's offline figure was +1,121), +1,272 in
   Eval_1. That is about +20% on the reranker call. Paired against the same
   candidates, the reranker was **not slower** (1.33 s against 1.40 s mean).
3. **The headline numbers barely move; which rows are right does.**

   | run | WP-6d | WP-6e (switch at 4) |
   |---|---|---|
   | Eval_1 (302 gradable): correct / asked, right chip / asked, wrong chips / wrong | 293 / 5 / 0 / 4 | **286 / 14 / 0 / 2** |
   | gold (275): behaving correctly / confidently wrong | 248 (90.2%) / 6 | **249 (90.5%) / 6** |
   | pilot (44): correct / asked / wrong | 38 / 5 / 1 | **40 / 3 / 1** |

4. **What it fixed.** "Delayed GPDP submissions" now reaches PLN-007 wherever it
   appears (Eval_1 315 and 321, gold #2046, stage 1). It does that through the
   existing "behind / lagging" phrasings, so the WP-6d §9.3 phrasing patch may not be
   needed. Eval_1 211 now answers PLN-024 instead of PLN-072. Rows 42 and 49 ("compare
   tied fund spending between water and sanitation") no longer get TRD-002 in the
   Eval_1 run. They ask instead, with EXP-009 as the first chip; row 49 still got
   TRD-002 once in stage 1.
5. **What it cost: more asking in Eval_1, and it comes from one visible cause.** In
   Eval_1 the reranker declined 16 times, against 8 in WP-6d. Eleven rows went from
   answered to asked (and four the other way). Nine of the eleven are in two groups:
   "total activities in main GPDPs" (141–149) and "GPs with zero-cost activities"
   (12, 186, 188, 193). The other two (7, 174: planned-budget totals under BUD-006)
   have the same shape. In each, the phrasings
   shown under the right template are **generated filter variants that describe a
   narrower question** than the officer's. PLN-024 shows "How many activities are
   planned under **each GPDP theme** in a given block…" four times over, so the
   reranker decides it cannot give an overall total. Every one of these asks offered
   the right template on its chips (asked with wrong chips: 0). §3.2 has the detail.
6. **Look-alike families.** The SBM, plan-versus-cashbook and uploaded-versus-approved
   families lost 2 rows and gained 6 (§5). The one loss that matters is gold #1214:
   "toilet sarichi" (Odia, *finished*) was answered with SBM-SI-013 (ongoing) instead
   of SBM-SI-014 (completed). The shown phrasings did say "completed" and "ongoing"
   correctly. The model misread the Odia word, not the listing.
7. **Recommendation: keep the switch at 4, and give the "found by" lines one
   follow-up** (§8). It cut wrong answers in Eval_1 (4 → 2), held gold, fixed the
   "delayed" family without a patch, and costs no time. Its one clear weakness is
   fixable at the source: many of the phrasings shown are machine-generated
   filter variants that add near-duplicate lines. By a simple pattern (a phrasing
   ending ", for a given …" / ", in the main GPDP" and the like) that is 33% of the
   lines shown in Eval_1 and 22% in gold. The pattern misses variants without a
   comma, such as "…in a given block…", so the true share is higher.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | Switch at 0 byte-identical to WP-6d's reranker input; candidate list identical in both states; full suite and `prdw_gates.py` green | **PASS** — 237 / 237 recall queries: messages at 0 byte-identical to the WP-6d mirror's `rerank`, candidates identical; system-prompt hash and every indexed id's listing pinned in tests; **GATE GREEN 9/9, 761 tests** (22 skipped without the live key); `validate_catalog.py` 343 / 0; derive in step |
| 2 | Stage 1 reported in full | **PASS** — §2 (all 12 calls returned valid JSON, finish `stop`, none timed out) |
| 3 | Eval_1, gold and pilot complete, diffed row by row against WP-6d, with the look-alike list and clarification counts | **PASS** — §3, §4, §5; the gold replay was split into parallel parts partway through, at the operator's request (§4.1) |
| 4 | Tokens and latency reported; mean added input within ~20% of +1,121 | **PASS** — gold +1,121, Eval_1 +1,272 (+13%), pilot +1,186, offline recall set +1,170 (§6) |
| 5 | No catalogue, paraphrase, note or threshold change; brief and report committed, one commit per task, not pushed | **PASS** — `derive --check` green, 343 / 0, `rerank_context.py` / `_DISAMBIGUATION` untouched |

---

## 2. Stage 1 — the rows the reranker has been getting wrong

Switch at 4, one run (`WP6e_stage1.*`). "Stage 2" is the same row in its full
replay, run later, and shows how much of the change is run-to-run variation.

| row | question | WP-6d | stage 1 | stage 2 | reranker (stage 1) |
|---|---|---|---|---|---|
| 1002 | how much came from Own Funds vs SFC in Khordha in 2024-25 | asked | asked | asked | no_match → FND-004 / FND-005 / SCH-010 |
| 1007 | What share of the sanctioned budget came from SFC and 15th Finance Commission in 2024-25? | asked | asked | **BUD-003** | no_match → BUD-003 / BUD-004 / FND-001 |
| 1009 | How much of the 2024-25 sanctioned amount is from the State Finance Commission? | asked | **BUD-002, correct** | asked | BUD-002 |
| 1032 | Which focus areas with at least 50 activities have the lowest completion rate in 2025-26? | asked | **IMP-009, correct** | **correct** | IMP-009 |
| 1043 | What is the count of planned activities in Barpali in 2024-25? | asked | asked | **PLN-024, correct** | no_match → PLN-024 / PLN-027 / PLN-028 |
| 1044 | count of planned activities in Attabira in 2025-26 | PLU-005 refusal | PLU-005 refusal | PLU-005 refusal | **no_match** → PLN-044 / PLN-024 / PLN-049; the refusal is served by D28.5 rank-0 precedence, not the reranker |
| 42 | Compare tied fund spending between water and sanitation for 2024 to 2026. | TRD-002, wrong | **asked, EXP-009 first chip** | asked | no_match → EXP-009 / EXP-011 / TRD-002 |
| 49 | …for 2022 to 2023. | TRD-002, wrong | TRD-002, wrong | **asked** | TRD-002 |
| 211 | What is the thematic distribution of planned activities for 2021 to 2022? | PLN-072, wrong | **PLN-024, correct** | **correct** | PLN-024 |
| 315 | Identify districts with delayed GPDP submissions for 2024 to 2026. | PLN-023 refusal | **PLN-007, correct** | **correct** | PLN-007 |
| 17 | How many sanitation activities have been completed under Swachh Bharat for 2025 to 2026? (WP-6 §5, → STS-003) | correct | correct | correct | STS-003 |
| 219 | Number of activities proposed within the sanitation category for 2024 to 2025. (WP-6 §5, → PLN-049) | correct | correct | correct | PLN-049 |

**What the reranker was shown** (retrieval rank in brackets; up to four phrasings,
best first):

* **1007 / 1009 — BUD-003 (0):** "What share of the sanctioned budget came from SFC and
  the 15th Finance Commission?" · "How much was sanctioned as tied vs untied in
  2024-2025?" · (1009 also) "How much of the sanctioned amount came from a given
  scheme in a given year?". The second line is BUD-003's own tied/untied wording, and
  its "↳" says tied/untied. The reranker weighs that against the scheme phrasings and
  goes both ways from run to run. **BUD-002 (9 / 12):** "How much funding came from
  each source in 2024-2025?" · "How much funding is available from each funding
  source (CFC, SFC, Own Funds, MGNREGS, etc.)…".
* **1002:** neither BUD-003 nor BUD-002 is among the 30 candidates. Rank 0 is SCH-009
  ("status breakdown under XV Finance Commission in Khordha"). This is a search gap;
  showing phrasings cannot fix it.
* **1032 — IMP-009 (0):** "Which focus area has the lowest completion rate in a given
  year?" and three filter variants of it.
* **1043 / 1044 — PLN-024 (5 / 7):** "How many activities are planned under each
  focus area in Bhubaneswar in 2024-2025?". **PLN-049 (22 / 29):** "How many
  activities are planned under Sanitation in Andhrua in 2024-2025?". **Rank 0:**
  STS-003 for 1043 (shown "How many Bhubaneswar activities are WORK ONGOING in
  2024-2025?"), PLU-005 for 1044 (shown "How many activities in Attabira are
  delegated to another panchayat tier…"). 1044's refusal is the D28.5 precedence rule
  firing on a rank-0 refusal after the reranker declined. WP-6d §9 already hands that
  rule back.
* **42 / 49 — EXP-009 (0):** "How much tied-fund spending went to Sanitation in
  2024-2025?" · "How much tied-fund expenditure was incurred under a given focus
  area in a given year?" · two filter variants. **TRD-002 (11 / 14):** "Compare
  theme-wise cost and spend between 2023-2024 and 2024-2025." The word "compare" in
  TRD-002's phrasing still pulls on 49.
* **211 — PLN-072 (0):** "Are planned activities balanced across themes…" ×4 variants.
  **PLN-024 (7):** "Show the breakdown of planned activities by theme in a given
  year." · "Theme-wise breakdown of all planned activities." This is the clearest case
  of the phrasings doing their job.
* **315 — PLN-007 (4):** "Which districts are lagging on GPDP submission…" ·
  "…behind on GPDP submission…" · "…lowest GPDP submission rate…" ×2. **PLN-023
  (2):** "Which Districts consistently experience delays in GPDP **approvals**…". The
  WP-6d T4 phrasings reach the reranker and settle the "delayed" row.
* **17 — STS-003 (0)** and **219 — PLN-049 (6)**: already right in WP-6d, still right.

**No row failed to return valid JSON or timed out**, so stage 2 went ahead as briefed.

---

## 3. Eval_1 — `WP6e_eval1_replay.csv`

314 rows, ten parallel parts (WP-6d's split), 0 errors, graded by `grade_eval1.py`
unchanged, `--baseline WP6d_eval1_replay.csv`.

| outcome | WP-6d | WP-6e | share of 302 |
|---|--:|--:|--:|
| correct | 293 | **286** | 94.7% |
| asked, right template offered | 5 | **14** | 4.6% |
| asked, right template NOT offered | 0 | 0 | |
| incorrect | 4 | **2** | 0.7% |
| defective row | 12 | 12 | |

### 3.1 Every row that moved (21)

| row | WP-6d → WP-6e | served now | reading |
|---|---|---|---|
| 14, 45, 171, 321 | asked → correct | PLU-008, EXP-009, BUD-006, PLN-007 | |
| 211, 315 | wrong → correct | PLN-024, PLN-007 | §2 |
| 42, 49 | wrong → asked | EXP-009 first chip | §2 |
| 7, 174 | correct → asked | BUD-006 first chip | §3.2 |
| 141, 144, 145, 148, 149 | correct → asked | PLN-024 first chip | §3.2 |
| 12, 186, 188, 193 | correct → asked | PLU-008 / DQY-007 on the chips | §3.2 |
| **44** | correct → **wrong** | TRD-008 | "What is the **sector-wise** expenditure of tied funds for water and sanitation" — TRD-008's one phrasing is "approved cost and expenditure **sector-wise** in a given district…, funded from tied grants" |
| **281** | correct → **wrong** | IMP-005 | "sector" group, ruled to ASK. "Identify the sector with the highest…" slips past the sector clarification (known, WP-6c brief §0); WP-6d's reranker declined, which counted as correct; this run picked IMP-005 (completion rate per theme) |

By group: "total activities in main GPDPs" 12 → 7 correct; "GPs with zero-cost
activities" 17 → 14; "districts behind on GPDP submission" 9 → **11** (all);
"planned activities by theme" 11 → **12**; "tied spend water vs sanitation" wrong
2 → 1. No other group moved by more than one row.

### 3.2 Why the new asks happen

The reranker declined on all eleven rows that went from answered to asked. Each
time the right template was its **first** near-miss: at retrieval rank 0 or 1 in
eight of them, and rank 13–21 in the other three (144, 145, 149, where EXP-005 ranks first).
What it was shown under that template:

* **141 "How many activities are scheduled in the main GPDPs overall…" — PLN-024:**
  "…planned under each GPDP theme in Andhrua in 2024-2025?" · "…under each GPDP
  theme in a given block in a given year?" · "…in a given district…" · "…in a given
  gram panchayat in a given year, in the main GPDP?"
* **7 "Provide the sum of the planned budget outlay across main GPDPs…" — BUD-006:**
  "How much planned expenditure goes to each GPDP theme…" · "…to each focus area…" ·
  "…allocated to each GPDP theme in a given year, in the main GPDP?" · "…to each
  GPDP theme in a given year?"
* **12 / 188 "GPs whose planned activities have an estimated cost of zero" — PLU-008:**
  "How many no-cost activities are planned in a given gram panchayat for a given
  year?" (one line; its catalogue question says the same).

The catalogue question and "↳" of PLN-024 and BUD-006 are already per-theme with a
breakdown slot that gives a total. The phrasings repeat the per-theme reading four
times, and the reranker then judges that the template cannot give "overall" or "sum".
The new rule ("decide by what the candidate measures") did not outweigh four lines
all saying "each theme". **Most of those lines are the WP-6 filter variants** ("…,
in the main GPDP?", "…, for a given block?", "…, for ongoing activities?"). They were
written to be *searched*, and they crowd out the handful of hand-written phrasings.

### 3.3 Clarifications

| where the ask came from | WP-6d | WP-6e |
|---|--:|--:|
| reranker declined (`ambiguous_templates` after a rerank, and `no_match`) | 8 | **16** |
| before the reranker: "sector" (`ambiguous_term`) | 7 | 7 |
| before the reranker: retrieval too close to call | 1 | 1 |

(WP-6d's split is inferred by assuming the same rows reach the reranker, which holds
because retrieval is unchanged.) In Eval_1 the switch made the reranker **less**
decisive, not more. The asks it added all offered the right template.

---

## 4. The gold replay — `WP6e_gold_replay_run1.csv`

### 4.1 How it was run

The first 123 rows ran sequentially, as briefed. The operator then asked why the
queries were not run in parallel. The replay was stopped and the remaining 152 rows
ran as **eight parallel parts**, each cut where the next question starts a fresh
session. The 13 follow-up rows that reuse the previous row's session each stayed in
the same part as the row before them. No row was run twice; all 275 in file order,
0 errors, graded by `grade_full_eval.py` unchanged. The first 123 rows' usage file
was lost when that process was stopped. Their reranker calls are in the call log, so
§6 is complete; only the §9 spend line for those rows is estimated.

### 4.2 Numbers

| | WP-6 run 1 / 2 / 3 | WP-6d | **WP-6e** |
|---|--:|--:|--:|
| behaving correctly (hit + asked with the gold chip + asked as ratified) | 90.5% / 90.9% / 89.8% | 90.2% (248) | **90.5% (249)** |
| confidently wrong (wrong template + wrong values) | 5 / 5 / 6 | 6 | **6** |

### 4.3 Every row that moved (11)

| row | WP-6d → WP-6e | reading |
|---|---|---|
| **#1214** "2024-2025 re kete anganwadi o school re toilet sarichi?" | hit → **wrong** (SBM-SI-013) | *sarichi* = finished. Shown under SI-013: "…toilets and handwash units in AWCs and schools are **ongoing**…"; under SI-014 (rank 3): "…have been **completed**…". The listing was right, and the model picked ongoing |
| **#1415** "2024-2025 re Andhrua ra kama pain tied o untied panthi kete bhaga…" | hit → **wrong** (BUD-005) | FND-001 at rank 0 showed "What is Andhrua's tied vs untied split in 2024-2025?"; the reranker still picked BUD-005 (sanctioned budget share) with FND-001 as first near-miss. WP-6 had this row wrong on majority too (WP-6d report §8.3) |
| **#1852** Odia "assets created by asset category in Bhubaneswar block" | asked → **wrong** (AST-006) | the gold AST-002 is **not among the 30 candidates**; AST-006 ("How many immovable assets were created in Bhubaneswar…") was picked instead of declining |
| #1505 Odia "which focus area has the highest actual expenditure" | wrong (EXP-018) → asked | gold EXP-028 not among the candidates; now declines instead of guessing |
| #1624 "and for 2023-24?", #1701 "…zero expenditure 90 days after sanction" | wrong values → hit | extractor variation (WP-6d §8.3 named both as noise); nothing the reranker sees |
| #1232 "2024-25 me kitne compost pit complete hue?" | asked with gold chip → hit | SBM-SWM-005 shown "How many community compost pits have been completed…" |
| #1521 "expenditure Andhrua?" | asked → asked as ratified (partial) | chips now carry EXP-001 |
| #1605, #2010, #2046 | asked with the gold chip → hit | STS-003, EXP-009, PLN-007 answered instead of offered |

**Against WP-6's three verdicts:** WP-6 majority right and this run not: #1214 (above)
and #1202 "and household ones?" (asked, as in WP-6d). WP-6 majority not right and this
run right: G1613 (WP-6d's ruling) and #2005 (Swachh Bharat completed).

**Clarifications:** `ambiguous_templates` 24 → 20 (after a rerank about 13 → 9;
before the reranker 11 → 11); every other reason unchanged (missing_parameter 4,
broad_question 3, no_match 2, known_unanswerable 1, tier_collision 1,
ambiguous_term 1). In gold the shift went the other way from Eval_1: fewer asks,
three of them now correct answers.

---

## 5. Look-alike families

The families the "↳" lines protect: **SBM keyword** (every `SBM-*` template: compost
pits, segregation, IHHL, AWC/school toilets); **plan versus cashbook** (every `EXP-*`
plus the cashbook entries BUD-002, BUD-004, EXP-024, ALR-012, ALR-013); **uploaded
versus approved** (PLN-001 / PLN-002 and the other upload/approval questions). A row
counts if its expected template, or the template served in either run, is in a
family: 79 Eval_1 rows, 99 gold rows, 12 pilot rows.

**Every such row that changed outcome:**

| run | row | family | WP-6d → WP-6e | |
|---|---|---|---|---|
| gold | #1214 | SBM keyword | hit → **wrong** (ongoing for completed) | worse |
| gold | #1232 | SBM keyword | asked (partial) → hit | better |
| Eval_1 | 44 | plan vs cashbook | correct → **wrong** (TRD-008) | worse |
| Eval_1 | 42 | plan vs cashbook | wrong → asked, EXP-009 first chip | better |
| Eval_1 | 49 | plan vs cashbook | wrong → asked, EXP-009 first chip | better |
| Eval_1 | 45 | plan vs cashbook | asked → correct (EXP-009) | better |
| gold | #1505 | plan vs cashbook | wrong → asked | better |
| gold | #1521 | plan vs cashbook | asked → asked as ratified | better |
| gold | #2010 | plan vs cashbook | asked with gold chip → hit | better |
| gold | #2046 | uploaded vs approved | asked with gold chip → hit (PLN-007) | better |

No pilot row in a family changed. No served answer anywhere crossed between plan
and cashbook, between uploaded and approved, or between two SBM keyword patterns.
#1214 stays within one pattern (AWC/school toilets) but picks the wrong status.

---

## 6. Tokens and speed

Prompt tokens are the provider's own count from `llm_usage`, per reranker call. The
"at 0" column is the **same calls** with the "found by" lines and the rule removed,
recounted with `tiktoken o200k_base`. Its gold mean is 6,167, exactly WP-6d's metered
gold figure (1,554,017 / 252), so the reconstruction matches.

| run | calls | at 0: mean / p90 | **at 4: mean / p90** | added, mean | latency at 4: mean / p90 |
|---|--:|--:|--:|--:|--:|
| gold | 252 | 6,167 / 7,641 | **7,288 / 8,564** | **+1,121** | 1.20 s / 1.59 s |
| Eval_1 | 306 | 6,073 / 6,813 | **7,345 / 7,838** | +1,272 | 1.38 s / 1.88 s (10 processes at once) |
| pilot | 44 | 5,847 / 6,105 | 7,033 / 7,692 | +1,186 | 1.25 s / 1.80 s |
| stage 1 | 12 | 6,098 / 6,642 | 7,211 / 7,634 | +1,113 | 1.89 s / 2.67 s |
| offline, 237 recall queries (tiktoken both sides) | — | 6,145 | 7,315 | +1,170 (p90 +1,755, max +2,142) | — |

Against the PM's +1,121: gold matches exactly; Eval_1 is 13% above, because its
questions pull more phrasings per call (Eval_1 49.9 on average, up to 85; gold 44.7,
up to 97; the offline recall set 47.2, up to 86). 52 of the added tokens are the one
new rule in the system prompt.

**Speed, measured paired** (`WP6e_paired_latency.json`). WP-6d recorded no
per-call latency, so "before" could not be read off its runs. 63 Eval_1 questions
(every fifth) were each retrieved once, and the same candidates were reranked twice,
at 0 and at 4, alternating which went first, run alone:

| | at 0 | at 4 |
|---|--:|--:|
| latency mean / median / p90 | 1.40 / 1.33 / 1.98 s | **1.33 / 1.27 / 1.79 s** |
| prompt tokens mean / p90 | 6,043 / 6,696 | 7,325 / 7,843 |
| reasoning tokens, mean | 86 | 68 |
| same pick | | 59 / 63 |
| declined | 5 | 3 |

At 4 the reranker was slower on 29 of 63 questions and faster on 34, a mean
difference of −0.07 s. The extra input costs no measurable time, and the model
reasons slightly less. The cost is the input tokens: about +20% on the reranker
call.

---

## 7. Decisions I made that the brief did not

1. **Where the walk stops.** The brief says to stop "when the (k+1)-th distinct
   template would begin", and calls that "exactly the set `crowding_extra` counts".
   The two differ slightly. `crowding_extra` stops at the vector that brings in the
   30th template; the brief's rule keeps walking through further phrasings of the 30
   until the 31st appears. I followed the rule the brief states and tests (it is also
   the one that makes "if four phrasings of one template outrank another template's
   best, all four are shown" hold). Offline on the 237 recall queries this walks 1.0
   more vector on average (max 13) and shows 0.47 more phrasings per call (75 queries
   affected, max 6).
2. **The rule sentence is sent only when examples are.** It is inserted right after
   the "↳" paragraph ("…choose between them with 'accepts filters:'"), and only when
   the router passes examples, so switch 0 stays byte-identical.
3. **A phrasing that repeats the catalogue question is skipped too**, not just the
   question's own vector: any phrasing whose cleaned text equals the cleaned question.
   Repeated phrasings within one candidate are shown once.
4. **Two older test stubs changed.** `test_refusal_precedence` and
   `test_wp6d_ranking_floor` stub the retriever and `rerank`; they now accept the new
   method and keyword. No assertion changed.
5. **`run_custom_eval.py`'s top-3 trace** wraps `retrieve_with_examples` too; without
   it the `retrieved` column would be empty with the switch on.
6. **The gold replay went parallel partway through**, at the operator's request (§4.1).
7. **An extra paired timing check** (~190 calls, §6), because WP-6d's runs carry no
   per-call latency and the brief asks for latency before and after.
8. **Measurement without production changes.** Per-call tokens, wall time and the
   phrasings shown were recorded by a harness wrapper around `router.rerank`, not by
   `llm_usage`, which records no latency. `llm_usage` is unchanged.

---

## 8. Recommendation

**Keep the switch at 4.**

* It is right where the brief said the gap was: 211, 315, 321, #2046 and gold's
  "gold chip offered" rows now answer, and 42 / 49 stop being answered wrong.
  Row 315's "delayed" is fixed by phrasings already in the catalogue.
* It does not raise the confidently-wrong count anywhere (Eval_1 4 → 2, gold 6 → 6,
  pilot 1 → 1). The new wrong answers (Eval_1 44, 281; gold #1214, #1415, #1852) are
  offset by as many fixes. Two of the five are the reranker picking against
  correctly-worded lines (#1214 Odia "sarichi", #1415), and one (#1852) had no right
  candidate at all.
* It costs about +20% on the reranker's input tokens and no time.
* **Its cost is Eval_1's extra asks** (net +9), all with the right template on the chips.
  Each run is one sample, and D33 recorded a quarter of Eval_1 rows flipping between
  answering and asking from run to run. Stage 1 and the pilot show the same flipping
  here (1007, 1009 and 1043 each came out differently in the two runs). So the
  7-point drop in correct answers is partly noise. The two groups behind it, however,
  have a clear mechanism (§3.2).

**The follow-up, if the operator adopts it** (not built; out of this package's scope):
choose *which* walked phrasings are shown instead of taking the first four. The
cheapest version skips the WP-6 filter variants (phrasings that are another phrasing
plus ", for / in / under a given …" or ", in the main GPDP"). It would show the next
hand-written line instead, or nothing. It is measurable offline for free on the call
log (`WP6e_rerank_calls.jsonl`): 141–149, 7, 174, 12 and 186–193 are the rows to
watch. If the operator prefers not to carry an experiment, setting the switch to 0
restores WP-6d exactly.

**Still open from WP-6d §9, after this run:** §9.3 (row 315) looks fixed by the
examples alone. §9.4 (42 / 49) is improved but not settled; 49 went to TRD-002 once in
two runs. §9.1 (1007 / 1009) now answers about half the time; BUD-003's own
tied/untied phrasing competes with its scheme phrasings. §9.2 (plain count) is
unchanged in kind: 1043 answered PLN-024 in one run of two, and 1044 is still the
PLU-005 refusal by rank-0 precedence, with the reranker itself declining.

---

## 9. Spend

All paid runs went through `confirm_spend`. `run_custom_eval.py` has no meter, so
those lines are counted from the records, as WP-6b..6d did.

| | calls |
|---|--:|
| offline checks (cached index and recall vectors) | 0 |
| gate 5 live model list | 1 |
| stage 1, 12 rows | ~40 |
| Eval_1, 314 rows | ~1,000 (306 reranks) |
| gold, first 123 rows sequential (meter lost when stopped; estimated at WP-6d's 2.83 per row) | ~350 |
| gold, remaining 152 rows in 8 parts | 426 (metered) |
| pilot, 44 rows | ~150 (44 reranks) |
| paired timing check, 63 questions | 189 (metered; a first attempt failed before any call) |
| **total** | **~2,160** |

The brief estimated ~2,000. The difference is the paired timing check.

# WP-D17 report — breakdown sentences carry only their own numbers

**Brief:** `handoffs/WPD17_breakdown_cautions.md`. **Decisions:** D81, D82, D83 (R28).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d17`, results copied back to the Drive repo after each task.
**Commits (on `master`, not pushed):** `7cb57e2` T1+T2, `90bf1bb` T3 (the rebuilt store), `dada1db` T4, then the live check and this report.

**Before starting.**
- T0 asks for a clean tree holding this brief and D83. D83 is in the PM's plan, but the plan, this brief and the WP-D15b/15c briefs were uncommitted. The operator told me to run this package after WP-D15c and WP-D15b, which are committed (`39a06cf`, `4b5c84a`). I left the PM's files alone.
- WP-D15b also edits `gates.py`. It ran before this package, not at the same time, as the brief requires.
- Baselines therefore include WP-D15b: **gate 50/52, suite 318, sheet checks 9 of 9**.

**Outcome in one line.**
- The four cautions are gone from all 11,268 breakdown sentences, and nothing else in the store changed.
- A typed-in digit now fails the build.
- In the live check, no answer repeats a removed caution's figure (11 sentences did before). No wrong number is shown. One answer of 50 was lost, against 0 before; the brief allows one.

---

## §0 The pass marks, with evidence

| # | Pass mark | Result | Evidence |
|---|---|---|---|
| T0 | The store rebuilds unchanged before any change | **PASS** | The unchanged builder: 66,779 records, **0 embedded**, every record, field and vector identical; the three store files byte-identical (only the stamp's time and duration differ) (§2) |
| T3 | Exactly the four texts removed, nothing else | **PASS** | Same 66,779 ids in the same order; **11,268** sentences changed: 407 / 7,759 / 1,417 / 1,685, exactly the PM's counts, each the old sentence minus one caution from its end; every other field identical; exactly those 11,268 re-embedded; the other **55,511 vectors bit-identical**; candidate set unchanged (`610cb3d26dff7bf3`) (§3) |
| T3 | No "no match" question now finds something | **PASS** | All four still clear no floor (threshold hits 0 → 0) |
| T3 | Sheet checks 9 of 9 on the untouched sheet store | **PASS** | 9 of 9 |
| T4 | Held picks refreshed, not re-judged; `--check` clean | **PASS** | 56 held sentences refreshed; 0 questions re-judged (0 judge calls); every pick and judge record unchanged; `--check`: 53 held, 50 reach the writer, 0 problems |
| T4 | Switch-off baseline re-made from `f0c5efb` on the new store | **PASS** | 76 answers re-made from the pre-WP-D15 code; **all 76 identical** to the previous baseline (no offline answer showed a caution) |
| T5-1 | Wrong numbers shown: 0 | **PASS** | 0, by the runner's independent second pass |
| T5-2 | Lost ≤ WP-D15c `rule_off` + 1 | **PASS** | 1 lost (OPN-03, step 2: the writer gave 3.13 and 1.26, in no record it cited) against 0 (+1 allowed) |
| T5-3 | No answer states a removed caution's figure unless its record does | **PASS** | After: **0** sentences. Before (WP-D15c `rule_off`, old store): 11, listed in §6 |
| Gate | Baseline + `breakdowns-own-numbers` green; nothing green turned red; suite green; sheets 9/9 | **PASS** | Gate 50/52 → **51/53** (reds: only the two D69 lines); suite 318 → **325 passed**; sheets 9 of 9 |

---

## §1 What was built, file by file

| File | Change | Task |
|---|---|---|
| `Insights/src/phase5f_decompose.py` | `_MEASURE_CAVEAT` and its use removed. New `build_sentence_marked`: every value a sentence interpolates (formatted figures, counts, members' and places' names, the scope phrase) goes through `_v()`, which wraps it in two control characters. `build_sentence` returns the marked text stripped, so the two can never differ. `own_numbers_check(record_id, marked)` stops the build, naming the record, if any digit stands outside a marked value. The size and ratio clauses and the remainder line are marked the same way. `build_records` builds, checks and strips each sentence. No other line, order, format or word changed (the T3 comparison proves it) | T1, T2 |
| `Insights/metainsights/decompose_corpus.json.gz`, `.part0.npy`, `.part1.npy`, `_stamp.json` | Rebuilt: 11,268 sentences lose their caution; 11,268 vectors new, 55,511 unchanged | T3 |
| `DiscoverChat/gates.py` | New line `breakdowns-own-numbers` (§4) | T2 |
| `DiscoverChat/tests/test_breakdown_own_numbers.py` (new) | 7 tests: the table is gone; sentences of every shape pass and strip to the plain sentence; signed and offsetting measures pass; data names with digits ("Theme 4", "5TH STATE FINANCE COMMISSION", a fiscal year) pass; the old digit cautions fail, naming the record; one typed-in figure fails; putting a caution back through the builder's own function fails | T2 |
| `DiscoverChat/experiments/build_judge_picks.py` | `--refresh`: a held sentence takes the store's only when the old one is the new one plus one removed caution (or they are equal). Anything else is listed for `--redo`. The file records when, why and how many. `--redo` now accepts a stale store when every stale question is being redone | T4 |
| `DiscoverChat/experiments/judge_picks.json` | Refreshed (56 sentences); a `refreshed` record added | T4 |
| `handoffs/WPD15_trial/offline_baseline_answers.json.gz` | Re-made from `f0c5efb` on the new store; the answers are identical, and `what_this_is` says it was re-made | T4 |
| `handoffs/WPD17_cautions/` | `compare_stores.py` (T0 and T3), `t0_rebuild_proof.json`, `t3_comparison.json`, `pools.py` + `t3_search.json` + `query_vectors_held.pkl` (the 53 held questions' query vectors, embedded once), `remake_baseline.py`, `audit_other_stores.py/.json`, `live_analyse.py`, `live/` (the runner's JSON and markdown, `tables.md`, `answers_before_after.md`) | T0–T5 |

No change to the chat's service code. Do-not-touch files were not edited.

**What the commit added to the repository:** the T3 commit `90bf1bb` holds three new binary blobs: `decompose_corpus.part0.npy` 68.4 MB, `.part1.npy` 68.4 MB and `.json.gz` 11.8 MB. That is **148.5 MB**, uncompressed, and float vectors barely compress. The old versions stay in history, so the repository grows by about that much. Each part stays under the 95 MB limit (`vector-parts-under-limit` green).

---

## §2 The T0 rebuild proof

The builder, unchanged, run in the mirror with the four view parquets from `C:\dev\odisha-d11b\Insights\views_prdw\`. The committed store was saved first to `C:\dev\odisha-d17-store-before\`.

| | |
|---|---|
| Records | 66,779 (view1 50,908, view2 2,837, view3 3,832, view4 9,202); 66,779 reconcile |
| Embedding | **66,779 reused from cache, 0 to embed** — no call |
| Records, fields, order | identical (`compare_stores.py --expect identical`: PASS) |
| Vectors | 66,779 of 66,779 bit-identical |
| Files | `decompose_corpus.json.gz`, `.part0.npy` and `.part1.npy` byte-identical (SHA-256) |
| Stamp | differs only in `generated_at` and `build_seconds` |

---

## §3 The T3 comparison, and what it does to search

`handoffs/WPD17_cautions/t3_comparison.json` (`compare_stores.py --expect cautions-removed`: **PASS**):

| | Expected | Found |
|---|---|---|
| Ids, order | the same 66,779 | the same |
| Sentences changed | 11,268 | **11,268** |
| … "A rise here … 2.7% to 53.2% …" | 407 | 407 |
| … "The sanctioned basis … about one in six." | 7,759 | 7,759 |
| … "Only 17 completions …" | 1,417 | 1,417 |
| … "A swap between the SC and ST components …" | 1,685 | 1,685 |
| Changes of any other kind | 0 | **0** |
| New sentences still holding a caution | 0 | 0 |
| Other fields of any record | identical | identical (only `embed_text_sha256` of the 11,268 changed, as it must) |
| Records re-embedded | the 11,268 | 11,268 (177 embedding calls) |
| Vectors of the other records | bit-identical | **55,511 of 55,511** |
| Candidate set | unchanged | `610cb3d26dff7bf3` → `610cb3d26dff7bf3` |
| Sheet checks on the untouched sheet store | 9 of 9 | 9 of 9 |

**Search** (`t3_search.json`). Query vectors were never re-embedded: the offline questions use WP-D15's stored vectors, and the held questions' vectors were embedded once and kept. The 76 offline gate questions and the 53 held questions overlap, leaving 78 distinct questions.

| | |
|---|---|
| Share of each top-100 pool kept | middle **97%**, lowest 84% |
| Pools identical | 22 of 78 |
| Threshold-path hits (what the offline gate shows) changed | **0** |
| Held insights no longer in their question's pool | 15, across 10 questions (the held picks keep them; only the search would now find them less often) |
| "No match" questions clearing the floor | **none** — all four: 0 hits before, 0 after |

---

## §4 The T2 check, its proof, and the audit of the other two stores

**In the builder (exact).** The method is decision 1 of §9. Every digit of a stored sentence must sit inside a value the builder interpolated for that record. The rebuild ran the check on all 66,779 records, and all passed.

**Proof it works** (`test_breakdown_own_numbers.py`): the "2.7% to 53.2%" and "17 completions" cautions appended to a built sentence fail and name the record. So does one figure typed into the template ("across about 20"), and so does a caution put back through the builder's own function.

**A limit, stated.** The rule is about digits. Two of the four cautions hold no digit: "about one in six", and the SC/ST text. Put back, they would pass the digit rule. They are kept out by the gate line's text test below. Number words cannot be banned from the template: it uses "one" legitimately ("The one remaining", "Every one of them").

**In the chat's gate, on the stored file:** `breakdowns-own-numbers`, green:

```
66,779 breakdown sentences: no caution text; every one rebuilt from its own record by the builder's code
with no digit in its fixed text; 58,056 size and 4,368 ratio clauses checked for shape and member
(their volume and ratio figures are proved by the builder's check, not here)
```

1. None of the four caution texts is in any stored sentence.
2. Each sentence is **rebuilt from its own stored record** (total, gross, signs, shape, scope, and every member's name, value, share and rows) by the builder's own `build_sentence_marked`, and held to the same digit rule. The stored sentence must be that rebuilt core, followed by nothing or by the size and/or ratio clause in their fixed shapes. All 66,779 match.
3. **What only the builder proves.** The size clause's volume share and volume in scope, and the ratio clause's figure, are computed from the view parquets and are not stored on the record. The gate checks their shape, that the member is the record's own top member, and that the size clause's money share is the record's own. That those two figures were computed for this record is proved by the builder's check, at build time, on every record. No field was added to the stored records.

**Audit of the other two stores** (`audit_other_stores.json`, reported, nothing fixed):
- **Mined insights** (4,404 records): each sentence is split at full stops, semicolons and "Exception:". Any part that holds a digit and appears word for word on at least 10 records about at least 5 different subjects is listed (threshold: decision 4). **17 parts; none is a typed-in figure.** Every one is a name from the data ("Exception: Theme 1 - Poverty Free and Enhanced Livelihoods Village (different pattern)", "Uneven only in: Code 109 …", "Exception: 2024-2025 (no clear pattern)") or a coverage count the engine computed for the record ("Across most measure values (6/9) …"). They repeat because the same pattern recurs across subjects, not because a figure was typed in.
- **Profile sheets:** sheet check 5 (`--check` "sentences hold only stored figures"; gate line `profile-sheets-formatter-parity`) already proves that every numeral in every sheet sentence is a stored value of that sheet's row, through the stored formatter. Run here: 2,871 sentences, all pass.

---

## §5 The held picks and the switch-off baseline

**Held picks.** `build_judge_picks.py --refresh`:
- 56 held sentences refreshed: each was the new sentence plus one removed caution.
- 0 questions could not be refreshed, so 0 were re-judged (no judge call).
- Every entry's ids, order, question and judge record are unchanged (checked against a copy taken before).
- The file now carries `"refreshed": [{"at": "2026-11-24T22:01:33", "why": "WP-D17 (R28, D83): …", "sentences_refreshed": 56, "not_refreshed_questions": [], …}]`.
- `--check`: 53 held, 50 reach the writer, 0 problems.

**Baseline.** `remake_baseline.py` on a tree assembled from `git archive f0c5efb DiscoverChat Insights/src` (the code before WP-D15: no `place.py`; the script asserts both). It ran with today's `Ask/`, the view parquets and the **new** breakdown store, using WP-D15's own 76 questions and stored query vectors. Result: **76 of 76 answers identical** to the previous baseline. None of the 76 offline answers showed a breakdown that carried a caution; I checked the previous file's answers and their citations for all four texts and found none. Only the file's description changed, to say it was re-made. `place-switch-off-identical` stays green and keeps its meaning.

**Fixtures and tests quoting a caution:** none read by a test or the gate. The caution texts survive only in the result files of earlier experiments under `DiscoverChat/experiments/` (`answer_compare*.json`, `*_trial_results.json`, `writer_trials/*.json`): records of past runs, which no test or gate line reads, so I left them. They also survive in `Insights/src/phase5b_report.py`, the report's reading notes, which are outside this package.

---

## §6 The live check

The 50 held questions that reach the writer, through `Assembler.answer` (`run_writer_trial.py --sheets`), once each, with the shipped defaults (every-insight `log`, standing `log`, causal `log`, direction `block`). Writer `gpt-6.2-sol`. Compared with WP-D15c's `rule_off` arm: the same path and settings on the old store.

| | Before (WP-D15c `rule_off`, old store) | After (rebuilt store) |
|---|---|---|
| Answers | 50 | 50 |
| Kept | 50 | 49 |
| Lost | 0 | 1 (OPN-03, step 2) |
| Passed on the first try | 47 | 45 |
| **Wrong numbers shown** | 0 | **0** |
| Seconds per answer, middle | 10.8 | 9.3 |
| Words, middle (kept) | 216.5 | 212 |
| Insights cited, middle (kept) | 6 | 7 |
| Place facts used, middle (kept place answers) | 13 | 12 |

The one loss (OPN-03, "Is drinking water getting its share of the money?") is step 2 working. The writer gave "3.13" and "1.26", which stand in neither record it cited (d1-45862, d1-45863), on both attempts, and the officer would have seen the stored sentences instead. One run per question, so one answer is within run-to-run difference, as the brief allows. (While analysing, my script first printed these two columns the wrong way round; it is corrected, and the figures above are the right way round.)

**Pass mark 3.** Every shown answer was searched for "2.7%" beside "53.2%", "about one in six" and "17 … completions". **After the rebuild: 0 sentences.** Before, in WP-D15c's `rule_off`, there were 11:

| Question | Figure | Sentence (start) | Cites | Stated by the cited record for its own subject? |
|---|---|---|---|---|
| GEO-19 | 2.7% / 53.2% | "The linked share rose from 2.7% to 53.2% over the period …" | d2-01861 (Mendarajpur) | no — the caution's whole-sample figure |
| GEO-29 | 2.7% / 53.2% | "… Only 23.1% of cashbook payments were linked … although the linked share rose from 2.7% to 53.2% over the period covered." | d2-00845 among others | no |
| MEA-08 | 2.7% / 53.2% | "The share of spending linked to a planned activity rose from 2.7% to 53.2% …" | d2-00074 | no |
| VAG-04 | 2.7% / 53.2% | "… linked share …" | d2-00074, d2-01090 | no |
| VAG-06 | 2.7% / 53.2% | "The share of spending linked to a planned activity rose from 2.7% to 53.2% …" | d2-00081 | no |
| L03 | about one in six | "The sanction comparison covers only activities with a sanction on file, about one in six." | d1-03874, d1-46097 | no |
| L05 | about one in six | "These amount comparisons cover only activities with a sanction on file—about one in six." | d1-41292, d1-40071 | no |
| L07 | about one in six | (a long paragraph ending with the caution's words) | d1-… | no |
| OPN-01 | about one in six | "Recorded sanctions totalled Rs 19.80 crore, but that total covers only activities with a sanction record on file—about one in six." | d1-42179 | no |
| OPN-03 | about one in six | "… that comparison covers only activities with a sanction on file—about one in six." | d1-45863 | no |
| L06 | 17 completions | "Kalimela also accounts for 13 of the 17 works marked completed in the sample." | p-block-3843-E2 | **yes** — the sheet line says "13 works are marked completed, out of 17 in the whole sample" (my pattern missed that wording; this one is properly sourced) |

So 10 of the 11 "before" sentences carried a whole-sample figure from a caution into an answer about something else. After the rebuild there is none.

**The three answers, before and after, in full** (GEO-29 Khordha, L01 Kandhamal, L06 Kalimela) follow. GEO-29's before answer is the example the brief quotes ("although the linked share rose from 2.7% to 53.2% …"); its after answer no longer says it.

## GEO-29 — How is Khordha district doing overall?

**Before (WP-D15c rule_off, old store)** — kept, 1 tries, 228 words, insights cited 4 of 8, place facts used A6, I4, J, A3, A4, A5, A7, A2, B, B, G3, E5, E2, E4

> Khordha spent the highest share of its planned cost among the 9 districts in the sample: 55.9%, against a middle value of 35.9%. The district figures cover 3 Gram Panchayats in Bhubaneswar block. Of Rs 5.95 crore planned, Rs 4.06 crore was sanctioned on approvals on file and Rs 3.33 crore was spent on planned activities, the 3rd highest spending in the sample. Spending was still Rs 2.63 crore below plan, and 546 planned activities (41.5%) had no cost recorded.
>
> The spending gap was spread across all the sampled Gram Panchayats and was not dominated by any one year. Sanitation had the largest gap at Rs 70.08 lakh below plan, followed by drinking water at Rs 35.86 lakh below plan. In 2025-2026, recorded spending on planned activities was 35.1% of planned cost, down from 68.7% in 2024-2025.
>
> Two priorities for the next review are to reconcile payments with plans and verify the status of older works. Only 23.1% of cashbook payments were linked to a planned activity, the lowest share among the 9 districts, although the linked share rose from 2.7% to 53.2% over the period covered. Meanwhile, 145 works planned in 2022-2023 or earlier are still marked ongoing, with 86.0% of their planned cost spent. Only 1 work is marked completed, while 293 activities have photo evidence that officials can consult where available when checking work status.
>
> (as of 2026-09-11)

**After (rebuilt store)** — kept, 1 tries, 239 words, insights cited 3 of 8, place facts used A6, A5, A3, A7, A4, I4, J, B, B, B, B, B, B, G3, A1, A2, H1, E2, E5

> Khordha had the highest spending as a share of planned cost among the 9 districts in the sample: 55.9%, against a sample midpoint of 35.9%. The district spent Rs 3.33 crore against a planned cost of Rs 5.95 crore, leaving spending Rs 2.63 crore below plan. Sanctions on file totalled Rs 4.06 crore, the 3rd highest in the sample. The Khordha figures cover 3 Gram Panchayats in Bhubaneswar block, not the whole district.
>
> The gap between planned cost and spending was spread across all sampled Gram Panchayats, with none accounting for a majority. Sanitation had the largest gap of any focus area, at Rs 70.08 lakh below plan, followed by drinking water at Rs 35.86 lakh below plan. The largest annual gap was in 2023-2024, at Rs 61.33 lakh below plan. In 2025-2026, spending was 35.1% of planned cost, the lowest share across the years shown.
>
> At the next review, prioritise reconciling payment and work-status records. Only 23.1% of cashbook payments were linked to a planned activity, the lowest share in the sample. Of 1,316 planned activities, 546 (41.5%) had no cost recorded, and 48 had an approval cost recorded but no approval record on file. Only 1 work was marked completed, while 145 works planned in 2022-2023 or earlier were still marked ongoing, with 86.0% of their planned cost already spent. Those older works are a priority for checking whether the recorded status matches progress on the ground.
>
> (as of 2026-09-11)

## L01 — What should I know about Kandhamal?

**Before (WP-D15c rule_off, old store)** — kept, 1 tries, 299 words, insights cited 5 of 8, place facts used I4, J, A1, A3, A4, A5, A6, B, A2, F1, G3, E5, E4, E3, C, C

> Kandhamal’s figures cover one Gram Panchayat in Khajuripada block, not the whole district. In the sample, Kandhamal recorded 573 planned activities with a planned cost of Rs 3.48 crore. It had the lowest sanctioned amount, at Rs 1.14 crore, and the lowest spending on planned activities, at Rs 58.17 lakh, among the 9 districts represented. Recorded spending was 16.7% of planned cost, against a sample middle value of 35.9%. The gap was particularly pronounced in 2025-2026, with Rs 5.10 lakh spent against Rs 1.06 crore planned (4.8%). 
>
> Start the records review with missing costs and funding details. No cost was attached to 241 activities (42.1%), and 167 of those were from 2023-2024. The scheme and fund component were each missing for 437 activities (76.3%). Administrative approval was on file for 136 activities (23.7%); a missing record does not establish that approval was never given. Reconcile cashbook payments with the plans as part of that review: 47.0% of payments were linked to a planned activity. 
>
> For the works review, check whether older works are still ongoing and whether their status is supported by field evidence. There are 42 works planned in 2022-2023 or earlier still marked ongoing, with Rs 24.82 lakh spent against Rs 38.51 lakh planned. Of the 17 works marked abandoned, 16 were planned in 2022-2023. Photo evidence was on file for 75 activities, the fewest among the 9 districts represented. 
>
> Village infrastructure and drinking water are useful starting points for checking the larger planned allocations. The Self-sufficient Infrastructure in Village theme accounted for Rs 1.90 crore (67.9%) of planned untied grants. Drinking water was the largest focus area by planned cost, with Rs 89.50 lakh planned and Rs 18.76 lakh spent. Roads are a specific item to reconcile: Rs 33.50 lakh was planned, with no spending recorded.
>
> (as of 2026-09-11)

**After (rebuilt store)** — kept, 1 tries, 260 words, insights cited 5 of 8, place facts used I4, J, A1, A3, A4, A5, A6, B, A2, F1, C, E5, E3, E4

> Kandhamal’s figures cover only Khajuripada block and one Gram Panchayat in the sample. The district recorded 573 planned activities, the second fewest among the nine sampled districts. Of the Rs 3.48 crore planned, Rs 1.14 crore was sanctioned for activities with an approval on file and Rs 58.17 lakh was recorded as spent on planned activities. Spending was 16.7% of planned cost, the lowest share among the sampled districts, against a middle value of 35.9%. For activities planned in 2025-2026, recorded spending was 4.8% of planned cost.
>
> The first records to check are missing cost and funding details. No cost was attached to 241 activities (42.1%), with 167 of those in 2023-2024. No scheme was recorded for 437 activities, and no fund component was recorded for 437 activities. Administrative approvals were on file for 136 activities (23.7%); a missing record does not establish that an activity lacked approval.
>
> Village infrastructure and drinking water are useful starting points for reviewing the plan. Self-sufficient Infrastructure in Village accounted for 67.9% of planned untied grants (Rs 1.90 crore). Drinking water was the largest focus area by planned cost, at Rs 89.50 lakh, with Rs 18.76 lakh recorded as spent.
>
> At the next works review, verify the status of 42 works planned in 2022-2023 or earlier that are still marked ongoing, with Rs 24.82 lakh recorded as spent against Rs 38.51 lakh planned. Also check the records for the 17 works marked abandoned, 16 of which were planned in 2022-2023. Photo evidence was on file for 75 activities, the fewest among the sampled districts.
>
> (as of 2026-09-11)

## L06 — What should I know about Kalimela?

**Before (WP-D15c rule_off, old store)** — kept, 1 tries, 236 words, insights cited 3 of 8, place facts used I4, J, A1, A2, A3, A4, A5, A6, B, B, C, C, F1, G3, E5, E2

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented in the sample by Kalimela Gram Panchayat alone. It recorded 852 planned activities, of which 392 (46.0%) had no cost attached. Its recorded planned cost was Rs 7.65 crore, the 2nd highest of 16 blocks in the sample. Sanctions on file totalled Rs 2.08 crore, and spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest of 16 blocks. Spending was 11.1% of planned cost in 2023-2024 and 10.5% in 2024-2025.
>
> Drinking water is the first area to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. Land improvement is another priority for checking: Rs 73.95 lakh was planned, with no spending recorded.
>
> Start the records review by matching plans, approvals and payments. A fund component was missing for 684 activities (80.3%), and Rs 5.57 crore of planned cost (72.7%) had no scheme recorded. Administrative approvals were on file for 168 activities (19.7%); a missing record does not establish that an activity was unapproved. Only 33.3% of cashbook payments were linked to a planned activity, against a sample middle value of 46.5%.
>
> At the next works review, verify the status of 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost already recorded as spent. Kalimela also accounts for 13 of the 17 works marked completed in the sample.
>
> (as of 2026-09-11)

**After (rebuilt store)** — kept, 1 tries, 244 words, insights cited 4 of 8, place facts used I4, A1, A2, A3, A4, A5, A6, C, C, C, F1, G1, G3, E5

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented by one Gram Panchayat in the sample. It recorded 852 planned activities, of which 392 (46.0%) had no cost attached. Its recorded plan cost of Rs 7.65 crore was the 2nd highest of 16 blocks in the sample. Sanctions on file totalled Rs 2.08 crore and spending on planned activities was Rs 1.76 crore. That was 23.0% of planned cost, the 4th lowest of 16 blocks in the sample, against a middle value of 36.6%.
>
> Drinking water is a priority for the next review: it accounted for 48.8% of planned cost (Rs 3.74 crore), with Rs 60.98 lakh spent. All planned tied-grant funding was allocated to drinking water and sanitation. Land improvement and poverty alleviation also warrant a check: they had Rs 73.95 lakh and Rs 37.09 lakh planned, respectively, but neither showed any spending.
>
> Reconcile the plan, approval and payment records before drawing conclusions about delivery. Activities with no scheme recorded account for Rs 5.57 crore (72.7%) of planned cost, and 684 activities lack a fund component on file. Only 168 activities (19.7%) have an administrative approval on file; a missing record does not establish that an activity was unapproved. The cashbook shows Rs 5.28 crore paid out, but only 33.3% of payments are linked to a planned activity. At the next review, verify the status of the 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost recorded as spent.
>
> (as of 2026-09-11)

---

## §7 The gate, the suite and the sheet checks, baseline against final

| | Baseline (T0) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 50/52; red: `judge-model-evidenced`, `classifier-model-evidenced` (D69) | **51/53**; red: the same two |
| `python -m pytest DiscoverChat/tests -q` | 318 passed | **325 passed** (7 new), 0 failed |
| `python Insights/src/phase5g_profile_sheets.py --check` | 9 of 9 | **9 of 9** (on the untouched sheet store, with the new breakdown store) |

Lines a rebuild could move, all green after it: `corpus-pin`, `vector-parts-under-limit`, `corpus-deterministic-text`, `decompose-reconciles`, `decompose-evenness-honest`, `decompose-signed-not-a-magnitude`, `no-match-honest`, `numerals-traceable`, `findings-verbatim`, `profile-sheets-stamp`, `profile-sheets-insights`, `place-switch-off-identical` (76 of 76 against the re-made baseline), and the new `breakdowns-own-numbers`.

Files beside the mirror: `C:\dev\odisha-d17-baseline-{gates,pytest,check}.txt`, `-final-{gates,pytest,check}.txt`, `-t0-rebuild.txt`, `-t3-rebuild.txt`, `-pools-{old,new}.json`, `-judge_picks-before.json`, `-offline-baseline-before.json.gz`, `-store-before\` (the committed store), `-f0c5efb\` (the tree the baseline was re-made in), `-live.txt`.

---

## §8 Every model call and its cost

| What | Model | Calls | Tokens / texts | Cost |
|---|---|---|---|---|
| Re-embedding the 11,268 changed breakdown records | `qwen/qwen3-embedding-8b` (OpenRouter) | 177 | 11,268 texts | about $0.01 per 1M tokens; under a cent |
| The 53 held questions' query vectors (search report, embedded once, kept) | the same | a handful (one per question) | 53 queries | negligible |
| Offline gate runs (questions embedded live, memoised per run) | the same | as in every gate run | — | negligible |
| Live check (T5) | `gpt-6.2-sol` | **55** | 146,154 in / 27,381 out | price not set |
| Judge calls | — | **0** | — | — |

No price is on file for `gpt-6.2-sol`, so no cost is guessed. Every chat-model call is also in the mirror's `DiscoverChat/logs/calls.jsonl`.

---

## §9 Decision journal

1. **How the builder's check collects the figures of a sentence:** markers, not a list. Every value interpolated into a sentence is wrapped in `\x02 … \x03` while the sentence is built, and the stored sentence is the marked text stripped, so the check and the output cannot drift apart. The rule is that the text outside the markers, the fixed template, holds no digit. That catches any typed-in figure, in any line, of any shape, without the check having to know which figures a line should hold. The measure phrase, the dimension words and the verb are left unmarked on purpose, so the glossary's wording is held to the same rule. No record needed an exception.
2. **What the gate line can prove from the stored record:** it rebuilds the sentence core from the record with the builder's own code (§4). This is stronger than searching for the four texts, and needs no parquet. Its limit is the size and ratio figures, which are not stored. No field was added to the records.
3. **The digit rule cannot see a number in words** ("about one in six"). That is why the gate line also tests for the four texts. Banning number words from the template is not possible ("The one remaining").
4. **The audit's threshold:** a digit-bearing sentence part on at least 10 records about at least 5 different subjects (subject = subspace phrase plus measures). A figure computed for one subject cannot repeat word for word across five subjects unless it is fixed text, a whole-sample figure or a data name. The 17 parts found are all data names or per-record coverage counts.
5. **The refresh mode** accepts an exact match or "old = new + one space + one caution", nothing looser. That covered all 56; nothing was re-judged.
6. **The baseline tree** took `DiscoverChat/` and `Insights/src/` from `f0c5efb` (the old builder with its caution table is in it, but nothing at answer time calls the builder), and today's `Ask/`, parquets and new breakdown store. The script asserts it imports the old code.
7. **The search report's query vectors** for the held questions were embedded once, during the old-store run, and replayed for the new-store run (`query_vectors_held.pkl`). So the two runs differ only by the store.
8. **`--redo` with a stale store:** the old guard refused any `--redo` while any held sentence differed from the store. It now refuses only when a stale question is not among those being redone, so a question the refresh could not cover can be redone alone. It was not needed this time.

---

## §10 What in this brief was wrong or silent

1. **T0's clean-tree precondition** could not be met as written: the PM's plan and briefs were uncommitted. The operator's instruction to run this package after WP-D15c and WP-D15b covered it.
2. **The baselines** in "What exists" are WP-D15c's. WP-D15b ran in between, so the baselines here are gate 50/52 and suite 318, and the final numbers are one line and seven tests more.
3. **The digit rule and words.** The brief's rule ("fixed text contributes no digit") is enforced exactly, but two of the four cautions have no digit. Only the gate's text test keeps those two out (§4, decision 3). A future hand-typed number in words would pass both.
4. **What the gate line can prove** is stated in §4: everything except the size clause's volume figures and the ratio clause's figure, which only the builder proves.
5. **The live check's "before" holds one properly sourced sentence:** L06's "13 of the 17 works marked completed" cites sheet line E2, which states it. The pass mark concerns "after", which has none.
6. **Held insights leaving their pools** (15 across 10 questions) does not touch the held picks, which stay the judge's. It does mean a fresh judge run today could pick differently for those 10 questions. Reported, nothing done.
7. **Not done, as the brief says:** the insight report's reading notes (`phase5b_report.py`) still hold "about one in six" and the 2.7% to 53.2% note; the earlier experiment result files under `DiscoverChat/experiments/` still quote the cautions in their recorded answers (history, not read by any test).

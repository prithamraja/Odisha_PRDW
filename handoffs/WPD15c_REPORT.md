# WP-D15c report — four small changes after the WP-D15 review

**Brief:** `handoffs/WPD15c_review_fixes.md`. **Decisions:** D81, D82 (R25–R27).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d15c`, results copied back to the Drive repo after each task.
**Commits (on `master`, not pushed, not deployed):** `6d0f7d7` T1+T4, `d1cb0ee` T2, `dc6bab7` T3, `14976c3` T6 (gate and tests), then the live check and this report.

**Before starting.** T0 asks for a clean tree that holds this brief and D81/D82. The tree held the PM's uncommitted edits (`PROJECT_PLAN.md` with D81/D82, the WP-D15b brief, and this brief untracked). The operator told me to run WP-D15c first and then WP-D15b. I left the PM's files uncommitted and staged only my own.

**Outcome in one line.** All four pass marks hold. With the every-insight rule off (the shipped default), no answer was lost against 4 with it on; 47 of 50 passed on the first draft against 8; answers took half the time; and no wrong number was shown in either arm.

---

## §0 The pass marks, with evidence

| # | Pass mark | Result | Evidence |
|---|---|---|---|
| 1 | Wrong numbers shown: 0, both arms | **PASS** | rule_on 0, rule_off 0, by the runner's independent second pass (§4) |
| 2 | rule_off loses no more answers than rule_on | **PASS** | rule_off 0 of 50, rule_on 4 of 50 |
| 3 | `block` restores today's check | **PASS** | For 8 recorded inputs (clean, left-out insight, left-out plus uncited figure, unknown id, uncited figure, sheet turn, sheet turn with left-out insights, an answer citing nothing), `check_citations` and `citation_failure_reason` under `block` return exactly what the code before this package returned: 8 of 8 identical (`C:\dev\odisha-d15c-checks-{baseline,block}.json`). Also by test and by the gate line |
| 4 | No rule_off place answer carries the "More than" line; no note where T3 says none | **PASS** | "More than" on rule_off place answers: 0 of 21. Notes printed: 4, all on bare names (L06 Kalimela, GEO-07 Boipariguda, GEO-18 Laxmipur, TWO-01 Kalimela and Bheden); 0 where the officer named the level |

Gate: 46/48 → **47/49** (the new line green; the reds are still only the two D69 model-id lines). Suite: 285 → **297 passed**, 0 failed.

---

## §1 What was built, file by file

| File | Change | Task |
|---|---|---|
| `DiscoverChat/config.py` | `DISCOVERCHAT_EVERY_INSIGHT_CHECK` (`block` / `log`, default **`log`**), in `knobs()` | T1 |
| `DiscoverChat/checks.py` | Step 4: under `log` the step keeps `pass`, `dropped`, `of` and adds `mode: "log"`, `counts: false`; under `block` it is the old step, the same three keys and nothing else. `citation_failure_reason` gives the step 4 sentence only when the step counts. New argument `every_insight_mode=`. **T4:** step 6 compares a rank by its end (highest = most, lowest = fewest) and does not read "among the …" / "one of the …" as a rank | T1, T4 |
| `DiscoverChat/writer.py` | `Consolidated.left_out`: the insights handed and not cited by the shown narrative, in the order handed; empty on a fall-back. It is in `as_dict()`, so it travels in the `prose` record | T1 |
| `DiscoverChat/assemble.py` | The "More than N findings" line is not printed on a place answer; `place.insights_held_back` stays. The line on an ordinary capped turn is unchanged | T2 |
| `DiscoverChat/place.py` | A place joins the R4 note only when R4 chose its level (the name exists at two levels and the words beside it did not say which). `alternatives` unchanged | T3 |
| `DiscoverChat/experiments/run_writer_trial.py` | The step 4 wrapper is removed. `--allow-unused-findings` sets `log`; new `--every-insight block\|log` forces a mode; neither leaves the configured default. Records per answer: cards/charts/warnings counts, `left_out`, insights cited, whether a place was named | T1 point 8 |
| `DiscoverChat/gates.py` | New `every-insight-check-mode`. Updated: `place-resolution` (the T3 table, plus "Compare Kalimela GP and Bheden"), `place-standing-check` (the T4 cases), `place-facts-optional` and `citation-checks-fire` pin `block` where they assert a left-out insight fails | T6 |
| `DiscoverChat/tests/test_citations.py` | Step 4 under `log` and `block`; the retry reason with and without the step 4 sentence; no floor | T6 |
| `DiscoverChat/tests/test_place_answers.py` | The T3 table and notes; R26 (absent on a sheet turn, present on an ordinary capped turn); R25 (left-out ids, a sheet answer citing no insight kept, the fall-back unchanged, `block` restores the rule); T4 (the five sentences pass, the four mistakes caught, defaults stay `log`) | T6 |
| `DiscoverChat/tests/test_profile_sheets.py` | `test_the_service_does_not_import_the_reader` renamed `test_only_place_py_opens_the_store`; nothing else changed | T6 |
| `handoffs/WPD15c_trial/` | `standing_offline.py/.json` (T4 offline run); `rule_on`/`rule_off` `.json`/`.md` (the live check); `analyse.py` → `tables.md`, `review_items.json` | T4, T5 |

**Does `/chat` already carry the left-out ids?** Yes. `AskResponse.prose` is the writer's record, `Consolidated.as_dict()` plus `used`, so `prose.left_out` reaches the page with no change to `main.py`. It is absent on turns that did not go to the consolidating writer.

---

## §2 The T3 table — expected against actual

| Text | Expected answered / note / alternatives | Actual | Match |
|---|---|---|---|
| What should I know about Kalimela? | block 3843 / the R4 note / GP 119936 | the same; note `This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".` | yes |
| What should I know about Kalimela GP? | GP 119936 / none / block 3843 | the same | yes |
| How is Kalimela Gram Panchayat doing | GP 119936 / none / block 3843 | the same | yes |
| the panchayat of Kalimela | GP 119936 / none / block 3843 | the same | yes |
| How is Kalimela block doing | block 3843 / none / GP 119936 | the same | yes |
| Kalyansinghpur | block 3914 / as today / GP 121162 | the same; note as today | yes |
| Compare Kalimela and Bheden | blocks 3843, 3678 / the two-place note / GP 119936, GP 116438 | the same | yes |
| Compare Kalimela GP and Bheden | GP 119936, block 3678 / `This answer is about Bheden block. For the Gram Panchayat, ask about "Bheden GP".` / block 3843, GP 116438 | the same, word for word | yes |
| How is Chikilli doing? | GP 117835 / none / none | the same | yes |

The other rows of the WP-D15 table are unchanged (`place-resolution`: 14 rows).

---

## §3 The T4 offline run

The changed step 6 run over **every attempt** of the 168 stored WP-D15 trial answers (current, sheet, sheet_choose, sheet_midsize; 270 attempts). The place facts each turn handed are rebuilt by the shipped code. This covers more than the brief asked for (the shown text only), because the five WP-D15 false alarms were all on first attempts.

| | |
|---|---|
| Attempts | 270 |
| Sentences citing a place fact | 1,591 |
| Standing phrases checked | 207 |
| **Flagged** | **0** |

The five sentences of WP-D15 report §4.5 now pass, and the four kinds of real mistake are still caught: the other end ("4th highest" for "4th lowest"), a first place not held ("the most" for "5th most"), a rank not given ("3rd most" for "5th most"), and a quarter not stated. These are pinned by `place-standing-check` and by tests. The default stays `log`. Script and output: `handoffs/WPD15c_trial/standing_offline.{py,json}`.

---

## §4 The live check

All 50 held questions that reach the writer, through `Assembler.answer` (`run_writer_trial.py --sheets`, no `--place-only`), once each per arm, in parallel. Writer `gpt-6.2-sol`; causal `log`, direction `block`, standing `log`. No judge call.

### 4.1 Per arm

| | rule_on (block) | rule_off (log, shipped) |
|---|---|---|
| Answers | 50 | 50 |
| Kept | 46 | **50** |
| Lost | 4 (step 2 three, step 5 one) | **0** |
| Passed on the first try | 8 | **47** |
| **Wrong numbers shown** | **0** | **0** |
| Seconds per answer, middle | 20.5 | **10.8** |
| Words, middle (kept) | 250 | 216.5 |
| Sentences, middle (kept) | 13 | 11 |
| Insights handed, middle | 8 | 8 |
| Insights cited, middle (kept) | 8 | 6 |
| Kept answers citing fewer than half the insights handed | 0 | 7 |
| Kept answers citing none of the insights handed | 0 | **0** |

Split by kind of question:

| | Place answers (21) — on / off | No-place answers (29) — on / off |
|---|---|---|
| Kept | 19 / **21** | 27 / **29** |
| Lost | 2 (step 2) / 0 | 2 (step 2, step 5) / 0 |
| Passed on the first try | 1 / **21** | 7 / **26** |
| Seconds, middle | 19.2 / 8.6 | 22.8 / 11.1 |
| Words, middle | 250 / 217 | 250 / 216 |
| Insights handed, middle | 8 / 8 | 13 / 13 |
| Insights cited, middle | 8 / 4 | 13 / 10 |
| Citing fewer than half | 0 / 7 | 0 / 0 |
| Citing none | 0 / 0 | 0 / 0 |

All 7 answers citing fewer than half the insights are place answers: there the writer leans on the sheet. No answer that was handed insights cites none of them, so the "in full" list the brief asks for is empty.

### 4.2 Cards and charts

**15 of 50** rule_off answers show fewer cards or charts than their rule_on twin. Cards and charts are built from the insights the prose cites, so citing fewer means fewer of them. Examples: TWO-02 charts 0 against 2; TWO-01 cards 1 against 3 and charts 1 against 3; GEO-07 cards 1 against 3; MEA-09 cards 1 against 3. The full list is in `WPD15c_trial/tables.md`. This is the cost the operator was told of at R25. The left-out ids (`prose.left_out`) are now there for a later page package to show them.

### 4.3 Step 6 and step 7 log lines, judged

- **Step 6:** 0 log lines in either arm.
- **Step 7:** 46 lines (48 words), all judged. **None states a number the cited record does not support.**

| Word | Count | Judgement |
|---|---|---|
| majority | 30 | Supported. Each restates the cited finding's own words ("Code 101 accounts for the majority of …") |
| majority, inside a group's name ("SC-majority", "ST-majority") | 6 | Not a number word. The list catches the category label |
| second / third, as a rank | 5 | Supported (e.g. T04 "ranks third for both sanctions … and spending": Barpali A4 and A5 "3rd highest"; L02 "ranked first and second": d2-00011 Bhubaneswar, then Rangeilunda) |
| Second, as a list marker | 1 | No number stated |
| quarter / quarters, a calendar quarter ("quarter-by-quarter", "the largest quarter, 2026-Q1") | 5 | Not a fraction. The list catches a time word |
| half | 1 | Supported: "just under half" for 45.5% (Ganjam) and 48.4% (Bargarh) |

The step 7 list catches two families that are not numbers ("X-majority" group names, calendar quarters). See §8 item 2.

### 4.4 The four answers in full, both arms side by side

L06 (Kalimela), and the first three held questions that name no place, in file order: L02, L03, L05. Each heading gives the outcome, the insights cited and, for rule_off, the ids left out.

#### L06 — What should I know about Kalimela?

**rule_on** — kept, 2 tries, 324 words, insights cited 8 of 8; place facts used: I4, A1, A2, A3, A4, A5, A6, B, B, B, B, B, B, G3, F1, E5, E2, C

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented by one Gram Panchayat in the sample. It has 852 planned activities, of which 392 (46.0%) have no cost recorded. Its planned cost of Rs 7.65 crore is the 2nd highest of 16 blocks in the sample. Sanctions on file total Rs 2.08 crore, and recorded spending on planned activities is Rs 1.76 crore. Spending is 23.0% of planned cost, the 4th lowest of 16 blocks. The annual share was 11.1% in 2023-2024, 10.5% in 2024-2025 and 19.1% in 2025-2026, below the share in each of the preceding years.
>
> For the next review, reconcile funding and payment records and check the status of older works. The fund component is not recorded for 684 activities (80.3%), and Rs 5.57 crore (72.7% of planned cost) has no scheme recorded. Activities without an asset category account for Rs 2.14 crore (28.0% of planned cost). Only 33.3% of cashbook payments are linked to a planned activity, against a sample middle value of 46.5%. Administrative approvals are on file for 168 activities (19.7%); a missing record does not establish that an activity lacked approval. Of the works planned in 2022-2023 or earlier, 55 are still marked ongoing, with 86.0% of their planned cost already recorded as spent. Kalimela also accounts for 13 of the 17 works marked completed in the sample.
>
> Drinking water is the largest planned spending area, at Rs 3.74 crore (48.8% of planned cost), with Rs 60.98 lakh recorded as spent on planned activities. All planned tied-grant funding is split between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending figures, almost all spending is on public works, with just Rs 5,000 on beneficiary-oriented programmes; drinking water (Rs 70.85 lakh) and sanitation (Rs 41.40 lakh) are the largest areas in that breakdown. Separately, the Poverty Free and Enhanced Livelihoods Village theme accounts for 3,978 expected beneficiaries (45.1% of the total), despite representing 3.1% of planned activities.
>
> (as of 2026-09-11)

**rule_off** — kept, 1 tries, 236 words, insights cited 3 of 8; left out: d1-30946, d1-30937, d1-31016, d1-31173, d1-30940; place facts used: I4, J, A1, A2, A3, A4, A5, A6, B, B, C, C, F1, G3, E5, E2

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

#### L02 — Which blocks stand out on expenditure?

**rule_on** — kept, 2 tries, 282 words, insights cited 12 of 12

> In the sampled Gram Panchayats, **Bhubaneswar and Rangeilunda are the first blocks to review for overall expenditure**: they appear among the leaders on 5/9 measures. Neither dominates reported spending: Bhubaneswar accounts for 13.1% (Rs 3.33 crore), and Rangeilunda for 10.8% (Rs 2.73 crore). They are also the top two for spending linked to planned activities, at Rs 3.26 crore and Rs 2.57 crore, respectively. Bhubaneswar recorded the highest cashbook payments in 4/6 fiscal years, with 2024-2025 and 2025-2026 as exceptions. Rangeilunda had the largest gap against plan (Rs 9.11 crore below plan), followed by Kalimela (Rs 5.90 crore below plan).
>
> **Barpali and Bheden stand out on a different set of measures.** Bheden was among the leaders on 6/9 measures, while Barpali was among the leaders on the exceptions: spending linked to planned activities, sanction records and sanctioned amounts. Rangeilunda led on spending linked to planned activities in 2020-2021 (Rs 16.28 lakh); Barpali led in 2021-2022 (Rs 76.26 lakh). Neither block, nor Bheden, followed the quarter-by-quarter increase in linked spending seen in 9/16 blocks. The recorded share of spending linked to plans rose from 2.7% to 53.2% over six years; check linked amounts against cashbook totals before treating increases as higher expenditure.
>
> **Khallikote and Laxmipur merit a more targeted review of how expenditure is distributed.** Khallikote was the only block where the comparison of spending with plan was uneven across fund components, and it joined Laxmipur as an exception to the generally even spread across work types when spending was compared with sanctions. These exceptions concern the distribution of spending, not its size. Ongoing works accounted for most voucher-linked spending in 14/16 blocks; Laxmipur and Boipariguda showed no clear pattern by work status.
>
> (as of 2026-09-11)

**rule_off** — kept, 1 tries, 146 words, insights cited 6 of 12; left out: 1-00307, 2-00243, 1-00260, 2-00155, 2-00216, 1-00349

> **Bhubaneswar leads on overall expenditure, but no block dominates the sample.** Of the Rs 25.35 crore recorded in the annual Gram Panchayat report cards, Bhubaneswar had the highest expenditure at Rs 3.33 crore, followed by Rangeilunda at Rs 2.73 crore. The same two blocks ranked first and second for spending linked to planned activities. Bhubaneswar also led in cashbook payments in 4/6 fiscal years, but did not show the same lead in 2024-2025 or 2025-2026.
>
> **Rangeilunda stands out for the gap against plan.** Its recorded spending was Rs 9.11 crore below plan, the largest gap in the sample, followed by Kalimela at Rs 5.90 crore below plan. For spending linked to planned activities, Rangeilunda led in 2020-2021, while Barpali led in 2021-2022. Those rankings are worth checking against the cashbook: more spending recorded against planned activities does not, by itself, mean more money was paid out.
>
> (as of 2026-09-11)

#### L03 — What is unusual about water supply works?

**rule_on** — kept, 2 tries, 243 words, insights cited 11 of 11

> Drinking water and sanitation lead in planned tied grants in 19/20 sampled Gram Panchayats, but they rank lowest among focus areas on spending against sanction in 7/9 sampled districts. Bheden is the planning exception, with roads and sanitation leading. Ganjam and Rayagada are the spending exceptions: sanitation ranks lowest alongside maintenance of community systems in Ganjam and alongside GP office infrastructure in Rayagada. Water also stands out in Kalimela, where the Water Sufficient Village theme has the highest planned untied grant.
>
> Drinking water supply structures account for 47.8% of the Water Sufficient Village theme’s recorded spending shortfall against sanction, or Rs 66.60 lakh below sanction. Andhrua has the largest gap against sanction, at Rs 14.10 lakh, but the comparison covers only activities with a sanction on file—about one in six. Against plans, spending on these structures is Rs 2.26 crore below plan, with the largest gaps in Laxmipur and Bandhpali. Records with no sanctioning authority listed account for 69.8% of that gap. Voucher-linked spending is spread across the sample, with Sharagada and Kalimela recording the largest amounts.
>
> The records for abandoned works offer a focused reconciliation check: Chikilli and Govindapur account for all Rs 3.77 lakh in planned amounts for abandoned drinking water supply works, and none of that amount has a sanctioning authority listed. Separately, all spending labelled SC is recorded in Kalyansinghpur; a possible swap between the SC and ST labels remains unconfirmed, so the two components should not be compared.
>
> (as of 2026-09-11)

**rule_off** — kept, 1 tries, 229 words, insights cited 9 of 11; left out: d1-03870, 1-01793

> Drinking water and sanitation lead tied-grant plans in 19/20 sampled Gram Panchayats, but are the lowest-spending focus areas relative to sanction in 7/9 sampled districts. Bheden is the planning exception, with roads and sanitation leading. In Ganjam and Rayagada, sanitation is still among the lowest against sanction, but alongside maintenance of community systems and GP office infrastructure, respectively, rather than drinking water.
>
> Drinking water supply structures account for 47.8% of the spending shortfall against sanctions under the Water Sufficient Village theme, compared with 20.5% of the theme’s activities. Recorded spending on these structures is Rs 66.60 lakh below sanction, with the largest gap in Andhrua (Rs 14.10 lakh below sanction). The sanction comparison covers only activities with a sanction on file, about one in six.
>
> Against plans, spending on drinking water supply structures is Rs 2.26 crore below plan, with the largest gaps in Laxmipur (Rs 34.96 lakh below plan) and Bandhpali (Rs 24.70 lakh below plan). Records with no sanctioning authority listed account for 69.8% of the gap against plan. No sanctioning authority is listed for any of the abandoned works with planned funds; the full Rs 3.77 lakh planned for those works is recorded in Chikilli and Govindapur.
>
> Kalyansinghpur accounts for all Rs 1.79 lakh of spending labelled SC for these structures. Verify the labels before comparing SC and ST spending: a swap is suspected but unconfirmed.
>
> (as of 2026-09-11)

#### L05 — What patterns show up in sanctions across districts?

**rule_on** — kept, 2 tries, 177 words, insights cited 8 of 8

> In the sample, no district dominated the sanction count: Bargarh accounted for 17.7% and Ganjam for 17.5%. The distribution of sanctioned amounts differed by authority. Sarpanch-sanctioned amounts were spread across districts, with the largest shares in Khordha at 21.7% and Koraput at 19.0%. BDO-sanctioned amounts were more concentrated: Bargarh accounted for 68.8% of the amount and 66.0% of the activities in that comparison. These amount comparisons cover only activities with a sanction on file, about one in six.
>
> Over fiscal years, total sanctioned amounts declined in 5/9 districts; the average sanctioned amount per Gram Panchayat-year also declined in 5/9 districts. Both measures rose in Kandhamal, while neither showed a clear trend in Khordha or Ganjam.
>
> The same output codes and work types generally led by sanctioned amount. Code 101 ranked first among output types in 7/9 districts, and New/Fresh ranked first among work types in 7/9 districts. Khordha and Ganjam were exceptions to both patterns. Code 101 and Code 105 were the leading pair in 8/9 districts; in Malkangiri, Code 104 took the place of Code 105.
>
> (as of 2026-09-11)

**rule_off** — kept, 1 tries, 188 words, insights cited 8 of 8

> In the sample, no district dominated the 2,040 sanction records across 9 districts: Bargarh had the largest share at 17.7% (362 sanctions), closely followed by Ganjam at 17.5% (356 sanctions). The distribution of sanctioned amounts differed by authority. For Sarpanch sanctions, no district stood out: Khordha led at 21.7% (Rs 3.64 crore), followed by Koraput at 19.0% (Rs 3.19 crore). For BDO sanctions, Bargarh accounted for 68.8% (Rs 3.69 crore) of the amount recorded across 4 districts and 66.0% of the activities covered by those sanctions. These amount comparisons cover only activities with a sanction on file—about one in six. 
>
> Both the total sanctioned amount and the average per Gram Panchayat-year declined over fiscal years in 5/9 districts. Kandhamal showed an increase on both measures, while Khordha and Ganjam showed no clear trend on either. 
>
> The same two districts—Khordha and Ganjam—were exceptions to two other patterns: Code 101 led sanctioned amounts by output type in 7/9 districts, and New/Fresh led by work type in 7/9 districts. Code 101 and Code 105 were the leading output types in 8/9 districts; in Malkangiri, Code 101 and Code 104 led instead.
>
> (as of 2026-09-11)

---

## §5 The gate and the suite, baseline against final

| | Baseline (T0, on an untouched copy) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 46/48; red: `judge-model-evidenced`, `classifier-model-evidenced` (D69) | **47/49**; red: the same two |
| `python -m pytest DiscoverChat/tests -q` | 285 passed | **297 passed**, 0 failed |

```
PASS  every-insight-check-mode   log: left-out d1-00042 recorded, answer passes, retry reason silent on it; block: fails as before with its old keys; no floor (configured mode log)
PASS  place-resolution           14 rows of the T1 table reproduced; every note's quoted words resolve to its alternative; Kalimela block hands 61 lines
PASS  place-standing-check       the 5 correct sentences refused in the WP-D15 trial pass; the other end, a first place not held, a rank not given and a quarter not stated are caught; highest = most; a sentence citing no place fact is not checked (11 cases; mode log)
PASS  place-facts-optional       ... a dropped insight fails step 4 under block; an id not handed fails step 1
PASS  citation-checks-fire       clean prose passes; 7 seeded violations all caught (... dropped finding ...)
PASS  place-switch-off-identical switch off: 76 of 76 answers byte-identical ...
```

**A note on the baseline.** My first baseline run raced my own first edits: it ran in the background in the same mirror while I changed files, and it showed "5 failed". I re-took both baselines on `C:\dev\odisha-d15b`, an untouched copy of the same tree: 46/48 and 285, as D81 expects. The recorded check outputs for T1 point 3 were also re-taken there.

Files beside the mirror: `C:\dev\odisha-d15c-baseline-{gates,pytest}.txt`, `-final-{gates,pytest}.txt`, `-checks-{baseline,block,log}.json`, `-trial-logs\`, `-four-answers.md`.

---

## §6 Every model call and its cost

| What | Model | Calls | Tokens in | Tokens out | Cost |
|---|---|---|---|---|---|
| Live check, rule_on | gpt-6.2-sol | 92 | 257,580 | 53,341 | price not set |
| Live check, rule_off | gpt-6.2-sol | 53 | 139,841 | 26,869 | price not set |
| **Total** | | **145** | **397,421** | **80,210** | |

No judge call. Query embeddings were made only by the offline gate runs (memoised per process; negligible). No price is on file for `gpt-6.2-sol`, so no cost is guessed. The rule itself nearly halves the writer calls: 53 against 92 for the same 50 questions.

---

## §7 Decision journal

1. **Where the left-out ids are kept:** `Consolidated.left_out`, in `as_dict()`, so in the `/chat` `prose` record. It is computed from the shown narrative's tags against the insights handed, in the order handed, and is empty on a fall-back. It is not kept on the check result: step 4's `dropped` stays sorted, as before.
2. **`block` returns the old dict exactly.** The step's `mode`/`counts` keys are added only under `log`, so a caller (or a stored test output) that compares the step's dict sees no change under `block`.
3. **How the runner forces `block`:** a new `--every-insight block|log` that sets `config.EVERY_INSIGHT_CHECK` for the process. `--allow-unused-findings` is kept, as "log", so old commands still run.
4. **The T4 offline run covers every attempt, not only the shown text.** The five false alarms it must clear were first-attempt refusals.
5. **"among the …" is read only as "among the highest/lowest/most/fewest of|among|in"** (the first-place form), plus "one of the …". An ordinal after "among" ("among the 3 highest") was never a standing phrase.
6. **The baselines were re-taken on an untouched copy** after the race described in §5.
7. **The four answers:** "the first three held questions by id that name no place" taken in the held file's order (L02, L03, L05). L04 names Cuttack.

---

## §8 What in this brief was wrong or silent

1. **T0's clean-tree precondition** could not be met as written: the PM's own files were uncommitted. The operator's instruction to proceed covered it (top of the report).
2. **The step 7 word list catches non-numbers:** "majority" inside a group name ("SC-majority", "ST-majority", 6 lines) and "quarter(s)" meaning a calendar quarter (5 lines). It is a log, so nothing is refused, but the log is noisier than it needs to be. The word list is data (`number_words.json`), not in this brief's scope, and I did not change it. Proposed: skip "majority" after a hyphen, and "quarter(s)" next to a year, "Q1–Q4" or "by quarter".
3. **The page's cost of R25 is now measured:** 15 of 50 answers lose a card or a chart. `prose.left_out` is ready for WP-D16 if the page should list what was left out.
4. **Seven place answers cite fewer than half their insights** (all place answers, none of the no-place ones). No answer cites none. If the PM wants a floor after all, this is the evidence; the brief rules one out.
5. **Nothing found in the brief that shipped differently from what it describes.** The line numbers in "What exists" matched the tree.

**Next:** WP-D15b (spelling), then WP-D17, as the operator asked.

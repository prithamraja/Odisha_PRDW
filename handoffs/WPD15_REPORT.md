# WP-D15 report — place profile sheets: into the chat

**Brief:** `handoffs/WPD15_profile_serve.md`. **Spec:** `handoffs/PROFILE_SHEET_SPEC.md` (§3, §7, §11).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d15`, results copied back to the Drive repo after each task.
**Commits (on `master`, not pushed, not deployed):** `0c6ae3a` T1, `0ac7ef6` T3 (with the five settings), `2100584` T2, `255b2aa` T4+T5, `3f5c8c1` T7 (gate lines, tests, the switch-off baseline), `ced14fd` T6 (the trial; step 6 default set to `log`), then this report.

**Outcome in one line.** Pass marks 1, 2 and 3 hold, so `DISCOVERCHAT_PROFILE_SHEETS` ships **on**. Pass mark 4 does not: step 6 made five refusals in the trial and all five were false alarms. As the brief says, its default is now **`log`**, and this is a finding for the PM, not a failure of the package.

---

## §0 The gate, with evidence

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | The T1 table reproduced by tests and by `place-resolution` | **PASS** | 13 of 13 rows (§2); every note's quoted words resolve to the alternative |
| 2 | A no-place turn is untouched: prompt byte-identical; answers identical with the switch off (pass mark 3) | **PASS** | Prompts for all 47 held questions that name no place: 47 of 47 byte-identical to the pre-WP hashes. Offline answers with the switch off: 76 of 76 byte-identical to the pre-WP baseline (gate line `place-switch-off-identical`). With the switch on, the 49 answers that name no place are also unchanged |
| 3 | Gate: baseline + five new lines green, the two D69 reds unchanged, nothing green turned red; suite green | **PASS** | Gate 41/43 → **46/48**; reds are still only `judge-model-evidenced` and `classifier-model-evidenced`. Suite 247 → **285 passed**, 0 failed (§5) |
| 4 | Trial pass marks 1 and 2 hold; mark 4 reported with every step 6 refusal judged | **PASS** (marks 1, 2); mark 4 **not met → step 6 set to log** | Wrong numbers shown: 0 in every arm. Lost: sheet 4 of 54 (7.4%) against a limit of 11.1%. Step 6: 5 refusals, 5 false alarms (§4.5) |
| 5 | The report holds the trial tables, the L06 answers in full and the cost of every model call | **PASS** | §4, §4.9, §6 |

The pass marks:

| Mark | What | Result |
|---|---|---|
| 1 | Wrong numbers shown, every arm | **0** (current 0, sheet 0, sheet_choose 0, sheet_midsize 0, by an independent second pass) |
| 2 | sheet loses no larger a share than current + 1 in 18 | current 1/18 (5.6%); sheet 4/54 (7.4%); limit 11.1% — **holds** |
| 3 | Switch off: offline answers byte-identical to baseline | **76 of 76** |
| 4 | Step 6 made no false alarm | **5 false alarms, 0 true catches** → default `log` |

---

## §1 What was built, file by file

| File | Change | Task |
|---|---|---|
| `DiscoverChat/slots.py` | `geography()` gains one field, `mentions`: every occurrence of every accepted name, with its level, code (GPs), name and position. The four existing fields keep their values (a test proves it). `Slots.mentions` is **not** in `as_dict()`, so the logged retrieval payload is unchanged | T1 |
| `DiscoverChat/place.py` (new) | `resolve()` (the five T1 rules), `PlaceFact`, `groups_for()` (lines as stored, in the store's order; `main` = A1–A7), `render_for_writer()`, `used_in()` (`lines_used`), `fallback_groups()` / `main_lines()` / `render_groups()` (T4), `payload()` (T5), `record_payload()` (`/record` for `p-` ids), `open_store()` (never raises) | T1, T2, T4, T5 |
| `DiscoverChat/checks.py` | Step 1 knows the handed place-fact ids; step 2 binds numerals to place facts; **all answers:** en/em dashes (and the two hyphen look-alikes U+2010, U+2011) read as a hyphen, and a short fiscal year matches the long one when the years are consecutive; step 4 counts mined insights only; step 5 holds an A7 "below plan" line to the existing wrong-word test; **new step 6** (`check_standing`, `standing_failure_reason`); **new step 7** (`scan_number_words`) | T3 |
| `DiscoverChat/number_words.json` (new) | The step 7 word list, as data beside the other trigger lists | T3 |
| `DiscoverChat/config.py` | `DISCOVERCHAT_PROFILE_SHEETS` (1), `_PROFILE_INSIGHT_CAP` (8), `_PROFILE_MAX_PLACES` (3), `_STANDING_CHECK` (**log**, see §4.5), `_NUMBER_WORDS` (log); all five in `knobs()` | T3/T5 |
| `DiscoverChat/context_brief.py` | `PLACE_FACTS_PARAGRAPH`, the R18 text character for character. Nothing else changed | T2 |
| `DiscoverChat/writer.py` | `build_consolidation_prompt(..., place_groups=)`: PLACE FACTS blocks before FINDINGS, the R18 paragraph directly before "Return only the finished prose."; with no place groups, `_build_plain()` builds the old string unchanged. `consolidate(..., place_groups=)` passes the place facts to the check and keeps `last_prose` for T4; a shown answer's number words are logged (`kind: number_words_shown`) | T2, T3, T4 |
| `DiscoverChat/assemble.py` | On a retrieve / decompose / navigate-fall-through turn with a sheet store open: `place.resolve` → `_answer_with_sheets()` (cap 8, writer with place facts, T4 fall-back groups, the note as the first line, `place` payload, `retrieval["place"]`). `Answer` gains `place`, `place_facts`, `lead`. A turn with no place runs the old code untouched | T2, T4, T5 |
| `DiscoverChat/render.py` | `place_citation_map()` (T5 shape, `is_profile: true`, labelled display sentence); `to_html(..., place_facts=, lead=)` wraps `p-` tags and puts the note at the start of the narrative paragraph; numerals read on dash-normalised text | T5 |
| `DiscoverChat/main.py` | Opens the sheet store once at start-up (never fails to start; reason in `/health` → `profile_sheets`); the `place` response field; `answer_html` with place facts and lead; `/record/p-…` (JSON and HTML) | T5 |
| `DiscoverChat/gates.py` | Five new lines (§5); the R18 paragraph added to `consolidation-prompt-is-the-operators` as ratified addition 3 (D78); `numerals-traceable` also accepts the sheet lines an answer shows (see §8 item 2) | T7 |
| `DiscoverChat/tests/test_place_answers.py` (new) | 38 tests (§5) | T7 |
| `DiscoverChat/experiments/run_writer_trial.py` | `--sheets` (each turn through `Assembler.answer`, search and judge replaced by the held picks — no T1–T4 logic copied), `--place-only`, `--repeats`, `--ask`, `--ask-only`, `--out-dir`; an independent second pass over every shown answer | T6 |
| `DiscoverChat/experiments/writer_trial_questions.json`, `judge_picks.json` | Three two-place questions appended and held (TWO-01..03); the 50 held entries byte-identical (checked entry by entry and as text) | T6 |
| `handoffs/WPD15_trial/` | The runner's JSON and markdown for five runs; `analyse.py` → `tables.md`, `review_items.json`; `L06_prompt_as_sent.txt`; the switch-off baseline (`offline_baseline_answers.json.gz`, `offline_baseline_vectors.npy`) | T6, T7 |

Not touched: everything on the do-not-touch list (`Insights/**`, `profile_store.py`, judge, classifier, retrieval, corpus, layout, glossary, navigate, session, `frontend/**`, `Ask/**`, `deploy/**`, `Data/**`, every `.env`, the plan and the spec).

---

## §2 The T1 table — expected against actual

| Text | Expected | Actual | Match |
|---|---|---|---|
| What should I know about Kalimela? | block 3843, full; alt GP 119936; note | block 3843, full; alt GP 119936 (ask "Kalimela GP"); note | yes |
| What should I know about Kalimela GP? | GP 119936, full; alt block 3843; note | GP 119936, full; alt block 3843 (ask "Kalimela block"); note | yes |
| How is Kalimela Gram Panchayat doing | GP 119936, full | GP 119936, full (alt block 3843, note) | yes* |
| the panchayat of Kalimela | GP 119936, full | GP 119936, full (alt block 3843, note) | yes* |
| How is Kalimela block doing | block 3843, full | block 3843, full (alt GP 119936, note) | yes* |
| Kalyansinghpur | block 3914, full; alt GP 121162; note | block 3914 "Kalyansingpur block", full; alt GP 121162 (ask "Kalyansinghpur GP"); note | yes |
| How is Chikilli doing? | that GP, full; no alt, no note | GP 117835, full; none | yes |
| How is Barpali block doing? | block 3676, full | block 3676, full | yes |
| How is Khordha district doing overall? | district 321, full | district 321, full | yes |
| How is Itipur doing in Bhubaneswar block | GP Itipur, full (parent dropped) | GP 119605, full; Bhubaneswar block dropped as its parent (logged) | yes |
| Compare Kalimela and Bheden | blocks 3843 and 3678, main each; two alternatives | blocks 3843, 3678, main; alts GP 119936, GP 116438; one note | yes |
| Compare Kalimela, Bheden, Laxmipur and Boipariguda | no sheet (four places) | no sheet; `retrieval.place.why_no_sheet` = "4 places named, more than 3" | yes |
| Which blocks stand out on expenditure? | no sheet | no sheet | yes |

\* Rule 5 applies whenever rule 2 chose between two levels, including when the words decided it, so these three rows also carry the note and the alternative. The brief's table lists none for them. I read the table as stating only the place answered (rule 5 says "only when rule 2 chose between two levels", and it did). If the PM meant "no note when the officer was explicit", it is a one-line change in `resolve()` (§8 item 7).

The notes, as written:
- `This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".`
- `This answer is about Kalimela Gram Panchayat. For the block, ask about "Kalimela block".`
- `This answer is about Kalyansingpur block. For the Gram Panchayat, ask about "Kalyansinghpur GP".`
- Two places: `This answer is about Kalimela block and Bheden block. For the Gram Panchayats, ask about "Kalimela GP" or "Bheden GP".`

---

## §3 One full prompt as sent: L06, `sheet` arm, run 1, first attempt

From the call log (`logs/calls.jsonl`, turn `wt-sheet-L06-r1`); 3,824 prompt tokens. Also in `handoffs/WPD15_trial/L06_prompt_as_sent.txt`. The 18 held insights are capped to the first 8.

```
You are writing for a decision-aid system used by government officials in Odisha's Department of Panchayati Raj & Drinking Water. The system automatically analyses village-level planning and spending records — development plans, sanctions, payments, works and photo evidence from Gram Panchayats, blocks, and districts — and surfaces patterns worth an official's attention. The current data is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.

Your readers are busy block-, district- and state-level officials, not data analysts. They read these insights to decide where to direct attention: which districts to question, which records to reconcile, which local practices to check at the next review.

Turn the analytical findings below into clear, concise prose for a senior government official.

Do not rewrite each finding separately. Identify overlapping or repeated findings, consolidate them into a small number of underlying patterns, and explain those patterns as a coherent narrative. It is very important that you do not make causal claims - none of our data can be used to determine causality. Do not fabricate or overstate data.

Preserve important numbers and exceptions where useful. Ignore ranking metadata such as "not in the ranked shortlist." Avoid database-style language and do not infer causes that are not supported by the findings.

After every figure and every claim, tag the finding it comes from with its id in square brackets, exactly as given, e.g. [1-00235]. A sentence drawing on two findings carries both tags.

Use figures exactly as they appear in the findings. Do not compute new numbers — no percentages, sums, or differences that are not stated in a finding.

Some answers also come with PLACE FACTS: standard figures about the place the officer asked about, each with an id starting p-. Start from the place facts that answer the question, then bring in the findings. You do not have to use every place fact. Tag them the same way as findings.

Return only the finished prose.

The analysis was run as of 2026-09-11.
The officer asked: What should I know about Kalimela?

PLACE FACTS — Kalimela block
[p-block-3843-A1] Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
[p-block-3843-A2] 392 of them (46.0%) have no cost attached.
[p-block-3843-A3] Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.
[p-block-3843-A4] Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 5th highest of 16 blocks. The middle value is Rs 1.51 crore.
[p-block-3843-A5] It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.
[p-block-3843-A6] Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.
[p-block-3843-A7] Spending is Rs 5.90 crore below plan.
[p-block-3843-B-2020-2021] In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.
[p-block-3843-B-2021-2022] In 2021-2022: 32 activities, Rs 64.43 lakh planned, Rs 33.21 lakh spent, 51.5% of the plan.
[p-block-3843-B-2022-2023] In 2022-2023: 28 activities, Rs 35.77 lakh planned, Rs 28.84 lakh spent, 80.6% of the plan.
[p-block-3843-B-2023-2024] In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.
[p-block-3843-B-2024-2025] In 2024-2025: 268 activities (72 with no cost), Rs 3.00 crore planned, Rs 31.60 lakh spent, 10.5% of the plan.
[p-block-3843-B-2025-2026] In 2025-2026: 169 activities (124 with no cost), Rs 58.60 lakh planned, Rs 11.20 lakh spent, 19.1% of the plan.
[p-block-3843-C-drinking-water] Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.
[p-block-3843-C-land-improvement] Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.
[p-block-3843-C-maintenance-of-community-system] Maintenance of community system: 100 activities, Rs 62.03 lakh planned, Rs 11.54 lakh spent.
[p-block-3843-C-sanitation] Sanitation: 118 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent.
[p-block-3843-C-roads] Roads: 27 activities, Rs 52.19 lakh planned, Rs 19.72 lakh spent.
[p-block-3843-C-poverty-allevation-programme] Poverty allevation programme: 114 activities and Rs 37.09 lakh planned, with nothing spent.
[p-block-3843-C-education] Education: 42 activities, Rs 29.23 lakh planned, Rs 13.21 lakh spent.
[p-block-3843-C-water-conservation] Water Conservation: 8 activities, Rs 25.15 lakh planned, Rs 4.21 lakh spent.
[p-block-3843-C-administrative-technical-support] Administrative & Technical Support: 13 activities, Rs 19.40 lakh planned, Rs 12.23 lakh spent.
[p-block-3843-C-markets-and-fairs] Markets and fairs: 4 activities, Rs 12.50 lakh planned, Rs 3.47 lakh spent.
[p-block-3843-C-gp-office-infrastructure] GP Office Infrastructure: 2 activities, Rs 8.84 lakh planned, Rs 8.64 lakh spent.
[p-block-3843-C-health] Health: 57 activities, Rs 7.71 lakh planned, Rs 5.60 lakh spent.
[p-block-3843-C-women-and-child-development] Women and child development: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent.
[p-block-3843-C-public-distribution-system] Public distribution system: 5 activities and Rs 3.00 lakh planned, with nothing spent.
[p-block-3843-C-rural-electrification] Rural electrification: 7 activities, Rs 1.44 lakh planned, Rs 1.43 lakh spent.
[p-block-3843-C-social-welfare] Social welfare: 20 activities and Rs 68,500 planned, with nothing spent.
[p-block-3843-C-technical-training-and-vocationa] Technical training and vocational education: 14 activities, Rs 15,000 planned, Rs 15,000 spent.
[p-block-3843-C-agriculture] Agriculture: 12 activities, with no planned cost and nothing spent.
[p-block-3843-C-animal-husbandry] Animal husbandry: 1 activity, with no planned cost and nothing spent.
[p-block-3843-C-fuel-and-fodder] Fuel and fodder: 5 activities, with no planned cost and nothing spent.
[p-block-3843-C-khadi] Khadi: 1 activity, with no planned cost and nothing spent.
[p-block-3843-C-non-conventional-energy-sources] Non-conventional energy sources: 4 activities, with no planned cost and nothing spent.
[p-block-3843-C-rural-housing] Rural housing: 5 activities, with no planned cost and nothing spent.
[p-block-3843-C-welfare-of-the-weaker-sections] Welfare of the weaker sections: 15 activities, with no planned cost and nothing spent.
[p-block-3843-CT-4] Theme 4 - Water Sufficient Village: 174 activities, Rs 3.99 crore planned, Rs 65.19 lakh spent.
[p-block-3843-CT-6] Theme 6 - Self-sufficient Infrastructure in Village: 310 activities, Rs 2.27 crore planned, Rs 51.51 lakh spent.
[p-block-3843-CT-5] Theme 5 - Clean and Green Village: 122 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent.
[p-block-3843-CT-8] Theme 8 - Village with Good Governance: 116 activities, Rs 45.93 lakh planned, Rs 8.64 lakh spent.
[p-block-3843-CT-unmapped] Unmapped theme: 49 activities, Rs 34.90 lakh planned, Rs 15.70 lakh spent.
[p-block-3843-CT-3] Theme 3 - Child Friendly Village: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent.
[p-block-3843-CT-1] Theme 1 - Poverty Free and Enhanced Livelihoods Village: 26 activities, Rs 15,000 planned, Rs 15,000 spent.
[p-block-3843-D-plan] Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).
[p-block-3843-DS-xv-finance-commission] XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned.
[p-block-3843-DS-5th-state-finance-commission] 5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned.
[p-block-3843-DS-own-funds] Own Funds: 2 approvals, Rs 2.74 lakh sanctioned.
[p-block-3843-D-authority] Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2.
[p-block-3843-E1] 154 works are marked ongoing, the 5th most of 16 blocks. The middle value is 104.
[p-block-3843-E2] 13 works are marked completed, out of 17 in the whole sample.
[p-block-3843-E3] 22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.
[p-block-3843-E4] 129 activities have photo evidence (553 uploads), the 5th most of 16 blocks. The middle value is 83.
[p-block-3843-E5] 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).
[p-block-3843-F1] 168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. The middle value is 104.
    (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
[p-block-3843-F2] 168 activities have a technical approval on file.
[p-block-3843-G1] Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.
[p-block-3843-G3] 33.3% of the payments are linked to a planned activity, the 6th lowest of 16 blocks. The middle value is 46.5%.
[p-block-3843-H2] 49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.
[p-block-3843-I4] Kalimela block has 1 Gram Panchayat in the data.
[p-block-3843-J-119936] Kalimela Gram Panchayat: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan.

FINDINGS
[d1-30946] Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 34.3% (Rs 70.85 lakh), then Sanitation at 20.0% (Rs 41.40 lakh). The remaining 22 together account for Rs 94.29 lakh. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 34.3% of spending, general component -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-31150] Within Gram Panchayat Kalimela, activities planned totals 852 activities across 6 fund component values. It is concentrated: (not recorded) accounts for 80.3% of it (684 activities). The remaining 5 together account for 168 activities. 684 rows carry no fund component on file; they are counted here as (not recorded) and account for 684 activities.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-31128] Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 4 scheme values. It is concentrated: (not recorded) accounts for 72.7% of it (Rs 5.57 crore). The remaining 3 together account for Rs 2.09 crore. 684 rows carry no scheme on file; they are counted here as (not recorded) and account for Rs 5.57 crore.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-30939] Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 48.8% (Rs 3.74 crore), then Land improvement at 9.7% (Rs 73.95 lakh). The remaining 22 together account for Rs 3.18 crore. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 48.8% of planned cost -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-30937] Within Gram Panchayat Kalimela, expected beneficiaries totals 8,820 people across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 1 - Poverty Free and Enhanced Livelihoods Village at 45.1% (3,978 people), then Theme 6 - Self-sufficient Infrastructure in Village at 15.5% (1,367 people). The remaining 5 together account for 3,475 people. For size: Theme 1 - Poverty Free and Enhanced Livelihoods Village holds 3.1% of the 852 activities behind these totals, against 45.1% of expected beneficiaries -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-31016] Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 2 activity type values. It is concentrated: Public Works accounts for 100.0% of it (Rs 2.06 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs 5,000. For size: Public Works holds 82.3% of the 852 activities behind these totals, against 100.0% of spending, general component -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-31173] Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 22 asset category values. It is spread across them without one standing out: the largest is Uncategorised at 28.0% (Rs 2.14 crore), then Water Sources & Structures at 23.9% (Rs 1.83 crore). The remaining 20 together account for Rs 3.68 crore. For size: Uncategorised holds 57.5% of the 852 activities behind these totals, against 28.0% of planned cost -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
[d1-30940] Within Gram Panchayat Kalimela, tied grant planned totals Rs 92.28 lakh across 24 focus area values. It is spread across them without one standing out: the largest is Sanitation at 50.5% (Rs 46.59 lakh), then Drinking water at 49.5% (Rs 45.69 lakh). The remaining 22 together account for Rs 0. For size: Sanitation holds 13.8% of the 852 activities behind these totals, against 50.5% of tied grant planned -- a group's total grows with how much of the work it holds.
    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
```

---

## §4 The trial

**Set-up.** Writer calls only, on the held judge picks (built 2026-11-24, judge `gpt-6.2-sol`). The brief's 18 place questions, plus three new two-place questions: TWO-01 "Compare Kalimela and Bheden" (two blocks, by R4), TWO-02 "How does Chikilli compare with Hirlipali?" (two Gram Panchayats), TWO-03 "Compare Khordha and Cuttack districts". The `--place-only` filter (the shipped `place.resolve`) picked exactly these 21. Under R4 the 18 resolve to 5 Gram Panchayat sheets, 7 block sheets and 6 district sheets, as the brief predicted. Runs were made in parallel; causal check `log`, direction `block`, standing `block` (the shipped default at the time).

| Arm | What | Runs |
|---|---|---|
| `current` | today's path, the held picks as they are (all of them, no cap) | 1 per question |
| `sheet` | the package as shipped | 3 per question |
| `sheet_choose` | the same, with the every-insight rule off (`--allow-unused-findings`) | 3 per question |
| `sheet_midsize` | `sheet`, written by `gpt-6-luna` | 1 per question |
| `sheet_no_insight` | two out-of-scope questions that name a place, with no insight at all (see §4.8) | 1 each |

### 4.1 Per arm, all 21 questions

| | current | sheet | sheet_choose | sheet_midsize |
|---|---|---|---|---|
| Answers | 21 | 63 | 63 | 21 |
| Kept | 20 (95%) | 59 (94%) | **63 (100%)** | 13 (62%) |
| Lost (both attempts refused) | 1 — unknown id | 4 — all step 2 | 0 | 8 — 7 step 2, 1 step 4 |
| Passed on the first try | 2 (10%) | 3 (5%) | **60 (95%)** | 1 (5%) |
| **Wrong numbers shown (second pass)** | **0** | **0** | **0** | **0** |
| Fall-back lines not word for word | 0 | 0 | 0 | 0 |
| Writer calls | 40 | 123 | 66 | 41 |
| Seconds per answer, middle | 23.4 | 19.8 | 9.7 | 43.1 |
| Words, middle (kept) | 278 | 254 | 213 | 405 |
| Sentences, middle (kept) | 13.5 | 13 | 11 | 17 |
| Words per sentence, middle (kept) | 20.3 | 19.7 | 19.6 | 23.8 |
| Insights handed, middle | 18 | 8 | 8 | 8 |
| Insights cited, middle (kept) | 17 | 8 | 4 | 8 |

What failed first drafts: `sheet` 60 of 63 on step 4 (an insight left out), 5 on step 2; `current` 19 of 21 on step 4; `sheet_choose` 2 on step 2 and 1 on step 6. The every-insight rule is what costs the second call, as in the writer tests of 2026-11-24.

The four `sheet` losses, all caught by step 2 (the check working): GEO-19 run 1 (40.44, cited to nothing), GEO-30 runs 2 and 3 (37.37 and three other figures not in any cited record), GEO-32 run 2 (162 and 14.3, cited to sheet lines that do not hold them).

### 4.2 Pass mark 2

| Arm | Lost on the brief's 18 | Share |
|---|---|---|
| current (1 run each) | 1 of 18 | 5.6% |
| sheet (3 runs each) | 4 of 54 | 7.4% |

Limit = 5.6% + 1/18 = 11.1%. **Holds.** For reference: sheet_choose 0 of 54; sheet_midsize 8 of 18 (44%); the two-place questions in `sheet`, 0 of 9.

### 4.3 Place facts used (kept answers)

| Arm | Kept | Lines used, middle (most) | Use A6 | Use a line with a standing | Both |
|---|---|---|---|---|---|
| sheet | 59 | 12 (17) | 57 (97%) | 59 (100%) | 57 (97%) |
| sheet_choose | 63 | 13 (18) | 62 (98%) | 63 (100%) | 62 (98%) |
| sheet_midsize | 13 | 16 (20) | 13 (100%) | 13 (100%) | 13 (100%) |

Rows cited across the kept `sheet` answers (a line counted each time it is cited): A3 67, A6 66, A2 65, A5 64, A1 54, E5 47, A7 43, A4 38, E2 38, B 33, I4 30, J 28, F1 28, G3 24, E4 15, C 11, H1 8, G1 6, E3 6, CT 6, F2 2, E1 1. The plain facts (A1–A6) are almost always there, which is what R19's "the model picks" risked losing. It did not lose them.

### 4.4 How far three runs differ

Lines used in all three runs / in two / in one, summed over the 21 questions (per-question tables in `WPD15_trial/tables.md` §4):

| Arm | In all 3 | In 2 | In 1 |
|---|---|---|---|
| sheet | 201 (72%) | 37 (13%) | 43 (15%) |
| sheet_choose | 220 (74%) | 37 (12%) | 41 (14%) |

The two-place answers are the steadiest: TWO-01 and TWO-03 used the same 14 lines (A1–A7 of each place) in all three runs. The least steady is GEO-29 (Khordha): 9 in all three, 5 in two, 3 in one.

### 4.5 Step 6: every refusal, judged

Five refusals, all on a first attempt. None was in the `sheet` arm, where step 6 refused nothing.

| Arm, question | The phrase | The sentence (tags removed) | The cited line says | Judgement |
|---|---|---|---|---|
| sheet_choose T04 r3 | "the highest of" | Barpali has the most planned activities in the sample: 1,447 across its 2 Gram Panchayats, the highest of 16 blocks. | A1: "the most of 16 blocks" | **False alarm.** True rank 1; "highest" for a count where the line says "most" |
| sheet_midsize GEO-18 | "7th highest" | Its 808 planned activities rank 7th highest, but its planned cost of Rs 3.36 crore is the 7th lowest; … | A1: "7th most" | **False alarm.** Same rank, "highest" for "most" |
| sheet_midsize GEO-18 | "4th highest" | … 167 works are marked ongoing, the 4th highest count among 16 blocks, … | E1: "4th most" | **False alarm.** Same |
| sheet_midsize GEO-29 | "4th highest" | … its activity count is the 4th highest among 9 districts. | A1: "4th most" | **False alarm.** Same |
| sheet_midsize TWO-01 | "the highest in" | Their planned costs are also among the highest in the comparison: Rs 7.65 crore in Kalimela and Rs 7.22 crore in Bheden … | A3s: "2nd highest", "3rd highest" | **False alarm.** "Among the highest" claims no single rank |

**True catches: 0. False alarms: 5.** By the brief's rule, step 6 now defaults to `log` (`config.STANDING_CHECK`; `DISCOVERCHAT_STANDING_CHECK=block` turns blocking back on). The gate line `place-standing-check` still proves the step fires: it pins `block` for the test.

What would fix it, for the PM to rule on (not done): treat "highest" and "most" as the same end word, and "lowest" and "fewest" likewise (the spec's "counts say most/fewest" is a wording rule for the builder, not something an officer's sentence has to follow); and do not read "among the highest/lowest" as a first place. All five false alarms would then pass. The step's real targets would still be caught: "4th highest" for "4th lowest", "the most" for "5th most", a quarter the line does not state.

### 4.6 Step 7: every log line, judged

23 log lines in shown answers. Every one is **supported** by the lines its sentence cites:

| Kind | Lines | Example | Supported? |
|---|---|---|---|
| A rank in words | 18 | "both the second lowest among the 9 sampled districts" (Kandhamal A1 "2nd fewest", A3 "2nd lowest"); "the third fewest in the sample" (Haldikudar E4 "3rd fewest"); "the fourth highest in the sample" (Sharagada A3 "4th highest"); "It ranks third for both sanctions … and spending" (Barpali A4, A5 "3rd highest") | 18 of 18 |
| A fraction in words | 1 | "just over half is in village infrastructure (Rs 9.08 crore, or 50.9%)" (d1-14794: 50.9%) | yes |
| A list marker, no number stated | 3 | "Second, check theme assignments: …"; "Second, verify work status: …"; "Second, reconcile cashbook payments …" | not a figure |
| The midsize writer, a rank | 1 | "its spending is the second lowest" (Lahunipara A5 "2nd lowest") | yes |

So the writer writes ranks as words often (about one answer in four), and in this trial correctly every time. Note: had it written "2nd lowest" where Kandhamal's A1 says "2nd fewest", step 6 in `block` mode would have refused it (§4.5).

### 4.7 Fall-backs

| Arm | Fall-backs | Place facts shown: most | middle | A1–A7 supplied by code |
|---|---|---|---|---|
| sheet | 4 | 10 | 10 | 0 |
| sheet_choose | 0 | – | – | 0 |
| sheet_midsize | 8 | 25 | 14 | 0 |

Every fall-back showed the place facts the writer itself cited in its last attempt. Code never had to supply A1–A7. The midsize fall-backs are long (up to 25 lines, plus 8 bare insight sentences), because that writer cites many lines.

### 4.8 Two by-year spending series in one answer

Code flagged 21 answers that cite a by-year sheet line (by plan year) **and** a month-cube insight (by payment year). I read all 21:

- **1 answer gives two different by-year series:** `sheet_midsize` GEO-07 (Boipariguda): "By comparison, 2024-2025 spending was 67.9% of plan, while 2025-2026 was 19.6%." (sheet B lines, plan year) and, two sentences on, "Linked spending totals Rs 1.18 crore across six years; the largest year share is 2022-2023 at 32.6% (Rs 38.62 lakh), followed by 2021-2022 at 20.0% (Rs 23.70 lakh)." (d2-01615, payment year). Nothing tells the officer the two use different years.
- **20 answers** cite one plan-year line beside the month-cube insight's closing sentence, "the linked share went from 2.7% to 53.2% across these six years". That is a ratio, not a spending series, so not two series. But see §8 item 5: that sentence is the same sample-wide figure in every place's breakdown, and the writer presents it as the place's own. This happens equally in `current`.

### 4.8b A place question with no insight, out of scope

The two offline-gate "no match" questions name a district, so with the sheets on they now reach the writer with that district's 63 lines and no insight. The writer refused both, correctly, and used no figure:
- *What is the price of onions in Cuttack market?* → "The supplied Cuttack records cover village planning and spending, not market prices. They do not show the price of onions."
- *What is the rainfall forecast for Koraput next week?* → "The records provided do not include a rainfall forecast for Koraput district. For next week's outlook, check the latest district forecast and weather warnings from the India Meteorological Department (IMD)." (The advice to check the IMD is the writer's own.)

`lines_used` was [] for both. Offline (no writer), the T4 rule shows Cuttack's A1–A7 and then today's honest-miss text (§8 item 3).

### 4.9 Writer time and tokens, current against sheet (the brief's 18)

| | current | sheet |
|---|---|---|
| Seconds per answer, middle | 23.5 | 20.2 |
| Seconds per writer call, middle | 12.2 | 9.8 |
| Writer calls per answer, mean | 1.89 | 1.94 |
| Prompt tokens per answer, middle | 5,089 | 7,803 |
| Completion tokens per answer, middle | 1,169 | 1,151 |

Handing the whole sheet (about 61 lines) and capping insights at 8 makes each request about 1,400 tokens longer (2,471 → 3,877 per call). It is not slower: the cap leaves fewer insights to weave in.

### 4.10 Reported, not pass marks

- **A6 and a standing line in kept `sheet` answers:** 57 of 59 (97%).
- **Three-run agreement:** 72% of the lines used appear in all three runs (§4.4).
- **Mid-size (evidence for R17's fallback plan):** `gpt-6-luna` lost 8 of 18 (44%) against `sheet`'s 7.4%, and wrote longer answers (405 words, 23.8 words per sentence, against 254 and 19.7). The losses are mostly not "too many lines". Seven of the eight are step 2 refusals of the form "no finding cited in this sentence": luna tags the end of a paragraph, not each sentence. A smaller sheet would not fix that, so the evidence does **not** yet point to R17's 25-line core. It points to luna's tagging. luna also wrote two of the five step 6 false alarms.
- **`sheet_choose` against `sheet` (evidence for the every-insight rule):** with the rule off, nothing was lost (0 of 63 against 4), 95% passed first try (against 5%), answers took half the time (9.7 s against 19.8 s) and were shorter (213 words against 254). The writer cited a middle of 4 of the 8 insights. It used slightly more place facts (13 against 12) and kept A6 and a standing line in 98%.

### 4.11 L06 Kalimela, every answer in full

What the officer would see (the note and the run stamp included for the sheet arms; the `current` answer is the narrative only, as `current` has no code-written lines). Each heading gives the place facts used, in the order first cited.

#### current, run 1 — kept, 2 tries, 283 words, place facts used: -

> Kalimela’s plan lists 852 activities at a total cost of Rs 7.65 crore. The first review priority is to reconcile missing classifications: 684 activities have no fund component recorded, while entries with no scheme account for 72.7% of planned cost. A further classification issue is that 57.5% of activities have no asset category. Recorded sanctions total Rs 2.08 crore, but cover only about one in six activities.
>
> The cashbook is the next check. The recorded gap between planned cost and spending linked to planned activities is Rs 5.90 crore. The fiscal years 2024-2025 and 2023-2024 had both the highest planned costs and the largest gaps. The share of spending linked to planned activities rose from 2.7% to 53.2%, so check the linked records against the cashbook before treating the gap as underspending or the rise in linked spending as a rise in actual expenditure.
>
> Drinking water was the largest focus area in planned cost, recorded sanctions and general-component spending. Sanitation was second in recorded sanctions and general-component spending and had a slightly larger planned tied-grant allocation than drinking water. Nearly all general-component spending was on public works, with 68.9% on work classified as new and 91.8% on work still marked ongoing. At the next review, check whether those status entries are current: only 13 completions are recorded, while 129 activities have photo evidence, most often under Clean and Green Village and Water Sufficient Village.
>
> The beneficiary figures describe expected reach, not confirmed delivery. Of the 8,820 expected beneficiaries, 75.8% were in 2024-2025. Looking at the same total by activity type, 71.8% were associated with activities listed as costless; by theme, the largest share was for Poverty Free and Enhanced Livelihoods Village, at 45.1%.

#### sheet, run 1 — kept, 2 tries, 251 words, place facts used: I4, J, A1, A3, A5, A6, B, B, C, A2, G3, E5

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented in the sample by one Gram Panchayat, Kalimela. Its 852 planned activities carried a recorded cost of Rs 7.65 crore, the 2nd highest of 16 blocks in the sample. Yet spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest in the sample. Spending was 11.1% of plan in 2023-2024 and 10.5% in 2024-2025, the two years with the largest planned budgets.
>
> Drinking water is a priority for review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. All planned tied grants were for sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending figures, public works accounted for nearly all spending, with drinking water and sanitation the largest areas. The Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries but 3.1% of planned activities; these are planning estimates, not a count of people reached.
>
> At the next review, reconcile the plan, approvals and payments before drawing conclusions about delivery. No cost was recorded for 392 activities (46.0%). Activities without a scheme on file accounted for Rs 5.57 crore of planned cost; 684 activities had no fund component recorded, and 57.5% had no asset category. Only 33.3% of cashbook payments were linked to a planned activity. Also check the status of the 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost already recorded as spent.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet, run 2 — kept, 2 tries, 315 words, place facts used: I4, J, A1, A3, A5, A6, B, B, B, C, A2, F1, G1, G3, E5, E3

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented in the sample by Kalimela Gram Panchayat alone. Its 852 planned activities had a recorded cost of Rs 7.65 crore, the 2nd highest of 16 blocks in the sample. Recorded spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest share in the sample. Spending was 93.6% of plan in 2020-2021, compared with 11.1% in 2023-2024 and 10.5% in 2024-2025. 
>
> Drinking water is the first sector to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent on planned activities. The tied-grant plan was split almost evenly between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending figures, public works accounted for Rs 2.06 crore, compared with Rs 5,000 for beneficiary-oriented programmes; drinking water and sanitation were the largest spending areas in that breakdown. Separately, the Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries (3,978 people), against 3.1% of planned activities. 
>
> At the next review, reconcile the planning, approval and payment records before drawing conclusions about delivery. Of the planned activities, 392 (46.0%) had no cost attached, and 684 (80.3%) had no fund component recorded. Activities with no scheme on file accounted for Rs 5.57 crore (72.7% of planned cost), and activities without an asset category accounted for Rs 2.14 crore (28.0%). Administrative approvals were on file for 168 activities (19.7%); a missing approval record does not establish that approval was absent. The cashbook shows Rs 5.28 crore paid out, but only 33.3% of payments were linked to a planned activity. 
>
> For the works review, start with the 55 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 86.0% of their planned cost. Also check the status of the 22 works marked abandoned, 21 of which were planned in 2024-2025.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet, run 3 — kept, 2 tries, 287 words, place facts used: I4, J, A1, A2, A3, A5, A6, B, B, C, F1, G3, E5

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented in the sample by Kalimela Gram Panchayat alone. It has 852 planned activities, of which 392 (46.0%) have no cost attached. Its recorded plan of Rs 7.65 crore is the 2nd highest of the 16 blocks in the sample, but spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest in the sample. Spending was 11.1% of plan in 2023-2024 and 10.5% in 2024-2025.
>
> Drinking water is the first sector to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent on planned activities. The entire tied-grant plan was split between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending breakdown, drinking water was the largest category at Rs 70.85 lakh, followed by sanitation at Rs 41.40 lakh; public works accounted for nearly all of that spending. By contrast, the Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries but 3.1% of planned activities. These are planning estimates, not a count of people reached.
>
> At the next review, reconcile the plan, approvals and cashbook. Only 168 activities (19.7%) have an administrative approval on file; a missing record does not establish that approval was absent. No fund component is recorded for 684 activities, and activities without a recorded scheme account for Rs 5.57 crore of planned cost. Activities with no asset category account for Rs 2.14 crore of planned cost, and only 33.3% of cashbook payments are linked to a planned activity. Also verify the status of the 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost already recorded as spent.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet_choose, run 1 — kept, 1 tries, 270 words, place facts used: I4, A1, A2, A3, A4, A5, A6, B, B, B, C, C, C, F1, G1, G3, E2, E5

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented by one Gram Panchayat in the sample. It had 852 planned activities, the 5th most of 16 blocks, but 392 (46.0%) had no cost attached. Its recorded planned cost of Rs 7.65 crore was the 2nd highest of 16 blocks. Sanctions on file totalled Rs 2.08 crore, and spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost—the 4th lowest of 16 blocks, against a middle value of 36.6%. Spending was 11.1% of plan in 2023-2024, 10.5% in 2024-2025, and 19.1% in 2025-2026.
>
> Drinking water is a priority for review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. The entire tied-grant plan was allocated to sanitation and drinking water. Land improvement had Rs 73.95 lakh planned with no spending recorded, and poverty alleviation had Rs 37.09 lakh planned, also with no spending recorded.
>
> At the next review, reconcile plans, approvals and payments. Activities with no scheme recorded accounted for Rs 5.57 crore (72.7%) of planned cost, and 684 activities (80.3%) had no fund component recorded. Administrative approvals were on file for 168 activities (19.7%); a missing record does not establish that an activity lacked approval. The cashbook shows Rs 5.28 crore paid out, but only 33.3% of payments are linked to a planned activity, against a middle value of 46.5% across the blocks in the sample.
>
> Check work status as well. Kalimela accounted for 13 of the 17 works marked completed in the sample, yet 55 works planned in 2022-2023 or earlier were still marked ongoing, with 86.0% of their planned cost already spent.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet_choose, run 2 — kept, 1 tries, 236 words, place facts used: I4, A1, A2, A3, A5, A6, C, C, C, B, B, F1, G3, E5, E3

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented by 1 Gram Panchayat in the sample. It planned 852 activities, the 5th most of 16 sampled blocks, but 392 of them (46.0%) had no cost recorded. Its recorded plan cost was Rs 7.65 crore, the 2nd highest in the sample. It spent Rs 1.76 crore on planned activities, or 23.0% of the planned cost, the 4th lowest in the sample.
>
> Drinking water is the first sector to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. Land improvement had Rs 73.95 lakh planned and no recorded spending; the poverty alleviation programme likewise had Rs 37.09 lakh planned and no recorded spending. Across all sectors, spending was 11.1% of plan in 2023-2024 and 10.5% in 2024-2025.
>
> At the next review, reconcile the plan, approval and payment records. No scheme is recorded for 684 activities, which account for Rs 5.57 crore (72.7%) of planned cost. Administrative approvals are on file for 168 activities (19.7%); a missing approval record does not establish that the activity was unapproved. Only 33.3% of cashbook payments are linked to a planned activity, compared with a sample middle value of 46.5%.
>
> Also verify the status of older works: 55 planned in 2022-2023 or earlier are still marked ongoing, with Rs 89.63 lakh spent (86.0% of their planned cost). Separately, 21 of the 22 works marked abandoned were planned in 2024-2025.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet_choose, run 3 — kept, 1 tries, 222 words, place facts used: I4, A3, A5, A6, B, B, B, C, C, C, A1, A2, F1, G3, E5, E2

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block is represented by one Gram Panchayat in the sample. Its planned cost of Rs 7.65 crore was the 2nd highest of 16 blocks in the sample. It spent Rs 1.76 crore on planned activities, or 23.0% of planned cost, the 4th lowest in the sample. Spending was 93.6% of plan in 2020-2021, compared with 11.1% in 2023-2024 and 10.5% in 2024-2025.
>
> Drinking water is the first area to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. Land improvement had Rs 73.95 lakh planned but no spending recorded, and poverty alleviation had Rs 37.09 lakh planned but no spending recorded.
>
> At the next review, reconcile plans, approvals and payments. Of 852 planned activities, 392 (46.0%) had no cost attached, and only 168 (19.7%) had an administrative approval on file; a missing record does not establish that approval was absent. No scheme was recorded for activities accounting for Rs 5.57 crore (72.7% of planned cost), and only 33.3% of cashbook payments were linked to a planned activity.
>
> Check whether older works are still active or their status needs updating: 55 works planned in 2022-2023 or earlier are still marked ongoing, with 86.0% of their planned cost spent. Kalimela also accounts for 13 of the 17 works marked completed in the whole sample.
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

#### sheet_midsize, run 1 — LOST, 2 tries, 449 words, place facts used: I4, A1, A3, A4, A5, A6, A7, A2, B, B, B, B, C, C, C, C, H2, D, E1, E2, E5, E3, E4, G1, G3

> This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".
>
> Kalimela block
> - Kalimela block has 1 Gram Panchayat in the data.
> - Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
> - Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.
> - Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 5th highest of 16 blocks. The middle value is Rs 1.51 crore.
> - It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.
> - Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.
> - Spending is Rs 5.90 crore below plan.
> - 392 of them (46.0%) have no cost attached.
> - In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.
> - In 2024-2025: 268 activities (72 with no cost), Rs 3.00 crore planned, Rs 31.60 lakh spent, 10.5% of the plan.
> - In 2025-2026: 169 activities (124 with no cost), Rs 58.60 lakh planned, Rs 11.20 lakh spent, 19.1% of the plan.
> - In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.
> - Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.
> - Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.
> - Maintenance of community system: 100 activities, Rs 62.03 lakh planned, Rs 11.54 lakh spent.
> - Sanitation: 118 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent.
> - 49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.
> - Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).
> - 154 works are marked ongoing, the 5th most of 16 blocks. The middle value is 104.
> - 13 works are marked completed, out of 17 in the whole sample.
> - 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).
> - 22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.
> - 129 activities have photo evidence (553 uploads), the 5th most of 16 blocks. The middle value is 83.
> - Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.
> - 33.3% of the payments are linked to a planned activity, the 6th lowest of 16 blocks. The middle value is 46.5%.
>
> - Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 34.3% (Rs 70.85 lakh), then Sanitation at 20.0% (Rs 41.40 lakh). The remaining 22 together account for Rs 94.29 lakh. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 34.3% of spending, general component -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, activities planned totals 852 activities across 6 fund component values. It is concentrated: (not recorded) accounts for 80.3% of it (684 activities). The remaining 5 together account for 168 activities. 684 rows carry no fund component on file; they are counted here as (not recorded) and account for 684 activities.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 4 scheme values. It is concentrated: (not recorded) accounts for 72.7% of it (Rs 5.57 crore). The remaining 3 together account for Rs 2.09 crore. 684 rows carry no scheme on file; they are counted here as (not recorded) and account for Rs 5.57 crore.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 48.8% (Rs 3.74 crore), then Land improvement at 9.7% (Rs 73.95 lakh). The remaining 22 together account for Rs 3.18 crore. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 48.8% of planned cost -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, expected beneficiaries totals 8,820 people across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 1 - Poverty Free and Enhanced Livelihoods Village at 45.1% (3,978 people), then Theme 6 - Self-sufficient Infrastructure in Village at 15.5% (1,367 people). The remaining 5 together account for 3,475 people. For size: Theme 1 - Poverty Free and Enhanced Livelihoods Village holds 3.1% of the 852 activities behind these totals, against 45.1% of expected beneficiaries -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 2 activity type values. It is concentrated: Public Works accounts for 100.0% of it (Rs 2.06 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs 5,000. For size: Public Works holds 82.3% of the 852 activities behind these totals, against 100.0% of spending, general component -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 22 asset category values. It is spread across them without one standing out: the largest is Uncategorised at 28.0% (Rs 2.14 crore), then Water Sources & Structures at 23.9% (Rs 1.83 crore). The remaining 20 together account for Rs 3.68 crore. For size: Uncategorised holds 57.5% of the 852 activities behind these totals, against 28.0% of planned cost -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Kalimela, tied grant planned totals Rs 92.28 lakh across 24 focus area values. It is spread across them without one standing out: the largest is Sanitation at 50.5% (Rs 46.59 lakh), then Drinking water at 49.5% (Rs 45.69 lakh). The remaining 22 together account for Rs 0. For size: Sanitation holds 13.8% of the 852 activities behind these totals, against 50.5% of tied grant planned -- a group's total grows with how much of the work it holds.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.
>
> (as of 2026-09-11)

---

## §5 The gate and the suite, baseline against final

| | Baseline (T0) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 41/43 green; red: `judge-model-evidenced`, `classifier-model-evidenced` (D69) | **46/48 green**; red: the same two |
| `python -m pytest DiscoverChat/tests -q` | 247 passed, 114 subtests | **285 passed, 147 subtests, 0 failed** |
| `python Insights/src/phase5g_profile_sheets.py --check` | 9 of 9 | not re-run (store untouched) |

The five new gate lines, as printed:

```
PASS  place-resolution           13 rows of the T1 table reproduced; every note's quoted words resolve to its alternative; Kalimela block hands 61 lines
PASS  place-facts-optional       16 Kalimela block lines handed: an answer citing none passes; citing one passes; a dropped insight still fails step 4; an id not handed fails step 1
PASS  place-standing-check       7 sentences: the line's own rank passes; the other end word, a first place it does not hold and a quarter it does not state are caught; a sentence citing no place fact is not checked (mode log)
PASS  place-prompt-ratified      R18 identical to the D78 text; directly before "Return only the finished prose." on a place turn; absent on any other
PASS  place-switch-off-identical switch off: 76 of 76 answers byte-identical to the pre-WP-D15 service; switch on: 27 answers carry place facts, the other 49 unchanged
```

Changed existing lines: `consolidation-prompt-is-the-operators` now also pins the R18 paragraph to the gate's own copy of the D78 text and checks it is not in the standing prompt. `numerals-traceable` also accepts the numerals of the sheet lines an answer shows (§8 item 2). Neither changed any other check's result.

The 38 new tests (`test_place_answers.py`):
- T1: the table; the notes' words; quoted words resolve to the alternative; one mention decided by position; "G.P.", "GP Kalimela", "Gram Panchayat of"; `find` given the slot reader's spelling; `geography`'s old fields unchanged; a name with several codes dropped; more places than the setting.
- T2: a `full` and a `main` payload; R18 only with place facts; a no-place prompt byte-identical to a copy of the old function (with and without a retry reason); no FINDINGS block on a sheet-only request.
- T3: each row with a passing and a failing sentence; the short fiscal year and the dashes; steps 6 (block, log, off, not checked without a place fact) and 7 (logged, never counted, written to the log).
- T4/T5: a kept narrative (note first, `lines_used` in order, citations shape, reference render); a sheet-only answer when the judge kept nothing; the insight cap; the four T4 cases plus two places; a no-place turn untouched; lookup and why get no sheet; switch off; `/record` JSON, list line, HTML and 404; the service starting with no store; `open_store` never raising; the five knobs.

**How to replay (PM):** a fresh mirror of `Ask/ DiscoverChat/ eval/ handoffs/ Insights/` plus the view parquets from `C:\dev\odisha-d11b\Insights\views_prdw\`, then `python -m DiscoverChat.gates` (46/48) and `python -m pytest DiscoverChat/tests -q` (285). `place-switch-off-identical` replays the baseline's own query vectors, so it needs no embedding call and is not moved by the endpoint's drift. The trial tables come from `python handoffs/WPD15_trial/analyse.py` (no model call).

Files beside the mirror: `C:\dev\odisha-d15-baseline-{gates,pytest,check}.txt`, `-final-{gates,pytest}.txt`, `-offline-baseline.json`, `-offline-switch-{off,on}.json`, `-prompts-{baseline,final}.json`, `-query-vectors.pkl`, `-judge_picks-before.json`, `-trial-logs\`.

---

## §6 Every model call and its cost

| What | Model | Calls | Tokens in | Tokens out | Cost |
|---|---|---|---|---|---|
| Hold the 3 two-place judge picks (the only judge calls) | gpt-6.2-sol | 3 | 39,584 | 1,456 | price not set |
| Trial `current` | gpt-6.2-sol | 40 | 98,509 | 23,333 | price not set |
| Trial `sheet` | gpt-6.2-sol | 123 | 447,100 | 70,187 | price not set |
| Trial `sheet_choose` | gpt-6.2-sol | 66 | 237,905 | 34,236 | price not set |
| Trial `sheet_midsize` | gpt-6-luna | 41 | 150,460 | 91,279 | price not set |
| Trial `sheet_no_insight` | gpt-6.2-sol | 2 | 5,430 | 70 | price not set |
| **Chat models, total** | | **275** | **978,988** | **220,561** | |
| Query embeddings (offline baselines, gate runs) | qwen3-embedding-8b (OpenRouter) | 67 strings, memoised per process; the baseline vectors kept on file | – | – | about $0.01 per 1M tokens; negligible |

No price is on file for `gpt-6.2-sol` or `gpt-6-luna` (`held_picks.PRICES` has only `gpt-5.6-sol`), so the cost reads "price not set", by the WP-D13 Fix 9 rule; none was guessed. Every call is also in the mirror's `DiscoverChat/logs/calls.jsonl`. No call errored.

---

## §7 Decision journal

1. **How the place facts travel.** As `place.PlaceFact` objects in their own list, beside the findings and never mixed in. A `PlaceFact` answers the few attributes the check and the renderer read from a finding (`id`, `sentence`, `display_sentence()`, `is_decomposition=False`, `data={}`), so step 2 binds its numerals by the same rule and the same code. `check_citations(..., place_facts=)`, `bind_numerals(..., place_facts=)`, `to_html(..., place_facts=)` take them explicitly; step 4 never sees them; `layout.build` and the session's anchors get the findings only.
2. **Where the positions come from.** A new `mentions` field in `geography()`: for every name the existing logic accepts, every occurrence in the text and its position (longer names first, as the existing tier rule does). The existing fields are computed exactly as before; `mentions` is never read by them, and it is not in `Slots.as_dict()`.
3. **The `/record` payload for a place fact.** `record_type: "place_fact"`, `sentence`, `label`, `place` (level, code, name, parents), `row`, `key`, `figures` = the sheet's own entry, copied (`rows[row]` for a main line, plus `G2` for the G1 line that states both; `lists[row][key]` for a list line), `note`, `view: "Place profile"`, `run_stamp`, `candidate_set_id`, `url`. The HTML view is in the style of the finding view.
4. **The step 7 word list** (`number_words.json`): second … twentieth; half, halves, thirds, quarter, quarters, two-thirds, three-quarters; double, doubled, twice, triple, tripled, tenfold; majority. A hyphen also matches a space. I read the brief's "(but not the stored phrase '… quarter of the')" as **"quarter" right after a standing word** (lowest, lower-middle, upper-middle, highest). Excluding every "quarter of the" would also have hidden "a quarter of the activities", which is a number in words.
5. **A name that is also a district** (not in the sample; possible statewide, e.g. Koraput): the larger level is answered unless the words next to it say otherwise ("block", "GP", "district"). This is R4's reading carried one level up.
6. **The note when two places were both chosen between levels:** one sentence pair when every alternative is of one level (the TWO-01 wording in §2), otherwise the brief's sentence once per place.
7. **A sheet-only request has no FINDINGS block** (not an empty one).
8. **No writer (model off, or consolidation off):** A1–A7 under each label, then today's text for the turn, read literally. With no insight, that is today's honest-miss text. This keeps `no-match-honest` green for the two gate questions that name a district.
9. **The insight cap applies on every sheet turn**, including the no-writer path. When insights are held back, the existing "More than N findings clear the relevance bar …" line is printed with N = the number shown (8), so it stays true. In the trial it appeared on most place answers (held picks: middle 15).
10. **The note in `answer_html`** goes at the start of the one narrative `<p>`, not in a paragraph of its own. The present page (`discover-answer.ts`) reads only the first bare `<p>` and walks it against `answer` from the first character. A separate paragraph would have quietly switched off every hover on place answers. A new `Answer.lead` carries the note (and the decompose scope note, when present) for this.
11. **Every read of the sheet store goes through `place.py`**, including `/record`. That kept the WP-D14 test `test_the_service_does_not_import_the_reader` passing unchanged (§8 item 1).
12. **The two hyphen look-alikes** (U+2010, U+2011) are read as hyphens with the en and em dashes. GPT models do write U+2011 in years. Nothing else about matching loosened: `Rs 7.65 crore` still cannot become `Rs 7.7 crore` (tested).
13. **The switch-off gate line** compares against a baseline made on the pre-WP code and **replays that baseline's query vectors**, so it sees code changes only. The endpoint drifts between calls and would otherwise make a byte comparison flaky. The baseline lives in `handoffs/WPD15_trial/` (the only writable place for it). It fails, with instructions, if the corpus's candidate set changes.
14. **`retrieval["place"]`** is also written when names were found but no sheet was used (more than three places, or names dropped), so the call log says why.
15. **`place` in `Answer.as_dict()` only when not empty**, so the switch-off answer dict is byte-identical. The `/chat` response always has the field (`{}` when no sheet was used), as the brief says.
16. **Step 6 default `log`**, by the brief's rule after the trial (§4.5).
17. **`DISCOVERCHAT_PROFILE_SHEETS` default on**, because marks 1–3 hold.

---

## §8 What in the spec or the brief was wrong or silent

1. **A WP-D14 test pins "the service does not import the reader".** "Every existing test passes unchanged" and "wire the reader into /chat" could not both hold by the test's intent. It passes because the service reaches the store only through the new `place.py`, which is not on the test's file list. Its name is now stale; the PM may want it renamed to "only place.py opens the store".
2. **`numerals-traceable` had to learn about sheet lines.** With the switch on, the offline "How is Chikilli doing?" answer shows A1–A7, whose figures are in no finding, so the check went red. It now also accepts the numerals of the sheet lines an answer actually shows (`place.lines_used`), the way it accepts a finding's. The brief's gate ("nothing green turned red") did not foresee this.
3. **The offline gate's "no match" questions name places** ("onions in Cuttack market", "rainfall … Koraput"). With the sheets on, they are now place questions with no insight, so by T2.4 they go to the writer with the district's sheet. Live, the writer declined both, correctly (§4.8b). Offline, T4 read literally shows A1–A7 and then the honest-miss text. `no-match-honest` stays green because it checks findings and the miss line. But the officer sees a block of Cuttack figures above "The current analysis has nothing on this." **This needs a PM ruling:** should a place question with no insight and no writer show the sheet lines at all? `live:out-of-scope-silent` also counts only findings, so it cannot see sheet lines.
4. **Step 6's definition** ("the same rank with the same end word") produces false alarms on correct sentences: highest/most, lowest/fewest, "among the highest". §4.5 has the five, and a proposed fix.
5. **Found, not fixed (`Insights/` is out of scope):** every by-year linked-spending breakdown (view2, e.g. d2-00817 Kandhamal, d2-01882 Sharagada) ends with the same builder sentence, "the linked share went from 2.7% to 53.2% across these six years". That is a sample-wide figure, but the writer presents it as the place's own ("Kandhamal's linked share rose from 2.7% to 53.2%"), in 20 sheet answers and equally often in `current`. It passes every check, because the digits are in the cited record.
6. **Two year bases in one answer** happened once (§4.8, the mid-size writer). Nothing in the request tells the writer that the sheet's years are plan years and the month cube's are payment years.
7. **The T1 table lists no note or alternative for "How is Kalimela Gram Panchayat doing", "the panchayat of Kalimela" and "How is Kalimela block doing"**, while rule 5 ("only when rule 2 chose between two levels") gives them one. I followed the rule (§2). If the officer's own explicit word should suppress the note, it is a one-line change in `place.resolve`.
8. **The every-insight rule is the main cost of the first draft:** 60 of 63 first drafts in `sheet` were refused on step 4. `sheet_choose` is the evidence for the PM's separate ruling (§4.10).
9. **R17's fallback plan:** the mid-size arm's losses come from luna's tagging (whole paragraphs tagged at their end), not from the sheet's size (§4.10). A 25-line core would not obviously help.
10. **Prices** for `gpt-6.2-sol` and `gpt-6-luna` are not on file, so §6 gives tokens only.
11. **Pre-existing, noticed:** on a causally-worded decompose turn without a sheet, `answer` starts with the scope note but `answer_html` does not, so the page's hover alignment already fails there. Fixed for place turns (decision 10); not touched elsewhere.

**Not this package, for WP-D16:** highlight `place.lines_used` in order; a switch from `place.alternatives`; asking "which one?" for repeated names; sheets for no place or more than three; the every-insight ruling; the step 6 end-word ruling; the ruling in item 3.

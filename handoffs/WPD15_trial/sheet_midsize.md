# Writer test: sheet_midsize

Run 2026-11-24T19:49:35 on the held judge picks (held 2026-11-24T19:43:47).

| | |
|---|---|
| Writer model | gpt-6-luna |
| Prompt | the live prompt (context_brief.py) |
| Every finding must be mentioned | on |
| Questions | 21 |
| Answers kept | 13 |
| Answers lost (plain sentences shown instead) | 8 (1 on 4_all_findings_cited, 7 on 2_numerals_cited, 1 on 6_standing) |
| Passed on the first try | 1 |
| Writer calls | 41 |
| Seconds per answer, middle | 43.1 |
| Findings used, of those handed (middle) | 8 of 8 |
| Words per answer, middle | 405 |
| Words per answer, most | 515 |
| Sentences per answer, middle | 17 |
| Words per sentence, middle | 23.8 |
| Sentences over 25 words | 44% |
| Figures per answer, middle | 63 |
| Figures per sentence, middle | 3.6 |
| Sentences with more than 2 figures | 70% |
| Share of the handed figures that appear, middle | 80% |

## The instructions the writer was given

```
Turn the analytical findings below into clear, concise prose for a senior government official.

Do not rewrite each finding separately. Identify overlapping or repeated findings, consolidate them into a small number of underlying patterns, and explain those patterns as a coherent narrative. It is very important that you do not make causal claims - none of our data can be used to determine causality. Do not fabricate or overstate data.

Preserve important numbers and exceptions where useful. Ignore ranking metadata such as "not in the ranked shortlist." Avoid database-style language and do not infer causes that are not supported by the findings.

After every figure and every claim, tag the finding it comes from with its id in square brackets, exactly as given, e.g. [1-00235]. A sentence drawing on two findings carries both tags.

Use figures exactly as they appear in the findings. Do not compute new numbers — no percentages, sums, or differences that are not stated in a finding.

Return only the finished prose.
```

## The answers

### GEO-06 - How is Biswamathpur performing on spending?

- used 8 of 8 findings, 313 words, 11 sentences, 28.5 words per sentence, 41 figures, 61% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (3 of 61): A3, A5, A6

Biswamathpur spent Rs 1.42 crore on planned activities, equal to 16.4% of its Rs 8.65 crore planned cost—the lowest share among the 20 Gram Panchayats, compared with a middle value of 42.0%. Recorded spending was spread across the six fiscal years: the largest shares were in 2020-2021 at 19.8% (Rs 28.07 lakh) and 2022-2023 at 18.8% (Rs 26.60 lakh). The plan shortfall, however, is concentrated in 2023-2024, which accounts for 68.6% (Rs 4.96 crore) of the Rs 7.23 crore total gap, while holding 39.6% of the activities.

The gap is concentrated in Public Works: it accounts for 99.9% (Rs 7.22 crore) of the shortfall, against 77.6% of activities; spending against plan in this category is 16.4%. By focus area, Sanitation accounts for the largest share of the gap at 29.1% (Rs 2.10 crore), followed by Women and child development at 14.3% (Rs 1.04 crore); Sanitation’s spending against plan is 11.3%. Scheme records also warrant reconciliation: 414 rows have no scheme on file, and this “not recorded” group accounts for 94.2% (Rs 6.81 crore) of the plan gap.

Spending is Rs 42.13 lakh below the sanctioned amount across the six fiscal years, with no one year standing out; the sanctioned basis covers only activities with a sanction record on file, about one in six. Separately, spending linked to planned activities totals Rs 1.35 crore: the largest shares are in 2025-2026 at 33.6% (Rs 45.20 lakh) and 2022-2023 at 25.4% (Rs 34.17 lakh). The linked share went from 2.7% to 53.2% across the six years; the finding cautions that a rise in this measure indicates greater recording completeness unless the cashbook total also rises. Voucher-linked spending totals Rs 1.42 crore, all recorded under Public Works, although that category holds 77.6% of activities. These records point to a review of the 2023-2024 plan gap, missing scheme details and the links between payments, planned activities and sanctions.

What the officer sees instead:

```
Biswamathpur Gram Panchayat
- Its planned cost is Rs 8.65 crore, the highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
- It spent Rs 1.42 crore on planned activities, the 6th highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
- Spending is 16.4% of the planned cost, the lowest of 20 Gram Panchayats. The middle value is 42.0%.

- Within Gram Panchayat Biswamathpur, spending totals Rs 1.42 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2020-2021 at 19.8% (Rs 28.07 lakh), then 2022-2023 at 18.8% (Rs 26.60 lakh). The remaining 4 together account for Rs 87.12 lakh.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending measured against plan totals Rs 7.23 crore below plan across 6 fiscal years. It is concentrated: 2023-2024 accounts for 68.6% of it (Rs 4.96 crore below plan). The remaining 5 together account for Rs 2.27 crore below plan. For size: 2023-2024 holds 39.6% of the 540 activities behind these totals, against 68.6% of spending measured against plan -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending linked to a planned activity totals Rs 1.35 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2025-2026 at 33.6% (Rs 45.20 lakh), then 2022-2023 at 25.4% (Rs 34.17 lakh). The remaining 4 together account for Rs 55.25 lakh. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending measured against plan totals Rs 7.23 crore below plan across 2 activity type values. It is concentrated: Public Works accounts for 99.9% of it (Rs 7.22 crore below plan). The one remaining, Beneficiary Oriented Programmes, accounts for Rs 93,200 below plan. For size: Public Works holds 77.6% of the 540 activities behind these totals, against 99.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Public Works is 16.4%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending measured against plan totals Rs 7.23 crore below plan across 3 scheme values. It is concentrated: (not recorded) accounts for 94.2% of it (Rs 6.81 crore below plan). The remaining 2 together account for Rs 42.13 lakh below plan. 414 rows carry no scheme on file; they are counted here as (not recorded) and account for Rs 6.81 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending measured against sanction totals Rs 42.13 lakh below sanction across 6 fiscal years. It is spread across them without one standing out: the largest is 2020-2021 at 26.5% (Rs 11.14 lakh below sanction), then 2025-2026 at 24.5% (Rs 10.32 lakh below sanction). The remaining 4 together account for Rs 20.66 lakh below sanction. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, spending measured against plan totals Rs 7.23 crore below plan across 24 focus area values. It is spread across them without one standing out: the largest is Sanitation at 29.1% (Rs 2.10 crore below plan), then Women and child development at 14.3% (Rs 1.04 crore below plan). The remaining 22 together account for Rs 4.09 crore below plan. For size: Sanitation holds 11.7% of the 540 activities behind these totals, against 29.1% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 11.3%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Biswamathpur, voucher-linked spending totals Rs 1.42 crore across 2 activity type values. It is concentrated: Public Works accounts for 100.0% of it (Rs 1.42 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs 0. For size: Public Works holds 77.6% of the 540 activities behind these totals, against 100.0% of voucher-linked spending -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-07 - What stands out in Boipariguda?

- used 8 of 8 findings, 423 words, 20 sentences, 21.1 words per sentence, 68 figures, 70% of the handed figures, 2 tries
- place facts used (20 of 58): I4, A1, A2, A3, A5, A6, A7, C, B, B, B, E5, E2, H2, CT, CT, CT, CT, G3, G1

Boipariguda’s record covers one Gram Panchayat and 647 planned activities; 248 activities (38.3%) have no cost attached. Planned cost is Rs 6.15 crore, while spending is Rs 1.41 crore (22.8% of plan), the 3rd-lowest share among 16 blocks. The recorded gap is Rs 4.75 crore. The largest single focus-area share of that gap is Rural housing—Rs 2.13 crore, or 44.9%—followed by Drinking water at Rs 1.26 crore, or 26.5%; the remaining 20 focus areas account for Rs 1.35 crore together. Rural housing has six activities planned and no spending recorded. 

The gap is particularly concentrated in 2023-2024: that year accounts for 64.7% of planned cost and 79.7% of the recorded shortfall. It had 259 activities, including 69 with no cost, Rs 3.98 crore planned and Rs 19.75 lakh spent—5.0% of plan. By comparison, 2024-2025 spending was 67.9% of plan, while 2025-2026 was 19.6%. Separately, 64 works planned in 2022-2023 or earlier are still marked ongoing, although Rs 84.10 lakh of their Rs 94.38 lakh planned cost has been spent. No works are marked completed. 

Theme records also warrant review: 76 activities have no LSDG theme mapped, with Rs 2.43 crore planned; this is 39.5% of planned cost across the seven theme values. Theme 4 - Water Sufficient Village has Rs 1.81 crore planned, while the unmapped activities have Rs 9.29 lakh spent. Expected beneficiaries total 3,866 across the theme values; the largest recorded totals are 1,260 under Unmapped LSDG theme and 1,230 under Theme 6 - Self-sufficient Infrastructure in Village. Theme 3 - Child Friendly Village has 97 activities, Rs 9.47 lakh planned and Rs 1.00 lakh spent, while Theme 1 - Poverty Free and Enhanced Livelihoods Village has Rs 4.17 lakh planned and no spending recorded. 

A separate breakdown of spending, general component records Rs 1.62 crore across work types: Maintenance accounts for 46.6% (Rs 75.45 lakh) and New/Fresh for 35.1% (Rs 56.90 lakh). In the activity-type breakdown of that component, all recorded spending is under Public Works (Rs 1.62 crore); Beneficiary Oriented Programmes records Rs 0. Payment linkage is comparatively strong in the block: 75.8% of payments are linked to a planned activity, the 2nd-highest share among 16 blocks. Linked spending totals Rs 1.18 crore across six years; the largest year share is 2022-2023 at 32.6% (Rs 38.62 lakh), followed by 2021-2022 at 20.0% (Rs 23.70 lakh). The linked share went from 2.7% to 53.2% across those years; this reflects recording completeness unless the cashbook total also rises. The cashbook shows Rs 2.41 crore received and Rs 1.85 crore paid out.

### GEO-12 - What does the analysis say about Haldikudar?

- used 8 of 8 findings, 430 words, 18 sentences, 23.9 words per sentence, 68 figures, 91% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (11 of 62): A1, A2, A3, A5, A6, A7, H2, E1, E2, E3, E4

Haldikudar has 582 planned activities, of which 356 (61.2%) have no cost attached. Its planned cost is Rs 1.66 crore, the lowest among the 20 Gram Panchayats; spending is Rs 75.12 lakh, or 45.3% of plan, against a sample middle value of 42.0%, and is Rs 90.62 lakh below plan. 

A key record-completeness issue is that 488 activities have no fund component recorded: these are 83.8% of activities, and account for 72.6% (Rs 65.78 lakh) of the recorded shortfall between spending and plan. Separately, 488 rows have no scheme recorded; they account for all 10,455 expected beneficiaries recorded, while the other 2 scheme values together account for 0 people. Fifty-three activities have no LSDG theme mapped, with Rs 14.68 lakh planned. 

The planned untied grant totals Rs 1.04 crore across 23 focus areas, with Roads the largest share at 23.4% (Rs 24.42 lakh), followed by Sanitation at 17.4% (Rs 18.17 lakh); the remaining 21 areas together account for Rs 61.63 lakh. Roads represents 1.9% of the activities behind these totals. Across focus areas, spending is Rs 90.62 lakh below plan: Sanitation accounts for the largest share of that gap at 31.2% (Rs 28.32 lakh), followed by Drinking water at 27.7% (Rs 25.12 lakh); the remaining 21 areas account for Rs 37.18 lakh. Sanitation’s spending-to-plan ratio is 35.3%. By asset category, Water Sources & Structures accounts for 24.1% (Rs 21.81 lakh) of the plan shortfall, followed by Uncategorised at 12.4% (Rs 11.23 lakh); the remaining 19 categories account for Rs 57.58 lakh. Water Sources & Structures represents 3.1% of the activities behind these totals, and its spending-to-plan ratio is 23.9%. 

The sanction record covers only activities with a sanction on file—about one in six. Of the Rs 99.95 lakh sanctioned across 7 LSDG themes, Theme 6 - Self-sufficient Infrastructure in Village has the largest share at 38.9% (Rs 38.88 lakh), followed by Theme 5 - Clean and Green Village at 24.7% (Rs 24.64 lakh); the other 5 themes together account for Rs 36.42 lakh. Theme 6 represents 18.6% of the activities behind these totals. Against sanction, spending is Rs 24.83 lakh below the sanctioned amount: Sanitation accounts for 37.0% (Rs 9.19 lakh) of this gap, followed by Drinking water at 30.1% (Rs 7.47 lakh); the remaining 21 focus areas account for Rs 8.17 lakh. Sanitation’s spending-to-sanction ratio is 62.7%. 

For context on delivery records, 92 works are marked ongoing and none are marked completed; 9 are marked abandoned, with Rs 9.50 lakh planned on them, and 5 were planned in 2020-2021. Fifty-three activities have photo evidence, the third-fewest in the sample.

What the officer sees instead:

```
Haldikudar Gram Panchayat
- Haldikudar Gram Panchayat has 582 planned activities, the 10th fewest of 20 Gram Panchayats. The middle value for these 20 is 602.5.
- 356 of them (61.2%) have no cost attached.
- Its planned cost is Rs 1.66 crore, the lowest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
- It spent Rs 75.12 lakh on planned activities, the 2nd lowest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
- Spending is 45.3% of the planned cost, the 9th highest of 20 Gram Panchayats. The middle value is 42.0%.
- Spending is Rs 90.62 lakh below plan.
- 53 activities have no LSDG theme mapped; their planned cost is Rs 14.68 lakh.
- 92 works are marked ongoing, the 8th fewest of 20 Gram Panchayats. The middle value is 95.5.
- No works are marked completed.
- 9 works are marked abandoned, with Rs 9.50 lakh planned on them. 5 of them were planned in 2020-2021.
- 53 activities have photo evidence (424 uploads), the 3rd fewest of 20 Gram Panchayats. The middle value is 79.

- Within Gram Panchayat Haldikudar, untied grant planned totals Rs 1.04 crore across 23 focus area values. It is spread across them without one standing out: the largest is Roads at 23.4% (Rs 24.42 lakh), then Sanitation at 17.4% (Rs 18.17 lakh). The remaining 21 together account for Rs 61.63 lakh. For size: Roads holds 1.9% of the 582 activities behind these totals, against 23.4% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, expected beneficiaries totals 10,455 people across 3 scheme values. It is concentrated: (not recorded) accounts for 100.0% of it (10,455 people). The remaining 2 together account for 0 people. 488 rows carry no scheme on file; they are counted here as (not recorded) and account for 10,455 people.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, spending measured against plan totals Rs 90.62 lakh below plan across 23 focus area values. It is spread across them without one standing out: the largest is Sanitation at 31.2% (Rs 28.32 lakh below plan), then Drinking water at 27.7% (Rs 25.12 lakh below plan). The remaining 21 together account for Rs 37.18 lakh below plan. For size: Sanitation holds 13.1% of the 582 activities behind these totals, against 31.2% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 35.3%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, sanctioned amount totals Rs 99.95 lakh across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 6 - Self-sufficient Infrastructure in Village at 38.9% (Rs 38.88 lakh), then Theme 5 - Clean and Green Village  at 24.7% (Rs 24.64 lakh). The remaining 5 together account for Rs 36.42 lakh. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 18.6% of the 582 activities behind these totals, against 38.9% of sanctioned amount -- a group's total grows with how much of the work it holds. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, spending measured against plan totals Rs 90.62 lakh below plan across 4 fund component values. It is concentrated: (not recorded) accounts for 72.6% of it (Rs 65.78 lakh below plan). The remaining 3 together account for Rs 24.83 lakh below plan. 488 rows carry no fund component on file; they are counted here as (not recorded) and account for Rs 65.78 lakh below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, activities planned totals 582 activities across 4 fund component values. It is concentrated: (not recorded) accounts for 83.8% of it (488 activities). The remaining 3 together account for 94 activities. 488 rows carry no fund component on file; they are counted here as (not recorded) and account for 488 activities.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, spending measured against plan totals Rs 90.62 lakh below plan across 21 asset category values. It is spread across them without one standing out: the largest is Water Sources & Structures at 24.1% (Rs 21.81 lakh below plan), then Uncategorised at 12.4% (Rs 11.23 lakh below plan). The remaining 19 together account for Rs 57.58 lakh below plan. For size: Water Sources & Structures holds 3.1% of the 582 activities behind these totals, against 24.1% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Water Sources & Structures is 23.9%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Haldikudar, spending measured against sanction totals Rs 24.83 lakh below sanction across 23 focus area values. It is spread across them without one standing out: the largest is Sanitation at 37.0% (Rs 9.19 lakh below sanction), then Drinking water at 30.1% (Rs 7.47 lakh below sanction). The remaining 21 together account for Rs 8.17 lakh below sanction. For size: Sanitation holds 13.1% of the 582 activities behind these totals, against 37.0% of spending measured against sanction -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 62.7%. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-18 - Is Laxmipur behind on anything?

- used 6 of 6 findings, 427 words, 17 sentences, 25.1 words per sentence, 56 figures, 75% of the handed figures, 2 tries
- place facts used (11 of 62): A1, A3, A2, A6, A7, I4, F1, G3, E1, E2, E5

Laxmipur does not appear behind on recorded spending relative to other blocks in this data: its 808 planned activities are the 7th most among 16 blocks, while planned cost is the 7th lowest; 55.3% of activities have no cost attached. Spending is 52.1% of planned cost, the 3rd highest among the 16 blocks, compared with a middle value of 36.6%. Even so, spending is Rs 1.61 crore below plan. The block data cover one Gram Panchayat, Laxmipur. 

The recorded plan-to-spend gap is spread across years, themes and activity types rather than concentrated in one area. By year, the largest shares of the gap are in 2025-2026 (40.9%, Rs 65.79 lakh) and 2023-2024 (38.2%, Rs 61.40 lakh); the remaining four years account for Rs 33.74 lakh. By LSDG theme, Theme 4 - Water Sufficient Village accounts for 32.0% of the gap (Rs 51.55 lakh) and Theme 6 - Self-sufficient Infrastructure in Village for 28.7% (Rs 46.21 lakh); the remaining five themes account for Rs 63.17 lakh. By focus area, Drinking water accounts for 29.9% (Rs 48.04 lakh) and Sanitation for 27.5% (Rs 44.29 lakh), with the remaining 23 focus areas accounting for Rs 68.60 lakh. At the asset-category level, Drinking water supply structure accounts for 21.7% of the gap (Rs 34.96 lakh) and Liquid Waste Management for 14.4% (Rs 23.14 lakh); the remaining 21 categories account for Rs 1.03 crore. 

Some records may merit reconciliation. Of the Rs 1.61 crore gap against plan, 90.1% (Rs 1.45 crore) is in rows with no sanctioning authority recorded; 642 rows have no authority on file. Separately, 166 of 808 activities (20.5%) have an administrative approval on file; a missing approval record does not establish that an activity was unapproved. Spending is Rs 15.98 lakh below the recorded sanction total, with Drinking water accounting for 62.1% (Rs 9.93 lakh) of that gap; the sanctioned comparison covers only activities with a sanction record on file, about one in six. Also, 46.1% of payments are linked to a planned activity, the 8th lowest share among the 16 blocks, against a middle value of 46.5%. 

Work-status records may also be worth checking: 167 works are marked ongoing, the 4th most among 16 blocks, and none are marked completed. Of these, 90 works planned in 2022-2023 or earlier remain marked ongoing, although 91.0% of their planned cost has been spent. The next review could therefore focus on reconciling missing cost and approval details, payment links, and the status of older ongoing works, rather than treating the recorded plan-to-spend gap alone as evidence of a specific cause.

### GEO-19 - Mendarajpur - show me what the analysis found.

- used 8 of 8 findings, 515 words, 21 sentences, 24.5 words per sentence, 81 figures, 81% of the handed figures, 2 tries
- place facts used (18 of 61): A1, A3, A5, A6, A7, A2, C, F1, F2, G1, G3, D, E1, E2, E3, E5, E4, H2

Mendarajpur has 623 planned activities, with a planned cost of Rs 3.19 crore and Rs 1.32 crore spent; spending is 41.2% of plan, leaving a recorded gap of Rs 1.88 crore. A key planning-record issue is that 421 activities (67.6%) have no cost attached. 

The gap is spread across fiscal years, with the largest shares in 2025-2026 (39.7%, Rs 74.56 lakh) and 2023-2024 (33.1%, Rs 62.24 lakh); the other four years together account for Rs 51.09 lakh. By focus area, Water Conservation is the largest gap (21.7%, Rs 40.75 lakh), followed by Women and child development (16.4%, Rs 30.86 lakh); Water Conservation’s spending-to-plan ratio is 0.0%. The GP’s records show eight Water Conservation activities with Rs 40.75 lakh planned and nothing spent. By output type, Code 101 accounts for 84.0% of the gap (Rs 1.58 crore), while holding 23.9% of the activities; its spending-to-plan ratio is 40.0%. 

The recorded gap is also concentrated in activities without a sanctioning authority on file: these account for Rs 1.47 crore, or 78.5% of the gap, across 484 rows. This describes the records and does not establish that the activities were unapproved. Separately, 139 activities have administrative approval on file and 139 have technical approval on file; the GP records 139 of 623 activities (22.3%) with administrative approval. For activities with a sanction record, spending is Rs 40.44 lakh below sanction; Sanitation and Drinking water account for the largest shares of that gap, at 22.4% (Rs 9.04 lakh) and 21.9% (Rs 8.88 lakh), respectively. The sanctioned comparison covers only activities with a sanction record on file, described in the finding as about one in six. 

The cashbook records Rs 3.06 crore received and Rs 3.44 crore paid out, while 38.3% of payments are linked to a planned activity. Linked spending totals Rs 1.23 crore across six fiscal years; its largest yearly shares are 28.0% (Rs 34.33 lakh) in 2025-2026 and 25.2% (Rs 31.00 lakh) in 2021-2022. The linked share rose from 2.7% to 53.2% across those years; this can reflect improved recording linkage unless the cashbook total also rises. 

Grant planning is predominantly untied: Rs 2.60 crore (81.2%) is untied and Rs 59.89 lakh (18.8%) is tied. Of the tied grant, Drinking water accounts for 50.5% (Rs 30.27 lakh) and Sanitation 48.2% (Rs 28.87 lakh), with the remaining 20 focus areas together accounting for Rs 75,000. Within untied grant planning, Theme 6 - Self-sufficient Infrastructure in Village is the largest allocation at 39.9% (Rs 1.04 crore), followed by Theme 4 - Water Sufficient Village at 22.5% (Rs 58.37 lakh); the other five themes together account for Rs 97.56 lakh. 

For work-status review, 131 works are marked ongoing and none completed; 8 are marked abandoned, with Rs 5.34 lakh planned, and 7 of those were planned in 2020-2021. Of 66 works planned in 2022-2023 or earlier that remain marked ongoing, Rs 88.40 lakh of their Rs 1.07 crore planned cost has been spent (83.0%). There is photo evidence for 107 activities, across 248 uploads. The plan also has 37 activities without an LSDG theme mapped, with Rs 11.11 lakh planned.

### GEO-20 - Anything notable about Sharagada?

- used 8 of 8 findings, 420 words, 18 sentences, 23.3 words per sentence, 58 figures, 72% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (17 of 61): A1, A2, A3, A4, A5, A6, A7, B, F1, F2, G1, G3, E1, E2, E3, E5, E4

Sharagada has the most planned activities in the 20-GP sample: 920, compared with a middle value of 602.5. Of these, 722 (78.5%) have no cost attached; 198 are costed. Planned cost is Rs 6.51 crore, the fourth highest in the sample, while Rs 2.74 crore has been sanctioned for activities with an approval on file, the highest amount. Spending is also the highest, at Rs 1.88 crore, but equals 28.9% of planned cost and is Rs 4.63 crore below plan. 

The shortfall is concentrated in infrastructure and in the earliest year shown. Theme 6 accounts for 72.6% of the amount below plan (Rs 3.36 crore), despite representing 26.4% of activities; its spending-to-plan ratio is 19.6%. For 2020-2021, the shortfall is Rs 2.54 crore, or 54.9% of the total, although that year accounts for 3.2% of activities; spending was 12.3% of that year’s plan. Maintenance accounts for 85.0% of the untied grant planned (Rs 4.25 crore), while representing 12.9% of activities. 

The scheme field is missing for 827 rows, which are counted as “not recorded” and account for Rs 3.77 crore, or 57.9% of planned cost; XV Finance Commission accounts for 33.0% (Rs 2.15 crore), and the other two scheme values together account for Rs 59.28 lakh. Approval records also merit reconciliation: 93 activities (10.1%) have an administrative approval on file, and 93 have a technical approval on file. A missing administrative approval record does not establish that an activity was unapproved. The cashbook shows Rs 5.53 crore received and Rs 6.34 crore paid out, while 29.7% of payments are linked to a planned activity. Linked spending totals Rs 1.78 crore across the six fiscal years; the recorded linked share ranges from 2.7% to 53.2%, and a rise in that share may reflect more complete recording unless the cashbook total also rises. 

Work status and evidence present a further review point: 85 works are marked ongoing, none completed, and 19 abandoned, with Rs 1.19 crore planned on them; 6 of the abandoned works were planned in 2025-2026. Ongoing works account for 72.7% of general-component spending (Rs 2.07 crore) while representing 9.2% of activities. At the same time, 36 works planned in 2022-2023 or earlier remain marked ongoing, with 95.6% of their planned cost spent. Photo evidence is available for 80 activities across 7 themes; Theme 6 accounts for 35 of those activities (43.8%), and Theme 5 for 26 (32.5%). These records point to useful checks on missing cost and scheme details, payment-to-plan links, and the status of older and abandoned works.

What the officer sees instead:

```
Sharagada Gram Panchayat
- Sharagada Gram Panchayat has 920 planned activities, the most of 20 Gram Panchayats. The middle value for these 20 is 602.5.
- 722 of them (78.5%) have no cost attached.
- Its planned cost is Rs 6.51 crore, the 4th highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
- Rs 2.74 crore has been sanctioned for the activities with an approval on file, the highest of 20 Gram Panchayats. The middle value is Rs 1.37 crore.
- It spent Rs 1.88 crore on planned activities, the highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
- Spending is 28.9% of the planned cost, the 7th lowest of 20 Gram Panchayats. The middle value is 42.0%.
- Spending is Rs 4.63 crore below plan.
- In 2020-2021: 29 activities, Rs 2.90 crore planned, Rs 35.79 lakh spent, 12.3% of the plan.
- 93 of the 920 activities (10.1%) have an administrative approval on file, the 7th fewest of 20 Gram Panchayats. The middle value is 96.
   (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
- 93 activities have a technical approval on file.
- Its cashbook shows Rs 5.53 crore received and Rs 6.34 crore paid out.
- 29.7% of the payments are linked to a planned activity, the 6th lowest of 20 Gram Panchayats. The middle value is 42.2%.
- 85 works are marked ongoing, the 5th fewest of 20 Gram Panchayats. The middle value is 95.5.
- No works are marked completed.
- 19 works are marked abandoned, with Rs 1.19 crore planned on them. 6 of them were planned in 2025-2026.
- 36 works planned in 2022-2023 or earlier are still marked ongoing. Rs 87.38 lakh of their Rs 91.43 lakh planned cost has been spent (95.6%).
- 80 activities have photo evidence (195 uploads), the 10th most of 20 Gram Panchayats. The middle value is 79.

- Within Gram Panchayat Sharagada, planned cost totals Rs 6.51 crore across 4 scheme values. It is spread across them without one standing out: the largest is (not recorded) at 57.9% (Rs 3.77 crore), then XV Finance Commission at 33.0% (Rs 2.15 crore). The remaining 2 together account for Rs 59.28 lakh. 827 rows carry no scheme on file; they are counted here as (not recorded) and account for Rs 3.77 crore.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, activities planned totals 920 activities across 2 costed or costless values. It is concentrated: Costless accounts for 78.5% of it (722 activities). The one remaining, Costed, accounts for 198 activities.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, activities with photo evidence totals 80 activities across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 6 - Self-sufficient Infrastructure in Village at 43.8% (35 activities), then Theme 5 - Clean and Green Village  at 32.5% (26 activities). The remaining 5 together account for 19 activities. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 26.4% of the 920 activities behind these totals, against 43.8% of activities with photo evidence -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, spending measured against plan totals Rs 4.63 crore below plan across 7 LSDG theme values. It is concentrated: Theme 6 - Self-sufficient Infrastructure in Village accounts for 72.6% of it (Rs 3.36 crore below plan). The remaining 6 together account for Rs 1.27 crore below plan. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 26.4% of the 920 activities behind these totals, against 72.6% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Theme 6 - Self-sufficient Infrastructure in Village is 19.6%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, spending measured against plan totals Rs 4.63 crore below plan across 6 fiscal years. It is concentrated: 2020-2021 accounts for 54.9% of it (Rs 2.54 crore below plan). The remaining 5 together account for Rs 2.09 crore below plan. For size: 2020-2021 holds 3.2% of the 920 activities behind these totals, against 54.9% of spending measured against plan -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, spending linked to a planned activity totals Rs 1.78 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2024-2025 at 28.5% (Rs 50.71 lakh), then 2025-2026 at 27.7% (Rs 49.14 lakh). The remaining 4 together account for Rs 77.78 lakh. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, spending, general component totals Rs 2.84 crore across 5 activity status values. It is concentrated: WORK ONGOING accounts for 72.7% of it (Rs 2.07 crore). The remaining 4 together account for Rs 77.66 lakh. For size: WORK ONGOING holds 9.2% of the 920 activities behind these totals, against 72.7% of spending, general component -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Sharagada, untied grant planned totals Rs 5.00 crore across 4 type of work values. It is concentrated: Maintenance accounts for 85.0% of it (Rs 4.25 crore). The remaining 3 together account for Rs 75.02 lakh. For size: Maintenance holds 12.9% of the 920 activities behind these totals, against 85.0% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-22 - What has been found in Attabira block?

- used 8 of 8 findings, 462 words, 21 sentences, 22.0 words per sentence, 73 figures, 78% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (19 of 63): I4, J, A1, A2, A3, A5, A6, A7, F1, F2, H1, H2, G1, G3, E1, E2, E3, E5, E4

Attabira’s recorded data covers one Gram Panchayat, Hirlipali, with 777 planned activities. Of these, 563 (72.5%) have no cost attached. Planned cost is Rs 2.46 crore and spending is Rs 1.19 crore (48.3% of plan), leaving spending Rs 1.27 crore below plan. 

Records of approvals and activity classification are incomplete in several places. Administrative approval is on file for 89 activities (11.5%), and technical approval is on file for 89; a missing approval entry does not establish that an activity was unapproved. Separately, 688 activities have no scheme recorded, and 688 have no sanctioning authority recorded; the latter account for Rs 1.17 crore of the Rs 1.27 crore gap between spending and plan. Five activities have an approval cost recorded without an approval record, and 62 activities lack an LSDG theme mapping, with Rs 34.45 lakh in planned cost. 

The cashbook records Rs 1.58 crore received and Rs 1.60 crore paid out; 74.3% of payments are linked to a planned activity. Spending linked to planned activities totals Rs 1.06 crore across 6 fiscal years, with 2023-2024 the largest share at 24.9% (Rs 26.50 lakh), followed by 2022-2023 at 24.2% (Rs 25.73 lakh). The linked share rose from 2.7% to 53.2% across those years; the finding cautions that a rise in linked spending can reflect more complete recording unless the cashbook total rises as well. For the spending gap, 2023-2024 accounts for 37.1% (Rs 47.21 lakh) and 2022-2023 for 20.8% (Rs 26.51 lakh); 2023-2024 contains 27.3% of the activities behind the totals. By focus area, Drinking water accounts for 28.2% (Rs 35.94 lakh) of the gap and Sanitation for 18.7% (Rs 23.84 lakh); Drinking water represents 10.7% of the activities behind the totals, and spending there is 50.8% of plan. By sanctioning authority, the gap is concentrated in records with no authority recorded: Rs 1.17 crore, or 91.8%, compared with Rs 10.48 lakh for BDO. 

Work-status records show 89 works marked ongoing and none marked completed. Another 29 are marked abandoned, with Rs 40.19 lakh planned; 16 of these were planned in 2022-2023. The abandoned count is concentrated in 2022-2023, which accounts for 55.2% (16 activities). Of works planned in 2022-2023 or earlier, 52 remain marked ongoing; Rs 63.37 lakh of their Rs 70.00 lakh planned cost has been spent (90.5%). Photo evidence is recorded for 76 activities, across 166 uploads. 

Two cross-block comparisons stand out in the supplied findings. Attabira accounts for all abandoned Agriculture activities across 16 blocks: 1 activity, while the other 15 blocks have 0; Attabira holds 5.0% of the 321 Agriculture activities behind that comparison. For Markets and fairs, abandoned works across 7 blocks carry Rs 11.30 lakh in planned funds; Attabira accounts for Rs 10.30 lakh (91.2%), while holding 22.2% of the 36 activities behind the comparison.

What the officer sees instead:

```
Attabira block
- Attabira block has 1 Gram Panchayat in the data.
- Hirlipali Gram Panchayat: 777 activities, Rs 2.46 crore planned, Rs 1.19 crore spent, 48.3% of the plan.
- Attabira block has 777 planned activities, the 8th most of 16 blocks. The middle value for these 16 is 712.
- 563 of them (72.5%) have no cost attached.
- Its planned cost is Rs 2.46 crore, the 4th lowest of 16 blocks. The middle value is Rs 4.48 crore.
- It spent Rs 1.19 crore on planned activities, the 5th lowest of 16 blocks. The middle value is Rs 1.40 crore.
- Spending is 48.3% of the planned cost, the 5th highest of 16 blocks. The middle value is 36.6%.
- Spending is Rs 1.27 crore below plan.
- 89 of the 777 activities (11.5%) have an administrative approval on file, the 4th fewest of 16 blocks. The middle value is 104.
   (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
- 89 activities have a technical approval on file.
- 5 activities have an approval cost recorded with no approval record.
- 62 activities have no LSDG theme mapped; their planned cost is Rs 34.45 lakh.
- Its cashbook shows Rs 1.58 crore received and Rs 1.60 crore paid out.
- 74.3% of the payments are linked to a planned activity, the 3rd highest of 16 blocks. The middle value is 46.5%.
- 89 works are marked ongoing, the 5th fewest of 16 blocks. The middle value is 104.
- No works are marked completed.
- 29 works are marked abandoned, with Rs 40.19 lakh planned on them. 16 of them were planned in 2022-2023.
- 52 works planned in 2022-2023 or earlier are still marked ongoing. Rs 63.37 lakh of their Rs 70.00 lakh planned cost has been spent (90.5%).
- 76 activities have photo evidence (166 uploads), the 6th fewest of 16 blocks. The middle value is 83.

- Within block Attabira, spending linked to a planned activity totals Rs 1.06 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2023-2024 at 24.9% (Rs 26.50 lakh), then 2022-2023 at 24.2% (Rs 25.73 lakh). The remaining 4 together account for Rs 54.18 lakh. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within block Attabira, spending measured against plan totals Rs 1.27 crore below plan across 2 sanctioning authority values. It is concentrated: (not recorded) accounts for 91.8% of it (Rs 1.17 crore below plan). The one remaining, BDO, accounts for Rs 10.48 lakh below plan. 688 rows carry no sanctioning authority on file; they are counted here as (not recorded) and account for Rs 1.17 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within block Attabira, spending measured against plan totals Rs 1.27 crore below plan across 25 focus area values. It is spread across them without one standing out: the largest is Drinking water at 28.2% (Rs 35.94 lakh below plan), then Sanitation at 18.7% (Rs 23.84 lakh below plan). The remaining 23 together account for Rs 67.59 lakh below plan. For size: Drinking water holds 10.7% of the 777 activities behind these totals, against 28.2% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Drinking water is 50.8%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within block Attabira, activities abandoned totals 29 activities across 6 fiscal years. It is concentrated: 2022-2023 accounts for 55.2% of it (16 activities). The remaining 5 together account for 13 activities.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within block Attabira, activities planned totals 777 activities across 4 scheme values. It is concentrated: (not recorded) accounts for 88.5% of it (688 activities). The remaining 3 together account for 89 activities. 688 rows carry no scheme on file; they are counted here as (not recorded) and account for 688 activities.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within block Attabira, spending measured against plan totals Rs 1.27 crore below plan across 6 fiscal years. It is spread across them without one standing out: the largest is 2023-2024 at 37.1% (Rs 47.21 lakh below plan), then 2022-2023 at 20.8% (Rs 26.51 lakh below plan). The remaining 4 together account for Rs 53.65 lakh below plan. For size: 2023-2024 holds 27.3% of the 777 activities behind these totals, against 37.1% of spending measured against plan -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within focus area Agriculture, activities abandoned totals 1 activities across 16 blocks. It is concentrated: Attabira accounts for 100.0% of it (1 activities). The remaining 15 together account for 0 activities. For size: Attabira holds 5.0% of the 321 activities behind these totals, against 100.0% of activities abandoned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within focus area Markets and fairs, planned money on abandoned works totals Rs 11.30 lakh across 7 blocks. It is concentrated: Attabira accounts for 91.2% of it (Rs 10.30 lakh). The remaining 6 together account for Rs 1.00 lakh. For size: Attabira holds 22.2% of the 36 activities behind these totals, against 91.2% of planned money on abandoned works -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-24 - Is Lahunipara block an exception to anything?

- used 7 of 7 findings, 169 words, 7 sentences, 24.1 words per sentence, 21 figures, 88% of the handed figures, 1 tries
- place facts used (4 of 59): A3, A5, A6, I4

Yes. In the 16-block comparisons, Maintenance and New/Fresh lead untied-grant planned amounts in 13/16 blocks and planned cost in 14/16; they are also among the lowest-spending-against-plan work types in 14/16 blocks. Lahunipara is identified as a different-pattern exception in each of these comparisons, though the findings do not specify which work types lead there.

There is a similar departure by output type: Code 101 and Code 105 lead planned cost and untied-grant plans in 15/16 blocks, and general-component spending and lowest spending against plan in 14/16 blocks. Lahunipara is an exception in these comparisons; the specific spending exception reported is that Code 101 and Code 104, rather than Code 101 and Code 105, are lowest in spending against plan.

Its total planned cost is the lowest of 16 blocks and its spending is the second lowest, but spending is 45.3% of plan, the 7th highest; the middle value is 36.6%. The dataset contains one Gram Panchayat for Lahunipara, so these block figures represent that single GP in the data.

### GEO-26 - How do the GPs in Sheragada block look?

- used 8 of 8 findings, 423 words, 18 sentences, 23.5 words per sentence, 72 figures, 75% of the handed figures, 2 tries
- place facts used (18 of 60): I4, J, A1, A2, A3, A4, A5, A6, A7, E1, E2, E3, E5, E4, F1, F2, G1, G3

Sheragada block’s data cover one Gram Panchayat, Sharagada, with 920 planned activities; that is the 4th most among 16 blocks. Of the activities, 722 (78.5%) have no cost attached. The planned cost is Rs 6.51 crore, Rs 2.74 crore is sanctioned for activities with an approval on file, and Rs 1.88 crore has been spent; spending is 28.9% of plan, compared with a block middle value of 36.6%, and is Rs 4.63 crore below plan. 

By activity count, Theme 8 - Village with Good Governance accounts for 50.1% (461 activities) and Theme 6 - Self-sufficient Infrastructure in Village for 26.4% (243 activities); the other five recorded themes account for 216 activities together. The activity count is greatest in 2023-2024, at 47.1% (433 activities), followed by 2024-2025 at 30.0% (276 activities). Planned cost is greatest in 2020-2021, at 44.5% (Rs 2.90 crore), followed by 2021-2022 at 14.9% (Rs 97.02 lakh). Spending is greatest in 2023-2024, at 23.6% (Rs 44.41 lakh), followed by 2020-2021 at 19.0% (Rs 35.79 lakh); the remaining four years account for Rs 1.08 crore. 

The records show 85 works ongoing and none marked completed; 19 are marked abandoned, with Rs 1.19 crore planned on them. Of the ongoing activities, 84 (98.8%) are attributed to the Gram Panchayat; 827 rows have no sanctioning authority recorded and account for none of the ongoing activities. For context, the Gram Panchayat holds 90.3% of the 93 activities behind that breakdown. Separately, 36 works planned in 2022-2023 or earlier remain marked ongoing; Rs 87.38 lakh of their Rs 91.43 lakh planned cost has been spent (95.6%). Photo evidence is recorded for 80 activities, across 195 uploads. 

An administrative approval is on file for 93 activities (10.1%); absence of an approval record does not establish that an activity was unapproved. A technical approval is on file for 93 activities. In the cross-block breakdown of activities sanctioned by a Gram Panchayat, Sheragada accounts for 68.9% of planned cost (Rs 2.05 crore) across four blocks, while holding 49.4% of the 170 activities in that breakdown. In the block’s general-component spending breakdown, the Gram Panchayat accounts for 72.0% (Rs 2.05 crore); 827 rows with no sanctioning authority recorded account for Rs 10.57 lakh. 

The cashbook records Rs 5.53 crore received and Rs 6.34 crore paid out; 29.7% of payments are linked to a planned activity, compared with a block middle value of 46.5%. At district level, Sharagada accounts for 31.7% (13) of the 41 GPDP plans across four Gram Panchayats, and holds 33.8% of the 2,723 activities behind that comparison.

### GEO-29 - How is Khordha district doing overall?

- used 8 of 8 findings, 348 words, 14 sentences, 24.9 words per sentence, 63 figures, 82% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited, 6_standing. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (9 of 63): A1, A2, A3, A4, A5, A6, A7, G1, G3

In the records reviewed, Khordha has 1,316 planned activities across 1 block and 3 Gram Panchayats; its activity count is the 4th highest among 9 districts. Of these activities, 546 (41.5%) have no cost attached. Planned cost is Rs 5.95 crore, sanctioned amount is Rs 4.06 crore, and spending is Rs 3.33 crore; spending is 55.9% of plan, the highest among 9 districts, while the gap to plan is Rs 2.63 crore. 

Activity numbers are spread fairly evenly across the 3 Gram Panchayats: Andhrua has the largest share, 37.5% (493 activities), compared with an even share of 33.3%. Planned cost is Rs 5.95 crore across the Gram Panchayats, with Andhrua accounting for 42.1% (Rs 2.51 crore), Barimunda 29.7% (Rs 1.77 crore), and Itipur Rs 1.68 crore. Sanctioned amount totals Rs 4.06 crore: Andhrua accounts for 43.2% (Rs 1.76 crore), Barimunda 29.1% (Rs 1.18 crore), and Itipur Rs 1.13 crore. Spending totals Rs 3.33 crore, with Andhrua accounting for 44.7% (Rs 1.49 crore), Barimunda 32.3% (Rs 1.08 crore), and Itipur Rs 76.58 lakh. The Rs 2.63 crore gap to plan is also spread across the Gram Panchayats: Andhrua accounts for Rs 1.02 crore, Itipur Rs 90.99 lakh, and Barimunda Rs 69.45 lakh. 

The gap is distributed across all 6 fiscal years; the largest shares are in 2023-2024 at 23.4% (Rs 61.33 lakh) and 2025-2026 at 22.2% (Rs 58.33 lakh), while the remaining 4 years together account for Rs 1.43 crore below plan. By focus area, Sanitation accounts for the largest stated share of the gap at 26.7% (Rs 70.08 lakh), followed by Drinking water at 13.7% (Rs 35.86 lakh); the remaining 24 focus area values account for Rs 1.57 crore. Sanitation’s spending-to-plan ratio is 44.8%. 

The cashbook records Rs 13.97 crore received and Rs 14.41 crore paid out, while 23.1% of payments are linked to a planned activity, the lowest share among 9 districts. Linked spending totals Rs 3.26 crore across the 6 fiscal years, and the linked share ranges from 2.7% to 53.2% across those years. These payment-linkage figures are worth reconciling against the cashbook and planned-activity records.

What the officer sees instead:

```
Khordha district
- Khordha district has 1,316 planned activities, the 4th most of 9 districts. The middle value for these 9 is 1,129.
- 546 of them (41.5%) have no cost attached.
- Its planned cost is Rs 5.95 crore, the 5th highest of 9 districts. The middle value is Rs 5.95 crore.
- Rs 4.06 crore has been sanctioned for the activities with an approval on file, the 3rd highest of 9 districts. The middle value is Rs 2.33 crore.
- It spent Rs 3.33 crore on planned activities, the 3rd highest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is 55.9% of the planned cost, the highest of 9 districts. The middle value is 35.9%.
- Spending is Rs 2.63 crore below plan.
- Its cashbook shows Rs 13.97 crore received and Rs 14.41 crore paid out.
- 23.1% of the payments are linked to a planned activity, the lowest of 9 districts. The middle value is 47.0%.

- Within district Khordha, spending measured against plan totals Rs 2.63 crore below plan across 3 Gram Panchayats. It is spread across them without one standing out: the largest is Andhrua at 38.9% (Rs 1.02 crore below plan), then Itipur at 34.7% (Rs 90.99 lakh below plan). The one remaining, Barimunda, accounts for Rs 69.45 lakh below plan. For size: Andhrua holds 37.5% of the 1,316 activities behind these totals, against 38.9% of spending measured against plan -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, spending totals Rs 3.33 crore across 3 Gram Panchayats. It is spread across them without one standing out: the largest is Andhrua at 44.7% (Rs 1.49 crore), then Barimunda at 32.3% (Rs 1.08 crore). The one remaining, Itipur, accounts for Rs 76.58 lakh. For size: Andhrua holds 37.5% of the 1,316 activities behind these totals, against 44.7% of spending -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, planned cost totals Rs 5.95 crore across 3 Gram Panchayats. It is spread across them without one standing out: the largest is Andhrua at 42.1% (Rs 2.51 crore), then Barimunda at 29.7% (Rs 1.77 crore). The one remaining, Itipur, accounts for Rs 1.68 crore. For size: Andhrua holds 37.5% of the 1,316 activities behind these totals, against 42.1% of planned cost -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, spending measured against plan totals Rs 2.63 crore below plan across 6 fiscal years. It is spread across them without one standing out: the largest is 2023-2024 at 23.4% (Rs 61.33 lakh below plan), then 2025-2026 at 22.2% (Rs 58.33 lakh below plan). The remaining 4 together account for Rs 1.43 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, spending measured against plan totals Rs 2.63 crore below plan across 26 focus area values. It is spread across them without one standing out: the largest is Sanitation at 26.7% (Rs 70.08 lakh below plan), then Drinking water at 13.7% (Rs 35.86 lakh below plan). The remaining 24 together account for Rs 1.57 crore below plan. For size: Sanitation holds 24.8% of the 1,316 activities behind these totals, against 26.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 44.8%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, sanctioned amount totals Rs 4.06 crore across 3 Gram Panchayats. It is spread across them without one standing out: the largest is Andhrua at 43.2% (Rs 1.76 crore), then Barimunda at 29.1% (Rs 1.18 crore). The one remaining, Itipur, accounts for Rs 1.13 crore. For size: Andhrua holds 37.5% of the 1,316 activities behind these totals, against 43.2% of sanctioned amount -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, activities planned totals 1,316 activities across 3 Gram Panchayats. It is spread evenly across them -- no single Gram Panchayat accounts for it. The largest, Andhrua, holds 37.5% (493 activities), against an even share of 33.3%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Khordha, spending linked to a planned activity totals Rs 3.26 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2025-2026 at 30.8% (Rs 1.01 crore), then 2024-2025 at 26.9% (Rs 87.79 lakh). The remaining 4 together account for Rs 1.38 crore. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-30 - What has the analysis found in Koraput?

- used 8 of 8 findings, 236 words, 13 sentences, 18.2 words per sentence, 34 figures, 57% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (10 of 63): A1, A3, A5, A6, A7, J, J, B, C, A2

Koraput has 1,455 planned activities and Rs 9.51 crore in planned costs. Recorded spending is Rs 3.16 crore, or 33.2% of plan, leaving Rs 6.36 crore below plan. 

The shortfall is concentrated by block and year. Boipariguda accounts for 74.7% of the district’s shortfall (Rs 4.75 crore), despite holding 44.5% of activities; its spending is 22.8% of plan. Laxmipur accounts for the remaining Rs 1.61 crore of the shortfall. In 2023-2024, planned cost was Rs 4.90 crore, and that year accounts for 69.2% of the district shortfall (Rs 4.40 crore). 

Rural housing merits particular attention: Koraput has 24 such activities, with Rs 2.13 crore planned and nothing spent. That is the largest focus-area shortfall in Koraput, at 33.5% of the district total; drinking water is next at 27.4% (Rs 1.74 crore), while the other 23 focus areas together account for Rs 2.48 crore. Across the nine districts, Koraput accounts for 95.7% of the rural-housing shortfall, despite holding 7.9% of the activities in that comparison. 

There are also record-completeness and funding-distribution points to check. Of 1,455 activities, 695 (47.8%) have no cost attached; Laxmipur accounts for 447 of these and Boipariguda for 248. Boipariguda holds 67.6% of planned untied grant (Rs 5.23 crore), against 44.5% of activities. Spending is Rs 37.43 lakh below sanction across the two blocks, with Boipariguda accounting for 57.3% and Laxmipur 42.7%; this comparison covers only activities with a sanction record on file.

What the officer sees instead:

```
Koraput district
- Koraput district has 1,455 planned activities, the 3rd most of 9 districts. The middle value for these 9 is 1,129.
- Its planned cost is Rs 9.51 crore, the 3rd highest of 9 districts. The middle value is Rs 5.95 crore.
- It spent Rs 3.16 crore on planned activities, the 4th highest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is 33.2% of the planned cost, the 4th lowest of 9 districts. The middle value is 35.9%.
- Spending is Rs 6.36 crore below plan.
- Boipariguda block: 647 activities, Rs 6.15 crore planned, Rs 1.41 crore spent, 22.8% of the plan.
- Laxmipur block: 808 activities, Rs 3.36 crore planned, Rs 1.75 crore spent, 52.1% of the plan.
- In 2023-2024: 454 activities (173 with no cost), Rs 4.90 crore planned, Rs 50.50 lakh spent, 10.3% of the plan.
- Rural housing: 24 activities and Rs 2.13 crore planned, with nothing spent.
- 695 of them (47.8%) have no cost attached.

- Within district Koraput, spending measured against plan totals Rs 6.36 crore below plan across 25 focus area values. It is spread across them without one standing out: the largest is Rural housing at 33.5% (Rs 2.13 crore below plan), then Drinking water at 27.4% (Rs 1.74 crore below plan). The remaining 23 together account for Rs 2.48 crore below plan. For size: Rural housing holds 1.6% of the 1,455 activities behind these totals, against 33.5% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Rural housing is 0.0%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, spending measured against plan totals Rs 6.36 crore below plan across 2 blocks. It is concentrated: Boipariguda accounts for 74.7% of it (Rs 4.75 crore below plan). The one remaining, Laxmipur, accounts for Rs 1.61 crore below plan. For size: Boipariguda holds 44.5% of the 1,455 activities behind these totals, against 74.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Boipariguda is 22.8%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, spending measured against plan totals Rs 6.36 crore below plan across 6 fiscal years. It is concentrated: 2023-2024 accounts for 69.2% of it (Rs 4.40 crore below plan). The remaining 5 together account for Rs 1.96 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within focus area Rural housing, spending measured against plan totals Rs 2.23 crore below plan across 9 districts. It is concentrated: Koraput accounts for 95.7% of it (Rs 2.13 crore below plan). The remaining 8 together account for Rs 9.50 lakh below plan. For size: Koraput holds 7.9% of the 305 activities behind these totals, against 95.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Koraput is 0.0%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, planned cost totals Rs 9.51 crore across 6 fiscal years. It is concentrated: 2023-2024 accounts for 51.5% of it (Rs 4.90 crore). The remaining 5 together account for Rs 4.61 crore.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, untied grant planned totals Rs 7.74 crore across 2 blocks. It is concentrated: Boipariguda accounts for 67.6% of it (Rs 5.23 crore). The one remaining, Laxmipur, accounts for Rs 2.51 crore. For size: Boipariguda holds 44.5% of the 1,455 activities behind these totals, against 67.6% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, spending measured against sanction totals Rs 37.43 lakh below sanction across 2 blocks. It is spread across them without one standing out: the largest is Boipariguda at 57.3% (Rs 21.44 lakh below sanction), then Laxmipur at 42.7% (Rs 15.98 lakh below sanction). For size: Boipariguda holds 44.5% of the 1,455 activities behind these totals, against 57.3% of spending measured against sanction -- a group's total grows with how much of the work it holds. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Koraput, activities planned without a cost totals 695 activities across 2 blocks. It is spread across them without one standing out: the largest is Laxmipur at 64.3% (447 activities), then Boipariguda at 35.7% (248 activities). For size: Laxmipur holds 55.5% of the 1,455 activities behind these totals, against 64.3% of activities planned without a cost -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### GEO-32 - Sundergarh district - what should I look at?

- used 8 of 8 findings, 573 words, 26 sentences, 22.0 words per sentence, 70 figures, 61% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (17 of 64): A1, A2, A3, A5, A6, A7, B, B, B, F1, E1, E2, E3, E5, E4, G1, G3

Sundargarh has 1,129 planned activities, the middle value among the 9 districts, but 623 (55.2%) have no cost attached. Its planned cost is Rs 3.88 crore and recorded spending is Rs 1.69 crore (43.5% of plan), leaving Rs 2.19 crore below plan. The activity count is typical for the districts, while the planned and spent amounts are among the lower totals; the spending rate is comparatively high. A useful first check is whether activities without costs can be costed and whether recorded spending reconciles with the plan. 

The missing-cost entries are also numerous in recent plan years: 222 of 363 activities in 2023-2024, 148 of 245 in 2024-2025, and 253 of 357 in 2025-2026 have no cost recorded. Spending was 50.9% of plan in 2023-2024, 32.1% in 2024-2025 and 35.9% in 2025-2026. These records are worth checking alongside the overall plan-to-spending gap. 

The plan-to-spending gap is spread across both Gram Panchayats: Karuabahal accounts for 58.6% (Rs 1.28 crore) and Haldikudar for 41.4% (Rs 90.62 lakh); Karuabahal’s spending is 42.2% of plan. On the smaller set of activities with a sanction record, spending is Rs 37.66 lakh below sanction, with Haldikudar accounting for 65.9% of that gap and spending 75.2% of sanction. The sanctioned comparison covers only activities with a sanction record on file, about one in six. 

Record completeness merits a separate check: 162 activities (14.3%) have an administrative approval on file, and the absence of a recorded approval does not establish that an activity was unapproved. Separately, 967 rows have no sanctioning authority recorded and account for 82.8% (Rs 1.81 crore) of the plan-to-spending gap. Reconcile these fields against the underlying approvals and sanction records. 

The sector pattern points to drinking water and sanitation for closer reconciliation. Together they account for the largest portions of the plan-to-spending gap: 29.4% (Rs 64.45 lakh) for drinking water and 25.2% (Rs 55.17 lakh) for sanitation. In the voucher-linked spending totals, Roads and Drinking water are the largest contributors, at 23.6% (Rs 39.90 lakh) and 23.5% (Rs 39.63 lakh), respectively. On the sanctioned subset, Sanitation accounts for 32.6% of the gap below sanction and Drinking water for 23.3%; Sanitation spending is 67.2% of its sanction. 

Untied grant plans are concentrated differently from the activity counts: Theme 6 - Self-sufficient Infrastructure in Village accounts for 52.9% (Rs 1.37 crore) of untied grant planned while holding 20.9% of the activities. Across focus areas, Roads account for 22.3% (Rs 57.84 lakh) of untied grant planned and Drinking water for 13.8% (Rs 35.67 lakh), with no single focus area standing out. Reviewing the link between the larger allocations and their activity-level approvals and spending would help clarify the recorded pattern. 

Work-status and evidence records are another practical review point: 160 works are marked ongoing, none completed, and 17 abandoned, with Rs 29.26 lakh planned on the abandoned works; 7 of those were planned in 2021-2022. Of works planned in 2022-2023 or earlier, 95 remain marked ongoing, with Rs 94.33 lakh of their Rs 1.18 crore planned cost spent. Photo evidence is recorded for 103 activities (603 uploads). Comparing work status, payment records and available photos would help identify records needing follow-up. 

For that reconciliation, the cashbook shows Rs 2.91 crore received and Rs 2.54 crore paid out; 66.5% of payments are linked to a planned activity, the highest share among the 9 districts. This provides a useful starting point for matching payments to planned activities and the supporting work records.

What the officer sees instead:

```
Sundargarh district
- Sundargarh district has 1,129 planned activities, the 5th most of 9 districts. The middle value for these 9 is 1,129.
- 623 of them (55.2%) have no cost attached.
- Its planned cost is Rs 3.88 crore, the 3rd lowest of 9 districts. The middle value is Rs 5.95 crore.
- It spent Rs 1.69 crore on planned activities, the 3rd lowest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is 43.5% of the planned cost, the 3rd highest of 9 districts. The middle value is 35.9%.
- Spending is Rs 2.19 crore below plan.
- In 2023-2024: 363 activities (222 with no cost), Rs 55.73 lakh planned, Rs 28.39 lakh spent, 50.9% of the plan.
- In 2024-2025: 245 activities (148 with no cost), Rs 87.63 lakh planned, Rs 28.13 lakh spent, 32.1% of the plan.
- In 2025-2026: 357 activities (253 with no cost), Rs 50.17 lakh planned, Rs 18.01 lakh spent, 35.9% of the plan.
- 162 of the 1,129 activities (14.3%) have an administrative approval on file, the 3rd fewest of 9 districts. The middle value is 181.
   (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
- 160 works are marked ongoing, the 4th fewest of 9 districts. The middle value is 181.
- No works are marked completed.
- 17 works are marked abandoned, with Rs 29.26 lakh planned on them. 7 of them were planned in 2021-2022.
- 95 works planned in 2022-2023 or earlier are still marked ongoing. Rs 94.33 lakh of their Rs 1.18 crore planned cost has been spent (80.3%).
- 103 activities have photo evidence (603 uploads), the 3rd fewest of 9 districts. The middle value is 166.
- Its cashbook shows Rs 2.91 crore received and Rs 2.54 crore paid out.
- 66.5% of the payments are linked to a planned activity, the highest of 9 districts. The middle value is 47.0%.

- Within district Sundargarh, untied grant planned totals Rs 2.59 crore across 7 LSDG theme values. It is concentrated: Theme 6 - Self-sufficient Infrastructure in Village accounts for 52.9% of it (Rs 1.37 crore). The remaining 6 together account for Rs 1.22 crore. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 20.9% of the 1,129 activities behind these totals, against 52.9% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, untied grant planned totals Rs 2.59 crore across 27 focus area values. It is spread across them without one standing out: the largest is Roads at 22.3% (Rs 57.84 lakh), then Drinking water at 13.8% (Rs 35.67 lakh). The remaining 25 together account for Rs 1.65 crore. For size: Roads holds 2.1% of the 1,129 activities behind these totals, against 22.3% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, spending measured against plan totals Rs 2.19 crore below plan across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Karuabahal at 58.6% (Rs 1.28 crore below plan), then Haldikudar at 41.4% (Rs 90.62 lakh below plan). For size: Karuabahal holds 48.4% of the 1,129 activities behind these totals, against 58.6% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Karuabahal is 42.2%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, spending measured against plan totals Rs 2.19 crore below plan across 27 focus area values. It is spread across them without one standing out: the largest is Drinking water at 29.4% (Rs 64.45 lakh below plan), then Sanitation at 25.2% (Rs 55.17 lakh below plan). The remaining 25 together account for Rs 99.40 lakh below plan. For size: Drinking water holds 7.8% of the 1,129 activities behind these totals, against 29.4% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Drinking water is 38.1%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, spending measured against plan totals Rs 2.19 crore below plan across 4 sanctioning authority values. It is concentrated: (not recorded) accounts for 82.8% of it (Rs 1.81 crore below plan). The remaining 3 together account for Rs 37.66 lakh below plan. 967 rows carry no sanctioning authority on file; they are counted here as (not recorded) and account for Rs 1.81 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, spending measured against sanction totals Rs 37.66 lakh below sanction across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Haldikudar at 65.9% (Rs 24.83 lakh below sanction), then Karuabahal at 34.1% (Rs 12.82 lakh below sanction). For size: Haldikudar holds 51.6% of the 1,129 activities behind these totals, against 65.9% of spending measured against sanction -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Haldikudar is 75.2%. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, voucher-linked spending totals Rs 1.69 crore across 27 focus area values. It is spread across them without one standing out: the largest is Roads at 23.6% (Rs 39.90 lakh), then Drinking water at 23.5% (Rs 39.63 lakh). The remaining 25 together account for Rs 89.33 lakh. For size: Roads holds 2.1% of the 1,129 activities behind these totals, against 23.6% of voucher-linked spending -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within district Sundargarh, spending measured against sanction totals Rs 37.66 lakh below sanction across 27 focus area values. It is spread across them without one standing out: the largest is Sanitation at 32.6% (Rs 12.29 lakh below sanction), then Drinking water at 23.3% (Rs 8.79 lakh below sanction). The remaining 25 together account for Rs 16.58 lakh below sanction. For size: Sanitation holds 18.3% of the 1,129 activities behind these totals, against 32.6% of spending measured against sanction -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 67.2%. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### L01 - What should I know about Kandhamal?

- used 8 of 8 findings, 449 words, 21 sentences, 21.4 words per sentence, 77 figures, 86% of the handed figures, 2 tries
- place facts used (17 of 62): I4, A1, A2, A3, A4, A5, A6, A7, D, F1, F2, E1, E5, E3, E4, G1, G3

In this dataset, Kandhamal is represented by one block and one Gram Panchayat. The recorded plan has 573 activities, the 2nd fewest of 9 districts, and 241 (42.1%) have no cost attached. Planned cost is Rs 3.48 crore, the 2nd lowest of 9 districts. The amount sanctioned for activities with an approval on file is Rs 1.14 crore, the lowest of 9 districts. Spending on planned activities is Rs 58.17 lakh, also the lowest, and is 16.7% of plan; it is Rs 2.90 crore below plan.

The planned cost is mostly untied grant: Rs 2.80 crore (80.3%), compared with Rs 68.50 lakh in tied grant (19.7%). Across focus areas, drinking water accounts for 25.7% of planned cost (Rs 89.50 lakh), followed by maintenance of community system at 19.8% (Rs 68.83 lakh); the remaining 23 focus areas together account for Rs 1.90 crore. Within tied grant, drinking water accounts for 57.6% (Rs 39.48 lakh) and sanitation for 42.4% (Rs 29.01 lakh), with the remaining 23 focus areas accounting for Rs 0. Within untied grant, Theme 6—Self-sufficient Infrastructure in Village—accounts for 67.9% (Rs 1.90 crore), although it contains 37.5% of the activities; the other six themes together account for Rs 89.87 lakh.

Record completeness is a review point. Of the 573 activities, 437 (76.3%) have no scheme on file; separately, 437 activities have no fund component on file. Of the 241 activities without a cost, 167 were planned in 2023-2024. The finding notes that a missing approval on file does not establish that an activity was unapproved: 136 activities (23.7%) have an administrative approval on file, the 2nd fewest of 9 districts, and 136 have a technical approval on file.

There are 132 activities marked ongoing, the 2nd fewest of 9 districts. Among these, 53 (40.2%) are in Theme 4—Water Sufficient Village—and 37 (28.0%) in Theme 5—Clean and Green Village. Also check the status of older works: 42 works planned in 2022-2023 or earlier remain marked ongoing, while 17 works are marked abandoned, with Rs 24.81 lakh planned; 16 of those were planned in 2022-2023. Photo evidence is attached to 75 activities (239 uploads), the fewest of 9 districts.

The cashbook shows Rs 1.69 crore received and Rs 1.24 crore paid out; 47.0% of payments are linked to a planned activity. Recorded spending linked to planned activities totals Rs 51.44 lakh across six fiscal years; the largest shares are in 2025-2026 at 30.1% (Rs 15.49 lakh) and 2024-2025 at 25.9% (Rs 13.34 lakh), with the other four years together accounting for Rs 22.61 lakh. The linked share ranges from 2.7% to 53.2% across those years. Treat changes in that share as changes in recording completeness unless the cashbook total also rises.

### L04 - what should I know about Cuttack?

- used 8 of 8 findings, 336 words, 16 sentences, 21.0 words per sentence, 53 figures, 68% of the handed figures, 2 tries
- place facts used (18 of 63): I4, A1, A2, A3, A5, A6, A7, A4, J, J, F1, F2, G3, E1, E2, E3, E5, E4

Cuttack’s records cover 1,104 planned activities across 2 Gram Panchayats; 465 activities (42.1%) have no cost attached. Planned cost is Rs 5.35 crore, while spending is Rs 2.17 crore, or 40.5% of plan, leaving spending Rs 3.18 crore below plan. The district has Rs 2.33 crore sanctioned for activities with an approval on file. 

The district totals conceal different patterns across the two Gram Panchayats: Govindapur accounts for 56.2% (Rs 3.00 crore) of planned cost, while Dadhapatna accounts for 57.1% (Rs 1.24 crore) of spending. Govindapur holds 48.8% of activities and 71.1% of reported population (4,269 people), while Dadhapatna holds 51.2% of activities and has 1,734 people. The gap between plan and spending is also uneven: Govindapur accounts for 65.3% (Rs 2.07 crore) of the shortfall, and its spending-to-plan ratio is 30.9%. At block level, spending is 30.9% of plan in Tangi Choudwar and 52.9% in Baranga. 

Sanitation is the largest activity group, with 343 activities (31.1%), followed by maintenance of community system, with 162 (14.7%). Untied grant planning is concentrated differently: Roads accounts for 41.6% (Rs 1.53 crore), while the remaining 23 focus areas together account for Rs 1.74 crore; Roads represents 5.9% of activities. By LSDG theme, Theme 6—Self-sufficient Infrastructure in Village—accounts for 84.3% (Rs 3.11 crore) of untied grant planned, against 43.6% of activities. For general-component spending, Roads accounts for 24.2% (Rs 57.60 lakh) and Drinking water for 22.7% (Rs 54.22 lakh). 

A records review may be useful: 181 activities (16.4%) have an administrative approval on file, and 181 have a technical approval on file; absence of an approval record does not establish that approval was not given. Payments linked to a planned activity are 23.8% of payments, the second lowest among the nine districts. Work-status records show 181 works marked ongoing and none marked completed; 125 are marked abandoned, including 95 planned in 2023-2024. Separately, 90 works planned in 2022-2023 or earlier remain marked ongoing, with 92.1% of their planned cost spent. There is photo evidence for 166 activities, across 394 uploads.

### L06 - What should I know about Kalimela?

- used 7 of 8 findings, 449 words, 20 sentences, 22.4 words per sentence, 76 figures, 70% of the handed figures, 2 tries
- **LOST** on 4_all_findings_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (25 of 61): I4, A1, A3, A4, A5, A6, A7, A2, B, B, B, B, C, C, C, C, H2, D, E1, E2, E5, E3, E4, G1, G3

Kalimela block has one Gram Panchayat in the data. That GP has 852 planned activities, the 5th most among 16 blocks, and a planned cost of Rs 7.65 crore, the 2nd highest; Rs 2.08 crore has been sanctioned for activities with an approval on file. Spending is Rs 1.76 crore, or 23.0% of planned cost—the 4th-lowest rate among blocks—and Rs 5.90 crore below plan. A substantial portion of the plan needs record-level attention: 392 activities (46.0%) have no cost attached. 

Spending against plan is particularly low in the more recent years shown: it was 11.1% in 2023-2024, 10.5% in 2024-2025 and 19.1% in 2025-2026, compared with 93.6% in 2020-2021. Drinking water accounts for Rs 3.74 crore of planned cost, with Rs 60.98 lakh spent; land improvement has Rs 73.95 lakh planned and no spending recorded. Maintenance of community systems has Rs 62.03 lakh planned and Rs 11.54 lakh spent, while sanitation has Rs 52.89 lakh planned and Rs 33.62 lakh spent. 

The records also show gaps in how activities are classified. Of the 852 activities, 684 (80.3%) have no fund component recorded; 684 rows also have no scheme recorded, accounting for 72.7% of planned cost (Rs 5.57 crore). Forty-nine activities, with Rs 34.90 lakh planned, have no LSDG theme mapped. By asset category, Uncategorised accounts for 28.0% of planned cost (Rs 2.14 crore), while Water Sources & Structures accounts for 23.9% (Rs 1.83 crore); Uncategorised covers 57.5% of activities. 

Expected beneficiaries total 8,820 across the recorded LSDG themes; Theme 1 accounts for 45.1% (3,978 people), although it covers 3.1% of activities. The planned tied grant is Rs 92.28 lakh, divided between sanitation at 50.5% (Rs 46.59 lakh) and drinking water at 49.5% (Rs 45.69 lakh). 

Recorded spending under the general component totals Rs 2.07 crore across 24 focus areas: drinking water is the largest share at 34.3% (Rs 70.85 lakh), followed by sanitation at 20.0% (Rs 41.40 lakh), with the remaining 22 areas together accounting for Rs 94.29 lakh. Public Works accounts for 100.0% of this spending total (Rs 2.06 crore); Beneficiary Oriented Programmes accounts for Rs 5,000. 

Work-status records merit review alongside the spending figures: 154 works are marked ongoing, while 13 are marked completed, out of 17 completed works in the sample. Fifty-five works planned in 2022-2023 or earlier remain marked ongoing; Rs 89.63 lakh of their Rs 1.04 crore planned cost is recorded as spent (86.0%). Another 22 works are marked abandoned, with Rs 2.72 lakh planned; 21 were planned in 2024-2025. Photo evidence is recorded for 129 activities, with 553 uploads. Finally, the cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out, while 33.3% of payments are linked to a planned activity.

What the officer sees instead:

```
This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".

Kalimela block
- Kalimela block has 1 Gram Panchayat in the data.
- Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
- Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.
- Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 5th highest of 16 blocks. The middle value is Rs 1.51 crore.
- It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.
- Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.
- Spending is Rs 5.90 crore below plan.
- 392 of them (46.0%) have no cost attached.
- In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.
- In 2024-2025: 268 activities (72 with no cost), Rs 3.00 crore planned, Rs 31.60 lakh spent, 10.5% of the plan.
- In 2025-2026: 169 activities (124 with no cost), Rs 58.60 lakh planned, Rs 11.20 lakh spent, 19.1% of the plan.
- In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.
- Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.
- Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.
- Maintenance of community system: 100 activities, Rs 62.03 lakh planned, Rs 11.54 lakh spent.
- Sanitation: 118 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent.
- 49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.
- Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).
- 154 works are marked ongoing, the 5th most of 16 blocks. The middle value is 104.
- 13 works are marked completed, out of 17 in the whole sample.
- 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).
- 22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.
- 129 activities have photo evidence (553 uploads), the 5th most of 16 blocks. The middle value is 83.
- Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.
- 33.3% of the payments are linked to a planned activity, the 6th lowest of 16 blocks. The middle value is 46.5%.

- Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 34.3% (Rs 70.85 lakh), then Sanitation at 20.0% (Rs 41.40 lakh). The remaining 22 together account for Rs 94.29 lakh. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 34.3% of spending, general component -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, activities planned totals 852 activities across 6 fund component values. It is concentrated: (not recorded) accounts for 80.3% of it (684 activities). The remaining 5 together account for 168 activities. 684 rows carry no fund component on file; they are counted here as (not recorded) and account for 684 activities.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 4 scheme values. It is concentrated: (not recorded) accounts for 72.7% of it (Rs 5.57 crore). The remaining 3 together account for Rs 2.09 crore. 684 rows carry no scheme on file; they are counted here as (not recorded) and account for Rs 5.57 crore.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 24 focus area values. It is spread across them without one standing out: the largest is Drinking water at 48.8% (Rs 3.74 crore), then Land improvement at 9.7% (Rs 73.95 lakh). The remaining 22 together account for Rs 3.18 crore. For size: Drinking water holds 19.5% of the 852 activities behind these totals, against 48.8% of planned cost -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, expected beneficiaries totals 8,820 people across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 1 - Poverty Free and Enhanced Livelihoods Village at 45.1% (3,978 people), then Theme 6 - Self-sufficient Infrastructure in Village at 15.5% (1,367 people). The remaining 5 together account for 3,475 people. For size: Theme 1 - Poverty Free and Enhanced Livelihoods Village holds 3.1% of the 852 activities behind these totals, against 45.1% of expected beneficiaries -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, spending, general component totals Rs 2.07 crore across 2 activity type values. It is concentrated: Public Works accounts for 100.0% of it (Rs 2.06 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs 5,000. For size: Public Works holds 82.3% of the 852 activities behind these totals, against 100.0% of spending, general component -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, planned cost totals Rs 7.65 crore across 22 asset category values. It is spread across them without one standing out: the largest is Uncategorised at 28.0% (Rs 2.14 crore), then Water Sources & Structures at 23.9% (Rs 1.83 crore). The remaining 20 together account for Rs 3.68 crore. For size: Uncategorised holds 57.5% of the 852 activities behind these totals, against 28.0% of planned cost -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Kalimela, tied grant planned totals Rs 92.28 lakh across 24 focus area values. It is spread across them without one standing out: the largest is Sanitation at 50.5% (Rs 46.59 lakh), then Drinking water at 49.5% (Rs 45.69 lakh). The remaining 22 together account for Rs 0. For size: Sanitation holds 13.8% of the 852 activities behind these totals, against 50.5% of tied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked.

(as of 2026-09-11)
```

### T02 - How is Chikilli doing?

- used 8 of 8 findings, 404 words, 17 sentences, 23.8 words per sentence, 50 figures, 52% of the handed figures, 2 tries
- place facts used (17 of 65): A1, A3, A2, A5, A6, A7, A4, E1, E2, E3, E5, E4, F1, F2, H1, G1, G3

Chikilli has 640 planned activities, the 9th most among the 20 Gram Panchayats in the sample, and a planned cost of Rs 5.51 crore, the 6th highest. However, 329 activities (51.4%) have no cost attached. Recorded spending is Rs 1.39 crore, or 25.2% of planned cost, compared with a sample middle value of 42.0%; the recorded gap against plan is Rs 4.12 crore. Nothing has been sanctioned on record. 

The plan and spending shortfall are concentrated in infrastructure, especially Theme 6 - Self-sufficient Infrastructure in Village: it accounts for 59.5% of planned cost and 63.4% of the gap against plan, with spending at 20.2% of plan. Across focus areas, the largest recorded gaps are Maintenance of community system at Rs 98.63 lakh and Roads at Rs 74.02 lakh; the remaining 26 focus areas together account for Rs 2.39 crore of the gap. The shortfall is spread across fiscal years: 2024-2025 has the largest share, Rs 1.38 crore (33.5%), followed by 2020-2021 at Rs 83.01 lakh (20.2%). Of recorded spending, 2021-2022 accounts for the largest share, Rs 31.82 lakh (22.9%), followed by 2024-2025 at Rs 26.63 lakh (19.2%). 

Work-status records merit review alongside the spending figures: 65 works are marked ongoing, the fewest in the sample, none are marked completed, and 25 are marked abandoned, with Rs 46.72 lakh planned on them. Of works planned in 2022-2023 or earlier, 35 remain marked ongoing; Rs 70.25 lakh of their Rs 83.53 lakh planned cost is recorded as spent (84.1%). No activities have photo evidence. In the general component, WORK ONGOING accounts for 93.1% of recorded spending, although it represents 10.2% of the activities. 

Approval records also need checking: none of the 640 activities has an administrative approval on file, and none has a technical approval on file. The absence of an administrative approval on file does not establish that an activity was unapproved; 71 activities have an approval cost recorded but no approval record. 

The cashbook shows Rs 2.35 crore received and Rs 2.77 crore paid out; 50.1% of payments are linked to planned activities, compared with the sample middle value of 42.2%. Linked spending totals Rs 1.30 crore across six fiscal years, and the linked share rose from 2.7% to 53.2%; that rise may reflect more complete recording unless the cashbook total rose as well. Reconciling cashbook payments with planned activities, approvals, work status and photo records would help clarify what the recorded figures represent.

### T04 - How is Barpali block doing?

- used 8 of 8 findings, 405 words, 18 sentences, 22.5 words per sentence, 64 figures, 75% of the handed figures, 2 tries
- place facts used (16 of 62): A1, A2, A3, A4, A5, A6, A7, E1, E2, E3, E5, E4, F1, F2, G1, G3

Barpali has 1,447 planned activities, the most among 16 blocks (the middle value is 712); 1,067 (73.7%) have no cost attached. Its planned cost is Rs 5.49 crore, while Rs 2.96 crore has been sanctioned for activities with an approval on file. It has spent Rs 2.64 crore, the 3rd highest of 16 blocks; this is 48.1% of planned cost, compared with the 36.6% middle value, leaving spending Rs 2.85 crore below plan. 

The recorded gap to plan is concentrated in Bandhpali: it accounts for 68.2% (Rs 1.94 crore), while Bhatigaon accounts for Rs 90.49 lakh. Bandhpali has 50.4% of activities but 61.0% of planned cost; its share of spending is 53.1%, compared with Bhatigaon’s 46.9%. Spending as a proportion of plan is 41.9% in Bandhpali. The gap is spread across fiscal years: 2025-2026 accounts for 28.2% (Rs 80.35 lakh) and 2023-2024 for 22.0% (Rs 62.62 lakh), with the remaining four together accounting for Rs 1.42 crore. Spending itself is spread across six fiscal years; 2020-2021 is the largest share at 21.0% (Rs 55.47 lakh), against an even share of 16.7%. 

Work status merits checking alongside expenditure: 171 works are marked ongoing, split between Bhatigaon (88) and Bandhpali (83), and none are marked completed. A further 40 works are marked abandoned, with Rs 79.58 lakh planned on them; 19 were planned in 2022-2023. Of works planned in 2022-2023 or earlier, 76 remain marked ongoing; Rs 1.30 crore of their Rs 1.41 crore planned cost has been spent (92.0%). Photo evidence is recorded for 147 activities, with 417 uploads. 

Approval and payment records provide another reconciliation point: 180 of the 1,447 activities have an administrative approval on file, and 176 have a technical approval on file. An approval not appearing in the records does not establish that an activity was unapproved. Separately, the measure labelled “activities under approval” covers 6 activities, all in Bandhpali, and 0 in Bhatigaon. The cashbook records Rs 3.59 crore received and Rs 3.28 crore paid out; 80.4% of payments are linked to a planned activity, the highest share among 16 blocks. 

In the general-component breakdown, spending totals Rs 2.99 crore across 7 LSDG theme values: Theme 6 accounts for 33.1% (Rs 99.22 lakh), Theme 4 for 30.6% (Rs 91.57 lakh), and the remaining five together for Rs 1.09 crore. For follow-up, the records point to checking missing activity costs and reconciling approvals, payments, and the status of ongoing or abandoned works.

### T14 - Anything I should be looking at in Ganjam?

- used 8 of 8 findings, 427 words, 15 sentences, 28.5 words per sentence, 60 figures, 86% of the handed figures, 2 tries
- place facts used (9 of 70): I4, A1, A3, A2, A5, A6, A7, CT, G3

In the Ganjam data available here—covering 3 blocks and 4 Gram Panchayats—there are 2,723 planned activities, the 2nd most of 9 districts, and Rs 23.85 crore in planned costs, the highest of 9 districts. Of those activities, 1,768 (64.9%) have no cost attached. Spending is Rs 6.00 crore, the highest among the districts, but equals 25.2% of planned cost, the 3rd lowest; it is Rs 17.85 crore below plan. 

The activities without a recorded cost are spread across the four Gram Panchayats: Sharagada has the largest share at 40.8% (722 activities), followed by Mendarajpur at 23.8% (421); the other two together account for 625. The overall plan-to-spending gap is also spread across the four Gram Panchayats: Biswamathpur accounts for 40.5% (Rs 7.23 crore below plan), Sharagada for 25.9% (Rs 4.63 crore below plan), and the remaining two together for Rs 6.00 crore below plan. By theme, Theme 6 - Self-sufficient Infrastructure in Village accounts for 50.9% (Rs 9.08 crore) of the gap, compared with its 38.1% share of activities; its spending is 23.1% of planned cost. By year, the largest shares of the gap are in 2023-2024 at 36.1% (Rs 6.44 crore) and 2020-2021 at 25.3% (Rs 4.52 crore); the other four years together account for Rs 6.88 crore. 

Abandoned works merit a separate check: planned costs on these works total Rs 1.91 crore across the four Gram Panchayats, with Sharagada accounting for 62.1% (Rs 1.19 crore); the other three together account for Rs 72.47 lakh. The spending gap against sanction is Rs 1.68 crore across the four Gram Panchayats, with Sharagada accounting for 51.0% (Rs 85.77 lakh) and the other three together for Rs 82.57 lakh. This comparison covers only activities with a sanction record on file—about one in six—so it should be read on that basis. 

For reconciliation across blocks, approvals on file total Rs 6.30 crore: Rangeilunda accounts for 56.5% (Rs 3.56 crore), Sheragada for 43.5% (Rs 2.74 crore), and Khallikote for Rs 0. Spending linked to a planned activity totals Rs 5.65 crore: Rangeilunda accounts for 45.5% (Rs 2.57 crore), Sheragada for 31.4% (Rs 1.78 crore), and Khallikote for Rs 1.30 crore. Overall, 35.4% of payments are linked to a planned activity, the 4th lowest of 9 districts. The linked share went from 2.7% to 53.2% across six years; the finding cautions that a rise in this share indicates more complete recording unless the cashbook total also rises. These figures point to checks on missing activity costs, the status and records for abandoned works, and the links between approvals, planned activities and payments.

### TWO-01 - Compare Kalimela and Bheden

- used 8 of 8 findings, 383 words, 14 sentences, 27.4 words per sentence, 70 figures, 98% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A2, A2, A3, A3, A4, A4, A5, A5, A6, A6, A7, A7

Kalimela and Bheden have similar numbers of planned activities: 852 in Kalimela and 838 in Bheden, ranking 5th and 6th among 16 blocks, respectively. Across the six Gram Panchayats recorded under “panchayat bhawan No,” Kalimela accounts for 22.9% of 3,721 activities and Bheden for 22.5%; the other four account for 2,031. Cost is missing for 392 activities in Kalimela (46.0%) and 466 in Bheden (55.6%). Of the 1,759 activities with a cost across the six Gram Panchayats, Kalimela has 460 (26.2%) and Bheden 372 (21.1%); the other four account for 927. Reported population is 10,681 in Kalimela (31.0% of the six-GP total) and 9,005 in Bheden (26.1%); the other four account for 14,776. 

Planned costs are Rs 7.65 crore in Kalimela, the 2nd highest among 16 blocks, and Rs 7.22 crore in Bheden, the 3rd highest; the middle value is Rs 4.48 crore. Across the six Gram Panchayats, those amounts are 33.4% and 31.5% of the total planned cost of Rs 22.92 crore; the other four account for Rs 8.05 crore. Sanctions on activities with an approval on file total Rs 2.08 crore in Kalimela and Rs 1.76 crore in Bheden, ranking 5th and 7th among the 16 blocks, respectively. These are 23.4% and 19.8% of the six-GP sanctioned total of Rs 8.88 crore; the other four account for Rs 5.05 crore. 

Spending on planned activities is Rs 1.76 crore in Kalimela and Rs 1.62 crore in Bheden, ranking 5th and 7th among the 16 blocks, respectively. Across the six Gram Panchayats, Kalimela accounts for 22.9% and Bheden for 21.1% of the Rs 7.68 crore spent; the other four account for Rs 4.30 crore. Spending is 23.0% of planned cost in Kalimela and 22.4% in Bheden, against a middle value of 36.6%; these are the 4th-lowest and 2nd-lowest rates among the 16 blocks, respectively. The recorded shortfall against plan is Rs 5.90 crore in Kalimela and Rs 5.60 crore in Bheden; together they account for 38.7% and 36.7% of the six-GP shortfall of Rs 15.24 crore, while the other four account for Rs 3.75 crore. For the general component, recorded spending is Rs 2.07 crore in Kalimela and Rs 1.72 crore in Bheden, respectively 24.2% and 20.2% of the six-GP total of Rs 8.53 crore; the other four account for Rs 4.75 crore.

### TWO-02 - How does Chikilli compare with Hirlipali?

- used 8 of 8 findings, 303 words, 13 sentences, 23.3 words per sentence, 44 figures, 87% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A2, A2, A3, A3, A4, A4, A5, A5, A6, A6, A7, A7

In this 20-GP sample, Chikilli has 640 planned activities and Hirlipali 777; the middle value is 602.5. More of Chikilli’s activities have a cost attached: 329 (51.4%) have no cost, compared with 563 (72.5%) in Hirlipali. Despite its lower activity count, Chikilli’s planned cost is Rs 5.51 crore, against Rs 2.46 crore in Hirlipali; the middle value is Rs 3.10 crore. 

The recorded sanction position differs: nothing has been sanctioned on record in Chikilli, while Hirlipali has Rs 1.25 crore sanctioned for activities with an approval on file. Findings across fiscal years also place Chikilli lowest among Gram Panchayats for sanctioned amount and proposed cost at sanction. In 5/6 fiscal years, Chikilli had the lowest number of activities with technical approval and the lowest number with administrative approval; 2023-2024 was the exception in both cases. 

Recorded spending on planned activities is Rs 1.39 crore in Chikilli and Rs 1.19 crore in Hirlipali. This is 25.2% of plan in Chikilli and 48.3% in Hirlipali, against a middle value of 42.0%; the respective gaps below plan are Rs 4.12 crore and Rs 1.27 crore. Separate general-component breakdowns show spending totals of Rs 1.63 crore in Chikilli and Rs 1.30 crore in Hirlipali, distributed across themes without one theme standing out in either Panchayat. In Chikilli, Theme 6 accounts for 46.9% (Rs 76.32 lakh) and Theme 5 for 19.2% (Rs 31.28 lakh), with the remaining 5 themes accounting for Rs 55.28 lakh. In Hirlipali, Theme 6 accounts for 33.7% (Rs 43.89 lakh) and Theme 4 for 32.0% (Rs 41.67 lakh), with the remaining 5 themes accounting for Rs 44.56 lakh. 

Across 19/20 Gram Panchayats, spending measured against plan is spread evenly across fund components; Chikilli is the exception. The same pattern is reported for spending measured against sanction: 19/20 are evenly spread, with Chikilli the exception.

### TWO-03 - Compare Khordha and Cuttack districts

- used 8 of 8 findings, 382 words, 16 sentences, 23.9 words per sentence, 63 figures, 94% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A3, A3, A2, A2, A4, A4, A5, A5, A6, A6, A7, A7

Khordha has more planned activities than Cuttack (1,316 versus 1,104), while its planned cost is also higher (Rs 5.95 crore versus Rs 5.35 crore). The share of activities without a cost attached is similar: 41.5% in Khordha and 42.1% in Cuttack. 

Khordha has Rs 4.06 crore sanctioned, compared with Rs 2.33 crore in Cuttack; recorded spending is Rs 3.33 crore and Rs 2.17 crore, respectively. Spending represents 55.9% of planned cost in Khordha—the highest of the nine districts—and 40.5% in Cuttack; the middle value is 35.9%. The amounts below plan are Rs 2.63 crore in Khordha and Rs 3.18 crore in Cuttack. 

Within Cuttack, the two Gram Panchayats’ totals are described as spread without one standing out. Dadhapatna accounts for 57.1% of spending (Rs 1.24 crore) and holds 51.2% of the activities; Govindapur accounts for 42.9% of spending (Rs 92.85 lakh). Govindapur accounts for 65.3% of the amount below plan (Rs 2.07 crore), compared with Dadhapatna’s 34.7% (Rs 1.10 crore); Govindapur’s ratio is 30.9%. Planned cost is split between Govindapur at 56.2% (Rs 3.00 crore) and Dadhapatna at 43.8% (Rs 2.34 crore); Govindapur holds 48.8% of the activities. Of spending linked to planned activities, Dadhapatna accounts for 58.3% (Rs 1.20 crore) and Govindapur 41.7% (Rs 86.26 lakh); Dadhapatna holds 42.5% of the 831 vouchers. 

Khordha’s totals are also described as spread across its three Gram Panchayats without one standing out. Andhrua accounts for 44.7% of spending (Rs 1.49 crore) and holds 37.5% of the activities; Barimunda accounts for 32.3% (Rs 1.08 crore), and Itipur for Rs 76.58 lakh. Andhrua accounts for 38.9% of the amount below plan (Rs 1.02 crore), Itipur for 34.7% (Rs 90.99 lakh), and Barimunda for Rs 69.45 lakh; Andhrua’s ratio is 59.3%. Planned cost is split between Andhrua at 42.1% (Rs 2.51 crore), Barimunda at 29.7% (Rs 1.77 crore), and Itipur at Rs 1.68 crore; Andhrua holds 37.5% of the activities. Of spending linked to planned activities, Andhrua accounts for 45.5% (Rs 1.49 crore), Barimunda for 31.4% (Rs 1.02 crore), and Itipur for Rs 75.26 lakh; Andhrua holds 41.4% of the 2,135 vouchers. 

The linked-spending findings note that a rise in this measure reflects greater recording completeness unless the cashbook total also rises; in both district breakdowns, the linked share went from 2.7% to 53.2% across six years.

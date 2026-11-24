# Writer test: sheet

Run 2026-11-24T19:50:06 on the held judge picks (held 2026-11-24T19:43:47).

| | |
|---|---|
| Writer model | gpt-6.2-sol |
| Prompt | the live prompt (context_brief.py) |
| Every finding must be mentioned | on |
| Questions | 63 |
| Answers kept | 59 |
| Answers lost (plain sentences shown instead) | 4 (4 on 2_numerals_cited) |
| Passed on the first try | 3 |
| Writer calls | 123 |
| Seconds per answer, middle | 19.8 |
| Findings used, of those handed (middle) | 8 of 8 |
| Words per answer, middle | 254 |
| Words per answer, most | 334 |
| Sentences per answer, middle | 13 |
| Words per sentence, middle | 19.7 |
| Sentences over 25 words | 22% |
| Figures per answer, middle | 28 |
| Figures per sentence, middle | 2.1 |
| Sentences with more than 2 figures | 39% |
| Share of the handed figures that appear, middle | 30% |

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

### GEO-06 (run 1) - How is Biswamathpur performing on spending?

- used 8 of 8 findings, 246 words, 12 sentences, 20.5 words per sentence, 30 figures, 32% of the handed figures, 2 tries
- place facts used (10 of 61): A5, A3, A6, A7, A2, A4, B, G1, G3, E5

Biswamathpur spent Rs 1.42 crore on planned activities, the 6th highest amount in the 20-Gram-Panchayat sample. But its recorded plan was Rs 8.65 crore, the highest in the sample, and spending reached just 16.4% of that amount—the lowest share in the sample, against a middle value of 42.0%. Spending was Rs 7.23 crore below plan, and 296 activities (54.8%) had no cost recorded. For activities with a sanction on file, Rs 1.84 crore was sanctioned and spending was Rs 42.13 lakh below sanction.

Recorded spending was spread across the years, but 2023-2024 alone accounted for 68.6% of the gap against plan: Rs 4.96 crore below plan, with only 4.0% of that year’s planned cost spent. Public Works accounted for 99.9% of the gap and 100.0% of voucher-linked spending. Across focus areas, the largest gaps were in sanitation (Rs 2.10 crore below plan) and women and child development (Rs 1.04 crore below plan).

At the next review, start by reconciling the 2023-2024 Public Works plans with sanctions and payment records. Activities with no scheme recorded accounted for Rs 6.81 crore of the gap against plan (94.2%). The cashbook shows Rs 4.39 crore paid out, with 32.3% of payments linked to a planned activity. The linked share rose from 2.7% to 53.2% over the period, but that does not by itself show that spending rose. Also verify the status of 46 older works still marked ongoing: they show Rs 80.61 lakh spent against Rs 84.81 lakh planned (95.1%).

### GEO-06 (run 2) - How is Biswamathpur performing on spending?

- used 8 of 8 findings, 250 words, 14 sentences, 17.9 words per sentence, 28 figures, 30% of the handed figures, 2 tries
- place facts used (11 of 61): A5, A3, A6, A7, A4, B, G1, G3, A2, E5, E2

Biswamathpur spent Rs 1.42 crore on planned activities, the 6th highest amount in the 20-Gram-Panchayat sample. But it had the largest recorded plan, at Rs 8.65 crore, and spent only 16.4% of that amount, the lowest share in the sample. Spending was Rs 7.23 crore below plan. For activities with a sanction on file, Rs 1.84 crore was sanctioned, and spending was Rs 42.13 lakh below sanction, with that gap spread across fiscal years.

Spending itself was spread across the 6 fiscal years, but 2023-2024 accounted for 68.6% of the gap against plan (Rs 4.96 crore). In that year, Biswamathpur spent Rs 20.69 lakh against Rs 5.16 crore planned, or 4.0%. Public works accounted for all voucher-linked spending and 99.9% of the gap against plan. Across focus areas, the largest gaps were in sanitation (Rs 2.10 crore) and women and child development (Rs 1.04 crore).

At the next review, reconcile cashbook payments with activity and scheme records. The cashbook shows Rs 4.39 crore paid out, but only 32.3% of payments are linked to planned activities. The linked share rose from 2.7% to 53.2% across the period; that does not by itself show that total payments rose. Activities with no scheme recorded account for 94.2% of the gap against plan, and 296 planned activities (54.8%) have no cost attached.

Also verify the status of the 46 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 95.1% of their planned cost. No works are marked completed.

### GEO-06 (run 3) - How is Biswamathpur performing on spending?

- used 8 of 8 findings, 257 words, 11 sentences, 23.4 words per sentence, 25 figures, 28% of the handed figures, 2 tries
- place facts used (8 of 61): A5, A6, A3, A7, A4, G1, G3, E5

Biswamathpur spent Rs 1.42 crore on planned activities, the 6th highest of the 20 Gram Panchayats sampled, but spent only 16.4% of its planned cost—the lowest share in the sample, against a middle value of 42.0%. Its planned cost of Rs 8.65 crore was the highest in the sample, and recorded spending was Rs 7.23 crore below plan. Against the Rs 1.84 crore sanctioned for activities with approval on file, spending was Rs 42.13 lakh below sanction; that comparison covers only activities with a sanction on file. 

Spending was spread across the years, but the gap against plan was concentrated in 2023-2024, which accounted for 68.6% of the gap (Rs 4.96 crore below plan). Public Works accounted for all voucher-linked spending (Rs 1.42 crore) and 99.9% of the gap against plan. The gap was spread across several focus areas, with the largest amounts in sanitation (Rs 2.10 crore below plan) and women and child development (Rs 1.04 crore below plan). 

At the next review, prioritise reconciling Public Works plans with sanctions and payments, starting with 2023-2024. Activities with no scheme recorded account for 94.2% of the gap against plan. The cashbook shows Rs 4.39 crore paid out, but only 32.3% of payments are linked to a planned activity. The linked share rose from 2.7% to 53.2%; that shows more payments were linked in the records, not necessarily that spending rose. Also check the status of the 46 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 95.1% of their planned cost.

### GEO-07 (run 1) - What stands out in Boipariguda?

- used 8 of 8 findings, 242 words, 15 sentences, 16.1 words per sentence, 26 figures, 30% of the handed figures, 2 tries
- place facts used (10 of 58): I4, A3, A5, A6, A1, A2, B, C, E5, E2

Boipariguda block is represented by one Gram Panchayat in the sample. It spent Rs 1.41 crore against a plan of Rs 6.15 crore. At 22.8% of planned cost, its spending rate was the 3rd lowest of 16 blocks in the sample, against a middle value of 36.6%. Of its 647 planned activities, 248 (38.3%) had no cost attached.

The first records to review are from 2023-2024: that year accounted for 64.7% of planned cost but 79.7% of the overall spending gap. Only 5.0% of that year’s planned cost was spent. Across all years, rural housing had the largest gap, with Rs 2.13 crore planned and nothing spent; drinking water was next, at Rs 1.26 crore below plan.

Two record checks stand out. First, 64 works planned in 2022-2023 or earlier are still marked ongoing, with 89.1% of their planned cost spent, and no works in the block are marked completed. Check whether those statuses are current. Second, check theme assignments: activities without a mapped theme account for 39.5% of planned cost and 32.6% of expected beneficiaries.

When reconciling spending records, keep the measures separate. Public works account for all Rs 1.62 crore recorded under general-component spending, with maintenance at 46.6% and new works at 35.1%. Separately, spending linked to planned activities totalled Rs 1.18 crore, and the linked share went from 2.7% to 53.2% across the six years. Check that change against cashbook totals before interpreting it as a rise in spending.

### GEO-07 (run 2) - What stands out in Boipariguda?

- used 8 of 8 findings, 283 words, 15 sentences, 18.9 words per sentence, 29 figures, 29% of the handed figures, 2 tries
- place facts used (14 of 58): A3, A5, A6, A1, A2, I4, J, B, C, C, E2, E5, G1, G3

Boipariguda stands out for a high planned budget and a low share spent. Its Rs 6.15 crore planned cost was the 5th highest of 16 blocks in the sample, but recorded spending of Rs 1.41 crore was only 22.8% of plan, the 3rd lowest share. Of 647 planned activities, 248 (38.3%) had no cost attached. The block figures cover only Boipariguda Gram Panchayat in this sample.

Start the spending review with 2023-2024: it accounted for 64.7% of the planned cost and 79.7% of the Rs 4.75 crore gap between plan and spending. Just 5.0% of that year’s plan was spent. Across all years, rural housing and drinking water had the largest gaps: rural housing had Rs 2.13 crore planned and no recorded spending, while drinking water had Rs 1.65 crore planned and Rs 39.14 lakh spent.

Check work status alongside the spending records. No works are marked complete, and 64 works planned in 2022-2023 or earlier are still marked ongoing even though 89.1% of their planned cost has been spent. The cashbook shows Rs 1.85 crore paid out, with 75.8% of payments linked to a planned activity. When reconciling the records year by year, check the cashbook totals as well as the links: the recorded linked share rose from 2.7% to 53.2% across the six years, which does not by itself show that spending rose.

Two classifications also merit a check. Activities without a mapped development theme account for 39.5% of planned cost and 32.6% of expected beneficiaries. In the separate general-component spending figures, all Rs 1.62 crore is recorded under public works, with none under beneficiary-oriented programmes. Maintenance was the largest work category in that spending measure, at Rs 75.45 lakh (46.6%).

### GEO-07 (run 3) - What stands out in Boipariguda?

- used 8 of 8 findings, 252 words, 13 sentences, 19.4 words per sentence, 27 figures, 32% of the handed figures, 2 tries
- place facts used (9 of 58): A3, A6, I4, J, B, C, E2, E5, A2

Boipariguda stands out for a high planned cost and low spending against plan. The sample covers one Gram Panchayat in the block. It recorded Rs 1.41 crore in spending against Rs 6.15 crore planned. That is 22.8% of plan, the 3rd lowest of 16 blocks in the sample, against a middle value of 36.6%. 

The first place to look is 2023-2024: it accounted for 64.7% of planned cost and 79.7% of the Rs 4.75 crore gap between plan and spending. Only 5.0% of that year’s planned cost was spent. Across all years, rural housing had the largest gap, with Rs 2.13 crore planned and no spending recorded; drinking water was next, at Rs 1.26 crore below plan. 

The next review should check work status and reconcile payment records. No works are marked completed, and 64 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 89.1% of their planned cost. Spending linked to planned activities totalled Rs 1.18 crore in the payment-linkage analysis; the linked share went from 2.7% to 53.2%, which does not by itself show that overall spending rose. Separately, all Rs 1.62 crore recorded under the general spending component was for public works, with maintenance the largest work type at Rs 75.45 lakh. 

Planning records also need attention: 248 activities (38.3%) have no cost attached. Activities without a mapped village development theme account for 39.5% of planned cost (Rs 2.43 crore) and 32.6% of expected beneficiaries (1,260 people), making theme mapping a priority for review.

### GEO-12 (run 1) - What does the analysis say about Haldikudar?

- used 8 of 8 findings, 299 words, 15 sentences, 19.9 words per sentence, 34 figures, 39% of the handed figures, 2 tries
- place facts used (9 of 62): A1, A2, A3, A5, A6, F1, E2, E5, E4

Haldikudar listed 582 planned activities, of which 356 (61.2%) had no cost recorded. Its recorded plan of Rs 1.66 crore was the lowest in the 20-Gram-Panchayat sample, and spending of Rs 75.12 lakh was the second lowest. Even so, spending was 45.3% of the recorded plan, above the sample median of 42.0%.

Sanitation and drinking water had the largest gaps between planned cost and spending: Rs 28.32 lakh and Rs 25.12 lakh, respectively, out of an overall gap of Rs 90.62 lakh. They also had the largest gaps against sanctions on file: Rs 9.19 lakh for sanitation and Rs 7.47 lakh for drinking water. By asset category, Water Sources & Structures had the largest gap against plan, at Rs 21.81 lakh. Roads had the largest share of the Rs 1.04 crore planned from untied grants, at 23.4% (Rs 24.42 lakh), followed by sanitation at 17.4% (Rs 18.17 lakh). Of the Rs 99.95 lakh sanctioned on file, the largest amounts were for Self-sufficient Infrastructure in Village (Rs 38.88 lakh) and Clean and Green Village (Rs 24.64 lakh).

Missing records limit what can be concluded about funding and approvals. No fund component was recorded for 488 activities (83.8%); those activities accounted for Rs 65.78 lakh (72.6%) of the gap against plan. The entire recorded expected-beneficiary total of 10,455 people was attached to activities with no scheme recorded. Administrative approval was on file for 94 activities (16.2%); a missing record does not establish that an activity lacked approval.

At the next review, prioritise checking work status against expenditure and available evidence. No works were marked completed, while 57 works planned in 2022-2023 or earlier were still marked ongoing, with Rs 40.99 lakh spent against Rs 56.42 lakh planned. Photo evidence was on file for 53 activities, the third fewest in the sample.

### GEO-12 (run 2) - What does the analysis say about Haldikudar?

- used 8 of 8 findings, 303 words, 15 sentences, 20.2 words per sentence, 33 figures, 37% of the handed figures, 2 tries
- place facts used (9 of 62): A1, A2, A3, A5, A6, E2, E5, F1, E4

Haldikudar planned 582 activities, close to the middle of the 20-Gram-Panchayat sample, but 356 (61.2%) had no cost attached. Its recorded planned cost of Rs 1.66 crore was the lowest in the sample, and its spending of Rs 75.12 lakh was the second lowest. Even so, spending was 45.3% of recorded planned cost, above the sample’s middle value of 42.0%.

Sanitation and drinking water had the largest gaps against both plan and sanction. Of the Rs 90.62 lakh gap against plan, sanitation accounted for Rs 28.32 lakh and drinking water for Rs 25.12 lakh. Viewed by asset type rather than service area, Water Sources & Structures had the largest gap, at Rs 21.81 lakh. Among activities with a sanction on file, spending was Rs 24.83 lakh below sanction, with gaps of Rs 9.19 lakh in sanitation and Rs 7.47 lakh in drinking water. The largest shares of the Rs 99.95 lakh sanctioned were for Self-sufficient Infrastructure in Village (Rs 38.88 lakh) and Clean and Green Village (Rs 24.64 lakh). Within the Rs 1.04 crore untied-grant plan, roads had the largest allocation (Rs 24.42 lakh), followed by sanitation (Rs 18.17 lakh).

The next review should reconcile funding records and verify the status of older works. No fund component was recorded for 488 activities (83.8%); those activities accounted for Rs 65.78 lakh (72.6%) of the gap against plan. The entire recorded expected beneficiary count of 10,455 was attached to activities with no scheme listed. Administrative approvals were on file for 94 activities (16.2%); a missing record does not establish that an activity lacked approval. No works were marked complete, and 57 planned in 2022-2023 or earlier were still marked ongoing, with Rs 40.99 lakh spent against a planned Rs 56.42 lakh. Photo evidence was on file for 53 activities, the third fewest in the sample.

### GEO-12 (run 3) - What does the analysis say about Haldikudar?

- used 8 of 8 findings, 261 words, 12 sentences, 21.8 words per sentence, 29 figures, 32% of the handed figures, 2 tries
- place facts used (8 of 62): A1, A2, A3, A5, A6, F1, E2, E5

Haldikudar recorded 582 planned activities, of which 356 (61.2%) had no cost attached. Its recorded plan cost of Rs 1.66 crore was the lowest in the 20-Gram-Panchayat sample, and its spending of Rs 75.12 lakh was the second lowest. Even so, it spent 45.3% of its recorded plan cost, above the sample’s middle value of 42.0%.

Sanitation and drinking water had the largest gaps against both plan and sanction: sanitation was Rs 28.32 lakh below plan and drinking water Rs 25.12 lakh below plan; against sanction, the gaps were Rs 9.19 lakh and Rs 7.47 lakh, respectively. Water Sources & Structures had the largest gap among asset categories, at Rs 21.81 lakh below plan. Roads had the largest share of planned untied grants, at 23.4% (Rs 24.42 lakh). Of the Rs 99.95 lakh sanctioned on file, the largest share went to the Self-sufficient Infrastructure in Village theme, at 38.9% (Rs 38.88 lakh).

At the next review, reconcile funding and approval records before drawing conclusions about the spending gap. No fund component was recorded for 488 activities (83.8%), and these activities accounted for Rs 65.78 lakh of the Rs 90.62 lakh gap against plan. The entire recorded expected-beneficiary total of 10,455 people was attached to activities with no scheme listed. Administrative approvals were on file for 94 activities (16.2%); a missing record does not establish that approval was absent.

Also verify the status of older works: none are marked completed, and 57 works planned in 2022-2023 or earlier are still marked ongoing, with Rs 40.99 lakh spent against Rs 56.42 lakh planned.

### GEO-18 (run 1) - Is Laxmipur behind on anything?

- used 6 of 6 findings, 241 words, 14 sentences, 17.2 words per sentence, 22 figures, 25% of the handed figures, 2 tries
- place facts used (8 of 62): A5, A3, A7, A6, E2, E5, A2, F1

Yes. Laxmipur is behind its own spending plan, even though it compares relatively well with other blocks in the sample. It spent Rs 1.75 crore against a planned Rs 3.36 crore, leaving a gap of Rs 1.61 crore. Spending was 52.1% of plan, the 3rd highest of 16 blocks in the sample. The largest annual gaps were in 2025-2026 (Rs 65.79 lakh below plan) and 2023-2024 (Rs 61.40 lakh below plan).

Drinking water is a priority for review: it had the largest gap among focus areas (Rs 48.04 lakh below plan), followed by sanitation (Rs 44.29 lakh below plan). The same records, grouped differently, show the largest gaps under Water Sufficient Village among themes (Rs 51.55 lakh) and drinking water supply structures among asset categories (Rs 34.96 lakh). These are overlapping views of the same spending gap, not additional shortfalls. Among activities with a sanction on file, drinking water accounted for Rs 9.93 lakh of the Rs 15.98 lakh gap against sanctions.

At the next review, check work status and reconcile the planning and approval records. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing even though 91.0% of their planned cost has been spent. Of the planned activities, 447 (55.3%) have no cost attached. Activities with no sanctioning authority on file account for Rs 1.45 crore of the gap against plan. A missing record does not establish that approval was never given.

### GEO-18 (run 2) - Is Laxmipur behind on anything?

- used 6 of 6 findings, 254 words, 10 sentences, 25.4 words per sentence, 23 figures, 25% of the handed figures, 2 tries
- place facts used (11 of 62): A3, A5, A7, A1, A2, A6, B, B, E2, E5, F1

Laxmipur is behind its recorded spending plan, but not behind most blocks in the sample on that measure. It spent Rs 1.75 crore against a recorded plan of Rs 3.36 crore, leaving a gap of Rs 1.61 crore. Spending reached 52.1% of planned cost, the 3rd highest of 16 blocks in the sample, but 447 of its 808 planned activities (55.3%) had no cost attached. 

Start the spending review with 2025-2026, when spending reached 24.0% of plan and was Rs 65.79 lakh below it, and 2023-2024, when it reached 33.4% and was Rs 61.40 lakh below plan. The gap spans several areas, but drinking water (Rs 48.04 lakh below plan) and sanitation (Rs 44.29 lakh below plan) are the largest by focus area. The same gap, viewed by theme, is largest in Water Sufficient Village and Self-sufficient Infrastructure in Village; by asset type, it is largest in drinking water supply structures and liquid waste management. Drinking water is also the first area to check against sanctions: among activities with a sanction on file, it accounts for Rs 9.93 lakh of the Rs 15.98 lakh gap between sanctions and spending. 

At the next review, verify work status and reconcile the approval records. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 91.0% of their planned cost. Activities with no sanctioning authority recorded account for Rs 1.45 crore of the gap against plan; a missing entry does not establish that approval was never given.

### GEO-18 (run 3) - Is Laxmipur behind on anything?

- used 6 of 6 findings, 247 words, 14 sentences, 17.6 words per sentence, 22 figures, 23% of the handed figures, 2 tries
- place facts used (9 of 62): A7, A5, I4, A3, A6, A2, F1, E2, E5

Yes. Laxmipur is behind its own spending plan, but it is not among the lowest-spending blocks in the sample. The records cover 1 Gram Panchayat in the block. It spent Rs 1.75 crore against a recorded plan of Rs 3.36 crore, leaving a gap of Rs 1.61 crore. Even so, spending reached 52.1% of planned cost, the 3rd highest of 16 blocks in the sample. That comparison is against recorded costs: 447 activities (55.3%) have no cost attached. 

The largest gaps were in 2025-2026, at Rs 65.79 lakh below plan, and 2023-2024, at Rs 61.40 lakh below plan. Drinking water and sanitation had the largest gaps by focus area, at Rs 48.04 lakh and Rs 44.29 lakh respectively. The same overall gap, viewed by village development theme, was largest for Water Sufficient Village and Self-sufficient Infrastructure in Village; by asset type, it was largest for drinking water supply structures and liquid waste management. Drinking water also accounted for 62.1% of the gap against sanctions, or Rs 9.93 lakh, among activities with a sanction on file. 

At the next review, reconcile the sanction and work-status records. Activities with no sanctioning authority recorded account for 90.1% of the gap against plan (Rs 1.45 crore); a missing record does not establish that approval was absent. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 91.0% of their planned cost. Verify their actual status before treating them as unfinished.

### GEO-19 (run 1) - Mendarajpur - show me what the analysis found.

- used 8 of 8 findings, 283 words, 14 sentences, 20.2 words per sentence, 33 figures, 36% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (10 of 61): A1, A2, A3, A5, A6, F1, C, G3, E2, E5

Mendarajpur Gram Panchayat recorded 623 planned activities, of which 421 (67.6%) had no cost attached. It spent Rs 1.32 crore against a recorded plan of Rs 3.19 crore, or 41.2% of plan, close to the 42.0% middle value in the 20-Gram-Panchayat sample. 

Of the Rs 1.88 crore gap between plan and spending, Rs 1.47 crore (78.5%) was on activities with no sanctioning authority recorded; that does not establish that the activities lacked approval. In a separate breakdown of the same gap, activities recorded under output code 101 accounted for Rs 1.58 crore (84.0%). The largest annual gaps were in 2025-2026 (Rs 74.56 lakh) and 2023-2024 (Rs 62.24 lakh). Across sectors, water conservation had the largest gap, with Rs 40.75 lakh planned and no spending recorded, followed by women and child development at Rs 30.86 lakh below plan. 

Where sanctions were on file, recorded spending was Rs 40.44 lakh below sanction. Sanitation (Rs 9.04 lakh) and drinking water (Rs 8.88 lakh) had the largest gaps on that basis. These were also the main uses planned for tied grants: Rs 28.87 lakh for sanitation and Rs 30.27 lakh for drinking water. For untied grants, the largest planned allocations were for self-sufficient village infrastructure (Rs 1.04 crore) and water-sufficient villages (Rs 58.37 lakh). 

At the next review, reconcile cashbook payments with planned activities and verify the status of older works. Only 38.3% of cashbook payments were linked to a planned activity. The linked share rose from 2.7% to 53.2% across the six years; that change alone does not show that spending rose. No works were marked complete, and 66 works planned in 2022-2023 or earlier were still marked ongoing, with 83.0% of their planned cost spent.

What the officer sees instead:

```
Mendarajpur Gram Panchayat
- Mendarajpur Gram Panchayat has 623 planned activities, the 10th most of 20 Gram Panchayats. The middle value for these 20 is 602.5.
- 421 of them (67.6%) have no cost attached.
- Its planned cost is Rs 3.19 crore, the 10th highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
- It spent Rs 1.32 crore on planned activities, the 10th highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
- Spending is 41.2% of the planned cost, the 9th lowest of 20 Gram Panchayats. The middle value is 42.0%.
- 139 of the 623 activities (22.3%) have an administrative approval on file, the 4th most of 20 Gram Panchayats. The middle value is 96.
   (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
- Water Conservation: 8 activities and Rs 40.75 lakh planned, with nothing spent.
- 38.3% of the payments are linked to a planned activity, the 10th lowest of 20 Gram Panchayats. The middle value is 42.2%.
- No works are marked completed.
- 66 works planned in 2022-2023 or earlier are still marked ongoing. Rs 88.40 lakh of their Rs 1.07 crore planned cost has been spent (83.0%).

- Within Gram Panchayat Mendarajpur, spending measured against plan totals Rs 1.88 crore below plan across 6 sanctioning authority values. It is concentrated: (not recorded) accounts for 78.5% of it (Rs 1.47 crore below plan). The remaining 5 together account for Rs 40.44 lakh below plan. 484 rows carry no sanctioning authority on file; they are counted here as (not recorded) and account for Rs 1.47 crore below plan.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, spending measured against plan totals Rs 1.88 crore below plan across 7 output type values. It is concentrated: Code 101 accounts for 84.0% of it (Rs 1.58 crore below plan). The remaining 6 together account for Rs 30.03 lakh below plan. For size: Code 101 holds 23.9% of the 623 activities behind these totals, against 84.0% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Code 101 is 40.0%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, spending measured against plan totals Rs 1.88 crore below plan across 6 fiscal years. It is spread across them without one standing out: the largest is 2025-2026 at 39.7% (Rs 74.56 lakh below plan), then 2023-2024 at 33.1% (Rs 62.24 lakh below plan). The remaining 4 together account for Rs 51.09 lakh below plan. For size: 2025-2026 holds 18.5% of the 623 activities behind these totals, against 39.7% of spending measured against plan -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, spending linked to a planned activity totals Rs 1.23 crore across 6 fiscal years. It is spread across them without one standing out: the largest is 2025-2026 at 28.0% (Rs 34.33 lakh), then 2021-2022 at 25.2% (Rs 31.00 lakh). The remaining 4 together account for Rs 57.48 lakh. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, spending measured against plan totals Rs 1.88 crore below plan across 22 focus area values. It is spread across them without one standing out: the largest is Water Conservation at 21.7% (Rs 40.75 lakh below plan), then Women and child development at 16.4% (Rs 30.86 lakh below plan). The remaining 20 together account for Rs 1.16 crore below plan. For size: Water Conservation holds 1.3% of the 623 activities behind these totals, against 21.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Water Conservation is 0.0%.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, spending measured against sanction totals Rs 40.44 lakh below sanction across 22 focus area values. It is spread across them without one standing out: the largest is Sanitation at 22.4% (Rs 9.04 lakh below sanction), then Drinking water at 21.9% (Rs 8.88 lakh below sanction). The remaining 20 together account for Rs 22.52 lakh below sanction. For size: Sanitation holds 10.1% of the 623 activities behind these totals, against 22.4% of spending measured against sanction -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sanitation is 69.4%. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, tied grant planned totals Rs 59.89 lakh across 22 focus area values. It is spread across them without one standing out: the largest is Drinking water at 50.5% (Rs 30.27 lakh), then Sanitation at 48.2% (Rs 28.87 lakh). The remaining 20 together account for Rs 75,000. For size: Drinking water holds 6.6% of the 623 activities behind these totals, against 50.5% of tied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

- Within Gram Panchayat Mendarajpur, untied grant planned totals Rs 2.60 crore across 7 LSDG theme values. It is spread across them without one standing out: the largest is Theme 6 - Self-sufficient Infrastructure in Village at 39.9% (Rs 1.04 crore), then Theme 4 - Water Sufficient Village at 22.5% (Rs 58.37 lakh). The remaining 5 together account for Rs 97.56 lakh. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 42.2% of the 623 activities behind these totals, against 39.9% of untied grant planned -- a group's total grows with how much of the work it holds.
   (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)

(as of 2026-09-11)
```

### GEO-19 (run 2) - Mendarajpur - show me what the analysis found.

- used 8 of 8 findings, 334 words, 15 sentences, 22.3 words per sentence, 39 figures, 40% of the handed figures, 2 tries
- place facts used (12 of 61): A1, A3, A2, A5, A6, A7, C, F1, E2, E5, E4, G3

Mendarajpur planned 623 activities at a recorded cost of Rs 3.19 crore, both 10th among the 20 Gram Panchayats in the sample. Of those activities, 421 (67.6%) had no cost attached. Spending on planned activities was Rs 1.32 crore, or 41.2% of recorded planned cost, close to the sample middle value of 42.0%. 

**Where spending fell short of plan.** Spending was Rs 1.88 crore below plan. The largest annual gaps were in 2025-2026 (Rs 74.56 lakh) and 2023-2024 (Rs 62.24 lakh). By sector, the largest gaps were in water conservation, with Rs 40.75 lakh planned and no spending recorded, and women and child development, at Rs 30.86 lakh below plan. The same overall gap was concentrated in activities classified as output Code 101, which accounted for 84.0% of the gap but 23.9% of activities. Viewed by sanctioning authority, 78.5% of the gap was on 484 activities with no authority recorded; a missing entry does not establish that approval was absent. 

**Grant plans and sanctions.** Of the Rs 59.89 lakh in planned tied grants, Rs 30.27 lakh was for drinking water and Rs 28.87 lakh for sanitation. Of the Rs 2.60 crore in planned untied grants, the largest allocations were for self-sufficient village infrastructure (Rs 1.04 crore) and the Water Sufficient Village theme (Rs 58.37 lakh). For activities with sanctions on file, spending was Rs 40.44 lakh below sanction; the largest sector gaps were in sanitation (Rs 9.04 lakh) and drinking water (Rs 8.88 lakh). 

**Records to reconcile at the next review.** No works were marked completed, and 66 works planned in 2022-2023 or earlier were still marked ongoing, with Rs 88.40 lakh spent against Rs 1.07 crore planned (83.0%). Check those older status entries against completion records and any available photos; the GP has photo evidence for 107 activities. Separately, only 38.3% of cashbook payments were linked to a planned activity. The annual linked share rose from 2.7% to 53.2% over the period, but that change alone does not show that cashbook spending rose.

### GEO-19 (run 3) - Mendarajpur - show me what the analysis found.

- used 8 of 8 findings, 306 words, 14 sentences, 21.9 words per sentence, 37 figures, 41% of the handed figures, 2 tries
- place facts used (8 of 61): A1, A2, A3, A5, A6, E5, E2, E4

Mendarajpur recorded 623 planned activities, of which 421 (67.6%) had no cost attached. Against a recorded plan of Rs 3.19 crore, it spent Rs 1.32 crore on planned activities. That was 41.2% of planned cost, close to the middle value of 42.0% in the 20-Gram-Panchayat sample.

Of the Rs 1.88 crore gap between plan and spending, Rs 1.47 crore (78.5%) was on activities with no sanctioning authority recorded. In a separate breakdown of the same gap, activities recorded under output Code 101 accounted for Rs 1.58 crore (84.0%). The largest annual gaps were in 2025-2026 (Rs 74.56 lakh) and 2023-2024 (Rs 62.24 lakh). Across sectors, the largest gaps against plan were in water conservation (Rs 40.75 lakh) and women and child development (Rs 30.86 lakh). Among activities with sanctions on file, spending was Rs 40.44 lakh below sanction, with the largest gaps in sanitation (Rs 9.04 lakh) and drinking water (Rs 8.88 lakh).

The grant plans show a different split: nearly all of the Rs 59.89 lakh in planned tied grants was for drinking water (Rs 30.27 lakh) and sanitation (Rs 28.87 lakh). Of the Rs 2.60 crore in planned untied grants, the largest allocations were for village infrastructure (Rs 1.04 crore) and the Water Sufficient Village theme (Rs 58.37 lakh).

At the next review, reconcile cashbook payments with activity records and check the status of older works. Cashbook payments linked to planned activities totalled Rs 1.23 crore; the linked share rose from 2.7% to 53.2% across the six years, which does not by itself show that spending rose. No works were marked completed, and 66 works planned in 2022-2023 or earlier were still marked ongoing despite recorded spending of Rs 88.40 lakh (83.0% of their planned cost). Photo evidence is on file for 107 activities and can be checked against the work records where available.

### GEO-20 (run 1) - Anything notable about Sharagada?

- used 8 of 8 findings, 250 words, 13 sentences, 19.2 words per sentence, 30 figures, 37% of the handed figures, 2 tries
- place facts used (10 of 61): A1, A2, A3, A4, A5, A6, A7, E2, E5, G3

Sharagada has the most planned activities in the 20-Gram-Panchayat sample: 920, of which 722 (78.5%) have no cost recorded. Its planned cost was Rs 6.51 crore, the fourth highest in the sample. It had the highest sanctioned amount on file, Rs 2.74 crore, and the highest spending on planned activities, Rs 1.88 crore. Even so, spending was 28.9% of plan, against a sample median of 42.0%.

The Rs 4.63 crore gap between plan and spending is concentrated in village infrastructure, which accounts for Rs 3.36 crore of the gap (72.6%). Looking at the same gap by year, 2020-2021 accounts for Rs 2.54 crore (54.9%). Maintenance accounts for Rs 4.25 crore (85.0%) of the untied grant plan, while Rs 3.77 crore of the overall plan (57.9%) has no scheme recorded.

A priority for the next review is to verify the status of older works. No works are marked completed, and 36 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 95.6% of their planned cost. Works marked ongoing also account for 72.7% of recorded spending under the general component. Of the 80 activities with photo evidence, 35 are in village infrastructure and 26 are under the Clean and Green Village theme.

Payment links are another point to check: 29.7% of payments are linked to a planned activity, against a sample median of 42.2%. The linked share rose from 2.7% to 53.2% over the period reviewed; that rise does not, by itself, show that cashbook spending increased.

### GEO-20 (run 2) - Anything notable about Sharagada?

- used 8 of 8 findings, 223 words, 12 sentences, 18.6 words per sentence, 24 figures, 30% of the handed figures, 2 tries
- place facts used (8 of 61): A1, A2, A4, A5, A6, A7, E2, E5

Sharagada recorded 920 planned activities, the most in the 20-Gram-Panchayat sample, but 722 (78.5%) had no cost attached. It also had the sample’s highest sanctioned amount, Rs 2.74 crore, and the highest spending on planned activities, Rs 1.88 crore. Even so, spending was just 28.9% of planned cost, against a sample midpoint of 42.0%.

Spending was Rs 4.63 crore below plan. The gap was concentrated in village infrastructure, which accounted for Rs 3.36 crore of it. Looking at the same gap by year, 2020-2021 accounted for Rs 2.54 crore. Two planning records are worth checking: Rs 3.77 crore of planned cost had no scheme on file, and maintenance accounted for Rs 4.25 crore (85.0%) of the planned untied grant.

At the next review, verify work status against payments and available photos. No works were marked complete, and 36 works planned in 2022-2023 or earlier were still marked ongoing despite recorded spending of 95.6% of their planned cost. Works marked ongoing accounted for 72.7% of spending under the general component. Of the 80 activities with photo evidence, 35 were in village infrastructure and 26 in the Clean and Green Village theme. The share of cashbook spending linked to planned activities rose from 2.7% to 53.2% over the period reviewed; that shows more spending was linked in the records, not necessarily that overall spending rose.

### GEO-20 (run 3) - Anything notable about Sharagada?

- used 8 of 8 findings, 282 words, 15 sentences, 18.8 words per sentence, 31 figures, 37% of the handed figures, 2 tries
- place facts used (13 of 61): A1, A2, A4, A5, A6, A3, A7, E2, E5, E3, E4, F1, G3

Sharagada had the most planned activities in the 20-Gram-Panchayat sample, at 920, but 722 activities (78.5%) had no cost recorded. It had the highest sanctioned amount (Rs 2.74 crore) and the highest spending on planned activities (Rs 1.88 crore). Even so, it spent only 28.9% of its planned cost of Rs 6.51 crore, leaving spending Rs 4.63 crore below plan.

Village infrastructure is the clearest place to start reviewing that gap: it accounts for Rs 3.36 crore (72.6%) of the amount below plan. Looking at the same gap by year, 2020-2021 accounts for Rs 2.54 crore (54.9%). Two planning details are also worth checking: Rs 3.77 crore in planned costs had no scheme recorded, and maintenance accounted for Rs 4.25 crore (85.0%) of planned untied grants.

Work status is another priority for reconciliation. No works are marked complete, and 36 works planned in 2022-2023 or earlier are still marked ongoing even though 95.6% of their planned cost has been spent. Works marked ongoing account for 72.7% of spending recorded under the general component. A further 19 works are marked abandoned, with Rs 1.19 crore planned for them. For the status review, photo evidence is on file for 80 activities, including 35 under village infrastructure and 26 under Clean and Green Village.

The next review should also check the links between plans, approvals and payments. Administrative approvals are on file for 93 activities (10.1%); a missing record does not establish that an activity lacked approval. Only 29.7% of cashbook payments are linked to a planned activity. The share of spending linked to planned activities rose from 2.7% to 53.2% over the period, but that change alone does not show that total spending rose.

### GEO-22 (run 1) - What has been found in Attabira block?

- used 8 of 8 findings, 247 words, 16 sentences, 15.4 words per sentence, 29 figures, 36% of the handed figures, 2 tries
- place facts used (11 of 63): I4, J, A1, A2, A3, A5, A6, A7, F1, E2, E5

The Attabira records cover one Gram Panchayat, Hirlipali. Of its 777 planned activities, 563 (72.5%) have no cost recorded. Against a recorded plan of Rs 2.46 crore, spending was Rs 1.19 crore, or 48.3% of plan, leaving a gap of Rs 1.27 crore.

The first priority is to reconcile the planning, sanction and payment records. Only 89 activities (11.5%) have an administrative approval on file; a missing record does not establish that approval was never granted. No scheme is recorded for 688 activities (88.5%). Activities with no sanctioning authority recorded account for Rs 1.17 crore of the spending gap (91.8%). Separately, payments linked to planned activities total Rs 1.06 crore across 6 fiscal years. The recorded linked share rose from 2.7% to 53.2%; that change alone does not show that overall spending rose.

The spending gap is spread across sectors and years. Drinking water had the largest gap, at Rs 35.94 lakh, followed by sanitation at Rs 23.84 lakh. The largest annual gap was in 2023-2024, at Rs 47.21 lakh.

Work status is the other priority for review. No works are marked completed, and 52 works planned in 2022-2023 or earlier are still marked ongoing, although 90.5% of their planned cost has been spent. Of the 29 works marked abandoned, 16 were planned in 2022-2023. Two cases stand out in the sample: Attabira accounts for Rs 10.30 lakh (91.2%) of the planned cost of abandoned markets and fairs works and has the only agriculture activity marked abandoned.

### GEO-22 (run 2) - What has been found in Attabira block?

- used 8 of 8 findings, 267 words, 13 sentences, 20.5 words per sentence, 31 figures, 36% of the handed figures, 2 tries
- place facts used (12 of 63): I4, J, A1, A2, A3, A4, A5, A7, A6, F1, E2, E5

Attabira is represented in the sample by Hirlipali Gram Panchayat alone. It recorded 777 planned activities, of which 563 (72.5%) had no cost attached. The recorded plan totalled Rs 2.46 crore, with Rs 1.25 crore sanctioned and Rs 1.19 crore spent. Spending was Rs 1.27 crore below plan, although at 48.3% of planned cost it was the 5th highest share among the 16 blocks in the sample. 

The gap between planned and recorded spending was spread across years and sectors. The largest annual gap was in 2023-2024, at Rs 47.21 lakh below plan; drinking water and sanitation had the largest sector gaps, at Rs 35.94 lakh and Rs 23.84 lakh respectively. For reconciliation, start with the 688 activities with no sanctioning authority on file: they account for 91.8% of the recorded gap. There were also 688 activities with no scheme on file, and only 89 activities (11.5%) had an administrative approval on file; a missing approval record does not establish that the activity was unapproved. Payments linked to planned activities totalled Rs 1.06 crore across 6 fiscal years, and the recorded linked share rose from 2.7% to 53.2%; that rise alone does not show that cashbook spending increased. 

Work status is another priority for review. No works are marked completed, and 52 works planned in 2022-2023 or earlier are still marked ongoing, with 90.5% of their planned cost spent. Of the 29 works marked abandoned, 16 were planned in 2022-2023. Attabira accounts for Rs 10.30 lakh (91.2%) of the sample’s planned cost for abandoned markets and fairs works, and it recorded the sample’s only abandoned agriculture activity.

### GEO-22 (run 3) - What has been found in Attabira block?

- used 8 of 8 findings, 253 words, 13 sentences, 19.5 words per sentence, 29 figures, 33% of the handed figures, 2 tries
- place facts used (12 of 63): I4, J, A1, A2, A3, A5, A6, A7, F1, E2, E5, E3

Attabira’s figures cover only Hirlipali Gram Panchayat. Of its 777 planned activities, 563 (72.5%) have no cost attached. Against a recorded plan of Rs 2.46 crore, spending was Rs 1.19 crore, or 48.3% of planned cost, leaving spending Rs 1.27 crore below plan.

The spending gap was spread across years and sectors. The largest annual gap was in 2023-2024, at Rs 47.21 lakh below plan, followed by 2022-2023 at Rs 26.51 lakh below plan. Drinking water and sanitation had the largest sector gaps, at Rs 35.94 lakh and Rs 23.84 lakh below plan, respectively. A priority for reconciliation is the approval and scheme information: 89 activities have an administrative approval on file, 688 have no scheme recorded, and records with no sanctioning authority listed account for Rs 1.17 crore (91.8%) of the spending gap. Missing approval information does not establish that an activity was unapproved. The share of spending linked to planned activities rose from 2.7% to 53.2% across the six fiscal years; that change in recorded linkage does not by itself show that spending rose.

Work status is another priority for review. No works are marked completed, and 52 works planned in 2022-2023 or earlier are still marked ongoing, with Rs 63.37 lakh of their Rs 70.00 lakh planned cost already spent (90.5%). Of the 29 works marked abandoned, 16 were planned in 2022-2023. In the sample, Attabira accounts for Rs 10.30 lakh (91.2%) of the planned cost of abandoned markets and fairs works and for the only agriculture activity marked abandoned.

### GEO-24 (run 1) - Is Lahunipara block an exception to anything?

- used 7 of 7 findings, 168 words, 12 sentences, 14.0 words per sentence, 12 figures, 50% of the handed figures, 1 tries
- place facts used (5 of 59): I4, J, A3, A6, A2

Yes. Lahunipara’s records cover only Haldikudar Gram Panchayat in this sample. Its recorded planned cost was Rs 1.66 crore, the lowest of 16 blocks. Spending was 45.3% of that cost, above the sample’s middle value of 36.6%. Of its planned activities, 356 (61.2%) had no cost attached.

The clearest exception is in the mix of output types. Lahunipara alone departed from the pattern in which Codes 101 and 105 led both in planned cost and in planned use of untied grants. Those codes also led general-component spending in most blocks, but not in Lahunipara. When spending is measured against plan, Lahunipara’s lowest output types were Codes 101 and 104, rather than Codes 101 and 105 as in most blocks.

Lahunipara also departed from the usual pattern by type of work. In most blocks, Maintenance and New/Fresh works led in planned cost and in planned use of untied grants, yet ranked lowest in spending against plan. Lahunipara was an exception on all three measures, though not the only one.

### GEO-24 (run 2) - Is Lahunipara block an exception to anything?

- used 7 of 7 findings, 184 words, 11 sentences, 16.7 words per sentence, 25 figures, 88% of the handed figures, 1 tries
- place facts used (6 of 59): I4, J, A3, A1, A2, A6

Yes. The sample covers only Haldikudar Gram Panchayat in Lahunipara block. Lahunipara has the lowest recorded planned cost of the 16 blocks, at Rs 1.66 crore. Of its 582 planned activities, 356 (61.2%) have no cost attached. Spending is 45.3% of the recorded plan, above the sample’s middle value of 36.6%. 

**The clearest exception is by output type.** Lahunipara is the only block where Codes 101 and 105 do not lead in overall planned cost or in planned untied-grant funding; they lead on both measures in 15/16 blocks. The pair leads in general-component spending in 14/16 blocks, but not in Lahunipara. When spending is measured against plan, Codes 101 and 104 are lowest in Lahunipara, rather than Codes 101 and 105, which are lowest in 14/16 blocks. 

**Lahunipara also differs by type of work, but is not alone.** Maintenance and New/Fresh lead in overall planned cost in 14/16 blocks and in planned untied-grant funding in 13/16 blocks. They also have the lowest spending relative to plan in 14/16 blocks. Lahunipara and Balisankara depart from all three patterns; Khallikote also departs from the untied-grant pattern.

### GEO-24 (run 3) - Is Lahunipara block an exception to anything?

- used 7 of 7 findings, 164 words, 11 sentences, 14.9 words per sentence, 21 figures, 75% of the handed figures, 1 tries
- place facts used (5 of 59): A3, A1, A2, I4, J

Yes. Lahunipara had the lowest recorded planned cost of the 16 blocks in the sample, at Rs 1.66 crore. Of its 582 planned activities, 356 (61.2%) had no cost attached. The block’s figures cover only Haldikudar Gram Panchayat.

The clearest exception is in the output codes. Lahunipara was the only block where Codes 101 and 105 did not lead in either planned cost or planned untied grant funding. The same pair led general-component spending in 14/16 blocks, but not in Lahunipara. Within Lahunipara, Codes 101 and 104 had the lowest spending relative to plan, rather than Codes 101 and 105, the pair seen in 14/16 blocks.

Lahunipara also stood apart by type of work, though it was not alone. Maintenance and New/Fresh led in planned cost in 14/16 blocks and in planned untied grant funding in 13/16 blocks; Lahunipara was an exception to both patterns. It also differed from the 14/16 blocks where those two work types had the lowest spending relative to plan.

### GEO-26 (run 1) - How do the GPs in Sheragada block look?

- used 8 of 8 findings, 301 words, 15 sentences, 20.1 words per sentence, 31 figures, 28% of the handed figures, 2 tries
- place facts used (15 of 60): I4, J, A3, A4, A5, A6, A2, CT, CT, B, E2, E5, F1, H1, G3

Only Sharagada Gram Panchayat is represented in the sample for Sheragada block, so the figures describe that GP, not all GPs in the block. Sharagada has 920 planned activities and accounts for 13 of the 41 GP development plans recorded across the sampled GPs in Ganjam. It recorded Rs 6.51 crore in planned costs, Rs 2.74 crore in sanctions and Rs 1.88 crore in spending on planned activities. Spending was 28.9% of planned cost, below the middle value of 36.6% across the 16 sampled blocks.

The activity count and the budget tell different stories: 722 activities (78.5%) have no cost attached. Good Governance accounts for 461 activities, with Rs 2.12 lakh planned and no spending recorded, while village infrastructure accounts for 243 activities and Rs 4.18 crore in planned costs. The busiest planning year, 2023-2024, had 433 activities, of which 387 had no cost attached. It also had the highest recorded spending, at Rs 44.41 lakh, while the largest planned budget was Rs 2.90 crore in 2020-2021.

At the next review, start by checking work status: no works are marked completed, and 36 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 95.6% of their planned cost. The GP is the recorded sanctioning authority for 84 of the 85 ongoing works. Across the sampled blocks with GP-sanctioned activities, Sheragada accounts for 68.9% of their planned cost. Within Sheragada, activities with the GP listed as sanctioning authority account for 72.0% of spending recorded under the general component.

Also reconcile approvals and payments with the activity records. Administrative approvals are on file for 93 activities (10.1%); a missing record does not establish that approval was absent. Five activities show an approval cost but no approval record, and only 29.7% of cashbook payments are linked to a planned activity.

### GEO-26 (run 2) - How do the GPs in Sheragada block look?

- used 8 of 8 findings, 303 words, 14 sentences, 21.6 words per sentence, 29 figures, 27% of the handed figures, 2 tries
- place facts used (14 of 60): I4, J, A2, A3, A4, A5, A6, CT, CT, B, E2, E5, F1, G3

Sheragada block is represented in the sample by a single GP, Sharagada, so the figures do not show how GPs across the block compare. Sharagada recorded 13 GPDP plans, the most among the four sampled GPs in Ganjam. It listed 920 activities, of which 722 (78.5%) had no cost recorded. Against Rs 6.51 crore planned, Rs 2.74 crore was sanctioned for activities with an approval on file and Rs 1.88 crore was spent on planned activities. Spending was 28.9% of planned cost, below the sample block midpoint of 36.6%.

The years and themes with the most activities were not the ones with the largest budgets. The activity count peaked in 2023-2024 at 433, with no cost recorded for 387 of them; that year also had the highest recorded spending, at Rs 44.41 lakh. The largest planned amount was in 2020-2021, at Rs 2.90 crore. Good Governance had the most activities (461), with Rs 2.12 lakh planned and no spending recorded, while Self-sufficient Infrastructure had 243 activities, Rs 4.18 crore planned and Rs 82.17 lakh spent.

At the next review, start by checking the status of older works against payment and completion records. No works are marked completed, and 36 works planned in 2022-2023 or earlier are still marked ongoing despite recorded spending of 95.6% of their planned cost. The GP is listed as the sanctioning authority for 84 of the 85 ongoing works and accounts for 72.0% of the separately reported general-component spending. Sheragada also accounts for 68.9% of the planned cost of GP-sanctioned activities across the four sampled blocks with such records. Reconcile approvals and payment links as part of that review: only 93 activities have an administrative approval on file, which does not establish that the others lacked approval, and only 29.7% of cashbook payments are linked to a planned activity.

### GEO-26 (run 3) - How do the GPs in Sheragada block look?

- used 8 of 8 findings, 303 words, 17 sentences, 17.8 words per sentence, 35 figures, 32% of the handed figures, 2 tries
- place facts used (14 of 60): I4, J, A1, A3, A5, A6, A2, B, CT, CT, E5, E2, F1, G3

Sharagada is the only Gram Panchayat represented for Sheragada block in the sample. It recorded 920 planned activities and Rs 6.51 crore in planned costs, both the 4th highest of 16 blocks in the sample. It spent Rs 1.88 crore on planned activities, or 28.9% of recorded planned costs, against a sample midpoint of 36.6%. No cost was attached to 722 activities (78.5%). Within the Ganjam sample, Sharagada accounted for 13 of the 41 GP development plans across 4 GPs. 

The years with the most activities were not the years with the largest budgets. The activity count peaked in 2023-2024 at 433, of which 387 had no cost attached. That year also had the highest spending on planned activities, at Rs 44.41 lakh, while planned costs were highest in 2020-2021, at Rs 2.90 crore. The same distinction shows up across themes: Village with Good Governance accounted for 461 activities (50.1%), with Rs 2.12 lakh planned and no spending recorded, while village infrastructure accounted for 243 activities, with Rs 4.18 crore planned and Rs 82.17 lakh spent. 

At the next review, verify the status of the 36 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 95.6% of their planned cost. No works are marked completed. The Gram Panchayat is listed as the sanctioning authority for 84 of the 85 ongoing works. Sheragada also accounts for 68.9% of planned costs for GP-sanctioned activities across the 4 blocks in that comparison. 

Reconcile approvals and payments alongside the status check. Administrative approvals are on file for 93 activities (10.1%); a missing record does not establish that an activity was unapproved. Only 29.7% of cashbook payments are linked to a planned activity. In the separate general-component spending figures, Rs 10.57 lakh is recorded against activities with no sanctioning authority on file.

### GEO-29 (run 1) - How is Khordha district doing overall?

- used 8 of 8 findings, 222 words, 13 sentences, 17.1 words per sentence, 25 figures, 23% of the handed figures, 2 tries
- place facts used (12 of 63): A6, A5, A3, A7, A4, I4, J, B, G3, E5, A2, H1

Khordha recorded the highest spending as a share of planned cost among the 9 districts in the sample: 55.9%. It spent Rs 3.33 crore against a plan of Rs 5.95 crore, leaving spending Rs 2.63 crore below plan. Sanctions on file totalled Rs 4.06 crore. The district figures cover only Bhubaneswar block and its 3 sampled Gram Panchayats.

No single Gram Panchayat dominated the activity count, planned cost, sanctions, spending or gap against plan. The largest annual gaps were in 2023-2024 (Rs 61.33 lakh below plan) and 2025-2026 (Rs 58.33 lakh below plan). In 2025-2026, spending was 35.1% of planned cost. Sanitation had the largest gap by sector (Rs 70.08 lakh), followed by drinking water (Rs 35.86 lakh).

The next review should focus on reconciling payment records and checking the status of older works. Only 23.1% of cashbook payments were linked to a planned activity, the lowest share among the 9 districts in the sample. The linked share rose from 2.7% to 53.2% over the period, indicating more complete linking, not necessarily higher spending. Meanwhile, 145 works planned in 2022-2023 or earlier are still marked ongoing, although 86.0% of their planned cost has been spent. Two other record gaps merit a check: 546 activities (41.5%) have no cost attached, and 48 have an approval cost recorded but no approval record on file.

### GEO-29 (run 2) - How is Khordha district doing overall?

- used 8 of 8 findings, 278 words, 14 sentences, 19.9 words per sentence, 31 figures, 29% of the handed figures, 2 tries
- place facts used (17 of 63): A6, I4, J, A1, A2, A3, A4, A5, A7, B, G3, E1, E2, E5, E4, H1, F1

Khordha recorded the highest spending as a share of planned cost among the 9 districts in the sample: 55.9%, against a middle value of 35.9%. The district figures cover 3 Gram Panchayats in Bhubaneswar block, not the whole district. Of 1,316 planned activities, 546 (41.5%) had no cost attached. The recorded plan was Rs 5.95 crore; Khordha had Rs 4.06 crore sanctioned and Rs 3.33 crore spent, both the 3rd highest in the sample. Spending was still Rs 2.63 crore below plan. 

No single Gram Panchayat accounted for most of the activity, planned cost, sanctions, spending or the gap against plan. Andhrua had the largest share of each, including 37.5% of activities and 38.9% of the gap. The largest annual gaps were in 2023-2024 (Rs 61.33 lakh below plan) and 2025-2026 (Rs 58.33 lakh below plan); in the latter year, spending reached 35.1% of plan. Sanitation had the largest gap by sector (Rs 70.08 lakh below plan), followed by drinking water (Rs 35.86 lakh below plan). 

At the next review, prioritize reconciling payment links and verifying the status of older works. Only 23.1% of cashbook payments were linked to a planned activity, the lowest share among the 9 districts, although the share rose from 2.7% to 53.2% over the period. Khordha had 353 works marked ongoing and only 1 marked complete. Of those still marked ongoing, 145 were planned in 2022-2023 or earlier, with 86.0% of their planned cost already spent. Use the available photo evidence to help check recorded status, and reconcile the 48 activities that show an approval cost but have no approval record on file; a missing record does not establish that approval was absent.

### GEO-29 (run 3) - How is Khordha district doing overall?

- used 8 of 8 findings, 222 words, 11 sentences, 20.2 words per sentence, 29 figures, 30% of the handed figures, 2 tries
- place facts used (11 of 63): I4, J, A5, A3, A6, A7, A1, A2, G3, E5, E2

Khordha’s records in the 20-Gram-Panchayat sample cover 3 Gram Panchayats in Bhubaneswar block. The district spent Rs 3.33 crore against a recorded plan of Rs 5.95 crore. At 55.9%, it had the highest spending against plan of the 9 districts in the sample, compared with a middle value of 35.9%. Even so, spending was Rs 2.63 crore below plan, and 546 of its 1,316 planned activities (41.5%) had no cost attached.

No single Gram Panchayat dominated planning or spending: Andhrua had the largest share of activities (37.5%), planned cost (42.1%), sanctions (43.2%) and spending (44.7%). The gap against plan was also spread across the Gram Panchayats and across years, with the largest amounts in 2023-2024 (Rs 61.33 lakh below plan) and 2025-2026 (Rs 58.33 lakh below plan). Sanitation had the largest gap by sector (Rs 70.08 lakh below plan), followed by drinking water (Rs 35.86 lakh below plan).

At the next review, prioritise reconciling cashbook payments with planned activities and checking the status of older works. Only 23.1% of payments were linked to a planned activity, the lowest share among the 9 districts sampled, although the linked share rose from 2.7% to 53.2% across the six years. Meanwhile, 145 works planned in 2022-2023 or earlier were still marked ongoing, with 86.0% of their planned cost spent. Only 1 work was marked completed.

### GEO-30 (run 1) - What has the analysis found in Koraput?

- used 8 of 8 findings, 250 words, 12 sentences, 20.8 words per sentence, 36 figures, 49% of the handed figures, 2 tries
- place facts used (11 of 63): I4, A1, A5, A3, A6, J, J, C, A2, E2, E5

The sample covers 2 blocks and 2 Gram Panchayats in Koraput. Koraput recorded 1,455 planned activities, the 3rd most of 9 districts in the sample. It spent Rs 3.16 crore against a planned cost of Rs 9.51 crore, or 33.2% of plan.

The Rs 6.36 crore gap between plan and spending was concentrated in Boipariguda and in 2023-2024. Boipariguda accounted for 74.7% of the gap (Rs 4.75 crore) and 67.6% of the district’s planned untied grant (Rs 5.23 crore). It spent 22.8% of its planned cost, compared with 52.1% in Laxmipur. Across the district, 2023-2024 accounted for 51.5% of planned cost (Rs 4.90 crore) and 69.2% of the spending gap (Rs 4.40 crore).

The gap was less concentrated by sector: rural housing had the largest gap at Rs 2.13 crore, followed by drinking water at Rs 1.74 crore. Koraput recorded no spending on its 24 planned rural housing activities and accounted for 95.7% of the rural housing gap across the 9 sampled districts.

For record reconciliation, 695 activities (47.8%) had no cost attached: 447 in Laxmipur and 248 in Boipariguda. The comparison with sanctions covers only activities with a sanction on file; on that basis, spending was Rs 37.43 lakh below sanction, with the gap more evenly split between Boipariguda (Rs 21.44 lakh) and Laxmipur (Rs 15.98 lakh). Work status also merits a check: no works were marked completed, and 154 works planned in 2022-2023 or earlier were still marked ongoing despite recorded spending of 90.1% of their planned cost.

### GEO-30 (run 2) - What has the analysis found in Koraput?

- used 8 of 8 findings, 252 words, 12 sentences, 21.0 words per sentence, 33 figures, 43% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (10 of 63): I4, A1, A2, A5, A6, A7, B, C, E2, E5

In the sample, Koraput is represented by 2 Gram Panchayats in 2 blocks. It recorded 1,455 planned activities, the 3rd most of 9 districts, but 695 of them (47.8%) had no cost attached. Recorded spending on planned activities was Rs 3.16 crore, or 33.2% of the planned cost, leaving spending Rs 6.36 crore below plan.

The gap was concentrated in Boipariguda and in 2023-2024. Boipariguda accounted for 74.7% of the district’s gap against plan (Rs 4.75 crore below plan) and 67.6% of its planned untied grant (Rs 5.23 crore). Laxmipur, by contrast, had more activities without a cost: 447, compared with 248 in Boipariguda. Among activities with a sanction on file, spending was Rs 37.37 crore below sanction across the two blocks, with the gap more evenly split: Rs 21.44 lakh in Boipariguda and Rs 15.98 lakh in Laxmipur.

The 2023-2024 plan accounted for 51.5% of Koraput’s planned cost (Rs 4.90 crore) and 69.2% of its gap against plan (Rs 4.40 crore). Spending that year was 10.3% of the plan. By sector, the largest gaps were in rural housing (Rs 2.13 crore below plan) and drinking water (Rs 1.74 crore below plan). Koraput recorded no spending against its rural housing plan and accounted for 95.7% of the rural housing gap across the 9 districts in the sample.

A separate check is whether work statuses are up to date: no works are marked completed, and 154 works planned in 2022-2023 or earlier are still marked ongoing, with 90.1% of their planned cost spent.

What the officer sees instead:

```
Koraput district
- Koraput district has 2 blocks and 2 Gram Panchayats in the data.
- Koraput district has 1,455 planned activities, the 3rd most of 9 districts. The middle value for these 9 is 1,129.
- 695 of them (47.8%) have no cost attached.
- It spent Rs 3.16 crore on planned activities, the 4th highest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is 33.2% of the planned cost, the 4th lowest of 9 districts. The middle value is 35.9%.
- Spending is Rs 6.36 crore below plan.
- In 2023-2024: 454 activities (173 with no cost), Rs 4.90 crore planned, Rs 50.50 lakh spent, 10.3% of the plan.
- Rural housing: 24 activities and Rs 2.13 crore planned, with nothing spent.
- No works are marked completed.
- 154 works planned in 2022-2023 or earlier are still marked ongoing. Rs 1.80 crore of their Rs 2.00 crore planned cost has been spent (90.1%).

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

### GEO-30 (run 3) - What has the analysis found in Koraput?

- used 8 of 8 findings, 241 words, 12 sentences, 20.1 words per sentence, 29 figures, 43% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (10 of 63): I4, A1, A2, A5, A6, A3, A7, C, E2, E5

Koraput’s records cover 2 Gram Panchayats in 2 blocks in the sample. They show 1,455 planned activities, of which 695 (47.8%) have no cost attached. Recorded spending was Rs 3.16 crore, or 33.2% of the Rs 9.51 crore planned cost, leaving spending Rs 6.36 crore below plan.

Boipariguda is the clearest place to start reviewing the gap between plan and spending: it accounts for 74.7% of the district’s gap (Rs 4.75 crore) and 67.6% of its planned untied grant (Rs 5.23 crore). Laxmipur has more activities with no cost recorded: 447, compared with 248 in Boipariguda. The gap against sanctions is more evenly split: of the Rs 37.43 lakh below sanction, Rs 21.44 lakh was in Boipariguda and Rs 15.98 lakh in Laxmipur. This comparison covers only activities with a sanction on file.

By year, 2023-2024 accounts for 51.5% of Koraput’s planned cost and 69.2% of its spending gap (Rs 4.40 crore). By sector, rural housing and drinking water have the largest gaps, at Rs 2.13 crore and Rs 1.74 crore respectively. Rural housing warrants a closer look: Koraput had 24 planned activities and no recorded spending in that sector, and it accounts for 95.7% of the rural housing spending gap across the sampled districts.

Work status is also worth checking at the next review. No works are marked completed, and 154 works planned in 2022-2023 or earlier are still marked ongoing, with 90.1% of their planned cost recorded as spent.

What the officer sees instead:

```
Koraput district
- Koraput district has 2 blocks and 2 Gram Panchayats in the data.
- Koraput district has 1,455 planned activities, the 3rd most of 9 districts. The middle value for these 9 is 1,129.
- 695 of them (47.8%) have no cost attached.
- It spent Rs 3.16 crore on planned activities, the 4th highest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is 33.2% of the planned cost, the 4th lowest of 9 districts. The middle value is 35.9%.
- Its planned cost is Rs 9.51 crore, the 3rd highest of 9 districts. The middle value is Rs 5.95 crore.
- Spending is Rs 6.36 crore below plan.
- Rural housing: 24 activities and Rs 2.13 crore planned, with nothing spent.
- No works are marked completed.
- 154 works planned in 2022-2023 or earlier are still marked ongoing. Rs 1.80 crore of their Rs 2.00 crore planned cost has been spent (90.1%).

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

### GEO-32 (run 1) - Sundergarh district - what should I look at?

- used 8 of 8 findings, 282 words, 15 sentences, 18.8 words per sentence, 26 figures, 32% of the handed figures, 2 tries
- place facts used (10 of 64): I4, A1, A2, A5, A3, A7, F1, E5, E2, E4

Start with the costing and approval records for the two Gram Panchayats in the Sundargarh sample. Of 1,129 planned activities, 623 (55.2%) have no cost attached. Recorded spending was Rs 1.69 crore against a recorded plan of Rs 3.88 crore. Of the Rs 2.19 crore gap, Rs 1.81 crore (82.8%) was on activities with no sanctioning authority recorded. Only 162 activities (14.3%) have an administrative approval on file; a missing record does not establish that an activity was unapproved.

Review both Panchayats, but distinguish the gap against plan from the gap against sanction. Karuabahal had the larger gap against plan, at Rs 1.28 crore below plan, compared with Rs 90.62 lakh in Haldikudar. For activities with a sanction on file, the order reverses: Haldikudar was Rs 24.83 lakh below sanction and Karuabahal was Rs 12.82 lakh below sanction.

For the sector review, start with drinking water and sanitation. Drinking water had the largest gap against plan (Rs 64.45 lakh), followed by sanitation (Rs 55.17 lakh). Among activities with sanctions on file, sanitation had the largest gap (Rs 12.29 lakh), followed by drinking water (Rs 8.79 lakh). For the untied-grant review, focus on village infrastructure, which accounted for 52.9% (Rs 1.37 crore) of planned untied funds. Roads were the largest individual focus area for planned untied funds (Rs 57.84 lakh) and narrowly led spending linked to payment vouchers (Rs 39.90 lakh, against Rs 39.63 lakh for drinking water).

At the next works review, verify the status of the 95 works planned in 2022-2023 or earlier that are still marked ongoing, with Rs 94.33 lakh already recorded as spent. No works are marked completed; check the recorded status against available photos and local records.

### GEO-32 (run 2) - Sundergarh district - what should I look at?

- used 8 of 8 findings, 309 words, 17 sentences, 18.2 words per sentence, 27 figures, 30% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:
- place facts used (10 of 64): I4, A1, A2, A3, A5, A7, F1, E2, E5, E3

Start with the planning and approval records. In the two Gram Panchayats covered in Sundargarh, 623 of the 1,129 planned activities (55.2%) have no cost attached. Recorded spending was Rs 1.69 crore against a plan of Rs 3.88 crore, leaving it Rs 2.19 crore below plan. Only 162 activities (14.3%) have an administrative approval on file, and 82.8% of the gap against plan sits with activities for which no sanctioning authority is recorded. Check the underlying files before treating a missing record as a missing approval.

Review drinking water and sanitation first. They had the largest gaps against plan—Rs 64.45 lakh and Rs 55.17 lakh, respectively. Among activities with sanctions on file, the same sectors had the largest gaps, but sanitation came first at Rs 12.29 lakh below sanction, followed by drinking water at Rs 8.79 lakh below sanction. The GP comparison also changes with the benchmark: Karuabahal had the larger gap against plan (Rs 1.28 crore below plan), while Haldikudar had the larger gap against sanction (Rs 24.83 lakh below sanction). Keep those comparisons separate at review, since the sanction figures cover only activities with a sanction on file.

Check the untied grant priorities alongside those spending gaps. Self-sufficient Infrastructure in Village accounted for 52.9% (Rs 1.37 crore) of the Rs 2.59 crore planned from untied grants. No single focus area dominated that allocation: roads had the largest share at 22.3% (Rs 57.84 lakh). Roads and drinking water recorded nearly the same spending linked to vouchers—Rs 39.90 lakh and Rs 39.63 lakh, respectively.

Finally, verify the status of older works against site records and available photos. No works are marked completed, and 95 works planned in 2022-2023 or earlier are still marked ongoing, with 80.3% of their planned cost spent. Also check the files for the 17 works marked abandoned, which had Rs 29.26 lakh in planned costs.

What the officer sees instead:

```
Sundargarh district
- Sundargarh district has 2 blocks and 2 Gram Panchayats in the data.
- Sundargarh district has 1,129 planned activities, the 5th most of 9 districts. The middle value for these 9 is 1,129.
- 623 of them (55.2%) have no cost attached.
- Its planned cost is Rs 3.88 crore, the 3rd lowest of 9 districts. The middle value is Rs 5.95 crore.
- It spent Rs 1.69 crore on planned activities, the 3rd lowest of 9 districts. The middle value is Rs 2.17 crore.
- Spending is Rs 2.19 crore below plan.
- 162 of the 1,129 activities (14.3%) have an administrative approval on file, the 3rd fewest of 9 districts. The middle value is 181.
   (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
- No works are marked completed.
- 95 works planned in 2022-2023 or earlier are still marked ongoing. Rs 94.33 lakh of their Rs 1.18 crore planned cost has been spent (80.3%).
- 17 works are marked abandoned, with Rs 29.26 lakh planned on them. 7 of them were planned in 2021-2022.

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

### GEO-32 (run 3) - Sundergarh district - what should I look at?

- used 8 of 8 findings, 317 words, 18 sentences, 17.6 words per sentence, 31 figures, 34% of the handed figures, 2 tries
- place facts used (11 of 64): I4, A1, A2, A5, A3, A7, A6, F1, E2, E5, E4

Start with the planning and approval records. The Sundargarh snapshot covers 2 blocks and 2 Gram Panchayats in the sample. Of 1,129 planned activities, 623 (55.2%) have no cost attached. Recorded spending was Rs 1.69 crore against a plan of Rs 3.88 crore, leaving it Rs 2.19 crore below plan. Yet spending as a share of plan was 43.5%, the 3rd highest of 9 districts in the sample. Activities with no sanctioning authority on file account for 82.8% (Rs 1.81 crore) of the gap. Only 162 activities (14.3%) have an administrative approval on file; check whether approvals are missing from the records before treating those activities as unapproved.

Review drinking water and sanitation first, and use the right comparison for each Panchayat. Drinking water (Rs 64.45 lakh below plan) and sanitation (Rs 55.17 lakh below plan) have the largest gaps against plan. Among activities with sanctions on file, sanitation has the largest gap (Rs 12.29 lakh below sanction), followed by drinking water (Rs 8.79 lakh below sanction). Karuabahal has the larger gap against plan (Rs 1.28 crore), while Haldikudar has the larger gap against recorded sanctions (Rs 24.83 lakh). The sanction comparison covers only activities with a sanction on file, about one in six.

For the untied-grant review, look first at village infrastructure: the theme accounts for 52.9% (Rs 1.37 crore) of planned untied funds. By focus area, roads are the largest item in the untied plan (Rs 57.84 lakh), followed by drinking water (Rs 35.67 lakh). Roads and drinking water also have the highest spending linked to vouchers, at Rs 39.90 lakh and Rs 39.63 lakh respectively.

At the next works review, verify the status of older works against site records and photo evidence. No works are marked completed, and 95 works planned in 2022-2023 or earlier are still marked ongoing, with 80.3% of their planned cost spent. Photo evidence is on file for 103 activities.

### L01 (run 1) - What should I know about Kandhamal?

- used 8 of 8 findings, 327 words, 18 sentences, 18.2 words per sentence, 39 figures, 39% of the handed figures, 2 tries
- place facts used (15 of 62): I4, J, A1, A3, A4, A5, A6, B, A2, F1, G1, G3, E5, E3, E4

Kandhamal is represented in the sample by one Gram Panchayat in Khajuripada block. It has 573 planned activities and a planned cost of Rs 3.48 crore, both the second lowest among the 9 sampled districts. Sanctions on file total Rs 1.14 crore, the lowest in the sample. Recorded spending on planned activities was Rs 58.17 lakh, also the lowest. That was 16.7% of planned cost, against a sample middle value of 35.9%. In 2025-2026, recorded spending was Rs 5.10 lakh against Rs 1.06 crore planned, or 4.8%.

The first review priority is to reconcile the planning, approval and payment records. Of the planned activities, 241 (42.1%) have no cost recorded; 167 of those were planned in 2023-2024. Scheme and fund-component details are each missing for 437 activities (76.3%). Administrative approvals are on file for 136 activities (23.7%); a missing record does not establish that approval was never granted. The cashbook shows Rs 1.24 crore paid out, but only 47.0% of payments are linked to a planned activity. The recorded share of spending linked to planned activities rose from 2.7% to 53.2% over the period; that change alone does not establish that cashbook spending rose.

For the works review, drinking water was the largest planned spending area at Rs 89.50 lakh (25.7% of planned cost), followed by maintenance of community systems at Rs 68.83 lakh (19.8%). All recorded tied-grant funding was planned for drinking water and sanitation, while Self-sufficient Infrastructure in Village accounted for Rs 1.90 crore (67.9%) of planned untied funding. The largest groups of works marked ongoing were in Water Sufficient Village (53) and Clean and Green Village (37). At the next review, verify the status of the 42 works planned in 2022-2023 or earlier that are still marked ongoing, with Rs 24.82 lakh recorded as spent. Also check the 17 works marked abandoned, 16 of which were planned in 2022-2023. Photo evidence is on file for 75 activities, the fewest among the 9 sampled districts.

### L01 (run 2) - What should I know about Kandhamal?

- used 8 of 8 findings, 277 words, 14 sentences, 19.8 words per sentence, 26 figures, 35% of the handed figures, 2 tries
- place facts used (12 of 62): A5, A6, I4, J, A1, A3, A4, B, A2, F1, E5, E4

Kandhamal had the lowest recorded spending against plan among the districts in the sample: Rs 58.17 lakh, or 16.7% of planned cost, against a sample middle value of 35.9%. The district figures cover only Khajuripada block and one Gram Panchayat. The sample recorded 573 planned activities, Rs 3.48 crore in planned costs and Rs 1.14 crore in sanctions, the lowest in the sample. In 2025-2026, recorded spending was 4.8% of that year’s plan.

The next review should check gaps in the planning and approval records. Of the 241 activities with no cost attached, 167 were from 2023-2024. Scheme and fund component were each missing from 437 activity records (76.3%). Administrative approvals were on file for 136 activities (23.7%); a missing record does not establish that an activity lacked approval. Reconcile cashbook entries with activity records before interpreting spending trends: the share of cashbook spending linked to a planned activity went from 2.7% to 53.2%, but better linkage does not by itself show that spending rose.

For a focused review of works, start with the 42 works planned in 2022-2023 or earlier that are still marked ongoing, and check their status against available photo evidence. Only 75 activities have photos on file, the fewest in the sample. Water Sufficient Village accounted for the largest group of ongoing works (53), followed by Clean and Green Village (37).

Drinking water was the largest spending priority in the plan at Rs 89.50 lakh, followed by maintenance of community systems at Rs 68.83 lakh. All recorded tied-grant funding in the plan was for drinking water and sanitation, while Self-sufficient Infrastructure in Village accounted for 67.9% of planned untied-grant funding (Rs 1.90 crore).

### L01 (run 3) - What should I know about Kandhamal?

- used 8 of 8 findings, 280 words, 15 sentences, 18.7 words per sentence, 29 figures, 35% of the handed figures, 2 tries
- place facts used (13 of 62): I4, J, A1, A3, A4, A5, A6, B, A2, F1, E5, E3, E4

Kandhamal is represented in the sample by one Gram Panchayat in Khajuripada block. It recorded 573 planned activities and Rs 3.48 crore in planned costs, both the second lowest among the nine districts in the sample. Sanctions on file totalled Rs 1.14 crore. Recorded spending against plans was Rs 58.17 lakh, or 16.7% of planned cost, the lowest share in the sample. In 2025-2026, recorded spending was just 4.8% of that year’s plan.

At the next review, reconcile the planning, approval and payment records before drawing conclusions about delivery. No cost is recorded for 241 activities (42.1%), including 167 from 2023-2024. The scheme and fund-component fields are each blank for 437 activities (76.3%). Only 136 activities (23.7%) have an administrative approval on file; a missing record does not establish that approval was absent. The share of cashbook spending linked to a planned activity rose from 2.7% to 53.2% over the six fiscal years, but that change alone does not show that total cashbook spending rose.

For the works review, start with the 42 works planned in 2022-2023 or earlier that are still marked ongoing, and check the status of the 17 marked abandoned, of which 16 were planned in 2022-2023. Photo evidence is on file for 75 activities, the fewest among the nine districts sampled. Among works marked ongoing, the largest groups are Water Sufficient Village (53) and Clean and Green Village (37).

Drinking water is the largest planned spending area at Rs 89.50 lakh, followed by maintenance of community systems at Rs 68.83 lakh. Drinking water and sanitation account for all recorded tied-grant allocations, while Self-sufficient Infrastructure in Village accounts for 67.9% (Rs 1.90 crore) of planned untied grants.

### L04 (run 1) - what should I know about Cuttack?

- used 8 of 8 findings, 269 words, 15 sentences, 17.9 words per sentence, 26 figures, 28% of the handed figures, 2 tries
- place facts used (13 of 63): I4, A1, A2, A3, A4, A5, A6, A7, C, G3, E5, E2, F1

Cuttack’s figures cover two Gram Panchayats in two blocks. Of 1,104 planned activities, 465 (42.1%) have no cost recorded. Against a recorded plan of Rs 5.35 crore, Rs 2.33 crore was sanctioned for activities with an approval on file and Rs 2.17 crore was spent on planned activities. Spending was 40.5% of the recorded plan, leaving a gap of Rs 3.18 crore.

Govindapur had the larger share of planned cost, at 56.2%, while Dadhapatna had the larger share of spending, at 57.1%. Govindapur spent 30.9% of its recorded plan and accounted for Rs 2.07 crore of the district’s spending gap. It also accounted for 71.1% of the two panchayats’ reported population.

Sanitation had the most planned activities, at 343, with Rs 91.72 lakh planned and Rs 23.63 lakh spent. Untied grant plans were concentrated in the Self-sufficient Infrastructure in Village theme, which accounted for 84.3% of the planned amount. Roads alone accounted for 41.6% of planned untied grant funding. In the separately reported general spending component, roads and drinking water were the largest items, at Rs 57.60 lakh and Rs 54.22 lakh, respectively.

At the next review, prioritise matching cashbook payments to planned activities and checking whether older work statuses are up to date. Only 23.8% of payments are linked to a planned activity, the second-lowest share among the nine districts in the sample. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing, with 92.1% of their planned cost already spent. Administrative approvals are on file for 181 activities (16.4%); a missing record does not establish that an activity lacked approval.

### L04 (run 2) - what should I know about Cuttack?

- used 8 of 8 findings, 226 words, 13 sentences, 17.4 words per sentence, 22 figures, 30% of the handed figures, 2 tries
- place facts used (10 of 63): I4, A1, A2, A5, A3, A6, A7, G3, E2, E5

Cuttack’s figures cover the two Gram Panchayats in the sample, not the whole district. Of 1,104 planned activities, 42.1% have no cost recorded. Recorded spending on planned activities was Rs 2.17 crore against a recorded plan of Rs 5.35 crore. That is 40.5% of plan, or Rs 3.18 crore below plan. 

Govindapur had the larger planned budget, at Rs 3.00 crore, while Dadhapatna recorded the higher spending, at Rs 1.24 crore. Govindapur spent 30.9% of its planned cost and accounted for 65.3% of the gap between planned cost and spending. It also accounted for 71.1% of the two Panchayats’ reported population and 48.8% of their planned activities. 

Sanitation led by number of planned activities, with 343, but the largest share of planned untied grants went to village infrastructure, at 84.3%. Roads alone accounted for 41.6% of planned untied grants. In the separately reported general spending component, roads and drinking water were the two largest areas, at 24.2% and 22.7%, respectively. 

At the next review, prioritise reconciling cashbook payments with activity records and checking whether older work statuses are current. Only 23.8% of payments are linked to a planned activity, against a middle value of 47.0% among the districts in the sample. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing, with 92.1% of their planned cost already spent.

### L04 (run 3) - what should I know about Cuttack?

- used 8 of 8 findings, 268 words, 15 sentences, 17.9 words per sentence, 37 figures, 38% of the handed figures, 2 tries
- place facts used (13 of 63): I4, A1, A2, A3, A5, A6, A7, C, G3, E2, E5, B, E3

The Cuttack records cover 2 Gram Panchayats in 2 blocks. They list 1,104 planned activities, of which 465 (42.1%) have no cost attached. Against a recorded plan of Rs 5.35 crore, spending on planned activities was Rs 2.17 crore, or 40.5% of plan, compared with a middle value of 35.9% across the 9 districts in the sample. The recorded gap was Rs 3.18 crore.

Govindapur accounts for 71.1% of the two panchayats’ reported population but 48.8% of planned activities. It accounts for 56.2% of planned cost and 65.3% of the gap between plan and spending, with Rs 2.07 crore below plan. Dadhapatna, by contrast, accounts for 57.1% of recorded spending on planned activities (Rs 1.24 crore).

Sanitation leads by activity count, with 343 activities (31.1%), and records Rs 23.63 lakh spent against Rs 91.72 lakh planned. Untied grant plans were concentrated in the Self-sufficient Infrastructure in Village theme, at 84.3% (Rs 3.11 crore). Roads alone accounted for 41.6% of planned untied grant funds. In the separate general-component spending figures, roads and drinking water had the largest shares, at 24.2% and 22.7%, respectively.

For the next review, prioritise matching cashbook payments to plan records and checking older work statuses. Only 23.8% of payments are linked to a planned activity, the second-lowest share among the 9 sampled districts. No works are marked completed, and 90 works planned in 2022-2023 or earlier are still marked ongoing, with 92.1% of their planned cost recorded as spent. Also review the 2023-2024 records: 275 of 551 planned activities have no cost attached, and 95 of the 125 works marked abandoned were planned that year.

### L06 (run 1) - What should I know about Kalimela?

- used 8 of 8 findings, 251 words, 13 sentences, 19.3 words per sentence, 27 figures, 24% of the handed figures, 2 tries
- place facts used (12 of 61): I4, J, A1, A3, A5, A6, B, B, C, A2, G3, E5

Kalimela block is represented in the sample by one Gram Panchayat, Kalimela. Its 852 planned activities carried a recorded cost of Rs 7.65 crore, the 2nd highest of 16 blocks in the sample. Yet spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest in the sample. Spending was 11.1% of plan in 2023-2024 and 10.5% in 2024-2025, the two years with the largest planned budgets.

Drinking water is a priority for review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent. All planned tied grants were for sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending figures, public works accounted for nearly all spending, with drinking water and sanitation the largest areas. The Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries but 3.1% of planned activities; these are planning estimates, not a count of people reached.

At the next review, reconcile the plan, approvals and payments before drawing conclusions about delivery. No cost was recorded for 392 activities (46.0%). Activities without a scheme on file accounted for Rs 5.57 crore of planned cost; 684 activities had no fund component recorded, and 57.5% had no asset category. Only 33.3% of cashbook payments were linked to a planned activity. Also check the status of the 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost already recorded as spent.

### L06 (run 2) - What should I know about Kalimela?

- used 8 of 8 findings, 315 words, 15 sentences, 21.0 words per sentence, 41 figures, 39% of the handed figures, 2 tries
- place facts used (16 of 61): I4, J, A1, A3, A5, A6, B, B, B, C, A2, F1, G1, G3, E5, E3

Kalimela block is represented in the sample by Kalimela Gram Panchayat alone. Its 852 planned activities had a recorded cost of Rs 7.65 crore, the 2nd highest of 16 blocks in the sample. Recorded spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest share in the sample. Spending was 93.6% of plan in 2020-2021, compared with 11.1% in 2023-2024 and 10.5% in 2024-2025. 

Drinking water is the first sector to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent on planned activities. The tied-grant plan was split almost evenly between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending figures, public works accounted for Rs 2.06 crore, compared with Rs 5,000 for beneficiary-oriented programmes; drinking water and sanitation were the largest spending areas in that breakdown. Separately, the Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries (3,978 people), against 3.1% of planned activities. 

At the next review, reconcile the planning, approval and payment records before drawing conclusions about delivery. Of the planned activities, 392 (46.0%) had no cost attached, and 684 (80.3%) had no fund component recorded. Activities with no scheme on file accounted for Rs 5.57 crore (72.7% of planned cost), and activities without an asset category accounted for Rs 2.14 crore (28.0%). Administrative approvals were on file for 168 activities (19.7%); a missing approval record does not establish that approval was absent. The cashbook shows Rs 5.28 crore paid out, but only 33.3% of payments were linked to a planned activity. 

For the works review, start with the 55 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 86.0% of their planned cost. Also check the status of the 22 works marked abandoned, 21 of which were planned in 2024-2025.

### L06 (run 3) - What should I know about Kalimela?

- used 8 of 8 findings, 287 words, 14 sentences, 20.5 words per sentence, 31 figures, 30% of the handed figures, 2 tries
- place facts used (13 of 61): I4, J, A1, A2, A3, A5, A6, B, B, C, F1, G3, E5

Kalimela block is represented in the sample by Kalimela Gram Panchayat alone. It has 852 planned activities, of which 392 (46.0%) have no cost attached. Its recorded plan of Rs 7.65 crore is the 2nd highest of the 16 blocks in the sample, but spending on planned activities was Rs 1.76 crore, or 23.0% of planned cost, the 4th lowest in the sample. Spending was 11.1% of plan in 2023-2024 and 10.5% in 2024-2025.

Drinking water is the first sector to review: it accounted for 48.8% of planned cost, with Rs 3.74 crore planned and Rs 60.98 lakh spent on planned activities. The entire tied-grant plan was split between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). In the separate general-component spending breakdown, drinking water was the largest category at Rs 70.85 lakh, followed by sanitation at Rs 41.40 lakh; public works accounted for nearly all of that spending. By contrast, the Poverty Free and Enhanced Livelihoods Village theme accounted for 45.1% of expected beneficiaries but 3.1% of planned activities. These are planning estimates, not a count of people reached.

At the next review, reconcile the plan, approvals and cashbook. Only 168 activities (19.7%) have an administrative approval on file; a missing record does not establish that approval was absent. No fund component is recorded for 684 activities, and activities without a recorded scheme account for Rs 5.57 crore of planned cost. Activities with no asset category account for Rs 2.14 crore of planned cost, and only 33.3% of cashbook payments are linked to a planned activity. Also verify the status of the 55 works planned in 2022-2023 or earlier that are still marked ongoing, with 86.0% of their planned cost already recorded as spent.

### T02 (run 1) - How is Chikilli doing?

- used 8 of 8 findings, 256 words, 13 sentences, 19.7 words per sentence, 30 figures, 38% of the handed figures, 2 tries
- place facts used (10 of 65): A5, A3, A7, A6, B, A4, H1, E5, E2, E4

Chikilli recorded Rs 1.39 crore in spending against a planned cost of Rs 5.51 crore, leaving spending Rs 4.12 crore below plan. It spent 25.2% of planned cost, the 6th lowest in the 20-Gram-Panchayat sample, where the middle value was 42.0%. Of its 640 planned activities, 329 (51.4%) had no cost attached.

Village infrastructure is the first area to review: it accounted for 59.5% of planned cost and 63.4% of the gap between plan and spending (Rs 2.61 crore). By focus area, the largest gaps were in community system maintenance (Rs 98.63 lakh) and roads (Rs 74.02 lakh), but the remaining areas together accounted for Rs 2.39 crore. Spending was spread across the years, with the highest amount in 2021-2022 (Rs 31.82 lakh). The largest gap was in 2024-2025 (Rs 1.38 crore below plan), while spending in 2025-2026 was 12.0% of that year’s planned cost.

At the next review, reconcile payments with sanction and approval files, and verify the status of older works. No sanctions are recorded, and 71 activities show an approval cost but have no approval record on file. The share of spending linked to a planned activity rose from 2.7% to 53.2%; that shows more spending was linked in the records, not necessarily that total spending rose. Works marked ongoing accounted for 93.1% of recorded general-component spending. Among them, 35 works planned in 2022-2023 or earlier are still marked ongoing, with Rs 70.25 lakh spent against Rs 83.53 lakh planned. No works are marked complete, and no activities have photo evidence on file.

### T02 (run 2) - How is Chikilli doing?

- used 8 of 8 findings, 269 words, 11 sentences, 24.5 words per sentence, 33 figures, 34% of the handed figures, 2 tries
- place facts used (15 of 65): A5, A3, A7, A6, B, B, B, B, E5, E2, E4, A4, F1, F2, H1

Chikilli recorded Rs 1.39 crore in spending against a planned cost of Rs 5.51 crore, leaving it Rs 4.12 crore below plan. It spent 25.2% of the planned cost, compared with a middle value of 42.0% in the 20-Gram-Panchayat sample. Of its 640 planned activities, 329 (51.4%) had no cost attached. 

Village infrastructure accounted for 59.5% of planned costs and 63.4% of the overall spending gap (Rs 2.61 crore below plan). Looking at individual focus areas, community system maintenance had the largest gap (Rs 98.63 lakh below plan), followed by roads (Rs 74.02 lakh below plan); neither accounted for most of the gap. The year with the most spending was 2021-2022 (Rs 31.82 lakh), while the largest gap was in 2024-2025 (Rs 1.38 crore below plan). Spending as a share of plan fell from 76.2% in 2022-2023 to 23.7% in 2023-2024, 16.2% in 2024-2025 and 12.0% in 2025-2026. 

At the next review, verify work status, starting with the 35 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 84.1% of their planned cost. Works marked ongoing account for 93.1% of spending under the general component; no works are marked completed, and no activities have photo evidence on file. Reconcile the sanction and approval records as well: no sanctions or administrative or technical approvals are on file, yet 71 activities have an approval cost recorded without a corresponding approval record. The share of cashbook spending linked to planned activities rose from 2.7% to 53.2% across the six years; that shows more spending was linked to the plan, not necessarily that total cashbook spending rose.

### T02 (run 3) - How is Chikilli doing?

- used 8 of 8 findings, 252 words, 15 sentences, 16.8 words per sentence, 28 figures, 29% of the handed figures, 2 tries
- place facts used (15 of 65): A1, A2, A3, A5, A6, A7, B, B, E2, E4, E5, A4, F1, F2, H1

Chikilli planned 640 activities, but 329 (51.4%) have no cost attached. Its recorded plan of Rs 5.51 crore was the 6th highest in the 20-Gram-Panchayat sample. It spent Rs 1.39 crore on planned activities, or 25.2% of planned cost, against a sample middle value of 42.0%. That left spending Rs 4.12 crore below plan.

Village infrastructure is the clearest place to look within that gap: it accounts for 59.5% of planned cost and 63.4% of the gap (Rs 2.61 crore). No single focus area dominates the gap; maintenance of community systems and roads are the largest individual contributors. Spending itself was spread across fiscal years, but the share of planned cost spent fell from 76.2% in 2022-2023 to 12.0% in 2025-2026. The largest gap in rupee terms was Rs 1.38 crore in 2024-2025.

At the next review, reconcile work status, approvals and payments. No works are marked complete, and no activities have photo evidence. Works marked ongoing account for 93.1% of recorded general-component spending. In particular, 35 works planned in 2022-2023 or earlier are still marked ongoing, with Rs 70.25 lakh spent against Rs 83.53 lakh planned (84.1%). No sanctions are on record, and no administrative or technical approvals are on file, although 71 activities have an approval cost recorded. Missing files do not establish that approval was never granted. The share of cashbook spending linked to planned activities rose from 2.7% to 53.2% over the period; that shows more spending was linked in the records, not necessarily that spending itself rose.

### T04 (run 1) - How is Barpali block doing?

- used 8 of 8 findings, 275 words, 15 sentences, 18.3 words per sentence, 31 figures, 33% of the handed figures, 2 tries
- place facts used (14 of 62): A1, A2, A3, A4, A5, A6, A7, G3, J, J, B, E2, E5, F1

Barpali ranks high in recorded sanctions and spending, but much of its plan has no cost attached. Its 1,447 planned activities are the most among the 16 blocks compared, and 1,067 (73.7%) have no cost attached. Against a recorded plan of Rs 5.49 crore, Barpali recorded Rs 2.96 crore in sanctions and Rs 2.64 crore in spending on planned activities, both 3rd highest in the comparison. Spending reached 48.1% of the recorded plan, above the middle value of 36.6%, but remained Rs 2.85 crore below plan. The block had the highest share of cashbook payments linked to a planned activity, at 80.4%.

For the spending gap, start with Bandhpali. It accounts for 61.0% of planned cost and 53.1% of spending, but 68.2% of the gap, or Rs 1.94 crore. Bandhpali spent 41.9% of its plan, compared with 57.7% in Bhatigaon. Spending was spread across the years, but 2025-2026 had the largest gap, at Rs 80.35 lakh, with spending at 31.6% of plan. In the separate general-component spending figures, the largest amounts were for Self-sufficient Infrastructure in Village (Rs 99.22 lakh) and Water Sufficient Village (Rs 91.57 lakh).

At the next review, reconcile work status in both Gram Panchayats. Bhatigaon has 88 works marked ongoing and Bandhpali has 83; none are marked completed in the block. Start with the 76 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending at 92.0% of their planned cost. Check approval records as well: 180 activities (12.4%) have an administrative approval on file, but a missing record does not establish that approval was never granted. All 6 activities listed as under approval are in Bandhpali.

### T04 (run 2) - How is Barpali block doing?

- used 8 of 8 findings, 256 words, 13 sentences, 19.7 words per sentence, 28 figures, 31% of the handed figures, 2 tries
- place facts used (12 of 62): A1, A2, A3, A5, A6, A7, G3, J, J, E2, E5, F1

Barpali had the most planned activities of the 16 blocks compared in the sample, at 1,447, but 1,067 (73.7%) had no cost attached. Against a recorded plan of Rs 5.49 crore, it spent Rs 2.64 crore, the 3rd highest amount among the blocks compared. That was 48.1% of planned cost, above the sample middle value of 36.6%, but still Rs 2.85 crore below plan. Barpali also had the highest share of payments linked to a planned activity, at 80.4%.

Spending was fairly evenly split between Bandhpali and Bhatigaon, but Bandhpali accounted for 61.0% of planned cost and 68.2% of the block’s spending gap (Rs 1.94 crore). It spent 41.9% of its plan, compared with 57.7% in Bhatigaon. Spending was spread across fiscal years, while the largest annual gap was in 2025-2026, at Rs 80.35 lakh below plan. In the separate general-component spending figures, village infrastructure and water sufficiency were the largest themes, at Rs 99.22 lakh and Rs 91.57 lakh, respectively.

At the next review, reconcile work status against payments and available photo evidence. Works marked ongoing were nearly evenly split between Bhatigaon (88) and Bandhpali (83), and none were marked completed. Start with the 76 works planned in 2022-2023 or earlier that are still marked ongoing despite recorded spending of 92.0% of their planned cost. Also check Bandhpali’s approval records: all 6 activities listed as under approval were in that Gram Panchayat. Across the block, 180 activities (12.4%) had an administrative approval on file; a missing record does not establish that approval was not granted.

### T04 (run 3) - How is Barpali block doing?

- used 8 of 8 findings, 229 words, 11 sentences, 20.8 words per sentence, 27 figures, 33% of the handed figures, 2 tries
- place facts used (13 of 62): A1, A2, J, J, A3, A4, A5, A6, A7, B, E2, E4, E5

Barpali has the most planned activities in the sample—1,447 across Bandhpali and Bhatigaon—but 1,067 (73.7%) have no cost attached. Against a recorded plan of Rs 5.49 crore, Barpali had Rs 2.96 crore sanctioned and spent Rs 2.64 crore on planned activities, ranking 3rd of 16 sampled blocks on both sanctions and spending. Spending was 48.1% of the recorded plan, above the sample middle value of 36.6%, but still Rs 2.85 crore below plan. 

The spending gap is more concentrated by panchayat than by year. Bandhpali held 61.0% of planned cost and 53.1% of spending, but accounted for 68.2% of the block’s gap (Rs 1.94 crore below plan), compared with Rs 90.49 lakh below plan in Bhatigaon. No single year dominated spending; the largest annual gap was Rs 80.35 lakh in 2025-2026, when spending was 31.6% of plan. In the separate general-component spending breakdown, the largest shares went to village infrastructure and water sufficiency, at 33.1% and 30.6% respectively. 

At the next review, prioritise reconciling work status with payments and photo evidence. Ongoing works are nearly evenly split—88 in Bhatigaon and 83 in Bandhpali—and none are marked completed. In particular, 76 works planned in 2022-2023 or earlier are still marked ongoing, with 92.0% of their recorded planned cost already spent. Bandhpali is also the place to follow up on pending approvals: all 6 activities recorded as under approval are there.

### T14 (run 1) - Anything I should be looking at in Ganjam?

- used 8 of 8 findings, 267 words, 11 sentences, 24.3 words per sentence, 26 figures, 28% of the handed figures, 2 tries
- place facts used (10 of 70): A3, A5, A6, A7, A2, B, E2, E5, H1, G3

Ganjam had the highest planned cost (Rs 23.85 crore) and the highest recorded spending on planned activities (Rs 6.00 crore) among the 9 districts in the sample. Even so, spending was 25.2% of planned cost, the 3rd lowest in the sample, and Rs 17.85 crore below plan. Also check the completeness of the plans: 1,768 activities (64.9%) had no cost recorded, with missing costs spread across the sampled Gram Panchayats. 

**Start the spending review with village infrastructure.** The Self-sufficient Infrastructure in Village theme accounted for 50.9% of the district’s gap against plan (Rs 9.08 crore). The largest annual gap was in 2023-2024 (Rs 6.44 crore), when 809 activities had no cost recorded. The gap was spread across the sampled Gram Panchayats; Biswamathpur had the largest amount (Rs 7.23 crore below plan), with spending at 16.4% of planned cost. 

**Verify work status, starting with older works and Sharagada GP.** No works were marked completed, and 183 works planned in 2022-2023 or earlier were still marked ongoing, with 89.2% of their planned cost spent. Sharagada accounted for 62.1% of the planned cost of works marked abandoned (Rs 1.19 crore). Among activities with sanctions on file, it also accounted for 51.0% of the district’s spending gap against sanction (Rs 85.77 lakh). 

**Reconcile approvals and payments, starting with Khallikote block.** The block had Rs 0 in recorded sanctions but Rs 1.30 crore in payments linked to planned activities; check whether the corresponding approvals are on file. Districtwide, 76 activities had an approval amount recorded but no corresponding approval record, and only 35.4% of cashbook payments were linked to a planned activity.

### T14 (run 2) - Anything I should be looking at in Ganjam?

- used 8 of 8 findings, 306 words, 14 sentences, 21.9 words per sentence, 30 figures, 34% of the handed figures, 2 tries
- place facts used (11 of 70): A1, I4, A3, A5, A6, A2, E2, E5, F1, H1, G3

Start with the gap between plans and recorded spending. In the sample, Ganjam has 2,723 planned activities across 3 blocks and 4 Gram Panchayats. It has the highest planned cost (Rs 23.85 crore) and the highest spending on planned activities (Rs 6.00 crore) among the 9 districts in the sample, but spending is only 25.2% of planned cost, the 3rd lowest share. Of the Rs 17.85 crore gap, just over half is in village infrastructure (Rs 9.08 crore, or 50.9%). The gap is spread across the sampled Panchayats and years, but Biswamathpur has the largest Panchayat gap (Rs 7.23 crore below plan), and 2023-2024 has the largest annual gap (Rs 6.44 crore below plan). Check the cost entries alongside the spending figures: 1,768 activities (64.9%) have no cost recorded, including 722 in Sharagada and 421 in Mendarajpur.

At the works review, verify the status of older projects. Ganjam has no works marked complete, yet 183 works planned in 2022-2023 or earlier are still marked ongoing, with 89.2% of their planned cost already spent. In Sharagada Gram Panchayat, review the works marked abandoned: they account for Rs 1.19 crore, or 62.1%, of Ganjam’s planned cost on abandoned works. Sharagada also accounts for Rs 85.77 lakh, or 51.0%, of the gap between spending and sanctions for activities with a sanction on file.

For financial reconciliation, start with Khallikote: it has Rs 1.30 crore in cashbook payments linked to planned activities but no sanctioned amount recorded. Check those payments against the approval files rather than assuming they were made without approval. Across the sampled Ganjam Panchayats, 76 activities have an approval cost recorded but no approval record, and only 35.4% of cashbook payments are linked to a planned activity. The linked share rose from 2.7% to 53.2% over the period; that does not, by itself, show that spending rose.

### T14 (run 3) - Anything I should be looking at in Ganjam?

- used 8 of 8 findings, 254 words, 14 sentences, 18.1 words per sentence, 20 figures, 24% of the handed figures, 2 tries
- place facts used (8 of 70): I4, A3, A5, A6, A7, E5, E2, A2

Start with the gap between Ganjam’s plans and recorded spending. Across the 4 Gram Panchayats in the sample, Ganjam had the highest planned cost (Rs 23.85 crore) and the highest spending on planned activities (Rs 6.00 crore) among the districts sampled. Even so, spending was 25.2% of planned cost, leaving a gap of Rs 17.85 crore. The gap was spread across panchayats, with the largest amount in Biswamathpur (Rs 7.23 crore). Village infrastructure accounted for 50.9% of the gap, and 2023-2024 had the largest annual gap (Rs 6.44 crore).

At the next works review, check whether older works are still ongoing and focus the abandoned-works review on Sharagada. Ganjam has 183 works planned in 2022-2023 or earlier that are still marked ongoing, despite recorded spending of 89.2% of their planned cost. No works are marked completed. Sharagada accounts for 62.1% of the planned cost of abandoned works and 51.0% of the spending gap on activities with a sanction on file. It also has the most activities without a recorded cost (722), though missing costs are widespread across the sampled panchayats: districtwide, 1,768 activities (64.9%) have no cost attached.

For financial reconciliation, start with Khallikote: it shows Rs 1.30 crore in payments linked to planned activities, but no sanctioned amount in the records reviewed. Check the underlying approvals before treating this as spending without sanction. Across Ganjam, the share of spending linked to planned activities rose from 2.7% to 53.2%. That shows more spending was linked in the records, not necessarily that spending itself rose.

### TWO-01 (run 1) - Compare Kalimela and Bheden

- used 8 of 8 findings, 253 words, 10 sentences, 25.3 words per sentence, 34 figures, 49% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A2, A2, A3, A4, A5, A3, A4, A5, A6, A6, A7, A7

Kalimela and Bheden planned nearly the same number of activities: 852 in Kalimela and 838 in Bheden, both above the middle value of 712 across the sampled blocks. Bheden had more activities with no cost recorded: 466 (55.6%), compared with 392 (46.0%) in Kalimela.

Kalimela recorded a higher planned cost (Rs 7.65 crore), sanctioned amount (Rs 2.08 crore) and spending on planned activities (Rs 1.76 crore) than Bheden (Rs 7.22 crore planned, Rs 1.76 crore sanctioned and Rs 1.62 crore spent ). Yet both spent a similar share of recorded planned cost: 23.0% in Kalimela and 22.4% in Bheden, well below the sample’s middle value of 36.6%. Kalimela had the larger gap in rupees: Rs 5.90 crore below plan, compared with Rs 5.60 crore in Bheden.

Among records marked “No” for panchayat bhawan, the two blocks had similar shares of planned activities (22.9% for Kalimela and 22.5% for Bheden). Kalimela accounted for a larger share of activities with a recorded cost (26.2% versus 21.1%) and of the reported population (31.0% versus 26.1%). For both blocks, their shares of planned cost (33.4% and 31.5%, respectively) were larger than their shares of either sanctions (23.4% and 19.8%) or spending on planned activities (22.9% and 21.1%). The separate general-component spending figures show a similar split (24.2% and 20.2%), while both blocks accounted for larger shares of the gap between plan and spending (38.7% and 36.7%). At the next review, check missing cost entries first in Bheden and reconcile planned costs, sanctions and payments in both blocks.

### TWO-01 (run 2) - Compare Kalimela and Bheden

- used 8 of 8 findings, 221 words, 11 sentences, 20.1 words per sentence, 22 figures, 30% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A3, A3, A2, A2, A4, A5, A4, A5, A6, A6, A7, A7

Kalimela and Bheden have similar numbers of planned activities: 852 in Kalimela and 838 in Bheden. Kalimela has a higher recorded plan cost, at Rs 7.65 crore against Rs 7.22 crore in Bheden. But more activities have no cost attached in Bheden—466 (55.6%) versus 392 (46.0%) in Kalimela.

Kalimela had Rs 2.08 crore sanctioned and spent Rs 1.76 crore on planned activities. Bheden had Rs 1.76 crore sanctioned and spent Rs 1.62 crore. Both spent well below the sample’s middle value of 36.6% of planned cost: Kalimela spent 23.0% and Bheden 22.4%. In rupee terms, Kalimela was further below plan, by Rs 5.90 crore versus Rs 5.60 crore for Bheden.

Among the 6 sampled Gram Panchayats recorded as having no panchayat bhawan, Kalimela and Bheden had the two largest shares of planned activities, activities with a cost attached, and reported population. Their shares of planned cost—33.4% for Kalimela and 31.5% for Bheden —were larger than their respective shares of sanctions, spending on planned activities, or separately reported general-component spending. They also accounted for the two largest shares of the gap between plan and spending in this group: 38.7% for Kalimela and 36.7% for Bheden.

At the next review, check the activities without costs first in Bheden, where they are more common, and reconcile planned costs, sanctions and payments in both blocks.

### TWO-01 (run 3) - Compare Kalimela and Bheden

- used 8 of 8 findings, 230 words, 10 sentences, 23.0 words per sentence, 20 figures, 26% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A2, A2, A3, A3, A4, A5, A4, A5, A6, A6, A7, A7

Kalimela and Bheden had similar numbers of planned activities: 852 in Kalimela and 838 in Bheden. Bheden had more activities without a recorded cost: 466 (55.6%), compared with 392 (46.0%) in Kalimela. Kalimela’s recorded plan was larger at Rs 7.65 crore, compared with Rs 7.22 crore in Bheden.

Kalimela had more sanctioned (Rs 2.08 crore) and spent more on planned activities (Rs 1.76 crore) than Bheden, where Rs 1.76 crore was sanctioned and Rs 1.62 crore was spent. Yet spending was a similar share of planned cost in both blocks: 23.0% in Kalimela and 22.4% in Bheden, both below the sample block median of 36.6%. Spending was Rs 5.90 crore below plan in Kalimela and Rs 5.60 crore below plan in Bheden.

Among the 6 sampled Gram Panchayats recorded as having no panchayat bhawan, Kalimela and Bheden accounted for similar shares of planned activities, but Kalimela had more activities with a recorded cost and a larger reported population. Both accounted for larger shares of the group’s planned cost and spending gap than of its sanctions or spending on planned activities. The separately reported general-component spending was also higher in Kalimela, at Rs 2.07 crore, than in Bheden, at Rs 1.72 crore.

At the next review, reconcile planned costs, sanctions and spending in both blocks, and give particular attention to the higher share of activities without a recorded cost in Bheden.

### TWO-02 (run 1) - How does Chikilli compare with Hirlipali?

- used 8 of 8 findings, 242 words, 11 sentences, 22.0 words per sentence, 20 figures, 39% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A2, A2, A3, A3, A5, A5, A6, A6, A7, A7, A4, A4

Hirlipali has more planned activities than Chikilli—777 against 640 —but a larger share have no cost attached: 72.5% against 51.4%. Chikilli has the higher recorded planned cost at Rs 5.51 crore, compared with Rs 2.46 crore in Hirlipali. Chikilli also spent more on planned activities, Rs 1.39 crore against Rs 1.19 crore, but that was a smaller share of its recorded plan: 25.2% against 48.3%. Spending was Rs 4.12 crore below plan in Chikilli and Rs 1.27 crore below plan in Hirlipali.

The clearest records check is in Chikilli: it shows spending on planned activities but no sanction on record, while Hirlipali has Rs 1.25 crore in recorded sanctions. Across all fiscal years reviewed, Chikilli had the lowest sanctioned amount and the lowest proposed cost at sanction in the sample. It also had the fewest activities with technical or administrative approval in 5/6 fiscal years, with no clear pattern in 2023-2024. Chikilli was the only Gram Panchayat in the sample where spending was unevenly spread across fund components when measured against either plans or sanctions. At the next review, officials could reconcile Chikilli’s spending entries with its sanction and approval files and check the fund-component entries.

In the separate general-component breakdown, village infrastructure was the largest spending theme in both places, accounting for 46.9% in Chikilli and 33.7% in Hirlipali. Chikilli’s next-largest theme was Clean and Green Village at 19.2%, while in Hirlipali, Water Sufficient Village was close behind infrastructure at 32.0%.

### TWO-02 (run 2) - How does Chikilli compare with Hirlipali?

- used 8 of 8 findings, 193 words, 10 sentences, 19.3 words per sentence, 19 figures, 35% of the handed figures, 2 tries
- place facts used (12 of 14): A1, A1, A2, A2, A3, A3, A5, A5, A6, A6, A4, A4

Hirlipali planned more activities than Chikilli: 777 versus 640. But more of Hirlipali’s activities had no cost attached—563 (72.5%), compared with 329 (51.4%) in Chikilli. Chikilli’s recorded planned cost was higher, at Rs 5.51 crore versus Rs 2.46 crore. Chikilli also spent more on planned activities—Rs 1.39 crore versus Rs 1.19 crore —but that represented a smaller share of its recorded plan: 25.2% versus 48.3%.

The first records to reconcile are Chikilli’s sanctions and approvals. Chikilli recorded spending on planned activities but had no sanctioned amount on record, while Hirlipali had Rs 1.25 crore sanctioned. Across all fiscal years reviewed, Chikilli had the lowest sanctioned amount and the lowest proposed cost at sanction among the sampled Gram Panchayats. It also had the fewest activities with technical or administrative approval in 5/6 fiscal years; neither measure showed a clear pattern in 2023-2024.

Chikilli was also the only sampled Gram Panchayat where spending was unevenly spread across fund components, whether measured against plan or sanction. Within the general component, village infrastructure took the largest share in both Panchayats: 46.9% in Chikilli and 33.7% in Hirlipali, where the water sufficiency theme was close behind at 32.0%.

### TWO-02 (run 3) - How does Chikilli compare with Hirlipali?

- used 8 of 8 findings, 204 words, 9 sentences, 22.7 words per sentence, 20 figures, 39% of the handed figures, 2 tries
- place facts used (12 of 14): A1, A1, A2, A2, A3, A3, A5, A5, A6, A6, A4, A4

Hirlipali planned more activities—777 against Chikilli’s 640 —but more of its activities had no cost attached: 563 (72.5%) compared with 329 (51.4%) in Chikilli. Chikilli’s recorded planned cost was higher, at Rs 5.51 crore against Rs 2.46 crore. Chikilli also spent more on planned activities—Rs 1.39 crore against Rs 1.19 crore —but that was a smaller share of its recorded plan: 25.2% compared with 48.3% in Hirlipali.

The clearest records issue for review is that Chikilli shows spending on planned activities but no sanctions on record, while Hirlipali has Rs 1.25 crore sanctioned. Chikilli recorded both the lowest sanctioned amount and the lowest proposed cost at sanction in the sample in every fiscal year reviewed. It also had the fewest activities with technical approval and the fewest with administrative approval in 5/6 fiscal years; neither pattern held clearly in 2023-2024.

Chikilli was the only panchayat in the sample where spending was unevenly spread across funding components, whether measured against plan or against sanction. In the general component specifically, village infrastructure was the largest spending theme in both panchayats: 46.9% in Chikilli and 33.7% in Hirlipali. Hirlipali’s water-sufficiency theme was close behind at 32.0%, while Chikilli’s next-largest theme, Clean and Green Village, accounted for 19.2%.

### TWO-03 (run 1) - Compare Khordha and Cuttack districts

- used 8 of 8 findings, 233 words, 10 sentences, 23.3 words per sentence, 25 figures, 33% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A3, A3, A2, A2, A4, A4, A5, A5, A6, A6, A7, A7

In the sample, Khordha had more planned activities than Cuttack (1,316 versus 1,104) and a higher planned cost (Rs 5.95 crore versus Rs 5.35 crore). The share of activities with no recorded cost was similar: 41.5% in Khordha and 42.1% in Cuttack. Khordha recorded more in sanctions (Rs 4.06 crore versus Rs 2.33 crore) and spending (Rs 3.33 crore versus Rs 2.17 crore). Khordha spent 55.9% of planned cost, the highest share among the 9 districts in the sample, compared with 40.5% in Cuttack. Cuttack was further below plan in rupee terms: Rs 3.18 crore, compared with Rs 2.63 crore in Khordha.

For the next review, Govindapur is the clearest starting point in Cuttack: it accounted for 56.2% of planned cost and 65.3% of the gap between plan and spending, while Dadhapatna accounted for 57.1% of spending. In Khordha, Andhrua had the largest share of both planned cost (42.1%) and spending (44.7%), but the gap was more evenly spread: Andhrua was Rs 1.02 crore below plan, Itipur Rs 90.99 lakh below, and Barimunda Rs 69.45 lakh below.

When reconciling payments with plans, keep spending linked to a planned activity separate from total recorded spending. The linked amounts were Rs 3.26 crore in Khordha and Rs 2.07 crore in Cuttack. A rise in the share linked to plans does not by itself show that spending rose; check the cashbook totals before drawing that conclusion.

### TWO-03 (run 2) - Compare Khordha and Cuttack districts

- used 8 of 8 findings, 234 words, 10 sentences, 23.4 words per sentence, 26 figures, 33% of the handed figures, 2 tries
- place facts used (14 of 14): A1, A1, A3, A3, A2, A2, A4, A5, A4, A5, A6, A6, A7, A7

In the 20-Gram-Panchayat sample, Khordha recorded more planned activities than Cuttack (1,316 versus 1,104) and a higher planned cost (Rs 5.95 crore versus Rs 5.35 crore). The share of activities with no cost attached was similar: 41.5% in Khordha and 42.1% in Cuttack. Khordha recorded Rs 4.06 crore in sanctions and Rs 3.33 crore in spending, compared with Rs 2.33 crore and Rs 2.17 crore, respectively, in Cuttack. Khordha spent 55.9% of its planned cost, the highest share among the 9 districts in the sample, compared with Cuttack’s 40.5%. Spending was Rs 2.63 crore below plan in Khordha and Rs 3.18 crore below plan in Cuttack.

For the next review, Govindapur is a useful starting point in Cuttack: it accounted for 56.2% of planned cost and 65.3% of the district’s gap between plan and spending, while Dadhapatna accounted for 57.1% of spending. In Khordha, Andhrua had the largest share of both planned cost (42.1%) and spending (44.7%), but the gap was spread across all three sampled panchayats: Andhrua was Rs 1.02 crore below plan, Itipur Rs 90.99 lakh below and Barimunda Rs 69.45 lakh below.

A separate records check is to reconcile payments with planned activities. Spending explicitly linked to a planned activity totalled Rs 3.26 crore in Khordha and Rs 2.07 crore in Cuttack. An increase in the share of payments linked to a plan is not, by itself, evidence of higher spending.

### TWO-03 (run 3) - Compare Khordha and Cuttack districts

- used 8 of 8 findings, 192 words, 8 sentences, 24.0 words per sentence, 24 figures, 33% of the handed figures, 2 tries
- place facts used (14 of 14): A3, A3, A4, A4, A5, A5, A1, A1, A2, A2, A6, A7, A6, A7

Khordha recorded higher planned costs, sanctions and spending than Cuttack in the sample. Khordha had 1,316 planned activities with a recorded cost of Rs 5.95 crore, compared with 1,104 activities and Rs 5.35 crore in Cuttack. The share of activities without a cost was similar: 41.5% in Khordha and 42.1% in Cuttack.

Khordha recorded Rs 4.06 crore in sanctions and Rs 3.33 crore in spending, compared with Rs 2.33 crore and Rs 2.17 crore, respectively, in Cuttack. Khordha spent 55.9% of its recorded planned cost and was Rs 2.63 crore below plan; Cuttack spent 40.5% and was Rs 3.18 crore below plan. Spending explicitly linked to planned activities totalled Rs 3.26 crore in Khordha and Rs 2.07 crore in Cuttack.

For the next review, Govindapur is a useful starting point in Cuttack: it accounted for 56.2% of planned cost and 65.3% of the gap between plan and spending, while Dadhapatna accounted for 57.1% of spending. In Khordha, Andhrua had the largest share of both planned cost (42.1%) and spending (44.7%), but the gap was more evenly spread: Andhrua accounted for 38.9%, Itipur for 34.7%, and Barimunda was Rs 69.45 lakh below plan.

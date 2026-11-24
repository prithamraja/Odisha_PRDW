# Writer tests side by side: current, plainlines, current_choose, plainlines_choose

| | current | plainlines | current_choose | plainlines_choose |
|---|---|---|---|---|
| Writer model | gpt-6.2-sol | gpt-6.2-sol | gpt-6.2-sol | gpt-6.2-sol |
| Prompt | the live prompt (context_brief.py) | DiscoverChat/experiments/writer_prompts/original_plain_lines.txt | the live prompt (context_brief.py) | DiscoverChat/experiments/writer_prompts/original_plain_lines.txt |
| Every finding must be mentioned | on | on | off (test only) | off (test only) |
| Questions | 12 | 12 | 12 | 12 |
| Answers kept | 12 | 11 | 12 | 12 |
| Answers lost (plain sentences shown instead) | 0 | 1 (1 on 2_numerals_cited) | 0 | 0 |
| Passed on the first try | 3 | 2 | 11 | 9 |
| Writer calls | 21 | 22 | 13 | 15 |
| Seconds per answer, middle | 19.8 | 21.1 | 10.2 | 10.4 |
| Findings used, of those handed (middle) | 15.0 of 15.0 | 15 of 15 | 11.0 of 15.0 | 9.0 of 15.0 |
| Words per answer, middle | 277.5 | 254 | 213.0 | 179.5 |
| Words per answer, most | 343 | 316 | 274 | 253 |
| Sentences per answer, middle | 14.0 | 16 | 11.5 | 12.0 |
| Words per sentence, middle | 19.4 | 15.9 | 18.1 | 15.0 |
| Sentences over 25 words | 19% | 4% | 23% | 2% |
| Figures per answer, middle | 24.5 | 19 | 18.0 | 12.0 |
| Figures per sentence, middle | 1.9 | 1.3 | 1.5 | 1.2 |
| Sentences with more than 2 figures | 28% | 10% | 19% | 10% |
| Share of the handed figures that appear, middle | 30% | 20% | 20% | 20% |

## The 12 questions every run answered

### L06 - What should I know about Kalimela?

**current**

- used 18 of 18 findings, 293 words, 14 sentences, 20.9 words per sentence, 24 figures, 21% of the handed figures, 2 tries

Kalimela’s first priority for review is to reconcile the plan, sanction and payment records. Planned costs totalled Rs 7.65 crore, and spending linked to planned activities was Rs 5.90 crore below plan. The largest recorded gap was in 2024-2025, at Rs 2.68 crore below plan; that year also had the highest planned cost, at Rs 3.00 crore. Check the gap against the cashbook before drawing conclusions about actual spending: the share of spending linked to planned activities rose from 2.7% to 53.2%, and only about one in six activities had a sanction on file.

Drinking water was the largest focus area by planned cost (Rs 3.74 crore), recorded sanctions (Rs 71.75 lakh) and general-component spending (Rs 70.85 lakh). Planned tied grants were split almost evenly between sanitation (Rs 46.59 lakh) and drinking water (Rs 45.69 lakh). The plan is harder to review by funding source or asset type: 684 activities had no fund component recorded, Rs 5.57 crore in planned costs had no scheme recorded, and 57.5% of activities were uncategorised by asset type.

For the next works review, start by checking the status and photo evidence of works marked ongoing: they account for 91.8% of general-component spending. Nearly all general-component spending was on public works, and 68.9% was recorded against new works. Photo evidence was on file for 129 activities, most often under the Clean and Green Village and Water Sufficient Village themes. Only 13 activities were recorded as completed; check whether completion records are up to date.

Treat beneficiary figures as planning estimates, not verified reach. The plan listed 8,820 expected beneficiaries, with 75.8% in 2024-2025 and 71.8% associated with activities recorded as costless. The Poverty Free and Enhanced Livelihoods Village theme had the largest share of expected beneficiaries, at 45.1%.

**plainlines**

- used 18 of 18 findings, 316 words, 21 sentences, 15.0 words per sentence, 28 figures, 23% of the handed figures, 2 tries

Drinking water is Kalimela Gram Panchayat’s largest focus area by planned cost, recorded sanctions and general-component spending. At the next review, check the funding records and reconcile spending against the plan.

The plan totals Rs 7.65 crore, with Rs 3.74 crore for drinking water. Drinking water also leads recorded sanctions at Rs 71.75 lakh and general-component spending at Rs 70.85 lakh, with sanitation next on both measures. Only about one in six activities has a sanction record on file. The Rs 92.28 lakh in planned tied grants is split almost evenly between sanitation and drinking water.

No fund component is listed for 684 of the 852 planned activities. Activities with no scheme listed account for Rs 5.57 crore in planned costs. Activities without an asset category account for Rs 2.14 crore. The largest planned amounts were in 2024-2025 and 2023-2024. Those years also had the largest recorded gaps against plan: Rs 2.68 crore below plan in 2024-2025 and Rs 2.33 crore below in 2023-2024, out of a total gap of Rs 5.90 crore. The share of spending linked to a planned activity went from 2.7% to 53.2%. Check the cashbook before treating the rise in linked spending as a rise in actual spending.

Nearly all general-component spending was recorded under public works, with just Rs 5,000 under beneficiary-oriented programmes. New works accounted for 68.9% of that spending, and works marked ongoing accounted for 91.8%. Only 13 activities are recorded as complete. Photo evidence is on file for 129 activities, with the most in the Clean and Green Village and Water Sufficient Village themes. Check work status and photo records together at the review.

The plans list 8,820 expected beneficiaries, not confirmed reach. Most of the expected beneficiaries are listed under 2024-2025 (6,688 people) and under activities marked as having no cost (6,333 people). The poverty and livelihoods theme has the largest expected count, at 3,978 people.

**current_choose**

- used 11 of 18 findings, 214 words, 12 sentences, 17.8 words per sentence, 18 figures, 17% of the handed figures, 1 tries

For Kalimela Gram Panchayat, the first review priority is to reconcile plans, sanctions and payments. Of 852 planned activities, 684 have no fund component recorded. Scheme details are missing for Rs 5.57 crore of the Rs 7.65 crore planned, and only about one in six activities has a sanction on file. Spending was recorded at Rs 5.90 crore below plan, with the largest gaps in 2024-2025 (Rs 2.68 crore below plan) and 2023-2024 (Rs 2.33 crore below plan). The share of spending linked to planned activities rose from 2.7% to 53.2%; check the cashbook before interpreting that rise as an increase in spending.

Drinking water is the largest focus area in planned costs, recorded sanctions and general-component spending. It accounts for 48.8% of planned costs and 34.3% of general-component spending. The planned tied grant of Rs 92.28 lakh is split almost evenly between sanitation and drinking water, making those areas a practical starting point for checking sanctions and payments.

At the next works review, verify whether activity statuses are up to date. Works marked ongoing account for 91.8% of general-component spending but only 18.1% of planned activities. Kalimela has 129 activities with photo evidence and only 13 recorded completions. Check the status entries against completion records and available photos before drawing conclusions about progress.

**plainlines_choose**

- used 11 of 18 findings, 182 words, 12 sentences, 15.2 words per sentence, 12 figures, 12% of the handed figures, 1 tries

Drinking water is Kalimela’s largest focus area by planned cost and recorded general-component spending. At the next review, check how payments are linked to plans and whether work status is up to date. 

Drinking water accounts for 48.8% of planned cost and 34.3% of recorded general-component spending. Sanitation is next in recorded spending, at 20.0%. Planned tied grants are split almost evenly between drinking water and sanitation. 

Spending linked to planned activities was Rs 5.90 crore below plan, with the largest gaps in 2024-2025 and 2023-2024. Check that gap against the cashbook before treating it as underspending: the share of spending linked to a planned activity went from 2.7% to 53.2%. Scheme names are missing for activities worth Rs 5.57 crore in planned cost. Fund components are missing for 684 activities, and only about one in six activities has a sanction on file. 

Works marked ongoing account for 91.8% of recorded general-component spending. Only 13 activities are recorded as complete. Check the status of those ongoing works against site records and available photos before drawing conclusions about how much work is finished.

### T06 - Which blocks account for the shortfall?

**current**

- used 1 of 1 findings, 62 words, 4 sentences, 15.5 words per sentence, 8 figures, 80% of the handed figures, 1 tries

The recorded spending shortfall was Rs 51.96 crore, spread across 16 blocks. Rangeilunda accounted for the largest share at 17.5%, with spending Rs 9.11 crore below plan. Kalimela followed at 11.3%, with spending Rs 5.90 crore below plan. The remaining 14 blocks were collectively Rs 36.96 crore below plan, so the shortfall was not concentrated in either of the two largest contributors.

**plainlines**

- used 1 of 1 findings, 55 words, 5 sentences, 11.0 words per sentence, 8 figures, 80% of the handed figures, 1 tries

The Rs 51.96 crore shortfall against plan is spread across 16 blocks in the sample. Rangeilunda and Kalimela account for the largest shares.

Rangeilunda was Rs 9.11 crore below plan, or 17.5% of the shortfall. Kalimela was Rs 5.90 crore below plan, or 11.3%. The remaining 14 blocks were together Rs 36.96 crore below plan.

**current_choose**

- used 1 of 1 findings, 55 words, 4 sentences, 13.8 words per sentence, 8 figures, 80% of the handed figures, 1 tries

The recorded spending shortfall against plan was Rs 51.96 crore, spread across 16 blocks in the sample. Rangeilunda accounted for the largest share at 17.5%, with spending Rs 9.11 crore below plan. Kalimela followed at 11.3%, with spending Rs 5.90 crore below plan. The remaining 14 blocks together accounted for Rs 36.96 crore below plan.

**plainlines_choose**

- used 1 of 1 findings, 44 words, 4 sentences, 11.0 words per sentence, 8 figures, 80% of the handed figures, 1 tries

The recorded spending shortfall was Rs 51.96 crore across 16 blocks in the sample. Rangeilunda had the largest shortfall, at Rs 9.11 crore (17.5%).

Kalimela was next, at Rs 5.90 crore (11.3%). The remaining 14 blocks together accounted for Rs 36.96 crore below plan.

### T14 - Anything I should be looking at in Ganjam?

**current**

- used 15 of 15 findings, 336 words, 18 sentences, 18.7 words per sentence, 25 figures, 33% of the handed figures, 2 tries

Start with the gap between planned and recorded spending. Across the 4 sampled Gram Panchayats in Ganjam, recorded spending was Rs 17.85 crore below plan. The gap was spread across the panchayats, with the largest amount in Biswamathpur (Rs 7.23 crore). It was more concentrated by theme: Theme 6 – Self-sufficient Infrastructure in Village accounted for 50.9% of the gap (Rs 9.08 crore). The largest annual gap was in 2023-2024 (Rs 6.44 crore). Ganjam and Bargarh were the lowest against plan in 6/7 themes among the districts sampled; in Theme 4 – Water Sufficient Village, the lowest were Ganjam and Malkangiri.

Sharagada’s work records merit a closer look. It accounted for 62.1% of the money planned for abandoned works (Rs 1.19 crore) and 51.0% of the gap between sanctions and spending (Rs 85.77 lakh below sanction). The latter comparison covers only activities with a sanction record on file, about one in six. Missing cost estimates are a broader planning issue: 1,768 activities across the 4 sampled panchayats had no cost recorded, including 722 in Sharagada. Within Ganjam, Maintenance of community system and Sanitation were lowest against sanction, rather than Drinking water and Sanitation as in most sampled districts. Chikilli was the only panchayat in the wider sample where spending against sanction was unevenly spread across focus areas.

At block level, reconcile Khallikote’s records: it showed Rs 0 in sanctions alongside Rs 1.30 crore in spending linked to planned activities. Ganjam and Bargarh led the sampled districts in voucher-linked spending in 5/6 fiscal years, with no clear pattern in 2022-2023. Ganjam’s share of spending linked to planned activities rose from 2.7% to 53.2%; that shows more spending was linked in the records, not necessarily that total spending rose.

Check how works are classified at the next review. Ganjam did not follow the usual pattern of New/Fresh works having the highest planned tied-grant amount or the highest sanctioned amount. It was also the only sampled district where New/Fresh works did not account for the majority of voucher-linked spending.

**plainlines**

- used 15 of 15 findings, 305 words, 16 sentences, 19.1 words per sentence, 20 figures, 31% of the handed figures, 2 tries

Start with Ganjam’s gap between planned and recorded spending, and check the abandoned works in Sharagada Gram Panchayat. 

Recorded spending was Rs 17.85 crore below plan across the 4 sampled Gram Panchayats. The gap was spread across the panchayats, with the largest amount in Biswamathpur (Rs 7.23 crore below plan). Village infrastructure accounted for 50.9% of the gap (Rs 9.08 crore below plan). The largest gap by year was in 2023-2024 (Rs 6.44 crore below plan). Ganjam was among the lowest sampled districts for spending against plan across all themes, alongside Bargarh except in Water Sufficient Village, where it was alongside Malkangiri. 

Sharagada accounted for 62.1% of the money planned for abandoned works (Rs 1.19 crore). It also had the most activities planned without a cost (722 of 1,768 across the sampled Ganjam panchayats). Sharagada was Rs 85.77 lakh below sanction, or 51.0% of the gap, but that comparison covers only activities with a sanction record on file, about one in six. 

Reconcile the sanction and payment records in Khallikote block: the records show Rs 0 in sanctions but Rs 1.30 crore in spending linked to planned activities. Ganjam and Bargarh led the sampled districts in voucher-linked spending in 5/6 fiscal years, with no clear pattern in 2022-2023. Ganjam’s linked share rose from 2.7% to 53.2%; that alone does not show that total spending rose. 

At the next review, check the mix of work types. Ganjam differs from most sampled districts, where New/Fresh works have the largest amounts in tied-grant plans and sanctions and make up most voucher-linked spending. Within Ganjam, maintenance of community systems and sanitation were lowest for spending against sanction, rather than drinking water and sanitation as in most sampled districts. At panchayat level, Chikilli was the only one in the sample where spending against sanction was unevenly spread across focus areas.

**current_choose**

- used 7 of 15 findings, 192 words, 11 sentences, 17.5 words per sentence, 12 figures, 19% of the handed figures, 1 tries

Yes. Start with Sharagada Gram Panchayat. It accounts for 62.1% of Ganjam’s planned money on abandoned works in the sample (Rs 1.19 crore) and 51.0% of the gap between sanctioned amounts and recorded spending (Rs 85.77 lakh below sanction). It also has 722 activities planned without a cost. Review the abandoned-work entries and missing cost estimates, and bear in mind that the spending-to-sanction comparison covers only activities with a sanction on file—about one in six.

For the broader gap against plan, look at village infrastructure and Biswamathpur. Recorded spending was Rs 17.85 crore below plan across the 4 sampled Ganjam Gram Panchayats. Theme 6 – Self-sufficient Infrastructure in Village accounts for Rs 9.08 crore of that gap, while Biswamathpur has the largest gap among the sampled Ganjam Gram Panchayats, at Rs 7.23 crore below plan. These are two views of the same total, not separate gaps to add together.

Ask Khallikote block to reconcile its sanction and payment records: the sample shows Rs 0 in recorded sanctions alongside Rs 1.30 crore in spending linked to planned activities. Check whether the linked payments have corresponding sanctions on file before drawing conclusions about authorisation.

**plainlines_choose**

- used 7 of 15 findings, 177 words, 12 sentences, 14.8 words per sentence, 10 figures, 14% of the handed figures, 1 tries

Yes. Start with the gap between planned and recorded spending, especially for village infrastructure. Then review abandoned works in Sharagada and reconcile spending with sanction records in Khallikote. 

Recorded spending was Rs 17.85 crore below plan across the 4 Ganjam Gram Panchayats in the sample. The gap was spread across the panchayats, but village infrastructure alone accounted for Rs 9.08 crore of it. When reviewing the gap, check the plan entries with no cost listed: there were 1,768 such activities across the 4 panchayats. 

Sharagada is the clearest place to review abandoned works. It accounts for Rs 1.19 crore of the Rs 1.91 crore planned for abandoned works in the Ganjam sample. It also accounts for 51.0% of the gap between sanctioned amounts and recorded spending. That comparison covers only activities with a sanction on file, about one in six. 

In Khallikote block, the records show Rs 1.30 crore in spending linked to planned activities, but Rs 0 in recorded sanctions. Check whether the vouchers can be matched to sanction records before drawing conclusions about the payments.

### T15 - What is the position on abandoned works?

**current**

- used 20 of 20 findings, 343 words, 18 sentences, 19.1 words per sentence, 29 figures, 22% of the handed figures, 2 tries

In the sample, works recorded as abandoned had Rs 5.85 crore in planned funding across 18 Gram Panchayats. Sharagada had the largest amount, at Rs 1.19 crore, followed by Bheden at Rs 87.81 lakh. Separately, records marked “work ongoing” show Rs 25.45 lakh in planned funding counted against abandoned works, with the largest amounts in Kalyansinghpur and Bandhpali. Those records warrant a status check before they are treated as abandoned.

Sharagada and Bheden are priorities for different kinds of work. Sharagada led in maintenance, which accounted for Rs 2.56 crore in planned funding for abandoned works, and in the Self-sufficient Infrastructure in Village theme. It also accounted for 63.9% of the amount in the maintenance of community systems focus area and 83.4% of the amount recorded under Sarpanch sanctions. Bheden led in new works, which accounted for Rs 3.07 crore, and also had the largest amounts in the Clean and Green Village theme and the roads focus area. Upgradation presents a different pattern: of the Rs 38.49 lakh planned for abandoned works, the largest amounts were in Chikilli and Hirlipali.

At district level, Bargarh had the highest planned funding for abandoned works across the village development themes. It led in both Village with Good Governance and Child Friendly Village. Of the Rs 42.00 lakh in the governance theme, 63.6% was recorded in 2021-2022. The sanctioning authority was not recorded for 69.3% of the theme’s planned funding for abandoned works, making those records a priority for reconciliation.

By number of abandoned activities, sanitation was the leading focus area in 7/9 districts, with no clear pattern in Koraput or Kandhamal. New works led in 5/6 fiscal years; maintenance led in 2022-2023. Output Code 101 accounted for a majority of abandoned activities in 8/9 districts and a majority of planned funding for abandoned works in 17/20 Gram Panchayats. Koraput showed no clear district pattern by activity count, while Andhrua, Boipariguda and Laxmipur showed no clear Panchayat pattern by planned funding. Code 101 also led by activity count in 5/6 fiscal years; Code 105 led in 2022-2023.

**plainlines**

- used 20 of 20 findings, 258 words, 16 sentences, 16.1 words per sentence, 24 figures, 18% of the handed figures, 2 tries

In the sample, works marked abandoned had Rs 5.85 crore in planned funding, spread across 18 Gram Panchayats. Sharagada and Bheden had the largest amounts, while Bargarh led among districts across development themes.

Sharagada is a priority for checking maintenance records. It had Rs 1.10 crore in planned funding for abandoned maintenance works and led the village infrastructure theme with Rs 77.65 lakh. It also accounted for 63.9% of the planned money for abandoned works in community system maintenance and 83.4% where the Sarpanch was listed as the sanctioning authority. Bheden led for new works, roads and the Clean and Green Village theme. For upgrades, check Chikilli and Hirlipali first.

By number of abandoned activities, sanitation led in 7/9 districts, with no clear pattern in Koraput or Kandhamal. New works led in 5/6 fiscal years. Code 101 accounted for most abandoned activities in 8/9 districts, with Koraput the exception. It also led by count in 5/6 fiscal years and accounted for most planned money on abandoned works in 17/20 Gram Panchayats. In 2022-2023, maintenance led instead of new works, and Code 105 led instead of Code 101.

For the district review, Bargarh had the largest share in both the Village with Good Governance and Child Friendly Village themes. In the governance theme, 63.6% of the planned money on abandoned works was in 2021-2022, and 69.3% had no sanctioning authority recorded. Separately, records marked ongoing show Rs 25.45 lakh in planned money on abandoned works. Reconcile those status records first in Kalyansinghpur and Bandhpali, where the amounts were largest.

**current_choose**

- used 16 of 20 findings, 270 words, 13 sentences, 20.8 words per sentence, 29 figures, 24% of the handed figures, 1 tries

In the sample, works marked abandoned had Rs 5.85 crore in planned funding across 18 Gram Panchayats. Sharagada had the largest amount (Rs 1.19 crore), followed by Bheden (Rs 87.81 lakh), while Rs 3.78 crore was spread across the other 16 Gram Panchayats. These are planned amounts, not payments. Records marked “work ongoing” also show Rs 25.45 lakh in planned funding under abandoned works; reconcile those records first in Kalyansinghpur and Bandhpali, which have the largest amounts in that group.

Sharagada and Bheden warrant different lines of review. Sharagada leads in planned funding for abandoned maintenance works (Rs 1.10 crore), village infrastructure works (Rs 77.65 lakh) and maintenance of community systems (Rs 56.07 lakh). Bheden leads for new works (Rs 72.52 lakh), Clean and Green Village works (Rs 32.54 lakh) and roads (Rs 15.82 lakh). At district level, Bargarh has the highest planned amount across all village development themes. For the Good Governance theme, Rs 26.72 lakh of the Rs 42.00 lakh total is recorded in 2021-2022, and Rs 29.11 lakh is on records with no sanctioning authority listed.

By number of abandoned activities, sanitation leads among focus areas in 7/9 districts, with no clear pattern in Koraput or Kandhamal. Code 101 accounts for most abandoned activities in 8/9 districts, with no clear pattern in Koraput, and most planned funding for abandoned works in 17/20 Gram Panchayats, with no clear pattern in Andhrua, Boipariguda or Laxmipur. New works and Code 101 each lead their respective categories by number of abandoned activities in 5/6 fiscal years. The exception for both is 2022-2023, when maintenance and Code 105 lead their respective categories.

**plainlines_choose**

- used 11 of 20 findings, 220 words, 15 sentences, 14.7 words per sentence, 20 figures, 17% of the handed figures, 1 tries

In the sample, works marked abandoned had Rs 5.85 crore in planned funds. They were recorded in 18 Gram Panchayats.

Sharagada and Bheden are the first Panchayats to review by planned amount. Sharagada had the largest amount for works marked abandoned (Rs 1.19 crore), followed by Bheden (Rs 87.81 lakh). Sharagada also had the largest share of planned funds on abandoned maintenance works (43.1%), while Bheden had the largest share for new works (23.6%).

By number of abandoned works, new works led in 5/6 fiscal years. Maintenance led instead in 2022-2023. Sanitation had the most abandoned works in 7/9 districts. Code 101 accounted for most abandoned works in 8/9 districts and most planned funds on abandoned works in 17/20 Gram Panchayats.

At district level, start with Bargarh: it had the highest planned amount on abandoned works across development themes. For Village with Good Governance works, check the 2021-2022 records, which account for 63.6% of the theme’s planned funds on abandoned works. Also check the sanction records: entries with no sanctioning authority recorded account for 69.3% of that theme’s planned funds on abandoned works.

Reconcile the work status separately. Records still marked “Work ongoing” show Rs 25.45 lakh in planned funds on abandoned works. Kalyansinghpur and Bandhpali have the largest amounts in those records and are the places to check first.

### GEO-12 - What does the analysis say about Haldikudar?

**current**

- used 20 of 20 findings, 323 words, 15 sentences, 21.5 words per sentence, 39 figures, 32% of the handed figures, 2 tries

Haldikudar recorded 582 planned activities across 6 fiscal years, of which 356 were listed as costless and 226 as costed. Poverty alleviation accounted for the most activities (241), followed by Sanitation (76). The year with the most activities was 2025-2026 (194), while the highest planned cost was in 2021-2022 (Rs 35.26 lakh), against Rs 1.66 crore planned overall.

The Rs 61.52 lakh tied-grant plan was entirely for Drinking water (Rs 35.91 lakh) and Sanitation (Rs 25.60 lakh). Of the Rs 1.04 crore planned in untied grants, 54.9% was under Theme 6 – Self-sufficient Infrastructure in Village, and 76.0% was for new works. Theme 6 also accounted for the largest share of sanctions, at 38.9% of Rs 99.95 lakh, and of voucher-linked spending, at 43.4% of Rs 75.12 lakh. By focus area, Roads had the largest share of both planned untied grants (23.4%) and voucher-linked spending (22.5%).

Recorded spending was Rs 90.62 lakh below plan, with the largest gaps in Sanitation (Rs 28.32 lakh below plan) and Drinking water (Rs 25.12 lakh below plan). Those same areas had the largest gaps against sanctions: Rs 9.19 lakh for Sanitation and Rs 7.47 lakh for Drinking water, out of an overall gap of Rs 24.83 lakh below sanction. That comparison covers only activities with a sanction on file, about one in six. By asset category, Water Sources & Structures had the largest gap against plan (Rs 21.81 lakh below plan).

For the next review, reconcile the missing fund-component and scheme entries: 488 activities had no fund component recorded, and 488 had no scheme recorded. Activities without a recorded fund component accounted for Rs 65.78 lakh below plan. All 10,455 expected beneficiaries were listed against activities with no scheme recorded, and 4,136 were listed against activities not mapped to a development theme. The share of spending linked to planned activities went from 2.7% to 53.2%; check the cashbook before treating that change as an increase in spending.

**plainlines**

- used 20 of 20 findings, 254 words, 16 sentences, 15.9 words per sentence, 12 figures, 10% of the handed figures, 2 tries

Haldikudar’s recorded spending was Rs 90.62 lakh below plan, with the largest gaps in sanitation and drinking water. Most planned activities had no scheme or fund component recorded.

Sanitation was Rs 28.32 lakh below plan, and drinking water was Rs 25.12 lakh below plan. These were also the only two areas with tied grants planned. They had the largest gaps against sanctioned amounts as well, but only about one in six activities had a sanction on file. Looking at the same plan gap by asset type, water sources and structures accounted for the largest amount: Rs 21.81 lakh below plan.

Activities with no fund component recorded accounted for Rs 65.78 lakh of the gap against plan. All 10,455 expected beneficiaries were listed on records with no scheme named. The largest group of expected beneficiaries by theme was on records with no theme assigned.

Haldikudar planned 582 activities, of which 356 were listed as costless. Poverty alleviation had the most planned activities, while roads had the largest share of planned untied grants and of spending recorded against vouchers. Most planned untied grant money was for new works. By theme, village infrastructure took 54.9% of planned untied grants and had the largest share of both sanctioned amounts and spending recorded against vouchers.

Planned costs were highest in 2021-2022, while the number of planned activities was highest in 2025-2026. Spending linked to planned activities was also highest in 2025-2026. That does not by itself show that total spending rose; check the cashbook totals before drawing that conclusion.

**current_choose**

- used 11 of 20 findings, 212 words, 10 sentences, 21.2 words per sentence, 21 figures, 18% of the handed figures, 1 tries

Haldikudar recorded Rs 1.66 crore in planned costs and Rs 75.12 lakh in voucher-linked spending, with spending Rs 90.62 lakh below plan. Sanitation and drinking water had the largest gaps: Rs 28.32 lakh and Rs 25.12 lakh below plan, respectively. They also had the largest gaps against sanctions, at Rs 9.19 lakh and Rs 7.47 lakh below sanction, respectively; that comparison covers only the activities with a sanction on file, about one in six.

The entire Rs 61.52 lakh tied-grant plan was allocated to drinking water (Rs 35.91 lakh) and sanitation (Rs 25.60 lakh). In the Rs 1.04 crore untied-grant plan, self-sufficient village infrastructure accounted for 54.9% (Rs 57.26 lakh). Roads were the largest focus area for both planned untied grants (Rs 24.42 lakh) and voucher-linked spending (Rs 16.89 lakh).

The next review should prioritise reconciling sanitation and drinking-water records and checking missing funding classifications. No fund component was recorded for 488 of the 582 planned activities; those records accounted for Rs 65.78 lakh of the gap against plan. All 10,455 expected beneficiaries were recorded against entries with no scheme on file. The share of spending linked to a planned activity rose from 2.7% to 53.2%, but that change alone does not show that total spending rose; check it against the cashbook.

**plainlines_choose**

- used 10 of 20 findings, 182 words, 12 sentences, 15.2 words per sentence, 10 figures, 9% of the handed figures, 1 tries

Haldikudar’s recorded spending was Rs 90.62 lakh below plan, with the largest gaps in sanitation and drinking water. Most planned activities had no scheme or fund component recorded, making it hard to pin down where to follow up.

Drinking water and sanitation accounted for all Rs 61.52 lakh in planned tied grants. Spending was Rs 28.32 lakh below plan for sanitation and Rs 25.12 lakh below plan for drinking water. They also had the largest gaps against sanctions, but that comparison covers only about one in six activities with a sanction on file.

The untied grant plan had a different emphasis. Of the Rs 1.04 crore planned, 54.9% was under the Self-sufficient Infrastructure in Village theme. Roads had the largest share by focus area, at 23.4%. Roads also had the largest share of spending linked to vouchers, at 22.5%.

For the next review, start with the activities that have no fund component on file. They account for Rs 65.78 lakh of the gap against plan. Check the scheme entries too: all 10,455 expected beneficiaries were listed on records with no scheme named.

### GEO-18 - Is Laxmipur behind on anything?

**current**

- used 6 of 6 findings, 138 words, 8 sentences, 17.2 words per sentence, 13 figures, 27% of the handed figures, 2 tries

Yes—Laxmipur’s recorded spending is Rs 1.61 crore below plan. The largest gaps by year were in 2025-2026 (Rs 65.79 lakh) and 2023-2024 (Rs 61.40 lakh). Water is a priority for review: Drinking water had the largest gap among focus areas (Rs 48.04 lakh), followed by Sanitation (Rs 44.29 lakh). Water Sufficient Village had the largest gap among themes (Rs 51.55 lakh), and drinking water supply structures had the largest among asset categories (Rs 34.96 lakh). These are overlapping views of the same shortfall, not amounts to add together.

Start by reconciling the 642 records with no sanctioning authority listed. They account for Rs 1.45 crore of the gap against plan. Among activities with a sanction on file—about one in six—recorded spending was Rs 15.98 lakh below sanction, with Drinking water accounting for Rs 9.93 lakh of that gap.

**plainlines**

- used 6 of 6 findings, 172 words, 13 sentences, 13.2 words per sentence, 14 figures, 29% of the handed figures, 2 tries

Yes. Laxmipur’s recorded spending is Rs 1.61 crore below plan. For activities with a sanction on file, spending is Rs 15.98 lakh below the sanctioned amount.

The gap against plan spans 6 fiscal years. It was largest in 2025-2026 at Rs 65.79 lakh below plan, followed by 2023-2024 at Rs 61.40 lakh below plan. Drinking water and sanitation had the largest gaps by focus area, at Rs 48.04 lakh and Rs 44.29 lakh below plan, respectively. Water Sufficient Village had the largest gap by theme, at Rs 51.55 lakh below plan. Drinking water supply structures had the largest gap by asset type, at Rs 34.96 lakh below plan. These are different views of the same overall gap, not amounts to add together.

For the next review, check the 642 records with no sanctioning authority listed. They account for Rs 1.45 crore of the gap against plan. The comparison with sanctioned amounts covers only about one in six activities. Within that group, drinking water accounts for 62.1% of the spending gap against sanctions.

**current_choose**

- used 4 of 6 findings, 124 words, 7 sentences, 17.7 words per sentence, 11 figures, 23% of the handed figures, 1 tries

Yes. Laxmipur’s recorded spending was Rs 1.61 crore below plan. The gap spans 6 fiscal years, with the largest shortfalls in 2025-2026 (Rs 65.79 lakh) and 2023-2024 (Rs 61.40 lakh). Drinking water (Rs 48.04 lakh below plan) and sanitation (Rs 44.29 lakh below plan) had the largest gaps by focus area, though the shortfall was spread across other areas as well.

For the next review, reconcile the sanction records and start with drinking water when checking spending against sanctions. Records with no sanctioning authority listed account for 90.1% of the gap against plan. The separate comparison against sanctions covers only about one in six activities; within those records, spending was Rs 15.98 lakh below sanction, with drinking water accounting for 62.1% of that gap.

**plainlines_choose**

- used 5 of 6 findings, 112 words, 9 sentences, 12.4 words per sentence, 11 figures, 23% of the handed figures, 2 tries

Yes. Laxmipur’s recorded spending was Rs 1.61 crore below plan. For activities with a sanction on file, spending was Rs 15.98 lakh below the sanctioned amount.

The gap against plan was spread across several areas, with the largest gaps in drinking water (Rs 48.04 lakh) and sanitation (Rs 44.29 lakh). The largest gaps by year were in 2025-2026 (Rs 65.79 lakh) and 2023-2024 (Rs 61.40 lakh).

Drinking water is a good place to start the review: it accounted for 62.1% of the gap against sanctions. That comparison covers only about one in six activities. Separately, 642 records had no sanctioning authority listed. Those records accounted for 90.1% of the gap against plan.

### GEO-20 - Anything notable about Sharagada?

**current**

- used 13 of 13 findings, 219 words, 11 sentences, 19.9 words per sentence, 17 figures, 21% of the handed figures, 2 tries

Sharagada’s first priority is to reconcile the plan with the cashbook. Recorded spending was Rs 4.63 crore below plan, and Rs 3.77 crore of that gap sat in entries with no fund component recorded. The planned-cost records also show Rs 3.77 crore with no scheme recorded, while 78.5% of planned activities were classified as costless. Start with 2020-2021: it had the largest gap against plan, at Rs 2.54 crore, and the highest cashbook payments, at Rs 2.13 crore. The share of cashbook spending linked to planned activities went from 2.7% to 53.2%; that change in linkage does not establish that payments rose.

Maintenance and village infrastructure stand out in separate breakdowns of the same spending gap. Maintenance accounted for 85.0% of planned untied grants and 90.6% of the gap against plan. Village infrastructure accounted for 72.6% of that gap and 64.0% of the gap against sanctions, although only about one in six activities had a sanction on file. These are the records to check first when comparing plans, sanctions and payments.

For the next works review, focus on ongoing public works: all 85 activities marked ongoing were public works, and activities marked ongoing accounted for 72.7% of recorded general-component spending. Village infrastructure had the most activities with photo evidence, at 35, followed by Clean and Green Village, at 26.

**plainlines**

- used 13 of 13 findings, 221 words, 15 sentences, 14.7 words per sentence, 21 figures, 28% of the handed figures, 2 tries

Yes. Sharagada’s spending linked to planned activities was Rs 4.63 crore below plan, with maintenance accounting for 90.6% of that gap. Start the review with maintenance and the records for 2020-2021, which accounted for Rs 2.54 crore of the same gap.

Maintenance also accounted for Rs 4.25 crore of the Rs 5.00 crore planned under untied grants. By theme, village infrastructure had the largest gap against plan, at Rs 3.36 crore. It also had the largest gap against sanction, at Rs 54.92 lakh, though only about one in six activities had a sanction on file. Village infrastructure accounted for 35 of the 80 activities with photo evidence.

Reconcile the plan and cashbook before treating the gap as money left unspent. Of the Rs 6.51 crore in planned costs, Rs 3.77 crore had no scheme recorded. Separately, entries with no fund component recorded accounted for Rs 3.77 crore of the gap against plan. The cashbook shows Rs 6.34 crore paid out, while Rs 1.78 crore in spending was linked to planned activities. The linked share rose from 2.7% to 53.2%; that alone does not show that payments rose.

For the works review, all 85 activities marked ongoing were public works. Activities marked ongoing accounted for 72.7% of general-component spending. Across the full plan, 722 of the 920 activities were listed as costless.

**current_choose**

- used 11 of 13 findings, 221 words, 12 sentences, 18.4 words per sentence, 16 figures, 21% of the handed figures, 1 tries

Sharagada’s first priority is to reconcile the activity records with the cashbook. Spending recorded against the plan was Rs 4.63 crore below plan, and Rs 3.77 crore of that gap was on entries with no fund component recorded. Separately, 827 entries had no scheme recorded and accounted for Rs 3.77 crore in planned costs. The cashbook shows Rs 6.34 crore paid out, while spending linked to planned activities totals Rs 1.78 crore. The linked share rose from 2.7% to 53.2%; that is a change in how much spending was linked to activities, not evidence that payments increased.

For the next review, start with maintenance, village infrastructure and the older records. These are overlapping views of the same plan-to-spending gap, not amounts to add together. Maintenance accounted for Rs 4.19 crore below plan and Rs 4.25 crore in planned untied grants. The Self-sufficient Infrastructure in Village theme accounted for Rs 3.36 crore below plan and Rs 54.92 lakh below sanction, though the sanction comparison covers only activities with a sanction on file—about one in six. By year, 2020-2021 alone accounted for Rs 2.54 crore below plan.

For a check on work status, all 85 activities marked ongoing were public works. Activities marked ongoing accounted for 72.7% of recorded spending under the general component, making their progress records a useful place to start.

**plainlines_choose**

- used 8 of 13 findings, 154 words, 10 sentences, 15.4 words per sentence, 10 figures, 13% of the handed figures, 1 tries

Sharagada’s recorded spending was Rs 4.63 crore below plan, with most of the gap in maintenance. Check the missing fund details and reconcile payments with planned activities before treating the gap as unspent money.

Maintenance accounted for Rs 4.19 crore of the gap and was also the main planned use of untied grants. Looking at the same gap by theme, village infrastructure accounted for Rs 3.36 crore. It also had the largest gap against sanctions, at Rs 54.92 lakh, though that comparison covers only about one in six activities.

Start the records check with 2020-2021. It had the largest gap against plan, at Rs 2.54 crore, and the highest cashbook payments, at Rs 2.13 crore. Across the records, entries with no fund component accounted for Rs 3.77 crore of the gap. The share of cashbook spending linked to planned activities rose from 2.7% to 53.2%. That shows more complete linking, not necessarily higher spending.

### GEO-32 - Sundergarh district - what should I look at?

**current**

- used 15 of 15 findings, 299 words, 11 sentences, 27.2 words per sentence, 18 figures, 22% of the handed figures, 2 tries

**Start by reconciling plans, sanctions and payments.** In the sampled Sundargarh records, spending was Rs 2.19 crore below plan, with larger gaps in Karuabahal (Rs 1.28 crore below plan) than in Haldikudar (Rs 90.62 lakh below plan). Records with no sanctioning authority listed account for 82.8% of the plan gap, and records with no scheme listed account for 46.8% of planned cost. The comparison with sanctions covers only about one in six activities; on that narrower basis, Haldikudar has the larger gap (Rs 24.83 lakh below sanction). The share of spending linked to a planned activity went from 2.7% to 53.2%; check the cashbook before interpreting that change as higher spending.

**Review drinking water and sanitation first, and check roads separately.** Drinking water has the largest gap against plan (Rs 64.45 lakh below plan), followed by sanitation (Rs 55.17 lakh below plan). Among activities with sanctions on file, the order is reversed: sanitation has the largest gap, followed by drinking water. In untied grant plans, the village infrastructure theme accounts for 52.9% of the total, while roads are the largest individual focus area at 22.3%. Roads and drinking water have nearly equal voucher-linked spending: Rs 39.90 lakh for roads and Rs 39.63 lakh for drinking water.

**Check how works and beneficiaries are classified before comparing districts.** Sundargarh differs from the usual sample pattern for Maintenance and New/Fresh works, both in untied grant plans and in spending against plan. Its leading output codes for untied grant plans also differ from the usual pattern, and Codes 101 and 104 are lowest on the spending-against-plan measure, rather than Codes 101 and 105. Also check the theme assignments for activities with expected beneficiaries: Sundargarh has the highest expected beneficiary count among sampled districts in the unmapped theme, while Bargarh leads in most themes.

**plainlines**

- used 15 of 15 findings, 289 words, 18 sentences, 16.1 words per sentence, 17 figures, 18% of the handed figures, 2 tries

Start by reconciling plans, sanctions and payments in Karuabahal and Haldikudar. Check drinking water and sanitation first: they show the largest spending gaps against both plan and sanction in the Sundargarh sample. 

Recorded spending was Rs 2.19 crore below plan across the two Panchayats. Karuabahal had the larger gap against plan, at Rs 1.28 crore. Haldikudar had the larger gap against sanction, at Rs 24.83 lakh, but that comparison covers only about one in six activities with a sanction on file. Records with no sanctioning authority listed account for 82.8% of the gap against plan. Also check where the scheme was left blank: those records account for Rs 1.81 crore in planned costs. 

For the untied grant review, look first at village infrastructure. Theme 6 accounts for 52.9% of planned untied grants. By focus area, roads had the largest untied grant allocation, followed by drinking water. The two were nearly level in voucher-linked spending: Rs 39.90 lakh for roads and Rs 39.63 lakh for drinking water. The share of spending linked to a planned activity rose from 2.7% to 53.2%. Check the cashbook before treating that rise as an increase in spending. 

At the next review, ask how work types and output codes are assigned locally. Unlike most districts in the sample, Sundargarh does not follow the usual Maintenance and New/Fresh pattern for untied grant plans or for spending against plan. It also differs from the usual Code 101 and Code 105 pattern for untied grant plans. For spending against plan, its lowest output types are Code 101 and Code 104, rather than Code 101 and Code 105. Check the theme labels too: Sundargarh has the highest expected beneficiary count among sampled districts for activities without a mapped theme.

**current_choose**

- used 13 of 15 findings, 274 words, 12 sentences, 22.8 words per sentence, 18 figures, 22% of the handed figures, 1 tries

Start by reconciling the plan, sanction and payment records for Karuabahal and Haldikudar. In the sampled Sundargarh records, spending was Rs 2.19 crore below plan, with a larger gap in Karuabahal (Rs 1.28 crore below plan) than in Haldikudar (Rs 90.62 lakh below plan). Records with no sanctioning authority on file account for 82.8% of the plan gap. Check the scheme details as well: 967 entries have no scheme recorded, representing Rs 1.81 crore in planned costs. The comparison with sanctions covers only about one in six activities; on that narrower basis, Haldikudar has the larger gap (Rs 24.83 lakh below sanction).

Prioritise drinking water and sanitation in that reconciliation. They have the largest spending gaps against plan—Rs 64.45 lakh below plan for drinking water and Rs 55.17 lakh below plan for sanitation —and also the largest gaps against recorded sanctions, with sanitation first on that measure. Check payment links against the cashbook before drawing conclusions about spending trends: the share linked to a planned activity rose from 2.7% to 53.2%, but better linkage alone does not show that spending rose.

For the planning review, look at village infrastructure and roads. The self-sufficient village infrastructure theme accounts for 52.9% of planned untied grants. Roads are the largest individual focus area at Rs 57.84 lakh in planned untied grants and also the largest for voucher-linked spending at Rs 39.90 lakh. Check how works and outputs are classified locally: Sundargarh differs from the common district pattern for planned untied grants by work and output type, and its lowest spending against plan by output type is in Codes 101 and 104, rather than Codes 101 and 105.

**plainlines_choose**

- used 8 of 15 findings, 177 words, 13 sentences, 13.6 words per sentence, 12 figures, 16% of the handed figures, 1 tries

In the Sundargarh sample, start by reconciling spending with plans and checking records with no sanctioning authority listed. Review drinking water and sanitation first: they have the largest gaps against plan. 

Spending was Rs 2.19 crore below plan across the two sampled Gram Panchayats. Karuabahal was Rs 1.28 crore below plan, and Haldikudar was Rs 90.62 lakh below plan. Records with no sanctioning authority listed account for Rs 1.81 crore of the gap (82.8%). Also check the scheme entries: 967 records have no scheme listed. 

Keep the comparison with sanctions separate. Only about one in six activities had a sanction record on file. Among those activities, Haldikudar had the larger gap: Rs 24.83 lakh below sanction, compared with Rs 12.82 lakh in Karuabahal. Sanitation and drinking water also had the largest gaps against sanction. 

For the planning review, look at what is grouped under village infrastructure. The theme accounts for 52.9% of planned untied grants but 20.9% of activities. By focus area, roads had the largest share of planned untied grants (22.3%), followed by drinking water (13.8%).

### MEA-05 - How is the tied grant behaving?

**current**

- used 20 of 20 findings, 279 words, 15 sentences, 18.6 words per sentence, 30 figures, 21% of the handed figures, 2 tries

Tied-grant plans are broadly spread across the sampled Gram Panchayats, but the same output codes tend to lead. Records classified under the Tied Grant component show Rs 10.91 crore in planned funding, with Sharagada holding the largest share at 10.3%. Code 101 accounts for a majority of planned tied-grant funding across the sample. Code 101 and Code 105 lead in 18/20 Gram Panchayats; Dadhapatna and Dutimendi are the exceptions.

Annual plans show some shifts in where the money is concentrated. Planned funding was Rs 3.12 crore in 2020-2021, Rs 3.26 crore in 2021-2022, and Rs 3.13 crore in 2022-2023, before falling to Rs 2.46 crore in 2023-2024 and then rising to Rs 2.52 crore in 2024-2025 and Rs 3.18 crore in 2025-2026. In that latest year, Bheden accounted for 25.0% of planned funding and 8.2% of activities. Bheden also had the largest funding share for new works and for activities marked approved, while Sharagada led for maintenance and ongoing works. Funding planned for Scheduled Tribe beneficiaries was especially concentrated: Kalyansinghpur accounted for 95.8%.

Sanction records are a priority for reconciliation. The Sarpanch accounts for 56.7% of planned funding within the Tied Grant component and a majority in 5/6 fiscal years. The exception was 2020-2021, when the largest share, 35.7%, had no sanctioning authority recorded. Authority was also missing for 45.6% of planned tied-grant funding under the Clean and Green Village theme and for Rs 37.70 lakh in Sharagada, where the Gram Panchayat was the main authority on file. Separately, where the Gram Panchayat was recorded as the sanctioning authority, tied-grant spending was Rs 29.10 lakh below plan. That shortfall is specific to those records, not a statewide spending measure.

**plainlines**

- used 20 of 20 findings, 260 words, 16 sentences, 16.2 words per sentence, 36 figures, 24% of the handed figures, 2 tries

Planned tied grant is generally spread across the sampled Gram Panchayats, but Bheden stands out in 2025-2026. The Sarpanch accounts for most of the planned amount in 5/6 fiscal years. 

In the records listed under the Tied Grant component, plans total Rs 10.91 crore across 19 Gram Panchayats. Sharagada has the largest share at 10.3%. Annual plans totalled Rs 3.12 crore in 2020-2021, Rs 3.26 crore in 2021-2022 and Rs 3.13 crore in 2022-2023. They fell to Rs 2.46 crore in 2023-2024, then rose to Rs 2.52 crore in 2024-2025 and Rs 3.18 crore in 2025-2026. In that latest year, Bheden accounted for 25.0% of the planned amount but 8.2% of activities. 

Bheden also has the largest share of planned tied grant for approved activities (19.5%) and new works (13.3%). Sharagada leads for maintenance (22.7%) and ongoing works (8.7%). Code 101 accounts for most of the planned amount across the sample. Codes 101 and 105 lead in 18/20 Gram Panchayats, with Dadhapatna and Dutimendi showing a different pattern. Kalyansinghpur accounts for 95.8% of the amount planned for works marked as serving Scheduled Tribes. 

The Sarpanch accounts for 56.7% of the amount planned under the Tied Grant component. The exception to the yearly pattern is 2020-2021, when no sanctioning authority was recorded for 35.7% of the planned amount, the largest share. Missing authority records are also worth checking for Clean and Green Village works (Rs 4.02 crore) and in Sharagada (Rs 37.70 lakh). Where the Gram Panchayat was recorded as the sanctioning authority, tied-grant spending was Rs 29.10 lakh below plan.

**current_choose**

- used 10 of 20 findings, 231 words, 13 sentences, 17.8 words per sentence, 20 figures, 14% of the handed figures, 1 tries

Tied-grant plans are generally spread across the sampled Gram Panchayats, but Bheden stands out in the latest year shown. Records classified under the Tied Grant fund component show Rs 10.91 crore planned across 19 Gram Panchayats, with Sharagada holding the largest share at 10.3%. In 2025-2026, Bheden accounted for 25.0% of planned tied-grant funding and 8.2% of activities. The work-type breakdowns show two other concentrations worth reviewing: Bheden accounts for 13.3% of planned tied-grant funding for new works, and Sharagada accounts for 22.7% for maintenance.

The same output codes recur across the sample. Code 101 accounts for the majority of planned tied-grant funding across the sampled panchayats. Codes 101 and 105 lead in 18/20 Gram Panchayats, with Dadhapatna and Dutimendi showing a different pattern.

Sanctioning records are a priority for reconciliation. The Sarpanch accounts for the majority of planned tied-grant funding in 5/6 fiscal years. The exception is 2020-2021, when 35.7% of planned funding had no sanctioning authority on file. The gap is particularly large for Clean and Green Village activities, where 45.6% of planned tied-grant funding had no sanctioning authority recorded.

On spending, tied-grant activities for which the Gram Panchayat was listed as the sanctioning authority were Rs 29.10 lakh below plan, compared with Rs 22.69 lakh below plan for untied-grant activities under the same authority. This is a specific set of records to reconcile, not a statewide spending estimate.

**plainlines_choose**

- used 11 of 20 findings, 208 words, 12 sentences, 17.3 words per sentence, 23 figures, 16% of the handed figures, 1 tries

Planned tied grant funding is generally spread across the sampled Gram Panchayats, but Bheden stands out in 2025-2026. Sarpanches account for most of the planned amount in 5/6 fiscal years.

The sample’s planned total rose from Rs 2.52 crore in 2024-2025 to Rs 3.18 crore in 2025-2026. In the latter year, Bheden accounted for 25.0% of the planned amount (Rs 79.27 lakh), compared with 8.2% of the activities. The work-type breakdown shows two places to look more closely: Bheden had the largest share for new works, at 13.3%, while Sharagada led for maintenance, at 22.7%.

The types of outputs funded in the plans are more consistent. Code 101 accounts for most of the planned amount across the sample. Codes 101 and 105 lead in 18/20 Gram Panchayats, with Dadhapatna and Dutimendi the exceptions.

For the next review, check missing sanction records and compare spending with plans. In 2020-2021, the exception to the usual Sarpanch pattern, no sanctioning authority was recorded for 35.7% of the planned amount (Rs 1.11 crore). The same field was missing for 45.6% of the planned amount (Rs 4.02 crore) under Clean and Green Village. Separately, where the Gram Panchayat was recorded as the sanctioning authority, tied grant spending was Rs 29.10 lakh below plan.

### MEA-09 - Anything on administrative approval?

**current**

- used 17 of 17 findings, 276 words, 14 sentences, 19.7 words per sentence, 30 figures, 40% of the handed figures, 1 tries

The Sarpanch was the sanctioning authority for most activities with administrative approval in every fiscal year and recorded the highest count in 6/7 themes. The exception was Poverty Free and Enhanced Livelihoods Village, where no clear pattern emerged. Drinking water and Sanitation were the leading focus areas in every fiscal year. The XV Finance Commission accounted for most approved activities in 5/6 fiscal years, with no clear pattern in 2024-2025. In that same year, average approval records per Gram Panchayat-year peaked in 2/3 social composition groups, but not in the Mixed group, where there was no clear pattern.

Chikilli stands out for a records review: it had the lowest count of activities with administrative approval in 5/6 fiscal years, with no clear pattern in 2023-2024. It was also the only sampled Gram Panchayat where Code 101 did not account for a majority of approved activities. Ongoing work accounted for most approved activities in 17/20 Gram Panchayats; Chikilli, Boipariguda and Laxmipur showed no clear pattern. Codes 101 and 105 led in 7/9 districts; in Sundargarh and Malkangiri, Codes 101 and 104 led instead. Code 105 had 558 approved activities, with no one Gram Panchayat standing out, while Code 110 had just 2, one each in Boipariguda and Kalimela.

In the Village with Good Governance theme, all 67 approved activities were public works. Most were in GP Office Infrastructure (53 activities), recorded under the General beneficiary category (52 activities), or funded through untied grants (63 activities). Laxmipur had the largest block count, with 21 approved activities. By contrast, the Near distance band’s share of approval records in the sample (68.9%) was close to its share of activities (70.2%).

**plainlines**

- used 17 of 17 findings, 278 words, 19 sentences, 14.6 words per sentence, 32 figures, 42% of the handed figures, 2 tries
- **LOST** on 2_numerals_cited. The officer would see the plain stored sentences. What the writer wrote on its last try:

In the sample, Sarpanches were the sanctioning authority for most activities with administrative approval in every fiscal year. Drinking water and Sanitation led among focus areas every year. 

Sarpanches also led among sanctioning authorities in 6/7 themes, with no clear pattern in the poverty and livelihoods theme. The XV Finance Commission accounted for most approved activities in 5/6 fiscal years, with no clear pattern in 2024-2025. In that same year, average approval records per Gram Panchayat-year peaked in 2/3 social composition groups; the Mixed group showed no clear pattern. 

Chikilli is worth a closer look. It had the fewest activities with administrative approval in 5/6 fiscal years, with no clear pattern in 2023-2024. It was also the only exception to Code 101 making up most approved activities in 19/20 Gram Panchayats. Ongoing works made up most approved activities in 17/20 Gram Panchayats; Chikilli, Boipariguda and Laxmipur showed no clear pattern. 

Codes 101 and 105 led in 7/9 districts. In Sundargarh and Malkangiri, Codes 101 and 104 led instead. The 558 approved activities under Code 105 were spread across Gram Panchayats, with no single Panchayat standing out. Code 110 had just 2 approved activities, one each in Boipariguda and Kalimela. 

In the Village with Good Governance theme, all 67 activities with administrative approval were public works. GP Office Infrastructure accounted for 53 activities. The largest group the work was listed for was General, with 52 activities. Untied grants were recorded for 63 activities. Laxmipur had the largest block count, at 21 activities. 

The distance split was close to the split for activities overall: the Near band held 68.9% of approval records and 70.2% of the activities in that comparison.

**current_choose**

- used 11 of 17 findings, 197 words, 9 sentences, 21.9 words per sentence, 20 figures, 32% of the handed figures, 1 tries

In the sample, the Sarpanch was the sanctioning authority for most activities with administrative approval in every fiscal year. Drinking water and Sanitation were the leading focus areas in every year, and the XV Finance Commission accounted for most approved activities in 5/6 fiscal years, with no clear pattern in 2024-2025.

Chikilli is a priority for the next records review: it had the fewest activities with administrative approval in 5/6 fiscal years, with no clear pattern in 2023-2024. It was also the only sampled Gram Panchayat where Code 101 did not account for a majority of approved activities. At district level, Codes 101 and 105 led in 7/9 districts; in Sundargarh and Malkangiri, Codes 101 and 104 led instead. Approved activities were mostly recorded as ongoing in 17/20 Gram Panchayats, with no clear pattern in Boipariguda, Chikilli or Laxmipur.

Under the Village with Good Governance theme, all 67 activities with administrative approval were public works. GP Office Infrastructure accounted for 53 activities, and 63 activities were recorded under untied grants. Laxmipur is worth checking at the block review: it accounted for 31.3% of approved activities under the theme, compared with 4.0% of all activities under the theme.

**plainlines_choose**

- used 11 of 17 findings, 185 words, 11 sentences, 16.8 words per sentence, 24 figures, 32% of the handed figures, 2 tries

Yes. In the sample, the Sarpanch accounted for the majority of activities with administrative approval in every fiscal year. Drinking water and Sanitation were the leading focus areas in every year.

The Sarpanch also led among sanctioning authorities in 6/7 themes, with no clear pattern in Theme 1 - Poverty Free and Enhanced Livelihoods Village. The XV Finance Commission accounted for the majority of approved activities in 5/6 fiscal years, with no clear pattern in 2024-2025.

Code 101 accounted for the majority of approved activities in 19/20 Gram Panchayats, with no clear pattern in Chikilli. Chikilli also had the fewest approved activities in 5/6 fiscal years, with no clear pattern in 2023-2024. Code 101 and Code 105 led in 7/9 districts; in Sundargarh and Malkangiri, Code 104 took the place of Code 105. Ongoing work accounted for the majority of approved activities in 17/20 Gram Panchayats, with no clear pattern in Boipariguda, Chikilli or Laxmipur.

In Theme 8 - Village with Good Governance, all 67 approved activities were public works. GP Office Infrastructure accounted for 53 activities, and 63 activities were recorded under untied grants.

### VAG-06 - Anything worth my attention this quarter?

**current**

- used 11 of 11 findings, 269 words, 14 sentences, 19.2 words per sentence, 28 figures, 36% of the handed figures, 1 tries

Start the quarterly review with Bargarh and Ganjam: they recorded the lowest spending against plan among districts in 6/7 themes in the sample. For Water Sufficient Village, the lowest were Ganjam and Malkangiri. Ganjam also accounted for 63.8% (Rs 1.71 crore) of the Child Friendly Village shortfall, compared with 28.6% of the activities.

Some gaps warrant a wider review; others point to specific records to check. Self-sufficient Infrastructure was Rs 20.13 crore below plan across 16 blocks, with the largest gaps in Sheragada (Rs 3.36 crore) and Rangeilunda (Rs 3.11 crore). Clean and Green Village was Rs 8.62 crore below plan across 20 Gram Panchayats; Biswamathpur had the largest gap at Rs 2.15 crore, but most of the gap was elsewhere. Rural housing was much more concentrated: Boipariguda accounted for 95.7% (Rs 2.13 crore) of the sample’s rural housing gap. Review those records alongside Boipariguda’s drinking water spending, which was Rs 1.26 crore below plan.

For Village with Good Governance, reconcile spending with sanction records before interpreting the Rs 2.41 crore gap. Buildings accounted for 68.6% (Rs 1.66 crore) of that gap, while records with no sanctioning authority on file accounted for 91.3% (Rs 2.20 crore). These are separate views of the same gap, not amounts to add.

Check the cashbook before treating increases in spending linked to plans as increases in actual spending. The linked share rose from 2.7% to 53.2% over the period reviewed, and linked spending increased over time in 6/9 districts; Bargarh, Koraput and Cuttack showed different patterns. Separately, 2026-Q1 was unusually high on 8/9 measures, but spending linked to planned activities was the exception.

**plainlines**

- used 11 of 11 findings, 246 words, 18 sentences, 13.7 words per sentence, 19 figures, 24% of the handed figures, 1 tries

Yes. Start with infrastructure spending against plan, then check Boipariguda’s housing records and the missing sanctioning authority entries under Good Governance. 

Infrastructure spending in the sample was Rs 20.13 crore below plan across 16 blocks. Sheragada and Rangeilunda had the largest gaps, but the gap was spread across blocks. Clean and Green Village showed a similar spread: spending was Rs 8.62 crore below plan, with the largest gap in Biswamathpur. 

Elsewhere, the gaps point to specific places to review. Boipariguda accounted for 95.7% of the sample’s rural housing gap, with spending Rs 2.13 crore below plan. Its drinking water spending was also Rs 1.26 crore below plan. For the district review, start with Ganjam and Bargarh: they had the lowest spending against plan in 6/7 themes. Water Sufficient Village was the exception, with Ganjam and Malkangiri lowest. Ganjam alone accounted for 63.8% of the Child Friendly Village gap. 

Under Good Governance, buildings accounted for 68.6% of the spending gap. In a separate breakdown of the same gap, 91.3% was on records with no sanctioning authority listed. Check those entries against the sanction records. 

For the quarterly review, check the cashbook before reading more payments linked to plans as higher spending. The share of spending linked to planned activities rose from 2.7% to 53.2% over six years. Linked spending rose over time in 6/9 districts; Bargarh, Koraput and Cuttack followed different patterns. It also did not show the unusually high reading seen in 8/9 measures in 2026-Q1.

**current_choose**

- used 11 of 11 findings, 265 words, 18 sentences, 14.7 words per sentence, 21 figures, 27% of the handed figures, 2 tries

Start the review with Ganjam and Bargarh. In the sample, they were the lowest-spending districts relative to plan in 6/7 themes. Water Sufficient Village was the exception: Ganjam and Malkangiri were lowest. Ganjam also accounted for 63.8% of the Child Friendly Village gap, with spending Rs 1.71 crore below plan.

Give infrastructure and clean-and-green works a broader review. Spending on Self-sufficient Infrastructure in Village was Rs 20.13 crore below plan across 16 blocks. Sheragada and Rangeilunda had the largest gaps, but the shortfall was spread across blocks. Clean and Green Village spending was Rs 8.62 crore below plan, with Biswamathpur recording the largest gap. Rural housing calls for a more targeted check: Boipariguda alone accounted for 95.7% of the sample’s rural housing gap, at Rs 2.13 crore below plan. Its drinking water spending was also Rs 1.26 crore below plan.

For Village with Good Governance, reconcile spending against plans and check the sanction records together. Of the Rs 2.41 crore gap, Rs 1.66 crore was in buildings, while Rs 2.20 crore was on records with no sanctioning authority listed. These are two views of the same gap, not amounts to add together.

Check the cashbook before reading the quarterly figures as a rise in spending. In 2026-Q1, 8/9 measures were unusually high; spending linked to a planned activity was the exception. Linked spending was trending up in 6/9 districts, with Bargarh, Koraput and Cuttack showing different patterns. Over the period reviewed, the share of spending linked to plans rose from 2.7% to 53.2%. That shows more complete linking in the records, not necessarily more spending.

**plainlines_choose**

- used 10 of 11 findings, 253 words, 15 sentences, 16.9 words per sentence, 20 figures, 25% of the handed figures, 2 tries

Yes. Start by checking the gaps between plans and recorded spending in Bargarh and Ganjam, then reconcile the rural housing records in Boipariguda and the missing sanctioning authority entries under Village with Good Governance.

In the sample, Bargarh and Ganjam had the lowest spending against plan in 6/7 themes. Water Sufficient Village was the exception: Ganjam and Malkangiri were lowest. For Child Friendly Village, Ganjam alone accounted for 63.8% of the gap (Rs 1.71 crore below plan).

Some gaps call for a focused check; others need a wider review. Boipariguda accounted for 95.7% of the rural housing gap (Rs 2.13 crore below plan). Under Village with Good Governance, buildings accounted for 68.6% of the gap. Looking at the same theme by sanctioning authority, entries with no authority on file accounted for 91.3% of the gap (Rs 2.20 crore below plan). By contrast, Self-sufficient Infrastructure in Village was Rs 20.13 crore below plan across 16 blocks, with no single block dominating. The Clean and Green Village gap of Rs 8.62 crore was also spread across Gram Panchayats.

For the quarterly review, check the cashbook before treating more payments linked to plans as evidence of higher spending. In 2026-Q1, 8/9 measures were unusually high, but spending linked to planned activities was the exception. Over time, linked spending rose in 6/9 districts; Bargarh, Koraput and Cuttack followed different patterns. The share of spending linked to plans rose from 2.7% to 53.2% over six years, so the linked figures alone do not show whether total spending rose.

### OPN-01 - How is GPDP implementation going under XV FC?

**current**

- used 9 of 9 findings, 202 words, 9 sentences, 22.4 words per sentence, 18 figures, 32% of the handed figures, 2 tries

Under the XV Finance Commission, the sampled Gram Panchayats recorded 1,502 planned activities with a planned cost of Rs 19.83 crore across 19 Gram Panchayats. The plan included Rs 10.91 crore in tied grants, and recorded spending for the general component was Rs 19.51 crore. Recorded sanctions totalled Rs 19.80 crore, but only about one in six activities had a sanction record on file. The closeness of the planned and sanctioned totals should therefore not be read as confirmation that most activities were sanctioned.

Recorded spending was Rs 3.61 crore below plan across the 19 Gram Panchayats. XV FC had the lowest spending relative to plan among the schemes compared in 5/6 fiscal years; the exception was 2024-2025, when there was no clear pattern. The shortfall was spread across Gram Panchayats, but Sharagada merits a closer look: it accounted for 18.7% of the shortfall (Rs 67.77 lakh below plan) and 4.7% of planned activities.

For the next review, reconcile plan, sanction and spending records, starting with Sharagada, and verify work status separately. The records list 9 XV FC activities under approval across the 19 Gram Panchayats; in Govindapur, XV FC accounted for 50 of the 69 activities recorded as ongoing across schemes.

**plainlines**

- used 9 of 9 findings, 147 words, 9 sentences, 16.3 words per sentence, 17 figures, 34% of the handed figures, 2 tries

In the sample, XV FC spending was Rs 3.61 crore below plan across 19 Gram Panchayats. XV FC had the lowest spending against plan among the schemes compared in 5/6 fiscal years, with no clear pattern in 2024-2025.

The spending gap was spread across the panchayats. Sharagada had the largest gap, at Rs 67.77 lakh below plan, followed by Dutimendi at Rs 39.63 lakh below plan.

The plans listed 1,502 activities at a planned cost of Rs 19.83 crore, with Rs 10.91 crore planned under tied grants. Recorded spending in the general component was Rs 19.51 crore. Sanctions on file totalled Rs 19.80 crore, but that figure covers only activities with a sanction record, about one in six.

The records list 9 XV FC activities under approval, including 3 in Bandhpali and 2 in Haldikudar. In Govindapur, XV FC accounted for 50 of the 69 ongoing activities.

**current_choose**

- used 7 of 9 findings, 191 words, 9 sentences, 21.2 words per sentence, 12 figures, 24% of the handed figures, 1 tries

In the sample, GPDP spending under the XV Finance Commission was Rs 3.61 crore below plan across 19 Gram Panchayats. Compared with other schemes in the sample, XV FC had the lowest spending against plan in most fiscal years (5/6); 2024-2025 was the exception, with no clear pattern. The shortfall was spread across the panchayats, with the largest gaps in Sharagada (Rs 67.77 lakh below plan) and Dutimendi (Rs 39.63 lakh below plan). These are useful starting points for reconciling spending with plans, but the review should not be limited to them.

The records give a clearer picture of planning than of completion. They show 1,502 planned activities with a planned cost of Rs 19.83 crore. The recorded sanctioned amount was Rs 19.80 crore, but it covers only activities with a sanction record on file—about one in six—so the closeness of the amounts should not be read as evidence that nearly all planned activities were sanctioned. The records list 9 activities under approval across the scheme and 50 ongoing XV FC activities in Govindapur alone. At the next review, check sanction coverage and confirm work status before drawing conclusions about completion.

**plainlines_choose**

- used 5 of 9 findings, 118 words, 9 sentences, 13.1 words per sentence, 12 figures, 24% of the handed figures, 1 tries

In the sample, XV Finance Commission spending was Rs 3.61 crore below plan. It had the lowest spending against plan among schemes in 5/6 fiscal years. There was no clear pattern in 2024-2025.

The spending gap was spread across 19 Gram Panchayats. Sharagada had the largest gap at Rs 67.77 lakh below plan, followed by Dutimendi at Rs 39.63 lakh below plan. The remaining 17 together were Rs 2.54 crore below plan.

The plans listed 1,502 activities at a total cost of Rs 19.83 crore. The recorded sanction total was Rs 19.80 crore, but only about one in six activities had a sanction record on file. The close totals therefore do not show how widely activities were sanctioned.

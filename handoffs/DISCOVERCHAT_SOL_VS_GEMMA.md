# DiscoverChat: Sol vs Gemma 4 31B on three questions

*Measured 2026-09-14. One run per version. Nothing in the repo was changed to produce it.*

## The short version

- **As a writer, Gemma costs some polish, not accuracy.** Given the same findings, it passed the number check on the first draft for both questions and got every figure right. What is lost is Sol's judgement about what matters: Sol points the officer at the thing to raise, Gemma lists everything evenly.
- **As the finding-picker, the drop is bigger.** Gemma keeps too much (20 and 13 findings against Sol's 8 and 4), so answers turn into long lists padded with side facts. On the "why" question it found records Sol missed. It has not been tested on questions it should refuse.
- **Gemma writes markdown, which the Discover tab does not display.** Officers would see literal asterisks, and bullets run together into paragraphs (details below). Either way Gemma is used, this needs a "plain paragraphs only" line in the writer prompt, or the formatting stripped before display.
- **The money is in the picker.** Changing only the writer saves about 2 cents a question, out of about 9 cents. Changing both brings a question under 1 cent.

**Recommendation.** If cost matters, trying Gemma as the writer only is reasonable, once the plain-text fix is in. Do not switch the finding-picker without first re-running the tests that check it refuses out-of-scope questions (`DiscoverChat/experiments/run_judge_arm.py` and `run_decompose_oos.py --repeats 4`). The picker's model id is tied to that evidence by a gate check, so the gate would also go red until it is re-run.

## What was run

Each question was run three ways:

- **A:** Sol picks, Sol writes (what runs today)
- **B:** Sol's picks, Gemma writes (the writing on its own)
- **C:** Gemma picks, Gemma writes (a full switch)

Sol does two jobs in DiscoverChat: it picks which findings answer the question (the "judge"), then writes the answer. Version B keeps Sol's picks so the writing can be compared on its own. Version C shows what a full switch would give.

- **Code and data:** the committed DiscoverChat, run from the `C:\dev\odisha-d11b` mirror (identical to the committed `DiscoverChat/` and `Insights/src/`, and the same corpus stamps).
- **Held constant:** the question classifier (`gpt-5.4-nano`) and the question embedding (computed once per question and reused), so only the picking and writing models differ.
- **Sol:** `gpt-5.6-sol` through OpenAI, $4 in / $20 out per million tokens. This is a temporary offer that OpenAI says runs at least until 21 Nov 2026; the later price is not published.
- **Gemma:** `google/gemma-4-31b-it` through OpenRouter, $0.09 in / $0.34 out per million tokens, default settings (no extended thinking turned on).
- **Prompts:** unchanged. Gemma got exactly the prompts Sol gets.

## Results at a glance

| Question | Version | Findings | Drafts | Officer sees | Model time | Cost |
|---|---|--:|--:|---|--:|--:|
| How is Barpali block doing? | A | 8 | 1 | Written answer | 22.8 s | $0.0787 |
| How is Barpali block doing? | B | 8 | 1 | Written answer | 21.2 s | $0.0004 |
| How is Barpali block doing? | C | 20 | 2 | Written answer (2nd draft) | 237.1 s | $0.0028 |
| Is spending on track? | A | 4 | 1 | Written answer | 27.3 s | $0.0887 |
| Is spending on track? | B | 4 | 1 | Written answer | 6.3 s | $0.0002 |
| Is spending on track? | C | 13 | 2 | Written answer (2nd draft) | 47.7 s | $0.0029 |
| Why is spending low in Chikilli? | A | 0 | – | Fixed "why" reply | 6.4 s | $0.0573 |
| Why is spending low in Chikilli? | C | 10 | – | Fixed "why" reply | 9.9 s | $0.0014 |

Cost for all three questions: A $0.2247, B $0.0006 (writing only), C $0.0071. "Model time" adds up the picking and writing calls; it leaves out the classifier (about 1 s) and the embedding.

## Question 1: How is Barpali block doing?

### What I noticed

**Writing (A vs B, same 8 findings).** Both are accurate and both passed the number check on the first draft. Sol reads like a briefing: it names planning-record completeness as the main issue and flags the 6 activities awaiting approval in Bandhpali for the next review. Gemma reads like a tidy report: headings and bullets, every figure in its place, but it leaves the officer to decide what matters. Gemma also included the sanctioned total (Rs 2.96 crore), which Sol left out.

**Picking (C).** Gemma kept 22 findings, which the 20-finding cap cut to 20. About half are off the point for "how is Barpali doing": primary schools, a bank, wards, general-category population. The answer became a long list. Its first draft failed the number check, and the version that passed says 171 activities "started" and 171 "ongoing" as two separate bullets. Gemma's picking call took 195 s on this question.

### A: Sol picks, Sol writes (what runs today)

8 findings · 22.8 s of model time · $0.0787 · officer sees: Written answer

Picking: `gpt-5.6-sol`, 11.9 s, reading 12,161 tokens of candidate findings.

What the officer would read:

> In the sample, Barpali records Rs 2.64 crore of spending across 1,447 activities and accounts for 48.4% of Bargarh district’s Rs 5.44 crore spending across the three sampled blocks. Spending is broadly balanced between Bandhpali at Rs 1.40 crore and Bhatigaon at Rs 1.24 crore, in line with their similar shares of activities.
>
> The main issue for review is planning-record completeness. Of the activities, 1,067 are planned without a cost—539 in Bandhpali and 528 in Bhatigaon—and sanction records cover only about one in six activities. Recorded spending is Rs -2.85 crore against plan, indicating spending below plan; Bandhpali accounts for Rs -1.94 crore and Bhatigaon for Rs -90.49 lakh. Spending linked to planned activities totals Rs 2.55 crore, while the linked share increased from 2.7% to 53.2% across six years, pointing to improved recording completeness unless cashbook spending rose alongside it.
>
> Operationally, 171 activities are ongoing, split closely between Bhatigaon with 88 and Bandhpali with 83. All 6 activities under approval are in Bandhpali, with none in Bhatigaon, which merits checking at the next review.
>
> (as of 2026-09-11)

<details><summary>Findings picked (8)</summary>

1. `d4-00583` Within block Barpali, spending totals Rs 2.64 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 53.1% (Rs 1.40 crore), then Bhatigaon at 46.9% (Rs 1.24 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 53.1% of spending -- a group's total grows with how much of the work it holds.
2. `d4-00584` Within block Barpali, spending measured against plan totals Rs -2.85 crore across 2 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Bandhpali accounts for 68.2% of it (Rs -1.94 crore). The one remaining, Bhatigaon, accounts for Rs -90.49 lakh. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 68.2% of spending measured against plan -- a group's total grows with how much of the work it holds.
3. `d3-00244` Within block Barpali, activities ongoing totals 171 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bhatigaon at 51.5% (88 activities), then Bandhpali at 48.5% (83 activities). For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 51.5% of activities ongoing -- a group's total grows with how much of the work it holds.
4. `d1-09528` Within block Barpali, activities under approval totals 6 activities across 2 Gram Panchayats. It is concentrated: Bandhpali accounts for 100.0% of it (6 activities). The one remaining, Bhatigaon, accounts for 0 activities. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 100.0% of activities under approval -- a group's total grows with how much of the work it holds.
5. `d2-00151` Within block Barpali, spending linked to a planned activity totals Rs 2.55 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 52.8% (Rs 1.34 crore), then Bhatigaon at 47.2% (Rs 1.20 crore). For size: Bandhpali holds 44.3% of the 440 vouchers behind these totals, against 52.8% of spending linked to a planned activity -- a group's total grows with how much of the work it holds. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
6. `d4-00580` Within block Barpali, activities planned without a cost totals 1,067 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 50.5% (539 activities), then Bhatigaon at 49.5% (528 activities). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 50.5% of activities planned without a cost -- a group's total grows with how much of the work it holds.
7. `d1-09520` Within block Barpali, sanctioned amount totals Rs 2.96 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 54.6% (Rs 1.62 crore), then Bhatigaon at 45.4% (Rs 1.34 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 54.6% of sanctioned amount -- a group's total grows with how much of the work it holds. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
8. `d4-02188` Within district Bargarh, spending totals Rs 5.44 crore across 3 blocks. It is spread across them without one standing out: the largest is Barpali at 48.4% (Rs 2.64 crore), then Bheden at 29.7% (Rs 1.62 crore). The one remaining, Attabira, accounts for Rs 1.19 crore. For size: Barpali holds 47.3% of the 3,062 activities behind these totals, against 48.4% of spending -- a group's total grows with how much of the work it holds.

</details>

### B: Sol's picks, Gemma writes (the writing on its own)

8 findings · 21.2 s of model time · $0.0004 · officer sees: Written answer

What the officer would read:

> As of 2026-09-11, the analysis of Barpali block shows the following patterns:
>
> **Financial Overview and Planning**
> Total spending in Barpali block is Rs 2.64 crore, representing 48.4% of the total spending of Rs 5.44 crore across the three blocks of Bargarh district. This spending is distributed between two Gram Panchayats: Bandhpali (Rs 1.40 crore) and Bhatigaon (Rs 1.24 crore). However, spending measured against plan is negative across the block, totaling Rs -2.85 crore. This is primarily concentrated in Bandhpali, which accounts for Rs -1.94 crore (68.2% of the block total), while Bhatigaon accounts for Rs -90.49 lakh.
>
> **Activity and Sanction Records**
> There is a significant gap in cost recording: 1,067 activities were planned without a cost, split almost evenly between Bandhpali (539 activities) and Bhatigaon (528 activities). The total sanctioned amount for the block is Rs 2.96 crore, with Rs 1.62 crore in Bandhpali and Rs 1.34 crore in Bhatigaon; notably, sanction records are only available for about one in six activities.
>
> **Work Progress and Approvals**
> Current activity levels are as follows:
> * **Ongoing:** There are 171 ongoing activities, with 88 in Bhatigaon and 83 in Bandhpali.
> * **Under Approval:** There are 6 activities currently under approval, all of which are located in Bandhpali.
>
> **Recording Completeness**
> Spending linked to a planned activity totals Rs 2.55 crore, split between Bandhpali (Rs 1.34 crore) and Bhatigaon (Rs 1.20 crore). The linked share of spending has increased from 2.7% to 53.2% over the last six years.

<details><summary>Findings picked (8)</summary>

1. `d4-00583` Within block Barpali, spending totals Rs 2.64 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 53.1% (Rs 1.40 crore), then Bhatigaon at 46.9% (Rs 1.24 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 53.1% of spending -- a group's total grows with how much of the work it holds.
2. `d4-00584` Within block Barpali, spending measured against plan totals Rs -2.85 crore across 2 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Bandhpali accounts for 68.2% of it (Rs -1.94 crore). The one remaining, Bhatigaon, accounts for Rs -90.49 lakh. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 68.2% of spending measured against plan -- a group's total grows with how much of the work it holds.
3. `d3-00244` Within block Barpali, activities ongoing totals 171 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bhatigaon at 51.5% (88 activities), then Bandhpali at 48.5% (83 activities). For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 51.5% of activities ongoing -- a group's total grows with how much of the work it holds.
4. `d1-09528` Within block Barpali, activities under approval totals 6 activities across 2 Gram Panchayats. It is concentrated: Bandhpali accounts for 100.0% of it (6 activities). The one remaining, Bhatigaon, accounts for 0 activities. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 100.0% of activities under approval -- a group's total grows with how much of the work it holds.
5. `d2-00151` Within block Barpali, spending linked to a planned activity totals Rs 2.55 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 52.8% (Rs 1.34 crore), then Bhatigaon at 47.2% (Rs 1.20 crore). For size: Bandhpali holds 44.3% of the 440 vouchers behind these totals, against 52.8% of spending linked to a planned activity -- a group's total grows with how much of the work it holds. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
6. `d4-00580` Within block Barpali, activities planned without a cost totals 1,067 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 50.5% (539 activities), then Bhatigaon at 49.5% (528 activities). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 50.5% of activities planned without a cost -- a group's total grows with how much of the work it holds.
7. `d1-09520` Within block Barpali, sanctioned amount totals Rs 2.96 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 54.6% (Rs 1.62 crore), then Bhatigaon at 45.4% (Rs 1.34 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 54.6% of sanctioned amount -- a group's total grows with how much of the work it holds. The sanctioned basis covers only the activities with a sanction record on file, about one in six.
8. `d4-02188` Within district Bargarh, spending totals Rs 5.44 crore across 3 blocks. It is spread across them without one standing out: the largest is Barpali at 48.4% (Rs 2.64 crore), then Bheden at 29.7% (Rs 1.62 crore). The one remaining, Attabira, accounts for Rs 1.19 crore. For size: Barpali holds 47.3% of the 3,062 activities behind these totals, against 48.4% of spending -- a group's total grows with how much of the work it holds.

</details>

### C: Gemma picks, Gemma writes (a full switch)

20 findings · 237.1 s of model time · $0.0028 · officer sees: Written answer (2nd draft)

Picking: `google/gemma-4-31b-it`, 195.0 s, reading 13,657 tokens of candidate findings.

What the officer would read:

> In block Barpali, 1,447 activities were planned across 2 Gram Panchayats (GPs), with Bandhpali holding 50.4% (729 activities) and Bhatigaon holding 49.6% (718 activities). These activities are spread across 21 plans, with 12 in Bandhpali and 9 in Bhatigaon. A significant number of these, 1,067 activities, were planned without a cost, distributed almost evenly between Bandhpali (539) and Bhatigaon (528).
>
> Financial data shows a total planned cost of Rs 5.49 crore, comprising Rs 3.34 crore in Bandhpali (61.0%) and Rs 2.14 crore in Bhatigaon (39.0%). This includes tied grant planning totaling Rs 1.73 crore, with Rs 1.05 crore in Bandhpali (60.6%) and Rs 68.41 lakh in Bhatigaon (39.4%). Sanctioned amounts total Rs 2.96 crore, with Rs 1.62 crore in Bandhpali (54.6%) and Rs 1.34 crore in Bhatigaon (45.4%). Total spending across the two GPs is Rs 2.64 crore, with Rs 1.40 crore spent in Bandhpali (53.1%) and Rs 1.24 crore in Bhatigaon (46.9%). Spending linked to a planned activity totals Rs 2.55 crore, with Rs 1.34 crore in Bandhpali (52.8%) and Rs 1.20 crore in Bhatigaon (47.2%).
>
> Spending measured against plan is Rs -2.85 crore, meaning spending is below plan. This is concentrated in Bandhpali, which accounts for 68.2% (Rs -1.94 crore) of this figure, while Bhatigaon accounts for Rs -90.49 lakh. In terms of general component spending, the total is Rs 2.99 crore. This is spread across 7 LSDG themes, with "Theme 6 - Self-sufficient Infrastructure in Village" accounting for 33.1% (Rs 99.22 lakh) and "Theme 4 - Water Sufficient Village" accounting for 30.6% (Rs 91.57 lakh).
>
> Regarding implementation and administration:
> * 180 administrative approval records exist, with 92 in Bandhpali and 88 in Bhatigaon.
> * 6 activities are currently under approval, all of which (100.0%) are in Bandhpali.
> * 171 activities have started, with 88 in Bhatigaon (51.5%) and 83 in Bandhpali (48.5%).
> * 171 activities are ongoing, with 88 in Bhatigaon (51.5%) and 83 in Bandhpali (48.5%).
>
> Demographic and infrastructure data:
> * The reported population is 10,072, with 5,741 (57.0%) in Bandhpali and 4,331 (43.0%) in Bhatigaon. 
> * Expected beneficiaries total 15,651 people, concentrated in Bandhpali with 11,383 people (72.7%) compared to 4,268 in Bhatigaon. 
> * There are 28 reported wards, split evenly with 14 in each GP.
> * The reported general-category population is 420 people, with 294 (70.0%) in Bhatigaon and 126 in Bandhpali.
> * Infrastructure is concentrated: all 5 reported primary schools are in Bandhpali, while the single reported bank/cooperative bank facility is in Bhatigaon.
>
> More than 20 findings clear the relevance bar for this question; these are the 20 closest to what you asked.
>
> (as of 2026-09-11)

<details><summary>Rejected draft 1 (17.5 s)</summary>

Rejected by the number check: citations it could not match: `[d3-00244, d1-09525]`; 3 picked findings left uncited (`d1-09516`, `d2-00151`, `d4-00551`).

> As of 2026-09-11, the analysis of Barpali block, covering two Gram Panchayats (Bandhpali and Bhatigaon), shows the following patterns:
>
> **Planning and Financial Execution**
> Across the block, 1,447 activities were planned via 21 plans. However, 1,067 of these activities were planned without an associated cost. While the total planned cost was Rs 5.49 crore, the sanctioned amount was Rs 2.96 crore, and actual spending totaled Rs 2.64 crore. 
>
> Consequently, spending was Rs 2.85 crore below the planned cost across the block. Bandhpali accounts for the majority of this gap, with spending measured against plan at Rs -1.94 crore.
>
> **Distribution Across Gram Panchayats**
> Workload and spending are distributed relatively evenly between the two Panchayats:
> *   **Activities:** Bandhpali has 729 planned activities and Bhatigaon has 718.
> *   **Spending:** Bandhpali spent Rs 1.40 crore and Bhatigaon spent Rs 1.24 crore.
> *   **Administrative Records:** Administrative approvals are split between Bandhpali (92 records) and Bhatigaon (88 records).
>
> There are, however, significant concentrations in other areas. Bandhpali accounts for 100% of activities currently under approval (6 activities) and 100% of reported primary schools (5 schools). Conversely, Bhatigaon accounts for 100% of reported banks and cooperative banks (1 facility).
>
> **Beneficiaries and Demographics**
> While the reported population is split between Bandhpali (5,741 people) and Bhatigaon (4,331 people), the expected beneficiaries are heavily concentrated in Bandhpali, which accounts for 11,383 people (72.7% of the block total). Regarding general-category population, Bhatigaon accounts for 294 people compared to 126 in Bandhpali.
>
> **Activity Status and Themes**
> A total of 171 activities have started and are currently ongoing, with 88 in Bhatigaon and 83 in Bandhpali. Spending for the general component totals Rs 2.99 crore, primarily directed toward "Theme 6 - Self-sufficient Infrastructure in Village" (Rs 99.22 lakh) and "Theme 4 - Water Sufficient Village" (Rs 91.57 lakh).

</details>

<details><summary>Findings picked (20)</summary>

1. `d4-00583` Within block Barpali, spending totals Rs 2.64 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 53.1% (Rs 1.40 crore), then Bhatigaon at 46.9% (Rs 1.24 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 53.1% of spending -- a group's total grows with how much of the work it holds.
2. `d4-00581` Within block Barpali, planned cost totals Rs 5.49 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 61.0% (Rs 3.34 crore), then Bhatigaon at 39.0% (Rs 2.14 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 61.0% of planned cost -- a group's total grows with how much of the work it holds.
3. `d4-00584` Within block Barpali, spending measured against plan totals Rs -2.85 crore across 2 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Bandhpali accounts for 68.2% of it (Rs -1.94 crore). The one remaining, Bhatigaon, accounts for Rs -90.49 lakh. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 68.2% of spending measured against plan -- a group's total grows with how much of the work it holds.
4. `d4-00577` Within block Barpali, plans totals 21 plans across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 57.1% (12 plans), then Bhatigaon at 42.9% (9 plans). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 57.1% of plans -- a group's total grows with how much of the work it holds.
5. `d3-00232` Within block Barpali, activities planned totals 1,447 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 50.4% (729 activities), then Bhatigaon at 49.6% (718 activities).
6. `d4-00582` Within block Barpali, sanctioned amount totals Rs 2.96 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 54.6% (Rs 1.62 crore), then Bhatigaon at 45.4% (Rs 1.34 crore). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 54.6% of sanctioned amount -- a group's total grows with how much of the work it holds.
7. `d1-09534` Within block Barpali, expected beneficiaries totals 15,651 people across 2 Gram Panchayats. It is concentrated: Bandhpali accounts for 72.7% of it (11,383 people). The one remaining, Bhatigaon, accounts for 4,268 people. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 72.7% of expected beneficiaries -- a group's total grows with how much of the work it holds.
8. `d4-00540` Within block Barpali, reported population totals 10,072 people across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 57.0% (5,741 people), then Bhatigaon at 43.0% (4,331 people). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 57.0% of reported population -- a group's total grows with how much of the work it holds.
9. `d3-00244` Within block Barpali, activities ongoing totals 171 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bhatigaon at 51.5% (88 activities), then Bandhpali at 48.5% (83 activities). For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 51.5% of activities ongoing -- a group's total grows with how much of the work it holds.
10. `d1-09528` Within block Barpali, activities under approval totals 6 activities across 2 Gram Panchayats. It is concentrated: Bandhpali accounts for 100.0% of it (6 activities). The one remaining, Bhatigaon, accounts for 0 activities. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 100.0% of activities under approval -- a group's total grows with how much of the work it holds.
11. `d4-00556` Within block Barpali, reported primary schools totals 5 schools across 2 Gram Panchayats. It is concentrated: Bandhpali accounts for 100.0% of it (5 schools). The one remaining, Bhatigaon, accounts for 0 schools. For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 100.0% of reported primary schools -- a group's total grows with how much of the work it holds.
12. `d4-00569` Within block Barpali, reported reported banks and cooperative banks and cooperative reported banks and cooperative banks totals 1 facilities across 2 Gram Panchayats. It is concentrated: Bhatigaon accounts for 100.0% of it (1 facilities). The one remaining, Bandhpali, accounts for 0 facilities. For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 100.0% of reported reported banks and cooperative banks and cooperative reported banks and cooperative banks -- a group's total grows with how much of the work it holds.
13. `d4-00547` Within block Barpali, reported general-category population totals 420 people across 2 Gram Panchayats. It is concentrated: Bhatigaon accounts for 70.0% of it (294 people). The one remaining, Bandhpali, accounts for 126 people. For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 70.0% of reported general-category population -- a group's total grows with how much of the work it holds.
14. `d1-09543` Within block Barpali, spending, general component totals Rs 2.99 crore across 7 LSDG LSDG theme values. It is spread across them without one standing out: the largest is Theme 6 - Self-sufficient Infrastructure in Village at 33.1% (Rs 99.22 lakh), then Theme 4 - Water Sufficient Village at 30.6% (Rs 91.57 lakh). The remaining 5 together account for Rs 1.09 crore. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 31.0% of the 1,447 activities behind these totals, against 33.1% of spending, general component -- a group's total grows with how much of the work it holds.
15. `d1-09525` Within block Barpali, activities started totals 171 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bhatigaon at 51.5% (88 activities), then Bandhpali at 48.5% (83 activities). For size: Bhatigaon holds 49.6% of the 1,447 activities behind these totals, against 51.5% of activities started -- a group's total grows with how much of the work it holds.
16. `d4-00551` Within block Barpali, reported reported wards totals 28 reported wards across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 50.0% (14 reported wards), then Bhatigaon at 50.0% (14 reported wards). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 50.0% of reported reported wards -- a group's total grows with how much of the work it holds.
17. `d2-00151` Within block Barpali, spending linked to a planned activity totals Rs 2.55 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 52.8% (Rs 1.34 crore), then Bhatigaon at 47.2% (Rs 1.20 crore). For size: Bandhpali holds 44.3% of the 440 vouchers behind these totals, against 52.8% of spending linked to a planned activity -- a group's total grows with how much of the work it holds. A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years.
18. `d4-00588` Within block Barpali, administrative approvals totals 180 approval records across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 51.1% (92 approval records), then Bhatigaon at 48.9% (88 approval records). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 51.1% of administrative approvals -- a group's total grows with how much of the work it holds.
19. `d1-09516` Within block Barpali, tied grant planned totals Rs 1.73 crore across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 60.6% (Rs 1.05 crore), then Bhatigaon at 39.4% (Rs 68.41 lakh). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 60.6% of tied grant planned -- a group's total grows with how much of the work it holds.
20. `d4-00580` Within block Barpali, activities planned without a cost totals 1,067 activities across 2 Gram Panchayats. It is spread across them without one standing out: the largest is Bandhpali at 50.5% (539 activities), then Bhatigaon at 49.5% (528 activities). For size: Bandhpali holds 50.4% of the 1,447 activities behind these totals, against 50.5% of activities planned without a cost -- a group's total grows with how much of the work it holds.

</details>

## Question 2: Is spending on track?

### What I noticed

**Writing (A vs B, same 4 findings).** The closest of the three. Gemma's version is correct and well organised. Two small drops: "below plan by a total of Rs -51.96 crore" is a double negative that Sol avoids by explaining the minus sign, and Sol ends each paragraph with a pointer for the review where Gemma only lists.

**Picking (C).** Gemma picked 13 spending-against-plan breakdowns and none of the four patterns Sol chose, so the finding that cuts across places ("Activity Approved" has the lowest spending against plan in 18 of 20 GPs) is gone. What is left is a list of gaps, including "Output Code 101" and "uncategorised asset categories", which mean little to an officer. Two lines also end in a stray ",." where a citation was removed.

### A: Sol picks, Sol writes (what runs today)

4 findings · 27.3 s of model time · $0.0887 · officer sees: Written answer

Picking: `gpt-5.6-sol`, 10.3 s, reading 14,543 tokens of candidate findings.

What the officer would read:

> In the 20-Gram-Panchayat sample, spending on costed activities is below plan overall, with spending measured against plan totalling Rs -51.96 crore; the negative figure denotes spending below plan. The gap is spread across the sample rather than dominated by one Gram Panchayat: Biswamathpur accounts for 13.9% (Rs -7.23 crore), Kalimela for 11.3% (Rs -5.90 crore), and the remaining 18 together for Rs -38.84 crore. 
>
> The most consistent point for review is approved activities: “Activity Approved” has the lowest spending measured against plan in 18/20 Gram Panchayats, while Boipariguda and Laxmipur show no clear status pattern. Theme 6—Self-sufficient Infrastructure in Village—also has the lowest spending measured against plan across all population-size bands. 
>
> District-level review should pay particular attention to Bargarh and Ganjam, which record the lowest spending measured against plan across 6/7 LSDG themes. The exception is Theme 4—Water Sufficient Village—where Ganjam and Malkangiri are the lowest.
>
> (as of 2026-09-11)

<details><summary>Findings picked (4)</summary>

1. `d1-36141` Within costed or costless Costed, spending measured against plan totals Rs -51.96 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 13.9% (Rs -7.23 crore), then Kalimela at 11.3% (Rs -5.90 crore). The remaining 18 together account for Rs -38.84 crore. For size: Biswamathpur holds 4.3% of the 5,630 activities behind these totals, against 13.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 16.4%.
2. `1-02208` Across all population size bands, Theme 6 - Self-sufficient Infrastructure in Village has the lowest spending measured against plan among LSDG theme values
3. `1-03549` Across most LSDG theme values (6/7), Bargarh and Ganjam are lowest in spending measured against plan among districts. Exception: Theme 4 - Water Sufficient Village (Ganjam and Malkangiri are lowest in spending measured against plan among districts)
4. `1-01801` Across nearly all Gram Panchayats (18/20), Activity Approved has the lowest spending measured against plan among activity status values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

</details>

### B: Sol's picks, Gemma writes (the writing on its own)

4 findings · 6.3 s of model time · $0.0002 · officer sees: Written answer

What the officer would read:

> As of 2026-09-11, spending across the 20-Gram-Panchayat sample is below plan by a total of Rs -51.96 crore. This underspending is distributed across the sample, with Biswamathpur (Rs -7.23 crore) and Kalimela (Rs -5.90 crore) recording the largest amounts.
>
> Patterns in this underspending are evident across specific themes, districts, and activity statuses:
>
> * **Themes and Districts:** "Theme 6 - Self-sufficient Infrastructure in Village" has the lowest spending measured against plan among all LSDG themes across all population size bands. Geographically, Bargarh and Ganjam are the lowest in spending measured against plan across 6 of 7 LSDG theme values. For "Theme 4 - Water Sufficient Village," Ganjam and Malkangiri are the lowest in spending measured against plan.
> * **Activity Status:** In 18 of the 20 Gram Panchayats, the "Activity Approved" status has the lowest spending measured against plan. The exceptions are Boipariguda and Laxmipur, where no clear pattern was identified.

<details><summary>Findings picked (4)</summary>

1. `d1-36141` Within costed or costless Costed, spending measured against plan totals Rs -51.96 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 13.9% (Rs -7.23 crore), then Kalimela at 11.3% (Rs -5.90 crore). The remaining 18 together account for Rs -38.84 crore. For size: Biswamathpur holds 4.3% of the 5,630 activities behind these totals, against 13.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 16.4%.
2. `1-02208` Across all population size bands, Theme 6 - Self-sufficient Infrastructure in Village has the lowest spending measured against plan among LSDG theme values
3. `1-03549` Across most LSDG theme values (6/7), Bargarh and Ganjam are lowest in spending measured against plan among districts. Exception: Theme 4 - Water Sufficient Village (Ganjam and Malkangiri are lowest in spending measured against plan among districts)
4. `1-01801` Across nearly all Gram Panchayats (18/20), Activity Approved has the lowest spending measured against plan among activity status values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

</details>

### C: Gemma picks, Gemma writes (a full switch)

13 findings · 47.7 s of model time · $0.0029 · officer sees: Written answer (2nd draft)

Picking: `google/gemma-4-31b-it`, 15.7 s, reading 16,179 tokens of candidate findings.

What the officer would read:

> Spending is currently below plan across several key areas within the sample.
>
> **General Spending Gaps**
> Across the 20 Gram Panchayats, spending is significantly below plan for costed activities (Rs -51.96 crore), activities with "Approved" status (Rs -41.61 crore), and "New/Fresh" types of work (Rs -34.36 crore). Additionally, spending for output type Code 101 is below plan by Rs -30.97 crore and uncategorised asset categories by Rs -18.60 crore. 
>
> Biswamathpur is a frequent contributor to these gaps, accounting for 13.9% (Rs -7.23 crore) of the under-spending in costed activities, 16.2% (Rs -6.74 crore) for approved activities, 15.8% (Rs -5.43 crore) for new/fresh work, and 17.5% (Rs -5.42 crore) for output type Code 101.
>
> **LSDG Theme Performance**
> Spending is below plan across multiple LSDG themes:
> * **Self-sufficient Infrastructure (Theme 6):** Totals Rs -20.13 crore, with Sharagada accounting for 16.7% (Rs -3.36 crore).
> * **Water Sufficient Village (Theme 4):** Totals Rs -13.11 crore, with Kalimela accounting for 25.5% (Rs -3.34 crore).
> * **Clean and Green Village (Theme 5):** Totals Rs -8.62 crore,. This is spread across the sample, with Biswamathpur accounting for 25.0% (Rs -2.15 crore) and Rangeilunda accounting for 27.4% (Rs -2.36 crore).
> * **Child Friendly Village (Theme 3):** Totals Rs -2.67 crore,. Rangeilunda accounts for 50.3% (Rs -1.34 crore), while Biswamathpur accounts for 38.7% (Rs -1.04 crore).
> * **Village with Good Governance (Theme 8):** Totals Rs -2.41 crore, with Bheden accounting for 24.8% (Rs -59.78 lakh).
>
> **Rural Housing**
> In the Rural housing focus area, spending is below plan by Rs -2.23 crore. This is highly concentrated, with Boipariguda accounting for 95.7% (Rs -2.13 crore) of the total.
>
> (as of 2026-09-11)

<details><summary>Rejected draft 1 (15.5 s)</summary>

Rejected by the number check: citations it could not match: `[d1-45414, d1-45394]`, `[d1-46308, d1-46285]`; figures not tied to a cited finding: `3`, `2.67`.

> Spending is currently below plan across several key categories and themes within the 20-Gram-Panchayat sample.
>
> **Significant Spending Gaps in General Categories**
> Broadly, spending is below plan for costed activities by Rs -51.96 crore, for approved activities by Rs -41.61 crore, and for new/fresh works by Rs -34.36 crore. Biswamathpur shows a notable gap in these areas, with spending below plan by Rs -7.23 crore for costed activities, Rs -6.74 crore for approved activities, and Rs -5.43 crore for new/fresh works. Kalimela also shows gaps in these categories: Rs -5.90 crore for costed activities, Rs -5.46 crore for approved activities, and Rs -3.95 crore for new/fresh works.
>
> **LSDG Theme Performance**
> Spending is below plan across multiple LSDG themes:
> *   **Infrastructure & Environment:** Spending for "Self-sufficient Infrastructure in Village" (Theme 6) is below plan by Rs -20.13 crore, with Sharagada recording a gap of Rs -3.36 crore and Biswamathpur Rs -2.66 crore. "Clean and Green Village" (Theme 5) is below plan by Rs -8.62 crore, with gaps in Rangeilunda (Rs -2.36 crore) and Biswamathpur (Rs -2.15 crore).
> *   **Water & Governance:** "Water Sufficient Village" (Theme 4) spending is below plan by Rs -13.11 crore, led by Kalimela at Rs -3.34 crore. "Village with Good Governance" (Theme 8) is below plan by Rs -2.41 crore, with Bheden recording a gap of Rs -59.78 lakh.
> *   **Child-Friendly Village:** Spending for Theme 3 is below plan by Rs -2.67 crore. Rangeilunda accounts for 50.3% of this gap (Rs -1.34 crore), while Biswamathpur accounts for 38.7% (Rs -1.04 crore).
>
> **Other Notable Gaps**
> *   **Rural Housing:** Spending is below plan by Rs -2.23 crore, with Boipariguda accounting for 95.7% of this gap (Rs -2.13 crore).
> *   **Output and Asset Types:** Spending for Output Code 101 is below plan by Rs -30.97 crore, with the largest gaps in Biswamathpur (Rs -5.42 crore) and Kalimela (Rs -3.94 crore). Uncategorised asset categories are below plan by Rs -18.60 crore, with Sharagada (Rs -3.49 crore) and Boipariguda (Rs -3.13 crore) showing the largest gaps.

</details>

<details><summary>Findings picked (13)</summary>

1. `d1-46308` Within LSDG LSDG theme Theme 5 - Clean and Green Village , spending measured against plan totals Rs -8.62 crore across 16 blocks. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Rangeilunda at 27.4% (Rs -2.36 crore), then Bheden at 10.9% (Rs -93.73 lakh). The remaining 14 together account for Rs -5.32 crore. For size: Rangeilunda holds 6.0% of the 2,127 activities behind these totals, against 27.4% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Rangeilunda is 16.7%.
2. `d1-24173` Within focus area Rural housing, spending measured against plan totals Rs -2.23 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Boipariguda accounts for 95.7% of it (Rs -2.13 crore). The remaining 19 together account for Rs -9.50 lakh. For size: Boipariguda holds 2.0% of the 305 activities behind these totals, against 95.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Boipariguda is 0.0%.
3. `d1-45394` Within LSDG LSDG theme Theme 3 - Child Friendly Village, spending measured against plan totals Rs -2.67 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 38.7% (Rs -1.04 crore), then Bheden at 13.1% (Rs -35.09 lakh). The remaining 18 together account for Rs -1.29 crore. For size: Biswamathpur holds 7.3% of the 1,041 activities behind these totals, against 38.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 6.1%.
4. `d1-46285` Within LSDG LSDG theme Theme 5 - Clean and Green Village , spending measured against plan totals Rs -8.62 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 25.0% (Rs -2.15 crore), then Bheden at 10.9% (Rs -93.73 lakh). The remaining 18 together account for Rs -5.53 crore. For size: Biswamathpur holds 3.1% of the 2,127 activities behind these totals, against 25.0% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 11.1%.
5. `d1-45414` Within LSDG LSDG theme Theme 3 - Child Friendly Village, spending measured against plan totals Rs -2.67 crore across 16 blocks. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Rangeilunda accounts for 50.3% of it (Rs -1.34 crore). The remaining 15 together account for Rs -1.33 crore. For size: Rangeilunda holds 18.5% of the 1,041 activities behind these totals, against 50.3% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Rangeilunda is 8.7%.
6. `d1-47232` Within LSDG LSDG theme Theme 8 - Village with Good Governance, spending measured against plan totals Rs -2.41 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Bheden at 24.8% (Rs -59.78 lakh), then Kalimela at 15.5% (Rs -37.29 lakh). The remaining 18 together account for Rs -1.44 crore. For size: Bheden holds 2.2% of the 1,748 activities behind these totals, against 24.8% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Bheden is 0.1%.
7. `d1-46759` Within LSDG LSDG theme Theme 6 - Self-sufficient Infrastructure in Village, spending measured against plan totals Rs -20.13 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Sharagada at 16.7% (Rs -3.36 crore), then Biswamathpur at 13.2% (Rs -2.66 crore). The remaining 18 together account for Rs -14.12 crore. For size: Sharagada holds 5.2% of the 4,693 activities behind these totals, against 16.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sharagada is 19.6%.
8. `d1-49758` Within type of work New/Fresh, spending measured against plan totals Rs -34.36 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 15.8% (Rs -5.43 crore), then Kalimela at 11.5% (Rs -3.95 crore). The remaining 18 together account for Rs -24.98 crore. For size: Biswamathpur holds 4.4% of the 11,047 activities behind these totals, against 15.8% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 17.9%.
9. `d1-44064` Within activity status Activity Approved, spending measured against plan totals Rs -41.61 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 16.2% (Rs -6.74 crore), then Kalimela at 13.1% (Rs -5.46 crore). The remaining 18 together account for Rs -29.40 crore. For size: Biswamathpur holds 4.0% of the 10,108 activities behind these totals, against 16.2% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 0.0%.
10. `d1-36141` Within costed or costless Costed, spending measured against plan totals Rs -51.96 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 13.9% (Rs -7.23 crore), then Kalimela at 11.3% (Rs -5.90 crore). The remaining 18 together account for Rs -38.84 crore. For size: Biswamathpur holds 4.3% of the 5,630 activities behind these totals, against 13.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 16.4%.
11. `d1-45790` Within LSDG LSDG theme Theme 4 - Water Sufficient Village, spending measured against plan totals Rs -13.11 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Kalimela at 25.5% (Rs -3.34 crore), then Boipariguda at 10.1% (Rs -1.32 crore). The remaining 18 together account for Rs -8.45 crore. For size: Kalimela holds 11.0% of the 1,575 activities behind these totals, against 25.5% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Kalimela is 16.3%.
12. `d1-36728` Within output type Code 101, spending measured against plan totals Rs -30.97 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Biswamathpur at 17.5% (Rs -5.42 crore), then Kalimela at 12.7% (Rs -3.94 crore). The remaining 18 together account for Rs -21.61 crore. For size: Biswamathpur holds 5.0% of the 3,618 activities behind these totals, against 17.5% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Biswamathpur is 17.9%.
13. `d1-07898` Within asset category Uncategorised, spending measured against plan totals Rs -18.60 crore across 20 Gram Panchayats. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Sharagada at 18.7% (Rs -3.49 crore), then Boipariguda at 16.8% (Rs -3.13 crore). The remaining 18 together account for Rs -11.98 crore. For size: Sharagada holds 9.5% of the 8,439 activities behind these totals, against 18.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Sharagada is 1.1%.

</details>

## Question 3: Why is spending low in Chikilli?

### What I noticed

**Picking only.** A "why" question never reaches the writer: the reply is fixed wording plus the picked findings, so the model only decides which findings are shown. There is no version B.

This is the one case where Gemma did better. Sol kept nothing, so the officer is told the analysis "holds nothing on the subject", which is wrong. Gemma found 10 relevant Chikilli records (Rs 4.12 crore below plan, lowest sanctioned amount among the GPs). But keeping more is also the risk: Sol is the only picker that has been tested against questions the analysis should refuse (0% wrong answers), and Gemma has not.

### A: Sol picks, Sol writes (what runs today)

0 findings · 6.4 s of model time · $0.0573 · officer sees: Fixed "why" reply

Picking: `gpt-5.6-sol`, 6.4 s, reading 13,019 tokens of candidate findings.

What the officer would read:

> This analysis finds patterns and associations. It cannot establish what causes what — the outcome measures in this data are not reliable enough for that — so I will not answer a 'why' with a reason.
>
> The analysis also holds nothing on the subject of your question, so there is not even a pattern to point at.
>
> What can be done next is describable rather than analytical: ask the places named here what they did differently, check whether the records behind the pattern are complete, and put the question to the officers who were there.
>
> (as of 2026-09-11)

### C: Gemma picks, Gemma writes (a full switch)

10 findings · 9.9 s of model time · $0.0014 · officer sees: Fixed "why" reply

Picking: `google/gemma-4-31b-it`, 9.9 s, reading 14,666 tokens of candidate findings.

What the officer would read:

> This analysis finds patterns and associations. It cannot establish what causes what — the outcome measures in this data are not reliable enough for that — so I will not answer a 'why' with a reason.
>
> What the analysis does show about this:
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 6 fiscal years. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is 2024-2025 at 33.5% (Rs -1.38 crore), then 2020-2021 at 20.2% (Rs -83.01 lakh). The remaining 4 together account for Rs -1.91 crore.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 28 focus area values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Maintenance of community system at 23.9% (Rs -98.63 lakh), then Roads at 18.0% (Rs -74.02 lakh). The remaining 26 together account for Rs -2.39 crore. For size: Maintenance of community system holds 17.3% of the 640 activities behind these totals, against 23.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Maintenance of community system is 22.3%.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 4 type of work values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: New/Fresh accounts for 84.3% of it (Rs -3.47 crore). The remaining 3 together account for Rs -64.50 lakh. For size: New/Fresh holds 88.0% of the 640 activities behind these totals, against 84.3% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, New/Fresh is 19.3%.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 7 LSDG LSDG theme values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Theme 6 - Self-sufficient Infrastructure in Village accounts for 63.4% of it (Rs -2.61 crore). The remaining 6 together account for Rs -1.51 crore. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 48.4% of the 640 activities behind these totals, against 63.4% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Theme 6 - Self-sufficient Infrastructure in Village is 20.2%.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 2 activity type values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Public Works accounts for 95.3% of it (Rs -3.93 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs -19.22 lakh. For size: Public Works holds 84.1% of the 640 activities behind these totals, against 95.3% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Public Works is 26.1%.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 3 activity status values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Activity Approved accounts for 85.5% of it (Rs -3.52 crore). The remaining 2 together account for Rs -59.76 lakh. For size: Activity Approved holds 85.9% of the 640 activities behind these totals, against 85.5% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Activity Approved is 0.0%.
>    (a breakdown of the recorded totals, not a mined pattern — the parts add up to the whole)
>
> - Across all fiscal years, Chikilli has the lowest sanctioned amount among Gram Panchayats
>    (not in the ranked shortlist — one of the wider set of patterns the analysis found but did not promote)
>
> - Across all fiscal years, Chikilli has the lowest proposed cost at sanction among Gram Panchayats
>    (not in the ranked shortlist — one of the wider set of patterns the analysis found but did not promote)
>
> - Across most fiscal years (5/6), Chikilli has the lowest activities with technical approval among Gram Panchayats. Exception: 2023-2024 (no clear pattern)
>    (not in the ranked shortlist — one of the wider set of patterns the analysis found but did not promote)
>
> - Across most fiscal years (5/6), Chikilli has the lowest activities with administrative approval among Gram Panchayats. Exception: 2023-2024 (no clear pattern)
>    (not in the ranked shortlist — one of the wider set of patterns the analysis found but did not promote)
>
> Those readings are open in both directions: a pattern like this can be a real difference in how places work, or a difference in what gets recorded, and nothing in the analysis separates the two.
>
> What can be done next is describable rather than analytical: ask the places named here what they did differently, check whether the records behind the pattern are complete, and put the question to the officers who were there.
>
> (as of 2026-09-11)

<details><summary>Findings picked (10)</summary>

1. `d3-01702` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 6 fiscal years. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is 2024-2025 at 33.5% (Rs -1.38 crore), then 2020-2021 at 20.2% (Rs -83.01 lakh). The remaining 4 together account for Rs -1.91 crore.
2. `d1-29244` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 28 focus area values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is spread across them without one standing out: the largest is Maintenance of community system at 23.9% (Rs -98.63 lakh), then Roads at 18.0% (Rs -74.02 lakh). The remaining 26 together account for Rs -2.39 crore. For size: Maintenance of community system holds 17.3% of the 640 activities behind these totals, against 23.9% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Maintenance of community system is 22.3%.
3. `d1-29257` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 4 type of work values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: New/Fresh accounts for 84.3% of it (Rs -3.47 crore). The remaining 3 together account for Rs -64.50 lakh. For size: New/Fresh holds 88.0% of the 640 activities behind these totals, against 84.3% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, New/Fresh is 19.3%.
4. `d1-29231` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 7 LSDG LSDG theme values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Theme 6 - Self-sufficient Infrastructure in Village accounts for 63.4% of it (Rs -2.61 crore). The remaining 6 together account for Rs -1.51 crore. For size: Theme 6 - Self-sufficient Infrastructure in Village holds 48.4% of the 640 activities behind these totals, against 63.4% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Theme 6 - Self-sufficient Infrastructure in Village is 20.2%.
5. `d1-29281` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 2 activity type values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Public Works accounts for 95.3% of it (Rs -3.93 crore). The one remaining, Beneficiary Oriented Programmes, accounts for Rs -19.22 lakh. For size: Public Works holds 84.1% of the 640 activities behind these totals, against 95.3% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Public Works is 26.1%.
6. `d1-29304` Within Gram Panchayat Chikilli, spending measured against plan totals Rs -4.12 crore across 3 activity status values. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Activity Approved accounts for 85.5% of it (Rs -3.52 crore). The remaining 2 together account for Rs -59.76 lakh. For size: Activity Approved holds 85.9% of the 640 activities behind these totals, against 85.5% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Activity Approved is 0.0%.
7. `1-01299` Across all fiscal years, Chikilli has the lowest sanctioned amount among Gram Panchayats
8. `1-01309` Across all fiscal years, Chikilli has the lowest proposed cost at sanction among Gram Panchayats
9. `1-01302` Across most fiscal years (5/6), Chikilli has the lowest activities with technical approval among Gram Panchayats. Exception: 2023-2024 (no clear pattern)
10. `1-01305` Across most fiscal years (5/6), Chikilli has the lowest activities with administrative approval among Gram Panchayats. Exception: 2023-2024 (no clear pattern)

</details>

## Why Gemma's first drafts were rejected

Not because of invented numbers. In both cases Gemma put two citations inside one bracket (`[d3-00244, d1-09525]`), where the number check expects one finding per bracket. The check could not match the pair, so the figures in that sentence counted as uncited; the Barpali draft also left 3 picked findings uncited. Both second drafts fixed this and passed. Every figure Gemma wrote was traceable to a cited finding. A line in the writer prompt asking for one id per bracket would probably remove the retry and its 15-24 s.

## The formatting problem

Gemma answers with markdown: bold headings (`**Financial Overview**`) and `*` bullets. Sol writes plain paragraphs. The Discover tab's answer parser ([discover-answer.ts](../frontend/ab-dashboard-main/src/lib/discover-answer.ts)) splits the answer into paragraphs on blank lines and joins the lines inside a paragraph, and nothing in it reads markdown. An officer would therefore see the asterisks, with bullets run together into one paragraph. This report shows Gemma's answers with the formatting applied, as Gemma meant them.

## Where the cost goes

An earlier run the same day (10 questions of mixed kinds, all on Sol) averaged about 10 cents a question, and about 12-13 cents for questions that get a written answer. Most of that is the picking step: it reads 12,000-15,000 tokens of candidate findings each time, about 5.5 cents a question on its own. The writer is about 2 cents per draft. So:

| Setup | Rough cost per question |
|---|--:|
| Sol picks and writes (today) | ~9 cents |
| Sol picks, Gemma writes | ~7 cents |
| Gemma picks and writes | under 1 cent |

## Limits

- One run per version on three questions. The picks, the wording and the times will all change somewhat on a rerun.
- Gemma's picking call took 195 s on one question and 10-16 s on the other two. That looks like an OpenRouter provider delay rather than the model, but one run cannot tell.
- Gemma ran without extended thinking. Turning it on might improve its picking, at some cost in time.
- Version B's answers are the writer's output only; in the live service each answer would also end with the "(as of 2026-09-11)" line.
- The scripts that produced this (`compare3.py`, `build_md.py`) and the raw results (`compare3.json`) are in the session's temporary folder, not the repo. Every answer and every rejected draft is copied into this report word for word.

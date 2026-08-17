# Top findings across the programme

*Generated 2026-08-17T08:56:36Z from candidate set `a7f991c1df3771f9` (6 candidate files).*

The 3 analytical views are ranked internally, each against its own total. This table is the cross-view feed: one ordering of everything the analysis found, so the front page is not decided by which view a finding happened to come from.

## How the ordering was decided

Two rules, both editorial, both stated here rather than buried.

**Every area's best finding is on this page by construction.** The top finding from each of the 3 areas is seeded into the list unconditionally, so no question family can be dropped just because another area happened to score higher.

**The remaining places are filled by**

`global_score = area weight x within-area score x 0.85^(position in its own area - 1)`

The decay term is what makes an area spend its weight on its best findings first: without it, a large area converts its size into a long tail of middling entries and crowds out smaller areas' strongest results. The weights are below.

**A finding is dropped only if another finding already on the page says the same thing.** Each candidate is charged for its single closest overlap with what is already selected, not for the sum of its overlaps with all of them, and two findings count as overlapping only if they share a measure, a breakdown, or an actual filter — two findings that both describe the whole programme are not saying the same thing, they are simply both unfiltered.

| view | | Gram Panchayats covered | weight |
|---|---|---:|---:|
| view1 | Activity Lifecycle | 20 | 0.3333 |
| view2 | Geo-Month Cash Cube | 20 | 0.3333 |
| view3 | GP Performance | 20 | 0.3333 |

**The weights are equal, and that is a decision.** Coverage is counted as the distinct Gram Panchayats each area holds rows for, and it is the same 20 for all 3 of them: a Gram Panchayat that planned nothing, wrote no voucher and spent nothing is still present in every area as a row of zeros, so no area covers more of the state than another. Two alternatives were rejected. Weighting by row count would put the activity area at 88 times the performance area, which is a statement about how finely each one is cut and not about how much of the programme it speaks for. Weighting by rupees would rank the cashbook above the areas that read the same money at a different grain. With equal weights the ordering below is decided by each finding's own score and its own position in its area — the judgements the analysis actually made.

Knobs, fixed in the specification and not adjusted after the fact: rank decay **0.85**, seeds per area **1**.

Pooled 32 ranked-eligible candidates from 5,124 raw candidates across the 3 views. 0 were merged as duplicates of another view's finding — same source columns, same pattern type, same subspace, same highlight — leaving 32 distinct findings, of which the 32 below were selected for diversity.

## The feed

`seed` marks the findings guaranteed a place as their area's best; `in area` is the finding's own position within its area.

| # | | view | in area | finding | pattern | global score |
|---:|---|---|---:|---|---|---:|
| 1 | **seed** | Activity Lifecycle | 1 | Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.2920 |
| 2 | **seed** | Geo-Month Cash Cube | 1 | Across all temporal_grain values, activity_linked_expenditure is increasing over (varies) | TREND | 0.2404 |
| 3 | **seed** | GP Performance | 1 | Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others | TREND | 0.0820 |
| 4 |  | Activity Lifecycle | 2 | Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.2482 |
| 5 |  | Activity Lifecycle | 3 | Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern) | TOP_TWO | 0.1933 |
| 6 |  | Geo-Month Cash Cube | 2 | Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern) | OUTSTANDING_1 | 0.1806 |
| 7 |  | Activity Lifecycle | 4 | Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern) | OUTSTANDING_1 | 0.1643 |
| 8 |  | Activity Lifecycle | 5 | Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | OUTSTANDING_LAST | 0.1285 |
| 9 |  | Geo-Month Cash Cube | 3 | Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern) | SEASONALITY | 0.1175 |
| 10 |  | Activity Lifecycle | 6 | Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | ATTRIBUTION | 0.1092 |
| 11 |  | Geo-Month Cash Cube | 4 | Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern) | TREND | 0.0998 |
| 12 |  | Activity Lifecycle | 7 | Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | OUTSTANDING_1 | 0.0928 |
| 13 |  | Activity Lifecycle | 8 | Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values); Kalimela (Theme 4 - Water Sufficient Village has the highest fund_untied_total among theme values) | OUTSTANDING_1 | 0.0789 |
| 14 |  | Activity Lifecycle | 9 | Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern) | OUTSTANDING_LAST | 0.0664 |
| 15 |  | Activity Lifecycle | 10 | Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern) | ATTRIBUTION | 0.0564 |
| 16 |  | Geo-Month Cash Cube | 5 | Across most measure values (6/9), (varies) shows seasonal pattern (PERIOD_12) over month. Exception: activity_linked_expenditure ((varies) shows seasonal pattern (PERIOD_3) over month); sanctions_count (different pattern); sanctioned_amount (different pattern) | SEASONALITY | 0.0551 |
| 17 |  | Activity Lifecycle | 11 | Across all activity_for_label values, Code 101 and Code 105 are lowest in overspend_vs_plan among output_type_label values | LAST_TWO | 0.0473 |
| 18 |  | Activity Lifecycle | 12 | Across all activity_for_label values, Drinking water and Sanitation lead in fund_tied_total among focus_area_name values | TOP_TWO | 0.0402 |
| 19 |  | Activity Lifecycle | 13 | Across all fiscal_year values, Chikilli has the lowest fund_sanctioned_total among gp_name values | OUTSTANDING_LAST | 0.0342 |
| 20 |  | Geo-Month Cash Cube | 6 | Across most district_name values (5/9), activity_linked_expenditure shows seasonal pattern (PERIOD_12) over quarter. Exceptions: Sundargarh (activity_linked_expenditure shows seasonal pattern (PERIOD_6) over quarter); Rayagada (activity_linked_expenditure shows seasonal pattern (PERIOD_3) over quarter); Kandhamal (different pattern) and 1 others | SEASONALITY | 0.0295 |
| 21 |  | Activity Lifecycle | 14 | Across all fiscal_year values, Other has the lowest gen_amount among tied_untied values | OUTSTANDING_LAST | 0.0291 |
| 22 |  | Activity Lifecycle | 15 | Across all fiscal_year values, Activity Approved and WORK ONGOING lead in n_activities among status_label values | TOP_TWO | 0.0247 |
| 23 |  | Geo-Month Cash Cube | 7 | Across most temporal_grain values (2/3), receipt_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (different pattern) | SEASONALITY | 0.0613 |
| 24 |  | Geo-Month Cash Cube | 8 | Across most temporal_grain values (2/3), sanctions_count is increasing over (varies). Exception: month (different pattern) | TREND | 0.0521 |
| 25 |  | GP Performance | 2 | Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 5 others -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.0144 |
| 26 |  | Geo-Month Cash Cube | 9 | Across most block_name values (9/16), activity_linked_expenditure is increasing over quarter. Exceptions: Barpali (different pattern); Bheden (different pattern); Rangeilunda (different pattern) and 4 others | TREND | 0.0407 |
| 27 |  | Geo-Month Cash Cube | 10 | Across most measure values (6/9), (varies) has a significant shift at 2020-08 in month. Exception: activity_linked_expenditure ((varies) has a significant shift at 2020-11 in month); sanctions_count ((varies) has a significant shift at 2020-10 in month); sanctioned_amount ((varies) has a significant shift at 2020-10 in month) | CHANGE_POINT | 0.0093 |
| 28 |  | Geo-Month Cash Cube | 11 | Across most measure values (6/9), Ganjam has the highest (varies) among district_name values. Exception: payment_count (different pattern); payment_amount_mean (different pattern); receipt_amount_mean (different pattern) | OUTSTANDING_1 | 0.0074 |
| 29 |  | Geo-Month Cash Cube | 12 | Across most temporal_grain values (2/3), sanctioned_amount is increasing over (varies). Exception: fiscal_year (no clear pattern) | TREND | 0.0062 |
| 30 |  | Geo-Month Cash Cube | 13 | Across all temporal_grain values, activity_linked_expenditure is increasing over (varies) | TREND | 0.0086 |
| 31 |  | Geo-Month Cash Cube | 14 | Across most measure values (6/9), Bheden has the highest (varies) among block_name values. Exception: activity_linked_expenditure (Barpali has the highest (varies) among block_name values); sanctions_count (Barpali has the highest (varies) among block_name values); sanctioned_amount (Barpali has the highest (varies) among block_name values) | OUTSTANDING_1 | 0.0036 |
| 32 |  | Geo-Month Cash Cube | 15 | Across most temporal_grain values (2/3), payment_amount_mean is increasing over (varies). Exception: fiscal_year (no clear pattern) | TREND | 0.0028 |

# Top findings across the programme

*Generated 2026-09-11T09:31:44Z from candidate set `610cb3d26dff7bf3` (8 candidate files).*

The 4 analytical views are ranked internally, each against its own total. This table is the cross-view feed: one ordering of everything the analysis found, so the front page is not decided by which view a finding happened to come from.

## How the ordering was decided

Two rules, both editorial, both stated here rather than buried.

**Every area's best finding is on this page by construction.** The top finding from each of the 4 areas is seeded into the list unconditionally, so no question family can be dropped just because another area happened to score higher.

**The remaining places are filled by**

`global_score = area weight x within-area score x 0.85^(position in its own area - 1)`

The decay term is what makes an area spend its weight on its best findings first: without it, a large area converts its size into a long tail of middling entries and crowds out smaller areas' strongest results. The weights are below.

**A finding is dropped only if another finding already on the page says the same thing.** Each candidate is charged for its single closest overlap with what is already selected, not for the sum of its overlaps with all of them, and two findings count as overlapping only if they share a measure, a breakdown, or an actual filter — two findings that both describe the whole programme are not saying the same thing, they are simply both unfiltered.

| view | | Gram Panchayats covered | weight |
|---|---|---:|---:|
| view1 | Activity Lifecycle | 20 | 0.2500 |
| view2 | Geo-Month Cash Cube | 20 | 0.2500 |
| view3 | GP Performance | 20 | 0.2500 |
| view4 | GP Profile | 20 | 0.2500 |

**The weights are equal, and that is a decision.** Coverage is counted as the distinct Gram Panchayats each area holds rows for, and it is the same 20 for all 4 of them: a Gram Panchayat that planned nothing, wrote no voucher and spent nothing is still present in every area as a row of zeros, so no area covers more of the state than another. Two alternatives were rejected. Weighting by row count would put the activity area at 88 times the performance area, which is a statement about how finely each one is cut and not about how much of the programme it speaks for. Weighting by rupees would rank the cashbook above the areas that read the same money at a different grain. With equal weights the ordering below is decided by each finding's own score and its own position in its area — the judgements the analysis actually made.

Knobs, fixed in the specification and not adjusted after the fact: rank decay **0.85**, seeds per area **1**.

Pooled 58 ranked-eligible candidates from 5,398 raw candidates across the 4 views. 12 were merged as duplicates of another view's finding — same source columns, same pattern type, same subspace, same highlight — leaving 46 distinct findings, of which the 46 below were selected for diversity.

## The feed

`seed` marks the findings guaranteed a place as their area's best; `in area` is the finding's own position within its area.

| # | | view | in area | finding | pattern | global score |
|---:|---|---|---:|---|---|---:|
| 1 | **seed** | Activity Lifecycle | 1 | Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.2190 |
| 2 | **seed** | Geo-Month Cash Cube | 1 | Across all temporal_grain values, activity_linked_expenditure is increasing over (varies) | TREND | 0.1803 |
| 3 | **seed** | GP Performance | 1 | Across most gp_size values (3/4), expenditure_total_mean is decreasing over fiscal_year. Exception: 10,000 and above (no clear pattern) | TREND | 0.1368 |
| 4 | **seed** | GP Profile | 1 | Across most social_composition values (2/3), overspend_vs_plan_mean is evenly distributed across block_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.1219 |
| 5 |  | Activity Lifecycle | 2 | Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.1862 |
| 6 |  | Geo-Month Cash Cube | 2 | Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in payment_amount among gp_size values | LAST_TWO | 0.1532 |
| 7 |  | Activity Lifecycle | 3 | Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern) | TOP_TWO | 0.1450 |
| 8 |  | Geo-Month Cash Cube | 3 | Across all fiscal_year values, 2,500 to 5,000 and 5,000 to 10,000 lead in activity_linked_expenditure among gp_size values | TOP_TWO | 0.1302 |
| 9 |  | Activity Lifecycle | 4 | Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern) | OUTSTANDING_1 | 0.1232 |
| 10 |  | Geo-Month Cash Cube | 4 | Across all gp_size values, activity_linked_expenditure is increasing over month | TREND | 0.1107 |
| 11 |  | Activity Lifecycle | 5 | Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | OUTSTANDING_LAST | 0.0964 |
| 12 |  | Geo-Month Cash Cube | 5 | Across all social_composition values, receipt_count shows seasonal pattern (PERIOD_12) over quarter | SEASONALITY | 0.0941 |
| 13 |  | GP Profile | 3 | Across most social_composition values (2/3), overspend_vs_sanction_mean is evenly distributed across gp_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.0881 |
| 14 |  | Activity Lifecycle | 6 | Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | ATTRIBUTION | 0.0819 |
| 15 |  | Geo-Month Cash Cube | 6 | Across all fiscal_year values, Mixed accounts for the majority of activity_linked_expenditure among social_composition values | ATTRIBUTION | 0.0800 |
| 16 |  | Activity Lifecycle | 7 | Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern) | OUTSTANDING_1 | 0.0696 |
| 17 |  | GP Performance | 5 | Across most social_composition values (2/3), n_admin_approvals_mean forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern) | UNIMODALITY | 0.0636 |
| 18 |  | Geo-Month Cash Cube | 7 | Across most fiscal_year values (5/6), SC-majority has the lowest payment_amount_mean among social_composition values. Exception: 2025-2026 (different pattern) | OUTSTANDING_LAST | 0.0601 |
| 19 |  | GP Profile | 4 | Across most measure values (57/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (ST-majority has the highest (varies) among social_composition values); households_tap_water_mean (ST-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (SC-majority has the highest (varies) among social_composition values) and 14 others | OUTSTANDING_1 | 0.0597 |
| 20 |  | Activity Lifecycle | 8 | Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values); Kalimela (Theme 4 - Water Sufficient Village has the highest fund_untied_total among theme values) | OUTSTANDING_1 | 0.0592 |
| 21 |  | Geo-Month Cash Cube | 8 | Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern) | OUTSTANDING_1 | 0.0511 |
| 22 |  | Activity Lifecycle | 9 | Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern) | OUTSTANDING_LAST | 0.0498 |
| 23 |  | GP Profile | 2 | Across most social_composition values (2/3), overspend_vs_plan is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.1036 |
| 24 |  | Activity Lifecycle | 10 | Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern) | ATTRIBUTION | 0.0423 |
| 25 |  | Activity Lifecycle | 11 | Across all activity_for_label values, Code 101 and Code 105 are lowest in overspend_vs_plan among output_type_label values | LAST_TWO | 0.0355 |
| 26 |  | Geo-Month Cash Cube | 10 | Across most gp_size values (3/4), sanctions_count has a significant shift at 2020-10 in month. Exception: 10,000 and above (sanctions_count has a significant shift at 2021-01 in month) | CHANGE_POINT | 0.0317 |
| 27 |  | Activity Lifecycle | 12 | Across all activity_for_label values, Drinking water and Sanitation lead in fund_tied_total among focus_area_name values | TOP_TWO | 0.0302 |
| 28 |  | Geo-Month Cash Cube | 11 | Across most gp_size values (3/4), payment_amount_mean shows seasonal pattern (PERIOD_12) over month. Exception: 10,000 and above (different pattern) | SEASONALITY | 0.0269 |
| 29 |  | GP Profile | 7 | Across most measure values (58/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition values); households_tap_water_mean (ST-majority accounts for the majority of (varies) among social_composition values); household_toilets_mean (ST-majority accounts for the majority of (varies) among social_composition values) and 13 others | ATTRIBUTION | 0.0305 |
| 30 |  | GP Performance | 6 | Across most social_composition values (2/3), expenditure_total is decreasing over fiscal_year. Exception: SC-majority (different pattern) | TREND | 0.0541 |
| 31 |  | GP Profile | 6 | Across most measure values (61/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (ST-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values) and 10 others | OUTSTANDING_1 | 0.0391 |
| 32 |  | Activity Lifecycle | 14 | Across all fiscal_year values, Chikilli has the lowest fund_sanctioned_total among gp_name values | OUTSTANDING_LAST | 0.0218 |
| 33 |  | GP Profile | 5 | Across most measure values (53/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); planned_cost_mean (no clear pattern); expenditure_total_mean (no clear pattern) and 18 others | ATTRIBUTION | 0.0479 |
| 34 |  | Geo-Month Cash Cube | 12 | Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern) | SEASONALITY | 0.0204 |
| 35 |  | Activity Lifecycle | 15 | Across all fiscal_year values, Other has the lowest gen_amount among tied_untied values | OUTSTANDING_LAST | 0.0185 |
| 36 |  | Geo-Month Cash Cube | 14 | Across most measure values (7/9), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern) | LAST_TWO | 0.0145 |
| 37 |  | Geo-Month Cash Cube | 15 | Across most measure values (7/9), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern) | TOP_TWO | 0.0123 |
| 38 |  | GP Profile | 11 | Across most measure values (62/74), Mixed has the highest (varies) among social_composition values. Exceptions: overspend_vs_sanction_mean (SC-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values); households_tap_water_mean (ST-majority has the highest (varies) among social_composition values) and 9 others | OUTSTANDING_1 | 0.0158 |
| 39 |  | GP Profile | 12 | Across most measure values (60/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: evidence_uploads_mean (ST-majority accounts for the majority of (varies) among social_composition values); households_tap_water_mean (ST-majority accounts for the majority of (varies) among social_composition values); n_completed (no clear pattern) and 11 others | ATTRIBUTION | 0.0126 |
| 40 |  | GP Profile | 8 | Across most measure values (50/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values) and 21 others | TOP_TWO | 0.0133 |
| 41 |  | GP Profile | 10 | Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.0282 |
| 42 |  | Activity Lifecycle | 13 | Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in fund_sanctioned_total among gp_size values | LAST_TWO | 0.0256 |
| 43 |  | GP Performance | 12 | Across most social_composition values (2/3), n_admin_approvals forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern) | UNIMODALITY | 0.0204 |
| 44 |  | Geo-Month Cash Cube | 13 | Across most social_composition values (2/3), sanctions_count is increasing over fiscal_year. Exception: ST-majority (no clear pattern) | TREND | 0.0173 |
| 45 |  | GP Profile | 13 | Across most measure values (48/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values) and 23 others | TOP_TWO | 0.0044 |
| 46 |  | GP Performance | 13 | Across most measure values (16/28), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 9 others -- this is about how the total is spread, not about how much any one of them spends | EVENNESS | 0.0020 |

# WP-D11b — top-15 diff, `d619a72e4fe98d5f` against `a7f991c1df3771f9`

A finding is *the same finding* when its pattern type, measure, breakdown, slice, extending dimension and strategy all match; the score is not part of it. **averaged twin** = the finding rests on a `_mean` measure (its own measure, or one of the measures it compares). **band-headcount** = it breaks down or varies along a GP profile band while measuring a TOTAL.


## view1

15 ranked before, 15 now: **14 unchanged, 1 dropped, 1 new.** **0 of the 15 rest on an averaged twin.** Band-headcount findings: 0 before, 1 now; 0 of the earlier ones were displaced.


### The current top-15

- **#1** `EVENNESS` overspend_vs_plan by `block_name`, varied along `asset_category_label`
  - Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread)
- **#2** `EVENNESS` overspend_vs_sanction by `district_name`, varied along `asset_category_label`
  - Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not even
- **#3** `TOP_TWO` fund_untied_total by `output_type_label`, varied along `gp_name`
  - Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern)
- **#4** `OUTSTANDING_1` n_activities by `asset_category_label`, varied along `gp_name`
  - Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern)
- **#5** `OUTSTANDING_LAST` overspend_vs_plan by `status_label`, varied along `gp_name`
  - Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)
- **#6** `ATTRIBUTION` gen_amount by `status_label`, varied along `gp_name`
  - Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)
- **#7** `OUTSTANDING_1` beneficiaries_expected by `status_label`, varied along `gp_name`
  - Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)
- **#8** `OUTSTANDING_1` fund_untied_total by `theme`, varied along `gp_name`
  - Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values)
- **#9** `OUTSTANDING_LAST` overspend_vs_sanction by `output_type_label`, varied along `gp_name`
  - Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern)
- **#10** `ATTRIBUTION` evidence_uploads by `output_type_label`, varied along `gp_name`
  - Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern)
- **#11** `LAST_TWO` overspend_vs_plan by `output_type_label`, varied along `activity_for_label`
  - Across all activity_for_label values, Code 101 and Code 105 are lowest in overspend_vs_plan among output_type_label values
- **#12** `TOP_TWO` fund_tied_total by `focus_area_name`, varied along `activity_for_label`
  - Across all activity_for_label values, Drinking water and Sanitation lead in fund_tied_total among focus_area_name values
- **#13** `LAST_TWO` fund_sanctioned_total by `gp_size`, varied along `fiscal_year` — band-headcount; profile: gp_size
  - Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in fund_sanctioned_total among gp_size values
- **#14** `OUTSTANDING_LAST` fund_sanctioned_total by `gp_name`, varied along `fiscal_year`
  - Across all fiscal_year values, Chikilli has the lowest fund_sanctioned_total among gp_name values
- **#15** `OUTSTANDING_LAST` gen_amount by `tied_untied`, varied along `fiscal_year`
  - Across all fiscal_year values, Other has the lowest gen_amount among tied_untied values

### Dropped out (earlier rank shown)

- **#15** `TOP_TWO` n_activities by `status_label`, varied along `fiscal_year`
  - Across all fiscal_year values, Activity Approved and WORK ONGOING lead in n_activities among status_label values

## view2

15 ranked before, 15 now: **3 unchanged, 12 dropped, 12 new.** **5 of the 15 rest on an averaged twin.** Band-headcount findings: 0 before, 7 now; 0 of the earlier ones were displaced.


### The current top-15

- **#1** `TREND` activity_linked_expenditure by `(varies)`, varied along `temporal_grain`
  - Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)
- **#2** `LAST_TWO` payment_amount by `gp_size`, varied along `fiscal_year` — band-headcount; profile: gp_size
  - Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in payment_amount among gp_size values
- **#3** `TOP_TWO` activity_linked_expenditure by `gp_size`, varied along `fiscal_year` — band-headcount; profile: gp_size
  - Across all fiscal_year values, 2,500 to 5,000 and 5,000 to 10,000 lead in activity_linked_expenditure among gp_size values
- **#4** `TREND` activity_linked_expenditure by `month`, varied along `gp_size` — band-headcount; profile: gp_size
  - Across all gp_size values, activity_linked_expenditure is increasing over month
- **#5** `SEASONALITY` receipt_count by `quarter`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across all social_composition values, receipt_count shows seasonal pattern (PERIOD_12) over quarter
- **#6** `ATTRIBUTION` activity_linked_expenditure by `social_composition`, varied along `fiscal_year` — band-headcount; profile: social_composition
  - Across all fiscal_year values, Mixed accounts for the majority of activity_linked_expenditure among social_composition values
- **#7** `OUTSTANDING_LAST` payment_amount_mean by `social_composition`, varied along `fiscal_year` — **averaged twin**; profile: social_composition
  - Across most fiscal_year values (5/6), SC-majority has the lowest payment_amount_mean among social_composition values. Exception: 2025-2026 (different pattern)
- **#8** `OUTSTANDING_1` payment_count by `block_name`, varied along `fiscal_year`
  - Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern)
- **#9** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: social_composition
  - Across most measure values (7/9), Mixed accounts for the majority of (varies) among social_composition values. Exception: payment_amount_mean (different pattern); receipt_amount_mean (different pattern)
- **#10** `CHANGE_POINT` sanctions_count by `month`, varied along `gp_size` — band-headcount; profile: gp_size
  - Across most gp_size values (3/4), sanctions_count has a significant shift at 2020-10 in month. Exception: 10,000 and above (sanctions_count has a significant shift at 2021-01 in month)
- **#11** `SEASONALITY` payment_amount_mean by `month`, varied along `gp_size` — **averaged twin**; profile: gp_size
  - Across most gp_size values (3/4), payment_amount_mean shows seasonal pattern (PERIOD_12) over month. Exception: 10,000 and above (different pattern)
- **#12** `SEASONALITY` payment_count by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern)
- **#13** `TREND` sanctions_count by `fiscal_year`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), sanctions_count is increasing over fiscal_year. Exception: ST-majority (no clear pattern)
- **#14** `LAST_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, social_composition
  - Across most measure values (7/9), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)
- **#15** `TOP_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, social_composition
  - Across most measure values (7/9), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)

### Dropped out (earlier rank shown)

- **#4** `TREND` activity_linked_expenditure by `quarter`, varied along `district_name`
  - Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)
- **#5** `SEASONALITY` (varies) by `month`, varied along `measure` — **averaged twin**
  - Across most measure values (6/9), (varies) shows seasonal pattern (PERIOD_12) over month. Exception: activity_linked_expenditure ((varies) shows seasonal pattern (PERIOD_3) over month); sanctions_count (different pattern); sanctioned_amount
- **#6** `SEASONALITY` activity_linked_expenditure by `quarter`, varied along `district_name`
  - Across most district_name values (5/9), activity_linked_expenditure shows seasonal pattern (PERIOD_12) over quarter. Exceptions: Sundargarh (activity_linked_expenditure shows seasonal pattern (PERIOD_6) over quarter); Rayagada (activity_lin
- **#7** `SEASONALITY` receipt_count by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), receipt_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (different pattern)
- **#8** `TREND` sanctions_count by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), sanctions_count is increasing over (varies). Exception: month (different pattern)
- **#9** `TREND` activity_linked_expenditure by `quarter`, varied along `block_name`
  - Across most block_name values (9/16), activity_linked_expenditure is increasing over quarter. Exceptions: Barpali (different pattern); Bheden (different pattern); Rangeilunda (different pattern) and 4 others
- **#10** `CHANGE_POINT` (varies) by `month`, varied along `measure` — **averaged twin**
  - Across most measure values (6/9), (varies) has a significant shift at 2020-08 in month. Exception: activity_linked_expenditure ((varies) has a significant shift at 2020-11 in month); sanctions_count ((varies) has a significant shift at 2020
- **#11** `OUTSTANDING_1` (varies) by `district_name`, varied along `measure` — **averaged twin**
  - Across most measure values (6/9), Ganjam has the highest (varies) among district_name values. Exception: payment_count (different pattern); payment_amount_mean (different pattern); receipt_amount_mean (different pattern)
- **#12** `TREND` sanctioned_amount by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), sanctioned_amount is increasing over (varies). Exception: fiscal_year (no clear pattern)
- **#13** `TREND` activity_linked_expenditure by `(varies)`, varied along `temporal_grain`
  - Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)
- **#14** `OUTSTANDING_1` (varies) by `block_name`, varied along `measure` — **averaged twin**
  - Across most measure values (6/9), Bheden has the highest (varies) among block_name values. Exception: activity_linked_expenditure (Barpali has the highest (varies) among block_name values); sanctions_count (Barpali has the highest (varies) 
- **#15** `TREND` payment_amount_mean by `(varies)`, varied along `temporal_grain` — **averaged twin**
  - Across most temporal_grain values (2/3), payment_amount_mean is increasing over (varies). Exception: fiscal_year (no clear pattern)

## view3

2 ranked before, 15 now: **1 unchanged, 1 dropped, 14 new.** **11 of the 15 rest on an averaged twin.** Band-headcount findings: 0 before, 4 now; 0 of the earlier ones were displaced.


### The current top-15

- **#1** `TREND` expenditure_total_mean by `fiscal_year`, varied along `gp_size` — **averaged twin**; profile: gp_size
  - Across most gp_size values (3/4), expenditure_total_mean is decreasing over fiscal_year. Exception: 10,000 and above (no clear pattern)
- **#2** `EVENNESS` overspend_vs_plan_mean by `block_name`, varied along `social_composition` — **averaged twin**; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_plan_mean is evenly distributed across block_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them
- **#3** `EVENNESS` overspend_vs_plan by `district_name`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_plan is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is
- **#4** `EVENNESS` overspend_vs_sanction_mean by `gp_name`, varied along `social_composition` — **averaged twin**; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_sanction_mean is evenly distributed across gp_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of the
- **#5** `UNIMODALITY` n_admin_approvals_mean by `fiscal_year`, varied along `social_composition` — **averaged twin**; profile: social_composition
  - Across most social_composition values (2/3), n_admin_approvals_mean forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)
- **#6** `TREND` expenditure_total by `fiscal_year`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), expenditure_total is decreasing over fiscal_year. Exception: SC-majority (different pattern)
- **#7** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_panchayat_bhawan, social_composition
  - Across most measure values (17/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition values); sanctioned_total_m
- **#8** `OUTSTANDING_1` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_panchayat_bhawan, social_composition
  - Across most measure values (19/28), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (ST-majority has the 
- **#9** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: social_composition
  - Across most measure values (15/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); planned_cost_mean 
- **#10** `OUTSTANDING_1` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_csc, social_composition
  - Across most measure values (19/28), Mixed has the highest (varies) among social_composition values. Exceptions: overspend_vs_sanction_mean (SC-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-maj
- **#11** `EVENNESS` overspend_vs_sanction by `block_name`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is a
- **#12** `UNIMODALITY` n_admin_approvals by `fiscal_year`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), n_admin_approvals forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)
- **#13** `EVENNESS` (varies) by `gp_name`, varied along `measure` — **averaged twin**
  - Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 5 others -- this is about how t
- **#14** `TOP_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, has_panchayat_bhawan
  - Across most measure values (16/28), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); planned_cost_mean (10,
- **#15** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_csc, social_composition
  - Across most measure values (18/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: evidence_uploads_mean (ST-majority accounts for the majority of (varies) among social_composition values); n_comple

### Dropped out (earlier rank shown)

- **#1** `TREND` sanctioned_total by `fiscal_year`, varied along `district_name`
  - Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others

## view4

0 ranked before, 13 now: **0 unchanged, 0 dropped, 13 new.** **11 of the 13 rest on an averaged twin.** Band-headcount findings: 0 before, 2 now; 0 of the earlier ones were displaced.


### The current top-15

- **#1** `EVENNESS` overspend_vs_plan_mean by `block_name`, varied along `social_composition` — **averaged twin**; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_plan_mean is evenly distributed across block_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them
- **#2** `EVENNESS` overspend_vs_plan by `district_name`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_plan is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is
- **#3** `EVENNESS` overspend_vs_sanction_mean by `gp_name`, varied along `social_composition` — **averaged twin**; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_sanction_mean is evenly distributed across gp_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of the
- **#4** `OUTSTANDING_1` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: social_composition
  - Across most measure values (57/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (ST-majority has the highest (varies) among social_composition values); households_tap_water_mean (ST-majority has t
- **#5** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: social_composition
  - Across most measure values (53/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); planned_cost_mean 
- **#6** `OUTSTANDING_1` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_panchayat_bhawan, social_composition
  - Across most measure values (61/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (ST-majority has the 
- **#7** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_panchayat_bhawan, social_composition
  - Across most measure values (58/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition values); households_tap_wat
- **#8** `TOP_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, has_panchayat_bhawan
  - Across most measure values (50/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and abov
- **#9** `TOP_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, social_composition
  - Across most measure values (46/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: schools_pre_primary (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); households_tap_water
- **#10** `EVENNESS` overspend_vs_sanction by `block_name`, varied along `social_composition` — band-headcount; profile: social_composition
  - Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is a
- **#11** `OUTSTANDING_1` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_csc, social_composition
  - Across most measure values (62/74), Mixed has the highest (varies) among social_composition values. Exceptions: overspend_vs_sanction_mean (SC-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-maj
- **#12** `ATTRIBUTION` (varies) by `social_composition`, varied along `measure` — **averaged twin**; profile: has_csc, social_composition
  - Across most measure values (60/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: evidence_uploads_mean (ST-majority accounts for the majority of (varies) among social_composition values); househol
- **#13** `TOP_TWO` (varies) by `gp_size`, varied along `measure` — **averaged twin**; profile: gp_size, has_csc
  - Across most measure values (48/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and abov

## Summary

| view | before | now | unchanged | new | dropped | now resting on a twin | band-headcount before | band-headcount now | band-headcount displaced |
|---|---|---|---|---|---|---|---|---|---|
| view1 | 15 | 15 | 14 | 1 | 1 | 0 | 0 | 1 | 0 |
| view2 | 15 | 15 | 3 | 12 | 12 | 5 | 0 | 7 | 0 |
| view3 | 2 | 15 | 1 | 14 | 1 | 11 | 0 | 4 | 0 |
| view4 | 0 | 13 | 0 | 13 | 0 | 11 | 0 | 2 | 0 |

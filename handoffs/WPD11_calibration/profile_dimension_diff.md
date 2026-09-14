# WP-D11 — what the GP profile dimensions changed in the top-15s

Baseline candidate set `a7f991c1df3771f9` (pre-Amendment B, 3 views) against
the WP-D11 set (4 views, +6 profile dimensions at sample scale).

A finding is *the same finding* across the two runs when its pattern type,
measure, breakdown, slice and extending dimension all match. Score is not
part of the signature: the same statement re-scored is the same statement.


## view1

15 ranked before, 15 after. **14 unchanged, 1 dropped out, 1 new.** Of the 1 new, **1 use a profile dimension**; 1 of the 15 findings in the new top list do.


### Entered

- `LAST_TWO` **fund_sanctioned_total** by `gp_size`, varied along `fiscal_year` — **profile: gp_size**
  - Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in fund_sanctioned_total among gp_size values

### Dropped out

- `TOP_TWO` **n_activities** by `status_label`, varied along `fiscal_year`
  - Across all fiscal_year values, Activity Approved and WORK ONGOING lead in n_activities among status_label values

## view2

15 ranked before, 15 after. **3 unchanged, 12 dropped out, 12 new.** Of the 12 new, **12 use a profile dimension**; 12 of the 15 findings in the new top list do.


### Entered

- `LAST_TWO` **payment_amount** by `gp_size`, varied along `fiscal_year` — **profile: gp_size**
  - Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in payment_amount among gp_size values
- `TOP_TWO` **activity_linked_expenditure** by `gp_size`, varied along `fiscal_year` — **profile: gp_size**
  - Across all fiscal_year values, 2,500 to 5,000 and 5,000 to 10,000 lead in activity_linked_expenditure among gp_size values
- `TREND` **activity_linked_expenditure** by `month`, varied along `gp_size` — **profile: gp_size**
  - Across all gp_size values, activity_linked_expenditure is increasing over month
- `SEASONALITY` **receipt_count** by `quarter`, varied along `social_composition` — **profile: social_composition**
  - Across all social_composition values, receipt_count shows seasonal pattern (PERIOD_12) over quarter
- `ATTRIBUTION` **activity_linked_expenditure** by `social_composition`, varied along `fiscal_year` — **profile: social_composition**
  - Across all fiscal_year values, Mixed accounts for the majority of activity_linked_expenditure among social_composition values
- `OUTSTANDING_LAST` **payment_amount_mean** by `social_composition`, varied along `fiscal_year` — **profile: social_composition**
  - Across most fiscal_year values (5/6), SC-majority has the lowest payment_amount_mean among social_composition values. Exception: 2025-2026 (different pattern)
- `ATTRIBUTION` **(varies)** by `social_composition`, varied along `measure` — **profile: social_composition**
  - Across most measure values (7/9), Mixed accounts for the majority of (varies) among social_composition values. Exception: payment_amount_mean (different pattern); receipt_amount_mean (different pattern)
- `CHANGE_POINT` **sanctions_count** by `month`, varied along `gp_size` — **profile: gp_size**
  - Across most gp_size values (3/4), sanctions_count has a significant shift at 2020-10 in month. Exception: 10,000 and above (sanctions_count has a significant shift at 2021-01 in month)
- `SEASONALITY` **payment_amount_mean** by `month`, varied along `gp_size` — **profile: gp_size**
  - Across most gp_size values (3/4), payment_amount_mean shows seasonal pattern (PERIOD_12) over month. Exception: 10,000 and above (different pattern)
- `TREND` **sanctions_count** by `fiscal_year`, varied along `social_composition` — **profile: social_composition**
  - Across most social_composition values (2/3), sanctions_count is increasing over fiscal_year. Exception: ST-majority (no clear pattern)
- `LAST_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size, social_composition**
  - Across most measure values (7/9), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)
- `TOP_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size, social_composition**
  - Across most measure values (7/9), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)

### Dropped out

- `TREND` **activity_linked_expenditure** by `quarter`, varied along `district_name`
  - Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)
- `SEASONALITY` **(varies)** by `month`, varied along `measure`
  - Across most measure values (6/9), (varies) shows seasonal pattern (PERIOD_12) over month. Exception: activity_linked_expenditure ((varies) shows seasonal pattern (PERIOD_3) over month); sanctions_count (different pattern
- `SEASONALITY` **activity_linked_expenditure** by `quarter`, varied along `district_name`
  - Across most district_name values (5/9), activity_linked_expenditure shows seasonal pattern (PERIOD_12) over quarter. Exceptions: Sundargarh (activity_linked_expenditure shows seasonal pattern (PERIOD_6) over quarter); Ra
- `SEASONALITY` **receipt_count** by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), receipt_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (different pattern)
- `TREND` **sanctions_count** by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), sanctions_count is increasing over (varies). Exception: month (different pattern)
- `TREND` **activity_linked_expenditure** by `quarter`, varied along `block_name`
  - Across most block_name values (9/16), activity_linked_expenditure is increasing over quarter. Exceptions: Barpali (different pattern); Bheden (different pattern); Rangeilunda (different pattern) and 4 others
- `CHANGE_POINT` **(varies)** by `month`, varied along `measure`
  - Across most measure values (6/9), (varies) has a significant shift at 2020-08 in month. Exception: activity_linked_expenditure ((varies) has a significant shift at 2020-11 in month); sanctions_count ((varies) has a signi
- `OUTSTANDING_1` **(varies)** by `district_name`, varied along `measure`
  - Across most measure values (6/9), Ganjam has the highest (varies) among district_name values. Exception: payment_count (different pattern); payment_amount_mean (different pattern); receipt_amount_mean (different pattern)
- `TREND` **sanctioned_amount** by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), sanctioned_amount is increasing over (varies). Exception: fiscal_year (no clear pattern)
- `TREND` **activity_linked_expenditure** by `(varies)`, varied along `temporal_grain`
  - Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)
- `OUTSTANDING_1` **(varies)** by `block_name`, varied along `measure`
  - Across most measure values (6/9), Bheden has the highest (varies) among block_name values. Exception: activity_linked_expenditure (Barpali has the highest (varies) among block_name values); sanctions_count (Barpali has t
- `TREND` **payment_amount_mean** by `(varies)`, varied along `temporal_grain`
  - Across most temporal_grain values (2/3), payment_amount_mean is increasing over (varies). Exception: fiscal_year (no clear pattern)

## view3

2 ranked before, 15 after. **0 unchanged, 2 dropped out, 15 new.** Of the 15 new, **15 use a profile dimension**; 15 of the 15 findings in the new top list do.


### Entered

- `TOP_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size**
  - Across most measure values (15/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: n_completed (10,000 and above and 2,500 to 5,000 lead in (varies) among gp_size values); overspend_
- `ATTRIBUTION` **(varies)** by `social_composition`, varied along `measure` — **profile: social_composition**
  - Across most measure values (15/18), Mixed accounts for the majority of (varies) among social_composition values. Exception: n_completed (ST-majority accounts for the majority of (varies) among social_composition values);
- `TREND` **expenditure_total** by `fiscal_year`, varied along `gp_size` — **profile: gp_size**
  - Across most gp_size values (3/4), expenditure_total is decreasing over fiscal_year. Exception: 10,000 and above (no clear pattern)
- `LAST_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size**
  - Across most measure values (13/18), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: planned_cost (different pattern); overspend_vs_plan (different pattern); overspend_vs_sanction
- `EVENNESS` **overspend_vs_plan** by `block_name`, varied along `social_composition` — **profile: social_composition**
  - Across most social_composition values (2/3), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spre
- `EVENNESS` **overspend_vs_sanction** by `district_name`, varied along `social_composition` — **profile: social_composition**
  - Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not e
- `UNIMODALITY` **n_admin_approvals** by `fiscal_year`, varied along `social_composition` — **profile: social_composition**
  - Across most social_composition values (2/3), n_admin_approvals forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)
- `TOP_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size, has_panchayat_bhawan**
  - Across most measure values (16/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); ove
- `OUTSTANDING_1` **(varies)** by `social_composition`, varied along `measure` — **profile: gp_size, social_composition**
  - Across most measure values (15/18), Mixed has the highest (varies) among social_composition values. Exception: overspend_vs_plan (ST-majority has the highest (varies) among social_composition values); overspend_vs_sancti
- `ATTRIBUTION` **(varies)** by `social_composition`, varied along `measure` — **profile: remoteness, social_composition**
  - Across most measure values (15/18), Mixed accounts for the majority of (varies) among social_composition values. Exception: n_completed (ST-majority accounts for the majority of (varies) among social_composition values);
- `TREND` **sanctioned_total** by `fiscal_year`, varied along `social_composition` — **profile: social_composition**
  - Across most social_composition values (2/3), sanctioned_total is decreasing over fiscal_year. Exception: SC-majority (different pattern)
- `LAST_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size, social_composition**
  - Across most measure values (13/18), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: overspend_vs_plan (2,500 to 5,000 and 5,000 to 10,000 are lowest in (varies) among gp_size val
- `OUTSTANDING_1` **(varies)** by `block_name`, varied along `measure` — **profile: has_csc**
  - Across most measure values (12/18), Bhubaneswar has the highest (varies) among block_name values. Exceptions: n_completed (Kalimela has the highest (varies) among block_name values); n_costless (different pattern); plann
- `OUTSTANDING_1` **(varies)** by `social_composition`, varied along `measure` — **profile: has_panchayat_bhawan, social_composition**
  - Across most measure values (15/18), Mixed has the highest (varies) among social_composition values. Exception: overspend_vs_plan (SC-majority has the highest (varies) among social_composition values); n_completed (ST-maj
- `TOP_TWO` **(varies)** by `gp_size`, varied along `measure` — **profile: gp_size, social_composition**
  - Across most measure values (15/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); ove

### Dropped out

- `TREND` **sanctioned_total** by `fiscal_year`, varied along `district_name`
  - Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 
- `EVENNESS` **(varies)** by `gp_name`, varied along `measure`
  - Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 5 others --

## view4

**New view.** 15 ranked finding(s); there is no baseline to
diff against, so every one of them is new by construction.

- **#1** `OUTSTANDING_1` (varies) by social_composition — uses **social_composition**
  - Across nearly all measure values (56/60), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (ST-majority has the highest (varies) among social_composition values); job_card_holders (
- **#2** `ATTRIBUTION` (varies) by social_composition — uses **social_composition**
  - Across most measure values (53/60), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values)
- **#3** `EVENNESS` overspend_vs_plan by block_name — uses **social_composition**
  - Across most social_composition values (2/3), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spre
- **#4** `EVENNESS` overspend_vs_sanction by district_name — uses **social_composition**
  - Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not e
- **#5** `LAST_TWO` (varies) by gp_size — uses **gp_size**
  - Across most measure values (35/60), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: atms (2,500 to 5,000 and Under 2,500 are lowest in (varies) among gp_size values); population_
- **#6** `TOP_TWO` (varies) by gp_size — uses **gp_size, has_panchayat_bhawan**
  - Across most measure values (49/60), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); a
- **#7** `OUTSTANDING_1` (varies) by social_composition — uses **has_panchayat_bhawan, social_composition**
  - Across nearly all measure values (56/60), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); drinking_water_sou
- **#8** `ATTRIBUTION` (varies) by social_composition — uses **has_panchayat_bhawan, social_composition**
  - Across nearly all measure values (55/60), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition v
- **#9** `OUTSTANDING_1` (varies) by gp_size — uses **gp_size, social_composition**
  - Across most measure values (33/60), 5,000 to 10,000 has the highest (varies) among gp_size values. Exceptions: disaster_rescue_centres (2,500 to 5,000 has the highest (varies) among gp_size values); evidence_uploads (2,5
- **#10** `TOP_TWO` (varies) by gp_size — uses **gp_size, social_composition**
  - Across most measure values (45/60), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: schools_pre_primary (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); 
- **#11** `LAST_TWO` (varies) by gp_size — uses **gp_size, has_panchayat_bhawan**
  - Across most measure values (35/60), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: wellbeing_centres (5,000 to 10,000 and Under 2,500 are lowest in (varies) among gp_size values
- **#12** `OUTSTANDING_1` (varies) by social_composition — uses **has_csc, social_composition**
  - Across nearly all measure values (57/60), Mixed has the highest (varies) among social_composition values. Exception: n_completed (no clear pattern); overspend_vs_plan (different pattern); overspend_vs_sanction (different
- **#13** `ATTRIBUTION` (varies) by social_composition — uses **has_csc, social_composition**
  - Across nearly all measure values (56/60), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (no clear pattern); drinking_water_sources (different pattern); overspend_vs_
- **#14** `EVENNESS` overspend_vs_plan by gp_name — uses **social_composition**
  - Across most social_composition values (2/3), overspend_vs_plan is spread evenly across gp_name values -- it belongs to all of them and no single gp_name accounts for it. Uneven only in: ST-majority (not evenly spread) --
- **#15** `TOP_TWO` (varies) by gp_size — uses **gp_size**
  - Across most measure values (40/60), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: schools_secondary (5,000 to 10,000 and Under 2,500 lead in (varies) among gp_size values); atms (1

## Summary

| view | new | dropped | unchanged | new using a profile band | all findings using one |
|---|---|---|---|---|---|
| view1 | 1 | 1 | 14 | 1 | 1 |
| view2 | 12 | 12 | 3 | 12 | 12 |
| view3 | 15 | 2 | 0 | 15 | 15 |
| view4 | 15 | 0 | 0 | 15 | 15 |
| **total** | **43** | **15** | **17** | **43** | |

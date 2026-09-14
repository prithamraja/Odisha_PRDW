# Gram Panchayat Report Card by Year -- top 15 findings

*View `view3`, GP Performance. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.5474  (conciseness 0.5474 x impact 1.0000)

**Across most gp_size values (3/4), expenditure_total_mean is decreasing over fiscal_year. Exception: 10,000 and above (no clear pattern)**

- pattern: `TREND`, measure `expenditure_total_mean`, broken down by `fiscal_year`
- slice: (whole view), varied along `gp_size` (subspace), 4 members
- commonness: ('DECREASING',) in 3/4 (75%): 5,000 to 10,000 people, 2,500 to 5,000 people, Under 2,500 people
- exceptions: 10,000 people and above [NO_PATTERN]
- figures: top: 2020-2021 = Rs 26.94 lakh per Gram Panchayat-year; top: 2021-2022 = Rs 22.76 lakh per Gram Panchayat-year; top: 2022-2023 = Rs 22.21 lakh per Gram Panchayat-year
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_plan_mean is evenly distributed across block_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan_mean`, broken down by `block_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: top: Bhubaneswar = Rs -14.58 lakh per Gram Panchayat-year; top: Lahunipara = Rs -15.10 lakh per Gram Panchayat-year; top: Baranga = Rs -18.40 lakh per Gram Panchayat-year
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_plan is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan`, broken down by `district_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -51.96 crore; top: Rayagada = Rs -1.24 crore; top: Sundargarh = Rs -2.19 crore; top: Khordha = Rs -2.63 crore
- deterministic framing: evenness reframed (A3); per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_sanction_mean is evenly distributed across gp_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction_mean`, broken down by `gp_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: top: Chikilli = Rs 0 per Gram Panchayat-year; top: Govindapur = Rs -1.16 lakh per Gram Panchayat-year; top: Hirlipali = Rs -1.75 lakh per Gram Panchayat-year
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), n_admin_approvals_mean forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)**

- pattern: `UNIMODALITY`, measure `n_admin_approvals_mean`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('PEAK', '2024-2025') in 2/3 (67%): SC-majority, ST-majority
- exceptions: Mixed [NO_PATTERN]
- figures: 2024-2025 = 19.6 approval records per Gram Panchayat-year; top: 2023-2024 = 21.2 approval records per Gram Panchayat-year; top: 2024-2025 = 19.6 approval records per Gram Panchayat-year; top: 2020-2021 = 18.1 approval records per Gram Panchayat-year
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), expenditure_total is decreasing over fiscal_year. Exception: SC-majority (different pattern)**

- pattern: `TREND`, measure `expenditure_total`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('DECREASING',) in 2/3 (67%): Mixed, ST-majority
- exceptions: SC-majority [TYPE_CHANGE]
- figures: total Rs 25.35 crore; top: 2020-2021 = Rs 5.39 crore (21.3%); top: 2021-2022 = Rs 4.55 crore (18.0%); top: 2022-2023 = Rs 4.44 crore (17.5%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.1916  (conciseness 0.2710 x impact 0.7071)

**Across most measure values (17/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition values); sanctioned_total_mean (no clear pattern); overspend_vs_plan (different pattern) and 8 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 28 members
- commonness: ('Mixed',) in 17/28 (61%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, payment_amount_mean, receipt_amount_mean
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('SC-majority',) | sanctioned_total_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | planned_cost_mean [TYPE_CHANGE] | expenditure_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.1784  (conciseness 0.2522 x impact 0.7071)

**Across most measure values (19/28), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (ST-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values) and 6 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 28 members
- commonness: ('Mixed',) in 19/28 (68%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, expenditure_total_mean, payment_amount_mean, receipt_amount_mean
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('SC-majority',) | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | sanctioned_total_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.1489  (conciseness 0.1489 x impact 1.0000)

**Across most measure values (15/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); planned_cost_mean (no clear pattern); expenditure_total_mean (no clear pattern) and 10 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: (whole view), varied along `measure` (measure), 28 members
- commonness: ('Mixed',) in 15/28 (54%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | planned_cost_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.1405  (conciseness 0.2202 x impact 0.6382)

**Across most measure values (19/28), Mixed has the highest (varies) among social_composition values. Exceptions: overspend_vs_sanction_mean (SC-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values); n_completed (no clear pattern) and 6 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: has_csc=Yes, varied along `measure` (measure), 28 members
- commonness: ('Mixed',) in 19/28 (68%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, expenditure_total_mean, payment_amount_mean, receipt_amount_mean
- exceptions: overspend_vs_sanction_mean [HIGHLIGHT_CHANGE] ('SC-majority',) | evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | n_completed [NO_PATTERN] | sanctioned_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction`, broken down by `block_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -5.02 crore; top: Khallikote = Rs 0; top: Tangi Choudwar = Rs -6.94 lakh; top: Attabira = Rs -10.48 lakh
- deterministic framing: evenness reframed (A3); per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), n_admin_approvals forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)**

- pattern: `UNIMODALITY`, measure `n_admin_approvals`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('PEAK', '2024-2025') in 2/3 (67%): SC-majority, ST-majority
- exceptions: Mixed [NO_PATTERN]
- figures: total 2,101 approval records; 2024-2025 = 391 approval records (18.6%); top: 2023-2024 = 424 approval records (20.2%); top: 2024-2025 = 391 approval records (18.6%); top: 2020-2021 = 362 approval records (17.2%)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.0556  (conciseness 0.2308 x impact 0.2410)

**Across most measure values (16/28), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 9 others -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `(varies)`, broken down by `gp_name`
- slice: district_name=Bargarh, varied along `measure` (measure), 28 members
- commonness: ('EVEN',) in 16/28 (57%): n_activities, n_costless, expenditure_total, overspend_vs_plan, overspend_vs_sanction, n_admin_approvals, n_tech_approvals, n_ongoing, n_with_evidence, evidence_uploads, n_activities_mean, expenditure_total_mean, overspend_vs_plan_mean, overspend_vs_sanction_mean, n_admin_approvals_mean, evidence_uploads_mean
- exceptions: n_plans [NO_PATTERN] | sanctioned_total [NO_PATTERN] | n_completed [NO_PATTERN] | sanctioned_total_mean [NO_PATTERN] | n_costed [TYPE_CHANGE] | planned_cost [TYPE_CHANGE] | payment_amount [TYPE_CHANGE] | receipt_amount [TYPE_CHANGE] | n_abandoned [TYPE_CHANGE] | planned_cost_mean [TYPE_CHANGE] | payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: evenness reframed (A3); per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #14  score 0.0556  (conciseness 0.0787 x impact 0.7071)

**Across most measure values (16/28), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); overspend_vs_plan_mean (2,500 to 5,000 and Under 2,500 lead in (varies) among gp_size values) and 9 others**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 28 members
- commonness: ('2,500 to 5,000 people', '5,000 to 10,000 people') in 16/28 (57%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_completed, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 people and above', 'Under 2,500 people') | planned_cost_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('2,500 to 5,000 people', 'Under 2,500 people') | n_activities_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #15  score 0.1387  (conciseness 0.2173 x impact 0.6382)

**Across most measure values (18/28), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: evidence_uploads_mean (ST-majority accounts for the majority of (varies) among social_composition values); n_completed (no clear pattern); sanctioned_total_mean (no clear pattern) and 7 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: has_csc=Yes, varied along `measure` (measure), 28 members
- commonness: ('Mixed',) in 18/28 (64%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, payment_amount_mean, receipt_amount_mean
- exceptions: evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | n_completed [NO_PATTERN] | sanctioned_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | expenditure_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________

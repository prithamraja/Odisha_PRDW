# Gram Panchayat Profile - Who Lives There and What They Have -- top 13 findings

*View `view4`, GP Profile. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_plan_mean is evenly distributed across block_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan_mean`, broken down by `block_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: top: Bhubaneswar = Rs -87.50 lakh per Gram Panchayat; top: Lahunipara = Rs -90.62 lakh per Gram Panchayat; top: Baranga = Rs -1.10 crore per Gram Panchayat
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_plan is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan`, broken down by `district_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -51.96 crore; top: Rayagada = Rs -1.24 crore; top: Sundargarh = Rs -2.19 crore; top: Khordha = Rs -2.63 crore
- deterministic framing: evenness reframed (A3); per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_sanction_mean is evenly distributed across gp_name values. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction_mean`, broken down by `gp_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: top: Chikilli = Rs 0 per Gram Panchayat; top: Govindapur = Rs -6.94 lakh per Gram Panchayat; top: Hirlipali = Rs -10.48 lakh per Gram Panchayat
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.3890  (conciseness 0.3890 x impact 1.0000)

**Across most measure values (57/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (ST-majority has the highest (varies) among social_composition values); households_tap_water_mean (ST-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (SC-majority has the highest (varies) among social_composition values) and 14 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: (whole view), varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 57/74 (77%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, population_general, households, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, drinking_water_sources, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, overspend_vs_sanction_mean
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | households_tap_water_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('SC-majority',) | planned_cost_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | household_toilets_mean [NO_PATTERN] | job_card_holders [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE] | osr_collected_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.3673  (conciseness 0.3673 x impact 1.0000)

**Across most measure values (53/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); planned_cost_mean (no clear pattern); expenditure_total_mean (no clear pattern) and 18 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: (whole view), varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 53/74 (72%): population_total, population_male, population_female, population_children, population_sc, population_obc, population_general, households, shgs, wards, revenue_villages, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, drinking_water_sources, households_tap_water, household_toilets, community_sanitary_complexes, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | planned_cost_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | household_toilets_mean [NO_PATTERN] | population_st [TYPE_CHANGE] | job_card_holders [TYPE_CHANGE] | villages_mapped_lgd [TYPE_CHANGE] | solid_waste_centres [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE] | households_tap_water_mean [TYPE_CHANGE] | osr_collected_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.3528  (conciseness 0.4989 x impact 0.7071)

**Across most measure values (61/74), Mixed has the highest (varies) among social_composition values. Exceptions: n_completed (SC-majority has the highest (varies) among social_composition values); overspend_vs_plan_mean (ST-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values) and 10 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 61/74 (82%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, population_general, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, expenditure_total_mean, payment_amount_mean, receipt_amount_mean, osr_collected_mean
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('SC-majority',) | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | households_tap_water_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | household_toilets_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | sanctioned_total_mean [NO_PATTERN] | drinking_water_sources [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.3235  (conciseness 0.4575 x impact 0.7071)

**Across most measure values (58/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: n_completed (SC-majority accounts for the majority of (varies) among social_composition values); households_tap_water_mean (ST-majority accounts for the majority of (varies) among social_composition values); household_toilets_mean (ST-majority accounts for the majority of (varies) among social_composition values) and 13 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 58/74 (78%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, population_general, households, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, payment_amount_mean, receipt_amount_mean, osr_collected_mean
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('SC-majority',) | households_tap_water_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | household_toilets_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | sanctioned_total_mean [NO_PATTERN] | job_card_holders [TYPE_CHANGE] | drinking_water_sources [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | planned_cost_mean [TYPE_CHANGE] | expenditure_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.1658  (conciseness 0.2344 x impact 0.7071)

**Across most measure values (50/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values) and 21 others**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 74 members
- commonness: ('2,500 to 5,000 people', '5,000 to 10,000 people') in 50/74 (68%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_higher_secondary, health_sub_centres, ayurvedic_clinics, drinking_water_sources, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, rural_libraries, bus_stands_with_water, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_completed, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, osr_collected_mean
- exceptions: population_general [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | atms [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | planned_cost_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | household_toilets_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | wellbeing_centres [HIGHLIGHT_CHANGE] ('10,000 people and above', '2,500 to 5,000 people') | overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 people and above', 'Under 2,500 people') | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('2,500 to 5,000 people', 'Under 2,500 people') | n_activities_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN] | schools_secondary [TYPE_CHANGE] | primary_health_centres [TYPE_CHANGE] | dispensaries [TYPE_CHANGE] | children_parks [TYPE_CHANGE] | disaster_rescue_centres [TYPE_CHANGE] | seed_centres [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | households_tap_water_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.1552  (conciseness 0.1945 x impact 0.7982)

**Across most measure values (46/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: schools_pre_primary (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); households_tap_water (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values) and 25 others**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: social_composition=Mixed, varied along `measure` (measure), 74 members
- commonness: ('2,500 to 5,000 people', '5,000 to 10,000 people') in 46/74 (62%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, health_sub_centres, primary_health_centres, dispensaries, ayurvedic_clinics, drinking_water_sources, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, osr_collected_mean
- exceptions: schools_pre_primary [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | households_tap_water [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | planned_cost_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | household_toilets_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 people and above', 'Under 2,500 people') | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('2,500 to 5,000 people', 'Under 2,500 people') | n_activities_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN] | population_general [TYPE_CHANGE] | schools_primary [TYPE_CHANGE] | schools_secondary [TYPE_CHANGE] | schools_higher_secondary [TYPE_CHANGE] | wellbeing_centres [TYPE_CHANGE] | household_toilets [TYPE_CHANGE] | atms [TYPE_CHANGE] | rural_libraries [TYPE_CHANGE] | children_parks [TYPE_CHANGE] | disaster_rescue_centres [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | n_completed [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | households_tap_water_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction`, broken down by `block_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -5.02 crore; top: Khallikote = Rs 0; top: Tangi Choudwar = Rs -6.94 lakh; top: Attabira = Rs -10.48 lakh
- deterministic framing: evenness reframed (A3); per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.3208  (conciseness 0.5026 x impact 0.6382)

**Across most measure values (62/74), Mixed has the highest (varies) among social_composition values. Exceptions: overspend_vs_sanction_mean (SC-majority has the highest (varies) among social_composition values); evidence_uploads_mean (ST-majority has the highest (varies) among social_composition values); households_tap_water_mean (ST-majority has the highest (varies) among social_composition values) and 9 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: has_csc=Yes, varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 62/74 (84%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, population_general, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, drinking_water_sources, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, expenditure_total_mean, payment_amount_mean, receipt_amount_mean, osr_collected_mean
- exceptions: overspend_vs_sanction_mean [HIGHLIGHT_CHANGE] ('SC-majority',) | evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | households_tap_water_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | household_toilets_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | n_completed [NO_PATTERN] | sanctioned_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.3024  (conciseness 0.4738 x impact 0.6382)

**Across most measure values (60/74), Mixed accounts for the majority of (varies) among social_composition values. Exceptions: evidence_uploads_mean (ST-majority accounts for the majority of (varies) among social_composition values); households_tap_water_mean (ST-majority accounts for the majority of (varies) among social_composition values); n_completed (no clear pattern) and 11 others**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: has_csc=Yes, varied along `measure` (measure), 74 members
- commonness: ('Mixed',) in 60/74 (81%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, population_general, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_secondary, schools_higher_secondary, health_sub_centres, primary_health_centres, wellbeing_centres, dispensaries, ayurvedic_clinics, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, atms, rural_libraries, children_parks, disaster_rescue_centres, bus_stands_with_water, seed_centres, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, planned_cost_mean, payment_amount_mean, receipt_amount_mean, osr_collected_mean
- exceptions: evidence_uploads_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | households_tap_water_mean [HIGHLIGHT_CHANGE] ('ST-majority',) | n_completed [NO_PATTERN] | sanctioned_total_mean [NO_PATTERN] | n_admin_approvals_mean [NO_PATTERN] | drinking_water_sources [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_activities_mean [TYPE_CHANGE] | expenditure_total_mean [TYPE_CHANGE] | overspend_vs_plan_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | household_toilets_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.1241  (conciseness 0.1944 x impact 0.6382)

**Across most measure values (48/74), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exceptions: population_general (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); atms (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values); planned_cost_mean (10,000 and above and 5,000 to 10,000 lead in (varies) among gp_size values) and 23 others**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: has_csc=Yes, varied along `measure` (measure), 74 members
- commonness: ('2,500 to 5,000 people', '5,000 to 10,000 people') in 48/74 (65%): population_total, population_male, population_female, population_children, population_sc, population_st, population_obc, households, job_card_holders, shgs, wards, revenue_villages, villages_mapped_lgd, anganwadi_centres, schools_pre_primary, schools_primary, schools_higher_secondary, health_sub_centres, ayurvedic_clinics, drinking_water_sources, households_tap_water, household_toilets, community_sanitary_complexes, solid_waste_centres, common_service_centres, banks, bus_stands_with_water, osr_collected, laptops, printers, scanners, sports_courts, n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads, osr_collected_mean
- exceptions: population_general [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | atms [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | planned_cost_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | households_tap_water_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | household_toilets_mean [HIGHLIGHT_CHANGE] ('10,000 people and above', '5,000 to 10,000 people') | overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 people and above', 'Under 2,500 people') | overspend_vs_plan_mean [HIGHLIGHT_CHANGE] ('2,500 to 5,000 people', 'Under 2,500 people') | n_completed [NO_PATTERN] | n_activities_mean [NO_PATTERN] | expenditure_total_mean [NO_PATTERN] | payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN] | schools_secondary [TYPE_CHANGE] | primary_health_centres [TYPE_CHANGE] | wellbeing_centres [TYPE_CHANGE] | dispensaries [TYPE_CHANGE] | rural_libraries [TYPE_CHANGE] | children_parks [TYPE_CHANGE] | disaster_rescue_centres [TYPE_CHANGE] | seed_centres [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | sanctioned_total_mean [TYPE_CHANGE] | overspend_vs_sanction_mean [TYPE_CHANGE] | n_admin_approvals_mean [TYPE_CHANGE] | evidence_uploads_mean [TYPE_CHANGE] | shgs_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________

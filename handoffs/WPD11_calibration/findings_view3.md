# Gram Panchayat Report Card by Year -- top 15 findings

*View `view3`, GP Performance. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.5520  (conciseness 0.5520 x impact 1.0000)

**Across most measure values (15/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: n_completed (10,000 and above and 2,500 to 5,000 lead in (varies) among gp_size values); overspend_vs_plan (different pattern); overspend_vs_sanction (different pattern)**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: (whole view), varied along `measure` (measure), 18 members
- commonness: ('2,500 to 5,000', '5,000 to 10,000') in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('10,000 and above', '2,500 to 5,000') | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.5520  (conciseness 0.5520 x impact 1.0000)

**Across most measure values (15/18), Mixed accounts for the majority of (varies) among social_composition values. Exception: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); overspend_vs_plan (different pattern); overspend_vs_sanction (different pattern)**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: (whole view), varied along `measure` (measure), 18 members
- commonness: ('Mixed',) in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.5474  (conciseness 0.5474 x impact 1.0000)

**Across most gp_size values (3/4), expenditure_total is decreasing over fiscal_year. Exception: 10,000 and above (no clear pattern)**

- pattern: `TREND`, measure `expenditure_total`, broken down by `fiscal_year`
- slice: (whole view), varied along `gp_size` (subspace), 4 members
- commonness: ('DECREASING',) in 3/4 (75%): 5,000 to 10,000, 2,500 to 5,000, Under 2,500
- exceptions: 10,000 and above [NO_PATTERN]
- figures: total Rs 25.35 crore; top: 2020-2021 = Rs 5.39 crore (21.3%); top: 2021-2022 = Rs 4.55 crore (18.0%); top: 2022-2023 = Rs 4.44 crore (17.5%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.5244  (conciseness 0.5244 x impact 1.0000)

**Across most measure values (13/18), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: planned_cost (different pattern); overspend_vs_plan (different pattern); overspend_vs_sanction (different pattern) and 2 others**

- pattern: `LAST_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: (whole view), varied along `measure` (measure), 18 members
- commonness: ('10,000 and above', 'Under 2,500') in 13/18 (72%): n_plans, n_activities, n_costed, n_costless, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence
- exceptions: planned_cost [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_completed [TYPE_CHANGE] | evidence_uploads [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan`, broken down by `block_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -51.96 crore; top: Lahunipara = Rs -90.62 lakh; top: Baranga = Rs -1.10 crore; top: Kalyansingpur = Rs -1.24 crore
- deterministic framing: evenness reframed (A3); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: ST-majority (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction`, broken down by `district_name`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('EVEN',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total Rs -5.02 crore; top: Rayagada = Rs -17.43 lakh; top: Cuttack = Rs -18.73 lakh; top: Malkangiri = Rs -32.05 lakh
- deterministic framing: evenness reframed (A3); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), n_admin_approvals forms a peak at 2024-2025 over fiscal_year. Exception: Mixed (no clear pattern)**

- pattern: `UNIMODALITY`, measure `n_admin_approvals`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('PEAK', '2024-2025') in 2/3 (67%): SC-majority, ST-majority
- exceptions: Mixed [NO_PATTERN]
- figures: total 2,101 approval records; 2024-2025 = 391 approval records (18.6%); top: 2023-2024 = 424 approval records (20.2%); top: 2024-2025 = 391 approval records (18.6%); top: 2020-2021 = 362 approval records (17.2%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.4647  (conciseness 0.6573 x impact 0.7071)

**Across most measure values (16/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); overspend_vs_plan (different pattern)**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: has_panchayat_bhawan=Yes, varied along `measure` (measure), 18 members
- commonness: ('2,500 to 5,000', '5,000 to 10,000') in 16/18 (89%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_completed, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 and above', 'Under 2,500') | overspend_vs_plan [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.2600  (conciseness 0.6373 x impact 0.4079)

**Across most measure values (15/18), Mixed has the highest (varies) among social_composition values. Exception: overspend_vs_plan (ST-majority has the highest (varies) among social_composition values); overspend_vs_sanction (ST-majority has the highest (varies) among social_composition values); n_completed (SC-majority has the highest (varies) among social_composition values)**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: gp_size=2,500 to 5,000, varied along `measure` (measure), 18 members
- commonness: ('Mixed',) in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: overspend_vs_plan [HIGHLIGHT_CHANGE] ('ST-majority',) | overspend_vs_sanction [HIGHLIGHT_CHANGE] ('ST-majority',) | n_completed [HIGHLIGHT_CHANGE] ('SC-majority',)
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as ATTRIBUTION on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.3925  (conciseness 0.5520 x impact 0.7111)

**Across most measure values (15/18), Mixed accounts for the majority of (varies) among social_composition values. Exception: n_completed (ST-majority accounts for the majority of (varies) among social_composition values); overspend_vs_plan (different pattern); overspend_vs_sanction (different pattern)**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: remoteness=Near, varied along `measure` (measure), 18 members
- commonness: ('Mixed',) in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), sanctioned_total is decreasing over fiscal_year. Exception: SC-majority (different pattern)**

- pattern: `TREND`, measure `sanctioned_total`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('DECREASING',) in 2/3 (67%): Mixed, ST-majority
- exceptions: SC-majority [TYPE_CHANGE]
- figures: total Rs 28.84 crore; top: 2020-2021 = Rs 6.13 crore (21.2%); top: 2021-2022 = Rs 5.51 crore (19.1%); top: 2024-2025 = Rs 4.63 crore (16.0%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.3271  (conciseness 0.4126 x impact 0.7928)

**Across most measure values (13/18), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exceptions: overspend_vs_plan (2,500 to 5,000 and 5,000 to 10,000 are lowest in (varies) among gp_size values); planned_cost (different pattern); overspend_vs_sanction (different pattern) and 2 others**

- pattern: `LAST_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: social_composition=Mixed, varied along `measure` (measure), 18 members
- commonness: ('10,000 and above', 'Under 2,500') in 13/18 (72%): n_plans, n_activities, n_costed, n_costless, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence
- exceptions: overspend_vs_plan [HIGHLIGHT_CHANGE] ('2,500 to 5,000', '5,000 to 10,000') | planned_cost [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_completed [TYPE_CHANGE] | evidence_uploads [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.1379  (conciseness 0.3668 x impact 0.3760)

**Across most measure values (12/18), Bhubaneswar has the highest (varies) among block_name values. Exceptions: n_completed (Kalimela has the highest (varies) among block_name values); n_costless (different pattern); planned_cost (different pattern) and 3 others**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `block_name`
- slice: has_csc=No, varied along `measure` (measure), 18 members
- commonness: ('Bhubaneswar',) in 12/18 (67%): n_plans, n_activities, n_costed, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_with_evidence, evidence_uploads
- exceptions: n_completed [HIGHLIGHT_CHANGE] ('Kalimela',) | n_costless [TYPE_CHANGE] | planned_cost [TYPE_CHANGE] | overspend_vs_plan [TYPE_CHANGE] | overspend_vs_sanction [TYPE_CHANGE] | n_abandoned [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #14  score 0.1672  (conciseness 0.5520 x impact 0.3029)

**Across most measure values (15/18), Mixed has the highest (varies) among social_composition values. Exception: overspend_vs_plan (SC-majority has the highest (varies) among social_composition values); n_completed (ST-majority has the highest (varies) among social_composition values); overspend_vs_sanction (different pattern)**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `social_composition`
- slice: has_panchayat_bhawan=No, varied along `measure` (measure), 18 members
- commonness: ('Mixed',) in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: overspend_vs_plan [HIGHLIGHT_CHANGE] ('SC-majority',) | n_completed [HIGHLIGHT_CHANGE] ('ST-majority',) | overspend_vs_sanction [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #15  score 0.4376  (conciseness 0.5520 x impact 0.7928)

**Across most measure values (15/18), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: overspend_vs_sanction (10,000 and above and Under 2,500 lead in (varies) among gp_size values); overspend_vs_plan (different pattern); n_completed (different pattern)**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: social_composition=Mixed, varied along `measure` (measure), 18 members
- commonness: ('2,500 to 5,000', '5,000 to 10,000') in 15/18 (83%): n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads
- exceptions: overspend_vs_sanction [HIGHLIGHT_CHANGE] ('10,000 and above', 'Under 2,500') | overspend_vs_plan [TYPE_CHANGE] | n_completed [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________

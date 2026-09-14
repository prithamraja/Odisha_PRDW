# Monthly Money Flows by Gram Panchayat -- top 15 findings

*View `view2`, Geo-Month Cash Cube. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)**

- pattern: `TREND`, measure `activity_linked_expenditure`, broken down by `(varies)`
- slice: (whole view), varied along `temporal_grain` (breakdown), 3 members
- commonness: ('INCREASING',) in 3/3 (100%): month, quarter, fiscal_year
- exceptions: (none)
- figures: Varies across members -- see individual patterns
- deterministic framing: recording-completeness framing (A6)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, 10,000 and above and Under 2,500 are lowest in payment_amount among gp_size values**

- pattern: `LAST_TWO`, measure `payment_amount`, broken down by `gp_size`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('10,000 and above', 'Under 2,500') in 6/6 (100%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2024-2025, 2025-2026
- exceptions: (none)
- figures: total Rs 68.58 crore; 10,000 and above = Rs 11.62 crore (16.9%); Under 2,500 = Rs 6.62 crore (9.7%); top: 5,000 to 10,000 = Rs 27.77 crore (40.5%); top: 2,500 to 5,000 = Rs 22.57 crore (32.9%); top: 10,000 and above = Rs 11.62 crore (16.9%)
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, 2,500 to 5,000 and 5,000 to 10,000 lead in activity_linked_expenditure among gp_size values**

- pattern: `TOP_TWO`, measure `activity_linked_expenditure`, broken down by `gp_size`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('2,500 to 5,000', '5,000 to 10,000') in 6/6 (100%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2024-2025, 2025-2026
- exceptions: (none)
- figures: total Rs 24.00 crore; 2,500 to 5,000 = Rs 8.19 crore (34.1%); 5,000 to 10,000 = Rs 9.93 crore (41.4%); top: 5,000 to 10,000 = Rs 9.93 crore (41.4%); top: 2,500 to 5,000 = Rs 8.19 crore (34.1%); top: 10,000 and above = Rs 3.53 crore (14.7%)
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all gp_size values, activity_linked_expenditure is increasing over month**

- pattern: `TREND`, measure `activity_linked_expenditure`, broken down by `month`
- slice: (whole view), varied along `gp_size` (subspace), 4 members
- commonness: ('INCREASING',) in 4/4 (100%): 5,000 to 10,000, 2,500 to 5,000, Under 2,500, 10,000 and above
- exceptions: (none)
- figures: total Rs 24.00 crore; top: 2025-03 = Rs 1.05 crore (4.4%); top: 2026-03 = Rs 99.60 lakh (4.2%); top: 2023-03 = Rs 86.39 lakh (3.6%)
- deterministic framing: recording-completeness framing (A6)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all social_composition values, receipt_count shows seasonal pattern (PERIOD_12) over quarter**

- pattern: `SEASONALITY`, measure `receipt_count`, broken down by `quarter`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('PERIOD_12',) in 3/3 (100%): Mixed, SC-majority, ST-majority
- exceptions: (none)
- figures: total 3,911 vouchers; top: 2024-Q1 = 395 vouchers (10.1%); top: 2021-Q1 = 379 vouchers (9.7%); top: 2022-Q1 = 379 vouchers (9.7%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, Mixed accounts for the majority of activity_linked_expenditure among social_composition values**

- pattern: `ATTRIBUTION`, measure `activity_linked_expenditure`, broken down by `social_composition`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Mixed',) in 6/6 (100%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2024-2025, 2025-2026
- exceptions: (none)
- figures: total Rs 24.00 crore; Mixed = Rs 19.04 crore (79.4%); top: Mixed = Rs 19.04 crore (79.4%); top: SC-majority = Rs 2.54 crore (10.6%); top: ST-majority = Rs 2.41 crore (10.0%)
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.6373  (conciseness 0.6373 x impact 1.0000)

**Across most fiscal_year values (5/6), SC-majority has the lowest payment_amount_mean among social_composition values. Exception: 2025-2026 (different pattern)**

- pattern: `OUTSTANDING_LAST`, measure `payment_amount_mean`, broken down by `social_composition`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('SC-majority',) in 5/6 (83%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2024-2025
- exceptions: 2025-2026 [TYPE_CHANGE]
- figures: SC-majority = Rs 2.31 lakh; top: Mixed = Rs 5.30 lakh; top: ST-majority = Rs 4.38 lakh; top: SC-majority = Rs 2.31 lakh
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.6373  (conciseness 0.6373 x impact 1.0000)

**Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern)**

- pattern: `OUTSTANDING_1`, measure `payment_count`, broken down by `block_name`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Bhubaneswar',) in 5/6 (83%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2025-2026
- exceptions: 2024-2025 [NO_PATTERN]
- figures: total 8,529 vouchers; Bhubaneswar = 2,135 vouchers (25.0%); top: Bhubaneswar = 2,135 vouchers (25.0%); top: Rangeilunda = 945 vouchers (11.1%); top: Bheden = 885 vouchers (10.4%)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.5737  (conciseness 0.5737 x impact 1.0000)

**Across most measure values (7/9), Mixed accounts for the majority of (varies) among social_composition values. Exception: payment_amount_mean (different pattern); receipt_amount_mean (different pattern)**

- pattern: `ATTRIBUTION`, measure `(varies)`, broken down by `social_composition`
- slice: (whole view), varied along `measure` (measure), 9 members
- commonness: ('Mixed',) in 7/9 (78%): payment_amount, receipt_amount, payment_count, receipt_count, activity_linked_expenditure, sanctions_count, sanctioned_amount
- exceptions: payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.5474  (conciseness 0.5474 x impact 1.0000)

**Across most gp_size values (3/4), sanctions_count has a significant shift at 2020-10 in month. Exception: 10,000 and above (sanctions_count has a significant shift at 2021-01 in month)**

- pattern: `CHANGE_POINT`, measure `sanctions_count`, broken down by `month`
- slice: (whole view), varied along `gp_size` (subspace), 4 members
- commonness: ('2020-10',) in 3/4 (75%): 5,000 to 10,000, 2,500 to 5,000, Under 2,500
- exceptions: 10,000 and above [HIGHLIGHT_CHANGE] ('2021-01',)
- figures: total 2,040 sanctions; 2020-10 = 19 sanctions (0.9%); top: 2026-01 = 76 sanctions (3.7%); top: 2023-05 = 66 sanctions (3.2%); top: 2025-12 = 66 sanctions (3.2%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.5474  (conciseness 0.5474 x impact 1.0000)

**Across most gp_size values (3/4), payment_amount_mean shows seasonal pattern (PERIOD_12) over month. Exception: 10,000 and above (different pattern)**

- pattern: `SEASONALITY`, measure `payment_amount_mean`, broken down by `month`
- slice: (whole view), varied along `gp_size` (subspace), 4 members
- commonness: ('PERIOD_12',) in 3/4 (75%): 5,000 to 10,000, 2,500 to 5,000, Under 2,500
- exceptions: 10,000 and above [TYPE_CHANGE]
- figures: top: 2022-03 = Rs 22.47 lakh; top: 2026-03 = Rs 20.12 lakh; top: 2021-03 = Rs 17.20 lakh
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern)**

- pattern: `SEASONALITY`, measure `payment_count`, broken down by `(varies)`
- slice: (whole view), varied along `temporal_grain` (breakdown), 3 members
- commonness: ('PERIOD_12',) in 2/3 (67%): month, quarter
- exceptions: fiscal_year [NO_PATTERN]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most social_composition values (2/3), sanctions_count is increasing over fiscal_year. Exception: ST-majority (no clear pattern)**

- pattern: `TREND`, measure `sanctions_count`, broken down by `fiscal_year`
- slice: (whole view), varied along `social_composition` (subspace), 3 members
- commonness: ('INCREASING',) in 2/3 (67%): Mixed, SC-majority
- exceptions: ST-majority [NO_PATTERN]
- figures: total 2,040 sanctions; top: 2025-2026 = 485 sanctions (23.8%); top: 2024-2025 = 404 sanctions (19.8%); top: 2022-2023 = 343 sanctions (16.8%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #14  score 0.4791  (conciseness 0.5737 x impact 0.8352)

**Across most measure values (7/9), 10,000 and above and Under 2,500 are lowest in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)**

- pattern: `LAST_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: social_composition=Mixed, varied along `measure` (measure), 9 members
- commonness: ('10,000 and above', 'Under 2,500') in 7/9 (78%): payment_amount, receipt_amount, payment_count, receipt_count, activity_linked_expenditure, sanctions_count, sanctioned_amount
- exceptions: payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #15  score 0.4791  (conciseness 0.5737 x impact 0.8352)

**Across most measure values (7/9), 2,500 to 5,000 and 5,000 to 10,000 lead in (varies) among gp_size values. Exception: payment_amount_mean (no clear pattern); receipt_amount_mean (no clear pattern)**

- pattern: `TOP_TWO`, measure `(varies)`, broken down by `gp_size`
- slice: social_composition=Mixed, varied along `measure` (measure), 9 members
- commonness: ('2,500 to 5,000', '5,000 to 10,000') in 7/9 (78%): payment_amount, receipt_amount, payment_count, receipt_count, activity_linked_expenditure, sanctions_count, sanctioned_amount
- exceptions: payment_amount_mean [NO_PATTERN] | receipt_amount_mean [NO_PATTERN]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________

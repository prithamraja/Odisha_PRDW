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


## #2  score 0.6373  (conciseness 0.6373 x impact 1.0000)

**Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern)**

- pattern: `OUTSTANDING_1`, measure `payment_count`, broken down by `block_name`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Bhubaneswar',) in 5/6 (83%): 2020-2021, 2021-2022, 2022-2023, 2023-2024, 2025-2026
- exceptions: 2024-2025 [NO_PATTERN]
- figures: total 8,529 vouchers; Bhubaneswar = 2,135 vouchers (25.0%); top: Bhubaneswar = 2,135 vouchers (25.0%); top: Rangeilunda = 945 vouchers (11.1%); top: Bheden = 885 vouchers (10.4%)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern)**

- pattern: `SEASONALITY`, measure `payment_count`, broken down by `(varies)`
- slice: (whole view), varied along `temporal_grain` (breakdown), 3 members
- commonness: ('PERIOD_12',) in 2/3 (67%): month, quarter
- exceptions: fiscal_year [NO_PATTERN]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)**

- pattern: `TREND`, measure `activity_linked_expenditure`, broken down by `quarter`
- slice: (whole view), varied along `district_name` (subspace), 9 members
- commonness: ('INCREASING',) in 6/9 (67%): Khordha, Ganjam, Kandhamal, Sundargarh, Malkangiri, Rayagada
- exceptions: Bargarh [TYPE_CHANGE] | Koraput [TYPE_CHANGE] | Cuttack [TYPE_CHANGE]
- figures: total Rs 24.00 crore; top: 2026-Q1 = Rs 1.99 crore (8.3%); top: 2025-Q1 = Rs 1.92 crore (8.0%); top: 2023-Q1 = Rs 1.79 crore (7.4%)
- deterministic framing: recording-completeness framing (A6)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.3169  (conciseness 0.3169 x impact 1.0000)

**Across most measure values (6/9), (varies) shows seasonal pattern (PERIOD_12) over month. Exception: activity_linked_expenditure ((varies) shows seasonal pattern (PERIOD_3) over month); sanctions_count (different pattern); sanctioned_amount (different pattern)**

- pattern: `SEASONALITY`, measure `(varies)`, broken down by `month`
- slice: (whole view), varied along `measure` (measure), 9 members
- commonness: ('PERIOD_12',) in 6/9 (67%): payment_amount, receipt_amount, payment_count, receipt_count, payment_amount_mean, receipt_amount_mean
- exceptions: activity_linked_expenditure [HIGHLIGHT_CHANGE] ('PERIOD_3',) | sanctions_count [TYPE_CHANGE] | sanctioned_amount [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.1992  (conciseness 0.1992 x impact 1.0000)

**Across most district_name values (5/9), activity_linked_expenditure shows seasonal pattern (PERIOD_12) over quarter. Exceptions: Sundargarh (activity_linked_expenditure shows seasonal pattern (PERIOD_6) over quarter); Rayagada (activity_linked_expenditure shows seasonal pattern (PERIOD_3) over quarter); Kandhamal (different pattern) and 1 others**

- pattern: `SEASONALITY`, measure `activity_linked_expenditure`, broken down by `quarter`
- slice: (whole view), varied along `district_name` (subspace), 9 members
- commonness: ('PERIOD_12',) in 5/9 (56%): Khordha, Bargarh, Ganjam, Koraput, Cuttack
- exceptions: Sundargarh [HIGHLIGHT_CHANGE] ('PERIOD_6',) | Rayagada [HIGHLIGHT_CHANGE] ('PERIOD_3',) | Kandhamal [TYPE_CHANGE] | Malkangiri [TYPE_CHANGE]
- figures: total Rs 24.00 crore; top: 2026-Q1 = Rs 1.99 crore (8.3%); top: 2025-Q1 = Rs 1.92 crore (8.0%); top: 2023-Q1 = Rs 1.79 crore (7.4%)
- deterministic framing: recording-completeness framing (A6)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most temporal_grain values (2/3), receipt_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (different pattern)**

- pattern: `SEASONALITY`, measure `receipt_count`, broken down by `(varies)`
- slice: (whole view), varied along `temporal_grain` (breakdown), 3 members
- commonness: ('PERIOD_12',) in 2/3 (67%): month, quarter
- exceptions: fiscal_year [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.4877  (conciseness 0.4877 x impact 1.0000)

**Across most temporal_grain values (2/3), sanctions_count is increasing over (varies). Exception: month (different pattern)**

- pattern: `TREND`, measure `sanctions_count`, broken down by `(varies)`
- slice: (whole view), varied along `temporal_grain` (breakdown), 3 members
- commonness: ('INCREASING',) in 2/3 (67%): quarter, fiscal_year
- exceptions: month [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.4484  (conciseness 0.4484 x impact 1.0000)

**Across most block_name values (9/16), activity_linked_expenditure is increasing over quarter. Exceptions: Barpali (different pattern); Bheden (different pattern); Rangeilunda (different pattern) and 4 others**

- pattern: `TREND`, measure `activity_linked_expenditure`, broken down by `quarter`
- slice: (whole view), varied along `block_name` (subspace), 16 members
- commonness: ('INCREASING',) in 9/16 (56%): Bhubaneswar, Khallikote, Khajuripada, Lahunipara, Kalimela, Kalyansingpur, Balisankara, Laxmipur, Sheragada
- exceptions: Barpali [TYPE_CHANGE] | Bheden [TYPE_CHANGE] | Rangeilunda [TYPE_CHANGE] | Boipariguda [TYPE_CHANGE] | Baranga [TYPE_CHANGE] | Tangi Choudwar [TYPE_CHANGE] | Attabira [TYPE_CHANGE]
- figures: total Rs 24.00 crore; top: 2026-Q1 = Rs 1.99 crore (8.3%); top: 2025-Q1 = Rs 1.92 crore (8.0%); top: 2023-Q1 = Rs 1.79 crore (7.4%)
- deterministic framing: recording-completeness framing (A6)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.1204  (conciseness 0.4877 x impact 0.2469)

**Across most measure values (6/9), (varies) has a significant shift at 2020-08 in month. Exception: activity_linked_expenditure ((varies) has a significant shift at 2020-11 in month); sanctions_count ((varies) has a significant shift at 2020-10 in month); sanctioned_amount ((varies) has a significant shift at 2020-10 in month)**

- pattern: `CHANGE_POINT`, measure `(varies)`, broken down by `month`
- slice: district_name=Ganjam, varied along `measure` (measure), 9 members
- commonness: ('2020-08',) in 6/9 (67%): payment_amount, receipt_amount, payment_count, receipt_count, payment_amount_mean, receipt_amount_mean
- exceptions: activity_linked_expenditure [HIGHLIGHT_CHANGE] ('2020-11',) | sanctions_count [HIGHLIGHT_CHANGE] ('2020-10',) | sanctioned_amount [HIGHLIGHT_CHANGE] ('2020-10',)
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.1135  (conciseness 0.4877 x impact 0.2327)

**Across most measure values (6/9), Ganjam has the highest (varies) among district_name values. Exception: payment_count (different pattern); payment_amount_mean (different pattern); receipt_amount_mean (different pattern)**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `district_name`
- slice: fiscal_year=2025-2026, varied along `measure` (measure), 9 members
- commonness: ('Ganjam',) in 6/9 (67%): payment_amount, receipt_amount, receipt_count, activity_linked_expenditure, sanctions_count, sanctioned_amount
- exceptions: payment_count [TYPE_CHANGE] | payment_amount_mean [TYPE_CHANGE] | receipt_amount_mean [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.1110  (conciseness 0.4877 x impact 0.2275)

**Across most temporal_grain values (2/3), sanctioned_amount is increasing over (varies). Exception: fiscal_year (no clear pattern)**

- pattern: `TREND`, measure `sanctioned_amount`, broken down by `(varies)`
- slice: fiscal_year=2020-2021, varied along `temporal_grain` (breakdown), 3 members
- commonness: ('INCREASING',) in 2/3 (67%): month, quarter
- exceptions: fiscal_year [NO_PATTERN]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.1805  (conciseness 0.7211 x impact 0.2503)

**Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)**

- pattern: `TREND`, measure `activity_linked_expenditure`, broken down by `(varies)`
- slice: block_name=Bhubaneswar, varied along `temporal_grain` (breakdown), 3 members
- commonness: ('INCREASING',) in 3/3 (100%): month, quarter, fiscal_year
- exceptions: (none)
- figures: Varies across members -- see individual patterns
- deterministic framing: recording-completeness framing (A6)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #14  score 0.0884  (conciseness 0.4877 x impact 0.1813)

**Across most measure values (6/9), Bheden has the highest (varies) among block_name values. Exception: activity_linked_expenditure (Barpali has the highest (varies) among block_name values); sanctions_count (Barpali has the highest (varies) among block_name values); sanctioned_amount (Barpali has the highest (varies) among block_name values)**

- pattern: `OUTSTANDING_1`, measure `(varies)`, broken down by `block_name`
- slice: district_name=Bargarh, varied along `measure` (measure), 9 members
- commonness: ('Bheden',) in 6/9 (67%): payment_amount, receipt_amount, payment_count, receipt_count, payment_amount_mean, receipt_amount_mean
- exceptions: activity_linked_expenditure [HIGHLIGHT_CHANGE] ('Barpali',) | sanctions_count [HIGHLIGHT_CHANGE] ('Barpali',) | sanctioned_amount [HIGHLIGHT_CHANGE] ('Barpali',)
- figures: Varies across members -- see individual patterns
- deterministic framing: per-GP-month companion (A4); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #15  score 0.0825  (conciseness 0.4877 x impact 0.1692)

**Across most temporal_grain values (2/3), payment_amount_mean is increasing over (varies). Exception: fiscal_year (no clear pattern)**

- pattern: `TREND`, measure `payment_amount_mean`, broken down by `(varies)`
- slice: fiscal_year=2024-2025, varied along `temporal_grain` (breakdown), 3 members
- commonness: ('INCREASING',) in 2/3 (67%): month, quarter
- exceptions: fiscal_year [NO_PATTERN]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________

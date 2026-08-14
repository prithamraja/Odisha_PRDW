# Gram Panchayat Report Card by Year -- top 3 findings

*View `view3`, GP Performance. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.6598  (conciseness 0.6598 x impact 1.0000)

**Across most gp_name values (17/20), n_completed is decreasing over fiscal_year. Exception: Dutimendi (no clear pattern); Andhrua (no clear pattern); Kalimela (no clear pattern)**

- pattern: `TREND`, measure `n_completed`, broken down by `fiscal_year`
- slice: (whole view), varied along `gp_name` (subspace), 20 members
- commonness: ('DECREASING',) in 17/20 (85%): Hirlipali, Bandhpali, Bhatigaon, Bheden, Dadhapatna, Govindapur, Chikilli, Biswamathpur, Sharagada, Barimunda, Itipur, Boipariguda, Laxmipur, Kalyansinghpur, Karuabahal, Haldikudar, Mendarajpur
- exceptions: Dutimendi [NO_PATTERN] | Andhrua [NO_PATTERN] | Kalimela [NO_PATTERN]
- figures: total 17 activities; top: 2021-2022 = 6 activities (35.3%); top: 2022-2023 = 6 activities (35.3%); top: 2020-2021 = 3 activities (17.6%)
- **FY 2023-24 reporting caveat applies** (activity counts compared across the boundary)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.6116  (conciseness 0.6116 x impact 1.0000)

**Across most block_name values (13/16), n_completed is decreasing over fiscal_year. Exception: Khajuripada (no clear pattern); Bhubaneswar (no clear pattern); Kalimela (no clear pattern)**

- pattern: `TREND`, measure `n_completed`, broken down by `fiscal_year`
- slice: (whole view), varied along `block_name` (subspace), 16 members
- commonness: ('DECREASING',) in 13/16 (81%): Attabira, Barpali, Bheden, Baranga, Tangi Choudwar, Khallikote, Rangeilunda, Sheragada, Boipariguda, Laxmipur, Kalyansingpur, Balisankara, Lahunipara
- exceptions: Khajuripada [NO_PATTERN] | Bhubaneswar [NO_PATTERN] | Kalimela [NO_PATTERN]
- figures: total 17 activities; top: 2021-2022 = 6 activities (35.3%); top: 2022-2023 = 6 activities (35.3%); top: 2020-2021 = 3 activities (17.6%)
- **FY 2023-24 reporting caveat applies** (activity counts compared across the boundary)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.0507  (conciseness 0.2105 x impact 0.2410)

**Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Exceptions: n_plans (no clear pattern); sanctioned_total (no clear pattern); n_completed (no clear pattern) and 5 others**

- pattern: `EVENNESS`, measure `(varies)`, broken down by `gp_name`
- slice: district_name=Bargarh, varied along `measure` (measure), 18 members
- commonness: ('EVEN',) in 10/18 (56%): n_activities, n_costless, expenditure_total, overspend_vs_plan, overspend_vs_sanction, n_admin_approvals, n_tech_approvals, n_ongoing, n_with_evidence, evidence_uploads
- exceptions: n_plans [NO_PATTERN] | sanctioned_total [NO_PATTERN] | n_completed [NO_PATTERN] | n_costed [TYPE_CHANGE] | planned_cost [TYPE_CHANGE] | payment_amount [TYPE_CHANGE] | receipt_amount [TYPE_CHANGE] | n_abandoned [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns

**label:** `real` / `already-known` / `spurious`  ->  ________________

# Gram Panchayat Report Card by Year -- top 2 findings

*View `view3`, GP Performance. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.2460  (conciseness 0.2460 x impact 1.0000)

**Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others**

- pattern: `TREND`, measure `sanctioned_total`, broken down by `fiscal_year`
- slice: (whole view), varied along `district_name` (subspace), 9 members
- commonness: ('DECREASING',) in 5/9 (56%): Bargarh, Koraput, Cuttack, Sundargarh, Malkangiri
- exceptions: Kandhamal [HIGHLIGHT_CHANGE] ('INCREASING',) | Khordha [NO_PATTERN] | Ganjam [NO_PATTERN] | Rayagada [NO_PATTERN]
- figures: total Rs 28.84 crore; top: 2020-2021 = Rs 6.13 crore (21.2%); top: 2021-2022 = Rs 5.51 crore (19.1%); top: 2024-2025 = Rs 4.63 crore (16.0%)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.0507  (conciseness 0.2105 x impact 0.2410)

**Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 5 others -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `(varies)`, broken down by `gp_name`
- slice: district_name=Bargarh, varied along `measure` (measure), 18 members
- commonness: ('EVEN',) in 10/18 (56%): n_activities, n_costless, expenditure_total, overspend_vs_plan, overspend_vs_sanction, n_admin_approvals, n_tech_approvals, n_ongoing, n_with_evidence, evidence_uploads
- exceptions: n_plans [NO_PATTERN] | sanctioned_total [NO_PATTERN] | n_completed [NO_PATTERN] | n_costed [TYPE_CHANGE] | planned_cost [TYPE_CHANGE] | payment_amount [TYPE_CHANGE] | receipt_amount [TYPE_CHANGE] | n_abandoned [TYPE_CHANGE]
- figures: Varies across members -- see individual patterns
- deterministic framing: evenness reframed (A3); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________

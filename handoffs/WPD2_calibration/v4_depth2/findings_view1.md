# Activity Lifecycle - Every Planned Work and Its Money -- top 15 findings

*View `view1`, Activity Lifecycle. Ranked by the phase 5 greedy selector (score = conciseness x impact), redundancy-penalised.*


## #1  score 0.8760  (conciseness 0.8760 x impact 1.0000)

**Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_plan`, broken down by `block_name`
- slice: is_costless=Costed, varied along `asset_category_label` (subspace), 28 members
- commonness: ('EVEN',) in 27/28 (96%): Uncategorised, Buildings, Recreational Facilities, Drinking water supply structure, Water Sources & Structures, Roads, Bridges & Culverts, Community Sanitation, Plastic Waste Management, Solid Waste Management, Sanitation & Sewerage Facilities, Liquid Waste Management, Household Sanitation, Movable Sanitation Asset, Faecal Sludge Management, Education Facilities, Office Equipment, Medical & Health Facilities, Land, Irrigation Sources, Computers and peripherals, Electrification, Drinking water supply equipment, Pond & Reservoir, Other Public/Social, Electrical Installation and Equipment, Medical Supplies, Grey water management
- exceptions: Banking Facilities [NO_PATTERN]
- figures: total Rs -51.96 crore; top: Lahunipara = Rs -90.62 lakh; top: Baranga = Rs -1.10 crore; top: Kalyansingpur = Rs -1.24 crore
- deterministic framing: evenness reframed (A3); size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #2  score 0.8760  (conciseness 0.8760 x impact 1.0000)

**Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends**

- pattern: `EVENNESS`, measure `overspend_vs_sanction`, broken down by `district_name`
- slice: (whole view), varied along `asset_category_label` (subspace), 28 members
- commonness: ('EVEN',) in 27/28 (96%): Uncategorised, Buildings, Recreational Facilities, Drinking water supply structure, Water Sources & Structures, Roads, Bridges & Culverts, Community Sanitation, Plastic Waste Management, Solid Waste Management, Sanitation & Sewerage Facilities, Liquid Waste Management, Household Sanitation, Movable Sanitation Asset, Faecal Sludge Management, Education Facilities, Office Equipment, Medical & Health Facilities, Land, Irrigation Sources, Computers and peripherals, Electrification, Drinking water supply equipment, Pond & Reservoir, Other Public/Social, Electrical Installation and Equipment, Medical Supplies, Grey water management
- exceptions: Banking Facilities [NO_PATTERN]
- figures: total Rs -5.02 crore; top: Rayagada = Rs -17.43 lakh; top: Cuttack = Rs -18.73 lakh; top: Malkangiri = Rs -32.05 lakh
- deterministic framing: evenness reframed (A3); size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #3  score 0.8025  (conciseness 0.8402 x impact 0.9551)

**Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern)**

- pattern: `TOP_TWO`, measure `fund_untied_total`, broken down by `output_type_label`
- slice: activity_type_label=Public Works, varied along `gp_name` (subspace), 20 members
- commonness: ('Code 101', 'Code 105') in 19/20 (95%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Boipariguda, Chikilli, Dadhapatna, Dutimendi, Govindapur, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Laxmipur, Mendarajpur, Sharagada
- exceptions: Haldikudar [TYPE_CHANGE]
- figures: total Rs 56.20 crore; Code 101 = Rs 34.88 crore (62.1%); Code 105 = Rs 16.90 crore (30.1%); top: Code 101 = Rs 34.88 crore (62.1%); top: Code 105 = Rs 16.90 crore (30.1%); top: Code 104 = Rs 2.35 crore (4.2%)
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #4  score 0.8025  (conciseness 0.8402 x impact 0.9551)

**Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern)**

- pattern: `OUTSTANDING_1`, measure `n_activities`, broken down by `asset_category_label`
- slice: activity_type_label=Public Works, varied along `gp_name` (subspace), 20 members
- commonness: ('Uncategorised',) in 19/20 (95%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Boipariguda, Chikilli, Dadhapatna, Dutimendi, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Laxmipur, Mendarajpur, Sharagada
- exceptions: Govindapur [TYPE_CHANGE]
- figures: total 9,418 activities; Uncategorised = 5,181 activities (55.0%); top: Uncategorised = 5,181 activities (55.0%); top: Buildings = 688 activities (7.3%); top: Household Sanitation = 524 activities (5.6%)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #5  score 0.7384  (conciseness 0.7384 x impact 1.0000)

**Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)**

- pattern: `OUTSTANDING_LAST`, measure `overspend_vs_plan`, broken down by `status_label`
- slice: is_costless=Costed, varied along `gp_name` (subspace), 20 members
- commonness: ('Activity Approved',) in 18/20 (90%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Chikilli, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Mendarajpur, Sharagada
- exceptions: Boipariguda [NO_PATTERN] | Laxmipur [NO_PATTERN]
- figures: total Rs -51.96 crore; Activity Approved = Rs -41.61 crore; top: WORK COMPLETED = Rs 18,797; top: Buildings = Rs -10.88 lakh; top: UNDER APPROVAL = Rs -37.60 lakh
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #6  score 0.7384  (conciseness 0.7384 x impact 1.0000)

**Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)**

- pattern: `ATTRIBUTION`, measure `gen_amount`, broken down by `status_label`
- slice: is_costless=Costed, varied along `gp_name` (subspace), 20 members
- commonness: ('WORK ONGOING',) in 18/20 (90%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Chikilli, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Mendarajpur, Sharagada
- exceptions: Boipariguda [NO_PATTERN] | Laxmipur [NO_PATTERN]
- figures: total Rs 30.43 crore; WORK ONGOING = Rs 28.59 crore (93.9%); top: WORK ONGOING = Rs 28.59 crore (93.9%); top: WORK ABANDONED = Rs 1.15 crore (3.8%); top: Activity Approved = Rs 32.74 lakh (1.1%)
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #7  score 0.7384  (conciseness 0.7384 x impact 1.0000)

**Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)**

- pattern: `OUTSTANDING_1`, measure `beneficiaries_expected`, broken down by `status_label`
- slice: (whole view), varied along `gp_name` (subspace), 20 members
- commonness: ('Activity Approved',) in 18/20 (90%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Chikilli, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Mendarajpur, Sharagada
- exceptions: Boipariguda [NO_PATTERN] | Laxmipur [NO_PATTERN]
- figures: total 2,06,929 people; Activity Approved = 2,03,534 people (98.4%); top: Activity Approved = 2,03,534 people (98.4%); top: WORK ONGOING = 2,759 people (1.3%); top: WORK ABANDONED = 606 people (0.3%)
- deterministic framing: size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #8  score 0.7384  (conciseness 0.7384 x impact 1.0000)

**Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values); Kalimela (Theme 4 - Water Sufficient Village has the highest fund_untied_total among theme values)**

- pattern: `OUTSTANDING_1`, measure `fund_untied_total`, broken down by `theme`
- slice: is_costless=Costed, varied along `gp_name` (subspace), 20 members
- commonness: ('Theme 6 - Self-sufficient Infrastructure in Village',) in 18/20 (90%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Chikilli, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalyansinghpur, Karuabahal, Laxmipur, Mendarajpur, Sharagada
- exceptions: Boipariguda [HIGHLIGHT_CHANGE] ('Unmapped theme',) | Kalimela [HIGHLIGHT_CHANGE] ('Theme 4 - Water Sufficient Village',)
- figures: total Rs 59.64 crore; Theme 6 - Self-sufficient Infrastructure in Village = Rs 30.07 crore (50.4%); top: Theme 6 - Self-sufficient Infrastructure in Village = Rs 30.07 crore (50.4%); top: Theme 4 - Water Sufficient Village = Rs 11.63 crore (19.5%); top: Unmapped theme = Rs 5.70 crore (9.6%)
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #9  score 0.7306  (conciseness 0.8402 x impact 0.8696)

**Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern)**

- pattern: `OUTSTANDING_LAST`, measure `overspend_vs_sanction`, broken down by `output_type_label`
- slice: work_type_label=New/Fresh, varied along `gp_name` (subspace), 20 members
- commonness: ('Code 101',) in 19/20 (95%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Boipariguda, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Laxmipur, Mendarajpur, Sharagada
- exceptions: Chikilli [NO_PATTERN]
- figures: total Rs -2.54 crore; Code 101 = Rs -2.49 crore; top: Code 109 = Rs 0; top: Code 102 = Rs -21,568; top: Code 110 = Rs -1.78 lakh
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #10  score 0.7306  (conciseness 0.8402 x impact 0.8696)

**Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern)**

- pattern: `ATTRIBUTION`, measure `evidence_uploads`, broken down by `output_type_label`
- slice: work_type_label=New/Fresh, varied along `gp_name` (subspace), 20 members
- commonness: ('Code 101',) in 19/20 (95%): Andhrua, Bandhpali, Barimunda, Bhatigaon, Bheden, Biswamathpur, Boipariguda, Dadhapatna, Dutimendi, Govindapur, Haldikudar, Hirlipali, Itipur, Kalimela, Kalyansinghpur, Karuabahal, Laxmipur, Mendarajpur, Sharagada
- exceptions: Chikilli [NO_PATTERN]
- figures: total 6,893 photo uploads; Code 101 = 6,893 photo uploads (100.0%); top: Code 101 = 6,893 photo uploads (100.0%); top: Code 102 = 0 photo uploads (0.0%); top: Code 103 = 0 photo uploads (0.0%)
- deterministic framing: size shares attached (2b)
- **twin merged in** (A2): also found as OUTSTANDING_1 on the same members
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #11  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all activity_for_label values, Code 101 and Code 105 are lowest in overspend_vs_plan among output_type_label values**

- pattern: `LAST_TWO`, measure `overspend_vs_plan`, broken down by `output_type_label`
- slice: (whole view), varied along `activity_for_label` (subspace), 4 members
- commonness: ('Code 101', 'Code 105') in 4/4 (100%): ALL/ General public, General, sc, st
- exceptions: (none)
- figures: total Rs -51.96 crore; Code 101 = Rs -30.97 crore; Code 105 = Rs -15.11 crore; top: Code 109 = Rs 0; top: Code 110 = Rs -5.11 lakh; top: Code 102 = Rs -61.67 lakh
- deterministic framing: size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #12  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all activity_for_label values, Drinking water and Sanitation lead in fund_tied_total among focus_area_name values**

- pattern: `TOP_TWO`, measure `fund_tied_total`, broken down by `focus_area_name`
- slice: is_costless=Costed, varied along `activity_for_label` (subspace), 4 members
- commonness: ('Drinking water', 'Sanitation') in 4/4 (100%): ALL/ General public, General, sc, st
- exceptions: (none)
- figures: total Rs 17.66 crore; Drinking water = Rs 8.42 crore (47.7%); Sanitation = Rs 8.82 crore (49.9%); top: Sanitation = Rs 8.82 crore (49.9%); top: Drinking water = Rs 8.42 crore (47.7%); top: Roads = Rs 31.01 lakh (1.8%)
- deterministic framing: size shares attached (2b)
- **NEW IN THIS RUN** -- not present in the comparison run's top-15

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #13  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, Chikilli has the lowest fund_sanctioned_total among gp_name values**

- pattern: `OUTSTANDING_LAST`, measure `fund_sanctioned_total`, broken down by `gp_name`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Chikilli',) in 6/6 (100%): 2023-2024, 2024-2025, 2025-2026, 2021-2022, 2020-2021, 2022-2023
- exceptions: (none)
- figures: total Rs 28.84 crore; Chikilli = Rs 0 (0.0%); top: Sharagada = Rs 2.74 crore (9.5%); top: Kalimela = Rs 2.08 crore (7.2%); top: Laxmipur = Rs 1.88 crore (6.5%)
- deterministic framing: size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #14  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, Other has the lowest gen_amount among tied_untied values**

- pattern: `OUTSTANDING_LAST`, measure `gen_amount`, broken down by `tied_untied`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Other',) in 6/6 (100%): 2023-2024, 2024-2025, 2025-2026, 2021-2022, 2020-2021, 2022-2023
- exceptions: (none)
- figures: total Rs 28.48 crore; Other = Rs 1.02 crore (3.6%); top: Untied = Rs 16.75 crore (58.8%); top: Tied = Rs 10.71 crore (37.6%); top: Other = Rs 1.02 crore (3.6%)
- deterministic framing: size shares attached (2b)

**label:** `real` / `already-known` / `spurious`  ->  ________________


## #15  score 0.7211  (conciseness 0.7211 x impact 1.0000)

**Across all fiscal_year values, Activity Approved and WORK ONGOING lead in n_activities among status_label values**

- pattern: `TOP_TWO`, measure `n_activities`, broken down by `status_label`
- slice: (whole view), varied along `fiscal_year` (subspace), 6 members
- commonness: ('Activity Approved', 'WORK ONGOING') in 6/6 (100%): 2023-2024, 2024-2025, 2025-2026, 2021-2022, 2020-2021, 2022-2023
- exceptions: (none)
- figures: total 12,704 activities; Activity Approved = 10,108 activities (79.6%); WORK ONGOING = 2,110 activities (16.6%); top: Activity Approved = 10,108 activities (79.6%); top: WORK ONGOING = 2,110 activities (16.6%); top: WORK ABANDONED = 420 activities (3.3%)
- **FY 2023-24 reporting caveat applies** (activity counts compared across the boundary)

**label:** `real` / `already-known` / `spurious`  ->  ________________

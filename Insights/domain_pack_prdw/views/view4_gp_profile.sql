-- =============================================================================
-- view4_gp_profile — one row per Gram Panchayat (20 rows on this drop)
--
-- DISCOVER_VIEW_MAPPING Amendment B §12.4, built in WP-D11. The GP itself as
-- the unit of analysis: who lives here, what the panchayat has, and what it has
-- planned, sanctioned, spent and evidenced over the whole window.
--
-- GRAIN: GP. No temporal dimension at all — this view is the lifetime total,
-- and every time-varying question belongs to view2 (cash months) or view3
-- (GP x fiscal year). Post-view validation pins the grain at 20 rows with
-- gp_lgd_code unique.
--
-- MATERIALISED FROM THE MASTER, LEFT JOINS ONLY — view3's discipline, for
-- view3's reason. The grid is `gram_panchayat` and nothing else; the profile
-- and all three lifetime aggregates hang off it by LEFT JOIN. Chikilli is the
-- proof again: 640 planned activities, ZERO administrative approvals, and it
-- keeps its row with n_admin_approvals = 0 and its profile fully populated. A
-- GP with a profile and no activity would survive the same way.
--
-- SUM-EQUALITY WITH view3, BY CONSTRUCTION. Every lifetime performance column
-- below is view3's expression over the same stg_* layer with the fiscal-year
-- key removed, so SUM(view4.col) = SUM(view3.col) exactly, for all eighteen.
-- WP-D11 T5 checks all eighteen; a mismatch means one of the two views has
-- changed its attribution rule and the other has not.
--
-- THE FISCAL-YEAR DOMAIN IS APPLIED, NOT DROPPED. view3's aggregates reach the
-- reader through a grid built on stg_fiscal_year_domain, so a row whose fiscal
-- year is outside that domain — or null — never reaches a view3 cell. Summing
-- the raw tables here instead would quietly add those rows back and break the
-- equality above; the phantom '2026-2027' rows of §8.1 are the case the pack
-- has already been bitten by. Each CTE therefore filters to the same derived
-- domain, which is a re-statement of view3's grid join, not a new rule.
--
-- NO RATE, NO PER-CAPITA COLUMN (§3, §12.4). Because the grain is GP, a SUM
-- over any scope yields a correct numerator and a correct denominator at the
-- same time — spend per household or approvals per activity are honest at
-- block and district roll-up here and nowhere else in the pack. The engine
-- still cannot form that quotient: its measures are SUM or AVG of ONE column
-- (the WP-D2c intensity measures are AVG-of-a-column, not a ratio). So v1 of
-- this view ships numerators and denominators only. Per-capita MINING needs an
-- engine ratio-measure extension, which Amendment B explicitly defers to a
-- separate engine WP. The prose and decomposition layers can still state a
-- per-household figure from the two columns.
--
-- MEASURES ARE ZERO-FILLED; DIMENSIONS NEVER ARE (§4.2). One consequence is
-- worth stating rather than discovering: laptops / printers / scanners are the
-- three profile counts that carry the literal 'NA' token in the source (2 GPs
-- each). derived_columns.sql turns that token into a NULL, and the zero-fill
-- here then reads it as 0 — so "reported none" and "did not report" are not
-- distinguishable in this view for those three columns. Logged in the WP-D11
-- report; not repaired, because the zero-fill rule is the grid's, not this
-- column's, and a partial exemption would be the more surprising behaviour.
--
-- SAMPLE-SCALE EXPECTATION, STATED IN ADVANCE (§12.4). 20 rows across 9
-- districts. The engine will produce few rankable findings here and thin bands
-- on social_composition are expected (B2). The view is built, validated and
-- mined now so that the machinery and the glossary exist; it becomes a live
-- signal statewide (~6,800 rows). Do not tune toward a sample gate on it.
--
-- WHAT IS DELIBERATELY ABSENT. `work_proposed_cost` is a view3 measure and is
-- NOT in §12.4's lifetime list, so it is not projected — the column list here
-- is §12.4's, exactly. `general_no_of_destitue_homes_old_age_homes` and the
-- three yes/no amenity attributes (renewable energy, rainwater harvesting,
-- panchayat library) are counts and attributes the spec's role table does not
-- assign and §12.4 does not list; they are left out and raised as proposed
-- amendments in the WP-D11 report rather than invented into the view.
-- =============================================================================
WITH fy AS (
    SELECT fiscal_year FROM stg_fiscal_year_domain
),

-- view3's `activity` CTE, verbatim, with the fiscal-year key removed from the
-- GROUP BY and moved into the domain filter. Every expression — including
-- overspend_vs_plan's coalesce and overspend_vs_sanction's deliberate absence
-- of one — is the same expression view1 and view3 project.
activity AS (
    SELECT
        a.gp_lgd_code,
        COUNT(*)                                                    AS n_activities,
        SUM(CASE WHEN a.is_costless = 'Costed'   THEN 1 ELSE 0 END) AS n_costed,
        SUM(CASE WHEN a.is_costless = 'Costless' THEN 1 ELSE 0 END) AS n_costless,
        SUM(a.total_cost)                                           AS planned_cost,
        SUM(ap.fund_sanctioned_total)                               AS sanctioned_total,
        SUM(COALESCE(e.total_expenditure, 0))                       AS expenditure_total,
        SUM(COALESCE(e.total_expenditure, 0) - COALESCE(a.total_cost, 0))
                                                                    AS overspend_vs_plan,
        SUM(COALESCE(e.total_expenditure, 0) - ap.fund_sanctioned_total)
                                                                    AS overspend_vs_sanction,
        SUM(CASE WHEN ap.activity_code IS NOT NULL THEN 1 ELSE 0 END) AS n_admin_approvals,
        SUM(COALESCE(ap.has_technical_approval, 0))                 AS n_tech_approvals,
        SUM(a.is_completed)                                         AS n_completed,
        SUM(a.is_ongoing)                                           AS n_ongoing,
        SUM(a.is_abandoned)                                         AS n_abandoned,
        SUM(CASE WHEN pp.activity_code IS NOT NULL THEN 1 ELSE 0 END) AS n_with_evidence,
        SUM(COALESCE(pp.evidence_uploads, 0))                       AS evidence_uploads
    FROM stg_planned_activity a
    LEFT JOIN stg_exp_rollup      e  ON e.activity_code  = a.activity_code
    LEFT JOIN stg_approval        ap ON ap.activity_code = a.activity_code
    LEFT JOIN stg_progress_rollup pp ON pp.activity_code = a.activity_code
    WHERE a.fiscal_year IN (SELECT fiscal_year FROM fy)
    GROUP BY 1
),

plans AS (
    SELECT gp_lgd_code, COUNT(*) AS n_plans
    FROM stg_plan
    WHERE fiscal_year IN (SELECT fiscal_year FROM fy)
    GROUP BY 1
),

cash AS (
    SELECT gp_lgd_code,
           SUM(CASE WHEN direction = 'payment' THEN amount ELSE 0 END) AS payment_amount,
           SUM(CASE WHEN direction = 'receipt' THEN amount ELSE 0 END) AS receipt_amount
    FROM stg_voucher
    WHERE fiscal_year IN (SELECT fiscal_year FROM fy)
    GROUP BY 1
)

SELECT
    -- ── geography: all six name+code columns, as every view carries them ───
    CAST(g.gp_lgd_code   AS VARCHAR) AS gp_lgd_code,
    CAST(g.gp_name       AS VARCHAR) AS gp_name,
    CAST(g.block_code    AS VARCHAR) AS block_code,
    CAST(g.block_name    AS VARCHAR) AS block_name,
    CAST(g.district_code AS VARCHAR) AS district_code,
    CAST(g.district_name AS VARCHAR) AS district_name,

    -- ── GP profile dimensions (§12.3) ──────────────────────────────────────
    -- Same seven bands, same COALESCE, as views 1-3. Cut points and sample
    -- splits are documented once, at the CASE ladders in derived_columns.sql.
    COALESCE(p.social_composition,   'Not reported') AS social_composition,
    COALESCE(p.gp_size,              'Not reported') AS gp_size,
    COALESCE(p.remoteness,           'Not reported') AS remoteness,
    COALESCE(p.digital_readiness,    'Not reported') AS digital_readiness,
    COALESCE(p.has_panchayat_bhawan, 'Not reported') AS has_panchayat_bhawan,
    COALESCE(p.has_csc,              'Not reported') AS has_csc,
    COALESCE(p.plc_available,        'Not reported') AS plc_available,

    -- ── measures: profile, population ──────────────────────────────────────
    -- Sample totals: 115,246 people in 26,132 households across the 20 GPs.
    CAST(COALESCE(p.population_total,    0) AS DOUBLE) AS population_total,
    CAST(COALESCE(p.population_male,     0) AS DOUBLE) AS population_male,
    CAST(COALESCE(p.population_female,   0) AS DOUBLE) AS population_female,
    -- 0 in 9 of 20 GPs (§12.6.13) — a reporting gap, carried as reported
    CAST(COALESCE(p.population_children, 0) AS DOUBLE) AS population_children,
    CAST(COALESCE(p.population_sc,       0) AS DOUBLE) AS population_sc,
    -- 0 in 3 GPs, not the 5 §12.6.13 names: Sharagada reports 16 and
    -- Barimunda 1 (measured, WP-D11; amendment proposed in the report)
    CAST(COALESCE(p.population_st,       0) AS DOUBLE) AS population_st,
    CAST(COALESCE(p.population_obc,      0) AS DOUBLE) AS population_obc,
    CAST(COALESCE(p.population_general,  0) AS DOUBLE) AS population_general,

    -- ── measures: profile, households and organisation ─────────────────────
    -- Karuabahal reports 12 households against 3,208 people (§12.6.11). The
    -- column is carried as reported and is never a denominator in this pack.
    CAST(COALESCE(p.households,          0) AS DOUBLE) AS households,
    CAST(COALESCE(p.job_card_holders,    0) AS DOUBLE) AS job_card_holders,
    CAST(COALESCE(p.shgs,                0) AS DOUBLE) AS shgs,
    CAST(COALESCE(p.wards,               0) AS DOUBLE) AS wards,
    CAST(COALESCE(p.revenue_villages,    0) AS DOUBLE) AS revenue_villages,
    CAST(COALESCE(p.villages_mapped_lgd, 0) AS DOUBLE) AS villages_mapped_lgd,

    -- ── measures: profile, education and childcare ─────────────────────────
    CAST(COALESCE(p.anganwadi_centres,        0) AS DOUBLE) AS anganwadi_centres,
    CAST(COALESCE(p.schools_pre_primary,      0) AS DOUBLE) AS schools_pre_primary,
    CAST(COALESCE(p.schools_primary,          0) AS DOUBLE) AS schools_primary,
    CAST(COALESCE(p.schools_secondary,        0) AS DOUBLE) AS schools_secondary,
    CAST(COALESCE(p.schools_higher_secondary, 0) AS DOUBLE) AS schools_higher_secondary,

    -- ── measures: profile, health ──────────────────────────────────────────
    CAST(COALESCE(p.health_sub_centres,     0) AS DOUBLE) AS health_sub_centres,
    CAST(COALESCE(p.primary_health_centres, 0) AS DOUBLE) AS primary_health_centres,
    CAST(COALESCE(p.wellbeing_centres,      0) AS DOUBLE) AS wellbeing_centres,
    CAST(COALESCE(p.dispensaries,           0) AS DOUBLE) AS dispensaries,
    CAST(COALESCE(p.ayurvedic_clinics,      0) AS DOUBLE) AS ayurvedic_clinics,

    -- ── measures: profile, water and sanitation ────────────────────────────
    -- household_toilets exceeds households in 5 GPs and households_tap_water
    -- in 2 (Chikilli, Haldikudar) — §12.6.12. Counts only; §3 forbids
    -- materialising the coverage ratio, and these two columns are exactly why.
    CAST(COALESCE(p.drinking_water_sources,       0) AS DOUBLE) AS drinking_water_sources,
    CAST(COALESCE(p.households_tap_water,         0) AS DOUBLE) AS households_tap_water,
    CAST(COALESCE(p.household_toilets,            0) AS DOUBLE) AS household_toilets,
    CAST(COALESCE(p.community_sanitary_complexes, 0) AS DOUBLE) AS community_sanitary_complexes,
    CAST(COALESCE(p.solid_waste_centres,          0) AS DOUBLE) AS solid_waste_centres,

    -- ── measures: profile, services and civic infrastructure ───────────────
    CAST(COALESCE(p.common_service_centres,  0) AS DOUBLE) AS common_service_centres,
    CAST(COALESCE(p.banks,                   0) AS DOUBLE) AS banks,
    CAST(COALESCE(p.atms,                    0) AS DOUBLE) AS atms,
    CAST(COALESCE(p.rural_libraries,         0) AS DOUBLE) AS rural_libraries,
    CAST(COALESCE(p.children_parks,          0) AS DOUBLE) AS children_parks,
    CAST(COALESCE(p.disaster_rescue_centres, 0) AS DOUBLE) AS disaster_rescue_centres,
    CAST(COALESCE(p.bus_stands_with_water,   0) AS DOUBLE) AS bus_stands_with_water,
    CAST(COALESCE(p.seed_centres,            0) AS DOUBLE) AS seed_centres,

    -- ── measures: profile, revenue and equipment ───────────────────────────
    -- osr_collected is own-source revenue to date, rupees. It is NOT one of
    -- §3's four money bases and must never be totalled alongside them.
    CAST(COALESCE(p.osr_collected, 0) AS DOUBLE) AS osr_collected,
    -- the three 'NA' columns: 0 here means "none reported OR not reported"
    -- (see the header). 2 GPs are affected on each.
    CAST(COALESCE(p.laptops,       0) AS DOUBLE) AS laptops,
    CAST(COALESCE(p.printers,      0) AS DOUBLE) AS printers,
    CAST(COALESCE(p.scanners,      0) AS DOUBLE) AS scanners,
    CAST(COALESCE(p.sports_courts, 0) AS DOUBLE) AS sports_courts,

    -- ── measures: lifetime performance (each equals its view3 column total) ─
    -- planning
    CAST(COALESCE(plans.n_plans,         0) AS DOUBLE) AS n_plans,
    CAST(COALESCE(activity.n_activities, 0) AS DOUBLE) AS n_activities,
    CAST(COALESCE(activity.n_costed,     0) AS DOUBLE) AS n_costed,
    CAST(COALESCE(activity.n_costless,   0) AS DOUBLE) AS n_costless,
    CAST(COALESCE(activity.planned_cost, 0) AS DOUBLE) AS planned_cost,

    -- sanction. n_admin_approvals is 0 across Chikilli's whole row, exactly as
    -- it is across all six of Chikilli's view3 rows.
    CAST(COALESCE(activity.sanctioned_total,  0) AS DOUBLE) AS sanctioned_total,
    CAST(COALESCE(activity.n_admin_approvals, 0) AS DOUBLE) AS n_admin_approvals,
    -- 2,095 sample-wide, not the 2,134 technical-approval records: v_approval
    -- hangs the technical approval off the administrative one (WP-D1 §4).
    CAST(COALESCE(activity.n_tech_approvals,  0) AS DOUBLE) AS n_tech_approvals,

    -- spend. A zero in overspend_vs_sanction means "nothing sanctioned", not
    -- "spent exactly what was sanctioned" — read it against n_admin_approvals.
    CAST(COALESCE(activity.expenditure_total,     0) AS DOUBLE) AS expenditure_total,
    CAST(COALESCE(activity.overspend_vs_plan,     0) AS DOUBLE) AS overspend_vs_plan,
    CAST(COALESCE(activity.overspend_vs_sanction, 0) AS DOUBLE) AS overspend_vs_sanction,

    -- cashbook (GP-level flows, not activity-attributed)
    CAST(COALESCE(cash.payment_amount, 0) AS DOUBLE) AS payment_amount,
    CAST(COALESCE(cash.receipt_amount, 0) AS DOUBLE) AS receipt_amount,

    -- progress and evidence. Only 17 activities are complete sample-wide
    -- (§8.4), so n_completed is a known-degenerate calibration measure.
    CAST(COALESCE(activity.n_completed,      0) AS DOUBLE) AS n_completed,
    CAST(COALESCE(activity.n_ongoing,        0) AS DOUBLE) AS n_ongoing,
    CAST(COALESCE(activity.n_abandoned,      0) AS DOUBLE) AS n_abandoned,
    CAST(COALESCE(activity.n_with_evidence,  0) AS DOUBLE) AS n_with_evidence,
    CAST(COALESCE(activity.evidence_uploads, 0) AS DOUBLE) AS evidence_uploads

FROM stg_gram_panchayat g
LEFT JOIN stg_gp_profile p        ON p.gp_lgd_code        = g.gp_lgd_code
LEFT JOIN activity                ON activity.gp_lgd_code = g.gp_lgd_code
LEFT JOIN plans                   ON plans.gp_lgd_code    = g.gp_lgd_code
LEFT JOIN cash                    ON cash.gp_lgd_code     = g.gp_lgd_code

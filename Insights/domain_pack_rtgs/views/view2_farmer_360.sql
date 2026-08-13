-- =============================================================================
-- view2_farmer_360 — one row per PM-KISAN roster farmer (1,100).
--
-- survey_land_records has no Aadhaar column, so its 1,100 land parcels cannot
-- be attached to a farmer and the file sits out.
--
-- ITERATION 2 — the spine is the roster, not "every Aadhaar seen anywhere".
-- 1,140 distinct Aadhaars appear across the seven scheme files; 40 of them have
-- no PM-KISAN record at all, and in iteration 1 those 40 carried the literal
-- 'NOT_IN_PMKISAN' on every roster-sourced dimension. That literal was more
-- extreme than any real value on every measure — lowest gender, lowest land
-- class, lowest scheme count — so it took the extremum slot in every ordering
-- and a data gap was reported as a demographic finding.
--
-- Those 40 farmers are not deleted from the analysis, they are RESTATED: the
-- build reports them as a named coverage statistic (how many farmers draw
-- scheme benefits with no PM-KISAN record, and under which schemes), which
-- phase5b carries as a fixed preamble fact in the view description rather than
-- as a mined finding. See validation.yaml POST-VIEW note and the build report.
--
-- total_benefit_amount is the per-farmer sum of view1's benefit_amount over the
-- roster: both views read the same stg_benefit_long spine, so Ask, view1 and
-- view2 agree on any roster-scoped total.
--
-- ITERATION 2 — a rate-shaped AVG measure. The engine describes the
-- distribution of ONE measure, so a rate has to arrive as a column.
-- `ekyc_pending_rate` is a row-level 1.0 / 0.0 at farmer grain, so the engine's
-- avg over any slice is the share of that slice's farmers whose eKYC is still
-- pending.
--
-- ITERATION 5 — `agri_share_of_input_pair` is RETIRED, not replaced. Iteration
-- 4 added it (crop agriculture's share of the two-scheme input pair, per
-- farmer, defined only for farmers in both) and it measured correctly: a 1.92x
-- district contrast, Krishna and West Godavari the two lowest. It could not
-- RANK. Only 386 of 1,100 farmers draw on both schemes, so the column is NULL
-- for 714 of them, and once any subspace filter is applied most breakdown
-- values fall below the engine's minimum of three non-null values: the measure
-- supported 3 candidates out of view2's 1,452 and produced no ranked finding at
-- all. A measure that cannot be ranked cannot be reported, so it is gone rather
-- than carried.
--
-- The question it was trying to answer — which schemes a district's benefit
-- rupees actually flow through — moves to `view9_scheme_mix`, at district x
-- scheme grain where the share is dense. Nothing else about view2 changes.
--
-- PROPORTIONAL LAND — `land_acres_mean` carries the same row values as
-- `land_acres` and is declared `avg` in VIEW2_CONFIG: the duplicate-column
-- pattern already used for `benefit_amount_mean`, `subsidy_mean` and
-- `amount_paid_mean`. The engine describes ONE measure at a time, so per-farmer
-- landholding has to arrive as its own column; the alternative was to let the
-- summed column stand alone, which is how "BC and OC hold the largest land
-- base, ST the smallest" reached a report as an equity finding when it is a
-- headcount fact. Measured on this drop, acres per farmer are 3.12 (BC), 3.04
-- (SC), 2.99 (OC) and 2.98 (ST) — near-flat, so the honest outcome of mining
-- this column is EVENNESS, not a gap. That is the point of adding it.
-- =============================================================================
WITH per_farmer AS (
    SELECT
        aadhaar,
        max(CASE WHEN scheme = 'PM-KISAN'                  THEN 1 ELSE 0 END) AS in_pm_kisan,
        max(CASE WHEN scheme = 'Agriculture Input Subsidy' THEN 1 ELSE 0 END) AS in_agriculture,
        max(CASE WHEN scheme = 'Horticulture APMIP'        THEN 1 ELSE 0 END) AS in_horticulture,
        max(CASE WHEN scheme = 'Fisheries'                 THEN 1 ELSE 0 END) AS in_fisheries,
        max(CASE WHEN scheme = 'Sericulture'               THEN 1 ELSE 0 END) AS in_sericulture,
        max(CASE WHEN scheme = 'MARKFED Procurement'       THEN 1 ELSE 0 END) AS in_markfed,
        max(CASE WHEN scheme = 'RySS Rythu Sadhikara'      THEN 1 ELSE 0 END) AS in_ryss,
        sum(benefit_amount)                                                   AS total_benefit_amount,
        avg(land_acres)                                                       AS scheme_land_acres
    FROM stg_benefit_long
    GROUP BY aadhaar
)
SELECT
    CAST(p.district           AS VARCHAR) AS district,
    CAST(p.gender             AS VARCHAR) AS gender,
    CAST(p.category           AS VARCHAR) AS category,
    CAST(p.ekyc_status        AS VARCHAR) AS ekyc_status,
    CAST(p.beneficiary_status AS VARCHAR) AS beneficiary_status,
    CAST(p.land_size_class    AS VARCHAR) AS land_size_class,

    CAST(f.in_pm_kisan + f.in_agriculture + f.in_horticulture + f.in_fisheries
         + f.in_sericulture + f.in_markfed + f.in_ryss AS DOUBLE)      AS scheme_count,

    CAST(f.in_pm_kisan     AS DOUBLE) AS in_pm_kisan,
    CAST(f.in_agriculture  AS DOUBLE) AS in_agriculture,
    CAST(f.in_horticulture AS DOUBLE) AS in_horticulture,
    CAST(f.in_fisheries    AS DOUBLE) AS in_fisheries,
    CAST(f.in_sericulture  AS DOUBLE) AS in_sericulture,
    CAST(f.in_markfed      AS DOUBLE) AS in_markfed,
    CAST(f.in_ryss         AS DOUBLE) AS in_ryss,

    -- rate-shaped measure: row-level 0..1, averaged by the engine
    CAST(CASE WHEN p.ekyc_status = 'Pending' THEN 1.0 ELSE 0.0 END AS DOUBLE)
                                                                        AS ekyc_pending_rate,

    CAST(f.total_benefit_amount AS DOUBLE)                              AS total_benefit_amount,
    CAST(COALESCE(p.land_acres, f.scheme_land_acres) AS DOUBLE)         AS land_acres,
    -- same column as land_acres, averaged rather than totalled: acres per
    -- farmer. See the duplicate-column note in the header.
    CAST(COALESCE(p.land_acres, f.scheme_land_acres) AS DOUBLE)         AS land_acres_mean,
    CAST(1 AS DOUBLE)                                                   AS farmer_count
FROM per_farmer f
JOIN stg_pm_kisan p ON f.aadhaar = p.aadhaar
-- No ORDER BY: the runner materialises every view as
-- `COPY (SELECT * FROM <view>) TO ...`, and that re-scan discards any ordering
-- the view definition carries, so one here would be a no-op. This view's
-- Parquet is therefore not byte-stable across runs -- the row set and every
-- aggregate are identical, only the physical order and the last bits of the
-- parallel SUM differ. See AP_METAINSIGHTS_DRYRUN_REPORT.md 7.4.
--
-- 2026-07-31: it is NOT the only such view, as this note used to claim. Two
-- back-to-back builds off identical inputs were measured, and view5 and view9
-- move too (view9's benefit_share by 1.1e-16, its row order freely). Only
-- views 1, 3, 4, 6, 7 and 8 are byte-stable. A byte diff on 2, 5 or 9 is not
-- evidence that anything changed; compare values.

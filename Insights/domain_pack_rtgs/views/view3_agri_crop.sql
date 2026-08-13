-- =============================================================================
-- view3_agri_crop — the Agriculture input-subsidy register at source grain,
-- one row per registration (1,114 less the 153 that fall in the incomplete
-- final year = 961).
--
-- ITERATION 2 — complete years only. Nothing anywhere in the drop is dated
-- after 2026-07-31, so the last crop year is a part year: every crop's count
-- falls in it for that reason alone, which makes every series non-monotone and
-- prevents any "rising over the years" majority from forming at all. The
-- temporal axis is therefore cut to the complete years: 2023, 2024, 2025. The
-- excluded count and the cells it thins are reported by validation.yaml and the
-- build report. 2026 is a property of this drop's calendar, not of any crop,
-- district or category.
--
-- seedvarietyname is in scope but NOT a dimension here: its 20 values are
-- cropnameeng crossed with {BPT-5204, MTU-1010}, both paddy varieties, applied
-- to every crop including Cotton and Turmeric. It carries no information the
-- crop name does not already carry (see demo_crosswalk.csv note).
--
-- No quantity column exists in the flat Agriculture file; none is invented.
-- subsidyamount / subsidy_mean are the same column twice (SUM and AVG).
-- =============================================================================
SELECT
    CAST(cropnameeng      AS VARCHAR) AS cropnameeng,
    CAST(season           AS VARCHAR) AS season,
    CAST(district_name    AS VARCHAR) AS district,
    CAST(cropstatus       AS VARCHAR) AS cropstatus,
    CAST(social_status    AS VARCHAR) AS social_status,
    CAST(cultivator_type  AS VARCHAR) AS cultivator_type,
    CAST(cropyear         AS VARCHAR) AS cropyear,
    CAST(subsidyamount    AS DOUBLE)  AS subsidyamount,
    CAST(subsidyamount    AS DOUBLE)  AS subsidy_mean,
    CAST(nonsubsidyamount AS DOUBLE)  AS nonsubsidyamount,
    CAST(1                AS DOUBLE)  AS record_count
FROM stg_agriculture
WHERE cropyear <> 2026

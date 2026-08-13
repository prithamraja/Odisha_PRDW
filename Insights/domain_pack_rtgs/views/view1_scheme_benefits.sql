-- =============================================================================
-- view1_scheme_benefits — one row per benefit row across the seven AP scheme
-- files (survey_land_records excluded: no benefit column).
--
-- Grain: benefit row. 1,100 PM-KISAN + 1,114 Agriculture + 567 Horticulture
--        + 627 Fisheries + 666 Sericulture + 1,086 MARKFED + 684 RySS = 5,844,
--        less the 26 rows whose category is the UNKNOWN placeholder = 5,818.
--
-- Aadhaar is the join spine inside stg_benefit_long and is dropped here: the
-- view carries no personal identifier.
--
-- benefit_amount / benefit_amount_mean are the same column twice — the engine
-- takes exactly one aggregation per measure, so the SUM and the AVG story each
-- need their own column.
--
-- ITERATION 2 — union artefacts removed. `season` and `crop_year` are gone from
-- the projection: only the seasonal schemes carry a real season and only the
-- Agriculture register carries a real crop year, so in a view that unions all
-- seven programmes both columns were 62% / 98% placeholder ('ALL', 'NA') and the
-- placeholder took the extremum slot in every pattern built over them. Season
-- and year analysis lives in view3 and view4, where the values are real.
--
-- The `category = 'UNKNOWN'` rows go the same way: UNKNOWN is not a social
-- category, it is "this row could not be matched to the PM-KISAN roster, so no
-- category is on file". Its mean benefit sat below every real category, so it
-- owned the bottom slot of every category ordering. The filter is written
-- against the placeholder literal, not against any scheme or category of
-- interest. The excluded count is asserted in validation.yaml.
-- =============================================================================
SELECT
    CAST(scheme            AS VARCHAR) AS scheme,
    CAST(district          AS VARCHAR) AS district,
    CAST(gender            AS VARCHAR) AS gender,
    CAST(category          AS VARCHAR) AS category,
    CAST(status            AS VARCHAR) AS status,
    CAST(benefit_amount    AS DOUBLE)  AS benefit_amount,
    CAST(benefit_amount    AS DOUBLE)  AS benefit_amount_mean,
    CAST(land_acres        AS DOUBLE)  AS land_acres,
    CAST(1                 AS DOUBLE)  AS benefit_count
FROM stg_benefit_long
WHERE category <> 'UNKNOWN'

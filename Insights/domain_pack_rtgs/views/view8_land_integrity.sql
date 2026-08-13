-- =============================================================================
-- view8_land_integrity — declared land against recorded land, per farmer.
--
-- Why this view exists. PM-KISAN pays on the land a farmer DECLARES. The
-- revenue department records the land they are on the RECORD for. Where the
-- two disagree, entitlement is being computed off a number nobody verified —
-- which is a targeting question, not a data-quality footnote, because the
-- larger figure is the one that pays. No other view can see the disagreement:
-- every one of them reads the declared figure.
--
-- Grain: one row per PM-KISAN roster farmer, 1,100 of them.
--
-- THE JOIN, AND THE CAVEAT THAT TRAVELS WITH IT. `pm_kisan.khata_no` matches
-- `survey_land_records.khata_no` 1:1 for all 1,100 roster farmers on this drop
-- — every farmer resolves to exactly one parcel, and the village on both sides
-- agrees in 100% of cases. That is a property of THIS SYNTHETIC DROP and must
-- not be carried into production. A real khata is village-scoped and m:n: one
-- khata covers joint holdings and several survey numbers, and the same khata
-- number recurs across villages. The production key is the composite
-- (khata_no, village), the cardinality is many-to-many, and a farmer's recorded
-- extent is a SUM over parcels rather than a single value. Anyone reusing this
-- join must re-establish the cardinality first.
--
-- Direction matters. `discrepancy_ratio` is declared over recorded, so above
-- 1.0 means the farmer claims more than the record carries, and below 1.0 means
-- the record carries more than they claim. Only the first is an entitlement
-- risk; the flag is one-sided for that reason and its threshold (1.10) sits
-- clear of the rounding either side of the hectare-to-acre conversion.
-- =============================================================================
SELECT
    CAST(p.district        AS VARCHAR) AS district,
    CAST(p.category        AS VARCHAR) AS category,
    CAST(p.gender          AS VARCHAR) AS gender,
    CAST(p.land_size_class AS VARCHAR) AS land_size_class,

    CAST(p.land_acres        AS DOUBLE) AS declared_acres,
    CAST(s.recorded_acres    AS DOUBLE) AS recorded_acres,

    -- rate-shaped: row-level ratio, averaged by the engine over any slice
    CAST(COALESCE(p.land_acres / NULLIF(s.recorded_acres, 0), 1.0) AS DOUBLE)
                                        AS discrepancy_ratio,
    CAST(CASE WHEN s.recorded_acres > 0
               AND p.land_acres > 1.10 * s.recorded_acres
              THEN 1.0 ELSE 0.0 END AS DOUBLE)
                                        AS over_declared_flag,

    CAST(1 AS DOUBLE)                   AS farmer_count
FROM stg_pm_kisan p
JOIN stg_survey_land_records s
  ON CAST(p.khata_no AS VARCHAR) = s.khata

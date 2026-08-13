-- =============================================================================
-- domain_pack_rtgs / derived_columns.sql
-- =============================================================================
-- Staging layer for the AP RTGS Decision Aid "Discover" views.
--
--   1. district_code_map    — dcode/DIST_CODE -> district name, RECOVERED from
--                             the data (no hard-coded map)
--   2. stg_<table>          — one per registered source, adding the normalised
--                             Aadhaar spine, district_name, land_acres,
--                             land_size_class and the MARKFED date parts
--   3. stg_benefit_long     — the seven scheme files unioned to benefit-row
--                             grain, carrying Aadhaar. view1 projects it minus
--                             Aadhaar; view2 aggregates it per farmer, so the
--                             two views cannot disagree by construction.
--
-- Aadhaar never leaves this file: it appears in stg_* and stg_benefit_long as
-- the join spine and is dropped by every view.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. District code -> name, recovered by joining a coded table to pm_kisan on
--    Aadhaar and taking the modal district per code. Comes out as the census
--    ordering of the thirteen pre-2022 AP districts, with 7 = Guntur
--    (validation.yaml CHECK 5 asserts the resulting name domain).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW district_code_map AS
WITH pairs AS (
    SELECT a.dcode      AS district_code,
           p.district   AS district_name,
           count(*)     AS n
    FROM agriculture a
    JOIN pm_kisan    p ON trim(a.aadharno) = trim(p.aadhaar_no)
    WHERE a.dcode IS NOT NULL
    GROUP BY 1, 2
),
ranked AS (
    SELECT district_code, district_name, n,
           row_number() OVER (PARTITION BY district_code
                              ORDER BY n DESC, district_name) AS rk
    FROM pairs
)
SELECT district_code, district_name
FROM ranked
WHERE rk = 1;


-- -----------------------------------------------------------------------------
-- 2. Staging views — one per source table
-- -----------------------------------------------------------------------------

-- PM-KISAN is the farmer roster: the only file with hectares, and the source of
-- the land-size classes used across the whole pack.
CREATE OR REPLACE VIEW stg_pm_kisan AS
SELECT *,
       trim(aadhaar_no)      AS aadhaar,
       area_hectares * 2.471 AS land_acres,
       CASE WHEN area_hectares IS NULL THEN NULL
            WHEN area_hectares <  1  THEN 'Marginal (<1 ha)'
            WHEN area_hectares <  2  THEN 'Small (1-2 ha)'
            WHEN area_hectares <  4  THEN 'Semi-medium (2-4 ha)'
            WHEN area_hectares < 10  THEN 'Medium (4-10 ha)'
            ELSE                          'Large (>10 ha)'
       END                   AS land_size_class
FROM pm_kisan;

-- Agriculture carries a district CODE and no gender or land column at all;
-- both are recovered from the roster on Aadhaar.
CREATE OR REPLACE VIEW stg_agriculture AS
SELECT a.*,
       trim(a.aadharno)                 AS aadhaar,
       m.district_name                  AS district_name,
       COALESCE(p.gender, 'UNKNOWN')    AS gender_from_roster,
       p.land_acres                     AS land_acres
FROM agriculture a
LEFT JOIN district_code_map m ON a.dcode = m.district_code
LEFT JOIN stg_pm_kisan      p ON trim(a.aadharno) = p.aadhaar;

CREATE OR REPLACE VIEW stg_horticulture_apmip AS
SELECT *,
       trim(EXTN_AADHARNO) AS aadhaar,
       DISTRICT            AS district_name,
       EXTENT              AS land_acres
FROM horticulture_apmip;

CREATE OR REPLACE VIEW stg_fisheries AS
SELECT *,
       trim(aadhar_no) AS aadhaar,
       district        AS district_name,
       EXTENT          AS land_acres
FROM fisheries;

-- Sericulture carries a district CODE and no caste column; caste comes from the
-- roster on Aadhaar (D1 pin table: "via Aadhaar").
CREATE OR REPLACE VIEW stg_sericulture AS
SELECT s.*,
       trim(s.aadhaar_no)             AS aadhaar,
       m.district_name                AS district_name,
       s.Area                         AS land_acres,
       COALESCE(p.category, 'UNKNOWN') AS category_from_roster
FROM sericulture s
LEFT JOIN district_code_map m ON s.DIST_CODE = m.district_code
LEFT JOIN stg_pm_kisan      p ON trim(s.aadhaar_no) = p.aadhaar;

CREATE OR REPLACE VIEW stg_markfed AS
SELECT *,
       trim(AADHAAR_NO)                    AS aadhaar,
       DIST_NAME                           AS district_name,
       AREA_IN_ACRES                       AS land_acres,
       strftime(PROCUREMENT_DATE, '%Y')    AS proc_year,
       strftime(PROCUREMENT_DATE, '%Y-%m') AS proc_month
FROM markfed;

CREATE OR REPLACE VIEW stg_ryss AS
SELECT *,
       trim(Aadhar_no) AS aadhaar,
       district        AS district_name,
       ACREAGE         AS land_acres
FROM ryss;

-- ITERATION 3. Survey_Land_Records carries no Aadhaar, so it hangs off the
-- roster by khata number. On this drop that key is 1:1 with pm_kisan.khata_no
-- for all 1,100 roster farmers, villages agreeing 100%, which is what lets a
-- recorded extent be attributed to a farmer at all. Real khata is
-- village-scoped and m:n; view8's description carries that caveat, and nothing
-- outside view8 uses this view.
CREATE OR REPLACE VIEW stg_survey_land_records AS
SELECT *,
       CAST(khata_no AS VARCHAR) AS khata,
       extent                    AS recorded_acres
FROM survey_land_records;


-- -----------------------------------------------------------------------------
-- 3. The scheme-benefit spine: one row per benefit row in the seven scheme
--    files (survey_land_records has no benefit column and is excluded).
--    Dimension sources follow the D1 §2.1 pin table.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW stg_benefit_long AS

SELECT aadhaar,
       'PM-KISAN'                AS scheme,
       district                  AS district,
       gender                    AS gender,
       category                  AS category,
       'ALL'                     AS season,
       ekyc_status               AS status,
       last_amount_credited      AS benefit_amount,
       land_acres                AS land_acres,
       'NA'                      AS crop_year
FROM stg_pm_kisan

UNION ALL
SELECT aadhaar,
       'Agriculture Input Subsidy',
       district_name,
       gender_from_roster,        -- no gender column exists in agriculture
       social_status,
       season,
       cropstatus,
       subsidyamount,
       land_acres,                -- no land column exists either; roster-derived
       CAST(cropyear AS VARCHAR)
FROM stg_agriculture

UNION ALL
SELECT aadhaar, 'Horticulture APMIP', district_name, Gender, Category,
       'ALL', Status, SubsidyAmt, land_acres, 'NA'
FROM stg_horticulture_apmip

UNION ALL
SELECT aadhaar, 'Fisheries', district_name, gender, caste,
       'ALL', payment_status, amount, land_acres, 'NA'
FROM stg_fisheries

UNION ALL
SELECT aadhaar, 'Sericulture', district_name, Sex, category_from_roster,
       'ALL', status, Net_Incentive, land_acres, 'NA'
FROM stg_sericulture

UNION ALL
SELECT aadhaar, 'MARKFED Procurement', district_name, GENDER, CASTE,
       SEASON_ID, PAYMENT_STATUS, AMOUNT_PAID, land_acres, 'NA'
FROM stg_markfed

UNION ALL
SELECT aadhaar, 'RySS Rythu Sadhikara', district_name, Gender, Category,
       'ALL', PaymentStatus, Amount, land_acres, 'NA'
FROM stg_ryss;

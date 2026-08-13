-- =============================================================================
-- view9_scheme_mix — district x scheme, the SHAPE of a district's benefit mix.
--
-- ITERATION 5. Third and final form of the P2 measure. The two earlier forms
-- both failed for measured reasons, and both failures were about GRAIN, not
-- about the pattern:
--
--   iteration 3  fisheries_benefit_share  — fisheries rupees over the farmer's
--                whole benefit basket. The basket is dominated by MARKFED bulk
--                that has nothing to do with the input mix, and the numerator
--                sits inside its own denominator, so the share saturates.
--                Measured district contrast 1.12x against an injected 2.02x.
--
--   iteration 4  agri_share_of_input_pair — crop agriculture's share of the
--                two-scheme input pair, per farmer, defined only for farmers in
--                BOTH schemes. Correct as a measure (contrast 1.92x) and far too
--                sparse as one: NULL for 714 of 1,100 farmers, which left three
--                candidates in view2's 1,452 and no ranked finding at all.
--
-- The fix is the move view5 and view4's rate columns already make: PRECOMPUTE
-- THE SHARE AT THE GRAIN WHERE IT IS DENSE. A district's scheme mix is a
-- property of the district, not of a farmer, so the cell is district x scheme
-- and the share is computed once per cell in SQL. Thirteen districts x seven
-- schemes = 91 rows, every one of them populated by construction.
--
-- Grain: one row per district x scheme. Every row is already an aggregate, so a
-- single row-level value carries the share and the engine's AVG over any slice
-- is the mean share of that slice's cells. A slice of one cell — which is what
-- "fisheries in each district" is — returns the cell's own share unchanged.
--
-- Schemes: all seven, PM-KISAN included. This view is not view5: it is not
-- measuring coverage against a population base, it is decomposing a rupee
-- total, and PM-KISAN rupees are part of that total. The scheme list is derived
-- from the spine, not enumerated.
--
-- ATTRIBUTION. Rupees are attributed to the farmer's PM-KISAN ROSTER district,
-- the same rule view5 uses, so numerator and denominator can never disagree
-- about which district a rupee landed in. The alternative — each scheme file's
-- own district column, which is view1's convention — moves the fisheries share
-- by up to 0.0085 and would leave the 62 off-roster benefit rows attributed to
-- a district while no roster farmer stands behind them. The join drops those 62
-- rows (of 5,844), leaving 5,782 behind the cube; view1 excludes 26 of the same
-- rows by the category placeholder instead. Neither filter names a district, a
-- scheme or a category of interest.
--
-- EMPTY CELLS ARE ZERO, NOT MISSING. The grid is the full cross product, so
-- YSR Kadapa x Horticulture APMIP is present at 0.0000: YSR Kadapa has no
-- horticulture sanctions in the drop, and "no rupees flowed through this
-- scheme here" is a fact about the district, not an absent measurement. Keeping
-- it also makes every district's seven shares sum to exactly 1.0000, which is
-- what lets the column be read as a decomposition.
-- =============================================================================
WITH roster_benefit AS (
    SELECT p.district        AS district,
           b.scheme          AS scheme,
           b.benefit_amount  AS benefit_amount
    FROM stg_benefit_long b
    JOIN stg_pm_kisan     p ON b.aadhaar = p.aadhaar
),

district_domain AS (SELECT DISTINCT district FROM roster_benefit),
scheme_domain   AS (SELECT DISTINCT scheme   FROM roster_benefit),

-- the full 13 x 7 grid; a scheme that reached nobody in a district still gets
-- its row, at zero
grid AS (
    SELECT d.district, s.scheme
    FROM district_domain d
    CROSS JOIN scheme_domain s
),

cell AS (
    SELECT district, scheme, sum(benefit_amount) AS cell_benefit
    FROM roster_benefit
    GROUP BY 1, 2
),

district_total AS (
    SELECT district, sum(benefit_amount) AS district_benefit
    FROM roster_benefit
    GROUP BY 1
)

SELECT
    CAST(g.district AS VARCHAR) AS district,
    CAST(g.scheme   AS VARCHAR) AS scheme,

    -- of every benefit rupee reaching this district, the share flowing through
    -- this scheme. Averaged by the engine; a district's seven values sum to 1.
    CAST(COALESCE(c.cell_benefit, 0.0) / t.district_benefit AS DOUBLE)
                                                            AS benefit_share,

    CAST(COALESCE(c.cell_benefit, 0.0) AS DOUBLE)           AS total_benefit

FROM grid g
JOIN district_total t ON g.district = t.district
LEFT JOIN cell c      ON g.district = c.district
                     AND g.scheme   = c.scheme

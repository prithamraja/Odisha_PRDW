-- =============================================================================
-- view5_equity_cube — district x category x scheme, PROPORTIONAL not absolute.
--
-- Why this view exists. "Is the Scheduled Tribe population reached in
-- proportion to its size?" is unanswerable from a SUM measure. ST is about 6%
-- of the roster, so ST's absolute total is the smallest of the four categories
-- in every scheme, in every district, by construction — an extremum pattern
-- over a SUM measure will keep reporting that headcount artefact as a finding.
-- This view carries the proportional forms as first-class AVG measures so the
-- engine can describe them directly.
--
-- Grain: one row per district x social category x scheme. Every row is already
-- an aggregate, so each rate is a single row-level value and the engine's AVG
-- over any slice is the mean rate of that slice's cells.
--
-- Schemes: the six AP state programmes. PM-KISAN is excluded because it IS the
-- denominator — its own coverage is 100% by construction and would be a
-- tautology. The list is derived from the data (every scheme in the benefit
-- spine that is not the roster scheme), not enumerated.
--
-- Denominator — a stated assumption, not a measurement. `population` is the
-- count of PM-KISAN ROSTER farmers in the district x category cell. The roster
-- is near-universal for landholding farmers, which is what makes it usable as
-- a population base, but it is not the farming population: tenant and landless
-- farmers are outside it, and they are exactly the groups an equity question
-- most wants counted. Every rate below therefore reads as "per roster farmer",
-- and with real ministry data this becomes an SME-visible caveat rather than a
-- footnote. The glossary states it in those words.
--
-- Empty cells are dropped, not fabricated: a district x category pair with no
-- roster farmers produces no rows, because the cell grid is built FROM the
-- roster rather than from a cross product of the value domains.
--
-- Thin cells are kept, not filtered. ST is roughly five farmers per district.
-- `population` stays in the view as a measure so a reader can always see the
-- base size behind a rate; the glossary tells the report to qualify small cells.
-- Filtering them would be the wrong fix — the signal is robust because the
-- underlying means are deterministic — but a rate over five people still has to
-- be READ as a rate over five people.
--
-- Benefit rupees are attributed to the farmer's ROSTER district and category,
-- the same attribution as the denominator, so numerator and denominator can
-- never disagree about who is in a cell. Rupees come from the same
-- stg_benefit_long spine as view1 and view2.
--
-- LAND, PROPORTIONALLY. `land_share_index` is `representation_index` with acres
-- in place of rupees: the cell's share of its district's roster acres over the
-- cell's share of its district's roster farmers, 1.0 = proportional. Benefits
-- got this treatment when the cube was built; land never did, and the absolute
-- form ("BC and OC hold the largest land base") went on being reported as
-- equity when it is composition. Measured on this drop the index sits at
-- 0.99 +/- 0.17 across the 52 cells and 0.97-1.02 statewide by category, i.e.
-- proportional — which is the truthful answer, not a disappointing one.
--
-- It is CONSTANT PER CELL and repeated across the six scheme rows, exactly like
-- `population`, because land is a property of the farmer and not of the
-- programme. It therefore takes the same non-additive treatment: declared avg
-- in VIEW5_CONFIG, with the glossary warning that it is never summed. Read it
-- against `population` as every other rate in this cube is read: Scheduled
-- Tribe is roughly five roster farmers per district, so a single district's
-- index rests on a handful of holdings and the wide cells (0.62 to 1.73) are
-- thin cells, not findings.
-- =============================================================================
WITH roster AS (
    SELECT aadhaar, district, category, land_acres
    FROM stg_pm_kisan
),

-- benefit rows of roster farmers under the non-roster schemes
roster_benefit AS (
    SELECT r.district, r.category, b.scheme, b.aadhaar, b.benefit_amount
    FROM stg_benefit_long b
    JOIN roster r ON b.aadhaar = r.aadhaar
    WHERE b.scheme <> 'PM-KISAN'
),

cell_population AS (
    SELECT district, category,
           count(*)        AS population,
           sum(land_acres) AS cell_acres
    FROM roster
    GROUP BY 1, 2
),

district_population AS (
    SELECT district,
           count(*)        AS district_population,
           sum(land_acres) AS district_acres
    FROM roster
    GROUP BY 1
),

scheme_domain AS (
    SELECT DISTINCT scheme FROM roster_benefit
),

-- the cell grid: every populated district x category pair, crossed with the
-- scheme domain. Cells with no roster population never enter.
grid AS (
    SELECT p.district, p.category, s.scheme, p.population, p.cell_acres
    FROM cell_population p
    CROSS JOIN scheme_domain s
),

cell AS (
    SELECT district, category, scheme,
           count(DISTINCT aadhaar) AS enrolled,
           sum(benefit_amount)     AS cell_benefit
    FROM roster_benefit
    GROUP BY 1, 2, 3
),

district_scheme AS (
    SELECT district, scheme, sum(benefit_amount) AS district_scheme_benefit
    FROM roster_benefit
    GROUP BY 1, 2
)

SELECT
    CAST(g.district AS VARCHAR) AS district,
    CAST(g.category AS VARCHAR) AS category,
    CAST(g.scheme   AS VARCHAR) AS scheme,

    CAST(g.population              AS DOUBLE) AS population,
    CAST(COALESCE(c.enrolled, 0)   AS DOUBLE) AS enrolled,

    CAST(COALESCE(c.enrolled, 0) * 1.0 / g.population AS DOUBLE)      AS coverage_rate,
    CAST(COALESCE(c.cell_benefit, 0.0) / g.population AS DOUBLE)      AS rupees_per_capita,

    -- benefit share of the district-scheme, over population share of the
    -- district. 1.0 = the cell draws exactly its population's worth.
    CAST(COALESCE(
             (COALESCE(c.cell_benefit, 0.0) / NULLIF(ds.district_scheme_benefit, 0))
           / NULLIF(g.population * 1.0 / dp.district_population, 0),
         0.0) AS DOUBLE)                                              AS representation_index,

    -- the same construction over ACRES instead of rupees, and therefore
    -- constant across the six scheme rows of a cell. 1.0 = the cell holds
    -- exactly its population's worth of the district's land.
    CAST(COALESCE(
             (COALESCE(g.cell_acres, 0.0) / NULLIF(dp.district_acres, 0))
           / NULLIF(g.population * 1.0 / dp.district_population, 0),
         0.0) AS DOUBLE)                                              AS land_share_index

FROM grid g
JOIN district_population dp ON g.district = dp.district
LEFT JOIN cell c            ON g.district = c.district
                           AND g.category = c.category
                           AND g.scheme   = c.scheme
LEFT JOIN district_scheme ds ON g.district = ds.district
                            AND g.scheme   = ds.scheme

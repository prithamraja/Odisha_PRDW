-- =============================================================================
-- view7_input_to_market — what the state put in against what it bought back.
--
-- Why this view exists. Agriculture pays a farmer to plant; MARKFED pays the
-- same farmer for what they harvest. Neither view alone can say whether the
-- first turned into the second. This one puts both on one row per farmer and
-- carries the ratio as a first-class measure, so "which districts realise the
-- least market value per rupee of input subsidy" is a question the engine can
-- answer rather than one a reader has to assemble.
--
-- Grain: one row per farmer who appears in BOTH programmes. That intersection
-- is the only population for whom the ratio is defined at all — a farmer with
-- subsidy and no sale has an infinite ratio, one with a sale and no subsidy has
-- no denominator — so the view is scoped to it and the count is reported by the
-- build rather than padded with zeros.
--
-- WHAT THIS VIEW CANNOT SEE. Crop is a FARMER attribute in this data: the same
-- farmer names the same crop in the input-subsidy register and at the
-- procurement centre, by construction of the data build. So `crop` here mines
-- INTENSITY — how much subsidy and how much realisation each crop's growers
-- carry — and can say nothing whatever about farmers switching crop between
-- the two programmes. With real data that would be a genuine question; on this
-- drop it is answered by construction and must not be reported.
--
-- The spine is the PM-KISAN roster, as in view2: district, social category,
-- gender and landholding are the roster's, so a farmer is counted in exactly
-- one district and no dimension can carry a "not on the roster" placeholder.
-- =============================================================================
WITH input AS (
    SELECT aadhaar,
           sum(subsidyamount)     AS input_subsidy,
           any_value(cropnameeng) AS crop
    FROM stg_agriculture
    GROUP BY aadhaar
),

market AS (
    SELECT aadhaar,
           sum(PROCURED_QTY) AS procured_qty,
           sum(AMOUNT_PAID)  AS procurement_value
    FROM stg_markfed
    GROUP BY aadhaar
)

SELECT
    CAST(p.district        AS VARCHAR) AS district,
    CAST(p.category        AS VARCHAR) AS category,
    CAST(p.gender          AS VARCHAR) AS gender,
    CAST(i.crop            AS VARCHAR) AS crop,
    CAST(p.land_size_class AS VARCHAR) AS land_size_class,

    CAST(i.input_subsidy     AS DOUBLE) AS input_subsidy,
    CAST(m.procured_qty      AS DOUBLE) AS procured_qty,
    CAST(m.procurement_value AS DOUBLE) AS procurement_value,

    -- rate-shaped: rupees back per rupee in, at farmer level. The engine's AVG
    -- over a slice is that slice's mean realisation, which is comparable
    -- between a large district and a small one; the two rupee totals above are
    -- not.
    CAST(COALESCE(m.procurement_value / NULLIF(i.input_subsidy, 0), 0.0) AS DOUBLE)
                                        AS realization_ratio,

    CAST(p.land_acres AS DOUBLE)        AS land_acres,
    CAST(1 AS DOUBLE)                   AS farmer_count
FROM input i
JOIN market      m ON i.aadhaar = m.aadhaar
JOIN stg_pm_kisan p ON i.aadhaar = p.aadhaar

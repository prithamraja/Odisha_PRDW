-- =============================================================================
-- view6_horti_pipeline — the micro-irrigation sanction-to-release funnel.
--
-- Why this view exists. Every other view measures money that has ALREADY
-- moved. Horticulture APMIP is the one programme in the drop that records both
-- halves of the transaction — what was sanctioned and what was actually
-- released — so it is the only place the question "has the money left the
-- building?" can be asked at all. That is a live officer question (the Ask
-- catalog's G22 family asks exactly it), and it has a findable answer here.
--
-- Grain: one row per micro-irrigation sanction, 567 of them. No aggregation
-- happens in this view; the engine does it.
--
-- Twelve districts, not thirteen. YSR Kadapa has no horticulture rows in this
-- drop at all. That is a deliberate gap in the data build, not a zero: the
-- district is ABSENT from this view rather than present with nothing in it,
-- and a reader must not report it as a district that received nothing. The
-- glossary says so in those words.
--
-- Crop is carried as a dimension. It is a FARMER attribute in this data, not a
-- row attribute — the same farmer names the same crop in every file they
-- appear in — so it profiles cleanly here (ten values, every row filled).
--
-- The three money columns are not independent: released + balance = sanctioned
-- on every row, by construction in the data build. `release_rate` is that
-- relation expressed at row level so the engine can average it over any slice;
-- `stalled_flag` is its hard end — a sanction with 90% or more of its money
-- still sitting is stalled whatever its status field says.
-- =============================================================================
SELECT
    CAST(district_name AS VARCHAR) AS district,
    CAST(Gender        AS VARCHAR) AS gender,
    CAST(Category      AS VARCHAR) AS category,
    CAST(Status        AS VARCHAR) AS status,
    CAST(CROPNAME      AS VARCHAR) AS crop,

    CAST(SubsidyAmt AS DOUBLE)                          AS subsidy_amt,
    -- the same rupee column again, for the engine to AVERAGE rather than total:
    -- the typical size of one sanction, independent of how many there were
    CAST(SubsidyAmt AS DOUBLE)                          AS subsidy_amt_mean,

    CAST(BALANCE_AMOUNT_TO_RELEASE AS DOUBLE)           AS balance_to_release,
    CAST(Subsidy_Rlsd AS DOUBLE)                        AS released_amount,

    -- rate-shaped measures: row-level values, averaged by the engine
    CAST(COALESCE(Subsidy_Rlsd / NULLIF(SubsidyAmt, 0), 0.0) AS DOUBLE)
                                                        AS release_rate,
    CAST(CASE WHEN SubsidyAmt > 0
               AND BALANCE_AMOUNT_TO_RELEASE >= 0.90 * SubsidyAmt
              THEN 1.0 ELSE 0.0 END AS DOUBLE)          AS stalled_flag,

    CAST(1 AS DOUBLE)                                   AS beneficiary_count
FROM stg_horticulture_apmip

-- =============================================================================
-- view4_markfed_procurement — MARKFED procurement transactions at source
-- grain, one row per transaction (1,086).
--
-- proc_month is derived from PROCUREMENT_DATE, which the Demo Field Inventory
-- files under Produce/Qty but which holds ISO date strings (100% parse,
-- 2023-08-01 to 2026-07-31) — re-roled to temporal in the crosswalk.
--
-- ITERATION 2 — proc_year is gone. It held four values of which the first and
-- last were part years, so any trend across it was reading a truncation.
-- proc_month carries the same information at 28 points, which is enough for the
-- temporal evaluators to see through the truncated ends; the two dimensions
-- were redundant and only the coarse one was misleading. No rows are dropped —
-- unlike view3's crop year, the month axis does not need the part years removed.
--
-- unpaid_count / unpaid_share are the same 1/0 flag twice: SUM over a slice
-- reads as "payments still stuck" in transactions, AVG over the same slice
-- reads as the share of that slice's transactions still unpaid. The engine
-- takes exactly one aggregation per measure, so a rate needs its own column.
-- amount_paid / amount_paid_mean are the same column twice (SUM and AVG).
-- =============================================================================
SELECT
    CAST(CROP_NAME      AS VARCHAR) AS crop_name,
    CAST(DIST_NAME      AS VARCHAR) AS district,
    CAST(SEASON_ID      AS VARCHAR) AS season,
    CAST(GENDER         AS VARCHAR) AS gender,
    CAST(CASTE          AS VARCHAR) AS caste,
    CAST(PAYMENT_STATUS AS VARCHAR) AS payment_status,
    CAST(proc_month     AS VARCHAR) AS proc_month,
    CAST(AMOUNT_PAID    AS DOUBLE)  AS amount_paid,
    CAST(AMOUNT_PAID    AS DOUBLE)  AS amount_paid_mean,
    CAST(PROCURED_QTY   AS DOUBLE)  AS procured_qty,
    CAST(CASE WHEN PAYMENT_STATUS <> 'Approved' THEN 1 ELSE 0 END AS DOUBLE) AS unpaid_count,
    CAST(CASE WHEN PAYMENT_STATUS <> 'Approved' THEN 1 ELSE 0 END AS DOUBLE) AS unpaid_share,
    CAST(1              AS DOUBLE)  AS txn_count
FROM stg_markfed

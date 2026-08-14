-- =============================================================================
-- view2_geo_month_cube — GP x calendar month, cash basis (1,440 rows on this drop)
--
-- DISCOVER_VIEW_MAPPING §4.2. The cashbook is the only measure family with a
-- clean, artifact-free monthly signal across the whole window: payments run
-- ₹156M/138M/92M/93M/96M/111M across the six fiscal years with no step change,
-- while the activity tables jump 609 -> 4,607 rows at FY 2023-24 purely because
-- costless activities begin being recorded (§5). Temporal pattern mining is
-- therefore routed HERE and to nowhere else.
--
-- THE GRID IS A CROSS JOIN, ON PURPOSE. Every GP x every month exists, measures
-- zero-filled. A GP with no payments for a quarter is a finding; if the row were
-- simply absent, the quarter would read as "no data" and the engine would never
-- see it. 1,181 of the 1,440 cells carry cashbook activity on this drop, so 259
-- rows exist only because the grid is complete.
--
-- THE CALENDAR IS DERIVED, NEVER WRITTEN DOWN. stg_month_calendar runs from
-- DATE_TRUNC('month', MIN(voucher.date)) to DATE_TRUNC('month', MAX(voucher.date))
-- — 2020-04 .. 2026-03, 72 months on this drop. Two consequences, both wanted:
--   * no wall-clock or sample-scale literal enters the view, so the statewide
--     drop re-derives its own window (D15);
--   * the 488 phantom activity_voucher links (fiscal_year '2026-2027', NULL
--     voucher_pk, dates from 2026-04-09 onward, §8.1) fall PAST the last
--     calendar month and are excluded structurally rather than by a filter.
--     They carry ₹13,513,516.05, which is exactly the gap between this view's
--     activity_linked_expenditure total and view1's total_expenditure.
--
-- SANCTIONS ARE CLIPPED BY THE SAME CALENDAR, and that is a real subtraction:
-- 61 of the 2,101 administrative approvals are dated outside the cashbook window
-- (14 before 2020-04 — twelve of them on 2019-10-02 — and 47 from 2026-04
-- onward, including the single future-dated sanction of §8.2). Their sanction
-- months have no row to attach to here. view3 counts approvals by FISCAL YEAR
-- and so reconciles to the full 2,101; this view does not, and the WP-D1 report
-- carries the arithmetic. Nothing is dropped from the data — only from a cube
-- whose time axis is the cashbook's.
--
-- Both SANCTIONED-basis amounts are carried, distinctly named, because §3 gives
-- the approval record two: `sanctioned_amount` is the scheme rollup
-- (fund_sanctioned_total, the headline SANCTIONED measure) and
-- `work_proposed_amount` is admin_approval's own work_proposed_cost. Neither is
-- a substitute for the other and a reader must never have to guess which is which.
--
-- Measures only are zero-filled; dimensions never are.
-- =============================================================================
WITH cash AS (
    SELECT v.gp_lgd_code,
           v.voucher_month_start                                     AS month_start,
           SUM(CASE WHEN v.direction = 'payment' THEN v.amount ELSE 0 END) AS payment_amount,
           SUM(CASE WHEN v.direction = 'receipt' THEN v.amount ELSE 0 END) AS receipt_amount,
           SUM(CASE WHEN v.direction = 'payment' THEN 1 ELSE 0 END)        AS payment_count,
           SUM(CASE WHEN v.direction = 'receipt' THEN 1 ELSE 0 END)        AS receipt_count
    FROM stg_voucher v
    GROUP BY 1, 2
),

-- Activity-linked spend, attributed to the month of the voucher that paid it.
-- This is the SPENT basis on a cash timeline; view1 carries the same rupees at
-- activity grain with no time axis.
linked AS (
    SELECT av.gp_lgd_code,
           av.voucher_month_start   AS month_start,
           SUM(av.voucher_cost)     AS activity_linked_expenditure
    FROM stg_activity_voucher av
    GROUP BY 1, 2
),

sanction AS (
    SELECT ap.gp_lgd_code,
           ap.sanction_month_start          AS month_start,
           COUNT(*)                         AS sanctions_count,
           SUM(ap.fund_sanctioned_total)    AS sanctioned_amount,
           SUM(ap.work_proposed_cost)       AS work_proposed_amount
    FROM stg_approval ap
    GROUP BY 1, 2
),

grid AS (
    SELECT g.gp_lgd_code, g.gp_name, g.block_code, g.block_name,
           g.district_code, g.district_name,
           c.month_start
    FROM stg_gram_panchayat g
    CROSS JOIN stg_month_calendar c
)

SELECT
    -- ── geography: all six name+code columns ───────────────────────────────
    CAST(grid.gp_lgd_code   AS VARCHAR) AS gp_lgd_code,
    CAST(grid.gp_name       AS VARCHAR) AS gp_name,
    CAST(grid.block_code    AS VARCHAR) AS block_code,
    CAST(grid.block_name    AS VARCHAR) AS block_name,
    CAST(grid.district_code AS VARCHAR) AS district_code,
    CAST(grid.district_name AS VARCHAR) AS district_name,

    -- ── temporal dimensions ────────────────────────────────────────────────
    -- 'YYYY-MM' sorts lexicographically in calendar order, so the engine can
    -- treat it as an ordered axis without parsing it.
    CAST(STRFTIME(grid.month_start, '%Y-%m') AS VARCHAR) AS month,
    CAST(CAST(YEAR(grid.month_start) AS VARCHAR) || '-Q'
      || CAST(QUARTER(grid.month_start) AS VARCHAR) AS VARCHAR) AS quarter,
    -- Indian fiscal year, April-March. Derived from the calendar month rather
    -- than read off voucher.fiscal_year so that a zero-filled cell still has
    -- one; the two agree on all 12,440 voucher rows (verified WP-D1).
    CAST(CASE WHEN MONTH(grid.month_start) >= 4
              THEN CAST(YEAR(grid.month_start)     AS VARCHAR) || '-' || CAST(YEAR(grid.month_start) + 1 AS VARCHAR)
              ELSE CAST(YEAR(grid.month_start) - 1 AS VARCHAR) || '-' || CAST(YEAR(grid.month_start)     AS VARCHAR)
         END AS VARCHAR)                                    AS fiscal_year,

    -- ── measures: CASHBOOK ─────────────────────────────────────────────────
    CAST(COALESCE(cash.payment_amount, 0) AS DOUBLE) AS payment_amount,
    CAST(COALESCE(cash.receipt_amount, 0) AS DOUBLE) AS receipt_amount,
    CAST(COALESCE(cash.payment_count,  0) AS DOUBLE) AS payment_count,
    CAST(COALESCE(cash.receipt_count,  0) AS DOUBLE) AS receipt_count,

    -- ── measures: SPENT, on the cash timeline ──────────────────────────────
    CAST(COALESCE(linked.activity_linked_expenditure, 0) AS DOUBLE)
                                                     AS activity_linked_expenditure,

    -- ── measures: SANCTIONED, by sanction month ────────────────────────────
    CAST(COALESCE(sanction.sanctions_count,      0) AS DOUBLE) AS sanctions_count,
    CAST(COALESCE(sanction.sanctioned_amount,    0) AS DOUBLE) AS sanctioned_amount,
    CAST(COALESCE(sanction.work_proposed_amount, 0) AS DOUBLE) AS work_proposed_amount

FROM grid
LEFT JOIN cash     ON cash.gp_lgd_code     = grid.gp_lgd_code
                  AND cash.month_start     = grid.month_start
LEFT JOIN linked   ON linked.gp_lgd_code   = grid.gp_lgd_code
                  AND linked.month_start   = grid.month_start
LEFT JOIN sanction ON sanction.gp_lgd_code = grid.gp_lgd_code
                  AND sanction.month_start = grid.month_start

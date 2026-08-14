-- =============================================================================
-- view3_gp_performance — GP x fiscal year (120 rows on this drop: 20 x 6)
--
-- DISCOVER_VIEW_MAPPING §4.3. The institution view: how each Gram Panchayat
-- performed, year by year, across planning, sanctioning, spending and evidence.
--
-- MATERIALISED FROM THE MASTER, LEFT JOINS ONLY. The grid is
-- `gram_panchayat` x the observed fiscal-year domain; every aggregate hangs off
-- it by LEFT JOIN and is zero-filled. The sample proves why this is not
-- pedantry: Chikilli has 640 planned activities and ZERO administrative
-- approvals. An inner join on the approval side would silently delete the six
-- most interesting rows in the table — a GP that plans and never gets sanctioned
-- is exactly the finding this view exists to surface. Post-view validation
-- pins the grain at 120 rows so a regression to inner-join behaviour fails the
-- build instead of quietly shrinking the denominator.
--
-- THE FISCAL-YEAR DOMAIN IS DERIVED (stg_fiscal_year_domain): the years actually
-- observed in planned_activity, plan and voucher — 2020-2021 .. 2025-2026 here.
-- activity_voucher is deliberately not in that union: it is the only table
-- carrying '2026-2027', on 488 orphan rows with no voucher and dates past the
-- cashbook (§8.1). Excluding the SOURCE rather than filtering a literal keeps
-- the exclusion honest when statewide data arrives (§5.3).
--
-- ONE ATTRIBUTION RULE. Everything that hangs off an activity is attributed to
-- that ACTIVITY's GP and fiscal year — approvals included. This is safe rather
-- than assumed: admin_approval's own fiscal year (plan_year + 1) equals
-- planned_activity.fiscal_year on all 2,101 approvals, and
-- activity_expenditure.fiscal_year equals it on every matched row (both verified
-- in WP-D1). Cashbook payments and receipts use voucher.fiscal_year, since they
-- are GP-level flows and many belong to no activity at all. Plans use
-- plan.fiscal_year.
--
-- AGREES WITH view1 BY CONSTRUCTION. Every activity-grain expression below is
-- the same expression view1 projects, over the same stg_* layer — including
-- overspend_vs_plan's coalesce and overspend_vs_sanction's deliberate null.
-- Sum any of them across this view and you get view1's column total.
--
-- NO RATE IS MATERIALISED (§3). n_completed / n_activities is a rate the reader
-- or the engine forms; storing it would make block and district roll-ups
-- averages of averages. Note that completion is near-degenerate on this sample
-- — 17 activities statewide are WORK COMPLETED (§8.4) — so n_completed is kept
-- as a known-degenerate calibration measure, not as a live signal.
-- =============================================================================
WITH activity AS (
    SELECT
        a.gp_lgd_code,
        a.fiscal_year,
        COUNT(*)                                                    AS n_activities,
        SUM(CASE WHEN a.is_costless = 'Costed'   THEN 1 ELSE 0 END) AS n_costed,
        SUM(CASE WHEN a.is_costless = 'Costless' THEN 1 ELSE 0 END) AS n_costless,
        SUM(a.total_cost)                                           AS planned_cost,
        SUM(ap.fund_sanctioned_total)                               AS sanctioned_total,
        SUM(ap.work_proposed_cost)                                  AS work_proposed_cost,
        SUM(COALESCE(e.total_expenditure, 0))                       AS expenditure_total,
        SUM(COALESCE(e.total_expenditure, 0) - COALESCE(a.total_cost, 0))
                                                                    AS overspend_vs_plan,
        SUM(COALESCE(e.total_expenditure, 0) - ap.fund_sanctioned_total)
                                                                    AS overspend_vs_sanction,
        SUM(CASE WHEN ap.activity_code IS NOT NULL THEN 1 ELSE 0 END) AS n_admin_approvals,
        SUM(COALESCE(ap.has_technical_approval, 0))                 AS n_tech_approvals,
        SUM(a.is_completed)                                         AS n_completed,
        SUM(a.is_ongoing)                                           AS n_ongoing,
        SUM(a.is_abandoned)                                         AS n_abandoned,
        SUM(CASE WHEN pp.activity_code IS NOT NULL THEN 1 ELSE 0 END) AS n_with_evidence,
        SUM(COALESCE(pp.evidence_uploads, 0))                       AS evidence_uploads
    FROM stg_planned_activity a
    LEFT JOIN stg_exp_rollup      e  ON e.activity_code  = a.activity_code
    LEFT JOIN stg_approval        ap ON ap.activity_code = a.activity_code
    LEFT JOIN stg_progress_rollup pp ON pp.activity_code = a.activity_code
    GROUP BY 1, 2
),

plans AS (
    SELECT gp_lgd_code, fiscal_year, COUNT(*) AS n_plans
    FROM stg_plan
    GROUP BY 1, 2
),

cash AS (
    SELECT gp_lgd_code, fiscal_year,
           SUM(CASE WHEN direction = 'payment' THEN amount ELSE 0 END) AS payment_amount,
           SUM(CASE WHEN direction = 'receipt' THEN amount ELSE 0 END) AS receipt_amount
    FROM stg_voucher
    GROUP BY 1, 2
),

grid AS (
    SELECT g.gp_lgd_code, g.gp_name, g.block_code, g.block_name,
           g.district_code, g.district_name,
           fy.fiscal_year
    FROM stg_gram_panchayat g
    CROSS JOIN stg_fiscal_year_domain fy
)

SELECT
    -- ── geography: all six name+code columns ───────────────────────────────
    CAST(grid.gp_lgd_code   AS VARCHAR) AS gp_lgd_code,
    CAST(grid.gp_name       AS VARCHAR) AS gp_name,
    CAST(grid.block_code    AS VARCHAR) AS block_code,
    CAST(grid.block_name    AS VARCHAR) AS block_name,
    CAST(grid.district_code AS VARCHAR) AS district_code,
    CAST(grid.district_name AS VARCHAR) AS district_name,

    -- ── temporal dimension ─────────────────────────────────────────────────
    CAST(grid.fiscal_year   AS VARCHAR) AS fiscal_year,

    -- ── measures: planning ─────────────────────────────────────────────────
    CAST(COALESCE(plans.n_plans,          0) AS DOUBLE) AS n_plans,
    CAST(COALESCE(activity.n_activities,  0) AS DOUBLE) AS n_activities,
    CAST(COALESCE(activity.n_costed,      0) AS DOUBLE) AS n_costed,
    CAST(COALESCE(activity.n_costless,    0) AS DOUBLE) AS n_costless,
    CAST(COALESCE(activity.planned_cost,  0) AS DOUBLE) AS planned_cost,

    -- ── measures: sanction ─────────────────────────────────────────────────
    CAST(COALESCE(activity.sanctioned_total,   0) AS DOUBLE) AS sanctioned_total,
    CAST(COALESCE(activity.work_proposed_cost, 0) AS DOUBLE) AS work_proposed_cost,
    CAST(COALESCE(activity.n_admin_approvals,  0) AS DOUBLE) AS n_admin_approvals,
    CAST(COALESCE(activity.n_tech_approvals,   0) AS DOUBLE) AS n_tech_approvals,

    -- ── measures: spend ────────────────────────────────────────────────────
    CAST(COALESCE(activity.expenditure_total, 0) AS DOUBLE) AS expenditure_total,
    -- A zero here means "nothing sanctioned in this cell", not "spent exactly
    -- what was sanctioned" — read it against n_admin_approvals, which is 0 in
    -- the same rows. Zero-fill is §4.3's rule for every measure on this grid.
    CAST(COALESCE(activity.overspend_vs_plan,     0) AS DOUBLE) AS overspend_vs_plan,
    CAST(COALESCE(activity.overspend_vs_sanction, 0) AS DOUBLE) AS overspend_vs_sanction,

    -- ── measures: cashbook (GP-level flows, not activity-attributed) ───────
    CAST(COALESCE(cash.payment_amount, 0) AS DOUBLE) AS payment_amount,
    CAST(COALESCE(cash.receipt_amount, 0) AS DOUBLE) AS receipt_amount,

    -- ── measures: progress and evidence ────────────────────────────────────
    CAST(COALESCE(activity.n_completed,      0) AS DOUBLE) AS n_completed,
    CAST(COALESCE(activity.n_ongoing,        0) AS DOUBLE) AS n_ongoing,
    CAST(COALESCE(activity.n_abandoned,      0) AS DOUBLE) AS n_abandoned,
    CAST(COALESCE(activity.n_with_evidence,  0) AS DOUBLE) AS n_with_evidence,
    CAST(COALESCE(activity.evidence_uploads, 0) AS DOUBLE) AS evidence_uploads

FROM grid
LEFT JOIN activity ON activity.gp_lgd_code = grid.gp_lgd_code
                  AND activity.fiscal_year = grid.fiscal_year
LEFT JOIN plans    ON plans.gp_lgd_code    = grid.gp_lgd_code
                  AND plans.fiscal_year    = grid.fiscal_year
LEFT JOIN cash     ON cash.gp_lgd_code     = grid.gp_lgd_code
                  AND cash.fiscal_year     = grid.fiscal_year

-- =============================================================================
-- view1_activity_lifecycle — one row per planned activity (12,704 on this drop)
--
-- DISCOVER_VIEW_MAPPING §4.1. This is `v_activity` re-expressed over the stg_*
-- layer, plus the 1:1 folds the Ask views keep in separate places: asset labels
-- (v_asset), fund splits (activity_fund), training, community service. Every
-- activity child table is 1:1 with planned_activity — 12,704 rows, 12,704
-- distinct activity_codes each — so folding them adds columns, never rows.
--
-- WHAT THE GRAIN COSTS. The join to planned_activity is what defines the row
-- set, so the twenty activity_expenditure codes with no planned_activity parent
-- (§8, 12,724 distinct expenditure codes vs 12,704 activities) do not appear
-- here. They carry ₹0 of total_expenditure on this drop, so nothing departs
-- with them; the WP-D1 report states the measured amount and row count, and
-- validation.yaml deliberately does NOT declare that foreign key.
--
-- MONEY BASES (§3) — never mix them silently:
--   PLANNED    total_cost, fund_*_total          (null <=> costless activity)
--   SANCTIONED work_proposed_cost, fund_sanctioned_*, tec_approval_cost
--   SPENT      total_expenditure (+ gen/sc/st)   == linked voucher sums, exactly
-- The two `overspend_*` columns are the one sanctioned cross-basis mix. Both are
-- signed differences, which roll up honestly where a ratio would not.
--
-- NO RATE IS MATERIALISED. Every rate ships as numerator + denominator:
-- the `is_*` / `has_*` flags are 0/1 numerators and `n_activities` is the
-- denominator, so a block or district roll-up re-derives the rate correctly
-- instead of averaging averages.
--
-- NO TEMPORAL DIMENSION (§4.1). Temporal mining runs on view2. `fiscal_year` is
-- here as a CATEGORICAL dimension only, and count-based comparisons across the
-- FY 2023-24 boundary need the §5 reading-note caveat — the activity count jumps
-- because costless activities begin being recorded, not because activity rose.
-- The sanction date is deliberately not projected: it exists for only 17% of
-- rows, and one value is future-dated (§8.2).
--
-- NOT PROJECTED, BY ROLE (§7 / §9.6): activity_name, activity_desc, search_text,
-- plan_code, source_file, operation_*, the raw decode codes, expenditure_id,
-- v_exp.scheme_name (82% null), and every free-text authority or document
-- number. `days_since_sanction` is dropped as non-reproducible (§3).
-- =============================================================================
SELECT
    -- ── grain ──────────────────────────────────────────────────────────────
    CAST(a.activity_code AS VARCHAR)          AS activity_code,

    -- ── geography: all six name+code columns, on every view ────────────────
    CAST(g.gp_lgd_code   AS VARCHAR)          AS gp_lgd_code,
    CAST(g.gp_name       AS VARCHAR)          AS gp_name,
    CAST(g.block_code    AS VARCHAR)          AS block_code,
    CAST(g.block_name    AS VARCHAR)          AS block_name,
    CAST(g.district_code AS VARCHAR)          AS district_code,
    CAST(g.district_name AS VARCHAR)          AS district_name,

    -- ── dimensions ─────────────────────────────────────────────────────────
    CAST(a.fiscal_year          AS VARCHAR)   AS fiscal_year,
    CAST(a.theme                AS VARCHAR)   AS theme,
    CAST(a.focus_area_name      AS VARCHAR)   AS focus_area_name,
    CAST(a.work_type_label      AS VARCHAR)   AS work_type_label,
    CAST(a.activity_for_label   AS VARCHAR)   AS activity_for_label,
    CAST(a.activity_type_label  AS VARCHAR)   AS activity_type_label,
    CAST(a.output_type_label    AS VARCHAR)   AS output_type_label,
    CAST(a.status_label         AS VARCHAR)   AS status_label,
    CAST(a.is_costless          AS VARCHAR)   AS is_costless,
    CAST(ast.asset_category_label AS VARCHAR) AS asset_category_label,
    CAST(ast.asset_type_label     AS VARCHAR) AS asset_type_label,
    -- approval-subset dimensions: null for the 83% of activities with no
    -- administrative approval. Absence of a sanction record is a data property,
    -- not evidence that the activity was unsanctioned (§3).
    CAST(ap.tied_untied            AS VARCHAR) AS tied_untied,
    CAST(ap.authority_clean        AS VARCHAR) AS sanction_authority,
    CAST(ap.sanctioned_scheme_name AS VARCHAR) AS sanctioned_scheme_name,
    CAST(ap.fund_component_name    AS VARCHAR) AS fund_component_name,
    CAST(ap.tec_approval_required  AS VARCHAR) AS tec_approval_required,
    -- sparse candidate dimensions (§9.7): staged into the view so the statewide
    -- switch is a VIEW1_CONFIG edit rather than a pack change (§6). The
    -- sample-phase config omits them.
    CAST(f.planned_fund_scheme_name    AS VARCHAR) AS planned_fund_scheme_name,
    CAST(f.planned_fund_component_name AS VARCHAR) AS planned_fund_component_name,
    CAST(tr.training_category_label    AS VARCHAR) AS training_category_label,
    CAST(tr.training_organiser_label   AS VARCHAR) AS training_organiser_label,
    CAST(cs.community_service_label    AS VARCHAR) AS community_service_label,

    -- ── measures: PLANNED ──────────────────────────────────────────────────
    CAST(1                      AS DOUBLE)    AS n_activities,
    CAST(a.total_cost           AS DOUBLE)    AS total_cost,
    CAST(f.fund_tied_total      AS DOUBLE)    AS fund_tied_total,
    CAST(f.fund_untied_total    AS DOUBLE)    AS fund_untied_total,
    CAST(f.fund_abandoned_total AS DOUBLE)    AS fund_abandoned_total,
    CAST(f.fund_tied_general    AS DOUBLE)    AS fund_tied_general,
    CAST(f.fund_tied_sc         AS DOUBLE)    AS fund_tied_sc,
    CAST(f.fund_tied_st         AS DOUBLE)    AS fund_tied_st,
    CAST(f.fund_untied_general  AS DOUBLE)    AS fund_untied_general,
    CAST(f.fund_untied_sc       AS DOUBLE)    AS fund_untied_sc,
    CAST(f.fund_untied_st       AS DOUBLE)    AS fund_untied_st,

    -- ── measures: SANCTIONED (approval subset) ─────────────────────────────
    CAST(ap.work_proposed_cost       AS DOUBLE) AS work_proposed_cost,
    CAST(ap.fund_sanctioned_total    AS DOUBLE) AS fund_sanctioned_total,
    CAST(ap.fund_sanctioned_general  AS DOUBLE) AS fund_sanctioned_general,
    CAST(ap.fund_sanctioned_sc       AS DOUBLE) AS fund_sanctioned_sc,
    CAST(ap.fund_sanctioned_st       AS DOUBLE) AS fund_sanctioned_st,
    CAST(ap.tec_approval_cost        AS DOUBLE) AS tec_approval_cost,
    -- how many admin_approval_scheme rows the ARG_MAX rollup collapsed: 1 for
    -- almost every approved activity, 2 for the six multi-scheme ones.
    CAST(ap.scheme_rows              AS DOUBLE) AS sanction_scheme_rows,

    -- ── measures: SPENT ────────────────────────────────────────────────────
    CAST(COALESCE(e.total_expenditure, 0) AS DOUBLE) AS total_expenditure,
    CAST(COALESCE(e.gen_amount, 0)        AS DOUBLE) AS gen_amount,
    CAST(COALESCE(e.sc_amount,  0)        AS DOUBLE) AS sc_amount,
    CAST(COALESCE(e.st_amount,  0)        AS DOUBLE) AS st_amount,
    CAST(e.approved_cost_action_plan      AS DOUBLE) AS approved_cost_action_plan,
    CAST(e.technical_approved_cost        AS DOUBLE) AS technical_approved_cost,
    CAST(e.admin_approved_cost            AS DOUBLE) AS admin_approved_cost,

    -- ── measures: the two signed cross-basis differences (§3) ──────────────
    -- SPENT - PLANNED. total_cost is null exactly when the activity is costless,
    -- i.e. planned at zero, so it is coalesced: an activity that spends money
    -- against no planned cost must show up as overspend, not as null. On this
    -- drop costless activities carry ₹0 of expenditure, so the coalesce changes
    -- no number here — it is the statewide behaviour that is being pinned.
    CAST(COALESCE(e.total_expenditure, 0) - COALESCE(a.total_cost, 0) AS DOUBLE)
                                                     AS overspend_vs_plan,
    -- SPENT - SANCTIONED. NOT coalesced: null where no sanction record exists,
    -- because absence of a record is not a sanction of zero (§3). Defined on the
    -- 2,101-activity approval subset only.
    CAST(COALESCE(e.total_expenditure, 0) - ap.fund_sanctioned_total AS DOUBLE)
                                                     AS overspend_vs_sanction,

    -- ── measures: activity content ─────────────────────────────────────────
    CAST(ast.asset_unit_cost                    AS DOUBLE) AS asset_unit_cost,
    CAST(tr.training_trainees_total             AS DOUBLE) AS trainees_total,
    CAST(tr.training_duration_days              AS DOUBLE) AS training_days,
    CAST(cs.community_beneficiaries_expected    AS DOUBLE) AS beneficiaries_expected,
    CAST(cs.community_service_duration          AS DOUBLE) AS community_service_days,
    CAST(COALESCE(pp.evidence_uploads, 0)       AS DOUBLE) AS evidence_uploads,

    -- ── flags: SUM-able numerators, denominator is n_activities ────────────
    CAST(a.is_started        AS BIGINT) AS is_started,
    CAST(a.is_completed      AS BIGINT) AS is_completed,
    CAST(a.is_ongoing        AS BIGINT) AS is_ongoing,
    CAST(a.is_abandoned      AS BIGINT) AS is_abandoned,
    CAST(a.is_under_approval AS BIGINT) AS is_under_approval,
    CAST(CASE WHEN ap.activity_code IS NOT NULL THEN 1 ELSE 0 END AS BIGINT)
                                        AS is_admin_approved,
    -- 140 activities carry an admin_approved_cost with no approval record.
    CAST(CASE WHEN ap.activity_code IS NULL
               AND COALESCE(e.admin_approved_cost, 0) > 0 THEN 1 ELSE 0 END AS BIGINT)
                                        AS has_approval_cost_only,
    CAST(COALESCE(ap.has_technical_approval, 0) AS BIGINT) AS has_technical_approval,
    CAST(CASE WHEN pp.activity_code IS NOT NULL THEN 1 ELSE 0 END AS BIGINT)
                                        AS has_progress_evidence

FROM stg_planned_activity a
-- inner join, exactly as v_activity: every activity has a gram_panchayat row
-- (verified, zero orphans). Zero-activity GPs are view3's job, not this view's.
JOIN      stg_gram_panchayat          g   ON g.gp_lgd_code   = a.gp_lgd_code
LEFT JOIN stg_exp_rollup              e   ON e.activity_code = a.activity_code
LEFT JOIN stg_approval                ap  ON ap.activity_code = a.activity_code
LEFT JOIN stg_progress_rollup         pp  ON pp.activity_code = a.activity_code
LEFT JOIN stg_activity_asset          ast ON ast.activity_code = a.activity_code
LEFT JOIN stg_activity_fund           f   ON f.activity_code  = a.activity_code
LEFT JOIN stg_activity_training       tr  ON tr.activity_code = a.activity_code
LEFT JOIN stg_activity_community_service cs ON cs.activity_code = a.activity_code

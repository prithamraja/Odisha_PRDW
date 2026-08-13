-- ============================================================
--  Chatbot support views for panchayat_1.duckdb
--  Run this once after (re)building the database:
--      duckdb panchayat_1.duckdb < create_views.sql
--  Every parameterised query in AI_Chatbot_Questions_V4.xlsx
--  reads from these views.
--
--  v_exp        expenditure rolled up to one row per activity
--  v_approval   administrative + technical approval, with the
--               sanctioned scheme and tied/untied component
--  v_activity   the workhorse: one row per planned activity
--  v_plan       GPDP plans with geography
--  v_asset      asset rows with parent activity and geography
--  v_progress   geotagged physical-progress evidence per activity
--  v_voucher    cashbook vouchers with geography
-- ============================================================

-- Expenditure rolled up to one row per activity.
-- (6 activity_codes have duplicate rows in activity_expenditure;
--  aggregating here keeps the joins strictly 1:1.)
CREATE OR REPLACE VIEW v_exp AS
SELECT activity_code,
       SUM(approved_cost_action_plan) AS approved_cost_action_plan,
       SUM(technical_approved_cost)   AS technical_approved_cost,
       SUM(admin_approved_cost)       AS admin_approved_cost,
       SUM(general)                   AS gen_amount,
       SUM(sc)                        AS sc_amount,
       SUM(st)                        AS st_amount,
       SUM(total_expenditure)         AS total_expenditure,
       MAX(scheme_name)               AS scheme_name,
       MIN(expenditure_id)            AS expenditure_id
FROM activity_expenditure
GROUP BY activity_code;

-- ------------------------------------------------------------
-- v_approval : one row per activity that has an administrative
-- approval, carrying the sanction date, order number, authority,
-- the technical approval alongside it, and the sanctioned scheme
-- with its tied/untied component.
--
-- Notes on the source data:
--  * admin_approval.plan_year is 'YYYY'; it is converted here to
--    the 'YYYY-YYYY' form used everywhere else.
--  * adm_approval_authority is free text with many spellings of
--    the same office (SARPANCH / SARAPANCH / Sarapancha / ...).
--    authority_clean collapses the obvious variants.
--  * 6 activity_codes have two admin_approval_scheme rows; the
--    scheme columns below take the largest-value row so the join
--    stays 1:1. Query admin_approval_scheme directly if you need
--    the full multi-scheme split.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_approval AS
WITH sch AS (
    SELECT activity_code,
           SUM(COALESCE(fund_sanctioned_general,0)) AS fund_sanctioned_general,
           SUM(COALESCE(fund_sanctioned_sc,0))      AS fund_sanctioned_sc,
           SUM(COALESCE(fund_sanctioned_st,0))      AS fund_sanctioned_st,
           SUM(COALESCE(fund_sanctioned_total,0))   AS fund_sanctioned_total,
           COUNT(*)                                  AS scheme_rows,
           ARG_MAX(scheme_code,           COALESCE(fund_sanctioned_total,0)) AS scheme_code,
           ARG_MAX(scheme_component_code, COALESCE(fund_sanctioned_total,0)) AS scheme_component_code
    FROM admin_approval_scheme
    GROUP BY activity_code)
SELECT
    aa.activity_code,
    aa.gp_lgd_code,
    aa.plan_year || '-' || CAST(CAST(aa.plan_year AS INT) + 1 AS VARCHAR) AS fiscal_year,
    aa.adm_approval_no,
    aa.adm_approval_sanction_date              AS sanction_date,
    CAST(aa.adm_approval_sanction_date AS DATE) AS sanction_day,
    DATE_TRUNC('month', aa.adm_approval_sanction_date) AS sanction_month,
    QUARTER(aa.adm_approval_sanction_date)     AS sanction_quarter,
    aa.work_proposed_cost,
    aa.adm_approval_authority                  AS authority_raw,
    CASE
      WHEN UPPER(aa.adm_approval_authority) LIKE 'SAR%PANCH%' THEN 'Sarpanch'
      WHEN UPPER(aa.adm_approval_authority) LIKE '%BDO%'      THEN 'BDO'
      WHEN UPPER(aa.adm_approval_authority) IN ('AE','AEE','JE','ASSISTANT ENGINEER') THEN 'Engineer'
      WHEN UPPER(aa.adm_approval_authority) LIKE 'GP%'        THEN 'Gram Panchayat'
      WHEN UPPER(aa.adm_approval_authority) LIKE '%PALIKA%'
        OR UPPER(aa.adm_approval_authority) LIKE '%SAMITI%'   THEN 'Panchayat Samiti'
      ELSE TRIM(aa.adm_approval_authority)
    END                                        AS authority_clean,
    ta.tec_approval_required,
    ta.tec_approval_cost,
    ta.tec_approval_authority,
    ta.tec_approval_order_no,
    ta.tec_approval_order_date,
    CASE WHEN ta.activity_code IS NOT NULL THEN 1 ELSE 0 END AS has_technical_approval,
    sch.fund_sanctioned_general,
    sch.fund_sanctioned_sc,
    sch.fund_sanctioned_st,
    sch.fund_sanctioned_total,
    sch.scheme_rows,
    sch.scheme_code,
    COALESCE(fs.description, 'Code ' || sch.scheme_code) AS sanctioned_scheme_name,
    sch.scheme_component_code,
    COALESCE(fc.description, 'Code ' || sch.scheme_component_code) AS fund_component_name,
    -- Coarse tied / untied classification. 4249 = Tied Grant,
    -- 4211 = Basic Grant (untied). Everything else is reported as
    -- 'Other' rather than guessed at.
    CASE sch.scheme_component_code
      WHEN '4249' THEN 'Tied'
      WHEN '4211' THEN 'Untied'
      WHEN '4250' THEN 'Untied'
      ELSE 'Other'
    END AS tied_untied
FROM admin_approval aa
LEFT JOIN technical_approval ta ON ta.activity_code = aa.activity_code
LEFT JOIN sch                   ON sch.activity_code = aa.activity_code
LEFT JOIN dim_code fs ON fs.variable = 'fund_scheme_code'
                     AND fs.code = sch.scheme_code
LEFT JOIN dim_code fc ON fc.variable = 'fund_component_code'
                     AND fc.code = sch.scheme_component_code;

-- ------------------------------------------------------------
-- v_activity : the workhorse. One row per planned activity,
-- with geography, decoded labels, LSDG theme, expenditure and
-- (new) the administrative-approval record.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_activity AS
SELECT
    a.activity_code,
    a.plan_code,
    a.gp_lgd_code,
    a.fiscal_year,
    g.gp_name,
    g.block_name,
    g.zp_name                                   AS district_name,
    g.state_name,
    a.activity_name,
    a.activity_desc,
    LOWER(a.activity_name || ' ' || COALESCE(a.activity_desc,'')) AS search_text,
    a.total_cost,
    a.is_costless_activity,
    COALESCE(fa.description, 'Code ' || a.focus_area) AS focus_area_name,
    COALESCE(th.lsdg_theme, 'Unmapped theme')         AS theme,
    COALESCE(TRIM(REPLACE(stx.description, chr(9), ' ')),
             'Unknown (' || a.activity_status || ')') AS status_label,
    COALESCE(wt.description, 'Unknown')               AS work_type_label,
    COALESCE(aty.description, 'Unknown')               AS activity_type_label,
    COALESCE(af.description, 'Unknown')               AS activity_for_label,
    a.activity_status,
    a.focus_area,
    a.work_type,
    -- normalised progress flags, so questions do not each re-invent them
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) IN ('WORK ONGOING','WORK COMPLETED')
         THEN 1 ELSE 0 END                            AS is_started,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK COMPLETED' THEN 1 ELSE 0 END AS is_completed,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK ONGOING'   THEN 1 ELSE 0 END AS is_ongoing,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK ABANDONED' THEN 1 ELSE 0 END AS is_abandoned,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'UNDER APPROVAL' THEN 1 ELSE 0 END AS is_under_approval,
    e.approved_cost_action_plan,
    e.technical_approved_cost,
    e.admin_approved_cost,
    COALESCE(e.gen_amount,0) AS gen_amount,
    COALESCE(e.sc_amount,0)  AS sc_amount,
    COALESCE(e.st_amount,0)  AS st_amount,
    COALESCE(e.total_expenditure,0) AS total_expenditure,
    e.scheme_name,
    e.expenditure_id,
    -- Administrative approval now comes from the admin_approval table
    -- (2,101 activities) rather than being inferred from a non-zero
    -- admin_approved_cost. 140 activities carry a cost but have no
    -- approval record; has_approval_cost_only flags them.
    CASE WHEN ap.activity_code IS NOT NULL THEN 1 ELSE 0 END AS is_admin_approved,
    CASE WHEN ap.activity_code IS NULL
          AND COALESCE(e.admin_approved_cost,0) > 0 THEN 1 ELSE 0 END AS has_approval_cost_only,
    ap.adm_approval_no,
    ap.sanction_date,
    ap.sanction_day,
    ap.sanction_month,
    ap.sanction_quarter,
    ap.authority_clean          AS sanction_authority,
    ap.authority_raw            AS sanction_authority_raw,
    ap.work_proposed_cost,
    ap.tec_approval_order_no,
    ap.tec_approval_order_date,
    ap.tec_approval_cost,
    ap.tec_approval_authority,
    ap.has_technical_approval,
    ap.sanctioned_scheme_name,
    ap.fund_component_name,
    ap.tied_untied,
    ap.fund_sanctioned_general,
    ap.fund_sanctioned_sc,
    ap.fund_sanctioned_st,
    ap.fund_sanctioned_total,
    ap.scheme_rows,
    -- Days from sanction to the end of the plan year, useful for the
    -- "no expenditure N days after sanction" style questions.
    CASE WHEN ap.sanction_day IS NOT NULL
         THEN DATE_DIFF('day', ap.sanction_day, CURRENT_DATE) END AS days_since_sanction,
    COALESCE(pp.evidence_uploads, 0) AS evidence_uploads,
    CASE WHEN pp.activity_code IS NOT NULL THEN 1 ELSE 0 END AS has_progress_evidence
FROM planned_activity a
JOIN gram_panchayat g ON g.gp_lgd_code = a.gp_lgd_code
LEFT JOIN v_exp   e   ON e.activity_code = a.activity_code
LEFT JOIN v_approval ap ON ap.activity_code = a.activity_code
LEFT JOIN (SELECT activity_code, COUNT(*) AS evidence_uploads
           FROM physical_progress GROUP BY activity_code) pp
       ON pp.activity_code = a.activity_code
LEFT JOIN dim_code fa ON fa.variable = 'focus_area'
                     AND fa.code = CAST(a.focus_area AS VARCHAR)
LEFT JOIN dim_lsdg_theme th ON th.focus_area_name = fa.description
LEFT JOIN dim_code stx ON stx.variable = 'activity_status'
                      AND stx.code = CAST(a.activity_status AS VARCHAR)
LEFT JOIN dim_code wt  ON wt.variable = 'work_type'
                      AND wt.code = CAST(a.work_type AS VARCHAR)
LEFT JOIN dim_code aty ON aty.variable = 'activity_type'
                      AND aty.code = CAST(a.activity_type AS VARCHAR)
LEFT JOIN dim_code af  ON af.variable = 'activity_for'
                     AND af.code = CAST(a.activity_for AS VARCHAR);

-- ------------------------------------------------------------
-- v_plan : GPDP plans with geography.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_plan AS
SELECT p.plan_code, p.gp_lgd_code, p.fiscal_year, p.plan_type,
       p.approval_date, p.plan_code_status,
       g.gp_name, g.block_name, g.zp_name AS district_name, g.state_name,
       CASE WHEN p.approval_date IS NOT NULL THEN 1 ELSE 0 END AS is_approved
FROM plan p
JOIN gram_panchayat g ON g.gp_lgd_code = p.gp_lgd_code;

-- ------------------------------------------------------------
-- v_asset : asset rows with their parent activity and geography.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_asset AS
SELECT aa.*,
       a.fiscal_year, a.gp_name, a.block_name, a.district_name,
       a.activity_name, a.focus_area_name, a.theme, a.status_label,
       a.work_type_label, a.total_expenditure, a.total_cost,
       COALESCE(ac.description, 'Uncategorised') AS asset_category_label,
       COALESCE(asc_.description,'Uncategorised') AS asset_subcategory_label,
       COALESCE(mac.description,'Uncategorised') AS main_asset_category_label,
       COALESCE(ast.description,'Unknown')       AS asset_type_label
FROM activity_asset aa
JOIN v_activity a ON a.activity_code = aa.activity_code
LEFT JOIN dim_code ac   ON ac.variable  = 'asset_category'
                       AND ac.code = CAST(CAST(aa.asset_category AS BIGINT) AS VARCHAR)
LEFT JOIN dim_code asc_ ON asc_.variable = 'asset_subcategory'
                       AND asc_.code = CAST(CAST(aa.asset_subcategory AS BIGINT) AS VARCHAR)
LEFT JOIN dim_code mac  ON mac.variable = 'main_asset_category'
                       AND mac.code = CAST(CAST(aa.main_asset_category AS BIGINT) AS VARCHAR)
LEFT JOIN dim_code ast  ON ast.variable = 'asset_type'
                       AND ast.code = CAST(CAST(aa.asset_type AS BIGINT) AS VARCHAR);

-- ------------------------------------------------------------
-- v_progress : geotagged physical-progress uploads, with the
-- parent activity and geography. This is photo/GPS evidence, not
-- a stage model - there are no stage names or stage dates.
-- 1,675 of 12,704 activities have at least one upload.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_progress AS
SELECT pp.row_id, pp.parent_row_id, pp.pos, pp.activity_code,
       pp.file_upload_id, pp.longitude, pp.latitude, pp.n_coords,
       a.fiscal_year, a.gp_name, a.block_name, a.district_name,
       a.activity_name, a.focus_area_name, a.theme, a.status_label,
       a.total_expenditure, a.total_cost
FROM physical_progress pp
JOIN v_activity a ON a.activity_code = pp.activity_code;

-- ------------------------------------------------------------
-- v_voucher : cashbook vouchers with geography.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_voucher AS
SELECT v.*, g.gp_name, g.block_name, g.zp_name AS district_name
FROM voucher v
JOIN gram_panchayat g ON g.gp_lgd_code = v.gp_lgd_code;

-- =============================================================================
-- domain_pack_prdw / derived_columns.sql
-- =============================================================================
-- Staging layer for the Odisha PR&DW "Discover" views.
--
-- CONTRACT WITH ASK. Every derivation below is re-expressed VERBATIM from
-- `Data/create_views.sql` — the same view definitions the Ask chatbot's
-- parameterised queries read. Same decode joins, same CASE ladders, same
-- rollups. If a number differs between an Ask answer and a Discover finding,
-- that is a bug in this file, not a modelling choice. Deviations are marked
-- `-- DELTA` and there is exactly one (see §4 below).
--
-- Layout:
--   1. stg_<table>          — one per registered source (19). Pass-through where
--                             nothing derives, so the views address a single
--                             uniform namespace.
--   2. stg_exp_rollup       — v_exp: expenditure to one row per activity
--      stg_approval         — v_approval: admin + technical approval, scheme
--                             rollup, authority_clean, tied_untied
--      stg_progress_rollup  — the v_activity evidence-upload subquery
--   3. stg_month_calendar   — the view2 month spine, DERIVED from the cashbook
--      stg_fiscal_year_domain — the view3 fiscal-year spine, DERIVED
--
-- NO WALL-CLOCK VALUES. Every reference point is a scalar subquery over the
-- data. That is why the calendar in §3 is derived rather than written down, and
-- why v_activity's `days_since_sanction` is dropped:
--
--   -- DELTA (the only one): v_activity.days_since_sanction is NOT re-expressed.
--   -- It is DATE_DIFF('day', sanction_day, CURRENT_DATE), so its value depends
--   -- on when the build runs. DISCOVER_VIEW_MAPPING §3 excludes it everywhere.
--
-- PERSON-FREE BY CONSTRUCTION. Free-text authority fields, activity names and
-- descriptions, and document numbers are consumed HERE (into authority_clean,
-- into join keys) and never projected by a view — DISCOVER_VIEW_MAPPING §9.6.
-- =============================================================================


-- #############################################################################
-- 1. stg_<table> — one per registered source
-- #############################################################################

-- Decode tables first: the staging views below join to them.
CREATE OR REPLACE VIEW stg_dim_code          AS SELECT * FROM dim_code;
CREATE OR REPLACE VIEW stg_dim_lsdg_theme    AS SELECT * FROM dim_lsdg_theme;
-- Currently referenced by no populated column — welfare tagging arrives with
-- NSAP data, if ever (§7). Staged so the crosswalk can say so.
CREATE OR REPLACE VIEW stg_dim_welfare_scheme AS SELECT * FROM dim_welfare_scheme;


-- The geography spine. All six name+code columns, named as every view exposes
-- them (zp_name -> district_name, per v_activity). state_* is constant in this
-- drop and excluded from mining, but staged for statewide continuity (§7).
CREATE OR REPLACE VIEW stg_gram_panchayat AS
SELECT gp_lgd_code,
       gp_name,
       block_code,
       block_name,
       district_code,
       zp_name AS district_name,
       state_code,
       state_name
FROM gram_panchayat;


-- planned_activity + every dim_code decode v_activity performs, + the
-- normalised progress flags. Decode joins are VARCHAR-to-VARCHAR with the
-- explicit CAST v_activity uses; the status decode carries v_activity's
-- TRIM/chr(9) cleaning, which is what makes the tab-prefixed WORK COMPLETED
-- (17 activities, §8.3) land in the same bucket as a clean one.
CREATE OR REPLACE VIEW stg_planned_activity AS
SELECT
    a.*,
    COALESCE(fa.description, 'Code ' || a.focus_area)   AS focus_area_name,
    COALESCE(th.lsdg_theme, 'Unmapped theme')           AS theme,
    COALESCE(TRIM(REPLACE(stx.description, chr(9), ' ')),
             'Unknown (' || a.activity_status || ')')   AS status_label,
    COALESCE(wt.description,  'Unknown')                AS work_type_label,
    COALESCE(aty.description, 'Unknown')                AS activity_type_label,
    COALESCE(af.description,  'Unknown')                AS activity_for_label,
    -- v_activity does not decode output_type; DISCOVER_VIEW_MAPPING §4.1 asks
    -- for output_type_label, so the decode follows the same COALESCE-to-'Code N'
    -- shape as focus_area. All eight output_type codes are description-less on
    -- this drop, so every value is currently 'Code 1NN' (reported, not fixed).
    COALESCE(ot.description, 'Code ' || a.output_type)  AS output_type_label,
    -- §2's `is_costless` dimension (Costed / Costless), off the raw 0/1 flag.
    CASE a.is_costless_activity WHEN '1' THEN 'Costless'
                                WHEN '0' THEN 'Costed'
                                ELSE 'Unknown' END      AS is_costless,
    -- normalised progress flags, verbatim from v_activity
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) IN ('WORK ONGOING','WORK COMPLETED')
         THEN 1 ELSE 0 END                              AS is_started,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK COMPLETED' THEN 1 ELSE 0 END AS is_completed,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK ONGOING'   THEN 1 ELSE 0 END AS is_ongoing,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'WORK ABANDONED' THEN 1 ELSE 0 END AS is_abandoned,
    CASE WHEN TRIM(REPLACE(stx.description, chr(9), ' ')) = 'UNDER APPROVAL' THEN 1 ELSE 0 END AS is_under_approval
FROM planned_activity a
LEFT JOIN stg_dim_code fa  ON fa.variable  = 'focus_area'
                          AND fa.code      = CAST(a.focus_area AS VARCHAR)
LEFT JOIN stg_dim_lsdg_theme th ON th.focus_area_name = fa.description
LEFT JOIN stg_dim_code stx ON stx.variable = 'activity_status'
                          AND stx.code     = CAST(a.activity_status AS VARCHAR)
LEFT JOIN stg_dim_code wt  ON wt.variable  = 'work_type'
                          AND wt.code      = CAST(a.work_type AS VARCHAR)
LEFT JOIN stg_dim_code aty ON aty.variable = 'activity_type'
                          AND aty.code     = CAST(a.activity_type AS VARCHAR)
LEFT JOIN stg_dim_code af  ON af.variable  = 'activity_for'
                          AND af.code      = CAST(a.activity_for AS VARCHAR)
LEFT JOIN stg_dim_code ot  ON ot.variable  = 'output_type'
                          AND ot.code      = CAST(a.output_type AS VARCHAR);


-- v_plan's is_approved flag. approval_date is non-null on all 204 rows in this
-- drop, so the flag is currently constant 1 — kept because that is a property
-- of the sample, not of the schema.
-- `approval_date_ts`: the generic runner's CHECK 6 reads min()/max() back and
-- calls .date() on them, which only a datetime carries. The analytical column
-- stays DATE per §7; this TIMESTAMP twin exists solely so the date-range check
-- can run. No view projects it. Same pattern on the four other dated tables.
CREATE OR REPLACE VIEW stg_plan AS
SELECT p.*,
       CASE WHEN p.approval_date IS NOT NULL THEN 1 ELSE 0 END AS is_approved,
       CAST(p.approval_date AS TIMESTAMP)                      AS approval_date_ts
FROM plan p;


-- The cashbook. fiscal_year is carried by the source and agrees with the
-- April-March fiscal year of `date` on all 12,440 rows (verified WP-D1), so
-- view2 derives its calendar fiscal year the same way without contradiction.
CREATE OR REPLACE VIEW stg_voucher AS
SELECT v.*,
       DATE_TRUNC('month', v.date)              AS voucher_month_start,
       CAST(v.date AS TIMESTAMP)                AS date_ts
FROM voucher v;


-- Activity-to-voucher links. 488 rows carry a NULL voucher_pk and dates from
-- 2026-04 onward, beyond the cashbook's coverage (§8.1). They are NOT filtered
-- here — view2's derived calendar ends where the cashbook ends, so they fall
-- outside it structurally, and the crosswalk/report state the arithmetic.
--
-- voucher_pk_norm — NEW DEFECT, found in WP-D1, not in DISCOVER_VIEW_MAPPING §8.
-- activity_voucher stores voucher_pk in float text form ('186.0') while voucher
-- stores it as integer text ('1'). Compared as VARCHAR the two NEVER match:
-- 0 of the 5,488 non-null links join, not 5,488 of 5,488. The normalisation is
-- v_asset's own double-cast idiom, applied to the same class of problem, and it
-- recovers all 5,488 links exactly. Nothing is repaired in the data and no
-- measure depends on this column — no view projects it. It exists so the
-- foreign key can be declared and checked (validation.yaml CHECK 3) instead of
-- the defect sitting silently between two tables.
CREATE OR REPLACE VIEW stg_activity_voucher AS
SELECT av.*,
       DATE_TRUNC('month', av.voucher_date)              AS voucher_month_start,
       CAST(av.voucher_date AS TIMESTAMP)                AS voucher_date_ts,
       CAST(CAST(av.voucher_pk AS BIGINT) AS VARCHAR)    AS voucher_pk_norm
FROM activity_voucher av;


CREATE OR REPLACE VIEW stg_activity_expenditure AS SELECT * FROM activity_expenditure;


-- admin_approval + v_approval's two derivations that belong to this table:
-- the 'YYYY' -> 'YYYY-YYYY' fiscal year, and authority_clean. The raw
-- free-text authority is consumed here and never leaves this file (§9.6).
CREATE OR REPLACE VIEW stg_admin_approval AS
SELECT
    aa.*,
    aa.plan_year || '-' || CAST(CAST(aa.plan_year AS INT) + 1 AS VARCHAR) AS fiscal_year,
    CAST(aa.adm_approval_sanction_date AS DATE)              AS sanction_day,
    DATE_TRUNC('month', aa.adm_approval_sanction_date)       AS sanction_month_start,
    QUARTER(aa.adm_approval_sanction_date)                   AS sanction_quarter,
    CASE
      WHEN UPPER(aa.adm_approval_authority) LIKE 'SAR%PANCH%' THEN 'Sarpanch'
      WHEN UPPER(aa.adm_approval_authority) LIKE '%BDO%'      THEN 'BDO'
      WHEN UPPER(aa.adm_approval_authority) IN ('AE','AEE','JE','ASSISTANT ENGINEER') THEN 'Engineer'
      WHEN UPPER(aa.adm_approval_authority) LIKE 'GP%'        THEN 'Gram Panchayat'
      WHEN UPPER(aa.adm_approval_authority) LIKE '%PALIKA%'
        OR UPPER(aa.adm_approval_authority) LIKE '%SAMITI%'   THEN 'Panchayat Samiti'
      ELSE TRIM(aa.adm_approval_authority)
    END                                                      AS authority_clean,
    CAST(aa.adm_approval_sanction_date AS TIMESTAMP)         AS adm_approval_sanction_date_ts
FROM admin_approval aa;


CREATE OR REPLACE VIEW stg_admin_approval_scheme AS SELECT * FROM admin_approval_scheme;


CREATE OR REPLACE VIEW stg_technical_approval AS
SELECT ta.*,
       CAST(ta.tec_approval_order_date AS TIMESTAMP) AS tec_approval_order_date_ts
FROM technical_approval ta;


-- Fund splits. The tied/untied/abandoned totals are the sums §3 declares as
-- measures; the gen/sc/st components stay available alongside them. The two
-- rows carrying fund_overflow_json (multi-scheme funding squeezed into one row)
-- lose that split here — accepted and logged, §8.8.
-- fund_scheme_code / fund_component_code are the PLANNED-side funding codes and
-- are a different pair from admin_approval_scheme's sanctioned codes; the
-- labels are named `planned_*` so the two can never be confused.
CREATE OR REPLACE VIEW stg_activity_fund AS
SELECT
    f.*,
    f.fund_tied_general   + f.fund_tied_sc   + f.fund_tied_st    AS fund_tied_total,
    f.fund_untied_general + f.fund_untied_sc + f.fund_untied_st  AS fund_untied_total,
    f.fund_tied_abandoned_general   + f.fund_tied_abandoned_sc   + f.fund_tied_abandoned_st
  + f.fund_untied_abandoned_general + f.fund_untied_abandoned_sc + f.fund_untied_abandoned_st
                                                                 AS fund_abandoned_total,
    COALESCE(fs.description, 'Code ' || f.fund_scheme_code)      AS planned_fund_scheme_name,
    COALESCE(fc.description, 'Code ' || f.fund_component_code)   AS planned_fund_component_name
FROM activity_fund f
LEFT JOIN stg_dim_code fs ON fs.variable = 'fund_scheme_code'
                         AND fs.code     = CAST(f.fund_scheme_code AS VARCHAR)
LEFT JOIN stg_dim_code fc ON fc.variable = 'fund_component_code'
                         AND fc.code     = CAST(f.fund_component_code AS VARCHAR);


-- Asset labels, decoded with v_asset's double cast
-- (CAST(CAST(x AS BIGINT) AS VARCHAR)) — the source codes carry a decimal
-- suffix that the inner BIGINT cast strips before the VARCHAR join.
CREATE OR REPLACE VIEW stg_activity_asset AS
SELECT aa.*,
       COALESCE(ac.description,  'Uncategorised') AS asset_category_label,
       COALESCE(ast.description, 'Unknown')       AS asset_type_label
FROM activity_asset aa
LEFT JOIN stg_dim_code ac  ON ac.variable  = 'asset_category'
                          AND ac.code      = CAST(CAST(aa.asset_category AS BIGINT) AS VARCHAR)
LEFT JOIN stg_dim_code ast ON ast.variable = 'asset_type'
                          AND ast.code     = CAST(CAST(aa.asset_type AS BIGINT) AS VARCHAR);


-- Sparse candidate dimensions (§9.7): decoded here and carried into view1 so
-- the statewide switch is a config change, not a pack change (§6). Neither
-- dim_code variable carries any description on this drop, so both labels are
-- currently 'Code N' throughout.
CREATE OR REPLACE VIEW stg_activity_training AS
SELECT t.*,
       COALESCE(tc.description, 'Code ' || t.training_category_code)  AS training_category_label,
       COALESCE(tg.description, 'Code ' || t.training_organiser_code) AS training_organiser_label
FROM activity_training t
LEFT JOIN stg_dim_code tc ON tc.variable = 'training_category_code'
                         AND tc.code     = CAST(t.training_category_code AS VARCHAR)
LEFT JOIN stg_dim_code tg ON tg.variable = 'training_organiser_code'
                         AND tg.code     = CAST(t.training_organiser_code AS VARCHAR);


CREATE OR REPLACE VIEW stg_activity_community_service AS
SELECT c.*,
       COALESCE(cs.description, 'Code ' || c.community_service_code) AS community_service_label
FROM activity_community_service c
LEFT JOIN stg_dim_code cs ON cs.variable = 'community_service_code'
                         AND cs.code     = CAST(c.community_service_code AS VARCHAR);


-- Staged, feeds nothing: every analytical column is null (§7). Present so the
-- crosswalk can record the fact rather than the table's silent absence.
CREATE OR REPLACE VIEW stg_activity_delegation AS SELECT * FROM activity_delegation;

-- Zero rows — the evidence for "no equity view in v1" (§4.4).
CREATE OR REPLACE VIEW stg_activity_nsap AS SELECT * FROM activity_nsap;

-- Geotagged evidence uploads. Coordinates are X-id (Ask's v_progress serves
-- them); Discover only ever counts the uploads.
CREATE OR REPLACE VIEW stg_physical_progress AS SELECT * FROM physical_progress;


-- #############################################################################
-- 2. The three create_views.sql building blocks, re-expressed
-- #############################################################################

-- v_exp, verbatim. Six activity_codes have duplicate activity_expenditure rows;
-- aggregating here keeps every downstream join strictly 1:1. The twenty
-- activity_codes with no planned_activity parent (§8) survive this rollup and
-- are dropped by view1's join to the activity grain — see the WP-D1 report for
-- the measured amount that departs with them.
CREATE OR REPLACE VIEW stg_exp_rollup AS
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
FROM stg_activity_expenditure
GROUP BY activity_code;


-- v_approval, verbatim: one row per administratively approved activity, with
-- the technical approval alongside, the scheme rollup, and the tied/untied
-- component. Six activity_codes have two admin_approval_scheme rows; the ARG_MAX
-- pair takes the largest-value row so the join stays 1:1, and `scheme_rows`
-- carries the count so the collapse is visible in the output rather than silent.
--
-- Projection note (not a semantic change): authority_raw, tec_approval_authority,
-- adm_approval_no and tec_approval_order_no are v_approval columns that §7 roles
-- X-id / excluded-free-text. They are not selected here, so no view can leak them.
CREATE OR REPLACE VIEW stg_approval AS
WITH sch AS (
    SELECT activity_code,
           SUM(COALESCE(fund_sanctioned_general,0)) AS fund_sanctioned_general,
           SUM(COALESCE(fund_sanctioned_sc,0))      AS fund_sanctioned_sc,
           SUM(COALESCE(fund_sanctioned_st,0))      AS fund_sanctioned_st,
           SUM(COALESCE(fund_sanctioned_total,0))   AS fund_sanctioned_total,
           COUNT(*)                                 AS scheme_rows,
           ARG_MAX(scheme_code,           COALESCE(fund_sanctioned_total,0)) AS scheme_code,
           ARG_MAX(scheme_component_code, COALESCE(fund_sanctioned_total,0)) AS scheme_component_code
    FROM stg_admin_approval_scheme
    GROUP BY activity_code)
SELECT
    aa.activity_code,
    aa.gp_lgd_code,
    aa.fiscal_year,
    aa.sanction_day,
    aa.sanction_month_start,
    aa.sanction_quarter,
    aa.work_proposed_cost,
    aa.authority_clean,
    ta.tec_approval_required,
    ta.tec_approval_cost,
    ta.tec_approval_order_date,
    CASE WHEN ta.activity_code IS NOT NULL THEN 1 ELSE 0 END AS has_technical_approval,
    sch.fund_sanctioned_general,
    sch.fund_sanctioned_sc,
    sch.fund_sanctioned_st,
    sch.fund_sanctioned_total,
    sch.scheme_rows,
    COALESCE(fs.description, 'Code ' || sch.scheme_code)           AS sanctioned_scheme_name,
    COALESCE(fc.description, 'Code ' || sch.scheme_component_code) AS fund_component_name,
    -- Coarse tied / untied classification. 4249 = Tied Grant, 4211 = Basic
    -- Grant (untied), 4250 = Devolution of Fund (untied). Everything else is
    -- reported as 'Other' rather than guessed at.
    CASE sch.scheme_component_code
      WHEN '4249' THEN 'Tied'
      WHEN '4211' THEN 'Untied'
      WHEN '4250' THEN 'Untied'
      ELSE 'Other'
    END AS tied_untied
FROM stg_admin_approval aa
LEFT JOIN stg_technical_approval ta ON ta.activity_code = aa.activity_code
LEFT JOIN sch                       ON sch.activity_code = aa.activity_code
LEFT JOIN stg_dim_code fs ON fs.variable = 'fund_scheme_code'
                         AND fs.code     = sch.scheme_code
LEFT JOIN stg_dim_code fc ON fc.variable = 'fund_component_code'
                         AND fc.code     = sch.scheme_component_code;


-- The evidence-upload subquery v_activity inlines.
CREATE OR REPLACE VIEW stg_progress_rollup AS
SELECT activity_code, COUNT(*) AS evidence_uploads
FROM stg_physical_progress
GROUP BY activity_code;


-- #############################################################################
-- 3. Derived spines — no literal ever appears in these
-- #############################################################################

-- view2's month calendar, DERIVED from the cashbook: every month from the month
-- of the first voucher to the month of the last, inclusive. On this drop that
-- is 2020-04 .. 2026-03 = 72 months. Deriving rather than hardcoding is what
-- makes the pack reproducible AND what structurally excludes the phantom-FY
-- orphan links (§8.1): their dates start 2026-04, past the cashbook's last
-- month, so no calendar row exists for them to attach to.
CREATE OR REPLACE VIEW stg_month_calendar AS
SELECT CAST(m AS DATE) AS month_start
FROM range(
        (SELECT CAST(DATE_TRUNC('month', MIN(date)) AS TIMESTAMP) FROM stg_voucher),
        (SELECT CAST(DATE_TRUNC('month', MAX(date)) AS TIMESTAMP) FROM stg_voucher)
            + INTERVAL 1 MONTH,
        INTERVAL 1 MONTH
     ) t(m);


-- view3's fiscal-year domain: the years actually observed in the planning,
-- plan and cashbook tables. activity_voucher is deliberately NOT in the union —
-- it is the only table carrying '2026-2027', on 488 orphan rows with no
-- voucher (§8.1, §5.3). Excluding the source rather than filtering a literal
-- keeps the exclusion true when statewide data arrives.
CREATE OR REPLACE VIEW stg_fiscal_year_domain AS
SELECT fiscal_year FROM (
    SELECT DISTINCT fiscal_year FROM stg_planned_activity
    UNION
    SELECT DISTINCT fiscal_year FROM stg_plan
    UNION
    SELECT DISTINCT fiscal_year FROM stg_voucher
) d
WHERE fiscal_year IS NOT NULL;

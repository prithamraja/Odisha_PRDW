"""
Family descriptions for the re-ranker's "↳" line.

The re-ranker shows each candidate as

    EXP-001: What is the total actual expenditure incurred by {gp_name} in {date_range}?
        ↳ <desc>
        accepts filters: date_range, district_name, block_name, gp_name

and its system prompt tells the model to judge a candidate by the ↳ description
rather than by surface word overlap. This module supplies those descriptions.

WHAT A FAMILY IS HERE
    A maximal set of templates with IDENTICAL SQL and identical slots — the only
    grouping under which the contract "siblings repeat one description
    word-for-word" is true rather than merely tidy, because those members
    execute the same statement and the reranker's choice between them cannot
    change the answer. 14 such groups cover 33 of the 346 ids; the workbook's
    own scope variants are most of them (PLN-025 "in {GP}", PLN-027 "in
    {Block}", PLN-029 "in {District}" are one query once D2 makes geography
    optional). The other 313 templates are each their own family.

    That is a deliberate departure from the AP catalogue, where descriptions
    covered large families. The AP lesson — per-variant descriptions caused
    confusion, not precision — is about PARAMETER variants, which the
    "accepts filters:" line already separates. It does not transfer to this
    catalogue: SBM-SWM-002 (community compost pits) and SBM-SWM-007 (household
    compost pits) accept identical filters and differ only in a keyword regex
    frozen inside the SQL, so one shared description would leave the model
    choosing between them blind.

WHAT A DESCRIPTION SAYS, and why it is generated
    Descriptions are BUILT FROM THE SQL by tools/build_catalog.py, because what
    the reranker is missing is exactly what the SQL knows and the question text
    does not:

      1. the measure AND its accounting basis — the data dictionary's central
         trap is that this database holds two expenditure conventions, plan
         basis (activity_expenditure) and cash basis (the voucher cashbook), and
         an answer that does not say which is a wrong answer;
      2. the row grain — one row per GP, per theme, or a single total;
      3. the status filter — "only WORK COMPLETED", "only activities with an
         administrative approval", "only those with no expenditure recorded";
      4. for the 85 SBM families, WHICH KEYWORDS define the concept, since
         nothing in the database codes SBM activity types and every one of those
         questions is a text search;
      5. the scope behaviour — one entry answers state-wide or narrowed.

    Hand-written prose would be a less accurate way of saying the same things
    and would drift from the SQL at the first re-ratification. The hand-authored
    half is `_DISAMBIGUATION` in the builder: the near-miss warnings no amount of
    SQL parsing can infer ("uploaded a GPDP is any plan row, not the approved
    subset").

CONTRACT (mirrors _RERANK_SYS in reranker.py — do not break it)
    - ONE line, no newlines: the candidate listing is line-oriented.
    - Every template has a non-empty description, and no template appears in two
      families. tests/test_rerank_context.py enforces both.
"""
# ── GENERATED FILE — do not edit by hand ─────────────────────────────────────
# Built from AI_Chatbot_Questions.xlsx by tools/build_catalog.py.
# To change a question, a caveat or a SQL string, change the WORKBOOK and
# regenerate; `python tools/build_catalog.py --check` fails if this file and the
# workbook have drifted apart.


FAMILY_DESCRIPTIONS: dict[str, dict] = {

    'alr_001__financial_exceptions': {
        "desc": "LISTS: Which administratively approved activities in a given block still have zero expenditure a given threshold days after sanction. Returns activity_name, sanction_day, sanction_authority, admin_approved_cost, total_expenditure, days_since_sanction. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). Restricted to activities with no expenditure recorded. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Unblocked by the sanction date.",
        "members": ['ALR-001'],
    },

    'alr_002__financial_exceptions': {
        "desc": "LISTS: Which activities in a given district have expenditure exceeding their administratively approved cost in a given year. Returns activity_name, admin_approved_cost, total_expenditure, overrun_amount, overrun_pct. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['ALR-002'],
    },

    'alr_003__financial_exceptions': {
        "desc": "LISTS: Which activities in a given block have expenditure more than a given threshold percent above estimated cost in a given year. Returns activity_name, estimated_cost, total_expenditure, overrun_pct. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['ALR-003'],
    },

    'alr_004__financial_exceptions': {
        "desc": "LISTS: Which activities in a given district have a technically approved cost higher than the administratively approved cost in a given year. Returns activity_name, technical_approved_cost, admin_approved_cost, difference. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['ALR-004'],
    },

    'alr_005__financial_exceptions': {
        "desc": "LISTS: Which abandoned activities in a given district had expenditure incurred, and how much in a given year. Returns activity_name, admin_approved_cost, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work abandoned. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no abandonment date, so 'before abandonment' cannot be tested;.",
        "members": ['ALR-005'],
    },

    'alr_008__progress_exceptions': {
        "desc": "LISTS: Which activities approved more than a given threshold days ago in a given block are still not started. Returns activity_name, sanction_day, sanction_authority, status_label, admin_approved_cost, total_expenditure. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only activities not yet started. Restricted to activities that have an administrative approval (17% of them). admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Unblocked by the sanction date.",
        "members": ['ALR-008'],
    },

    'alr_009__progress_exceptions': {
        "desc": 'LISTS: Which GPs in a given block have an approved plan but no administratively approved activities in a given year. Returns approved_plans, admin_approved_activities, total_activities. One row per gp_name × block_name × district_name. Restricted to plans with an approval date. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope. Caveat: Administrative approval proxied by admin_approved_cost > 0.',
        "members": ['ALR-009'],
    },

    'alr_011__progress_exceptions': {
        "desc": 'RANKS: Which blocks in a given district are below a given threshold percent activity completion in a given year. Returns activities, completed, started, completion_rate_pct. One row per block_name × district_name. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no mid-year cut-off in the data, so the whole year is measured.',
        "members": ['ALR-011'],
    },

    'alr_012__inactivity': {
        "desc": "LISTS: Which GPs in a given block recorded no activity in a given year. Returns (SELECT COUNT(*). One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Reads the CASHBOOK (v_voucher) — cash basis, a different convention from the plan-basis expenditure questions. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Last N days' cannot be evaluated - activities carry no dates.",
        "members": ['ALR-012'],
    },

    'alr_013__inactivity': {
        "desc": 'LISTS: Which GPs in a given district have no data entry for a given year in any module. Returns *. One row per matching record. Reads the CASHBOOK (v_voucher) — cash basis, a different convention from the plan-basis expenditure questions. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope. Caveat: Checks the three modules that hold GP-level data: plan, activities and vouchers.',
        "members": ['ALR-013'],
    },

    'ast_001__asset_creation': {
        "desc": 'COUNTS: How many assets were created in a given gram panchayat during a given year. Returns asset_rows, asset_creating_activities, categorised_assets. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286;.',
        "members": ['AST-001'],
    },

    'ast_002__asset_creation': {
        "desc": 'COUNTS: What is the asset category-wise count of assets created in a given block for a given year. Returns asset_category_label, asset_rows, activities, expenditure. One row per asset_category_label. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286;.',
        "members": ['AST-002'],
    },

    'ast_003__asset_creation': {
        "desc": 'COUNTS: How many a given asset sub-category assets exist across a given district for a given year. Returns asset_subcategory_label, asset_rows, gps, expenditure. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286;.',
        "members": ['AST-003'],
    },

    'ast_006__asset_creation': {
        "desc": 'COUNTS: How many immovable-type assets were created in a given block during a given year. Returns asset_type_label, asset_rows, activities. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: asset_type decodes to movable / Immovable but is populated on only a small share of rows;.',
        "members": ['AST-006'],
    },

    'ast_007__asset_creation': {
        "desc": "RANKS: Which asset category received the highest expenditure in a given district for a given year. Returns asset_category_label, asset_rows, expenditure. One row per asset_category_label. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286;.",
        "members": ['AST-007'],
    },

    'ast_008__asset_creation': {
        "desc": 'COUNTS: How many assets were created under a given LSDG theme in a given block for a given year. Returns theme, asset_rows, activities, expenditure. One row per theme. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.',
        "members": ['AST-008'],
    },

    'ast_009__asset_creation': {
        "desc": "LISTS: Which GPs in a given block created no assets in a given year. Returns gp_name, block_name, district_name. One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Created no assets' means no categorised asset row.",
        "members": ['AST-009'],
    },

    'ast_012__asset_creation': {
        "desc": 'The YEAR-BY-YEAR trend of: How has the number of assets created per year in a given block changed. Returns asset_rows, categorised_assets, activities, expenditure. One row per fiscal_year. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286;.',
        "members": ['AST-012'],
    },

    'bud_001__budgeting': {
        "desc": 'TOTALS: How much total funding is recorded for a given gram panchayat in a given year. Returns activities, plan_cost, approved_cost_action_plan, admin_approved_cost, actual_expenditure. One row per gp_name × block_name × fiscal_year. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no funds-available/receipts table at GP level tied to the plan.',
        "members": ['BUD-001'],
    },

    'bud_002__budgeting': {
        "desc": 'TOTALS: How much funding is recorded from each funding source in a given year. Returns funding_source, activities, amount, pct_of_total. One row per funding_source. amount is CASHBOOK voucher amounts (cash basis), which is a different convention from the plan-basis expenditure most questions use. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Funding source is proxied by activity_expenditure.scheme_name, which has only 5 non-null values and is NULL on 82% of rows.',
        "members": ['BUD-002'],
    },

    'bud_003__budgeting': {
        "desc": 'TOTALS: How much funding is sanctioned under tied and untied components in a given year. Returns tied_untied, activities, general_amount, sc_amount, st_amount, sanctioned_amount. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied).',
        "members": ['BUD-003'],
    },

    'bud_004__budgeting': {
        "desc": 'The PERCENTAGE for: What percentage of the total comes from each funding source in a given year. Returns funding_source, amount, pct_of_total. One row per funding_source. amount is CASHBOOK voucher amounts (cash basis), which is a different convention from the plan-basis expenditure most questions use. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Same scheme_name coverage caveat as BUD-002.',
        "members": ['BUD-004'],
    },

    'bud_005__budgeting': {
        "desc": 'The PERCENTAGE for: What percentage of the sanctioned budget is tied and untied in a given year. Returns tied_untied, sanctioned_amount, pct_of_sanctioned. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied).',
        "members": ['BUD-005'],
    },

    'bud_006__budgeting': {
        "desc": 'TOTALS: How much planned expenditure is allocated to each GPDP theme in a given year. Returns theme, activities, planned_cost, approved_cost, actual_expenditure. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.',
        "members": ['BUD-006', 'BUD-013'],
    },

    'bud_007__budgeting': {
        "desc": "RANKS: Which GPDP theme has the highest planned expenditure in a given year. Returns theme, planned_cost, activities. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['BUD-007'],
    },

    'bud_008__budgeting': {
        "desc": "RANKS: Which GPDP theme has the lowest planned expenditure in a given year. Returns theme, planned_cost, activities. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['BUD-008'],
    },

    'bud_009__budgeting': {
        "desc": 'The PERCENTAGE for: What percentage of total planned expenditure is allocated to each GPDP theme in a given year. Returns theme, planned_cost, pct_of_planned_cost. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.',
        "members": ['BUD-009'],
    },

    'bud_010__budgeting': {
        "desc": "RANKS: Which GPDP themes have high planned expenditure but relatively few activities in a given year. Returns theme, activities, planned_cost, cost_per_activity, pct_of_activities, pct_of_cost. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are not defined in the source question, so the query ranks by cost per activity and shows both share columns.",
        "members": ['BUD-010'],
    },

    'bud_011__budgeting': {
        "desc": "RANKS: Which GPDP themes have many activities but relatively low planned expenditure in a given year. Returns theme, activities, planned_cost, cost_per_activity, pct_of_activities, pct_of_cost. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are not defined in the source question, so the query ranks by cost per activity and shows both share columns.",
        "members": ['BUD-011'],
    },

    'bud_012__budgeting': {
        "desc": 'LISTS: Which GPDP themes have no planned expenditure in a given year. Returns theme, activities, planned_cost. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Only themes that appear in the plan are considered;.',
        "members": ['BUD-012'],
    },

    'bud_014__budgeting': {
        "desc": 'The YEAR-BY-YEAR trend of: How has planned expenditure under each GPDP theme changed over the years. Returns theme, activities, planned_cost, actual_expenditure. One row per theme × fiscal_year. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.',
        "members": ['BUD-014', 'BUD-017'],
    },

    'bud_018__budgeting': {
        "desc": 'TOTALS: How much planned expenditure is allocated to each focus area in a given year. Returns focus_area_name, activities, planned_cost, actual_expenditure. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['BUD-018'],
    },

    'bud_019__budgeting': {
        "desc": 'COUNTS: How many activities under a given focus area have planned expenditure greater than zero in a given year. Returns focus_area_name, total_activities, activities_with_planned_cost, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['BUD-019'],
    },

    'bud_020__budgeting': {
        "desc": "LISTS: What are the activities with expenditure under a given focus area in a given year. Returns activity_name, planned_cost, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['BUD-020'],
    },

    'bud_021__budgeting': {
        "desc": "LISTS: What are the activities with zero expenditure under a given focus area in a given year. Returns activity_name, planned_cost, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities with no expenditure recorded. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['BUD-021'],
    },

    'bud_022__budgeting': {
        "desc": "RANKS: Which focus area has the highest planned expenditure in a given year. Returns focus_area_name, planned_cost, activities. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['BUD-022'],
    },

    'bud_023__budgeting': {
        "desc": "RANKS: Which focus area has the lowest planned expenditure in a given year. Returns focus_area_name, planned_cost, activities. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['BUD-023'],
    },

    'bud_024__budgeting': {
        "desc": 'The PERCENTAGE for: What percentage of total planned expenditure is allocated to each focus area in a given year. Returns focus_area_name, planned_cost, pct_of_planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['BUD-024'],
    },

    'bud_025__budgeting': {
        "desc": "RANKS: Which focus areas receive high planned expenditure but relatively few activities in a given year. Returns focus_area_name, activities, planned_cost, cost_per_activity, pct_of_activities, pct_of_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are undefined;.",
        "members": ['BUD-025'],
    },

    'bud_026__budgeting': {
        "desc": "RANKS: Which focus areas receive many activities but relatively low planned expenditure in a given year. Returns focus_area_name, activities, planned_cost, cost_per_activity, pct_of_activities, pct_of_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are undefined;.",
        "members": ['BUD-026'],
    },

    'bud_027__budgeting': {
        "desc": 'LISTS: Which focus areas receive no planned expenditure in a given year. Returns focus_area_name, activities, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['BUD-027'],
    },

    'dqy_001__missing_fields': {
        "desc": 'COUNTS: How many activities in a given district have no focus area recorded for a given year. Returns total_activities, undecoded_focus_area, missing_focus_area, pct_unusable. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. A DATA-QUALITY check on how much of the data decodes at all, not a programme measure. Do not answer a coverage or spend question with it. Caveat: Separates genuinely missing focus areas from codes that exist but are not in the decoder.',
        "members": ['DQY-001'],
    },

    'dqy_002__missing_fields': {
        "desc": "LISTS: Which asset-creating activities in a given block have no asset details recorded in a given year. Returns activity_name, asset_category_label, asset_subcategory_label, total_expenditure. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: This is the single biggest data-quality gap: asset detail is missing on roughly two-thirds of asset rows.",
        "members": ['DQY-002'],
    },

    'dqy_003__missing_fields': {
        "desc": "LISTS: Which administratively approved activities in a given block have a missing sanction order date or authority in a given year. Returns activity_name, adm_approval_no, sanction_day, sanction_authority_raw, tec_approval_order_no, tec_approval_order_date. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Unblocked by the new approval tables.",
        "members": ['DQY-003'],
    },

    'dqy_004__missing_fields': {
        "desc": 'COUNTS: How many activities in a given district have no funding scheme recorded for a given year. Returns total_activities, missing_scheme, pct_missing_scheme. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['DQY-004'],
    },

    'dqy_006__inconsistencies': {
        "desc": "LISTS: Which activities in a given block are marked completed or ongoing but have no progress evidence in a given year. Returns activity_name, status_label, evidence_uploads, admin_approved_cost, total_expenditure. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Rewritten: the original compared status against asset stages, which do not exist.",
        "members": ['DQY-006'],
    },

    'dqy_007__inconsistencies': {
        "desc": "LISTS: Which activities in a given district have a zero or negative estimated cost recorded in a given year. Returns activity_name, total_cost, approved_cost_action_plan, total_expenditure, is_costless_activity, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Activities flagged is_costless_activity = 1 are excluded, since a zero cost is legitimate for those.",
        "members": ['DQY-007'],
    },

    'dqy_008__inconsistencies': {
        "desc": "LISTS: Which activities within a given gram panchayat share identical descriptions in a given year. Returns activity_name, duplicate_count, activity_codes, combined_planned_cost. One row per gp_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Exact string match on activity_name within one GP and year.",
        "members": ['DQY-008'],
    },

    'dqy_009__inconsistencies': {
        "desc": "LISTS: For which activities in a given block does the sanctioned scheme funding not equal the approved cost in a given year. Returns activity_name, scheme_allocation_rows, fund_sanctioned_total, admin_approved_cost, work_proposed_cost, difference. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). fund_sanctioned_total is funds sanctioned under the approval's scheme components. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Unblocked by admin_approval_scheme.",
        "members": ['DQY-009'],
    },

    'dqy_010__inconsistencies': {
        "desc": 'LISTS: Which GPs in a given district show all-zero values in the physical-financial comparison for a given year. Returns activities, planned_cost, approved_cost, expenditure, started. One row per gp_name × block_name × district_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['DQY-010'],
    },

    'dqy_011__inconsistencies': {
        "desc": "LISTS: Which activities in a given block report expenditure but have no payment vouchers in a given year. Returns activity_name, total_expenditure, vouchers, voucher_total. One row per activity_code × gp_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Verified clean: all 1,911 activities with expenditure above zero have at least one linked voucher, so this query correctly returns no rows in every year.",
        "members": ['DQY-011'],
    },

    'dss_001__prioritisation': {
        "desc": "RANKS: Which focus areas in a given gram panchayat have high approved cost but completion below a given threshold percent in a given year. Returns focus_area_name, activities, approved_cost, expenditure, completed, completion_rate_pct. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Only 17 activities database-wide are complete, so almost every focus area falls below any threshold.",
        "members": ['DSS-001'],
    },

    'dss_002__prioritisation': {
        "desc": "RANKS: Which blocks in a given district combine high pending sanctions with low expenditure in a given year. Returns activities, pending_sanctions, pct_pending, planned_cost, expenditure, pct_utilised. One row per block_name × district_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are undefined;.",
        "members": ['DSS-002'],
    },

    'dss_003__prioritisation': {
        "desc": "RANKS: Which asset sub-categories in a given block show the highest repeat-maintenance frequency in a given year. Returns asset_subcategory_label, maintenance_activities, years_with_maintenance, total_asset_rows, maintenance_expenditure. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Pooled across all years because a single year cannot show repeat maintenance.",
        "members": ['DSS-003'],
    },

    'dss_005__prioritisation': {
        "desc": "LISTS: Which ongoing activities in a given block have spent less than a given threshold percent of their sanctioned cost in a given year. Returns activity_name, admin_approved_cost, total_expenditure, pct_of_sanction_spent, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work ongoing. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no date on activities, so 'with one quarter left' cannot be evaluated;.",
        "members": ['DSS-005'],
    },

    'dss_006__prioritisation': {
        "desc": "RANKS: Which GPs in a given block have the largest unspent balance in a given year. Returns activities, approved_cost, expenditure, unspent_balance, pct_utilised. One row per gp_name × block_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no resource-envelope table, so 'unprogrammed envelope balance' is approximated by approved plan cost minus actual expenditure.",
        "members": ['DSS-006'],
    },

    'exp_001__expenditure': {
        "desc": 'TOTALS: What is the total actual expenditure incurred by a given gram panchayat in a given year. Returns activities, total_expenditure. One row per gp_name × block_name × fiscal_year. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. TOTAL SPEND on the plan basis. The cashbook questions read v_voucher and answer a different accounting convention; never substitute one for the other.',
        "members": ['EXP-001'],
    },

    'exp_002__expenditure': {
        "desc": 'The YEAR-BY-YEAR trend of: How has the total actual expenditure of a given gram panchayat changed over the years. Returns activities, planned_cost, actual_expenditure, pct_utilised. One row per fiscal_year. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Six years are present: 2020-2021 to 2025-2026.',
        "members": ['EXP-002'],
    },

    'exp_003__expenditure': {
        "desc": 'The PERCENTAGE for: What percentage of the planned expenditure has been utilised in a given year. Returns planned_cost, actual_expenditure, pct_utilised. A single summary row. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['EXP-003'],
    },

    'exp_004__expenditure': {
        "desc": "TOTALS: What is the total unspent amount (planned minus actual) in a given year. Returns planned_cost, actual_expenditure, unspent_amount, pct_unspent. A single summary row. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Unspent' here is plan versus spend, not a cash balance - there is no opening/closing balance table.",
        "members": ['EXP-004'],
    },

    'exp_005__expenditure': {
        "desc": 'COUNTS: How many planned activities have recorded actual expenditure in a given year. Returns total_activities, activities_with_expenditure, pct_with_expenditure. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['EXP-005'],
    },

    'exp_006__expenditure': {
        "desc": 'TOTALS: How much actual expenditure has been incurred under each funding source in a given year. Returns funding_source, activities, expenditure, pct_of_expenditure. One row per funding_source. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Funding source is proxied by scheme_name (5 non-null values, NULL on 82% of rows).',
        "members": ['EXP-006', 'EXP-007'],
    },

    'exp_008__expenditure': {
        "desc": 'TOTALS: How much actual expenditure has been incurred under tied and untied funds in a given year. Returns tied_untied, activities, sanctioned_amount, actual_expenditure, pct_utilised. Restricted to activities that have an administrative approval (17% of them). actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Expenditure can only be split tied/untied for sanctioned activities.',
        "members": ['EXP-008'],
    },

    'exp_009__expenditure': {
        "desc": 'TOTALS: How much tied-fund expenditure was incurred under a given focus area in a given year. Returns focus_area_name, tied_untied, activities, sanctioned_amount, actual_expenditure. One row per focus_area_name. Restricted to activities that have an administrative approval (17% of them). actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Pass $focus_area = NULL to see every focus area.',
        "members": ['EXP-009', 'EXP-011'],
    },

    'exp_010__expenditure': {
        "desc": 'COUNTS: How many activities have expenditure under a given focus area in a given year. Returns focus_area_name, activities, activities_with_expenditure, expenditure. One row per focus_area_name. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['EXP-010'],
    },

    'exp_012__expenditure': {
        "desc": "RANKS: Which funding source has the highest utilisation in a given year. Returns funding_source, planned_cost, expenditure, unspent_amount, pct_utilised. One row per funding_source. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Funding source proxied by scheme_name.",
        "members": ['EXP-012'],
    },

    'exp_013__expenditure': {
        "desc": "RANKS: Which funding source has the largest unspent amount in a given year. Returns funding_source, planned_cost, expenditure, unspent_amount, pct_utilised. One row per funding_source. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Funding source proxied by scheme_name.",
        "members": ['EXP-013'],
    },

    'exp_014__expenditure': {
        "desc": 'TOTALS: What is the total actual expenditure under each GPDP theme in a given year. Returns theme, activities, planned_cost, actual_expenditure. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.',
        "members": ['EXP-014'],
    },

    'exp_015__expenditure': {
        "desc": "RANKS: Which GPDP theme has the highest actual expenditure in a given year. Returns theme, actual_expenditure, activities. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['EXP-015'],
    },

    'exp_016__expenditure': {
        "desc": "RANKS: Which GPDP theme has the lowest actual expenditure in a given year. Returns theme, actual_expenditure, activities. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['EXP-016'],
    },

    'exp_017__expenditure': {
        "desc": 'The PERCENTAGE for: What percentage of total actual expenditure goes to each GPDP theme in a given year. Returns theme, actual_expenditure, pct_of_expenditure. One row per theme. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.',
        "members": ['EXP-017'],
    },

    'exp_018__expenditure': {
        "desc": "RANKS: Which GPDP themes have the highest expenditure utilisation in a given year. Returns theme, planned_cost, actual_expenditure, pct_utilised. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['EXP-018'],
    },

    'exp_019__expenditure': {
        "desc": "RANKS: Which GPDP themes have the largest gap between planned and actual expenditure in a given year. Returns theme, planned_cost, actual_expenditure, gap_amount, gap_pct. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['EXP-019'],
    },

    'exp_020__expenditure': {
        "desc": "RANKS: Which theme has the highest utilisation of 15th CFC funds at Block level in a given year. Returns theme, funding_source, planned_cost, actual_expenditure, pct_utilised. One row per theme × funding_source. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Pass $scheme = 'XV Finance Commission' for CFC or '5TH STATE FINANCE COMMISSION' for SFC.",
        "members": ['EXP-020', 'EXP-021', 'EXP-022'],
    },

    'exp_023__expenditure': {
        "desc": 'The PERCENTAGE for: What percentage of sanctioned funds was utilised in a given year. Returns admin_sanctioned, actual_expenditure, pct_of_sanctioned_utilised. A single summary row. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: admin_approved_cost is populated on only 2,247 of 12,730 expenditure rows, so the denominator is incomplete.',
        "members": ['EXP-023'],
    },

    'exp_024__expenditure': {
        "desc": 'TOTALS: What are the receipts, payments and closing balance for a given gram panchayat in a given year. Returns receipts, payments, closing_balance, pct_utilised. One row per gp_name × block_name × fiscal_year. pct_utilised is utilisation as a percentage of the approved cost. Reads the CASHBOOK (v_voucher) — cash basis, a different convention from the plan-basis expenditure questions. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Derived from the voucher cashbook.',
        "members": ['EXP-024'],
    },

    'exp_025__expenditure': {
        "desc": 'TOTALS: What is the total actual expenditure under each focus area in a given year. Returns focus_area_name, activities, planned_cost, actual_expenditure. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['EXP-025'],
    },

    'exp_026__expenditure': {
        "desc": 'COUNTS: How many activities have expenditure under a given focus area in a given year. Returns focus_area_name, activities_with_expenditure, total_activities, expenditure. One row per focus_area_name. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Duplicate of EXP-010 in the source list.',
        "members": ['EXP-026', 'EXP-030'],
    },

    'exp_027__expenditure': {
        "desc": "LISTS: List the activities with expenditure under a given focus area in a given year. Returns activity_name, focus_area_name, approved_cost_action_plan, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['EXP-027'],
    },

    'exp_028__expenditure': {
        "desc": "RANKS: Which focus area has the highest actual expenditure in a given year. Returns focus_area_name, actual_expenditure, activities. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Set the geography parameters to choose the GP, Block or District level.",
        "members": ['EXP-028'],
    },

    'exp_029__expenditure': {
        "desc": "RANKS: Which focus area has the lowest actual expenditure in a given year. Returns focus_area_name, actual_expenditure, activities. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. actual_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Set the geography parameters to choose the GP, Block or District level.",
        "members": ['EXP-029'],
    },

    'exp_031__expenditure': {
        "desc": "RANKS: Which activities have the highest expenditure in a given year. Returns activity_name, focus_area_name, approved_cost_action_plan, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['EXP-031', 'EXP-032'],
    },

    'exp_033__expenditure': {
        "desc": "LISTS: Which high-value activities (planned cost above a given amount) have no expenditure in a given year. Returns activity_name, approved_cost_action_plan, total_cost, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities with no expenditure recorded. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High-value' was undefined in the source question, so it is now the $amount_threshold parameter.",
        "members": ['EXP-033'],
    },

    'exp_034__expenditure': {
        "desc": "LISTS: Which activities have actual expenditure equal to the planned expenditure in a given gram panchayat in a given year. Returns activity_name, planned_cost, total_expenditure, variance, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['EXP-034'],
    },

    'exp_035__expenditure': {
        "desc": "LISTS: Which activities have actual expenditure exceeding the planned expenditure in a given gram panchayat in a given year. Returns activity_name, planned_cost, total_expenditure, variance, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['EXP-035'],
    },

    'exp_036__expenditure': {
        "desc": "TOTALS: How much expenditure went on creation of new assets in a given gram panchayat in a given year. Returns work_type_label, activities, planned_cost, actual_expenditure. One row per work_type_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Uses work_type = 'New/Fresh'.",
        "members": ['EXP-036'],
    },

    'exp_037__expenditure': {
        "desc": "TOTALS: How much expenditure went on repair and maintenance in a given gram panchayat in a given year. Returns work_type_label, activities, planned_cost, actual_expenditure. One row per work_type_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Uses work_type = 'Maintenance'.",
        "members": ['EXP-037'],
    },

    'exp_038__expenditure': {
        "desc": "TOTALS: How much expenditure went on administrative activities in a given year. Returns focus_area_name, activities, planned_cost, actual_expenditure. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Administrative' is interpreted as the focus areas 'Administrative & Technical Support' and 'GP Office Infrastructure';.",
        "members": ['EXP-038'],
    },

    'fnd_001__tied_untied_funds': {
        "desc": 'TOTALS: What is the split of tied and untied funds sanctioned to activities of a given gram panchayat in a given year. Returns tied_untied, fund_component_name, sanctioned_activities, sanctioned_amount, pct_of_sanctioned. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied).',
        "members": ['FND-001'],
    },

    'fnd_002__tied_untied_funds': {
        "desc": "RANKS: Which focus areas consume the largest share of tied funds in a given block in a given year. Returns focus_area_name, tied_activities, tied_amount, pct_of_tied_funds. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied).",
        "members": ['FND-002'],
    },

    'fnd_003__tied_untied_funds': {
        "desc": "COUNTS: How many activities in a given gram panchayat are funded entirely from untied funds in a given year. Returns untied_only_activities, tied_activities, other_component_activities, sanctioned_activities, untied_amount. A single summary row. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Entirely' is taken from the dominant component on the activity.",
        "members": ['FND-003'],
    },

    'fnd_004__tied_untied_funds': {
        "desc": 'The PERCENTAGE for: What percentage of sanctioned funds in a given district is tied in a given year. Returns total_sanctioned, tied_amount, untied_amount, other_amount, pct_tied. A single summary row. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied).',
        "members": ['FND-004'],
    },

    'fnd_005__category_funds': {
        "desc": 'TOTALS: How much of the sanctioned funding in a given block is earmarked for SC and ST categories in a given year. Returns sanctioned_activities, general_sanctioned, sc_sanctioned, st_sanctioned, total_sanctioned, pct_sc_st. A single summary row. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Now uses the real earmark columns from admin_approval_scheme rather than the spent split.',
        "members": ['FND-005'],
    },

    'fnd_006__category_funds': {
        "desc": 'COMPARES: How does the SC-category funding of a given gram panchayat compare with its total for a given year. Returns sc_targeted_activities, sc_amount, total_amount, pct_sc. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: No resource-envelope or allocation table exists in the database - only actual expenditure is recorded, so planned allocation cannot be compared against it.',
        "members": ['FND-006'],
    },

    'fnd_007__category_funds': {
        "desc": 'LISTS: Which GPs in a given block have sanctioned activities but no SC/ST earmark in a given year. Returns sanctioned_activities, total_sanctioned, sc_st_sanctioned. One row per gp_name × block_name × district_name. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Still no resource-envelope table, so this lists GPs with zero SC/ST earmark rather than GPs that had an envelope and did not use it.',
        "members": ['FND-007'],
    },

    'fnd_008__multi_scheme': {
        "desc": 'LISTS: Which activities in a given gram panchayat are funded from more than one scheme in a given year. Returns distinct_schemes, schemes, total_expenditure. One row per activity_code × gp_name × block_name. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Queries activity_expenditure directly (not v_activity) because the view collapses duplicate rows.',
        "members": ['FND-008'],
    },

    'fnd_009__multi_scheme': {
        "desc": "RANKS: Which scheme funds the largest number of activities in a given block in a given year. Returns scheme_name, activities, expenditure. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name is NULL on 82% of expenditure rows;.",
        "members": ['FND-009'],
    },

    'fnd_010__multi_scheme': {
        "desc": "TOTALS: What is the total amount recorded per scheme across a given district in a given year. Returns scheme_name, activities, approved_cost, expenditure, pct_of_expenditure. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Fund allocated' is not stored;.",
        "members": ['FND-010'],
    },

    'imp_001__implementation': {
        "desc": "COUNTS: How many planned activities have been initiated in a given gram panchayat in a given year. Returns planned_activities, initiated_activities, initiation_rate_pct. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Initiated' = status WORK ONGOING or WORK COMPLETED.",
        "members": ['IMP-001'],
    },

    'imp_002__implementation': {
        "desc": 'COUNTS: How many initiated activities have been completed in a given year. Returns initiated_activities, completed_activities, completion_rate_pct. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['IMP-002'],
    },

    'imp_003__implementation': {
        "desc": "COUNTS: How many planned activities have not yet been initiated in a given gram panchayat in a given year. Returns planned_activities, not_initiated, cost_not_initiated. A single summary row. Counts only activities not yet started. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Includes both 'Activity Approved' and 'UNDER APPROVAL' activities.",
        "members": ['IMP-003'],
    },

    'imp_004__implementation': {
        "desc": 'The PERCENTAGE for: What is the initiation rate under each theme and focus area in a given year. Returns theme, focus_area_name, planned_activities, initiation_count, initiation_rate_pct. One row per theme × focus_area_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['IMP-004'],
    },

    'imp_005__implementation': {
        "desc": 'The PERCENTAGE for: What is the completion rate under each theme and focus area in a given year. Returns theme, focus_area_name, planned_activities, completion_count, completion_rate_pct. One row per theme × focus_area_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['IMP-005'],
    },

    'imp_006__implementation': {
        "desc": "RANKS: Which themes have the highest number of completed activities in a given year. Returns theme, planned_activities, completed_activities, completion_rate_pct. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.",
        "members": ['IMP-006'],
    },

    'imp_007__implementation': {
        "desc": "RANKS: Which themes have the largest implementation gap (planned versus initiated) in a given year. Returns theme, planned_activities, initiated_activities, implementation_gap, gap_pct. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.",
        "members": ['IMP-007'],
    },

    'imp_008__implementation': {
        "desc": "RANKS: Which focus area has the highest number of completed activities in a given year. Returns focus_area_name, planned_activities, completed_activities. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.",
        "members": ['IMP-008'],
    },

    'imp_009__implementation': {
        "desc": "RANKS: Which focus area has the lowest completion rate in a given year. Returns focus_area_name, planned_activities, completed_activities, completion_rate_pct. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: $threshold sets a minimum activity count so focus areas with one or two activities do not dominate the ranking.",
        "members": ['IMP-009'],
    },

    'imp_010__implementation': {
        "desc": "RANKS: Which focus areas have the largest implementation gap (planned versus initiated) in a given year. Returns focus_area_name, planned_activities, initiated_activities, implementation_gap, gap_pct. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.",
        "members": ['IMP-010'],
    },

    'imp_011__implementation': {
        "desc": "RANKS: Which focus areas have the largest number of ongoing activities in a given year. Returns focus_area_name, ongoing_activities, planned_activities, expenditure_on_ongoing. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work ongoing. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['IMP-011'],
    },

    'imp_012__implementation': {
        "desc": "RANKS: Which themes receive funds but show poor implementation in a given year. Returns theme, planned_activities, expenditure, completed_activities, completion_rate_pct. One row per theme. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Poor implementation' is undefined in the source question;.",
        "members": ['IMP-012'],
    },

    'imp_013__implementation': {
        "desc": "LISTS: Which high-expenditure activities have not yet started in a given year. Returns activity_name, approved_cost_action_plan, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only activities not yet started. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High-expenditure' is now the $amount_threshold parameter.",
        "members": ['IMP-013'],
    },

    'imp_014__implementation': {
        "desc": "RANKS: Which themes have the greatest mismatch between planning and expenditure in a given year. Returns theme, activities, pct_of_activities, expenditure, pct_of_expenditure, share_gap_pts. One row per theme. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Mismatch is measured as the gap between a theme's share of activities and its share of spend.",
        "members": ['IMP-014'],
    },

    'imp_015__implementation': {
        "desc": "The YEAR-BY-YEAR trend of: Which GPDP themes consistently perform well in implementation across years. Returns theme, years_present, total_activities, started, completed, avg_initiation_rate_pct. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Consistently' is not defined in the source question;.",
        "members": ['IMP-015'],
    },

    'imp_016__implementation': {
        "desc": "The YEAR-BY-YEAR trend of: Which GPDP themes consistently underperform in implementation across years. Returns theme, years_present, total_activities, started, completed, avg_initiation_rate_pct. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Consistently' is not defined in the source question;.",
        "members": ['IMP-016'],
    },

    'imp_017__implementation': {
        "desc": "The YEAR-BY-YEAR trend of: Which types of activity remain incomplete across multiple years. Returns activity_name, years_appearing, occurrences, completed, planned_cost. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Groups on the exact activity_name string.",
        "members": ['IMP-017'],
    },

    'imp_018__implementation': {
        "desc": "LISTS: Which activities are marked Work Ongoing despite expenditure reaching the approved cost in a given year. Returns activity_name, approved_cost_action_plan, total_expenditure, pct_of_approved_spent, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work ongoing. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['IMP-018'],
    },

    'imp_019__implementation': {
        "desc": "RANKS: Which themes should be prioritised for implementation support in a given year. Returns theme, planned_activities, started, initiation_rate_pct, approved_cost, expenditure. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Advisory question with no defined rule.",
        "members": ['IMP-019'],
    },

    'imp_020__implementation': {
        "desc": "RANKS: Which focus areas should be prioritised for implementation support in a given year. Returns focus_area_name, planned_activities, started, initiation_rate_pct, approved_cost, expenditure. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Advisory question with no defined rule.",
        "members": ['IMP-020'],
    },

    'imp_021__implementation': {
        "desc": "LISTS: Which activities should be carried forward to the next GPDP because they are incomplete in a given year. Returns activity_name, focus_area_name, status_label, approved_cost_action_plan, total_expenditure, unspent_amount. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Should be carried forward' is a policy judgement;.",
        "members": ['IMP-021'],
    },

    'imp_022__implementation': {
        "desc": "RANKS: Which schemes have the highest number of delayed or incomplete activities in a given year. Returns scheme_name, activities, incomplete_activities, ongoing, abandoned, pct_incomplete. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: No planned end-date exists, so 'delayed' cannot be measured;.",
        "members": ['IMP-022'],
    },

    'phy_001__asset_stages': {
        "desc": "LOOKS UP: What physical-progress evidence has been recorded for activity a given activity. Returns activity_name, status_label, geotagged_uploads, file_upload_id). One row per matching record. Caveat: physical_progress holds geotagged photo uploads, not a stage model - there are no stage names or stage dates, so the original 'current stage of each asset' cannot be answered.",
        "members": ['PHY-001'],
    },

    'phy_003__asset_stages': {
        "desc": "COUNTS: How many assets in a given gram panchayat belong to completed activities in a given year. Returns asset_rows, assets_under_completed_activities. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no per-asset completion flag, so the parent activity's status is used instead.",
        "members": ['PHY-003'],
    },

    'phy_004__asset_stages': {
        "desc": "COUNTS: How many activities in a given block have physical-progress evidence recorded in a given year. Returns status_label, activities, with_evidence, total_uploads, pct_with_evidence. One row per status_label. Restricted to activities with geotagged progress evidence. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Rewritten from 'assets at each implementation stage' to 'activities with progress evidence', which is what physical_progress actually supports.",
        "members": ['PHY-004'],
    },

    'pln_001__planning': {
        "desc": 'COUNTS: How many Gram Panchayats in a given district/a given block have uploaded the GPDP in a given year. Returns gps_with_gpdp. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. UPLOADED a GPDP, which is any plan row — not the approved subset; the approval question is the neighbouring one. Caveat: A row in plan = an uploaded GPDP.',
        "members": ['PLN-001'],
    },

    'pln_002__planning': {
        "desc": "COUNTS: How many GPs in a given district/a given block have the GPDP approved in a given year. Returns gps_approved. A single summary row. Restricted to plans with an approval date. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. APPROVED plans specifically. Because plan_code_status is entirely NULL, approval is proxied by an approval date, and every loaded plan has one, so this currently returns the same figure as the 'uploaded' question — say so rather than presenting them as two different findings. Caveat: plan_code_status is 100% NULL, so approval is proxied by approval_date IS NOT NULL.",
        "members": ['PLN-002', 'PLN-013'],
    },

    'pln_003__planning': {
        "desc": 'The PERCENTAGE for: What percentage of Gram Panchayats in a given block have uploaded their GPDP in a given year. Returns total_gps, gps_uploaded, pct_uploaded. One row per block_name. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: Denominator is the GPs present in gram_panchayat (20 loaded), not the full official roster.',
        "members": ['PLN-003'],
    },

    'pln_004__planning': {
        "desc": 'The PERCENTAGE for: What percentage of Gram Panchayats in a given district have uploaded their GPDP in a given year. Returns total_gps, gps_uploaded, pct_uploaded. One row per district_name. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: Denominator is the GPs present in gram_panchayat (20 loaded), not the full official roster.',
        "members": ['PLN-004'],
    },

    'pln_005__planning': {
        "desc": 'LISTS: Which Gram Panchayats have not yet uploaded their GPDP in a given year. Returns gp_name, block_name, district_name. One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope. The GPs that filed NOTHING — an absence, listed from the roster by LEFT JOIN, so a GP with no plan still appears. That is the finding a review meeting wants and the opposite of the counting questions. Caveat: Returns zero rows when every loaded GP has a plan for that year.',
        "members": ['PLN-005'],
    },

    'pln_006__planning': {
        "desc": "LISTS: Which Blocks have achieved 100% GPDP submission in a given year. Returns total_gps, gps_uploaded. One row per block_name × district_name. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: '100%' is measured against loaded GPs only.",
        "members": ['PLN-006'],
    },

    'pln_007__planning': {
        "desc": "RANKS: Which Districts have the lowest GPDP submission rate in a given year. Returns total_gps, gps_uploaded, pct_uploaded. One row per district_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Caveat: Rate is over loaded GPs only.",
        "members": ['PLN-007'],
    },

    'pln_008__planning': {
        "desc": 'COUNTS: How many GPs in a given block uploaded the GPDP after the deadline a given deadline in a given year. Returns gps_late. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: No upload-date column exists;.',
        "members": ['PLN-008', 'PLN-009'],
    },

    'pln_010__planning': {
        "desc": 'LISTS: Which GPs in a given block/a given district uploaded the GPDP after the deadline a given deadline in a given year. Returns plan_type, approval_date, deadline, days_late. One row per matching record. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: approval_date used as the upload timestamp;.',
        "members": ['PLN-010'],
    },

    'pln_011__planning': {
        "desc": 'COUNTS: How many GPs uploaded the GPDP before and how many after the deadline a given deadline in a given year. Returns on_time_gps, late_gps, total_gps. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: approval_date used as the upload timestamp.',
        "members": ['PLN-011'],
    },

    'pln_012__planning': {
        "desc": 'LOOKS UP: What is the status of the GPDP for a given gram panchayat in a given year. Returns plan_type, approval_date, gpdp_status, (SELECT COUNT(*). One row per matching record. Restricted to plans with an approval date. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Only two states are distinguishable because plan_code_status is NULL throughout.',
        "members": ['PLN-012'],
    },

    'pln_014__planning': {
        "desc": 'COUNTS: How many Gram Panchayats in a given block/a given district are still awaiting GPDP approval in a given year. Returns gps_awaiting_approval. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Returns 0 because every plan row carries an approval_date.',
        "members": ['PLN-014'],
    },

    'pln_015__planning': {
        "desc": 'The PERCENTAGE for: What is the GPDP approval rate for each Block in a given year. Returns gps_with_plan, gps_approved, approval_rate_pct. One row per block_name. Restricted to plans with an approval date. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Approval proxied by approval_date, so the rate is 100% everywhere.',
        "members": ['PLN-015'],
    },

    'pln_016__planning': {
        "desc": 'The PERCENTAGE for: What is the GPDP approval rate for each District in a given year. Returns gps_with_plan, gps_approved, approval_rate_pct. One row per district_name. Restricted to plans with an approval date. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Approval proxied by approval_date, so the rate is 100% everywhere.',
        "members": ['PLN-016'],
    },

    'pln_017__planning': {
        "desc": 'LISTS: Which Districts have completed GPDP approval for all Gram Panchayats in a given year. Returns total_gps, gps_approved. One row per district_name. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Caveat: Approval proxied by approval_date.',
        "members": ['PLN-017'],
    },

    'pln_018__planning': {
        "desc": 'LISTS: Which Blocks have completed GPDP approval for all Gram Panchayats in a given year. Returns total_gps, gps_approved. One row per block_name. Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero activity are still in the denominator and still appear — which is the finding a review meeting is looking for. Caveat: Approval proxied by approval_date.',
        "members": ['PLN-018'],
    },

    'pln_019__planning': {
        "desc": 'LISTS: Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in a given year. Returns plan_type. One row per matching record. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Returns no rows: approval_date is populated on every plan.',
        "members": ['PLN-019'],
    },

    'pln_020__planning': {
        "desc": "RANKS: Which Blocks have the highest number of pending GPDP approvals in a given year. Returns pending_approvals, gps_with_plan. One row per block_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: pending_approvals is 0 everywhere because approval_date is always populated.",
        "members": ['PLN-020'],
    },

    'pln_021__planning': {
        "desc": "RANKS: Which district have the highest number of pending GPDP approvals in a given year. Returns pending_approvals, gps_with_plan. One row per district_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: pending_approvals is 0 everywhere because approval_date is always populated.",
        "members": ['PLN-021'],
    },

    'pln_024__planning': {
        "desc": 'COUNTS: How many activities are planned under each GPDP theme in a given gram panchayat in a given year. Returns theme, planned_activities, planned_cost. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Themes come from dim_lsdg_theme, which maps only 17 of 30 focus areas;.',
        "members": ['PLN-024'],
    },

    'pln_025__planning': {
        "desc": "RANKS: Which GPDP theme has the highest number of planned activities in a given gram panchayat in a given year. Returns theme, planned_activities, planned_cost. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.",
        "members": ['PLN-025', 'PLN-027', 'PLN-029'],
    },

    'pln_026__planning': {
        "desc": "RANKS: Which GPDP theme has the lowest number of planned activities in a given gram panchayat in a given year. Returns theme, planned_activities, planned_cost. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.",
        "members": ['PLN-026', 'PLN-028', 'PLN-030'],
    },

    'pln_031__planning': {
        "desc": "RANKS: Which Gram Panchayats have planned the highest number of activities under a given LSDG theme in a given year. Returns planned_activities, planned_cost. One row per gp_name × block_name × district_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme values must match dim_lsdg_theme.lsdg_theme exactly (note the trailing space on some).",
        "members": ['PLN-031'],
    },

    'pln_032__planning': {
        "desc": 'LISTS: Which Gram Panchayats have not planned any activities under a given LSDG theme in a given year. Returns gp_name, block_name, district_name. One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.',
        "members": ['PLN-032'],
    },

    'pln_033__planning': {
        "desc": 'RANKS: Which GP has the highest number of planned activities under each GPDP theme in a given year. Returns theme, planned_activities. One row per theme × gp_name. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: One winning unit per theme;.',
        "members": ['PLN-033'],
    },

    'pln_034__planning': {
        "desc": 'RANKS: Which Block has the highest number of planned activities under each GPDP theme in a given year. Returns theme, planned_activities. One row per theme × block_name. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: One winning unit per theme;.',
        "members": ['PLN-034'],
    },

    'pln_035__planning': {
        "desc": 'RANKS: Which District has the highest number of planned activities under each GPDP theme in a given year. Returns theme, planned_activities. One row per theme × district_name. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: One winning unit per theme;.',
        "members": ['PLN-035'],
    },

    'pln_036__planning': {
        "desc": "RANKS: Which theme receives the greatest planning attention across a given district in a given year. Returns theme, planned_activities, planned_cost, pct_of_activities. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['PLN-036'],
    },

    'pln_037__planning': {
        "desc": "RANKS: Which theme receives the least planning attention across a given district in a given year. Returns theme, planned_activities, planned_cost, pct_of_activities. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.",
        "members": ['PLN-037'],
    },

    'pln_038__planning': {
        "desc": 'The YEAR-BY-YEAR trend of: How has the number of planned activities under each theme changed over the last five years. Returns theme, planned_activities, planned_cost. One row per theme × fiscal_year. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Covers all six years present (2020-2021 to 2025-2026).',
        "members": ['PLN-038'],
    },

    'pln_039__planning': {
        "desc": "The YEAR-BY-YEAR trend of: Which themes have shown the greatest increase in planned activities between a second year and a given year. Returns theme, activities_year1, activities_year2, change_in_activities. One row per theme. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: The source question said 'in {Date_Range}';.",
        "members": ['PLN-039'],
    },

    'pln_040__planning': {
        "desc": "The YEAR-BY-YEAR trend of: Which themes have shown the greatest decline in planned activities between a second year and a given year. Returns theme, activities_year1, activities_year2, change_in_activities. One row per theme. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: The source question said 'in {Date_Range}';.",
        "members": ['PLN-040'],
    },

    'pln_043__planning': {
        "desc": 'LISTS: Which GPDP themes have no planned activities in a given year. Returns theme. One row per matching record. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Universe is the 7 distinct themes in dim_lsdg_theme, not the official nine LSDG themes.',
        "members": ['PLN-043'],
    },

    'pln_044__planning': {
        "desc": "TOTALS: Are the planned activities balanced across themes in a given gram panchayat/a given block in a given year. Returns theme, planned_activities, pct_share, even_share_pct, deviation_pts. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Balanced' is undefined in the source question, so the query returns each theme's share and its deviation from an even split for the user to judge.",
        "members": ['PLN-044'],
    },

    'pln_045__planning': {
        "desc": 'LISTS: Which GPDP themes have fewer than a given threshold planned activities in a given year. Returns theme, planned_activities. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-045'],
    },

    'pln_046__planning': {
        "desc": "The YEAR-BY-YEAR trend of: Which themes consistently receive low planning attention across multiple years. Returns theme, years_present, years_in_bottom_3, avg_activities_per_year. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Consistently low' is operationalised as how often a theme lands in the bottom 3 of a year.",
        "members": ['PLN-046'],
    },

    'pln_047__planning': {
        "desc": 'RANKS: Which themes require greater planning attention in the next GPDP cycle in a given year. Returns theme, planned_activities, pct_of_activities, planned_cost, actual_expenditure, pct_completed. One row per theme. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Advisory question with no defined rule;.',
        "members": ['PLN-047'],
    },

    'pln_049__planning': {
        "desc": 'COUNTS: How many activities are planned under a given focus area in a given gram panchayat in a given year. Returns focus_area_name, planned_activities, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-049'],
    },

    'pln_050__planning': {
        "desc": 'COUNTS: How many activities are planned under each focus area in a given gram panchayat in a given year. Returns focus_area_name, planned_activities, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-050', 'PLN-051'],
    },

    'pln_052__planning': {
        "desc": "RANKS: Which focus area has the highest number of planned activities in a given year. Returns focus_area_name, planned_activities, planned_cost. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Set $top_n = 1 for a single answer.",
        "members": ['PLN-052', 'PLN-054', 'PLN-056'],
    },

    'pln_053__planning': {
        "desc": "RANKS: Which focus area has the lowest number of planned activities in a given year. Returns focus_area_name, planned_activities, planned_cost. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Set $top_n = 1 for a single answer.",
        "members": ['PLN-053', 'PLN-055', 'PLN-057'],
    },

    'pln_058__planning': {
        "desc": "LISTS: What activities are planned under a given focus area in a given year. Returns activity_name, total_cost, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Raise $top_n to list more than the default page.",
        "members": ['PLN-058'],
    },

    'pln_059__planning': {
        "desc": 'LISTS: Which Gram Panchayats have not planned any activities under a given focus area in a given year. Returns gp_name, block_name, district_name. One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Filterable by district, block; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-059'],
    },

    'pln_060__planning': {
        "desc": 'COMPARES: How does the number of planned activities under each focus area compare across Gram Panchayats in a Block in a given year. Returns focus_area_name, unit, planned_activities, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: Long format - one row per focus area per unit;.',
        "members": ['PLN-060'],
    },

    'pln_061__planning': {
        "desc": 'COMPARES: How does the number of planned activities under each focus area compare across Blocks in a District in a given year. Returns focus_area_name, unit, planned_activities, planned_cost. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: Long format - one row per focus area per unit;.',
        "members": ['PLN-061'],
    },

    'pln_062__planning': {
        "desc": "RANKS: Which focus area receives the highest planning attention across a given district in a given year. Returns focus_area_name, planned_activities, pct_of_activities, planned_cost. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['PLN-062'],
    },

    'pln_063__planning': {
        "desc": "RANKS: Which focus area receives the lowest planning attention across a given district in a given year. Returns focus_area_name, planned_activities, pct_of_activities, planned_cost. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['PLN-063'],
    },

    'pln_064__planning': {
        "desc": "RANKS: Which focus areas account for the largest share of planned activities in a given gram panchayat in a given year. Returns focus_area_name, planned_activities, pct_share, planned_cost, pct_cost_share. One row per focus_area_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['PLN-064'],
    },

    'pln_065__planning': {
        "desc": "RANKS: Which focus areas account for the smallest share of planned activities in a given gram panchayat in a given year. Returns focus_area_name, planned_activities, pct_share, planned_cost, pct_cost_share. One row per focus_area_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['PLN-065'],
    },

    'pln_066__planning': {
        "desc": "The YEAR-BY-YEAR trend of: Which types of activity are repeatedly planned across years. Returns activity_name, years_planned, total_occurrences, total_planned_cost, first_year, last_year. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Matches on the exact activity_name string;.",
        "members": ['PLN-066'],
    },

    'pln_068__planning': {
        "desc": 'LISTS: Which focus areas have no planned activities in a given year. Returns focus_area_name. One row per matching record. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Universe is the 30 focus-area codes in dim_code.',
        "members": ['PLN-068'],
    },

    'pln_069__planning': {
        "desc": 'LISTS: Which focus areas have fewer than a given threshold planned activities in a given year. Returns focus_area_name, planned_activities. One row per focus_area_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-069'],
    },

    'pln_070__planning': {
        "desc": 'The YEAR-BY-YEAR trend of: Which focus areas are repeatedly included in the GPDP across multiple years. Returns focus_area_name, years_present, total_activities, avg_planned_cost. One row per focus_area_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLN-070'],
    },

    'pln_071__planning': {
        "desc": 'RANKS: Which focus areas require greater planning attention in the next GPDP cycle after a given year. Returns focus_area_name, planned_activities, pct_of_activities, planned_cost, actual_expenditure, pct_completed. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Advisory;.',
        "members": ['PLN-071'],
    },

    'pln_072__planning': {
        "desc": "TOTALS: Are the planned activities balanced across themes in a given year. Returns theme, planned_activities, pct_share, even_share_pct. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Same caveat as PLN-044: 'balanced' is not defined, so shares and the even-split benchmark are returned.",
        "members": ['PLN-072'],
    },

    'plu_001__plan_structure': {
        "desc": 'LOOKS UP: What is the status of the a given year plan of a given gram panchayat. Returns plan_type, approval_date, plan_status, (SELECT COUNT(*). One row per matching record. Restricted to plans with an approval date. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: plan_code_status is NULL throughout, so only Approved / Not approved can be distinguished.',
        "members": ['PLU-001'],
    },

    'plu_003__plan_structure': {
        "desc": 'LOOKS UP: Does a given gram panchayat have a supplementary plan in addition to the main plan for a given year. Returns main_plans, supplementary_plans, has_supplementary. One row per gp_name × block_name × district_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLU-003'],
    },

    'plu_004__plan_structure': {
        "desc": 'COUNTS: How many GPs in a given block uploaded supplementary plans for a given year. Returns gps_with_supplementary, supplementary_plans. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLU-004'],
    },

    'plu_006__low_cost_no_cost_activities': {
        "desc": "COUNTS: How many low-cost activities (below a given threshold rupees) are planned theme-wise in a given year. Returns theme, low_cost_activities, total_activities, pct_low_cost. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Pass $threshold = 1000 to reproduce the 'below Rs.",
        "members": ['PLU-006'],
    },

    'plu_007__low_cost_no_cost_activities': {
        "desc": 'TOTALS: What is the cost-band split (below 500, 500-1000, above 1000) of activities in a given district for a given year. Returns cost_band, activities, planned_cost, pct_of_activities. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLU-007'],
    },

    'plu_008__low_cost_no_cost_activities': {
        "desc": "COUNTS: How many no-cost activities are planned in a given block for a given year. Returns no_cost_activities, total_activities, pct_no_cost. A single summary row. Restricted to zero-cost activities. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Flagship' activities are not identifiable - no flagship flag exists.",
        "members": ['PLU-008'],
    },

    'plu_009__low_cost_no_cost_activities': {
        "desc": 'The PERCENTAGE for: What share of planned activities in a given gram panchayat are low-cost (below a given threshold) in a given year. Returns total_activities, low_cost_activities, pct_low_cost. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['PLU-009'],
    },

    'san_001__administrative_approval': {
        "desc": 'COUNTS: How many activities in a given gram panchayat received administrative approval in a given year. Returns admin_approved_activities, total_activities, pct_approved. A single summary row. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no approval-date or approval-flag column.',
        "members": ['SAN-001'],
    },

    'san_002__administrative_approval': {
        "desc": 'COUNTS: How many activities in a given block are still awaiting administrative approval in a given year. Returns total_activities, sanctioned, awaiting_sanction, cost_recorded_but_no_approval_row, cost_awaiting. A single summary row. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Now based on the presence of an admin_approval row rather than a non-zero cost.',
        "members": ['SAN-002'],
    },

    'san_003__administrative_approval': {
        "desc": 'TOTALS: What is the total administratively sanctioned amount for a given gram panchayat in a given year. Returns admin_sanctioned_amount, technical_sanctioned_amount, sanctioned_activities. One row per gp_name × block_name. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['SAN-003'],
    },

    'san_004__administrative_approval': {
        "desc": 'TOTALS: What is the block-wise administratively sanctioned amount in a given district in a given year. Returns sanctioned_activities, admin_sanctioned_amount, expenditure. One row per block_name. Restricted to activities that have an administrative approval (17% of them). expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['SAN-004'],
    },

    'san_005__administrative_approval': {
        "desc": 'LOOKS UP: What are the administrative approval order number, date and issuing authority for activity a given activity. Returns activity_name, admin_approval_no, admin_sanction_date, admin_issuing_authority, admin_authority_as_recorded, work_proposed_cost. One row per matching record. work_proposed_cost is the cost proposed in the approval order. Caveat: Unblocked by the new admin_approval and technical_approval tables.',
        "members": ['SAN-005'],
    },

    'san_006__administrative_approval': {
        "desc": 'COUNTS: How many activities in a given block were administratively sanctioned by each issuing authority in a given year. Returns issuing_authority, sanctioned_activities, proposed_cost, sanctioned_amount, first_sanction, last_sanction. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: adm_approval_authority is free text with many spellings of the same office.',
        "members": ['SAN-006'],
    },

    'san_007__administrative_approval': {
        "desc": 'The PERCENTAGE for: What percentage of planned activities in a given block have received administrative approval in a given year. Returns planned_activities, approved_activities, pct_approved. One row per block_name. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Approval proxied by admin_approved_cost > 0.',
        "members": ['SAN-007'],
    },

    'san_008__administrative_approval': {
        "desc": "RANKS: Which blocks in a given district have the lowest administrative approval coverage in a given year. Returns planned_activities, approved_activities, pct_approved. One row per block_name × district_name. A top-N list, lowest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Approval proxied by admin_approved_cost > 0.",
        "members": ['SAN-008'],
    },

    'san_009__administrative_approval': {
        "desc": 'The YEAR-BY-YEAR trend of: How many activities were administratively sanctioned in each month of a given year in a given block. Returns month, sanctioned_activities, sanctioned_amount, gps. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Unblocked by admin_approval.adm_approval_sanction_date.',
        "members": ['SAN-009'],
    },

    'san_010__administrative_approval': {
        "desc": 'COUNTS: How many administrative approvals in a given district were issued in each quarter of a given year. Returns calendar_quarter, sanction_year, sanctioned_activities, sanctioned_amount. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Quarters are calendar quarters of the sanction date, shown with their year because sanctions for one plan year are spread across several calendar years in this data.',
        "members": ['SAN-010'],
    },

    'san_011__administrative_approval': {
        "desc": "RANKS: Which activities in a given district received the highest administratively sanctioned amounts in a given year. Returns activity_name, sanction_day, sanction_authority, admin_approved_cost, fund_sanctioned_total, sanctioned_scheme_name. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Now enriched with the sanction date, authority, scheme and tied/untied component.",
        "members": ['SAN-011'],
    },

    'san_012__administrative_approval': {
        "desc": "RANKS: Which GPs in a given block have the highest total proposed cost awaiting administrative sanction in a given year. Returns activities_awaiting, proposed_cost_awaiting, sanctioned_activities, sanctioned_amount. One row per gp_name × block_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Awaiting sanction' now means no row in admin_approval.",
        "members": ['SAN-012'],
    },

    'san_013__administrative_approval': {
        "desc": 'TOTALS: What is the scheme-wise split of administratively sanctioned amounts in a given gram panchayat for a given year. Returns sanctioned_scheme_name, fund_component_name, tied_untied, sanctioned_activities, sanctioned_amount, expenditure. Restricted to activities that have an administrative approval (17% of them). expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Uses the sanctioned scheme from admin_approval_scheme, which is far more reliable than activity_expenditure.scheme_name (82% NULL).',
        "members": ['SAN-013'],
    },

    'san_014__administrative_approval': {
        "desc": 'TOTALS: What is the General/SC/ST split of administratively sanctioned funds in a given block for a given year. Returns target_category, sanctioned_activities, general_sanctioned, sc_sanctioned, st_sanctioned, total_sanctioned. Restricted to activities that have an administrative approval (17% of them). Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Now uses the real sanctioned-fund category columns.',
        "members": ['SAN-014'],
    },

    'sbm_gwm_001__grey_water_management': {
        "desc": 'COUNTS: How many Grey Water Management activities have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /soak|grey ?water|gwm/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-001'],
    },

    'sbm_gwm_002__grey_water_management': {
        "desc": 'TOTALS: What is the expenditure on Grey Water Management activities in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /soak|grey ?water|gwm/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-002'],
    },

    'sbm_gwm_003__grey_water_management': {
        "desc": 'COUNTS: How many community soak pits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(community|group|cluster)|(community|group|cluster).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-003'],
    },

    'sbm_gwm_004__grey_water_management': {
        "desc": 'COUNTS: How many community soak pits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(community|group|cluster)|(community|group|cluster).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-004'],
    },

    'sbm_gwm_005__grey_water_management': {
        "desc": 'COUNTS: How many community soak pits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(community|group|cluster)|(community|group|cluster).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-005'],
    },

    'sbm_gwm_006__grey_water_management': {
        "desc": 'COUNTS: How many community soak pits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(community|group|cluster)|(community|group|cluster).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-006'],
    },

    'sbm_gwm_007__grey_water_management': {
        "desc": 'TOTALS: What is the expenditure on community soak pits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(community|group|cluster)|(community|group|cluster).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-007'],
    },

    'sbm_gwm_008__grey_water_management': {
        "desc": 'COUNTS: How many household soak pits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(household|individual|hh)|(household|individual|hh).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-008'],
    },

    'sbm_gwm_009__grey_water_management': {
        "desc": 'COUNTS: How many household soak pits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(household|individual|hh)|(household|individual|hh).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-009'],
    },

    'sbm_gwm_010__grey_water_management': {
        "desc": 'COUNTS: How many household soak pits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(household|individual|hh)|(household|individual|hh).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-010'],
    },

    'sbm_gwm_011__grey_water_management': {
        "desc": 'COUNTS: How many household soak pits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(household|individual|hh)|(household|individual|hh).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-011'],
    },

    'sbm_gwm_012__grey_water_management': {
        "desc": 'TOTALS: What is the expenditure on household soak pits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(soak).*(household|individual|hh)|(household|individual|hh).*(soak)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-GWM-012'],
    },

    'sbm_om_001__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on community sanitary complexes in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|sanitary).*(complex|community)|community.*(toilet|complex)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-001'],
    },

    'sbm_om_002__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on community compost pits in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-002'],
    },

    'sbm_om_003__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on segregation sheds in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-003'],
    },

    'sbm_om_004__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on Plastic Waste Management Units in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /plastic waste|pwmu/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-004'],
    },

    'sbm_om_005__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on Gobardhan units in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-005'],
    },

    'sbm_om_006__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /soak|grey ?water|gwm/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-006'],
    },

    'sbm_om_007__operation_maintenance': {
        "desc": 'TOTALS: What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in a given year. Returns maintenance_activities, planned_cost, om_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /faecal|fsm|sludge/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text.',
        "members": ['SBM-OM-007'],
    },

    'sbm_om_008__operation_maintenance': {
        "desc": 'COUNTS: How many PPE kits and safety equipment purchases have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ppe|safety equipment|glove|mask|protective/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-OM-008'],
    },

    'sbm_om_009__operation_maintenance': {
        "desc": 'TOTALS: What is the expenditure on waste-management and safety equipment in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ppe|safety equipment|glove|mask|protective|waste.*equipment|equipment.*waste/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-OM-009'],
    },

    'sbm_om_010__operation_maintenance': {
        "desc": 'TOTALS: What is the total Operation & Maintenance expenditure in a given gram panchayat in a given year. Returns focus_area_name, maintenance_activities, planned_cost, om_expenditure. One row per focus_area_name. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: O&M is read as work_type Maintenance or Upgradation.',
        "members": ['SBM-OM-010'],
    },

    'sbm_si_001__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets in public institutions have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet).*(public|institution|community)|(public|institution|community).*(toilet)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-001'],
    },

    'sbm_si_002__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets in public institutions have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet).*(public|institution|community)|(public|institution|community).*(toilet)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-002'],
    },

    'sbm_si_003__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets in public institutions are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet).*(public|institution|community)|(public|institution|community).*(toilet)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-003'],
    },

    'sbm_si_004__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets in public institutions have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet).*(public|institution|community)|(public|institution|community).*(toilet)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-004'],
    },

    'sbm_si_005__sanitation_infrastructure': {
        "desc": 'TOTALS: What is the expenditure on toilets in public institutions in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet).*(public|institution|community)|(public|institution|community).*(toilet)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-005'],
    },

    'sbm_si_006__sanitation_infrastructure': {
        "desc": 'COUNTS: How many Individual Household Latrines (IHHLs) have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ihhl|individual household latrine/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-006'],
    },

    'sbm_si_007__sanitation_infrastructure': {
        "desc": 'COUNTS: How many Individual Household Latrines (IHHLs) have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ihhl|individual household latrine/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-007'],
    },

    'sbm_si_008__sanitation_infrastructure': {
        "desc": 'COUNTS: How many Individual Household Latrines (IHHLs) are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ihhl|individual household latrine/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-008'],
    },

    'sbm_si_009__sanitation_infrastructure': {
        "desc": 'COUNTS: How many Individual Household Latrines (IHHLs) have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ihhl|individual household latrine/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-009'],
    },

    'sbm_si_010__sanitation_infrastructure': {
        "desc": 'TOTALS: What is the expenditure on Individual Household Latrines (IHHLs) in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /ihhl|individual household latrine/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-010'],
    },

    'sbm_si_011__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets and handwash units in AWCs and schools have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-011'],
    },

    'sbm_si_012__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets and handwash units in AWCs and schools have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-012'],
    },

    'sbm_si_013__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets and handwash units in AWCs and schools are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-013'],
    },

    'sbm_si_014__sanitation_infrastructure': {
        "desc": 'COUNTS: How many toilets and handwash units in AWCs and schools have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-014'],
    },

    'sbm_si_015__sanitation_infrastructure': {
        "desc": 'TOTALS: What is the expenditure on toilets and handwash units in AWCs and schools in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-015'],
    },

    'sbm_si_016__sanitation_infrastructure': {
        "desc": 'COUNTS: How many single-pit to twin-pit toilet retrofits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /retrofit.*(twin|single)|twin pit|single pit/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-016'],
    },

    'sbm_si_017__sanitation_infrastructure': {
        "desc": 'COUNTS: How many single-pit to twin-pit toilet retrofits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /retrofit.*(twin|single)|twin pit|single pit/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-017'],
    },

    'sbm_si_018__sanitation_infrastructure': {
        "desc": 'COUNTS: How many single-pit to twin-pit toilet retrofits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /retrofit.*(twin|single)|twin pit|single pit/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-018'],
    },

    'sbm_si_019__sanitation_infrastructure': {
        "desc": 'COUNTS: How many single-pit to twin-pit toilet retrofits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /retrofit.*(twin|single)|twin pit|single pit/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-019'],
    },

    'sbm_si_020__sanitation_infrastructure': {
        "desc": 'TOTALS: What is the expenditure on single-pit to twin-pit toilet retrofits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /retrofit.*(twin|single)|twin pit|single pit/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-020'],
    },

    'sbm_si_021__sanitation_infrastructure': {
        "desc": 'COUNTS: How many septic-tank-with-soak-pit retrofits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /septic/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-021'],
    },

    'sbm_si_022__sanitation_infrastructure': {
        "desc": 'COUNTS: How many septic-tank-with-soak-pit retrofits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /septic/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-022'],
    },

    'sbm_si_023__sanitation_infrastructure': {
        "desc": 'COUNTS: How many septic-tank-with-soak-pit retrofits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /septic/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-023'],
    },

    'sbm_si_024__sanitation_infrastructure': {
        "desc": 'COUNTS: How many septic-tank-with-soak-pit retrofits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /septic/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-024'],
    },

    'sbm_si_025__sanitation_infrastructure': {
        "desc": 'TOTALS: What is the expenditure on septic-tank-with-soak-pit retrofits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /septic/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SI-025'],
    },

    'sbm_swm_001__solid_waste_management': {
        "desc": 'COUNTS: How many Solid Waste Management activities have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /solid waste|waste management|compost|segregat|gobardhan|plastic waste/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-001'],
    },

    'sbm_swm_002__solid_waste_management': {
        "desc": 'COUNTS: How many community compost pits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-002'],
    },

    'sbm_swm_003__solid_waste_management': {
        "desc": 'COUNTS: How many community compost pits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-003'],
    },

    'sbm_swm_004__solid_waste_management': {
        "desc": 'COUNTS: How many community compost pits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-004'],
    },

    'sbm_swm_005__solid_waste_management': {
        "desc": 'COUNTS: How many community compost pits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-005'],
    },

    'sbm_swm_006__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on community compost pits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(community|group|cluster)|(community|group|cluster).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-006'],
    },

    'sbm_swm_007__solid_waste_management': {
        "desc": 'COUNTS: How many household compost pits have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(household|individual|hh)|(household|individual|hh).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-007'],
    },

    'sbm_swm_008__solid_waste_management': {
        "desc": 'COUNTS: How many household compost pits have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(household|individual|hh)|(household|individual|hh).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-008'],
    },

    'sbm_swm_009__solid_waste_management': {
        "desc": 'COUNTS: How many household compost pits are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(household|individual|hh)|(household|individual|hh).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-009'],
    },

    'sbm_swm_010__solid_waste_management': {
        "desc": 'COUNTS: How many household compost pits have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(household|individual|hh)|(household|individual|hh).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-010'],
    },

    'sbm_swm_011__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on household compost pits in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(compost).*(household|individual|hh)|(household|individual|hh).*(compost)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-011'],
    },

    'sbm_swm_012__solid_waste_management': {
        "desc": 'COUNTS: How many segregation sheds have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-012'],
    },

    'sbm_swm_013__solid_waste_management': {
        "desc": 'COUNTS: How many segregation sheds have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-013'],
    },

    'sbm_swm_014__solid_waste_management': {
        "desc": 'COUNTS: How many segregation sheds are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-014'],
    },

    'sbm_swm_015__solid_waste_management': {
        "desc": 'COUNTS: How many segregation sheds have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-015'],
    },

    'sbm_swm_016__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on segregation sheds in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /segregation shed|sorting shed|waste.*shed/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-016'],
    },

    'sbm_swm_017__solid_waste_management': {
        "desc": 'COUNTS: How many segregation bins have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /bin|dustbin|dust bin/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-017'],
    },

    'sbm_swm_018__solid_waste_management': {
        "desc": 'COUNTS: How many segregation bins have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /bin|dustbin|dust bin/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-018'],
    },

    'sbm_swm_019__solid_waste_management': {
        "desc": 'COUNTS: How many segregation bins are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /bin|dustbin|dust bin/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-019'],
    },

    'sbm_swm_020__solid_waste_management': {
        "desc": 'COUNTS: How many segregation bins have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /bin|dustbin|dust bin/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-020'],
    },

    'sbm_swm_021__solid_waste_management': {
        "desc": 'COUNTS: How many household segregation bins have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(bin|dustbin).*(household|individual|hh)|(household|individual|hh).*(bin|dustbin)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-021'],
    },

    'sbm_swm_022__solid_waste_management': {
        "desc": 'COUNTS: How many community segregation bins have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /(bin|dustbin).*(community|group|cluster|public)|(community|group|cluster|public).*(bin|dustbin)/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-022'],
    },

    'sbm_swm_023__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on segregation bins in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /bin|dustbin|dust bin/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-023'],
    },

    'sbm_swm_024__solid_waste_management': {
        "desc": 'COUNTS: How many Gobardhan units have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-024'],
    },

    'sbm_swm_025__solid_waste_management': {
        "desc": 'COUNTS: How many Gobardhan units have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-025'],
    },

    'sbm_swm_026__solid_waste_management': {
        "desc": 'COUNTS: How many Gobardhan units are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-026'],
    },

    'sbm_swm_027__solid_waste_management': {
        "desc": 'COUNTS: How many Gobardhan units have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-027'],
    },

    'sbm_swm_028__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on Gobardhan units in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /gobardhan|bio.?gas/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-028'],
    },

    'sbm_swm_029__solid_waste_management': {
        "desc": 'COUNTS: How many door-to-door waste-collection vehicles have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-029'],
    },

    'sbm_swm_030__solid_waste_management': {
        "desc": 'COUNTS: How many door-to-door waste-collection vehicles have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-030'],
    },

    'sbm_swm_031__solid_waste_management': {
        "desc": 'COUNTS: How many door-to-door waste-collection vehicles are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-031'],
    },

    'sbm_swm_032__solid_waste_management': {
        "desc": 'COUNTS: How many door-to-door waste-collection vehicles have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-032'],
    },

    'sbm_swm_034__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on door-to-door waste-collection vehicles in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-034'],
    },

    'sbm_swm_035__solid_waste_management': {
        "desc": 'COUNTS: How many weighing machines have been planned in a given year. Returns matching_activities, planned_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /weighing/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-035'],
    },

    'sbm_swm_036__solid_waste_management': {
        "desc": 'COUNTS: How many weighing machines have been approved in a given year. Returns matching_activities, approved_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /weighing/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. Restricted to activities that have an administrative approval (17% of them). planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-036'],
    },

    'sbm_swm_037__solid_waste_management': {
        "desc": 'COUNTS: How many weighing machines are ongoing in a given year. Returns matching_activities, ongoing_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /weighing/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-037'],
    },

    'sbm_swm_038__solid_waste_management': {
        "desc": 'COUNTS: How many weighing machines have been completed in a given year. Returns matching_activities, completed_activities, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /weighing/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-038'],
    },

    'sbm_swm_039__solid_waste_management': {
        "desc": 'TOTALS: What is the expenditure on weighing machines in a given year. Returns matching_activities, expenditure, planned_cost, total_expenditure. A single summary row. Identifies the activity by KEYWORD MATCH on activity_name + activity_desc against the pattern /weighing/. Nothing in the database codes SBM activity types, so this is a text search: it both misses differently-worded activities and picks up unrelated ones. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL.',
        "members": ['SBM-SWM-039'],
    },

    'sch_001__scheme_coverage': {
        "desc": 'COUNTS: How many activities are recorded under a given scheme in a given district for a given year. Returns scheme_name, activities, expenditure. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name has only 5 non-null values and is NULL on 82% of rows.',
        "members": ['SCH-001'],
    },

    'sch_002__scheme_coverage': {
        "desc": "LISTS: Which activities of a given gram panchayat are funded under a given scheme in a given year. Returns activity_name, focus_area_name, approved_cost_action_plan, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. approved_cost_action_plan is the action-plan approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name coverage is 18%.",
        "members": ['SCH-002'],
    },

    'sch_003__scheme_coverage': {
        "desc": 'TOTALS: What is the total estimated cost of activities under a given scheme in a given block for a given year. Returns scheme_name, activities, estimated_cost, approved_cost, expenditure. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name coverage is 18%.',
        "members": ['SCH-003'],
    },

    'sch_005__scheme_coverage': {
        "desc": "RANKS: Which scheme has the highest expenditure in a given block for a given year. Returns scheme_name, activities, expenditure. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name coverage is 18%.",
        "members": ['SCH-005'],
    },

    'sch_006__scheme_coverage': {
        "desc": 'LISTS: Which GPs in a given block have no activities under a given scheme in a given year. Returns gp_name, block_name, district_name. One row per matching record. An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no matching record at all. A query over the activity table alone can never return these rows, because the rows it would need do not exist there. Filterable by block, district; answers state-wide when no place is named — one entry serves every scope. Caveat: Because scheme_name is NULL on 82% of rows, many GPs appear here purely from missing data rather than genuine absence.',
        "members": ['SCH-006'],
    },

    'sch_007__scheme_coverage': {
        "desc": "LOOKS UP: Under which scheme and fund component is activity a given activity sanctioned. Returns activity_name, sanctioned_scheme_name, fund_component_name, tied_untied, fund_sanctioned_general, fund_sanctioned_sc. One row per matching record. fund_sanctioned_total is funds sanctioned under the approval's scheme components. Caveat: Fully unblocked: admin_approval_scheme supplies both the scheme and the fund component, which the previous database could not.",
        "members": ['SCH-007'],
    },

    'sch_008__scheme_coverage': {
        "desc": 'COMPARES: Compare the activity counts and expenditure of a given scheme and a second scheme in a given district for a given year. Returns scheme_name, activities, approved_cost, expenditure, pct_utilised. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name coverage is 18%.',
        "members": ['SCH-008'],
    },

    'sch_009__scheme_coverage': {
        "desc": 'COUNTS: What is the status breakdown of activities under a given scheme in a given district for a given year. Returns status_label, activities, expenditure. One row per status_label. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: scheme_name coverage is 18%;.',
        "members": ['SCH-009'],
    },

    'sch_010__scheme_coverage': {
        "desc": 'TOTALS: What is the General/SC/ST funding split under a given scheme in a given block for a given year. Returns scheme_name, general_amount, sc_amount, st_amount, total_amount. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: sc and st amounts are sparsely populated.',
        "members": ['SCH-010'],
    },

    'sch_011__scheme_coverage': {
        "desc": 'COUNTS: What is the district-wise activity count under a given scheme for a given year. Returns activities, expenditure. One row per district_name. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Caveat: scheme_name coverage is 18%.',
        "members": ['SCH-011'],
    },

    'sts_001__status_counts': {
        "desc": "COUNTS: How many activities in a given gram panchayat are in each progress status for a given year. Returns status_label, activities, planned_cost, expenditure. One row per status_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: activity_status code 173 decodes to 'Buildings' in dim_code, which is not a status and needs verifying.",
        "members": ['STS-001'],
    },

    'sts_002__status_counts': {
        "desc": 'COUNTS: What is the block-wise activity status breakdown in a given district for a given year. Returns status_label, activities. One row per block_name × status_label. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: See STS-001 note on code 173.',
        "members": ['STS-002'],
    },

    'sts_003__status_counts': {
        "desc": 'COUNTS: How many activities in a given block are in a given status status for a given year. Returns status_label, activities, planned_cost, expenditure. One row per status_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: $status must match a decoded label exactly: Activity Approved, WORK ONGOING, WORK COMPLETED, WORK ABANDONED, UNDER APPROVAL.',
        "members": ['STS-003'],
    },

    'sts_004__status_counts': {
        "desc": "RANKS: Which GPs in a given district have the highest number of abandoned activities in a given year. Returns abandoned_activities, total_activities, expenditure_on_abandoned. One row per gp_name × block_name × district_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work abandoned. Filterable by district; answers state-wide when no place is named — one entry serves every scope.",
        "members": ['STS-004'],
    },

    'sts_005__status_counts': {
        "desc": "LISTS: Which activities in a given block are abandoned, and what are their costs in a given year. Returns activity_name, estimated_cost, admin_approved_cost, total_expenditure, status_label. One row per matching record. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Counts only work abandoned. admin_approved_cost is the administratively approved cost. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no 'suspended' status in the data;.",
        "members": ['STS-005'],
    },

    'sts_006__status_counts': {
        "desc": 'The PERCENTAGE for: What percentage of taken-up activities in a given block are completed in a given year. Returns taken_up_activities, completed_activities, pct_completed. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['STS-006'],
    },

    'sts_007__status_counts': {
        "desc": "RANKS: Which blocks in a given district have the highest activity completion rate for a given year. Returns activities, started, completed, pct_completed. One row per block_name × district_name. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.",
        "members": ['STS-007'],
    },

    'sts_008__status_counts': {
        "desc": "The PERCENTAGE for: What share of approved activities in a given district has not yet started in a given year. Returns activities, approved_not_started, started, pct_not_started. A single summary row. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Not started' is read as status 'Activity Approved' - approved but with no work status recorded.",
        "members": ['STS-008'],
    },

    'sts_009__status_counts': {
        "desc": 'LISTS: Which GPs in a given block have zero completed activities in a given year. Returns activities, completed. One row per gp_name × block_name × district_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['STS-009'],
    },

    'sts_010__status_counts': {
        "desc": 'COUNTS: How many activities in a given block are stuck in Under Approval status for a given year. Returns under_approval, total_activities, cost_under_approval. A single summary row. Counts only activities under approval. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 36 activities carry this status across the whole database.',
        "members": ['STS-010'],
    },

    'sts_011__status_counts': {
        "desc": 'LISTS: Which blocks in a given district have every taken-up activity started for a given year. Returns activities, started, pct_started. One row per block_name × district_name. Filterable by district; answers state-wide when no place is named — one entry serves every scope. Caveat: Progress is read from activity_status.',
        "members": ['STS-011'],
    },

    'sts_012__status_counts': {
        "desc": 'COUNTS: How many plan units and taken-up activities does a given gram panchayat have for a given year. Returns plan_units, planned_activities, taken_up_activities, completed_activities. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['STS-012'],
    },

    'sts_013__status_counts': {
        "desc": 'COUNTS: What is the district-wise activity status summary for a given year. Returns activities, approved_not_started, ongoing, completed, abandoned, under_approval. One row per district_name. Caveat: Progress is read from activity_status.',
        "members": ['STS-013'],
    },

    'trd_001__year_on_year': {
        "desc": 'COMPARES: Compare the activities planned and started theme-wise between a second year and a given year. Returns theme, planned_year1, planned_year2, started_year1, started_year2. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping covers 17 of 30 focus areas.',
        "members": ['TRD-001'],
    },

    'trd_002__year_on_year': {
        "desc": 'COMPARES: Compare the approved cost and expenditure theme-wise between a second year and a given year. Returns theme, approved_cost_year1, approved_cost_year2, expenditure_year1, expenditure_year2. One row per theme. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.',
        "members": ['TRD-002'],
    },

    'trd_003__year_on_year': {
        "desc": 'The YEAR-BY-YEAR trend of: What is the year-wise expenditure of a given gram panchayat against the plan of each year. Returns activities, approved_cost, expenditure, pct_utilised. One row per fiscal_year. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Expenditure is recorded against the year of the plan it belongs to;.',
        "members": ['TRD-003'],
    },

    'trd_004__year_on_year': {
        "desc": 'COMPARES: How did the total expenditure of a given block change between a second year and a given year. Returns expenditure_year1, expenditure_year2, change_amount, change_pct. One row per matching record. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['TRD-004'],
    },

    'trd_005__year_on_year': {
        "desc": 'The YEAR-BY-YEAR trend of: How has the activity completion rate of a given district changed over the years. Returns activities, started, completed, completion_rate_pct, initiation_rate_pct. One row per fiscal_year. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Only 17 activities in the whole database are marked WORK COMPLETED, so completion rates are near zero throughout.',
        "members": ['TRD-005'],
    },

    'trd_006__year_on_year': {
        "desc": 'The YEAR-BY-YEAR trend of: What is the year-wise total expenditure of a given gram panchayat. Returns activities, expenditure. One row per gp_name × fiscal_year. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['TRD-006'],
    },

    'trd_007__physical_vs_financial': {
        "desc": 'COMPARES: What are the approved cost, expenditure and status counts theme-wise for a given gram panchayat in a given year. Returns theme, activities, approved_cost, expenditure, started, ongoing. One row per theme. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: Theme mapping is partial.',
        "members": ['TRD-007'],
    },

    'trd_008__physical_vs_financial': {
        "desc": "COMPARES: What are the approved cost and expenditure sector-wise in a given district for a given year. Returns sector, activities, approved_cost, expenditure, pct_utilised. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'Sector' is read as focus area, the closest sectoral classification in the data.",
        "members": ['TRD-008'],
    },

    'trd_009__physical_vs_financial': {
        "desc": "RANKS: Which themes in a given block show high expenditure but low activity completion in a given year. Returns theme, activities, expenditure, completed, completion_rate_pct. One row per theme. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: 'High' and 'low' are undefined;.",
        "members": ['TRD-009'],
    },

    'trd_010__entity_comparison': {
        "desc": 'COMPARES: Compare planned expenditure, actual expenditure and completion rate between a given gram panchayat and a second gram panchayat for a given year. Returns activities, planned_cost, actual_expenditure, pct_utilised, completed, completion_rate_pct. One row per gp_name × block_name × district_name. planned_cost is the planned cost the GP entered in the action plan. A two-GP head-to-head. Both GPs must be named; a question about one GP alone belongs to an ordinary GP-filtered family. Caveat: Both $gp_name and $gp_name_2 must be supplied (no NULL skip here).',
        "members": ['TRD-010'],
    },

    'trd_011__entity_comparison': {
        "desc": 'COMPARES: Compare activity counts, expenditure and completion rates between a given block and a second block for a given year. Returns gps, activities, planned_cost, actual_expenditure, pct_utilised, completion_rate_pct. One row per block_name × district_name. planned_cost is the planned cost the GP entered in the action plan. A two-BLOCK head-to-head. Both blocks must be named. Caveat: Both block parameters must be supplied.',
        "members": ['TRD-011'],
    },

    'trd_012__entity_comparison': {
        "desc": 'COMPARES: How does a given district compare with the state average on expenditure per GP and completion rate for a given year. Returns gps, activities, expenditure, expenditure_per_gp, completion_rate_pct, state_avg_expenditure_per_gp. One row per district_name. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district; answers state-wide when no place is named — one entry serves every scope. One district read against the STATE benchmark. Every district is returned so the chosen one can be seen in context — the district filter deliberately does not narrow the table. Caveat: Every district is returned alongside the state benchmark so the chosen district can be read in context.',
        "members": ['TRD-012'],
    },

    'wrk_001__fresh_vs_maintenance': {
        "desc": 'COUNTS: How many fresh and how many maintenance activities does a given gram panchayat have in a given year. Returns work_type_label, activities, planned_cost, actual_expenditure. One row per work_type_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: work_type decodes to New/Fresh, Maintenance, Upgradation, None;.',
        "members": ['WRK-001'],
    },

    'wrk_002__fresh_vs_maintenance': {
        "desc": 'TOTALS: What is the expenditure on fresh versus maintenance activities in a given block for a given year. Returns work_type_label, activities, planned_cost, actual_expenditure, pct_of_expenditure. One row per work_type_label. planned_cost is the planned cost the GP entered in the action plan. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['WRK-002'],
    },

    'wrk_003__fresh_vs_maintenance': {
        "desc": 'The PERCENTAGE for: What share of total expenditure in a given district went to maintenance activities in a given year. Returns total_expenditure, maintenance_expenditure, pct_maintenance. A single summary row. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['WRK-003'],
    },

    'wrk_004__fresh_vs_maintenance': {
        "desc": "RANKS: Which asset sub-categories have the highest number of maintenance activities in a given district in a given year. Returns asset_subcategory_label, maintenance_activities, expenditure. A top-N list, highest first; $top_n = 1 answers 'which is the single highest/lowest'. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: asset_subcategory is populated on 4,286 of 12,704 asset rows, so most maintenance activity lands in 'Uncategorised'.",
        "members": ['WRK-004'],
    },

    'wrk_005__fresh_vs_maintenance': {
        "desc": 'LISTS: Which GPs in a given block spend more on maintenance than on fresh assets in a given year. Returns maintenance_exp, fresh_exp, total_exp. One row per gp_name × block_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['WRK-005'],
    },

    'wrk_007__fresh_vs_maintenance': {
        "desc": 'The YEAR-BY-YEAR trend of: How has maintenance expenditure in a given block changed over the years. Returns maintenance_activities, maintenance_expenditure, total_expenditure, pct_maintenance. One row per fiscal_year. total_expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope.',
        "members": ['WRK-007'],
    },

    'wrk_008__fresh_vs_maintenance': {
        "desc": 'COMPARES: What is the fresh versus maintenance split for a given asset category activities in a given district in a given year. Returns asset_category_label, work_type_label, activities, expenditure. One row per asset_category_label × work_type_label. expenditure is actual expenditure on the PLAN basis (activity_expenditure), not the cashbook. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: asset_category is populated on 4,286 of 12,704 rows.',
        "members": ['WRK-008'],
    },

    'wrk_009__fresh_vs_maintenance': {
        "desc": 'LISTS: Which assets in a given gram panchayat have had maintenance activities in more than one year. Returns asset_subcategory_label, activity_name, years_with_maintenance, years, total_maintenance_expenditure. One row per gp_name. Filterable by district, block, GP; answers state-wide when no place is named — one entry serves every scope. Caveat: There is no asset identifier that persists across years, so repeat maintenance is inferred from identical activity_name + asset sub-category.',
        "members": ['WRK-009'],
    },
}


# query_id -> family description, expanded from the members lists above.
DESC_BY_QID: dict[str, str] = {
    qid: family["desc"]
    for family in FAMILY_DESCRIPTIONS.values()
    for qid in family["members"]
}

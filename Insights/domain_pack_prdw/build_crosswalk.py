"""Materialise DISCOVER_VIEW_MAPPING §7 as domain_pack_prdw/crosswalk.csv.

NOT PART OF THE PIPELINE. `build_views.py` never reads this file — a domain pack
is declarative YAML + SQL, and this is a maintenance script that regenerates one
delivered artefact. It lives beside the pack because the role table it carries IS
the pack's copy of §7; keeping it here is what stops crosswalk.csv drifting away
from the views it describes.

One row per column of every staged table: its §7 role, the cast applied at
registration, the view columns it feeds, and — for excluded roles — the reason.
fill_pct / n_distinct are measured from the CSVs at generation time, so
crosswalk.csv is regenerated, never hand-edited.

It also runs the gate checks against the built Parquet views:
  1. no X-* role names an output column   (nothing excluded reaches a view)
  2. every claimed output column exists   (no stale crosswalk entry)
  3. every view column is claimed         (no undocumented output column)
  4. every CSV column has exactly one row  (100% staged-column coverage)
  5. no X-pii column NAME appears in any view's output columns  (WP-D11)

WP-D11 (Amendment B §12) added the twentieth table, `gp_profile`: 99 columns,
one row per Gram Panchayat, and a fourth view built on it. Check 5 is new and
is the operator's ruling made mechanical -- email, mobile, address and
gp_attractions are needed for nothing, so the assertion is not that they carry
no analytical role but that their NAMES cannot be found in a Parquet schema.
Check 1 already forbids an X-* role from claiming an output column; check 5 is
the independent half, read off the built views rather than off this file, so a
column renamed into a view would still be caught.

Usage (paths default to the repo layout, relative to this file):
    python Insights/domain_pack_prdw/build_crosswalk.py \
        [--data-dir Data] [--views-dir Insights/views_prdw] \
        [--out Insights/domain_pack_prdw/crosswalk.csv]
"""
import argparse, csv, duckdb, os

_here = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.dirname(os.path.dirname(_here))
_p = argparse.ArgumentParser(description="Regenerate domain_pack_prdw/crosswalk.csv.")
_p.add_argument("--data-dir",  default=os.path.join(_repo, "Data"))
_p.add_argument("--views-dir", default=os.path.join(_repo, "Insights", "views_prdw"))
_p.add_argument("--out",       default=os.path.join(_here, "crosswalk.csv"))
_a = _p.parse_args()

D = os.path.abspath(_a.data_dir).replace("\\", "/")
V = os.path.abspath(_a.views_dir).replace("\\", "/")
OUT = _a.out

con = duckdb.connect(); con.execute("SET TimeZone='UTC'")

# casts as declared in sources.yaml (logical type -> recorded in the crosswalk)
CASTS = {
    "plan": {"approval_date": "date"},
    "planned_activity": {"total_cost": "float"},
    "activity_expenditure": {c: "float" for c in [
        "approved_cost_action_plan", "technical_approved_cost", "admin_approved_cost",
        "general", "sc", "st", "total_expenditure"]},
    "activity_voucher": {"voucher_cost": "float", "voucher_date": "date"},
    "voucher": {"amount": "float", "date": "date"},
    "admin_approval": {"work_proposed_cost": "float", "adm_approval_sanction_date": "date"},
    "admin_approval_scheme": {c: "float" for c in [
        "fund_sanctioned_general", "fund_sanctioned_sc", "fund_sanctioned_st",
        "fund_sanctioned_total"]},
    "technical_approval": {"tec_approval_cost": "float", "tec_approval_order_date": "date"},
    "activity_fund": {c: "float" for c in [
        "fund_tied_general", "fund_tied_sc", "fund_tied_st", "fund_untied_general",
        "fund_untied_sc", "fund_untied_st", "fund_amount_total",
        "fund_tied_abandoned_general", "fund_tied_abandoned_sc", "fund_tied_abandoned_st",
        "fund_untied_abandoned_general", "fund_untied_abandoned_sc",
        "fund_untied_abandoned_st"]},
    "activity_asset": {"asset_unit_cost": "float", "asset_unit_count": "float",
                       "main_asset_unit_count": "float", "asset_loc_unit_count": "float",
                       "asset_loc_unit_cost_total": "float"},
    "activity_training": {"training_trainees_total": "int", "training_duration_days": "int"},
    "activity_community_service": {"community_service_duration": "int",
                                   "community_beneficiaries_expected": "int"},
    "physical_progress": {"longitude": "float", "latitude": "float", "n_coords": "int"},
    "dim_lsdg_theme": {"distinct_themes": "int", "n_rows": "int"},
    # WP-D11. 43 int + 2 float, exactly as sources.yaml declares them. The seven
    # numeric columns that carry the literal 'NA' token are deliberately absent
    # here as well: they stay VARCHAR at registration and are cast behind NULLIF
    # in derived_columns.sql, and the crosswalk must record what the pack does.
    "gp_profile": dict(
        [(c, "int") for c in [
            "basic_info_distance_from_nearest_bus_stop",
            "demographic_details_total_gender_wise_population",
            "demographic_details_male_population", "demographic_details_female_population",
            "demographic_details_transgender_population", "demographic_details_children_population",
            "demographic_details_general_population", "demographic_details_obc_population",
            "demographic_details_sc_population", "demographic_details_st_population",
            "education_total_pre_primary_schools", "education_total_primary_schools",
            "education_total_secondary_schools", "education_total_higher_secondary_schools",
            "general_no_of_anganwadi_centers", "general_no_of_destitue_homes_old_age_homes",
            "general_no_of_households", "general_no_of_job_card_holders", "general_no_of_shg",
            "health_no_of_health_sub_centers", "health_no_of_primary_health_centers",
            "health_no_of_well_being_centers", "health_no_of_dispensary",
            "health_no_of_ayurvedic_clinics",
            "infrastructure_no_of_drinking_water_sources",
            "infrastructure_no_of_households_connected_to_tap_water",
            "infrastructure_no_of_household_toilets",
            "infrastructure_no_of_community_sanitary_complexes",
            "infrastructure_no_of_solid_waste_managements_centers",
            "infrastructure_no_of_common_service_centers",
            "infrastructure_no_of_banks_cooperative_banks", "infrastructure_no_of_atms",
            "infrastructure_no_of_rural_library", "infrastructure_no_of_children_parks",
            "infrastructure_no_of_disaster_rescue_centers",
            "infrastructure_no_of_bus_stands_with_drinking_water_facility",
            "infrastructure_no_of_cooperative_seed_centers",
            "panchayat_area_no_of_wards_sansads_of_the_panchayat",
            "panchayat_area_no_of_revenue_villages",
            "panchayat_area_no_of_villages_mapped_with_lgd",
            "sports_no_of_badminton_court", "sports_no_of_football_court",
            "sports_no_of_volleyball_court"]]
        + [("basic_amenities_osr_collected_so_far", "float"),
           ("panchayat_area_total_area", "float")]),
}

V1, V2, V3 = "view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance"
V4 = "view4_gp_profile"                      # WP-D11, Amendment B §12.4
ALL3 = f"{V1}; {V2}; {V3}"
ALL4 = f"{V1}; {V2}; {V3}; {V4}"             # the seven profile dimensions ride all four
VIEWS = (V1, V2, V3, V4)
GEO = "gp_lgd_code; gp_name; block_code; block_name; district_code; district_name"

# (role, views, output_columns, reason, note)
SPEC = {
 "gram_panchayat": {
  "gp_lgd_code":  ("dim", ALL4, "gp_lgd_code", "", "the join spine of every view, the grain of views 2, 3 and 4, and the key gp_profile joins on"),
  "gp_name":      ("dim", ALL4, "gp_name", "", ""),
  "block_code":   ("dim", ALL4, "block_code", "", ""),
  "block_name":   ("dim", ALL4, "block_name", "", ""),
  "district_code":("dim", ALL4, "district_code", "", ""),
  "zp_name":      ("dim", ALL4, "district_name", "", "renamed district_name, as v_activity does"),
  "state_code":   ("X-const", "", "", "constant in this drop (Odisha only)", "staged for statewide continuity"),
  "state_name":   ("X-const", "", "", "constant in this drop (Odisha only)", "staged for statewide continuity"),
 },
 "plan": {
  "plan_code":        ("grain", "", "", "plan grain; view3 exposes the COUNT, not the code", "n_plans"),
  "gp_lgd_code":      ("join", f"{V3}; {V4}", "", "", "attributes n_plans to a GP"),
  "fiscal_year":      ("dim", V3, "fiscal_year", "", "one of the three sources of stg_fiscal_year_domain"),
  "plan_type":        ("dim", "", "", "Main/Supplementary is a plan-grain attribute; view3 is GP x FY, where a cell can hold both", "CHECK 5 asserts the domain"),
  "approval_date":    ("temp", "", "", "non-null on all 204 rows, so is_approved is constant 1 here", "CHECK 6 reads it via stg_plan.approval_date_ts"),
  "plan_code_status": ("X-empty", "", "", "always null (known generated placeholder) - §8.6", ""),
 },
 "planned_activity": {
  "activity_code":        ("grain", V1, "activity_code", "", "view1's grain; the unique_grain post-view check"),
  "plan_code":            ("join", "", "", "consumed by the plan FK check; no analytical role", ""),
  "gp_lgd_code":          ("join", ALL4, "", "", "consumed into the geography block"),
  "fiscal_year":          ("dim", f"{V1}; {V3}", "fiscal_year", "", "CATEGORICAL in view1 - §5 routes temporal mining to view2"),
  "source_file":          ("X-id", "", "", "ingestion provenance, no analytical role", ""),
  "activity_type":        ("decode-dim", V1, "activity_type_label", "", "dim_code variable activity_type"),
  "activity_name":        ("join", "", "", "free text; feeds Ask's search_text only - §9.6", ""),
  "activity_desc":        ("join", "", "", "free text; feeds Ask's search_text only - §9.6", ""),
  "focus_area":           ("decode-dim", V1, "focus_area_name; theme", "", "also the join to dim_lsdg_theme"),
  "activity_for":         ("decode-dim", V1, "activity_for_label", "", ""),
  "work_type":            ("decode-dim", V1, "work_type_label", "", "code 142 has no description -> 'Unknown'"),
  "is_costless_activity": ("dim", V1, "is_costless", "", "0/1 raw; view1 exposes the Costed/Costless label (§2)"),
  "total_cost":           ("meas", f"{V1}; {V3}; {V4}", "total_cost; planned_cost", "", "PLANNED basis; null <=> costless. view4 carries the lifetime total under the same name view3 uses"),
  "operation_type":       ("X-empty", "", "", "97.3% null", ""),
  "operation_remarks":    ("X-empty", "", "", "98.6% null", ""),
  "output_type":          ("decode-dim", V1, "output_type_label", "", "all 8 codes lack a dim_code description -> every label is 'Code 1NN'"),
  "activity_status":      ("decode-dim", V1, "status_label", "", "carries the 'Buildings' mis-decode (13) and the tab-prefixed WORK COMPLETED (17) - §8.3"),
 },
 "activity_expenditure": {
  "expenditure_id":            ("grain", "", "", "expenditure grain; stg_exp_rollup collapses it to the activity", "also the activity_voucher FK parent"),
  "activity_code":             ("join", "", "", "20 codes have no planned_activity parent - the FK is deliberately NOT declared", ""),
  "plan_code":                 ("join", "", "", "redundant with planned_activity", ""),
  "gp_lgd_code":               ("join", "", "", "redundant with planned_activity; FK-checked", ""),
  "fiscal_year":               ("dim", "", "", "equals planned_activity.fiscal_year on every matched row; view1/view3 use the activity's", ""),
  "s_no":                      ("X-id", "", "", "source line number", ""),
  "scheme_name":               ("X-empty", "", "", "82.3% null - superseded by sanctioned_scheme_name (§2)", "v_activity carries it; Discover does not"),
  "approved_cost_action_plan": ("meas", V1, "approved_cost_action_plan", "", ""),
  "technical_approved_cost":   ("meas", V1, "technical_approved_cost", "", ""),
  "admin_approved_cost":       ("meas", V1, "admin_approved_cost", "", "also drives has_approval_cost_only (140 activities)"),
  "general":                   ("meas", V1, "gen_amount", "", "v_exp naming"),
  "sc":                        ("meas", V1, "sc_amount", "", "19 non-null rows sample-wide (§4.4)"),
  "st":                        ("meas", V1, "st_amount", "", "2 non-null rows sample-wide (§4.4)"),
  "total_expenditure":         ("meas", f"{V1}; {V3}; {V4}", "total_expenditure; expenditure_total; overspend_vs_plan; overspend_vs_sanction", "", "SPENT basis; == linked voucher sums exactly"),
 },
 "activity_voucher": {
  "expenditure_id": ("join", "", "", "links a voucher to an expenditure row", ""),
  "voucher_pk":     ("join", "", "", "488 null + 5,488 float-text values that never match voucher.voucher_pk as VARCHAR - see stg_activity_voucher.voucher_pk_norm", "NEW defect found in WP-D1"),
  "gp_lgd_code":    ("join", V2, "", "", "attributes activity_linked_expenditure to a GP"),
  "fiscal_year":    ("dim", "", "", "the only place '2026-2027' exists (488 orphan rows); view2 derives FY from the calendar month instead", "§8.1"),
  "voucher_no":     ("X-id", "", "", "document number", ""),
  "voucher_date":   ("temp", V2, "month; quarter; fiscal_year", "", "attributes linked spend to a cash month"),
  "voucher_cost":   ("meas", V2, "activity_linked_expenditure", "", "SPENT basis on the cash timeline"),
 },
 "voucher": {
  "voucher_pk":  ("grain", "", "", "cashbook grain; view2 exposes counts, not keys", ""),
  "gp_lgd_code": ("join", f"{V2}; {V3}; {V4}", "", "", "attributes cash flows to a GP"),
  "fiscal_year": ("dim", V3, "fiscal_year", "", "one of the three sources of stg_fiscal_year_domain"),
  "voucher_no":  ("X-id", "", "", "document number", ""),
  "voucher_id":  ("X-id", "", "", "system identifier", ""),
  "direction":   ("dim", V2, "payment_amount; receipt_amount; payment_count; receipt_count", "", "splits every cashbook measure; CHECK 5 asserts [payment, receipt]"),
  "type":        ("dim", "", "", "7 transaction types; an OPEN domain, so not asserted and not exposed as a v1 dimension", "profiled every build"),
  "date":        ("temp", V2, "month; quarter; fiscal_year", "", "DERIVES the whole view2 calendar (min..max month)"),
  "month":       ("X-derived", "", "", "month-name string, redundant with date - §8.7", ""),
  "amount":      ("meas", f"{V2}; {V3}; {V4}", "payment_amount; receipt_amount", "", "CASHBOOK basis"),
 },
 "admin_approval": {
  "row_id":                     ("X-id", "", "", "source row identifier (declared as the PK)", ""),
  "gp_lgd_code":                ("join", V2, "", "", "attributes sanctions to a GP in view2"),
  "gp_name":                    ("X-derived", "", "", "denormalised; joins use codes - §8.9", ""),
  "plan_year":                  ("temp", f"{V1}; {V3}", "", "", "'YYYY' -> 'YYYY-YYYY'; equals planned_activity.fiscal_year on all 2,101 rows"),
  "doc_type":                   ("X-id", "", "", "ingestion provenance", ""),
  "source_file":                ("X-id", "", "", "ingestion provenance", ""),
  "activity_code":              ("join", "", "", "the approval-to-activity link", ""),
  "work_plan_year":             ("X-derived", "", "", "identical to plan_year on every row", ""),
  "adm_approval_no":            ("X-id", "", "", "document number - §9.6", ""),
  "adm_approval_sanction_date": ("temp", V2, "month; quarter; fiscal_year", "", "attributes sanctions to a month; one value is future-dated (§8.2). NOT projected by view1 - §4.1 carries no temporal dimension"),
  "work_proposed_cost":         ("meas", f"{V1}; {V2}; {V3}", "work_proposed_cost; work_proposed_amount", "", "SANCTIONED basis"),
  "adm_approval_authority":     ("join", V1, "sanction_authority", "", "free text consumed into authority_clean; the raw form never leaves derived_columns.sql - §9.6"),
 },
 "admin_approval_scheme": {
  "row_id":                  ("X-id", "", "", "source row identifier (declared as the PK)", ""),
  "parent_row_id":           ("X-id", "", "", "link to admin_approval.row_id", ""),
  "pos":                     ("X-id", "", "", "position within the parent record", ""),
  "activity_code":           ("join", "", "", "6 duplicates - the multi-scheme approvals the ARG_MAX rollup collapses", ""),
  "scheme_code":             ("decode-dim", V1, "sanctioned_scheme_name", "", "ARG_MAX by fund_sanctioned_total"),
  "scheme_component_code":   ("decode-dim", V1, "fund_component_name; tied_untied", "", "4249 Tied / 4211+4250 Untied / else Other"),
  "fund_sanctioned_general": ("meas", V1, "fund_sanctioned_general", "", ""),
  "fund_sanctioned_sc":      ("meas", V1, "fund_sanctioned_sc", "", "₹0.44M sample-wide - thin (§4.4)"),
  "fund_sanctioned_st":      ("meas", V1, "fund_sanctioned_st", "", "₹3.23M sample-wide - thin (§4.4)"),
  "fund_sanctioned_total":   ("meas", f"{V1}; {V2}; {V3}; {V4}", "fund_sanctioned_total; sanctioned_amount; sanctioned_total; overspend_vs_sanction", "", "SANCTIONED basis, headline measure"),
 },
 "technical_approval": {
  "row_id":                 ("X-id", "", "", "source row identifier (declared as the PK)", ""),
  "gp_lgd_code":            ("join", "", "", "FK-checked; geography comes from the activity", ""),
  "gp_name":                ("X-derived", "", "", "denormalised - §8.9", ""),
  "plan_year":              ("X-derived", "", "", "redundant with the activity's fiscal year", ""),
  "doc_type":               ("X-id", "", "", "ingestion provenance", ""),
  "source_file":            ("X-id", "", "", "ingestion provenance", ""),
  "activity_code":          ("join", "", "", "joined onto the ADMIN approval, as v_approval does", ""),
  "tec_approval_required":  ("dim", V1, "tec_approval_required", "", "CHECK 5 asserts [R, N]"),
  "tec_approval_cost":      ("meas", V1, "tec_approval_cost", "", "SANCTIONED basis"),
  "tec_approval_authority": ("join", "", "", "free text, excluded - §9.6", ""),
  "tec_approval_order_no":  ("X-id", "", "", "document number - §9.6", ""),
  "tec_approval_order_date":("temp", "", "", "view1 carries no temporal dimension (§4.1)", "CHECK 6 reads it via stg_technical_approval"),
 },
 "activity_fund": {
  "activity_code":                 ("join", "", "", "1:1 with planned_activity", ""),
  "fund_scheme_code":              ("decode-dim", V1, "planned_fund_scheme_name", "", "sparse candidate (44% populated) - staged, sample configs omit it (§9.7)"),
  "fund_component_code":           ("decode-dim", V1, "planned_fund_component_name", "", "sparse candidate (44% populated) - staged, sample configs omit it (§9.7)"),
  "fund_tied_general":             ("meas", V1, "fund_tied_general; fund_tied_total", "", ""),
  "fund_tied_sc":                  ("meas", V1, "fund_tied_sc; fund_tied_total", "", ""),
  "fund_tied_st":                  ("meas", V1, "fund_tied_st; fund_tied_total", "", ""),
  "fund_untied_general":           ("meas", V1, "fund_untied_general; fund_untied_total", "", ""),
  "fund_untied_sc":                ("meas", V1, "fund_untied_sc; fund_untied_total", "", ""),
  "fund_untied_st":                ("meas", V1, "fund_untied_st; fund_untied_total", "", ""),
  "fund_amount_total":             ("meas", "", "", "identical to planned_activity.total_cost in aggregate (₹773,088,536) and per activity; view1 carries total_cost", "the reconciliation identity of §3"),
  "fund_tied_abandoned_general":   ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_tied_abandoned_sc":        ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_tied_abandoned_st":        ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_untied_abandoned_general": ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_untied_abandoned_sc":      ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_untied_abandoned_st":      ("meas", V1, "fund_abandoned_total", "", ""),
  "fund_overflow_json":            ("X-empty", "", "", "2 non-null rows: multi-scheme funding squeezed into one row; the 1:1 fold loses that split for exactly 2 activities - accepted, §8.8", ""),
 },
 "activity_asset": {
  "activity_code":            ("join", "", "", "1:1 with planned_activity", ""),
  "main_asset_category":      ("X-sparse", "", "", "90.9% null - too sparse for v1, revisit statewide", ""),
  "main_asset_subcategory":   ("X-sparse", "", "", "89.7% null - too sparse for v1, revisit statewide", ""),
  "main_asset_unit_type":     ("X-sparse", "", "", "89.7% null - too sparse for v1", ""),
  "main_asset_unit_count":    ("X-sparse", "", "", "89.7% null - too sparse for v1", ""),
  "asset_type":               ("decode-dim", V1, "asset_type_label", "", "decoded with v_asset's double cast"),
  "asset_category":           ("decode-dim", V1, "asset_category_label", "", "decoded with v_asset's double cast"),
  "asset_subcategory":        ("X-sparse", "", "", "66.3% null and 198 codes, 56 without a description - too sparse for v1 (§7, §9.7)", ""),
  "asset_coverage_code":      ("X-const", "", "", "single value across every populated row", ""),
  "asset_name":               ("X-empty", "", "", "100% null", ""),
  "asset_unit_type":          ("X-sparse", "", "", "66.3% null - too sparse for v1", ""),
  "asset_unit_count":         ("X-sparse", "", "", "66.3% null - too sparse for v1", ""),
  "asset_unit_cost":          ("meas", V1, "asset_unit_cost", "", "candidate measure, 30.2% populated (§7)"),
  "asset_parameter_type":     ("X-sparse", "", "", "71.5% null, 193 codes, 74 without a description", ""),
  "asset_details_raw":        ("X-empty", "", "", "100% null", ""),
  "asset_loc_code":           ("X-sparse", "", "", "66.3% null - too sparse for v1", ""),
  "asset_loc_unit_code":      ("X-empty", "", "", "100% null", ""),
  "asset_loc_unit_type":      ("X-empty", "", "", "100% null", ""),
  "asset_loc_unit_count":     ("X-sparse", "", "", "66.3% null - too sparse for v1", ""),
  "asset_loc_unit_cost_total":("X-empty", "", "", "100% null", ""),
  "asset_loc_overflow_json":  ("X-empty", "", "", "99.6% null (54 rows) - §7 records it as X-empty; measured non-zero in WP-D1", ""),
 },
 "activity_training": {
  "activity_code":           ("join", "", "", "1:1 with planned_activity", ""),
  "training_capacity_raw":   ("X-empty", "", "", "100% null", ""),
  "training_category_code":  ("decode-dim", V1, "training_category_label", "", "sparse candidate (8.1% populated) - staged, sample configs omit it (§9.7)"),
  "training_organiser_code": ("decode-dim", V1, "training_organiser_label", "", "sparse candidate (8.1% populated) - staged, sample configs omit it (§9.7)"),
  "training_subject":        ("X-id", "", "", "free text - §9.6", ""),
  "training_trainees_total": ("meas", V1, "trainees_total", "", "127,588 trainees across 1,034 activities"),
  "training_duration_days":  ("meas", V1, "training_days", "", ""),
 },
 "activity_community_service": {
  "activity_code":                    ("join", "", "", "1:1 with planned_activity", ""),
  "community_service_raw":            ("X-empty", "", "", "100% null", ""),
  "community_service_code":           ("decode-dim", V1, "community_service_label", "", "sparse candidate (6.0% populated), no dim_code descriptions - staged, sample configs omit it (§9.7)"),
  "community_service_duration":       ("meas", V1, "community_service_days", "", ""),
  "community_beneficiaries_expected": ("meas", V1, "beneficiaries_expected", "", "206,929 expected beneficiaries across 763 activities"),
 },
 "activity_delegation": {
  "activity_code":             ("join", "", "", "1:1 with planned_activity; the table feeds nothing", ""),
  "is_delegated":              ("X-empty", "", "", "100% null", ""),
  "delegated_unit_code":       ("X-empty", "", "", "100% null", ""),
  "delegated_unit_type":       ("X-empty", "", "", "100% null", ""),
  "delegated_unit_level":      ("X-empty", "", "", "100% null", ""),
  "delegated_unit_category":   ("X-empty", "", "", "100% null", ""),
  "is_shareable":              ("X-const", "", "", "constant False where populated (11,289 rows), null elsewhere", ""),
  "delegated_parent_unit_code":("X-empty", "", "", "100% null", ""),
 },
 "activity_nsap": {
  "nsap_id":           ("X-empty", "", "", "table has zero rows", "the evidence for 'no equity view in v1' - §4.4"),
  "activity_code":     ("X-empty", "", "", "table has zero rows", ""),
  "category":          ("X-empty", "", "", "table has zero rows", ""),
  "age_band":          ("X-empty", "", "", "table has zero rows", ""),
  "gender":            ("X-empty", "", "", "table has zero rows", ""),
  "beneficiary_count": ("X-empty", "", "", "table has zero rows", ""),
 },
 "physical_progress": {
  "row_id":              ("X-id", "", "", "source row identifier (declared as the PK)", ""),
  "parent_row_id":       ("X-id", "", "", "link to the parent record", ""),
  "pos":                 ("X-id", "", "", "position within the parent record", ""),
  "activity_code":       ("join", "", "", "the evidence-to-activity link", ""),
  "file_upload_id":      ("meas", f"{V1}; {V3}; {V4}", "evidence_uploads; n_with_evidence; has_progress_evidence", "", "counted, never exposed: 8,267 uploads on 1,675 activities"),
  "longitude":           ("X-id", "", "", "evidence coordinate; Ask's v_progress serves it", ""),
  "latitude":            ("X-id", "", "", "evidence coordinate; Ask's v_progress serves it", ""),
  "n_coords":            ("X-id", "", "", "coordinate-list length", ""),
  "longitude_raw":       ("X-id", "", "", "comma-joined coordinate LIST, not a scalar - stays VARCHAR", ""),
  "latitude_raw":        ("X-id", "", "", "comma-joined coordinate LIST, not a scalar - stays VARCHAR", ""),
  "plan_unit_type_code": ("X-const", "", "", "single value across all 8,267 rows", ""),
 },
 "dim_code": {
  "variable":    ("decode", V1, "", "", "half of the composite decode key"),
  "code":        ("decode", V1, "", "", "half of the composite decode key"),
  "description": ("decode", V1, "focus_area_name; status_label; work_type_label; activity_type_label; activity_for_label; output_type_label; asset_category_label; asset_type_label; sanctioned_scheme_name; fund_component_name; planned_fund_scheme_name; planned_fund_component_name; training_category_label; training_organiser_label; community_service_label", "", "233 of 717 codes have none -> 'Code N' / 'Unknown' / 'Uncategorised' labels reach findings (§8.5)"),
  "source":      ("X-id", "", "", "decode provenance", "drives the §8.5 logging"),
  "confidence":  ("X-id", "", "", "decode provenance", "drives the §8.5 logging"),
 },
 "dim_lsdg_theme": {
  "focus_area_name": ("decode", V1, "", "", "joins to dim_code.description, not to a code"),
  "lsdg_theme":      ("decode", V1, "theme", "", "'Theme 5 - Clean and Green Village ' carries a trailing space - logged, NOT trimmed (§8)"),
  "distinct_themes": ("X-derived", "", "", "profiling artefact of the source extract", ""),
  "n_rows":          ("X-derived", "", "", "profiling artefact of the source extract", ""),
 },
 "dim_welfare_scheme": {
  "scheme_code": ("decode", "", "", "referenced by no populated column in this drop - welfare tagging arrives with NSAP data, if ever (§7)", ""),
  "scheme_name": ("decode", "", "", "referenced by no populated column in this drop", ""),
 },

 # ═══ WP-D11 / Amendment B §12.2 ═══════════════════════════════════════════
 # The GP profile: 99 columns, one row per Gram Panchayat, self-reported. Seven
 # of these columns become the derived bands that ride ALL FOUR views; the
 # counts become view4's profile measure family; the rest are excluded, and the
 # exclusion is the point of the two tables below it -- 4 X-pii on an operator
 # ruling, 22 X-sparse, 10 X-derived geography duplicates, 4 X-const, 3 X-multi,
 # 1 X-unreliable, and 4 the signed spec does not place at all (X-deferred).
 "gp_profile": {
  # ── the spine ────────────────────────────────────────────────────────────
  "basic_info_lgd": ("join", ALL4, "", "", "the profile spine: = gram_panchayat.gp_lgd_code, 1:1 on all 20 rows, zero orphans either side. Cast to VARCHAR in stg_gp_profile so the join matches the master's type"),

  # ── X-derived: the master is authoritative for geography (§12.2) ─────────
  "param__label1":      ("X-derived", "", "", "geography duplicated from the master - never re-projected", ""),
  "param__label11":     ("X-derived", "", "", "geography duplicated from the master - never re-projected", ""),
  "param__label111":    ("X-derived", "", "", "geography duplicated from the master - never re-projected", ""),
  "param__bp_name":     ("X-derived", "", "", "block name; the master's block_name is authoritative", ""),
  "param__zp_name":     ("X-derived", "", "", "district name; the master's zp_name -> district_name is authoritative", ""),
  "param__gp_name":     ("X-derived", "", "", "GP name; the master's gp_name is authoritative", ""),
  "basic_info_block":   ("X-derived", "", "", "geography duplicated from the master", ""),
  "basic_info_district":("X-derived", "", "", "geography duplicated from the master", ""),
  "basic_info_state":   ("X-derived", "", "", "geography duplicated from the master; constant in this drop", ""),
  "basic_info_village": ("X-derived", "", "", "sub-GP geography the master does not carry and no view is grained on", ""),

  # ── X-const ──────────────────────────────────────────────────────────────
  "param__localbodytypecode":                 ("X-const", "", "", "single value across all 20 rows", ""),
  "param__stateid":                           ("X-const", "", "", "single value across all 20 rows (Odisha only)", "staged for statewide continuity"),
  "demographic_details_transgender_population":("X-const", "", "", "0 on all 20 rows", "a reporting property, not a population fact - logged in WPD11_REPORT §8"),
  "basic_amenities_no_of_computer":           ("X-const", "", "", "1 on all 18 non-null rows while laptop/printer/scanner counts vary - a form default (§12.6.15)", "the other three equipment counts ARE projected"),

  # ── X-pii: operator ruling, needed for nothing (§12.2) ───────────────────
  # The fifth crosswalk gate check asserts that none of these four names
  # appears in ANY view's output columns.
  "basic_info_email_address": ("X-pii", "", "", "personal contact data; operator ruling 2026-09-07 - reaches no view", ""),
  "basic_info_mobile":        ("X-pii", "", "", "personal contact data (already masked 977XXX7120 at source); operator ruling - reaches no view", ""),
  "basic_info_address":       ("X-pii", "", "", "personal/premises address; operator ruling - reaches no view", ""),
  "basic_info_gp_attractions":("X-pii", "", "", "free text describing places and people; operator ruling - reaches no view", ""),

  # ── X-multi: comma-separated multi-value strings, deferred (§12.2) ───────
  "basic_amenities_alternate_source_of_water_in_gram_panchayat_bhawan":  ("X-multi", "", "", "comma-separated multi-value string; not a dimension without an unnest - deferred", ""),
  "basic_amenities_sources_of_internet_in_gram_panchayat_bhawan":        ("X-multi", "", "", "comma-separated multi-value string; not a dimension without an unnest - deferred", ""),
  "basic_amenities_sources_of_power_supply_in_gram_panchayat_bhawan":    ("X-multi", "", "", "comma-separated multi-value string; not a dimension without an unnest - deferred", ""),

  # ── X-unreliable ─────────────────────────────────────────────────────────
  "panchayat_area_total_area": ("X-unreliable", "", "", "1.11 to 3,000 across 20 GPs with no consistent unit - three values are two orders of magnitude off the rest (§12.6.10). No band is built on it", "cast float in sources.yaml: the cast records what the column claims to be"),

  # ── X-sparse: staged, unused in v1, statewide candidates (§12.2) ─────────
  "basic_amenities_common_service_centre_situated_in": ("X-sparse", "", "", "free text, 9 of 20 rows populated - too sparse and too free-form for v1", ""),
  "basic_amenities_location_of_common_service_centre": ("X-sparse", "", "", "12 of 20 rows populated - too sparse for v1", ""),
  "basic_amenities_types_of_connection":               ("X-sparse", "", "", "11 of 20 rows populated - too sparse for v1", ""),
  "panchayat_learning_centre_details_award_name":                                             ("X-sparse", "", "", "PLC detail: populated only where a learning centre exists (1 of 20)", ""),
  "panchayat_learning_centre_details_biometric_devices":                                      ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_do_the_plc_contribute_in_generating_gp_own_source_revenue":("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_funding_information":                                    ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_gp_received_any_award":                                  ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_internet_wi_fi_availability":                            ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_library_facility":                                       ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_meeting_room_available":                                 ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_number_of_computers_laptops":                            ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", "carries the literal 'NA' token on the other 18 - left uncast in sources.yaml"),
  "panchayat_learning_centre_details_other_digital_tools":                                    ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_panchayat_manuals_handbooks":                            ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_plc_located_in_panchayat_office_premises":               ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_printers_scanners":                                      ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_projector_smart_tv":                                     ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_seating_capacity":                                       ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", "carries the literal 'NA' token on the other 18 - left uncast in sources.yaml"),
  "panchayat_learning_centre_details_sound_system":                                           ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_success_stories_documented":                             ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_vc_facility_available":                                  ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", ""),
  "panchayat_learning_centre_details_year_of_establishment":                                  ("X-sparse", "", "", "PLC detail: populated on the 2 GPs with a learning centre", "carries the literal 'NA' token on the other 18 - left uncast in sources.yaml"),

  # ── X-deferred: NOT ASSIGNED A ROLE BY §12.2 AND NOT LISTED BY §12.4 ─────
  # Four columns fall through both of Amendment B's tables. §12.2 assigns
  # "every remaining count" the meas role but then enumerates the counts, and
  # the enumeration omits the destitute-homes column; the three yes/no amenity
  # attributes below are neither counts nor among §12.3's six derived
  # dimensions. Rather than invent a role or a view4 column the signed spec
  # does not carry, they are held out of every view and raised as a proposed
  # amendment in WPD11_REPORT §9. All four are fully populated and are live
  # statewide candidates.
  "general_no_of_destitue_homes_old_age_homes": ("X-deferred", "", "", "not in §12.4's view4 column list; §12.6.14 records that the column mixes a count of homes with a count of residents (values 0, 1, 110), so its meaning is not settled - see WPD11_REPORT §9", ""),
  "basic_amenities_panchayat_library":          ("X-deferred", "", "", "yes/no attribute; not among §12.3's six derived dimensions and not in §12.4's column list - see WPD11_REPORT §9", "fully populated; a dimension candidate"),
  "basic_amenities_availability_of_renewable_source_of_energy_in_gram_panchayat_bhawan":   ("X-deferred", "", "", "yes/no attribute; not among §12.3's six derived dimensions and not in §12.4's column list - see WPD11_REPORT §9", "fully populated; a dimension candidate"),
  "basic_amenities_availability_of_rooftop_rainwater_harvesting_system_in_gram_panchayat_bhawan": ("X-deferred", "", "", "yes/no attribute; not among §12.3's six derived dimensions and not in §12.4's column list - see WPD11_REPORT §9", "fully populated; a dimension candidate"),

  # ── dim: the seven derived bands' sources (§12.3) ────────────────────────
  # Three of these are ALSO view4 measures; the crosswalk gives a column one
  # role, so the role is `dim` (the band is the reason the column is staged)
  # and output_columns names the band AND the measure it feeds.
  "demographic_details_total_gender_wise_population": ("dim", ALL4, "gp_size; social_composition; population_total", "", "the population cuts 2,500 / 5,000 / 10,000 (lower bound inclusive) and the denominator of the ST/SC majority test; sample split 2 / 9 / 7 / 2"),
  "demographic_details_st_population":                ("dim", ALL4, "social_composition; population_st", "", "ST share > 50% -> ST-majority. 2 of 20; Kalimela is the only GP near the cut at 50.9%"),
  "demographic_details_sc_population":                ("dim", ALL4, "social_composition; population_sc", "", "SC share > 50% -> SC-majority where ST is not; 3 of 20"),
  "basic_info_distance_from_nearest_bus_stop":        ("dim", ALL4, "remoteness", "", "km to the nearest bus stop, cut at 5: under 5 Near, 5 or more Far; 14 / 6. Itipur and Hirlipali report exactly 5 and are therefore Far"),
  "basic_amenities_internet_service_available_in_panchayat_bhawan":                       ("dim", ALL4, "digital_readiness", "", "internet AND computer both Yes -> Ready; 10 / 10"),
  "basic_amenities_computer_laptop_printers_scanner_etc_availability_in_panchayat_bhawan":("dim", ALL4, "digital_readiness", "", "the second half of the AND; Boipariguda has internet and no computer and is therefore Not ready"),
  "basic_amenities_panchayat_bhawan":                 ("dim", ALL4, "has_panchayat_bhawan", "", "as reported; 14 Yes / 6 No"),
  "basic_amenities_is_common_service_centre_available_in_panchayat": ("dim", ALL4, "has_csc", "", "as reported; 12 Yes / 8 No"),
  "panchayat_learning_centre_details_panchayat_learning_centre_available": ("dim", ALL4, "plc_available", "", "18 No / 2 Yes - materialised on every view, MINED STATEWIDE ONLY (§12.3), the §9.7 sparse-dimension shape"),

  # ── meas: the view4 profile measure family (§12.4), view4 only ───────────
  # None of these reaches views 1-3: a GP constant summed once per activity,
  # once per month or once per fiscal year is a wrong denominator (§12.4).
  "demographic_details_male_population":     ("meas", V4, "population_male", "", ""),
  "demographic_details_female_population":   ("meas", V4, "population_female", "", "male + female = total on all 20 rows (§12.1)"),
  "demographic_details_children_population": ("meas", V4, "population_children", "", "0 in 9 of 20 GPs - plausible for some, unlikely for all (§12.6.13)"),
  "demographic_details_obc_population":      ("meas", V4, "population_obc", "", ""),
  "demographic_details_general_population":  ("meas", V4, "population_general", "", "general + obc + sc + st = total on all 20 rows (§12.1)"),
  "general_no_of_households":               ("meas", V4, "households", "", "26,132 sample-wide. Karuabahal reports 12 against 3,208 people (§12.6.11) - never a denominator in this pack"),
  "general_no_of_job_card_holders":         ("meas", V4, "job_card_holders", "", ""),
  "general_no_of_shg":                      ("meas", V4, "shgs", "", ""),
  "general_no_of_anganwadi_centers":        ("meas", V4, "anganwadi_centres", "", ""),
  "education_total_pre_primary_schools":    ("meas", V4, "schools_pre_primary", "", ""),
  "education_total_primary_schools":        ("meas", V4, "schools_primary", "", ""),
  "education_total_secondary_schools":      ("meas", V4, "schools_secondary", "", ""),
  "education_total_higher_secondary_schools":("meas", V4, "schools_higher_secondary", "", ""),
  "health_no_of_health_sub_centers":        ("meas", V4, "health_sub_centres", "", ""),
  "health_no_of_primary_health_centers":    ("meas", V4, "primary_health_centres", "", ""),
  "health_no_of_well_being_centers":        ("meas", V4, "wellbeing_centres", "", ""),
  "health_no_of_dispensary":                ("meas", V4, "dispensaries", "", ""),
  "health_no_of_ayurvedic_clinics":         ("meas", V4, "ayurvedic_clinics", "", ""),
  "infrastructure_no_of_drinking_water_sources":            ("meas", V4, "drinking_water_sources", "", ""),
  "infrastructure_no_of_households_connected_to_tap_water": ("meas", V4, "households_tap_water", "", "exceeds households in 2 GPs, Chikilli and Haldikudar (§12.6.12) - a count, never a materialised coverage rate"),
  "infrastructure_no_of_household_toilets":                 ("meas", V4, "household_toilets", "", "exceeds households in 5 GPs (§12.6.12) - a count, never a materialised coverage rate"),
  "infrastructure_no_of_community_sanitary_complexes":      ("meas", V4, "community_sanitary_complexes", "", ""),
  "infrastructure_no_of_solid_waste_managements_centers":   ("meas", V4, "solid_waste_centres", "", ""),
  "infrastructure_no_of_common_service_centers":            ("meas", V4, "common_service_centres", "", "the COUNT; the yes/no availability flag is the has_csc dimension"),
  "infrastructure_no_of_banks_cooperative_banks":           ("meas", V4, "banks", "", ""),
  "infrastructure_no_of_atms":                              ("meas", V4, "atms", "", ""),
  "infrastructure_no_of_rural_library":                     ("meas", V4, "rural_libraries", "", ""),
  "infrastructure_no_of_children_parks":                    ("meas", V4, "children_parks", "", ""),
  "infrastructure_no_of_disaster_rescue_centers":           ("meas", V4, "disaster_rescue_centres", "", ""),
  "infrastructure_no_of_bus_stands_with_drinking_water_facility": ("meas", V4, "bus_stands_with_water", "", ""),
  "infrastructure_no_of_cooperative_seed_centers":          ("meas", V4, "seed_centres", "", ""),
  "panchayat_area_no_of_wards_sansads_of_the_panchayat":    ("meas", V4, "wards", "", ""),
  "panchayat_area_no_of_revenue_villages":                  ("meas", V4, "revenue_villages", "", ""),
  "panchayat_area_no_of_villages_mapped_with_lgd":          ("meas", V4, "villages_mapped_lgd", "", ""),
  "basic_amenities_osr_collected_so_far":   ("meas", V4, "osr_collected", "", "own-source revenue to date, rupees. NOT one of §3's four money bases and never totalled alongside them"),
  "basic_amenities_no_of_laptop":           ("meas", V4, "laptops", "", "carries the literal 'NA' on 2 rows: cast behind NULLIF in derived_columns.sql, then zero-filled at view4's grid, so 'none' and 'not reported' are indistinguishable in the view"),
  "basic_amenities_no_of_printer":          ("meas", V4, "printers", "", "same 'NA' handling as no_of_laptop, same 2 rows"),
  "basic_amenities_no_of_scanner":          ("meas", V4, "scanners", "", "same 'NA' handling as no_of_laptop, same 2 rows"),
  "sports_no_of_badminton_court":           ("meas", V4, "sports_courts", "", "the three disciplines are summed into one count (§12.4)"),
  "sports_no_of_football_court":            ("meas", V4, "sports_courts", "", "the three disciplines are summed into one count (§12.4)"),
  "sports_no_of_volleyball_court":          ("meas", V4, "sports_courts", "", "the three disciplines are summed into one count (§12.4)"),
 },
}

rows, problems = [], []
for table, colspec in SPEC.items():
    reader = f"read_csv('{D}/{table}.csv', all_varchar=true, header=true)"
    actual = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {reader}").fetchall()]
    total = con.execute(f"SELECT count(*) FROM {reader}").fetchone()[0]
    missing = set(actual) - set(colspec)
    extra = set(colspec) - set(actual)
    if missing:
        problems.append(f"{table}: columns in CSV but not in SPEC: {sorted(missing)}")
    if extra:
        problems.append(f"{table}: columns in SPEC but not in CSV: {sorted(extra)}")
    for col in actual:
        role, views, outs, reason, note = colspec[col]
        if total:
            nn, nd = con.execute(
                f'SELECT count("{col}"), count(DISTINCT "{col}") FROM {reader}').fetchone()
            fill, dist = round(nn / total * 100, 1), nd
        else:
            fill, dist = 0.0, 0
        rows.append({
            "table": table, "column": col, "role": role,
            "cast": CASTS.get(table, {}).get(col, "varchar"),
            "used_in_views": views, "output_columns": outs,
            "fill_pct": fill, "n_distinct": dist,
            "exclusion_reason": reason, "note": note,
        })

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["table", "column", "role", "cast", "used_in_views",
                                       "output_columns", "fill_pct", "n_distinct",
                                       "exclusion_reason", "note"])
    w.writeheader()
    w.writerows(rows)

print(f"wrote {OUT}: {len(rows)} column rows across {len(SPEC)} tables")

# ── gate checks ────────────────────────────────────────────────────────────
print("\n--- GATE: crosswalk vs the built Parquet views")
view_cols = {}
for v in VIEWS:
    view_cols[v] = [c[0] for c in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{V}/{v}.parquet')").fetchall()]

# 1. no X-* role may name an output column
leaks = [r for r in rows if r["role"].startswith("X-") and r["output_columns"]]
print(f"  X-* roles naming an output column: {len(leaks)} {[ (l['table'],l['column']) for l in leaks ]}")

# 2. every output_columns entry must exist in the view(s) it claims
bad = []
for r in rows:
    if not r["output_columns"]:
        continue
    claimed_views = [v.strip() for v in r["used_in_views"].split(";") if v.strip()]
    for oc in [o.strip() for o in r["output_columns"].split(";") if o.strip()]:
        if not any(oc in view_cols[v] for v in claimed_views):
            bad.append((r["table"], r["column"], oc, claimed_views))
print(f"  output_columns not found in their claimed view: {len(bad)} {bad}")

# 3. every view column must be claimed by at least one non-X source column
claimed = set()
for r in rows:
    if r["role"].startswith("X-"):
        continue
    claimed |= {o.strip() for o in r["output_columns"].split(";") if o.strip()}
DERIVED_ONLY = {  # grid / flag columns with no single source column
    "n_activities", "n_costed", "n_costless", "n_plans", "n_admin_approvals",
    "n_tech_approvals", "n_completed", "n_ongoing", "n_abandoned",
    "is_started", "is_completed", "is_ongoing", "is_abandoned", "is_under_approval",
    "is_admin_approved", "has_approval_cost_only", "has_technical_approval",
    "sanction_scheme_rows", "payment_count", "receipt_count", "sanctions_count",
}
for v in VIEWS:
    unclaimed = [c for c in view_cols[v] if c not in claimed and c not in DERIVED_ONLY]
    print(f"  {v}: {len(view_cols[v])} columns, unclaimed (non-derived): {unclaimed}")

# 5. NO X-pii COLUMN NAME MAY APPEAR IN ANY VIEW'S OUTPUT COLUMNS (WP-D11).
# Operator ruling of 2026-09-07: email, mobile, address and gp_attractions are
# needed for nothing. Check 1 above asserts that this FILE claims no output for
# them; this check reads the BUILT views instead, so a column that reached a
# Parquet under its own name would be caught even if the crosswalk had been
# edited to look innocent.
pii = [r["column"] for r in rows if r["role"] == "X-pii"]
pii_leaks = [(v, c) for v in VIEWS for c in pii if c in view_cols[v]]
print(f"  X-pii column names found in a view schema: {len(pii_leaks)} {pii_leaks}"
      + ("" if not pii_leaks else "   <-- GATE FAILURE"))
print(f"    (checked {len(pii)} X-pii columns against {len(VIEWS)} views: {pii})")

print("\n--- SPEC integrity")
for p in problems:
    print("  PROBLEM:", p)
if not problems:
    print("  every CSV column has exactly one crosswalk row; no phantom rows")
print(f"  total staged columns: {len(rows)}")

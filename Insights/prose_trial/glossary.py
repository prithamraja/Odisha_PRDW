#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) T1 -- one-line variable definitions for the packets.

Source: the SIGNED glossary -- handoffs/WPD2_mining_calibration.md Appendix A
(the PM-authored VIEW_DESCRIPTIONS / column_glossary content, transcribed
verbatim into Insights/src/phase5b_report.py) and the domain-pack crosswalk
(Insights/domain_pack_prdw/crosswalk.csv). Units are cross-checked against
phase5b_report._UNITS, which is the table that actually formats every figure.

WHAT THESE ARE. A definition says what a variable IS: its unit, its money basis
(planned / sanctioned / spent / cashbook), its sign convention where it is
signed, and what the values are. Two "what the values are" facts the brief names
explicitly are carried here: output-type codes have no descriptions on file, and
"Uncategorised" means no asset category was recorded.

WHAT THESE ARE NOT. A definition never says how much to trust a variable
(brief T1: "Definitions say what a variable IS, never how much to trust it").
The glossary's coverage and skew sentences -- "an activity without one is not
shown to be unapproved", "a near-zero here is data coverage, not a finding",
"completion is near-degenerate" -- are trust statements and are deliberately
NOT transcribed. Neither is any caution or scope note (operator ruling,
2026-08-31: no caution layer of any kind).
"""

PROVENANCE = ("signed glossary: handoffs/WPD2_mining_calibration.md Appendix A "
              "(= phase5b_report.VIEW_DESCRIPTIONS column_glossary); units "
              "cross-checked against phase5b_report._UNITS")

# --------------------------------------------------------------------------
# Measures. Keyed (view, measure): a name can mean different things by view.
# --------------------------------------------------------------------------
MEASURES = {
    ("view1", "overspend_vs_plan"):
        "rupees, totalled, SIGNED (money spent minus money planned). A positive "
        "figure is spending above the plan; a negative figure is planned money "
        "not spent.",
    ("view3", "overspend_vs_plan"):
        "rupees, totalled, SIGNED (money spent minus money planned), aggregated "
        "per Gram Panchayat per year. Positive is spending above the plan; "
        "negative is planned money not spent.",
    ("view1", "overspend_vs_sanction"):
        "rupees, totalled, SIGNED (money spent minus money sanctioned). Positive "
        "is spending above the sanctioned amount; negative is sanctioned money "
        "not spent. It exists only where a sanction record exists.",
    ("view3", "overspend_vs_sanction"):
        "rupees, totalled, SIGNED (money spent minus money sanctioned), "
        "aggregated per Gram Panchayat per year.",
    ("view1", "fund_untied_total"):
        "rupees, totalled, PLANNED basis -- the untied part of the planned "
        "funding. Untied is the discretionary grant (components 4211 and 4250), "
        "as against the tied grant, which is earmarked (component 4249).",
    ("view1", "fund_tied_total"):
        "rupees, totalled, PLANNED basis -- the tied, earmarked part of the "
        "planned funding (component 4249).",
    ("view1", "total_cost"):
        "rupees, totalled, PLANNED basis -- the action-plan cost. Empty for "
        "costless activities.",
    ("view1", "total_expenditure"):
        "rupees, totalled, SPENT basis -- voucher-linked actual spending.",
    ("view1", "n_activities"):
        "activities, counted -- one per planned activity.",
    ("view3", "n_activities"):
        "activities, counted -- one per planned activity, per Gram Panchayat "
        "per year.",
    ("view1", "gen_amount"):
        "rupees, totalled, SPENT basis -- voucher-linked spending recorded "
        "against the General social-category component (the other two "
        "components are SC and ST).",
    ("view1", "beneficiaries_expected"):
        "people, totalled -- the beneficiaries an activity records as expected. "
        "Recorded by the activities that carry community-service detail, 763 of "
        "them in this sample.",
    ("view1", "trainees_total"):
        "people, totalled -- recorded by the 1,034 activities that carry "
        "training detail.",
    ("view1", "evidence_uploads"):
        "geotagged photo uploads, counted -- 8,267 uploads across 1,675 "
        "activities in this sample.",
    ("view3", "evidence_uploads"):
        "geotagged photo uploads, counted, per Gram Panchayat per year.",
    ("view2", "activity_linked_expenditure"):
        "rupees, totalled, SPENT basis -- the part of the month's cashbook "
        "payments that is linked to a planned activity.",
    ("view2", "payment_count"):
        "vouchers, counted, CASHBOOK basis -- every payment voucher the Gram "
        "Panchayat recorded in the month, whether or not it is tied to a "
        "planned activity.",
    ("view2", "payment_amount"):
        "rupees, totalled, CASHBOOK basis -- all outflows recorded in the month.",
    ("view2", "receipt_amount"):
        "rupees, totalled, CASHBOOK basis -- all inflows recorded in the month.",
    ("view2", "receipt_count"):
        "vouchers, counted, CASHBOOK basis -- inflow vouchers recorded in the "
        "month.",
    ("view2", "sanctioned_amount"):
        "rupees, totalled, SANCTIONED basis, counted by the month the sanction "
        "is dated.",
    ("view2", "sanctions_count"):
        "sanctions, counted, by the month the sanction is dated.",
    ("view3", "sanctioned_total"):
        "rupees, totalled, SANCTIONED basis -- the approval amounts recorded "
        "for a Gram Panchayat in a fiscal year.",
    ("view3", "planned_cost"):
        "rupees, totalled, PLANNED basis, per Gram Panchayat per year.",
    ("view3", "expenditure_total"):
        "rupees, totalled, SPENT basis, per Gram Panchayat per year.",
    ("view3", "n_admin_approvals"):
        "sanction records, counted -- administrative approvals per Gram "
        "Panchayat per year.",
    ("view3", "n_tech_approvals"):
        "sanction records, counted -- technical approvals per Gram Panchayat "
        "per year.",
}

# --------------------------------------------------------------------------
# Dimensions: breakdowns, extending dimensions, and filter dimensions.
# --------------------------------------------------------------------------
DIMENSIONS = {
    "gp_name": "the Gram Panchayat, from the LGD-coded government roster. 20 of them in this sample.",
    "block_name": "the Block, from the LGD-coded government roster. 16 of them in this sample.",
    "district_name": "the District, from the LGD-coded government roster. 9 of them in this sample.",
    "fiscal_year": "the April-to-March year, written in full, for example 2024-2025. Six years run from 2020-2021 to 2025-2026.",
    "quarter": "the calendar quarter, for example 2024-Q1.",
    "month": "the calendar month, for example 2024-03.",
    "temporal_grain": "which time unit the pattern was measured over: month, quarter or fiscal year. Its three values are the three time units, not places or categories.",
    "theme": "the LSDG theme the activity's focus area maps to. 6 themes; 'Unmapped theme' means the focus area has no theme mapping on file.",
    "focus_area_name": "the plan's focus area: 30 values, such as roads, drinking water, sanitation and education.",
    "asset_category_label": "the asset the work creates. 27 named categories reach this view; 'Uncategorised' means no asset category was recorded against the work, and is not itself a kind of asset.",
    "status_label": "the activity's current recorded status. The values are Activity Approved, WORK ONGOING, WORK ABANDONED, UNDER APPROVAL and WORK COMPLETED; 'Buildings' is a known mis-coding on 13 rows.",
    "output_type_label": "the activity's output-type code. No output-type code has a description on file, so every value reads 'Code 101' through 'Code 110' -- eight codes with nothing recorded about what they contain.",
    "work_type_label": "the decoded kind of work, 4 values; 'Unknown' means the code has no decode on file.",
    "activity_type_label": "the decoded kind of activity, 2 values.",
    "activity_for_label": "the decoded purpose the activity is for, 4 values.",
    "is_costless": "whether the activity was planned with a cost ('Costed') or without one ('Costless' -- training, campaigns and services).",
    "tied_untied": "whether the sanctioned grant is Tied (earmarked, component 4249) or Untied (discretionary, components 4211 and 4250); 'Other' is any other component.",
    "sanction_authority": "the sanctioning office, cleaned of spelling variants: Sarpanch, BDO, Engineer, Gram Panchayat, Panchayat Samiti, plus ten low-count free-text residues -- 14 distinct values in all.",
    "sanctioned_scheme_name": "the scheme behind the sanction; 'Code N' means the code has no description on file.",
    "fund_component_name": "the funding component behind the sanction; 'Code N' means the code has no description on file.",
    "planned_fund_scheme_name": "the scheme behind the planned funding; 'Code N' means the code has no description on file.",
    "planned_fund_component_name": "the component behind the planned funding; 'Code N' means the code has no description on file.",
}

VIEW_ROW = {
    "view1": "one row per planned activity -- 12,704 activities planned by the 20 Gram Panchayats between 2020-2021 and 2025-2026.",
    "view2": "one row per Gram Panchayat per calendar month -- 1,440 rows covering April 2020 to March 2026, months with no transactions included as zeros.",
    "view3": "one row per Gram Panchayat per fiscal year -- 120 rows, all 20 Gram Panchayats across all 6 years, including years with nothing recorded.",
}


def measure_definition(view, measure):
    """One line saying what the measure IS, or None if the glossary has none."""
    if measure == "(varies)":
        return ("this finding compares several measures at once, so it carries "
                "no single unit of its own.")
    return MEASURES.get((view, measure))


def dimension_definition(dim):
    """One line saying what the dimension IS, or None if the glossary has none."""
    if dim == "(varies)":
        return ("this finding compares several breakdowns at once rather than "
                "one fixed breakdown.")
    return DIMENSIONS.get(dim)

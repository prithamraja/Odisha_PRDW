# =============================================================================
# Phase 5b: Executive MetaInsight Report (LLM-Generated)
# =============================================================================
# Takes ranked MetaInsight candidates from Phase 5 and uses Claude to
# generate a readable executive report for a state-level PM-JAY programme
# officer. The LLM translates already-validated structured findings into
# clear prose -- it does not re-analyse data or exercise analytical judgment.
#
# Inputs:
#   metainsights/view{1-9}_ranked.json
#
# Outputs:
#   reports/executive_metainsight_report.md
#
# Run from project root:
#   python src/phase5b_report.py
# =============================================================================

import os
import sys
import ast
import json

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase4a_engine import (
    VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG, VIEW4_CONFIG, VIEW5_CONFIG,
    VIEW6_CONFIG, VIEW7_CONFIG, VIEW8_CONFIG, VIEW9_CONFIG,
    ViewConfig,
)
from discover_config import DISCOVER_PROSE_MODEL, DISCOVER_MAX_COMPLETION_TOKENS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# view name -> its config. Module-level because the feed prompt needs to ask a
# measure's aggregation type outside main()'s local scope.
VIEW_CONFIGS = {
    "view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG,
    "view4": VIEW4_CONFIG, "view5": VIEW5_CONFIG, "view6": VIEW6_CONFIG,
    "view7": VIEW7_CONFIG, "view8": VIEW8_CONFIG, "view9": VIEW9_CONFIG,
}


# =============================================================================
# STEP 0: NUMBER FORMATTING
# =============================================================================
# Iteration 1 produced three arithmetic/style defects in the prose, all of the
# same kind: the model was handed bare floats and asked to render them. It
# called ₹20.25 crore "202.5 crore" (a factor-of-ten slip on a conversion it
# should never have been doing), and it used Indian digit grouping in one
# section and Western grouping in the other three.
#
# The fix is to stop asking. Every number that reaches the prompt is rendered
# here, once, in one style, with its unit attached; the prompt then forbids
# converting or re-deriving anything. The model's job is to choose which
# figures to quote and to explain them — not to do arithmetic.
#
# "Rs" rather than the ₹ glyph: the PDF is typeset by ReportLab in Helvetica,
# whose WinAnsi encoding has no U+20B9, so the glyph would drop out of the
# deliverable. "Rs" is standard Indian usage and survives both renderers.

def _indian_group(digits: str) -> str:
    """Group an integer digit string the Indian way: 12,34,567 not 1,234,567."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _num(x: float, decimals: int = 0) -> str:
    """A number in Indian digit grouping, with a fixed number of decimals."""
    sign = "-" if x < 0 else ""
    s = f"{abs(x):.{decimals}f}"
    whole, _, frac = s.partition(".")
    out = sign + _indian_group(whole)
    return f"{out}.{frac}" if frac else out


def _rupees(x: float) -> str:
    """Rupees, in crore or lakh from one lakh upwards, plain below that."""
    a = abs(x)
    if a >= 1e7:
        return f"Rs {_num(x / 1e7, 2)} crore"
    if a >= 1e5:
        return f"Rs {_num(x / 1e5, 2)} lakh"
    return f"Rs {_num(x, 0)}"


# unit -> renderer. `_UNITS` below assigns one to every measure of every view,
# so no measure can reach the prompt as a bare number.
_FORMATTERS = {
    "rupees":    _rupees,
    "farmers":   lambda x: f"{_num(x, 0)} farmers",
    "records":   lambda x: f"{_num(x, 0)} records",
    "payments":  lambda x: f"{_num(x, 0)} payments",
    "sanctions": lambda x: f"{_num(x, 0)} sanctions",
    "txns":      lambda x: f"{_num(x, 0)} transactions",
    "acres":     lambda x: f"{_num(x, 1)} acres",
    "quintals":  lambda x: f"{_num(x, 1)} quintals",
    "schemes":   lambda x: f"{_num(x, 2)} programmes",
    "share":     lambda x: f"{_num(x * 100, 1)}%",
    "index":     lambda x: _num(x, 2),
}

_UNITS = {
    "view1": {
        "benefit_amount": "rupees", "benefit_amount_mean": "rupees",
        "land_acres": "acres", "benefit_count": "payments",
    },
    "view2": {
        "scheme_count": "schemes",
        "in_pm_kisan": "farmers", "in_agriculture": "farmers",
        "in_horticulture": "farmers", "in_fisheries": "farmers",
        "in_sericulture": "farmers", "in_markfed": "farmers",
        "in_ryss": "farmers",
        "ekyc_pending_rate": "share",
        "total_benefit_amount": "rupees", "land_acres": "acres",
        "land_acres_mean": "acres",
        "farmer_count": "farmers",
    },
    "view3": {
        "subsidyamount": "rupees", "subsidy_mean": "rupees",
        "nonsubsidyamount": "rupees", "record_count": "records",
    },
    "view4": {
        "amount_paid": "rupees", "amount_paid_mean": "rupees",
        "procured_qty": "quintals", "unpaid_count": "txns",
        "unpaid_share": "share", "txn_count": "txns",
    },
    "view5": {
        "population": "farmers", "enrolled": "farmers",
        "coverage_rate": "share", "rupees_per_capita": "rupees",
        "representation_index": "index", "land_share_index": "index",
    },
    "view6": {
        "subsidy_amt": "rupees", "subsidy_amt_mean": "rupees",
        "balance_to_release": "rupees", "released_amount": "rupees",
        "release_rate": "share", "stalled_flag": "share",
        "beneficiary_count": "sanctions",
    },
    "view7": {
        "input_subsidy": "rupees", "procured_qty": "quintals",
        "procurement_value": "rupees", "realization_ratio": "index",
        "land_acres": "acres", "farmer_count": "farmers",
    },
    "view8": {
        "declared_acres": "acres", "recorded_acres": "acres",
        "discrepancy_ratio": "index", "over_declared_flag": "share",
        "farmer_count": "farmers",
    },
    "view9": {
        "benefit_share": "share", "total_benefit": "rupees",
    },
}


def format_measure(view_name: str, measure: str, value: float) -> str:
    """Render one measured value for one view's measure, unit included."""
    unit = _UNITS.get(view_name, {}).get(measure)
    return _FORMATTERS.get(unit, lambda x: _num(x, 2))(float(value))


# =============================================================================
# STEP 1: VIEW DESCRIPTIONS
# =============================================================================

# Shared vocabulary. Every AP view carries the same thirteen districts and the
# same four social categories, so the definitions are written once and merged
# into each view's glossary.
_DISTRICTS = (
    "One of the thirteen districts of Andhra Pradesh used across the RTGS "
    "datasets: Srikakulam, Vizianagaram, Visakhapatnam, East Godavari, "
    "West Godavari, Krishna, Guntur, Prakasam, Nellore, YSR Kadapa, Kurnool, "
    "Anantapur and Chittoor. Always name the district in full; never use a code."
)
_CATEGORY = (
    "Social category of the farmer: SC (Scheduled Caste), ST (Scheduled Tribe), "
    "BC (Backward Class), OC (Other Caste, i.e. not reserved). Write the full "
    "name on first use."
)
_SEASON = (
    "Cropping season: Kharif is the monsoon season (roughly June to October) and "
    "Rabi is the winter season (roughly November to March). Spell both out on "
    "first use."
)

# A stated fact, established by the build and carried into the prose as
# context. It is NOT a mined finding and must not be presented as one: it is
# the reason the farmer view counts 1,100 farmers rather than 1,140.
#
# The writer is told this so that it does not contradict it. It is NOT asked to
# restate it: the restatement is the deterministic reading note below, appended
# to the section after the model has written. See READING_NOTES.
_OFF_ROSTER = (
    "Coverage note, established by the data build rather than by the analysis: "
    "40 farmers draw benefits from a state programme while having no PM-KISAN "
    "record at all - 26 of them in Sericulture (Rs 2.61 lakh), 20 in Fisheries "
    "(Rs 7.51 lakh) and 16 in RySS Rythu Sadhikara (Rs 2.23 lakh); some appear "
    "in more than one. Because nothing is known about them beyond the "
    "programme record - no district, no social category, no landholding - they "
    "are counted here as a coverage gap and are not carried into the farmer "
    "figures. Do not write this out as a note of your own and do not describe "
    "it as a pattern that was discovered: the section already carries a "
    "reading note that states it."
)


# =============================================================================
# READING NOTES -- deterministic, not LLM-authored
# =============================================================================
# Methodology caveats are fixed content. They were previously left to the model,
# which meant the wording of the PM-KISAN denominator assumption and of the
# 40-farmer coverage gap changed from run to run -- and a caveat is exactly
# where a paraphrase does the most damage (an earlier gamma suite invented a
# "Telangana-style procurement" clause out of nothing).
#
# So they are emitted here, verbatim, and appended to the view's section after
# the model's text. The marker is the contract the Discover feed parses against:
# a blockquote whose first line opens with READING_NOTE_MARKER. Everything from
# that line to the end of the blockquote is the note; the feed renders it as a
# callout, not as a finding, and excludes it from its row and chip counts.
#
# If this marker changes, change it in the frontend parser too --
# frontend/ab-dashboard-main/src/lib/insights-report.ts, READING_NOTE_MARKER.

READING_NOTE_MARKER = "> **Reading note:**"

_COVERAGE_GAP = (
    "The data build also found **40 farmers** drawing at least one "
    "state-programme benefit with no PM-KISAN record at all -- **26** in "
    "Sericulture, **20** in Fisheries and **16** in RySS Rythu Sadhikara, some "
    "in more than one. Nothing is known about them beyond the programme record "
    "-- no district, no social category, no landholding -- so they are counted "
    "as a coverage gap and are not carried into the per-farmer figures here."
)

# One entry per view whose figures rest on an assumption the reader has to be
# told about. A view with no entry gets no note and no blockquote.
READING_NOTES = {
    "view2": (
        "this view has one row for each of the **1,100 farmers on the PM-KISAN "
        "roster**, so every per-farmer figure below is per roster farmer, not "
        "per farmer in the full farming population. Tenant farmers and landless "
        "agricultural workers are not on the roster. " + _COVERAGE_GAP
    ),
    "view5": (
        "these figures are **per farmer on the PM-KISAN roster**, not per farmer "
        "in the full farming population. PM-KISAN is the denominator because it "
        "is close to universal among landholding farmers, but tenant farmers and "
        "landless agricultural workers are outside this base, and they are among "
        "the groups an equity review most wants counted. " + _COVERAGE_GAP
    ),
    "view9": (
        "each district's seven shares add to 100 per cent, so this view says how "
        "a district's money was **divided**, never how much it received. Rupees "
        "are attributed to the farmer's PM-KISAN district, which keeps the money "
        "and the people in the same place but means the base is the **PM-KISAN "
        "roster**: tenant farmers and landless agricultural workers are outside "
        "it. " + _COVERAGE_GAP
    ),
}


def reading_note_block(view_name: str) -> str:
    """The view's reading note as a markdown blockquote, or "" if it has none.

    One line, so the marker and the note body cannot be separated. Returned with
    a leading blank line so it concatenates straight onto the model's text.
    """
    note = READING_NOTES.get(view_name)
    if not note:
        return ""
    return f"\n\n{READING_NOTE_MARKER} {note}\n"


# =============================================================================
# VIEW VOCABULARY -- what each view's pipeline is NOT
# =============================================================================
# Every view has its own pipeline and its own words for it. view4 is MARKFED
# procurement: crop is delivered and the farmer is paid or not. view6 is the
# horticulture subsidy: money is sanctioned, then released, and a file that has
# released almost nothing is stalled. Neither view holds the other's columns,
# so neither may borrow the other's words -- the gamma 0.5 report of 2026-07-30
# called a horticulture release stall "the payment hold-up", which is about real
# figures and still sends an officer to the wrong pipeline.
#
# The lists are deliberately narrow: a term appears only where the view has no
# column it could honestly describe. "Unpaid balance" is NOT listed for view6 --
# money sanctioned and not released is unpaid in plain English, and denying it
# would be a style preference rather than a correctness rule.
#
# Used twice: told to the writer by vocabulary_rule() below, and checked in the
# finished report by src/prose_gate.py. Add a view here and both ends pick it up.

VIEW_VOCABULARY = {
    "view4": {
        "pipeline": "procurement -- crop is delivered and the farmer is paid or not",
        "deny": [
            (r"\bsanction(?:s|ed|ing)?\b", "view6's sanction/release pipeline"),
            (r"\brelease rate\b",          "view6's release_rate measure"),
            (r"\bstalled?\b",              "view6's stalled_flag measure"),
            (r"\bbalance to release\b",    "view6's balance_to_release measure"),
            (r"\bmicro-?irrigation\b",     "the Horticulture APMIP programme"),
            (r"\bAPMIP\b",                 "the Horticulture APMIP programme"),
        ],
    },
    "view6": {
        "pipeline": ("subsidy -- money is sanctioned, then released, and a file "
                     "that has released almost nothing is stalled"),
        "deny": [
            (r"\bpayment hold[- ]?up\b",   "view4's payment backlog framing"),
            (r"\bprocure(?:d|ment)\b",     "view4's procurement pipeline"),
            (r"\bquintals?\b",             "view4's procured_qty unit"),
            (r"\bMARKFED\b",               "the MARKFED procurement programme"),
        ],
    },
}

# The prose forms of the denied patterns, for the prompt. A regex is the right
# thing to check with and the wrong thing to show a writer.
_DENIED_PHRASES = {
    "view4": ["sanction", "sanctioned", "release rate", "stalled",
              "balance to release", "micro-irrigation", "APMIP"],
    "view6": ["payment hold-up", "procurement", "procured", "quintals",
              "MARKFED"],
}


def vocabulary_rule(view_name: str, label: str) -> str:
    """The view's vocabulary constraint as a numbered prompt rule.

    Empty for a view with no entry, so it drops out of the prompt cleanly.
    `label` is the rule number to file it under, which differs between the two
    generators' instruction lists.
    """
    rules = VIEW_VOCABULARY.get(view_name)
    if not rules:
        return ""
    denied = ", ".join(f'"{phrase}"' for phrase in _DENIED_PHRASES[view_name])
    return (
        f"""{label}. VOCABULARY FOR THIS VIEW. This view's pipeline is {rules['pipeline']}. Another view in the same report covers the other pipeline, and its words do not describe anything here.
   - These words are BANNED in this section, in headlines and in bullets alike: {denied}
   - They are banned because this view has no column they could describe, not as a matter of style. A reader who meets them here is sent to the wrong programme and the wrong office
   - Use the words the Column Glossary above uses for the columns you are quoting

"""
    )


# The counterpart instruction: the writer must not produce its own version of
# what reading_note_block already appends. Shared by both report generators so
# the two prompts cannot drift apart on it.
NO_METHODOLOGY_NOTE_RULE = """DO NOT WRITE A METHODOLOGY NOTE. Where this section needs one, it is appended after your text from a fixed source, word for word, every run. Yours would duplicate it and could paraphrase it wrongly, and a caveat is the worst place in the report for a paraphrase.
   - Write no "Reading note", "Note on the data", "Coverage note", "Caveat", "Assumption", "Limitation", "Methodology" or "How to read this" block, under any heading and in any position
   - Do not open or close the section by explaining what the figures are per, which population is behind them, who is missing from it, or how the view was built. Say it inside a finding if a finding turns on it, and not otherwise
   - The base and its limits are given to you above so that you do not contradict them, not so that you can restate them
   - Write findings only"""

VIEW_DESCRIPTIONS = {
    "view1": {
        "title": "Scheme Benefits Across the Seven Programmes",
        "description": (
            "This view brings together 5,818 individual benefit records from the seven "
            "Andhra Pradesh farmer programmes that pay money to farmers: PM-KISAN income "
            "support, Agriculture input subsidy, Horticulture APMIP micro-irrigation "
            "subsidy, Fisheries assistance, Sericulture incentive, MARKFED procurement "
            "payment and RySS Rythu Sadhikara support. Each row is one payment or "
            "sanction to one farmer under one programme, with the district, the farmer's "
            "gender and social category, the current processing status, the amount in "
            "rupees and the land behind the claim in acres. It covers all thirteen "
            "districts. A further 26 Sericulture records are excluded because the farmer "
            "could not be matched to the PM-KISAN roster, so no social category is on "
            "file for them. Season and crop year are deliberately not in this view: only "
            "some of the seven programmes record either, so a comparison across them "
            "would be comparing programmes rather than seasons or years. Those questions "
            "are answered by the Agriculture register and the procurement view, where "
            "every row carries a real season and a real date."
        ),
        "audience_context": (
            "Key questions for the programme officer: Which programmes carry the most "
            "money, and is that spread evenly across districts? Do farmers of every "
            "social category receive comparable amounts, and where do they not? Which "
            "districts and which programmes have the most claims sitting unapproved?"
        ),
        "column_glossary": {
            "scheme": (
                "The programme the payment came from. Seven values: PM-KISAN (central "
                "income support, a fixed instalment per farmer), Agriculture Input "
                "Subsidy (seed and input subsidy), Horticulture APMIP (micro-irrigation "
                "subsidy), Fisheries (fisheries assistance), Sericulture (mulberry and "
                "cocoon incentive), MARKFED Procurement (payment for crop bought at the "
                "procurement centre) and RySS Rythu Sadhikara (natural-farming support)."
            ),
            "district": _DISTRICTS,
            "gender": "Male or Female, as recorded on the farmer's programme record.",
            "category": _CATEGORY,
            "status": (
                "Where the record currently sits in its programme's workflow: Approved, "
                "Pending or Under Review for the payment-bearing programmes; Completed or "
                "Pending for PM-KISAN eKYC verification; and Damaged, which only the "
                "Agriculture crop register uses, for a crop reported destroyed."
            ),
            "benefit_amount": (
                "UNIT: rupees (INR), TOTALLED across benefit records. An absolute "
                "figure - it rises with the number of records in the group, so a large "
                "total for a large group is not by itself a finding."
            ),
            "benefit_amount_mean": (
                "UNIT: rupees (INR), AVERAGED per benefit record. The same rupee column "
                "as benefit_amount, normalised by record count: the typical size of one "
                "payment, independent of how many payments the group received."
            ),
            "land_acres": (
                "UNIT: acres, TOTALLED. Land behind the benefit. PM-KISAN records land "
                "in hectares; it is converted here (1 hectare = 2.471 acres) so every "
                "programme is on the same unit."
            ),
            "benefit_count": (
                "UNIT: benefit records, COUNTED - one per payment or sanction."
            ),
        },
    },
    "view2": {
        "title": "Farmer 360 - One Row Per Farmer",
        "description": (
            "This view has one row for each of the 1,100 farmers on the PM-KISAN roster. "
            "It shows which programmes each farmer is enrolled in, how many programmes "
            "that is in total, the rupees they have received across all of them, their "
            "landholding both as a group total and as acres per farmer, and their "
            "district, gender, social category, eKYC status and PM-KISAN beneficiary "
            "status. It is the view for equity and coverage questions: who is reached "
            "by many programmes and who by only one. "
            + _OFF_ROSTER
        ),
        "audience_context": (
            "Key questions: Are small and marginal farmers reached by as many programmes "
            "as large farmers? Are any districts or social categories systematically "
            "enrolled in fewer programmes? Where is eKYC verification lagging, which "
            "blocks payment?"
        ),
        "column_glossary": {
            "district": _DISTRICTS,
            "gender": "Male or Female.",
            "category": _CATEGORY,
            "ekyc_status": (
                "PM-KISAN electronic-KYC verification: Completed or Pending. A farmer "
                "whose eKYC is Pending cannot be paid the next instalment, so this is an "
                "operational blockage, not a paperwork detail."
            ),
            "beneficiary_status": (
                "PM-KISAN eligibility decision: Included (eligible and on the payment "
                "list), Excluded (found ineligible) or Pending (still being decided)."
            ),
            "land_size_class": (
                "Standard Indian landholding class, computed from the farmer's PM-KISAN "
                "holding in HECTARES: Marginal (<1 ha), Small (1-2 ha), Semi-medium "
                "(2-4 ha), Medium (4-10 ha), Large (>10 ha). No farmer in this data "
                "reaches the Large class."
            ),
            "scheme_count": (
                "UNIT: programmes per farmer, AVERAGED across the farmers in the group. "
                "How many of the seven programmes a farmer is enrolled in, from 1 to 7, "
                "so '2.50 programmes' means farmers in that group are enrolled in two "
                "and a half programmes each on average. A per-farmer figure: it does not "
                "grow with the size of the group."
            ),
            "in_pm_kisan": "UNIT: farmers, COUNTED - those in the group enrolled in PM-KISAN.",
            "in_agriculture": "UNIT: farmers, COUNTED - those with an Agriculture input-subsidy record.",
            "in_horticulture": "UNIT: farmers, COUNTED - those in the Horticulture APMIP programme.",
            "in_fisheries": "UNIT: farmers, COUNTED - those in the Fisheries programme.",
            "in_sericulture": "UNIT: farmers, COUNTED - those in the Sericulture programme.",
            "in_markfed": "UNIT: farmers, COUNTED - those who sold to MARKFED.",
            "in_ryss": "UNIT: farmers, COUNTED - those in RySS Rythu Sadhikara.",
            "ekyc_pending_rate": (
                "UNIT: percentage of the group's farmers whose eKYC verification is "
                "still pending. A RATE, not a count: it does not grow with the size of "
                "the group, so a small district and a large one can be compared "
                "directly. Read '27.9%' as 'in this group, 27.9 farmers in every hundred "
                "cannot be paid their next instalment until eKYC clears'."
            ),
            "total_benefit_amount": (
                "UNIT: rupees (INR), TOTALLED across the group. What these farmers have "
                "received across all seven programmes combined. An absolute figure - it "
                "grows with the number of farmers in the group."
            ),
            "land_acres": (
                "UNIT: acres, TOTALLED - the group's landholding. An absolute figure, "
                "and one that is easy to misread: it grows with the number of farmers "
                "in the group, so the largest social category holds the most acres for "
                "the same reason it has the most farmers. That is a fact about group "
                "SIZE, not about how land is distributed. Never present a totalled "
                "acreage as though it showed one community holding more land than "
                "another; for that question use land_acres_mean, which is per farmer."
            ),
            "land_acres_mean": (
                "UNIT: acres, AVERAGED PER FARMER. The same land column as land_acres, "
                "divided by how many farmers are in the group: the typical holding of "
                "one farmer. A per-farmer figure - it does not grow with the size of "
                "the group, so a large community and a small one are directly "
                "comparable. This is the measure that answers 'do farmers in this "
                "group hold more land than farmers in that one'."
            ),
            "farmer_count": "UNIT: farmers, COUNTED - one per row.",
        },
    },
    "view3": {
        "title": "Agriculture Input-Subsidy Register",
        "description": (
            "This view holds 961 input-subsidy registrations in the Agriculture "
            "programme, one row per registration. Each row names the crop, the season, "
            "the district, the crop's current status, the farmer's social category and "
            "whether they own or rent the land, the crop year, the government subsidy "
            "in rupees and the farmer's own contribution in rupees. It covers the three "
            "complete crop years 2023, 2024 and 2025. The 153 registrations dated 2026 "
            "are excluded: the data stops on 31 July 2026, so 2026 is a part year and "
            "including it would make every crop appear to be falling. Year-on-year "
            "comparisons here are therefore complete year against complete year."
        ),
        "audience_context": (
            "Key questions: Which crops absorb the most subsidy, and has that shifted "
            "between 2023 and 2025? Is the subsidy per registration consistent across "
            "districts and crops, or are there pockets paying far more? Where are "
            "registrations stuck unapproved or reported damaged?"
        ),
        "column_glossary": {
            "cropnameeng": (
                "The crop registered for input subsidy. Ten crops: Paddy, Groundnut, "
                "Chilli, Blackgram, Bengalgram, Tobacco, Sugarcane, Turmeric, Cotton "
                "and Maize."
            ),
            "season": _SEASON,
            "district": _DISTRICTS,
            "cropstatus": (
                "Where the registration sits: Approved, Pending, Under Review, or "
                "Damaged - the last meaning the standing crop was reported destroyed."
            ),
            "social_status": _CATEGORY,
            "cultivator_type": (
                "Owner (the farmer holds the land title) or Tenant (the farmer rents it). "
                "Tenants are usually the harder group to reach with entitlements."
            ),
            "cropyear": (
                "Crop year of the registration: 2023, 2024 or 2025. All three are "
                "complete years."
            ),
            "subsidyamount": (
                "UNIT: rupees (INR), TOTALLED across registrations. Government input "
                "subsidy. An absolute figure - it grows with the number of "
                "registrations in the group."
            ),
            "subsidy_mean": (
                "UNIT: rupees (INR), AVERAGED per registration. The same rupee column "
                "as subsidyamount, normalised by registration count: the typical "
                "sanction size. A high average against a low total means a small number "
                "of unusually large sanctions, which is what an audit would look for."
            ),
            "nonsubsidyamount": (
                "UNIT: rupees (INR), TOTALLED. The farmer's own contribution towards "
                "the same inputs."
            ),
            "record_count": "UNIT: registrations, COUNTED - one per row.",
        },
    },
    "view4": {
        "title": "MARKFED Procurement",
        "description": (
            "This view holds the 1,086 MARKFED procurement transactions, one row per "
            "purchase from a farmer at a procurement centre. Each row names the crop, "
            "the district, the season, the farmer's gender and social category, the "
            "payment status, the month and year of procurement (August 2023 to July "
            "2026), the quantity bought in quintals and the rupees paid."
        ),
        "audience_context": (
            "Key questions: Which crops and districts dominate procurement value, and "
            "does that match the cropping pattern on the ground? Where are payments to "
            "farmers not getting made? Is procurement volume rising or falling, and is "
            "there a seasonal shape to it?"
        ),
        "column_glossary": {
            "crop_name": (
                "The commodity procured. Ten crops: Paddy, Groundnut, Chilli, Blackgram, "
                "Bengalgram, Tobacco, Sugarcane, Turmeric, Cotton and Maize."
            ),
            "district": _DISTRICTS,
            "season": _SEASON,
            "gender": "Male or Female, as recorded on the farmer's procurement record.",
            "caste": _CATEGORY,
            "payment_status": (
                "Whether MARKFED has paid the farmer: Approved (payment cleared), Pending "
                "(not yet processed) or Under Review (held for checking). Anything other "
                "than Approved means the farmer has delivered the crop but not been paid."
            ),
            "proc_month": (
                "Month of procurement as YYYY-MM, from August 2023 to July 2026. Note "
                "that August 2023 and July 2026 are the ends of the record, so the "
                "first and last months carry less volume for that reason alone."
            ),
            "amount_paid": (
                "UNIT: rupees (INR), TOTALLED across transactions. Paid to farmers. An "
                "absolute figure - it grows with the number of transactions."
            ),
            "amount_paid_mean": (
                "UNIT: rupees (INR), AVERAGED per transaction. The same rupee column as "
                "amount_paid, normalised by transaction count: the typical size of one "
                "purchase from one farmer."
            ),
            "procured_qty": (
                "UNIT: quintals (1 quintal = 100 kg), TOTALLED. Quantity bought."
            ),
            "unpaid_count": (
                "UNIT: transactions, COUNTED - those whose payment status is not "
                "Approved, i.e. crop delivered but money not yet released. An absolute "
                "figure: a large district can show a high count simply by being large."
            ),
            "unpaid_share": (
                "UNIT: percentage of the group's transactions still unpaid. The same "
                "information as unpaid_count but NORMALISED by transaction volume, so "
                "districts of different sizes can be compared directly. Read '35.0%' as "
                "'35 in every hundred deliveries in this group are still awaiting "
                "payment'. This is the fair measure of a payment backlog; unpaid_count "
                "is the fair measure of how many farmers are affected."
            ),
            "txn_count": "UNIT: transactions, COUNTED - one per row.",
        },
    },
    "view5": {
        "title": "Equity Cube - Reach in Proportion to Population",
        "description": (
            "This view answers a different question from the others, and it is worth "
            "being clear about which. Every other view measures totals: how many rupees, "
            "how many records. Totals cannot answer 'is this community being reached "
            "fairly', because a community that is 6 per cent of farmers will always show "
            "the smallest total - that is arithmetic, not a finding. This view therefore "
            "carries only PROPORTIONAL measures. It has one row for each combination of "
            "district, social category and state programme - thirteen districts by four "
            "social categories by the six Andhra Pradesh programmes (Agriculture input "
            "subsidy, Horticulture APMIP, Fisheries, Sericulture, MARKFED procurement "
            "and RySS Rythu Sadhikara), 312 rows in all. Each row states how many "
            "farmers of that community live in that district, how many of them the "
            "programme reached, what share that is, how many rupees per farmer it "
            "delivered, whether the community's share of the district's money matches "
            "its share of the district's farmers, and whether its share of the "
            "district's land does the same.\n\n"
            "IMPORTANT ASSUMPTION, which the section's reading note states for you -- "
            "do not write it out again: the population base is the PM-KISAN roster. "
            "PM-KISAN is close to "
            "universal among landholding farmers, which is what makes it usable as a "
            "denominator, but it is not the farming population. Tenant farmers and "
            "landless agricultural workers are not on it, and they are among the groups "
            "an equity review most wants counted. Every rate here therefore reads as "
            "'per roster farmer', not 'per farmer'. " + _OFF_ROSTER
        ),
        "audience_context": (
            "Key questions for the programme officer: Is each social category reached in "
            "proportion to its numbers, or does one consistently fall short? Does that "
            "differ by district, and by which programme? Where a community is enrolled "
            "at the same rate as everyone else but receives fewer rupees per head, the "
            "gap is in what they receive rather than in whether they are on the list, "
            "and that is a different remedy.\n\n"
            "SMALL NUMBERS: some cells are thin. Scheduled Tribe farmers number roughly "
            "five per district on the roster, so a Scheduled Tribe rate in a single "
            "district rests on a handful of people. The population figure is given for "
            "every finding precisely so this can be said out loud. When a finding rests "
            "on a small cell, quote the population alongside the rate and say that the "
            "district-level figure is indicative while the statewide one is firm."
        ),
        "column_glossary": {
            "district": _DISTRICTS,
            "category": _CATEGORY,
            "scheme": (
                "The state programme: Agriculture Input Subsidy (seed and input "
                "subsidy), Horticulture APMIP (micro-irrigation subsidy), Fisheries "
                "(fisheries assistance), Sericulture (mulberry and cocoon incentive), "
                "MARKFED Procurement (payment for crop bought at the procurement centre) "
                "or RySS Rythu Sadhikara (natural-farming support). PM-KISAN is not "
                "among them because it is the population base itself - its coverage is "
                "100 per cent by definition."
            ),
            "population": (
                "UNIT: farmers. THE BASE POPULATION OF THE CELL - NEVER ADDITIVE "
                "ACROSS PROGRAMMES. How many farmers of that social category are on "
                "the PM-KISAN roster in that district. This is the DENOMINATOR behind "
                "every rate in this view, and it is the number to quote when a rate "
                "rests on a small group. The same population is repeated against each "
                "of the six programmes because the same people are in all six rows, so "
                "adding it up across programmes counts every farmer six times: it would "
                "turn 498 Backward Class farmers into 2,988. The figure you are given "
                "is therefore AVERAGED, not totalled, and it is already the true number "
                "of farmers in the group however many programmes the group spans. Quote "
                "it as it is given and never add two of these figures together."
            ),
            "enrolled": (
                "UNIT: farmers, COUNTED. How many of that cell's roster farmers the "
                "programme actually reached."
            ),
            "coverage_rate": (
                "UNIT: percentage of the cell's roster farmers who are enrolled in that "
                "programme. Enrolled divided by population. A RATE - directly comparable "
                "between a large community and a small one. Read '58.1%' as '58 in every "
                "hundred roster farmers of this community in this district are on this "
                "programme'."
            ),
            "rupees_per_capita": (
                "UNIT: rupees (INR) PER ROSTER FARMER of the cell. The programme's total "
                "spending on that community in that district, divided by how many of "
                "them there are. This is what makes two communities of different sizes "
                "comparable: it answers 'how much reaches a typical member', not 'how "
                "much reaches the group'. Note it is per roster farmer including those "
                "the programme never reached, so it blends coverage and generosity."
            ),
            "representation_index": (
                "UNIT: a ratio, where 1.00 means parity. The community's share of the "
                "district's spending on that programme, divided by its share of the "
                "district's roster farmers. 1.00 means the community receives exactly "
                "its numerical share; 0.74 means it receives about three-quarters of "
                "what its numbers would give it; 1.20 means a fifth more. This is the "
                "single figure that answers 'is this fair in proportion', and it is the "
                "one to lead with. It says nothing about whether the total is large or "
                "small."
            ),
            "land_share_index": (
                "UNIT: a ratio, where 1.00 means proportional. NEVER ADDITIVE - see "
                "population, and treat this figure the same way. The community's share "
                "of the district's roster LAND, divided by its share of the district's "
                "roster farmers. 1.00 means the community holds exactly the acreage its "
                "numbers would give it; 0.80 means four-fifths of it; 1.20 a fifth "
                "more. It is the land counterpart of representation_index, and it "
                "exists because a totalled acreage cannot answer the land question at "
                "all: the largest community holds the most acres because it is the "
                "largest community. Because land belongs to the farmer and not to the "
                "programme, this figure is IDENTICAL across all six programmes for a "
                "given district and community - do not describe it as varying by "
                "programme, and never add two of these figures together. Read it "
                "against population: Scheduled Tribe farmers number roughly five per "
                "district, so a single district's figure rests on a handful of "
                "holdings. Quote the population whenever you quote a district-level "
                "value, and treat the statewide picture as the firm one."
            ),
        },
    },
    "view6": {
        "title": "Horticulture - From Sanction to Money in Hand",
        "description": (
            "This view holds all 567 micro-irrigation subsidy sanctions under the "
            "Horticulture APMIP programme, one row per sanction. It is the only place "
            "in this analysis where both halves of a payment are on record: what was "
            "SANCTIONED to the farmer, and how much of it has actually been RELEASED. "
            "Every other view can only see money that has already moved. Each row also "
            "carries the district, the farmer's gender and social category, the crop, "
            "the balance still to be released, and where the file currently sits.\n\n"
            "TWELVE DISTRICTS, NOT THIRTEEN. YSR Kadapa has no horticulture records in "
            "this data at all. It is absent from this view rather than showing zero, "
            "and it must not be described as a district that received nothing - the "
            "programme simply is not recorded here for it. Do not name it as a low "
            "performer, and do not count it among the districts compared."
        ),
        "audience_context": (
            "Key questions for the programme officer: where has money been sanctioned "
            "but not released, and how much is sitting there? Is the hold-up spread "
            "evenly or concentrated in particular districts? Do the sanctions that are "
            "stuck differ from the ones that cleared - by crop, by social category, by "
            "size of sanction? A sanction that has been approved on paper but has "
            "released nothing is a farmer who has been promised an irrigation system "
            "and does not have one."
        ),
        "column_glossary": {
            "district": _DISTRICTS + (
                " NOTE: only twelve of the thirteen appear in this view. YSR Kadapa "
                "has no horticulture records at all and is absent rather than zero."
            ),
            "gender": "Male or Female, as recorded on the sanction.",
            "category": _CATEGORY,
            "status": (
                "Where the sanction file currently sits: Approved, Pending or Under "
                "Review. In this programme the status tracks the money: a file that "
                "has released everything reads Approved, one that has released nothing "
                "reads Pending, and a part-released file reads Under Review."
            ),
            "crop": (
                "The horticulture crop the irrigation subsidy was sanctioned for. Ten "
                "crops: Paddy, Groundnut, Chilli, Blackgram, Bengalgram, Tobacco, "
                "Sugarcane, Turmeric, Cotton and Maize."
            ),
            "subsidy_amt": (
                "UNIT: rupees (INR), TOTALLED across sanctions. What was SANCTIONED - "
                "promised, not necessarily paid. An absolute figure that grows with "
                "the number of sanctions in the group."
            ),
            "subsidy_amt_mean": (
                "UNIT: rupees (INR), AVERAGED per sanction. The typical size of one "
                "micro-irrigation sanction, independent of how many there were."
            ),
            "balance_to_release": (
                "UNIT: rupees (INR), TOTALLED. Money sanctioned but still not released "
                "- the amount a farmer has been promised and has not received. This is "
                "the figure to quote when describing the size of a hold-up."
            ),
            "released_amount": (
                "UNIT: rupees (INR), TOTALLED. Money actually released. Released amount "
                "plus balance equals the sanctioned amount on every record."
            ),
            "release_rate": (
                "UNIT: percentage of each sanction's money that has been released, "
                "AVERAGED across the sanctions in the group. A RATE, so a district with "
                "few sanctions and one with many can be compared directly. Read '84.0%' "
                "as 'across these sanctions, an average of 84 paise in every rupee "
                "promised has reached the farmer'."
            ),
            "stalled_flag": (
                "UNIT: percentage of the group's sanctions that are STALLED, meaning "
                "90 per cent or more of the sanctioned money is still sitting. This is "
                "the hard end of a low release rate: not slow, but effectively not "
                "started. Read '55.0%' as 'more than half the sanctions in this group "
                "have had almost none of their money released'."
            ),
            "beneficiary_count": (
                "UNIT: sanctions, COUNTED - one per row, one per farmer."
            ),
        },
    },
    "view7": {
        "title": "From Input Subsidy to Market Realisation",
        "description": (
            "This view puts two programmes on one row per farmer: the input subsidy the "
            "state paid them to plant, and the money MARKFED paid them for what they "
            "harvested. It covers the 416 farmers who appear in both. That restriction "
            "is deliberate and it is the only honest scope - a farmer who took subsidy "
            "and never sold to MARKFED has no realisation to measure, and one who sold "
            "without subsidy has nothing to measure it against. Each row carries the "
            "district, social category, gender, crop, land-size class, the rupees in, "
            "the quintals and rupees back, and the ratio between them.\n\n"
            "WHAT THIS VIEW CANNOT SEE, and it matters. Crop is a property of the "
            "FARMER in this data, not of the individual record: the same farmer is "
            "recorded against the same crop in the subsidy register and at the "
            "procurement centre. So this view can say how much subsidy and how much "
            "realisation each crop's growers carry - that is real - but it can say "
            "NOTHING about farmers switching crop between the two programmes. Do not "
            "describe any finding here as farmers growing one thing and selling "
            "another; that question cannot be asked of this data."
        ),
        "audience_context": (
            "Key questions for the programme officer: for every rupee of input subsidy, "
            "how much crop value comes back through the procurement system, and does "
            "that differ by district? Where it is low, is that because farmers are "
            "selling elsewhere, because yields are poor, or because procurement is not "
            "reaching them - those are three different remedies and this view cannot "
            "tell them apart, so it is a question to take to the district rather than "
            "an answer. Are smaller farmers realising as much per rupee as larger ones?"
        ),
        "column_glossary": {
            "district": _DISTRICTS,
            "category": _CATEGORY,
            "gender": "Male or Female.",
            "crop": (
                "The crop this farmer is recorded against in both programmes. Ten "
                "crops: Paddy, Groundnut, Chilli, Blackgram, Bengalgram, Tobacco, "
                "Sugarcane, Turmeric, Cotton and Maize. See the note in the section "
                "description: this describes the intensity of subsidy and realisation "
                "among a crop's growers, never a switch between crops."
            ),
            "land_size_class": (
                "Standard Indian landholding class from the farmer's PM-KISAN holding: "
                "Marginal (<1 ha), Small (1-2 ha), Semi-medium (2-4 ha), Medium "
                "(4-10 ha). No farmer here reaches the Large class."
            ),
            "input_subsidy": (
                "UNIT: rupees (INR), TOTALLED. Agriculture input subsidy paid to these "
                "farmers - the money in. An absolute figure that grows with the number "
                "of farmers in the group."
            ),
            "procured_qty": (
                "UNIT: quintals (1 quintal = 100 kg), TOTALLED. Quantity these farmers "
                "sold to MARKFED."
            ),
            "procurement_value": (
                "UNIT: rupees (INR), TOTALLED. What MARKFED paid them for it - the "
                "money back. An absolute figure."
            ),
            "realization_ratio": (
                "UNIT: a ratio - rupees of procurement value per rupee of input "
                "subsidy, AVERAGED across the farmers in the group. This is the "
                "measure this view exists for. It is NORMALISED, so a large district "
                "and a small one are directly comparable, which the two rupee totals "
                "above are not. Read '24.90' as 'these farmers sold back about 25 "
                "rupees of crop for every rupee of input subsidy they received'. A low "
                "value means the subsidy is not converting into marketed produce "
                "through this channel; it does not by itself say why."
            ),
            "land_acres": "UNIT: acres, TOTALLED - the group's landholding.",
            "farmer_count": "UNIT: farmers, COUNTED - one per row.",
        },
    },
    "view8": {
        "title": "Declared Land Against the Revenue Record",
        "description": (
            "PM-KISAN pays on the land a farmer DECLARES. The revenue department holds "
            "a separate record of the land they are on the books for. This view puts "
            "the two side by side, one row for each of the 1,100 farmers on the roster, "
            "matched through their khata number. Where the two disagree, an entitlement "
            "is being computed from a figure nobody has checked against the record - "
            "and the larger figure is the one that pays. No other view can see this: "
            "every one of them reads the declared number.\n\n"
            "HOW THE MATCH WAS MADE, and its limit. On this data every farmer's khata "
            "number resolves to exactly one land record, and the village agrees on both "
            "sides in every case. That is a property of this dataset and not of land "
            "records in general: a real khata is village-scoped and covers joint "
            "holdings and several survey numbers, so one farmer can hold several "
            "parcels and one khata number can recur in different villages. State the "
            "findings here as what the two systems say about each other, not as proof "
            "of a farmer's true holding."
        ),
        "audience_context": (
            "Key questions for the programme officer: how many farmers are claiming "
            "more land than the revenue record shows, and where are they concentrated? "
            "Is the gap spread thinly across the state or does it sit in particular "
            "districts, which would point at a local process rather than at "
            "individuals? Does it fall differently across social categories or "
            "landholding sizes? A district where declarations routinely exceed the "
            "record is a verification question for the collector, not an accusation "
            "against any farmer: the record itself may be out of date."
        ),
        "column_glossary": {
            "district": _DISTRICTS,
            "category": _CATEGORY,
            "gender": "Male or Female.",
            "land_size_class": (
                "Standard Indian landholding class from the DECLARED PM-KISAN holding: "
                "Marginal (<1 ha), Small (1-2 ha), Semi-medium (2-4 ha), Medium "
                "(4-10 ha)."
            ),
            "declared_acres": (
                "UNIT: acres, TOTALLED. Land the farmer declares in PM-KISAN, converted "
                "from hectares (1 hectare = 2.471 acres). This is the figure the "
                "entitlement is computed from."
            ),
            "recorded_acres": (
                "UNIT: acres, TOTALLED. Land the revenue record carries against the "
                "same khata number."
            ),
            "discrepancy_ratio": (
                "UNIT: a ratio, where 1.00 means the two systems agree. Declared land "
                "divided by recorded land, AVERAGED across the farmers in the group. "
                "Above 1.00 the farmer claims more than the record shows; below 1.00 "
                "the record shows more than they claim. Only the first is an "
                "entitlement risk. Read '1.07' as 'on average these farmers declare "
                "about 7 per cent more land than the revenue record carries'."
            ),
            "over_declared_flag": (
                "UNIT: percentage of the group's farmers who declare MORE THAN 10 PER "
                "CENT above what the record shows. A RATE, comparable between a large "
                "district and a small one. The 10 per cent threshold is set clear of "
                "the rounding involved in converting hectares to acres, so a farmer "
                "counted here differs from the record by more than a unit conversion "
                "can explain."
            ),
            "farmer_count": "UNIT: farmers, COUNTED - one per row.",
        },
    },
    "view9": {
        "title": "How Each District's Money Is Split Between Programmes",
        "description": (
            "Every other view counts rupees. This one describes their SHAPE. It has "
            "one row for each of the thirteen districts crossed with each of the seven "
            "programmes - 91 rows - and each row says what share of that district's "
            "total benefit spending flowed through that programme. A district's seven "
            "shares always add to 100 per cent, so the view is a decomposition: it "
            "cannot say whether a district received a lot or a little, only how what it "
            "received was divided up.\n\n"
            "That is the question it exists to answer, and it is not answerable from "
            "the other views. Totals cannot answer it because a large district has "
            "large totals under every programme; per-farmer figures cannot answer it "
            "because most farmers draw on only one or two programmes and a mix needs at "
            "least two. The share is therefore computed once for each district and "
            "programme, at the level where every district has one.\n\n"
            "Rupees are attributed to the farmer's PM-KISAN district, so the money and "
            "the people are always counted in the same place. " + _OFF_ROSTER
        ),
        "audience_context": (
            "Key questions for the programme officer: which programmes actually carry a "
            "district's support, and where does that differ from the state pattern? A "
            "district whose mix leans on one programme far more than its neighbours' do "
            "is either serving a different kind of farming or being served by a "
            "different set of offices, and which of those it is decides who should look "
            "at it.\n\n"
            "READ THESE AS PROPORTIONS, NOT AMOUNTS. A programme can hold a large share "
            "of a small district's money and a small share of a large one's while "
            "paying out the same rupees in both. The rupee figure is given alongside "
            "every share for exactly this reason: quote both, and never describe a high "
            "share as 'more money' without checking the amount."
        ),
        "column_glossary": {
            "district": _DISTRICTS,
            "scheme": (
                "The programme the money flowed through: PM-KISAN income support, "
                "Agriculture Input Subsidy (seed and input subsidy), Horticulture APMIP "
                "(micro-irrigation subsidy), Fisheries (fisheries assistance), "
                "Sericulture (mulberry and cocoon incentive), MARKFED Procurement "
                "(payment for crop bought at the procurement centre) or RySS Rythu "
                "Sadhikara (natural-farming support). All seven are here, PM-KISAN "
                "included: this view divides up a rupee total rather than measuring "
                "coverage against a population, so leaving one programme out would make "
                "the shares add up to less than the whole."
            ),
            "benefit_share": (
                "UNIT: percentage. OF EVERY BENEFIT RUPEE REACHING THIS DISTRICT, THE "
                "SHARE FLOWING THROUGH THIS SCHEME. Read '22.2%' as 'in this district, "
                "22 paise in every rupee of farmer support came through this "
                "programme'. The district's seven shares add to 100 per cent. It is a "
                "PROPORTION, so a large district and a small one compare directly - but "
                "it says nothing about size, and a rising share can mean either that "
                "this programme paid more or that the others paid less. Where the "
                "figure given is an average across several cells, it is the mean of "
                "those cells' shares."
            ),
            "total_benefit": (
                "UNIT: rupees (INR), TOTALLED. The actual money behind the share - what "
                "this programme paid to farmers in this district. An absolute figure: "
                "it grows with the size of the district. Quote it whenever a share is "
                "quoted, so a proportion is never mistaken for an amount."
            ),
        },
    },
}


# =============================================================================
# STEP 2a: ROSTER POPULATION SHARES
# =============================================================================
# Composition read as equity is the failure this block exists to prevent.
#
# A TOTALLED measure broken down by a demographic dimension almost always ranks
# the groups by their own size. "BC and OC hold the largest land base, ST the
# smallest" reached a ranked insight in the gamma reports wearing equity
# framing, and it is nothing of the kind: BC is 45.3% of the roster and holds
# 46.3% of the land, ST is 5.9% and holds 5.8%. The finding was true, the
# reading was wrong, and nothing in the enrichment block let the model tell the
# difference — it was handed the totals and not the headcounts behind them.
#
# So for any demographic breakdown of a SUM, the group's share of the roster
# population travels with the total, and rule 2b of the prompt requires the two
# to be stated together. The model can then write composition as composition.
#
# The base is the PM-KISAN roster, read from view2's parquet — one row per
# roster farmer, so it IS the roster, and using it means these shares cannot
# disagree with view2's own published figures. Every figure leaves here as a
# rendered string, per STEP 0.

# A view's dimension name -> the roster column carrying the same attribute.
# Three views spell the social category differently; it is one dimension.
_ROSTER_DIM = {
    "category":        "category",
    "social_status":   "category",   # view3's name for it
    "caste":           "category",   # view4's name for it
    "gender":          "gender",
    "land_size_class": "land_size_class",
    "district":        "district",   # filter only - see below
}

# Which BREAKDOWNS get the comparison. `district` is in the map above so that a
# district FILTER can narrow the base, but a district breakdown is a geography
# question, not a demographic one, and "Guntur is 9% of farmers" is not the
# thing that was being misread.
_DEMOGRAPHIC_BREAKDOWNS = {"category", "social_status", "caste", "gender",
                           "land_size_class"}

# The prose rule that goes with the block above. Defined ONCE and imported by
# phase5c_gamma_reports, for the same reason the enrichment function is shared:
# two copies of a rule about the same stats key drift, and a rule that names a
# key the enrichment does not emit is worse than no rule at all.
POPULATION_SHARE_RULE = """2b. COMPOSITION IS NOT EQUITY. Where a finding carries 'stats.population_share', it is a TOTAL broken down by a demographic group -- social category, gender or landholding class -- and that block gives each group's share of the farmers on the PM-KISAN roster. A total across groups of different sizes ranks them by SIZE: the largest group holds the largest total almost by definition.
   - Whenever you quote such a total, quote the group's share of the roster alongside it, from 'share_of_roster_farmers', in the same sentence. Correct: "Backward Class farmers hold 46.3% of the land, in line with their 45.3% share of farmers on the roster." The reader now knows this is composition
   - Wrong: "Backward Class and Other Caste hold the largest land base, Scheduled Tribe the smallest." True, and it reads as a gap when it is a headcount fact
   - The smallest community will have the smallest total of everything. That is arithmetic, not a finding, and it must never be written as though it were one. Do not call such a split a gap, a shortfall, an imbalance, an under-representation or a disparity
   - When the two shares are close, SAY SO PLAINLY -- "in proportion to their numbers", "in line with their share of farmers". A group receiving its numerical share is a real and reportable result, not a failure to find something, and matching is the common case here
   - Only call a divergence a gap when the two shares actually diverge, and say by how much using the figures given. That IS the finding when it happens, and it is the one to lead with
   - Copy the percentages verbatim like every other figure. 'scope' tells you which population the share describes and 'roster_farmers_in_scope' how many farmers are behind it. If 'base_not_narrowed_by' is present, the share covers a WIDER population than the finding does -- name the population you are describing so the reader is not misled
   - The base is the PM-KISAN roster. Call it "farmers on the PM-KISAN roster", never "the population": tenant and landless farmers are not on it"""


_roster_cache: dict = {}


def _roster() -> pd.DataFrame:
    """The PM-KISAN roster, one row per farmer, from view2's parquet."""
    if "df" not in _roster_cache:
        _roster_cache["df"] = pd.read_parquet(VIEW2_CONFIG.parquet_path)
    return _roster_cache["df"]


def roster_population_share(breakdown: str, base_subspace) -> dict | None:
    """Each group's share of the roster population, for a demographic breakdown.

    Returns None when the comparison does not apply. The scope is narrowed by
    whichever base-subspace filters the roster can honour; filters it cannot
    (scheme, crop, season, status...) are NAMED in the returned block rather
    than silently ignored, because a share quoted against the wrong base is
    exactly the error this is here to stop.
    """
    if breakdown not in _DEMOGRAPHIC_BREAKDOWNS:
        return None

    col = _ROSTER_DIM[breakdown]
    df = _roster()
    if col not in df.columns:
        return None

    applied, unapplied = [], []
    if isinstance(base_subspace, list):
        for dim_val in base_subspace:
            dim, val = dim_val[0], dim_val[1]
            rcol = _ROSTER_DIM.get(dim)
            if rcol is not None and rcol in df.columns and rcol != col:
                df = df[df[rcol] == val]
                applied.append(f"{val}")
            elif rcol != col:
                unapplied.append(f"{dim}={val}")

    if len(df) == 0:
        return None

    counts = df.groupby(col).size().sort_values(ascending=False)
    total = int(counts.sum())
    if total == 0:
        return None

    block = {
        "what_this_is": (
            "each group's share of the farmers on the PM-KISAN roster - the "
            "headcount base behind the totals above"
        ),
        "scope": (" and ".join(applied) + " only") if applied else "all thirteen districts",
        "roster_farmers_in_scope": _num(total, 0),
        "share_of_roster_farmers": {
            str(k): f"{v / total * 100:.1f}%" for k, v in counts.items()
        },
    }
    if unapplied:
        block["base_not_narrowed_by"] = (
            "the roster has no such column, so this share is NOT restricted to: "
            + ", ".join(unapplied)
            + ". Say which population the share describes if you quote it here."
        )
    return block


# =============================================================================
# STEP 2: ENRICH CANDIDATES WITH QUANTITATIVE STATS
# =============================================================================

def enrich_candidates_with_stats(
    view_name: str,
    ranked_candidates: list,
    config: ViewConfig,
) -> list:
    """
    For each ranked candidate, compute the actual distribution values
    so the LLM can cite specific numbers.
    """
    df = pd.read_parquet(config.parquet_path)

    enriched = []
    for candidate in ranked_candidates:
        c = candidate.copy()

        breakdown    = c["breakdown"]
        measure      = c["measure"]
        base_subspace = c["base_subspace"]

        # Skip measure/breakdown-extending HDPs where aggregation is ambiguous
        if measure == "(varies)" or breakdown == "(varies)":
            c["stats"] = {"note": "Varies across members -- see individual patterns"}
            enriched.append(c)
            continue

        # Apply base subspace filter
        filtered = df.copy()
        if isinstance(base_subspace, list):
            for dim_val in base_subspace:
                dim, val = dim_val[0], dim_val[1]
                filtered = filtered[filtered[dim] == val]

        if len(filtered) == 0:
            c["stats"] = {"note": "No data after filtering"}
            enriched.append(c)
            continue

        # Aggregate using the measure's configured agg type
        agg_type = config.get_agg(measure)
        if agg_type == "avg":
            dist = filtered.groupby(breakdown)[measure].mean()
        else:
            dist = filtered.groupby(breakdown)[measure].sum()

        dist = dist.dropna().sort_values(ascending=False)

        if len(dist) == 0:
            c["stats"] = {"note": "No data after filtering"}
            enriched.append(c)
            continue

        total = dist.sum()

        # Every figure below leaves this function as a rendered string. Nothing
        # numeric reaches the prompt that the model could be tempted to convert,
        # re-scale or re-group; see STEP 0.
        def render(label, val):
            entry = {"value": format_measure(view_name, measure, val)}
            # A "share of the total" is only meaningful when the parts add up
            # to the whole. For an AVG measure the column is a sum of averages
            # and the share is arithmetic nonsense, so it is not offered.
            if agg_type == "sum" and total > 0:
                entry["share_of_total"] = f"{val / total * 100:.1f}%"
            return str(label), entry

        stats = {}
        stats["top_values"]    = dict(render(l, v) for l, v in dist.head(5).items())
        stats["bottom_values"] = dict(render(l, v) for l, v in dist.tail(2).items())
        stats["count_breakdown_values"] = len(dist)
        stats["measure_unit"] = _UNITS.get(view_name, {}).get(measure, "unknown")
        stats["how_aggregated"] = (
            "averaged across rows - a per-unit figure, not a total"
            if agg_type == "avg"
            else "totalled across rows - an absolute figure"
        )
        if agg_type == "sum":
            stats["total"] = format_measure(view_name, measure, total)

            # A demographic breakdown of a TOTAL ranks groups by their own size
            # unless the headcounts travel with it. See STEP 2a.
            pop_share = roster_population_share(breakdown, base_subspace)
            if pop_share:
                stats["population_share"] = pop_share

        # Highlight-specific stats
        if c.get("commonness_sets"):
            cs = c["commonness_sets"][0]
            highlight = cs.get("highlight", "")
            try:
                hl = ast.literal_eval(highlight) if isinstance(highlight, str) else highlight
            except (ValueError, SyntaxError):
                hl = ()

            if isinstance(hl, tuple) and len(hl) > 0 and hl[0] not in ("EVEN", "DECREASING", "INCREASING"):
                highlight_vals = {}
                for h in hl:
                    if not isinstance(h, tuple) and h in dist.index:
                        k, entry = render(h, float(dist[h]))
                        highlight_vals[k] = entry
                if highlight_vals:
                    stats["highlight_values"] = highlight_vals

        # For AVG measures, the sample size behind each average — the base a
        # rate has to be read against (see the view5 thin-cell note).
        if agg_type == "avg":
            counts = filtered.groupby(breakdown)[measure].count()
            counts = counts.reindex(dist.head(5).index).dropna()
            stats["rows_behind_each_average"] = {
                str(k): _num(int(v), 0) for k, v in counts.items()
            }

        c["stats"] = stats
        enriched.append(c)

    return enriched


# =============================================================================
# STEP 4: BUILD LLM PROMPT PER VIEW
# =============================================================================

def build_view_prompt(view_name: str, ranked_candidates: list) -> str:
    """Build the LLM prompt for generating the executive summary for one view."""
    view_info = VIEW_DESCRIPTIONS[view_name]

    findings = []
    for i, c in enumerate(ranked_candidates):
        finding = {
            "rank":                i + 1,
            "pattern_type":        c["pattern_type"],
            "extending_strategy":  c["extending_strategy"],
            "extending_dimension": c["extending_dimension"],
            "breakdown":           c["breakdown"],
            "measure":             c["measure"],
            "base_subspace":       c["base_subspace"],
            "hdp_size":            c["hdp_size"],
            "commonness_sets":     c["commonness_sets"],
            "exceptions":          c["exceptions"],
            "score":               c["score"],
            "conciseness":         c["conciseness"],
            "impact":              c["impact"],
        }
        if "stats" in c:
            finding["stats"] = c["stats"]
        findings.append(finding)

    findings_json = json.dumps(findings, indent=2, default=str)

    return f"""You are writing the findings section of an analytical report on the farmer welfare programmes run by the Department of Agriculture, Government of Andhra Pradesh, India. The programmes covered are PM-KISAN, Agriculture input subsidy, Horticulture APMIP, Fisheries, Sericulture, MARKFED procurement and RySS Rythu Sadhikara, across the thirteen districts of the state.

## Your Audience
A senior programme officer in the AP Department of Agriculture, who takes these findings into collector-level district review meetings. They are non-technical -- they understand scheme delivery, district administration and programme targets, but not data science terminology. They want to know: what did the data reveal, why does it matter for delivery, and what should they raise with district collectors.

## This Section: {view_info['title']}

{view_info['description']}

{view_info['audience_context']}

## Column Glossary
{json.dumps(view_info['column_glossary'], indent=2)}

## Ranked Findings (from automated pattern analysis)

The following findings were automatically discovered and ranked by analytical importance. Each finding represents a pattern that holds consistently across multiple subgroups, with any exceptions noted.

Key concepts:
- "commonness" = a pattern that holds for the majority of subgroups (e.g., "in 73 out of 75 districts, Cardiology has the highest claim amounts")
- "exceptions" = specific subgroups where the pattern breaks
- "HIGHLIGHT_CHANGE" exception = the same pattern type but with a different leading value
- "TYPE_CHANGE" exception = a completely different pattern applies
- "NO_PATTERN" exception = no clear pattern exists in that subgroup

{findings_json}

## Instructions

Write a clear, readable summary of these findings for the programme officer. Follow these rules:

1. STRUCTURE: Organise findings into 3-5 thematic groups (e.g., "Where the Money Goes", "Equity Across Social Categories", "Payments Stuck in the Pipeline", "Trends Over Time"). Do not list findings by rank number.

2. NUMBERS -- READ THIS BEFORE YOU WRITE ANY FIGURE:
   Every number in the 'stats' field has ALREADY been formatted for print, with its unit attached. Your job is to choose which figures to quote and to explain what they mean. It is NOT to do arithmetic.
   - Copy each formatted string VERBATIM, exactly as it appears -- the same digits, the same grouping, the same unit word. "Rs 20.25 crore" is written "Rs 20.25 crore"
   - NEVER convert between units. Do not turn rupees into lakh or crore yourself, do not turn a percentage into a fraction, do not turn quintals into tonnes. The conversion has been done
   - NEVER re-derive, add, subtract, average, or compute a percentage of your own from the figures given. If a number you want is not in the stats, do not produce it -- write around it
   - Digit grouping is Indian throughout (12,34,567 -- not 1,234,567) and it is already applied. Do not re-group anything, and keep one style across the whole section
   - Each measure's stats carry 'measure_unit' and 'how_aggregated'. Use them: a TOTALLED figure is an absolute that grows with the size of the group, an AVERAGED figure is a per-unit rate that does not. Never describe a total as though it were a rate, or a rate as though it were a total
   - Where 'rows_behind_each_average' is given, it is the number of records behind each average. If it is small, say so when you quote the average

{POPULATION_SHARE_RULE}

3. LANGUAGE:
   - Write in English. Use plain English, no jargon
   - NEVER print a raw code or an internal column name in the prose. Use the Column Glossary above to translate every value into words: spell out social categories on first use ("Scheduled Tribe (ST)"), name districts in full, spell out seasons ("Kharif, the monsoon season"), give the scheme its full name, and write land-size classes as the glossary spells them
   - The unit is already inside every formatted figure. Do not add a second unit word after it, and do not strip the one that is there
   - Explain what each finding means operationally
   - Name specific districts when they appear as exceptions
   - Never print an Aadhaar number, a farmer name or any other personal identifier; none appear in the findings and none may appear in the prose

4. EXCEPTIONS ARE THE STORY: Universal patterns (100% commonness) are context. Exceptions are where actionable intelligence lives. Highlight them prominently.

4b. NEVER INVENT A CAUSE. This is the hardest rule in this list and the easiest to break by accident. The findings tell you WHAT is happening, WHERE, and HOW MUCH. They contain no information whatever about WHY. You must not supply one.
   - Do not write that something happened "because", "due to", "driven by", "as a result of", "reflecting", or "explained by" anything. Those phrases are claims about causation that the analysis did not make
   - Do not reach for a plausible mechanism to tidy up a finding. A previous version of this report explained a procurement pattern as an artefact of "record-edge months". Nothing in the data said that. It was invented, it was wrong, and it would have sent an officer looking in the wrong place
   - Do not attribute a pattern to administrative capacity, staffing, awareness, weather, terrain, market conditions, or any other unstated factor
   - Where a cause matters - and it usually does - write it as a QUESTION FOR THE OFFICER, not as a statement. "Payments in East Godavari are running at 35.0% unpaid against 8.5% elsewhere; what is holding them?" is correct. "Payments in East Godavari are slow because the district office is understaffed" is not, and neither is "likely reflecting staffing pressure"
   - Hedging does not make an invented cause acceptable. "Possibly", "may reflect", "suggests that", "appears to be driven by" are the same violation in softer words
   - The one thing you MAY state as fact is what the glossary or section description explicitly tells you (for example, that a district is absent from a view, or that a figure is a per-unit rate). Those are established by the data build, not inferred by you

4c. {NO_METHODOLOGY_NOTE_RULE}

{vocabulary_rule(view_name, "4d")}5. TONE: Professional, direct, advisory. Not academic. A trusted analyst briefing a decision-maker.

6. LENGTH: 400-800 words for this section. Be concise but complete.

7. DO NOT:
   - Mention scores, conciseness, impact, HDP, extending strategies, or any technical MetaInsight terminology
   - Invent information not present in the findings
   - Use bullet points for the main narrative (short lists for exceptions are OK)

8. DO:
   - Start with the most important headline finding
   - Connect related findings into a narrative
   - Use specific figures from the 'stats' field, copied verbatim per rule 2: cite actual values, and the 'share_of_total' string where one is given. If stats.highlight_values is present, always cite those figures
   - For AVERAGED measures, quote the average as given (e.g., "the typical subsidy per registration is Rs 4,200") and make clear it is a per-unit figure
   - End with 2-3 specific follow-up questions the officer should raise at the next district review

9. FORMATTING RULES (strictly follow these):
   - Use ### for thematic section headers (e.g., ### Financial Patterns)
   - Never use **text** as a substitute for a header
   - Use inline bold sparingly — only for specific district/entity names that are exceptions or outliers
   - No bold for general phrases or conclusions
   - Plain prose for everything else
"""


# =============================================================================
# STEP 5: CALL LLM AND ASSEMBLE REPORT
# =============================================================================

def build_global_feed_prompt(feed: dict) -> str:
    """The opening section: the cross-view feed, written as one narrative.

    The per-view sections that follow are unchanged. This one exists because a
    reader opening the report should meet the programme's most important
    findings in one place rather than having to hold eight sections in their
    head and rank them mentally.
    """
    weighting = feed["weighting"]
    rows = feed["feed"][:20]

    findings = []
    for r in rows:
        f = {
            "rank": r["rank"],
            "area": r["view_title"],
            "finding": r["summary"],
            "pattern_type": r["pattern_type"],
            "measure": r["measure"],
            "breakdown": r["breakdown"],
            "base_subspace": r["base_subspace"],
            "exceptions": r["exceptions"][:4],
        }
        # This section carries no `stats` block - it is written from the feed's
        # own one-line summaries - but those summaries have exactly the shape
        # rule 2b exists for ("BC has the highest declared_acres"), and this is
        # the OPENING section, the part most certain to be read. So the roster
        # shares travel with a demographic breakdown of a SUM here too.
        cfg = VIEW_CONFIGS.get(r["view"])
        if cfg is not None and cfg.get_agg(r["measure"]) == "sum":
            pop_share = roster_population_share(r["breakdown"], r["base_subspace"])
            if pop_share:
                f["population_share"] = pop_share
        findings.append(f)

    return f"""You are writing the OPENING section of an analytical report on the farmer welfare programmes run by the Department of Agriculture, Government of Andhra Pradesh, India. Everything after this section goes area by area; this section is the one place the whole programme is looked at together.

## Your Audience
A senior programme officer in the AP Department of Agriculture, who takes these findings into collector-level district review meetings. Non-technical: they understand scheme delivery and district administration, not data science.

## What this section is

Eight analytical areas were each mined separately, and each was ranked against its own totals. The findings below are the top of a single combined ordering across all eight, so that what a reader meets first is not decided by which area a finding happened to come from.

The combined ordering weights each area by how many farmers it covers, listed here:

{json.dumps(weighting['weights'], indent=2)}

That weighting is a judgement, not a measurement. You do not need to explain it and you must not defend it; if it is worth a sentence, say only that the areas were combined in proportion to how many farmers each covers.

## The top findings across the programme

{json.dumps(findings, indent=2, default=str)}

## Instructions

Write 350-550 words. Rules:

1. Open with the single most important thing the analysis found across the whole programme. Not a summary of the method, not "this report covers" - the finding itself.

2. Group what follows into 3-4 themes and connect them. This is a narrative, not a list, and it must not repeat the per-area sections that follow it - it frames them.

3. NEVER INVENT A CAUSE. The findings say what, where and how much. They say nothing about why, and you must not supply it. No "because", "due to", "driven by", "reflecting", "as a result of". No mechanism offered to tidy a finding up. Hedging does not help: "may reflect" and "likely driven by" are the same violation. Where the cause matters, put it as a question for the officer to raise.

4. Do not quote a numeric figure in this section unless it appears verbatim in the finding text above. Do not compute, convert or re-derive anything. The detailed figures live in the sections that follow.

4b. COMPOSITION IS NOT EQUITY. Some findings carry a 'population_share' block. Those total something across social categories, genders or landholding classes, and a total across groups of different sizes ranks them by SIZE -- the largest group holds the largest total almost by definition. A finding worded "Backward Class and Other Caste lead in declared land" is a headcount fact, and writing it as a fairness result would be wrong.
   - If you carry such a finding into this section, carry its roster share with it, copied verbatim from 'share_of_roster_farmers'. "Backward Class farmers hold the largest share of declared land, in line with their 45.3% share of farmers on the roster" is right; the first half alone is not
   - Do not call such a split a gap, a shortfall, an imbalance, an under-representation or a disparity unless the two shares actually differ, and then say by how much
   - The base is the PM-KISAN roster. Call it "farmers on the PM-KISAN roster", never "the population": tenant and landless farmers are not on it
   - If a finding has no 'population_share' block, this rule does not apply to it

5. Name districts, social categories and programmes in full plain English. Never print an internal column name, a code, or any personal identifier. Spell out social categories on first use, e.g. "Scheduled Tribe (ST)".

5b. COMPOSITION IS NOT EQUITY. This section carries no population figures, so it cannot make the comparison the detailed sections make -- which means it must not make the claim either. Where a finding says one social category, gender or landholding class leads or trails on a TOTAL, do not present that as a gap, a shortfall, an imbalance or an under-representation. The largest group has the largest total of everything, and the smallest the smallest, before any programme does anything. Either write it plainly as a description of who is in the data, or leave it to the section that has the population share to hand.

6. Do not mention scores, ranks, weights beyond the one sentence permitted above, or any technical analysis terminology.

7. End with the three questions you would put on the agenda of the next district review.

8. FORMATTING: ### for any sub-headers. No bold except for a district or entity name that is an exception. Plain prose otherwise.
"""


def _require_content(response, what: str) -> str:
    """Return the model's text, or fail loudly saying exactly why it is empty.

    This exists because the failure it catches is silent. On a reasoning model
    the completion budget is shared between reasoning and the visible answer,
    so an under-budgeted call returns finish_reason='length' with content='' --
    and the report is then assembled, written and saved with a blank section.
    A hollow deliverable that looks fine is worse than a crash, so this crashes.
    phase5c_gamma_reports has carried the same guard since iteration 5; this is
    the copy phase5b was missing.
    """
    choice = response.choices[0]
    text = choice.message.content
    if text and text.strip():
        return text

    details = getattr(response.usage, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None)
    raise RuntimeError(
        f"The model returned no text for {what}. "
        f"finish_reason={choice.finish_reason!r}, "
        f"completion_tokens={response.usage.completion_tokens}, "
        f"reasoning_tokens={reasoning}, "
        f"budget={DISCOVER_MAX_COMPLETION_TOKENS}. "
        f"If reasoning_tokens has consumed the whole budget, raise "
        f"DISCOVER_MAX_COMPLETION_TOKENS in discover_config.py."
    )


def generate_executive_report(
    all_ranked: dict,
    all_configs: dict,
    output_path: str,
    global_feed: dict | None = None,
) -> str:
    """Generate the full executive report using Claude."""
    client = OpenAI()

    report_sections = [
        "# AP RTGS Decision Aid -- Analytical Findings Report\n\n"
        "*Department of Agriculture, Government of Andhra Pradesh*\n\n"
        "*Automated MetaInsight Analysis*\n\n"
        "---\n"
    ]

    if global_feed:
        print("Generating section: Top findings across the programme ...")
        response = client.chat.completions.create(
            model=DISCOVER_PROSE_MODEL,
            max_completion_tokens=DISCOVER_MAX_COMPLETION_TOKENS,
            messages=[{"role": "user",
                       "content": build_global_feed_prompt(global_feed)}],
        )
        report_sections.append("\n## Top Findings Across the Programme\n\n")
        report_sections.append(_require_content(response, "the global feed"))
        report_sections.append("\n\n---\n")

    view_order = [(v, VIEW_DESCRIPTIONS[v]["title"])
                  for v in ("view1", "view2", "view3", "view4", "view5",
                            "view6", "view7", "view8", "view9")]

    for view_name, view_title in view_order:
        print(f"Generating section: {view_title} ...")
        ranked = all_ranked[view_name]
        config = all_configs[view_name]

        enriched = enrich_candidates_with_stats(view_name, ranked, config)
        prompt   = build_view_prompt(view_name, enriched)

        response = client.chat.completions.create(
            model=DISCOVER_PROSE_MODEL,
            max_completion_tokens=DISCOVER_MAX_COMPLETION_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        section_text = _require_content(response, view_title)

        report_sections.append(f"\n## {view_title}\n\n")
        report_sections.append(section_text)
        report_sections.append(reading_note_block(view_name))
        report_sections.append("\n\n---\n")

    full_report = "".join(report_sections)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    print(f"\nExecutive report -> {output_path}")
    return full_report


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    views = ["view1", "view2", "view3", "view4", "view5",
             "view6", "view7", "view8", "view9"]

    all_ranked  = {}
    all_configs = {
        "view1": VIEW1_CONFIG,
        "view2": VIEW2_CONFIG,
        "view3": VIEW3_CONFIG,
        "view4": VIEW4_CONFIG,
        "view5": VIEW5_CONFIG,
        "view6": VIEW6_CONFIG,
        "view7": VIEW7_CONFIG,
        "view8": VIEW8_CONFIG,
        "view9": VIEW9_CONFIG,
    }

    for view_name in views:
        path = os.path.join(BASE_DIR, "metainsights", f"{view_name}_ranked.json")
        with open(path, encoding="utf-8") as f:
            all_ranked[view_name] = json.load(f)
        print(f"Loaded {len(all_ranked[view_name])} ranked candidates for {view_name}")

    # ITERATION 3 — the cross-view feed opens the report, ahead of the per-view
    # sections, which are unchanged. Absent (phase5c not run), the report is
    # built exactly as before.
    feed_path = os.path.join(BASE_DIR, "metainsights", "global_feed.json")
    global_feed = None
    if os.path.exists(feed_path):
        with open(feed_path, encoding="utf-8") as f:
            global_feed = json.load(f)
        print(f"Loaded the global feed: {len(global_feed['feed'])} findings")
    else:
        print("No global_feed.json — writing the per-view sections only")

    # The AP report lands in reports_rtgs/ so it cannot overwrite the UP
    # deployment's executive report, which stays in reports/ as the reference.
    md_path = os.path.join(BASE_DIR, "reports_rtgs", "executive_metainsight_report.md")
    generate_executive_report(all_ranked, all_configs, md_path, global_feed)

    import md_to_pdf
    md_to_pdf.convert(md_path, md_path.replace(".md", ".pdf"))

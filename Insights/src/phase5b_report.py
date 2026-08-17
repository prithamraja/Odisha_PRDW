# =============================================================================
# Phase 5b: Executive MetaInsight Report (LLM-Generated)
# =============================================================================
# Takes ranked MetaInsight candidates from Phase 5 and uses an LLM to generate
# a readable executive report for the officers who sit in the Odisha
# Panchayati Raj & Drinking Water review meeting. The LLM translates
# already-validated structured findings into clear prose -- it does not
# re-analyse data or exercise analytical judgment.
#
# Inputs:
#   metainsights/view{1-3}_ranked.json
#
# Outputs:
#   reports_prdw/executive_metainsight_report.md
#
# Run from project root:
#   python src/phase5b_report.py
# =============================================================================

import os
import re
import sys
import ast
import csv
import json

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase4a_engine import (
    VIEW1_CONFIG, VIEW2_CONFIG, VIEW3_CONFIG,
    ViewConfig,
    # WP-D2c A3: the one list of signed money measures, shared with the ranker
    SIGNED_MONEY_MEASURES,
)
from discover_config import DISCOVER_PROSE_MODEL, DISCOVER_MAX_COMPLETION_TOKENS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# view name -> its config. Module-level because the feed prompt needs to ask a
# measure's aggregation type outside main()'s local scope. This is the ONE
# registry: the report's section order, the entry point and phase5b_dual_reports
# all read it, so a view cannot be half-added.
VIEW_CONFIGS = {
    "view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG,
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
    "rupees":     _rupees,
    "activities": lambda x: f"{_num(x, 0)} activities",
    "plans":      lambda x: f"{_num(x, 0)} plans",
    "vouchers":   lambda x: f"{_num(x, 0)} vouchers",
    "sanctions":  lambda x: f"{_num(x, 0)} sanctions",
    "approvals":  lambda x: f"{_num(x, 0)} approval records",
    "uploads":    lambda x: f"{_num(x, 0)} photo uploads",
    "people":     lambda x: f"{_num(x, 0)} people",
}

# Every measure of every view has a unit here, so no measure can reach the
# prompt as a bare number. The unit is also what decides which measures the FY
# 2023-24 reporting caveat applies to -- see activity_count_measures() below --
# so "activities" means an activity COUNT and nothing else. Photo uploads,
# vouchers, sanction records, plans and people are their own units precisely
# because they are counted on a different thing.
_UNITS = {
    "view1": {
        "n_activities": "activities",
        "total_cost": "rupees", "fund_tied_total": "rupees",
        "fund_untied_total": "rupees", "fund_abandoned_total": "rupees",
        "work_proposed_cost": "rupees", "fund_sanctioned_total": "rupees",
        "total_expenditure": "rupees", "gen_amount": "rupees",
        "sc_amount": "rupees", "st_amount": "rupees",
        "overspend_vs_plan": "rupees", "overspend_vs_sanction": "rupees",
        "is_started": "activities", "is_completed": "activities",
        "is_ongoing": "activities", "is_abandoned": "activities",
        "is_under_approval": "activities", "is_admin_approved": "activities",
        "has_technical_approval": "activities",
        "has_progress_evidence": "activities",
        "evidence_uploads": "uploads",
        "trainees_total": "people", "beneficiaries_expected": "people",
    },
    "view2": {
        "payment_amount": "rupees", "receipt_amount": "rupees",
        "payment_count": "vouchers", "receipt_count": "vouchers",
        "activity_linked_expenditure": "rupees",
        "sanctions_count": "sanctions", "sanctioned_amount": "rupees",
        # WP-D2c A4. Rupees either way -- the unit does not change when the
        # aggregation does, and `how_aggregated` in the stats is what tells the
        # writer this one is a per-GP-month rate rather than a total.
        "payment_amount_mean": "rupees", "receipt_amount_mean": "rupees",
    },
    "view3": {
        "n_plans": "plans",
        "n_activities": "activities", "n_costed": "activities",
        "n_costless": "activities",
        "planned_cost": "rupees", "sanctioned_total": "rupees",
        "expenditure_total": "rupees",
        "overspend_vs_plan": "rupees", "overspend_vs_sanction": "rupees",
        "payment_amount": "rupees", "receipt_amount": "rupees",
        "n_admin_approvals": "approvals", "n_tech_approvals": "approvals",
        "n_completed": "activities", "n_ongoing": "activities",
        "n_abandoned": "activities", "n_with_evidence": "activities",
        "evidence_uploads": "uploads",
    },
}


def format_measure(view_name: str, measure: str, value: float) -> str:
    """Render one measured value for one view's measure, unit included."""
    unit = _UNITS.get(view_name, {}).get(measure)
    return _FORMATTERS.get(unit, lambda x: _num(x, 2))(float(value))


# =============================================================================
# STEP 1: VIEW DESCRIPTIONS
# =============================================================================

# Shared vocabulary. All three PR&DW views carry the same geography spine and
# the same fiscal-year axis, so the definitions are written once and merged into
# each view's glossary.
_GP = (
    "The Gram Panchayat, from the LGD-coded government roster. 20 Gram "
    "Panchayats in this sample, across 16 blocks and 9 districts. Always name "
    "the Gram Panchayat in full; never use a code."
)
_BLOCK = (
    "The Block the Gram Panchayat sits in, from the LGD-coded government "
    "roster. 16 blocks in this sample. Always name the block; never use a code."
)
_DISTRICT = (
    "The District, from the LGD-coded government roster. 9 districts in this "
    "sample. Always name the district in full; never use a code."
)
_FISCAL_YEAR = (
    "The plan year, as the full string form ('2024-2025'). Counts across the "
    "2023-24 boundary reflect the reporting change described above, not real "
    "workload change."
)

# The counted-flag family in view1: eight columns, one definition.
_ACTIVITY_FLAG = (
    "UNIT: activities, COUNTED - activities meeting the condition. Read against "
    "n_activities for a rate."
)


# =============================================================================
# READING NOTES -- deterministic, not LLM-authored
# =============================================================================
# Methodology caveats are fixed content. They were previously left to the model,
# which meant the wording of an assumption changed from run to run -- and a
# caveat is exactly where a paraphrase does the most damage (an earlier AP gamma
# suite invented a "Telangana-style procurement" clause out of nothing).
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

# Sanction records cover about a sixth of the activities in this drop. Every
# view carrying a SANCTIONED-basis measure has to say so, because the absence of
# a sanction record is not evidence that a work was never approved.
_SANCTION_COVERAGE = (
    "Sanction records exist for **2,101 of the 12,704 activities** (about one in "
    "six), so every sanctioned-basis figure -- sanctioned amounts, approval "
    "counts, and overspend against sanction -- describes that subset only. An "
    "activity with no sanction record is **not** shown to be unapproved; it is "
    "shown to have no record on file."
)

# One entry per view whose figures rest on an assumption the reader has to be
# told about. A view with no entry gets no note and no blockquote. All three
# PR&DW views have one: this drop carries a reporting change, a coverage gap and
# a near-degenerate status column, and none of them is a finding.
READING_NOTES = {
    "view1": (
        "this view has one row for each of the **12,704 activities** the 20 "
        "Gram Panchayats planned, and three of its properties are features of "
        "the data rather than results. First, **costless activities** -- "
        "training, campaigns and services planned without a cost -- only began "
        "being reported in 2023-24, and they are 7,074 of the 12,704 rows, so "
        "activity counts rise about eightfold at that boundary for a reporting "
        "reason. Second, " + _SANCTION_COVERAGE + " Third, only **17 activities "
        "are marked WORK COMPLETED** in the whole sample, so completion rates "
        "here measure recording practice, not delivery."
    ),
    "view2": (
        "this view's time axis is the **cashbook's own 72 months** (April 2020 "
        "to March 2026), and a Gram Panchayat month with no transactions is "
        "present as a row of zeros rather than absent -- 259 of the 1,440 cells "
        "are such months. Two consequences follow. Sanctions are counted by "
        "**sanction month**, so the **2,040** sanctions dated inside the window "
        "are here and **61** dated outside it are not; the yearly report card "
        "counts the full 2,101 by fiscal year, and both totals are correct for "
        "their own axis. And **March concentrates payments every year** -- 2,040 "
        "of the 8,529 payment vouchers fall in a March -- which is the "
        "fiscal-year end, a known property of government cash flow."
    ),
    "view3": (
        "this view is a full grid -- all 20 Gram Panchayats against all 6 fiscal "
        "years, 120 rows -- so a **zero is a recorded zero**, not a missing row. "
        "It can mean either that nothing happened or that nothing was recorded, "
        "and this view cannot tell those apart. "
        # WP-D2c A7. The operator's ruling on view3's two displaced findings:
        # keep the completion story, reframed as data quality. The trends that
        # carried it are no longer mined -- a series of six zeros cannot be
        # read as a decline -- so the statement is made here, from the counts,
        # where it cannot depend on a pattern that should not have been found.
        "**Completion recording effectively ceased after 2022-23**: the 17 "
        "activities ever marked WORK COMPLETED fall 3 / 6 / 6 across 2020-21 to "
        "2022-23, then 0, 2 and 0 across the three years since. No comparison "
        "of Gram Panchayats on completions can be supported by this column, and "
        "trend patterns on it are reported in the data-quality annex rather "
        "than as findings. "
        + _SANCTION_COVERAGE
        + " `n_tech_approvals` totals **2,095**, not the 2,134 technical-approval "
        "records in the source: 39 sit on activities that have no administrative "
        "approval, and the approval view hangs the technical approval off the "
        "administrative one. The Ask chatbot reports the same 2,095, so the two "
        "systems agree."
    ),
}


# =============================================================================
# THE FY 2023-24 REPORTING-ARTIFACT CAVEAT -- per finding, deterministic
# =============================================================================
# Mapping doc §5 decomposed the step-change the data dictionary flagged:
# activity rows jump 609 -> 4,607 at FY 2023-24 ENTIRELY because costless
# activities begin being recorded (0 before, 2,780 / 2,367 / 1,927 after). The
# cashbook is smooth across the same boundary and approvals are steady, so the
# artifact lives in planning-data completeness and nowhere else.
#
# §5.2 therefore requires a caveat on any finding that COMPARES activity counts
# across that boundary -- and on no other finding. Getting that scope right is
# the point: a caveat on every finding is wallpaper, and a caveat on a rupee
# finding is wrong (money measures are unaffected).
#
# The test is mechanical, runs before the model sees anything, and has three
# parts, all of which must hold:
#
#   1. The view's counts carry the artifact at all. view1 and view3 count
#      activities; view2 counts vouchers and sanctions and is artifact-free.
#   2. The measure is an ACTIVITY COUNT. Derived from _UNITS above rather than
#      listed again here, so a new measure cannot be added to a config and
#      silently escape the test. Rupees, plans, vouchers, sanction records,
#      photo uploads and people are all outside it.
#   3. The finding COMPARES fiscal years across the boundary -- either because
#      fiscal_year is its breakdown, or because fiscal_year is the dimension its
#      HDP members vary along. A fiscal_year FILTER does not qualify: a finding
#      sitting inside one year makes no comparison across the boundary.
#
# The flag is set in enrich_candidates_with_stats (which is the one place that
# already holds both the candidate and the data), travels into the prompt so the
# writer knows not to present the artifact as a discovery, and is appended to
# the section's deterministic reading note -- one blockquote, one marker, so the
# prose gate's count still holds.

_FY_PRE_2023 = frozenset({"2020-2021", "2021-2022", "2022-2023"})
_FY_FROM_2023 = frozenset({"2023-2024", "2024-2025", "2025-2026"})

# Views whose counted measures are activity counts, and therefore carry it.
_COUNT_CAVEAT_VIEWS = ("view1", "view3")

COUNT_CAVEAT_SENTENCE = (
    "Activity-count comparisons across FY 2023-24 reflect a change in reporting "
    "completeness (costless activities begin being recorded), not a change in "
    "activity."
)

# What the writer is told, on the qualifying findings only.
COUNT_CAVEAT_FOR_PROMPT = (
    "REPORTING ARTIFACT ON THIS FINDING: it compares activity counts across the "
    "FY 2023-24 boundary, where costless activities begin being recorded. The "
    "jump is a change in what was written down, not a change in what was done. "
    "Do not present the rise as growth, as a surge, as improved performance or "
    "as any kind of discovery, and do not explain it. The section already "
    "carries a fixed note that states it -- do not write your own."
)


# =============================================================================
# A3 -- EVENNESS on a signed money measure
# =============================================================================
# Calibration session 1, ruling 3, on the finding the operator called the most
# interesting in the set: Rs 51.96 crore of underspend, spread evenly across
# every Gram Panchayat in 27 of 28 asset categories. The engine wrote it as
# "overspend_vs_plan is evenly distributed across gp_name values. Exception:
# Banking Facilities (no clear pattern)" -- a neutral sentence about a shape,
# with an exception clause that reads as praise for the excepted category.
#
# Both halves are wrong for a signed money measure. Evenness on a shortfall is
# the FINDING: there is no concentration to chase, no small set of Gram
# Panchayats to call in, and the shortfall is a property of the programme
# rather than of any place in it. And the exception is about the SPREAD, not
# about the level -- Banking Facilities is where the shortfall is unevenly
# spread, which says nothing whatever about whether it spends well.

EVENNESS_FOR_PROMPT = (
    "EVENNESS ON A SIGNED MONEY MEASURE. This finding says the measure is "
    "spread EVENLY -- not that it is small, and not that it is fine. Lead with "
    "the magnitude from 'stats.total' and then with the absence of "
    "concentration: the money belongs to every group in the breakdown and no "
    "one of them accounts for it. That is what makes it actionable, because it "
    "rules out the small set of places an officer would otherwise go looking "
    "for. The exceptions are the groups where the measure is NOT evenly spread "
    "-- they are about the SHAPE of the distribution and say nothing about how "
    "much any of them spends. Never write an exception here as good or bad "
    "behaviour, and never call an even spread a balanced or healthy one."
)

# =============================================================================
# A6 -- activity-linked expenditure is a recording measure before it is a
#       spending measure
# =============================================================================
# Calibration session 1, ruling 6. Four of view2's fifteen findings were rises
# in `activity_linked_expenditure` -- read straight, "spending on planned works
# is growing". The cashbook says otherwise: total outflow did not rise across
# the same six years, and what rose was the share of it that carries a link to
# a planned activity. Every figure below is measured off this drop (view2 by
# fiscal year; the link count from `activity_voucher`).

LINKAGE_MEASURE = "activity_linked_expenditure"

LINKAGE_SENTENCE = (
    "On activity-linked expenditure specifically: the cashbook's total outflow "
    "did **not** grow across these six years (**Rs 15.60 crore** in 2020-21 "
    "against **Rs 11.12 crore** in 2025-26), while the share of it carrying a "
    "link to a planned activity rose from **2.7%** to **53.2%**, and the number "
    "of recorded activity-voucher links rose from **30** to **2,122**. A rise "
    "in activity-linked expenditure is therefore a rise in recording "
    "completeness unless the cashbook total rises with it."
)

LINKAGE_FOR_PROMPT = (
    "RECORDING-COMPLETENESS FRAMING ON THIS FINDING: it is about "
    "activity_linked_expenditure, which is the part of the cashbook that has "
    "been LINKED to a planned activity. Linking practice grew steeply over "
    "this window while the cashbook total did not, so a rise here is first of "
    "all a rise in how completely the link was recorded. Present it that way. "
    "Do not describe it as growth in spending, in delivery or in execution, "
    "and do not describe a flat or falling one as a decline in spending -- for "
    "those groups the linking practice is what has not moved. The section "
    "already carries a fixed sentence with the figures; do not write your own."
)


def activity_count_measures(view_name: str) -> set:
    """The view's measures whose UNIT is activities, read off _UNITS."""
    return {m for m, unit in _UNITS.get(view_name, {}).items() if unit == "activities"}


def _member_labels(finding: dict) -> set:
    """Every HDP member label on a finding: the commonness members and the
    exceptions together are the full member list."""
    labels = set()
    for cs in finding.get("commonness_sets") or []:
        labels.update(str(m) for m in cs.get("members", []))
    for exc in finding.get("exceptions") or []:
        labels.add(str(exc.get("member_label")))
    return labels


def count_caveat_applies(view_name: str, finding: dict, fiscal_years=None) -> bool:
    """Does §5.2's reporting-artifact caveat apply to this finding?

    `fiscal_years` is the set of fiscal-year values the finding's breakdown
    actually compares, which only the enrichment step can know (it holds the
    data). It is ignored unless fiscal_year IS the breakdown.
    """
    if view_name not in _COUNT_CAVEAT_VIEWS:
        return False

    # -- 2. an activity-count measure must be involved --
    counts = activity_count_measures(view_name)
    measure = finding.get("measure")
    if measure == "(varies)":
        # a measure-extending HDP: the members ARE the measures
        if not (_member_labels(finding) & counts):
            return False
    elif measure not in counts:
        return False

    # -- 3. fiscal years must be COMPARED, not filtered --
    breakdown = finding.get("breakdown")
    strategy = finding.get("extending_strategy")
    ext_dim = finding.get("extending_dimension")

    if strategy == "subspace" and ext_dim == "fiscal_year":
        years = _member_labels(finding)
    elif breakdown == "fiscal_year":
        years = set(fiscal_years or ())
    elif breakdown == "(varies)" and "fiscal_year" in _member_labels(finding):
        # a breakdown-extending HDP with fiscal_year among the breakdowns; no
        # fiscal_year filter can be present, so the whole axis is in play
        years = _FY_PRE_2023 | _FY_FROM_2023
    else:
        return False

    # -- 4. and the comparison must straddle the boundary --
    return bool(years & _FY_PRE_2023) and bool(years & _FY_FROM_2023)


# =============================================================================
# KNOWN EVENTS -- context the data does not carry (WP-D2c A5)
# =============================================================================
# Calibration session 1, ruling 5. The operator looked at view2's August 2020
# change point and its FY 2020-21 ramp and said "COVID". The engine cannot know
# that, and rule 4b of the prompt forbids the model from supplying it -- an
# invented cause is the error this pipeline guards hardest against.
#
# So the events are a table the department owns, in the domain pack, and the
# citation is a DATE TEST rather than a judgement: a change point inside an
# event window (or within the three months after it, because a resumption is as
# dated as an interruption) or a finding whose own slice pins a period that
# overlaps one. The note prints verbatim, in the deterministic reading note,
# and says the dates coincide -- never that the event caused the pattern.

KNOWN_EVENTS_PATH = os.path.join(
    BASE_DIR, "domain_pack_prdw", "known_events.csv")

# How long after an event ends a dated shift may still be attached to it. The
# COVID window closes 2020-06 and view2's Ganjam change point is at 2020-08.
_EVENT_RECOVERY_MONTHS = 3

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")
_FY_RE = re.compile(r"^(\d{4})-(\d{4})$")


def _month_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def _period_bounds(label) -> tuple | None:
    """(first month index, last month index) for '2020-08', '2020-Q3', '2024-2025'."""
    s = str(label).strip()
    m = _MONTH_RE.match(s)
    if m:
        i = _month_index(int(m.group(1)), int(m.group(2)))
        return i, i
    m = _QUARTER_RE.match(s)
    if m:
        first = _month_index(int(m.group(1)), (int(m.group(2)) - 1) * 3 + 1)
        return first, first + 2
    m = _FY_RE.match(s)
    if m and int(m.group(2)) == int(m.group(1)) + 1:
        first = _month_index(int(m.group(1)), 4)      # April-March
        return first, first + 11
    return None


_known_events_cache: list | None = None


def known_events(path: str | None = None) -> list:
    """The pack's event table. Unfilled TODO(SME) rows are skipped."""
    global _known_events_cache
    if path is None and _known_events_cache is not None:
        return _known_events_cache
    events = []
    target = path or KNOWN_EVENTS_PATH
    if os.path.exists(target):
        with open(target, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("event") or "").strip()
                start = _period_bounds((row.get("start_month") or "").strip())
                end = _period_bounds((row.get("end_month") or "").strip())
                if not name or name.startswith("TODO(SME)") or not start or not end:
                    continue
                events.append({
                    "event": name,
                    "start_label": row["start_month"].strip(),
                    "end_label": row["end_month"].strip(),
                    "start": start[0],
                    "end": end[1],
                    "note": (row.get("note") or "").strip(),
                })
    events.sort(key=lambda e: (e["start"], e["event"]))
    if path is None:
        _known_events_cache = events
    return events


# The temporal pattern types whose highlight IS a date.
_DATED_HIGHLIGHT_TYPES = frozenset({"CHANGE_POINT", "OUTLIER", "UNIMODALITY"})


def _finding_periods(finding: dict) -> list:
    """Every dated period this finding points AT: highlights and its own slice."""
    periods = []
    for cs in finding.get("commonness_sets") or []:
        if cs.get("pattern_type") in _DATED_HIGHLIGHT_TYPES:
            try:
                hl = ast.literal_eval(cs.get("highlight") or "()")
            except (ValueError, SyntaxError):
                hl = ()
            for item in (hl if isinstance(hl, tuple) else ()):
                for part in (item if isinstance(item, tuple) else (item,)):
                    bounds = _period_bounds(part)
                    if bounds:
                        periods.append((bounds, "the shift this finding reports"))
    for exc in finding.get("exceptions") or []:
        if exc.get("pattern_type") in _DATED_HIGHLIGHT_TYPES and exc.get("highlight"):
            try:
                hl = ast.literal_eval(exc["highlight"])
            except (ValueError, SyntaxError):
                hl = ()
            for item in (hl if isinstance(hl, tuple) else ()):
                for part in (item if isinstance(item, tuple) else (item,)):
                    bounds = _period_bounds(part)
                    if bounds:
                        periods.append((bounds, "an exception in this finding"))
    for dim_val in finding.get("base_subspace") or []:
        bounds = _period_bounds(dim_val[1])
        if bounds:
            periods.append((bounds, "the period this finding is restricted to"))
    return periods


def event_citations(findings: list, events: list | None = None) -> list:
    """The deterministic event sentences for a section's findings."""
    events = known_events() if events is None else events
    if not events:
        return []
    # One sentence per EVENT, not per finding and not per kind of overlap. A
    # section that touches the same window twice -- a change point just after
    # it and a fiscal year inside it -- was printing the whole note twice.
    hits: dict = {}
    for finding in findings or []:
        for (first, last), what in _finding_periods(finding):
            for ev in events:
                during = first <= ev["end"] and last >= ev["start"]
                after = ev["end"] < first <= ev["end"] + _EVENT_RECOVERY_MONTHS
                if not (during or after):
                    continue
                slot = hits.setdefault(ev["event"], {"ev": ev, "what": {}})
                slot["what"].setdefault(
                    what, "inside" if during else "in the months just after")

    out = []
    for name in sorted(hits):
        ev, what = hits[name]["ev"], hits[name]["what"]
        clauses = " and ".join(
            f"{w} falls {when}" for w, when in sorted(what.items())
        )
        out.append(
            f"A dated event overlaps this section: {clauses} the {ev['event']} "
            f"({ev['start_label']} to {ev['end_label']}). {ev['note']} The dates "
            f"coincide; this analysis does not establish that one produced the "
            f"other."
        )
    return out


def reading_note_block(view_name: str, findings: list | None = None) -> str:
    """The view's reading note as a markdown blockquote, or "" if it has none.

    One line, so the marker and the note body cannot be separated. Returned with
    a leading blank line so it concatenates straight onto the model's text.

    `findings` is the enriched list the section was written from. When any of
    them trips §5.2's test, the reporting-artifact sentence joins THIS note
    rather than becoming a second blockquote -- the prose gate expects exactly
    one marker per section, and a second callout would also read as two separate
    caveats where there is one set of conditions on reading the section. The
    A5 event citations and the A6 linkage sentence join it for the same reason.
    """
    note = READING_NOTES.get(view_name)
    if not note:
        return ""
    if findings and any(f.get("reporting_caveat") for f in findings):
        note = f"{note} {COUNT_CAVEAT_SENTENCE}"
    if findings and any(f.get("linkage_framing") for f in findings):
        note = f"{note} {LINKAGE_SENTENCE}"
    for sentence in event_citations(findings or []):
        note = f"{note} {sentence}"
    return f"\n\n{READING_NOTE_MARKER} {note}\n"


# =============================================================================
# VIEW VOCABULARY -- what each view's pipeline is NOT
# =============================================================================
# Every view has its own pipeline and its own words for it. view1 follows a
# planned activity from plan to sanction to spending to evidence. view2 is the
# cashbook: every voucher the Gram Panchayat wrote, including money that belongs
# to no planned activity. Neither holds the other's columns, so neither may
# borrow the other's words -- an earlier deployment's report called a subsidy
# release stall "the payment hold-up", which was about real figures and still
# sent an officer to the wrong pipeline.
#
# The distinction that matters most here is money basis. view2's
# `payment_amount` is Rs 68.58 crore of cashbook outflow; view1's
# `total_expenditure` is Rs 25.35 crore of voucher-linked spending on planned
# activities. Describing the first as spending on works overstates work spending
# by a factor of nearly three, and it is the easiest error in this deployment to
# make.
#
# The lists are deliberately narrow: a term appears only where the view has no
# column it could honestly describe.
#
# Used twice: told to the writer by vocabulary_rule() below, and checked in the
# finished report by src/prose_gate.py. Add a view here and both ends pick it up.

VIEW_VOCABULARY = {
    "view1": {
        "pipeline": ("the activity lifecycle -- a work is planned, sanctioned, "
                     "spent against and photographed"),
        "deny": [
            (r"\breceipts?\b",            "view2's receipt_amount, a cashbook inflow"),
            (r"\bcashbook\b",             "view2's cash basis"),
            (r"\binflows?\b",             "view2's receipt side"),
            (r"\bmonthly\b",              "view2's month axis"),
            (r"\bmonth-on-month\b",       "view2's month axis"),
            (r"\bseasonal(?:ity)?\b",     "view2's month axis"),
        ],
    },
    "view2": {
        "pipeline": ("the cashbook -- every voucher the Gram Panchayat wrote, "
                     "month by month, whether or not it belongs to a planned "
                     "activity"),
        "deny": [
            (r"\bwork completed\b",       "view1's completion status"),
            (r"\bcompleted works?\b",     "view1's completion status"),
            (r"\bongoing works?\b",       "view1's status_label"),
            (r"\babandoned\b",            "view1's abandonment status and funding"),
            (r"\bgeotagged\b",            "view1's photo evidence"),
            (r"\bphoto evidence\b",       "view1's evidence_uploads"),
            (r"\boverspend\w*\b",         "view1's and view3's overspend measures"),
            (r"\baction plan\b",          "view1's planned cost basis"),
            (r"\bplanned cost\b",         "view1's total_cost"),
            (r"\bcostless\b",             "view1's is_costless dimension"),
        ],
    },
    "view3": {
        "pipeline": ("the yearly report card -- one row per Gram Panchayat per "
                     "fiscal year, comparing who plans, who sanctions, who "
                     "spends and who evidences"),
        "deny": [
            (r"\bmonthly\b",              "view2's month axis"),
            (r"\bmonth-on-month\b",       "view2's month axis"),
            (r"\bmonth by month\b",       "view2's month axis"),
            (r"\bseasonal(?:ity)?\b",     "view2's month axis"),
        ],
    },
}

# The prose forms of the denied patterns, for the prompt. A regex is the right
# thing to check with and the wrong thing to show a writer.
_DENIED_PHRASES = {
    "view1": ["receipts", "cashbook", "inflows", "monthly", "month-on-month",
              "seasonality"],
    "view2": ["work completed", "completed works", "ongoing works", "abandoned",
              "geotagged", "photo evidence", "overspend", "action plan",
              "planned cost", "costless"],
    "view3": ["monthly", "month-on-month", "month by month", "seasonality"],
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

# =============================================================================
# The three PR&DW view descriptions.
# =============================================================================
# Content is PM-authored (WP-D2 brief, Appendix A) and transcribed as written,
# with two mechanical adaptations and one measured correction:
#
#   - Appendix A groups sibling columns under one heading ("gp_name /
#     block_name / district_name"). Each column gets its own key here, sharing
#     the constant above, so that "every config column has a glossary entry" is
#     a check a script can run rather than a claim a reader has to trust.
#   - `sc_amount` / `st_amount` carry the WP-D1 §5.5 finding. Appendix A says
#     only that the components are near-empty; WP-D1 measured the two source
#     tables to carry these values swapped relative to each other on all 21
#     affected activities. That patch is item 0 of WP-D1 §8's list and is the
#     one line where the Appendix A wording could produce a confidently wrong
#     equity statement rather than a vague one, so it is applied here. WP-D2b
#     (operator ruling on D-4) narrows the claim to a SUSPECTED swap: which side
#     is wrong - the labels or the data - is unconfirmed with the data team. The
#     ban on any SC-versus-ST comparison from these columns is unchanged, since
#     it holds under either reading. See WPD2_REPORT.md §6 and WPD2b_REPORT.md.
#
# The other five WP-D1 §8 patches (output_type_label, sanction_authority,
# asset_category_label, view3's n_tech_approvals, view2's sanctions_count) were
# already applied in Appendix A and are transcribed as they stand.

VIEW_DESCRIPTIONS = {
    "view1": {
        "title": "Activity Lifecycle - Every Planned Work and Its Money",
        "description": (
            "One row for each of the 12,704 activities the 20 Gram Panchayats "
            "planned between fiscal years 2020-2021 and 2025-2026, following each "
            "from plan (cost, funding source, LSDG theme, focus area) through "
            "administrative and technical sanction, voucher-linked spending, "
            "current status, and geotagged photo evidence. Three recorded skews "
            "are properties of the data, not findings: (1) costless activities "
            "(56% of rows) only began being reported from 2023-24, so activity "
            "counts jump ~8x at that boundary; (2) sanction records cover only "
            "~17% of activities - an activity without one is not shown to be "
            "unapproved; (3) only 17 activities are marked WORK COMPLETED, so "
            "completion is near-degenerate in this sample. Money columns carry "
            "their basis: PLANNED (action-plan cost and funding splits), "
            "SANCTIONED (approval amounts), SPENT (voucher-linked expenditure)."
        ),
        "audience_context": (
            "Key questions for the review meeting: which themes and focus areas "
            "carry the money, and in which districts or blocks does that pattern "
            "break? Where do sanctioned funds and actual spending diverge? Which "
            "sanctioning authorities dominate, and where? Where does spending run "
            "ahead of the plan (positive overspend), and is it the same Gram "
            "Panchayats each time?"
        ),
        "column_glossary": {
            "gp_name": _GP,
            "block_name": _BLOCK,
            "district_name": _DISTRICT,
            "fiscal_year": _FISCAL_YEAR,
            "theme": (
                "The LSDG theme (6 themes; 'Unmapped theme' where the focus area "
                "has no mapping - 986 activities)."
            ),
            "focus_area_name": (
                "The plan's focus area, 30 values (roads, drinking water, "
                "sanitation, education, ...)."
            ),
            "work_type_label": (
                "Decoded classification of the work: 4 values (New/Fresh, "
                "Maintenance, Upgradation, Unknown). 'Unknown' means the code has "
                "no decode on file."
            ),
            "activity_for_label": (
                "Who the work is for: 4 values. 'Unknown' means the code has no "
                "decode on file."
            ),
            "activity_type_label": (
                "The type of work: 2 values (Public Works, Beneficiary Oriented "
                "Programmes). 'Unknown' means the code has no decode on file."
            ),
            "output_type_label": (
                "The activity's output-type code. NO output_type code has a "
                "description on file, so every value reads 'Code 101' ... 'Code "
                "110' - eight opaque codes until the department supplies the "
                "decode."
            ),
            "status_label": (
                "Current recorded status. Heavily skewed: Activity Approved "
                "10,108; WORK ONGOING 2,110; WORK ABANDONED 420; UNDER APPROVAL "
                "36; WORK COMPLETED 17; 'Buildings' is a known mis-coding "
                "affecting 13 rows."
            ),
            "is_costless": (
                "'Costless' marks activities planned without a cost (training, "
                "campaigns, services); recorded only from 2023-24 onward."
            ),
            "tied_untied": (
                "Whether the sanctioned grant is Tied (earmarked, code 4249) or "
                "Untied (discretionary, codes 4211/4250); 'Other' is any other "
                "component."
            ),
            "sanction_authority": (
                "The sanctioning office, cleaned of spelling variants: Sarpanch, "
                "BDO, Engineer, Gram Panchayat, Panchayat Samiti - plus, in this "
                "sample, ten low-count free-text residues (15 records) the "
                "cleaning rule passes through, so 14 distinct values in all."
            ),
            "sanctioned_scheme_name": (
                "The scheme behind the sanction; 'Code N' means the code has no "
                "description on file."
            ),
            "fund_component_name": (
                "The fund component behind the sanction; 'Code N' means the code "
                "has no description on file."
            ),
            "asset_category_label": (
                "The asset the work creates - 27 named categories reach this view "
                "(several codes share a description and 8 codes have none); "
                "'Uncategorised' covers 8,439 activities: the two-thirds without "
                "asset data plus 21 whose code has no description. It is not "
                "itself an asset category."
            ),
            "n_activities": "UNIT: activities, COUNTED - one per planned activity.",
            "total_cost": (
                "UNIT: rupees, TOTALLED. PLANNED basis - the action-plan cost. "
                "Null for costless activities."
            ),
            "fund_tied_total": (
                "UNIT: rupees, TOTALLED. PLANNED basis - the tied share of the "
                "planned funding."
            ),
            "fund_untied_total": (
                "UNIT: rupees, TOTALLED. PLANNED basis - the untied share of the "
                "planned funding."
            ),
            "fund_abandoned_total": (
                "UNIT: rupees, TOTALLED. PLANNED basis - funding recorded against "
                "abandoned works (Rs 6.17 crore in this sample)."
            ),
            "work_proposed_cost": (
                "UNIT: rupees, TOTALLED. SANCTIONED basis - present only for the "
                "~17% with sanction records."
            ),
            "fund_sanctioned_total": (
                "UNIT: rupees, TOTALLED. SANCTIONED basis - present only for the "
                "~17% with sanction records."
            ),
            "total_expenditure": (
                "UNIT: rupees, TOTALLED. SPENT basis - voucher-linked actual "
                "spending; reconciles exactly with the cashbook links."
            ),
            "gen_amount": (
                "UNIT: rupees, TOTALLED. SPENT basis, the general component."
            ),
            "sc_amount": (
                "UNIT: rupees, TOTALLED. SPENT basis, social-category component. "
                "READ THE LABEL WITH CARE: a SWAP IS SUSPECTED between this "
                "column and st_amount on all 21 activities that carry either "
                "value - the two source tables carry these values swapped "
                "relative to each other; whether the labels or the data are "
                "wrong is unconfirmed with the data team. Never make a Scheduled "
                "Caste versus Scheduled Tribe comparison from these two columns. "
                "The combined figure is Rs 36.67 lakh across 21 activities "
                "either way, which is too thin to carry an equity finding at all."
            ),
            "st_amount": (
                "UNIT: rupees, TOTALLED. SPENT basis, social-category component. "
                "A SWAP WITH sc_amount IS SUSPECTED and unconfirmed - see that "
                "entry. Never make a Scheduled Caste versus Scheduled Tribe "
                "comparison from these two columns."
            ),
            "overspend_vs_plan": (
                "UNIT: rupees, TOTALLED, SIGNED (SPENT minus PLANNED). Positive = "
                "spending above plan; negative = unspent plan. The "
                "over/under-spend detector."
            ),
            "overspend_vs_sanction": (
                "UNIT: rupees, TOTALLED, SIGNED (SPENT minus SANCTIONED); "
                "meaningful only for the sanctioned ~17%."
            ),
            "is_started": _ACTIVITY_FLAG,
            "is_completed": _ACTIVITY_FLAG + " Only 17 sample-wide.",
            "is_ongoing": _ACTIVITY_FLAG,
            "is_abandoned": _ACTIVITY_FLAG,
            "is_under_approval": _ACTIVITY_FLAG,
            "is_admin_approved": _ACTIVITY_FLAG,
            "has_technical_approval": _ACTIVITY_FLAG,
            "has_progress_evidence": _ACTIVITY_FLAG,
            "evidence_uploads": (
                "UNIT: geotagged photo uploads, TOTALLED (8,267 uploads across "
                "1,675 activities)."
            ),
            "trainees_total": (
                "UNIT: people, TOTALLED - for the small subset recording training "
                "detail (1,034 activities)."
            ),
            "beneficiaries_expected": (
                "UNIT: people, TOTALLED - for the small subset recording "
                "community-service detail (763 activities)."
            ),
        },
    },
    "view2": {
        "title": "Monthly Money Flows by Gram Panchayat",
        "description": (
            "One row per Gram Panchayat per calendar month across the full "
            "cashbook window (April 2020 - March 2026, 72 months - 1,440 rows "
            "including months with no transactions, which appear as zeros and are "
            "themselves meaningful). CASHBOOK basis: every voucher the GP "
            "recorded, including flows not tied to planned activities. This is "
            "the view for trends, seasonality, sudden shifts, and outlier months. "
            "One pattern is real and known: March, the fiscal year-end, "
            "concentrates payments every year."
        ),
        "audience_context": (
            "Key questions: Is money moving steadily, or in year-end bursts? "
            "Which GPs' outflows have shifted sharply, and when? Where are "
            "receipts arriving but payments stalling - or payments running with "
            "no matching receipts? Which blocks or districts move money "
            "differently from the rest?"
        ),
        "column_glossary": {
            "gp_name": _GP,
            "block_name": _BLOCK,
            "district_name": _DISTRICT,
            "month": "Calendar month ('YYYY-MM'), April 2020 to March 2026.",
            "quarter": "Calendar quarter ('YYYY-Qn').",
            "fiscal_year": (
                "April-March year, full string form ('2024-2025'), derived from "
                "the calendar month so a zero-filled cell still carries one."
            ),
            "payment_amount": (
                "UNIT: rupees, TOTALLED. CASHBOOK basis - all outflows in the "
                "month."
            ),
            "receipt_amount": (
                "UNIT: rupees, TOTALLED. CASHBOOK basis - all inflows in the "
                "month."
            ),
            "payment_count": "UNIT: vouchers, COUNTED - outflow vouchers.",
            "receipt_count": "UNIT: vouchers, COUNTED - inflow vouchers.",
            "activity_linked_expenditure": (
                "UNIT: rupees, TOTALLED. SPENT basis - the subset of payments "
                "linked to planned activities."
            ),
            "sanctions_count": (
                "UNIT: sanctions, COUNTED. SANCTIONED basis, by sanction month. "
                "This view counts 2,040 of the 2,101 sanctions: 61 are dated "
                "outside the cashbook's 72-month window (14 before it, 47 after, "
                "including one future-dated sanction). The yearly report card "
                "counts by fiscal year and carries the full 2,101 - two time "
                "axes, two totals, both correct."
            ),
            "sanctioned_amount": (
                "UNIT: rupees, TOTALLED. SANCTIONED basis, by sanction month - "
                "the same 2,040 sanctions as sanctions_count."
            ),
            # WP-D2c A4, transcribed verbatim from the brief's Appendix.
            "payment_amount_mean": (
                "UNIT: rupees, AVERAGED per GP-month. The same rupee column as "
                "payment_amount, normalised by GP-months: the typical monthly "
                "outflow of one Gram Panchayat in the group, independent of how "
                "many GPs or months the group contains. Use this, not the total, "
                "to compare places of different size."
            ),
            "receipt_amount_mean": (
                "UNIT: rupees, AVERAGED per GP-month. As payment_amount_mean, "
                "for inflows."
            ),
        },
    },
    "view3": {
        "title": "Gram Panchayat Report Card by Year",
        "description": (
            "One row per Gram Panchayat per fiscal year - all 20 GPs x all 6 "
            "years, 120 rows, including GP-years with nothing recorded (zeros are "
            "the point: a GP with activities but no sanctions, or plans but no "
            "spending, is exactly what this view exists to surface - one sample "
            "GP has 640 activities and zero administrative approvals on record). "
            "The institutional comparison table: who plans, who sanctions, who "
            "spends, who uploads evidence, year over year."
        ),
        "audience_context": (
            "Key questions: Which GPs convert plans into sanctioned, executed, "
            "evidenced work - and which consistently do not? Is a GP's weak year "
            "a one-off or a trajectory? Do neighbouring GPs in the same block "
            "behave alike? Where is money spent with thin photo evidence?"
        ),
        "column_glossary": {
            "gp_name": _GP,
            "block_name": _BLOCK,
            "district_name": _DISTRICT,
            "fiscal_year": _FISCAL_YEAR,
            "n_plans": "UNIT: GPDP plans, COUNTED (Main + Supplementary).",
            "n_activities": "UNIT: activities, COUNTED - one per planned activity.",
            "n_costed": (
                "UNIT: activities, COUNTED - those planned with a cost."
            ),
            "n_costless": (
                "UNIT: activities, COUNTED - those planned without one, recorded "
                "only from 2023-24 onward."
            ),
            "planned_cost": "UNIT: rupees, TOTALLED, PLANNED basis.",
            "sanctioned_total": (
                "UNIT: rupees, TOTALLED, SANCTIONED basis (~17% coverage caveat "
                "as in view1)."
            ),
            "expenditure_total": "UNIT: rupees, TOTALLED, SPENT basis.",
            "overspend_vs_plan": (
                "UNIT: rupees, TOTALLED, SIGNED (SPENT minus PLANNED), aggregated "
                "per GP-year. Positive = spending above plan; negative = unspent "
                "plan."
            ),
            "overspend_vs_sanction": (
                "UNIT: rupees, TOTALLED, SIGNED (SPENT minus SANCTIONED), "
                "aggregated per GP-year; meaningful only for the sanctioned ~17%."
            ),
            "payment_amount": "UNIT: rupees, TOTALLED, CASHBOOK basis.",
            "receipt_amount": "UNIT: rupees, TOTALLED, CASHBOOK basis.",
            "n_admin_approvals": (
                "UNIT: sanction records, COUNTED. Zero can mean nothing was "
                "sanctioned OR nothing was recorded - the 17%-coverage caveat "
                "applies."
            ),
            "n_tech_approvals": (
                "UNIT: sanction records, COUNTED. Zero can mean nothing was "
                "sanctioned OR nothing was recorded. This totals 2,095, not the "
                "2,134 technical-approval records: 39 sit on activities with no "
                "administrative approval and are invisible to this view - "
                "deliberately, so the Ask chatbot and Discover report the same "
                "number."
            ),
            "n_completed": (
                "UNIT: activities, COUNTED (completion near-degenerate in sample "
                "- see view1)."
            ),
            "n_ongoing": "UNIT: activities, COUNTED.",
            "n_abandoned": "UNIT: activities, COUNTED.",
            "n_with_evidence": (
                "UNIT: activities, COUNTED - those with at least one geotagged "
                "photo upload."
            ),
            "evidence_uploads": (
                "UNIT: geotagged photo uploads, TOTALLED (8,267 uploads across "
                "1,675 activities)."
            ),
        },
    },
}


# =============================================================================
# STEP 2a: SIZE SHARES BEHIND A GEOGRAPHY TOTAL
# =============================================================================
# Size read as performance is the failure this block exists to prevent.
#
# A TOTALLED measure broken down by Gram Panchayat, block or district almost
# always ranks those places by how much they do at all. "Chikilli spends the
# least" and "Chikilli plans the fewest activities" are the same sentence twice
# when Chikilli is a small Gram Panchayat, and the first one reads as a delivery
# failure while the second reads as arithmetic. The AP deployment hit exactly
# this shape with social categories -- a finding that was true, a reading that
# was wrong, and nothing in the enrichment that let the model tell the
# difference, because it was handed the totals and not the volumes behind them.
#
# So for any geography breakdown of a SUM, the group's share of the view's own
# VOLUME travels with the total, and rule 2b of the prompt requires the two to
# be stated together. The model can then write size as size.
#
# The volume is the view's own count column -- activities for view1 and view3,
# payment vouchers for view2 -- read from the same parquet the measure came
# from, so these shares cannot disagree with the view's published figures.
# Every figure leaves here as a rendered string, per STEP 0.

# The count a view's other measures should be read against.
_VOLUME_MEASURE = {
    "view1": "n_activities",
    "view2": "payment_count",
    "view3": "n_activities",
}

# Which BREAKDOWNS get the comparison. It was the geography spine only, on the
# argument that a breakdown by theme or status is a property of the work rather
# than a size question. Calibration session 1 refuted that on two of its own
# findings: "Activity Approved has the LOWEST overspend_vs_plan among status
# values" and "Maintenance and New/Fresh are lowest in overspend_vs_plan among
# work types" were both labelled spurious with the same note -- unspent money
# sits where most activities sit. Those are the geography confound exactly, on
# a non-geography axis, and the reader had no volume figure to see it with.
#
# So the comparison now travels with EVERY categorical breakdown of a total.
# Where the volume is evenly spread the block simply shows that, and rule 2b
# already requires the model to say so plainly rather than to hunt for a gap.
# Temporal breakdowns are excluded: a month is not bigger than another month in
# the sense this measures, and the view's own reading note handles the calendar.
_SIZE_CONFOUND_BREAKDOWNS = {"gp_name", "block_name", "district_name"}

# The prose rule that goes with the block above. Defined ONCE and imported by
# phase5c_gamma_reports, for the same reason the enrichment function is shared:
# two copies of a rule about the same stats key drift, and a rule that names a
# key the enrichment does not emit is worse than no rule at all.
POPULATION_SHARE_RULE = """2b. SIZE IS NOT PERFORMANCE. Where a finding carries 'stats.size_share', it is a TOTAL broken down by some group -- a Gram Panchayat, a block, a district, a work type, a status -- and that block gives each group's share of the volume behind those totals. A total across groups of different sizes ranks them by SIZE: the biggest planner holds the biggest total almost by definition, and so does the status that most activities sit in.
   - Whenever you quote such a total, quote the group's share of the volume alongside it, from 'share_of_volume', in the same sentence. Correct: "Chikilli accounts for 10.9% of spending, against 5.0% of the activities planned." The reader now knows which part is size and which part is not
   - Wrong: "Chikilli and Badakodanda lead on spending, Kuluma trails." True, and it reads as a delivery gap when it may be a headcount fact
   - The smallest Gram Panchayat will have the smallest total of everything, and the largest category will have the largest. That is arithmetic, not a finding, and it must never be written as though it were one. Do not call such a split a gap, a shortfall, an imbalance, an under-performance or a disparity
   - When the two shares are close, SAY SO PLAINLY -- "in proportion to what it planned", "in line with its share of the work". A group carrying its numerical share is a real and reportable result, not a failure to find something, and matching is the common case here
   - Only call a divergence a gap when the two shares actually diverge, and say by how much using the figures given. That IS the finding when it happens, and it is the one to lead with
   - Copy the percentages verbatim like every other figure. 'scope' tells you which slice the share describes and 'volume_in_scope' how much volume is behind it. If 'base_not_narrowed_by' is present, the share covers a WIDER slice than the finding does -- name the slice you are describing so the reader is not misled

2c. PREFER THE PER-UNIT FIGURE WHERE ONE IS OFFERED. Where a finding carries 'stats.intensity_companion', the same rupees are also available as an average per Gram Panchayat per month, which does not grow with the number of Gram Panchayats a place contains.
   - Quote the companion figure alongside the total whenever you rank places, and prefer it when you say which place stands out. A district leading on total outflow because it holds four of the sample's twenty Gram Panchayats is not a finding; a district whose typical Gram Panchayat moves more money each month than its neighbours' is
   - Copy those figures verbatim too, and keep the words that come with them: one is a total, the other is a typical month for one Gram Panchayat. Never add them together and never present one as the other"""


_view_df_cache: dict = {}


def _view_df(view_name: str) -> pd.DataFrame:
    """The view's own rows, cached. The volume shares are read from the same
    parquet the measures come from, so they cannot disagree with them."""
    if view_name not in _view_df_cache:
        _view_df_cache[view_name] = pd.read_parquet(
            VIEW_CONFIGS[view_name].parquet_path
        )
    return _view_df_cache[view_name]


def volume_share(view_name: str, breakdown: str, measure: str, base_subspace) -> dict | None:
    """Each group's share of the view's volume, for a categorical breakdown.

    Returns None when the comparison does not apply -- a temporal breakdown, a
    view with no volume column, or a finding that is ALREADY about the volume
    measure, where the share would just restate the finding.

    The scope is narrowed by whichever base-subspace filters the view carries;
    a filter it cannot honour is NAMED in the returned block rather than
    silently ignored, because a share quoted against the wrong base is exactly
    the error this is here to stop.
    """
    config = VIEW_CONFIGS.get(view_name)
    if config is None or breakdown in config.temporal_dimensions:
        return None
    if breakdown == "(varies)":
        return None
    volume = _VOLUME_MEASURE.get(view_name)
    if volume is None or volume == measure:
        return None

    df = _view_df(view_name)
    if volume not in df.columns or breakdown not in df.columns:
        return None

    applied, unapplied = [], []
    if isinstance(base_subspace, list):
        for dim_val in base_subspace:
            dim, val = dim_val[0], dim_val[1]
            if dim == breakdown:
                continue
            if dim in df.columns:
                df = df[df[dim] == val]
                applied.append(f"{val}")
            else:
                unapplied.append(f"{dim}={val}")

    if len(df) == 0:
        return None

    counts = df.groupby(breakdown)[volume].sum().sort_values(ascending=False)
    total = float(counts.sum())
    if total <= 0:
        return None

    block = {
        "what_this_is": (
            f"each place's share of the {format_measure(view_name, volume, total)} "
            "behind the totals above - the volume base, not a performance figure"
        ),
        "scope": (" and ".join(applied) + " only") if applied else "the whole view",
        "volume_in_scope": format_measure(view_name, volume, total),
        "share_of_volume": {
            str(k): f"{v / total * 100:.1f}%" for k, v in counts.items()
        },
    }
    if unapplied:
        block["base_not_narrowed_by"] = (
            "this view has no such column, so this share is NOT restricted to: "
            + ", ".join(unapplied)
            + ". Say which slice the share describes if you quote it here."
        )
    return block


# =============================================================================
# STEP 2b: THE INTENSITY COMPANION (WP-D2c A4)
# =============================================================================
# The size-share block above lets a reader SEE the confound. The intensity
# companion removes it: the same rupees per Gram Panchayat per month, which is
# what the operator asked for when they said "let's think about a denominator".
# It is offered only where the view has an AVG-aggregated alias of the very
# column the finding totals -- view2's payment_amount_mean and
# receipt_amount_mean -- so the two figures are the same money, not two
# measures that happen to be near each other.

_INTENSITY_COMPANION = {
    "view2": {"payment_amount": "payment_amount_mean",
              "receipt_amount": "receipt_amount_mean"},
}


def intensity_companion(view_name: str, breakdown: str, measure: str,
                        base_subspace) -> dict | None:
    """The per-GP-month average behind a money total, by the same breakdown."""
    companion = _INTENSITY_COMPANION.get(view_name, {}).get(measure)
    if companion is None:
        return None
    config = VIEW_CONFIGS.get(view_name)
    if config is None or breakdown in config.temporal_dimensions or breakdown == "(varies)":
        return None

    df = _view_df(view_name)
    column = config.get_column(companion)
    if column not in df.columns or breakdown not in df.columns:
        return None
    if isinstance(base_subspace, list):
        for dim_val in base_subspace:
            dim, val = dim_val[0], dim_val[1]
            if dim != breakdown and dim in df.columns:
                df = df[df[dim] == val]
    if len(df) == 0:
        return None

    means = df.groupby(breakdown)[column].mean().sort_values(ascending=False)
    rows  = df.groupby(breakdown)[column].size()
    return {
        "measure": companion,
        "what_this_is": (
            f"the same rupees as {measure}, averaged per Gram Panchayat per "
            "month instead of totalled - a typical month for one Gram "
            "Panchayat, which does not grow with how many of them a group holds"
        ),
        "how_aggregated": "averaged across rows - a per-unit figure, not a total",
        "values": {
            str(k): format_measure(view_name, companion, v)
            for k, v in means.head(5).items()
        },
        "gp_months_behind_each_average": {
            str(k): _num(int(rows[k]), 0) for k in means.head(5).index
        },
    }


# =============================================================================
# STEP 2: ENRICH CANDIDATES WITH QUANTITATIVE STATS
# =============================================================================

def _mark_count_caveat(view_name: str, c: dict, fiscal_years=None) -> None:
    """Set the finding's §5.2 flag, and tell the writer about it where it fires.

    Called on EVERY candidate, including the ones whose stats block is a note
    rather than a distribution: a measure-extending HDP still compares activity
    counts across years, and the caveat is about what the finding compares, not
    about how much of it could be enriched.
    """
    applies = count_caveat_applies(view_name, c, fiscal_years)
    c["reporting_caveat"] = applies
    if applies and isinstance(c.get("stats"), dict):
        c["stats"]["reporting_artifact"] = COUNT_CAVEAT_FOR_PROMPT


def _measures_involved(finding: dict) -> set:
    """The measure(s) a finding ASSERTS something about.

    For a measure-extending HDP that is the commonness members only, not the
    exceptions: view2's "six of nine measures peak in March" is not a finding
    about activity-linked expenditure just because linked expenditure is the
    one that does something else.
    """
    measure = finding.get("measure")
    if measure and measure != "(varies)":
        return {measure}
    members = set()
    for cs in finding.get("commonness_sets") or []:
        members.update(str(m) for m in cs.get("members", []))
    return members


def _mark_framing_rules(view_name: str, c: dict, config: ViewConfig) -> None:
    """A3 and A6: the two deterministic framing rules, keyed to the finding.

    Both are set on the finding AND handed to the writer inside its stats, and
    both have a fixed sentence in the section's reading note. The writer is
    told not to write its own version of either, for the reason every caveat
    in this file is deterministic: a paraphrase of a caveat is where the damage
    is done.
    """
    stats = c.get("stats") if isinstance(c.get("stats"), dict) else None

    # A6 -- activity-linked expenditure, on any temporal reading of it
    temporal = (
        c.get("pattern_type") in _TEMPORAL_PATTERN_TYPES
        or c.get("breakdown") in list(config.temporal_dimensions) + ["(varies)"]
    )
    linkage = LINKAGE_MEASURE in _measures_involved(c) and temporal
    c["linkage_framing"] = linkage
    if linkage and stats is not None:
        stats["linkage_framing"] = LINKAGE_FOR_PROMPT

    # A3 -- EVENNESS on a signed money measure
    evenness = (
        c.get("pattern_type") == "EVENNESS"
        and bool(_measures_involved(c) & SIGNED_MONEY_MEASURES)
    )
    c["evenness_framing"] = evenness
    if evenness and stats is not None:
        stats["evenness_framing"] = EVENNESS_FOR_PROMPT


_TEMPORAL_PATTERN_TYPES = frozenset({
    "TREND", "OUTLIER", "SEASONALITY", "CHANGE_POINT", "UNIMODALITY",
})

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
            # ... but the size confound does NOT vary with the measure. "Ganjam
            # has the highest (varies) among district_name values" is a place
            # ranking whatever it ranks on, and calibration session 1 labelled
            # exactly that finding size-driven -- Ganjam holds 4 of the 20
            # sample Gram Panchayats. The volume shares behind the breakdown
            # are the same figures for every member of the HDP, so they can be
            # given here even when the aggregation cannot (A4 / rule 2b).
            if breakdown != "(varies)":
                size_share = volume_share(view_name, breakdown, measure, base_subspace)
                if size_share:
                    c["stats"]["size_share"] = size_share
                # and the same for the per-GP-month companion: where the HDP's
                # members include a money total that has one, the size-free
                # version of that member is the figure the reader needs
                for member in sorted(_measures_involved(c)):
                    companion = intensity_companion(
                        view_name, breakdown, member, base_subspace)
                    if companion:
                        c["stats"].setdefault("intensity_companion", companion)
                        break
            _mark_count_caveat(view_name, c)
            _mark_framing_rules(view_name, c, config)
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
            _mark_count_caveat(view_name, c)
            _mark_framing_rules(view_name, c, config)
            enriched.append(c)
            continue

        # Aggregate using the measure's configured agg type, off the column the
        # measure reads -- an intensity measure is an alias of its total (A4)
        agg_type = config.get_agg(measure)
        column   = config.get_column(measure)
        if agg_type == "avg":
            dist = filtered.groupby(breakdown)[column].mean()
        else:
            dist = filtered.groupby(breakdown)[column].sum()

        dist = dist.dropna().sort_values(ascending=False)

        if len(dist) == 0:
            c["stats"] = {"note": "No data after filtering"}
            _mark_count_caveat(view_name, c)
            _mark_framing_rules(view_name, c, config)
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

            # A geography breakdown of a TOTAL ranks places by their own size
            # unless the volume travels with it. See STEP 2a.
            size_share = volume_share(view_name, breakdown, measure, base_subspace)
            if size_share:
                stats["size_share"] = size_share

            # ... and where the same rupees exist as a per-GP-month average,
            # the size-free figure travels with the total (A4).
            companion = intensity_companion(view_name, breakdown, measure, base_subspace)
            if companion:
                stats["intensity_companion"] = companion

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
            counts = filtered.groupby(breakdown)[column].count()
            counts = counts.reindex(dist.head(5).index).dropna()
            stats["rows_behind_each_average"] = {
                str(k): _num(int(v), 0) for k, v in counts.items()
            }

        c["stats"] = stats
        # §5.2: only a breakdown BY fiscal_year can tell us which years this
        # finding actually compares, and `dist` is where that lives.
        _mark_count_caveat(
            view_name, c,
            list(dist.index) if breakdown == "fiscal_year" else None,
        )
        _mark_framing_rules(view_name, c, config)
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

    return f"""You are writing the findings section of an analytical report on Gram Panchayat development planning and spending in Odisha, India, for the Department of Panchayati Raj & Drinking Water. The data covers the Gram Panchayat Development Plan (GPDP): the works and services a Gram Panchayat plans each year, the administrative and technical sanctions that approve them, the money actually paid out of the Gram Panchayat cashbook, and the geotagged photographs recorded as evidence.

## Your Audience
An officer of the Department of Panchayati Raj & Drinking Water who takes these findings into the departmental review meeting, where district and block officials are held to account for how their Gram Panchayats plan, sanction and spend. They are non-technical -- they understand the GPDP cycle, sanctioning authority and grant components, but not data science terminology. They want to know: what did the data reveal, why does it matter for delivery, and what should they put to the district and block officials in front of them.

## This Section: {view_info['title']}

{view_info['description']}

{view_info['audience_context']}

## Column Glossary
{json.dumps(view_info['column_glossary'], indent=2)}

## Ranked Findings (from automated pattern analysis)

The following findings were automatically discovered and ranked by analytical importance. Each finding represents a pattern that holds consistently across multiple subgroups, with any exceptions noted.

Key concepts:
- "commonness" = a pattern that holds for the majority of subgroups (e.g., "in 14 of the 16 blocks, drinking water is the focus area carrying the most planned cost")
- "exceptions" = specific subgroups where the pattern breaks
- "HIGHLIGHT_CHANGE" exception = the same pattern type but with a different leading value
- "TYPE_CHANGE" exception = a completely different pattern applies
- "NO_PATTERN" exception = no clear pattern exists in that subgroup

{findings_json}

## Instructions

Write a clear, readable summary of these findings for the programme officer. Follow these rules:

1. STRUCTURE: Organise findings into 3-5 thematic groups (e.g., "Where the Planned Money Goes", "Sanction and Spending Out of Step", "Works That Stall", "Evidence on File"). Do not list findings by rank number.

2. NUMBERS -- READ THIS BEFORE YOU WRITE ANY FIGURE:
   Every number in the 'stats' field has ALREADY been formatted for print, with its unit attached. Your job is to choose which figures to quote and to explain what they mean. It is NOT to do arithmetic.
   - Copy each formatted string VERBATIM, exactly as it appears -- the same digits, the same grouping, the same unit word. "Rs 20.25 crore" is written "Rs 20.25 crore"
   - NEVER convert between units. Do not turn rupees into lakh or crore yourself, do not turn a percentage into a fraction, do not turn a count of activities into a share. The conversion has been done
   - NEVER re-derive, add, subtract, average, or compute a percentage of your own from the figures given. If a number you want is not in the stats, do not produce it -- write around it
   - Digit grouping is Indian throughout (12,34,567 -- not 1,234,567) and it is already applied. Do not re-group anything, and keep one style across the whole section
   - Each measure's stats carry 'measure_unit' and 'how_aggregated'. Use them: a TOTALLED figure is an absolute that grows with the size of the group, an AVERAGED figure is a per-unit rate that does not. Never describe a total as though it were a rate, or a rate as though it were a total
   - Where 'rows_behind_each_average' is given, it is the number of records behind each average. If it is small, say so when you quote the average

{POPULATION_SHARE_RULE}

3. LANGUAGE:
   - Write in English. Use plain English, no jargon
   - NEVER print a raw code or an internal column name in the prose. Use the Column Glossary above to translate every value into words: name Gram Panchayats, blocks and districts in full, give a grant component and a scheme its full name, and say "administrative sanction" or "technical sanction" rather than an approval flag's column name
   - Several dimensions in this data are UNDECODED and reach you as literal code strings -- 'Code 101', 'Code 1518', 'Code 3880'. Do not print them, and do not invent a meaning for them. If a finding rests on one, say that the category has no description on file and that the department has to supply the decode before the finding can be read
   - The unit is already inside every formatted figure. Do not add a second unit word after it, and do not strip the one that is there
   - Explain what each finding means operationally
   - Name specific Gram Panchayats, blocks and districts when they appear as exceptions
   - Never print a personal name, an Aadhaar number, a bank account or any other personal identifier. One dimension, the sanctioning authority, is free text and could in principle carry one; if a value looks like a person's name rather than an office, do not print it -- say "an uncleaned sanctioning-authority value"

4. EXCEPTIONS ARE THE STORY: Universal patterns (100% commonness) are context. Exceptions are where actionable intelligence lives. Highlight them prominently.

4b. NEVER INVENT A CAUSE. This is the hardest rule in this list and the easiest to break by accident. The findings tell you WHAT is happening, WHERE, and HOW MUCH. They contain no information whatever about WHY. You must not supply one.
   - Do not write that something happened "because", "due to", "driven by", "as a result of", "reflecting", or "explained by" anything. Those phrases are claims about causation that the analysis did not make
   - Do not reach for a plausible mechanism to tidy up a finding. A previous version of this report explained a pattern as an artefact of "record-edge months". Nothing in the data said that. It was invented, it was wrong, and it would have sent an officer looking in the wrong place
   - Do not attribute a pattern to administrative capacity, staffing, awareness, monsoon or terrain, contractor availability, election years, or any other unstated factor
   - Where a cause matters - and it usually does - write it as a QUESTION FOR THE OFFICER, not as a statement. "Chikilli has 640 activities and no administrative approvals on record; is nothing being sanctioned, or is nothing being entered?" is correct. "Chikilli is not sanctioning because the block office is understaffed" is not, and neither is "likely reflecting staffing pressure"
   - Hedging does not make an invented cause acceptable. "Possibly", "may reflect", "suggests that", "appears to be driven by" are the same violation in softer words
   - A recorded zero is the sharpest case of this rule. This data cannot tell you whether nothing happened or whether nothing was entered, and those call for different action from the officer. Where a zero or a near-zero is the finding, say that both readings are open and put the question
   - The one thing you MAY state as fact is what the glossary or section description explicitly tells you (for example, that a code has no description on file, or that sanction records cover about one activity in six). Those are established by the data build, not inferred by you

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
   - Keep each money figure on the basis its glossary entry gives it -- PLANNED (what the action plan proposed), SANCTIONED (what was approved) or SPENT (what left the cashbook against a voucher). They are three different numbers about the same work, and swapping them silently is the most damaging error you can make here. Name the basis in the sentence
   - Where a finding carries 'stats.reporting_artifact', 'stats.linkage_framing' or 'stats.evenness_framing', read it before writing a word about that finding. Each is a fixed instruction about how that finding must be presented, it is there because presenting it the obvious way would be wrong, and the section already carries the matching fixed sentence -- so follow it and do not write your own version of it
   - End with 2-3 specific follow-up questions the officer should raise at the next departmental review

9. FORMATTING RULES (strictly follow these):
   - Use ### for thematic section headers (e.g., ### Where the Planned Money Goes)
   - Never use **text** as a substitute for a header
   - Use inline bold sparingly — only for specific Gram Panchayat, block or district names that are exceptions or outliers
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
        # rule 2b exists for ("Chikilli has the highest expenditure_total"), and
        # this is the OPENING section, the part most certain to be read. So the
        # volume shares travel with a geography breakdown of a SUM here too.
        cfg = VIEW_CONFIGS.get(r["view"])
        if cfg is not None and cfg.get_agg(r["measure"]) == "sum":
            size_share = volume_share(
                r["view"], r["breakdown"], r["measure"], r["base_subspace"]
            )
            if size_share:
                f["size_share"] = size_share
        findings.append(f)

    return f"""You are writing the OPENING section of an analytical report on Gram Panchayat development planning and spending in Odisha, India, for the Department of Panchayati Raj & Drinking Water. Everything after this section goes area by area; this section is the one place the whole picture is looked at together.

## Your Audience
An officer of the Department of Panchayati Raj & Drinking Water who takes these findings into the departmental review meeting, where district and block officials answer for how their Gram Panchayats plan, sanction and spend. Non-technical: they understand the GPDP cycle and sanctioning authority, not data science.

## What this section is

Each analytical area was mined separately, and each was ranked against its own totals. The findings below are the top of a single combined ordering across all of them, so that what a reader meets first is not decided by which area a finding happened to come from.

The combined ordering weights each area by how much of the programme it covers, listed here:

{json.dumps(weighting['weights'], indent=2)}

That weighting is a judgement, not a measurement. You do not need to explain it and you must not defend it; if it is worth a sentence, say only that the areas were combined in proportion to how much of the programme each covers.

## The top findings across the programme

{json.dumps(findings, indent=2, default=str)}

## Instructions

Write 350-550 words. Rules:

1. Open with the single most important thing the analysis found across the whole programme. Not a summary of the method, not "this report covers" - the finding itself.

2. Group what follows into 3-4 themes and connect them. This is a narrative, not a list, and it must not repeat the per-area sections that follow it - it frames them.

3. NEVER INVENT A CAUSE. The findings say what, where and how much. They say nothing about why, and you must not supply it. No "because", "due to", "driven by", "reflecting", "as a result of". No mechanism offered to tidy a finding up. Hedging does not help: "may reflect" and "likely driven by" are the same violation. Where the cause matters, put it as a question for the officer to raise.

4. Do not quote a numeric figure in this section unless it appears verbatim in the finding text above. Do not compute, convert or re-derive anything. The detailed figures live in the sections that follow.

4b. SIZE IS NOT PERFORMANCE. Some findings carry a 'size_share' block. Those total something across Gram Panchayats, blocks or districts, and a total across places of different sizes ranks them by SIZE -- the biggest planner holds the biggest total almost by definition. A finding worded "Chikilli and Badakodanda lead on spending" is a size fact, and writing it as a delivery result would be wrong.
   - If you carry such a finding into this section, carry its volume share with it, copied verbatim from 'share_of_volume'. "Chikilli accounts for the largest share of spending, in proportion to the share of activities it plans" is right; the first half alone is not
   - Do not call such a split a gap, a shortfall, an imbalance, an under-performance or a disparity unless the two shares actually differ, and then say by how much
   - If a finding has no 'size_share' block, this rule does not apply to it

5. Name Gram Panchayats, blocks and districts in full plain English. Never print an internal column name, an undecoded 'Code NNN' value, or any personal identifier.

5b. A ZERO IS NOT A VERDICT. Where a finding turns on something being zero or near zero -- no sanctions recorded, no photo evidence, no completed works -- this data cannot tell you whether nothing happened or whether nothing was entered. Say that both readings are open and put it as a question. Do not write it as a failure to deliver.

6. Do not mention scores, ranks, weights beyond the one sentence permitted above, or any technical analysis terminology.

7. End with the three questions you would put on the agenda of the next departmental review.

8. FORMATTING: ### for any sub-headers. No bold except for a Gram Panchayat, block or district name that is an exception. Plain prose otherwise.
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


# =============================================================================
# THE DATA-QUALITY ANNEX (WP-D2c A7) -- deterministic, not LLM-authored
# =============================================================================
# Operator ruling, calibration session 1 item 7: a trend on a column with
# almost no non-zero events is a recording observation and it STAYS VISIBLE as
# one. It does not belong in the performance narrative -- "completions are
# declining across 17 of 20 Gram Panchayats" is a sentence about a form nobody
# filled in -- and it does not belong in a log file either, because the
# department's data-quality report is one of the things this analysis is for.
#
# So it is a section of the report, written from `*_data_quality.json` by this
# function and not by the model. It carries no view title, so the prose gate
# reads it as prose outside the per-view sections -- which is what it is.

def data_quality_annex(all_data_quality: dict) -> str:
    """The annex, or "" when the mining run displaced nothing."""
    if not any(dq.get("displaced_findings") or dq.get("sub_support_measures")
               for dq in all_data_quality.values()):
        return ""

    lines = [
        "\n## Data-Quality Annex\n",
        "\nThis section is generated from the mining run's own record, not "
        "written up from the findings. It lists what the analysis declined to "
        "report as a finding, and why -- so that a column nobody is filling in "
        "is visible as a recording problem rather than absent from the report "
        "or, worse, present in it as a performance result.\n",
    ]
    for view_name, dq in all_data_quality.items():
        displaced = dq.get("displaced_findings") or []
        measures  = dq.get("sub_support_measures") or []
        if not displaced and not measures:
            continue
        title = VIEW_DESCRIPTIONS[view_name]["title"]
        lines.append(f"\n### {title}\n")

        for m in measures:
            lines.append(
                f"\n- **`{m['measure']}` over {m['breakdown']}** carries too "
                f"little non-zero data to support a time pattern: of the "
                f"{m['series_examined']} series the engine would read, "
                f"{m['series_below_guard']} fall below the guard "
                f"({m['guard']}), with between {m['nonzero_points_min']} and "
                f"{m['nonzero_points_max']} non-zero points each. The column is "
                f"non-zero on {m['measure_total_nonzero_rows']} of the view's "
                f"rows. A time pattern over a series that is mostly zeros "
                f"describes the recording, so none is reported as a finding."
            )
        for d in displaced:
            common = d.get("commonness_sets") or [{}]
            highlight = common[0].get("highlight", "")
            lines.append(
                f"\n- **{d['pattern_type']} on `{d['measure']}` over "
                f"{d['breakdown']}** {highlight}, across "
                f"{common[0].get('count', 0)} of {d['hdp_size']} "
                f"{d['extending_dimension']} values, was displaced from the "
                f"findings: {d.get('support_note', '')}."
            )
    lines.append("\n")
    return "".join(lines)


def load_data_quality(base_dir: str, view_names) -> dict:
    """Read the mining run's data-quality files. Missing files are not errors:
    a view mined before this WP simply has none."""
    out = {}
    for view_name in view_names:
        path = os.path.join(base_dir, "metainsights", f"{view_name}_data_quality.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            out[view_name] = payload
    return out


def generate_executive_report(
    all_ranked: dict,
    all_configs: dict,
    output_path: str,
    global_feed: dict | None = None,
    all_data_quality: dict | None = None,
) -> str:
    """Generate the full executive report using Claude."""
    client = OpenAI()

    report_sections = [
        "# Odisha Gram Panchayat Development -- Analytical Findings Report\n\n"
        "*Department of Panchayati Raj & Drinking Water, Government of Odisha*\n\n"
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

    # Section order comes from the one view registry, so a view cannot be mined
    # and then silently left out of the report.
    #
    # A view in the registry with no ranked findings is NOT a quiet omission. It
    # means the view was not mined, or was mined and did not drain, and a
    # truncated queue must never be scored (phase4b's run-list comment). It is
    # skipped, said out loud here, and left to fail the prose gate's own
    # missing-section check -- which is the gate doing its job, not a bug.
    missing = [v for v in VIEW_CONFIGS if v not in all_ranked]
    if missing:
        print("!" * 70)
        for v in missing:
            print(f"!! NO RANKED FINDINGS FOR {v} ({VIEW_DESCRIPTIONS[v]['title']}) -- "
                  f"its section is OMITTED from this report.")
        print("!! The prose gate will flag the missing section(s). That is correct.")
        print("!" * 70)

    view_order = [(v, VIEW_DESCRIPTIONS[v]["title"])
                  for v in VIEW_CONFIGS if v in all_ranked]

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
        # The enriched findings decide whether §5.2's reporting-artifact
        # sentence joins this section's note. See reading_note_block.
        report_sections.append(reading_note_block(view_name, enriched))
        report_sections.append("\n\n---\n")

    # A7's annex closes the report: deterministic, model-free, and present only
    # when the run actually displaced something.
    if all_data_quality:
        annex = data_quality_annex(all_data_quality)
        if annex:
            report_sections.append(annex)
            report_sections.append("\n---\n")

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
    # One registry, read three ways: the views to load, the configs to enrich
    # against, and the section order inside generate_executive_report.
    views = list(VIEW_CONFIGS)
    all_ranked  = {}
    all_configs = dict(VIEW_CONFIGS)

    for view_name in views:
        path = os.path.join(BASE_DIR, "metainsights", f"{view_name}_ranked.json")
        if not os.path.exists(path):
            # Loud, not fatal: see generate_executive_report. A missing ranked
            # file means the view did not drain, and a report of two honest
            # sections beats no report at all -- but nothing about the omission
            # may be quiet.
            print(f"MISSING {path} -- {view_name} has no ranked findings")
            continue
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

    # The PR&DW report lands in reports_prdw/, beside the pack's validation and
    # profile reports, so it cannot overwrite another deployment's.
    md_path = os.path.join(BASE_DIR, "reports_prdw", "executive_metainsight_report.md")
    all_data_quality = load_data_quality(BASE_DIR, views)
    if all_data_quality:
        print(f"Loaded the data-quality record for "
              f"{', '.join(all_data_quality)} (A7)")
    generate_executive_report(all_ranked, all_configs, md_path, global_feed,
                              all_data_quality)

    import md_to_pdf
    md_to_pdf.convert(md_path, md_path.replace(".md", ".pdf"))

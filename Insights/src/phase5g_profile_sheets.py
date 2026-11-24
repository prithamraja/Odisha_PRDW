# =============================================================================
# Phase 5g: Place profile sheets (WP-D14; spec handoffs/PROFILE_SHEET_SPEC.md)
# =============================================================================
# One PROFILE SHEET per Gram Panchayat, block and district, and one for the
# whole: a main row of single figures, where the place stands among its peers,
# a few short lists, and a ready-made sentence with a stable id for every
# figure. Fetched by code, never searched (spec §2 rule 1): a sheet has no
# vector.
#
# THE RULES THIS FILE KEEPS (spec §2, D76):
#   * Built only from the views the insights are built from, so a sheet and a
#     mined insight cannot disagree. The builder REFUSES to write the real store
#     when the view parquets are not the ones the decomposition corpus was built
#     from (`decompose_corpus_stamp.json` -> `view_parquets`).
#   * Every number is worked out here. The reader and the writer compute nothing.
#   * Each level is computed from its own rows. A share is never averaged: a
#     block's share spent is the block's spent over the block's planned.
#   * Set-based. One grouped query per level for each part of a sheet (DuckDB,
#     GROUP BY and window functions). No query and no dataframe filter inside a
#     loop over places; only the writing-out of sentences walks the places.
#   * No mark, no threshold, no note the spec does not hold (R5, R9). No date
#     from the clock in any figure or sentence; `generated_at` in the stamp is
#     the only wall-clock value, and the only one two builds may differ in.
#   * The sample's size lives in data, never in code (D15): nothing below knows
#     how many places there are. The spec §13 reference figures, which do, are
#     a fixed expectation table used only by check 7 (`REFERENCE`).
#
# Inputs (read-only): Insights/views_prdw/view{1,3,4}*.parquet,
#   metainsights/global_feed_source_set.json (the run stamp),
#   metainsights/decompose_corpus_stamp.json (the view hashes to match).
# Outputs (new files; every existing file in metainsights/ is untouched):
#   metainsights/profile_sheets_index.json.gz
#   metainsights/profile_sheets.part<N>.bin
#   metainsights/profile_sheets_stamp.json
#
# Run from the LOCAL MIRROR, repo root:
#   python Insights/src/phase5g_profile_sheets.py            build the store
#   python Insights/src/phase5g_profile_sheets.py --check    the seven checks
#   python Insights/src/phase5g_profile_sheets.py --synthetic \
#          --views-dir <made-up views> --out-dir <outside the repo>   (T7)
# =============================================================================

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import zlib

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SRC_DIR)                    # Insights/
REPO_DIR = os.path.dirname(BASE_DIR)
for _p in (SRC_DIR, REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phase5b_report import format_measure                       # noqa: E402
from phase5d_retrieval_corpus import sha256_of, write_corpus_json  # noqa: E402
from phase5f_decompose import RECONCILE_ABS, RECONCILE_REL      # noqa: E402
from DiscoverChat.glossary import signed_money, signed_above    # noqa: E402
from DiscoverChat.checks import numerals                        # noqa: E402
from DiscoverChat.profile_store import (                        # noqa: E402
    ProfileStore, INDEX_NAME, INDEX_FORMAT, STAMP_NAME, PART_PATTERN,
    SHEET_ID_RE,
)

MI_DIR = os.path.join(BASE_DIR, "metainsights")
VIEWS_DIR = os.path.join(BASE_DIR, "views_prdw")
VIEW_FILES = {
    "view1": "view1_activity_lifecycle.parquet",
    "view3": "view3_gp_performance.parquet",
    "view4": "view4_gp_profile.parquet",
}

# ── Settings ─────────────────────────────────────────────────────────────────
# Fact 9: the whole's name is ONE setting. Statewide it becomes "the state".
WHOLE_NAME = "the whole sample"
MIN_PEERS = 5             # R1: no standing from fewer than 5 peers
EXACT_PEERS_MAX = 50      # R1: exact place up to 50 peers, quarters above
SLUG_MAX = 32             # T4
ID_MAX = 60               # the citation tag's own bound (checks._TAG)
PART_LIMIT = 95_000_000   # T5 / WP-D11b: no file over 95 MB
UNMAPPED_THEME = "Unmapped theme"          # Fact 11
NOT_RECORDED = "(not recorded)"            # phase5f's label for a null member
NOT_REPORTED = "Not reported"              # view4's label for a missing band
OLD_WORK_YEARS = 3        # E5: three or more fiscal years before the latest
TOP_SCHEMES = 5           # D: the five largest schemes, then "all others"
TOP_AUTHORITIES = 3       # D: the three largest authorities, then "all others"

LEVELS = ("gp", "block", "district", "all")
STORE_ORDER = ("all", "district", "block", "gp")
KEY = {"gp": "gp_lgd_code", "block": "block_code",
       "district": "district_code", "all": "'all'"}
LEVEL_WORD = {"gp": "Gram Panchayat", "block": "block", "district": "district"}
LEVEL_PLURAL = {"gp": "Gram Panchayats", "block": "blocks",
                "district": "districts"}
# Peer groups, smallest first (spec §4, R1). "all" is the whole.
PEER_GROUPS = {"gp": ("block", "district", "all"),
               "block": ("district", "all"),
               "district": ("all",),
               "all": ()}
GROUP_KEY = {"block": "block_code", "district": "district_code", "all": "'all'"}
CHILD = {"block": "gp", "district": "block", "all": "district"}

# The two fixed notes (T5). Stored once, in the index; rows refer to them.
NOTES = {
    "no_approval": ("An activity with no approval on file is not known to be "
                    "unapproved; the record may simply be missing."),
    "self_reported": "Reported by the Gram Panchayat itself and not checked.",
}
ROW_NOTE = {"F1": "no_approval", "H3": "self_reported", "H4": "self_reported",
            "H5": "self_reported", "I1": "self_reported",
            "I2": "self_reported", "I3": "self_reported"}

# ── The figures ──────────────────────────────────────────────────────────────
# Main-row sums from view3 (spec §5): figure -> view3 column.
V3_SUMS = {
    "A1": "n_activities", "A2": "n_costless", "A3": "planned_cost",
    "A4": "sanctioned_total", "A5": "expenditure_total",
    "A7": "overspend_vs_plan", "E1": "n_ongoing", "E2": "n_completed",
    "E3": "n_abandoned", "E4": "n_with_evidence", "E4u": "evidence_uploads",
    "F1": "n_admin_approvals", "F2": "n_tech_approvals",
    "G1": "receipt_amount", "G2": "payment_amount",
}
MONEY_MEASURE = {"A3": "planned_cost", "A4": "sanctioned_total",
                 "A5": "expenditure_total", "A7": "overspend_vs_plan",
                 "G1": "receipt_amount", "G2": "payment_amount"}
# Ranked figures and their kind (spec §5 "Standing" column, Fact 7).
RANKED = {"A1": "count", "A3": "money", "A4": "money", "A5": "money",
          "A6": "share", "E1": "count", "E2": "count", "E4": "count",
          "F1": "count", "G1": "money", "G2": "money", "G3": "share"}
WORDS = {"count": ("most", "fewest"), "money": ("highest", "lowest"),
         "share": ("highest", "lowest")}
QUARTERS = ("lowest", "lower-middle", "upper-middle", "highest")
# Check 4: corpus measure -> (sheet row, field). Only figures the sheet holds.
INSIGHT_MEASURES = {
    "n_activities": ("A1", "value"), "n_costless": ("A2", "value"),
    "planned_cost": ("A3", "value"), "sanctioned_total": ("A4", "value"),
    "expenditure_total": ("A5", "value"), "overspend_vs_plan": ("A7", "value"),
    "n_ongoing": ("E1", "value"), "n_completed": ("E2", "value"),
    "n_abandoned": ("E3", "value"), "n_with_evidence": ("E4", "value"),
    "evidence_uploads": ("E4", "uploads"), "n_admin_approvals": ("F1", "value"),
    "n_tech_approvals": ("F2", "value"), "receipt_amount": ("G1", "value"),
    "payment_amount": ("G2", "value"),
}
PLACE_DIMENSION = {"gp_name": "gp", "block_name": "block",
                   "district_name": "district"}


# =============================================================================
# FORMATS (Fact 4). The corpus's own money formatter; counts and shares here.
# =============================================================================

def fmt_money(value: float, measure: str = "planned_cost") -> str:
    return format_measure("view3", measure, value)


def fmt_count(value) -> str:
    return f"{int(round(value)):,}"


def fmt_median_count(value: float) -> str:
    """Whole when whole (712), one decimal when not (602.5)."""
    r = round(float(value), 1)
    return f"{int(r):,}" if r == int(r) else f"{r:,.1f}"


def fmt_share(share: float) -> str:
    return f"{share * 100:.1f}%"


def fmt_ratio(value: float) -> str:
    return f"{value:,.1f}"


FORMAT = {"count": fmt_count, "money": fmt_money, "share": fmt_share,
          "ratio": fmt_ratio, "median_count": fmt_median_count}
MEDIAN_KIND = {"count": "median_count", "money": "money", "share": "share"}

# Every numeric field a sheet stores, and the formatter it is shown through.
# Check 5 regenerates each one through this table; `value` and `median` take
# the kind of the row they sit on.
FIELD_KIND = {
    "share": "share", "of": "count", "whole": "count", "uploads": "count",
    "planned": "money", "spent": "money", "amount": "money",
    "tied": "money", "untied": "money", "tied_share": "share",
    "untied_share": "share", "top_year_count": "count",
    "activities": "count", "no_cost": "count", "abandoned": "count",
    "approvals": "count", "households": "count", "population": "count",
    "toilets": "count", "taps": "count", "ratio": "ratio", "gps": "count",
    "blocks": "count", "districts": "count", "share_of_planned": "share",
    "share_of_spent": "share", "peers": "count", "rank_high": "count",
    "rank_low": "count", "tied_with": "count", "others": "count",
}
ROW_VALUE_KIND = {
    "A1": "count", "A2": "count", "A3": "money", "A4": "money",
    "A5": "money", "A6": "share", "A7": "money", "E1": "count",
    "E2": "count", "E3": "count", "E4": "count", "E5": "count",
    "F1": "count", "F2": "count", "G1": "money", "G2": "money",
    "G3": "share", "H1": "count", "H2": "count",
}


def kind_of(field: str, row_kind: str | None) -> str | None:
    if field == "value":
        return row_kind
    if field == "median":
        return MEDIAN_KIND.get(row_kind)
    return FIELD_KIND.get(field)


def display(field: str, value, row_kind: str | None, measure: str | None = None):
    kind = kind_of(field, row_kind)
    if value is None or kind is None:
        return None
    if kind == "money" and measure:
        return fmt_money(value, measure)
    return FORMAT[kind](value)


# =============================================================================
# WORDS
# =============================================================================

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def agree(n, one: str, many: str) -> str:
    return one if n == 1 else many


def cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def slug(name: str) -> str:
    """Lower case, every run of other characters one hyphen, cut to 32.

    Leading and trailing hyphens are dropped, before and after the cut, so a
    name such as "(not recorded)" gives "not-recorded"."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:SLUG_MAX].strip("-")


def theme_key(name: str) -> str:
    """CT key: the theme's number, `unmapped`, else its slug (T4)."""
    if name == UNMAPPED_THEME:
        return "unmapped"
    m = re.match(r"Theme\s+(\d+)\b", name)
    return m.group(1) if m else slug(name)


def place_label(level: str, name: str, whole: str) -> str:
    """`Kalimela Gram Panchayat`, `Kalimela block`, `the whole sample`."""
    return whole if level == "all" else f"{name} {LEVEL_WORD[level]}"


def sheet_id(level: str, code: str, row: str, key: str | None = None) -> str:
    head = "p-all" if level == "all" else f"p-{level}-{code}"
    return f"{head}-{row}" + (f"-{key}" if key is not None else "")


# ── Standing (spec §4, Fact 7, Appendix A) ───────────────────────────────────

def quarter(rank_low: int, peers: int) -> str:
    p = (rank_low - 1) / peers            # peers with a strictly smaller value
    return QUARTERS[0 if p < 0.25 else 1 if p < 0.5 else 2 if p < 0.75 else 3]


def sentence_group(level: str, standing: dict) -> str | None:
    """The smallest peer group with at least MIN_PEERS members (R1)."""
    for group in PEER_GROUPS[level]:
        st = standing.get(group)
        if st and st["peers"] >= MIN_PEERS:
            return group
    return None


def exact_phrase(st: dict, kind: str) -> str:
    """`the 2nd most`, `the joint highest`, `the 4th lowest` -- the nearer end,
    named from the highest when the two ranks are equal (T2)."""
    high, low = WORDS[kind]
    rank, word = ((st["rank_high"], high) if st["rank_high"] <= st["rank_low"]
                  else (st["rank_low"], low))
    joint = "joint " if st["tied_with"] else ""
    return f"the {joint}{word}" if rank == 1 else f"the {joint}{ordinal(rank)} {word}"


def standing_phrase(level: str, row: dict, kind: str, whole: str) -> str | None:
    """The standing clause of a sentence, or None when no group has 5 peers.

    Up to 50 peers the exact place, above that the quarter. A group that is a
    block or a district is named. When the group used is not the whole and the
    whole has more than 50 peers, the place's quarter in the whole is added
    (spec §4: "a Gram Panchayat sentence gives its place in the block and its
    quarter in the state")."""
    group = row.get("sentence_group")
    if group is None:
        return None
    st = row["standing"][group]
    n = st["peers"]
    plural = LEVEL_PLURAL[level]
    where = whole if group == "all" else st["group_name"]
    if n <= EXACT_PEERS_MAX:
        of = (f"of {n:,} {plural}" if group == "all"
              else f"of the {n:,} {plural} in {where}")
        phrase = f"{exact_phrase(st, kind)} {of}"
    else:
        phrase = (f"in the {quarter(st['rank_low'], n)} quarter of the "
                  f"{n:,} {plural} in {where}")
    if names_two_groups(row):
        top = row["standing"]["all"]
        phrase += (f" and in the {quarter(top['rank_low'], top['peers'])} "
                   f"quarter of the {top['peers']:,} in {whole}")
    return phrase


def names_two_groups(row: dict) -> bool:
    """The standing clause names a block or district AND the whole: the group
    used is not the whole, and the whole has more than 50 peers."""
    group = row.get("sentence_group")
    top = row.get("standing", {}).get("all")
    return bool(group and group != "all" and top
                and top["peers"] > EXACT_PEERS_MAX)


def middle_sentence(row: dict, median: str | None, always_n: bool = False) -> str:
    """` The middle value is …`, or ` … for these {n} is …` when the sentence
    names two groups (R11) -- or always, for A1. {n} is the first group's size."""
    if median is None:
        return ""
    if always_n or names_two_groups(row):
        n = row["standing"][row["sentence_group"]]["peers"]
        return f" The middle value for these {n:,} is {median}."
    return f" The middle value is {median}."


def middle_value(row: dict, kind: str) -> str | None:
    group = row.get("sentence_group")
    if group is None:
        return None
    return display("median", row["standing"][group]["median"], kind)


# =============================================================================
# SENTENCES (Appendix A). Every sentence is written from stored values only.
# =============================================================================

def _ranked_tail(level, row, fig, whole) -> tuple:
    kind = RANKED[fig]
    phrase = standing_phrase(level, row, kind, whole)
    median = middle_value(row, kind)
    return phrase, median


def main_sentences(sheet: dict, whole: str) -> dict:
    """Row -> sentence text for the main row; a row with no sentence is absent."""
    level = sheet["level"]
    rows = sheet["rows"]
    place = cap(place_label(level, sheet["name"], whole))
    out = {}

    def ranked(fig, body):
        phrase, median = _ranked_tail(level, rows[fig], fig, whole)
        text = body + (f", {phrase}." if phrase else ".")
        return text + middle_sentence(rows[fig], median)

    a1 = rows["A1"]
    if a1["value"] == 0:
        out["A1"] = f"{place} has no planned activities in the data."
    else:
        phrase, median = _ranked_tail(level, a1, "A1", whole)
        text = (f"{place} has {fmt_count(a1['value'])} planned "
                f"{agree(a1['value'], 'activity', 'activities')}")
        text += f", {phrase}." if phrase else "."
        out["A1"] = text + middle_sentence(a1, median, always_n=True)

    a2 = rows["A2"]
    if a1["value"] != 0:
        if a2["value"] == 0:
            out["A2"] = "All of them have a cost attached."
        else:
            out["A2"] = (f"{fmt_count(a2['value'])} of them "
                         f"({fmt_share(a2['share'])}) "
                         f"{agree(a2['value'], 'has', 'have')} no cost attached.")

    a3 = rows["A3"]
    out["A3"] = ("It has no planned cost on record." if a3["value"] == 0 else
                 ranked("A3", f"Its planned cost is {a3['display']}"))
    a4 = rows["A4"]
    out["A4"] = ("Nothing has been sanctioned on record." if a4["value"] == 0 else
                 ranked("A4", f"{a4['display']} has been sanctioned for the "
                              f"activities with an approval on file"))
    a5 = rows["A5"]
    out["A5"] = ("The data shows no spending on its planned activities."
                 if a5["value"] == 0 else
                 ranked("A5", f"It spent {a5['display']} on planned activities"))
    a6 = rows["A6"]
    if a3["value"] != 0 and a5["value"] != 0:
        out["A6"] = ranked("A6", f"Spending is {a6['display']} of the planned cost")
    a7 = rows["A7"]
    if a7["value"] < 0:
        out["A7"] = f"Spending is {signed_money(a7['display'], 'overspend_vs_plan')}."
    elif a7["value"] > 0:
        out["A7"] = (f"Spending is {a7['display']} "
                     f"{signed_above('overspend_vs_plan')}.")

    e1 = rows["E1"]
    out["E1"] = ("No works are marked ongoing." if e1["value"] == 0 else
                 ranked("E1", f"{fmt_count(e1['value'])} "
                              f"{agree(e1['value'], 'work is', 'works are')} "
                              f"marked ongoing"))
    e2 = rows["E2"]
    if e2["value"] == 0:
        out["E2"] = "No works are marked completed."
    else:
        text = (f"{fmt_count(e2['value'])} "
                f"{agree(e2['value'], 'work is', 'works are')} marked completed")
        out["E2"] = (text + "." if level == "all" else
                     f"{text}, out of {fmt_count(e2['whole'])} in {whole}.")
    e3 = rows["E3"]
    if e3["value"] == 0:
        out["E3"] = "No works are marked abandoned."
    else:
        one = e3["value"] == 1
        text = (f"{fmt_count(e3['value'])} "
                f"{agree(e3['value'], 'work is', 'works are')} marked abandoned, ")
        text += (f"with {fmt_money(e3['planned'])} planned on "
                 f"{'it' if one else 'them'}." if e3["planned"] != 0 else
                 f"with no planned cost on {'it' if one else 'them'}.")
        if e3.get("top_year"):
            k = e3["top_year_count"]
            text += (f" It was planned in {e3['top_year']}." if one else
                     f" {fmt_count(k)} of them {agree(k, 'was', 'were')} "
                     f"planned in {e3['top_year']}.")
        out["E3"] = text
    e4 = rows["E4"]
    out["E4"] = ("No activities have photo evidence." if e4["value"] == 0 else
                 ranked("E4", f"{fmt_count(e4['value'])} "
                              f"{agree(e4['value'], 'activity has', 'activities have')}"
                              f" photo evidence ({fmt_count(e4['uploads'])} "
                              f"{agree(e4['uploads'], 'upload', 'uploads')})"))
    e5 = rows["E5"]
    if e5["value"] and e5.get("cutoff_year"):
        one = e5["value"] == 1
        text = (f"{fmt_count(e5['value'])} "
                f"{agree(e5['value'], 'work', 'works')} planned in "
                f"{e5['cutoff_year']} or earlier "
                f"{agree(e5['value'], 'is', 'are')} still marked ongoing.")
        if e5["planned"] != 0 and e5["spent"] == 0:
            text += (f" Nothing has been spent of {'its' if one else 'their'} "
                     f"{fmt_money(e5['planned'])} planned cost.")
        elif e5["planned"] != 0:
            text += (f" {fmt_money(e5['spent'])} of {'its' if one else 'their'} "
                     f"{fmt_money(e5['planned'])} planned cost has been spent "
                     f"({fmt_share(e5['share'])}).")
        out["E5"] = text

    f1 = rows["F1"]
    if a1["value"] != 0:
        noun = agree(a1["value"], "activity", "activities")
        if f1["value"] == 0:
            out["F1"] = (f"None of the {fmt_count(a1['value'])} {noun} has an "
                         f"administrative approval on file.")
        else:
            out["F1"] = ranked("F1", (
                f"{fmt_count(f1['value'])} of the {fmt_count(a1['value'])} "
                f"{noun} ({fmt_share(f1['share'])}) "
                f"{agree(f1['value'], 'has', 'have')} an administrative "
                f"approval on file"))
    f2 = rows["F2"]
    out["F2"] = ("No activities have a technical approval on file."
                 if f2["value"] == 0 else
                 f"{fmt_count(f2['value'])} "
                 f"{agree(f2['value'], 'activity has', 'activities have')} "
                 f"a technical approval on file.")

    g1, g2, g3 = rows["G1"], rows["G2"], rows["G3"]
    out["G1"] = ("Its cashbook shows no receipts and no payments."
                 if g1["value"] == 0 and g2["value"] == 0 else
                 f"Its cashbook shows {g1['display']} received and "
                 f"{g2['display']} paid out.")
    if g2["value"] != 0:
        out["G3"] = ("None of the payments is linked to a planned activity."
                     if g3["value"] == 0 else
                     ranked("G3", f"{g3['display']} of the payments are linked "
                                  f"to a planned activity"))

    h1 = rows["H1"]
    if h1["value"]:
        out["H1"] = (f"{fmt_count(h1['value'])} "
                     f"{agree(h1['value'], 'activity has', 'activities have')} "
                     f"an approval cost recorded with no approval record.")
    h2 = rows["H2"]
    if h2["value"]:
        one = h2["value"] == 1
        head = (f"{fmt_count(h2['value'])} "
                f"{agree(h2['value'], 'activity has', 'activities have')} "
                f"no LSDG theme mapped; ")
        if h2["planned"] == 0:
            out["H2"] = head + ("it has no cost attached." if one else
                                "none of them has a cost attached.")
        else:
            out["H2"] = (head + f"{'its' if one else 'their'} planned cost is "
                                f"{fmt_money(h2['planned'])}.")
    if level == "gp":
        h3, h4, h5 = rows["H3"], rows["H4"], rows["H5"]
        if h3["flag"]:
            out["H3"] = (f"Its profile reports {fmt_count(h3['toilets'])} "
                         f"household toilets for {fmt_count(h3['households'])} "
                         f"households.")
        if h4["flag"]:
            out["H4"] = (f"Its profile reports {fmt_count(h4['taps'])} tap "
                         f"connections for {fmt_count(h4['households'])} "
                         f"households.")
        if h5["flag"]:
            out["H5"] = (f"Its profile reports {fmt_count(h5['population'])} "
                         f"people in {fmt_count(h5['households'])} households, "
                         f"which is {fmt_ratio(h5['ratio'])} people per "
                         f"household.")
        i1, i2, i3 = rows["I1"], rows["I2"], rows["I3"]
        if i1["population"]:
            band = ("" if i1["gp_size"] in (None, NOT_REPORTED)
                    else f" (size band: {i1['gp_size']})")
            out["I1"] = (f"Its profile reports a population of "
                         f"{fmt_count(i1['population'])}{band}.")
        if i2["households"]:
            out["I2"] = f"Its profile reports {fmt_count(i2['households'])} households."
        parts = []
        if i3["social_composition"] not in (None, NOT_REPORTED):
            parts.append(i3["social_composition"])
        if i3["remoteness"] in ("Near", "Far"):
            parts.append("near a bus stop" if i3["remoteness"] == "Near"
                         else "far from a bus stop")
        if parts:
            out["I3"] = f"Its profile classes it as {' and as '.join(parts)}."
    else:
        i4 = rows["I4"]
        gps = (f"{fmt_count(i4['gps'])} "
               f"{agree(i4['gps'], 'Gram Panchayat', 'Gram Panchayats')}")
        if level == "block":
            out["I4"] = f"{place} has {gps} in the data."
        elif level == "district":
            out["I4"] = (f"{place} has {fmt_count(i4['blocks'])} "
                         f"{agree(i4['blocks'], 'block', 'blocks')} and {gps} "
                         f"in the data.")
        else:
            out["I4"] = (f"{place} has {fmt_count(i4['districts'])} "
                         f"{agree(i4['districts'], 'district', 'districts')}, "
                         f"{fmt_count(i4['blocks'])} "
                         f"{agree(i4['blocks'], 'block', 'blocks')} and {gps}.")
    return out


def _money_line(planned, spent, share) -> str:
    """The shared tail of a B and a J line, with their two "nothing" forms."""
    if planned == 0 and spent == 0:
        return "nothing planned, nothing spent."
    if planned == 0:
        return f"nothing planned, {fmt_money(spent)} spent."
    if spent == 0:
        return f"{fmt_money(planned)} planned, nothing spent."
    return (f"{fmt_money(planned)} planned, {fmt_money(spent)} spent, "
            f"{fmt_share(share)} of the plan.")


def b_sentence(line: dict) -> str:
    n = line["activities"]
    if n == 0 and line["planned"] == 0 and line["spent"] == 0:
        return f"In {line['year']}: no planned activities."
    head = f"In {line['year']}: {fmt_count(n)} {agree(n, 'activity', 'activities')}"
    if line["no_cost"]:
        head += f" ({fmt_count(line['no_cost'])} with no cost)"
    return f"{head}, {_money_line(line['planned'], line['spent'], line['share'])}"


def c_sentence(line: dict) -> str:
    n, planned, spent = line["activities"], line["planned"], line["spent"]
    acts = f"{fmt_count(n)} {agree(n, 'activity', 'activities')}"
    name = line["name"]
    if planned != 0 and spent != 0:
        return f"{name}: {acts}, {fmt_money(planned)} planned, {fmt_money(spent)} spent."
    if planned != 0:
        return f"{name}: {acts} and {fmt_money(planned)} planned, with nothing spent."
    if spent != 0:
        return f"{name}: {acts} with no planned cost, {fmt_money(spent)} spent."
    return f"{name}: {acts}, with no planned cost and nothing spent."


def ds_sentence(line: dict) -> str:
    n = line["approvals"]
    name = "All other schemes" if line.get("others") else line["name"]
    return (f"{name}: {fmt_count(n)} {agree(n, 'approval', 'approvals')}, "
            f"{fmt_money(line['amount'])} sanctioned.")


def d_plan_sentence(plan: dict) -> str:
    return (f"Of the planned cost, {fmt_money(plan['tied'])} is tied grant "
            f"({fmt_share(plan['tied_share'])}) and {fmt_money(plan['untied'])} "
            f"is untied grant ({fmt_share(plan['untied_share'])}).")


def d_authority_sentence(auth: dict) -> str:
    parts = [f"{line['name']} {fmt_count(line['approvals'])}"
             for line in auth["lines"]]
    if auth.get("others"):
        parts.append(f"all others {fmt_count(auth['others'])}")
    return "Approvals on file, by who approved: " + ", ".join(parts) + "."


def j_sentence(line: dict, level: str) -> str:
    member = place_label(CHILD[level], line["name"], "")
    n = line["activities"]
    if n == 0 and line["planned"] == 0 and line["spent"] == 0:
        return f"{member}: no planned activities."
    return (f"{member}: {fmt_count(n)} {agree(n, 'activity', 'activities')}, "
            f"{_money_line(line['planned'], line['spent'], line['share'])}")


def write_sentences(sheet: dict, whole: str) -> list:
    """Every sentence of a sheet, in the hand-over order of T5."""
    level, code = sheet["level"], sheet["code"]
    main = main_sentences(sheet, whole)
    lists = sheet["lists"]
    out = []

    def add(row, text, key=None):
        out.append({"id": sheet_id(level, code, row, key), "row": row,
                    "key": key, "sentence": text, "note": ROW_NOTE.get(row)})

    for row in ("A1", "A2", "A3", "A4", "A5", "A6", "A7"):
        if row in main:
            add(row, main[row])
    for key, line in lists["B"].items():
        add("B", b_sentence(line), key)
    for key, line in lists["C"].items():
        add("C", c_sentence(line), key)
    for key, line in lists["CT"].items():
        add("CT", c_sentence(line), key)
    if lists["D"]["plan"] is not None:
        add("D", d_plan_sentence(lists["D"]["plan"]), "plan")
    for key, line in lists["DS"].items():
        add("DS", ds_sentence(line), key)
    if lists["D"]["authority"] is not None:
        add("D", d_authority_sentence(lists["D"]["authority"]), "authority")
    for row in ("E1", "E2", "E3", "E4", "E5", "F1", "F2", "G1", "G3",
                "H1", "H2", "H3", "H4", "H5", "I1", "I2", "I3", "I4"):
        if row in main:
            add(row, main[row])
    for key, line in lists.get("J", {}).items():
        add("J", j_sentence(line, level), key)
    return out


# =============================================================================
# BUILD (set-based: DuckDB GROUP BY and window functions, one query per level
# for each part of a sheet)
# =============================================================================

class BuildStop(SystemExit):
    pass


def _stop(msg: str):
    raise BuildStop(f"STOP: {msg}")


def view_paths(views_dir: str) -> dict:
    return {v: os.path.join(views_dir, f) for v, f in VIEW_FILES.items()}


def parquet_provenance(paths: dict) -> dict:
    """phase5f's logic, over the views this builder reads."""
    return {os.path.basename(p): {"sha256": sha256_of(p),
                                  "bytes": os.path.getsize(p)}
            for p in paths.values()}


REQUIRED_COLUMNS = {
    "view1": ["gp_lgd_code", "block_code", "district_code", "fiscal_year",
              "theme", "focus_area_name", "sanctioned_scheme_name",
              "sanction_authority", "total_cost", "total_expenditure",
              "fund_tied_total", "fund_untied_total",
              "fund_sanctioned_total", "is_ongoing", "is_abandoned",
              "is_admin_approved", "has_approval_cost_only"],
    "view3": ["gp_lgd_code", "block_code", "district_code", "fiscal_year"]
             + sorted(set(V3_SUMS.values())),
    "view4": ["gp_lgd_code", "gp_name", "block_code", "block_name",
              "district_code", "district_name", "population_total",
              "households", "household_toilets", "households_tap_water",
              "gp_size", "social_composition", "remoteness"],
}


def _connect(paths: dict):
    import duckdb
    con = duckdb.connect()
    # One thread: float sums are then taken in one fixed order, so two builds
    # from the same views give the same bits (gate item 5).
    con.execute("SET threads TO 1")
    for view, path in paths.items():
        con.execute(f"CREATE VIEW {view} AS SELECT * FROM "
                    f"read_parquet('{path.replace(os.sep, '/')}')")
        cols = {r[0] for r in con.execute(f"DESCRIBE {view}").fetchall()}
        missing = [c for c in REQUIRED_COLUMNS[view] if c not in cols]
        if missing:
            _stop(f"{view} has no column {missing} that the spec names")
    return con


def _rows(con, sql: str) -> list:
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _places(con, whole: str, log: list) -> dict:
    """The place lists, from the Gram Panchayat master (view4), with names
    trimmed and the one-parent rule checked in every view read (Fact 1)."""
    dup = con.execute("SELECT gp_lgd_code FROM view4 GROUP BY 1 "
                      "HAVING COUNT(*) > 1").fetchall()
    if dup:
        _stop(f"view4 holds a Gram Panchayat code more than once: {dup[:5]}")
    for view in ("view1", "view3", "view4"):
        for child, parent in (("gp_lgd_code", "block_code"),
                              ("block_code", "district_code")):
            bad = con.execute(
                f"SELECT {child} FROM {view} GROUP BY 1 "
                f"HAVING COUNT(DISTINCT {parent}) > 1").fetchall()
            if bad:
                _stop(f"in {view}, {child} {bad[:3]} maps to more than one "
                      f"{parent}")
        stray = con.execute(
            f"SELECT DISTINCT gp_lgd_code FROM {view} WHERE gp_lgd_code NOT IN "
            f"(SELECT gp_lgd_code FROM view4)").fetchall()
        if stray:
            _stop(f"{view} holds Gram Panchayats not in the master: {stray[:5]}")
        clash = con.execute(
            f"SELECT v.gp_lgd_code FROM (SELECT DISTINCT gp_lgd_code, block_code "
            f"FROM {view}) v JOIN view4 m USING (gp_lgd_code) "
            f"WHERE v.block_code <> m.block_code").fetchall()
        if clash:
            _stop(f"{view} puts Gram Panchayats {clash[:3]} in another block "
                  f"than the master does")

    for col in ("gp_name", "block_name", "district_name"):
        for (raw,) in con.execute(f"SELECT DISTINCT {col} FROM view4 "
                                  f"WHERE {col} <> trim({col})").fetchall():
            log.append(f"name trimmed ({col}): {raw!r}")
    con.execute("""
        CREATE TABLE p_gp AS SELECT CAST(gp_lgd_code AS VARCHAR) AS code,
               trim(gp_name) AS name, CAST(block_code AS VARCHAR) AS block_code,
               trim(block_name) AS block_name,
               CAST(district_code AS VARCHAR) AS district_code,
               trim(district_name) AS district_name, 'all' AS all_code
        FROM view4""")
    con.execute("""
        CREATE TABLE p_block AS SELECT DISTINCT block_code AS code,
               block_name AS name, district_code, district_name,
               'all' AS all_code FROM p_gp""")
    con.execute("""
        CREATE TABLE p_district AS SELECT DISTINCT district_code AS code,
               district_name AS name, 'all' AS all_code FROM p_gp""")
    con.execute("CREATE TABLE p_all AS SELECT 'all' AS code, ? AS name, "
                "'all' AS all_code", [whole])
    for level in ("block", "district"):
        dup = con.execute(f"SELECT code FROM p_{level} GROUP BY 1 "
                          f"HAVING COUNT(*) > 1").fetchall()
        if dup:
            _stop(f"{level} codes {dup[:3]} carry two names or two parents")
    places = {}
    for level in LEVELS:
        for r in _rows(con, f"SELECT * FROM p_{level} ORDER BY code"):
            if not re.fullmatch(r"[A-Za-z0-9_.]+", r["code"]):
                _stop(f"{level} code {r['code']!r} cannot sit inside an id")
            places.setdefault(level, []).append(r)
    return places


def _fiscal_years(con) -> tuple:
    years = sorted(r[0] for r in con.execute(
        "SELECT DISTINCT fiscal_year FROM view3 WHERE fiscal_year IS NOT NULL"
    ).fetchall())
    latest = years[-1]
    start = int(latest[:4])
    old = [y for y in years if int(y[:4]) <= start - OLD_WORK_YEARS]
    return years, latest, (old[-1] if old else None), old


def _sql_list(values) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values) or "NULL"


def _build_main(con, years_old: list) -> None:
    """Table m_<level>: one row per place, every main-row figure (T1)."""
    old = _sql_list(years_old)
    for level in LEVELS:
        k = KEY[level]
        sums = ",\n".join(f"SUM({col}) AS {fig}" for fig, col in V3_SUMS.items())
        con.execute(f"""
        CREATE TABLE m_{level} AS
        WITH s3 AS (SELECT CAST({k} AS VARCHAR) AS code, {sums}
                    FROM view3 GROUP BY 1),
             s1 AS (SELECT CAST({k} AS VARCHAR) AS code,
                    -- R10 (D77): the planned cost of the works marked
                    -- abandoned. Not fund_abandoned_total, which 19 rows that
                    -- are not marked abandoned also carry (spec §12 item 8).
                    SUM(CASE WHEN is_abandoned = 1
                             THEN COALESCE(total_cost, 0) ELSE 0 END) AS E3_planned,
                    SUM(CASE WHEN is_ongoing = 1 AND fiscal_year IN ({old})
                             THEN 1 ELSE 0 END) AS E5,
                    SUM(CASE WHEN is_ongoing = 1 AND fiscal_year IN ({old})
                             THEN COALESCE(total_cost, 0) ELSE 0 END) AS E5_planned,
                    SUM(CASE WHEN is_ongoing = 1 AND fiscal_year IN ({old})
                             THEN COALESCE(total_expenditure, 0) ELSE 0 END) AS E5_spent,
                    SUM(has_approval_cost_only) AS H1,
                    SUM(CASE WHEN trim(theme) = '{UNMAPPED_THEME}'
                             THEN 1 ELSE 0 END) AS H2,
                    SUM(CASE WHEN trim(theme) = '{UNMAPPED_THEME}'
                             THEN COALESCE(total_cost, 0) ELSE 0 END) AS H2_planned,
                    SUM(COALESCE(fund_tied_total, 0)) AS D_tied,
                    SUM(COALESCE(fund_untied_total, 0)) AS D_untied
                    FROM view1 GROUP BY 1),
             t AS (SELECT p.code,
                    {", ".join(f"COALESCE(s3.{f}, 0) AS {f}" for f in V3_SUMS)},
                    COALESCE(s1.E3_planned, 0) AS E3_planned,
                    COALESCE(s1.E5, 0) AS E5,
                    COALESCE(s1.E5_planned, 0) AS E5_planned,
                    COALESCE(s1.E5_spent, 0) AS E5_spent,
                    COALESCE(s1.H1, 0) AS H1, COALESCE(s1.H2, 0) AS H2,
                    COALESCE(s1.H2_planned, 0) AS H2_planned,
                    COALESCE(s1.D_tied, 0) AS D_tied,
                    COALESCE(s1.D_untied, 0) AS D_untied
                   FROM p_{level} p LEFT JOIN s3 USING (code)
                   LEFT JOIN s1 USING (code))
        SELECT t.*,
          CASE WHEN A1 <> 0 THEN A2 / A1 END AS A2_share,
          CASE WHEN A3 <> 0 THEN A5 / A3 END AS A6,
          CASE WHEN A1 <> 0 THEN F1 / A1 END AS F1_share,
          CASE WHEN G2 <> 0 THEN A5 / G2 END AS G3,
          CASE WHEN E5_planned <> 0 THEN E5_spent / E5_planned END AS E5_share,
          CASE WHEN A3 <> 0 THEN D_tied / A3 END AS D_tied_share,
          CASE WHEN A3 <> 0 THEN D_untied / A3 END AS D_untied_share
        FROM t ORDER BY code""")


def _build_standing(con) -> dict:
    """standing[(level, code, fig)][group] -- window functions over each peer
    group (T2). Blank values are unpivoted away, so they are out of the
    ranking and out of the peer count (Fact 6)."""
    out = {}
    figs = ", ".join(RANKED)
    for level in LEVELS:
        for group in PEER_GROUPS[level]:
            g = GROUP_KEY[group]
            rows = _rows(con, f"""
            WITH u AS (
              UNPIVOT (SELECT m.code, CAST({g} AS VARCHAR) AS g, {figs}
                       FROM m_{level} m JOIN p_{level} USING (code))
              ON {figs} INTO NAME fig VALUE v)
            SELECT code, g, fig,
              COUNT(*) OVER (PARTITION BY fig, g) AS peers,
              RANK() OVER (PARTITION BY fig, g ORDER BY v DESC) AS rank_high,
              RANK() OVER (PARTITION BY fig, g ORDER BY v ASC) AS rank_low,
              COUNT(*) OVER (PARTITION BY fig, g, v) - 1 AS tied_with,
              quantile_cont(v, 0.5) OVER (PARTITION BY fig, g) AS median
            FROM u ORDER BY fig, g, code""")
            for r in rows:
                out.setdefault((level, r["code"], r["fig"]), {})[group] = {
                    "group_code": r["g"], "peers": int(r["peers"]),
                    "rank_high": int(r["rank_high"]),
                    "rank_low": int(r["rank_low"]),
                    "tied_with": int(r["tied_with"]),
                    "median": float(r["median"]),
                }
    return out


def _grouped(rows: list, key: str = "code") -> dict:
    out = {}
    for r in rows:
        out.setdefault(r[key], []).append(r)
    return out


def _build_lists(con, years: list) -> dict:
    """B, C, CT, DS, D-authority and E3's top year, per level (T3)."""
    lists = {}
    yrs = " UNION ALL ".join(f"SELECT '{y}' AS year" for y in years)
    for level in LEVELS:
        k = KEY[level]
        lists[("B", level)] = _grouped(_rows(con, f"""
            WITH s AS (SELECT CAST({k} AS VARCHAR) AS code, fiscal_year AS year,
                         SUM(n_activities) AS activities,
                         SUM(n_costless) AS no_cost,
                         SUM(planned_cost) AS planned,
                         SUM(expenditure_total) AS spent,
                         SUM(n_abandoned) AS abandoned
                       FROM view3 GROUP BY 1, 2)
            SELECT p.code, y.year,
                   COALESCE(s.activities, 0) AS activities,
                   COALESCE(s.no_cost, 0) AS no_cost,
                   COALESCE(s.planned, 0) AS planned,
                   COALESCE(s.spent, 0) AS spent,
                   COALESCE(s.abandoned, 0) AS abandoned
            FROM p_{level} p CROSS JOIN ({yrs}) y
            LEFT JOIN s ON s.code = p.code AND s.year = y.year
            ORDER BY p.code, y.year"""))
        for tag, col in (("C", "focus_area_name"), ("CT", "theme")):
            lists[(tag, level)] = _grouped(_rows(con, f"""
                SELECT CAST({k} AS VARCHAR) AS code,
                       COALESCE(trim({col}), '{NOT_RECORDED}') AS name,
                       COUNT(*) AS activities,
                       SUM(COALESCE(total_cost, 0)) AS planned,
                       SUM(COALESCE(total_expenditure, 0)) AS spent
                FROM view1 GROUP BY 1, 2
                ORDER BY code, planned DESC, name"""))
        lists[("DS", level)] = _grouped(_rows(con, f"""
            WITH s AS (SELECT CAST({k} AS VARCHAR) AS code,
                         COALESCE(trim(sanctioned_scheme_name),
                                  '{NOT_RECORDED}') AS name,
                         COUNT(*) AS approvals,
                         SUM(COALESCE(fund_sanctioned_total, 0)) AS amount
                       FROM view1 WHERE is_admin_approved = 1 GROUP BY 1, 2)
            SELECT *, ROW_NUMBER() OVER (PARTITION BY code
                        ORDER BY amount DESC, name) AS rn
            FROM s ORDER BY code, rn"""))
        lists[("DA", level)] = _grouped(_rows(con, f"""
            WITH s AS (SELECT CAST({k} AS VARCHAR) AS code,
                         COALESCE(trim(sanction_authority),
                                  '{NOT_RECORDED}') AS name,
                         COUNT(*) AS approvals
                       FROM view1 WHERE is_admin_approved = 1 GROUP BY 1, 2)
            SELECT *, ROW_NUMBER() OVER (PARTITION BY code
                        ORDER BY approvals DESC, name) AS rn
            FROM s ORDER BY code, rn"""))
        # E3's plan year with the most abandoned works; ties -> earliest (T1).
        lists[("E3", level)] = {r["code"]: r for r in _rows(con, f"""
            WITH s AS (SELECT CAST({k} AS VARCHAR) AS code, fiscal_year AS year,
                         COUNT(*) AS n
                       FROM view1 WHERE is_abandoned = 1 GROUP BY 1, 2)
            SELECT code, year, n FROM (
              SELECT *, ROW_NUMBER() OVER (PARTITION BY code
                          ORDER BY n DESC, year ASC) AS rn FROM s)
            WHERE rn = 1""")}
        # I4: places inside it.
        lists[("I4", level)] = {r["code"]: r for r in _rows(con, f"""
            SELECT CAST({k} AS VARCHAR) AS code,
                   COUNT(DISTINCT gp_lgd_code) AS gps,
                   COUNT(DISTINCT block_code) AS blocks,
                   COUNT(DISTINCT district_code) AS districts
            FROM view4 GROUP BY 1""")}
    return lists


def _f(v):
    """A stored float, or None for a blank (never NaN in the store)."""
    if v is None:
        return None
    v = float(v)
    return None if v != v else v


def _i(v) -> int:
    v = float(v or 0)
    if v != int(v):
        _stop(f"a count is not whole: {v}")
    return int(v)


def _assemble(level, place, m, standing, lists, whole_e2, cutoff, profile,
              whole) -> dict:
    code = place["code"]
    sheet = {"level": level, "code": code, "name": place["name"],
             "label": place_label(level, place["name"], whole), "parents": {}}
    if level == "gp":
        sheet["parents"] = {
            "block": {"code": place["block_code"], "name": place["block_name"]},
            "district": {"code": place["district_code"],
                         "name": place["district_name"]}}
    elif level == "block":
        sheet["parents"] = {"district": {"code": place["district_code"],
                                         "name": place["district_name"]}}

    def row(fig, **extra):
        r = dict(extra)
        kind = ROW_VALUE_KIND.get(fig)
        if fig in RANKED:
            groups = standing.get((level, code, fig), {})
            st = {}
            for group in PEER_GROUPS[level]:
                if group in groups:
                    s = dict(groups[group])
                    s["group_name"] = (whole if group == "all" else
                                       place_label(group, place[f"{group}_name"],
                                                   whole))
                    s["quarter"] = quarter(s["rank_low"], s["peers"])
                    st[group] = s
            r["standing"] = st
            r["sentence_group"] = sentence_group(level, st)
        if "value" in r and kind is not None:
            r["display"] = display("value", r["value"], kind,
                                   MONEY_MEASURE.get(fig))
        return r

    rows = {
        "A1": row("A1", value=_i(m["A1"])),
        "A2": row("A2", value=_i(m["A2"]), share=_f(m["A2_share"])),
        "A3": row("A3", value=_f(m["A3"])),
        "A4": row("A4", value=_f(m["A4"])),
        "A5": row("A5", value=_f(m["A5"])),
        "A6": row("A6", value=_f(m["A6"])),
        "A7": row("A7", value=_f(m["A7"])),
        "E1": row("E1", value=_i(m["E1"])),
        "E2": row("E2", value=_i(m["E2"]), whole=whole_e2),
        "E3": row("E3", value=_i(m["E3"]), planned=_f(m["E3_planned"])),
        "E4": row("E4", value=_i(m["E4"]), uploads=_i(m["E4u"])),
        "E5": row("E5", value=_i(m["E5"]), cutoff_year=cutoff,
                  planned=_f(m["E5_planned"]), spent=_f(m["E5_spent"]),
                  share=_f(m["E5_share"])),
        "F1": row("F1", value=_i(m["F1"]), of=_i(m["A1"]),
                  share=_f(m["F1_share"])),
        "F2": row("F2", value=_i(m["F2"])),
        "G1": row("G1", value=_f(m["G1"])),
        "G2": row("G2", value=_f(m["G2"])),
        "G3": row("G3", value=_f(m["G3"])),
        "H1": row("H1", value=_i(m["H1"])),
        "H2": row("H2", value=_i(m["H2"]), planned=_f(m["H2_planned"])),
    }
    top = lists[("E3", level)].get(code)
    if top:
        rows["E3"]["top_year"] = top["year"]
        rows["E3"]["top_year_count"] = _i(top["n"])
    if level == "gp":
        p = profile[code]
        hh, pop = _f(p["households"]), _f(p["population_total"])
        toilets, taps = _f(p["household_toilets"]), _f(p["households_tap_water"])
        ratio = pop / hh if hh else None
        # view4 fills an unreported count with 0, so 0 households is "not
        # reported" and the H3/H4 comparison has nothing to compare against.
        rows["H3"] = {"toilets": _i(toilets), "households": _i(hh),
                      "flag": bool(hh and toilets > hh)}
        rows["H4"] = {"taps": _i(taps), "households": _i(hh),
                      "flag": bool(hh and taps > hh)}
        rows["H5"] = {"population": _i(pop), "households": _i(hh),
                      "ratio": ratio, "flag": bool(ratio is not None and ratio > 20)}
        rows["I1"] = {"population": _i(pop), "gp_size": p["gp_size"]}
        rows["I2"] = {"households": _i(hh)}
        rows["I3"] = {"social_composition": p["social_composition"],
                      "remoteness": p["remoteness"]}
    else:
        i4 = lists[("I4", level)].get(code, {})
        rows["I4"] = {"gps": _i(i4.get("gps")), "blocks": _i(i4.get("blocks")),
                      "districts": _i(i4.get("districts"))}
        if level == "block":
            del rows["I4"]["blocks"], rows["I4"]["districts"]
        elif level == "district":
            del rows["I4"]["districts"]
    sheet["rows"] = rows

    a3, a5 = rows["A3"]["value"], rows["A5"]["value"]

    def line_c(r):
        planned, spent = _f(r["planned"]), _f(r["spent"])
        return {"name": r["name"], "activities": _i(r["activities"]),
                "planned": planned, "spent": spent,
                "share_of_planned": planned / a3 if a3 else None,
                "share_of_spent": spent / a5 if a5 else None,
                "share": spent / planned if planned else None}

    b = {}
    for r in lists[("B", level)].get(code, []):
        planned, spent = _f(r["planned"]), _f(r["spent"])
        b[r["year"]] = {"year": r["year"], "activities": _i(r["activities"]),
                        "no_cost": _i(r["no_cost"]), "planned": planned,
                        "spent": spent,
                        "share": spent / planned if planned else None,
                        "abandoned": _i(r["abandoned"])}
    c, ct = {}, {}
    for tag, target, keyf in (("C", c, slug), ("CT", ct, theme_key)):
        for r in lists[(tag, level)].get(code, []):
            key = keyf(r["name"])
            if key in target or not key:
                _stop(f"two names at {level} {code} give the {tag} key "
                      f"{key!r}: {target.get(key, {}).get('name')!r} and "
                      f"{r['name']!r}")
            target[key] = line_c(r)
    ds = {}
    scheme_rows = lists[("DS", level)].get(code, [])
    for r in scheme_rows[:TOP_SCHEMES]:
        key = slug(r["name"])
        if key in ds or key in ("others", ""):
            _stop(f"two schemes at {level} {code} give the key {key!r}")
        ds[key] = {"name": r["name"], "approvals": _i(r["approvals"]),
                   "amount": _f(r["amount"])}
    rest = scheme_rows[TOP_SCHEMES:]
    if rest:
        ds["others"] = {"name": "All other schemes", "others": len(rest),
                        "approvals": sum(_i(r["approvals"]) for r in rest),
                        "amount": float(sum(_f(r["amount"]) for r in rest))}
    auth_rows = lists[("DA", level)].get(code, [])
    authority = None
    if rows["F1"]["value"] and auth_rows:
        authority = {"lines": [{"name": r["name"],
                                "approvals": _i(r["approvals"])}
                               for r in auth_rows[:TOP_AUTHORITIES]],
                     "others": sum(_i(r["approvals"])
                                   for r in auth_rows[TOP_AUTHORITIES:])}
    plan = None
    if a3:
        plan = {"tied": _f(m["D_tied"]), "untied": _f(m["D_untied"]),
                "tied_share": _f(m["D_tied_share"]),
                "untied_share": _f(m["D_untied_share"])}
    sheet["lists"] = {"B": b, "C": c, "CT": ct,
                      "D": {"plan": plan, "authority": authority}, "DS": ds}
    if level != "gp":
        sheet["lists"]["J"] = {}
    return sheet


def build(views_dir: str, whole: str = WHOLE_NAME, log: list | None = None) -> dict:
    """Every sheet, from the views. Returns {"sheets": [...], ...}."""
    log = log if log is not None else []
    paths = view_paths(views_dir)
    for p in paths.values():
        if not os.path.exists(p):
            _stop(f"{p} is missing -- build the views first")
    con = _connect(paths)
    places = _places(con, whole, log)
    years, latest, cutoff, old = _fiscal_years(con)
    _build_main(con, old)
    standing = _build_standing(con)
    lists = _build_lists(con, years)
    main = {level: {r["code"]: r for r in _rows(con, f"SELECT * FROM m_{level}")}
            for level in LEVELS}
    profile = {r["gp_lgd_code"]: r for r in _rows(con, """
        SELECT CAST(gp_lgd_code AS VARCHAR) AS gp_lgd_code, population_total,
               households, household_toilets, households_tap_water,
               trim(gp_size) AS gp_size,
               trim(social_composition) AS social_composition,
               trim(remoteness) AS remoteness FROM view4""")}
    whole_e2 = _i(main["all"]["all"]["E2"])
    for (raw,) in con.execute(
            "SELECT DISTINCT theme FROM view1 WHERE theme <> trim(theme) UNION "
            "SELECT DISTINCT focus_area_name FROM view1 "
            "WHERE focus_area_name <> trim(focus_area_name)").fetchall():
        log.append(f"name trimmed (theme / focus area): {raw!r}")
    con.close()

    sheets = {}
    for level in LEVELS:
        for place in places[level]:
            sheets[(level, place["code"])] = _assemble(
                level, place, main[level][place["code"]], standing, lists,
                whole_e2, cutoff, profile, whole)
    # J: member places, ordered by A6 from the lowest, blanks last (T3).
    for level in ("block", "district", "all"):
        child = CHILD[level]
        parent_col = {"block": "block_code", "district": "district_code",
                      "all": "all_code"}[level]
        members = {}
        for place in places[child]:
            members.setdefault(place[parent_col], []).append(
                sheets[(child, place["code"])])
        for code, kids in members.items():
            kids.sort(key=lambda s: (s["rows"]["A6"]["value"] is None,
                                     s["rows"]["A6"]["value"] or 0.0,
                                     s["name"], s["code"]))
            sheets[(level, code)]["lists"]["J"] = {
                s["code"]: {"code": s["code"], "name": s["name"],
                            "activities": s["rows"]["A1"]["value"],
                            "planned": s["rows"]["A3"]["value"],
                            "spent": s["rows"]["A5"]["value"],
                            "share": s["rows"]["A6"]["value"]}
                for s in kids}

    for sheet in sheets.values():
        sheet["sentences"] = write_sentences(sheet, whole)
    return {"sheets": sheets, "fiscal_years": years, "latest_year": latest,
            "cutoff_year": cutoff, "whole": whole, "log": log}


# =============================================================================
# STORE (T5): an index, numbered parts of independently compressed sheets, and
# a stamp. Format owned here, read by DiscoverChat/profile_store.py.
# =============================================================================

def _sheet_bytes(sheet: dict) -> bytes:
    text = json.dumps(sheet, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)
    return zlib.compress(text.encode("utf-8"), 9)


def write_store(result: dict, out_dir: str, provenance: dict, run_stamp: dict,
                synthetic: bool) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    sheets = result["sheets"]
    index = {level: {} for level in STORE_ORDER}
    parts, buf, part_no = [], bytearray(), 0

    def flush():
        nonlocal buf, part_no
        name = PART_PATTERN.format(part_no)
        with open(os.path.join(out_dir, name), "wb") as fh:
            fh.write(bytes(buf))
        parts.append(name)
        buf, part_no = bytearray(), part_no + 1

    counts = {}
    ids = set()
    # T3 (WP-D14b): the name table. One entry per sheet, in the sheets' own
    # order: the trimmed name, the sheet's own label, and the parents' codes
    # (a block has only its district; a district and the whole have none).
    places = {level: {} for level in STORE_ORDER}
    for level in STORE_ORDER:
        n_sheets = n_sentences = 0
        for (lv, code) in sorted(k for k in sheets if k[0] == level):
            sheet = sheets[(lv, code)]
            for s in sheet["sentences"]:
                if s["id"] in ids:
                    _stop(f"two sentences share the id {s['id']}")
                ids.add(s["id"])
            blob = _sheet_bytes(sheet)
            if buf and len(buf) + len(blob) > PART_LIMIT:
                flush()
            index[level][code] = [part_no, len(buf), len(blob)]
            entry = {"name": sheet["name"], "label": sheet["label"]}
            for parent in ("block", "district"):
                if parent in sheet["parents"]:
                    entry[parent] = sheet["parents"][parent]["code"]
            places[level][code] = entry
            buf.extend(blob)
            n_sheets += 1
            n_sentences += len(sheet["sentences"])
        counts[level] = {"sheets": n_sheets, "sentences": n_sentences}
    if buf or not parts:
        flush()

    # Retire parts of an earlier build that this one no longer writes.
    for name in os.listdir(out_dir):
        if re.fullmatch(PART_PATTERN.replace("{}", r"\d+").replace(".", r"\."),
                        name) and name not in parts:
            os.remove(os.path.join(out_dir, name))

    index_payload = {
        "what_this_is": (
            "WP-D14 place profile sheets: the index. One sheet per Gram "
            "Panchayat, block, district and the whole, each stored as its own "
            "zlib-compressed JSON inside the numbered part files; `sheets` maps "
            "level -> code -> [part, byte offset, byte length], so one sheet is "
            "read without reading any other; `places` maps level -> code -> "
            "name, label and parent codes, so a name finds its sheet without "
            "opening any (format 2, WP-D14b). Built by "
            "Insights/src/phase5g_profile_sheets.py; read by "
            "DiscoverChat/profile_store.py. Fetched by code, never searched."),
        "format": INDEX_FORMAT,
        "candidate_set_id": run_stamp["candidate_set_id"],
        "source_generated_at": run_stamp["generated_at"],
        "whole_name": result["whole"],
        "fiscal_years": result["fiscal_years"],
        "latest_year": result["latest_year"],
        "old_work_cutoff_year": result["cutoff_year"],
        "notes": NOTES,
        "parts": parts,
        "sheets": index,
        "places": places,
    }
    # Gzipped, through the corpora's own writer (no clock in the header): git
    # treats it as binary, so a Windows checkout (core.autocrlf) cannot turn
    # its line ends into CRLF and break its hash in the stamp.
    write_corpus_json(os.path.join(out_dir, INDEX_NAME), index_payload)

    files = [{"file": name, "sha256": sha256_of(os.path.join(out_dir, name)),
              "bytes": os.path.getsize(os.path.join(out_dir, name))}
             for name in [INDEX_NAME] + parts]
    stamp = {
        "what_this_is": (
            "Provenance for the profile sheet store (WP-D14). `generated_at` is "
            "the ONLY field expected to differ between two builds from the same "
            "views. `files` lists the index and every part with its SHA-256; "
            "the reader refuses a missing or altered file, a store whose "
            "candidate set differs from the findings corpus's, and any store "
            "marked synthetic."),
        "candidate_set_id": run_stamp["candidate_set_id"],
        "source_generated_at": run_stamp["generated_at"],
        "synthetic": bool(synthetic),
        "whole_name": result["whole"],
        "view_parquets": provenance,
        "counts": counts,
        "files": files,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(os.path.join(out_dir, STAMP_NAME), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump(stamp, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return stamp


# =============================================================================
# CHECKS (spec §9; T6). Each returns a one-line detail or raises AssertionError.
# Checks 2, 3, 4, 5, 7 and the stamp check read only the store (and the corpus),
# so the gate runs them; 1 and 6 need the view parquets and run in --check.
# =============================================================================

def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(RECONCILE_ABS, RECONCILE_REL * max(abs(a), abs(b)))


def all_sheets(store: ProfileStore):
    for level in STORE_ORDER:
        for code in store.codes(level):
            yield store.get(level, code)


SUM_FIELDS = [("A1", "value"), ("A2", "value"), ("A3", "value"),
              ("A4", "value"), ("A5", "value"), ("A7", "value"),
              ("E1", "value"), ("E2", "value"), ("E3", "value"),
              ("E3", "planned"), ("E4", "value"), ("E4", "uploads"),
              ("E5", "value"), ("E5", "planned"), ("E5", "spent"),
              ("F1", "value"), ("F2", "value"), ("G1", "value"),
              ("G2", "value"), ("H1", "value"), ("H2", "value"),
              ("H2", "planned")]
SHARE_FIELDS = [("A2", "share", "A2", "A1"), ("A6", "value", "A5", "A3"),
                ("F1", "share", "F1", "A1"), ("G3", "value", "A5", "G2")]


def check_parts_add_up(store: ProfileStore) -> str:
    """Check 2: Gram Panchayats add to their block, blocks to their district,
    districts to the whole -- every main-row sum and every by-year line."""
    sheets = {(s["level"], s["code"]): s for s in all_sheets(store)}
    parent_of = {"gp": "block", "block": "district", "district": "all"}
    totals, problems, compared = {}, [], 0
    for (level, code), s in sheets.items():
        if level == "all":
            continue
        up = parent_of[level]
        pcode = "all" if up == "all" else s["parents"][up]["code"]
        acc = totals.setdefault((up, pcode), {})
        for row, field in SUM_FIELDS:
            acc[(row, field)] = acc.get((row, field), 0.0) + s["rows"][row][field]
        for year, line in s["lists"]["B"].items():
            for field in ("activities", "no_cost", "planned", "spent", "abandoned"):
                k = ("B", year, field)
                acc[k] = acc.get(k, 0.0) + line[field]
    for (level, code), acc in totals.items():
        s = sheets[(level, code)]
        for k, v in acc.items():
            stored = (s["lists"]["B"][k[1]][k[2]] if k[0] == "B"
                      else s["rows"][k[0]][k[1]])
            compared += 1
            if not _close(v, stored):
                problems.append((level, code, k, v, stored))
    assert not problems, f"{len(problems)} sums do not add up: {problems[:3]}"
    assert compared, "no sums compared"
    return (f"{compared:,} parent figures equal the sum of their members "
            f"(Gram Panchayat -> block -> district -> whole)")


def check_shares(store: ProfileStore) -> str:
    """Check 3: every share at every level is its own numerator over its own
    denominator -- never the average of its members' shares."""
    problems, multi, checked = [], 0, 0
    for s in all_sheets(store):
        rows = s["rows"]
        for row, field, num, den in SHARE_FIELDS:
            d = rows[den]["value"]
            want = rows[num]["value"] / d if d else None
            got = rows[row][field]
            checked += 1
            if (want is None) != (got is None) or (
                    want is not None and not _close(want, got)):
                problems.append((s["level"], s["code"], row, want, got))
        members = s["lists"].get("J", {})
        if len(members) > 1:
            multi += 1
    assert not problems, f"{len(problems)} shares are not re-derived: {problems[:3]}"
    ref = store.get("block", REFERENCE_SHARE_BLOCK)
    if ref is not None and len(ref["lists"]["J"]) > 1:
        avg = sum(m["share"] for m in ref["lists"]["J"].values()
                  if m["share"] is not None) / len(ref["lists"]["J"])
        assert not _close(avg, ref["rows"]["A6"]["value"])
        extra = (f"; {ref['label']} {fmt_share(ref['rows']['A6']['value'])}, not "
                 f"the members' average {fmt_share(avg)}")
    else:
        extra = ""
    return (f"{checked:,} shares re-derived from their own parts, "
            f"{multi:,} places with more than one member{extra}")


def check_insights(store: ProfileStore, decompositions) -> str:
    """Check 4: every view3 breakdown total for a place (or the whole) on a
    measure the sheet holds equals the sheet's figure; money displays equal.
    Places are matched by level and the record's resolved code (Gram
    Panchayat) or by name within the level (block, district: the record
    resolves those by name only). Zero compared at a level is a failure."""
    names = {}
    for level in ("block", "district"):
        for code in store.codes(level):
            s = store.get(level, code)
            if s["name"] in names.setdefault(level, {}):
                raise AssertionError(f"two {level}s are named {s['name']!r}")
            names[level][s["name"]] = code
    compared = {lv: 0 for lv in LEVELS}
    problems = []
    whole_a7 = None
    for r in decompositions:
        if r.get("finding_id") == "d1-00248":
            whole_a7 = r
        if r["view"] != "view3" or r["measure"] not in INSIGHT_MEASURES:
            continue
        sub = r["subspace"]
        if not sub:
            level, code = "all", "all"
        elif len(sub) == 1 and sub[0][0] in PLACE_DIMENSION:
            level = PLACE_DIMENSION[sub[0][0]]
            if level == "gp":
                codes = r["geography"]["gp_lgd_codes"]
                if len(codes) != 1:
                    problems.append((r["finding_id"], "unresolved", codes))
                    continue
                code = str(codes[0])
            else:
                code = names[level].get(sub[0][1])
        else:
            continue
        sheet = store.get(level, code) if code else None
        if sheet is None:
            problems.append((r["finding_id"], "no sheet", level, sub))
            continue
        row, field = INSIGHT_MEASURES[r["measure"]]
        value = sheet["rows"][row][field]
        compared[level] += 1
        if not _close(float(r["total"]), float(value)):
            problems.append((r["finding_id"], level, code, r["measure"],
                             r["total"], value))
        if field == "value" and row in MONEY_MEASURE:
            if sheet["rows"][row]["display"] != r["total_display"]:
                problems.append((r["finding_id"], "display",
                                 sheet["rows"][row]["display"],
                                 r["total_display"]))
    assert not problems, (f"{len(problems)} sheet figures disagree with the "
                          f"insights: {problems[:3]}")
    empty = [lv for lv, n in compared.items() if n == 0]
    assert not empty, f"check 4 compared zero records at: {empty}"
    whole = store.get("all", "all")
    if whole_a7 is not None:
        a7 = whole["rows"]["A7"]
        assert _close(whole_a7["total"], a7["value"]), (whole_a7["total"], a7)
        assert whole_a7["total_display"] == a7["display"], (
            whole_a7["total_display"], a7["display"])
        a7_line = (f"; the whole's A7 = d1-00248 "
                   f"({signed_money(a7['display'], 'overspend_vs_plan')})")
    else:
        a7_line = ""
        if store.stamp().get("synthetic") is False:
            raise AssertionError("record d1-00248 is not in the corpus")
    return ("records compared: " + ", ".join(f"{lv} {n:,}" for lv, n in
                                               compared.items()) + a7_line)


def _row_record(sheet: dict, sentence: dict) -> tuple:
    """The stored record a sentence was written from, and its value kind."""
    row, key = sentence["row"], sentence["key"]
    if row in ("B", "C", "CT", "DS", "J"):
        return sheet["lists"][row][key], None
    if row == "D":
        return sheet["lists"]["D"][key], None
    if row == "G1":
        g1, g2 = sheet["rows"]["G1"], sheet["rows"]["G2"]
        return {"value": g1["value"], "amount": g2["value"]}, "money"
    if row == "F1" or row == "A2":
        rec = dict(sheet["rows"][row])
        rec["of"] = sheet["rows"]["A1"]["value"]
        return rec, ROW_VALUE_KIND.get(row)
    if row == "E2":
        return sheet["rows"]["E2"], "count"
    return sheet["rows"][row], ROW_VALUE_KIND.get(row)


def _allowed(record, row_kind, out: set, displays: list) -> None:
    """Numerals of every stored value of a record, through its formatter."""
    if isinstance(record, list):
        for item in record:
            _allowed(item, row_kind, out, displays)
        return
    if not isinstance(record, dict):
        return
    for field, value in record.items():
        if field.endswith("display") and isinstance(value, str):
            displays.append((field, value, record, row_kind))
            continue
        if isinstance(value, (dict, list)):
            _allowed(value, row_kind, out, displays)
        elif isinstance(value, str):
            out.update(numerals(value))
        elif isinstance(value, bool) or value is None:
            continue
        else:
            kind = kind_of(field, row_kind)
            if kind is None:
                raise AssertionError(f"no formatter for the stored field {field!r}")
            out.update(numerals(FORMAT[kind](value)))


def check_sentences(store: ProfileStore) -> str:
    """Check 5 (the layout-formatter-parity proof): every numeral in every
    sentence is a stored value of the sentence's row through the stored
    formatter, and every stored display string is its value through it."""
    problems, n_sent, n_disp = [], 0, 0
    ids = set()
    for s in all_sheets(store):
        names = {s["name"], s["label"]}
        names.update(p["name"] for p in s["parents"].values())
        name_nums = set()
        for n in names:
            name_nums.update(numerals(n))
        for item in s["sentences"]:
            n_sent += 1
            sid = item["id"]
            if (sid in ids or len(sid) > ID_MAX or " " in sid or "[" in sid
                    or "]" in sid or not SHEET_ID_RE.match(sid)):
                problems.append((sid, "id"))
            ids.add(sid)
            record, kind = _row_record(s, item)
            allowed, displays = set(name_nums), []
            _allowed(record, kind, allowed, displays)
            if item["row"] == "E2":
                allowed.update(numerals(fmt_count(record.get("whole", 0))))
            for field, text, rec, rk in displays:
                n_disp += 1
                base = field[:-len("_display")] if field != "display" else "value"
                regen = display(base, rec.get(base), rk,
                                MONEY_MEASURE.get(item["row"]))
                if regen is not None and numerals(regen) != numerals(text):
                    problems.append((sid, "display", text, regen))
                allowed.update(numerals(text))
            stray = [t for t in numerals(item["sentence"]) if t not in allowed]
            if stray:
                problems.append((sid, stray, item["sentence"]))
    assert not problems, (f"{len(problems)} sentences hold a figure that is not "
                          f"stored: {problems[:3]}")
    return (f"{n_sent:,} sentences: every numeral is a stored value through the "
            f"stored formatter; {n_disp:,} display strings regenerated; "
            f"{len(ids):,} ids unique, at most {ID_MAX} characters, no space "
            f"or bracket")


def check_stamp(store: ProfileStore, findings_stamp: dict,
                decompose_stamp: dict | None) -> str:
    """The store's stamp matches the corpus: same candidate set, same "as of",
    same view parquets as the decomposition corpus."""
    st = store.stamp()
    assert not st.get("synthetic"), "the store is marked synthetic"
    assert st["candidate_set_id"] == findings_stamp["candidate_set_id"], (
        st["candidate_set_id"], findings_stamp["candidate_set_id"])
    if decompose_stamp is not None:
        assert st["candidate_set_id"] == decompose_stamp["candidate_set_id"]
        for name, prov in st["view_parquets"].items():
            want = decompose_stamp["view_parquets"].get(name)
            assert want and want["sha256"] == prov["sha256"], (
                f"{name}: the store was built from other views than the "
                f"decomposition corpus")
    store.verify()
    return (f"candidate set {st['candidate_set_id']}, as of "
            f"{st['source_generated_at']}, {len(st['view_parquets'])} view "
            f"hashes = the decomposition corpus's, {len(st['files'])} files "
            f"verified")


def check_views(store: ProfileStore, views_dir: str) -> str:
    """Check 1: every A, E, F, G figure of a Gram Panchayat equals the sum of
    its view3 column, re-summed here by pandas (an independent pass from the
    DuckDB build), and the view4 lifetime column where view4 holds one."""
    import pandas as pd
    paths = view_paths(views_dir)
    v3 = pd.read_parquet(paths["view3"])
    v4 = pd.read_parquet(paths["view4"]).set_index("gp_lgd_code")
    sums = v3.groupby("gp_lgd_code")[sorted(set(V3_SUMS.values()))].sum()
    lifetime = [c for c in set(V3_SUMS.values()) if c in v4.columns]
    problems, compared = [], 0
    for code in store.codes("gp"):
        s = store.get("gp", code)
        for fig, col in V3_SUMS.items():
            row, field = ("E4", "uploads") if fig == "E4u" else (fig, "value")
            got = s["rows"][row][field]
            want = float(sums.loc[code, col]) if code in sums.index else 0.0
            compared += 1
            if not _close(want, got):
                problems.append((code, fig, want, got))
            if col in lifetime:
                compared += 1
                if not _close(float(v4.loc[code, col]), got):
                    problems.append((code, fig, "view4", v4.loc[code, col], got))
    assert not problems, f"{len(problems)} figures differ from the views: {problems[:3]}"
    return (f"{compared:,} Gram Panchayat figures equal the view3 sums "
            f"(re-summed by pandas) and the view4 lifetime columns")


def check_every_place(store: ProfileStore, views_dir: str) -> str:
    """Check 6: every place in the master has a sheet, and nothing else does."""
    import pandas as pd
    v4 = pd.read_parquet(view_paths(views_dir)["view4"])
    want = {"gp": set(v4.gp_lgd_code.astype(str)),
            "block": set(v4.block_code.astype(str)),
            "district": set(v4.district_code.astype(str)), "all": {"all"}}
    for level, codes in want.items():
        have = set(store.codes(level))
        assert have == codes, (level, sorted(codes - have)[:5],
                               sorted(have - codes)[:5])
    v3 = pd.read_parquet(view_paths(views_dir)["view3"])
    idle = sorted(want["gp"] - set(v3.loc[v3.n_activities > 0, "gp_lgd_code"]))
    return (", ".join(f"{lv} {len(c):,}" for lv, c in want.items())
            + f" sheets, one per place in the master; {len(idle)} with no "
              f"activity")


# ── Check 7: the reference figures of spec §13 and the Appendix A examples ──
# A FIXED EXPECTATION TABLE, used by nothing but this check. It is the one
# place the sample's size appears, because the spec states it (D15 governs the
# build's logic, not its reference answers).
REFERENCE_SHARE_BLOCK = "3745"      # Rangeilunda block (spec §9 check 3)

REFERENCE = {
    ("gp", "119936"): {
        "A1": (852, "all", 2, "high", 20, 602.5),
        "A2": (392, None, None, None, None, None, ("share", 0.460)),
        "A3": (76548042, "all", 2, "high", 20, 30986778),
        "A4": (20784410, "all", 2, "high", 20, 13707759.5),
        "A5": (17579894, "all", 2, "high", 20, 12765765.3),
        "A6": (0.229658, "all", 5, "low", 20, 0.420457),
        "A7": (-58968148,),
        "E1": (154, "all", 2, "high", 20, 95.5),
        "E2": (13, "all", 1, "high", 20, 0, ("whole", 17)),
        "E3": (22, None, None, None, None, None, ("planned", 272440),
               ("top_year", "2024-2025"), ("top_year_count", 21)),
        "E4": (129, "all", 2, "high", 20, 79, ("uploads", 553)),
        "E5": (55, None, None, None, None, None, ("planned", 10426968),
               ("spent", 8963247), ("share", 0.860)),
        "F1": (168, "all", 1, "high", 20, 96, ("share", 0.197)),
        "F2": (168,),
        "G1": (46304795.56, "all", 5, "high", 20, 29779715.50),
        "G2": (52838871.78, "all", 4, "high", 20, 33647520.815),
        "G3": (0.332708, "all", 9, "low", 20, 0.421689),
        "H1": (0,),
        "H2": (49, None, None, None, None, None, ("planned", 3490278)),
    },
    ("block", "3843"): {
        "A1": (852, "all", 5, "high", 16, 712),
        "A3": (76548042, "all", 2, "high", 16, 44840248),
        "A4": (20784410, "all", 5, "high", 16, 15087289.5),
        "A5": (17579894, "all", 5, "high", 16, 13963300.5),
        "A6": (0.229658, "all", 4, "low", 16, 0.365570),
        "E1": (154, "all", 5, "high", 16, 104),
        "E2": (13, "all", 1, "high", 16, 0),
        "E4": (129, "all", 5, "high", 16, 83),
        "F1": (168, "all", 4, "high", 16, 104),
        "G1": (46304795.56, "all", 6, "high", 16, 37230713),
        "G2": (52838871.78, "all", 5, "high", 16, 35410176.78),
        "G3": (0.332708, "all", 6, "low", 16, 0.465430),
    },
    ("all", "all"): {
        "A1": (12704,), "A2": (7074,), "A3": (773088536,), "A4": (288438745,),
        "A5": (253475090.46,), "A6": (0.327873,), "A7": (-519613445.54,),
        "E1": (2110,), "E2": (17,), "E3": (420,), "E4": (1675, None, None,
                                                         None, None, None,
                                                         ("uploads", 8267)),
        "F1": (2101,), "F2": (2095,), "G1": (664791435.89,),
        "G2": (685750811.29,),
    },
    ("block", "3745"): {"A3": (118410265,), "A5": (27329118,),
                        "A6": (0.230800,)},
    ("block", "3823"): {"A6": (0.558936,)},
    ("district", "321"): {"A6": (0.558936,)},
    ("district", "318"): {"A6": (0.167013, "all", 1, "low", 9, None)},
    ("district", "323"): {"A6": (0.229658,)},
}
REFERENCE_BY_YEAR = {   # Kalimela block; the Gram Panchayat is the same
    "2020-2021": (20, 0, 4490312, 4200837, "93.6%"),
    "2021-2022": (32, 0, 6443270, 3320583, "51.5%"),
    "2022-2023": (28, 0, 3576920, 2884416, "80.6%"),
    "2023-2024": (335, 196, 26182640, 2894236, "11.1%"),
    "2024-2025": (268, 72, 29995250, 3159940, "10.5%"),
    "2025-2026": (169, 124, 5859650, 1119882, "19.1%"),
}
REFERENCE_FOCUS = [("Drinking water", 166, 37376058, 6098020),
                   ("Land improvement", 57, 7395000, 0),
                   ("Maintenance of community system", 100, 6202800, 1153867),
                   ("Sanitation", 118, 5289128, 3362022),
                   ("Roads", 27, 5218686, 1972350)]
REFERENCE_NOTHING_SPENT = ("Poverty allevation programme", 114, 3709000, 0)
REFERENCE_MONEY_SOURCE = {
    "tied": 9228256, "untied": 67319786,
    "schemes": [("XV Finance Commission", 125, 13889087),
                ("5TH STATE FINANCE COMMISSION", 41, 6621323),
                ("Own Funds", 2, 274000)],
    "authorities": [("BDO", 91), ("Sarpanch", 72), ("Engineer", 3)],
    "authority_others": 2,
}
REFERENCE_PROFILE = {"population": 10681, "gp_size": "10,000 and above",
                     "households": 200, "social_composition": "ST-majority",
                     "remoteness": "Near", "ratio": "53.4"}

# Appendix A examples, character for character (R6). id suffix -> sentence.
APPENDIX_A = {
    "p-gp-119936": {
        "A1": "Kalimela Gram Panchayat has 852 planned activities, the 2nd most of 20 Gram Panchayats. The middle value for these 20 is 602.5.",
        "A2": "392 of them (46.0%) have no cost attached.",
        "A3": "Its planned cost is Rs 7.65 crore, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.",
        "A4": "Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.37 crore.",
        "A5": "It spent Rs 1.76 crore on planned activities, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.",
        "A6": "Spending is 23.0% of the planned cost, the 5th lowest of 20 Gram Panchayats. The middle value is 42.0%.",
        "A7": "Spending is Rs 5.90 crore below plan.",
        "B-2020-2021": "In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.",
        "B-2023-2024": "In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.",
        "C-drinking-water": "Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.",
        "C-land-improvement": "Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.",
        "D-plan": "Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).",
        "DS-xv-finance-commission": "XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned.",
        "DS-5th-state-finance-commission": "5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned.",
        "DS-own-funds": "Own Funds: 2 approvals, Rs 2.74 lakh sanctioned.",
        "D-authority": "Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2.",
        "E1": "154 works are marked ongoing, the 2nd most of 20 Gram Panchayats. The middle value is 95.5.",
        "E2": "13 works are marked completed, out of 17 in the whole sample.",
        "E3": "22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.",
        "E4": "129 activities have photo evidence (553 uploads), the 2nd most of 20 Gram Panchayats. The middle value is 79.",
        "E5": "55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).",
        "F1": "168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats.",
        "F2": "168 activities have a technical approval on file.",
        "G1": "Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.",
        "G3": "33.3% of the payments are linked to a planned activity. The middle value is 42.2%.",
        "H2": "49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.",
        "H5": "Its profile reports 10,681 people in 200 households, which is 53.4 people per household.",
        "I1": "Its profile reports a population of 10,681 (size band: 10,000 and above).",
        "I2": "Its profile reports 200 households.",
        "I3": "Its profile classes it as ST-majority and as near a bus stop.",
    },
    "p-block-3843": {
        "A1": "Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.",
        "A3": "Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.",
        "A5": "It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.",
        "A6": "Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.",
        "F1": "168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks.",
        "G3": "33.3% of the payments are linked to a planned activity. The middle value is 46.5%.",
        "I4": "Kalimela block has 1 Gram Panchayat in the data.",
        "J-119936": "Kalimela Gram Panchayat: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan.",
    },
    "p-all": {
        "A1": "The whole sample has 12,704 planned activities.",
        "A2": "7,074 of them (55.7%) have no cost attached.",
        "A3": "Its planned cost is Rs 77.31 crore.",
        "A5": "It spent Rs 25.35 crore on planned activities.",
        "A6": "Spending is 32.8% of the planned cost.",
        "A7": "Spending is Rs 51.96 crore below plan.",
        "I4": "The whole sample has 9 districts, 16 blocks and 20 Gram Panchayats.",
    },
}


def _ref_value_ok(want, got) -> bool:
    if isinstance(want, str) or isinstance(got, str):
        return want == got
    if got is None:
        return False
    if abs(want) < 1.5 and abs(want) > 0 and isinstance(want, float):
        return abs(want - got) < 5e-7 or round(got, 3) == round(want, 3)
    return _close(float(want), float(got)) or abs(float(want) - float(got)) < 0.006


def check_reference(store: ProfileStore) -> str:
    """Check 7: spec §13 reproduced, and every Appendix A example character for
    character (gate items 1 and 2)."""
    problems, n = [], 0
    for (level, code), rows in REFERENCE.items():
        s = store.get(level, code)
        assert s is not None, f"no sheet for {level} {code}"
        for row, spec in rows.items():
            r = s["rows"][row]
            n += 1
            if not _ref_value_ok(spec[0], r["value"]):
                problems.append((level, code, row, "value", spec[0], r["value"]))
            if len(spec) > 1 and spec[1] is not None:
                st = r["standing"][spec[1]]
                hi = spec[3] == "high"
                rank = st["rank_high"] if hi else st["rank_low"]
                if rank != spec[2] or st["peers"] != spec[4]:
                    problems.append((level, code, row, "standing", spec[2:5],
                                     (st["rank_high"], st["rank_low"],
                                      st["peers"])))
                if spec[5] is not None and not _ref_value_ok(spec[5], st["median"]):
                    problems.append((level, code, row, "median", spec[5],
                                     st["median"]))
            for extra in spec[6:]:
                field, want = extra
                n += 1
                if not _ref_value_ok(want, r[field]):
                    problems.append((level, code, row, field, want, r[field]))
    for code in ("3843", "119936"):
        level = "block" if code == "3843" else "gp"
        b = store.get(level, code)["lists"]["B"]
        for year, (acts, nc, planned, spent, share) in REFERENCE_BY_YEAR.items():
            line = b[year]
            n += 1
            got = (line["activities"], line["no_cost"], line["planned"],
                   line["spent"], fmt_share(line["share"]))
            if got != (acts, nc, planned, spent, share):
                problems.append((level, code, "B", year, got))
    kal = store.get("gp", "119936")
    focus = list(kal["lists"]["C"].values())
    got = [(c["name"], c["activities"], c["planned"], c["spent"])
           for c in focus[:len(REFERENCE_FOCUS)]]
    n += 1
    if got != REFERENCE_FOCUS:
        problems.append(("C", got))
    if (REFERENCE_NOTHING_SPENT[0], *REFERENCE_NOTHING_SPENT[1:]) not in [
            (c["name"], c["activities"], c["planned"], c["spent"]) for c in focus]:
        problems.append(("C nothing spent", REFERENCE_NOTHING_SPENT))
    plan = kal["lists"]["D"]["plan"]
    ms = REFERENCE_MONEY_SOURCE
    if (plan["tied"], plan["untied"]) != (ms["tied"], ms["untied"]):
        problems.append(("D plan", plan))
    schemes = [(d["name"], d["approvals"], d["amount"])
               for d in kal["lists"]["DS"].values()]
    if schemes != ms["schemes"]:
        problems.append(("DS", schemes))
    auth = kal["lists"]["D"]["authority"]
    if ([(a["name"], a["approvals"]) for a in auth["lines"]] != ms["authorities"]
            or auth["others"] != ms["authority_others"]):
        problems.append(("D authority", auth))
    rows = kal["rows"]
    prof = (rows["I1"]["population"], rows["I1"]["gp_size"],
            rows["I2"]["households"], rows["I3"]["social_composition"],
            rows["I3"]["remoteness"], fmt_ratio(rows["H5"]["ratio"]))
    if prof != tuple(REFERENCE_PROFILE.values()):
        problems.append(("profile", prof))
    n += 5
    examples = 0
    for prefix, lines in APPENDIX_A.items():
        for suffix, want in lines.items():
            examples += 1
            got = store.sentence(f"{prefix}-{suffix}")
            if got is None or got["sentence"] != want:
                problems.append((f"{prefix}-{suffix}",
                                 got and got["sentence"], want))
    assert not problems, (f"{len(problems)} reference figures or examples not "
                          f"reproduced: {problems[:4]}")
    return (f"{n} spec §13 reference figures reproduced; {examples} Appendix A "
            f"examples character for character")


def run_checks(store: ProfileStore, views_dir: str | None, decompositions,
               findings_stamp, decompose_stamp, which=None) -> int:
    checks = [
        ("1 equal to the views", lambda: check_views(store, views_dir)),
        ("2 the parts add up", lambda: check_parts_add_up(store)),
        ("3 shares re-derived", lambda: check_shares(store)),
        ("4 equal to the insights",
         lambda: check_insights(store, decompositions)),
        ("5 sentences hold only stored figures", lambda: check_sentences(store)),
        ("6 every place has a sheet",
         lambda: check_every_place(store, views_dir)),
        ("7 reference figures", lambda: check_reference(store)),
        ("stamp matches the corpus",
         lambda: check_stamp(store, findings_stamp, decompose_stamp)),
    ]
    failures = 0
    for name, fn in checks:
        if which and name.split()[0] not in which:
            continue
        try:
            detail = fn()
            print(f"  PASS  {name:<38} {detail}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {name:<38} {exc}")
    return failures


# =============================================================================
# MAIN
# =============================================================================

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WP-D14 place profile sheets")
    ap.add_argument("--check", action="store_true",
                    help="run the seven checks of spec §9 on the built store")
    ap.add_argument("--views-dir", default=VIEWS_DIR)
    ap.add_argument("--out-dir", default=MI_DIR)
    ap.add_argument("--whole-name", default=WHOLE_NAME)
    ap.add_argument("--synthetic", action="store_true",
                    help="T7 scale test: lift the view-hash refusal, write "
                         "outside metainsights/, mark the stamp synthetic")
    ap.add_argument("--only", default=None,
                    help="comma-separated check numbers for --check (e.g. 2,3,5,6)")
    args = ap.parse_args(argv)

    out_dir = os.path.abspath(args.out_dir)
    if args.synthetic and os.path.normcase(out_dir) == os.path.normcase(
            os.path.abspath(MI_DIR)):
        print("STOP: a synthetic store must be written outside metainsights/")
        return 2

    run_stamp = load_json(os.path.join(MI_DIR, "global_feed_source_set.json"))
    d_stamp_path = os.path.join(MI_DIR, "decompose_corpus_stamp.json")
    decompose_stamp = load_json(d_stamp_path) if os.path.exists(d_stamp_path) else None

    if args.check:
        store = ProfileStore(out_dir, allow_synthetic=args.synthetic,
                             expected_candidate_set=None)
        which = set(args.only.split(",")) if args.only else None
        decompositions = []
        if not which or "4" in which:
            from phase5d_retrieval_corpus import read_corpus_json
            decompositions = read_corpus_json(os.path.join(
                MI_DIR, "decompose_corpus.json.gz"))["records"]
        findings_stamp = load_json(os.path.join(MI_DIR,
                                                "retrieval_corpus_stamp.json"))
        print(f"  profile sheets --check  ({out_dir})")
        failures = run_checks(store, args.views_dir, decompositions,
                              findings_stamp, decompose_stamp, which)
        print(f"\n  {'all green' if not failures else f'{failures} FAILED'}")
        return 1 if failures else 0

    t0 = time.time()
    paths = view_paths(args.views_dir)
    provenance = parquet_provenance(paths)
    if not args.synthetic:
        want = (decompose_stamp or {}).get("view_parquets", {})
        bad = [n for n, p in provenance.items()
               if want.get(n, {}).get("sha256") != p["sha256"]]
        if bad:
            print(f"STOP: {bad} differ from the view parquets the decomposition "
                  f"corpus was built from (decompose_corpus_stamp.json). Sheets "
                  f"built from other views would disagree with the insights.")
            return 2
    log = []
    result = build(args.views_dir, args.whole_name, log)
    t_build = time.time() - t0
    stamp = write_store(result, out_dir, provenance, run_stamp, args.synthetic)
    elapsed = time.time() - t0
    for line in log:
        print(f"  log: {line}")
    for level, c in stamp["counts"].items():
        print(f"  {level:<9} {c['sheets']:>6,} sheets  {c['sentences']:>8,} sentences")
    total = sum(f["bytes"] for f in stamp["files"])
    print(f"  {len(stamp['files'])} files, {total / 1e6:.1f} MB, largest "
          f"{max(f['bytes'] for f in stamp['files']) / 1e6:.1f} MB")
    print(f"  built in {t_build:.1f} s, written in {elapsed - t_build:.1f} s "
          f"(total {elapsed:.1f} s) -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

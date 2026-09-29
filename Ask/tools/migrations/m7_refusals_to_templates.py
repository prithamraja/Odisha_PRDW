"""WP-6f T4, migration M7: refusals whose data or definition exists become templates.

    python tools/migrations/m7_refusals_to_templates.py            # apply (idempotent)
    python tools/migrations/m7_refusals_to_templates.py --check    # exit 1 if not applied

WHY (operator, 2026-09-28): "We are working on sample data, in prod, this data is
there. We should not have any refusals." Amended 2026-09-29: "let's not remove
the 14 questions — let's leave it as is with the refusal." So the refusals whose
columns EXIST (empty in the sample) or whose blocker was a missing DEFINITION
become real questions with SQL; the ones with no column anywhere in the schema
stay refusals, unchanged.

WHAT MOVES — 15 ids, out of `unanswerable_catalog.py` into `template_catalog.py`,
each keeping its id so every gold row and reference still resolves:

  group a, the columns exist and are empty in the sample (11)
    PLU-005                         activity_delegation.is_delegated / delegated_unit_*
    AST-004, AST-005                activity_asset.asset_loc_* / asset_unit_count /
    AST-010, AST-011                asset_unit_cost — NOT empty: about a third of the
                                    rows carry them (unit cost 3,841 of 12,704), so
                                    these answer with real figures on the sample too.
                                    The refusal reasons ("100% NULL") were wrong.
    BEN-001, 003, 007, 008, 011, 012  activity_nsap (0 rows in the sample), joined
                                    through activity_code to the activity's GP,
                                    block and scheme
  group b, a definition was missing (4), built to the definitions the operator
  confirmed on 2026-09-29
    PLN-022, PLN-023                "consistently delayed in GPDP approvals": a
                                    required $deadline; per block / district, the
                                    GPs whose MAIN plan was approved after it,
                                    the share late, and — over a span — in how
                                    many years more than half its GPs were late
    PLN-041, PLN-042                "consistently among the top / lowest
                                    priorities": per theme, in how many of the
                                    five most recent years in the data it ranked
                                    in the top 3 / bottom 3 by planned cost

WHAT STAYS a refusal, untouched: the 14 with no column in the schema, and
BEN-010 ("each pension scheme"). The brief moved BEN-010 only if
`activity_nsap.category` holds the pension scheme; `dim_code` carries no decode
for that column, so nothing says it does, and it stays (15 refusals, not 14).

Each moved entry: its `question` becomes the `abstract_question` with `{slot}`
placeholders; its hand paraphrases carry over unchanged (the derived block is
rebuilt by tools/derive_catalog.py from the new question); the universal
optional filters are added the way M1 did, and `$group_by` where the statement
is a single aggregate (M2's GROUPING SETS shape).

THE ORACLE. Every new statement is executed against the sample BEFORE anything
is written, with the parameters recorded for it in
`tests/data/workbook_test_report.json`, and its row count is recorded there —
the same contract gate 2 checks for the other 343.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402

GROUP_A = ("PLU-005", "AST-004", "AST-005", "AST-010", "AST-011",
           "BEN-001", "BEN-003", "BEN-007", "BEN-008", "BEN-011", "BEN-012")
GROUP_B = ("PLN-022", "PLN-023", "PLN-041", "PLN-042")
MOVED = GROUP_A + GROUP_B
STAYS = ("SCH-004", "PHY-002", "PHY-005", "SBM-SWM-033", "ALR-006", "ALR-007",
         "ALR-010", "DSS-004", "BEN-002", "BEN-004", "BEN-005", "BEN-006",
         "BEN-009", "BEN-010", "DQY-005")

# ── The SQL pieces every activity-view statement repeats (M1 / M2 idiom) ──────

_GEO = """\
  AND ($district_name IS NULL OR v.district_name IN (SELECT UNNEST($district_name)))
  AND ($block_name    IS NULL OR v.block_name    IN (SELECT UNNEST($block_name)))
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)"""
_UNIVERSAL = """\
  AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
  AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
  AND ($focus_area IS NULL OR v.focus_area_name IN (SELECT UNNEST($focus_area)))
  AND ($theme IS NULL OR v.theme IN (SELECT UNNEST($theme)))
  AND ($scheme IS NULL OR v.scheme_name IN (SELECT UNNEST($scheme)))
  AND ($tied_untied IS NULL OR v.tied_untied = $tied_untied)"""
# v_asset carries these four of the six (M1's VIEW_CARRIES), and no gp_lgd_code.
_ASSET_GEO = """\
  AND ($district_name IS NULL OR v.district_name IN (SELECT UNNEST($district_name)))
  AND ($block_name    IS NULL OR v.block_name    IN (SELECT UNNEST($block_name)))
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))"""
_ASSET_UNIVERSAL = """\
  AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
  AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
  AND ($focus_area IS NULL OR v.focus_area_name IN (SELECT UNNEST($focus_area)))
  AND ($theme IS NULL OR v.theme IN (SELECT UNNEST($theme)))"""


def _case(default: str, absent: str | None) -> str:
    """M2's breakdown CASE; `absent` names the column the ELSE gives back."""
    tail = f"ELSE {default}  -- absent: {absent}" if absent else f"ELSE {default} END"
    body = """CASE $group_by
                WHEN 'district'     THEN v.district_name
                WHEN 'block'        THEN v.block_name
                WHEN 'gp'           THEN v.gp_name
                WHEN 'theme'        THEN v.theme
                WHEN 'focus_area'   THEN v.focus_area_name
                WHEN 'status'       THEN v.status_label
                WHEN 'scheme'       THEN v.scheme_name
                WHEN 'plan_type'    THEN v.plan_type
                WHEN 'fiscal_year'  THEN v.fiscal_year
                WHEN 'total'        THEN 'All'
                """ + tail
    return body + ("\n              END AS group_label" if absent else " AS group_label")


def _slot(name, etype, **flags):
    return {"name": name, "entity_type": etype, **flags}


DATE = _slot("date_range", "fiscal_year", list=True)
GEO_SLOTS = [_slot("district_name", "district", optional=True, list=True),
             _slot("block_name", "block", optional=True, list=True),
             _slot("gp_name", "gp", optional=True, bind="code")]
UNIVERSAL_SLOTS = [_slot("plan_type", "plan_type", optional=True, list=True),
                   _slot("status", "status", optional=True, list=True),
                   _slot("focus_area", "focus_area", optional=True, list=True),
                   _slot("theme", "theme", optional=True, list=True),
                   _slot("scheme", "scheme", optional=True, list=True),
                   _slot("tied_untied", "tied_untied", optional=True)]
ASSET_UNIVERSAL_SLOTS = UNIVERSAL_SLOTS[:4]
GROUP_BY = _slot("group_by", "group_by", optional=True)
TOP_N = _slot("top_n", "top_n", optional=True, default="10")


def _absent(slots, **given):
    """The Test Report's parameters: every slot named, absent ones as null."""
    return {s["name"]: given.get(s["name"]) for s in sorted(slots, key=lambda s: s["name"])}


# ── group a ───────────────────────────────────────────────────────────────────

_NSAP = """FROM activity_nsap n
JOIN v_activity v ON v.activity_code = n.activity_code"""

SPECS: dict[str, dict] = {}

SPECS["PLU-005"] = dict(
    abstract_question="How many activities in {block_name} are delegated to another "
                      "panchayat tier for execution in {date_range}?",
    question_type="Count",
    sql=f"""
SELECT CAST(d.delegated_unit_level AS BIGINT) AS delegated_unit_level_code,
       CAST(d.delegated_unit_type AS BIGINT)  AS delegated_unit_type_code,
       COUNT(*) AS delegated_activities,
       COUNT(DISTINCT v.gp_lgd_code) AS gps
FROM v_activity v
JOIN activity_delegation d ON d.activity_code = v.activity_code
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
  AND d.is_delegated = 1
{_GEO}
{_UNIVERSAL}
GROUP BY 1, 2
ORDER BY delegated_activities DESC
""",
    slots=[DATE, *GEO_SLOTS, *UNIVERSAL_SLOTS],
    params={"date_range": "2025-2026", "block_name": "Attabira"},
)

SPECS["AST-004"] = dict(
    abstract_question="Where are the assets under activity {activity_code} located, "
                      "and how many units at each location?",
    question_type="Lookup",
    sql="""
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.asset_subcategory_label,
       CAST(v.asset_loc_code AS BIGINT) AS asset_location_code,
       v.asset_loc_unit_count AS units_at_location
FROM v_asset v
WHERE v.activity_code = $activity_code
""",
    slots=[_slot("activity_code", "activity_code")],
    params={"activity_code": "50378563"},
)

SPECS["AST-005"] = dict(
    abstract_question="What are the unit count and unit cost of assets created under "
                      "activity {activity_code}?",
    question_type="Lookup",
    sql="""
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.asset_subcategory_label,
       v.asset_unit_count AS unit_count,
       v.asset_unit_cost  AS cost_per_unit
FROM v_asset v
WHERE v.activity_code = $activity_code
""",
    slots=[_slot("activity_code", "activity_code")],
    params={"activity_code": "50378563"},
)

SPECS["AST-010"] = dict(
    abstract_question="What is the average unit cost of {asset_sub_category} across "
                      "{district_name} for {date_range}?",
    question_type="Aggregation",
    sql=f"""
SELECT v.asset_subcategory_label,
       COUNT(*) AS assets_counted,
       ROUND(AVG(v.asset_unit_cost), 2) AS avg_cost_per_unit,
       MIN(v.asset_unit_cost) AS min_cost_per_unit,
       MAX(v.asset_unit_cost) AS max_cost_per_unit
FROM v_asset v
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
  AND v.asset_unit_cost IS NOT NULL
  AND ($asset_sub_category IS NULL OR v.asset_subcategory_label = $asset_sub_category)
{_ASSET_GEO}
{_ASSET_UNIVERSAL}
GROUP BY 1
ORDER BY assets_counted DESC
""",
    slots=[DATE, _slot("asset_sub_category", "asset_subcategory", optional=True),
           *GEO_SLOTS[:2], _slot("gp_name", "gp", optional=True, bind="code"),
           *ASSET_UNIVERSAL_SLOTS],
    params={"date_range": "2021-2022", "asset_sub_category": "Road CC",
            "district_name": "Bargarh"},
)

# The district average is taken over the district (and sub-category) as a whole;
# a block or GP named narrows the LIST, not the average it is compared with.
SPECS["AST-011"] = dict(
    abstract_question="Which {asset_sub_category} assets in {district_name} have a unit "
                      "cost more than {threshold} percent above the district average "
                      "in {date_range}?",
    question_type="Listing",
    sql=f"""
WITH a AS (
    SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.district_name,
           v.asset_subcategory_label, v.asset_unit_cost,
           AVG(v.asset_unit_cost) OVER (
               PARTITION BY v.district_name, v.asset_subcategory_label) AS district_avg_unit_cost
    FROM v_asset v
    WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
      AND v.asset_unit_cost IS NOT NULL
      AND ($asset_sub_category IS NULL OR v.asset_subcategory_label = $asset_sub_category)
      AND ($district_name IS NULL OR v.district_name IN (SELECT UNNEST($district_name)))
      AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
      AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
      AND ($focus_area IS NULL OR v.focus_area_name IN (SELECT UNNEST($focus_area)))
      AND ($theme IS NULL OR v.theme IN (SELECT UNNEST($theme)))
)
SELECT a.activity_code, a.activity_name, a.gp_name, a.block_name, a.district_name,
       a.asset_subcategory_label, a.asset_unit_cost AS cost_per_unit,
       ROUND(a.district_avg_unit_cost, 2) AS district_avg_cost_per_unit,
       ROUND(100.0 * (a.asset_unit_cost - a.district_avg_unit_cost)
             / NULLIF(a.district_avg_unit_cost, 0), 2) AS pct_above_district_avg
FROM a
WHERE 100.0 * (a.asset_unit_cost - a.district_avg_unit_cost) / NULLIF(a.district_avg_unit_cost, 0) > $threshold
  AND ($block_name IS NULL OR a.block_name IN (SELECT UNNEST($block_name)))
  AND ($gp_name    IS NULL OR a.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
ORDER BY pct_above_district_avg DESC
""",
    slots=[DATE, _slot("asset_sub_category", "asset_subcategory", optional=True),
           _slot("threshold", "threshold"), *GEO_SLOTS, *ASSET_UNIVERSAL_SLOTS],
    params={"date_range": "2021-2022", "district_name": "Bargarh", "threshold": 50},
)

SPECS["BEN-001"] = dict(
    abstract_question="How many beneficiaries received benefits under {scheme} in "
                      "{gp_name} during {date_range}?",
    question_type="Count",
    sql=f"""
SELECT {_case("'All'", None)},
       COALESCE(SUM(n.beneficiary_count), 0) AS beneficiaries,
       COUNT(DISTINCT n.activity_code) AS activities
{_NSAP}
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
{_GEO}
{_UNIVERSAL}
GROUP BY GROUPING SETS ((group_label), ())
HAVING (GROUPING(group_label) = 1) = ($group_by IS NULL OR $group_by = 'total')
""",
    slots=[DATE, *GEO_SLOTS, *UNIVERSAL_SLOTS, GROUP_BY],
    params={"date_range": "2024-2025"},
)

SPECS["BEN-003"] = dict(
    abstract_question="How many beneficiaries are recorded across GPs of {block_name} "
                      "under {scheme} for {date_range}?",
    question_type="Count",
    sql=f"""
SELECT {_case("v.gp_name", "gp_name")}, CASE WHEN $group_by IS NULL THEN v.block_name END AS block_name,
       COALESCE(SUM(n.beneficiary_count), 0) AS beneficiaries,
       COUNT(DISTINCT n.activity_code) AS activities
{_NSAP}
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
{_GEO}
{_UNIVERSAL}
GROUP BY 1, 2
ORDER BY beneficiaries DESC
""",
    slots=[DATE, *GEO_SLOTS, *UNIVERSAL_SLOTS, GROUP_BY],
    params={"date_range": "2024-2025", "block_name": "Barpali"},
)

SPECS["BEN-007"] = dict(
    abstract_question="Which scheme has the most recorded beneficiaries in "
                      "{block_name} for {date_range}?",
    question_type="Ranking",
    sql=f"""
SELECT COALESCE(v.scheme_name, '(not recorded)') AS scheme_name,
       COALESCE(SUM(n.beneficiary_count), 0) AS beneficiaries,
       COUNT(DISTINCT n.activity_code) AS activities
{_NSAP}
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
{_GEO}
  AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
  AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
  AND ($focus_area IS NULL OR v.focus_area_name IN (SELECT UNNEST($focus_area)))
  AND ($theme IS NULL OR v.theme IN (SELECT UNNEST($theme)))
  AND ($tied_untied IS NULL OR v.tied_untied = $tied_untied)
GROUP BY 1
ORDER BY beneficiaries DESC
LIMIT $top_n
""",
    slots=[DATE, *GEO_SLOTS, TOP_N, *UNIVERSAL_SLOTS[:4], UNIVERSAL_SLOTS[5]],
    params={"date_range": "2024-2025", "block_name": "Barpali", "top_n": 10},
)

# An ABSENCE, read from the GP roster (the PLN-032 shape): a GP with no
# beneficiary record has no row in activity_nsap to find.
SPECS["BEN-008"] = dict(
    abstract_question="Which GPs in {block_name} have no recorded beneficiaries under "
                      "{scheme} for {date_range}?",
    question_type="Listing",
    sql="""
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (
        SELECT 1 FROM activity_nsap n
        JOIN v_activity v ON v.activity_code = n.activity_code
        WHERE v.gp_lgd_code = g.gp_lgd_code
          AND v.fiscal_year IN (SELECT UNNEST($date_range))
          AND COALESCE(n.beneficiary_count, 0) > 0
          AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
          AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
          AND ($focus_area IS NULL OR v.focus_area_name IN (SELECT UNNEST($focus_area)))
          AND ($theme IS NULL OR v.theme IN (SELECT UNNEST($theme)))
          AND ($scheme IS NULL OR v.scheme_name IN (SELECT UNNEST($scheme)))
          AND ($tied_untied IS NULL OR v.tied_untied = $tied_untied))
  AND ($district_name IS NULL OR g.zp_name IN (SELECT UNNEST($district_name)))
  AND ($block_name    IS NULL OR g.block_name IN (SELECT UNNEST($block_name)))
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
    slots=[DATE, *GEO_SLOTS[:2], *UNIVERSAL_SLOTS],
    params={"date_range": "2024-2025", "block_name": "Barpali"},
)

SPECS["BEN-011"] = dict(
    abstract_question="Compare beneficiary counts under {scheme} between {block_name} "
                      "and {block_name_2} for {date_range}.",
    question_type="Comparison",
    sql=f"""
SELECT {_case("v.block_name", "block_name")},
       COALESCE(SUM(n.beneficiary_count), 0) AS beneficiaries,
       COUNT(DISTINCT n.activity_code) AS activities,
       COUNT(DISTINCT v.gp_lgd_code) AS gps
{_NSAP}
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
{_UNIVERSAL}
  AND v.block_name IN ($block_name, $block_name_2)
GROUP BY 1
ORDER BY beneficiaries DESC
""",
    slots=[DATE, _slot("block_name", "block"), _slot("block_name_2", "block_2"),
           *UNIVERSAL_SLOTS, GROUP_BY],
    params={"date_range": "2024-2025", "block_name": "Barpali",
            "block_name_2": "Attabira"},
)

SPECS["BEN-012"] = dict(
    abstract_question="How has the beneficiary count under {scheme} in {gp_name} "
                      "changed over {date_range}?",
    question_type="Trend",
    sql=f"""
SELECT v.fiscal_year,
       COALESCE(SUM(n.beneficiary_count), 0) AS beneficiaries,
       COUNT(DISTINCT n.activity_code) AS activities
{_NSAP}
WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
{_GEO}
{_UNIVERSAL}
GROUP BY 1
ORDER BY 1
""",
    slots=[DATE, *GEO_SLOTS, *UNIVERSAL_SLOTS],
    params={"date_range": ["2022-2023", "2023-2024", "2024-2025"]},
)

# ── group b ───────────────────────────────────────────────────────────────────
#
# "Consistently delayed" (operator-confirmed 2026-09-29). A GP's plan for a year
# is LATE when its MAIN plan was approved after the deadline — the GPDP is the
# main plan; supplementary plans are approved mid-year by design, so counting
# them would measure who files one, not who is late. The officer gives ONE date
# for the latest year asked about; each earlier year's deadline is the same day
# that many years before (`to_years`), so a span is judged year by year.

_LATE = """\
    SELECT v.district_name, v.block_name, v.fiscal_year, v.gp_lgd_code,
           MAX(CASE WHEN v.approval_date > CAST($deadline AS DATE)
                        + to_years(CAST(LEFT(v.fiscal_year, 4) AS INTEGER)
                                   - (SELECT MAX(CAST(LEFT(y, 4) AS INTEGER))
                                      FROM (SELECT UNNEST($date_range) AS y)))
                    THEN 1 ELSE 0 END) AS late
    FROM v_plan v
    WHERE v.fiscal_year IN (SELECT UNNEST($date_range))
      AND v.plan_type = 'Main'
      AND ($district_name IS NULL OR v.district_name IN (SELECT UNNEST($district_name)))"""


def _delay_sql(unit: str, extra_filter: str) -> str:
    keys = "block_name, district_name" if unit == "block" else "district_name"
    return f"""
WITH per_gp AS (
{_LATE}{extra_filter}
    GROUP BY 1, 2, 3, 4
), per_year AS (
    SELECT {keys}, fiscal_year,
           COUNT(*) AS gps, SUM(late) AS gps_late
    FROM per_gp
    GROUP BY {keys}, fiscal_year
)
SELECT {keys},
       SUM(gps) AS gps,
       SUM(gps_late) AS gps_late,
       ROUND(100.0 * SUM(gps_late) / NULLIF(SUM(gps), 0), 2) AS pct_late,
       COUNT(*) AS years_counted,
       SUM(CASE WHEN 2 * gps_late > gps THEN 1 ELSE 0 END) AS years_mostly_late
FROM per_year
GROUP BY {keys}
ORDER BY pct_late DESC, years_mostly_late DESC, {keys}
LIMIT $top_n
"""


SPECS["PLN-022"] = dict(
    abstract_question="Which Blocks consistently experience delays in GPDP approvals "
                      "after the deadline {deadline} in {date_range}?",
    question_type="Ranking",
    sql=_delay_sql("block", """
      AND ($block_name    IS NULL OR v.block_name    IN (SELECT UNNEST($block_name)))"""),
    slots=[DATE, _slot("deadline", "deadline"), GEO_SLOTS[0], GEO_SLOTS[1], TOP_N],
    params={"date_range": "2024-2025", "deadline": "2024-06-30", "top_n": 10},
)

SPECS["PLN-023"] = dict(
    abstract_question="Which Districts consistently experience delays in GPDP "
                      "approvals after the deadline {deadline} in {date_range}?",
    question_type="Ranking",
    sql=_delay_sql("district", ""),
    slots=[DATE, _slot("deadline", "deadline"), GEO_SLOTS[0], TOP_N],
    params={"date_range": "2024-2025", "deadline": "2024-06-30", "top_n": 10},
)

# "Consistently among the top / lowest priorities" (operator-confirmed): per
# theme, in how many of the FIVE MOST RECENT fiscal years in the data it ranked
# in the top 3 (bottom 3) by planned cost. A theme with nothing planned in a year
# is in that year's ranking at 0 — the grid is every theme x every year — so a
# bottom-3 finish is not missed by having no rows. 'Unmapped theme' is not a
# theme. The question says the rule, so the echo does too.


def _priority_sql(direction: str, label: str) -> str:
    return f"""
WITH years AS (
    SELECT DISTINCT fiscal_year FROM v_activity ORDER BY fiscal_year DESC LIMIT 5
), themes AS (
    SELECT DISTINCT theme FROM v_activity WHERE theme <> 'Unmapped theme'
), cost AS (
    SELECT v.fiscal_year, v.theme, SUM(COALESCE(v.total_cost, 0)) AS planned_cost
    FROM v_activity v
    WHERE v.fiscal_year IN (SELECT fiscal_year FROM years)
      AND v.theme <> 'Unmapped theme'
{_GEO.replace("  AND", "      AND")}
      AND ($plan_type IS NULL OR v.plan_type IN (SELECT UNNEST($plan_type)))
      AND ($status IS NULL OR v.status_label IN (SELECT UNNEST($status)))
      AND ($scheme IS NULL OR v.scheme_name IN (SELECT UNNEST($scheme)))
      AND ($tied_untied IS NULL OR v.tied_untied = $tied_untied)
    GROUP BY 1, 2
), ranked AS (
    SELECT y.fiscal_year, t.theme, COALESCE(c.planned_cost, 0) AS planned_cost,
           RANK() OVER (PARTITION BY y.fiscal_year
                        ORDER BY COALESCE(c.planned_cost, 0) {direction}) AS rank_in_year
    FROM years y
    CROSS JOIN themes t
    LEFT JOIN cost c ON c.fiscal_year = y.fiscal_year AND c.theme = t.theme
)
SELECT theme,
       SUM(CASE WHEN rank_in_year <= 3 THEN 1 ELSE 0 END) AS {label},
       COUNT(*) AS years_counted,
       MIN(fiscal_year) || ' to ' || MAX(fiscal_year) AS period,
       SUM(planned_cost) AS planned_cost
FROM ranked
GROUP BY theme
ORDER BY {label} DESC, planned_cost {direction}, theme
"""


_PRIORITY_SLOTS = [*GEO_SLOTS, UNIVERSAL_SLOTS[0], UNIVERSAL_SLOTS[1],
                   UNIVERSAL_SLOTS[4], UNIVERSAL_SLOTS[5]]

SPECS["PLN-041"] = dict(
    abstract_question="Which themes have remained consistently among the top "
                      "priorities over the last five years (top 3 by planned cost, "
                      "in how many of the last 5 years)?",
    question_type="Ranking",
    sql=_priority_sql("DESC", "years_in_top_3"),
    slots=list(_PRIORITY_SLOTS),
    params={},
    keep_question=True,
)

SPECS["PLN-042"] = dict(
    abstract_question="Which themes have remained consistently among the lowest "
                      "priorities over the last five years (bottom 3 by planned "
                      "cost, in how many of the last 5 years)?",
    question_type="Ranking",
    sql=_priority_sql("ASC", "years_in_bottom_3"),
    slots=list(_PRIORITY_SLOTS),
    params={},
    keep_question=True,
)

# PLN-022 / PLN-023 name the deadline in the new question; the refusal's own
# wording ("…in a given year?") stays searchable as a hand paraphrase.
SPECS["PLN-022"]["keep_question"] = True
SPECS["PLN-023"]["keep_question"] = True


# Output column names are chosen so column_types.json types them without a new
# rule: a per-unit cost must read as a RATIO (never summed down a table), a
# delegation code as an identifier, a count of years as a count.

# ── Building the entries ──────────────────────────────────────────────────────

def _hand_paraphrases(source_lines: list[str], qid: str) -> list[str]:
    """The refusal's hand-written paraphrases (above the derived marker)."""
    for entry_id, start, end in dc._entry_spans(source_lines):
        if entry_id != qid:
            continue
        opened, closed = dc._find_block(source_lines, start, end,
                                        dc.PARAPHRASES_OPEN, dc.PARAPHRASES_CLOSE, qid)
        _, hand = dc._split_paraphrase_body(source_lines[opened + 1:closed], qid)
        return list(hand)
    raise KeyError(qid)


def build_entries(unanswerable: dict, un_lines: list[str]) -> dict[str, dict]:
    entries = {}
    for qid in MOVED:
        spec, refusal = SPECS[qid], unanswerable[qid]
        hand = _hand_paraphrases(un_lines, qid)
        if spec.get("keep_question") and refusal["question"] not in hand:
            hand = [refusal["question"], *hand]
        entries[qid] = {
            "abstract_question": spec["abstract_question"],
            "date_filter": None,
            "date_kind": None,
            "sql_template": spec["sql"].strip("\n"),
            "param_slots": copy.deepcopy(spec["slots"]),
            "result_ttl_seconds": 600,
            "caveat": None,
            "bracket": refusal["bracket"],
            "module": refusal["module"],
            "submodule": refusal["submodule"],
            "question_type": spec["question_type"],
            "answerable": "Partial",
            "paraphrases": hand,
        }
    return entries


def _emit(qid: str, entry: dict) -> str:
    """dc.emit_entry, with the paraphrase list carrying the derived markers."""
    text = dc.emit_entry(qid, {k: v for k, v in entry.items() if k != "paraphrases"})
    lines = text.split("\n")
    body = [dc.PARAPHRASES_OPEN]
    body += [f"{dc._ITEM_PAD}{p!r}," for p in entry["paraphrases"]]
    body += [dc._ITEM_PAD + dc.MARK_BEGIN, dc._ITEM_PAD + dc.MARK_END, dc.PARAPHRASES_CLOSE]
    return "\n".join(lines[:-1] + body + lines[-1:])


# ── Rewriting the two catalogue files ─────────────────────────────────────────

_UN_DOC_OLD = """The questions this database CANNOT answer, and why.

Thirty of them: the 17 rows the workbook marks "Answerable from DB = No", and
the 13 beneficiary questions on its Dropped sheet."""
_UN_DOC_NEW = """The questions this database CANNOT answer, and why.

Fifteen of them since WP-6f (2026-09-29): the questions with NO COLUMN anywhere
in the schema to answer them from (tiers above the GP, stage dates, suspension,
planned duration, resource envelopes, PAI grades, repair flags, beneficiary
villages / names / cash / purpose), and BEN-010, whose pension-scheme column has
no decode. There were thirty: the 17 rows the workbook marks "Answerable from DB
= No" and the 13 beneficiary questions on its Dropped sheet. Migration M7
(tools/migrations/m7_refusals_to_templates.py) moved the fifteen whose columns
exist — empty in the sample — or whose blocker was a missing definition into
template_catalog.py, keeping their ids, on the operator's ruling that production
holds the data. `handoffs/WP6f_prod_schema_needs.md` lists what each remaining
one would need."""


def rewrite_unanswerable(source: str) -> str:
    lines = source.split("\n")
    for qid, start, end in reversed(dc._entry_spans(lines)):
        if qid not in MOVED:
            continue
        stop = end + 1
        # the blank line that follows an entry goes with it
        if stop < len(lines) and not lines[stop].strip():
            stop += 1
        del lines[start:stop]
    out = "\n".join(lines)
    if _UN_DOC_OLD in out:
        out = out.replace(_UN_DOC_OLD, _UN_DOC_NEW)
    return out


def rewrite_templates(source: str, entries: dict[str, dict]) -> str:
    lines = source.split("\n")
    present = {qid for qid, _, _ in dc._entry_spans(lines)}
    close = lines.index("}", lines.index("TEMPLATE_CATALOG: dict[str, dict] = {"))
    block = []
    for qid in MOVED:
        if qid in present:
            continue
        block += ["", *_emit(qid, entries[qid]).split("\n")]
    lines[close:close] = block
    return "\n".join(lines)


# ── Proving and recording ─────────────────────────────────────────────────────

def execute_all(entries: dict[str, dict]) -> dict[str, dict]:
    """Run every new statement against the sample; the oracle lines to record."""
    from db_factory import open_analytical_db
    from query_router import template_catalog as tc
    from query_router.entity_validator import EntityValidator

    adapter = open_analytical_db(BACKEND / "data" / "panchayat_1.duckdb")
    validator = EntityValidator(adapter)
    oracle = {}
    injected = []
    try:
        for qid, entry in entries.items():
            if qid not in tc.TEMPLATE_CATALOG:
                tc.TEMPLATE_CATALOG[qid] = entry
                injected.append(qid)
            params = _absent(entry["param_slots"], **SPECS[qid]["params"])
            values = {}
            for name, value in params.items():
                slot = next(s for s in entry["param_slots"] if s["name"] == name)
                if value is not None and slot.get("bind") == "code":
                    value = validator.validate(str(value), name.replace("_name", "")) \
                        .resolved_code or value
                values[name] = value
            sql, bound = tc.bind(qid, values)
            rows = adapter.execute(sql, bound).fetchall()
            oracle[qid] = {"answerable": "Partial", "params": params,
                           "rows": len(rows), "status": "PASS"}
            shown = rows[0] if rows else "-"
            print(f"  {qid:<8} {len(rows):>3} row(s)   first: {str(shown)[:90]}")
    finally:
        for qid in injected:
            tc.TEMPLATE_CATALOG.pop(qid, None)
        adapter.close()
    return oracle


def applied() -> list[str]:
    """What is still to do; [] when M7 is fully applied."""
    todo = []
    templates = dc.load_catalog(dc.TEMPLATE_PATH.read_text(encoding="utf-8"),
                                "TEMPLATE_CATALOG")
    unanswerable = dc.load_catalog(dc.UNANSWERABLE_PATH.read_text(encoding="utf-8"),
                                   "UNANSWERABLE_CATALOG")
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))
    todo += [f"{q} still a refusal" for q in MOVED if q in unanswerable]
    todo += [f"{q} not a template" for q in MOVED if q not in templates]
    todo += [f"{q} not in the Test Report" for q in MOVED if q not in oracle]
    todo += [f"{q} is no longer a refusal" for q in STAYS if q not in unanswerable]
    return todo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 when the catalogue still needs M7")
    args = ap.parse_args()

    todo = applied()
    if args.check:
        if todo:
            print("M7 NOT applied: " + "; ".join(todo), file=sys.stderr)
            return 1
        print(f"M7 applied: {len(MOVED)} templates ({', '.join(MOVED)}); "
              f"{len(STAYS)} refusals stay")
        return 0
    if not todo:
        print("M7 already applied — nothing to do")
        return 0

    un_source = dc.UNANSWERABLE_PATH.read_text(encoding="utf-8")
    tpl_source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    unanswerable = dc.load_catalog(un_source, "UNANSWERABLE_CATALOG")
    missing = [q for q in MOVED if q not in unanswerable]
    if missing:
        print(f"REFUSED: not refusals any more, so not M7's to move: {missing}",
              file=sys.stderr)
        return 1
    entries = build_entries(unanswerable, un_source.split("\n"))

    # The contract derive_catalog enforces, before anything is written.
    problems = dc.contract_problems(entries)
    if problems:
        print("REFUSED — the new statements break the slot contract:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("Executing the new statements against the sample:")
    oracle_lines = execute_all(entries)

    new_tpl = rewrite_templates(tpl_source, entries)
    new_un = rewrite_unanswerable(un_source)
    after_tpl = dc.load_catalog(new_tpl, "TEMPLATE_CATALOG")
    after_un = dc.load_catalog(new_un, "UNANSWERABLE_CATALOG")
    before_tpl = dc.load_catalog(tpl_source, "TEMPLATE_CATALOG")
    before_un = unanswerable
    # Nothing else changes: every old template's SQL and every kept refusal.
    for qid, entry in before_tpl.items():
        if after_tpl[qid] != entry:
            print(f"REFUSED: {qid} would change", file=sys.stderr)
            return 1
    for qid in STAYS:
        if after_un.get(qid) != before_un[qid]:
            print(f"REFUSED: the refusal {qid} would change", file=sys.stderr)
            return 1
    if sorted(after_un) != sorted(STAYS) or set(after_tpl) - set(before_tpl) != set(MOVED):
        print("REFUSED: the two catalogues would not hold what M7 says", file=sys.stderr)
        return 1

    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))
    oracle.update(oracle_lines)
    dc.TEMPLATE_PATH.write_text(new_tpl, encoding="utf-8")
    dc.UNANSWERABLE_PATH.write_text(new_un, encoding="utf-8")
    dc.ORACLE_PATH.write_text(json.dumps(dict(sorted(oracle.items())), indent=1,
                                         ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"moved {len(MOVED)}; {len(after_un)} refusals remain; Test Report "
          f"+{len(oracle_lines)} — now run tools/derive_catalog.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

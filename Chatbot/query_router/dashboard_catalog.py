"""
Tier-1 dashboard queries — precomputed, parameter-free, served from dashboard_cache.

**PROPOSED, NOT RATIFIED. `DASHBOARD_CATALOG` is empty until an operator sets
`DASHBOARDS_RATIFIED = True`.** See "Why this ships switched off" below.

WHAT A DASHBOARD IS HERE
    The twenty-one questions below are the ones an officer opens a review meeting
    with: did the plans arrive, how much has been spent, how much of the plan
    that is, what is stuck awaiting approval, and where nothing has been recorded
    at all. They are precomputed at startup and served from cache, so the
    highest-frequency whole-of-sample questions cost no query time and no LLM
    parameter extraction.

    Every one is DERIVED FROM A SIGNED-OFF TEMPLATE, not authored here. The
    product's first design principle is that the ministry can audit a finite,
    validated query set; a dashboard whose SQL was written fresh in this file
    would be SQL nobody ratified, sitting in the one part of the catalogue that
    answers without any user input to qualify it. So `_state_wide()` takes the
    template's own statement and substitutes its parameters:

        $date_range  ->  the fiscal year literal below
        $top_n       ->  the default page size
        anything else -> NULL, which every optional geography filter reads as
                         "do not filter" — the D2 idiom, unchanged

    The result is the workbook's query at state scope. tests/test_dashboards.py
    executes each one and asserts it returns exactly what the source template
    returns when bound with the same values, so the substitution cannot drift
    into meaning something else.

WHY THIS SHIPS SWITCHED OFF
    Deriving the SQL mechanically makes the substitution safe; it does not make
    the SELECTION ratified. Which twenty-one questions deserve to be the ones
    answered instantly — and shown without anyone having asked — is a product
    judgement for the operator and the SME, not one an implementer should make
    silently. Flipping `DASHBOARDS_RATIFIED` is the whole activation.

    Everything downstream already handles an empty catalogue: startup.seed()
    writes zero rows, VectorRetriever indexes only the templates and the
    known-unanswerables, and `_serve_query_id`'s dashboard branch is never taken.

TWO THINGS THE OPERATOR SHOULD DECIDE WITH IT
    1. `DASHBOARD_FISCAL_YEAR`. A precomputed answer has to name its year, and
       nothing here can infer which year an officer means. It is pinned rather
       than computed: `MAX(fiscal_year)` would silently roll onto 2025-2026 the
       moment a handful of next-year rows land, and a dashboard that quietly
       changes which year it reports is worse than one that is a year stale.
    2. Whether a caveated question belongs on a dashboard at all. Sixteen of the
       twenty-one carry one, and a dashboard is exactly where a caveat is most
       likely to be read past. They are carried through to `QueryResponse.caveat`
       and appended to the answer text like any other, but a tile is not a
       sentence.
"""
from .template_catalog import TEMPLATE_CATALOG

# Flip to True once the operator has ratified the selection below.
DASHBOARDS_RATIFIED = False

# The year every precomputed answer reports. Must move with the data — see the
# module docstring for why it is not derived.
DASHBOARD_FISCAL_YEAR = "2024-2025"

# The page size for the ranking/listing dashboards.
DASHBOARD_TOP_N = 10


def _state_wide(template_id: str) -> str:
    """One signed-off template's SQL, bound state-wide, as a literal statement.

    Substitution is textual and total: every `$name` in the statement is replaced
    or the result would still be a parameterised query masquerading as a
    dashboard. A slot this function has no value for becomes NULL, which the
    catalogue's `($p IS NULL OR col = $p)` idiom reads as "no filter" — the same
    behaviour the router gets by binding None.
    """
    import re

    template = TEMPLATE_CATALOG[template_id]
    values = {
        "date_range": f"'{DASHBOARD_FISCAL_YEAR}'",
        "date_range_2": f"'{DASHBOARD_FISCAL_YEAR}'",
        "top_n": str(DASHBOARD_TOP_N),
    }
    slots = {s["name"] for s in template["param_slots"]}
    # Longest name first, so `$date_range` never eats the head of
    # `$date_range_2` and leaves a stray `_2` behind.
    sql = template["sql_template"]
    for name in sorted(slots, key=len, reverse=True):
        sql = re.sub(r"\$" + re.escape(name) + r"\b", values.get(name, "NULL"), sql)
    return sql.strip()


def _entry(template_id: str, question: str, *paraphrases: str) -> dict:
    template = TEMPLATE_CATALOG[template_id]
    return {
        "question": question,
        "sql": _state_wide(template_id),
        "caveat": template.get("caveat"),
        "source_template": template_id,
        "paraphrases": list(paraphrases),
    }


# The proposal. One or two per bracket, chosen for how often a review meeting
# asks them rather than for coverage of the catalogue.
PROPOSED_DASHBOARDS: dict[str, dict] = {
    # ── Planning: did the plans arrive, and from whom ────────────────────────
    "D01": _entry("PLN-001",
                  f"How many Gram Panchayats uploaded a GPDP in {DASHBOARD_FISCAL_YEAR}?",
                  "How many GPs have filed their plan this year?",
                  "GPDP upload count state-wide"),
    "D02": _entry("PLN-005",
                  f"Which Gram Panchayats have not uploaded a GPDP in {DASHBOARD_FISCAL_YEAR}?",
                  "Which GPs are missing their plan?",
                  "GPs with no GPDP filed"),
    "D03": _entry("PLN-004",
                  "What percentage of Gram Panchayats in each district uploaded their GPDP?",
                  "District-wise GPDP submission rate"),
    "D04": _entry("PLN-007",
                  "Which districts have the lowest GPDP submission rate?",
                  "Worst-performing districts on plan submission"),
    "D05": _entry("PLN-052",
                  "Which focus areas have the most planned activities?",
                  "What are GPs planning the most of?"),

    # ── Budget: where the money is meant to go ───────────────────────────────
    "D06": _entry("BUD-002",
                  "How much funding is recorded from each funding source?",
                  "Funding by source state-wide"),
    "D07": _entry("BUD-005",
                  "What percentage of the sanctioned budget is tied and untied?",
                  "Tied versus untied split"),
    "D08": _entry("BUD-006",
                  "How much planned expenditure is allocated to each GPDP theme?",
                  "Theme-wise budget allocation"),

    # ── Expenditure: what was actually spent ─────────────────────────────────
    "D09": _entry("EXP-003",
                  "What percentage of the planned expenditure has been utilised?",
                  "Overall utilisation rate",
                  "How much of the plan has been spent?"),
    "D10": _entry("EXP-004",
                  "What is the total unspent amount?",
                  "How much money is lying unspent?"),
    "D11": _entry("EXP-006",
                  "How much actual expenditure was incurred under each funding source?",
                  "Spend by funding source"),

    # ── Implementation: what is actually happening on the ground ─────────────
    "D12": _entry("STS-001",
                  "How many activities are in each work status?",
                  "Activity status breakdown",
                  "How many works are completed, ongoing or abandoned?"),
    "D13": _entry("IMP-005",
                  "What is the completion rate under each theme and focus area?",
                  "Completion rate by theme"),
    "D14": _entry("IMP-011",
                  "Which focus areas have the most ongoing activities?",
                  "Where is the most work in progress?"),

    # ── Sanctions: what is stuck ─────────────────────────────────────────────
    "D15": _entry("SAN-002",
                  "How many activities are still awaiting administrative approval?",
                  "Pending administrative approvals"),
    "D16": _entry("SAN-007",
                  "What percentage of planned activities have received administrative approval?",
                  "Administrative approval coverage"),

    # ── Assets and sanitation ────────────────────────────────────────────────
    "D17": _entry("AST-002",
                  "How many assets were created in each asset category?",
                  "Asset creation by category"),
    "D18": _entry("SBM-SI-006",
                  "How many Individual Household Latrines have been planned?",
                  "IHHL planning under SBM"),
    "D19": _entry("SBM-SWM-001",
                  "How many Solid Waste Management activities have been planned?",
                  "SWM activity count"),

    # ── Monitoring: where nothing was recorded at all ────────────────────────
    "D20": _entry("ALR-012",
                  f"Which Gram Panchayats recorded no activity in {DASHBOARD_FISCAL_YEAR}?",
                  "GPs with no activity at all",
                  "Which panchayats are silent this year?"),
    "D21": _entry("DQY-001",
                  "How many activities have no focus area recorded?",
                  "Undecoded focus-area count",
                  "Data-quality: missing focus area"),
}

DASHBOARD_CATALOG: dict[str, dict] = (
    PROPOSED_DASHBOARDS if DASHBOARDS_RATIFIED else {}
)

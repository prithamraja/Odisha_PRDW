"""
Derive the generated parts of the PR&DW catalogue from the catalogue itself.

    python tools/derive_catalog.py            # rewrite the derived parts in place
    python tools/derive_catalog.py --check    # report drift, write nothing

THE CATALOGUE FILE IS THE SOURCE OF TRUTH (WP-6 T0, operator decision of
2026-09-12). `query_router/template_catalog.py` and
`query_router/unanswerable_catalog.py` are edited by hand — SQL, slots, caveats,
hand-written paraphrases — and their git history is the audit trail the
ministry reads. Until WP-6 both were generated from `AI_Chatbot_Questions.xlsx`;
that workbook is archived in `handoffs/archive/` as the record of the
2026-08-13 sign-off, and nothing in the build or the gates reads it any more.
(`tools/import_workbook.py` can still turn it into a FRESH copy for comparison;
it refuses to write over the live files.)

WHAT THIS SCRIPT OWNS — the things that must be DERIVED from the statements,
because a hand-written copy drifts at the first edit:

    1. The derived block at the foot of every `paraphrases` list: the lines
       between the `# ── derived …` marker and `# ── end derived ──`. Lines
       ABOVE the marker are hand-owned and never touched; lines inside it are
       rewritten on every run.
    2. `grouped_geo` on each template — the geography its outermost GROUP BY
       reports one row per, read off the SQL (see `grouped_geo_slots`).
    3. `query_router/rerank_context.py`, whole — the reranker's "↳" family
       descriptions, built from the SQL (see `describe_family`).

WHAT IT REFUSES — the contracts a hand edit can break silently, checked before
anything is written and on every `--check`:

    * every `$name` in a statement has a slot, and every slot has a `$name`;
    * a slot is `optional` exactly when its statement carries the
      `$p IS NULL OR` guard (D2), unless it is a defaulted slot (D18.P1);
    * every slot's entity_type is the one `PARAM_ENTITY_TYPES` names;
    * every GP slot binds a code, never a name (D4/D10).

THE REGRESSION CONTRACT IS NOT HERE. Every statement, bound with the Test
Report's sample parameters (and any newer slot left absent), must still return
the row count in `tests/data/workbook_test_report.json`. `validate_catalog.py`
and `tests/test_catalog_execution.py` assert that, and neither ever depended on
the workbook — which is why the file can now be edited freely.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent

TEMPLATE_PATH = BACKEND / "query_router" / "template_catalog.py"
UNANSWERABLE_PATH = BACKEND / "query_router" / "unanswerable_catalog.py"
RERANK_OUT = BACKEND / "query_router" / "rerank_context.py"
ORACLE_PATH = BACKEND / "tests" / "data" / "workbook_test_report.json"


# ── Geography: the D10 predicate rewrite ──────────────────────────────────────
#
# The seven views expose `gp_lgd_code` on v_activity, v_plan and v_voucher, and
# NO block or district code anywhere (verified against the built views, not
# assumed). So:
#
#   GP        binds the resolved gp_lgd_code, and the predicate moves off the
#             name onto the code. Statewide there are ~6,800 GPs and names
#             repeat freely, so a name predicate would silently aggregate every
#             namesake into one answer.
#   BLOCK /   bind the registry-validated canonical NAME, because no view
#   DISTRICT  carries their codes. Safe for the pilot and reported as a
#             view-change request; see WP3_REPORT.
#
# `v_asset` is the one view that joins geography without carrying the code. Its
# 13 GP predicates resolve through the parent activity instead, which is exactly
# equivalent — v_asset is `activity_asset ⋈ v_activity ON activity_code`, every
# v_asset row's activity_code exists in v_activity, no activity_code is
# duplicated there, and none maps to two GPs. Replace this with the plain
# `v.gp_lgd_code = $gp_name` the day v_asset exposes the column.

VIEWS_WITH_GP_CODE = {"v_activity", "v_plan", "v_voucher", "v_approval", "gram_panchayat"}
VIEWS_WITHOUT_GP_CODE = {"v_asset", "v_progress"}

_SQL_KEYWORDS = {
    "WHERE", "GROUP", "ORDER", "ON", "LEFT", "JOIN", "LIMIT", "HAVING", "UNION",
    "SELECT", "CROSS", "INNER", "RIGHT", "FULL", "USING", "AS", "AND", "OR",
}


def mask_literals(sql: str) -> str:
    """Same-length blanking of string literals and line comments.

    Offsets still index the original, so a `$name` or a `gp_name` inside a
    literal is neither counted nor rewritten. The SBM bracket makes this matter:
    86 of its queries hold regexes like 'grey ?water' and 'e-?cart'.
    """
    out = re.sub(r"'(?:[^']|'')*'", lambda m: " " * len(m.group(0)), sql)
    return re.sub(r"--[^\n]*", lambda m: " " * len(m.group(0)), out)


# ── Which geography a statement reports ONE ROW PER ───────────────────────────
#
# Read at BUILD time and emitted as `grouped_geo`, so the runtime never parses
# SQL. The echo layer needs it to tell two readings of the same unbound slot
# apart: EXP-001 with no `$gp_name` reports one row PER GP ("…incurred by each
# GP…") while PLN-001 with no `$gp_name` reports a single count over all of them
# ("…across all GPs…"). Rendering both as "all GPs" describes the first one
# wrongly — see query_router/zones.py.

_GEO_COLUMNS = {
    "district_name": re.compile(r"\bdistrict_name\b", re.IGNORECASE),
    "block_name":    re.compile(r"\bblock_name\b", re.IGNORECASE),
    "gp_name":       re.compile(r"\bgp_(?:name|lgd_code)\b", re.IGNORECASE),
}


def _split_top_level(text: str) -> list[str]:
    """Comma-split at paren depth 0, so `SUM(a, b)` stays one item."""
    out: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(current))
            current = []
        else:
            current.append(ch)
    out.append("".join(current))
    return [piece.strip() for piece in out if piece.strip()]


def outer_select_and_group(sql: str) -> tuple[list[str], list[str]]:
    """(SELECT items, GROUP BY items) of the OUTERMOST statement.

    Depth-0 only: 145 of the geography templates carry a GROUP BY inside a
    subquery whose grain says nothing about the shape of the answer. Literals
    are masked first so a 'group by' inside an SBM regex cannot be read as a
    clause.
    """
    masked = mask_literals(sql)
    upper = masked.upper()
    depth = 0
    select_start = select_end = group_start = group_end = None
    for i, ch in enumerate(masked):
        if ch == "(":
            depth += 1
            continue
        if ch == ")":
            depth -= 1
            continue
        if depth != 0 or (i and (upper[i - 1].isalnum() or upper[i - 1] == "_")):
            continue
        if select_start is None and upper.startswith("SELECT", i):
            select_start = i + len("SELECT")
        elif select_start is not None and select_end is None and upper.startswith("FROM", i):
            select_end = i
        elif upper.startswith("GROUP BY", i):
            group_start = i + len("GROUP BY")
        elif (group_start is not None and group_end is None
              and re.match(r"(?:ORDER\s+BY|LIMIT|HAVING)\b", upper[i:])):
            group_end = i

    select = (_split_top_level(sql[select_start:select_end])
              if select_start is not None and select_end is not None else [])
    group = (_split_top_level(sql[group_start:group_end or len(sql)])
             if group_start is not None else [])
    return select, group


def grouped_geo_slots(sql: str, slots: list[dict]) -> list[str]:
    """The geography slots this statement returns one row per.

    A bare ordinal (`GROUP BY 1,2,3`, which is how 155 of these are written) is
    resolved against the SELECT list, because the ordinal alone says nothing.
    """
    names = {s["name"] for s in slots}
    select, group = outer_select_and_group(sql)
    if not group:
        return []
    expressions = []
    for item in group:
        if item.isdigit():
            index = int(item) - 1
            if 0 <= index < len(select):
                expressions.append(select[index])
        else:
            expressions.append(item)
    # WP-6 T3: a `$group_by` CASE groups by its ELSE branch when the slot is
    # absent, and by its `$group_by IS NULL` branch for a blanked finer column —
    # that is the reading grouped_geo describes. A chosen breakdown is resolved
    # at run time (query_router/breakdown.effective_grouped_geo).
    expressions = [_absent_branch(e) for e in expressions]
    joined = mask_literals(" , ".join(expressions))
    return [slot for slot, pattern in _GEO_COLUMNS.items()
            if slot in names and pattern.search(joined)]


def _absent_branch(expr: str) -> str:
    """What a `$group_by` expression groups by when the slot is ABSENT."""
    if "$group_by" not in expr:
        return expr
    m = (re.search(r"\bELSE\s+(.+?)(?:\s+--[^\n]*)?\s+END\b", expr, re.S)
         or re.search(r"\$group_by\s+IS\s+NULL\s+THEN\s+(.+?)\s+END\b", expr, re.S))
    return m.group(1) if m else ""


def alias_relations(sql: str) -> dict[str, str]:
    """{alias: relation} for every FROM/JOIN in the statement.

    Raises when one alias names two relations, which would make a rewrite
    ambiguous — better to stop the build than to guess which table a predicate
    sits on.
    """
    found: dict[str, str] = {}
    for m in re.finditer(r"\b(?:FROM|JOIN)\s+(\w+)\s+(?:AS\s+)?(\w+)\b",
                         mask_literals(sql), re.IGNORECASE):
        relation, alias = m.group(1), m.group(2)
        if alias.upper() in _SQL_KEYWORDS:
            continue
        if alias in found and found[alias] != relation:
            raise ValueError(
                f"alias {alias!r} names both {found[alias]!r} and {relation!r}"
            )
        found[alias] = relation
    return found


def _reflow(spacing: str, grew_by: int) -> str:
    """Give back `grew_by` of the pad spaces a longer column name just consumed.

    `spacing` is the whole `\\s*=\\s*` between column and parameter, e.g.
    `'       = '`; only the run BEFORE the `=` is padding.
    """
    pad = len(spacing) - len(spacing.lstrip(" "))
    return " " * max(1, pad - grew_by) + spacing.lstrip(" ")


def rewrite_geography(qid: str, sql: str) -> tuple[str, list[str]]:
    """Move every GP predicate off `gp_name` and onto the resolved LGD code.

    Returns (rewritten sql, notes). Block and district predicates are left
    exactly as the workbook wrote them.
    """
    aliases = alias_relations(sql)
    notes: list[str] = []
    masked = mask_literals(sql)

    # Collected first, applied right-to-left, so earlier offsets stay valid.
    edits: list[tuple[int, int, str]] = []

    # `v.gp_name IN ($gp_name, $gp_name_2)` — the GP-vs-GP comparison (TRD-010).
    for m in re.finditer(r"(\w+)\.gp_name(\s+IN\s*\(\s*)\$(\w+)(\s*,\s*)\$(\w+)(\s*\))",
                         masked, re.IGNORECASE):
        alias = m.group(1)
        relation = aliases.get(alias)
        if relation not in VIEWS_WITH_GP_CODE:
            raise ValueError(
                f"{qid}: GP list-predicate on {relation!r}, which has no gp_lgd_code"
            )
        edits.append((m.start(), m.end(),
                      f"{alias}.gp_lgd_code{m.group(2)}${m.group(3)}"
                      f"{m.group(4)}${m.group(5)}{m.group(6)}"))
        notes.append(f"{alias}.gp_name IN (…) -> {alias}.gp_lgd_code IN (…)")

    # `v.gp_name = $gp_name` — the 302-occurrence ordinary case.
    for m in re.finditer(r"(\w+)\.gp_name(\s*=\s*)\$(gp_name(?:_2)?)\b",
                         masked, re.IGNORECASE):
        if any(s <= m.start() < e for s, e, _ in edits):
            continue
        alias, spacing, param = m.group(1), m.group(2), m.group(3)
        relation = aliases.get(alias)
        if relation in VIEWS_WITH_GP_CODE:
            # The workbook pads these predicates so the `=` signs line up down
            # the WHERE clause. `gp_lgd_code` is four characters longer than
            # `gp_name`, so give four of the pad spaces back and the column
            # survives the rewrite.
            edits.append((m.start(), m.end(),
                          f"{alias}.gp_lgd_code{_reflow(spacing, 4)}${param}"))
        elif relation in VIEWS_WITHOUT_GP_CODE:
            # Equivalent, and the only form available until the view exposes the
            # column: select the parent activities of that GP, then filter this
            # view's rows to them.
            edits.append((
                m.start(), m.end(),
                f"{alias}.activity_code IN (SELECT activity_code FROM v_activity"
                f" WHERE gp_lgd_code = ${param})",
            ))
            notes.append(
                f"{relation} exposes no gp_lgd_code; the GP filter resolves "
                f"through v_activity on activity_code"
            )
        else:
            raise ValueError(
                f"{qid}: GP predicate on unknown relation {relation!r} (alias {alias!r})"
            )

    for start, end, replacement in sorted(edits, reverse=True):
        sql = sql[:start] + replacement + sql[end:]

    # Nothing may bind a GP by name after this point — the whole purpose.
    leftover = re.search(r"\w+\.gp_name\s*(?:=|\bIN\b)\s*\(?\s*\$", mask_literals(sql),
                         re.IGNORECASE)
    if leftover:
        raise ValueError(f"{qid}: a GP name predicate survived the rewrite")
    return sql, notes


# ── Slots ─────────────────────────────────────────────────────────────────────

# Workbook bind name -> entity type. Mirrors entity_validator.PARAM_ENTITY_TYPES,
# which a test asserts this agrees with; kept here so the build has no runtime
# import and the generated file can carry literal, auditable values.
PARAM_ENTITY_TYPES = {
    "date_range": "fiscal_year", "date_range_2": "fiscal_year_2",
    "district_name": "district", "block_name": "block", "block_name_2": "block_2",
    "gp_name": "gp", "gp_name_2": "gp_2",
    "focus_area": "focus_area", "theme": "theme",
    "scheme": "scheme", "scheme_2": "scheme_2", "status": "status",
    "plan_type": "plan_type", "tied_untied": "tied_untied",
    "group_by": "group_by",
    "asset_category": "asset_category", "asset_sub_category": "asset_subcategory",
    "activity_code": "activity_code", "top_n": "top_n",
    "threshold": "threshold", "amount_threshold": "amount_threshold",
    "deadline": "deadline",
}

# The slots that bind a resolved code rather than the text the user said.
CODE_BOUND = {"gp_name", "gp_name_2"}

# Slots that ship OPTIONAL WITH A DEFAULT regardless of what the SQL guard says
# (decision D18.P1). `$top_n` is the LIMIT on 91 of the 346 templates and no
# officer says "top 10" — it is a page size the system supplies. Generated as
# required, every ranking question stalls on a "how many rows?" clarification,
# which WP-4a §5.2 showed would cost the first eval run a large, uniform and
# entirely artificial accuracy loss.
#
# STRICTLY numeric-and-presentational, and the runtime asserts the same list:
# `query_router.router._DEFAULT_ENTITY_VALUES` must agree with these values
# (tests/test_param_binding.py pins it). A categorical slot or a threshold that
# changes the POPULATION under study — $threshold, $amount_threshold — must
# never appear here: guessing there silently answers a different question than
# the one asked (D18.P2; the 15 threshold-bearing templates clarify instead).
#
# The value is a string because ExtractedEntity carries strings and DuckDB casts
# at bind time, including inside LIMIT.
DEFAULTED_SLOTS = {"top_n": "10"}

# The other half of the D18 table: dimensions that are optional and must NEVER
# carry a default, each with its reason. `contract_problems` already refuses a
# default on anything outside DEFAULTED_SLOTS; this names the ones where the
# temptation is real, so the refusal has its reason written next to it.
# WP-6 T3: the only values a `$group_by` CASE may list (query_router/breakdown.py
# and entity_validator carry the same tuple; a test pins all three together).
GROUP_BY_VALUES = ("district", "block", "gp", "theme", "focus_area", "status",
                   "scheme", "plan_type", "fiscal_year", "total")

UNDEFAULTED_SLOTS = {
    # WP-6 T1. "How many activities are planned?" with no qualifier means BOTH
    # plan types; that is the signed-off Test Report count. Defaulting to Main
    # (the plan most questions are about) would silently drop the Supplementary
    # activities from every answer that did not ask for them.
    "plan_type": "absent means both plan types (Main and Supplementary)",
}

# {Token} in the question text -> the slot it stands for. `.format()` is called
# on abstract_question by suggestions._chip_for, so every placeholder must be a
# real slot name or a pre-filled chip raises KeyError.
QUESTION_TOKENS = {
    "Date_Range": "date_range", "Date_Range_2": "date_range_2",
    "District": "district_name", "Block": "block_name", "Block_2": "block_name_2",
    "GP_Name": "gp_name", "GP_Name_2": "gp_name_2",
    "Focus_Area": "focus_area", "Theme": "theme",
    "Scheme": "scheme", "Scheme_2": "scheme_2", "Status": "status",
    "Asset_Category": "asset_category", "Asset_Sub_Category": "asset_sub_category",
    "Activity_Code": "activity_code", "Threshold": "threshold",
    "Amount_Threshold": "amount_threshold", "Deadline": "deadline",
}


def is_optional(sql: str, param: str) -> bool:
    """True when the SQL itself says a missing value means "don't filter".

    The guard `$p IS NULL OR …` is the authority rather than the Parameter
    Registry's NULL-skips column, because the guard is what executes. The two
    disagree on 13 questions, every one of them a case where a normally-optional
    filter is that question's subject (SCH-006 asks which GPs planned nothing
    under a named scheme — without the scheme there is no question). The
    parenthesis is optional: TRD-012 writes the guard unbracketed.
    """
    return bool(re.search(r"\$" + re.escape(param) + r"\s+IS\s+NULL\s+OR",
                          mask_literals(sql), re.IGNORECASE))


# ── Question text and paraphrases ─────────────────────────────────────────────

# How each placeholder reads when a question is written out in prose for the
# embedding index. The retriever strips the braces from `abstract_question`
# anyway ({district_name} -> district_name), so paraphrases are written as plain
# words instead: that is the text an officer's own question has to match.
TOKEN_PROSE = {
    "Date_Range": "a given year", "Date_Range_2": "a second year",
    "District": "a given district", "Block": "a given block",
    "Block_2": "a second block", "GP_Name": "a given gram panchayat",
    "GP_Name_2": "a second gram panchayat", "Focus_Area": "a given focus area",
    "Theme": "a given LSDG theme", "Scheme": "a given scheme",
    "Scheme_2": "a second scheme", "Status": "a given status",
    "Asset_Category": "a given asset category",
    "Asset_Sub_Category": "a given asset sub-category",
    "Activity_Code": "a given activity", "Threshold": "a given threshold",
    "Amount_Threshold": "a given amount", "Deadline": "a given deadline",
    "Subject": "a given subject",
}

# Decision D2: one consolidated template answers at every geographic scope, so
# each scope has to be RETRIEVABLE. A template gets one paraphrase per tier it
# can actually filter on — the tier NOUN is what an officer's own wording shares
# with the index ("in Khordha district", "for Andhrua panchayat").
SCOPE_NOUN = {
    "district_name": "a given district",
    "block_name": "a given block",
    "gp_name": "a given gram panchayat",
}
SCOPE_SUFFIX = {
    "district_name": "for a given district",
    "block_name": "for a given block",
    "gp_name": "for a given gram panchayat (GP)",
}

# A run of geography placeholders and whatever joins them: '{District}/{Block}',
# '{District} or {Block}', '{GP_Name}'. Replaced as a unit, so a question that
# already names its scope reads naturally in each tier's variant instead of
# collecting all three.
_GEO_TOKENS = "District|Block|Block_2|GP_Name|GP_Name_2"
_GEO_RUN = re.compile(
    r"\{(?:" + _GEO_TOKENS + r")\}(?:\s*(?:/|,|\bor\b|\band\b)\s*"
    r"\{(?:" + _GEO_TOKENS + r")\})*"
)


def to_prose(question: str) -> str:
    """Every placeholder written out, for the embedding index."""
    return re.sub(
        r"\{([^}]*)\}",
        lambda m: TOKEN_PROSE.get(m.group(1), m.group(1).replace("_", " ").lower()),
        question or "",
    ).strip()


# ── Retrieval surface for the questions with no SQL ───────────────────────────
#
# A known-unanswerable row carries no parameterised SQL, so it has no
# {placeholders} and the workbook writes its parameters out as PROSE: "…under a
# given Scheme in a given GP Name during a given Plan Year?". That sentence is
# what gets embedded, and it does not retrieve. Measured (WP-4c T2c) against the
# gold question that is almost word-for-word its own:
#
#   BEN-001  "How many beneficiaries received benefits under Swachh Bharat
#             Mission in Andhrua during 2024-25?"   ->  rank 51 of 376
#
# outside the top-30 window, so the reranker never saw the entry and the
# documented refusal could not be reached at all. Same for BEN-003 (64) and
# PLN-022 (46). The cause is a plain asymmetry of index surface: a TEMPLATE
# carries 6.1 vectors on average — abstract question, example question with real
# values, one scope line per tier it can filter on (D2) — while the 13 Dropped
# rows carried exactly ONE, and that one is three-fifths filler. The Dropped
# sheet has no Parameterized or Example column to draw on, so the generator has
# to make the surface itself.
#
# IT STRIPS THE SCOPE, which is the same thing SCOPE_SUFFIX does for templates
# from the other direction: an officer names the place and the year, so the
# catalogue's copy of them adds nothing and dilutes the measure words that do the
# matching. Measured after: BEN-001 rank 1, BEN-003 rank 12, PLN-022 rank 0.
#
# A paraphrase can only ever RAISE the entry it belongs to — the retriever scores
# an entry as the MAX over its vectors — so this cannot cost any other row its
# place except by out-ranking it, which is the intended effect.

_GIVEN_PERIOD = re.compile(
    r"\s*\b(?:in|for|during|over)\s+a\s+given\s+"
    r"(?:Plan\s+Year|Date\s+Range|year)\b", re.I)
_GIVEN_GEO = re.compile(
    r"\s*\b(?:in|for|of|across|at)\s+a\s+given\s+"
    r"(?:District|Block(?:\s+2)?|GP\s+Name(?:\s+2)?)\b", re.I)


def scope_free_question(question: str) -> str | None:
    """The question with its geography and period prose removed, or None.

    None when nothing was removed — PLN-041 ("…over the last five years?") names
    no parameter, so there is no second shape of it to index.
    """
    stripped = _GIVEN_GEO.sub("", _GIVEN_PERIOD.sub("", question or ""))
    stripped = re.sub(r"\s{2,}", " ", stripped).strip().rstrip(" ,")
    if not stripped or stripped.lower() == (question or "").strip().lower():
        return None
    if not stripped.endswith(("?", ".")):
        stripped += "?"
    return stripped[0].upper() + stripped[1:]




# ── The CODE-MIXED retrieval surface (D31.5, WP-5 T4c) ────────────────────────
#
# WHAT WP-4c LEFT OPEN. Stripping the scope prose (above) moved BEN-001 from
# rank 51 to rank 4 against its own gold question and turned 0/3 replays into
# 3/3. It did nothing for BEN-003, which sat at 64 before and 64 after — because
# BEN-003's gold question is not English:
#
#   BEN-003 catalogue: "How many beneficiaries are recorded across GPs of a
#                       given Block under a given Scheme for a given Plan Year?"
#   BEN-003 gold:      "Bhubaneswar block ke GPs me kitne beneficiary hain
#                       2024-25 me?"
#
# WP-4c filed that as F2 and D28.2 gated F2 on SME ratification. D31.5 rules it
# back IN: code-mixed is not a deferred register — it retrieves at 100% for
# every ANSWERABLE question in the set — so a documented refusal that cannot be
# reached in it is an index gap, not a language gap.
#
# WHY A FRAME TABLE AND NOT A TRANSLATION. Nothing here translates. An officer
# typing code-mixed keeps the domain nouns in English — scheme, pension scheme,
# beneficiary, village, cash, purpose — and switches only the INTERROGATIVE
# FRAME around them: "kitne … hain?", "sabse zyada … kis … me?". So the rule
# rewrites the frame and leaves every content word exactly as the workbook wrote
# it. That is deterministic, inspectable in one table, and cannot invent a
# domain term the catalogue does not use.
#
# IT IS APPLIED TO THE SCOPE-FREE FORM, not the raw question, so the place and
# the year are already gone — which is right twice over: the officer states them
# in their own sentence, and "a given Block" has no code-mixed rendering worth
# indexing.
#
# SAFETY. A paraphrase can only ever RAISE the entry it belongs to (an entry
# scores as the MAX over its vectors), so the worst case is an entry that
# out-ranks another — which is the intended effect where it happens and is
# measured for all 30 entries by `refusal_recall.py`, not asserted by argument.

# (pattern, replacement) applied in order to a scope-free question. Every
# replacement keeps the ORIGINAL noun phrase, captured as \1.
_HINGLISH_FRAMES: tuple[tuple["re.Pattern[str]", str], ...] = (
    # "How many beneficiaries received benefits for each stated purpose?"
    (re.compile(r"^How many (.+?) received benefits(.*?)\??$", re.I),
     r"Kitne \1 ko benefit mila\2?"),
    # "How many beneficiaries are recorded under each pension scheme?"
    (re.compile(r"^How many (.+?) (?:are|is) recorded(.*?)\??$", re.I),
     r"Kitne \1 darj hain\2?"),
    # "How many beneficiary records are missing the village field?"
    (re.compile(r"^How many (.+?)\??$", re.I),
     r"Kitne \1 hain?"),
    # "What is the total cash benefit quantum distributed under a given Scheme?"
    (re.compile(r"^What is the total (.+?)\??$", re.I),
     r"Total \1 kitna hai?"),
    # "What is the village-wise count of beneficiaries under a given Scheme?"
    (re.compile(r"^What is the (.+?)\??$", re.I),
     r"\1 kya hai?"),
    # "Which scheme has the most recorded beneficiaries?"
    (re.compile(r"^Which (.+?) has the most (.+?)\??$", re.I),
     r"Sabse zyada \2 kis \1 me hain?"),
    # "Which GPs have no recorded beneficiaries under a given Scheme?"
    (re.compile(r"^Which (.+?) have no (.+?)\??$", re.I),
     r"Kin \1 me koi \2 nahi hai?"),
    (re.compile(r"^Which (.+?)\??$", re.I),
     r"Kaunse \1?"),
    # "List the beneficiaries of a given Scheme with village and benefit details."
    (re.compile(r"^List the (.+?)\.?\??$", re.I),
     r"\1 ki list dikhao"),
    # "Compare beneficiary counts under a given Scheme between …"
    (re.compile(r"^Compare (.+?)\.?\??$", re.I),
     r"\1 compare karo"),
    # "How has the beneficiary count under a given Scheme changed?"
    (re.compile(r"^How has (.+?) changed(.*?)\.?\??$", re.I),
     r"\1 me kya change aaya\2?"),
)

# Residual English function words the frames do not consume. Rewritten AFTER a
# frame matches, never on their own — a sentence that matched no frame is left
# alone rather than half-converted.
_HINGLISH_CONNECTIVES: tuple[tuple["re.Pattern[str]", str], ...] = (
    (re.compile(r"\bunder (?:a given|each) ", re.I), "har "),
    (re.compile(r"\bunder ", re.I), "ke under "),
    (re.compile(r"\bacross GPs\b", re.I), "GPs me"),
    (re.compile(r"\bfor each\b", re.I), "har"),
    (re.compile(r"\bof a given ", re.I), "ke "),
    (re.compile(r"\bwith ", re.I), "ke saath "),
    (re.compile(r"\bbetween ", re.I), "ke beech "),
    (re.compile(r"\ba given ", re.I), ""),
    (re.compile(r"\s{2,}"), " "),
)


def code_mixed_question(question: str) -> str | None:
    """A Hinglish rendering of one refusal question, or None.

    None when no frame matches — a sentence this table does not recognise gets
    no code-mixed line at all, rather than a half-converted one that would
    embed as neither register.
    """
    text = (question or "").strip()
    if not text:
        return None
    for pattern, replacement in _HINGLISH_FRAMES:
        rewritten, count = pattern.subn(replacement, text)
        if not count:
            continue
        for connective, into in _HINGLISH_CONNECTIVES:
            rewritten = connective.sub(into, rewritten)
        rewritten = re.sub(r"\s+([?.])", r"\1", rewritten).strip()
        rewritten = re.sub(r"\s{2,}", " ", rewritten)
        if not rewritten or rewritten.lower() == text.lower():
            return None
        return rewritten[0].upper() + rewritten[1:]
    return None



# ── The derived paraphrase block ──────────────────────────────────────────────
#
# A template's paraphrases have two owners. The HAND-OWNED lines came from the
# workbook's Example Question and Original Question columns — real phrasings an
# officer might type, which nothing in the SQL could reproduce — and are edited
# like any other authored text. The DERIVED lines are a function of the entry's
# own abstract question and slots, so they are rebuilt here on every run and a
# hand edit to the question or the slots carries through to the retrieval
# surface without anyone remembering to update it.
#
# Measured at the switch (WP-6 T0): for all 346 templates and all 30
# unanswerable entries, "hand lines + derive(entry, hand lines)" reproduces the
# workbook-built list exactly, in order. So the switch changed no embedded text
# and the retrieval index signature did not move.

# slot name -> the workbook token it was written as; the inverse of
# QUESTION_TOKENS. `_GEO_RUN` and `TOKEN_PROSE` both read token spelling.
SLOT_TOKEN = {slot: token for token, slot in QUESTION_TOKENS.items()}


def token_form(abstract: str) -> str:
    """'…in {district_name}…' -> '…in {District}…', the inverse of the old
    import's `to_abstract`, so the scope rules below read a question the way
    they always have."""
    return re.sub(r"\{(\w+)\}",
                  lambda m: "{" + SLOT_TOKEN.get(m.group(1), m.group(1)) + "}",
                  abstract or "")


# WP-6 T2: how each universal filter reads when appended to a question. ONE line
# per dimension per template, and only for a dimension the question does not
# already name — a universal slot is invisible to retrieval unless some line
# mentions it ("main GPDP totals" will not reach PLN-024 on the word "main"
# otherwise), and the retriever scores a template as the MAX over its vectors, so
# these can raise their own template and cannot crowd the window (brief §3).
# "Sector" is deliberately absent: the operator ruled it is not assumed to mean
# focus area (2026-09-12).
DIMENSION_SUFFIX = {
    "plan_type":   "in the main GPDP",
    "status":      "for ongoing activities",
    "focus_area":  "under a given focus area",
    "theme":       "under a given LSDG theme",
    "scheme":      "under a given scheme",
    "tied_untied": "funded from tied grants",
}


def derived_template_paraphrases(entry: dict, hand: list[str]) -> list[str]:
    """The derived lines for one template, deduplicated against the hand lines.

      * the abstract question written out in prose ("a given district");
      * one scope line per optional geography tier (D2), so one consolidated
        template is retrievable at district, block and GP phrasing;
      * one line per optional filter DIMENSION the question does not already
        name (WP-6 T2), from `DIMENSION_SUFFIX`.
    """
    abstract = entry["abstract_question"]
    seen = {to_prose(abstract).lower()} | {h.lower() for h in hand}
    out: list[str] = []

    def add(candidate: str) -> None:
        candidate = re.sub(r"\s+", " ", candidate or "").strip()
        if not candidate or candidate.lower() in seen:
            return
        seen.add(candidate.lower())
        out.append(candidate)

    source = token_form(abstract)
    add(to_prose(source))

    optional_geo = [s["name"] for s in entry["param_slots"]
                    if s.get("optional") and s["name"] in SCOPE_NOUN]
    if optional_geo:
        has_geo_run = bool(_GEO_RUN.search(source))
        for slot in optional_geo:
            if has_geo_run:
                # The question names its own scope — swap that run for this tier
                # so the variant reads as a real question rather than a list of
                # every tier at once.
                add(to_prose(_GEO_RUN.sub(SCOPE_NOUN[slot], source)))
            else:
                # A naturally state-wide question, which D2 says the same
                # template must also answer for one district / block / GP.
                add(f"{to_prose(source).rstrip('?. ')}, {SCOPE_SUFFIX[slot]}?")

    for slot in entry["param_slots"]:
        name = slot["name"]
        if (name in DIMENSION_SUFFIX and slot.get("optional")
                and "{" + name + "}" not in abstract):
            add(f"{to_prose(source).rstrip('?. ')}, {DIMENSION_SUFFIX[name]}?")
    return out


def derived_unanswerable_paraphrases(entry: dict, hand: list[str]) -> list[str]:
    """The derived lines for one refusal: the scope-free form (WP-4c), and for
    the Dropped beneficiary rows the code-mixed form (D31.5). See
    `scope_free_question` and `code_mixed_question` for what each measured."""
    question = entry["question"]
    scope_free = scope_free_question(question)
    candidates = [scope_free]
    if entry.get("source") == "Dropped":
        candidates.append(code_mixed_question(scope_free or question))
    taken = {h.strip().lower() for h in hand}
    out: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        key = candidate.strip().lower()
        if key == (question or "").strip().lower() or key in taken:
            continue
        taken.add(key)
        out.append(candidate.strip())
    return out


# ── Editing the catalogue files in place ──────────────────────────────────────
#
# The files are Python, edited by hand, so this never re-emits one wholesale —
# that would flatten any comment or formatting an editor added. It finds each
# entry by its opening line (`    'QID': {`) and its closing line (`    },`),
# and rewrites only the two regions it owns: the derived block inside
# `paraphrases`, and the `grouped_geo` list.

MARK_BEGIN = ("# ── derived by tools/derive_catalog.py: edit the question or the "
              "SQL, not these lines ──")
MARK_END = "# ── end derived ──"
_ITEM_PAD = " " * 12

_ENTRY_OPEN = re.compile(r"""^    ('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"): \{$""")
PARAPHRASES_OPEN, PARAPHRASES_CLOSE = '        "paraphrases": [', "        ],"
SLOTS_OPEN, SLOTS_CLOSE = '        "param_slots": [', "        ],"
GEO_OPEN, GEO_CLOSE = '        "grouped_geo": [', "],"


class CatalogFileError(ValueError):
    """The file is not in the shape this script can edit safely."""


def load_catalog(source: str, name: str) -> dict:
    """Execute a catalogue module's source and return its dict.

    Both catalogue modules have no top-level imports (`bind()` imports inside
    its body), so they execute standalone — and reading the dict back out of the
    exact text being written is the surest way for the derived parts to be about
    the entries that are actually there.
    """
    namespace: dict = {}
    exec(compile(source, f"<{name}>", "exec"), namespace)
    return namespace[name]


def _entry_spans(lines: list[str]) -> list[tuple[str, int, int]]:
    """[(qid, opening line, closing line)] for every entry, in file order."""
    spans = []
    i = 0
    while i < len(lines):
        m = _ENTRY_OPEN.match(lines[i])
        if m:
            qid = ast.literal_eval(m.group(1))
            j = i + 1
            while j < len(lines) and lines[j] != "    },":
                j += 1
            if j == len(lines):
                raise CatalogFileError(f"{qid}: the entry never closes with '    }},'")
            spans.append((qid, i, j))
            i = j
        i += 1
    return spans


def _find_block(lines, start, end, opener, closer, qid, *, required=True):
    """(opener line, closer line) of a list inside one entry, or None."""
    for k in range(start, end):
        if lines[k] == opener:
            for c in range(k + 1, end):
                if lines[c] == closer:
                    return k, c
            raise CatalogFileError(f"{qid}: {opener.strip()!r} never closes")
    if required:
        raise CatalogFileError(f"{qid}: no {opener.strip()!r} block — every entry "
                               f"needs one, even if it holds only the markers")
    return None


def _string_line(line: str, qid: str) -> str:
    stripped = line.strip()
    try:
        value = ast.literal_eval(stripped[:-1] if stripped.endswith(",") else stripped)
    except (ValueError, SyntaxError):
        value = None
    if not isinstance(value, str):
        raise CatalogFileError(
            f"{qid}: a paraphrase line must be ONE string literal per line, "
            f"got {stripped[:70]!r}")
    return value


def _split_paraphrase_body(body: list[str], qid: str) -> tuple[list[str], list[str]]:
    """(hand lines verbatim, hand values). The derived region is dropped.

    An entry with no markers at all — a freshly hand-written one — is all hand,
    and gets its derived block appended on the next run.
    """
    hand_lines: list[str] = []
    hand_values: list[str] = []
    in_derived = False
    for line in body:
        stripped = line.strip()
        if stripped.startswith("# ── derived"):
            in_derived = True
            continue
        if stripped.startswith("# ── end derived"):
            in_derived = False
            continue
        if in_derived:
            continue
        hand_lines.append(line)
        if stripped and not stripped.startswith("#"):
            hand_values.append(_string_line(line, qid))
    return hand_lines, hand_values


def paraphrase_block(hand_lines: list[str], derived: list[str]) -> list[str]:
    return ([*hand_lines, _ITEM_PAD + MARK_BEGIN]
            + [f"{_ITEM_PAD}{text!r}," for text in derived]
            + [_ITEM_PAD + MARK_END])


def _rewrite_grouped_geo(lines, start, end, qid, entry) -> int:
    """Make the entry's `grouped_geo` match its SQL. Returns the line delta."""
    want = grouped_geo_slots(entry["sql_template"], entry["param_slots"])
    new = ([GEO_OPEN] + [f"    {slot!r}," for slot in want] + [GEO_CLOSE]) if want else []
    found = _find_block(lines, start, end, GEO_OPEN, GEO_CLOSE, qid, required=False)
    if found:
        k, c = found
        lines[k:c + 1] = new
        return len(new) - (c - k + 1)
    if not new:
        return 0
    _, slots_close = _find_block(lines, start, end, SLOTS_OPEN, SLOTS_CLOSE, qid)
    lines[slots_close + 1:slots_close + 1] = new
    return len(new)


def rewrite_source(source: str, catalog: dict, derive, *, grouped_geo: bool) -> str:
    """The file with every entry's derived regions brought up to date."""
    lines = source.split("\n")
    # Bottom-up, so an edit never moves an entry not yet visited.
    for qid, start, end in reversed(_entry_spans(lines)):
        entry = catalog[qid]
        if grouped_geo:
            end += _rewrite_grouped_geo(lines, start, end, qid, entry)
        opened, closed = _find_block(lines, start, end,
                                     PARAPHRASES_OPEN, PARAPHRASES_CLOSE, qid)
        hand_lines, hand = _split_paraphrase_body(lines[opened + 1:closed], qid)
        lines[opened + 1:closed] = paraphrase_block(hand_lines, derive(entry, hand))
    return "\n".join(lines)


def adopt_markers(source: str, catalog: dict, derive) -> tuple[str, list[str]]:
    """Put the markers into a marker-less file, splitting each list at the point
    where "the lines above + derive(entry, lines above)" reproduces it exactly.

    Used once, by `tools/migrations/m0_mark_derived.py`, to convert the last
    workbook-built file; and by `tools/import_workbook.py` on a fresh import.
    Returns (source, ids that could not be split — left all-hand).
    """
    lines = source.split("\n")
    unsplit: list[str] = []
    for qid, start, end in reversed(_entry_spans(lines)):
        opened, closed = _find_block(lines, start, end,
                                     PARAPHRASES_OPEN, PARAPHRASES_CLOSE, qid)
        body = lines[opened + 1:closed]
        if any(line.strip().startswith("# ── derived") for line in body):
            continue
        values = [_string_line(line, qid) for line in body if line.strip()]
        split = next((i for i in range(len(values) + 1)
                      if values[:i] + derive(catalog[qid], values[:i]) == values),
                     None)
        if split is None:
            unsplit.append(qid)
            split = len(values)
        lines[opened + 1:closed] = paraphrase_block(body[:split], values[split:])
    return "\n".join(lines), unsplit


# ── Emitting Python ───────────────────────────────────────────────────────────

def py(value, indent: int = 0) -> str:
    """repr() with the quoting style the rest of the catalogue uses."""
    pad = " " * indent
    if isinstance(value, str):
        if "\n" in value:
            # SQL is emitted as a readable triple-quoted block rather than a
            # repr with \n escapes, so a reviewer can read it as SQL. That is
            # only safe while no statement contains a backslash or a triple
            # quote; assert rather than escape, so a future workbook that does
            # stops the build instead of emitting something subtly wrong.
            if "\\" in value or '"""' in value:
                raise ValueError("SQL contains a backslash or triple quote")
            return f'"""\n{value.strip()}\n"""'
        return repr(value)
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dict):
        inner = ", ".join(f"{k!r}: {py(v)}" for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = ",\n".join(f"{pad}    {py(v, indent + 4)}" for v in value)
        return "[\n" + lines + f",\n{pad}]"
    raise TypeError(type(value))


def emit_entry(qid: str, entry: dict) -> str:
    order = ["abstract_question", "date_filter", "date_kind", "sql_template",
             "param_slots", "grouped_geo", "result_ttl_seconds", "caveat",
             "bracket", "module", "submodule", "question_type", "answerable",
             "paraphrases", "notes"]
    lines = [f"    {qid!r}: {{"]
    for key in order:
        if key not in entry:
            continue
        value = entry[key]
        if key == "sql_template":
            lines.append(f'        "sql_template": {py(value)},')
        elif key == "param_slots":
            lines.append('        "param_slots": [')
            for slot in value:
                lines.append(f"            {py(slot)},")
            lines.append("        ],")
        elif key == "paraphrases":
            lines.append('        "paraphrases": [')
            for text_ in value:
                lines.append(f"            {text_!r},")
            lines.append("        ],")
        else:
            lines.append(f'        "{key}": {py(value)},')
    lines.append("    },")
    return "\n".join(lines)


# ── Family descriptions for the reranker ──────────────────────────────────────
#
# A FAMILY here is a maximal set of templates with IDENTICAL SQL and identical
# slots. That is the only grouping under which "siblings share one description
# word-for-word" is true rather than merely tidy: those members execute the same
# statement with the same binds, so which one the reranker picks cannot change
# the answer. There are 14 such groups covering 33 template ids — some are the
# workbook's own scope variants collapsed by D2's optional filters (PLN-025 "in
# {GP}" / PLN-027 "in {Block}" / PLN-029 "in {District}" are one query), and a
# few are duplicate questions.
#
# Everything else gets its OWN description, and that is deliberate. The AP lesson
# — "per-variant descriptions caused confusion, not precision" — is about
# PARAMETER variants, where `accepts filters:` already tells the model which
# sibling to take. It does not transfer here: SBM-SWM-002 (community compost
# pits) and SBM-SWM-007 (household compost pits) accept identical filters and
# differ only in a keyword regex frozen inside the SQL. Giving them one
# description would leave the reranker choosing between them blind.
#
# The descriptions are BUILT FROM THE SQL rather than hand-written prose,
# because what the reranker needs is exactly what the SQL says and the question
# text does not: the measure and its accounting basis, the row grain, the status
# filter, and — for the 85 SBM families — which keywords define the concept. A
# hand-written line would be a less accurate way of saying the same thing, and
# would drift from the SQL at the first edit.
# `_DISAMBIGUATION` carries the hand-authored half: the near-miss warnings no
# amount of SQL parsing can infer.

MEASURE_GLOSS = {
    "total_expenditure": "actual expenditure on the PLAN basis (activity_expenditure), "
                         "not the cashbook",
    "actual_expenditure": "actual expenditure on the PLAN basis (activity_expenditure), "
                          "not the cashbook",
    "expenditure": "actual expenditure on the PLAN basis (activity_expenditure), "
                   "not the cashbook",
    "planned_cost": "the planned cost the GP entered in the action plan",
    "approved_cost_action_plan": "the action-plan approved cost",
    "admin_approved_cost": "the administratively approved cost",
    "work_proposed_cost": "the cost proposed in the approval order",
    "tec_approval_cost": "the technically approved cost",
    "fund_sanctioned_total": "funds sanctioned under the approval's scheme components",
    "pct_utilised": "utilisation as a percentage of the approved cost",
    "amount": "CASHBOOK voucher amounts (cash basis), which is a different "
              "convention from the plan-basis expenditure most questions use",
}

STATUS_CLAUSES = [
    (r"\bis_completed\s*=\s*1", "counts only WORK COMPLETED"),
    (r"\bis_ongoing\s*=\s*1", "counts only WORK ONGOING"),
    (r"\bis_abandoned\s*=\s*1", "counts only WORK ABANDONED"),
    (r"\bis_under_approval\s*=\s*1", "counts only activities UNDER APPROVAL"),
    (r"\bis_started\s*=\s*0", "counts only activities NOT YET STARTED"),
    (r"\bis_admin_approved\s*=\s*1", "restricted to activities that HAVE an "
                                     "administrative approval (17% of them)"),
    (r"\bis_approved\s*=\s*1", "restricted to plans with an approval date"),
    (r"\bis_costless_activity\s*=\s*1", "restricted to zero-cost activities"),
    (r"\bhas_progress_evidence\s*=\s*1", "restricted to activities with geotagged "
                                         "progress evidence"),
    (r"COALESCE\(v\.total_expenditure,\s*0\)\s*=\s*0",
     "restricted to activities with NO expenditure recorded"),
    (r"tied_untied\s*=\s*'Tied'", "restricted to TIED grant funds"),
    (r"tied_untied\s*=\s*'Untied'", "restricted to UNTIED grant funds"),
]

# Hand-authored near-miss warnings, appended to the family a query_id belongs to.
# These are the distinctions the SQL cannot state about itself.
_DISAMBIGUATION: dict[str, str] = {
    "PLN-001": "UPLOADED a GPDP, which is any plan row — not the approved subset; "
               "the approval question is the neighbouring one.",
    "PLN-002": "APPROVED plans specifically. Because plan_code_status is entirely "
               "NULL, approval is proxied by an approval date, and every loaded "
               "plan has one, so this currently returns the same figure as the "
               "'uploaded' question — say so rather than presenting them as two "
               "different findings. 'Supplementary plans approved' is THIS with "
               "plan_type = Supplementary (approved = has approval_date); PLU-004 "
               "counts GPs that UPLOADED one.",
    # WP-6b T5. The Eval_1 replay's reranker losses: the right template was in
    # the window every time, and it was passed over for a sibling or declined.
    "PLU-004": "Counts GPs that UPLOADED a supplementary plan. 'Supplementary "
               "plans APPROVED' is PLN-002 with plan_type = Supplementary "
               "(approved = has approval_date).",
    "PLU-003": "A per-GP YES/NO lookup: does this GP have a supplementary plan. A "
               "COUNT of supplementary plans approved state-wide is PLN-002.",
    "PLN-031": "$theme is OPTIONAL since WP-6: 'which GP has the most planned "
               "activities' with no theme ANSWERS across all themes. Do not ask. A "
               "named focus area ('piped water') is a filter on this entry too.",
    "PLN-025": "Ranks THEMES within one place. 'Which GP has the most planned "
               "activities' ranks GRAM PANCHAYATS and is PLN-031.",
    "PLN-032": "'GPs with no allocation / no funds / nothing planned under the "
               "Sankalp themes' is THIS: the Sankalp themes are the LSDG themes, "
               "and with no theme named it answers across all of them. Do not ask.",
    "AST-001": "'District-wise / summary of asset creation' is THIS with the "
               "district breakdown, not AST-002 (category split in a block) or "
               "AST-003 (one sub-category).",
    "AST-002": "Splits assets by CATEGORY. A district-wise or overall summary of "
               "asset creation is AST-001.",
    "AST-003": "Counts ONE named asset sub-category. A district-wise summary of "
               "all asset creation is AST-001.",
    "TRD-003": "'Five-year time series / trend of fund utilisation' is THIS "
               "(expenditure against plan per year). EXP-003 and EXP-023 are ONE "
               "year's percentage.",
    "EXP-002": "'Five-year time series / trend of fund utilisation' is THIS or "
               "TRD-003 (expenditure against plan per year). EXP-003 and EXP-023 "
               "are ONE year's percentage.",
    "EXP-003": "ONE year's utilisation percentage. A multi-year TREND or time "
               "series of fund utilisation is TRD-003.",
    "EXP-023": "ONE year's utilisation percentage. A multi-year TREND or time "
               "series of fund utilisation is TRD-003.",
    "PLN-072": "A judgement of whether the spread across themes is BALANCED. A "
               "plain 'breakdown / distribution of planned activities by theme' "
               "is PLN-024.",
    "SCH-003": "The estimated cost under a NAMED SCHEME. A plain state-wide total "
               "estimated cost with no scheme named is BUD-006 with the total "
               "breakdown.",
    "BUD-001": "Funding RECORDED against each GP, one row per GP. The total "
               "estimated (planned) cost of planned activities is BUD-006.",
    "TRD-002": "Compares TWO DIFFERENT named years side by side. Tied-fund "
               "spending on water vs sanitation within one period is EXP-009.",
    "TRD-008": "Approved cost AND expenditure per focus area. 'Tied-fund "
               "expenditure, water vs sanitation' is EXP-009, which reports tied "
               "spend per focus area.",
    "IMP-002": "'How many activities have been completed' — state-wide, across "
               "the state or 'for all districts' — is THIS (or STS-003 with status "
               "= WORK COMPLETED). STS-013 is a per-district table of EVERY status; "
               "STS-001 splits activities across all statuses.",
    "STS-013": "A per-DISTRICT table of every status. A single count of completed "
               "activities, state-wide or 'for all districts', is IMP-002.",
    "STS-001": "Splits activities across ALL statuses. A count of ONE status "
               "(completed, ongoing) is STS-003 or IMP-002.",
    "PLU-008": "'Which GPs planned zero-cost / no-cost / cost-free activities' is "
               "THIS with the GP breakdown; DQY-007 lists the individual "
               "activities.",
    "PLN-005": "The GPs that filed NOTHING — an absence, listed from the roster by "
               "LEFT JOIN, so a GP with no plan still appears. That is the finding "
               "a review meeting wants and the opposite of the counting questions.",
    "EXP-001": "TOTAL SPEND on the plan basis. The cashbook questions read "
               "v_voucher and answer a different accounting convention; never "
               "substitute one for the other.",
    "TRD-010": "A two-GP head-to-head. Both GPs must be named; a question about one "
               "GP alone belongs to an ordinary GP-filtered family.",
    "TRD-011": "A two-BLOCK head-to-head. Both blocks must be named.",
    "TRD-012": "One district read against the STATE benchmark. Every district is "
               "returned so the chosen one can be seen in context — the district "
               "filter deliberately does not narrow the table.",
    "DQY-001": "A DATA-QUALITY check on how much of the data decodes at all, not a "
               "programme measure. Do not answer a coverage or spend question with it.",
    # WP-6 T2. With universal filters many templates accept the same filters,
    # so the "accepts filters:" line stops telling siblings apart; these two say
    # what the filters are FOR.
    "PLN-024": "PLAN TYPE is a filter on ACTIVITIES, not on plans: 'activities in "
               "the main GPDP' is this entry with plan_type bound, not a plan-count "
               "question. 'The total number of activities planned (in the main "
               "GPDPs)' is THIS with the total breakdown, and a 'breakdown / "
               "distribution of planned activities by theme' is THIS as it stands.",
    "BUD-006": "PLAN TYPE is a filter on ACTIVITIES, not on plans: 'planned cost of "
               "the main GPDPs' is this entry with plan_type bound. 'The total "
               "estimated cost / budget outlay of all planned activities, "
               "state-wide' is THIS with the total breakdown: planned_cost IS the "
               "estimated cost.",
    "STS-003": "A COUNT of activities by status, filterable by FOCUS AREA. 'How "
               "many completed sanitation activities' / 'Swachh Bharat' with a "
               "status word is THIS with focus_area = Sanitation — not an SBM item "
               "entry, which counts one keyword-defined item type (soak pits, "
               "toilets). \"Road works in progress\" and \"ongoing activities in "
               "this block\" are this entry too.",
    "PLN-052": "A RANKING ACROSS focus areas — which one has the most. A COUNT for "
               "one named focus area (\"how many activities under sanitation\") is "
               "PLN-049, not this.",
    "PLN-049": "FOCUS AREA is a filter. 'Sector' is NOT assumed to mean focus area "
               "(operator ruling 2026-09-12): a named value such as 'sanitation "
               "sector' is a focus area, but 'which sector…' is asked about.",
}


def _select_columns(sql: str) -> list[str]:
    """The output column names of the outermost SELECT."""
    body = mask_literals(sql)
    # Skip a leading CTE so the reported columns are the ones the user sees.
    tail = body
    if re.match(r"\s*WITH\b", body, re.IGNORECASE):
        depth = 0
        for i, ch in enumerate(body):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and body[i:i + 7].upper() == "SELECT " and i > 4:
                tail = body[i:]
                break
    m = re.search(r"\bSELECT\b(.*?)\bFROM\b", tail, re.S | re.IGNORECASE)
    if not m:
        return []
    depth, current, parts = 0, "", []
    for ch in m.group(1):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)

    names = []
    for part in parts:
        part = " ".join(part.split())
        if not part:
            continue
        alias = re.search(r"\bAS\s+(\w+)\s*$", part, re.IGNORECASE)
        names.append(alias.group(1) if alias else part.split(".")[-1])
    return names


GEO_COLUMNS = {"gp_name", "block_name", "district_name", "gp_lgd_code",
               "state_name", "activity_code", "plan_code", "fiscal_year", "item",
               "group_label"}   # WP-6 T3: the breakdown label, not a measure

# slot name -> how it reads in prose, the inverse of QUESTION_TOKENS.
SLOT_PROSE = {slot: TOKEN_PROSE[token] for token, slot in QUESTION_TOKENS.items()}


def describe_family(entry: dict, member_ids: list[str]) -> str:
    """One line saying what this family's answer actually is."""
    sql = entry["sql_template"]
    masked = mask_literals(sql)
    columns = _select_columns(sql)
    measures = [c for c in columns if c not in GEO_COLUMNS]

    kind = {
        "Count": "COUNTS", "Aggregation": "TOTALS", "Ranking": "RANKS",
        "Listing": "LISTS", "Rate/Percentage": "The PERCENTAGE for",
        "Trend": "The YEAR-BY-YEAR trend of", "Comparison": "COMPARES",
        "Status Lookup": "LOOKS UP", "Lookup": "LOOKS UP",
    }.get(entry["question_type"], "Reports")

    # Placeholders are written OUT rather than deleted: dropping {district_name}
    # from "…in {district_name}/{block_name} have uploaded…" leaves "…in/ have
    # uploaded…", which reads as damage rather than as a description.
    subject = re.sub(
        r"\{(\w+)\}",
        lambda m: SLOT_PROSE.get(m.group(1), m.group(1).replace("_", " ")),
        entry["abstract_question"],
    )
    subject = re.sub(r"\s+", " ", subject).strip(" ?.,")
    parts = [f"{kind}: {subject}."]

    # A pure listing has no measure columns at all (PLN-005 returns three place
    # names); say what it lists rather than saying nothing.
    shown = measures or columns
    if shown:
        parts.append("Returns " + ", ".join(shown[:6]) + ".")

    grain = re.search(r"\bGROUP BY\b([^\n]*)", masked, re.IGNORECASE)
    group_cols = [c for c in columns[:3] if c in GEO_COLUMNS or c in
                  ("theme", "focus_area_name", "status_label", "work_type_label",
                   "asset_category_label", "funding_source", "sanction_authority")]
    if "$group_by" in masked:
        # WP-6 T3: the grain is the statement's own unless a breakdown is asked
        # for. Read off the CASE's absent branch, which is what runs by default.
        default = re.search(r"--\s*absent:\s*(\w+)", sql)
        finer = re.findall(r"\$group_by\s+IS\s+NULL\s+THEN\s+\S+\s+END\s+AS\s+(\w+)",
                           sql)
        if default:
            parts.append("One row per " + " × ".join([default.group(1), *finer])
                         + " by default; other breakdowns on request.")
        else:
            parts.append("A single summary row by default; breakdowns on request.")
    elif grain and group_cols:
        parts.append("One row per " + " × ".join(group_cols) + ".")
    elif not grain and entry["question_type"] in ("Count", "Aggregation",
                                                  "Rate/Percentage"):
        parts.append("A single summary row.")
    elif not grain:
        parts.append("One row per matching record.")

    order = re.search(r"\bORDER BY\b[^\n]*?\b(ASC|DESC)\b", masked, re.IGNORECASE)
    if "LIMIT $top_n" in masked:
        direction = "lowest first" if (order and order.group(1).upper() == "ASC") \
            else "highest first"
        parts.append(f"A top-N list, {direction}; $top_n = 1 answers "
                     f"'which is the single highest/lowest'.")

    concept = re.search(r"regexp_matches\(\s*v\.search_text\s*,\s*'([^']*)'", sql)
    if concept:
        # The pattern is quoted VERBATIM rather than split into a word list:
        # several of these use alternation inside groups
        # ('(compost).*(community|group|cluster)'), and splitting on the pipe
        # turns a precise rule into a misleading one.
        parts.append(
            f"Identifies the activity by KEYWORD MATCH on activity_name + "
            f"activity_desc against the pattern /{concept.group(1)}/. Nothing in "
            f"the database codes SBM activity types, so this is a text search: "
            f"it both misses differently-worded activities and picks up "
            f"unrelated ones."
        )
        if any(qid.startswith("SBM-") for qid in member_ids):
            # WP-6b T5: seven Swachh Bharat questions lost STS-003 to these.
            parts.append("Counts ONE item type by keyword. A question about "
                         "sanitation activities in general, or a status count, "
                         "is STS-003.")

    for pattern, clause in STATUS_CLAUSES:
        if re.search(pattern, masked, re.IGNORECASE):
            parts.append(clause.capitalize() + ".")

    # The bootstrap's load-bearing shape: a question answered FROM THE ROSTER, so
    # that a GP with nothing to show still appears. "Which GPs planned nothing
    # under this theme" cannot be answered by any query over v_activity alone —
    # the rows it wants do not exist there — and an activity-side near neighbour
    # would silently answer a different question.
    if re.search(r"\bFROM\s+gram_panchayat\b", masked, re.IGNORECASE):
        if re.search(r"\bNOT\s+EXISTS\b", masked, re.IGNORECASE):
            parts.append(
                "An ABSENCE, read from the GP ROSTER: the Gram Panchayats with no "
                "matching record at all. A query over the activity table alone can "
                "never return these rows, because the rows it would need do not "
                "exist there."
            )
        elif re.search(r"\bLEFT\s+JOIN\b", masked, re.IGNORECASE):
            parts.append(
                "Counted FROM THE GP ROSTER by LEFT JOIN, so panchayats with zero "
                "activity are still in the denominator and still appear — which is "
                "the finding a review meeting is looking for."
            )

    for measure in measures:
        gloss = MEASURE_GLOSS.get(measure)
        if gloss:
            parts.append(f"{measure} is {gloss}.")
            break

    if re.search(r"\bv_voucher\b", masked):
        parts.append("Reads the CASHBOOK (v_voucher) — cash basis, a different "
                     "convention from the plan-basis expenditure questions.")

    geo = [s["name"] for s in entry["param_slots"]
           if s.get("optional") and s["name"] in SCOPE_NOUN]
    if geo:
        tiers = ", ".join(n.replace("_name", "").replace("gp", "GP") for n in geo)
        parts.append(f"Filterable by {tiers}; answers state-wide when no place is "
                     f"named — one entry serves every scope.")

    for qid in member_ids:
        if qid in _DISAMBIGUATION:
            parts.append(_DISAMBIGUATION[qid])
            break

    caveat = (entry.get("caveat") or "").strip()
    if caveat:
        first = re.split(r"(?<=[.;])\s", caveat)[0]
        parts.append("Caveat: " + first.rstrip(".") + ".")

    return " ".join(" ".join(p.split()) for p in parts)


RERANK_HEADER = '''"""
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
    Descriptions are BUILT FROM THE SQL by tools/derive_catalog.py, because what
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
    and would drift from the SQL at the first edit. The hand-authored
    half is `_DISAMBIGUATION` in the builder: the near-miss warnings no amount of
    SQL parsing can infer ("uploaded a GPDP is any plan row, not the approved
    subset").

CONTRACT (mirrors _RERANK_SYS in reranker.py — do not break it)
    - ONE line, no newlines: the candidate listing is line-oriented.
    - Every template has a non-empty description, and no template appears in two
      families. tests/test_rerank_context.py enforces both.
"""
'''


RERANK_BANNER = '''# ── GENERATED FILE — do not edit by hand ─────────────────────────────────────
# Built from query_router/template_catalog.py by tools/derive_catalog.py.
# To change a description, change the template's SQL or question (or the
# hand-authored `_DISAMBIGUATION` notes in the script) and re-run it;
# `python tools/derive_catalog.py --check` fails if this file has drifted.
'''


def build_rerank_context(templates_src: str) -> tuple[str, int]:
    """rerank_context.py, from the template catalogue's own source."""
    catalog = load_catalog(templates_src, "TEMPLATE_CATALOG")

    families: dict[tuple, list[str]] = defaultdict(list)
    for qid, entry in catalog.items():
        key = (" ".join(entry["sql_template"].split()),
               tuple((s["name"], s.get("optional", False))
                     for s in entry["param_slots"]))
        families[key].append(qid)

    blocks = []
    for members in sorted(families.values(), key=lambda m: sorted(m)[0]):
        members = sorted(members)
        entry = catalog[members[0]]
        name = _family_name(members, entry)
        desc = describe_family(entry, members)
        assert "\n" not in desc
        blocks.append(
            f"    {name!r}: {{\n"
            f"        \"desc\": {desc!r},\n"
            f"        \"members\": {members!r},\n"
            f"    }},"
        )

    body = (
        RERANK_HEADER
        + RERANK_BANNER
        + "\n\nFAMILY_DESCRIPTIONS: dict[str, dict] = {\n\n"
        + "\n\n".join(blocks)
        + "\n}\n\n"
        + '''
# query_id -> family description, expanded from the members lists above.
DESC_BY_QID: dict[str, str] = {
    qid: family["desc"]
    for family in FAMILY_DESCRIPTIONS.values()
    for qid in family["members"]
}
'''
    )
    return body, len(families)


def _family_name(members: list[str], entry: dict) -> str:
    """A readable key: the lead id plus a slug of the submodule."""
    slug = re.sub(r"[^a-z0-9]+", "_", entry["submodule"].lower()).strip("_")
    return f"{members[0].lower().replace('-', '_')}__{slug}"


# ── The contracts a hand edit can break ───────────────────────────────────────

def contract_problems(catalog: dict) -> list[str]:
    """Everything wrong with the slot declarations, one line each."""
    problems: list[str] = []
    for qid, entry in catalog.items():
        sql = entry["sql_template"]
        declared = [s["name"] for s in entry["param_slots"]]
        in_sql = set(re.findall(r"\$(\w+)", mask_literals(sql)))
        if set(declared) != in_sql:
            problems.append(f"{qid}: slots {sorted(set(declared))} but the SQL "
                            f"binds {sorted(in_sql)}")
        if len(declared) != len(set(declared)):
            problems.append(f"{qid}: a slot is declared twice")
        for slot in entry["param_slots"]:
            name = slot["name"]
            if slot.get("entity_type") != PARAM_ENTITY_TYPES.get(name):
                problems.append(
                    f"{qid} ${name}: entity_type {slot.get('entity_type')!r}, "
                    f"PARAM_ENTITY_TYPES says {PARAM_ENTITY_TYPES.get(name)!r}")
            if name == "group_by":
                # WP-6 T3. Optional through its CASE's ELSE (the statement's own
                # breakdown), not through a `$p IS NULL OR` guard, and only ever
                # one of the whitelisted values.
                case = re.search(r"CASE\s+\$group_by\b(.*?)\bEND\s+AS\s+group_label",
                                 sql, re.S)
                if not slot.get("optional") or "default" in slot:
                    problems.append(f"{qid} $group_by: must be optional with no "
                                    f"default — absent means the statement's own "
                                    f"breakdown")
                if not case or not re.search(r"\bELSE\b", mask_literals(case.group(1))):
                    problems.append(f"{qid} $group_by: needs `CASE $group_by … ELSE … "
                                    f"END AS group_label`")
                else:
                    stray = set(re.findall(r"WHEN\s+'(\w+)'", case.group(1))) \
                        - set(GROUP_BY_VALUES)
                    if stray:
                        problems.append(f"{qid} $group_by: {sorted(stray)} is outside "
                                        f"the breakdown whitelist")
                continue
            if name in DEFAULTED_SLOTS:
                if not slot.get("optional") or slot.get("default") != DEFAULTED_SLOTS[name]:
                    problems.append(f"{qid} ${name}: must be optional with default "
                                    f"{DEFAULTED_SLOTS[name]!r} (D18.P1)")
            else:
                guarded = is_optional(sql, name)
                if bool(slot.get("optional")) != guarded:
                    problems.append(
                        f"{qid} ${name}: optional={bool(slot.get('optional'))} but the "
                        f"SQL {'has' if guarded else 'has no'} `${name} IS NULL OR` guard "
                        f"— the guard is what executes, so the two must agree (D2)")
                if "default" in slot:
                    problems.append(f"{qid} ${name}: only {sorted(DEFAULTED_SLOTS)} may "
                                    f"carry a default (D18.P1/P2)")
            # WP-6 T4: a list-capable slot filters with IN (SELECT UNNEST($slot))
            # and nothing else; a scalar slot never does. The flag is what the
            # binders read, so the two must agree — or a bare scalar reaches a
            # list filter (a binder error) and a list reaches an equality (a
            # silently empty answer).
            unnest = f"UNNEST(${name})" in sql
            equality = bool(re.search(r"=\s*\$" + re.escape(name) + r"\b",
                                      mask_literals(sql)))
            if slot.get("list") and (not unnest or equality):
                problems.append(
                    f"{qid} ${name}: marked list but the SQL "
                    + ("still compares it with =" if equality else "has no UNNEST"))
            if not slot.get("list") and unnest:
                problems.append(f"{qid} ${name}: filters with UNNEST but carries "
                                f"no list flag")
            if name in CODE_BOUND and slot.get("bind") != "code":
                problems.append(f"{qid} ${name}: a GP slot must bind a code (D4/D10)")
    return problems


# ── Main ──────────────────────────────────────────────────────────────────────

def derive_all() -> tuple[dict[Path, str], dict, dict, int]:
    """(new text per output file, templates, unanswerable, family count)."""
    template_src = TEMPLATE_PATH.read_text(encoding="utf-8")
    unanswerable_src = UNANSWERABLE_PATH.read_text(encoding="utf-8")
    templates = load_catalog(template_src, "TEMPLATE_CATALOG")
    unanswerable = load_catalog(unanswerable_src, "UNANSWERABLE_CATALOG")

    new_templates = rewrite_source(template_src, templates,
                                   derived_template_paraphrases, grouped_geo=True)
    new_unanswerable = rewrite_source(unanswerable_src, unanswerable,
                                      derived_unanswerable_paraphrases,
                                      grouped_geo=False)
    rerank_src, n_families = build_rerank_context(new_templates)
    outputs = {
        TEMPLATE_PATH: new_templates,
        UNANSWERABLE_PATH: new_unanswerable,
        RERANK_OUT: rerank_src,
    }
    return outputs, templates, unanswerable, n_families


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="report drift and contract breaks; write nothing")
    args = ap.parse_args()

    outputs, templates, unanswerable, n_families = derive_all()
    print(f"templates: {len(templates)}   unanswerable: {len(unanswerable)}   "
          f"reranker families: {n_families}")

    problems = contract_problems(templates)
    if problems:
        print(f"\nCONTRACT BROKEN — {len(problems)} slot declaration(s) disagree "
              f"with their SQL; nothing written:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1

    drifted = [path for path, source in outputs.items()
               if not path.exists() or path.read_text(encoding="utf-8") != source]

    if args.check:
        if drifted:
            print("\nDRIFT — these do not match what the catalogue derives; run "
                  "`python tools/derive_catalog.py`:", file=sys.stderr)
            for path in drifted:
                print(f"  {path.relative_to(BACKEND)}", file=sys.stderr)
            return 1
        print("\nderived artefacts in step with the catalogue")
        return 0

    for path in drifted:
        path.write_text(outputs[path], encoding="utf-8")
        print(f"wrote {path.relative_to(BACKEND)}  ({len(outputs[path]):,} bytes)")
    if not drifted:
        print("nothing to rewrite — already in step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

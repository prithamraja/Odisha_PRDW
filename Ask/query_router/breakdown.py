"""The breakdown slot, `$group_by`, at run time (WP-6 T3) — and the one word
officers use for a breakdown that is NOT assumed: "sector".

WHAT `$group_by` IS. Migration M2 wrote a CASE over a fixed whitelist into every
single-aggregate statement:

    CASE $group_by
      WHEN 'district' THEN v.district_name   …   WHEN 'total' THEN 'All'
      ELSE <the statement's own breakdown>          -- absent: theme
    END AS group_label

so choosing a breakdown is BINDING A VALUE, never editing SQL. Absent, the ELSE
gives back exactly the signed-off statement.

WHY A READER AND NOT THE EXTRACTOR. The value comes from a short phrase table
("district-wise", "by block", "per theme", "for each focus area", "year-wise",
"across districts"), read deterministically before the extractor is called —
the same promotion WP-5 gave `$date_range`. A breakdown is structure, not an
entity: there is nothing in the database to validate it against, and a model
guessing one would silently regroup a correct answer. No match, no slot: the
statement's own breakdown stands.

WHAT THE OFFICER SEES. `group_label` is renamed back to the column it holds —
`theme` when nothing was chosen, `district_name` when "district-wise" was — so
the table reads as before and the operations layer types the column by its real
name. A chosen breakdown blanks a geography template's finer columns
(`CASE WHEN $group_by IS NULL THEN v.block_name END`); those are dropped from
the rows rather than shown empty. The echo says which breakdown ran.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache

_log = logging.getLogger(__name__)

GROUP_BY_VALUES = ("district", "block", "gp", "theme", "focus_area", "status",
                   "scheme", "plan_type", "fiscal_year", "total")

# value -> (the column the CASE selects, how it reads in an answer)
DIMENSIONS = {
    "district":    ("district_name",   "district"),
    "block":       ("block_name",      "block"),
    "gp":          ("gp_name",         "gram panchayat"),
    "theme":       ("theme",           "LSDG theme"),
    "focus_area":  ("focus_area_name", "focus area"),
    "status":      ("status_label",    "work status"),
    "scheme":      ("scheme_name",     "scheme"),
    "plan_type":   ("plan_type",       "plan type"),
    "fiscal_year": ("fiscal_year",     "year"),
}
GEO_SLOT_FOR = {"district": "district_name", "block": "block_name", "gp": "gp_name"}


# ── The phrase table ──────────────────────────────────────────────────────────
#
# (the stem "-wise"/"-level"/"breakdown" attach to, the noun in either number,
#  the plural alone — for "which districts …")
_NOUNS = {
    "district":    (r"district", r"districts?", r"districts"),
    "block":       (r"block", r"blocks?", r"blocks"),
    "gp":          (r"(?:gp|panchayat|gram[- ]panchayat)",
                    r"(?:gps?|gram[- ]panchayats?|panchayats?)",
                    r"(?:gps|gram[- ]panchayats|panchayats)"),
    "theme":       (r"theme", r"(?:lsdg |gpdp |sankalp )?themes?",
                    r"(?:lsdg |gpdp |sankalp )?themes"),
    "focus_area":  (r"focus[- ]area", r"focus[- ]areas?", r"focus[- ]areas"),
    "status":      (r"status", r"(?:work )?status(?:es)?", r"statuses"),
    "scheme":      (r"scheme", r"(?:schemes?|funding sources?)", r"schemes"),
    "plan_type":   (r"plan[- ]type", r"plan[- ]types?", r"plan[- ]types"),
    "fiscal_year": (r"year", r"(?:fiscal |financial |plan )?years?", r"years"),
}
_DET = r"(?:(?:all|the|their|its|respective|different|various|\d+)\s+)*"


def _firm(stem: str, noun: str, plural: str) -> re.Pattern:
    """Cues that can only mean "one row per <noun>"."""
    return re.compile(
        rf"\b{stem}[- ]?(?:wise|level)\b"
        rf"|\b{stem}\s+(?:breakdown|split)\b"
        rf"|\b(?:by|per|each|every|for each|for every|in each|under each|of each)"
        rf"\s+{_DET}{noun}\b"
        # "for the 9 Sankalp themes": a COUNTED set of units is asked about unit
        # by unit — and a grand total there would add in the activities that
        # belong to no theme at all.
        rf"|\b(?:for|across|of|to)\s+(?:the\s+|all\s+)*\d+\s+{plural}\b"
        rf"|\bwhich\s+{plural}\b",
        re.IGNORECASE)


def _collective(noun: str, plural: str) -> re.Pattern:
    """"across all districts", "for the 9 themes": one row per unit when asked
    plainly, but a plain TOTAL when the question says so ("the total unspent
    balance across all GPs in the state")."""
    return re.compile(rf"\b(?:across|for|over)\s+{_DET}(?:{plural})\b", re.IGNORECASE)


_CUES = {value: (_firm(*parts), _collective(parts[1], parts[2]))
         for value, parts in _NOUNS.items()}
_THEMATIC = re.compile(r"\bthematic\b", re.IGNORECASE)
_PLAN_TYPE_PAIR = re.compile(
    r"\b(?:main|primary)\s+(?:vs\.?|versus|and)\s+supplementary\b"
    r"|\bsupplementary\s+(?:vs\.?|versus|and)\s+(?:main|primary)\b", re.IGNORECASE)
_TOTAL = re.compile(r"\b(?:total|overall|aggregate|grand total|sum of|altogether|in all)\b",
                    re.IGNORECASE)


def group_by_from_text(text: str) -> str | None:
    """The breakdown the question asks for, or None.

    A firm cue wins, earliest first. A collective cue ("across all districts")
    is a breakdown unless the question also asks for a total, in which case the
    total is what it asked for. "total" with no dimension cue at all is the
    single-total reading. Nothing matched: None, and the statement keeps its own.
    """
    text = text or ""
    firm: list[tuple[int, str]] = []
    collective: list[tuple[int, str]] = []
    for value, (firm_re, collective_re) in _CUES.items():
        m = firm_re.search(text)
        if m:
            firm.append((m.start(), value))
        m = collective_re.search(text)
        if m:
            collective.append((m.start(), value))
    m = _THEMATIC.search(text)
    if m:
        firm.append((m.start(), "theme"))
    m = _PLAN_TYPE_PAIR.search(text)
    if m:
        firm.append((m.start(), "plan_type"))
    if firm:
        return min(firm)[1]
    total = _TOTAL.search(text)
    if collective and not total:
        return min(collective)[1]
    if total:
        return "total"
    return None


# ── What a migrated statement says about itself ──────────────────────────────

_CASE_RE = re.compile(r"CASE\s+\$group_by\b(.*?)\bEND\s+AS\s+group_label", re.S | re.I)
_ABSENT_RE = re.compile(r"--\s*absent:\s*(\w+)")
_SUBORDINATE_RE = re.compile(
    r"CASE\s+WHEN\s+\$group_by\s+IS\s+NULL\s+THEN\s+.+?\s+END\s+AS\s+(\w+)", re.S | re.I)


@lru_cache(maxsize=None)
def _parse(sql: str) -> tuple[frozenset, str | None, tuple]:
    case = _CASE_RE.search(sql)
    if not case:
        return frozenset(), None, ()
    values = frozenset(re.findall(r"WHEN\s+'(\w+)'", case.group(1)))
    absent = _ABSENT_RE.search(case.group(1))
    return values, (absent.group(1) if absent else None), tuple(_SUBORDINATE_RE.findall(sql))


def template_group_values(template: dict) -> frozenset:
    """The breakdowns THIS statement's CASE lists — its own whitelist."""
    return _parse(template.get("sql_template") or "")[0]


def drop_unsupported(template: dict, entities: list) -> list:
    """Remove a `$group_by` the statement cannot honour.

    `v_asset` carries no scheme, so "scheme-wise assets" would fall to the ELSE
    and answer with the default breakdown while the echo claimed a scheme one.
    Dropping it means the answer is the statement's own, and says so.
    """
    values = template_group_values(template)
    kept = []
    for entity in entities:
        if entity.slot_name == "group_by" and entity.resolved_value not in values:
            _log.info("group_by=%r is not a breakdown %s offers; dropped",
                      entity.resolved_value, template.get("abstract_question", "")[:60])
            continue
        kept.append(entity)
    return kept


def reshape(template: dict, group_by: str | None, rows: list[dict] | None):
    """Rename `group_label` to the column it holds; drop blanked columns."""
    if not rows or "group_label" not in rows[0]:
        return rows
    _, absent, subordinates = _parse(template.get("sql_template") or "")
    if group_by is None:
        name = absent                       # None: a plain total, label dropped
    elif group_by == "total":
        name = None
    else:
        name = DIMENSIONS[group_by][0]
    drop = set(subordinates) if group_by is not None else set()
    out = []
    for row in rows:
        new = {}
        for key, value in row.items():
            if key == "group_label":
                if name:
                    new[name] = value
            elif key not in drop:
                new[key] = value
        out.append(new)
    return out


def effective_grouped_geo(template: dict, group_by: str | None):
    """The geography the answer reports one row per — the echo's distributive
    reading ("each district") — given the breakdown actually chosen."""
    if group_by is None:
        return template.get("grouped_geo")
    return [GEO_SLOT_FOR[group_by]] if group_by in GEO_SLOT_FOR else []


def describe(description: str | None, group_by: str | None) -> str | None:
    """The echo, with the breakdown that ran said out loud."""
    if not description or group_by is None:
        return description
    if group_by == "total":
        return f"{description} (as one total)"
    return f"{description} (broken down by {DIMENSIONS[group_by][1]})"


# ── "Sector" (operator ruling, 2026-09-12) ────────────────────────────────────
#
# Officers say "sector" for a focus area — and sometimes for an LSDG theme. The
# operator ruled it is NOT assumed: used as the BREAKDOWN ("which sector has the
# best completion rate?", "sector-wise spend") with no value named, the bot asks.
# A NAMED value already says which dimension is meant ("the sanitation sector",
# "water vs sanitation by sector"), so that just answers.

_SECTOR_AS_BREAKDOWN = re.compile(
    r"\bsector[- ]?wise\b|\bsectoral\b"
    r"|\b(?:which|what|each|every|per|by|across|between|among|for each)\s+"
    r"(?:(?:the|all|different|various)\s+)*sectors?\b",
    re.IGNORECASE)


def _swap(text: str, singular: str, plural: str, wise: str) -> str:
    text = re.sub(r"\bsector[- ]?wise\b", wise, text, flags=re.IGNORECASE)
    text = re.sub(r"\bsectoral\b", singular, text, flags=re.IGNORECASE)
    text = re.sub(r"\bsectors\b", plural, text, flags=re.IGNORECASE)
    return re.sub(r"\bsector\b", singular, text, flags=re.IGNORECASE)


def sector_clarification(text: str, focus_area_names) -> tuple[str, list[tuple[str, str]]] | None:
    """(prompt, [(chip label, text it sends)]) when "sector" must be asked about.

    `focus_area_names` may be a list or a zero-argument callable; a callable is
    only invoked when the question uses "sector" as a breakdown at all, so the
    ordinary question never pays for (or depends on) the registry lookup.
    """
    text = text or ""
    if not _SECTOR_AS_BREAKDOWN.search(text):
        return None
    if callable(focus_area_names):
        focus_area_names = focus_area_names()
    for name in focus_area_names:
        if name and re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            return None
    return (
        "By “sector”, do you mean the focus area (Sanitation, Drinking water, …) "
        "or the LSDG theme? I don't assume one.",
        [("By focus area", _swap(text, "focus area", "focus areas", "focus-area-wise")),
         ("By LSDG theme", _swap(text, "LSDG theme", "LSDG themes", "theme-wise"))],
    )


def focus_area_names(validator) -> list[str]:
    """Every focus-area value and alias the validator knows, longest first."""
    from .entity_validator import REGISTRY_CONFIG
    names = set(validator.registry_values("focus_area"))
    names |= set(REGISTRY_CONFIG["focus_area"].get("aliases", {}))
    return sorted((n for n in names if n), key=len, reverse=True)

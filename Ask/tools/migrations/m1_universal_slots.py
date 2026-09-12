"""WP-6 T2, migration M1: universal optional filter slots.

    python tools/migrations/m1_universal_slots.py            # apply, print decisions
    python tools/migrations/m1_universal_slots.py --dry-run  # decisions only

ONE-SHOT. Run once against `query_router/template_catalog.py`; its diff is
reviewed and committed, and from then on the file is edited by hand like any
other. Kept in the tree as the record of what was scripted.

WHAT IT DOES. Every non-SBM template whose statement reads an activity view
(`v_activity`, or `v_asset` / `v_progress` which carry its columns) gets an
OPTIONAL predicate for each dimension that view carries and the statement does
not already use:

    $plan_type    plan_type         Main / Supplementary (WP-6 T1)
    $status       status_label      the six work statuses
    $focus_area   focus_area_name   the 30 Eleventh Schedule subjects
    $theme        theme             the LSDG themes
    $scheme       scheme_name       the recorded funding scheme
    $tied_untied  tied_untied       Tied / Untied / Other (the sanctioned grant)

Templates over `v_plan` get `$plan_type` only — the one of these a plan row
carries. That extends the brief's letter (activity views) because three
Eval_1 questions are plan-grain and name a plan type: "GPs that uploaded their
main GPDP", "supplementary plans approved", "GPs with a supplementary plan in
Ganjam".

Each predicate is the D2 idiom, `AND ($slot IS NULL OR <alias>.<col> = $slot)`,
inserted after the statement's own optional-geography run on the same alias (or,
where a SELECT has none, after its `WHERE <alias>.fiscal_year = $date_range`).
A bound value is never interpolated; absent, the slot binds NULL and the
statement is unchanged — which the Test Report row counts then prove.

WHAT IT SKIPS, and prints:
    * the 85 SBM templates (constraint 6): their subject is a keyword regex on
      activity text, and a focus-area predicate would silently narrow them;
    * single-activity lookups (a template binding `$activity_code`): a filter on
      one keyed row means nothing;
    * a dimension the statement already uses in a predicate, inside an
      aggregate, or through one of its derived flags (`is_completed`,
      `is_ongoing`, … are `status_label` by another name) — STS-003 keeps its
      own `$status`, IMP-005 keeps `SUM(v.is_completed)` meaning what it says;
    * a dimension already declared as a slot (PLN-049's required `$focus_area`).

WHAT IT LEAVES FOR HAND EDITING, and lists: any template where some SELECT
reading an activity view has no anchor — the LEFT-JOIN / NOT-EXISTS-from-roster
shapes (the predicate belongs inside the subquery or the ON clause), and CTEs
that aggregate before the geography is applied.

THE ORACLE. `tests/data/workbook_test_report.json` records each template's
sample parameters, and `test_catalog_execution` asserts they name exactly the
template's slots. So every added slot is also added there as `null` — the
contract "bound with the new slot ABSENT" written down rather than implied.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402

# (slot, column, entity type, what counts as the statement already using it)
DIMENSIONS = (
    ("plan_type",   "plan_type",       "plan_type",   r"\bplan_type\b"),
    ("status",      "status_label",    "status",
     r"\b(?:status_label|activity_status)\b"),
    ("focus_area",  "focus_area_name", "focus_area",  r"\bfocus_area(?:_name)?\b"),
    ("theme",       "theme",           "theme",       r"\btheme\b"),
    ("scheme",      "scheme_name",     "scheme",      r"\b(?:sanctioned_)?scheme_name\b"),
    ("tied_untied", "tied_untied",     "tied_untied", r"\btied_untied\b"),
)
# Derived status flags: ANY use of one is a use of status_label.
STATUS_FLAGS = re.compile(
    r"\bis_(?:started|completed|ongoing|abandoned|under_approval)\b", re.I)

VIEW_CARRIES = {
    "v_activity": {"plan_type", "status", "focus_area", "theme", "scheme", "tied_untied"},
    "v_asset":    {"plan_type", "status", "focus_area", "theme"},
    "v_progress": {"plan_type", "status", "focus_area", "theme"},
    "v_plan":     {"plan_type"},
}
ACTIVITY_VIEWS = {"v_activity", "v_asset", "v_progress"}
AGGREGATES = {"COUNT", "SUM", "AVG", "MIN", "MAX", "STRING_AGG", "LIST",
              "ARG_MAX", "ARG_MIN", "MODE", "MEDIAN", "ANY_VALUE", "FIRST", "LAST"}
_COMPARISON_AFTER = re.compile(
    r"\s*(?:=|<>|!=|<=|>=|<|>|\bIN\b|\bNOT\b|\bLIKE\b|\bILIKE\b|\bIS\b|\bBETWEEN\b)",
    re.I)
_COMPARISON_BEFORE = re.compile(r"(?:=|<>|!=|\bIN\s*\()\s*$", re.I)


def _inside_aggregate(masked: str, pos: int) -> bool:
    """True when `pos` sits inside the parentheses of an aggregate call."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        ch = masked[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            if depth == 0:
                word = re.search(r"(\w+)\s*$", masked[:i])
                if word and word.group(1).upper() in AGGREGATES:
                    return True
                if word and word.group(1).upper() == "FILTER":
                    return True
            else:
                depth -= 1
    return False


def uses(sql: str, pattern: str, slot: str) -> str | None:
    """Why the statement already uses this dimension, or None."""
    masked = dc.mask_literals(sql)
    if slot == "status" and STATUS_FLAGS.search(masked):
        return f"uses the derived flag {STATUS_FLAGS.search(masked).group(0)}"
    for m in re.finditer(pattern, masked, re.I):
        if _COMPARISON_AFTER.match(masked, m.end()):
            return f"compares {m.group(0)} in a predicate"
        if _COMPARISON_BEFORE.search(masked[:m.start()]):
            return f"compares {m.group(0)} in a predicate"
        if _inside_aggregate(masked, m.start()):
            return f"uses {m.group(0)} inside an aggregate"
    return None


_GEO_ANCHOR = r"^(\s*)AND\s+\(\$(?:district_name|block_name|gp_name)\s+IS\s+NULL\s+OR\s+{alias}\."
_FY_ANCHOR = r"^(\s*)WHERE\s+{alias}\.fiscal_year\s*=\s*\$date_range\b"


def anchors(sql_lines: list[str], alias: str) -> list[tuple[int, str]]:
    """[(line index to insert AFTER, indent)] — one per SELECT reading `alias`."""
    geo = re.compile(_GEO_ANCHOR.format(alias=re.escape(alias)), re.I)
    found: list[tuple[int, str]] = []
    i = 0
    while i < len(sql_lines):
        m = geo.match(sql_lines[i])
        if m:
            j = i
            while j + 1 < len(sql_lines) and geo.match(sql_lines[j + 1]):
                j += 1
            found.append((j, m.group(1)))
            i = j + 1
            continue
        i += 1
    if found:
        return found
    fy = re.compile(_FY_ANCHOR.format(alias=re.escape(alias)), re.I)
    for i, line in enumerate(sql_lines):
        m = fy.match(line)
        if m:
            found.append((i, m.group(1) + "  "))
    return found


def plan(qid: str, entry: dict) -> dict:
    """What to do with one template: {'action', 'why', 'add', 'skips', 'edits'}."""
    sql = entry["sql_template"]
    declared = {s["name"] for s in entry["param_slots"]}
    if qid.startswith("SBM-"):
        return {"action": "skip", "why": "SBM keyword template (constraint 6)"}
    if "activity_code" in declared:
        return {"action": "skip", "why": "single-activity lookup"}
    try:
        aliases = dc.alias_relations(sql)
    except ValueError as exc:
        return {"action": "hand", "why": str(exc)}
    targets = {a: r for a, r in aliases.items() if r in VIEW_CARRIES}
    if not targets:
        return {"action": "skip", "why": "reads no activity or plan view"}

    lines = sql.strip("\n").split("\n")
    placed: dict[str, list[tuple[int, str]]] = {}
    for alias in targets:
        placed[alias] = anchors(lines, alias)
    unanchored = [f"{a} ({r})" for a, r in targets.items() if not placed[a]]
    if unanchored:
        return {"action": "hand",
                "why": "no insertion point for " + ", ".join(unanchored)
                       + (" — reads the GP roster" if "gram_panchayat" in aliases.values()
                          else "")}

    carried = set.intersection(*(VIEW_CARRIES[r] for r in targets.values()))
    add, skips = [], {}
    for slot, column, etype, pattern in DIMENSIONS:
        if slot not in carried:
            continue
        if slot in declared:
            skips[slot] = "already a slot"
            continue
        why = uses(sql, pattern, slot)
        if why:
            skips[slot] = why
            continue
        add.append((slot, column, etype))
    if not add:
        return {"action": "none", "why": "every carried dimension is already used",
                "skips": skips}

    edits = []   # (line index, indent, alias)
    for alias, points in placed.items():
        for index, indent in points:
            edits.append((index, indent, alias, targets[alias]))
    return {"action": "script", "add": add, "skips": skips, "edits": edits,
            "lines": lines}


def apply_to_source(source: str, qid: str, decision: dict) -> str:
    """Rewrite one entry's SQL lines and param_slots in the file text."""
    lines = source.split("\n")
    spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
    start, end = spans[qid]
    sql_open = next(k for k in range(start, end)
                    if lines[k] == '        "sql_template": """')
    sql_close = next(k for k in range(sql_open + 1, end) if lines[k] == '""",')
    sql_lines = lines[sql_open + 1:sql_close]
    if sql_lines != decision["lines"]:
        raise RuntimeError(f"{qid}: the file's SQL lines are not the statement's")

    new_sql = list(sql_lines)
    for index, indent, alias, relation in sorted(decision["edits"], reverse=True):
        insert = [f"{indent}AND (${slot} IS NULL OR {alias}.{column} = ${slot})"
                  for slot, column, _ in decision["add"]
                  if slot in VIEW_CARRIES[relation]]
        if not insert:
            continue
        # THE ANCHOR MAY ALSO CLOSE ITS SUBQUERY. PLN-043's last geography
        # predicate is `…= $gp_name))` — its own bracket plus the NOT EXISTS'.
        # Inserted after it, the new predicates land OUTSIDE the subquery, where
        # the alias is out of scope (a binder error) or, worse, bound to an outer
        # alias of the same name (a silently misplaced filter). So any bracket
        # the anchor closes beyond its own moves to the last inserted line.
        anchor = new_sql[index].rstrip()
        excess = anchor.count(")") - anchor.count("(")
        if excess > 0:
            assert anchor.endswith(")" * (excess + 1)), anchor
            new_sql[index] = anchor[:-excess]
            insert[-1] += ")" * excess
        new_sql[index + 1:index + 1] = insert
    lines[sql_open + 1:sql_close] = new_sql

    end += len(new_sql) - len(sql_lines)
    _, slots_close = dc._find_block(lines, start, end, dc.SLOTS_OPEN, dc.SLOTS_CLOSE, qid)
    new_slots = [f"            {dc.py({'name': slot, 'entity_type': etype, 'optional': True})},"
                 for slot, _, etype in decision["add"]]
    lines[slots_close:slots_close] = new_slots
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    catalog = dc.load_catalog(source, "TEMPLATE_CATALOG")
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))

    buckets: dict[str, list[str]] = {"script": [], "hand": [], "none": [], "skip": []}
    for qid, entry in catalog.items():
        decision = plan(qid, entry)
        buckets[decision["action"]].append(qid)
        if decision["action"] == "script":
            added = ", ".join(f"${s}" for s, _, _ in decision["add"])
            where = ", ".join(sorted({f"{a}:{r}" for _, _, a, r in decision["edits"]}))
            print(f"SCRIPT {qid:<12} + {added}   [{where}; "
                  f"{len(decision['edits'])} SELECT(s)]")
            for slot, why in decision["skips"].items():
                print(f"       {'':<12}   skip ${slot}: {why}")
            if not args.dry_run:
                source = apply_to_source(source, qid, decision)
                for slot, _, _ in decision["add"]:
                    oracle[qid]["params"][slot] = None
        elif decision["action"] == "none":
            print(f"NONE   {qid:<12} {decision['why']}: "
                  + "; ".join(f"${s} {w}" for s, w in decision["skips"].items()))
        elif decision["action"] == "hand":
            print(f"HAND   {qid:<12} {decision['why']}")

    print(f"\nscripted {len(buckets['script'])} · hand-edit {len(buckets['hand'])} · "
          f"nothing to add {len(buckets['none'])} · out of scope {len(buckets['skip'])}")
    print("HAND-EDIT LIST: " + ", ".join(buckets["hand"]))

    if args.dry_run:
        return 0
    after = dc.load_catalog(source, "TEMPLATE_CATALOG")
    assert set(after) == set(catalog), "an entry appeared or vanished"
    dc.TEMPLATE_PATH.write_text(source, encoding="utf-8")
    dc.ORACLE_PATH.write_text(json.dumps(oracle, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    print(f"wrote {dc.TEMPLATE_PATH.relative_to(BACKEND)} and "
          f"{dc.ORACLE_PATH.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

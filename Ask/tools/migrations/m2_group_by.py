"""WP-6 T3, migration M2: a breakdown slot, `$group_by`.

    python tools/migrations/m2_group_by.py            # apply, print decisions
    python tools/migrations/m2_group_by.py --dry-run  # decisions only

ONE-SHOT, like M1: run once against `query_router/template_catalog.py`, diff
reviewed, committed; the file is hand-edited from then on.

WHAT IT DOES. A template whose statement is a single aggregate over one view
gains an optional `$group_by`, written into the statement as a CASE over a
FIXED WHITELIST of that view's columns — never interpolated at query time:

    CASE $group_by
      WHEN 'district'    THEN v.district_name
      …
      WHEN 'total'       THEN 'All'
      ELSE <the statement's own breakdown, or 'All'> END AS group_label

Three shapes qualify:

  * GROUP BY on exactly ONE whitelisted column (BUD-006 per theme; SCH-003 per
    `COALESCE(v.scheme_name, '(not recorded)')`). That expression becomes the
    ELSE, so with `$group_by` absent the statement groups exactly as it did —
    the Test Report rows are unchanged by construction.
  * GROUP BY a run of GEOGRAPHY columns, finest first (EXP-001's gp × block ×
    district; AST-001's gp × block). This is the `grouped_geo` shape the brief
    asks to generalise. The first column becomes the CASE; each of the others
    becomes `CASE WHEN $group_by IS NULL THEN <col> END`, so it is still there
    when no breakdown is chosen and blank — unable to split the groups — when
    one is.
  * NO GROUP BY (a plain total, EXP-004). It is grouped by
    `GROUPING SETS ((group_label), ())` with a HAVING that keeps the empty set
    when no breakdown (or 'total') is chosen — so absent, the statement returns
    its one row exactly as before, INCLUDING over no matching rows, where a
    plain aggregate still answers "0" and a GROUP BY would answer nothing.

`'total'` is the explicit single-total reading of a statement that normally
breaks down ("total planned cost of all activities" over BUD-006). It is a
whitelist value, not the absent case, because absent must keep the signed-off
shape (constraint 2); the brief's T5.3 said "group_by absent" there, which would
have broken the Test Report count of every breakdown template.

WHO GETS IT. `v_activity` and `v_asset` (the brief), and `v_plan` with the
plan-grain columns only — the same extension M1 made, for the same Eval_1
questions. Anything else — a JOIN, a CTE, a window, a second SELECT, a
non-geographic two-column GROUP BY, a listing — is printed and left alone.

FOLDS. Three pairs are one measure with a different fixed breakdown: BUD-006 /
BUD-018 (planned cost per theme / per focus area), PLN-024 / PLN-050 (+ PLN-051,
PLN-050's identical sibling), EXP-014 / EXP-025. The second of each is retired:
its question and hand paraphrases move into the survivor's hand block, and
`tests/data/retired_templates.json` records which surviving id and `$group_by`
value reproduce its Test Report count — executed here before anything is
written, and asserted by the suite after.
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

RETIRED_PATH = BACKEND / "tests" / "data" / "retired_templates.json"

# (value, column) in the order the CASE lists them.
WHITELIST = (
    ("district",    "district_name"),
    ("block",       "block_name"),
    ("gp",          "gp_name"),
    ("theme",       "theme"),
    ("focus_area",  "focus_area_name"),
    ("status",      "status_label"),
    ("scheme",      "scheme_name"),
    ("plan_type",   "plan_type"),
    ("fiscal_year", "fiscal_year"),
)
VIEW_COLUMNS = {
    "v_activity": {c for _, c in WHITELIST},
    "v_asset":    {c for _, c in WHITELIST} - {"scheme_name"},
    "v_plan":     {"district_name", "block_name", "gp_name", "plan_type", "fiscal_year"},
}
COLUMN_TO_VALUE = {c: v for v, c in WHITELIST}
GEO = ("gp_name", "block_name", "district_name")      # finest first

FOLDS = {            # retired -> survivor
    "BUD-018": "BUD-006",
    "PLN-050": "PLN-024",
    "PLN-051": "PLN-024",
    "EXP-025": "EXP-014",
}

_D10_SUBQUERY = re.compile(
    r"\(SELECT activity_code FROM v_activity WHERE gp_lgd_code = \$gp_name\)")


def _item(alias: str, text: str):
    """(column, expression, output name) for a SELECT item over one column —
    `v.theme`, `v.theme AS t`, `COALESCE(v.scheme_name, '…') AS scheme_name` —
    or None."""
    text = text.strip()
    m = re.fullmatch(rf"{re.escape(alias)}\.(\w+)(?:\s+AS\s+(\w+))?", text, re.I)
    if m:
        return m.group(1), f"{alias}.{m.group(1)}", m.group(2) or m.group(1)
    m = re.fullmatch(rf"(COALESCE\(\s*{re.escape(alias)}\.(\w+)\s*,\s*'[^']*'\s*\))"
                     rf"\s+AS\s+(\w+)", text, re.I)
    if m:
        return m.group(2), m.group(1), m.group(3)
    return None


def classify(qid: str, entry: dict) -> dict:
    sql = entry["sql_template"]
    masked = dc.mask_literals(sql)
    names = {s["name"] for s in entry["param_slots"]}
    if "group_by" in names:
        return {"action": "skip", "why": "already has $group_by"}
    if "activity_code" in names:
        return {"action": "skip", "why": "single-activity lookup"}
    stripped = _D10_SUBQUERY.sub("(D10)", masked)
    for word, why in ((r"\bWITH\b", "a CTE"), (r"\bUNION\b", "a UNION"),
                      (r"\bJOIN\b", "a JOIN"), (r"\bOVER\s*\(", "a window function")):
        if re.search(word, stripped, re.I):
            return {"action": "skip", "why": why}
    if len(re.findall(r"\bSELECT\b", stripped, re.I)) != 1:
        return {"action": "skip", "why": "more than one SELECT"}
    try:
        aliases = dc.alias_relations(sql)
    except ValueError as exc:
        return {"action": "skip", "why": str(exc)}
    views = {a: r for a, r in aliases.items() if r in VIEW_COLUMNS}
    if len(views) != 1 or len(aliases) != 1:
        return {"action": "skip", "why": f"reads {sorted(aliases.values()) or 'no view'}"}
    (alias, relation), = views.items()

    select, group = dc.outer_select_and_group(sql)
    if not re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", " ".join(select), re.I):
        return {"action": "skip", "why": "not an aggregate"}
    base = {"action": "script", "alias": alias, "relation": relation}
    if not group:
        if re.search(r"\bHAVING\b", stripped, re.I):
            return {"action": "skip", "why": "HAVING without GROUP BY"}
        return {**base, "kind": "none", "items": []}

    resolved = []
    for expr in group:
        if expr.isdigit():
            index = int(expr) - 1
            if not 0 <= index < len(select):
                return {"action": "skip", "why": "GROUP BY ordinal out of range"}
            text = select[index]
        else:
            text = next((s for s in select if _item(alias, s) and
                         _item(alias, s)[1].lower() == expr.strip().lower()), expr)
        item = _item(alias, text)
        if not item or item[0] not in VIEW_COLUMNS[relation]:
            return {"action": "skip", "why": f"GROUP BY {text.strip()!r} is not a whitelisted column"}
        resolved.append((text.strip(), *item))

    if len(resolved) == 1:
        return {**base, "kind": "one", "items": resolved}
    columns = [r[1] for r in resolved]
    if set(columns) <= set(GEO) and columns == sorted(columns, key=GEO.index):
        return {**base, "kind": "geo", "items": resolved}
    return {"action": "skip", "why": f"GROUP BY {len(group)} expressions"}


def case_lines(alias: str, relation: str, default: str, indent: str,
               absent: str | None = None) -> list[str]:
    columns = VIEW_COLUMNS[relation]
    width = max(len(v) for v, c in WHITELIST if c in columns) + 3
    lines = ["CASE $group_by"]
    for value, column in WHITELIST:
        if column in columns:
            lines.append(f"{indent}  WHEN {repr(value):<{width}} THEN {alias}.{column}")
    lines.append(f"{indent}  WHEN {repr('total'):<{width}} THEN 'All'")
    if absent:
        # Read back by query_router/breakdown.py: the name `group_label` is
        # shown under when no breakdown is chosen, so the table reads as before.
        lines.append(f"{indent}  ELSE {default}  -- absent: {absent}")
        lines.append(f"{indent}END AS group_label")
    else:
        lines.append(f"{indent}  ELSE {default} END AS group_label")
    return lines


def rewrite_sql(sql_lines: list[str], d: dict) -> list[str]:
    text = "\n".join(sql_lines)
    alias, relation = d["alias"], d["relation"]
    head_end = re.search(rf"\bFROM\s+{relation}\b", dc.mask_literals(text), re.I).start()
    head, tail = text[:head_end], text[head_end:]

    def indent_at(pos: int) -> str:
        return " " * (pos - (head.rfind("\n", 0, pos) + 1))

    if d["kind"] == "none":
        m = re.match(r"(\s*SELECT\s+)", head, re.I)
        indent = indent_at(m.end())
        case = case_lines(alias, relation, "'All'", indent)
        head = head[:m.end()] + ("\n" + indent).join(case) + ",\n" + indent + head[m.end():]
        clause = re.search(r"\n\s*(ORDER\s+BY|LIMIT)\b", tail, re.I)
        cut = clause.start() if clause else len(tail)
        # GROUPING SETS, not `GROUP BY 1`. A plain aggregate over NO rows still
        # returns its one row ("0 activities"); a GROUP BY over no rows returns
        # none — PLN-014 and two SBM counts lost their row that way on the first
        # run. The empty grouping set keeps that row whenever no breakdown (or
        # 'total') is chosen, and the HAVING keeps exactly one of the two sets.
        tail = (tail[:cut]
                + "\nGROUP BY GROUPING SETS ((group_label), ())"
                + "\nHAVING (GROUPING(group_label) = 1) = "
                  "($group_by IS NULL OR $group_by = 'total')"
                + tail[cut:])
        return (head + tail).split("\n")

    # The primary item becomes the CASE; the rest (geo shape) are blanked when a
    # breakdown is chosen. Replaced right-to-left so offsets stay valid.
    spots = []
    for position, (text_, column, expr, output) in enumerate(d["items"]):
        found = [m for m in re.finditer(re.escape(text_), head)]
        if len(found) != 1:
            raise RuntimeError(f"expected one SELECT item {text_!r}, found {len(found)}")
        spots.append((found[0], position, column, expr, output))
    for m, position, column, expr, output in sorted(spots, key=lambda s: -s[0].start()):
        if position == 0:
            new = ("\n" + indent_at(m.start())).join(
                case_lines(alias, relation, expr, indent_at(m.start()), output))
        else:
            new = f"CASE WHEN $group_by IS NULL THEN {expr} END AS {output}"
        head = head[:m.start()] + new + head[m.end():]

    # A GROUP BY / ORDER BY that NAMES an item must now name its label — and
    # ONLY those clauses: the WHERE above them holds M1's own predicates on the
    # same column (`$theme IS NULL OR v.theme = $theme`), which must keep
    # reading the view's column, not the label.
    clauses = re.search(r"\bGROUP\s+BY\b", tail, re.I)
    if clauses:
        before, after = tail[:clauses.start()], tail[clauses.start():]
        primary = d["items"][0]
        for text_, column, expr, output in d["items"]:
            target = "group_label" if (text_, column) == primary[:2] else output
            after = re.sub(rf"(?<![\w.]){re.escape(expr)}(?![\w(])", target, after)
        tail = before + after
    return (head + tail).split("\n")


def replace_entry_sql(source: str, qid: str, new_lines: list[str]) -> str:
    lines = source.split("\n")
    spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
    start, end = spans[qid]
    sql_open = next(k for k in range(start, end) if lines[k] == '        "sql_template": """')
    sql_close = next(k for k in range(sql_open + 1, end) if lines[k] == '""",')
    lines[sql_open + 1:sql_close] = new_lines
    end += len(new_lines) - (sql_close - sql_open - 1)
    _, slots_close = dc._find_block(lines, start, end, dc.SLOTS_OPEN, dc.SLOTS_CLOSE, qid)
    lines[slots_close:slots_close] = [
        f"            {dc.py({'name': 'group_by', 'entity_type': 'group_by', 'optional': True})},"]
    return "\n".join(lines)


def fold(source: str, catalog: dict, retired: str, survivor: str) -> str:
    """Remove `retired`; move its question and hand paraphrases to `survivor`."""
    lines = source.split("\n")
    spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
    r_start, r_end = spans[retired]
    opened, closed = dc._find_block(lines, r_start, r_end, dc.PARAPHRASES_OPEN,
                                    dc.PARAPHRASES_CLOSE, retired)
    _, hand = dc._split_paraphrase_body(lines[opened + 1:closed], retired)
    moved = [dc.to_prose(dc.token_form(catalog[retired]["abstract_question"])), *hand]

    drop_from = r_start - 1 if r_start and lines[r_start - 1] == "" else r_start
    del lines[drop_from:r_end + 1]

    spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
    s_start, s_end = spans[survivor]
    opened, closed = dc._find_block(lines, s_start, s_end, dc.PARAPHRASES_OPEN,
                                    dc.PARAPHRASES_CLOSE, survivor)
    body = lines[opened + 1:closed]
    marker = next((i for i, l in enumerate(body) if l.strip().startswith("# ── derived")),
                  len(body))
    existing = {dc._string_line(l, survivor).lower() for l in body[:marker]
                if l.strip() and not l.strip().startswith("#")}
    new = [f"            # folded from {retired} (WP-6 T3): the same measure, "
           f"answered with $group_by"]
    new += [f"            {t!r}," for t in dict.fromkeys(moved) if t.lower() not in existing]
    lines[opened + 1 + marker:opened + 1 + marker] = new
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    catalog = dc.load_catalog(source, "TEMPLATE_CATALOG")
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))

    scripted, skipped, defaults = [], [], {}
    for qid, entry in catalog.items():
        d = classify(qid, entry)
        if d["action"] == "skip":
            skipped.append((qid, d["why"]))
            continue
        new = rewrite_sql(entry["sql_template"].strip("\n").split("\n"), d)
        default = d["items"][0][1] if d["items"] else None
        defaults[qid] = default
        label = {"none": "no breakdown -> 'All'", "one": f"default {default}",
                 "geo": "geo grain " + " x ".join(i[1] for i in d["items"])}[d["kind"]]
        grouped = " [grouped_geo carrier]" if entry.get("grouped_geo") else ""
        print(f"SCRIPT {qid:<12} {d['relation']:<10} {label}{grouped}")
        scripted.append(qid)
        if not args.dry_run:
            source = replace_entry_sql(source, qid, new)
            oracle[qid]["params"]["group_by"] = None

    carriers = [q for q, e in catalog.items() if e.get("grouped_geo")]
    left = [q for q in carriers if q not in scripted]
    print(f"\nscripted {len(scripted)} · left alone {len(skipped)}")
    print(f"grouped_geo carriers: {len(carriers)}; migrated {len(carriers) - len(left)}; "
          f"left: {', '.join(left)}")
    reasons: dict[str, int] = {}
    for _, why in skipped:
        key = re.sub(r"'.*'", "'…'", why)
        reasons[key] = reasons.get(key, 0) + 1
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  left alone — {why}: {n}")
    print("  grouped_geo carriers left, with why: " + "; ".join(
        f"{q} ({why})" for q, why in skipped if q in left))

    if args.dry_run:
        return 0

    # ── folds: prove, then retire ────────────────────────────────────────────
    from db_factory import open_analytical_db
    from query_router.entity_validator import EntityValidator
    adapter = open_analytical_db(BACKEND / "data" / "panchayat_1.duckdb")
    validator = EntityValidator(adapter)
    migrated = dc.load_catalog(source, "TEMPLATE_CATALOG")
    retired_log = json.loads(RETIRED_PATH.read_text(encoding="utf-8")) \
        if RETIRED_PATH.exists() else {}
    for retired, survivor in FOLDS.items():
        want = oracle[retired]
        group = COLUMN_TO_VALUE[defaults[retired]]
        slots = {s["name"]: s for s in migrated[survivor]["param_slots"]}
        params = {name: want["params"].get(name) for name in slots}
        for name, slot in slots.items():
            if slot.get("bind") == "code" and params.get(name):
                params[name] = validator.validate(str(params[name]),
                                                  slot["entity_type"]).resolved_code
        params["group_by"] = group
        rows = adapter.execute(migrated[survivor]["sql_template"], params).fetchall()
        if len(rows) != want["rows"]:
            print(f"FOLD REFUSED {retired} -> {survivor}: {len(rows)} rows, "
                  f"Test Report says {want['rows']}", file=sys.stderr)
            return 1
        print(f"FOLD   {retired} -> {survivor} with $group_by = {group!r}: "
              f"{len(rows)} rows = the Test Report's {want['rows']}")
        source = fold(source, catalog, retired, survivor)
        retired_log[retired] = {
            "survivor": survivor, "group_by": group, "rows": want["rows"],
            "params": want["params"], "retired_in": "WP-6 T3",
            "question": catalog[retired]["abstract_question"],
        }
        del oracle[retired]

    after = dc.load_catalog(source, "TEMPLATE_CATALOG")
    assert set(after) == set(catalog) - set(FOLDS)
    dc.TEMPLATE_PATH.write_text(source, encoding="utf-8")
    dc.ORACLE_PATH.write_text(json.dumps(oracle, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    RETIRED_PATH.write_text(json.dumps(retired_log, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(f"wrote the catalogue ({len(after)} templates), the oracle and "
          f"{RETIRED_PATH.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

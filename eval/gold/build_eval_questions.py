#!/usr/bin/env python
"""Concatenate the per-bracket gold files into the shapes the WP-4 harnesses read.

The gold set is authored one JSONL file per bracket (see README.md). The
harnesses each want a single file in a fixed place:

  run_full_eval.py / run_custom_eval.py / run_consistency_eval.py
      Chatbot/eval_questions_full.json   — a JSON array of question specs
  recall_eval.py
      <repo root>/test_questions_query_mapping.csv
      — columns query_code, topic, intent

This script produces both. It does not modify any harness and makes no LLM,
network or database calls.

  python eval/gold/build_eval_questions.py                 # write next to the gold files
  python eval/gold/build_eval_questions.py --install       # write where the harnesses look
  python eval/gold/build_eval_questions.py --out-dir DIR

FILE ORDER IS LOAD-BEARING. run_full_eval.py resolves `"session": "prev"` to the
session of the IMMEDIATELY PRECEDING record, so a follow-up fragment must stay
directly after its prior question. --check enforces that and exits non-zero if
the invariant is broken.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# eval/gold -> eval -> repo root. PRDW_REPO overrides it, for the case where the
# gold tree is staged outside the repo (as it was during WP-4a, while WP-3 owned
# the working tree).
REPO = Path(os.environ.get("PRDW_REPO") or HERE.parent.parent)
CHATBOT = REPO / "Chatbot"

# Emission order. Follow-ups are adjacent to their prior question inside a file,
# so only the file order is a choice; keeping it stable keeps `n` stable too.
BRACKET_FILES = [
    "planning.jsonl",
    "sanitation_sbm.jsonl",
    "budgeting_funding.jsonl",
    "expenditure.jsonl",
    "implementation_progress.jsonl",
    "monitoring_alerts_dq.jsonl",
    "sanctions_approvals.jsonl",
    "assets.jsonl",
    "trends_comparison.jsonl",
    "decision_support.jsonl",
    "beneficiaries_dropped.jsonl",
    "out_of_domain.jsonl",
]

# Question shapes that do not belong in a RETRIEVAL recall measurement:
# a bare fragment has no retrievable subject of its own, and a question whose
# gold is `no_match` has no catalogue entry to rank.
RECALL_EXCLUDED_CASES = {"followup", "unanswerable", "out_of_domain"}


def load(gold_dir: Path) -> list[dict]:
    recs: list[dict] = []
    for name in BRACKET_FILES:
        path = gold_dir / name
        if not path.exists():
            sys.exit(f"missing gold file: {path}")
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                sys.exit(f"{name}:{line_no}: {exc}")
    return recs


def check(recs: list[dict]) -> list[str]:
    """Invariants the harnesses depend on. Returns a list of problems."""
    problems: list[str] = []
    seen_n: dict[int, str] = {}
    by_id = {r["id"]: r for r in recs}

    for i, rec in enumerate(recs):
        rid = rec.get("id", f"<index {i}>")
        for field in ("n", "q", "gold"):
            if field not in rec:
                problems.append(f"{rid}: missing required field {field!r}")
        n = rec.get("n")
        if n in seen_n:
            problems.append(f"{rid}: duplicate n={n} (also {seen_n[n]})")
        seen_n[n] = rid
        if not isinstance(rec.get("acc", []), list):
            problems.append(f"{rid}: acc must be a list")
        for flag in ("partial", "excluded"):
            if not isinstance(rec.get(flag, False), bool):
                problems.append(f"{rid}: {flag} must be a bool")

        if rec.get("session") == "prev":
            prior = rec.get("prior_id")
            if not prior:
                problems.append(f"{rid}: session=prev without prior_id")
            elif prior not in by_id:
                problems.append(f"{rid}: prior_id {prior} not found")
            elif i == 0 or recs[i - 1]["id"] != prior:
                got = recs[i - 1]["id"] if i else "<start of file>"
                problems.append(
                    f"{rid}: must directly follow {prior}, but follows {got} — "
                    "run_full_eval.py would attach this fragment to the wrong session")
    return problems


def check_against_catalogue(recs: list[dict]) -> tuple[list[str], list[str]]:
    """Cross-check every route and slot against the live catalogue.

    Catches gold-set drift when WP-3 (or anyone) renames an id or changes a
    template's slots. Skipped with a warning if Chatbot/ will not import —
    the gold set is still valid data, it just cannot be cross-checked here.

    Returns (problems, notes).
    """
    problems: list[str] = []
    notes: list[str] = []
    sys.path.insert(0, str(CHATBOT))
    try:
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.dashboard_catalog import DASHBOARD_CATALOG as D
        from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG as U
    except Exception as exc:  # noqa: BLE001
        notes.append(f"catalogue cross-check SKIPPED ({type(exc).__name__}: {exc})")
        return problems, notes

    # WP-4 T3: an unanswerable id is a legitimate GOLD, not only a provenance
    # ref. The router retrieves these entries and serves the workbook's own
    # reason for declining, returning that query_id — so naming the id says
    # "declined for the RIGHT documented reason", which `no_match` cannot
    # express (WP-4a §5).
    known = set(T) | set(D) | set(U)
    notes.append(f"catalogue: {len(T)} templates, {len(D)} dashboards, "
                 f"{len(U)} unanswerable")

    for rec in recs:
        rid, gold = rec["id"], rec["gold"]
        for qid in [gold, *rec.get("acc", [])]:
            if qid and qid != "no_match" and qid not in known:
                problems.append(f"{rid}: {qid} is not in the catalogue")
        ref = rec.get("unanswerable_ref")
        if ref and ref not in U:
            problems.append(f"{rid}: unanswerable_ref {ref} is not in "
                            f"UNANSWERABLE_CATALOG")
        if rec.get("case_type") == "unanswerable":
            if gold not in U:
                problems.append(
                    f"{rid}: an unanswerable row's gold must be an "
                    f"UNANSWERABLE_CATALOG id (got {gold!r})")
            elif ref and ref != gold:
                problems.append(
                    f"{rid}: gold {gold} and unanswerable_ref {ref} disagree")
        if gold in T:
            slots = {s["name"] for s in T[gold]["param_slots"]}
            for k in rec.get("expected_entities", {}):
                if k not in slots:
                    problems.append(
                        f"{rid}: expected_entities has {k!r} but {gold} has no such "
                        f"slot (slots: {sorted(slots)})")
            problems += _check_direction_pin(rec, T[gold], slots)

    paired = {qid for qid, t in T.items()
              if {"date_range", "date_range_2"} <= {s["name"] for s in t["param_slots"]}}
    pinned = {rec["gold"] for rec in recs
              if (rec.get("expected_result") or {}).get("direction_pin")}
    notes.append(f"direction pins: {len(pinned)} of {len(paired)} paired-year "
                 f"templates covered")
    if paired - pinned:
        problems.append(
            "D30.3: these paired-year templates carry no direction-pinned gold row, "
            "so an inverted $date_range/$date_range_2 pair would be invisible to the "
            f"eval: {', '.join(sorted(paired - pinned))}")
    return problems, notes


def _check_direction_pin(rec: dict, template: dict, slots: set[str]) -> list[str]:
    """Structural validation of a `direction_pin` (D30.3, WP-4c T3b).

    THE PIN EXISTS BECAUSE A SIGN INVERSION IS INVISIBLE TO A ROUTE-GRADED EVAL.
    All five paired templates bind `$date_range_2` as year1 and `$date_range` as
    year2, and three compute `$date_range - $date_range_2`; swap the pair and
    "greatest increase" answers with the greatest decline, in a table that looks
    entirely normal and whose query_id is exactly right. WP-4's replays did that
    on every paired row in all three runs and graded all of them `hit`.

    This checks only that the pin DESCRIBES the template it is attached to — that
    its columns and slots exist, and that its arithmetic is self-consistent.
    Whether the values are TRUE is checked by executing the SQL, in
    `Chatbot/tests/test_paired_year_direction.py` (always on, no LLM), and whether
    the ROUTER preserves them is checked by `grade_full_eval`'s `wrong_direction`
    bucket on every replay.
    """
    pin = (rec.get("expected_result") or {}).get("direction_pin")
    if not pin:
        return []
    rid, gold = rec["id"], rec["gold"]
    problems: list[str] = []
    sql = template["sql_template"]

    for field in ("why", "params", "year_columns", "first_row"):
        if field not in pin:
            problems.append(f"{rid}: direction_pin missing {field!r}")
    if problems:
        return problems

    for name in pin["params"]:
        if name not in slots:
            problems.append(f"{rid}: direction_pin params name {name!r}, which "
                            f"{gold} has no slot for")
    for column, slot in pin["year_columns"].items():
        if f"AS {column}" not in sql:
            problems.append(f"{rid}: direction_pin names column {column!r}, which "
                            f"{gold}'s SQL does not select")
        if slot not in ("date_range", "date_range_2"):
            problems.append(f"{rid}: direction_pin maps {column!r} to {slot!r}; only "
                            f"date_range / date_range_2 are a pair")
    if set(pin["year_columns"].values()) != {"date_range", "date_range_2"}:
        problems.append(f"{rid}: direction_pin must map columns to BOTH ends of the "
                        f"pair, or it pins nothing")
    for column in pin["year_columns"]:
        if column not in pin["first_row"]:
            problems.append(f"{rid}: direction_pin year column {column!r} has no "
                            f"value in first_row")

    # Self-consistency: a change column pinned alongside its two year columns must
    # equal year2 - year1, or the pin itself encodes the inversion it exists to
    # catch.
    row = pin["first_row"]
    for change, (a, b) in (("change_in_activities",
                            ("activities_year1", "activities_year2")),
                           ("change_amount",
                            ("expenditure_year1", "expenditure_year2"))):
        if change in row and a in row and b in row:
            if abs((row[b] - row[a]) - row[change]) > 0.01:
                problems.append(
                    f"{rid}: direction_pin is not self-consistent — {change} is "
                    f"{row[change]} but {b} - {a} is {row[b] - row[a]}")
    return problems


def write_full(recs: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out}  ({len(recs)} specs)")


def write_recall_csv(recs: list[dict], out: Path) -> None:
    # A FRAGMENT has no standalone retrieval target — "what about Laxmipur?"
    # carries a place and no subject, so scoring it against a template measures
    # the frame it was denied rather than the retriever. `session: "prev"` is
    # the property that says so; case_type does not, because a fragment can also
    # be an AMBIGUITY row (G1524 is both, and scored 107 here before this rule).
    rows = [r for r in recs
            if r.get("case_type") not in RECALL_EXCLUDED_CASES
            and r.get("session") != "prev"
            and r.get("gold") and r["gold"] != "no_match"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        # `lang` is additive — recall_eval reads by DictReader, so older
        # readers ignore it — and it is what turns "recall@30 is 94.8%" into
        # "recall@30 is 98% in English and 76% in Odia script", which is a
        # finding rather than a number.
        w.writerow(["query_code", "topic", "intent", "lang"])
        for r in rows:
            w.writerow([r["gold"], r["q"], r.get("bracket") or "",
                        r.get("lang") or ""])
    skipped = len(recs) - len(rows)
    print(f"wrote {out}  ({len(rows)} rows; {skipped} skipped — "
          f"fragments, unanswerables and out-of-domain have no retrieval target)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-dir", type=Path, default=HERE)
    ap.add_argument("--out-dir", type=Path,
                    help="write both artefacts here (default: alongside the gold files)")
    ap.add_argument("--install", action="store_true",
                    help="write to the paths the harnesses actually read: "
                         "Chatbot/eval_questions_full.json and "
                         "<repo>/test_questions_query_mapping.csv")
    ap.add_argument("--check", action="store_true",
                    help="validate only; write nothing")
    args = ap.parse_args()

    recs = load(args.gold_dir)
    problems = check(recs)
    cat_problems, cat_notes = check_against_catalogue(recs)
    problems += cat_problems
    for n in cat_notes:
        print(f"  {n}")
    if problems:
        print(f"FAILED — {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"OK — {len(recs)} records, invariants hold")

    if args.check:
        return 0

    if args.install:
        write_full(recs, CHATBOT / "eval_questions_full.json")
        write_recall_csv(recs, REPO / "test_questions_query_mapping.csv")
    else:
        out = args.out_dir or HERE
        write_full(recs, out / "eval_questions_full.json")
        write_recall_csv(recs, out / "test_questions_query_mapping.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

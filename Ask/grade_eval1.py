"""Grade an Eval_1 replay the way the PM graded the 2026-09-14 one (WP-6b T6).

    cd Ask
    python run_custom_eval.py --questions ../handoffs/WP6_eval1_questions.json \\
        --out eval1_results.jsonl --yes
    python grade_eval1.py eval1_results.jsonl --out ../handoffs/WP6b_eval1_replay.csv \\
        --baseline ../handoffs/WP6_eval1_replay.csv

THE FILE IS A STANDING REGRESSION. Eval_1 is 314 officer phrasings of 26
questions, written by people who did not know the catalogue's wording. The PM's
first full replay of it (`handoffs/WP6_eval1_replay.*`) found five defects that
639 tests, nine gates and a recall harness had all passed. So it is re-run after
any Ask package that touches slots, paraphrases or the reranker, graded the same
way every time, and diffed against the last run.

THE GRADING, LIFTED FROM THE PM'S:

  correct            answered with an accepted template — and, for the road
                     group, with the Roads focus area actually bound. That one
                     filter check moved a whole group on 2026-09-14: ten rows
                     answered with the count of EVERY ongoing activity.
  clarify            asked, and an accepted template was among the chips
  clarify-incorrect  asked, and none of the chips was an accepted template
  incorrect          answered with anything else, served a refusal, or declined
  defective row      Eval_1's own: the question names two different years. Kept
                     and marked, never fixed — informative about that shape.

The "sector" group is expected to ASK (operator ruling 2026-09-12): there a
clarification of any kind is correct and an answer is not.

Chips are mapped back to template ids by their wording, the way the PM read
them, and an id stands for its FAMILY — the templates with identical SQL and
slots in `rerank_context` (PLN-025/027/029 are one statement at three scopes).
The reranker's choice inside a family cannot change the answer, and the PM named
a family by its lead id. `tests/test_wp6b_eval1_fixes.py` holds this file to the
PM's grading of the baseline, row for row.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from query_router.dashboard_catalog import DASHBOARD_CATALOG        # noqa: E402
from query_router.rerank_context import FAMILY_DESCRIPTIONS         # noqa: E402
from query_router.template_catalog import TEMPLATE_CATALOG          # noqa: E402
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG  # noqa: E402
from query_router.zones import readable_question                    # noqa: E402

# id -> the catalogue question a chip for it is rendered from.
_QUESTION = {**{q: e["question"] for q, e in DASHBOARD_CATALOG.items()},
             **{q: e["question"] for q, e in UNANSWERABLE_CATALOG.items()},
             **{q: e["abstract_question"] for q, e in TEMPLATE_CATALOG.items()}}

# id -> its family, lead id first (members are stored sorted).
_FAMILY = {qid: tuple(family["members"])
           for family in FAMILY_DESCRIPTIONS.values() for qid in family["members"]}


def family(qid: str) -> tuple[str, ...]:
    return _FAMILY.get(qid, (qid,))


# (group, Eval_1 rows as inclusive ranges, accepted template ids) — the PM's
# 2026-09-12 matching table as graded on 2026-09-14, after WP-6's folds.
GROUPS: list[tuple[str, list[tuple[int, int]], tuple[str, ...]]] = [
    ("total planned budget, main GPDPs", [(1, 8), (25, 30)], ("BUD-006",)),
    ("GPs with zero-cost activities", [(10, 15), (185, 190), (192, 197)],
     ("DQY-007", "PLU-008")),
    ("Swachh Bharat sanitation completed", [(17, 22), (291, 302)], ("STS-003",)),
    ("total unspent statewide", [(32, 37)], ("EXP-004",)),
    ("tied spend water vs sanitation", [(40, 45), (47, 52)], ("EXP-009", "EXP-011")),
    ("allocation to Sankalp themes", [(54, 59), (61, 66)], ("BUD-006",)),
    ("GPs with nothing under Sankalp themes", [(68, 73), (75, 80)], ("PLN-032",)),
    ("GPs uploaded main GPDP (conflicting years)", [(83, 94)], ("PLN-001",)),
    ("GPs not uploaded GPDP", [(97, 108)], ("PLN-005",)),
    ("supplementary plans approved", [(111, 116), (118, 123)], ("PLN-002", "PLU-004")),
    ("GPs with supplementary plan in Ganjam", [(126, 137)], ("PLU-004",)),
    ("total activities in main GPDPs", [(140, 145), (147, 152)], ("PLN-024",)),
    ("GP with most planned activities", [(155, 160), (162, 167)], ("PLN-031",)),
    ("total estimated cost statewide", [(170, 175), (177, 182)], ("BUD-006",)),
    ("planned activities by theme", [(200, 205), (207, 212)], ("PLN-024",)),
    ("activities under sanitation", [(215, 220), (222, 227)], ("PLN-049",)),
    ("GP with most piped water activities", [(230, 235), (237, 242)], ("PLN-031",)),
    ("GPs pending GPDP approval", [(246, 257)], ("PLN-014",)),
    ("completed activities statewide", [(258, 268)], ("IMP-002", "STS-003")),
    ("activities in progress", [(269, 279)], ("STS-003",)),
    ("sector with best completion rate", [(280, 290)], ("IMP-005",)),
    ("road works in progress", [(303, 313)], ("IMP-011", "STS-003")),
    ("districts behind on GPDP submission", [(314, 324)], ("PLN-007",)),
    ("GPs with spend but no physical progress", [(325, 335)], ("PHY-006",)),
    ("district-wise asset creation", [(336, 346)], ("AST-001",)),
    ("five-year fund utilisation", [(347, 357), (370, 371)],
     ("EXP-002", "TRD-003", "TRD-006")),
]
DEFECTIVE = "GPs uploaded main GPDP (conflicting years)"
EXPECTED_TO_ASK = "sector with best completion rate"
# A hit must carry these bound values, or it answered a different question.
REQUIRED_FILTERS = {"road works in progress": {"focus_area": "Roads"}}

OUTCOMES = ("correct", "clarify", "clarify-incorrect", "incorrect", "defective row")
HEADER = ["eval_row", "question_group", "question", "expected_template_ids",
          "expected_template_question", "served_template_id", "served_question",
          "bound_filters", "outcome", "note"]


def row_spec(n: int) -> tuple[str, tuple[str, ...]] | None:
    for group, ranges, accepted in GROUPS:
        if any(lo <= n <= hi for lo, hi in ranges):
            return group, accepted
    return None


def _question_patterns() -> list[tuple[str, re.Pattern, int]]:
    """(id, pattern, literal length) for every question a chip can show.

    A chip is a catalogue question with its placeholders filled or turned into
    stand-ins ("a gram panchayat"), so each placeholder becomes a wildcard. When
    several questions match, the one with the most literal text is the chip.
    """
    patterns = []
    for qid, question in _QUESTION.items():
        parts = re.split(r"\{\w+\}", question.strip())
        body = ".+?".join(re.escape(p) for p in parts)
        patterns.append((qid, re.compile(rf"\s*{body}\s*", re.I | re.S),
                         sum(len(p) for p in parts)))
    return patterns


_PATTERNS = _question_patterns()


def chip_ids(label: str) -> list[str]:
    """The template id(s) a chip's wording belongs to; [] when none does.

    Siblings whose wording differs only in a placeholder — PLN-032 "…under
    {theme}…" and PLN-059 "…under {focus_area}…" — match the same chip, so a
    tie is broken by how close each one's chip rendering ("…under a theme…")
    is to the label.
    """
    text = re.sub(r"^Why I can't answer:\s*", "", label or "")
    hits = [(literal, qid) for qid, pattern, literal in _PATTERNS
            if pattern.fullmatch(text)]
    if not hits:
        return []
    best = max(literal for literal, _ in hits)
    tied = sorted({qid for literal, qid in hits if literal == best})
    if len(tied) == 1:
        return tied
    closeness = {qid: SequenceMatcher(None, readable_question(_QUESTION[qid]), text).ratio()
                 for qid in tied}
    top = max(closeness.values())
    return [qid for qid in tied if closeness[qid] == top]


def _accepted(ids, accepted: tuple[str, ...]) -> bool:
    return any(set(family(qid)) & set(accepted) for qid in ids)


def _bound(record: dict) -> dict:
    return {e["slot"]: (e.get("values") or e.get("value"))
            for e in record.get("entities") or []}


def grade(record: dict) -> dict:
    """One graded CSV row for one replay record."""
    n = int(record["n"])
    spec = row_spec(n)
    if spec is None:
        raise ValueError(f"Eval_1 row {n} is in no question group")
    group, accepted = spec
    row = {"eval_row": n, "question_group": group, "question": record.get("q", ""),
           "expected_template_ids": "; ".join(accepted),
           "expected_template_question":
               TEMPLATE_CATALOG.get(accepted[0], {}).get("abstract_question", ""),
           "served_template_id": "", "served_question": "", "bound_filters": "",
           "outcome": "", "note": ""}
    notes: list[str] = []
    clarification = record.get("clarification") or {}
    query_id = record.get("query_id")

    if record.get("error"):
        row["outcome"] = "incorrect"
        notes.append(f"error: {record['error'][:80]}")
    elif (record.get("tier") == "clarify"
          or (clarification and clarification.get("reason") != "known_unanswerable")):
        # The no-match path offers its readings on the FALLBACK tier ("I can't
        # answer that exactly, but I can answer these:"); the PM read those as the
        # clarifications they are. A served refusal's one "closest question" chip
        # is not a clarification — it is the refusal, graded below.
        row["served_question"] = f"(asked: {(clarification.get('prompt') or '')[:60]})"
        if group == DEFECTIVE:
            row["outcome"] = "defective row"
            notes.append("question names two different years")
        elif group == EXPECTED_TO_ASK:
            row["outcome"] = "correct"
            notes.append("expected to ask (operator ruling on 'sector')")
        else:
            chips = [chip_ids(o.get("label", "")) for o in clarification.get("options") or []]
            shown = ", ".join(ids[0] if ids else "?" for ids in chips)
            if any(_accepted(ids, accepted) for ids in chips):
                row["outcome"] = "clarify"
                notes.append(f"right template offered as a chip: {shown}")
            else:
                row["outcome"] = "clarify-incorrect"
                notes.append(f"right template NOT offered; chips: {shown}")
    elif query_id:
        bound = _bound(record)
        row["served_template_id"] = query_id
        row["served_question"] = record.get("query_description") or ""
        row["bound_filters"] = json.dumps(bound, ensure_ascii=False) if bound else ""
        if group == DEFECTIVE:
            row["outcome"] = "defective row"
            notes.append("question names two different years")
        elif group == EXPECTED_TO_ASK:
            row["outcome"] = "incorrect"
            notes.append("expected to ask which reading of 'sector'")
        elif query_id in UNANSWERABLE_CATALOG:
            row["outcome"] = "incorrect"
            notes.append("served a refusal entry")
        elif _accepted([query_id], accepted):
            missing = {slot: value for slot, value in REQUIRED_FILTERS.get(group, {}).items()
                       if bound.get(slot) != value}
            if missing:
                row["outcome"] = "incorrect"
                notes.append("filter not bound: " + ", ".join(
                    f"{slot} = {value}" for slot, value in missing.items()))
            else:
                row["outcome"] = "correct"
        else:
            row["outcome"] = "incorrect"
        if "No records matched" in (record.get("answer") or ""):
            notes.append("answered 'No records matched'")
    else:
        row["outcome"] = "incorrect"
        notes.append(f"declined: {(record.get('answer') or '')[:60]}")

    row["note"] = "; ".join(notes)
    return row


def grade_file(path: Path) -> list[dict]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    return sorted((grade(r) for r in records), key=lambda r: r["eval_row"])


def read_graded(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_graded(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _counts(rows: list[dict]) -> Counter:
    return Counter(r["outcome"] for r in rows)


def headline(rows: list[dict], label: str) -> None:
    counts = _counts(rows)
    gradable = len(rows) - counts["defective row"]
    print(f"\n── {label}: {len(rows)} rows, {gradable} gradable ──")
    for outcome in OUTCOMES:
        share = (f"{counts[outcome] / gradable:6.1%}" if outcome != "defective row"
                 and gradable else "")
        print(f"  {outcome:<18} {counts[outcome]:>4}  {share}")


def movement(before: list[dict], after: list[dict]) -> None:
    """Per-group before -> after, then every row whose outcome changed."""
    b_by = {int(r["eval_row"]): r for r in before}
    a_by = {int(r["eval_row"]): r for r in after}
    short = {"correct": "ok", "clarify": "cl", "clarify-incorrect": "ci",
             "incorrect": "wrong", "defective row": "def"}
    print("\n── Per group, baseline -> this run "
          "(ok = correct, cl = clarify, ci = clarify-incorrect) ──")
    for group, _, _ in GROUPS:
        rows_b = [r for r in before if r["question_group"] == group]
        rows_a = [r for r in after if r["question_group"] == group]
        cb, ca = _counts(rows_b), _counts(rows_a)
        cells = "  ".join(f"{short[o]} {cb[o]:>2}->{ca[o]:<2}" for o in OUTCOMES[:4])
        print(f"  {group[:40]:<40} n={len(rows_a):<3} {cells}")
    moved = [(n, b_by[n]["outcome"], a_by[n]["outcome"]) for n in sorted(a_by)
             if n in b_by and b_by[n]["outcome"] != a_by[n]["outcome"]]
    print(f"\n── Rows that moved — {len(moved)} ──")
    for n, was, now in moved:
        row = a_by[n]
        print(f"  #{n:<4} {was:>17} -> {now:<17} {row['served_template_id'] or '-':<8} "
              f"{row['question'][:60]}")


def clarification_reasons(path: Path) -> None:
    """How the run asked, and every `unbound_subject` question in full (T7.4)."""
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    asked = [r for r in records if r.get("clarification")]
    reasons = Counter(r["clarification"].get("reason") for r in asked)
    print("\n── Clarifications by reason ──")
    for reason, count in reasons.most_common():
        print(f"  {str(reason):<22} {count}")
    unbound = [r for r in asked if r["clarification"].get("reason") == "unbound_subject"]
    print(f"\n── unbound_subject clarifications — {len(unbound)} ──")
    for r in unbound:
        chips = ", ".join(o.get("label", "") for o in r["clarification"].get("options") or [])
        print(f"  #{r['n']:<4} {r['q'][:70]}")
        print(f"        asked: {r['clarification'].get('prompt')}  [{chips}]")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", type=Path, help="run_custom_eval.py output (.jsonl)")
    ap.add_argument("--out", type=Path, help="write the graded CSV here")
    ap.add_argument("--baseline", type=Path,
                    help="a graded CSV to diff against (e.g. WP6_eval1_replay.csv)")
    args = ap.parse_args()

    rows = grade_file(args.results)
    if args.out:
        write_graded(rows, args.out)
        print(f"wrote {args.out} ({len(rows)} rows)")
    if args.baseline:
        before = read_graded(args.baseline)
        headline(before, f"baseline {args.baseline.name}")
        headline(rows, f"this run {args.results.name}")
        movement(before, rows)
    else:
        headline(rows, args.results.name)
    clarification_reasons(args.results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

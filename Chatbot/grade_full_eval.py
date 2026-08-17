"""
Grade eval_full_results.jsonl.

Buckets per question:
  hit                   answered with the gold (or acceptable) template, or
                        declined with the gold known-unanswerable
  partial               partial-row: clarified/missed but the gold question was
                        offered as a chip
  clarify               router asked a question instead of answering
  wrong_template        answered, but with a template outside the gold set
  wrong_direction       answered with the RIGHT template and the wrong sign — the
                        paired-year slots arrived inverted (D30.3); see below
  wrong_refusal         declined with a documented reason, but the WRONG one
  declined_generically  declined without retrieving the documented refusal —
                        right outcome, wrong reason
  refusal_with_rows     a served refusal carried a result set; see below
  fallback              no answer, no useful clarification
  error                 HTTP/exception
  new                   unlabelled question -- listed for manual judgement

REFUSALS ARE GRADED ON THEIR REASON (WP-4 T3). The 19 known-unanswerable gold
rows name the UNANSWERABLE_CATALOG id rather than `no_match`, because "the
database cannot answer this, and here is the workbook's own reason" is a
different outcome from "nothing matched" — which is exactly the distinction
unanswerable_catalog exists to make, and which `no_match` collapses.

An honest refusal leaves `result` as None, NEVER an empty list. If one ever
sets n_rows the row lands in `refusal_with_rows` rather than being silently
mis-bucketed — the single coupling that would flip all 19 rows at once. WP-5's
gates file asserts the same thing (WP-4a §5).

A RIGHT TEMPLATE CAN STILL BE A WRONG ANSWER (D30.3, WP-4c T3b). Five templates
carry both `$date_range` and `$date_range_2`; `$date_range_2` is year1 and three
of them compute `$date_range - $date_range_2`. Swap the pair and PLN-039 answers
"which themes showed the greatest INCREASE" with the greatest decline — right
query_id, right row count, plausible table, inverted sign. This grader used to
call that a `hit`, and did: in all three WP-4 replays every paired row arrived
with `date_range=2023-2024, date_range_2=2024-2025` and scored clean. Gold rows
for those five now carry `expected_result.direction_pin`, and a row whose first
returned row contradicts its pin lands in `wrong_direction` instead. This is the
only check in the harness that reads a VALUE rather than a route, and it is here
because that is the only place the defect is visible.
"""
import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from query_router.template_catalog import TEMPLATE_CATALOG  # noqa: E402
from query_router.dashboard_catalog import DASHBOARD_CATALOG  # noqa: E402
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG  # noqa: E402

# The tiers main.py ACTUALLY puts in the response. RouteTier's values are
# "tier1"/"tier2" and the operation path sets the literal "operation"; the AP
# build tested for "tier1_dashboard"/"tier2_template", which are the ENUM MEMBER
# names, not the values. That first clause was therefore always false for a
# template answer and grading survived only on the `n_rows is not None`
# fallback — so a template answer that legitimately returns NO rows was
# misgraded (WP-4a §6.4). 21 of the 346 templates return zero rows by design.
ANSWER_TIERS = ("tier1", "tier2", "operation")

# question text -> query_id, to map clarify chips back to templates
Q_TO_ID = {}
for qid, t in TEMPLATE_CATALOG.items():
    Q_TO_ID[t["abstract_question"].strip().lower()] = qid
for qid, d in DASHBOARD_CATALOG.items():
    Q_TO_ID[d["question"].strip().lower()] = qid

import re

def chip_ids(rec):
    ids = []
    clar = rec.get("clarification") or {}
    for o in clar.get("options") or []:
        label = (o.get("label") or "").strip().lower()
        if label in Q_TO_ID:
            ids.append(Q_TO_ID[label])
            continue
        # chips may have slots pre-filled; try matching with braces wildcarded
        for q, qid in Q_TO_ID.items():
            if "{" in q:
                pat = re.escape(q)
                pat = re.sub(r"\\\{\w+\\\}", ".+", pat)
                if re.fullmatch(pat, label):
                    ids.append(qid)
                    break
    return ids


# Direction pins, keyed by question number. Read from the built spec file rather
# than required on the result record, so WP-4's existing replays can be re-graded
# against the pins without being re-run. `run_full_eval` also copies the pin onto
# each record it writes, which is what makes a results file self-contained.
def _load_direction_pins() -> dict:
    path = HERE / "eval_questions_full.json"
    try:
        specs = json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                        # pragma: no cover
        return {}
    return {spec["n"]: pin for spec in specs
            if (pin := (spec.get("expected_result") or {}).get("direction_pin"))}


PIN_BY_N = _load_direction_pins()


def _as_number(value):
    """The harness serialises Decimals with `default=str`, so a money column
    arrives as "5550255.00". Compare numerically or the pin never matches."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def direction_verdict(rec):
    """None (nothing to check / it holds) or a one-line description of the break.

    Checked against the FIRST returned row, which is the one the pin was computed
    for: every paired template has a deterministic ORDER BY, and `rows_sample`
    keeps the first three rows. A run that returned nothing to look at is not
    evidence of a direction error, so it is left to the ordinary buckets.
    """
    pin = rec.get("gold_direction_pin") or PIN_BY_N.get(rec.get("n"))
    if not pin:
        return None
    sample = rec.get("rows_sample") or []
    if not sample or not isinstance(sample[0], dict):
        return None
    row, expected = sample[0], pin.get("first_row") or {}
    breaks = []
    for column, want in expected.items():
        got = row.get(column)
        if column not in row:
            breaks.append(f"{column} missing")
            continue
        if isinstance(want, str):
            if str(got).strip() != want.strip():
                breaks.append(f"{column}={got!r} (pinned {want!r})")
            continue
        got_n, want_n = _as_number(got), _as_number(want)
        if got_n is None or abs(got_n - want_n) > max(0.01, abs(want_n) * 1e-6):
            breaks.append(f"{column}={got} (pinned {want})")
    if not breaks:
        return None
    inverted = all(
        _as_number(row.get(a)) is not None
        and _as_number(row.get(a)) == _as_number(expected.get(b))
        for a, b in (("activities_year1", "activities_year2"),
                     ("activities_year2", "activities_year1"))
        if a in expected and b in expected)
    lead = ("the paired years arrived INVERTED: " if inverted else "")
    return lead + "; ".join(breaks)


def grade(rec):
    if rec.get("error"):
        return "error"
    gold = rec.get("gold")
    ok = {gold, *(rec.get("acc") or [])} if gold else set()
    qid = rec.get("query_id")
    tier = rec.get("tier")
    clar = rec.get("clarification")

    if gold is None:
        return "new"

    if rec.get("excluded"):
        return "excluded"

    # A SERVED REFUSAL is not an answer and must not be graded as one. The
    # router retrieves a known-unanswerable, returns its query_id and leaves
    # `result` as None — so it arrives here with a query_id and a fallback tier.
    # Checked BEFORE the answer branch, because a refusal that ever set n_rows
    # would otherwise be read as a template answer whose id is not a template.
    if qid in UNANSWERABLE_CATALOG:
        if rec.get("n_rows") is not None:
            # The one coupling that silently flips every unanswerable row to
            # wrong_template (WP-4a §5, destined for WP-5's gates). An honest
            # refusal has NO result set — not an empty one.
            return "refusal_with_rows"
        return "hit" if qid in ok else "wrong_refusal"

    if qid and tier in ANSWER_TIERS or (qid and rec.get("n_rows") is not None):
        if qid not in ok:
            return "wrong_template"
        # Right template, and now: right direction? Only the five paired-year
        # templates carry a pin, so this is a no-op for every other row.
        broken = direction_verdict(rec)
        if broken:
            rec["direction_break"] = broken
            return "wrong_direction"
        return "hit"

    # no direct answer
    offered = set(chip_ids(rec))
    if gold == "no_match":
        return "hit"  # gold behaviour IS declining
    if gold in UNANSWERABLE_CATALOG:
        # Gold names a documented refusal and the router declined WITHOUT
        # retrieving it — right outcome, wrong reason. Distinguishable on
        # purpose: that is the whole point of the T3 upgrade.
        return "declined_generically"
    if offered & ok:
        return "partial" if rec.get("partial") else "clarify_gold_offered"
    if clar:
        return "clarify"
    return "fallback"


def main():
    # The replay to grade. WP-4 T5c runs the full eval three times and the
    # triage rule is that no failure counts as a regression unless it appears in
    # at least 2 of 3 — which means grading each replay, not just the last one
    # to overwrite the default file.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", type=Path,
                    default=HERE / "eval_full_results.jsonl")
    ap.add_argument("--out", dest="out_path", type=Path, default=None)
    args = ap.parse_args()
    out_path = args.out_path or args.in_path.with_name(
        args.in_path.stem.replace("results", "graded") + ".json")

    recs = [json.loads(l) for l in
            args.in_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    buckets = {}
    for r in recs:
        v = grade(r)
        r["verdict"] = v
        buckets.setdefault(v, []).append(r)

    print(f"{args.in_path.name}: total {len(recs)}")
    for k in ("hit", "partial", "clarify_gold_offered", "clarify", "wrong_template",
              "wrong_direction", "wrong_refusal", "declined_generically",
              "refusal_with_rows", "fallback", "error", "excluded", "new"):
        if k in buckets:
            print(f"  {k:<22} {len(buckets[k])}")

    for k in ("wrong_template", "wrong_direction", "wrong_refusal",
              "declined_generically", "refusal_with_rows", "clarify",
              "clarify_gold_offered", "partial", "fallback", "error"):
        for r in buckets.get(k, []):
            extra = ""
            if k in ("wrong_template", "wrong_refusal"):
                extra = f" gold={r['gold']} picked={r['query_id']}"
            elif k == "wrong_direction":
                extra = (f" gold={r['gold']} — RIGHT template, WRONG sign: "
                         f"{r.get('direction_break')}")
            elif k == "declined_generically":
                extra = f" gold={r['gold']} (refusal not retrieved)"
            elif k == "refusal_with_rows":
                extra = (f" gold={r['gold']} n_rows={r.get('n_rows')} — a served "
                         f"refusal must leave result as None, never []")
            elif k in ("clarify", "clarify_gold_offered", "partial"):
                clar = r.get("clarification") or {}
                extra = f" gold={r.get('gold')} reason={clar.get('reason')} prompt={clar.get('prompt','')[:60]!r}"
            elif k == "error":
                extra = " " + (r.get("error") or "")[:100]
            print(f"[{k}] #{r['n']} {r['q'][:66]}{extra}")

    print("\n── NEW questions (manual judgement) ──")
    for r in buckets.get("new", []):
        clar = r.get("clarification") or {}
        rows = r.get("rows_sample")
        print(f"#{r['n']:>2} {r['q'][:70]}")
        print(f"    tier={r.get('tier')} qid={r.get('query_id')} n_rows={r.get('n_rows')} "
              f"desc={ (r.get('query_description') or '')[:80]!r}")
        if clar:
            print(f"    clarify[{clar.get('reason')}]: {clar.get('prompt','')[:90]!r}")
            for o in (clar.get("options") or [])[:4]:
                print(f"      chip: {(o.get('label') or '')[:80]}")
        if rows:
            print(f"    rows: {json.dumps(rows, ensure_ascii=False, default=str)[:220]}")

    out_path.write_text(
        json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

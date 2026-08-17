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
  wrong_entities        answered with the RIGHT template and a slot bound to a
                        value the gold contradicts; see below
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


def _load_specs() -> dict:
    """The built gold specs by question number, or {} if unreadable."""
    path = HERE / "eval_questions_full.json"
    try:
        return {spec["n"]: spec
                for spec in json.loads(path.read_text(encoding="utf-8"))}
    except Exception:                                        # pragma: no cover
        return {}


SPEC_BY_N = _load_specs()
EXPECTED_ENTITIES_BY_N = {n: s["expected_entities"] for n, s in SPEC_BY_N.items()
                          if s.get("expected_entities")}


def acceptable_ids(rec):
    """The ids that count as right for this question.

    THE GOLD SET WINS over the copy `run_full_eval` wrote onto the record, for the
    same reason it wins on direction pins: the spec file is where the contract is
    maintained, so a corrected `acc` applies to replays already on disk instead of
    requiring 211 questions to be re-run. `read_records` has already checked that
    the results file and the spec file describe the same question set.
    """
    spec = SPEC_BY_N.get(rec.get("n")) or {}
    gold = spec.get("gold", rec.get("gold"))
    acc = spec.get("acc", rec.get("acc")) or []
    return gold, {gold, *acc} if gold else set()


def entity_contradictions(rec):
    """Slots the run BOUND to something the gold says is a different value.

    CONTRADICTIONS ONLY, never absences. A slot the router left unbound is
    already visible — the question clarifies, or an optional filter is off and
    the echo says so. A slot bound to the WRONG value is the invisible case: the
    query_id is right, the table looks normal, and the eval calls it a hit.

    Measured on WP-4c's replay 1 this fires on exactly one row in 211, and that
    row was graded `hit`: #1016 "what about last year?" over a 2024-2025 answer
    kept 2024-2025 and echoed it as the year asked for. The gold row says
    2023-2024 in as many words ("swap $date_range to known[-2]"). One
    false-positive-free check for one real silent wrong answer is a good trade;
    the same reasoning as the direction pins (D30.3), one layer up.
    """
    want = EXPECTED_ENTITIES_BY_N.get(rec.get("n")) or {}
    if not want:
        return []
    got = {e["slot"]: str(e["value"]) for e in (rec.get("entities") or [])
           if isinstance(e, dict) and "slot" in e}
    return [f"{slot}={got[slot]!r} but the gold says {str(value)!r}"
            for slot, value in want.items()
            if slot in got and got[slot] != str(value)]


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


def read_records(path, allow_subset=False):
    """The replay's records, repairing split lines and duplicated writes.

    WHY THIS IS NOT PARANOIA. The repo lives in a Google Drive folder (D6), and
    `run_full_eval` appends one JSON line per question and flushes each time. In
    WP-4c's replay 1 the sync layer left a record split across two lines and one
    record written twice — 213 lines for 211 questions, with a fragment in the
    middle:

        {"n": 1984, …            <- truncated
        mple": null, "date_range"…  <- the rest of it
        {"n": 1984, …            <- and then the whole record again

    A `json.loads` per line dies on the fragment. Skipping the bad line silently
    is the worse failure, though: it drops a question from the denominator and
    reports the result as if the whole set had run.

    So: split lines are rejoined where the halves are adjacent, records are
    deduplicated by `n` keeping the last complete one, leftover fragments are
    dropped — and every repair is PRINTED. Then the recovered `n`s are checked
    against `eval_questions_full.json`, and a genuinely missing question raises
    rather than being graded around. In WP-4c's replay 1 the orphan turned out to
    be a redundant copy of a record that was also present in full, so nothing was
    lost; that is a conclusion the check earns rather than assumes.
    """
    lines = [l for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]
    records, rejoined, orphans, i = [], 0, 0, 0
    while i < len(lines):
        try:
            records.append(json.loads(lines[i]))
            i += 1
            continue
        except json.JSONDecodeError:
            pass
        # A record split across two adjacent lines: head + tail.
        if i + 1 < len(lines):
            try:
                records.append(json.loads(lines[i] + lines[i + 1]))
                rejoined += 1
                i += 2
                continue
            except json.JSONDecodeError:
                pass
        orphans += 1
        i += 1

    by_n, duplicated = {}, 0
    for rec in records:
        if rec["n"] in by_n:
            duplicated += 1
        by_n[rec["n"]] = rec

    if rejoined or duplicated or orphans:
        print(f"  {path.name}: {len(lines)} lines -> {len(by_n)} questions "
              f"(rejoined {rejoined} split, dropped {duplicated} duplicate "
              f"write(s) and {orphans} orphan fragment(s) — Drive sync artefact, "
              f"see read_records)")
    expected = {spec["n"] for spec in json.loads(
        (HERE / "eval_questions_full.json").read_text(encoding="utf-8"))}
    missing = sorted(expected - set(by_n))
    if missing and not allow_subset:
        raise ValueError(
            f"{path.name}: {len(missing)} question(s) have no recoverable record "
            f"({missing[:10]}). Grading a subset and reporting it as the whole "
            f"set is how an accuracy figure lies; re-run the replay, or pass "
            f"--allow-subset if this replay predates the current gold set.")
    if missing:
        print(f"  SUBSET: {len(missing)} question(s) in the current gold set were "
              f"not in this replay ({missing[:10]}) — percentages below are over "
              f"{len(by_n)} questions, not {len(expected)}. This is the flag you "
              f"asked for; it is not a clean comparison.")
    return list(by_n.values())


def _matches(row, pinned):
    """True when every pinned column is present in `row` and equal to it."""
    if not pinned:
        return False
    for column, want in pinned.items():
        if column not in row:
            return False
        if isinstance(want, str):
            if str(row[column]).strip() != want.strip():
                return False
            continue
        got_n, want_n = _as_number(row[column]), _as_number(want)
        if got_n is None or abs(got_n - want_n) > max(0.01, abs(want_n) * 1e-6):
            return False
    return True


def _sign(value):
    return 0 if value is None or abs(value) < 1e-9 else (1 if value > 0 else -1)


def _year_column_pairs(pin):
    """[(year1_column, year2_column)] from the pin's year_columns mapping.

    `activities_year1` -> date_range_2 and `activities_year2` -> date_range makes
    one pair; TRD-001 and TRD-002 declare two pairs each.
    """
    by_stem = {}
    for column, slot in (pin.get("year_columns") or {}).items():
        stem = re.sub(r"_year[12]$", "", column)
        by_stem.setdefault(stem, {})[slot] = column
    return [(cols["date_range_2"], cols["date_range"])
            for cols in by_stem.values()
            if {"date_range_2", "date_range"} <= set(cols)]


def direction_verdict(rec):
    """None (nothing to check / it holds) or a one-line description of the break.

    IT CHECKS DIRECTION, NOT MAGNITUDE, and the distinction is load-bearing. The
    obvious implementation — compare the returned row to the pinned row value by
    value — reports a break whenever anything else about the query differed, and
    the most likely "anything else" is a geography slot that did not bind: TRD-004
    is pinned for Bhubaneswar block, so an unbound block gives state-wide figures
    that match nothing. That is a SCOPE defect, which the ordinary buckets and the
    echo already surface, and calling it a sign inversion would be a worse error
    than the one this exists to catch.

    So two scale-free properties are tested, both of them exactly what an
    inverted `$date_range`/`$date_range_2` pair breaks:

      * every change column carries the sign the pin says it does;
      * for each year1/year2 column pair, the change BETWEEN the two years runs in
        the pinned direction.

    Exact values are pinned too, but where they belong: in
    `tests/test_paired_year_direction.py`, which executes the SQL with the pinned
    parameters and can therefore demand equality.

    Checked against the FIRST returned row — every paired template has a
    deterministic ORDER BY and `rows_sample` keeps the first three. A run with no
    rows to look at is not evidence of a direction error and is left alone.
    """
    # THE GOLD SET WINS over the copy on the record. The record's copy makes a
    # results file self-describing, but the built spec file is where the contract
    # is maintained — so re-grading an older replay applies the CURRENT pin, which
    # is how WP-4's three replays were shown to have been serving an inverted pair
    # all along while grading clean.
    pin = PIN_BY_N.get(rec.get("n")) or rec.get("gold_direction_pin")
    if not pin:
        return None
    sample = rec.get("rows_sample") or []
    if not sample or not isinstance(sample[0], dict):
        return None
    row, expected = sample[0], pin.get("first_row") or {}
    breaks = []

    # POSITIVE IDENTIFICATION FIRST, because it is the only test that catches
    # PLN-039 and PLN-040. Their ORDER BY is on the change column, so under an
    # inverted pair the top row is still a POSITIVE change for "greatest
    # increase" — it is simply a different theme, the one that actually declined
    # most. Every sign and direction test passes; the answer is still backwards.
    # `inverted_row` is what the template returns with the two years exchanged
    # (computed with the pin, asserted by test_paired_year_direction), so matching
    # it is not a heuristic: it says the pair arrived swapped, and a scope slot
    # that failed to bind cannot reproduce those exact figures.
    inverted = pin.get("inverted_row") or {}
    if inverted and _matches(row, inverted) and not _matches(row, expected):
        return ("the paired years arrived INVERTED — the row returned is exactly "
                "what this template gives with $date_range and $date_range_2 "
                f"exchanged: {json.dumps(inverted, default=str)[:200]}")

    for column, want in expected.items():
        if not column.startswith("change") or column not in row:
            continue
        want_sign, got_sign = _sign(_as_number(want)), _sign(_as_number(row[column]))
        if want_sign and got_sign and want_sign != got_sign:
            breaks.append(f"{column}={row[column]} but the pin says it is "
                          f"{'positive' if want_sign > 0 else 'negative'} "
                          f"({want})")

    for earlier, later in _year_column_pairs(pin):
        if not {earlier, later} <= set(row) or not {earlier, later} <= set(expected):
            continue
        want_sign = _sign(_as_number(expected[later]) - _as_number(expected[earlier]))
        got_sign = _sign(_as_number(row[later]) - _as_number(row[earlier]))
        if want_sign and got_sign and want_sign != got_sign:
            breaks.append(
                f"{earlier}={row[earlier]} {later}={row[later]} run "
                f"{'up' if got_sign > 0 else 'down'} where the pin runs "
                f"{'up' if want_sign > 0 else 'down'} "
                f"({expected[earlier]} -> {expected[later]}) — the paired years "
                f"look INVERTED")
    return "; ".join(breaks) or None


def grade(rec):
    if rec.get("error"):
        return "error"
    gold, ok = acceptable_ids(rec)
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
        # Right template, right direction — and the right values? A bound value
        # that contradicts the gold is the same class of defect one layer up.
        contradictions = entity_contradictions(rec)
        if contradictions:
            rec["entity_contradictions"] = contradictions
            return "wrong_entities"
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
    ap.add_argument("--allow-subset", action="store_true",
                    help="grade a replay that predates the current gold set, "
                         "reporting over the questions it actually contains")
    args = ap.parse_args()
    out_path = args.out_path or args.in_path.with_name(
        args.in_path.stem.replace("results", "graded") + ".json")

    recs = read_records(args.in_path, allow_subset=args.allow_subset)
    buckets = {}
    for r in recs:
        v = grade(r)
        r["verdict"] = v
        buckets.setdefault(v, []).append(r)

    print(f"{args.in_path.name}: total {len(recs)}")
    for k in ("hit", "partial", "clarify_gold_offered", "clarify", "wrong_template",
              "wrong_direction", "wrong_entities", "wrong_refusal",
              "declined_generically", "refusal_with_rows", "fallback", "error",
              "excluded", "new"):
        if k in buckets:
            print(f"  {k:<22} {len(buckets[k])}")

    for k in ("wrong_template", "wrong_direction", "wrong_entities",
              "wrong_refusal", "declined_generically", "refusal_with_rows",
              "clarify", "clarify_gold_offered", "partial", "fallback", "error"):
        for r in buckets.get(k, []):
            extra = ""
            if k in ("wrong_template", "wrong_refusal"):
                extra = f" gold={r['gold']} picked={r['query_id']}"
            elif k == "wrong_entities":
                extra = (f" gold={r['gold']} — RIGHT template, WRONG value: "
                         f"{'; '.join(r.get('entity_contradictions') or [])}")
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

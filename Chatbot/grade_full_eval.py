"""
Grade eval_full_results.jsonl.

Buckets per question:
  hit             answered with the gold (or acceptable) template
  partial         partial-row: clarified/missed but the gold question was offered as a chip
  clarify         router asked a question instead of answering (chips/prompt recorded)
  wrong_template  answered, but with a template outside the gold set
  fallback        no answer, no useful clarification
  error           HTTP/exception
  new             unlabelled question -- listed for manual judgement
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

    if qid and tier in ("tier1_dashboard", "tier2_template", "operation") or (
        qid and rec.get("n_rows") is not None
    ):
        return "hit" if qid in ok else "wrong_template"

    # no direct answer
    offered = set(chip_ids(rec))
    if gold == "no_match":
        return "hit"  # gold behaviour IS declining
    if offered & ok:
        return "partial" if rec.get("partial") else "clarify_gold_offered"
    if clar:
        return "clarify"
    return "fallback"


def main():
    recs = [json.loads(l) for l in
            (HERE / "eval_full_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    buckets = {}
    for r in recs:
        v = grade(r)
        r["verdict"] = v
        buckets.setdefault(v, []).append(r)

    print(f"total: {len(recs)}")
    for k in ("hit", "partial", "clarify_gold_offered", "clarify", "wrong_template",
              "fallback", "error", "excluded", "new"):
        if k in buckets:
            print(f"  {k:<22} {len(buckets[k])}")

    for k in ("wrong_template", "clarify", "clarify_gold_offered", "partial", "fallback", "error"):
        for r in buckets.get(k, []):
            extra = ""
            if k == "wrong_template":
                extra = f" gold={r['gold']} picked={r['query_id']}"
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

    (HERE / "eval_full_graded.json").write_text(
        json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

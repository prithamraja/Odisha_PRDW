"""
Routing regression eval for the template-direct path (retrieve -> rerank).

Replays the WP-4a gold set through exactly the pipeline router._route_vector
uses -- normalize() -> retriever.retrieve_scored(q, VECTOR_TOP_K) -> zone() ->
rerank() -- and scores the picked query_id against the gold label.

It stops at the routing decision: no entity extraction, no SQL, no database.
That is the point -- it isolates the reranker so a description change can be
measured without data or binding noise. One run costs one query embedding plus
one rerank call per row; catalog embeddings come from the .tmp cache.

  cd Chatbot
  python rerank_eval.py --out ../eval_baseline.json --yes
  python rerank_eval.py --out ../eval_after.json --yes
  python rerank_eval.py --compare ../eval_baseline.json ../eval_after.json

THE GOLD SET IS THE REPO'S, NOT AP'S (WP-4 T4d). This harness previously carried
79 hand-labelled AP questions in a `GOLD_RAW` docstring block -- PM-KISAN
farmers, eKYC status, MARKFED procurement -- scored against query_ids
(`Q001`, `F09`, `G03-S`) that no longer exist in this catalogue. Every row
would have missed, and the number meant nothing. Rows now come from
`eval/gold/*.jsonl`, the same source `run_full_eval` and `recall_eval` read, so
the three harnesses cannot disagree about what the right answer is.

WHICH ROWS. Everything with a retrieval target, which is everything except the
FOLLOW-UP FRAGMENTS: "and Khajuripada?" has no subject of its own and only means
something with the previous question's frame on screen, which this harness
deliberately does not have. Known-unanswerables ARE included -- they are in the
retrieval index on purpose, so "did the router retrieve the right documented
refusal?" is a reranker question like any other -- and so are the out-of-domain
rows, whose gold is `no_match`.

Verdicts:
  hit       picked == gold, or picked is in the row's `acc` list
  partial   row marked `partial` (a clarification IS the right answer) and the
            router either picked an acceptable id or returned no_match with the
            gold id among its near-misses
  miss      anything else
  excluded  rows marked `excluded` in the gold set -- reported, not scored
"""
import os
import io
import sys
import json
import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openai import OpenAI

from query_router.config import VECTOR_TOP_K
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.preprocessor import normalize
from query_router.reranker import rerank
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
from query_router.vector_retriever import VectorRetriever
from query_router.llm_usage import meter
from eval_spend import confirm_spend
from query_router.zones import zone

# ── Gold set — eval/gold/*.jsonl, via the same reader the builder uses ────────

GOLD_DIR = Path(__file__).resolve().parent.parent / "eval" / "gold"

# A fragment has no subject of its own; scoring it without its frame measures
# the failure this harness cannot reproduce rather than the reranker.
_NO_RETRIEVAL_TARGET = {"followup"}


def load_gold() -> list[dict]:
    """The gold rows that have something for retrieval to find.

    Read straight off the JSONL rather than through `eval_questions_full.json`,
    so a stale build of that file cannot silently change what this measures.
    """
    rows = []
    for path in sorted(GOLD_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("case_type") in _NO_RETRIEVAL_TARGET:
                continue
            rows.append({
                "id": rec["id"],
                "question": rec["q"],
                "gold": rec["gold"],
                "acceptable": list(rec.get("acc") or []),
                "note": rec.get("notes", ""),
                "partial": bool(rec.get("partial")),
                "excluded": bool(rec.get("excluded")),
            })
    return rows


def score_row(row: dict, picked: str, near_misses: list[str]) -> str:
    ok = {row["gold"], *row["acceptable"]}
    if row["excluded"]:
        # The gold IS no_match here; a clarify carrying either near-miss is the
        # good outcome, but the row never counts toward accuracy either way.
        return "excluded"
    if picked in ok:
        return "hit"
    if row["partial"] and picked == "no_match" and any(m in ok for m in near_misses):
        return "partial"
    return "miss"


def run(out_path: Path | None, limit: int | None) -> dict:
    meter().reset()                     # D28.8 — per-run totals, not cumulative
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # The unanswerables are indexed here for the same reason main.py indexes
    # them: 19 gold rows expect a DOCUMENTED refusal, and an entry that is not
    # in the index can never be retrieved, let alone reranked.
    retriever = VectorRetriever(client, DASHBOARD_CATALOG, TEMPLATE_CATALOG,
                                UNANSWERABLE_CATALOG)
    gold = load_gold()
    if limit:
        gold = gold[:limit]

    results = []
    for i, row in enumerate(gold, 1):
        normalized = normalize(row["question"])
        scored = retriever.retrieve_scored(normalized, VECTOR_TOP_K)
        score_zone = zone([s for _, _, s in scored])
        candidates = [(qid, q) for qid, q, _ in scored]
        picked, near_misses = rerank(row["question"], candidates, client)

        ranked_ids = [qid for qid, _, _ in scored]
        gold_rank = ranked_ids.index(row["gold"]) if row["gold"] in ranked_ids else None
        verdict = score_row(row, picked, near_misses)

        results.append({
            "id": row["id"],
            "question": row["question"],
            "gold": row["gold"],
            "acceptable": row["acceptable"],
            "partial": row["partial"],
            "excluded": row["excluded"],
            "note": row["note"],
            "picked": picked,
            "near_misses": near_misses,
            "zone": score_zone,
            "top_score": round(scored[0][2], 4) if scored else None,
            "gold_retrieval_rank": gold_rank,
            "verdict": verdict,
        })
        print(f"[{i:>2}/{len(gold)}] {verdict:<8} gold={row['gold']:<6} "
              f"picked={picked:<9} zone={score_zone:<9} {row['question'][:62]}")

    scored_rows = [r for r in results if r["verdict"] != "excluded"]
    hits = sum(1 for r in scored_rows if r["verdict"] in ("hit", "partial"))
    summary = {
        "n_total": len(results),
        "n_scored": len(scored_rows),
        "n_hit": sum(1 for r in scored_rows if r["verdict"] == "hit"),
        "n_partial": sum(1 for r in scored_rows if r["verdict"] == "partial"),
        "n_miss": sum(1 for r in scored_rows if r["verdict"] == "miss"),
        "n_excluded": len(results) - len(scored_rows),
        "accuracy": round(hits / len(scored_rows), 4) if scored_rows else 0.0,
    }

    print("\n── Summary ──")
    for k, v in summary.items():
        print(f"  {k:<12} {v}")
    print("\n── Misses ──")
    for r in results:
        if r["verdict"] == "miss":
            print(f"  gold={r['gold']:<6} picked={r['picked']:<9} "
                  f"rank={r['gold_retrieval_rank']} {r['question'][:70]}")

    # Recorded IN the payload, so an A/B comparison can price the two arms as
    # well as score them — which is the whole question in T5's transliteration
    # vs paraphrase-index choice.
    print(meter().report("rerank_eval: token spend"))
    payload = {"summary": summary, "usage": meter().snapshot(), "results": results}
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"\nWrote {out_path}")
    return payload


def compare(before_path: Path, after_path: Path) -> None:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    b_by_q = {r["question"]: r for r in before["results"]}

    print(f"accuracy: {before['summary']['accuracy']:.1%} -> {after['summary']['accuracy']:.1%}")
    fixed, regressed, still = [], [], []
    for r in after["results"]:
        b = b_by_q.get(r["question"])
        if b is None:
            continue
        b_ok = b["verdict"] in ("hit", "partial")
        a_ok = r["verdict"] in ("hit", "partial")
        if a_ok and not b_ok:
            fixed.append((r, b))
        elif b_ok and not a_ok:
            regressed.append((r, b))
        elif not a_ok and not b_ok:
            still.append((r, b))

    print(f"\n── Fixed ({len(fixed)}) ──")
    for r, b in fixed:
        print(f"  {b['picked']:>9} -> {r['picked']:<9} gold={r['gold']:<6} {r['question'][:64]}")
    print(f"\n── REGRESSED ({len(regressed)}) ──")
    for r, b in regressed:
        print(f"  {b['picked']:>9} -> {r['picked']:<9} gold={r['gold']:<6} {r['question'][:64]}")
    print(f"\n── Still missing ({len(still)}) ──")
    for r, b in still:
        print(f"  {b['picked']:>9} -> {r['picked']:<9} gold={r['gold']:<6} {r['question'][:64]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="write per-row results JSON here")
    ap.add_argument("--limit", type=int, help="only run the first N questions")
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
        return

    n = len(load_gold()[:args.limit] if args.limit else load_gold())
    confirm_spend(
        "rerank_eval",
        [("catalogue embedding index (cached after the first build)", 1),
         (f"per row: 1 embed + 1 rerank x {n}", 2 * n)],
        confirmed=args.yes,
    )
    run(args.out, args.limit)


if __name__ == "__main__":
    main()

"""
Routing regression eval for the template-direct path (retrieve -> rerank).

Replays the 79 hand-labelled sample questions of AP_ASK_RERANK_HANDOFF.md
Appendix A through exactly the pipeline router._route_vector uses --
normalize() -> retriever.retrieve_scored(q, VECTOR_TOP_K) -> zone() -> rerank() --
and scores the picked query_id against the gold label.

It stops at the routing decision: no entity extraction, no SQL, no database.
That is the point -- it isolates the reranker so a description change can be
measured without data or binding noise. One run costs 79 query embeddings plus
79 rerank calls; catalog embeddings come from the .tmp cache.

  cd Chatbot/backend
  python rerank_eval.py --out ../../eval_baseline.json
  python rerank_eval.py --out ../../eval_after.json
  python rerank_eval.py --compare ../../eval_baseline.json ../../eval_after.json

Verdicts:
  hit       picked == gold, or picked is in the row's also_acceptable list
  partial   row marked `partial` (the catalog can only approximate it) and the
            router either picked an acceptable id or returned no_match with the
            gold id among its clarify chips
  miss      anything else
  excluded  rows whose gold is a known catalog gap -- reported, not scored
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
from query_router.vector_retriever import VectorRetriever
from query_router.zones import zone

# ── Gold set — Appendix A of AP_ASK_RERANK_HANDOFF.md ─────────────────────────
# question | gold | also_acceptable | note      ("partial" in the note marks a
# row the catalog can only approximate; see the module docstring.)
GOLD_RAW = """
How many beneficiaries are registered in PM-KISAN? | Q001 | M01 |
What is the eKYC status of Ramesh Naidu? | F01 | |
Which farmers have eKYC still pending? | V05 | |
Whose beneficiary status is Pending (not yet Included)? | V06 | |
What is the total cultivable area (hectares) of all PM-KISAN beneficiaries? | G03-S | M01 |
When was the last installment paid to Lakshmi Devi, and how much? | F01 | |
Give the category (caste) breakdown of PM-KISAN beneficiaries. | G04-S | |
How many male vs female beneficiaries? | G05-S | |
Who has the largest landholding in PM-KISAN? | R01 | |
How many distinct districts do beneficiaries come from? | M01 | G01-S, Q017 |
Which crop did Ramesh Naidu take input subsidy for, and in which season? | F02 | |
Who received the highest input subsidy and how much? | R02 | |
List farmers who took subsidy in the Rabi season. | V01 | |
What is the total subsidy amount disbursed? | M01 | G10-S |
Which district received the highest single input subsidy? | R04 | |
What is the district code (dcode) for Guntur in the data? | M03 | |
What is the average input subsidy per farmer? | Q056 | M01 |
Is Ramesh Naidu a horticulture (APMIP) beneficiary? | F03 | |
What micro-irrigation subsidy amount did Venkateswarlu G avail? | F03 | |
What is the land EXTENT recorded for Suresh Reddy in horticulture? | F03 | |
How many horticulture beneficiaries are there? | Q147 | G21-S |
Which farmers are registered in Fisheries? | S07 | G25-S |
Does Padma Sri appear in the Fisheries data? | F04 | |
How much was paid (amount_paid) to Lakshmi Devi in Fisheries? | F04 | |
What cocoon quantity is recorded for Ramesh Naidu? | F05 | |
Which PM-KISAN farmers are NOT in Sericulture? | S01 | S02 |
What is the net incentive for Padma Sri? | F05 | |
Which crop did MARKFED procure from Nagaraju P? | F06 | |
Who received the highest MARKFED payment? | R03 | |
Are all 10 PM-KISAN farmers present in MARKFED? | S01 | | wording predates the 1,100-farmer drop
Is Mohan Rao an RySS (natural farming) member? | F07 | |
What ACREAGE is recorded for Suresh Reddy in RySS? | F07 | |
What is the khata number of Ramesh Naidu in land records? | F08 | |
Who is the pattadar in Kolakaluru village? | V07 | |
How many land records are there, and do they carry Aadhaar? | M02 | |
Which farmers receive AP scheme benefits but are NOT in PM-KISAN? | Q059 | |
Which PM-KISAN farmers never took an input subsidy? | S01 | Q036 |
Which farmer participates in ALL six AP schemes? | Q114 | Q148 | Q148 answers this without the scheme_count binding hazard (all six STATE schemes, no numeric slot); Q114 needs scheme_count=6, which now means six of seven
How many schemes is Venkateswarlu G enrolled in? | F09 | Q125 |
Show the complete profile of Aadhaar 726018159083 across all datasets. | Q124 | |
What are Anjamma's total benefits across all schemes? | F12 | |
Who gets the highest input subsidy per acre of land? | Q094 | |
Ramesh Naidu's land shows 1.30 in PM-KISAN and 3.20 in MARKFED — is this a discrepancy? | F11 | |
Which Krishna-district farmers got a horticulture subsidy? | Q040 | |
Which farmers are in Fisheries but not Sericulture? | S02 | | HARD GATE - the motivating defect
Which female farmers received MARKFED payments? | V04 | |
How many input-subsidy farmers also sold produce to MARKFED? | Q118 | Q098 |
Which RySS natural-farming members still take input subsidies? | Q117 | |
Which farmers have eKYC pending yet receive scheme benefits? | G37-S | |
Is Lakshmi Devi's mobile number consistent across all datasets? | F10 | |
Which district has the most total scheme participations? | S05 | |
Which ST farmers exist, and which schemes cover them? | S06 | |
Are there land records for farmers missing from PM-KISAN? | M06 | |
List Aadhaar numbers in Fisheries that don't exist in PM-KISAN. | Q135 | S03 |
Survey has no Aadhaar — link Ramesh Naidu's land record to his PM-KISAN entry. | F13 | F08, F01, F11 |
What crops are grown by farmers whose eKYC is pending? | V08 | |
How many farmers are in each dataset? | M02 | Q005 |
Which datasets is Kiran Kumar missing from? | F09 | |
Rank farmers by number of schemes enrolled. | S04 | |
Do any farmers receive PM-KISAN + all 6 AP schemes? | Q148 | Q114, Q113 |
What is the distribution of farmers by beneficiary_status and ekyc_status per district, and which districts have a Pending backlog? | G02-S | |
What is the distribution of declared area_hectares by category (SC/ST/BC/OC)? | Q149 | Q027, G04-S |
What is the total subsidy amount by season, and what is the subsidy-to-farmer-contribution ratio (subsidyamount vs nonsubsidyamount)? | Q150 | Q090 |
What is the total Subsidy Amt released vs BALANCE_AMOUNT_TO_RELEASE still pending per beneficiary? | M04 | |
How many beneficiaries have random inspection pending or under review? | G46-S | G23-S |
Which beneficiaries have sanctioned but stalled subsidies? | G22-S | Q132 |
How many FCS members exist per district? | G25-S | |
What is the procurement payment per farmer and which farmer/district leads? | Q151 | R03, G14-S, Q111 |
How many APCNF members are enrolled and what is the total acreage under natural farming? | G28-S | |
Which farmers have a crop registered in eCrop but no seed-subsidy record for the same season - registered cultivation that never converted to input support? | M05 | |
Which farmers' PM-KISAN declared area exceeds their Survey Land Records - and is their subsidy per acre also elevated? | M07 | Q082 |
Which Aadhaar numbers have multiple transactionids for the same seed, season, and cropyear - duplicate subsidy draws? | M08 | Q068 |
Which records show a pattadar different from the recorded cultivator for the same survey number? | M09 | Q074 |
Which Aadhaar numbers appear both as fisheries registrants and crop input-subsidy recipients? | Q122 | |
Which PM-KISAN farmers which have been excluded are still receiving AP scheme benefits? | Q128 | |
Which small/marginal farmers (area_hectares below 1 ha) appear in no AP scheme dataset at all - the most-entitled least-reached segment? | Q152 | G35-S, Q036 |
Which registered crops are marked as Damaged? | V02 | |
How many farmers have discrepancies in their caste category? | G41-S | |
How many farmers have discrepancies in their land amount? | G42-S | |
"""


def load_gold() -> list[dict]:
    rows = []
    for line in GOLD_RAW.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 4:
            parts.append("")
        question, gold, also, note = parts[0], parts[1], parts[2], parts[3]
        acceptable = [a.strip() for a in also.split(",") if a.strip()]
        rows.append({
            "question": question,
            "gold": gold,
            "acceptable": acceptable,
            "note": note,
            "partial": "partial" in note.lower(),
            "excluded": "exclude from accuracy gate" in note.lower(),
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
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    retriever = VectorRetriever(client, DASHBOARD_CATALOG, TEMPLATE_CATALOG)
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

    payload = {"summary": summary, "results": results}
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
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
        return
    run(args.out, args.limit)


if __name__ == "__main__":
    main()

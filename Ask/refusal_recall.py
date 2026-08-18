"""Refusal recall — can a documented refusal be RETRIEVED at all?

WHY THIS EXISTS (WP-4c 7.4, adopted as D31.4). `recall_eval.py` drops every
`unanswerable` row through `RECALL_EXCLUDED_CASES`, so "recall@30 = 95.4%" says
nothing whatever about the 19 refusal rows — and that gap hid finding B for a
whole work package. BEN-001 sat at rank 51 of 376 against a gold question almost
word for word its own; the reranker was never handed the candidate, so no
instruction to it could have helped, and the row declined generically instead of
for the workbook's own documented reason.

So the refusals get their OWN line rather than being folded into a headline that
divides them away.

WHAT IT MEASURES. For every entry in UNANSWERABLE_CATALOG that the gold set
names as a gold, the rank of that entry among DISTINCT query_ids retrieved for
its gold question, over the same index the router uses — same vectors, same
per-paraphrase build, same max-over-vectors scoring. Rank 0 is best; `k` (30 by
default, VECTOR_TOP_K) is the window the reranker ever sees. Outside it, the
entry does not exist as far as the answer is concerned.

WHAT IT ASSERTS. In-window for the RATIFIED registers only. English is ratified;
code-mixed was ruled in scope by D31.5 and is asserted alongside it once it
holds. Odia script and Odia transliterated are operator-deferred (WP-4c ruling
4), so their ranks are REPORTED AND NOT ASSERTED — a number nobody is acting on
must not be able to turn a gate red, and must not be invisible either.

SPEND. Two embedding jobs, both cached: the catalogue index (shared with the
running server, `.tmp/catalog_index.json`) and one vector per gold question
(`.tmp/refusal_recall_queries.json`). Warm, this costs nothing and makes no
call. `--cached-only` refuses to make any call at all and is how `prdw_gates.py`
runs it, because the gates file makes exactly one paid call and it is not this
one.

  cd Ask
  python refusal_recall.py --yes          # measure, populating the caches
  python refusal_recall.py --cached-only  # gate mode: no call, ever
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from query_router.config import EMBEDDING_MODEL, VECTOR_TOP_K   # noqa: E402
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG  # noqa: E402
from eval_spend import confirm_spend                            # noqa: E402

SPECS = HERE / "eval_questions_full.json"
QUERY_CACHE = HERE / ".tmp" / "refusal_recall_queries.json"

# Registers whose in-window result is ASSERTED rather than merely reported.
#
# English has been ratified since WP-4a. Code-mixed joined it under D31.5: it is
# not a deferred register — every answerable code-mixed row in the gold set
# retrieves at 100% — so a refusal unreachable in it is an index gap and is
# treated as one.
#
# Odia script and Odia transliterated are NOT here, and the omission is a
# ruling rather than an oversight: the operator scoped Odia out after WP-4c
# (report 5.5), and the SME has not ratified the 34 Odia phrasing rows. Their
# ranks are printed on every run so that deferring them stays a visible choice.
ASSERTED_REGISTERS = ("en", "code_mixed")
DEFERRED_REGISTERS = ("odia", "odia_translit")

# The row WP-4c moved from rank 51 to rank 4 by giving the Dropped entries a
# scope-free line. It is named explicitly because it is the regression this
# whole check exists to catch a second time.
MUST_STAY_IN_WINDOW = "BEN-001"


def gold_refusal_rows() -> list[dict]:
    """Every gold row whose expected outcome is a DOCUMENTED refusal."""
    try:
        specs = json.loads(SPECS.read_text(encoding="utf-8"))
    except Exception as exc:                                 # noqa: BLE001
        sys.exit(f"cannot read {SPECS} ({type(exc).__name__}: {exc}) — run "
                 f"eval/gold/build_eval_questions.py --install first")
    return [s for s in specs
            if s.get("case_type") == "unanswerable"
            and s.get("gold") in UNANSWERABLE_CATALOG]


def index_cache_is_usable(retriever_cls, dashboards, templates) -> bool:
    """Whether the catalogue index will actually be REUSED, not merely exist.

    THE SAME MISTAKE WP-4c FOUND IN `recall_eval`, AND THE FIRST RUN OF THIS
    FILE MADE IT. Testing `_CACHE_PATH.exists()` printed "0 (cached)" and then
    spent nine embedding calls, because regenerating `unanswerable_catalog.py`
    changed the signature and `_load_or_build` correctly rejected the stale
    cache a moment later. An estimate wrong by an order of magnitude is worse
    than no estimate: the whole point of the guard is that a reader can decide
    whether to press go.

    So the signature is computed here the way the retriever computes it — from
    the same text list, in the same order — and compared against the cache.
    """
    from query_router.vector_retriever import _CACHE_PATH, _clean

    if not _CACHE_PATH.exists():
        return False
    texts: list[str] = []
    for catalog, question_key in ((dashboards, "question"),
                                  (templates, "abstract_question"),
                                  (UNANSWERABLE_CATALOG, "question")):
        for entry in catalog.values():
            for text in (entry[question_key], *(entry.get("paraphrases") or [])):
                cleaned = _clean(text).strip()
                if cleaned:
                    texts.append(cleaned)
    try:
        cached = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:                                        # pragma: no cover
        return False
    try:
        # `_signature` is an instance method that reads nothing off `self`, so an
        # uninitialised instance is enough to borrow the retriever's own hashing
        # rather than reimplement it. If that ever stops being true this fails
        # CLOSED — "assume the cache is cold" over-estimates the spend, which is
        # the only direction a spend guard may be wrong in.
        probe = retriever_cls.__new__(retriever_cls)
        return cached.get("signature") == probe._signature(texts)
    except Exception:                                        # pragma: no cover
        return False


def load_query_cache() -> dict:
    try:
        cached = json.loads(QUERY_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if cached.get("model") != EMBEDDING_MODEL:
        return {}
    return cached.get("vectors") or {}


def save_query_cache(vectors: dict) -> None:
    QUERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    QUERY_CACHE.write_text(
        json.dumps({"model": EMBEDDING_MODEL, "vectors": vectors}),
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=VECTOR_TOP_K,
                    help="the retrieval window the reranker sees")
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    ap.add_argument("--cached-only", action="store_true",
                    help="make no API call; fail if either cache is cold")
    ap.add_argument("--quiet", action="store_true",
                    help="one summary line per register, no per-row table")
    args = ap.parse_args()

    rows = gold_refusal_rows()
    if not rows:
        print("FAIL  no gold rows name a documented refusal — nothing to measure")
        return 1

    cached_queries = load_query_cache()
    uncached = [r for r in rows if r["q"] not in cached_queries]

    import numpy as np
    from query_router.dashboard_catalog import DASHBOARD_CATALOG
    from query_router.template_catalog import TEMPLATE_CATALOG
    from query_router.vector_retriever import VectorRetriever

    index_warm = index_cache_is_usable(
        VectorRetriever, DASHBOARD_CATALOG, TEMPLATE_CATALOG)

    if args.cached_only:
        cold = [what for what, warm in
                (("the catalogue index (.tmp/catalog_index.json — present but "
                   "STALE counts as cold)", index_warm),
                 ("the gold-question vectors "
                  "(.tmp/refusal_recall_queries.json)", not uncached))
                if not warm]
        if cold:
            print("UNMEASURED  refusal recall could not be computed without an "
                  "API call:")
            for what in cold:
                print(f"    cold: {what}")
            print("    fix:  cd Ask && python refusal_recall.py --yes")
            return 1
    else:
        confirm_spend(
            "refusal_recall",
            [("catalogue index (shared with the server)",
              0 if index_warm else 9),
             (f"gold-question vectors ({len(rows)} refusal rows)",
              -(-len(uncached) // 256))],
            confirmed=args.yes,
        )

    from openai import OpenAI
    key = os.environ.get("OPENAI_API_KEY", "")
    client = OpenAI(api_key=key) if key else None
    if client is None and (uncached or not index_warm):
        print("FAIL  OPENAI_API_KEY is not set and the caches are cold")
        return 1

    retriever = VectorRetriever(client, DASHBOARD_CATALOG, TEMPLATE_CATALOG,
                                UNANSWERABLE_CATALOG)

    if uncached:
        texts = [r["q"] for r in uncached]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        for text, item in zip(texts, resp.data):
            cached_queries[text] = item.embedding
        save_query_cache(cached_queries)

    matrix = retriever._matrix          # (V, dim), L2-normalised
    vec_qids = retriever.vec_qids

    results = []
    for row in rows:
        qv = np.array(cached_queries[row["q"]], dtype=np.float32)
        qv = qv / (np.linalg.norm(qv) or 1.0)
        scores = matrix @ qv
        order = np.argsort(-scores)
        seen, rank = set(), None
        for position, i in enumerate(order):
            qid = vec_qids[i]
            if qid in seen:
                continue
            seen.add(qid)
            if qid == row["gold"]:
                rank = len(seen) - 1
                break
        results.append({
            "id": row["id"], "n": row["n"], "gold": row["gold"],
            "lang": row.get("lang") or "en", "q": row["q"],
            "rank": rank if rank is not None else len(seen),
            "in_window": rank is not None and rank < args.k,
        })

    by_register = defaultdict(list)
    for r in results:
        by_register[r["lang"]].append(r)

    print(f"\n── Refusal recall@{args.k} "
          f"({len(results)} documented refusals, "
          f"{len(retriever.ids)}-entry index) ──")
    failures: list[str] = []
    for register in (*ASSERTED_REGISTERS, *DEFERRED_REGISTERS,
                     *sorted(set(by_register) - set(ASSERTED_REGISTERS)
                             - set(DEFERRED_REGISTERS))):
        group = by_register.get(register)
        if not group:
            continue
        inside = [r for r in group if r["in_window"]]
        asserted = register in ASSERTED_REGISTERS
        status = "asserted" if asserted else "reported, NOT asserted (deferred)"
        print(f"  {register:<14} {len(inside)}/{len(group)} in window   "
              f"[{status}]")
        if not args.quiet:
            for r in sorted(group, key=lambda r: r["rank"]):
                mark = " " if r["in_window"] else "!"
                print(f"    {mark} rank {r['rank']:>4}  {r['gold']:<8} "
                      f"#{r['n']}  {r['q'][:58]}")
        if asserted:
            failures += [
                f"{r['gold']} ({register}, #{r['n']}) is at rank {r['rank']}, "
                f"outside the {args.k}-candidate window — the reranker never "
                f"sees it, so the documented refusal cannot be served"
                for r in group if not r["in_window"]]

    pinned = [r for r in results if r["gold"] == MUST_STAY_IN_WINDOW]
    if not pinned:
        failures.append(
            f"{MUST_STAY_IN_WINDOW} has no gold row any more — the regression "
            f"WP-4c fixed (rank 51 -> 4) is no longer measured by anything")
    for r in pinned:
        verdict = "OK" if r["in_window"] else "REGRESSED"
        print(f"\n  {MUST_STAY_IN_WINDOW} pin: rank {r['rank']} "
              f"(was 51 before WP-4c, 4 after) — {verdict}")

    if failures:
        print(f"\nFAIL  {len(failures)} refusal(s) unreachable in a ratified "
              f"register:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS  every refusal in a ratified register retrieves in window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

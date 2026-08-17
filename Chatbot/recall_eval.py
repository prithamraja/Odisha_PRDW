"""
Recall@K harness for the *template-direct* vector-retrieval design.

Question we are answering BEFORE any refactor:
  If we embed every catalog question (D dashboards + T templates) and retrieve
  the top-K by cosine similarity for a user query, how often is the CORRECT
  query_id in the top-K?  And how badly do near-duplicate template variants
  crowd the top-30?

Usage:
  cd Chatbot
  python recall_eval.py --yes          # questions from the gold CSV
  python recall_eval.py --k 30 --yes   # change the headline K
  python recall_eval.py --refresh --yes  # ignore cached catalog embeddings

THIS SPENDS MONEY, so it requires --yes (or PRDW_EVAL_CONFIRM=1) and prints its
call estimate first. WP-2 found a test suite quietly making paid calls whenever
a key happened to sit in `.env`; a harness that embeds the whole catalogue plus
every gold question on a bare `python recall_eval.py` is the same trap one layer
up (standing discipline §3a).

MANY VECTORS PER TEMPLATE (WP-4 T4b). The index is built the way the SHIPPED
retriever builds it — one vector per abstract question AND one per paraphrase,
all mapped to the same query_id, scored as the MAX over a template's vectors,
with k counting DISTINCT query_ids. The earlier one-vector-per-id build measured
a retriever this system does not have: decision D2 replaced AP's per-scope
sibling templates with scope-phrased paraphrases, so paraphrases are how a
block- or GP-phrased question reaches its consolidated template at all.

Notes:
  - Uses the gold `topic` column as the query proxy. English rows FLATTER
    retrieval (they are phrased like the catalog); the Odia and code-mixed rows
    in the gold set are the ones that measure anything hard.
  - Catalog embeddings are cached to .tmp/catalog_embeddings.json so reruns are
    free; pass --refresh after editing the catalogs.
"""
import os
import re
import csv
import sys
import json
import io
import argparse
from pathlib import Path
from collections import Counter, defaultdict

from dotenv import load_dotenv
load_dotenv()

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openai import OpenAI

from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.template_catalog  import TEMPLATE_CATALOG
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
from query_router.config            import EMBEDDING_MODEL, ABSTRACTION_MODEL
from query_router.llm_usage         import meter, record_call
from eval_spend                     import confirm_spend

# DEFENDED, because this module is the last consumer of the retired AP retrieval
# layer (WP-4a §6.3). WP-3's T5/T6/T7 commit is titled "retire the AP retrieval
# layer"; `intent_catalog.py` happens to have survived it, holding zero entries.
# Whoever finishes that retirement should not discover it by this harness dying
# at import on the morning of an eval run.
try:
    from query_router.intent_catalog import INTENT_LOOKUP
except Exception:                                            # pragma: no cover
    INTENT_LOOKUP = {}

HERE       = Path(__file__).parent
CSV_PATH   = HERE.parent / "test_questions_query_mapping.csv"
CACHE_PATH = HERE / ".tmp" / "catalog_embeddings.json"
HINGLISH_PATH = HERE / ".tmp" / "topics_hinglish.json"

# The AP crowding metric read the intent families out of INTENT_LOOKUP. That
# table is EMPTY here — the PR&DW catalogue is retrieved template-direct — so
# the section printed "mean: 0.0, max: 0" on every run, which reads as "no
# crowding measured" when nothing was measured at all. WP-4a §6.1 shows the
# opposite is true: the workbook ships nine entries where four would do.
QID_TO_INTENTS: dict[str, set[str]] = defaultdict(set)
for (intent, _entities), qid in INTENT_LOOKUP.items():
    QID_TO_INTENTS[qid].add(intent)
INTENT_FAMILIES_AVAILABLE = bool(QID_TO_INTENTS)


def _clean_template(text: str) -> str:
    """'utilization in {district}?' -> 'utilization in district?' so the brace
    tokens don't pollute the embedding."""
    return re.sub(r"\{(\w+?)\}", r"\1", text)


def build_index() -> tuple[list[str], list[str], dict[str, str]]:
    """The retrieval index, built exactly as `VectorRetriever` builds it.

    Returns `(texts, vec_qids, display)` — one entry in the first two lists per
    EMBEDDED VECTOR, so a template with six scope paraphrases contributes seven.
    `display` is one question per distinct query_id, for the miss report.

    The known-unanswerables are indexed alongside the templates because the
    router indexes them: an officer's beneficiary question has to retrieve
    before it can be refused with a documented reason.
    """
    texts: list[str] = []
    vec_qids: list[str] = []
    display: dict[str, str] = {}

    def add(qid: str, question: str, paraphrases) -> None:
        display[qid] = question
        for text in (question, *(paraphrases or [])):
            cleaned = _clean_template(text).strip()
            if cleaned:
                texts.append(cleaned)
                vec_qids.append(qid)

    for qid, entry in DASHBOARD_CATALOG.items():
        add(qid, entry["question"], entry.get("paraphrases"))
    for tid, entry in TEMPLATE_CATALOG.items():
        add(tid, entry["abstract_question"], entry.get("paraphrases"))
    for qid, entry in UNANSWERABLE_CATALOG.items():
        add(qid, entry["question"], entry.get("paraphrases"))
    return texts, vec_qids, display


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    B = 256
    for i in range(0, len(texts), B):
        chunk = texts[i:i + B]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=chunk)
        record_call("embed", EMBEDDING_MODEL, resp)
        out.extend(d.embedding for d in resp.data)
    return out


def load_or_build_catalog_embeddings(
    client: OpenAI, texts: list[str], refresh: bool
) -> list[list[float]]:
    """One vector per INDEX ENTRY, cached against the exact text list.

    Keyed on the texts themselves, so editing a question OR adding a paraphrase
    invalidates the cache rather than silently scoring against a stale index.
    """
    if CACHE_PATH.exists() and not refresh:
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if (cached.get("model") == EMBEDDING_MODEL
                and cached.get("texts") == texts):
            return cached["vectors"]
    vecs = embed_batch(client, texts)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(
        {"model": EMBEDDING_MODEL, "texts": texts, "vectors": vecs}),
        encoding="utf-8")
    return vecs


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: list[float]) -> float:
    return sum(x * x for x in a) ** 0.5


def cosine_rank(
    qvec: list[float], vectors: list[list[float]], vec_qids: list[str]
) -> tuple[list[str], list[str]]:
    """(distinct query_ids best-first, raw vector owners best-first).

    The first list is what the router's k counts: a template scores as its
    BEST-matching vector and appears once. The second is kept so crowding can be
    measured — how much of the raw ranking a single template's paraphrases
    occupy before the candidate list is deduplicated.
    """
    qn = _norm(qvec) or 1.0
    scored = sorted(
        ((qid, _dot(qvec, v) / (qn * (_norm(v) or 1.0)))
         for qid, v in zip(vec_qids, vectors)),
        key=lambda t: t[1], reverse=True,
    )
    raw = [qid for qid, _ in scored]
    seen: set[str] = set()
    distinct = [q for q in raw if not (q in seen or seen.add(q))]
    return distinct, raw


# Domain-corrected for PR&DW (WP-4). The AP prompt asked for health-insurance
# questions and named PM-JAY, TAT and LAMA — run against this catalogue it would
# have produced fluent questions about the wrong subject entirely and reported
# the resulting recall as a multilingual measurement.
_HINGLISH_SYS = (
    "You convert English descriptions of PANCHAYAT data questions into natural "
    "Hinglish — the romanized Hindi-English mix an Odisha Panchayati Raj & "
    "Drinking Water official would actually type into a chatbot. Keep place "
    "names, fiscal years and scheme terms (GPDP, SBM, LSDG, SFC, XV Finance "
    "Commission, GP, block, district) as-is. Make it sound like a real typed "
    "question, not a literal translation. Return ONLY a JSON object "
    'mapping each input index (as a string) to its Hinglish question.'
)


def translate_to_hinglish(client: OpenAI, topics: list[str], refresh: bool) -> list[str]:
    if HINGLISH_PATH.exists() and not refresh:
        cached = json.loads(HINGLISH_PATH.read_text(encoding="utf-8"))
        if cached.get("topics") == topics:
            return cached["hinglish"]

    out: list[str] = [""] * len(topics)
    B = 20
    for i in range(0, len(topics), B):
        chunk = topics[i:i + B]
        payload = {str(j): t for j, t in enumerate(chunk)}
        resp = client.chat.completions.create(
            model=ABSTRACTION_MODEL,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _HINGLISH_SYS},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        record_call("hinglish", ABSTRACTION_MODEL, resp)
        parsed = json.loads(resp.choices[0].message.content)
        for j in range(len(chunk)):
            out[i + j] = parsed.get(str(j), chunk[j])

    HINGLISH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HINGLISH_PATH.write_text(
        json.dumps({"topics": topics, "hinglish": out}, ensure_ascii=False),
        encoding="utf-8")
    return out


def load_gold() -> list[dict]:
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            gold = (r.get("query_code") or "").strip()
            topic = (r.get("topic") or "").strip()
            if gold and topic:
                rows.append({"topic": topic, "gold": gold,
                             "intent": (r.get("intent") or "").strip(),
                             "lang": (r.get("lang") or "").strip() or "en"})
    return rows


def _duplicate_question_groups(display: dict[str, str]) -> list[list[str]]:
    """Distinct ids whose cleaned question text is IDENTICAL.

    The crowding the catalogue ships with, independent of any query: WP-4a §6.1
    found nine workbook rows where four would do (EXP-010/026/030 all read "How
    many activities have expenditure under {Focus_Area} in {Date_Range}?").
    Every one of them consumes a slot in every top-K it reaches.
    """
    by_text: dict[str, list[str]] = defaultdict(list)
    for qid, question in display.items():
        by_text[_clean_template(question).strip().lower()].append(qid)
    return [sorted(ids) for ids in by_text.values() if len(ids) > 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--lang", choices=["english", "hinglish"], default="english")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    args = ap.parse_args()

    texts, vec_qids, display = build_index()
    gold = load_gold()
    scorable_n = sum(1 for g in gold if g["gold"] in display)
    cached = CACHE_PATH.exists() and not args.refresh
    confirm_spend(
        "recall_eval",
        [(f"catalogue embeddings ({len(texts)} vectors over "
          f"{len(display)} entries)", 0 if cached else -(-len(texts) // 256)),
         (f"query embeddings ({scorable_n} gold questions)",
          -(-scorable_n // 256)),
         *([(f"Hinglish translation of {scorable_n} topics",
             -(-scorable_n // 20))] if args.lang == "hinglish" else [])],
        confirmed=args.yes,
    )

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    print(f"Index: {len(display)} entries, {len(texts)} vectors "
          f"({len(texts) - len(display)} from paraphrases)")

    vectors  = load_or_build_catalog_embeddings(client, texts, args.refresh)

    # Gold rows whose query_code isn't in the current catalog can't be scored.
    missing  = [g for g in gold if g["gold"] not in display]
    scorable = [g for g in gold if g["gold"] in display]
    print(f"Gold rows: {len(gold)} | scorable: {len(scorable)} | "
          f"gold id not in catalog: {len(missing)}")
    if missing:
        print("  (unmatched gold ids: "
              + ", ".join(sorted({g['gold'] for g in missing})) + ")")

    if args.lang == "hinglish":
        q_texts = translate_to_hinglish(client, [g["topic"] for g in scorable], args.refresh)
        print(f"\nLanguage: HINGLISH (sample: {q_texts[0]!r})")
    else:
        q_texts = [g["topic"] for g in scorable]
        print(f"\nLanguage: ENGLISH")
    q_vecs   = embed_batch(client, q_texts)

    Ks       = sorted({5, 10, 20, args.k})
    hits     = {k: 0 for k in Ks}
    ranks    = []
    crowd    = []   # raw vector slots spent to reach K DISTINCT query_ids
    dup_hits = []   # duplicate-question ids sharing the top-K with the gold
    misses   = []

    dup_groups = _duplicate_question_groups(display)
    dup_of = {qid: set(group) - {qid}
              for group in dup_groups for qid in group}

    ranks_in_order = []
    for g, qv in zip(scorable, q_vecs):
        ranked, raw = cosine_rank(qv, vectors, vec_qids)
        gold_id  = g["gold"]
        rank     = ranked.index(gold_id)          # 0-based, distinct ids
        ranks.append(rank)
        ranks_in_order.append(rank)
        for k in Ks:
            if rank < k:
                hits[k] += 1

        # CROWDING, measured two ways that both cost real top-K room.
        #
        # 1. Paraphrase crowding: how many RAW vectors the retriever has to walk
        #    to collect K distinct query_ids. K exactly means no paraphrase ever
        #    displaced another template; the excess is the price of the D2
        #    scope-paraphrase design, which is the number this harness exists to
        #    keep honest.
        seen: set[str] = set()
        consumed = 0
        for qid in raw:
            consumed += 1
            seen.add(qid)
            if len(seen) == args.k:
                break
        crowd.append(consumed - args.k)

        # 2. Duplicate-row crowding: sibling entries with IDENTICAL question
        #    text that reached the same top-K (WP-4a §6.1). These are distinct
        #    ids, so the dedup above cannot help — each one really does take a
        #    slot, and the reranker then sees a tie it cannot break on meaning.
        dup_hits.append(len(dup_of.get(gold_id, set()) & set(ranked[:args.k])))

        if rank >= args.k:
            misses.append((g["topic"], gold_id, rank))

    n = len(scorable)
    note = "optimistic — topics phrased like the catalog" if args.lang == "english" \
        else "LLM-generated Hinglish from English topics"
    print(f"\n── Recall@K ({args.lang}; {note}) ──")
    for k in Ks:
        print(f"  recall@{k:<3}: {hits[k]/n:6.1%}  ({hits[k]}/{n})")

    # PER LANGUAGE, because the headline hides the finding. English rows are
    # phrased like the catalogue and flatter retrieval; the Odia-script rows are
    # the ones that measure whether an officer typing in the state language can
    # reach the catalogue at all.
    print(f"\n── Recall@{args.k} by language ──")
    by_lang = defaultdict(lambda: [0, 0])
    for g, rank in zip(scorable, ranks_in_order):
        bucket = by_lang[g.get("lang") or "en"]
        bucket[1] += 1
        if rank < args.k:
            bucket[0] += 1
    for lang in sorted(by_lang):
        hit_n, total = by_lang[lang]
        print(f"  {lang:<14} {hit_n/total:6.1%}  ({hit_n}/{total})")

    ranks.sort()
    def pct(p): return ranks[min(len(ranks) - 1, int(len(ranks) * p))]
    print("\n── Gold-answer rank (0-based) ──")
    print(f"  median: {pct(0.5)}   p90: {pct(0.9)}   p99: {pct(0.99)}   worst: {ranks[-1]}")

    print(f"\n── Crowding 1: extra raw vectors walked to reach {args.k} "
          f"distinct ids ──")
    print("  (0 = no paraphrase ever displaced another template)")
    c = Counter(crowd)
    print(f"  mean: {sum(crowd)/len(crowd):.1f}   max: {max(crowd)}")
    print(f"  distribution: " + ", ".join(f"{k}:{c[k]}" for k in sorted(c)))

    print(f"\n── Crowding 2: identical-question siblings in top-{args.k} ──")
    print(f"  the catalogue ships {len(dup_groups)} groups of duplicate "
          f"question text ({sum(len(g) for g in dup_groups)} entries where "
          f"{len(dup_groups)} would do)")
    for group in dup_groups:
        print(f"    {', '.join(group)}")
    d = Counter(dup_hits)
    print(f"  mean: {sum(dup_hits)/len(dup_hits):.2f}   max: {max(dup_hits)}")
    print(f"  distribution: " + ", ".join(f"{k}:{d[k]}" for k in sorted(d)))

    if not INTENT_FAMILIES_AVAILABLE:
        print("\n  note: the AP intent-family crowding metric is REMOVED, not "
              "measured-as-zero. INTENT_LOOKUP holds 0 entries here (PR&DW "
              "retrieves template-direct), so it printed 'mean: 0.0' on every "
              "run and read as evidence of a clean catalogue — see Crowding 2 "
              "for the opposite.")

    if misses:
        print(f"\n── Misses (gold outside top-{args.k}) — {len(misses)} ──")
        for topic, gid, rank in misses[:20]:
            print(f"  rank {rank:>3}  {gid:>5}  {topic[:70]}")

    # D28.8. A cached catalogue index reports zero embedding calls here, which is
    # information rather than a gap: it says the cache did its job.
    print(meter().report("recall_eval: token spend"))


if __name__ == "__main__":
    main()

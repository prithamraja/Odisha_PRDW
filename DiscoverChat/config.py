"""DiscoverChat configuration — one place for every knob (WP-D5).

Three rules this file exists to keep:

1. **The embedding pin is not re-declared here.** It is imported from
   `phase5d_retrieval_corpus`, which built the corpus, and then CHECKED against
   the stamp the build wrote. A corpus embedded under one pin can never be
   served under another, and the failure is loud. Re-declaring the pin would be
   the drift D17 exists to prevent.

2. **The prose model is `discover_config`'s, never a constant of our own**
   (D42 ruling 6 / D17). Same for the completion budget.

3. **The retrieval thresholds are KNOBS, not buried constants** (D5.1). They
   are the numbers the operator ratifies at D5.3, so they carry their
   provisional status in their names and in this comment, and every one is
   overridable by environment variable without a code change.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
INSIGHTS_SRC = REPO / "Insights" / "src"
ASK_DIR = REPO / "Ask"
METAINSIGHTS = REPO / "Insights" / "metainsights"

for path in (str(INSIGHTS_SRC), str(ASK_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

# ── The pins, imported from where they were decided ──────────────────────────
from phase5d_retrieval_corpus import (            # noqa: E402
    EMBED_MODEL, EMBED_DIMS, QUERY_INSTRUCTION, Embedder,
    embedding_pin, pin_fingerprint,
)
from discover_config import (                     # noqa: E402
    DISCOVER_PROSE_MODEL, DISCOVER_MAX_COMPLETION_TOKENS,
)

CORPUS_PATH = METAINSIGHTS / "retrieval_corpus.json"
VECTORS_PATH = METAINSIGHTS / "retrieval_corpus.npy"
STAMP_PATH = METAINSIGHTS / "retrieval_corpus_stamp.json"

ASK_DB_PATH = ASK_DIR / "data" / "panchayat_1.duckdb"

DATA_QUERY_EXPANSION = HERE / "query_expansion.json"
DATA_MEASURE_KEYWORDS = HERE / "measure_keywords.json"

# ── The generative models ────────────────────────────────────────────────────
WRITER_MODEL = DISCOVER_PROSE_MODEL                     # D17 pin, via discover_config
WRITER_MAX_COMPLETION = DISCOVER_MAX_COMPLETION_TOKENS  # D17 budget

# WP-D4 T4 asks for a DIFFERENT model from the writer. Changed from `gpt-5.5`
# to `gpt-5.6-luna` on 2026-09-01 on the operator's instruction, for cost --
# and `luna` is a SIBLING of the writer `gpt-5.6-sol`, not a different
# generation, so the independence T4 was built on is materially weaker here.
# The full rationale and the reopened-gate note live in
# Insights/src/insight_prose_config.py; this pin follows it deliberately so the
# chat path and the build step are judged by the same model.
# Same vendor remains the disclosed limitation: Insights/.env serves one
# completion vendor, so a cross-vendor judge needs a new credential.
VERIFIER_MODEL = os.getenv("DISCOVERCHAT_VERIFIER_MODEL", "gpt-5.6-luna")

# 9,000, NOT WP-D4's 4,000, and the difference was measured rather than guessed.
# The trial's ceiling was sized for one rewritten finding. This verifier reads a
# whole answer -- as many as twelve findings plus the writer's context -- and
# must map every factual claim to a source line. At 4,000 it starved on 4 of 6
# calls: `finish_reason='length'`, 4,000 completion tokens spent entirely on
# reasoning, empty string returned, no error. That is the exact failure D17's
# budget note describes and the exact failure D43's retry-on-empty was added
# for -- and the retry could not help, because the second attempt starved too.
# The two calls that DID return used 1,305 and 1,400 tokens, so the budget is
# not marginal at 9,000; it was simply wrong at 4,000.
VERIFIER_MAX_COMPLETION = int(os.getenv("DISCOVERCHAT_VERIFIER_TOKENS", "9000"))

# The classifier is a small, cheap routing decision, logged per turn (D5.2).
CLASSIFIER_MODEL = os.getenv("DISCOVERCHAT_CLASSIFIER_MODEL", "gpt-5.5")
CLASSIFIER_MAX_COMPLETION = int(os.getenv("DISCOVERCHAT_CLASSIFIER_TOKENS", "2000"))

# The relevance judge (operator proposal, 2026-09-01). Ruling on up to 100
# findings at once is a large reasoning job, and this WP has already lost two
# calls to a reasoning model spending its whole budget on reasoning and
# returning an empty string. Sized with that in mind, and retried on empty.
JUDGE_MODEL = os.getenv("DISCOVERCHAT_JUDGE_MODEL", "gpt-5.6-sol")
JUDGE_MAX_COMPLETION = int(os.getenv("DISCOVERCHAT_JUDGE_TOKENS", "12000"))

MAX_PROMPT_TOKENS = 16000        # WP-D4's ceiling, unchanged

# ── Retrieval knobs — PROVISIONAL until D5.3 ratifies them ───────────────────
# Set from the D5.1 experiment; every one is an env override so the operator can
# move a threshold at the pilot without a code change, and so the D5.3 gate can
# ratify a number rather than a diff.
#
# RELEVANCE_THRESHOLD is a FLOOR, not a top-N (D42 ruling 5). Everything above
# it is the answer; if nothing clears it the bot says the analysis has nothing
# on this. It is never relaxed to manufacture an answer.
RELEVANCE_THRESHOLD = float(os.getenv("DISCOVERCHAT_THRESHOLD", "0.62"))

# --- the judged path (arm D) --------------------------------------------------
# When USE_JUDGE is on, the floor drops to CANDIDATE_FLOOR and an LLM decides
# which of the top CANDIDATE_POOL candidates actually answer the question.
# Measured before building: at 0.50, top 100 after the diversity collapse, all
# 34 place questions in the D5.1 set have a genuinely relevant finding in the
# pool (against 19 of 34 answered under the 0.62 threshold alone), and the
# candidate list costs a median 8,589 tokens against the 16k input cap.
#
# The judge may only REJECT. Nothing below CANDIDATE_FLOOR is ever reachable, so
# D42 ruling 5's floor still stands; what moves is the last step of "is this an
# answer?", from a comparison to a judgement.
USE_JUDGE = os.getenv("DISCOVERCHAT_USE_JUDGE", "1") not in ("0", "", "false", "False")
CANDIDATE_FLOOR = float(os.getenv("DISCOVERCHAT_CANDIDATE_FLOOR", "0.50"))
CANDIDATE_POOL = int(os.getenv("DISCOVERCHAT_CANDIDATE_POOL", "100"))

# The engine-score quality floor. The corpus is wide on purpose (D42 ruling 3):
# candidates that never reached the ranked cut are indexed. This is the knob
# that decides which of them may be SHOWN.
QUALITY_FLOOR = float(os.getenv("DISCOVERCHAT_QUALITY_FLOOR", "0.0"))

# The structural boost, added to cosine. Survives only if D5.1 shows it beats
# cosine alone (D42 ruling 4) — the numbers decide, not the argument.
GEO_BOOST = float(os.getenv("DISCOVERCHAT_GEO_BOOST", "0.06"))
MEASURE_BOOST = float(os.getenv("DISCOVERCHAT_MEASURE_BOOST", "0.03"))
# A finding whose SUBSPACE is the officer's own place is about that place; one
# that merely lists it among 20 members mentions it. Both are hits, weighted apart.
GEO_SUBSPACE_BONUS = float(os.getenv("DISCOVERCHAT_GEO_SUBSPACE_BONUS", "0.02"))

# Above this many findings, the answer is written as consolidated prose rather
# than rendered finding by finding (D42 "presentation adapts to its size").
FULL_RENDER_MAX = int(os.getenv("DISCOVERCHAT_FULL_RENDER_MAX", "4"))
# The hard ceiling on how many findings reach one answer. Not a top-N in the
# sense ruling 5 forbids — the floor still decides membership; this only caps
# how much of a very broad sweep is written out at once, and the answer says so.
ANSWER_CAP = int(os.getenv("DISCOVERCHAT_ANSWER_CAP", "12"))


def load_stamp() -> dict:
    with open(STAMP_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def assert_pin_matches_corpus() -> dict:
    """The corpus was embedded under the pin this process is about to query with.

    Called at service startup and by every test. A silent mismatch would mean
    querying a 1,024-dimension corpus with a 4,096-dimension query, or an
    instructed corpus with an uninstructed query — cases that produce plausible
    nonsense rather than an error.
    """
    if not STAMP_PATH.exists():
        raise SystemExit(
            f"STOP: no retrieval corpus stamp at {STAMP_PATH}. "
            f"Run `python Insights/src/phase5d_retrieval_corpus.py` first (D5.0)."
        )
    stamp = load_stamp()
    if stamp.get("embedding_pin_fingerprint") != pin_fingerprint():
        raise SystemExit(
            "STOP: the corpus was embedded under a different pin than this "
            "process would query with.\n"
            f"  corpus: {json.dumps(stamp.get('embedding_pin'), indent=2)}\n"
            f"  here:   {json.dumps(embedding_pin(), indent=2)}\n"
            "Rebuild the corpus, or restore the pin."
        )
    return stamp


def run_stamp_line() -> str:
    """'as of <run date>' — on every answer, by D42's presentation rule."""
    stamp = load_stamp()
    date = str(stamp.get("candidate_set_generated_at")
               or stamp.get("source_generated_at", ""))[:10]
    if not date:
        # The corpus stamp always carries the candidate set's own stamp; the
        # feed sidecar is the authority for when the analysis was run.
        with open(METAINSIGHTS / "global_feed_source_set.json", encoding="utf-8") as fh:
            date = json.load(fh)["generated_at"][:10]
    return f"as of {date}"


def knobs() -> dict:
    """Every provisional number, for the report and for the D5.3 ratification."""
    return {
        "relevance_threshold": RELEVANCE_THRESHOLD,
        "quality_floor": QUALITY_FLOOR,
        "geo_boost": GEO_BOOST,
        "measure_boost": MEASURE_BOOST,
        "geo_subspace_bonus": GEO_SUBSPACE_BONUS,
        "full_render_max": FULL_RENDER_MAX,
        "answer_cap": ANSWER_CAP,
        "use_judge": USE_JUDGE,
        "candidate_floor": CANDIDATE_FLOOR,
        "candidate_pool": CANDIDATE_POOL,
    }

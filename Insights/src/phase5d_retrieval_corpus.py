# =============================================================================
# Phase 5d: Retrieval corpus + embeddings (WP-D5, stage D5.0)
# =============================================================================
# Builds the sidecar that DiscoverChat retrieves over. It computes nothing about
# the data: every sentence is `phase5_ranking.generate_nl_summary` and every
# figure stays where the engine put it. What this file adds is (a) coordinates
# the sentence does not carry, (b) an ENRICHED RETRIEVAL TEXT, and (c) its
# embedding.
#
# Inputs  (read-only, SHA-verified by the caller):
#   metainsights/view{1,2,3}_candidates.json   the corpus, wide (D42 ruling 3)
#   metainsights/view{1,2,3}_ranked.json       per-view rank, where a record has one
#   metainsights/global_feed.json              feed membership
#   metainsights/global_feed_source_set.json   the run stamp (candidate_set_id)
#   Ask's EntityValidator                      geography -> LGD codes (read-only DB)
#
# Outputs (new files; the feed's JSON is never touched -- D16):
#   metainsights/retrieval_corpus.json         one record per finding, no vectors
#   metainsights/retrieval_corpus.npy          float32 (N, EMBED_DIMS), L2-normalised
#   metainsights/retrieval_corpus_stamp.json   provenance + the embedding pin
#
# Run from the LOCAL MIRROR (D6), repo root:
#   python Insights/src/phase5d_retrieval_corpus.py
#   python Insights/src/phase5d_retrieval_corpus.py --no-embed   (structure only)
#
# =============================================================================
# WHY AN ENRICHED TEXT, AND WHAT IS DELIBERATELY NOT IN IT
# =============================================================================
# MEASURED, not assumed: the 4,239 records that survive twin-merge carry only
# 1,775 DISTINCT sentences. `generate_nl_summary` never mentions the base
# subspace, so eight findings about eight different slices of the data --
# costed works, maintenance works, one asset category -- render as one identical
# string. Embedding the bare sentence therefore gives 2,464 records a vector
# some other record already owns, and retrieval cannot tell them apart at all.
# That is the "templated sentences cluster by template" failure D42 ruling 4
# names, and it is why the document side embeds sentence + view title +
# glossary-expanded measure + breakdown/subspace labels + exception member
# names. D5.1 measures whether it helps; this file only makes it measurable.
#
# NO SHARED DOMAIN PREAMBLE (D42 ruling 7). Nothing here is prepended to every
# vector. Identical text on 4,239 vectors moves them all the same distance and
# blurs exactly the distinctions retrieval depends on. Domain background belongs
# to the generative components (ruling 8) -- the writer, the classifier and the
# verifier get the context brief; the embedder never does. The field labels
# below ("Measure:", "Within") are the minimum scaffolding that keeps the text
# readable and are kept short for that reason.
#
# ASYMMETRIC USE (D42 ruling 7). Queries carry ONE fixed task instruction in the
# Qwen3 convention (`Instruct: ...\nQuery: ...`); documents are embedded plain.
# The instruction text, the model id and the dimension count are pinned together
# below and copied into the stamp, so a corpus built under one pin can never be
# served under another (DiscoverChat.config asserts this).
# =============================================================================

import argparse
import ast
import gzip
import hashlib
import json
import os
import sys
import time

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Insights/
REPO_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase2_engine import (                                    # noqa: E402
    MetaInsightCandidate, Subspace, load_candidates, RANKING_PREFILTER_CAP,
)
from phase5_ranking import (                                   # noqa: E402
    merge_twin_candidates, generate_nl_summary,
)
from phase5b_report import VIEW_DESCRIPTIONS                   # noqa: E402
from phase5c_global_feed import VIEW_TITLES                    # noqa: E402

MI_DIR = os.path.join(BASE_DIR, "metainsights")
VIEWS = ("view1", "view2", "view3", "view4")   # WP-D11

CORPUS_PATH  = os.path.join(MI_DIR, "retrieval_corpus.json.gz")
VECTORS_PATH = os.path.join(MI_DIR, "retrieval_corpus.npy")
STAMP_PATH   = os.path.join(MI_DIR, "retrieval_corpus_stamp.json")

# The pre-WP-D10 spelling. Read for the vector cache, never written (D10.0):
# the first rebuild under the new format must reuse the old build's vectors by
# hash rather than re-embed them, and the old build is a plain .json.
LEGACY_CORPUS_PATH = os.path.join(MI_DIR, "retrieval_corpus.json")


# =============================================================================
# THE STORAGE FORMAT  (WP-D10)
# =============================================================================
# One format, one loader, both corpora (D10 ruling 5). What changed and why,
# each of them MEASURED on the real corpus before it was adopted:
#
#   GZIP, LEVEL 6, mtime=0.   The record JSON compresses 10.9x (76 -> 7.0 MB)
#       and decompresses in 0.15 s. Level 9 is slower and no smaller. `mtime=0`
#       and an empty `filename` because gzip's header otherwise carries a
#       timestamp and the source file's name, and the build gate compares BYTES
#       between two consecutive builds -- a header clock would fail it every
#       time for no reason to do with the data.
#
#   COMPACT JSON.  No indentation. The file is a build output read by one
#       loader, not a document anyone diffs by eye; `python -m json.tool` and
#       `--embed-text` below are what make it readable when it must be.
#
#   NO `embed_text`, ITS HASH KEPT.  The exact text that was embedded is no
#       longer STORED, it is REPRODUCIBLE and hash-pinned -- D10 ruling 3
#       amending WP-D5 ruling 7. `--embed-text <id>` rebuilds it from the
#       record's own fields and checks it against `embed_text_sha256`, so the
#       audit trail is a command rather than 60 MB of duplicated strings. The
#       hash stays because it is also the vector cache's key.
#
#   FLOAT16 VECTORS, FLOAT32 ARITHMETIC.  Measured against the fp32 file on the
#       real corpus: 100% top-100 pool overlap, top-1 unchanged, cosine drift
#       < 1e-4 -- an order of magnitude below the endpoint's own call-to-call
#       jitter of 1.2e-3. Every loader upcasts at load, so RAM and every
#       comparison downstream are fp32 exactly as before; only the disk changes
#       (148 -> 74 MB). Vectors are NOT gzipped: floats compress 1.09x, which
#       buys nothing and costs a decompress.
#
# DIMENSIONS ARE UNTOUCHED. Matryoshka truncation was measured (512 gives 92.8%
# pool overlap, 256 gives 87.4%) and declined by the operator. Nothing in this
# section changes the pin's model, dims or instructions -- only how the numbers
# are laid down on disk.
GZIP_LEVEL = 6
STORAGE_DTYPE = "float16"
VECTOR_DTYPE = np.float16


def write_corpus_json(path: str, payload: dict) -> None:
    """The record file: compact JSON, gzip 6, and a header with no clock in it."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=False,
                     separators=(",", ":")).encode("utf-8")
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=GZIP_LEVEL,
                           fileobj=fh, mtime=0) as gz:
            gz.write(raw)
    os.replace(tmp, path)


def read_corpus_json(path: str) -> dict:
    """A record file in EITHER format -- gzipped or the pre-D10 plain .json.

    Both spellings are read and only the new one is written. This is what makes
    the first rebuild under D10 cost zero embedding calls: the cache reader
    below opens the previous build, which is a plain .json, and the endpoint is
    never touched.
    """
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# =============================================================================
# THE VECTOR PARTS  (WP-D11b T1, D61 ruling 1)
# =============================================================================
# WP-D11 grew the decomposition matrix to 66,779 x 1,024 fp16 = 136.8 MB, over
# GitHub's 100 MB per-file limit, and the deployed `discover-api` reads its
# corpus straight from git. The operator's ruling: SPLIT the file, do not shrink
# it -- no dimension truncation (declined 2026-09-04), no re-embedding, no record
# dropped. So a vector matrix is now written as `<name>.part0.npy`,
# `<name>.part1.npy`, ... in row order, each at most PART_MAX_BYTES, and the
# stamp carries the list with a SHA-256 per part.
#
# THE SPLIT IS INVISIBLE TO RETRIEVAL. The parts are consecutive row slices of
# one C-contiguous fp16 array, so concatenating them in order gives back the
# identical bytes (`matrix_sha256` in the manifest is the hash of exactly those
# bytes, and the T1 proof compares it against the unsplit file). Nothing about
# what a vector means changes, so `semantic_pin()` is untouched and the cache
# reuses every vector; `storage_layout` joins `storage_dtype` in the full pin,
# for the same loader-guard reason.
#
# ONE PART EVEN WHEN ONE WOULD DO. The findings matrix is 9 MB and fits in one
# file, and it is still written as `.part0.npy`, so there is one layout and one
# loader rather than a size-dependent fork -- and the unsplit spelling, which is
# the thing git must never be handed again, is never written by anything.
#
# The parts are sized EVENLY (ceil(rows / n) each) rather than filled to the
# limit, so the decompose matrix is two ~68 MB files, not a 95 MB one and a
# 42 MB one: the headroom is shared, and the next mining run that adds records
# does not push the first part over the limit before it adds a third.
STORAGE_LAYOUT = "npy-parts"
# 95 MB of decimal bytes: 5 MB under the limit git enforces, and the limit the
# brief sets. The gate (`vector-parts-under-limit`) checks 100 MB separately, so
# the two numbers are not the same check twice.
PART_MAX_BYTES = 95_000_000
_NPY_HEADER_ALLOWANCE = 4096          # np.save writes a 128-byte header; generous


class VectorPartsError(Exception):
    """A vector part named by the stamp is missing, altered, or mis-shaped.

    An Exception, not a SystemExit, on purpose: the builders' cache readers
    catch Exception and fall back to "no cache", and the service's loader turns
    it into a STOP. Each caller decides what a bad file costs it.
    """


def part_path(vectors_path: str, index: int) -> str:
    """`.../decompose_corpus.npy` -> `.../decompose_corpus.part<index>.npy`."""
    stem = vectors_path[:-len(".npy")] if vectors_path.endswith(".npy") else vectors_path
    return f"{stem}.part{index}.npy"


def _existing_parts(vectors_path: str) -> list:
    stem = os.path.basename(part_path(vectors_path, 0))[:-len("0.npy")]
    folder = os.path.dirname(vectors_path)
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                  if n.startswith(stem) and n.endswith(".npy")
                  and n[len(stem):-len(".npy")].isdigit())


def save_vectors(path: str, vectors: np.ndarray) -> dict:
    """Store fp16, as evenly sized row-slice parts; return the stamp manifest.

    Rounding fp32 -> fp16 is deterministic, re-storing an already-fp16 vector is
    the identity, and the part boundaries depend only on the row count, so a
    rebuild from the cache reproduces every part byte for byte.

    New parts are written under temporary names first and swapped in only when
    all of them exist, and stale parts from a larger previous build are removed
    after that -- so a kill mid-write leaves the previous build readable. The
    unsplit legacy file is NOT removed here: the caller removes it after the
    stamp that supersedes it has been written (see `retire_unsplit`).
    """
    arr = np.ascontiguousarray(np.asarray(vectors, dtype=VECTOR_DTYPE))
    n_rows = int(arr.shape[0])
    row_bytes = int(arr.shape[1]) * arr.itemsize if arr.ndim == 2 else arr.itemsize
    n_parts = max(1, -(-(n_rows * row_bytes) // PART_MAX_BYTES))
    rows_per = max(1, -(-n_rows // n_parts))
    while rows_per * row_bytes + _NPY_HEADER_ALLOWANCE > PART_MAX_BYTES:
        n_parts += 1
        rows_per = -(-n_rows // n_parts)

    written = []
    for i in range(n_parts):
        final = part_path(path, i)
        tmp = final[:-len(".npy")] + ".tmp.npy"     # np.save appends .npy otherwise
        np.save(tmp, arr[i * rows_per:(i + 1) * rows_per])
        written.append((tmp, final))
    keep = set()
    for tmp, final in written:
        os.replace(tmp, final)
        keep.add(os.path.normcase(os.path.abspath(final)))
    for stale in _existing_parts(path):
        if os.path.normcase(os.path.abspath(stale)) not in keep:
            os.remove(stale)

    parts = []
    for _tmp, final in written:
        parts.append({"file": os.path.basename(final),
                      "rows": int(np.load(final, mmap_mode="r").shape[0]),
                      "bytes": os.path.getsize(final),
                      "sha256": sha256_of(final)})
    return {
        "layout": STORAGE_LAYOUT,
        "dtype": STORAGE_DTYPE,
        "shape": [n_rows] + [int(d) for d in arr.shape[1:]],
        "part_max_bytes": PART_MAX_BYTES,
        # The hash of the whole fp16 matrix's bytes, C order -- the same bytes
        # whether they sit in one file or in several. This is what the T1 proof
        # compares against the unsplit array, and what an auditor can recompute.
        "matrix_sha256": hashlib.sha256(arr.tobytes()).hexdigest(),
        "parts": parts,
    }


def retire_unsplit(path: str) -> bool:
    """Remove the pre-WP-D11b single `.npy`, once a split build has replaced it."""
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def load_vectors(path: str, manifest: dict | None = None) -> np.ndarray:
    """The vector matrix as fp32, from the parts a stamp's manifest names.

    With a manifest: read every part IN ORDER, refuse if one is missing, if its
    SHA-256 is not the one the stamp recorded, or if the concatenation is not
    the recorded shape, and hand back the concatenation upcast to fp32.

    Without one: read a single pre-WP-D11b `.npy`. Only the builders' cache
    readers take this path, so the first split build can reuse the unsplit
    build's vectors by hash and make no embedding call; the service always
    passes a manifest.

    Every consumer of a vector in this system works in fp32; the storage dtype
    and the storage layout both stop at this function.
    """
    if manifest is None:
        return np.asarray(np.load(path), dtype=np.float32)
    if manifest.get("layout") != STORAGE_LAYOUT or not manifest.get("parts"):
        raise VectorPartsError(
            f"the stamp's vector manifest is not a {STORAGE_LAYOUT!r} manifest "
            f"with parts: {json.dumps(manifest)[:200]}")
    folder = os.path.dirname(path)
    blocks = []
    for part in manifest["parts"]:
        file = os.path.join(folder, part["file"])
        if not os.path.exists(file):
            raise VectorPartsError(f"vector part {part['file']} is missing from {folder}")
        actual = sha256_of(file)
        if actual != part["sha256"]:
            raise VectorPartsError(
                f"vector part {part['file']} has sha256 {actual[:16]}, the stamp "
                f"recorded {part['sha256'][:16]} -- it is not the file this build wrote")
        blocks.append(np.load(file))
    matrix = blocks[0] if len(blocks) == 1 else np.concatenate(blocks, axis=0)
    if list(matrix.shape) != list(manifest["shape"]):
        raise VectorPartsError(
            f"the parts concatenate to {list(matrix.shape)}, the stamp says "
            f"{manifest['shape']}")
    return np.asarray(matrix, dtype=np.float32)


def load_previous_vectors(vectors_path: str, stamp_path: str):
    """The previous build's vectors, in whichever layout it wrote, or None.

    A split build is found through its stamp's manifest; a pre-split build
    through the single `.npy` it left. Anything unreadable is None -- for a
    cache, "no cache" is always a safe answer, and the byte-identity gate is what
    would notice if it happened when it should not have.
    """
    manifest = None
    if os.path.exists(stamp_path):
        try:
            with open(stamp_path, encoding="utf-8") as fh:
                manifest = json.load(fh).get("vector_storage")
        except (OSError, ValueError):
            manifest = None
    try:
        if manifest:
            return load_vectors(vectors_path, manifest)
        if os.path.exists(vectors_path):
            return load_vectors(vectors_path)
    except Exception:
        return None
    return None


# ── The decomposition member list, columnar (D10 ruling 3) ───────────────────
# 36,218 records carry 1.1M members between them, and stored one dict per member
# the key names alone were the single largest thing in the file. Columnar stores
# each key once. `is_null` becomes `null_index` -- the positions that are null,
# which for this corpus is a handful of entries rather than 1.1M `false`s.
#
# The order of the lists IS the order of the members, and the builder sorts them
# (descending by magnitude, then by label) before they get here, so "the largest
# member" stays position 0 through the round trip.
MEMBER_COLUMNS = ("member", "value", "rows", "share")


def members_columnar(members: list) -> dict:
    """[{member, is_null, value, rows, share}, ...] -> columns."""
    columnar = {col: [m[col] for m in members] for col in MEMBER_COLUMNS}
    columnar["null_index"] = [i for i, m in enumerate(members) if m["is_null"]]
    return columnar


def members_expand(members) -> list:
    """Columns -> [{member, is_null, value, rows, share}, ...].

    Accepts a pre-D10 list unchanged, so one reader serves a corpus in either
    format and no caller has to ask which it is holding.
    """
    if isinstance(members, list):
        return members
    if not members:
        return []
    nulls = set(members.get("null_index") or ())
    names = members["member"]
    return [{"member": names[i],
             "is_null": i in nulls,
             "value": members["value"][i],
             "rows": members["rows"][i],
             "share": members["share"][i]}
            for i in range(len(names))]


# =============================================================================
# THE EMBEDDING PIN  (D17 discipline: model id, dimensions and instruction
# pinned TOGETHER, and verified against the live endpoint before use)
# =============================================================================
# Verified live on 2026-09-01 against Novita's OpenAI-compatible endpoint, not
# guessed. What the probe found:
#
#   qwen/qwen3-embedding-8b      200, native 4,096 dims
#   qwen/qwen3-embedding-0.6b    200, native 1,024 dims
#   qwen/qwen3-embedding-4b      404 MODEL_NOT_FOUND  (it is NOT served here)
#   Qwen/Qwen3-Embedding-8B      404  -- the id is lower-case, vendor-prefixed
#
# The 8b is the pin: it is the strongest of the two that exist on this key.
#
# DIMENSIONS = 1024, by Matryoshka truncation, which the endpoint honours
# (probed at 1024 and 2048, both returned). Native 4,096 would make the vector
# sidecar 84 MB for 4,239 records, in a Drive-synced git repo, for a corpus this
# size. 1,024 is 21 MB. Raising it is a one-line change plus a rebuild, and the
# stamp records which was used, so the choice is reversible rather than baked in.
#
# THE API IS NOT BIT-DETERMINISTIC. Two calls on the same string differ by up to
# 1.2e-3 per component (measured). The D5.0 gate -- two consecutive builds
# byte-identical -- therefore rests on the VECTOR CACHE below, not on the
# endpoint: a rebuild re-embeds only texts whose SHA-256 is new. This is also
# why nothing downstream may re-embed a document.
#
# THE PROVIDER IS OPENROUTER FROM WP-D11b (operator ruling, 2026-09-11). Between
# 2026-09-08 (WP-D11 embedded ~28,000 texts with exactly this request) and
# 2026-09-11, Novita began refusing `dimensions=1024` ("not supported") and the
# OpenAI client's default base64 encoding, and returned only native 4,096-dim
# vectors -- which also broke every query embedding in the deployed chat. The
# same model on OpenRouter honours `dimensions=1024`, and was MEASURED against
# the stored corpus before the switch (handoffs/WPD11b_calibration/
# openrouter_probe_output.txt): cosine >= 0.99983 against stored vectors on
# 32 records, Novita and OpenRouter agreeing at >= 0.99985 on the same text,
# and OpenRouter's server-side 1,024 equal to the first 1,024 of its native
# vector -- the Matryoshka prefix the stored vectors were made with.
#
# ONE HOST PREFERRED. OpenRouter routes a model to several hosts; DeepInfra and
# Nebius both measured inside the noise above. DeepInfra is preferred for
# repeatability, with fallback allowed so an outage there does not take query
# embedding down with it. Set DISCOVER_EMBED_PROVIDER to change the preference.
EMBED_MODEL       = os.getenv("DISCOVER_EMBED_MODEL", "qwen/qwen3-embedding-8b")
EMBED_DIMS        = int(os.getenv("DISCOVER_EMBED_DIMS", "1024"))
EMBED_BASE_URL    = os.getenv("DISCOVER_EMBED_BASE_URL", "https://openrouter.ai/api/v1")
EMBED_API_KEY_VAR = "OPENROUTER_API_KEY"
EMBED_PROVIDER_ROUTE = {
    "order": [os.getenv("DISCOVER_EMBED_PROVIDER", "DeepInfra")],
    "allow_fallbacks": True,
}
EMBED_BATCH       = 64
# A 429 is waited out, not reported.
EMBED_MAX_RETRIES = int(os.getenv("DISCOVER_EMBED_MAX_RETRIES", "8"))

# The ONE query-side instruction. Documents never receive it.
QUERY_INSTRUCTION = (
    "Instruct: Given a question from a government official about village-level "
    "planning and spending, retrieve analysis findings that answer it\nQuery: "
)


def semantic_pin() -> dict:
    """Everything that decides what a vector MEANS -- the model, the dimension
    count, the endpoint, the instructions, the normalisation.

    Deliberately excludes `storage_dtype`, which decides only how the number is
    laid down on disk. The distinction is what lets the WP-D10 rebuild reuse the
    fp32 build's vectors instead of re-embedding 40,457 texts against a
    non-deterministic endpoint: the vectors mean the same thing, they are simply
    about to be written narrower.
    """
    # WP-D11b: `base_url` LEFT this dict when the provider moved from Novita to
    # OpenRouter (operator ruling, 2026-09-11). It had stood for "which weights
    # produce the vector", and the switch MEASURED that it no longer does: the
    # same text through Novita and through OpenRouter (DeepInfra and Nebius
    # hosts) agrees at cosine >= 0.99985 on the full 4,096 dimensions, and every
    # source agrees with the stored vectors at >= 0.99983 -- run-to-run noise.
    # Keeping it here would have re-embedded all ~71,000 texts for a change of
    # address. It is still in the FULL pin and every stamp (SERVICE_PIN_FIELDS).
    # Evidence: handoffs/WPD11b_calibration/openrouter_probe_output.txt.
    return {
        "model": EMBED_MODEL,
        "dims": EMBED_DIMS,
        "query_instruction": QUERY_INSTRUCTION,
        "document_instruction": None,          # documents are embedded plain
        "normalisation": "L2, client-side",
    }


def embedding_pin() -> dict:
    """The full pin, meaning plus storage. Copied into the stamp.

    `storage_dtype` is in here, and therefore in the fingerprint, on purpose
    (D10.1): an fp32 file and an fp16 file are read by different code paths, so
    a loader must never be able to open the wrong one quietly. The cache reader
    is the one place that compares `semantic_pin()` instead, and it says why.
    """
    # WP-D11b: `storage_layout` joins `storage_dtype`, for the same reason. A
    # split corpus and an unsplit one are read by different code paths, so the
    # service's pin check refuses a stamp from the other layout outright.
    return dict(semantic_pin(), storage_dtype=STORAGE_DTYPE,
                storage_layout=STORAGE_LAYOUT,
                # WP-D11b: WHERE the vector was fetched, not what it means.
                base_url=EMBED_BASE_URL,
                provider_route=EMBED_PROVIDER_ROUTE)


# The fields of the full pin that say how a vector is STORED, not what it means.
STORAGE_PIN_FIELDS = ("storage_dtype", "storage_layout")
# ... and the ones that say which SERVICE fetched it (WP-D11b). A pre-switch pin
# carries `base_url` inside its meaning half; stripping it from both sides is
# what lets the Novita-built cache be reused, on the measurement above.
SERVICE_PIN_FIELDS = ("base_url", "provider_route")
# The cache reader strips exactly these, and nothing else.
NON_SEMANTIC_PIN_FIELDS = STORAGE_PIN_FIELDS + SERVICE_PIN_FIELDS


def pin_fingerprint() -> str:
    """A short hash of the pin, so a mismatch is one string comparison."""
    return hashlib.sha256(
        json.dumps(embedding_pin(), sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def cache_is_reusable(old_payload: dict) -> bool:
    """May the vectors in a previous build be reused as they stand?

    Yes when the previous build MEANS the same thing by a vector, whatever
    dtype or file layout it wrote. An old file that predates the pin carrying
    a storage field at all compares equal here too, because the storage fields
    are stripped from both sides rather than defaulted on one.
    """
    old_pin = dict(old_payload.get("embedding_pin") or {})
    for name in NON_SEMANTIC_PIN_FIELDS:
        old_pin.pop(name, None)
    return old_pin == semantic_pin()


# =============================================================================
# THE EMBEDDING CLIENT
# =============================================================================
# The key is loaded FROM Insights/.env in place and is never copied, printed or
# written (WPD3 §4.4 bug 1 was this path being wrong and the load silently doing
# nothing -- so a missing key raises here rather than degrading).

def _load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    # The mirror runs from a copy of the tree; the Drive .env is the one that
    # holds keys. Load it too when it is reachable, without overriding anything
    # already set.
    drive_env = ("i:/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW/"
                 "Insights/.env")
    if os.path.exists(drive_env):
        load_dotenv(drive_env)


class Embedder:
    """Qwen3 embeddings, asymmetric. `documents()` plain, `query()` instructed."""

    def __init__(self):
        _load_env()
        key = os.getenv(EMBED_API_KEY_VAR)
        if not key:
            raise SystemExit(
                f"STOP: no {EMBED_API_KEY_VAR} in Insights/.env -- the embedder "
                f"cannot run (precondition 4)."
            )
        from openai import OpenAI
        self._client = OpenAI(api_key=key, base_url=EMBED_BASE_URL)
        self.calls = 0
        self.texts_embedded = 0
        self.rate_limit_waits = 0

    def _raw(self, texts: list) -> np.ndarray:
        out = []
        for i in range(0, len(texts), EMBED_BATCH):
            chunk = texts[i:i + EMBED_BATCH]
            resp = self._with_retry(chunk)
            self.calls += 1
            self.texts_embedded += len(chunk)
            rows = sorted(resp.data, key=lambda d: d.index)
            # A vector of the wrong length is a STOP, never a silent pad or cut:
            # Novita's quiet change of 2026-09 (it began refusing `dimensions`)
            # is the reminder that the endpoint's behaviour is not ours.
            bad = [len(d.embedding) for d in rows if len(d.embedding) != EMBED_DIMS]
            if bad or len(rows) != len(chunk):
                raise SystemExit(
                    f"STOP: the embedding endpoint returned {len(rows)} vectors of "
                    f"lengths {sorted(set(bad)) or [EMBED_DIMS]} for {len(chunk)} "
                    f"texts; the pin says {EMBED_DIMS}.")
            out.extend(d.embedding for d in rows)
        return np.asarray(out, dtype=np.float32)

    def _with_retry(self, chunk: list):
        """The endpoint allows 50 requests a minute and says so in a 429.

        A rate limit is not an error to report, it is a wait to take: the
        alternative is a half-embedded corpus, and a corpus missing 300 vectors
        because a burst was refused would be a retrieval hole with no symptom.
        Backoff is exponential from 5s; anything that is not a rate limit is
        raised immediately, because a bad model id must not be retried into a
        five-minute silence.
        """
        import openai
        delay = 5.0
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                # `encoding_format="float"` explicitly: the OpenAI client
                # otherwise asks for base64, which Novita began refusing in
                # 2026-09 and which is one more thing to depend on.
                # `provider` is OpenRouter's routing field (WP-D11b).
                return self._client.embeddings.create(
                    model=EMBED_MODEL, input=chunk, dimensions=EMBED_DIMS,
                    encoding_format="float",
                    extra_body={"provider": EMBED_PROVIDER_ROUTE},
                )
            except openai.RateLimitError:
                if attempt == EMBED_MAX_RETRIES - 1:
                    raise
                self.rate_limit_waits += 1
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
        raise RuntimeError("unreachable")

    def documents(self, texts: list) -> np.ndarray:
        return l2_normalise(self._raw(texts))

    def query(self, text: str) -> np.ndarray:
        return l2_normalise(self._raw([QUERY_INSTRUCTION + text]))[0]


def l2_normalise(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    if m.ndim == 1:
        m = m.reshape(1, -1)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


# =============================================================================
# COLUMN DISPLAY + GLOSSARY EXPANSION
# =============================================================================
# Display names are presentation only; the glossary text behind them is
# phase5b_report's `column_glossary`, which is the SIGNED WP-D2 Appendix A
# transcribed. Nothing is authored about the data here.

_DISPLAY = {
    "gp_name":                "Gram Panchayat",
    "block_name":             "block",
    "district_name":          "district",
    "fiscal_year":            "fiscal year",
    "month":                  "calendar month",
    "quarter":                "calendar quarter",
    "temporal_grain":         "time unit (month, quarter or fiscal year)",
    "theme":                  "LSDG theme",
    "focus_area_name":        "focus area",
    "asset_category_label":   "asset category",
    "status_label":           "activity status",
    "output_type_label":      "output type",
    "work_type_label":        "type of work",
    "activity_type_label":    "activity type",
    "activity_for_label":     "who the work is for",
    "is_costless":            "costed or costless",
    "tied_untied":            "tied or untied grant",
    "sanction_authority":     "sanctioning authority",
    "sanctioned_scheme_name": "scheme",
    "fund_component_name":    "fund component",
    "measure":                "measure",
    "(varies)":               "several measures",
    # WP-D11: the seven GP profile bands (§12.3). These are DIMENSION display
    # names -- the short phrase a sentence uses in place of the column name --
    # so they name the attribute, not its cut. The cut itself lives in the
    # report's column glossary, which is where a reader who needs "more than
    # half the population" rather than "social composition" will find it.
    "social_composition":     "social composition",
    "gp_size":                "population size band",
    "remoteness":             "distance to a bus stop",
    "digital_readiness":      "office internet and computer",
    "has_panchayat_bhawan":   "panchayat bhawan",
    "has_csc":                "common service centre",
    "plc_available":          "panchayat learning centre",
}

# The ALL-CAPS scaffolding in the glossary is a machine convention, not officer
# language. Softened for the vector; the meaning is untouched.
_GLOSS_SOFTEN = (
    ("UNIT: ", ""), ("TOTALLED", "totalled"), ("COUNTED", "counted"),
    ("AVERAGED", "averaged"), ("SIGNED", "signed"),
    ("PLANNED basis", "planned basis"), ("SANCTIONED basis", "sanctioned basis"),
    ("SPENT basis", "spent basis"), ("CASHBOOK basis", "cashbook basis"),
)

GLOSSARY_SNIPPET_CHARS = 240


def long_view_title(view: str) -> str:
    """The descriptive title from the signed view descriptions."""
    return VIEW_DESCRIPTIONS[view]["title"]


def display_name(col: str) -> str:
    if col in _DISPLAY:
        return _DISPLAY[col]
    return col.replace("_label", "").replace("_name", "").replace("_", " ")


def glossary_snippet(view: str, col: str) -> str:
    """The signed glossary line for a column, softened and capped. '' if none."""
    gloss = VIEW_DESCRIPTIONS.get(view, {}).get("column_glossary", {}).get(col)
    if not gloss:
        return ""
    text = " ".join(str(gloss).split())
    for old, new in _GLOSS_SOFTEN:
        text = text.replace(old, new)
    if len(text) > GLOSSARY_SNIPPET_CHARS:
        cut = text[:GLOSSARY_SNIPPET_CHARS]
        # Cut on a sentence boundary when there is one, else on a word.
        dot = cut.rfind(". ")
        text = cut[:dot + 1] if dot > 80 else cut.rsplit(" ", 1)[0] + " ..."
    return text


# =============================================================================
# COORDINATES PULLED OFF A CANDIDATE
# =============================================================================

GEO_DIMS = ("gp_name", "block_name", "district_name")

# The engine's own SHAPE vocabulary, which appears in `highlight` alongside real
# data values and must never be mistaken for one. This list cannot be "every
# ALL-CAPS token": 'WORK ONGOING' (521 highlights), 'BDO' (11) and
# '5TH STATE FINANCE COMMISSION' (7) are all genuine values of genuine columns.
# It is the closed set the pattern detectors emit, and nothing else.
ENGINE_SHAPE_TOKENS = frozenset({
    "EVEN", "INCREASING", "DECREASING", "PEAK", "VALLEY",
    "ABOVE", "BELOW", "HIGH", "LOW", "NO_PATTERN",
})


def _is_engine_token(value: str) -> bool:
    s = str(value).strip()
    return s in ENGINE_SHAPE_TOKENS or s.startswith("PERIOD_")


def _highlight_values(raw) -> list:
    """The highlight tuple's member VALUES, flattened to strings.

    `highlight` is stored as the repr of a tuple -- "('Barpali',)",
    "(('2024-03', 'HIGH'),)" for outliers. `generate_nl_summary` parses it the
    same way; this reuses that reading rather than inventing a second one.
    """
    if raw in (None, "", "None"):
        return []
    try:
        hl = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return [str(raw)]
    if not isinstance(hl, (tuple, list)):
        hl = (hl,)
    out = []
    for item in hl:
        if isinstance(item, (tuple, list)):
            out.extend(str(x) for x in item)
        else:
            out.append(str(item))
    return [v for v in out if not _is_engine_token(v)]


def named_members(c: MetaInsightCandidate) -> list:
    """Every place / category name this finding actually names, in a stable order.

    Three places carry them and all three are read:
      - the base subspace's filter VALUES  (the slice the finding is about)
      - the commonness members + exception labels, when the finding compares
        ACROSS a named dimension (extending_dimension)
      - the highlight values, when the BREAKDOWN is a named dimension
    """
    names = []

    def add(value):
        s = str(value).strip()
        if s and s not in names:
            names.append(s)

    for _dim, value in sorted(c.base_subspace.filters):
        add(value)
    for cs in c.commonness_sets:
        for m in cs.get("members", []):
            add(m)
        for v in _highlight_values(cs.get("highlight")):
            add(v)
    for e in c.exceptions:
        add(e.get("member_label"))
        for v in _highlight_values(e.get("highlight")):
            add(v)
    return names


def geography_candidates(c: MetaInsightCandidate) -> dict:
    """Which Gram Panchayats / blocks / districts this finding may be ABOUT.

    CANDIDATES, not conclusions: `resolve_geography` confirms each one against
    Ask's registry and drops what does not resolve. Reading the column a value
    sits under is not enough on its own -- an EVENNESS finding broken down by
    `gp_name` carries the highlight `('EVEN',)`, which is the engine describing
    a shape, and taking it for a panchayat put the token 'EVEN' in the
    geography of 1,125 records on the first build.

    Kept per tier and per ROLE, because the two are different questions. A
    finding whose subspace is `gp_name=Chikilli` is about Chikilli; a finding
    that compares across all 20 GPs mentions Chikilli as one member of a
    pattern. Both are legitimate hits for "how is my GP doing" and the roles let
    D5.1 and the answer text tell them apart.
    """
    geo = {"gp_name": [], "block_name": [], "district_name": []}
    roles = {}

    def add(dim, value, role):
        s = str(value).strip()
        if not s:
            return
        if s not in geo[dim]:
            geo[dim].append(s)
        roles.setdefault(s, role)

    for dim, value in sorted(c.base_subspace.filters):
        if dim in GEO_DIMS:
            add(dim, value, "subspace")

    if c.extending_dimension in GEO_DIMS:
        for cs in c.commonness_sets:
            for m in cs.get("members", []):
                add(c.extending_dimension, m, "follows_pattern")
        for e in c.exceptions:
            add(c.extending_dimension, e.get("member_label"), "exception")

    if c.breakdown in GEO_DIMS:
        for cs in c.commonness_sets:
            for v in _highlight_values(cs.get("highlight")):
                add(c.breakdown, v, "highlight")
        for e in c.exceptions:
            for v in _highlight_values(e.get("highlight")):
                add(c.breakdown, v, "highlight")

    return {
        "gp_names":  geo["gp_name"],
        "blocks":    geo["block_name"],
        "districts": geo["district_name"],
        "roles":     roles,
    }


def measures_of(c: MetaInsightCandidate) -> list:
    """The measure column(s) this finding is about.

    A measure-extending finding carries `measure == '(varies)'` and the actual
    measure names are its HDP members, so the literal field is not the answer.
    """
    if c.measure != "(varies)":
        return [c.measure]
    out = []
    for cs in c.commonness_sets:
        for m in cs.get("members", []):
            if str(m) not in out:
                out.append(str(m))
    for e in c.exceptions:
        label = str(e.get("member_label", ""))
        if label and label not in out:
            out.append(label)
    return out


def subspace_phrase(c: MetaInsightCandidate, view: str) -> str:
    """'costed activities' / 'all records in this table' -- the slice, in words."""
    if not c.base_subspace.filters:
        return "all records in this table"
    parts = [f"{display_name(dim)} {value}"
             for dim, value in sorted(c.base_subspace.filters)]
    return "; ".join(parts)


# =============================================================================
# THE ENRICHED RETRIEVAL TEXT
# =============================================================================

MAX_NAMED_IN_TEXT = 30      # a 27-member commonness list is signal; 500 is noise


def _clause(prefix: str, name: str, gloss: str) -> str:
    """'Grouped by block -- <definition>.' with no doubled full stop."""
    text = prefix + " " + name
    if gloss:
        text += " -- " + gloss
    return text.rstrip(".") + "."


def build_embed_text(c: MetaInsightCandidate, view: str) -> str:
    """What actually gets embedded for this finding. Deterministic; no LLM.

    The view's LONG title is used, not the feed's short one: 'Monthly Money
    Flows by Gram Panchayat' is a phrase an officer's question can match,
    'Geo-Month Cash Cube' is a phrase nobody will ever type. The feed's short
    title still travels on the record as `view_title`, unchanged (D16).
    """
    lines = [generate_nl_summary(c), long_view_title(view) + "."]

    for m in measures_of(c)[:4]:
        lines.append(_clause("Measure:", display_name(m), glossary_snippet(view, m)))

    if c.breakdown != "(varies)":
        lines.append(_clause("Grouped by", display_name(c.breakdown),
                             glossary_snippet(view, c.breakdown)))
    else:
        lines.append("Grouped by several different things rather than one.")

    ext = c.extending_dimension
    gloss = "" if ext in ("measure", "temporal_grain") else glossary_snippet(view, ext)
    lines.append(_clause("Compared across", display_name(ext), gloss))

    lines.append("Within " + subspace_phrase(c, view) + ".")

    names = named_members(c)
    if names:
        shown = names[:MAX_NAMED_IN_TEXT]
        tail = "" if len(names) <= MAX_NAMED_IN_TEXT else \
            f" and {len(names) - MAX_NAMED_IN_TEXT} more"
        lines.append("Named: " + ", ".join(shown) + tail + ".")

    return "\n".join(lines)


def build_bare_text(c: MetaInsightCandidate) -> str:
    """Arm A of the D5.1 experiment: the sentence and nothing else."""
    return generate_nl_summary(c)


# =============================================================================
# GEOGRAPHY -> LGD CODES, THROUGH ASK'S REGISTRY
# =============================================================================
# D42 risk note: this couples Discover to Ask's code, read-only and on purpose.
# Nothing is copy-pasted -- drift between two copies of a roster is worse than
# the coupling, and WP-4a is explicit that transliterated Odia names are
# unreliable as TEXT, so the identity that travels is the LGD code.
#
# Blocks and districts have no code in `gram_panchayat` (only `gp_lgd_code`
# does), so their resolved identity is the registry's own canonical STRING --
# reached through the same validator, alias table included, never by fuzzy
# string comparison at query time. Logged in the report as a limitation.

def open_ask_validator():
    """Ask's EntityValidator over the read-only sample DB, or None with a reason."""
    ask_dir = os.path.join(REPO_DIR, "Ask")
    db_path = os.path.join(ask_dir, "data", "panchayat_1.duckdb")
    if not os.path.exists(db_path):
        return None, f"no database at {db_path}"
    if ask_dir not in sys.path:
        sys.path.insert(0, ask_dir)
    try:
        import db_factory
        from query_router.entity_validator import EntityValidator
        adapter = db_factory.open_analytical_db(os.path.abspath(db_path))
        return EntityValidator(adapter), ""
    except Exception as exc:                                   # pragma: no cover
        return None, f"{type(exc).__name__}: {exc}"


def resolve_geography(validator, candidates: dict) -> dict:
    """Candidate names -> the registry's canonical values. Unresolved is DROPPED.

    A GP carries its `gp_lgd_code`, which is the identity everything downstream
    compares on. Blocks and districts have no code in `gram_panchayat`, so their
    resolved identity is the registry's own canonical STRING -- reached through
    the same validator and the same alias table, never by fuzzy comparison at
    query time. That asymmetry is a limitation of the roster, not a design
    choice, and it is reported as one.
    """
    out = {"gp_lgd_codes": [], "gp_names": [], "blocks": [], "districts": [],
           "roles": {}, "rejected": []}

    def try_one(name, etype):
        try:
            return validator.validate(name, etype)
        except Exception:
            return None

    for name in candidates["gp_names"]:
        entity = try_one(name, "gp")
        code = getattr(entity, "resolved_code", None) if entity else None
        if not code:
            out["rejected"].append({"tier": "gp", "name": name})
            continue
        value = getattr(entity, "resolved_value", name)
        if str(code) not in out["gp_lgd_codes"]:
            out["gp_lgd_codes"].append(str(code))
            out["gp_names"].append(value)
        out["roles"].setdefault(str(code), candidates["roles"].get(name, "named"))

    for tier, etype in (("blocks", "block"), ("districts", "district")):
        for name in candidates[tier]:
            entity = try_one(name, etype)
            value = getattr(entity, "resolved_value", None) if entity else None
            if not value:
                out["rejected"].append({"tier": etype, "name": name})
                continue
            if value not in out[tier]:
                out[tier].append(value)
            out["roles"].setdefault(value, candidates["roles"].get(name, "named"))
    return out


# =============================================================================
# BUILD
# =============================================================================

def load_stamp() -> dict:
    path = os.path.join(MI_DIR, "global_feed_source_set.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def feed_index() -> dict:
    """canonical_key -> the feed row, for the 32 findings that made the feed."""
    with open(os.path.join(MI_DIR, "global_feed.json"), encoding="utf-8") as fh:
        feed = json.load(fh)["feed"]
    index = {}
    for row in feed:
        c = MetaInsightCandidate(
            extending_strategy=row["extending_strategy"],
            extending_dimension=row["extending_dimension"],
            pattern_type=row["pattern_type"],
            breakdown=row["breakdown"],
            measure=row["measure"],
            base_subspace=Subspace(frozenset(tuple(f) for f in row["base_subspace"])),
            commonness_sets=row["commonness_sets"],
            exceptions=row["exceptions"],
            hdp_size=row["hdp_size"],
        )
        index[c.canonical_key()] = row
    return index


def ranked_index(view: str) -> dict:
    """canonical_key -> 1-based rank within the view's ranked list."""
    ranked = load_candidates(os.path.join(MI_DIR, f"{view}_ranked.json"))
    return {c.canonical_key(): i + 1 for i, c in enumerate(ranked)}


def build_records(validator) -> tuple:
    """Every candidate surviving twin-merge, as a corpus record. No embeddings."""
    stamp = load_stamp()
    feed = feed_index()
    records, counts = [], {}

    for view in VIEWS:
        raw = load_candidates(os.path.join(MI_DIR, f"{view}_candidates.json"))
        kept, merged = merge_twin_candidates(raw)
        # Canonical key ordering: the file is already in canonical order, but
        # the merge returns passthrough-then-merged, so re-sort to make the
        # record ids reproducible independently of the merge's bookkeeping.
        kept.sort(key=lambda c: c.canonical_key())
        ranks = ranked_index(view)
        counts[view] = {"raw": len(raw), "twin_merged": merged, "corpus": len(kept),
                        "ranked": len(ranks)}

        for i, c in enumerate(kept):
            key = c.canonical_key()
            geo = resolve_geography(validator, geography_candidates(c))
            feed_row = feed.get(key)
            records.append({
                "finding_id":         f"{view[-1]}-{i:05d}",
                "canonical_key":      key,
                "view":               view,
                "view_title":         VIEW_TITLES[view],
                "sentence":           generate_nl_summary(c),
                "pattern_type":       c.pattern_type,
                "extending_strategy": c.extending_strategy,
                "extending_dimension": c.extending_dimension,
                "breakdown":          c.breakdown,
                "measure":            c.measure,
                "measures":           measures_of(c),
                "base_subspace":      [list(f) for f in sorted(c.base_subspace.filters)],
                "subspace_phrase":    subspace_phrase(c, view),
                "hdp_size":           c.hdp_size,
                "commonness_sets":    c.commonness_sets,
                "exceptions":         c.exceptions,
                "merged_twins":       list(c.merged_twins),
                "conciseness":        round(c.conciseness, 6),
                "impact":             round(c.impact, 6),
                "score":              round(c.score, 6),
                "impact_measure_used": c.impact_measure_used,
                "low_temporal_support": bool(c.low_temporal_support),
                "support_note":       c.support_note,
                "view_rank":          ranks.get(key),
                "in_feed":            feed_row is not None,
                "feed_rank":          feed_row["rank"] if feed_row else None,
                "named_members":      named_members(c),
                "geography":          geo,
                "candidate_set_id":   stamp["candidate_set_id"],
                # `bare_text` STAYS. D10 ruling 3 drops the enriched embedded
                # text and nothing else, and this one has a reader:
                # `experiments/run_arms.py` embeds it as arm A of D5.1.
                "bare_text":          build_bare_text(c),
                # NOT stored (D10 ruling 3). The text that was embedded is
                # carried only as far as the embedder and the hash below;
                # `--embed-text <id>` regenerates it from the fields above and
                # checks it against that hash.
                "_embed_text":        build_embed_text(c, view),
            })

    for r in records:
        r["embed_text_sha256"] = hashlib.sha256(
            r["_embed_text"].encode("utf-8")).hexdigest()
        r["bare_text_sha256"] = hashlib.sha256(
            r["bare_text"].encode("utf-8")).hexdigest()
    return records, counts, stamp


def strip_transient(records: list) -> list:
    """Drop the underscore-prefixed build scratch before the records are written.

    The texts themselves are 60 MB of the old file and every byte of them is
    reproducible from what stays; the hashes are what the cache and the audit
    command need, and those are kept.
    """
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]


def load_vector_cache() -> dict:
    """sha256(embed_text) -> vector, from the PREVIOUS build.

    This is what makes the D5.0 gate meet-able: the endpoint is not
    bit-deterministic, so a rebuild that re-embedded everything could never be
    byte-identical. Reuse is keyed on the exact text, so any change to the
    enrichment recipe invalidates exactly the records it changed and no others.
    """
    corpus_path = next((c for c in (CORPUS_PATH, LEGACY_CORPUS_PATH)
                        if os.path.exists(c)), None)
    if corpus_path is None:
        return {}
    try:
        old = read_corpus_json(corpus_path)
    except Exception:
        return {}
    # WP-D11b: the previous build's vectors in whichever layout it wrote -- the
    # parts its stamp names, or the single pre-split .npy. This is what lets the
    # first split build reuse every vector and make no embedding call.
    vectors = load_previous_vectors(VECTORS_PATH, STAMP_PATH)
    if vectors is None:
        return {}
    old_records = old.get("records", [])
    if len(old_records) != len(vectors):
        return {}
    # The SEMANTIC pin, not the fingerprint: a build that wrote fp32 and a build
    # that writes fp16 produce the same vector for the same text, and refusing
    # the old file here would re-embed the whole corpus against an endpoint that
    # is not bit-deterministic -- which is a cost AND a broken determinism gate.
    if not cache_is_reusable(old):
        return {}          # a different pin means different vectors, always
    return {r["embed_text_sha256"]: vectors[i] for i, r in enumerate(old_records)}


def vector_artefacts(manifest: dict | None) -> list:
    """The stamp's `artefacts` entries for the vectors: one per part, or none
    when the build wrote no vectors (`--no-embed`)."""
    if not manifest:
        return []
    return ["metainsights/" + p["file"] for p in manifest["parts"]]


def write_outputs(records, counts, stamp, vectors, embedder, elapsed):
    payload = {
        "what_this_is": (
            "WP-D5 retrieval corpus. One record per MetaInsight candidate that "
            "survives twin-merge, wide by design (D42 ruling 3): the ranked cut "
            "and the 32-finding feed are marked, not selected for. Every "
            "sentence is phase5_ranking.generate_nl_summary -- nothing here "
            "computes, re-reads or rewrites a figure. Vectors live beside this "
            "file as retrieval_corpus.part<N>.npy -- consecutive row slices, "
            "listed with their SHA-256 in the stamp (WP-D11b) -- float16 on disk "
            "and read as float32, row-aligned with `records`. The embedded text "
            "is not stored: "
            "`embed_text_sha256` pins it, and `python "
            "Insights/src/phase5d_retrieval_corpus.py --embed-text <id>` "
            "regenerates it from the record and verifies it (WP-D10)."
        ),
        "candidate_set_id": stamp["candidate_set_id"],
        "source_generated_at": stamp["generated_at"],
        "embedding_pin": embedding_pin(),
        "embedding_pin_fingerprint": pin_fingerprint(),
        "counts": counts,
        "records": strip_transient(records),
    }
    write_corpus_json(CORPUS_PATH, payload)

    manifest = save_vectors(VECTORS_PATH, vectors) if vectors is not None else None

    # The INPUTS this build read, hashed. Both sidecars are excluded BY NAME:
    # `decompose_corpus.*` is a sibling OUTPUT of phase5f, not a source of this
    # build, and the pre-D10 filter (ends in ".json", does not start with
    # "retrieval_corpus") admitted it only because it happened to end in .json --
    # so a retrieval rebuild run after the sidecar existed would have quietly
    # hashed 161 MB of someone else's output into this provenance. The rename
    # forced the question; naming both corpora answers it once.
    source_files = {}
    for name in sorted(os.listdir(MI_DIR)):
        if not (name.endswith(".json") or name.endswith(".json.gz")):
            continue
        if name.startswith("retrieval_corpus") or name.startswith("decompose_corpus"):
            continue
        path = os.path.join(MI_DIR, name)
        source_files[name] = {"sha256": sha256_of(path),
                              "bytes": os.path.getsize(path)}

    with open(STAMP_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "what_this_is": (
                "Provenance for retrieval_corpus.json.gz and its vector parts. "
                "The `generated_at` line is the ONLY field expected to differ "
                "between two consecutive builds (D5.0 gate); everything else, "
                "vectors included, is reproduced from the cache. "
                "`vector_storage` lists the parts in row order with a SHA-256 "
                "each; the loader refuses a missing or altered part (WP-D11b)."
            ),
            "artefacts": (["metainsights/retrieval_corpus.json.gz"]
                          + vector_artefacts(manifest)),
            "candidate_set_id": stamp["candidate_set_id"],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "build_seconds": round(elapsed, 1),
            "embedding_pin": embedding_pin(),
            "embedding_pin_fingerprint": pin_fingerprint(),
            "embedding_calls": getattr(embedder, "calls", 0),
            "texts_embedded": getattr(embedder, "texts_embedded", 0),
            "records": len(records),
            "counts": counts,
            "ranking_prefilter_cap": RANKING_PREFILTER_CAP,
            "source_files": source_files,
            "vector_storage": manifest,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # Only now, with a stamp on disk that names the parts, is the unsplit file
    # retired. Retiring it first would leave a window in which neither layout
    # is readable and the next build would re-embed everything.
    if manifest:
        retire_unsplit(VECTORS_PATH)
    return manifest


# =============================================================================
# THE AUDIT COMMAND  (WP-D10, D10.2)
# =============================================================================
# WP-D5 ruling 7 said "the exact embedded text is stored". D10 ruling 3 amends
# it to "the exact embedded text is REPRODUCIBLE and hash-pinned", and this is
# the reproduction. It rebuilds the text from the stored record alone -- the
# same `build_embed_text` the build called, over the same fields -- and compares
# its SHA-256 to the one on the record.
#
# MATCH means the stored hash and the regenerated text agree, which is the whole
# claim: nothing was lost by not storing 60 MB of strings. MISMATCH means the
# record and its vector no longer describe each other, and the corpus needs
# rebuilding -- so the command exits non-zero and the text is printed either way,
# because an auditor asking what was embedded should get an answer even when the
# answer is "not this".

def candidate_from_record(record: dict) -> MetaInsightCandidate:
    """The candidate a findings record was built from, back out of the record.

    Only the fields `build_embed_text` actually reads are reconstructed, and
    they are read the same way `feed_index` reads a feed row -- one way to turn
    a serialised candidate back into a candidate, not two.
    """
    return MetaInsightCandidate(
        extending_strategy=record["extending_strategy"],
        extending_dimension=record["extending_dimension"],
        pattern_type=record["pattern_type"],
        breakdown=record["breakdown"],
        measure=record["measure"],
        base_subspace=Subspace(frozenset(tuple(f) for f in record["base_subspace"])),
        commonness_sets=record["commonness_sets"],
        exceptions=record["exceptions"],
        hdp_size=record["hdp_size"],
    )


def regenerate_embed_text(record: dict) -> str:
    return build_embed_text(candidate_from_record(record), record["view"])


def audit_embed_text(finding_ids: list) -> int:
    """Print each id's regenerated embed text with MATCH / MISMATCH. 0 if all match."""
    corpus_path = next((c for c in (CORPUS_PATH, LEGACY_CORPUS_PATH)
                        if os.path.exists(c)), None)
    if corpus_path is None:
        raise SystemExit(f"STOP: no corpus at {CORPUS_PATH}. Build it first.")
    payload = read_corpus_json(corpus_path)
    by_id = {r["finding_id"]: r for r in payload["records"]}

    failures = 0
    for finding_id in finding_ids:
        record = by_id.get(finding_id)
        if record is None:
            print(f"{finding_id}  UNKNOWN ID")
            failures += 1
            continue
        text = regenerate_embed_text(record)
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        stored = record["embed_text_sha256"]
        ok = actual == stored
        failures += 0 if ok else 1
        print(f"=== {finding_id}  {'MATCH' if ok else 'MISMATCH'}")
        print(text)
        print(f"--- stored     {stored}")
        print(f"--- regenerated {actual}")
    return 1 if failures else 0


def all_finding_ids() -> list:
    corpus_path = next((c for c in (CORPUS_PATH, LEGACY_CORPUS_PATH)
                        if os.path.exists(c)), None)
    payload = read_corpus_json(corpus_path)
    return [r["finding_id"] for r in payload["records"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WP-D5 D5.0 retrieval corpus build")
    ap.add_argument("--no-embed", action="store_true",
                    help="build the records and skip the vectors (structure check)")
    ap.add_argument("--force-embed", action="store_true",
                    help="ignore the vector cache and re-embed everything")
    ap.add_argument("--embed-text", nargs="+", metavar="ID",
                    help="regenerate these records' embedded text from their "
                         "stored fields and check it against embed_text_sha256 "
                         "(D10.2). 'ALL' checks every record.")
    args = ap.parse_args(argv)

    if args.embed_text:
        ids = (all_finding_ids() if args.embed_text == ["ALL"]
               else args.embed_text)
        return audit_embed_text(ids)

    t0 = time.time()
    validator, why = open_ask_validator()
    # A missing registry is a STOP, not a degradation. Ask's own bootstrap
    # lesson is that a view-less adapter fails SOFTLY -- registries load empty
    # and everything downstream passes vacuously. Here that would mean a corpus
    # with no geography at all, which still builds, still embeds, and quietly
    # makes every own-GP question unanswerable.
    if validator is None:
        raise SystemExit(
            f"STOP: Ask's entity registry could not be opened ({why}). "
            f"Geography resolution is load-bearing for D5.1; building without "
            f"it would produce a corpus that looks complete and answers no "
            f"own-GP question."
        )
    n_gp = len(validator.registry_values("gp"))
    if n_gp == 0:
        raise SystemExit(
            "STOP: Ask's GP registry loaded EMPTY. That is the soft-failure "
            "mode db_factory.open_analytical_db exists to prevent -- check the "
            "adapter has its views."
        )
    print(f"  Ask registry: {n_gp} GPs, "
          f"{len(validator.registry_values('block'))} blocks, "
          f"{len(validator.registry_values('district'))} districts")

    records, counts, stamp = build_records(validator)
    print(f"  {len(records):,} corpus records "
          + ", ".join(f"{v}={counts[v]['corpus']:,}" for v in VIEWS))
    with_gp = sum(1 for r in records if r["geography"]["gp_lgd_codes"])
    rejected = sum(len(r["geography"]["rejected"]) for r in records)
    print(f"  geography: {with_gp:,} records name a registry-confirmed GP; "
          f"{rejected:,} candidate names rejected as non-geographic")
    distinct_bare = len({r["bare_text_sha256"] for r in records})
    distinct_rich = len({r["embed_text_sha256"] for r in records})
    print(f"  distinct texts: bare sentence {distinct_bare:,}, "
          f"enriched {distinct_rich:,} (of {len(records):,})")

    embedder, vectors = None, None
    if not args.no_embed:
        cache = {} if args.force_embed else load_vector_cache()
        need = [r for r in records if r["embed_text_sha256"] not in cache]
        print(f"  vectors: {len(records) - len(need):,} reused from cache, "
              f"{len(need):,} to embed")
        if need:
            embedder = Embedder()
            fresh = embedder.documents([r["_embed_text"] for r in need])
            for r, v in zip(need, fresh):
                cache[r["embed_text_sha256"]] = v
        # NOT re-normalised here. `Embedder.documents` normalises once, at the
        # moment of embedding, and float32 L2-normalisation is not idempotent:
        # a second pass over already-unit vectors moves the last bit of some
        # components and the first attempt at this gate failed on exactly that
        # -- 0 texts re-embedded and a different .npy anyway.
        vectors = np.stack([np.asarray(cache[r["embed_text_sha256"]],
                                       dtype=np.float32) for r in records])

    manifest = write_outputs(records, counts, stamp, vectors, embedder,
                             time.time() - t0)
    print(f"  wrote {CORPUS_PATH}")
    if manifest:
        print(f"  wrote vectors shape={tuple(manifest['shape'])} as "
              f"{len(manifest['parts'])} part(s), matrix sha256 "
              f"{manifest['matrix_sha256'][:16]}")
        for part in manifest["parts"]:
            print(f"    {part['file']}  {part['rows']:,} rows  "
                  f"{part['bytes'] / 1e6:.1f} MB  sha256 {part['sha256'][:16]}")
    print(f"  wrote {STAMP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

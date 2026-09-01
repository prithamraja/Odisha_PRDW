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
VIEWS = ("view1", "view2", "view3")

CORPUS_PATH  = os.path.join(MI_DIR, "retrieval_corpus.json")
VECTORS_PATH = os.path.join(MI_DIR, "retrieval_corpus.npy")
STAMP_PATH   = os.path.join(MI_DIR, "retrieval_corpus_stamp.json")


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
EMBED_MODEL       = os.getenv("DISCOVER_EMBED_MODEL", "qwen/qwen3-embedding-8b")
EMBED_DIMS        = int(os.getenv("DISCOVER_EMBED_DIMS", "1024"))
EMBED_BASE_URL    = os.getenv("DISCOVER_EMBED_BASE_URL", "https://api.novita.ai/openai")
EMBED_API_KEY_VAR = "NOVITA_API_KEY"
EMBED_BATCH       = 64
# The endpoint publishes 50 requests/minute; a 429 is waited out, not reported.
EMBED_MAX_RETRIES = int(os.getenv("DISCOVER_EMBED_MAX_RETRIES", "8"))

# The ONE query-side instruction. Documents never receive it.
QUERY_INSTRUCTION = (
    "Instruct: Given a question from a government official about village-level "
    "planning and spending, retrieve analysis findings that answer it\nQuery: "
)


def embedding_pin() -> dict:
    """Everything that decides what a vector means. Copied into the stamp."""
    return {
        "model": EMBED_MODEL,
        "dims": EMBED_DIMS,
        "base_url": EMBED_BASE_URL,
        "query_instruction": QUERY_INSTRUCTION,
        "document_instruction": None,          # documents are embedded plain
        "normalisation": "L2, client-side",
        "storage_dtype": "float32",
    }


def pin_fingerprint() -> str:
    """A short hash of the pin, so a mismatch is one string comparison."""
    return hashlib.sha256(
        json.dumps(embedding_pin(), sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


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
            out.extend(d.embedding for d in resp.data)
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
                return self._client.embeddings.create(
                    model=EMBED_MODEL, input=chunk, dimensions=EMBED_DIMS,
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
                "embed_text":         build_embed_text(c, view),
                "bare_text":          build_bare_text(c),
                "candidate_set_id":   stamp["candidate_set_id"],
            })

    for r in records:
        r["embed_text_sha256"] = hashlib.sha256(
            r["embed_text"].encode("utf-8")).hexdigest()
        r["bare_text_sha256"] = hashlib.sha256(
            r["bare_text"].encode("utf-8")).hexdigest()
    return records, counts, stamp


def load_vector_cache() -> dict:
    """sha256(embed_text) -> vector, from the PREVIOUS build.

    This is what makes the D5.0 gate meet-able: the endpoint is not
    bit-deterministic, so a rebuild that re-embedded everything could never be
    byte-identical. Reuse is keyed on the exact text, so any change to the
    enrichment recipe invalidates exactly the records it changed and no others.
    """
    if not (os.path.exists(CORPUS_PATH) and os.path.exists(VECTORS_PATH)):
        return {}
    try:
        with open(CORPUS_PATH, encoding="utf-8") as fh:
            old = json.load(fh)
        vectors = np.load(VECTORS_PATH)
    except Exception:
        return {}
    old_records = old.get("records", [])
    if len(old_records) != len(vectors):
        return {}
    if old.get("embedding_pin_fingerprint") != pin_fingerprint():
        return {}          # a different pin means different vectors, always
    return {r["embed_text_sha256"]: vectors[i] for i, r in enumerate(old_records)}


def write_outputs(records, counts, stamp, vectors, embedder, elapsed):
    payload = {
        "what_this_is": (
            "WP-D5 retrieval corpus. One record per MetaInsight candidate that "
            "survives twin-merge, wide by design (D42 ruling 3): the ranked cut "
            "and the 32-finding feed are marked, not selected for. Every "
            "sentence is phase5_ranking.generate_nl_summary -- nothing here "
            "computes, re-reads or rewrites a figure. Vectors live beside this "
            "file in retrieval_corpus.npy, row-aligned with `records`."
        ),
        "candidate_set_id": stamp["candidate_set_id"],
        "source_generated_at": stamp["generated_at"],
        "embedding_pin": embedding_pin(),
        "embedding_pin_fingerprint": pin_fingerprint(),
        "counts": counts,
        "records": records,
    }
    with open(CORPUS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")

    if vectors is not None:
        np.save(VECTORS_PATH, vectors)

    source_files = {}
    for name in sorted(os.listdir(MI_DIR)):
        if not name.endswith(".json") or name.startswith("retrieval_corpus"):
            continue
        path = os.path.join(MI_DIR, name)
        source_files[name] = {"sha256": sha256_of(path),
                              "bytes": os.path.getsize(path)}

    with open(STAMP_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "what_this_is": (
                "Provenance for retrieval_corpus.json/.npy. The `generated_at` "
                "line is the ONLY field expected to differ between two "
                "consecutive builds (D5.0 gate); everything else, vectors "
                "included, is reproduced from the cache."
            ),
            "artefacts": ["metainsights/retrieval_corpus.json",
                          "metainsights/retrieval_corpus.npy"],
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
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WP-D5 D5.0 retrieval corpus build")
    ap.add_argument("--no-embed", action="store_true",
                    help="build the records and skip the vectors (structure check)")
    ap.add_argument("--force-embed", action="store_true",
                    help="ignore the vector cache and re-embed everything")
    args = ap.parse_args(argv)

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
            fresh = embedder.documents([r["embed_text"] for r in need])
            for r, v in zip(need, fresh):
                cache[r["embed_text_sha256"]] = v
        # NOT re-normalised here. `Embedder.documents` normalises once, at the
        # moment of embedding, and float32 L2-normalisation is not idempotent:
        # a second pass over already-unit vectors moves the last bit of some
        # components and the first attempt at this gate failed on exactly that
        # -- 0 texts re-embedded and a different .npy anyway.
        vectors = np.stack([cache[r["embed_text_sha256"]] for r in records])

    write_outputs(records, counts, stamp, vectors, embedder, time.time() - t0)
    print(f"  wrote {CORPUS_PATH}")
    if vectors is not None:
        print(f"  wrote {VECTORS_PATH}  shape={vectors.shape} "
              f"({os.path.getsize(VECTORS_PATH) / 1e6:.1f} MB)")
    print(f"  wrote {STAMP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Deterministic query preparation: expansion, then geography and measure slots.

Three jobs, all deterministic — no model runs here.

1. **Expansion** (D42 ruling 7). The query passes through
   `query_expansion.json` before it is embedded, so 'XV FC' and
   'XV Finance Commission' reach the same place. Data file, not code.

2. **Geography slots**, resolved through **Ask's `EntityValidator`** to LGD
   codes — not by string similarity. WP-4a is explicit that transliterated Odia
   names are unreliable as text, so the identity that travels is the code. The
   validator is imported, never copied: two copies of a roster drift, and drift
   is worse than the coupling (D42 risk note).

3. **Measure slots**, through `measure_keywords.json` — the second authored
   data file, on the SBM-dictionary precedent.

What this module deliberately does NOT do: fuzzy-match a place name that the
registry rejects. An unresolvable place is no geography at all, and the answer
then rides on cosine and, if nothing clears the floor, says so honestly. Ask's
product refuses rather than guesses at geography, and a Discover answer that
silently attached the wrong panchayat would be exactly the confidently-wrong
class D5.3 measures.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from . import config


# ── 1. Expansion ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _expansion_table() -> tuple:
    """(one compiled alternation, {lowercased surface: long form}).

    ONE regex, applied in ONE pass. The alternatives are sorted longest-first
    because Python's alternation is leftmost-FIRST rather than leftmost-longest,
    so 'xv fc' has to be offered before 'fc' or the short one wins. A single
    pass is also what makes the rewrite safe: text this function has already
    inserted is behind the cursor and can never be expanded again, so
    'GP' -> 'Gram Panchayat (GP)' cannot loop.
    """
    with open(config.DATA_QUERY_EXPANSION, encoding="utf-8") as fh:
        entries = json.load(fh)["expansions"]
    entries.sort(key=lambda e: -len(e["match"]))
    table = {e["match"].lower(): e["long_form"] for e in entries}
    alternation = "|".join(re.escape(e["match"]) for e in entries)
    pattern = re.compile(
        r"(?<![A-Za-z0-9])(?:" + alternation + r")(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    return pattern, table


def expand(question: str) -> tuple:
    """('the expanded question', [what was expanded]). Deterministic.

    An abbreviation is REWRITTEN as 'long form (surface form)' rather than
    replaced, so the officer's own word survives into the vector alongside the
    form the corpus uses.
    """
    pattern, table = _expansion_table()
    applied = []

    def replace(m):
        surface = m.group(0)
        long_form = table[surface.lower()]
        applied.append({"surface": surface, "long_form": long_form})
        return f"{long_form} ({surface})"

    return pattern.sub(replace, question), applied


# ── 2 + 3. Slots ─────────────────────────────────────────────────────────────

@dataclass
class Slots:
    question: str
    expanded: str
    expansions: list = field(default_factory=list)
    gp_lgd_codes: list = field(default_factory=list)
    gp_names: list = field(default_factory=list)
    blocks: list = field(default_factory=list)
    districts: list = field(default_factory=list)
    measures: list = field(default_factory=list)
    measure_phrases: list = field(default_factory=list)

    @property
    def has_geography(self) -> bool:
        return bool(self.gp_lgd_codes or self.blocks or self.districts)

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "expanded": self.expanded,
            "expansions": self.expansions,
            "gp_lgd_codes": self.gp_lgd_codes,
            "gp_names": self.gp_names,
            "blocks": self.blocks,
            "districts": self.districts,
            "measures": self.measures,
            "measure_phrases": self.measure_phrases,
        }


class SlotExtractor:
    """Holds Ask's registry open. One instance per process."""

    def __init__(self, validator=None):
        self._validator = validator if validator is not None else _open_validator()
        self._geo_vocab = self._build_geo_vocab()
        self._measure_map = _load_measure_keywords()

    # -- geography ------------------------------------------------------------
    def _build_geo_vocab(self) -> list:
        """(compiled pattern, surface, entity_type) for every registry value.

        The vocabulary is ASK'S, read from the database at startup, so the
        statewide extract grows 20 GPs to ~6,800 with no edit here (Ask's
        decision D4, inherited).
        """
        vocab = []
        for etype in ("gp", "block", "district"):
            for value in self._validator.registry_values(etype):
                vocab.append((_word_pattern(value), value, etype))
        # Ask's alias tables, so 'Khurda' and 'Sundergarh' work here too. Read,
        # not re-authored — one alias table for both products.
        from query_router import entity_validator as ev
        for aliases, etype in ((ev._DISTRICT_ALIASES, "district"),
                               (ev._BLOCK_ALIASES, "block"),
                               (ev._GP_ALIASES, "gp")):
            for alias in aliases:
                vocab.append((_word_pattern(alias), alias, etype))
        # Longest surface first: 'Tangi Choudwar' must win over 'Tangi'.
        vocab.sort(key=lambda v: -len(v[1]))
        return vocab

    def geography(self, text: str) -> dict:
        found = {"gp_lgd_codes": [], "gp_names": [], "blocks": [], "districts": []}
        # Spans are tracked PER TIER, not globally. Within a tier a longer name
        # must swallow a shorter one — 'Tangi' sits inside 'Tangi Choudwar' and
        # only the block that was meant should match. ACROSS tiers the same
        # span may legitimately resolve twice: 'Kalimela' and 'Bheden' are each
        # both a Gram Panchayat and a block in this sample, and an officer who
        # types one has not said which. Boosting both is the honest reading;
        # picking one silently is the confidently-wrong class.
        seen_spans = {"gp": [], "block": [], "district": []}
        for pattern, surface, etype in self._geo_vocab:
            m = pattern.search(text)
            if not m:
                continue
            if any(m.start() < e and m.end() > s for s, e in seen_spans[etype]):
                continue
            try:
                entity = self._validator.validate(surface, etype)
            except Exception:
                continue
            resolved = getattr(entity, "resolved_value", None)
            if not resolved:
                continue
            if etype == "gp":
                code = getattr(entity, "resolved_code", None)
                if not code:
                    continue
                if str(code) not in found["gp_lgd_codes"]:
                    found["gp_lgd_codes"].append(str(code))
                    found["gp_names"].append(resolved)
            else:
                key = "blocks" if etype == "block" else "districts"
                if resolved not in found[key]:
                    found[key].append(resolved)
            seen_spans[etype].append((m.start(), m.end()))
        return found

    # -- measures -------------------------------------------------------------
    def measures(self, text: str) -> tuple:
        hit_measures, hit_phrases = [], []
        for pattern, phrase, measures in self._measure_map:
            if not pattern.search(text):
                continue
            hit_phrases.append(phrase)
            for m in measures:
                if m not in hit_measures:
                    hit_measures.append(m)
        return hit_measures, hit_phrases

    # -- the whole job --------------------------------------------------------
    def extract(self, question: str) -> Slots:
        expanded, applied = expand(question)
        # Geography is read from the ORIGINAL text: expansion rewrites 'GP' to
        # 'Gram Panchayat (GP)' and a place name must not be matched inside a
        # phrase the expansion inserted.
        geo = self.geography(question)
        measures, phrases = self.measures(expanded)
        return Slots(
            question=question, expanded=expanded, expansions=applied,
            measures=measures, measure_phrases=phrases, **geo,
        )


def _word_pattern(value: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(str(value).strip())
                      + r"(?![A-Za-z0-9])", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_measure_keywords() -> tuple:
    with open(config.DATA_MEASURE_KEYWORDS, encoding="utf-8") as fh:
        entries = json.load(fh)["keywords"]
    out = []
    for entry in entries:
        for phrase in entry["phrases"]:
            out.append((_word_pattern(phrase), phrase, entry["measures"]))
    out.sort(key=lambda e: -len(e[1]))
    return tuple(out)


def _open_validator():
    """Ask's EntityValidator over the read-only sample DB. Loud on failure."""
    import db_factory
    from query_router.entity_validator import EntityValidator
    if not config.ASK_DB_PATH.exists():
        raise SystemExit(
            f"STOP: no database at {config.ASK_DB_PATH}. DiscoverChat resolves "
            f"geography through Ask's registry and will not start without it."
        )
    adapter = db_factory.open_analytical_db(str(config.ASK_DB_PATH))
    validator = EntityValidator(adapter)
    if not validator.registry_values("gp"):
        raise SystemExit(
            "STOP: Ask's GP registry loaded EMPTY — the soft-failure mode "
            "db_factory.open_analytical_db exists to prevent. Every own-GP "
            "question would silently miss."
        )
    return validator

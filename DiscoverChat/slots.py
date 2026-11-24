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
    # WP-D15 T1: where in the text each place name stood -- one entry per
    # occurrence, {"level", "code" (Gram Panchayats only), "name", "start",
    # "end"}. Read by `place.resolve` to tell one mention that resolved to two
    # levels from two mentions. Deliberately NOT in `as_dict`, so the
    # retrieval payload every caller already logs is unchanged.
    mentions: list = field(default_factory=list)
    # WP-D15b: how every place was read -- {"level", "code", "name", "start",
    # "end", "how": exact | alias | loose, "typed"} and, for a loose reading,
    # "score" and "others" (up to three other close names) -- and every word
    # marked as a place that read as nothing ({"typed", "level", "start",
    # "end", "close"}). Empty with DISCOVERCHAT_LOOSE_PLACES=0. Not in
    # `as_dict`, like `mentions`.
    readings: list = field(default_factory=list)
    not_found: list = field(default_factory=list)

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
        self._alias_surfaces = set()            # WP-D15b: (level, casefolded alias)
        for aliases, etype in ((ev._DISTRICT_ALIASES, "district"),
                               (ev._BLOCK_ALIASES, "block"),
                               (ev._GP_ALIASES, "gp")):
            for alias in aliases:
                vocab.append((_word_pattern(alias), alias, etype))
                self._alias_surfaces.add((etype, str(alias).casefold()))
        # Longest surface first: 'Tangi Choudwar' must win over 'Tangi'.
        vocab.sort(key=lambda v: -len(v[1]))
        return vocab

    def geography(self, text: str) -> dict:
        """The places in `text`: the four fields and `mentions` (WP-D15).
        With the loose pass on, its readings fill these fields too; how each
        place was read is returned by `read_places`."""
        found = self.read_places(text)
        found.pop("readings", None)
        found.pop("not_found", None)
        return found

    def read_places(self, text: str) -> dict:
        """`geography`'s fields plus, with the loose pass on (WP-D15b),
        `readings` (how every place was read) and `not_found` (words marked
        as a place that read as nothing)."""
        found = {"gp_lgd_codes": [], "gp_names": [], "blocks": [], "districts": []}
        # Spans are tracked PER TIER, not globally. Within a tier a longer name
        # must swallow a shorter one — 'Tangi' sits inside 'Tangi Choudwar' and
        # only the block that was meant should match. ACROSS tiers the same
        # span may legitimately resolve twice: 'Kalimela' and 'Bheden' are each
        # both a Gram Panchayat and a block in this sample, and an officer who
        # types one has not said which. Boosting both is the honest reading;
        # picking one silently is the confidently-wrong class.
        seen_spans = {"gp": [], "block": [], "district": []}
        # WP-D15 T1: every occurrence of every name accepted below, with its
        # position. Built beside the existing logic and never read by it, so
        # the four fields above keep exactly the values they had.
        mentions, taken = [], {"gp": [], "block": [], "district": []}
        how = {}         # WP-D15b: (level, start, end) -> "exact" | "alias"
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
            for occ in pattern.finditer(text):
                if any(occ.start() < e and occ.end() > s
                       for s, e in taken[etype]):
                    continue
                taken[etype].append((occ.start(), occ.end()))
                mentions.append({
                    "level": etype,
                    "code": str(entity.resolved_code) if etype == "gp" else None,
                    "name": resolved, "start": occ.start(), "end": occ.end()})
                how[(etype, occ.start(), occ.end())] = (
                    "alias" if ((etype, str(surface).casefold())
                                in self._alias_surfaces
                                and str(surface).casefold()
                                != str(resolved).casefold())
                    else "exact")
        found["mentions"] = sorted(mentions, key=lambda x: (x["start"], x["level"]))
        # WP-D15b: the loose pass, after the exact one. With the switch off
        # nothing below runs and `found` is exactly the exact reading.
        if config.LOOSE_PLACES:
            self._loose(text, found, how)
        return found

    # -- WP-D15b: the loose pass ----------------------------------------------
    def _loose_setup(self):
        """Built once, on first use: the ordinary words less every token of
        every registry name and alias; per level, the registry names in Ask's
        comparison form, Ask's cut-off, and the GP codes."""
        if getattr(self, "_loose_ready", False):
            return
        from query_router import entity_validator as ev
        self._norm = ev._collapse_ws
        names_tokens = set()
        self._choices, self._cutoff, self._gp_code = {}, {}, {}
        for level in LEVELS:
            values = list(self._validator.registry_values(level))
            self._choices[level] = (values, [self._norm(v) for v in values])
            self._cutoff[level] = ev.REGISTRY_CONFIG[level]["fuzzy_threshold"]
            for v in values:
                names_tokens |= {w.lower() for w in _TOKEN.findall(str(v))}
        for _, surface, _ in self._geo_vocab:
            names_tokens |= {w.lower() for w in _TOKEN.findall(str(surface))}
        self._ordinary = (_load_ordinary_words() | _LEVEL_WORDS) - names_tokens
        self._loose_ready = True

    def _code_of(self, name: str) -> str | None:
        if name not in self._gp_code:
            try:
                entity = self._validator.validate(name, "gp")
                self._gp_code[name] = str(getattr(entity, "resolved_code", "")) or None
            except Exception:
                self._gp_code[name] = None
        return self._gp_code[name]

    def _score(self, typed: str, level: str, floor: float) -> list:
        """[(name, score)] at `level` scoring at least `floor`, best first,
        with Ask's scorer on Ask's comparison form."""
        from rapidfuzz import fuzz, process
        values, normed = self._choices[level]
        hits = process.extract(self._norm(typed), normed, scorer=fuzz.WRatio,
                               score_cutoff=floor, limit=None)
        return sorted(((values[i], round(s, 1)) for _, s, i in hits),
                      key=lambda h: (-h[1], h[0]))

    def _loose(self, text: str, found: dict, how: dict) -> None:
        self._loose_setup()
        mentions = found["mentions"]
        taken = [(m["start"], m["end"]) for m in mentions]
        tokens = [(m.start(), m.end(), m.group(0)) for m in _TOKEN.finditer(text)]

        def eligible(tok, inside_exact_ok=False):
            s, e, w = tok
            # Under 3 letters ("is", "in", "of") a word is never part of a
            # name tried loosely; the vocabulary keeps words of 3 or more.
            if len(w) < 3 or w.lower() in self._ordinary:
                return False
            if not inside_exact_ok and any(s < te and e > ts for ts, te in taken):
                return False
            return True

        spans = []                                   # (start, end, typed, n words)
        for i in range(len(tokens)):
            for k in (1, 2, 3):
                run = tokens[i:i + k]
                if len(run) < k or not all(eligible(t) for t in run):
                    break
                if any(not _GAP.fullmatch(text[a[1]:b[0]])
                       for a, b in zip(run, run[1:])):
                    break
                letters = sum(len(t[2]) for t in run)
                if letters < config.LOOSE_MIN_LETTERS:
                    continue
                spans.append((run[0][0], run[-1][1], text[run[0][0]:run[-1][1]], k))

        # Every span tried, at the marked level only when the text marks one.
        hits = []                                     # (span, [(level, name, score)])
        tried = []
        for start, end, typed, k in spans:
            marked = marked_level(text, start, end)
            levels = [marked] if marked else list(LEVELS)
            got = [(lv, name, score) for lv in levels
                   for name, score in self._score(typed, lv, self._cutoff[lv])]
            tried.append({"typed": typed, "start": start, "end": end,
                          "marked": marked, "hit": bool(got)})
            if got:
                hits.append(((start, end, typed, k), got))
        # What this call tried and skipped -- read by the WP-D15b harness for
        # its report; never by the service.
        self.last_loose = {"tokens": len(tokens),
                           "skipped": sum(1 for t in tokens if not eligible(t)),
                           "tried": tried}

        # T1 point 9: a word that matched exactly at one level but is marked as
        # another is tried loosely at the marked level, and only then.
        replaced = []
        for (start, end) in sorted({(m["start"], m["end"]) for m in mentions}):
            levels_here = {m["level"] for m in mentions
                           if (m["start"], m["end"]) == (start, end)}
            marked = marked_level(text, start, end)
            if marked and marked not in levels_here:
                got = [(marked, name, score) for name, score in
                       self._score(text[start:end], marked, self._cutoff[marked])]
                if got:
                    hits.append(((start, end, text[start:end], 1), got))
                    replaced.append((start, end))

        # Choose: the best-scoring span first; a tie goes to the longer span.
        def best(item):
            return max(score for _, _, score in item[1])
        hits.sort(key=lambda h: (-best(h), -(h[0][1] - h[0][0]), h[0][0]))
        chosen, used = [], []
        for span, got in hits:
            s, e = span[0], span[1]
            if any(s < ue and e > us for us, ue in used):
                continue
            used.append((s, e))
            chosen.append((span, got))

        # The exact mentions T1.9 replaced leave the reading.
        if replaced:
            gone = [m for m in mentions if (m["start"], m["end"]) in replaced
                    and any((m["start"], m["end"]) == (c[0][0], c[0][1])
                            for c in chosen)]
            for m in gone:
                mentions.remove(m)
                how.pop((m["level"], m["start"], m["end"]), None)
            self._refill(found, mentions)

        loose = []
        for (start, end, typed, _), got in sorted(chosen, key=lambda c: c[0][0]):
            ordered = sorted(got, key=lambda g: (-g[2], _RANK[g[0]], g[1]))
            level, name, score = ordered[0]
            levels = [(level, name, score)]
            twin = next((g for g in ordered[1:] if g[1].casefold() == name.casefold()
                         and g[0] != level), None)
            if twin:
                levels.append(twin)
            others = [g for g in ordered[1:] if g is not twin
                      and (g[0], g[1]) not in {(lv, nm) for lv, nm, _ in levels}][:3]
            other_list = [{"level": lv, "name": nm, "score": sc,
                           "code": self._code_of(nm) if lv == "gp" else None}
                          for lv, nm, sc in others]
            for lv, nm, sc in levels:
                code = self._code_of(nm) if lv == "gp" else None
                if lv == "gp" and not code:
                    continue
                mention = {"level": lv, "code": code, "name": nm,
                           "start": start, "end": end}
                mentions.append(mention)
                loose.append({**mention, "how": "loose", "typed": typed,
                              "score": sc, "others": other_list})
                self._add(found, lv, nm, code)
        mentions.sort(key=lambda x: (x["start"], x["level"]))

        readings = [{**m, "how": how.get((m["level"], m["start"], m["end"]), "exact"),
                     "typed": text[m["start"]:m["end"]]}
                    for m in mentions
                    if (m["level"], m["start"], m["end"]) in how]
        readings += loose
        readings.sort(key=lambda r: (r["start"], r["level"]))
        found["readings"] = readings

        # T3: a word marked as a place that reads as nothing.
        read_spans = [(r["start"], r["end"]) for r in readings]
        not_found = []
        for start, end, typed, k in sorted(spans, key=lambda s: (-(s[1] - s[0]), s[0])):
            marked = marked_level(text, start, end)
            if not marked:
                continue
            # Only a word written as a name -- an initial capital -- is taken
            # for a place the officer named. Measured on set A: the marked
            # words that are not places are Hindi and Odia words typed in
            # English ("kitne GP", "kaunse GP", "dusre panchayat", "jillare
            # block"), all lowercase; the vocabulary holds English only.
            if not typed[:1].isupper():
                continue
            if any(start < e and end > s for s, e in read_spans):
                continue
            if any(start < nf["end"] and end > nf["start"] for nf in not_found):
                continue
            close = [{"level": marked, "name": nm, "score": sc}
                     for nm, sc in self._score(typed, marked, CLOSE_NAME_FLOOR)
                     if sc < self._cutoff[marked]][:3]
            not_found.append({"typed": typed, "level": marked, "start": start,
                              "end": end, "close": close})
        found["not_found"] = sorted(not_found, key=lambda n: n["start"])

    @staticmethod
    def _add(found: dict, level: str, name: str, code) -> None:
        if level == "gp":
            if code not in found["gp_lgd_codes"]:
                found["gp_lgd_codes"].append(code)
                found["gp_names"].append(name)
        else:
            key = "blocks" if level == "block" else "districts"
            if name not in found[key]:
                found[key].append(name)

    @staticmethod
    def _refill(found: dict, mentions: list) -> None:
        """After T1.9 removed an exact mention: keep in the four fields only
        what some remaining mention still names (their order kept)."""
        codes = {m["code"] for m in mentions if m["level"] == "gp"}
        keep = [(c, n) for c, n in zip(found["gp_lgd_codes"], found["gp_names"])
                if c in codes]
        found["gp_lgd_codes"] = [c for c, _ in keep]
        found["gp_names"] = [n for _, n in keep]
        for level, key in (("block", "blocks"), ("district", "districts")):
            names = {m["name"] for m in mentions if m["level"] == level}
            found[key] = [n for n in found[key] if n in names]

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
        geo = self.read_places(question)
        measures, phrases = self.measures(expanded)
        return Slots(
            question=question, expanded=expanded, expansions=applied,
            measures=measures, measure_phrases=phrases, **geo,
        )


# ── WP-D15b: the loose pass's small parts ────────────────────────────────────
LEVELS = ("district", "block", "gp")
# Tie order (R4's: the larger place first), then the name's alphabet.
_RANK = {"district": 0, "block": 1, "gp": 2}
# A word of the text: letters, joined by an apostrophe or a hyphen.
_TOKEN = re.compile(r"[A-Za-z]+(?:['\-][A-Za-z]+)*")
# Neighbouring words of a pair or triple are separated by spaces only -- a
# comma or a full stop ends a name.
_GAP = re.compile(r"[ \t]+")
# Level words are marks, never part of a name tried loosely.
_LEVEL_WORDS = {"block", "blocks", "district", "districts", "gp", "gps",
                "gram", "panchayat", "panchayats"}
# T3: close names under the cut-off are offered from this score (the brief's
# 80, stated in WPD15b T3 point 3; Ask's cut-off is read, never restated).
CLOSE_NAME_FLOOR = 80

# The marks of T3 point 1, exactly the brief's list: a level word directly
# after the word, or "block of", "district of", "GP of", "Gram Panchayat of",
# "panchayat of" directly before it. (WP-D15's R4 also reads a bare "GP X";
# here that made "each GP during 2024" mark "during", so it is not a mark.)
_MARK_AFTER = (
    ("gp", re.compile(r"^\s+(?:G\.P\.|(?:GP|Gram\s+Panchayat|panchayat)\b)", re.I)),
    ("block", re.compile(r"^\s+block\b", re.I)),
    ("district", re.compile(r"^\s+district\b", re.I)),
)
_MARK_BEFORE = (
    ("gp", re.compile(r"(?<![A-Za-z0-9])(?:GP|Gram\s+Panchayat|panchayat)\s+of\s+$", re.I)),
    ("block", re.compile(r"(?<![A-Za-z0-9])block\s+of\s+$", re.I)),
    ("district", re.compile(r"(?<![A-Za-z0-9])district\s+of\s+$", re.I)),
)


def marked_level(text: str, start: int, end: int) -> str | None:
    """The level the words next to text[start:end] mark it as, or None."""
    after, before = text[end:], text[:start]
    for level, pattern in _MARK_AFTER:
        if pattern.match(after):
            return level
    for level, pattern in _MARK_BEFORE:
        if pattern.search(before):
            return level
    return None


@lru_cache(maxsize=1)
def _load_ordinary_words() -> frozenset:
    with open(config.DATA_ORDINARY_WORDS, encoding="utf-8") as fh:
        return frozenset(w.lower() for w in json.load(fh)["words"])


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

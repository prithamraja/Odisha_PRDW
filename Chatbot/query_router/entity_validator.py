"""
Validates extracted entities against the AP Agriculture registries.

Four validation kinds, chosen per entity type by REGISTRY_CONFIG:

  categorical  exact match -> alias lookup -> fuzzy match -> EntityNotFound.
               Values come either from the database (district, mandal, village,
               crop) or from a static enum (season, scheme, statuses).
  roster       farmer_name. Resolves to a PERSON, not a name. Fuzzy, but a
               value that matches several people — whether several different
               names or one name several Aadhaars hold — is a
               ClarificationNeeded listing the candidates, never a silent pick.
  identifier   aadhaar. Exactly 12 digits, exact-match only, never fuzzy.
  numeric      the catalog's pass-through numbers (top_n, thresholds, ...).
               Parsed and range-checked, no fuzzy matching.

Everything returns an ExtractedEntity, so the router flow is unchanged. Numeric
values are returned as strings because that is what ExtractedEntity carries;
DuckDB casts them at bind time, including in LIMIT and HAVING.

PRIVACY: a full Aadhaar number must never appear in an answer. `mask_aadhaar`
is the single place that rule is implemented; the router applies it when it
formats query_description, and roster candidates carry an Aadhaar only so a
tap can resolve to an individual — it is masked before it is rendered.
"""
import re
from dataclasses import dataclass

from rapidfuzz import process, fuzz
from .models import (
    ClarificationNeeded,
    EntityCandidate,
    EntityNotFound,
    ExtractedEntity,
)
from .config import DEFAULT_FUZZY_THRESHOLD

import logging
_log = logging.getLogger(__name__)


def _collapse_ws(text: str) -> str:
    """Casefold and squeeze runs of whitespace — the comparison form for names."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


# ── Land units ────────────────────────────────────────────────────────────────
# Users say acres, and in AP small plots are quoted in CENTS (1 acre = 100
# cents), but every threshold_hectares slot is in hectares. The conversion used
# to happen inside the extractor prompt, i.e. an LLM doing arithmetic — and this
# model is not reproducible even at temperature 0. Doing it here makes the same
# question give the same number every time.
LAND_UNIT_FACTORS: dict[str, float] = {
    "ha": 1.0, "hectare": 1.0, "hectares": 1.0,
    "ac": 0.404686, "acre": 0.404686, "acres": 0.404686,
    "cent": 0.00404686, "cents": 0.00404686,
}

# "2 acres", "0.5 ha", "50 cents", "2acres" — number then optional unit word.
_LAND_VALUE_RE = re.compile(
    r"^\s*(?P<num>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)?\s*$", re.IGNORECASE
)


def parse_land_value(raw: str) -> tuple[float, str | None]:
    """'2 acres' -> (0.8094, 'acres'); '1.5' -> (1.5, None). Hectares out.

    Returns the value already converted to hectares and the unit word that was
    recognised (None when the input was a bare number, which means hectares).
    Raises ValueError for anything that is not a number with an optional KNOWN
    unit — an unrecognised unit must fail loudly rather than be read as hectares.
    """
    m = _LAND_VALUE_RE.match(str(raw).replace(",", ""))
    if not m:
        raise ValueError(f"not a land value: {raw!r}")
    number = float(m.group("num"))
    unit = m.group("unit")
    if unit is None:
        return number, None
    key = unit.lower()
    if key not in LAND_UNIT_FACTORS:
        raise ValueError(f"unknown land unit: {unit!r}")
    return round(number * LAND_UNIT_FACTORS[key], 4), key


# ── Alias tables ──────────────────────────────────────────────────────────────

# Colloquial / pre-reorganisation district names -> the roster spelling.
# Only names that genuinely differ from the roster value belong here; the fuzzy
# matcher handles ordinary misspellings.
_DISTRICT_ALIASES = {
    "vizag":            "Visakhapatnam",
    "vishakapatnam":    "Visakhapatnam",
    "kadapa":           "YSR Kadapa",
    "cuddapah":         "YSR Kadapa",
    "ysr":              "YSR Kadapa",
    "ananthapur":       "Anantapur",
    "anantapuram":      "Anantapur",
    "w godavari":       "West Godavari",
    "e godavari":       "East Godavari",
}

# Colloquial names for the seven delivery channels — the six AP state schemes
# plus PM-KISAN, which is a scheme in its own right (the one nearly every farmer
# is enrolled in, which is exactly why it also serves as the spine). The
# canonical values are the labels the catalog SQL emits, so they must not drift.
# Bare "kisan" is deliberately absent: too loose. The fuzzy matcher (threshold
# 88) already catches near-spellings like "pm kisaan".
_SCHEME_ALIASES = {
    "pm kisan":          "PM-KISAN",
    "pm-kisan":          "PM-KISAN",
    "pmkisan":           "PM-KISAN",
    "pm kisan roster":   "PM-KISAN",
    "pm kisan scheme":   "PM-KISAN",
    "agriculture":       "Agriculture",
    "seed subsidy":      "Agriculture",
    "input subsidy":     "Agriculture",
    "seed":              "Agriculture",
    "horticulture":      "Horticulture",
    "apmip":             "Horticulture",
    "micro irrigation":  "Horticulture",
    "micro-irrigation":  "Horticulture",
    "drip":              "Horticulture",
    "fisheries":         "Fisheries",
    "fishery":           "Fisheries",
    "sericulture":       "Sericulture",
    "silk":              "Sericulture",
    "markfed":           "MARKFED",
    "procurement":       "MARKFED",
    "msp":               "MARKFED",
    "ryss":              "RySS",
    "rythu sadhikara":   "RySS",
    "natural farming":   "RySS",
    "apcnf":             "RySS",
}

_SEASON_ALIASES = {
    "kharif season": "Kharif",
    "rabi season":   "Rabi",
    "summer season": "Summer",
    "monsoon":       "Kharif",
    "k":             "Kharif",
    "r":             "Rabi",
}

_SOCIAL_CATEGORY_ALIASES = {
    "scheduled caste":  "SC",
    "scheduled tribe":  "ST",
    "backward class":   "BC",
    "backward caste":   "BC",
    "other caste":      "OC",
    "open category":    "OC",
    "general":          "OC",
}

# ── Registry config ───────────────────────────────────────────────────────────
# 'kind' selects the validation strategy. Types with "values" are static enums;
# the rest are loaded from the database in _load(). "mirrors" declares a paired
# slot that shares its base type's values and aliases (scheme/scheme_2).

REGISTRY_CONFIG: dict[str, dict] = {
    # ── Geography and people (loaded from pm_kisan) ──────────────────────────
    "district":    {"kind": "categorical", "fuzzy_threshold": 85,
                    "aliases": _DISTRICT_ALIASES},
    "mandal":      {"kind": "categorical", "fuzzy_threshold": 85, "aliases": {}},
    "village":     {"kind": "categorical", "fuzzy_threshold": 85, "aliases": {}},
    "farmer_name": {"kind": "roster",      "fuzzy_threshold": 82, "aliases": {}},
    # Same input, deliberately NOT disambiguated: F14 asks how many farmers
    # share a name, so resolving to one person would answer a different question.
    "name_search": {"kind": "passthrough"},

    # ── Crops (agriculture.cropname ∪ markfed.CROP_NAME) ─────────────────────
    "crop":        {"kind": "categorical", "fuzzy_threshold": 85, "aliases": {}},

    # ── Static enums ─────────────────────────────────────────────────────────
    "season": {
        "kind": "categorical",
        "values": ["Kharif", "Rabi", "Summer"],
        "fuzzy_threshold": 88,
        "aliases": _SEASON_ALIASES,
    },
    "gender": {
        "kind": "categorical",
        "values": ["Male", "Female", "Other"],
        "fuzzy_threshold": 90,
        "aliases": {"m": "Male", "men": "Male", "male": "Male",
                    "f": "Female", "women": "Female", "woman": "Female",
                    "lady": "Female", "ladies": "Female", "female": "Female"},
    },
    "ekyc_status": {
        # 'Approved' is accepted DELIBERATELY and matches zero rows in
        # pm_kisan.ekyc_status (whose only values are Completed/Pending) — it is the
        # value markfed.EKYC_STATUS uses, and no template binds that column yet.
        # Keeping it here lets "whose eKYC is approved?" bind truthfully and return
        # "no records found" instead of silently mis-binding to Completed. Do NOT
        # tidy it away: that is exactly how crop_status lost 'Damaged'.
        "kind": "categorical",
        "values": ["Completed", "Pending", "Approved"],
        "fuzzy_threshold": 88,
        "aliases": {"done": "Completed", "complete": "Completed",
                    "verified": "Completed", "not done": "Pending",
                    "incomplete": "Pending", "outstanding": "Pending"},
    },
    "beneficiary_status": {
        # 'Pending' is in the demo data even though the catalog's ENTITY_TYPES
        # lists only Included/Excluded — all three are accepted.
        "kind": "categorical",
        "values": ["Included", "Excluded", "Pending"],
        "fuzzy_threshold": 88,
        "aliases": {"active": "Included", "eligible": "Included",
                    "dropped": "Excluded", "removed": "Excluded",
                    "ineligible": "Excluded", "waiting": "Pending"},
    },
    "crop_status": {
        # Four values on the current drop. 'Damaged' is rare (3 rows) but real —
        # an earlier comment here asserted it did not exist and the validator
        # rejected the question outright. Re-derive from the data, do not assume:
        # the sweep in AP_ASK_TEMPLATE_FIDELITY_REPORT.md is the procedure.
        "kind": "categorical",
        "values": ["Approved", "Pending", "Under Review", "Damaged"],
        "fuzzy_threshold": 88,
        "aliases": {"approve": "Approved", "accepted": "Approved",
                    "review": "Under Review", "under-review": "Under Review",
                    "in review": "Under Review", "waiting": "Pending",
                    "damage": "Damaged", "damages": "Damaged",
                    "crop damage": "Damaged", "destroyed": "Damaged"},
    },
    "approval_status": {
        "kind": "categorical",
        "values": ["Approved", "Pending", "Under Review"],
        "fuzzy_threshold": 88,
        "aliases": {"approve": "Approved", "cleared": "Approved",
                    "review": "Under Review", "in review": "Under Review",
                    "waiting": "Pending", "stuck": "Pending"},
    },
    "social_category": {
        "kind": "categorical",
        "values": ["SC", "ST", "BC", "OC"],
        "fuzzy_threshold": 100,   # two-letter codes: fuzzy would confuse SC/ST
        "aliases": _SOCIAL_CATEGORY_ALIASES,
    },
    "scheme": {
        "kind": "categorical",
        "values": ["PM-KISAN", "Agriculture", "Horticulture", "Fisheries",
                   "Sericulture", "MARKFED", "RySS"],
        "fuzzy_threshold": 88,
        "aliases": _SCHEME_ALIASES,
    },

    # ── Paired slots: same values and aliases as their base type ─────────────
    "scheme_2":          {"mirrors": "scheme"},
    "social_category_2": {"mirrors": "social_category"},

    # ── Identifier ───────────────────────────────────────────────────────────
    "aadhaar": {"kind": "identifier"},

    # ── Numeric pass-through ─────────────────────────────────────────────────
    "top_n":                  {"kind": "numeric", "cast": int,   "min": 1,    "max": 100},
    # 7, not 6: PM-KISAN counts as a scheme, so a farmer in every AP programme
    # who is also on the roster has seven.
    "scheme_count":           {"kind": "numeric", "cast": int,   "min": 1,    "max": 7},
    # The date-shifted drop runs 2023-2026; the ceiling was 2025 and rejected
    # every question about the current crop year.
    "crop_year":              {"kind": "numeric", "cast": int,   "min": 2022, "max": 2026},
    # land_units: accepts "2 acres" / "50 cents" / "1.5 ha" and converts to
    # hectares here, deterministically, rather than in the extractor prompt.
    "threshold_hectares":     {"kind": "numeric", "cast": float, "exclusive_min": 0,
                               "land_units": True},
    "threshold_qty_per_acre": {"kind": "numeric", "cast": float, "exclusive_min": 0},
    "tolerance_pct":          {"kind": "numeric", "cast": float, "min": 0,    "max": 100},
    # Not a user input: a constant the catalog exposes so the 12-digit rule is
    # visible in the SQL. The extractor is never asked for it; the router
    # defaults it. Whatever arrives here resolves to 12.
    "aadhaar_length":         {"kind": "constant", "value": "12"},
}

# Scope markers, not real entities — "how is the state doing" must not fuzzy-match
# some village called "Statepalli".
_STATE_LEVEL_TERMS = {"ap", "andhra pradesh", "state", "all", "entire state", "statewide"}
_GEO_TYPES = {"district", "mandal", "village"}

AADHAAR_LENGTH = 12

# Every person sharing a name has to be OFFERABLE: truncating to the usual
# three or four options leaves the rest unreachable, and per-farmer lookup for
# them silently impossible. The worst name on this drop is held by seven people
# ("Anil Devi", "Prasad Babu", "Satish Sharma"), so this is a backstop against
# a future drop, not a limit that fires. Raise it rather than trim the list.
MAX_PERSON_CANDIDATES = 8


def mask_aadhaar(value: str) -> str:
    """'726018159083' -> 'XXXX-XXXX-9083'. Never show a full Aadhaar in an answer."""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) != AADHAAR_LENGTH:
        return str(value)
    return f"XXXX-XXXX-{digits[-4:]}"


# ── People, not names ─────────────────────────────────────────────────────────
# 316 of the 446 distinct names in pm_kisan are held by more than one Aadhaar —
# 71%, the worst reaching seven people — so a list of distinct name STRINGS
# cannot tell "one name" from "one person". Every per-farmer template used to
# filter on the name, and F12 reported four different Lakshmi Devis' MARKFED
# payments (₹259,181.42) as one farmer's total. The roster now carries identity.


@dataclass(frozen=True)
class FarmerPerson:
    """One roster row: a person, with what tells them apart from their
    namesakes. District alone is not enough — two of the four Lakshmi Devis are
    both in Nellore — so the reference form is name + village."""
    aadhaar:  str
    name:     str
    district: str
    mandal:   str
    village:  str


def person_ref(person: FarmerPerson) -> str:
    """'Lakshmi Devi of Rambilli' — the sayable, routable form of one person.

    Name + village is unique across the whole roster on this drop; where it
    would not be, the caller appends a masked Aadhaar (see zones.candidate_
    replies) and `_place_matches` accepts that too.
    """
    return f"{person.name} of {person.village}" if person.village else person.name


def describe_person(person: FarmerPerson) -> str:
    """How one person reads in a disambiguation prompt."""
    if person.village and person.district:
        return f"{person.name} of {person.village} ({person.district})"
    return f"{person.name} ({person.district})" if person.district else person.name


# "Lakshmi Devi of Rambilli" / "…of Rambilli, Visakhapatnam district".
_PERSON_REF_RE = re.compile(r"^(?P<name>.+?)\s+of\s+(?P<place>.+)$", re.IGNORECASE)
_MASKED_AADHAAR_RE = re.compile(r"X{4}-X{4}-\d{4}", re.IGNORECASE)
# Words that name the KIND of place rather than the place: "Rambilli village".
_PLACE_NOUNS = {"village", "mandal", "district", "sub-district", "subdistrict"}


def _place_tokens(place: str) -> list[str]:
    """'Rambilli, Visakhapatnam district' -> ['rambilli', 'visakhapatnam'].

    A masked Aadhaar is pulled out first: it is one token containing no spaces
    but also no comma, so the ordinary split would glue it to the village.
    """
    text = str(place)
    tokens = [m.group(0).lower() for m in _MASKED_AADHAAR_RE.finditer(text)]
    for part in re.split(r"[,/]", _MASKED_AADHAAR_RE.sub(" ", text)):
        words = _collapse_ws(part).split()
        while words and words[-1] in _PLACE_NOUNS:
            words.pop()
        if words:
            tokens.append(" ".join(words))
    return tokens


def _place_matches(person: FarmerPerson, place: str) -> bool:
    """Does this person sit in EVERY place the reference named?

    Equality, not containment: 'Sangam' must not also select a village called
    'Sangampalli', because the whole point of the reference is that it picks
    exactly one of several same-name people.
    """
    fields = {
        _collapse_ws(person.village),
        _collapse_ws(person.mandal),
        _collapse_ws(person.district),
        mask_aadhaar(person.aadhaar).lower(),
    }
    fields.discard("")
    tokens = _place_tokens(place)
    return bool(tokens) and all(token in fields for token in tokens)


def _resolve_config(entity_type: str) -> tuple[str, dict]:
    """(base type, config) — following a 'mirrors' pointer if there is one."""
    cfg = REGISTRY_CONFIG.get(entity_type, {})
    base = cfg.get("mirrors")
    if base:
        return base, REGISTRY_CONFIG.get(base, {})
    return entity_type, cfg


def _format_number(value) -> str:
    """2.0 -> '2', 2.5 -> '2.5' — reads better in query_description."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class EntityValidator:
    def __init__(self, cache_conn):
        self._registry: dict[str, list[str]] = {}
        # farmer_name -> the districts that name appears in, for disambiguation
        self._farmer_districts: dict[str, list[str]] = {}
        # Same values as _registry, ordered most-common-first. Chips only.
        self._registry_ranked: dict[str, list[str]] = {}
        # The identity half of the roster: collapsed name -> the PEOPLE who
        # hold it, plus the two indexes that resolve a reference back to one.
        self._farmer_people: dict[str, list[FarmerPerson]] = {}
        self._person_by_aadhaar: dict[str, FarmerPerson] = {}
        self._roster_by_norm: dict[str, str] = {}
        self._load(cache_conn)

    # ── Registry loading ──────────────────────────────────────────────────────

    def _query(self, cache_conn, sql: str) -> list[tuple]:
        try:
            return cache_conn.execute(sql).fetchall()
        except Exception as exc:
            _log.warning("entity registry query failed (%s): %s", sql.strip()[:60], exc)
            return []

    def _load(self, cache_conn) -> None:
        """DB-backed registries first, then the static enums.

        Every DB registry reads pm_kisan (crop also reads markfed). That is
        deliberate: pm_kisan is the farmer roster, so it defines the vocabulary
        the user is allowed to ask in. It also means a scheme table that spells
        a district differently will silently return no rows — see the data
        contract in AP_BACKEND_INTEGRATION_HANDOFF.md.
        """
        _RANKED_SOURCES = {
            "district": 'SELECT "district" FROM pm_kisan WHERE "district" IS NOT NULL '
                        'GROUP BY "district" ORDER BY COUNT(*) DESC',
            "crop": (
                'SELECT v, COUNT(*) AS n FROM ('
                '  SELECT "cropname" AS v FROM agriculture WHERE "cropname" IS NOT NULL'
                '  UNION ALL '
                '  SELECT "CROP_NAME" FROM markfed WHERE "CROP_NAME" IS NOT NULL'
                ') GROUP BY v ORDER BY n DESC'
            ),
        }
        db_sources = {
            "district":    'SELECT DISTINCT "district"     FROM pm_kisan',
            "mandal":      'SELECT DISTINCT "sub_district" FROM pm_kisan',
            "village":     'SELECT DISTINCT "village"      FROM pm_kisan',
            "farmer_name": 'SELECT DISTINCT "name"         FROM pm_kisan',
            "crop": (
                'SELECT DISTINCT "cropname" FROM agriculture WHERE "cropname" IS NOT NULL '
                'UNION '
                'SELECT DISTINCT "CROP_NAME" FROM markfed WHERE "CROP_NAME" IS NOT NULL'
            ),
        }
        for etype, sql in db_sources.items():
            rows = self._query(cache_conn, sql)
            self._registry[etype] = sorted({str(r[0]).strip() for r in rows if r[0] is not None})

        # Same vocabulary, ordered by how much of the data each value actually
        # covers. Offering "Bengalgram, Blackgram, Chilli" as example crops
        # because they sort first is a worse prompt than offering the crops the
        # state mostly grows. Matching never uses this order — only chips do.
        for etype, sql in _RANKED_SOURCES.items():
            rows = self._query(cache_conn, sql)
            ranked = [str(r[0]).strip() for r in rows if r[0] is not None]
            if ranked:
                self._registry_ranked[etype] = ranked

        # The roster as PEOPLE. One query feeds both the district shortlist the
        # multi-NAME prompt uses and the per-name person index that stops one
        # shared name resolving to a silent merge of everyone who holds it.
        for name, aadhaar, district, mandal, village in self._query(
            cache_conn,
            'SELECT "name", "aadhaar_no", "district", "sub_district", "village" '
            'FROM pm_kisan WHERE "name" IS NOT NULL'
        ):
            name = str(name).strip()
            districts = self._farmer_districts.setdefault(name.lower(), [])
            if district and str(district) not in districts:
                districts.append(str(district))

            digits = "".join(ch for ch in str(aadhaar or "") if ch.isdigit())
            if len(digits) != AADHAAR_LENGTH or digits in self._person_by_aadhaar:
                # No usable identity (or a duplicate roster row). The name still
                # validates; it simply cannot be bound to a person, which the
                # name-keyed templates never needed.
                continue
            person = FarmerPerson(
                aadhaar=digits, name=name,
                district=str(district or ""), mandal=str(mandal or ""),
                village=str(village or ""),
            )
            self._person_by_aadhaar[digits] = person
            self._farmer_people.setdefault(_collapse_ws(name), []).append(person)

        self._roster_by_norm = {
            _collapse_ws(v): v for v in self._registry.get("farmer_name", [])
        }

        for etype, cfg in REGISTRY_CONFIG.items():
            if "values" in cfg:
                self._registry[etype] = cfg["values"]

        _log.info(
            "entity registries: %s",
            ", ".join(f"{k}={len(v)}" for k, v in sorted(self._registry.items()) if v),
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, raw_value, entity_type: str) -> ExtractedEntity:
        if raw_value is None:
            raise EntityNotFound(entity_type, "<null>", [])

        base_type, cfg = _resolve_config(entity_type)
        kind = cfg.get("kind", "categorical")

        if kind == "constant":
            return self._entity(entity_type, raw_value, cfg["value"], "constant")
        if kind == "numeric":
            return self._validate_numeric(raw_value, entity_type, cfg)
        if kind == "identifier":
            return self._validate_aadhaar(raw_value, entity_type)

        raw_text = str(raw_value)
        if base_type in _GEO_TYPES and raw_text.strip().lower() in _STATE_LEVEL_TERMS:
            # Not an error the user should see as "unknown district" — the router
            # turns an empty geography into the state-wide template instead.
            raise EntityNotFound(entity_type, raw_text, [])

        if kind == "roster":
            return self._validate_roster(raw_text, entity_type, base_type, cfg)
        if kind == "passthrough":
            # Trim and collapse whitespace, resolve nothing. For questions where
            # AMBIGUITY IS THE ANSWER — "which farmers share this name?" — the
            # roster kind's ClarificationNeeded would defeat the question by
            # asking the user to pick one of the very people being counted.
            return self._entity(entity_type, raw_text,
                                re.sub(r"\s+", " ", raw_text).strip(), "exact")
        return self._validate_categorical(raw_text, entity_type, base_type, cfg)

    # ── Kinds ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _entity(entity_type, raw_value, resolved, confidence) -> ExtractedEntity:
        return ExtractedEntity(
            slot_name=entity_type,
            raw_value=str(raw_value),
            resolved_value=str(resolved),
            entity_type=entity_type,
            confidence=confidence,
        )

    def _validate_numeric(self, raw_value, entity_type: str, cfg: dict) -> ExtractedEntity:
        cast = cfg["cast"]
        text = str(raw_value).strip().replace(",", "").rstrip("%")

        if cfg.get("land_units"):
            # "2 acres" -> 0.8094 ha. A bare number is still accepted and read as
            # hectares, so an extractor that already converted — or an older
            # prompt — keeps working unchanged.
            try:
                number, unit = parse_land_value(text)
            except ValueError:
                raise EntityNotFound(entity_type, str(raw_value), [])
            self._check_numeric_range(number, entity_type, raw_value, cfg)
            # "converted" only when the unit actually moved the number — a
            # question already asked in hectares should not be echoed back as
            # the redundant "1.5 hectares (1.5 ha)".
            converted = unit is not None and LAND_UNIT_FACTORS[unit] != 1.0
            return self._entity(entity_type, raw_value, _format_number(number),
                                "converted" if converted else "numeric")

        try:
            # int("10.0") raises, and the extractor does hand back "10.0"
            number = cast(float(text)) if cast is int else cast(text)
        except (TypeError, ValueError):
            raise EntityNotFound(entity_type, str(raw_value), [])

        if cast is int and float(text) != number:
            raise EntityNotFound(entity_type, str(raw_value), [])
        self._check_numeric_range(number, entity_type, raw_value, cfg)

        return self._entity(entity_type, raw_value, _format_number(number), "numeric")

    @staticmethod
    def _check_numeric_range(number, entity_type: str, raw_value, cfg: dict) -> None:
        if "min" in cfg and number < cfg["min"]:
            raise EntityNotFound(entity_type, str(raw_value), [])
        if "max" in cfg and number > cfg["max"]:
            raise EntityNotFound(entity_type, str(raw_value), [])
        if "exclusive_min" in cfg and number <= cfg["exclusive_min"]:
            raise EntityNotFound(entity_type, str(raw_value), [])

    def _validate_aadhaar(self, raw_value, entity_type: str) -> ExtractedEntity:
        """Exactly 12 digits. Exact match only — a fuzzy Aadhaar is a wrong person."""
        digits = "".join(ch for ch in str(raw_value) if ch.isdigit())
        if len(digits) != AADHAAR_LENGTH:
            raise EntityNotFound(entity_type, mask_aadhaar(str(raw_value)), [])
        return self._entity(entity_type, digits, digits, "exact")

    def _validate_roster(
        self, raw_text: str, entity_type: str, base_type: str, cfg: dict
    ) -> ExtractedEntity:
        roster = self._registry.get(base_type, [])
        norm = _collapse_ws(raw_text)

        # An Aadhaar where a name was expected. Not something a user types into
        # this slot — it is the unambiguous internal form, so any caller holding
        # an identity can name a PERSON. Never rendered back: chips carry
        # `mask_aadhaar` output only.
        digits = "".join(ch for ch in str(raw_text) if ch.isdigit())
        if len(digits) == AADHAAR_LENGTH and digits in self._person_by_aadhaar:
            person = self._person_by_aadhaar[digits]
            # Same round-trip rule as _bind_person: a shared name resolves to
            # the reference, so re-validating the answer finds the same person.
            namesakes = self._farmer_people.get(_collapse_ws(person.name), [])
            return self._person_entity(
                entity_type, raw_text, person,
                person_ref(person) if len(namesakes) > 1 else person.name,
            )

        # EXACT MATCH FIRST, and no FUZZY expansion runs when there is one. A
        # roster name that the user typed verbatim must never reach the fuzzy
        # expansion below, or a real name gets buried in a "Several farmers
        # match…" prompt alongside people who merely resemble it — 'Padma Sri'
        # is on the roster, yet also fuzzy-matches every other Padma. Whitespace
        # and case are normalised on both sides so "padma  sri" still counts as
        # verbatim.
        #
        # It short-circuits to a NAME, though, not to a person: because the
        # roster is deduplicated, "Lakshmi Devi" appeared exactly once here and
        # four people collapsed into one bound value. _bind_person is where that
        # is now decided.
        exact = [v for v in roster if _collapse_ws(v) == norm]
        if len(exact) == 1:
            return self._bind_person(entity_type, raw_text, exact[0], None, "exact")

        # "<roster name> of <village>" — the reference a disambiguation chip
        # sends back, and what a user who knows the village would say anyway.
        # Tried only when the head is a VERBATIM roster name, so an ordinary
        # name is never split on a stray "of", and only AFTER the exact test
        # above, so a roster name that itself contained " of " would have won.
        split = self._split_person_ref(raw_text)
        if split is not None:
            name, place = split
            return self._bind_person(entity_type, raw_text, name, place, "exact")

        threshold = cfg.get("fuzzy_threshold", DEFAULT_FUZZY_THRESHOLD)
        matches = process.extract(
            norm, [_collapse_ws(v) for v in roster],
            scorer=fuzz.WRatio, score_cutoff=threshold, limit=5,
        )
        names: list[str] = []
        for _, _, idx in matches:
            if roster[idx] not in names:
                names.append(roster[idx])

        if not names:
            top = process.extract(norm, [v.lower() for v in roster],
                                  scorer=fuzz.WRatio, limit=3)
            raise EntityNotFound(entity_type, raw_text, [roster[t[2]] for t in top])

        if len(names) == 1:
            confidence = "exact" if names[0].lower() == norm else "fuzzy"
            return self._bind_person(entity_type, raw_text, names[0], None, confidence)

        # Several DIFFERENT NAMES answer to this — asking is the only safe move.
        # (One name held by several people is the other ambiguity and is raised
        # by _bind_person; a tap here lands on a name and cascades into it.) The
        # candidates travel with the exception as data as well as prose: the
        # prompt disambiguates people BY DISTRICT, so the router has to be able
        # to resolve a reply that names one.
        shortlist = names[:4]
        raise ClarificationNeeded(
            f"Several farmers match '{raw_text}': "
            + "; ".join(self._describe_farmer(n) for n in shortlist)
            + ". Which one do you mean?",
            entity_type=entity_type,
            raw_value=raw_text,
            candidates=[
                EntityCandidate(
                    name=name,
                    districts=list(self._farmer_districts.get(name.lower(), [])),
                )
                for name in shortlist
            ],
        )

    def _describe_farmer(self, name: str) -> str:
        districts = self._farmer_districts.get(name.lower(), [])
        return f"{name} ({', '.join(districts)})" if districts else name

    # ── One name → one person ─────────────────────────────────────────────────

    def _split_person_ref(self, raw_text: str) -> tuple[str, str] | None:
        """('Lakshmi Devi', 'Rambilli') for a reference, None for a plain name."""
        match = _PERSON_REF_RE.match(str(raw_text).strip())
        if not match:
            return None
        name = self._roster_by_norm.get(_collapse_ws(match.group("name")))
        if name is None:
            return None
        return name, match.group("place")

    def _person_entity(
        self, entity_type: str, raw_value, person: FarmerPerson,
        resolved: str, confidence: str = "exact",
    ) -> ExtractedEntity:
        entity = self._entity(entity_type, raw_value, resolved, confidence)
        entity.person_aadhaar = person.aadhaar
        return entity

    def _bind_person(
        self, entity_type: str, raw_text: str, name: str,
        place: str | None, confidence: str,
    ) -> ExtractedEntity:
        """One roster NAME has been resolved. Now resolve it to one PERSON.

        This is the whole defect: a name several Aadhaars hold must reach a
        clarify and never a silent pick, because the templates then aggregate
        across datasets and add several people's money together.
        """
        people = self._farmer_people.get(_collapse_ws(name), [])
        if not people:
            # A name the registry knows but the person index does not — a roster
            # row without a usable Aadhaar, or a stubbed registry in a test.
            # Bind the name, exactly as before: nothing here can improve on it.
            return self._entity(entity_type, raw_text, name, confidence)

        shortlist = people
        if place:
            narrowed = [p for p in people if _place_matches(p, place)]
            if narrowed:
                shortlist = narrowed

        if len(shortlist) == 1:
            person = shortlist[0]
            # The reference has to survive a round trip. When the name is shared,
            # resolved_value carries the village, so a chained clarify (Q125 asks
            # for the village next, and re-validates everything already filled)
            # lands on the SAME person instead of asking again — an unbreakable
            # loop otherwise. A name only one person holds reads exactly as the
            # user wrote it, so nothing else changes.
            resolved = person_ref(person) if len(people) > 1 else person.name
            return self._person_entity(
                entity_type, raw_text, person, resolved, confidence
            )

        raise ClarificationNeeded(
            f"{len(shortlist)} different farmers are called '{name}': "
            + "; ".join(describe_person(p) for p in shortlist[:MAX_PERSON_CANDIDATES])
            + ". Which one do you mean?",
            entity_type=entity_type,
            raw_value=raw_text,
            candidates=[
                EntityCandidate(
                    name=p.name,
                    districts=[p.district] if p.district else [],
                    village=p.village or None,
                    aadhaar=p.aadhaar,
                )
                for p in shortlist[:MAX_PERSON_CANDIDATES]
            ],
        )

    # ── Registry access ───────────────────────────────────────────────────────

    def registry_values(
        self, entity_type: str, *, by_frequency: bool = False
    ) -> list[str]:
        """The known values for an entity type — used to offer example chips
        when a question can only be answered one value at a time.

        `by_frequency` asks for most-common-first, which is what makes a short
        example list representative rather than merely alphabetical. Falls back
        to the sorted vocabulary where no ranking was loaded.
        """
        base_type, _ = _resolve_config(entity_type)
        if by_frequency and base_type in self._registry_ranked:
            return list(self._registry_ranked[base_type])
        return list(self._registry.get(base_type, []))

    def _validate_categorical(
        self, raw_text: str, entity_type: str, base_type: str, cfg: dict
    ) -> ExtractedEntity:
        aliases      = {k.lower(): v for k, v in cfg.get("aliases", {}).items()}
        threshold    = cfg.get("fuzzy_threshold", DEFAULT_FUZZY_THRESHOLD)
        valid_values = self._registry.get(base_type, [])
        norm         = raw_text.strip().lower()

        for v in valid_values:
            if v.lower() == norm:
                return self._entity(entity_type, raw_text, v, "exact")

        if norm in aliases:
            return self._entity(entity_type, raw_text, aliases[norm], "alias")

        if valid_values and threshold < 100:
            match = process.extractOne(
                norm, [v.lower() for v in valid_values],
                scorer=fuzz.WRatio, score_cutoff=threshold,
            )
            if match:
                _, _, idx = match
                return self._entity(entity_type, raw_text, valid_values[idx], "fuzzy")

        suggestions: list[str] = []
        if valid_values:
            top = process.extract(norm, [v.lower() for v in valid_values],
                                  scorer=fuzz.WRatio, limit=3)
            suggestions = [valid_values[t[2]] for t in top]
        raise EntityNotFound(entity_type, raw_text, suggestions)

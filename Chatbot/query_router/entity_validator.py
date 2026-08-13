"""
Validates extracted entities against the Odisha PR&DW registries.

The vocabulary is the workbook's **Parameter Registry** sheet: 19 bind names,
each with a source column and an allowed-values query. `PARAM_ENTITY_TYPES`
maps every one of those bind names to the entity type here, so a catalogue entry
never has to guess what `$asset_sub_category` validates as.

Five validation kinds, chosen per entity type by REGISTRY_CONFIG:

  categorical  exact match -> alias lookup -> fuzzy match -> EntityNotFound.
               Every value is loaded from the database at startup (read-only),
               which is what makes the statewide roll-out a data swap rather
               than a redesign (decision D4).
  roster       gp. Resolves to a GRAM PANCHAYAT, not a name — the validated
               entity carries `resolved_code`, the `gp_lgd_code`. A name several
               GPs answer to is a ClarificationNeeded listing the candidates
               with their block and district, never a silent pick.
  fiscal_year  the six exact `'2020-2021'`…`'2025-2026'` strings, reached
               through `date_phrase` so that "FY 24-25", "24-25" and "last year"
               all land on the stored full form. `'2024-25'` never reaches SQL.
  numeric      the catalogue's pass-through numbers (top_n, thresholds). Parsed,
               Indian-notation amounts normalised, and range-checked.
  date         `deadline`. ISO out; anything genuinely ambiguous is refused
               rather than guessed at.

Everything returns an ExtractedEntity, so the router flow is unchanged. Numeric
values are returned as strings because that is what ExtractedEntity carries;
DuckDB casts them at bind time, including in LIMIT and HAVING.

**Exact DB strings bind; matching is whitespace-collapsed.** Source values carry
stray whitespace — `dim_lsdg_theme.lsdg_theme` has a trailing space on
'Theme 5 - Clean and Green Village ', and the `activity_status` decode of code
178 has a LEADING TAB. Logged at load, never repaired: the column holds those
bytes, so a tidied value would filter to zero rows — a silent wrong answer, which
is exactly what "validation logs, never fixes" is about. The registry therefore
stores the database's own strings and normalises only the COMPARISON, so a user
typing the label cleanly still resolves.

**Every value is loaded from the column the catalogue FILTERS ON**, which since
WP-3 means the `v_*` views rather than the base tables behind them. That
distinction is doing real work: `v_activity.status_label` TRIMs and de-tabs the
`dim_code` decode, so the value the registry binds is 'WORK COMPLETED' even
though `dim_code` still stores '\\tWORK COMPLETED'. Loading the raw decode and
binding it against the view is a zero-row answer with no error anywhere. The
theme trailing space, by contrast, survives into the view and so survives here.
The views are created at adapter startup — see `db_factory._seed_views` and
`open_analytical_db`, which anything constructing an adapter directly must use.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

from rapidfuzz import process, fuzz
from .models import (
    ClarificationNeeded,
    EntityCandidate,
    EntityNotFound,
    ExtractedEntity,
)
from .config import DEFAULT_FUZZY_THRESHOLD
from .date_phrase import resolve_fiscal_years

import logging
_log = logging.getLogger(__name__)


def _collapse_ws(text: str) -> str:
    """Casefold and squeeze runs of whitespace — the comparison form for names.

    Load-bearing beyond its size: `\\s+` covers the tab inside
    '\\tWORK COMPLETED' and the trailing space on 'Theme 5 - …Village ', so a
    user who types either label cleanly still matches the value the database
    actually stores.
    """
    return re.sub(r"\s+", " ", text or "").strip().lower()


# ── Indian-notation amounts ───────────────────────────────────────────────────
# Officers quote money in lakhs and crores, and every rupee slot in the
# catalogue is a plain number. Doing the arithmetic here rather than in the
# extractor prompt is the same lesson AP paid for with land units: an LLM doing
# multiplication is not reproducible even at temperature 0, so "activities above
# 1 lakh" could answer about ₹1 one time and ₹100,000 the next.
AMOUNT_UNIT_FACTORS: dict[str, float] = {
    "rupee": 1.0, "rupees": 1.0, "rs": 1.0, "inr": 1.0,
    "hundred": 1e2,
    "thousand": 1e3, "thousands": 1e3, "k": 1e3,
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
}

# "1 lakh", "2.5 crore", "₹50,000", "Rs. 1,00,000/-", "50000", "50 lakh rupees".
# The Indian digit grouping (1,00,000) falls out of stripping commas, so no
# separate rule is needed for it.
_AMOUNT_RE = re.compile(
    r"^\s*(?:₹|₨|rs\.?|inr)?\s*"
    r"(?P<num>-?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[a-z]+\.?)?\s*"
    r"(?:rupees|rupee|rs\.?|inr)?\s*(?:/-)?\s*$",
    re.IGNORECASE,
)


def parse_amount(raw: str) -> tuple[float, str | None]:
    """'1 lakh' -> (100000.0, 'lakh'); '₹50,000' -> (50000.0, None).

    Returns the value in rupees and the multiplier word that was recognised
    (None when the input was a plain number, which is already rupees). Raises
    ValueError for anything that is not a number with an optional KNOWN unit —
    an unrecognised unit must fail loudly rather than be read as bare rupees,
    because "2 bighas" silently becoming ₹2 is a wrong answer that looks right.
    """
    text = str(raw).replace(",", "").strip()
    m = _AMOUNT_RE.match(text)
    if not m:
        raise ValueError(f"not an amount: {raw!r}")
    number = float(m.group("num"))
    unit = m.group("unit")
    if unit is None:
        return number, None
    key = unit.lower().rstrip(".")
    if key not in AMOUNT_UNIT_FACTORS:
        raise ValueError(f"unknown amount unit: {unit!r}")
    return round(number * AMOUNT_UNIT_FACTORS[key], 2), key


# ── Alias tables ──────────────────────────────────────────────────────────────
# GROWTH PATH (decision D5): these seed the English colloquials officers already
# use. They are per-entity dicts of *lowercased user text* -> *canonical label*,
# and the canonical label is looked up in the loaded registry before it binds
# (see `_canonical`), so an alias may be written in clean form even where the
# stored value carries stray whitespace.
#
# The structure takes Odia and transliterated keys with no code change — a key
# is just a string. The operator's forthcoming keyword/alias dictionary file and
# the unanswered-question log are the two feeds; neither needs this module
# edited, only these dicts extended (or, once the dictionary file lands, loaded
# into them).

# Colloquial and pre-reorganisation district spellings -> the roster spelling.
# Only names that genuinely DIFFER belong here; the fuzzy matcher handles
# ordinary misspellings. NOTE the column is `zp_name` (Zilla Parishad), which is
# co-terminous with the district but is not literally called one — see the
# Parameter Registry sheet's warning on $district_name.
_DISTRICT_ALIASES = {
    "khurda":       "Khordha",
    "khorda":       "Khordha",
    "khurdha":      "Khordha",
    "cuttak":       "Cuttack",
    "kataka":       "Cuttack",
    "sundergarh":   "Sundargarh",
    "sundergad":    "Sundargarh",
    "sundargad":    "Sundargarh",
    "phulbani":     "Kandhamal",       # pre-1994 name of the district
    "boudh kandhamal": "Kandhamal",
}

# Blocks are Panchayat Samitis. Seeded thin deliberately: the sample carries 16
# of the statewide 314, so a large hand-written table here would be guesswork.
_BLOCK_ALIASES = {
    "kalyansinghpur": "Kalyansingpur",   # the GP spells it with the h, the block does not
    "tangi choudwar": "Tangi Choudwar",
    "tangi-choudwar": "Tangi Choudwar",
}

# Gram Panchayat colloquials. Empty by design — 20 of ~6,800 GPs are loaded, so
# every entry written today would be a guess about names not yet in the data.
# This is the dict the operator's dictionary file feeds first.
_GP_ALIASES: dict[str, str] = {}

# The five non-null scheme_name values. 82% of activity_expenditure rows are
# NULL here, which is a WP-3 caveat, not a registry problem.
_SCHEME_ALIASES = {
    "cfc":                          "XV Finance Commission",
    "central finance commission":   "XV Finance Commission",
    "central fc":                   "XV Finance Commission",
    "15th fc":                      "XV Finance Commission",
    "15th finance commission":      "XV Finance Commission",
    "fifteenth finance commission": "XV Finance Commission",
    "xv fc":                        "XV Finance Commission",
    "14th fc":                      "Fourteen Finance Commission",
    "14th finance commission":      "Fourteen Finance Commission",
    "fourteenth finance commission": "Fourteen Finance Commission",
    "xiv finance commission":       "Fourteen Finance Commission",
    # "SFC" unqualified means the CURRENT State Finance Commission, per the
    # brief. The 4th is still in the data, so an officer who means it must say
    # "4th SFC" — flagged in WP2_REPORT as an operator decision.
    "sfc":                          "5TH STATE FINANCE COMMISSION",
    "state finance commission":     "5TH STATE FINANCE COMMISSION",
    "5th sfc":                      "5TH STATE FINANCE COMMISSION",
    "fifth state finance commission": "5TH STATE FINANCE COMMISSION",
    "4th sfc":                      "4TH STATE FINANCE SCHEME",
    "fourth state finance commission": "4TH STATE FINANCE SCHEME",
    "4th state finance commission": "4TH STATE FINANCE SCHEME",
    "own funds":                    "Own Funds",
    "own fund":                     "Own Funds",
    "own source revenue":           "Own Funds",
    "osr":                          "Own Funds",
}

# Work-status colloquials. The alias TARGETS are written cleanly; `_canonical`
# resolves them onto the stored strings, tab and all.
_STATUS_ALIASES = {
    "ongoing":            "WORK ONGOING",
    "in progress":        "WORK ONGOING",
    "under execution":    "WORK ONGOING",
    "running":            "WORK ONGOING",
    "completed":          "WORK COMPLETED",
    "complete":           "WORK COMPLETED",
    "finished":           "WORK COMPLETED",
    "done":               "WORK COMPLETED",
    "abandoned":          "WORK ABANDONED",
    "stalled":            "WORK ABANDONED",
    "dropped":            "WORK ABANDONED",
    "under approval":     "UNDER APPROVAL",
    "pending approval":   "UNDER APPROVAL",
    "awaiting approval":  "UNDER APPROVAL",
    "not yet approved":   "UNDER APPROVAL",
    "approved":           "Activity Approved",
    "activity approved":  "Activity Approved",
}

# The 30 Eleventh Schedule subjects, by what an officer calls them.
# 'Poverty allevation programme' is spelt that way IN THE DATABASE; the alias is
# how the correct spelling still resolves. Logged at load, not repaired.
_FOCUS_AREA_ALIASES = {
    "toilet":            "Sanitation",
    "toilets":           "Sanitation",
    "swachh bharat":     "Sanitation",
    "sbm":               "Sanitation",
    "odf":               "Sanitation",
    "water":             "Drinking water",
    "drinking water supply": "Drinking water",
    "piped water":       "Drinking water",
    "jal jeevan":        "Drinking water",
    "road":              "Roads",
    "rural roads":       "Roads",
    "school":            "Education",
    "schools":           "Education",
    "anganwadi":         "Women and child development",
    "icds":              "Women and child development",
    "health centre":     "Health",
    "health center":     "Health",
    "phc":               "Health",
    "electricity":       "Rural electrification",
    "power":             "Rural electrification",
    "street light":      "Rural electrification",
    "housing":           "Rural housing",
    "houses":            "Rural housing",
    "awaas":             "Rural housing",
    "pond":              "Water Conservation",
    "ponds":             "Water Conservation",
    "watershed":         "Water Conservation",
    "poverty alleviation programme": "Poverty allevation programme",
    "poverty alleviation": "Poverty allevation programme",
    "livelihood":        "Poverty allevation programme",
    "solar":             "Non-conventional energy sources",
    "gp office":         "GP Office Infrastructure",
    "panchayat office":  "GP Office Infrastructure",
}

# LSDG themes. The stored labels are long ('Theme 5 - Clean and Green Village ',
# trailing space included), so the alias table carries both the bare number and
# the memorable half of each name.
_THEME_ALIASES = {
    "theme 1":            "Theme 1 - Poverty Free and Enhanced Livelihoods Village",
    "poverty free":       "Theme 1 - Poverty Free and Enhanced Livelihoods Village",
    "livelihoods":        "Theme 1 - Poverty Free and Enhanced Livelihoods Village",
    "theme 3":            "Theme 3 - Child Friendly Village",
    "child friendly":     "Theme 3 - Child Friendly Village",
    "theme 4":            "Theme 4 - Water Sufficient Village",
    "water sufficient":   "Theme 4 - Water Sufficient Village",
    "theme 5":            "Theme 5 - Clean and Green Village",
    "clean and green":    "Theme 5 - Clean and Green Village",
    "clean & green":      "Theme 5 - Clean and Green Village",
    "theme 6":            "Theme 6 - Self-sufficient Infrastructure in Village",
    "self sufficient infrastructure": "Theme 6 - Self-sufficient Infrastructure in Village",
    "infrastructure":     "Theme 6 - Self-sufficient Infrastructure in Village",
    "theme 8":            "Theme 8 - Village with Good Governance",
    "good governance":    "Theme 8 - Village with Good Governance",
}

_ASSET_CATEGORY_ALIASES = {
    "toilet":           "Household Sanitation",
    "toilets":          "Household Sanitation",
    "community toilet": "Community Sanitation",
    "swm":              "Solid Waste Management",
    "solid waste":      "Solid Waste Management",
    "liquid waste":     "Liquid Waste Management",
    "lwm":              "Liquid Waste Management",
    "grey water":       "Grey water management",
    "greywater":        "Grey water management",
    "plastic waste":    "Plastic Waste Management",
    "fsm":              "Faecal Sludge Management",
    "tubewell":         "Drinking water supply structure",
    "tube well":        "Drinking water supply structure",
    "borewell":         "Drinking water supply structure",
    "road":             "Roads, Bridges & Culverts",
    "roads":            "Roads, Bridges & Culverts",
    "culvert":          "Roads, Bridges & Culverts",
    "bridge":           "Roads, Bridges & Culverts",
    "building":         "Buildings",
    "buildings":        "Buildings",
    "pond":             "Pond & Reservoir",
    "computer":         "Computers and peripherals",
}


# ── Registry config ───────────────────────────────────────────────────────────
# 'kind' selects the validation strategy. Every categorical type is DB-loaded —
# there are no static enums in PR&DW, which is decision D4's whole point.
# "mirrors" declares a paired slot that shares its base type's values and
# aliases ($scheme/$scheme_2, $gp_name/$gp_name_2, …).

REGISTRY_CONFIG: dict[str, dict] = {
    # ── Geography: the three tiers ───────────────────────────────────────────
    # District is `gram_panchayat.zp_name` — the Zilla Parishad, co-terminous
    # with the district. 9 values in the sample, 30 statewide.
    "district": {"kind": "categorical", "fuzzy_threshold": 85,
                 "aliases": _DISTRICT_ALIASES},
    # Block is the Panchayat Samiti. 16 in the sample, 314 statewide.
    "block":    {"kind": "categorical", "fuzzy_threshold": 85,
                 "aliases": _BLOCK_ALIASES},
    # GP resolves to gp_lgd_code, never to a name. 20 in the sample (all
    # distinct), ~6,800 statewide where names certainly repeat — which is why
    # the collision machinery is built now and tested against a synthetic
    # duplicate fixture rather than against the sample. See test_gp_collisions.
    "gp":       {"kind": "roster", "fuzzy_threshold": 85, "aliases": _GP_ALIASES},

    # ── Time ─────────────────────────────────────────────────────────────────
    # The six exact strings from planned_activity.fiscal_year. Full form only:
    # '2024-25' matches nothing in the column, so date_phrase maps every
    # phrasing onto the stored nine characters before this validates.
    "fiscal_year": {"kind": "fiscal_year"},

    # ── Programme vocabulary ─────────────────────────────────────────────────
    "focus_area": {"kind": "categorical", "fuzzy_threshold": 85,
                   "aliases": _FOCUS_AREA_ALIASES},
    "theme":      {"kind": "categorical", "fuzzy_threshold": 85,
                   "aliases": _THEME_ALIASES},
    "scheme":     {"kind": "categorical", "fuzzy_threshold": 88,
                   "aliases": _SCHEME_ALIASES},
    "status":     {"kind": "categorical", "fuzzy_threshold": 88,
                   "aliases": _STATUS_ALIASES},
    # Asset coverage is sparse (4,286 of 12,704 activity rows carry a category)
    # and 8 of 36 category codes / 56 of 198 subcategory codes have no decode.
    # Both are WP-3 answer caveats; the registry's job is only to accept the
    # labels that DO decode.
    "asset_category":    {"kind": "categorical", "fuzzy_threshold": 85,
                          "aliases": _ASSET_CATEGORY_ALIASES},
    "asset_subcategory": {"kind": "categorical", "fuzzy_threshold": 88,
                          "aliases": {}},

    # ── Identifiers ──────────────────────────────────────────────────────────
    # planned_activity.activity_code — a key the user pastes, never a name to
    # resolve. Trimmed and bound verbatim; a wrong code returns no rows, which
    # is honest, whereas fuzzy-matching one key onto another is a wrong answer.
    "activity_code": {"kind": "passthrough"},

    # ── Numeric pass-through ─────────────────────────────────────────────────
    # 10,000 rather than WP-2's provisional 1,000 (decision D11.4, which asked
    # WP-3 to audit and raise if needed — it is needed). The audit of all 91
    # $top_n templates found 38 whose statewide result can exceed 1,000, in two
    # classes:
    #   * whole-roster rankings and listings at GP grain — "list every GP by
    #     unspent balance" is ~6,800 rows statewide, and a ceiling that refuses
    #     it makes a legitimate question unanswerable;
    #   * exception reports at ACTIVITY grain (ALR-*, DQY-*, EXP-03x) — those are
    #     unbounded, 12,704 activities in a 20-GP sample alone.
    # 10,000 clears the roster case with headroom. It deliberately does NOT clear
    # the activity case: serving tens of thousands of exception rows into a chat
    # answer is a pagination problem, not a limit to raise, and is flagged for
    # the operator in WP3_REPORT rather than solved by a bigger number here.
    "top_n":            {"kind": "numeric", "cast": int, "min": 1, "max": 10000},
    # The sheet is explicit that $threshold's unit varies by question — percent,
    # rupees, days, or a minimum activity count. Amount notation is accepted
    # because some of those questions ARE rupee questions; a bare number passes
    # through untouched, so the other three readings are unaffected.
    "threshold":        {"kind": "numeric", "cast": float, "min": 0,
                         "amount_units": True},
    "amount_threshold": {"kind": "numeric", "cast": float, "min": 0,
                         "amount_units": True},

    # ── Date ─────────────────────────────────────────────────────────────────
    # No deadline is stored anywhere in the database, so the GPDP-deadline
    # questions require the user to supply one.
    "deadline": {"kind": "date"},

    # ── Paired slots: same values and aliases as their base type ─────────────
    "fiscal_year_2": {"mirrors": "fiscal_year"},
    "block_2":       {"mirrors": "block"},
    "gp_2":          {"mirrors": "gp"},
    "scheme_2":      {"mirrors": "scheme"},
}


# The workbook's Parameter Registry sheet, as data. Catalogue entries authored
# in WP-3 declare `"entity_type": PARAM_ENTITY_TYPES["<bind name>"]` (or just
# the value), so the sheet's 19 bind names and this module's entity types cannot
# drift apart. `test_extraction_enums` asserts every bind name is covered.
PARAM_ENTITY_TYPES: dict[str, str] = {
    "date_range":         "fiscal_year",
    "date_range_2":       "fiscal_year_2",
    "district_name":      "district",
    "block_name":         "block",
    "block_name_2":       "block_2",
    "gp_name":            "gp",
    "gp_name_2":          "gp_2",
    "focus_area":         "focus_area",
    "theme":              "theme",
    "scheme":             "scheme",
    "scheme_2":           "scheme_2",
    "status":             "status",
    "asset_category":     "asset_category",
    "asset_sub_category": "asset_subcategory",
    "activity_code":      "activity_code",
    "top_n":              "top_n",
    "threshold":          "threshold",
    "amount_threshold":   "amount_threshold",
    "deadline":           "deadline",
}


# Scope markers, not real entities — "how is the state doing" must not fuzzy-
# match some block called "Statepur". The router turns an empty geography into
# the state-wide reading, which under decision D2 means binding NULL rather than
# stalling for a clarification.
_STATE_LEVEL_TERMS = {
    "odisha", "orissa", "state", "the state", "all", "any",
    "entire state", "whole state", "statewide", "state wide", "across the state",
    "all districts", "all blocks", "all gps", "all gram panchayats",
    "all panchayats", "everywhere",
}

# Both the entity types and the workbook's bind names: `pending_resolver` tests
# membership with whichever of the two the pending carries, and a scope-widening
# reply must be recognised either way.
_GEO_TYPES = {
    "district", "block", "gp", "block_2", "gp_2",
    "district_name", "block_name", "gp_name", "block_name_2", "gp_name_2",
}

# The activity_status decode carries a sixth label, 'Buildings', on code 173 —
# which is an asset_category value, so the decoder plainly picked from the wrong
# code list. Keeping it out of the enum stops "which activities are Buildings?"
# routing to a status filter; logging it is how the operator gets to fix the
# source. Validation logs, never fixes.
_SUSPECT_STATUS_LABELS = {"buildings"}

AADHAAR_LENGTH = 12


def mask_aadhaar(value: str) -> str:
    """'726018159083' -> 'XXXX-XXXX-9083'. Never show a full Aadhaar in an answer.

    Dormant for PR&DW — the panchayat database holds no Aadhaar, and a GP's LGD
    code is a public identifier that is shown in full. Kept because `zones` and
    `router` call it on the shared candidate path, and because the person
    entities the bootstrap anticipates (sarpanch, secretary) would need it back.
    A value that is not exactly 12 digits passes through unchanged, so an LGD
    code is never mangled by it.
    """
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) != AADHAAR_LENGTH:
        return str(value)
    return f"XXXX-XXXX-{digits[-4:]}"


# ── Gram Panchayats, not names ────────────────────────────────────────────────
# The sample's 20 GP names happen to be unique, and nothing here may depend on
# that. Statewide there are ~6,800 GPs across 314 blocks and 30 districts, and
# GP names repeat freely — 'Naugaon' and 'Rampur' several times over. Binding a
# name would then quietly aggregate several panchayats into one answer, which is
# the AP name-collision defect (four Lakshmi Devis reported as one farmer's
# ₹259,181) transplanted into geography. Every template binds `gp_lgd_code`.


@dataclass(frozen=True)
class GramPanchayat:
    """One roster row: a panchayat, with what tells it apart from its namesakes.

    District alone will not do it statewide — a district holds ~10 blocks and a
    name can repeat inside one — so the reference form is name + block, with the
    LGD code as the final tiebreak.
    """
    lgd_code: str
    name:     str
    block:    str
    district: str


def gp_ref(gp: GramPanchayat) -> str:
    """'Naugaon of Barpali' — the sayable, routable form of one panchayat."""
    return f"{gp.name} of {gp.block}" if gp.block else gp.name


def describe_gp(gp: GramPanchayat) -> str:
    """How one GP reads in a disambiguation prompt."""
    if gp.block and gp.district:
        return f"{gp.name} ({gp.block} block, {gp.district} district)"
    if gp.district:
        return f"{gp.name} ({gp.district} district)"
    return gp.name


# "Naugaon of Barpali" / "…of Barpali, Bargarh district".
_GP_REF_RE = re.compile(r"^(?P<name>.+?)\s+of\s+(?P<place>.+)$", re.IGNORECASE)
# An LGD code inside a reference — the tiebreak a chip appends when name + block
# still names two GPs. Public, so it is shown and sent in full.
_CODE_RE = re.compile(r"(?<!\d)\d{4,}(?!\d)")
# Words that name the KIND of place rather than the place: "Barpali block".
_PLACE_NOUNS = {
    "block", "blocks", "district", "districts", "gp", "gps",
    "panchayat", "panchayats", "gram", "village", "samiti",
    "zilla", "parishad", "zp", "subdivision", "sub-division",
}

# Every GP sharing a name has to be OFFERABLE: truncating to three or four
# options leaves the rest unreachable and per-GP lookup for them silently
# impossible. Statewide a common name may be held by a dozen panchayats, so
# raise this rather than trim the list.
MAX_GP_CANDIDATES = 12


def _place_tokens(place: str) -> list[str]:
    """'Barpali, Bargarh district' -> ['barpali', 'bargarh'].

    An LGD code is pulled out first: it is one token containing no spaces but
    also no comma, so the ordinary split would glue it to the block name.
    """
    text = str(place)
    tokens = [m.group(0) for m in _CODE_RE.finditer(text)]
    for part in re.split(r"[,/]", _CODE_RE.sub(" ", text)):
        words = _collapse_ws(part).split()
        while words and words[-1] in _PLACE_NOUNS:
            words.pop()
        while words and words[0] in _PLACE_NOUNS:
            words.pop(0)
        if words:
            tokens.append(" ".join(words))
    return tokens


def _place_matches(gp: GramPanchayat, place: str) -> bool:
    """Does this GP sit in EVERY place the reference named?

    Equality, not containment: 'Sheragada' must not also select a block called
    'Sheragada North', because the whole point of the reference is that it picks
    exactly one of several same-name panchayats.
    """
    fields = {
        _collapse_ws(gp.block),
        _collapse_ws(gp.district),
        _collapse_ws(gp.lgd_code),
    }
    fields.discard("")
    tokens = _place_tokens(place)
    return bool(tokens) and all(_collapse_ws(t) in fields for t in tokens)


def _resolve_config(entity_type: str) -> tuple[str, dict]:
    """(base type, config) — following a 'mirrors' pointer if there is one."""
    cfg = REGISTRY_CONFIG.get(entity_type, {})
    base = cfg.get("mirrors")
    if base:
        return base, REGISTRY_CONFIG.get(base, {})
    return entity_type, cfg


def _format_number(value) -> str:
    """2.0 -> '2', 2.5 -> '2.5' — reads better in query_description, and keeps
    an integer rupee figure out of scientific notation at crore scale."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ── Deadlines ─────────────────────────────────────────────────────────────────
# ISO in, ISO out. The named-month forms are accepted because they are
# unambiguous; an all-numeric day/month pair is accepted ONLY when the first
# field cannot be a month. '06/07/2024' is refused outright rather than read as
# one of the two dates it might be: a deadline decides which plans count as
# late, so guessing here silently reclassifies the answer.
_DATE_FORMATS = (
    "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%d-%B-%Y", "%d-%b-%Y",
)
_NUMERIC_DATE_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$")


def parse_deadline(raw: str) -> str:
    """'2024-06-30' / '30 June 2024' / '30-06-2024' -> '2024-06-30'.

    Raises ValueError for anything unparseable OR genuinely ambiguous.
    """
    text = re.sub(r"\s+", " ", str(raw or "")).strip().strip(",.")
    if not text:
        raise ValueError("empty deadline")
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text.replace(",", ""), fmt).date().isoformat()
        except ValueError:
            continue
    m = _NUMERIC_DATE_RE.match(text)
    if m:
        first, second, year = (int(g) for g in m.groups())
        if first > 12:      # unambiguously a day; the other field is the month
            return date(year, second, first).isoformat()
        raise ValueError(
            f"ambiguous date {text!r} — give it as YYYY-MM-DD"
        )
    raise ValueError(f"not a date: {raw!r}")


class EntityValidator:
    def __init__(self, cache_conn):
        self._registry: dict[str, list[str]] = {}
        # Same values as _registry, ordered most-relevant-first. Chips only.
        self._registry_ranked: dict[str, list[str]] = {}
        # collapsed name -> the exact stored value, for O(1) canonicalisation.
        self._by_norm: dict[str, dict[str, str]] = {}
        # The identity half of the roster: collapsed GP name -> the PANCHAYATS
        # that hold it, plus the code index a chip's reply resolves through.
        self._gps_by_name: dict[str, list[GramPanchayat]] = {}
        self._gp_by_code: dict[str, GramPanchayat] = {}
        # gp name -> the districts it occurs in, for the multi-NAME prompt.
        self._gp_districts: dict[str, list[str]] = {}
        self._load(cache_conn)

    # ── Registry loading ──────────────────────────────────────────────────────

    def _query(self, cache_conn, sql: str) -> list[tuple]:
        try:
            return cache_conn.execute(sql).fetchall()
        except Exception as exc:
            _log.warning("entity registry query failed (%s): %s", sql.strip()[:60], exc)
            return []

    # The allowed-values queries from the workbook's Parameter Registry sheet,
    # verbatim. WP-2 had to substitute base-table decodes for four of them
    # because the v_* views were absent; WP-3 created the views (see
    # db_factory._seed_views) and switched all four back. The registry now reads
    # exactly the columns the catalogue SQL filters on, which is the only way a
    # validated value is guaranteed to match.
    #
    # THE VIEW IS THE SOURCE OF TRUTH, NOT THE DECODE BEHIND IT. Three values
    # moved in the switch, and each one matters:
    #   status_label      the view TRIMs and de-tabs the decode, so the registry
    #                     now holds 'WORK COMPLETED' where WP-2 held
    #                     '\tWORK COMPLETED'. This is WP2_REPORT §4.1's marked
    #                     switch. Binding the tabbed form against the view would
    #                     answer "no activities are complete" — same value count
    #                     (6), opposite meaning.
    #   asset_*_label     the view COALESCEs an undecoded code to 'Uncategorised'
    #                     (+1 value each). That is not padding: 8,439 of the
    #                     12,704 asset rows are 'Uncategorised', the single
    #                     largest bucket, and it is a legitimate thing to ask
    #                     about. Omitting it would refuse a question the view can
    #                     answer.
    # `theme` deliberately still reads dim_lsdg_theme, because that is the query
    # the sheet gives for it. v_activity.theme carries a seventh value,
    # 'Unmapped theme', for the 13 focus areas with no LSDG mapping; it is a
    # view artefact rather than a theme, so it is not offered as one.
    _DB_SOURCES: dict[str, str] = {
        "district": 'SELECT DISTINCT zp_name FROM gram_panchayat '
                    'WHERE zp_name IS NOT NULL',
        "block":    'SELECT DISTINCT block_name FROM gram_panchayat '
                    'WHERE block_name IS NOT NULL',
        "gp":       'SELECT DISTINCT gp_name FROM gram_panchayat '
                    'WHERE gp_name IS NOT NULL',
        "fiscal_year": 'SELECT DISTINCT fiscal_year FROM planned_activity '
                       'WHERE fiscal_year IS NOT NULL',
        "focus_area":  "SELECT DISTINCT description FROM dim_code "
                       "WHERE variable = 'focus_area' AND description IS NOT NULL",
        "theme":       'SELECT DISTINCT lsdg_theme FROM dim_lsdg_theme '
                       'WHERE lsdg_theme IS NOT NULL',
        "scheme":      'SELECT DISTINCT scheme_name FROM activity_expenditure '
                       'WHERE scheme_name IS NOT NULL',
        "status":            'SELECT DISTINCT status_label FROM v_activity '
                             'WHERE status_label IS NOT NULL',
        "asset_category":    'SELECT DISTINCT asset_category_label FROM v_asset '
                             'WHERE asset_category_label IS NOT NULL',
        "asset_subcategory": 'SELECT DISTINCT asset_subcategory_label FROM v_asset '
                             'WHERE asset_subcategory_label IS NOT NULL',
    }

    # Same vocabulary, ordered by how much of the data each value actually
    # covers. Offering three alphabetically-first focus areas as examples is a
    # worse prompt than offering the ones GPs actually plan under. Matching
    # never uses this order — only chips do.
    _RANKED_SOURCES: dict[str, str] = {
        "district": 'SELECT zp_name FROM gram_panchayat WHERE zp_name IS NOT NULL '
                    'GROUP BY zp_name ORDER BY COUNT(*) DESC',
        "block":    'SELECT block_name FROM gram_panchayat WHERE block_name IS NOT NULL '
                    'GROUP BY block_name ORDER BY COUNT(*) DESC',
        # Newest first: an officer offered a year wants the current one.
        "fiscal_year": 'SELECT DISTINCT fiscal_year FROM planned_activity '
                       'WHERE fiscal_year IS NOT NULL ORDER BY fiscal_year DESC',
        # The fourth WP-2 substitute, switched to the view. Same 30 values in the
        # same frequency order; the join was already equivalent, but reading the
        # view keeps every allowed-values query pointed at the column the
        # catalogue actually filters on.
        "focus_area": 'SELECT focus_area_name FROM v_activity '
                      'WHERE focus_area_name IS NOT NULL '
                      'GROUP BY focus_area_name ORDER BY COUNT(*) DESC',
        "scheme": 'SELECT scheme_name FROM activity_expenditure '
                  'WHERE scheme_name IS NOT NULL '
                  'GROUP BY scheme_name ORDER BY COUNT(*) DESC',
    }

    def _load(self, cache_conn) -> None:
        """Every registry comes from the database, read-only, at startup.

        Nothing is hard-coded, so loading the statewide extract behind the same
        `db_factory` adapter grows 9 districts to 30 and 20 GPs to ~6,800 with
        no code change (decision D4).
        """
        for etype, sql in self._DB_SOURCES.items():
            rows = self._query(cache_conn, sql)
            values = [str(r[0]) for r in rows if r[0] is not None]
            if etype == "status":
                values = self._filter_status(values)
            # Sorted on the COLLAPSED form so a leading tab does not push
            # '\tWORK COMPLETED' to the front of every chip list, while the
            # stored bytes are what gets kept.
            self._registry[etype] = sorted(set(values), key=_collapse_ws)
            self._by_norm[etype] = {_collapse_ws(v): v for v in self._registry[etype]}
            self._warn_about_whitespace(etype, self._registry[etype])

        for etype, sql in self._RANKED_SOURCES.items():
            rows = self._query(cache_conn, sql)
            ranked = [str(r[0]) for r in rows if r[0] is not None]
            seen: set[str] = set()
            ordered = [v for v in ranked if not (v in seen or seen.add(v))]
            if ordered:
                self._registry_ranked[etype] = ordered

        self._load_gp_roster(cache_conn)

        _log.info(
            "entity registries: %s",
            ", ".join(f"{k}={len(v)}" for k, v in sorted(self._registry.items()) if v),
        )

    @staticmethod
    def _filter_status(values: list[str]) -> list[str]:
        """Drop the suspected bad decode, and say so. See _SUSPECT_STATUS_LABELS."""
        kept, dropped = [], []
        for v in values:
            (dropped if _collapse_ws(v) in _SUSPECT_STATUS_LABELS else kept).append(v)
        if dropped:
            _log.warning(
                "status registry: excluded %s — 'Buildings' is an asset_category "
                "label appearing in the activity_status decode (dim_code code 173), "
                "so it is a decoder defect in the SOURCE. Not repaired here; "
                "reported for the data owner.",
                sorted(set(dropped)),
            )
        return kept

    @staticmethod
    def _warn_about_whitespace(etype: str, values: list[str]) -> None:
        """Log source values that carry stray whitespace, and bind them anyway.

        `dim_lsdg_theme` has a trailing space on one theme and the
        `activity_status` decode has a leading TAB on 'WORK COMPLETED'. The
        column stores those bytes, so the registry must too — a trimmed value
        filters to zero rows and the answer says "no activities are complete",
        which is worse than untidy.
        """
        odd = [v for v in values if v != v.strip() or "\t" in v or "  " in v]
        if odd:
            _log.warning(
                "%s registry: %d value(s) carry stray whitespace in the SOURCE "
                "and are bound verbatim (trimming them would filter to zero "
                "rows): %s",
                etype, len(odd), [repr(v) for v in odd[:5]],
            )

    def _load_gp_roster(self, cache_conn) -> None:
        """The GP roster as PANCHAYATS: one query feeds the code index that
        every template binds through and the block/district qualifiers a
        collision prompt needs."""
        rows = self._query(
            cache_conn,
            "SELECT gp_lgd_code, gp_name, block_name, zp_name FROM gram_panchayat "
            "WHERE gp_name IS NOT NULL",
        )
        for code, name, block, district in rows:
            name = str(name).strip()
            code = str(code or "").strip()
            districts = self._gp_districts.setdefault(_collapse_ws(name), [])
            if district and str(district) not in districts:
                districts.append(str(district))
            if not code or code in self._gp_by_code:
                # No usable identity, or a duplicate roster row. The NAME still
                # validates; it simply cannot bind a code, and the caller is
                # told so rather than being handed the name as a substitute.
                if not code:
                    _log.warning("gram_panchayat row %r has no gp_lgd_code", name)
                continue
            gp = GramPanchayat(
                lgd_code=code, name=name,
                block=str(block or ""), district=str(district or ""),
            )
            self._gp_by_code[code] = gp
            self._gps_by_name.setdefault(_collapse_ws(name), []).append(gp)

        shared = {n: g for n, g in self._gps_by_name.items() if len(g) > 1}
        if shared:
            _log.info(
                "GP roster: %d of %d names are held by more than one panchayat "
                "(worst: %d)", len(shared), len(self._gps_by_name),
                max(len(g) for g in shared.values()),
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
        if kind == "date":
            return self._validate_date(raw_value, entity_type)

        raw_text = str(raw_value)
        if base_type in _GEO_TYPES and _collapse_ws(raw_text) in _STATE_LEVEL_TERMS:
            # Not an error the user should see as "unknown district" — under D2
            # the router binds NULL for an absent optional geography, which IS
            # the state-wide reading.
            raise EntityNotFound(entity_type, raw_text, [])

        if kind == "fiscal_year":
            return self._validate_fiscal_year(raw_text, entity_type, base_type)
        if kind == "roster":
            return self._validate_roster(raw_text, entity_type, base_type, cfg)
        if kind == "passthrough":
            # Trim and collapse whitespace, resolve nothing. activity_code is a
            # key the user pasted: fuzzy-matching one key onto a different one
            # would answer about a different activity entirely.
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
        text = str(raw_value).strip().rstrip("%").strip()

        if cfg.get("amount_units"):
            # "2.5 crore" -> 25000000. A bare number is still accepted and read
            # as rupees, so a question already asked in figures — and every
            # non-money reading of $threshold — keeps working unchanged.
            try:
                number, unit = parse_amount(text)
            except ValueError:
                raise EntityNotFound(entity_type, str(raw_value), [])
            self._check_numeric_range(number, entity_type, raw_value, cfg)
            # "converted" only when the unit actually moved the number, so
            # "50000" is not echoed back as the redundant "50000 (₹50,000)".
            converted = unit is not None and AMOUNT_UNIT_FACTORS[unit] != 1.0
            return self._entity(entity_type, raw_value, _format_number(number),
                                "converted" if converted else "numeric")

        text = text.replace(",", "")
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

    def _validate_date(self, raw_value, entity_type: str) -> ExtractedEntity:
        try:
            return self._entity(entity_type, raw_value, parse_deadline(raw_value), "exact")
        except ValueError:
            raise EntityNotFound(entity_type, str(raw_value), [])

    # ── Fiscal year ───────────────────────────────────────────────────────────

    def _validate_fiscal_year(
        self, raw_text: str, entity_type: str, base_type: str
    ) -> ExtractedEntity:
        """One of the six stored strings, however the user said it.

        The abbreviated forms are the whole point: `fiscal_year` is a VARCHAR
        equality filter, so '2024-25' binds successfully and matches nothing —
        a zero-row answer with no error anywhere. date_phrase maps every
        phrasing onto the stored full form before membership is tested.
        """
        known = self._registry.get(base_type, [])
        norm = _collapse_ws(raw_text)

        exact = self._by_norm.get(base_type, {}).get(norm)
        if exact is not None:
            return self._entity(entity_type, raw_text, exact, "exact")

        years = resolve_fiscal_years(raw_text, known)
        # A paired slot takes the OTHER end of a two-year phrase: "compare the
        # last two years" fills $date_range with the earlier and $date_range_2
        # with the later, which is the only reading a comparison template has.
        # (`resolve_fiscal_years` returns them oldest-first.)
        if len(years) > 1:
            years = years[-1:] if entity_type != base_type else years[:1]

        for candidate in years:
            stored = self._by_norm.get(base_type, {}).get(_collapse_ws(candidate))
            if stored is not None:
                return self._entity(entity_type, raw_text, stored, "alias")

        # Either nothing year-shaped was said, or a year the database does not
        # hold. Both are honest refusals; the suggestions are the loaded years,
        # which is what the clarification chips offer.
        raise EntityNotFound(entity_type, raw_text, list(known))

    def fiscal_years(self) -> list[str]:
        """The loaded fiscal years, oldest first. The axis 'last year' moves on."""
        return sorted(self._registry.get("fiscal_year", []))

    # ── One name → one panchayat ──────────────────────────────────────────────

    def _validate_roster(
        self, raw_text: str, entity_type: str, base_type: str, cfg: dict
    ) -> ExtractedEntity:
        roster = self._registry.get(base_type, [])
        norm = _collapse_ws(raw_text)

        # An LGD code where a name was expected. Not something a user usually
        # types — it is the unambiguous form a disambiguation chip sends back,
        # and it is public, so unlike an Aadhaar it is also fine to show.
        code = raw_text.strip()
        if code in self._gp_by_code:
            gp = self._gp_by_code[code]
            namesakes = self._gps_by_name.get(_collapse_ws(gp.name), [])
            return self._gp_entity(
                entity_type, raw_text, gp,
                gp_ref(gp) if len(namesakes) > 1 else gp.name,
            )

        # EXACT MATCH FIRST, and no fuzzy expansion runs when there is one. A
        # roster name the user typed verbatim must never reach the fuzzy
        # expansion below, or a real GP gets buried in a "Several panchayats
        # match…" prompt alongside places that merely resemble it —
        # 'Laxmipur' is a real GP and also fuzzy-matches 'Laxmipur' the block.
        #
        # It short-circuits to a NAME, though, not to a panchayat: the roster is
        # deduplicated, so a shared name appears here exactly once and several
        # GPs would collapse into one bound value. _bind_gp is where that is
        # decided.
        exact = self._by_norm.get(base_type, {}).get(norm)
        if exact is not None:
            return self._bind_gp(entity_type, raw_text, exact, None, "exact")

        aliases = {_collapse_ws(k): v for k, v in cfg.get("aliases", {}).items()}
        if norm in aliases:
            target = self._canonical(base_type, aliases[norm])
            return self._bind_gp(entity_type, raw_text, target, None, "alias")

        # "<roster name> of <block>" — the reference a disambiguation chip sends
        # back, and what an officer who knows the block would say anyway. Tried
        # only when the head is a VERBATIM roster name, so an ordinary name is
        # never split on a stray "of", and only AFTER the exact test above, so a
        # GP whose name itself contained " of " would have won.
        split = self._split_gp_ref(base_type, raw_text)
        if split is not None:
            name, place = split
            return self._bind_gp(entity_type, raw_text, name, place, "exact")

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
            top = process.extract(norm, [_collapse_ws(v) for v in roster],
                                  scorer=fuzz.WRatio, limit=3)
            raise EntityNotFound(entity_type, raw_text, [roster[t[2]] for t in top])

        if len(names) == 1:
            confidence = "exact" if _collapse_ws(names[0]) == norm else "fuzzy"
            return self._bind_gp(entity_type, raw_text, names[0], None, confidence)

        # Several DIFFERENT NAMES answer to this — asking is the only safe move.
        # (One name held by several panchayats is the other ambiguity and is
        # raised by _bind_gp; a tap here lands on a name and cascades into it.)
        shortlist = names[:4]
        raise ClarificationNeeded(
            f"Several panchayats match '{raw_text}': "
            + "; ".join(self._describe_gp_name(n) for n in shortlist)
            + ". Which one do you mean?",
            entity_type=entity_type,
            raw_value=raw_text,
            candidates=[
                EntityCandidate(
                    name=name,
                    districts=list(self._gp_districts.get(_collapse_ws(name), [])),
                )
                for name in shortlist
            ],
        )

    def _describe_gp_name(self, name: str) -> str:
        districts = self._gp_districts.get(_collapse_ws(name), [])
        return f"{name} ({', '.join(districts)})" if districts else name

    def _split_gp_ref(self, base_type: str, raw_text: str) -> tuple[str, str] | None:
        """('Naugaon', 'Barpali') for a reference, None for a plain name."""
        match = _GP_REF_RE.match(str(raw_text).strip())
        if not match:
            return None
        name = self._by_norm.get(base_type, {}).get(_collapse_ws(match.group("name")))
        if name is None:
            return None
        return name, match.group("place")

    def _gp_entity(
        self, entity_type: str, raw_value, gp: GramPanchayat,
        resolved: str, confidence: str = "exact",
    ) -> ExtractedEntity:
        entity = self._entity(entity_type, raw_value, resolved, confidence)
        entity.resolved_code = gp.lgd_code
        return entity

    def _bind_gp(
        self, entity_type: str, raw_text: str, name: str,
        place: str | None, confidence: str,
    ) -> ExtractedEntity:
        """One roster NAME has been resolved. Now resolve it to one PANCHAYAT.

        This is the whole defect the collision guard exists for: a name several
        GPs answer to must reach a clarify and never a silent pick, because the
        templates aggregate expenditure and a merged total is reported to nobody
        as somebody's figure.
        """
        gps = self._gps_by_name.get(_collapse_ws(name), [])
        if not gps:
            # A name the registry knows but the code index does not — a roster
            # row with no gp_lgd_code, or a stubbed registry in a test. Bind the
            # name; nothing here can improve on it, and the caller sees no
            # resolved_code so a code-bound slot fails loudly rather than
            # silently filtering by name.
            return self._entity(entity_type, raw_text, name, confidence)

        shortlist = gps
        if place:
            narrowed = [g for g in gps if _place_matches(g, place)]
            if narrowed:
                shortlist = narrowed

        if len(shortlist) == 1:
            gp = shortlist[0]
            # The reference has to survive a round trip: when the name is
            # shared, resolved_value carries the block, so a chained clarify
            # that re-validates everything already filled lands on the SAME
            # panchayat instead of asking again — an unbreakable loop otherwise.
            # A name only one GP holds reads exactly as the user wrote it.
            resolved = gp_ref(gp) if len(gps) > 1 else gp.name
            return self._gp_entity(entity_type, raw_text, gp, resolved, confidence)

        raise ClarificationNeeded(
            f"{len(shortlist)} different gram panchayats are called '{name}': "
            + "; ".join(describe_gp(g) for g in shortlist[:MAX_GP_CANDIDATES])
            + ". Which one do you mean?",
            entity_type=entity_type,
            raw_value=raw_text,
            candidates=[
                EntityCandidate(
                    name=g.name,
                    districts=[g.district] if g.district else [],
                    parent_place=g.block or None,   # the narrower place; see models
                    code=g.lgd_code,
                )
                for g in shortlist[:MAX_GP_CANDIDATES]
            ],
        )

    # ── Registry access ───────────────────────────────────────────────────────

    def registry_values(
        self, entity_type: str, *, by_frequency: bool = False
    ) -> list[str]:
        """The known values for an entity type — used to offer example chips
        when a question can only be answered one value at a time.

        `by_frequency` asks for most-relevant-first, which is what makes a short
        example list representative rather than merely alphabetical. Falls back
        to the sorted vocabulary where no ranking was loaded.
        """
        base_type, _ = _resolve_config(entity_type)
        if by_frequency and base_type in self._registry_ranked:
            return list(self._registry_ranked[base_type])
        return list(self._registry.get(base_type, []))

    def _canonical(self, base_type: str, value: str) -> str:
        """The exact stored string for a value written in clean form.

        This is what lets an alias table say 'WORK COMPLETED' while the column
        holds '\\tWORK COMPLETED', and 'Theme 5 - Clean and Green Village' while
        the column holds it with a trailing space. Unknown values pass through
        unchanged, so an alias pointing outside the loaded registry still binds
        what it says (and then honestly returns no rows).
        """
        return self._by_norm.get(base_type, {}).get(_collapse_ws(value), value)

    def _validate_categorical(
        self, raw_text: str, entity_type: str, base_type: str, cfg: dict
    ) -> ExtractedEntity:
        aliases      = {_collapse_ws(k): v for k, v in cfg.get("aliases", {}).items()}
        threshold    = cfg.get("fuzzy_threshold", DEFAULT_FUZZY_THRESHOLD)
        valid_values = self._registry.get(base_type, [])
        norm         = _collapse_ws(raw_text)

        exact = self._by_norm.get(base_type, {}).get(norm)
        if exact is not None:
            return self._entity(entity_type, raw_text, exact, "exact")

        if norm in aliases:
            return self._entity(
                entity_type, raw_text, self._canonical(base_type, aliases[norm]), "alias"
            )

        if valid_values and threshold < 100:
            match = process.extractOne(
                norm, [_collapse_ws(v) for v in valid_values],
                scorer=fuzz.WRatio, score_cutoff=threshold,
            )
            if match:
                _, _, idx = match
                return self._entity(entity_type, raw_text, valid_values[idx], "fuzzy")

        suggestions: list[str] = []
        if valid_values:
            top = process.extract(norm, [_collapse_ws(v) for v in valid_values],
                                  scorer=fuzz.WRatio, limit=3)
            suggestions = [valid_values[t[2]] for t in top]
        raise EntityNotFound(entity_type, raw_text, suggestions)

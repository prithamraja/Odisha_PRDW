"""
Step 2: Extract entity values from the user query.
Given the chosen template, we know exactly which slots to look for — so the
prompt is small and targeted, making extraction very reliable.

**The enum lists in this prompt are GENERATED FROM THE REGISTRY at import time,
never hand-written.** This is the single most expensive lesson the two previous
deployments paid for: an incomplete enumeration is a value the extractor
*cannot emit*, whatever the validator would have accepted, and the failure is
silent. In AP it returned 9 rows where 38 were right, and 200 confidently wrong
rows on another question — routing correct throughout, so no query_id assertion
would ever have caught it. `test_extraction_enums.py` is the agreement gate;
`_registry_enum` below is why it can stay green without anybody remembering to
update prose.

The registry values come from the database, so the enums are also how the
prompt learns 30 districts instead of 9 when the statewide extract lands — no
edit here at all.

Division of labour with `entity_validator`: this module emits the user's RAW
SURFACE FORM ("khordha", "FY 24-25", "1 lakh"); validation owns resolution to
the stored value ("Khordha", "2024-2025", 100000). The one thing extraction must
get right is WHICH SLOT a value belongs in.
"""
import json
import logging

from openai import OpenAI
from .config import (
    EXTRACTION_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS_EXTRACT,
    LLM_TIMEOUT_SECONDS,
    REASONING_MODELS,
)
from .llm_usage import record_call, record_extraction

_log = logging.getLogger(__name__)

# How many values to spell out before falling back to "…". Status, scheme and
# theme are small and are ALWAYS listed in full: those are the slots where a
# missing value silently mis-binds. Districts and blocks are long lists whose
# job is to tell the model what a district looks like, not to be exhaustive —
# the validator's fuzzy+alias cascade catches the rest, and an unresolvable
# place clarifies rather than mis-binding.
_FULLY_ENUMERATED = {"status", "scheme", "theme", "fiscal_year"}
_ENUM_SAMPLE = 12


def _registry_enum(values: list[str], *, full: bool) -> str:
    """The values, as they should read inside a prompt rule line.

    Whitespace is stripped for DISPLAY only — 'Theme 5 - Clean and Green
    Village ' would otherwise put a trailing space before a comma and teach the
    model to emit it. The validator matches on the collapsed form, so a model
    that echoes the tidy label still resolves onto the stored one.
    """
    cleaned = [" ".join(str(v).split()) for v in values]
    cleaned = [v for v in cleaned if v]
    if not cleaned:
        return ""
    if full or len(cleaned) <= _ENUM_SAMPLE:
        return ", ".join(cleaned)
    return ", ".join(cleaned[:_ENUM_SAMPLE]) + ", …"


# ── The prompt ────────────────────────────────────────────────────────────────
# {…_enum} placeholders are filled by `refresh_prompt_enums` from the live
# registry. Until it runs they hold the empty string, which the agreement test
# treats as a failure — an empty enum must never look like a passing one.

_PROMPT_TEMPLATE = """\
Extract entity values from this Odisha Panchayati Raj & Drinking Water (PR&DW) query.
Questions come from block and district programme officers and are often code-mixed \
(Odia words or transliteration inside an English sentence). Read the meaning, and \
return values in ENGLISH using the spellings below.
{intent_context}
Query: "{query}"

Extract ONLY these specific values (return null if not present):
{slot_lines}

Rules:
- For district: the district (Zilla Parishad). Return the name in ENGLISH standard \
spelling: {district_enum}. "khordha"/"khurda" → "Khordha". A district is the WIDEST \
tier; do not put a block or GP name here.
- For block: the block, also called the Panchayat Samiti: {block_enum}. A block sits \
inside a district and contains gram panchayats.
- For gp: the gram panchayat, the narrowest tier. Return the GP name exactly as \
written in the query, without the words "GP", "gram panchayat" or "panchayat" — \
"GPDP status of Andhrua GP" → "Andhrua". KEEP a trailing "of <place>" that directly \
follows the name — "Naugaon of Barpali" stays "Naugaon of Barpali" — because GP names \
repeat across blocks and the block is what says which panchayat is meant. This applies \
ONLY when "of <place>" follows a GP name; "panchayats of Khordha" names no GP, so gp is \
null there and district is "Khordha".
- For block_2 / gp_2: the SECOND place named, when the query compares two. \
"Compare Barpali and Bheden blocks" → block="Barpali", block_2="Bheden". (There is no \
district_2 slot — the catalogue compares districts a different way.)
- For fiscal_year: COPY the year phrase AS THE USER WROTE IT — "FY 24-25" → "FY 24-25", \
"2024-25" → "2024-25", "last year" → "last year", "in 2024" → "2024". Do NOT expand, \
reformat or convert it; the caller maps every phrasing onto the exact stored value. If \
no year is named at all, return null. The years held in the data are: {fiscal_year_enum}
- For fiscal_year_2: the SECOND year, for year-on-year comparisons. "2024-25 vs 2023-24" \
→ fiscal_year="2024-25", fiscal_year_2="2023-24". For "the last two years" put the whole \
phrase in BOTH slots and let the caller split it.
- For focus_area: one of the Eleventh Schedule subjects: {focus_area_enum}. Map the \
colloquial names: toilets, SBM, ODF → "Sanitation"; piped water, Jal Jeevan → "Drinking \
water"; anganwadi, ICDS → "Women and child development"; street light → "Rural \
electrification".
- For theme: one of the LSDG themes, exactly: {theme_enum}. "clean and green" → \
"Theme 5 - Clean and Green Village". Return null if no theme is named.
- For scheme / scheme_2: return exactly one of: {scheme_enum}. Map the colloquial names: \
CFC, central finance commission, 15th FC → "XV Finance Commission"; SFC, state finance \
commission → "5TH STATE FINANCE COMMISSION"; own source revenue, OSR → "Own Funds". If \
the query mentions no scheme from the list, return null.
- For status: the work status, exactly one of: {status_enum}. Map: ongoing, in progress \
→ "WORK ONGOING"; finished, done → "WORK COMPLETED"; stalled, dropped → "WORK \
ABANDONED"; pending/awaiting approval → "UNDER APPROVAL".
- For asset_category / asset_subcategory: the asset classification as written, e.g. \
{asset_category_enum}
- For activity_code: the activity identifier, copied exactly as given. Never invent one.
- For numeric slots (top_n, threshold): return a BARE NUMBER with no units, no "%" and \
no words. Example: "top 20 GPs" → top_n=20. Example: "above 50 percent" → threshold=50. \
(amount_threshold is the exception — see its own rule below.)
- For amount_threshold specifically, and for threshold WHEN THE QUESTION IS ABOUT MONEY: \
COPY the figure WITH ITS MULTIPLIER WORD exactly as the user gave it — "above 1 lakh" → \
"1 lakh", "more than 2.5 crore" → "2.5 crore", "over ₹50,000" → "50000". Do NOT convert \
between lakh/crore and plain rupees; the caller does that, deterministically.
- For top_n specifically: a BARE SUPERLATIVE with no number attached means one. "Which \
GP spent the most?", "which block has the highest completion rate" → top_n=1. A number \
always wins over the superlative: "top 5 GPs by expenditure" → top_n=5. If the query asks \
to rank or list with no number and no superlative ("Rank GPs by expenditure"), return \
null and let the caller apply its default.
- For deadline: COPY the date as written — "by 30 June 2024" → "30 June 2024", \
"before 2024-06-30" → "2024-06-30". Do not reformat it.

Examples (officer phrasings, including code-mixed):
Q: "GPDP status of Andhrua" → {{"gp": "Andhrua"}}
Q: "khordha me kitne GP ne 2024-25 ka plan approve kiya?" → {{"district": "Khordha", \
"fiscal_year": "2024-25"}}
Q: "Barpali block ki sanitation activities last year" → {{"block": "Barpali", \
"focus_area": "Sanitation", "fiscal_year": "last year"}}
Q: "Top 5 GPs by expenditure under XV Finance Commission in Ganjam" → {{"top_n": 5, \
"scheme": "XV Finance Commission", "district": "Ganjam"}}
Q: "Which works are still ongoing in Naugaon of Barpali?" → {{"gp": "Naugaon of Barpali", \
"status": "WORK ONGOING"}}
Q: "activities above 1 lakh in FY 24-25" → {{"amount_threshold": "1 lakh", \
"fiscal_year": "FY 24-25"}}
Q: "Compare Attabira and Bheden blocks for drinking water" → {{"block": "Attabira", \
"block_2": "Bheden", "focus_area": "Drinking water"}}
Q: "How many gram panchayats are there?" → {{}}

Return ONLY a JSON object with these exact keys.
JSON:"""

# Filled by refresh_prompt_enums(). Kept as a module-level string because
# `test_extraction_enums` and any future gate read it directly.
_EXTRACTION_PROMPT: str = ""

_ENUM_SLOTS = (
    "district", "block", "fiscal_year", "focus_area",
    "theme", "scheme", "status", "asset_category",
)


def build_prompt(registry_values, *, warn: bool = True) -> str:
    """The extraction prompt with every enum filled from the live registry.

    `registry_values(entity_type)` is `EntityValidator.registry_values`; passing
    the bound method rather than the validator keeps this module free of a
    circular import and makes the function trivially testable with a dict.
    """
    enums = {}
    for slot in _ENUM_SLOTS:
        try:
            values = list(registry_values(slot) or [])
        except Exception:                                    # pragma: no cover
            values = []
        if not values and warn:
            _log.warning(
                "extraction prompt: registry for %r is EMPTY, so the model "
                "cannot emit any %s — questions about it will silently return "
                "null and stall on a clarification.", slot, slot,
            )
        enums[f"{slot}_enum"] = _registry_enum(
            values, full=slot in _FULLY_ENUMERATED
        )
    # `.replace` rather than `.format`: the template also carries the runtime
    # {query} / {slot_lines} / {intent_context} placeholders, which must survive
    # this pass untouched.
    prompt = _PROMPT_TEMPLATE
    for key, value in enums.items():
        prompt = prompt.replace("{" + key + "}", value)
    return prompt


def refresh_prompt_enums(registry_values) -> str:
    """Rebuild `_EXTRACTION_PROMPT` from a loaded registry. Called once at
    startup, after `EntityValidator` has read the database."""
    global _EXTRACTION_PROMPT
    _EXTRACTION_PROMPT = build_prompt(registry_values)
    return _EXTRACTION_PROMPT


# The import-time build has no database, so every enum is empty. It exists only
# so the module is importable and the rule TEXT can be inspected; `startup` must
# call refresh_prompt_enums() once EntityValidator has read the registries, and
# `test_extraction_enums` builds its own against the real database rather than
# trusting this one. Warnings are suppressed here — an empty enum at import is
# expected, an empty enum at startup is the alarm.
_EXTRACTION_PROMPT = build_prompt(lambda _slot: [], warn=False)


# ── The sentinel (D28.1 / D30.2) ──────────────────────────────────────────────

class ExtractionUnavailable(dict):
    """All-None slots that mean THE EXTRACTOR DID NOT ANSWER.

    WHY THIS IS A TYPE AND NOT A FLAG. The old code ended `except Exception:
    return {s: None for s in slots}` — so a timeout, a 429, an auth failure and a
    truncated response were all indistinguishable from the model reading the
    question and reporting that the user named nothing. The officer then got
    "For which date range?" about a sentence in which they had plainly stated the
    year, and nothing anywhere said an API call had failed. WP-4 §5.1 found this
    sitting next to F1 and it survived F1's fix; D30.2 makes closing it a task in
    its own right.

    IT IS STILL A DICT OF NULLS, deliberately. Every caller reads
    `raw.get(slot)`, and the right *behaviour* on an API failure is unchanged:
    the deterministic `$date_range` fallback should absolutely still run (it is
    exactly the right response to a call that never happened), and a genuinely
    missing slot should still clarify. What changes is that the cause is now
    attributable — in the log, in the meter, and to any caller that cares enough
    to ask `isinstance(raw, ExtractionUnavailable)`.

    `cause` is one of a small closed vocabulary (see `_CAUSE_BY_EXC_NAME` and
    the parse branches below), so the eval can count causes rather than grep
    strings.
    """
    __slots__ = ("cause", "detail")

    def __init__(self, slots, cause: str, detail: str = ""):
        super().__init__({s: None for s in slots})
        self.cause = cause
        self.detail = detail

    def __repr__(self) -> str:                               # pragma: no cover
        return (f"ExtractionUnavailable(cause={self.cause!r}, "
                f"slots={list(self)!r})")


def extraction_failed(raw) -> bool:
    """True when an all-None result was an API/parse failure, not an answer."""
    return isinstance(raw, ExtractionUnavailable)


# Exception class name → cause, walked over the MRO so a provider subclass we
# have never seen still lands on its family. Names rather than imported classes:
# the openai package reorganises these between majors, and an ImportError here
# would take the extractor down to fix a logging label.
_CAUSE_BY_EXC_NAME = {
    "APITimeoutError":       "timeout",
    "APIConnectionError":    "connection",
    "RateLimitError":        "rate_limit",
    "AuthenticationError":   "auth",
    "PermissionDeniedError": "auth",
    "NotFoundError":         "bad_request",
    "BadRequestError":       "bad_request",
    "UnprocessableEntityError": "bad_request",
    "InternalServerError":   "server_error",
    "APIStatusError":        "api_status",
    "APIError":              "api_error",
    "JSONDecodeError":       "bad_json",
}


def _cause_of(exc: BaseException) -> str:
    for klass in type(exc).__mro__:
        cause = _CAUSE_BY_EXC_NAME.get(klass.__name__)
        if cause is not None:
            return cause
    return "unexpected_error"


def _unavailable(slots, cause: str, detail: str, user_query: str
                 ) -> ExtractionUnavailable:
    """Log the failure with its cause, meter it, and hand back the sentinel."""
    _log.warning(
        "entity extraction UNAVAILABLE (%s): %s | slots=%s | query=%r — "
        "these nulls are an API/parse failure, NOT 'the user named nothing'",
        cause, detail, list(slots), (user_query or "")[:120],
    )
    record_extraction(slots, None, cause=cause, query=user_query)
    return ExtractionUnavailable(slots, cause, detail)


def extract_entities(
    user_query: str,
    slots: list[str],
    client: OpenAI,
    *,
    intent: str | None = None,
) -> dict[str, str | None]:
    """
    slots: flat list of entity type names e.g. ["district", "fiscal_year"]
    intent: the classified intent name (provides context for better extraction)
    Returns dict mapping slot_name → raw string value (or None if not found).

    On an API or parse failure the return is an `ExtractionUnavailable` — still
    a dict of nulls, so every caller behaves as before, but carrying the cause.
    """
    if not slots:
        return {}

    slot_lines = "\n".join(f'- "{s}"' for s in slots)
    intent_context = f"The query was classified as intent: {intent}" if intent else ""

    kwargs = dict(
        model=EXTRACTION_MODEL,
        timeout=LLM_TIMEOUT_SECONDS,
        messages=[{
            "role": "user",
            "content": _EXTRACTION_PROMPT.format(
                query=user_query,
                slot_lines=slot_lines,
                intent_context=intent_context,
            )
        }],
        response_format={"type": "json_object"},
    )
    if EXTRACTION_MODEL in REASONING_MODELS:
        kwargs["max_completion_tokens"] = 2000
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    else:
        kwargs["temperature"] = LLM_TEMPERATURE
        kwargs["max_tokens"] = LLM_MAX_TOKENS_EXTRACT

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as exc:
        return _unavailable(slots, _cause_of(exc),
                            f"{type(exc).__name__}: {exc}", user_query)

    # THE CALL AND THE PARSE ARE SEPARATE `try`s on purpose. Wrapping both in one
    # is how a JSON error came to look like a timeout came to look like an empty
    # question; they are three different faults with three different fixes.
    try:
        choice = resp.choices[0]
        content = choice.message.content or ""
        finish = getattr(choice, "finish_reason", None)
    except Exception as exc:
        return _unavailable(slots, "malformed_response",
                            f"{type(exc).__name__}: {exc}", user_query)

    usage = record_call("extraction", EXTRACTION_MODEL, resp, finish_reason=finish)
    reasoning = usage.reasoning_tokens if usage is not None else None

    if not content.strip():
        # A reasoning model that spent its entire completion budget thinking
        # emits `finish_reason="length"` with no content at all — the failure
        # mode D17 exists for, and one no eval would otherwise distinguish from
        # an empty answer.
        cause = "truncated" if finish == "length" else "empty_response"
        return _unavailable(slots, cause, f"finish_reason={finish!r}", user_query)

    try:
        parsed = json.loads(content)
    except Exception as exc:
        cause = "truncated" if finish == "length" else "bad_json"
        return _unavailable(slots, cause,
                            f"{type(exc).__name__}: {exc} | finish_reason={finish!r}",
                            user_query)

    if not isinstance(parsed, dict):
        return _unavailable(slots, "bad_json",
                            f"top-level {type(parsed).__name__}, expected object",
                            user_query)

    result = {s: parsed.get(s) for s in slots}
    record_extraction(slots, result, reasoning_tokens=reasoning, query=user_query)
    return result

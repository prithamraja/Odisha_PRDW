"""
Step 2: Extract entity values from the user query.
Given the chosen template, we know exactly which slots to look for — so the
prompt is small and targeted, making extraction very reliable.

`aadhaar_length` is deliberately absent from the rules: it is a catalog constant,
not something a user says. router._extract_slot_values fills it in at 12 and
never sends it here.
"""
import json
from datetime import date
from openai import OpenAI
from .config import EXTRACTION_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS_EXTRACT, LLM_TIMEOUT_SECONDS, REASONING_MODELS

_VALID_YEARS = ", ".join(str(y) for y in range(2022, date.today().year + 1))

_EXTRACTION_PROMPT = """\
Extract entity values from this Andhra Pradesh agriculture schemes query.
{intent_context}
Query: "{query}"

Extract ONLY these specific values (return null if not present):
{slot_lines}

Rules:
- For district/mandal/village: return the place name in ENGLISH, standard spelling (e.g. కృష్ణా → "Krishna", గుంటూరు → "Guntur"). A mandal is the sub-district; a village sits inside a mandal. Do not put a district name in the mandal slot or vice versa.
- For farmer_name: return the person's name exactly as written in the query, without the word "farmer". Strip an honorific ONLY when it LEADS the name and a non-empty name is left after it: "Sri Ramesh Naidu" → "Ramesh Naidu", "Smt Padma Sri" → "Padma Sri". NEVER drop a trailing token — in this data "Sri", "Devi", "Babu", "Naidu", "Rao" and "Sastry" are SURNAMES, so "Padma Sri" stays "Padma Sri" and "Lakshmi Devi" stays "Lakshmi Devi". When in doubt, keep the whole name. KEEP a trailing "of <place>" that directly follows the name — "Lakshmi Devi of Rambilli" stays "Lakshmi Devi of Rambilli" — because most names on this roster are shared and the village is what says which person is meant. This applies ONLY when "of <place>" follows a person's name; "farmers of Kurnool" names no person, so farmer_name is null there.
- For aadhaar: return the 12-digit number with spaces and dashes stripped. Never invent digits — if the query gives fewer than 12, return what was given.
- For season: return Kharif, Rabi, or Summer
- For crop: return the crop name as written (e.g. "Paddy", "Cotton", "Maize", "Groundnut", "Chilli")
- For scheme: return exactly one of PM-KISAN, Agriculture, Horticulture, Fisheries, Sericulture, MARKFED, RySS. Map the colloquial names: input/seed subsidy → "Agriculture"; micro-irrigation, drip, APMIP → "Horticulture"; procurement, MSP, paddy purchase → "MARKFED"; natural farming, APCNF, Rythu Sadhikara → "RySS". One exception: when "PM-KISAN farmers" is the query's SUBJECT and another scheme is named — "Which PM-KISAN farmers are not in Sericulture?" — the scheme is the OTHER one: return "Sericulture". If the query mentions no scheme from the list, return null.
- For social_category: return SC, ST, BC, or OC
- For gender: return Male, Female, or Other
- For ekyc_status: return Completed, Pending, or Approved
- For beneficiary_status: return Included, Excluded, or Pending
- For crop_status / approval_status: return Approved, Pending, Under Review, or Damaged
- For crop_year: return a 4-digit year ({valid_years})
- For numeric slots (top_n, scheme_count, threshold_qty_per_acre, tolerance_pct): return a BARE NUMBER with no units, no "%" and no words. Example: "top 20 landholders" → top_n=20. Example: "within 10 percent" → tolerance_pct=10. (threshold_hectares is the exception — see its own rule below.)
- For threshold_hectares specifically: COPY the figure WITH ITS UNIT WORD exactly as the user gave it — "less than 2 acres" → "2 acres", "under 50 cents" → "50 cents", "below 1.5 hectares" → "1.5 hectares". Do NOT convert between units; the caller does that. A BARE number means hectares, so "under 1.5" → "1.5". The policy LAND BANDS are fixed hectare figures and are the one case you supply a number the user did not say: "marginal" (below 1 ha) → "1", "small" or "small and marginal" together (below 2 ha) → "2". An explicit figure always wins over a band word.
- For top_n specifically: a BARE SUPERLATIVE with no number attached means one. "Who has the largest landholding?", "Who received the highest input subsidy?", "which farmer got the most" → top_n=1. A number always wins over the superlative: "top 5 largest landholders" → top_n=5. If the query asks to rank or list with no number and no superlative ("Rank farmers by number of schemes"), return null and let the caller apply its default.
- For scheme_2: return the SECOND scheme mentioned in the query. Example: "Which farmers are in both Sericulture and Fisheries?" → scheme="Sericulture", scheme_2="Fisheries".
- For social_category_2: return the SECOND social category mentioned (same logic as scheme_2). Example: "Compare SC and ST beneficiaries" → social_category="SC", social_category_2="ST".

Return ONLY a JSON object with these exact keys.
JSON:"""


def extract_entities(
    user_query: str,
    slots: list[str],
    client: OpenAI,
    *,
    intent: str | None = None,
) -> dict[str, str | None]:
    """
    slots: flat list of entity type names e.g. ["district", "specialty"]
    intent: the classified intent name (provides context for better extraction)
    Returns dict mapping slot_name → raw string value (or None if not found).
    """
    if not slots:
        return {}

    slot_lines = "\n".join(f'- "{s}"' for s in slots)
    intent_context = f"The query was classified as intent: {intent}" if intent else ""

    try:
        kwargs = dict(
            model=EXTRACTION_MODEL,
            timeout=LLM_TIMEOUT_SECONDS,
            messages=[{
                "role": "user",
                "content": _EXTRACTION_PROMPT.format(
                    query=user_query,
                    slot_lines=slot_lines,
                    intent_context=intent_context,
                    valid_years=_VALID_YEARS,
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
        resp = client.chat.completions.create(**kwargs)
        parsed = json.loads(resp.choices[0].message.content.strip())
        return {s: parsed.get(s) for s in slots}
    except Exception:
        return {s: None for s in slots}

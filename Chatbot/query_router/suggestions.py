"""
Next-question suggestion chips (spec 8b) and broad-question elicitation (8e).

v1 generation is hand-authored "moves" per template family (drill to related
measure, switch measure, extend to trend). A chip is only emitted when every
slot of the target template can be filled from the current frame, so every
chip is a fully pre-filled, executable catalog question — the LLM never
freestyles a suggestion.
"""
from .config import MAX_SUGGESTION_CHIPS
from .models import Chip, ContextFrame
from .template_catalog import TEMPLATE_CATALOG

# Hand-authored moves, keyed by the slot that anchors the family. Order is
# priority order; the current template is skipped at build time.
#
# A chip is only emitted when every slot of the target can be filled from the
# current frame, so the mandal moves (which need district AND mandal) only ever
# appear after a mandal-scoped question.
FAMILY_MOVES: dict[str, list[str]] = {
    "district": [
        "G01-D",  # beneficiaries per mandal
        "G10-D",  # input subsidy per mandal
        "G14-D",  # procurement per mandal
        "G02-D",  # eKYC backlog
        "G07-D",  # DBT credited
        "G04-D",  # social category breakdown
        "G39-D",  # mandal scorecard
        "G11-D",  # crop mix
    ],
    "mandal": [
        "G01-M",  # beneficiaries per village
        "G10-M",  # input subsidy per village
        "G02-M",  # eKYC position village by village
        "G07-M",  # DBT credited per village
        "G39-M",  # village scorecard
        "G11-M",  # crop mix
    ],
    "farmer_name": [
        "F09",    # which datasets is this farmer in
        "F12",    # total benefits across schemes
        "F02",    # input subsidy taken
        "F08",    # land records
        "F06",    # MARKFED procurement and payment
        "F01",    # PM-KISAN record
    ],
    "crop": ["V03", "Q098"],
    "scheme": ["S01", "S07", "S03"],
}

# 8e: families offered when only an entity is resolved ("How is Krishna doing?")
# — beneficiary coverage, input subsidy, procurement, eKYC backlog.
ELICITATION_MOVES: dict[str, list[str]] = {
    "district": ["G01-D", "G10-D", "G14-D", "G02-D"],
    "farmer_name": ["F01", "F09", "F12"],
}


def _template_slots(query_id: str) -> set[str] | None:
    template = TEMPLATE_CATALOG.get(query_id)
    if template is None:
        return None
    return {s["name"] for s in template["param_slots"]}


def _chip_for(query_id: str, params: dict[str, str]) -> Chip | None:
    """Pre-filled chip for a target template, or None if it can't be filled."""
    slots = _template_slots(query_id)
    if slots is None or not slots <= set(params):
        return None
    question = TEMPLATE_CATALOG[query_id]["abstract_question"].format(
        **{k: v for k, v in params.items() if k in slots}
    )
    return Chip(label=question, send_text=question)


def suggest_followups(frame: ContextFrame) -> list[Chip]:
    chips: list[Chip] = []
    seen: set[str] = set()
    for slot in frame.bound_params:
        for target in FAMILY_MOVES.get(slot, []):
            if target == frame.template_id or target in seen:
                continue
            chip = _chip_for(target, frame.bound_params)
            if chip is None:
                continue
            seen.add(target)
            chips.append(chip)
            if len(chips) == MAX_SUGGESTION_CHIPS:
                return chips
    return chips


def elicitation_chips(entity_type: str, value: str) -> list[Chip]:
    chips: list[Chip] = []
    for target in ELICITATION_MOVES.get(entity_type, []):
        chip = _chip_for(target, {entity_type: value})
        if chip is not None:
            chips.append(chip)
    return chips

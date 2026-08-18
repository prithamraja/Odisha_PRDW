"""
Next-question suggestion chips (spec 8b) and broad-question elicitation (8e).

Generation is hand-authored "moves" per anchoring slot (drill to a related
measure, switch measure, extend to a trend). A chip is only emitted when every
REQUIRED slot of the target template can be filled from the current frame, so
every chip is a fully pre-filled, executable catalogue question — the LLM never
freestyles a suggestion.

OPTIONAL SLOTS ARE OFFERABLE, NEVER DEMANDED (decision D2). The AP catalogue had
no optional slots, so "can this chip be filled?" was simply `slots <= params`.
Under D2 almost every template carries three optional geography slots, and that
test would refuse to offer a perfectly good state-wide question because the
frame happens not to know a GP. So the requirement is on the REQUIRED slots
only, and an unfilled optional slot binds NULL exactly as it does on the main
path.
"""
from .config import MAX_SUGGESTION_CHIPS
from .models import Chip, ContextFrame
from .template_catalog import TEMPLATE_CATALOG

# Hand-authored moves, keyed by the slot that anchors them. Order is priority
# order; the current template is skipped at build time.
#
# These are the questions a review meeting actually asks NEXT, which is why they
# are authored rather than derived: after "how much did this GP spend?", the
# useful follow-ups are utilisation, what is stalled, and what was planned but
# never started — not the nearest question by embedding distance.
FAMILY_MOVES: dict[str, list[str]] = {
    "district_name": [
        "PLN-004",   # GPDP upload rate across the district
        "EXP-001",   # total actual expenditure
        "EXP-003",   # what share of the plan has been utilised
        "SAN-007",   # administrative approval coverage
        "STS-001",   # activity status counts
        "IMP-005",   # completion rate by theme and focus area
        "TRD-012",   # this district against the state benchmark
    ],
    "block_name": [
        "PLN-003",   # GPDP upload rate across the block
        "EXP-001",   # total actual expenditure
        "EXP-004",   # unspent amount
        "SAN-002",   # activities still awaiting administrative approval
        "STS-001",   # activity status counts
        "ALR-012",   # GPs that recorded no activity at all
    ],
    "gp_name": [
        "PLN-012",   # GPDP status for this panchayat
        "EXP-001",   # total actual expenditure
        "EXP-002",   # how its expenditure has moved across years
        "PLN-050",   # what it planned, by focus area
        "STS-001",   # activity status counts
        "SAN-001",   # activities that received administrative approval
    ],
    "theme": ["BUD-006", "IMP-005", "EXP-014"],
    "focus_area": ["PLN-049", "EXP-010", "EXP-027"],
    "scheme": ["SCH-002", "BUD-002", "EXP-012"],
}

# 8e: what to offer when only an entity is resolved ("How is Khordha doing?").
# The four an officer opens a review with: did the plans arrive, what was spent,
# how much of the plan that is, and what is stuck.
#
# Keyed by ENTITY TYPE, because that is what the caller resolved. The templates
# want a SLOT name, which is a different word — see ELICITATION_SLOT.
ELICITATION_MOVES: dict[str, list[str]] = {
    "district": ["PLN-004", "EXP-001", "EXP-003", "SAN-007"],
    "block":    ["PLN-003", "EXP-001", "EXP-004", "SAN-002"],
    "gp":       ["PLN-012", "EXP-001", "EXP-002", "STS-001"],
}

# entity type -> the workbook bind name that carries it.
ELICITATION_SLOT: dict[str, str] = {
    "district": "district_name",
    "block":    "block_name",
    "gp":       "gp_name",
}


def _required_slots(query_id: str) -> set[str] | None:
    """The slots a target template cannot execute without.

    Optional slots are excluded deliberately: an absent optional geography binds
    NULL and answers state-wide, so requiring the frame to know one would
    suppress the chip for exactly the questions that need no narrowing.
    """
    template = TEMPLATE_CATALOG.get(query_id)
    if template is None:
        return None
    return {s["name"] for s in template["param_slots"] if not s.get("optional")}


def _chip_for(
    query_id: str, params: dict[str, str], anchor: str | None = None,
) -> Chip | None:
    """Pre-filled chip for a target template, or None if it can't be filled.

    `anchor` is the slot the chip is OFFERED FOR — the district the user named,
    the GP the conversation is about. It gets a guarantee the other slots do
    not: if the target's question text does not mention that slot, the value is
    appended rather than quietly dropped.

    That case is common and its failure is silent. Elicitation on a district
    offers EXP-001, whose question reads "What is the total actual expenditure
    incurred by {gp_name} in {date_range}?" — no district placeholder anywhere.
    Formatting it with a district in `params` renders a chip that names no
    district at all, so tapping "what about Khordha?" would answer STATE-WIDE
    and present it as the district's figure. Appending keeps the scope in the
    text, where the router re-extracts it.
    """
    required = _required_slots(query_id)
    if required is None or not required <= set(params):
        return None
    template = TEMPLATE_CATALOG[query_id]
    # Every placeholder in the question must be substitutable, including the
    # optional ones the frame happens to know; a `{gp_name}` left in the text
    # would reach the user as a placeholder and, worse, would not route back.
    known = {s["name"] for s in template["param_slots"]} & set(params)
    try:
        question = template["abstract_question"].format(
            **{k: params[k] for k in known}
        )
    except KeyError:
        # The question names an optional slot this frame cannot fill. Render the
        # readable stand-in instead of dropping the suggestion — "…for a gram
        # panchayat" still routes.
        from .zones import readable_question
        question = readable_question(
            template["abstract_question"], {k: params[k] for k in known}
        )

    if anchor and anchor in params:
        value = str(params[anchor])
        if value and value not in question:
            question = f"{question.rstrip('?. ')} in {value}?"
    return Chip(label=question, send_text=question)


def suggest_followups(frame: ContextFrame) -> list[Chip]:
    chips: list[Chip] = []
    seen: set[str] = set()
    for slot in frame.bound_params:
        for target in FAMILY_MOVES.get(slot, []):
            if target == frame.template_id or target in seen:
                continue
            chip = _chip_for(target, frame.bound_params, anchor=slot)
            if chip is None:
                continue
            seen.add(target)
            chips.append(chip)
            if len(chips) == MAX_SUGGESTION_CHIPS:
                return chips
    return chips


def elicitation_chips(
    entity_type: str, value: str, *, defaults: dict[str, str] | None = None,
) -> list[Chip]:
    """Measure chips for a bare entity — "How is Khordha doing?".

    `defaults` fills the slots the user did not say but every one of these
    questions needs. In practice that is the fiscal year: essentially every
    PR&DW template requires `$date_range`, so without it `_chip_for` would refuse
    every target and a bare place name would get no chips at all — the failure
    mode being a blank elicitation that looks like the bot having nothing to
    offer about a district it knows plenty about. The router passes the most
    recent loaded year, which is what an officer naming no year means.
    """
    slot = ELICITATION_SLOT.get(entity_type, entity_type)
    params = {**(defaults or {}), slot: value}
    chips: list[Chip] = []
    for target in ELICITATION_MOVES.get(entity_type, []):
        chip = _chip_for(target, params, anchor=slot)
        if chip is not None:
            chips.append(chip)
    return chips

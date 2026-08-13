from pydantic import BaseModel
from enum import Enum
from typing import Optional


class RouteTier(str, Enum):
    TIER1_DASHBOARD = "tier1"
    TIER2_TEMPLATE  = "tier2"
    FALLBACK        = "fallback"
    CLARIFY         = "clarify"   # paused before execution; user picks an interpretation


class Chip(BaseModel):
    """A tappable suggestion. send_text is what the tap submits as a message —
    it must always route to something the engine can execute."""
    label:     str
    send_text: str


class Clarification(BaseModel):
    reason:  str          # ambiguous_templates | missing_parameter | unknown_entity | broad_question
    prompt:  str
    options: list[Chip] = []


class EntityCandidate(BaseModel):
    """One of the several registry entries a raw value matched. Districts are
    what the roster disambiguation prompt names people by, so a reply naming a
    district is answerable against this list without another round trip.

    A candidate is sometimes a NAME (several different names fuzzy-match what
    the user typed) and sometimes a PERSON (one name, several Aadhaars hold
    it). `village` and `aadhaar` are set only in the second case and are what
    tell two people apart — district alone does not: two of the four Lakshmi
    Devis are both in Nellore.

    PRIVACY: `aadhaar` is the full number. It exists so a tap can resolve to an
    individual; it must be passed through `mask_aadhaar` before it reaches any
    label, chip or answer.
    """
    name:      str
    districts: list[str] = []
    village:   Optional[str] = None
    aadhaar:   Optional[str] = None


class PendingClarification(BaseModel):
    """The question the system paused on (spec Sec 6: pause BEFORE execution).
    Stored per session so the user's next message can resume it — 'For which
    district?' → 'lucknow' executes the pending template with context intact."""
    query_id:       str
    missing_slot:   str
    slot_type:      str
    filled:         dict[str, str]   # slot -> already-resolved value
    original_query: str
    # Set only when the pause was an ambiguous entity: the candidates the user
    # is choosing between. Without it a reply that answers the disambiguation
    # prompt on its own terms ("Anantapur") fails slot validation and the
    # paused question is lost.
    candidates:     list[EntityCandidate] = []
    # True once this pending has already survived one unusable reply. Bounds the
    # short-reply retry to a single extra turn: a user who genuinely changed
    # subject is never trapped in a clarify they don't want to answer.
    retried:        bool = False


class ExtractedEntity(BaseModel):
    slot_name:      str
    raw_value:      str
    resolved_value: str
    entity_type:    str
    confidence:     str   # exact | alias | fuzzy
    # The Aadhaar of the ONE person a farmer_name resolved to. A name is not a
    # person — 316 of 446 roster names are shared — so templates bind this
    # rather than the name string wherever a param slot declares
    # {"bind": "aadhaar"}. None for every other entity type.
    # PRIVACY: never rendered; query_description shows resolved_value.
    person_aadhaar: Optional[str] = None

class ColumnType(str, Enum):
    DIMENSION       = "dimension"
    TEMPORAL        = "temporal"
    IDENTIFIER      = "identifier"
    ADDITIVE_COUNT  = "additive_count"
    ADDITIVE_VALUE  = "additive_value"
    RATIO           = "ratio"
    SNAPSHOT_STOCK  = "snapshot_stock"
    UNCLASSIFIED    = "unclassified"


class ColumnMetadata(BaseModel):
    name:        str
    column_type: ColumnType


class ActiveFilter(BaseModel):
    dimension: str
    operator:  str = "="
    value:     str


class TimeRange(BaseModel):
    start: str | None
    end:   str | None
    grain: str


class ResultSetReference(BaseModel):
    id:        str
    row_count: int
    columns:   list[ColumnMetadata]


class ContextFrameSnapshot(BaseModel):
    template_id:        str
    template_question:  Optional[str] = None   # canonical question, for breadcrumb rendering
    bound_params:       dict[str, str]
    active_filters:     list[ActiveFilter]
    time_range:         TimeRange
    grouping_dimension: str | None
    result_set:         ResultSetReference


class ContextFrame(ContextFrameSnapshot):
    history_stack: list[ContextFrameSnapshot] = []


class OperationMode(str, Enum):
    CLIENT   = "client"     # computed deterministically on the displayed table
    REQUERY  = "requery"    # recomputed through a catalog template
    REJECTED = "rejected"   # not executed; answer explains why / what to ask instead


class OperationRequest(BaseModel):
    operation:       str
    column:          Optional[str] = None        # target measure column
    label:           Optional[str] = None        # target row (dimension value), e.g. share of "Agra"
    n:               Optional[int] = None        # top_n / bottom_n
    direction:       Optional[str] = None        # asc | desc
    filter_column:   Optional[str] = None
    filter_operator: Optional[str] = None        # = != > >= < <= contains
    filter_value:    Optional[str] = None
    comparator:      Optional[list[str]] = None  # compare: entity values to re-query with
    comparator_slot: Optional[str] = None        # compare: which bound param to swap


class OperationResult(BaseModel):
    operation: str
    mode:      OperationMode
    answer:    str
    column:    Optional[str]        = None
    value:     Optional[float]      = None
    result:    Optional[list[dict]] = None
    result_columns: Optional[list[ColumnMetadata]] = None


class RouteResult(BaseModel):
    tier:              RouteTier
    entities:          Optional[list[ExtractedEntity]] = None
    query_description: Optional[str]                   = None
    fallback_message:  Optional[str]                   = None
    result:            Optional[list[dict]]             = None

    # The catalogue entry's answerability note, carried through to the payload
    # so the answer layer and the frontend can surface it.
    #
    # 251 of the 363 signed-off PR&DW questions are only PARTIALLY answerable —
    # approval tables cover ~17% of activities, scheme_name is 82% null, the
    # 2023-24 reporting step-change poisons cross-year trends, and percentages
    # divide by the GPs actually loaded rather than the official roster. A
    # partial answer served without its caveat is the confidently-wrong failure
    # mode this field exists to prevent, so it travels WITH the rows rather than
    # being looked up separately by whoever renders them.
    #
    # None for entries that carry no note — those behave exactly as before.
    caveat:            Optional[str]                   = None

    raw_query:        str
    normalized_query: str
    total_latency_ms: float

    start_date:          Optional[str] = None   # YYYY-MM-DD
    end_date:            Optional[str] = None   # YYYY-MM-DD
    date_filter_applied: bool          = False

    query_id: Optional[str] = None
    intent:   Optional[str] = None
    context_frame: Optional[ContextFrame] = None
    clarification: Optional[Clarification] = None
    suggestions:   Optional[list[Chip]]    = None
    pending:       Optional[PendingClarification] = None  # set alongside a clarify

    model_config = {"arbitrary_types_allowed": True}


class ClarificationNeeded(Exception):
    """Several registry entries answer to the value the user gave.

    The prose message is what the user reads; `candidates` is the same
    information structured, so callers can build chips and resolve a reply that
    picks a candidate by one of its attributes rather than by name.
    """

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        raw_value: str | None = None,
        candidates: list[EntityCandidate] | None = None,
    ):
        self.entity_type = entity_type
        self.raw_value   = raw_value
        self.candidates  = candidates or []
        super().__init__(message)


class EntityNotFound(Exception):
    def __init__(self, entity_type: str, raw_value: str, suggestions: list[str]):
        self.entity_type = entity_type
        self.raw_value   = raw_value
        self.suggestions = suggestions
        super().__init__(
            f"Could not find a valid '{entity_type}' matching '{raw_value}'. "
            f"Did you mean: {', '.join(suggestions[:3])}?"
            if suggestions else
            f"Could not find a valid '{entity_type}' matching '{raw_value}'."
        )

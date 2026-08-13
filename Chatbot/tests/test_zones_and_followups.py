import unittest

from query_router.config import (
    CLARIFY_SCORE_MARGIN,
    CLARIFY_UPPER_THRESHOLD,
    NO_MATCH_LOWER_THRESHOLD,
)
from query_router.echo import echo_answer
from query_router.followup_classifier import (
    catalog_question_patterns,
    matches_catalog_question,
    parse_decision,
    resolve_subject,
)
from query_router.models import (
    ActiveFilter,
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    ResultSetReference,
    RouteResult,
    RouteTier,
    TimeRange,
)
from query_router.suggestions import (
    ELICITATION_MOVES,
    FAMILY_MOVES,
    elicitation_chips,
    suggest_followups,
)
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.zones import corrected_query_chips, question_chips, zone


def make_frame(
    template_id: str = "G01-D",
    bound_params: dict | None = None,
    grain: str = "day",
) -> ContextFrame:
    params = {"district": "Krishna"} if bound_params is None else bound_params
    return ContextFrame(
        template_id=template_id,
        template_question=(
            "How many PM-KISAN beneficiaries are there in each mandal of {district} district?"
        ),
        bound_params=params,
        active_filters=[
            ActiveFilter(dimension=k, value=v)
            for k, v in params.items() if k not in ("year", "month")
        ],
        time_range=TimeRange(
            start="2025-01-01" if grain == "day" else None,
            end="2025-12-31" if grain == "day" else None,
            grain=grain,
        ),
        grouping_dimension=None,
        result_set=ResultSetReference(
            id="rs_x", row_count=1,
            columns=[ColumnMetadata(name="beneficiaries", column_type=ColumnType.ADDITIVE_COUNT)],
        ),
    )


class ZoneTests(unittest.TestCase):
    def test_below_lower_threshold_is_no_match(self):
        self.assertEqual(zone([]), "no_match")
        self.assertEqual(zone([NO_MATCH_LOWER_THRESHOLD - 0.01, 0.1]), "no_match")

    def test_tight_top_two_below_upper_is_ambiguous(self):
        top = CLARIFY_UPPER_THRESHOLD - 0.05
        self.assertEqual(zone([top, top - CLARIFY_SCORE_MARGIN / 2]), "ambiguous")

    def test_clear_winner_proceeds(self):
        self.assertEqual(zone([CLARIFY_UPPER_THRESHOLD + 0.1, 0.2]), "proceed")
        top = CLARIFY_UPPER_THRESHOLD - 0.05
        self.assertEqual(zone([top, top - CLARIFY_SCORE_MARGIN * 3]), "proceed")

    def test_question_chips_are_readable_and_deduplicated(self):
        chips = question_chips(
            [
                ("G01-D", "How many beneficiaries are there in {district}?", 0.5),
                ("G01-Db", "How many beneficiaries are there in {district}?", 0.4),
                ("V03", "Which farmers grow {crop}?", 0.3),
            ],
            limit=3,
        )
        self.assertEqual(len(chips), 2)
        self.assertNotIn("{", chips[0].label)
        self.assertIn("a district", chips[0].send_text)

    def test_corrected_query_chips_swap_the_entity_in_place(self):
        chips = corrected_query_chips(
            "input subsidy in Krishnaa this year", "Krishnaa", ["Krishna", "Kurnool"], 3
        )
        self.assertEqual(chips[0].send_text, "input subsidy in Krishna this year")
        self.assertEqual(chips[1].label, "Kurnool")


class SuggestionTests(unittest.TestCase):
    def test_every_authored_move_is_an_executable_template(self):
        for moves in list(FAMILY_MOVES.values()) + list(ELICITATION_MOVES.values()):
            for qid in moves:
                self.assertIn(qid, TEMPLATE_CATALOG, f"{qid} is not in the catalog")

    def test_followup_chips_are_prefilled_and_capped(self):
        chips = suggest_followups(make_frame())
        self.assertTrue(0 < len(chips) <= 3)
        for chip in chips:
            self.assertNotIn("{", chip.send_text, "chip must be fully pre-filled")
            self.assertIn("Krishna", chip.send_text)

    def test_current_template_is_not_suggested(self):
        chips = suggest_followups(make_frame("G01-D"))
        current = TEMPLATE_CATALOG["G01-D"]["abstract_question"].format(district="Krishna")
        self.assertNotIn(current, [c.send_text for c in chips])

    def test_unfillable_targets_are_skipped(self):
        # A mandal-scoped family needs district AND mandal — a crop-only frame
        # can fill neither, so nothing half-substituted may escape.
        chips = suggest_followups(make_frame("V03", {"crop": "Paddy"}))
        for chip in chips:
            self.assertNotIn("{", chip.send_text)

    def test_elicitation_chips_for_broad_district_question(self):
        chips = elicitation_chips("district", "Krishna")
        self.assertEqual(len(chips), 4)
        for chip in chips:
            self.assertIn("Krishna", chip.send_text)


class FollowupParseTests(unittest.TestCase):
    def setUp(self):
        self.frame = make_frame()

    def test_entity_swap_is_a_frame_edit(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Lucknow"}, self.frame
        )
        self.assertEqual(decision.kind, "frame_edit")
        self.assertEqual(decision.edit.slot, "district")
        self.assertEqual(decision.edit.value, "Lucknow")

    def test_swap_of_unknown_slot_degrades_to_new_question(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "hospital", "value": "X"}, self.frame
        )
        self.assertEqual(decision.kind, "new_question")

    def test_time_edit_carries_iso_dates(self):
        decision = parse_decision(
            {"kind": "frame_edit", "start_date": "2024-01-01", "end_date": "2024-12-31"},
            self.frame,
        )
        self.assertEqual(decision.kind, "frame_edit")
        self.assertEqual(decision.edit.start_date, "2024-01-01")
        self.assertIsNone(decision.edit.slot)

    def test_operation_kind_projects_to_closed_set(self):
        decision = parse_decision(
            {"kind": "operation", "operation": "sum", "column": "total_cases"}, self.frame
        )
        self.assertEqual(decision.kind, "operation")
        self.assertEqual(decision.operation.operation, "sum")

        bad = parse_decision(
            {"kind": "operation", "operation": "regression"}, self.frame
        )
        self.assertEqual(bad.kind, "new_question")

    def test_unknown_kind_is_new_question(self):
        self.assertEqual(parse_decision({}, self.frame).kind, "new_question")

    def test_noop_entity_swap_degrades_to_new_question(self):
        # "district → Krishna" when district already IS Krishna changes nothing:
        # the LLM latched onto an entity in a complete question. Re-route.
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Krishna"}, self.frame
        )
        self.assertEqual(decision.kind, "new_question")

    def test_noop_swap_check_ignores_case_and_whitespace(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "  krishna "}, self.frame
        )
        self.assertEqual(decision.kind, "new_question")

    def test_noop_swap_with_time_edit_still_applies_the_time_edit(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Krishna",
             "start_date": "2024-01-01", "end_date": "2024-12-31"},
            self.frame,
        )
        self.assertEqual(decision.kind, "frame_edit")
        self.assertIsNone(decision.edit.slot)
        self.assertEqual(decision.edit.start_date, "2024-01-01")


def frame_with_columns(columns: list[ColumnMetadata], row_count: int = 25) -> ContextFrame:
    return ContextFrame(
        template_id="R02",
        template_question="Who received the 25 highest input subsidies?",
        bound_params={"top_n": "25"},
        active_filters=[],
        time_range=TimeRange(start=None, end=None, grain="all_time"),
        grouping_dimension=None,
        result_set=ResultSetReference(id="rs_r02", row_count=row_count, columns=columns),
    )


# The reproduced frame: farmer-level rows. It cannot answer a question about
# districts, however plausibly "highest" reads as a max.
FARMER_SUBSIDY_COLUMNS = [
    ColumnMetadata(name="FARMERNAME", column_type=ColumnType.DIMENSION),
    ColumnMetadata(name="CROPNAME", column_type=ColumnType.DIMENSION),
    ColumnMetadata(name="SEASON", column_type=ColumnType.DIMENSION),
    ColumnMetadata(name="cropyear", column_type=ColumnType.TEMPORAL),
    ColumnMetadata(name="subsidy_amount", column_type=ColumnType.ADDITIVE_VALUE),
]

# The second reproduced frame: procurement by mandal. "farmers" IS a column
# here, which is exactly why the subject guard alone doesn't catch Fix 5.
PROCUREMENT_COLUMNS = [
    ColumnMetadata(name="GEOGRAPHY", column_type=ColumnType.DIMENSION),
    ColumnMetadata(name="farmers", column_type=ColumnType.ADDITIVE_COUNT),
    ColumnMetadata(name="total_quantity", column_type=ColumnType.ADDITIVE_VALUE),
    ColumnMetadata(name="total_value", column_type=ColumnType.ADDITIVE_VALUE),
]


class SubjectResolutionTests(unittest.TestCase):
    """Fix 2 — an operation's subject must be a column of the displayed table."""

    def test_alias_map_reaches_columns_loose_matching_cannot(self):
        self.assertEqual(
            resolve_subject("farmer", FARMER_SUBSIDY_COLUMNS), "FARMERNAME"
        )
        self.assertEqual(resolve_subject("crop", FARMER_SUBSIDY_COLUMNS), "CROPNAME")
        self.assertEqual(
            resolve_subject("mandal", [ColumnMetadata(
                name="sub_district", column_type=ColumnType.DIMENSION)]),
            "sub_district",
        )

    def test_plural_and_case_are_tolerated(self):
        self.assertEqual(resolve_subject("Farmers", FARMER_SUBSIDY_COLUMNS), "FARMERNAME")
        self.assertEqual(resolve_subject("SEASONS", FARMER_SUBSIDY_COLUMNS), "SEASON")

    def test_a_subject_the_table_has_no_column_for_is_unresolvable(self):
        self.assertIsNone(resolve_subject("district", FARMER_SUBSIDY_COLUMNS))
        self.assertIsNone(resolve_subject("", FARMER_SUBSIDY_COLUMNS))


class SubjectGuardTests(unittest.TestCase):
    def setUp(self):
        self.frame = frame_with_columns(FARMER_SUBSIDY_COLUMNS)

    def test_district_max_over_a_farmer_table_is_a_new_question(self):
        """The reproduced bug: max(subsidy_amount) labelled with FARMERNAME
        answered 'which DISTRICT received the highest single input subsidy?'
        with a farmer's name."""
        decision = parse_decision(
            {"kind": "operation", "operation": "max", "subject": "district",
             "column": "subsidy_amount"},
            self.frame,
        )
        self.assertEqual(decision.kind, "new_question")

    def test_a_resolvable_subject_still_runs_as_an_operation(self):
        decision = parse_decision(
            {"kind": "operation", "operation": "max", "subject": "farmer",
             "column": "subsidy_amount"},
            self.frame,
        )
        self.assertEqual(decision.kind, "operation")
        self.assertEqual(decision.operation.operation, "max")

    def test_a_word_for_the_table_itself_is_not_a_subject(self):
        """"only rows above 900" is a filter with no subject. The model fills
        "rows" in anyway often enough that treating it as unresolvable rejected
        a legitimate operation."""
        for meta in ("rows", "records", "Results", "entries"):
            decision = parse_decision(
                {"kind": "operation", "operation": "filter_rows", "subject": meta,
                 "filter_column": "subsidy_amount", "filter_operator": ">",
                 "filter_value": "900"},
                self.frame,
            )
            self.assertEqual(decision.kind, "operation", meta)

    def test_a_null_subject_is_unaffected(self):
        for payload in (
            {"kind": "operation", "operation": "sum"},
            {"kind": "operation", "operation": "sum", "subject": None},
        ):
            self.assertEqual(parse_decision(payload, self.frame).kind, "operation")

    def test_mandal_max_over_a_mandal_dimension_table_still_runs(self):
        mandal_frame = frame_with_columns([
            ColumnMetadata(name="sub_district", column_type=ColumnType.DIMENSION),
            ColumnMetadata(name="total_value", column_type=ColumnType.ADDITIVE_VALUE),
        ])
        decision = parse_decision(
            {"kind": "operation", "operation": "max", "subject": "mandal",
             "column": "total_value"},
            mandal_frame,
        )
        self.assertEqual(decision.kind, "operation")
        self.assertEqual(decision.operation.operation, "max")


class FilterTypeGuardTests(unittest.TestCase):
    """Fix 5 — a filter value has to be a plausible value OF its column."""

    def setUp(self):
        self.frame = frame_with_columns(PROCUREMENT_COLUMNS, row_count=2)

    def test_contains_on_a_count_column_is_a_new_question(self):
        """The reproduced bug: '0 of 2 rows where farmers contains small or
        marginal' — a confident answer to a question the table can't hold."""
        decision = parse_decision(
            {"kind": "operation", "operation": "filter_rows",
             "filter_column": "farmers", "filter_operator": "contains",
             "filter_value": "small or marginal"},
            self.frame,
        )
        self.assertEqual(decision.kind, "new_question")

    def test_numeric_operator_with_a_text_value_is_a_new_question(self):
        decision = parse_decision(
            {"kind": "operation", "operation": "filter_rows",
             "filter_column": "total_quantity", "filter_operator": ">",
             "filter_value": "a lot"},
            self.frame,
        )
        self.assertEqual(decision.kind, "new_question")

    def test_equality_on_a_measure_with_a_text_value_is_a_new_question(self):
        decision = parse_decision(
            {"kind": "operation", "operation": "filter_rows",
             "filter_column": "farmers", "filter_operator": "=",
             "filter_value": "marginal"},
            self.frame,
        )
        self.assertEqual(decision.kind, "new_question")

    def test_legitimate_filters_survive(self):
        for payload in (
            {"filter_column": "total_quantity", "filter_operator": ">",
             "filter_value": "900"},
            {"filter_column": "GEOGRAPHY", "filter_operator": "=",
             "filter_value": "Peddapuram"},
            {"filter_column": "GEOGRAPHY", "filter_operator": "contains",
             "filter_value": "kota"},
            {"filter_column": "farmers", "filter_operator": ">=",
             "filter_value": "10"},
        ):
            decision = parse_decision(
                {"kind": "operation", "operation": "filter_rows", **payload},
                self.frame,
            )
            self.assertEqual(decision.kind, "operation", payload)

    def test_an_unknown_column_is_left_to_the_operations_layer(self):
        decision = parse_decision(
            {"kind": "operation", "operation": "filter_rows",
             "filter_column": "land_band", "filter_operator": "contains",
             "filter_value": "marginal"},
            self.frame,
        )
        self.assertEqual(decision.kind, "operation")


class SlotPlaceholderTests(unittest.TestCase):
    """Fix 4 — an unfilled slot must read as English, not as a slot name."""

    def _chip(self, question, fill=None):
        return question_chips([("X", question, 0.4)], limit=1, fill=fill)[0].send_text

    def test_mapped_slots_read_naturally(self):
        self.assertEqual(
            self._chip("Which schemes is {farmer_name} of {village} enrolled in?"),
            "Which schemes is a farmer of a village enrolled in?",
        )
        self.assertEqual(
            self._chip("Show me everything we hold on {aadhaar}."),
            "Show me everything we hold on an Aadhaar number.",
        )
        self.assertEqual(
            self._chip("Who received the {top_n} highest input subsidies?"),
            "Who received the N highest input subsidies?",
        )

    def test_unmapped_slots_fall_back_to_a_or_an(self):
        self.assertEqual(self._chip("Claims filed in {block}?"), "Claims filed in a block?")
        self.assertEqual(self._chip("Claims filed in {area}?"), "Claims filed in an area?")
        self.assertEqual(
            self._chip("Registrations at {approval_status}?"),
            "Registrations at an approval status?",
        )

    def test_the_unit_swallowing_behaviour_is_retained(self):
        self.assertEqual(
            self._chip("Beneficiaries in each village of {mandal} mandal?"),
            "Beneficiaries in each village of a mandal?",
        )

    def test_a_filled_slot_still_wins(self):
        self.assertEqual(
            self._chip("Which schemes is {farmer_name} enrolled in?",
                       fill={"farmer_name": "Rajesh Sri"}),
            "Which schemes is Rajesh Sri enrolled in?",
        )


class CatalogQuestionGuardTests(unittest.TestCase):
    """Messages that are word-for-word catalog questions bypass the follow-up
    classifier — they can never be frame edits or operations."""

    PATTERNS = catalog_question_patterns([
        "How many hospitals are empanelled in {district}?",
        "What is the monthly case trend in {district}?",
        "What is the claims summary for {district}?",
        "What is the average claim size by specialty?",  # slotless (dashboard)
    ])

    def test_filled_chip_text_matches(self):
        self.assertTrue(matches_catalog_question(
            "How many hospitals are empanelled in Lucknow?", self.PATTERNS
        ))
        self.assertTrue(matches_catalog_question(
            "What is the monthly case trend in Gautam Buddha Nagar?", self.PATTERNS
        ))

    def test_match_ignores_case_punctuation_and_spacing(self):
        self.assertTrue(matches_catalog_question(
            "  how many hospitals are  empanelled in lucknow ", self.PATTERNS
        ))

    def test_slotless_question_matches_exactly(self):
        self.assertTrue(matches_catalog_question(
            "What is the average claim size by specialty?", self.PATTERNS
        ))

    def test_paraphrases_do_not_match(self):
        for message in (
            "how many hospitals do we have in Lucknow?",
            "hospitals empanelled?",
            "total?",
            "what about Lucknow?",
        ):
            self.assertFalse(
                matches_catalog_question(message, self.PATTERNS), message
            )

    def test_every_real_catalog_question_matches_its_own_filled_form(self):
        import re as _re

        questions = [t["abstract_question"] for t in TEMPLATE_CATALOG.values()]
        patterns = catalog_question_patterns(questions)
        for q in questions:
            filled = _re.sub(r"\{\w+?\}", "Lucknow", q)
            self.assertTrue(
                matches_catalog_question(filled, patterns),
                f"catalog question failed to match its own filled form: {filled}",
            )


class EchoTests(unittest.TestCase):
    def test_echo_is_just_the_resolved_question(self):
        frame = make_frame(bound_params={"district": "Guntur", "gender": "Female"})
        result = RouteResult(
            tier=RouteTier.TIER2_TEMPLATE,
            raw_query="q", normalized_query="q", total_latency_ms=1,
            query_id="G05-D",
            query_description="What is the male-female split in Guntur district?",
            result=[{"gender": "Female", "farmers": 4}],
            context_frame=frame,
        )
        # Filters/period are shown in the breadcrumb, not repeated in prose.
        self.assertEqual(
            echo_answer(result), "What is the male-female split in Guntur district?"
        )

    def test_echo_ignores_all_time_grain_too(self):
        frame = make_frame(grain="all_time")
        result = RouteResult(
            tier=RouteTier.TIER2_TEMPLATE,
            raw_query="q", normalized_query="q", total_latency_ms=1,
            query_id="G03-D", query_description="Cultivable area in Krishna district",
            result=[{"hectares": 12.0}],
            context_frame=frame,
        )
        self.assertEqual(echo_answer(result), "Cultivable area in Krishna district")

    def test_empty_result_says_so_instead_of_leaving_it_ambiguous(self):
        """Integrity questions are supposed to return nothing — the answer has to
        say that out loud rather than echo the question over a blank table."""
        result = RouteResult(
            tier=RouteTier.TIER2_TEMPLATE,
            raw_query="q", normalized_query="q", total_latency_ms=1,
            query_id="S03",
            query_description="Which Aadhaar numbers in Sericulture do not exist in PM-KISAN?",
            result=[],
            context_frame=make_frame(),
        )
        answer = echo_answer(result)
        self.assertIn("Which Aadhaar numbers in Sericulture", answer)
        self.assertIn("No records matched", answer)


class ContextPopTests(unittest.TestCase):
    def test_pop_restores_previous_frame_and_rows(self):
        from query_router.context_store import ContextStore

        store = ContextStore()
        first = make_frame("T01", {"district": "Agra"})
        second = make_frame("T02", {"district": "Lucknow"})
        store.set_frame("s", first, rows=[{"total_cases": 1}])
        store.set_frame("s", second, rows=[{"total_cases": 2}])

        popped = store.pop("s")
        self.assertIsNotNone(popped)
        frame, rows = popped
        self.assertEqual(frame.template_id, "T01")
        self.assertEqual(rows, [{"total_cases": 1}])
        self.assertEqual(frame.history_stack, [])

        current = store.get_with_rows("s")
        self.assertEqual(current[0].template_id, "T01")
        self.assertIsNone(store.pop("s"), "no further history to pop")


if __name__ == "__main__":
    unittest.main()

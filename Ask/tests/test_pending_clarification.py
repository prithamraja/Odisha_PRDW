import unittest

from query_router import router
from query_router.context_store import ContextStore
from query_router.models import (
    EntityNotFound,
    ExtractedEntity,
    PendingClarification,
    RouteTier,
)
from query_router.router import _fill_slots_or_clarify, serve_pending_answer
from query_router.zones import question_chips


class StubValidator:
    def __init__(self, known: dict[str, list[str]]):
        self.known = known

    def validate(self, raw, entity_type):
        for value in self.known.get(entity_type, []):
            if value.lower() == str(raw).strip().lower():
                return ExtractedEntity(
                    slot_name=entity_type, raw_value=str(raw), resolved_value=value,
                    entity_type=entity_type, confidence="exact",
                )
        raise EntityNotFound(entity_type, str(raw), self.known.get(entity_type, [])[:3])


class FakeConn:
    def __init__(self, columns, rows):
        self.description = columns
        self._rows = rows
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        return self

    def fetchmany(self, n):
        return self._rows


TEMPLATE_MAP = {
    "TX1": {
        "abstract_question": "How many beneficiaries are there in {district}?",
        "date_filter": None,
        "sql_template": "SELECT district, farmers FROM t WHERE district = ?",
        "param_slots": [{"name": "district", "entity_type": "district", "position": 1}],
    },
    "TX2": {
        "abstract_question": "Beneficiaries in {mandal} of {district}?",
        "date_filter": None,
        "sql_template": "SELECT * FROM t WHERE mandal = ? AND district = ?",
        "param_slots": [
            {"name": "mandal", "entity_type": "mandal", "position": 1},
            {"name": "district", "entity_type": "district", "position": 2},
        ],
    },
    # The real AP mandal shape: the question names only the mandal, but the SQL
    # declares district FIRST. Order must not decide what survives a clarify.
    "TX3": {
        "abstract_question": "Beneficiaries in each village of {mandal} mandal?",
        "date_filter": None,
        "sql_template": "SELECT * FROM t WHERE district = ? AND mandal = ?",
        "param_slots": [
            {"name": "district", "entity_type": "district", "position": 1},
            {"name": "mandal", "entity_type": "mandal", "position": 2},
        ],
    },
}

VALIDATOR = StubValidator({"district": ["Krishna", "Guntur"], "mandal": ["Machilipatnam"]})


class FillSlotsTests(unittest.TestCase):
    def _fill(self, query_id, slot_type, raw):
        return _fill_slots_or_clarify(
            query_id, slot_type, raw, VALIDATOR, "original query", "original query", 0.0
        )

    def test_all_slots_validate(self):
        validated, clarify = self._fill("TX1", {"district": "district"}, {"district": "krishna"})
        self.assertIsNone(clarify)
        self.assertEqual(validated[0].resolved_value, "Krishna")

    def test_missing_slot_pauses_with_pending_state(self):
        _, clarify = self._fill(
            "TX2", {"mandal": "mandal", "district": "district"},
            {"mandal": "Machilipatnam", "district": None},
        )
        self.assertEqual(clarify.tier, RouteTier.CLARIFY)
        self.assertEqual(clarify.clarification.reason, "missing_parameter")
        self.assertEqual(clarify.pending.query_id, "TX2")
        self.assertEqual(clarify.pending.missing_slot, "district")
        self.assertEqual(clarify.pending.filled, {"mandal": "Machilipatnam"},
                         "already-validated slots must survive into pending state")
        self.assertEqual(clarify.pending.original_query, "original query")

    def test_supplied_slot_survives_even_when_declared_after_the_missing_one(self):
        """G01-M shape: district is slot 1 and absent, mandal is slot 2 and given.
        Asking for the district must not discard the mandal, or answering
        'Krishna' just produces a second question for what the user already said."""
        _, clarify = self._fill(
            "TX3", {"district": "district", "mandal": "mandal"},
            {"district": None, "mandal": "Machilipatnam"},
        )
        self.assertEqual(clarify.pending.missing_slot, "district")
        self.assertEqual(clarify.pending.filled, {"mandal": "Machilipatnam"})

    def test_unknown_entity_pauses_with_pending_and_chips(self):
        _, clarify = self._fill("TX1", {"district": "district"}, {"district": "Krishnaa"})
        self.assertEqual(clarify.clarification.reason, "unknown_entity")
        self.assertTrue(clarify.clarification.options)
        self.assertEqual(clarify.pending.missing_slot, "district")


class ServePendingAnswerTests(unittest.TestCase):
    def setUp(self):
        router._result_cache.clear()

    def _pending(self, query_id, missing, filled):
        return PendingClarification(
            query_id=query_id, missing_slot=missing,
            slot_type=missing, filled=filled,
            original_query="beneficiaries in krishna",
        )

    def test_short_answer_resumes_and_executes_the_pending_template(self):
        conn = FakeConn(["district", "farmers"], [("Krishna", 42)])
        result = serve_pending_answer(
            self._pending("TX1", "district", {}), "krishna",
            template_map=TEMPLATE_MAP, cache_conn=conn, validator=VALIDATOR,
            dashboard_results={}, dashboard_questions={},
            start_date=None, end_date=None,
        )
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE)
        self.assertEqual(conn.last_params, ["Krishna"])
        self.assertEqual(result.result, [{"district": "Krishna", "farmers": 42}])
        self.assertEqual(
            result.query_description, "How many beneficiaries are there in Krishna?"
        )
        self.assertEqual(result.raw_query, "beneficiaries in krishna",
                         "the answer resumes the ORIGINAL question")

    def test_answering_the_missing_slot_executes_with_the_carried_slot(self):
        """The other half of the G01-M fix: 'Krishna' completes the question
        instead of triggering 'For which mandal?' for a mandal already named."""
        conn = FakeConn(["village", "farmers"], [("Pedana", 7)])
        result = serve_pending_answer(
            self._pending("TX3", "district", {"mandal": "Machilipatnam"}), "Krishna",
            template_map=TEMPLATE_MAP, cache_conn=conn, validator=VALIDATOR,
            dashboard_results={}, dashboard_questions={},
            start_date=None, end_date=None,
        )
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE)
        self.assertEqual(conn.last_params, ["Krishna", "Machilipatnam"])

    def test_chained_clarification_when_another_slot_is_still_missing(self):
        result = serve_pending_answer(
            self._pending("TX2", "mandal", {}), "Machilipatnam",
            template_map=TEMPLATE_MAP, cache_conn=FakeConn([], []), validator=VALIDATOR,
            dashboard_results={}, dashboard_questions={},
            start_date=None, end_date=None,
        )
        self.assertEqual(result.tier, RouteTier.CLARIFY)
        self.assertEqual(result.pending.missing_slot, "district")
        self.assertEqual(result.pending.filled, {"mandal": "Machilipatnam"})

    def test_unknown_template_raises(self):
        with self.assertRaises(ValueError):
            serve_pending_answer(
                self._pending("NOPE", "district", {}), "krishna",
                template_map=TEMPLATE_MAP, cache_conn=FakeConn([], []), validator=VALIDATOR,
                dashboard_results={}, dashboard_questions={},
                start_date=None, end_date=None,
            )


class PendingStoreTests(unittest.TestCase):
    def test_take_is_one_shot(self):
        store = ContextStore()
        pending = PendingClarification(
            query_id="TX1", missing_slot="district", slot_type="district",
            filled={}, original_query="q",
        )
        store.set_pending("s", pending)
        self.assertEqual(store.take_pending("s").query_id, "TX1")
        self.assertIsNone(store.take_pending("s"), "consumed on first take")

    def test_pending_expires_with_inactivity(self):
        now = [0.0]
        store = ContextStore(inactivity_timeout_seconds=10, clock=lambda: now[0])
        store.set_pending("s", PendingClarification(
            query_id="TX1", missing_slot="district", slot_type="district",
            filled={}, original_query="q",
        ))
        now[0] = 11
        self.assertIsNone(store.take_pending("s"))

    def test_reset_clears_pending(self):
        store = ContextStore()
        store.set_pending("s", PendingClarification(
            query_id="TX1", missing_slot="district", slot_type="district",
            filled={}, original_query="q",
        ))
        store.reset("s")
        self.assertIsNone(store.take_pending("s"))


class FilledChipTests(unittest.TestCase):
    def test_known_entities_are_substituted_into_chips(self):
        chips = question_chips(
            [("G05-D", "What is the male-female split in {district} district?", 0.5)],
            limit=3,
            fill={"district": "Krishna"},
        )
        self.assertEqual(
            chips[0].send_text, "What is the male-female split in Krishna district?"
        )

    def test_unknown_slots_stay_readable(self):
        chips = question_chips(
            [("G01-M", "Beneficiaries in each village of {mandal} mandal?", 0.5)],
            limit=3,
            fill={"district": "Krishna"},
        )
        # 'a mandal mandal' would be the naive substitution — the duplicated
        # unit word is dropped when the slot is unfilled.
        self.assertEqual(chips[0].send_text, "Beneficiaries in each village of a mandal?")


if __name__ == "__main__":
    unittest.main()

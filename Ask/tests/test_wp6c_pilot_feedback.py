"""WP-6c — the two pilot-feedback fixes, pinned.

    T1  a threshold reply is read — the figure, the direction beside it, a
        number written in words through one model call — and asked for in the
        slot's own unit; a reply the other way round is asked about, never bound
    T2  a scheme is never a tied/untied value (added with T2)

No API key and no network: the extractor and the model fallback are stubbed,
and every router path runs against the sample database.
"""
import json
import time
import types
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

_STATE: dict = {}


def _adapter():
    if "adapter" not in _STATE:
        adapter = None
        if _DB_PATH.exists():
            try:
                from db_factory import open_analytical_db
                adapter = open_analytical_db(_DB_PATH)
            except Exception:                                # pragma: no cover
                adapter = None
        _STATE["adapter"] = adapter
    return _STATE["adapter"]


def _validator():
    if "validator" not in _STATE:
        from query_router.entity_validator import EntityValidator
        _STATE["validator"] = EntityValidator(_adapter())
    return _STATE["validator"]


def tearDownModule():
    adapter = _STATE.get("adapter")
    if adapter is not None:
        try:
            adapter.close()
        except Exception:                                    # pragma: no cover
            pass


def _needs_db(test):
    return unittest.skipUnless(_DB_PATH.exists(), "no sample database")(test)


def _fill(qid: str, question: str, raw: dict, *, first_turn: bool = True):
    from query_router import breakdown, router, threshold_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    template = T[qid]
    return router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), raw, _validator(),
        question, "n", time.monotonic(),
        optional=router.optional_slots(template["param_slots"]),
        defaults=router.slot_defaults(template["param_slots"]),
        list_slots=router._list_slots(template["param_slots"]),
        splits=breakdown.slots_the_statement_splits(template),
        numeric=threshold_reply.numeric_meta(template["param_slots"]),
        check_direction=first_turn)


def _resume(pending, value):
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    return router.serve_pending_answer(
        pending, value, template_map=T, cache_conn=_adapter(), validator=_validator(),
        dashboard_results={}, dashboard_questions={}, start_date=None, end_date=None)


class _FigureModel:
    """Stands in for the OpenAI client on the one threshold-reply call."""

    READS = {
        "twenty thousand": {"amount": "20 thousand", "direction": None},
        "two and a half lakh": {"amount": "2.5 lakh", "direction": None},
        "more than twenty thousand": {"amount": "20 thousand", "direction": "above"},
    }

    def __init__(self):
        self.replies: list[str] = []
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        reply = kwargs["messages"][0]["content"].split('"')[1]
        self.replies.append(reply)
        content = json.dumps(self.READS.get(reply, {"amount": None, "direction": None}))
        choice = types.SimpleNamespace(message=types.SimpleNamespace(content=content),
                                       finish_reason="stop")
        return types.SimpleNamespace(choices=[choice], usage=None)


# ── T1 ────────────────────────────────────────────────────────────────────────

# The brief's pins (WP6c_pilot_feedback.md §T1): ALR-003 is the one read by hand.
EXPECTED_THRESHOLD_META = {
    "EXP-033": ("above", "rupees"), "IMP-013": ("above", "rupees"),
    "IMP-009": ("above", "activities"), "IMP-019": ("above", "activities"),
    "IMP-020": ("above", "activities"),
    "ALR-001": ("above", "days"), "ALR-008": ("above", "days"),
    "ALR-003": ("above", "percent"),
    "PLN-045": ("below", "activities"), "PLN-069": ("below", "activities"),
    "PLU-006": ("below", "rupees"), "PLU-009": ("below", "rupees"),
    "ALR-011": ("below", "percent"), "DSS-001": ("below", "percent"),
    "DSS-005": ("below", "percent"),
}

EXP_033_Q = "Which high-value activities have no expenditure in 2024-25?"
PLU_006_Q = "How many low-cost activities are planned theme-wise in 2024-25?"


class T1DerivedSlotMetaTests(unittest.TestCase):

    def test_every_threshold_slot_carries_the_derived_direction_and_unit(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        found = {}
        for qid, entry in T.items():
            for slot in entry["param_slots"]:
                if slot["entity_type"] in ("threshold", "amount_threshold"):
                    found[qid] = (slot.get("direction"), slot.get("unit"))
        self.assertEqual(found, EXPECTED_THRESHOLD_META)

    def test_derive_reads_them_off_the_sql_not_the_file(self):
        import sys
        sys.path.insert(0, str(_BACKEND / "tools"))
        import derive_catalog
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid, expected in EXPECTED_THRESHOLD_META.items():
            name = next(s["name"] for s in T[qid]["param_slots"]
                        if s["entity_type"] in ("threshold", "amount_threshold"))
            self.assertEqual(derive_catalog.threshold_meta(qid, T[qid]["sql_template"], name),
                             expected, qid)
        self.assertEqual(set(derive_catalog.HAND_THRESHOLD_META), {("ALR-003", "threshold")})

    def test_a_threshold_the_sql_does_not_state_breaks_the_contract(self):
        import sys
        sys.path.insert(0, str(_BACKEND / "tools"))
        import derive_catalog
        entry = {"sql_template": "SELECT 1 FROM v WHERE f($threshold)",
                 "param_slots": [{"name": "threshold", "entity_type": "threshold"}]}
        problems = derive_catalog.contract_problems({"X-001": entry})
        self.assertTrue(any("HAND_THRESHOLD_META" in p for p in problems), problems)


class T1ReadReplyTests(unittest.TestCase):

    def test_the_figure_and_the_direction_beside_it(self):
        from query_router.threshold_reply import read_reply
        cases = {
            "above ₹20,000": ("20,000", "above"),
            "activities above 20,000": ("20,000", "above"),
            "more than 20,000 rupees": ("20,000", "above"),
            "the threshold is 20000": ("20000", None),
            "20,000 and above": ("20,000", "above"),
            "under 2 lakhs": ("2 lakhs", "below"),
            "not more than 5 lakh": ("5 lakh", "below"),
            "at least 10 activities": ("10", "above"),
            "within 30 days": ("30", "below"),
            "20k": ("20k", None),
            "above 1 lakh for 2024-25": ("1 lakh", "above"),
        }
        for reply, (figure, direction) in cases.items():
            reading = read_reply(reply)
            self.assertIsNotNone(reading, reply)
            self.assertEqual((reading.figure, reading.direction), (figure, direction), reply)

    def test_a_scheme_preposition_is_not_a_direction(self):
        from query_router.threshold_reply import read_reply
        self.assertIsNone(read_reply("under SFC with a cost of 20000").direction)

    def test_several_figures_or_none_is_no_reading(self):
        from query_router.threshold_reply import read_reply
        for reply in ("between 1 lakh and 5 lakh", "10 or 20", "twenty thousand", "hello"):
            self.assertIsNone(read_reply(reply), reply)

    def test_our_own_chips_are_bare_figures(self):
        from query_router.threshold_reply import is_bare_figure
        for chip in ("₹50,000", "1 lakh", "5 lakh", "25%", "30 days", "10", "2 lakhs"):
            self.assertTrue(is_bare_figure(chip), chip)
        for text in ("above 1 lakh", "Which low-value activities (below ₹2 lakhs)?"):
            self.assertFalse(is_bare_figure(text), text)


@_needs_db
class T1AskTests(unittest.TestCase):

    def test_the_ask_is_in_the_slots_own_unit_with_three_example_chips(self):
        cases = [
            ("EXP-033", EXP_033_Q, {"date_range": "2024-2025"},
             "Above what planned cost? For example ₹50,000 or 1 lakh.",
             ["₹50,000", "1 lakh", "5 lakh"]),
            ("PLU-006", PLU_006_Q, {"date_range": "2024-2025"},
             "Below what planned cost? For example ₹50,000 or 1 lakh.",
             ["₹50,000", "1 lakh", "5 lakh"]),
            ("ALR-011", "Which blocks in Khordha are behind on completion in 2024-25?",
             {"date_range": "2024-2025", "district_name": "Khordha"},
             "Below what percentage?", ["25%", "50%", "75%"]),
            ("ALR-008", "Which activities approved long ago in Barpali are not started?",
             {"block_name": "Barpali"}, "How many days?",
             ["30 days", "60 days", "90 days"]),
            ("IMP-009", "Which focus area has the lowest completion rate in 2024-25?",
             {"date_range": "2024-2025"}, "At least how many activities?", ["5", "10", "20"]),
        ]
        for qid, question, raw, prompt, chips in cases:
            _, clarify = _fill(qid, question, raw)
            self.assertEqual(clarify.clarification.prompt, prompt, qid)
            self.assertEqual([c.send_text for c in clarify.clarification.options], chips, qid)
            self.assertEqual(clarify.pending.missing_slot,
                             "amount_threshold" if qid == "EXP-033" else "threshold")


@_needs_db
class T1ReplyTests(unittest.TestCase):
    """The brief's fixture: bare and wordy forms resume, contradictions ask,
    number words reach the stubbed model, small talk falls through."""

    @classmethod
    def setUpClass(cls):
        _, cls.exp_033 = _fill("EXP-033", EXP_033_Q, {"date_range": "2024-2025"})
        _, cls.plu_006 = _fill("PLU-006", PLU_006_Q, {"date_range": "2024-2025"})

    def _resolve(self, reply, clarify, model=None):
        from query_router.pending_resolver import resolve_pending_reply
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        return resolve_pending_reply(reply, clarify.pending, _validator(),
                                     template_map=T, openai_client=model)

    def _answers_with(self, reply, clarify, expected, model=None):
        from query_router.pending_resolver import RESUME, admits_reply
        self.assertTrue(admits_reply(reply, clarify.pending, from_chip=False), reply)
        resolution = self._resolve(reply, clarify, model)
        self.assertEqual(resolution.kind, RESUME, reply)
        result = _resume(clarify.pending, resolution.value)
        self.assertEqual(result.tier.value, "tier2", reply)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound[clarify.pending.missing_slot], expected, reply)

    def test_the_eight_bare_forms_answer_as_today(self):
        for reply, expected in [("20000", "20000"), ("₹20,000", "20000"),
                                ("Rs. 20,000/-", "20000"), ("2 lakh", "200000"),
                                ("20k", "20000"), ("20,000", "20000"),
                                ("Rs 20000", "20000"), ("₹ 20000", "20000")]:
            self._answers_with(reply, self.exp_033, expected)

    def test_the_five_wordy_forms_answer_with_20000(self):
        for reply in ("above ₹20,000", "activities above 20,000", "more than 20,000 rupees",
                      "the threshold is 20000", "20,000 and above"):
            self._answers_with(reply, self.exp_033, "20000")

    def test_a_long_reply_with_a_figure_is_still_read(self):
        self._answers_with("please show me the activities costing more than 20,000 rupees",
                           self.exp_033, "20000")

    def test_a_reply_the_other_way_round_asks_and_never_serves(self):
        from query_router.pending_resolver import REASK
        for reply, clarify, ours, theirs in [
                ("under 2 lakhs", self.exp_033, "Above ₹2 lakhs", "Below ₹2 lakhs instead"),
                ("above 2 lakh", self.plu_006, "Below ₹2 lakh", "Above ₹2 lakh instead")]:
            resolution = self._resolve(reply, clarify)
            self.assertEqual((resolution.kind, resolution.reason), (REASK, "direction_mismatch"))
            self.assertEqual([c.label for c in resolution.options], [ours, theirs])
            # Chip 1 is a bare figure — it resumes the paused question...
            self.assertIs(resolution.pending, clarify.pending)
            from query_router.pending_resolver import admits_reply
            resume, other = resolution.options
            self.assertTrue(admits_reply(resume.send_text, clarify.pending, from_chip=True))
            # ...chip 2 is a new question, and routes as one.
            self.assertFalse(admits_reply(other.send_text, clarify.pending, from_chip=True))
        self.assertIn("above a planned cost",
                      self._resolve("under 2 lakhs", self.exp_033).prompt)

    def test_chip_1_resumes_with_the_figure(self):
        resolution = self._resolve("under 2 lakhs", self.exp_033)
        self._answers_with(resolution.options[0].send_text, self.exp_033, "200000")

    def test_number_words_reach_the_model_and_bind_what_it_reads(self):
        model = _FigureModel()
        self._answers_with("twenty thousand", self.exp_033, "20000", model)
        self._answers_with("two and a half lakh", self.exp_033, "250000", model)
        self.assertEqual(model.replies, ["twenty thousand", "two and a half lakh"])

    def test_the_models_direction_is_checked_too(self):
        from query_router.pending_resolver import REASK
        resolution = self._resolve("more than twenty thousand", self.plu_006, _FigureModel())
        self.assertEqual((resolution.kind, resolution.reason), (REASK, "direction_mismatch"))

    def test_the_model_is_not_asked_when_a_digit_is_there_or_no_number_is(self):
        model = _FigureModel()
        self._resolve("above ₹20,000", self.exp_033, model)
        self._resolve("show me districts", self.exp_033, model)
        self.assertEqual(model.replies, [])

    def test_a_model_that_reads_nothing_asks_again(self):
        from query_router.pending_resolver import REASK
        resolution = self._resolve("a few thousand", self.exp_033, _FigureModel())
        self.assertEqual(resolution.kind, REASK)
        self.assertIn("Above what planned cost?", resolution.prompt)

    def test_small_talk_falls_through(self):
        from query_router.pending_resolver import FALLTHROUGH
        self.assertEqual(self._resolve("hello there how are you today", self.exp_033).kind,
                         FALLTHROUGH)

    def test_a_short_reply_with_no_number_asks_once_in_the_units_words(self):
        from query_router.pending_resolver import FALLTHROUGH, REASK
        first = self._resolve("show me districts", self.exp_033)
        self.assertEqual(first.kind, REASK)
        self.assertIn("Above what planned cost?", first.prompt)
        self.assertEqual([c.send_text for c in first.options][:3], ["₹50,000", "1 lakh", "5 lakh"])
        from query_router.pending_resolver import resolve_pending_reply
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        second = resolve_pending_reply("show me districts", first.pending, _validator(),
                                       template_map=T)
        self.assertEqual(second.kind, FALLTHROUGH)

    def test_percent_and_days(self):
        from query_router.pending_resolver import REASK
        _, alr_011 = _fill("ALR-011", "Which blocks in Khordha lag on completion in 2024-25?",
                           {"date_range": "2024-2025", "district_name": "Khordha"})
        self._answers_with("below 40 percent", alr_011, "40")
        self.assertEqual(self._resolve("above 60%", alr_011).reason, "direction_mismatch")
        _, alr_008 = _fill("ALR-008", "Which activities approved long ago in Barpali are "
                           "not started?", {"block_name": "Barpali"})
        self._answers_with("more than 60 days", alr_008, "60")
        resolution = self._resolve("within 30 days", alr_008)
        self.assertEqual((resolution.kind, resolution.reason), (REASK, "direction_mismatch"))


@_needs_db
class T1FirstTurnTests(unittest.TestCase):
    """The question itself states the figure the other way round."""

    def test_under_on_an_above_statement_asks_with_one_chip(self):
        question = "Which activities under 2 lakhs have no expenditure in 2024-25?"
        entities, clarify = _fill("EXP-033", question,
                                  {"date_range": "2024-2025", "amount_threshold": "2 lakh"})
        self.assertEqual(entities, [])
        self.assertEqual(clarify.clarification.reason, "direction_mismatch")
        self.assertEqual([c.send_text for c in clarify.clarification.options], ["2 lakhs"])
        result = _resume(clarify.pending, "2 lakhs")
        self.assertEqual(result.tier.value, "tier2")

    def test_the_same_direction_answers(self):
        for qid, question, raw in [
                ("EXP-033", "Which activities above ₹2 lakh have no expenditure in 2024-25?",
                 {"date_range": "2024-2025", "amount_threshold": "2 lakh"}),
                ("PLU-006", "How many activities below 50,000 rupees are planned in 2024-25?",
                 {"date_range": "2024-2025", "threshold": "50,000"})]:
            entities, clarify = _fill(qid, question, raw)
            self.assertIsNone(clarify, qid)

    def test_a_resumed_reply_is_not_checked_against_the_question(self):
        question = "Which activities under 2 lakhs have no expenditure in 2024-25?"
        entities, clarify = _fill("EXP-033", question,
                                  {"date_range": "2024-2025", "amount_threshold": "2 lakh"},
                                  first_turn=False)
        self.assertIsNone(clarify)


if __name__ == "__main__":
    unittest.main()

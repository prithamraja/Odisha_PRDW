"""WP-6c — the two pilot-feedback fixes, pinned.

    T1  a threshold reply is read — the figure, the direction beside it, a
        number written in words through one model call — and asked for in the
        slot's own unit; a reply the other way round is asked about, never bound
    T2  a scheme is never a tied/untied value: re-homed to `$scheme`, a list of
        schemes answered one row per scheme (M5), and a tied/untied value the
        question never says is dropped rather than asked about
    T3  the pilot rows are graded as grade_eval1.py's fourth standing group

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


# ── T2 ────────────────────────────────────────────────────────────────────────

def _extract(qid: str, question: str, extractor_says: dict):
    """`_extract_slot_values` with the extractor stubbed."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T

    def stub(query, slots, client, intent=None):
        return {s: extractor_says.get(s) for s in slots}

    real, router.extract_entities = router.extract_entities, stub
    try:
        return router._extract_slot_values(
            question, router._template_slot_types(T[qid]), object(),
            validator=_validator(), list_slots=router._list_slots(T[qid]["param_slots"]))
    finally:
        router.extract_entities = real


def _answer(qid: str, question: str, extractor_says: dict):
    """(entities, clarify, served result or None), the vector path from extraction on."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    raw = _extract(qid, question, extractor_says)
    entities, clarify = _fill(qid, question, raw)
    if clarify is not None:
        return entities, clarify, None
    result = router._serve_query_id(
        qid, entities, None, user_query=question, normalized=question,
        start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
        template_map=T, dashboard_questions={}, start_date=None, end_date=None)
    return entities, None, result


SPLIT_INTO_TWO = "Split the sanctioned funds into SFC and Own Funds for 2024-25"
Y = {"date_range": "2024-2025"}


@_needs_db
class T2SchemeIsNeverTiedUntiedTests(unittest.TestCase):

    def test_a_scheme_in_tied_untied_moves_to_scheme_and_answers(self):
        question = ("What share of sanctioned funding came from the panchayat's "
                    "own-source income in 2024-25?")
        with self.assertLogs("query_router.router", "INFO") as logs:
            entities, clarify, result = _answer("BUD-005", question,
                                                {**Y, "tied_untied": "Own Funds"})
        self.assertIsNone(clarify)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("scheme"), "Own Funds")
        self.assertNotIn("tied_untied", bound)
        self.assertTrue(any("rehomed tied_untied→scheme" in line for line in logs.output))

    def test_two_schemes_answer_one_row_per_scheme(self):
        for qid in ("BUD-005", "BUD-003", "EXP-008", "FND-001"):
            entities, clarify, result = _answer(qid, SPLIT_INTO_TWO,
                                                {**Y, "tied_untied": ["SFC", "Own Funds"]})
            self.assertIsNone(clarify, qid)
            bound = {e.slot_name: e.resolved_value for e in result.entities}
            self.assertEqual(bound.get("group_by"), "scheme", qid)
            self.assertIn("(broken down by scheme)", result.query_description, qid)
            self.assertTrue(result.result, qid)
            for row in result.result:
                self.assertIn("scheme_name", row, qid)
                self.assertNotIn("tied_untied", row, qid)
                self.assertNotIn("fund_component_name", row, qid)
            names = {row["scheme_name"] for row in result.result}
            self.assertLessEqual(names, {"5TH STATE FINANCE COMMISSION", "Own Funds"}, qid)

    def test_schemes_already_in_scheme_on_bud_002_are_unchanged(self):
        entities, clarify, result = _answer(
            "BUD-002", "How much funding came from SFC and Own Funds in 2024-25?",
            {**Y, "scheme": ["SFC", "Own Funds"]})
        self.assertIsNone(clarify)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertNotIn("group_by", bound)   # BUD-002 already reports per source
        self.assertEqual({row["funding_source"] for row in result.result},
                         {"5TH STATE FINANCE COMMISSION"})

    def test_a_tied_word_in_the_question_still_binds(self):
        entities, clarify, result = _answer(
            "BUD-005", "What percentage of the sanctioned budget is tied in 2024-25?",
            {**Y, "tied_untied": "Tied"})
        self.assertIsNone(clarify)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("tied_untied"), "Tied")

    def test_tied_untied_with_no_such_word_in_the_question_is_dropped_and_logged(self):
        question = "What percentage of the sanctioned budget is from XV FC in 2024-25?"
        with self.assertLogs("query_router.router", "INFO") as logs:
            raw = _extract("BUD-005", question, {**Y, "tied_untied": "Tied"})
        self.assertIsNone(raw["tied_untied"])
        self.assertTrue(any("dropped tied_untied" in line for line in logs.output))

    def test_the_tied_untied_chips_are_never_offered_for_a_scheme(self):
        for says in ({"tied_untied": "Own Funds"}, {"tied_untied": ["SFC", "Own Funds"]},
                     {"tied_untied": "15th FC"}):
            _, clarify, _ = _answer("BUD-005", SPLIT_INTO_TWO, {**Y, **says})
            if clarify is not None:
                labels = {c.label for c in clarify.clarification.options}
                self.assertFalse(labels & {"Tied", "Untied", "Other"}, says)

    def test_gold_1423_still_answers(self):
        question = "Which activities of Andhrua are funded under Own Funds in 2024-25?"
        for qid in ("SCH-002", "BUD-005"):
            entities, clarify, result = _answer(qid, question,
                                                {**Y, "tied_untied": "Own Funds",
                                                 "gp_name": "Andhrua"})
            self.assertIsNone(clarify, qid)
            bound = {e.slot_name: e.resolved_value for e in result.entities}
            self.assertEqual(bound.get("scheme"), "Own Funds", qid)

    def test_gold_1402_and_1522_answer_the_split_with_no_scheme_breakdown(self):
        for qid, question in [
                ("BUD-005", "What percentage of the sanctioned budget is tied and untied "
                            "in 2024-2025?"),
                ("EXP-008", "Tied aur untied fund se 2024-25 me kitna kharcha hua?")]:
            entities, clarify, result = _answer(qid, question,
                                                {**Y, "tied_untied": ["Tied", "Untied"]})
            self.assertIsNone(clarify, qid)
            bound = {e.slot_name: e.resolved_value for e in result.entities}
            self.assertNotIn("group_by", bound, qid)
            self.assertNotIn("tied_untied", bound, qid)
            self.assertEqual({row["tied_untied"] for row in result.result},
                             {"Tied", "Untied", "Other"}, qid)


@_needs_db
class T2MigrationM5Tests(unittest.TestCase):

    def test_scheme_is_the_only_breakdown_the_four_offer(self):
        from query_router import breakdown
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid in ("BUD-003", "BUD-005", "EXP-008", "FND-001"):
            self.assertEqual(breakdown.template_group_values(T[qid]), frozenset({"scheme"}))
            self.assertIn("tied_untied", breakdown.slots_the_statement_splits(T[qid]))

    def test_absent_is_the_signed_off_statement(self):
        oracle = json.loads((_BACKEND / "tests" / "data" / "workbook_test_report.json")
                            .read_text(encoding="utf-8"))
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid in ("BUD-003", "BUD-005", "EXP-008", "FND-001"):
            self.assertIsNone(oracle[qid]["params"]["group_by"])
            params = router.bind_for_template(T[qid], {"date_range": ["2024-2025"]})
            rows = _adapter().execute(T[qid]["sql_template"], params).fetchall()
            self.assertEqual(len(rows), oracle[qid]["rows"], qid)

    def test_any_other_breakdown_keeps_the_tied_untied_table(self):
        entities, clarify, result = _answer(
            "EXP-008", "district-wise tied and untied expenditure 2024-25",
            {**Y, "tied_untied": ["tied", "untied"]})
        self.assertIsNone(clarify)
        self.assertTrue(all("tied_untied" in row for row in result.result))
        self.assertNotIn("broken down", result.query_description)

    def test_scheme_wise_is_read_off_the_question(self):
        entities, clarify, result = _answer("BUD-003", "scheme-wise sanctioned amount 2024-25", Y)
        self.assertIsNone(clarify)
        self.assertTrue(all("scheme_name" in row for row in result.result))
        self.assertIn("(broken down by scheme)", result.query_description)

# ── T3 ────────────────────────────────────────────────────────────────────────

def _ask(prompt, reason="missing_parameter", chips=()):
    return {"tier": "clarify", "clarification": {
        "reason": reason, "prompt": prompt,
        "options": [{"label": c, "send_text": c} for c in chips]}}


class T3PilotGradingTests(unittest.TestCase):
    """The fourth standing group in grade_eval1.py, on synthetic records."""

    def _grade(self, record):
        import sys
        sys.path.insert(0, str(_BACKEND))
        import grade_eval1
        return grade_eval1.grade(record)

    def test_a_threshold_row_answers_with_the_expected_figure(self):
        row = self._grade({
            "n": 1011, "q": "Which high-value activities have no expenditure in 2024-25?",
            "group": "threshold reply", "expect": {"template": "EXP-033", "value": "20000"},
            **_ask("Above what planned cost? For example ₹50,000 or 1 lakh."),
            "turn2": {"q": "above ₹20,000", "tier": "tier2", "query_id": "EXP-033",
                      "entities": [{"slot": "amount_threshold", "value": "20000"}]}})
        self.assertEqual(row["outcome"], "correct")
        self.assertIn("->  above ₹20,000", row["question"])

    def test_a_contradiction_row_must_ask_and_serve_nothing(self):
        record = {
            "n": 1016, "q": "q", "group": "threshold reply",
            "expect": {"reason": "direction_mismatch"},
            **_ask("Above what planned cost? For example ₹50,000 or 1 lakh."),
            "turn2": {"q": "under 2 lakhs", **_ask(
                "This question looks for results above a planned cost.", "direction_mismatch",
                ["Above ₹2 lakhs", "Below ₹2 lakhs instead"])}}
        self.assertEqual(self._grade(record)["outcome"], "correct")
        record["turn2"] = {"q": "under 2 lakhs", "tier": "tier2", "query_id": "EXP-033",
                           "entities": [{"slot": "amount_threshold", "value": "200000"}]}
        self.assertEqual(self._grade(record)["outcome"], "incorrect")

    def test_a_first_turn_that_does_not_ask_fails_the_row(self):
        row = self._grade({
            "n": 1020, "q": "q", "group": "threshold reply",
            "expect": {"template": "EXP-033", "value": "100000"},
            "tier": "tier2", "query_id": "EXP-032",
            "turn2": {"q": "1 lakh", "tier": "tier2", "query_id": "EXP-033"}})
        self.assertEqual(row["outcome"], "incorrect")
        self.assertIn("instead of asking", row["note"])

    def test_a_fund_split_row_needs_a_scheme_column_or_the_scheme_bound(self):
        per_scheme = self._grade({
            "n": 1005, "q": "split the sanctioned funds into SFC and Own Funds",
            "group": "fund split by scheme", "expect": {"per_scheme": True},
            "retrieved": ["BUD-003", "BUD-002", "SAN-013"], "tier": "tier2",
            "query_id": "BUD-003", "n_rows": 1,
            "rows_sample": [{"scheme_name": "5TH STATE FINANCE COMMISSION"}]})
        self.assertEqual(per_scheme["outcome"], "correct")
        self.assertIn("rank 0: BUD-003 (tied-untied)", per_scheme["note"])
        tied_table = self._grade({
            "n": 1005, "q": "q", "group": "fund split by scheme",
            "expect": {"per_scheme": True}, "tier": "tier2", "query_id": "BUD-003",
            "n_rows": 3, "rows_sample": [{"tied_untied": "Tied"}]})
        self.assertEqual(tied_table["outcome"], "incorrect")

    def test_the_tied_untied_chip_set_is_flagged_in_any_turn(self):
        row = self._grade({
            "n": 1006, "q": "q", "group": "fund split by scheme",
            "expect": {"scheme": "Own Funds"},
            **_ask("I couldn't find a tied untied called 'Own Funds'.", "unknown_entity",
                   ["Untied", "Other", "Tied"])})
        self.assertIn("TIED / UNTIED / OTHER CHIPS OFFERED", row["note"])

if __name__ == "__main__":
    unittest.main()

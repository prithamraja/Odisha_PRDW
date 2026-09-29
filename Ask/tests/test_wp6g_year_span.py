"""WP-6g T1c — a missing year is asked for in plain words, with chips.

    "For which date range?" with no chips  ->  "Which year? For example 2024-25."
    with the three latest fiscal years in the data to tap, newest first; the
    earlier year of a two-year comparison is "Compared with which year?", never
    offering the year already bound. A chip tap and a typed reply both resume the
    paused question. (T1's reader and T1b's rule removal are pinned in
    test_date_phrase and test_refusal_precedence.)

No API key and no network: every router path runs against the sample database.
"""
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

_STATE: dict = {}

EXP_008_Q = "Andhrua untied-fund expenditure"
PLN_024_Q = "Barimunda planned activities count"
PLN_039_Q = "Which themes have shown the greatest increase in planned activities?"
LATEST_THREE = ["2025-26", "2024-25", "2023-24"]


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


def _needs_db(cls):
    return unittest.skipUnless(_DB_PATH.exists(), "no sample database")(cls)


def _fill(qid: str, question: str, raw: dict, validator=None):
    from query_router import breakdown, router, threshold_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    template = T[qid]
    return router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), raw, validator or _validator(),
        question, "n", time.monotonic(),
        optional=router.optional_slots(template["param_slots"]),
        defaults=router.slot_defaults(template["param_slots"]),
        list_slots=router._list_slots(template["param_slots"]),
        splits=breakdown.slots_the_statement_splits(template),
        numeric=threshold_reply.numeric_meta(template["param_slots"]),
        check_direction=True)


def _resume(pending, value):
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    return router.serve_pending_answer(
        pending, value, template_map=T, cache_conn=_adapter(), validator=_validator(),
        dashboard_results={}, dashboard_questions={}, start_date=None, end_date=None)


def _resolve(reply, pending):
    from query_router.pending_resolver import resolve_pending_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    return resolve_pending_reply(reply, pending, _validator(), template_map=T)


class YearAskHelperTests(unittest.TestCase):
    """The helper on its own — no database."""

    def test_the_chips_follow_the_registry(self):
        """Never hard-coded: other years in the data give other chips."""
        from query_router import year_ask
        prompt, chips = year_ask.ask(
            "fiscal_year", ["2016-2017", "2017-2018", "2018-2019", "2019-2020"])
        self.assertEqual(prompt, "Which year? For example 2018-19.")
        self.assertEqual([c.label for c in chips], ["2019-20", "2018-19", "2017-18"])
        self.assertEqual([c.send_text for c in chips], ["2019-20", "2018-19", "2017-18"])

    def test_a_short_registry(self):
        from query_router import year_ask
        prompt, chips = year_ask.ask("fiscal_year", ["2024-2025"])
        self.assertEqual(prompt, "Which year? For example 2024-25.")
        self.assertEqual([c.label for c in chips], ["2024-25"])
        self.assertEqual(year_ask.ask("fiscal_year", []), ("Which year?", []))

    def test_the_router_reads_the_validators_registry(self):
        """Through `_fill_slots_or_clarify` with a stubbed registry."""
        from query_router import router
        stub = SimpleNamespace(fiscal_years=lambda: ["2010-2011", "2011-2012",
                                                    "2012-2013", "2013-2014"])
        _, clarify = router._fill_slots_or_clarify(
            "X-001", {"date_range": "fiscal_year"}, {}, stub, "spend?", "n",
            time.monotonic())
        self.assertEqual(clarify.clarification.prompt,
                         "Which year? For example 2012-13.")
        self.assertEqual([c.label for c in clarify.clarification.options],
                         ["2013-14", "2012-13", "2011-12"])
        self.assertEqual(clarify.pending.missing_slot, "date_range")

    def test_a_year_chip_is_recognised_and_nothing_else(self):
        from query_router import year_ask
        for text in ("2024-25", " 2025-26 "):
            self.assertTrue(year_ask.is_year_chip(text), text)
        for text in ("2024-2025", "FY 2024-25", "2024", "How many GPs in 2024-25?",
                     "1 lakh", ""):
            self.assertFalse(year_ask.is_year_chip(text), text)

    def test_the_words_an_officer_reads(self):
        from query_router import year_ask
        from query_router.interpretation import readable_slot
        self.assertEqual(year_ask.slot_words("date_range"), "year")
        self.assertEqual(year_ask.slot_words("date_range_2"), "year")
        self.assertEqual(year_ask.slot_words("block_name"), "block name")
        self.assertEqual(readable_slot("date_range_2"), "year")


@_needs_db
class MissingYearAskTests(unittest.TestCase):

    def test_a_date_range_pending(self):
        _, clarify = _fill("EXP-008", EXP_008_Q,
                           {"gp_name": "Andhrua", "tied_untied": "Untied"})
        c = clarify.clarification
        self.assertEqual(c.reason, "missing_parameter")
        self.assertEqual(c.prompt, "Which year? For example 2024-25.")
        self.assertEqual([o.label for o in c.options], LATEST_THREE)
        self.assertEqual([o.send_text for o in c.options], LATEST_THREE)
        self.assertEqual(clarify.pending.missing_slot, "date_range")
        self.assertEqual(clarify.pending.slot_type, "fiscal_year")
        self.assertNotIn("date range", c.prompt)

    def test_a_date_range_2_pending_leaves_out_the_bound_year(self):
        _, clarify = _fill("PLN-039", PLN_039_Q, {"date_range": "2024-2025"})
        c = clarify.clarification
        self.assertEqual(clarify.pending.missing_slot, "date_range_2")
        self.assertEqual(c.prompt, "Compared with which year? For example 2023-24.")
        self.assertEqual([o.label for o in c.options],
                         ["2025-26", "2023-24", "2022-23"])

    def test_a_date_range_2_pending_with_the_latest_year_bound(self):
        _, clarify = _fill("PLN-039", PLN_039_Q, {"date_range": "2025-2026"})
        self.assertEqual(clarify.clarification.prompt,
                         "Compared with which year? For example 2023-24.")
        self.assertEqual([o.label for o in clarify.clarification.options],
                         ["2024-25", "2023-24", "2022-23"])

    def test_several_years_on_a_one_year_slot_say_year(self):
        from query_router import router
        _, clarify = router._fill_slots_or_clarify(
            "PLN-039", {"date_range": "fiscal_year"},
            {"date_range": ["2023-2024", "2024-2025"]}, _validator(), "q", "n",
            time.monotonic())
        self.assertEqual(clarify.clarification.prompt,
                         "I can answer that for one year at a time. Which did you mean?")

    def test_an_unknown_year_says_year(self):
        from query_router import router
        _, clarify = router._fill_slots_or_clarify(
            "EXP-008", {"date_range": "fiscal_year"}, {"date_range": "1999-2000"},
            _validator(), "q", "n", time.monotonic())
        self.assertIn("I couldn't find a year called '1999-2000'",
                      clarify.clarification.prompt)


@_needs_db
class ResumeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _, cls.exp_008 = _fill("EXP-008", EXP_008_Q,
                               {"gp_name": "Andhrua", "tied_untied": "Untied"})
        _, cls.pln_024 = _fill("PLN-024", PLN_024_Q, {"gp_name": "Barimunda"})

    def _answers(self, reply, clarify, *, from_chip, expected):
        from query_router.pending_resolver import RESUME, admits_reply
        self.assertTrue(admits_reply(reply, clarify.pending, from_chip=from_chip), reply)
        resolution = _resolve(reply, clarify.pending)
        self.assertEqual(resolution.kind, RESUME, reply)
        result = _resume(clarify.pending, resolution.value)
        self.assertEqual(result.tier.value, "tier2", reply)
        self.assertEqual(result.query_id, clarify.pending.query_id)
        entity = next(e for e in result.entities if e.slot_name == "date_range")
        self.assertEqual(entity.values or [entity.resolved_value], expected, reply)
        return result

    def test_a_chip_tap_resumes_and_answers(self):
        chip = self.exp_008.clarification.options[1]
        self.assertEqual(chip.send_text, "2024-25")
        result = self._answers(chip.send_text, self.exp_008, from_chip=True,
                               expected=["2024-2025"])
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("tied_untied"), "Untied")
        self.assertTrue(result.result)

    def test_the_barimunda_chip_tap(self):
        chip = self.pln_024.clarification.options[0]
        self.assertEqual(chip.send_text, "2025-26")
        self._answers(chip.send_text, self.pln_024, from_chip=True,
                      expected=["2025-2026"])

    def test_a_full_question_chip_still_routes_as_one(self):
        from query_router.pending_resolver import admits_reply
        self.assertFalse(admits_reply("How many GPs are there in 2024-25?",
                                      self.exp_008.pending, from_chip=True))

    def test_each_typed_reply_resumes(self):
        for reply, expected in (
            ("2024-25", ["2024-2025"]), ("FY 2024-25", ["2024-2025"]),
            ("2024", ["2024-2025"]), ("last year", ["2024-2025"]),
            ("from 2022-23 to 2024-25", ["2022-2023", "2023-2024", "2024-2025"]),
        ):
            with self.subTest(reply=reply):
                self._answers(reply, self.exp_008, from_chip=False, expected=expected)

    def test_the_re_ask_says_year_with_the_same_chips(self):
        from query_router.pending_resolver import REASK
        resolution = _resolve("no idea", self.exp_008.pending)
        self.assertEqual(resolution.kind, REASK)
        self.assertEqual(
            resolution.prompt,
            f'I still need a year to answer "{EXP_008_Q}". '
            "Which year? For example 2024-25.")
        self.assertEqual([o.label for o in resolution.options][:3], LATEST_THREE)
        self.assertEqual(resolution.options[-1].label, 'Ask "no idea" instead')

    def test_the_scope_reply_says_year(self):
        resolution = _resolve("all years", self.exp_008.pending)
        self.assertNotIn("date range", resolution.prompt or "")


@_needs_db
class ThresholdUnchangedTests(unittest.TestCase):
    """A threshold pending's ask, chips and re-ask are exactly WP-6c's."""

    def test_the_threshold_ask_and_re_ask(self):
        from query_router import threshold_reply
        from query_router.pending_resolver import REASK, admits_reply
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        _, clarify = _fill("EXP-033", "activities above what planned cost?",
                           {"date_range": "2024-2025"})
        meta = threshold_reply.numeric_meta(T["EXP-033"]["param_slots"])
        prompt, chips = threshold_reply.ask(meta[clarify.pending.missing_slot])
        self.assertEqual(clarify.clarification.prompt, prompt)
        self.assertEqual([(c.label, c.send_text) for c in clarify.clarification.options],
                         [(c.label, c.send_text) for c in chips])
        self.assertFalse(admits_reply("2024-25", clarify.pending, from_chip=True))
        resolution = _resolve("what?", clarify.pending)
        self.assertEqual(resolution.kind, REASK)
        self.assertTrue(resolution.prompt.startswith("I still need a number to answer"))


if __name__ == "__main__":
    unittest.main()

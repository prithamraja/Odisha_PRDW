"""The deterministic backstop for `$date_range` (WP-4 finding F1).

THE DEFECT. The entity extractor returns a well-formed `{"date_range": null}`
on roughly a quarter of calls. Measured over 12 IDENTICAL calls on one question:
nine read the year, three did not, every one `finish_reason=stop` with valid
JSON and no exception. The model is not failing to respond — it is answering
"this question names no fiscal year" about a sentence containing '2024-2025'.

WHY IT COST SO MUCH. Under D9 `$date_range` is required on 344 of the 346
templates, so every null became "For which date range?" asked of an officer who
had already said it. That was 30% of WP-4's eval set — 55 of the 73 confirmed
failures, and the single largest cause of the gap to the 96-97% benchmark.

THE FIX IS NOT A NEW PARSER. `date_phrase` is a word-bounded regex pass built in
WP-2 for exactly this mapping, and `EntityValidator._validate_fiscal_year`
already calls it, already consults the loaded years for relative phrases, and
already splits a two-year phrase across `$date_range` / `$date_range_2`. It was
simply unreachable: it only ever received the string the EXTRACTOR produced, so
a null meant it was never consulted. The router now hands it the QUESTION.

Measured against WP-4's own failures: 55 of 62 recovered with the gold value,
zero wrong. The seven it does not recover are correct refusals — five follow-up
fragments whose year lives in the frame rather than the sentence, and two
questions that genuinely name no year.

No API key and no network: `date_phrase` is pure regex and the registry is read
from the sample database.
"""
import unittest
from pathlib import Path

from query_router import router
from query_router.models import RouteTier

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

# PLN-005 — "which GPs have not uploaded their GPDP" — required `$date_range`,
# optional district and block. The shape 62 of WP-4's failures had.
QID = "PLN-005"
STATES_A_YEAR = "Which Gram Panchayats have not yet uploaded their GPDP in 2024-2025?"
STATES_NO_YEAR = "GPDP status?"


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
class FiscalYearFallbackTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from db_factory import open_analytical_db
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG

        cls.adapter = open_analytical_db(_DB_PATH)
        cls.validator = EntityValidator(cls.adapter)
        cls.templates = TEMPLATE_CATALOG

    @classmethod
    def tearDownClass(cls):
        try:
            cls.adapter.close()
        except Exception:                                    # pragma: no cover
            pass

    def _fill(self, query_id, user_query, raw_entities, defaults=None):
        """The real validation path, with the extractor's output handed in."""
        template = self.templates[query_id]
        slot_type = router._template_slot_types(template)
        declared = router.slot_defaults(template["param_slots"])
        return router._fill_slots_or_clarify(
            query_id, slot_type, raw_entities, self.validator,
            user_query, "normalized", 0.0,
            optional=router.optional_slots(template["param_slots"]),
            defaults={**declared, **(defaults or {})},
        )

    # ── The defect, closed ────────────────────────────────────────────────────

    def test_a_null_extraction_is_recovered_from_the_question(self):
        """The exact failure: the extractor returns nothing, the question says
        2024-2025, and the officer used to be asked what year they meant."""
        validated, clarify = self._fill(
            QID, STATES_A_YEAR,
            {"date_range": None, "district_name": None, "block_name": None},
        )
        self.assertIsNone(clarify, "the year is right there in the question")
        self.assertEqual(
            [(e.slot_name, e.resolved_value) for e in validated],
            [("date_range", "2024-2025")],
        )

    def test_the_recovered_value_says_where_it_came_from(self):
        """The raw value would otherwise be the entire question, which is true
        and useless in an echo or a pending state."""
        validated, _ = self._fill(QID, STATES_A_YEAR, {"date_range": None})
        self.assertIn("read from the question", validated[0].raw_value)
        self.assertNotIn("Gram Panchayats", validated[0].raw_value)

    def test_a_question_with_no_year_still_clarifies_normally(self):
        """The fallback must not invent one — and must not leak the question
        into the prompt as if it were a bad value."""
        validated, clarify = self._fill(QID, STATES_NO_YEAR, {"date_range": None})
        self.assertIsNotNone(clarify)
        self.assertEqual(clarify.tier, RouteTier.CLARIFY)
        self.assertEqual(clarify.clarification.reason, "missing_parameter")
        self.assertNotIn("GPDP status?", clarify.clarification.prompt,
                         "the officer's own question must never be quoted back "
                         "as if it were a malformed value")
        self.assertEqual(clarify.pending.missing_slot, "date_range")

    def test_the_extractor_still_wins_when_it_answers(self):
        """A FALLBACK, not a prefill: nothing that works today may change."""
        validated, clarify = self._fill(
            QID, "Which GPs have not uploaded their GPDP in 2023-2024?",
            {"date_range": "2023-2024"},
        )
        self.assertIsNone(clarify)
        self.assertEqual(validated[0].resolved_value, "2023-2024")

    # ── What it inherits from date_phrase for free ────────────────────────────

    def test_a_relative_phrase_resolves_against_the_loaded_data(self):
        """"last year" is not a string date_phrase can read without the loaded
        years — and the validator passes them in, so the fallback gets it too."""
        validated, clarify = self._fill(
            QID, "Which GPs have not uploaded their GPDP last year?",
            {"date_range": None},
        )
        self.assertIsNone(clarify)
        self.assertIn(validated[0].resolved_value, self.validator.fiscal_years())

    def test_odia_numerals_are_read_by_the_fallback_too(self):
        """D18.P5 normalisation sits inside date_phrase, so it applies here
        without a second implementation."""
        validated, clarify = self._fill(
            QID, "ଆର୍ଥିକ ବର୍ଷ ୨୦୨୪-୨୫ରେ କେଉଁ GP GPDP ଅପଲୋଡ କରିନାହାନ୍ତି?",
            {"date_range": None},
        )
        self.assertIsNone(clarify)
        self.assertEqual(validated[0].resolved_value, "2024-2025")

    def _paired(self):
        return [q for q, t in self.templates.items()
                if {"date_range", "date_range_2"}
                <= {s["name"] for s in t["param_slots"]}]

    def test_the_catalogue_binds_date_range_as_the_LATER_year(self):
        """The convention the split rule depends on, read off the SQL.

        All five paired templates bind `$date_range_2` as **year1** and
        `$date_range` as **year2**. If a future template reverses that, this
        fails here rather than silently inverting the sign of a change measure.
        """
        import re
        paired = self._paired()
        self.assertEqual(len(paired), 5, "the paired-template set changed")
        for qid in paired:
            sql = self.templates[qid]["sql_template"]
            for line in sql.splitlines():
                m = re.search(r"\$(date_range(?:_2)?)\b[^\n]*?AS\s+\w*_year(\d)", line)
                if m:
                    slot, ordinal = m.group(1), m.group(2)
                    with self.subTest(qid=qid, alias=f"year{ordinal}"):
                        self.assertEqual(
                            slot, "date_range_2" if ordinal == "1" else "date_range",
                            f"{qid}: year{ordinal} is bound to ${slot} — the "
                            f"pair convention has changed, and _validate_fiscal_year "
                            f"splits a two-year phrase on it",
                        )

    def test_a_two_year_comparison_splits_across_the_paired_slots(self):
        """One string, two slots, and the direction matters.

        `$date_range` is the LATER year (see the test above), because
        PLN-039/PLN-040/TRD-004 compute `$date_range - $date_range_2`. Filling it
        with the earlier year inverts the sign: "which themes showed the greatest
        increase" answers with the greatest DECLINE, silently and with a
        plausible-looking table.

        WP-2's rule had it backwards. It stayed hidden because the extractor
        normally assigns the two slots itself; it only surfaces when ONE string
        carries both years — which is exactly what the fallback hands over.
        """
        paired = self._paired()[0]
        slot_type = router._template_slot_types(self.templates[paired])
        validated, clarify = router._fill_slots_or_clarify(
            paired, slot_type,
            {s: None for s in slot_type}, self.validator,
            "Compare 2023-24 with 2024-25", "normalized", 0.0,
            optional=router.optional_slots(self.templates[paired]["param_slots"]),
            defaults=router.slot_defaults(self.templates[paired]["param_slots"]),
        )
        by_slot = ({e.slot_name: e.resolved_value for e in validated}
                   if clarify is None else dict(clarify.pending.filled))
        self.assertEqual(by_slot.get("date_range_2"), "2023-2024", "year1 = earlier")
        self.assertEqual(by_slot.get("date_range"), "2024-2025", "year2 = later")

    def test_the_money_and_quantity_guards_still_hold(self):
        """date_phrase refuses to read a rupee figure as a year, and the
        fallback must not route around that."""
        for query in ("Which GPs have activities above Rs 2025?",
                      "Which GPs have more than 2024 households?"):
            with self.subTest(query=query):
                _, clarify = self._fill(QID, query, {"date_range": None})
                self.assertIsNotNone(clarify, "a rupee figure is not a year")
                self.assertEqual(clarify.clarification.reason, "missing_parameter")

    # ── The two documented gotchas, pinned (WP-4c T1c) ────────────────────────

    def test_the_question_beats_a_declared_default(self):
        """ORDER MATTERS, and this is the half the ordering tests missed.

        The fallback runs AHEAD of `defaults` deliberately: evidence from the
        officer's own sentence beats any value the system supplies. Reversed, a
        template that ever declares a `$date_range` default would answer about
        the default year while the question named another — the same silent
        wrong answer the optional-slot ordering avoids, arriving through the
        other door. No shipped template declares one today; this is what stops a
        future generator change making it true quietly.
        """
        validated, clarify = self._fill(
            QID, STATES_A_YEAR, {"date_range": None},
            defaults={"date_range": "2020-2021"},
        )
        self.assertIsNone(clarify)
        self.assertEqual(
            {e.slot_name: e.resolved_value for e in validated}["date_range"],
            "2024-2025",
            "the year in the question must beat the declared default",
        )

    def test_the_default_still_applies_when_the_question_names_no_year(self):
        """The other side of the same ordering: the fallback recovers nothing,
        so the declared default is reached exactly as before."""
        validated, clarify = self._fill(
            QID, STATES_NO_YEAR, {"date_range": None},
            defaults={"date_range": "2020-2021"},
        )
        self.assertIsNone(clarify, "a declared default fills the slot")
        self.assertEqual(
            {e.slot_name: e.resolved_value for e in validated}["date_range"],
            "2020-2021",
        )

    def test_the_officers_sentence_is_never_quoted_back_as_a_bad_value(self):
        """`EntityNotFound` is swallowed in `_fiscal_year_from_text` for one
        reason: the raw value handed to the validator is THE WHOLE QUESTION, so
        letting it propagate renders "I couldn't find a date range called
        '<the entire question>'". That is strictly worse than the stall it
        replaces, and it is a wrong-looking answer rather than a missing one.

        Pinned at the function AND at the clarification, because the swallow is
        invisible from either side alone.
        """
        from query_router.entity_validator import EntityNotFound

        with self.assertRaises(EntityNotFound):
            self.validator.validate(STATES_NO_YEAR, "fiscal_year")

        self.assertIsNone(router._fiscal_year_from_text(
            STATES_NO_YEAR, "date_range", "fiscal_year", self.validator))

        _, clarify = self._fill(QID, STATES_NO_YEAR, {"date_range": None})
        self.assertEqual(clarify.clarification.reason, "missing_parameter")
        self.assertNotEqual(clarify.clarification.reason, "unknown_entity")
        self.assertNotIn("couldn't find", clarify.clarification.prompt)

    def test_the_fallback_runs_on_the_UNAVAILABLE_sentinel_too(self):
        """D30.2: "the deterministic fallback may still run on the sentinel (it
        is exactly the right response to an API failure)". A year the officer
        typed is recoverable from the question whether the extractor timed out
        or merely declined to read it."""
        from query_router.entity_extractor import ExtractionUnavailable

        raw = ExtractionUnavailable(["date_range", "district_name", "block_name"],
                                    "timeout", "APITimeoutError")
        validated, clarify = self._fill(QID, STATES_A_YEAR, raw)
        self.assertIsNone(clarify, "an API failure must not cost a stated year")
        self.assertEqual(
            [(e.slot_name, e.resolved_value) for e in validated],
            [("date_range", "2024-2025")],
        )

    # ── Blast radius ──────────────────────────────────────────────────────────

    def test_no_other_slot_type_is_recovered_from_the_text(self):
        """Only the fiscal year has a deterministic reader. A district named in
        the sentence but missed by the extractor is NOT recovered here — there
        is no equivalent regex for it, and pretending otherwise would fuzzy-match
        place names out of free text."""
        validated, _ = self._fill(
            QID, "Which GPs in Khordha have not uploaded their GPDP in 2024-2025?",
            {"date_range": None, "district_name": None, "block_name": None},
        )
        self.assertEqual([e.slot_name for e in validated], ["date_range"])

    def test_an_optional_fiscal_year_is_recovered_rather_than_bound_null(self):
        """ALR-001/ALR-008 carry an OPTIONAL `$date_range` (D13.3). Binding NULL
        there answers across every loaded year about a question that named one —
        a silent wrong answer rather than a visible stall, which is why the
        fallback runs ahead of the optional check."""
        optional_year = [
            q for q, t in self.templates.items()
            for s in t["param_slots"]
            if s["name"] == "date_range" and s.get("optional")
        ]
        self.assertTrue(optional_year, "no optional-$date_range template left")
        qid = optional_year[0]
        slot_type = router._template_slot_types(self.templates[qid])
        # ALR-001 also carries a REQUIRED $threshold (a day count), which is
        # genuinely user-supplied and must keep clarifying (D18.P2). Supply it,
        # so what this test measures is the optional year and nothing else.
        raw = {s: None for s in slot_type}
        for name, etype in slot_type.items():
            if etype in ("threshold", "amount_threshold"):
                raw[name] = "30"
        validated, clarify = router._fill_slots_or_clarify(
            qid, slot_type, raw, self.validator,
            "How many activities are overdue in 2024-2025?", "normalized", 0.0,
            optional=router.optional_slots(self.templates[qid]["param_slots"]),
            defaults=router.slot_defaults(self.templates[qid]["param_slots"]),
        )
        self.assertIsNone(clarify, "the year is in the question and the "
                                   "threshold was supplied")
        self.assertEqual(
            {e.slot_name: e.resolved_value for e in validated}.get("date_range"),
            "2024-2025",
            "an optional $date_range must be RECOVERED, not bound NULL — NULL "
            "answers across every loaded year about a question that named one",
        )


if __name__ == "__main__":
    unittest.main()

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
from query_router.entity_extractor import ExtractionUnavailable
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
        """The real serving path, with the extractor's output handed in.

        WHAT THIS EXERCISES CHANGED IN WP-5. `$date_range` is a PREFILL now, not
        an extractor-empty fallback, so a test that called
        `_fill_slots_or_clarify` directly would be testing a path the router no
        longer takes. This runs `_extract_slot_values` first — reader, then
        extractor for whatever is left — and records WHICH SLOTS WERE ACTUALLY
        ASKED FOR in `self.asked`, which is the property the promotion is worth
        anything for.

        `raw_entities` stands in for the extractor's reply. Its
        `ExtractionUnavailable` type survives the stub, because "the call failed"
        and "the model read nothing" have to stay distinguishable here too.
        """
        template = self.templates[query_id]
        slot_type = router._template_slot_types(template)
        declared = router.slot_defaults(template["param_slots"])

        asked: list[str] = []

        def _stub_extract(query, slots, client, intent=None):
            asked.extend(slots)
            if isinstance(raw_entities, ExtractionUnavailable):
                return ExtractionUnavailable(slots, raw_entities.cause,
                                             raw_entities.detail)
            return {s: raw_entities.get(s) for s in slots}

        real = router.extract_entities
        router.extract_entities = _stub_extract
        try:
            raw = router._extract_slot_values(
                user_query, slot_type, None, validator=self.validator)
        finally:
            router.extract_entities = real
        self.asked = asked

        return router._fill_slots_or_clarify(
            query_id, slot_type, raw, self.validator,
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

    def test_the_prefilled_value_never_carries_the_whole_question(self):
        """The reader validates THE WHOLE QUESTION, so the entity it used to
        return carried the officer's entire sentence as its raw value — true,
        and useless in an echo or a pending state. As a prefill it hands over
        the RESOLVED year instead, so what travels is a year."""
        validated, _ = self._fill(QID, STATES_A_YEAR, {"date_range": None})
        self.assertEqual(validated[0].resolved_value, "2024-2025")
        self.assertNotIn("Gram Panchayats", validated[0].raw_value)
        self.assertIn("2024", validated[0].raw_value)

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

    def test_the_reader_goes_first_and_the_slot_is_never_asked_for(self):
        """D30.4, the promotion itself. A year the reader can read leaves the
        extractor's job entirely — ~160 slots per eval replay, on a model
        measured at a 12% all-None rate."""
        validated, clarify = self._fill(
            QID, "Which GPs have not uploaded their GPDP in 2023-2024?",
            {"date_range": "2023-2024"},
        )
        self.assertIsNone(clarify)
        self.assertEqual(validated[0].resolved_value, "2023-2024")
        self.assertNotIn("date_range", self.asked,
                         "the reader resolved it, so it must not be sent")
        self.assertIn("district_name", self.asked,
                      "the slots with no deterministic reader still go out")

    def test_the_extractor_is_still_the_fallback_for_the_slot(self):
        """READER-FIRST-THEN-EXTRACTOR, not reader-only. The reader's vocabulary
        is narrow — it resolves "last year" and "this year" but not "the year
        before" — so a phrase it cannot read is still sent, and a year the model
        recovers from it is still bound."""
        query = "Which GPs have not uploaded their GPDP the year before last?"
        self.assertIsNone(
            router._fiscal_year_from_text(query, "fiscal_year", self.validator),
            "the premise of this test: the reader cannot read this phrase")

        validated, clarify = self._fill(QID, query, {"date_range": "2023-2024"})
        self.assertIn("date_range", self.asked,
                      "a slot the reader could not fill must still be asked for")
        self.assertIsNone(clarify)
        self.assertEqual(
            {e.slot_name: e.resolved_value for e in validated}["date_range"],
            "2023-2024")

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
        validated, clarify = self._fill(
            paired, "Compare 2023-24 with 2024-25", {})
        by_slot = ({e.slot_name: e.resolved_value for e in validated}
                   if clarify is None else dict(clarify.pending.filled))
        self.assertEqual(by_slot.get("date_range_2"), "2023-2024", "year1 = earlier")
        self.assertEqual(by_slot.get("date_range"), "2024-2025", "year2 = later")
        self.assertNotIn("date_range", self.asked)
        self.assertNotIn("date_range_2", self.asked)

    def test_the_reader_fills_BOTH_paired_slots_or_neither(self):
        """WHY `_order_paired_fiscal_years` COULD BE DELETED (WP-5 T1). The
        re-ordering existed because the extraction prompt orders a pair by
        MENTION and the catalogue orders it CHRONOLOGICALLY, so a question
        naming the earlier year first arrived inverted and PLN-039 answered
        "greatest increase" with the greatest decline.

        The prefill removes the collision at its source, and this is the
        property that makes that true: both paired slots are read from ONE
        string by ONE call, split by entity type, so a mixed pair — one slot
        from the reader, one from the extractor — cannot arise.
        """
        for query, expect in (("Compare 2023-24 with 2024-25", True),
                              ("Compare 2024-25 with 2023-24", True),
                              ("GPDP status?", False)):
            with self.subTest(query=query):
                read = [router._fiscal_year_from_text(query, etype, self.validator)
                        for etype in ("fiscal_year", "fiscal_year_2")]
                self.assertEqual([r is not None for r in read], [expect, expect],
                                 "both slots or neither")
                if expect:
                    self.assertGreater(read[0], read[1],
                                       "$date_range is the LATER year, whichever "
                                       "order the question named them in")

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
            STATES_NO_YEAR, "fiscal_year", self.validator))

        _, clarify = self._fill(QID, STATES_NO_YEAR, {"date_range": None})
        self.assertEqual(clarify.clarification.reason, "missing_parameter")
        self.assertNotEqual(clarify.clarification.reason, "unknown_entity")
        self.assertNotIn("couldn't find", clarify.clarification.prompt)

    def test_the_fallback_runs_on_the_UNAVAILABLE_sentinel_too(self):
        """D30.2: "the deterministic fallback may still run on the sentinel (it
        is exactly the right response to an API failure)". A year the officer
        typed is recoverable from the question whether the extractor timed out
        or merely declined to read it."""
        raw = ExtractionUnavailable(["date_range", "district_name", "block_name"],
                                    "timeout", "APITimeoutError")
        validated, clarify = self._fill(QID, STATES_A_YEAR, raw)
        self.assertIsNone(clarify, "an API failure must not cost a stated year")
        self.assertEqual(
            [(e.slot_name, e.resolved_value) for e in validated],
            [("date_range", "2024-2025")],
        )

    # ── The disagreement log D30.4 is decided on ───────────────────────────────

    def _disagreements(self, query, slot, entity_type, extracted):
        with self.assertLogs("query_router.router", level="INFO") as cm:
            # A guaranteed record, so assertLogs never fails for want of output.
            router._log.info("probe")
            router._log_fiscal_year_disagreement(
                query, slot, entity_type, extracted, self.validator)
        return [line for line in cm.output if "disagreement" in line]

    def test_an_abbreviated_year_is_not_a_disagreement(self):
        """THE BUG THIS PINS. The check compared the extractor's RAW SURFACE FORM
        against a RESOLVED value, so '2023-24' vs '2023-2024' logged as a
        disagreement — and `date_phrase` exists precisely to map one onto the
        other (D9). Every officer writing a year the normal way produced a false
        positive, which would have made D30.4's "zero disagreements → promote to
        prefill" test unpassable and argued the opposite of the truth."""
        for extracted in ("2023-24", "FY 2023-24", "2023-2024"):
            with self.subTest(extracted=extracted):
                self.assertEqual(
                    self._disagreements(
                        "How many activities were planned in 2023-24?",
                        "date_range", "fiscal_year", extracted),
                    [], f"{extracted!r} and '2023-2024' are the same year")

    def test_the_pair_mirror_matches_the_validator(self):
        """The old mirror gave `_2` the LATER year, the opposite of what
        `_validate_fiscal_year` does — so a comparison question logged both slots
        as disagreeing with themselves."""
        query = "Compare 2023-24 with 2024-25"
        self.assertEqual(
            self._disagreements(query, "date_range", "fiscal_year", "2024-25"), [])
        self.assertEqual(
            self._disagreements(query, "date_range_2", "fiscal_year_2", "2023-24"), [])

    def test_a_real_disagreement_is_still_logged(self):
        """The log has to keep working, or it proves nothing by being empty."""
        found = self._disagreements(
            "How many activities were planned in 2023-24?",
            "date_range", "fiscal_year", "2024-25")
        self.assertEqual(len(found), 1)
        self.assertIn("2024-2025", found[0])
        self.assertIn("2023-2024", found[0])

    def test_an_unresolvable_extraction_is_logged_loudly(self):
        found = self._disagreements(
            "How many activities were planned in 2023-24?",
            "date_range", "fiscal_year", "the year before last")
        self.assertEqual(len(found), 1)
        self.assertIn("UNRESOLVABLE", found[0])

    def test_a_question_with_no_year_logs_nothing(self):
        self.assertEqual(
            self._disagreements("GPDP status?", "date_range", "fiscal_year",
                                "2024-25"),
            [], "there is nothing in the text to disagree with")

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
        raw = {name: "30" for name, etype in slot_type.items()
               if etype in ("threshold", "amount_threshold")}
        validated, clarify = self._fill(
            qid, "How many activities are overdue in 2024-2025?", raw)
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

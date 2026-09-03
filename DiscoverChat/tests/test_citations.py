# -*- coding: utf-8 -*-
"""WP-D7 — citations, provenance and the consolidating writer. No model calls.

    python -m unittest DiscoverChat.tests.test_citations

Everything here is deterministic. The three things WP-D7 changed that a model
decides — which nano routes a rule-miss to, what the writer actually writes, and
the audit's drift rate — are measured by the experiment scripts, with repeats,
because a number that moves does not belong in a suite that must stay green.

THE FIXTURES ARE SYNTHETIC ON PURPOSE. A seeded-violation test needs figures it
can violate by hand, and a corpus record's figures change when the corpus is
rebuilt — which would make these tests fail for a reason that has nothing to do
with what they test. The tests that must touch the real corpus say so and use it.
"""
import unittest

from DiscoverChat import config  # noqa: F401  — first, so Insights/src is on sys.path
from DiscoverChat import (checks, classifier, context_brief, render,
                          verifier, writer)
from DiscoverChat.corpus import Finding


def _finding(finding_id, sentence, **extra):
    data = {"finding_id": finding_id, "sentence": sentence, "view": "view1",
            "view_title": "Activity Lifecycle", "score": 0.4, "in_feed": False,
            "view_rank": None, "feed_rank": None, "measures": [],
            "geography": {}, "named_members": [],
            "subspace_phrase": "the whole view"}
    data.update(extra)
    return Finding(0, data)


FINDINGS = [
    _finding("1-00235", "Across most measure values (19/22), Code 101 accounts "
                        "for 51.96 percent of total_cost."),
    _finding("1-00987", "Across 12 blocks, fund_untied_total reaches Rs 1.24 "
                        "crore in Boipariguda.", named_members=["Boipariguda"]),
    _finding("d1-00042", "Within the whole view, activities planned totals "
                         "12,704 activities across 20 Gram Panchayats.",
             record_type="decomposition"),
]
RUN_DATE = "as of 2026-08-17"
CLEAN = ("Code 101 accounts for 51.96 percent of total cost across 19 of 22 "
         "measures [1-00235]. Untied grant planned reaches Rs 1.24 crore in "
         "Boipariguda across 12 blocks [1-00987]. Activities planned total "
         "12,704 across 20 Gram Panchayats [d1-00042].")


def _check(prose, findings=None):
    return checks.check_citations(prose, findings or FINDINGS,
                                  run_date=RUN_DATE)


class CitationCheckTests(unittest.TestCase):
    def test_clean_prose_passes_every_step(self):
        result = _check(CLEAN)
        self.assertTrue(result["all_pass"],
                        checks.citation_failure_reason(result))

    def test_an_unknown_id_fails(self):
        result = _check(CLEAN.replace("[1-00235]", "[1-99999]"))
        self.assertFalse(result["1_ids_known"]["pass"])
        self.assertIn("1-99999", result["1_ids_known"]["unknown"])

    def test_an_invented_tag_that_is_not_an_id_fails(self):
        """`[Finding 3]` must fail rather than be ignored. A tag parser tight
        enough to only see real ids would skip this one silently, and a silent
        skip is the failure the whole check exists to prevent."""
        result = _check(CLEAN.replace("[1-00235]", "[Finding 3]"))
        self.assertFalse(result["1_ids_known"]["pass"])

    def test_a_derived_figure_fails(self):
        """PM addition 2, enforced rather than requested: a percentage the
        writer computed appears in no finding's stored sentence."""
        result = _check(CLEAN + " Together these cover 63.2 percent [1-00235].")
        self.assertFalse(result["2_numerals_cited"]["pass"])
        self.assertEqual([u["numeral"] for u in
                          result["2_numerals_cited"]["unsupported"]], ["63.2"])

    def test_a_figure_cited_to_the_wrong_finding_fails(self):
        """The case check (a) cannot see. 51.96 IS in the supplied material, so
        the nothing-invented check passes it; it is not in 1-00987, which is
        what this sentence says it came from."""
        result = _check("Untied grant reaches Rs 51.96 crore [1-00987]. " + CLEAN)
        self.assertFalse(result["2_numerals_cited"]["pass"])

    def test_an_uncited_numeral_fails(self):
        result = _check(CLEAN + " There were 7 exceptions.")
        self.assertFalse(result["2_numerals_cited"]["pass"])
        self.assertEqual(result["2_numerals_cited"]["unsupported"][0]["cited"], [])

    def test_a_dropped_finding_fails(self):
        """The judge already picked the smallest sufficient set, so a finding
        the writer left out is loss, not concision."""
        result = _check("Code 101 accounts for 51.96 percent across 19 of 22 "
                        "[1-00235]. Untied grant reaches Rs 1.24 crore in 12 "
                        "blocks [1-00987].")
        self.assertFalse(result["4_all_findings_cited"]["pass"])
        self.assertEqual(result["4_all_findings_cited"]["dropped"], ["d1-00042"])

    def test_a_causal_claim_fails(self):
        result = _check(CLEAN + " The shortfall was caused by late sanctions "
                                "[1-00235].")
        self.assertFalse(result["3_causal"]["pass"])

    def test_every_failure_gives_a_reason_to_feed_back(self):
        for prose in (CLEAN.replace("[1-00235]", "[1-99999]"),
                      CLEAN + " Together these cover 63.2 percent [1-00235].",
                      CLEAN + " There were 7 exceptions."):
            self.assertTrue(checks.citation_failure_reason(_check(prose)).strip())

    def test_the_run_date_is_exempt_and_nothing_else_is(self):
        """A date is not a finding and can be cited to none; a figure is."""
        self.assertTrue(_check("The analysis was run as of 2026-08-17. "
                               + CLEAN)["all_pass"])
        self.assertFalse(_check(CLEAN + " Another 4,412 records were "
                                        "reviewed.")["all_pass"])

    def test_a_trailing_tag_cites_the_sentence_it_follows(self):
        """The one latitude in the check, and it is one-directional."""
        trailing = ("Code 101 accounts for 51.96 percent across 19 of 22 "
                    "measures. [1-00235] Untied grant reaches Rs 1.24 crore in "
                    "12 blocks. [1-00987] Activities planned total 12,704 "
                    "across 20 Gram Panchayats. [d1-00042]")
        self.assertTrue(_check(trailing)["all_pass"])

    def test_a_tag_never_travels_forwards(self):
        """A tag at the head of the FIRST sentence has no sentence to attach
        to, so the figures after it are uncited and must fail."""
        self.assertFalse(_check("[1-00235] There were 63.2 percent of "
                                "records.")["all_pass"])

    def test_digits_inside_a_tag_are_not_treated_as_figures(self):
        """`[1-00235]` carries digits. Counting them would let a writer smuggle
        any number into an answer by shaping it like an id."""
        bindings = checks.bind_numerals(CLEAN, FINDINGS, run_date=RUN_DATE)
        self.assertNotIn("00235", [b["token"] for b in bindings])
        self.assertNotIn("00042", [b["token"] for b in bindings])


class TagStrippingTests(unittest.TestCase):
    def test_no_tag_survives_into_the_display_text(self):
        stripped = checks.strip_tags(CLEAN)
        self.assertNotIn("[", stripped)
        self.assertNotIn("]", stripped)
        for finding in FINDINGS:
            self.assertNotIn(finding.id, stripped)

    def test_stripping_removes_no_content(self):
        stripped = checks.strip_tags(CLEAN)
        for kept in ("51.96 percent", "Rs 1.24 crore", "12,704", "Boipariguda"):
            self.assertIn(kept, stripped)

    def test_punctuation_survives_the_strip(self):
        self.assertTrue(checks.strip_tags("A figure of 5 [1-00235].")
                        .endswith("."))


class HoverRenderTests(unittest.TestCase):
    def test_every_bound_numeral_is_wrapped(self):
        bindings = checks.bind_numerals(CLEAN, FINDINGS, run_date=RUN_DATE)
        bound = [b for b in bindings if b["matched"]]
        self.assertTrue(bound)
        html = render.to_html(CLEAN, FINDINGS, run_date=RUN_DATE)
        for binding in bound:
            self.assertIn(f'data-finding-id="{binding["matched"]}"', html)

    def test_the_hover_carries_the_stored_sentence_scope_and_stamp(self):
        html = render.to_html(CLEAN, FINDINGS, run_date=RUN_DATE)
        for finding in FINDINGS:
            self.assertIn(finding.display_sentence()[:40], html)
        self.assertIn("the whole view", html)
        self.assertIn(RUN_DATE, html)

    def test_every_citation_links_to_its_record(self):
        html = render.to_html(CLEAN, FINDINGS, run_date=RUN_DATE)
        for finding in FINDINGS:
            self.assertIn(config.record_url(finding.id), html)

    def test_the_renderer_uses_the_checks_binding_not_its_own(self):
        """A renderer that matched numbers its own way could show a hover the
        check never approved. This pins the two together: the figure 51.96
        belongs to 1-00235, so the span whose DISPLAYED content is 51.96 must
        declare 1-00235 and no span may show 51.96 under 1-00987.

        Asserted with a regex against the span's own shape rather than by
        slicing a window out of the string: attribute values are HTML-escaped so
        the only literal '>' in an opening tag is the tag-closer, which makes
        `data-finding-id="X"[^>]*>51.96<` an exact 'this id wraps this visible
        number' test — and it does not break when the markup around it changes."""
        import re
        html = render.to_html(CLEAN, FINDINGS, run_date=RUN_DATE)
        self.assertRegex(html, r'data-finding-id="1-00235"[^>]*>51\.96<')
        self.assertNotRegex(html, r'data-finding-id="1-00987"[^>]*>51\.96<')

    def test_a_non_numeric_claim_is_still_hoverable(self):
        prose = "Spending is broadly even across the sample [d1-00042]."
        html = render.to_html(prose, FINDINGS, run_date=RUN_DATE)
        self.assertIn('data-finding-id="d1-00042"', html)
        self.assertIn("Spending is broadly even", html)

    def test_the_rendered_output_is_ascii_safe(self):
        """The gate and the tests print fragments to a cp1252 console."""
        render.to_page(CLEAN, FINDINGS, question="Is spending on track?",
                       run_date=RUN_DATE).encode("ascii", "strict")


class WriterPromptTests(unittest.TestCase):
    def test_the_prompt_is_the_operators_text(self):
        prompt = context_brief.CONSOLIDATING_WRITER_PROMPT
        for line in ("Turn the analytical findings below into clear, concise "
                     "prose",
                     "consolidate them into a small number of underlying "
                     "patterns",
                     "Do not make causal claims ever",
                     "tag the finding it comes from with its id in square "
                     "brackets",
                     "Do not compute new numbers",
                     "Return only the finished prose."):
            self.assertIn(line, prompt)

    def test_the_bracket_scaffolding_is_not_in_the_prompt(self):
        self.assertNotIn("PM addition",
                         context_brief.CONSOLIDATING_WRITER_PROMPT)

    def test_the_context_brief_is_background_only(self):
        """WRITER_TASK is D5's connective-prose job and tells the writer not to
        restate a finding — the exact instruction D7.3 reverses."""
        brief = context_brief.for_consolidating_writer()
        self.assertEqual(brief, context_brief.BACKGROUND)
        self.assertNotIn(context_brief.WRITER_TASK, brief)

    def test_no_ranking_metadata_reaches_the_writer(self):
        """Belt is the prompt line telling the writer to ignore it; braces are
        that it is never sent."""
        built = writer.build_consolidation_prompt(
            "Is spending on track?", FINDINGS, run_date=RUN_DATE)
        payload = built.replace(context_brief.CONSOLIDATING_WRITER_PROMPT, "")
        for banned in ("ranked", "score", "Standing in the analysis",
                       "not in the ranked shortlist"):
            self.assertNotIn(banned, payload)

    def test_each_finding_arrives_as_id_then_sentence(self):
        built = writer.build_consolidation_prompt("q", FINDINGS,
                                                  run_date=RUN_DATE)
        for finding in FINDINGS:
            self.assertIn(f"[{finding.id}] {finding.display_sentence()}", built)

    def test_a_decomposition_carries_its_scope_note(self):
        built = writer.build_consolidation_prompt("q", FINDINGS,
                                                  run_date=RUN_DATE)
        self.assertIn("the parts add up to the whole", built)

    def test_the_run_date_is_supplied_so_the_prose_can_say_as_of(self):
        self.assertIn(RUN_DATE, writer.build_consolidation_prompt(
            "q", FINDINGS, run_date=RUN_DATE))

    def test_a_rejection_reason_is_fed_back_on_the_second_attempt(self):
        built = writer.build_consolidation_prompt(
            "q", FINDINGS, run_date=RUN_DATE, reason="It invented 63.2.")
        self.assertIn("A previous attempt at this answer was rejected", built)
        self.assertIn("It invented 63.2.", built)


class VerifierPlacementTests(unittest.TestCase):
    def test_inline_verification_is_off_by_default(self):
        self.assertFalse(config.INLINE_VERIFY)

    def test_the_verifier_module_is_still_here_for_the_audit(self):
        """A config default, not a deletion — the audit runs the same module."""
        self.assertTrue(hasattr(verifier, "verify"))
        self.assertTrue(hasattr(verifier, "build_audit_prompt"))

    def test_the_audit_prompt_describes_a_consolidated_answer(self):
        prompt = verifier.build_audit_prompt(
            CLEAN, "sources", "context", consolidated=True)
        self.assertIn("Restating a finding is the job", prompt)
        self.assertNotIn("this is the connective prose only", prompt)

    def test_the_connective_prompt_is_unchanged_for_old_prose(self):
        prompt = verifier.build_audit_prompt(
            "text", "sources", "context", consolidated=False)
        self.assertIn("this is the connective prose only", prompt)


class ClassifierSignalTests(unittest.TestCase):
    def test_a_null_classification_is_named_not_swallowed(self):
        """Ask's F1: a small model returning nulls looked exactly like a model
        with no opinion, for a whole work package."""
        empty = classifier.Routing(classifier.RETRIEVE, "default", "x",
                                   model_empty=True)
        unparseable = classifier.Routing(classifier.RETRIEVE, "default", "x",
                                         model_unparseable=True)
        self.assertTrue(empty.model_null)
        self.assertTrue(unparseable.model_null)
        self.assertTrue(empty.as_dict()["model_empty"])
        self.assertTrue(unparseable.as_dict()["model_unparseable"])

    def test_a_rule_routed_turn_never_claims_a_model_null(self):
        routing = classifier.rule_route("Why is spending low in Chikilli?")
        self.assertFalse(routing.model_null)

    def test_rules_still_run_first(self):
        """D7.0 changed the model, not the routing. `allow_rules=False` exists
        only so the gate can exercise the model at all."""
        for question, expected in (
                ("Why is spending low in Chikilli?", classifier.WHY),
                ("How much was spent in Khordha?", classifier.LOOKUP),
                ("Where does the gap sit?", classifier.DECOMPOSE)):
            self.assertEqual(
                classifier.classify(question, allow_model=False).move, expected)


class RecordEndpointTests(unittest.TestCase):
    """D7.2, against the real corpus — the endpoint's whole job is to serve what
    the corpus actually holds, so a synthetic fixture would test nothing."""

    @classmethod
    def setUpClass(cls):
        from DiscoverChat import main as main_mod
        from DiscoverChat.retrieval import Retriever
        cls.main = main_mod
        cls.retriever = Retriever()
        main_mod.STATE["retriever"] = cls.retriever
        main_mod.STATE["stamp"] = cls.retriever.corpus.stamp
        cls.finding = next(f for f in cls.retriever.corpus.all()
                           if not f.is_decomposition)
        cls.decomposition = next((f for f in cls.retriever.corpus.all()
                                  if f.is_decomposition), None)

    def test_a_finding_resolves_with_its_stored_sentence(self):
        payload = self.main.record(self.finding.id)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["sentence"], self.finding.sentence)
        self.assertEqual(payload["display_sentence"],
                         self.finding.display_sentence())

    def test_the_record_carries_coordinates_values_score_and_stamp(self):
        payload = self.main.record(self.finding.id)
        self.assertIn("view_title", payload["coordinates"])
        self.assertIn("named_members", payload["values"])
        self.assertIn("engine_score", payload)
        self.assertEqual(payload["run_stamp"], config.run_stamp_line())

    def test_a_decomposition_resolves_from_the_same_endpoint(self):
        if self.decomposition is None:
            self.skipTest("no decomposition sidecar loaded in this mirror")
        payload = self.main.record(self.decomposition.id)
        self.assertEqual(payload["record_type"], "decomposition")
        self.assertTrue(payload["values"]["members"])

    def test_an_unknown_id_404s(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            self.main.record("1-99999999")
        self.assertEqual(caught.exception.status_code, 404)

    def test_the_html_view_is_readable_and_stamped(self):
        payload = self.main.record(self.finding.id)
        page = self.main._record_html(payload)
        self.assertIn(config.run_stamp_line(), page)
        self.assertIn("Stored sentence", page)
        self.assertIn(self.finding.id, page)

    def test_the_citation_url_points_at_this_endpoint(self):
        self.assertTrue(config.record_url(self.finding.id)
                        .endswith(f"/{self.finding.id}"))


class CitationMapTests(unittest.TestCase):
    def test_the_map_carries_what_a_hover_needs(self):
        cites = render.citation_map(FINDINGS, run_date=RUN_DATE)
        for finding in FINDINGS:
            entry = cites[finding.id]
            self.assertEqual(entry["sentence"], finding.sentence)
            self.assertEqual(entry["display_sentence"],
                             finding.display_sentence())
            self.assertEqual(entry["stamp"], RUN_DATE)
            self.assertTrue(entry["url"].endswith(finding.id))

    def test_a_decomposition_is_marked_as_one(self):
        cites = render.citation_map(FINDINGS, run_date=RUN_DATE)
        self.assertTrue(cites["d1-00042"]["is_decomposition"])
        self.assertFalse(cites["1-00235"]["is_decomposition"])


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""WP-D15 -- place profile sheets in the chat. Offline: no model call.

    python -m pytest DiscoverChat/tests/test_place_answers.py -q

Reads the committed profile sheet store and Ask's registry (both on disk);
the writer is a stub of `llm.call`, so what is tested is the code around it.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from DiscoverChat import config  # noqa: F401  -- first, so Insights/src is on sys.path
from DiscoverChat import (assemble, checks, classifier, context_brief, llm,
                          place, render, writer)
from DiscoverChat.corpus import Finding
from DiscoverChat.retrieval import Hit, Result
from DiscoverChat.slots import SlotExtractor

R18 = ("Some answers also come with PLACE FACTS: standard figures about the "
       "place the officer asked about, each with an id starting p-. Start from "
       "the place facts that answer the question, then bring in the findings. "
       "You do not have to use every place fact. Tag them the same way as "
       "findings.")
STAMP = "as of 2026-09-11"


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
]
CLEAN = ("Code 101 accounts for 51.96 percent of total cost across 19 of 22 "
         "measures [1-00235]. Untied grant planned reaches Rs 1.24 crore in "
         "Boipariguda across 12 blocks [1-00987].")

# The brief's T1 table.
T1 = [
    ("What should I know about Kalimela?", [("block", "3843")], "full", [("gp", "119936")], True),
    # WP-D15c (R27): the officer named the level -- no note, alternative kept.
    ("What should I know about Kalimela GP?", [("gp", "119936")], "full", [("block", "3843")], False),
    ("How is Kalimela Gram Panchayat doing", [("gp", "119936")], "full", [("block", "3843")], False),
    ("the panchayat of Kalimela", [("gp", "119936")], "full", [("block", "3843")], False),
    ("How is Kalimela block doing", [("block", "3843")], "full", [("gp", "119936")], False),
    ("Compare Kalimela GP and Bheden", [("gp", "119936"), ("block", "3678")], "main",
     [("block", "3843"), ("gp", "116438")], True),
    ("Kalyansinghpur", [("block", "3914")], "full", [("gp", "121162")], True),
    ("How is Chikilli doing?", [("gp", "117835")], "full", [], False),
    ("How is Barpali block doing?", [("block", "3676")], "full", [], False),
    ("How is Khordha district doing overall?", [("district", "321")], "full", [], False),
    ("How is Itipur doing in Bhubaneswar block", [("gp", "119605")], "full", [], False),
    ("Compare Kalimela and Bheden", [("block", "3843"), ("block", "3678")], "main",
     [("gp", "119936"), ("gp", "116438")], True),
    ("Compare Kalimela, Bheden, Laxmipur and Boipariguda", [], "", [], False),
    ("Which blocks stand out on expenditure?", [], "", [], False),
]


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store, why = place.open_store()
        if cls.store is None:
            raise unittest.SkipTest(f"no profile sheet store: {why}")
        cls.extractor = SlotExtractor()

    def plan(self, text):
        return place.resolve(text, self.extractor.geography(text)["mentions"],
                             self.store)

    def groups(self, text):
        return place.groups_for(self.plan(text), self.store)

    def kalimela(self):
        return {f.row: f for f in place.all_facts(
            self.groups("How is Kalimela block doing"))
            if f.row[:1] in "AEFG"}


# ═════════════════════════════════════════════════════════════════════════════
# T1 -- from the question to the places
# ═════════════════════════════════════════════════════════════════════════════

class ResolutionTests(_Base):

    def test_the_t1_table(self):
        for text, answered, mode, alternatives, has_note in T1:
            with self.subTest(text=text):
                plan = self.plan(text)
                self.assertEqual([(p["level"], p["code"]) for p in plan.places], answered)
                self.assertEqual(plan.mode, mode)
                self.assertEqual([(a["level"], a["code"]) for a in plan.alternatives],
                                 alternatives)
                self.assertEqual(bool(plan.note), has_note)

    def test_the_notes_words(self):
        self.assertEqual(self.plan("What should I know about Kalimela?").note,
                         'This answer is about Kalimela block. For the Gram '
                         'Panchayat, ask about "Kalimela GP".')
        # WP-D15c (R27): the officer wrote "GP", so no note.
        self.assertEqual(self.plan("What should I know about Kalimela GP?").note, "")
        self.assertEqual(self.plan("Compare Kalimela GP and Bheden").note,
                         'This answer is about Bheden block. For the Gram '
                         'Panchayat, ask about "Bheden GP".')
        self.assertEqual(self.plan("Kalyansinghpur").note,
                         'This answer is about Kalyansingpur block. For the Gram '
                         'Panchayat, ask about "Kalyansinghpur GP".')

    def test_the_quoted_words_resolve_to_the_alternative(self):
        for text, *_ in T1:
            for alt in self.plan(text).alternatives:
                with self.subTest(text=text, ask=alt["ask"]):
                    again = self.plan(alt["ask"])
                    self.assertEqual([(p["level"], p["code"]) for p in again.places],
                                     [(alt["level"], alt["code"])])

    def test_one_mention_is_decided_by_position(self):
        # Two mentions of one name: the first says GP, the second says block,
        # and the block is the GP's parent -- dropped (rule 3).
        plan = self.plan("Kalimela GP in Kalimela block")
        self.assertEqual([(p["level"], p["code"]) for p in plan.places],
                         [("gp", "119936")])
        self.assertIn("parent", plan.dropped[0]["why"])

    def test_g_p_with_dots_and_gp_before(self):
        self.assertEqual(self.plan("Kalimela G.P. spending").places[0]["level"], "gp")
        self.assertEqual(self.plan("GP Kalimela spending").places[0]["level"], "gp")
        self.assertEqual(self.plan("Gram Panchayat of Bheden").places[0]["level"], "gp")

    def test_find_is_given_the_slot_readers_name(self):
        # The typed spelling finds nothing; the spelling geography returns does.
        self.assertEqual(self.store.find("block", "Kalyansinghpur"), [])
        geo = self.extractor.geography("Kalyansinghpur")
        self.assertIn("Kalyansingpur", geo["blocks"])
        self.assertEqual(self.plan("Kalyansinghpur").places[0]["code"], "3914")

    def test_geographys_existing_fields_are_unchanged(self):
        geo = self.extractor.geography("What should I know about Kalimela?")
        self.assertEqual({k: v for k, v in geo.items() if k != "mentions"},
                         {"gp_lgd_codes": ["119936"], "gp_names": ["Kalimela"],
                          "blocks": ["Kalimela"], "districts": []})
        slots = self.extractor.extract("What should I know about Kalimela?")
        self.assertNotIn("mentions", slots.as_dict())
        self.assertEqual(len(slots.mentions), 2)

    def test_a_name_with_several_codes_is_dropped(self):
        fake = mock.Mock(wraps=self.store)
        fake.find.side_effect = lambda level, name: ["1", "2"]
        fake.place.side_effect = self.store.place
        plan = place.resolve("How is Barpali block doing?",
                             self.extractor.geography("How is Barpali block doing?")["mentions"],
                             fake)
        self.assertEqual(plan.places, [])
        self.assertEqual(plan.dropped[0]["why"], "2 places share the name")

    def test_more_places_than_the_setting(self):
        text = "Compare Kalimela and Bheden"
        plan = place.resolve(text, self.extractor.geography(text)["mentions"],
                             self.store, max_places=1)
        self.assertEqual(plan.places, [])
        self.assertIn("more than 1", plan.why_no_sheet)


# ═════════════════════════════════════════════════════════════════════════════
# T2 -- what the writer is handed
# ═════════════════════════════════════════════════════════════════════════════

def _legacy_prompt(question, findings, run_date="", reason=""):
    """The request exactly as `build_consolidation_prompt` built it before
    WP-D15, copied here so a drift in the no-place path shows."""
    parts = [context_brief.for_consolidating_writer(), ""]
    parts.append(context_brief.CONSOLIDATING_WRITER_PROMPT)
    parts.append("")
    if run_date:
        parts.append(f"The analysis was run {run_date}.")
    parts.append(f"The officer asked: {question}")
    parts.append("")
    parts.append("FINDINGS")
    parts.append(writer._render_findings_for_consolidation(findings))
    if reason:
        parts.append("")
        parts.append("A previous attempt at this answer was rejected. The "
                     "reason given was:")
        parts.append(reason)
    return "\n".join(parts)


class HandOverTests(_Base):

    def test_full_turn_payload(self):
        groups = self.groups("What should I know about Kalimela?")
        prompt = writer.build_consolidation_prompt(
            "What should I know about Kalimela?", FINDINGS, run_date=STAMP,
            place_groups=groups)
        stored = self.store.sentences("block", "3843")
        block = prompt[prompt.index("PLACE FACTS — Kalimela block"):
                       prompt.index("\n\nFINDINGS")]
        lines = [l for l in block.splitlines()[1:] if l.startswith("[")]
        self.assertEqual(lines, [f"[{s['id']}] {s['sentence']}" for s in stored])
        f1 = next(s for s in stored if s["row"] == "F1")
        self.assertIn(f"[{f1['id']}] {f1['sentence']}\n    ({f1['note']})", block)
        self.assertLess(prompt.index("PLACE FACTS"), prompt.index("FINDINGS"))
        self.assertIn("[1-00235] ", prompt)

    def test_main_turn_payload(self):
        groups = self.groups("Compare Kalimela and Bheden")
        prompt = writer.build_consolidation_prompt(
            "Compare Kalimela and Bheden", FINDINGS, run_date=STAMP,
            place_groups=groups)
        self.assertIn("PLACE FACTS — Kalimela block", prompt)
        self.assertIn("PLACE FACTS — Bheden block", prompt)
        rows = {l.split("]")[0].rsplit("-", 1)[1]
                for l in prompt.splitlines() if l.startswith("[p-")}
        self.assertEqual(rows, set(place.MAIN_ROWS) & rows)
        self.assertEqual(sum(1 for l in prompt.splitlines() if l.startswith("[p-")),
                         sum(len(g.facts) for g in groups))

    def test_the_paragraph_only_with_place_facts(self):
        self.assertEqual(context_brief.PLACE_FACTS_PARAGRAPH, R18)
        groups = self.groups("What should I know about Kalimela?")
        with_place = writer.build_consolidation_prompt(
            "q", FINDINGS, run_date=STAMP, place_groups=groups)
        self.assertIn(R18 + "\n\nReturn only the finished prose.", with_place)
        plain = writer.build_consolidation_prompt("q", FINDINGS, run_date=STAMP)
        self.assertNotIn(R18, plain)
        self.assertNotIn(R18, context_brief.CONSOLIDATING_WRITER_PROMPT)

    def test_a_no_place_prompt_is_byte_identical_to_todays(self):
        for reason in ("", "It cited 1-99999."):
            self.assertEqual(
                writer.build_consolidation_prompt("Is spending on track?", FINDINGS,
                                                  run_date=STAMP, reason=reason),
                _legacy_prompt("Is spending on track?", FINDINGS, STAMP, reason))
            self.assertEqual(
                writer.build_consolidation_prompt("Is spending on track?", FINDINGS,
                                                  run_date=STAMP, reason=reason,
                                                  place_groups=[]),
                _legacy_prompt("Is spending on track?", FINDINGS, STAMP, reason))

    def test_a_sheet_only_request_has_no_findings_block(self):
        groups = self.groups("What should I know about Kalimela?")
        prompt = writer.build_consolidation_prompt("q", [], run_date=STAMP,
                                                   place_groups=groups)
        self.assertNotIn("FINDINGS", prompt)
        self.assertIn("PLACE FACTS", prompt)


# ═════════════════════════════════════════════════════════════════════════════
# T3 -- the number check, row by row: one passing and one failing sentence
# ═════════════════════════════════════════════════════════════════════════════

class NumberCheckTests(_Base):

    def run_check(self, prose, findings=(), **kw):
        facts = list(self.kalimela().values())
        return checks.check_citations(prose, list(findings), place_facts=facts,
                                      run_date=STAMP, **kw)

    def test_step1_place_ids_are_known(self):
        a1 = self.kalimela()["A1"].id
        self.assertTrue(self.run_check(f"It has 852 planned activities [{a1}].")
                        ["1_ids_known"]["pass"])
        self.assertFalse(self.run_check("It has 852 planned activities "
                                        "[p-block-3843-Z9].")["1_ids_known"]["pass"])

    def test_step2_a_place_fact_supports_its_numerals(self):
        a3 = self.kalimela()["A3"].id
        self.assertTrue(self.run_check(
            f"Its planned cost is Rs 7.65 crore [{a3}].")["2_numerals_cited"]["pass"])
        self.assertFalse(self.run_check(
            f"Its planned cost is Rs 7.7 crore [{a3}].")["2_numerals_cited"]["pass"])
        self.assertFalse(self.run_check(
            "Its planned cost is Rs 7.65 crore.")["2_numerals_cited"]["pass"])

    def test_step2_dashes_and_short_fiscal_years_all_answers(self):
        f = _finding("1-00500", "In 2023-2024 the cost was Rs 2.62 crore.")
        for written in ("2023-24", "2023–24", "2023—2024", "2023‑24"):
            with self.subTest(written=written):
                r = checks.check_citations(f"In {written} it was Rs 2.62 crore [1-00500].", [f])
                self.assertTrue(r["2_numerals_cited"]["pass"], r["2_numerals_cited"])
        for wrong in ("2023-25", "2022-24"):
            with self.subTest(wrong=wrong):
                r = checks.check_citations(f"In {wrong} it was Rs 2.62 crore [1-00500].", [f])
                self.assertFalse(r["2_numerals_cited"]["pass"])
        self.assertIn("2023-2024", checks._num_variants("2023-24"))
        self.assertIn("2023-24", checks._num_variants("2023-2024"))
        self.assertNotIn("2023-2025", checks._num_variants("2023-25"))

    def test_step3_causal_is_unchanged(self):
        a6 = self.kalimela()["A6"].id
        r = self.run_check(f"Spending is 23.0% of the planned cost because of "
                           f"late approvals [{a6}].", causal_mode="block")
        self.assertFalse(r["3_causal"]["pass"])
        r = self.run_check(f"Spending is 23.0% of the planned cost [{a6}].",
                           causal_mode="block")
        self.assertTrue(r["3_causal"]["pass"])

    def test_step4_place_facts_are_never_required(self):
        r = self.run_check(CLEAN, FINDINGS)
        self.assertTrue(r["4_all_findings_cited"]["pass"])
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))
        r = self.run_check(CLEAN.split(" Untied")[0], FINDINGS)
        self.assertFalse(r["4_all_findings_cited"]["pass"])
        self.assertEqual(r["4_all_findings_cited"]["dropped"], ["1-00987"])

    def test_step5_the_a7_line_holds_its_direction(self):
        a7 = self.kalimela()["A7"].id
        r = self.run_check(f"Spending is Rs 5.90 crore below plan [{a7}].",
                           direction_mode="block")
        self.assertTrue(r["5_direction"]["pass"])
        self.assertEqual(r["5_direction"]["checked"], 1)
        r = self.run_check(f"Spending exceeded the plan by Rs 5.90 crore [{a7}].",
                           direction_mode="block")
        self.assertFalse(r["5_direction"]["pass"])
        self.assertIn("Rs 5.90 crore below plan", checks.citation_failure_reason(r))

    def test_step6_standing(self):
        rows = self.kalimela()
        a6, a1, g3 = rows["A6"].id, rows["A1"].id, rows["G3"].id
        good = [f"Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks [{a6}].",
                f"It has 852 planned activities, the 5th-most of 16 blocks [{a1}].",
                f"33.3% of payments are linked, the 6th lowest [{g3}]."]
        bad = [f"Spending is 23.0% of the planned cost, the 4th highest of 16 blocks [{a6}].",
               f"It has 852 planned activities, the most of 16 blocks [{a1}].",
               f"Spending is 23.0%, in the lowest quarter [{a6}]."]
        for prose in good:
            with self.subTest(prose=prose):
                self.assertTrue(self.run_check(prose, standing_mode="block")["6_standing"]["pass"])
        for prose in bad:
            with self.subTest(prose=prose):
                r = self.run_check(prose, standing_mode="block")
                self.assertFalse(r["6_standing"]["pass"])
                self.assertFalse(r["all_pass"])
                self.assertIn(a6 if a6 in prose else a1,
                              checks.citation_failure_reason(r))
        r = self.run_check(bad[0], standing_mode="log")
        self.assertFalse(r["6_standing"]["pass"])
        self.assertFalse(r["6_standing"]["counts"])
        self.assertNotIn("6_standing", self.run_check(bad[0], standing_mode="off"))
        # A sentence citing no place fact is not checked.
        r = checks.check_citations("Code 101 is the 4th highest [1-00235].",
                                   FINDINGS[:1], place_facts=[rows["A6"]],
                                   standing_mode="block")
        self.assertTrue(r["6_standing"]["pass"])
        self.assertEqual(r["6_standing"]["checked"], 0)
        # No place facts: no step 6 at all.
        self.assertNotIn("6_standing", checks.check_citations(CLEAN, FINDINGS))

    def test_step7_number_words_are_logged_never_counted(self):
        a6 = self.kalimela()["A6"].id
        r = self.run_check(f"Spending is 23.0% of the planned cost, about a "
                           f"quarter, the 4th lowest [{a6}]. Nearly half had "
                           f"no cost [{a6}].")
        step = r["7_number_words"]
        self.assertFalse(step["pass"])
        self.assertFalse(step["counts"])
        self.assertEqual([w.lower() for w in step["words"]], ["quarter", "half"])
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))
        clean = checks.scan_number_words("It sits in the lowest quarter of the "
                                         "6,800 and the upper-middle quarter.")
        self.assertTrue(clean["pass"], clean)
        self.assertNotIn("7_number_words",
                         self.run_check(f"It is 23.0% [{a6}].", number_words_mode="off"))
        self.assertIn("two-thirds", [w.lower() for w in
                                     checks.scan_number_words("Two-thirds of it.")["words"]])

    def test_step7_is_written_to_the_log(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(llm, "LOG_DIR", Path(tmp)):
            writer._log_number_words("t1", "q", 1, checks.scan_number_words(
                "Spending doubled in the second year."))
            line = json.loads((Path(tmp) / "citation_failures.jsonl").read_text(
                encoding="utf-8").splitlines()[0])
        self.assertEqual(line["kind"], "number_words_shown")
        self.assertIs(line["fell_back"], False)
        self.assertEqual([w.lower() for w in line["words"]], ["doubled", "second"])


# ═════════════════════════════════════════════════════════════════════════════
# T4 + T5 -- what the officer sees, and what the service returns
# ═════════════════════════════════════════════════════════════════════════════

def _routing(move=classifier.RETRIEVE):
    return classifier.Routing(move=move, source="rule", reason="test stub")


class TurnTests(_Base):

    def setUp(self):
        self.assembler = assemble.Assembler(
            SimpleNamespace(corpus=SimpleNamespace(all=lambda: [])),
            allow_model=True, use_judge=False, sheets=self.store)

    def turn(self, question, findings, replies, *, allow_model=True,
             move=classifier.RETRIEVE):
        self.assembler.allow_model = allow_model
        slots = self.extractor.extract(question)
        result = Result(slots=slots,
                        hits=[Hit(finding=f, cosine=0.7, boost=0.0, score=0.7)
                              for f in findings],
                        considered=100, best_cosine=0.7,
                        threshold=config.CANDIDATE_FLOOR, collapsed_count=0)
        self.assembler._retrieve = lambda message, turn_id=None: (result, {"used": True})
        calls = iter(replies)

        def fake_call(model, prompt, max_completion, purpose, *, turn_id=None,
                      attempt=None):
            reply = next(calls)
            if isinstance(reply, Exception):
                raise reply
            return {"response_text": reply, "finish_reason": "stop",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(llm, "LOG_DIR", Path(tmp)), \
                mock.patch.object(llm, "call", side_effect=fake_call), \
                mock.patch.object(assemble.classifier, "classify",
                                  return_value=_routing(move)):
            return self.assembler.answer(question)

    def test_a_kept_narrative(self):
        rows = self.kalimela()
        prose = (f"Spending is 23.0% of the planned cost, the 4th lowest of 16 "
                 f"blocks [{rows['A6'].id}]. It spent Rs 1.76 crore "
                 f"[{rows['A5'].id}]. " + CLEAN)
        answer = self.turn("What should I know about Kalimela?", FINDINGS, [prose])
        self.assertTrue(answer.text.startswith(
            'This answer is about Kalimela block. For the Gram Panchayat, ask '
            'about "Kalimela GP".\n\n'))
        self.assertEqual(answer.place["lines_used"], [rows["A6"].id, rows["A5"].id])
        self.assertEqual(answer.place["mode"], "full")
        self.assertEqual(answer.place["lines_offered"],
                         len(self.store.sentences("block", "3843")))
        self.assertEqual(answer.place["answered"],
                         [{"level": "block", "code": "3843", "name": "Kalimela",
                           "label": "Kalimela block"}])
        self.assertEqual(answer.place["alternatives"][0]["ask"], "Kalimela GP")
        self.assertEqual(answer.retrieval["place"]["lines_used"],
                         answer.place["lines_used"])
        self.assertEqual([f.id for f in answer.findings], ["1-00235", "1-00987"])
        # citations: one entry per place fact handed, in a finding's shape.
        entry = answer.citations[rows["A3"].id]
        self.assertEqual(entry["display_sentence"],
                         "Kalimela block: " + rows["A3"].sentence)
        self.assertEqual(entry["scope"], "Kalimela block")
        self.assertEqual(entry["view"], "Place profile")
        self.assertIs(entry["is_profile"], True)
        self.assertIs(entry["is_decomposition"], False)
        self.assertEqual(answer.citations[rows["A1"].id]["display_sentence"],
                         rows["A1"].sentence)
        self.assertEqual(answer.citations[rows["F1"].id]["standing"], rows["F1"].note)
        self.assertEqual(len(answer.citations),
                         2 + answer.place["lines_offered"])
        # answer_html: place tags wrapped, note leading.
        html_out = render.to_html(answer.tagged_text, answer.findings,
                                  run_date=answer.stamp,
                                  place_facts=answer.place_facts,
                                  lead=answer.lead)
        self.assertIn(f'data-finding-id="{rows["A6"].id}"', html_out)
        self.assertNotIn(f"[{rows['A6'].id}]", html_out)
        self.assertTrue(html_out.split("<p>", 1)[1].startswith("This answer is about"))

    def test_sheet_only_when_the_judge_kept_nothing(self):
        a1 = self.kalimela()["A1"].id
        answer = self.turn("What should I know about Kalimela?", [],
                           [f"Kalimela block has 852 planned activities [{a1}]."])
        self.assertTrue(answer.prose["used"])
        self.assertNotIn("nothing on this", answer.text)
        self.assertEqual(answer.place["insights_offered"], 0)
        self.assertEqual(answer.place["lines_used"], [a1])

    def test_the_insight_cap(self):
        many = [_finding(f"1-0{i:04d}", f"Across {i} things, x reaches {i}.")
                for i in range(1, 11)]
        prose = " ".join(f"It reaches {i} [1-0{i:04d}]." for i in range(1, 9))
        answer = self.turn("What should I know about Kalimela?", many, [prose])
        self.assertEqual(answer.place["insights_offered"], config.PROFILE_INSIGHT_CAP)
        self.assertEqual(answer.place["insights_held_back"], 2)
        self.assertEqual(len(answer.findings), 8)

    def test_t4_refused_twice_shows_what_the_writer_chose(self):
        rows = self.kalimela()
        bad = (f"It spent Rs 9.99 crore [{rows['A5'].id}]. Spending is 23.0% "
               f"[{rows['A6'].id}]. Again [{rows['A5'].id}].")
        answer = self.turn("What should I know about Kalimela?", FINDINGS, [bad, bad])
        self.assertFalse(answer.prose["used"])
        self.assertEqual(answer.place["lines_used"], [rows["A5"].id, rows["A6"].id])
        body = answer.text.split("\n\n", 1)[1]
        self.assertTrue(body.startswith(
            f"Kalimela block\n- {rows['A5'].sentence}\n- {rows['A6'].sentence}"))
        self.assertIn(FINDINGS[0].display_sentence(), answer.text)
        self.assertEqual(answer.tagged_text, "")
        self.assertEqual(answer.citations, {})

    def test_t4_refused_twice_citing_no_place_fact(self):
        bad = "It reached Rs 9.99 crore [1-00235]."
        answer = self.turn("What should I know about Kalimela?", FINDINGS, [bad, bad])
        self.assertEqual(answer.place["lines_used"],
                         [f"p-block-3843-{r}" for r in place.MAIN_ROWS])

    def test_t4_writer_call_failed_or_empty(self):
        answer = self.turn("What should I know about Kalimela?", FINDINGS,
                           [RuntimeError("down")])
        self.assertEqual(answer.place["lines_used"],
                         [f"p-block-3843-{r}" for r in place.MAIN_ROWS])
        answer = self.turn("What should I know about Kalimela?", FINDINGS, ["", ""])
        self.assertEqual(answer.place["lines_used"],
                         [f"p-block-3843-{r}" for r in place.MAIN_ROWS])

    def test_t4_model_off(self):
        answer = self.turn("How is Chikilli doing?", FINDINGS, [], allow_model=False)
        self.assertTrue(answer.text.startswith("Chikilli Gram Panchayat\n- Chikilli "
                                               "Gram Panchayat has"))
        self.assertEqual(answer.place["lines_used"],
                         [f"p-gp-117835-{r}" for r in place.MAIN_ROWS
                          if self.store.sentence(f"p-gp-117835-{r}")])
        self.assertIn(FINDINGS[0].display_sentence(), answer.text)
        none = self.turn("How is Chikilli doing?", [], [], allow_model=False)
        self.assertIn("nothing on this", none.text)

    def test_t4_two_places_one_group_each(self):
        bad = "It reached Rs 9.99 crore [1-00235]."
        answer = self.turn("Compare Kalimela and Bheden", FINDINGS, [bad, bad])
        self.assertIn("\n\nKalimela block\n- ", answer.text)
        self.assertIn("\n\nBheden block\n- ", answer.text)
        self.assertEqual(answer.place["mode"], "main")
        self.assertEqual(len(answer.place["lines_used"]), 14)

    def test_no_place_turn_is_untouched(self):
        answer = self.turn("Is spending on track?", FINDINGS, [CLEAN])
        self.assertEqual(answer.place, {})
        self.assertNotIn("place", answer.as_dict())
        self.assertNotIn("place", answer.retrieval)

    def test_lookup_and_why_get_no_sheet(self):
        answer = self.turn("How much was spent in Kalimela?", [], [],
                           move=classifier.LOOKUP)
        self.assertEqual(answer.place, {})
        answer = self.turn("Why is spending low in Kalimela?", FINDINGS, [],
                           move=classifier.WHY)
        self.assertEqual(answer.place, {})

    def test_switch_off(self):
        with mock.patch.object(config, "PROFILE_SHEETS", False):
            answer = self.turn("What should I know about Kalimela?", FINDINGS, [CLEAN])
        self.assertEqual(answer.place, {})
        self.assertFalse(answer.text.startswith("This answer is about"))

    # ── WP-D15c ───────────────────────────────────────────────────────────────
    def test_r26_no_more_than_line_on_a_place_answer(self):
        many = [_finding(f"1-0{i:04d}", f"Across {i} things, x reaches {i}.")
                for i in range(1, 11)]
        answer = self.turn("What should I know about Kalimela?", many,
                           ["It reaches 1 [1-00001]."])
        self.assertEqual(answer.place["insights_held_back"], 2)
        self.assertNotIn("More than", answer.text)

    def test_r26_the_line_stays_on_an_ordinary_capped_turn(self):
        slots = self.extractor.extract("Is spending on track?")
        result = Result(slots=slots,
                        hits=[Hit(finding=f, cosine=0.7, boost=0.0, score=0.7)
                              for f in FINDINGS],
                        considered=100, best_cosine=0.7,
                        threshold=config.CANDIDATE_FLOOR, collapsed_count=0,
                        capped=True)
        self.assembler._retrieve = lambda message, turn_id=None: (result, {"used": True})
        self.assembler.allow_model = False
        with mock.patch.object(assemble.classifier, "classify",
                               return_value=_routing()):
            answer = self.assembler.answer("Is spending on track?")
        self.assertIn(f"More than {config.ANSWER_CAP} findings", answer.text)

    def test_r25_left_out_ids_kept_in_the_prose_record(self):
        answer = self.turn("Is spending on track?", FINDINGS,
                           ["Untied grant planned reaches Rs 1.24 crore in "
                            "Boipariguda across 12 blocks [1-00987]."])
        self.assertTrue(answer.prose["used"])
        self.assertEqual(answer.prose["left_out"], ["1-00235"])
        # A sheet answer that cites no insight at all is kept (no floor).
        a1 = self.kalimela()["A1"].id
        answer = self.turn("What should I know about Kalimela?", FINDINGS,
                           [f"Kalimela block has 852 planned activities [{a1}]."])
        self.assertTrue(answer.prose["used"])
        self.assertEqual(answer.prose["left_out"], ["1-00235", "1-00987"])

    def test_r25_the_fall_back_is_unchanged(self):
        bad = "It reached Rs 9.99 crore [1-00235]."
        answer = self.turn("Is spending on track?", FINDINGS, [bad, bad])
        self.assertFalse(answer.prose["used"])
        self.assertEqual(answer.prose["left_out"], [])
        for f in FINDINGS:
            self.assertIn(f.display_sentence(), answer.text)

    def test_r25_block_restores_the_old_rule(self):
        with mock.patch.object(config, "EVERY_INSIGHT_CHECK", "block"):
            answer = self.turn("Is spending on track?", FINDINGS,
                               ["Untied grant planned reaches Rs 1.24 crore in "
                                "Boipariguda across 12 blocks [1-00987].",
                                "Untied grant planned reaches Rs 1.24 crore in "
                                "Boipariguda across 12 blocks [1-00987]."])
        self.assertFalse(answer.prose["used"])
        self.assertIn("never cited", answer.prose["reason"])


class StandingEndTests(_Base):
    """WP-D15c T4: highest = most, lowest = fewest; "among the highest" is
    not a rank. The five correct sentences of WP-D15 report §4.5 pass; the
    four kinds of real mistake are still caught."""

    def facts(self, *places):
        out = []
        for level, code in places:
            info = self.store.place(level, code)
            plan = place.Plan(places=[{k: info[k] for k in ("level", "code", "name", "label")}],
                              mode="full")
            out += place.all_facts(place.groups_for(plan, self.store))
        return out

    def step6(self, prose, facts):
        return checks.check_citations(prose, [], place_facts=facts,
                                      standing_mode="block")["6_standing"]

    def test_the_five_false_alarms_now_pass(self):
        cases = [
            ("Barpali has the most planned activities in the sample: 1,447 across its 2 "
             "Gram Panchayats, the highest of 16 blocks [p-block-3676-A1][p-block-3676-I4].",
             [("block", "3676")]),
            ("Its 808 planned activities rank 7th highest, but its planned cost of Rs 3.36 "
             "crore is the 7th lowest [p-block-3838-A1][p-block-3838-A3].", [("block", "3838")]),
            ("167 works are marked ongoing, the 4th highest count among 16 blocks "
             "[p-block-3838-E1][p-block-3838-E2].", [("block", "3838")]),
            ("Its activity count is the 4th highest among 9 districts. [p-district-321-A1]",
             [("district", "321")]),
            ("Their planned costs are also among the highest in the comparison: Rs 7.65 "
             "crore in Kalimela and Rs 7.22 crore in Bheden [p-block-3843-A3][p-block-3678-A3].",
             [("block", "3843"), ("block", "3678")]),
        ]
        for prose, places in cases:
            with self.subTest(prose=prose[:50]):
                step = self.step6(prose, self.facts(*places))
                self.assertTrue(step["pass"], step["failures"])

    def test_the_four_mistakes_are_still_caught(self):
        facts = self.facts(("block", "3843"))       # A1 "5th most", A6 "4th lowest"
        for prose in ("Spending is 23.0%, the 4th highest of 16 blocks [p-block-3843-A6].",
                      "It has 852 planned activities, the most of 16 blocks [p-block-3843-A1].",
                      "It has 852 planned activities, the 3rd most of 16 blocks [p-block-3843-A1].",
                      "Spending is 23.0%, in the lowest quarter of blocks [p-block-3843-A6]."):
            with self.subTest(prose=prose):
                self.assertFalse(self.step6(prose, facts)["pass"])

    def test_the_default_stays_log(self):
        self.assertEqual(config.STANDING_CHECK, "log")
        self.assertEqual(config.EVERY_INSIGHT_CHECK, "log")
        self.assertIn("every_insight_check", config.knobs())


# ═════════════════════════════════════════════════════════════════════════════
# T5 -- /record, the payload, and starting with no store
# ═════════════════════════════════════════════════════════════════════════════

class ServiceTests(_Base):

    def test_record_for_a_place_fact(self):
        from DiscoverChat import main
        from fastapi import HTTPException
        with mock.patch.dict(main.STATE, {"profile": self.store,
                                          "retriever": SimpleNamespace(
                                              corpus=SimpleNamespace(get=lambda i: None))}):
            payload = main.record("p-block-3843-F1")
            self.assertEqual(payload["record_type"], "place_fact")
            self.assertEqual(payload["label"], "Kalimela block")
            self.assertEqual(payload["row"], "F1")
            self.assertEqual(payload["figures"]["F1"]["value"], 168)
            self.assertTrue(payload["note"].startswith("An activity with no approval"))
            self.assertEqual(payload["run_stamp"], config.run_stamp_line())
            self.assertTrue(payload["url"].endswith("p-block-3843-F1"))
            listed = main.record("p-block-3843-B-2023-2024")
            self.assertEqual(listed["figures"]["B"]["activities"], 335)
            page = main.record("p-block-3843-F1", format="html").body.decode("utf-8")
            for needle in ("Kalimela block", "Stored sentence", config.run_stamp_line()):
                self.assertIn(needle, page)
            with self.assertRaises(HTTPException) as caught:
                main.record("p-block-3843-Z9")
            self.assertEqual(caught.exception.status_code, 404)

    def test_the_service_starts_with_no_store(self):
        from DiscoverChat import main

        class _Corpus(list):
            def all(self):
                return list(self)

        class _Retriever:
            corpus = _Corpus()

        async def run():
            async with main.lifespan(main.app):
                health = main.health()
                self.assertFalse(health["profile_sheets"]["available"])
                self.assertIn("no store here", health["profile_sheets"]["why"])
                self.assertIsNotNone(main.STATE["assembler"])
                self.assertIsNone(main.STATE["assembler"].sheet_store())

        with mock.patch.object(main, "Retriever", _Retriever), \
                mock.patch.object(main.place_mod, "open_store",
                                  return_value=(None, "OSError: no store here")):
            asyncio.run(run())

    def test_open_store_never_raises(self):
        from DiscoverChat import profile_store
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(profile_store, "_DEFAULT",
                                  profile_store.ProfileStore(tmp)):
            store, why = place.open_store()
        self.assertIsNone(store)
        self.assertIn("stamp", why)

    def test_knobs_show_the_five_settings(self):
        knobs = config.knobs()
        for key in ("profile_sheets", "profile_insight_cap", "profile_max_places",
                    "standing_check", "number_words"):
            self.assertIn(key, knobs)
        self.assertEqual(knobs["profile_insight_cap"], 8)
        self.assertEqual(knobs["profile_max_places"], 3)


if __name__ == "__main__":
    unittest.main()

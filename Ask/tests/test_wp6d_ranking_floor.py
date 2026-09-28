"""WP-6d — bottom-10 rankings, the D34 conditions, chips and the echo, pinned.

    T1  M6: IMP-009 / IMP-019 / IMP-020 default their ranking floor to 1 and keep
        ten rows; no other threshold defaults
    T2  a superlative on those three keeps the list unless the number is written
    T3  gold G1613 expects an answer

No API key and no network: the extractor is stubbed, and every router path runs
against the sample database.
"""
import json
import os
import re
import time
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


def _stubbed(extractor_says: dict):
    """A stand-in for `extract_entities` that also records the slots it was asked."""
    asked: list = []

    def stub(query, slots, client, intent=None):
        asked.append(list(slots))
        return {s: extractor_says.get(s) for s in slots}
    return stub, asked


def _extract(qid: str, question: str, extractor_says: dict):
    """`_extract_slot_values` exactly as the vector path calls it, extractor stubbed."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    slots = T[qid]["param_slots"]
    stub, _ = _stubbed(extractor_says)
    real, router.extract_entities = router.extract_entities, stub
    try:
        return router._extract_slot_values(
            question, router._template_slot_types(T[qid]), object(),
            validator=_validator(), list_slots=router._list_slots(slots),
            superlative_lists=router.superlative_list_slots(slots))
    finally:
        router.extract_entities = real


def _fill(qid: str, question: str, raw: dict):
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
        check_direction=True)


def _answer(qid: str, question: str, extractor_says: dict):
    """(entities, clarify, served result or None) — the vector path from extraction on."""
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


RANKING_FLOORS = ("IMP-009", "IMP-019", "IMP-020")
FY26 = {"date_range": "2025-2026"}


# ── T1 ────────────────────────────────────────────────────────────────────────

class T1MigrationTests(unittest.TestCase):

    def _slot(self, qid, name):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        return next(s for s in T[qid]["param_slots"] if s["name"] == name)

    def test_the_three_floors_default_to_one_and_keep_unit_and_direction(self):
        for qid in RANKING_FLOORS:
            slot = self._slot(qid, "threshold")
            self.assertEqual((slot.get("optional"), slot.get("default")), (True, "1"), qid)
            self.assertEqual((slot["unit"], slot["direction"]), ("activities", "above"), qid)
            top_n = self._slot(qid, "top_n")
            self.assertEqual((top_n["default"], top_n["superlative_means_one"]),
                             ("10", False), qid)

    def test_no_other_threshold_defaults_and_no_other_list_is_declared(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid, entry in T.items():
            for slot in entry["param_slots"]:
                if qid in RANKING_FLOORS:
                    continue
                with self.subTest(qid=qid, slot=slot["name"]):
                    self.assertNotIn("superlative_means_one", slot)
                    if slot["entity_type"] in ("threshold", "amount_threshold"):
                        self.assertNotIn("default", slot)
                        self.assertFalse(slot.get("optional"))

    def test_m6_is_applied_and_idempotent(self):
        import sys
        sys.path.insert(0, str(_BACKEND))
        from tools import derive_catalog as dc
        from tools.migrations import m6_ranking_floor as m6
        source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertEqual(m6.rewrite(source), (source, []))

    def test_the_contract_refuses_a_floor_default_anywhere_else(self):
        import sys
        sys.path.insert(0, str(_BACKEND))
        from tools import derive_catalog as dc
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        entry = json.loads(json.dumps(T["PLN-045"]))
        for slot in entry["param_slots"]:
            if slot["name"] == "threshold":
                slot.update(optional=True, default="1")
        problems = dc.contract_problems({"PLN-045": entry})
        self.assertTrue(any("default" in p for p in problems), problems)
        entry = json.loads(json.dumps(T["IMP-009"]))
        for slot in entry["param_slots"]:
            if slot["name"] == "top_n":
                del slot["superlative_means_one"]
        problems = dc.contract_problems({"IMP-009": entry})
        self.assertTrue(any("superlative_means_one" in p for p in problems), problems)

    @_needs_db
    def test_the_default_floor_answers_and_the_oracle_still_reproduces(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        oracle = json.loads((_BACKEND / "tests" / "data" / "workbook_test_report.json")
                            .read_text(encoding="utf-8"))
        for qid in RANKING_FLOORS:
            want = oracle[qid]
            self.assertEqual((want["params"]["threshold"], want["params"]["top_n"]),
                             (50, 10), qid)
            _, clarify, result = _answer(qid, T[qid]["abstract_question"].format(
                date_range="2025-26"), FY26)
            self.assertIsNone(clarify, qid)
            # IMP-019 ranks LSDG themes, and FY 2025-26 has activities under seven.
            self.assertEqual(len(result.result), 7 if qid == "IMP-019" else 10, qid)
            bound = router.bind_for_template(
                T[qid], {"date_range": ["2025-2026"]}, context=qid, person_ids={})
            self.assertEqual((bound["threshold"], bound["top_n"]), ("1", "10"), qid)


# ── T2 ────────────────────────────────────────────────────────────────────────

@_needs_db
class T2SuperlativeTests(unittest.TestCase):

    def test_the_four_operator_questions_answer_with_the_bottom_ten(self):
        for question in (
            "Which focus area has the smallest activity completion rate in FY 2025-26?",
            "Which focus area has the lowest completion rate in FY 2025-26?",
            "Identify the focus area with the lowest completion percentage for FY 2025-26.",
            "For FY 2025-26, which focus area ranks last by completion rate?",
        ):
            with self.assertLogs("query_router.router", "INFO") as logs:
                _, clarify, result = _answer("IMP-009", question, {"top_n": "1", **FY26})
            self.assertIsNone(clarify, question)
            rows = result.result
            self.assertEqual(len(rows), 10, question)
            rates = [r["completion_rate_pct"] for r in rows]
            self.assertEqual(rates, sorted(rates), question)
            self.assertTrue(any("superlative read as list (declared)" in m
                                for m in logs.output), question)

    def test_a_number_written_is_kept(self):
        for question, top_n, rows in (
            ("bottom 3 focus areas by completion rate in 2025-26", "3", 3),
            ("the three focus areas with the lowest completion rate in 2025-26", "3", 3),
            ("the single lowest focus area by completion rate in 2025-26", "1", 10),
            ("which one focus area completes least in 2025-26", "1", 10),
        ):
            _, clarify, result = _answer("IMP-009", question, {"top_n": top_n, **FY26})
            self.assertIsNone(clarify, question)
            self.assertEqual(len(result.result), rows, question)

    def test_a_year_is_not_a_length(self):
        from query_router.router import number_in_question
        self.assertFalse(number_in_question("25", "lowest completion in FY 2024-25"))
        self.assertFalse(number_in_question("2025", "lowest completion in 2025-26"))
        self.assertTrue(number_in_question("5", "bottom 5 in 2024-25"))
        self.assertTrue(number_in_question("12", "the twelve lowest"))

    def test_a_floor_the_officer_sets_binds_and_reads_above(self):
        question = "Which focus areas with at least 50 activities have the lowest completion rate in 2025-26?"
        entities, clarify, result = _answer("IMP-009", question, {"threshold": "50", **FY26})
        self.assertIsNone(clarify)
        self.assertEqual(next(e.resolved_value for e in entities if e.slot_name == "threshold"),
                         "50")

    def test_control_other_rankings_still_honour_one(self):
        _, clarify, result = _answer("EXP-015", "Which GP spent the most in 2024-25?",
                                     {"top_n": "1", "date_range": "2024-2025"})
        self.assertIsNone(clarify)
        self.assertEqual(len(result.result), 1)


# ── T3 ────────────────────────────────────────────────────────────────────────

class T3GoldRowTests(unittest.TestCase):

    def test_g1613_expects_an_answer(self):
        rows = json.loads((_BACKEND / "eval_questions_full.json").read_text(encoding="utf-8"))
        row = next(r for r in rows if r["id"] == "G1613")
        self.assertEqual((row["expected_behavior"], row["case_type"]), ("answer", "standard"))
        self.assertIn("Operator ruling 2026-09-28 (WP-6d): no floor by default, bottom 10.",
                      row["notes"])
        for other in ("G2041", "G2042"):
            r = next(r for r in rows if r["id"] == other)
            self.assertIn("IMP-009", r["acc"], other)


# ── T4 ────────────────────────────────────────────────────────────────────────

_REPO = Path(os.environ.get("PRDW_REPO") or _BACKEND.parent)
_EVAL1 = _REPO / "handoffs" / "WP6_eval1_questions.json"

# D34.4: the extractor invented `plan_type = Main` on these, none of which says "main".
INVENTED_MAIN = (
    ("PLN-014", "Number of Gram Panchayats whose GPDPs are pending for 2022-2023."),   # Eval_1 #253
    ("PLN-001", "ଖୋର୍ଦ୍ଧା ଜିଲ୍ଲାରେ 2024-2025 ରେ କେତେ ଗ୍ରାମ ପଞ୍ଚାୟତ GPDP ଅପଲୋଡ କରିଛନ୍ତି?"),  # gold #1006
    ("PLN-008", "How many GPs in Bhubaneswar uploaded the GPDP after 30 June 2024 in 2024-25?"),  # #1014
    ("PLN-014", "How many GPs have their GPDPs still pending approval for 2024 to 2026?"),  # #2035
)


@_needs_db
class T4PlanTypeGuardTests(unittest.TestCase):

    def test_the_guard_list_is_the_prefill_list_plus_the_words_it_leaves_out(self):
        from query_router import subject_reader as sr
        from query_router.entity_validator import _resolve_config
        _, cfg = _resolve_config("plan_type")
        registry = _validator().registry_values("plan_type")
        prefill = set(sr._vocabulary("plan_type", cfg, registry)[0])
        guard = set(sr.guard_vocabulary("plan_type", _validator()))
        self.assertEqual(guard - prefill, set(sr._NOT_READ["plan_type"]))
        self.assertEqual(prefill - guard, set())
        self.assertIn("plan_type", sr.VOCABULARY_GUARDED)

    def test_an_invented_main_is_dropped_and_logged(self):
        for qid, question in INVENTED_MAIN:
            with self.subTest(qid=qid), self.assertLogs("query_router.router", "INFO") as logs:
                raw = _extract(qid, question, {"plan_type": "Main"})
            self.assertIsNone(raw.get("plan_type"), question)
            self.assertTrue(any("dropped plan_type=['Main']" in m and "plan type words" in m
                                for m in logs.output), logs.output)

    @unittest.skipUnless(_EVAL1.exists(), f"no Eval_1 at {_EVAL1} (set PRDW_REPO from a mirror)")
    def test_every_eval1_row_that_says_main_or_supplementary_still_binds_it(self):
        import re
        import sys
        sys.path.insert(0, str(_BACKEND))
        import grade_eval1
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        rows = json.loads(_EVAL1.read_text(encoding="utf-8"))
        checked = 0
        for row in rows:
            text = row["q"]
            says_main = re.search(r"\bmain\b", text, re.I)
            says_supp = re.search(r"\bsupplementary\b", text, re.I)
            spec = grade_eval1.row_spec(row["n"])
            if not (says_main or says_supp) or spec is None:
                continue
            qid = next((q for q in spec[1]
                        if any(s["name"] == "plan_type" for s in T[q]["param_slots"])), None)
            if qid is None:
                continue
            value = ["Main", "Supplementary"] if says_main and says_supp else \
                ("Main" if says_main else "Supplementary")
            raw = _extract(qid, text, {"plan_type": value})
            with self.subTest(n=row["n"], q=text):
                bound = raw.get("plan_type")
                self.assertIsNotNone(bound)
                got = {_validator().validate(v, "plan_type").resolved_value
                       for v in (bound if isinstance(bound, list) else [bound])}
                self.assertEqual(got, set(value if isinstance(value, list) else [value]))
            checked += 1
        self.assertGreaterEqual(checked, 20)
        # Rows 1-2 are the brief's named pair.
        for n in (1, 2):
            row = next(r for r in rows if r["n"] == n)
            raw = _extract("BUD-006", row["q"], {"plan_type": "Main"})
            self.assertEqual(_validator().validate(raw["plan_type"], "plan_type").resolved_value,
                             "Main", n)


# ── T4 / T5: the hand phrasings ───────────────────────────────────────────────

class T5PhrasingTests(unittest.TestCase):

    def test_the_hand_phrasings_are_in_the_catalogue(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        wanted = {
            "PLN-007": ("Which districts are behind on GPDP submission in a given year?",
                        "Which districts are lagging on GPDP submission in a given year?"),
            "BUD-003": ("Split the sanctioned funds into SFC and Own Funds in a given year",
                        "How much of the sanctioned amount came from a given scheme in a given year?",
                        "What share of the sanctioned budget came from SFC and the 15th Finance Commission?"),
            "PLN-024": ("How many activities are planned in a given block in a given year?",),
        }
        for qid, phrasings in wanted.items():
            for phrasing in phrasings:
                self.assertIn(phrasing, T[qid]["paraphrases"], qid)


# ── T6 ────────────────────────────────────────────────────────────────────────

KALIMELA_Q = "What is the count of planned activities in Kalimela in 2024?"


class _Retriever:
    """A retriever that returns a fixed list — the chips come from the reranker."""

    def __init__(self, qids):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        self.scored = [(q, T[q]["abstract_question"], 0.9 - 0.01 * i)
                       for i, q in enumerate(qids)]

    def retrieve_scored(self, text, k):
        return self.scored[:k]


def _chips_for(question, extractor_says, near_misses):
    """The reranker no-match chips for `question`, extractor and reranker stubbed."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    stub, _ = _stubbed(extractor_says)
    real_extract, real_rerank = router.extract_entities, router.rerank
    router.extract_entities = stub
    router.rerank = lambda query, candidates, client: ("no_match", list(near_misses))
    try:
        result = router._route_vector(
            question, question, time.monotonic(), validator=_validator(),
            openai_client=object(), retriever=_Retriever(near_misses), cache_conn=_adapter(),
            dashboard_results={}, template_map=T, dashboard_questions={},
            start_date=None, end_date=None)
    finally:
        router.extract_entities, router.rerank = real_extract, real_rerank
    return result


@_needs_db
class T6ChipTests(unittest.TestCase):

    def test_a_block_fill_takes_the_gp_gap_with_its_noun(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.zones import readable_question
        fill = {"block_name": "Kalimela", "date_range": "2024-2025"}
        self.assertEqual(readable_question(T["PLN-024"]["abstract_question"], fill),
                         "How many activities are planned under each GPDP theme in "
                         "Kalimela block in 2024-2025?")
        self.assertEqual(readable_question(T["PLN-049"]["abstract_question"], fill),
                         "How many activities are planned under a focus area in "
                         "Kalimela block in 2024-2025?")

    def test_two_tiers_side_by_side_show_the_one_named_and_a_place_keeps_its_tier(self):
        """Pilot rows 1041 / 1042: "in a gram panchayat/Bheden", and "in Laxmipur"
        on a chip for a question that said "Laxmipur GP"."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.zones import readable_question, resolved_question
        q44 = T["PLN-044"]["abstract_question"]
        self.assertEqual(readable_question(q44, {"block_name": "Bheden", "date_range": "2024-2025"}),
                         "Are the planned activities balanced across themes in Bheden block "
                         "in 2024-2025?")
        self.assertEqual(readable_question(T["PLN-024"]["abstract_question"],
                                           {"gp_name": "Laxmipur", "date_range": "2024-2025"}),
                         "How many activities are planned under each GPDP theme in Laxmipur GP "
                         "in 2024-2025?")
        self.assertEqual(readable_question(T["PLN-001"]["abstract_question"],
                                           {"district_name": "Ganjam", "date_range": "2024-2025"}),
                         "How many Gram Panchayats in Ganjam district have uploaded the GPDP "
                         "in 2024-2025?")
        # A unit noun the question already writes is not doubled; the answer echo
        # is unchanged by the chip-only rules.
        self.assertIn("Laxmipur block", readable_question(
            "Which GPs in {block_name} block spent most in {date_range}?",
            {"block_name": "Laxmipur", "date_range": "2024-2025"}))
        self.assertNotIn("block block", readable_question(
            "Which GPs in {block_name} block spent most in {date_range}?",
            {"block_name": "Laxmipur", "date_range": "2024-2025"}))
        self.assertIn("in Laxmipur in", resolved_question(
            T["PLN-024"]["abstract_question"], {"gp_name": "Laxmipur", "date_range": "2024-2025"}))

    def test_block_first_unless_the_question_says_gp(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        slot_type = router._template_slot_types(T["PLN-024"])
        self.assertEqual(_validator().validate("Kalimela", "block").confidence, "exact")
        self.assertEqual(_validator().validate("Kalimela", "gp").confidence, "exact")
        cases = (
            (KALIMELA_Q, {"gp_name": "Kalimela"}, {"block_name": "Kalimela", "gp_name": None}),
            (KALIMELA_Q, {"gp_name": "Kalimela", "block_name": "Kalimela"},
             {"block_name": "Kalimela", "gp_name": None}),
            ("planned activities in Kalimela GP in 2024", {"gp_name": "Kalimela"},
             {"gp_name": "Kalimela"}),
            ("planned activities in Kalimela gram panchayat in 2024", {"gp_name": "Kalimela"},
             {"gp_name": "Kalimela"}),
            ("planned activities in Andhrua in 2024", {"gp_name": "Andhrua"},
             {"gp_name": "Andhrua"}),
        )
        for question, raw, want in cases:
            raw = dict(raw)
            router._block_first(raw, slot_type, _validator(), question)
            for slot, value in want.items():
                self.assertEqual(raw.get(slot), value, (question, slot))

    def test_the_operators_question_chips_name_kalimela_block_and_the_tap_binds_it(self):
        with self.assertLogs("query_router.router", "INFO") as logs:
            result = _chips_for(KALIMELA_Q, {"gp_name": "Kalimela"},
                                ["PLN-024", "PLN-049", "PLN-025"])
        self.assertTrue(any("chip fill: Kalimela read as block (also a GP)" in m
                            for m in logs.output), logs.output)
        chips = [c.send_text for c in result.clarification.options]
        self.assertTrue(chips)
        for chip in chips:
            self.assertIn("Kalimela block", chip)
            self.assertNotIn("a gram panchayat", chip)
            self.assertEqual(chip, next(c.label for c in result.clarification.options
                                        if c.send_text == chip))
        per_theme = next(c for c in chips if "each GPDP theme" in c)
        raw = _extract("PLN-024", per_theme, {"block_name": "Kalimela block"})
        entities, clarify = _fill("PLN-024", per_theme, raw)
        self.assertIsNone(clarify)
        bound = {e.slot_name: e.resolved_value for e in entities}
        self.assertEqual(bound.get("block_name"), "Kalimela")
        self.assertNotIn("gp_name", bound)

    def test_a_chip_shows_no_list_length_the_officer_did_not_write(self):
        """Pilot row 1032: chips read "(the lowest, …)" from the extractor's
        superlative top_n = 1, on a ranking that answers ten rows."""
        question = "Which focus areas with at least 50 activities have the lowest completion rate in 2025-26?"
        result = _chips_for(question, {"top_n": "1", "threshold": "50"}, ["IMP-009", "IMP-020"])
        labels = [c.label for c in result.clarification.options]
        self.assertTrue(labels)
        for label in labels:
            self.assertNotIn("the lowest,", label)
            self.assertIn("(bottom 10, focus areas with at least 50 activities)", label)
        result = _chips_for("bottom 3 focus areas by completion rate in 2025-26",
                            {"top_n": "3"}, ["IMP-009"])
        self.assertIn("(bottom 3)", result.clarification.options[0].label)

    def test_a_scheme_list_survives_into_the_chip_and_is_read_back(self):
        from query_router import subject_reader
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        result = _chips_for("split the sanctioned funds into SFC and Own Funds for 2024-25",
                            {"scheme": ["SFC", "Own Funds"]}, ["BUD-003", "BUD-004"])
        chip = next(c.send_text for c in result.clarification.options
                    if "tied and untied components" in c.send_text)
        self.assertIn("5th State Finance Commission (SFC) and Own Funds", chip)
        named = subject_reader.named_subjects(
            chip, router_slot_types("BUD-003"), _validator())
        self.assertEqual({m.value for m in named["scheme"]},
                         {"5TH STATE FINANCE COMMISSION", "Own Funds"})

    def test_display_names_read_back_as_the_same_values(self):
        from query_router import subject_reader
        from query_router.zones import DISPLAY_NAMES
        slot_type = router_slot_types("BUD-002")
        for label, shown in DISPLAY_NAMES.items():
            if label.startswith("WORK") or label == "UNDER APPROVAL":
                continue
            named = subject_reader.named_subjects(f"funds from {shown} in 2024-25",
                                                  slot_type, _validator())
            self.assertEqual({m.value for m in named["scheme"]}, {label}, shown)


def router_slot_types(qid):
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    return router._template_slot_types(T[qid])


# ── T7 ────────────────────────────────────────────────────────────────────────

_REPLAY = _REPO / "handoffs" / "WP6c_eval1_replay.jsonl"
_RAW_GROUP = re.compile(r"\((?:total|fiscal_year|district|block|gp|theme|focus_area|status|"
                        r"scheme|plan_type)\)")
_BARE_NUMBER = re.compile(r"\(\d+\)")
_RAW_SCHEMES = ("5TH STATE FINANCE COMMISSION", "XV Finance Commission", "4TH STATE FINANCE SCHEME")
_NOUNLESS = {"Main", "Supplementary", "Tied", "Untied", "Other"}


def rerender(record: dict):
    """(entities, the echo) for a recorded served row, re-served offline from its
    template and bound values — the path `_serve_query_id` takes today."""
    from query_router import breakdown, router, threshold_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    qid = record["query_id"]
    template = T[qid]
    raw = {e["slot"]: (e.get("values") or e.get("value")) for e in record.get("entities") or []}
    entities, clarify = router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), raw, _validator(),
        record["q"], "n", time.monotonic(),
        optional=router.optional_slots(template["param_slots"]),
        defaults=router.slot_defaults(template["param_slots"]),
        list_slots=router._list_slots(template["param_slots"]),
        splits=breakdown.slots_the_statement_splits(template),
        numeric=threshold_reply.numeric_meta(template["param_slots"]),
        check_direction=False)
    if clarify is not None:
        return None, None
    result = router._serve_query_id(
        qid, entities, None, user_query=record["q"], normalized=record["q"],
        start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
        template_map=T, dashboard_questions={}, start_date=None, end_date=None)
    return entities, result.query_description


def echo_problems(echo: str, entities) -> list[str]:
    """Everything T7 says an echo must not do, for one echo."""
    from query_router.zones import _PLAN_TYPE_WORDS, display_label
    problems = []
    if _RAW_GROUP.search(echo):
        problems.append("raw breakdown value")
    if _BARE_NUMBER.search(echo):
        problems.append("bare number")
    if any(label in echo for label in _RAW_SCHEMES):
        problems.append("raw scheme label")
    for bracket in re.findall(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", echo):
        if any(part.strip() in _NOUNLESS for part in bracket.split(";")):
            problems.append(f"noun-less value ({bracket})")
    lowered = echo.lower()
    for e in entities:
        if e.slot_name in ("group_by", "top_n", "threshold", "date_range", "gp_name"):
            continue
        for value in (e.values or [e.resolved_value]):
            shown = _PLAN_TYPE_WORDS.get(value) if e.slot_name == "plan_type" else \
                display_label(value)
            if str(shown).lower().strip() not in lowered:
                problems.append(f"{e.slot_name}={value!r} not named")
    return problems


@_needs_db
class T7EchoTests(unittest.TestCase):

    def test_the_worst_case_reads_as_english(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.zones import resolved_question
        echo = resolved_question(
            T["STS-003"]["abstract_question"],
            {"date_range": ["2024-2025", "2025-2026"], "status": "WORK ONGOING",
             "focus_area": "Roads", "group_by": "fiscal_year"},
            {"block_name": "all blocks"})
        self.assertEqual(echo, "How many activities in all blocks are in ongoing status for "
                               "2024-2025 and 2025-2026 (Roads focus area)?")

    def test_filters_share_one_bracket_with_their_nouns(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.zones import resolved_question
        echo = resolved_question(
            T["BUD-006"]["abstract_question"],
            {"date_range": "2024-2025", "focus_area": "Sanitation", "plan_type": "Main",
             "tied_untied": ["Tied", "Untied"], "status": "UNDER APPROVAL",
             "scheme": ["5TH STATE FINANCE COMMISSION", "XV Finance Commission"],
             "district_name": "Ganjam"}, {})
        self.assertTrue(echo.endswith(
            "in 2024-2025 (Sanitation focus area; main GPDP; tied and untied funds; "
            "work awaiting approval; 5th State Finance Commission (SFC) and 15th Finance "
            "Commission (CFC); Ganjam district)?"), echo)

    def test_the_list_length_reads_as_a_length(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        from query_router.zones import resolved_question
        q9 = T["IMP-009"]["abstract_question"]
        cases = (
            ("IMP-009", {"top_n": "10", "threshold": "1"}, "(bottom 10)?"),
            ("IMP-009", {"top_n": "10", "threshold": "50"},
             "(bottom 10, focus areas with at least 50 activities)?"),
            ("IMP-009", {"top_n": "3", "threshold": "1"}, "(bottom 3)?"),
            ("EXP-015", {"top_n": "10"}, "(top 10)?"),
            ("EXP-015", {"top_n": "1"}, "(the highest)?"),
            ("EXP-016", {"top_n": "1"}, "(the lowest)?"),
        )
        for qid, fill, tail in cases:
            echo = resolved_question(T[qid]["abstract_question"],
                                     {"date_range": "2025-2026", **fill}, {})
            self.assertTrue(echo.endswith(tail), (qid, echo))
            self.assertNotIn("(1)", echo)
        self.assertIn("{date_range}", q9)

    def test_the_served_echo_and_its_bound_values(self):
        """Display is not binding: the SQL parameters are byte-identical to what
        the values bind, whatever the echo says."""
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        question = "Budget for sanitation in main GPDPs of Ganjam under SFC and Own Funds 2024-25"
        entities, clarify, result = _answer("BUD-006", question, {
            "scheme": ["SFC", "Own Funds"], "district_name": "Ganjam", **{"date_range": "2024-2025"}})
        self.assertIsNone(clarify)
        self.assertEqual(echo_problems(result.query_description, entities), [])
        params = {e.slot_name: (e.values if e.values else e.resolved_value) for e in entities}
        self.assertEqual(sorted(params["scheme"]), ["5TH STATE FINANCE COMMISSION", "Own Funds"])
        self.assertEqual(params["plan_type"], "Main")
        self.assertEqual(params["focus_area"], "Sanitation")
        bound = router.bind_for_template(T["BUD-006"], params, context="x", person_ids={
            e.slot_name: e.resolved_code for e in entities if e.resolved_code})
        self.assertEqual(sorted(bound["scheme"]), ["5TH STATE FINANCE COMMISSION", "Own Funds"])

    @unittest.skipUnless(_REPLAY.exists(), f"no WP-6c replay at {_REPLAY}")
    def test_every_served_eval1_echo_re_renders_clean(self):
        records = [json.loads(line) for line in _REPLAY.read_text(encoding="utf-8").splitlines()]
        served = [r for r in records if r.get("query_id") and r.get("tier") == "tier2"]
        self.assertGreater(len(served), 280)
        bad = {}
        for record in served:
            entities, echo = rerender(record)
            if echo is None:
                bad[record["n"]] = ["asked on re-render"]
                continue
            problems = echo_problems(echo, entities)
            if problems:
                bad[record["n"]] = problems + [echo]
        self.assertEqual(bad, {})


# ── T8 ────────────────────────────────────────────────────────────────────────

_PILOT = _REPO / "handoffs" / "WP6d_pilot_replay"


@unittest.skipUnless(_PILOT.with_suffix(".jsonl").exists(),
                     f"no WP-6d pilot replay at {_PILOT} (set PRDW_REPO from a mirror)")
class T8GraderTests(unittest.TestCase):

    def test_the_fifth_group_grades_as_committed(self):
        import sys
        sys.path.insert(0, str(_BACKEND))
        import grade_eval1
        mine = {r["eval_row"]: r["outcome"]
                for r in grade_eval1.grade_file(_PILOT.with_suffix(".jsonl"))}
        theirs = {int(r["eval_row"]): r["outcome"]
                  for r in grade_eval1.read_graded(_PILOT.with_suffix(".csv"))}
        self.assertEqual(mine, theirs)
        self.assertEqual(sum(1 for n in mine if n >= 1023), 22)

    def test_a_chip_tap_row_sends_the_chip(self):
        import sys
        sys.path.insert(0, str(_BACKEND))
        import run_custom_eval
        record = {"clarification": {"options": [
            {"label": "How many activities are planned under a focus area in X block?",
             "send_text": "A"},
            {"label": "How many activities are planned under each GPDP theme in X block?",
             "send_text": "B"}]}}
        self.assertEqual(run_custom_eval._pick_chip(record, "each GPDP theme"), "B")
        self.assertIsNone(run_custom_eval._pick_chip(record, "nothing like this"))


if __name__ == "__main__":
    unittest.main()

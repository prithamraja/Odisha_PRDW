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


if __name__ == "__main__":
    unittest.main()

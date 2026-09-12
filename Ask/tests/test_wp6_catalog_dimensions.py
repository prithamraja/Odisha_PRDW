"""WP-6 — catalogue dimensions: what each task promised, pinned.

Grouped by task so a failure names the promise it broke:

    T0  the catalogue file is the source of truth; its derived parts are the
        script's, and the script's slot-type table is the validator's
    T1  `plan_type` is a column of the three activity views, a validated
        categorical, and never defaulted
"""
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

_STATE: dict = {}


def _adapter():
    """The sample database with its views, or None — memoised."""
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


def tearDownModule():
    adapter = _STATE.get("adapter")
    if adapter is not None:
        try:
            adapter.close()
        except Exception:                                    # pragma: no cover
            pass


class T0SourceOfTruthTests(unittest.TestCase):

    def test_no_tool_reads_the_workbook(self):
        """The workbook is archived; the build and the gates must not need it.
        (`import_workbook.py` is the one exception, and it only creates.)"""
        offenders = []
        for path in _BACKEND.rglob("*.py"):
            if ".venv" in path.parts or path.name in ("import_workbook.py",
                                                      "test_wp6_catalog_dimensions.py"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "AI_Chatbot_Questions.xlsx" in text and "openpyxl" in text:
                offenders.append(str(path.relative_to(_BACKEND)))
        self.assertEqual(offenders, [])

    def test_the_script_and_the_validator_agree_on_slot_types(self):
        from query_router.entity_validator import PARAM_ENTITY_TYPES as runtime
        from tools.derive_catalog import PARAM_ENTITY_TYPES as derive
        self.assertEqual(derive, runtime)

    def test_the_derived_parts_are_in_step(self):
        """`derive_catalog --check`, in-process: a hand edit to a derived line,
        or a slot that disagrees with its SQL, fails here as well as at gate 3."""
        from tools import derive_catalog as dc
        outputs, templates, _, _ = dc.derive_all()
        self.assertEqual(dc.contract_problems(templates), [])
        for path, source in outputs.items():
            with self.subTest(path=path.name):
                self.assertEqual(path.read_text(encoding="utf-8"), source)


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T1PlanTypeTests(unittest.TestCase):

    def test_plan_type_is_a_column_of_the_three_activity_views(self):
        adapter = _adapter()
        for view in ("v_activity", "v_asset", "v_progress"):
            with self.subTest(view=view):
                total, typed = adapter.execute(
                    f"SELECT COUNT(*), COUNT(plan_type) FROM {view}").fetchone()
                self.assertGreater(total, 0)
                self.assertEqual(typed, total, "every row inherits its plan's type")

    def test_the_join_adds_no_rows(self):
        adapter = _adapter()
        views = adapter.execute("SELECT COUNT(*) FROM v_activity").fetchone()[0]
        base = adapter.execute("SELECT COUNT(*) FROM planned_activity").fetchone()[0]
        self.assertEqual(views, base)

    def test_plan_type_validates_from_the_database(self):
        from query_router.entity_validator import EntityValidator
        validator = EntityValidator(_adapter())
        self.assertEqual(sorted(validator.registry_values("plan_type")),
                         ["Main", "Supplementary"])
        for said, stored in (("main GPDP", "Main"), ("primary GPDPs", "Main"),
                             ("supplementary plan", "Supplementary")):
            with self.subTest(said=said):
                self.assertEqual(validator.validate(said, "plan_type").resolved_value,
                                 stored)

    def test_plan_type_is_never_defaulted(self):
        """Absent means BOTH plan types — the signed-off row count (D18)."""
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG
        from tools.derive_catalog import DEFAULTED_SLOTS, UNDEFAULTED_SLOTS
        self.assertIn("plan_type", UNDEFAULTED_SLOTS)
        self.assertNotIn("plan_type", DEFAULTED_SLOTS)
        self.assertNotIn("plan_type", router._DEFAULT_ENTITY_VALUES)
        for qid, entry in TEMPLATE_CATALOG.items():
            for slot in entry["param_slots"]:
                if slot["name"] == "plan_type":
                    with self.subTest(qid=qid):
                        self.assertNotIn("default", slot)


UNIVERSAL = {"plan_type": "plan_type", "status": "status_label",
             "focus_area": "focus_area_name", "theme": "theme",
             "scheme": "scheme_name", "tied_untied": "tied_untied"}


class T2UniversalSlotStructureTests(unittest.TestCase):
    """What M1 and its hand edits promised, checked on the file."""

    def test_no_sbm_template_gained_a_universal_slot(self):
        """Constraint 6: an SBM template defines its subject by a keyword
        regex; a focus-area predicate would silently narrow it."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        sbm = [qid for qid in T if qid.startswith("SBM-")]
        self.assertEqual(len(sbm), 85)
        for qid in sbm:
            with self.subTest(qid=qid):
                names = {s["name"] for s in T[qid]["param_slots"]}
                self.assertFalse(names & {"plan_type", "tied_untied", "status",
                                          "theme", "scheme"},
                                 "an SBM template carries a universal slot")

    def test_every_new_filter_is_the_d2_idiom(self):
        """`($slot IS NULL OR alias.column = $slot)` and nothing cleverer, so an
        absent slot is exactly the old statement."""
        import re
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid, entry in T.items():
            for slot in entry["param_slots"]:
                if slot["name"] not in ("plan_type", "tied_untied"):
                    continue
                with self.subTest(qid=qid, slot=slot["name"]):
                    self.assertTrue(slot.get("optional"))
                    self.assertNotIn("default", slot)
                    col = UNIVERSAL[slot["name"]]
                    idiom = re.compile(r"\(\$%s IS NULL OR \w+\.%s = \$%s\)"
                                       % (slot["name"], col, slot["name"]))
                    self.assertRegex(entry["sql_template"], idiom)

    def test_a_statement_that_owns_a_dimension_keeps_it(self):
        """STS-003 already filters on $status; PLU-004 fixes the plan type as
        'Supplementary'. Neither may gain a second predicate on the column."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        self.assertEqual(T["STS-003"]["sql_template"].count("v.status_label ="), 1)
        self.assertNotIn("plan_type", {s["name"] for s in T["PLU-004"]["param_slots"]})

    def test_the_no_data_in_any_module_questions_stay_unfiltered(self):
        """ALR-012/013 ask for GPs with no data in ANY module; an activity-side
        filter would narrow one module of three and answer something else."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid in ("ALR-012", "ALR-013"):
            with self.subTest(qid=qid):
                names = {s["name"] for s in T[qid]["param_slots"]}
                self.assertFalse(names & set(UNIVERSAL))

    def test_the_new_slots_are_retrievable(self):
        """A universal slot no paraphrase mentions is invisible to retrieval."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        lines = " || ".join(T["PLN-024"]["paraphrases"]).lower()
        for phrase in ("main gpdp", "ongoing activities", "tied grants"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lines)
        self.assertNotIn("sector", lines, "operator ruling: sector is not assumed")


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T2UniversalSlotExecutionTests(unittest.TestCase):
    """Binding a universal slot must actually filter, and filter correctly."""

    def _total(self, qid, column, **values):
        """SUM(column) over the template's result, computed by the database."""
        from query_router.template_catalog import bind
        sql, params = bind(qid, {"date_range": "2024-2025", **values})
        return _adapter().execute(
            f"SELECT COALESCE(SUM({column}), 0) FROM ({sql}) AS answer", params
        ).fetchone()[0]

    def test_plan_type_narrows_activities_to_the_main_plan(self):
        adapter = _adapter()
        want = adapter.execute(
            "SELECT COUNT(*) FROM planned_activity a JOIN plan p USING (plan_code) "
            "WHERE a.fiscal_year = '2024-2025' AND p.plan_type = 'Main'").fetchone()[0]
        got = self._total("PLN-024", "planned_activities", plan_type="Main")
        self.assertEqual(got, want)
        self.assertLess(got, self._total("PLN-024", "planned_activities"))

    def test_focus_area_and_status_compose(self):
        """Eval_1: 'road construction activities in progress'."""
        adapter = _adapter()
        want = adapter.execute(
            "SELECT COUNT(*) FROM v_activity WHERE fiscal_year = '2024-2025' "
            "AND status_label = 'WORK ONGOING' AND focus_area_name = 'Roads'").fetchone()[0]
        self.assertEqual(self._total("STS-003", "activities", status="WORK ONGOING",
                                     focus_area="Roads"), want)

    def test_tied_untied_validates(self):
        from query_router.entity_validator import EntityValidator
        validator = EntityValidator(_adapter())
        self.assertEqual(sorted(validator.registry_values("tied_untied")),
                         ["Other", "Tied", "Untied"])
        for said, stored in (("tied grants", "Tied"), ("basic grant", "Untied"),
                             ("untied funds", "Untied")):
            with self.subTest(said=said):
                self.assertEqual(validator.validate(said, "tied_untied").resolved_value,
                                 stored)


if __name__ == "__main__":
    unittest.main()

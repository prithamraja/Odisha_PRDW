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


if __name__ == "__main__":
    unittest.main()

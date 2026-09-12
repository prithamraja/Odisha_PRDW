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
                    name = slot["name"]
                    scalar = re.compile(r"\(\$%s\s+IS NULL OR \w+\.%s\s*= \$%s\)"
                                        % (name, col, name))
                    # WP-6 T4 rewrote the same idiom to bind a LIST; the slot's
                    # flag and the form it is written in must agree.
                    listed = re.compile(
                        r"\(\$%s\s+IS NULL OR \w+\.%s\s*IN \(SELECT UNNEST\(\$%s\)\)\)"
                        % (name, col, name))
                    form = listed if slot.get("list") else scalar
                    self.assertRegex(entry["sql_template"], form)

    def test_a_statement_that_owns_a_dimension_keeps_it(self):
        """STS-003 already filters on $status; PLU-004 fixes the plan type as
        'Supplementary'. Neither may gain a second predicate on the column."""
        import re
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        status = re.findall(r"v\.status_label\s*(?:=|IN)", T["STS-003"]["sql_template"])
        self.assertEqual(len(status), 1, "one status predicate, not two")
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


class T3BreakdownReaderTests(unittest.TestCase):
    """The `$group_by` phrase table, on Eval_1's own wordings."""

    CASES = (
        ("Give a district-wise summary of asset creation for 2024 to 2025.", "district"),
        ("What is the district-level summary of assets created in 2024 to 2025?", "district"),
        ("Show asset creation totals across all districts for 2024 to 2025.", "district"),
        ("What is the total estimated cost of all planned activities state-wide "
         "for 2024 to 2026?", "total"),
        ("What is the total unspent balance across all GPs in the state for 2020 "
         "to 2021?", "total"),
        ("Which GPs have planned zero-cost activities for 2024 to 2025?", "gp"),
        ("What is the total allocation for the 9 Sankalp themes state-wide for "
         "2024 to 2025?", "theme"),
        ("What is the thematic distribution of planned activities for 2024 to 2025?",
         "theme"),
        ("Categorize the planned activities by their respective themes for 2024 to "
         "2025.", "theme"),
        ("What is the total actual expenditure incurred by each GP in 2024-25?", "gp"),
        ("Year-wise expenditure of Andhrua", "fiscal_year"),
        ("How many activities are in the main vs supplementary plans in 2024-25?",
         "plan_type"),
        ("How many activities are in progress during 2024 to 2025?", None),
        ("How many activities are planned under the sanitation sector for 2024 to "
         "2025?", None),
    )

    def test_eval1_wordings(self):
        from query_router.breakdown import group_by_from_text
        for question, want in self.CASES:
            with self.subTest(question=question):
                self.assertEqual(group_by_from_text(question), want)

    def test_one_whitelist_in_three_places(self):
        from query_router.breakdown import GROUP_BY_VALUES as runtime
        from query_router.entity_validator import REGISTRY_CONFIG
        from tools.derive_catalog import GROUP_BY_VALUES as derive
        self.assertEqual(runtime, derive)
        self.assertEqual(runtime, REGISTRY_CONFIG["group_by"]["values"])

    def test_no_statement_lists_a_value_outside_the_whitelist(self):
        """T7.3(b): a `$group_by` value outside the whitelist in any statement."""
        import re
        from query_router.breakdown import GROUP_BY_VALUES
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        carriers = 0
        for qid, entry in T.items():
            case = re.search(r"CASE\s+\$group_by\b(.*?)\bEND\s+AS\s+group_label",
                             entry["sql_template"], re.S)
            if case:
                carriers += 1
                with self.subTest(qid=qid):
                    self.assertLessEqual(set(re.findall(r"WHEN\s+'(\w+)'", case.group(1))),
                                         set(GROUP_BY_VALUES))
        self.assertGreater(carriers, 100)

    def test_reshape_names_the_column_it_holds(self):
        from query_router.breakdown import reshape
        template = {"sql_template": (
            "SELECT CASE $group_by\n  WHEN 'district' THEN v.district_name\n"
            "  WHEN 'total' THEN 'All'\n  ELSE v.theme  -- absent: theme\n"
            "END AS group_label,\n CASE WHEN $group_by IS NULL THEN v.block_name "
            "END AS block_name, COUNT(*) AS n FROM v_activity v GROUP BY 1, 2")}
        rows = [{"group_label": "Theme 1", "block_name": "B", "n": 3}]
        self.assertEqual(reshape(template, None, rows),
                         [{"theme": "Theme 1", "block_name": "B", "n": 3}])
        self.assertEqual(reshape(template, "district", rows),
                         [{"district_name": "Theme 1", "n": 3}])
        self.assertEqual(reshape(template, "total", rows), [{"n": 3}])


class T3SectorTests(unittest.TestCase):
    """Operator ruling 2026-09-12: 'sector' as the breakdown is asked about."""

    NAMES = ["Drinking water", "Sanitation", "water", "sanitation", "road"]

    def test_sector_as_the_breakdown_asks(self):
        from query_router.breakdown import sector_clarification
        asked = sector_clarification(
            "Which sector has the best activity completion rate for 2024 to 2026?",
            self.NAMES)
        self.assertIsNotNone(asked)
        prompt, chips = asked
        self.assertIn("focus area", prompt)
        self.assertEqual([label for label, _ in chips], ["By focus area", "By LSDG theme"])
        self.assertIn("Which focus area has", chips[0][1])
        self.assertIn("Which LSDG theme has", chips[1][1])

    def test_a_named_value_answers(self):
        from query_router.breakdown import sector_clarification
        for question in (
                "Show the breakdown of tied fund expenditure by sector (water vs "
                "sanitation) for 2025 to 2026.",
                "How many activities are planned under the sanitation sector for 2024 "
                "to 2025?"):
            with self.subTest(question=question):
                self.assertIsNone(sector_clarification(question, self.NAMES))


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T3BreakdownExecutionTests(unittest.TestCase):

    def _binds(self, qid, sample):
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        validator = EntityValidator(_adapter())
        values = {}
        for slot in T[qid]["param_slots"]:
            value = sample.get(slot["name"])
            if value is not None and slot.get("bind") == "code":
                value = validator.validate(str(value), slot["entity_type"]).resolved_code
            values[slot["name"]] = value
        return values

    def _count(self, qid, values, wrap="COUNT(*)"):
        from query_router.template_catalog import bind
        sql, params = bind(qid, values)
        return _adapter().execute(f"SELECT {wrap} FROM ({sql}) AS answer", params).fetchone()

    def test_every_retired_id_is_reproduced_by_its_survivor(self):
        import json
        retired = json.loads((_BACKEND / "tests" / "data" / "retired_templates.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(sorted(retired), ["BUD-018", "EXP-025", "PLN-050", "PLN-051"])
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid, record in retired.items():
            with self.subTest(retired=qid, survivor=record["survivor"]):
                self.assertNotIn(qid, T)
                values = self._binds(record["survivor"], record["params"])
                values["group_by"] = record["group_by"]
                self.assertEqual(self._count(record["survivor"], values)[0], record["rows"])

    def test_ast001_by_district_sums_to_the_ungrouped_total(self):
        """The brief's own proof for T3."""
        base = {"date_range": "2024-2025"}
        per_gp = self._count("AST-001", base, "COUNT(*), SUM(asset_rows)")
        per_district = self._count("AST-001", {**base, "group_by": "district"},
                                   "COUNT(*), SUM(asset_rows)")
        districts = _adapter().execute(
            "SELECT COUNT(DISTINCT district_name) FROM v_asset "
            "WHERE fiscal_year = '2024-2025'").fetchone()[0]
        self.assertEqual(per_district[0], districts)
        self.assertEqual(per_district[1], per_gp[1])
        self.assertGreater(per_gp[0], per_district[0])

    def test_total_is_one_row(self):
        rows = self._count("BUD-006", {"date_range": "2024-2025", "group_by": "total"},
                           "COUNT(*), SUM(planned_cost)")
        themes = self._count("BUD-006", {"date_range": "2024-2025"},
                             "COUNT(*), SUM(planned_cost)")
        self.assertEqual(rows[0], 1)
        self.assertEqual(rows[1], themes[1])
        self.assertGreater(themes[0], 1)


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T3RouterTests(unittest.TestCase):
    """The breakdown through the real router functions, with no LLM call."""

    @classmethod
    def setUpClass(cls):
        from query_router.entity_validator import EntityValidator
        cls.validator = EntityValidator(_adapter())

    def test_the_extractor_is_never_asked_for_a_breakdown(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        asked: list[str] = []

        def stub(query, slots, client, intent=None):
            asked.extend(slots)
            return {s: None for s in slots}

        real, router.extract_entities = router.extract_entities, stub
        try:
            raw = router._extract_slot_values(
                "Give a district-wise summary of asset creation for 2024-25",
                router._template_slot_types(T["AST-001"]), object(),
                validator=self.validator)
        finally:
            router.extract_entities = real
        self.assertEqual(raw.get("group_by"), "district")
        self.assertNotIn("group_by", asked)

    def _serve(self, qid, **values):
        import time
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        types = router._template_slot_types(T[qid])
        entities = []
        for slot, value in values.items():
            entity = self.validator.validate(value, types[slot])
            entity.slot_name = slot
            entities.append(entity)
        return router._serve_query_id(
            qid, entities, None, user_query="q", normalized="q",
            start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
            template_map=T, dashboard_questions={}, start_date=None, end_date=None)

    def test_a_district_breakdown_reads_as_districts(self):
        result = self._serve("AST-001", date_range="2024-2025", group_by="district")
        self.assertTrue(result.result)
        row = result.result[0]
        self.assertIn("district_name", row)
        self.assertNotIn("group_label", row)
        self.assertNotIn("block_name", row, "the blanked finer column is dropped")
        self.assertIn("broken down by district", result.query_description)

    def test_no_breakdown_reads_exactly_as_before(self):
        row = self._serve("AST-001", date_range="2024-2025").result[0]
        self.assertLessEqual({"gp_name", "block_name"}, set(row))
        self.assertNotIn("group_label", row)

    def test_a_breakdown_the_statement_cannot_honour_is_dropped(self):
        """v_asset carries no scheme: 'scheme-wise assets' must not answer with
        the default breakdown while claiming a scheme one."""
        result = self._serve("AST-001", date_range="2024-2025", group_by="scheme")
        self.assertIn("gp_name", result.result[0])
        self.assertNotIn("broken down", result.query_description or "")

    def test_which_sector_is_asked_before_retrieval(self):
        import time
        from query_router import router

        class NoRetrieval:
            def retrieve_scored(self, query, k):
                raise AssertionError("retrieval must not run before the question")

        result = router._route_vector(
            "Which sector has the best activity completion rate for 2024 to 2026?",
            "n", time.monotonic(), validator=self.validator, openai_client=object(),
            retriever=NoRetrieval(), cache_conn=None, dashboard_results={},
            template_map={}, dashboard_questions={}, start_date=None, end_date=None)
        self.assertEqual(result.clarification.reason, "ambiguous_term")
        self.assertEqual([c.label for c in result.clarification.options],
                         ["By focus area", "By LSDG theme"])


class T4YearSpanTests(unittest.TestCase):
    """"2024 to 2026" is a span of fiscal years, and "2024 to 2025" is one."""

    YEARS = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025",
             "2025-2026"]

    def test_spans(self):
        from query_router.date_phrase import resolve_fiscal_years
        for question, want in (
                ("What is the total unspent balance for 2024 to 2025?", ["2024-2025"]),
                ("Compare tied fund spending for 2024 to 2026.",
                 ["2024-2025", "2025-2026"]),
                ("activities planned for 2022 through 2025",
                 ["2022-2023", "2023-2024", "2024-2025"]),
                ("GPDP uploads in FY 2025-26", ["2025-2026"]),
                ("2024-25 vs 2023-24", ["2023-2024", "2024-2025"])):
            with self.subTest(question=question):
                self.assertEqual(resolve_fiscal_years(question, self.YEARS), want)

    def test_the_reader_refuses_a_span_the_data_does_not_hold(self):
        """Whole-or-nothing: answering about the loaded half of "2019 to 2022"
        would be a smaller answer wearing the question's words."""
        from query_router import router
        from types import SimpleNamespace
        validator = SimpleNamespace(fiscal_years=lambda: self.YEARS)
        self.assertEqual(
            router._fiscal_years_from_text("spend for 2019 to 2022", validator), [])
        self.assertEqual(
            router._fiscal_years_from_text("spend for 2021 to 2023", validator),
            ["2021-2022", "2022-2023"])


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T4ListFilterTests(unittest.TestCase):
    """The brief's own two proofs, executed."""

    def _rows(self, qid, values):
        from query_router.template_catalog import bind
        sql, params = bind(qid, values)
        return _adapter().execute(sql, params).fetchall()

    def test_a_single_value_still_binds(self):
        """Every Test Report sample is a scalar; the binder wraps it."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T, bind
        _, params = bind("EXP-009", {"date_range": "2024-2025",
                                     "focus_area": "Sanitation"})
        self.assertEqual(params["focus_area"], ["Sanitation"])
        self.assertEqual(params["date_range"], ["2024-2025"])
        self.assertTrue(any(s["name"] == "focus_area" and s.get("list")
                            for s in T["EXP-009"]["param_slots"]))

    def test_exp009_two_values_equal_two_scalar_calls(self):
        base = {"date_range": "2024-2025", "tied_untied": "Tied"}
        both = self._rows("EXP-009", {**base,
                                      "focus_area": ["Drinking water", "Sanitation"]})
        singles = [self._rows("EXP-009", {**base, "focus_area": one})
                   for one in ("Drinking water", "Sanitation")]
        self.assertEqual(len(both), sum(len(rows) for rows in singles))
        # column 4 is actual_expenditure; the two values are never summed into one
        self.assertEqual(sorted(row[4] for row in both),
                         sorted(row[4] for rows in singles for row in rows))

    def test_pln001_a_two_year_span_equals_the_two_years(self):
        span = self._rows("PLN-001", {"date_range": ["2024-2025", "2025-2026"],
                                      "group_by": "fiscal_year"})
        singles = [self._rows("PLN-001", {"date_range": year})[0][1]
                   for year in ("2024-2025", "2025-2026")]
        self.assertEqual(len(span), 2)
        self.assertEqual(sum(row[1] for row in span), sum(singles))

    def test_one_bad_element_refuses_the_whole_list(self):
        """Never a silent partial bind: "water and Atlantis" must not answer
        about water alone."""
        from query_router import router
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        validator = EntityValidator(_adapter())
        slot_type = router._template_slot_types(T["EXP-009"])
        validated, clarify = router._fill_slots_or_clarify(
            "EXP-009", slot_type,
            {"date_range": "2024-2025", "focus_area": ["Drinking water", "Atlantis"]},
            validator, "q", "q", 0.0,
            optional=router.optional_slots(T["EXP-009"]["param_slots"]),
            list_slots=router._list_slots(T["EXP-009"]["param_slots"]))
        self.assertIsNotNone(clarify)
        self.assertFalse(any(e.slot_name == "focus_area" for e in validated))

    def test_a_one_value_at_a_time_statement_asks(self):
        """PLN-049's focus area is its subject and stays scalar, so two values
        are a question, not a filter."""
        from query_router import router
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        validator = EntityValidator(_adapter())
        slot_type = router._template_slot_types(T["PLN-049"])
        validated, clarify = router._fill_slots_or_clarify(
            "PLN-049", slot_type,
            {"date_range": "2024-2025", "focus_area": ["Drinking water", "Sanitation"]},
            validator, "q", "q", 0.0,
            optional=router.optional_slots(T["PLN-049"]["param_slots"]),
            list_slots=router._list_slots(T["PLN-049"]["param_slots"]))
        self.assertIsNotNone(clarify)
        self.assertEqual([c.label for c in clarify.clarification.options],
                         ["Drinking water", "Sanitation"])
        self.assertEqual(clarify.pending.missing_slot, "focus_area")

    def test_a_comparison_is_grouped_rather_than_summed(self):
        """PLN-024 counts per theme; two focus areas must land in two rows."""
        import time
        from query_router import router
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        validator = EntityValidator(_adapter())
        year = validator.validate("2024-2025", "fiscal_year")
        year.slot_name = "date_range"
        focus = validator.validate("Drinking water", "focus_area")
        focus.slot_name = "focus_area"
        focus.values = ["Drinking water", "Sanitation"]
        focus.resolved_value = "Drinking water, Sanitation"
        result = router._serve_query_id(
            "PLN-024", [year, focus], None, user_query="q", normalized="q",
            start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
            template_map=T, dashboard_questions={}, start_date=None, end_date=None)
        self.assertEqual(len(result.result), 2)
        self.assertEqual({row["focus_area_name"] for row in result.result},
                         {"Drinking water", "Sanitation"})
        self.assertIn("broken down by focus area", result.query_description)
        self.assertIn("Drinking water and Sanitation", result.query_description)


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T5NewTemplateAndRelaxedSlotsTests(unittest.TestCase):
    """The one genuinely new question, and the two slots the operator relaxed."""

    def _bind_rows(self, qid, values):
        from query_router.template_catalog import bind
        sql, params = bind(qid, values)
        return _adapter().execute(sql, params).fetchall()

    def test_phy006_answers_the_eval1_question(self):
        """Gap A: "which GPs have expenditure recorded but zero physical
        progress". Roster-shaped, so the grain is panchayats, not activity rows.
        """
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        entry = T["PHY-006"]
        self.assertIn("FROM gram_panchayat g", entry["sql_template"])
        self.assertIn("LEFT JOIN v_activity", entry["sql_template"])
        self.assertEqual(entry["answerable"], "Partial")
        self.assertIn("photo/GPS evidence", entry["caveat"])

        rows = self._bind_rows("PHY-006", {"date_range": "2024-2025"})
        want = _adapter().execute(
            "SELECT COUNT(DISTINCT gp_lgd_code) FROM v_activity "
            "WHERE fiscal_year = '2024-2025' AND COALESCE(total_expenditure,0) > 0 "
            "AND has_progress_evidence = 0").fetchone()[0]
        self.assertEqual(len(rows), want)
        self.assertGreater(len(rows), 0)

    def test_pln031_answers_across_all_themes(self):
        """Operator ruling 2026-09-12: the theme becomes optional, so "which GP
        planned the most activities?" no longer asks which theme."""
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        theme = next(s for s in T["PLN-031"]["param_slots"] if s["name"] == "theme")
        self.assertTrue(theme.get("optional"))
        rows = self._bind_rows("PLN-031", {"date_range": "2024-2025", "top_n": "1"})
        want = _adapter().execute(
            "SELECT COUNT(*) FROM v_activity WHERE fiscal_year = '2024-2025' "
            "GROUP BY gp_lgd_code ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], want, "the top GP's own activity count")

    def test_pln032_with_no_theme_means_no_theme_at_all(self):
        """With the theme absent it lists the GPs with nothing under ANY LSDG
        theme — activities whose focus area maps to no theme do not count as
        theme planning, which is what 'Unmapped theme' means."""
        rows = self._bind_rows("PLN-032", {"date_range": "2024-2025"})
        want = _adapter().execute(
            "SELECT COUNT(*) FROM gram_panchayat g WHERE NOT EXISTS ("
            "SELECT 1 FROM v_activity v WHERE v.gp_lgd_code = g.gp_lgd_code "
            "AND v.fiscal_year = '2024-2025' AND v.theme <> 'Unmapped theme')"
        ).fetchone()[0]
        self.assertEqual(len(rows), want)

    def test_a_named_theme_still_narrows_pln032(self):
        both = len(self._bind_rows("PLN-032", {"date_range": "2024-2025"}))
        one = len(self._bind_rows(
            "PLN-032", {"date_range": "2024-2025",
                        "theme": "Theme 4 - Water Sufficient Village"}))
        self.assertGreaterEqual(one, both)


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T5LossyAliasTests(unittest.TestCase):
    """A reading the database cannot quite express says so in the answer."""

    @classmethod
    def setUpClass(cls):
        from query_router.entity_validator import EntityValidator
        cls.validator = EntityValidator(_adapter())

    def _serve(self, qid, **values):
        import time
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        types = router._template_slot_types(T[qid])
        entities = []
        for slot, value in values.items():
            entity = self.validator.validate(value, types[slot])
            entity.slot_name = slot
            entities.append(entity)
        return router._serve_query_id(
            qid, entities, None, user_query="q", normalized="q",
            start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
            template_map=T, dashboard_questions={}, start_date=None, end_date=None)

    def test_swachh_bharat_answers_with_its_caveat(self):
        result = self._serve("STS-003", date_range="2024-2025",
                             focus_area="Swachh Bharat", status="WORK COMPLETED")
        self.assertIn("Sanitation focus area", result.caveat)
        self.assertIn("do not record SBM as a scheme", result.caveat)

    def test_the_templates_own_caveat_survives_beside_it(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        own = (T["STS-003"].get("caveat") or "").strip()
        result = self._serve("STS-003", date_range="2024-2025",
                             focus_area="Swachh Bharat")
        self.assertTrue(own and own in result.caveat)

    def test_the_plain_value_owes_nothing(self):
        result = self._serve("STS-003", date_range="2024-2025",
                             focus_area="Sanitation")
        self.assertNotIn("read here as", result.caveat or "")

    def test_sankalp_themes_answer_without_a_caveat(self):
        """Operator ruling 2026-09-12: answer from the six themes present, no
        warning. Nothing may quietly turn the collective name into one theme."""
        from query_router.entity_validator import LOSSY_ALIASES, REGISTRY_CONFIG
        aliases = REGISTRY_CONFIG["theme"]["aliases"]
        self.assertNotIn("sankalp themes", aliases)
        self.assertFalse([k for k in LOSSY_ALIASES if k[0] == "theme"])


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T7ReplayFindingsTests(unittest.TestCase):
    """What the first 3x replay found, which nothing else did."""

    @classmethod
    def setUpClass(cls):
        from query_router.entity_validator import EntityValidator
        cls.validator = EntityValidator(_adapter())

    def test_naming_both_values_of_a_split_is_not_a_question(self):
        """"What percentage of the sanctioned budget is tied and untied?" —
        BUD-005 REPORTS both, so the two values are the answer's own shape. WP-5
        answered it; WP-6 gave the extractor a $tied_untied slot to fill and it
        started asking which half the officer meant."""
        from query_router import breakdown, router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        template = T["BUD-005"]
        splits = breakdown.slots_the_statement_splits(template)
        self.assertIn("tied_untied", splits)
        validated, clarify = router._fill_slots_or_clarify(
            "BUD-005", router._template_slot_types(template),
            {"date_range": "2024-2025", "tied_untied": ["Tied", "Untied"]},
            self.validator, "q", "q", 0.0,
            optional=router.optional_slots(template["param_slots"]),
            list_slots=router._list_slots(template["param_slots"]),
            splits=splits)
        self.assertIsNone(clarify, "it must answer, not ask")
        self.assertNotIn("tied_untied", {e.slot_name for e in validated})

    def test_a_comparison_on_a_list_slot_still_binds(self):
        """The rule above must not swallow "water vs sanitation": EXP-009 also
        separates focus areas, and there the officer named two of thirty."""
        from query_router import breakdown, router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        template = T["EXP-009"]
        validated, clarify = router._fill_slots_or_clarify(
            "EXP-009", router._template_slot_types(template),
            {"date_range": "2024-2025",
             "focus_area": ["Drinking water", "Sanitation"]},
            self.validator, "q", "q", 0.0,
            optional=router.optional_slots(template["param_slots"]),
            list_slots=router._list_slots(template["param_slots"]),
            splits=breakdown.slots_the_statement_splits(template))
        self.assertIsNone(clarify)
        focus = next(e for e in validated if e.slot_name == "focus_area")
        self.assertEqual(focus.values, ["Drinking water", "Sanitation"])

    def test_the_echo_only_names_a_breakdown_that_is_news(self):
        """"Which blocks have the most pending approvals?" reads `block` off its
        own wording, and block is what PLN-020 groups by anyway."""
        from query_router import breakdown
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        same = breakdown.describe("Which Blocks have the most pending approvals?",
                                  "block", T["PLN-020"])
        self.assertNotIn("broken down", same)
        different = breakdown.describe("How much planned expenditure per theme?",
                                       "district", T["BUD-006"])
        self.assertIn("broken down by district", different)

    def test_the_reranker_is_told_what_the_filters_are_for(self):
        """Both Eval_1 misses had their template in the window and lost it at the
        reranker, which never sees paraphrases — only the question and the
        description."""
        from query_router.rerank_context import DESC_BY_QID
        self.assertIn("FOCUS AREA", DESC_BY_QID["STS-003"])
        self.assertIn("completed sanitation activities", DESC_BY_QID["STS-003"])
        self.assertIn("PLN-049", DESC_BY_QID["PLN-052"])


if __name__ == "__main__":
    unittest.main()

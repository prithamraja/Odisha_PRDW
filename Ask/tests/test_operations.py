import unittest

from query_router.models import (
    ActiveFilter,
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    OperationMode,
    OperationRequest,
    OperationResult,
    ResultSetReference,
    TimeRange,
)
from query_router.operations import (
    OPERATIONS,
    _POPULATION_DEPENDENT,
    aggregation_mode,
    run_operation,
    truncating_limit,
)
from query_router.echo import operation_answer, operation_description


def make_frame(columns: list[ColumnMetadata], row_count: int = 3) -> ContextFrame:
    return ContextFrame(
        template_id="T02",
        bound_params={"district": "Agra"},
        active_filters=[ActiveFilter(dimension="district", value="Agra")],
        time_range=TimeRange(start="2025-01-01", end="2025-12-31", grain="day"),
        grouping_dimension="district_name",
        result_set=ResultSetReference(id="rs_test", row_count=row_count, columns=columns),
    )


MEASURE_COLUMNS = [
    ColumnMetadata(name="hospital_name", column_type=ColumnType.DIMENSION),
    ColumnMetadata(name="case_count", column_type=ColumnType.ADDITIVE_COUNT),
    ColumnMetadata(name="total_claimed", column_type=ColumnType.ADDITIVE_VALUE),
    ColumnMetadata(name="approval_rate", column_type=ColumnType.RATIO),
    ColumnMetadata(name="total_beds", column_type=ColumnType.SNAPSHOT_STOCK),
    ColumnMetadata(name="mystery", column_type=ColumnType.UNCLASSIFIED),
]

ROWS = [
    {"hospital_name": "Alpha", "case_count": 100, "total_claimed": 5000.0,
     "approval_rate": 80.0, "total_beds": 50, "mystery": 1},
    {"hospital_name": "Beta", "case_count": 300, "total_claimed": 12000.0,
     "approval_rate": 60.0, "total_beds": 150, "mystery": 2},
    {"hospital_name": "Gamma", "case_count": 100, "total_claimed": 3000.0,
     "approval_rate": 90.0, "total_beds": 100, "mystery": 3},
]


class PolicyTableTests(unittest.TestCase):
    """Exhaustive client-vs-requery policy per (aggregation, column type)."""

    def test_aggregation_policy_exhaustive(self):
        expected = {
            ColumnType.ADDITIVE_COUNT: "client",
            ColumnType.ADDITIVE_VALUE: "client",
            ColumnType.RATIO:          "requery",
            ColumnType.SNAPSHOT_STOCK: "client",
            ColumnType.UNCLASSIFIED:   "requery",
            ColumnType.DIMENSION:      "invalid",
            ColumnType.TEMPORAL:       "invalid",
            ColumnType.IDENTIFIER:     "invalid",
        }
        self.assertEqual(set(expected), set(ColumnType), "policy must cover every column type")
        for column_type, mode in expected.items():
            got = aggregation_mode(
                ColumnMetadata(name="c", column_type=column_type), MEASURE_COLUMNS
            )
            self.assertEqual(got, mode, f"aggregation on {column_type} should be {mode}")

    def test_snapshot_stock_across_time_requires_requery(self):
        with_time = MEASURE_COLUMNS + [
            ColumnMetadata(name="month", column_type=ColumnType.TEMPORAL)
        ]
        stock = ColumnMetadata(name="total_beds", column_type=ColumnType.SNAPSHOT_STOCK)
        self.assertEqual(aggregation_mode(stock, with_time), "requery")
        self.assertEqual(aggregation_mode(stock, MEASURE_COLUMNS), "client")

    def test_ratio_aggregations_never_run_client_side(self):
        frame = make_frame(MEASURE_COLUMNS)
        for op in ("sum", "average", "share_of_total"):
            result = run_operation(
                OperationRequest(operation=op, column="approval_rate"), frame, ROWS
            )
            self.assertEqual(result.mode, OperationMode.REJECTED, f"{op} on ratio must not execute")
            self.assertIsNone(result.value)
            self.assertIsNone(result.result)

    def test_unknown_operation_rejected(self):
        result = run_operation(
            OperationRequest(operation="regression"), make_frame(MEASURE_COLUMNS), ROWS
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)


class ClientOpsTests(unittest.TestCase):
    def setUp(self):
        self.frame = make_frame(MEASURE_COLUMNS)

    def run_op(self, **kwargs):
        return run_operation(OperationRequest(**kwargs), self.frame, ROWS)

    def test_sum_average_on_additive(self):
        self.assertEqual(self.run_op(operation="sum", column="case_count").value, 500.0)
        self.assertEqual(self.run_op(operation="average", column="total_claimed").value,
                         (5000 + 12000 + 3000) / 3)

    def test_min_max_names_the_row_and_the_column_it_came_from(self):
        result = self.run_op(operation="max", column="approval_rate")  # min/max on ratio is fine
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(result.value, 90.0)
        # Naming the label's own column is what makes a misclassified subject
        # visible: "(Devi Kumar)" reads as an answer to whatever was asked,
        # "(farmername: Devi Kumar)" shows it answered about a farmer.
        self.assertIn("hospital name: Gamma", result.answer)
        self.assertEqual(self.run_op(operation="min", column="case_count").value, 100.0)

    def test_count(self):
        self.assertEqual(self.run_op(operation="count").value, 3.0)

    def test_default_column_prefers_additive_value(self):
        result = self.run_op(operation="sum")
        self.assertEqual(result.column, "total_claimed")
        self.assertEqual(result.value, 20000.0)

    def test_share_of_total_with_label(self):
        result = self.run_op(operation="share_of_total", column="case_count", label="beta")
        self.assertEqual(result.value, 60.0)
        self.assertIn("accounts for 60.0%", result.answer)

    def test_share_of_total_adds_ratio_column(self):
        result = self.run_op(operation="share_of_total", column="case_count")
        self.assertEqual(result.result[0]["share_of_case_count_pct"], 20.0)
        added = result.result_columns[-1]
        self.assertEqual(added.column_type, ColumnType.RATIO)

    def test_percent_change_sorts_by_temporal(self):
        columns = [
            ColumnMetadata(name="month", column_type=ColumnType.TEMPORAL),
            ColumnMetadata(name="claims", column_type=ColumnType.ADDITIVE_COUNT),
        ]
        rows = [
            {"month": "2025-03", "claims": 150},
            {"month": "2025-01", "claims": 100},
            {"month": "2025-02", "claims": 120},
        ]
        result = run_operation(
            OperationRequest(operation="percent_change", column="claims"),
            make_frame(columns), rows,
        )
        self.assertEqual(result.value, 50.0)

    def test_percent_change_needs_two_rows(self):
        result = run_operation(
            OperationRequest(operation="percent_change", column="case_count"),
            self.frame, ROWS[:1],
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_sort_and_top_bottom(self):
        result = self.run_op(operation="sort", column="total_claimed", direction="asc")
        self.assertEqual([r["hospital_name"] for r in result.result],
                         ["Gamma", "Alpha", "Beta"])
        top = self.run_op(operation="top_n", column="case_count", n=1)
        self.assertEqual([r["hospital_name"] for r in top.result], ["Beta"])
        bottom = self.run_op(operation="bottom_n", column="total_claimed", n=2)
        self.assertEqual([r["hospital_name"] for r in bottom.result], ["Gamma", "Alpha"])

    def test_filter_rows_numeric_and_string(self):
        numeric = self.run_op(
            operation="filter_rows",
            filter_column="case_count", filter_operator=">", filter_value="100",
        )
        self.assertEqual([r["hospital_name"] for r in numeric.result], ["Beta"])
        text = self.run_op(
            operation="filter_rows",
            filter_column="hospital_name", filter_operator="contains", filter_value="alp",
        )
        self.assertEqual(len(text.result), 1)
        bad = self.run_op(
            operation="filter_rows",
            filter_column="case_count", filter_operator="~", filter_value="1",
        )
        self.assertEqual(bad.mode, OperationMode.REJECTED)

    def test_numeric_strings_are_coerced(self):
        rows = [{"hospital_name": "Alpha", "total_claimed": "1,500.50"},
                {"hospital_name": "Beta", "total_claimed": "500"}]
        result = run_operation(
            OperationRequest(operation="sum", column="total_claimed"),
            self.frame, rows,
        )
        self.assertEqual(result.value, 2000.5)

    def test_empty_table_rejected(self):
        result = run_operation(OperationRequest(operation="sum"), self.frame, [])
        self.assertEqual(result.mode, OperationMode.REJECTED)


class FilterTypeMirrorTests(unittest.TestCase):
    """The /operation endpoint has no routing fallback, so a filter that can't
    mean anything against its column is explained rather than silently
    answered with '0 of N rows'."""

    def setUp(self):
        self.frame = make_frame(MEASURE_COLUMNS)

    def run_op(self, **kwargs):
        return run_operation(
            OperationRequest(operation="filter_rows", **kwargs), self.frame, ROWS
        )

    def test_contains_on_a_numeric_column_is_rejected_with_an_explanation(self):
        result = self.run_op(
            filter_column="case_count", filter_operator="contains",
            filter_value="small or marginal",
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)
        self.assertIn("holds numbers", result.answer)
        self.assertIn("case_count", result.answer)
        self.assertIsNone(result.result, "a rejected filter must not return rows")

    def test_equality_against_a_measure_needs_a_number(self):
        result = self.run_op(
            filter_column="case_count", filter_operator="=", filter_value="marginal",
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_numeric_comparison_against_a_dimension_is_rejected(self):
        result = self.run_op(
            filter_column="hospital_name", filter_operator=">", filter_value="5",
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_legitimate_filters_still_run(self):
        self.assertEqual(
            self.run_op(filter_column="case_count", filter_operator=">",
                        filter_value="100").mode,
            OperationMode.CLIENT,
        )
        self.assertEqual(
            self.run_op(filter_column="hospital_name", filter_operator="contains",
                        filter_value="alp").mode,
            OperationMode.CLIENT,
        )
        self.assertEqual(
            self.run_op(filter_column="hospital_name", filter_operator="=",
                        filter_value="Beta").mode,
            OperationMode.CLIENT,
        )


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.columns = [
            ColumnMetadata(name="district_name", column_type=ColumnType.DIMENSION),
            ColumnMetadata(name="total_cases", column_type=ColumnType.ADDITIVE_COUNT),
        ]
        self.frame = make_frame(self.columns, row_count=1)
        self.rows = [{"district_name": "Agra", "total_cases": 1200}]

    def test_compare_merges_requery_rows(self):
        def requery(slot, value):
            self.assertEqual(slot, "district")
            return [{"district_name": value, "total_cases": 950}]

        result = run_operation(
            OperationRequest(operation="compare", comparator=["Lucknow"]),
            self.frame, self.rows, requery=requery,
        )
        self.assertEqual(result.mode, OperationMode.REQUERY)
        self.assertEqual(
            [r["compared_district"] for r in result.result], ["Agra", "Lucknow"]
        )
        self.assertIn("1,200 vs 950", result.answer)
        self.assertEqual(result.result_columns[0].column_type, ColumnType.DIMENSION)

    def test_compare_without_comparator_rejected(self):
        result = run_operation(
            OperationRequest(operation="compare"), self.frame, self.rows,
            requery=lambda s, v: [],
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_compare_unknown_slot_rejected(self):
        result = run_operation(
            OperationRequest(operation="compare", comparator=["Lucknow"],
                             comparator_slot="specialty"),
            self.frame, self.rows, requery=lambda s, v: [],
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_compare_requery_failure_is_reported(self):
        def requery(slot, value):
            raise ValueError("no such district")

        result = run_operation(
            OperationRequest(operation="compare", comparator=["Atlantis"]),
            self.frame, self.rows, requery=requery,
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)
        self.assertIn("Atlantis", result.answer)


class DistributionOpsTests(unittest.TestCase):
    """median / stdev / percentile / range — per-row distribution statistics,
    client-safe on every measure type including ratios."""

    def setUp(self):
        self.frame = make_frame(MEASURE_COLUMNS)

    def run_op(self, **kwargs):
        return run_operation(OperationRequest(**kwargs), self.frame, ROWS)

    def test_median(self):
        result = self.run_op(operation="median", column="case_count")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(result.value, 100.0)
        self.assertIn("rows shown", result.answer)

    def test_median_on_ratio_runs_client_side(self):
        # Unlike average: a median district rate is a legitimate row statistic.
        result = self.run_op(operation="median", column="approval_rate")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(result.value, 80.0)

    def test_stdev(self):
        result = self.run_op(operation="stdev", column="case_count")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertAlmostEqual(result.value, 115.4701, places=3)  # sample stdev

    def test_stdev_needs_two_values(self):
        result = run_operation(
            OperationRequest(operation="stdev", column="case_count"),
            self.frame, ROWS[:1],
        )
        self.assertEqual(result.mode, OperationMode.REJECTED)

    def test_percentile_median_equivalence(self):
        result = self.run_op(operation="percentile", column="total_claimed", n=50)
        self.assertEqual(result.value, 5000.0)
        self.assertIn("50th percentile", result.answer)

    def test_percentile_interpolates(self):
        # sorted case_count [100, 100, 300], rank 0.9 * 2 = 1.8 → 100 + 0.8 * 200
        result = self.run_op(operation="percentile", column="case_count", n=90)
        self.assertAlmostEqual(result.value, 260.0)

    def test_percentile_requires_valid_n(self):
        self.assertEqual(
            self.run_op(operation="percentile", column="case_count").mode,
            OperationMode.REJECTED,
        )
        self.assertEqual(
            self.run_op(operation="percentile", column="case_count", n=150).mode,
            OperationMode.REJECTED,
        )

    def test_range_names_both_endpoints(self):
        result = self.run_op(operation="range", column="total_claimed")
        self.assertEqual(result.value, 9000.0)
        self.assertIn("Gamma", result.answer)  # min row
        self.assertIn("Beta", result.answer)   # max row


class ValueFrequencyTests(unittest.TestCase):
    """mode / count_distinct — any column, dimensions included."""

    def setUp(self):
        self.frame = make_frame(MEASURE_COLUMNS)

    def run_op(self, **kwargs):
        return run_operation(OperationRequest(**kwargs), self.frame, ROWS)

    def test_mode_on_numeric_column(self):
        result = self.run_op(operation="mode", column="case_count")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(result.value, 100.0)
        self.assertIn("2 of 3 rows", result.answer)

    def test_mode_all_unique_is_honest(self):
        result = self.run_op(operation="mode", column="hospital_name")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertIsNone(result.value)
        self.assertIn("no most common value", result.answer)

    def test_mode_defaults_to_dimension_column(self):
        result = self.run_op(operation="mode")
        self.assertEqual(result.column, "hospital_name")

    def test_mode_reports_ties(self):
        rows = ROWS + [{"hospital_name": "Delta", "case_count": 300}]
        result = run_operation(
            OperationRequest(operation="mode", column="case_count"), self.frame, rows
        )
        self.assertIsNone(result.value)
        self.assertIn("tie as most common", result.answer)
        self.assertIn("100", result.answer)
        self.assertIn("300", result.answer)

    def test_count_distinct(self):
        self.assertEqual(
            self.run_op(operation="count_distinct", column="hospital_name").value, 3.0
        )
        self.assertEqual(
            self.run_op(operation="count_distinct", column="case_count").value, 2.0
        )

    def test_unknown_column_rejected(self):
        result = self.run_op(operation="count_distinct", column="nonexistent")
        self.assertEqual(result.mode, OperationMode.REJECTED)


class TruncatedTableTests(unittest.TestCase):
    """WP-4c 5.2 / D31.2 - an operation must never be computed on a table the
    question truncated.

    THE RECORDED SHAPES, from the replay record rather than from imagination:

      #1403 "Which focus area has the highest planned expenditure in 2024-25?"
            -> BUD-022, top_n = 1. The displayed table is ONE ROW: the highest.
      #1404 "and the lowest?"
            -> read as an OPERATION on that table. The minimum of a one-row
               table is that row, so the answer named the HIGHEST focus area as
               the lowest, in a sentence with no echo above it.
      #1042 "aur sabse kam?"  (the same thing in Hinglish)
            -> "Bottom 1 rows by planned_cost. Poverty allevation programme
               leads with 3,581,500."

    Both must now re-query or reject. Neither may serve the one-row minimum.
    """

    FOCUS_COLUMNS = [
        ColumnMetadata(name="focus_area_name", column_type=ColumnType.DIMENSION),
        ColumnMetadata(name="planned_cost", column_type=ColumnType.ADDITIVE_VALUE),
        ColumnMetadata(name="activities", column_type=ColumnType.ADDITIVE_COUNT),
    ]

    # The population BUD-022 ranks, and the one row `LIMIT 1` left on screen.
    FULL_ROWS = [
        {"focus_area_name": "Drinking water", "planned_cost": 42118474.0,
         "activities": 900},
        {"focus_area_name": "Sanitation", "planned_cost": 12000000.0,
         "activities": 400},
        {"focus_area_name": "Poverty allevation programme",
         "planned_cost": 3581500.0, "activities": 120},
    ]
    TRUNCATED_ROWS = FULL_ROWS[:1]

    def frame(self, top_n="1"):
        return ContextFrame(
            template_id="BUD-022",
            template_question="Which focus area has the highest planned "
                              "expenditure in 2024-2025?",
            bound_params={"date_range": "2024-2025", "top_n": top_n},
            active_filters=[ActiveFilter(dimension="date_range",
                                         value="2024-2025")],
            time_range=TimeRange(start=None, end=None, grain="year"),
            grouping_dimension="focus_area_name",
            result_set=ResultSetReference(
                id="rs_bud022", row_count=1, columns=self.FOCUS_COLUMNS),
        )

    def requery(self, slot, value):
        self.requeried.append((slot, value))
        return list(self.FULL_ROWS)

    def setUp(self):
        self.requeried = []

    def run_op(self, operation, frame=None, rows=None, requery="real", **kw):
        return run_operation(
            OperationRequest(operation=operation, **kw),
            frame if frame is not None else self.frame(),
            self.TRUNCATED_ROWS if rows is None else rows,
            requery=self.requery if requery == "real" else requery,
        )

    # -- The two recorded shapes ---------------------------------------------

    def test_1404_the_lowest_of_a_top_one_table_re_queries(self):
        """The defect, closed. `min` over the one row left by `LIMIT 1` used to
        return Drinking water - the HIGHEST - as the lowest."""
        result = self.run_op("min", column="planned_cost")
        self.assertEqual(result.mode, OperationMode.REQUERY)
        self.assertEqual(self.requeried, [("top_n", "1000")],
                         "the limit is lifted by re-binding $top_n, not removed")
        self.assertEqual(result.value, 3581500.0)
        self.assertIn("Poverty allevation programme", result.answer)
        self.assertNotIn("Drinking water", result.answer,
                         "the highest must never come back as the lowest")

    def test_1042_bottom_n_of_a_top_one_table_re_queries(self):
        """"aur sabse kam?" - the Hinglish half of the same pair. `bottom_n`
        over a top-1 table returned "Bottom 1 rows ... Poverty allevation
        programme leads", which was true of nothing."""
        result = self.run_op("bottom_n", column="planned_cost", n=1)
        self.assertEqual(result.mode, OperationMode.REQUERY)
        self.assertEqual([r["focus_area_name"] for r in result.result],
                         ["Poverty allevation programme"])

    def test_neither_shape_can_be_served_from_the_truncated_table(self):
        """The property that matters is not which of re-query or reject
        happens - it is that the one-row minimum is never the answer."""
        for requery in (None, self.requery):
            for op in ("min", "bottom_n"):
                with self.subTest(op=op, requery=bool(requery)):
                    result = self.run_op(op, column="planned_cost",
                                         requery=requery)
                    self.assertIn(result.mode, (OperationMode.REQUERY,
                                                OperationMode.REJECTED))
                    self.assertNotEqual(result.value, 42118474.0)

    # -- The rejection path --------------------------------------------------

    def test_without_a_requery_hook_it_rejects_and_names_the_truncation(self):
        result = self.run_op("min", column="planned_cost", requery=None)
        self.assertEqual(result.mode, OperationMode.REJECTED)
        self.assertIn("top 1 row", result.answer)
        self.assertIn("whole population", result.answer)

    def test_a_failing_requery_rejects_rather_than_falling_back(self):
        """FALLING BACK TO THE TRUNCATED TABLE WOULD BE THE DEFECT AGAIN, with
        an excuse attached. A re-query that raises must reject."""
        def boom(slot, value):
            raise RuntimeError("template is not re-queryable")
        result = self.run_op("min", column="planned_cost", requery=boom)
        self.assertEqual(result.mode, OperationMode.REJECTED)
        self.assertIn("RuntimeError", result.answer)

    def test_an_empty_requery_rejects(self):
        result = self.run_op("min", column="planned_cost",
                             requery=lambda slot, value: [])
        self.assertEqual(result.mode, OperationMode.REJECTED)

    # -- What the guard must NOT do ------------------------------------------

    def test_a_limit_that_never_bound_is_not_a_truncation(self):
        """`top_n = 10` over a three-row population returns three rows: the
        LIMIT never bit, the table IS the population, and refusing here would
        decline a question that has a correct answer."""
        frame = self.frame(top_n="10")
        self.assertIsNone(truncating_limit(frame, self.FULL_ROWS))
        result = self.run_op("min", frame=frame, rows=self.FULL_ROWS,
                             column="planned_cost")
        self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(self.requeried, [], "nothing to lift")

    def test_a_frame_with_no_top_n_is_untouched(self):
        frame = self.frame()
        frame.bound_params.pop("top_n")
        self.assertIsNone(truncating_limit(frame, self.TRUNCATED_ROWS))
        self.assertEqual(
            self.run_op("min", frame=frame, column="planned_cost").mode,
            OperationMode.CLIENT)

    def test_count_and_sort_are_not_guarded(self):
        """`count` answers "the table has N rows", which is a statement about
        the table; `sort` returns the rows on screen in another order. Neither
        claims anything about a population, so neither pays for a re-query."""
        for op in ("count", "sort"):
            with self.subTest(op=op):
                result = self.run_op(op, column="planned_cost")
                self.assertEqual(result.mode, OperationMode.CLIENT)
        self.assertEqual(self.requeried, [])

    def test_every_population_dependent_operation_is_a_real_operation(self):
        self.assertTrue(_POPULATION_DEPENDENT <= OPERATIONS)
        self.assertEqual(
            OPERATIONS - _POPULATION_DEPENDENT,
            {"count", "sort", "filter_rows", "compare"},
            "the unguarded set is a deliberate list, not a leftover - see the "
            "enumeration in operations.py")

    def test_the_guard_cannot_recurse(self):
        """The re-query recomputes through `run_operation` itself, so the frame
        it hands down must no longer carry the limit."""
        self.run_op("min", column="planned_cost")
        self.assertEqual(len(self.requeried), 1)


class OperationEchoTests(unittest.TestCase):
    """D31.2 - an operations answer restates what it answered.

    `query_description` was None on this path, which is why #1404 arrived with
    nothing beside it. Every other confidently-wrong row in WP-4c's replays at
    least printed the question it answered.
    """

    def setUp(self):
        self.case = TruncatedTableTests("run")
        self.case.setUp()

    def test_the_echo_names_the_operation_the_measure_and_the_period(self):
        result = run_operation(
            OperationRequest(operation="min", column="planned_cost"),
            self.case.frame(), self.case.TRUNCATED_ROWS,
            requery=self.case.requery)
        echo = operation_description(self.case.frame(), result)
        self.assertEqual(
            echo, "Lowest planned cost among all focus area name, 2024-2025:")

    def test_the_scope_clause_distinguishes_requery_from_client_side(self):
        """"among all" is only ever written after the full population was
        fetched. A client-side computation says so."""
        frame = self.case.frame(top_n="10")
        client = run_operation(
            OperationRequest(operation="min", column="planned_cost"),
            frame, self.case.FULL_ROWS, requery=self.case.requery)
        self.assertEqual(client.mode, OperationMode.CLIENT)
        self.assertIn("among the focus area name shown",
                      operation_description(frame, client))

    def test_the_answer_carries_the_echo_and_the_caveat(self):
        result = run_operation(
            OperationRequest(operation="min", column="planned_cost"),
            self.case.frame(), self.case.TRUNCATED_ROWS,
            requery=self.case.requery)
        answer = operation_answer(self.case.frame(), result,
                                  "Covers only the 20 loaded GPs.")
        self.assertTrue(answer.startswith("Lowest planned cost"))
        self.assertIn(result.answer, answer)
        self.assertIn("Note: Covers only the 20 loaded GPs.", answer)

    def test_a_rejection_gets_no_echo(self):
        """Restating the question above a sentence explaining why it was not
        answered reads as though it had been."""
        result = run_operation(
            OperationRequest(operation="min", column="planned_cost"),
            self.case.frame(), self.case.TRUNCATED_ROWS, requery=None)
        self.assertEqual(result.mode, OperationMode.REJECTED)
        answer = operation_answer(self.case.frame(), result, None)
        self.assertEqual(answer, result.answer)

    def test_every_operation_produces_a_non_empty_description(self):
        """The assertion in main.py refuses to serve an answer without one, so
        no operation may produce an empty echo."""
        for op in sorted(OPERATIONS):
            with self.subTest(op=op):
                result = OperationResult(
                    operation=op, mode=OperationMode.CLIENT, answer="x",
                    column="planned_cost")
                self.assertTrue(
                    operation_description(self.case.frame(), result).strip())


class OperationSetTests(unittest.TestCase):
    def test_closed_set_matches_spec(self):
        self.assertEqual(OPERATIONS, {
            "sum", "average", "min", "max", "count", "share_of_total",
            "sort", "filter_rows", "percent_change", "top_n", "bottom_n", "compare",
            "median", "mode", "stdev", "percentile", "range", "count_distinct",
        })


if __name__ == "__main__":
    unittest.main()

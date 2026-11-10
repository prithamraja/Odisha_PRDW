import re
import unittest

from query_router.column_metadata import build_catalog_column_metadata, classify_column
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.models import ColumnType
from query_router.template_catalog import TEMPLATE_CATALOG


class CatalogColumnMetadataTests(unittest.TestCase):
    def test_every_catalog_has_fully_typed_result_columns(self):
        metadata = build_catalog_column_metadata(
            DASHBOARD_CATALOG,
            TEMPLATE_CATALOG,
        )

        self.assertEqual(len(metadata), len(DASHBOARD_CATALOG) + len(TEMPLATE_CATALOG))
        self.assertFalse([query_id for query_id, columns in metadata.items() if not columns])
        self.assertFalse([
            (query_id, column.name)
            for query_id, columns in metadata.items()
            for column in columns
            if column.column_type == ColumnType.UNCLASSIFIED
        ])


class MoneyColumnClassificationTests(unittest.TestCase):
    """Money must never classify as a count, and a mean must never classify as
    summable.

    column_types.json puts the reason plainly: summing a column of percentages
    down a displayed table produces a confident number that means nothing. The
    same applies to a per-activity average. These tests exist so a future column
    rename cannot silently reclassify either.
    """

    # Stems that only ever appear on an amount or on something derived from one.
    MONEY_STEM = re.compile(r"(cost|expenditure|amount|unspent|spent|paid|payment)", re.I)

    def _catalog_columns(self):
        metadata = build_catalog_column_metadata(DASHBOARD_CATALOG, TEMPLATE_CATALOG)
        for query_id, columns in metadata.items():
            for column in columns:
                yield query_id, column

    def test_no_money_column_is_classified_as_a_count(self):
        offenders = sorted({
            (column.name, query_id)
            for query_id, column in self._catalog_columns()
            if self.MONEY_STEM.search(column.name)
            and column.column_type == ColumnType.ADDITIVE_COUNT
            # Not every column carrying a money stem is an amount. A column
            # that COUNTS things which happen to have a cost is a count
            # ('activities_with_expenditure', 'low_cost_activities'), and an
            # 'is_' column is a 0/1 indicator whose sum is likewise a count
            # ('is_costless_activity'). Both are correctly additive_count.
            and not re.search(r"^is_|^(activities|gps)_|_activities$", column.name)
        })
        self.assertFalse(
            offenders,
            "money columns classified as additive_count: %s" % (offenders,),
        )

    def test_per_unit_means_are_ratios(self):
        for name in ("cost_per_activity", "expenditure_per_gp",
                     "state_avg_expenditure_per_gp", "avg_planned_cost"):
            with self.subTest(name=name):
                self.assertEqual(classify_column(name), ColumnType.RATIO)

    def test_named_money_aliases_are_additive_value(self):
        for name in ("approved_cost", "admin_approved_cost",
                     "approved_cost_action_plan", "technical_approved_cost",
                     "expenditure_year1", "expenditure_year2",
                     "approved_cost_year1", "approved_cost_year2"):
            with self.subTest(name=name):
                self.assertEqual(classify_column(name), ColumnType.ADDITIVE_VALUE)

    def test_gps_approved_is_still_a_count(self):
        """Regression guard. The status-prefix rule sits above the money rule so
        that this stays a count; the fix must not have been a reorder."""
        self.assertEqual(classify_column("gps_approved"), ColumnType.ADDITIVE_COUNT)


if __name__ == "__main__":
    unittest.main()

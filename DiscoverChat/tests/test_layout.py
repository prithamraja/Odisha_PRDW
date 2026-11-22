# -*- coding: utf-8 -*-
"""WP-D12 (D62): the Insight report layout -- cards, charts and warnings drawn
by code from the stored records.

Offline and deterministic: no model call and no embedding call. Where a test
needs a whole turn, the classifier, the retrieval step and the writer are
replaced by stubs that hand back RECORDED material -- the WP-D13 trial's
answers of 2026-11-21 (`experiments/direction_trial_results.json`), recorded
on the current corpus, whose every numeral still binds.

    python -m pytest DiscoverChat/tests/test_layout.py -q
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from DiscoverChat import (                                          # noqa: E402
    assemble, checks, classifier, config, corpus as corpus_mod, glossary,
    layout, navigate,
)
from DiscoverChat.corpus import Finding                             # noqa: E402
from DiscoverChat.retrieval import Hit, Result                      # noqa: E402
from DiscoverChat.slots import Slots                                # noqa: E402
from DiscoverChat.writer import Consolidated                        # noqa: E402
from phase5f_decompose import _fmt, measure_phrase                  # noqa: E402

TRIAL = REPO / "DiscoverChat" / "experiments" / "direction_trial_results.json"

_CORPUS = None


def _corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = corpus_mod.load()
    return _CORPUS


def _recorded() -> list:
    """Every recorded answer of the WP-D13 trial: the judge's findings in the
    service's order, and the tagged prose ("" where it fell back)."""
    with open(TRIAL, encoding="utf-8") as fh:
        trial = json.load(fh)
    questions = {q["n"]: q for q in trial["questions"]}
    out = []
    for arm in ("log", "block"):
        for run in trial["arms"][arm]:
            question = questions[run["n"]]
            out.append({
                "arm": arm, "n": run["n"], "question": question["question"],
                "findings": [_corpus().get(i) for i in question["findings"]],
                "tagged": "" if run["fell_back"] else run["final_tagged"],
                "stamp": trial["stamp"],
            })
    return out


def _ids(built: dict) -> set:
    """Every record id a layout mentions."""
    out = {c["id"] for c in built.get("cards", [])}
    out |= {w["id"] for w in built.get("warnings", [])}
    for panel in built.get("panels", []):
        out |= set(panel["ids"])
    return out


def _strings(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _strings(value)
    elif isinstance(obj, str):
        yield obj


# ── synthetic records, for rules that need exact control ─────────────────────

def _decomposition(fid, members, *, measure="total_cost", view="view1",
                   dimension="tied_untied", dimension_phrase="tied or untied grant",
                   subspace=(), temporal=False, null=None, sentence=None):
    """A decomposition record in the corpus's own shape. `members` is
    [(name, value, rows)] in STORED order; `null` names the null member."""
    gross = sum(abs(v) for _, v, _ in members)
    total = sum(v for _, v, _ in members)
    positives = any(v > 0 for _, v, _ in members)
    negatives = any(v < 0 for _, v, _ in members)
    signs = ("mixed" if positives and negatives
             else "all_negative" if negatives else "all_positive")
    names = [n for n, _, _ in members]
    data = {
        "finding_id": fid, "record_type": "decomposition",
        "view": view, "view_title": "Activity Lifecycle",
        "measure": measure, "measures": [measure],
        "measure_phrase": measure_phrase(view, measure),
        "dimension": dimension, "dimension_phrase": dimension_phrase,
        "dimension_is_temporal": temporal,
        "subspace": [list(p) for p in subspace],
        "subspace_phrase": ("; ".join(f"{d} {v}" for d, v in subspace)
                            or "the whole of the table"),
        "total": total, "total_display": _fmt(view, measure, total),
        "gross": gross, "signs": signs, "shape": "spread",
        "n_members": len(members), "has_null_member": null is not None,
        "members": {"member": names,
                    "value": [v for _, v, _ in members],
                    "rows": [r for _, _, r in members],
                    "share": [round(abs(v) / gross, 6) for _, v, _ in members],
                    "null_index": [names.index(null)] if null else []},
        "named_members": [n for n in names if n != null],
        "sentence": sentence or f"Within the table, {measure} totals "
                                f"{_fmt(view, measure, total)}.",
    }
    return Finding(0, data)


def _pattern(fid, measure="total_cost", sentence="Across most blocks, Kalimela "
                                                  "has the highest total_cost."):
    return Finding(0, {"finding_id": fid, "view": "view1",
                       "view_title": "Activity Lifecycle", "sentence": sentence,
                       "measure": measure, "measures": [measure],
                       "subspace_phrase": "the whole of the table",
                       "in_feed": False, "view_rank": None, "score": 0.5,
                       "named_members": ["Kalimela"]})


def _two(fid, a=60.0, b=40.0, **kw):
    kw.setdefault("measure", "total_cost")
    return _decomposition(fid, [("Tied", a * 1e5, 3), ("Untied", b * 1e5, 2)], **kw)


def _many(fid, n, *, null_value=None, measure="total_cost",
          dimension="theme", temporal=False):
    members = [(f"Theme {i}", (n - i) * 1e5, 10) for i in range(n)]
    null = None
    if null_value is not None:
        members.append(("(not recorded)", null_value, 7))
        members.sort(key=lambda m: -abs(m[1]))
        null = "(not recorded)"
    return _decomposition(fid, members, measure=measure, dimension=dimension,
                          dimension_phrase="LSDG theme", temporal=temporal,
                          null=null)


def _with_null(fid, share, dimension="tied_untied", measure="total_cost"):
    """Two members plus a null member holding `share` of the gross."""
    rest = 100.0 - share * 100.0
    return _decomposition(
        fid, sorted([("Tied", rest / 2 * 1e5, 4), ("Untied", rest / 2 * 1e5, 4),
                     ("(not recorded)", share * 100.0 * 1e5, 9)],
                    key=lambda m: -abs(m[1])),
        dimension=dimension, measure=measure, null="(not recorded)")


# ═════════════════════════════════════════════════════════════════════════════
# 1. Formatter parity -- the layout's numbers are the corpus's numbers
# ═════════════════════════════════════════════════════════════════════════════

class ParityTests(unittest.TestCase):

    def test_the_whole_corpus(self):
        detail = layout.parity_check(_corpus())
        self.assertIn("decompositions", detail)

    def test_a_negative_signed_total_reads_below_plan(self):
        record = next(f for f in _corpus().all()
                      if f.is_decomposition and f.data["signs"] == "all_negative"
                      and f.data["measure"] == "overspend_vs_plan")
        card = layout.card_for(record)
        self.assertNotIn("Rs -", card["value"])
        self.assertTrue(card["value"].endswith(" below plan"), card["value"])
        self.assertEqual(card["value"], glossary.signed_money(
            record.data["total_display"], "overspend_vs_plan"))

    def test_a_positive_signed_total_reads_above(self):
        record = next(f for f in _corpus().all()
                      if f.is_decomposition and f.data["signs"] == "all_positive"
                      and f.data["measure"] == "overspend_vs_sanction")
        card = layout.card_for(record)
        self.assertEqual(card["value"],
                         f"{record.data['total_display']} above sanction")


# ═════════════════════════════════════════════════════════════════════════════
# 2. Whole-corpus sweep -- every record's panel obeys the kind table
# ═════════════════════════════════════════════════════════════════════════════

class SweepTests(unittest.TestCase):

    def test_every_decomposition(self):
        kinds, problems = {}, []
        for record in _corpus().all():
            if not record.is_decomposition:
                continue
            data = record.data
            panel = layout.panel_for(record)
            kind = panel["kind"] if panel else None
            kinds[kind] = kinds.get(kind, 0) + 1
            if data["signs"] == "mixed" or float(data["total"]) == 0:
                if panel is not None:
                    problems.append((record.id, "mixed or zero got a panel"))
                continue
            if panel is None:
                problems.append((record.id, "chartable record got no panel"))
                continue
            expected = ("compare" if data["n_members"] == 2 else
                        "time" if data["dimension_is_temporal"] else "ranked")
            if kind != expected:
                problems.append((record.id, f"{kind} for {expected}"))
            bars = (panel["rows"][0]["parts"] if kind == "compare"
                    else panel["bars"])
            if any(not 0.0 <= b["fraction"] <= 1.0 for b in bars):
                problems.append((record.id, "fraction out of [0, 1]"))
            if any("Rs -" in s for s in _strings(panel)):
                problems.append((record.id, "a minus sign reached the panel"))
            nulls = [b for b in bars if b["role"] == "not_recorded"]
            if len(nulls) != (1 if data["has_null_member"] else 0):
                problems.append((record.id, "null bar missing or doubled"))
            if kind == "compare":
                if len(bars) != 2:
                    problems.append((record.id, "compare without two parts"))
                continue
            real = [b for b in bars if b["role"] == "member"]
            if bars[len(real):] != nulls:
                problems.append((record.id, "null bar not last"))
            if panel["shown"] != len(real) or panel["of"] < panel["shown"]:
                problems.append((record.id, "shown/of wrong"))
            if kind == "ranked" and len(real) > config.LAYOUT_MAX_BARS:
                problems.append((record.id, "more than five bars"))
            if kind == "time":
                labels = [b["member"] for b in real]
                if labels != sorted(labels) or len(set(labels)) != len(labels):
                    problems.append((record.id, "time not strictly ordered"))
                if len(real) > config.LAYOUT_MAX_TIME_BARS:
                    problems.append((record.id, "more than twelve periods"))
        self.assertEqual(problems, [], problems[:5])
        self.assertEqual(kinds.get(None), sum(
            1 for r in _corpus().all() if r.is_decomposition
            and (r.data["signs"] == "mixed" or float(r.data["total"]) == 0)))


# ═════════════════════════════════════════════════════════════════════════════
# 3. The rules of T1.2
# ═════════════════════════════════════════════════════════════════════════════

class CardRuleTests(unittest.TestCase):

    def test_at_most_three_one_per_measure_in_order(self):
        findings = [_two("d1-90001", measure="total_cost"),
                    _two("d1-90002", measure="total_cost"),         # repeat
                    _two("d1-90003", measure="fund_tied_total"),
                    _pattern("1-90004", measure="fund_tied_total"),  # repeat
                    _two("d1-90005", measure="fund_untied_total"),
                    _two("d1-90006", measure="total_expenditure")]
        built = layout.build(findings, "")
        self.assertEqual([c["id"] for c in built["cards"]],
                         ["d1-90001", "d1-90003", "d1-90005"])

    def test_the_same_quantity_from_two_tables_is_one_card(self):
        # view1 `total_cost` and view3 `planned_cost` both read "planned cost".
        findings = [_two("d1-90001", measure="total_cost"),
                    _two("d3-90002", measure="planned_cost", view="view3"),
                    _two("d1-90003", measure="fund_tied_total")]
        self.assertEqual(measure_phrase("view3", "planned_cost"),
                         measure_phrase("view1", "total_cost"))
        built = layout.build(findings, "")
        self.assertEqual([c["id"] for c in built["cards"]],
                         ["d1-90001", "d1-90003"])

    def test_none_under_three_findings(self):
        self.assertEqual(layout.build([_two("d1-90001"), _two(
            "d1-90002", measure="fund_tied_total")], "")["cards"], [])

    def test_mixed_signs_get_no_card(self):
        mixed = _decomposition("d1-90001", [("A", 5e5, 1), ("B", -3e5, 1)],
                               measure="overspend_vs_plan")
        built = layout.build([mixed, _two("d1-90002"),
                              _two("d1-90003", measure="fund_tied_total")], "")
        self.assertEqual([c["id"] for c in built["cards"]],
                         ["d1-90002", "d1-90003"])
        self.assertNotIn("d1-90001", _ids(built))

    def test_card_shapes(self):
        pattern_record = _pattern("1-90002", measure="gen_amount")
        built = layout.build([_two("d1-90001"), pattern_record,
                              _two("d1-90003", measure="fund_tied_total")], "")
        total, pattern = built["cards"][0], built["cards"][1]
        self.assertEqual(total["kind"], "total")
        self.assertEqual(total["value"], "Rs 1.00 crore")
        self.assertEqual(total["label"], "planned cost")
        self.assertEqual(pattern["kind"], "pattern")
        # The pattern's sentence verbatim, column names translated.
        self.assertEqual(pattern["text"], pattern_record.display_sentence())
        self.assertNotIn("total_cost", pattern["text"])


class UncitedTests(unittest.TestCase):

    def test_records_the_prose_does_not_cite_are_left_out(self):
        findings = [_two("d1-90001"), _two("d1-90002", measure="fund_tied_total"),
                    _with_null("d1-90003", 0.5),
                    _two("d1-90004", measure="fund_untied_total")]
        tagged = ("Planned cost is shown. [d1-90001] Untied money is shown. "
                  "[d1-90004]")
        built = layout.build(findings, tagged)
        self.assertEqual(_ids(built), {"d1-90001", "d1-90004"})
        self.assertEqual(built["warnings"], [])


class WarningRuleTests(unittest.TestCase):

    def test_threshold_on_both_sides(self):
        at = _with_null("d1-90001", 0.30)
        below = _with_null("d1-90002", 0.2999, dimension="theme")
        self.assertEqual(layout.null_member(at.data)["share"], 0.3)
        built = layout.build([at, below], "")
        self.assertEqual([w["id"] for w in built["warnings"]], ["d1-90001"])

    def test_one_per_dimension_the_largest_and_sorted(self):
        findings = [_with_null("d1-90001", 0.40),
                    _with_null("d1-90002", 0.90),            # same dimension
                    _with_null("d1-90003", 0.60, dimension="theme"),
                    _with_null("d1-90004", 0.50, dimension="scheme"),
                    _with_null("d1-90005", 0.35, dimension="block_name")]
        warnings = layout.build(findings, "")["warnings"]
        self.assertEqual([w["id"] for w in warnings],
                         ["d1-90002", "d1-90003", "d1-90004"])

    def test_no_minimum_findings_and_the_fields(self):
        record = _with_null("d1-90001", 0.5)
        (warning,) = layout.build([record], "")["warnings"]
        self.assertEqual(warning, {
            "id": "d1-90001", "url": config.record_url("d1-90001"),
            "rows": "9", "missing": "tied or untied grant",
            "measure": "planned cost", "share": "50.0%",
            "amount": "Rs 50.00 lakh", "scope": "the whole of the table"})

    def test_a_signed_amount_states_its_direction(self):
        record = _decomposition(
            "d1-90001", [("(not recorded)", -3e7, 923), ("Tied", -1e7, 50)],
            measure="overspend_vs_plan", null="(not recorded)")
        (warning,) = layout.build([record], "")["warnings"]
        self.assertEqual(warning["amount"], "Rs 3.00 crore below plan")
        self.assertEqual(warning["share"], "75.0%")

    def test_a_mixed_sign_record_raises_no_warning(self):
        """WP-D13 Fix 7 T3 (D66): the null share of a mixed record is a share
        of all the money moving both ways, not of the net."""
        record = _decomposition(
            "d1-90001", [("(not recorded)", -4.5e7, 923), ("Tied", 3e7, 50),
                         ("Untied", -2.5e7, 40)],
            measure="overspend_vs_plan", null="(not recorded)")
        self.assertEqual(record.data["signs"], "mixed")
        self.assertGreaterEqual(layout.null_member(record.data)["share"],
                                config.LAYOUT_NULL_SHARE_WARN)
        self.assertEqual(layout.build([record], "")["warnings"], [])
        # The same parts all running one way still warn.
        one_way = _decomposition(
            "d1-90002", [("(not recorded)", -4.5e7, 923), ("Tied", -3e7, 50),
                         ("Untied", -2.5e7, 40)],
            measure="overspend_vs_plan", null="(not recorded)")
        self.assertEqual([w["id"] for w in
                          layout.build([one_way], "")["warnings"]], ["d1-90002"])

    def test_the_whole_corpus_loses_29_warnings_all_mixed(self):
        lost, warned = [], 0
        for record in _corpus().all():
            if not record.is_decomposition:
                continue
            member = layout.null_member(record.data)
            would = (member is not None and abs(float(member["share"]))
                     >= config.LAYOUT_NULL_SHARE_WARN)
            now = bool(layout._warnings([record], {record.id: 0}))
            self.assertFalse(now and not would, record.id)
            if now:
                warned += 1
                self.assertNotEqual(record.data["signs"], "mixed", record.id)
            elif would:
                lost.append(record)
        self.assertEqual(len(lost), 29)
        self.assertTrue(all(r.data["signs"] == "mixed" for r in lost))
        self.assertGreater(warned, 3000)


class PanelRuleTests(unittest.TestCase):

    def test_compare_groups_and_keeps_the_first_rows_member_order(self):
        first = _two("d1-90001", a=60, b=40)
        # Stored largest first, so this record lists Untied before Tied.
        second = _decomposition("d1-90002", [("Untied", 70e5, 1), ("Tied", 30e5, 1)],
                                measure="fund_tied_total")
        elsewhere = _two("d1-90003", subspace=[("block_name", "Kalimela")])
        built = layout.build([first, second, elsewhere], "")
        compare = [p for p in built["panels"] if p["kind"] == "compare"]
        self.assertEqual(len(compare), 2)
        grouped = compare[0]
        self.assertEqual(grouped["ids"], ["d1-90001", "d1-90002"])
        self.assertEqual(grouped["members"], ["Tied", "Untied"])
        second_row = grouped["rows"][1]
        self.assertEqual([p["member"] for p in second_row["parts"]],
                         ["Tied", "Untied"])
        self.assertEqual([p["share"] for p in second_row["parts"]],
                         ["30.0%", "70.0%"])
        self.assertEqual(compare[1]["ids"], ["d1-90003"])

    def test_compare_rows_capped_at_five_by_weight(self):
        measures = ["total_cost", "fund_tied_total", "fund_untied_total",
                    "total_expenditure", "work_proposed_cost",
                    "fund_sanctioned_total", "gen_amount"]
        findings = [_two(f"d1-9000{i}", a=60 + i, b=40 - i, measure=m)
                    for i, m in enumerate(measures)]
        # Only the last two records are given figures in the prose.
        tagged = " ".join(
            f"It totals {f.data['total_display']}. [{f.id}]"
            for f in findings[5:]) + " " + " ".join(
            f"Shown. [{f.id}]" for f in findings[:5])
        (panel,) = [p for p in layout.build(findings, tagged)["panels"]]
        self.assertEqual(panel["ids"], ["d1-90005", "d1-90006", "d1-90000",
                                        "d1-90001", "d1-90002"])

    def test_panels_capped_and_ranked_by_weight(self):
        findings = [_many(f"d1-9000{i}", 4 + i, measure=m)
                    for i, m in enumerate(["total_cost", "fund_tied_total",
                                           "fund_untied_total", "gen_amount"])]
        tagged = (f"Untied is {findings[2].data['total_display']}. "
                  f"[{findings[2].id}] " + " ".join(
                      f"Shown. [{f.id}]" for f in findings))
        panels = layout.build(findings, tagged)["panels"]
        self.assertEqual([p["id"] for p in panels],
                         ["d1-90002", "d1-90000", "d1-90001"])

    def test_one_panel_under_three_findings(self):
        built = layout.build([_many("d1-90001", 4), _many(
            "d1-90002", 5, measure="fund_tied_total")], "")
        self.assertEqual(len(built["panels"]), 1)

    def test_ranked_shows_five_and_always_the_null_bar(self):
        record = _many("d1-90001", 9, null_value=1e5)
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual(panel["kind"], "ranked")
        self.assertEqual((panel["shown"], panel["of"]), (5, 9))
        self.assertEqual([b["role"] for b in panel["bars"]],
                         ["member"] * 5 + ["not_recorded"])
        self.assertEqual(panel["bars"][-1]["member"], "Not recorded")
        self.assertEqual([b["member"] for b in panel["bars"][:5]],
                         [f"Theme {i}" for i in range(5)])

    def test_ranked_leaves_out_members_holding_nothing(self):
        members = [("Roads", 9e5, 4), ("Water", 3e5, 2), ("Agriculture", 0.0, 1),
                   ("Health", 0.0, 1), ("Sports", 0.0, 1)]
        record = _decomposition("d1-90001", members, dimension="focus_area_name",
                                dimension_phrase="focus area")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual([b["member"] for b in panel["bars"]], ["Roads", "Water"])
        self.assertEqual((panel["shown"], panel["of"]), (2, 5))

    def test_ranked_with_only_the_null_member_holding_anything(self):
        members = [("(not recorded)", 5e5, 9), ("Tied", 0.0, 1), ("Untied", 0.0, 1)]
        record = _decomposition("d1-90001", members, null="(not recorded)")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual([b["role"] for b in panel["bars"]], ["not_recorded"])
        self.assertEqual((panel["shown"], panel["of"]), (0, 2))

    def test_a_zero_period_stays_on_a_time_chart(self):
        years = [("2022-2023", 5e5, 3), ("2020-2021", 2e5, 1), ("2021-2022", 0.0, 1)]
        record = _decomposition("d2-90001", years, dimension="fiscal_year",
                                temporal=True, measure="payment_amount",
                                view="view2")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual([b["member"] for b in panel["bars"]],
                         ["2020-2021", "2021-2022", "2022-2023"])

    def test_scope_is_not_translated_twice(self):
        record = _two("d1-90001", subspace=[("theme", "Theme 4 - Water")])
        record.data["subspace_phrase"] = "LSDG theme Theme 4 - Water"
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual(panel["scope"], "LSDG theme Theme 4 - Water")

    def test_time_is_in_time_order_not_stored_order(self):
        months = [("2024-03", 9e5), ("2023-11", 7e5), ("2024-01", 5e5),
                  ("2023-12", 3e5)]
        record = _decomposition("d2-90001", [(m, v, 1) for m, v in months],
                                dimension="month", temporal=True,
                                measure="payment_amount", view="view2")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual(panel["kind"], "time")
        self.assertEqual([b["member"] for b in panel["bars"]],
                         ["2023-11", "2023-12", "2024-01", "2024-03"])

    def test_time_keeps_the_twelve_largest(self):
        months = [(f"2024-{m:02d}", float(m) * 1e5) for m in range(1, 13)]
        months += [("2023-11", 0.5e5), ("2023-12", 0.25e5)]
        months.sort(key=lambda m: -m[1])
        record = _decomposition("d2-90001", [(m, v, 1) for m, v in months],
                                dimension="month", temporal=True,
                                measure="payment_amount", view="view2")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual((panel["shown"], panel["of"]), (12, 14))
        self.assertEqual([b["member"] for b in panel["bars"]],
                         [f"2024-{m:02d}" for m in range(1, 13)])

    def test_a_signed_panel_states_its_direction_once(self):
        record = _decomposition(
            "d1-90001", [(f"GP {i}", -(5 - i) * 1e7, 3) for i in range(4)],
            measure="overspend_vs_plan", dimension="gp_name")
        (panel,) = layout.build([record], "")["panels"]
        self.assertEqual(panel["direction"], "below plan")
        self.assertEqual(panel["total"], "Rs 14.00 crore below plan")
        self.assertEqual(panel["bars"][0]["value"], "Rs 5.00 crore")

    def test_every_item_carries_its_own_record_link(self):
        for case in _recorded():
            built = layout.build(case["findings"], case["tagged"],
                                 run_date=case["stamp"])
            for item in built["cards"] + built["warnings"]:
                self.assertEqual(item["url"], config.record_url(item["id"]))
            for panel in built["panels"]:
                rows = panel["rows"] if panel["kind"] == "compare" else [panel]
                for row in rows:
                    self.assertEqual(row["url"], config.record_url(row["id"]))


# ═════════════════════════════════════════════════════════════════════════════
# 4. Determinism
# ═════════════════════════════════════════════════════════════════════════════

class DeterminismTests(unittest.TestCase):

    def test_same_inputs_same_dict(self):
        for case in _recorded():
            one = layout.build(case["findings"], case["tagged"],
                               run_date=case["stamp"])
            two = layout.build(list(case["findings"]), str(case["tagged"]),
                               run_date=case["stamp"])
            self.assertEqual(one, two)
            self.assertEqual(json.dumps(one, sort_keys=False),
                             json.dumps(two, sort_keys=False))


# ═════════════════════════════════════════════════════════════════════════════
# 5. Additivity -- every other response field is the same with layout on/off
# ═════════════════════════════════════════════════════════════════════════════

def _routing(move):
    return classifier.Routing(move=move, source="rule", reason="test stub")


def _result(findings, question="q"):
    return Result(slots=Slots(question=question, expanded=question),
                  hits=[Hit(finding=f, cosine=0.7, boost=0.0, score=0.7)
                        for f in findings],
                  considered=100, best_cosine=0.7,
                  threshold=config.CANDIDATE_FLOOR, collapsed_count=0)


class AdditivityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assembler = assemble.Assembler(SimpleNamespace(corpus=_corpus()),
                                           allow_model=True, use_judge=False)
        cases = _recorded()
        cls.narrative = next(c for c in cases if c["tagged"]
                             and len(c["findings"]) >= 5)

    def _turn(self, *, move=classifier.RETRIEVE, findings=None, tagged="",
              fell_back=False, layout_on=True, walk=None):
        findings = self.narrative["findings"] if findings is None else findings
        consolidated = Consolidated(tagged=tagged, text=checks.strip_tags(tagged),
                                    fell_back=fell_back, attempts=1)
        self.assembler._retrieve = lambda message, turn_id=None: (
            _result(findings, message), {"used": True})
        with mock.patch.object(config, "LAYOUT", layout_on), \
                mock.patch.object(assemble.classifier, "classify",
                                  return_value=_routing(move)), \
                mock.patch.object(assemble.writer_mod, "consolidate",
                                  return_value=consolidated), \
                mock.patch.object(assemble.navigate, "walk",
                                  return_value=walk):
            return self.assembler.answer(self.narrative["question"],
                                         anchors=findings)

    def _response(self, answer) -> dict:
        """The /chat payload, field for field, as `main.chat` builds it."""
        from DiscoverChat import main, render
        response = main.AskResponse(
            answer=answer.text, move=answer.move, session_id="s",
            turn_id="t",
            findings=[{"id": f.id, "sentence": f.sentence,
                       "coverage": f.coverage_line(), "view": f.view_title}
                      for f in answer.findings],
            routing=answer.routing, retrieval=answer.retrieval,
            prose=answer.prose, stamp=answer.stamp,
            answer_tagged=answer.tagged_text, citations=answer.citations,
            answer_html=(render.to_html(answer.tagged_text, answer.findings,
                                        run_date=answer.stamp)
                         if answer.tagged_text else ""),
            layout=answer.layout)
        return response.model_dump()

    def _assert_additive(self, on, off):
        a, b = self._response(on), self._response(off)
        self.assertEqual(b.pop("layout"), {})
        a.pop("layout")
        self.assertEqual(a, b)
        dict_on, dict_off = on.as_dict(), off.as_dict()
        dict_on.pop("layout"), dict_off.pop("layout")
        self.assertEqual(dict_on, dict_off)

    def test_narrative_on_and_off(self):
        tagged = self.narrative["tagged"]
        on = self._turn(tagged=tagged)
        off = self._turn(tagged=tagged, layout_on=False)
        self.assertEqual(on.layout["version"], 1)
        self.assertTrue(on.layout["panels"] or on.layout["cards"])
        self.assertTrue(on.tagged_text and on.citations)
        self._assert_additive(on, off)

    def test_fallback_on_and_off(self):
        on = self._turn(fell_back=True)
        off = self._turn(fell_back=True, layout_on=False)
        self.assertEqual(on.tagged_text, "")
        self.assertEqual(on.citations, {})
        self.assertTrue(on.layout["cards"])
        self._assert_additive(on, off)

    def test_the_main_response_model_carries_it(self):
        from DiscoverChat import main
        self.assertIn("layout", main.AskResponse.model_fields)
        on = self._turn(tagged=self.narrative["tagged"])
        self.assertEqual(self._response(on)["layout"], on.layout)

    def test_empty_on_every_other_path(self):
        cases = {
            "nothing found": dict(findings=[]),
            "lookup": dict(move=classifier.LOOKUP),
            "why": dict(move=classifier.WHY),
            "navigate": dict(move=classifier.NAVIGATE, walk=navigate.Walk(
                kind="exception", findings=self.narrative["findings"][:3],
                explanation="Following the exception you were shown.")),
        }
        for name, kwargs in cases.items():
            with self.subTest(path=name):
                answer = self._turn(**kwargs)
                self.assertEqual(answer.layout, {})
                if name != "nothing found" and name != "lookup":
                    self.assertTrue(answer.findings)


# ═════════════════════════════════════════════════════════════════════════════
# 6. Weak-writer cases (ruling 7)
# ═════════════════════════════════════════════════════════════════════════════

class WeakWriterTests(unittest.TestCase):

    def test_fallback_gives_a_full_layout_in_order(self):
        for case in _recorded():
            built = layout.build(case["findings"], "", run_date=case["stamp"])
            order = {f.id: i for i, f in enumerate(case["findings"])}
            positions = [order[c["id"]] for c in built["cards"]]
            self.assertEqual(positions, sorted(positions))
            if len(case["findings"]) >= config.LAYOUT_CARDS_MIN_FINDINGS:
                self.assertTrue(built["cards"], case["question"])
            # With no prose every weight is 0, so Order decides the panels.
            firsts = [min(order[i] for i in p["ids"]) for p in built["panels"]]
            self.assertEqual(firsts, sorted(firsts))

    def test_one_long_paragraph_gives_the_same_layout(self):
        tested = 0
        for case in _recorded():
            if "\n\n" not in case["tagged"]:
                continue
            tested += 1
            spread = layout.build(case["findings"], case["tagged"],
                                  run_date=case["stamp"])
            single = layout.build(case["findings"],
                                  re.sub(r"\s*\n\s*\n\s*", " ", case["tagged"]),
                                  run_date=case["stamp"])
            self.assertEqual(spread, single)
        self.assertGreater(tested, 0)

    def test_prose_citing_one_record_of_six(self):
        case = next(c for c in _recorded() if len(c["findings"]) >= 6
                    and any(layout.chartable(f.data) for f in c["findings"]))
        findings = case["findings"][:6]
        if not any(layout.chartable(f.data) for f in findings):
            findings = ([f for f in case["findings"] if layout.chartable(f.data)][:1]
                        + case["findings"][:5])
        one = next(f for f in findings if layout.chartable(f.data))
        tagged = f"{one.display_sentence()} [{one.id}]"
        built = layout.build(findings, tagged, run_date=case["stamp"])
        self.assertEqual(_ids(built), {one.id})
        self.assertEqual(len(built["cards"]), 1)
        self.assertEqual(len(built["panels"]), 1)

    def test_no_minus_sign_reaches_any_layout(self):
        for case in _recorded():
            for tagged in (case["tagged"], ""):
                built = layout.build(case["findings"], tagged,
                                     run_date=case["stamp"])
                self.assertFalse([s for s in _strings(built) if "Rs -" in s])


class SwitchTests(unittest.TestCase):

    def test_off_returns_empty(self):
        case = _recorded()[0]
        with mock.patch.object(config, "LAYOUT", False):
            self.assertEqual(layout.build(case["findings"], case["tagged"]), {})

    def test_no_findings_returns_empty(self):
        self.assertEqual(layout.build([], "anything"), {})

    def test_the_settings_dump_lists_the_switch_and_the_caps(self):
        knobs = config.knobs()
        for key in ("layout", "layout_null_share_warn", "layout_max_cards",
                    "layout_max_panels", "layout_max_bars",
                    "layout_max_compare_rows"):
            self.assertIn(key, knobs)


if __name__ == "__main__":
    unittest.main()

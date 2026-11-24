# -*- coding: utf-8 -*-
"""WP-D14: the place profile sheets -- the builder's words, ids and checks, and
the reader's refusals.

Offline and deterministic: no model call, no embedding call, no view parquet.
Everything reads the committed store (`Insights/metainsights/profile_sheets*`)
through the reader, or builds small sheets in memory.

    python -m pytest DiscoverChat/tests/test_profile_sheets.py -q
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from DiscoverChat import config, profile_store                     # noqa: E402
from DiscoverChat.checks import numerals, _TAG                     # noqa: E402
from DiscoverChat.profile_store import (                           # noqa: E402
    ProfileStore, ProfileStoreRefused, STAMP_NAME, INDEX_NAME,
)
import phase5g_profile_sheets as p5g                               # noqa: E402

WHOLE = p5g.WHOLE_NAME
_STORE = None


def store() -> ProfileStore:
    global _STORE
    if _STORE is None:
        _STORE = profile_store.default_store()
    return _STORE


def kalimela() -> dict:
    return copy.deepcopy(store().get("gp", "119936"))


def standing(peers, rank_high, rank_low, tied_with=0, median=1.0,
             group_name="Kalimela block"):
    return {"peers": peers, "rank_high": rank_high, "rank_low": rank_low,
            "tied_with": tied_with, "median": median, "group_name": group_name}


def row_with(groups: dict, level="gp"):
    row = {"standing": groups}
    row["sentence_group"] = p5g.sentence_group(level, groups)
    return row


def read_index(directory) -> dict:
    with gzip.open(os.path.join(directory, INDEX_NAME), "rt",
                   encoding="utf-8") as fh:
        return json.load(fh)


def write_index(directory, index: dict) -> None:
    """Rewrite a copied store's index and re-stamp it, so the reader's hash
    check passes and only the check under test can catch what was planted."""
    path = os.path.join(directory, INDEX_NAME)
    with gzip.GzipFile(path, "wb", mtime=0) as gz:
        gz.write(json.dumps(index, ensure_ascii=False).encode("utf-8"))
    stamp_path = os.path.join(directory, STAMP_NAME)
    with open(stamp_path, encoding="utf-8") as fh:
        st = json.load(fh)
    data = open(path, "rb").read()
    st["files"][0].update(sha256=hashlib.sha256(data).hexdigest(),
                          bytes=len(data))
    with open(stamp_path, "w", encoding="utf-8") as fh:
        json.dump(st, fh)


VIEWS_DIR = REPO / "Insights" / "views_prdw"


class FakeStore:
    """The real store with some sheets replaced -- for proving a check fires."""

    def __init__(self, real, overrides):
        self.real, self.overrides = real, overrides

    def codes(self, level):
        return self.real.codes(level)

    def get(self, level, code):
        return copy.deepcopy(self.overrides.get((level, code))
                             or self.real.get(level, code))

    def sentence(self, sid):
        m = profile_store.SHEET_ID_RE.match(sid)
        level, code = (m.group(1), m.group(2)) if m.group(1) else ("all", "all")
        sheet = self.get(level, code)
        return next((s for s in sheet["sentences"] if s["id"] == sid), None)

    def stamp(self):
        return self.real.stamp()


# ── The standing phrase ──────────────────────────────────────────────────────
class StandingPhraseTests(unittest.TestCase):

    def test_ordinals_first_to_twenty_third(self):
        want = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th",
                "10th", "11th", "12th", "13th", "14th", "15th", "16th", "17th",
                "18th", "19th", "20th", "21st", "22nd", "23rd"]
        self.assertEqual([p5g.ordinal(n) for n in range(1, 24)], want)
        self.assertEqual([p5g.ordinal(n) for n in (111, 112, 113, 101)],
                         ["111th", "112th", "113th", "101st"])

    def test_first_is_the_most_or_the_highest(self):
        st = standing(20, 1, 20)
        self.assertEqual(p5g.exact_phrase(st, "count"), "the most")
        self.assertEqual(p5g.exact_phrase(st, "money"), "the highest")
        self.assertEqual(p5g.exact_phrase(standing(20, 20, 1), "count"),
                         "the fewest")
        self.assertEqual(p5g.exact_phrase(standing(20, 20, 1), "share"),
                         "the lowest")

    def test_the_nearer_end_is_named(self):
        # rank 13 from the highest of 16 is the 4th lowest
        self.assertEqual(p5g.exact_phrase(standing(16, 13, 4), "money"),
                         "the 4th lowest")
        self.assertEqual(p5g.exact_phrase(standing(20, 2, 19), "count"),
                         "the 2nd most")

    def test_equal_ranks_are_named_from_the_highest(self):
        self.assertEqual(p5g.exact_phrase(standing(21, 11, 11), "money"),
                         "the 11th highest")
        self.assertEqual(p5g.exact_phrase(standing(5, 3, 3), "count"),
                         "the 3rd most")

    def test_ties_read_joint(self):
        # values 9, 7, 7, 4: the two 7s are both rank 2 from the highest
        self.assertEqual(p5g.exact_phrase(standing(4, 2, 2, tied_with=1), "money"),
                         "the joint 2nd highest")
        self.assertEqual(p5g.exact_phrase(standing(6, 1, 5, tied_with=1), "count"),
                         "the joint most")

    def test_the_quarter_cut(self):
        # p = strictly smaller / peers; < 0.25 lowest, then lower-middle ...
        self.assertEqual(p5g.quarter(1, 100), "lowest")
        self.assertEqual(p5g.quarter(25, 100), "lowest")        # p = 0.24
        self.assertEqual(p5g.quarter(26, 100), "lower-middle")  # p = 0.25
        self.assertEqual(p5g.quarter(51, 100), "upper-middle")  # p = 0.50
        self.assertEqual(p5g.quarter(76, 100), "highest")       # p = 0.75
        self.assertEqual(p5g.quarter(100, 100), "highest")

    def test_fewer_than_five_peers_gives_no_standing(self):
        row = row_with({"block": standing(4, 1, 4)})
        self.assertIsNone(row["sentence_group"])
        self.assertIsNone(p5g.standing_phrase("gp", row, "count", WHOLE))

    def test_the_smallest_group_with_five_is_used_and_named(self):
        row = row_with({"block": standing(4, 1, 4),
                        "district": standing(22, 18, 5,
                                             group_name="Malkangiri district"),
                        "all": standing(30, 3, 28)})
        self.assertEqual(row["sentence_group"], "district")
        self.assertEqual(p5g.standing_phrase("gp", row, "money", WHOLE),
                         "the 5th lowest of the 22 Gram Panchayats in "
                         "Malkangiri district")

    def test_over_fifty_peers_gives_the_quarter(self):
        row = row_with({"all": standing(6800, 6790, 11)}, level="gp")
        self.assertEqual(p5g.standing_phrase("gp", row, "money", "the state"),
                         "in the lowest quarter of the 6,800 Gram Panchayats "
                         "in the state")

    def test_statewide_gives_the_block_place_and_the_state_quarter(self):
        row = row_with({"block": standing(22, 18, 5),
                        "district": standing(220, 100, 121),
                        "all": standing(6800, 6790, 11)})
        self.assertEqual(
            p5g.standing_phrase("gp", row, "money", "the state"),
            "the 5th lowest of the 22 Gram Panchayats in Kalimela block and in "
            "the lowest quarter of the 6,800 in the state")

    def test_counts_say_most_money_says_highest(self):
        row = row_with({"all": standing(20, 2, 19)})
        self.assertEqual(p5g.standing_phrase("gp", row, "count", WHOLE),
                         "the 2nd most of 20 Gram Panchayats")
        self.assertEqual(p5g.standing_phrase("gp", row, "money", WHOLE),
                         "the 2nd highest of 20 Gram Panchayats")

    def test_a_block_with_a_small_district_uses_the_larger_group(self):
        b = store().get("block", "3843")
        st = b["rows"]["A1"]["standing"]
        self.assertIn("district", st)                    # stored ...
        self.assertLess(st["district"]["peers"], p5g.MIN_PEERS)
        self.assertEqual(b["rows"]["A1"]["sentence_group"], "all")  # ... not used


# ── Zero, blank, singular and plural (Appendix A) ────────────────────────────
class SentenceFormTests(unittest.TestCase):

    def words(self, sheet):
        return p5g.main_sentences(sheet, WHOLE)

    def test_zero_forms(self):
        s = kalimela()
        for fig in ("A1", "A2", "A3", "A4", "A5", "A7", "E1", "E2", "E3",
                    "E4", "E5", "F1", "F2", "G1", "G2", "H1", "H2"):
            s["rows"][fig]["value"] = 0
        s["rows"]["A6"]["value"] = None
        s["rows"]["G3"]["value"] = None
        out = self.words(s)
        self.assertEqual(out["A1"], "Kalimela Gram Panchayat has no planned "
                                    "activities in the data.")
        self.assertNotIn("A2", out)          # none when A1 is zero
        self.assertEqual(out["A3"], "It has no planned cost on record.")
        self.assertEqual(out["A4"], "Nothing has been sanctioned on record.")
        self.assertEqual(out["A5"], "The data shows no spending on its planned "
                                    "activities.")
        self.assertNotIn("A6", out)
        self.assertNotIn("A7", out)
        self.assertEqual(out["E1"], "No works are marked ongoing.")
        self.assertEqual(out["E2"], "No works are marked completed.")
        self.assertEqual(out["E3"], "No works are marked abandoned.")
        self.assertEqual(out["E4"], "No activities have photo evidence.")
        self.assertNotIn("E5", out)
        self.assertNotIn("F1", out)          # blank share when A1 is zero
        self.assertEqual(out["F2"], "No activities have a technical approval "
                                    "on file.")
        self.assertEqual(out["G1"], "Its cashbook shows no receipts and no "
                                    "payments.")
        self.assertNotIn("G3", out)
        self.assertNotIn("H1", out)
        self.assertNotIn("H2", out)

    def test_a2_all_costed_and_f1_none_approved(self):
        s = kalimela()
        s["rows"]["A2"]["value"] = 0
        s["rows"]["F1"]["value"] = 0
        out = self.words(s)
        self.assertEqual(out["A2"], "All of them have a cost attached.")
        self.assertEqual(out["F1"], "None of the 852 activities has an "
                                    "administrative approval on file.")

    def test_a6_needs_both_planned_and_spent(self):
        s = kalimela()
        s["rows"]["A5"]["value"] = 0
        self.assertNotIn("A6", self.words(s))

    def test_a7_above_plan(self):
        s = kalimela()
        s["rows"]["A7"]["value"] = 1235000.0
        s["rows"]["A7"]["display"] = p5g.fmt_money(1235000.0, "overspend_vs_plan")
        self.assertEqual(self.words(s)["A7"], "Spending is Rs 12.35 lakh above plan.")

    def test_e5_second_sentence_dropped_without_planned_cost(self):
        s = kalimela()
        s["rows"]["E5"]["planned"] = 0
        self.assertEqual(self.words(s)["E5"], "55 works planned in 2022-2023 or "
                                              "earlier are still marked ongoing.")

    def test_h_rows_only_when_met(self):
        s = kalimela()
        out = self.words(s)
        self.assertNotIn("H1", out)          # H1 is zero for Kalimela
        self.assertNotIn("H3", out)          # 200 toilets, 200 households
        self.assertNotIn("H4", out)
        s["rows"]["H5"]["flag"] = False
        self.assertNotIn("H5", self.words(s))

    def test_i_rows_leave_out_what_is_not_reported(self):
        s = kalimela()
        s["rows"]["I3"]["remoteness"] = "Not reported"
        self.assertEqual(self.words(s)["I3"], "Its profile classes it as "
                                              "ST-majority.")
        s["rows"]["I3"]["social_composition"] = "Not reported"
        self.assertNotIn("I3", self.words(s))
        s["rows"]["I1"]["population"] = 0
        s["rows"]["I2"]["households"] = 0
        out = self.words(s)
        self.assertNotIn("I1", out)
        self.assertNotIn("I2", out)

    def test_singular(self):
        s = kalimela()
        for fig in ("E1", "E2", "E3", "E4", "E5", "F2", "H1", "H2"):
            s["rows"][fig]["value"] = 1
        s["rows"]["E3"]["top_year_count"] = 1
        s["rows"]["E4"]["uploads"] = 1
        s["rows"]["A2"]["value"] = 1
        out = self.words(s)
        self.assertTrue(out["A2"].startswith("1 of them (46.0%) has no cost"))
        self.assertTrue(out["E1"].startswith("1 work is marked ongoing, the "))
        self.assertTrue(out["E2"].startswith("1 work is marked completed, out of"))
        self.assertEqual(out["E3"], "1 work is marked abandoned, with Rs 2.72 "
                                    "lakh planned on it. It was planned in "
                                    "2024-2025.")
        self.assertTrue(out["E4"].startswith("1 activity has photo evidence "
                                             "(1 upload)"))
        self.assertTrue(out["E5"].startswith("1 work planned in 2022-2023 or "
                                             "earlier is still marked ongoing. "
                                             "Rs 89.63 lakh of its "))
        self.assertEqual(out["F2"], "1 activity has a technical approval on file.")
        self.assertEqual(out["H1"], "1 activity has an approval cost recorded "
                                    "with no approval record.")
        self.assertTrue(out["H2"].startswith("1 activity has no LSDG theme "
                                             "mapped; its planned cost is"))

    def test_singular_places_inside(self):
        d = copy.deepcopy(store().get("district", "323"))
        self.assertEqual(p5g.main_sentences(d, WHOLE)["I4"],
                         "Malkangiri district has 1 block and 1 Gram Panchayat "
                         "in the data.")
        b = copy.deepcopy(store().get("block", "3745"))
        self.assertEqual(p5g.main_sentences(b, WHOLE)["I4"],
                         "Rangeilunda block has 2 Gram Panchayats in the data.")

    def test_list_forms(self):
        line = {"year": "2025-2026", "activities": 12, "no_cost": 12,
                "planned": 0.0, "spent": 5000.0, "share": None}
        self.assertEqual(p5g.b_sentence(line), "In 2025-2026: 12 activities "
                         "(12 with no cost), nothing planned, Rs 5,000 spent.")
        line.update(planned=15000.0, spent=0.0, no_cost=0, activities=1)
        self.assertEqual(p5g.b_sentence(line), "In 2025-2026: 1 activity, "
                         "Rs 15,000 planned, nothing spent.")
        line.update(planned=0.0, spent=0.0, activities=0)
        self.assertEqual(p5g.b_sentence(line), "In 2025-2026: no planned activities.")
        c = {"name": "Roads", "activities": 3, "planned": 0.0, "spent": 2000.0}
        self.assertEqual(p5g.c_sentence(c), "Roads: 3 activities with no planned "
                                            "cost, Rs 2,000 spent.")
        c.update(spent=0.0)
        self.assertEqual(p5g.c_sentence(c), "Roads: 3 activities, with no planned "
                                            "cost and nothing spent.")
        ds = {"name": "All other schemes", "others": 2, "approvals": 1,
              "amount": 449000.0}
        self.assertEqual(p5g.ds_sentence(ds), "All other schemes: 1 approval, "
                                              "Rs 4.49 lakh sanctioned.")
        auth = {"lines": [{"name": "BDO", "approvals": 4}], "others": 0}
        self.assertEqual(p5g.d_authority_sentence(auth),
                         "Approvals on file, by who approved: BDO 4.")

    # ── WP-D14b T2c: the three zero forms (R13), from made-up rows ──────────
    def test_e5_nothing_spent(self):
        s = kalimela()
        s["rows"]["E5"]["spent"] = 0.0
        s["rows"]["E5"]["share"] = 0.0
        self.assertEqual(self.words(s)["E5"], "55 works planned in 2022-2023 or "
                         "earlier are still marked ongoing. Nothing has been "
                         "spent of their Rs 1.04 crore planned cost.")
        s["rows"]["E5"]["value"] = 1
        self.assertEqual(self.words(s)["E5"], "1 work planned in 2022-2023 or "
                         "earlier is still marked ongoing. Nothing has been "
                         "spent of its Rs 1.04 crore planned cost.")

    def test_h2_no_planned_cost(self):
        s = kalimela()
        s["rows"]["H2"]["planned"] = 0.0
        self.assertEqual(self.words(s)["H2"], "49 activities have no LSDG theme "
                         "mapped; none of them has a cost attached.")
        s["rows"]["H2"]["value"] = 1
        self.assertEqual(self.words(s)["H2"], "1 activity has no LSDG theme "
                         "mapped; it has no cost attached.")

    def test_g3_zero(self):
        s = kalimela()
        s["rows"]["G3"]["value"] = 0.0
        s["rows"]["G3"]["display"] = "0.0%"
        self.assertEqual(self.words(s)["G3"], "None of the payments is linked "
                                              "to a planned activity.")

    # ── WP-D14b T2a/T2b: two groups named (R11), F1 and G3 ranked (R12) ─────
    def two_groups(self, row, value_median, rank_high, rank_low_state):
        row["standing"] = {
            "block": standing(21, rank_high, 22 - rank_high,
                              median=value_median),
            "district": standing(200, 50, 151, median=value_median,
                                 group_name="Malkangiri district"),
            "all": standing(6800, 6800 - rank_low_state + 1, rank_low_state,
                            median=value_median, group_name="the state"),
        }
        row["sentence_group"] = p5g.sentence_group("gp", row["standing"])
        self.assertEqual(row["sentence_group"], "block")

    def test_two_groups_a3_is_the_spec_illustration(self):
        s = kalimela()
        a3 = s["rows"]["A3"]
        a3["value"] = 44700000.0
        a3["display"] = p5g.fmt_money(44700000.0)
        self.two_groups(a3, 19500000.0, 4, 4000)
        self.assertEqual(
            p5g.main_sentences(s, "the state")["A3"],
            "Its planned cost is Rs 4.47 crore, the 4th highest of the 21 Gram "
            "Panchayats in Kalimela block and in the upper-middle quarter of "
            "the 6,800 in the state. The middle value for these 21 is "
            "Rs 1.95 crore.")

    def test_two_groups_f1_and_g3(self):
        s = kalimela()
        self.two_groups(s["rows"]["F1"], 96.0, 2, 6500)
        self.two_groups(s["rows"]["G3"], 0.4217, 18, 900)
        out = p5g.main_sentences(s, "the state")
        self.assertEqual(
            out["F1"], "168 of the 852 activities (19.7%) have an "
            "administrative approval on file, the 2nd most of the 21 Gram "
            "Panchayats in Kalimela block and in the highest quarter of the "
            "6,800 in the state. The middle value for these 21 is 96.")
        self.assertEqual(
            out["G3"], "33.3% of the payments are linked to a planned activity, "
            "the 4th lowest of the 21 Gram Panchayats in Kalimela block and in "
            "the lowest quarter of the 6,800 in the state. The middle value for "
            "these 21 is 42.2%.")

    def test_one_group_keeps_the_short_middle_value(self):
        out = self.words(kalimela())
        self.assertTrue(out["F1"].endswith(" The middle value is 96."))
        self.assertTrue(out["A3"].endswith(" The middle value is Rs 3.10 crore."))
        self.assertIn("The middle value for these 20 is 602.5.", out["A1"])

    def test_the_whole_has_no_standing(self):
        out = p5g.main_sentences(copy.deepcopy(store().get("all", "all")), WHOLE)
        for row in ("A1", "A3", "A4", "A5", "A6", "E1", "E4", "F1", "G3"):
            self.assertNotIn(" of 20 ", out[row])
            self.assertNotIn("middle value", out[row])
        self.assertEqual(out["E2"], "17 works are marked completed.")


# ── Ids ──────────────────────────────────────────────────────────────────────
class IdTests(unittest.TestCase):

    def test_slug(self):
        self.assertEqual(p5g.slug("Drinking water"), "drinking-water")
        self.assertEqual(p5g.slug("Administrative & Technical Support"),
                         "administrative-technical-support")
        self.assertEqual(p5g.slug("(not recorded)"), "not-recorded")
        self.assertEqual(p5g.slug("Technical training and vocational education"),
                         "technical-training-and-vocationa")
        self.assertLessEqual(len(p5g.slug("x" * 80)), p5g.SLUG_MAX)

    def test_theme_key(self):
        self.assertEqual(p5g.theme_key("Theme 6 - Self-sufficient Infrastructure "
                                       "in Village"), "6")
        self.assertEqual(p5g.theme_key("Unmapped theme"), "unmapped")

    def test_id_shapes(self):
        self.assertEqual(p5g.sheet_id("gp", "119936", "A6"), "p-gp-119936-A6")
        self.assertEqual(p5g.sheet_id("block", "3843", "A1"), "p-block-3843-A1")
        self.assertEqual(p5g.sheet_id("all", "all", "A7"), "p-all-A7")
        self.assertEqual(p5g.sheet_id("gp", "119936", "B", "2023-2024"),
                         "p-gp-119936-B-2023-2024")
        self.assertEqual(p5g.sheet_id("block", "3843", "J", "119936"),
                         "p-block-3843-J-119936")

    def test_every_stored_id_obeys_the_rules(self):
        seen = set()
        for level in p5g.STORE_ORDER:
            for code in store().codes(level):
                for s in store().get(level, code)["sentences"]:
                    sid = s["id"]
                    self.assertLessEqual(len(sid), p5g.ID_MAX, sid)
                    self.assertNotIn(" ", sid)
                    self.assertNotIn("[", sid)
                    self.assertNotIn("]", sid)
                    self.assertNotIn(sid, seen)
                    seen.add(sid)
                    self.assertEqual(_TAG.findall(f"[{sid}]"), [sid])
                    self.assertTrue(profile_store.SHEET_ID_RE.match(sid))
        self.assertTrue(seen)

    def test_two_names_one_slug_stops(self):
        rows = [{"name": "Roads & bridges", "activities": 1, "planned": 0.0,
                 "spent": 0.0},
                {"name": "Roads  bridges", "activities": 1, "planned": 0.0,
                 "spent": 0.0}]
        target = {}
        with self.assertRaises(p5g.BuildStop):
            for r in rows:
                key = p5g.slug(r["name"])
                if key in target:
                    p5g._stop(f"two names give the C key {key!r}")
                target[key] = r


# ── Appendix A, character for character ──────────────────────────────────────
class AppendixATests(unittest.TestCase):

    def test_every_example(self):
        for prefix, lines in p5g.APPENDIX_A.items():
            for suffix, want in lines.items():
                with self.subTest(id=f"{prefix}-{suffix}"):
                    got = profile_store.sentence(f"{prefix}-{suffix}")
                    self.assertIsNotNone(got)
                    self.assertEqual(got["sentence"], want)

    def test_appendix_a_examples_are_the_spec_text(self):
        """The builder's copy is spec Appendix A (current), both ways: every
        copied example is in the spec, and every example the spec asks for is
        in the copy. The made-up two-group illustration is not a reference."""
        spec = REPO / "handoffs" / "PROFILE_SHEET_SPEC.md"
        if not spec.exists():
            self.skipTest("the spec is not in this checkout")
        text = spec.read_text(encoding="utf-8")
        appendix = text[text.index("## Appendix A — the sentence patterns (current)"):]
        examples = appendix[appendix.index("**Examples to reproduce"):
                            appendix.index("**A two-group sentence**")]
        wanted = set()
        for block in examples.split("```")[1::2]:
            for line in block.strip().splitlines():
                wanted.add(re.split(r"\s{2,}", line.strip(), maxsplit=1)[1])
        copied = {want for lines in p5g.APPENDIX_A.values()
                  for want in lines.values()}
        self.assertEqual(copied - wanted, set(), "copied but not in the spec")
        self.assertEqual(wanted - copied, set(), "in the spec but not copied")
        self.assertEqual(len(wanted), 51)     # 30 + 8 + 11 + 2


# ── The reader ───────────────────────────────────────────────────────────────
class ReaderTests(unittest.TestCase):

    def copy_store(self):
        tmp = tempfile.mkdtemp(prefix="profile_sheets_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for f in store().stamp()["files"] + [{"file": STAMP_NAME}]:
            shutil.copy(os.path.join(config.PROFILE_SHEETS_DIR, f["file"]), tmp)
        return tmp

    def test_contract(self):
        self.assertTrue(profile_store.available())
        sheet = profile_store.get("gp", "119936")
        self.assertEqual(sheet["name"], "Kalimela")
        self.assertEqual(sheet["parents"]["block"],
                         {"code": "3843", "name": "Kalimela"})
        self.assertEqual(sheet["parents"]["district"],
                         {"code": "323", "name": "Malkangiri"})
        self.assertIsNone(profile_store.get("gp", "000000"))
        self.assertIsNone(profile_store.get("county", "119936"))
        self.assertIsNone(profile_store.sentence("p-gp-000000-A1"))
        self.assertIsNone(profile_store.sentence("not an id"))
        items = profile_store.sentences("gp", "119936")
        self.assertEqual(set(items[0]), {"id", "row", "sentence", "note"})
        f1 = profile_store.sentence("p-gp-119936-F1")
        self.assertEqual(f1["note"], p5g.NOTES["no_approval"])
        self.assertEqual(profile_store.sentence("p-gp-119936-I1")["note"],
                         p5g.NOTES["self_reported"])
        self.assertIsNone(profile_store.sentence("p-gp-119936-A1")["note"])
        self.assertEqual(profile_store.stamp()["candidate_set_id"],
                         config.load_stamp()["candidate_set_id"])

    def test_hand_over_order(self):
        rows = [s["row"] for s in profile_store.sentences("block", "3843")]
        order = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "B", "C", "CT", "D",
                 "DS", "E1", "E2", "E3", "E4", "E5", "F1", "F2", "G1", "G3",
                 "H1", "H2", "I4", "J"]
        compact = [r for i, r in enumerate(rows) if i == 0 or rows[i - 1] != r]
        # D-plan, the schemes, then D-authority: D, DS, D
        self.assertEqual([r for r in compact if r != "D"],
                         [r for r in order if r in compact and r != "D"])
        ids = [s["id"] for s in profile_store.sentences("block", "3843")]
        self.assertLess(ids.index("p-block-3843-D-plan"),
                        ids.index("p-block-3843-DS-xv-finance-commission"))
        self.assertLess(ids.index("p-block-3843-DS-own-funds"),
                        ids.index("p-block-3843-D-authority"))
        self.assertLess(ids.index("p-block-3843-D-authority"),
                        ids.index("p-block-3843-E1"))

    def test_an_altered_byte_is_refused(self):
        tmp = self.copy_store()
        part = store().stamp()["files"][1]["file"]
        path = os.path.join(tmp, part)
        data = bytearray(open(path, "rb").read())
        data[len(data) // 2] ^= 0x01
        open(path, "wb").write(bytes(data))
        s = ProfileStore(tmp)
        self.assertFalse(s.available())
        with self.assertRaises(ProfileStoreRefused):
            s.get("gp", "119936")

    def test_a_missing_part_is_refused(self):
        tmp = self.copy_store()
        os.remove(os.path.join(tmp, store().stamp()["files"][1]["file"]))
        self.assertFalse(ProfileStore(tmp).available())

    def test_an_altered_index_is_refused(self):
        tmp = self.copy_store()
        with open(os.path.join(tmp, INDEX_NAME), "ab") as fh:
            fh.write(b" ")
        self.assertFalse(ProfileStore(tmp).available())

    def test_another_candidate_set_is_refused(self):
        tmp = self.copy_store()
        s = ProfileStore(tmp, expected_candidate_set="0000000000000000")
        self.assertFalse(s.available())
        with self.assertRaises(ProfileStoreRefused):
            s.verify()

    def test_a_synthetic_store_is_refused(self):
        tmp = self.copy_store()
        path = os.path.join(tmp, STAMP_NAME)
        st = json.load(open(path, encoding="utf-8"))
        st["synthetic"] = True
        json.dump(st, open(path, "w", encoding="utf-8"))
        self.assertFalse(ProfileStore(tmp).available())
        self.assertTrue(ProfileStore(tmp, allow_synthetic=True).available())

    def test_no_sheet_held_until_asked(self):
        s = ProfileStore(config.PROFILE_SHEETS_DIR)
        s.verify()
        held = json.dumps(s._index)
        # Names are in the index by design (WP-D14b T3); sheet content is not.
        self.assertIn("Kalimela", held)
        for content in ("planned activities", "Rs ", "sentences", "standing",
                        "crore", "lakh"):
            self.assertNotIn(content, held)

    # ── WP-D14b T3: the name table ──────────────────────────────────────────
    def test_place_and_find(self):
        self.assertEqual(profile_store.place("gp", "119936"), {
            "level": "gp", "code": "119936", "name": "Kalimela",
            "label": "Kalimela Gram Panchayat",
            "parents": {"block": {"code": "3843", "name": "Kalimela"},
                        "district": {"code": "323", "name": "Malkangiri"}}})
        self.assertEqual(profile_store.place("block", "3843")["label"],
                         "Kalimela block")
        self.assertEqual(profile_store.place("block", "3843")["parents"],
                         {"district": {"code": "323", "name": "Malkangiri"}})
        self.assertEqual(profile_store.place("all", "all"),
                         {"level": "all", "code": "all", "name": WHOLE,
                          "label": WHOLE, "parents": {}})
        self.assertIsNone(profile_store.place("gp", "000000"))
        self.assertEqual(profile_store.find("block", "  KALIMELA "), ["3843"])
        self.assertEqual(profile_store.find("gp", "kalimela"), ["119936"])
        self.assertEqual(profile_store.find("block", "Kalyansinghpur"), [])
        self.assertEqual(profile_store.find("block", "Kalyansingpur"), ["3914"])
        self.assertEqual(profile_store.find("district", "Nowhere"), [])
        self.assertEqual(profile_store.find("county", "Kalimela"), [])

    def test_find_returns_every_code_of_a_repeated_name(self):
        tmp = self.copy_store()
        index = read_index(tmp)
        index["places"]["gp"]["117835"]["name"] = "Kalimela"   # Chikilli
        write_index(tmp, index)
        s = ProfileStore(tmp)
        self.assertEqual(sorted(s.find("gp", "Kalimela")), ["117835", "119936"])

    def test_the_name_map_is_built_on_first_find(self):
        s = ProfileStore(config.PROFILE_SHEETS_DIR)
        s.verify()
        self.assertEqual(s._names, {})
        s.find("block", "Kalimela")
        self.assertEqual(set(s._names), {"block"})

    def test_an_index_with_no_name_table_is_refused(self):
        tmp = self.copy_store()
        index = read_index(tmp)
        del index["places"]
        write_index(tmp, index)
        s = ProfileStore(tmp)
        self.assertFalse(s.available())
        with self.assertRaisesRegex(ProfileStoreRefused, "rebuild the store"):
            s.verify()

    def test_the_places_check_catches_a_changed_name(self):
        tmp = self.copy_store()
        index = read_index(tmp)
        index["places"]["block"]["3843"]["name"] = "Kalimella"
        write_index(tmp, index)
        s = ProfileStore(tmp)
        self.assertTrue(s.available())          # re-stamped: only the check sees it
        with self.assertRaises(AssertionError):
            p5g.check_places(s)
        p5g.check_places(store())               # the real store passes

    def test_only_place_py_opens_the_store(self):
        for name in ("main.py", "assemble.py", "writer.py", "retrieval.py",
                     "judge.py", "layout.py", "render.py"):
            text = (REPO / "DiscoverChat" / name).read_text(encoding="utf-8")
            self.assertNotIn("profile_store", text, name)


# ── The checks fire (they are not vacuous) ───────────────────────────────────
class ChecksFireTests(unittest.TestCase):

    def fake(self, level, code, edit):
        sheet = copy.deepcopy(store().get(level, code))
        edit(sheet)
        return FakeStore(store(), {(level, code): sheet})

    @unittest.skipUnless((VIEWS_DIR / "view1_activity_lifecycle.parquet").exists(),
                         "the view parquets are not built in this checkout")
    def test_check_1_catches_e3_money_on_a_work_not_abandoned(self):
        # Bandhpali's E3 money as WP-D14 had it: fund_abandoned_total over every
        # row, which includes 8 rows not marked abandoned (R10).
        def edit(s):
            s["rows"]["E3"]["planned"] = 7065872.0
        with self.assertRaisesRegex(AssertionError, "E3 planned"):
            p5g.check_views(self.fake("gp", "116397", edit), str(VIEWS_DIR))
        p5g.check_views(store(), str(VIEWS_DIR))          # the real store passes

    def test_check_2_catches_a_sum_that_does_not_add_up(self):
        def edit(s):
            s["rows"]["A3"]["value"] += 1000.0
        with self.assertRaises(AssertionError):
            p5g.check_parts_add_up(self.fake("block", "3745", edit))

    def test_check_3_catches_an_averaged_share(self):
        b = store().get("block", "3745")
        avg = sum(m["share"] for m in b["lists"]["J"].values()) / 2

        def edit(s):
            s["rows"]["A6"]["value"] = avg
        with self.assertRaises(AssertionError):
            p5g.check_shares(self.fake("block", "3745", edit))
        self.assertEqual(p5g.fmt_share(b["rows"]["A6"]["value"]), "23.1%")
        self.assertEqual(p5g.fmt_share(avg), "28.8%")

    def test_check_4_catches_a_sheet_that_disagrees_with_an_insight(self):
        def edit(s):
            s["rows"]["A5"]["value"] += 50.0
        with self.assertRaises(AssertionError):
            p5g.check_insights(self.fake("gp", "119936", edit),
                               self._decompositions())

    def test_check_4_fails_when_nothing_is_compared(self):
        with self.assertRaises(AssertionError):
            p5g.check_insights(store(), [])

    def test_check_5_catches_an_invented_figure(self):
        def edit(s):
            for item in s["sentences"]:
                if item["id"] == "p-gp-119936-A6":
                    item["sentence"] = item["sentence"].replace("23.0%", "23.1%")
        with self.assertRaises(AssertionError):
            p5g.check_sentences(self.fake("gp", "119936", edit))

    def test_check_5_catches_a_display_off_its_value(self):
        def edit(s):
            s["rows"]["A3"]["display"] = "Rs 7.66 crore"
        with self.assertRaises(AssertionError):
            p5g.check_sentences(self.fake("gp", "119936", edit))

    def test_check_7_catches_a_changed_figure(self):
        def edit(s):
            s["rows"]["E1"]["standing"]["all"]["rank_high"] = 3
        with self.assertRaises(AssertionError):
            p5g.check_reference(self.fake("gp", "119936", edit))

    def test_check_5_numerals_are_the_stored_ones(self):
        allowed, displays = set(), []
        a1 = store().get("gp", "119936")["rows"]["A1"]
        p5g._allowed(a1, "count", allowed, displays)
        self.assertTrue({"852", "602.5", "2", "20"} <= allowed)
        self.assertEqual(numerals("the 2nd most of 20"), ["2", "20"])

    _DECOMP = None

    def _decompositions(self):
        if ChecksFireTests._DECOMP is None:
            from phase5d_retrieval_corpus import read_corpus_json
            ChecksFireTests._DECOMP = read_corpus_json(
                str(config.DECOMPOSE_CORPUS_PATH))["records"]
        return ChecksFireTests._DECOMP


if __name__ == "__main__":
    unittest.main()

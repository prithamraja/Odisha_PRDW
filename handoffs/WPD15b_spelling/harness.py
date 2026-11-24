#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D15b T4: the spelling harness. Offline; no model call, no API key.

    python handoffs/WPD15b_spelling/harness.py                 # the sample (Ask's registry)
    python handoffs/WPD15b_spelling/harness.py --names state.json --questions q.json

--names     a list of place names by level, JSON:
                {"district": ["Khordha", ...], "block": ["Barpali", ...],
                 "gp": [{"name": "Kalimela", "code": "119936"}, ...]}
            Default: Ask's registry over the sample database (the real slot
            reader, its validator and the committed profile sheet store).
--questions extra correctly spelled questions, JSON list of strings, added to
            set A (default: the 53 held questions + the 245 CSV rows).

Sets (WPD15b brief T4):
  A  correctly spelled questions -> nothing may change (pass mark 1)
  B  made misspellings of every name, in three question frames (marks 2-4)
  C  the PM's hand-written examples (mark 5)          -- sample only
  D  size: 6,800 + 314 + 30 made-up names, a 25-word question (mark 6)
  and the what-if: sets A and B again with the cut-off at 80 (not shipped).

Output: results.json and RESULTS.md beside this file (or --out DIR).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
import logging                                             # noqa: E402
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import config, place                       # noqa: E402
from DiscoverChat.slots import SlotExtractor, LEVELS        # noqa: E402
sys.path.insert(0, str(HERE))
from record_geography import questions as set_a_questions, FIELDS  # noqa: E402

LEVEL_WORD = {"gp": "GP", "block": "block", "district": "district"}


# ── a name list as a validator and a store ───────────────────────────────────

class ListValidator:
    """What the slot reader needs from Ask's validator, over a plain list:
    `registry_values(level)` and `validate(surface, level)` (exact, ignoring
    case, then Ask's alias tables when the alias's target is on the list)."""

    def __init__(self, names: dict):
        from query_router import entity_validator as ev
        self.values = {lv: [] for lv in LEVELS}
        self.codes = {}
        for level in LEVELS:
            for item in names.get(level, []):
                name = item["name"] if isinstance(item, dict) else item
                self.values[level].append(name)
                if level == "gp":
                    self.codes[name] = str(item.get("code") or f"X{len(self.codes):05d}")
        self.fold = {lv: {v.casefold(): v for v in vs} for lv, vs in self.values.items()}
        self.aliases = {"district": ev._DISTRICT_ALIASES, "block": ev._BLOCK_ALIASES,
                        "gp": ev._GP_ALIASES}

    def registry_values(self, level):
        return list(self.values.get(level, []))

    def validate(self, surface, level):
        key = str(surface).strip().casefold()
        name = self.fold[level].get(key)
        if name is None:
            target = {k.casefold(): v for k, v in self.aliases[level].items()}.get(key)
            name = self.fold[level].get(str(target).casefold()) if target else None
        if name is None:
            raise ValueError(f"{surface!r} is not a {level}")
        return SimpleNamespace(resolved_value=name,
                               resolved_code=self.codes.get(name) if level == "gp" else None)


class ListStore:
    """`find` and `place`, as `place.resolve` uses them, over the same list."""

    def __init__(self, validator: ListValidator):
        self.v = validator

    def find(self, level, name):
        if level == "gp":
            return [c for n, c in self.v.codes.items() if n.casefold() == str(name).casefold()]
        return [n for n in self.v.values[level] if n.casefold() == str(name).casefold()]

    def place(self, level, code):
        if level == "gp":
            name = next((n for n, c in self.v.codes.items() if c == str(code)), None)
        else:
            name = code if code in self.v.values[level] else None
        if name is None:
            return None
        return {"level": level, "code": str(code), "name": name,
                "label": f"{name} {place._LEVEL_WORD[level]}", "parents": {}}


# ── one question ─────────────────────────────────────────────────────────────

def read(se, store, text: str) -> dict:
    geo = se.read_places(text)
    readings = geo.get("readings", [])
    plan = place.resolve(text, geo["mentions"], store,
                         readings=readings) if store is not None else None
    return {"text": text, "geo": geo, "readings": readings, "not_found": geo.get("not_found", []),
            "loose": [r for r in readings if r["how"] == "loose"],
            "line": place.reading_note(text, readings),
            "nf_message": place.not_found_message(geo.get("not_found", [])),
            "payload": place.spelling_payload(text, readings, geo.get("not_found", [])),
            "plan": plan, "tried": getattr(se, "last_loose", {})}


def asks_resolve(se, store, r: dict) -> list:
    """Every quoted `ask` (R4 alternatives of loose readings, close names)
    must resolve, by the chat's own reading, to the place it names."""
    bad = []
    asks = []
    for c in place.loose_choices(r["text"], r["readings"]):
        if c["r4_chose"] and c["alternative"]:
            a = c["alternative"]
            asks.append((place._ask({"name": a["name"], "level": a["level"]}), a["level"], a["name"]))
    for c in r["payload"].get("close_names", []):
        asks.append((c["ask"], c["level"], c["label"].rsplit(" ", 1)[0] if c["level"] != "gp"
                     else c["label"].replace(" Gram Panchayat", "")))
    for ask, level, name in asks:
        again = read(se, store, ask)
        names = {(p["level"], p["name"].casefold()) for p in (again["plan"].places if again["plan"] else [])}
        if (level, name.casefold()) not in names:
            bad.append({"ask": ask, "expected": (level, name), "got": sorted(names)})
    return bad


# ── set B: made misspellings ─────────────────────────────────────────────────

SUBS = [("sh", "s"), ("th", "t"), ("kh", "k"), ("gh", "g"), ("bh", "b"),
        ("ee", "i"), ("oo", "u"), ("a", "o"), ("v", "b"), ("w", "v")]
SUB_GROUPS = [("pur", "pore", "poor"), ("garh", "gad", "gada")]


def misspellings(name: str) -> list:
    """(rule, variant) -- one mistake each, every rule that applies, at every
    place it applies."""
    out = []
    low = name
    for i, ch in enumerate(low):
        if ch.isalpha():
            out.append(("letter dropped", low[:i] + low[i + 1:]))
            out.append(("letter doubled", low[:i] + ch + low[i:]))
    for i in range(len(low) - 1):
        if low[i].isalpha() and low[i + 1].isalpha() and low[i] != low[i + 1]:
            out.append(("neighbours swapped", low[:i] + low[i + 1] + low[i] + low[i + 2:]))

    def replace_each(src, dst, rule):
        start = 0
        lw = low.lower()
        while True:
            j = lw.find(src, start)
            if j < 0:
                break
            piece = dst if not low[j].isupper() else dst[0].upper() + dst[1:]
            out.append((rule, low[:j] + piece + low[j + len(src):]))
            start = j + 1

    for a, b in SUBS:
        replace_each(a, b, f"{a}->{b}")
        replace_each(b, a, f"{b}->{a}")
    for group in SUB_GROUPS:
        for a in group:
            for b in group:
                if a != b:
                    replace_each(a, b, f"{a}->{b}")
    if low.lower().endswith("a"):
        out.append(("final a dropped", low[:-1]))
    else:
        out.append(("final a added", low + "a"))
    seen, uniq = set(), []
    for rule, v in out:
        if v.casefold() != name.casefold() and v.casefold() not in seen:
            seen.add(v.casefold())
            uniq.append((rule, v))
    return uniq


def frames(variant: str, level: str) -> list:
    return [f"How is {variant} doing?",
            f"What should I know about {variant}?",
            f"Anything notable in {variant} {LEVEL_WORD[level]}?"]


def run_set_b(se, store, names: dict, real: set) -> dict:
    rows = []
    for level in LEVELS:
        for item in names[level]:
            name = item["name"] if isinstance(item, dict) else item
            for rule, variant in misspellings(name):
                if variant.casefold() in real:
                    continue          # a real name, not a misspelling
                for k, q in enumerate(frames(variant, level)):
                    r = read(se, store, q)
                    marked = level if k == 2 else None
                    right = any(x["name"].casefold() == name.casefold()
                                and (marked is None or x["level"] == marked)
                                for x in r["readings"])
                    wrong = [(x["level"], x["name"], x.get("score")) for x in r["loose"]
                             if x["name"].casefold() != name.casefold()]
                    line_ok = all(f'Reading "{c["typed"]}"' in r["line"]
                                  for c in place.loose_choices(q, r["readings"]))
                    rows.append({"name": name, "level": level, "letters": len(name.replace(" ", "")),
                                 "rule": rule, "variant": variant, "frame": k, "question": q,
                                 "right": right, "wrong": wrong,
                                 "loose": bool(r["loose"]), "line_ok": line_ok,
                                 "asks_bad": asks_resolve(se, store, r) if r["loose"] else [],
                                 "not_found": [n["typed"] for n in r["not_found"]],
                                 "near_unmarked": near_unmarked(se, r)})
    return summarise_b(rows)


def near_unmarked(se, r) -> list:
    """Unmarked words tried with no reading that scored 80 or more at some
    level (under the cut-off, so left alone) -- the "Bhedan" case."""
    out = []
    for t in r["tried"].get("tried", []):
        if t["hit"] or t["marked"]:
            continue
        best = max((s for lv in LEVELS for _, s in se._score(t["typed"], lv, 80)), default=None)
        if best is not None:
            out.append({"typed": t["typed"], "best": best})
    return out


def summarise_b(rows: list) -> dict:
    def part(sel):
        n = len(sel)
        right = sum(r["right"] for r in sel)
        return {"questions": n, "read_right": right,
                "share": round(right / n, 4) if n else None}
    long_ = [r for r in rows if r["letters"] >= 7]
    short = [r for r in rows if 5 <= r["letters"] <= 6]
    tiny = [r for r in rows if r["letters"] < 5]
    wrong = [r for r in rows if r["wrong"]]
    near = {"Sharagada", "Sheragada", "Kalyansinghpur", "Kalyansingpur"}
    unexpected = [r for r in wrong if not ({r["name"]} | {w[1] for w in r["wrong"]}) <= near]
    return {
        "rows": rows,
        "names_7_plus": part(long_), "names_5_6": part(short), "names_under_5": part(tiny),
        "misses_7_plus": [r for r in long_ if not r["right"]],
        "misses_5_6": [r for r in short if not r["right"]],
        "wrong": wrong, "wrong_unexpected": unexpected,
        "wrong_share": round(len(wrong) / len(rows), 4) if rows else 0,
        "unexpected_share": round(len(unexpected) / len(rows), 4) if rows else 0,
        "lines_missing": [r for r in rows if r["loose"] and not r["line_ok"]],
        "asks_bad": [r for r in rows if r["asks_bad"]],
        "near_unmarked": sum(len(r["near_unmarked"]) for r in rows),
    }


# ── set A ────────────────────────────────────────────────────────────────────

def run_set_a(se, store, record: dict | None, extra: list) -> dict:
    qs = set_a_questions() + [(f"extra:{i}", q) for i, q in enumerate(extra)]
    changed, loose, nf, words = [], [], [], []
    tried, skipped, unmarked_tried = [], [], 0
    for qid, text in qs:
        r = read(se, store, text)
        if record is not None and qid in record:
            before = record[qid]
            after = {k: r["geo"][k] for k in FIELDS}
            if any(after[k] != before[k] for k in FIELDS):
                changed.append({"id": qid, "question": text,
                                "fields": [k for k in FIELDS if after[k] != before[k]]})
        if r["loose"]:
            loose.append({"id": qid, "question": text,
                          "readings": [(x["typed"], x["level"], x["name"], x["score"]) for x in r["loose"]]})
        if r["not_found"]:
            nf.append({"id": qid, "question": text, "not_found": r["not_found"]})
        t = r["tried"]
        tried.append(len(t.get("tried", [])))
        skipped.append(t.get("skipped", 0))
        un = [x["typed"] for x in t.get("tried", []) if not x["hit"] and not x["marked"]]
        if un:
            unmarked_tried += 1
            words.append({"id": qid, "words": un})
    return {"questions": len(qs), "fields_changed": changed, "loose_readings": loose,
            "not_found": nf,
            "spans_tried_per_question": {"middle": statistics.median(tried) if tried else 0,
                                         "most": max(tried, default=0)},
            "words_skipped_per_question": {"middle": statistics.median(skipped) if skipped else 0,
                                           "most": max(skipped, default=0)},
            "questions_with_unmarked_words_tried_and_left_alone": unmarked_tried,
            "examples_unmarked": words[:15]}


# ── set C ────────────────────────────────────────────────────────────────────

SET_C = [   # (question, expected: ("read", level, name) | ("none",) | ("not_found", close names))
    ("What should I know about Kalimella?", ("read", "block", "Kalimela")),
    ("How is Malkangri doing?", ("read", "district", "Malkangiri")),
    ("How is Barpalli block doing?", ("read", "block", "Barpali")),
    ("Anything in Bhubaneshwar block?", ("read", "block", "Bhubaneswar")),
    ("How is Chikili doing?", ("read", "gp", "Chikilli")),
    ("Tell me about Khurda", ("alias", "district", "Khordha")),
    ("how is kalimela doing", ("exact", "block", "Kalimela")),
    ("Is Mendrajpur behind on anything?", ("read", "gp", "Mendarajpur")),
    ("What has been found in Atabira?", ("read", "block", "Attabira")),
    ("What should I know about Kandhmal?", ("read", "district", "Kandhamal")),
    ("What has the analysis found in Koraputt?", ("read", "district", "Koraput")),
    ("Is Laxmipoor behind on anything?", ("none",)),
    ("How is Laxmipoor block doing?", ("not_found", ["Laxmipur block"])),
    ("How is Rampur block doing?", ("not_found", [])),
]


def run_set_c(se, store) -> list:
    out = []
    for q, expect in SET_C:
        r = read(se, store, q)
        answered = [(p["level"], p["name"]) for p in (r["plan"].places if r["plan"] else [])]
        hows = {(x["level"], x["name"]): x["how"] for x in r["readings"]}
        if expect[0] in ("read", "alias", "exact"):
            want = (expect[1], expect[2])
            how_ok = {"read": "loose", "alias": "alias", "exact": "exact"}[expect[0]]
            ok = want in answered and hows.get(want) == how_ok
            ok = ok and ((expect[0] == "read") == bool(r["line"]))
        elif expect[0] == "none":
            ok = not r["readings"] and not r["not_found"] and not r["line"]
        else:
            closes = [c["label"] for nf in r["payload"].get("not_found", []) for c in nf["close"]]
            ok = bool(r["not_found"]) and not r["readings"] and closes == expect[1]
        out.append({"question": q, "expected": list(expect), "ok": ok,
                    "answered": answered, "line": r["line"], "message": r["nf_message"],
                    "asks_bad": asks_resolve(se, store, r) if r["loose"] else []})
    return out


# ── set D: size ──────────────────────────────────────────────────────────────

def made_up_state() -> dict:
    gps = ["Kalimela", "Bheden", "Chikilli", "Itipur", "Hirlipali", "Bandhpali",
           "Laxmipur", "Boipariguda", "Kalyansinghpur", "Sharagada", "Mendarajpur",
           "Biswamathpur", "Haldikudar", "Andhrua", "Barimunda", "Dadhapatna",
           "Dutimendi", "Bhatigaon", "Khallikote", "Rangeilunda"]
    return {"gp": [{"name": f"{g} {k:03d}", "code": f"9{i:02d}{k:03d}"}
                   for i, g in enumerate(gps) for k in range(1, 341)],
            "block": [f"Block {k:03d}" for k in range(1, 315)],
            "district": [f"District {k:02d}" for k in range(1, 31)]}


QUESTION_25 = ("Please tell me how the planned activities and spending in "
               "Kalimella 017 compare with other panchayats in Block 093 over "
               "the last three years of the plan")


def run_set_d(runs: int = 200) -> dict:
    names = made_up_state()
    tracemalloc.start()
    t0 = time.perf_counter()
    se = SlotExtractor(validator=ListValidator(names))
    se._loose_setup()
    startup = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    se.read_places(QUESTION_25)                      # warm
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        geo = se.read_places(QUESTION_25)
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return {"names": {lv: len(v) for lv, v in names.items()},
            "question_words": len(QUESTION_25.split()),
            "runs": runs, "median_ms": round(statistics.median(times), 2),
            "p95_ms": round(times[int(0.95 * len(times)) - 1], 2),
            "max_ms": round(times[-1], 2),
            "startup_s": round(startup, 2),
            "memory_added_at_startup_mb": round(peak / 1e6, 1),
            "reading_of_the_question": [(r["level"], r["name"], r["how"], r.get("score"))
                                        for r in geo.get("readings", [])]}


# ── the run ──────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--names", help="place names by level (JSON); default Ask's registry")
    ap.add_argument("--questions", help="extra correctly spelled questions (JSON list)")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--skip-size", action="store_true")
    args = ap.parse_args(argv)

    if args.names:
        names = json.loads(Path(args.names).read_text(encoding="utf-8"))
        validator = ListValidator(names)
        se, store = SlotExtractor(validator=validator), ListStore(validator)
        record = None
    else:
        se = SlotExtractor()
        store, why = place.open_store()
        names = {lv: (se._validator.registry_values(lv) if lv != "gp" else
                      [{"name": n, "code": None} for n in se._validator.registry_values("gp")])
                 for lv in LEVELS}
        record = json.loads((HERE / "t0_geography.json").read_text(encoding="utf-8"))
    extra = json.loads(Path(args.questions).read_text(encoding="utf-8")) if args.questions else []
    se._loose_setup()
    real = {str(n["name"] if isinstance(n, dict) else n).casefold()
            for lv in LEVELS for n in names[lv]}
    from query_router import entity_validator as ev
    real |= {a.casefold() for t in (ev._DISTRICT_ALIASES, ev._BLOCK_ALIASES,
                                    ev._GP_ALIASES) for a in t}

    out = {"names": {lv: len(names[lv]) for lv in LEVELS},
           "cutoffs": dict(se._cutoff), "min_letters": config.LOOSE_MIN_LETTERS}
    out["A"] = run_set_a(se, store, record, extra)
    out["B"] = run_set_b(se, store, names, real)
    if not args.names:
        out["C"] = run_set_c(se, store)

    # The what-if: the cut-off at 80, in this process only.
    saved = dict(se._cutoff)
    se._cutoff = {lv: 80 for lv in saved}
    whatif_a = run_set_a(se, store, record, extra)
    whatif_b = run_set_b(se, store, names, real)
    se._cutoff = saved
    out["whatif_80"] = {"A_loose_readings": whatif_a["loose_readings"],
                        "A_not_found": whatif_a["not_found"],
                        "A_fields_changed": len(whatif_a["fields_changed"]),
                        "B_names_7_plus": whatif_b["names_7_plus"],
                        "B_names_5_6": whatif_b["names_5_6"],
                        "B_wrong": len(whatif_b["wrong"]),
                        "B_wrong_unexpected": [(r["variant"], r["name"], r["wrong"])
                                               for r in whatif_b["wrong_unexpected"]][:40]}
    if not args.skip_size:
        out["D"] = run_set_d()

    target = Path(args.out)
    target.mkdir(parents=True, exist_ok=True)
    (target / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1,
                                                    default=str), encoding="utf-8")
    md = report(out)
    (target / "RESULTS.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def report(o: dict) -> str:
    A, B = o["A"], o["B"]
    L = ["# WP-D15b spelling harness — results", "",
         f"Names: {o['names']}; Ask's cut-offs {o['cutoffs']}; shortest single word "
         f"tried {o['min_letters']}.", "",
         "## Pass marks", "",
         f"1. **Set A** ({A['questions']} questions): fields changed "
         f"{len(A['fields_changed'])}; loose readings {len(A['loose_readings'])}; "
         f"\"could not find\" {len(A['not_found'])}.",
         f"2. **Set B, names of 7+ letters:** {B['names_7_plus']['read_right']} of "
         f"{B['names_7_plus']['questions']} read right ({B['names_7_plus']['share']:.1%}). "
         f"Names of 5-6 letters (reported apart): {B['names_5_6']['read_right']} of "
         f"{B['names_5_6']['questions']} ({(B['names_5_6']['share'] or 0):.1%}).",
         f"3. **Set B wrong readings:** {len(B['wrong'])} ({B['wrong_share']:.2%}); "
         f"outside the known near-names: {len(B['wrong_unexpected'])} "
         f"({B['unexpected_share']:.2%}).",
         f"4. **Lines and asks:** loose readings without their line: "
         f"{len(B['lines_missing'])}; asks not resolving: {len(B['asks_bad'])}"
         + (f"; set C asks not resolving: {sum(len(c['asks_bad']) for c in o['C'])}"
            if "C" in o else "") + "."]
    if "C" in o:
        L.append(f"5. **Set C:** {sum(c['ok'] for c in o['C'])} of {len(o['C'])} as expected.")
    if "D" in o:
        D = o["D"]
        L.append(f"6. **Size** ({D['names']}, {D['question_words']}-word question, "
                 f"{D['runs']} runs): median {D['median_ms']} ms, p95 {D['p95_ms']} ms "
                 f"(max {D['max_ms']}); memory added at start-up {D['memory_added_at_startup_mb']} MB; "
                 f"start-up {D['startup_s']} s.")
    L += ["", "## Set C", "", "| Question | OK | What the officer sees first |", "|---|---|---|"]
    for c in o.get("C", []):
        L.append(f"| {c['question']} | {'yes' if c['ok'] else '**NO**'} | "
                 f"{(c['line'] or c['message'] or '(no line)').replace(chr(10), ' / ')} |")
    L += ["", "## Set B misses, names of 7+ letters", ""]
    L += [f"- {r['name']} ({r['level']}) <- {r['variant']!r} [{r['rule']}], frame {r['frame']}"
          + (f" -> not found" if r["not_found"] else "") for r in B["misses_7_plus"]] or ["None."]
    L += ["", "## Set B wrong readings", ""]
    L += [f"- {r['variant']!r} (made from {r['name']} {r['level']}) read as {r['wrong']}"
          for r in B["wrong"]] or ["None."]
    L += ["", "## Set B misses, names of 5-6 letters (reported apart)", ""]
    L += [f"- {r['name']} ({r['level']}) <- {r['variant']!r} [{r['rule']}], frame {r['frame']}"
          for r in B["misses_5_6"]] or ["None."]
    L += ["", "## Reported, not pass marks", "",
          f"- Set A questions with an unmarked word tried and left alone: "
          f"{A['questions_with_unmarked_words_tried_and_left_alone']} "
          f"(examples: {[e['words'] for e in A['examples_unmarked'][:8]]})",
          f"- Spans tried per set A question: middle {A['spans_tried_per_question']['middle']}, "
          f"most {A['spans_tried_per_question']['most']}; words skipped: middle "
          f"{A['words_skipped_per_question']['middle']}, most {A['words_skipped_per_question']['most']}",
          f"- Unmarked words in set B scoring 80 or more but under the cut-off (left alone): "
          f"{B['near_unmarked']}",
          "", "## What-if: the cut-off at 80 (harness only, not shipped)", "",
          f"- Set B, 7+ letters: {o['whatif_80']['B_names_7_plus']['read_right']} of "
          f"{o['whatif_80']['B_names_7_plus']['questions']} "
          f"({o['whatif_80']['B_names_7_plus']['share']:.1%}); 5-6 letters: "
          f"{o['whatif_80']['B_names_5_6']['read_right']} of {o['whatif_80']['B_names_5_6']['questions']} "
          f"({(o['whatif_80']['B_names_5_6']['share'] or 0):.1%})",
          f"- Set B wrong readings: {o['whatif_80']['B_wrong']}; outside the near-names: "
          f"{len(o['whatif_80']['B_wrong_unexpected'])}",
          f"- Set A: loose readings {len(o['whatif_80']['A_loose_readings'])} "
          f"{[(x['question'], x['readings']) for x in o['whatif_80']['A_loose_readings']][:10]}; "
          f"\"could not find\" {len(o['whatif_80']['A_not_found'])}; fields changed "
          f"{o['whatif_80']['A_fields_changed']}", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())

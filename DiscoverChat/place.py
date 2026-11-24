# -*- coding: utf-8 -*-
"""From the question to the places, and from the places to their sheet lines
(WP-D15 T1, T2, T4; spec handoffs/PROFILE_SHEET_SPEC.md §3, §7, §11).

Pure code: no model call, no number worked out. Three jobs.

1. RESOLVE (T1). What `SlotExtractor.geography` found in the searched text
   becomes the places to answer for, by the brief's rules in order:
     1  names to codes, through the sheet store's `find` (blocks, districts)
        and the slot reader's own code (Gram Panchayats). A name with no sheet,
        or with more than one code, is dropped and logged.
     2  one mention that resolved to a Gram Panchayat AND a block is answered
        for the BLOCK (ruling R4) unless the words next to it say Gram
        Panchayat; the level not chosen becomes the alternative. "One mention"
        is decided by position in the text (`Slots.mentions`), never by
        comparing names, so the alias pair Kalyansinghpur / Kalyansingpur
        behaves like the other four.
     3  a place named with its own parent ("Itipur in Bhubaneswar block"):
        the parent is dropped.
     4  one place left: its full sheet; two or three: lines A1-A7 of each
        (ruling R16); none, or more than PROFILE_MAX_PLACES: no sheet.
     5  the note, only when rule 2 chose between two levels.

2. THE LINES (T2). Each place's sentences exactly as the store holds them, in
   the store's order. No score, no mark, no ordering of our own (R5): every
   line is optional for the writer.

3. THE FALL-BACK GROUPS (T4). What the officer sees when no narrative is
   shown: the place facts the writer itself cited in its last attempt, or,
   when it cited none, lines A1-A7 -- each group under the place's label.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from . import checks

_log = logging.getLogger(__name__)

MAIN_ROWS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7")
FULL, MAIN = "full", "main"
PAYLOAD_VERSION = 1

# The words that say "Gram Panchayat" next to a name (rule 2). After the name:
# GP, G.P., Gram Panchayat or panchayat. Before it: GP, Gram Panchayat or
# panchayat, optionally followed by "of". "block" directly after keeps the
# block. Whole words, any case.
_GP_AFTER = re.compile(
    r"^\s+(?:G\.P\.|(?:GP|Gram\s+Panchayat|panchayat)\b)", re.I)
_GP_BEFORE = re.compile(
    r"(?<![A-Za-z0-9])(?:GP|Gram\s+Panchayat|panchayat)(?:\s+of)?\s+$", re.I)
_BLOCK_AFTER = re.compile(r"^\s+block\b", re.I)
_DISTRICT_AFTER = re.compile(r"^\s+district\b", re.I)

# Larger first. R4 answers for the block over the Gram Panchayat; the same
# reading (the larger place unless the words say otherwise) is applied to a
# name that is also a district, which the brief does not cover (report §7).
_RANK = {"district": 0, "block": 1, "gp": 2}
_LEVEL_WORD = {"gp": "Gram Panchayat", "block": "block", "district": "district"}
_LEVEL_WORDS = {"gp": "Gram Panchayats", "block": "blocks",
                "district": "districts"}
_ASK_SUFFIX = {"gp": "GP", "block": "block", "district": "district"}


# ── the place facts ──────────────────────────────────────────────────────────

class PlaceFact:
    """One sheet sentence, as the store holds it.

    It answers the few attributes the citation check and the renderer read
    from a finding (`id`, `sentence`, `display_sentence()`, `is_decomposition`,
    `data`), so step 2 binds its numerals by the same rule as a finding's. It
    is NOT a finding: it makes no card, is never required by step 4, and never
    enters the session's anchors.
    """
    is_place_fact = True
    is_decomposition = False
    view_title = "Place profile"

    def __init__(self, item: dict, place: dict):
        self.id = item["id"]
        self.row = item["row"]
        self.sentence = item["sentence"]
        self.note = item.get("note") or ""
        self.place = place
        self.label = place["label"]
        self.data = {}

    def display_sentence(self) -> str:
        return self.sentence

    def coverage_line(self) -> str:
        return self.note

    def labelled_sentence(self) -> str:
        """The sentence with the label and a colon in front when it does not
        itself begin with the label (T5): "Kalimela block: Its planned cost is
        Rs 7.65 crore, ...". So no line is ever shown without its place."""
        if self.sentence.startswith(self.label):
            return self.sentence
        return f"{self.label}: {self.sentence}"

    def __repr__(self) -> str:                               # pragma: no cover
        return f"PlaceFact({self.id})"


@dataclass
class Group:
    """One place's lines, in the store's order."""
    place: dict
    facts: list = field(default_factory=list)


# ── the plan ─────────────────────────────────────────────────────────────────

@dataclass
class Plan:
    places: list = field(default_factory=list)       # [{level, code, name, label}]
    mode: str = ""                                    # full | main | ""
    alternatives: list = field(default_factory=list)  # [{level, code, label, ask}]
    note: str = ""
    dropped: list = field(default_factory=list)       # [{name, level, why}]
    why_no_sheet: str = ""

    @property
    def named_anything(self) -> bool:
        return bool(self.places or self.dropped or self.why_no_sheet)


def _says(text: str, start: int, end: int) -> str | None:
    """'gp', 'block', 'district' or None: what the words next to one mention
    say about its level (rule 2)."""
    after, before = text[end:], text[:start]
    if _GP_AFTER.match(after) or _GP_BEFORE.search(before):
        return "gp"
    if _BLOCK_AFTER.match(after):
        return "block"
    if _DISTRICT_AFTER.match(after):
        return "district"
    return None


def _clusters(mentions: list) -> list:
    """Mentions grouped by overlapping position: one cluster = one mention in
    the text, however many levels it resolved to."""
    out = []
    for m in sorted(mentions, key=lambda x: (x["start"], -x["end"])):
        if out and m["start"] < out[-1]["end"]:
            out[-1]["items"].append(m)
            out[-1]["end"] = max(out[-1]["end"], m["end"])
        else:
            out.append({"start": m["start"], "end": m["end"], "items": [m]})
    return out


def _code_for(store, mention: dict, dropped: list) -> str | None:
    """Rule 1. The code a mention resolves to, or None (dropped, logged)."""
    level, name = mention["level"], mention["name"]
    if level == "gp":
        code = mention.get("code")
        if code and store.place("gp", code) is not None:
            return str(code)
        why = "no sheet"
    else:
        codes = store.find(level, name)
        if len(codes) == 1:
            return codes[0]
        why = "no sheet" if not codes else f"{len(codes)} places share the name"
    entry = {"name": name, "level": level, "why": why}
    if entry not in dropped:
        dropped.append(entry)
        _log.info("place dropped: %s %s (%s)", level, name, why)
    return None


def _ask(place: dict) -> str:
    return f"{place['name']} {_ASK_SUFFIX[place['level']]}"


def _short(place: dict) -> dict:
    return {"level": place["level"], "code": place["code"],
            "name": place["name"], "label": place["label"]}


def resolve(text: str, mentions: list, store, *, max_places: int = 3) -> Plan:
    """The brief's T1 rules, in order. `mentions` is `Slots.mentions` for the
    text that is searched on this turn; `store` is an open ProfileStore."""
    plan = Plan()
    chosen = []                  # (position, place dict, alternative or None)
    for cluster in _clusters(mentions or []):
        candidates = {}
        for m in cluster["items"]:
            code = _code_for(store, m, plan.dropped)
            if code is None or m["level"] in candidates:
                continue
            info = store.place(m["level"], code)
            candidates[m["level"]] = {"level": m["level"], "code": code,
                                      "name": info["name"],
                                      "label": info["label"],
                                      "parents": info["parents"]}
        if not candidates:
            continue
        said = _says(text, cluster["start"], cluster["end"])
        if said in candidates:
            pick = said
        else:
            pick = min(candidates, key=_RANK.get)
        others = sorted((lv for lv in candidates if lv != pick), key=_RANK.get)
        alternative = candidates[others[0]] if others else None
        chosen.append((cluster["start"], candidates[pick], alternative))

    # The same place named twice is one place, kept at its first mention.
    seen, unique = set(), []
    for pos, place, alt in chosen:
        key = (place["level"], place["code"])
        if key in seen:
            continue
        seen.add(key)
        unique.append((pos, place, alt))

    # Rule 3: a named parent of another named place is dropped.
    parents = set()
    for _, place, _ in unique:
        for level, parent in place["parents"].items():
            parents.add((level, parent["code"]))
    kept = [(p, pl, a) for p, pl, a in unique
            if (pl["level"], pl["code"]) not in parents]
    for _, pl, _ in unique:
        if (pl["level"], pl["code"]) in parents:
            plan.dropped.append({"name": pl["name"], "level": pl["level"],
                                 "why": "named as the parent of another place"})

    # Rule 4.
    if not kept:
        return plan
    if len(kept) > max_places:
        plan.why_no_sheet = (f"{len(kept)} places named, more than "
                             f"{max_places}")
        return plan
    plan.mode = FULL if len(kept) == 1 else MAIN
    plan.places = [_short(pl) for _, pl, _ in kept]
    choices = [(pl, a) for _, pl, a in kept if a is not None]
    plan.alternatives = [{"level": a["level"], "code": a["code"],
                          "label": a["label"], "ask": _ask(a)}
                         for _, a in choices]
    plan.note = note_for(choices)
    return plan


def note_for(choices: list) -> str:
    """Rule 5: only when rule 2 chose between two levels.

    One choice, in the brief's words:
      This answer is about Kalimela block. For the Gram Panchayat, ask about
      "Kalimela GP".
    Several, when every alternative is of one level, in one sentence pair;
    otherwise one pair per place."""
    if not choices:
        return ""
    if len(choices) == 1:
        place, alt = choices[0]
        return (f"This answer is about {place['label']}. For the "
                f"{_LEVEL_WORD[alt['level']]}, ask about \"{_ask(alt)}\".")
    levels = {alt["level"] for _, alt in choices}
    if len(levels) == 1:
        labels = [p["label"] for p, _ in choices]
        asks = [f"\"{_ask(a)}\"" for _, a in choices]
        joined = ", ".join(labels[:-1]) + " and " + labels[-1]
        return (f"This answer is about {joined}. For the "
                f"{_LEVEL_WORDS[levels.pop()]}, ask about "
                + ", ".join(asks[:-1]) + " or " + asks[-1] + ".")
    return " ".join(note_for([c]) for c in choices)


# ── the lines (T2) ───────────────────────────────────────────────────────────

def groups_for(plan: Plan, store) -> list:
    """[Group] -- each place's sentences exactly as stored, in the store's
    order: all of them for `full`, rows A1-A7 for `main`. Nothing ranked,
    filtered or marked (R5)."""
    out = []
    for place in plan.places:
        items = store.sentences(place["level"], place["code"])
        if plan.mode == MAIN:
            items = [i for i in items if i["row"] in MAIN_ROWS]
        out.append(Group(place=place,
                         facts=[PlaceFact(i, place) for i in items]))
    return out


def render_for_writer(groups: list) -> str:
    """The PLACE FACTS blocks of the writer's request, one per place:

        PLACE FACTS — Kalimela block
        [p-block-3843-A1] Kalimela block has 852 planned activities, ...
        [p-block-3843-F1] 168 of the 852 activities (19.7%) have ...
            (An activity with no approval on file is not known to be ...)

    A sentence with a note carries it on one indented bracket line, as a
    breakdown carries its scope note."""
    blocks = []
    for group in groups:
        lines = [f"PLACE FACTS — {group.place['label']}"]
        for fact in group.facts:
            lines.append(f"[{fact.id}] {fact.sentence}")
            if fact.note:
                lines.append(f"    ({fact.note})")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def all_facts(groups: list) -> list:
    return [f for g in groups for f in g.facts]


def used_in(tagged: str, groups: list) -> list:
    """The place facts a piece of tagged prose cites: ids among those handed,
    in the order first cited, each once. This is `place.lines_used` (R19)."""
    handed = {f.id for f in all_facts(groups)}
    out = []
    for tag in checks.cited_ids(tagged or ""):
        if tag in handed and tag not in out:
            out.append(tag)
    return out


# ── the fall-back groups (T4) ────────────────────────────────────────────────

def main_lines(groups: list) -> list:
    """Each place's lines A1-A7 (the code-supplied set, R19's last resort)."""
    return [Group(place=g.place,
                  facts=[f for f in g.facts if f.row in MAIN_ROWS])
            for g in groups]


def fallback_groups(groups: list, last_prose: str) -> list:
    """T4. Per place: the facts of that place the writer cited in its last
    attempt, in the order first cited, each once; when it cited none of that
    place's facts (or wrote nothing), that place's lines A1-A7."""
    cited = used_in(last_prose, groups)
    order = {fact_id: i for i, fact_id in enumerate(cited)}
    out = []
    for group in groups:
        mine = sorted((f for f in group.facts if f.id in order),
                      key=lambda f: order[f.id])
        if not mine:
            mine = [f for f in group.facts if f.row in MAIN_ROWS]
        out.append(Group(place=group.place, facts=mine))
    return out


def render_groups(groups: list) -> str:
    """What the officer reads: each group under a line holding the place's
    label, every sentence in its stored wording, a note on its own line --
    so "Its planned cost is..." is never shown without its place. Bulleted,
    for the reason `assemble.render_finding` gives (no list numbers)."""
    blocks = []
    for group in groups:
        lines = [group.place["label"]]
        for fact in group.facts:
            lines.append(f"- {fact.sentence}")
            if fact.note:
                lines.append(f"   ({fact.note})")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def shown_ids(groups: list) -> list:
    return [f.id for g in groups for f in g.facts]


# ── the payload (T5) ─────────────────────────────────────────────────────────

def payload(plan: Plan, groups: list, *, lines_used: list,
            insights_offered: int, insights_held_back: int) -> dict:
    return {"version": PAYLOAD_VERSION,
            "mode": plan.mode,
            "answered": [dict(p) for p in plan.places],
            "alternatives": [dict(a) for a in plan.alternatives],
            "note": plan.note,
            "lines_offered": len(all_facts(groups)),
            "lines_used": list(lines_used),
            "insights_offered": insights_offered,
            "insights_held_back": insights_held_back}


# ── /record for a place fact (T5.2) ──────────────────────────────────────────

def record_payload(store, fact_id: str) -> dict | None:
    """One sheet sentence for `/record/{id}`: the sentence, the place's label,
    the row, the stored figures of that row exactly as the sheet holds them
    (`rows[row]` for a main-row line, plus G2 for the G1 line which states
    both; `lists[row][key]` for a list line), the note and the run stamp.
    None for anything that is not a sheet sentence of this store."""
    from . import config, profile_store
    match = profile_store.SHEET_ID_RE.match(fact_id or "")
    if store is None or not match:
        return None
    level, code = ((match.group(1), match.group(2)) if match.group(1)
                   else ("all", "all"))
    sheet = store.get(level, code)
    if sheet is None:
        return None
    item = next((s for s in sheet["sentences"] if s["id"] == fact_id), None)
    if item is None:
        return None
    row, key = item["row"], item.get("key")
    if key is None:
        figures = {row: sheet["rows"].get(row)}
        if row == "G1" and "G2" in sheet["rows"]:
            figures["G2"] = sheet["rows"]["G2"]
    else:
        figures = {row: (sheet.get("lists", {}).get(row) or {}).get(key)}
    note = (store.sentence(fact_id) or {}).get("note")
    return {
        "found": True,
        "id": fact_id,
        "record_type": "place_fact",
        "sentence": item["sentence"],
        "label": sheet["label"],
        "place": {"level": sheet["level"], "code": sheet["code"],
                  "name": sheet["name"], "parents": sheet.get("parents", {})},
        "row": row,
        "key": key,
        "figures": figures,
        "note": note or "",
        "view": "Place profile",
        "run_stamp": config.run_stamp_line(),
        "candidate_set_id": store.stamp().get("candidate_set_id"),
        "url": config.record_url(fact_id),
    }


# ── the store, opened once ───────────────────────────────────────────────────

def open_store():
    """(store, why). The committed store, verified; or (None, the reason) --
    never an exception, so the service never fails to start because of the
    sheets (T5.7)."""
    try:
        from . import profile_store
        store = profile_store.default_store()
        store.verify()
        return store, "ok"
    except BaseException as exc:          # SystemExit from config included
        if isinstance(exc, KeyboardInterrupt):
            raise
        return None, f"{type(exc).__name__}: {exc}"

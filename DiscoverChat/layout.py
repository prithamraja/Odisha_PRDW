# -*- coding: utf-8 -*-
"""The Insight report's visual layer: cards, charts and a warning box, drawn by
code (WP-D12, D62).

THE ONE PRINCIPLE: THE MODEL CHOOSES AND ARRANGES; CODE DRAWS. The judge picked
the records and the writer wrote prose around them. Everything this module
returns is built from those same stored records by deterministic code: no model
call, no network, no file write, and no figure that a stored record does not
hold. Every figure is a stored value put through the corpus's own formatter
(`phase5f_decompose._fmt` / `_pct`, `phase5b_report._num`); nothing is summed,
subtracted or divided here.

DESIGNED AROUND A MID-SIZE WRITER (ruling 7). The layout asks the writer for
nothing and depends on it for nothing. It is built on the bare-sentence
fallback too, where there is no tagged prose at all: then every finding counts
as cited and every weight is 0, so the judge's order decides. Every item
carries its own record link, so the frontend never needs the `citations` map
(which is empty on the fallback) to link a card, a warning or a chart row.

    build(findings, tagged_text, run_date=...)   the `layout` field of /chat
    parity_check(corpus)                         the gate's whole-corpus proof
                                                 that these numbers are the
                                                 corpus's numbers

Shared definitions (brief T1.1):
  Order   the order of `findings` as handed in (the judge's picks, in the
          service's own order)
  Cited   ids tagged in the prose AND in `findings`; on the fallback, all
  Weight  how many numerals in the prose `checks.bind_numerals` bound to a
          record; ties break by Order
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache

from . import checks, config, glossary
from .corpus import members_of
from phase5b_report import _num, display_band_labels             # noqa: E402
from phase5f_decompose import NULL_LABEL, _fmt, _pct             # noqa: E402

VERSION = 1

# How the null member reads on screen. The stored label is "(not recorded)";
# the parentheses are the engine's marker that it is not a real category.
NOT_RECORDED = "Not recorded"

# Chartable shapes. `mixed` nets parts that run both ways, so its total "is not
# a size" (the record says so itself) and a bar of its share would be a bar of a
# share of the gross dressed up as a share of the net.
_ONE_SIGN = ("all_positive", "all_negative")


# ═════════════════════════════════════════════════════════════════════════════
# Formatting: the corpus's own functions, never a second formatter
# ═════════════════════════════════════════════════════════════════════════════

def _is_signed(measure: str) -> bool:
    return glossary.signed_below(measure) is not None


def signed_value(view: str, measure: str, value: float) -> str:
    """A stored value through the stored formatter, its direction in words.

    For the two signed measures the minus sign is replaced by the stored
    "below" words through `glossary.signed_money` -- the SAME function the
    prose's display sentences use (WP-D13 Fix 1), so a card and a sentence can
    never word one figure two ways. A positive figure takes the stored "above"
    words. Every other measure is the formatter's output untouched.
    """
    shown = _fmt(view, measure, value)
    if not _is_signed(measure):
        return shown
    if value < 0:
        return glossary.signed_money(shown, measure)
    if value > 0:
        return f"{shown} {glossary.signed_above(measure)}"
    return shown


def _bar_value(view: str, measure: str, value: float) -> str:
    """A bar's value: the magnitude, because the panel states the direction
    once in words ("all figures below plan"). Only a signed measure loses its
    sign here, and only because the words carry it; any other measure is
    formatted exactly as stored, minus sign included if it ever had one."""
    if _is_signed(measure):
        return _fmt(view, measure, abs(value))
    return _fmt(view, measure, value)


def _direction(data: dict) -> str | None:
    """'below plan' / 'above plan' for a one-signed record of a signed measure,
    else None. The words are `_SIGNED_DIRECTION`'s, through the glossary."""
    measure = data.get("measure", "")
    if data.get("signs") == "all_negative":
        return glossary.signed_below(measure)
    if data.get("signs") == "all_positive":
        return glossary.signed_above(measure)
    return None


@lru_cache(maxsize=None)
def _display(text: str, view: str) -> str:
    """`glossary.render`, remembered. The glossary builds its whole substitution
    pattern on every call, which is nothing for one sentence and most of the
    cost of a whole-corpus sweep; its output is a pure function of its inputs,
    so remembering it changes no string."""
    return glossary.render(text, view)


def member_name(name, view: str) -> str:
    """A member as an officer reads it: the null label as "Not recorded", every
    other name through the glossary's own display path (`glossary.render` --
    the one that puts "people" on a size band, WP-D11b ruling 3, and that the
    display sentence of every record goes through)."""
    if name == NULL_LABEL:
        return NOT_RECORDED
    # Stripped: a few stored labels carry a trailing space ("Theme 5 - Clean
    # and Green Village "), which is invisible in a sentence and not in a label.
    return _display(str(name), view).strip()


def _scope(data: dict) -> str:
    """`subspace_phrase` with a size band shown with its unit (WP-D11b ruling
    3, `display_band_labels`) and nothing else changed.

    NOT `glossary.render`: the phrase is already in officer words (the builder
    wrote it with `display_name`), and rendering it again re-translates them --
    "LSDG theme Theme 4" became "LSDG LSDG theme Theme 4" on 7 of the corpus's
    300 distinct scopes."""
    return display_band_labels(str(data.get("subspace_phrase", "")))


def _rows(n) -> str:
    """A row count, grouped as the corpus groups it (`_num`)."""
    return _num(int(n), 0)


# ═════════════════════════════════════════════════════════════════════════════
# The parts, each from ONE stored record
# ═════════════════════════════════════════════════════════════════════════════

def card_for(finding) -> dict:
    """One card. A decomposition shows its total; a pattern its sentence."""
    data = finding.data
    if finding.is_decomposition:
        return {"id": finding.id, "url": config.record_url(finding.id),
                "kind": "total",
                "value": signed_value(data["view"], data["measure"],
                                      data["total"]),
                "label": data.get("measure_phrase", ""),
                "scope": _scope(data)}
    return {"id": finding.id, "url": config.record_url(finding.id),
            "kind": "pattern",
            "text": finding.display_sentence(),
            "scope": _scope(data)}


def _card_keys(finding) -> set:
    """What "the same measure" means for the one-card-per-measure rule.

    The stored measure name AND its officer phrase. The name alone lets the
    same quantity through twice when two analysis tables call it differently
    (view1 `total_cost` and view3 `planned_cost` are both "planned cost"), and
    two cards reading "planned cost" are the near-repeat the rule is there to
    skip. A pattern's phrase comes from the same glossary table as a
    decomposition's `measure_phrase`.
    """
    data = finding.data
    measure = str(data.get("measure", ""))
    phrase = (data.get("measure_phrase") if finding.is_decomposition
              else _display(measure, finding.view))
    return {("measure", measure), ("phrase", str(phrase or measure))}


def null_member(data: dict) -> dict | None:
    return next((m for m in members_of(data) if m.get("is_null")), None)


def warning_for(finding, member: dict) -> dict:
    """One "Needs checking" line, from the record's null member."""
    data = finding.data
    return {"id": finding.id, "url": config.record_url(finding.id),
            "rows": _rows(member["rows"]),
            "missing": data.get("dimension_phrase", ""),
            "measure": data.get("measure_phrase", ""),
            "share": _pct(abs(float(member["share"]))),
            "amount": signed_value(data["view"], data["measure"],
                                   member["value"]),
            "scope": _scope(data)}


def _bar(data: dict, member: dict) -> dict:
    share = abs(float(member["share"]))
    return {"member": member_name(member["member"], data["view"]),
            "fraction": share,
            "share": _pct(share),
            "value": _bar_value(data["view"], data["measure"],
                                member["value"]),
            "role": "not_recorded" if member.get("is_null") else "member"}


def chartable(data: dict) -> bool:
    """A decomposition whose parts all run one way and whose total is not 0."""
    return (data.get("record_type") == "decomposition"
            and data.get("signs") in _ONE_SIGN
            and float(data.get("total") or 0.0) != 0.0
            and int(data.get("n_members") or 0) >= 2)


def panel_kind(data: dict) -> str | None:
    if not chartable(data):
        return None
    if int(data["n_members"]) == 2:
        return "compare"
    return "time" if data.get("dimension_is_temporal") else "ranked"


def _compare_row(finding, member_order: list) -> dict:
    data = finding.data
    by_name = {m["member"]: m for m in members_of(data)}
    return {"id": finding.id, "url": config.record_url(finding.id),
            "label": data.get("measure_phrase", ""),
            "total": signed_value(data["view"], data["measure"], data["total"]),
            "direction": _direction(data),
            "parts": [_bar(data, by_name[name]) for name in member_order]}


def _compare_panel(findings: list) -> dict:
    """Records sharing one dimension, one pair of members and one slice, as one
    panel with a row per record. The member order is the first row's (its
    stored order, largest first) and every other row follows it, so a column
    means the same member all the way down."""
    first = findings[0].data
    order = [m["member"] for m in members_of(first)]
    return {"kind": "compare",
            "ids": [f.id for f in findings],
            "by": first.get("dimension_phrase", ""),
            "scope": _scope(first),
            "members": [member_name(name, first["view"]) for name in order],
            "rows": [_compare_row(f, order) for f in findings]}


def _bars_panel(finding, kind: str) -> dict:
    data = finding.data
    members = members_of(data)
    real = [m for m in members if not m.get("is_null")]
    null = [m for m in members if m.get("is_null")]
    if kind == "time":
        # The largest periods (stored order is largest first), then put into
        # time order -- never stored order. Every period label the corpus holds
        # ('2024-2025', '2024-03', '2024-Q1') sorts into time order as text.
        cap = config.LAYOUT_MAX_TIME_BARS
        kept = sorted(real[:cap], key=lambda m: str(m["member"]))
    else:
        # A member holding exactly nothing is not one of "the largest": 12,292
        # ranked records would otherwise fill their five bars with "Rs 0 ·
        # 0.0%" (Cuttack's tied grant: 3 focus areas hold money, 22 hold none).
        # `of` still counts every member, so the caption stays true -- "the 3
        # largest of 25". A zero PERIOD is kept on a time chart: a year with
        # nothing in it is information.
        kept = [m for m in real if float(m["value"]) != 0.0]
        kept = kept[:config.LAYOUT_MAX_BARS]
    # The null member is always drawn, as an extra grey bar, even when it is not
    # among the largest: a missing-record share that a chart quietly dropped
    # would be the same figure without its warning.
    bars = [_bar(data, m) for m in kept] + [_bar(data, m) for m in null]
    return {"kind": kind,
            "id": finding.id, "ids": [finding.id],
            "url": config.record_url(finding.id),
            "label": data.get("measure_phrase", ""),
            "by": data.get("dimension_phrase", ""),
            "scope": _scope(data),
            "total": signed_value(data["view"], data["measure"], data["total"]),
            "direction": _direction(data),
            "shown": len(kept), "of": len(real),
            "bars": bars}


def panel_for(finding) -> dict | None:
    """The panel ONE record would get on its own, or None if it is not
    chartable. What `build` uses for every non-compare panel, and what the
    whole-corpus sweep exercises."""
    kind = panel_kind(finding.data)
    if kind is None:
        return None
    if kind == "compare":
        return _compare_panel([finding])
    return _bars_panel(finding, kind)


def _compare_key(data: dict) -> tuple:
    subspace = tuple(tuple(pair) for pair in (data.get("subspace") or []))
    return (data.get("dimension"),
            frozenset(m["member"] for m in members_of(data)),
            subspace)


# ═════════════════════════════════════════════════════════════════════════════
# The entry point
# ═════════════════════════════════════════════════════════════════════════════

def build(findings: list, tagged_text: str, *, run_date: str = "") -> dict:
    """The `layout` field for one answer that shows findings. `{}` when the
    switch is off or there is nothing to lay out.

    Pure: the same findings and prose give the same dict, and nothing here
    reads a clock, a model or a file beyond the already-loaded records.
    """
    if not config.LAYOUT or not findings:
        return {}

    unique, order = [], {}
    for finding in findings:
        if finding.id not in order:
            order[finding.id] = len(unique)
            unique.append(finding)

    if tagged_text:
        cited = set(checks.cited_ids(tagged_text)) & set(order)
        weight = Counter(
            b["matched"] for b in checks.bind_numerals(
                tagged_text, unique, run_date=run_date) if b["matched"])
    else:
        # The bare-sentence fallback prints every finding verbatim.
        cited = set(order)
        weight = Counter()
    shown = [f for f in unique if f.id in cited]           # in Order

    return {"version": VERSION,
            "cards": _cards(shown, len(unique)),
            "warnings": _warnings(shown, order),
            "panels": _panels(shown, order, weight, len(unique))}


def _cards(shown: list, n_findings: int) -> list:
    if n_findings < config.LAYOUT_CARDS_MIN_FINDINGS:
        return []
    cards, seen = [], set()
    for finding in shown:
        if finding.is_decomposition and finding.data.get("signs") == "mixed":
            continue
        keys = _card_keys(finding)
        if keys & seen:
            continue
        seen |= keys
        cards.append(card_for(finding))
        if len(cards) >= config.LAYOUT_MAX_CARDS:
            break
    return cards


def _warnings(shown: list, order: dict) -> list:
    best = {}
    for finding in shown:
        if not finding.is_decomposition:
            continue
        # WP-D13 Fix 7 T3 (D66): no warning from a mixed-sign record. Its
        # parts move both ways, so the "not recorded" share is a share of all
        # the money moving, not of the net, and "they account for 45% of
        # spending measured against plan" would be loose. Cards and charts
        # already skip these records (29 in the corpus).
        if finding.data.get("signs") == "mixed":
            continue
        member = null_member(finding.data)
        if member is None:
            continue
        share = abs(float(member["share"]))
        if share < config.LAYOUT_NULL_SHARE_WARN:
            continue
        dimension = finding.data.get("dimension")
        candidate = (share, -order[finding.id], finding, member)
        if dimension not in best or candidate[:2] > best[dimension][:2]:
            best[dimension] = candidate
    ranked = sorted(best.values(), key=lambda c: (-c[0], -c[1]))
    return [warning_for(finding, member)
            for _, _, finding, member in ranked[:config.LAYOUT_MAX_WARNINGS]]


def _panels(shown: list, order: dict, weight: Counter, n_findings: int) -> list:
    groups, ranked = {}, []
    for finding in shown:
        kind = panel_kind(finding.data)
        if kind is None:
            continue
        if kind == "compare":
            groups.setdefault(_compare_key(finding.data), []).append(finding)
        else:
            ranked.append((-weight[finding.id], order[finding.id],
                           _bars_panel(finding, kind)))
    for members in groups.values():
        rows = sorted(members, key=lambda f: (-weight[f.id], order[f.id]))
        rows = rows[:config.LAYOUT_MAX_COMPARE_ROWS]
        ranked.append((-sum(weight[f.id] for f in rows),
                       min(order[f.id] for f in rows),
                       _compare_panel(rows)))
    ranked.sort(key=lambda item: (item[0], item[1]))
    cap = (config.LAYOUT_MAX_PANELS
           if n_findings >= config.LAYOUT_CARDS_MIN_FINDINGS
           else config.LAYOUT_MAX_PANELS_SMALL)
    return [panel for _, _, panel in ranked[:cap]]


# ═════════════════════════════════════════════════════════════════════════════
# The gate's proof: the layout's numbers are the corpus's numbers
# ═════════════════════════════════════════════════════════════════════════════

def _stored_form(text: str, measure: str) -> str:
    """A layout string with its direction words taken off, so it can be looked
    for in the stored sentence, which carries a minus sign instead."""
    for words in (glossary.signed_below(measure), glossary.signed_above(measure)):
        if words:
            text = text.replace(" " + words, "")
    return text


def parity_check(corpus) -> str:
    """Over every decomposition in the corpus, independently of `build`'s rules:

      1. the card value's digits are the digits of the stored `total_display`;
      2. where the record is `concentrated`, the top member's share and value
         as the record's panel draws them appear verbatim in the stored
         sentence ("accounts for 95.7% of it (Rs 2.13 crore)"), sign aside;
      3. where it has a null member, the warning's row count and amount appear
         verbatim in the stored sentence's "not on file" clause, sign aside.

    Raises AssertionError naming the first records that disagree.
    """
    problems = []
    records = concentrated = nulls = 0
    for finding in corpus.all():
        if not finding.is_decomposition:
            continue
        records += 1
        data = finding.data
        measure = data["measure"]
        stored = finding.sentence.replace("Rs -", "Rs ")

        value = card_for(finding)["value"]
        if checks.numerals(value) != checks.numerals(str(data["total_display"])):
            problems.append((finding.id, "card", value, data["total_display"]))

        if data.get("shape") == "concentrated":
            concentrated += 1
            panel = panel_for(finding)
            top = member_name(members_of(data)[0]["member"], data["view"])
            bars = (panel["rows"][0]["parts"] if panel and panel["kind"] == "compare"
                    else (panel or {}).get("bars", []))
            bar = next((b for b in bars if b["member"] == top), None)
            if bar is None or (f"accounts for {bar['share']} of it "
                               f"({bar['value']})") not in stored:
                problems.append((finding.id, "top member", bar))

        member = null_member(data)
        if member is not None:
            nulls += 1
            warning = warning_for(finding, member)
            amount = _stored_form(warning["amount"], measure)
            if (f"{warning['rows']} rows carry no" not in stored
                    or f"account for {amount}." not in stored):
                problems.append((finding.id, "not recorded", warning["rows"],
                                 warning["amount"]))
    assert not problems, (f"{len(problems)} records disagree with their "
                          f"stored sentence: {problems[:3]}")
    return (f"{records:,} decompositions: card totals = total_display; "
            f"{concentrated:,} concentrated top members and {nulls:,} "
            f"'not recorded' rows/amounts found verbatim in the stored sentence")

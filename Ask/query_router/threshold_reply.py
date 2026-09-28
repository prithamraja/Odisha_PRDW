"""A threshold, read out of an officer's reply — and asked for in plain words
(WP-6c T1).

THE DEFECT (pilot feedback, 2026-09-28). The bot asked "For which amount
threshold?", and a bare figure ("20000", "₹20,000", "2 lakh") resumed fine. Any
words around it did not: "above ₹20,000" failed strict validation, drew one
"I still need a amount threshold…", and the next wordy reply — or any over three
words, like "more than 20,000 rupees" — routed as a NEW question, landed on the
same template, and asked again. That was the loop. Worse, a direction word was
never read: "under 2 lakhs" given to an "above" question bound 2 lakh and
answered ABOVE 2 lakh, silently.

WHAT THIS MODULE DOES, deterministic first:

  1. `read_reply` finds ONE figure — the rupee reader the question path already
     uses (`router.amount_from_text`), then a plain number for the percent /
     days / activity-count readings — and the direction word written beside it.
     Nothing else is stripped: the figure still goes through `parse_amount` and
     the range check exactly as a typed number does.
  2. When there is no figure but there IS a number word ("twenty thousand"), the
     caller may ask the extractor model once (`entity_extractor.read_figure`).
  3. The direction read is compared with the slot's own — derived from the SQL
     operator by `tools/derive_catalog.py` and written on the slot as
     `direction` / `unit`. A contradiction is asked about, never bound, and the
     SQL operator is never flipped at run time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Chip

# The slot types this module reads replies for.
NUMERIC_SLOT_TYPES = frozenset({"threshold", "amount_threshold", "top_n"})


def slot_meta(template: dict | None, slot_name: str) -> dict:
    """{'unit': …, 'direction': …} as the catalogue declares it, or {}."""
    for slot in (template or {}).get("param_slots", []):
        if slot.get("name") == slot_name:
            return {k: slot[k] for k in ("unit", "direction") if k in slot}
    return {}


def numeric_meta(param_slots: list[dict]) -> dict[str, dict]:
    """slot name -> its declared unit and direction, for every slot that has them."""
    return {s["name"]: {k: s[k] for k in ("unit", "direction") if k in s}
            for s in param_slots if "unit" in s or "direction" in s}


# ── Direction words ───────────────────────────────────────────────────────────

# Longest phrases first inside each alternation, so "not more than" is one match
# rather than "more than" read the wrong way round.
_ABOVE = (r"not\s+less\s+than|no\s+less\s+than|not\s+fewer\s+than|more\s+than|"
          r"greater\s+than|higher\s+than|at\s+least|a\s+minimum\s+of|minimum\s+of|"
          r"in\s+excess\s+of|upwards\s+of|exceeding|exceeds?|above|over|>=|≥|>")
_BELOW = (r"not\s+more\s+than|no\s+more\s+than|not\s+over|less\s+than|fewer\s+than|"
          r"lower\s+than|at\s+most|a\s+maximum\s+of|maximum\s+of|up\s*to|within|"
          r"below|under|<=|≤|<")
_DIRECTION_RE = re.compile(rf"(?<!\w)(?:(?P<below>{_BELOW})|(?P<above>{_ABOVE}))(?!\w)",
                           re.IGNORECASE)
# "20,000 and above", "10 or more", "20000+"
_TRAILING_RE = re.compile(
    r"^\s*(?:rupees|rs\.?|/-|%|percent|per\s*cent|days?|activities)?\s*"
    r"(?:(?:and|or)\s+(?:(?P<above>above|more|over|higher|greater|upwards)|"
    r"(?P<below>below|less|under|lower|fewer))\b|(?P<plus>\+))",
    re.IGNORECASE)
# The words that may sit between a direction word and its figure: "above a
# planned cost of ₹20,000". A closed set, because "under" is also how officers
# name a scheme ("under SFC") and must not reach a figure further along.
_FILLER = frozenset("""a an the of rs rs. inr ₹ planned estimated approved sanctioned
    total cost costs value amount budget spend spending expenditure about around
    approx approximately roughly just say rupees is be only threshold limit figure
    than""".split())


def _direction_word(match: re.Match) -> str:
    return "below" if match.group("below") else "above"


def direction_at(text: str, start: int, end: int) -> str | None:
    """The direction written beside the figure at text[start:end], or None."""
    trailing = _TRAILING_RE.match(text[end:])
    if trailing:
        return "below" if trailing.group("below") else "above"
    before = text[:start]
    last = None
    for m in _DIRECTION_RE.finditer(before):
        last = m
    if last is None:
        return None
    gap = before[last.end():].replace("₹", " ₹ ").split()
    if all(word.lower().strip(",.:") in _FILLER for word in gap):
        return _direction_word(last)
    return None


# ── The figure ────────────────────────────────────────────────────────────────

# A fiscal year inside a reply is not the threshold: "above 1 lakh for 2024-25".
_YEAR_SPAN_RE = re.compile(r"\b(?:19|20)\d{2}\s*[-–/]\s*\d{2,4}\b|\bFY\s*\d{2,4}\b",
                           re.IGNORECASE)
# The non-money readings of $threshold: a count, a percentage, days. "20k" is
# kept whole for parse_amount; the other unit words carry nothing a number does
# not, and "25 percent" would fail parse_amount as an unknown unit.
_PLAIN_RE = re.compile(
    r"(?<![\w.,])(?P<num>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent\b|per\s*cent\b|k\b|days?\b|activities\b|activity\b)?",
    re.IGNORECASE)
_DROP_UNITS = re.compile(r"\s*(?:%|percent|per\s*cent|days?|activities|activity)\s*$",
                         re.IGNORECASE)


@dataclass(frozen=True)
class Reading:
    figure: str            # what binds: "20,000", "2 lakh", "20k", "25"
    direction: str | None  # "above" | "below" | None
    written: str           # the figure as the officer wrote it, for the chips
    source: str            # "reader" | "model"


def clean_figure(figure: str) -> str:
    """Drop a unit word parse_amount does not know ("25 percent" -> "25")."""
    return _DROP_UNITS.sub("", str(figure).strip()).strip()


def read_reply(text: str) -> Reading | None:
    """ONE figure and the direction beside it, or None (no figure, or several)."""
    from .router import _AMOUNT_TEXT_RE, amount_from_text   # the question path's reader
    text = str(text or "")
    masked = _YEAR_SPAN_RE.sub(lambda m: " " * len(m.group(0)), text)
    found = amount_from_text(masked)
    if found is not None:
        m = next(_AMOUNT_TEXT_RE.finditer(masked))
        return Reading(found, direction_at(masked, m.start(), m.end()),
                       m.group(0).strip(), "reader")
    plain = list(_PLAIN_RE.finditer(masked))
    if len(plain) != 1:
        return None
    m = plain[0]
    number = m.group("num").rstrip(",")
    unit = (m.group("unit") or "").lower()
    figure = f"{number}k" if unit == "k" else number
    return Reading(figure, direction_at(masked, m.start(), m.end()),
                   m.group(0).strip(), "reader")


_NUMBER_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakhs?|lacs?|"
    r"crores?|half|quarter|dozen)\b"
    # Odia: one to ten, hundred, thousand, lakh, crore, half
    r"|ଏକ|ଦୁଇ|ତିନି|ଚାରି|ପାଞ୍ଚ|ଛଅ|ସାତ|ଆଠ|ନଅ|ଦଶ|ଶହ|ହଜାର|ଲକ୍ଷ|କୋଟି|ଅଧା",
    re.IGNORECASE)


def has_digit(text: str) -> bool:
    return any(ch.isdigit() for ch in str(text or ""))


def has_number_word(text: str) -> bool:
    return bool(_NUMBER_WORDS.search(str(text or "")))


def mentions_number(text: str) -> bool:
    return has_digit(text) or has_number_word(text)


_BARE_REST = re.compile(r"^[\s₹.,/\-:]*(?:rupees|rs\.?|inr)?[\s.,/\-]*$", re.IGNORECASE)


def is_bare_figure(text: str) -> bool:
    """A figure and nothing else — what our own chips send ("1 lakh", "25%",
    "30 days"). A chip tap routes as a new question unless it is this."""
    reading = read_reply(text)
    if reading is None or reading.direction is not None:
        return False
    rest = str(text).replace(reading.written, " ", 1)
    return bool(_BARE_REST.match(rest))


# ── What the bot says ─────────────────────────────────────────────────────────

_ASK = {
    ("rupees", "above"):     "Above what planned cost? For example ₹50,000 or 1 lakh.",
    ("rupees", "below"):     "Below what planned cost? For example ₹50,000 or 1 lakh.",
    ("percent", "above"):    "More than what percentage?",
    ("percent", "below"):    "Below what percentage?",
    ("days", "above"):       "How many days?",
    ("days", "below"):       "Within how many days?",
    ("activities", "above"): "At least how many activities?",
    ("activities", "below"): "Fewer than how many activities?",
}
_EXAMPLES = {
    "rupees":     [("₹50,000", "₹50,000"), ("1 lakh", "1 lakh"), ("5 lakh", "5 lakh")],
    "percent":    [("25%", "25%"), ("50%", "50%"), ("75%", "75%")],
    "days":       [("30 days", "30 days"), ("60 days", "60 days"), ("90 days", "90 days")],
    "activities": [("5", "5"), ("10", "10"), ("20", "20")],
}
_LOOKS_FOR = {
    "rupees":     "results {cmp} a planned cost",
    "percent":    "results {cmp} a percentage",
    "days":       "activities waiting {cmp} a number of days",
    "activities": "results with {cmp} a number of activities",
}


def ask(meta: dict) -> tuple[str | None, list[Chip]]:
    """(the question in the slot's own unit, three example chips), or
    (None, []) for a slot the catalogue declares nothing about."""
    prompt = _ASK.get((meta.get("unit"), meta.get("direction")))
    if prompt is None:
        return None, []
    return prompt, [Chip(label=label, send_text=send)
                    for label, send in _EXAMPLES.get(meta["unit"], [])]


def figure_label(written: str, unit: str | None) -> str:
    """The figure as the officer will read it back: "₹2 lakhs", "25%", "90 days"."""
    figure = clean_figure(written)
    if unit == "rupees":
        return figure if re.match(r"^(?:₹|rs\.?|inr)", figure, re.I) else f"₹{figure}"
    if unit == "percent":
        return f"{figure}%"
    if unit == "days":
        return f"{figure} days"
    return figure


def _comparison_word(direction: str, unit: str | None) -> str:
    if unit == "activities":
        return "at least" if direction == "above" else "fewer than"
    if unit == "days":
        return "more than" if direction == "above" else "within"
    return direction


# The question's own direction words, swapped for the other way round — the text
# chip 2 sends, so the officer's opposite reading routes as a new question.
_SWAPS = [
    (r"\bhigh[- ]value\b", "low-value"), (r"\blow[- ]value\b", "high-value"),
    (r"\bhigh[- ]expenditure\b", "low-expenditure"),
    (r"\blow[- ]cost\b", "high-cost"), (r"\bhigh[- ]cost\b", "low-cost"),
    (r"\bmore than\b", "less than"), (r"\bless than\b", "more than"),
    (r"\bfewer than\b", "more than"), (r"\bat least\b", "at most"),
    (r"\babove\b", "below"), (r"\bbelow\b", "above"),
    (r"\bover\b", "under"), (r"\bunder\b", "over"),
]


def swapped_question(original: str, reply_direction: str, label: str,
                     unit: str | None) -> str:
    """The paused question the other way round, carrying the figure."""
    text = str(original or "").strip()
    for pattern, replacement in _SWAPS:
        swapped = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
        if swapped != text:
            text = swapped
            break
    body = text.rstrip(" ?.")
    return f"{body} ({_comparison_word(reply_direction, unit)} {label})?"


def mismatch(meta: dict, reading: Reading, original_query: str, *,
             first_turn: bool = False) -> tuple[str, list[Chip]]:
    """(prompt, chips) for a figure whose direction contradicts the statement's.

    Chip 1 sends the bare figure, which resumes the paused question. On a REPLY,
    chip 2 sends the paused question the other way round, as a new question —
    if no template answers it, the ordinary no-match path says so. On the FIRST
    TURN there is no chip 2: the officer's own question already says it the
    other way round and was retrieved onto this statement, so sending it again
    would come straight back here.
    """
    unit, slot_dir = meta.get("unit"), meta["direction"]
    label = figure_label(reading.written, unit)
    ours = _comparison_word(slot_dir, unit)
    theirs = _comparison_word(reading.direction, unit)
    looks_for = _LOOKS_FOR.get(unit, "results {cmp} a figure").format(cmp=ours)
    resume = Chip(label=f"{ours.capitalize()} {label}", send_text=reading.written)
    if first_turn:
        return (f"The closest question I have looks for {looks_for}, not {theirs}. "
                f"Did you mean {ours} {label}?"), [resume]
    prompt = (f"This question looks for {looks_for}. "
              f"Did you mean {ours} {label}, or do you want the ones {theirs} {label}?")
    return prompt, [
        resume,
        Chip(label=f"{theirs.capitalize()} {label} instead",
             send_text=swapped_question(original_query, reading.direction, label, unit)),
    ]


def direction_of_value(text: str, value) -> Reading | None:
    """Where a bound figure sits in the QUESTION, and the direction beside it.

    The first-turn half of the check: "activities under 2 lakhs" retrieved onto
    an "above" template had its figure prefilled by the rupee reader and was
    answered above 2 lakh. Located by its digits, commas ignored; None when the
    figure is not in the text or appears more than once.
    """
    digits = re.sub(r"[^\d.]", "", str(value or "").split()[0] if value else "")
    if not digits:
        return None
    pattern = r"(?<![\d,.])" + r",?".join(map(re.escape, digits)) + r"(?![\d])"
    hits = list(re.finditer(pattern, str(text or "")))
    if len(hits) != 1:
        return None
    m = hits[0]
    text = str(text)
    # Take in the multiplier word and a leading ₹ so the chips read naturally.
    tail = re.match(r"\s*(?:lakhs?|lacs?|crores?|cr|thousand|k)\b", text[m.end():], re.I)
    end = m.end() + (tail.end() if tail else 0)
    head = re.search(r"(?:₹|₨|\bRs\.?|\bINR)\s*$", text[:m.start()], re.I)
    start = head.start() if head else m.start()
    direction = direction_at(text, start, end)
    if direction is None:
        return None
    return Reading(str(value), direction, text[start:end].strip(), "reader")

"""How a missing year is asked for (WP-6g T1c, operator ruling 2026-09-29).

THE DEFECT. 332 of the 358 templates require `$date_range` and five also need
`$date_range_2`. A question naming no year was asked "For which date range?"
with NO chips — the slot's code name, and nothing to tap. The tester read it as
the bot giving no answer ("Andhrua untied-fund expenditure", "Barimunda planned
activities count" both stopped there), and a failed reply was re-asked as "I
still need a date range to answer …".

NOW. "Which year? For example 2024-25." with the three latest fiscal years in
the data as chips, newest first, each labelled and sent in the short form an
officer writes. `$date_range_2` — the EARLIER year of the five two-year
comparisons — is asked "Compared with which year?", and never offers the year
already bound in `$date_range`. The years come from the validator's registry,
never from this file, so the chips move when the data does. The example is the
second chip offered: the second-latest year when nothing is bound, and always
a year that exists.

A chip sends "2024-25", which `pending_resolver.admits_reply` reads against the
paused question (`is_year_chip`), exactly as a threshold chip's bare figure is.
Slot NAMES are unchanged; only the words an officer reads change (`slot_words`).
"""
from __future__ import annotations

import re

from .models import Chip

# The entity types a fiscal-year slot carries (`entity_validator`'s map).
FISCAL_YEAR_TYPES = frozenset({"fiscal_year", "fiscal_year_2"})

# How many of the latest years are offered.
YEAR_CHIPS = 3

# The words an officer reads for a slot, where the bind name is not one.
_SLOT_WORDS = {"date_range": "year", "date_range_2": "year"}

# What a year chip sends: "2024-25", as `short_label` writes it.
_YEAR_CHIP_RE = re.compile(r"\s*20\d{2}-\d{2}\s*")


def slot_words(slot: str) -> str:
    """`date_range` -> "year"; any other slot reads as its name, as before."""
    return _SLOT_WORDS.get(slot, slot.replace("_", " "))


def short_label(stored: str) -> str:
    """'2024-2025' -> '2024-25'. Anything else is returned unchanged."""
    match = re.fullmatch(r"(20\d{2})-20(\d{2})", str(stored).strip())
    return f"{match.group(1)}-{match.group(2)}" if match else str(stored)


def is_year_chip(message: str) -> bool:
    """True for exactly what a year chip sends."""
    return bool(_YEAR_CHIP_RE.fullmatch(str(message or "")))


def known_years(validator) -> list[str]:
    """The loaded fiscal years, oldest first; empty when there is no registry."""
    try:
        return list(validator.fiscal_years())
    except Exception:
        return []


def bound_years(values) -> set[str]:
    """Stored years already bound, from resolved values that may be lists
    ('2023-2024, 2024-2025' is how a list reads once resolved)."""
    bound: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple)):
            bound.update(str(v).strip() for v in value)
        elif value:
            bound.update(v.strip() for v in str(value).split(","))
    return bound


def ask(entity_type: str, years, bound=()) -> tuple[str, list[Chip]]:
    """The question and the chips for a missing fiscal-year slot."""
    bound = set(bound)
    offered = [y for y in sorted(years, reverse=True) if y not in bound][:YEAR_CHIPS]
    chips = [Chip(label=short_label(y), send_text=short_label(y)) for y in offered]
    lead = "Compared with which year?" if entity_type == "fiscal_year_2" else "Which year?"
    if not offered:
        return lead, []
    example = offered[1] if len(offered) > 1 else offered[0]
    return f"{lead} For example {short_label(example)}.", chips

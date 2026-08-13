"""Deterministic year/season extraction from question text.

The router takes its date window from the request body, which the frontend's
date picker fills. Nothing read the question itself, so "…in 2024?" was answered
over the default window (last full calendar year) without a word to the user —
an invisible wrong answer, which is the worst kind.

This module is the fix, and it deliberately stays in the same register as the
rest of the router: **no LLM, no fuzzy NLP**. A word-bounded regex pass over the
ORIGINAL message text, returning a window only for phrases that name a period
outright. Anything relative ("last year", "this season"), anything bare ("in
kharif"), anything that merely looks numeric — no window, and the caller keeps
its default.

Not to be confused with `preprocessor.normalize()`: that output feeds retrieval
embeddings only, and mutating it would corrupt bound values. Nothing here
touches the text the router routes on.
"""
from __future__ import annotations

import calendar
import re

__all__ = ["extract_date_window"]


# ── Vocabulary ────────────────────────────────────────────────────────────────

# 2020–2039. Wide enough for anything a user will type about this data (which
# spans 2023–2026) and narrow enough that Aadhaar/mobile/khata digit runs need
# the adjacency guard rather than a lucky miss.
_YEAR = r"(?<!\d)(20[2-3]\d)(?!\d)"

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

# The only two seasons in the AP flat data. A season contributes its LABEL YEAR
# and nothing more — see _season_windows().
_SEASON_ALT = "kharif|rabi"

# Joins a phrase to the year that qualifies it: "March 2025", "March, 2025",
# "Kharif of 2024", "Rabi season 2023".
_LINK = r"[\s,]*(?:of\s+)?(?:season\s+)?"

# FY 2024-25 / 2024-25 / 2024–25. The two-digit tail is what distinguishes a
# crop-year label from a range: "2023-2025" fails here (the tail must not be
# followed by another digit) and falls through to the multi-year rule.
_FY_RE = re.compile(
    r"(?:\bF\.?\s?Y\.?\s*)?" + _YEAR + r"\s*[-–—/]\s*(\d{2})(?!\d)",
    re.IGNORECASE,
)
_MONTH_RE = re.compile(rf"\b({_MONTH_ALT})\b{_LINK}{_YEAR}", re.IGNORECASE)
_SEASON_RE = re.compile(rf"\b({_SEASON_ALT})\b{_LINK}{_YEAR}", re.IGNORECASE)
_BARE_YEAR_RE = re.compile(_YEAR)


# ── Guards ────────────────────────────────────────────────────────────────────

# "₹2025", "Rs. 2025", "INR 2025" — an amount, not a year. \b keeps "years"
# from reading as a stray "rs".
_MONEY_PREFIX_RE = re.compile(r"(?:₹|₨|\bRs\.?|\bINR)\s*$", re.IGNORECASE)

# "2025 kg", "2024 acres" — a quantity, not a year.
_UNIT_SUFFIX_RE = re.compile(
    r"\s*(?:rupees|rs|acres?|hectares?|kgs?|quintals?|tons?|tonnes?|bags?)\b",
    re.IGNORECASE,
)


def _passes_guards(text: str, start: int, end: int) -> bool:
    """True when the digits at text[start:end] read as a year, not as money or
    a quantity. Digit adjacency is already handled by _YEAR's lookarounds."""
    if _MONEY_PREFIX_RE.search(text[:start]):
        return False
    if _UNIT_SUFFIX_RE.match(text[end:]):
        return False
    return True


# ── Window builders ───────────────────────────────────────────────────────────

def _year_window(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"


def _month_window(year: int, month: int) -> tuple[str, str]:
    last = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def _collect(
    pattern: re.Pattern,
    text: str,
    consumed: list[tuple[int, int]],
    build,
    year_group: int,
) -> list[tuple[str, str]]:
    """Run one pattern, skipping matches whose year overlaps an earlier (more
    specific) match, and appending the years it claims to `consumed`."""
    windows: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        y_start, y_end = m.span(year_group)
        if any(y_start < c_end and c_start < y_end for c_start, c_end in consumed):
            continue
        if not _passes_guards(text, y_start, y_end):
            continue
        windows.append(build(m))
        consumed.append((y_start, y_end))
    return windows


def extract_date_window(message: str) -> tuple[str, str] | None:
    """Read an explicit period out of the question text.

    Returns an ISO ``(start_date, end_date)`` pair, or None when the text names
    no usable period. Callers must treat None as "leave the window alone" — this
    never guesses, and never overrides a range the request already carried.

        "in 2024"                 -> ("2024-01-01", "2024-12-31")
        "between 2023 and 2025"   -> ("2023-01-01", "2025-12-31")
        "FY 2024-25"              -> ("2024-01-01", "2024-12-31")
        "March 2025"              -> ("2025-03-01", "2025-03-31")
        "Kharif 2024"             -> ("2024-01-01", "2024-12-31")
        "in kharif" / "last year" -> None

    Years outside the data's 2023–2026 span are honoured as typed. An honest
    "no records in that window" beats a silent substitution.
    """
    if not message:
        return None

    consumed: list[tuple[int, int]] = []
    windows: list[tuple[str, str]] = []

    # Most specific first, so each phrase is read once and at its own precision.
    # A crop-year label ("2024-25") is treated as its label calendar year: crude
    # by design. Real fiscal/crop years straddle two calendar years, and the
    # `year` date-kind compares a bare integer `cropyear`, so a two-year window
    # would be both wrong and unrepresentable. The response's
    # derived_from_question flag is how the user learns a window was inferred.
    windows += _collect(
        _FY_RE, message, consumed,
        lambda m: _year_window(int(m.group(1))), 1,
    )

    windows += _collect(
        _MONTH_RE, message, consumed,
        lambda m: _month_window(int(m.group(2)), _MONTHS[m.group(1).lower()]), 2,
    )

    # A season contributes ONLY its label year. Season *filtering* already has a
    # home — the season entity/parameter path on the templates that declare one
    # — and a true Rabi window spans two calendar years, which the integer
    # `cropyear` comparison cannot express. So: no season-shaped windows here.
    windows += _collect(
        _SEASON_RE, message, consumed,
        lambda m: _year_window(int(m.group(2))), 2,
    )

    windows += _collect(
        _BARE_YEAR_RE, message, consumed,
        lambda m: _year_window(int(m.group(1))), 1,
    )

    if not windows:
        return None

    # Several periods named ("between 2023 and 2025", "2023 to 2025") — span
    # them all, which is what the plain reading of such a question asks for.
    return min(w[0] for w in windows), max(w[1] for w in windows)

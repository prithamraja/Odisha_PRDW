"""Deterministic fiscal-year extraction from question text.

Odisha PR&DW keeps everything on a **fiscal year**, stored as the full string
`'2024-2025'` in `planned_activity.fiscal_year` / `plan.fiscal_year`. Two rules
follow from that and this module exists to enforce both:

1. **`'2024-25'` must never reach SQL.** The column holds the nine-character
   full form, so the abbreviated label an officer actually says matches nothing
   — a silent zero-row answer. Every phrasing is mapped here, once, to the exact
   stored string. (`resolve_fiscal_years` returns canonical strings; the
   registry then decides whether the DB actually holds that year.)
2. **Relative phrases resolve against the DATA, not the wall clock.** "this
   year" means the latest fiscal year present in the database. The shipped
   sample ends at 2025-2026 while the clock may say otherwise, and answering
   "this year" with an empty year nobody has loaded is the same silent-wrong
   failure in a different costume. Callers pass the loaded years in.

Per decision D9 the fiscal year is an ordinary named slot (`$date_range`), NOT
a `date_filter` injection: the `date_kind: "year"` machinery compares integers
and would raise a binder error on a `'2024-2025'` string. `extract_date_window`
below therefore serves only the genuine *calendar* windows in this domain — the
GPDP `$deadline` questions compared against `plan.approval_date` — and stays
dormant for anything fiscal-year shaped.

The register is the same as the rest of the router: **no LLM, no fuzzy NLP**. A
word-bounded regex pass over the ORIGINAL message text. Anything this module
cannot read outright it declines to guess at, and the caller clarifies.

Not to be confused with `preprocessor.normalize()`: that output feeds retrieval
embeddings only, and mutating it would corrupt bound values. Nothing here
touches the text the router routes on.
"""
from __future__ import annotations

import calendar
import re

__all__ = [
    "extract_date_window",
    "resolve_fiscal_years",
    "resolve_fiscal_year",
    "fiscal_year_window",
    "FISCAL_YEAR_START_MONTH",
]

# India's financial year runs 1 April → 31 March. `'2024-2025'` therefore means
# 2024-04-01 .. 2025-03-31, which is why a fiscal label can never be read as a
# calendar year without losing three months at each end.
FISCAL_YEAR_START_MONTH = 4


# ── Vocabulary ────────────────────────────────────────────────────────────────

# 2000–2099. The data spans 2020-2021 … 2025-2026; the wider window means a year
# outside the data is honoured as typed and answered honestly, rather than
# silently substituted. Digit runs (LGD codes, mobile numbers, amounts) are held
# off by the lookarounds plus the guards below.
_YEAR = r"(?<!\d)(20\d{2})(?!\d)"

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

# Joins a phrase to the year that qualifies it: "March 2025", "March, 2025".
_LINK = r"[\s,]*(?:of\s+)?"

# The optional label an officer puts in front of a fiscal year: "FY 2024-25",
# "F.Y. 2024-25", "financial year 2024-25", "fiscal year 2024-25". Never
# required — "2024-25 expenditure" is the commonest form of all.
_FY_LABEL = r"(?:\b(?:F\.?\s?Y\.?|financial\s+year|fiscal\s+year|plan\s+year)\s*)?"

# '2024-2025' — the stored form. The tail must be a full year AND the pair must
# be consecutive; `_fiscal_pair` enforces that, so "2023-2025" falls through to
# the bare-year scan and reads as the range it is.
_FY_FULL_RE = re.compile(_FY_LABEL + _YEAR + r"\s*[-–—/]\s*(20\d{2})(?!\d)", re.IGNORECASE)

# '2024-25' / 'FY 2024-25' — four-digit head, two-digit tail.
_FY_SHORT_RE = re.compile(_FY_LABEL + _YEAR + r"\s*[-–—/]\s*(\d{2})(?!\d)", re.IGNORECASE)

# '24-25' — both halves two digits. The lookbehind is what stops this firing on
# the tail of '2024-25' and on any longer digit run.
_FY_TWO_RE = re.compile(
    _FY_LABEL + r"(?<!\d)(\d{2})\s*[-–—/]\s*(\d{2})(?!\d)", re.IGNORECASE
)

_MONTH_RE = re.compile(rf"\b({_MONTH_ALT})\b{_LINK}{_YEAR}", re.IGNORECASE)
_BARE_YEAR_RE = re.compile(_YEAR)

# ── Relative phrases ──────────────────────────────────────────────────────────
# Resolved against the loaded years, newest last. "financial"/"fiscal" is
# optional throughout because officers say both "last year" and "last FY".

_REL_WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "couple": 2, "few": 3,
}

_FY_WORD = r"(?:financial\s+|fiscal\s+)?(?:year|f\.?\s?y\.?)"

# "last two years", "past 3 financial years", "previous couple of years"
_LAST_N_RE = re.compile(
    r"\b(?:last|past|previous|recent)\s+"
    r"(two|three|four|five|six|couple|few|\d{1,2})\s*(?:of\s+)?"
    r"(?:financial\s+|fiscal\s+)?years\b",
    re.IGNORECASE,
)
# "last year", "previous financial year", "last FY"
_LAST_YEAR_RE = re.compile(
    rf"\b(?:last|previous|prior|preceding)\s+{_FY_WORD}\b", re.IGNORECASE
)
# "this year", "current financial year", "the ongoing FY"
_THIS_YEAR_RE = re.compile(
    rf"\b(?:this|current|ongoing|present|running)\s+{_FY_WORD}\b", re.IGNORECASE
)


# ── Guards ────────────────────────────────────────────────────────────────────

# "₹2025", "Rs. 2025", "INR 2025" — an amount, not a year. \b keeps "years"
# from reading as a stray "rs".
_MONEY_PREFIX_RE = re.compile(r"(?:₹|₨|\bRs\.?|\bINR)\s*$", re.IGNORECASE)

# "2025 lakh", "2024 households" — a quantity, not a year. The rupee units are
# the live risk in this domain: every expenditure question quotes figures.
_UNIT_SUFFIX_RE = re.compile(
    r"\s*(?:rupees|rs|lakhs?|lacs?|crores?|cr|thousand|"
    r"households?|beneficiaries|activities|works?|gps?|schemes?)\b",
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


# ── Fiscal-year strings ───────────────────────────────────────────────────────

def _fiscal_label(start_year: int) -> str:
    """2024 -> '2024-2025' — the exact nine characters the column stores."""
    return f"{start_year}-{start_year + 1}"


def _fiscal_pair(head: int, tail: int, tail_digits: int) -> int | None:
    """The START year of the fiscal year '<head>-<tail>' names, or None.

    Consecutiveness is the whole test: '2024-2025' and '2024-25' and '24-25' all
    name one fiscal year, while '2023-2025' names a two-year range and must be
    refused here so the bare-year scan can read it correctly.

    A two-digit HEAD is expanded first ('24-25' -> 2024), then the tail takes its
    century from the expanded head, so '99-00' reads as 2099-2100 rather than
    silently crossing back a hundred years.
    """
    if head < 100:
        head += 2000
    if tail_digits == 2:
        tail = (head // 100) * 100 + tail
    return head if tail == head + 1 else None


def _ordered(known_years) -> list[str]:
    """The loaded fiscal years, oldest first — the axis relative phrases move on."""
    return sorted({str(y).strip() for y in (known_years or []) if str(y).strip()})


def _relative_years(text: str, known: list[str]) -> list[str]:
    """Years named by 'this year' / 'last year' / 'last N years'.

    Empty when nothing relative was said OR when no years are loaded: with no
    axis, "last year" is unanswerable and the caller must clarify rather than
    receive a guess.
    """
    if not known:
        return []
    picked: list[str] = []

    match = _LAST_N_RE.search(text)
    if match:
        token = match.group(1).lower()
        count = _REL_WORD_NUMBERS.get(token)
        if count is None:
            try:
                count = int(token)
            except ValueError:
                count = 0
        if count > 0:
            picked += known[-count:]

    if _LAST_YEAR_RE.search(text) and len(known) >= 2:
        picked.append(known[-2])

    if _THIS_YEAR_RE.search(text):
        picked.append(known[-1])

    return picked


def resolve_fiscal_years(text: str, known_years=()) -> list[str]:
    """Every fiscal year the text names, oldest first, in stored full form.

        "FY 24-25"              -> ['2024-2025']
        "2024-25 vs 2023-24"    -> ['2023-2024', '2024-2025']
        "in 2024"               -> ['2024-2025']
        "last two years"        -> the two newest loaded years
        "how many GPs are there"-> []

    `known_years` is only consulted for RELATIVE phrases; absolute ones are
    canonicalised whether or not the database holds them, so a question about a
    year nobody loaded reaches the registry and is refused by name rather than
    silently answered about a different year.
    """
    text = str(text or "")
    if not text:
        return []

    known = _ordered(known_years)
    consumed: list[tuple[int, int]] = []
    starts: list[int] = []

    def _claim(pattern: re.Pattern, tail_digits: int) -> None:
        for m in pattern.finditer(text):
            span = (m.start(1), m.end(2))
            if any(span[0] < c_end and c_start < span[1] for c_start, c_end in consumed):
                continue
            if not _passes_guards(text, *m.span(1)):
                continue
            start = _fiscal_pair(int(m.group(1)), int(m.group(2)), tail_digits)
            if start is None:
                continue
            starts.append(start)
            consumed.append(span)

    # Most specific first, so '2024-25' is read once and never also as a bare
    # 2024 plus a stray 25.
    _claim(_FY_FULL_RE, 4)
    _claim(_FY_SHORT_RE, 2)
    _claim(_FY_TWO_RE, 2)

    # A bare four-digit year LABELS the fiscal year that starts in it: "the 2024
    # plan", "expenditure in 2024" -> 2024-2025. That is the convention the
    # workbook's own sample values follow. It is a reading, not a certainty —
    # see WP2_REPORT for the operator decision it is flagged under.
    for m in _BARE_YEAR_RE.finditer(text):
        span = m.span(1)
        if any(span[0] < c_end and c_start < span[1] for c_start, c_end in consumed):
            continue
        if not _passes_guards(text, *span):
            continue
        starts.append(int(m.group(1)))
        consumed.append(span)

    years = [_fiscal_label(s) for s in starts] + _relative_years(text, known)
    return sorted(set(years))


def resolve_fiscal_year(text: str, known_years=()) -> str | None:
    """The ONE fiscal year the text names, or None when it names none or several.

    'None for several' is deliberate: a slot binds one value, and picking the
    first of "2023-24 and 2024-25" would answer a different question than the
    one asked. The caller clarifies instead.
    """
    years = resolve_fiscal_years(text, known_years)
    return years[0] if len(years) == 1 else None


def fiscal_year_window(label: str) -> tuple[str, str] | None:
    """'2024-2025' -> ('2024-04-01', '2025-03-31'). None if it is not a label.

    Only for the questions that compare a fiscal year against a real DATE column
    (`plan.approval_date`). The fiscal-year SLOT binds the label itself.
    """
    match = re.fullmatch(r"\s*(\d{4})\s*-\s*(\d{4})\s*", str(label or ""))
    if not match:
        return None
    start = int(match.group(1))
    if int(match.group(2)) != start + 1:
        return None
    return (
        f"{start}-{FISCAL_YEAR_START_MONTH:02d}-01",
        f"{start + 1}-{FISCAL_YEAR_START_MONTH - 1:02d}-31",
    )


# ── Calendar windows ──────────────────────────────────────────────────────────

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
    specific) match, and claiming the WHOLE match so a later, looser pattern
    cannot read part of it again.

    Claiming the whole span rather than just the year group is what stops
    '2024-2025' being read as a fiscal window AND, a moment later, as a bare
    2025 — which would stretch the window to 2025-12-31. The guard still tests
    the year group alone, since that is the run of digits being judged.
    """
    windows: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        start, end = m.span()
        if any(start < c_end and c_start < end for c_start, c_end in consumed):
            continue
        if not _passes_guards(text, *m.span(year_group)):
            continue
        built = build(m)
        if built is None:
            continue
        windows.append(built)
        consumed.append((start, end))
    return windows


def extract_date_window(message: str) -> tuple[str, str] | None:
    """Read an explicit CALENDAR period out of the question text.

    Returns an ISO ``(start_date, end_date)`` pair, or None when the text names
    no usable period. Callers must treat None as "leave the window alone" — this
    never guesses, and never overrides a range the request already carried.

        "in 2024"                  -> ("2024-01-01", "2024-12-31")
        "between 2023 and 2025"    -> ("2023-01-01", "2025-12-31")
        "FY 2024-25"               -> ("2024-04-01", "2025-03-31")
        "March 2025"               -> ("2025-03-01", "2025-03-31")
        "last year" / "this year"  -> None

    A fiscal label produces the REAL 1 April – 31 March window, not its head
    calendar year. The AP build flattened it to the calendar year because that
    domain compared an integer crop-year column; here the only consumer is a
    genuine DATE column (`plan.approval_date`), where three missing months at
    each end would be a wrong answer.

    Relative phrases are absent by design: they resolve against the loaded data,
    which this function cannot see. `resolve_fiscal_years` handles them.

    Years outside the data's span are honoured as typed. An honest "no records
    in that window" beats a silent substitution.
    """
    if not message:
        return None

    consumed: list[tuple[int, int]] = []
    windows: list[tuple[str, str]] = []

    def _fy_window(m: re.Match, tail_digits: int):
        start = _fiscal_pair(int(m.group(1)), int(m.group(2)), tail_digits)
        return None if start is None else fiscal_year_window(_fiscal_label(start))

    # Most specific first, so each phrase is read once and at its own precision.
    windows += _collect(_FY_FULL_RE, message, consumed, lambda m: _fy_window(m, 4), 1)
    windows += _collect(_FY_SHORT_RE, message, consumed, lambda m: _fy_window(m, 2), 1)

    windows += _collect(
        _MONTH_RE, message, consumed,
        lambda m: _month_window(int(m.group(2)), _MONTHS[m.group(1).lower()]), 2,
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

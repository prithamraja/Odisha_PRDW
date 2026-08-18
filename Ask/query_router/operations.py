"""
Deterministic operations layer over the current context frame's result table.

The LLM (or a UI button) only *selects* an operation + arguments from this
closed set; every number below is computed in code. The policy table decides,
per (operation, column type), whether the computation may run client-side on
the displayed rows or must be recomputed through a catalog template — an
unweighted mean of ratios is wrong, so ratio aggregations never run here.
"""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Callable

from .models import (
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    OperationMode,
    OperationRequest,
    OperationResult,
)

OPERATIONS = {
    "sum", "average", "min", "max", "count", "share_of_total",
    "sort", "filter_rows", "percent_change", "top_n", "bottom_n", "compare",
    "median", "mode", "stdev", "percentile", "range", "count_distinct",
}

# Operations that aggregate a measure column — these are the dangerous ones.
_AGGREGATIONS = {"sum", "average", "share_of_total"}

# Measure-typed columns an aggregation may target, and how.
#   client  — safe on the displayed table
#   requery — must be recomputed from base data through a catalog template
_AGGREGATION_POLICY: dict[ColumnType, str] = {
    ColumnType.ADDITIVE_COUNT: "client",
    ColumnType.ADDITIVE_VALUE: "client",
    ColumnType.RATIO:          "requery",
    ColumnType.SNAPSHOT_STOCK: "client",   # except across time — see aggregation_mode()
    ColumnType.UNCLASSIFIED:   "requery",  # additivity unverified; don't guess
}

# Non-aggregating numeric ops are order/pick or distribution-of-the-displayed-rows
# statistics — safe on any measure, ratios included (a median district rate is a
# legitimate per-row statistic; it's the unweighted *mean* of rates that lies).
_NUMERIC_OPS = {
    "min", "max", "percent_change", "sort", "top_n", "bottom_n",
    "median", "stdev", "percentile", "range",
}

_MEASURE_TYPES = set(_AGGREGATION_POLICY)


# ── The truncation guard (WP-4c §5.2, decision D31.2) ────────────────────────
#
# THE DEFECT IT CLOSES, verbatim from the replay record:
#
#   #1403 "Which focus area has the highest planned expenditure in 2024-25?"
#         -> BUD-022 with top_n = 1 (a bare superlative binds it, by design)
#         -> the displayed table is ONE ROW: Drinking water, the highest
#   #1404 "and the lowest?"
#         -> read as an OPERATION on the displayed table
#         -> "Lowest planned_cost: 42,118,474 (focus area name: Drinking water)."
#
# Drinking water is the HIGHEST. The minimum of a one-row table is that row, so
# the sentence is true of the table and false of the question, and the officer is
# handed a superlative that is exactly inverted. #1042 is the same thing in
# Hinglish. `frame.bound_params` carried `top_n: '1'` the whole time; nothing
# consulted it.
#
# The information needed to refuse was always present, so this is a guard rather
# than a feature: 91 templates carry `$top_n`, a bare superlative binds it to 1,
# and "which GP spent the most?" followed by "and the lowest?" is about as
# natural a pair as this system will ever see.
_TOP_N_SLOT = "top_n"

# The re-query LIMIT. Not "unlimited": the operator ruling of 2026-08-13 keeps
# the `$top_n` ceiling at 1,000 and clarifies rather than answers above it, so
# lifting a truncation means going to the ceiling, not past it. `LIMIT NULL` is
# unbounded in DuckDB, which is the opposite of a page size and is exactly what
# `slot_defaults` exists to prevent.
_UNTRUNCATED_TOP_N = "1000"

# WHICH OPERATIONS THE LIMIT CAN LIE TO. The test is not "does it aggregate" but
# "is its answer a claim about a POPULATION" — because a claim about a
# population computed over a slice of it is wrong however correctly it was
# computed. Enumerated over OPERATIONS above, one decision per entry:
#
#   sum, average, share_of_total   a total, or a share of one, taken over a
#                                  slice is neither.
#   min, max                       the defect itself. `max` is included even
#                                  though a top-N-DESCENDING slice does contain
#                                  the true maximum, because nothing here knows
#                                  the slice's sort direction — over a bottom-N
#                                  frame the same call is wrong.
#   top_n, bottom_n                "bottom 1 of the top 1" is #1042 exactly.
#   percent_change                 first-to-last across a truncated span.
#   median, stdev, percentile,     distribution statistics of a slice. Their
#   range                          narration does say "across the N rows shown",
#                                  which is a disclosure and not a defence: the
#                                  question asked was about the population.
#   mode, count_distinct           the commonest value, and how many distinct
#                                  values exist, are both population facts.
#
# NOT guarded, deliberately:
#
#   count                          its entire answer is "The table has N rows" —
#                                  a statement about the table, which is what
#                                  the table is.
#   sort, filter_rows              re-order and select the displayed rows, and
#                                  claim nothing beyond the rows on screen.
#   compare                        re-queries by construction already.
_POPULATION_DEPENDENT = frozenset({
    "sum", "average", "share_of_total", "min", "max", "top_n", "bottom_n",
    "percent_change", "median", "stdev", "percentile", "range",
    "mode", "count_distinct",
})


def truncating_limit(frame: ContextFrame, rows: list[dict]) -> int | None:
    """The `$top_n` that actually CUT this table, or None.

    None in three cases, and the third is the one worth naming: a frame with no
    `$top_n` at all, a `$top_n` that is not a number, and a `$top_n` the result
    never reached. `top_n = 10` over a seven-row population returns seven rows,
    the LIMIT never bound, and the table IS the population — so guarding it
    would refuse a question that has a correct answer to give. Fewer rows than
    the limit is proof the limit did not bite.
    """
    raw = (frame.bound_params or {}).get(_TOP_N_SLOT)
    if raw is None:
        return None
    try:
        limit = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if limit <= 0 or len(rows) < limit:
        return None
    return limit


def _truncation_rejected(op: str, limit: int, why: str) -> OperationResult:
    """Explain instead of answering. The reason NAMES THE TRUNCATION, because a
    generic "I can't do that" leaves the officer believing the table is the
    population — which is the belief that made the defect dangerous."""
    rows = f"{limit} row{'s' if limit != 1 else ''}"
    return _rejected(
        op,
        f"The table on screen is the top {rows} of a longer result, so a "
        f"{op.replace('_', ' ')} taken over it would describe those {rows} "
        f"rather than the whole population — which is how a 'lowest' comes back "
        f"naming the highest. I could not recompute it over the full result "
        f"({why}). Ask the question directly, naming how many rows you want, so "
        f"it is computed from base data.",
    )


def aggregation_mode(column: ColumnMetadata, table_columns: list[ColumnMetadata]) -> str:
    """Client-vs-requery decision for aggregating one column of the table."""
    if column.column_type not in _MEASURE_TYPES:
        return "invalid"
    mode = _AGGREGATION_POLICY[column.column_type]
    if column.column_type == ColumnType.SNAPSHOT_STOCK and any(
        c.column_type == ColumnType.TEMPORAL for c in table_columns
    ):
        return "requery"  # summing a stock across time periods double-counts
    return mode


# ── Value helpers ─────────────────────────────────────────────────────────────

def _to_number(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def _fmt(value: float, decimals: int = 2) -> str:
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"


def _numeric_values(rows: list[dict], column: str) -> list[float]:
    values = (_to_number(row.get(column)) for row in rows)
    return [v for v in values if v is not None]


def _column_map(columns: list[ColumnMetadata]) -> dict[str, ColumnMetadata]:
    return {c.name: c for c in columns}


def _humanize(column: str) -> str:
    """'FARMERNAME' -> 'farmername', 'sub_district' -> 'sub district' — a column
    name readable inside a sentence."""
    return column.strip().strip('"').replace("_", " ").lower()


def _label_column(columns: list[ColumnMetadata], rows: list[dict]) -> str | None:
    """First dimension (else temporal) column — used to name rows in narration."""
    for wanted in (ColumnType.DIMENSION, ColumnType.TEMPORAL):
        for c in columns:
            if c.column_type == wanted:
                return c.name
    if rows:
        for name in rows[0]:
            if _to_number(rows[0][name]) is None:
                return name
    return None


def _match_column_name(requested: str, columns: list[ColumnMetadata]) -> str | None:
    """Loose name match against any column, exact first then substring."""
    wanted = requested.strip().lower().replace(" ", "_")
    for c in columns:
        if c.name.lower() == wanted:
            return c.name
    for c in columns:
        if wanted in c.name.lower() or c.name.lower() in wanted:
            return c.name
    return None


def _resolve_column(
    requested: str | None,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> str | None:
    """Match a (possibly loose) column reference; default to the first measure."""
    if requested:
        return _match_column_name(requested, columns)
    for preferred in (
        ColumnType.ADDITIVE_VALUE,
        ColumnType.ADDITIVE_COUNT,
        ColumnType.SNAPSHOT_STOCK,
        ColumnType.RATIO,
    ):
        for c in columns:
            if c.column_type == preferred and _numeric_values(rows, c.name):
                return c.name
    for c in columns:
        if _numeric_values(rows, c.name):
            return c.name
    return None


def _rejected(operation: str, answer: str, column: str | None = None) -> OperationResult:
    return OperationResult(
        operation=operation, mode=OperationMode.REJECTED, answer=answer, column=column,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

# Re-query hook: (comparator_slot, comparator_value) -> rows of the same
# template with that one bound parameter swapped. Raises on failure.
RequeryFn = Callable[[str, str], list[dict]]


def run_operation(
    request: OperationRequest,
    frame: ContextFrame,
    rows: list[dict],
    requery: RequeryFn | None = None,
) -> OperationResult:
    op = request.operation.strip().lower()
    if op not in OPERATIONS:
        return _rejected(op, f"'{request.operation}' is not a supported operation.")
    if not rows and op != "compare":
        return _rejected(op, "The current result table is empty — nothing to compute.")

    columns = frame.result_set.columns

    if op == "count":
        return OperationResult(
            operation=op, mode=OperationMode.CLIENT, value=float(len(rows)),
            answer=f"The table has {len(rows):,} row{'s' if len(rows) != 1 else ''}.",
        )

    if op == "filter_rows":
        return _filter_rows(request, columns, rows)

    if op == "compare":
        return _compare(request, frame, rows, requery)

    # THE TRUNCATION GUARD (D31.2). Before any population-dependent number is
    # computed, ask whether the table it would be computed over is the whole
    # population. Placed here rather than inside each implementation so a new
    # operation cannot be added past it: everything below this line either
    # states a fact about the displayed rows and says so, or has been re-queried
    # over the full result.
    limit = truncating_limit(frame, rows)
    if limit is not None and op in _POPULATION_DEPENDENT:
        if requery is None:
            return _truncation_rejected(
                op, limit, "re-query is not available right now")
        try:
            full_rows = requery(_TOP_N_SLOT, _UNTRUNCATED_TOP_N)
        except Exception as ex:
            return _truncation_rejected(
                op, limit, f"{type(ex).__name__}: {ex}")
        if not full_rows:
            return _truncation_rejected(
                op, limit, "the re-query returned nothing")
        # Recompute on the full result, through this same function, so the
        # operation's own implementation is untouched and stays the single
        # definition of what a minimum is. The frame handed down no longer
        # carries the limit, so the guard cannot recurse.
        lifted = frame.model_copy(update={
            "bound_params": {k: v for k, v in (frame.bound_params or {}).items()
                             if k != _TOP_N_SLOT},
        })
        result = run_operation(request, lifted, full_rows, requery=requery)
        if result.mode is not OperationMode.REJECTED:
            result = result.model_copy(update={
                "mode": OperationMode.REQUERY,
                "answer": (
                    f"{result.answer} (Recomputed over all {len(full_rows):,} "
                    f"rows: the table on screen was the top {limit}.)"
                ),
            })
        return result

    # These two target any column (dimensions included), so they resolve their
    # own column instead of going through the numeric default below.
    if op in ("mode", "count_distinct"):
        return _value_frequency_op(op, request, columns, rows)

    column = _resolve_column(request.column, columns, rows)
    if column is None:
        return _rejected(
            op,
            f"I couldn't find a numeric column matching '{request.column}' in this table."
            if request.column else
            "This table has no numeric column to compute on.",
        )
    meta = _column_map(columns).get(column, ColumnMetadata(name=column, column_type=ColumnType.UNCLASSIFIED))

    if op in _AGGREGATIONS:
        mode = aggregation_mode(meta, columns)
        if mode == "invalid":
            return _rejected(op, f"'{column}' is not a measure column, so it can't be aggregated.", column)
        if mode == "requery":
            reason = (
                f"'{column}' is a rate/ratio — a {op.replace('_', ' ')} over displayed rows would be an "
                "unweighted mean, which is statistically wrong. Ask the underlying question "
                "(e.g. the state-wide or period-total version) so it's computed from base data."
                if meta.column_type == ColumnType.RATIO else
                f"'{column}' is a point-in-time stock and this table spans time periods — "
                f"a {op.replace('_', ' ')} would double-count. Ask for the figure as of a single date."
                if meta.column_type == ColumnType.SNAPSHOT_STOCK else
                f"'{column}' isn't verified as safely additive, so I won't {op.replace('_', ' ')} it here. "
                "Ask the question directly so it's computed from base data."
            )
            return _rejected(op, reason, column)

    if op in ("sum", "average", "min", "max"):
        return _scalar_op(op, column, meta, columns, rows)
    if op in ("median", "stdev", "percentile", "range"):
        return _distribution_op(op, request, column, columns, rows)
    if op == "share_of_total":
        return _share_of_total(request, column, columns, rows)
    if op == "percent_change":
        return _percent_change(column, columns, rows)
    if op == "sort":
        return _sort(request, column, columns, rows)
    if op in ("top_n", "bottom_n"):
        return _top_bottom(op, request, column, columns, rows)

    return _rejected(op, f"'{op}' is not implemented.")


# ── Implementations ───────────────────────────────────────────────────────────

def _scalar_op(
    op: str,
    column: str,
    meta: ColumnMetadata,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    values = _numeric_values(rows, column)
    if not values:
        return _rejected(op, f"'{column}' has no numeric values to compute on.", column)

    label_col = _label_column(columns, rows)
    if op == "sum":
        value = sum(values)
        answer = f"Total {column} across {len(values):,} rows: {_fmt(value)}."
    elif op == "average":
        value = sum(values) / len(values)
        answer = f"Average {column} across {len(values):,} rows: {_fmt(value)}."
    else:
        pick = min if op == "min" else max
        value = pick(values)
        row = next((r for r in rows if _to_number(r.get(column)) == value), None)
        # Name the column the winner comes from. "(Devi Kumar)" reads as an
        # answer to whatever was asked; "(farmer: Devi Kumar)" makes a
        # misclassified subject visible in the answer itself.
        where = (
            f" ({_humanize(label_col)}: {row[label_col]})"
            if row and label_col and row.get(label_col) is not None else ""
        )
        answer = f"{'Lowest' if op == 'min' else 'Highest'} {column}: {_fmt(value)}{where}."

    return OperationResult(
        operation=op, mode=OperationMode.CLIENT, answer=answer, column=column, value=value,
    )


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _distribution_op(
    op: str,
    request: OperationRequest,
    column: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    """Distribution statistics over the displayed rows. These describe the rows
    as shown (each row weighted equally), so unlike sum/average they are safe on
    any measure type — the narration says so explicitly."""
    values = _numeric_values(rows, column)
    if not values:
        return _rejected(op, f"'{column}' has no numeric values to compute on.", column)
    n_rows = len(values)

    if op == "median":
        value = float(statistics.median(values))
        answer = f"Median {column} across the {n_rows:,} rows shown: {_fmt(value)}."

    elif op == "stdev":
        if n_rows < 2:
            return _rejected(op, "Standard deviation needs at least two numeric values.", column)
        value = statistics.stdev(values)
        answer = (
            f"Standard deviation of {column} across the {n_rows:,} rows shown: "
            f"{_fmt(value)} (sample)."
        )

    elif op == "percentile":
        if request.n is None:
            return _rejected(op, "Tell me which percentile you want (e.g. 90).", column)
        if not 0 <= request.n <= 100:
            return _rejected(op, f"{request.n} is not a valid percentile (0–100).", column)
        ordered = sorted(values)
        rank = request.n / 100 * (n_rows - 1)
        lo, frac = int(rank), rank - int(rank)
        value = ordered[lo] if frac == 0 else ordered[lo] + frac * (ordered[lo + 1] - ordered[lo])
        answer = (
            f"{_ordinal(request.n)} percentile of {column} across the "
            f"{n_rows:,} rows shown: {_fmt(value)}."
        )

    else:  # range
        low, high = min(values), max(values)
        value = high - low
        label_col = _label_column(columns, rows)

        def _where(target: float) -> str:
            row = next((r for r in rows if _to_number(r.get(column)) == target), None)
            if row and label_col and row.get(label_col) is not None:
                return f" ({row[label_col]})"
            return ""

        answer = (
            f"{column} ranges from {_fmt(low)}{_where(low)} to {_fmt(high)}{_where(high)} "
            f"across the {n_rows:,} rows shown — a spread of {_fmt(value)}."
        )

    return OperationResult(
        operation=op, mode=OperationMode.CLIENT, answer=answer, column=column, value=value,
    )


def _value_frequency_op(
    op: str,
    request: OperationRequest,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    """mode / count_distinct — work on any column; default to the first dimension."""
    if request.column:
        column = _match_column_name(request.column, columns)
        if column is None:
            return _rejected(op, f"No column matching '{request.column}' in this table.")
    else:
        column = next(
            (c.name for c in columns if c.column_type == ColumnType.DIMENSION), None
        ) or (next(iter(rows[0]), None) if rows else None)
    if column is None:
        return _rejected(op, "This table has no column to compute on.")

    values = [str(row[column]).strip() for row in rows if row.get(column) is not None]
    if not values:
        return _rejected(op, f"'{column}' has no values to compute on.", column)
    counts = Counter(values)

    if op == "count_distinct":
        distinct = len(counts)
        return OperationResult(
            operation=op, mode=OperationMode.CLIENT, column=column, value=float(distinct),
            answer=(
                f"{column} has {distinct:,} distinct value{'s' if distinct != 1 else ''} "
                f"across the {len(values):,} rows shown."
            ),
        )

    top_count = max(counts.values())
    if top_count == 1:
        return OperationResult(
            operation=op, mode=OperationMode.CLIENT, column=column,
            answer=(
                f"Every value of {column} appears exactly once in the "
                f"{len(values):,} rows shown — there is no most common value."
            ),
        )
    modes = sorted(v for v, c in counts.items() if c == top_count)
    if len(modes) == 1:
        answer = (
            f"Most common {column}: {modes[0]} "
            f"({top_count:,} of {len(values):,} rows)."
        )
    else:
        listed = ", ".join(modes[:3]) + (f" and {len(modes) - 3} more" if len(modes) > 3 else "")
        answer = (
            f"{len(modes)} values of {column} tie as most common "
            f"({top_count:,} rows each): {listed}."
        )
    value = _to_number(modes[0]) if len(modes) == 1 else None
    return OperationResult(
        operation=op, mode=OperationMode.CLIENT, column=column, value=value, answer=answer,
    )


def _share_of_total(
    request: OperationRequest,
    column: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    values = _numeric_values(rows, column)
    total = sum(values)
    if total == 0:
        return _rejected("share_of_total", f"Total of '{column}' is zero — shares are undefined.", column)

    label_col = _label_column(columns, rows)
    share_col = f"share_of_{column}_pct"
    result = []
    for row in rows:
        v = _to_number(row.get(column))
        result.append({**row, share_col: round(v / total * 100, 2) if v is not None else None})

    if request.label and label_col:
        wanted = request.label.strip().lower()
        match = next(
            (r for r in result if str(r.get(label_col, "")).strip().lower() == wanted),
            None,
        )
        if match is None:
            return _rejected(
                "share_of_total",
                f"No row with {label_col} = '{request.label}' in the current table.",
                column,
            )
        return OperationResult(
            operation="share_of_total", mode=OperationMode.CLIENT, column=column,
            value=match[share_col], result=result,
            answer=(
                f"{match[label_col]} accounts for {match[share_col]}% of total {column} "
                f"({_fmt(_to_number(match.get(column)) or 0)} of {_fmt(total)})."
            ),
        )

    top = max(
        (r for r in result if r[share_col] is not None),
        key=lambda r: r[share_col],
        default=None,
    )
    lead = (
        f" The largest share is {top[share_col]}%"
        + (f" ({top[label_col]})" if label_col and top.get(label_col) is not None else "")
        + "." if top else ""
    )
    return OperationResult(
        operation="share_of_total", mode=OperationMode.CLIENT, column=column, result=result,
        result_columns=columns + [ColumnMetadata(name=share_col, column_type=ColumnType.RATIO)],
        answer=f"Added each row's share of total {column} (total: {_fmt(total)}).{lead}",
    )


def _percent_change(
    column: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    temporal = next((c.name for c in columns if c.column_type == ColumnType.TEMPORAL), None)
    ordered = rows
    if temporal:
        ordered = sorted(rows, key=lambda r: str(r.get(temporal, "")))

    pairs = [
        (row, _to_number(row.get(column)))
        for row in ordered
        if _to_number(row.get(column)) is not None
    ]
    if len(pairs) < 2:
        return _rejected(
            "percent_change",
            f"Percent change needs at least two rows with numeric '{column}' values.",
            column,
        )
    (first_row, first), (last_row, last) = pairs[0], pairs[-1]
    if first == 0:
        return _rejected(
            "percent_change",
            f"The starting value of '{column}' is zero — percent change is undefined.",
            column,
        )

    change = (last - first) / abs(first) * 100
    label_col = temporal or _label_column(columns, rows)
    span = (
        f" from {first_row.get(label_col)} to {last_row.get(label_col)}"
        if label_col and first_row.get(label_col) is not None else ""
    )
    return OperationResult(
        operation="percent_change", mode=OperationMode.CLIENT, column=column,
        value=round(change, 2),
        answer=(
            f"{column}{span}: {_fmt(first)} → {_fmt(last)}, "
            f"a change of {change:+.1f}%."
        ),
    )


def _sort(
    request: OperationRequest,
    column: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    descending = (request.direction or "desc").lower() != "asc"
    ordered = sorted(
        rows,
        key=lambda r: (_to_number(r.get(column)) is None, _to_number(r.get(column)) or 0),
        reverse=descending,
    )
    return OperationResult(
        operation="sort", mode=OperationMode.CLIENT, column=column, result=ordered,
        result_columns=columns,
        answer=f"Sorted by {column}, {'highest first' if descending else 'lowest first'}.",
    )


def _top_bottom(
    op: str,
    request: OperationRequest,
    column: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    n = max(1, request.n or 5)
    descending = op == "top_n"
    ordered = [r for r in rows if _to_number(r.get(column)) is not None]
    ordered.sort(key=lambda r: _to_number(r.get(column)), reverse=descending)
    sliced = ordered[:n]
    if not sliced:
        return _rejected(op, f"'{column}' has no numeric values to rank.", column)

    label_col = _label_column(columns, rows)
    lead_row = sliced[0]
    lead = (
        f" {lead_row[label_col]} leads with {_fmt(_to_number(lead_row.get(column)))}."
        if label_col and lead_row.get(label_col) is not None else ""
    )
    which = "Top" if descending else "Bottom"
    return OperationResult(
        operation=op, mode=OperationMode.CLIENT, column=column, result=sliced,
        result_columns=columns,
        answer=f"{which} {len(sliced)} rows by {column}.{lead}",
    )


_FILTER_OPS: dict[str, Callable[[float, float], bool]] = {
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}

# Columns whose values are text, so `contains` can mean something on them.
_STRINGISH_TYPES = {ColumnType.DIMENSION, ColumnType.IDENTIFIER, ColumnType.TEMPORAL}

# Columns that hold numbers. `"small or marginal" in str(20)` is False for every
# row, so a text comparison against one of these produces a confident "0 of N
# rows" that reads like an answer and is not one.
_NUMERIC_COLUMN_TYPES = {
    ColumnType.ADDITIVE_COUNT,
    ColumnType.ADDITIVE_VALUE,
    ColumnType.RATIO,
    ColumnType.SNAPSHOT_STOCK,
}


def filter_type_error(
    filter_column: str | None,
    filter_operator: str | None,
    filter_value,
    columns: list[ColumnMetadata],
) -> str | None:
    """Why this filter can't mean anything against the column it names, or None.

    Unknown columns and unknown operators return None — they have their own
    rejection messages downstream. What this catches is the filter that WOULD
    run and answer wrongly: a text match against a column of numbers, or a
    numeric comparison against a value that is not a number.
    """
    if not filter_column or not filter_operator:
        return None
    # The /query path hands this raw LLM JSON, where a field can be any type.
    resolved = _match_column_name(str(filter_column), columns)
    if resolved is None:
        return None
    column_type = next(
        (c.column_type for c in columns if c.name == resolved), ColumnType.UNCLASSIFIED
    )
    operator = str(filter_operator).strip()
    number = _to_number(filter_value)
    numeric_column = column_type in _NUMERIC_COLUMN_TYPES or (
        column_type == ColumnType.UNCLASSIFIED and number is not None
    )

    if operator == "contains" and column_type not in _STRINGISH_TYPES:
        return (
            f"'{resolved}' holds numbers — 'contains {filter_value}' doesn't apply "
            "to it. Ask the question directly instead."
        )
    if operator in _FILTER_OPS:
        if number is None:
            return f"'{filter_value}' is not a number, so '{operator}' can't be applied."
        if not numeric_column:
            return f"'{resolved}' isn't a numeric column, so '{operator}' can't be applied to it."
    if operator in ("=", "==", "!=") and column_type in _NUMERIC_COLUMN_TYPES and number is None:
        return (
            f"'{resolved}' holds numbers, so it can't equal '{filter_value}'. "
            "Ask the question directly instead."
        )
    return None


def _filter_rows(
    request: OperationRequest,
    columns: list[ColumnMetadata],
    rows: list[dict],
) -> OperationResult:
    if not request.filter_column or not request.filter_operator or request.filter_value is None:
        return _rejected("filter_rows", "Filtering needs a column, an operator, and a value.")

    column = _resolve_column(request.filter_column, columns, rows)
    if column is None:
        # Fall back to any (non-numeric) column by name for =/contains filters
        names = {c.name.lower(): c.name for c in columns}
        column = names.get(request.filter_column.strip().lower().replace(" ", "_"))
    if column is None:
        return _rejected("filter_rows", f"No column matching '{request.filter_column}' in this table.")

    op = request.filter_operator.strip()
    value = request.filter_value

    # The /operation endpoint has no routing fallback, so a type-incompatible
    # filter is explained here rather than silently returning zero rows.
    type_error = filter_type_error(column, op, value, columns)
    if type_error is not None:
        return _rejected("filter_rows", type_error, column)
    if op in _FILTER_OPS:
        threshold = _to_number(value)
        if threshold is None:
            return _rejected("filter_rows", f"'{value}' is not a number, so '{op}' can't be applied.")
        kept = [
            r for r in rows
            if (v := _to_number(r.get(column))) is not None and _FILTER_OPS[op](v, threshold)
        ]
    elif op in ("=", "=="):
        kept = [r for r in rows if str(r.get(column, "")).strip().lower() == str(value).strip().lower()]
    elif op == "!=":
        kept = [r for r in rows if str(r.get(column, "")).strip().lower() != str(value).strip().lower()]
    elif op == "contains":
        kept = [r for r in rows if str(value).strip().lower() in str(r.get(column, "")).lower()]
    else:
        return _rejected("filter_rows", f"'{op}' is not a supported filter operator.")

    return OperationResult(
        operation="filter_rows", mode=OperationMode.CLIENT, column=column, result=kept,
        result_columns=columns,
        answer=f"{len(kept):,} of {len(rows):,} rows where {column} {op} {value}.",
    )


def _compare(
    request: OperationRequest,
    frame: ContextFrame,
    rows: list[dict],
    requery: RequeryFn | None,
) -> OperationResult:
    if requery is None:
        return _rejected("compare", "Comparison re-query is not available right now.")
    if not request.comparator:
        return _rejected("compare", "Tell me what to compare with (e.g. another district).")

    slot = request.comparator_slot
    if slot and slot not in frame.bound_params:
        return _rejected(
            "compare",
            f"The current question has no '{slot}' parameter to swap "
            f"(it has: {', '.join(frame.bound_params) or 'none'}).",
        )
    if not slot:
        slot = next((s for s in frame.bound_params if s not in ("year", "month")), None)
    if not slot:
        return _rejected(
            "compare",
            "The current question has no swappable parameter — comparison needs an "
            "entity-scoped result (e.g. a specific district).",
        )

    base_value = frame.bound_params[slot]
    slot_col = f"compared_{slot}"
    merged: list[dict] = [{slot_col: base_value, **row} for row in rows]
    for value in request.comparator[:3]:
        try:
            peer_rows = requery(slot, value)
        except Exception as ex:
            return _rejected("compare", f"Couldn't re-run the query for '{value}': {ex}")
        merged.extend({slot_col: value, **row} for row in peer_rows)

    columns = [ColumnMetadata(name=slot_col, column_type=ColumnType.DIMENSION)] + list(
        frame.result_set.columns
    )
    entities = [base_value] + list(request.comparator[:3])
    answer = f"Comparison of {slot}: {' vs '.join(str(e) for e in entities)}."

    # Single-row-per-entity results get a numeric narration of the differences.
    if len(rows) == 1 and len(merged) == len(entities):
        deltas = []
        for col in frame.result_set.columns:
            if col.column_type not in _MEASURE_TYPES:
                continue
            vals = [_to_number(r.get(col.name)) for r in merged]
            if any(v is None for v in vals):
                continue
            deltas.append(f"{col.name}: " + " vs ".join(_fmt(v) for v in vals))
            if len(deltas) == 4:
                break
        if deltas:
            answer += " " + "; ".join(deltas) + "."

    return OperationResult(
        operation="compare", mode=OperationMode.REQUERY, result=merged,
        result_columns=columns, answer=answer,
    )

"""Gate-green, as a command (WP-5 T3, replacing AP's `pmkisan_gates.py`).

    cd Ask
    python prdw_gates.py            # exit 0 = green
    python prdw_gates.py --list     # what it would run, and nothing else

WHY THIS FILE IS THE POINT OF WP-5. The bootstrap has said since day one that
"gate-green must be a command, not a judgment call", and until now it was nine
things run and read by hand out of a report header. WP-4c's own assessment put
it plainly: for a v1 that will be revised, the risk is not a wrong answer today
but an unnoticed regression tomorrow — and that package added three value-level
checks (the direction pins, the `wrong_entities` bucket, refusal reachability)
precisely so that regressions in the confidently-wrong class could not hide.
They only help if something runs them.

WHAT IT COSTS. One API call, in check 5, and it is a model LIST — not a
completion. Everything else is executed locally against the sample database and
the generated catalogue. `--no-spend` drops even that one and reports the check
as UNVERIFIED rather than pretending. `--yes`/`PRDW_EVAL_CONFIRM=1` confirms it
unattended, through the same `eval_spend` guard as every paid harness.

WHAT IT DOES NOT DO. It does not run the end-to-end eval. That is ~700 paid
calls over three replays and takes half an hour; it belongs in a work package,
not in a gate somebody is meant to run before every commit. What this file
asserts instead is every INVARIANT the eval would otherwise have to notice
after the fact — the served-refusal shape, the paired-year direction, the
refusal ranks, the model identity, the catalogue's static contracts.

EACH CHECK PRINTS ONE LINE, and a failure names the check. Detail goes
underneath, indented, so a green run is nine lines and a red one tells you where
to look without reading the rest.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
# THE REPO-SIDE ARTEFACTS (the workbook, eval/gold) live one level up — except
# when the backend is being run from a local mirror, which is the documented way
# to run anything here: DuckDB cannot create temp files inside the Drive folder
# (bootstrap 6). `PRDW_REPO` points at the real repo in that case, the same
# override `eval/gold/build_eval_questions.py` already takes.
REPO = Path(os.environ.get("PRDW_REPO") or HERE.parent)
sys.path.insert(0, str(HERE))

load_dotenv(HERE / ".env")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

PYTHON = sys.executable
WORKBOOK = REPO / "AI_Chatbot_Questions.xlsx"
GOLD = REPO / "eval" / "gold"

# The bootstrap's model-risk lesson, quoted where a mismatch will read it.
COMPLETION_BUDGET_REMINDER = (
    "ON ANY MODEL SWAP, CHECK THE COMPLETION-TOKEN BUDGET FIRST (bootstrap, "
    "model risk). A reasoning model once consumed a 2,000-token budget entirely "
    "on reasoning and returned empty strings; a report was generated with every "
    "section blank and nothing failed loudly. The same signature is F1 in this "
    "project: `finish_reason=length` with no content is `truncated`, not an "
    "empty question. Do not accept a swap until the budget has been re-measured."
)

# The three harnesses that spend, and the guard every one of them must go
# through. `pmkisan_gates.py` is deliberately absent: it is deleted by this
# package (it was AP's).
PAID_HARNESSES = ("run_full_eval.py", "recall_eval.py", "rerank_eval.py")

results: list[tuple[str, bool, str]] = []


class Check:
    """One gate item. The body returns (ok, detail) or raises."""

    def __init__(self, number: int, title: str, fn):
        self.number, self.title, self.fn = number, title, fn

    def run(self, args) -> bool:
        try:
            ok, detail = self.fn(args)
        except Exception as exc:                             # noqa: BLE001
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {self.number}. {self.title}")
        for line in (detail or "").splitlines():
            if line.strip():
                print(f"          {line}")
        results.append((f"{self.number}. {self.title}", ok, detail or ""))
        return ok


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env={**os.environ, **(env or {})} if env else None)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _tail(output: str, n: int = 3) -> str:
    lines = [l for l in (output or "").splitlines() if l.strip()]
    return "\n".join(lines[-n:])


# ── 1. the suite ─────────────────────────────────────────────────────────────

def check_suite(args):
    """Every test, from FRESH CACHES.

    §3a exists because WP-1 found copied `__pycache__` directories executing
    bytecode compiled from the SOURCE repo's paths — `co_filename` proved it. A
    suite run against stale bytecode is a green light for code that is not in
    the tree.
    """
    removed = 0
    for cache in list(HERE.rglob("__pycache__")) + [HERE / ".pytest_cache"]:
        if cache.is_dir() and ".venv" not in cache.parts:
            shutil.rmtree(cache, ignore_errors=True)
            removed += 1

    modules = sorted(f"tests.{p.stem}" for p in (HERE / "tests").glob("test_*.py"))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(modules)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    ok = result.wasSuccessful()
    detail = (f"{result.testsRun} tests across {len(modules)} modules, "
              f"{len(result.skipped)} skipped, {removed} caches cleared")
    if not ok:
        detail += "\n" + "\n".join(
            f"{kind}: {test}" for kind, tests in
            (("FAIL", result.failures), ("ERROR", result.errors))
            for test, _ in tests)
    return ok, detail


# ── 2. the catalogue executes ────────────────────────────────────────────────

def check_validate_catalog(args):
    """All 346 templates bind, execute, and agree with the workbook's own row
    counts. The only check here that touches the database with real SQL."""
    code, out = _run([PYTHON, "validate_catalog.py"], HERE)
    ok = code == 0 and "All clear" in out
    return ok, _tail(out, 2 if ok else 12)


# ── 3. the catalogue matches the workbook ────────────────────────────────────

def check_catalog_drift(args):
    """THE CATALOGUE IS GENERATED. Edit the workbook and regenerate; a
    hand-edited `template_catalog.py` is a change nothing can reproduce."""
    if not WORKBOOK.exists():
        return False, f"workbook not found at {WORKBOOK}"
    code, out = _run([PYTHON, "tools/build_catalog.py", "--check",
                      "--workbook", str(WORKBOOK)], HERE)
    if "No module named 'openpyxl'" in out:
        return False, ("openpyxl is not installed — it is a BUILD-TIME "
                       "dependency, deliberately not in requirements.txt. "
                       "`pip install openpyxl` to run this check.")
    ok = code == 0 and "in step with the workbook" in out
    return ok, _tail(out, 1 if ok else 10)


# ── 4. the gold set ──────────────────────────────────────────────────────────

def check_gold(args):
    """The gold set's own invariants, plus the harness-format gate: the built
    artefacts loaded with the harnesses' OWN parsers, not with a fresh one."""
    detail = []
    ok = True
    for script, want in (("build_eval_questions.py", "invariants hold"),
                         ("check_harness_format.py", "hard checks: PASS")):
        code, out = _run(
            [PYTHON, str(GOLD / script)] + (["--check"] if "build" in script else []),
            REPO, env={"PRDW_REPO": str(REPO)})
        passed = code == 0 and want in out
        ok = ok and passed
        detail.append(_tail(out, 2 if passed else 8))
    return ok, "\n".join(detail)


# ── 5. model identity ────────────────────────────────────────────────────────

def check_model_identity(args):
    """The four pinned models, against config AND against the live model list.

    WHY BOTH. Checking config against itself proves nothing; an upstream swap is
    exactly the failure this exists for. The bootstrap's own account: "an
    upstream swap to a smaller extraction model broke name extraction (~2/3 None
    on some names) with no code change — proved by A/B on the model, not the
    prompt". So the second half asks the provider whether the ids this system
    pins are still ids the provider serves.

    ONE CALL, and it is `models.list()` — a catalogue read, not a completion.
    """
    from query_router import config

    pinned = {
        "extraction": config.EXTRACTION_MODEL,
        "rerank": config.RERANK_MODEL,
        "abstraction": config.ABSTRACTION_MODEL,
        "embedding": config.EMBEDDING_MODEL,
    }
    expected = {
        "extraction": "gpt-5.4-mini",
        "rerank": "gpt-5.4-mini",
        "abstraction": "gpt-5.4-mini",
        "embedding": "text-embedding-3-large",
    }
    drifted = {role: (pinned[role], want)
               for role, want in expected.items() if pinned[role] != want}
    if drifted:
        return False, (
            "\n".join(f"{role}: config pins {got!r}, this gate expects {want!r}"
                      for role, (got, want) in drifted.items())
            + "\n" + COMPLETION_BUDGET_REMINDER)

    line = ("config: " + ", ".join(f"{role}={model}"
                                   for role, model in sorted(pinned.items())))

    if args.no_spend:
        return True, line + "\n" + ("live model list NOT CHECKED (--no-spend) — "
                                    "config-only, so an upstream swap would not "
                                    "be visible to this run")

    from eval_spend import confirm_spend
    confirm_spend("prdw_gates (model identity)",
                  [("provider model list (one catalogue read, no completion)", 1)],
                  confirmed=args.yes)

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return False, (line + "\nOPENAI_API_KEY is not set, so the live model "
                              "list could not be read. Re-run with --no-spend "
                              "to skip it deliberately.")
    from openai import OpenAI
    live = {m.id for m in OpenAI(api_key=key).models.list().data}
    missing = sorted({m for m in pinned.values() if m not in live})
    if missing:
        return False, (
            line + "\n"
            + f"the provider does not list: {', '.join(missing)}\n"
            + COMPLETION_BUDGET_REMINDER)
    return True, line + f"\nall four ids present on the live model list "\
                        f"({len(live)} models)"


# ── 6, 7. the two value-level invariants, lifted verbatim ────────────────────

def _run_test_modules(*modules: str):
    suite = unittest.TestLoader().loadTestsFromNames(list(modules))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    detail = f"{result.testsRun} assertions"
    if not result.wasSuccessful():
        detail += "\n" + "\n".join(
            f"{test}" for tests in (result.failures, result.errors)
            for test, _ in tests)
    return result.wasSuccessful(), detail


def check_served_refusal(args):
    """`result is None`, never `[]`, on all 30 refusals.

    ONE LINE OF SURFACE AREA THAT FLIPS 19 GOLD ROWS AT ONCE. `grade_full_eval`
    decides "was this an answer?" partly on whether the record carries a result
    set, so a refusal that ever set `result = []` reads as a template answer
    whose query_id is not a template — and every unanswerable row becomes a
    failure in one move, with nothing in the eval output saying why.
    """
    return _run_test_modules("tests.test_served_refusal")


def check_direction_pins(args):
    """The paired-year direction, EXECUTED against the sample database.

    `$date_range` is the LATER year on all five paired templates and three of
    them compute `$date_range - $date_range_2`. Swap the pair and PLN-039
    answers "which themes showed the greatest INCREASE" with the greatest
    decline — right query_id, right row count, plausible table, inverted sign,
    and WP-4's replays graded all three of them `hit`. No LLM: the SQL is run
    both ways round and the two answers are compared.
    """
    return _run_test_modules("tests.test_paired_year_direction")


# ── 8. refusal recall ────────────────────────────────────────────────────────

def check_refusal_recall(args):
    """Can a documented refusal be RETRIEVED? (D31.4, from WP-4c 7.4.)

    `recall_eval` divides every refusal away, so "recall@30 = 95.4%" said
    nothing about the 19 rows where BEN-001 sat at rank 51 of 376 — outside the
    window, so the reranker never saw it and the documented reason could not be
    served. That gap hid the defect for a whole work package, which is why this
    is its own line and not a component of a headline.

    Run `--cached-only`: this file makes exactly one paid call and it is check
    5's. A cold cache reports UNMEASURED and names the one command that fills
    it, because an unverifiable invariant is not a passing one.
    """
    code, out = _run([PYTHON, "refusal_recall.py", "--cached-only", "--quiet"],
                     HERE)
    ok = code == 0
    body = _tail(out, 12)
    if not ok and "UNMEASURED" in out:
        body += "\n(the ranks themselves are unchanged by this — the cache is "\
                "cold, not the measurement wrong)"
    return ok, body


# ── 9. static invariants ─────────────────────────────────────────────────────

def check_static_invariants(args):
    """The contracts that hold by construction, asserted so they keep holding.

    Each of these was a real defect somewhere in this lineage, and each is
    invisible until an answer is already wrong.
    """
    from query_router.entity_extractor import ExtractionUnavailable, extraction_failed
    from query_router.sql_params import mask_literals
    from query_router.template_catalog import TEMPLATE_CATALOG

    problems: list[str] = []
    notes: list[str] = []

    # (a) No `date_filter` on any template. PR&DW filters by FISCAL YEAR through
    # a bound `$date_range`; a date_filter would inject a second, silent window
    # over the same rows and answer about their intersection.
    with_filter = sorted(qid for qid, t in TEMPLATE_CATALOG.items()
                         if t.get("date_filter") or t.get("date_kind"))
    if with_filter:
        problems.append(f"date_filter/date_kind set on: {', '.join(with_filter)}")
    notes.append(f"date_filter unset on all {len(TEMPLATE_CATALOG)} templates")

    # (b) No tagged dollar quoting. `$tag$ ... $tag$` makes `$name` inside a
    # literal indistinguishable from a bind parameter, so the binder would
    # rewrite text the SQL means literally.
    tagged = re.compile(r"\$(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\$.*?\$(?P=tag)\$",
                        re.DOTALL)
    quoted = sorted(qid for qid, t in TEMPLATE_CATALOG.items()
                    if tagged.search(mask_literals(t["sql_template"])))
    if quoted:
        problems.append(f"tagged dollar quoting in: {', '.join(quoted)}")
    notes.append("no $tag$ dollar quoting in any sql_template")

    # (c) Every PARTIAL answer carries a caveat (D3). 251 of the 363 signed-off
    # questions are only partially answerable; a partial answer served without
    # its caveat is the confidently-wrong failure mode, not a slightly worse
    # answer.
    uncaveated = sorted(
        qid for qid, t in TEMPLATE_CATALOG.items()
        if str(t.get("answerable", "")).strip().lower() == "partial"
        and not (t.get("caveat") or "").strip())
    if uncaveated:
        problems.append(
            f"{len(uncaveated)} Partial template(s) carry no caveat: "
            f"{', '.join(uncaveated[:8])}"
            + (" …" if len(uncaveated) > 8 else ""))
    partials = sum(1 for t in TEMPLATE_CATALOG.values()
                   if str(t.get("answerable", "")).strip().lower() == "partial")
    if not partials:
        # The field was renamed or dropped: "all 0 Partial templates carry a
        # caveat" is a vacuous pass, and a vacuous pass on the caveat invariant
        # is the worst possible thing for this check to print.
        problems.append(
            "no template reports answerable='Partial' — the workbook says 251 "
            "of 363 questions are partially answerable, so this invariant is "
            "checking a field that no longer exists")
    notes.append(f"all {partials} Partial templates carry a caveat")

    # (d) The extraction sentinel is wired (D30.2). `except Exception: return
    # {s: None}` made a timeout, a 429 and an auth failure indistinguishable
    # from the model reading the question and finding nothing in it.
    sentinel = ExtractionUnavailable(["date_range"], "timeout", "probe")
    if not extraction_failed(sentinel) or extraction_failed({"date_range": None}):
        problems.append("the extraction sentinel does not distinguish an API "
                        "failure from an honestly empty extraction")
    notes.append("extraction sentinel distinguishes failure from empty")

    # (e) Every paid harness goes through the spend guard. WP-2 found a test
    # suite quietly making ~7 paid calls whenever a key happened to sit in
    # `.env`; the harnesses were the same trap one layer up.
    for name in PAID_HARNESSES:
        path = HERE / name
        if not path.exists():
            problems.append(f"{name} is missing")
            continue
        source = path.read_text(encoding="utf-8")
        if "confirm_spend" not in source:
            problems.append(f"{name} does not call confirm_spend")
    notes.append(f"spend guard present on {len(PAID_HARNESSES)} paid harnesses")

    # (f) The AP gates file is gone (WP-5 T3).
    if (HERE / "pmkisan_gates.py").exists():
        problems.append("pmkisan_gates.py still exists — it is AP's, and this "
                        "file replaces it")
    notes.append("pmkisan_gates.py deleted")

    return not problems, "\n".join(problems or notes)


CHECKS = [
    Check(1, "Full test suite, fresh caches", check_suite),
    Check(2, "Catalogue executes (346 templates, row counts)", check_validate_catalog),
    Check(3, "Catalogue in step with the workbook", check_catalog_drift),
    Check(4, "Gold set + harness format", check_gold),
    Check(5, "Model identity (config + live model list)", check_model_identity),
    Check(6, "Served-refusal invariant (result is None, never [])", check_served_refusal),
    Check(7, "Paired-year direction pins (executed)", check_direction_pins),
    Check(8, "Refusal recall (documented refusals retrieve)", check_refusal_recall),
    Check(9, "Static invariants", check_static_invariants),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true",
                    help="confirm check 5's single API call unattended")
    ap.add_argument("--no-spend", action="store_true",
                    help="make no API call at all; check 5 reports config-only")
    ap.add_argument("--list", action="store_true",
                    help="print what would run and exit")
    ap.add_argument("--only", type=int, nargs="*", metavar="N",
                    help="run only these check numbers (for iterating on one)")
    ap.add_argument("--repo", type=Path,
                    help="the repo holding the workbook and eval/gold, when the "
                         "backend is run from a local mirror (or set PRDW_REPO)")
    args = ap.parse_args()

    if args.repo:
        globals()["REPO"] = args.repo.resolve()
        globals()["WORKBOOK"] = REPO / "AI_Chatbot_Questions.xlsx"
        globals()["GOLD"] = REPO / "eval" / "gold"

    if args.list:
        for check in CHECKS:
            print(f"  {check.number}. {check.title}")
        return 0

    selected = [c for c in CHECKS
                if not args.only or c.number in args.only]
    print(f"\n══ PR&DW gates ══  {len(selected)} checks, from {HERE}\n")
    for check in selected:
        check.run(args)

    failed = [name for name, ok, _ in results if not ok]
    print()
    if failed:
        print(f"GATE RED — {len(failed)} of {len(results)} check(s) failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    print(f"GATE GREEN — {len(results)}/{len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

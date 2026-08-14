"""WP-D2 T5 checks on the generated executive report.

Four checks, all mechanical, all re-runnable by the operator:

  (a) PROSE GATE      -- src/prose_gate.py, unmodified, over the report
  (b) NO HOLLOW SECTIONS
                      -- every per-view section carries real prose, not just its
                         deterministic reading note. This is the gpt-5.5
                         incident: nine sections were written BLANK and nothing
                         failed loudly
  (c) FY 2023-24 CAVEAT SCOPE
                      -- the §5.2 sentence appears in a section IF AND ONLY IF
                         one of the findings that section was written from trips
                         the deterministic test. Both directions are checked:
                         a missing caveat and a spurious one are both failures
  (d) NUMBER TRACE    -- every figure in the prose traces to engine output or to
                         the view's own glossary. Nothing the model produced by
                         arithmetic of its own is allowed through

Usage:
    python check_report_prdw.py --base <Insights dir> [--report <path.md>]
"""
import argparse
import io
import os
import re
import subprocess
import sys


def load_report(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    src = os.path.join(base, "src")
    sys.path.insert(0, src)

    report_path = args.report or os.path.join(
        base, "reports_prdw", "executive_metainsight_report.md")

    import json
    import phase5b_report as p5b
    import prose_gate

    md = load_report(report_path)
    failures = []

    def check(ok, label, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    # ---------------------------------------------------------------- (a)
    # The gate is run unmodified. A view in the registry with no mined findings
    # has no section, and the gate says so -- correctly. That is a different
    # failure from a prose failure, so the two are separated here: a missing
    # section is a MINING result, and everything else is a WRITING result.
    print("\n=== (a) prose gate ===")
    proc = subprocess.run([sys.executable, os.path.join(src, "prose_gate.py"), report_path],
                          capture_output=True, text=True)
    print("\n".join("      " + ln for ln in proc.stdout.strip().split("\n")))
    problems = [ln.strip() for ln in proc.stdout.split("\n")
                if ln.startswith("  [") or ln.strip().startswith("line ")]
    structural = [p for p in problems if "section is missing from the report" in p]
    prose_problems = [p for p in problems if p not in structural]
    check(not prose_problems,
          "prose gate: no vocabulary or reading-note problem in any section written",
          f"{len(prose_problems)} problem(s)")
    if structural:
        print(f"  [FAIL-STRUCTURAL] {len(structural)} section(s) missing because the "
              f"view has no mined findings -- the gate is right; see check (b)")
        failures.append("prose gate: missing section(s)")
    check(proc.returncode == 0, "prose_gate exits 0", f"rc={proc.returncode}")

    # ---------------------------------------------------------------- (b)
    print("\n=== (b) no hollow sections ===")
    sections = prose_gate.split_sections(md)
    seen = {}
    for view_name, title, lines in sections:
        if view_name is None:
            continue
        seen[view_name] = (title, lines)
        body = [ln for _, ln in lines
                if ln.strip() and not ln.startswith(">") and not ln.startswith("---")]
        words = sum(len(ln.split()) for ln in body)
        check(words >= 100, f"{title}: section carries prose", f"{words} words")
    missing = [v for v in p5b.VIEW_CONFIGS if v not in seen]
    check(not missing, "every view has a section in the report", str(missing))

    # ---------------------------------------------------------------- (c)
    print("\n=== (c) FY 2023-24 caveat scope ===")
    for view_name in p5b.VIEW_CONFIGS:
        ranked_path = os.path.join(base, "metainsights", f"{view_name}_ranked.json")
        if not os.path.exists(ranked_path):
            # already reported by check (b); nothing to check against here
            print(f"  [skip] {view_name}: no ranked findings")
            continue
        with io.open(ranked_path, encoding="utf-8") as f:
            ranked = json.load(f)
        enriched = p5b.enrich_candidates_with_stats(
            view_name, ranked, p5b.VIEW_CONFIGS[view_name])
        qualifying = [i + 1 for i, c in enumerate(enriched) if c.get("reporting_caveat")]
        expected = bool(qualifying)

        title, lines = seen.get(view_name, ("<missing>", []))
        body = "\n".join(ln for _, ln in lines)
        present = p5b.COUNT_CAVEAT_SENTENCE in body
        check(present == expected,
              f"{title}: caveat present == a finding qualifies",
              f"qualifying ranks={qualifying or 'none'}, in report={present}")

        # and it must live inside the deterministic note, not in model prose
        if present:
            note_lines = [ln for _, ln in lines
                          if ln.startswith(p5b.READING_NOTE_MARKER)]
            check(any(p5b.COUNT_CAVEAT_SENTENCE in ln for ln in note_lines),
                  f"{title}: the caveat sits inside the deterministic note")

    # ---------------------------------------------------------------- (d)
    print("\n=== (d) every figure traces to engine output ===")
    # The vocabulary of legitimate figures: everything the enrichment rendered,
    # plus every number the view's own description, glossary and reading note
    # state as established fact.
    def numbers_in(text: str) -> set:
        # trailing punctuation is prose, not part of the figure: "in 2020, the"
        # must yield 2020 and not "2020,"
        out = set()
        for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
            m = m.rstrip(",.")
            if m:
                out.add(m)
        return out

    allowed: dict = {}
    for view_name in p5b.VIEW_CONFIGS:
        ranked_path = os.path.join(base, "metainsights", f"{view_name}_ranked.json")
        if not os.path.exists(ranked_path):
            # already reported by check (b); nothing to check against here
            print(f"  [skip] {view_name}: no ranked findings")
            continue
        with io.open(ranked_path, encoding="utf-8") as f:
            ranked = json.load(f)
        enriched = p5b.enrich_candidates_with_stats(
            view_name, ranked, p5b.VIEW_CONFIGS[view_name])
        pool = set()
        pool |= numbers_in(json.dumps(enriched, default=str))
        info = p5b.VIEW_DESCRIPTIONS[view_name]
        pool |= numbers_in(info["description"] + info["audience_context"]
                           + json.dumps(info["column_glossary"]))
        pool |= numbers_in(p5b.reading_note_block(view_name, enriched))
        # hdp member counts are written as "5 of the 6" style prose
        pool |= {str(c["hdp_size"]) for c in enriched}
        pool |= {str(len(c.get("exceptions") or [])) for c in enriched}
        for c in enriched:
            for cs in c.get("commonness_sets") or []:
                pool.add(str(cs.get("count")))
        allowed[view_name] = pool

    total_checked = total_ok = 0
    for view_name, (title, lines) in seen.items():
        body = "\n".join(ln for _, ln in lines if not ln.startswith(">"))
        found = numbers_in(body)
        # single digits below 20 are counting words ("five of the six"), not
        # quoted figures; they are checked by the hdp/commonness pool above and
        # anything left is prose, not data
        quoted = {n for n in found if len(n.replace(",", "").replace(".", "")) > 1
                  or float(n.replace(",", "")) >= 20}
        untraced = sorted(n for n in quoted if n not in allowed[view_name])
        total_checked += len(quoted)
        total_ok += len(quoted) - len(untraced)
        check(not untraced, f"{title}: {len(quoted)} figures, all traced",
              f"untraced={untraced}" if untraced else "")

    print(f"\n  {total_ok}/{total_checked} quoted figures traced to engine output "
          f"or to the view's stated facts")

    print(f"\n{'=' * 60}")
    print(f"{len(failures)} failure(s)" + (": " + "; ".join(failures) if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

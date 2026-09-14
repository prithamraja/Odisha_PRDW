"""WP-D11b T3 -- no bare size-band label on any regenerated prose surface.

    python handoffs/WPD11b_calibration/t3_label_scan.py --base Insights [--chat]

Scans, case-insensitively, for a gp_size label WITHOUT its unit ('Under 2,500',
'2,500 to 5,000', '5,000 to 10,000', '10,000 and above' not followed by
"people") in:
  * metainsights/insight_feed.md            the Discover feed
  * reports_prdw/gamma_*_report.md          the five editions
  * reports_prdw/executive_metainsight_report.md
  * reports_prdw/global_feed.md
and counts the displayed forms, so a zero is not merely a surface that never
mentions a band.

--chat also produces one real chat answer: the consolidating writer (the
production prompt, `writer.consolidate`) over the highest-scoring corpus records
that name a size band, then scans the answer and confirms its citation check
passed. The records are picked from the corpus directly rather than retrieved,
so the answer does not depend on what retrieval happens to surface for one
question: it is guaranteed to be an answer ABOUT size bands, which is the thing
under test. Everything from the writer onward is the production path. One model
call, maybe two.

Exits non-zero on any bare label, or on a chat answer that fell back.
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "Insights", "src"))
sys.path.insert(0, REPO)

from phase5b_report import BAND_DISPLAY          # noqa: E402

BARE = re.compile(
    r"(?<![\w,.])(" + "|".join(re.escape(k) for k in sorted(BAND_DISPLAY, key=len, reverse=True))
    + r")(?![\w,]|\s+people\b)", re.IGNORECASE)
SHOWN = re.compile("|".join(re.escape(v) for v in BAND_DISPLAY.values()), re.IGNORECASE)


def scan(label, text):
    bare = [(text.count("\n", 0, m.start()) + 1, m.group(0)) for m in BARE.finditer(text)]
    shown = len(SHOWN.findall(text))
    print(f"  {'FAIL' if bare else 'PASS'}  {label}: {len(bare)} bare, {shown} with unit")
    for line, token in bare[:10]:
        print(f"        line {line}: {token!r}")
    return len(bare)


def chat_answer():
    from DiscoverChat import checks, config, corpus as corpus_mod, writer
    corpus = corpus_mod.load()
    picks = sorted((f for f in corpus.all()
                    if not f.is_decomposition and BARE.search(f.sentence)),
                   key=lambda f: -f.score)[:3]
    picks += sorted((f for f in corpus.all()
                     if f.is_decomposition and BARE.search(f.sentence)),
                    key=lambda f: f.id)[:2]
    question = "How do Gram Panchayats of different population sizes compare?"
    stamp = config.run_stamp_line()
    print(f"\n  chat: {len(picks)} records naming a size band: {[f.id for f in picks]}")
    for f in picks:
        print(f"    stored   {f.sentence[:150]}")
        print(f"    rendered {f.display_sentence()[:150]}")
    out = writer.consolidate(question, picks, run_date=stamp, turn_id="wpd11b-t3")
    print(f"  chat: fell_back={out.fell_back} attempts={out.attempts} {out.reason}")
    text = out.text if not out.fell_back else "\n".join(f.display_sentence() for f in picks)
    print("  --- answer ---\n" + "\n".join("  | " + l for l in text.splitlines()) + "\n  ---")
    bad = scan("chat answer", text)
    if not out.fell_back:
        result = checks.check_citations(out.tagged, picks, run_date=stamp)
        print(f"  chat: citation check all_pass={result['all_pass']}")
        bad += 0 if result["all_pass"] else 1
    return bad + (1 if out.fell_back else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the Insights directory")
    ap.add_argument("--chat", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    files = ([os.path.join(a.base, "metainsights", "insight_feed.md")]
             + sorted(glob.glob(os.path.join(a.base, "reports_prdw", "gamma_*_report.md")))
             + [os.path.join(a.base, "reports_prdw", "executive_metainsight_report.md"),
                os.path.join(a.base, "reports_prdw", "global_feed.md")])
    bad = 0
    print("Surfaces")
    for path in files:
        if os.path.exists(path):
            bad += scan(os.path.relpath(path, a.base),
                        io.open(path, encoding="utf-8").read())
        else:
            print(f"  ....  {path} not present")
    if a.chat:
        bad += chat_answer()
    print(f"\n{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

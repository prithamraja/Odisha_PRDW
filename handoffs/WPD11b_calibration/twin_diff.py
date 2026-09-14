"""WP-D11b T4/T5: what the averaged twins changed in the top-15s.

Diffs the current ranked findings against an earlier candidate set's, on the
WP-D2 signature (pattern type, measure, breakdown, slice, extending dimension,
extending strategy -- score deliberately excluded, as in WP-D11's
profile_diff.py, which this generalises). For views 3 and 4 it also answers the
brief's T4 question directly:

  * how many top-15 findings REST ON an averaged twin -- the finding's measure
    is a `_mean`, or, for a finding that compares measures, a `_mean` is among
    the measures it compares;
  * which BAND-HEADCOUNT findings they displaced -- a finding that broke down
    or varied along a GP profile band while measuring a TOTAL (a SUM measure),
    present in the earlier top-15 and absent now. That is the WP-D11 artifact
    D61 ruling 4 was aimed at: a band of 15 Gram Panchayats outranks a band of 2
    on any total by headcount alone.

Usage (from the mirror root):
    python handoffs/WPD11b_calibration/twin_diff.py --base Insights \
        --old Insights/metainsights_baseline_d619a72e --label d619a72e4fe98d5f \
        --out handoffs/WPD11b_calibration/diff_vs_d619a72e.md
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "Insights", "src"))
from phase5_ranking import generate_nl_summary       # noqa: E402
from phase2_engine import load_candidates             # noqa: E402

PROFILE_DIMS = {"social_composition", "gp_size", "remoteness", "digital_readiness",
                "has_panchayat_bhawan", "has_csc", "plc_available"}
_SUMMARIES = {}


def sig(c):
    return (c.get("pattern_type"), c.get("measure"), c.get("breakdown"),
            tuple(tuple(x) for x in (c.get("base_subspace") or [])),
            c.get("extending_dimension"), c.get("extending_strategy"))


def load(path):
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return d.get("candidates", d) if isinstance(d, dict) else d


def index_summaries(path):
    if not os.path.exists(path):
        return
    for obj, raw in zip(load_candidates(path), load(path)):
        try:
            _SUMMARIES[sig(raw)] = generate_nl_summary(obj)
        except Exception:
            pass


def compared_measures(c):
    """The measures a finding is about: its own, or -- when it varies along
    `measure` -- every member measure it compares."""
    if c.get("extending_dimension") == "measure":
        out = set()
        for cs in c.get("commonness_sets") or []:
            out |= {str(m) for m in cs.get("members") or []}
        out |= {str(e.get("member_label")) for e in c.get("exceptions") or []}
        return out
    return {c.get("measure")}


def rests_on_twin(c):
    return any(str(m).endswith("_mean") for m in compared_measures(c))


def profile_hits(c):
    hits = set()
    for d in (c.get("breakdown"), c.get("extending_dimension")):
        if d in PROFILE_DIMS:
            hits.add(d)
    for d, _v in (c.get("base_subspace") or []):
        if d in PROFILE_DIMS:
            hits.add(d)
    return hits


def band_headcount(c):
    """Broken down or varied along a profile band, measuring a total."""
    along = {c.get("breakdown"), c.get("extending_dimension")} & PROFILE_DIMS
    return bool(along) and not rests_on_twin(c)


def line(i, c):
    tag = []
    if rests_on_twin(c):
        tag.append("**averaged twin**")
    if band_headcount(c):
        tag.append("band-headcount")
    hits = profile_hits(c)
    if hits:
        tag.append("profile: " + ", ".join(sorted(hits)))
    head = (f"- **#{i}** `{c.get('pattern_type')}` {c.get('measure')} by "
            f"`{c.get('breakdown')}`, varied along `{c.get('extending_dimension')}`"
            + (f" — {'; '.join(tag)}" if tag else ""))
    return head + "\n  - " + _SUMMARIES.get(sig(c), "")[:240]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--old", required=True, help="directory holding the earlier *_ranked.json")
    ap.add_argument("--label", required=True, help="the earlier candidate set id")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    new_dir = os.path.join(a.base, "metainsights")
    cur = json.load(io.open(os.path.join(new_dir, "global_feed_source_set.json"),
                            encoding="utf-8"))["candidate_set_id"]

    L = []
    W = L.append
    W(f"# WP-D11b — top-15 diff, `{cur}` against `{a.label}`\n")
    W("A finding is *the same finding* when its pattern type, measure, breakdown, "
      "slice, extending dimension and strategy all match; the score is not part of "
      "it. **averaged twin** = the finding rests on a `_mean` measure (its own "
      "measure, or one of the measures it compares). **band-headcount** = it breaks "
      "down or varies along a GP profile band while measuring a TOTAL.\n")
    rows = []
    for view in ("view1", "view2", "view3", "view4"):
        np_ = os.path.join(new_dir, f"{view}_ranked.json")
        op_ = os.path.join(a.old, f"{view}_ranked.json")
        index_summaries(np_)
        index_summaries(op_)
        new, old = load(np_), load(op_)
        if new is None:
            continue
        old = old or []
        osig = {sig(c): c for c in old}
        nsig = {sig(c): c for c in new}
        entered = [c for s, c in nsig.items() if s not in osig]
        dropped = [c for s, c in osig.items() if s not in nsig]
        kept = [c for s, c in nsig.items() if s in osig]
        twins_new = [c for c in new if rests_on_twin(c)]
        band_old = [c for c in old if band_headcount(c)]
        band_new = [c for c in new if band_headcount(c)]
        band_dropped = [c for c in dropped if band_headcount(c)]
        rows.append((view, len(old), len(new), len(kept), len(entered), len(dropped),
                     len(twins_new), len(band_old), len(band_new), len(band_dropped)))

        W(f"\n## {view}\n")
        W(f"{len(old)} ranked before, {len(new)} now: **{len(kept)} unchanged, "
          f"{len(dropped)} dropped, {len(entered)} new.** "
          f"**{len(twins_new)} of the {len(new)} rest on an averaged twin.** "
          f"Band-headcount findings: {len(band_old)} before, {len(band_new)} now; "
          f"{len(band_dropped)} of the earlier ones were displaced.\n")
        W("\n### The current top-15\n")
        for i, c in enumerate(new, 1):
            W(line(i, c))
        if dropped:
            W("\n### Dropped out (earlier rank shown)\n")
            for c in dropped:
                W(line(old.index(c) + 1, c))

    W("\n## Summary\n")
    W("| view | before | now | unchanged | new | dropped | now resting on a twin "
      "| band-headcount before | band-headcount now | band-headcount displaced |")
    W("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        W("| " + " | ".join(str(x) for x in r) + " |")
    io.open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"wrote {a.out}")
    for r in rows:
        print("  %s: before %d, now %d, unchanged %d, new %d, dropped %d, twins now %d, "
              "band-headcount %d -> %d (%d displaced)" % r)


if __name__ == "__main__":
    sys.exit(main())

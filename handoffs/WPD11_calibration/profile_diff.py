"""WP-D11 T7: what the profile dimensions changed in the top-15s.

Compares the ranked findings of the pre-amendment candidate set (a7f991c1df3771f9,
kept in Insights/metainsights_baseline_a7f991c1/) against the new one, and counts
how many of the newly entering findings actually use a profile dimension.

A finding is "the same finding" across two runs on the WP-D2 signature: pattern
type, measure, breakdown, base subspace and the dimension it varies along. The
score is deliberately not part of it -- the same statement re-scored is still the
same statement, and what the operator is being asked is whether the statement is
worth reading.

Usage:  python profile_diff.py --base <Insights dir> --out <file.md>
"""
import argparse, io, json, os, sys

# The ranked files carry the structured finding, not its sentence -- the report
# and the feed each render their own. Borrow the engine's own renderer so this
# diff reads in the same words the operator will meet in the labelling sheet.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "Insights", "src"))
from phase5_ranking import generate_nl_summary
from phase2_engine import load_candidates

# sig -> sentence, filled per file. `generate_nl_summary` takes the dataclass,
# not the dict, and `load_candidates` is the loader that builds it, so the
# sentences are rendered from the object exactly as the labelling sheet does.
_SUMMARIES = {}


def index_summaries(path, sigfn):
    if not os.path.exists(path):
        return
    for obj, raw in zip(load_candidates(path), load(path)):
        try:
            _SUMMARIES[sigfn(raw)] = generate_nl_summary(obj)
        except Exception:
            pass


def summary(c, sigfn):
    return _SUMMARIES.get(sigfn(c), "")

PROFILE_DIMS = {"social_composition", "gp_size", "remoteness", "digital_readiness",
                "has_panchayat_bhawan", "has_csc", "plc_available"}


def sig(c):
    return (c.get("pattern_type"), c.get("measure"), c.get("breakdown"),
            tuple(tuple(x) for x in (c.get("base_subspace") or [])),
            c.get("extending_dimension"), c.get("extending_strategy"))


def uses_profile(c):
    """Every place a dimension name can reach a finding."""
    hits = set()
    if c.get("breakdown") in PROFILE_DIMS:
        hits.add(c["breakdown"])
    if c.get("extending_dimension") in PROFILE_DIMS:
        hits.add(c["extending_dimension"])
    for d, _v in (c.get("base_subspace") or []):
        if d in PROFILE_DIMS:
            hits.add(d)
    # a measure-extending finding varies along `measure`; its MEMBERS are then
    # measure names, never dimensions, so only the three places above count
    return hits


def load(path):
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return d.get("candidates", d) if isinstance(d, dict) else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    new_dir = os.path.join(a.base, "metainsights")
    old_dir = os.path.join(a.base, "metainsights_baseline_a7f991c1")

    L = []
    W = L.append
    W("# WP-D11 — what the GP profile dimensions changed in the top-15s\n")
    W("Baseline candidate set `a7f991c1df3771f9` (pre-Amendment B, 3 views) against")
    W("the WP-D11 set (4 views, +6 profile dimensions at sample scale).\n")
    W("A finding is *the same finding* across the two runs when its pattern type,")
    W("measure, breakdown, slice and extending dimension all match. Score is not")
    W("part of the signature: the same statement re-scored is the same statement.\n")

    tot_new = tot_drop = tot_kept = tot_profile = 0
    per_view = []
    for view in ("view1", "view2", "view3", "view4"):
        np_, op_ = (os.path.join(new_dir, f"{view}_ranked.json"),
                    os.path.join(old_dir, f"{view}_ranked.json"))
        index_summaries(np_, sig)
        index_summaries(op_, sig)
        new = load(np_)
        old = load(op_)
        if new is None:
            continue
        W(f"\n## {view}\n")
        if old is None:
            W(f"**New view.** {len(new)} ranked finding(s); there is no baseline to")
            W("diff against, so every one of them is new by construction.\n")
            prof = [c for c in new if uses_profile(c)]
            tot_new += len(new)
            tot_profile += len(prof)
            per_view.append((view, len(new), 0, 0, len(prof), len(new)))
            for i, c in enumerate(new, 1):
                hits = uses_profile(c)
                W(f"- **#{i}** `{c.get('pattern_type')}` {c.get('measure')} by "
                  f"{c.get('breakdown')}"
                  + (f" — uses **{', '.join(sorted(hits))}**" if hits else ""))
                W(f"  - {summary(c, sig)[:220]}")
            continue

        osig = {sig(c): c for c in old}
        nsig = {sig(c): c for c in new}
        entered = [c for s, c in nsig.items() if s not in osig]
        dropped = [c for s, c in osig.items() if s not in nsig]
        kept = [nsig[s] for s in nsig if s in osig]
        prof = [c for c in entered if uses_profile(c)]
        prof_any = [c for c in new if uses_profile(c)]
        tot_new += len(entered); tot_drop += len(dropped)
        tot_kept += len(kept); tot_profile += len(prof)
        per_view.append((view, len(entered), len(dropped), len(kept),
                         len(prof), len(prof_any)))

        W(f"{len(old)} ranked before, {len(new)} after. "
          f"**{len(kept)} unchanged, {len(dropped)} dropped out, "
          f"{len(entered)} new.** Of the {len(entered)} new, "
          f"**{len(prof)} use a profile dimension**; "
          f"{len(prof_any)} of the {len(new)} findings in the new top list do.\n")

        if entered:
            W("\n### Entered\n")
            for c in entered:
                hits = uses_profile(c)
                W(f"- `{c.get('pattern_type')}` **{c.get('measure')}** by "
                  f"`{c.get('breakdown')}`, varied along "
                  f"`{c.get('extending_dimension')}`"
                  + (f" — **profile: {', '.join(sorted(hits))}**" if hits
                     else " — no profile dimension"))
                W(f"  - {summary(c, sig)[:220]}")
        if dropped:
            W("\n### Dropped out\n")
            for c in dropped:
                W(f"- `{c.get('pattern_type')}` **{c.get('measure')}** by "
                  f"`{c.get('breakdown')}`, varied along "
                  f"`{c.get('extending_dimension')}`")
                W(f"  - {summary(c, sig)[:220]}")

    W("\n## Summary\n")
    W("| view | new | dropped | unchanged | new using a profile band | all findings using one |")
    W("|---|---|---|---|---|---|")
    for v, n, d, k, p, pa in per_view:
        W(f"| {v} | {n} | {d} | {k} | {p} | {pa} |")
    W(f"| **total** | **{tot_new}** | **{tot_drop}** | **{tot_kept}** "
      f"| **{tot_profile}** | |")
    io.open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"wrote {a.out}: {tot_new} new, {tot_drop} dropped, "
          f"{tot_kept} unchanged, {tot_profile} new findings use a profile band")


if __name__ == "__main__":
    sys.exit(main())

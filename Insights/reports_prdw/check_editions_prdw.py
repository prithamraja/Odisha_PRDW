"""WP-D3 T4b/T4c — the published-artefact checks, over EVERY edition.

The executive report already has `handoffs/WPD2_calibration/check_report_prdw.py`.
This is its counterpart for the artefacts WP-D3 publishes: the five gamma
editions and the global feed's markdown twin. It exists as a separate script
rather than an argument to that one because the gamma editions are not the same
document -- each one is a DIFFERENT re-ranking of the same candidates, so
"does the caveat appear exactly where a finding qualifies" has to be re-derived
per edition, against that edition's own ranked list.

It ships here, beside the artefacts it checks, for the reason WP-D1's D-12
ruling gave for the pack's verification scripts: re-runnable parity beats format
purity. It makes no API call and no network call.

  (a) PROSE GATE          -- src/prose_gate.py, unmodified, over each edition
  (b) NO HOLLOW SECTION   -- every view's section in every edition carries real
                             prose and not just its reading note. This is the
                             check that catches the silent-empty-completion
                             failure, and the gamma path calls the LLM
                             separately from phase5b, so passing there proves
                             nothing here
  (c) CAVEATS RIDE ALONG  -- the FY 2023-24 reporting caveat appears in a
                             section IF AND ONLY IF one of the findings that
                             section was written from trips the deterministic
                             test, re-derived per gamma; and where it appears it
                             sits inside the deterministic note, not in prose
  (d) FRAMING RULES       -- same iff test for the A6 linkage sentence and the
                             A9 XV FC earmark sentence
  (e) ONE CANDIDATE SET   -- every artefact carries the same candidate-set id
                             and the same run stamp. This is the stale-editions
                             lesson as an assertion: a suite that fails here is
                             a mixed suite whatever else is true of it

Usage:
    python Insights/reports_prdw/check_editions_prdw.py --base Insights
"""
import argparse
import io
import os
import re
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the Insights directory")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    src = os.path.join(base, "src")
    reports = os.path.join(base, "reports_prdw")
    sys.path.insert(0, src)

    import phase5b_report as p5b
    import phase5c_gamma_reports as gam
    import phase5c_global_feed as feed
    import prose_gate

    failures = []

    def check(ok, label, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
              + (f"  -- {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    editions = {g: os.path.join(reports, f"gamma_{g}_report.md")
                for g in gam.GAMMA_VALUES}
    feed_md = os.path.join(reports, "global_feed.md")

    print("=" * 72)
    print("WP-D3 T4b/T4c — EDITION CHECKS")
    print("=" * 72)
    missing = [g for g, p in editions.items() if not os.path.exists(p)]
    check(not missing, f"all {len(gam.GAMMA_VALUES)} gamma editions exist",
          f"missing={missing}" if missing else "")
    check(os.path.exists(feed_md), "the feed's markdown twin exists")
    if missing:
        print("\nCannot check editions that were not generated.")
        return 1

    # ------------------------------------------------------------------ (a)
    print("\n=== (a) prose gate, every edition ===")
    proc = subprocess.run(
        [sys.executable, os.path.join(src, "prose_gate.py")]
        + [editions[g] for g in gam.GAMMA_VALUES],
        capture_output=True, text=True)
    print("\n".join("      " + ln for ln in proc.stdout.strip().split("\n")))
    check(proc.returncode == 0, "prose gate clean on all editions",
          f"rc={proc.returncode}")

    # ---------------------------------------------------- the per-gamma truth
    # Steps 1 and 2 of the generator, replayed exactly: rescore at this gamma,
    # prefilter, rank to K_PER_VIEW, enrich. No API call. This is what the
    # section was written from, so it is what the caveat tests are run against.
    print("\n=== per-gamma re-derivation of what each section was written from ===")
    views, _ = gam.discover_views()
    raw = {name: gam.load_candidates(path) for name, _, _, path in views}
    s_stars = {name: gam.compute_s_star(cfg.tau) for name, cfg, _, _ in views}

    enriched_by_gamma = {}
    for gamma in gam.GAMMA_VALUES:
        per_view = {}
        for view_name, config, _, _ in views:
            rescored = gam.rescore_candidates(raw[view_name], gamma,
                                              s_stars[view_name])
            filtered = gam.prefilter_candidates(rescored, max_candidates=5000)
            ranked = gam.rank_metainsights(filtered, k=gam.K_PER_VIEW)
            as_dicts = [c.to_dict() if hasattr(c, "to_dict") else c
                        for c in ranked]
            per_view[view_name] = p5b.enrich_candidates_with_stats(
                view_name, as_dicts, config)
        enriched_by_gamma[gamma] = per_view
        print(f"  gamma {gamma}: "
              + ", ".join(f"{v} {len(per_view[v])}" for v in sorted(per_view)))

    parsed = {g: prose_gate.split_sections(io.open(p, encoding="utf-8").read())
              for g, p in editions.items()}

    def section_of(gamma, view_name):
        for vn, title, lines in parsed[gamma]:
            if vn == view_name:
                return title, lines
        return None, []

    # ------------------------------------------------------------------ (b)
    print("\n=== (b) no hollow section, any edition ===")
    for gamma in gam.GAMMA_VALUES:
        for view_name, _, view_title, _ in views:
            title, lines = section_of(gamma, view_name)
            body = [ln for _, ln in lines
                    if ln.strip() and not ln.startswith(">")
                    and not ln.startswith("---")]
            words = sum(len(ln.split()) for ln in body)
            check(words >= 100, f"gamma {gamma} / {view_title}: carries prose",
                  f"{words} words")

    # ---------------------------------------------------------------- (c)(d)
    # One table, three deterministic sentences, the same iff test on each.
    RULES = [
        ("FY 2023-24 reporting caveat", "reporting_caveat",
         lambda: p5b.COUNT_CAVEAT_SENTENCE),
        ("A6 linkage framing", "linkage_framing", lambda: p5b.LINKAGE_SENTENCE),
        ("A9 XV FC earmark", "earmark_framing", None),
    ]
    print("\n=== (c)+(d) deterministic caveats ride with the findings ===")
    for gamma in gam.GAMMA_VALUES:
        for view_name, _, view_title, _ in views:
            enriched = enriched_by_gamma[gamma][view_name]
            title, lines = section_of(gamma, view_name)
            body = "\n".join(ln for _, ln in lines)
            note_lines = [ln for _, ln in lines
                          if ln.startswith(p5b.READING_NOTE_MARKER)]

            for label, flag, sentence_fn in RULES:
                qualifying = [i + 1 for i, c in enumerate(enriched)
                              if c.get(flag)]
                expected = bool(qualifying)
                if sentence_fn is not None:
                    sentence = sentence_fn()
                else:
                    # the earmark sentence carries measured figures, so it is
                    # taken from the finding that produced it -- the same one
                    # reading_note_block picks: the widest scope
                    got = [c for c in enriched if c.get("earmark_sentence")]
                    sentence = (
                        min(got, key=lambda c: len(c.get("base_subspace") or []))
                        ["earmark_sentence"] if got else None
                    )
                if sentence is None:
                    check(not expected,
                          f"gamma {gamma} / {view_title}: {label} not expected")
                    continue
                present = sentence in body
                check(present == expected,
                      f"gamma {gamma} / {view_title}: {label} present == "
                      f"a finding qualifies",
                      f"qualifying={qualifying or 'none'}, in edition={present}")
                if present:
                    check(any(sentence in ln for ln in note_lines),
                          f"gamma {gamma} / {view_title}: {label} sits inside "
                          f"the deterministic note")

    # ------------------------------------------------------------------ (f)
    # THE ELEVATION CHECK. D29 says the XV FC earmark deviation is to be
    # "elevated in the report, not footnoted". The deterministic sentence in the
    # reading note is the footnote; it is necessary and it is not sufficient.
    # This checks the MODEL'S OWN PROSE -- the section body with the reading-note
    # blockquote removed -- carries the earmarked share. The first run of this WP
    # failed exactly here: the finding was ranked 12th, carried its measured
    # block, put its sentence in the note, and the prose never mentioned it.
    print("\n=== (f) the earmark finding is ELEVATED, not footnoted (D29) ===")
    exec_report = os.path.join(reports, "executive_metainsight_report.md")
    targets = [(f"gamma {g}", editions[g], enriched_by_gamma[g])
               for g in gam.GAMMA_VALUES]
    if os.path.exists(exec_report):
        # the executive report is written from the k=15 ranked lists, not from a
        # gamma re-ranking, so it needs its own enrichment
        exec_enriched = {}
        for view_name, config, _, _ in views:
            rp = os.path.join(base, "metainsights", f"{view_name}_ranked.json")
            if os.path.exists(rp):
                import json as _json
                exec_enriched[view_name] = p5b.enrich_candidates_with_stats(
                    view_name, _json.load(io.open(rp, encoding="utf-8")), config)
        targets.append(("executive report", exec_report, exec_enriched))

    for label, path, enriched_map in targets:
        md = io.open(path, encoding="utf-8").read()
        for vn, title, lines in prose_gate.split_sections(md):
            if vn is None or vn not in enriched_map:
                continue
            carriers = [c for c in enriched_map[vn]
                        if isinstance(c.get("stats"), dict)
                        and "earmark_framing" in c["stats"]]
            if not carriers:
                continue
            share = carriers[0]["stats"]["earmark_framing"][
                "on_the_two_earmarked_purposes"]
            outside = carriers[0]["stats"]["earmark_framing"][
                "amount_outside_them"]
            prose = "\n".join(ln for _, ln in lines if not ln.startswith(">"))
            check(share in prose and outside in prose,
                  f"{label} / {title}: the earmarked share and the amount "
                  f"outside it appear in the PROSE, not only the note",
                  f"share {share} in prose={share in prose}, "
                  f"outside {outside} in prose={outside in prose}")

    # ------------------------------------------------------------------ (e)
    print("\n=== (e) one candidate set behind every artefact ===")
    identity = feed.source_set_identity()
    expected_id = identity["candidate_set_id"]
    id_re = re.compile(r"candidate set `([0-9a-f]+)`")
    stamp_re = re.compile(r"\*Generated (\S+) from candidate set")

    artefacts = dict(editions)
    artefacts["global_feed.md"] = feed_md
    seen_ids, seen_stamps = {}, {}
    for name, path in artefacts.items():
        head = io.open(path, encoding="utf-8").read(4096)
        found_id = id_re.search(head)
        found_stamp = stamp_re.search(head)
        check(found_id is not None,
              f"{os.path.basename(path)}: carries a candidate-set id")
        if found_id:
            seen_ids[name] = found_id.group(1)
        if found_stamp:
            seen_stamps[name] = found_stamp.group(1)

    check(len(set(seen_ids.values())) <= 1,
          "every artefact names the SAME candidate set", str(seen_ids))
    check(set(seen_ids.values()) in ({expected_id}, set()),
          "and it is the set currently on disk",
          f"on disk={expected_id}, in artefacts={sorted(set(seen_ids.values()))}")
    check(len(set(seen_stamps.values())) <= 1,
          "every artefact carries the SAME run stamp",
          str(sorted(set(seen_stamps.values()))))

    # the JSON's provenance lives in the sidecar (D16: no key may be added)
    sidecar = os.path.join(base, "metainsights", feed.SOURCE_SET_SIDECAR)
    check(os.path.exists(sidecar),
          f"the feed JSON's provenance sidecar exists ({feed.SOURCE_SET_SIDECAR})")
    if os.path.exists(sidecar):
        import json
        side = json.load(io.open(sidecar, encoding="utf-8"))
        check(side.get("candidate_set_id") == expected_id,
              "the sidecar names the same candidate set",
              f"{side.get('candidate_set_id')} vs {expected_id}")

    print(f"\n{'=' * 72}")
    print(f"{len(failures)} failure(s)"
          + (":\n  - " + "\n  - ".join(failures) if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

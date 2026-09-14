# WP-D11b brief — profile follow-on: split vectors, causal wording, unit labels, averaged twins

**Workstream:** Discover. **Nature: BUILD, gated — closes the two blockers
and the one calibration defect WP-D11 left open, on operator rulings of
2026-09-11.** **Authored:** PM, 2026-09-11. Decision number for the rulings:
**D61** (block D60–D69). Predecessor: `handoffs/WPD11_gp_profile.md` and its
report `handoffs/WPD11_REPORT.md` (read both first; this brief assumes them).

**Operator rulings this brief encodes (2026-09-11):**

1. **Vector files are split, not shrunk.** The decomposition vector file is
   136.8 MB, over GitHub's 100 MB per-file limit, and the deployed chat
   service reads the corpus from git. Split each `.npy` into parts under
   100 MB with a loader that concatenates them. No dimension truncation
   (declined 2026-09-04), no re-embedding, no record dropping.
2. **Causal wording is fixed the operator's way: one general sentence, no
   banned-word list.** The operator's own edit to the chat writer prompt
   (uncommitted in `DiscoverChat/context_brief.py`) is the wording. It is
   applied verbatim to the two writers that actually failed — the gamma
   editions writer and the feed writer — and the outcome is **measured**, not
   assumed. If the editions' word-scan gate stays red under the general
   sentence, that is the finding; do not reroll and do not add a word list.
3. **Size-band labels carry their unit at prose time only.** `'Under 2,500'`
   is displayed as "under 2,500 people" wherever prose is written. The pack,
   the Parquet views, the categorical domain and the mined candidates keep
   the bare label. No pack change, no view1 re-mine.
4. **Averaged twins on views 3 and 4.** Per-row averages of the main
   measures (`agg="avg"`, the WP-D2c intensity mechanism) so a band of 15
   GPs is compared with a band of 2 by the typical GP, not by the headcount.
   **Re-mine view3 and view4 only.** view1 and view2 candidates are reused
   unchanged.
5. **Every edition and both corpora regenerate from the resulting candidate
   set** (unavoidable: rulings 2–4 only take effect in the prose, and a new
   candidate set must not ship beside stale sidecars).

**For:** the operator-controlled implementation agent.

**Files in scope (you may write ONLY these):**
`Insights/src/phase5f_decompose.py` and `phase5d_retrieval_corpus.py`
(vector writing), `DiscoverChat/corpus.py` and `DiscoverChat/config.py`
(vector loading and stamp), `DiscoverChat/gates.py` (the prompt-assertion
line and a part-size check only), `DiscoverChat/context_brief.py` (the
operator's edit stands; fix the typo "impotant" only),
`Insights/src/phase5c_gamma_reports.py` (rule 5 text only),
`Insights/src/insight_prose_config.py` (`CONTEXT` sentence, `run_log_dir`),
`Insights/src/phase5e_insight_prose.py` (display labels; checker hook),
`Insights/reports_prdw/check_insight_prose.py` (D41 scan),
`Insights/src/phase2_engine.py` and `phase4a_engine.py` (`VIEW3_CONFIG` /
`VIEW4_CONFIG` measure lists only), `Insights/src/phase5b_report.py`
(glossary entries and `_UNITS` for the new measures; display labels),
`DiscoverChat/glossary.py` (display labels), `Insights/metainsights/**`,
`Insights/reports_prdw/**`, `.gitignore` (only if the split changes the
tracked spellings), `handoffs/WPD11b_REPORT.md`,
`handoffs/WPD11b_calibration/**` (new).

**DO NOT TOUCH:** `Data/**`, `Insights/domain_pack_prdw/**` (the pack is
correct; ruling 3 forbids a label change there), `Insights/DISCOVER_VIEW_MAPPING.md`,
`handoffs/PROJECT_PLAN.md`, `Ask/**`, `frontend/**`, `deploy/**`, `.env`,
engine algorithms, the judge prompt, `handoffs/WPD11_*` (the prior record).

**Preconditions — verify all; if any fail, STOP and flag:**

- [ ] The working tree carries WP-D11's uncommitted output (candidate set
      `d619a72e4fe98d5f` in every stamp; `git status` shows the 47 modified
      files plus the WP-D11 untracked ones). Nothing has been committed since
      `31f343d`. The operator's edit to `context_brief.py` is present.
- [ ] The mirror `C:\dev\odisha-d11` still holds the four built Parquets
      and `Insights/views_baseline/`. If not, rebuild with the WP-D11 §1
      command before anything else; T5's baseline diff needs them.
- [ ] Live `OPENAI_API_KEY` and `NOVITA_API_KEY` in `Insights/.env`; probe
      one call each.
- [ ] Sweep `C:\dev\odisha-*` for follow-on work already started.

**Read first:** `handoffs/WPD11_REPORT.md` §§4–9 and
`handoffs/WPD11_calibration/README.md` (the mining command WITH its cache
flags — copy it verbatim); `handoffs/WPD10_corpus_footprint.md` (vector
format and the determinism rules the split must keep);
`handoffs/WPD2c_engine_scaling.md` A4 and its appendix (the intensity-measure
mechanism and glossary form you are extending); `Insights/src/prose_gate.py`
(the D41 word scan the editions gate runs — you will reuse its list in the
feed checker, not write a second one).

---

## Objective

The four WP-D11 defects are closed on the operator's rulings and the whole
artefact set is regenerated from one new candidate set: vector files fit
under the git limit with identical retrieval; the three writers carry the
operator's causal sentence and the editions gate outcome is measured;
size-band findings render with a unit and their prose fallback rate is
re-measured against WP-D11's 57 percent; views 3 and 4 carry averaged
measures and their top-15s show whether the band-membership artifact is
displaced. Nothing is committed or pushed.

## Non-goals

No view1 or view2 re-mine. No pack change of any kind. No banned-word list
in any prompt (ruling 2). No ratio measures. No frontend change. No data
fixes. No git or Railway operations.

## Facts you need

1. **The split must be invisible to retrieval.** WP-D10 proved fp16 storage
   at 99.97 percent pool overlap and byte-identical rebuilds; the split must
   keep both. Load the parts, concatenate, and the resulting matrix must be
   byte-identical to the unsplit array. `semantic_pin()` must not change
   (it drives cache reuse); `embedding_pin()` may record the part scheme.
2. **The operator's causal sentence** is the one now in
   `CONSOLIDATING_WRITER_PROMPT`: *"It is very important that you do not
   make causal claims - none of our data can be used to determine
   causality."* (with the typo fixed). That sentence, verbatim, goes into
   the editions writer's rule 5 and the feed writer's `CONTEXT`. The chat
   gate `consolidation-prompt-is-the-operators` asserts the old line
   `"Do not make causal claims ever"`; update that assertion to the new
   sentence — the gate exists to pin the operator's text, and this is the
   operator's text.
3. **The editions gate is a word scan** (`prose_gate.py`: drives / because /
   as a result / consequently / thereby / therefore / hence and others). The
   WP-D11 editions failed 0/5 on "therefore" and "consequently" in
   social-composition sentences. Whether a general instruction clears a word
   scan is the open question of ruling 2. **Report the outcome either way;
   a red gate here is a result to hand the operator, not a reason to reroll
   or to add words to the prompt.** The feed has never been scanned; you add
   the same scan to `check_insight_prose.py` (import the compiled list from
   `prose_gate`, do not copy it) so the feed and the editions are judged by
   one rule.
4. **Size-band display labels.** Values `'Under 2,500'`, `'2,500 to 5,000'`,
   `'5,000 to 10,000'`, `'10,000 and above'` display as "under 2,500 people",
   "2,500 to 5,000 people", "5,000 to 10,000 people", "10,000 people and
   above". Apply in the packet renderer (`phase5e`), the report glossary
   display layer (`phase5b_report`) and the chat glossary
   (`DiscoverChat/glossary.py`) so all three surfaces agree. The numeral
   checks bind figures to source sentences: confirm "2,500 people" does not
   break the binding (the digits are unchanged; the word is not a numeral).
   The verifier's Source Material must carry the displayed form, or it will
   reject "people" exactly as it rejected "population".
5. **Averaged twins.** `MeasureConfig(name=f"{m}_mean", agg="avg", column=m)`
   — the same alias pattern as `payment_amount_mean`. On **view4** (row =
   GP, so the average is per GP): `n_activities`, `planned_cost`,
   `sanctioned_total`, `expenditure_total`, `overspend_vs_plan`,
   `overspend_vs_sanction`, `n_admin_approvals`, `evidence_uploads`,
   `payment_amount`, `receipt_amount`, `households_tap_water`,
   `household_toilets`, `osr_collected`, `shgs`. On **view3** (row = GP-year,
   so the average is per GP-year): the first ten of those. Every new measure
   needs a `_UNITS` entry ("rupees, AVERAGED per Gram Panchayat" / "per
   Gram Panchayat-year") with a formatter, and a glossary entry in the
   WP-D2c appendix form. `impact_measures` unchanged. The A4/2b
   size-share rule already treats a `_mean` as the intensity companion of
   its total; confirm it fires for the new pairs rather than treating them
   as twins to merge.
6. **Mining command** — from `WPD11_calibration/README.md`, with
   `--views view3,view4` and the cache flags. Before mining, record the
   SHA-256 of `view1_candidates.json` and `view2_candidates.json`; after,
   they must be unchanged. The candidate set id will change because it is
   computed over all candidate files; that is expected.
7. **Prose spend.** Set `run_log_dir` to a per-WP directory (`wpd11b_run`)
   — the §9.C fix — so the 150-call cap counts this WP alone. Reading notes
   OFF (D48-1). Verifier retry-on-empty stays.
8. **Determinism yardsticks** (WP-D10): the offline gate's
   `numerals-traceable` count is noisy (±15); pool-overlap is the measure,
   compared against the 6× endpoint jitter, never strict set equality.

## Tasks

### T1 — Split the vector files

- **Do:** in both builders, write `<name>.npy` as parts
  `<name>.part0.npy`, `<name>.part1.npy`, … each ≤ 95 MB, and record the
  part list and per-part SHA-256 in the stamp. In the loader, read the parts
  in order and concatenate; refuse to load if a part named in the stamp is
  missing or its hash differs. Remove the unsplit `.npy` from the tracked
  spellings; add a `gates.py` check that every tracked vector part is under
  100 MB.
- **Done when:** the concatenated matrix is byte-identical to the unsplit
  array (assert with a hash, for both corpora); `semantic_pin()` unchanged;
  a rebuild with no changed text makes zero embedding calls.

### T2 — Causal wording, the operator's way

- **Do:** fix the typo in `context_brief.py`; update the gate assertion
  (fact 2); add the sentence to `phase5c_gamma_reports.build_prompt` rule 5
  and to `insight_prose_config.CONTEXT`; add the D41 scan to
  `check_insight_prose.py` as a gating check that reports every hit with
  its line.
- **Done when:** `gates.py` prompt check green with the new assertion; the
  scan runs on the regenerated feed and its result is in the report with
  hit counts for the WP-D11 feed (baseline) and the new one.

### T3 — Unit labels at prose time

- **Do:** one display map for the four values, defined once and imported by
  the three surfaces (fact 4). No change to any pack file, view, or
  candidate.
- **Done when:** a grep of the regenerated feed, editions and a chat answer
  finds no bare band label; the numeral checks pass; the verifier's Source
  Material shows the unit form.

### T4 — Averaged twins and the two-view re-mine

- **Do:** extend `VIEW3_CONFIG` and `VIEW4_CONFIG` (fact 5) with units and
  glossary; run the four-view config gate
  (`WPD11_calibration/verify_configs_prdw_d11.py`, updated for the new
  measures); mine view3 and view4 with the cache flags; verify view1 and
  view2 candidate files unchanged by hash; re-rank all four; run the WP-D2c
  regression gate.
- **Done when:** view3 and view4 drained; regression gate 0 failures; the
  report shows, for each of the two views, how many top-15 findings rest on
  a `_mean` measure and which band-headcount findings they displaced.
- **Escalate if:** the ranker treats a `_mean` and its total as twins and
  merges them — that is a rule-2b interaction the operator must rule on.

### T5 — Regenerate everything from the new candidate set

- **Do:** global feed, five gamma editions, executive report + PDF,
  `insight_prose.json` + `insight_feed.md`, both corpora (split), then
  `check_feed_contract`, `check_insight_prose` (with the new scan),
  `check_editions_prdw`, DiscoverChat `gates.py` offline and `--live`, and
  the unit tests. Refresh the calibration package: `WPD11b_calibration/`
  with per-view findings sheets, the labelling CSV (blank labels), and a
  diff against both `d619a72e4fe98d5f` (WP-D11) and `a7f991c1df3771f9`
  (pre-amendment).
- **Done when:** every artefact carries one candidate set id; every gate
  result is recorded, red or green; prose first-pass / regenerated /
  fell-back counts are reported overall and for size-band findings
  specifically, against WP-D11's 16 / 22 / 12 and 57 percent.

### T6 — Report

`handoffs/WPD11b_REPORT.md` per the spec below. No git operations.

## Cut-line

T1 and T2 are independent of T3–T5 and must ship even if the mining path
stalls. T3, T4 and T5 are one unit: never regenerate a subset of editions.
If the editions gate is red after T5, ship everything with the gate reported
red; the operator decides the next step.

## Escalation protocol

- **STOP:** preconditions fail; view1 or view2 candidate hashes change;
  the concatenated vectors are not byte-identical; the verifier shows
  silently empty sections.
- **Decide-and-document:** part size threshold; label wording micro-choices;
  formatter strings; which `_mean` measures to keep if a config gate rejects
  one.
- **Never:** add a banned-word list; reroll prose to clear a gate; change a
  pack file; truncate or re-embed vectors; commit; push.

## Gate (definition of done)

1. Both corpora load from parts, byte-identical to unsplit; every tracked
   vector file under 100 MB; zero embedding calls on an unchanged rebuild.
2. Prompt gate green on the operator's wording; the D41 scan runs on the
   feed; editions gate outcome reported honestly.
3. No bare size-band label in any regenerated prose surface; numeral and
   verifier checks pass on the unit form.
4. view3 and view4 re-mined with averaged twins; view1/view2 candidates
   unchanged; regression gate 0 failures; `_mean` findings present in both
   top-15s.
5. One candidate set across every artefact; calibration package refreshed;
   fallback rate on size-band findings reported against 57 percent.
6. **Operator calibration session** on the refreshed top-15s. Closes the WP.

Gate holder: PM replays 1–5; operator holds 6 and rules on a red editions
gate.

## Report spec — `handoffs/WPD11b_REPORT.md`

§0 status table (six gates); §1 the split (sizes, hashes, loader change);
§2 causal wording (the three prompts as changed, gate results, D41 hit
counts before and after, whether the general sentence cleared the word
scan); §3 unit labels (where applied, verifier behaviour, size-band fallback
rate before and after); §4 mining (view3/view4 timings, hash proof for
view1/view2, `_mean` findings in each top-15 and what they displaced);
§5 editions and spend (candidate set id, calls against cap, prose counts);
§6 decision journal; §7 proposed amendments; §8 self-audit and what the PM
should replay first.

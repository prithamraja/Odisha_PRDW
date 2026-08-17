# WP-D3 — Global feed + gamma editions (handoff brief)

**Workstream:** Discover. **For:** the operator-controlled implementation agent.
**Status note:** drafted while WP-D2 was running. Slots marked `⟦PENDING-WPD2⟧`
are filled by the PM after the calibration session closes the WP-D2 workstream
gate. **Do not dispatch — and if dispatched, STOP — while any slot is unfilled:**
a feed generated from a pre-calibration candidate set is stale by construction.

**Files in scope (you may write ONLY these):**
`Insights/src/phase5c_global_feed.py` (paths, view registry, coverage weights —
**never the emitted JSON structure: D16**), `Insights/src/phase5c_gamma_reports.py`
(paths, budget-constant unification, AP prompt text → PR&DW),
`Insights/src/phase2_engine.py` (**one line — the D29-authorized depth-2
default flip in `VIEW1_CONFIG`'s sample branch, + its comment**),
`Insights/src/phase5b_report.py` (**T0's two framing additions only: the A8
utilization companion and the #12 earmark-elevation rule — D29**),
`Insights/reports_prdw/**` and `Insights/metainsights/**` outputs,
`handoffs/WPD3_REPORT.md`.
**DO NOT TOUCH:** everything else — engine, ranking, phase5b, prose gate, pack,
`discover_config.py` (already pinned by WP-D2), `Data/`, `Chatbot/`, `eval/`,
`PROJECT_PLAN.md`, `.env`.

**Preconditions — verify all; STOP on any failure:**

- [ ] WP-D2's workstream gate is closed (D28) and both calibration sessions
      are recorded (D27/D29). **The candidate set this WP feeds from is the
      fresh re-mine T0 performs at the committed default config** — never a
      pre-existing package directory.
- [ ] T0's re-mine must DRAIN on all three views (a feed built on a truncated
      run must not ship) — this is T0's own done-check, hashes recorded.
- [ ] Tree clean and committed; local-mirror execution; `.env` key present.
- [ ] Operator's edition decision recorded below (Facts 6) — if marked
      undecided, STOP.

**Read first:** the two phase5c file headers (the feed's seed+decay design and
the gamma mechanism — both documented in place); `handoffs/WPD2_REPORT.md`
(model probe evidence, drain diagnostics); `PROJECT_PLAN.md` D16–D17, D22–D23;
mapping doc §5 (caveat rules follow findings into every edition).

---

## Objective

The frontend Discover feed (`global_feed.json` + its markdown twin) and the
published gamma report edition(s) exist, generated **from the final
post-calibration candidate set in one run**, with the feed's JSON structure
byte-shape-compatible with the AP contract (D16) and every edition regenerated
together (the stale-editions lesson).

## Non-goals

- No re-mining, no re-ranking changes, no phase5b edits — this WP re-orders and
  re-renders a completed, calibrated run.
- No feed-shape evolution, whatever the temptation (D16: operator decision only).
- No frontend work; delivery ends at the agreed handover path (Facts 7).

## Facts you need

1. Phase5 ranks within a view; the feed is the cross-view front page. Its
   mechanism (seed one finding per view unconditionally, fill remaining slots
   by `view_weight × score × RANK_DECAY^(rank−1)`) is inherited — keep it.
2. **Coverage weights become EQUAL for PR&DW** (operator-ratified editorial
   choice, D24): AP weighted views by farmer-count coverage; all three PR&DW
   views cover all 20 GPs (statewide ~6,800) by construction (zero-fill), so
   population coverage cannot distinguish them and equality is the honest
   weight. The weights remain PRINTED in both artefact headers, as the AP
   design requires — a reader must be able to disagree.
3. The AP feed reads `rtgs_csv/*.csv` for its weights — that input disappears
   with equal weights; remove the dependency rather than porting it.
4. **Unify the gamma budget:** `phase5c_gamma_reports.py` hardcodes
   `MAX_COMPLETION_TOKENS = 9000`; switch it to
   `discover_config.DISCOVER_MAX_COMPLETION_TOKENS`. This is the exact
   one-path-under-budgeted failure the shared constant exists to prevent.
5. The gamma view registry is discovered (config + candidates + description
   present) — with WP-D2's three views it adapts by itself; verify, don't
   assume.
6. **Editions (operator decision, 2026-08-15): generate ALL FIVE gamma
   editions (0.1 / 0.3 / 0.5 / 0.7 / 0.9), in one run, from T0's candidate
   set.** None is designated "published" yet — the operator reviews the suite
   and picks; that pick and every later regeneration follow the
   all-together rule (never a mix of fresh and stale files). Label each
   edition's header with its gamma and the shared candidate-set identity.
7. **Feed handover path (default, operator informed):**
   `Insights/metainsights/global_feed.json` + its markdown twin in
   `Insights/reports_prdw/` — the repo is the handover point; the frontend
   workstream consumes from there, and any future path change is a copy, not
   a rework. Contract check is against the writer's documented schema (D16).
8. Deterministic reading notes / caveats (incl. the FY 2023-24 count caveat)
   ride with findings into every edition — verify presence, same as WP-D2 T5c.

## Tasks

**T0 — Depth-2 default + the two session-2 framings + the canonical re-mine
(D29).** (a) Flip `VIEW1_CONFIG`'s **sample** branch to `max_subspace_depth=2`
(one line + comment; the depth-1 rationale comment becomes history, pointer to
D29). (b) **A8 utilization companion**: where a ranked finding highlights an
overspend measure, the enrichment attaches the ratio-of-sums
(Σ`total_expenditure` / Σ`total_cost`, and vs sanction where applicable) for
the highlighted groups — computed downstream from the num/denom columns (the
no-materialized-ratios rule holds; engine config untouched), with a prompt
rule to present the story as utilization percentage, absolute in parens.
(c) **#12 elevation**: a framing rule stating the XV FC tied-grant earmark so
the measured deviation (97.6% vs the rule's expected share) reads as
compliance-relevant, deterministic text, never model-authored. (d) Re-mine all
three views at the committed config (~92 min for view1; **drain required**),
re-rank, regenerate the executive report, re-run the config/regression/report
gates. Record candidate hashes — this is the feed's source set.
*Done when:* gates green on the regenerated output; hashes in the report.

**T1 — Port paths + weights.** Output paths to `Insights/metainsights/` and
`Insights/reports_prdw/`; equal view weights (Facts 2–3); registry check
(Facts 5). *Done when:* feed runs end-to-end on the final candidate set;
weights and knobs printed in both artefact headers.

**T2 — Budget unification.** Facts 4. *Done when:* no completion-token literal
remains in either phase5c file.

**T3 — Generate.** One run, in order: gamma suite (Facts 6) then the feed, all
from the same candidate JSONs. Record which candidate files (path + hash) fed
it. *Done when:* every published artefact carries the same generation
timestamp and source-set identity in its header.

**T4 — Contract + determinism checks.** (a) Feed JSON structure: field-by-field
identical to the AP writer's emitted schema — document the schema in the
report; any difference is a STOP (D16). (b) Caveats present on qualifying
findings in every edition (Facts 8). (c) Prose sections non-hollow in every
gamma edition (the WP-D2 T5 check, re-run here because gamma editions call the
LLM separately). *Done when:* all three pass with evidence.

**T5 — Report.** `handoffs/WPD3_REPORT.md`: §0 gate table · §1 what was
generated from which candidate set (paths + hashes) · §2 schema documentation +
contract verdict · §3 caveat/hollow check evidence · §4 decision journal ·
§5 self-audit. No git operations.

## Cut-line

None — this WP is small and atomic. A partial delivery (feed without editions,
or editions from a different candidate set than the feed) is worse than no
delivery; that is the stale-editions lesson in one sentence.

## Escalation protocol

- **STOP:** any precondition or `⟦PENDING⟧` unfilled; feed schema would change;
  candidate set ambiguous or truncated; a gamma edition comes back hollow.
- **Decide-and-document:** output naming, header wording, edition file layout.
- **Never:** re-mine, re-rank, touch the shape, mix candidate sets, commit.

## Gate (definition of done)

1. Feed + published edition(s) generated from the single final candidate set,
   identities recorded.
2. Feed schema documented and unchanged vs the AP writer (D16).
3. Equal-weight choice printed in artefacts (D24); no stale edition exists
   anywhere in the output tree — editions from earlier runs deleted in the
   same change.
4. Budget constant unified; caveat + non-hollow checks green.
5. Handover: feed delivered to the Facts-7 path; frontend workstream (or
   operator) acknowledges receipt.

Gate holder: PM replays T4; operator confirms the edition choice and handover.
Closing this gate closes the Discover sample phase — the two reference packs
(`domain_pack/`, `domain_pack_rtgs/`) are then deleted per the handoff, as a
separate operator-approved commit.

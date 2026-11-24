# WP-D14 brief — place profile sheets: the build

**Workstream:** Discover. **Nature: BUILD, offline.** No model call, no
embedding call, no change to the running service. **Authored:** PM,
2026-11-24. **Decisions:** D75 (approach), D76 (the operator's nine rulings).
**For:** the operator-controlled implementation agent.

**The spec is `handoffs/PROFILE_SHEET_SPEC.md` (SIGNED).** It defines every
figure. This brief says how to build it, what to hand back, and how we will
know it is right. Where the spec is specific you have no design freedom. Where
this brief and the spec disagree, stop and say so in your report.

## What this package delivers

1. A builder that reads the view parquets and writes one **profile sheet** for
   every Gram Panchayat, block and district, and one for the whole: figures,
   standing among peers, short lists, and a ready-made sentence for every
   figure.
2. A **store** of those sheets, committed beside the insight corpora and
   stamped with the same candidate set.
3. A small **reader** that returns one place's sheet by level and code. Nothing
   in the service calls it yet.
4. **Checks** that prove the sheets equal the views and the insights.
5. A **scale test** on a made-up state of 6,800 Gram Panchayats.

Wiring the sheets into `/chat` is WP-D15. The page is WP-D16. Neither is
written yet. Do not start them.

## The operator's rulings this brief encodes (2026-11-24, D76)

| # | Ruling | What it means for you |
|---|---|---|
| R1 | Peers as in spec §4; no standing from fewer than 5 peers; exact place up to 50 peers, quarters above | T2 |
| R2 | "Spent" is the views' `expenditure_total` as it stands | Do not remove the repeated spending rows. Do not read `Data/`. |
| R3 | By-year figures use the plan year of the activity | The by-year list comes from `view3`, never `view2` |
| R4 | A name that is both a Gram Panchayat and a block is answered for the block | Not yours (WP-D15). Build both sheets. |
| R5 | **The model chooses what to use. No "notable" marks.** | Compute no mark, store no threshold. Spec §7. |
| R6 | Sentence wording approved | Appendix A. Reproduce the examples character for character. |
| R7 | Places only | No sheets for schemes, sectors or years |
| R8 | Show the self-reported profile figures, with the "not checked" note and the H3–H5 checks | Rows H3–H5, I1–I3 |
| R9 | **No fixed note on the by-year list** | Store none |

---

## What exists (PM-verified 2026-11-24)

| Fact | Where |
|---|---|
| The views are built by `python Insights/src/build_views.py --pack Insights/domain_pack_prdw --data-dir Data --views-dir Insights/views_prdw --reports-dir Insights/reports_prdw --strict`. The parquets are gitignored. | `Insights/src/phase5f_decompose.py` header |
| A built copy is in `C:\dev\odisha-d11b\Insights\views_prdw\`. Its four files have the SHA-256 values recorded under `view_parquets` in `Insights/metainsights/decompose_corpus_stamp.json` (view1 `33311e2f…`, view2 `4b9b503d…`, view3 `9a4bea34…`, view4 `aa9ce0ad…`). | measured |
| The current candidate set is `610cb3d26dff7bf3`. The "as of" stamp is `generated_at` in `Insights/metainsights/global_feed_source_set.json` (2026-09-11T09:31:44Z). | measured |
| `view3_gp_performance`: 120 rows = 20 Gram Panchayats × 6 fiscal years (2020-2021 … 2025-2026). Keys `gp_lgd_code`, `block_code`, `district_code` (VARCHAR) with `gp_name`, `block_name`, `district_name`. Measures: `n_plans`, `n_activities`, `n_costed`, `n_costless`, `planned_cost`, `sanctioned_total`, `work_proposed_cost`, `n_admin_approvals`, `n_tech_approvals`, `expenditure_total`, `overspend_vs_plan`, `overspend_vs_sanction`, `payment_amount`, `receipt_amount`, `n_completed`, `n_ongoing`, `n_abandoned`, `n_with_evidence`, `evidence_uploads`. | measured |
| `view1_activity_lifecycle`: 12,704 rows, one per planned activity. `view4_gp_profile`: 20 rows, one per Gram Panchayat. | WP-D11 |
| The sample has 20 Gram Panchayats, 16 blocks (13 hold one Gram Panchayat, two hold two, one holds three) and 9 districts. | measured |
| Money is formatted by `format_measure(view, measure, value)`: `76548042` → `Rs 7.65 crore`, `2894236` → `Rs 28.94 lakh`, `15000` → `Rs 15,000`, `0` → `Rs 0`, `-58968148` → `Rs -5.90 crore`. | `Insights/src/phase5b_report.py:288` |
| **`format_measure` on a count adds a unit noun and rounds**: `852` → `852 activities`, `602.5` → `602 activities`, `168` → `168 approval records`. **Do not use it for counts** (see Fact 4). | measured |
| `glossary.signed_money("Rs -5.90 crore", "overspend_vs_plan")` → `Rs 5.90 crore below plan`. A positive value comes back unchanged (`Rs 12.35 lakh`), so the "above plan" words are yours to add from `glossary.signed_above`. | `DiscoverChat/glossary.py:278-290` |
| `DiscoverChat/glossary.py` already imports from `phase5f_decompose` and `phase5b_report`. `DiscoverChat/config.py` puts `Insights/src` on the path and holds the store paths (`METAINSIGHTS`, `CORPUS_PATH`, …). | code |
| A breakdown record holds `view`, `measure`, `subspace` (a list of `[dimension, value]` pairs, empty for the whole), `geography` (the resolved codes), `total` and `total_display`. Record `d1-00248` is the whole's `overspend_vs_plan`: total `-519613445.54`, display `Rs -51.96 crore`. | `decompose_corpus.json.gz` |
| The citation check reads numerals with `_NUM = \d{4}-\d{2,4}|\d+(?:[.,]\d+)*` and tags with `\[([^\[\]\n]{1,60})\]`. Corpus ids are `1-00042` and `d1-00042`. | `DiscoverChat/checks.py:49, 325` |
| The gate is `python -m DiscoverChat.gates`; the suite is `python -m pytest DiscoverChat/tests -q`. Two model-evidence checks in the gate are red by an operator decision (D69). They are not yours to fix. | D71 |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] `handoffs/PROFILE_SHEET_SPEC.md` says **SIGNED … (D76)**.
- [ ] Work from a fresh local mirror, never the Drive path: `C:\dev\odisha-d14`.
      Copy results back to the Drive repo at the end of each task.
- [ ] Sweep `C:\dev\odisha-*` for earlier profile-sheet work. There should be
      none.
- [ ] Uncommitted files you may meet and must leave alone:
      `DiscoverChat/experiments/**` (the operator's writer tests),
      `handoffs/Kalimela insights.pdf`, and the PM's files in `handoffs/`. Any
      other uncommitted change under `Insights/` or `DiscoverChat/`: ask the
      operator.
- [ ] Put the four view parquets in `Insights/views_prdw/` of your mirror —
      copy them from `C:\dev\odisha-d11b\Insights\views_prdw\` or rebuild them.
      **Their SHA-256 must equal the `view_parquets` values in
      `decompose_corpus_stamp.json`.** If they do not, STOP: sheets built from
      other views would disagree with the insights.
- [ ] Baselines, kept as files beside the mirror: the gate and the suite before
      any change. Record the counts, including the two known red checks.
- [ ] No API key is needed. If your work wants one, you have left the scope.

---

## Facts you need

1. **Levels and keys.** `gp` keyed by `gp_lgd_code`, `block` by `block_code`,
   `district` by `district_code`, and `all` with the fixed key `all`. Codes
   stay VARCHAR. A Gram Panchayat must map to exactly one block and a block to
   exactly one district in the views; if not, STOP.
2. **Every place gets a sheet.** The list of Gram Panchayats is `view4` (the
   master). A place with no activity gets a sheet of zeros.
3. **The fiscal years** are the distinct `fiscal_year` values of `view3`. "The
   latest year" is the largest of them. No date from the clock appears in any
   figure or sentence.
4. **Formats.**
   - Money: `format_measure("view3", <a rupee measure>, value)`.
   - Counts: digits with thousands separators and nothing else (`852`,
     `12,704`). A middle value of counts is shown whole when it is whole
     (`712`, `79`) and to one decimal when it is not (`602.5`, `95.5`).
   - Shares: `f"{share * 100:.1f}%"`, worked out from the unrounded sums.
   - Fiscal years: as stored (`2023-2024`).
   - People per household (H5): one decimal.
5. **A share is never averaged.** At every level it is the level's own
   numerator over the level's own denominator. Rangeilunda block is 23.1%; the
   mean of its two Gram Panchayats' shares (28.8%) is wrong.
6. **A blank is not a zero.** A share whose denominator is zero has no value,
   no standing and no sentence. Places with no value are left out of that
   figure's ranking and out of its count of peers.
7. **Standing** (spec §4), for A1, A3, A4, A5, A6, E1, E2, E4, F1, G1, G2, G3.
   Stored for every peer group of the place: rank from the highest, rank from
   the lowest, number of peers, number tied, the middle value, the quarter.
   - Ranks use the unrounded values. Equal values share a rank (`1, 2, 2, 4`).
   - The place itself counts among its peers.
   - Quarter: let `p` = (peers with a strictly smaller value) ÷ (peers). Lowest
     quarter when `p < 0.25`, then lower-middle, upper-middle, highest.
   - The **sentence** uses the smallest peer group with at least 5 members.
     In the sample that is always the whole sample.
8. **Set-based.** One grouped query per level for each part of a sheet. No
   query, and no dataframe filter, inside a loop over places. Writing out the
   sentences row by row is fine.
9. **The whole's name is one setting**, default `the whole sample`. No literal
   20, 16 or 9 anywhere in code (D15: the sample's size lives in data, not in
   code).
10. **Names are shown as stored**, with leading and trailing spaces trimmed
    (one theme is stored as `Theme 5 - Clean and Green Village ` with a
    trailing space). Do not correct spellings (`Poverty allevation programme`,
    `sarapacnh`). Log them.
11. **The unmapped theme** is the `theme` value `Unmapped theme`.
12. **E5's cut-off.** With six years ending 2025-2026, "three or more fiscal
    years before the latest" means a plan year of 2022-2023 or earlier.
13. **Not on a sheet:** anything per activity, any person's name, any free
    text, and no mark or threshold (R5).

---

## Tasks

### T1 — the main row, for every place at every level

- **Do:** spec §5, rows A1–A7, E1–E5, F1–F2, G1–G3, H1–H5, I1–I4, from `view3`
  (sums), `view1` (E3's planned money and top year, E5, H1, H2) and `view4`
  (H3–H5, I1–I3).
- **Done when:** every figure in spec §13 is reproduced exactly, for Kalimela
  Gram Panchayat, Kalimela block and the whole.
- **Trap:** E3's "plan year with the most" needs a tie rule — take the
  earliest year.

### T2 — standing

- **Do:** Fact 7, with window functions over each peer group.
- **Done when:** the standings in spec §13 are reproduced (two tables: among
  20 Gram Panchayats, among 16 blocks), and a block with fewer than 5 peers in
  its district has standings stored for it but uses the larger group in its
  sentences.
- **Trap:** the nearer end is named. Rank 13 from the highest of 16 is "4th
  lowest", not "13th highest". When the two ranks are equal, name it from the
  highest.

### T3 — the lists

- **Do:** spec §5 lists B (by year), C (by focus area, and by theme), D (money
  source: at planning, at sanction by scheme, who approved) and J (member
  places).
- **Order:** B by year, oldest first. C by planned cost, largest first, then
  by name. D schemes by sanctioned amount, largest first, the five largest
  then one "all others" line. D authorities by number of approvals, the three
  largest then "all others". J by A6 from the lowest, blanks last.
- **Done when:** the by-year table, the five focus areas, the money-source
  figures and the authority counts in spec §13 are reproduced.

### T4 — sentences and ids

- **Do:** Appendix A. Every sentence is written from stored values by a fixed
  pattern.
- **Ids:** `p-<level>-<code>-<row>`, for example `p-gp-119936-A6`,
  `p-block-3843-A1`, `p-all-A7`. List lines add a key:
  `p-gp-119936-B-2023-2024`, `p-gp-119936-C-drinking-water`,
  `p-gp-119936-CT-6` (theme number; `CT-unmapped`), `p-gp-119936-DS-<slug>`
  (scheme; `DS-others`), `p-gp-119936-D-plan`, `p-gp-119936-D-authority`,
  `p-block-3843-J-119936` (the member's code).
  A slug is the name in lower case with every run of other characters turned
  into one hyphen, cut to 32 characters.
- **Rules for every id:** at most 60 characters; no square bracket, no space;
  unique across the whole store; the same from one build to the next. Two
  names at one place that give the same slug: STOP and report.
- **Done when:** the Appendix A examples come out character for character, and
  every numeral that `checks.numerals` finds in a sentence is a stored value
  of that sentence's row.

### T5 — the store, the stamp and the reader

- **The store** lives under `Insights/metainsights/`, in files whose names
  begin `profile_sheets`. The format is your choice within spec §8:
  - one place's sheet can be read without reading any other;
  - no file over 95 MB; if the store is split, the stamp lists every part
    with its SHA-256 and the reader refuses a missing or altered part (the
    WP-D11b discipline);
  - two builds from the same views give byte-identical store files.
- **The stamp** (`profile_sheets_stamp.json`): `candidate_set_id`,
  `source_generated_at`, `view_parquets` (name, SHA-256, bytes — reuse
  `phase5f_decompose.parquet_provenance` or its logic), counts of sheets and
  sentences per level, the file list with hashes, and `generated_at`.
  `generated_at` is the only value allowed to differ between two builds.
- **The builder refuses** to write the real store when the view parquets'
  hashes differ from `decompose_corpus_stamp.json`. A flag for the scale test
  (T7) lifts this, writes elsewhere, and marks that stamp `"synthetic": true`.
- **The reader**, `DiscoverChat/profile_store.py`. Nothing in the service
  imports it in this package. Its contract, which WP-D15 will build on:

  ```
  available() -> bool                 the store is present and passes the checks below
  stamp() -> dict
  get(level, code) -> dict | None     one sheet: the place, its parents, the main rows, the lists
  sentences(level, code) -> list      in the hand-over order below; each item:
                                      {"id", "row", "sentence", "note"}
  sentence(id) -> dict | None         one sentence by its id
  ```

  It refuses a store whose `candidate_set_id` differs from the findings
  corpus's, and any store marked synthetic. It holds no sheet in memory until
  asked for it.
- **Hand-over order** of `sentences()`: A1–A7, then B, C (focus areas, then
  themes), D, then E1–E5, F1–F2, G1, G3, H, I, J. A row with no sentence is
  skipped.
- **Notes.** Two fixed notes are stored once and referred to from their
  rows, never pasted into a sentence: on F1 *"An activity with no approval on
  file is not known to be unapproved; the record may simply be missing."*; on
  H3–H5 and I1–I3 *"Reported by the Gram Panchayat itself and not checked."*
- **Done when:** `get("gp", "119936")` returns the Kalimela sheet; an unknown
  code returns `None`; a store with an altered byte is refused.

### T6 — the checks

All seven checks of spec §9. The builder's `--check` runs all of them. Every
check that can run without the view parquets also goes into
`DiscoverChat/gates.py`, so the one gate command covers it:

| Check (spec §9) | Builder `--check` | Gate |
|---|---|---|
| 1 Equal to the views | yes | no (needs the parquets) |
| 2 The parts add up, level to level | yes | yes |
| 3 Shares are re-derived, not averaged | yes | yes |
| 4 Equal to the insights | yes | yes |
| 5 Sentences hold only stored figures | yes | yes |
| 6 Every place has a sheet | yes | no (needs `view4`) |
| 7 The reference figures of spec §13 | yes | yes |
| The store's stamp matches the corpus | yes | yes |

- **Check 4, made concrete.** Take every breakdown record of `view3` whose
  `subspace` is empty or is exactly one pair on a place dimension (Gram
  Panchayat, block or district) and whose measure is one the sheet holds. Its
  `total` must equal the sheet's figure for that place, within the corpus's
  own reconciliation tolerance, and for money its `total_display` must equal
  the sheet's display string (a negative total compared before the direction
  words are applied). Match places by the record's resolved codes, not by
  name — four names are both a Gram Panchayat and a block. **Report how many
  records were compared at each level. Zero compared is a failure of the
  check, not a pass.** Also assert that the whole's A7 equals record
  `d1-00248`.
- **Check 5** is the same proof as `layout-formatter-parity`: regenerate each
  sentence's figures from the row's stored values through the same formatter
  and compare the numerals.
- **Tests** in `DiscoverChat/tests/test_profile_sheets.py`: the standing
  phrase (1st to 23rd, 11th–13th, ties, the nearer end, the equal-ranks case,
  the quarter cut, fewer than 5 peers); the zero and blank cases of Appendix
  A; singular and plural; the id rules; every Appendix A example.
- **Done when:** `--check` is green; the gate shows the baseline's results
  plus the new checks green, and nothing that was green is red; the suite is
  green.

### T7 — the scale test (required; a missed target is a STOP for the PM)

- **Do:** a script in `handoffs/WPD14_scale/` that turns the sample views into
  a made-up state and writes them **outside the repo** (for example
  `C:\dev\odisha-d14-scale\`). Nothing it writes is committed.
  - 340 copies of each sample Gram Panchayat → 6,800, with new codes and
    names (`Kalimela 017`).
  - Assigned in a fixed order to 314 blocks and 30 districts, with new codes
    and names.
  - Every money column of copy `k` multiplied by `0.5 + (k mod 101) / 100`,
    the same factor in every view, so `view1` and `view3` still agree. Counts
    are left as they are, so the test also exercises large ties.
  - Only the views the builder reads need making.
- **Measure, and report the method for each:**

  | Measure | Target |
  |---|---|
  | Build time, parquets to finished store, on the development machine | under 10 minutes |
  | Store size on disk | under 300 MB |
  | Largest single file | under 95 MB |
  | One lookup by level and code, fresh process, median and 95th percentile over 1,000 random keys | under 50 ms |
  | Memory added by opening the store | under 100 MB |
  | Sheets written | 6,800 + 314 + 30 + 1 |

- Run checks 2, 3, 5 and 6 on the made-up store.
- **Done when:** the table is filled with measured values. If a target is
  missed, deliver what you have, report the measurement and STOP. Do not
  change the design to pass it without the PM.

### T8 — report

`handoffs/WPD14_REPORT.md`:

- **§0 Status** — each gate item below, PASS / FAIL / PARTIAL, one line of
  evidence.
- **§1 What was built** — commands, runtime, the store format chosen and why.
- **§2 Reference figures** — spec §13, expected against actual, every row.
- **§3 Sentences** — every sentence of three sheets printed in full: Kalimela
  Gram Panchayat, Kalimela block, the whole. **List every sentence shape you
  used that is not in Appendix A.** The PM shows these to the operator.
- **§4 Checks** — the output of `--check`, the gate and the suite, baseline
  against final; for check 4, the number of records compared per level.
- **§5 Scale test** — the T7 table, with the method for each measure.
- **§6 Determinism** — two builds, file hashes side by side.
- **§7 Decision journal** — decision / options / choice / cost of reversing.
- **§8 Data oddities** — anything beyond spec §12. Logged, never fixed.
- **§9 Where the spec or this brief was wrong** — proposed changes; you do
  not edit the spec.
- **§10 Files** touched / not touched / not yours; what the PM should replay.

Commit per task on the current branch (`WP-D14 T<n>: …`), as in WP-D12 and
WP-D13. Do not push.

---

## Files in scope (you may write ONLY these)

```
Insights/src/phase5g_profile_sheets.py       new — the builder and its --check
Insights/metainsights/profile_sheets*        new — the store and its stamp
DiscoverChat/profile_store.py                new — the reader
DiscoverChat/config.py                       the store's path constants only
DiscoverChat/gates.py                        the new check lines only
DiscoverChat/tests/test_profile_sheets.py    new
handoffs/WPD14_REPORT.md                     new
handoffs/WPD14_scale/**                      new — the script and its measurements, no data
```

**DO NOT TOUCH:** `Data/**` (and do not read it — R2); `Insights/domain_pack_prdw/**`
and `build_views.py` (no change to the views); every existing file in
`Insights/metainsights/` (byte-identical before and after — prove it in §10);
every other file in `Insights/src/` (import from them);
`DiscoverChat/main.py`, `assemble.py`, `writer.py`, `judge.py`, `checks.py`,
`layout.py`, `render.py`, `classifier.py`, `retrieval.py`, `corpus.py`,
`glossary.py`, `context_brief.py`; `DiscoverChat/experiments/**`; `Ask/**`;
`frontend/**`; `deploy/**`; every `.env`; `handoffs/PROJECT_PLAN.md`;
`handoffs/PROFILE_SHEET_SPEC.md`; `Insights/DISCOVER_VIEW_MAPPING.md`.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/PROFILE_SHEET_SPEC.md` | The spec. §5 is every figure, §13 is what you must reproduce. |
| `Insights/DISCOVER_VIEW_MAPPING.md` §3, §5, §6, §8, §12 | The money bases, the year rules, the statewide switch, "log, never fix", `view4` |
| `Insights/domain_pack_prdw/views/view1_activity_lifecycle.sql`, `view3_gp_performance.sql`, `view4_gp_profile.sql` | What each column means; you read their output, you do not change them |
| `Insights/src/phase5f_decompose.py` (header, `parquet_provenance`, `write_outputs`) | The pattern to copy: stamp, view hashes, determinism |
| `Insights/src/phase5b_report.py` (`format_measure`), `DiscoverChat/glossary.py` (`signed_money`, `signed_above`) | The formatters. Import them; do not restate them. |
| `DiscoverChat/config.py`, `corpus.py` (`_read`, `load`) | How a store is located, stamped and refused |
| `DiscoverChat/checks.py` (`numerals`, `_NUM`, `_TAG`) | The rules your sentences and ids must satisfy |
| `DiscoverChat/gates.py` (`layout-formatter-parity`) | The form of check 5 |
| `handoffs/WPD11b_REPORT.md` | Split files and their hashes |

## Escalation

- **STOP and end the run:** a precondition fails; the view hashes differ from
  the corpus stamp; a column the spec names is not in the view; a Gram
  Panchayat maps to two blocks, or a block to two districts; a spec §13 figure
  cannot be reproduced; check 4 finds a sheet and an insight that disagree; a
  scale target is missed; two names give one id.
- **Decide and document** (report §7): the store format; the tool (DuckDB or
  pandas); where a helper lives; the wording of a sentence shape Appendix A
  does not cover (and list it in §3).
- **Never:** change a view or read `Data/`; work out a figure in the reader;
  average a rate; fix or drop a data oddity; add a mark, a threshold or a
  note the spec does not hold; call a model; wire the reader into the
  service; edit a prompt; push.

## Gate — green as one set

1. Spec §13 reproduced exactly (three places).
2. The Appendix A examples reproduced character for character.
3. `--check` green on all seven checks; check 4 compared more than zero
   records at every level.
4. `python -m DiscoverChat.gates`: the baseline plus the new checks green,
   nothing that was green now red. `python -m pytest DiscoverChat/tests -q`
   green.
5. Two builds give byte-identical store files.
6. Every existing file in `Insights/metainsights/` unchanged.
7. The scale table filled in, every target met.

Gate holder: the PM replays the build, `--check` and the gate, then shows the
operator the three printed sheets of report §3.

## Not this package — notes for WP-D15 (serve) and WP-D16 (page)

Recorded so they are not lost. Do not build them here.

- Matching a question's place name to a sheet. R4: the block by default,
  unless the question clearly says Gram Panchayat; say which was answered and
  let the officer switch.
- Handing the sheet to the writer in the fixed order, with every sheet
  sentence optional (the every-record-cited rule must not apply to them).
- The number check, for sheet sentences: (a) the year-dash false alarm
  (`2023–24` against the stored `2023-2024`, D74) will fire on the by-year
  lines; (b) today's direction step covers breakdown records only — it needs
  "below plan / above plan" for A7 and the standing words (highest / lowest,
  most / fewest); (c) numbers written as words ("a fifth") are not checked —
  a known limit.
- Sentences that begin "Its…" or "It…" need the place's name beside them when
  shown alone (a hover card, the fall-back list, two places in one answer).
- How many mined insights accompany a sheet on a place question.
- The trial: the same question three times, and how far the chosen facts
  differ (R5).
- The page: the six headline figures, the by-year list and the largest focus
  areas as cards and tables drawn by code — a PM recommendation the operator
  has not yet ruled on.

---

## Appendix A — the sentence patterns

The operator approved the wording of the patterns marked ✔ on 2026-11-24 (R6).
The others are PM-drafted in the same shape. Use them as written.

**General rules**

- `{Place}` is the name and the level word: `Kalimela Gram Panchayat`,
  `Kalimela block`, `Malkangiri district`. For the whole it is the setting of
  Fact 9: `The whole sample` at the start of a sentence, `the whole sample`
  inside one.
- `{standing}` — counts use most / fewest; money and shares use highest /
  lowest.
  - Up to 50 peers: `the most of 20 Gram Panchayats`, `the 2nd highest of 20
    Gram Panchayats`, `the 4th lowest of 16 blocks`. Tied: `the joint 2nd
    highest of …`, `the joint most of …`.
  - When the peer group is a block or a district, name it: `of the 22 Gram
    Panchayats in Kalimela block`.
  - More than 50 peers: `in the lowest quarter of the 6,800 Gram Panchayats in
    the state` (quarters: lowest, lower-middle, upper-middle, highest).
  - Statewide, a Gram Panchayat sentence gives both: `the 5th lowest of the 22
    Gram Panchayats in Kalimela block and in the lowest quarter of the 6,800
    in the state`.
- "The middle value" is that of the first peer group named in the sentence.
- **No peer group of at least 5** (and always for the whole): leave out the
  standing clause and the middle-value sentence. `Kalimela Gram Panchayat has
  852 planned activities.`
- **A zero value takes the zero form** below, which carries no standing.
- **One of something** agrees: `1 work is marked completed`, `1 activity has`,
  `1 approval`, `1 block and 1 Gram Panchayat`.
- A row whose pattern is not met (a blank share, an H row that is zero) has no
  sentence.

**The main row**

| Row | Pattern | Zero or blank form |
|---|---|---|
| A1 ✔ | {Place} has {A1} planned activities, the {standing}. The middle value for these {n} is {median}. | {Place} has no planned activities in the data. |
| A2 ✔ | {A2} of them ({share}) have no cost attached. | All of them have a cost attached. (None when A1 is zero.) |
| A3 ✔ | Its planned cost is {A3}, the {standing}. The middle value is {median}. | It has no planned cost on record. |
| A4 | {A4} has been sanctioned for the activities with an approval on file, the {standing}. The middle value is {median}. | Nothing has been sanctioned on record. |
| A5 ✔ | It spent {A5} on planned activities, the {standing}. The middle value is {median}. | The data shows no spending on its planned activities. |
| A6 ✔ | Spending is {A6} of the planned cost, the {standing}. The middle value is {median}. | No sentence when A3 or A5 is zero. |
| A7 ✔ | Spending is {amount} below plan. / Spending is {amount} above plan. | No sentence when A7 is zero. |
| E1 | {E1} works are marked ongoing, the {standing}. The middle value is {median}. | No works are marked ongoing. |
| E2 ✔ | {E2} works are marked completed, out of {the whole's E2} in {the whole}. (On the whole's own sheet: {E2} works are marked completed.) | No works are marked completed. |
| E3 | {E3} works are marked abandoned, with {money} planned on them. {k} of them were planned in {year}. | No works are marked abandoned. |
| E4 | {E4} activities have photo evidence ({uploads} uploads), the {standing}. The middle value is {median}. | No activities have photo evidence. |
| E5 ✔ | {count} works planned in {cut-off year} or earlier are still marked ongoing. {spent} of their {planned} planned cost has been spent ({share}). | No sentence when the count is zero. The second sentence is dropped when their planned cost is zero. |
| F1 ✔ | {F1} of the {A1} activities ({share}) have an administrative approval on file, the {standing}. | None of the {A1} activities has an administrative approval on file. |
| F2 | {F2} activities have a technical approval on file. | No activities have a technical approval on file. |
| G1 + G2 ✔ | Its cashbook shows {G1} received and {G2} paid out. (One sentence, id `…-G1`, for both rows.) | Its cashbook shows no receipts and no payments. |
| G3 ✔ | {G3} of the payments are linked to a planned activity. The middle value is {median}. | No sentence when G2 is zero. |
| H1 | {H1} activities have an approval cost recorded with no approval record. | No sentence. |
| H2 | {H2} activities have no LSDG theme mapped; their planned cost is {money}. | No sentence. |
| H3 | Its profile reports {toilets} household toilets for {households} households. | Only when toilets exceed households. |
| H4 | Its profile reports {taps} tap connections for {households} households. | Only when connections exceed households. |
| H5 | Its profile reports {population} people in {households} households, which is {ratio} people per household. | Only when the ratio is over 20. |
| I1 | Its profile reports a population of {population} (size band: {gp_size}). | No sentence when not reported. |
| I2 | Its profile reports {households} households. | No sentence when not reported. |
| I3 | Its profile classes it as {social_composition} and as {near a bus stop / far from a bus stop}. | Leave out a part that is "Not reported". |
| I4 | Block: {Place} has {n} Gram Panchayats in the data. District: {Place} has {b} blocks and {n} Gram Panchayats in the data. Whole: {Place} has {d} districts, {b} blocks and {n} Gram Panchayats. | — |

**The lists**

| Line | Pattern | Other forms |
|---|---|---|
| B ✔ | In {year}: {n} activities ({c} with no cost), {planned} planned, {spent} spent, {share} of the plan. | Drop the bracket when none has no cost. Nothing planned: `…, nothing planned, {spent} spent.` Nothing spent: `…, {planned} planned, nothing spent.` No activities: `In {year}: no planned activities.` |
| C ✔ | {Name}: {n} activities, {planned} planned, {spent} spent. | Nothing spent ✔: `{Name}: {n} activities and {planned} planned, with nothing spent.` No planned cost: `{Name}: {n} activities with no planned cost, {spent} spent.` Neither: `{Name}: {n} activities, with no planned cost and nothing spent.` |
| D-plan | Of the planned cost, {tied} is tied grant ({share}) and {untied} is untied grant ({share}). | No sentence when A3 is zero. |
| D-scheme | {Scheme}: {n} approvals, {amount} sanctioned. | The sixth line, when there are more than five: `All other schemes: {n} approvals, {amount} sanctioned.` |
| D-authority | Approvals on file, by who approved: {A} {n}, {B} {n}, {C} {n}, all others {n}. | Fewer names when fewer exist; no "all others" when there are none. No sentence when F1 is zero. |
| J | {Member}: {A1} activities, {A3} planned, {A5} spent, {A6} of the plan. | The same forms as B for nothing planned and nothing spent. |

**Examples to reproduce character for character**

Kalimela Gram Panchayat (`p-gp-119936-…`):

```
A1  Kalimela Gram Panchayat has 852 planned activities, the 2nd most of 20 Gram Panchayats. The middle value for these 20 is 602.5.
A2  392 of them (46.0%) have no cost attached.
A3  Its planned cost is Rs 7.65 crore, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
A4  Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.37 crore.
A5  It spent Rs 1.76 crore on planned activities, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
A6  Spending is 23.0% of the planned cost, the 5th lowest of 20 Gram Panchayats. The middle value is 42.0%.
A7  Spending is Rs 5.90 crore below plan.
B-2020-2021  In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.
B-2023-2024  In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.
C   Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.
C   Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.
D-plan       Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).
DS  XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned.
DS  5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned.
DS  Own Funds: 2 approvals, Rs 2.74 lakh sanctioned.
D-authority  Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2.
E1  154 works are marked ongoing, the 2nd most of 20 Gram Panchayats. The middle value is 95.5.
E2  13 works are marked completed, out of 17 in the whole sample.
E3  22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.
E4  129 activities have photo evidence (553 uploads), the 2nd most of 20 Gram Panchayats. The middle value is 79.
E5  55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).
F1  168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats.
F2  168 activities have a technical approval on file.
G1  Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.
G3  33.3% of the payments are linked to a planned activity. The middle value is 42.2%.
H2  49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.
H5  Its profile reports 10,681 people in 200 households, which is 53.4 people per household.
I1  Its profile reports a population of 10,681 (size band: 10,000 and above).
I2  Its profile reports 200 households.
I3  Its profile classes it as ST-majority and as near a bus stop.
```

Kalimela block (`p-block-3843-…`):

```
A1  Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
A3  Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.
A5  It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.
A6  Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.
F1  168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks.
G3  33.3% of the payments are linked to a planned activity. The middle value is 46.5%.
I4  Kalimela block has 1 Gram Panchayat in the data.
J   Kalimela Gram Panchayat: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan.
```

The whole (`p-all-…`):

```
A1  The whole sample has 12,704 planned activities.
A2  7,074 of them (55.7%) have no cost attached.
A3  Its planned cost is Rs 77.31 crore.
A5  It spent Rs 25.35 crore on planned activities.
A6  Spending is 32.8% of the planned cost.
A7  Spending is Rs 51.96 crore below plan.
I4  The whole sample has 9 districts, 16 blocks and 20 Gram Panchayats.
```

If the views give a different string for any line above, do not adjust the
figure to match. Report the difference: either this appendix or the build is
wrong, and the PM needs to know which.

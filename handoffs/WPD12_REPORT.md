# WP-D12 report — Insight report layout: cards, charts and a warning box drawn by code

**For:** the PM and the operator. **Executed:** 2026-11-21, mirrors
`C:\dev\odisha-d12` (service) and `C:\dev\ab-dashboard-odisha` (frontend).
**Brief:** `handoffs/WPD12_report_layout.md` (D62).

## Outcome in one paragraph

Built and green. The service now sends an optional `layout` field: up to three
cards, up to three small charts and a "Needs checking" list, all made by code
from the records the answer already uses — no model call, no prompt change, and
every figure a stored value through the corpus's own formatter (a whole-corpus
gate check proves it on all 66,779 decompositions). The tab draws them around
the unchanged prose. With the layout absent, `{}` or another version, the
report renders **exactly** as before (tested against a capture of the old
render). On the five live turns the layout took **1.0–5.1 ms** per answer.
Most importantly for ruling 7: **in all 8 answers where the writer fell back to
bare sentences (2 of 5 live, 6 of 24 recorded), the officer still got the
cards, the charts and the warning.** Two things I changed after seeing the
screenshots are listed in §6 for the PM to overrule if wanted.

## 1. Commits (current branch `master`, not pushed)

| Commit | Task |
|---|---|
| `759b099` | T1: the `layout` field, gate check, tests, live payloads (+ the brief and its mock-up, committed unchanged) |
| `40de4b2` | T2: the frontend; plus two service fixes found from the screenshots (§6 items 3 and 4) |
| T3 commit | T3: this report and the screenshots |

Switch to turn it off, no code change: `DISCOVERCHAT_LAYOUT=0` (the field is
then `{}` and the tab renders as before).

## 2. Checks, baseline vs final

| | Baseline (HEAD `05a80ca`) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 35/35 green | **36/36 green** (new: `layout-formatter-parity`) |
| `python -m pytest DiscoverChat/tests -q` | 111 passed, 1 failed | **150 passed, 1 failed** (+39 in `test_layout.py`) |
| `npm test` (vitest) | 110 passed, 8 files | **146 passed, 10 files** (+36) |
| `npm run lint` | 3 errors, 7 warnings | **3 errors, 7 warnings — the same ones** |
| `npm run build` | green | **green** |

- The one pytest failure is the same test in both runs and predates this work:
  `test_citations.py::WriterPromptTests::test_the_prompt_is_the_operators_text`
  (the operator's 2026-09-11 prompt edit). Not touched.
- **Lint is not green, and was not green before.** The 3 errors are
  pre-existing: `src/components/ui/command.tsx`, `src/components/ui/textarea.tsx`
  (empty interfaces) and the `require()` at the bottom of `tailwind.config.ts`.
  I edited `tailwind.config.ts` (colours only), so that error's line number
  moved from 109 to 125; nothing else about it changed. Logged, not fixed — the
  first two files are outside this package, and the third would mean changing
  how the config loads its plugin.
- No existing frontend test assertion had to change.

## 3. The payload (final shape)

```json
"layout": {
  "version": 1,
  "cards": [
    {"id": "d4-02525", "url": "/record/d4-02525", "kind": "total",
     "value": "Rs 2.17 crore", "label": "spending", "scope": "district Cuttack"},
    {"id": "1-…", "url": "/record/1-…", "kind": "pattern",
     "text": "<the pattern's display sentence, verbatim>", "scope": "…"}
  ],
  "warnings": [
    {"id": "d1-…", "url": "/record/d1-…", "rows": "923",
     "missing": "sanctioning authority", "measure": "spending measured against plan",
     "share": "94.1%", "amount": "Rs 2.99 crore below plan", "scope": "district Cuttack"}
  ],
  "panels": [
    {"kind": "compare", "ids": ["d3-01105", "d1-14417", "…"], "by": "Gram Panchayat",
     "scope": "district Cuttack", "members": ["Govindapur", "Dadhapatna"],
     "rows": [{"id": "d3-01105", "url": "/record/d3-01105",
               "label": "spending measured against plan",
               "total": "Rs 3.18 crore below plan", "direction": "below plan",
               "parts": [{"member": "Govindapur", "fraction": 0.652659, "share": "65.3%",
                          "value": "Rs 2.07 crore", "role": "member"}, {"…": "…"}]}]},
    {"kind": "ranked", "id": "d1-14462", "ids": ["d1-14462"], "url": "/record/d1-14462",
     "label": "untied grant planned", "by": "LSDG theme", "scope": "district Cuttack",
     "total": "Rs 3.69 crore", "direction": null, "shown": 5, "of": 7,
     "bars": [{"member": "Theme 6 - Self-sufficient Infrastructure in Village",
               "fraction": 0.842791, "share": "84.3%", "value": "Rs 3.11 crore",
               "role": "member"}]},
    {"kind": "time", "…": "same keys as ranked; bars in time order"}
  ]
}
```

- Every card, warning, compare row and ranked/time panel carries its own `url`.
- `fraction` is the only number and is used for bar length only.
- Signed figures: a total, a card, a warning amount and a compare row's total
  say the direction in words ("Rs 3.18 crore below plan", via
  `glossary.signed_money`, the WP-D13 helper — no second helper was written; a
  positive figure appends `glossary.signed_above`). Bars and parts carry the
  bare amount, and the panel or row states the direction once (`direction`,
  shown as "all figures below plan"). No "Rs -" reaches any layout string
  (tested over every answer, and over every record's panel in the sweep).
- Lookup, why, a navigate **walk**, and nothing-found return `{}`. A navigate
  turn with no walk falls through to an ordinary search and is answered on the
  retrieve path, so it gets a layout — I read "navigate returns `{}`" as the
  walk.

## 4. Fixtures, and the 15 recorded answers

- **The 15 recorded answers in `answer_compare.json` are stale.** Their ids
  still exist, but in 10 of the 13 tagged texts the figures no longer bind to
  the cited records — the WP-D11b rebuild reassigned the ids. I did not use
  them.
- **Offline tests use the 24 answers recorded by the WP-D13 trial today**
  (`experiments/direction_trial_results.json`, 12 questions × 2 arms, current
  corpus; 103 of 104 tagged texts bind cleanly). Read-only.
- **Live turns** (`/chat` through the app's own routes, saved whole as
  `frontend/…/src/lib/discover-layout.fixtures.json`): the brief's five, plus a
  sixth ("Which blocks account for the shortfall?") because none of the five
  had one or two findings, which a screenshot needed. The out-of-scope question
  ("What is the price of onions in Cuttack market?") was routed to Ask by the
  classifier, so it is a decline with `{}`, not a "nothing found".
- After the two T2 fixes, the `layout` field of each saved payload was
  recomputed offline with the final `layout.py` (it depends only on the recorded
  findings and prose — no model call). Only the intended changes appeared (two
  charts lost their zero bars); the other layouts came out byte-identical to
  the live ones.
- `discover-layout-baseline.fixtures.json` holds the text the **old**
  component rendered for each payload, captured from the committed component
  before any frontend change. The "no layout renders as before" test compares
  against it.

## 5. Build time

Live, measured around `layout.build` inside the real `/chat` call:

| Turn | Findings | Layout build |
|---|---|---|
| Cuttack | 13 | 4.9 ms (first call; includes warming the label cache) |
| Chikilli | 14 | 5.1 ms |
| Kalimela | 11 | 2.3 ms |
| Mostly patterns | 9 | 1.0 ms |
| Small answer | 1 | 1.2 ms |

On the 24 recorded answers: 0.1–5.1 ms. The whole-corpus gate check takes
about 1 s.

## 6. Decisions I made — please overrule any you disagree with

1. **One card per measure compares the measure name AND its officer words.**
   With the name alone, view1 `total_cost` and view3 `planned_cost` both
   become a card reading "planned cost". The brief's literal rule is still
   applied; this adds the phrase.
2. **Time charts with more than 12 periods show the 12 largest, put into time
   order**, captioned "the 12 largest of 72, in time order". The brief said
   "max 12" without saying which. Affects 846 month/quarter records. The
   alternative (the latest 12) could leave out the month the prose talks about.
3. **Ranked charts leave out members holding exactly nothing** (found in the
   screenshots: Cuttack's tied-grant chart showed "Administrative & Technical
   Support Rs 0 · 0.0%" among "the 5 largest of 25"). 12,292 ranked records
   would otherwise draw at least one zero bar. `of` still counts every member,
   so the caption stays true ("the 3 largest of 25"). Zero **years** stay on
   time charts — a year with nothing in it is information. When only the "Not
   recorded" member holds anything (719 records), the chart is that one grey
   bar and no "largest" caption.
4. **The scope line is not passed through the glossary again.** My first
   version did, and it turned "LSDG theme Theme 4" into "LSDG LSDG theme
   Theme 4" on 7 of the corpus's 300 distinct scopes. Scope now gets only the
   size-band unit rule (`display_band_labels`, WP-D11b ruling 3).
5. **Warnings on mixed-sign records are kept, as the brief says — but look at
   them.** For a mixed record the null member's share is a share of all the
   money moving both ways, not of the net, so "They account for 45% of
   spending measured against plan" is loose. Only 29 corpus records are
   affected. Cards and charts already skip mixed records. I'd suggest skipping
   them in warnings too; I did not, because the brief did not.
6. **Row counts use the corpus's own grouping** (`_num`, Indian style), so
   they match the stored sentence exactly. Identical to a thousands separator
   below 1,00,000, which covers every row count in the sample.
7. **The warning card in the top row appears only when there are other cards**
   (cards need at least 3 findings). The "Needs checking" box always appears
   when there is a warning.
8. **Layout of panels:** one or three panels under a paragraph — the odd last
   one takes the full row; two sit side by side from 640px.
9. **Compare charts keep their two colours even for a "Not recorded" part.**
   Grey with white or ink text fails the 4.5:1 contrast rule. The legend names
   the member.
10. **Titles:** compare panels read "Split by {by}"; ranked and time panels
    read "{label} by {by}", with "Total {total}" under it.

## 7. Found, not fixed (outside this package's files)

- **DM Sans is not loaded upright.** `src/index.css` loads DM Sans in italic
  400/500 only, so the brief's "big value in DM Sans" would render italic.
  The value uses the app's normal sans (Inter) at 28px semibold instead.
  `index.css` is not in the files in scope.
- **"LSDG LSDG theme" in display sentences.** The glossary re-translates
  decomposition sentences that were already built in officer words, so some
  display sentences read "across 7 LSDG LSDG theme values" (visible in the
  Kalimela fallback screenshot and in hover cards). `glossary.py` is outside
  this package.
- **Long underlined phrases break the line early.** A claim span (a cited
  phrase with no figure) is one button, so a long one jumps whole to the next
  line ("…across 6 / fiscal years; this may reflect…"). Pre-existing:
  `0_chikilli_before_wpd12.png` shows the same breaks with the old component.
- The judge's picks decide whether Cuttack gets a warning: today's recorded
  Cuttack answer had none (no picked record has a "not recorded" member,
  though 35 Cuttack records do); the live turn did. Nothing for the layout to
  do — noted because the brief's T1 done-condition depends on it.

## 8. Member display labels

Member names go through `glossary.render(name, view)` — the same path every
display sentence goes through — which is what adds "people" to size bands
("Under 2,500 people") and, for example, turns "Unmapped theme" into
"Unmapped LSDG theme", matching the prose. `(not recorded)` shows as "Not
recorded". Leading and trailing spaces are trimmed (one stored theme name ends
in a space). Measured over all 479 distinct member labels in the corpus (by
view and breakdown): only the four size bands and "Unmapped theme" change. The function's output is
remembered per name, because the glossary rebuilds its pattern on every call
(that alone took the whole-corpus check from 48 s to 1 s).

## 9. The weak-writer table (ruling 7)

Writer for every row: `gpt-5.6-sol` (judge `gpt-5.6-sol`). "Failed check(s)"
are the checks that counted against each attempt. "Cards / panels / warnings"
is what the layout produced.

| Turn | Findings (decomp. / patterns) | Attempts | Failed check(s) | Fell back | Paragraphs | Cards / panels (kinds) / warnings |
|---|---|---|---|---|---|---|
| live: What should I know about Cuttack? | 13 (12 / 1) | 1 | none | no | 3 | 3 / 3 (compare, ranked, ranked) / 1 |
| live: How is Chikilli doing? | 14 (10 / 4) | 1 | none | no | 3 | 3 / 3 (ranked, time, ranked) / 0 |
| live: What should I know about Kalimela? | 11 (11 / 0) | 2 | att 1: 3_causal; att 2: 3_causal | **yes** | bare sentences | 3 / 3 (compare, time, ranked) / 1 |
| live: Which places are behaving differently from the rest? | 9 (0 / 9) | 1 | none | no | 3 | 2 / 0 / 0 |
| live: What is the price of onions in Cuttack market? | 0 (routed to Ask) | — | — | — | — | `{}` |
| live: Which blocks account for the shortfall? | 1 (1 / 0) | 2 | att 1: 3_causal; att 2: 3_causal | **yes** | bare sentences | 0 / 1 (ranked) / 0 |
| recorded (log) 1: Is spending on track? | 5 (4 / 1) | 1 | none | no | 3 | 1 / 3 (ranked ×3) / 0 |
| recorded (log) 2: What makes up the underspend? | 6 (6 / 0) | 2 | att 1: 3_causal; att 2: 3_causal | **yes** | bare sentences | 1 / 3 (ranked ×3) / 1 |
| recorded (log) 3: What should I raise at the next review meeting? | 8 (7 / 1) | 2 | att 1: 3_causal; att 2: 2_numerals_cited, 3_causal | **yes** | bare sentences | 2 / 3 (ranked ×3) / 1 |
| recorded (log) 4: Where does the gap sit? | 3 (3 / 0) | 2 | att 1: 3_causal; att 2: 3_causal | **yes** | bare sentences | 1 / 3 (ranked ×3) / 0 |
| recorded (log) 5: Which blocks account for the shortfall? | 1 (1 / 0) | 1 | none | no | 1 | 0 / 1 (ranked) / 0 |
| recorded (log) 6: Which places are behaving differently from the rest? | 11 (1 / 10) | 1 | none | no | 3 | 2 / 1 (ranked) / 0 |
| recorded (log) 7: Who is driving the shortfall? | 3 (0 / 3) | 2 | att 1: 3_causal | no | 1 | 1 / 0 / 0 |
| recorded (log) 8: Where is money planned but not spent? | 12 (11 / 1) | 1 | none | no | 3 | 1 / 3 (ranked ×3) / 0 |
| recorded (log) 9: Anything worth my attention this quarter? | 8 (5 / 3) | 2 | att 1: 3_causal | no | 3 | 3 / 3 (ranked ×3) / 1 |
| recorded (log) 10: How is Barpali block doing? | 8 (8 / 0) | 2 | att 1: 3_causal | no | 3 | 3 / 2 (compare, ranked) / 0 |
| recorded (log) 11: Anything I should be looking at in Ganjam? | 7 (6 / 1) | 2 | att 1: 3_causal | no | 4 | 3 / 3 (ranked ×3) / 0 |
| recorded (log) 12: What should I know about Cuttack? | 13 (13 / 0) | 1 | none | no | 3 | 3 / 3 (compare, ranked, time) / 0 |
| recorded (block) 1: Is spending on track? | 5 (4 / 1) | 2 | att 1: 5_direction | no | 4 | 1 / 3 (ranked ×3) / 0 |
| recorded (block) 2: What makes up the underspend? | 6 (6 / 0) | 2 | att 1: 3_causal | no | 4 | 1 / 3 (ranked ×3) / 1 |
| recorded (block) 3: What should I raise at the next review meeting? | 8 (7 / 1) | 2 | att 1: 3_causal, 5_direction | no | 4 | 2 / 3 (ranked ×3) / 1 |
| recorded (block) 4: Where does the gap sit? | 3 (3 / 0) | 2 | att 1: 3_causal; att 2: 5_direction | **yes** | bare sentences | 1 / 3 (ranked ×3) / 0 |
| recorded (block) 5: Which blocks account for the shortfall? | 1 (1 / 0) | 2 | att 1: 3_causal | no | 1 | 0 / 1 (ranked) / 0 |
| recorded (block) 6: Which places are behaving differently from the rest? | 11 (1 / 10) | 1 | none | no | 3 | 2 / 1 (ranked) / 0 |
| recorded (block) 7: Who is driving the shortfall? | 3 (0 / 3) | 1 | none | no | 1 | 1 / 0 / 0 |
| recorded (block) 8: Where is money planned but not spent? | 12 (11 / 1) | 2 | att 1: 5_direction | no | 5 | 1 / 3 (ranked ×3) / 0 |
| recorded (block) 9: Anything worth my attention this quarter? | 8 (5 / 3) | 2 | att 1: 3_causal, 5_direction | no | 3 | 3 / 3 (ranked ×3) / 1 |
| recorded (block) 10: How is Barpali block doing? | 8 (8 / 0) | 1 | none | no | 3 | 3 / 2 (compare, ranked) / 0 |
| recorded (block) 11: Anything I should be looking at in Ganjam? | 7 (6 / 1) | 2 | att 1: 4_all_findings_cited; att 2: 5_direction | **yes** | bare sentences | 3 / 3 (ranked ×3) / 0 |
| recorded (block) 12: What should I know about Cuttack? | 13 (13 / 0) | 2 | att 1: 3_causal; att 2: 3_causal | **yes** | bare sentences | 3 / 3 (compare, ranked, time) / 0 |

("log" and "block" are the WP-D13 trial's two direction-check settings; the
service now runs `log`. In the recorded rows the layout was built offline from
the recorded findings and prose.)

**What this says about how much the layout loses to the writer:**

- **Fall-backs: 8 of 29 answers with findings (28%)** — 2 of 5 live, 6 of 24
  recorded. The causal scan (`3_causal`) is in 7 of the 8, matching WP-D13.
  Every one of the 8 still got its full layout: cards wherever there were 3+
  findings, a chart wherever a record was chartable, and its warning.
- **Cards and warnings do not depend on the prose at all.** Over the 21
  answers that kept their narrative, building the layout with the prose and
  without it gives identical cards and warnings in 21 of 21 (citation step 4
  already forces every finding to be cited, so "Cited" is always everything).
- **Charts do depend on it, a little.** Which three charts are shown, and in
  what order, changed in 12 of those 21 when the prose was removed: the prose's
  figures decide the weights; without them the judge's order decides. On a
  fall-back the charts also sit after the text rather than next to the
  paragraph that discusses them.
- **Writers do write a single paragraph sometimes** (4 recorded rows, all with
  1–3 findings); any chart then sits under that paragraph. The layout itself
  does not depend on paragraphs: a test joins every multi-paragraph answer into
  one paragraph and gets an identical layout.

## 10. Screenshots (`handoffs/WPD12_shots/`)

The real app's Discover tab (Vite dev server, Chromium via Playwright), with
`/chat` answered from the saved payloads so the pictures show exactly the tested
answers.

| File | What |
|---|---|
| `1_cuttack_desktop.png` | Cuttack at desktop width: 3 cards + warning card, compare chart, two ranked charts, Needs-checking box, Copy |
| `2_cuttack_390.png` | Cuttack at 390px |
| `3_mostly_patterns.png` | Mostly-patterns answer: pattern cards, no charts |
| `4_small_answer_one_finding.png` | One finding (fell back): one ranked chart |
| `5_no_layout_out_of_scope.png` | An answer with no layout (`{}`, the Ask decline) |
| `5b_no_layout_cuttack_switch_off.png` | Cuttack with the layout removed — what `DISCOVERCHAT_LAYOUT=0` gives |
| `6_hover_card_open.png` | The hover card open on a figure; only the hovered figure is underlined |
| `7_kalimela_fallback.png` | Kalimela, where the writer fell back: cards, charts after the last block, warning |
| `8_chikilli_desktop.png` | Chikilli: charts under the paragraphs that cite them, a time chart |
| `0_chikilli_before_wpd12.png` | The same Chikilli answer with the pre-WP-D12 component, for comparison |

No horizontal scroll at 360px on any of the six payloads (checked in the
browser: page overflow 0 px, no element past the right edge).

## 11. Files

**Touched (all within the brief's list):**
`DiscoverChat/layout.py` (new), `assemble.py` (the `Answer.layout` field and
the one call), `main.py` (the `AskResponse.layout` field), `config.py` (the
switch, the caps, the settings dump), `gates.py` (the import and one check
line), `tests/test_layout.py` (new);
`frontend/ab-dashboard-main/tailwind.config.ts` (12 `report-*` colours added,
none changed), `src/services/discover-api.ts` (types),
`src/lib/discover-answer-layout.ts` (+ test; placement helper),
`src/lib/discover-layout.fixtures.json`,
`src/lib/discover-layout-baseline.fixtures.json`,
`src/components/insights/InsightReport.tsx`, `CitationSpan.tsx` (colours and
the underline rule), `ReportCards.tsx`, `ReportPanel.tsx`,
`ReportWarnings.tsx`, `ReportFooter.tsx`, `ReportRecordLink.tsx`,
`ReportLayout.test.tsx` (new); `handoffs/WPD12_REPORT.md`,
`handoffs/WPD12_shots/`. The brief and its mock-up were committed unchanged
in T1.

**Not touched:** `writer.py`, `judge.py`, `verifier.py`, `context_brief.py`,
`checks.py`, `render.py`, `classifier.py`, `retrieval.py`, `glossary.py`,
`Insights/**` (no corpus rebuild), `AnomaliesView.tsx` and every component
outside `insights/`, every existing colour value, `src/index.css`, `Ask/**`,
`deploy/**`, every `.env`, `handoffs/PROJECT_PLAN.md`, the mock-up's content.
`experiments/direction_trial_results.json` was read, not written.

**Not mine, left as found:** `Ask/bench/bench.py` and the `Ask/bench/*` result
files, `prdw-ask-directions.html`, `prdw-frontend-directions.html`, and the
uncommitted edits to `handoffs/PROJECT_PLAN.md` and
`handoffs/WPD13_report_fixes.md`.

## 12. To see it running

Nothing was pushed and Railway was not touched. Locally: restart the
DiscoverChat service so it serves `layout`, and copy the frontend `src/` and
`tailwind.config.ts` into whichever mirror the dev server runs from (the
operator's `:8080` server runs from `C:\dev\ab-dashboard-main`, which I did not
update). A Tailwind config change needs the dev server restarted.

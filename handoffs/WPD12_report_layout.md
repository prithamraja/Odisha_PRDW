# WP-D12 brief — Insight report layout: cards, charts and a warning box drawn by code

**Workstream:** Discover (service leg + frontend leg, one agent, in that
order). **Nature: BUILD, gated.** **Authored:** PM, 2026-11-20. **Decision
number for the rulings:** **D62** (block D60–D69). **For:** the
operator-controlled implementation agent.

Today the Insight report is one block of prose with about forty underlined
figures (`frontend/ab-dashboard-main/src/components/insights/InsightReport.tsx`).
Nothing stands out and every comparison is a sentence. This package adds a
visual layer **around the same prose**: up to three insight cards at the top,
small charts under the paragraphs that cite them, and a "Needs checking" box
for missing records.

**The one principle: the model chooses and arranges; code draws.** Every
card, chart and warning is built by deterministic code from the stored
records the answer already uses. No model call is added, no prompt changes,
and no figure appears that a stored record does not hold.

---

## Operator rulings this brief encodes (2026-11-20, D62)

1. **Code-only first.** The writer, the judge, the verifier and
   `context_brief.py` are not touched. The prose an officer reads is byte for
   byte what the service produces today. A "short answer" at the top and
   section headlines that state the finding both need the writer and are
   **deferred to a later package** on a separate ruling. Do not approximate
   them in code (no generated headings, no summary sentence).
2. **Top cards are the top three insights after the judge.** Take the
   judge-selected findings in the service's own order, skip near-repeats
   (one card per measure), skip anything the prose does not cite. A separate
   warning card appears when a "not recorded" share is large.
3. **Charts come only from breakdown (decomposition) records.** A mined
   pattern is a sentence and stays a sentence.
4. **No follow-up question chips.**
5. **New colours apply to the Insight report only.** Ink `#243447`, Cyan
   `#0E7490`, Cyan deep `#155E75`, and lighter shades of them. The rest of
   the app (Ask, the feed page around the report, every shared token value)
   keeps today's ivory and teal.
6. **The source underline shows on hover or focus**, not on every figure at
   rest (touch devices keep it visible — see T2.5).
7. **Design around mid-size models.** The prose is written by a mid-size
   model and will stay that way. So the layout asks the model for nothing,
   and must not depend on the model doing anything well: it has to hold up
   when the writer writes one long paragraph, or fails its checks (a dropped
   finding, an untagged figure) and falls back to bare sentences. That is why the layout is
   built on the fallback path too, why every item carries its own record
   link, and why T3 measures how often each of those cases happens.

**PM design choices (not operator rulings — say so in the report if you
disagree, do not silently change them):**

- The layout is computed **in the service** and sent as one optional
  `layout` field. The frontend formats no number and decides no ranking.
- Thresholds and caps in §T1.2 (`0.30`, three cards, three panels, five
  bars, five rows).
- A **Copy** button is in scope. **Download** and "Show the N rows" (both in
  the mock-up) are **out**: each warning links to its record view instead.

**Reference mock-up:** <https://claude.ai/artifact/AWtULLTCDsQycca9mGaWVv>
(private to the operator; frame "Proposed"). Its source is saved at
`handoffs/WPD12_mockup/proposed.dc.html` — the inline styles there are the
spec for spacing, sizes and colours. Its **text is illustrative**. These
parts of the mock-up are NOT in this package: "The short answer" block, the
numbered section headings, the grants table, "Show the 923 rows", Download,
and the "2 sampled Gram Panchayats" caption. Where the mock-up and this brief
disagree, the brief wins.

---

## What exists (verified 2026-11-20)

| Fact | Where |
|---|---|
| An answer's findings are the judge's picks **in retrieval-score order**, capped at `ANSWER_CAP` (20) | `DiscoverChat/assemble.py` `_retrieve`, `answer` |
| The consolidated prose carries `[id]` tags; `checks.cited_ids` lists them; `checks.bind_numerals` binds each numeral to a record | `DiscoverChat/checks.py` |
| `/chat` returns `answer`, `answer_tagged`, `citations`, `answer_html`; the last three are empty when the narrative fell back to bare sentences | `DiscoverChat/main.py`, `assemble.py` |
| A decomposition record stores `measure`, `measure_phrase`, `measure_kind`, `dimension`, `dimension_phrase`, `dimension_is_temporal`, `subspace`, `subspace_phrase`, `total`, `total_display`, `signs`, `shape`, `attribution_member`, `n_members`, `has_null_member`, and columnar `members` {`member`, `value`, `rows`, `share`, `null_index`} — read members through `corpus.members_of` | `Insights/metainsights/decompose_corpus.json.gz` |
| Corpus shape: 66,779 decompositions. `n_members` 2 → 21,614; 3–9 → 35,652; up to 72. `signs`: all_positive 61,078 / all_negative 5,420 / mixed 281. Temporal dimension 2,395 (`fiscal_year`, `month`, `quarter`). `has_null_member` 9,745; the null member's share is bimodal — median 0.006, 3,794 at ≥ 0.30 | measured |
| Members are stored **by size, not in time order** (a `fiscal_year` record lists 2020-2021, 2021-2022, 2025-2026, …) | measured |
| The only signed measures are `overspend_vs_plan` and `overspend_vs_sanction`; their direction words live in `_SIGNED_DIRECTION` | `Insights/src/phase5f_decompose.py` |
| Member values are stored raw (`164.0`, share `0.796117`). The sentence formats them with `format_measure(view, measure, value)` and `f"{share*100:.1f}%"` | `Insights/src/phase5b_report.py:288`, `phase5f_decompose.py` `_fmt`, `_pct` |
| `DiscoverChat/glossary.py` already imports from `phase5f_decompose` and `phase5b_report`, so importing the formatter into the service is the established pattern | `DiscoverChat/glossary.py` |
| A pattern record (4,404 of them) has `sentence`, `measure`, `subspace_phrase`, `pattern_type` and no member values to draw | `Insights/metainsights/retrieval_corpus.json.gz` |
| The report is rendered by `InsightReport.tsx`, hosted in `AnomaliesView.tsx`; the hover card is `CitationSpan.tsx`, portalled to `document.body` | frontend |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] Work from fresh local mirrors, never the Drive path: the repo to
      `C:\dev\odisha-d12`, the frontend to `C:\dev\ab-dashboard-odisha`
      (re-mirror first — mirrors drift; npm breaks on Drive). Copy results
      back to the Drive repo at the end of each task.
- [ ] Service baseline, before any change: `python -m DiscoverChat.gates`
      and `python -m pytest DiscoverChat/tests -q`. Record the counts.
- [ ] Frontend baseline: `npm test`, `npm run lint`, `npm run build`. Record
      the counts. A pre-existing red is logged, not fixed.
- [ ] The tree has unrelated dirty paths under `Ask/bench/` and two
      `prdw-*.html` files at the root. They are not yours; leave them.
- **Done when:** baselines are in the report.

## T1 — service: the `layout` field

New module `DiscoverChat/layout.py`, pure functions, **no model call, no
network, no file write**. Entry point:

```python
def build(findings: list, tagged_text: str, *, run_date: str = "") -> dict
```

Called from `Assembler.answer` on the retrieve path **whenever the answer
shows findings**: the consolidated narrative, and also the bare-sentence
fallback (ruling 7 — a mid-size writer falls back more often, and that is
exactly when the officer most needs the cards and charts). On the fallback
`tagged_text` is empty; pass it as it is. Nothing found, `lookup`, `why` and
`navigate` return `layout == {}`. Add `layout: dict` to `Answer` and to
`AskResponse`.

**Hard invariant:** with layout on or off, `answer`, `answer_tagged`,
`citations`, `answer_html`, `findings` and `stamp` are byte-identical. The
field is additive.

Reversion switch: `DISCOVERCHAT_LAYOUT` (default on) in `config.py`, beside
`CONSOLIDATE`; off returns `{}`. Add the constants below to `config.py` and
to its settings dump.

### T1.1 — shared definitions

- **Order** = the order of `findings` as handed to `build`.
- **Cited** = `checks.cited_ids(tagged_text)` ∩ the ids in `findings`. When
  `tagged_text` is empty (the fallback), every finding is Cited — each one
  is printed verbatim — and every Weight is 0, so Order decides. Note that
  step 4 of `check_citations` already rejects a narrative that leaves a
  selected finding uncited, so on the consolidated path Cited is normally
  every finding as well. Keep the filter anyway: it is what keeps `build`
  correct as a pure function if that step is ever relaxed.
- **Every card, warning and panel row carries `url`** =
  `config.record_url(id)`. The frontend must not need the `citations` map to
  link a layout item, because on the fallback that map is empty.
- **Weight** of a record = the number of `checks.bind_numerals(...)` entries
  whose `matched` is that id. Ties break by Order.
- **Formatting.** Use the corpus's own functions; do not write a second
  formatter. Money and counts: `format_measure(view, measure, value)`.
  Percent: one decimal, exactly as `_pct`. Row counts: thousands separator.
- **Signed measures.** Use `glossary.signed_money(text, measure)`, which
  WP-D13 Fix 1 added (commit `6faea99`; it works on a bare formatted value:
  `signed_money("Rs -51.96 crore", "overspend_vs_plan")` → `"Rs 51.96 crore
  below plan"`). The prose and the charts must get their direction words
  from the same function. If it is somehow not there, STOP and say so; do
  not write a second one. The effect: for a measure in `_SIGNED_DIRECTION`
  show the magnitude and the direction in words:
  `Rs 51.96 crore below plan`, never `Rs -51.96 crore`. Same digits, the
  minus sign replaced by the stored direction word. A positive figure takes
  the "above" word.
- **Member names.** `(not recorded)` displays as `Not recorded`. Every other
  member name goes through whatever display-label path the glossary already
  applies to prose (WP-D11b ruling 3, e.g. "under 2,500 people"). If no
  reusable function exists, show the stored name and log it — do not invent
  labels.
- **No derived figures.** Every figure in the layout is a stored value put
  through the stored formatter. No sums, no remainders, no differences.

### T1.2 — the three parts

**Cards** — only when the answer has **≥ 3 findings**
(`LAYOUT_CARDS_MIN_FINDINGS`). Walk the findings in Order; skip a record
that is not Cited; skip one whose `measure` already has a card; skip a
decomposition whose `signs` is `mixed` (its net total "is not a size" — the
record says so itself); stop at 3 (`LAYOUT_MAX_CARDS`).

- decomposition → `{"id", "kind": "total", "value", "label", "scope"}` with
  `value` = the formatted total, `label` = `measure_phrase`, `scope` =
  `subspace_phrase`.
- pattern → `{"id", "kind": "pattern", "text", "scope"}` with `text` =
  `display_sentence()` verbatim.

**Warnings** — for each Cited decomposition with a null member whose
`abs(share)` ≥ `LAYOUT_NULL_SHARE_WARN` (0.30):
`{"id", "rows", "missing", "measure", "share", "amount", "scope"}` where
`rows` is the null member's row count, `missing` = `dimension_phrase`,
`measure` = `measure_phrase`, `share` and `amount` are the null member's
formatted share and value. One per `dimension` (keep the largest share),
sorted by share descending, at most 3. No minimum-findings rule.

**Panels** — at most 3 (`LAYOUT_MAX_PANELS`); at most 1 when the answer has
fewer than 3 findings. A record is chartable when it is a Cited
decomposition, `signs` is `all_positive` or `all_negative`, and its total is
not zero. Each chartable record goes into exactly one panel:

| Kind | When | Content |
|---|---|---|
| `compare` | `n_members == 2` | Records sharing the same `dimension`, the same two members and the same `subspace` form ONE panel with one row per record (max 5, `LAYOUT_MAX_COMPARE_ROWS`, by Weight). A lone record is a one-row panel. The member order is fixed by the first row and every other row follows it. |
| `time` | `dimension_is_temporal` and `n_members ≥ 3` | Every member, **sorted into time order** (not stored order), max 12. |
| `ranked` | otherwise, `n_members ≥ 3` | The 5 largest members by `abs(value)` (`LAYOUT_MAX_BARS`). The null member is always shown, as an extra bar with `role: "not_recorded"`, even when it is not in the top 5. When members are left out, send `shown` and `of` so the caption can say "the 5 largest of 23" — no "Other" bar. |

Rank panels by Weight (a compare panel's weight is the sum of its rows),
ties by Order, and keep the first 3.

Payload shape — settle the exact keys in code, but it must carry at least:

```json
"layout": {
  "version": 1,
  "cards":    [ {"id": "d1-…", "kind": "total", "value": "1,104 activities", "label": "…", "scope": "…"} ],
  "warnings": [ {"id": "d1-…", "rows": "923", "missing": "…", "measure": "…", "share": "94.1%", "amount": "Rs 2.99 crore below plan", "scope": "…"} ],
  "panels": [
    {"kind": "compare", "ids": ["…"], "by": "<dimension_phrase>", "scope": "…", "members": ["A", "B"],
     "rows": [ {"id": "…", "label": "<measure_phrase>", "total": "…", "direction": null,
                "parts": [ {"fraction": 0.512, "share": "51.2%", "value": "565 activities"}, {…} ]} ]},
    {"kind": "ranked", "ids": ["…"], "label": "<measure_phrase>", "by": "<dimension_phrase>", "scope": "…",
     "total": "…", "direction": "below plan", "shown": 5, "of": 23,
     "bars": [ {"member": "…", "fraction": 0.311, "share": "31.1%", "value": "…", "role": "member"} ]}
  ]
}
```

`fraction` (a number, `abs(share)`) is for bar geometry only. Every string an
officer reads is formatted by the service.

### T1.3 — tests and gate

New `DiscoverChat/tests/test_layout.py`, offline and deterministic:

1. **Formatter parity over the whole corpus.** For every decomposition
   record: the card value's digits equal the digits of `total_display`; and
   where `shape == "concentrated"`, the layout's formatted share and value
   for the top member appear verbatim in the stored sentence (sign wording
   aside). This is the independent proof that the layout's numbers are the
   corpus's numbers.
2. **Whole-corpus sweep.** Building a panel for each of the 66,779 records
   raises nothing and obeys the kind table (no panel for `mixed`; `time`
   strictly ordered; `ranked` ≤ 5 + the null bar; fractions in [0, 1]).
3. **Rules.** Caps; one card per measure; uncited records excluded; cards
   absent under 3 findings; warning threshold on both sides of 0.30; one
   warning per dimension; compare grouping and fixed member order.
4. **Determinism.** Same inputs → identical dict, twice.
5. **Additivity.** Switch on vs off: every other response field identical;
   off → `{}`; nothing-found, `lookup`, `why` and `navigate` → `{}`.
6. **Weak-writer cases (ruling 7).** Empty `tagged_text` with findings → a
   full layout in Order; all tags in a single paragraph → same layout as
   when they are spread out; prose that cites one record out of six → the
   layout holds that one record only and nothing raises (a state the service
   does not emit today — citation step 4 rejects it — tested as a
   pure-function case).

Fixtures need real tagged prose. `DiscoverChat/experiments/answer_compare.json`
holds 15 recorded answers, but the corpus was rebuilt in WP-D11b — check that
their ids still resolve. If they do not, record fresh ones (below) and say so.

Add one line to `gates.py` that runs the parity check (1) so it sits in the
single gate command. `python -m DiscoverChat.gates` and the pytest suite stay
green.

**Live, five turns, payloads saved for T2** (`--live` or direct `/chat`):
"What should I know about Cuttack?", "How is Chikilli doing?", "What should I
know about Kalimela?", one question whose answer is mostly patterns, one
out-of-scope question. Save each full response as a frontend fixture. Report
the layout build time per answer (expect well under 20 ms).

- **Done when:** gate and tests green; the five payloads saved; the Cuttack
  payload has cards, at least one panel and at least one warning.

## T2 — frontend: render the layout

### T2.1 — type and fallback

Add an optional `layout` to `DiscoverChatResponse` in
`src/services/discover-api.ts`. **If `layout` is absent, empty, or its
`version` is not 1, render exactly as today** (new colours aside). An
unknown panel `kind` skips that panel. Never blank the report.

### T2.2 — colours, report only

Add **new named colours** to `tailwind.config.ts`; change no existing value.
Use named colours, not CSS variables scoped to the report — the hover card is
portalled to `document.body` and must wear them too.

| Token | Hex | Use |
|---|---|---|
| `report-ink` | `#243447` | headings, values, the dark button |
| `report-ink-soft` | `#3A4A5C` | body text |
| `report-ink-muted` | `#5B6878` | captions, labels |
| `report-grey` | `#7F8E9D` | the "not recorded" bar |
| `report-axis` | `#B8C4CE` | chart baseline |
| `report-line-strong` | `#C9D3DC` | button borders |
| `report-line` | `#DCE3E9` | card and panel borders |
| `report-cyan` | `#0E7490` | bars, first compare part |
| `report-cyan-deep` | `#155E75` | eyebrow, warning label and icon |
| `report-cyan-light` | `#6DB9CC` | second compare part (ink text inside) |
| `report-cyan-edge` | `#A9D3DD` | warning border |
| `report-cyan-wash` | `#E8F4F7` | warning background |

**The page background does not change** (operator, 2026-11-21): the report
card sits on the same light cream (`ivory`, `#FAF7F2`) as every other page,
and the card itself stays white. No cool-grey ground anywhere.

Apply them to `InsightReport.tsx`, the new components and `CitationSpan.tsx`.
`AnomaliesView.tsx` and everything outside the report keep their tokens.
Text never wears a bar colour. All text meets 4.5:1.

### T2.3 — the parts (new components under `src/components/insights/`)

Order inside the report card: header → cards → prose with panels → warnings
box → footer.

- **Cards row.** Wraps; stacks on a phone. A `total` card: label, big value
  (DM Sans, ~28px, semibold), scope. A `pattern` card: the sentence at body
  size, scope. The **first warning** is repeated as a last, tinted card
  ("Rows needing a check", the row count, "no {missing} recorded"). Each
  card carries an "Open record ↗" link (`recordHref(item.url)` — the item's
  own `url`, never the `citations` map).
- **Panels.** Place each panel under the **first paragraph that cites any of
  its `ids`** (you already have per-paragraph citations from
  `parseCitedAnswer`). Two panels under one paragraph sit side by side from
  640px, stacked below (three under one paragraph: two, then one — a
  mid-size writer often returns a single paragraph). A panel no paragraph
  cites goes after the last block; on the bare-sentence fallback that is
  every panel. Build bars from plain elements as in the mock-up source — no
  chart library:
  - `compare`: a legend naming the two members, then one row per record — a
    28px split bar, 2px gap, 4px corners, the share printed inside each part
    (white on cyan, ink on light cyan). A part too narrow for its label
    prints none.
  - `ranked` / `time`: one row per bar — name, a 16px bar with a rounded end
    growing from a baseline, the value and share at the tip. The "not
    recorded" bar is grey. Caption "the 5 largest of 23" when `of > shown`.
  - Title from `label` and `by`; show `direction` in words when present
    ("all figures below plan"); show `scope` as the caption.
  - Each panel is a `<figure>` with a `<figcaption>`, and every bar or part
    has an accessible name with member, value and share.
- **Needs-checking box.** Tinted, with an alert icon and the label "Needs
  checking" (never colour alone). One numbered line per warning: "{rows} rows
  have no {missing} on file. They account for {share} of {measure}
  ({amount})." Each with "Open record ↗".

### T2.4 — the footer

The run stamp as today, plus a **Copy** button that copies the question and
the plain `answer` to the clipboard and reads "Copied" for two seconds. No
Download. No follow-up chips. The "Put this question to Ask" button stays,
in report ink.

### T2.5 — the source underline

On devices that hover (`@media (hover: hover)`), a bound figure shows its
dotted underline only on hover and on keyboard focus. On touch devices it
stays visible, as today. When the answer has citations, the header caption
gains "point at any number to see its source" ("tap" on touch). The hover
card's behaviour is unchanged.

### T2.6 — tests

Vitest, using the five T1 payloads as fixtures:

1. No `layout` (and `version: 2`) → the rendered text is identical to
   today's render of the same payload.
2. Every card, panel and warning string in a fixture's `layout` is in the
   DOM; nothing numeric is in the DOM that is in neither the prose nor the
   layout.
3. Each panel sits under the first paragraph citing one of its ids.
4. Unknown panel kind → skipped, the rest renders.
5. Copy puts the question and answer on the clipboard.
6. Existing tests stay green. List any assertion you had to change; a colour
   class name is an acceptable reason, a behaviour change is not.

`npm run lint` and `npm run build` green. No horizontal scroll at 360px.

- **Done when:** tests, lint and build green; screenshots (below) taken.

## T3 — report

`handoffs/WPD12_REPORT.md`: baseline vs final counts (service gate, pytest,
vitest, lint, build); the final payload shape; which fixtures were used and
whether the 15 recorded answers still resolved; layout build time; how member
display labels were obtained; anything in the brief you found wrong or could
not do (logged, not worked around); files touched / not touched / not-yours.

**The weak-writer table (ruling 7).** For every live turn and every recorded
answer you used, one row: the writer model; findings selected; attempts (1
or 2) and the check that failed, if any; whether the narrative fell back;
paragraphs; cards, panels and warnings produced. This is what tells the PM how much the layout loses to
the writer, and it sizes the next package.

Screenshots in `handoffs/WPD12_shots/`: the Cuttack answer at desktop width
and at 390px; the mostly-patterns answer; an answer with one or two
findings; an answer with no layout; a hover card open on a figure.

Commit per task on the current branch (`WP-D12 T<n>: …`), as in WP-6g/6h.
Do not push.

---

## Files in scope (you may write ONLY these)

```
DiscoverChat/layout.py                                   new
DiscoverChat/assemble.py                                 the Answer field and the one call
DiscoverChat/main.py                                     the AskResponse field
DiscoverChat/config.py                                   the switch and the constants
DiscoverChat/gates.py                                    one parity check line
DiscoverChat/tests/test_layout.py                        new
frontend/ab-dashboard-main/tailwind.config.ts            ADD the report-* colours only
frontend/ab-dashboard-main/src/services/discover-api.ts  the type
frontend/ab-dashboard-main/src/lib/discover-answer*.ts   only if placement needs a helper
frontend/ab-dashboard-main/src/lib/*.fixtures.json       the five payloads
frontend/ab-dashboard-main/src/components/insights/InsightReport.tsx (+ test)
frontend/ab-dashboard-main/src/components/insights/CitationSpan.tsx  colours and the underline rule
frontend/ab-dashboard-main/src/components/insights/Report*.tsx       new components (+ tests)
handoffs/WPD12_REPORT.md, handoffs/WPD12_shots/**
```

**DO NOT TOUCH:** `DiscoverChat/writer.py`, `judge.py`, `verifier.py`,
`context_brief.py`, `checks.py`, `render.py`, `classifier.py`,
`retrieval.py` (import from them; change nothing); `Insights/**` (import the
formatter and `_SIGNED_DIRECTION`; no edit, **no corpus rebuild**);
`AnomaliesView.tsx` and every component outside `insights/`; any existing
colour value; `Ask/**`; `deploy/**`; every `.env`; `handoffs/PROJECT_PLAN.md`;
`handoffs/WPD12_mockup/**`.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD12_mockup/proposed.dc.html` | The visual spec: spacing, sizes, colours, bar construction |
| `DiscoverChat/assemble.py` (`answer`, from "findings = …") | Where the consolidated path sets `tagged_text` — the one place `layout.build` is called |
| `DiscoverChat/checks.py` (`cited_ids`, `bind_numerals`, `supplied_text`) | Cited and Weight come from here; do not re-derive them |
| `DiscoverChat/corpus.py` (`Finding`, `members_of`) | The record accessors |
| `Insights/src/phase5f_decompose.py` (`build_sentence`, `_fmt`, `_pct`, `_SIGNED_DIRECTION`) | How the corpus formats what you will display |
| `frontend/…/insights/InsightReport.tsx`, `CitationSpan.tsx`, `lib/discover-answer.ts` | The card you extend and the per-paragraph citations you place panels with |
| `handoffs/WPD8_hover_to_source.md` and `WPD8_REPORT.md` | How the hover layer was added without disturbing the old render — the same discipline applies |

## Gate — green as one set

- `python -m DiscoverChat.gates` green, with the parity check added.
- `python -m pytest DiscoverChat/tests -q` green, including `test_layout.py`.
- `npm test`, `npm run lint`, `npm run build` green.
- Additivity holds: layout off → the service and the tab behave as before
  this package.
- The six screenshots and the weak-writer table are in the report.

## Not this package — note for the next one

The short answer and the section headlines will be written by the same
mid-size model. They are being trialled separately, on operator rulings of
2026-11-21 — see `handoffs/WPD13b_headline_trial.md`. Do not build towards
them here.

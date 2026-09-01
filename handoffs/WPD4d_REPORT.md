# WP-D4d report — the checked feed prose onto the Discover page

**Agent run 2026-09-01 (D48).** Brief: `handoffs/WPD4d_frontend_feed.md`.
**Zero API calls.** No model ran in this WP: the emitter reads the shipped
sidecar and writes markdown, and nothing on that path can reach a `Caller`.

---

## §0 Gate table

| # | Gate | Result |
|---|---|---|
| 1 | Emitter deterministic; checker green including round-trip | **PASS** — two emits byte-identical in both modes; checker 29/29 on the Drive copy (notes off), 30/30 in the mirror (notes on); WP-D4c self-test still 14/14 |
| 2 | Frontend suite + build green in the mirror; parser and components untouched | **PASS** — `vitest run` 40 tests / 5 files, `npm run build` ✓ 3,744 modules. `src/lib/insights-report.ts` and every component byte-unchanged |
| 3 | Exactly one report file in the data folder; provenance header present | **PASS** — `insight_feed.md` + `README.md`, nothing else; header carries stamp, candidate set, "do not hand-edit" and the regeneration command |
| 4 | `git status` = writable set + standing exclusions | **PASS** — §2.4 |
| 5 | Operator gate-6 read on the rendered page | **PENDING YOU** — dev server up at **http://localhost:8080/**, Discover tab |

Two dispatch decisions were put to the operator before any code was written
(§5, D48-1 and D48-2): **reading notes OFF** for the published edition, and
**the feed's own `view_title`** for the section headings. Both are as answered.

**Artifacts.** `Insights/metainsights/insight_feed.md` — 22,174 bytes, sha256
`2064d327a29552968779502ca5c85eec41dcbaa0ecd8635e8ed240861557e36e`, rendered
from sidecar sha256 `333b24e5214fec8ce4056d5bdd38506ad8059061ddd7d9022417496182354f10`.
The copy in the frontend data folder is `cmp`-identical to it.

---

## §1 The emitted shape

One `## ` section per view — sections in first-appearance order, findings in
feed order inside them — and **one** of the parser's two recognised insight
shapes, never a third:

```markdown
**<the record's lead>**

1. <the record's detail>
```

The parser reads that back as `leadline == lead` and `bullets == [detail]`.

**Why this shape and not `### ` + paragraph.** Both would carry the text, but
the `### ` collector runs to the next `## `, `### ` or `---` and silently
swallows everything else on the way — *including a reading-note blockquote*,
which would then never be parsed as a note. The bold-leadline collector stops
at the first non-numbered line, so a note that follows a finding still parses.
With reading notes ON, only this shape is safe, and using one shape in both
modes means the mode switch cannot change how a finding is read.

**Why the detail is not split into sentences.** The brief allows splitting
"only if the shape needs bullets"; this shape does not. One verbatim string is
a stronger guarantee than *n* verbatim fragments, and sentence-splitting prose
that contains `Rs 51.96 crore`, `2020-21` and `“Activity Approved”` is a
defect waiting to happen.

### Shape class A — a record with a detail (31 of 32 possible; all 32 here)

Rank 1, verbatim from the emitted file:

```markdown
**The 20-GP sample records spending of Rs 51.96 crore below plan across 5,630 costed activities, and the gap is widespread rather than driven by one block. Rangeilunda and Kalimela have the largest block-level gaps, at Rs 9.11 crore and Rs 5.90 crore respectively.**

1. In 27 of 28 asset categories, the plan–spending gap is distributed across the 16 sampled blocks rather than concentrated in one place. Banking Facilities did not show the same pattern, but the data provide no clear alternative explanation. Blocks should review ageing costed activities and reconcile plans, progress and payments, with early attention to Rangeilunda and Kalimela; the figures show recorded underspending, not why it occurred.
```

### Shape class B — a fallback record (lead, empty detail)

**No record in the shipped sidecar is a fallback** (19 first-pass, 13
regenerated, 0 fell-back), so this class does not appear in the emitted file.
It is not therefore untested. Rank 32 was turned into a fallback in memory —
`lead = packet.cleaned_sentence`, `detail = ""`, exactly as `build_records`
writes one — re-rendered and re-parsed:

```markdown
**The average monthly payments out per Gram Panchayat is rising in 2 of the 3 time views (year: 2024-2025) — by month and by quarter. The exception is: by year (no clear pattern).**
```

parses back as `leadline == lead` → `True`, `bullets == []`, section
`Geo-Month Cash Cube`, still 32 insights, and every other record unchanged.
Separately, all 32 cleaned fallback sentences were run through the emitter's
renderability guard: none is rejected, so a run that fell back on every finding
would still emit.

### The header

```markdown
# Odisha PR&DW Decision Aid -- the insight feed

*Department of Panchayati Raj & Drinking Water, Government of Odisha*

*Every finding in `metainsights/global_feed.json`, written as checked prose by the insight-prose step: one section per view, findings in feed order, 32 in all.*

*Prose run 2026-09-01T08:17:35Z from candidate set `a7f991c1df3771f9`.*

*Reading notes: omitted (`--no-reading-notes`).*

*Generated from `metainsights/insight_prose.json` -- do not hand-edit; regenerate via `python Insights/src/phase5e_insight_prose.py --emit-feed-md --no-reading-notes`.*
```

Every line is one the parser ignores (`# `, `*italic*`), and none matches
`/^\*\*.*\*\*$/`, so the leadline count still equals the finding count. The
reading-notes line is the one machine-read line: the checker reads the mode off
it and regenerates in that mode, so a regeneration cannot silently use the other
one and call the difference a drift. The documented command was run verbatim,
with no `--base`, and reproduced the shipped file byte for byte.

### Determinism

| mode | run A → B | bytes | sha256 |
|---|---|---|---|
| `--no-reading-notes` (shipped) | byte-identical | 22,174 | `2064d327a2955296…` |
| reading notes on (mirror) | byte-identical | 26,689 | `d4a5aab1b473d00c…` |

`render_feed_markdown` reads nothing off disk and has no clock; the note text,
which does need disk, is built by the caller and handed in.

### Reading notes — built, verified, and then switched off

The ON path was implemented and proved before the operator's OFF answer was
applied to the shipped file, because a flag that has never run is not a flag.
It enriches the feed rows through `phase5b_report.enrich_candidates_with_stats`
and calls `reading_note_block` on the result — the same call the executive
report makes — so the sentences the machinery appends off the findings (the
count caveat, the linkage sentence, the earmark figures, the dated-event
citations) are the ones this feed's own findings earn, not a base note.

Evidence it is verbatim: the three notes it emits are **byte-identical to the
three in the retired `gamma_0.5_report.md`**, em dash for em dash, including
view1's XV Finance Commission earmark sentence and view2's COVID-19 lockdown
citation. Nothing was re-worded here.

Because enrichment reads `views_prdw/*.parquet`, notes ON needs a mirror. Notes
OFF — the shipped mode — reads only the sidecar, and the flag is handled before
`phase5b_report` is imported, so the default mode runs on the Drive copy with
no pandas stack and no parquet.

---

## §2 The swap

### 2.1 The data folder

| before | after |
|---|---|
| `README.md` | `README.md` (updated) |
| `gamma_0.5_report.md` (30,144 b) | `insight_feed.md` (22,174 b) |

Exactly one report file, as the folder's own rule requires. The copy is
`cmp`-identical to `Insights/metainsights/insight_feed.md`.

The README's **Where the report comes from** section described the gamma
editions and named gamma 0.5 as bundled — false the moment the swap landed, and
this folder's README is the thing a future agent reads before touching the
folder. It now documents the emitter, the regeneration command, the fact that
the file is emitted and checked rather than hand-written, and that the gamma
editions still exist but are no longer what Discover renders. The drop-in
contract, the shape section and the reading-note contract are unchanged.

### 2.2 The pin test

It failed, as the brief anticipated — at the import, before any assertion:

```
Error: Failed to resolve import "@/data/insights/gamma_0.5_report.md?raw"
```

Changes, kept to the report's identity and the facts that changed with it:

| test | change |
|---|---|
| import | `gamma05` → `feedReport from "@/data/insights/insight_feed.md?raw"` |
| "is the Odisha report, not a retired AP or UP one" | unchanged assertions, retargeted |
| **new**: "is the emitted rendering of the checked prose, at its own run stamp" | pins the stamp line `*Prose run 2026-09-01T08:17:35Z from candidate set \`a7f991c1df3771f9\`.*` and the "do not hand-edit" marker — the brief's "Odisha content + the stamp line" |
| "parses every bold leadline in the file, and nothing else" | retargeted; `32` added, since D16 freezes the feed at 32 |
| "discovers the report's three sections" | section names → the feed's view titles |
| "leaves no insight stranded outside a section" | retargeted only |
| "gives every insight supporting detail" | retargeted only |
| "carries the generator's deterministic reading notes…" → "carries no reading note, and no insight is one" | **the one substantive rewrite** — see §4 defect 4 |
| "counts only insights, so the chip totals sum to the row count" | retargeted only |
| "renders each reading note as a callout, not as a row" → "gives every finding a row and nothing else one" | the row-count assertion is kept; the callout assertion has no note to make — see §4 defect 4 |
| "excludes the notes from the chip counts" | retargeted only |

Net +1 test. `parseReport`'s own reading-note suite (synthetic fixtures, four
tests) is untouched and still covers the marker contract end to end.

### 2.3 Suite and build

Run in `C:\dev\ab-dashboard-odisha` (Drive path can't run npm — bootstrap §6);
the mirror was resynced from Drive first and `diff -rq` confirms Drive == mirror
after the copy-back.

```
Test Files  5 passed (5)
     Tests  40 passed (40)          ← 24 of them in insights-report.test.ts
✓ built in 7.64s                     ← vite build, 3,744 modules
```

**`src/lib/insights-report.ts` and every component are byte-unchanged.** The
emitter was made to satisfy the parser as-is; it never needed adjusting.

### 2.4 Files, exclusions, pinned set

```
 M Insights/reports_prdw/check_insight_prose.py
 M Insights/src/insight_prose_config.py            (+4 lines: the feed_md path)
 M Insights/src/phase5e_insight_prose.py
 M frontend/ab-dashboard-main/src/data/insights/README.md
 D frontend/ab-dashboard-main/src/data/insights/gamma_0.5_report.md
 M frontend/ab-dashboard-main/src/lib/insights-report.test.ts
?? Insights/metainsights/insight_feed.md
?? Insights/reports_prdw/wpd4d_run/
?? frontend/ab-dashboard-main/src/data/insights/insight_feed.md
?? DiscoverChat/experiments/logs/                  ← WP-D5's, D43, untouched
```

The writable set and nothing else. `insight_prose.json` is not in that list —
the sidecar was read, never written. **Pinned set re-verified after every run,
all seven unchanged**, `global_feed.json` still `3da40edae324f917…`; D16's
freeze holds. **Git read-only** throughout (`status` only). **No `.env`, no API
key, no network call** — the emitter path exits before `_load_key` is reachable.

---

## §3 Round-trip evidence

Two independent implementations, because a checker that transcribes the parser
can only prove the emitter agrees with *that transcription*.

### 3.1 The Python transcription — replays anywhere, including the Drive copy

`parse_report_min` in `check_insight_prose.py` is a literal transcription of
`insights-report.ts`'s `parseReport`: **both** insight shapes, the reading-note
blockquote, `tidy` and `stripOuterBold`, in the same order. It runs in the
default checker invocation.

```
The Discover rendering -- insight_feed.md
  PASS  header names exactly one reading-notes mode          matched 1 of the 2 mode lines
  PASS  provenance header present (generated, do not hand-edit)
  PASS  header carries the run stamp and candidate set id    2026-09-01T08:17:35Z / a7f991c1df3771f9
  PASS  regenerates byte-identical from the shipped sidecar  22174 bytes, sha256 2064d327a2955296
  PASS  one insight parses back per sidecar record           32 parsed, 32 records
  PASS  every leadline is its record's lead, verbatim        32 compared
  PASS  every detail comes back whole, and nothing else does 32 with detail, 0 fallbacks
  PASS  every finding lands in its own view's section
  PASS  sections are the feed's view titles, in feed order   Activity Lifecycle / Geo-Month Cash Cube / GP Performance
  PASS  no finding is stranded outside a section
  PASS  the chip counts sum to the row count                 32
  PASS  no reading notes, as emitted (--no-reading-notes)    the operator's dispatch decision, 2026-09-01
  PASS  no reading note is parsed as a finding

check_insight_prose: 29 checks, 0 failed
```

In the mirror with notes ON, 30/30 — the two extra being *each note is attached
to the section that earned it* and *one parsed note per marker in the file*.

### 3.2 The real parser — run in the mirror

A throwaway vitest file (not committed; kept as evidence at
`Insights/reports_prdw/wpd4d_run/roundtrip_real_parser.test.ts.txt`) imports the
**actual** `parseReport` and `interleaveBySection` and compares against the
sidecar JSON read off disk, record by record. 6 tests, all passing: 32 insights
out, every leadline byte-equal to its record's `lead`, every `bullets` deep-equal
to `[detail]`, every section equal to the record's `view_title`, no reading note,
and the unfiltered list still interleaves Activity Lifecycle → Geo-Month Cash
Cube → GP Performance.

### 3.3 What replays where

| assertion | Drive copy | needs the mirror |
|---|---|---|
| every WP-D4b/c sidecar check (29 of them) | ✔ | |
| header mode, provenance, stamp | ✔ | |
| regenerates byte-identical (notes OFF) | ✔ | |
| regenerates byte-identical (notes ON) | | ✔ parquet |
| parse round-trip, Python transcription | ✔ | |
| parse round-trip, real parser | | ✔ node |
| frontend suite + build | | ✔ node |

Everything asserted about the *shipped* file replays on the Drive copy with no
node, no parquet and no key. Only the notes-ON variant and the real-parser
confirmation need a mirror, and the checker says so in its output rather than
quietly passing.

---

## §4 Defects — logged, not fixed

**1. The page mixes `₹` and `Rs`.** Ranks 8 and 21 write `₹41.61 crore`,
`₹14 lakh`, `₹1.02 crore`; the other 18 money-carrying findings write `Rs`.
Both are the writer's own wording inside the accepted sidecar, so fixing it
means rebuilding the sidecar — out of scope here, and the operator's standing
reason for shipping this one as-is (verified under the stronger pre-D47 judge)
argues against a rebuild for a glyph. Visible on the page. Worth a queued item:
either pin the currency form in the writer's context, or normalise `₹` → `Rs`
in the emitter, which would make the emitted text no longer verbatim and so
needs a decision, not a patch.

**2. The published page now carries no methodology caveats.** This is the
operator's decision (D48-1) and is implemented exactly as asked, but the
consequence should be on the record: the notes are what said that a zero may be
a recorded zero, that completion recording effectively ceased after 2022-23,
that sanction figures describe one activity in six, and that activity counts
jump at FY 2023-24 for a reporting reason. Several shipped findings quote
sanction-basis and completion figures. The machinery is built, verified
byte-identical to the gamma notes, and one flag away; re-emitting without
`--no-reading-notes` restores them.

**3. Two of the three chips read as engine names.** The section headings are
now `Activity Lifecycle`, **`Geo-Month Cash Cube`** and **`GP Performance`** —
brief-mandated and operator-confirmed (D48-2), replacing `Monthly Money Flows by
Gram Panchayat` and `Gram Panchayat Report Card by Year`. "Cube" is the analysis
engine's word, and this is the kind of language the prose checks
(`banned_tokens`, `_SNAKE`, `ENGINE_ENUMS`) ban everywhere else in officer-facing
text. `phase5b_report.VIEW_DESCRIPTIONS[view]["title"]` holds the reader-facing
titles if this is ever revisited; it is a one-line change in
`render_feed_markdown`.

**4. One test lost its subject.** "renders each reading note as a callout, not
as a row" exercised `ReadingNoteCallout` against the bundled report. With no
note in the bundled report there is nothing for it to assert, so it is now
"gives every finding a row and nothing else one" — it keeps the row-count
guarantee and adds that "Reading note" appears nowhere on the page, but the
callout *rendering* path is no longer covered by any test. `parseReport`'s
reading-note suite still covers the parser side against synthetic fixtures. If
notes go back on, restore the old assertions with them.

**5. A detail now renders as a single numbered row.** The gamma edition gave
each finding four or five short numbered points; each finding here has one row
numbered `01` carrying a 60–90 word paragraph. That is the honest rendering of
what the sidecar holds — one lead, one detail — and no component was touched to
accommodate it, but it is a visible change of texture and the `01` marker in
front of a lone paragraph is slightly odd. Worth your eye at the gate-6 read: if
it reads badly, the fix belongs in the component (drop the number when there is
one bullet), not in the emitter.

**Not a defect, stated so it is not mistaken for one:** the prose carries curly
quotes, en dashes and em dashes (`“Activity Approved”`, `plan–spending`). The
repo's ASCII-only convention exists because ReportLab's Helvetica has no glyph
for them in the PDF deliverable. This file is only ever rendered by a browser.

---

## §5 Decision journal

**D48-1 — reading notes: OFF for the published edition.** *Operator, at
dispatch.* The brief set the default to ON and required confirmation. Asked with
both consequences stated; answered OFF. Implemented as: the `--no-reading-notes`
flag the brief names, with the code default left ON as the brief designed it,
and the shipped file emitted with the flag. The mode is recorded in the file's
own header and the checker regenerates in whichever mode the header states, so
the default and the shipped file cannot disagree silently.

**D48-2 — section headings: the feed's `view_title`.** *Operator, at dispatch.*
Raised because the brief's wording ("the feed's own view titles") resolves to
`Activity Lifecycle` / `Geo-Month Cash Cube` / `GP Performance`, which is not
what the page shows today and puts engine vocabulary on the chips. Both options
were put with the rendered chip labels shown; answered: as the brief says.
Logged as defect 3 so the trade-off is on the record, not because it is
unresolved.

**D48-3 — bold leadline + one numbered bullet, not `### ` + paragraph.** *Mine.*
Both parser shapes can carry lead and detail. The `### ` collector swallows a
reading-note blockquote (§1); the bold-leadline collector does not. One shape
that is safe in both modes beats two shapes that differ by mode.

**D48-4 — the detail is one bullet, not sentence-split.** *Mine.* The brief
permits splitting only if the shape needs it. It does not, and one verbatim
string is a stronger claim than *n* fragments over prose full of decimals,
fiscal years and quoted status labels. Cost: defect 5.

**D48-5 — the emitter refuses to emit prose that would not round-trip.** *Mine.*
`_check_renderable` rejects a lead that is empty, multi-line, whitespace-padded,
contains `**`, contains a spaced `--`, or opens with `#`, `>`, `- ` or `1. ` —
each one a property of the parser, not a style rule. None fires on this sidecar
or on any of the 32 cleaned fallbacks. It exists so "leadline == the record's
lead" is structural rather than an observation about one file, and so a future
sidecar that breaks the contract stops the emitter instead of shipping a page
that reads wrong. This is the brief's "STOP and report" rule, in code.

**D48-6 — notes ON enriches rather than using the base note.** *Mine.* Handing
`reading_note_block` no findings would return the base note and drop the
earmark, linkage, count-caveat and event sentences — a quieter caveat than the
page shows today. Enriching costs a parquet dependency in ON mode only, and buys
notes byte-identical to the gamma edition's.

**D48-7 — the data-folder README was updated.** *Mine, in-scope file.* It named
gamma 0.5 as bundled and pointed at `phase5c_gamma_reports.py`. Left alone it
would send the next agent to regenerate the wrong thing.

**D48-8 — the real-parser round trip is evidence, not a committed test.** *Mine.*
The brief lets the pin test be touched only as far as the pin needs; a
32-record comparison against a JSON file outside the frontend tree is more than
that. It was run, it passed, the file and its log are in `wpd4d_run/`, and the
committed test file carries only the retarget.

---

## §6 Self-audit

**What I would claim.** The emitted file is a deterministic function of the
sidecar and nothing else; it regenerates byte-identical; and run back through
both a transcription of the frontend parser and the frontend parser itself it
yields 32 insights whose leadlines are the 32 records' leads byte for byte and
whose bullets are the 32 details, whole. The frontend suite and build are green
with the parser and every component untouched. The reading-note path is built
and produces text byte-identical to the retired report's.

**What I would not claim.**

- **Not that the page reads well.** Every gate below the last is mechanical.
  Nobody has looked at the rendered Discover tab yet — that is gate 6, and it is
  yours. Defect 5 is the thing I would look at first.
- **Not that the fallback shape has ever fired in production.** No record has
  ever fallen back. Class B is proved by mutating a record in memory, which is
  the same idiom WP-D4c used for the cleaned renderer, and no stronger.
- **Not that `parse_report_min` is the parser.** It is my reading of it. That is
  exactly why §3.2 exists; the two agree on all 32 records, which is the useful
  claim.
- **Not that the notes-ON mode is production-ready on the Drive tree.** It needs
  a mirror with parquet. The checker reports this rather than asserting past it,
  but a future operator flipping the flag on the Drive copy will get a failure,
  not a file.
- **Not that WP-D4b/c's own findings are re-litigated here.** The sidecar is
  shipped as accepted; the D46 deferred fixes are still deferred; the D44
  verifier-weakening note in `insight_prose_config.py` still stands and this WP
  neither improved nor worsened it.

**Scope.** No file outside the brief's writable list was modified. The parser,
the components, `insight_prose.json`, the pinned set, `Ask/`, `Data/`, the packs,
`PROJECT_PLAN.md`, WP-D5's paths and the PM's dispatch files are untouched.
Mirrors used: `C:\dev\ab-dashboard-odisha` (frontend, resynced from Drive first,
results copied back and diffed) and `C:\dev\odisha-d6` (parquet, for the
notes-ON verification only; its scratch copy of the ON-mode file was deleted
afterwards so nothing stale is left reading as current).

**Logs.** `Insights/reports_prdw/wpd4d_run/` — `emit_1.log`, `emit_2.log`,
`checker_drive_notes_off.log`, `checker_mirror_notes_on.log`,
`roundtrip_real_parser.log`, `roundtrip_real_parser.test.ts.txt`,
`vitest_full.log`.

---

## Gate 6 — over to you

`npm run dev` is running in the mirror: **http://localhost:8080/** → the
**Discover** tab. That single read closes WP-D4b, WP-D4c and WP-D4d together and
ratifies that feed prose supersedes the gamma edition as the published Discover
surface.

What to look at: the three chips and their counts (15 / 15 / 2, "All" 32); a
finding opened, for defect 5's `01`-numbered paragraph; the absence of any
reading-note callout, which is D48-1 as you decided it; and ranks 8 and 21 for
defect 1's `₹`.

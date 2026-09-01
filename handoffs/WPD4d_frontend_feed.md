# WP-D4d brief — the checked feed prose onto the Discover page

**Workstream:** Discover + frontend (operator authorized the cross-boundary
touch 2026-09-01: "now let's move this to the frontend"). **Nature: BUILD,
small.** **Zero API calls — no model runs in this WP.** **Authored:** PM,
2026-09-01 (D48).

**What this does.** The Discover tab currently renders a committed copy of the
gamma 0.5 edition through the drop-in contract documented in
`frontend/ab-dashboard-main/src/data/insights/README.md` (one markdown file,
parsed at build time by `src/lib/insights-report.ts`). This WP replaces that
file with a **deterministic markdown rendering of the accepted 32-finding
prose sidecar** (`Insights/metainsights/insight_prose.json`), emitted by the
pipeline so it can never drift from the checked artifact.

**What this deliberately does NOT do:** no rebuild of the sidecar, no LLM
call, no change to the frontend parser or components, no change to the feed
JSON (D16 untouched), no D46 deferred fixes (operator: "add this later" — and
the shipped sidecar was verified under the stronger pre-D47 judge, which is a
reason to ship it as-is, not rebuild it under the weaker one).

---

## Files in scope (writable) — nothing else

```
Insights/src/phase5e_insight_prose.py                     the markdown emitter (new function + CLI flag only)
Insights/src/insight_prose_config.py                      emitter constants if needed
Insights/metainsights/insight_feed.md                     NEW — the emitted report
Insights/reports_prdw/check_insight_prose.py              new assertions (see T3)
Insights/reports_prdw/wpd4d_run/**                        logs
frontend/ab-dashboard-main/src/data/insights/**           the swap: remove the gamma copy, add insight_feed.md
frontend/ab-dashboard-main/src/lib/insights-report.test.ts   ONLY if the pin test fails on the new file
handoffs/WPD4d_REPORT.md                                  your report
```

**DO NOT TOUCH:** `src/lib/insights-report.ts` and every frontend component —
the whole point is that the existing contract holds; **if the emitter cannot
satisfy the parser as-is, STOP and report — do not adjust the parser.** Also:
everything WP-D5 owns, the pinned candidate/feed files, `insight_prose.json`
itself, `Ask/`, packs, `Data/`, `PROJECT_PLAN.md`, `.env` (not even needed —
no API calls). No git beyond read-only.

## Preconditions

Standing exclusions apply (D43 concurrency for WP-D5's paths; D44 ruling 1 for
PM dispatch files). Pinned-set SHA check as usual. Frontend work runs from a
`C:\dev` mirror (bootstrap §6 — npm breaks on the Drive path); copy results
back as files only.

## Read first

| File | Why |
|---|---|
| `frontend/ab-dashboard-main/src/data/insights/README.md` | The drop-in contract you are emitting INTO — shapes, the reading-note marker, the one-file rule, the Odisha pin |
| `frontend/ab-dashboard-main/src/lib/insights-report.ts` | The parser that defines what round-trips: bold-leadline + numbered bullets, or `###` + paragraph + dash bullets; `READING_NOTE_MARKER` |
| `Insights/metainsights/insight_prose.json` | The source: 32 records — lead, detail, status, stamp, candidate_set_id |
| `Insights/src/phase5b_report.py` | `READING_NOTES` / `reading_note_block` — the deterministic per-view notes, if the operator keeps them (T1 switch) |

## Tasks

### T1 — The emitter
**Do:** a deterministic function in `phase5e`: sidecar → `insight_feed.md`.
Requirements:
- One `## ` section per view, using the feed's own view titles; findings in
  feed order within their section. (The page's chips derive from sections; the
  unfiltered list interleaves them — both existing behaviors.)
- Each finding renders so that the frontend parser recovers **leadline == the
  record's lead** and **bullets carrying the record's detail verbatim** (split
  only at sentence boundaries if the shape needs bullets). Pick whichever of
  the parser's two recognized shapes satisfies that; do not invent a third.
- A fallback record (lead, empty detail) renders as a leadline with no bullets.
- File header carries provenance as plain lines the parser ignores: run stamp,
  candidate set id, "generated — do not hand-edit; regenerate via phase5e".
- **Reading notes — operator switch, default ON:** emit each view section's
  deterministic reading note (from the existing `reading_note_block` machinery,
  verbatim, behind `READING_NOTE_MARKER`) at the end of its section — this
  preserves what the page shows today. A `--no-reading-notes` flag omits them.
  Confirm the default with the operator at dispatch; do not decide it.
**Done when:** two emitter runs on the same sidecar are byte-identical.

### T2 — The swap
**Do:** in the frontend data folder: remove `gamma_0.5_report.md`, add the
emitted `insight_feed.md` (exactly one report file remains — the README's
rule). Run the frontend's own test suite in the mirror; if
`insights-report.test.ts`'s Odisha pin fails on the new file, update the pin
minimally to assert this report's identity (Odisha content + the stamp line),
nothing else.
**Done when:** `npm test` green in the mirror; `npm run build` succeeds.

### T3 — Checker + round-trip proof
**Do:** extend `check_insight_prose.py`: (a) `insight_feed.md` regenerates
byte-identical from the sidecar (same idiom as the fallback recomputation);
(b) a parse-level round-trip — reimplement the parser's recognition minimally
or invoke the real one via node in the mirror — asserting 32 insights out,
every leadline equal to its record's lead, every detail fully present, reading
notes (if on) attached to the right sections and to no finding row.
**Done when:** checker green; state plainly which assertions replay on the
Drive copy.

## Gate

1. Emitter deterministic; checker green including round-trip.
2. Frontend suite + build green in the mirror; parser and components untouched.
3. Exactly one report file in the data folder; provenance header present.
4. `git status` = writable set + standing exclusions.
5. **Operator gate (the big one): the gate-6 read happens ON THE RENDERED
   PAGE** — `npm run dev` in the mirror, read the Discover tab. That single
   read closes WP-D4b, WP-D4c and WP-D4d together, and ratifies that feed
   prose supersedes the gamma edition as the published Discover surface.

## Report — `handoffs/WPD4d_REPORT.md`

§0 gate table · §1 the emitted shape, with one rendered finding per shape
class quoted · §2 the swap + test/pin changes · §3 round-trip evidence ·
§4 defects (logged, not fixed) · §5 decision journal · §6 self-audit.

# Discover insights drop-in

`AnomaliesView` globs `*.md` in this folder at build time. Drop the report the
MetaInsights run produces over the Odisha PR&DW datasets here and Discover
lights up with no code change; leave the folder empty and Discover shows an
honest "no insights generated yet" state. What is bundled today is
`insight_feed.md` — see **Where the report comes from**.

**Keep exactly one `.md` report here.** If several are present the
alphabetically first one wins, which is a coin toss rather than a decision.

**The report must be this department's.** Discover renders whatever it finds as
this programme's own findings, so a report left behind from an earlier
deployment is silently wrong rather than visibly broken — the page still looks
right, it just briefs officers on another state. `insights-report.test.ts` pins
the bundled report to Odisha for exactly this reason; if you legitimately swap
in a different programme's report, that test is the thing to update.

## Expected report shape

Sections come from the report's own `## ` headings — they are discovered, not
mapped to a fixed list, so the filter chips always match the report supplied.
Within a section, two insight shapes are recognised:

```markdown
## Activity Lifecycle - Every Planned Work and Its Money

**Chikilli has Rs 0 sanctioned across every year despite accounting for 5.0% of the activities recorded.**

1. Chikilli is the only Gram Panchayat with Rs 0 of the sample's Rs 28.84 crore sanctioned amount.
2. Its recorded sanction amount remains Rs 0 in every fiscal year from 2020-2021 to 2025-2026.

### Alternatively, a heading works too

A leading paragraph becomes the first detail line.

- Dash bullets are collected as details.
```

Numbers in the leadline are bolded automatically in the UI, so write leadlines
with the number in them. `**bold**` is honoured everywhere — leadlines, bullets
and reading notes — so a marker never reaches the page as an asterisk.

## Reading notes

A section may end with a methodology caveat. It is **not** a finding: it takes
no row, no chevron, no number and no place in a chip count, and it renders as a
muted callout pinned under the findings it qualifies.

The marker is the contract, and the whole blockquote is the note:

```markdown
> **Reading note:** Sanction records exist for **2,101 of the 12,704 activities**
> (about one in six), so every sanctioned-basis figure describes that subset only.
```

The text is emitted verbatim by `Insights/src/phase5b_report.py`
(`READING_NOTES` / `reading_note_block`), never written by the model — a
paraphrased caveat is worse than no caveat. Both ends of the contract are named
`READING_NOTE_MARKER`, in that file and in `src/lib/insights-report.ts`; change
one and change the other. `Insights/src/prose_gate.py` fails a report that is
missing a note, carries two, or lets the model write a rival one under its own
heading.

These notes carry the caveats that make the numbers safe to act on — that a
zero may be a recorded zero rather than nothing happening, that completion
recording effectively ceased after 2022-23, that activity counts jump at
FY 2023-24 for a reporting reason.

**The bundled edition carries none.** The emitter can emit them and does by
default; the operator's dispatch decision on 2026-09-01 (WP-D4d) was to publish
this edition with `--no-reading-notes`. Re-emit without that flag to put them
back — the contract above is unchanged and the parser still honours it.

## Where the report comes from

`Insights/metainsights/insight_feed.md`, emitted by

```
python Insights/src/phase5e_insight_prose.py --emit-feed-md --no-reading-notes
```

which renders `Insights/metainsights/insight_prose.json` — the checked prose
sidecar, one record per finding in the global feed — into the shape above. Each
finding becomes a bold leadline carrying the record's `lead` and one numbered
bullet carrying its `detail`, verbatim; the `## ` sections are the feed's own
view titles, and the findings sit in feed order inside them.

**It is emitted, never hand-written.** `Insights/reports_prdw/check_insight_prose.py`
regenerates this file from the sidecar and asserts it byte-identical, then parses
it back and asserts every leadline is its record's lead and every detail is
present whole. A hand-edit here fails that check; fix the sidecar and re-emit.
Reading notes ON additionally needs a mirror carrying `views_prdw/*.parquet`,
because the note text is built from the enriched findings.

**This supersedes the gamma editions as the published Discover surface**
(WP-D4d, ratified at the WP-D4b/c/d gate-6 read). Until then this folder held a
copy of the gamma 0.5 executive report from `Insights/reports_prdw/`, produced
by `Insights/src/phase5c_gamma_reports.py` at an operator-chosen gamma (D24).
Those editions are still generated and still live there; they are no longer what
Discover renders.

# Discover insights drop-in

`AnomaliesView` globs `*.md` in this folder at build time. Drop the report the
MetaInsights run produces over the AP datasets here and Discover lights up with
no code change; leave the folder empty and Discover shows an honest "no insights
generated yet" state.

**Keep exactly one `.md` report here.** If several are present the
alphabetically first one wins, which is a coin toss rather than a decision.

## Expected report shape

Sections come from the report's own `## ` headings — they are discovered, not
mapped to a fixed list, so the filter chips always match the report supplied.
Within a section, two insight shapes are recognised:

```markdown
## Payments & DBT

**Payment pendency is concentrated in two districts — 35% of MARKFED transactions**

1. East Godavari accounts for 412 of the pending transactions.
2. Prakasam follows at 388.

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
> **Reading note:** these figures are **per farmer on the PM-KISAN roster**, not
> per farmer in the full farming population.
```

The text is emitted verbatim by
`Metainsights_anomalies/src/phase5b_report.py` (`READING_NOTES` /
`reading_note_block`), never written by the model — a paraphrased caveat is
worse than no caveat. Both ends of the contract are named `READING_NOTE_MARKER`,
in that file and in `src/lib/insights-report.ts`; change one and change the
other. `src/prose_gate.py` fails a report that is missing a note, carries two,
or lets the model write a rival one under its own heading.

## Where the report comes from

`AP_METAINSIGHTS_DRYRUN_HANDOFF.md` (v3) in the repo root. Note that its
calibration scorecard is scored against `D1_PATTERN_ANSWER_KEY.md`, which must
never be fed to an LLM — copy only the generated report into this folder.

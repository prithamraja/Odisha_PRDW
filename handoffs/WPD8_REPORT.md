# WP-D8 report — frontend: hover-to-source on the Discover answer

**Status: built, gate green.** Every figure in a Discover answer is now the
hover target for the finding it came from, with a link to the raw record. The
fallback-selection notice (D8.3) is in. **Executed:** 2026-09-04, against the
WP-D7 DiscoverChat running from the `C:\dev\odisha-d7` mirror on port 8100.

---

## 1. Preconditions

| # | Check | Result |
|---|---|---|
| 1 | DiscoverChat serving the WP-D7 payload | **Pass.** `/chat` on 8100 returns `answer_tagged` (672 chars), `citations` (2 entries) and `answer_html` (8,340 chars) for "What should I know about Kalimela?". The service died partway through fixture recording and was restarted from `C:\dev\odisha-d7` (`python -m uvicorn DiscoverChat.main:app --port 8100`); all figures below are from the restarted process. |
| 2 | Fresh local mirror | **Pass.** `C:\dev\ab-dashboard-odisha` re-mirrored from `frontend/ab-dashboard-main` (`src/` already byte-identical; all config files recopied). `npm install` clean, `npm run dev` on **8080**. |
| 3 | Baseline green before changing anything | **Test and build pass; lint was already red.** See §2. |
| 4 | Tree state | Clean apart from paths listed in §8. |

**One local-only change outside the repo:** the mirror's `.env` pointed
`VITE_DISCOVER_API_BASE_URL` at **8101**, left by an earlier session; 8101 is
dead and the WP-D7 service is on 8100, so the mirror's `.env` was repointed.
The Drive repo's `.env` and `.env.example` were **not touched** — they already
say 8100.

## 2. Baseline vs final

| | Baseline | Final |
|---|---|---|
| `npm test` | **7 files, 61 tests, all pass** (exit 0) | **8 files, 110 tests, all pass** (exit 0) |
| `npm run lint` | **10 problems (3 errors, 7 warnings)**, exit 1 | **10 problems (3 errors, 7 warnings)**, exit 1 — *byte-identical file list* |
| `npm run build` | pass, built in 22.6s | pass, built in 24.1s |

A **flake worth knowing about, not caused by this WP**: with the vite dev
server and DiscoverChat both running, two `src/pages/Index.test.tsx` cases
(Ask tab) cross vitest's 5,000 ms per-test timeout. They take 3.6 s and 1.7 s on
an otherwise idle machine, so the margin is thin. Run in isolation, or with the
dev server stopped, all three pass. `Index.test.tsx` is unmodified in this WP
(`git status` clean, no diff) and contains no reference to Discover. The counts
above are from a run with the dev server stopped.

**The lint red is pre-existing and not mine.** All 3 errors are in files I
never opened: `src/components/ui/command.tsx:24`, `src/components/ui/textarea.tsx:5`
(`no-empty-object-type`, shadcn boilerplate) and `tailwind.config.ts:109`
(`no-require-imports`). Diffing the flagged-file lists before and after gives
no difference, and **no file I wrote appears in the lint output at all**. Logged,
not fixed, per the brief.

## 3. The design decision, and why it changed

**The brief's D8.1 sketch of the binding rule does not describe what the service
does, and the two produce visibly different pages.** The brief says a bound span
is "the number immediately before the tag when there is one". The service's
actual rule (`render._spans_for_sentence`, driven by `checks.bind_numerals`)
binds **every numeral in a sentence** to the first tag in that sentence whose
*stored* sentence contains it, and only then falls back to a claim phrase for a
tag that bound no numeral.

On one Kalimela turn the difference is 10 bound spans versus about 4 — and under
the sketch most of them are whole sentences, so nearly every line carries a
dotted underline and "the number itself is the hover target" (WP-D7 ruling 4)
stops being true.

Three options were put to the PM. **The ruling was: transport the span
boundaries out of `answer_html`, and render the card with our own components.**
That is what is built. It means:

- the frontend performs **no numeral matching of its own** — no second
  implementation of `_num_variants` to drift away from the rule the citation
  check actually passed on, which is exactly what `render.py`'s docstring warns
  against;
- the render matches the oracle **by construction**, not by agreement;
- the design decision in D8.0 is still honoured where it was actually arguing —
  the card is built from `citations` with the tab's own tokens, and nothing of
  `answer_html`'s styling, `title=` tooltips or `↗` anchors reaches the page.

`answer_tagged` is therefore carried in the type (an older service may send it
without `answer_html`) but is not the parsing input.

## 4. How it works

`spansFromHtml` walks the reference render's text stream and the plain `answer`
**in step**, allowing any whitespace run on either side to match any run on the
other — which is the only way the two differ, because `to_html` strips each
sentence, joins with a single space, and closes the gap before `.,;:!?`. Nothing
is searched for, so a span whose text is `"4"` cannot land on the wrong `4`. If
the two streams ever disagree on a non-space character the function returns
null and the tab renders exactly as it did before.

The result is offsets into `answer` itself, so **segments are slices of the
answer** and reassembling them reproduces it byte for byte by construction.

`parseAnswer` was refactored onto a shared block splitter that keeps character
offsets; its output shape is unchanged and all 13 of its original tests pass
untouched.

## 5. The `record_url` shape, and how it was prefixed

`DiscoverChat/config.record_url()` returns **a bare path** — `/record/{id}` —
unless the deployment sets `DISCOVERCHAT_RECORD_URL_BASE`. Confirmed against
the running service: `citations["1-02147"].url == "/record/1-02147"`.

`recordHref` in `discover-api.ts` therefore:
1. passes an absolute `http(s)` URL through untouched (the deployed case);
2. otherwise resolves the path against **`VITE_DISCOVER_API_BASE_URL`** — the
   same base `askDiscover` posts to, not the frontend's own origin, which is a
   different host in every deployed configuration;
3. appends `?format=html` for the readable view.

Verified end to end: `GET /record/1-02147?format=html` → `200 text/html`, and
the record page opened from a live hover card is in
`WPD8_shots/kalimela-5-record.png`.

## 6. Fixtures

**The brief's stated fixture source does not contain what it says it does.**
`DiscoverChat/experiments/answer_compare.json` is described as "15 real answers
with `tagged_text`, `citations` and rendered HTML". In fact: the `old` arm has
`tagged_text` empty in all 15; the `new` arm has it in 13 of 15; `findings` is a
list of **id strings only**; and there is **no citations map and no rendered
HTML anywhere in the file**. It cannot supply the oracle the gate needs.

So fixtures were **recorded from the running WP-D7 service** on 2026-09-04 —
the 15 questions from that file (which already include "How is Chikilli
doing?"), plus "What should I know about Kalimela?" = **16 turns**, each with
`answer`, `answer_tagged`, `citations`, `answer_html` and `retrieval.judge.source`.
Stored at `src/lib/discover-answers.fixtures.json` (128 KB).

- **15 turns carry `answer_html`** and drive the oracle tests.
- **1 turn ("Who is driving the shortfall?") came back with no tagged text at
  all** — the bare-sentence fallback. It is kept deliberately: it exercises the
  degradation path with a real payload rather than a synthetic one.
- Across the 15, **327 bound spans, every one matching the oracle exactly** in
  id, text and order.

## 7. Gate

| Gate item | Result |
|---|---|
| (a) stripping reproduces `answer` exactly, every fixture | **Pass** — 15 per-fixture tests. Segments are slices of `answer`, so this is exact, not normalised. |
| (b) every `data-finding-id` span in `answer_html` bound, no extras | **Pass** — 15 per-fixture tests comparing the ordered `(id, text)` list against the markup, plus an id-set check. |
| (c) unknown id → plain text, no crash | **Pass** — warns once per id, never per occurrence; block text unchanged. |
| (d) missing `answer_tagged`/markup → today's render | **Pass** — checked against `parseAnswer` on all 16 fixtures; also a "markup is not this answer's" case. |
| (e) fallback notice iff `judge.source === "fallback-threshold"` | **Pass** — unit tests on both branches plus 4 component tests. |
| `npm run lint`, `npm run build` | **Build green. Lint red exactly as at baseline** (see §2). |
| Ask tab untouched | **Pass** — `Index.test.tsx` not modified and green; no assertion changed. |

**Manual, live against the service** (`WPD8_shots/`, and `shots.json` for the
recorded assertions):

| | Kalimela | Chikilli (decomposition-bearing) |
|---|---|---|
| bound spans on screen | **49** | **28** |
| figure hovered | `852` | `5` |
| record link | `…/record/d1-23759?format=html` | `…/record/1-02288?format=html` |
| focus opened the card | yes | yes |
| `Escape` closed it | yes | yes |

`kalimela-2-hovercard.png` shows the card open on `852`, carrying the finding's
display sentence, `Covers: Gram Panchayat Kalimela`, the standing line ("a
breakdown of the recorded totals, not a mined pattern"), `Activity Lifecycle —
as of 2026-08-17` and `Open record ↗`. **It is not clipped** — it extends past
the report card's `overflow-hidden` edge, which is what the portal is for.
`kalimela-5-record.png` is the record it links to; its stored sentence is the
card's sentence.

## 8. Payload and behaviour notes — logged, not fixed

1. **The brief's "hard invariant" does not hold of `answer_tagged`.** Stripping
   `[id]` tags from it does **not** reproduce `answer` byte for byte: (a) the
   tagged text carries **no stamp block**, and (b) the service's own strip
   leaves the space where a tag was, so `answer` has a trailing space before
   `\n\n` that a `\s*\[…\]` strip removes. Only whitespace-normalised equality
   holds. This is not a defect in the service — but any implementation that had
   taken the invariant literally would have failed. Ours does not depend on it.
2. **A finding cited in a sentence with no numerals may get no hover in that
   sentence.** `_spans_for_sentence` gives the claim phrase to the *first*
   unbound tag; a second tag in the same sentence has an empty phrase left and
   is skipped. Kalimela's opening sentence cites `[1-02147] [1-02930]` and only
   `1-02147` gets a span. Matches `render.py` exactly, so it is reproduced, not
   corrected — flagging it because "every cited finding is hoverable somewhere"
   is not guaranteed sentence by sentence.
3. **`judge.source` was `"judge"` on all 16 recorded turns**, so the D8.3 notice
   could not be exercised against the live service. It is covered by unit and
   component tests only.
4. **No encoding defect.** An early console read suggested mojibake in
   `citations[].standing`; the raw bytes are correct UTF-8 em-dashes. That was a
   cp1252 terminal, not the payload.

**One bug found and fixed in this WP's own code:** the hover card was first
keyed by citation id, which marked *every* span bound to the same finding as
expanded — the normal case, since one finding usually binds several figures.
It is now keyed by the anchor element. Covered by the "shows one card at a
time" test.

## 9. Files

**Touched (in the brief's writable set):**

```
frontend/ab-dashboard-main/src/services/discover-api.ts          DiscoverCitation, 3 optional fields, recordHref
frontend/ab-dashboard-main/src/lib/discover-answer.ts            offset-keeping block split, parseCitedAnswer,
                                                                 spansFromHtml, usedFallbackSelection
frontend/ab-dashboard-main/src/lib/discover-answer.test.ts       +39 tests (13 originals untouched and green)
frontend/ab-dashboard-main/src/components/insights/InsightReport.tsx   cited render, D8.3 notice
frontend/ab-dashboard-main/src/components/insights/CitationSpan.tsx    NEW — the span, the card, the portal
frontend/ab-dashboard-main/src/components/insights/InsightReport.test.tsx  NEW — 10 tests
handoffs/WPD8_REPORT.md                                          this report
```

**Two additions outside the letter of the writable set, both test/report
assets — flagging rather than assuming:**

- `frontend/ab-dashboard-main/src/lib/discover-answers.fixtures.json` — the 16
  recorded turns. The gate requires fixture-driven tests and the named source
  cannot supply them (§6). Inlining 128 KB of recorded HTML into the `.test.ts`
  was the alternative.
- `handoffs/WPD8_shots/` — the 10 screenshots and `shots.json` the report cites.

**Not touched, as instructed:** `DiscoverChat/**`, `Insights/**`, `Ask/**`,
`deploy/**`, `PROJECT_PLAN.md`, `LABEL_SHEET.md`, every `.env` in the repo, the
Ask tab's components and services. `src/pages/Index.test.tsx` needed no change
— the new response fields are optional — so it was left alone. The unchecked-prose
path (D40 item 5) was not touched and Discover text is not routed through it.
No git operation beyond `status` / `log` / `rev-parse`.

**Dirty in the tree but not mine** (concurrent WPs — left alone):

```
 M DiscoverChat/context_brief.py
?? DiscoverChat/experiments/logs/
?? handoffs/WPD8_hover_to_source.md      (this WP's brief)
?? handoffs/WPD9_judge_completeness.md
```

## 10. Not registered

WP-D8 is still absent from `PROJECT_PLAN.md`, as the brief noted. Registering it
is a PM action; `PROJECT_PLAN.md` is outside the writable set and was not edited.

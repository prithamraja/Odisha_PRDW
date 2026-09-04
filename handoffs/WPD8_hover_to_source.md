# WP-D8 brief — frontend: hover-to-source on the Discover answer

**Workstream:** Discover (frontend leg). **Nature: BUILD, gated.** The
DiscoverChat service already returns, for every consolidated answer, the
citation data that binds each figure to the finding it came from (WP-D7
§3–§4). The Discover tab discards it and renders plain text. This WP makes
the number itself the hover target, with a link to the raw record — the
user's validation mechanism, as ruled in WP-D7 (ruling 4). **Authored:** PM,
2026-09-03. Not yet registered in `PROJECT_PLAN.md`.

**What the service sends, and what the frontend reads today**

| `/chat` field | content | frontend today |
|---|---|---|
| `answer` | plain prose, tags stripped | rendered via `parseAnswer` |
| `answer_tagged` | the same prose with `[id]` tags after each figure/claim, e.g. `…lowest sanctioned amount across all fiscal years [1-02285].` | **discarded** |
| `citations` | per-id map: stored `sentence`, `display_sentence`, `scope`, `standing`, `view`, `stamp`, `url` (the `/record/{id}` link) | **discarded** |
| `answer_html` | the service's REFERENCE render: each bound numeral in `<span class="dc-cite" data-finding-id="…" title="hover text">`, plus `<a class="dc-cite-link" href="…">↗</a>` | **discarded** |
| `retrieval.judge.source` | `"judge"` or `"fallback-threshold"` | discarded |

The binding (which numeral belongs to which finding) is computed **server
side** by the same function the blocking citation check uses
(`DiscoverChat/checks.bind_numerals`), so the frontend verifies nothing —
it only displays. Do not re-derive bindings in the frontend.

---

## Design decision: render from `answer_tagged` + `citations`, not `answer_html`

`answer_html` is a reference render with no styling and native `title=`
tooltips; it exists so the service's own suite can exercise hover-to-source
without a frontend. The product frontend has a design system (the `text-ink`
/ `border-line` / `accent-saffron` / `font-display` tokens in
`InsightReport.tsx`), so build a proper hover card from the tagged text and
the citations map. `answer_html` stays useful as a **fixture and oracle**:
its `data-finding-id` spans tell you exactly which numerals the service
bound, and your render must bind the same ones.

## D8.0 — the payload

- Extend `DiscoverChatResponse` in
  `frontend/ab-dashboard-main/src/services/discover-api.ts` (line ~34) with
  `answer_tagged`, `citations`, `answer_html`, all **optional** — an older
  service, or a turn that fell back to bare sentences, sends them empty or
  absent, and the tab must render exactly as today in that case.
- The `citations[id].url` may be a path or an absolute URL — check what
  `DiscoverChat/config.record_url()` produces against the running service
  and, if it is a path, prefix `VITE_DISCOVER_API_BASE_URL` (the same base
  `askDiscover` already uses). Link to the readable view:
  `…/record/{id}?format=html`.

## D8.1 — parsing

- `src/lib/discover-answer.ts` (`parseAnswer`) splits the plain answer into
  blocks (read it first — bullets, the "as of" line, the decline/why
  messages). Add a tag-aware path: split `answer_tagged` into the same blocks,
  and within a block into segments of `{text, ids[]}` where a segment is the
  span a tag (or run of tags) follows. **Which span:** the number immediately
  before the tag when there is one; otherwise the phrase back to the previous
  tag or sentence start (a non-numeric claim like "spread evenly" is also
  hoverable — WP-D7 §4 render rule). Tags never render.
- **Hard invariant:** stripping the tags from your parsed segments must
  reproduce `answer` byte for byte — numerals exactly, in order, no
  whitespace drift. Test it on every fixture.
- Unknown id (present in the text, absent from `citations`) → render the
  span as plain text, no hover, and `console.warn` once. Never blank a block.

## D8.2 — the hover card

- The bound span is the interactive element: dotted underline in the ink
  colour, no colour change of the number itself (text wears text tokens).
- On hover / focus (keyboard: the span is focusable, `Escape` closes; on
  touch: tap toggles) show a card with: the finding's `display_sentence`;
  its `scope` and `standing` lines; "as of {stamp}"; and a link "Open
  record ↗" to the readable record view (new tab). Use the tab's existing
  card idiom (border-line, rounded, white) — no new design language.
- One card open at a time; it must not be clipped by the report card's
  `overflow-hidden` (portal or positioned outside the clipping container —
  check `InsightReport.tsx` line ~66).
- The "as of" footer, the move caption, and the decline/why renderings are
  unchanged.

## D8.3 — the fallback notice (small, separate, do it)

When `response.retrieval.judge.source === "fallback-threshold"`, the answer
was produced without the selection step (the judge was unreachable — on
2026-09-03 this turned a dead API key into "Bhubaneswar has no findings").
Render a one-line notice above the answer, in the caption style: *"The
selection step was unavailable for this answer; only exact matches are
shown."* Nothing else changes. This is a display of a field the service
already sends, not a behaviour change — and it stops an infrastructure
failure reading as a data finding.

---

## Files in scope (writable) — nothing else

```
frontend/ab-dashboard-main/src/services/discover-api.ts        the type, the URL prefixing
frontend/ab-dashboard-main/src/lib/discover-answer.ts          tag-aware parsing
frontend/ab-dashboard-main/src/lib/discover-answer.test.ts     its tests
frontend/ab-dashboard-main/src/components/insights/**          InsightReport + a new hover-card component
frontend/ab-dashboard-main/src/pages/Index.test.tsx            only if the page test needs the new optional fields
handoffs/WPD8_REPORT.md                                        your report
```

**DO NOT TOUCH:** `DiscoverChat/**` (the service is correct; if you believe
the payload is wrong, log it — the test oracle is `answer_html`),
`Insights/**`, `Ask/**`, `deploy/**`, `PROJECT_PLAN.md`, `LABEL_SHEET.md`,
every `.env`, the Ask tab's components and services. The unchecked-prose
path the frontend already carries (D40 item 5) is out of scope — do not
touch it, do not route Discover text through it. No git operation beyond
read-only `status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. **A DiscoverChat serving the WP-D7 payload is reachable** at the base
   URL you will point the tab at: `curl` one `/chat` turn and confirm
   `answer_tagged` and `citations` are present and non-empty for
   "What should I know about Kalimela?". The `C:\dev\odisha-d7` mirror runs
   it (`python -m uvicorn DiscoverChat.main:app --port 8100`, from the
   mirror's repo root, with working keys in its `Insights/.env`). If the
   service you reach lacks the fields, STOP — it is running pre-D7 code.
2. **Frontend runs from a fresh local mirror** (`C:\dev\ab-dashboard-odisha`,
   re-mirrored from `frontend/ab-dashboard-main` first — mirrors drift), never
   from the Drive path (npm breaks there). `npm install`, `npm run dev` →
   port 8080, `VITE_DISCOVER_API_BASE_URL` pointing at the service.
3. `npm test`, `npm run lint`, `npm run build` all green **before** you
   change anything — record the baseline counts. A pre-existing red is
   logged, not fixed, and not yours.
4. Tree committed, or every dirty path outside your writable set listed in
   your report as not-yours (concurrent WPs: DiscoverChat/Insights sets may
   be uncommitted — leave them).

## Read first (with why)

| File | Why |
|---|---|
| `frontend/ab-dashboard-main/src/components/insights/InsightReport.tsx` | The card you extend; its move captions, the `overflow-hidden` wrapper, the "as of" footer |
| `frontend/ab-dashboard-main/src/lib/discover-answer.ts` + `.test.ts` | The block parser and its existing tests — your tag-aware path must keep every one green |
| `frontend/ab-dashboard-main/src/services/discover-api.ts` | The client, the base-URL convention, the type |
| `DiscoverChat/render.py` | The reference render: what a bound span is, what the hover text contains, the `↗` link — your oracle |
| `DiscoverChat/experiments/answer_compare.json` | 15 real answers with `tagged_text`, `citations` and rendered HTML — build your fixtures from these, not from hand-written samples |
| `handoffs/WPD7_REPORT.md` §3–§4 | What the payload means and why the binding is server-side |

## Gate — green as one command set

- `npm test` green, including new tests: (a) tag stripping reproduces
  `answer` exactly on all 15 fixtures; (b) every `data-finding-id` in a
  fixture's `answer_html` has a corresponding bound span in your render, and
  no extra ones; (c) unknown id → plain text, no crash; (d) missing
  `answer_tagged` → identical output to today's render; (e) fallback notice
  appears iff `judge.source === "fallback-threshold"`.
- `npm run lint` and `npm run build` green.
- **Manual, in the report:** a screenshot of the Kalimela answer with a
  hover card open on a number, and the record view it links to; the same
  for one decomposition-bearing answer ("How is Chikilli doing?"). Keyboard
  focus reaches a span and `Escape` closes the card.
- Ask tab untouched: `Index.test.tsx` green with no assertion changed.

## Report

`handoffs/WPD8_REPORT.md`: baseline vs final test/lint/build counts; the
`record_url` shape found and how it was prefixed; the fixture set used; the
screenshots; anything in the payload that did not match `render.py`'s
behaviour (logged, not fixed); files touched / not touched / not-yours.

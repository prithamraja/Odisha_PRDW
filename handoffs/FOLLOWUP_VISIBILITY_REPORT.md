# Follow-up visibility, executed against PR&DW: REPORT

Brief: `handoffs/FOLLOWUP_VISIBILITY_PATTERN.md`. Everything the pattern calls
portable shipped as written; the four system-specific decisions it hands over
(§7) are answered below, along with three deviations and the evidence for them.

> ## Where everything is
>
> ```
> Chatbot/query_router/interpretation.py        the contract + the two rules   (new)
> Chatbot/main.py                               all five paths stamped; the prose retired
> Chatbot/query_router/echo.py                  docstring: its one external caller is gone
> Chatbot/query_router/router.py                comment: where the carry is reported now
> Chatbot/tests/test_followup_visibility.py     19 tests — the whole backend gate  (new)
> Chatbot/tests/test_context_window_endpoint.py the retired-prose assertion, flipped
>
> frontend/ab-dashboard-main/src/types/chat.ts               Interpretation on the wire
> frontend/ab-dashboard-main/src/services/api.ts             …and on ChatResponse
> frontend/ab-dashboard-main/src/pages/Index.tsx             the escape hatch's re-send
> frontend/ab-dashboard-main/src/components/chat/ChatArea.tsx        passes it down
> frontend/ab-dashboard-main/src/components/chat/MessageBubble.tsx   the thread + control
> frontend/ab-dashboard-main/src/components/chat/MessageBubble.test.tsx  8 tests  (new)
> frontend/ab-dashboard-main/src/pages/Index.test.tsx                    3 tests  (new)
> ```
>
> **Nothing is committed.** The working tree carries the change; no commit, no
> push, no `PROJECT_PLAN.md` edit — that file is PM-owned and shared with a
> concurrent session, so this report is the artefact to slot in.
>
> Re-run everything (from the local mirrors, never the Drive path):
> ```
> cd C:\dev\odisha-prdw-backend
> .venv\Scripts\python -m unittest tests.test_followup_visibility     # 19, no network
> .venv\Scripts\python -m unittest $(all tests.* modules)             # 568 OK / 22 skipped
>
> cd C:\dev\ab-dashboard-odisha
> npx vitest run --testTimeout=30000                                  # 39 passed / 5 files
> npx tsc -p tsconfig.app.json --noEmit                               # clean
> npx eslint <the five changed sources + two test files>              # clean
> ```
> The live browser gate is a standalone script (§5) — it is not checked in,
> because `playwright.config.ts` imports a `lovable-agent-playwright-config`
> package that is not installed in this environment.

---

## 1. For the PM — what changed, in one screen

An officer asks *"What is the total actual expenditure incurred by each GP in
2024-25?"*, then types *"in khordha?"*. Before this change the second answer
looked exactly like a fresh answer: the same shape, the same confidence, and
nothing saying whether the system had narrowed the question on screen or routed
those three words on their own and landed somewhere else. Now:

```
What is the total actual expenditure incurred by each GP in 2024-2025?          ← gray
  │ What is the total actual expenditure incurred by each GP in 2024-2025 (Khordha district)?
  │ ↳ read as a follow-up · Ask as a new question instead
```

Read top to bottom, that is the entire interpretation, and the control at the
bottom re-asks the officer's own words with the conversation context cleared.

**The one place this information used to live has been taken away.** Scope
inheritance appended *"Answered for Khordha, carried over from your previous
question."* to the answer TEXT. The answer body is what an officer copies,
exports and pastes into a report; a system log inside it reads there as noise.
The same fact is now a field beside the answer — and it is stamped by all five
paths that bind a message to context, not by that one.

---

## 2. The five binding paths (pattern §1)

The pattern predicted "several silent paths, and possibly one that was already
handled well." PR&DW had exactly five, and exactly one of them spoke:

| Path | What it does | Was it visible? |
|---|---|---|
| Frame edit | swaps a slot, re-queries the **same** template | no |
| Operation | computes on the table already on screen | partly — `tier: "operation"` |
| Fragment re-route | reads a subject-less fragment (*"in khordha?"*) against the frame: the deterministic drill hop, the re-route of the fragment WITH the frame's question, the tier clarification (D18.P3/D28.3), and the ambiguous-fragment clarification | no |
| Scope inheritance | a new question narrowed to the frame's geography | **yes** — prose + an undo chip |
| Clarification reply | a short reply resumes the question the router paused on | no |

The template was scope inheritance, as predicted: it already named what it
carried and offered the way back. The work was generalising it to the other
four and moving the announcement out of the prose.

---

## 3. The contract as shipped

`Chatbot/query_router/interpretation.py`:

```python
class Interpretation(BaseModel):
    kind: Literal["new_question", "frame_edit", "operation",
                  "fragment_reroute", "scope_inherited",
                  "clarification_reply"] = "new_question"
    anchor_question:    Optional[str] = None
    anchor_template_id: Optional[str] = None
    detail:             Optional[str] = None      # "district → Khordha"
```

on `QueryResponse.interpretation`, defaulting to the standalone reading. The
three properties the pattern asks for hold: the default is `new_question`, every
non-default kind carries an anchor (asserted, §4), and the anchor is read off
the frame the message was **classified against** — `current_frame`, captured at
line ~860 of `main.py` before any handler replaces the store's frame. The store
hands out `model_copy(deep=True)`, so the later `set_frame` cannot reach it.

Answers to the four system-specific questions the pattern hands over (§7):

- **the set of paths** — the five in §2;
- **the kind values** — the pattern's own five, unchanged. PR&DW's paths map
  onto them one for one;
- **the reset mechanism** — already existed: `QueryRequest.reset_context`
  clears frame *and* pending in one call (`ContextStore.reset`), which is
  precisely what the escape hatch needs. No new endpoint;
- **duplicate prose** — one sentence, retired (§1).

### Three deviations, each deliberate

**1. An anchorless bound kind is impossible, not merely untested.** The
pattern's helper returns `Interpretation(kind=kind)` when the frame is None;
ours returns a plain `new_question`. A marker with nothing to anchor to is a UI
with nothing to draw, and the pattern's own default-to-standalone rule says a
half-built reading should fail safe rather than be reported. The frontend still
double-checks (`boundReading` requires `anchor_question`), because a backend and
a UI disagreeing about this is exactly what the live gate exists to catch.

**2. The two CLARIFY outcomes of the fragment path are stamped
`fragment_reroute`, not left standalone.** A tier collision (*"what about
Laxmipur?"* — a block and a GP in the sample) asks *which place*, and the
ambiguous-fragment prompt offers both readings. Both are readings of the
message **against the frame** — the question only makes sense as one — so both
are marked, and the anchor tells the officer which question the choices belong
to. This adds no sixth kind: the pattern says to name kinds after your paths,
and in PR&DW these are outcomes of one path.

**3. `/operation` — the typed operation invoked by tapping a control ON the
table — reports nothing**, while *"total?"* typed into the composer reports
`operation`. Rule 2 generalises from generated text to generated actions: a
control tapped on a table names the table it computes over, nothing was
classified, and there is no other reading it could have had. Same reasoning
retires the marker on `/context/pop`: restoring an earlier frame is not a
message.

`detail` is capped at 60 characters **in the model** (`field_validator`), not
just asserted in a test, so no future call site can widen it. It is never
rendered (pattern §4) — it restates a difference the reader can already see —
but it is on the contract and asserted per path.

---

## 4. Backend gate (pattern §5)

`tests/test_followup_visibility.py` — 19 tests, **no network and no LLM**, but
through the real `/query` handler. Only `classify_followup` and `route` are
stubbed (the two functions that would make paid calls); the registry, the
templates, the DuckDB sample, the drill hop, the pending resolver and the frame
store are all real. A unit test of the helpers would have passed with nothing
wired up at all.

| Gate row | Test | |
|---|---|---|
| Fragment vs a live frame → bound kind, anchor = the *previous* question, non-null `detail` | `test_a_fragment_against_a_live_frame_reports_the_reroute` | ✅ |
| …and the same fragment when the classifier produces the edit | `test_the_classifier_route_to_the_same_place_reports_it_too` | ✅ |
| Word-for-word catalogue question mid-session → `new_question` | `test_a_word_for_word_catalogue_question_is_standalone` | ✅ |
| Tapped chip → `new_question` | `test_a_tapped_chip_is_standalone` | ✅ |
| Operation → `operation`, detail names the operation | `test_an_operation_names_the_operation` | ✅ |
| Frame edit → `frame_edit`, detail names the swap | `test_a_frame_edit_reports_the_swap` | ✅ |
| First message of a session → `new_question` | `test_the_first_message_of_a_session_is_standalone` | ✅ |
| Clarification reply → anchored to the *paused* question | `test_a_clarification_reply_anchors_to_the_paused_question` | ✅ |
| …including a reply we could not use (the re-ask) | `test_a_reply_we_could_not_use_is_still_a_reply` | ✅ |
| Scope inheritance → bound kind **and the retired prose is gone** | `test_scope_inheritance_reports_the_carry_and_the_prose_is_gone` | ✅ |
| Same question with the context reset → `new_question` | `test_the_same_question_with_the_context_reset_is_standalone` | ✅ |
| Back/restore endpoint → `new_question` | `test_the_back_endpoint_is_standalone` | ✅ |
| (added) `/operation` endpoint → `new_question` | `test_the_operation_endpoint_is_standalone` | ✅ |
| The contract itself: default, anchor on every bound kind, degradation, detail cap and phrasings | `InterpretationContractTests` (6) | ✅ |

The anchor test does the thing the pattern warns about explicitly: it asserts
`marker.anchor_question == frame_before.template_question` **and** that the
anchor does not contain "Khordha" — a marker built after the frame was replaced
would name the answer's own question and pass a weaker assertion.

Whole suite after the change: **568 tests OK, 22 skipped** (the opt-in
live-routing classes). Frontend: **39 passed across 5 files**, `tsc` clean,
`eslint` clean on every changed file.

---

## 5. Frontend, and the live browser gate

The thread renders on the **assistant's echo-back**, never on the user's bubble
— the pattern's two reasons both apply here unchanged (user messages are
appended optimistically in `Index.handleSend`, and the user bubble is
right-aligned). The escape control re-sends `message.originalQuery` — what the
officer typed — with `reset_context: true`, and **appends**; the exchange it
corrects stays on screen above it.

Component and page tests (11) cover the frontend checklist. To prove they bite
rather than pass vacuously, the marker was disabled in the mirror
(`boundReading` → always null) and the suite re-run: **5 of 11 failed**, and the
6 that survived are precisely the tests asserting absence. Restored afterwards
and re-verified.

**Live browser gate — 8/8, six consecutive clean runs.** Real backend
(`uvicorn` on a fresh port 8010, real OpenAI key, real `panchayat_1.duckdb`),
real Vite dev server on 8111 pointed at it, chromium driven by a standalone
Playwright script:

```
PASS  a standalone question shows no marker
      anchor line: What is the total actual expenditure incurred by each GP in 2024-2025?
PASS  a fragment is marked as a follow-up
PASS  the marker names the question already on screen
PASS  the correction is a new exchange, not a replacement
PASS  the exchange it corrects survives, marker and all
PASS  the correction itself carries no marker
PASS  a tapped chip is never a follow-up
PASS  no console or page errors throughout
```

The correction is worth reading: re-sent standalone, *"in khordha?"* comes back
as *"I couldn't match that exactly. Did you mean one of these?"* — which is the
honest answer to a bare fragment with no context, and it carries no marker.

Scope inheritance is the one path the browser gate does not reach (see §7), so
it was probed live over HTTP instead, and it behaves end to end:

```
Q1  "What percentage of Gram Panchayats in Khordha uploaded their GPDP in 2024-25?"
    → PLN-004,  interpretation: new_question
Q2  "how much did each GP actually spend in 2024-25?"
    → EXP-001,  "…in 2024-2025 (Khordha district)"
       interpretation: {kind: scope_inherited,
                        anchor_question: "What percentage of Gram Panchayats in Khordha…",
                        detail: "district → Khordha"}
       answer text: the echoed question ONLY — no "carried over" sentence
       first chip:  "Show this across the whole state instead"
```

---

## 6. Traps, and what they cost

**The retired prose HAD a test, and the default suite would never have told
me.** Pattern §6 says to grep the shortest distinctive fragment; grepping
`carried over` found `tests/test_context_window_endpoint.py:229` asserting the
sentence was present. That class is opt-in (`PRDW_LIVE_ROUTING=1`), so it stays
green by skipping — a full-suite pass would have been meaningless here. The
assertion is now inverted (prose absent, `interpretation.kind ==
"scope_inherited"`), and `router.py`'s "the answer says the scope was carried
over" comment was corrected in the same pass.

**One flaky live-gate run, and it was the script, not the product.** The gate
failed once on `Ask as a new question instead` not being found. Cause: my
`settle()` waited for a paragraph count to grow, and the **user's own bubble
uses the same paragraph classes** and is appended optimistically — so it
returned while the request was still in flight, which is exactly the window in
which the control is deliberately hidden (pattern §4). Fixed by waiting for the
typing indicator to detach. Four runs before the fix, six after; the failure has
not recurred.

**A locator that tested the answer instead of the anchor.**
`page.locator("div").filter({hasText: …}).last()` lands on the *innermost*
matching div — the indented block, which holds the answer and the footer but not
the gray anchor line above it. It passed on one run and failed on the next for
reasons that had nothing to do with the anchor. Now scoped to
`div.max-w-2xl`, and the gate prints the anchor line it read.

**Fresh ports, as instructed.** Both servers were started on unused ports and
killed **by port** afterwards (`Get-NetTCPConnection … | Stop-Process`), not by
killing the shell.

**Two live-routing failures are pre-existing, and here is the proof.**
`ConversationEndpointTests` has two failing tests, both failing at the ROUTE:
*"how much was actually spent?"* → `clarify` ("I couldn't match that exactly"),
and *"how much was actually spent in Ganjam district?"* → empty
`query_description`. Neither touches the marker; one of them
(`test_a_question_naming_its_own_scope_keeps_it`) I never edited. They repeat
identically across three runs — so not flakiness — and the decisive check: the
HEAD versions of `main.py`, `router.py`, `echo.py` and the test file were copied
into the mirror and the class re-run, producing **the same two failures, same
assertions, same messages**. They predate this work and are a routing/catalogue
question for whoever owns WP-4's remainders.

One unrelated frontend test, `src/lib/insights-report.test.ts` → "shows no raw
markdown markers anywhere on the page" (the Discover feed), **times out at
vitest's 5s default** on this machine and passes at `--testTimeout=30000`. It
is a render-speed issue in a file this change does not touch.

---

## 7. What is not done

- **`PROJECT_PLAN.md` is untouched** and nothing is committed — both are the
  PM's call, and the plan is shared with a concurrent session.
- **The scope-inheritance row of the live browser gate is not covered by the
  browser.** It needs a paraphrase that both routes reliably AND leaves its
  geography unnamed; the one the existing live test uses no longer routes at
  all (§6). It is covered deterministically in the backend suite and probed
  live over HTTP (§5), which between them exercise the same code — but a
  browser click-through of that path is genuinely missing.
- **The live gate script is not checked in.** It cannot use the repo's
  `playwright.config.ts` (missing package), and a second, standalone Playwright
  setup felt like a decision for the frontend workstream rather than a side
  effect of this change. It is preserved in this session's scratchpad; say the
  word and it lands under `frontend/ab-dashboard-main/`.
- **`followup_classifier._SYS` still describes the AP RTGS domain** (PM-KISAN,
  mandals, Andhra Pradesh schemes) while classifying Odisha panchayat
  follow-ups. Pre-existing, out of scope here, and worth a line on someone's
  list — the classifier is the component whose reading this whole change makes
  visible.

Budget, against the pattern's estimate of ~1 day at roughly 60/40 backend to
frontend: it landed close to that split, with the live browser gate taking about
as long as the frontend code — as predicted.

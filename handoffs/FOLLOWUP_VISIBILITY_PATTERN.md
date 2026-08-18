# Pattern: tell the user when a question was read as a follow-up

A portable spec for any conversational analytics product that keeps a
**conversation context** (a "frame": the last answered question, its bound
parameters, its result table) and silently reads the next message against it.

Reference implementation: AP RTGS Decision Aid, 2026-08-17 —
`AP_FOLLOWUP_VISIBILITY_HANDOFF.md` (spec) and `_REPORT.md` (what shipped, with
gates). This document is the version to hand to a *different* system; it names
the shape and the traps, not this repo's line numbers.

---

## 1. The defect this closes

A conversational data product decides, per message, whether you asked something
new or refined what was already on screen. That decision changes the answer
completely — and it is usually invisible.

The user types **"in kurnool?"**. The system answers a Kurnool question. Did it
narrow the question already on screen, or did it route those three words on
their own and land somewhere unrelated? The answer looks equally confident
either way. Nothing in the response says which happened, and there is no way to
say *"no, I meant that as a new question."*

This is not a routing-accuracy problem. The routing may be right every time.
It is a **legibility** problem: the user cannot tell which question the answer
answers, so they cannot catch the case where the system read them wrong.

### Find your binding paths first

Before writing any code, enumerate every path in your query handler that binds
a message to prior context. In the reference system there were **five**, and
only one of them said so:

| Path | What it does | Was it visible? |
|---|---|---|
| Frame edit | swaps a slot, re-queries the *same* template | no |
| Operation | computes on the table already on screen | partly (a `tier` value) |
| Fragment re-route | re-routes a subject-less fragment together with the prior question | no |
| Scope inheritance | a genuinely new question narrowed to the frame's geography | **yes** — prose + an undo chip |
| Clarification reply | a short reply resumes a paused question | no |

Expect the same shape: several silent paths, and possibly one that was already
handled well. **That one is your template.** In the reference system, scope
inheritance already named what it carried and offered the way back; the work was
generalising that to the other four.

> **Do not assume your frontend can infer this.** A frame edit re-queries the
> same template and returns an ordinary successful answer — byte-for-byte
> indistinguishable from a fresh question that happened to match that template.
> This is a backend field first, a UI treatment second.

---

## 2. Two rules that govern everything

**1. Report, never predict.** The marker appears only *after* the system has
said what it actually did. Nothing in the UI may claim in advance that the next
message will be treated as a follow-up.

This rule kills the most tempting design — a pill above the composer reading
*"Following up on: <question> ✕"*. It was proposed and rejected in review, and
the reasoning generalises: **a frame is live after every answered question**, so
the pill is permanently on, while the actual reading is decided per message by
a classifier. It would be always-on chrome asserting something the system has
not decided yet. Don't build it.

**2. Generated text is never a follow-up.** Suggestion chips, "try next"
prompts, and word-for-word catalogue questions bypass the classifier by
construction. They must render with **no marker at all**. Assert this — a false
marker on a chip tap teaches the user to distrust the true ones.

---

## 3. The backend contract

Return this on every query response. Adjust names to your conventions; keep the
shape.

```python
class Interpretation(BaseModel):
    kind: Literal[
        "new_question",         # routed standalone — the UI renders nothing
        "frame_edit",
        "operation",
        "fragment_reroute",
        "scope_inherited",
        "clarification_reply",
    ] = "new_question"
    anchor_question:    Optional[str] = None  # the earlier question it was read against
    anchor_template_id: Optional[str] = None
    detail:             Optional[str] = None  # short phrase, e.g. "district → Kurnool"
```

Wire it in with three properties:

- **Default to the standalone reading.** Any path that does not bind is then
  correct by omission, and a path you forget to stamp fails safe (no marker)
  rather than lying.
- **Every non-`new_question` kind carries `anchor_question`.** Assert it in a
  test; a marker with nothing to anchor to is a UI with nothing to draw.
- **Capture the anchor BEFORE the handler replaces the frame.** This is the one
  easy bug. Read it off the frame the message was *classified against*, at
  classification time. Read it afterwards and you will report the answer's own
  question as the question it followed up on — a marker that is always
  self-referential and always wrong.

```python
def _interpretation(kind, frame, detail=None):
    if frame is None:
        return Interpretation(kind=kind, detail=detail)
    return Interpretation(
        kind=kind,
        anchor_question=frame.template_question or frame.template_id,
        anchor_template_id=frame.template_id,
        detail=detail,
    )
```

`detail` is a short human phrase — `district → Kurnool`, `sum of subsidy_amount`,
`answered: district` — never a debug dump. Cap it (≤60 chars) in a test.

**Restoration is not a follow-up.** A breadcrumb/back endpoint that restores an
earlier frame returns `new_question`: there is no new message to have been read
one way or the other.

### Retire any duplicate prose

If a path already announces itself inside the answer *text* (the reference
system appended *"Answered for X, carried over from your previous question."*),
delete that sentence once the marker ships. The answer body is what users copy,
export and paste into reports; a system log embedded in it reads as noise. Keep
any path-specific escape affordance — a "show this state-wide instead" chip is
sharper than the generic re-ask and both can coexist.

---

## 4. The UI pattern

**Put the thread in the echo-back — the assistant's restatement of the question
— not on the user's own message bubble.**

```
                                            and in kurnool?     ← plain, untouched

 Assistant · 05:58 PM
 How many PM-KISAN beneficiaries are there in each mandal of Guntur district?   ← gray
   │ How many PM-KISAN beneficiaries are there in each mandal of Kurnool district?
   │ ↳ read as a follow-up · Ask as a new question instead
 [result table]
```

Gray anchor = the question already on screen. Indented beneath it = the question
actually answered. Read top to bottom, that is the entire interpretation.

The reference implementation built it on the **user's bubble** first and it was
wrong for two reasons worth inheriting:

1. **User messages are appended optimistically**, before the answer exists — so
   the marker could only be written retroactively, forcing it into the same
   state update as the answer to avoid a visible pop. On the answer, the field
   is just set at construction and nothing on screen is ever rewritten.
2. **Right-aligned bubbles indent backwards.** The echo-back is left-aligned and
   has room for two full question lines.

### The escape hatch

One control: **"Ask as a new question instead"**, inline in the thread footer.

- It re-sends the **user's original text** with the context reset — in the
  reference system, one existing flag (`reset_context: true`) that clears frame
  *and* pending state, so the classifier never runs. Check whether your backend
  already has this; it probably does.
- Re-send **what the user typed**, not the echoed catalogue phrasing. The echo
  is the system's wording; re-sending it silently substitutes a question they
  never asked.
- **Append the correction, don't replace the original.** Leaving the follow-up
  reading on screen above its correction is what makes the correction auditable.
- Hide the control (not the marker) while a request is in flight.

### What not to show

Don't print `detail` in the footer if the two questions are already stacked one
above the other — `district → Kurnool` restates a difference the reader can see.
Keep the field on the API contract (it is worth having, and worth asserting in
backend tests); just don't render it. Footer type at ~12px; smaller reads as
disclaimer text and gets skipped.

---

## 5. Gate checklist

Backend, one test per row:

- [ ] Fragment against a live frame → bound kind, anchor = the *previous*
      question, non-null `detail`
- [ ] Word-for-word catalogue question mid-session → `new_question`, no anchor
- [ ] Tapped chip / generated text → `new_question`
- [ ] Operation on the current table → `operation`, detail names the operation
- [ ] First message of a session → `new_question`
- [ ] Clarification reply → `clarification_reply`, anchored to the *paused*
      question
- [ ] Scope inheritance → bound kind, and the retired prose is **gone**
- [ ] Same question with the context reset → `new_question`
- [ ] Back/restore endpoint → `new_question`

Frontend:

- [ ] Thread renders anchor + indented answer + control when bound
- [ ] Nothing extra renders when unbound
- [ ] The user's own bubble is untouched
- [ ] The control re-sends the user's original text, with the reset flag
- [ ] The original exchange survives the correction

Live browser, against a real backend — this is the only gate that catches the
backend's reading and the UI's drawing disagreeing:

- [ ] Ask a standalone question → no marker
- [ ] Ask a fragment → marker, anchor shows question 1
- [ ] Tap the control → new exchange, no marker, first exchange intact
- [ ] Tap a suggestion chip → no marker
- [ ] No console or page errors throughout

---

## 6. Traps, all paid for once already

**Testing scope inheritance needs a paraphrase, not a catalogue question.** If
your system has a guard that clears the frame when a message matches a
catalogue question word-for-word (it probably does — it stops "how many X?" from
being read as a count operation), then a word-for-word question *can never*
inherit scope. A test asserting inheritance on one silently tests nothing. Probe
a few paraphrases, pick one that binds reliably, and retry once if your routing
is nondeterministic.

**`getByRole({ name })` in testing-library is an exact match** (Playwright's is
substring + case-insensitive). Change a button label and every
`queryByRole(...).not.toBeInTheDocument()` keeps passing while asserting
nothing. After any label change, grep for the old string.

**Grep the shortest distinctive fragment, not the full phrase.** "No test
asserts this prose" was claimed on a grep for the whole sentence; a test
asserted a four-word substring of it and failed on the first regression run.

**A killed shell is not a killed server.** Stopping a background task may leave
a detached dev/preview server holding the port. The next run fails to bind, the
old process keeps serving the **previous build**, and your browser gate passes
against stale code. Serve each rebuild on a fresh port, or kill by port.

**Separate real failures from routing nondeterminism, with evidence.** If your
router is LLM-backed, identical replays flip a small fraction of questions. When
a regression run fails, check before re-running: does the failing assertion test
*routing* (a template id) or the thing you changed? Does the file pass in
isolation? Does the failure move between runs? Record the reasoning, not just
the eventual green.

---

## 7. Adapting this

The engine-vs-content split: the `Interpretation` contract, the two rules in §2,
the UI pattern in §4 and the gates in §5 are **portable as-is**. What is
system-specific:

- the *set* of binding paths (enumerate yours — §1)
- the `kind` values (name them after your paths; keep `new_question`)
- the reset mechanism (find your existing one before adding an endpoint)
- whether any path already announces itself in prose (retire it — §3)

Budget: in the reference system this was ~1 day, roughly 60/40 backend to
frontend, with the live browser gate taking as long as the frontend code.

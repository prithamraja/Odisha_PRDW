# WP-D7 brief — fast answers: latency, provenance, and the consolidating writer

**Workstream:** Discover. **Nature: BUILD, staged and gated.** Three changes
to DiscoverChat: a cheaper classifier, the inline verifier replaced by
checkable provenance plus an offline audit, and a writer that turns the
judge's selections into one consolidated narrative — every figure and claim
in it citing the finding it came from, every citation mechanically verified.
**Authored:** PM, 2026-09-01; revised same day (operator dropped the compact
renderer and progressive rendering in favour of the consolidating writer).
Not yet registered in `PROJECT_PLAN.md`; D-numbers to be assigned by the
operator.

**Operator rulings this brief encodes (2026-09-01):**

1. **Classifier moves to `gpt-5.5-nano`** for cost and speed — behind a
   repeated gate, because of the F1 lesson (a small model once returned
   all-null structured output on ~25% of calls, silently).
2. **The inline verifier is dropped.** REVISES the WP-D4 pattern as applied to
   DiscoverChat turns (needs its own D-number). Per-turn prose is guarded by
   mechanical checks only — and those checks grow (ruling 3). The verifier
   moves offline as a sampled audit with a reported drift rate.
3. **The writer consolidates; it no longer only introduces.** REVISES D42
   ruling 6 ("the LLM writes only connective prose") — needs a D-number. The
   judge's selected findings (median 3, max 6; `ANSWER_CAP` 12 is a ceiling,
   not a typical size) go to `gpt-5.6-sol` with the operator's prompt
   (Appendix A), which asks for overlapping findings to be consolidated into
   a small number of patterns told as one narrative. Three guards make this
   safe without a verifier: **(a) citations** — every figure and claim tags
   the finding id it came from; **(b) the citation check** — every numeral
   in the prose must appear in the stored sentence of the id it cites, every
   cited id must be in the answer set, and an uncited numeral is a failure;
   **(c) no derived figures** — the writer may not compute new numbers
   (percentages, sums, differences) from the findings. Any check failure
   falls back to the bare glossary-translated sentences — the existing path.
4. **Hover-to-source on every datapoint.** Citations render as hover
   elements showing the stored sentence, its coordinates and run stamp, with
   a link to the raw record (D7.2). This is the user's validation mechanism
   and the reason the citations must be checkable, not decorative.
5. **Dropped from the earlier draft:** the deterministic compact renderer
   (the writer now does the shortening) and progressive rendering (the
   operator accepts ~20–25 s to first paint: classify + embed + judge +
   write, no verifier wait, versus ~60 s today).

**Concurrency:** check `git status` for WP-D4b's set (per the WP-D6 brief's
list) — touch none of it. **This WP must start from a committed baseline
including the WP-D6 work** — if the WP-D6 file set (WPD6_REPORT §6) is not
committed, STOP and report.

---

## D7.0 — classifier on nano

`CLASSIFIER_MODEL` becomes an env-pinned constant defaulting to
`gpt-5.5-nano` (D17 discipline: one constant, budget checked alongside).
Rules-first routing is unchanged; only the LLM fallback classification moves.

**Gate D7.0:** the full routing suite — decompose routes (8/8), why-reframes
(6/6), lookups (6/6), shape-questions (2/2) — run **four independent times**
on nano, all green all four; plus a non-empty-output assertion on every
classify call (the F1 check: a null or unparseable classification is a gate
failure, not a silent fallback). Reversion is the env var; document it.

## D7.1 — verifier out of the turn, into the audit

- Inline verification OFF for turn prose (config default, not code
  deletion — the verifier module stays for the audit).
- **Offline audit:** a script that samples logged writer outputs from
  `calls.jsonl` (all below a volume threshold; a stated sample above it),
  runs the verifier over each with the writer's full context (the T4
  lesson), and reports a **drift rate** with the flagged texts. Runs as part
  of the offline gate; its result is a number in the gate output, not a
  pass/fail — the operator judges the rate. With ruling 3 the writer now
  restates findings, so this audit is the only check on *qualitative* drift
  (a limitation narrowed, a subset total generalised); the citation check
  covers numbers, not meaning. State this in the README.

**Gate D7.1:** a turn with writer prose completes with no verifier call in
its trace; the audit runs over the existing logged writer calls and reports
its rate; mechanical checks demonstrably still fire (one seeded violation
caught).

## D7.2 — provenance: the record endpoint

- `GET /record/{id}` returns the stored record — sentence as stored and as
  glossary-translated, coordinates, values, engine score, run stamp — as JSON
  and as a minimal readable HTML view. Both corpora (`1-…`, `d1-…`).
  Read-only, same corpus the chatbot serves; no auth question opened.
- The answer payload carries, per citation, the id and this URL (D7.3
  supplies the citations; the hover UI is the operator's frontend side).

**Gate D7.2:** every id cited in every suite answer resolves (200, correct
record); an unknown id 404s; the record view carries the run stamp.

## D7.3 — the consolidating writer with checkable citations

**Input to the writer:** the judge's selected findings, each as
`[id] glossary-translated sentence` — nothing else. No scores, no coverage
notes, no "not in the ranked shortlist" (the prompt's "ignore ranking
metadata" line is belt-and-braces; the braces are that the metadata is never
sent). Decompositions included on equal footing, with their scope note. The
context brief (WP-D5 ruling 8) precedes the prompt, verbatim; the run date
is supplied so the prose can say "as of".

**The prompt:** Appendix A, the operator's text, plus the two PM additions
marked there (citation tagging; no derived figures). Nothing else in the
prompt — no writing rules beyond those lines.

**The citation check (`checks.py`), blocking, in this order:**

1. Parse `[id]` tags. Every id must be in the answer set — an unknown id
   fails.
2. Every numeral in the prose (after normalising Rs/crore/lakh/percent
   spellings — reuse the numeral normaliser the nothing-invented check
   already has) must appear in the stored sentence of a finding cited
   **in the same sentence** of the prose. A numeral cited to a finding that
   doesn't contain it fails; an uncited numeral fails.
3. The causal scan (prose_gate) over the prose — unchanged, blocking.
4. Every finding in the answer set must be cited at least once — a finding
   the judge selected but the writer silently dropped is a failure (the
   judge already picked the smallest sufficient set; omission is loss, not
   concision).

On any failure: regenerate once; on second failure, render the bare
glossary-translated sentences (existing path) and log the failed prose with
its reason. The fallback rate is reported.

**Rendering:** the tags are plumbing and never appear on screen. **The
number itself is the hover target**: the renderer binds each numeral to the
cited finding whose stored sentence contains it — the same match the
citation check computes in step 2 — and wraps the numeral (or, for a
non-numeric claim, the phrase the tag follows) in a hover element carrying
the stored sentence, its scope and run stamp, plus the D7.2 link. The API
returns the prose with tags and a per-id record map; the hover UI is the
operator's frontend side, but the service ships a reference HTML render so
the behaviour suite can exercise it end to end.

**Gate D7.3:** over the full suite's live turns — zero citation-check
failures reaching the user (fallbacks counted and reported); 605-numeral
class traceability holds on the new prose (every numeral cited and matched);
every selected finding cited; causal scan green; **before/after table of 15
answers** (old bare sentences vs new narrative, including ≥3 with
decompositions and 1 evenness case) for the operator to read — narrative
quality is the operator's acceptance, not the suite's. Measured latency:
p50/p90 time-to-complete, against today's ~60 s baseline; target p50 ≤ 30 s.

---

## Files in scope (writable) — nothing else

```
DiscoverChat/**                  the three changes, their tests, README
handoffs/WPD7_REPORT.md          your report
```

**DO NOT TOUCH:** everything under `Insights/` (stored sentences, corpora,
embeddings and the prose gate do not change), `Ask/**`, `LABEL_SHEET.md`,
`PROJECT_PLAN.md`, every `.env`, `.gitignore`. WP-D4b's set per its list.
Bugs found: log, don't fix. No git operation beyond read-only
`status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. WP-D6 file set committed; tree otherwise clean except WP-D4b's set and
   PM-edited handoffs. Any other dirty path → STOP.
2. Local-mirror execution only; re-mirror first. **Sweep for existing work
   before building anything** (the WP-D6 §0 lesson): check the mirrors and
   `git status` for anything already done against this brief.
3. Pinned SHAs per WPD6_REPORT §6 (all nine) plus `decompose_corpus_stamp.json`
   present. Mismatch → STOP.
4. `Insights/.env` keys present; `gpt-5.5-nano` reachable (one probe call) —
   unreachable → STOP and report rather than substituting a model.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD6_REPORT.md` | Current state: the re-aimed tests you extend, the gate list you grow, §0's lesson |
| `DiscoverChat/assemble.py`, `writer.py`, `checks.py`, `glossary.py`, `gates.py` | The layers D7.3 replaces and extends; the checks that must stay green |
| `DiscoverChat/context_brief.py` | The context brief that precedes the writer prompt (ruling 8) |
| `DiscoverChat/experiments/logs/calls.jsonl` | The measured baseline (verify median 41.3 s; judge 6.4 s; write 12.0 s) and D7.1's audit input |
| `handoffs/WPD4_REPORT.md` | What the verifier caught (3 qualitative drifts in 15 packets) — the class of error the audit must keep measuring now that nothing catches it inline |
| `DiscoverChat/config.py` | Where every new constant and default lives; env-override conventions |

## Report

`handoffs/WPD7_REPORT.md`: the three gates with numbers; the nano routing
matrix (4 runs × 22 questions); the audit's drift rate over existing logs;
the citation-check results (failures, fallbacks, reasons); the before/after
narrative table; measured latency p50/p90 before and after; WP-D6-style
close-out with pinned SHAs re-verified.

---

## Appendix A — the writer prompt

Operator's text, verbatim. The two bracketed lines are PM additions for the
operator to approve or strike; nothing else may be added.

> Turn the analytical findings below into clear, concise prose for a senior
> government official.
>
> Do not rewrite each finding separately. Identify overlapping or repeated
> findings, consolidate them into a small number of underlying patterns, and
> explain those patterns as a coherent narrative. Do not make causal claims
> ever. Do not fabricate or overstate data.
>
> Preserve important numbers and exceptions where useful. Ignore ranking
> metadata such as "not in the ranked shortlist." Avoid database-style
> language and do not infer causes that are not supported by the findings.
>
> [PM addition 1 — citations: After every figure and every claim, tag the
> finding it comes from with its id in square brackets, exactly as given,
> e.g. [1-00235]. A sentence drawing on two findings carries both tags.]
>
> [PM addition 2 — no derived figures: Use figures exactly as they appear in
> the findings. Do not compute new numbers — no percentages, sums, or
> differences that are not stated in a finding.]
>
> Return only the finished prose.

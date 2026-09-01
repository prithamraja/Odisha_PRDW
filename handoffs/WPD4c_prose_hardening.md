# WP-D4c brief — prose hardening: cleaned-template fallback + ratified fixes

**Workstream:** Discover. **Nature: BUILD, small closeout.** Implements the
rulings already made on the WP-D4b report (D44, D45) — nothing here is a new
design decision. One rebuild of the sidecar at the end. **Authored:** PM,
2026-09-01.

## The changes, all pre-ratified

1. **Cleaned-template fallback (D45, the headline).** When both attempts fail,
   the record no longer carries the raw feed sentence — it carries a
   **deterministic cleaned rendering** of it: variable names translated through
   the glossaries already in `insight_prose_config.py`, `(varies)` expanded to
   say what actually varies, exception-list grammar fixed ("and 1 others" →
   name them, or "and N others" with correct grammar), codes left as codes
   (no decode exists — never invent one). Pure code, no model call, so the
   can't-be-wrong property of the fallback is preserved. Target quality, by
   example:

   - Rank 25 raw: *"Across most measure values (10/18), (varies) is evenly
     distributed across gp_name values. Uneven only in: n_plans (not evenly
     spread); sanctioned_total (not evenly spread); n_completed (not evenly
     spread) and 5 others…"*
     → cleaned: *"For 10 of 18 measures, values are spread evenly across the
     Gram Panchayats. Not evenly spread: number of plans, total sanctioned
     amount on record, number of completed works, and five others — this is
     about how totals are spread, not about how much any one place spends."*
   - Rank 2 raw: *"Across all temporal_grain values, activity_linked_expenditure
     is increasing over (varies)"*
     → cleaned: *"Spending linked to planned activities is rising in all three
     time views — by month, by quarter and by year."*

   Everything in a cleaned sentence must come mechanically from the finding's
   own fields + the glossaries. No figures added, no interpretation, no
   "so what". The fallback's detail stays empty.

2. **The two check false positives (D44 ruling 2):** the numeral variant
   accepts a dropped trailing `.00` (`Rs 14.00 lakh` ↔ `Rs 14 lakh`); the name
   roster skips a flagged name that also appears case-insensitively in the
   packet's own text (the "Tied" case).

3. **Top/bottom overlap guard (D44 ruling 5):** skip `bottom_values` when the
   breakdown has ≤ 7 groups (or take the tail from the complement of the head)
   so no packet lists a group as both highest and lowest.

4. **Verifier budget probe (D44 ruling 5):** the verifier ceiling gets the
   same D17-style pre-run probe the writer has, so starvation is prevented,
   not just retried.

## Files in scope (writable) — nothing else

```
Insights/src/phase5e_insight_prose.py          the build step (this workstream's own file)
Insights/src/insight_prose_config.py           its constants + glossaries
Insights/metainsights/insight_prose.json       rebuilt sidecar
Insights/reports_prdw/check_insight_prose.py   checker updates
Insights/reports_prdw/wpd4c_run/**             run + gate logs
handoffs/WPD4c_REPORT.md                       your report
```

**DO NOT TOUCH:** everything else — the standing WP-D4b list applies verbatim
(existing `Insights/src/` files beyond the two above, `Insights/prose_trial/`,
the pinned candidate/feed files, WP-D5's paths, `Ask/`, packs, `Data/`,
`PROJECT_PLAN.md`, `.env`). No git beyond read-only.

## Preconditions

The WP-D4b list applies, with both standing exclusions (D43 concurrency for
WP-D5's paths; D44 ruling 1 for the PM's dispatching files). Pinned-set SHA
check as before, ignoring `insight_prose.*` and `retrieval_corpus.*`.

## Tasks

### T1 — The cleaned renderer
**Do:** a deterministic function: finding record → cleaned sentence, per
change 1. Wire it as the fallback lead.
**Done when:** an offline test (no API) renders **all 32 current feed
sentences** through it and asserts: no raw database token survives (the T3
banned-token scan, reused), no `(varies)`, no "and N others" without a
number-word or names, output non-empty for every finding.
**Trap:** don't "improve" the facts while cleaning — same counts, same
members, same claim, better words only.

### T2 — The three small fixes
Changes 2–4 above, each with a unit test reproducing the measured case from
the WP-D4b report before the fix and passing after.

### T3 — Checker updates
The fallback assertion becomes: every fell-back record's lead **equals the
recomputed cleaned rendering** (byte-exact — the renderer is deterministic and
travels in the step, so replay recomputes it). Cleaned fallbacks also pass the
banned-token check. All other assertions unchanged.

### T4 — Rebuild
One full build. Report the quality profile against the D44 range (21–24
first-pass of 32). If a fallback occurs, show its cleaned text prominently —
that's the feature. **The operator's gate-6 read (ranks 16–32) happens on
THIS rebuild's output**, not WP-D4b's.

## Spend guard

Cap **150 calls** (one build ≈ 55; headroom for a second if a defect forces
it — D44 ruling 4). Ceilings unchanged (16k / 8k / 4k). Usage on every call.

## Gate

1. T1 offline test green on all 32 sentences; T2 unit tests green.
2. Checker green on the rebuilt sidecar (Drive-replayable parts on Drive).
3. Quality profile within or explained against the D44 range.
4. `git status` = writable set + standing exclusions disclosed.
5. **Operator gate-6 read** on the rebuilt prose closes WP-D4b and WP-D4c
   together.

## Report — `handoffs/WPD4c_REPORT.md`

§0 gate table · §1 what changed, with before/after cleaned-sentence samples
for every finding class touched (`(varies)` measure, `(varies)` breakdown,
"and N others", code-named, plain) · §2 rebuild profile vs the D44 range ·
§3 what the safety layers caught this run · §4 cost · §5 defects (logged, not
fixed) · §6 decision journal · §7 self-audit.

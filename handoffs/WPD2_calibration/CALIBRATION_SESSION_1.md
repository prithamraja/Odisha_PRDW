# Discover calibration session 1 — record

**Date:** 2026-08-14. **Participants:** operator (SME, D20) + PM. **Input:**
package v2, 33 findings (WP-D2b). **Labels:** in `labeling_sheet.csv`
(operator's rulings; PM transcription).

## Tally

| | real | already-known | spurious |
|---|---|---|---|
| view1 (15) | 6 | 3 | 6 |
| view2 (15) | 7 | 4 | 4 |
| view3 (3) | 2 | 0 | 1 |
| **total (33)** | **15** | **7** | **11** |

One label is a PM proposal pending operator confirmation: view2 #7 (spurious —
the row was omitted from the session grouping in error).

## Operator rulings that shape the engine (the WP-D2c calibration actions)

1. **Definitional-pair exclusion** (view1 #3–6): measure×dimension pairs that
   are circular by construction (`fund_tied_total` × fund_component;
   `trainees_total` × work_type) must be excludable per view config and
   excluded. Mechanism: an `excluded_pairs` list on `ViewConfig`.
2. **Twin deduplication**: OUTSTANDING_1 + ATTRIBUTION with the same highlight
   and member set are one finding (4 pairs in this run); near-twins that differ
   only by breakdown/measure but tell one story (view1 #1/#2, view2 #1/#15)
   should be collapsed or co-presented. Ranking-overlap tuning.
3. **EVENNESS reframing** (view1 #1 — operator: "very interesting… make the
   text pop"): deterministic template rewording. For a signed money measure:
   lead with the magnitude, state absence-of-concentration as the message
   ("the shortfall belongs to everyone — no GP drives it"). The exception
   clause must not read as "the excepted category behaves well" — it is about
   distribution shape. Template + phase5b framing rules, both gated.
4. **Per-GP intensity denominators** (view2 #2/#5/#10/#12 — operator: "let's
   think about a denominator"): add AVG-agg intensity measures (e.g.
   `payment_amount` per GP-month) so place rankings can be size-corrected;
   AP's `benefit_amount_mean` is the precedent (note its `extremum_ratio`
   implications). Size-total findings stay minable but the report prefers the
   intensity phrasing.
5. **Known-events context** (view2 #13/#14 — operator: "COVID"): a small
   deterministic events table (COVID lockdown Apr–Jun 2020, first wave, …) that
   reading notes cite when a change-point or trend window overlaps a known
   event. Events as data, not prompt freestyle.
6. **Linkage-vs-spending reframe** (view2 #1/#4/#11/#15): activity-linked
   expenditure trends must be presented as recording-completeness improvement
   unless corroborated by cashbook growth (payments are flat by FY while links
   grew 30 → 2,122). Deterministic framing rule keyed to the measure.
7. **Degenerate-measure guard** (view3 #1/#2 — operator: keep, reframed):
   trends on measures with almost no non-zero events (17 completions ever)
   route to the **data-quality annex** ("completion recording ceased after
   2022-23"), not the performance narrative. Candidate engine guard: minimum
   non-zero support for temporal patterns, with the displaced finding logged
   as data-quality rather than dropped.
8. **Publication holds**: view1 #8 (output_type codes) held until the decode
   team-ask lands. view1 #12 (Chikilli) kept in the report by operator choice.

## Regression baseline

The labeled sheet is now the baseline for a Discover regression gate: after
any config/engine/prose change, re-mine and assert that no labeled-spurious
*class* (definitional pairs, size-total rankings without intensity framing,
sub-support temporal trends) re-enters any top-15. To be codified as part of
the Discover gates command (WP-D2c/WP-D3).

## Workstream-gate status

WP-D2's gate ("no nonsense findings in top ranks") is **not yet closed**: 11
of 33 top-rank findings were labeled spurious. It closes when WP-D2c applies
actions 1–7 and a re-mine + re-rank shows top-15s free of the labeled-spurious
classes, verified against this baseline.

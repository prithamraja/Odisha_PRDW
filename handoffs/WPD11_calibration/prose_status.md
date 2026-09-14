# WP-D11 prose status — the fallback rate, and what actually causes it

A `fell-back` finding is NOT an empty section: the emitter ships the
deterministic engine sentence instead of the model's. The brief's stop
condition ("the prose step's verifier shows silently empty sections") is
therefore NOT met — all 50 findings carry text. What follows is a quality
regression for the calibration session, and one concrete WP-D11 defect.

| run | findings | first-pass | regenerated | fell-back |
|---|---|---|---|---|
| WP-D4c run 1 | 32 | 24 | 8 | 0 |
| WP-D4c run 2 | 32 | 21 | 10 | 1 |
| **WP-D11** | **50** | **16** | **22** | **12** |

## It is NOT "profile dimensions in general"

The first reading of these numbers — that a profile dimension makes a finding
*about a kind of Gram Panchayat* (§12.5's own phrase) and that this tempts the
writer into causal language — is **not supported by the data**, and is
recorded here because it was the author's first conclusion and it was wrong:

| | findings | fell back | rate |
|---|---|---|---|
| involve a profile dimension | 32 | 8 | 25% |
| involve none | 18 | 4 | 22% |

Profile findings fall back at the same rate as everything else, and their
first-pass rate is BETTER (13/32 = 41% against 3/18 = 17%). Causal drift
appears in only 2 of the 12 fallbacks. If "about a kind of GP" were the
mechanism, `social_composition` would be the worst dimension. It is the best:

| profile dimension | in findings | fell back | rate |
|---|---|---|---|
| `social_composition` | 18 | 0 | 0% |
| `gp_size` | 14 | 8 | 57% |

## It IS `gp_size`, and the cause is this WP's band labels

`gp_size` carries 8 of the 12 fallbacks and appears in 9 of them; it fails at
**57%** where `social_composition` fails at 0%. The verifier's objection is the
same sentence three times over:

> claim: "GPs with **populations** of 10,000 and above show the shift later"
> missing: *The source identifies the exception only as the gp_size category
> '10,000 and above'; it does not define gp_size as population.*

> claim: "the under-2,500 and 10,000-plus **population** groups"
> missing: *Source Material 1 identifies these only as gp_size values and does
> not define gp_size as population groups.*

The writer is right — `gp_size` IS banded population, and this WP's column
glossary says so. The verifier is also right — its Source Material carries the
band LABEL and not the glossary, so "population" is an unverifiable gloss.
The two disagree because of a choice made in this WP: **the band labels are
bare numbers.** `'Under 2,500'`, `'2,500 to 5,000'`, `'5,000 to 10,000'`,
`'10,000 and above'` name no unit, so any writer describing them has to supply
one, and whatever it supplies is unsupported.

`social_composition`'s values — `'ST-majority'`, `'SC-majority'`, `'Mixed'` —
are self-describing, need no gloss, and produce no fallbacks. That contrast is
the evidence.

### The fix, and why it was not applied here

Label the bands with their unit: `'Under 2,500 people'`, `'2,500 to 5,000
people'`, and so on. §12.3 fixes the CUT POINTS, not the label strings, so
this is a labelling change rather than a change to a signed definition.

It was not applied in this WP because the label is the categorical domain
value: it is written in `derived_columns.sql`, asserted in `validation.yaml`
CHECK 5, recorded in `crosswalk.csv`, and embedded in every mined candidate.
Changing it invalidates the candidate set and forces a rebuild, a full
re-mine (view1 alone is 2.4 h), a re-rank and a complete edition
regeneration including another ~124-call prose build. That is the operator's
call, not the agent's — raised as a proposed amendment in WPD11_REPORT §9.

## The other causes, for completeness

- **Writer drift onto facts the packet does not carry.** view1 rank 5's first
  attempt invented an 'Activity Approved' story with five figures absent from
  its source material. Both checks and the verifier caught it.
- **The numeral checker rejecting arithmetic on packet figures.** A writer
  summed two shares it was given (40.8% + 37.0%) and quoted 77.8%, which is
  not literally in the packet. Pre-existing behaviour, not new.
- **Causal drift**, in 2 of 12 — including one that reached for transaction
  volume as an explanation of a spending concentration. The size-share block
  is labelled "the volume base, not a performance figure" and the verifier
  held the line. Rule 4b / D41, working.

## By view

| view | first-pass | regenerated | fell-back |
|---|---|---|---|
| view1 | 1 | 11 | 3 |
| view2 | 4 | 3 | 6 |
| view3 | 6 | 2 | 1 |
| view4 | 5 | 6 | 2 |

## Every fallback

- **view1 rank 5** — EVENNESS, `overspend_vs_sanction` by `district_name` (ext `asset_category_label`)
  - checks failed: none; verifier: fail
  - verifier: The source establishes a total underspend relative to sanctions and says the reason for the gap is not established. It does not establish that pending bills, incomplete works or unspent sanc
- **view2 rank 6** — LAST_TWO, `payment_amount` by `gp_size` (ext `fiscal_year`)
  - checks failed: none; verifier: fail
  - verifier: Source Material 1 identifies these only as gp_size values and does not define gp_size as population groups; the category meaning is therefore not explicitly supported.
- **view2 rank 10** — TREND, `activity_linked_expenditure` by `month` (ext `gp_size`)
  - checks failed: ['a_numerals']; verifier: pass
- **view2 rank 19** — TOP_TWO, `activity_linked_expenditure` by `gp_size` (ext `fiscal_year`)
  - checks failed: none; verifier: fail
  - verifier: The source provides voucher-volume shares, but defines them as "the volume base, not a performance figure" and does not establish that transaction volume explains the expenditure concentrati
- **view2 rank 20** — OUTSTANDING_1, `payment_count` by `block_name` (ext `fiscal_year`)
  - checks failed: none; verifier: fail
  - verifier: The source says Bhubaneswar has the highest payment_count in 5 of 6 fiscal years, with no clear pattern in 2024-2025; "consistently higher" weakens or omits that exception.
- **view3 rank 24** — LAST_TWO, `(varies)` by `gp_size` (ext `measure`)
  - checks failed: ['a_numerals']; verifier: pass
- **view1 rank 26** — LAST_TWO, `overspend_vs_plan` by `output_type_label` (ext `activity_for_label`)
  - checks failed: none; verifier: fail
  - verifier: Source Material 1 establishes that the output-type codes have no descriptions on file, but it does not state that the data cannot determine whether the gaps reflect pending works, incomplete
- **view2 rank 27** — CHANGE_POINT, `sanctions_count` by `month` (ext `gp_size`)
  - checks failed: none; verifier: fail
  - verifier: The source identifies the exception only as the gp_size category “10,000 and above”; it does not define gp_size as population.
- **view1 rank 35** — OUTSTANDING_LAST, `gen_amount` by `tied_untied` (ext `fiscal_year`)
  - checks failed: none; verifier: fail
  - verifier: The sources support that the finding covers all records in the view and provides aggregate totals, but they do not explicitly state that the data cannot identify a particular Gram Panchayat 
- **view4 rank 36** — OUTSTANDING_1, `(varies)` by `gp_size` (ext `measure`)
  - checks failed: none; verifier: fail
  - verifier: The source identifies the 48.6% as the group's share of the activity volume and says it is not a performance figure, but it does not establish that the volume base is not an explanation for 
- **view4 rank 42** — TOP_TWO, `(varies)` by `gp_size` (ext `measure`)
  - checks failed: none; verifier: fail
  - verifier: The source says that 2,500 to 5,000 and 5,000 to 10,000 lead across 45 of 60 measures, but it does not establish an ordering between those two groups.
- **view2 rank 44** — LAST_TWO, `(varies)` by `gp_size` (ext `measure`)
  - checks failed: none; verifier: fail
  - verifier: The source identifies these categories only as gp_size values; it does not define gp_size as population. The supported wording is that “10,000 and above and Under 2,500 are lowest in (varies

# Place profile sheets — specification

**Status: SIGNED by the operator, 2026-11-24 (D76). Amended the same day,
after the build was reviewed (D77) and for the serve package (D78).** All the
rulings are in §11. Two of the first nine changed the draft: the operator
dropped the code-set "notable" marks (R5 — the model chooses what to use) and
the fixed count note on the by-year list (R9). The amendments correct one
definition (E3, the money on abandoned works), settle five points of wording,
and record how the sheets reach an answer.
**Workstream:** Discover. **Authored:** PM, 2026-11-24. **Decisions:** D75, D76,
D77, D78.
**Read by:** the coding agent, through the briefs: WP-D14 build
(`handoffs/WPD14_profile_build.md`, executed and accepted, D77), WP-D14b fixes
(`handoffs/WPD14b_profile_fixes.md`), WP-D15 serve
(`handoffs/WPD15_profile_serve.md`), then WP-D16 front end (not yet written).
**The sentence patterns are Appendix A of this spec.** They were first written
as Appendix A of the WP-D14 brief; that copy is history and this one is
current.

How to read it: §0–§2 say what a sheet is and the rules it obeys. §3–§7 define
every figure on it. A name in `code font` is a column in the views the insights
are already built from; the operator can skip those and read the plain names.

---

## 0. In brief

A **profile sheet** is a fixed set of facts about one place: a Gram Panchayat,
a block, a district, or the whole state. Every place gets the same sheet. It is
built by code in the same run that mines the insights, and it is fetched by the
place's official code when a question is about that place. It is never found by
search.

Each sheet is **one main row of single figures** (activities, planned, spent,
the share spent, where the place stands among its peers) **plus a few short
lists** (by year, by focus area, by money source, member places). Every figure
comes with a **ready-made sentence** and an id, so the existing rule — every
number in an answer must trace to a stored sentence — works unchanged and the
writer still works out no number of its own.

## 1. Why this exists

1. **Half the questions are "tell me about X".** Of the 31 different questions
   ever typed into the live service, 16 ask for a profile and 9 of those name a
   place. Thin evidence (mostly our own demos), but consistent.
2. **Today's stored data cannot answer them well.** For "What should I know
   about Kalimela?" (2026-11-23) the judge picked 16 records. All 16 are
   breakdowns, nearly all of them *inside* Kalimela, and none is a mined
   pattern. Almost nothing among them says how Kalimela compares with other
   Gram Panchayats, puts planned beside spent, or gives the share spent. A raw
   model reading the data files gave a clearly better answer, and
   its headline figures were verified against the files (PM, 2026-11-24).
3. **At state scale the gap gets worse, by design.** The signed plan for
   statewide data (`Insights/DISCOVER_VIEW_MAPPING.md` §6) stops mining
   Gram Panchayat and block as breakdowns, because 6,800 values cannot be
   mined. Per-place breakdowns also cannot stay in the search: there are about
   300 per Gram Panchayat today, which is about 2 million statewide.
   The profile sheet is where facts about one place live at state scale.
4. This is proposal (4) of D73 — "a code-built fact sheet of totals" — reopened
   by the operator on 2026-11-24.

## 2. Rules every sheet obeys

1. **Fetched by code, never searched.** A sheet has no search vector.
2. **Built only from the views the insights are built from**:
   `view1_activity_lifecycle`, `view3_gp_performance` and `view4_gp_profile`.
   (`view2_geo_month_cube` is not read: ruling R3 put the by-year list on
   `view3`.) No new reading of the raw files and no change to the view pack in
   this version. So a sheet and a mined insight cannot disagree.
3. **Every number is worked out at build time**: values, shares, ranks, middle
   values. The service and the writer compute nothing.
4. **Each level is computed from its own records.** A block's share spent is
   the block's spent divided by the block's planned — never the average of its
   Gram Panchayats' shares. (The views' own rule: no rate is stored, only its
   two parts.)
5. **The four money bases keep their names**: PLANNED, SANCTIONED, SPENT,
   CASHBOOK (mapping doc §3). A figure that combines two bases says so in its
   name ("spent as a share of planned cost").
6. **Set-based build.** One grouped query per level for each part of the sheet.
   No loop over places. The work grows with the data, not with the number of
   places.
7. **Same run, same stamp.** Sheets carry the same candidate-set id and
   "as of" date as the insights corpus they were built beside. The service
   refuses a sheet store whose id differs from the corpus's.
8. **Data oddities are logged and shown, not fixed** (mapping doc §8). A sheet
   reports what the views hold. Oddities go under "Records to check" (§5 H)
   and in §12.
9. **Facts only in the ready-made sentences.** No advice, no cause, no word of
   judgement ("only", "poor", "strong").
10. **No wall-clock values.** "Latest year" means the latest fiscal year in the
    data, never today's date.

## 3. Which places get a sheet

| Level | Key | Sample | Statewide |
|---|---|---|---|
| Gram Panchayat | `gp_lgd_code` | 20 | about 6,800 |
| Block | `block_code` | 16 | 314 |
| District | `district_code` | 9 | 30 |
| The whole (state; today, the sample) | the fixed key `all` | 1 | 1 |

- The list of places comes from the Gram Panchayat master, as `view3` and
  `view4` do, so **a place with no activity still gets a sheet** (zeros).
- Every sheet names its parent (a Gram Panchayat's block and district; a
  block's district) by code and by name.
- In the sample, 13 of the 16 blocks hold one Gram Panchayat, so for those the
  block sheet and the Gram Panchayat sheet show the same figures. That is
  correct, and it stops being true statewide.
- Four names are both a Gram Panchayat and a block in the sample (Bheden,
  Boipariguda, Kalimela, Laxmipur). **Ruling R4: the question is answered for
  the block, unless it clearly says it is about the Gram Panchayat.** This is
  built in the serve brief (WP-D15). The build makes both sheets regardless.

## 4. Peers and standing

"Standing" is where a place's figure sits among comparable places.

**Peer groups** (ruling R1):

| Sheet for a | is compared with |
|---|---|
| Gram Panchayat | (a) the Gram Panchayats in its block, (b) those in its district, (c) all in the state |
| Block | (a) the blocks in its district, (b) all blocks in the state |
| District | all districts in the state |
| The whole | nothing |

**Stored for every ranked figure, for every peer group:** rank from the
highest, rank from the lowest, number of peers, number tied with it, the middle
value (median) of the group, and which quarter of the group it falls in.

**Which peer group a sentence uses:**
- A peer group with **fewer than 5 members gives no standing** (ruling R1).
- The sentence uses the *smallest* group that has at least 5 members. Statewide
  that is the block (about 22 Gram Panchayats). In the sample it is the whole
  sample, because no block or district holds 5.
- With **50 or fewer** peers the sentence gives the exact place: "the 5th
  lowest of 20 Gram Panchayats". With **more than 50** it gives the quarter:
  "in the lowest quarter of the 6,800 Gram Panchayats in the state".
- Statewide, a Gram Panchayat sentence gives its place in the block and its
  quarter in the state. A block sentence does the same with its district and
  the state (D77).
- The whole is named by the build's one setting (`the whole sample` today,
  `the state` statewide), never by fixed words.
- **When a sentence names two groups, its middle value says which one it
  belongs to** (ruling R11): "…the 4th highest of the 21 Gram Panchayats in
  Kalimela block and in the upper-middle quarter of the 6,800 in the state.
  The middle value for these 21 is Rs 1.95 crore." With one group named the
  sentence stays "The middle value is …".

**Wording:** counts say "most / fewest"; money and shares say "highest /
lowest". The end nearer the figure is named (rank 2 of 20 is "2nd highest", not
"19th lowest"). Equal figures share a rank and read "joint 2nd highest".
High is never called good, nor low bad.

## 5. What is on a sheet

All figures cover **every fiscal year in the data** unless the row says
otherwise. "Sum" means the sum over the place's rows of that view. For a block,
a district or the whole, the same sums are taken over all rows belonging to it.

### The main row

**A — Size and money**

| Id | Plain name | Definition | Standing |
|---|---|---|---|
| A1 | Planned activities | sum of `view3.n_activities` | yes |
| A2 | Activities with no cost attached | sum of `view3.n_costless`; also as a share of A1 | no |
| A3 | Planned cost (PLANNED) | sum of `view3.planned_cost` | yes |
| A4 | Sanctioned amount (SANCTIONED) | sum of `view3.sanctioned_total` — activities with an approval on file only | yes |
| A5 | Spent on planned activities (SPENT) | sum of `view3.expenditure_total` | yes |
| A6 | Spent as a share of planned cost | A5 ÷ A3; blank when A3 is zero | yes |
| A7 | Spending measured against plan | sum of `view3.overspend_vs_plan`, shown in words ("Rs 5.90 crore below plan") through the existing `glossary.signed_money` | no |

**E — Works**

| Id | Plain name | Definition | Standing |
|---|---|---|---|
| E1 | Works marked ongoing | sum of `view3.n_ongoing` | yes |
| E2 | Works marked completed | sum of `view3.n_completed`; also as a share of the whole's E2 | yes |
| E3 | Works marked abandoned | sum of `view3.n_abandoned`; planned money on them = sum of `view1.total_cost` over the rows marked abandoned (`is_abandoned = 1`); the plan year with the most, and its count. **Corrected, D77:** the first version summed `view1.fund_abandoned_total` over every row, and 19 rows that are not marked abandoned carry that amount (§12 item 8), so four Gram Panchayats' sentences overstated the money. | no |
| E4 | Activities with photo evidence | sum of `view3.n_with_evidence`; uploads = sum of `view3.evidence_uploads` | yes |
| E5 | Older works still marked ongoing | `view1` rows with `is_ongoing = 1` whose `fiscal_year` is three or more fiscal years before the latest in the data: count, planned cost, spent, spent ÷ planned | no |

**F — Approvals**

| Id | Plain name | Definition | Standing |
|---|---|---|---|
| F1 | Activities with an administrative approval on file | sum of `view3.n_admin_approvals`; also as a share of A1 | yes |
| F2 | Activities with a technical approval on file | sum of `view3.n_tech_approvals` | no |

F1 always carries this fixed note: *"An activity with no approval on file is
not known to be unapproved; the record may simply be missing."*

**G — Cashbook** (all money in and out of the place's books, including money
tied to no activity; by the year of the cashbook entry)

| Id | Plain name | Definition | Standing |
|---|---|---|---|
| G1 | Received (CASHBOOK) | sum of `view3.receipt_amount` | yes |
| G2 | Paid out (CASHBOOK) | sum of `view3.payment_amount` | yes |
| G3 | Share of payments linked to a planned activity | A5 ÷ G2; blank when G2 is zero | yes |

**H — Records to check** (each a count; shown only when not zero)

| Id | Plain name | Definition |
|---|---|---|
| H1 | Approval cost recorded with no approval record | sum of `view1.has_approval_cost_only` |
| H2 | Activities with no LSDG theme mapped | `view1` rows whose `theme` is the unmapped label: count and planned cost |
| H3 | Reported toilets exceed reported households (Gram Panchayat only) | `view4.household_toilets > view4.households` |
| H4 | Reported tap connections exceed reported households (Gram Panchayat only) | `view4.households_tap_water > view4.households` |
| H5 | More than 20 people per reported household (Gram Panchayat only) | `view4.population_total ÷ view4.households > 20` |

**I — About the place**

| Id | Plain name | Definition |
|---|---|---|
| I1 | Population and size band (Gram Panchayat only) | `view4.population_total`, `gp_size` |
| I2 | Households (Gram Panchayat only) | `view4.households` |
| I3 | Kind of place (Gram Panchayat only) | `view4.social_composition`, `remoteness` |
| I4 | Places inside it (block, district, whole) | number of Gram Panchayats; for a district and the whole, also the number of blocks |

I1–I3 always carry this fixed note: *"Reported by the Gram Panchayat itself and
not checked."*

### The lists

**B — By year.** One line for every fiscal year in the data, including years
with nothing. By the **plan year of the activity** (ruling R3).

| Column | Definition |
|---|---|
| Activities | `view3.n_activities` |
| With no cost | `view3.n_costless` |
| Planned | `view3.planned_cost` |
| Spent | `view3.expenditure_total` |
| Spent as a share of planned | spent ÷ planned; blank when planned is zero |
| Abandoned | `view3.n_abandoned` |

**No fixed note on this list (ruling R9).** The draft carried a note that
activity counts rise from 2023-2024 because activities with no cost began to
be recorded then; the operator dropped it. Each year's line still shows how
many of its activities have no cost, which is the fact the note pointed at.

**C — By focus area, and by LSDG theme.** From `view1`, grouped by
`focus_area_name` (up to 30 lines) and, separately, by `theme` (up to 7).
Every value present at the place is stored.

| Column | Definition |
|---|---|
| Activities | count of rows |
| Planned | sum of `total_cost` (no cost counts as zero) |
| Spent | sum of `total_expenditure` |
| Share of the place's planned cost | planned ÷ A3 |
| Share of the place's spending | spent ÷ A5 |
| Spent as a share of planned | spent ÷ planned; blank when planned is zero |

**D — By money source.**
- *At planning:* planned tied grant = sum of `view1.fund_tied_total`; planned
  untied grant = sum of `view1.fund_untied_total`; each also as a share of A3.
- *At sanction:* `view1` rows with `is_admin_approved = 1`, grouped by
  `sanctioned_scheme_name`: number of approvals and sum of
  `fund_sanctioned_total`. The five largest, then "all others".
- *Who approved:* the same rows grouped by `sanction_authority`: number of
  approvals. The three largest, then "all others".

**J — Member places** (not on a Gram Panchayat sheet). A block lists its Gram
Panchayats, a district its blocks, the whole its districts. Each line gives the
member's name, code, A1, A3, A5 and A6, in order of A6 from lowest.

### What a sheet does not hold

Nothing per activity, no names of people, no free text. The excluded columns of
mapping doc §7 and §9.6 stay excluded.

## 6. Ready-made sentences

Every figure the writer may quote has one short sentence, written by a fixed
pattern at build time, with an id. The patterns below were **approved by the
operator (rulings R6 and R11–R13)**; the agent implements them as written. The
patterns for the remaining rows, and for the zero and no-peers cases, follow
the same shape and are listed in full in Appendix A of this spec.

Formats: money through the corpus's own formatter (`format_measure`:
"Rs 7.65 crore", "Rs 92.28 lakh"); shares to one decimal ("23.0%"); counts with
separators ("12,704"); fiscal years as stored ("2023-2024"). Sentences are kept
short; the by-year line is the longest, at five figures.

| Row | Pattern | For Kalimela Gram Panchayat (figures from §13) |
|---|---|---|
| A1 | {place} has {A1} planned activities, the {standing}. The middle value for these {n} is {median}. | Kalimela Gram Panchayat has 852 planned activities, the 2nd most of 20 Gram Panchayats. The middle value for these 20 is 602.5. |
| A2 | {A2} of them ({share}) have no cost attached. | 392 of them (46.0%) have no cost attached. |
| A3 | Its planned cost is {A3}, the {standing}. The middle value is {median}. | Its planned cost is Rs 7.65 crore, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore. |
| A5 | It spent {A5} on planned activities, the {standing}. The middle value is {median}. | It spent Rs 1.76 crore on planned activities, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore. |
| A6 | Spending is {A6} of the planned cost, the {standing}. The middle value is {median}. | Spending is 23.0% of the planned cost, the 5th lowest of 20 Gram Panchayats. The middle value is 42.0%. |
| A7 | Spending is {A7 in words}. | Spending is Rs 5.90 crore below plan. |
| B (one per year) | In {year}: {activities} activities ({costless} with no cost), {planned} planned, {spent} spent, {share} of the plan. | In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan. |
| C (one per line) | {focus area}: {activities} activities, {planned} planned, {spent} spent. | Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent. |
| C, nothing spent | {focus area}: {activities} activities and {planned} planned, with nothing spent. | Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent. |
| E2 | {E2} works are marked completed, {share-of-whole phrase}. | 13 works are marked completed, out of 17 in the whole sample. |
| E5 | {count} works planned in {latest old year} or earlier are still marked ongoing. {spent} of their {planned} planned cost has been spent ({share}). | 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%). |
| F1 | {F1} of the {A1} activities ({share}) have an administrative approval on file, the {standing}. The middle value is {median}. | 168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats. The middle value is 96. |
| G1, G2 | Its cashbook shows {G1} received and {G2} paid out. | Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out. |
| G3 | {G3} of the payments are linked to a planned activity, the {standing}. The middle value is {median}. | 33.3% of the payments are linked to a planned activity, the 9th lowest of 20 Gram Panchayats. The middle value is 42.2%. |

F1 and G3 are shown as amended by ruling R12: the first version gave F1 a
standing with no middle value and G3 a middle value with no standing.

Rows not listed (A4, E1, E3, E4, F2, D, H, I, J) follow the same shape; the
full list is Appendix A of this spec.

Sentence ids are stable across builds and name the level, the place's code and
the row — for example `p-gp-119936-A6`, `p-gp-119936-B-2023-2024`. They must
fit the existing citation tag (60 characters, no square brackets).

## 7. What leads an answer (ruling R5)

**The model chooses.** What matters about a place depends on the question, so
no fixed rule decides which facts an answer uses. The draft of this section
held six code-set "notable" marks with thresholds (nothing spent, a sharp
change in a year, at an end of its peers, old works open, holds most of the
whole, records to check). The operator dropped them on 2026-11-24. **The build
computes no mark and stores no threshold.**

What stays in code, so the model's choice cannot lose or change a fact:

- **Each sentence already says what makes its figure stand out** — the
  standing, the middle value, "with nothing spent". The model judges from the
  sentence and works nothing out.
- **Sheet sentences reach the writer in a fixed order** (the order of §5), and
  using any one of them is optional. The rule that every record handed to the
  writer must be cited does not apply to sheet sentences (built in WP-D15).
- **No fixed set of figures on the page (ruling R19, D78).** The PM had
  recommended that code always show six headline figures, the by-year list and
  the largest focus areas, whatever the prose used. The operator ruled no: "let
  the model pick the most interesting finding to highlight". So the page
  highlights the sheet lines the writer's own answer used, in the order it used
  them. WP-D15 returns that list; WP-D16 draws it. Two runs of one question may
  highlight different facts; that is accepted.
- **When the writer's answer is refused twice**, the officer still sees the
  sheet lines the writer chose in its last attempt, in their stored wording.
  Only when it chose none does code supply the seven lines A1–A7 (PM reading
  of R19, stated to the operator on 2026-11-24).
- **The WP-D15 trial measures what these rulings risk:** the same question
  asked three times, and how far the chosen facts differ between runs.

## 8. Scale and storage: what the build must meet

How the sheets are stored is the agent's choice within these limits.

1. **Lookup by key.** Given a level and a code, the service gets that sheet's
   main row and lists without reading any other sheet, in under 50 ms once the
   store is open. Opening the store checks every file against its stamp; it
   happens once, when the service starts, and is not part of the target (PM,
   D77). Measured at state size in WP-D14: a lookup takes under 1 ms, opening
   about 60 ms.
2. **Nothing held in memory for all places.** Starting the service with the
   sheet store adds no more than 100 MB.
3. **Git limits.** No file over 95 MB (the limit already enforced for vector
   parts). Two builds from the same views differ only in the timestamp.
4. **Scale test, required in WP-D14.** A made-up state: the sample copied to
   6,800 Gram Panchayats, 314 blocks and 30 districts with new codes and
   names. Targets: build in under 10 minutes on the development machine; the
   sheet store under 300 MB on disk. The agent reports what it measured; a
   missed target is a stop for the PM, not a thing to work around.
5. **Size expected** (PM estimate, to be measured): about 60 lines per Gram
   Panchayat, so about 430,000 lines statewide.

## 9. How we know a sheet is right

Checks the build must pass, each over every sheet:

1. **Equal to the views.** Every A, E, F, G figure of a Gram Panchayat equals
   the sum of the matching `view3` column for that Gram Panchayat (and the
   matching `view4` lifetime column). E3's planned money equals the sum of
   `view1.total_cost` over that place's rows marked abandoned (added D77).
2. **The parts add up.** For every figure that is a sum, Gram Panchayats add to
   their block, blocks to their district, districts to the whole.
3. **Shares are re-derived, not averaged.** For every block with more than one
   Gram Panchayat, A6 equals the block's A5 ÷ A3. Reference: Rangeilunda block
   is 23.1%; the average of its two Gram Panchayats' shares is 28.8% and is
   wrong.
4. **Equal to the insights.** Where the breakdowns corpus holds a total for the
   same place and measure, its digits equal the sheet's. Reference: the whole's
   A7 is "Rs 51.96 crore below plan", as record `d1-00248` states. A Gram
   Panchayat is matched by its code; a block or a district by its level and
   name, because the breakdowns corpus holds only names for those — so every
   name must be unique within its level, and the check says so (D77).
5. **Sentences hold only stored figures.** Every numeral in a ready-made
   sentence is a stored value of its row through the stored formatter (the
   same proof as `layout-formatter-parity`).
6. **Every place has a sheet**, including a place with no activity.
7. **The reference figures of §13** are reproduced exactly.

## 10. Not in this first version

| Left out | Why | Needs |
|---|---|---|
| Sheets for schemes, sectors, stages of work, years | Places first (ruling R7) | Their own spec, after the trial |
| "Who stands out" tables across all places | Same numbers turned the other way; second step | A short spec |
| Spending by scheme | The spending table's scheme column is not in the views (82% empty) | A change to the view pack |
| Repeated spending rows; late approval dates; vouchers matched to spending | Not visible in the views, which hold one rolled-up row per activity | A change to the view pack, made for Ask and Discover together |
| Approvals moving from one authority to another over the years | Needs approvals by authority by year, and the authority field still carries stray spellings | A later list, and a cleaner field |
| Month-by-month payments and year-end bursts | Available in `view2`; left out to keep the first sheet small | A later list |
| Spending per person or per household | The profile figures are self-reported and visibly unreliable (§12) | Better profile data |
| Anything a fixed list did not think of | A sheet holds only what is listed here | The offline "scout" idea (D75), not specified here |
| Code-set "notable" marks and their thresholds | Dropped by the operator (ruling R5): the model chooses | Comes back only if the WP-D15 trial shows the model's choices are unstable or miss the plain facts |
| A fixed note on the by-year list about the 2023-2024 change in recording | Dropped by the operator (ruling R9) | — |
| A flag for fewer than one person per reported household (Kalyansinghpur reports 4,051 households for 2,049 people; H5 catches only more than 20 per household) | The operator: ignore for now (ruling R14) | A ruling |
| A fixed set of headline figures drawn by code on every place answer | Rejected by the operator (ruling R19): the model picks what to highlight | Comes back only if the WP-D15 trial shows the plain facts going missing |
| A sheet for a question that names no place, or more than three | Not in the first serve package (ruling R16) | A ruling after the trial |

## 11. The operator's rulings (signed 2026-11-24, D76)

| # | Question | Ruling |
|---|---|---|
| R1 | **Peers.** Who is a place compared with, and how few peers is too few? | **As recommended (§4):** block, district, state for a Gram Panchayat; no standing from fewer than 5 peers; exact place up to 50 peers, quarters above that. |
| R2 | **"Spent".** Which figure is reported? | **The views' figure as it stands** (`expenditure_total`), so sheets and insights agree. It counts six repeated rows (§12 item 1); removing them is a separate decision for Ask and Discover together. On today's views Kalimela spends 23.0% of plan, 5th lowest of 20; with the repeats removed it would be 22.2%, 3rd lowest. |
| R3 | **Year.** Which year does spending belong to in the by-year list? | **The plan year of the activity** (as `view3` does). Cashbook figures stay by the year of the cashbook entry and say so. |
| R4 | **A name that is both a Gram Panchayat and a block.** | **Answer for the block, unless the question clearly says it is about the Gram Panchayat.** (The PM had recommended asking the officer.) Built in WP-D15. |
| R5 | **What counts as notable** (§7). | **Let the model decide.** No code-set marks, no thresholds. (The PM had recommended six rules.) §7 is rewritten to match. |
| R6 | **The sentence wording** (§6). | **Approved as written.** The operator asked whether the numbers can change on the way to the officer; the answer and two gaps to close are in D76 and go into WP-D15. |
| R7 | **Scope of the first version.** | **Places only** (Gram Panchayat, block, district, the whole). |
| R8 | **Self-reported profile figures** (population, households). | **Show them**, with the fixed "not checked" note, and show the H3–H5 checks. |
| R9 | **The count note on the by-year list.** | **Dropped.** No fixed note. (The PM had recommended showing it.) |

**After the build was reviewed (D77, 2026-11-24).** The PM listed six points
in the chat; the operator answered by number.

| # | Question | Ruling |
|---|---|---|
| R10 | **The money on abandoned works** counted amounts on works not marked abandoned (the PM's error in §5). | **Fix it.** Sum the planned cost of the abandoned works only. Bandhpali reads Rs 56.52 lakh, not Rs 70.66 lakh; the whole Rs 5.85 crore, not Rs 6.17 crore. |
| R11 | **Which group a middle value belongs to**, when a sentence names two groups (state size). | **Say it:** "The middle value for these 21 is …". |
| R12 | **The approvals line (F1) and the cashbook-link line (G3)** did not match the other ranked lines. | **Both get a standing and a middle value.** |
| R13 | **Zero cases** that would print "Rs 0 … (0.0%)", "their planned cost is Rs 0", "0.0% of the payments". | **Plain wording for all three** (Appendix A). |
| R14 | **Flag fewer than one person per reported household?** | **Ignore for now.** |
| R15 | **Small variants the agent added** (one of something, joint ranks, a single approver). | **Fine.** |

**For the serve package, WP-D15 (D78, 2026-11-24).**

| # | Question | Ruling |
|---|---|---|
| R16 | **Which questions get a sheet.** | **One place named: its full sheet. Two or three places named: the seven main lines (A1–A7) of each. No place named: no sheet for now.** |
| R17 | **How much of the sheet the writer sees.** | **All of it; the writer chooses.** A fixed core of about 25 lines is the fallback plan if the trial shows the whole sheet is too much for a mid-size model. |
| R18 | **Lines added to the writer's prompt** (the operator's file). | **Approved as proposed:** "Some answers also come with PLACE FACTS: standard figures about the place the officer asked about, each with an id starting p-. Start from the place facts that answer the question, then bring in the findings. You do not have to use every place fact. Tag them the same way as findings." |
| R19 | **A fixed set of figures on the page**, drawn by code on every place answer. | **No. "Let the model pick the most interesting finding to highlight."** §7 is rewritten to match. (The PM had recommended the fixed set.) |
| R20 | **Numbers written as words** ("second highest", "nearly half") are not read by the number check. | **Log them during the trial; decide on blocking after seeing how often they are wrong.** |

## 12. Data notes found while writing this (for the mapping doc's §8 log)

Logged, not fixed. Items 1–3 affect what officers see today.

1. **Six spending rows are repeats** — same activity, same amount, same voucher
   — worth Rs 7.84 lakh across 3 Gram Panchayats (Kalimela: 4 rows,
   Rs 5.5 lakh, all in 2020-2021). The pack's `stg_exp_rollup` sums them, as
   Ask's `v_exp` does, so both products count them.
2. **For Kalimela the "general" spending component (Rs 2.07 crore) is larger
   than total spending (Rs 1.76 crore).** The two columns of the spending table
   disagree. Today's report shows both (a card and a chart) without saying so.
   The sheet uses total spending only.
3. **"Not recorded" on a fund component means "no approval on file".** The fund
   component and scheme are filled only for activities with an administrative
   approval. Today's report says "684 rows have no fund component on file" for
   Kalimela; 684 is exactly its 852 activities less its 168 approvals. The
   warning reads as missing data when it is missing approvals.
4. **Two ways of dating spending are in use.** `view3` puts spending in the
   plan year of the activity; `view2` (the source of today's by-year chart)
   puts it in the year of the payment. For Kalimela 2020-2021 the first gives
   Rs 42.01 lakh and the second Rs 0. Neither is wrong; the chart does not say
   which it is.
5. **Kalimela's profile reports 200 households, 200 toilets, 200 tap
   connections and 200 job cards** against a population of 10,681.
6. **The approving-authority field still carries stray spellings** ("sar",
   "sarapacnh") after cleaning (mapping doc §11 item 2).
7. **A focus area is spelled "Poverty allevation programme"** in the data.

Found by the WP-D14 agent and checked by the PM (2026-11-24):

8. **19 activities not marked abandoned carry an "abandoned" fund amount**
   (`fund_abandoned_total`), Rs 32.85 lakh in all: Bandhpali 8 rows
   (Rs 14.14 lakh), Kalyansinghpur 8 (Rs 13.71 lakh), Hirlipali 2
   (Rs 4.00 lakh), Bheden 1 (Rs 1.00 lakh). On the 420 rows that are marked
   abandoned the amount equals the planned cost, row for row. This is why E3
   now sums the planned cost of the abandoned rows (ruling R10).
9. **A stage-of-work value "Buildings"** sits on 2 Bandhpali rows. It reads
   like a kind of asset, not a stage.
10. **Two sanctioned schemes appear only as codes**: "Code 1518" (22 approvals,
    Rs 34.53 lakh) and "Code 1526" (1 approval, Rs 4.49 lakh). The sheets show
    them as stored.
11. **More stray approving-authority values than item 6 lists**: "SARAPNCH",
    "SWARPANCH", "S", "12", "14", "15", "KALYANSINGHPUR", "GRAMPANCHAYATKS".
    They fall into "all others" on the sheets.
12. **Kalyansinghpur's profile reports 4,051 households for 2,049 people.**
    Karuabahal's reports 12 households for 3,208 people and 1,256 toilets.
13. **The money formatter rounds across a unit boundary**: 99,999.99 prints as
    "Rs 1,00,000" and 9,999,999.99 as "Rs 100.00 lakh". No sheet figure
    reaches it today.
14. **The block is spelled "Kalyansingpur" and its Gram Panchayat
    "Kalyansinghpur".** The chat resolves a typed "Kalyansinghpur" to both.

## 13. Reference figures (the build must reproduce these)

PM-computed on 2026-11-24 from the built views of the current candidate set
(as of 2026-09-11). Money in rupees.

**Kalimela Gram Panchayat** (`gp_lgd_code` 119936; block Kalimela 3843;
district Malkangiri 323). Peers: the 20 Gram Panchayats of the sample.

| Row | Value | Standing among 20 | Middle value |
|---|---|---|---|
| A1 planned activities | 852 | 2nd most | 602.5 |
| A2 with no cost | 392 (46.0%) | | |
| A3 planned cost | 76,548,042 | 2nd highest | 30,986,778 |
| A4 sanctioned | 20,784,410 | 2nd highest | 13,707,759.5 |
| A5 spent | 17,579,894 | 2nd highest | 12,765,765.3 |
| A6 spent ÷ planned | 22.9658% | 5th lowest | 42.0457% |
| A7 against plan | −58,968,148 | | |
| E1 ongoing | 154 | 2nd most | 95.5 |
| E2 completed | 13 (of 17 in the whole) | most | 0 |
| E3 abandoned | 22; planned money on them 272,440; most in 2024-2025 (21) | | |
| E4 with photo evidence | 129; uploads 553 | 2nd most | 79 |
| E5 older works ongoing | 55; planned 10,426,968; spent 8,963,247 (86.0%) | | |
| F1 administrative approvals | 168 (19.7% of activities) | most | 96 |
| F2 technical approvals | 168 | | |
| G1 received | 46,304,795.56 | 5th highest | 29,779,715.50 |
| G2 paid out | 52,838,871.78 | 4th highest | 33,647,520.815 |
| G3 linked share of payments | 33.2708% | 9th lowest | 42.1689% |
| H1 / H2 | 0 / 49 activities, planned cost 3,490,278 | | |
| H5 people per reported household | 53.4 (10,681 ÷ 200) | | |
| I1–I3 about the place | population 10,681; size band "10,000 and above"; 200 households; "ST-majority"; "Near" | | |

**Kalimela block** (`block_code` 3843; one Gram Panchayat in the sample, so
its sums equal the Gram Panchayat's). Under ruling R4 this is the sheet a
question about "Kalimela" gets. Peers: the 16 blocks of the sample.

| Row | Value | Standing among 16 | Middle value |
|---|---|---|---|
| A1 planned activities | 852 | 5th most | 712 |
| A3 planned cost | 76,548,042 | 2nd highest | 44,840,248 |
| A4 sanctioned | 20,784,410 | 5th highest | 15,087,289.5 |
| A5 spent | 17,579,894 | 5th highest | 13,963,300.5 |
| A6 spent ÷ planned | 22.9658% | 4th lowest | 36.5570% |
| E1 ongoing | 154 | 5th most | 104 |
| E2 completed | 13 | most | 0 |
| E4 with photo evidence | 129 | 5th most | 83 |
| F1 administrative approvals | 168 | 4th most | 104 |
| G1 received | 46,304,795.56 | 6th highest | 37,230,713 |
| G2 paid out | 52,838,871.78 | 5th highest | 35,410,176.78 |
| G3 linked share of payments | 33.2708% | 6th lowest | 46.5430% |

By year (activities / with no cost / planned / spent / share):

| Year | Activities | No cost | Planned | Spent | Share |
|---|---|---|---|---|---|
| 2020-2021 | 20 | 0 | 4,490,312 | 4,200,837 | 93.6% |
| 2021-2022 | 32 | 0 | 6,443,270 | 3,320,583 | 51.5% |
| 2022-2023 | 28 | 0 | 3,576,920 | 2,884,416 | 80.6% |
| 2023-2024 | 335 | 196 | 26,182,640 | 2,894,236 | 11.1% |
| 2024-2025 | 268 | 72 | 29,995,250 | 3,159,940 | 10.5% |
| 2025-2026 | 169 | 124 | 5,859,650 | 1,119,882 | 19.1% |

Five largest focus areas by planned cost (activities / planned / spent):
Drinking water 166 / 37,376,058 / 6,098,020; Land improvement 57 / 7,395,000 /
0; Maintenance of community system 100 / 6,202,800 / 1,153,867; Sanitation
118 / 5,289,128 / 3,362,022; Roads 27 / 5,218,686 / 1,972,350.
Also nothing spent: Poverty allevation programme 114 / 3,709,000 / 0.

Money source: planned tied grant 9,228,256; planned untied grant 67,319,786.
Sanctioned by scheme: XV Finance Commission 125 approvals, 13,889,087; 5TH
STATE FINANCE COMMISSION 41, 6,621,323; Own Funds 2, 274,000. Approved by: BDO
91, Sarpanch 72, Engineer 3, all others 2.

**The whole sample** (key `all`): A1 12,704; A2 7,074; A3 773,088,536; A4
288,438,745; A5 253,475,090.46; A6 32.7873%; A7 −519,613,445.54; E1 2,110; E2
17; E3 420; E4 1,675 with 8,267 uploads; F1 2,101; F2 2,095; G1
664,791,435.89; G2 685,750,811.29.

**The money on abandoned works, as corrected (ruling R10, D77).** Works marked
abandoned / planned cost on them / plan year with the most (count). Kalimela is
unchanged at 22 / 272,440 / 2024-2025 (21). Every other sheet keeps the figure
it had.

| Sheet | Works | Planned on them | Was | Top year |
|---|---|---|---|---|
| Hirlipali Gram Panchayat (116350) | 29 | 4,019,174 | 4,419,174 | 2022-2023 (16) |
| Bandhpali Gram Panchayat (116397) | 25 | 5,651,792 | 7,065,872 | 2020-2021 (10) |
| Bheden Gram Panchayat (116438) | 52 | 8,781,358 | 8,881,358 | 2021-2022 (26) |
| Kalyansinghpur Gram Panchayat (121162) | 31 | 4,457,998 | 5,828,844 | 2021-2022 (14) |
| Attabira block (3674) | 29 | 4,019,174 | 4,419,174 | 2022-2023 (16) |
| Barpali block (3676) | 40 | 7,957,981 | 9,372,061 | 2022-2023 (19) |
| Bheden block (3678) | 52 | 8,781,358 | 8,881,358 | 2021-2022 (26) |
| Kalyansingpur block (3914) | 31 | 4,457,998 | 5,828,844 | 2021-2022 (14) |
| Bargarh district (306) | 121 | 20,758,513 | 22,672,593 | 2022-2023 (43) |
| Rayagada district (329) | 31 | 4,457,998 | 5,828,844 | 2021-2022 (14) |
| The whole | 420 | 58,463,049 | 61,747,975 | 2023-2024 (105) |

**Shares at higher levels** (check 3 of §9): Rangeilunda block 23.0800%
(planned 118,410,265; spent 27,329,118); Bhubaneswar block 55.8936%; Khordha
district 55.8936%; Kandhamal district 16.7013% (the lowest of 9); Malkangiri
district 22.9658%.

---

## Appendix A — the sentence patterns (current)

This is the one current list. It began as Appendix A of the WP-D14 brief
(rulings R6); the lines marked **(D77)** were changed or added by rulings
R10–R13 and R15. The builder's own copy of the examples must be this text,
character for character, and a test says so.

**General rules**

- `{Place}` is the name and the level word: `Kalimela Gram Panchayat`,
  `Kalimela block`, `Malkangiri district`. For the whole it is the build's one
  setting: `The whole sample` at the start of a sentence, `the whole sample`
  inside one.
- `{standing}` — counts use most / fewest; money and shares use highest /
  lowest. The end nearer the figure is named.
  - Up to 50 peers: `the most of 20 Gram Panchayats`, `the 2nd highest of 20
    Gram Panchayats`, `the 4th lowest of 16 blocks`. Tied: `the joint 2nd
    highest of …`, `the joint most of …`.
  - When the peer group is a block or a district, name it: `of the 22 Gram
    Panchayats in Kalimela block`.
  - More than 50 peers: `in the lowest quarter of the 6,800 Gram Panchayats in
    {the whole}` (quarters: lowest, lower-middle, upper-middle, highest).
    `{the whole}` is the setting, never the fixed words "the state" **(D77)**.
  - Statewide, a Gram Panchayat sentence gives both: `the 5th lowest of the 22
    Gram Panchayats in Kalimela block and in the lowest quarter of the 6,800
    in the state`. A block sentence does the same: `the 2nd most of the 11
    blocks in Malkangiri district and in the highest quarter of the 314 in the
    state` **(D77)**.
- **The middle value** is that of the first peer group named in the sentence.
  When the sentence names one group it reads `The middle value is {median}.`
  When it names two it reads `The middle value for these {n} is {median}.`,
  with `{n}` the size of the first group **(D77, R11)**. A1 says `for these
  {n}` in both cases, as before.
- **No peer group of at least 5** (and always for the whole): leave out the
  standing clause and the middle-value sentence. `Kalimela Gram Panchayat has
  852 planned activities.`
- **A zero value takes the zero form** below, which carries no standing and no
  middle value.
- **One of something agrees**, in every pattern **(D77, R15)**: `1 of them
  (x%) has no cost attached`, `1 work is marked completed`, `1 activity has
  photo evidence (1 upload)`, `1 approval`, `1 block and 1 Gram Panchayat`.
- A row whose pattern is not met (a blank share, an H row that is zero) has no
  sentence.

**The main row**

| Row | Pattern | Zero or blank form |
|---|---|---|
| A1 | {Place} has {A1} planned activities, the {standing}. The middle value for these {n} is {median}. | {Place} has no planned activities in the data. |
| A2 | {A2} of them ({share}) have no cost attached. | All of them have a cost attached. (None when A1 is zero.) |
| A3 | Its planned cost is {A3}, the {standing}. The middle value is {median}. | It has no planned cost on record. |
| A4 | {A4} has been sanctioned for the activities with an approval on file, the {standing}. The middle value is {median}. | Nothing has been sanctioned on record. |
| A5 | It spent {A5} on planned activities, the {standing}. The middle value is {median}. | The data shows no spending on its planned activities. |
| A6 | Spending is {A6} of the planned cost, the {standing}. The middle value is {median}. | No sentence when A3 or A5 is zero. |
| A7 | Spending is {amount} below plan. / Spending is {amount} above plan. | No sentence when A7 is zero. |
| E1 | {E1} works are marked ongoing, the {standing}. The middle value is {median}. | No works are marked ongoing. |
| E2 | {E2} works are marked completed, out of {the whole's E2} in {the whole}. (On the whole's own sheet: {E2} works are marked completed.) | No works are marked completed. |
| E3 | {E3} works are marked abandoned, with {money} planned on them. {k} of them were planned in {year}. | No works are marked abandoned. With no planned money on them: `{E3} works are marked abandoned, with no planned cost on them.` One work: `1 work is marked abandoned, with {money} planned on it. It was planned in {year}.` **(D77)** |
| E4 | {E4} activities have photo evidence ({uploads} uploads), the {standing}. The middle value is {median}. | No activities have photo evidence. |
| E5 | {count} works planned in {cut-off year} or earlier are still marked ongoing. {spent} of their {planned} planned cost has been spent ({share}). | No sentence when the count is zero. The second sentence is dropped when their planned cost is zero. **When nothing has been spent (D77, R13):** `{count} works planned in {cut-off year} or earlier are still marked ongoing. Nothing has been spent of their {planned} planned cost.` One work: `… is still marked ongoing. Nothing has been spent of its {planned} planned cost.` |
| F1 **(D77, R12)** | {F1} of the {A1} activities ({share}) have an administrative approval on file, the {standing}. The middle value is {median}. | None of the {A1} activities has an administrative approval on file. |
| F2 | {F2} activities have a technical approval on file. | No activities have a technical approval on file. |
| G1 + G2 | Its cashbook shows {G1} received and {G2} paid out. (One sentence, id `…-G1`, for both rows.) | Its cashbook shows no receipts and no payments. |
| G3 **(D77, R12)** | {G3} of the payments are linked to a planned activity, the {standing}. The middle value is {median}. | No sentence when G2 is zero. **When G3 is zero (D77, R13):** `None of the payments is linked to a planned activity.` |
| H1 | {H1} activities have an approval cost recorded with no approval record. | No sentence. |
| H2 | {H2} activities have no LSDG theme mapped; their planned cost is {money}. | No sentence when H2 is zero. **When their planned cost is zero (D77, R13):** `{H2} activities have no LSDG theme mapped; none of them has a cost attached.` One activity: `1 activity has no LSDG theme mapped; it has no cost attached.` |
| H3 | Its profile reports {toilets} household toilets for {households} households. | Only when toilets exceed households. |
| H4 | Its profile reports {taps} tap connections for {households} households. | Only when connections exceed households. |
| H5 | Its profile reports {population} people in {households} households, which is {ratio} people per household. | Only when the ratio is over 20. |
| I1 | Its profile reports a population of {population} (size band: {gp_size}). | No sentence when not reported. Size band not reported: `Its profile reports a population of {population}.` |
| I2 | Its profile reports {households} households. | No sentence when not reported. |
| I3 | Its profile classes it as {social_composition} and as {near a bus stop / far from a bus stop}. | Leave out a part that is "Not reported". |
| I4 | Block: {Place} has {n} Gram Panchayats in the data. District: {Place} has {b} blocks and {n} Gram Panchayats in the data. Whole: {Place} has {d} districts, {b} blocks and {n} Gram Panchayats. | — |

F1 and G3 follow the general rules like every other ranked row: no peer group
of at least 5 means no standing clause and no middle-value sentence, and two
groups named means `The middle value for these {n} is …`. F1's middle value is
that of the count of approvals, the figure it is ranked on. F1 keeps its fixed
note.

**The lists**

| Line | Pattern | Other forms |
|---|---|---|
| B | In {year}: {n} activities ({c} with no cost), {planned} planned, {spent} spent, {share} of the plan. | Drop the bracket when none has no cost. Nothing planned: `…, nothing planned, {spent} spent.` Nothing spent: `…, {planned} planned, nothing spent.` Neither: `…, nothing planned, nothing spent.` No activities: `In {year}: no planned activities.` |
| C | {Name}: {n} activities, {planned} planned, {spent} spent. | Nothing spent: `{Name}: {n} activities and {planned} planned, with nothing spent.` No planned cost: `{Name}: {n} activities with no planned cost, {spent} spent.` Neither: `{Name}: {n} activities, with no planned cost and nothing spent.` |
| D-plan | Of the planned cost, {tied} is tied grant ({share}) and {untied} is untied grant ({share}). | No sentence when A3 is zero. |
| D-scheme | {Scheme}: {n} approvals, {amount} sanctioned. | The sixth line, when there are more than five: `All other schemes: {n} approvals, {amount} sanctioned.` |
| D-authority | Approvals on file, by who approved: {A} {n}, {B} {n}, {C} {n}, all others {n}. | Fewer names when fewer exist; no "all others" when there are none (`Approvals on file, by who approved: Sarpanch 181.`). No sentence when F1 is zero. |
| J | {Member}: {A1} activities, {A3} planned, {A5} spent, {A6} of the plan. | The same forms as B for nothing planned and nothing spent. A member with no activity: `{Member}: no planned activities.` |

**Examples to reproduce character for character**

Kalimela Gram Panchayat (`p-gp-119936-…`):

```
A1  Kalimela Gram Panchayat has 852 planned activities, the 2nd most of 20 Gram Panchayats. The middle value for these 20 is 602.5.
A2  392 of them (46.0%) have no cost attached.
A3  Its planned cost is Rs 7.65 crore, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore.
A4  Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.37 crore.
A5  It spent Rs 1.76 crore on planned activities, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore.
A6  Spending is 23.0% of the planned cost, the 5th lowest of 20 Gram Panchayats. The middle value is 42.0%.
A7  Spending is Rs 5.90 crore below plan.
B-2020-2021  In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan.
B-2023-2024  In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan.
C   Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent.
C   Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent.
D-plan       Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%).
DS  XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned.
DS  5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned.
DS  Own Funds: 2 approvals, Rs 2.74 lakh sanctioned.
D-authority  Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2.
E1  154 works are marked ongoing, the 2nd most of 20 Gram Panchayats. The middle value is 95.5.
E2  13 works are marked completed, out of 17 in the whole sample.
E3  22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025.
E4  129 activities have photo evidence (553 uploads), the 2nd most of 20 Gram Panchayats. The middle value is 79.
E5  55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%).
F1  168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats. The middle value is 96.
F2  168 activities have a technical approval on file.
G1  Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out.
G3  33.3% of the payments are linked to a planned activity, the 9th lowest of 20 Gram Panchayats. The middle value is 42.2%.
H2  49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh.
H5  Its profile reports 10,681 people in 200 households, which is 53.4 people per household.
I1  Its profile reports a population of 10,681 (size band: 10,000 and above).
I2  Its profile reports 200 households.
I3  Its profile classes it as ST-majority and as near a bus stop.
```

Kalimela block (`p-block-3843-…`):

```
A1  Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
A3  Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore.
A5  It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore.
A6  Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%.
F1  168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. The middle value is 104.
G3  33.3% of the payments are linked to a planned activity, the 6th lowest of 16 blocks. The middle value is 46.5%.
I4  Kalimela block has 1 Gram Panchayat in the data.
J   Kalimela Gram Panchayat: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan.
```

The whole (`p-all-…`):

```
A1  The whole sample has 12,704 planned activities.
A2  7,074 of them (55.7%) have no cost attached.
A3  Its planned cost is Rs 77.31 crore.
A5  It spent Rs 25.35 crore on planned activities.
A6  Spending is 32.8% of the planned cost.
A7  Spending is Rs 51.96 crore below plan.
E3  420 works are marked abandoned, with Rs 5.85 crore planned on them. 105 of them were planned in 2023-2024.
F1  2,101 of the 12,704 activities (16.5%) have an administrative approval on file.
G3  37.0% of the payments are linked to a planned activity.
DS  Code 1526: 1 approval, Rs 4.49 lakh sanctioned.
I4  The whole sample has 9 districts, 16 blocks and 20 Gram Panchayats.
```

Other places:

```
p-gp-116397-E3     25 works are marked abandoned, with Rs 56.52 lakh planned on them. 10 of them were planned in 2020-2021.
p-block-3823-E2    1 work is marked completed, out of 17 in the whole sample.
```

**A two-group sentence** cannot be checked against the sample, which has no
peer group above 50. This one is an illustration of the form (R11), with
made-up figures, not a reference:

```
Its planned cost is Rs 4.47 crore, the 4th highest of the 21 Gram Panchayats in Kalimela block and in the upper-middle quarter of the 6,800 in the state. The middle value for these 21 is Rs 1.95 crore.
```

If the views give a different string for any reference line above, the agent
does not adjust the figure to match. It reports the difference: either this
appendix or the build is wrong, and the PM needs to know which.

# PR&DW Language & Keyword Dictionary — fill-in template

**For:** the operator (and any colleague/SME helping with Odia terms).
**Why this exists:** Decision D5 in `PROJECT_PLAN.md`. Two separate consumers:

1. **Activity keyword matching (Sheet 1).** The 86 SBM questions identify
   activities by matching text patterns against `activity_name` and
   `activity_desc`. In the 20-GP sample that text is romanized English;
   statewide it may be any language/script. Every term you add widens what the
   queries can find. **Missing terms do not cause errors — they cause silent
   undercounts.** That is why this file matters.
2. **Entity aliases (Sheet 2).** What users *type* ("Khurda", "15th FC",
   "ଖୋର୍ଦ୍ଧା") mapped to the canonical database value ("Khordha",
   "XV Finance Commission"). Feeds the entity validator so questions resolve
   without guessing.

**Delivery format:** one Excel file, `PRDW_Dictionary.xlsx`, with two sheets
named `activity_keywords` and `entity_aliases`, saved in this repo's root.
Odia script is expected — do not save as ANSI CSV (Excel .xlsx is safe).
Version the file by re-saving; the implementing agent converts it to a lookup
table the SQL joins against, so **you can keep adding rows forever without
touching the signed-off SQL**.

---

## Sheet 1 — `activity_keywords`

One row per **concept**. The first four columns are pre-filled below (copy
them into the sheet as-is); you fill the last three. Within a cell, separate
multiple terms with `;`.

Columns:

| Column | Filled by | Meaning |
|---|---|---|
| `concept_id` | pre-filled | Stable key the SQL references — do not edit |
| `submodule` | pre-filled | SBM grouping (GWM / SWM / Sanitation Infrastructure / O&M) |
| `concept_label` | pre-filled | Human name of the thing being counted |
| `english_terms_current` | pre-filled | Terms the tested workbook SQL matches **today** — never remove, only extend |
| `odia_terms` | **you** | Odia-script terms as they would appear in activity names/descriptions (e.g. ସୋକ୍ ପିଟ୍, ଶୌଚାଳୟ) |
| `romanized_odia_terms` | **you** | Same terms as data-entry operators romanize them (e.g. `soka pita`, `paikhana`, `sauchalaya`) |
| `other_variants` | **you** | Misspellings, local abbreviations, Hindi terms, scheme jargon you've seen in real entries (e.g. `lechpit`, `leach pit`, `sochalay`) |

### Filling rules

- Think "what would a GP data-entry operator actually type", not dictionary
  Odia — colloquial and misspelled beats correct and unused.
- Avoid terms shorter than 4 characters or generic words that would match
  unrelated activities ("water", "road", ପାଣି alone) — matching is
  case-insensitive substring, so short terms over-match. If a term is
  genuinely ambiguous, add it with a note in `other_variants` like
  `pani (AMBIGUOUS — review)`.
- Where a concept is a **pair** (household vs community variant of the same
  asset), the qualifier words matter as much as the asset words — fill the
  three `QUALIFIER-*` rows too; the SQL combines asset-term × qualifier-term.
- Leave a cell blank if you have nothing — blank is safe, wrong is not.

### Pre-seeded concept rows (copy into the sheet)

| concept_id | submodule | concept_label | english_terms_current | odia_terms | romanized_odia_terms | other_variants |
|---|---|---|---|---|---|---|
| QUALIFIER-HOUSEHOLD | (cross-cutting) | Household/individual qualifier | household; individual; hh | | | |
| QUALIFIER-COMMUNITY | (cross-cutting) | Community/shared qualifier | community; group; cluster; public | | | |
| QUALIFIER-INSTITUTION | (cross-cutting) | School/anganwadi qualifier | anganwadi; awc; school; institution | | | |
| GWM-SOAKPIT | GWM | Soak pit (asset term; pairs with qualifiers) | soak | | | |
| GWM-GENERIC | GWM | Grey water management, generic | grey water; greywater; gwm | | | |
| SWM-COMPOST | SWM | Compost pit/unit (pairs with qualifiers) | compost | | | |
| SWM-SEGREGATION-SHED | SWM | Segregation / sorting shed (MRF) | segregation shed; sorting shed; waste shed | | | |
| SWM-BIN | SWM | Dustbins (pairs with qualifiers) | bin; dustbin; dust bin | | | |
| SWM-GOBARDHAN | SWM | GOBAR-dhan / biogas unit | gobardhan; biogas; bio gas | | | |
| SWM-COLLECTION-VEHICLE | SWM | Waste collection vehicle | tricycle; vehicle; rickshaw; e-cart; ecart; pushcart; collection cart | | | |
| SWM-WEIGHING | SWM | Weighing equipment/machine | weighing | | | |
| SWM-PLASTIC | SWM | Plastic waste management unit | plastic waste; pwmu | | | |
| SWM-GENERIC | SWM | Solid waste management, generic | solid waste; waste management; segregat | | | |
| SI-IHHL | Sanitation Infrastructure | Individual household latrine | ihhl; individual household latrine | | | |
| SI-TOILET-PUBLIC | Sanitation Infrastructure | Public/community/institutional toilet (pairs with qualifiers) | toilet | | | |
| SI-CSC | Sanitation Infrastructure | Community sanitary complex | sanitary complex; community toilet; csc | | | |
| SI-HANDWASH | Sanitation Infrastructure | Handwash station (schools/AWC) | handwash; hand wash | | | |
| SI-RETROFIT | Sanitation Infrastructure | Toilet retrofitting (twin/single pit) | retrofit; twin pit; single pit | | | |
| SI-SEPTIC | Sanitation Infrastructure | Septic tank | septic | | | |
| OM-FSM | O&M | Faecal sludge management | faecal; fsm; sludge | | | |
| OM-PPE | O&M | Sanitation worker safety equipment | ppe; safety equipment; glove; mask; protective | | | |

*(The concept list was extracted from the tested SQL in
`AI_Chatbot_Questions.xlsx`; the implementing agent will reconcile it 1:1
against the workbook at conversion time. If you know an SBM asset type that is
missing entirely, add a row with `concept_id = NEW-<shortname>` and we'll wire
it in.)*

**Also useful, same sheet, lower priority:** general (non-SBM) activity
vocabulary that appears in activity names — e.g. terms for road (ରାସ୍ତା /
rasta), pond (ପୋଖରୀ / pokhari), drinking water (ପାନୀୟ ଜଳ / paniya jala),
kalyan mandap, AWC building. Use `concept_id = GEN-<shortname>`. These aren't
matched by current SQL but will improve future search/discovery features.

---

## Sheet 2 — `entity_aliases`

One row per **alias** (not per canonical value — a canonical value with five
nicknames gets five rows).

| Column | Filled by | Meaning |
|---|---|---|
| `entity_type` | you | One of: `district`, `block`, `gp`, `scheme`, `focus_area`, `theme`, `status`, `plan_type` |
| `canonical_value` | you | **Exactly** as it appears in the database (copy from the lists below — spelling, case and all) |
| `alias` | you | What a user might type instead — any language/script |
| `notes` | optional | e.g. "common misspelling", "Hindi", "could also mean X" |

### Rules

- An alias must map to exactly **one** canonical value within its
  entity_type. If the same word genuinely means two things, note it — that
  becomes a clarification chip, not a dictionary row.
- Don't alias things to themselves; exact and close-fuzzy matches already
  work. Aliases earn their keep on *non-obvious* variants: old spellings
  (Khurda→Khordha), abbreviations (15th FC, XVFC), Odia script forms,
  colloquial terms (sarkari → public/government categories).
- **Don't attempt GP-name aliases exhaustively** (6,800 GPs statewide) — seed
  only ones you know are commonly mis-typed; the rest grows from query logs
  after pilot.

### Canonical values to alias against (from the sample DB — statewide lists will extend these)

- **district:** Khordha; Bargarh; Ganjam; Koraput; Cuttack; Kandhamal; Sundargarh; Malkangiri; Rayagada
- **scheme:** XV Finance Commission; 5TH STATE FINANCE COMMISSION; Fourteen Finance Commission; Own Funds; 4TH STATE FINANCE SCHEME
- **status:** Activity Approved; WORK ONGOING; WORK COMPLETED; WORK ABANDONED; UNDER APPROVAL
- **plan_type:** Main; Supplementary
- **focus_area:** the 30 Eleventh-Schedule subjects (run `SELECT description FROM dim_code WHERE variable='focus_area'` or ask the PM session for the list)
- **theme:** the 7 LSDG themes in `dim_lsdg_theme` (beware: DB values carry trailing spaces — copy, don't retype)

### Seed examples (delete or keep — they show the intended granularity)

| entity_type | canonical_value | alias | notes |
|---|---|---|---|
| district | Khordha | Khurda | old official spelling |
| district | Khordha | ଖୋର୍ଦ୍ଧା | Odia script |
| scheme | XV Finance Commission | 15th FC | |
| scheme | XV Finance Commission | 15th Finance Commission | |
| scheme | XV Finance Commission | CFC | central FC, as used in activity names |
| scheme | 5TH STATE FINANCE COMMISSION | SFC | as used in activity names — NOTE: also matches 4th SFC; keep an eye on this one |
| status | WORK ONGOING | in progress | |
| status | WORK ONGOING | chalu | colloquial |
| status | WORK COMPLETED | finished | |
| status | WORK COMPLETED | sampurna | colloquial |

---

## What happens after you deliver it

1. The implementing agent loads both sheets as data tables (WP-2/WP-3),
   reconciles Sheet 1 concepts against the workbook SQL, and reports any
   mismatch rather than guessing.
2. A **keyword-coverage profile** runs against the activity text (what % of
   SBM-relevant rows match nothing) — that report tells you where the
   dictionary needs growing, so treat this file as living, not one-shot.
3. Ambiguous aliases and over-matching terms are logged, never silently
   applied (bootstrap rule: validation logs, never fixes).

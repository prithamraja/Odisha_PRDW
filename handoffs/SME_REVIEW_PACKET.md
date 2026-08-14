# SME Review Packet — Ask gold eval set

Everything the domain expert must rule on before eval results can be trusted.
Sources: `handoffs/WP4a_REPORT.md` §4 (full detail) and `eval/gold/*.jsonl`
(the rows; every item below is flagged `sme_review: true` or listed in §4.1/§4.2).
Return format: a marked-up copy of this file is enough.

---

## Part 1 — Seven metric definitions (decide what the words mean)

These decide whether a route is *right at all*. Officers use these words
interchangeably; the database supports more than one arithmetic for each.

| # | Term | The choice to make | Rows affected |
|---|---|---|---|
| M1 | "utilisation" | % of *planned* cost spent (EXP-003) vs % of *sanctioned* cost spent (EXP-023)? Also: "expenditure" as cash out of the account (vouchers) vs booked against the plan (activity_expenditure)? | G1502, G1520 |
| M2 | "completion rate" | Completed ÷ *taken-up*, ÷ *approved*, or ÷ *all planned*? (STS-006 / STS-008 differ) | G1607, G1612, G1907 |
| M3 | "initiated" / "started" / "taken up" | Same status transition or different ones? (IMP-001/002/003 vs STS-*) | G1611, G1617 |
| M4 | "GPDP approved" | The DB has no approval status — approval is proxied by `approval_date` being present. Acceptable as "approved"? | G1010, G1017, G1018 |
| M5 | "CFC utilisation at district level" | Aggregated per block (EXP-020) or per district (EXP-021)? | G1516 |
| M6 | "no activity" | No activity *in this module* (ALR-012) vs no data entry *anywhere* (ALR-013)? | G1704 |
| M7 | "year-wise expenditure of a GP" | TRD-006, TRD-003 and EXP-002 all answer it — all acceptable, or one canonical? | G1512, G1905, G1908 |

## Part 2 — Eleven behavior calls (is asking back the right answer?)

The system currently *clarifies* on each of these. Overruling any changes the
router's behavior, not just the eval score.

| # | Row | Question (as an officer asked it) | Current behavior | The alternative |
|---|---|---|---|---|
| B1 | G1036 | "GPDP status?" (no year) | ask which year | default to latest year |
| B2 | G1521 | "expenditure Andhrua?" (no year) | ask | default to latest year |
| B3 | G1411 | "SFC vs CFC comparison" (no year) | ask | latest year, statewide |
| B4 | G1037 | "How many GPs in **Laxmipur** uploaded…" (Laxmipur is a GP *and* a block) | ask which tier | infer block from "GPs **in** X" |
| B5 | G1038 | "**Bheden** ka plan status 2024-25?" (both tiers) | ask | assume GP |
| B6 | G1909 | "Compare **Laxmipur** and **Kalimela**…" (both are both) | ask | assume block-vs-block |
| B7 | G1203 | "How many soak pits completed?" | ask community vs household | sum both |
| B8 | G1232 | "kitne compost pit complete hue?" | ask community vs household | sum both |
| B9 | G1008 | Year written in Odia numerals `୨୦୨୪-୨୫` | ~~ask~~ **being fixed (D18.P5)** — will answer | — |
| B10 | G1613 | "Which focus area has the lowest completion rate?" | ask for a minimum-activity cut-off | default (e.g. 5) and answer |
| B11 | G1614 | "Which high-expenditure activities haven't started?" | ask what "high" means in ₹ | default (e.g. ₹1 lakh) and answer |

B10/B11 are one policy question: when a judgment number is required, ask or
assume? (PM default per D18.P2: **ask** — overrule once for the class if you
disagree.) B4–B6 are the collision policy (D4): statewide there will be
thousands; current ruling is **ask**, revisit on pilot evidence.

## Part 3 — The 34 Odia rows (ratify or rewrite the phrasing)

Authored by a non-Odia speaker from vocabulary, not fluency. The question for a
native reader: *is this how an officer would actually type it?* Rewrites
welcome directly in this file; row IDs map back to `eval/gold/*.jsonl`.

### 3a. Odia script (19)

| Row | Routes to | Text | Intended meaning |
|---|---|---|---|
| G1006 | PLN-001 | ଖୋର୍ଦ୍ଧା ଜିଲ୍ଲାରେ 2024-2025 ରେ କେତେ ଗ୍ରାମ ପଞ୍ଚାୟତ GPDP ଅପଲୋଡ କରିଛନ୍ତି? | How many GPs in Khordha district uploaded the GPDP in 2024-25? |
| G1008 | PLN-001 | ଆର୍ଥିକ ବର୍ଷ ୨୦୨୪-୨୫ରେ ଖୋର୍ଦ୍ଧାରେ କେତେ GP GPDP ଅପଲୋଡ କରିଛନ୍ତି? | Same, with the year in Odia numerals (digit-handling probe) |
| G1020 | PLN-020 | 2024-2025 ରେ କେଉଁ ବ୍ଲକରେ ସବୁଠାରୁ ଅଧିକ GPDP ଅନୁମୋଦନ ବାକି ଅଛି? | Which block has the most GPDP approvals pending? |
| G1028 | PLN-068 | 2024-2025 ରେ କେଉଁ ଫୋକସ ଏରିଆରେ କୌଣସି ଯୋଜନାବଦ୍ଧ କାର୍ଯ୍ୟ ନାହିଁ? | Which focus area has no planned activity? |
| G1206 | SBM-GWM-003 | 2024-2025 ରେ କେତେ ସାମୁଦାୟିକ ସୋକ୍‌ପିଟ୍ ଯୋଜନା କରାଯାଇଛି? | How many community soak pits planned? |
| G1216 | SBM-SI-006 | 2024-2025 ରେ କେତେ ବ୍ୟକ୍ତିଗତ ଘରୋଇ ଶୌଚାଳୟ ଯୋଜନା କରାଯାଇଛି? | How many individual household toilets (IHHL) planned? |
| G1230 | SBM-OM-004 | 2024-2025 ରେ ପ୍ଲାଷ୍ଟିକ ବର୍ଜ୍ୟବସ୍ତୁ ପରିଚାଳନା ୟୁନିଟ ପାଇଁ କେତେ ଖର୍ଚ୍ଚ ହୋଇଛି? | Spend on plastic waste management units? |
| G1407 | BUD-027 | 2024-2025 ରେ କେଉଁ ଫୋକସ ଏରିଆକୁ କୌଣସି ଯୋଜନାବଦ୍ଧ ଖର୍ଚ୍ଚ ମିଳିନାହିଁ? | Which focus area got no planned expenditure? |
| G1419 | BUD-002 | 2024-2025 ରେ ପ୍ରତ୍ୟେକ ପାଣ୍ଠି ଉତ୍ସରୁ କେତେ ଅର୍ଥ ମିଳିଛି? | How much received from each funding source? |
| G1505 | EXP-028 | 2024-2025 ରେ କେଉଁ ଫୋକସ ଏରିଆରେ ସର୍ବାଧିକ ପ୍ରକୃତ ଖର୍ଚ୍ଚ ହୋଇଛି? | Which focus area has the highest actual expenditure? |
| G1519 | EXP-004 | 2024-2025 ରେ ମୋଟ କେତେ ଟଙ୍କା ଖର୍ଚ୍ଚ ହୋଇନାହିଁ? | How much money is unspent in total? |
| G1611 | IMP-002 | 2024-2025 ରେ ଆରମ୍ଭ ହୋଇଥିବା କେତେ କାର୍ଯ୍ୟ ସମ୍ପୂର୍ଣ୍ଣ ହୋଇଛି? | How many started works are completed? (also M3) |
| G1616 | IMP-011 | 2024-2025 ରେ କେଉଁ ଫୋକସ ଏରିଆରେ ସବୁଠାରୁ ଅଧିକ ଚାଲୁଥିବା କାର୍ଯ୍ୟ ଅଛି? | Which focus area has the most ongoing works? |
| G1704 | ALR-012 | 2024-2025 ରେ ଭୁବନେଶ୍ୱର ବ୍ଲକର କେଉଁ ଗ୍ରାମ ପଞ୍ଚାୟତରେ କୌଣସି କାର୍ଯ୍ୟ ହୋଇନାହିଁ? | Which GPs in Bhubaneswar block had no activity? (also M6) |
| G1809 | SAN-003 | 2024-2025 ରେ ଆନ୍ଧ୍ରୁଆ ପାଇଁ ମୋଟ ପ୍ରଶାସନିକ ମଞ୍ଜୁରୀ ରାଶି କେତେ? | Total administrative sanction amount for Andhrua? |
| G1852 | AST-002 | 2024-2025 ରେ ଭୁବନେଶ୍ୱର ବ୍ଲକରେ ସମ୍ପତ୍ତି ଶ୍ରେଣୀ ଅନୁସାରେ କେତେ ସମ୍ପତ୍ତି ସୃଷ୍ଟି ହୋଇଛି? | Assets created by category in Bhubaneswar block? |
| G1905 | TRD-006 | ଆନ୍ଧ୍ରୁଆର ବର୍ଷ ଅନୁସାରେ ମୋଟ ଖର୍ଚ୍ଚ କେତେ? | Andhrua's year-wise total expenditure (script twin of G1908; also M7) |
| G1974 | *refusal* | 2024-2025 ରେ ଆନ୍ଧ୍ରୁଆରେ କେତେ ହିତାଧିକାରୀ ପେନସନ ପାଇଛନ୍ତି? | How many beneficiaries got pensions in Andhrua? — must refuse honestly, in intelligible Odia |
| G1984 | *fallback* | ଆଜି ଭୁବନେଶ୍ୱରରେ ପାଗ କିପରି ଅଛି? | What's the weather in Bhubaneswar today? — out-of-domain probe |

### 3b. Transliterated / romanized (15)

| Row | Routes to | Text | Intended meaning |
|---|---|---|---|
| G1007 | PLN-001 | Khordha jillare 2024-2025 re kete GP GPDP upload karichanti? | How many GPs in Khordha uploaded the GPDP? |
| G1039 | *refusal* | 2025-26 re kaun kaun blockre GPDP anumodan re barambar bilamba huachi? | Which blocks are repeatedly late on approvals? — no deadline data exists; honest refusal |
| G1214 | SBM-SI-014 | 2024-2025 re kete anganwadi o school re toilet sarichi? | Toilets completed at anganwadis and schools? |
| G1221 | SBM-SWM-027 | 2024-2025 re kete Gobardhan unit sampurna heichi? | Gobardhan units completed? |
| G1415 | FND-001 | 2024-2025 re Andhrua ra kama pain tied o untied panthi kete bhaga heichi? | Tied vs untied fund split for Andhrua's works? |
| G1422 | SCH-005 | 2024-2025 re kaun scheme re sabuthara adhika kharcha heichi Bhubaneswar block re? | Which scheme spent the most in Bhubaneswar block? |
| G1511 | EXP-024 | Andhrua ra 2024-2025 ra receipt, payment o closing balance kete? | Andhrua's receipts, payments, closing balance? |
| G1514 | EXP-036 | 2024-2025 re Andhrua re nua sampati tiari pain kete kharcha heichi? | Spend on creating new assets in Andhrua? |
| G1620 | PHY-004 | 2024-2025 re Bhubaneswar block re kete kama ra physical progress evidence achi? | How many works have physical-progress evidence? |
| G1623 | STS-003 | 2024-2025 re Bhubaneswar block re kete kama sarichi? | How many works finished? (SME: count or rate? — §4.4) |
| G1711 | DQY-004 | 2024-2025 re Khordha re kete activity re funding scheme record hoini? | Activities with no funding scheme recorded? |
| G1804 | SAN-004 | 2024-2025 re Khordha jillare block anusare prashasanika manjuri rashi kete? | Block-wise admin sanction amounts in Khordha? |
| G1860 | AST-001 | Bhubaneswar block ru? | Bare follow-up fragment: "from Bhubaneswar block?" |
| G1908 | TRD-006 | Andhrua ra barsa bhittire mota kharcha kete? | Transliterated twin of G1905 (also M7) |
| G1952 | DSS-005 | 2024-2025 re Bhubaneswar re kaun chalu kama manjuri rashira 25 percent tharu kama kharcha karichi? | Ongoing works that spent <25% of sanction? |

*(One further flagged row is code-mixed Hindi, not Odia: G1018 — "Bhubaneswar
block me GPDP approval rate kitna hai 2024-25 ka?" — flagged for M4, not
language.)*

## Part 4 — Six questions with no clean home (confirm, retarget, or exclude)

See WP4a report §4.4: G1002, G1015, G1030, G1220, G1623, G1005 — including one
genuine catalogue gap (no "how many GPs did NOT upload" count template; the
listing exists as PLN-005).

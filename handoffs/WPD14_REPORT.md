# WP-D14 report — place profile sheets: the build

**Brief:** `handoffs/WPD14_profile_build.md`. **Spec:** `handoffs/PROFILE_SHEET_SPEC.md` (SIGNED, D76).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d14`, results copied back to the Drive repo after each task.
**Commits (on `master`, not pushed):** `d66923f` T1–T4, `2d9da75` T5, `ef41ca0` T6, `b93a121` T5 follow-up, `2e0d68f` T7, then this report (T8).

---

## §0 Status

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | Spec §13 reproduced exactly (three places) | **PASS** | 53 of 53 rows in §2 match, plus the by-year table, the five focus areas, the money source and the profile figures; check 7 green |
| 2 | Appendix A examples character for character | **PASS** | All 45 examples, checked by `--check` (check 7), the gate and 45 subtests; a test also proves the builder's copy of the examples is the brief's text |
| 3 | `--check` green on all seven checks; check 4 compared more than zero at every level | **PASS** | 8 of 8 green (seven checks plus the stamp check); check 4 compared gp 276, block 393, district 507, whole 150 |
| 4 | Gate: baseline plus the new checks green, nothing green turned red; suite green | **PASS** | Gate 34/36 → 40/42: the 6 new checks green, the same two D69 reds; no other line changed. Suite 188 → 235 passed, 0 failed |
| 5 | Two builds give byte-identical store files | **PASS** | Index and part: same SHA-256; the stamp differs only in `generated_at` (§6) |
| 6 | Every existing file in `Insights/metainsights/` unchanged | **PASS** | All 23 files hash the same before and after, in the mirror and in the Drive repo (§10) |
| 7 | Scale table filled in, every target met | **PASS, with one reading for the PM** | Every target met on the reading "one lookup, timed in a fresh process": 0.56 ms median, 0.86 ms p95. **If "lookup" includes opening the store in that fresh process, the p95 is 64.0 ms, over 50 ms** (median 49.0 ms). See §5. I did not change the design. |

**One decision for the PM (§5):** which reading of the 50 ms lookup target holds. If it is "open + lookup", the target is missed at p95 by 14 ms, and the design question is whether checking the store's hashes on open belongs at service start (today's design) or should be made cheaper.

---

## §1 What was built

| Piece | File | What it does |
|---|---|---|
| Builder | `Insights/src/phase5g_profile_sheets.py` | Reads view1, view3, view4. Builds one sheet per Gram Panchayat, block, district and the whole. Writes every sentence and id. Holds the seven checks behind `--check`. |
| Store | `Insights/metainsights/profile_sheets_index.json.gz`, `profile_sheets.part0.bin`, `profile_sheets_stamp.json` | 46 sheets, 2,871 sentences, 0.2 MB in all |
| Reader | `DiscoverChat/profile_store.py` | `available()`, `stamp()`, `get()`, `sentences()`, `sentence()`. Nothing in the service imports it (a test asserts this). |
| Paths | `DiscoverChat/config.py` | Three path constants, nothing else |
| Gate | `DiscoverChat/gates.py` | Six new checks: stamp, add-up, shares, insights, formatter parity, reference |
| Tests | `DiscoverChat/tests/test_profile_sheets.py` | 47 tests (plus 45 subtests, one per Appendix A example) |
| Scale test | `handoffs/WPD14_scale/run_scale.py`, `measurements.json` | Script and measurements; no data |

**Commands** (from the mirror's repo root):

```
python Insights/src/phase5g_profile_sheets.py            # build: 0.5 s inside the script, ~6 s with Python start-up
python Insights/src/phase5g_profile_sheets.py --check    # the seven checks + the stamp check: ~10 s
python -m DiscoverChat.gates                             # 40/42, ~2 min
python -m pytest DiscoverChat/tests -q                   # 235 passed, ~1-2 min
python handoffs/WPD14_scale/run_scale.py                 # T7: ~5 min (most of it is 1,000 fresh processes)
```

**The tool: DuckDB, one thread.** Every part of a sheet is one grouped query per level (`GROUP BY` the level's key), and standing is one window-function query per level and peer group (`RANK()`, `COUNT() OVER`, `quantile_cont() OVER`). Nothing filters or queries inside a loop over places; only writing out the sentences walks the places. One thread so that float sums are always added in the same order, which is what makes two builds byte-identical.

**The store format, and why.** One small index, plus numbered part files. Each sheet is its own zlib-compressed JSON inside a part; the index maps level → code → [part, byte offset, byte length]. So:
- one sheet is read with one `seek` and one `read`, without touching any other sheet;
- a new part starts before any file would pass 95 MB (at 6,800 Gram Panchayats there is still only one part, 40.9 MB);
- zlib and compact JSON in a fixed order give the same bytes every build;
- the reader is standard-library Python only, so opening the store costs ~2 MB.

The index is gzipped (through the corpora's own `write_corpus_json`, which puts no clock in the gzip header). This repo checks out with `core.autocrlf=true` and has no `.gitattributes`, so a plain-JSON index would come back with CRLF line ends on a Windows clone, fail its SHA-256 in the stamp, and the reader would refuse the store. Gzip makes git treat it as binary. (First committed as plain JSON in T5; fixed in the T5 follow-up commit.)

---

## §2 Reference figures (spec §13): expected against actual

Money in rupees; shares to four decimals where the spec gives four. "Middle" is the median of the peer group.

| Place | Row | Expected (spec §13) | Actual (store) | Match |
|---|---|---|---|---|
| Kalimela GP | A1 | 852; 2nd most of 20; middle 602.50 | 852; 2nd most of 20; middle 602.50 | yes |
| Kalimela GP | A2 | 392; share 46.0% | 392; share 46.0% (46.0094%) | yes |
| Kalimela GP | A3 | 76,548,042; 2nd highest of 20; middle 30,986,778 | 76,548,042; 2nd highest of 20; middle 30,986,778 | yes |
| Kalimela GP | A4 | 20,784,410; 2nd highest of 20; middle 13,707,759.50 | 20,784,410; 2nd highest of 20; middle 13,707,759.50 | yes |
| Kalimela GP | A5 | 17,579,894; 2nd highest of 20; middle 12,765,765.30 | 17,579,894; 2nd highest of 20; middle 12,765,765.30 | yes |
| Kalimela GP | A6 | 22.9658%; 5th lowest of 20; middle 42.0457% | 22.9658%; 5th lowest of 20; middle 42.0457% | yes |
| Kalimela GP | A7 | -58,968,148 | -58,968,148 | yes |
| Kalimela GP | E1 | 154; 2nd most of 20; middle 95.50 | 154; 2nd most of 20; middle 95.50 | yes |
| Kalimela GP | E2 | 13; most of 20; middle 0; whole 17 | 13; most of 20; middle 0; whole 17 | yes |
| Kalimela GP | E3 | 22; planned 272,440; top_year 2024-2025; top_year_count 21 | 22; planned 272,440; top_year 2024-2025; top_year_count 21 | yes |
| Kalimela GP | E4 | 129; 2nd most of 20; middle 79; uploads 553 | 129; 2nd most of 20; middle 79; uploads 553 | yes |
| Kalimela GP | E5 | 55; planned 10,426,968; spent 8,963,247; share 86.0% | 55; planned 10,426,968; spent 8,963,247; share 86.0% (85.9622%) | yes |
| Kalimela GP | F1 | 168; most of 20; middle 96; share 19.7% | 168; most of 20; middle 96; share 19.7% (19.7183%) | yes |
| Kalimela GP | F2 | 168 | 168 | yes |
| Kalimela GP | G1 | 46,304,795.56; 5th highest of 20; middle 29,779,715.50 | 46,304,795.56; 5th highest of 20; middle 29,779,715.50 | yes |
| Kalimela GP | G2 | 52,838,871.78; 4th highest of 20; middle 33,647,520.81 | 52,838,871.78; 4th highest of 20; middle 33,647,520.81 | yes |
| Kalimela GP | G3 | 33.2708%; 9th lowest of 20; middle 42.1689% | 33.2708%; 9th lowest of 20; middle 42.1689% | yes |
| Kalimela GP | H1 | 0 | 0 | yes |
| Kalimela GP | H2 | 49; planned 3,490,278 | 49; planned 3,490,278 | yes |
| Kalimela block | A1 | 852; 5th most of 16; middle 712 | 852; 5th most of 16; middle 712 | yes |
| Kalimela block | A3 | 76,548,042; 2nd highest of 16; middle 44,840,248 | 76,548,042; 2nd highest of 16; middle 44,840,248 | yes |
| Kalimela block | A4 | 20,784,410; 5th highest of 16; middle 15,087,289.50 | 20,784,410; 5th highest of 16; middle 15,087,289.50 | yes |
| Kalimela block | A5 | 17,579,894; 5th highest of 16; middle 13,963,300.50 | 17,579,894; 5th highest of 16; middle 13,963,300.50 | yes |
| Kalimela block | A6 | 22.9658%; 4th lowest of 16; middle 36.5570% | 22.9658%; 4th lowest of 16; middle 36.5570% | yes |
| Kalimela block | E1 | 154; 5th most of 16; middle 104 | 154; 5th most of 16; middle 104 | yes |
| Kalimela block | E2 | 13; most of 16; middle 0 | 13; most of 16; middle 0 | yes |
| Kalimela block | E4 | 129; 5th most of 16; middle 83 | 129; 5th most of 16; middle 83 | yes |
| Kalimela block | F1 | 168; 4th most of 16; middle 104 | 168; 4th most of 16; middle 104 | yes |
| Kalimela block | G1 | 46,304,795.56; 6th highest of 16; middle 37,230,713 | 46,304,795.56; 6th highest of 16; middle 37,230,713 | yes |
| Kalimela block | G2 | 52,838,871.78; 5th highest of 16; middle 35,410,176.78 | 52,838,871.78; 5th highest of 16; middle 35,410,176.78 | yes |
| Kalimela block | G3 | 33.2708%; 6th lowest of 16; middle 46.5430% | 33.2708%; 6th lowest of 16; middle 46.5430% | yes |
| The whole | A1 | 12,704 | 12,704 | yes |
| The whole | A2 | 7,074 | 7,074 | yes |
| The whole | A3 | 773,088,536 | 773,088,536 | yes |
| The whole | A4 | 288,438,745 | 288,438,745 | yes |
| The whole | A5 | 253,475,090.46 | 253,475,090.46 | yes |
| The whole | A6 | 32.7873% | 32.7873% | yes |
| The whole | A7 | -519,613,445.54 | -519,613,445.54 | yes |
| The whole | E1 | 2,110 | 2,110 | yes |
| The whole | E2 | 17 | 17 | yes |
| The whole | E3 | 420 | 420 | yes |
| The whole | E4 | 1,675; uploads 8,267 | 1,675; uploads 8,267 | yes |
| The whole | F1 | 2,101 | 2,101 | yes |
| The whole | F2 | 2,095 | 2,095 | yes |
| The whole | G1 | 664,791,435.89 | 664,791,435.89 | yes |
| The whole | G2 | 685,750,811.29 | 685,750,811.29 | yes |
| Rangeilunda block | A3 | 118,410,265 | 118,410,265 | yes |
| Rangeilunda block | A5 | 27,329,118 | 27,329,118 | yes |
| Rangeilunda block | A6 | 23.0800% | 23.0800% | yes |
| Bhubaneswar block | A6 | 55.8936% | 55.8936% | yes |
| Khordha district | A6 | 55.8936% | 55.8936% | yes |
| Kandhamal district | A6 | 16.7013%; lowest of 9 | 16.7013%; lowest of 9 | yes |
| Malkangiri district | A6 | 22.9658% | 22.9658% | yes |

**By year — Kalimela block** (the Gram Panchayat's list is identical; both checked):

| Year | Activities | No cost | Planned | Spent | Share | Match |
|---|---|---|---|---|---|---|
| 2020-2021 | 20 | 0 | 4,490,312 | 4,200,837 | 93.6% | yes |
| 2021-2022 | 32 | 0 | 6,443,270 | 3,320,583 | 51.5% | yes |
| 2022-2023 | 28 | 0 | 3,576,920 | 2,884,416 | 80.6% | yes |
| 2023-2024 | 335 | 196 | 26,182,640 | 2,894,236 | 11.1% | yes |
| 2024-2025 | 268 | 72 | 29,995,250 | 3,159,940 | 10.5% | yes |
| 2025-2026 | 169 | 124 | 5,859,650 | 1,119,882 | 19.1% | yes |

**Five largest focus areas — Kalimela** (activities / planned / spent), all match: Drinking water 166 / 37,376,058 / 6,098,020; Land improvement 57 / 7,395,000 / 0; Maintenance of community system 100 / 6,202,800 / 1,153,867; Sanitation 118 / 5,289,128 / 3,362,022; Roads 27 / 5,218,686 / 1,972,350. Also nothing spent: Poverty allevation programme 114 / 3,709,000 / 0 — matches.

**Money source — Kalimela**, all match: planned tied 9,228,256; planned untied 67,319,786. Sanctioned by scheme: XV Finance Commission 125 approvals, 13,889,087; 5TH STATE FINANCE COMMISSION 41, 6,621,323; Own Funds 2, 274,000. Approved by: BDO 91, Sarpanch 72, Engineer 3, all others 2.

**About the place — Kalimela**, all match: population 10,681; size band "10,000 and above"; 200 households; "ST-majority"; "Near"; 53.4 people per household.

---

## §3 Sentences

Every sentence of the three sheets, in the hand-over order `sentences()` returns. **[note]** marks a row that carries one of the two fixed notes (the note itself is stored once and returned beside the sentence, never inside it).

### Kalimela Gram Panchayat (`p-gp-119936-…`) — 63 sentences

| Id | Sentence |
|---|---|
| `p-gp-119936-A1` | Kalimela Gram Panchayat has 852 planned activities, the 2nd most of 20 Gram Panchayats. The middle value for these 20 is 602.5. |
| `p-gp-119936-A2` | 392 of them (46.0%) have no cost attached. |
| `p-gp-119936-A3` | Its planned cost is Rs 7.65 crore, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 3.10 crore. |
| `p-gp-119936-A4` | Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.37 crore. |
| `p-gp-119936-A5` | It spent Rs 1.76 crore on planned activities, the 2nd highest of 20 Gram Panchayats. The middle value is Rs 1.28 crore. |
| `p-gp-119936-A6` | Spending is 23.0% of the planned cost, the 5th lowest of 20 Gram Panchayats. The middle value is 42.0%. |
| `p-gp-119936-A7` | Spending is Rs 5.90 crore below plan. |
| `p-gp-119936-B-2020-2021` | In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan. |
| `p-gp-119936-B-2021-2022` | In 2021-2022: 32 activities, Rs 64.43 lakh planned, Rs 33.21 lakh spent, 51.5% of the plan. |
| `p-gp-119936-B-2022-2023` | In 2022-2023: 28 activities, Rs 35.77 lakh planned, Rs 28.84 lakh spent, 80.6% of the plan. |
| `p-gp-119936-B-2023-2024` | In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan. |
| `p-gp-119936-B-2024-2025` | In 2024-2025: 268 activities (72 with no cost), Rs 3.00 crore planned, Rs 31.60 lakh spent, 10.5% of the plan. |
| `p-gp-119936-B-2025-2026` | In 2025-2026: 169 activities (124 with no cost), Rs 58.60 lakh planned, Rs 11.20 lakh spent, 19.1% of the plan. |
| `p-gp-119936-C-drinking-water` | Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent. |
| `p-gp-119936-C-land-improvement` | Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent. |
| `p-gp-119936-C-maintenance-of-community-system` | Maintenance of community system: 100 activities, Rs 62.03 lakh planned, Rs 11.54 lakh spent. |
| `p-gp-119936-C-sanitation` | Sanitation: 118 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent. |
| `p-gp-119936-C-roads` | Roads: 27 activities, Rs 52.19 lakh planned, Rs 19.72 lakh spent. |
| `p-gp-119936-C-poverty-allevation-programme` | Poverty allevation programme: 114 activities and Rs 37.09 lakh planned, with nothing spent. |
| `p-gp-119936-C-education` | Education: 42 activities, Rs 29.23 lakh planned, Rs 13.21 lakh spent. |
| `p-gp-119936-C-water-conservation` | Water Conservation: 8 activities, Rs 25.15 lakh planned, Rs 4.21 lakh spent. |
| `p-gp-119936-C-administrative-technical-support` | Administrative & Technical Support: 13 activities, Rs 19.40 lakh planned, Rs 12.23 lakh spent. |
| `p-gp-119936-C-markets-and-fairs` | Markets and fairs: 4 activities, Rs 12.50 lakh planned, Rs 3.47 lakh spent. |
| `p-gp-119936-C-gp-office-infrastructure` | GP Office Infrastructure: 2 activities, Rs 8.84 lakh planned, Rs 8.64 lakh spent. |
| `p-gp-119936-C-health` | Health: 57 activities, Rs 7.71 lakh planned, Rs 5.60 lakh spent. |
| `p-gp-119936-C-women-and-child-development` | Women and child development: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent. |
| `p-gp-119936-C-public-distribution-system` | Public distribution system: 5 activities and Rs 3.00 lakh planned, with nothing spent. |
| `p-gp-119936-C-rural-electrification` | Rural electrification: 7 activities, Rs 1.44 lakh planned, Rs 1.43 lakh spent. |
| `p-gp-119936-C-social-welfare` | Social welfare: 20 activities and Rs 68,500 planned, with nothing spent. |
| `p-gp-119936-C-technical-training-and-vocationa` | Technical training and vocational education: 14 activities, Rs 15,000 planned, Rs 15,000 spent. |
| `p-gp-119936-C-agriculture` | Agriculture: 12 activities, with no planned cost and nothing spent. |
| `p-gp-119936-C-animal-husbandry` | Animal husbandry: 1 activity, with no planned cost and nothing spent. |
| `p-gp-119936-C-fuel-and-fodder` | Fuel and fodder: 5 activities, with no planned cost and nothing spent. |
| `p-gp-119936-C-khadi` | Khadi: 1 activity, with no planned cost and nothing spent. |
| `p-gp-119936-C-non-conventional-energy-sources` | Non-conventional energy sources: 4 activities, with no planned cost and nothing spent. |
| `p-gp-119936-C-rural-housing` | Rural housing: 5 activities, with no planned cost and nothing spent. |
| `p-gp-119936-C-welfare-of-the-weaker-sections` | Welfare of the weaker sections: 15 activities, with no planned cost and nothing spent. |
| `p-gp-119936-CT-4` | Theme 4 - Water Sufficient Village: 174 activities, Rs 3.99 crore planned, Rs 65.19 lakh spent. |
| `p-gp-119936-CT-6` | Theme 6 - Self-sufficient Infrastructure in Village: 310 activities, Rs 2.27 crore planned, Rs 51.51 lakh spent. |
| `p-gp-119936-CT-5` | Theme 5 - Clean and Green Village: 122 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent. |
| `p-gp-119936-CT-8` | Theme 8 - Village with Good Governance: 116 activities, Rs 45.93 lakh planned, Rs 8.64 lakh spent. |
| `p-gp-119936-CT-unmapped` | Unmapped theme: 49 activities, Rs 34.90 lakh planned, Rs 15.70 lakh spent. |
| `p-gp-119936-CT-3` | Theme 3 - Child Friendly Village: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent. |
| `p-gp-119936-CT-1` | Theme 1 - Poverty Free and Enhanced Livelihoods Village: 26 activities, Rs 15,000 planned, Rs 15,000 spent. |
| `p-gp-119936-D-plan` | Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%). |
| `p-gp-119936-DS-xv-finance-commission` | XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned. |
| `p-gp-119936-DS-5th-state-finance-commission` | 5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned. |
| `p-gp-119936-DS-own-funds` | Own Funds: 2 approvals, Rs 2.74 lakh sanctioned. |
| `p-gp-119936-D-authority` | Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2. |
| `p-gp-119936-E1` | 154 works are marked ongoing, the 2nd most of 20 Gram Panchayats. The middle value is 95.5. |
| `p-gp-119936-E2` | 13 works are marked completed, out of 17 in the whole sample. |
| `p-gp-119936-E3` | 22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025. |
| `p-gp-119936-E4` | 129 activities have photo evidence (553 uploads), the 2nd most of 20 Gram Panchayats. The middle value is 79. |
| `p-gp-119936-E5` | 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%). |
| `p-gp-119936-F1` | 168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats. **[note]** |
| `p-gp-119936-F2` | 168 activities have a technical approval on file. |
| `p-gp-119936-G1` | Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out. |
| `p-gp-119936-G3` | 33.3% of the payments are linked to a planned activity. The middle value is 42.2%. |
| `p-gp-119936-H2` | 49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh. |
| `p-gp-119936-H5` | Its profile reports 10,681 people in 200 households, which is 53.4 people per household. **[note]** |
| `p-gp-119936-I1` | Its profile reports a population of 10,681 (size band: 10,000 and above). **[note]** |
| `p-gp-119936-I2` | Its profile reports 200 households. **[note]** |
| `p-gp-119936-I3` | Its profile classes it as ST-majority and as near a bus stop. **[note]** |

### Kalimela block (`p-block-3843-…`) — 61 sentences

| Id | Sentence |
|---|---|
| `p-block-3843-A1` | Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712. |
| `p-block-3843-A2` | 392 of them (46.0%) have no cost attached. |
| `p-block-3843-A3` | Its planned cost is Rs 7.65 crore, the 2nd highest of 16 blocks. The middle value is Rs 4.48 crore. |
| `p-block-3843-A4` | Rs 2.08 crore has been sanctioned for the activities with an approval on file, the 5th highest of 16 blocks. The middle value is Rs 1.51 crore. |
| `p-block-3843-A5` | It spent Rs 1.76 crore on planned activities, the 5th highest of 16 blocks. The middle value is Rs 1.40 crore. |
| `p-block-3843-A6` | Spending is 23.0% of the planned cost, the 4th lowest of 16 blocks. The middle value is 36.6%. |
| `p-block-3843-A7` | Spending is Rs 5.90 crore below plan. |
| `p-block-3843-B-2020-2021` | In 2020-2021: 20 activities, Rs 44.90 lakh planned, Rs 42.01 lakh spent, 93.6% of the plan. |
| `p-block-3843-B-2021-2022` | In 2021-2022: 32 activities, Rs 64.43 lakh planned, Rs 33.21 lakh spent, 51.5% of the plan. |
| `p-block-3843-B-2022-2023` | In 2022-2023: 28 activities, Rs 35.77 lakh planned, Rs 28.84 lakh spent, 80.6% of the plan. |
| `p-block-3843-B-2023-2024` | In 2023-2024: 335 activities (196 with no cost), Rs 2.62 crore planned, Rs 28.94 lakh spent, 11.1% of the plan. |
| `p-block-3843-B-2024-2025` | In 2024-2025: 268 activities (72 with no cost), Rs 3.00 crore planned, Rs 31.60 lakh spent, 10.5% of the plan. |
| `p-block-3843-B-2025-2026` | In 2025-2026: 169 activities (124 with no cost), Rs 58.60 lakh planned, Rs 11.20 lakh spent, 19.1% of the plan. |
| `p-block-3843-C-drinking-water` | Drinking water: 166 activities, Rs 3.74 crore planned, Rs 60.98 lakh spent. |
| `p-block-3843-C-land-improvement` | Land improvement: 57 activities and Rs 73.95 lakh planned, with nothing spent. |
| `p-block-3843-C-maintenance-of-community-system` | Maintenance of community system: 100 activities, Rs 62.03 lakh planned, Rs 11.54 lakh spent. |
| `p-block-3843-C-sanitation` | Sanitation: 118 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent. |
| `p-block-3843-C-roads` | Roads: 27 activities, Rs 52.19 lakh planned, Rs 19.72 lakh spent. |
| `p-block-3843-C-poverty-allevation-programme` | Poverty allevation programme: 114 activities and Rs 37.09 lakh planned, with nothing spent. |
| `p-block-3843-C-education` | Education: 42 activities, Rs 29.23 lakh planned, Rs 13.21 lakh spent. |
| `p-block-3843-C-water-conservation` | Water Conservation: 8 activities, Rs 25.15 lakh planned, Rs 4.21 lakh spent. |
| `p-block-3843-C-administrative-technical-support` | Administrative & Technical Support: 13 activities, Rs 19.40 lakh planned, Rs 12.23 lakh spent. |
| `p-block-3843-C-markets-and-fairs` | Markets and fairs: 4 activities, Rs 12.50 lakh planned, Rs 3.47 lakh spent. |
| `p-block-3843-C-gp-office-infrastructure` | GP Office Infrastructure: 2 activities, Rs 8.84 lakh planned, Rs 8.64 lakh spent. |
| `p-block-3843-C-health` | Health: 57 activities, Rs 7.71 lakh planned, Rs 5.60 lakh spent. |
| `p-block-3843-C-women-and-child-development` | Women and child development: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent. |
| `p-block-3843-C-public-distribution-system` | Public distribution system: 5 activities and Rs 3.00 lakh planned, with nothing spent. |
| `p-block-3843-C-rural-electrification` | Rural electrification: 7 activities, Rs 1.44 lakh planned, Rs 1.43 lakh spent. |
| `p-block-3843-C-social-welfare` | Social welfare: 20 activities and Rs 68,500 planned, with nothing spent. |
| `p-block-3843-C-technical-training-and-vocationa` | Technical training and vocational education: 14 activities, Rs 15,000 planned, Rs 15,000 spent. |
| `p-block-3843-C-agriculture` | Agriculture: 12 activities, with no planned cost and nothing spent. |
| `p-block-3843-C-animal-husbandry` | Animal husbandry: 1 activity, with no planned cost and nothing spent. |
| `p-block-3843-C-fuel-and-fodder` | Fuel and fodder: 5 activities, with no planned cost and nothing spent. |
| `p-block-3843-C-khadi` | Khadi: 1 activity, with no planned cost and nothing spent. |
| `p-block-3843-C-non-conventional-energy-sources` | Non-conventional energy sources: 4 activities, with no planned cost and nothing spent. |
| `p-block-3843-C-rural-housing` | Rural housing: 5 activities, with no planned cost and nothing spent. |
| `p-block-3843-C-welfare-of-the-weaker-sections` | Welfare of the weaker sections: 15 activities, with no planned cost and nothing spent. |
| `p-block-3843-CT-4` | Theme 4 - Water Sufficient Village: 174 activities, Rs 3.99 crore planned, Rs 65.19 lakh spent. |
| `p-block-3843-CT-6` | Theme 6 - Self-sufficient Infrastructure in Village: 310 activities, Rs 2.27 crore planned, Rs 51.51 lakh spent. |
| `p-block-3843-CT-5` | Theme 5 - Clean and Green Village: 122 activities, Rs 52.89 lakh planned, Rs 33.62 lakh spent. |
| `p-block-3843-CT-8` | Theme 8 - Village with Good Governance: 116 activities, Rs 45.93 lakh planned, Rs 8.64 lakh spent. |
| `p-block-3843-CT-unmapped` | Unmapped theme: 49 activities, Rs 34.90 lakh planned, Rs 15.70 lakh spent. |
| `p-block-3843-CT-3` | Theme 3 - Child Friendly Village: 55 activities, Rs 5.46 lakh planned, Rs 98,869 spent. |
| `p-block-3843-CT-1` | Theme 1 - Poverty Free and Enhanced Livelihoods Village: 26 activities, Rs 15,000 planned, Rs 15,000 spent. |
| `p-block-3843-D-plan` | Of the planned cost, Rs 92.28 lakh is tied grant (12.1%) and Rs 6.73 crore is untied grant (87.9%). |
| `p-block-3843-DS-xv-finance-commission` | XV Finance Commission: 125 approvals, Rs 1.39 crore sanctioned. |
| `p-block-3843-DS-5th-state-finance-commission` | 5TH STATE FINANCE COMMISSION: 41 approvals, Rs 66.21 lakh sanctioned. |
| `p-block-3843-DS-own-funds` | Own Funds: 2 approvals, Rs 2.74 lakh sanctioned. |
| `p-block-3843-D-authority` | Approvals on file, by who approved: BDO 91, Sarpanch 72, Engineer 3, all others 2. |
| `p-block-3843-E1` | 154 works are marked ongoing, the 5th most of 16 blocks. The middle value is 104. |
| `p-block-3843-E2` | 13 works are marked completed, out of 17 in the whole sample. |
| `p-block-3843-E3` | 22 works are marked abandoned, with Rs 2.72 lakh planned on them. 21 of them were planned in 2024-2025. |
| `p-block-3843-E4` | 129 activities have photo evidence (553 uploads), the 5th most of 16 blocks. The middle value is 83. |
| `p-block-3843-E5` | 55 works planned in 2022-2023 or earlier are still marked ongoing. Rs 89.63 lakh of their Rs 1.04 crore planned cost has been spent (86.0%). |
| `p-block-3843-F1` | 168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. **[note]** |
| `p-block-3843-F2` | 168 activities have a technical approval on file. |
| `p-block-3843-G1` | Its cashbook shows Rs 4.63 crore received and Rs 5.28 crore paid out. |
| `p-block-3843-G3` | 33.3% of the payments are linked to a planned activity. The middle value is 46.5%. |
| `p-block-3843-H2` | 49 activities have no LSDG theme mapped; their planned cost is Rs 34.90 lakh. |
| `p-block-3843-I4` | Kalimela block has 1 Gram Panchayat in the data. |
| `p-block-3843-J-119936` | Kalimela Gram Panchayat: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan. |

### The whole sample (`p-all-…`) — 78 sentences

| Id | Sentence |
|---|---|
| `p-all-A1` | The whole sample has 12,704 planned activities. |
| `p-all-A2` | 7,074 of them (55.7%) have no cost attached. |
| `p-all-A3` | Its planned cost is Rs 77.31 crore. |
| `p-all-A4` | Rs 28.84 crore has been sanctioned for the activities with an approval on file. |
| `p-all-A5` | It spent Rs 25.35 crore on planned activities. |
| `p-all-A6` | Spending is 32.8% of the planned cost. |
| `p-all-A7` | Spending is Rs 51.96 crore below plan. |
| `p-all-B-2020-2021` | In 2020-2021: 571 activities, Rs 13.20 crore planned, Rs 5.39 crore spent, 40.8% of the plan. |
| `p-all-B-2021-2022` | In 2021-2022: 580 activities, Rs 9.72 crore planned, Rs 4.55 crore spent, 46.8% of the plan. |
| `p-all-B-2022-2023` | In 2022-2023: 609 activities, Rs 7.72 crore planned, Rs 4.44 crore spent, 57.5% of the plan. |
| `p-all-B-2023-2024` | In 2023-2024: 4,607 activities (2,780 with no cost), Rs 21.73 crore planned, Rs 4.19 crore spent, 19.3% of the plan. |
| `p-all-B-2024-2025` | In 2024-2025: 3,423 activities (2,367 with no cost), Rs 11.29 crore planned, Rs 4.26 crore spent, 37.7% of the plan. |
| `p-all-B-2025-2026` | In 2025-2026: 2,914 activities (1,927 with no cost), Rs 13.65 crore planned, Rs 2.52 crore spent, 18.4% of the plan. |
| `p-all-C-drinking-water` | Drinking water: 1,381 activities, Rs 17.40 crore planned, Rs 6.71 crore spent. |
| `p-all-C-sanitation` | Sanitation: 2,101 activities, Rs 13.28 crore planned, Rs 4.74 crore spent. |
| `p-all-C-maintenance-of-community-system` | Maintenance of community system: 1,367 activities, Rs 9.52 crore planned, Rs 2.40 crore spent. |
| `p-all-C-roads` | Roads: 339 activities, Rs 7.92 crore planned, Rs 3.18 crore spent. |
| `p-all-C-education` | Education: 554 activities, Rs 3.79 crore planned, Rs 1.96 crore spent. |
| `p-all-C-women-and-child-development` | Women and child development: 1,041 activities, Rs 3.27 crore planned, Rs 59.08 lakh spent. |
| `p-all-C-land-improvement` | Land improvement: 403 activities, Rs 2.93 crore planned, Rs 45.71 lakh spent. |
| `p-all-C-health` | Health: 1,378 activities, Rs 2.80 crore planned, Rs 71.28 lakh spent. |
| `p-all-C-social-welfare` | Social welfare: 468 activities, Rs 2.70 crore planned, Rs 1.16 crore spent. |
| `p-all-C-water-conservation` | Water Conservation: 194 activities, Rs 2.69 crore planned, Rs 26.72 lakh spent. |
| `p-all-C-rural-housing` | Rural housing: 305 activities and Rs 2.23 crore planned, with nothing spent. |
| `p-all-C-administrative-technical-support` | Administrative & Technical Support: 223 activities, Rs 2.06 crore planned, Rs 87.70 lakh spent. |
| `p-all-C-gp-office-infrastructure` | GP Office Infrastructure: 109 activities, Rs 2.04 crore planned, Rs 1.07 crore spent. |
| `p-all-C-poverty-allevation-programme` | Poverty allevation programme: 1,639 activities, Rs 1.52 crore planned, Rs 7.99 lakh spent. |
| `p-all-C-markets-and-fairs` | Markets and fairs: 36 activities, Rs 91.64 lakh planned, Rs 37.36 lakh spent. |
| `p-all-C-rural-electrification` | Rural electrification: 173 activities, Rs 73.54 lakh planned, Rs 44.36 lakh spent. |
| `p-all-C-agriculture` | Agriculture: 321 activities, Rs 62.96 lakh planned, Rs 2.00 lakh spent. |
| `p-all-C-non-conventional-energy-sources` | Non-conventional energy sources: 26 activities, Rs 18.00 lakh planned, Rs 10.15 lakh spent. |
| `p-all-C-cultural-activities` | Cultural activities: 11 activities, Rs 16.43 lakh planned, Rs 11.80 lakh spent. |
| `p-all-C-technical-training-and-vocationa` | Technical training and vocational education: 213 activities, Rs 14.10 lakh planned, Rs 5.74 lakh spent. |
| `p-all-C-social-forestry-and-farm-forestr` | Social forestry and farm forestry: 21 activities and Rs 13.34 lakh planned, with nothing spent. |
| `p-all-C-animal-husbandry` | Animal husbandry: 33 activities and Rs 8.05 lakh planned, with nothing spent. |
| `p-all-C-libraries` | Libraries: 11 activities, Rs 7.32 lakh planned, Rs 2.14 lakh spent. |
| `p-all-C-welfare-of-the-weaker-sections` | Welfare of the weaker sections: 119 activities and Rs 4.68 lakh planned, with nothing spent. |
| `p-all-C-public-distribution-system` | Public distribution system: 80 activities and Rs 3.20 lakh planned, with nothing spent. |
| `p-all-C-family-welfare` | Family welfare: 5 activities, Rs 3.20 lakh planned, Rs 1.20 lakh spent. |
| `p-all-C-fisheries` | Fisheries: 8 activities and Rs 95,001 planned, with nothing spent. |
| `p-all-C-fuel-and-fodder` | Fuel and fodder: 122 activities, with no planned cost and nothing spent. |
| `p-all-C-khadi` | Khadi: 17 activities, with no planned cost and nothing spent. |
| `p-all-C-small-scale-industries` | Small-scale industries: 6 activities, with no planned cost and nothing spent. |
| `p-all-CT-6` | Theme 6 - Self-sufficient Infrastructure in Village: 4,693 activities, Rs 30.46 crore planned, Rs 10.33 crore spent. |
| `p-all-CT-4` | Theme 4 - Water Sufficient Village: 1,575 activities, Rs 20.09 crore planned, Rs 6.98 crore spent. |
| `p-all-CT-5` | Theme 5 - Clean and Green Village: 2,127 activities, Rs 13.46 crore planned, Rs 4.84 crore spent. |
| `p-all-CT-unmapped` | Unmapped theme: 986 activities, Rs 5.70 crore planned, Rs 1.38 crore spent. |
| `p-all-CT-8` | Theme 8 - Village with Good Governance: 1,748 activities, Rs 3.57 crore planned, Rs 1.15 crore spent. |
| `p-all-CT-3` | Theme 3 - Child Friendly Village: 1,041 activities, Rs 3.27 crore planned, Rs 59.08 lakh spent. |
| `p-all-CT-1` | Theme 1 - Poverty Free and Enhanced Livelihoods Village: 534 activities, Rs 77.06 lakh planned, Rs 7.74 lakh spent. |
| `p-all-D-plan` | Of the planned cost, Rs 17.66 crore is tied grant (22.8%) and Rs 59.64 crore is untied grant (77.2%). |
| `p-all-DS-xv-finance-commission` | XV Finance Commission: 1,502 approvals, Rs 19.80 crore sanctioned. |
| `p-all-DS-5th-state-finance-commission` | 5TH STATE FINANCE COMMISSION: 571 approvals, Rs 8.55 crore sanctioned. |
| `p-all-DS-code-1518` | Code 1518: 22 approvals, Rs 34.53 lakh sanctioned. |
| `p-all-DS-own-funds` | Own Funds: 5 approvals, Rs 10.48 lakh sanctioned. |
| `p-all-DS-code-1526` | Code 1526: 1 approval, Rs 4.49 lakh sanctioned. |
| `p-all-D-authority` | Approvals on file, by who approved: Sarpanch 1,319, BDO 347, Engineer 250, all others 185. |
| `p-all-E1` | 2,110 works are marked ongoing. |
| `p-all-E2` | 17 works are marked completed. |
| `p-all-E3` | 420 works are marked abandoned, with Rs 6.17 crore planned on them. 105 of them were planned in 2023-2024. |
| `p-all-E4` | 1,675 activities have photo evidence (8,267 uploads). |
| `p-all-E5` | 992 works planned in 2022-2023 or earlier are still marked ongoing. Rs 13.93 crore of their Rs 15.61 crore planned cost has been spent (89.2%). |
| `p-all-F1` | 2,101 of the 12,704 activities (16.5%) have an administrative approval on file. **[note]** |
| `p-all-F2` | 2,095 activities have a technical approval on file. |
| `p-all-G1` | Its cashbook shows Rs 66.48 crore received and Rs 68.58 crore paid out. |
| `p-all-G3` | 37.0% of the payments are linked to a planned activity. |
| `p-all-H1` | 140 activities have an approval cost recorded with no approval record. |
| `p-all-H2` | 986 activities have no LSDG theme mapped; their planned cost is Rs 5.70 crore. |
| `p-all-I4` | The whole sample has 9 districts, 16 blocks and 20 Gram Panchayats. |
| `p-all-J-318` | Kandhamal district: 573 activities, Rs 3.48 crore planned, Rs 58.17 lakh spent, 16.7% of the plan. |
| `p-all-J-323` | Malkangiri district: 852 activities, Rs 7.65 crore planned, Rs 1.76 crore spent, 23.0% of the plan. |
| `p-all-J-313` | Ganjam district: 2,723 activities, Rs 23.85 crore planned, Rs 6.00 crore spent, 25.2% of the plan. |
| `p-all-J-322` | Koraput district: 1,455 activities, Rs 9.51 crore planned, Rs 3.16 crore spent, 33.2% of the plan. |
| `p-all-J-306` | Bargarh district: 3,062 activities, Rs 15.16 crore planned, Rs 5.44 crore spent, 35.9% of the plan. |
| `p-all-J-309` | Cuttack district: 1,104 activities, Rs 5.35 crore planned, Rs 2.17 crore spent, 40.5% of the plan. |
| `p-all-J-332` | Sundargarh district: 1,129 activities, Rs 3.88 crore planned, Rs 1.69 crore spent, 43.5% of the plan. |
| `p-all-J-329` | Rayagada district: 490 activities, Rs 2.46 crore planned, Rs 1.22 crore spent, 49.6% of the plan. |
| `p-all-J-321` | Khordha district: 1,316 activities, Rs 5.95 crore planned, Rs 3.33 crore spent, 55.9% of the plan. |

The two notes: F1 → *"An activity with no approval on file is not known to be unapproved; the record may simply be missing."*; H3–H5 and I1–I3 → *"Reported by the Gram Panchayat itself and not checked."*

### Sentence shapes I used that are not in Appendix A

The PM shows these to the operator. Counts are how often each shape occurs in the real store (sample) and in the made-up state of T7.

| # | Shape | Example | Sample | Made-up state |
|---|---|---|---|---|
| 1 | **Singular agreement** wherever a count is 1 (Appendix A's general rule, applied to every pattern): "1 of them (x%) **has** no cost attached", "1 **work is** marked …", "1 **activity has** photo evidence (1 **upload**)", "1 approval", "1 block and 1 Gram Panchayat", "… no LSDG theme mapped; **its** planned cost is …", "1 work planned in … **is** still marked ongoing. … of **its** … planned cost …" | `Code 1526: 1 approval, Rs 4.49 lakh sanctioned.` | 145 | 19,668 |
| 2 | **D-authority with no "all others"** — Appendix A allows it ("no 'all others' when there are none"); listed because it is frequent | `Approvals on file, by who approved: Sarpanch 181.` | 34 | 5,440 |
| 3 | **Joint ranks** (Appendix A gives the words, not an example sentence) | `… the joint 10th most of 20 Gram Panchayats.` | 2 | 5,144 |
| 4 | **A block's statewide sentence** gives its place among the blocks of its district *and* its quarter in the state — the spec states this for Gram Panchayats only; I applied the same rule to blocks | `Block 001 block has 14,210 planned activities, the 2nd most of the 11 blocks in District 01 district and in the highest quarter of the 314 in the state.` | 0 | 2,512 |
| 5 | The state quarter clause names the whole by **the Fact 9 setting**, not the fixed words "the state". With the default setting a >50 sentence would read "… of the 6,800 in the whole sample". T7 ran with `--whole-name "the state"`. | (Gram Panchayat form, as Appendix A) | 0 | 53,380 |
| 6 | **More than 50 peers inside a block or district** (not reached in either store): `in the lowest quarter of the 60 Gram Panchayats in X block` | — | 0 | 0 |
| 7 | **E3 with no planned money on the abandoned works:** `N works are marked abandoned, with no planned cost on them.` | — | 0 | 0 |
| 8 | **E3 singular:** `1 work is marked abandoned, with Rs X planned on it. It was planned in 2024-2025.` and, when only one of several was in the top year, `1 of them was planned in …` | — | 0 | 0 |
| 9 | **B / J with nothing planned and nothing spent:** the two "nothing" forms combined: `In 2025-2026: 5 activities (5 with no cost), nothing planned, nothing spent.` | — | 0 | 0 |
| 10 | **J, a member with no activity:** `X Gram Panchayat: no planned activities.` (B's form) | — | 0 | 0 |
| 11 | **I1 with the size band not reported:** `Its profile reports a population of 3,208.` | — | 0 | 0 |
| 12 | **I3 with one part not reported:** `Its profile classes it as ST-majority.` / `Its profile classes it as near a bus stop.` | — | 0 | 0 |

Shapes that follow Appendix A as written but can print an awkward zero (none occur in either store): E5 when nothing was spent prints `Rs 0 of their Rs X planned cost has been spent (0.0%).`; H2 when the unmapped activities have no cost prints `their planned cost is Rs 0.`; G3 when nothing was spent prints `0.0% of the payments are linked to a planned activity.` I left these as the patterns say; the operator may want a zero form for them.

---

## §4 Checks

### `--check` (final)

```
  profile sheets --check  (C:\dev\odisha-d14\Insights\metainsights)
  PASS  1 equal to the views                   600 Gram Panchayat figures equal the view3 sums (re-summed by pandas) and the view4 lifetime columns
  PASS  2 the parts add up                     1,352 parent figures equal the sum of their members (Gram Panchayat -> block -> district -> whole)
  PASS  3 shares re-derived                    184 shares re-derived from their own parts, 9 places with more than one member; Rangeilunda block 23.1%, not the members' average 28.8%
  PASS  4 equal to the insights                records compared: gp 276, block 393, district 507, all 150; the whole's A7 = d1-00248 (Rs 51.96 crore below plan)
  PASS  5 sentences hold only stored figures   2,871 sentences: every numeral is a stored value through the stored formatter; 760 display strings regenerated; 2,871 ids unique, at most 60 characters, no space or bracket
  PASS  6 every place has a sheet              gp 20, block 16, district 9, all 1 sheets, one per place in the master; 0 with no activity
  PASS  7 reference figures                    83 spec §13 reference figures reproduced; 45 Appendix A examples character for character
  PASS  stamp matches the corpus               candidate set 610cb3d26dff7bf3, as of 2026-09-11T09:31:44Z, 3 view hashes = the decomposition corpus's, 2 files verified

  all green
```

### The gate — baseline against final

| | Baseline (before any change) | Final |
|---|---|---|
| Result | 34/36 green, 2 failed | **40/42 green, 2 failed** |
| Red | `judge-model-evidenced`, `classifier-model-evidenced` (D69, not mine) | the same two, unchanged |
| New | — | `profile-sheets-stamp`, `-add-up`, `-shares`, `-insights`, `-formatter-parity`, `-reference`: all green |
| Changed | — | none: a line-by-line diff of PASS/FAIL names shows only the six additions |

The six new lines as the gate prints them:

```
  PASS  profile-sheets-stamp       the profile sheet store is the one built beside this corpus: same candidate set and view parquets, every file verified (WP-D14)
        candidate set 610cb3d26dff7bf3, as of 2026-09-11T09:31:44Z, 3 view hashes = the decomposition corpus's, 2 files verified
  PASS  profile-sheets-add-up      every profile sheet sum equals the sum of its member places' (spec §9 check 2)
        1,352 parent figures equal the sum of their members (Gram Panchayat -> block -> district -> whole)
  PASS  profile-sheets-shares      every profile sheet share is re-derived from its own parts, never averaged (spec §9 check 3)
        184 shares re-derived from their own parts, 9 places with more than one member; Rangeilunda block 23.1%, not the members' average 28.8%
  PASS  profile-sheets-insights    every profile sheet figure a breakdown also states equals it, at every level (spec §9 check 4)
        records compared: gp 276, block 393, district 507, all 150; the whole's A7 = d1-00248 (Rs 51.96 crore below plan)
  PASS  profile-sheets-formatter-parity every numeral in a profile sheet sentence is a stored figure through the stored formatter (spec §9 check 5)
        2,871 sentences: every numeral is a stored value through the stored formatter; 760 display strings regenerated; 2,871 ids unique, at most 60 characters, no space or bracket
  PASS  profile-sheets-reference   the spec §13 figures and the Appendix A sentences are reproduced exactly (spec §9 check 7)
        83 spec §13 reference figures reproduced; 45 Appendix A examples character for character

  40/42 checks green — 2 FAILED
```

### The suite — baseline against final

| | Baseline | Final |
|---|---|---|
| `python -m pytest DiscoverChat/tests -q` | 188 passed, 63 subtests | **235 passed, 108 subtests, 0 failed** |

(My first baseline run showed one failure, `test_direction.py::RecordedTrialTests::test_every_recorded_attempt_passes_step_5`. It was my mirror missing `handoffs/WPD13b_headline_trial/trial_results.json`; with `handoffs/` copied in, the baseline is 188 passed, 0 failed.)

### Check 4 — records compared per level

| Level | Records compared |
|---|---|
| Gram Panchayat | 276 |
| Block | 393 |
| District | 507 |
| The whole | 150 |
| Plus | the whole's A7 = record `d1-00248`: total −519,613,445.54, display `Rs -51.96 crore` → `Rs 51.96 crore below plan` |

What was compared: every `view3` breakdown whose subspace is empty or one place pair, on the 15 measures the sheet holds (A1–A5, A7, E1–E4, E4 uploads, F1, F2, G1, G2). Totals within the corpus's own tolerance (relative 1e-9, absolute 1e-6); for money, `total_display` must equal the sheet's display string exactly (before the "below plan" words).

### The checks are not vacuous

Tests plant one error each and assert the check fails: a block sum off by Rs 1,000 (check 2), a block's share replaced by its members' average (check 3, Rangeilunda 28.8% instead of 23.1%), a Gram Panchayat's spending off by Rs 50 (check 4), "23.0%" changed to "23.1%" in a sentence and a display string off its value (check 5), a rank changed (check 7). Check 4 also fails when given no records.

---

## §5 Scale test (T7)

**Machine:** Intel Core i5-1250P, 12 cores / 16 logical, 15.7 GB RAM, Windows 11, Python 3.14.0, DuckDB 1.5.1. **Made-up state:** written to `C:\dev\odisha-d14-scale\` (outside the repo, not committed): view1 4,319,360 rows (104 MB), view3 40,800 rows, view4 6,800 rows; made in 66 s.

| Measure | Target | Measured | Met? | Method |
|---|---|---|---|---|
| Build time, parquets to finished store | under 10 minutes | **26.9 s** | yes | Wall clock around the builder process (`--synthetic`), process start to exit: imports, every DuckDB query, writing 451,529 sentences, compressing, writing and hashing the store. The builder's own split: 12.0 s building, 8.9 s writing. |
| Store size on disk | under 300 MB | **41.0 MB** | yes | Sum of the bytes of the index, the part and the stamp (MB = 10^6 bytes) |
| Largest single file | under 95 MB | **40.9 MB** (`profile_sheets.part0.bin`) | yes | File size |
| One lookup by level and code, fresh process, median and p95 over 1,000 random keys | under 50 ms | **0.56 ms median, 0.86 ms p95** (max 1.26 ms) | yes — see the note | 1,000 keys drawn uniformly (seed 14) from all 7,145 sheet keys (948 Gram Panchayats, 44 blocks, 7 districts, 1 whole). Each in a **new Python process**: import the reader, open the store, then time `get(level, code)` alone. |
| (same, counting the open) | — | **open 48.5 ms median, 63.3 ms p95; open + lookup 64.0 ms p95** | **no, on this reading** | Opening = read the stamp, SHA-256 every file (41 MB), load the index. A service does this once at start, not per question. OS file cache warm. |
| Memory added by opening the store | under 100 MB | **2.0 MB median, 2.2 MB max** | yes | psutil RSS in each of the same 1,000 processes, after importing the reader and before opening; then after opening and one `get()` |
| Sheets written | 6,800 + 314 + 30 + 1 | **6,800 + 314 + 30 + 1** | yes | The stamp's counts; check 6 confirms one per place in the made-up master |

**Checks 2, 3, 5 and 6 on the made-up store: all green** (25.5 s): 17,940 parent figures add up; 28,580 shares re-derived; 451,529 sentences hold only stored figures, ids unique and within the rules; every one of the 7,145 places has a sheet.

**Size against the spec's estimate (§8.5):** about 62 sentences per Gram Panchayat (420,580 / 6,800), close to the PM's estimate of 60; 451,529 sentences in all against an estimate of ~430,000.

**The lookup-target reading (for the PM).** The brief's table says "one lookup by level and code, fresh process". I measured the lookup itself in a fresh process (0.86 ms p95), and separately what opening the store costs in that process (63.3 ms p95, almost all of it hashing the 41 MB part to prove it unaltered). Spec §8.1 says "the service gets that sheet … in under 50 ms", which the first reading meets by a factor of 50. If the PM means the second, the target is missed at p95 and this is a STOP: options would be to keep verifying once at service start (today's design; costs ~60 ms at boot), or to check hashes less often. I changed nothing.

**Notes on the made-up state.** The made-up block names are "Block 001" etc., so sentences read "Block 093 block" — an artefact of my naming, not of the builder. Counts were left unscaled (as the brief says), so large ties appear (5,144 sentences say "joint").

---

## §6 Determinism

Two fresh builds from the same views, five seconds apart, into a scratch folder; then compared with the committed store:

| File | Build 1 SHA-256 | Build 2 SHA-256 | Committed | Same? |
|---|---|---|---|---|
| `profile_sheets.part0.bin` | `d78a55f45376a913bfb9778629608f3a8b4d9316d8959e7440e2b0d53d2a673c` | `d78a55f4…2a673c` | `d78a55f4…2a673c` | yes |
| `profile_sheets_index.json.gz` | `b8a9598d7d03cc83870a6460a7686d7cc4214aee9b1216a50ff55eebfffb00cc` | `b8a9598d…fb00cc` | `b8a9598d…fb00cc` | yes |
| `profile_sheets_stamp.json` | `2c201c9d…063a54` | `6f96b9a7…f994e2` | — | differs in one line only |

`diff` of the two stamps:

```
51c51
<   "generated_at": "2026-11-24T10:29:47Z"
---
>   "generated_at": "2026-11-24T10:29:52Z"
```

The stamp holds no build time for this reason. One caveat: the stamp is plain JSON, so a Windows checkout with `core.autocrlf=true` gives it CRLF line ends. Nothing hashes the stamp and it parses the same, so this is harmless, but a byte comparison of a fresh build against a Windows checkout would show it.

---

## §7 Decision journal

| Decision | Options | Choice | Cost of reversing |
|---|---|---|---|
| Tool | pandas; DuckDB | **DuckDB**, single thread, for every aggregation; pandas only as the independent path in check 1 | Low: the queries are SQL strings in one file |
| Store format | SQLite; one JSON file per place; one big JSON; **index + parts of independently compressed sheets** | Index + parts: one sheet read alone, deterministic bytes, split by size, stdlib reader. SQLite's file bytes depend on the library version; 7,145 files in git is unwieldy; one big JSON breaks "read one sheet without the others" | Medium: reader and writer both change, nothing else |
| Index encoding | plain JSON; **gzipped JSON** | Gzipped, because `core.autocrlf=true` would break the hash of a plain-JSON index on a Windows clone | Low |
| Where the format lives | builder; reader; a new module | Reader owns the file names and id pattern (stdlib only); the builder imports them. A new module was not in the file list | Low |
| Where the checks live | builder; gate | Builder (`check_*` functions); the gate imports and calls them, so `--check` and the gate run the same code | Low |
| When the reader verifies | every lookup; **once per process, on first use** | Once: reads the stamp, hashes every file, loads the index. That is the 48.5 ms "open" in §5 | Low; see §5 |
| Which view hashes the builder compares | all four; **the three it reads** | View1, view3, view4. The builder never reads view2 (R3 puts the by-year list on view3) | Low |
| Spec §13 reference figures in code | in a data file; **in the builder, as a fixed table used only by check 7** | The table states the sample's size (20, 16, 9), which D15 keeps out of code. It is an expectation, not logic; nothing in the build reads it. No data file was in the allowed file list | Low: move the table |
| Ties in ordering | — | C by planned cost then name; schemes by amount then name; authorities by count then name; J by A6 from the lowest, blanks last, then name, then code; E3's top year: most, then earliest (brief) | Low |
| "Number tied" | count including itself; **others with the same value** | `tied_with` = peers with the same value, not counting the place; "joint" when it is above 0 | Low |
| Slug edges | — | Leading and trailing hyphens dropped before and after the 32-character cut (`(not recorded)` → `not-recorded`) | Low; ids would change |
| A null focus area, theme, scheme or authority | drop; **label** | Labelled `(not recorded)`, phase5f's own label. None occurs in the sample | Low |
| Profile counts of 0 | treat as a value; **treat as not reported** | view4 fills an unreported count with 0 (`COALESCE(…, 0)`). So I1 and I2 have no sentence at 0, and H3/H4 need households above 0 (else "200 toilets for 0 households" would fire on a missing figure) | Low |
| E5's cut-off year | arithmetic on the clock; **from the years in the data** | The latest year whose start is at least 3 before the latest year's start, chosen from view3's own fiscal years, so it is printed as stored | Low |
| The whole's name in a >50-peer clause | the fixed words "the state"; **the Fact 9 setting** | The setting, so one switch changes every sentence (§3 shape 5) | Low |
| State quarter for blocks | Gram Panchayats only; **blocks too** | The spec's rule for Gram Panchayats applied to blocks (§3 shape 4) | Low |
| Commit split | one commit per task | T1–T4 in one commit: they are one file, and it imports the reader's constants, so the reader came in the same commit. The gzip fix is a separate T5 follow-up commit | — |

---

## §8 Data oddities (beyond spec §12) — logged, not fixed

1. **19 activities not marked abandoned carry a non-zero `fund_abandoned_total`**, Rs 32.85 lakh of the whole's Rs 6.17 crore: Bandhpali (8 rows: 6 "WORK ONGOING", 2 with the status "Buildings"), Kalyansinghpur (8: 7 ongoing, 1 "UNDER APPROVAL"), Hirlipali (2), Bheden (1). E3's "planned on them" is the spec's sum of `fund_abandoned_total`, so for these four places it includes money on works that are not abandoned. Kalimela is unaffected (its Rs 2.72 lakh matches §13). Every abandoned row does carry its amount (0 of 420 at zero).
2. **A status value "Buildings"** appears on 2 Bandhpali rows — it reads like an asset type, not a stage of work.
3. **The sanctioned-scheme field holds two codes, not names:** "Code 1518" (22 approvals, Rs 34.53 lakh) and "Code 1526" (1 approval, Rs 4.49 lakh). They appear as written on the whole's sheet and on the sheets of the places that hold them.
4. **More stray approving-authority spellings than spec §12 item 6 lists:** besides "sar" and "sarapacnh", also "SARAPNCH", "SWARPANCH", "S", "12" (5 approvals), "14", "15", "KALYANSINGHPUR" (2), "GRAMPANCHAYATKS". "Gram Panchayat" (170) is a separate, clean-looking value. On the whole's sheet they all fall into "all others 185".
5. **Kalyansinghpur's profile reports 4,051 households for 2,049 people** (0.5 people per household). H5 only catches more than 20; the reverse is not a check the spec holds. Karuabahal (12 households for 3,208 people, 267.3 per household; 1,256 toilets) does fire H3 and H5.
6. **The breakdown corpus resolves blocks and districts by name only.** A record's `geography` holds `gp_lgd_codes` for a Gram Panchayat but only names (`blocks: ['Attabira']`) for blocks and districts. Check 4 therefore matches blocks and districts by name *within the level* (the subspace dimension says which level), and asserts every name is unique within its level. Four names that are both a Gram Panchayat and a block cannot be confused this way.
7. **The money formatter rounds across a unit boundary:** `format_measure` prints 99,999.99 as `Rs 1,00,000` and 9,999,999.99 as `Rs 100.00 lakh`. Not reached by any figure I saw; noted because the sheets print through it.
8. **A trailing space in a theme name** (`Theme 5 - Clean and Green Village `) — trimmed for display, as Fact 10 says; logged by the builder on every run.

---

## §9 Where the spec or the brief was wrong, or silent (proposed changes; I did not edit the spec)

1. **Check 4 "match places by the record's resolved codes"** — the corpus has resolved codes for Gram Panchayats only (§8 item 6). Propose: "by code for a Gram Panchayat, by level and name for a block or district".
2. **The 50 ms lookup target** — "fresh process" can be read as including the store's open (§5). Propose the spec says which: per lookup after open (met, 0.86 ms p95), or open + lookup (64 ms p95, missed).
3. **Spec §2 rule 2 names four views; the sheets read three.** view2 is never read (R3 moved the by-year list to view3). Propose: "built from view1, view3 and view4".
4. **G3's pattern carries a middle value but no standing clause; F1's carries a standing clause but no middle value.** Both are as written and approved; the PM may want them to match the other ranked rows. E2, G1 and G2 have standings stored but no sentence uses them — also as written.
5. **Zero forms missing for E5 (nothing spent), H2 (no planned cost) and G3 (nothing spent)** — §3, last paragraph.
6. **Appendix A's ">50 peers … in the state"** is written with a fixed "the state", while Fact 9 makes the whole's name a setting. I used the setting (§3 shape 5). Propose the appendix say "in {the whole}".
7. **The spec's "statewide, a Gram Panchayat sentence gives its place in the block and its quarter in the state"** says nothing about blocks. I applied it to blocks too (§3 shape 4). Propose the spec say so, or say not.
8. **Store files and line ends.** The brief's "two builds give byte-identical store files" holds for the build output; a Windows checkout rewrites text files (`core.autocrlf=true`, no `.gitattributes`). I gzipped the index so its hash survives; the stamp stays plain text. A repo-level `.gitattributes` would settle it but was outside my file list.

---

## §10 Files

**Touched (all committed, not pushed):**

| File | Change |
|---|---|
| `Insights/src/phase5g_profile_sheets.py` | new — builder and `--check` |
| `Insights/metainsights/profile_sheets_index.json.gz` | new — the index |
| `Insights/metainsights/profile_sheets.part0.bin` | new — the sheets |
| `Insights/metainsights/profile_sheets_stamp.json` | new — the stamp |
| `DiscoverChat/profile_store.py` | new — the reader |
| `DiscoverChat/config.py` | +6 lines: the three path constants and a comment |
| `DiscoverChat/gates.py` | +49 lines: six checks and one helper, nothing else changed |
| `DiscoverChat/tests/test_profile_sheets.py` | new — 47 tests |
| `handoffs/WPD14_scale/run_scale.py`, `measurements.json` | new — the scale test and its numbers, no data |
| `handoffs/WPD14_REPORT.md` | new — this report |

(`Insights/metainsights/profile_sheets_index.json` was committed in T5 as plain JSON and removed in the T5 follow-up.)

**Not touched:** `Data/**` (not read), `Insights/domain_pack_prdw/**`, `build_views.py`, every other file in `Insights/src/`, `DiscoverChat/main.py`, `assemble.py`, `writer.py`, `judge.py`, `checks.py`, `layout.py`, `render.py`, `classifier.py`, `retrieval.py`, `corpus.py`, `glossary.py`, `context_brief.py`, `Ask/**`, `frontend/**`, `deploy/**`, every `.env`, `handoffs/PROJECT_PLAN.md`, `handoffs/PROFILE_SHEET_SPEC.md`, `Insights/DISCOVER_VIEW_MAPPING.md`. No model call, no embedding call, no API key.

**Every existing file in `Insights/metainsights/` unchanged.** SHA-256 of all 23 files taken before any change (`C:\dev\odisha-d14-metainsights-before.txt`) and re-checked at the end: 23 of 23 OK in the mirror, 23 of 23 OK in the Drive repo.

**Not mine, left alone:** the uncommitted `handoffs/PROJECT_PLAN.md` change, `DiscoverChat/experiments/**` (the operator's writer tests), `handoffs/Kalimela insights.pdf`, `handoffs/PROFILE_SHEET_SPEC.md`, `handoffs/WPD14_profile_build.md` (the PM's, still uncommitted).

**What the PM should replay** (in a fresh mirror with the four view parquets from `C:\dev\odisha-d11b\Insights\views_prdw\`):

```
python Insights/src/phase5g_profile_sheets.py           # rebuild; compare the part and index hashes with §6
python Insights/src/phase5g_profile_sheets.py --check   # 8 of 8 green
python -m DiscoverChat.gates                            # 40/42, only the two D69 reds
python -m pytest DiscoverChat/tests -q                  # 235 passed
```

Then show the operator §3.

Baseline and final outputs are kept beside the mirror: `C:\dev\odisha-d14-baseline-gates.txt`, `-baseline-pytest.txt`, `-final-gates.txt`, `-final-pytest.txt`, `-check.txt`, `-scale-run.txt`.

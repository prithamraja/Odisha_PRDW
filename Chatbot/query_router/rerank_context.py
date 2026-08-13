"""
Family descriptions for the re-ranker's "↳" line.

The re-ranker shows each candidate as

    S02: Which farmers are in {scheme} but not in {scheme_2}?
        ↳ <desc>
        accepts filters: scheme, scheme_2

and its system prompt tells the model to judge a candidate by the ↳ description
rather than by surface word overlap. This module supplies those descriptions.

WHY IT EXISTS
    Without a ↳ line the model word-matches. The defect this module was written
    for: "Which farmers are in Fisheries but not Sericulture?" retrieved S02
    correctly but the model picked Q122 ("registered both as fishers and as crop
    farmers") — same nouns, inverted set logic. Descriptions that say "difference
    / but NOT" against "overlap / in BOTH" are what separates them.

CONTRACT (mirrors _RERANK_SYS in reranker.py — do not break it)
    - A description describes a question FAMILY, not one template. Sibling
      parameter variants (G10-S / G10-D / G10-M) share one family and therefore
      repeat the same description word-for-word. The model picks the family by
      ↳ and then the variant by `accepts filters:`.
    - ONE line, no newlines: the candidate listing is line-oriented.
    - Every one of the 278 templates must have a non-empty description, and no
      template may appear in two families. tests/test_rerank_context.py enforces
      both, plus that the member ids all exist in TEMPLATE_CATALOG.

AUTHORING ORDER (what a description says, most important first)
    1. What the answer is — the measure and the row grain.
    2. Which dataset(s) it reads: pm_kisan (roster), agriculture (input/seed
       subsidy + eCrop), horticulture_apmip (micro-irrigation), fisheries,
       sericulture, markfed (MSP procurement), ryss (natural farming),
       survey_land_records.
    3. The logical relation where one exists — difference / intersection /
       absence-from-roster / reconciliation mismatch.
    4. Optionally one or two short example phrasings.

    Examples stay generic for families whose siblings accept different filter
    values, so an example can never name a value only a sibling can bind.

SEVEN SCHEMES
    PM-KISAN is a scheme, the seventh, alongside Agriculture, Horticulture,
    Fisheries, Sericulture, MARKFED and RySS. Scheme-count families say counts
    include it. The families that deliberately measure the six STATE schemes
    against the PM-KISAN roster say so explicitly — that contrast is what keeps
    G35 ("nothing from any state scheme") apart from S02 with scheme=PM-KISAN.
"""

_SEVEN = ("PM-KISAN, Agriculture, Horticulture, Fisheries, Sericulture, "
          "MARKFED, RySS")

FAMILY_DESCRIPTIONS: dict[str, dict] = {

    # ══ Scheme set logic — the collision-prone core ═══════════════════════
    "scheme_set_difference": {
        "desc": "Farmers enrolled in one named scheme and MISSING from a second "
                "named scheme: a set DIFFERENCE ('in X but NOT in Y'), never an "
                "intersection and never an overlap count. Two schemes are named "
                "and both are slots; either may be any of " + _SEVEN + ". "
                "e.g. 'in Fisheries but not Sericulture', 'in RySS but not PM-KISAN'.",
        "members": ["S02"],
    },
    "roster_minus_one_scheme": {
        "desc": "PM-KISAN roster members who are NOT in ONE named scheme — a "
                "difference whose left side is always the whole roster, so only "
                "one scheme is named. Use when 'PM-KISAN farmers' is the subject "
                "and a single other scheme is the thing they are missing from; if "
                "the query names TWO schemes as operands it is the two-scheme "
                "difference family instead. The scheme slot accepts all seven "
                "values; scheme=PM-KISAN is answered here and correctly comes back "
                "empty. e.g. 'which PM-KISAN farmers are not in Sericulture', "
                "'roster farmers never reached by this programme'. Also answers "
                "COMPLETENESS questions about this same relation — 'are all "
                "PM-KISAN farmers present in this scheme', 'is every roster farmer "
                "also in this scheme', 'do all roster farmers appear here' — which "
                "are the same difference asked as a yes/no: the answer is the list "
                "of roster farmers missing from the scheme, and an empty result "
                "means yes, all of them are present. A yes/no phrasing never makes "
                "a question unanswerable.",
        "members": ["S01"],
    },
    "scheme_membership_list": {
        "desc": "The membership roll of ONE named scheme — every farmer registered "
                "in it, with their roster details where they have them. A plain "
                "list, no set logic, no amounts. The scheme is a slot and may be "
                "any of " + _SEVEN + " (PM-KISAN returns the whole roster). "
                "e.g. 'which farmers are registered in this scheme', 'who is "
                "enrolled in this programme'.",
        "members": ["S07"],
    },
    "scheme_aadhaar_off_roster": {
        "desc": "Aadhaar numbers present in ONE named scheme's own data but ABSENT "
                "from the PM-KISAN roster — that scheme's off-roster beneficiaries. "
                "Measures a scheme AGAINST the roster, so the roster is the fixed "
                "right-hand side rather than a second operand. The scheme slot "
                "accepts all seven values, PM-KISAN included: that case is answered "
                "here and correctly comes back empty (roster minus roster). e.g. "
                "'Aadhaar numbers in this scheme that do not exist in PM-KISAN'.",
        "members": ["S03"],
    },
    "scheme_count_ranking": {
        "desc": "Farmers ranked by HOW MANY schemes they are enrolled in — one row "
                "per farmer with a scheme count and the scheme names, biggest first. "
                "Membership breadth, not money. Counts are over all seven schemes "
                "and include PM-KISAN, so a roster member scores one higher than "
                "they used to. e.g. 'rank farmers by number of schemes enrolled', "
                "'who touches the most programmes'.",
        "members": ["S04"],
    },
    "scheme_participations_by_district": {
        "desc": "Districts ranked by TOTAL scheme participations — one farmer in "
                "four schemes contributes four, so this counts enrolments and not "
                "people (the farmer count sits alongside for comparison). Over all "
                "seven schemes including PM-KISAN. e.g. 'which district has the "
                "most total scheme participations', 'where is scheme activity "
                "concentrated'.",
        "members": ["S05"],
    },
    "social_category_scheme_coverage": {
        "desc": "Farmers of ONE named social category (SC/ST/BC/OC) and which "
                "schemes cover each of them — one row per farmer with their scheme "
                "list, across all seven schemes including PM-KISAN. e.g. 'which ST "
                "farmers exist and which schemes cover them'.",
        "members": ["S06"],
    },
    "scheme_count_exact": {
        "desc": "Farmers enrolled in EXACTLY a given number of schemes, with the "
                "scheme names listed — the convergence extremes ('all of them', "
                "'only one'). Counts run over all seven schemes and include "
                "PM-KISAN, so a farmer in every AP programme plus the roster counts "
                "7, and a query saying 'all six AP schemes' should still be read as "
                "the maximum-convergence question. e.g. 'which farmer participates "
                "in all the schemes', 'farmers enrolled in exactly N schemes'.",
        "members": ["Q114"],
    },
    "scheme_count_single": {
        "desc": "Farmers whose scheme count is exactly one (or the given small "
                "number) AND which single scheme it is — the least-converged "
                "beneficiaries, named. Counts include PM-KISAN, so roster-only "
                "farmers now appear here with scheme 'PM-KISAN'. e.g. "
                "'single-scheme farmers', 'which one scheme is this farmer's only one'.",
        "members": ["Q115"],
    },
    "scheme_count_distribution": {
        "desc": "The HISTOGRAM of farmers by number of schemes — how many farmers "
                "are in 1, 2, 3+ schemes, as a distribution table, not a farmer "
                "list. Counts include PM-KISAN. A STATEWIDE aggregate over the "
                "whole population: a question that names ONE farmer ('how many "
                "schemes is this farmer enrolled in') is a per-farmer lookup and "
                "belongs to the single-farmer membership families, never here. "
                "e.g. 'distribution of farmers by number of schemes enrolled', "
                "'scheme-count histogram'.",
        "members": ["Q016"],
    },
    "scheme_participation_matrix": {
        "desc": "The scheme participation MATRIX: one row per farmer with a 0/1 "
                "column per programme (pm_kisan, agriculture, horticulture, "
                "fisheries, sericulture, markfed, ryss) plus a total. The backbone "
                "view every other convergence question filters. The pm_kisan column "
                "is 1 for everyone on the roster, which is the point of the spine. "
                "e.g. 'scheme participation matrix', 'for every farmer, which "
                "programmes are they in'.",
        "members": ["Q113"],
    },
    "farmer_scheme_membership_lookup": {
        "desc": "Which schemes ONE farmer is in, looked up by name (and village "
                "where given) — membership across the seven schemes, not amounts. "
                "e.g. 'which schemes is this farmer enrolled in', 'how many schemes "
                "is this farmer in'.",
        "members": ["Q125"],
    },
    "farmer_dataset_presence": {
        "desc": "A presence matrix for ONE named farmer across all eight datasets — "
                "Yes/No per dataset, so the answer is which datasets hold them and "
                "which they are MISSING from. Membership only, no money. Resolves "
                "the name across every dataset rather than starting from the roster, "
                "so a 'No' in the pm_kisan column is itself the finding. e.g. "
                "'which datasets is this farmer missing from', 'how many schemes is "
                "this farmer in'.",
        "members": ["F09"],
    },
    "scheme_pair_overlap": {
        "desc": "Which PAIRS of schemes overlap most in the farmers they serve — "
                "one row per scheme pair with the count of farmers in BOTH, ranked. "
                "An intersection measured across every pair at once, not a named-pair "
                "list and not a difference. Includes PM-KISAN, so PM-KISAN×X pairs "
                "top the list because the roster is the spine. ALSO the right answer "
                "to a HOW-MANY question about two named schemes with NO crop named — "
                "'how many input-subsidy farmers also sold produce to MARKFED' is "
                "read off this table's Agriculture × MARKFED row. The crop-narrowed "
                "input-to-market family needs a crop to bind and must not be used "
                "when none is given. e.g. 'which pairs of schemes overlap the most', "
                "'which programmes share beneficiaries', 'how many farmers are in "
                "both Agriculture and MARKFED'.",
        "members": ["Q118"],
    },
    "scheme_exclusive_reach": {
        "desc": "For each of the six AP STATE schemes, how many farmers it serves "
                "that NO OTHER state scheme reaches — one row per scheme giving its "
                "exclusive beneficiary count. Uniqueness, the complement of overlap. "
                "The PM-KISAN roster is deliberately EXCLUDED from the count: it is "
                "the near-universal spine, so counting it would give every roster "
                "farmer a second scheme and drive every exclusive count to zero. "
                "e.g. 'how many farmers does each scheme serve that no other scheme "
                "reaches', 'unique reach of each programme'.",
        "members": ["Q126"],
    },
    "fisheries_agriculture_overlap": {
        "desc": "Households registered in BOTH fisheries AND the crop input-subsidy "
                "data — an INTERSECTION of two fixed datasets (fisheries ∩ "
                "agriculture), dual-livelihood farmers. Not a difference: it never "
                "answers 'in fisheries but NOT in something'. e.g. 'Aadhaar numbers "
                "that appear both as fisheries registrants and crop input-subsidy "
                "recipients'.",
        "members": ["Q122"],
    },
    "sericulture_markfed_overlap": {
        "desc": "Sericulture farmers who ALSO sell produce through MARKFED — an "
                "INTERSECTION of two fixed datasets (sericulture ∩ markfed), "
                "diversified-income farmers. Not a difference. e.g. 'which "
                "sericulture farmers also sell through procurement'.",
        "members": ["Q123"],
    },
    "horticulture_agriculture_overlap": {
        "desc": "Farmers who took BOTH a micro-irrigation subsidy AND an input "
                "subsidy in one crop year — an INTERSECTION of horticulture_apmip "
                "and agriculture, filtered to the named year. Not a difference. "
                "e.g. 'who got both a drip subsidy and a seed subsidy that year'.",
        "members": ["Q121"],
    },
    "crop_input_to_procurement_overlap": {
        "desc": "For ONE NAMED CROP, farmers who took an input subsidy AND also "
                "sold that produce to MARKFED — the full input-to-market cycle, an "
                "INTERSECTION of agriculture and markfed narrowed to a crop slot. "
                "ONLY when a crop is actually named. A crop-less version of the "
                "same question — 'how many input-subsidy farmers also sold to "
                "MARKFED' — has nothing to bind the crop slot to and belongs to the "
                "scheme-pair overlap family, whose Agriculture x MARKFED row is "
                "exactly that all-crops answer. e.g. 'which paddy farmers took "
                "subsidy and also sold to procurement'.",
        "members": ["Q098"],
    },
    "natural_farming_input_subsidy_contradiction": {
        "desc": "RySS natural-farming members who are STILL drawing chemical input "
                "subsidies — an INTERSECTION of ryss and agriculture surfaced as a "
                "policy contradiction (the state pays for conversion and for "
                "purchased inputs on the same plot). e.g. 'which natural farming "
                "members still take input subsidies'.",
        "members": ["Q117"],
    },

    # ══ Absence from the PM-KISAN roster (the six STATE schemes vs the spine) ══
    "state_scheme_beneficiaries_off_roster": {
        "desc": "People drawing benefits from the six STATE schemes (agriculture, "
                "horticulture, fisheries, sericulture, markfed, ryss) whose Aadhaar "
                "is NOT on the PM-KISAN roster at all — off-roster beneficiaries, "
                "across every scheme at once rather than one named scheme. The "
                "roster is the comparison target here, not one of the operands, so "
                "PM-KISAN is deliberately excluded from the scheme set. Legitimate "
                "cases exist (tenants, landless fishers). e.g. 'which farmers "
                "receive AP scheme benefits but are not in PM-KISAN'.",
        "members": ["Q059"],
    },
    "off_roster_benefit_value": {
        "desc": "The total MONEY that has gone to Aadhaar numbers not on the "
                "PM-KISAN roster — one amount (with a scheme split) sizing the "
                "off-roster exposure, over the six STATE schemes measured against "
                "the roster. The ₹ counterpart of the off-roster beneficiary list. "
                "e.g. 'how much money has gone to Aadhaar numbers not on the roster'.",
        "members": ["Q129"],
    },
    "fisheries_off_roster": {
        "desc": "Fisheries registrants who are NOT on the PM-KISAN roster — the "
                "off-roster check for fisheries specifically, no scheme slot. "
                "Expected non-empty and largely legitimate: fishers often hold no "
                "agricultural land. e.g. 'list Aadhaar numbers in fisheries that "
                "do not exist in PM-KISAN'.",
        "members": ["Q135"],
    },
    "markfed_off_roster": {
        "desc": "MARKFED procurement suppliers who are NOT on the PM-KISAN roster — "
                "the off-roster check for procurement specifically, no scheme slot. "
                "Traders selling as farmers is the leakage route this looks for. "
                "DIRECTION MATTERS: the population is MARKFED and the roster is "
                "what it is checked against. If the question makes the ROSTER the "
                "subject — 'are all PM-KISAN farmers present in MARKFED', 'which "
                "roster farmers are missing from MARKFED' — it is the opposite "
                "difference and belongs to the roster-minus-one-scheme family. e.g. "
                "'which MARKFED suppliers have no PM-KISAN record'.",
        "members": ["Q112"],
    },
    "land_records_off_roster": {
        "desc": "Survey land records whose PATTADAR is not on the PM-KISAN roster — "
                "land exists but the title holder receives nothing, the reverse of "
                "the usual exclusion check. Reads survey_land_records against "
                "pm_kisan by name and village (survey records carry no Aadhaar). "
                "e.g. 'are there land records for farmers missing from PM-KISAN'.",
        "members": ["M06"],
    },
    "unreached_by_any_state_scheme": {
        "desc": "PM-KISAN roster farmers who receive NOTHING from any of the six "
                "STATE schemes — the core exclusion list, one row per completely "
                "unreached farmer. PM-KISAN is the population being tested, not one "
                "of the schemes tested for, so being on the roster never counts as "
                "coverage here. e.g. 'which farmers receive nothing from any state "
                "scheme', 'the exclusion list'.",
        "members": ["G35-S", "G35-D", "G35-M"],
    },
    "state_scheme_convergence_rate": {
        "desc": "The SHARE (percentage) of PM-KISAN farmers reached by at least one "
                "of the six STATE schemes — the headline convergence rate as one "
                "row, not a farmer list. Roster membership is the denominator and "
                "never counts as being 'reached'. e.g. 'what share of our farmers "
                "gets anything beyond PM-KISAN', 'convergence rate'.",
        "members": ["Q015"],
    },
    "excluded_categories_no_state_scheme": {
        "desc": "Farmers of two named social categories who are covered by NO state "
                "scheme — the priority outreach list with names and districts, "
                "filtered to the categories given. Measures the six STATE schemes "
                "against the roster, so roster membership is not coverage. e.g. "
                "'which SC and ST farmers are not covered by any state scheme'.",
        "members": ["Q029"],
    },

    # ══ Benefit amounts (money), as opposed to membership ═════════════════
    "farmer_total_benefit_by_name": {
        "desc": "The total ₹ AMOUNT one named farmer has received, broken down by "
                "scheme — money, not membership. Sums each scheme's own benefit "
                "column and includes a PM-KISAN row carrying the LATEST INSTALLMENT "
                "ONLY (the roster holds no DBT history). e.g. 'what are this "
                "farmer's total benefits across all schemes'.",
        "members": ["F12"],
    },
    "aadhaar_total_benefit": {
        "desc": "The total ₹ AMOUNT paid to ONE Aadhaar number across every scheme, "
                "with the per-scheme split — money, not membership, keyed by a "
                "12-digit number rather than a name. Includes a PM-KISAN row for "
                "the latest installment only. e.g. 'how much has this Aadhaar "
                "received in total'.",
        "members": ["Q058"],
    },
    "multi_scheme_benefit_total": {
        "desc": "Farmers drawing benefits from a given NUMBER OF SCHEMES OR MORE, "
                "with their combined ₹ total — a money question gated on a scheme "
                "count, the vigilance shortlist. Both the count and the total "
                "include PM-KISAN (latest installment only). e.g. 'which farmers "
                "draw from 3 or more schemes and what is their combined total'.",
        "members": ["Q057"],
    },
    "farmer_benefit_ranking": {
        "desc": "Farmers ranked by TOTAL ₹ BENEFIT across all schemes, biggest "
                "first, within the chosen geography — a money league table, not a "
                "scheme-count one. Includes a PM-KISAN leg (latest installment "
                "only). e.g. 'rank farmers by total benefit across schemes', "
                "'aggregate public money per farmer'.",
        "members": ["G36-S", "G36-D", "G36-M"],
    },
    "average_benefit_per_scheme": {
        "desc": "The AVERAGE ₹ benefit per farmer in EACH scheme — one row per "
                "scheme with beneficiary count, total and mean, so the schemes can "
                "be compared by transfer size. Includes a PM-KISAN row (latest "
                "installment only). e.g. 'average benefit per farmer in each "
                "scheme', 'which scheme pays the most per farmer'.",
        "members": ["Q056"],
    },
    "benefit_concentration_by_village": {
        "desc": "Villages where BENEFIT PER FARMER is unusually high against their "
                "district peers — one row per village with average ₹ per farmer, an "
                "inspection-targeting signal rather than proof. Sums every scheme's "
                "benefit including PM-KISAN (latest installment only). e.g. 'which "
                "villages show an unusually high concentration of benefits'.",
        "members": ["Q131"],
    },
    "consolidated_unpaid_liability": {
        "desc": "How much money is sitting UNPAID across departments — one "
                "consolidated pendency row per scheme (horticulture, fisheries, "
                "sericulture, markfed), the total unpaid liability. e.g. 'across "
                "all departments, how much money is sitting unpaid'.",
        "members": ["Q051"],
    },

    # ══ One-farmer lookups, per dataset ═══════════════════════════════════
    "farmer_roster_record": {
        "desc": "The PM-KISAN roster record for ONE named farmer — beneficiary and "
                "eKYC status, declared area, khata, and the last installment number, "
                "date and amount. Reads pm_kisan only. e.g. 'what is this farmer's "
                "eKYC status', 'when was the last installment paid to this farmer "
                "and how much'.",
        "members": ["F01"],
    },
    "farmer_input_subsidy_record": {
        "desc": "The input/seed-subsidy record for ONE named farmer — crop, season, "
                "crop year and subsidy amount from agriculture. e.g. 'which crop did "
                "this farmer take input subsidy for and in which season'.",
        "members": ["F02"],
    },
    "farmer_micro_irrigation_record": {
        "desc": "The micro-irrigation (APMIP/horticulture) record for ONE named "
                "farmer — whether they are a beneficiary, the sanctioned subsidy "
                "amount and the land EXTENT recorded. Reads horticulture_apmip. An "
                "empty result means they are not an APMIP beneficiary — that is the "
                "answer. e.g. 'is this farmer a micro-irrigation beneficiary and "
                "what was sanctioned', 'what extent is recorded for them in "
                "horticulture'.",
        "members": ["F03"],
    },
    "farmer_fisheries_record": {
        "desc": "The fisheries record for ONE named farmer — whether they appear in "
                "the fisheries data and what amount was paid. Reads fisheries. An "
                "empty result means they are not a registrant. e.g. 'does this "
                "person appear in the fisheries data', 'how much was paid to them "
                "in fisheries'.",
        "members": ["F04"],
    },
    "farmer_sericulture_record": {
        "desc": "The sericulture record for ONE named farmer — cocoon quantity "
                "produced and the net incentive paid. Reads sericulture. e.g. 'what "
                "cocoon quantity is recorded for this farmer', 'what is their net "
                "incentive'.",
        "members": ["F05"],
    },
    "farmer_procurement_record": {
        "desc": "The MARKFED procurement record for ONE named farmer — which crop "
                "was procured, what quantity and rate, and whether payment was made. "
                "Reads markfed. e.g. 'which crop did procurement buy from this "
                "farmer and was he paid'.",
        "members": ["F06"],
    },
    "farmer_natural_farming_record": {
        "desc": "The RySS natural-farming record for ONE named farmer — whether "
                "they are an APCNF member and what ACREAGE is recorded. Reads ryss. "
                "e.g. 'is this farmer a natural farming member', 'what acreage is "
                "recorded for them in RySS'.",
        "members": ["F07"],
    },
    "farmer_land_record": {
        "desc": "The survey land record(s) for ONE named farmer as pattadar — khata "
                "number, survey number, extent and mutation status. Reads "
                "survey_land_records, which carries no Aadhaar, so it matches on "
                "pattadar name. e.g. 'what is this farmer's khata number in land "
                "records', 'link this farmer's land parcel to his entry'.",
        "members": ["F08"],
    },
    "farmer_full_profile_by_aadhaar": {
        "desc": "EVERYTHING held on ONE Aadhaar number, across all eight datasets — "
                "the grievance-desk 360 profile, keyed by a 12-digit number rather "
                "than a name. e.g. 'show the complete profile of this Aadhaar across "
                "all datasets'.",
        "members": ["Q124"],
    },

    # ══ Identity / reconciliation mismatches (data quality) ═══════════════
    "farmer_mobile_consistency": {
        "desc": "Whether the MOBILE NUMBER held for ONE named farmer agrees across "
                "the systems that store it (pm_kisan, agriculture, fisheries, "
                "markfed) — one row per distinct number, so more than one row means "
                "the departments disagree. An integrity check, not a contact "
                "lookup. e.g. 'is this farmer's mobile number consistent across all "
                "datasets'.",
        "members": ["F10"],
    },
    "mobile_mismatch_statewide": {
        "desc": "Every farmer whose MOBILE NUMBER differs between departments — the "
                "statewide mismatch list, no farmer named. Integrity check across "
                "pm_kisan, agriculture, fisheries and markfed. e.g. 'is the mobile "
                "number for a farmer consistent across all the systems that hold it'.",
        "members": ["Q061"],
    },
    "shared_mobile_numbers": {
        "desc": "Mobile numbers registered against SEVERAL DIFFERENT farmers — one "
                "row per shared number with the farmers on it, an agent/middleman "
                "capture flag. Not the same as one farmer having several numbers. "
                "e.g. 'is one mobile number registered against several farmers'.",
        "members": ["Q062"],
    },
    "farmer_land_consistency": {
        "desc": "Whether the LANDHOLDING recorded for ONE named farmer agrees "
                "across pm_kisan (hectares), markfed and survey_land_records "
                "(acres) — the per-farmer reconciliation, with the unit conversion "
                "applied so 1.30 ha and 3.21 acres read as consistent rather than "
                "as a discrepancy. e.g. 'this farmer's land shows 1.30 in PM-KISAN "
                "and 3.20 in MARKFED — is that a discrepancy'.",
        "members": ["F11"],
    },
    "land_mismatch_pmkisan_markfed": {
        "desc": "ALL farmers whose declared area in pm_kisan disagrees with markfed "
                "beyond a 5% tolerance, once hectares are converted to acres — the "
                "statewide land-discrepancy COUNT/list, no farmer named. e.g. 'how "
                "many farmers have discrepancies in their land amount', 'which "
                "farmers show a land discrepancy'.",
        "members": ["G42-S", "G42-D", "G42-M"],
    },
    "land_declared_vs_surveyed": {
        "desc": "Each farmer's DECLARED PM-KISAN area set against the extent in the "
                "revenue/survey land records — one row per farmer with both figures "
                "and the gap, matched on name and village because survey records "
                "carry no Aadhaar. The plain comparison, without a tolerance slot "
                "and without the subsidy consequence. e.g. 'compare declared area "
                "against the land records'.",
        "members": ["Q081"],
    },
    "land_over_declaration": {
        "desc": "Farmers whose PM-KISAN declared area EXCEEDS the survey land "
                "records beyond a tolerance percentage the query supplies — the "
                "over-declaration list only (not the two-sided comparison). e.g. "
                "'which farmers declare more land than the revenue record shows, "
                "beyond 10%'.",
        "members": ["Q082"],
    },
    "land_over_declaration_with_subsidy": {
        "desc": "Farmers who over-declare land AND whose subsidy per acre is also "
                "elevated — two findings in one row, the over-declaration and its "
                "financial consequence. Reads pm_kisan, survey_land_records and "
                "agriculture. Use when the query asks whether inflated area also "
                "moved money. e.g. 'which farmers' declared area exceeds their land "
                "records — and is their subsidy per acre also elevated'.",
        "members": ["M07"],
    },
    "caste_mismatch_across_departments": {
        "desc": "Farmers whose SOCIAL CATEGORY (caste) is recorded differently in "
                "different departments — the conflicting-category count/list for "
                "the chosen geography. An integrity check across pm_kisan and the "
                "scheme datasets. e.g. 'how many farmers have discrepancies in "
                "their caste category', 'conflicting caste records'.",
        "members": ["G41-S", "G41-D", "G41-M"],
    },
    "gender_mismatch_across_departments": {
        "desc": "Farmers whose recorded GENDER differs between departments — one "
                "row per conflicting Aadhaar with the values each system holds. "
                "e.g. 'are there farmers whose gender differs between departments'.",
        "members": ["Q064"],
    },
    "name_mismatch_across_departments": {
        "desc": "The same Aadhaar carrying DIFFERENT FARMER NAMES in pm_kisan and "
                "markfed — an identity inconsistency that blocks Aadhaar-based "
                "payment validation. e.g. 'for the same Aadhaar, does the name "
                "differ between the roster and procurement'.",
        "members": ["Q060"],
    },
    "dob_mismatch_across_departments": {
        "desc": "The same farmer carrying a DIFFERENT DATE OF BIRTH across "
                "departments (pm_kisan, markfed, ryss) — age drives eligibility, so "
                "a mismatch can wrongly include or exclude. e.g. 'does the date of "
                "birth on record differ across departments'.",
        "members": ["Q065"],
    },
    "ration_card_mismatch": {
        "desc": "The same farmer carrying DIFFERENT RATION CARD numbers across "
                "departments — the household identifier used as fallback when "
                "Aadhaar is masked. e.g. 'do ration card numbers match across "
                "departments for the same farmer'.",
        "members": ["Q066"],
    },
    "ekyc_status_conflict": {
        "desc": "Farmers whose eKYC status in MARKFED disagrees with the PM-KISAN "
                "roster — which system says the farmer is verified, a common cause "
                "of stuck payments. Not the eKYC backlog and not the "
                "eKYC-pending-yet-paid check. e.g. 'does the eKYC status in "
                "procurement agree with the roster'.",
        "members": ["Q071"],
    },
    "malformed_aadhaar": {
        "desc": "Aadhaar numbers that are NOT 12 digits (malformed, blank or "
                "non-numeric), counted per dataset across every Aadhaar-bearing "
                "table including pm_kisan. Run before any cross-dataset join: a "
                "malformed key silently drops the record from every match. e.g. "
                "'are there any malformed Aadhaar numbers in our systems'.",
        "members": ["Q067"],
    },
    "duplicate_subsidy_draws": {
        "desc": "Aadhaar numbers appearing MORE THAN ONCE for the same crop, season "
                "and crop year in the input-subsidy data — duplicate subsidy draws, "
                "one row per suspected duplicate. Reads agriculture only. An empty "
                "result is the correct answer on clean data. e.g. 'which Aadhaar "
                "numbers have multiple subsidy transactions for the same seed, "
                "season and cropyear'.",
        "members": ["M08", "Q068"],
    },
    "records_missing_district": {
        "desc": "Records that carry NO DISTRICT and so cannot be assigned to any "
                "officer — counted per dataset. A completeness check on geography, "
                "not a coverage question. e.g. 'which records are missing a district'.",
        "members": ["Q069"],
    },
    "sericulture_district_resolution": {
        "desc": "Resolving sericulture's DIST_CODE values to real district names by "
                "going through the farmer's Aadhaar on the PM-KISAN spine — a "
                "geography-harmonisation fix for the one dataset that stores codes "
                "without names. e.g. 'which district does each sericulture farmer "
                "actually belong to'.",
        "members": ["Q070"],
    },
    "district_code_crosswalk": {
        "desc": "A district CODE-to-NAME crosswalk built from the data already held "
                "(agriculture and sericulture codes resolved through the PM-KISAN "
                "spine) — the reusable mapping table, covering every code. e.g. "
                "'build me a district code to district name crosswalk'.",
        "members": ["Q140"],
    },
    "district_code_lookup": {
        "desc": "The district CODE (dcode) used in the agriculture data for ONE "
                "named district — a single lookup answer, not the whole crosswalk. "
                "e.g. 'what is the district code for Guntur in the data'.",
        "members": ["M03"],
    },
    "zero_land_beneficiaries": {
        "desc": "PM-KISAN beneficiaries recorded with ZERO or MISSING land area — a "
                "completeness flag on the roster's own area column. e.g. 'are there "
                "beneficiaries with no land area recorded'.",
        "members": ["Q073"],
    },
    "data_completeness_scorecard": {
        "desc": "A FIELD-COMPLETENESS scorecard for the roster by geography — what "
                "percentage of records carry Aadhaar, mobile, bank details, area and "
                "so on. A data-quality dashboard, not a farmer list. e.g. 'give me a "
                "completeness scorecard by district'.",
        "members": ["G09-S", "G09-D", "G09-M"],
    },
    "integrity_dashboard": {
        "desc": "The ONE-PAGE INTEGRITY DASHBOARD: how many records fail each "
                "standard check (malformed Aadhaar, off-roster payments, land "
                "mismatch, duplicates, missing bank details …) as one row per check. "
                "A roll-up of every integrity query, not any single one of them. "
                "e.g. 'give me an integrity dashboard', 'all red flags in one view'.",
        "members": ["Q134"],
    },

    # ══ Bank / payment plumbing ═══════════════════════════════════════════
    "shared_bank_accounts": {
        "desc": "Bank account numbers linked to MORE THAN ONE farmer on the roster "
                "— the classic leakage flag, one row per shared account. An empty "
                "result is a clean bill of health and must be reported as such. "
                "e.g. 'is any bank account number linked to more than one farmer'.",
        "members": ["Q052"],
    },
    "bank_account_mismatch_markfed": {
        "desc": "Farmers whose bank account on the PM-KISAN roster differs from the "
                "one MARKFED pays into — a stale record or a diverted payment. e.g. "
                "'are we paying two different accounts for one farmer'.",
        "members": ["Q053"],
    },
    "bank_account_mismatch_sericulture": {
        "desc": "Farmers whose bank details in sericulture differ from the PM-KISAN "
                "roster — the silk-incentive version of the account cross-check. "
                "e.g. 'do the bank details in sericulture match the roster'.",
        "members": ["Q054"],
    },
    "missing_bank_details": {
        "desc": "Beneficiaries with NO bank account or IFSC recorded — farmers who "
                "physically cannot receive DBT, a blocking data-quality list. e.g. "
                "'which beneficiaries have no bank account recorded'.",
        "members": ["Q055"],
    },

    # ══ PM-KISAN roster coverage and demographics ════════════════════════
    "roster_count_by_geography": {
        "desc": "How many PM-KISAN beneficiaries there are in each area — a COUNT "
                "grouped by district, mandal or village depending on the scope "
                "asked for, ONE ROW PER PLACE. Reads pm_kisan only. Requires the "
                "question to ask for a geographic breakdown ('in each district', "
                "'by mandal', 'where'); a bare 'how many beneficiaries are there' "
                "with no area named is the single-total family, not this one, and a "
                "count filtered by CASTE, GENDER or STATUS belongs to that "
                "attribute's own breakdown family rather than here. e.g. 'how many "
                "beneficiaries in each district', 'where are our farmers'.",
        "members": ["G01-S", "G01-D", "G01-M"],
    },
    "roster_total_count": {
        "desc": "The single TOTAL number of farmers registered as PM-KISAN "
                "beneficiaries in the state — ONE NUMBER, one row, no grouping. "
                "This is the default for any roster-size question that does NOT "
                "name a district, mandal or village and does not ask for a "
                "breakdown; the per-area count family is only for questions that "
                "do. e.g. 'how many beneficiaries are registered in PM-KISAN', "
                "'how many farmers are on the roster', 'size of the roster'.",
        "members": ["Q001"],
    },
    "state_headline_totals": {
        "desc": "The statewide HEADLINE ROW: total beneficiaries, total area and "
                "total subsidy together in a single line — the 'in total' answer, "
                "as opposed to any by-district breakdown. Reads pm_kisan and "
                "agriculture. e.g. 'what is the total subsidy amount disbursed', "
                "'how many distinct districts do beneficiaries come from', "
                "'headline numbers for the state'.",
        "members": ["M01"],
    },
    "dataset_farmer_counts": {
        "desc": "How many FARMERS each of the eight datasets holds AND whether that "
                "dataset carries an Aadhaar column — the joinability answer as much "
                "as a count (survey_land_records has no Aadhaar at all, which is why "
                "it joins on pattadar name). e.g. 'how many farmers are in each "
                "dataset', 'how many land records are there and do they carry "
                "Aadhaar'.",
        "members": ["M02"],
    },
    "dataset_record_counts": {
        "desc": "The raw ROW COUNT each department dataset holds — a table-size "
                "inventory, without the Aadhaar-coverage column. e.g. 'one table "
                "showing how many records each dataset holds'.",
        "members": ["Q005"],
    },
    "combined_farmer_universe": {
        "desc": "The number of UNIQUE farmers touched across every dataset put "
                "together — the size of the union universe on distinct Aadhaar, "
                "which is larger than the roster because some scheme beneficiaries "
                "are off-roster. One number. e.g. 'how many unique farmers do we "
                "actually touch across every dataset'.",
        "members": ["Q004"],
    },
    "administrative_spread": {
        "desc": "How many MANDALS and VILLAGES in each district contain at least one "
                "PM-KISAN beneficiary — the administrative footprint, counting "
                "places rather than farmers. e.g. 'mandal and village coverage by "
                "district'.",
        "members": ["Q007"],
    },
    "scheme_district_breadth": {
        "desc": "How many DISTRICTS each scheme operates in — one row per scheme "
                "with its district count, a geographic-breadth comparison across "
                "departments. Sericulture is excluded because it stores district "
                "codes only. e.g. 'how many districts does each scheme operate in'.",
        "members": ["Q017"],
    },
    "ekyc_status_pendency_by_geography": {
        "desc": "Where the eKYC and beneficiary-status PENDENCY sits by area — "
                "completed/pending counts grouped by district, mandal or village, "
                "the backlog dashboard. Reads pm_kisan. e.g. 'which mandals have "
                "the biggest eKYC backlog', 'distribution of beneficiary_status and "
                "ekyc_status per district'.",
        "members": ["G02-S", "G02-D", "G02-M"],
    },
    "ekyc_completion_ranking": {
        "desc": "Districts ranked by eKYC completion RATE (percentage completed), "
                "worst first — a rate, deliberately not a raw pending count, so big "
                "districts do not automatically top the list. e.g. 'which districts "
                "have the worst eKYC completion rate'.",
        "members": ["Q138"],
    },
    "cultivable_area_total": {
        "desc": "The TOTAL cultivable area held by PM-KISAN beneficiaries in the "
                "chosen area, in hectares with an acre conversion — a land total, "
                "not a farmer count. e.g. 'what is the total cultivable area of all "
                "beneficiaries'.",
        "members": ["G03-S", "G03-D", "G03-M"],
    },
    "average_landholding_by_district": {
        "desc": "The AVERAGE landholding per district — mean farm size by district, "
                "showing where the smallest farms are. Not a total and not a size "
                "band. e.g. 'what is the average landholding per district'.",
        "members": ["Q019"],
    },
    "social_category_breakdown": {
        "desc": "The SOCIAL CATEGORY (caste) composition of PM-KISAN beneficiaries "
                "— SC/ST/BC/OC counts and shares for the chosen area. Reads "
                "pm_kisan. ANY question that names a caste code carries its answer "
                "here, including bare counts: 'how many SC farmers are there' and "
                "'how many SC or ST PM-KISAN farmers' are answered by reading the "
                "SC and ST rows of this breakdown. A caste-named question never "
                "belongs to the per-district count family. e.g. 'give the category "
                "breakdown of beneficiaries', 'how many SC beneficiaries are "
                "there', 'caste-wise beneficiary split'.",
        "members": ["G04-S", "G04-D", "G04-M"],
    },
    "gender_breakdown": {
        "desc": "The MALE/FEMALE split of PM-KISAN beneficiaries for the chosen "
                "area — counts and shares by gender. Reads pm_kisan. e.g. 'how many "
                "male vs female beneficiaries', 'women farmers on the roster'.",
        "members": ["G05-S", "G05-D", "G05-M"],
    },
    "land_size_bands": {
        "desc": "Beneficiaries split into MARGINAL / SMALL / SEMI-MEDIUM-and-above "
                "landholding bands (below 1 ha, 1-2 ha, above 2 ha) — a distribution "
                "over land-size classes. e.g. 'how many marginal farmers are there', "
                "'break beneficiaries into land size bands'.",
        "members": ["G06-S", "G06-D", "G06-M"],
    },
    "landholding_by_social_category": {
        "desc": "The AVERAGE LANDHOLDING for each social category (SC/ST/BC/OC) — "
                "area per category, showing whether some communities hold less land. "
                "Reads pm_kisan. e.g. 'what is the distribution of declared area by "
                "category', 'do SC/ST farmers hold less land'.",
        "members": ["Q027"],
    },
    "largest_landholders": {
        "desc": "The TOP-N largest landholders on the PM-KISAN roster, ranked by "
                "declared area — a leaderboard of biggest farms, no subsidy figure. "
                "e.g. 'who has the largest landholding in PM-KISAN', 'top 10 "
                "landholders'.",
        "members": ["R01"],
    },
    "ekyc_filtered_farmer_list": {
        "desc": "The list of farmers at a NAMED eKYC status (pending or completed) "
                "— a status-filtered roster list, with NO other filter. If the "
                "question also names a CROP ('paddy farmers whose eKYC is pending') "
                "the crop-filtered family applies instead; answering here would "
                "silently drop the crop and return every pending farmer. e.g. "
                "'which farmers have eKYC still pending'.",
        "members": ["V05"],
    },
    "beneficiary_status_filtered_list": {
        "desc": "The list of farmers at a NAMED beneficiary status (Included, "
                "Excluded or Pending) — a status-filtered roster list, distinct "
                "from eKYC. e.g. 'whose beneficiary status is Pending'.",
        "members": ["V06"],
    },
    "gender_ekyc_camp_list": {
        "desc": "Farmers of a named GENDER at a named eKYC STATUS, with mobile "
                "numbers — the actionable list for running a targeted verification "
                "camp. Two filters at once. e.g. 'list women farmers whose eKYC is "
                "pending so we can run a camp'.",
        "members": ["Q030"],
    },

    # ══ DBT / installments ════════════════════════════════════════════════
    "dbt_credited_by_geography": {
        "desc": "How much PM-KISAN DBT money was CREDITED in each area — installment "
                "amounts summed by district, mandal or village. Reads pm_kisan's "
                "last_amount_credited. e.g. 'how much DBT was credited district by "
                "district'.",
        "members": ["G07-S", "G07-D", "G07-M"],
    },
    "missed_installment": {
        "desc": "Farmers who have MISSED the most recent PM-KISAN installment — one "
                "row per farmer behind on DBT, for the chosen area. e.g. 'which "
                "farmers have missed the latest installment'.",
        "members": ["G08-S", "G08-D", "G08-M"],
    },
    "latest_installment_summary": {
        "desc": "A summary of the LATEST DBT CYCLE: which installment number it "
                "was, how many farmers it reached and the total amount — one row "
                "about the payment run, not about any farmer. e.g. 'what was the "
                "last installment paid, to how many farmers, for how much'.",
        "members": ["Q041"],
    },

    # ══ Input subsidy (agriculture) ═══════════════════════════════════════
    "input_subsidy_by_geography": {
        "desc": "How much INPUT/SEED SUBSIDY was disbursed in each area — amounts "
                "and beneficiary counts grouped by district, mandal or village. "
                "Reads agriculture, with geography resolved through the PM-KISAN "
                "spine because agriculture stores codes only. Micro-irrigation is a "
                "different measure. e.g. 'how much input subsidy went to each "
                "district'.",
        "members": ["G10-S", "G10-D", "G10-M"],
    },
    "crop_mix_subsidy": {
        "desc": "The CROP MIX behind input subsidy for the chosen area — one row per "
                "crop with farmers and subsidy amount, showing what is being "
                "subsidised. e.g. 'what is the crop mix in this district', 'which "
                "crops account for the most input subsidy'.",
        "members": ["G11-S", "G11-D", "G11-M"],
    },
    "crop_registration_backlog": {
        "desc": "How many eCrop CROP REGISTRATIONS are still awaiting approval in "
                "the chosen area — the approval backlog by status. The only "
                "statuses that exist are Approved, Pending and Under Review. e.g. "
                "'how many crop registrations are pending'.",
        "members": ["G12-S", "G12-D", "G12-M"],
    },
    "crop_registration_by_status": {
        "desc": "Crop registrations filtered to ONE NAMED status — the list at that "
                "status rather than a backlog count. Only Approved, Pending and "
                "Under Review exist in this column: a query for any other status "
                "(e.g. 'Damaged') correctly returns nothing and the answer is that "
                "the status does not exist. e.g. 'which registered crops are marked "
                "Damaged', 'which registrations are Under Review'.",
        "members": ["V02"],
    },
    "subsidy_by_social_category": {
        "desc": "How INPUT SUBSIDY money is distributed across social categories in "
                "the chosen area — each category's share of farmers set against its "
                "share of money, so the gap is the targeting story. e.g. 'how is "
                "input subsidy distributed across categories'.",
        "members": ["G13-S", "G13-D", "G13-M"],
    },
    "subsidy_equity_gap": {
        "desc": "Whether TWO NAMED social categories' share of subsidy MONEY matches "
                "their share of FARMERS — two percentages side by side with the gap, "
                "statewide. A negative gap means under-allocation. e.g. 'is the "
                "SC/ST share of subsidy in line with their share of farmers'.",
        "members": ["Q024"],
    },
    "subsidy_equity_gap_by_district": {
        "desc": "Which DISTRICTS give two named social categories a smaller share of "
                "subsidy than their share of the farmer base — the equity gap "
                "ranked by district, so it localises where targeting is weakest. "
                "e.g. 'which districts under-allocate to SC/ST farmers'.",
        "members": ["Q032"],
    },
    "subsidy_per_acre_by_land_band": {
        "desc": "Whether SMALLER farmers get more or less subsidy PER ACRE — "
                "subsidy intensity by land-size band, the progressivity test. Raw "
                "totals always favour large farms, so this normalises. e.g. 'do "
                "smaller farmers get more subsidy per acre'.",
        "members": ["Q028"],
    },
    "top_subsidy_per_acre_farmers": {
        "desc": "The individual FARMERS with the highest input subsidy PER ACRE of "
                "land held — outlier subsidy rates, one row per farmer. Per-acre "
                "normalisation surfaces anomalies raw amounts hide. e.g. 'who gets "
                "the highest input subsidy per acre of land'.",
        "members": ["Q094"],
    },
    "subsidy_per_acre_by_district": {
        "desc": "Which DISTRICTS receive the most subsidy PER ACRE of farmland — "
                "allocation intensity by district, comparable across districts of "
                "different sizes. e.g. 'which districts get the most subsidy per "
                "acre'.",
        "members": ["Q139"],
    },
    "elite_capture_check": {
        "desc": "How much INPUT SUBSIDY the TOP-N LARGEST LANDHOLDERS take — the "
                "elite-capture check pairing farm size with money drawn. e.g. "
                "'which largest landholders take the most input subsidy'.",
        "members": ["Q035"],
    },
    "large_landholders_in_targeted_schemes": {
        "desc": "LARGE landholders (above the small-farmer ceiling) who still "
                "receive subsidies meant to be pro-poor — support flowing upward, "
                "for the chosen area. Reads pm_kisan with agriculture and "
                "horticulture. e.g. 'which large landholders receive targeted "
                "subsidies'.",
        "members": ["G44-S", "G44-D", "G44-M"],
    },
    "marginal_farmers_without_subsidy": {
        "desc": "Farmers BELOW a hectare threshold who are on the PM-KISAN roster "
                "but have NEVER taken an input subsidy — the highest-priority "
                "outreach segment. BOTH conditions are required: a bare land-size "
                "list with no mention of subsidy belongs to the plain "
                "landholding-threshold family (this one returns roughly half as "
                "many rows), and a bare 'never took an input subsidy' with no land "
                "threshold is the roster-minus-one-scheme family with "
                "scheme=Agriculture. e.g. 'which farmers under 1 hectare have never "
                "taken input subsidy'.",
        "members": ["Q036"],
    },
    "highest_input_subsidies": {
        "desc": "The TOP-N single largest INPUT SUBSIDY payments and who received "
                "them — a payment leaderboard from agriculture. e.g. 'who received "
                "the highest input subsidy and how much'.",
        "members": ["R02"],
    },
    "highest_district_input_subsidy": {
        "desc": "The DISTRICT that recorded the largest SINGLE input subsidy "
                "payment — the peak transaction per district, not the district "
                "total, so an outlier payment a total would hide becomes visible. "
                "e.g. 'which district received the highest single input subsidy'.",
        "members": ["R04"],
    },
    "season_filtered_subsidy_list": {
        "desc": "Farmers who took an input subsidy in ONE NAMED season (Kharif, "
                "Rabi or Summer) — a season-filtered list of people. e.g. 'list "
                "farmers who took subsidy in the Rabi season'.",
        "members": ["V01"],
    },
    "seasonal_subsidy_totals": {
        "desc": "How input subsidy totals split across seasons counted by "
                "DISTINCT FARMERS — Kharif vs Rabi amounts with the number of "
                "farmers who took subsidy in each, plus the "
                "subsidy-to-farmer-contribution ratio (subsidyamount against "
                "nonsubsidyamount). Aggregates, not a farmer list. The sibling "
                "family reports the same cut counted by TRANSACTION. e.g. 'how many "
                "farmers took input subsidy in each season', 'what is the total "
                "subsidy amount by season'.",
        "members": ["Q090"],
    },
    "crop_filtered_farmer_list": {
        "desc": "Farmers who grow ONE NAMED crop and what subsidy they received — a "
                "crop-filtered list of people from agriculture. e.g. 'which farmers "
                "grow paddy and what subsidy did they get'.",
        "members": ["V03"],
    },
    "crop_pattern_by_district": {
        "desc": "The CROP PATTERN district by district — which crops are grown "
                "where, from agriculture with district names resolved through the "
                "PM-KISAN spine. e.g. 'show me the crop pattern by district'.",
        "members": ["Q091"],
    },
    "seed_distribution": {
        "desc": "How much SEED was distributed for each crop and VARIETY — input "
                "quantities issued, by seed variety rather than by money. e.g. 'how "
                "much seed was distributed for each crop and variety'.",
        "members": ["Q093"],
    },
    "irrigation_method_distribution": {
        "desc": "The IRRIGATION METHODS recorded against subsidised farmers — a "
                "distribution over irrmethodcode values from agriculture. e.g. "
                "'what irrigation methods are recorded against subsidised farmers'.",
        "members": ["Q096"],
    },
    "subsidy_year_trend": {
        "desc": "How input subsidy spend has moved YEAR ON YEAR — one row per crop "
                "year, the trend line. e.g. 'how has subsidy spend moved year on "
                "year'.",
        "members": ["Q099"],
    },
    "crops_of_ekyc_filtered_farmers": {
        "desc": "Which CROPS are grown by farmers at a NAMED eKYC status — the crop "
                "mix of (un)verified farmers, joining agriculture to the roster's "
                "verification state. e.g. 'what crops are grown by farmers whose "
                "eKYC is pending'.",
        "members": ["V08"],
    },
    "registered_crop_no_subsidy": {
        "desc": "Farmers with a crop REGISTERED in eCrop but NO seed-subsidy record "
                "for the same season — registered cultivation that never converted "
                "into input support. Reads agriculture. e.g. 'which farmers have a "
                "crop registered but no seed subsidy for the same season'.",
        "members": ["M05"],
    },
    "registered_vs_procured_crop": {
        "desc": "Whether farmers SELL THE SAME CROP they registered for input "
                "subsidy — a crop mismatch between agriculture and markfed, per "
                "farmer. Either a legitimate crop change or a subsidy drawn against "
                "a crop never sown. e.g. 'do farmers sell the same crop they "
                "registered for subsidy'.",
        "members": ["Q095"],
    },
    "procurement_without_registration": {
        "desc": "Farmers who sold produce to MARKFED with NO crop registration in "
                "the agriculture system at all — unregistered supply, an absence "
                "check between markfed and agriculture (not an overlap). e.g. "
                "'which farmers sold to procurement without any eCrop registration'.",
        "members": ["Q106"],
    },

    # ══ Micro-irrigation / horticulture (APMIP) ═══════════════════════════
    "micro_irrigation_coverage": {
        "desc": "MICRO-IRRIGATION (APMIP/horticulture) coverage BROKEN DOWN BY "
                "AREA — beneficiary counts, extent and subsidy grouped by district, "
                "mandal or village, one row per place. Reads horticulture_apmip. "
                "This is drip/sprinkler subsidy, never seed/input subsidy. For the "
                "single-row statewide total with sanctioned-versus-released subsidy, "
                "use the APMIP headline family instead. e.g. 'micro-irrigation "
                "coverage by district', 'which mandals have the most APMIP "
                "beneficiaries'.",
        "members": ["G21-S", "G21-D", "G21-M"],
    },
    "district_horticulture_reach": {
        "desc": "Within ONE NAMED district, which roster farmers DID and DID NOT "
                "receive a horticulture/micro-irrigation subsidy — the reach-and-gap "
                "list side by side for a district officer. e.g. 'which farmers in "
                "this district got a horticulture subsidy'.",
        "members": ["Q040"],
    },
    "apmip_stalled_sanctions": {
        "desc": "Micro-irrigation sanctions where money has been SANCTIONED but "
                "NOT RELEASED — the stalled-sanction list for the chosen area. "
                "e.g. 'which beneficiaries have sanctioned but stalled subsidies', "
                "'which micro-irrigation sanctions have seen no money released'.",
        "members": ["G22-S", "G22-D", "G22-M"],
    },
    "apmip_approved_unpaid": {
        "desc": "Micro-irrigation sanctions APPROVED on paper against which no money "
                "has moved — separating a documentation problem from a treasury one, "
                "statewide. e.g. 'which sanctions are approved but have seen no "
                "money move'.",
        "members": ["Q132"],
    },
    "apmip_inspection_backlog": {
        "desc": "Micro-irrigation applications stuck in APPLICATION PROCESSING "
                "— the approval backlog by Status (Pending and Under Review, "
                "Approved excluded) for the chosen area. This is the application's "
                "own approval state; the separate RANDOM INSPECTION process has its "
                "own column and its own family, so a question naming 'random "
                "inspection' or 'RI' belongs there, not here. e.g. 'what is the "
                "inspection backlog', 'how many APMIP applications are pending "
                "review'.",
        "members": ["G23-S", "G23-D", "G23-M"],
    },
    "apmip_unit_cost": {
        "desc": "The UNIT COST of micro-irrigation — cost and subsidy per hectare/acre "
                "for the chosen area, so intensity can be compared across places. "
                "e.g. 'what is the unit cost of micro-irrigation', 'subsidy per acre "
                "in APMIP'.",
        "members": ["G24-S", "G24-D", "G24-M"],
    },
    "apmip_release_position": {
        "desc": "Per micro-irrigation BENEFICIARY, what was sanctioned versus "
                "released versus still to be released — one row per beneficiary "
                "with the balance. e.g. 'total Subsidy Amt released vs "
                "BALANCE_AMOUNT_TO_RELEASE still pending per beneficiary'.",
        "members": ["M04"],
    },
    "apmip_sanctioned_vs_released_total": {
        "desc": "The STATEWIDE total of micro-irrigation subsidy SANCTIONED against "
                "what has actually been RELEASED, and the pending balance — "
                "aggregates, not a per-beneficiary list. e.g. 'how much APMIP "
                "subsidy has been sanctioned versus released'.",
        "members": ["Q044"],
    },
    "apmip_crop_season_mix": {
        "desc": "Which CROPS and SEASONS the micro-irrigation programme covers — the "
                "APMIP crop/season mix from horticulture_apmip. e.g. 'which crops "
                "and seasons does micro-irrigation cover'.",
        "members": ["Q097"],
    },
    "apmip_gender_share": {
        "desc": "What SHARE of micro-irrigation subsidy goes to WOMEN beneficiaries "
                "— the gender split of APMIP money. e.g. 'what share of "
                "micro-irrigation subsidy goes to women'.",
        "members": ["Q026"],
    },
    "apmip_dry_land_share": {
        "desc": "How much micro-irrigation coverage sits on DRY LAND versus total "
                "land — the rainfed share, which is the higher-value targeting "
                "question. e.g. 'how much of micro-irrigation is on dry land'.",
        "members": ["Q086"],
    },
    "districts_without_apmip": {
        "desc": "DISTRICTS that have PM-KISAN farmers but NO micro-irrigation "
                "beneficiary at all — the district-level white space for scheme "
                "expansion. e.g. 'which districts are untouched by micro-irrigation'.",
        "members": ["Q018"],
    },
    "mandals_without_apmip": {
        "desc": "MANDALS that have PM-KISAN farmers but NO micro-irrigation "
                "beneficiary — the same white-space check one level down, at "
                "sub-district grain. e.g. 'which mandals have no micro-irrigation "
                "beneficiary'.",
        "members": ["Q142"],
    },

    # ══ Fisheries ═════════════════════════════════════════════════════════
    "fisheries_coverage": {
        "desc": "How many FISHERS/FCS members are registered in each area and how "
                "much has been paid to them — counts and payouts grouped by "
                "district, mandal or village. Reads fisheries. e.g. 'how many FCS "
                "members exist per district', 'fisheries registrations by district'.",
        "members": ["G25-S", "G25-D", "G25-M"],
    },
    "fisheries_headline": {
        "desc": "The STATEWIDE fisheries summary in one row — how many fishers and "
                "aqua farmers are registered and how much has been paid in total. "
                "e.g. 'how many fishers are registered and how much has been paid'.",
        "members": ["Q010"],
    },
    "fisheries_payment_pendency": {
        "desc": "The fisheries PAYMENT position for the chosen area — paid against "
                "unpaid claims and the value stuck. Reads fisheries. e.g. 'what is "
                "the fisheries payment position', 'unpaid fisheries claims'.",
        "members": ["G26-S", "G26-D", "G26-M"],
    },
    "aqua_extent": {
        "desc": "The AQUA EXTENT position — water area under aquaculture and how "
                "much of it is cultivable, for the chosen area. A land/water-area "
                "measure, not a payment one. e.g. 'what area is under aquaculture "
                "and how much is cultivable'.",
        "members": ["G27-S", "G27-D", "G27-M"],
    },
    "fisheries_by_social_category": {
        "desc": "What FISHERIES payments look like by SOCIAL CATEGORY — caste-wise "
                "beneficiary counts and amounts within fisheries. e.g. 'what do "
                "fisheries payments look like by social category'.",
        "members": ["Q034"],
    },

    # ══ Sericulture ═══════════════════════════════════════════════════════
    "sericulture_headline": {
        "desc": "The STATEWIDE sericulture summary — how many silk farmers are "
                "registered and what incentive has been paid in total. e.g. 'how "
                "many sericulture farmers are registered and what incentive was "
                "paid'.",
        "members": ["Q011"],
    },
    "sericulture_productivity": {
        "desc": "COCOON OUTPUT and incentive PER FARMER — one row per sericulture "
                "farmer with quantity produced and incentive drawn, a productivity "
                "view. e.g. 'what is the cocoon output and incentive per farmer'.",
        "members": ["Q145"],
    },
    "sericulture_by_mandal": {
        "desc": "Which MANDALS produce the most COCOON and what incentive they drew "
                "— sericulture output grouped by mandal (a code in this dataset). "
                "e.g. 'which mandals produce the most cocoon'.",
        "members": ["Q146"],
    },
    "sericulture_payment_pendency": {
        "desc": "How many SERICULTURE incentive transactions are not yet APPROVED "
                "and what they are worth — the silk payment backlog. e.g. 'how many "
                "sericulture incentive transactions are unapproved and what is their "
                "value'.",
        "members": ["Q049"],
    },
    "sericulture_gender_split": {
        "desc": "How SERICULTURE incentive money splits between men and women — the "
                "gender share within silk. e.g. 'how is sericulture incentive split "
                "between men and women'.",
        "members": ["Q033"],
    },

    # ══ MARKFED procurement ═══════════════════════════════════════════════
    "procurement_by_geography": {
        "desc": "How much was PROCURED (quantity and value) in each area — MSP "
                "purchases grouped by district, mandal or village. Reads markfed. "
                "e.g. 'how much was procured in each district'.",
        "members": ["G14-S", "G14-D", "G14-M"],
    },
    "procurement_by_crop": {
        "desc": "What quantity and value was procured FOR EACH CROP in the chosen "
                "area — commodity-wise MSP purchases. e.g. 'what was procured by "
                "crop'.",
        "members": ["G15-S", "G15-D", "G15-M"],
    },
    "procurement_headline": {
        "desc": "The STATEWIDE procurement summary — total produce MARKFED has "
                "procured and total money paid to farmers, in one row. e.g. 'how "
                "much produce has procurement bought and how much has been paid'.",
        "members": ["Q012"],
    },
    "procured_but_unpaid": {
        "desc": "Farmers who DELIVERED produce but have NOT been paid — the "
                "field-actionable unpaid list with mobile numbers, for the chosen "
                "area. Reads markfed. e.g. 'which farmers delivered produce but have "
                "not been paid'.",
        "members": ["G16-S", "G16-D", "G16-M"],
    },
    "procurement_pendency_by_geography": {
        "desc": "How much procurement MONEY is STUCK in each area — the unpaid value "
                "grouped by district, mandal or village, rather than the farmer "
                "list. e.g. 'how much procurement payment is stuck district by "
                "district'.",
        "members": ["G17-S", "G17-D", "G17-M"],
    },
    "procurement_pendency_statewide": {
        "desc": "The statewide procurement PAYMENT STATUS breakdown and how much "
                "money is stuck — counts and value by payment status. e.g. 'what is "
                "the payment status breakdown for procurement'.",
        "members": ["Q046"],
    },
    "procurement_pendency_by_crop": {
        "desc": "For which CROPS the largest share of procurement payment is still "
                "PENDING — pendency by commodity rather than by place. e.g. 'for "
                "which crops is the largest share of payment still pending'.",
        "members": ["Q109"],
    },
    "procurement_reconciliation": {
        "desc": "Procurement records that FAIL ARITHMETIC RECONCILIATION — amount "
                "paid does not equal quantity times rate within 1% — one row per "
                "billing anomaly for the chosen area. A data-integrity check, not a "
                "pendency question. e.g. 'which procurement records do not "
                "reconcile'.",
        "members": ["G18-S", "G18-D", "G18-M"],
    },
    "procurement_yield_outliers": {
        "desc": "Farmers who sold an IMPLAUSIBLY HIGH QUANTITY for the land they "
                "hold — quantity per acre above a plausible ceiling, for the chosen "
                "area. e.g. 'which farmers show implausible yields'.",
        "members": ["G19-S", "G19-D", "G19-M"],
    },
    "procurement_equity_split": {
        "desc": "How PROCUREMENT PAYMENTS split by GENDER and SOCIAL CATEGORY in the "
                "chosen area — who sells to MARKFED, as counts and amounts. e.g. "
                "'how do procurement payments split by gender and category'.",
        "members": ["G20-S", "G20-D", "G20-M"],
    },
    "procurement_gender_gap": {
        "desc": "Whether there is a GENDER GAP in the AVERAGE procurement payment "
                "per farmer — mean payment for men against women, statewide. e.g. "
                "'is there a gender gap in average procurement payment'.",
        "members": ["Q039"],
    },
    "gender_filtered_procurement_list": {
        "desc": "The list of farmers of ONE NAMED gender who received MARKFED "
                "payments — a gender-filtered payment list of people, not a split. "
                "e.g. 'which female farmers received procurement payments'.",
        "members": ["V04"],
    },
    "highest_procurement_payments": {
        "desc": "The TOP-N largest MARKFED PAYMENTS and who received them — a "
                "payment leaderboard measured in rupees. e.g. 'who received the "
                "highest procurement payment'.",
        "members": ["R03"],
    },
    "largest_suppliers_by_quantity": {
        "desc": "The TOP-N largest suppliers by QUANTITY procured — a volume "
                "leaderboard, measured in produce not rupees. e.g. 'who are the "
                "biggest sellers to MARKFED by quantity'.",
        "members": ["Q107"],
    },
    "procurement_rate_variation": {
        "desc": "The IMPLIED RATE PER UNIT for each crop and whether it varies by "
                "district — a price-consistency check on whether farmers get the "
                "same rate everywhere. e.g. 'what is the implied rate per unit for "
                "each crop, and does it vary by district'.",
        "members": ["Q103"],
    },
    "procurement_by_season": {
        "desc": "How PROCUREMENT splits across SEASONS — Kharif against Rabi "
                "purchases, quantity and value. e.g. 'how does procurement split "
                "across seasons'.",
        "members": ["Q108"],
    },
    "procurement_intensity_by_district": {
        "desc": "The AVERAGE procurement value PER FARMER in each district relative "
                "to their landholding — procurement intensity per acre, comparable "
                "across districts. e.g. 'what is the procurement payment per farmer "
                "and which district leads'.",
        "members": ["Q111"],
    },

    # ══ RySS / natural farming ════════════════════════════════════════════
    "natural_farming_coverage": {
        "desc": "How many NATURAL FARMING (RySS/APCNF) members there are in each "
                "area and what acreage they cover — membership and area grouped by "
                "district, mandal or village. e.g. 'how many APCNF members are "
                "enrolled and what is the total acreage under natural farming'.",
        "members": ["G28-S", "G28-D", "G28-M"],
    },
    "natural_farming_practice_mix": {
        "desc": "The AREA under each natural-farming PRACTICE (C1, PMDS, S2S) for "
                "the chosen area — the APCNF practice mix, each practice having its "
                "own extent column. e.g. 'what area is under each natural farming "
                "practice'.",
        "members": ["G29-S", "G29-D", "G29-M"],
    },
    "natural_farming_survey_progress": {
        "desc": "How the natural-farming field SURVEY is progressing MONTH BY MONTH "
                "in the chosen area — completion over time, a progress trend rather "
                "than a stock. e.g. 'how is the natural farming survey progressing'.",
        "members": ["G30-S", "G30-D", "G30-M"],
    },
    "natural_farming_category_profile": {
        "desc": "The SOCIAL CATEGORY profile of natural-farming members in the "
                "chosen area — who joins APCNF, by caste. e.g. 'what is the category "
                "profile of natural farming members'.",
        "members": ["G31-S", "G31-D", "G31-M"],
    },
    "natural_farming_uptake_vs_roster": {
        "desc": "How natural-farming ENROLMENT compares with the PM-KISAN base by "
                "social category — an uptake RATE with the roster as denominator, "
                "not a raw count. e.g. 'is natural farming reaching SC/ST farmers'.",
        "members": ["Q031"],
    },
    "natural_farming_land_share": {
        "desc": "What SHARE OF FARMLAND is under natural farming in each area — RySS "
                "acreage against the roster's land base (converted to acres), a "
                "penetration percentage. e.g. 'what share of farmland is under "
                "natural farming, district by district'.",
        "members": ["G43-S", "G43-D", "G43-M"],
    },

    # ══ Land and survey records ═══════════════════════════════════════════
    "land_record_extent_by_geography": {
        "desc": "How much LAND is on record in each area — surveyed extent and "
                "parcel counts from survey_land_records, grouped by district, mandal "
                "or village. e.g. 'how much land is on record in each district'.",
        "members": ["G32-S", "G32-D", "G32-M"],
    },
    "land_record_pendency": {
        "desc": "Land records NOT YET APPROVED — mutation pendency for the chosen "
                "area, one row per parcel awaiting clearance. e.g. 'which land "
                "records are pending'.",
        "members": ["G33-S", "G33-D", "G33-M"],
    },
    "land_record_pendency_count": {
        "desc": "HOW MANY land records are stuck in pending or under-review status "
                "— the mutation-pendency count by status, statewide, rather than the "
                "parcel list. e.g. 'how many land records are stuck in pending "
                "status'.",
        "members": ["Q083"],
    },
    "pattadar_list_by_village": {
        "desc": "The PATTADARS (land title holders) in ONE NAMED village — the "
                "title-holder list for that village from survey_land_records. e.g. "
                "'who is the pattadar in this village'.",
        "members": ["V07"],
    },
    "khata_extent_by_village": {
        "desc": "The TOTAL EXTENT recorded against each KHATA, village by village — "
                "holdings aggregated by khata number. e.g. 'what is the total extent "
                "recorded against each khata'.",
        "members": ["Q077"],
    },
    "unverified_khatas": {
        "desc": "PM-KISAN khata numbers with NO matching entry in the land records — "
                "roster land claims with no revenue record behind them, the sharpest "
                "single inclusion-error flag. e.g. 'which PM-KISAN khata numbers "
                "have no matching land record'.",
        "members": ["Q078"],
    },
    "unmatched_land_parcels": {
        "desc": "Land parcels that CANNOT be matched to a PM-KISAN farmer by name "
                "and village — survey_land_records carries no Aadhaar, so these are "
                "a fuzzy-match review queue rather than errors. e.g. 'which land "
                "parcels cannot be matched to a beneficiary'.",
        "members": ["Q075"],
    },
    "contested_survey_numbers": {
        "desc": "The same SURVEY NUMBER claimed by more than one person across "
                "systems — overlapping land claims, either unrecorded subdivision or "
                "a duplicate benefit claim. e.g. 'is the same survey number claimed "
                "by more than one person'.",
        "members": ["Q079"],
    },
    "cultivator_not_pattadar_by_survey": {
        "desc": "SURVEY NUMBERS where the recorded CULTIVATOR differs from the "
                "PATTADAR — the tenancy signal listed per survey number, joining "
                "agriculture to survey_land_records. e.g. 'which records show a "
                "pattadar different from the recorded cultivator for the same survey "
                "number'.",
        "members": ["M09"],
    },
    "cultivator_not_pattadar_count": {
        "desc": "IN HOW MANY CASES the recorded cultivator differs from the pattadar "
                "— the tenancy signal as a count within agriculture, not a per-survey "
                "listing. e.g. 'in how many cases is the cultivator different from "
                "the land title holder'.",
        "members": ["Q074"],
    },
    "village_land_saturation": {
        "desc": "For each VILLAGE, how the number of beneficiaries compares with the "
                "LAND on record — beneficiaries per acre, where a high count against "
                "a small land base suggests fragmentation or over-registration. e.g. "
                "'how does the beneficiary count compare with land on record per "
                "village'.",
        "members": ["Q084"],
    },
    "apmip_extent_verification": {
        "desc": "Whether the land EXTENT claimed for a MICRO-IRRIGATION subsidy "
                "matches the revenue record — horticulture_apmip against "
                "survey_land_records, both in acres so no conversion is needed. e.g. "
                "'does the extent claimed for micro-irrigation match the land record'.",
        "members": ["Q085"],
    },
    "natural_farming_acreage_verification": {
        "desc": "Whether the ACREAGE claimed under NATURAL FARMING matches the "
                "recorded land extent — ryss against survey_land_records. e.g. 'does "
                "the acreage claimed under natural farming match the land records'.",
        "members": ["Q087"],
    },

    # ══ Convergence rankings, scorecards, exclusion ═══════════════════════
    "convergence_ranking_by_geography": {
        "desc": "Areas ranked by the AVERAGE NUMBER OF SCHEMES per farmer — "
                "districts, mandals or villages ordered by convergence breadth, with "
                "the count of farmers receiving nothing alongside. Counts include "
                "PM-KISAN. e.g. 'rank districts by average schemes per farmer', "
                "'which areas converge best'.",
        "members": ["G34-S", "G34-D", "G34-M"],
    },
    "convergence_by_social_category": {
        "desc": "The AVERAGE NUMBER OF SCHEMES accessed by each SOCIAL CATEGORY — "
                "does caste predict access, as a mean scheme count per category "
                "(including PM-KISAN). e.g. 'what is the average number of schemes "
                "accessed by each social category'.",
        "members": ["Q038"],
    },
    "scheme_access_by_land_size": {
        "desc": "Whether SCHEME ACCESS RISES WITH LANDHOLDING — average scheme count "
                "per land-size band for the chosen area, the equity question of "
                "whether bigger farmers capture more. Counts include PM-KISAN. e.g. "
                "'does the number of schemes a farmer accesses rise with their "
                "landholding'.",
        "members": ["G45-S", "G45-D", "G45-M"],
    },
    "ekyc_pending_yet_paid": {
        "desc": "Farmers whose eKYC is PENDING yet who are STILL RECEIVING benefits "
                "— money moving to identities the system has not confirmed, for the "
                "chosen area. Reads the roster's verification state against the "
                "state schemes. e.g. 'which farmers have eKYC pending yet receive "
                "scheme benefits'.",
        "members": ["G37-S", "G37-D", "G37-M"],
    },
    "excluded_status_yet_paid": {
        "desc": "Farmers whose BENEFICIARY STATUS is not 'Included' (Excluded or "
                "Pending) yet who are still DRAWING benefits — status says stop, "
                "payments say go. Distinct from the eKYC version, which is about "
                "verification rather than entitlement. e.g. 'which excluded PM-KISAN "
                "farmers are still receiving AP scheme benefits'.",
        "members": ["Q128"],
    },
    "benefits_without_land_record": {
        "desc": "Farmers receiving LAND-LINKED benefits who have NO land record at "
                "all — unverifiable entitlements for the chosen area, joining the "
                "roster and agriculture against survey_land_records. e.g. 'which "
                "farmers have benefits but no land record'.",
        "members": ["G38-S", "G38-D", "G38-M"],
    },
    "area_scorecard": {
        "desc": "The one-page AREA SCORECARD — farmers, land, subsidy and "
                "procurement side by side for each district, mandal or village, one "
                "column per department. The standing review-meeting table. e.g. "
                "'give me a district scorecard'.",
        "members": ["G39-S", "G39-D", "G39-M"],
    },
    "beneficiary_register": {
        "desc": "The full BENEFICIARY REGISTER for an area — every farmer listed "
                "with what they have received from each department, one row per "
                "farmer. The working list, not an aggregate. e.g. 'list every farmer "
                "and what they have received'.",
        "members": ["G40-S", "G40-D", "G40-M"],
    },

    # ══ Added by the template-fidelity pass (2026-07-30) ══════════════════
    "apmip_statewide_headline": {
        "desc": "The STATEWIDE micro-irrigation (APMIP) headline in one row — how "
                "many beneficiaries there are in total, the acres covered, and the "
                "subsidy sanctioned against the subsidy actually released. A single "
                "summary row, not a per-district breakdown: G21 is the family that "
                "splits the same coverage by district, mandal or village. e.g. 'how "
                "many horticulture beneficiaries are there', 'total APMIP subsidy "
                "sanctioned and released'.",
        "members": ["Q147"],
    },
    "farmer_land_record_link": {
        "desc": "Links ONE named farmer's PM-KISAN entry to their SURVEY LAND RECORD "
                "on khata number — roster village and declared area against the "
                "revenue record's pattadar name, survey number, status and recorded "
                "extent, with the declared-over-recorded ratio. The record-linkage "
                "view: F11 asks only whether the areas agree, this one shows the "
                "matched record itself. e.g. 'link this farmer's land records to "
                "their PM-KISAN entry', 'show the khata and survey number behind "
                "this farmer's declared area'.",
        "members": ["F13"],
    },
    "roster_in_all_six_state_schemes": {
        "desc": "PM-KISAN roster farmers who are ALSO in every one of the six AP "
                "STATE schemes — the full-house convergence list, one row per "
                "farmer. Membership in the roster is the population being tested "
                "(the inner join), so the six counted schemes are the state ones "
                "only. Fixed at six: no scheme-count number is read from the "
                "question, which is what separates it from the exactly-N family. "
                "e.g. 'do any farmers receive PM-KISAN and all 6 AP schemes', "
                "'farmers in every state programme as well as the roster'.",
        "members": ["Q148"],
    },
    "landholding_by_category_and_band": {
        "desc": "Landholding CROSS-TABULATED by social category AND land-size band "
                "— SC/ST/BC/OC against marginal (<1 ha), small (1-2 ha) and "
                "semi-medium-and-above (>2 ha), with farmer counts, total and "
                "average area in each cell. The two-dimensional distribution, not "
                "the per-category average (that is the averages-only family) and not "
                "the bands alone. e.g. 'how is landholding distributed across social "
                "categories by land size', 'land-size bands per caste category'.",
        "members": ["Q149"],
    },
    "procurement_payment_per_farmer": {
        "desc": "What EACH FARMER has been paid for MSP procurement — one row per "
                "supplier with their delivery count, total quantity and total amount "
                "paid, ranked so the biggest earners lead. A per-farmer league "
                "table; the family that totals procurement by district or mandal is "
                "the geographic one. Reads markfed. e.g. 'what has each farmer been "
                "paid for procurement', 'who are the top procurement earners'.",
        "members": ["Q151"],
    },
    "unreached_small_farmers": {
        "desc": "Farmers BELOW a land threshold the query supplies who receive "
                "nothing from any of the six STATE schemes — the most-entitled, "
                "least-reached list. A size-filtered subset of the plain exclusion "
                "list: use this one only when the question names a hectare "
                "threshold or says 'small'/'marginal'. Being on the PM-KISAN roster "
                "never counts as coverage here. e.g. 'which farmers below 1 hectare "
                "receive nothing from any state scheme'.",
        "members": ["Q152"],
    },
    "flagged_yet_credited_installment": {
        "desc": "Farmers the roster has FLAGGED — beneficiary status Excluded or "
                "Pending, or eKYC still pending — who were nonetheless CREDITED a "
                "PM-KISAN INSTALLMENT, listed with the installment number, date and "
                "amount. The central-DBT leakage leg: the eKYC-pending and "
                "excluded-status families ask whether flagged farmers draw STATE "
                "scheme benefits, this one asks whether PM-KISAN itself paid them, "
                "and the plain status-list families apply no payment condition at "
                "all. e.g. 'which excluded beneficiaries were still credited an "
                "installment', 'eKYC pending but the money went out'.",
        "members": ["Q153"],
    },
    "apmip_random_inspection_backlog": {
        "desc": "Micro-irrigation applications whose RANDOM INSPECTION is pending or "
                "under review — the RI_Status_Code backlog for the chosen area, "
                "Approved excluded. Random inspection is a SEPARATE process from "
                "application approval and the two disagree on most rows, so pick "
                "this family whenever the question says 'random inspection' or 'RI' "
                "and the application-processing backlog family whenever it says "
                "inspection or verification backlog without naming RI. e.g. 'how "
                "many beneficiaries have random inspection pending or under review', "
                "'what is the RI backlog'.",
        "members": ["G46-S", "G46-D", "G46-M"],
    },
    "seasonal_subsidy_by_transaction": {
        "desc": "The season split of input subsidy counted by TRANSACTION — one row "
                "per season with the number of subsidy transactions, subsidy total, "
                "farmer contribution and the subsidy-to-contribution ratio. Same cut "
                "as the per-farmer seasonal family, which counts DISTINCT FARMERS "
                "instead; pick this one when the question is about transactions or "
                "about the ratio itself, and that one when it is about how many "
                "farmers took subsidy in each season. e.g. 'what is the input "
                "subsidy by season and how does it compare with the farmers' own "
                "contribution'.",
        "members": ["Q150"],
    },

    # ══ Casual-phrasing coverage (fidelity item 13, 2026-07-30) ═══════════
    "crop_filtered_ekyc_pendency": {
        "desc": "Farmers growing ONE NAMED CROP whose eKYC is still PENDING — a "
                "crop-filtered verification worklist, one row per farmer. Pick "
                "this over the plain eKYC-status list whenever a crop is named: "
                "that family has no crop slot and silently answers for all crops. "
                "The crops-per-status family is an aggregate of crop names, not a "
                "list of people. e.g. 'give me a list of paddy farmers whose eKYC "
                "is pending', 'cotton growers with eKYC not done'.",
        "members": ["Q154"],
    },
    "landholding_threshold_list": {
        "desc": "The plain list of PM-KISAN farmers holding LESS THAN a given area, "
                "with no other condition — name, place, category, hectares and "
                "acres. This is the default for any bare 'farmers with under N "
                "hectares / less than an acre' question. Three near neighbours add "
                "a condition and must NOT be used for the bare question: one also "
                "requires never having taken an input subsidy, one also requires "
                "being in no state scheme, and the land-size-band family returns "
                "counts per band rather than a list of people. Accepts acres and "
                "converts (1 acre = 0.4047 ha). e.g. 'how many farmers with less "
                "than 1 acre land', 'list of marginal farmers'.",
        "members": ["Q155"],
    },
    "farmer_name_search": {
        "desc": "How many farmers SHARE A GIVEN NAME and where each of them is — "
                "one row per namesake with district, village, land and status, plus "
                "the total count of people with that name. The template for name "
                "COLLISIONS: use it when the question asks to list or count "
                "everyone called something, rather than to look one person up. The "
                "single-farmer families answer about one person and will ask which "
                "one is meant; here the ambiguity IS the answer. e.g. 'give me a "
                "list of all farmers named Ramesh Naidu', 'how many farmers have "
                "this name'.",
        "members": ["F14"],
    },
    "ecrop_registrations_by_year": {
        "desc": "eCrop crop registrations BY YEAR — one row per crop year with the "
                "distinct farmers who registered, the number of registrations and "
                "the subsidy disbursed. The enrolment trend across all years at "
                "once, so it is the right answer to 'each year' / 'year-wise' "
                "questions that must not be clamped to a single year. e.g. 'how "
                "many farmers registered crops in eCrop each year', 'eCrop "
                "enrolment trend'.",
        "members": ["Q156"],
    },
}

# query_id -> family description, expanded from the members lists above.
DESC_BY_QID: dict[str, str] = {
    qid: family["desc"]
    for family in FAMILY_DESCRIPTIONS.values()
    for qid in family["members"]
}

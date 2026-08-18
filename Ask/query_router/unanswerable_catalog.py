"""
The questions this database CANNOT answer, and why.

Thirty of them: the 17 rows the workbook marks "Answerable from DB = No", and
the 13 beneficiary questions on its Dropped sheet.

WHY THEY ARE IN THE CATALOGUE AT ALL
    Officers will ask these. Beneficiary questions especially — "how many
    beneficiaries got a pension in this GP" is an obvious thing to want, and the
    only beneficiary table in the database is empty. Left out of the catalogue,
    such a question retrieves nothing, scores below the no-match threshold and
    gets the generic "I'm not sure I can answer that specific question yet"
    fallback, which is indistinguishable from the bot merely failing. The
    officer is left unsure whether to rephrase, and a bot that looks unreliable
    on an answerable-sounding question is worse than one that says plainly what
    it does not hold.

    So these are RETRIEVABLE but NOT EXECUTABLE. They carry no SQL and no slots.
    `router` serves a matched id from here as an honest refusal built from the
    workbook's own reason — "the database cannot answer this because …" — and
    offers the nearest answerable questions where the note names one.

    They are a SEPARATE dict from TEMPLATE_CATALOG deliberately. Everything that
    iterates TEMPLATE_CATALOG assumes an entry has SQL and slots — the binder,
    the execution gate, `validate_catalog`, `_accepted_filters`. Merging the two
    would mean teaching every one of those about a third kind of entry; keeping
    them apart means the retriever indexes both and only the router has to know.

KEYS
    question    the workbook's Original Question, placeholders written out.
    reason      the Answerability Note / drop reason, VERBATIM. This is what the
                user is told; it is the whole value of the entry.
    alternative a query_id that answers the nearest answerable question, where
                the workbook's note names one. Offered as a chip, never
                substituted silently.
"""
# ── GENERATED FILE — do not edit by hand ─────────────────────────────────────
# Built from AI_Chatbot_Questions.xlsx by tools/build_catalog.py.
# To change a question, a caveat or a SQL string, change the WORKBOOK and
# regenerate; `python tools/build_catalog.py --check` fails if this file and the
# workbook have drifted apart.


UNANSWERABLE_CATALOG: dict[str, dict] = {

    'PLN-022': {
        "question": 'Which Blocks consistently experience delays in GPDP approvals in a given year?',
        "reason": "Requires a business rule for 'consistently delayed' and a submission deadline, neither of which exists in the database. PLN-010 with a user-supplied $deadline is the closest answerable form.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "source": 'No',
        "alternative": 'PLN-010',
        "paraphrases": [
            'Which Blocks consistently experience delays in GPDP approvals in FY 2025-26?',
            'Which Blocks consistently experience delays in GPDP approvals?',
        ],
    },

    'PLN-023': {
        "question": 'Which Districts consistently experience delays in GPDP approvals in a given year?',
        "reason": 'Same blocker as PLN-022 at district level.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "source": 'No',
        "alternative": 'PLN-022',
        "paraphrases": [
            'Which Districts consistently experience delays in GPDP approvals in FY 2025-26?',
            'Which Districts consistently experience delays in GPDP approvals?',
        ],
    },

    'PLN-041': {
        "question": 'Which themes have remained consistently among the top priorities over the last five years?',
        "reason": "'Consistently among the top priorities' is not a defined rule. PLN-038 gives the year-by-year series the user can judge from.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "source": 'No',
        "alternative": 'PLN-038',
        "paraphrases": [
            'Which themes have remained consistently among the top priorities over the 2022-23 to 2026-27?',
        ],
    },

    'PLN-042': {
        "question": 'Which themes have remained consistently among the lowest priorities over the last five years?',
        "reason": 'Same blocker as PLN-041.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "source": 'No',
        "alternative": 'PLN-041',
        "paraphrases": [
            'Which themes have remained consistently among the lowest priorities over the 2022-23 to 2026-27?',
        ],
    },

    'PLU-005': {
        "question": 'How many activities in a given Block are delegated to another panchayat tier for execution in a given Plan Year?',
        "reason": 'activity_delegation.is_delegated and delegated_unit_code are 100% NULL, so no activity can be identified as delegated to another panchayat tier.',
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Plan Structure',
        "source": 'No',
        "paraphrases": [
            'How many activities in Attabira are delegated to another panchayat tier for execution in 2025-26?',
            'How many activities are delegated to another panchayat tier for execution?',
        ],
    },

    'SCH-004': {
        "question": 'What is the fund allocated under a given Scheme at ZP, Block, and GP tiers in a given District for a given Plan Year?',
        "reason": 'The database holds only GP-tier data (gram_panchayat has no ZP or block tier rows), so a scheme split across ZP, Block and GP tiers cannot be produced.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "source": 'No',
        "paraphrases": [
            'What is the fund allocated under XV Finance Commission at ZP, Block, and GP tiers in Khordha for 2025-26?',
            'What is the fund allocated under a given Scheme at ZP, Block, and GP tiers?',
        ],
    },

    'PHY-002': {
        "question": 'What are the stage-wise completion dates for asset a given Asset Code?',
        "reason": 'No stage-wise completion dates exist anywhere in the database.',
        "bracket": 'Implementation & Progress',
        "module": 'Physical Progress',
        "submodule": 'Asset Stages',
        "source": 'No',
        "paraphrases": [
            'What are the stage-wise completion dates for asset 509018477?',
        ],
    },

    'PHY-005': {
        "question": 'Which assets in a given Block have not advanced a stage in the last a given Threshold days?',
        "reason": 'Requires stage-transition dates, which are not recorded.',
        "bracket": 'Implementation & Progress',
        "module": 'Physical Progress',
        "submodule": 'Asset Stages',
        "source": 'No',
        "paraphrases": [
            'Which assets in Attabira have not advanced a stage in the last 90 days?',
            'Which assets have not advanced a stage in the last a given Threshold days?',
        ],
    },

    'AST-004': {
        "question": 'Where are the assets under activity a given Activity Code located, and how many units at each location?',
        "reason": 'asset_loc_code, asset_loc_unit_code, asset_loc_unit_type and asset_loc_unit_count are 100% NULL, so asset locations cannot be reported.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "source": 'No',
        "paraphrases": [
            'Where are the assets under activity 125711758 located, and how many units at each location?',
        ],
    },

    'AST-005': {
        "question": 'What are the unit count and unit cost of assets created under activity a given Activity Code?',
        "reason": 'asset_unit_count and asset_unit_cost are 100% NULL.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "source": 'No',
        "paraphrases": [
            'What are the unit count and unit cost of assets created under activity 125711758?',
        ],
    },

    'AST-010': {
        "question": 'What is the average unit cost of a given Asset Sub Category across a given District for a given Plan Year?',
        "reason": 'asset_unit_cost is 100% NULL, so an average unit cost cannot be computed.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "source": 'No',
        "paraphrases": [
            'What is the average unit cost of tap connections across Khordha for 2025-26?',
            'What is the average unit cost of a given Asset Sub Category?',
        ],
    },

    'AST-011': {
        "question": 'Which a given Asset Sub Category assets in a given District have a unit cost more than a given Threshold percent above the district average in a given year?',
        "reason": 'asset_unit_cost is 100% NULL, so unit costs cannot be compared against a district average.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "source": 'No',
        "paraphrases": [
            'Which overhead tank assets in Khordha have a unit cost more than 50 percent above the district average in FY 2025-26?',
            'Which a given Asset Sub Category assets have a unit cost more than a given Threshold percent above the district average?',
        ],
    },

    'SBM-SWM-033': {
        "question": 'How many such vehicles have been repaired in a given year?',
        "reason": 'Repairs to collection vehicles cannot be isolated: there is no repair flag, and combining work_type = Maintenance with a vehicle keyword returns no rows in any year.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "source": 'No',
        "paraphrases": [
            'How many such vehicles have been repaired in FY 2025-26?',
            'How many such vehicles have been repaired?',
        ],
    },

    'ALR-006': {
        "question": 'Which suspended activities in a given Block have payment vouchers dated after suspension in a given year?',
        "reason": "Requires a suspension date and a 'suspended' status. Neither exists - the only comparable status is WORK ABANDONED, and it carries no date.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "source": 'No',
        "paraphrases": [
            'Which suspended activities in Attabira have payment vouchers dated after suspension in FY 2025-26?',
            'Which suspended activities have payment vouchers dated after suspension?',
        ],
    },

    'ALR-007': {
        "question": 'Which activities in a given Block have been ongoing longer than their planned duration in a given year?',
        "reason": 'Requires a planned duration or start date per activity; planned_activity has no duration or date columns.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Progress Exceptions',
        "source": 'No',
        "paraphrases": [
            'Which activities in Begunia have been ongoing longer than their planned duration in FY 2025-26?',
            'Which activities have been ongoing longer than their planned duration?',
        ],
    },

    'ALR-010': {
        "question": 'Which GPs in a given District have a resource envelope allocation but no uploaded plan for a given Plan Year?',
        "reason": 'There is no resource-envelope or allocation table, so GPs with an envelope but no plan cannot be identified.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Progress Exceptions',
        "source": 'No',
        "paraphrases": [
            'Which GPs in Khordha have a resource envelope allocation but no uploaded plan for 2025-26?',
            'Which GPs have a resource envelope allocation but no uploaded plan?',
        ],
    },

    'DSS-004': {
        "question": 'Which GPs in a given Block could reach the next PAI grade with the smallest score improvement, and on which themes are they weakest in a given year?',
        "reason": 'PAI (Panchayat Advancement Index) grades and scores are not present anywhere in the database.',
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "source": 'No',
        "paraphrases": [
            'Which GPs in Attabira could reach the next PAI grade with the smallest score improvement, and on which themes are they weakest in FY 2025-26?',
            'Which GPs could reach the next PAI grade with the smallest score improvement, and on which themes are they weakest?',
        ],
    },

    'BEN-001': {
        "question": 'How many beneficiaries received benefits under a given Scheme in a given GP Name during a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'How many beneficiaries received benefits under a given Scheme?',
            'Kitne beneficiaries ko benefit mila har Scheme?',
        ],
    },

    'BEN-002': {
        "question": 'What is the village-wise count of beneficiaries in a given GP Name under a given Scheme for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'What is the village-wise count of beneficiaries under a given Scheme?',
            'Village-wise count of beneficiaries har Scheme kya hai?',
        ],
    },

    'BEN-003': {
        "question": 'How many beneficiaries are recorded across GPs of a given Block under a given Scheme for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'How many beneficiaries are recorded across GPs under a given Scheme?',
            'Kitne beneficiaries darj hain GPs me har Scheme?',
        ],
    },

    'BEN-004': {
        "question": 'What is the cash versus kind split of benefits distributed in a given GP Name for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'What is the cash versus kind split of benefits distributed?',
            'Cash versus kind split of benefits distributed kya hai?',
        ],
    },

    'BEN-005': {
        "question": 'What is the total cash benefit quantum distributed under a given Scheme in a given GP Name for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'What is the total cash benefit quantum distributed under a given Scheme?',
            'Total cash benefit quantum distributed har Scheme kitna hai?',
        ],
    },

    'BEN-006': {
        "question": 'How many beneficiaries in a given GP Name received benefits for each stated purpose in a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'How many beneficiaries received benefits for each stated purpose?',
            'Kitne beneficiaries ko benefit mila har stated purpose?',
        ],
    },

    'BEN-007': {
        "question": 'Which scheme has the most recorded beneficiaries in a given Block for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'Which scheme has the most recorded beneficiaries?',
            'Sabse zyada recorded beneficiaries kis scheme me hain?',
        ],
    },

    'BEN-008': {
        "question": 'Which GPs in a given Block have no recorded beneficiaries under a given Scheme for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'Which GPs have no recorded beneficiaries under a given Scheme?',
            'Kin GPs me koi recorded beneficiaries har Scheme nahi hai?',
        ],
    },

    'BEN-009': {
        "question": 'List the beneficiaries of a given Scheme in a given GP Name for a given Plan Year with village and benefit details.',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'List the beneficiaries of a given Scheme with village and benefit details.',
            'Beneficiaries ke Scheme ke saath village and benefit details ki list dikhao',
        ],
    },

    'BEN-010': {
        "question": 'How many beneficiaries are recorded under each pension scheme in a given Block for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'How many beneficiaries are recorded under each pension scheme?',
            'Kitne beneficiaries darj hain har pension scheme?',
        ],
    },

    'BEN-011': {
        "question": 'Compare beneficiary counts under a given Scheme between a given Block and a given Block 2 for a given Plan Year.',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'Compare beneficiary counts under a given Scheme between a given Block and a given Block 2.',
            'Beneficiary counts har Scheme ke beech Block and Block 2 compare karo',
        ],
    },

    'BEN-012': {
        "question": 'How has the beneficiary count under a given Scheme in a given GP Name changed over a given Date Range?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Beneficiaries',
        "module": 'Beneficiary',
        "submodule": 'Beneficiary',
        "source": 'Dropped',
        "paraphrases": [
            'How has the beneficiary count under a given Scheme changed?',
            'The beneficiary count har Scheme me kya change aaya?',
        ],
    },

    'DQY-005': {
        "question": 'How many beneficiary records in a given GP Name are missing the village field for a given Plan Year?',
        "reason": 'Removed at your request. The only beneficiary table in the database, activity_nsap, has 0 rows, and activity_community_service.community_beneficiaries_expected and activity_training.training_trainees_total are 100% NULL. Nothing in the schema can answer it. Restore this row if the scraper starts populating NSAP data.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Data Quality',
        "source": 'Dropped',
        "paraphrases": [
            'How many beneficiary records are missing the village field?',
            'Kitne beneficiary records are missing the village field hain?',
        ],
    },
}


def retrieval_corpus():
    """(text, query_id) pairs for embedding, same shape as the template catalogue."""
    pairs = []
    for qid, entry in UNANSWERABLE_CATALOG.items():
        pairs.append((entry["question"], qid))
        for p in entry.get("paraphrases", []):
            pairs.append((p, qid))
    return pairs


def refusal_for(query_id: str) -> str | None:
    """The sentence an officer is shown, built from the workbook's own reason.

    Verbatim, for the same reason a caveat is verbatim: the reason IS the
    answer to "why not", and a paraphrase of it is a worse answer.
    """
    entry = UNANSWERABLE_CATALOG.get(query_id)
    if entry is None:
        return None
    return (
        f"I can't answer that from this database. {entry['reason']}"
    )

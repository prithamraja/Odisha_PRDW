"""
AP Department of Agriculture — Decision Aid query templates.

278 templates across eight departmental datasets, in the same contract as the
PM-JAY catalog: ``?`` positional placeholders, ``param_slots`` giving the ordered
entities to extract and validate, and a ``date_filter`` descriptor the runtime uses
to append a date range.

TWO CATALOGS
    TEMPLATE_CATALOG          139 templates that take at least one entity.
    UNPARAMETERISED_CATALOG   139 whole-of-state templates that take none —
                              statewide aggregates and cross-dataset integrity checks.
    They are authored separately but MERGED at the bottom of this module, so
    TEMPLATE_CATALOG as imported by the backend holds all 278. See the note there.

ID SCHEME
    Gnn-S / -D / -M   one base query at State / District / Mandal scope.
                      -S has no geography slot, -D takes {district}, -M takes both.
    Qnnn              standalone template.
    IDs match the accompanying workbook and markdown, so a reviewer can trace any
    template back to its documented question and demo result.

EXTRA KEYS
    Beyond the PM-JAY five, each entry carries persona, theme, datasets, geo_level,
    paraphrases, notes and date_kind. All additive — a loader reading only the
    original five keys is unaffected.

DATE FILTERING
    ``date_filter`` is {"alias", "column"} exactly as in PM-JAY; ``date_kind`` says
    how to compare:
        iso     a real date — router._inject_date_filter emits
                <col>::DATE BETWEEN ? AND ?.
        year    agriculture has no date column at all, only cropyear. Date questions
                against Agriculture can only be answered at year granularity, so the
                injector compares the year numbers instead.
        serial  Excel day numbers. NO LONGER USED BY ANY TEMPLATE. The 22 entries on
                horticulture_apmip.SanctionProceedingDate and
                fisheries.fcs_registration_date that carried this kind were flipped
                to `iso` when the catalog was integrated: the data contract for both
                the shipped stub (build_stub_data.py) and the real flat drop is real
                dates, no Excel serials. The kind is still recognised by the injector,
                which raises a clear "not supported" error rather than silently
                comparing a date against a day number — so mis-shaped data fails loud.

    Many AP date_filters have an EMPTY alias, because the SQL is single-table and
    the column is unqualified. The injector must omit the dot and quote the column
    (columns are mixed-case: "SurveyDate", "PROCUREMENT_DATE").
    Sericulture has no date column of any kind and so has no date_filter anywhere.
    Every template with a non-None date_filter is guaranteed to have a WHERE clause
    for the runtime to append to. Ranges should be half-open: from inclusive, to
    exclusive.

WHAT IS DELIBERATELY NOT A SLOT
    Village. District and mandal are slots; at mandal scope the output groups by
        village anyway, so the breakdown is visible without a village parameter.
    Pendency status. Queries like "which payments are stuck" hardcode
        <> 'Approved' because that is the definition of the question, not a filter
        the user chooses. Status is a slot only where the question is genuinely
        status-agnostic.
    Land bands. Marginal / small / semi-medium are a policy definition, not a
        user-supplied threshold.

UNITS WARNING
    pm_kisan.area_hectares is in HECTARES. Every other dataset stores acres.
    1 ha = 2.47105 acres. Compare without converting and every farmer looks like a
    discrepancy.

VALIDATION
    Every template here was executed against a SQLite database built from the eight
    demo tabs, with demo values bound to each slot: placeholder arity matches
    param_slots, positional order is correct, and every dated template was re-run
    with a date predicate appended to confirm it composes. See validate_catalog.py.

    54 templates return zero rows on the demo data because that data is
    internally consistent. Each is an integrity check — the bot must report
    "no records found" rather than fabricate rows.

TABLES
    pm_kisan, agriculture, horticulture_apmip, fisheries, sericulture, markfed,
    ryss, survey_land_records — one flat table per source tab, column names quoted
    exactly as they appear.

DIALECT
    ANSI SQL verified on SQLite. For PostgreSQL: rewrite ? to $1, $2 … and replace
    GROUP_CONCAT(DISTINCT x) with STRING_AGG(DISTINCT x, ',').
"""


# Entity types the extractor must produce, with the source to validate against.
# 'demo' is the value used by validate_catalog.py.
ENTITY_TYPES: dict[str, dict] = {
    "district": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.district (or the district master)',
        "examples": ['Krishna', 'Guntur', 'Kurnool'],
        "demo": 'Krishna',
    },
    "mandal": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.sub_district',
        "examples": ['Machilipatnam', 'Tenali', 'Gudivada'],
        "demo": 'Machilipatnam',
    },
    "village": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.village',
        "examples": ['Pedana', 'Kolakaluru'],
        "demo": 'Kolakaluru',
    },
    "farmer_name": {
        "kind": 'free_text',
        "validate_against": 'pm_kisan.name (fuzzy match, confirm before use)',
        "examples": ['Ramesh Naidu'],
        "demo": 'Ramesh Naidu',
    },
    "aadhaar": {
        "kind": 'identifier',
        "validate_against": '12 digits; never echo in full in the answer',
        "examples": ['726018159083'],
        "demo": '726018159083',
    },
    "crop": {
        "kind": 'categorical',
        "validate_against": 'agriculture.cropname / markfed.CROP_NAME',
        "examples": ['Paddy', 'Cotton', 'Maize'],
        "demo": 'Paddy',
    },
    "season": {
        "kind": 'categorical',
        "validate_against": 'agriculture.season',
        "examples": ['Kharif', 'Rabi'],
        "demo": 'Kharif',
    },
    "crop_year": {
        "kind": 'numeric_year',
        "validate_against": 'agriculture.cropyear',
        "examples": [2024, 2025],
        "demo": 2024,
    },
    "social_category": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.category',
        "examples": ['SC', 'ST', 'BC', 'OC'],
        "demo": 'SC',
    },
    "social_category_2": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.category (second value in a pair)',
        "examples": ['ST'],
        "demo": 'ST',
    },
    "gender": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.gender',
        "examples": ['Female', 'Male'],
        "demo": 'Female',
    },
    "ekyc_status": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.ekyc_status',
        "examples": ['Pending', 'Completed'],
        "demo": 'Pending',
    },
    "beneficiary_status": {
        "kind": 'categorical',
        "validate_against": 'pm_kisan.beneficiary_status',
        "examples": ['Included', 'Excluded'],
        "demo": 'Included',
    },
    "approval_status": {
        "kind": 'categorical',
        "validate_against": 'Status / PAYMENT_STATUS / current_status',
        "examples": ['Approved', 'Pending', 'Under Review'],
        "demo": 'Approved',
    },
    "top_n": {
        "kind": 'numeric',
        "validate_against": 'positive integer, cap at 100',
        "examples": [10, 20],
        "demo": 10,
    },
    "scheme_count": {
        "kind": 'numeric',
        "validate_against": 'integer 1-6',
        "examples": [1, 3, 6],
        "demo": 3,
    },
    "threshold_hectares": {
        "kind": 'numeric',
        "validate_against": 'positive number, HECTARES not acres',
        "examples": [1.0, 2.0],
        "demo": 2.0,
    },
    "threshold_qty_per_acre": {
        "kind": 'numeric',
        "validate_against": 'positive number; crop-specific, needs agronomic sign-off',
        "examples": [10],
        "demo": 10,
    },
    "tolerance_pct": {
        "kind": 'numeric',
        "validate_against": '0-100, expressed as a percentage',
        "examples": [5, 10],
        "demo": 10,
    },
    "scheme": {
        "kind": 'categorical',
        "validate_against": 'closed set: Agriculture, Horticulture, Fisheries, Sericulture, MARKFED, RySS',
        "examples": ['Sericulture', 'MARKFED'],
        "demo": 'Sericulture',
    },
    "scheme_2": {
        "kind": 'categorical',
        "validate_against": 'same closed set as scheme (second value in a pair)',
        "examples": ['Fisheries'],
        # Must differ from scheme's demo, or the paired templates (S02 etc.)
        # validate degenerately against 'Sericulture' vs 'Sericulture'.
        "demo": 'Fisheries',
    },
    "crop_status": {
        "kind": 'categorical',
        "validate_against": "agriculture.cropstatus — ONLY Approved, Pending, Under Review. 'Damaged' does not exist.",
        "examples": ['Approved', 'Pending', 'Under Review'],
        "demo": 'Approved',
    },
    "name_search": {
        "kind": 'free_text',
        "validate_against": 'pm_kisan.name, passed through WITHOUT disambiguation — F14 counts the people who share a name, so resolving to one defeats the question',
        "examples": ['Ramesh Naidu'],
        "demo": 'Ramesh Naidu',
    },
    "aadhaar_length": {
        "kind": 'numeric',
        "validate_against": 'fixed at 12; exposed only so the rule is visible',
        "examples": [12],
        # RUNTIME CONTRACT: this is a constant, not something a user says. The
        # extractor is never asked for it (entity_extractor.py) — the router's
        # extraction shim defaults it to 12 before validation, and the validator
        # pins it to 12 regardless of input. Never surface it as a clarify
        # question ("For which aadhaar length?").
        "demo": 12,
    },
}


# Templates that take at least one extracted entity.
TEMPLATE_CATALOG: dict[str, dict] = {

    # ── Convergence & overlap ─────────────────────────────────────────────
    "F01": {
        "abstract_question": 'What is the PM-KISAN record for {farmer_name} — status, land, installment?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "category", "gender",
       "area_hectares", "khata_no", "ekyc_status", "beneficiary_status",
       "last_installment_no", "last_installment_date", "last_amount_credited", "mobile_no"
FROM pm_kisan
WHERE "aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Look up one farmer on the roster', 'eKYC status and last payment for a farmer',
                        'What do we know about {farmer_name}?'],
        "notes": 'Keyed on the Aadhaar the name resolved to, never on the name: 316 of 446 roster names are shared, so a name filter returned every namesake as an extra row. The validator disambiguates first and binds one person.',
        "expected_empty_on_demo": False,
    },

    "F09": {
        "abstract_question": 'Which datasets is {farmer_name} present in, and which is she missing from?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH me AS (SELECT ? AS aadhaar)
SELECT m.aadhaar,
       CASE WHEN EXISTS (SELECT 1 FROM pm_kisan           WHERE "aadhaar_no"    = m.aadhaar) THEN 'Yes' ELSE 'No' END AS pm_kisan,
       CASE WHEN EXISTS (SELECT 1 FROM agriculture        WHERE "aadharno"      = m.aadhaar) THEN 'Yes' ELSE 'No' END AS agriculture,
       CASE WHEN EXISTS (SELECT 1 FROM horticulture_apmip WHERE "EXTN_AADHARNO" = m.aadhaar) THEN 'Yes' ELSE 'No' END AS horticulture,
       CASE WHEN EXISTS (SELECT 1 FROM fisheries          WHERE "aadhar_no"     = m.aadhaar) THEN 'Yes' ELSE 'No' END AS fisheries,
       CASE WHEN EXISTS (SELECT 1 FROM sericulture        WHERE "aadhaar_no"    = m.aadhaar) THEN 'Yes' ELSE 'No' END AS sericulture,
       CASE WHEN EXISTS (SELECT 1 FROM markfed            WHERE "AADHAAR_NO"    = m.aadhaar) THEN 'Yes' ELSE 'No' END AS markfed,
       CASE WHEN EXISTS (SELECT 1 FROM ryss               WHERE "Aadhar_no"     = m.aadhaar) THEN 'Yes' ELSE 'No' END AS ryss,
       CASE WHEN EXISTS (SELECT 1 FROM survey_land_records s
                          JOIN pm_kisan p
                            ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
                           AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
                          WHERE p."aadhaar_no" = m.aadhaar) THEN 'Yes' ELSE 'No' END AS land_records
FROM me m;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Convergence & overlap',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Presence matrix for one farmer', 'Which schemes cover this farmer',
                        'Tell me what we know about {farmer_name}'],
        "notes": "One row: the presence matrix for ONE person. It used to union the name across all eight datasets, which merged everyone sharing it — and the union could not have reached an off-roster person anyway, because the roster the validator matches names against is pm_kisan. Survey land records hold no Aadhaar, so that leg still links by name AND village, of the resolved person's own roster row.",
        "expected_empty_on_demo": False,
    },

    "F12": {
        "abstract_question": 'What are the total benefits for {farmer_name} across every scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", 'Horticulture', "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     'Fisheries',    "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    'Sericulture',  "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    'MARKFED',      "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     'RySS',         "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    'PM-KISAN (latest installment)', "last_amount_credited" FROM pm_kisan
)
SELECT p."name", p."village", b.scheme,
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2) AS amount
FROM pm_kisan p
JOIN benefits b ON b.aadhaar = p."aadhaar_no"
WHERE p."aadhaar_no" = ?
GROUP BY p."aadhaar_no", p."name", p."village", b.scheme
ORDER BY amount DESC;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ["One farmer's total benefit", 'Everything paid to this farmer'],
        "notes": 'Sums different benefit types. Read as total public money touching the farmer, not as income. Filtered and grouped on the ONE Aadhaar the name resolved to: this template used to filter and GROUP BY the name, which reported the four different Lakshmi Devis as one farmer with a MARKFED total of 259,181.42 — two real people added together. The village column is there so the answer names which one.',
        "expected_empty_on_demo": False,
    },

    "G34-D": {
        "abstract_question": 'Rank mandals in {district} district by average schemes per farmer.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT p."sub_district" AS geography,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes_per_farmer,
       SUM(CASE WHEN c.n IS NULL THEN 1 ELSE 0 END) AS farmers_with_nothing
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
GROUP BY p."sub_district"
ORDER BY avg_schemes_per_farmer DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Convergence ranking', 'Which areas converge best?'],
        "notes": "Rewards breadth of service rather than spend. The farmers_with_nothing column is the exclusion list's size.",
        "expected_empty_on_demo": False,
    },

    "G34-M": {
        "abstract_question": 'Rank villages in {mandal} mandal by average schemes per farmer.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT p."village" AS geography,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes_per_farmer,
       SUM(CASE WHEN c.n IS NULL THEN 1 ELSE 0 END) AS farmers_with_nothing
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."village"
ORDER BY avg_schemes_per_farmer DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Convergence ranking', 'Which areas converge best?'],
        "notes": "Rewards breadth of service rather than spend. The farmers_with_nothing column is the exclusion list's size.",
        "expected_empty_on_demo": False,
    },

    "G35-D": {
        "abstract_question": 'Which farmers in {district} district receive nothing from any state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."mobile_no"
FROM pm_kisan p
WHERE p."aadhaar_no" NOT IN (SELECT aadhaar FROM sch WHERE aadhaar IS NOT NULL)
  AND p."district" = ?
ORDER BY p."area_hectares";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Completely unreached farmers', 'Exclusion list'],
        "notes": 'The core exclusion list. Every convergence effort should be measured against this shrinking.',
        "expected_empty_on_demo": True,
    },

    "G35-M": {
        "abstract_question": 'Which farmers in {mandal} mandal receive nothing from any state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."mobile_no"
FROM pm_kisan p
WHERE p."aadhaar_no" NOT IN (SELECT aadhaar FROM sch WHERE aadhaar IS NOT NULL)
  AND p."district" = ?
  AND p."sub_district" = ?
ORDER BY p."area_hectares";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Completely unreached farmers', 'Exclusion list'],
        "notes": 'The core exclusion list. Every convergence effort should be measured against this shrinking.',
        "expected_empty_on_demo": True,
    },

    "G36-D": {
        "abstract_question": 'Rank farmers in {district} district by total benefit across schemes.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    "last_amount_credited" FROM pm_kisan
)
SELECT p."name", p."district", p."sub_district", p."category",
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2) AS total_benefit
FROM pm_kisan p
JOIN benefits b ON b.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
GROUP BY p."name", p."district", p."sub_district", p."category"
ORDER BY total_benefit DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Total benefit league table', 'Aggregate public money per farmer'],
        "notes": 'Sums different benefit types together. Read as total public money touching that farmer, not as income.',
        "expected_empty_on_demo": False,
    },

    "G36-M": {
        "abstract_question": 'Rank farmers in {mandal} mandal by total benefit across schemes.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    "last_amount_credited" FROM pm_kisan
)
SELECT p."name", p."district", p."sub_district", p."category",
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2) AS total_benefit
FROM pm_kisan p
JOIN benefits b ON b.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."name", p."district", p."sub_district", p."category"
ORDER BY total_benefit DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Total benefit league table', 'Aggregate public money per farmer'],
        "notes": 'Sums different benefit types together. Read as total public money touching that farmer, not as income.',
        "expected_empty_on_demo": False,
    },

    "Q114": {
        "abstract_question": 'Which farmers are enrolled in exactly {scheme_count} schemes?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar, p."name", p."district",
       COUNT(DISTINCT s.scheme)        AS schemes,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM sch s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s.aadhaar
GROUP BY s.aadhaar, p."name", p."district"
HAVING COUNT(DISTINCT s.scheme) = ?
ORDER BY p."name";
""",
        "param_slots": [
            {"name": 'scheme_count', "entity_type": 'scheme_count', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Farmers in all six schemes', 'Maximum convergence cases', 'Which farmer participates in all the schemes', 'Farmers enrolled in exactly a given number of schemes'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q115": {
        "abstract_question": 'Which farmers are in exactly {scheme_count} scheme, and which one is it?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar, p."name", p."district",
       GROUP_CONCAT(DISTINCT s.scheme) AS only_scheme
FROM sch s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s.aadhaar
GROUP BY s.aadhaar, p."name", p."district"
HAVING COUNT(DISTINCT s.scheme) = ?
ORDER BY p."district";
""",
        "param_slots": [
            {"name": 'scheme_count', "entity_type": 'scheme_count', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Single-scheme farmers', 'Least converged beneficiaries'],
        "notes": 'The list to work on if the goal is deepening convergence rather than widening coverage.',
        "expected_empty_on_demo": False,
    },

    "Q121": {
        "abstract_question": 'Which farmers got both a micro-irrigation subsidy and an input subsidy in {crop_year}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT h."Farmer_Name", h."DISTRICT",
       ROUND(CAST(MAX(h."SubsidyAmt") AS NUMERIC), 2)    AS horticulture_subsidy,
       COUNT(*)                                          AS input_subsidy_transactions,
       STRING_AGG(DISTINCT a."cropname", ', ')           AS crops,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(MAX(h."SubsidyAmt") + SUM(a."subsidyamount") AS NUMERIC), 2) AS combined,
       MAX(h."Year_Of_Subsidy")                          AS "Year_Of_Subsidy",
       MAX(a."cropyear")                                 AS "cropyear"
FROM horticulture_apmip h
JOIN agriculture a ON a."aadharno" = h."EXTN_AADHARNO"
WHERE h."Year_Of_Subsidy" = a."cropyear"
  AND a."cropyear" = ?
GROUP BY h."EXTN_AADHARNO", h."Farmer_Name", h."DISTRICT"
ORDER BY combined DESC;
""",
        "param_slots": [
            {"name": 'crop_year', "entity_type": 'crop_year', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Convergence & overlap',
        "datasets": 'Horticulture_APMIP + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Double subsidy in one year', 'Horticulture and agriculture overlap'],
        "notes": "Legitimate in most cases, but the combined per-acre support is worth knowing before sanctioning a third. One row per farmer: horticulture is one row per Aadhaar, agriculture is transactional and is summed.",
        "expected_empty_on_demo": False,
    },

    "Q124": {
        "abstract_question": 'Show me everything we hold on {aadhaar}, across every department.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PM-KISAN' AS source, "name" AS farmer, "district", "village",
       CAST("area_hectares" AS TEXT) || ' ha' AS land, "ekyc_status" AS status,
       CAST("last_amount_credited" AS TEXT) AS amount
FROM pm_kisan WHERE "aadhaar_no" = ?
UNION ALL
SELECT 'Agriculture', "farmername", CAST("dcode" AS TEXT), CAST("cr_vcode" AS TEXT),
       "cropname", "cropstatus", CAST("subsidyamount" AS TEXT)
FROM agriculture WHERE "aadharno" = ?
UNION ALL
SELECT 'Horticulture_APMIP', "Farmer_Name", "DISTRICT", "Village_Name",
       CAST("EXTENT" AS TEXT) || ' ac', "Status", CAST("SubsidyAmt" AS TEXT)
FROM horticulture_apmip WHERE "EXTN_AADHARNO" = ?
UNION ALL
SELECT 'Fisheries', "farmer_name", "district", "village",
       CAST("EXTENT" AS TEXT) || ' ac', "payment_status", CAST("amount_paid" AS TEXT)
FROM fisheries WHERE "aadhar_no" = ?
UNION ALL
SELECT 'Sericulture', "Farmer_Name", CAST("DIST_CODE" AS TEXT), "panchayat_name",
       CAST("Cocoon_Qty" AS TEXT) || ' kg', "Transaction_Status", CAST("Net_Incentive" AS TEXT)
FROM sericulture WHERE "aadhaar_no" = ?
UNION ALL
SELECT 'MARKFED', "FARMER_NAME", "DIST_NAME", "FARMER_VILLAGE",
       CAST("AREA_IN_ACRES" AS TEXT) || ' ac', "PAYMENT_STATUS", CAST("AMOUNT_PAID" AS TEXT)
FROM markfed WHERE "AADHAAR_NO" = ?
UNION ALL
SELECT 'RySS', "FarmerName", "district", "Village_name",
       CAST("ACREAGE" AS TEXT) || ' ac', "farmerStatus", CAST("Amount" AS TEXT)
FROM ryss WHERE "Aadhar_no" = ?;
""",
        "param_slots": [
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 1},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 2},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 3},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 4},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 5},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 6},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 7},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Convergence & overlap',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Farmer 360 profile', 'Full record for one Aadhaar'],
        "notes": 'The single most important query for a grievance desk. Parameterise on Aadhaar, or resolve a name to an Aadhaar first.',
        "expected_empty_on_demo": False,
    },

    "Q125": {
        "abstract_question": 'Which schemes is {farmer_name} of {village} enrolled in?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH me AS (
  SELECT "aadhaar_no", "name", "district", "village"
  FROM pm_kisan
  WHERE "aadhaar_no" = ?
    AND UPPER(TRIM("village")) = UPPER(TRIM(?))
)
SELECT me."name", me."district", me."village",
       'Yes' AS pm_kisan,
       CASE WHEN EXISTS (SELECT 1 FROM agriculture        WHERE "aadharno"      = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS agriculture,
       CASE WHEN EXISTS (SELECT 1 FROM horticulture_apmip WHERE "EXTN_AADHARNO" = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS horticulture,
       CASE WHEN EXISTS (SELECT 1 FROM fisheries          WHERE "aadhar_no"     = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS fisheries,
       CASE WHEN EXISTS (SELECT 1 FROM sericulture        WHERE "aadhaar_no"    = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS sericulture,
       CASE WHEN EXISTS (SELECT 1 FROM markfed            WHERE "AADHAAR_NO"    = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS markfed,
       CASE WHEN EXISTS (SELECT 1 FROM ryss               WHERE "Aadhar_no"     = me."aadhaar_no") THEN 'Yes' ELSE 'No' END AS ryss
FROM me;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
            {"name": 'village', "entity_type": 'village', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Look up a farmer by name', 'Find a farmer without their Aadhaar'],
        "notes": 'Name-based lookup is unavoidable at the counter, so the router resolves the name to one Aadhaar and binds that; the village stays as a second filter, which is honest about what was asked and returns nothing if the two disagree. The village never disambiguated on its own — it narrows the roster but two people sharing a name can share a village.',
        "expected_empty_on_demo": False,
    },

    "S01": {
        "abstract_question": 'Which PM-KISAN farmers are not in {scheme}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."mobile_no"
FROM pm_kisan p
WHERE p."aadhaar_no" NOT IN (SELECT aadhaar FROM sch WHERE scheme = ? AND aadhaar IS NOT NULL)
ORDER BY p."district", p."name";
""",
        "param_slots": [
            {"name": 'scheme', "entity_type": 'scheme', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Farmers missing from one scheme', 'Who has not been reached by this programme',
                        'Are all PM-KISAN farmers present in this scheme',
                        'Which roster farmers do not appear in this scheme'],
        "notes": 'Scheme is a real slot: valid values are Agriculture, Horticulture, Fisheries, Sericulture, MARKFED, RySS.',
        "expected_empty_on_demo": False,
    },

    "S02": {
        "abstract_question": 'Which farmers are in {scheme} but not in {scheme_2}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar,
       COALESCE(p."name", '(not in PM-KISAN)') AS farmer_name,
       p."district", p."sub_district"
FROM sch s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s.aadhaar
WHERE s.scheme = ?
  AND s.aadhaar NOT IN (SELECT aadhaar FROM sch WHERE scheme = ? AND aadhaar IS NOT NULL)
ORDER BY p."district";
""",
        "param_slots": [
            {"name": 'scheme', "entity_type": 'scheme', "position": 1},
            {"name": 'scheme_2', "entity_type": 'scheme_2', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['One scheme but not another', 'Cross-scheme gap list'],
        "notes": 'Both slots take the same vocabulary. Useful for planning joint outreach between two departments.',
        # Was True only because scheme and scheme_2 shared a demo value, making
        # this "in X but not in X" — trivially empty and no test of the query.
        # With scheme_2's demo fixed to Fisheries the template returns rows.
        "expected_empty_on_demo": False,
    },

    "S04": {
        "abstract_question": 'Rank farmers by the number of schemes they are enrolled in.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar,
       COALESCE(p."name", '(not in PM-KISAN)') AS farmer_name,
       p."district", p."category",
       COUNT(DISTINCT s.scheme)        AS schemes,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM sch s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s.aadhaar
GROUP BY s.aadhaar, p."name", p."district", p."category"
ORDER BY schemes DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Scheme-count league table', 'Who touches the most programmes'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "S07": {
        "abstract_question": 'Which farmers are registered in {scheme}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar,
       COALESCE(p."name", '(not in PM-KISAN)') AS farmer_name,
       p."district", p."sub_district", p."category", p."gender"
FROM sch s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s.aadhaar
WHERE s.scheme = ?
ORDER BY p."district", farmer_name;
""",
        "param_slots": [
            {"name": 'scheme', "entity_type": 'scheme', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Membership list for one scheme', 'Who is enrolled in this programme'],
        "notes": "One template covers all six membership lists. Farmers absent from PM-KISAN show as '(not in PM-KISAN)' rather than being dropped.",
        "expected_empty_on_demo": False,
    },

    # ── Coverage & scale ──────────────────────────────────────────────────
    "G01-D": {
        "abstract_question": 'How many PM-KISAN beneficiaries are there in each mandal of {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "sub_district" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
WHERE "district" = ?
GROUP BY "sub_district"
ORDER BY beneficiaries DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Beneficiary count by area', 'Where are our farmers?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G01-M": {
        "abstract_question": 'How many PM-KISAN beneficiaries are there in each village of {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "village" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY "village"
ORDER BY beneficiaries DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Beneficiary count by area', 'Where are our farmers?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G02-D": {
        "abstract_question": 'Which mandals in {district} district have the biggest eKYC backlog?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "sub_district" AS geography,
       COUNT(*) AS beneficiaries,
       SUM(CASE WHEN "ekyc_status" = 'Pending' THEN 1 ELSE 0 END) AS ekyc_pending,
       SUM(CASE WHEN "beneficiary_status" <> 'Included' THEN 1 ELSE 0 END) AS not_included,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc_complete
FROM pm_kisan
WHERE "district" = ?
GROUP BY "sub_district"
ORDER BY ekyc_pending DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['eKYC backlog by area', 'Status pendency dashboard'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G02-M": {
        "abstract_question": 'What is the eKYC position village by village in {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "village" AS geography,
       COUNT(*) AS beneficiaries,
       SUM(CASE WHEN "ekyc_status" = 'Pending' THEN 1 ELSE 0 END) AS ekyc_pending,
       SUM(CASE WHEN "beneficiary_status" <> 'Included' THEN 1 ELSE 0 END) AS not_included,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc_complete
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY "village"
ORDER BY ekyc_pending DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['eKYC backlog by area', 'Status pendency dashboard'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G03-D": {
        "abstract_question": 'What is the total cultivable area in {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS total_hectares,
       ROUND(CAST(SUM("area_hectares") * 2.47105 AS NUMERIC), 2) AS total_acres,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
WHERE "district" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Total land under the scheme', 'Area covered'],
        "notes": 'PM-KISAN stores hectares; the acre column is converted at 1 ha = 2.47105 acres.',
        "expected_empty_on_demo": False,
    },

    "G03-M": {
        "abstract_question": 'What is the total cultivable area in {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS total_hectares,
       ROUND(CAST(SUM("area_hectares") * 2.47105 AS NUMERIC), 2) AS total_acres,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Total land under the scheme', 'Area covered'],
        "notes": 'PM-KISAN stores hectares; the acre column is converted at 1 ha = 2.47105 acres.',
        "expected_empty_on_demo": False,
    },

    "G10-D": {
        "abstract_question": 'How much input subsidy went to each mandal of {district} district?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."sub_district" AS geography,
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(AVG(a."subsidyamount") AS NUMERIC), 2) AS avg_subsidy
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
GROUP BY p."sub_district"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Coverage & scale',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Seed subsidy by area', 'Input support disbursed'],
        "notes": 'Agriculture stores district and mandal as codes only, so geography is resolved through the PM-KISAN spine. Farmers not on the roster drop out of this query — see the off-roster checks for that population.',
        "expected_empty_on_demo": False,
    },

    "G10-M": {
        "abstract_question": 'How much input subsidy went to each village of {mandal} mandal?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."village" AS geography,
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(AVG(a."subsidyamount") AS NUMERIC), 2) AS avg_subsidy
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."village"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Coverage & scale',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Seed subsidy by area', 'Input support disbursed'],
        "notes": 'Agriculture stores district and mandal as codes only, so geography is resolved through the PM-KISAN spine. Farmers not on the roster drop out of this query — see the off-roster checks for that population.',
        "expected_empty_on_demo": False,
    },

    "G21-D": {
        "abstract_question": 'What is the micro-irrigation coverage in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Mandal" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres_covered,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_sanctioned
FROM horticulture_apmip
WHERE "DISTRICT" = ?
GROUP BY "Mandal"
ORDER BY subsidy_sanctioned DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Coverage & scale',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'District',
        "paraphrases": ['APMIP coverage by area', 'Micro-irrigation footprint'],
        "notes": 'Horticulture dates are Excel serial numbers in the source, so the date filter is numeric. Normalise these at ingestion.',
        "expected_empty_on_demo": False,
    },

    "G21-M": {
        "abstract_question": 'What is the micro-irrigation coverage in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Village_Name" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres_covered,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_sanctioned
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "Mandal" = ?
GROUP BY "Village_Name"
ORDER BY subsidy_sanctioned DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Coverage & scale',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'Mandal',
        "paraphrases": ['APMIP coverage by area', 'Micro-irrigation footprint'],
        "notes": 'Horticulture dates are Excel serial numbers in the source, so the date filter is numeric. Normalise these at ingestion.',
        "expected_empty_on_demo": False,
    },

    "G25-D": {
        "abstract_question": 'How many fishers are registered in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "mandal" AS geography,
       COUNT(DISTINCT "aadhar_no") AS registrants,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent_acres
FROM fisheries
WHERE "district" = ?
GROUP BY "mandal"
ORDER BY registrants DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Coverage & scale',
        "datasets": 'Fisheries',
        "geo_level": 'District',
        "paraphrases": ['Fisheries coverage by area', 'Registrations and payouts'],
        "notes": 'Fisheries registration dates are Excel serial numbers in the source; the date filter is numeric.',
        "expected_empty_on_demo": False,
    },

    "G25-M": {
        "abstract_question": 'How many fishers are registered in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "village" AS geography,
       COUNT(DISTINCT "aadhar_no") AS registrants,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent_acres
FROM fisheries
WHERE "district" = ?
  AND "mandal" = ?
GROUP BY "village"
ORDER BY registrants DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Coverage & scale',
        "datasets": 'Fisheries',
        "geo_level": 'Mandal',
        "paraphrases": ['Fisheries coverage by area', 'Registrations and payouts'],
        "notes": 'Fisheries registration dates are Excel serial numbers in the source; the date filter is numeric.',
        "expected_empty_on_demo": True,
    },

    "G28-D": {
        "abstract_question": 'How many natural farming members are in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "Mandal" AS geography,
       COUNT(DISTINCT "Aadhar_no") AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "district" = ?
GROUP BY "Mandal"
ORDER BY total_acreage DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Coverage & scale',
        "datasets": 'RySS',
        "geo_level": 'District',
        "paraphrases": ['APCNF coverage by area', 'Natural farming membership'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G28-M": {
        "abstract_question": 'How many natural farming members are in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "Village_name" AS geography,
       COUNT(DISTINCT "Aadhar_no") AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "district" = ?
  AND "Mandal" = ?
GROUP BY "Village_name"
ORDER BY total_acreage DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Coverage & scale',
        "datasets": 'RySS',
        "geo_level": 'Mandal',
        "paraphrases": ['APCNF coverage by area', 'Natural farming membership'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "R01": {
        "abstract_question": 'Who are the {top_n} largest landholders in PM-KISAN?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "category",
       "area_hectares",
       ROUND(CAST("area_hectares" * 2.47105 AS NUMERIC), 2) AS acres
FROM pm_kisan
ORDER BY "area_hectares" DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Largest landholdings', 'Biggest farms on the roster'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    # ── Crop & inputs ─────────────────────────────────────────────────────
    "F02": {
        "abstract_question": 'What input subsidy did {farmer_name} take, for which crop and season?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername", "pattadarname", "cropname", "varietyname", "season", "cropyear",
       "cropstatus", "surveyno", "khatano",
       ROUND(CAST("subsidyamount" AS NUMERIC), 2)    AS subsidy_amount,
       ROUND(CAST("nonsubsidyamount" AS NUMERIC), 2) AS farmer_contribution,
       ROUND(CAST("seed_production" AS NUMERIC), 2)  AS seed_quantity
FROM agriculture
WHERE "aadharno" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ["One farmer's input subsidy record", 'Crop and season for a farmer'],
        "notes": "Keyed on the Aadhaar the name resolved to. Filtering agriculture.farmername returned every namesake's crop rows mixed into one answer.",
        "expected_empty_on_demo": False,
    },

    "G11-D": {
        "abstract_question": 'What is the crop mix in {district} district?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropname", a."season",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."seed_production") AS NUMERIC), 2) AS seed_quantity
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
GROUP BY a."cropname", a."season"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Crop-wise subsidy', 'What are we subsidising?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G11-M": {
        "abstract_question": 'What is the crop mix in {mandal} mandal?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropname", a."season",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."seed_production") AS NUMERIC), 2) AS seed_quantity
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY a."cropname", a."season"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Crop-wise subsidy', 'What are we subsidising?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G12-D": {
        "abstract_question": 'How many crop registrations are pending in {district} district?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropstatus", a."cropname",
       COUNT(*) AS records,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS subsidy_held_up
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropstatus" <> 'Approved'
  AND p."district" = ?
GROUP BY a."cropstatus", a."cropname"
ORDER BY records DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['eCrop approval backlog', 'Pending crop registrations'],
        "notes": 'Valid statuses in this table are only Approved, Pending and Under Review — there is no Damaged status.',
        "expected_empty_on_demo": False,
    },

    "G12-M": {
        "abstract_question": 'How many crop registrations are pending in {mandal} mandal?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropstatus", a."cropname",
       COUNT(*) AS records,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS subsidy_held_up
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropstatus" <> 'Approved'
  AND p."district" = ?
  AND p."sub_district" = ?
GROUP BY a."cropstatus", a."cropname"
ORDER BY records DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['eCrop approval backlog', 'Pending crop registrations'],
        "notes": 'Valid statuses in this table are only Approved, Pending and Under Review — there is no Damaged status.',
        "expected_empty_on_demo": True,
    },

    "Q098": {
        "abstract_question": 'For {crop}, which farmers took input subsidy and also sold to MARKFED?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH ag AS (
  SELECT "aadharno" AS aadhaar,
         MIN("farmername")                               AS farmername,
         COUNT(*)                                        AS subsidy_transactions,
         ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS input_subsidy
  FROM agriculture
  WHERE UPPER(TRIM("cropname")) = UPPER(TRIM(?))
  GROUP BY "aadharno"
),
mk AS (
  SELECT "AADHAAR_NO" AS aadhaar,
         MIN("DIST_NAME")                               AS dist_name,
         COUNT(*)                                       AS deliveries,
         ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity_sold,
         ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS procurement_payment
  FROM markfed
  WHERE UPPER(TRIM("CROP_NAME")) = UPPER(TRIM(?))
  GROUP BY "AADHAAR_NO"
)
SELECT ag.farmername, ag.aadhaar AS aadharno, mk.dist_name AS "DIST_NAME",
       ag.subsidy_transactions, ag.input_subsidy,
       mk.deliveries, mk.quantity_sold, mk.procurement_payment
FROM ag
JOIN mk ON mk.aadhaar = ag.aadhaar
ORDER BY mk.procurement_payment DESC;
""",
        "param_slots": [
            {"name": 'crop', "entity_type": 'crop', "position": 1},
            {"name": 'crop', "entity_type": 'crop', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Paddy full-cycle farmers', 'Input-to-procurement chain for one crop'],
        "notes": "Traces the full input-to-market cycle for a single crop. Parameterise the crop name. Both sides are transactional, so each is pre-aggregated to one row per Aadhaar before the join — joining raw would multiply registrations by deliveries.",
        "expected_empty_on_demo": False,
        # A user asked "for which crop?" may reasonably answer "all crops" —
        # Q118's Agriculture×MARKFED row IS that crop-less answer.
        "scope_alternative": 'Q118',
    },

    "R02": {
        "abstract_question": 'Who received the {top_n} highest input subsidies?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername", "cropname", "season", "cropyear",
       ROUND(CAST("subsidyamount" AS NUMERIC), 2) AS subsidy_amount
FROM agriculture
ORDER BY "subsidyamount" DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Largest subsidy recipients', 'Top input subsidy payments'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "V01": {
        "abstract_question": 'Which farmers took input subsidy in the {season} season?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername",
       STRING_AGG(DISTINCT "cropname", ', ')                  AS crops,
       STRING_AGG(DISTINCT "varietyname", ', ')               AS varieties,
       MIN("season")                                          AS season,
       STRING_AGG(DISTINCT CAST("cropyear" AS VARCHAR), ', ') AS crop_years,
       COUNT(*)                                               AS registrations,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2)        AS subsidy_amount
FROM agriculture
WHERE UPPER(TRIM("season")) = UPPER(TRIM(?))
GROUP BY "aadharno", "farmername"
ORDER BY subsidy_amount DESC;
""",
        "param_slots": [
            {"name": 'season', "entity_type": 'season', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Season-filtered subsidy list', 'Farmers who drew subsidy in one season'],
        "notes": "One row per farmer (grouped on Aadhaar). V02 is the sibling that deliberately answers at crop-registration grain.",
        "expected_empty_on_demo": False,
    },

    "V02": {
        "abstract_question": 'Which crop registrations are marked {crop_status}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername", "cropname", "season", "cropyear", "cropstatus",
       ROUND(CAST("subsidyamount" AS NUMERIC), 2) AS subsidy_amount
FROM agriculture
WHERE UPPER(TRIM("cropstatus")) = UPPER(TRIM(?))
ORDER BY "farmername";
""",
        "param_slots": [
            {"name": 'crop_status', "entity_type": 'crop_status', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Crop registrations by status', 'Registrations in a given state'],
        "notes": "IMPORTANT: the only values this column takes are Approved, Pending and Under Review. There is no Damaged status in this schema. A query for 'Damaged' correctly returns nothing, and the bot must say the status does not exist rather than report zero damaged crops — those are different answers.",
        "expected_empty_on_demo": False,
    },

    "V03": {
        "abstract_question": 'Which farmers grow {crop}, and what subsidy did they receive?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername",
       MIN("cropname")                                        AS cropname,
       STRING_AGG(DISTINCT "varietyname", ', ')               AS varieties,
       STRING_AGG(DISTINCT "season", ', ')                    AS seasons,
       STRING_AGG(DISTINCT CAST("cropyear" AS VARCHAR), ', ') AS crop_years,
       COUNT(*)                                               AS registrations,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2)        AS subsidy_amount,
       ROUND(CAST(SUM("seed_production") AS NUMERIC), 2)      AS seed_quantity
FROM agriculture
WHERE UPPER(TRIM("cropname")) = UPPER(TRIM(?))
GROUP BY "aadharno", "farmername"
ORDER BY subsidy_amount DESC;
""",
        "param_slots": [
            {"name": 'crop', "entity_type": 'crop', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Crop-filtered farmer list', 'Who grows this crop'],
        "notes": "One row per farmer (grouped on Aadhaar), with the varieties, seasons and years the farmer registered carried as aggregates. V02 answers at crop-registration grain.",
        "expected_empty_on_demo": False,
    },

    "V08": {
        "abstract_question": 'What crops are grown by farmers whose eKYC status is {ekyc_status}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT a."cropname", a."season",
       COUNT(DISTINCT a."aadharno")                      AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS subsidy_at_risk
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE UPPER(TRIM(p."ekyc_status")) = UPPER(TRIM(?))
GROUP BY a."cropname", a."season"
ORDER BY subsidy_at_risk DESC;
""",
        "param_slots": [
            {"name": 'ekyc_status', "entity_type": 'ekyc_status', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Crops of unverified farmers', 'Crop mix by verification status'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    # ── Data quality & identity ───────────────────────────────────────────
    "F10": {
        "abstract_question": 'Is the mobile number for {farmer_name} consistent across all datasets?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH nums AS (
  SELECT "aadhaar_no" AS aadhaar, 'PM-KISAN' AS src, CAST("mobile_no" AS TEXT) AS mobile FROM pm_kisan
  UNION SELECT "aadharno",   'Agriculture', CAST("mobileno" AS TEXT)  FROM agriculture
  UNION SELECT "aadhar_no",  'Fisheries',   CAST("mobile_no" AS TEXT) FROM fisheries
  UNION SELECT "AADHAAR_NO", 'MARKFED',     CAST("MOBILE_NO" AS TEXT) FROM markfed
)
SELECT p."name", p."village", n.src, n.mobile
FROM pm_kisan p
JOIN nums n ON n.aadhaar = p."aadhaar_no"
WHERE p."aadhaar_no" = ?
ORDER BY n.src;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Agriculture + Fisheries + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Mobile consistency for one farmer', 'Which number is on file where'],
        "notes": 'One row per distinct number held. More than one row means the departments disagree. Keyed on the Aadhaar the name resolved to: filtering by name pulled in every namesake and manufactured exactly the disagreement this template is asked to detect.',
        "expected_empty_on_demo": False,
    },

    "F11": {
        "abstract_question": 'Is the landholding recorded for {farmer_name} consistent across datasets?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district",
       p."area_hectares"                                        AS pmkisan_hectares,
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2)   AS pmkisan_converted_acres,
       ROUND(CAST(m."AREA_IN_ACRES" AS NUMERIC), 2)             AS markfed_acres,
       ROUND(CAST(s."extent" AS NUMERIC), 2)                    AS survey_acres,
       ROUND(CAST(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105 AS NUMERIC), 2) AS markfed_minus_pmkisan
FROM pm_kisan p
LEFT JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
LEFT JOIN survey_land_records s
       ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
      AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
WHERE p."aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Land reconciliation for one farmer', 'Why does the area differ between systems', "This farmer's land differs between PM-KISAN and MARKFED - is it a discrepancy", "Farmer's area shows one figure in PM-KISAN and another in MARKFED", 'Do the hectares and acres recorded for this farmer agree'],
        "notes": 'ANSWERS THE UNIT TRAP DIRECTLY. PM-KISAN is hectares, MARKFED and survey records are acres. A farmer showing 1.30 in PM-KISAN and 3.20 in MARKFED is consistent: 1.30 ha x 2.47105 = 3.21 acres. The converted column makes that visible instead of leaving the officer to spot it. Keyed on the Aadhaar the name resolved to — a name filter returned one row per namesake and every one of them looked like a landholding discrepancy. The survey join still matches on name AND village because survey_land_records holds no Aadhaar, but it is now scoped to the resolved person\'s own roster row.',
        "expected_empty_on_demo": False,
    },

    "G09-D": {
        "abstract_question": 'Give me a completeness scorecard for each mandal of {district} district.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "sub_district" AS geography,
       COUNT(*) AS records,
       ROUND(CAST(100.0 * SUM(CASE WHEN "mobile_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_mobile,
       ROUND(CAST(100.0 * SUM(CASE WHEN "bank_account_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_bank,
       ROUND(CAST(100.0 * SUM(CASE WHEN "khata_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_khata,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc
FROM pm_kisan
WHERE "district" = ?
GROUP BY "sub_district"
ORDER BY pct_ekyc;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Data quality dashboard', 'Field completeness by area'],
        "notes": 'Run monthly. A falling percentage is usually a data-entry process problem, not a farmer problem.',
        "expected_empty_on_demo": False,
    },

    "G09-M": {
        "abstract_question": 'Give me a completeness scorecard for each village of {mandal} mandal.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "village" AS geography,
       COUNT(*) AS records,
       ROUND(CAST(100.0 * SUM(CASE WHEN "mobile_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_mobile,
       ROUND(CAST(100.0 * SUM(CASE WHEN "bank_account_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_bank,
       ROUND(CAST(100.0 * SUM(CASE WHEN "khata_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_khata,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY "village"
ORDER BY pct_ekyc;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Data quality dashboard', 'Field completeness by area'],
        "notes": 'Run monthly. A falling percentage is usually a data-entry process problem, not a farmer problem.',
        "expected_empty_on_demo": False,
    },

    "G41-D": {
        "abstract_question": 'How many farmers in {district} district have conflicting caste records?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH cats AS (
  SELECT "aadhaar_no" AS aadhaar, UPPER(TRIM("category")) AS cat FROM pm_kisan
  UNION SELECT "aadharno",      UPPER(TRIM("social_status"))   FROM agriculture
  UNION SELECT "EXTN_AADHARNO", UPPER(TRIM("Category"))        FROM horticulture_apmip
  UNION SELECT "aadhar_no",     UPPER(TRIM("social_category")) FROM fisheries
  UNION SELECT "AADHAAR_NO",    UPPER(TRIM("CASTE"))           FROM markfed
  UNION SELECT "Aadhar_no",     UPPER(TRIM("Social_Category")) FROM ryss
)
SELECT c.aadhaar, p."name", p."district", p."sub_district",
       COUNT(DISTINCT c.cat) AS distinct_categories,
       GROUP_CONCAT(DISTINCT c.cat) AS values_found
FROM cats c
JOIN pm_kisan p ON p."aadhaar_no" = c.aadhaar
WHERE c.cat IS NOT NULL
  AND p."district" = ?
GROUP BY c.aadhaar, p."name", p."district", p."sub_district"
HAVING COUNT(DISTINCT c.cat) > 1
ORDER BY distinct_categories DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + 5 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Caste discrepancies across datasets', 'Conflicting category records'],
        "notes": 'Directly affects reservation-linked targeting. Each conflict needs one authoritative source declared.',
        "expected_empty_on_demo": True,
    },

    "G41-M": {
        "abstract_question": 'How many farmers in {mandal} mandal have conflicting caste records?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH cats AS (
  SELECT "aadhaar_no" AS aadhaar, UPPER(TRIM("category")) AS cat FROM pm_kisan
  UNION SELECT "aadharno",      UPPER(TRIM("social_status"))   FROM agriculture
  UNION SELECT "EXTN_AADHARNO", UPPER(TRIM("Category"))        FROM horticulture_apmip
  UNION SELECT "aadhar_no",     UPPER(TRIM("social_category")) FROM fisheries
  UNION SELECT "AADHAAR_NO",    UPPER(TRIM("CASTE"))           FROM markfed
  UNION SELECT "Aadhar_no",     UPPER(TRIM("Social_Category")) FROM ryss
)
SELECT c.aadhaar, p."name", p."district", p."sub_district",
       COUNT(DISTINCT c.cat) AS distinct_categories,
       GROUP_CONCAT(DISTINCT c.cat) AS values_found
FROM cats c
JOIN pm_kisan p ON p."aadhaar_no" = c.aadhaar
WHERE c.cat IS NOT NULL
  AND p."district" = ?
  AND p."sub_district" = ?
GROUP BY c.aadhaar, p."name", p."district", p."sub_district"
HAVING COUNT(DISTINCT c.cat) > 1
ORDER BY distinct_categories DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + 5 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Caste discrepancies across datasets', 'Conflicting category records'],
        "notes": 'Directly affects reservation-linked targeting. Each conflict needs one authoritative source declared.',
        "expected_empty_on_demo": True,
    },

    "G42-D": {
        "abstract_question": 'Which farmers in {district} district show a land discrepancy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district",
       p."area_hectares" AS pmkisan_ha,
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS pmkisan_converted_acres,
       m."AREA_IN_ACRES" AS markfed_acres,
       ROUND(CAST(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105 AS NUMERIC), 2) AS difference_acres
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105)
      > 0.05 * (p."area_hectares" * 2.47105)
  AND p."district" = ?
ORDER BY ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105) DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Land amount discrepancies', 'Declared area conflicts after unit conversion'],
        "notes": 'CRITICAL: PM-KISAN is hectares, MARKFED is acres. Convert before comparing or every record looks like a discrepancy. Tolerance is 5%.',
        "expected_empty_on_demo": True,
    },

    "G42-M": {
        "abstract_question": 'Which farmers in {mandal} mandal show a land discrepancy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district",
       p."area_hectares" AS pmkisan_ha,
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS pmkisan_converted_acres,
       m."AREA_IN_ACRES" AS markfed_acres,
       ROUND(CAST(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105 AS NUMERIC), 2) AS difference_acres
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105)
      > 0.05 * (p."area_hectares" * 2.47105)
  AND p."district" = ?
  AND p."sub_district" = ?
ORDER BY ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105) DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Land amount discrepancies', 'Declared area conflicts after unit conversion'],
        "notes": 'CRITICAL: PM-KISAN is hectares, MARKFED is acres. Convert before comparing or every record looks like a discrepancy. Tolerance is 5%.',
        "expected_empty_on_demo": True,
    },

    "Q067": {
        "abstract_question": 'Are there any malformed Aadhaar numbers in our systems?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH a AS (
  SELECT 'PM-KISAN' AS src, CAST("aadhaar_no" AS TEXT) AS aadhaar FROM pm_kisan
  UNION ALL SELECT 'Agriculture',  CAST("aadharno" AS TEXT)      FROM agriculture
  UNION ALL SELECT 'Horticulture', CAST("EXTN_AADHARNO" AS TEXT) FROM horticulture_apmip
  UNION ALL SELECT 'Fisheries',    CAST("aadhar_no" AS TEXT)     FROM fisheries
  UNION ALL SELECT 'Sericulture',  CAST("aadhaar_no" AS TEXT)    FROM sericulture
  UNION ALL SELECT 'MARKFED',      CAST("AADHAAR_NO" AS TEXT)    FROM markfed
  UNION ALL SELECT 'RySS',         CAST("Aadhar_no" AS TEXT)     FROM ryss
)
SELECT src,
       COUNT(*) AS total_records,
       SUM(CASE WHEN aadhaar IS NULL THEN 1 ELSE 0 END)         AS null_aadhaar,
       SUM(CASE WHEN LENGTH(TRIM(aadhaar)) <> ? THEN 1 ELSE 0 END) AS wrong_length
FROM a
GROUP BY src
ORDER BY wrong_length DESC, null_aadhaar DESC;
""",
        "param_slots": [
            {"name": 'aadhaar_length', "entity_type": 'aadhaar_length', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'All 7 Aadhaar-bearing datasets',
        "geo_level": 'State',
        "paraphrases": ['Invalid Aadhaar format check', 'Aadhaar numbers that are not 12 digits'],
        "notes": 'Run this before any cross-dataset join: a malformed key silently drops the record from every match.',
        "expected_empty_on_demo": False,
    },

    "V05": {
        "abstract_question": 'Which farmers have eKYC status {ekyc_status}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "ekyc_status",
       "beneficiary_status", "mobile_no"
FROM pm_kisan
WHERE UPPER(TRIM("ekyc_status")) = UPPER(TRIM(?))
ORDER BY "district", "sub_district";
""",
        "param_slots": [
            {"name": 'ekyc_status', "entity_type": 'ekyc_status', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['eKYC-filtered farmer list', 'Farmers at a given verification stage'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "V06": {
        "abstract_question": 'Whose beneficiary status is {beneficiary_status}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "beneficiary_status",
       "ekyc_status", "area_hectares", "last_installment_no", "mobile_no"
FROM pm_kisan
WHERE UPPER(TRIM("beneficiary_status")) = UPPER(TRIM(?))
ORDER BY "district";
""",
        "param_slots": [
            {"name": 'beneficiary_status', "entity_type": 'beneficiary_status', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Beneficiary-status filtered list', 'Farmers at a given roster status'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    # ── Exclusion & leakage ───────────────────────────────────────────────
    "G37-D": {
        "abstract_question": 'Which farmers in {district} district have eKYC pending yet receive benefits?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status",
       COUNT(DISTINCT s.scheme) AS schemes_receiving,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
WHERE p."ekyc_status" = 'Pending'
  AND p."district" = ?
GROUP BY p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status"
ORDER BY schemes_receiving DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Unverified farmers receiving money', 'Verification gap'],
        "notes": 'Money moving to identities the system has not confirmed.',
        "expected_empty_on_demo": True,
    },

    "G37-M": {
        "abstract_question": 'Which farmers in {mandal} mandal have eKYC pending yet receive benefits?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status",
       COUNT(DISTINCT s.scheme) AS schemes_receiving,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
WHERE p."ekyc_status" = 'Pending'
  AND p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status"
ORDER BY schemes_receiving DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Unverified farmers receiving money', 'Verification gap'],
        "notes": 'Money moving to identities the system has not confirmed.',
        "expected_empty_on_demo": True,
    },

    "G38-D": {
        "abstract_question": 'Which farmers in {district} district have benefits but no land record?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
WHERE NOT EXISTS (
        SELECT 1 FROM survey_land_records s
        WHERE UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
          AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village")))
  AND p."district" = ?
GROUP BY p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Survey_Land_Records + Agriculture',
        "geo_level": 'District',
        "paraphrases": ['Benefits without land records', 'Unverifiable entitlements'],
        "notes": 'Land-linked subsidies with no revenue record behind them are the highest-risk category in the portfolio.',
        "expected_empty_on_demo": True,
    },

    "G38-M": {
        "abstract_question": 'Which farmers in {mandal} mandal have benefits but no land record?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
WHERE NOT EXISTS (
        SELECT 1 FROM survey_land_records s
        WHERE UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
          AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village")))
  AND p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Survey_Land_Records + Agriculture',
        "geo_level": 'Mandal',
        "paraphrases": ['Benefits without land records', 'Unverifiable entitlements'],
        "notes": 'Land-linked subsidies with no revenue record behind them are the highest-risk category in the portfolio.',
        "expected_empty_on_demo": True,
    },

    "G39-D": {
        "abstract_question": 'Give me a mandal scorecard for {district} district.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."sub_district" AS geography,
       COUNT(DISTINCT p."aadhaar_no") AS farmers,
       ROUND(CAST(SUM(p."area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(SUM(m."AMOUNT_PAID"), 0) AS NUMERIC), 2) AS procurement_value
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno"   = p."aadhaar_no"
LEFT JOIN markfed m     ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE p."district" = ?
GROUP BY p."sub_district"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Area scorecard', 'One-page comparison across departments'],
        "notes": 'The standing review-meeting table. Each column comes from a different department, joined on the spine.',
        "expected_empty_on_demo": False,
    },

    "G39-M": {
        "abstract_question": 'Give me a village scorecard for {mandal} mandal.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."village" AS geography,
       COUNT(DISTINCT p."aadhaar_no") AS farmers,
       ROUND(CAST(SUM(p."area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(SUM(m."AMOUNT_PAID"), 0) AS NUMERIC), 2) AS procurement_value
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno"   = p."aadhaar_no"
LEFT JOIN markfed m     ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."village"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Area scorecard', 'One-page comparison across departments'],
        "notes": 'The standing review-meeting table. Each column comes from a different department, joined on the spine.',
        "expected_empty_on_demo": False,
    },

    "G44-D": {
        "abstract_question": 'Which large landholders in {district} district receive targeted subsidies?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."category", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(MAX(h."SubsidyAmt"), 0) AS NUMERIC), 2) AS horticulture_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
WHERE p."area_hectares" > 2
  AND p."district" = ?
GROUP BY p."name", p."district", p."sub_district", p."category", p."area_hectares"
HAVING COALESCE(SUM(a."subsidyamount"), 0) + COALESCE(MAX(h."SubsidyAmt"), 0) > 0
ORDER BY p."area_hectares" DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + Horticulture',
        "geo_level": 'District',
        "paraphrases": ['Large farmers in targeted schemes', 'Support flowing upward'],
        "notes": 'The 2 ha threshold is the common small-farmer ceiling; set it to whatever the scheme guidelines actually specify.',
        "expected_empty_on_demo": True,
    },

    "G44-M": {
        "abstract_question": 'Which large landholders in {mandal} mandal receive targeted subsidies?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."category", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(MAX(h."SubsidyAmt"), 0) AS NUMERIC), 2) AS horticulture_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
WHERE p."area_hectares" > 2
  AND p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."name", p."district", p."sub_district", p."category", p."area_hectares"
HAVING COALESCE(SUM(a."subsidyamount"), 0) + COALESCE(MAX(h."SubsidyAmt"), 0) > 0
ORDER BY p."area_hectares" DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + Horticulture',
        "geo_level": 'Mandal',
        "paraphrases": ['Large farmers in targeted schemes', 'Support flowing upward'],
        "notes": 'The 2 ha threshold is the common small-farmer ceiling; set it to whatever the scheme guidelines actually specify.',
        "expected_empty_on_demo": True,
    },

    "S03": {
        "abstract_question": 'Which Aadhaar numbers in {scheme} do not exist in PM-KISAN?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s.aadhaar, s.scheme
FROM sch s
WHERE s.scheme = ?
  AND s.aadhaar NOT IN (SELECT "aadhaar_no" FROM pm_kisan WHERE "aadhaar_no" IS NOT NULL)
ORDER BY s.aadhaar;
""",
        "param_slots": [
            {"name": 'scheme', "entity_type": 'scheme', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'All 6 AP schemes + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Off-roster beneficiaries in one scheme', 'Aadhaar absent from the master list'],
        "notes": 'Expect legitimate cases: fishers and tenants often hold no agricultural land and so never enter PM-KISAN. The point is to size and explain the set.',
        "expected_empty_on_demo": False,
    },

    # ── Geography & performance ───────────────────────────────────────────
    "G40-D": {
        "abstract_question": 'List every farmer in {district} district and what they have received.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."ekyc_status",
       ROUND(CAST(COALESCE(a."subsidyamount", 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(h."SubsidyAmt", 0) AS NUMERIC), 2) AS horticulture_subsidy,
       ROUND(CAST(COALESCE(m."AMOUNT_PAID", 0) AS NUMERIC), 2) AS procurement_payment
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
LEFT JOIN markfed m            ON m."AADHAAR_NO"    = p."aadhaar_no"
WHERE p."district" = ?
ORDER BY p."name";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Mandal AO / RBK',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + Agriculture + Horticulture + MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Beneficiary register', 'Everything happening in one area'],
        "notes": 'The RBK-level working list. At state scope this returns the full roster, so expect it to be used at mandal scope in practice.',
        "expected_empty_on_demo": False,
    },

    "G40-M": {
        "abstract_question": 'List every farmer in {mandal} mandal and what they have received.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."ekyc_status",
       ROUND(CAST(COALESCE(a."subsidyamount", 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(h."SubsidyAmt", 0) AS NUMERIC), 2) AS horticulture_subsidy,
       ROUND(CAST(COALESCE(m."AMOUNT_PAID", 0) AS NUMERIC), 2) AS procurement_payment
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
LEFT JOIN markfed m            ON m."AADHAAR_NO"    = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
ORDER BY p."name";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Mandal AO / RBK',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + Agriculture + Horticulture + MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Beneficiary register', 'Everything happening in one area'],
        "notes": 'The RBK-level working list. At state scope this returns the full roster, so expect it to be used at mandal scope in practice.',
        "expected_empty_on_demo": False,
    },

    "G43-D": {
        "abstract_question": 'What share of farmland is under natural farming in each mandal of {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."sub_district" AS geography,
       ROUND(CAST(SUM(p."area_hectares") * 2.47105 AS NUMERIC), 2) AS total_farmland_acres,
       ROUND(CAST(COALESCE(SUM(r."ACREAGE"), 0) AS NUMERIC), 2) AS natural_farming_acres,
       ROUND(CAST(100.0 * COALESCE(SUM(r."ACREAGE"), 0) / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 1) AS pct_under_nf
FROM pm_kisan p
LEFT JOIN ryss r ON r."Aadhar_no" = p."aadhaar_no"
WHERE p."district" = ?
GROUP BY p."sub_district"
ORDER BY pct_under_nf DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Geography & performance',
        "datasets": 'RySS + PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Natural farming penetration', 'APCNF share of farmland'],
        "notes": 'PM-KISAN area is converted from hectares to acres to match RySS. Shares near 100% in the demo data reflect the sample, not reality.',
        "expected_empty_on_demo": False,
    },

    "G43-M": {
        "abstract_question": 'What share of farmland is under natural farming in each village of {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."village" AS geography,
       ROUND(CAST(SUM(p."area_hectares") * 2.47105 AS NUMERIC), 2) AS total_farmland_acres,
       ROUND(CAST(COALESCE(SUM(r."ACREAGE"), 0) AS NUMERIC), 2) AS natural_farming_acres,
       ROUND(CAST(100.0 * COALESCE(SUM(r."ACREAGE"), 0) / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 1) AS pct_under_nf
FROM pm_kisan p
LEFT JOIN ryss r ON r."Aadhar_no" = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."village"
ORDER BY pct_under_nf DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Geography & performance',
        "datasets": 'RySS + PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Natural farming penetration', 'APCNF share of farmland'],
        "notes": 'PM-KISAN area is converted from hectares to acres to match RySS. Shares near 100% in the demo data reflect the sample, not reality.',
        "expected_empty_on_demo": False,
    },

    "M03": {
        "abstract_question": 'What is the district code for {district} in the agriculture data?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT DISTINCT a."dcode" AS district_code,
       p."district"               AS district_name,
       a."mcode"                  AS mandal_code,
       p."sub_district"           AS mandal_name
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
ORDER BY district_code, mandal_code;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Geography & performance',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['District code lookup', 'Resolve a district name to its dcode'],
        "notes": 'Derived from the data by joining through the spine. A proper district master would be better — this reflects only codes that appear alongside a rostered farmer.',
        "expected_empty_on_demo": False,
    },

    # ── Land & records ────────────────────────────────────────────────────
    "F08": {
        "abstract_question": 'What land records exist for {farmer_name} — khata, survey number, extent?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT s."pattadar_name", s."applicant_name", s."dist_name", s."mandal", s."village",
       s."khata_no", s."surveyno", s."category_title", s."current_status",
       ROUND(CAST(s."extent" AS NUMERIC), 2) AS extent_acres
FROM survey_land_records s
JOIN pm_kisan p
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
 AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
WHERE p."aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Grievance / Call centre',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ["One farmer's land record", 'Khata and survey number for a pattadar'],
        "notes": 'Survey records carry no Aadhaar, so the parcel cannot be keyed on one directly. It is reached through the resolved person\'s own roster row instead — pattadar name AND village — which is the same linkage F09 and F11 use. Matching on the name alone returned every namesake\'s land as though it were this farmer\'s.',
        "expected_empty_on_demo": False,
    },

    "G32-D": {
        "abstract_question": 'How much land is on record in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "mandal" AS geography,
       COUNT(*) AS parcels,
       COUNT(DISTINCT "khata_no") AS khatas,
       ROUND(CAST(SUM("extent") AS NUMERIC), 2) AS total_extent_acres,
       ROUND(CAST(AVG("extent") AS NUMERIC), 2) AS avg_parcel_acres
FROM survey_land_records
WHERE "dist_name" = ?
GROUP BY "mandal"
ORDER BY total_extent_acres DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'District',
        "paraphrases": ['Land record coverage', 'Surveyed extent by area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G32-M": {
        "abstract_question": 'How much land is on record in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "village" AS geography,
       COUNT(*) AS parcels,
       COUNT(DISTINCT "khata_no") AS khatas,
       ROUND(CAST(SUM("extent") AS NUMERIC), 2) AS total_extent_acres,
       ROUND(CAST(AVG("extent") AS NUMERIC), 2) AS avg_parcel_acres
FROM survey_land_records
WHERE "dist_name" = ?
  AND "mandal" = ?
GROUP BY "village"
ORDER BY total_extent_acres DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'Mandal',
        "paraphrases": ['Land record coverage', 'Surveyed extent by area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G33-D": {
        "abstract_question": 'Which land records are pending in {district} district?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "dist_name", "mandal", "village", "pattadar_name",
       "khata_no", "surveyno",
       ROUND(CAST("extent" AS NUMERIC), 2) AS extent_acres,
       "current_status"
FROM survey_land_records
WHERE "current_status" <> 'Approved'
  AND "dist_name" = ?
ORDER BY extent_acres DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'District',
        "paraphrases": ['Mutation pendency', 'Land awaiting clearance'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G33-M": {
        "abstract_question": 'Which land records are pending in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "dist_name", "mandal", "village", "pattadar_name",
       "khata_no", "surveyno",
       ROUND(CAST("extent" AS NUMERIC), 2) AS extent_acres,
       "current_status"
FROM survey_land_records
WHERE "current_status" <> 'Approved'
  AND "dist_name" = ?
  AND "mandal" = ?
ORDER BY extent_acres DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'Mandal',
        "paraphrases": ['Mutation pendency', 'Land awaiting clearance'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "M07": {
        "abstract_question": 'Which farmers declare more land than the revenue record shows, and is their subsidy per acre also elevated?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."village",
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS declared_acres,
       ROUND(CAST(s."extent" AS NUMERIC), 2)                  AS surveyed_acres,
       ROUND(CAST(100.0 * (p."area_hectares" * 2.47105 - s."extent") / NULLIF(s."extent", 0) AS NUMERIC), 1) AS pct_over_declared,
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS subsidy,
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) / NULLIF(s."extent", 0) AS NUMERIC), 2) AS subsidy_per_surveyed_acre
FROM pm_kisan p
JOIN survey_land_records s
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
 AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
LEFT JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
WHERE p."area_hectares" * 2.47105 > s."extent" * (1 + CAST(? AS DOUBLE) / 100.0)
GROUP BY p."name", p."district", p."village", p."area_hectares", s."extent"
ORDER BY pct_over_declared DESC;
""",
        "param_slots": [
            {"name": 'tolerance_pct', "entity_type": 'tolerance_pct', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Over-declaration with subsidy consequence', 'Does inflated area translate into more money'],
        "notes": 'Two-part question in one query: the over-declaration and its financial consequence. Over-declaring is only material if it moves money, and this column pair shows whether it does.',
        "expected_empty_on_demo": False,
    },

    "Q082": {
        "abstract_question": 'Which farmers declare more land in PM-KISAN than the revenue records show, beyond a {tolerance_pct}% tolerance?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."village",
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS declared_acres,
       ROUND(CAST(s."extent" AS NUMERIC), 2)                  AS surveyed_acres,
       ROUND(CAST(100.0 * (p."area_hectares" * 2.47105 - s."extent") / NULLIF(s."extent", 0) AS NUMERIC), 1) AS pct_over_declared
FROM pm_kisan p
JOIN survey_land_records s
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
 AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
WHERE p."area_hectares" * 2.47105 > s."extent" * (1 + CAST(? AS DOUBLE) / 100.0)
ORDER BY pct_over_declared DESC;
""",
        "param_slots": [
            {"name": 'tolerance_pct', "entity_type": 'tolerance_pct', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Over-declared landholdings', 'Declared area exceeds survey extent'],
        "notes": 'Over-declaration inflates area-linked entitlements. Convert hectares to acres before comparing.',
        "expected_empty_on_demo": False,
    },

    "V07": {
        "abstract_question": 'Who are the pattadars in {village}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "pattadar_name", "applicant_name", "khata_no", "surveyno",
       ROUND(CAST("extent" AS NUMERIC), 2) AS extent_acres,
       "category_title", "current_status", "dist_name", "mandal"
FROM survey_land_records
WHERE UPPER(TRIM("village")) = UPPER(TRIM(?))
ORDER BY extent_acres DESC;
""",
        "param_slots": [
            {"name": 'village', "entity_type": 'village', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Mandal AO / RBK',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Land title holders in a village', 'Pattadar list for one village'],
        "notes": 'Village is a slot here because the question is about land records, where village is the natural unit — unlike the scheme aggregates, where it is a display grouping only.',
        "expected_empty_on_demo": False,
    },

    # ── Payments & DBT ────────────────────────────────────────────────────
    "G07-D": {
        "abstract_question": 'How much DBT was credited in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "sub_district" AS geography,
       COUNT(*) AS farmers_paid,
       ROUND(CAST(SUM("last_amount_credited") AS NUMERIC), 2) AS total_credited,
       MAX("last_installment_no") AS latest_installment
FROM pm_kisan
WHERE "last_amount_credited" IS NOT NULL
  AND "district" = ?
GROUP BY "sub_district"
ORDER BY total_credited DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['DBT disbursement by area', 'Money released'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G07-M": {
        "abstract_question": 'How much DBT was credited in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "village" AS geography,
       COUNT(*) AS farmers_paid,
       ROUND(CAST(SUM("last_amount_credited") AS NUMERIC), 2) AS total_credited,
       MAX("last_installment_no") AS latest_installment
FROM pm_kisan
WHERE "last_amount_credited" IS NOT NULL
  AND "district" = ?
  AND "sub_district" = ?
GROUP BY "village"
ORDER BY total_credited DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['DBT disbursement by area', 'Money released'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G08-D": {
        "abstract_question": 'Which farmers in {district} district have missed the latest installment?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "name", "district", "sub_district", "village",
       "last_installment_no", "last_installment_date", "ekyc_status", "mobile_no"
FROM pm_kisan
WHERE "last_installment_no" < (SELECT MAX("last_installment_no") FROM pm_kisan)
  AND "district" = ?
ORDER BY "last_installment_no";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Farmers behind on installments', 'Missed DBT list'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "G08-M": {
        "abstract_question": 'Which farmers in {mandal} mandal have missed the latest installment?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "name", "district", "sub_district", "village",
       "last_installment_no", "last_installment_date", "ekyc_status", "mobile_no"
FROM pm_kisan
WHERE "last_installment_no" < (SELECT MAX("last_installment_no") FROM pm_kisan)
  AND "district" = ?
  AND "sub_district" = ?
ORDER BY "last_installment_no";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Farmers behind on installments', 'Missed DBT list'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "G16-D": {
        "abstract_question": 'Which farmers in {district} district are still unpaid for procurement?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE",
       COUNT(*)                                       AS unpaid_deliveries,
       STRING_AGG(DISTINCT "CROP_NAME", ', ')         AS crops,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS amount_awaiting_payment,
       STRING_AGG(DISTINCT "PAYMENT_STATUS", ', ')    AS payment_statuses,
       MAX("PROCUREMENT_DATE")                        AS latest_delivery,
       MAX("MOBILE_NO")                               AS mobile_no
FROM markfed
WHERE "PAYMENT_STATUS" <> 'Approved'
  AND "DIST_NAME" = ?
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE"
ORDER BY amount_awaiting_payment DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Procured but unpaid', 'Pending MSP payments'],
        "notes": "Field-actionable list; mobile number included for grievance follow-up. One row per farmer (grouped on Aadhaar) — markfed is transactional (1086 rows over 646 suppliers), so the delivery detail is aggregated rather than fanned out. amount_awaiting_payment is the recorded AMOUNT_PAID on unpaid deliveries — the claim value, not money received.",
        "expected_empty_on_demo": False,
    },

    "G16-M": {
        "abstract_question": 'Which farmers in {mandal} mandal are still unpaid for procurement?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE",
       COUNT(*)                                       AS unpaid_deliveries,
       STRING_AGG(DISTINCT "CROP_NAME", ', ')         AS crops,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS amount_awaiting_payment,
       STRING_AGG(DISTINCT "PAYMENT_STATUS", ', ')    AS payment_statuses,
       MAX("PROCUREMENT_DATE")                        AS latest_delivery,
       MAX("MOBILE_NO")                               AS mobile_no
FROM markfed
WHERE "PAYMENT_STATUS" <> 'Approved'
  AND "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE"
ORDER BY amount_awaiting_payment DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Procured but unpaid', 'Pending MSP payments'],
        "notes": "Field-actionable list; mobile number included for grievance follow-up. One row per farmer (grouped on Aadhaar) — markfed is transactional (1086 rows over 646 suppliers), so the delivery detail is aggregated rather than fanned out. amount_awaiting_payment is the recorded AMOUNT_PAID on unpaid deliveries — the claim value, not money received.",
        "expected_empty_on_demo": True,
    },

    "G17-D": {
        "abstract_question": 'How much procurement payment is stuck in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'PAYMENT_DATE'},
        "date_kind": 'iso',  # payment date
        "sql_template": """
SELECT "FARMER_MANDAL" AS geography,
       COUNT(*) AS transactions,
       SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN 1 ELSE 0 END) AS pending_transactions,
       ROUND(CAST(SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) AS NUMERIC), 2) AS pending_value,
       ROUND(CAST(100.0 * SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) / NULLIF(SUM("AMOUNT_PAID"), 0) AS NUMERIC), 1) AS pct_pending
FROM markfed
WHERE "DIST_NAME" = ?
GROUP BY "FARMER_MANDAL"
ORDER BY pending_value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Payment pendency by area', 'Where is procurement money stuck?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G17-M": {
        "abstract_question": 'How much procurement payment is stuck in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'PAYMENT_DATE'},
        "date_kind": 'iso',  # payment date
        "sql_template": """
SELECT "FARMER_VILLAGE" AS geography,
       COUNT(*) AS transactions,
       SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN 1 ELSE 0 END) AS pending_transactions,
       ROUND(CAST(SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) AS NUMERIC), 2) AS pending_value,
       ROUND(CAST(100.0 * SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) / NULLIF(SUM("AMOUNT_PAID"), 0) AS NUMERIC), 1) AS pct_pending
FROM markfed
WHERE "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "FARMER_VILLAGE"
ORDER BY pending_value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Payment pendency by area', 'Where is procurement money stuck?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G22-D": {
        "abstract_question": 'Which sanctions are stalled in {district} district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal", "Village_Name",
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2) AS sanctioned,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2) AS pending,
       "Status", "BENEFICIARYMOBILE"
FROM horticulture_apmip
WHERE "BALANCE_AMOUNT_TO_RELEASE" >= "SubsidyAmt"
  AND "DISTRICT" = ?
ORDER BY pending DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'District',
        "paraphrases": ['Stalled APMIP sanctions', 'Sanctioned but unpaid'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G22-M": {
        "abstract_question": 'Which sanctions are stalled in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal", "Village_Name",
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2) AS sanctioned,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2) AS pending,
       "Status", "BENEFICIARYMOBILE"
FROM horticulture_apmip
WHERE "BALANCE_AMOUNT_TO_RELEASE" >= "SubsidyAmt"
  AND "DISTRICT" = ?
  AND "Mandal" = ?
ORDER BY pending DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'Mandal',
        "paraphrases": ['Stalled APMIP sanctions', 'Sanctioned but unpaid'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G26-D": {
        "abstract_question": 'What is the fisheries payment position in {district} district?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "payment_status",
       COUNT(*) AS records,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_amount
FROM fisheries
WHERE "district" = ?
GROUP BY "payment_status"
ORDER BY total_amount DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Payments & DBT',
        "datasets": 'Fisheries',
        "geo_level": 'District',
        "paraphrases": ['Fisheries payment pendency', 'Unpaid fisheries claims'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G26-M": {
        "abstract_question": 'What is the fisheries payment position in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "payment_status",
       COUNT(*) AS records,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_amount
FROM fisheries
WHERE "district" = ?
  AND "mandal" = ?
GROUP BY "payment_status"
ORDER BY total_amount DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Payments & DBT',
        "datasets": 'Fisheries',
        "geo_level": 'Mandal',
        "paraphrases": ['Fisheries payment pendency', 'Unpaid fisheries claims'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "Q057": {
        "abstract_question": 'Which farmers draw benefits from {scheme_count} or more schemes, and what is their combined total?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, 'agri' AS scheme, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", 'horti',   "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     'fish',    "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    'seri',    "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    'markfed', "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     'ryss',    "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    'pmkisan', "last_amount_credited" FROM pm_kisan
)
SELECT b.aadhaar,
       COALESCE(p."name", '(not in PM-KISAN)') AS farmer_name,
       p."district",
       COUNT(DISTINCT b.scheme)                       AS schemes,
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2)       AS total_benefit
FROM benefits b
LEFT JOIN pm_kisan p ON p."aadhaar_no" = b.aadhaar
GROUP BY b.aadhaar, p."name", p."district"
HAVING COUNT(DISTINCT b.scheme) >= ?
ORDER BY total_benefit DESC;
""",
        "param_slots": [
            {"name": 'scheme_count', "entity_type": 'scheme_count', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Payments & DBT',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Multi-scheme high-value beneficiaries', 'Combined benefit audit list'],
        "notes": 'Not evidence of fraud on its own — it is the shortlist a vigilance officer starts from.',
        "expected_empty_on_demo": False,
    },

    "Q058": {
        "abstract_question": 'What is the total benefit paid to {aadhaar} across every scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Agriculture' AS scheme, ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS amount FROM agriculture WHERE "aadharno" = ?
UNION ALL SELECT 'Horticulture_APMIP', ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) FROM horticulture_apmip WHERE "EXTN_AADHARNO" = ?
UNION ALL SELECT 'Fisheries', ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) FROM fisheries WHERE "aadhar_no" = ?
UNION ALL SELECT 'Sericulture', ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2) FROM sericulture WHERE "aadhaar_no" = ?
UNION ALL SELECT 'MARKFED', ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) FROM markfed WHERE "AADHAAR_NO" = ?
UNION ALL SELECT 'RySS', ROUND(CAST(SUM("Amount") AS NUMERIC), 2) FROM ryss WHERE "Aadhar_no" = ?
UNION ALL SELECT 'PM-KISAN (latest installment)', ROUND(CAST(SUM("last_amount_credited") AS NUMERIC), 2) FROM pm_kisan WHERE "aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 1},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 2},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 3},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 4},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 5},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 6},
            {"name": 'aadhaar', "entity_type": 'aadhaar', "position": 7},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Payments & DBT',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Full benefit history for one farmer', 'How much has this Aadhaar received in total?'],
        "notes": 'The single most-used grievance-desk query. Parameterise on Aadhaar or name.',
        "expected_empty_on_demo": False,
    },

    # ── Procurement & markets ─────────────────────────────────────────────
    "F06": {
        "abstract_question": 'What did MARKFED procure from {farmer_name}, and was payment made?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE", "CROP_NAME", "SEASON",
       ROUND(CAST("AREA_IN_ACRES" AS NUMERIC), 2) AS acres,
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2)  AS quantity,
       ROUND(CAST("RATE" AS NUMERIC), 2)          AS rate,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2)   AS amount_paid,
       "PAYMENT_STATUS", "PROCUREMENT_DATE", "PAYMENT_DATE"
FROM markfed
WHERE "AADHAAR_NO" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Grievance / Call centre',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ["One farmer's procurement record", 'What a farmer sold and was paid'],
        "notes": "Keyed on the Aadhaar the name resolved to. Every row carries money, so mixing namesakes here reads as one farmer having sold several times over.",
        "expected_empty_on_demo": False,
    },

    "G14-D": {
        "abstract_question": 'How much was procured in each mandal of {district} district?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_MANDAL" AS geography,
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS total_quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_value
FROM markfed
WHERE "DIST_NAME" = ?
GROUP BY "FARMER_MANDAL"
ORDER BY total_value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Procurement by area', 'MSP purchases geographically'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G14-M": {
        "abstract_question": 'How much was procured in each village of {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_VILLAGE" AS geography,
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS total_quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_value
FROM markfed
WHERE "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "FARMER_VILLAGE"
ORDER BY total_value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Procurement by area', 'MSP purchases geographically'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G15-D": {
        "abstract_question": 'What was procured by crop in {district} district?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "CROP_NAME", "SEASON",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS value,
       ROUND(CAST(SUM("AMOUNT_PAID") / NULLIF(SUM("PROCURED_QTY"), 0) AS NUMERIC), 2) AS implied_rate
FROM markfed
WHERE "DIST_NAME" = ?
GROUP BY "CROP_NAME", "SEASON"
ORDER BY value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Crop-wise procurement', 'Commodity purchases'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G15-M": {
        "abstract_question": 'What was procured by crop in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "CROP_NAME", "SEASON",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS value,
       ROUND(CAST(SUM("AMOUNT_PAID") / NULLIF(SUM("PROCURED_QTY"), 0) AS NUMERIC), 2) AS implied_rate
FROM markfed
WHERE "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "CROP_NAME", "SEASON"
ORDER BY value DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Crop-wise procurement', 'Commodity purchases'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G18-D": {
        "abstract_question": 'Which procurement records fail reconciliation in {district} district?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "CROP_NAME",
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2) AS quantity,
       ROUND(CAST("RATE" AS NUMERIC), 2) AS rate,
       ROUND(CAST("PROCURED_QTY" * "RATE" AS NUMERIC), 2) AS expected_amount,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2) AS actual_amount
FROM markfed
WHERE ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") > 0.01 * ("PROCURED_QTY" * "RATE")
  AND "DIST_NAME" = ?
ORDER BY ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Billing anomalies', 'Payment does not match quantity and rate'],
        "notes": 'Pure arithmetic reconciliation with a 1% tolerance — the cheapest audit test available.',
        "expected_empty_on_demo": True,
    },

    "G18-M": {
        "abstract_question": 'Which procurement records fail reconciliation in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "CROP_NAME",
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2) AS quantity,
       ROUND(CAST("RATE" AS NUMERIC), 2) AS rate,
       ROUND(CAST("PROCURED_QTY" * "RATE" AS NUMERIC), 2) AS expected_amount,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2) AS actual_amount
FROM markfed
WHERE ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") > 0.01 * ("PROCURED_QTY" * "RATE")
  AND "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
ORDER BY ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Billing anomalies', 'Payment does not match quantity and rate'],
        "notes": 'Pure arithmetic reconciliation with a 1% tolerance — the cheapest audit test available.',
        "expected_empty_on_demo": True,
    },

    "G19-D": {
        "abstract_question": 'Which farmers in {district} district show implausible yields?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL",
       STRING_AGG(DISTINCT "CROP_NAME", ', ')          AS crops,
       COUNT(*)                                        AS implausible_deliveries,
       ROUND(CAST(MAX("AREA_IN_ACRES") AS NUMERIC), 2) AS acres,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2)  AS quantity,
       ROUND(CAST(MAX("PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0)) AS NUMERIC), 2) AS qty_per_acre
FROM markfed
WHERE "PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0) > 10
  AND "DIST_NAME" = ?
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL"
ORDER BY qty_per_acre DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Yield outliers', 'Quantity per acre above plausible limits'],
        "notes": "The 10 units/acre ceiling is a placeholder. Real ceilings are crop-specific and need agronomic sign-off before this goes live. The ceiling is still applied per delivery; the result is then collapsed to one row per farmer, with qty_per_acre showing that farmer's worst delivery.",
        "expected_empty_on_demo": False,
    },

    "G19-M": {
        "abstract_question": 'Which farmers in {mandal} mandal show implausible yields?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL",
       STRING_AGG(DISTINCT "CROP_NAME", ', ')          AS crops,
       COUNT(*)                                        AS implausible_deliveries,
       ROUND(CAST(MAX("AREA_IN_ACRES") AS NUMERIC), 2) AS acres,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2)  AS quantity,
       ROUND(CAST(MAX("PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0)) AS NUMERIC), 2) AS qty_per_acre
FROM markfed
WHERE "PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0) > 10
  AND "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL"
ORDER BY qty_per_acre DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Yield outliers', 'Quantity per acre above plausible limits'],
        "notes": "The 10 units/acre ceiling is a placeholder. Real ceilings are crop-specific and need agronomic sign-off before this goes live. The ceiling is still applied per delivery; the result is then collapsed to one row per farmer, with qty_per_acre showing that farmer's worst delivery.",
        "expected_empty_on_demo": False,
    },

    "Q107": {
        "abstract_question": 'Who are the {top_n} largest suppliers by quantity procured?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "CROP_NAME",
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2) AS quantity,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2)  AS amount,
       "PAYMENT_STATUS"
FROM markfed
ORDER BY quantity DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Top farmers by procurement volume', 'Biggest sellers to MARKFED'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "R03": {
        "abstract_question": 'Who received the {top_n} highest MARKFED payments?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "CROP_NAME",
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2) AS quantity,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2)  AS amount_paid,
       "PAYMENT_STATUS"
FROM markfed
WHERE "AMOUNT_PAID" IS NOT NULL
ORDER BY "AMOUNT_PAID" DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Largest procurement payments', 'Top paid suppliers'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "V04": {
        "abstract_question": 'Which {gender} farmers received MARKFED payments?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "GENDER", "CASTE",
       STRING_AGG(DISTINCT "CROP_NAME", ', ')         AS crops,
       COUNT(*)                                       AS deliveries,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS amount_paid,
       STRING_AGG(DISTINCT "PAYMENT_STATUS", ', ')    AS payment_statuses
FROM markfed
WHERE UPPER(TRIM("GENDER")) = UPPER(TRIM(?))
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "GENDER", "CASTE"
ORDER BY amount_paid DESC;
""",
        "param_slots": [
            {"name": 'gender', "entity_type": 'gender', "position": 1},
        ],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Gender-filtered procurement list', 'Payments to farmers of one gender'],
        "notes": "One row per supplier (grouped on Aadhaar) — markfed is transactional, so the deliveries are aggregated rather than fanned out.",
        "expected_empty_on_demo": False,
    },

    # ── Sectoral deep dive ────────────────────────────────────────────────
    "F03": {
        "abstract_question": 'Is {farmer_name} a micro-irrigation beneficiary, and what was sanctioned?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal", "Village_Name", "CROPNAME", "Crop_Season",
       ROUND(CAST("EXTENT" AS NUMERIC), 2)                    AS extent_acres,
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2)                AS sanctioned,
       ROUND(CAST("Subsidy_Rlsd" AS NUMERIC), 2)              AS released,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2) AS balance,
       "Status"
FROM horticulture_apmip
WHERE "EXTN_AADHARNO" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ["One farmer's APMIP record", 'Horticulture subsidy and extent for a farmer', 'What land extent is recorded for a farmer in horticulture', 'Micro-irrigation extent and sanctioned amount for one farmer', 'Is this farmer an APMIP beneficiary'],
        "notes": 'An empty result means the farmer is not an APMIP beneficiary — that is the answer, not a failure.',
        "expected_empty_on_demo": True,
    },

    "F04": {
        "abstract_question": 'Does {farmer_name} appear in the fisheries data, and what was paid?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmer_name", "district", "mandal", "village", "social_category",
       "fcs_registration_no", "status", "payment_status",
       ROUND(CAST("EXTENT" AS NUMERIC), 2)          AS extent_acres,
       ROUND(CAST("amount_paid" AS NUMERIC), 2)     AS amount_paid,
       ROUND(CAST("subsidy_amount" AS NUMERIC), 2)  AS subsidy_amount
FROM fisheries
WHERE "aadhar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Sectoral deep dive',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ["One farmer's fisheries record", 'Fisheries payment for a farmer'],
        "notes": 'An empty result means this person is not a fisheries registrant.',
        "expected_empty_on_demo": False,
    },

    "F05": {
        "abstract_question": 'What cocoon quantity and incentive are recorded for {farmer_name}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Farmer_Name", "DIST_CODE", "mandal_code", "panchayat_name", "Sex",
       ROUND(CAST("Area" AS NUMERIC), 2)            AS area_acres,
       ROUND(CAST("NoOfDFLs" AS NUMERIC), 2)        AS dfls_brushed,
       ROUND(CAST("Cocoon_Qty" AS NUMERIC), 2)      AS cocoon_qty,
       ROUND(CAST("Eligible_Amount" AS NUMERIC), 2) AS eligible_amount,
       ROUND(CAST("Net_Incentive" AS NUMERIC), 2)   AS net_incentive,
       "Transaction_Status"
FROM sericulture
WHERE "aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Sectoral deep dive',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ["One farmer's sericulture record", 'Cocoon output and incentive for a farmer'],
        "notes": 'Sericulture holds district codes only, so no district name is returned here.',
        "expected_empty_on_demo": False,
    },

    "F07": {
        "abstract_question": 'Is {farmer_name} a natural farming member, and what acreage is recorded?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "FarmerName", "district", "Mandal", "Village_name", "Gram_Panchayat",
       "Social_Category", "season", "farmerStatus", "SurveyDate",
       ROUND(CAST("ACREAGE" AS NUMERIC), 2)                  AS acreage,
       ROUND(CAST("Nf_extent" AS NUMERIC), 2)                AS nf_extent,
       ROUND(CAST("C1 Extent(in Acres)" AS NUMERIC), 2)      AS c1_extent,
       ROUND(CAST("PMDS Extent(in Acres)" AS NUMERIC), 2)    AS pmds_extent
FROM ryss
WHERE "Aadhar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'State',
        "paraphrases": ["One farmer's APCNF record", 'Natural farming acreage for a farmer',
                        'What acreage is recorded for a farmer in RySS?'],
        "notes": "Keyed on the Aadhaar the name resolved to, so the acreage belongs to one member rather than to everyone who shares their name.",
        "expected_empty_on_demo": False,
    },

    "G23-D": {
        "abstract_question": 'What is the inspection backlog in {district} district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Status",
       COUNT(*) AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "Status" <> 'Approved'
GROUP BY "Status"
ORDER BY applications DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'District',
        "paraphrases": ['APMIP verification backlog', 'Inspection pendency'],
        "notes": "Backlog question, so Approved is excluded by definition; the GROUP BY keeps Pending and Under Review as separate rows. Application processing status, not random inspection (G46-D).",
        "expected_empty_on_demo": False,
    },

    "G23-M": {
        "abstract_question": 'What is the inspection backlog in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Status",
       COUNT(*) AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "Mandal" = ?
  AND "Status" <> 'Approved'
GROUP BY "Status"
ORDER BY applications DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'Mandal',
        "paraphrases": ['APMIP verification backlog', 'Inspection pendency'],
        "notes": "Backlog question, so Approved is excluded by definition; the GROUP BY keeps Pending and Under Review as separate rows. Application processing status, not random inspection (G46-M).",
        "expected_empty_on_demo": False,
    },

    "G24-D": {
        "abstract_question": 'What is the unit cost of micro-irrigation in {district} district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(AVG("Cost_per_Hectare") AS NUMERIC), 2) AS avg_cost_per_hectare,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM("SubsidyAmt") / NULLIF(SUM("EXTENT"), 0) AS NUMERIC), 2) AS subsidy_per_acre,
       ROUND(CAST(SUM("Dry_Land") AS NUMERIC), 2) AS dry_land_acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'District',
        "paraphrases": ['Cost per hectare', 'Subsidy intensity in APMIP'],
        "notes": 'Wide unit-cost variation across areas is worth a procurement question.',
        "expected_empty_on_demo": False,
    },

    "G24-M": {
        "abstract_question": 'What is the unit cost of micro-irrigation in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(AVG("Cost_per_Hectare") AS NUMERIC), 2) AS avg_cost_per_hectare,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM("SubsidyAmt") / NULLIF(SUM("EXTENT"), 0) AS NUMERIC), 2) AS subsidy_per_acre,
       ROUND(CAST(SUM("Dry_Land") AS NUMERIC), 2) AS dry_land_acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "Mandal" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'Mandal',
        "paraphrases": ['Cost per hectare', 'Subsidy intensity in APMIP'],
        "notes": 'Wide unit-cost variation across areas is worth a procurement question.',
        "expected_empty_on_demo": False,
    },

    "G27-D": {
        "abstract_question": 'What is the aqua extent position in {district} district?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT COUNT(*) AS registrants,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent,
       ROUND(CAST(SUM("Cultivatable_land") AS NUMERIC), 2) AS cultivable_land,
       ROUND(CAST(SUM("cultivation_land") AS NUMERIC), 2) AS land_under_cultivation,
       ROUND(CAST(SUM("operational_capacity") AS NUMERIC), 2) AS operational_capacity
FROM fisheries
WHERE "district" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Fisheries',
        "geo_level": 'District',
        "paraphrases": ['Aqua extent summary', 'Cultivable versus total water area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G27-M": {
        "abstract_question": 'What is the aqua extent position in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT COUNT(*) AS registrants,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent,
       ROUND(CAST(SUM("Cultivatable_land") AS NUMERIC), 2) AS cultivable_land,
       ROUND(CAST(SUM("cultivation_land") AS NUMERIC), 2) AS land_under_cultivation,
       ROUND(CAST(SUM("operational_capacity") AS NUMERIC), 2) AS operational_capacity
FROM fisheries
WHERE "district" = ?
  AND "mandal" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Fisheries',
        "geo_level": 'Mandal',
        "paraphrases": ['Aqua extent summary', 'Cultivable versus total water area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G29-D": {
        "abstract_question": 'What is the practice-wise area in {district} district?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(SUM("C1 Extent(in Acres)") AS NUMERIC), 2) AS c1_extent,
       ROUND(CAST(SUM("PMDS Extent(in Acres)") AS NUMERIC), 2) AS pmds_extent,
       ROUND(CAST(SUM("Nf_extent") AS NUMERIC), 2) AS nf_extent
FROM ryss
WHERE "district" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'District',
        "paraphrases": ['C1, PMDS and S2S extents', 'APCNF practice mix'],
        "notes": 'C1, PMDS and S2S are the APCNF practice categories, each with its own extent column.',
        "expected_empty_on_demo": False,
    },

    "G29-M": {
        "abstract_question": 'What is the practice-wise area in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(SUM("C1 Extent(in Acres)") AS NUMERIC), 2) AS c1_extent,
       ROUND(CAST(SUM("PMDS Extent(in Acres)") AS NUMERIC), 2) AS pmds_extent,
       ROUND(CAST(SUM("Nf_extent") AS NUMERIC), 2) AS nf_extent
FROM ryss
WHERE "district" = ?
  AND "Mandal" = ?
;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'Mandal',
        "paraphrases": ['C1, PMDS and S2S extents', 'APCNF practice mix'],
        "notes": 'C1, PMDS and S2S are the APCNF practice categories, each with its own extent column.',
        "expected_empty_on_demo": False,
    },

    "G30-D": {
        "abstract_question": 'How is the survey progressing in {district} district?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7) AS survey_month,
       COUNT(*) AS farmers_surveyed,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage_covered
FROM ryss
WHERE "SurveyDate" IS NOT NULL
  AND "district" = ?
GROUP BY SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7)
ORDER BY survey_month;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'District',
        "paraphrases": ['APCNF survey progress', 'Field survey completion over time'],
        "notes": 'SUBSTR on the ISO date gives year-month without a dialect-specific date function.',
        "expected_empty_on_demo": False,
    },

    "G30-M": {
        "abstract_question": 'How is the survey progressing in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7) AS survey_month,
       COUNT(*) AS farmers_surveyed,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage_covered
FROM ryss
WHERE "SurveyDate" IS NOT NULL
  AND "district" = ?
  AND "Mandal" = ?
GROUP BY SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7)
ORDER BY survey_month;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'Mandal',
        "paraphrases": ['APCNF survey progress', 'Field survey completion over time'],
        "notes": 'SUBSTR on the ISO date gives year-month without a dialect-specific date function.',
        "expected_empty_on_demo": False,
    },

    # ── Targeting & equity ────────────────────────────────────────────────
    "G04-D": {
        "abstract_question": 'Give me the social category breakdown for {district} district.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "category",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
WHERE "district" = ?
GROUP BY "category"
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Caste-wise beneficiary split', 'SC/ST/BC/OC composition'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G04-M": {
        "abstract_question": 'Give me the social category breakdown for {mandal} mandal.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "category",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY "category"
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Caste-wise beneficiary split', 'SC/ST/BC/OC composition'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G05-D": {
        "abstract_question": 'What is the male-female split in {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "gender",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM pm_kisan) AS NUMERIC), 1) AS pct_of_state_total
FROM pm_kisan
WHERE "district" = ?
GROUP BY "gender"
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Gender breakdown', 'Women farmers on the roster'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G05-M": {
        "abstract_question": 'What is the male-female split in {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "gender",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM pm_kisan) AS NUMERIC), 1) AS pct_of_state_total
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY "gender"
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Gender breakdown', 'Women farmers on the roster'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G06-D": {
        "abstract_question": 'What is the land-size distribution in {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CASE WHEN "area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN "area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
WHERE "district" = ?
GROUP BY land_band
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Land size bands', 'How many marginal farmers?'],
        "notes": 'GoI definition: marginal below 1 ha, small 1-2 ha, semi-medium and above over 2 ha.',
        "expected_empty_on_demo": False,
    },

    "G06-M": {
        "abstract_question": 'What is the land-size distribution in {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CASE WHEN "area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN "area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
WHERE "district" = ?
  AND "sub_district" = ?
GROUP BY land_band
ORDER BY farmers DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Land size bands', 'How many marginal farmers?'],
        "notes": 'GoI definition: marginal below 1 ha, small 1-2 ha, semi-medium and above over 2 ha.',
        "expected_empty_on_demo": False,
    },

    "G13-D": {
        "abstract_question": 'How is input subsidy distributed across categories in {district} district?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."category",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 2) AS subsidy_per_acre
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
GROUP BY p."category"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'District',
        "paraphrases": ['Caste-wise subsidy share', 'Who gets the money?'],
        "notes": 'Compare the farmer share against the amount share; the gap is the targeting story.',
        "expected_empty_on_demo": False,
    },

    "G13-M": {
        "abstract_question": 'How is input subsidy distributed across categories in {mandal} mandal?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."category",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 2) AS subsidy_per_acre
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY p."category"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'Mandal',
        "paraphrases": ['Caste-wise subsidy share', 'Who gets the money?'],
        "notes": 'Compare the farmer share against the amount share; the gap is the targeting story.',
        "expected_empty_on_demo": False,
    },

    "G20-D": {
        "abstract_question": 'How do procurement payments split by gender and category in {district} district?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "GENDER", "CASTE",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(AVG("AMOUNT_PAID") AS NUMERIC), 2) AS avg_paid
FROM markfed
WHERE "DIST_NAME" = ?
GROUP BY "GENDER", "CASTE"
ORDER BY total_paid DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Targeting & equity',
        "datasets": 'MARKFED',
        "geo_level": 'District',
        "paraphrases": ['Equity in procurement', 'Who sells to MARKFED?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G20-M": {
        "abstract_question": 'How do procurement payments split by gender and category in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "GENDER", "CASTE",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(AVG("AMOUNT_PAID") AS NUMERIC), 2) AS avg_paid
FROM markfed
WHERE "DIST_NAME" = ?
  AND "FARMER_MANDAL" = ?
GROUP BY "GENDER", "CASTE"
ORDER BY total_paid DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Targeting & equity',
        "datasets": 'MARKFED',
        "geo_level": 'Mandal',
        "paraphrases": ['Equity in procurement', 'Who sells to MARKFED?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G31-D": {
        "abstract_question": 'What is the category profile of natural farming members in {district} district?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "Social_Category", "Gender",
       COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "district" = ?
GROUP BY "Social_Category", "Gender"
ORDER BY members DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Targeting & equity',
        "datasets": 'RySS',
        "geo_level": 'District',
        "paraphrases": ['APCNF membership profile', 'Caste-wise natural farming uptake'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G31-M": {
        "abstract_question": 'What is the category profile of natural farming members in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "Social_Category", "Gender",
       COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "district" = ?
  AND "Mandal" = ?
GROUP BY "Social_Category", "Gender"
ORDER BY members DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Targeting & equity',
        "datasets": 'RySS',
        "geo_level": 'Mandal',
        "paraphrases": ['APCNF membership profile', 'Caste-wise natural farming uptake'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G45-D": {
        "abstract_question": 'Does scheme access rise with landholding in {district} district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT CASE WHEN p."area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN p."area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
GROUP BY land_band
ORDER BY avg_schemes DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'District',
        "paraphrases": ['Land size versus scheme access', 'Do bigger farmers capture more?'],
        "notes": 'Central to the equity story: access should not scale with land.',
        "expected_empty_on_demo": False,
    },

    "G45-M": {
        "abstract_question": 'Does scheme access rise with landholding in {mandal} mandal?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT CASE WHEN p."area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN p."area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
WHERE p."district" = ?
  AND p."sub_district" = ?
GROUP BY land_band
ORDER BY avg_schemes DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'Mandal',
        "paraphrases": ['Land size versus scheme access', 'Do bigger farmers capture more?'],
        "notes": 'Central to the equity story: access should not scale with land.',
        "expected_empty_on_demo": False,
    },

    "Q024": {
        "abstract_question": 'Is the {social_category}/{social_category_2} share of subsidy money in line with their share of farmers?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH base AS (
  SELECT SUM(CASE WHEN "category" IN (?,?) THEN 1 ELSE 0 END) AS scst_farmers,
         COUNT(*) AS all_farmers
  FROM pm_kisan
),
money AS (
  SELECT SUM(CASE WHEN "social_status" IN (?,?) THEN "subsidyamount" ELSE 0 END) AS scst_amount,
         SUM("subsidyamount") AS all_amount
  FROM agriculture
)
SELECT ROUND(CAST(100.0 * scst_farmers / all_farmers AS NUMERIC), 1) AS pct_farmers_scst,
       ROUND(CAST(100.0 * scst_amount  / all_amount  AS NUMERIC), 1) AS pct_subsidy_scst,
       ROUND(CAST(100.0 * scst_amount / all_amount - 100.0 * scst_farmers / all_farmers AS NUMERIC), 1) AS equity_gap_pts
FROM base, money;
""",
        "param_slots": [
            {"name": 'social_category', "entity_type": 'social_category', "position": 1},
            {"name": 'social_category_2', "entity_type": 'social_category_2', "position": 2},
            {"name": 'social_category', "entity_type": 'social_category', "position": 3},
            {"name": 'social_category_2', "entity_type": 'social_category_2', "position": 4},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Equity gap in subsidy allocation', 'Are SC/ST farmers under-served relative to their numbers?'],
        "notes": 'Returns two percentages side by side; a negative gap means under-allocation.',
        "expected_empty_on_demo": False,
    },

    "Q029": {
        "abstract_question": 'Which {social_category} and {social_category_2} farmers are not covered by any state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH ap AS (
  SELECT "aadharno"      AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT p."name", p."category", p."district", p."sub_district", p."area_hectares"
FROM pm_kisan p
WHERE p."category" IN (?, ?)
  AND p."aadhaar_no" NOT IN (SELECT aadhaar FROM ap WHERE aadhaar IS NOT NULL)
ORDER BY p."district", p."name";
""",
        "param_slots": [
            {"name": 'social_category', "entity_type": 'social_category', "position": 1},
            {"name": 'social_category_2', "entity_type": 'social_category_2', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Excluded SC/ST farmers', 'Most entitled, least reached'],
        "notes": 'Priority outreach list. Returns names and districts for field follow-up.',
        "expected_empty_on_demo": True,
    },

    "Q030": {
        "abstract_question": 'List {gender} farmers whose eKYC status is {ekyc_status}, so we can run a targeted camp.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "mobile_no"
FROM pm_kisan
WHERE "gender" = ?
  AND "ekyc_status" = ?
ORDER BY "district", "sub_district";
""",
        "param_slots": [
            {"name": 'gender', "entity_type": 'gender', "position": 1},
            {"name": 'ekyc_status', "entity_type": 'ekyc_status', "position": 2},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Women with incomplete eKYC', 'Female beneficiaries blocked on eKYC'],
        "notes": 'Actionable list — includes mobile number for the call centre.',
        "expected_empty_on_demo": True,
    },

    "Q032": {
        "abstract_question": 'Which districts give {social_category}/{social_category_2} farmers a smaller share of subsidy than their share of the farmer base?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH d AS (
  SELECT p."district" AS district,
         SUM(CASE WHEN p."category" IN (?, ?) THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS scst_share_farmers
  FROM pm_kisan p GROUP BY p."district"
),
m AS (
  SELECT p."district" AS district,
         SUM(CASE WHEN p."category" IN (?, ?) THEN a."subsidyamount" ELSE 0 END) * 1.0 / NULLIF(SUM(a."subsidyamount"), 0) AS scst_share_money
  FROM pm_kisan p JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
  GROUP BY p."district"
)
SELECT d.district,
       ROUND(CAST(100.0 * d.scst_share_farmers AS NUMERIC), 1) AS pct_farmers_scst,
       ROUND(CAST(100.0 * m.scst_share_money AS NUMERIC), 1)   AS pct_subsidy_scst,
       ROUND(CAST(100.0 * (m.scst_share_money - d.scst_share_farmers) AS NUMERIC), 1) AS equity_gap_pts
FROM d JOIN m ON m.district = d.district
ORDER BY equity_gap_pts;
""",
        "param_slots": [
            {"name": 'social_category', "entity_type": 'social_category', "position": 1},
            {"name": 'social_category_2', "entity_type": 'social_category_2', "position": 2},
            {"name": 'social_category', "entity_type": 'social_category', "position": 3},
            {"name": 'social_category_2', "entity_type": 'social_category_2', "position": 4},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['District-level equity gaps', 'Where is targeting weakest?'],
        "notes": 'Negative equity_gap_pts = under-allocation in that district.',
        "expected_empty_on_demo": False,
    },

    "Q035": {
        "abstract_question": 'Which {top_n} largest landholders take the most input subsidy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH ranked AS (
  SELECT p."name", p."district", p."area_hectares",
         SUM(a."subsidyamount") AS subsidy
  FROM pm_kisan p
  JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
  GROUP BY p."name", p."district", p."area_hectares"
)
SELECT "name", "district", "area_hectares", subsidy,
       ROUND(CAST(100.0 * subsidy / (SELECT SUM(subsidy) FROM ranked) AS NUMERIC), 1) AS pct_of_total_subsidy
FROM ranked
ORDER BY "area_hectares" DESC
LIMIT ?;
""",
        "param_slots": [
            {"name": 'top_n', "entity_type": 'top_n', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Elite capture check', 'Share of subsidy taken by the biggest farms'],
        "notes": 'Replace the LIMIT with a percentile at production scale (e.g. NTILE(10) for deciles).',
        "expected_empty_on_demo": False,
    },

    "Q036": {
        "abstract_question": 'Which farmers below {threshold_hectares} hectares are in PM-KISAN but have never taken an input subsidy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       p."area_hectares", p."category", p."mobile_no"
FROM pm_kisan p
WHERE p."area_hectares" < ?
  AND p."aadhaar_no" NOT IN (SELECT "aadharno" FROM agriculture WHERE "aadharno" IS NOT NULL)
ORDER BY p."area_hectares";
""",
        "param_slots": [
            {"name": 'threshold_hectares', "entity_type": 'threshold_hectares', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Marginal farmers missing from the subsidy list', 'Under 1 hectare and unreached'],
        "notes": 'The highest-priority outreach segment.',
        "expected_empty_on_demo": False,
    },

    "Q040": {
        "abstract_question": 'In {district}, which farmers received a horticulture subsidy and which did not?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."village", p."area_hectares",
       CASE WHEN h."EXTN_AADHARNO" IS NOT NULL THEN 'Yes' ELSE 'No' END AS got_horticulture_subsidy,
       ROUND(CAST(COALESCE(h."SubsidyAmt", 0) AS NUMERIC), 2) AS subsidy_amount
FROM pm_kisan p
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
WHERE p."district" = ?
ORDER BY got_horticulture_subsidy DESC, p."name";
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['District-level APMIP reach list', 'Who in Krishna got micro-irrigation?'],
        "notes": 'Parameterise the district; this is the workhorse district-officer query.',
        "expected_empty_on_demo": False,
    },

    "S06": {
        "abstract_question": 'Which {social_category} farmers exist, and which schemes cover them?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT p."name", p."district", p."sub_district", p."category", p."area_hectares",
       COUNT(DISTINCT s.scheme)        AS schemes,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM pm_kisan p
LEFT JOIN sch s ON s.aadhaar = p."aadhaar_no"
WHERE p."category" = ?
GROUP BY p."name", p."district", p."sub_district", p."category", p."area_hectares"
ORDER BY schemes DESC;
""",
        "param_slots": [
            {"name": 'social_category', "entity_type": 'social_category', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Category-wise scheme coverage', 'Which programmes reach this community'],
        "notes": 'The complement — category farmers covered by nothing — is the exclusion list.',
        "expected_empty_on_demo": False,
    },


    # ── Added by the template-fidelity pass (2026-07-30) ──────────────────
    "F13": {
        "abstract_question": "Link the land records of {farmer_name} to their PM-KISAN entry — khata, declared versus recorded extent.",
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."village"                     AS roster_village,
       p."khata_no",
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2)  AS declared_acres,
       s."pattadar_name", s."village"                          AS record_village,
       s."surveyno", s."current_status",
       ROUND(CAST(s."extent" AS NUMERIC), 2)                   AS recorded_acres,
       ROUND(CAST(p."area_hectares" * 2.47105 / NULLIF(s."extent", 0) AS NUMERIC), 2) AS declared_over_recorded
FROM pm_kisan p
LEFT JOIN survey_land_records s
  ON CAST(s."khata_no" AS VARCHAR) = CAST(p."khata_no" AS VARCHAR)
WHERE p."aadhaar_no" = ?;
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'farmer_name', "position": 1,
             "bind": 'aadhaar'},
        ],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Match land record to PM-KISAN entry', 'Roster khata against revenue record'],
        "notes": 'Joins on khata_no, which is 1:1 on this drop — production khata is village-scoped m:n, see the P11 caveat in the answer key. declared_over_recorded above 1.10 is the P11 over-declaration signal; F11 and M07 are the mismatch family. Keyed on the Aadhaar the name resolved to: the roster validator disambiguates a shared name before execution, so this can no longer link one person to a namesake\'s land.',
        "expected_empty_on_demo": False,
    },

    "Q152": {
        "abstract_question": 'Which farmers below {threshold_hectares} hectares receive nothing from any state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender",
       ROUND(CAST(p."area_hectares" AS NUMERIC), 2) AS area_hectares, p."mobile_no"
FROM pm_kisan p
WHERE p."area_hectares" < ?
  AND p."aadhaar_no" NOT IN (SELECT aadhaar FROM sch WHERE aadhaar IS NOT NULL)
ORDER BY p."area_hectares";
""",
        "param_slots": [
            {"name": 'threshold_hectares', "entity_type": 'threshold_hectares', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Most-entitled least-reached farmers', 'Small and marginal farmers in no scheme'],
        "notes": 'KEEP-SIX: this asks what no STATE scheme reaches, so PM-KISAN is deliberately absent from the CTE — adding the roster spine would make it empty by definition instead of empty by data. It is a subset of G35-S, an integrity trap that is empty on this drop, so the correct demo answer is "none: every sub-threshold farmer is reached by at least one scheme".',
        "expected_empty_on_demo": True,
    },

    "G46-D": {
        "abstract_question": 'What is the random-inspection backlog in {district} district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "RI_Status_Code"                              AS ri_status,
       COUNT(*)                                      AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)  AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)      AS acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "RI_Status_Code" <> 'Approved'
GROUP BY "RI_Status_Code"
ORDER BY applications DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'District',
        "paraphrases": ['Random inspection backlog in a district', 'RI status for a district'],
        "notes": 'Reads RI_Status_Code (random inspection), a different process from application approval — G23-D is the Status-based application backlog and the two disagree on most rows by design of the source systems. Pendency-filtered like G23.',
        "expected_empty_on_demo": False,
    },

    "G46-M": {
        "abstract_question": 'What is the random-inspection backlog in {mandal} mandal?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "RI_Status_Code"                              AS ri_status,
       COUNT(*)                                      AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)  AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)      AS acres
FROM horticulture_apmip
WHERE "DISTRICT" = ?
  AND "Mandal" = ?
  AND "RI_Status_Code" <> 'Approved'
GROUP BY "RI_Status_Code"
ORDER BY applications DESC;
""",
        "param_slots": [
            {"name": 'district', "entity_type": 'district', "position": 1},
            {"name": 'mandal', "entity_type": 'mandal', "position": 2},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'Mandal',
        "paraphrases": ['Random inspection backlog in a mandal', 'RI status for a mandal'],
        "notes": 'Reads RI_Status_Code (random inspection), a different process from application approval — G23-M is the Status-based application backlog. Carries the district slot as well as the mandal, exactly like G23-M.',
        "expected_empty_on_demo": False,
    },


    # ── Casual-phrasing coverage (fidelity item 13, 2026-07-30) ───────────
    "Q154": {
        "abstract_question": 'Which farmers growing {crop} have eKYC still pending?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       STRING_AGG(DISTINCT a."cropnameeng", ', ') AS crops,
       p."ekyc_status", p."beneficiary_status", p."mobile_no"
FROM pm_kisan p
JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
WHERE p."ekyc_status" = 'Pending'
  AND UPPER(a."cropnameeng") = UPPER(TRIM(?))
GROUP BY p."aadhaar_no", p."name", p."district", p."sub_district", p."village",
         p."ekyc_status", p."beneficiary_status", p."mobile_no"
ORDER BY p."district", p."name";
""",
        "param_slots": [
            {"name": 'crop', "entity_type": 'crop', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Paddy farmers with pending eKYC', 'List farmers of a crop whose eKYC is pending',
                        'Give me list of paddy farmers whose ekyc is pending'],
        "notes": 'One row per farmer (item-2 grain rule). V05 is the same list with NO crop filter — routing must not send a crop-named question there, which silently drops the filter and returns all 87 pending farmers. V08 is the crops-per-status rollup, an aggregate rather than a list.',
        "expected_empty_on_demo": False,
    },

    "Q155": {
        "abstract_question": 'Which farmers hold less than {threshold_hectares} hectares in PM-KISAN?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village", p."category", p."gender",
       ROUND(CAST(p."area_hectares" AS NUMERIC), 2)           AS area_hectares,
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS acres,
       p."mobile_no"
FROM pm_kisan p
WHERE p."area_hectares" < ?
ORDER BY p."area_hectares";
""",
        "param_slots": [
            {"name": 'threshold_hectares', "entity_type": 'threshold_hectares', "position": 1},
        ],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['List of marginal farmers', 'Farmers with less than 1 acre of land',
                        'Small landholders list', 'How many farmers with less than 1 acre land'],
        "notes": 'The UNCONDITIONED roster land filter — the plain answer to "farmers below N hectares". Q036 looks similar but also requires "never took an input subsidy" (31 rows where this gives 62 at the 1-acre threshold), G06-S is the band summary rather than a list, and Q152 additionally requires no state scheme. The extractor converts acres to hectares (1 acre = 0.4047 ha); area_hectares is HECTARES and acres is shown alongside so the answer can be read either way.',
        "expected_empty_on_demo": False,
    },

    "F14": {
        "abstract_question": 'Which farmers share the name {farmer_name}, and where are they?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       ROUND(CAST(p."area_hectares" AS NUMERIC), 2) AS area_hectares,
       p."category", p."ekyc_status", p."beneficiary_status",
       COUNT(*) OVER () AS farmers_with_this_name
FROM pm_kisan p
WHERE UPPER(TRIM(p."name")) = UPPER(TRIM(?))
ORDER BY p."district", p."village";
""",
        "param_slots": [
            {"name": 'farmer_name', "entity_type": 'name_search', "position": 1},
        ],
        "result_ttl_seconds": 600,
        "persona": 'Grievance / Call centre',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['How many farmers named Ramesh Naidu exist?', 'List all farmers with a given name',
                        'Give me list of all farmers named this'],
        "notes": 'Uses entity_type name_search, NOT farmer_name: the roster validator raises ClarificationNeeded on an ambiguous name, which would defeat this template — the ambiguity IS the question. Four Ramesh Naidus exist on this drop by design, and this is the template behind the Farmer 360 name-collision story. Every F-template other than this one wants farmer_name and its disambiguation.',
        "expected_empty_on_demo": False,
    },

}


# Whole-of-state templates that take no entity. Same shape, empty param_slots.
UNPARAMETERISED_CATALOG: dict[str, dict] = {

    # ── Convergence & overlap ─────────────────────────────────────────────
    "G34-S": {
        "abstract_question": 'Rank districts by the average number of schemes per farmer.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT p."district" AS geography,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes_per_farmer,
       SUM(CASE WHEN c.n IS NULL THEN 1 ELSE 0 END) AS farmers_with_nothing
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
GROUP BY p."district"
ORDER BY avg_schemes_per_farmer DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Convergence ranking', 'Which areas converge best?'],
        "notes": "Rewards breadth of service rather than spend. The farmers_with_nothing column is the exclusion list's size.",
        "expected_empty_on_demo": False,
    },

    "G35-S": {
        "abstract_question": 'Which farmers receive nothing from any state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."mobile_no"
FROM pm_kisan p
WHERE p."aadhaar_no" NOT IN (SELECT aadhaar FROM sch WHERE aadhaar IS NOT NULL)
ORDER BY p."area_hectares";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Completely unreached farmers', 'Exclusion list'],
        "notes": 'The core exclusion list. Every convergence effort should be measured against this shrinking.',
        "expected_empty_on_demo": True,
    },

    "G36-S": {
        "abstract_question": 'Rank farmers by the total benefit they receive across all schemes.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    "last_amount_credited" FROM pm_kisan
)
SELECT p."name", p."district", p."sub_district", p."category",
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2) AS total_benefit
FROM pm_kisan p
JOIN benefits b ON b.aadhaar = p."aadhaar_no"
GROUP BY p."name", p."district", p."sub_district", p."category"
ORDER BY total_benefit DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Total benefit league table', 'Aggregate public money per farmer'],
        "notes": 'Sums different benefit types together. Read as total public money touching that farmer, not as income.',
        "expected_empty_on_demo": False,
    },

    "Q113": {
        "abstract_question": 'Give me a scheme participation matrix: for every farmer, which programmes are they in?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."aadhaar_no", p."name", p."district", p."category", p."area_hectares",
       CASE WHEN p."aadhaar_no"    IS NOT NULL THEN 1 ELSE 0 END AS pm_kisan,
       CASE WHEN a."aadharno"      IS NOT NULL THEN 1 ELSE 0 END AS agriculture,
       CASE WHEN h."EXTN_AADHARNO" IS NOT NULL THEN 1 ELSE 0 END AS horticulture,
       CASE WHEN f."aadhar_no"     IS NOT NULL THEN 1 ELSE 0 END AS fisheries,
       CASE WHEN s."aadhaar_no"    IS NOT NULL THEN 1 ELSE 0 END AS sericulture,
       CASE WHEN m."AADHAAR_NO"    IS NOT NULL THEN 1 ELSE 0 END AS markfed,
       CASE WHEN r."Aadhar_no"     IS NOT NULL THEN 1 ELSE 0 END AS ryss
FROM pm_kisan p
LEFT JOIN (SELECT DISTINCT "aadharno"      FROM agriculture)        a ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN (SELECT DISTINCT "EXTN_AADHARNO" FROM horticulture_apmip) h ON h."EXTN_AADHARNO" = p."aadhaar_no"
LEFT JOIN (SELECT DISTINCT "aadhar_no"     FROM fisheries)          f ON f."aadhar_no"     = p."aadhaar_no"
LEFT JOIN (SELECT DISTINCT "aadhaar_no"    FROM sericulture)        s ON s."aadhaar_no"    = p."aadhaar_no"
LEFT JOIN (SELECT DISTINCT "AADHAAR_NO"    FROM markfed)            m ON m."AADHAAR_NO"    = p."aadhaar_no"
LEFT JOIN (SELECT DISTINCT "Aadhar_no"     FROM ryss)               r ON r."Aadhar_no"     = p."aadhaar_no"
ORDER BY p."district", p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Farmer 360 matrix', 'Which schemes does each farmer touch?'],
        "notes": 'The backbone view. Everything else in this theme is a filter on top of it.',
        "expected_empty_on_demo": False,
    },

    "Q117": {
        "abstract_question": 'Which natural farming members are still drawing chemical input subsidies?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT r."FarmerName", r."district", r."Mandal",
       ROUND(CAST(MAX(r."ACREAGE") AS NUMERIC), 2)       AS nf_acreage,
       COUNT(*)                                          AS subsidy_transactions,
       STRING_AGG(DISTINCT a."cropname", ', ')           AS crops,
       STRING_AGG(DISTINCT a."season", ', ')             AS seasons,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy
FROM ryss r
JOIN agriculture a ON a."aadharno" = r."Aadhar_no"
GROUP BY r."Aadhar_no", r."FarmerName", r."district", r."Mandal"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Convergence & overlap',
        "datasets": 'RySS + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['APCNF members taking input subsidy', 'Contradiction between natural farming and input support'],
        "notes": "A genuine policy contradiction worth surfacing: the state pays for natural farming conversion and for purchased inputs on the same plot. One row per RySS member (grouped on Aadhaar) — agriculture is transactional (1114 rows over 652 farmers), so the subsidy detail is aggregated rather than fanned out.",
        "expected_empty_on_demo": False,
    },

    "Q118": {
        "abstract_question": 'Which pairs of schemes overlap the most in the farmers they serve?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT s1.scheme AS scheme_a, s2.scheme AS scheme_b,
       COUNT(DISTINCT s1.aadhaar) AS shared_farmers
FROM sch s1
JOIN sch s2 ON s2.aadhaar = s1.aadhaar AND s1.scheme < s2.scheme
GROUP BY s1.scheme, s2.scheme
ORDER BY shared_farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Scheme co-occurrence', 'Which programmes share beneficiaries?',
                        'How many farmers are in both input subsidy and MARKFED?',
                        'Overlap between two schemes', 'How many input-subsidy farmers also sold produce to MARKFED', 'Farmers in both Agriculture and MARKFED, all crops'],
        "notes": 'Shows where a joint outreach or a single application form would save farmers a trip.',
        "expected_empty_on_demo": False,
    },

    "Q122": {
        "abstract_question": 'Which households are registered both as fishers and as crop farmers?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT f."farmer_name", f."district", f."mandal",
       ROUND(CAST(MAX(f."amount_paid") AS NUMERIC), 2)   AS fisheries_payment,
       COUNT(*)                                          AS crop_transactions,
       STRING_AGG(DISTINCT a."cropname", ', ')           AS crops,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS crop_subsidy
FROM fisheries f
JOIN agriculture a ON a."aadharno" = f."aadhar_no"
GROUP BY f."aadhar_no", f."farmer_name", f."district", f."mandal"
ORDER BY f."district", f."farmer_name";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Convergence & overlap',
        "datasets": 'Fisheries + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Fisheries and crop overlap', 'Dual-livelihood households'],
        "notes": "Dual livelihoods are common in delta districts. Worth knowing before designing single-livelihood interventions. One row per household (grouped on Aadhaar) — agriculture is transactional, so the crop detail is aggregated rather than fanned out.",
        "expected_empty_on_demo": False,
    },

    "Q123": {
        "abstract_question": 'Which sericulture farmers also sell produce through MARKFED?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT s."Farmer_Name",
       ROUND(CAST(MAX(s."Net_Incentive") AS NUMERIC), 2) AS sericulture_incentive,
       STRING_AGG(DISTINCT m."CROP_NAME", ', ')          AS crops,
       COUNT(*)                                          AS deliveries,
       ROUND(CAST(SUM(m."AMOUNT_PAID") AS NUMERIC), 2)   AS procurement_payment,
       MAX(m."DIST_NAME")                                AS "DIST_NAME"
FROM sericulture s
JOIN markfed m ON m."AADHAAR_NO" = s."aadhaar_no"
GROUP BY s."aadhaar_no", s."Farmer_Name"
ORDER BY procurement_payment DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Convergence & overlap',
        "datasets": 'Sericulture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Silk and procurement overlap', 'Diversified income farmers'],
        "notes": "One row per sericulture farmer (grouped on Aadhaar) — markfed is transactional, so the deliveries are aggregated rather than fanned out.",
        "expected_empty_on_demo": False,
    },

    "Q126": {
        "abstract_question": 'How many farmers does each scheme serve that no other scheme reaches?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT s.scheme,
       COUNT(DISTINCT s.aadhaar)                                             AS total_farmers,
       SUM(CASE WHEN c.n = 1 THEN 1 ELSE 0 END)                              AS exclusive_farmers
FROM sch s
JOIN cnt c ON c.aadhaar = s.aadhaar
GROUP BY s.scheme
ORDER BY exclusive_farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Exclusive beneficiaries per scheme', 'Unique reach of each programme'],
        "notes": "KEEP-SIX: measures the SIX STATE schemes' exclusive reach; the PM-KISAN roster is excluded on purpose. With PM-KISAN in the enumeration every roster farmer in one state scheme has two schemes, so no state scheme reaches anyone 'exclusively' and every count collapses to zero — the question reads naturally as state-scheme exclusivity. Operator decision 2026-07-30.",
        "expected_empty_on_demo": False,
    },

    # ── Coverage & scale ──────────────────────────────────────────────────
    "G01-S": {
        "abstract_question": 'How many PM-KISAN beneficiaries are there in each district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
GROUP BY "district"
ORDER BY beneficiaries DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Beneficiary count by area', 'Where are our farmers?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G02-S": {
        "abstract_question": 'Where does the eKYC and beneficiary-status pendency sit across districts?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district" AS geography,
       COUNT(*) AS beneficiaries,
       SUM(CASE WHEN "ekyc_status" = 'Pending' THEN 1 ELSE 0 END) AS ekyc_pending,
       SUM(CASE WHEN "beneficiary_status" <> 'Included' THEN 1 ELSE 0 END) AS not_included,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc_complete
FROM pm_kisan
GROUP BY "district"
ORDER BY ekyc_pending DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['eKYC backlog by area', 'Status pendency dashboard'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G03-S": {
        "abstract_question": 'What is the total cultivable area held by PM-KISAN beneficiaries?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS total_hectares,
       ROUND(CAST(SUM("area_hectares") * 2.47105 AS NUMERIC), 2) AS total_acres,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Total land under the scheme', 'Area covered'],
        "notes": 'PM-KISAN stores hectares; the acre column is converted at 1 ha = 2.47105 acres.',
        "expected_empty_on_demo": False,
    },

    "G10-S": {
        "abstract_question": 'How much input subsidy was disbursed in each district?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."district" AS geography,
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(AVG(a."subsidyamount") AS NUMERIC), 2) AS avg_subsidy
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropyear" IS NOT NULL
GROUP BY p."district"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Coverage & scale',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Seed subsidy by area', 'Input support disbursed'],
        "notes": 'Agriculture stores district and mandal as codes only, so geography is resolved through the PM-KISAN spine. Farmers not on the roster drop out of this query — see the off-roster checks for that population.',
        "expected_empty_on_demo": False,
    },

    "G21-S": {
        "abstract_question": 'What is the micro-irrigation coverage in each district?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "DISTRICT" AS geography,
       COUNT(*) AS beneficiaries,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres_covered,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_sanctioned
FROM horticulture_apmip
WHERE "SanctionProceedingDate" IS NOT NULL
GROUP BY "DISTRICT"
ORDER BY subsidy_sanctioned DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Coverage & scale',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['APMIP coverage by area', 'Micro-irrigation footprint', 'Micro-irrigation coverage by district', 'Which districts have the most APMIP beneficiaries'],
        "notes": 'Horticulture dates are Excel serial numbers in the source, so the date filter is numeric. Normalise these at ingestion.',
        "expected_empty_on_demo": False,
    },

    "G25-S": {
        "abstract_question": 'How many fishers are registered in each district, and how much has been paid?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "district" AS geography,
       COUNT(DISTINCT "aadhar_no") AS registrants,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent_acres
FROM fisheries
WHERE "fcs_registration_date" IS NOT NULL
GROUP BY "district"
ORDER BY registrants DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Coverage & scale',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ['Fisheries coverage by area', 'Registrations and payouts'],
        "notes": 'Fisheries registration dates are Excel serial numbers in the source; the date filter is numeric.',
        "expected_empty_on_demo": False,
    },

    "G28-S": {
        "abstract_question": 'How many natural farming members are there in each district, and what area do they cover?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "district" AS geography,
       COUNT(DISTINCT "Aadhar_no") AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "SurveyDate" IS NOT NULL
GROUP BY "district"
ORDER BY total_acreage DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Coverage & scale',
        "datasets": 'RySS',
        "geo_level": 'State',
        "paraphrases": ['APCNF coverage by area', 'Natural farming membership'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "M01": {
        "abstract_question": 'What are the statewide headline numbers — beneficiaries, area, subsidy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT (SELECT COUNT(*) FROM pm_kisan)                                             AS pmkisan_beneficiaries,
       (SELECT COUNT(DISTINCT "district") FROM pm_kisan)                            AS districts,
       (SELECT COUNT(DISTINCT "sub_district") FROM pm_kisan)                        AS mandals,
       (SELECT COUNT(DISTINCT "village") FROM pm_kisan)                             AS villages,
       (SELECT ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) FROM pm_kisan)       AS total_hectares,
       (SELECT ROUND(CAST(SUM("area_hectares") * 2.47105 AS NUMERIC), 2) FROM pm_kisan) AS total_acres,
       (SELECT COUNT(DISTINCT "aadharno") FROM agriculture)                         AS subsidy_farmers,
       (SELECT ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) FROM agriculture)    AS total_subsidy,
       (SELECT ROUND(CAST(AVG("subsidyamount") AS NUMERIC), 2) FROM agriculture)    AS avg_subsidy_per_transaction;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['One-line state summary', 'Headline totals for the state'],
        "notes": "A single row. The district-grouped versions (G01-S, G10-S) answer 'by district'; this one answers 'in total', which is a different question and was previously only reachable by summing a table.",
        "expected_empty_on_demo": False,
    },

    "M02": {
        "abstract_question": 'How many farmers are in each dataset, and do they carry Aadhaar?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PM-KISAN' AS dataset, COUNT(*) AS records, COUNT(DISTINCT "aadhaar_no") AS distinct_aadhaar, 'Yes' AS has_aadhaar FROM pm_kisan
UNION ALL SELECT 'Agriculture',        COUNT(*), COUNT(DISTINCT "aadharno"),      'Yes' FROM agriculture
UNION ALL SELECT 'Horticulture_APMIP', COUNT(*), COUNT(DISTINCT "EXTN_AADHARNO"), 'Yes' FROM horticulture_apmip
UNION ALL SELECT 'Fisheries',          COUNT(*), COUNT(DISTINCT "aadhar_no"),     'Yes' FROM fisheries
UNION ALL SELECT 'Sericulture',        COUNT(*), COUNT(DISTINCT "aadhaar_no"),    'Yes' FROM sericulture
UNION ALL SELECT 'MARKFED',            COUNT(*), COUNT(DISTINCT "AADHAAR_NO"),    'Yes' FROM markfed
UNION ALL SELECT 'RySS',               COUNT(*), COUNT(DISTINCT "Aadhar_no"),     'Yes' FROM ryss
UNION ALL SELECT 'Survey_Land_Records',COUNT(*), 0,                               'No — joins on pattadar name + village' FROM survey_land_records
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Data / MIS',
        "theme": 'Coverage & scale',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Record counts per dataset', 'Which datasets can be joined on Aadhaar'],
        "notes": 'ANSWERS A SCHEMA QUESTION AS WELL AS A COUNT. Survey_Land_Records has no Aadhaar column at all, which is why it joins on pattadar name plus village and why those matches are a review queue rather than a hard link.',
        "expected_empty_on_demo": False,
    },

    "Q001": {
        "abstract_question": 'How many farmers are registered as PM-KISAN beneficiaries in the state?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS total_beneficiaries
FROM pm_kisan;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Total PM-KISAN beneficiary count', 'Size of the PM-KISAN roster'],
        "notes": 'PM-KISAN is the spine roster; use it as the denominator for coverage questions.',
        "expected_empty_on_demo": False,
    },

    "Q004": {
        "abstract_question": 'How many unique farmers do we actually touch across every department dataset put together?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH all_aadhaar AS (
  SELECT "aadhaar_no"     AS aadhaar FROM pm_kisan
  UNION SELECT "aadharno"        FROM agriculture
  UNION SELECT "EXTN_AADHARNO"   FROM horticulture_apmip
  UNION SELECT "aadhar_no"       FROM fisheries
  UNION SELECT "aadhaar_no"      FROM sericulture
  UNION SELECT "AADHAAR_NO"      FROM markfed
  UNION SELECT "Aadhar_no"       FROM ryss
)
SELECT COUNT(*) AS unique_farmers
FROM all_aadhaar
WHERE aadhaar IS NOT NULL;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Data / MIS',
        "theme": 'Coverage & scale',
        "datasets": 'All 7 Aadhaar-bearing datasets',
        "geo_level": 'State',
        "paraphrases": ['Size of the combined farmer universe', 'Total distinct Aadhaar across all schemes'],
        "notes": 'The union universe is larger than PM-KISAN: some scheme beneficiaries are not on the PM-KISAN roster.',
        "expected_empty_on_demo": False,
    },

    "Q005": {
        "abstract_question": 'Give me one table showing how many records each department dataset holds.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PM-KISAN' AS dataset, COUNT(*) AS records FROM pm_kisan
UNION ALL SELECT 'Agriculture', COUNT(*) FROM agriculture
UNION ALL SELECT 'Horticulture_APMIP', COUNT(*) FROM horticulture_apmip
UNION ALL SELECT 'Fisheries', COUNT(*) FROM fisheries
UNION ALL SELECT 'Sericulture', COUNT(*) FROM sericulture
UNION ALL SELECT 'MARKFED', COUNT(*) FROM markfed
UNION ALL SELECT 'RySS', COUNT(*) FROM ryss
UNION ALL SELECT 'Survey_Land_Records', COUNT(*) FROM survey_land_records
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Record counts per dataset', "How big is each department's data?"],
        "notes": "Standing 'inventory' query — good first answer for a new user of the bot.",
        "expected_empty_on_demo": False,
    },

    "Q007": {
        "abstract_question": 'How many mandals and villages in each district have at least one PM-KISAN beneficiary?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district",
       COUNT(DISTINCT "sub_district") AS mandals_covered,
       COUNT(DISTINCT "village")      AS villages_covered,
       COUNT(*)                       AS beneficiaries
FROM pm_kisan
GROUP BY "district"
ORDER BY beneficiaries DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Administrative spread of PM-KISAN', 'Mandal and village coverage by district'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q010": {
        "abstract_question": 'How many fishers and aqua farmers are registered, and how much has been paid to them?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT "aadhar_no")                       AS registrants,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2)    AS total_paid,
       ROUND(CAST(SUM("subsidy_amount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)         AS total_extent_acres
FROM fisheries;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Coverage & scale',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ['Fisheries registration and payout summary', 'Coverage of the fisheries department'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q011": {
        "abstract_question": 'How many sericulture farmers are registered and what incentive has been paid?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT "aadhaar_no")                     AS farmers,
       ROUND(CAST(SUM("Cocoon_Qty") AS NUMERIC), 2)    AS total_cocoon_qty,
       ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2) AS total_net_incentive
FROM sericulture;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Coverage & scale',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Silk farming coverage', 'Sericulture incentive totals'],
        "notes": 'Sericulture carries district codes only, no district names.',
        "expected_empty_on_demo": False,
    },

    "Q012": {
        "abstract_question": 'How much produce has MARKFED procured and how much has been paid to farmers?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT "AADHAAR_NO")                     AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2)  AS total_quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)   AS total_paid,
       ROUND(CAST(AVG("RATE") AS NUMERIC), 2)          AS avg_rate
FROM markfed;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Coverage & scale',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Procurement headline numbers', 'MSP procurement volume and value'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q015": {
        "abstract_question": 'What share of PM-KISAN farmers has been reached by at least one state scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH ap AS (
  SELECT "aadharno"      AS aadhaar FROM agriculture
  UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
  UNION SELECT "aadhar_no"     FROM fisheries
  UNION SELECT "aadhaar_no"    FROM sericulture
  UNION SELECT "AADHAAR_NO"    FROM markfed
  UNION SELECT "Aadhar_no"     FROM ryss
)
SELECT COUNT(*)                                                        AS pmkisan_farmers,
       SUM(CASE WHEN ap.aadhaar IS NOT NULL THEN 1 ELSE 0 END)         AS reached_by_state_scheme,
       ROUND(CAST(100.0 * SUM(CASE WHEN ap.aadhaar IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_reached
FROM pm_kisan p
LEFT JOIN ap ON ap.aadhaar = p."aadhaar_no";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Convergence rate', 'How many of our farmers get anything beyond PM-KISAN?'],
        "notes": 'Headline convergence indicator. The complement is the untouched population.',
        "expected_empty_on_demo": False,
    },

    "Q016": {
        "abstract_question": 'What is the distribution of farmers by number of schemes they are enrolled in?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH scheme_flags AS (
  SELECT "aadharno" AS aadhaar, 'agri' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'horti' FROM horticulture_apmip
  UNION SELECT "aadhar_no",    'fish'  FROM fisheries
  UNION SELECT "aadhaar_no",   'seri'  FROM sericulture
  UNION SELECT "AADHAAR_NO",   'markfed' FROM markfed
  UNION SELECT "Aadhar_no",    'ryss'  FROM ryss  UNION SELECT "aadhaar_no",   'pmkisan' FROM pm_kisan
),
per_farmer AS (
  SELECT aadhaar, COUNT(DISTINCT scheme) AS n_schemes
  FROM scheme_flags GROUP BY aadhaar
)
SELECT n_schemes, COUNT(*) AS farmers
FROM per_farmer
GROUP BY n_schemes
ORDER BY n_schemes;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Coverage & scale',
        "datasets": 'All 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['How many farmers are in 1, 2, 3+ schemes?', 'Scheme-count histogram'],
        "notes": 'Concentration check: are the same farmers taking everything?',
        "expected_empty_on_demo": False,
    },

    "Q017": {
        "abstract_question": 'How many districts does each scheme operate in?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PM-KISAN' AS scheme, COUNT(DISTINCT "district") AS districts FROM pm_kisan
UNION ALL SELECT 'Horticulture_APMIP', COUNT(DISTINCT "DISTRICT") FROM horticulture_apmip
UNION ALL SELECT 'Fisheries', COUNT(DISTINCT "district") FROM fisheries
UNION ALL SELECT 'MARKFED', COUNT(DISTINCT "DIST_NAME") FROM markfed
UNION ALL SELECT 'RySS', COUNT(DISTINCT "district") FROM ryss
UNION ALL SELECT 'Survey_Land_Records', COUNT(DISTINCT "dist_name") FROM survey_land_records
ORDER BY districts DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Data / MIS',
        "theme": 'Coverage & scale',
        "datasets": 'All schemes with district names',
        "geo_level": 'State',
        "paraphrases": ['Geographic breadth per scheme', 'District spread by department'],
        "notes": 'Sericulture is excluded: it stores DIST_CODE only, no district name.',
        "expected_empty_on_demo": False,
    },

    "Q018": {
        "abstract_question": 'Which districts have PM-KISAN farmers but no micro-irrigation beneficiary at all?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district",
       COUNT(*) AS pmkisan_farmers
FROM pm_kisan p
WHERE p."district" NOT IN (SELECT "DISTRICT" FROM horticulture_apmip WHERE "DISTRICT" IS NOT NULL)
GROUP BY p."district"
ORDER BY pmkisan_farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN + Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Districts untouched by APMIP', 'Where has horticulture not reached?'],
        "notes": "Classic 'white space' query for scheme expansion planning.",
        "expected_empty_on_demo": False,
    },

    "Q019": {
        "abstract_question": 'What is the average landholding per district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district",
       COUNT(*)                                                  AS farmers,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2)           AS avg_hectares,
       ROUND(CAST(AVG("area_hectares") * 2.47105 AS NUMERIC), 2) AS avg_acres
FROM pm_kisan
GROUP BY "district"
ORDER BY avg_hectares;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Coverage & scale',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['District-wise average farm size', 'Where are the smallest farms?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    # ── Crop & inputs ─────────────────────────────────────────────────────
    "G11-S": {
        "abstract_question": 'Which crops account for the most input subsidy?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropname", a."season",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."seed_production") AS NUMERIC), 2) AS seed_quantity
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropyear" IS NOT NULL
GROUP BY a."cropname", a."season"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Crop-wise subsidy', 'What are we subsidising?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G12-S": {
        "abstract_question": 'How many crop registrations are still awaiting approval?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT a."cropstatus", a."cropname",
       COUNT(*) AS records,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS subsidy_held_up
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropstatus" <> 'Approved'
GROUP BY a."cropstatus", a."cropname"
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['eCrop approval backlog', 'Pending crop registrations'],
        "notes": 'Valid statuses in this table are only Approved, Pending and Under Review — there is no Damaged status.',
        "expected_empty_on_demo": False,
    },

    "M05": {
        "abstract_question": 'Which farmers have a crop registered but no seed subsidy for the same season?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "farmername", "cropname", "season", "cropyear", "cropstatus",
       "subsidyamount", "seed_production"
FROM agriculture
WHERE "subsidyamount" IS NULL OR "subsidyamount" = 0
ORDER BY "farmername";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Registered but unsupported', 'Crop registration that never converted to input support'],
        "notes": 'SCHEMA LIMITATION. In this schema crop registration and subsidy live in the same row, so a registration with no subsidy can only appear as a null or zero amount. If eCrop registration is a separate system in production, this needs a second source and the query will change shape entirely — worth confirming before relying on it.',
        "expected_empty_on_demo": True,
    },

    "Q090": {
        "abstract_question": 'How does input subsidy split between Kharif and Rabi?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "season",
       COUNT(DISTINCT "aadharno")                          AS farmers,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2)     AS total_subsidy,
       ROUND(CAST(SUM("nonsubsidyamount") AS NUMERIC), 2)  AS farmer_contribution,
       ROUND(CAST(SUM("subsidyamount") / NULLIF(SUM("nonsubsidyamount"), 0) AS NUMERIC), 2) AS subsidy_to_contribution_ratio
FROM agriculture
GROUP BY "season"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Season-wise subsidy totals', 'Kharif vs Rabi spending'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q091": {
        "abstract_question": 'Show me the crop pattern by district.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district", a."cropname",
       COUNT(DISTINCT a."aadharno")                      AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS subsidy
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
GROUP BY p."district", a."cropname"
ORDER BY p."district", subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Crop & inputs',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['District-wise crop mix', 'What is grown where?'],
        "notes": 'Agriculture stores district codes only; the district name comes from the PM-KISAN spine.',
        "expected_empty_on_demo": False,
    },

    "Q093": {
        "abstract_question": 'How much seed was distributed for each crop and variety?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "cropname", "varietyname",
       COUNT(*)                                          AS distributions,
       ROUND(CAST(SUM("seed_production") AS NUMERIC), 2) AS total_seed_quantity
FROM agriculture
GROUP BY "cropname", "varietyname"
ORDER BY total_seed_quantity DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Mandal AO / RBK',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Seed distribution by crop', 'Input quantities issued'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q094": {
        "abstract_question": 'Which farmers receive the highest input subsidy per acre of land held?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district",
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS acres,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2)      AS subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / NULLIF(p."area_hectares" * 2.47105, 0) AS NUMERIC), 2) AS subsidy_per_acre
FROM pm_kisan p
JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
GROUP BY p."aadhaar_no", p."name", p."district", p."area_hectares"
ORDER BY subsidy_per_acre DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Crop & inputs',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Subsidy intensity per acre', 'Outlier subsidy rates'],
        "notes": "Per-acre normalisation surfaces anomalies that raw amounts hide. Grouped on Aadhaar so two farmers who share a name, district and landholding stay separate rows.",
        "expected_empty_on_demo": False,
    },

    "Q095": {
        "abstract_question": 'Do farmers sell the same crop they registered for input subsidy?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT a."aadharno", a."farmername",
       a."cropname"    AS subsidised_crop,
       m."CROP_NAME"   AS procured_crop,
       a."season"      AS subsidy_season,
       m."SEASON"      AS procurement_season
FROM agriculture a
JOIN markfed m ON m."AADHAAR_NO" = a."aadharno"
WHERE UPPER(TRIM(a."cropname")) <> UPPER(TRIM(m."CROP_NAME"))
ORDER BY a."farmername";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Registered crop vs procured crop', 'Crop mismatch between subsidy and procurement'],
        "notes": 'A mismatch may be legitimate crop change, or it may mean the subsidy was drawn against a crop never sown.',
        "expected_empty_on_demo": True,
    },

    "Q096": {
        "abstract_question": 'What irrigation methods are recorded against subsidised farmers?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "irrmethodcode",
       COUNT(*)                                        AS records,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS subsidy
FROM agriculture
GROUP BY "irrmethodcode"
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Irrigation method distribution', 'How are subsidised plots irrigated?'],
        "notes": 'irrmethodcode is a code field; it needs a master lookup to become human readable.',
        "expected_empty_on_demo": False,
    },

    "Q097": {
        "abstract_question": 'Which crops and seasons does the micro-irrigation programme cover?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "CROPNAME", "Crop_Season",
       COUNT(*)                                        AS beneficiaries,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)        AS acres,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)    AS subsidy
FROM horticulture_apmip
GROUP BY "CROPNAME", "Crop_Season"
ORDER BY subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Crop & inputs',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['APMIP crop and season mix', 'Horticulture crop coverage'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q099": {
        "abstract_question": 'How has subsidy spend moved year on year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "cropyear",
       COUNT(DISTINCT "aadharno")                      AS farmers,
       COUNT(*)                                        AS transactions,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS total_subsidy
FROM agriculture
GROUP BY "cropyear"
ORDER BY "cropyear";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Year-wise subsidy trend', 'Crop year comparison'],
        "notes": 'Demo data holds a single crop year; at production scale this becomes the trend line.',
        "expected_empty_on_demo": False,
    },

    # ── Data quality & identity ───────────────────────────────────────────
    "G09-S": {
        "abstract_question": 'Give me a data completeness scorecard by district.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district" AS geography,
       COUNT(*) AS records,
       ROUND(CAST(100.0 * SUM(CASE WHEN "mobile_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_mobile,
       ROUND(CAST(100.0 * SUM(CASE WHEN "bank_account_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_bank,
       ROUND(CAST(100.0 * SUM(CASE WHEN "khata_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_khata,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_ekyc
FROM pm_kisan
GROUP BY "district"
ORDER BY pct_ekyc;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Data quality dashboard', 'Field completeness by area'],
        "notes": 'Run monthly. A falling percentage is usually a data-entry process problem, not a farmer problem.',
        "expected_empty_on_demo": False,
    },

    "G41-S": {
        "abstract_question": 'How many farmers have a different caste category recorded in different departments?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH cats AS (
  SELECT "aadhaar_no" AS aadhaar, UPPER(TRIM("category")) AS cat FROM pm_kisan
  UNION SELECT "aadharno",      UPPER(TRIM("social_status"))   FROM agriculture
  UNION SELECT "EXTN_AADHARNO", UPPER(TRIM("Category"))        FROM horticulture_apmip
  UNION SELECT "aadhar_no",     UPPER(TRIM("social_category")) FROM fisheries
  UNION SELECT "AADHAAR_NO",    UPPER(TRIM("CASTE"))           FROM markfed
  UNION SELECT "Aadhar_no",     UPPER(TRIM("Social_Category")) FROM ryss
)
SELECT c.aadhaar, p."name", p."district", p."sub_district",
       COUNT(DISTINCT c.cat) AS distinct_categories,
       GROUP_CONCAT(DISTINCT c.cat) AS values_found
FROM cats c
JOIN pm_kisan p ON p."aadhaar_no" = c.aadhaar
WHERE c.cat IS NOT NULL
GROUP BY c.aadhaar, p."name", p."district", p."sub_district"
HAVING COUNT(DISTINCT c.cat) > 1
ORDER BY distinct_categories DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + 5 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Caste discrepancies across datasets', 'Conflicting category records'],
        "notes": 'Directly affects reservation-linked targeting. Each conflict needs one authoritative source declared.',
        "expected_empty_on_demo": True,
    },

    "G42-S": {
        "abstract_question": 'Which farmers show a different landholding in PM-KISAN than in MARKFED, once units are converted?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district",
       p."area_hectares" AS pmkisan_ha,
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS pmkisan_converted_acres,
       m."AREA_IN_ACRES" AS markfed_acres,
       ROUND(CAST(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105 AS NUMERIC), 2) AS difference_acres
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105)
      > 0.05 * (p."area_hectares" * 2.47105)
ORDER BY ABS(m."AREA_IN_ACRES" - p."area_hectares" * 2.47105) DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Land amount discrepancies', 'Declared area conflicts after unit conversion'],
        "notes": 'CRITICAL: PM-KISAN is hectares, MARKFED is acres. Convert before comparing or every record looks like a discrepancy. Tolerance is 5%.',
        "expected_empty_on_demo": True,
    },

    "M08": {
        "abstract_question": 'Which Aadhaar numbers have duplicate subsidy draws for the same crop, season and year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "aadharno", "farmername", "cropname", "season", "cropyear",
       COUNT(*)                                        AS records,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS total_drawn
FROM agriculture
GROUP BY "aadharno", "farmername", "cropname", "season", "cropyear"
HAVING COUNT(*) > 1
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Duplicate subsidy draws', 'Same farmer paid twice in one season'],
        "notes": 'SCHEMA NOTE. The demo schema has no transactionid column, so duplicates are detected on Aadhaar + crop + season + year. If production carries a transaction identifier, add it to the GROUP BY — two legitimate transactions for the same crop and season would otherwise be indistinguishable from a duplicate draw.',
        "expected_empty_on_demo": True,
    },

    "Q059": {
        "abstract_question": 'Which farmers receive state scheme benefits but do not appear on the PM-KISAN roster at all?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH ap AS (
  SELECT "aadharno" AS aadhaar, "farmername" AS name, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", "Farmer_Name", 'Horticulture_APMIP' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     "farmer_name", 'Fisheries'   FROM fisheries
  UNION SELECT "aadhaar_no",    "Farmer_Name", 'Sericulture' FROM sericulture
  UNION SELECT "AADHAAR_NO",    "FARMER_NAME", 'MARKFED'     FROM markfed
  UNION SELECT "Aadhar_no",     "FarmerName",  'RySS'        FROM ryss
)
SELECT ap.aadhaar,
       MIN(ap.name)                 AS farmer_name,
       COUNT(DISTINCT ap.scheme)    AS schemes,
       GROUP_CONCAT(DISTINCT ap.scheme) AS scheme_list
FROM ap
WHERE ap.aadhaar NOT IN (SELECT "aadhaar_no" FROM pm_kisan WHERE "aadhaar_no" IS NOT NULL)
GROUP BY ap.aadhaar
ORDER BY schemes DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'All 6 AP schemes vs PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Off-roster beneficiaries', 'Aadhaar numbers absent from PM-KISAN'],
        "notes": 'Not necessarily fraud: tenants, fishers and landless workers legitimately fall outside PM-KISAN. But every one of them should be explainable.',
        "expected_empty_on_demo": False,
    },

    "Q060": {
        "abstract_question": 'For the same Aadhaar, does the farmer name differ between PM-KISAN and MARKFED?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."aadhaar_no",
       p."name"        AS pmkisan_name,
       m."FARMER_NAME" AS markfed_name,
       p."district"
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE UPPER(TRIM(p."name")) <> UPPER(TRIM(m."FARMER_NAME"))
ORDER BY p."district";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Name mismatches across systems', 'Identity inconsistency check'],
        "notes": 'Name mismatch blocks Aadhaar-based payment validation downstream.',
        "expected_empty_on_demo": True,
    },

    "Q061": {
        "abstract_question": 'Is the mobile number for a farmer consistent across all the systems that hold it?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH nums AS (
  SELECT "aadhaar_no" AS aadhaar, CAST("mobile_no" AS TEXT) AS mobile FROM pm_kisan
  UNION SELECT "aadharno",   CAST("mobileno" AS TEXT)   FROM agriculture
  UNION SELECT "aadhar_no",  CAST("mobile_no" AS TEXT)  FROM fisheries
  UNION SELECT "AADHAAR_NO", CAST("MOBILE_NO" AS TEXT)  FROM markfed
)
SELECT n.aadhaar,
       p."name",
       COUNT(DISTINCT n.mobile)   AS distinct_numbers,
       GROUP_CONCAT(DISTINCT n.mobile) AS numbers_on_file
FROM nums n
LEFT JOIN pm_kisan p ON p."aadhaar_no" = n.aadhaar
WHERE n.mobile IS NOT NULL
GROUP BY n.aadhaar, p."name"
HAVING COUNT(DISTINCT n.mobile) > 1
ORDER BY distinct_numbers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Agriculture + Fisheries + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Mobile number mismatch', 'Which contact number is the right one?'],
        "notes": 'Matters operationally: SMS-based grievance and payment alerts go to whichever number the department holds.',
        "expected_empty_on_demo": True,
    },

    "Q062": {
        "abstract_question": 'Is one mobile number registered against several different farmers?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH nums AS (
  SELECT "aadhaar_no" AS aadhaar, CAST("mobile_no" AS TEXT) AS mobile FROM pm_kisan
  UNION SELECT "AADHAAR_NO", CAST("MOBILE_NO" AS TEXT) FROM markfed
)
SELECT mobile,
       COUNT(DISTINCT aadhaar) AS farmers_sharing
FROM nums
WHERE mobile IS NOT NULL
GROUP BY mobile
HAVING COUNT(DISTINCT aadhaar) > 1
ORDER BY farmers_sharing DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Shared mobile numbers', 'Agent or intermediary capture flag'],
        "notes": 'A single number across many farmers often indicates a middleman registering on their behalf.',
        "expected_empty_on_demo": True,
    },

    "Q064": {
        "abstract_question": 'Are there farmers whose recorded gender differs between departments?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH g AS (
  SELECT "aadhaar_no" AS aadhaar, UPPER(TRIM("gender")) AS gender FROM pm_kisan
  UNION SELECT "EXTN_AADHARNO", UPPER(TRIM("Gender")) FROM horticulture_apmip
  UNION SELECT "aadhar_no",     UPPER(TRIM("gender")) FROM fisheries
  UNION SELECT "AADHAAR_NO",    UPPER(TRIM("GENDER")) FROM markfed
  UNION SELECT "Aadhar_no",     UPPER(TRIM("Gender")) FROM ryss
)
SELECT g.aadhaar, p."name",
       COUNT(DISTINCT g.gender)        AS distinct_values,
       GROUP_CONCAT(DISTINCT g.gender) AS values_found
FROM g
LEFT JOIN pm_kisan p ON p."aadhaar_no" = g.aadhaar
WHERE g.gender IS NOT NULL
GROUP BY g.aadhaar, p."name"
HAVING COUNT(DISTINCT g.gender) > 1;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Horticulture + Fisheries + MARKFED + RySS',
        "geo_level": 'State',
        "paraphrases": ['Gender field discrepancies', 'Conflicting gender records'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "Q065": {
        "abstract_question": 'Does the date of birth on record differ across departments for the same farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH d AS (
  SELECT "aadhaar_no" AS aadhaar, SUBSTR(CAST("date_of_birth" AS TEXT), 1, 10) AS dob FROM pm_kisan
  UNION SELECT "AADHAAR_NO", SUBSTR(CAST("DATE_OF_BIRTH" AS TEXT), 1, 10) FROM markfed
  UNION SELECT "Aadhar_no",  SUBSTR(CAST("DOB" AS TEXT), 1, 10)           FROM ryss
)
SELECT d.aadhaar, p."name",
       COUNT(DISTINCT d.dob)        AS distinct_dobs,
       GROUP_CONCAT(DISTINCT d.dob) AS values_found
FROM d
LEFT JOIN pm_kisan p ON p."aadhaar_no" = d.aadhaar
WHERE d.dob IS NOT NULL
GROUP BY d.aadhaar, p."name"
HAVING COUNT(DISTINCT d.dob) > 1;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED + RySS',
        "geo_level": 'State',
        "paraphrases": ['DOB mismatches', 'Age record inconsistency'],
        "notes": 'DOB drives age-based eligibility; a mismatch can wrongly include or exclude someone.',
        "expected_empty_on_demo": True,
    },

    "Q066": {
        "abstract_question": 'Do ration card numbers match across departments for the same farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH r AS (
  SELECT "aadhaar_no" AS aadhaar, UPPER(TRIM(CAST("ration_card_no" AS TEXT))) AS rc FROM pm_kisan
  UNION SELECT "aadhar_no",  UPPER(TRIM(CAST("ration_card_number" AS TEXT)))  FROM fisheries
  UNION SELECT "AADHAAR_NO", UPPER(TRIM(CAST("RATION_CARD_NUMBER" AS TEXT)))  FROM markfed
  UNION SELECT "Aadhar_no",  UPPER(TRIM(CAST("Ration_card_number" AS TEXT)))  FROM ryss
)
SELECT r.aadhaar, p."name",
       COUNT(DISTINCT r.rc)        AS distinct_cards,
       GROUP_CONCAT(DISTINCT r.rc) AS values_found
FROM r
LEFT JOIN pm_kisan p ON p."aadhaar_no" = r.aadhaar
WHERE r.rc IS NOT NULL AND r.rc <> ''
GROUP BY r.aadhaar, p."name"
HAVING COUNT(DISTINCT r.rc) > 1;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Fisheries + MARKFED + RySS',
        "geo_level": 'State',
        "paraphrases": ['Ration card mismatches', 'Household identifier inconsistency'],
        "notes": 'Ration card is the usual fallback key when Aadhaar is masked or encrypted.',
        "expected_empty_on_demo": True,
    },

    "Q068": {
        "abstract_question": 'Does any Aadhaar appear more than once for the same crop, season and year in the input subsidy data?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "aadharno", "farmername", "cropname", "season", "cropyear",
       COUNT(*)                                        AS records,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2) AS total_drawn
FROM agriculture
GROUP BY "aadharno", "farmername", "cropname", "season", "cropyear"
HAVING COUNT(*) > 1
ORDER BY records DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Duplicate subsidy draws', 'Same farmer paid twice in one season'],
        "notes": 'Duplicate-draw check. An empty result is the correct answer when the data is clean.',
        "expected_empty_on_demo": True,
    },

    "Q069": {
        "abstract_question": 'Which records are missing a district, so they cannot be assigned to any officer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PM-KISAN' AS dataset, COUNT(*) AS missing_district FROM pm_kisan WHERE "district" IS NULL OR TRIM("district") = ''
UNION ALL SELECT 'Horticulture_APMIP', COUNT(*) FROM horticulture_apmip WHERE "DISTRICT" IS NULL OR TRIM("DISTRICT") = ''
UNION ALL SELECT 'Fisheries', COUNT(*) FROM fisheries WHERE "district" IS NULL OR TRIM("district") = ''
UNION ALL SELECT 'MARKFED', COUNT(*) FROM markfed WHERE "DIST_NAME" IS NULL OR TRIM("DIST_NAME") = ''
UNION ALL SELECT 'RySS', COUNT(*) FROM ryss WHERE "district" IS NULL OR TRIM("district") = ''
ORDER BY missing_district DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + Horticulture + Fisheries + MARKFED + RySS',
        "geo_level": 'State',
        "paraphrases": ['Records with no geography', 'Unassignable records'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q070": {
        "abstract_question": 'Sericulture only stores district codes. Which district does each sericulture farmer actually belong to?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT s."DIST_CODE",
       COALESCE(p."district", '(unresolved)') AS district_name,
       COUNT(*)                                        AS farmers,
       ROUND(CAST(SUM(s."Net_Incentive") AS NUMERIC), 2) AS total_incentive
FROM sericulture s
LEFT JOIN pm_kisan p ON p."aadhaar_no" = s."aadhaar_no"
GROUP BY s."DIST_CODE", p."district"
ORDER BY farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'Sericulture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Resolve sericulture district codes to names', 'Geography harmonisation for silk data'],
        "notes": "Sericulture carries DIST_CODE with no name. Resolve via the farmer's Aadhaar on the PM-KISAN spine, or via a code-to-name master.",
        "expected_empty_on_demo": False,
    },

    "Q071": {
        "abstract_question": 'Does the eKYC status in MARKFED agree with the PM-KISAN roster?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district",
       p."ekyc_status" AS pmkisan_ekyc,
       m."EKYC_STATUS" AS markfed_ekyc
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE UPPER(TRIM(CAST(p."ekyc_status" AS TEXT))) <> UPPER(TRIM(CAST(m."EKYC_STATUS" AS TEXT)))
ORDER BY p."district", p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['eKYC status conflicts', 'Which system says the farmer is verified?'],
        "notes": 'Conflicting verification status is a common cause of stuck payments.',
        "expected_empty_on_demo": False,
    },

    "Q073": {
        "abstract_question": 'Are there beneficiaries with zero or missing land area recorded?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "area_hectares", "khata_no"
FROM pm_kisan
WHERE "area_hectares" IS NULL OR "area_hectares" <= 0
ORDER BY "district";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Records with no land', 'Zero-area beneficiaries'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "Q074": {
        "abstract_question": 'In how many cases is the recorded cultivator different from the pattadar (land title holder)?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "aadharno", "farmername" AS cultivator, "pattadarname" AS pattadar,
       "surveyno", "khatano", "cropname", "season"
FROM agriculture
WHERE UPPER(TRIM("farmername")) <> UPPER(TRIM("pattadarname"))
ORDER BY "farmername";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Data quality & identity',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Tenancy signal', 'Cultivator not the same as land owner'],
        "notes": 'A tenancy indicator: benefits flowing to a cultivator who does not hold title, or vice versa.',
        "expected_empty_on_demo": True,
    },

    "Q075": {
        "abstract_question": 'Survey records carry no Aadhaar. Which land parcels cannot be matched to a PM-KISAN farmer by name and village?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT s."pattadar_name", s."village", s."mandal", s."dist_name",
       s."khata_no", s."surveyno", s."extent"
FROM survey_land_records s
LEFT JOIN pm_kisan p
       ON UPPER(TRIM(p."name"))    = UPPER(TRIM(s."pattadar_name"))
      AND UPPER(TRIM(p."village")) = UPPER(TRIM(s."village"))
WHERE p."aadhaar_no" IS NULL
ORDER BY s."dist_name", s."village";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Data quality & identity',
        "datasets": 'Survey_Land_Records + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Unmatched land records', 'Parcels with no linked beneficiary'],
        "notes": 'Survey_Land_Records has no Aadhaar, so it joins on pattadar name + village + khata. That match is fuzzy by nature; treat misses as a review queue, not as errors.',
        "expected_empty_on_demo": True,
    },

    # ── Exclusion & leakage ───────────────────────────────────────────────
    "G37-S": {
        "abstract_question": 'Which farmers have eKYC pending but are still receiving benefits?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status",
       COUNT(DISTINCT s.scheme) AS schemes_receiving,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
WHERE p."ekyc_status" = 'Pending'
GROUP BY p."name", p."district", p."sub_district", p."ekyc_status", p."beneficiary_status"
ORDER BY schemes_receiving DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Unverified farmers receiving money', 'Verification gap'],
        "notes": 'Money moving to identities the system has not confirmed.',
        "expected_empty_on_demo": False,
    },

    "G38-S": {
        "abstract_question": 'Which farmers receive land-linked benefits but have no land record?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
WHERE NOT EXISTS (
        SELECT 1 FROM survey_land_records s
        WHERE UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
          AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village")))
GROUP BY p."name", p."district", p."sub_district", p."village", p."khata_no", p."area_hectares"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Survey_Land_Records + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Benefits without land records', 'Unverifiable entitlements'],
        "notes": 'Land-linked subsidies with no revenue record behind them are the highest-risk category in the portfolio.',
        "expected_empty_on_demo": True,
    },

    "G39-S": {
        "abstract_question": 'Give me a district scorecard: farmers, land, subsidy and procurement in one view.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district" AS geography,
       COUNT(DISTINCT p."aadhaar_no") AS farmers,
       ROUND(CAST(SUM(p."area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(SUM(m."AMOUNT_PAID"), 0) AS NUMERIC), 2) AS procurement_value
FROM pm_kisan p
LEFT JOIN agriculture a ON a."aadharno"   = p."aadhaar_no"
LEFT JOIN markfed m     ON m."AADHAAR_NO" = p."aadhaar_no"
GROUP BY p."district"
ORDER BY input_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Area scorecard', 'One-page comparison across departments'],
        "notes": 'The standing review-meeting table. Each column comes from a different department, joined on the spine.',
        "expected_empty_on_demo": False,
    },

    "G44-S": {
        "abstract_question": 'Which large landholders still receive subsidies meant to be pro-poor?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."category", p."area_hectares",
       ROUND(CAST(COALESCE(SUM(a."subsidyamount"), 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(MAX(h."SubsidyAmt"), 0) AS NUMERIC), 2) AS horticulture_subsidy
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
WHERE p."area_hectares" > 2
GROUP BY p."name", p."district", p."sub_district", p."category", p."area_hectares"
HAVING COALESCE(SUM(a."subsidyamount"), 0) + COALESCE(MAX(h."SubsidyAmt"), 0) > 0
ORDER BY p."area_hectares" DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + Agriculture + Horticulture',
        "geo_level": 'State',
        "paraphrases": ['Large farmers in targeted schemes', 'Support flowing upward'],
        "notes": 'The 2 ha threshold is the common small-farmer ceiling; set it to whatever the scheme guidelines actually specify.',
        "expected_empty_on_demo": False,
    },

    "M06": {
        "abstract_question": 'Are there land records whose pattadar is not on the PM-KISAN roster?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT s."pattadar_name", s."dist_name", s."mandal", s."village",
       s."khata_no", s."surveyno",
       ROUND(CAST(s."extent" AS NUMERIC), 2) AS extent_acres,
       s."current_status"
FROM survey_land_records s
WHERE NOT EXISTS (
        SELECT 1 FROM pm_kisan p
        WHERE UPPER(TRIM(p."name"))    = UPPER(TRIM(s."pattadar_name"))
          AND UPPER(TRIM(p."village")) = UPPER(TRIM(s."village")))
ORDER BY extent_acres DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'Survey_Land_Records + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Land records with no rostered farmer', 'Pattadars missing from PM-KISAN'],
        "notes": 'The reverse of the usual exclusion check: land exists, but the holder is not receiving PM-KISAN. Some are legitimate (institutional or absentee holders); the rest are potential exclusion errors.',
        "expected_empty_on_demo": True,
    },

    "Q128": {
        "abstract_question": "Are any farmers whose beneficiary status is not 'Included' still drawing benefits?",
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
)
SELECT p."name", p."district", p."beneficiary_status",
       COUNT(DISTINCT s.scheme)        AS schemes_receiving,
       GROUP_CONCAT(DISTINCT s.scheme) AS scheme_list
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
WHERE p."beneficiary_status" <> 'Included'
GROUP BY p."name", p."district", p."beneficiary_status"
ORDER BY schemes_receiving DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Excluded farmers still being paid', 'Status says stop, payments say go'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q129": {
        "abstract_question": 'How much money in total has gone to Aadhaar numbers that are not on the PM-KISAN roster?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", 'Horticulture', "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     'Fisheries',    "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    'Sericulture',  "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    'MARKFED',      "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     'RySS',         "Amount"        FROM ryss
)
SELECT scheme,
       COUNT(DISTINCT aadhaar)                  AS off_roster_farmers,
       ROUND(CAST(SUM(amount) AS NUMERIC), 2)   AS amount_paid
FROM benefits
WHERE aadhaar NOT IN (SELECT "aadhaar_no" FROM pm_kisan WHERE "aadhaar_no" IS NOT NULL)
GROUP BY scheme
ORDER BY amount_paid DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'All 6 AP schemes vs PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Value of off-roster payments', 'Money paid outside the master list'],
        "notes": 'Quantifies the exposure from Q059. Some of it will be legitimate (tenants, landless fishers) — the point is to size it and explain it.',
        "expected_empty_on_demo": False,
    },

    "Q131": {
        "abstract_question": 'Which villages show an unusually high concentration of benefits per farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH benefits AS (
  SELECT "aadharno" AS aadhaar, "subsidyamount" AS amount FROM agriculture
  UNION ALL SELECT "EXTN_AADHARNO", "SubsidyAmt"    FROM horticulture_apmip
  UNION ALL SELECT "aadhar_no",     "amount_paid"   FROM fisheries
  UNION ALL SELECT "aadhaar_no",    "Net_Incentive" FROM sericulture
  UNION ALL SELECT "AADHAAR_NO",    "AMOUNT_PAID"   FROM markfed
  UNION ALL SELECT "Aadhar_no",     "Amount"        FROM ryss  UNION ALL SELECT "aadhaar_no",    "last_amount_credited" FROM pm_kisan
)
SELECT p."district", p."village",
       COUNT(DISTINCT p."aadhaar_no")                                          AS farmers,
       ROUND(CAST(SUM(b.amount) AS NUMERIC), 2)                                AS total_benefit,
       ROUND(CAST(SUM(b.amount) / COUNT(DISTINCT p."aadhaar_no") AS NUMERIC), 2) AS benefit_per_farmer
FROM pm_kisan p
JOIN benefits b ON b.aadhaar = p."aadhaar_no"
GROUP BY p."district", p."village"
ORDER BY benefit_per_farmer DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'All 6 AP schemes + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Benefit concentration by village', 'Where is money clustering?'],
        "notes": 'Concentration is not proof of anything, but a village far above its district peers is where an inspection should start.',
        "expected_empty_on_demo": False,
    },

    "Q132": {
        "abstract_question": 'Which sanctions are approved on paper but have seen no money move?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal",
       "Status",
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2)                 AS sanctioned,
       ROUND(CAST("Subsidy_Rlsd" AS NUMERIC), 2)               AS released,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2)  AS balance
FROM horticulture_apmip
WHERE "Status" = 'Approved'
  AND "BALANCE_AMOUNT_TO_RELEASE" > 0
ORDER BY balance DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Approved but unpaid', 'Process completion gap'],
        "notes": 'Separates a documentation problem from a treasury problem. Both need different fixes.',
        "expected_empty_on_demo": False,
    },

    "Q134": {
        "abstract_question": 'Give me a one-page integrity dashboard: how many records fail each of our standard checks?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Off-roster beneficiaries (Aadhaar not in PM-KISAN)' AS check_name,
       (SELECT COUNT(DISTINCT aadhaar) FROM (
          SELECT "aadharno" AS aadhaar FROM agriculture
          UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
          UNION SELECT "aadhar_no"     FROM fisheries
          UNION SELECT "aadhaar_no"    FROM sericulture
          UNION SELECT "AADHAAR_NO"    FROM markfed
          UNION SELECT "Aadhar_no"     FROM ryss) x
        WHERE aadhaar NOT IN (SELECT "aadhaar_no" FROM pm_kisan)) AS record_count
UNION ALL
SELECT 'PM-KISAN farmers with eKYC pending',
       (SELECT COUNT(*) FROM pm_kisan WHERE "ekyc_status" = 'Pending')
UNION ALL
SELECT 'PM-KISAN farmers not marked Included',
       (SELECT COUNT(*) FROM pm_kisan WHERE "beneficiary_status" <> 'Included')
UNION ALL
SELECT 'Bank accounts shared by more than one farmer',
       (SELECT COUNT(*) FROM (SELECT "bank_account_no" FROM pm_kisan
        GROUP BY "bank_account_no" HAVING COUNT(DISTINCT "aadhaar_no") > 1) y)
UNION ALL
SELECT 'MARKFED payments not approved',
       (SELECT COUNT(*) FROM markfed WHERE "PAYMENT_STATUS" <> 'Approved')
UNION ALL
SELECT 'Horticulture sanctions with nothing released',
       (SELECT COUNT(*) FROM horticulture_apmip WHERE "BALANCE_AMOUNT_TO_RELEASE" >= "SubsidyAmt")
UNION ALL
SELECT 'Land records not approved',
       (SELECT COUNT(*) FROM survey_land_records WHERE "current_status" <> 'Approved')
UNION ALL
SELECT 'PM-KISAN khatas absent from land records',
       (SELECT COUNT(*) FROM pm_kisan WHERE CAST("khata_no" AS TEXT) NOT IN
         (SELECT CAST("khata_no" AS TEXT) FROM survey_land_records))
ORDER BY record_count DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'All 8',
        "geo_level": 'State',
        "paraphrases": ['Data integrity scorecard', 'All red flags in one view'],
        "notes": 'Run this before every review meeting. A rising count on any line is the signal; the detail queries then tell you where.',
        "expected_empty_on_demo": False,
    },

    "Q135": {
        "abstract_question": 'Which fisheries registrants are not on the PM-KISAN roster?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT f."aadhar_no", f."farmer_name", f."district", f."mandal",
       ROUND(CAST(f."amount_paid" AS NUMERIC), 2) AS amount_paid,
       f."fcs_registration_no"
FROM fisheries f
WHERE f."aadhar_no" NOT IN (SELECT "aadhaar_no" FROM pm_kisan WHERE "aadhaar_no" IS NOT NULL)
ORDER BY amount_paid DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'Fisheries + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Fisheries beneficiaries outside PM-KISAN', 'Landless fishers and other exceptions'],
        "notes": 'Expected to be non-empty and legitimate: fishers often hold no agricultural land, so PM-KISAN never covers them.',
        "expected_empty_on_demo": False,
    },

    # ── Geography & performance ───────────────────────────────────────────
    "G40-S": {
        "abstract_question": 'List every farmer and what they have received across schemes.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       p."category", p."gender", p."area_hectares", p."ekyc_status",
       ROUND(CAST(COALESCE(a."subsidyamount", 0) AS NUMERIC), 2) AS input_subsidy,
       ROUND(CAST(COALESCE(h."SubsidyAmt", 0) AS NUMERIC), 2) AS horticulture_subsidy,
       ROUND(CAST(COALESCE(m."AMOUNT_PAID", 0) AS NUMERIC), 2) AS procurement_payment
FROM pm_kisan p
LEFT JOIN agriculture a        ON a."aadharno"      = p."aadhaar_no"
LEFT JOIN horticulture_apmip h ON h."EXTN_AADHARNO" = p."aadhaar_no"
LEFT JOIN markfed m            ON m."AADHAAR_NO"    = p."aadhaar_no"
ORDER BY p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Mandal AO / RBK',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + Agriculture + Horticulture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Beneficiary register', 'Everything happening in one area'],
        "notes": 'The RBK-level working list. At state scope this returns the full roster, so expect it to be used at mandal scope in practice.',
        "expected_empty_on_demo": False,
    },

    "G43-S": {
        "abstract_question": 'What share of farmland is under natural farming, district by district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district" AS geography,
       ROUND(CAST(SUM(p."area_hectares") * 2.47105 AS NUMERIC), 2) AS total_farmland_acres,
       ROUND(CAST(COALESCE(SUM(r."ACREAGE"), 0) AS NUMERIC), 2) AS natural_farming_acres,
       ROUND(CAST(100.0 * COALESCE(SUM(r."ACREAGE"), 0) / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 1) AS pct_under_nf
FROM pm_kisan p
LEFT JOIN ryss r ON r."Aadhar_no" = p."aadhaar_no"
GROUP BY p."district"
ORDER BY pct_under_nf DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Geography & performance',
        "datasets": 'RySS + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Natural farming penetration', 'APCNF share of farmland'],
        "notes": 'PM-KISAN area is converted from hectares to acres to match RySS. Shares near 100% in the demo data reflect the sample, not reality.',
        "expected_empty_on_demo": False,
    },

    "Q138": {
        "abstract_question": 'Which districts have the worst eKYC completion rate?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "district",
       COUNT(*)                                                    AS farmers,
       SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) AS completed,
       ROUND(CAST(100.0 * SUM(CASE WHEN "ekyc_status" = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_complete
FROM pm_kisan
GROUP BY "district"
ORDER BY pct_complete;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['eKYC completion ranking', 'Worst-performing districts on verification'],
        "notes": 'Rate, not count — a big district will always top a raw count and that misdirects the review.',
        "expected_empty_on_demo": False,
    },

    "Q139": {
        "abstract_question": 'Which districts get the most subsidy per acre of farmland?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district",
       ROUND(CAST(SUM(p."area_hectares") * 2.47105 AS NUMERIC), 2)    AS acres,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2)              AS subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 2) AS subsidy_per_acre
FROM pm_kisan p
JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
GROUP BY p."district"
ORDER BY subsidy_per_acre DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Subsidy intensity by district', 'Per-acre allocation across districts'],
        "notes": 'Per-acre normalisation makes districts of different sizes comparable.',
        "expected_empty_on_demo": False,
    },

    "Q140": {
        "abstract_question": 'Build me a district code to district name crosswalk from the data we already hold.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT DISTINCT a."dcode" AS district_code,
       p."district"           AS district_name
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."dcode" IS NOT NULL
ORDER BY district_code;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Data / MIS',
        "theme": 'Geography & performance',
        "datasets": 'Agriculture + PM-KISAN + Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Geography harmonisation table', 'Map district codes to names'],
        "notes": 'Some datasets store codes, others names. Build this crosswalk once and reuse it, rather than re-deriving it in every query.',
        "expected_empty_on_demo": False,
    },

    "Q142": {
        "abstract_question": 'Which mandals have PM-KISAN farmers but no micro-irrigation beneficiary?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district", p."sub_district" AS mandal,
       COUNT(*) AS pmkisan_farmers
FROM pm_kisan p
WHERE p."sub_district" NOT IN (SELECT "Mandal" FROM horticulture_apmip WHERE "Mandal" IS NOT NULL)
GROUP BY p."district", p."sub_district"
ORDER BY pmkisan_farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Mandals with zero APMIP coverage', 'Sub-district white space'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "R04": {
        "abstract_question": 'Which district recorded the highest single input subsidy payment?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district",
       MAX(ROUND(CAST(a."subsidyamount" AS NUMERIC), 2)) AS highest_single_subsidy,
       COUNT(*)                                          AS transactions,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS district_total
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
GROUP BY p."district"
ORDER BY highest_single_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Geography & performance',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Largest single subsidy by district', 'Peak transaction per district'],
        "notes": 'The maximum single transaction, not the district total — useful for spotting an outlier payment that a total would hide.',
        "expected_empty_on_demo": False,
    },

    "S05": {
        "abstract_question": 'Which district has the most total scheme participations?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
)
SELECT p."district",
       COUNT(DISTINCT p."aadhaar_no") AS farmers,
       COUNT(*)                        AS total_participations,
       ROUND(CAST(COUNT(*) * 1.0 / COUNT(DISTINCT p."aadhaar_no") AS NUMERIC), 2) AS participations_per_farmer
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
GROUP BY p."district"
ORDER BY total_participations DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Geography & performance',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Total participations by district', 'Where is scheme activity concentrated'],
        "notes": 'Counts participations, not farmers: one farmer in four schemes contributes four. Compare against the farmer count in the same row to see whether a district is broad or deep.',
        "expected_empty_on_demo": False,
    },

    # ── Land & records ────────────────────────────────────────────────────
    "G32-S": {
        "abstract_question": 'How much land is on record in each district?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "dist_name" AS geography,
       COUNT(*) AS parcels,
       COUNT(DISTINCT "khata_no") AS khatas,
       ROUND(CAST(SUM("extent") AS NUMERIC), 2) AS total_extent_acres,
       ROUND(CAST(AVG("extent") AS NUMERIC), 2) AS avg_parcel_acres
FROM survey_land_records
WHERE "ulpin_generation_date" IS NOT NULL
GROUP BY "dist_name"
ORDER BY total_extent_acres DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Land record coverage', 'Surveyed extent by area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G33-S": {
        "abstract_question": 'Which land records are not yet approved?',
        "date_filter": {"alias": '', "column": 'ulpin_generation_date'},
        "date_kind": 'iso',  # ULPIN generation date
        "sql_template": """
SELECT "dist_name", "mandal", "village", "pattadar_name",
       "khata_no", "surveyno",
       ROUND(CAST("extent" AS NUMERIC), 2) AS extent_acres,
       "current_status"
FROM survey_land_records
WHERE "current_status" <> 'Approved'
ORDER BY extent_acres DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Mutation pendency', 'Land awaiting clearance'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "M09": {
        "abstract_question": 'Which survey numbers show a pattadar different from the recorded cultivator?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT a."surveyno", a."farmername" AS cultivator, a."pattadarname" AS pattadar_in_agriculture,
       s."pattadar_name" AS pattadar_in_land_records, s."village", s."dist_name",
       ROUND(CAST(s."extent" AS NUMERIC), 2) AS extent_acres
FROM agriculture a
LEFT JOIN survey_land_records s ON CAST(s."surveyno" AS TEXT) = CAST(a."surveyno" AS TEXT)
WHERE UPPER(TRIM(a."farmername")) <> UPPER(TRIM(a."pattadarname"))
   OR (s."pattadar_name" IS NOT NULL
       AND UPPER(TRIM(s."pattadar_name")) <> UPPER(TRIM(a."pattadarname")))
ORDER BY a."surveyno";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'Agriculture + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Tenancy signal by survey number', 'Cultivator is not the title holder'],
        "notes": 'A tenancy indicator. Benefits flowing to a cultivator who holds no title, or to a title holder who does not farm, are both worth knowing before an area-linked sanction.',
        "expected_empty_on_demo": True,
    },

    "Q077": {
        "abstract_question": 'What is the total extent recorded against each khata, village by village?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "dist_name", "mandal", "village", "khata_no", "surveyno",
       "pattadar_name",
       ROUND(CAST("extent" AS NUMERIC), 2) AS extent_acres,
       "current_status"
FROM survey_land_records
ORDER BY "dist_name", "village", "khata_no";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Khata-wise land extent', 'Land holdings by village'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q078": {
        "abstract_question": 'Which PM-KISAN khata numbers have no matching entry in the land records?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."sub_district", p."village",
       p."khata_no", p."area_hectares"
FROM pm_kisan p
WHERE p."khata_no" IS NOT NULL
  AND CAST(p."khata_no" AS TEXT) NOT IN (
        SELECT CAST("khata_no" AS TEXT) FROM survey_land_records WHERE "khata_no" IS NOT NULL)
ORDER BY p."district";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Unverified khatas', 'PM-KISAN land claims with no revenue record'],
        "notes": 'A PM-KISAN entry whose khata does not exist in revenue records is the sharpest single exclusion/inclusion-error flag available.',
        "expected_empty_on_demo": True,
    },

    "Q079": {
        "abstract_question": 'Is the same survey number claimed by more than one person across our systems?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH claims AS (
  SELECT CAST("surveyno" AS TEXT) AS survey_no, UPPER(TRIM("farmername"))   AS claimant, 'Agriculture' AS src FROM agriculture
  UNION SELECT CAST("surveyno" AS TEXT), UPPER(TRIM("pattadar_name")), 'Survey_Land_Records' FROM survey_land_records
)
SELECT survey_no,
       COUNT(DISTINCT claimant)        AS distinct_claimants,
       GROUP_CONCAT(DISTINCT claimant) AS claimants
FROM claims
WHERE survey_no IS NOT NULL
GROUP BY survey_no
HAVING COUNT(DISTINCT claimant) > 1
ORDER BY distinct_claimants DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'Agriculture + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Contested survey numbers', 'Duplicate land claims'],
        "notes": 'Overlapping claims on one survey number indicate either subdivision not yet recorded, or a duplicate benefit claim.',
        "expected_empty_on_demo": True,
    },

    "Q081": {
        "abstract_question": "Compare each farmer's declared PM-KISAN area against the extent in the land records.",
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district", p."village",
       p."area_hectares",
       ROUND(CAST(p."area_hectares" * 2.47105 AS NUMERIC), 2) AS declared_acres,
       ROUND(CAST(s."extent" AS NUMERIC), 2)                  AS surveyed_acres,
       ROUND(CAST(p."area_hectares" * 2.47105 - s."extent" AS NUMERIC), 2) AS difference_acres
FROM pm_kisan p
JOIN survey_land_records s
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(p."name"))
 AND UPPER(TRIM(s."village"))       = UPPER(TRIM(p."village"))
ORDER BY ABS(p."area_hectares" * 2.47105 - s."extent") DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Declared vs surveyed land', 'Land verification per farmer'],
        "notes": 'PM-KISAN is in hectares, survey records in acres. Convert first. Match is on name + village because survey records carry no Aadhaar.',
        "expected_empty_on_demo": False,
    },

    "Q083": {
        "abstract_question": 'How many land records are stuck in pending or under-review status?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "current_status",
       COUNT(*)                                 AS parcels,
       ROUND(CAST(SUM("extent") AS NUMERIC), 2) AS extent_acres
FROM survey_land_records
WHERE "current_status" <> 'Approved'
GROUP BY "current_status"
ORDER BY parcels DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Land & records',
        "datasets": 'Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Mutation pendency', 'Land records awaiting approval'],
        "notes": "\"Stuck\" is a pendency question, so Approved is excluded by definition; the GROUP BY keeps Pending and Under Review as separate rows.",
        "expected_empty_on_demo": False,
    },

    "Q084": {
        "abstract_question": 'For each village, how does the number of beneficiaries compare with the land on record?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH land AS (
  SELECT UPPER(TRIM("village")) AS village, SUM("extent") AS extent_acres
  FROM survey_land_records GROUP BY UPPER(TRIM("village"))
),
ben AS (
  SELECT UPPER(TRIM("village")) AS village, COUNT(*) AS beneficiaries,
         SUM("area_hectares") * 2.47105 AS declared_acres
  FROM pm_kisan GROUP BY UPPER(TRIM("village"))
)
SELECT b.village, b.beneficiaries,
       ROUND(CAST(b.declared_acres AS NUMERIC), 2) AS declared_acres,
       ROUND(CAST(l.extent_acres AS NUMERIC), 2)   AS recorded_acres,
       ROUND(CAST(b.declared_acres / NULLIF(l.extent_acres, 0) AS NUMERIC), 2) AS declared_to_recorded_ratio
FROM ben b
LEFT JOIN land l ON l.village = b.village
ORDER BY declared_to_recorded_ratio DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Mandal AO / RBK',
        "theme": 'Land & records',
        "datasets": 'PM-KISAN + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['Village saturation vs land base', 'Beneficiaries per acre by village'],
        "notes": 'A high beneficiary count against a small land base suggests either fragmentation or over-registration.',
        "expected_empty_on_demo": False,
    },

    "Q085": {
        "abstract_question": 'Does the land extent claimed for micro-irrigation subsidy match the revenue record?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT h."Farmer_Name", h."DISTRICT", h."Village_Name",
       ROUND(CAST(h."EXTENT" AS NUMERIC), 2)  AS horticulture_acres,
       ROUND(CAST(s."extent" AS NUMERIC), 2)  AS surveyed_acres,
       ROUND(CAST(h."EXTENT" - s."extent" AS NUMERIC), 2) AS difference_acres,
       ROUND(CAST(h."SubsidyAmt" AS NUMERIC), 2) AS subsidy
FROM horticulture_apmip h
JOIN survey_land_records s
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(h."Farmer_Name"))
ORDER BY ABS(h."EXTENT" - s."extent") DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Land & records',
        "datasets": 'Horticulture_APMIP + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['APMIP extent verification', 'Subsidised area vs recorded area'],
        "notes": 'Both are in acres, so no conversion needed. Subsidy is often proportional to area, which makes over-statement financially material.',
        "expected_empty_on_demo": False,
    },

    "Q086": {
        "abstract_question": 'How much of the micro-irrigation coverage is on dry land versus total land?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "DISTRICT",
       COUNT(*)                                          AS beneficiaries,
       ROUND(CAST(SUM("Dry_Land") AS NUMERIC), 2)        AS dry_land,
       ROUND(CAST(SUM("TotalLandAcres") AS NUMERIC), 2)  AS total_land_acres,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)          AS covered_extent
FROM horticulture_apmip
GROUP BY "DISTRICT"
ORDER BY covered_extent DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Land & records',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Dry land share under APMIP', 'Is micro-irrigation reaching rainfed areas?'],
        "notes": 'Micro-irrigation on dry land is the higher-value intervention; the split tells you whether targeting is right.',
        "expected_empty_on_demo": False,
    },

    "Q087": {
        "abstract_question": 'Does the acreage claimed under natural farming match the recorded land extent?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT r."FarmerName", r."district", r."Village_name",
       ROUND(CAST(r."ACREAGE" AS NUMERIC), 2) AS ryss_acreage,
       ROUND(CAST(s."extent" AS NUMERIC), 2)  AS surveyed_acres,
       ROUND(CAST(r."ACREAGE" - s."extent" AS NUMERIC), 2) AS difference_acres
FROM ryss r
JOIN survey_land_records s
  ON UPPER(TRIM(s."pattadar_name")) = UPPER(TRIM(r."FarmerName"))
ORDER BY ABS(r."ACREAGE" - s."extent") DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Land & records',
        "datasets": 'RySS + Survey_Land_Records',
        "geo_level": 'State',
        "paraphrases": ['APCNF acreage verification', 'Natural farming area vs land records'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    # ── Payments & DBT ────────────────────────────────────────────────────
    "G07-S": {
        "abstract_question": 'How much DBT was credited, district by district?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "district" AS geography,
       COUNT(*) AS farmers_paid,
       ROUND(CAST(SUM("last_amount_credited") AS NUMERIC), 2) AS total_credited,
       MAX("last_installment_no") AS latest_installment
FROM pm_kisan
WHERE "last_amount_credited" IS NOT NULL
GROUP BY "district"
ORDER BY total_credited DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['DBT disbursement by area', 'Money released'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G08-S": {
        "abstract_question": 'Which farmers have missed the most recent installment?',
        "date_filter": {"alias": '', "column": 'last_installment_date'},
        "date_kind": 'iso',  # installment date
        "sql_template": """
SELECT "name", "district", "sub_district", "village",
       "last_installment_no", "last_installment_date", "ekyc_status", "mobile_no"
FROM pm_kisan
WHERE "last_installment_no" < (SELECT MAX("last_installment_no") FROM pm_kisan)
ORDER BY "last_installment_no";
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Farmers behind on installments', 'Missed DBT list'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "G16-S": {
        "abstract_question": 'Which farmers delivered produce but have not been paid?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE",
       COUNT(*)                                       AS unpaid_deliveries,
       STRING_AGG(DISTINCT "CROP_NAME", ', ')         AS crops,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS amount_awaiting_payment,
       STRING_AGG(DISTINCT "PAYMENT_STATUS", ', ')    AS payment_statuses,
       MAX("PROCUREMENT_DATE")                        AS latest_delivery,
       MAX("MOBILE_NO")                               AS mobile_no
FROM markfed
WHERE "PAYMENT_STATUS" <> 'Approved'
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "FARMER_VILLAGE"
ORDER BY amount_awaiting_payment DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Procured but unpaid', 'Pending MSP payments'],
        "notes": "Field-actionable list; mobile number included for grievance follow-up. One row per farmer (grouped on Aadhaar) — markfed is transactional (1086 rows over 646 suppliers), so the delivery detail is aggregated rather than fanned out. amount_awaiting_payment is the recorded AMOUNT_PAID on unpaid deliveries — the claim value, not money received.",
        "expected_empty_on_demo": False,
    },

    "G17-S": {
        "abstract_question": 'How much procurement payment is stuck, district by district?',
        "date_filter": {"alias": '', "column": 'PAYMENT_DATE'},
        "date_kind": 'iso',  # payment date
        "sql_template": """
SELECT "DIST_NAME" AS geography,
       COUNT(*) AS transactions,
       SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN 1 ELSE 0 END) AS pending_transactions,
       ROUND(CAST(SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) AS NUMERIC), 2) AS pending_value,
       ROUND(CAST(100.0 * SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) / NULLIF(SUM("AMOUNT_PAID"), 0) AS NUMERIC), 1) AS pct_pending
FROM markfed
WHERE "PAYMENT_DATE" IS NOT NULL
GROUP BY "DIST_NAME"
ORDER BY pending_value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Payment pendency by area', 'Where is procurement money stuck?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G22-S": {
        "abstract_question": 'Which micro-irrigation sanctions have seen no money released?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal", "Village_Name",
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2) AS sanctioned,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2) AS pending,
       "Status", "BENEFICIARYMOBILE"
FROM horticulture_apmip
WHERE "BALANCE_AMOUNT_TO_RELEASE" >= "SubsidyAmt"
ORDER BY pending DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Stalled APMIP sanctions', 'Sanctioned but unpaid'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G26-S": {
        "abstract_question": 'What is the payment status position in fisheries?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT "payment_status",
       COUNT(*) AS records,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2) AS total_amount
FROM fisheries
WHERE "fcs_registration_date" IS NOT NULL
GROUP BY "payment_status"
ORDER BY total_amount DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Payments & DBT',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ['Fisheries payment pendency', 'Unpaid fisheries claims'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "M04": {
        "abstract_question": 'What is sanctioned versus released versus pending for each micro-irrigation beneficiary?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Farmer_Name", "DISTRICT", "Mandal", "Status",
       ROUND(CAST("SubsidyAmt" AS NUMERIC), 2)                AS sanctioned,
       ROUND(CAST("Subsidy_Rlsd" AS NUMERIC), 2)              AS released,
       ROUND(CAST("BALANCE_AMOUNT_TO_RELEASE" AS NUMERIC), 2) AS balance_pending,
       ROUND(CAST(100.0 * "BALANCE_AMOUNT_TO_RELEASE" / NULLIF("SubsidyAmt", 0) AS NUMERIC), 1) AS pct_unreleased
FROM horticulture_apmip
WHERE "SubsidyAmt" IS NOT NULL
ORDER BY balance_pending DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Per-beneficiary release position', 'Sanctioned vs released vs balance'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q041": {
        "abstract_question": 'What was the last installment paid, to how many farmers, and for how much in total?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "last_installment_no",
       "last_installment_date",
       COUNT(*)                                                AS farmers_paid,
       ROUND(CAST(SUM("last_amount_credited") AS NUMERIC), 2)  AS total_credited
FROM pm_kisan
GROUP BY "last_installment_no", "last_installment_date"
ORDER BY "last_installment_no" DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (PM-KISAN)',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Latest DBT cycle summary', 'How much went out in the last installment?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q044": {
        "abstract_question": 'How much micro-irrigation subsidy has been sanctioned versus actually released?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)                 AS total_sanctioned,
       ROUND(CAST(SUM("Subsidy_Rlsd") AS NUMERIC), 2)               AS total_released,
       ROUND(CAST(SUM("BALANCE_AMOUNT_TO_RELEASE") AS NUMERIC), 2)  AS total_balance,
       ROUND(CAST(100.0 * SUM("BALANCE_AMOUNT_TO_RELEASE") / NULLIF(SUM("SubsidyAmt"), 0) AS NUMERIC), 1) AS pct_unreleased
FROM horticulture_apmip;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Sanctioned vs released vs pending', 'APMIP release position'],
        "notes": 'BALANCE_AMOUNT_TO_RELEASE is the unreleased portion; a balance equal to the sanction means nothing has moved.',
        "expected_empty_on_demo": False,
    },

    "Q046": {
        "abstract_question": 'What is the payment status breakdown for procurement, and how much money is stuck?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "PAYMENT_STATUS",
       COUNT(*)                                       AS transactions,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS value,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity
FROM markfed
GROUP BY "PAYMENT_STATUS"
ORDER BY value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Payments & DBT',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Procurement payment pendency', 'Value of unpaid MARKFED claims'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q049": {
        "abstract_question": 'How many sericulture incentive transactions are not yet approved, and what is their value?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Transaction_Status",
       COUNT(*)                                          AS transactions,
       ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2)   AS value
FROM sericulture
WHERE "Transaction_Status" <> 'Approved'
GROUP BY "Transaction_Status"
ORDER BY value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Payments & DBT',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Sericulture payment pendency', 'Unapproved silk incentive claims'],
        "notes": "\"Not yet approved\" is a pendency question, so Approved is excluded by definition; the GROUP BY keeps Pending and Under Review as separate rows.",
        "expected_empty_on_demo": False,
    },

    "Q051": {
        "abstract_question": 'Across all departments, how much money is sitting unpaid?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Horticulture_APMIP' AS scheme,
       COUNT(*) AS pending_records,
       ROUND(CAST(SUM("BALANCE_AMOUNT_TO_RELEASE") AS NUMERIC), 2) AS pending_value
FROM horticulture_apmip WHERE "BALANCE_AMOUNT_TO_RELEASE" > 0
UNION ALL
SELECT 'Fisheries', COUNT(*), ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2)
FROM fisheries WHERE "payment_status" <> 'Approved'
UNION ALL
SELECT 'Sericulture', COUNT(*), ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2)
FROM sericulture WHERE "Transaction_Status" <> 'Approved'
UNION ALL
SELECT 'MARKFED', COUNT(*), ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)
FROM markfed WHERE "PAYMENT_STATUS" <> 'Approved'
ORDER BY pending_value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Payments & DBT',
        "datasets": 'Horticulture + Fisheries + Sericulture + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Total pendency across schemes', 'Consolidated unpaid liability'],
        "notes": 'One consolidated pendency view — the number a Secretary asks for before a review meeting.',
        "expected_empty_on_demo": False,
    },

    "Q052": {
        "abstract_question": 'Is any bank account number linked to more than one farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "bank_account_no",
       COUNT(DISTINCT "aadhaar_no") AS distinct_farmers,
       COUNT(*)                     AS records
FROM pm_kisan
WHERE "bank_account_no" IS NOT NULL
GROUP BY "bank_account_no"
HAVING COUNT(DISTINCT "aadhaar_no") > 1
ORDER BY distinct_farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Shared bank accounts', 'Duplicate account numbers in the roster'],
        "notes": 'Classic leakage flag. Empty result is a clean bill of health, and the bot must say so rather than invent rows.',
        "expected_empty_on_demo": True,
    },

    "Q053": {
        "abstract_question": 'For the same farmer, does the bank account on the PM-KISAN roster match the one MARKFED pays into?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district",
       p."bank_account_no"  AS pmkisan_account,
       m."ACCOUNT_NO"       AS markfed_account,
       p."ifsc_code"        AS pmkisan_ifsc,
       m."IFSC_CODE"        AS markfed_ifsc
FROM pm_kisan p
JOIN markfed m ON m."AADHAAR_NO" = p."aadhaar_no"
WHERE CAST(p."bank_account_no" AS TEXT) <> CAST(m."ACCOUNT_NO" AS TEXT)
   OR CAST(p."ifsc_code" AS TEXT)       <> CAST(m."IFSC_CODE" AS TEXT)
ORDER BY p."district", p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN + MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Bank account mismatch across schemes', 'Are we paying two different accounts for one farmer?'],
        "notes": 'A mismatch is either a stale record or a diverted payment; both need checking.',
        "expected_empty_on_demo": True,
    },

    "Q054": {
        "abstract_question": 'Do the bank details in sericulture match the PM-KISAN roster for the same farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."name", p."district",
       p."bank_account_no" AS pmkisan_account,
       s."Account_No"      AS sericulture_account,
       p."ifsc_code"       AS pmkisan_ifsc,
       s."IFSC_Code"       AS sericulture_ifsc
FROM pm_kisan p
JOIN sericulture s ON s."aadhaar_no" = p."aadhaar_no"
WHERE CAST(p."bank_account_no" AS TEXT) <> CAST(s."Account_No" AS TEXT)
ORDER BY p."district", p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN + Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Sericulture account mismatch', 'Cross-check silk incentive bank details'],
        "notes": "",
        "expected_empty_on_demo": True,
    },

    "Q055": {
        "abstract_question": 'Which beneficiaries have no bank account or IFSC recorded?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village", "mobile_no",
       "bank_account_no", "ifsc_code"
FROM pm_kisan
WHERE "bank_account_no" IS NULL OR TRIM(CAST("bank_account_no" AS TEXT)) = ''
   OR "ifsc_code" IS NULL       OR TRIM(CAST("ifsc_code" AS TEXT)) = ''
ORDER BY "district";
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Data / MIS',
        "theme": 'Payments & DBT',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Missing bank details', 'Farmers who cannot be paid by DBT'],
        "notes": 'These farmers physically cannot receive DBT; a blocking data-quality issue.',
        "expected_empty_on_demo": True,
    },

    "Q056": {
        "abstract_question": 'What is the average benefit per farmer in each scheme?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Agriculture (input subsidy)' AS scheme,
       COUNT(DISTINCT "aadharno") AS farmers,
       ROUND(CAST(AVG("subsidyamount") AS NUMERIC), 2) AS avg_benefit
FROM agriculture
UNION ALL SELECT 'Horticulture_APMIP', COUNT(DISTINCT "EXTN_AADHARNO"), ROUND(CAST(AVG("SubsidyAmt") AS NUMERIC), 2) FROM horticulture_apmip
UNION ALL SELECT 'Fisheries', COUNT(DISTINCT "aadhar_no"), ROUND(CAST(AVG("amount_paid") AS NUMERIC), 2) FROM fisheries
UNION ALL SELECT 'Sericulture', COUNT(DISTINCT "aadhaar_no"), ROUND(CAST(AVG("Net_Incentive") AS NUMERIC), 2) FROM sericulture
UNION ALL SELECT 'MARKFED', COUNT(DISTINCT "AADHAAR_NO"), ROUND(CAST(AVG("AMOUNT_PAID") AS NUMERIC), 2) FROM markfed
UNION ALL SELECT 'RySS', COUNT(DISTINCT "Aadhar_no"), ROUND(CAST(AVG("Amount") AS NUMERIC), 2) FROM ryss
UNION ALL SELECT 'PM-KISAN (latest installment)', COUNT(DISTINCT "aadhaar_no"), ROUND(CAST(AVG("last_amount_credited") AS NUMERIC), 2) FROM pm_kisan
ORDER BY avg_benefit DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Payments & DBT',
        "datasets": 'All benefit-bearing schemes',
        "geo_level": 'State',
        "paraphrases": ['Average transfer size by scheme', 'Which scheme pays the most per farmer?'],
        "notes": "One row per scheme, seven in all: the six state schemes plus PM-KISAN, whose row is the LATEST INSTALLMENT only because the roster holds no DBT history. RySS pays a benefit like the others — all 684 rows carry Amount > 0 — and is summed by F12, Q057, Q058, G36 and Q131 already; its leg was missing here until 2026-07-30.",
        "expected_empty_on_demo": False,
    },

    # ── Procurement & markets ─────────────────────────────────────────────
    "G14-S": {
        "abstract_question": 'How much has been procured in each district?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "DIST_NAME" AS geography,
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS total_quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_value
FROM markfed
WHERE "PROCUREMENT_DATE" IS NOT NULL
GROUP BY "DIST_NAME"
ORDER BY total_value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Procurement by area', 'MSP purchases geographically'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G15-S": {
        "abstract_question": 'What quantity and value has been procured for each crop?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "CROP_NAME", "SEASON",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS value,
       ROUND(CAST(SUM("AMOUNT_PAID") / NULLIF(SUM("PROCURED_QTY"), 0) AS NUMERIC), 2) AS implied_rate
FROM markfed
WHERE "PROCUREMENT_DATE" IS NOT NULL
GROUP BY "CROP_NAME", "SEASON"
ORDER BY value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Crop-wise procurement', 'Commodity purchases'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G18-S": {
        "abstract_question": 'Which procurement records do not reconcile — amount paid against quantity times rate?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL", "CROP_NAME",
       ROUND(CAST("PROCURED_QTY" AS NUMERIC), 2) AS quantity,
       ROUND(CAST("RATE" AS NUMERIC), 2) AS rate,
       ROUND(CAST("PROCURED_QTY" * "RATE" AS NUMERIC), 2) AS expected_amount,
       ROUND(CAST("AMOUNT_PAID" AS NUMERIC), 2) AS actual_amount
FROM markfed
WHERE ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") > 0.01 * ("PROCURED_QTY" * "RATE")
ORDER BY ABS("AMOUNT_PAID" - "PROCURED_QTY" * "RATE") DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Billing anomalies', 'Payment does not match quantity and rate'],
        "notes": 'Pure arithmetic reconciliation with a 1% tolerance — the cheapest audit test available.',
        "expected_empty_on_demo": True,
    },

    "G19-S": {
        "abstract_question": 'Which farmers sold an implausibly high quantity for the land they hold?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL",
       STRING_AGG(DISTINCT "CROP_NAME", ', ')          AS crops,
       COUNT(*)                                        AS implausible_deliveries,
       ROUND(CAST(MAX("AREA_IN_ACRES") AS NUMERIC), 2) AS acres,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2)  AS quantity,
       ROUND(CAST(MAX("PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0)) AS NUMERIC), 2) AS qty_per_acre
FROM markfed
WHERE "PROCURED_QTY" / NULLIF("AREA_IN_ACRES", 0) > 10
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME", "FARMER_MANDAL"
ORDER BY qty_per_acre DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Yield outliers', 'Quantity per acre above plausible limits'],
        "notes": "The 10 units/acre ceiling is a placeholder. Real ceilings are crop-specific and need agronomic sign-off before this goes live. The ceiling is still applied per delivery; the result is then collapsed to one row per farmer, with qty_per_acre showing that farmer's worst delivery.",
        "expected_empty_on_demo": False,
    },

    "Q103": {
        "abstract_question": 'What is the implied rate per unit for each crop, and does it vary by district?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "CROP_NAME", "DIST_NAME",
       ROUND(CAST(AVG("RATE") AS NUMERIC), 2)                                        AS avg_declared_rate,
       ROUND(CAST(SUM("AMOUNT_PAID") / NULLIF(SUM("PROCURED_QTY"), 0) AS NUMERIC), 2) AS implied_rate
FROM markfed
GROUP BY "CROP_NAME", "DIST_NAME"
ORDER BY "CROP_NAME", implied_rate DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Price variation by district', 'Are farmers getting the same rate everywhere?'],
        "notes": 'Rate variation for the same crop across districts is worth explaining: quality grading, or inconsistent application of MSP.',
        "expected_empty_on_demo": False,
    },

    "Q106": {
        "abstract_question": 'Which farmers sold produce to MARKFED without any crop registration in the agriculture system?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT m."FARMER_NAME", m."DIST_NAME",
       STRING_AGG(DISTINCT m."CROP_NAME", ', ')         AS crops,
       COUNT(*)                                         AS deliveries,
       ROUND(CAST(SUM(m."PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM(m."AMOUNT_PAID") AS NUMERIC), 2)  AS amount
FROM markfed m
WHERE m."AADHAAR_NO" NOT IN (SELECT "aadharno" FROM agriculture WHERE "aadharno" IS NOT NULL)
GROUP BY m."AADHAAR_NO", m."FARMER_NAME", m."DIST_NAME"
ORDER BY amount DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Unregistered supply', 'Procurement without eCrop registration'],
        "notes": "Registration is normally a precondition for MSP procurement; exceptions need a reason on file. One row per supplier (grouped on Aadhaar), not one per delivery.",
        "expected_empty_on_demo": False,
    },

    "Q108": {
        "abstract_question": 'How does procurement split across seasons?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "SEASON", "CR_YEAR",
       COUNT(DISTINCT "AADHAAR_NO")                   AS farmers,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS value
FROM markfed
GROUP BY "SEASON", "CR_YEAR"
ORDER BY value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Season-wise procurement', 'Kharif vs Rabi purchases'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q109": {
        "abstract_question": 'For which crops is the largest share of payment still pending?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "CROP_NAME",
       COUNT(*)                                                                         AS transactions,
       SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN 1 ELSE 0 END)                  AS pending_transactions,
       ROUND(CAST(SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) AS NUMERIC), 2) AS pending_value,
       ROUND(CAST(100.0 * SUM(CASE WHEN "PAYMENT_STATUS" <> 'Approved' THEN "AMOUNT_PAID" ELSE 0 END) / NULLIF(SUM("AMOUNT_PAID"), 0) AS NUMERIC), 1) AS pct_pending
FROM markfed
GROUP BY "CROP_NAME"
ORDER BY pending_value DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Crop-wise payment pendency', 'Where is procurement money stuck by commodity?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q111": {
        "abstract_question": 'What is the average procurement value per farmer in each district, relative to their landholding?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."district",
       COUNT(DISTINCT m."AADHAAR_NO")                                                        AS farmers,
       ROUND(CAST(SUM(m."AMOUNT_PAID") AS NUMERIC), 2)                                       AS total_value,
       ROUND(CAST(SUM(m."AMOUNT_PAID") / COUNT(DISTINCT m."AADHAAR_NO") AS NUMERIC), 2)      AS value_per_farmer,
       ROUND(CAST(SUM(m."AMOUNT_PAID") / NULLIF(SUM(p."area_hectares" * 2.47105), 0) AS NUMERIC), 2) AS value_per_acre
FROM markfed m
JOIN pm_kisan p ON p."aadhaar_no" = m."AADHAAR_NO"
GROUP BY p."district"
ORDER BY value_per_acre DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Procurement intensity by district', 'Value per acre by district'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q112": {
        "abstract_question": 'Which MARKFED suppliers are not on the PM-KISAN roster at all?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT m."AADHAAR_NO", m."FARMER_NAME", m."DIST_NAME",
       STRING_AGG(DISTINCT m."CROP_NAME", ', ')         AS crops,
       COUNT(*)                                         AS deliveries,
       ROUND(CAST(SUM(m."PROCURED_QTY") AS NUMERIC), 2) AS quantity,
       ROUND(CAST(SUM(m."AMOUNT_PAID") AS NUMERIC), 2)  AS amount
FROM markfed m
WHERE m."AADHAAR_NO" NOT IN (SELECT "aadhaar_no" FROM pm_kisan WHERE "aadhaar_no" IS NOT NULL)
GROUP BY m."AADHAAR_NO", m."FARMER_NAME", m."DIST_NAME"
ORDER BY amount DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 300,
        "persona": 'Audit / Vigilance',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Procurement from off-roster farmers', 'Suppliers with no PM-KISAN record'],
        "notes": "Traders selling as farmers is the standard leakage route in MSP procurement; this is the first list to pull. One row per supplier (grouped on Aadhaar), not one per delivery.",
        "expected_empty_on_demo": True,
    },

    # ── Sectoral deep dive ────────────────────────────────────────────────
    "G23-S": {
        "abstract_question": 'How many micro-irrigation applications are pending inspection or review?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "Status",
       COUNT(*) AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS acres
FROM horticulture_apmip
WHERE "SanctionProceedingDate" IS NOT NULL
  AND "Status" <> 'Approved'
GROUP BY "Status"
ORDER BY applications DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['APMIP verification backlog', 'Inspection pendency'],
        "notes": "Pendency question, so Approved is excluded by definition (see the module docstring); the GROUP BY keeps Pending and Under Review as separate rows. This is application processing status (\"Status\") — the random-inspection process is a different column, covered by the G46 family.",
        "expected_empty_on_demo": False,
    },

    "G24-S": {
        "abstract_question": 'What is the unit cost of micro-irrigation, and the subsidy per acre?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT COUNT(*) AS beneficiaries,
       ROUND(CAST(AVG("Cost_per_Hectare") AS NUMERIC), 2) AS avg_cost_per_hectare,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM("SubsidyAmt") / NULLIF(SUM("EXTENT"), 0) AS NUMERIC), 2) AS subsidy_per_acre,
       ROUND(CAST(SUM("Dry_Land") AS NUMERIC), 2) AS dry_land_acres
FROM horticulture_apmip
WHERE "SanctionProceedingDate" IS NOT NULL
;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Cost per hectare', 'Subsidy intensity in APMIP'],
        "notes": 'Wide unit-cost variation across areas is worth a procurement question.',
        "expected_empty_on_demo": False,
    },

    "G27-S": {
        "abstract_question": 'What area is under aquaculture, and how much of it is cultivable?',
        "date_filter": {"alias": '', "column": 'fcs_registration_date'},
        "date_kind": 'iso',  # FCS registration date
        "sql_template": """
SELECT COUNT(*) AS registrants,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2) AS total_extent,
       ROUND(CAST(SUM("Cultivatable_land") AS NUMERIC), 2) AS cultivable_land,
       ROUND(CAST(SUM("cultivation_land") AS NUMERIC), 2) AS land_under_cultivation,
       ROUND(CAST(SUM("operational_capacity") AS NUMERIC), 2) AS operational_capacity
FROM fisheries
WHERE "fcs_registration_date" IS NOT NULL
;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ['Aqua extent summary', 'Cultivable versus total water area'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G29-S": {
        "abstract_question": 'What area is under each natural farming practice?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS total_acreage,
       ROUND(CAST(SUM("C1 Extent(in Acres)") AS NUMERIC), 2) AS c1_extent,
       ROUND(CAST(SUM("PMDS Extent(in Acres)") AS NUMERIC), 2) AS pmds_extent,
       ROUND(CAST(SUM("Nf_extent") AS NUMERIC), 2) AS nf_extent
FROM ryss
WHERE "SurveyDate" IS NOT NULL
;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'State',
        "paraphrases": ['C1, PMDS and S2S extents', 'APCNF practice mix'],
        "notes": 'C1, PMDS and S2S are the APCNF practice categories, each with its own extent column.',
        "expected_empty_on_demo": False,
    },

    "G30-S": {
        "abstract_question": 'How is the natural farming survey progressing month by month?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7) AS survey_month,
       COUNT(*) AS farmers_surveyed,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage_covered
FROM ryss
WHERE "SurveyDate" IS NOT NULL
GROUP BY SUBSTR(CAST("SurveyDate" AS TEXT), 1, 7)
ORDER BY survey_month;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Sectoral deep dive',
        "datasets": 'RySS',
        "geo_level": 'State',
        "paraphrases": ['APCNF survey progress', 'Field survey completion over time'],
        "notes": 'SUBSTR on the ISO date gives year-month without a dialect-specific date function.',
        "expected_empty_on_demo": False,
    },

    "Q145": {
        "abstract_question": 'What is the cocoon output and incentive per farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Farmer_Name", "panchayat_name",
       ROUND(CAST("Cocoon_Qty" AS NUMERIC), 2)     AS cocoon_qty,
       ROUND(CAST("NoOfDFLs" AS NUMERIC), 2)       AS dfls,
       ROUND(CAST("Cocoon_Qty" / NULLIF("NoOfDFLs", 0) AS NUMERIC), 2) AS cocoon_per_dfl,
       ROUND(CAST("Net_Incentive" AS NUMERIC), 2)  AS net_incentive
FROM sericulture
ORDER BY cocoon_qty DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Sericulture productivity', 'Cocoon yield and incentive per farmer'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q146": {
        "abstract_question": 'Which mandals produce the most cocoon, and what incentive did they draw?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "mandal_code", "panchayat_name",
       COUNT(*)                                          AS farmers,
       ROUND(CAST(SUM("Cocoon_Qty") AS NUMERIC), 2)      AS total_cocoon,
       ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2)   AS total_incentive
FROM sericulture
GROUP BY "mandal_code", "panchayat_name"
ORDER BY total_cocoon DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Mandal-wise silk production', 'Cocoon output by area'],
        "notes": 'Mandal is a code here; join to a master or to the PM-KISAN spine for names.',
        "expected_empty_on_demo": False,
    },

    # ── Targeting & equity ────────────────────────────────────────────────
    "G04-S": {
        "abstract_question": 'Give me the social category breakdown of beneficiaries.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "category",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
GROUP BY "category"
ORDER BY farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise beneficiary split', 'SC/ST/BC/OC composition',
                        'How many SC beneficiaries are there?', 'SC and ST farmer counts',
                        'How many SC PM-KISAN farmers'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G05-S": {
        "abstract_question": 'What is the male-female split of beneficiaries?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "gender",
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares,
       ROUND(CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM pm_kisan) AS NUMERIC), 1) AS pct_of_state_total
FROM pm_kisan
GROUP BY "gender"
ORDER BY farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Gender breakdown', 'Women farmers on the roster'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G06-S": {
        "abstract_question": 'Break beneficiaries into marginal, small and other farmers by landholding.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CASE WHEN "area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN "area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS hectares
FROM pm_kisan
GROUP BY land_band
ORDER BY farmers DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Land size bands', 'How many marginal farmers?'],
        "notes": 'GoI definition: marginal below 1 ha, small 1-2 ha, semi-medium and above over 2 ha.',
        "expected_empty_on_demo": False,
    },

    "G13-S": {
        "abstract_question": 'How is input subsidy distributed across social categories?',
        "date_filter": {"alias": 'a', "column": 'cropyear'},
        "date_kind": 'year',  # crop year
        "sql_template": """
SELECT p."category",
       COUNT(DISTINCT a."aadharno") AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2) AS total_subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / NULLIF(SUM(p."area_hectares") * 2.47105, 0) AS NUMERIC), 2) AS subsidy_per_acre
FROM agriculture a
JOIN pm_kisan p ON p."aadhaar_no" = a."aadharno"
WHERE a."cropyear" IS NOT NULL
GROUP BY p."category"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'Agriculture + PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise subsidy share', 'Who gets the money?'],
        "notes": 'Compare the farmer share against the amount share; the gap is the targeting story.',
        "expected_empty_on_demo": False,
    },

    "G20-S": {
        "abstract_question": 'How do procurement payments split by gender and social category?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "GENDER", "CASTE",
       COUNT(DISTINCT "AADHAAR_NO") AS farmers,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2) AS total_paid,
       ROUND(CAST(AVG("AMOUNT_PAID") AS NUMERIC), 2) AS avg_paid
FROM markfed
WHERE "PROCUREMENT_DATE" IS NOT NULL
GROUP BY "GENDER", "CASTE"
ORDER BY total_paid DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Targeting & equity',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Equity in procurement', 'Who sells to MARKFED?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G31-S": {
        "abstract_question": 'Who joins natural farming, by social category?',
        "date_filter": {"alias": '', "column": 'SurveyDate'},
        "date_kind": 'iso',  # survey date
        "sql_template": """
SELECT "Social_Category", "Gender",
       COUNT(*) AS members,
       ROUND(CAST(SUM("ACREAGE") AS NUMERIC), 2) AS acreage,
       ROUND(CAST(AVG("ACREAGE") AS NUMERIC), 2) AS avg_acreage
FROM ryss
WHERE "SurveyDate" IS NOT NULL
GROUP BY "Social_Category", "Gender"
ORDER BY members DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Targeting & equity',
        "datasets": 'RySS',
        "geo_level": 'State',
        "paraphrases": ['APCNF membership profile', 'Caste-wise natural farming uptake'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "G45-S": {
        "abstract_question": 'Does the number of schemes a farmer accesses rise with their landholding?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss  UNION SELECT "aadhaar_no",    'PM-KISAN'     FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n FROM sch GROUP BY aadhaar)
SELECT CASE WHEN p."area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN p."area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(*) AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n, 0)) AS NUMERIC), 2) AS avg_schemes
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
GROUP BY land_band
ORDER BY avg_schemes DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Land size versus scheme access', 'Do bigger farmers capture more?'],
        "notes": 'Central to the equity story: access should not scale with land.',
        "expected_empty_on_demo": False,
    },

    "Q026": {
        "abstract_question": 'What share of micro-irrigation subsidy goes to women beneficiaries?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Gender",
       COUNT(*)                                        AS beneficiaries,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)    AS total_subsidy,
       ROUND(CAST(100.0 * SUM("SubsidyAmt") / (SELECT SUM("SubsidyAmt") FROM horticulture_apmip) AS NUMERIC), 1) AS pct_of_subsidy
FROM horticulture_apmip
GROUP BY "Gender"
ORDER BY total_subsidy DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Targeting & equity',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Gender share in APMIP', "Women's access to micro-irrigation"],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q027": {
        "abstract_question": 'What is the average landholding by social category?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "category",
       COUNT(*)                                        AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS total_hectares,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
GROUP BY "category"
ORDER BY avg_hectares DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise land distribution', 'Do SC/ST farmers hold less land?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q028": {
        "abstract_question": 'Do smaller farmers get more subsidy per acre, or less?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CASE WHEN p."area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN p."area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END AS land_band,
       COUNT(DISTINCT p."aadhaar_no")                                          AS farmers,
       ROUND(CAST(SUM(a."subsidyamount") AS NUMERIC), 2)                       AS total_subsidy,
       ROUND(CAST(SUM(a."subsidyamount") / SUM(p."area_hectares" * 2.47105) AS NUMERIC), 2) AS subsidy_per_acre
FROM pm_kisan p
JOIN agriculture a ON a."aadharno" = p."aadhaar_no"
GROUP BY land_band
ORDER BY subsidy_per_acre DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Audit / Vigilance',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Subsidy per acre by land band', 'Is the subsidy progressive?'],
        "notes": 'Per-acre normalisation is the honest comparison; raw totals always favour large farmers.',
        "expected_empty_on_demo": False,
    },

    "Q031": {
        "abstract_question": 'How does natural farming enrolment compare with the PM-KISAN base, by social category?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p."category",
       COUNT(*)                                                     AS pmkisan_farmers,
       SUM(CASE WHEN r."Aadhar_no" IS NOT NULL THEN 1 ELSE 0 END)   AS ryss_members,
       ROUND(CAST(100.0 * SUM(CASE WHEN r."Aadhar_no" IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC), 1) AS pct_enrolled
FROM pm_kisan p
LEFT JOIN (SELECT DISTINCT "Aadhar_no" FROM ryss) r ON r."Aadhar_no" = p."aadhaar_no"
GROUP BY p."category"
ORDER BY pct_enrolled DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (RySS)',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + RySS',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise APCNF uptake', 'Is natural farming reaching SC/ST farmers?'],
        "notes": 'Uptake rate, not raw count — the denominator is the PM-KISAN roster for that category.',
        "expected_empty_on_demo": False,
    },

    "Q033": {
        "abstract_question": 'How is sericulture incentive split between men and women?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "Sex",
       COUNT(*)                                          AS farmers,
       ROUND(CAST(SUM("Net_Incentive") AS NUMERIC), 2)   AS total_incentive,
       ROUND(CAST(AVG("Net_Incentive") AS NUMERIC), 2)   AS avg_incentive,
       ROUND(CAST(SUM("Cocoon_Qty") AS NUMERIC), 2)      AS total_cocoon
FROM sericulture
GROUP BY "Sex"
ORDER BY total_incentive DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Sericulture)',
        "theme": 'Targeting & equity',
        "datasets": 'Sericulture',
        "geo_level": 'State',
        "paraphrases": ['Gender split in silk incentives', 'Women in sericulture'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q034": {
        "abstract_question": 'What do fisheries payments look like by social category?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "social_category",
       COUNT(DISTINCT "aadhar_no")                    AS registrants,
       ROUND(CAST(SUM("amount_paid") AS NUMERIC), 2)  AS total_paid,
       ROUND(CAST(AVG("amount_paid") AS NUMERIC), 2)  AS avg_paid
FROM fisheries
GROUP BY "social_category"
ORDER BY total_paid DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Fisheries)',
        "theme": 'Targeting & equity',
        "datasets": 'Fisheries',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise fisheries support', 'Who receives fisheries payments?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q038": {
        "abstract_question": 'What is the average number of schemes accessed by each social category?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno" AS aadhaar, 'agri' AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'horti' FROM horticulture_apmip
  UNION SELECT "aadhar_no",    'fish'  FROM fisheries
  UNION SELECT "aadhaar_no",   'seri'  FROM sericulture
  UNION SELECT "AADHAAR_NO",   'markfed' FROM markfed
  UNION SELECT "Aadhar_no",    'ryss'  FROM ryss  UNION SELECT "aadhaar_no",   'pmkisan' FROM pm_kisan
),
cnt AS (SELECT aadhaar, COUNT(DISTINCT scheme) AS n_schemes FROM sch GROUP BY aadhaar)
SELECT p."category",
       COUNT(*)                                                 AS farmers,
       ROUND(CAST(AVG(COALESCE(c.n_schemes, 0)) AS NUMERIC), 2) AS avg_schemes
FROM pm_kisan p
LEFT JOIN cnt c ON c.aadhaar = p."aadhaar_no"
GROUP BY p."category"
ORDER BY avg_schemes DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Caste-wise convergence', 'Does category predict access?'],
        "notes": "",
        "expected_empty_on_demo": False,
    },

    "Q039": {
        "abstract_question": 'Is there a gender gap in average procurement payment per farmer?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "GENDER",
       ROUND(CAST(AVG("AMOUNT_PAID") AS NUMERIC), 2)  AS avg_payment,
       ROUND(CAST(AVG("PROCURED_QTY") AS NUMERIC), 2) AS avg_quantity,
       ROUND(CAST(AVG("AREA_IN_ACRES") AS NUMERIC), 2) AS avg_acres,
       ROUND(CAST(SUM("AMOUNT_PAID") / SUM("AREA_IN_ACRES") AS NUMERIC), 2) AS payment_per_acre
FROM markfed
GROUP BY "GENDER";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Targeting & equity',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Average MSP payment: men vs women', 'Gender gap in procurement value'],
        "notes": "",
        "expected_empty_on_demo": False,
    },


    # ── Added by the template-fidelity pass (2026-07-30) ──────────────────
    "Q147": {
        "abstract_question": 'How many micro-irrigation (APMIP) beneficiaries are there, and what subsidy has been sanctioned and released?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT COUNT(*)                                       AS beneficiaries,
       COUNT(DISTINCT "EXTN_AADHARNO")                AS unique_farmers,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)       AS acres_covered,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)   AS subsidy_sanctioned,
       ROUND(CAST(SUM("Subsidy_Rlsd") AS NUMERIC), 2) AS subsidy_released
FROM horticulture_apmip
WHERE "EXTN_AADHARNO" IS NOT NULL;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Coverage & scale',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Total horticulture beneficiaries', 'APMIP headline numbers',
                        'How many horticulture beneficiaries are there'],
        "notes": 'Statewide single-row headline; G21-S gives the same picture per district.',
        "expected_empty_on_demo": False,
    },

    "Q148": {
        "abstract_question": 'Which PM-KISAN farmers are enrolled in all six AP schemes?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH sch AS (
  SELECT "aadharno"      AS aadhaar, 'Agriculture'  AS scheme FROM agriculture
  UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
  UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
  UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
  UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
  UNION SELECT "Aadhar_no",     'RySS'         FROM ryss
)
SELECT p."name", p."district", p."sub_district", p."village",
       COUNT(DISTINCT s.scheme) AS state_schemes
FROM pm_kisan p
JOIN sch s ON s.aadhaar = p."aadhaar_no"
GROUP BY p."aadhaar_no", p."name", p."district", p."sub_district", p."village"
HAVING COUNT(DISTINCT s.scheme) = 6
ORDER BY p."district", p."name";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Commissioner / Principal Secretary',
        "theme": 'Convergence & overlap',
        "datasets": 'PM-KISAN + all 6 AP schemes',
        "geo_level": 'State',
        "paraphrases": ['Farmers in PM-KISAN plus every state scheme', 'Full-house scheme participation',
                        'Do any farmers receive PM-KISAN and all 6 AP schemes'],
        "notes": 'KEEP-SIX: the PM-KISAN requirement is the INNER JOIN onto the roster, so the CTE stays at six state schemes — adding a PM-KISAN leg would double-count the spine. Fixed at all six, so unlike Q114 there is no numeric slot for "all six AP schemes" to misbind to.',
        "expected_empty_on_demo": False,
    },

    "Q149": {
        "abstract_question": 'How is landholding distributed across social categories, by land-size band?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "category",
       CASE WHEN "area_hectares" < 1 THEN 'Marginal (<1 ha)'
            WHEN "area_hectares" < 2 THEN 'Small (1-2 ha)'
            ELSE 'Semi-medium and above (>2 ha)' END   AS land_band,
       COUNT(*)                                        AS farmers,
       ROUND(CAST(SUM("area_hectares") AS NUMERIC), 2) AS total_hectares,
       ROUND(CAST(AVG("area_hectares") AS NUMERIC), 2) AS avg_hectares
FROM pm_kisan
GROUP BY "category", land_band
ORDER BY "category", land_band;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'District Collector / JD Agriculture',
        "theme": 'Targeting & equity',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Area distribution by caste category', 'Land-size bands per social category'],
        "notes": 'Bands mirror G06 exactly (Marginal <1 ha, Small 1-2 ha, Semi-medium and above >2 ha). Q027 is the averages-only view of the same cut.',
        "expected_empty_on_demo": False,
    },

    "Q150": {
        "abstract_question": "What is the input subsidy by season, and how does it compare with the farmers' own contribution?",
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "season",
       COUNT(*)                                           AS transactions,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2)    AS subsidy_total,
       ROUND(CAST(SUM("nonsubsidyamount") AS NUMERIC), 2) AS farmer_contribution,
       ROUND(CAST(SUM("subsidyamount") / NULLIF(SUM("nonsubsidyamount"), 0) AS NUMERIC), 2) AS subsidy_to_contribution_ratio
FROM agriculture
GROUP BY "season"
ORDER BY subsidy_total DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Crop & inputs',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Subsidy versus non-subsidy amount by season', 'Subsidy-to-contribution ratio'],
        "notes": 'Near-duplicate of Q090, which already carries the same contribution ratio: the ONLY difference is that Q090 counts distinct farmers (Kharif 560, Rabi 460) while this counts transactions (632 / 482). Flagged for the operator — the two should probably be merged. No date_filter, mirroring Q090 — Agriculture is year-granular only.',
        "expected_empty_on_demo": False,
    },

    "Q151": {
        "abstract_question": 'What has each farmer been paid for MARKFED procurement, and who leads?',
        "date_filter": {"alias": '', "column": 'PROCUREMENT_DATE'},
        "date_kind": 'iso',  # procurement date
        "sql_template": """
SELECT "FARMER_NAME", "DIST_NAME",
       COUNT(*)                                       AS deliveries,
       ROUND(CAST(SUM("PROCURED_QTY") AS NUMERIC), 2) AS total_quantity,
       ROUND(CAST(SUM("AMOUNT_PAID") AS NUMERIC), 2)  AS total_paid
FROM markfed
GROUP BY "AADHAAR_NO", "FARMER_NAME", "DIST_NAME"
ORDER BY total_paid DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (MARKFED)',
        "theme": 'Procurement & markets',
        "datasets": 'MARKFED',
        "geo_level": 'State',
        "paraphrases": ['Per-farmer procurement payments ranked', 'Top procurement earners'],
        "notes": 'One row per supplier, grouped on Aadhaar, so there is no transaction fanout. The leading district shows on the top rows; G14-S gives the full district ranking.',
        "expected_empty_on_demo": False,
    },

    "Q153": {
        "abstract_question": 'Which flagged farmers — Excluded, Pending, or eKYC-pending — were still credited a PM-KISAN installment?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "name", "district", "sub_district", "village",
       "beneficiary_status", "ekyc_status",
       "last_installment_no", "last_installment_date",
       ROUND(CAST("last_amount_credited" AS NUMERIC), 2) AS last_amount_credited,
       "mobile_no"
FROM pm_kisan
WHERE ("beneficiary_status" <> 'Included' OR "ekyc_status" = 'Pending')
  AND "last_amount_credited" > 0
ORDER BY "beneficiary_status", "last_installment_date" DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Audit / Vigilance',
        "theme": 'Exclusion & leakage',
        "datasets": 'PM-KISAN',
        "geo_level": 'State',
        "paraphrases": ['Excluded beneficiaries still receiving PM-KISAN money',
                        'Ineligible farmers credited an installment',
                        'eKYC pending but installment credited'],
        "notes": 'The central-DBT leg that Q128 and G37 deliberately do not cover: those show flagged farmers drawing STATE-scheme benefits, this shows them drawing the PM-KISAN installment itself. Every roster row has last_amount_credited > 0 on this drop, so the filter bites entirely through the two status columns. V05 and V06 are the plain status lists with no payment condition.',
        "expected_empty_on_demo": False,
    },

    "G46-S": {
        "abstract_question": 'How many micro-irrigation applications have random inspection pending or under review?',
        "date_filter": {"alias": '', "column": 'SanctionProceedingDate'},
        "date_kind": 'iso',  # sanction date
        "sql_template": """
SELECT "RI_Status_Code"                              AS ri_status,
       COUNT(*)                                      AS applications,
       ROUND(CAST(SUM("SubsidyAmt") AS NUMERIC), 2)  AS subsidy_involved,
       ROUND(CAST(SUM("EXTENT") AS NUMERIC), 2)      AS acres
FROM horticulture_apmip
WHERE "RI_Status_Code" <> 'Approved'
GROUP BY "RI_Status_Code"
ORDER BY applications DESC;
""",
        "param_slots": [],
        "result_ttl_seconds": 600,
        "persona": 'Scheme Director (Horticulture)',
        "theme": 'Sectoral deep dive',
        "datasets": 'Horticulture_APMIP',
        "geo_level": 'State',
        "paraphrases": ['Random inspection backlog', 'RI status position',
                        'How many beneficiaries have random inspection pending or under review'],
        "notes": 'Random inspection (RI_Status_Code) is a different process from application approval (Status, the G23 family) — the two disagree on most rows by design of the source systems, so "random inspection" phrasings must not fall through to G23. FIVSTATUS (field inspection verification) remains unread by any template; re-raise if officers ask for it.',
        "expected_empty_on_demo": False,
    },


    # ── Casual-phrasing coverage (fidelity item 13, 2026-07-30) ───────────
    "Q156": {
        "abstract_question": 'How many farmers registered crops in eCrop each year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT "cropyear"                                        AS crop_year,
       COUNT(DISTINCT "aadharno")                        AS farmers,
       COUNT(*)                                          AS crop_registrations,
       ROUND(CAST(SUM("subsidyamount") AS NUMERIC), 2)   AS subsidy_disbursed
FROM agriculture
GROUP BY "cropyear"
ORDER BY "cropyear";
""",
        "param_slots": [],
        "result_ttl_seconds": 900,
        "persona": 'Scheme Director (Agriculture)',
        "theme": 'Coverage & scale',
        "datasets": 'Agriculture',
        "geo_level": 'State',
        "paraphrases": ['Year-wise farmer numbers in eCrop', 'eCrop enrolment trend by year'],
        "notes": 'date_filter is None DELIBERATELY: the question spans every year, and any date window — including the runtime default — would clamp it to one year and silently un-answer it. Agriculture is year-granular anyway (cropyear, no date column).',
        "expected_empty_on_demo": False,
    },

}


# ── Backend integration ───────────────────────────────────────────────────────
# The rest of the backend (main.py, startup.py, router.py, vector_retriever.py,
# suggestions.py, reranker.py) reads ONE catalog, so the two dicts are merged
# here. Zero-slot entries route unchanged — bind_param_values() returns [] for an
# empty param_slots — and no AP id starts with "D", so nothing collides with the
# router's precomputed-dashboard fast-path (`query_id.startswith("D")`).
# UNPARAMETERISED_CATALOG stays importable on its own for anyone who needs the
# original split.
TEMPLATE_CATALOG = {**TEMPLATE_CATALOG, **UNPARAMETERISED_CATALOG}

ALL_TEMPLATES: dict[str, dict] = TEMPLATE_CATALOG


def bind(template_id: str, values: dict):
    """Return (sql, ordered_params) for a template and a {slot_name: value} dict.

    Slot names repeat when one entity appears at several positions, so the
    ordering comes from param_slots, not from the dict.
    """
    t = ALL_TEMPLATES[template_id]
    slots = sorted(t['param_slots'], key=lambda s: s['position'])
    missing = {s['name'] for s in slots} - set(values)
    if missing:
        raise KeyError(f'{template_id} missing slot values: {sorted(missing)}')
    return t['sql_template'], [values[s['name']] for s in slots]


def required_entities(template_id: str) -> list[str]:
    """Distinct entity types the extractor must resolve for this template."""
    return sorted({s['entity_type'] for s in ALL_TEMPLATES[template_id]['param_slots']})


def retrieval_corpus():
    """(text, template_id) pairs for embedding — abstract question plus paraphrases."""
    pairs = []
    for tid, t in ALL_TEMPLATES.items():
        pairs.append((t['abstract_question'], tid))
        for p in t.get('paraphrases', []):
            pairs.append((p, tid))
    return pairs


def to_postgres(sql: str) -> str:
    """Rewrite ? to $1, $2 … and swap GROUP_CONCAT for STRING_AGG."""
    import re
    n = 0
    def sub(_):
        nonlocal n
        n += 1
        return f'${n}'
    sql = re.sub(r'\?', sub, sql)
    return re.sub(r'GROUP_CONCAT\((DISTINCT\s+)?([^)]+)\)',
                  r"STRING_AGG(\1\2, ',')", sql)

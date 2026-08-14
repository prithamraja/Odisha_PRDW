"""
Odisha Panchayati Raj & Drinking Water — the query catalogue.

346 templates: every question on the workbook's Questions sheet that the
database can answer (95 "Yes", 251 "Partial"). The 17 "No" rows and the 13
dropped beneficiary questions are NOT here — they live in
`unanswerable_catalog.py`, so that a question the database genuinely cannot
answer is retrieved and refused with its reason instead of missing.

ONE TEMPLATE PER QUESTION, SLOTS OPTIONAL (decision D2)
    The filter idiom is `($p IS NULL OR col = $p)`: an absent optional slot
    binds SQL NULL, which reads as "do not filter on this". So ONE entry answers
    a question state-wide, for a district, for a block or for a single GP,
    instead of the AP catalogue's -S/-D/-M sibling variants. Absent optional
    slots must never stall on a clarification — "how many activities are
    planned?" is a complete question state-wide.

    Because the scope is no longer visible in the id, it has to be visible to
    RETRIEVAL: each geography-optional entry carries scope-phrased paraphrases
    ("district-wise…", "block-wise…", "GP-wise…") that all resolve to the one
    entry. The vector retriever keeps the MAX score over a template's vectors and
    counts distinct query_ids toward k, so these can never crowd the candidate
    list.

NAMED PARAMETERS (decision D1)
    Every statement uses `$name` placeholders and binds a DICT, one entry per
    slot name however often the name occurs — which the optional-filter idiom
    makes the normal case, since each parameter appears twice. `param_style` is
    sniffed from the SQL by query_router/sql_params.py; no entry sets it.

GEOGRAPHY BINDS A CODE, NOT A NAME (decisions D4/D10)
    Every `$gp_name` slot is `{"bind": "code"}` and binds the resolved
    `gp_lgd_code`. The SQL predicate was rewritten to match: `v.gp_name =
    $gp_name` became `v.gp_lgd_code = $gp_name`. THE SLOT KEEPS ITS NAME AND ITS
    VALUE IS NOW A CODE — the name is the workbook's, the value is the
    validator's. Statewide there are ~6,800 GPs and names repeat freely, so a
    name predicate would silently merge every namesake into one answer.

    `v_asset` carries geography but not `gp_lgd_code`, so its 13 GP predicates
    resolve through the parent activity
    (`activity_code IN (SELECT … FROM v_activity WHERE gp_lgd_code = $gp_name)`),
    which is exactly equivalent. Blocks and districts still bind their validated
    NAME, because no view exposes their codes — see WP3_REPORT for the
    view-change request that would finish the job.

CAVEATS ARE FIRST-CLASS (decision D3)
    296 of these 346 entries carry a `caveat`, verbatim from the workbook's
    Answerability Note. 251 questions are only PARTIALLY answerable — a proxy
    column, a coverage gap, a denominator that is the 20 loaded GPs rather than
    the roster — and a Partial answer served without its caveat is the
    confidently-wrong failure mode this whole layer exists to prevent. The
    caveat reaches the user as `QueryResponse.caveat` AND appended verbatim to
    the rendered answer; it is never passed through an LLM prompt, where it
    could be paraphrased away.

DATES ARE ORDINARY SLOTS (decision D9)
    `date_filter` is None on every entry and `date_kind` is never set. The
    fiscal year is a normal `$date_range` slot binding the full `'2024-2025'`
    string; `date_phrase.py` maps "FY 24-25" / "last year" onto it. The engine's
    date-injection machinery stays dormant for PR&DW — its `year` kind compares
    integers and would raise a binder error on this column.

THE VIEWS
    Every statement reads the `v_*` analytical views, which are created at
    adapter startup from `sql/create_views.sql` into the writable in-memory
    catalog (`db_factory._seed_views`). Seventeen queries also touch a base
    table — `gram_panchayat` mostly, for the LEFT-JOIN-from-the-roster shape
    that keeps zero-activity GPs in the answer, which is the finding a review
    meeting wants.

ENTRY KEYS
    abstract_question   the parameterised question, placeholders renamed to slot
                        names so `.format()` works in suggestions.
    sql_template        the workbook's SQL, verbatim but for the geography
                        rewrite above.
    param_slots         [{name, entity_type, optional?, bind?}] in the
                        workbook's bind order. `entity_type` matches
                        entity_validator.PARAM_ENTITY_TYPES (a test asserts it).
    caveat              the Answerability Note, when there is one.
    bracket / module / submodule / question_type / answerable
                        the workbook's own classification. Bracket+Module+
                        Submodule is the family structure rerank_context.py
                        groups by.
    paraphrases         extra retrieval surface; see D2 above.

VALIDATION
    tests/test_catalog_execution.py executes all 346 against the sample database
    with the workbook's own sample parameters and compares row counts against
    the Test Report sheet. SQL is deterministic, so any mismatch is a real
    defect rather than replay noise.
"""
# ── GENERATED FILE — do not edit by hand ─────────────────────────────────────
# Built from AI_Chatbot_Questions.xlsx by tools/build_catalog.py.
# To change a question, a caveat or a SQL string, change the WORKBOOK and
# regenerate; `python tools/build_catalog.py --check` fails if this file and the
# workbook have drifted apart.


TEMPLATE_CATALOG: dict[str, dict] = {

    'PLN-001': {
        "abstract_question": 'How many Gram Panchayats in {district_name}/{block_name} have uploaded the GPDP in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_with_gpdp
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'A row in plan = an uploaded GPDP. Pass NULL to any geography parameter to drop that filter.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Gram Panchayats in Khordha have uploaded the GPDP in 2024-2025?',
            'How many Gram panchayats in a block/District have uploaded the GPDP in a given year?',
            'How many Gram Panchayats in a given district/a given block have uploaded the GPDP in a given year?',
            'How many Gram Panchayats in a given district have uploaded the GPDP in a given year?',
            'How many Gram Panchayats in a given block have uploaded the GPDP in a given year?',
            'How many Gram Panchayats in a given gram panchayat have uploaded the GPDP in a given year?',
        ],
    },

    'PLN-002': {
        "abstract_question": 'How many GPs in {district_name}/{block_name} have the GPDP approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_approved
FROM v_plan v
WHERE v.fiscal_year = $date_range AND v.is_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'plan_code_status is 100% NULL, so approval is proxied by approval_date IS NOT NULL. Every plan row has one, so this currently equals PLN-001.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many GPs in Bhubaneswar block have the GPDP approved in 2024-2025?',
            'How many GPs in a Block/District have the GPDP approved in a given year?',
            'How many GPs in a given district/a given block have the GPDP approved in a given year?',
            'How many GPs in a given district have the GPDP approved in a given year?',
            'How many GPs in a given block have the GPDP approved in a given year?',
            'How many GPs in a given gram panchayat have the GPDP approved in a given year?',
        ],
    },

    'PLN-003': {
        "abstract_question": 'What percentage of Gram Panchayats in {block_name} have uploaded their GPDP in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.block_name AS block_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT p.gp_lgd_code) AS gps_uploaded,
       ROUND(100.0 * COUNT(DISTINCT p.gp_lgd_code)
             / NULLIF(COUNT(DISTINCT g.gp_lgd_code),0), 2) AS pct_uploaded
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
WHERE ($block_name IS NULL OR g.block_name = $block_name)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
GROUP BY 1
ORDER BY pct_uploaded DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Denominator is the GPs present in gram_panchayat (20 loaded), not the full official roster.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What percentage of Gram Panchayats in Bhubaneswar have uploaded their GPDP in 2024-2025?',
            'What percentage of Gram Panchayats in a Block have uploaded their GPDP in a given year?',
            'What percentage of Gram Panchayats in a given block have uploaded their GPDP in a given year?',
            'What percentage of Gram Panchayats in a given district have uploaded their GPDP in a given year?',
        ],
    },

    'PLN-004': {
        "abstract_question": 'What percentage of Gram Panchayats in {district_name} have uploaded their GPDP in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.zp_name AS district_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT p.gp_lgd_code) AS gps_uploaded,
       ROUND(100.0 * COUNT(DISTINCT p.gp_lgd_code)
             / NULLIF(COUNT(DISTINCT g.gp_lgd_code),0), 2) AS pct_uploaded
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
WHERE ($block_name IS NULL OR g.block_name = $block_name)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
GROUP BY 1
ORDER BY pct_uploaded DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Denominator is the GPs present in gram_panchayat (20 loaded), not the full official roster.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What percentage of Gram Panchayats in Khordha have uploaded their GPDP in 2024-2025?',
            'What percentage of Gram Panchayats in a District have uploaded their GPDP in a given year?',
            'What percentage of Gram Panchayats in a given district have uploaded their GPDP in a given year?',
            'What percentage of Gram Panchayats in a given block have uploaded their GPDP in a given year?',
        ],
    },

    'PLN-005': {
        "abstract_question": 'Which Gram Panchayats have not yet uploaded their GPDP in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (SELECT 1 FROM plan p
                  WHERE p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
  AND ($block_name    IS NULL OR g.block_name = $block_name)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Returns zero rows when every loaded GP has a plan for that year.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Gram Panchayats have not yet uploaded their GPDP in 2024-2025?',
            'Which Gram Panchayats have not yet uploaded their GPDP in a given year?',
            'Which Gram Panchayats have not yet uploaded their GPDP in a given year, for a given district?',
            'Which Gram Panchayats have not yet uploaded their GPDP in a given year, for a given block?',
        ],
    },

    'PLN-006': {
        "abstract_question": 'Which Blocks have achieved 100% GPDP submission in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.block_name, g.zp_name AS district_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT p.gp_lgd_code) AS gps_uploaded
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
WHERE ($district_name IS NULL OR g.zp_name = $district_name)
GROUP BY 1,2
HAVING COUNT(DISTINCT p.gp_lgd_code) = COUNT(DISTINCT g.gp_lgd_code)
ORDER BY total_gps DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": "'100%' is measured against loaded GPs only.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Blocks have achieved 100% GPDP submission in 2024-2025?',
            'Which Blocks have achieved 100% GPDP submission in a given year?',
            'Which Blocks have achieved 100% GPDP submission in a given year, for a given district?',
        ],
    },

    'PLN-007': {
        "abstract_question": 'Which Districts have the lowest GPDP submission rate in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.zp_name AS district_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT p.gp_lgd_code) AS gps_uploaded,
       ROUND(100.0 * COUNT(DISTINCT p.gp_lgd_code)
             / NULLIF(COUNT(DISTINCT g.gp_lgd_code),0), 2) AS pct_uploaded
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
GROUP BY 1
ORDER BY pct_uploaded ASC, total_gps DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Rate is over loaded GPs only.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Districts have the lowest GPDP submission rate in 2024-2025?',
            'Which Districts have the lowest GPDP submission rate in a given year?',
        ],
    },

    'PLN-008': {
        "abstract_question": 'How many GPs in {block_name} uploaded the GPDP after the deadline {deadline} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_late
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND v.approval_date > CAST($deadline AS DATE)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'deadline', 'entity_type': 'deadline'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'No upload-date column exists; approval_date is used as the timestamp and the deadline is supplied by the user as $deadline.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many GPs in Bhubaneswar uploaded the GPDP after the deadline 2024-06-30 in 2024-2025?',
            'How many GPs in a block uploaded the GPDP after the deadline in a given year?',
            'How many GPs in a given block uploaded the GPDP after the deadline a given deadline in a given year?',
            'How many GPs in a given district uploaded the GPDP after the deadline a given deadline in a given year?',
            'How many GPs in a given gram panchayat uploaded the GPDP after the deadline a given deadline in a given year?',
        ],
    },

    'PLN-009': {
        "abstract_question": 'How many GPs in {district_name} uploaded the GPDP after the deadline {deadline} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_late
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND v.approval_date > CAST($deadline AS DATE)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'deadline', 'entity_type': 'deadline'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'No upload-date column exists; approval_date is used as the timestamp and the deadline is supplied by the user as $deadline.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many GPs in Khordha uploaded the GPDP after the deadline 2024-06-30 in 2024-2025?',
            'How many GPs in a District uploaded the GPDP after the deadline in a given year?',
            'How many GPs in a given district uploaded the GPDP after the deadline a given deadline in a given year?',
            'How many GPs in a given block uploaded the GPDP after the deadline a given deadline in a given year?',
            'How many GPs in a given gram panchayat uploaded the GPDP after the deadline a given deadline in a given year?',
        ],
    },

    'PLN-010': {
        "abstract_question": 'Which GPs in {block_name}/{district_name} uploaded the GPDP after the deadline {deadline} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name, v.plan_type,
       v.approval_date, CAST($deadline AS DATE) AS deadline,
       DATE_DIFF('day', CAST($deadline AS DATE), v.approval_date) AS days_late
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND v.approval_date > CAST($deadline AS DATE)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY days_late DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'deadline', 'entity_type': 'deadline'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'approval_date used as the upload timestamp; deadline supplied by the user.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPs in Bhubaneswar uploaded the GPDP after 2024-06-30 in 2024-2025?',
            'Which GPs in a Block/District uploaded the GPDP after the deadline in a given year?',
            'Which GPs in a given block/a given district uploaded the GPDP after the deadline a given deadline in a given year?',
            'Which GPs in a given district uploaded the GPDP after the deadline a given deadline in a given year?',
            'Which GPs in a given block uploaded the GPDP after the deadline a given deadline in a given year?',
            'Which GPs in a given gram panchayat uploaded the GPDP after the deadline a given deadline in a given year?',
        ],
    },

    'PLN-011': {
        "abstract_question": 'How many GPs uploaded the GPDP before and how many after the deadline {deadline} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT CASE WHEN v.approval_date <= CAST($deadline AS DATE)
                           THEN v.gp_lgd_code END) AS on_time_gps,
       COUNT(DISTINCT CASE WHEN v.approval_date >  CAST($deadline AS DATE)
                           THEN v.gp_lgd_code END) AS late_gps,
       COUNT(DISTINCT v.gp_lgd_code) AS total_gps
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'deadline', 'entity_type': 'deadline'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'approval_date used as the upload timestamp.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many GPs uploaded the GPDP before and after 2024-06-30 in 2024-2025?',
            'How many GPs uploaded the GPDP before the deadline and how many after the deadline in a given year?',
            'How many GPs uploaded the GPDP before and how many after the deadline a given deadline in a given year?',
            'How many GPs uploaded the GPDP before and how many after the deadline a given deadline in a given year, for a given district?',
            'How many GPs uploaded the GPDP before and how many after the deadline a given deadline in a given year, for a given block?',
            'How many GPs uploaded the GPDP before and how many after the deadline a given deadline in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-012': {
        "abstract_question": 'What is the status of the GPDP for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name, v.fiscal_year,
       v.plan_type, v.plan_code, v.approval_date,
       CASE WHEN v.is_approved = 1 THEN 'Approved' ELSE 'Uploaded, not approved' END AS gpdp_status,
       (SELECT COUNT(*) FROM v_activity a WHERE a.plan_code = v.plan_code) AS activities_in_plan
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.plan_type
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Only two states are distinguishable because plan_code_status is NULL throughout.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Status Lookup',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the status of the GPDP for Andhrua in 2024-2025?',
            'What is the status of GPDP for a particular panchayat in a given year?',
            'What is the status of the GPDP for a given gram panchayat in a given year?',
            'What is the status of the GPDP for a given district in a given year?',
            'What is the status of the GPDP for a given block in a given year?',
        ],
    },

    'PLN-013': {
        "abstract_question": 'How many Gram Panchayats in {block_name}/{district_name} have their GPDP approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_approved
FROM v_plan v
WHERE v.fiscal_year = $date_range AND v.is_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Duplicate of PLN-002 in the source list; same approval proxy applies.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gram Panchayats in Bhubaneswar have their GPDP approved in 2024-2025?',
            'How many Gram Panchayats in a Block/District have their GPDP approved in a given year?',
            'How many Gram Panchayats in a given block/a given district have their GPDP approved in a given year?',
            'How many Gram Panchayats in a given district have their GPDP approved in a given year?',
            'How many Gram Panchayats in a given block have their GPDP approved in a given year?',
            'How many Gram Panchayats in a given gram panchayat have their GPDP approved in a given year?',
        ],
    },

    'PLN-014': {
        "abstract_question": 'How many Gram Panchayats in {block_name}/{district_name} are still awaiting GPDP approval in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_awaiting_approval
FROM v_plan v
WHERE v.fiscal_year = $date_range AND v.is_approved = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Returns 0 because every plan row carries an approval_date. Genuinely-pending plans are not represented in the data.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gram Panchayats in Bhubaneswar are awaiting GPDP approval in 2024-2025?',
            'How many Gram Panchayats in a Block/District are still awaiting GPDP approval in a given year?',
            'How many Gram Panchayats in a given block/a given district are still awaiting GPDP approval in a given year?',
            'How many Gram Panchayats in a given district are still awaiting GPDP approval in a given year?',
            'How many Gram Panchayats in a given block are still awaiting GPDP approval in a given year?',
            'How many Gram Panchayats in a given gram panchayat are still awaiting GPDP approval in a given year?',
        ],
    },

    'PLN-015': {
        "abstract_question": 'What is the GPDP approval rate for each Block in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name,
       COUNT(DISTINCT v.gp_lgd_code) AS gps_with_plan,
       COUNT(DISTINCT CASE WHEN v.is_approved = 1 THEN v.gp_lgd_code END) AS gps_approved,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN v.is_approved = 1 THEN v.gp_lgd_code END)
             / NULLIF(COUNT(DISTINCT v.gp_lgd_code),0), 2) AS approval_rate_pct
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY approval_rate_pct DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by approval_date, so the rate is 100% everywhere.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the GPDP approval rate for each Block in 2024-2025?',
            'What is the GPDP approval rate for each Block in a given year?',
            'What is the GPDP approval rate for each Block in a given year, for a given district?',
        ],
    },

    'PLN-016': {
        "abstract_question": 'What is the GPDP approval rate for each District in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.district_name,
       COUNT(DISTINCT v.gp_lgd_code) AS gps_with_plan,
       COUNT(DISTINCT CASE WHEN v.is_approved = 1 THEN v.gp_lgd_code END) AS gps_approved,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN v.is_approved = 1 THEN v.gp_lgd_code END)
             / NULLIF(COUNT(DISTINCT v.gp_lgd_code),0), 2) AS approval_rate_pct
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY approval_rate_pct DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by approval_date, so the rate is 100% everywhere.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the GPDP approval rate for each District in 2024-2025?',
            'What is the GPDP approval rate for each District in a given year?',
            'What is the GPDP approval rate for each District in a given year, for a given district?',
        ],
    },

    'PLN-017': {
        "abstract_question": 'Which Districts have completed GPDP approval for all Gram Panchayats in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.zp_name AS district_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT CASE WHEN p.approval_date IS NOT NULL THEN g.gp_lgd_code END) AS gps_approved
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
GROUP BY 1
HAVING COUNT(DISTINCT CASE WHEN p.approval_date IS NOT NULL THEN g.gp_lgd_code END)
     = COUNT(DISTINCT g.gp_lgd_code)
ORDER BY total_gps DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by approval_date.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Districts completed GPDP approval for all GPs in 2024-2025?',
            'Which Districts have completed GPDP approval for all Gram Panchayats in a given year?',
        ],
    },

    'PLN-018': {
        "abstract_question": 'Which Blocks have completed GPDP approval for all Gram Panchayats in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.block_name AS block_name,
       COUNT(DISTINCT g.gp_lgd_code) AS total_gps,
       COUNT(DISTINCT CASE WHEN p.approval_date IS NOT NULL THEN g.gp_lgd_code END) AS gps_approved
FROM gram_panchayat g
LEFT JOIN plan p ON p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range
GROUP BY 1
HAVING COUNT(DISTINCT CASE WHEN p.approval_date IS NOT NULL THEN g.gp_lgd_code END)
     = COUNT(DISTINCT g.gp_lgd_code)
ORDER BY total_gps DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by approval_date.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Blocks completed GPDP approval for all GPs in 2024-2025?',
            'Which block has completed GPDP approval for all Gram Panchayats in a given year?',
            'Which Blocks have completed GPDP approval for all Gram Panchayats in a given year?',
        ],
    },

    'PLN-019': {
        "abstract_question": 'Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name, v.plan_type, v.plan_code
FROM v_plan v
WHERE v.fiscal_year = $date_range AND v.is_approved = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.district_name, v.block_name, v.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Returns no rows: approval_date is populated on every plan.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPs uploaded the GPDP but await approval in 2024-2025?',
            'Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in a given year?',
            'Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in a given year, for a given district?',
            'Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in a given year, for a given block?',
            'Which Gram Panchayats have uploaded the GPDP but are still awaiting approval in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-020': {
        "abstract_question": 'Which Blocks have the highest number of pending GPDP approvals in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name,
       COUNT(DISTINCT CASE WHEN v.is_approved = 0 THEN v.gp_lgd_code END) AS pending_approvals,
       COUNT(DISTINCT v.gp_lgd_code) AS gps_with_plan
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY pending_approvals DESC, gps_with_plan DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'pending_approvals is 0 everywhere because approval_date is always populated.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Blocks have the most pending GPDP approvals in 2024-2025?',
            'Which Blocks have the highest number of pending GPDP approvals in a given year?',
            'Which Blocks have the highest number of pending GPDP approvals in a given year, for a given district?',
        ],
    },

    'PLN-021': {
        "abstract_question": 'Which district have the highest number of pending GPDP approvals in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.district_name,
       COUNT(DISTINCT CASE WHEN v.is_approved = 0 THEN v.gp_lgd_code END) AS pending_approvals,
       COUNT(DISTINCT v.gp_lgd_code) AS gps_with_plan
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY pending_approvals DESC, gps_with_plan DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'pending_approvals is 0 everywhere because approval_date is always populated.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which district have the most pending GPDP approvals in 2024-2025?',
            'Which district has the highest number of pending GPDP approvals in a given year?',
            'Which district have the highest number of pending GPDP approvals in a given year?',
            'Which district have the highest number of pending GPDP approvals in a given year, for a given district?',
        ],
    },

    'PLN-024': {
        "abstract_question": 'How many activities are planned under each GPDP theme in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Themes come from dim_lsdg_theme, which maps only 17 of 30 focus areas; the rest fall into 'Unmapped theme'.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many activities are planned under each GPDP theme in Andhrua in 2024-2025?',
            'How many activities are planned under each of the nine GPDP themes in a Gram Panchayat in a given year?',
            'How many activities are planned under each GPDP theme in a given gram panchayat in a given year?',
            'How many activities are planned under each GPDP theme in a given district in a given year?',
            'How many activities are planned under each GPDP theme in a given block in a given year?',
        ],
    },

    'PLN-025': {
        "abstract_question": 'Which GPDP theme has the highest number of planned activities in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the highest number of planned activities in Andhrua in 2024-2025?',
            'Which GPDP theme has the highest number of planned activities in a Gram Panchayat in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given gram panchayat in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given block in a given year?',
        ],
    },

    'PLN-026': {
        "abstract_question": 'Which GPDP theme has the lowest number of planned activities in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the lowest number of planned activities in Andhrua in 2024-2025?',
            'Which GPDP theme has the lowest number of planned activities in a Gram Panchayat in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given gram panchayat in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given block in a given year?',
        ],
    },

    'PLN-027': {
        "abstract_question": 'Which GPDP theme has the highest number of planned activities in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the highest number of planned activities in Bhubaneswar in 2024-2025?',
            'Which GPDP theme has the highest number of planned activities in a Block in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given block in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-028': {
        "abstract_question": 'Which GPDP theme has the lowest number of planned activities in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the lowest number of planned activities in Bhubaneswar in 2024-2025?',
            'Which GPDP theme has the lowest number of planned activities in a Block in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given block in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-029': {
        "abstract_question": 'Which GPDP theme has the highest number of planned activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the highest number of planned activities in Khordha in 2024-2025?',
            'Which GPDP theme has the highest number of planned activities in a District in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given block in a given year?',
            'Which GPDP theme has the highest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-030': {
        "abstract_question": 'Which GPDP theme has the lowest number of planned activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the lowest number of planned activities in Khordha in 2024-2025?',
            'Which GPDP theme has the lowest number of planned activities in a District in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given district in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given block in a given year?',
            'Which GPDP theme has the lowest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-031': {
        "abstract_question": 'Which Gram Panchayats have planned the highest number of activities under {theme} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.theme = $theme
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
GROUP BY 1,2,3
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'theme', 'entity_type': 'theme'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Theme values must match dim_lsdg_theme.lsdg_theme exactly (note the trailing space on some).',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPs planned the most activities under Theme 5 - Clean and Green Village in 2024-2025?',
            'Which Gram Panchayats have planned the highest number of activities under a particular theme in a given year?',
            'Which Gram Panchayats have planned the highest number of activities under a given LSDG theme in a given year?',
            'Which Gram Panchayats have planned the highest number of activities under a given LSDG theme in a given year, for a given district?',
            'Which Gram Panchayats have planned the highest number of activities under a given LSDG theme in a given year, for a given block?',
        ],
    },

    'PLN-032': {
        "abstract_question": 'Which Gram Panchayats have not planned any activities under {theme} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (
        SELECT 1 FROM v_activity v
        WHERE v.gp_lgd_code = g.gp_lgd_code
          AND v.fiscal_year = $date_range
          AND v.theme = $theme)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
  AND ($block_name    IS NULL OR g.block_name = $block_name)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'theme', 'entity_type': 'theme'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPs planned nothing under Theme 5 - Clean and Green Village in 2024-2025?',
            'Which Gram Panchayats have not planned any activities under a particular theme in a given year?',
            'Which Gram Panchayats have not planned any activities under a given LSDG theme in a given year?',
            'Which Gram Panchayats have not planned any activities under a given LSDG theme in a given year, for a given district?',
            'Which Gram Panchayats have not planned any activities under a given LSDG theme in a given year, for a given block?',
        ],
    },

    'PLN-033': {
        "abstract_question": 'Which GP has the highest number of planned activities under each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH t AS (
  SELECT v.theme, v.gp_name AS unit, COUNT(*) AS planned_activities
  FROM v_activity v
  WHERE v.fiscal_year = $date_range
    AND ($district_name IS NULL OR v.district_name = $district_name)
  GROUP BY 1,2)
SELECT theme, unit AS gp_name, planned_activities
FROM (SELECT t.*, ROW_NUMBER() OVER (PARTITION BY theme ORDER BY planned_activities DESC) rn FROM t)
WHERE rn = 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'One winning unit per theme; ties are broken arbitrarily by ROW_NUMBER.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GP leads on each GPDP theme in 2024-2025?',
            'Which GP has the highest number of planned activities under each GPDP theme in a given year?',
            'Which GP has the highest number of planned activities under each GPDP theme in a given year, for a given district?',
        ],
    },

    'PLN-034': {
        "abstract_question": 'Which Block has the highest number of planned activities under each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH t AS (
  SELECT v.theme, v.block_name AS unit, COUNT(*) AS planned_activities
  FROM v_activity v
  WHERE v.fiscal_year = $date_range
    AND ($district_name IS NULL OR v.district_name = $district_name)
  GROUP BY 1,2)
SELECT theme, unit AS block_name, planned_activities
FROM (SELECT t.*, ROW_NUMBER() OVER (PARTITION BY theme ORDER BY planned_activities DESC) rn FROM t)
WHERE rn = 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'One winning unit per theme; ties are broken arbitrarily by ROW_NUMBER.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Block leads on each GPDP theme in 2024-2025?',
            'Which Block has the highest number of planned activities under each GPDP theme in a given year?',
            'Which Block has the highest number of planned activities under each GPDP theme in a given year, for a given district?',
        ],
    },

    'PLN-035': {
        "abstract_question": 'Which District has the highest number of planned activities under each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH t AS (
  SELECT v.theme, v.district_name AS unit, COUNT(*) AS planned_activities
  FROM v_activity v
  WHERE v.fiscal_year = $date_range
    AND ($district_name IS NULL OR v.district_name = $district_name)
  GROUP BY 1,2)
SELECT theme, unit AS district_name, planned_activities
FROM (SELECT t.*, ROW_NUMBER() OVER (PARTITION BY theme ORDER BY planned_activities DESC) rn FROM t)
WHERE rn = 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'One winning unit per theme; ties are broken arbitrarily by ROW_NUMBER.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which District leads on each GPDP theme in 2024-2025?',
            'Which District has the highest number of planned activities under each GPDP theme in a given year?',
            'Which District has the highest number of planned activities under each GPDP theme in a given year, for a given district?',
        ],
    },

    'PLN-036': {
        "abstract_question": 'Which theme receives the greatest planning attention across {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme receives the greatest planning attention across Khordha in 2024-2025?',
            'Which theme receives the greatest planning attention across the District in a given year?',
            'Which theme receives the greatest planning attention across a given district in a given year?',
        ],
    },

    'PLN-037': {
        "abstract_question": 'Which theme receives the least planning attention across {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme receives the least planning attention across Khordha in 2024-2025?',
            'Which theme receives the least planning attention across the District in a given year?',
            'Which theme receives the least planning attention across a given district in a given year?',
        ],
    },

    'PLN-038': {
        "abstract_question": 'How has the number of planned activities under each theme changed over the last five years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, v.fiscal_year,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY v.theme, v.fiscal_year
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Covers all six years present (2020-2021 to 2025-2026).',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'How has the number of planned activities per theme changed year on year?',
            'How has the number of planned activities under each theme changed over the last five years, for a given district?',
            'How has the number of planned activities under each theme changed over the last five years, for a given block?',
            'How has the number of planned activities under each theme changed over the last five years, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-039': {
        "abstract_question": 'Which themes have shown the greatest increase in planned activities between {date_range_2} and {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS activities_year1,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)   AS activities_year2,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)
       - COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS change_in_activities
FROM v_activity v
WHERE v.fiscal_year IN ($date_range, $date_range_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY change_in_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'date_range_2', 'entity_type': 'fiscal_year_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "The source question said 'in {Date_Range}'; a change needs two years, so a second year parameter was added.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'Which themes showed the greatest increase between 2023-2024 and 2024-2025?',
            'Which themes have shown the greatest increase in planned activities in a given year?',
            'Which themes have shown the greatest increase in planned activities between a second year and a given year?',
            'Which themes have shown the greatest increase in planned activities between a second year and a given year, for a given district?',
            'Which themes have shown the greatest increase in planned activities between a second year and a given year, for a given block?',
            'Which themes have shown the greatest increase in planned activities between a second year and a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-040': {
        "abstract_question": 'Which themes have shown the greatest decline in planned activities between {date_range_2} and {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS activities_year1,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)   AS activities_year2,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)
       - COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS change_in_activities
FROM v_activity v
WHERE v.fiscal_year IN ($date_range, $date_range_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY change_in_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'date_range_2', 'entity_type': 'fiscal_year_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "The source question said 'in {Date_Range}'; a change needs two years, so a second year parameter was added.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'Which themes showed the greatest decline between 2023-2024 and 2024-2025?',
            'Which themes have shown the greatest decline in planned activities in a given year?',
            'Which themes have shown the greatest decline in planned activities between a second year and a given year?',
            'Which themes have shown the greatest decline in planned activities between a second year and a given year, for a given district?',
            'Which themes have shown the greatest decline in planned activities between a second year and a given year, for a given block?',
            'Which themes have shown the greatest decline in planned activities between a second year and a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-043': {
        "abstract_question": 'Which GPDP themes have no planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT t.lsdg_theme AS theme
FROM (SELECT DISTINCT lsdg_theme FROM dim_lsdg_theme) t
WHERE NOT EXISTS (
        SELECT 1 FROM v_activity v
        WHERE v.theme = t.lsdg_theme
          AND v.fiscal_year = $date_range
          AND ($district_name IS NULL OR v.district_name = $district_name)
          AND ($block_name    IS NULL OR v.block_name    = $block_name)
          AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name))
ORDER BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Universe is the 7 distinct themes in dim_lsdg_theme, not the official nine LSDG themes.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP themes have no planned activities in 2024-2025?',
            'Which GPDP themes have no planned activities in a given year?',
            'Which GPDP themes have no planned activities in a given year, for a given district?',
            'Which GPDP themes have no planned activities in a given year, for a given block?',
            'Which GPDP themes have no planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-044': {
        "abstract_question": 'Are the planned activities balanced across themes in {gp_name}/{block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_share,
       ROUND(100.0 / COUNT(*) OVER (), 2) AS even_share_pct,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () - 100.0 / COUNT(*) OVER (), 2) AS deviation_pts
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_share DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Balanced' is undefined in the source question, so the query returns each theme's share and its deviation from an even split for the user to judge.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'Are planned activities balanced across themes in Bhubaneswar in 2024-2025?',
            'Are the planned activities balanced across themes in a GP/Block in a given year?',
            'Are the planned activities balanced across themes in a given gram panchayat/a given block in a given year?',
            'Are the planned activities balanced across themes in a given district in a given year?',
            'Are the planned activities balanced across themes in a given block in a given year?',
            'Are the planned activities balanced across themes in a given gram panchayat in a given year?',
        ],
    },

    'PLN-045': {
        "abstract_question": 'Which GPDP themes have fewer than {threshold} planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS planned_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(*) < $threshold
ORDER BY planned_activities ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'threshold', 'entity_type': 'threshold'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which GPDP themes have fewer than 50 planned activities in 2024-2025?',
            'Which GPDP themes have fewer than a specified number of planned activities in a given year?',
            'Which GPDP themes have fewer than a given threshold planned activities in a given year?',
            'Which GPDP themes have fewer than a given threshold planned activities in a given year, for a given district?',
            'Which GPDP themes have fewer than a given threshold planned activities in a given year, for a given block?',
            'Which GPDP themes have fewer than a given threshold planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-046': {
        "abstract_question": 'Which themes consistently receive low planning attention across multiple years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH per_year AS (
  SELECT v.fiscal_year, v.theme, COUNT(*) AS activities,
         RANK() OVER (PARTITION BY v.fiscal_year ORDER BY COUNT(*) ASC) AS rank_lowest
  FROM v_activity v
  WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
  GROUP BY 1,2)
SELECT theme,
       COUNT(*) AS years_present,
       COUNT(*) FILTER (WHERE rank_lowest <= 3) AS years_in_bottom_3,
       ROUND(AVG(activities),1) AS avg_activities_per_year
FROM per_year
GROUP BY 1
ORDER BY years_in_bottom_3 DESC, avg_activities_per_year ASC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Consistently low' is operationalised as how often a theme lands in the bottom 3 of a year. Change the 3 if you want a different rule.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes rank lowest on planned activities in every year?',
            'Which themes consistently receive low planning attention across multiple years, for a given district?',
            'Which themes consistently receive low planning attention across multiple years, for a given block?',
            'Which themes consistently receive low planning attention across multiple years, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-047': {
        "abstract_question": 'Which themes require greater planning attention in the next GPDP cycle in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS actual_expenditure,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS pct_completed
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC, pct_completed ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Advisory question with no defined rule; the query surfaces the low-activity, low-completion themes and leaves the judgement to the user.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes need more planning attention after 2024-2025?',
            'Which themes require greater planning attention in the next GPDP cycle in a given year?',
            'Which themes require greater planning attention in the next GPDP cycle in a given year, for a given district?',
            'Which themes require greater planning attention in the next GPDP cycle in a given year, for a given block?',
            'Which themes require greater planning attention in the next GPDP cycle in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-049': {
        "abstract_question": 'How many activities are planned under {focus_area} in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.focus_area_name = $focus_area
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities are planned under Sanitation in Andhrua in 2024-2025?',
            'How many activities are planned under a particular focus area in a particular Gram Panchayat in a given year?',
            'How many activities are planned under a given focus area in a given gram panchayat in a given year?',
            'How many activities are planned under a given focus area in a given district in a given year?',
            'How many activities are planned under a given focus area in a given block in a given year?',
        ],
    },

    'PLN-050': {
        "abstract_question": 'How many activities are planned under each focus area in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities are planned under each focus area in Andhrua in 2024-2025?',
            'How many activities are planned under each focus area in a Gram Panchayat in a given year?',
            'How many activities are planned under each focus area in a given gram panchayat in a given year?',
            'How many activities are planned under each focus area in a given district in a given year?',
            'How many activities are planned under each focus area in a given block in a given year?',
        ],
    },

    'PLN-051': {
        "abstract_question": 'How many activities are planned under each focus area in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities are planned under each focus area in Bhubaneswar in 2024-2025?',
            'How many total activities are planned under each focus area in a block in a given year?',
            'How many activities are planned under each focus area in a given block in a given year?',
            'How many activities are planned under each focus area in a given district in a given year?',
            'How many activities are planned under each focus area in a given gram panchayat in a given year?',
        ],
    },

    'PLN-052': {
        "abstract_question": 'Which focus area has the highest number of planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the highest number of planned activities in 2024-2025?',
            'Which focus area has the highest number of planned activities in the selected year?',
            'Which focus area has the highest number of planned activities in a given year?',
            'Which focus area has the highest number of planned activities in a given year, for a given district?',
            'Which focus area has the highest number of planned activities in a given year, for a given block?',
            'Which focus area has the highest number of planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-053': {
        "abstract_question": 'Which focus area has the lowest number of planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the lowest number of planned activities in 2024-2025?',
            'Which focus area has the lowest number of planned activities in the selected year?',
            'Which focus area has the lowest number of planned activities in a given year?',
            'Which focus area has the lowest number of planned activities in a given year, for a given district?',
            'Which focus area has the lowest number of planned activities in a given year, for a given block?',
            'Which focus area has the lowest number of planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-054': {
        "abstract_question": 'Which focus area has the highest number of planned activities in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the highest number of planned activities in 2024-2025?',
            'Which focus area has the highest number of planned activities in a Block in a given year?',
            'Which focus area has the highest number of planned activities in a given block in a given year?',
            'Which focus area has the highest number of planned activities in a given district in a given year?',
            'Which focus area has the highest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-055': {
        "abstract_question": 'Which focus area has the lowest number of planned activities in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the lowest number of planned activities in 2024-2025?',
            'Which focus area has the lowest number of planned activities in a Block in a given year?',
            'Which focus area has the lowest number of planned activities in a given block in a given year?',
            'Which focus area has the lowest number of planned activities in a given district in a given year?',
            'Which focus area has the lowest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-056': {
        "abstract_question": 'Which focus area has the highest number of planned activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the highest number of planned activities in 2024-2025?',
            'Which focus area has the highest number of planned activities in a District in a given year?',
            'Which focus area has the highest number of planned activities in a given district in a given year?',
            'Which focus area has the highest number of planned activities in a given block in a given year?',
            'Which focus area has the highest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-057': {
        "abstract_question": 'Which focus area has the lowest number of planned activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set $top_n = 1 for a single answer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the lowest number of planned activities in 2024-2025?',
            'Which focus area has the lowest number of planned activities in a District in a given year?',
            'Which focus area has the lowest number of planned activities in a given district in a given year?',
            'Which focus area has the lowest number of planned activities in a given block in a given year?',
            'Which focus area has the lowest number of planned activities in a given gram panchayat in a given year?',
        ],
    },

    'PLN-058': {
        "abstract_question": 'What activities are planned under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.focus_area_name = $focus_area
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_cost DESC NULLS LAST
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Raise $top_n to list more than the default page.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'What activities are planned under Sanitation in 2024-2025?',
            'What activities are planned under a particular focus area in a given year?',
            'What activities are planned under a given focus area in a given year?',
            'What activities are planned under a given focus area in a given year, for a given district?',
            'What activities are planned under a given focus area in a given year, for a given block?',
            'What activities are planned under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-059': {
        "abstract_question": 'Which Gram Panchayats have not planned any activities under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (
        SELECT 1 FROM v_activity v
        WHERE v.gp_lgd_code = g.gp_lgd_code
          AND v.fiscal_year = $date_range
          AND v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
  AND ($block_name    IS NULL OR g.block_name = $block_name)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which GPs planned nothing under Sanitation in 2024-2025?',
            'Which Gram Panchayats have not planned any activities under a particular focus area in a given year?',
            'Which Gram Panchayats have not planned any activities under a given focus area in a given year?',
            'Which Gram Panchayats have not planned any activities under a given focus area in a given year, for a given district?',
            'Which Gram Panchayats have not planned any activities under a given focus area in a given year, for a given block?',
        ],
    },

    'PLN-060': {
        "abstract_question": 'How does the number of planned activities under each focus area compare across Gram Panchayats in a Block in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, v.gp_name AS unit, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY v.focus_area_name, planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Long format - one row per focus area per unit; pivot in the presentation layer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Comparison',
        "answerable": 'Yes',
        "paraphrases": [
            'How do focus-area activity counts compare across GPs in Bhubaneswar in 2024-2025?',
            'How does the number of planned activities under each focus area compare across Gram Panchayats in a Block in a given year?',
            'How does the number of planned activities under each focus area compare across Gram Panchayats in a Block in a given year, for a given block?',
            'How does the number of planned activities under each focus area compare across Gram Panchayats in a Block in a given year, for a given district?',
        ],
    },

    'PLN-061': {
        "abstract_question": 'How does the number of planned activities under each focus area compare across Blocks in a District in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, v.block_name AS unit, COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY v.focus_area_name, planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Long format - one row per focus area per unit; pivot in the presentation layer.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Comparison',
        "answerable": 'Yes',
        "paraphrases": [
            'How do focus-area activity counts compare across blocks in Khordha in 2024-2025?',
            'How does the number of planned activities under each focus area compare across Blocks in a District in a given year?',
            'How does the number of planned activities under each focus area compare across Blocks in a District in a given year, for a given block?',
            'How does the number of planned activities under each focus area compare across Blocks in a District in a given year, for a given district?',
        ],
    },

    'PLN-062': {
        "abstract_question": 'Which focus area receives the highest planning attention across {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area gets the highest planning attention in Khordha in 2024-2025?',
            'Which focus area receives the highest planning attention across the District in a given year?',
            'Which focus area receives the highest planning attention across a given district in a given year?',
        ],
    },

    'PLN-063': {
        "abstract_question": 'Which focus area receives the lowest planning attention across {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY planned_activities ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area gets the lowest planning attention in Khordha in 2024-2025?',
            'Which focus area receives the lowest planning attention across the District in a given year?',
            'Which focus area receives the lowest planning attention across a given district in a given year?',
        ],
    },

    'PLN-064': {
        "abstract_question": 'Which focus areas account for the largest share of planned activities in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_share,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_cost_share
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_share DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas take the largest share in Andhrua in 2024-2025?',
            'Which focus areas account for the largest share of planned activities in a Gram Panchayat in a given year?',
            'Which focus areas account for the largest share of planned activities in a given gram panchayat in a given year?',
            'Which focus areas account for the largest share of planned activities in a given district in a given year?',
            'Which focus areas account for the largest share of planned activities in a given block in a given year?',
        ],
    },

    'PLN-065': {
        "abstract_question": 'Which focus areas account for the smallest share of planned activities in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_share,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_cost_share
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_share ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas take the smallest share in Andhrua in 2024-2025?',
            'Which focus areas account for the smallest share of planned activities in a Gram Panchayat in a given year?',
            'Which focus areas account for the smallest share of planned activities in a given gram panchayat in a given year?',
            'Which focus areas account for the smallest share of planned activities in a given district in a given year?',
            'Which focus areas account for the smallest share of planned activities in a given block in a given year?',
        ],
    },

    'PLN-066': {
        "abstract_question": 'Which types of activity are repeatedly planned across years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_name,
       COUNT(DISTINCT v.fiscal_year) AS years_planned,
       COUNT(*) AS total_occurrences,
       SUM(COALESCE(v.total_cost,0)) AS total_planned_cost,
       MIN(v.fiscal_year) AS first_year, MAX(v.fiscal_year) AS last_year
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(DISTINCT v.fiscal_year) > 1
ORDER BY years_planned DESC, total_occurrences DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Matches on the exact activity_name string; near-duplicate wording will not group together.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'Which activity names recur across the most years?',
            'Which type of activities are repeatedly planned across years in a given year?',
            'Which types of activity are repeatedly planned across years, for a given district?',
            'Which types of activity are repeatedly planned across years, for a given block?',
            'Which types of activity are repeatedly planned across years, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-068': {
        "abstract_question": 'Which focus areas have no planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT d.description AS focus_area_name
FROM dim_code d
WHERE d.variable = 'focus_area'
  AND NOT EXISTS (
        SELECT 1 FROM v_activity v
        WHERE v.focus_area_name = d.description
          AND v.fiscal_year = $date_range
          AND ($district_name IS NULL OR v.district_name = $district_name)
          AND ($block_name    IS NULL OR v.block_name    = $block_name)
          AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name))
ORDER BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Universe is the 30 focus-area codes in dim_code.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas have no planned activities in 2024-2025?',
            'Which focus areas have no planned activities in a given year?',
            'Which focus areas have no planned activities in a given year, for a given district?',
            'Which focus areas have no planned activities in a given year, for a given block?',
            'Which focus areas have no planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-069': {
        "abstract_question": 'Which focus areas have fewer than {threshold} planned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS planned_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(*) < $threshold
ORDER BY planned_activities ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'threshold', 'entity_type': 'threshold'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas have fewer than 50 planned activities in 2024-2025?',
            'Which focus areas have fewer than a specified number of planned activities in a given year?',
            'Which focus areas have fewer than a given threshold planned activities in a given year?',
            'Which focus areas have fewer than a given threshold planned activities in a given year, for a given district?',
            'Which focus areas have fewer than a given threshold planned activities in a given year, for a given block?',
            'Which focus areas have fewer than a given threshold planned activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-070': {
        "abstract_question": 'Which focus areas are repeatedly included in the GPDP across multiple years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(DISTINCT v.fiscal_year) AS years_present,
       COUNT(*) AS total_activities,
       ROUND(AVG(COALESCE(v.total_cost,0)),2) AS avg_planned_cost
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY years_present DESC, total_activities DESC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            "Which focus areas appear in every year's GPDP?",
            'Which focus areas are repeatedly included in the GPDP across multiple years, for a given district?',
            'Which focus areas are repeatedly included in the GPDP across multiple years, for a given block?',
            'Which focus areas are repeatedly included in the GPDP across multiple years, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-071': {
        "abstract_question": 'Which focus areas require greater planning attention in the next GPDP cycle after {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS actual_expenditure,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS pct_completed
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_activities ASC, pct_completed ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Advisory; no rule defined in the source question. Surfaces low-activity, low-completion focus areas.',
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas need more attention after 2024-2025?',
            'Which focus areas require greater planning attention in the next GPDP cycle in a given year?',
            'Which focus areas require greater planning attention in the next GPDP cycle after a given year?',
            'Which focus areas require greater planning attention in the next GPDP cycle after a given year, for a given district?',
            'Which focus areas require greater planning attention in the next GPDP cycle after a given year, for a given block?',
            'Which focus areas require greater planning attention in the next GPDP cycle after a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLN-072': {
        "abstract_question": 'Are the planned activities balanced across themes in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_share,
       ROUND(100.0 / COUNT(*) OVER (), 2) AS even_share_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_share DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Same caveat as PLN-044: 'balanced' is not defined, so shares and the even-split benchmark are returned.",
        "bracket": 'Planning',
        "module": 'GPDP',
        "submodule": 'Planning',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'Are planned activities balanced across themes in 2024-2025?',
            'Are the planned activities balanced across themes in a given year?',
            'Are the planned activities balanced across themes in a given year, for a given district?',
            'Are the planned activities balanced across themes in a given year, for a given block?',
            'Are the planned activities balanced across themes in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLU-006': {
        "abstract_question": 'How many low-cost activities (below {threshold} rupees) are planned theme-wise in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) FILTER (WHERE COALESCE(v.total_cost,0) > 0
                          AND COALESCE(v.total_cost,0) < $threshold) AS low_cost_activities,
       COUNT(*) AS total_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE COALESCE(v.total_cost,0) > 0
                          AND COALESCE(v.total_cost,0) < $threshold)
             / NULLIF(COUNT(*),0), 2) AS pct_low_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY low_cost_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $threshold = 1000 to reproduce the 'below Rs. 1000' band in the source question.",
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Low-cost & No-cost Activities',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities below Rs 1000 are planned theme-wise in 2024-2025?',
            'How many low-cost activities (below Rs. 1000) are registered theme-wise in the state plan for a given Plan Year?',
            'How many low-cost activities (below a given threshold rupees) are planned theme-wise in a given year?',
            'How many low-cost activities (below a given threshold rupees) are planned theme-wise in a given year, for a given district?',
            'How many low-cost activities (below a given threshold rupees) are planned theme-wise in a given year, for a given block?',
            'How many low-cost activities (below a given threshold rupees) are planned theme-wise in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PLU-007': {
        "abstract_question": 'What is the cost-band split (below 500, 500-1000, above 1000) of activities in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CASE WHEN COALESCE(v.total_cost,0) = 0     THEN '0 (no cost)'
            WHEN v.total_cost < 500               THEN 'Below 500'
            WHEN v.total_cost <= 1000             THEN '500 - 1000'
            ELSE 'Above 1000' END AS cost_band,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Low-cost & No-cost Activities',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the cost-band split of activities in Khordha for 2024-2025?',
            'What is the cost-band split (below 500, 500-1000, above 1000) of activities in a given District for a given Plan Year?',
            'What is the cost-band split (below 500, 500-1000, above 1000) of activities in a given district for a given year?',
            'What is the cost-band split (below 500, 500-1000, above 1000) of activities in a given block for a given year?',
            'What is the cost-band split (below 500, 500-1000, above 1000) of activities in a given gram panchayat for a given year?',
        ],
    },

    'PLU-008': {
        "abstract_question": 'How many no-cost activities are planned in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) FILTER (WHERE v.is_costless_activity = 1
                           OR COALESCE(v.total_cost,0) = 0) AS no_cost_activities,
       COUNT(*) AS total_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_costless_activity = 1
                           OR COALESCE(v.total_cost,0) = 0)
             / NULLIF(COUNT(*),0), 2) AS pct_no_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Flagship' activities are not identifiable - no flagship flag exists. Only the no-cost half of the question is answered.",
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Low-cost & No-cost Activities',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many no-cost activities are planned in Bhubaneswar for 2024-2025?',
            'How many no-cost or flagship activities are planned in a given Block for a given Plan Year?',
            'How many no-cost activities are planned in a given block for a given year?',
            'How many no-cost activities are planned in a given district for a given year?',
            'How many no-cost activities are planned in a given gram panchayat for a given year?',
        ],
    },

    'PLU-009': {
        "abstract_question": 'What share of planned activities in {gp_name} are low-cost (below {threshold}) in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE COALESCE(v.total_cost,0) > 0
                          AND COALESCE(v.total_cost,0) < $threshold) AS low_cost_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE COALESCE(v.total_cost,0) > 0
                          AND COALESCE(v.total_cost,0) < $threshold)
             / NULLIF(COUNT(*),0), 2) AS pct_low_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY pct_low_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Low-cost & No-cost Activities',
        "question_type": 'Rate/Percentage',
        "answerable": 'Yes',
        "paraphrases": [
            "What share of Andhrua's planned activities are below Rs 1000 in 2024-2025?",
            'What share of planned activities in a given GP Name are low-cost activities in a given Plan Year?',
            'What share of planned activities in a given gram panchayat are low-cost (below a given threshold) in a given year?',
            'What share of planned activities in a given district are low-cost (below a given threshold) in a given year?',
            'What share of planned activities in a given block are low-cost (below a given threshold) in a given year?',
        ],
    },

    'PLU-001': {
        "abstract_question": 'What is the status of the {date_range} plan of {gp_name}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name, v.fiscal_year,
       v.plan_type, v.plan_code, v.approval_date,
       CASE WHEN v.is_approved = 1 THEN 'Approved' ELSE 'Uploaded, not approved' END AS plan_status,
       (SELECT COUNT(*) FROM v_activity a WHERE a.plan_code = v.plan_code) AS activities,
       (SELECT SUM(COALESCE(a.total_cost,0)) FROM v_activity a WHERE a.plan_code = v.plan_code) AS planned_cost
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.plan_type
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'plan_code_status is NULL throughout, so only Approved / Not approved can be distinguished.',
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Plan Structure',
        "question_type": 'Status Lookup',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the status of the 2024-2025 plan of Andhrua?',
            'What is the status of the a given Plan Year plan of a given GP Name?',
            'What is the status of the a given year plan of a given gram panchayat?',
            'What is the status of the a given year plan of a given district?',
            'What is the status of the a given year plan of a given block?',
        ],
    },

    'PLU-003': {
        "abstract_question": 'Does {gp_name} have a supplementary plan in addition to the main plan for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) FILTER (WHERE v.plan_type = 'Main')          AS main_plans,
       COUNT(*) FILTER (WHERE v.plan_type = 'Supplementary') AS supplementary_plans,
       CASE WHEN COUNT(*) FILTER (WHERE v.plan_type = 'Supplementary') > 0
            THEN 'Yes' ELSE 'No' END AS has_supplementary
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
ORDER BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Plan Structure',
        "question_type": 'Status Lookup',
        "answerable": 'Yes',
        "paraphrases": [
            'Does Andhrua have a supplementary plan for 2024-2025?',
            'Does a given GP Name have a supplementary plan in addition to the main plan for a given Plan Year?',
            'Does a given gram panchayat have a supplementary plan in addition to the main plan for a given year?',
            'Does a given district have a supplementary plan in addition to the main plan for a given year?',
            'Does a given block have a supplementary plan in addition to the main plan for a given year?',
        ],
    },

    'PLU-004': {
        "abstract_question": 'How many GPs in {block_name} uploaded supplementary plans for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(DISTINCT v.gp_lgd_code) AS gps_with_supplementary,
       COUNT(*) AS supplementary_plans
FROM v_plan v
WHERE v.fiscal_year = $date_range
  AND v.plan_type = 'Supplementary'
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Plan Attributes',
        "submodule": 'Plan Structure',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many GPs in Bhubaneswar uploaded supplementary plans for 2024-2025?',
            'How many GPs in a given Block uploaded supplementary plans for a given Plan Year?',
            'How many GPs in a given block uploaded supplementary plans for a given year?',
            'How many GPs in a given district uploaded supplementary plans for a given year?',
            'How many GPs in a given gram panchayat uploaded supplementary plans for a given year?',
        ],
    },

    'WRK-001': {
        "abstract_question": 'How many fresh and how many maintenance activities does {gp_name} have in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.work_type_label,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'work_type decodes to New/Fresh, Maintenance, Upgradation, None; 346 activities have no work_type and show as Unknown.',
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many fresh vs maintenance activities does Andhrua have in 2024-2025?',
            'How many fresh and how many maintenance activities does a given GP Name have in a given Financial Year?',
            'How many fresh and how many maintenance activities does a given gram panchayat have in a given year?',
            'How many fresh and how many maintenance activities does a given district have in a given year?',
            'How many fresh and how many maintenance activities does a given block have in a given year?',
        ],
    },

    'WRK-002': {
        "abstract_question": 'What is the expenditure on fresh versus maintenance activities in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.work_type_label,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the fresh vs maintenance expenditure in Bhubaneswar for 2024-2025?',
            'What is the expenditure on fresh versus maintenance activities in a given Block for a given Financial Year?',
            'What is the expenditure on fresh versus maintenance activities in a given block for a given year?',
            'What is the expenditure on fresh versus maintenance activities in a given district for a given year?',
            'What is the expenditure on fresh versus maintenance activities in a given gram panchayat for a given year?',
        ],
    },

    'WRK-003': {
        "abstract_question": 'What share of total expenditure in {district_name} went to maintenance activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(v.total_expenditure) AS total_expenditure,
       SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance')
             / NULLIF(SUM(v.total_expenditure),0), 2) AS pct_maintenance
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Rate/Percentage',
        "answerable": 'Yes',
        "paraphrases": [
            "What share of Khordha's expenditure went to maintenance in 2024-2025?",
            'What share of total expenditure in a given District went to maintenance activities in a given Financial Year?',
            'What share of total expenditure in a given district went to maintenance activities in a given year?',
            'What share of total expenditure in a given block went to maintenance activities in a given year?',
            'What share of total expenditure in a given gram panchayat went to maintenance activities in a given year?',
        ],
    },

    'WRK-004': {
        "abstract_question": 'Which asset sub-categories have the highest number of maintenance activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_subcategory_label,
       COUNT(*) AS maintenance_activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label = 'Maintenance'
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY maintenance_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "asset_subcategory is populated on 4,286 of 12,704 asset rows, so most maintenance activity lands in 'Uncategorised'.",
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which asset sub-categories see the most maintenance in Khordha in 2024-2025?',
            'Which asset sub-categories have the highest number of maintenance activities in a given District in a given Financial Year?',
            'Which asset sub-categories have the highest number of maintenance activities in a given district in a given year?',
            'Which asset sub-categories have the highest number of maintenance activities in a given block in a given year?',
            'Which asset sub-categories have the highest number of maintenance activities in a given gram panchayat in a given year?',
        ],
    },

    'WRK-005': {
        "abstract_question": 'Which GPs in {block_name} spend more on maintenance than on fresh assets in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_exp,
       SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'New/Fresh')   AS fresh_exp,
       SUM(v.total_expenditure) AS total_exp
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
HAVING COALESCE(SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance'),0)
     > COALESCE(SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'New/Fresh'),0)
ORDER BY maintenance_exp DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which GPs in Bhubaneswar spend more on maintenance than fresh in 2024-2025?',
            'Which GPs in a given Block spend more on maintenance than on fresh assets in a given Financial Year?',
            'Which GPs in a given block spend more on maintenance than on fresh assets in a given year?',
            'Which GPs in a given district spend more on maintenance than on fresh assets in a given year?',
            'Which GPs in a given gram panchayat spend more on maintenance than on fresh assets in a given year?',
        ],
    },

    'WRK-007': {
        "abstract_question": 'How has maintenance expenditure in {block_name} changed over the years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.fiscal_year,
       COUNT(*) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_activities,
       SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_expenditure,
       SUM(v.total_expenditure) AS total_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance')
             / NULLIF(SUM(v.total_expenditure),0), 2) AS pct_maintenance
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY 1
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'How has maintenance expenditure in Bhubaneswar changed year on year?',
            'How has maintenance expenditure in a given Block changed over a given Date Range?',
            'How has maintenance expenditure in a given block changed over the years?',
            'How has maintenance expenditure in a given district changed over the years?',
            'How has maintenance expenditure in a given gram panchayat changed over the years?',
        ],
    },

    'WRK-008': {
        "abstract_question": 'What is the fresh versus maintenance split for {asset_category} activities in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_category_label, v.work_type_label,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($asset_category IS NULL OR v.asset_category_label = $asset_category)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1,2
ORDER BY v.asset_category_label, expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'asset_category', 'entity_type': 'asset_category', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'asset_category is populated on 4,286 of 12,704 rows. Pass NULL to $asset_category to see every category.',
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the fresh vs maintenance split for a given asset category in Khordha in 2024-2025?',
            'What is the fresh versus maintenance split for a given Asset Category activities in a given District in a given Financial Year?',
            'What is the fresh versus maintenance split for a given asset category activities in a given district in a given year?',
            'What is the fresh versus maintenance split for a given asset category activities in a given block in a given year?',
            'What is the fresh versus maintenance split for a given asset category activities in a given gram panchayat in a given year?',
        ],
    },

    'WRK-009': {
        "abstract_question": 'Which assets in {gp_name} have had maintenance activities in more than one year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.asset_subcategory_label, v.activity_name,
       COUNT(DISTINCT v.fiscal_year) AS years_with_maintenance,
       STRING_AGG(DISTINCT v.fiscal_year, ', ' ORDER BY v.fiscal_year) AS years,
       SUM(v.total_expenditure) AS total_maintenance_expenditure
FROM v_asset v
WHERE v.work_type_label = 'Maintenance'
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1,2,3
HAVING COUNT(DISTINCT v.fiscal_year) > 1
ORDER BY years_with_maintenance DESC, total_maintenance_expenditure DESC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'There is no asset identifier that persists across years, so repeat maintenance is inferred from identical activity_name + asset sub-category.',
        "bracket": 'Planning',
        "module": 'Work Type',
        "submodule": 'Fresh vs Maintenance',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which assets in Andhrua saw maintenance in more than one year?',
            'Which assets in a given GP Name have had maintenance activities in more than one of the last three years?',
            'Which assets in a given gram panchayat have had maintenance activities in more than one year?',
            'Which assets in a given district have had maintenance activities in more than one year?',
            'Which assets in a given block have had maintenance activities in more than one year?',
        ],
    },

    'FND-005': {
        "abstract_question": 'How much of the sanctioned funding in {block_name} is earmarked for SC and ST categories in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_general,0)) AS general_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_sc,0))      AS sc_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_st,0))      AS st_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_total,0))   AS total_sanctioned,
       ROUND(100.0 * SUM(COALESCE(v.fund_sanctioned_sc,0) + COALESCE(v.fund_sanctioned_st,0))
             / NULLIF(SUM(COALESCE(v.fund_sanctioned_total,0)),0), 2) AS pct_sc_st,
       SUM(v.sc_amount) AS sc_spent,
       SUM(v.st_amount) AS st_spent
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Now uses the real earmark columns from admin_approval_scheme rather than the spent split. Coverage is thin in the source: fund_sanctioned_sc is populated on 0.1% of rows and fund_sanctioned_st on 0.9%, so most areas will still return zero. Spent amounts are shown alongside for comparison.',
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Category Funds',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much Bhubaneswar funding is earmarked for SC/ST in 2024-2025?',
            'How much of the planned activity funding in a given Block is earmarked for SC and ST categories in a given Plan Year?',
            'How much of the sanctioned funding in a given block is earmarked for SC and ST categories in a given year?',
            'How much of the sanctioned funding in a given district is earmarked for SC and ST categories in a given year?',
            'How much of the sanctioned funding in a given gram panchayat is earmarked for SC and ST categories in a given year?',
        ],
    },

    'FND-006': {
        "abstract_question": 'How does the SC-category funding of {gp_name} compare with its total for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) FILTER (WHERE v.activity_for_label = 'sc') AS sc_targeted_activities,
       SUM(v.sc_amount) AS sc_amount,
       SUM(v.total_expenditure) AS total_amount,
       ROUND(100.0 * SUM(v.sc_amount) / NULLIF(SUM(v.total_expenditure),0), 2) AS pct_sc
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": "No resource-envelope or allocation table exists in the database - only actual expenditure is recorded, so planned allocation cannot be compared against it. The question was rewritten to compare SC funding against the GP's own total instead of against an envelope.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Category Funds',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            "How does Andhrua's SC-category funding compare with its total in 2024-2025?",
            'Does the SC-category planned funding of a given GP Name match its SC-category envelope allocation for a given Plan Year?',
            'How does the SC-category funding of a given gram panchayat compare with its total for a given year?',
            'How does the SC-category funding of a given district compare with its total for a given year?',
            'How does the SC-category funding of a given block compare with its total for a given year?',
        ],
    },

    'FND-007': {
        "abstract_question": 'Which GPs in {block_name} have sanctioned activities but no SC/ST earmark in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS total_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_sc,0) + COALESCE(v.fund_sanctioned_st,0)) AS sc_st_sanctioned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
HAVING COALESCE(SUM(COALESCE(v.fund_sanctioned_sc,0) + COALESCE(v.fund_sanctioned_st,0)),0) = 0
ORDER BY total_sanctioned DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Still no resource-envelope table, so this lists GPs with zero SC/ST earmark rather than GPs that had an envelope and did not use it. The SC/ST earmark columns are very sparsely populated.',
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Category Funds',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs sanctioned nothing for SC/ST in 2024-2025?',
            'Which GPs in a given Block have an SC or ST envelope allocation but no SC/ST-earmarked activities in a given Plan Year?',
            'Which GPs in a given block have sanctioned activities but no SC/ST earmark in a given year?',
            'Which GPs in a given district have sanctioned activities but no SC/ST earmark in a given year?',
            'Which GPs in a given gram panchayat have sanctioned activities but no SC/ST earmark in a given year?',
        ],
    },

    'FND-008': {
        "abstract_question": 'Which activities in {gp_name} are funded from more than one scheme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT a.activity_code, MAX(g.gp_name) AS gp_name, MAX(g.block_name) AS block_name,
       COUNT(DISTINCT e.scheme_name) AS distinct_schemes,
       STRING_AGG(DISTINCT e.scheme_name, ' | ') AS schemes,
       SUM(e.total_expenditure) AS total_expenditure
FROM activity_expenditure e
JOIN planned_activity a ON a.activity_code = e.activity_code
JOIN gram_panchayat g   ON g.gp_lgd_code = a.gp_lgd_code
WHERE e.fiscal_year = $date_range
  AND e.scheme_name IS NOT NULL
  AND ($district_name IS NULL OR g.zp_name = $district_name)
  AND ($block_name    IS NULL OR g.block_name = $block_name)
  AND ($gp_name       IS NULL OR g.gp_lgd_code = $gp_name)
GROUP BY a.activity_code
HAVING COUNT(DISTINCT e.scheme_name) > 1
ORDER BY distinct_schemes DESC, total_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Queries activity_expenditure directly (not v_activity) because the view collapses duplicate rows. scheme_name is NULL on 82% of rows, so multi-scheme activities are rarely detectable.',
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Multi-scheme',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which activities in Andhrua draw on more than one scheme in 2024-2025?',
            'Which activities in a given GP Name are funded from more than one scheme in a given Plan Year?',
            'Which activities in a given gram panchayat are funded from more than one scheme in a given year?',
            'Which activities in a given district are funded from more than one scheme in a given year?',
            'Which activities in a given block are funded from more than one scheme in a given year?',
        ],
    },

    'FND-009': {
        "abstract_question": 'Which scheme funds the largest number of activities in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name, '(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "scheme_name is NULL on 82% of expenditure rows; '(not recorded)' will usually top the list.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Multi-scheme',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which scheme funds the most activities in Bhubaneswar in 2024-2025?',
            'Which scheme funds the largest number of activities in a given Block in a given Plan Year?',
            'Which scheme funds the largest number of activities in a given block in a given year?',
            'Which scheme funds the largest number of activities in a given district in a given year?',
            'Which scheme funds the largest number of activities in a given gram panchayat in a given year?',
        ],
    },

    'FND-010': {
        "abstract_question": 'What is the total amount recorded per scheme across {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name, '(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Fund allocated' is not stored; approved cost and actual expenditure are returned instead.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Multi-scheme',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the total per scheme across Khordha in 2024-2025?',
            'What is the total fund allocated per scheme across a given District in a given Plan Year?',
            'What is the total amount recorded per scheme across a given district in a given year?',
            'What is the total amount recorded per scheme across a given block in a given year?',
            'What is the total amount recorded per scheme across a given gram panchayat in a given year?',
        ],
    },

    'FND-001': {
        "abstract_question": 'What is the split of tied and untied funds sanctioned to activities of {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.tied_untied, v.fund_component_name,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       ROUND(100.0 * SUM(COALESCE(v.fund_sanctioned_total,0))
             / NULLIF(SUM(SUM(COALESCE(v.fund_sanctioned_total,0))) OVER (),0), 2) AS pct_of_sanctioned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY sanctioned_amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Tied & Untied Funds',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            "What is Andhrua's tied vs untied split in 2024-2025?",
            'What is the split of tied and untied funds allocated to activities of a given GP Name in a given Plan Year?',
            'What is the split of tied and untied funds sanctioned to activities of a given gram panchayat in a given year?',
            'What is the split of tied and untied funds sanctioned to activities of a given district in a given year?',
            'What is the split of tied and untied funds sanctioned to activities of a given block in a given year?',
        ],
    },

    'FND-002': {
        "abstract_question": 'Which focus areas consume the largest share of tied funds in {block_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) FILTER (WHERE v.tied_untied = 'Tied') AS tied_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied') AS tied_amount,
       ROUND(100.0 * SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied')
             / NULLIF(SUM(SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied')) OVER (),0),
             2) AS pct_of_tied_funds
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied') > 0
ORDER BY tied_amount DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Tied & Untied Funds',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas absorb the most tied funding in Bhubaneswar in 2024-2025?',
            'Which focus areas consume the largest share of tied funds in a given Block in a given Plan Year?',
            'Which focus areas consume the largest share of tied funds in a given block in a given year?',
            'Which focus areas consume the largest share of tied funds in a given district in a given year?',
            'Which focus areas consume the largest share of tied funds in a given gram panchayat in a given year?',
        ],
    },

    'FND-003': {
        "abstract_question": 'How many activities in {gp_name} are funded entirely from untied funds in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) FILTER (WHERE v.tied_untied = 'Untied') AS untied_only_activities,
       COUNT(*) FILTER (WHERE v.tied_untied = 'Tied')   AS tied_activities,
       COUNT(*) FILTER (WHERE v.tied_untied = 'Other')  AS other_component_activities,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Untied') AS untied_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Entirely' is taken from the dominant component on the activity. Six activities have two admin_approval_scheme rows; query that table directly for a true multi-component split. Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Tied & Untied Funds',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua activities are wholly untied-funded in 2024-2025?',
            'How many activities in a given GP Name are funded entirely from untied funds in a given Plan Year?',
            'How many activities in a given gram panchayat are funded entirely from untied funds in a given year?',
            'How many activities in a given district are funded entirely from untied funds in a given year?',
            'How many activities in a given block are funded entirely from untied funds in a given year?',
        ],
    },

    'FND-004': {
        "abstract_question": 'What percentage of sanctioned funds in {district_name} is tied in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(COALESCE(v.fund_sanctioned_total,0)) AS total_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied')   AS tied_amount,
       SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Untied') AS untied_amount,
       SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Other')  AS other_amount,
       ROUND(100.0 * SUM(COALESCE(v.fund_sanctioned_total,0)) FILTER (WHERE v.tied_untied = 'Tied')
             / NULLIF(SUM(COALESCE(v.fund_sanctioned_total,0)),0), 2) AS pct_tied
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'Funds',
        "submodule": 'Tied & Untied Funds',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            "What share of Khordha's sanctioned funds is tied in 2024-2025?",
            'What percentage of total planned funds in a given District is tied in a given Plan Year?',
            'What percentage of sanctioned funds in a given district is tied in a given year?',
            'What percentage of sanctioned funds in a given block is tied in a given year?',
            'What percentage of sanctioned funds in a given gram panchayat is tied in a given year?',
        ],
    },

    'BUD-001': {
        "abstract_question": 'How much total funding is recorded for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.fiscal_year,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0))                AS plan_cost,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost_action_plan,
       SUM(COALESCE(v.admin_approved_cost,0))       AS admin_approved_cost,
       SUM(v.total_expenditure)                     AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'There is no funds-available/receipts table at GP level tied to the plan. The closest measures are the approved plan cost and actual expenditure. See BUD-002 note for the receipts alternative.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much total funding is recorded for Andhrua in 2024-2025?',
            'How much total funding is available to the Gram Panchayat for the financial year?',
            'How much total funding is recorded for a given gram panchayat in a given year?',
            'How much total funding is recorded for a given district in a given year?',
            'How much total funding is recorded for a given block in a given year?',
        ],
    },

    'BUD-002': {
        "abstract_question": 'How much funding is recorded from each funding source in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name, '(not recorded)') AS funding_source,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS amount,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_total
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Funding source is proxied by activity_expenditure.scheme_name, which has only 5 non-null values and is NULL on 82% of rows. MGNREGS and similar sources are not separable.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much funding came from each source in 2024-2025?',
            'How much funding is available from each funding source (CFC, SFC, Own Funds, MGNREGS, etc.) in a given year?',
            'How much funding is recorded from each funding source in a given year?',
            'How much funding is recorded from each funding source in a given year, for a given district?',
            'How much funding is recorded from each funding source in a given year, for a given block?',
            'How much funding is recorded from each funding source in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-003': {
        "abstract_question": 'How much funding is sanctioned under tied and untied components in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.tied_untied,
       COUNT(*) AS activities,
       SUM(COALESCE(v.fund_sanctioned_general,0)) AS general_amount,
       SUM(COALESCE(v.fund_sanctioned_sc,0))      AS sc_amount,
       SUM(COALESCE(v.fund_sanctioned_st,0))      AS st_amount,
       SUM(COALESCE(v.fund_sanctioned_total,0))   AS sanctioned_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY sanctioned_amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much was sanctioned as tied vs untied in 2024-2025?',
            'How much funding is available under Tied and Untied Funds in a given year?',
            'How much funding is sanctioned under tied and untied components in a given year?',
            'How much funding is sanctioned under tied and untied components in a given year, for a given district?',
            'How much funding is sanctioned under tied and untied components in a given year, for a given block?',
            'How much funding is sanctioned under tied and untied components in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-004': {
        "abstract_question": 'What percentage of the total comes from each funding source in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name, '(not recorded)') AS funding_source,
       SUM(v.total_expenditure) AS amount,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_total
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_of_total DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Same scheme_name coverage caveat as BUD-002.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What share came from each funding source in 2024-2025?',
            'What percentage of the total budget comes from each funding source in a given year?',
            'What percentage of the total comes from each funding source in a given year?',
            'What percentage of the total comes from each funding source in a given year, for a given district?',
            'What percentage of the total comes from each funding source in a given year, for a given block?',
            'What percentage of the total comes from each funding source in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-005': {
        "abstract_question": 'What percentage of the sanctioned budget is tied and untied in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.tied_untied,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       ROUND(100.0 * SUM(COALESCE(v.fund_sanctioned_total,0))
             / NULLIF(SUM(SUM(COALESCE(v.fund_sanctioned_total,0))) OVER (),0), 2) AS pct_of_sanctioned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_of_sanctioned DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the tied/untied share of the sanctioned budget in 2024-2025?',
            'What percentage of the total budget is tied and untied in a given year?',
            'What percentage of the sanctioned budget is tied and untied in a given year?',
            'What percentage of the sanctioned budget is tied and untied in a given year, for a given district?',
            'What percentage of the sanctioned budget is tied and untied in a given year, for a given block?',
            'What percentage of the sanctioned budget is tied and untied in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-006': {
        "abstract_question": 'How much planned expenditure is allocated to each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0))                AS planned_cost,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure)                     AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much planned expenditure goes to each GPDP theme in 2024-2025?',
            'How much planned expenditure is allocated to each GPDP theme in a given year?',
            'How much planned expenditure is allocated to each GPDP theme in a given year, for a given district?',
            'How much planned expenditure is allocated to each GPDP theme in a given year, for a given block?',
            'How much planned expenditure is allocated to each GPDP theme in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-007': {
        "abstract_question": 'Which GPDP theme has the highest planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the highest planned expenditure in 2024-2025?',
            'Which GPDP theme has the highest planned expenditure in a GP in a given year?',
            'Which GPDP theme has the highest planned expenditure in a given year?',
            'Which GPDP theme has the highest planned expenditure in a given year, for a given district?',
            'Which GPDP theme has the highest planned expenditure in a given year, for a given block?',
            'Which GPDP theme has the highest planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-008': {
        "abstract_question": 'Which GPDP theme has the lowest planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPDP theme has the lowest planned expenditure in 2024-2025?',
            'Which GPDP theme has the lowest planned expenditure in a given year?',
            'Which GPDP theme has the lowest planned expenditure in a given year, for a given district?',
            'Which GPDP theme has the lowest planned expenditure in a given year, for a given block?',
            'Which GPDP theme has the lowest planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-009': {
        "abstract_question": 'What percentage of total planned expenditure is allocated to each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_of_planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What share of planned expenditure goes to each theme in 2024-2025?',
            'What percentage of total planned expenditure is allocated to each GPDP theme in a given year?',
            'What percentage of total planned expenditure is allocated to each GPDP theme in a given year, for a given district?',
            'What percentage of total planned expenditure is allocated to each GPDP theme in a given year, for a given block?',
            'What percentage of total planned expenditure is allocated to each GPDP theme in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-010': {
        "abstract_question": 'Which GPDP themes have high planned expenditure but relatively few activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(SUM(COALESCE(v.total_cost,0)) / NULLIF(COUNT(*),0), 2) AS cost_per_activity,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY cost_per_activity DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are not defined in the source question, so the query ranks by cost per activity and shows both share columns.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes show high planned expenditure but relatively few activities in 2024-2025?',
            'Which GPDP themes receive high planned expenditure but relatively few activities in a given year?',
            'Which GPDP themes have high planned expenditure but relatively few activities in a given year?',
            'Which GPDP themes have high planned expenditure but relatively few activities in a given year, for a given district?',
            'Which GPDP themes have high planned expenditure but relatively few activities in a given year, for a given block?',
            'Which GPDP themes have high planned expenditure but relatively few activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-011': {
        "abstract_question": 'Which GPDP themes have many activities but relatively low planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(SUM(COALESCE(v.total_cost,0)) / NULLIF(COUNT(*),0), 2) AS cost_per_activity,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY cost_per_activity ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are not defined in the source question, so the query ranks by cost per activity and shows both share columns.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes show many activities but relatively low planned expenditure in 2024-2025?',
            'Which GPDP themes receive many activities but relatively low planned expenditure in a given year?',
            'Which GPDP themes have many activities but relatively low planned expenditure in a given year?',
            'Which GPDP themes have many activities but relatively low planned expenditure in a given year, for a given district?',
            'Which GPDP themes have many activities but relatively low planned expenditure in a given year, for a given block?',
            'Which GPDP themes have many activities but relatively low planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-012': {
        "abstract_question": 'Which GPDP themes have no planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COALESCE(SUM(COALESCE(v.total_cost,0)),0) = 0
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Only themes that appear in the plan are considered; use PLN-043 for themes with no activities at all.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes have no planned expenditure in 2024-2025?',
            'Which GPDP themes have no planned expenditure in a given year?',
            'Which GPDP themes have no planned expenditure in a given year, for a given district?',
            'Which GPDP themes have no planned expenditure in a given year, for a given block?',
            'Which GPDP themes have no planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-013': {
        "abstract_question": 'How much expenditure is planned under each theme for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0))                AS planned_cost,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure)                     AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much planned expenditure goes to each GPDP theme in 2024-2025?',
            'How much expenditure is planned under each theme for a GP in a given year?',
            'How much expenditure is planned under each theme for a given gram panchayat in a given year?',
            'How much expenditure is planned under each theme for a given district in a given year?',
            'How much expenditure is planned under each theme for a given block in a given year?',
        ],
    },

    'BUD-014': {
        "abstract_question": 'How has planned expenditure under each GPDP theme changed over the years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, v.fiscal_year,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY v.theme, v.fiscal_year
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'How has planned expenditure per theme changed year on year?',
            'How much expenditure is planned under each theme for a GP over the years?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given district?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given block?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-017': {
        "abstract_question": 'How has planned expenditure under each GPDP theme changed over the years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, v.fiscal_year,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY v.theme, v.fiscal_year
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'How has planned expenditure per theme changed year on year?',
            'How has planned expenditure under each GPDP theme changed over the last five years?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given district?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given block?',
            'How has planned expenditure under each GPDP theme changed over the years, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-018': {
        "abstract_question": 'How much planned expenditure is allocated to each focus area in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'How much planned expenditure goes to each focus area in 2024-2025?',
            'How much planned expenditure is allocated to each focus area in a given year?',
            'How much planned expenditure is allocated to each focus area in a given year, for a given district?',
            'How much planned expenditure is allocated to each focus area in a given year, for a given block?',
            'How much planned expenditure is allocated to each focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-019': {
        "abstract_question": 'How many activities under {focus_area} have planned expenditure greater than zero in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE COALESCE(v.total_cost,0) > 0) AS activities_with_planned_cost,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities_with_planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Sanitation activities have a planned cost above zero in 2024-2025?',
            'How many activities under a focus area with planned expenditure more than 0 in a given year?',
            'How many activities under a given focus area have planned expenditure greater than zero in a given year?',
            'How many activities under a given focus area have planned expenditure greater than zero in a given year, for a given district?',
            'How many activities under a given focus area have planned expenditure greater than zero in a given year, for a given block?',
            'How many activities under a given focus area have planned expenditure greater than zero in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-020': {
        "abstract_question": 'What are the activities with expenditure under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost AS planned_cost, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND COALESCE(v.total_expenditure,0) > 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC, v.total_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Sanitation activities have with expenditure in 2024-2025?',
            'What are the different activities with expenditure under a focus area in a given year?',
            'What are the activities with expenditure under a given focus area in a given year?',
            'What are the activities with expenditure under a given focus area in a given year, for a given district?',
            'What are the activities with expenditure under a given focus area in a given year, for a given block?',
            'What are the activities with expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-021': {
        "abstract_question": 'What are the activities with zero expenditure under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost AS planned_cost, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND COALESCE(v.total_expenditure,0) = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC, v.total_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Sanitation activities have with zero expenditure in 2024-2025?',
            'What are the different activities with zero expenditure under a focus area in a given year?',
            'What are the activities with zero expenditure under a given focus area in a given year?',
            'What are the activities with zero expenditure under a given focus area in a given year, for a given district?',
            'What are the activities with zero expenditure under a given focus area in a given year, for a given block?',
            'What are the activities with zero expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-022': {
        "abstract_question": 'Which focus area has the highest planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the highest planned expenditure in 2024-2025?',
            'Which focus area has the highest planned expenditure in a given year?',
            'Which focus area has the highest planned expenditure in a given year, for a given district?',
            'Which focus area has the highest planned expenditure in a given year, for a given block?',
            'Which focus area has the highest planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-023': {
        "abstract_question": 'Which focus area has the lowest planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_cost ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the lowest planned expenditure in 2024-2025?',
            'Which focus area has the lowest planned expenditure in a given year?',
            'Which focus area has the lowest planned expenditure in a given year, for a given district?',
            'Which focus area has the lowest planned expenditure in a given year, for a given block?',
            'Which focus area has the lowest planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-024': {
        "abstract_question": 'What percentage of total planned expenditure is allocated to each focus area in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_of_planned_cost DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Rate/Percentage',
        "answerable": 'Yes',
        "paraphrases": [
            'What share of planned expenditure goes to each focus area in 2024-2025?',
            'What percentage of total planned expenditure is allocated to each focus area in a given year?',
            'What percentage of total planned expenditure is allocated to each focus area in a given year, for a given district?',
            'What percentage of total planned expenditure is allocated to each focus area in a given year, for a given block?',
            'What percentage of total planned expenditure is allocated to each focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-025': {
        "abstract_question": 'Which focus areas receive high planned expenditure but relatively few activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(SUM(COALESCE(v.total_cost,0)) / NULLIF(COUNT(*),0), 2) AS cost_per_activity,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY cost_per_activity DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are undefined; ranked by cost per activity with both share columns shown.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas are out of step between cost and activity count in 2024-2025?',
            'Which focus areas receive high planned expenditure but relatively few activities in a given year?',
            'Which focus areas receive high planned expenditure but relatively few activities in a given year, for a given district?',
            'Which focus areas receive high planned expenditure but relatively few activities in a given year, for a given block?',
            'Which focus areas receive high planned expenditure but relatively few activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-026': {
        "abstract_question": 'Which focus areas receive many activities but relatively low planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       ROUND(SUM(COALESCE(v.total_cost,0)) / NULLIF(COUNT(*),0), 2) AS cost_per_activity,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       ROUND(100.0 * SUM(COALESCE(v.total_cost,0))
             / NULLIF(SUM(SUM(COALESCE(v.total_cost,0))) OVER (),0), 2) AS pct_of_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY cost_per_activity ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are undefined; ranked by cost per activity with both share columns shown.",
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas are out of step between cost and activity count in 2024-2025?',
            'Which focus areas receive many activities but relatively low planned expenditure in a given year?',
            'Which focus areas receive many activities but relatively low planned expenditure in a given year, for a given district?',
            'Which focus areas receive many activities but relatively low planned expenditure in a given year, for a given block?',
            'Which focus areas receive many activities but relatively low planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'BUD-027': {
        "abstract_question": 'Which focus areas receive no planned expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COALESCE(SUM(COALESCE(v.total_cost,0)),0) = 0
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Budgeting & Funding',
        "module": 'GPDP',
        "submodule": 'Budgeting',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas get no planned expenditure in 2024-2025?',
            'Which focus areas receive no planned expenditure in a given year?',
            'Which focus areas receive no planned expenditure in a given year, for a given district?',
            'Which focus areas receive no planned expenditure in a given year, for a given block?',
            'Which focus areas receive no planned expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SCH-001': {
        "abstract_question": 'How many activities are recorded under {scheme} in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name has only 5 non-null values and is NULL on 82% of rows.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many activities fall under XV Finance Commission in Khordha in 2024-2025?',
            'How many activities are recorded under a given Scheme in a given District for a given Plan Year?',
            'How many activities are recorded under a given scheme in a given district for a given year?',
            'How many activities are recorded under a given scheme in a given block for a given year?',
            'How many activities are recorded under a given scheme in a given gram panchayat for a given year?',
        ],
    },

    'SCH-002': {
        "abstract_question": 'Which activities of {gp_name} are funded under {scheme} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.focus_area_name,
       v.approved_cost_action_plan, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.scheme_name = $scheme
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name coverage is 18%.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Andhrua activities are funded under XV Finance Commission in 2024-2025?',
            'Which activities of a given GP Name are funded under a given Scheme in a given Plan Year?',
            'Which activities of a given gram panchayat are funded under a given scheme in a given year?',
            'Which activities of a given district are funded under a given scheme in a given year?',
            'Which activities of a given block are funded under a given scheme in a given year?',
        ],
    },

    'SCH-003': {
        "abstract_question": 'What is the total estimated cost of activities under {scheme} in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS estimated_cost,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name coverage is 18%.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the estimated cost under XV Finance Commission in Bhubaneswar in 2024-2025?',
            'What is the total estimated cost of activities under a given Scheme in a given Block for a given Plan Year?',
            'What is the total estimated cost of activities under a given scheme in a given block for a given year?',
            'What is the total estimated cost of activities under a given scheme in a given district for a given year?',
            'What is the total estimated cost of activities under a given scheme in a given gram panchayat for a given year?',
        ],
    },

    'SCH-005': {
        "abstract_question": 'Which scheme has the highest expenditure in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name coverage is 18%.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which scheme has the highest expenditure in Bhubaneswar in 2024-2025?',
            'Which scheme has the highest expenditure in a given Block for a given Plan Year?',
            'Which scheme has the highest expenditure in a given block for a given year?',
            'Which scheme has the highest expenditure in a given district for a given year?',
            'Which scheme has the highest expenditure in a given gram panchayat for a given year?',
        ],
    },

    'SCH-006': {
        "abstract_question": 'Which GPs in {block_name} have no activities under {scheme} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (
        SELECT 1 FROM v_activity v
        WHERE v.gp_lgd_code = g.gp_lgd_code
          AND v.fiscal_year = $date_range
          AND v.scheme_name = $scheme)
  AND ($block_name    IS NULL OR g.block_name = $block_name)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Because scheme_name is NULL on 82% of rows, many GPs appear here purely from missing data rather than genuine absence.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which GPs in Bhubaneswar have nothing under XV Finance Commission in 2024-2025?',
            'Which GPs in a given Block have no activities under a given Scheme in a given Plan Year?',
            'Which GPs in a given block have no activities under a given scheme in a given year?',
            'Which GPs in a given district have no activities under a given scheme in a given year?',
        ],
    },

    'SCH-007': {
        "abstract_question": 'Under which scheme and fund component is activity {activity_code} sanctioned?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.sanctioned_scheme_name, v.fund_component_name, v.tied_untied,
       v.fund_sanctioned_general, v.fund_sanctioned_sc, v.fund_sanctioned_st,
       v.fund_sanctioned_total,
       v.admin_approved_cost, v.total_expenditure,
       v.scheme_rows AS scheme_allocation_rows
FROM v_activity v
WHERE v.activity_code = $activity_code
""",
        "param_slots": [
            {'name': 'activity_code', 'entity_type': 'activity_code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Fully unblocked: admin_approval_scheme supplies both the scheme and the fund component, which the previous database could not. Returns no row if the activity was never sanctioned.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Lookup',
        "answerable": 'Yes',
        "paraphrases": [
            'Which scheme and component fund a given activity?',
            'Under which scheme and component is activity a given Activity Code funded?',
            'Under which scheme and fund component is activity a given activity sanctioned?',
        ],
    },

    'SCH-008': {
        "abstract_question": 'Compare the activity counts and expenditure of {scheme} and {scheme_2} in {district_name} for {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.scheme_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.scheme_name IN ($scheme, $scheme_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme'},
            {'name': 'scheme_2', 'entity_type': 'scheme_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name coverage is 18%.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'Compare XV Finance Commission with 5TH STATE FINANCE COMMISSION in Khordha in 2024-2025.',
            'Compare the activity counts and expenditure of a given Scheme and a given Scheme 2 in a given District for a given Plan Year.',
            'Compare the activity counts and expenditure of a given scheme and a second scheme in a given district for a given year.',
            'Compare the activity counts and expenditure of a given scheme and a second scheme in a given block for a given year.',
            'Compare the activity counts and expenditure of a given scheme and a second scheme in a given gram panchayat for a given year.',
        ],
    },

    'SCH-009': {
        "abstract_question": 'What is the status breakdown of activities under {scheme} in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.status_label, COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "scheme_name coverage is 18%; activity_status code 173 decodes to 'Buildings', which looks wrong.",
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the status breakdown under XV Finance Commission in Khordha in 2024-2025?',
            'What is the status breakdown of activities under a given Scheme in a given District for a given Plan Year?',
            'What is the status breakdown of activities under a given scheme in a given district for a given year?',
            'What is the status breakdown of activities under a given scheme in a given block for a given year?',
            'What is the status breakdown of activities under a given scheme in a given gram panchayat for a given year?',
        ],
    },

    'SCH-010': {
        "abstract_question": 'What is the General/SC/ST funding split under {scheme} in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS scheme_name,
       SUM(v.gen_amount) AS general_amount,
       SUM(v.sc_amount)  AS sc_amount,
       SUM(v.st_amount)  AS st_amount,
       SUM(v.total_expenditure) AS total_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'sc and st amounts are sparsely populated.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the General/SC/ST split under XV Finance Commission in Bhubaneswar in 2024-2025?',
            'What is the General/SC/ST funding split under a given Scheme in a given Block for a given Plan Year?',
            'What is the General/SC/ST funding split under a given scheme in a given block for a given year?',
            'What is the General/SC/ST funding split under a given scheme in a given district for a given year?',
            'What is the General/SC/ST funding split under a given scheme in a given gram panchayat for a given year?',
        ],
    },

    'SCH-011': {
        "abstract_question": 'What is the district-wise activity count under {scheme} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.district_name,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'scheme_name coverage is 18%.',
        "bracket": 'Budgeting & Funding',
        "module": 'Scheme',
        "submodule": 'Scheme Coverage',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the district-wise count under XV Finance Commission in 2024-2025?',
            'What is the district-wise activity count under a given Scheme across the state for a given Plan Year?',
            'What is the district-wise activity count under a given scheme for a given year?',
        ],
    },

    'EXP-001': {
        "abstract_question": 'What is the total actual expenditure incurred by {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.fiscal_year,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
ORDER BY total_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            "What is Andhrua's total actual expenditure in 2024-2025?",
            'What is the total actual expenditure incurred by the Gram Panchayat in the selected financial year?',
            'What is the total actual expenditure incurred by a given gram panchayat in a given year?',
            'What is the total actual expenditure incurred by a given district in a given year?',
            'What is the total actual expenditure incurred by a given block in a given year?',
        ],
    },

    'EXP-002': {
        "abstract_question": 'How has the total actual expenditure of {gp_name} changed over the years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.fiscal_year,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY 1
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Six years are present: 2020-2021 to 2025-2026.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            "How has Andhrua's expenditure changed year on year?",
            'How has the total actual expenditure changed over the last five years?',
            'How has the total actual expenditure of a given gram panchayat changed over the years?',
            'How has the total actual expenditure of a given district changed over the years?',
            'How has the total actual expenditure of a given block changed over the years?',
        ],
    },

    'EXP-003': {
        "abstract_question": 'What percentage of the planned expenditure has been utilised in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Rate/Percentage',
        "answerable": 'Yes',
        "paraphrases": [
            'What share of planned expenditure was utilised in 2024-2025?',
            'What percentage of the planned expenditure has been utilised in a given year?',
            'What percentage of the planned expenditure has been utilised in a given year, for a given district?',
            'What percentage of the planned expenditure has been utilised in a given year, for a given block?',
            'What percentage of the planned expenditure has been utilised in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-004': {
        "abstract_question": 'What is the total unspent amount (planned minus actual) in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure) AS unspent_amount,
       ROUND(100.0 * (SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure))
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_unspent
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Unspent' here is plan versus spend, not a cash balance - there is no opening/closing balance table.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the unspent amount in 2024-2025?',
            'What is the total unspent amount (planned expenditure vs. actual expenditure) in a given year?',
            'What is the total unspent amount (planned minus actual) in a given year?',
            'What is the total unspent amount (planned minus actual) in a given year, for a given district?',
            'What is the total unspent amount (planned minus actual) in a given year, for a given block?',
            'What is the total unspent amount (planned minus actual) in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-005': {
        "abstract_question": 'How many planned activities have recorded actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE v.total_expenditure > 0) AS activities_with_expenditure,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.total_expenditure > 0)
             / NULLIF(COUNT(*),0), 2) AS pct_with_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many planned activities recorded expenditure in 2024-2025?',
            'How many planned activities have recorded actual expenditure in a given year?',
            'How many planned activities have recorded actual expenditure in a given year, for a given district?',
            'How many planned activities have recorded actual expenditure in a given year, for a given block?',
            'How many planned activities have recorded actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-006': {
        "abstract_question": 'How much actual expenditure has been incurred under each funding source in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Funding source is proxied by scheme_name (5 non-null values, NULL on 82% of rows). 15th FC Tied/Untied cannot be separated.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much expenditure came from each funding source in 2024-2025?',
            'How much actual expenditure has been incurred under each funding source (15th FC Tied, 15th FC Untied, SFC, Own Funds, etc.) in a given year?',
            'How much actual expenditure has been incurred under each funding source in a given year?',
            'How much actual expenditure has been incurred under each funding source in a given year, for a given district?',
            'How much actual expenditure has been incurred under each funding source in a given year, for a given block?',
            'How much actual expenditure has been incurred under each funding source in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-007': {
        "abstract_question": 'What percentage of total actual expenditure comes from each funding source in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Funding source is proxied by scheme_name (5 non-null values, NULL on 82% of rows). 15th FC Tied/Untied cannot be separated.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'How much expenditure came from each funding source in 2024-2025?',
            'What percentage of total actual expenditure is contributed by each funding source in a given year?',
            'What percentage of total actual expenditure comes from each funding source in a given year?',
            'What percentage of total actual expenditure comes from each funding source in a given year, for a given district?',
            'What percentage of total actual expenditure comes from each funding source in a given year, for a given block?',
            'What percentage of total actual expenditure comes from each funding source in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-008': {
        "abstract_question": 'How much actual expenditure has been incurred under tied and untied funds in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.tied_untied,
       COUNT(*) AS activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.fund_sanctioned_total,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Expenditure can only be split tied/untied for sanctioned activities. Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much was spent from tied vs untied funds in 2024-2025?',
            'How much actual expenditure has been incurred under Tied and Untied Funds in a given year?',
            'How much actual expenditure has been incurred under tied and untied funds in a given year, for a given district?',
            'How much actual expenditure has been incurred under tied and untied funds in a given year, for a given block?',
            'How much actual expenditure has been incurred under tied and untied funds in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-009': {
        "abstract_question": 'How much tied-fund expenditure was incurred under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, v.tied_untied,
       COUNT(*) AS activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $focus_area = NULL to see every focus area. Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much tied-fund spending went to Sanitation in 2024-2025?',
            'Under ties funds, how much expenditure done under a given subject in a given year?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given district?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given block?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-010': {
        "abstract_question": 'How many activities have expenditure under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.total_expenditure > 0) AS activities_with_expenditure,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Sanitation activities have expenditure in 2024-2025?',
            'How many activities have expenditure under a given subject in a given year?',
            'How many activities have expenditure under a given focus area in a given year?',
            'How many activities have expenditure under a given focus area in a given year, for a given district?',
            'How many activities have expenditure under a given focus area in a given year, for a given block?',
            'How many activities have expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-011': {
        "abstract_question": 'How much tied-fund expenditure was incurred under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, v.tied_untied,
       COUNT(*) AS activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $focus_area = NULL to see every focus area. Tied/untied comes from admin_approval_scheme.scheme_component_code: 4249 = Tied Grant, 4211 = Basic Grant (untied), 4250 = Devolution of Fund (treated as untied). Codes 3880, 3907, 4251, 4252 and 0 are reported as 'Other' rather than guessed at. Only sanctioned activities carry a component, so this covers 2,101 activities, not the whole plan.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much tied-fund spending went to Sanitation in 2024-2025?',
            'Under the ties funds, how much expenditure was done under a given subject in a given year?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given district?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given block?',
            'How much tied-fund expenditure was incurred under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-012': {
        "abstract_question": 'Which funding source has the highest utilisation in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure) AS unspent_amount,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_utilised DESC NULLS LAST
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Funding source proxied by scheme_name.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which funding source has the highest utilisation in 2024-2025?',
            'Which funding source has the highest expenditure utilisation in a given year?',
            'Which funding source has the highest utilisation in a given year?',
            'Which funding source has the highest utilisation in a given year, for a given district?',
            'Which funding source has the highest utilisation in a given year, for a given block?',
            'Which funding source has the highest utilisation in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-013': {
        "abstract_question": 'Which funding source has the largest unspent amount in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure) AS unspent_amount,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY unspent_amount DESC NULLS LAST
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Funding source proxied by scheme_name.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which funding source has the largest unspent amount in 2024-2025?',
            'Which funding source has the largest unspent amount in a given year?',
            'Which funding source has the largest unspent amount in a given year, for a given district?',
            'Which funding source has the largest unspent amount in a given year, for a given block?',
            'Which funding source has the largest unspent amount in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-014': {
        "abstract_question": 'What is the total actual expenditure under each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure per GPDP theme in 2024-2025?',
            'What is the total actual expenditure under each GPDP theme in a given year?',
            'What is the total actual expenditure under each GPDP theme in a given year, for a given district?',
            'What is the total actual expenditure under each GPDP theme in a given year, for a given block?',
            'What is the total actual expenditure under each GPDP theme in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-015': {
        "abstract_question": 'Which GPDP theme has the highest actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, SUM(v.total_expenditure) AS actual_expenditure, COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme has the highest actual expenditure in 2024-2025?',
            'Which GPDP theme has the highest actual expenditure in a given year?',
            'Which GPDP theme has the highest actual expenditure in a given year, for a given district?',
            'Which GPDP theme has the highest actual expenditure in a given year, for a given block?',
            'Which GPDP theme has the highest actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-016': {
        "abstract_question": 'Which GPDP theme has the lowest actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, SUM(v.total_expenditure) AS actual_expenditure, COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme has the lowest actual expenditure in 2024-2025?',
            'Which GPDP theme has the lowest actual expenditure in a given year?',
            'Which GPDP theme has the lowest actual expenditure in a given year, for a given district?',
            'Which GPDP theme has the lowest actual expenditure in a given year, for a given block?',
            'Which GPDP theme has the lowest actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-017': {
        "abstract_question": 'What percentage of total actual expenditure goes to each GPDP theme in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_of_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What share of expenditure goes to each theme in 2024-2025?',
            'What percentage of total actual expenditure is allocated to each GPDP theme in a given year?',
            'What percentage of total actual expenditure goes to each GPDP theme in a given year?',
            'What percentage of total actual expenditure goes to each GPDP theme in a given year, for a given district?',
            'What percentage of total actual expenditure goes to each GPDP theme in a given year, for a given block?',
            'What percentage of total actual expenditure goes to each GPDP theme in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-018': {
        "abstract_question": 'Which GPDP themes have the highest expenditure utilisation in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING SUM(COALESCE(v.approved_cost_action_plan,0)) > 0
ORDER BY pct_utilised DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes utilise their planned cost best in 2024-2025?',
            'Which GPDP themes have the highest expenditure utilisation in a given year?',
            'Which GPDP themes have the highest expenditure utilisation in a given year, for a given district?',
            'Which GPDP themes have the highest expenditure utilisation in a given year, for a given block?',
            'Which GPDP themes have the highest expenditure utilisation in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-019': {
        "abstract_question": 'Which GPDP themes have the largest gap between planned and actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure) AS gap_amount,
       ROUND(100.0 * (SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure))
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS gap_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY gap_amount DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes show the largest plan-versus-spend gap in 2024-2025?',
            'Which GPDP themes have the largest gap between planned and actual expenditure in a given year?',
            'Which GPDP themes have the largest gap between planned and actual expenditure in a given year, for a given district?',
            'Which GPDP themes have the largest gap between planned and actual expenditure in a given year, for a given block?',
            'Which GPDP themes have the largest gap between planned and actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-020': {
        "abstract_question": 'Which theme has the highest utilisation of 15th CFC funds at Block level in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
HAVING SUM(COALESCE(v.approved_cost_action_plan,0)) > 0
ORDER BY pct_utilised DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $scheme = 'XV Finance Commission' for CFC or '5TH STATE FINANCE COMMISSION' for SFC. scheme_name is NULL on 82% of rows, so these totals understate reality.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme utilises 15th CFC funds best in 2024-2025?',
            'Which theme has the highest utilisation funds from the 15th CFC at Block level in a given year?',
            'Which theme has the highest utilisation of 15th CFC funds at Block level in a given year?',
            'Which theme has the highest utilisation of 15th CFC funds at Block level in a given year, for a given district?',
            'Which theme has the highest utilisation of 15th CFC funds at Block level in a given year, for a given block?',
            'Which theme has the highest utilisation of 15th CFC funds at Block level in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-021': {
        "abstract_question": 'Which theme has the highest utilisation of 15th CFC funds at District level in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
HAVING SUM(COALESCE(v.approved_cost_action_plan,0)) > 0
ORDER BY pct_utilised DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $scheme = 'XV Finance Commission' for CFC or '5TH STATE FINANCE COMMISSION' for SFC. scheme_name is NULL on 82% of rows, so these totals understate reality.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme utilises 15th CFC funds best in 2024-2025?',
            'Which theme has the highest utilisation of funds from the 15th CFC at the district level in a given year?',
            'Which theme has the highest utilisation of 15th CFC funds at District level in a given year?',
            'Which theme has the highest utilisation of 15th CFC funds at District level in a given year, for a given district?',
            'Which theme has the highest utilisation of 15th CFC funds at District level in a given year, for a given block?',
            'Which theme has the highest utilisation of 15th CFC funds at District level in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-022': {
        "abstract_question": 'Which theme has the highest utilisation of SFC funds at District level in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COALESCE(v.scheme_name,'(not recorded)') AS funding_source,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($scheme IS NULL OR v.scheme_name = $scheme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
HAVING SUM(COALESCE(v.approved_cost_action_plan,0)) > 0
ORDER BY pct_utilised DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'scheme', 'entity_type': 'scheme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Pass $scheme = 'XV Finance Commission' for CFC or '5TH STATE FINANCE COMMISSION' for SFC. scheme_name is NULL on 82% of rows, so these totals understate reality.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which theme utilises SFC funds best in 2024-2025?',
            'Which theme has the highest utilisation of funds from the SFC at the district level in a given year?',
            'Which theme has the highest utilisation of SFC funds at District level in a given year?',
            'Which theme has the highest utilisation of SFC funds at District level in a given year, for a given district?',
            'Which theme has the highest utilisation of SFC funds at District level in a given year, for a given block?',
            'Which theme has the highest utilisation of SFC funds at District level in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-023': {
        "abstract_question": 'What percentage of sanctioned funds was utilised in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(COALESCE(v.admin_approved_cost,0)) AS admin_sanctioned,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.admin_approved_cost,0)),0), 2) AS pct_of_sanctioned_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'admin_approved_cost is populated on only 2,247 of 12,730 expenditure rows, so the denominator is incomplete.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What share of sanctioned funds was utilised in 2024-2025?',
            'What percentage of sanctioned funds was utilized last financial year?',
            'What percentage of sanctioned funds was utilised in a given year?',
            'What percentage of sanctioned funds was utilised in a given year, for a given district?',
            'What percentage of sanctioned funds was utilised in a given year, for a given block?',
            'What percentage of sanctioned funds was utilised in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-024': {
        "abstract_question": 'What are the receipts, payments and closing balance for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.fiscal_year,
       SUM(v.amount) FILTER (WHERE v.direction = 'receipt') AS receipts,
       SUM(v.amount) FILTER (WHERE v.direction = 'payment') AS payments,
       SUM(v.amount) FILTER (WHERE v.direction = 'receipt')
       - SUM(v.amount) FILTER (WHERE v.direction = 'payment') AS closing_balance,
       ROUND(100.0 * SUM(v.amount) FILTER (WHERE v.direction = 'payment')
             / NULLIF(SUM(v.amount) FILTER (WHERE v.direction = 'receipt'),0), 2) AS pct_utilised
FROM v_voucher v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
ORDER BY closing_balance DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Derived from the voucher cashbook. There is no stored opening balance, so this is receipts minus payments within the year, not a true carry-forward.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            "What are Andhrua's receipts, payments and closing balance in 2024-2025?",
            'What is the closing/unspent balance carried forward to the next financial year, and as a percentage of total funds available?',
            'What are the receipts, payments and closing balance for a given gram panchayat in a given year?',
            'What are the receipts, payments and closing balance for a given district in a given year?',
            'What are the receipts, payments and closing balance for a given block in a given year?',
        ],
    },

    'EXP-025': {
        "abstract_question": 'What is the total actual expenditure under each focus area in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the expenditure per focus area in 2024-2025?',
            'What is the total actual expenditure under each focus area in a given year?',
            'What is the total actual expenditure under each focus area in a given year, for a given district?',
            'What is the total actual expenditure under each focus area in a given year, for a given block?',
            'What is the total actual expenditure under each focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-026': {
        "abstract_question": 'How many activities have expenditure under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) FILTER (WHERE v.total_expenditure > 0) AS activities_with_expenditure,
       COUNT(*) AS total_activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities_with_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Duplicate of EXP-010 in the source list.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities have expenditure under Sanitation in 2024-2025?',
            'How many activities have expenditure done under a given subject in a given year?',
            'How many activities have expenditure under a given focus area in a given year?',
            'How many activities have expenditure under a given focus area in a given year, for a given district?',
            'How many activities have expenditure under a given focus area in a given year, for a given block?',
            'How many activities have expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-027': {
        "abstract_question": 'List the activities with expenditure under {focus_area} in {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.focus_area_name, v.approved_cost_action_plan, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.total_expenditure > 0
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'List Sanitation activities with expenditure in 2024-2025.',
            'List the activities with expenditure done under a given subject or any particular Focus area in a given year.',
            'List the activities with expenditure under a given focus area in a given year.',
            'List the activities with expenditure under a given focus area in a given year, for a given district?',
            'List the activities with expenditure under a given focus area in a given year, for a given block?',
            'List the activities with expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-028': {
        "abstract_question": 'Which focus area has the highest actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, SUM(v.total_expenditure) AS actual_expenditure, COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set the geography parameters to choose the GP, Block or District level.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the highest expenditure in 2024-2025?',
            'Which focus area has the highest actual expenditure in a year at the GP/Block/District level?',
            'Which focus area has the highest actual expenditure in a given year?',
            'Which focus area has the highest actual expenditure in a given year, for a given district?',
            'Which focus area has the highest actual expenditure in a given year, for a given block?',
            'Which focus area has the highest actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-029': {
        "abstract_question": 'Which focus area has the lowest actual expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name, SUM(v.total_expenditure) AS actual_expenditure, COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Set the geography parameters to choose the GP, Block or District level.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus area has the lowest expenditure in 2024-2025?',
            'Which focus area has the lowest actual expenditure in a year at the GP/Block/District level?',
            'Which focus area has the lowest actual expenditure in a given year?',
            'Which focus area has the lowest actual expenditure in a given year, for a given district?',
            'Which focus area has the lowest actual expenditure in a given year, for a given block?',
            'Which focus area has the lowest actual expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-030': {
        "abstract_question": 'How many activities have expenditure under {focus_area} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) FILTER (WHERE v.total_expenditure > 0) AS activities_with_expenditure,
       COUNT(*) AS total_activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities_with_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Duplicate of EXP-010 in the source list.',
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many activities have expenditure under Sanitation in 2024-2025?',
            'How many activities with expenditure under a Focus areas in a given year?',
            'How many activities have expenditure under a given focus area in a given year?',
            'How many activities have expenditure under a given focus area in a given year, for a given district?',
            'How many activities have expenditure under a given focus area in a given year, for a given block?',
            'How many activities have expenditure under a given focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-031': {
        "abstract_question": 'Which activities have the highest expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.district_name,
       v.focus_area_name, v.approved_cost_action_plan, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which activities had the highest expenditure in 2024-2025?',
            'Which activities have the highest expenditure done in a given year?',
            'Which activities have the highest expenditure in a given year?',
            'Which activities have the highest expenditure in a given year, for a given district?',
            'Which activities have the highest expenditure in a given year, for a given block?',
            'Which activities have the highest expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-032': {
        "abstract_question": 'Which activities have the highest expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.district_name,
       v.focus_area_name, v.approved_cost_action_plan, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which activities had the highest expenditure in 2024-2025?',
            'Give a list of the top activities with expenditure in a GP in a given year.',
            'Which activities have the highest expenditure in a given year?',
            'Which activities have the highest expenditure in a given year, for a given district?',
            'Which activities have the highest expenditure in a given year, for a given block?',
            'Which activities have the highest expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-033': {
        "abstract_question": 'Which high-value activities (planned cost above {amount_threshold}) have no expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.approved_cost_action_plan, v.total_cost, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.total_expenditure,0) = 0
  AND COALESCE(v.approved_cost_action_plan, v.total_cost, 0) >= $amount_threshold
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY COALESCE(v.approved_cost_action_plan, v.total_cost) DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'amount_threshold', 'entity_type': 'amount_threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High-value' was undefined in the source question, so it is now the $amount_threshold parameter.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which activities above Rs 1,00,000 recorded no expenditure in 2024-2025?',
            'Which high-value activities have recorded no expenditure in a given year?',
            'Which high-value activities (planned cost above a given amount) have no expenditure in a given year?',
            'Which high-value activities (planned cost above a given amount) have no expenditure in a given year, for a given district?',
            'Which high-value activities (planned cost above a given amount) have no expenditure in a given year, for a given block?',
            'Which high-value activities (planned cost above a given amount) have no expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'EXP-034': {
        "abstract_question": 'Which activities have actual expenditure equal to the planned expenditure in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.approved_cost_action_plan AS planned_cost, v.total_expenditure,
       v.total_expenditure - COALESCE(v.approved_cost_action_plan,0) AS variance,
       v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.approved_cost_action_plan,0) > 0
  AND v.total_expenditure = v.approved_cost_action_plan
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY variance DESC, v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Andhrua activities have expenditure equal to plan in 2024-2025?',
            'Which activities have actual expenditure equal to the planned expenditure in a GP in a given year?',
            'Which activities have actual expenditure equal to the planned expenditure in a given gram panchayat in a given year?',
            'Which activities have actual expenditure equal to the planned expenditure in a given district in a given year?',
            'Which activities have actual expenditure equal to the planned expenditure in a given block in a given year?',
        ],
    },

    'EXP-035': {
        "abstract_question": 'Which activities have actual expenditure exceeding the planned expenditure in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.approved_cost_action_plan AS planned_cost, v.total_expenditure,
       v.total_expenditure - COALESCE(v.approved_cost_action_plan,0) AS variance,
       v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.approved_cost_action_plan,0) > 0
  AND v.total_expenditure > v.approved_cost_action_plan
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY variance DESC, v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Andhrua activities have expenditure exceeding plan in 2024-2025?',
            'Which activities have actual expenditure exceeding the planned expenditure in a GP in a given year?',
            'Which activities have actual expenditure exceeding the planned expenditure in a given gram panchayat in a given year?',
            'Which activities have actual expenditure exceeding the planned expenditure in a given district in a given year?',
            'Which activities have actual expenditure exceeding the planned expenditure in a given block in a given year?',
        ],
    },

    'EXP-036': {
        "abstract_question": 'How much expenditure went on creation of new assets in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.work_type_label,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label = 'New/Fresh'
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Uses work_type = 'New/Fresh'.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'How much did Andhrua spend on creation of new assets in 2024-2025?',
            'How much expenditure done on the creation of new assets in a GP in a given year?',
            'How much expenditure went on creation of new assets in a given gram panchayat in a given year?',
            'How much expenditure went on creation of new assets in a given district in a given year?',
            'How much expenditure went on creation of new assets in a given block in a given year?',
        ],
    },

    'EXP-037': {
        "abstract_question": 'How much expenditure went on repair and maintenance in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.work_type_label,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label = 'Maintenance'
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Uses work_type = 'Maintenance'.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'How much did Andhrua spend on repair and maintenance in 2024-2025?',
            'How much expenditure done on repair of Infrastructure in a GP in a given year?',
            'How much expenditure went on repair and maintenance in a given gram panchayat in a given year?',
            'How much expenditure went on repair and maintenance in a given district in a given year?',
            'How much expenditure went on repair and maintenance in a given block in a given year?',
        ],
    },

    'EXP-038': {
        "abstract_question": 'How much expenditure went on administrative activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.focus_area_name IN ('Administrative & Technical Support', 'GP Office Infrastructure')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Administrative' is interpreted as the focus areas 'Administrative & Technical Support' and 'GP Office Infrastructure'; there is no explicit admin-expenditure flag.",
        "bracket": 'Expenditure',
        "module": 'GPDP',
        "submodule": 'Expenditure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'How much was spent on administrative activities in 2024-2025?',
            'How much expenditure is done on administrative activities in a year?',
            'How much expenditure went on administrative activities in a given year?',
            'How much expenditure went on administrative activities in a given year, for a given district?',
            'How much expenditure went on administrative activities in a given year, for a given block?',
            'How much expenditure went on administrative activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SAN-001': {
        "abstract_question": 'How many activities in {gp_name} received administrative approval in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS admin_approved_activities,
       COUNT(*) AS total_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_admin_approved = 1)
             / NULLIF(COUNT(*),0), 2) AS pct_approved
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'There is no approval-date or approval-flag column. Administrative approval is proxied by admin_approved_cost > 0, populated on 2,247 of 12,730 rows.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua activities got administrative approval in 2024-2025?',
            'How many activities in a given GP Name received administrative approval in a given Plan Year?',
            'How many activities in a given gram panchayat received administrative approval in a given year?',
            'How many activities in a given district received administrative approval in a given year?',
            'How many activities in a given block received administrative approval in a given year?',
        ],
    },

    'SAN-002': {
        "abstract_question": 'How many activities in {block_name} are still awaiting administrative approval in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS sanctioned,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 0) AS awaiting_sanction,
       COUNT(*) FILTER (WHERE v.has_approval_cost_only = 1) AS cost_recorded_but_no_approval_row,
       SUM(COALESCE(v.total_cost,0)) FILTER (WHERE v.is_admin_approved = 0) AS cost_awaiting
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Now based on the presence of an admin_approval row rather than a non-zero cost. The third column counts the 140 activities that have an admin_approved_cost but no approval record - a data-quality signal worth watching. Administrative approval now comes from the admin_approval table: 2,101 of 12,704 activities (17%) have a sanction record. A further 140 activities carry an admin_approved_cost with no approval row - v_activity.has_approval_cost_only flags those.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Bhubaneswar activities await sanction in 2024-2025?',
            'How many approved-plan activities in a given Block are still awaiting administrative approval in a given year?',
            'How many activities in a given block are still awaiting administrative approval in a given year?',
            'How many activities in a given district are still awaiting administrative approval in a given year?',
            'How many activities in a given gram panchayat are still awaiting administrative approval in a given year?',
        ],
    },

    'SAN-003': {
        "abstract_question": 'What is the total administratively sanctioned amount for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       SUM(COALESCE(v.admin_approved_cost,0))     AS admin_sanctioned_amount,
       SUM(COALESCE(v.technical_approved_cost,0)) AS technical_sanctioned_amount,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS sanctioned_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY admin_sanctioned_amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            "What is Andhrua's total administratively sanctioned amount in 2024-2025?",
            'What is the total administratively sanctioned amount for activities of a given GP Name in a given Plan Year?',
            'What is the total administratively sanctioned amount for a given gram panchayat in a given year?',
            'What is the total administratively sanctioned amount for a given district in a given year?',
            'What is the total administratively sanctioned amount for a given block in a given year?',
        ],
    },

    'SAN-004': {
        "abstract_question": 'What is the block-wise administratively sanctioned amount in {district_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS sanctioned_activities,
       SUM(COALESCE(v.admin_approved_cost,0)) AS admin_sanctioned_amount,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1
ORDER BY admin_sanctioned_amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Aggregation',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the block-wise sanctioned amount in Khordha in 2024-2025?',
            'What is the total administratively sanctioned amount in a given District in a given Plan Year, block-wise?',
            'What is the block-wise administratively sanctioned amount in a given district in a given year?',
        ],
    },

    'SAN-005': {
        "abstract_question": 'What are the administrative approval order number, date and issuing authority for activity {activity_code}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.adm_approval_no        AS admin_approval_no,
       v.sanction_day           AS admin_sanction_date,
       v.sanction_authority     AS admin_issuing_authority,
       v.sanction_authority_raw AS admin_authority_as_recorded,
       v.work_proposed_cost,
       v.admin_approved_cost,
       v.tec_approval_order_no  AS technical_order_no,
       v.tec_approval_order_date AS technical_order_date,
       v.tec_approval_authority AS technical_authority,
       v.tec_approval_cost      AS technical_approved_cost
FROM v_activity v
WHERE v.activity_code = $activity_code
""",
        "param_slots": [
            {'name': 'activity_code', 'entity_type': 'activity_code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Unblocked by the new admin_approval and technical_approval tables. Returns no row if the activity was never sanctioned. 3.5% of technical order numbers are the placeholder 'NR' (not recorded).",
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Lookup',
        "answerable": 'Yes',
        "paraphrases": [
            'What are the sanction details for a given activity code?',
            'What are the administrative approval order number, date, and issuing authority for activity a given Activity Code?',
            'What are the administrative approval order number, date and issuing authority for activity a given activity?',
        ],
    },

    'SAN-006': {
        "abstract_question": 'How many activities in {block_name} were administratively sanctioned by each issuing authority in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.sanction_authority AS issuing_authority,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.work_proposed_cost,0)) AS proposed_cost,
       SUM(COALESCE(v.admin_approved_cost,0)) AS sanctioned_amount,
       MIN(v.sanction_day) AS first_sanction,
       MAX(v.sanction_day) AS last_sanction
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY sanctioned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "adm_approval_authority is free text with many spellings of the same office. The view collapses the obvious variants (SARPANCH / SARAPANCH / Sarapancha / sarpancha all become 'Sarpanch') into sanction_authority; sanction_authority_raw keeps the original. A long tail of one-off spellings remains.",
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Bhubaneswar activities did each authority sanction in 2024-2025?',
            'How many activities in a given Block were administratively sanctioned by each issuing authority in a given Plan Year?',
            'How many activities in a given block were administratively sanctioned by each issuing authority in a given year?',
            'How many activities in a given district were administratively sanctioned by each issuing authority in a given year?',
            'How many activities in a given gram panchayat were administratively sanctioned by each issuing authority in a given year?',
        ],
    },

    'SAN-007': {
        "abstract_question": 'What percentage of planned activities in {block_name} have received administrative approval in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name,
       COUNT(*) AS planned_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_admin_approved = 1)
             / NULLIF(COUNT(*),0), 2) AS pct_approved
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY pct_approved DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by admin_approved_cost > 0.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What share of Bhubaneswar activities are administratively approved in 2024-2025?',
            'What percentage of planned activities in a given Block have received administrative approval in a given Plan Year?',
            'What percentage of planned activities in a given block have received administrative approval in a given year?',
            'What percentage of planned activities in a given district have received administrative approval in a given year?',
            'What percentage of planned activities in a given gram panchayat have received administrative approval in a given year?',
        ],
    },

    'SAN-008': {
        "abstract_question": 'Which blocks in {district_name} have the lowest administrative approval coverage in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(*) AS planned_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_admin_approved = 1)
             / NULLIF(COUNT(*),0), 2) AS pct_approved
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY pct_approved ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Approval proxied by admin_approved_cost > 0.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Khordha blocks have the weakest approval coverage in 2024-2025?',
            'Which blocks in a given District have the lowest administrative approval coverage of planned activities in a given year?',
            'Which blocks in a given district have the lowest administrative approval coverage in a given year?',
        ],
    },

    'SAN-009': {
        "abstract_question": 'How many activities were administratively sanctioned in each month of {date_range} in {block_name}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT CAST(v.sanction_month AS DATE) AS month,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.admin_approved_cost,0)) AS sanctioned_amount,
       COUNT(DISTINCT v.gp_lgd_code) AS gps
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Unblocked by admin_approval.adm_approval_sanction_date. Note that sanction dates run well outside the plan year they belong to - 2020-2021 activities carry sanction dates as late as 2026 - so months will spread beyond the twelve you might expect.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            'What is the monthly sanction profile for Bhubaneswar in 2024-2025?',
            'How many activities were administratively sanctioned in each month of a given Plan Year in a given Block?',
            'How many activities were administratively sanctioned in each month of a given year in a given block?',
            'How many activities were administratively sanctioned in each month of a given year in a given district?',
            'How many activities were administratively sanctioned in each month of a given year in a given gram panchayat?',
        ],
    },

    'SAN-010': {
        "abstract_question": 'How many administrative approvals in {district_name} were issued in each quarter of {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.sanction_quarter AS calendar_quarter,
       YEAR(v.sanction_date) AS sanction_year,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.admin_approved_cost,0)) AS sanctioned_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY sanction_year, calendar_quarter
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Quarters are calendar quarters of the sanction date, shown with their year because sanctions for one plan year are spread across several calendar years in this data.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the quarterly sanction profile for Khordha in 2024-2025?',
            'How many administrative approvals in a given District were issued in the last quarter of a given Plan Year?',
            'How many administrative approvals in a given district were issued in each quarter of a given year?',
            'How many administrative approvals in a given block were issued in each quarter of a given year?',
            'How many administrative approvals in a given gram panchayat were issued in each quarter of a given year?',
        ],
    },

    'SAN-011': {
        "abstract_question": 'Which activities in {district_name} received the highest administratively sanctioned amounts in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.sanction_day, v.sanction_authority,
       v.admin_approved_cost, v.fund_sanctioned_total,
       v.sanctioned_scheme_name, v.tied_untied,
       v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.admin_approved_cost DESC NULLS LAST
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Now enriched with the sanction date, authority, scheme and tied/untied component.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha activities got the biggest sanctions in 2024-2025?',
            'Which activities in a given District received the highest administratively sanctioned amounts in a given Plan Year?',
            'Which activities in a given district received the highest administratively sanctioned amounts in a given year?',
            'Which activities in a given block received the highest administratively sanctioned amounts in a given year?',
            'Which activities in a given gram panchayat received the highest administratively sanctioned amounts in a given year?',
        ],
    },

    'SAN-012': {
        "abstract_question": 'Which GPs in {block_name} have the highest total proposed cost awaiting administrative sanction in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 0) AS activities_awaiting,
       SUM(COALESCE(v.total_cost,0)) FILTER (WHERE v.is_admin_approved = 0) AS proposed_cost_awaiting,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY proposed_cost_awaiting DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": "'Awaiting sanction' now means no row in admin_approval. Administrative approval now comes from the admin_approval table: 2,101 of 12,704 activities (17%) have a sanction record. A further 140 activities carry an admin_approved_cost with no approval row - v_activity.has_approval_cost_only flags those.",
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs have the most value awaiting sanction in 2024-2025?',
            'Which GPs in a given Block have the highest total proposed cost of activities awaiting administrative sanction in a given year?',
            'Which GPs in a given block have the highest total proposed cost awaiting administrative sanction in a given year?',
            'Which GPs in a given district have the highest total proposed cost awaiting administrative sanction in a given year?',
            'Which GPs in a given gram panchayat have the highest total proposed cost awaiting administrative sanction in a given year?',
        ],
    },

    'SAN-013': {
        "abstract_question": 'What is the scheme-wise split of administratively sanctioned amounts in {gp_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.sanctioned_scheme_name, v.fund_component_name, v.tied_untied,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_total,0)) AS sanctioned_amount,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
ORDER BY sanctioned_amount DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Uses the sanctioned scheme from admin_approval_scheme, which is far more reliable than activity_expenditure.scheme_name (82% NULL). Two scheme codes, 1518 and 1526, are not in the decoder and show as 'Code nnnn'.",
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            "What is Andhrua's scheme-wise sanction split in 2024-2025?",
            'What is the scheme-wise split of administratively sanctioned amounts in a given GP Name for a given Plan Year?',
            'What is the scheme-wise split of administratively sanctioned amounts in a given gram panchayat for a given year?',
            'What is the scheme-wise split of administratively sanctioned amounts in a given district for a given year?',
            'What is the scheme-wise split of administratively sanctioned amounts in a given block for a given year?',
        ],
    },

    'SAN-014': {
        "abstract_question": 'What is the General/SC/ST split of administratively sanctioned funds in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_for_label AS target_category,
       COUNT(*) AS sanctioned_activities,
       SUM(COALESCE(v.fund_sanctioned_general,0)) AS general_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_sc,0))      AS sc_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_st,0))      AS st_sanctioned,
       SUM(COALESCE(v.fund_sanctioned_total,0))   AS total_sanctioned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY total_sanctioned DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Now uses the real sanctioned-fund category columns. SC and ST earmarks are populated on under 1% of approval rows, so the split is dominated by the general column.',
        "bracket": 'Sanctions & Approvals',
        "module": 'Sanctions',
        "submodule": 'Administrative Approval',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the General/SC/ST sanction split in Bhubaneswar in 2024-2025?',
            'What is the General/SC/ST split of administratively sanctioned funds in a given Block for a given Plan Year?',
            'What is the General/SC/ST split of administratively sanctioned funds in a given block for a given year?',
            'What is the General/SC/ST split of administratively sanctioned funds in a given district for a given year?',
            'What is the General/SC/ST split of administratively sanctioned funds in a given gram panchayat for a given year?',
        ],
    },

    'STS-001': {
        "abstract_question": 'How many activities in {gp_name} are in each progress status for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.status_label, COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "activity_status code 173 decodes to 'Buildings' in dim_code, which is not a status and needs verifying.",
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua activities are in each status in 2024-2025?',
            'How many activities in a given GP Name are in each progress status for a given Plan Year?',
            'How many activities in a given gram panchayat are in each progress status for a given year?',
            'How many activities in a given district are in each progress status for a given year?',
            'How many activities in a given block are in each progress status for a given year?',
        ],
    },

    'STS-002': {
        "abstract_question": 'What is the block-wise activity status breakdown in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.status_label, COUNT(*) AS activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY v.block_name, activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'See STS-001 note on code 173.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the block-wise status breakdown in Khordha in 2024-2025?',
            'What is the block-wise activity status breakdown in a given District for a given Plan Year?',
            'What is the block-wise activity status breakdown in a given district for a given year?',
        ],
    },

    'STS-003': {
        "abstract_question": 'How many activities in {block_name} are in {status} status for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.status_label, COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($status IS NULL OR v.status_label = $status)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'status', 'entity_type': 'status', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": '$status must match a decoded label exactly: Activity Approved, WORK ONGOING, WORK COMPLETED, WORK ABANDONED, UNDER APPROVAL.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Bhubaneswar activities are WORK ONGOING in 2024-2025?',
            'How many activities in a given Block are in a given Status status for a given Plan Year?',
            'How many activities in a given block are in a given status status for a given year?',
            'How many activities in a given district are in a given status status for a given year?',
            'How many activities in a given gram panchayat are in a given status status for a given year?',
        ],
    },

    'STS-004': {
        "abstract_question": 'Which GPs in {district_name} have the highest number of abandoned activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       SUM(v.is_abandoned) AS abandoned_activities,
       COUNT(*) AS total_activities,
       SUM(v.total_expenditure) FILTER (WHERE v.is_abandoned = 1) AS expenditure_on_abandoned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2,3
HAVING SUM(v.is_abandoned) > 0
ORDER BY abandoned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha GPs have the most abandoned activities in 2024-2025?',
            'Which GPs in a given District have the highest number of abandoned activities in a given Plan Year?',
            'Which GPs in a given district have the highest number of abandoned activities in a given year?',
        ],
    },

    'STS-005': {
        "abstract_question": 'Which activities in {block_name} are abandoned, and what are their costs in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost AS estimated_cost, v.admin_approved_cost,
       v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_abandoned = 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_cost DESC NULLS LAST
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "There is no 'suspended' status in the data; the closest is WORK ABANDONED, which is what this query returns.",
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar activities are abandoned and at what cost in 2024-2025?',
            'Which activities in a given Block are currently suspended, and what are their estimated costs in a given year?',
            'Which activities in a given block are abandoned, and what are their costs in a given year?',
            'Which activities in a given district are abandoned, and what are their costs in a given year?',
            'Which activities in a given gram panchayat are abandoned, and what are their costs in a given year?',
        ],
    },

    'STS-006': {
        "abstract_question": 'What percentage of taken-up activities in {block_name} are completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(v.is_started)   AS taken_up_activities,
       SUM(v.is_completed) AS completed_activities,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(SUM(v.is_started),0), 2) AS pct_completed
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            "What share of Bhubaneswar's started activities are complete in 2024-2025?",
            'What percentage of taken-up activities in a given Block are completed in a given Plan Year?',
            'What percentage of taken-up activities in a given block are completed in a given year?',
            'What percentage of taken-up activities in a given district are completed in a given year?',
            'What percentage of taken-up activities in a given gram panchayat are completed in a given year?',
        ],
    },

    'STS-007': {
        "abstract_question": 'Which blocks in {district_name} have the highest activity completion rate for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(v.is_started)   AS started,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS pct_completed
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY pct_completed DESC, activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Khordha blocks complete the most activities in 2024-2025?',
            'Which blocks in a given District have the highest activity completion rate for a given Plan Year?',
            'Which blocks in a given district have the highest activity completion rate for a given year?',
        ],
    },

    'STS-008': {
        "abstract_question": 'What share of approved activities in {district_name} has not yet started in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.status_label = 'Activity Approved') AS approved_not_started,
       SUM(v.is_started) AS started,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.status_label = 'Activity Approved')
             / NULLIF(COUNT(*),0), 2) AS pct_not_started
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Not started' is read as status 'Activity Approved' - approved but with no work status recorded.",
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            "What share of Khordha's approved activities have not started in 2024-2025?",
            'What share of approved activities in a given District has not yet started in a given Plan Year?',
            'What share of approved activities in a given district has not yet started in a given year?',
            'What share of approved activities in a given block has not yet started in a given year?',
            'What share of approved activities in a given gram panchayat has not yet started in a given year?',
        ],
    },

    'STS-009': {
        "abstract_question": 'Which GPs in {block_name} have zero completed activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(v.is_completed) AS completed
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
HAVING SUM(v.is_completed) = 0
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs completed nothing in 2024-2025?',
            'Which GPs in a given Block have zero completed activities in a given Plan Year?',
            'Which GPs in a given block have zero completed activities in a given year?',
            'Which GPs in a given district have zero completed activities in a given year?',
            'Which GPs in a given gram panchayat have zero completed activities in a given year?',
        ],
    },

    'STS-010': {
        "abstract_question": 'How many activities in {block_name} are stuck in Under Approval status for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) FILTER (WHERE v.is_under_approval = 1) AS under_approval,
       COUNT(*) AS total_activities,
       SUM(COALESCE(v.total_cost,0)) FILTER (WHERE v.is_under_approval = 1) AS cost_under_approval
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": '36 activities carry this status across the whole database.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Bhubaneswar activities sit in Under Approval in 2024-2025?',
            'How many activities in a given Block are stuck in Under Approval status for a given Plan Year?',
            'How many activities in a given block are stuck in Under Approval status for a given year?',
            'How many activities in a given district are stuck in Under Approval status for a given year?',
            'How many activities in a given gram panchayat are stuck in Under Approval status for a given year?',
        ],
    },

    'STS-011': {
        "abstract_question": 'Which blocks in {district_name} have every taken-up activity started for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(v.is_started) AS started,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS pct_started
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
HAVING SUM(v.is_started) = COUNT(*)
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Khordha blocks have started every taken-up activity in 2024-2025?',
            'Which blocks in a given District have every taken-up activity started for a given Plan Year?',
            'Which blocks in a given district have every taken-up activity started for a given year?',
        ],
    },

    'STS-012': {
        "abstract_question": 'How many plan units and taken-up activities does {gp_name} have for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(DISTINCT v.plan_code) AS plan_units,
       COUNT(*) AS planned_activities,
       SUM(v.is_started)   AS taken_up_activities,
       SUM(v.is_completed) AS completed_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many plans and started activities does Andhrua have in 2024-2025?',
            'How many plan units and how many taken-up activities does a given GP Name have for a given Plan Year?',
            'How many plan units and taken-up activities does a given gram panchayat have for a given year?',
            'How many plan units and taken-up activities does a given district have for a given year?',
            'How many plan units and taken-up activities does a given block have for a given year?',
        ],
    },

    'STS-013': {
        "abstract_question": 'What is the district-wise activity status summary for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.district_name,
       COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.status_label = 'Activity Approved') AS approved_not_started,
       SUM(v.is_ongoing)   AS ongoing,
       SUM(v.is_completed) AS completed,
       SUM(v.is_abandoned) AS abandoned,
       SUM(v.is_under_approval) AS under_approval
FROM v_activity v
WHERE v.fiscal_year = $date_range
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'Activity Status',
        "submodule": 'Status Counts',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the district-wise status summary in 2024-2025?',
            'What is the district-wise activity status summary across the state for a given Plan Year?',
            'What is the district-wise activity status summary for a given year?',
        ],
    },

    'IMP-001': {
        "abstract_question": 'How many planned activities have been initiated in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS planned_activities,
       SUM(v.is_started) AS initiated_activities,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS initiation_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Initiated' = status WORK ONGOING or WORK COMPLETED.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua activities were initiated in 2024-2025?',
            'How many planned activities have been initiated in a GP in a year?',
            'How many planned activities have been initiated in a given gram panchayat in a given year?',
            'How many planned activities have been initiated in a given district in a given year?',
            'How many planned activities have been initiated in a given block in a given year?',
        ],
    },

    'IMP-002': {
        "abstract_question": 'How many initiated activities have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(v.is_started)   AS initiated_activities,
       SUM(v.is_completed) AS completed_activities,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(SUM(v.is_started),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many initiated activities were completed in 2024-2025?',
            'How many initiated activities have been completed in a given year?',
            'How many initiated activities have been completed in a given year, for a given district?',
            'How many initiated activities have been completed in a given year, for a given block?',
            'How many initiated activities have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-003': {
        "abstract_question": 'How many planned activities have not yet been initiated in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS planned_activities,
       COUNT(*) - SUM(v.is_started) AS not_initiated,
       SUM(COALESCE(v.total_cost,0)) FILTER (WHERE v.is_started = 0) AS cost_not_initiated
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Includes both 'Activity Approved' and 'UNDER APPROVAL' activities.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua activities have not started in 2024-2025?',
            'How many planned activities have not yet been initiated in a GP in a given year?',
            'How many planned activities have not yet been initiated in a given gram panchayat in a given year?',
            'How many planned activities have not yet been initiated in a given district in a given year?',
            'How many planned activities have not yet been initiated in a given block in a given year?',
        ],
    },

    'IMP-004': {
        "abstract_question": 'What is the initiation rate under each theme and focus area in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_started) AS initiation_count,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS initiation_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY initiation_rate_pct DESC, planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the initiation rate per theme in 2024-2025?',
            'What is the initiation rate under each theme/focus area in a given year?',
            'What is the initiation rate under each theme and focus area in a given year?',
            'What is the initiation rate under each theme and focus area in a given year, for a given district?',
            'What is the initiation rate under each theme and focus area in a given year, for a given block?',
            'What is the initiation rate under each theme and focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-005': {
        "abstract_question": 'What is the completion rate under each theme and focus area in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_completed) AS completion_count,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY completion_rate_pct DESC, planned_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Rate/Percentage',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the completion rate per theme in 2024-2025?',
            'What is the completion rate under each theme/focus area in a given year?',
            'What is the completion rate under each theme and focus area in a given year?',
            'What is the completion rate under each theme and focus area in a given year, for a given district?',
            'What is the completion rate under each theme and focus area in a given year, for a given block?',
            'What is the completion rate under each theme and focus area in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-006': {
        "abstract_question": 'Which themes have the highest number of completed activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(v.is_completed) AS completed_activities,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY completed_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes completed the most activities in 2024-2025?',
            'Which themes/focus areas have the highest number of completed activities in a given year?',
            'Which themes have the highest number of completed activities in a given year?',
            'Which themes have the highest number of completed activities in a given year, for a given district?',
            'Which themes have the highest number of completed activities in a given year, for a given block?',
            'Which themes have the highest number of completed activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-007': {
        "abstract_question": 'Which themes have the largest implementation gap (planned versus initiated) in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(v.is_started) AS initiated_activities,
       COUNT(*) - SUM(v.is_started) AS implementation_gap,
       ROUND(100.0 * (COUNT(*) - SUM(v.is_started)) / NULLIF(COUNT(*),0), 2) AS gap_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY implementation_gap DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes show the biggest planned-versus-started gap in 2024-2025?',
            'Which themes have the largest implementation gap(planned vs initiated) in a given year?',
            'Which themes have the largest implementation gap (planned versus initiated) in a given year?',
            'Which themes have the largest implementation gap (planned versus initiated) in a given year, for a given district?',
            'Which themes have the largest implementation gap (planned versus initiated) in a given year, for a given block?',
            'Which themes have the largest implementation gap (planned versus initiated) in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-008': {
        "abstract_question": 'Which focus area has the highest number of completed activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_completed) AS completed_activities
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY completed_activities DESC, planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus area completed the most activities in 2024-2025?',
            'Which focus area has the highest number of completed activities in a given year?',
            'Which focus area has the highest number of completed activities in a given year, for a given district?',
            'Which focus area has the highest number of completed activities in a given year, for a given block?',
            'Which focus area has the highest number of completed activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-009': {
        "abstract_question": 'Which focus area has the lowest completion rate in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_completed) AS completed_activities,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(*) >= $threshold
ORDER BY completion_rate_pct ASC, planned_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
            {'name': 'threshold', 'entity_type': 'threshold'},
        ],
        "result_ttl_seconds": 600,
        "caveat": '$threshold sets a minimum activity count so focus areas with one or two activities do not dominate the ranking. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus area completes least in 2024-2025?',
            'Which focus area has the lowest completion rate in a given year?',
            'Which focus area has the lowest completion rate in a given year, for a given district?',
            'Which focus area has the lowest completion rate in a given year, for a given block?',
            'Which focus area has the lowest completion rate in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-010': {
        "abstract_question": 'Which focus areas have the largest implementation gap (planned versus initiated) in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_started) AS initiated_activities,
       COUNT(*) - SUM(v.is_started) AS implementation_gap,
       ROUND(100.0 * (COUNT(*) - SUM(v.is_started)) / NULLIF(COUNT(*),0), 2) AS gap_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY implementation_gap DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas show the biggest planned-versus-started gap in 2024-2025?',
            'Which focus areas have the largest implementation gap in a given year?',
            'Which focus areas have the largest implementation gap (planned versus initiated) in a given year?',
            'Which focus areas have the largest implementation gap (planned versus initiated) in a given year, for a given district?',
            'Which focus areas have the largest implementation gap (planned versus initiated) in a given year, for a given block?',
            'Which focus areas have the largest implementation gap (planned versus initiated) in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-011': {
        "abstract_question": 'Which focus areas have the largest number of ongoing activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       SUM(v.is_ongoing) AS ongoing_activities,
       COUNT(*) AS planned_activities,
       SUM(v.total_expenditure) FILTER (WHERE v.is_ongoing = 1) AS expenditure_on_ongoing
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY ongoing_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Yes',
        "paraphrases": [
            'Which focus areas have the most ongoing work in 2024-2025?',
            'Which focus areas have the largest number of ongoing activities in a given year?',
            'Which focus areas have the largest number of ongoing activities in a given year, for a given district?',
            'Which focus areas have the largest number of ongoing activities in a given year, for a given block?',
            'Which focus areas have the largest number of ongoing activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-012': {
        "abstract_question": 'Which themes receive funds but show poor implementation in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(v.is_completed) AS completed_activities,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING SUM(v.total_expenditure) > 0
ORDER BY expenditure DESC, completion_rate_pct ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Poor implementation' is undefined in the source question; the query ranks by spend and shows the completion rate alongside. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes spend but do not complete in 2024-2025?',
            'Which themes consistently receive funds but show poor implementation in a given year?',
            'Which themes receive funds but show poor implementation in a given year?',
            'Which themes receive funds but show poor implementation in a given year, for a given district?',
            'Which themes receive funds but show poor implementation in a given year, for a given block?',
            'Which themes receive funds but show poor implementation in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-013': {
        "abstract_question": 'Which high-expenditure activities have not yet started in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.approved_cost_action_plan, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_started = 0
  AND COALESCE(v.approved_cost_action_plan, v.total_cost, 0) >= $amount_threshold
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY COALESCE(v.approved_cost_action_plan, v.total_cost) DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'amount_threshold', 'entity_type': 'amount_threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High-expenditure' is now the $amount_threshold parameter.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which costly activities have not started in 2024-2025?',
            'Which high-expenditure activities have not yet started in a given year?',
            'Which high-expenditure activities have not yet started in a given year, for a given district?',
            'Which high-expenditure activities have not yet started in a given year, for a given block?',
            'Which high-expenditure activities have not yet started in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-014': {
        "abstract_question": 'Which themes have the greatest mismatch between planning and expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_activities,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS pct_of_expenditure,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER ()
             - 100.0 * SUM(v.total_expenditure)
               / NULLIF(SUM(SUM(v.total_expenditure)) OVER (),0), 2) AS share_gap_pts
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY ABS(share_gap_pts) DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Mismatch is measured as the gap between a theme's share of activities and its share of spend.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes plan much and spend little in 2024-2025?',
            'Which themes have the greatest mismatch between planning and expenditure in a given year?',
            'Which themes have the greatest mismatch between planning and expenditure in a given year, for a given district?',
            'Which themes have the greatest mismatch between planning and expenditure in a given year, for a given block?',
            'Which themes have the greatest mismatch between planning and expenditure in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-015': {
        "abstract_question": 'Which GPDP themes consistently perform well in implementation across years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(DISTINCT v.fiscal_year) AS years_present,
       COUNT(*) AS total_activities,
       SUM(v.is_started)   AS started,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS avg_initiation_rate_pct
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY avg_initiation_rate_pct DESC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Consistently' is not defined in the source question; the query pools all years and reports the overall initiation rate per theme. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes consistently perform well in implementation?',
            'Which GPDP themes consistently perform well in implementation in a given year?',
            'Which GPDP themes consistently perform well in implementation across years, for a given district?',
            'Which GPDP themes consistently perform well in implementation across years, for a given block?',
            'Which GPDP themes consistently perform well in implementation across years, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-016': {
        "abstract_question": 'Which GPDP themes consistently underperform in implementation across years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(DISTINCT v.fiscal_year) AS years_present,
       COUNT(*) AS total_activities,
       SUM(v.is_started)   AS started,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS avg_initiation_rate_pct
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY avg_initiation_rate_pct ASC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Consistently' is not defined in the source question; the query pools all years and reports the overall initiation rate per theme. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes consistently underperform in implementation?',
            'Which GPDP themes consistently underperform in implementation in a given year?',
            'Which GPDP themes consistently underperform in implementation across years, for a given district?',
            'Which GPDP themes consistently underperform in implementation across years, for a given block?',
            'Which GPDP themes consistently underperform in implementation across years, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-017': {
        "abstract_question": 'Which types of activity remain incomplete across multiple years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_name,
       COUNT(DISTINCT v.fiscal_year) AS years_appearing,
       COUNT(*) AS occurrences,
       SUM(v.is_completed) AS completed,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(DISTINCT v.fiscal_year) > 1 AND SUM(v.is_completed) = 0
ORDER BY years_appearing DESC, occurrences DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Groups on the exact activity_name string. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'Which activity types stay incomplete year after year?',
            'Which type of activities remain incomplete across multiple years?',
            'Which types of activity remain incomplete across multiple years, for a given district?',
            'Which types of activity remain incomplete across multiple years, for a given block?',
            'Which types of activity remain incomplete across multiple years, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-018': {
        "abstract_question": 'Which activities are marked Work Ongoing despite expenditure reaching the approved cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.approved_cost_action_plan, v.total_expenditure,
       ROUND(100.0 * v.total_expenditure
             / NULLIF(v.approved_cost_action_plan,0), 2) AS pct_of_approved_spent,
       v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_ongoing = 1
  AND COALESCE(v.approved_cost_action_plan,0) > 0
  AND v.total_expenditure >= v.approved_cost_action_plan
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY pct_of_approved_spent DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which ongoing activities have already spent their approved cost in 2024-2025?',
            'Which activities are marked "Work Ongoing" despite actual expenditure equaling expected expenditure in a given year?',
            'Which activities are marked Work Ongoing despite expenditure reaching the approved cost in a given year?',
            'Which activities are marked Work Ongoing despite expenditure reaching the approved cost in a given year, for a given district?',
            'Which activities are marked Work Ongoing despite expenditure reaching the approved cost in a given year, for a given block?',
            'Which activities are marked Work Ongoing despite expenditure reaching the approved cost in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-019': {
        "abstract_question": 'Which themes should be prioritised for implementation support in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS planned_activities,
       SUM(v.is_started) AS started,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS initiation_rate_pct,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(*) >= $threshold
ORDER BY initiation_rate_pct ASC, approved_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Advisory question with no defined rule. Ranks by lowest initiation rate among groups with at least $threshold activities.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which themes need implementation support in 2024-2025?',
            'Which Gram Panchayat themes require immediate administrative intervention based on implementation performance in a given year?',
            'Which themes should be prioritised for implementation support in a given year?',
            'Which themes should be prioritised for implementation support in a given year, for a given district?',
            'Which themes should be prioritised for implementation support in a given year, for a given block?',
            'Which themes should be prioritised for implementation support in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-020': {
        "abstract_question": 'Which focus areas should be prioritised for implementation support in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS planned_activities,
       SUM(v.is_started) AS started,
       ROUND(100.0 * SUM(v.is_started) / NULLIF(COUNT(*),0), 2) AS initiation_rate_pct,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING COUNT(*) >= $threshold
ORDER BY initiation_rate_pct ASC, approved_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Advisory question with no defined rule. Ranks by lowest initiation rate among groups with at least $threshold activities.',
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which focus areas need implementation support in 2024-2025?',
            'Which focus areas should be prioritised for implementation support in a given year?',
            'Which focus areas should be prioritised for implementation support in a given year, for a given district?',
            'Which focus areas should be prioritised for implementation support in a given year, for a given block?',
            'Which focus areas should be prioritised for implementation support in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-021': {
        "abstract_question": 'Which activities should be carried forward to the next GPDP because they are incomplete in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.focus_area_name, v.status_label,
       v.approved_cost_action_plan, v.total_expenditure,
       COALESCE(v.approved_cost_action_plan,0) - v.total_expenditure AS unspent_amount
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_completed = 0
  AND v.is_abandoned = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY unspent_amount DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Should be carried forward' is a policy judgement; the query returns every non-completed, non-abandoned activity ordered by unspent amount.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which incomplete activities should carry forward from 2024-2025?',
            'Which activities should be carried forward to the next GPDP due to incomplete implementation in a given year?',
            'Which activities should be carried forward to the next GPDP because they are incomplete in a given year?',
            'Which activities should be carried forward to the next GPDP because they are incomplete in a given year, for a given district?',
            'Which activities should be carried forward to the next GPDP because they are incomplete in a given year, for a given block?',
            'Which activities should be carried forward to the next GPDP because they are incomplete in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'IMP-022': {
        "abstract_question": 'Which schemes have the highest number of delayed or incomplete activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COALESCE(v.scheme_name,'(not recorded)') AS scheme_name,
       COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.is_completed = 0) AS incomplete_activities,
       SUM(v.is_ongoing) AS ongoing,
       SUM(v.is_abandoned) AS abandoned,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_completed = 0)
             / NULLIF(COUNT(*),0), 2) AS pct_incomplete
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY incomplete_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "No planned end-date exists, so 'delayed' cannot be measured; only 'incomplete' is returned. scheme_name is NULL on 82% of rows.",
        "bracket": 'Implementation & Progress',
        "module": 'GPDP',
        "submodule": 'Implementation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which schemes carry the most incomplete work in 2024-2025?',
            'Which schemes have the highest number of delayed or incomplete activities in a given year?',
            'Which schemes have the highest number of delayed or incomplete activities in a given year, for a given district?',
            'Which schemes have the highest number of delayed or incomplete activities in a given year, for a given block?',
            'Which schemes have the highest number of delayed or incomplete activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'PHY-001': {
        "abstract_question": 'What physical-progress evidence has been recorded for activity {activity_code}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.status_label,
       v.evidence_uploads AS geotagged_uploads,
       (SELECT COUNT(DISTINCT p.file_upload_id) FROM v_progress p
         WHERE p.activity_code = v.activity_code) AS distinct_files,
       (SELECT ROUND(AVG(p.latitude), 6) FROM v_progress p
         WHERE p.activity_code = v.activity_code) AS avg_latitude,
       (SELECT ROUND(AVG(p.longitude), 6) FROM v_progress p
         WHERE p.activity_code = v.activity_code) AS avg_longitude,
       v.admin_approved_cost, v.total_expenditure
FROM v_activity v
WHERE v.activity_code = $activity_code
""",
        "param_slots": [
            {'name': 'activity_code', 'entity_type': 'activity_code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "physical_progress holds geotagged photo uploads, not a stage model - there are no stage names or stage dates, so the original 'current stage of each asset' cannot be answered. What is available is whether evidence was uploaded and where it was taken. 1,675 of 12,704 activities have at least one upload.",
        "bracket": 'Implementation & Progress',
        "module": 'Physical Progress',
        "submodule": 'Asset Stages',
        "question_type": 'Status Lookup',
        "answerable": 'Partial',
        "paraphrases": [
            'What progress evidence exists for a given activity code?',
            'What is the current stage of each asset under activity a given Activity Code?',
            'What physical-progress evidence has been recorded for activity a given activity?',
        ],
    },

    'PHY-003': {
        "abstract_question": 'How many assets in {gp_name} belong to completed activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) AS asset_rows,
       COUNT(*) FILTER (WHERE v.status_label = 'WORK COMPLETED') AS assets_under_completed_activities
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1,2
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": "There is no per-asset completion flag, so the parent activity's status is used instead. Progress is read from activity_status. Only 17 of 12,704 activities are marked WORK COMPLETED, so completion figures will look near-zero - that is what the data says, not a query fault.",
        "bracket": 'Implementation & Progress',
        "module": 'Physical Progress',
        "submodule": 'Asset Stages',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Andhrua assets sit under completed activities in 2024-2025?',
            'How many assets in a given GP Name are marked fully completed in a given Plan Year?',
            'How many assets in a given gram panchayat belong to completed activities in a given year?',
            'How many assets in a given district belong to completed activities in a given year?',
            'How many assets in a given block belong to completed activities in a given year?',
        ],
    },

    'PHY-004': {
        "abstract_question": 'How many activities in {block_name} have physical-progress evidence recorded in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.status_label,
       COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.has_progress_evidence = 1) AS with_evidence,
       SUM(v.evidence_uploads) AS total_uploads,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.has_progress_evidence = 1)
             / NULLIF(COUNT(*),0), 2) AS pct_with_evidence
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Rewritten from 'assets at each implementation stage' to 'activities with progress evidence', which is what physical_progress actually supports. Grouped by activity status as the nearest stage proxy.",
        "bracket": 'Implementation & Progress',
        "module": 'Physical Progress',
        "submodule": 'Asset Stages',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Bhubaneswar activities have progress evidence in 2024-2025?',
            'How many assets in a given Block are at each implementation stage in a given Plan Year?',
            'How many activities in a given block have physical-progress evidence recorded in a given year?',
            'How many activities in a given district have physical-progress evidence recorded in a given year?',
            'How many activities in a given gram panchayat have physical-progress evidence recorded in a given year?',
        ],
    },

    'AST-001': {
        "abstract_question": 'How many assets were created in {gp_name} during {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) AS asset_rows,
       COUNT(DISTINCT v.activity_code) AS asset_creating_activities,
       COUNT(*) FILTER (WHERE v.asset_category_label <> 'Uncategorised') AS categorised_assets
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1,2
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many assets were created in Andhrua in 2024-2025?',
            'How many assets were created in a given GP Name during a given Plan Year?',
            'How many assets were created in a given gram panchayat during a given year?',
            'How many assets were created in a given district during a given year?',
            'How many assets were created in a given block during a given year?',
        ],
    },

    'AST-002': {
        "abstract_question": 'What is the asset category-wise count of assets created in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_category_label,
       COUNT(*) AS asset_rows,
       COUNT(DISTINCT v.activity_code) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the category-wise asset count in Bhubaneswar in 2024-2025?',
            'What is the asset category-wise count of assets created in a given Block for a given Plan Year?',
            'What is the asset category-wise count of assets created in a given block for a given year?',
            'What is the asset category-wise count of assets created in a given district for a given year?',
            'What is the asset category-wise count of assets created in a given gram panchayat for a given year?',
        ],
    },

    'AST-003': {
        "abstract_question": 'How many {asset_sub_category} assets exist across {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_subcategory_label,
       COUNT(*) AS asset_rows,
       COUNT(DISTINCT v.gp_name) AS gps,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($asset_sub_category IS NULL OR v.asset_subcategory_label = $asset_sub_category)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'asset_sub_category', 'entity_type': 'asset_subcategory', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many assets of a given sub-category exist in Khordha in 2024-2025?',
            'How many a given Asset Sub Category assets exist across a given District as per a given Plan Year records?',
            'How many a given asset sub-category assets exist across a given district for a given year?',
            'How many a given asset sub-category assets exist across a given block for a given year?',
            'How many a given asset sub-category assets exist across a given gram panchayat for a given year?',
        ],
    },

    'AST-006': {
        "abstract_question": 'How many immovable-type assets were created in {block_name} during {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_type_label, COUNT(*) AS asset_rows,
       COUNT(DISTINCT v.activity_code) AS activities
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "asset_type decodes to movable / Immovable but is populated on only a small share of rows; 'permanent' maps to Immovable.",
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many immovable assets were created in Bhubaneswar in 2024-2025?',
            'How many permanent-type assets were created in a given Block during a given Plan Year?',
            'How many immovable-type assets were created in a given block during a given year?',
            'How many immovable-type assets were created in a given district during a given year?',
            'How many immovable-type assets were created in a given gram panchayat during a given year?',
        ],
    },

    'AST-007': {
        "abstract_question": 'Which asset category received the highest expenditure in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_category_label,
       COUNT(*) AS asset_rows,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which asset category absorbed the most spend in Khordha in 2024-2025?',
            'Which asset category received the highest expenditure in a given District for a given Plan Year?',
            'Which asset category received the highest expenditure in a given district for a given year?',
            'Which asset category received the highest expenditure in a given block for a given year?',
            'Which asset category received the highest expenditure in a given gram panchayat for a given year?',
        ],
    },

    'AST-008': {
        "abstract_question": 'How many assets were created under {theme} in {block_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme, COUNT(*) AS asset_rows,
       COUNT(DISTINCT v.activity_code) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND ($theme IS NULL OR v.theme = $theme)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY asset_rows DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'theme', 'entity_type': 'theme', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas. activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many assets fall under a given theme in Bhubaneswar in 2024-2025?',
            'How many assets were created under the a given Theme theme in a given Block for a given Plan Year?',
            'How many assets were created under a given LSDG theme in a given block for a given year?',
            'How many assets were created under a given LSDG theme in a given district for a given year?',
            'How many assets were created under a given LSDG theme in a given gram panchayat for a given year?',
        ],
    },

    'AST-009': {
        "abstract_question": 'Which GPs in {block_name} created no assets in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name
FROM gram_panchayat g
WHERE NOT EXISTS (
        SELECT 1 FROM v_asset v
        WHERE v.gp_name = g.gp_name
          AND v.fiscal_year = $date_range
          AND v.asset_category_label <> 'Uncategorised')
  AND ($block_name    IS NULL OR g.block_name = $block_name)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Created no assets' means no categorised asset row. Because asset_category is missing on two-thirds of rows, GPs may appear here from missing data alone.",
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs created no assets in 2024-2025?',
            'Which GPs in a given Block created no assets in a given Plan Year?',
            'Which GPs in a given block created no assets in a given year?',
            'Which GPs in a given district created no assets in a given year?',
        ],
    },

    'AST-012': {
        "abstract_question": 'How has the number of assets created per year in {block_name} changed?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.fiscal_year,
       COUNT(*) AS asset_rows,
       COUNT(*) FILTER (WHERE v.asset_category_label <> 'Uncategorised') AS categorised_assets,
       COUNT(DISTINCT v.activity_code) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_asset v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
ORDER BY 1
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'activity_asset is sparsely populated: asset_category has values on 4,286 of 12,704 rows and asset_subcategory on 4,286; asset_name, asset_unit_count and asset_unit_cost are 100% NULL. Uncategorised rows are reported separately rather than dropped.',
        "bracket": 'Assets',
        "module": 'Assets',
        "submodule": 'Asset Creation',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            'How has asset creation in Bhubaneswar changed year on year?',
            'How has the number of assets created per year in a given Block changed over a given Date Range?',
            'How has the number of assets created per year in a given block changed?',
            'How has the number of assets created per year in a given district changed?',
            'How has the number of assets created per year in a given gram panchayat changed?',
        ],
    },

    'SBM-GWM-001': {
        "abstract_question": 'How many Grey Water Management activities have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Grey Water Management activities' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'soak|grey ?water|gwm')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Grey Water Management activities have been planned in 2024-2025?',
            'How many activities fall under Grey Water Management (GWM) in a given year?',
            'How many Grey Water Management activities have been planned in a given year?',
            'How many Grey Water Management activities have been planned in a given year, for a given district?',
            'How many Grey Water Management activities have been planned in a given year, for a given block?',
            'How many Grey Water Management activities have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-002': {
        "abstract_question": 'What is the expenditure on Grey Water Management activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Grey Water Management activities' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'soak|grey ?water|gwm')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on Grey Water Management activities in 2024-2025?',
            'What is the total expenditure on Grey Water Management (GWM) activities in a given year?',
            'What is the expenditure on Grey Water Management activities in a given year?',
            'What is the expenditure on Grey Water Management activities in a given year, for a given district?',
            'What is the expenditure on Grey Water Management activities in a given year, for a given block?',
            'What is the expenditure on Grey Water Management activities in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-003': {
        "abstract_question": 'How many community soak pits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community soak pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(community|group|cluster)|(community|group|cluster).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community soak pits have been planned in 2024-2025?',
            'How many community soak pits for Grey Water Management (GWM) have been planned in a given year?',
            'How many community soak pits have been planned in a given year?',
            'How many community soak pits have been planned in a given year, for a given district?',
            'How many community soak pits have been planned in a given year, for a given block?',
            'How many community soak pits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-004': {
        "abstract_question": 'How many community soak pits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community soak pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(community|group|cluster)|(community|group|cluster).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community soak pits have been approved in 2024-2025?',
            'How many community soak pits for Grey Water Management (GWM) have been approved in a given year?',
            'How many community soak pits have been approved in a given year?',
            'How many community soak pits have been approved in a given year, for a given district?',
            'How many community soak pits have been approved in a given year, for a given block?',
            'How many community soak pits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-005': {
        "abstract_question": 'How many community soak pits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(community|group|cluster)|(community|group|cluster).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community soak pits are ongoing in 2024-2025?',
            'How many community soak pits for Grey Water Management (GWM) are ongoing in a given year?',
            'How many community soak pits are ongoing in a given year?',
            'How many community soak pits are ongoing in a given year, for a given district?',
            'How many community soak pits are ongoing in a given year, for a given block?',
            'How many community soak pits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-006': {
        "abstract_question": 'How many community soak pits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(community|group|cluster)|(community|group|cluster).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community soak pits have been completed in 2024-2025?',
            'How many community soak pits for Grey Water Management (GWM) have been completed in a given year?',
            'How many community soak pits have been completed in a given year?',
            'How many community soak pits have been completed in a given year, for a given district?',
            'How many community soak pits have been completed in a given year, for a given block?',
            'How many community soak pits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-007': {
        "abstract_question": 'What is the expenditure on community soak pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(community|group|cluster)|(community|group|cluster).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on community soak pits in 2024-2025?',
            'What is the expenditure on construction of community soak pits for Grey Water Management (GWM) in a given year?',
            'What is the expenditure on community soak pits in a given year?',
            'What is the expenditure on community soak pits in a given year, for a given district?',
            'What is the expenditure on community soak pits in a given year, for a given block?',
            'What is the expenditure on community soak pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-008': {
        "abstract_question": 'How many household soak pits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household soak pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(household|individual|hh)|(household|individual|hh).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household soak pits have been planned in 2024-2025?',
            'How many soak pits for individual households have been planned under Grey Water Management (GWM) in a given year?',
            'How many household soak pits have been planned in a given year?',
            'How many household soak pits have been planned in a given year, for a given district?',
            'How many household soak pits have been planned in a given year, for a given block?',
            'How many household soak pits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-009': {
        "abstract_question": 'How many household soak pits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household soak pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(household|individual|hh)|(household|individual|hh).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household soak pits have been approved in 2024-2025?',
            'How many soak pits for individual households have been approved under Grey Water Management (GWM) in a given year?',
            'How many household soak pits have been approved in a given year?',
            'How many household soak pits have been approved in a given year, for a given district?',
            'How many household soak pits have been approved in a given year, for a given block?',
            'How many household soak pits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-010': {
        "abstract_question": 'How many household soak pits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(household|individual|hh)|(household|individual|hh).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household soak pits are ongoing in 2024-2025?',
            'How many soak pits for individual households are ongoing under Grey Water Management (GWM) in a given year?',
            'How many household soak pits are ongoing in a given year?',
            'How many household soak pits are ongoing in a given year, for a given district?',
            'How many household soak pits are ongoing in a given year, for a given block?',
            'How many household soak pits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-011': {
        "abstract_question": 'How many household soak pits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(household|individual|hh)|(household|individual|hh).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household soak pits have been completed in 2024-2025?',
            'How many soak pits for individual households have been completed under Grey Water Management (GWM) in a given year?',
            'How many household soak pits have been completed in a given year?',
            'How many household soak pits have been completed in a given year, for a given district?',
            'How many household soak pits have been completed in a given year, for a given block?',
            'How many household soak pits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-GWM-012': {
        "abstract_question": 'What is the expenditure on household soak pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household soak pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(soak).*(household|individual|hh)|(household|individual|hh).*(soak)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Grey Water Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on household soak pits in 2024-2025?',
            'What is the expenditure on creation of soak pits for individual households under Grey Water Management (GWM) in a given year?',
            'What is the expenditure on household soak pits in a given year?',
            'What is the expenditure on household soak pits in a given year, for a given district?',
            'What is the expenditure on household soak pits in a given year, for a given block?',
            'What is the expenditure on household soak pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-001': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on community sanitary complexes in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community sanitary complexes' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, '(toilet|sanitary).*(complex|community)|community.*(toilet|complex)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on community sanitary complexes in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of Community a given subject Complexes in a given year?',
            'What is the Operation & Maintenance expenditure on community sanitary complexes in a given year?',
            'What is the Operation & Maintenance expenditure on community sanitary complexes in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on community sanitary complexes in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on community sanitary complexes in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-002': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on community compost pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on community compost pits in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of community compost pits in a given year?',
            'What is the Operation & Maintenance expenditure on community compost pits in a given year?',
            'What is the Operation & Maintenance expenditure on community compost pits in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on community compost pits in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on community compost pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-003': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on segregation sheds in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on segregation sheds in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of segregation sheds (community level) in a given year?',
            'What is the Operation & Maintenance expenditure on segregation sheds in a given year?',
            'What is the Operation & Maintenance expenditure on segregation sheds in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on segregation sheds in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on segregation sheds in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-004': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Plastic Waste Management Units' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, 'plastic waste|pwmu')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of Plastic Waste Management Units (PWMUs) in a given year?',
            'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in a given year?',
            'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on Plastic Waste Management Units in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-005': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on Gobardhan units in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on Gobardhan units in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of Gobardhan units (including forward linkages) in a given year?',
            'What is the Operation & Maintenance expenditure on Gobardhan units in a given year?',
            'What is the Operation & Maintenance expenditure on Gobardhan units in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on Gobardhan units in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on Gobardhan units in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-006': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community Grey Water Management systems and soak pits' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, 'soak|grey ?water|gwm')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of community Grey Water Management (GWM) systems / soak pits in a given year?',
            'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in a given year?',
            'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on community Grey Water Management systems and soak pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-007': {
        "abstract_question": 'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Faecal Sludge Management plants' AS item,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND regexp_matches(v.search_text, 'faecal|fsm|sludge')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'O&M is read as work_type Maintenance or Upgradation, combined with a keyword match on the activity text. SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in 2024-2025?',
            'What is the expenditure on Operation & Maintenance of the Faecal Sludge Management (FSM) plant in a given year?',
            'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in a given year?',
            'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in a given year, for a given district?',
            'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in a given year, for a given block?',
            'What is the Operation & Maintenance expenditure on Faecal Sludge Management plants in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-008': {
        "abstract_question": 'How many PPE kits and safety equipment purchases have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'PPE kits and safety equipment purchases' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ppe|safety equipment|glove|mask|protective')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many PPE kits and safety equipment purchases have been planned in 2024-2025?',
            'How many Personal Protective Equipment (PPE) kits / sets of safety equipment (gloves, masks) have been purchased for waste management in a given year?',
            'How many PPE kits and safety equipment purchases have been planned in a given year?',
            'How many PPE kits and safety equipment purchases have been planned in a given year, for a given district?',
            'How many PPE kits and safety equipment purchases have been planned in a given year, for a given block?',
            'How many PPE kits and safety equipment purchases have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-009': {
        "abstract_question": 'What is the expenditure on waste-management and safety equipment in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'waste-management and safety equipment' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ppe|safety equipment|glove|mask|protective|waste.*equipment|equipment.*waste')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on waste-management and safety equipment in 2024-2025?',
            'What is the expenditure on purchase of waste-management equipment, including safety equipment in a given year?',
            'What is the expenditure on waste-management and safety equipment in a given year?',
            'What is the expenditure on waste-management and safety equipment in a given year, for a given district?',
            'What is the expenditure on waste-management and safety equipment in a given year, for a given block?',
            'What is the expenditure on waste-management and safety equipment in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-OM-010': {
        "abstract_question": 'What is the total Operation & Maintenance expenditure in {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS maintenance_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS om_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.work_type_label IN ('Maintenance', 'Upgradation')
  AND ($focus_area IS NULL OR v.focus_area_name = $focus_area)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY om_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'focus_area', 'entity_type': 'focus_area', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "O&M is read as work_type Maintenance or Upgradation. Pass $focus_area = 'Sanitation' to restrict to SBM assets.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Operation & Maintenance',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            "What is Andhrua's total O&M expenditure in 2024-2025?",
            'What is the total Operation & Maintenance (O&M) expenditure on a given subject assets in the panchayat in a given year?',
            'What is the total Operation & Maintenance expenditure in a given gram panchayat in a given year?',
            'What is the total Operation & Maintenance expenditure in a given district in a given year?',
            'What is the total Operation & Maintenance expenditure in a given block in a given year?',
        ],
    },

    'SBM-SI-001': {
        "abstract_question": 'How many toilets in public institutions have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets in public institutions' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet).*(public|institution|community)|(public|institution|community).*(toilet)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets in public institutions have been planned in 2024-2025?',
            'How many toilets in public institutions have been planned in a given year?',
            'How many toilets in public institutions have been planned in a given year, for a given district?',
            'How many toilets in public institutions have been planned in a given year, for a given block?',
            'How many toilets in public institutions have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-002': {
        "abstract_question": 'How many toilets in public institutions have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets in public institutions' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet).*(public|institution|community)|(public|institution|community).*(toilet)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets in public institutions have been approved in 2024-2025?',
            'How many toilets in public institutions have been approved in a given year?',
            'How many toilets in public institutions have been approved in a given year, for a given district?',
            'How many toilets in public institutions have been approved in a given year, for a given block?',
            'How many toilets in public institutions have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-003': {
        "abstract_question": 'How many toilets in public institutions are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets in public institutions' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet).*(public|institution|community)|(public|institution|community).*(toilet)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets in public institutions are ongoing in 2024-2025?',
            'How many toilets in public institutions are ongoing in a given year?',
            'How many toilets in public institutions are ongoing in a given year, for a given district?',
            'How many toilets in public institutions are ongoing in a given year, for a given block?',
            'How many toilets in public institutions are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-004': {
        "abstract_question": 'How many toilets in public institutions have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets in public institutions' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet).*(public|institution|community)|(public|institution|community).*(toilet)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets in public institutions have been completed in 2024-2025?',
            'How many toilets in public institutions have been completed in a given year?',
            'How many toilets in public institutions have been completed in a given year, for a given district?',
            'How many toilets in public institutions have been completed in a given year, for a given block?',
            'How many toilets in public institutions have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-005': {
        "abstract_question": 'What is the expenditure on toilets in public institutions in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets in public institutions' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet).*(public|institution|community)|(public|institution|community).*(toilet)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on toilets in public institutions in 2024-2025?',
            'What is the expenditure on construction of toilets in public institutions in a given year?',
            'What is the expenditure on toilets in public institutions in a given year?',
            'What is the expenditure on toilets in public institutions in a given year, for a given district?',
            'What is the expenditure on toilets in public institutions in a given year, for a given block?',
            'What is the expenditure on toilets in public institutions in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-006': {
        "abstract_question": 'How many Individual Household Latrines (IHHLs) have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Individual Household Latrines (IHHLs)' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ihhl|individual household latrine')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Individual Household Latrines (IHHLs) have been planned in 2024-2025?',
            'How many Individual Household Latrines (IHHLs) for eligible households have been planned in a given year?',
            'How many Individual Household Latrines (IHHLs) have been planned in a given year?',
            'How many Individual Household Latrines (IHHLs) have been planned in a given year, for a given district?',
            'How many Individual Household Latrines (IHHLs) have been planned in a given year, for a given block?',
            'How many Individual Household Latrines (IHHLs) have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-007': {
        "abstract_question": 'How many Individual Household Latrines (IHHLs) have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Individual Household Latrines (IHHLs)' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ihhl|individual household latrine')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Individual Household Latrines (IHHLs) have been approved in 2024-2025?',
            'How many Individual Household Latrines (IHHLs) for eligible households have been approved in a given year?',
            'How many Individual Household Latrines (IHHLs) have been approved in a given year?',
            'How many Individual Household Latrines (IHHLs) have been approved in a given year, for a given district?',
            'How many Individual Household Latrines (IHHLs) have been approved in a given year, for a given block?',
            'How many Individual Household Latrines (IHHLs) have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-008': {
        "abstract_question": 'How many Individual Household Latrines (IHHLs) are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Individual Household Latrines (IHHLs)' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ihhl|individual household latrine')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Individual Household Latrines (IHHLs) are ongoing in 2024-2025?',
            'How many Individual Household Latrines (IHHLs) for eligible households are ongoing in a given year?',
            'How many Individual Household Latrines (IHHLs) are ongoing in a given year?',
            'How many Individual Household Latrines (IHHLs) are ongoing in a given year, for a given district?',
            'How many Individual Household Latrines (IHHLs) are ongoing in a given year, for a given block?',
            'How many Individual Household Latrines (IHHLs) are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-009': {
        "abstract_question": 'How many Individual Household Latrines (IHHLs) have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Individual Household Latrines (IHHLs)' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ihhl|individual household latrine')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Individual Household Latrines (IHHLs) have been completed in 2024-2025?',
            'How many Individual Household Latrines (IHHLs) for eligible households have been completed in a given year?',
            'How many Individual Household Latrines (IHHLs) have been completed in a given year?',
            'How many Individual Household Latrines (IHHLs) have been completed in a given year, for a given district?',
            'How many Individual Household Latrines (IHHLs) have been completed in a given year, for a given block?',
            'How many Individual Household Latrines (IHHLs) have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-010': {
        "abstract_question": 'What is the expenditure on Individual Household Latrines (IHHLs) in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Individual Household Latrines (IHHLs)' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'ihhl|individual household latrine')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on Individual Household Latrines (IHHLs) in 2024-2025?',
            'What is the expenditure on construction of Individual Household Latrines (IHHLs) in a given year?',
            'What is the expenditure on Individual Household Latrines (IHHLs) in a given year?',
            'What is the expenditure on Individual Household Latrines (IHHLs) in a given year, for a given district?',
            'What is the expenditure on Individual Household Latrines (IHHLs) in a given year, for a given block?',
            'What is the expenditure on Individual Household Latrines (IHHLs) in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-011': {
        "abstract_question": 'How many toilets and handwash units in AWCs and schools have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets and handwash units in AWCs and schools' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets and handwash units in AWCs and schools have been planned in 2024-2025?',
            'How many toilets / handwash units in Anganwadi Centres (AWCs) and schools have been planned in a given year?',
            'How many toilets and handwash units in AWCs and schools have been planned in a given year?',
            'How many toilets and handwash units in AWCs and schools have been planned in a given year, for a given district?',
            'How many toilets and handwash units in AWCs and schools have been planned in a given year, for a given block?',
            'How many toilets and handwash units in AWCs and schools have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-012': {
        "abstract_question": 'How many toilets and handwash units in AWCs and schools have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets and handwash units in AWCs and schools' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets and handwash units in AWCs and schools have been approved in 2024-2025?',
            'How many toilets / handwash units in Anganwadi Centres (AWCs) and schools have been approved in a given year?',
            'How many toilets and handwash units in AWCs and schools have been approved in a given year?',
            'How many toilets and handwash units in AWCs and schools have been approved in a given year, for a given district?',
            'How many toilets and handwash units in AWCs and schools have been approved in a given year, for a given block?',
            'How many toilets and handwash units in AWCs and schools have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-013': {
        "abstract_question": 'How many toilets and handwash units in AWCs and schools are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets and handwash units in AWCs and schools' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets and handwash units in AWCs and schools are ongoing in 2024-2025?',
            'How many toilets / handwash units in Anganwadi Centres (AWCs) and schools are ongoing in a given year?',
            'How many toilets and handwash units in AWCs and schools are ongoing in a given year?',
            'How many toilets and handwash units in AWCs and schools are ongoing in a given year, for a given district?',
            'How many toilets and handwash units in AWCs and schools are ongoing in a given year, for a given block?',
            'How many toilets and handwash units in AWCs and schools are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-014': {
        "abstract_question": 'How many toilets and handwash units in AWCs and schools have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets and handwash units in AWCs and schools' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many toilets and handwash units in AWCs and schools have been completed in 2024-2025?',
            'How many toilets / handwash units in Anganwadi Centres (AWCs) and schools have been completed in a given year?',
            'How many toilets and handwash units in AWCs and schools have been completed in a given year?',
            'How many toilets and handwash units in AWCs and schools have been completed in a given year, for a given district?',
            'How many toilets and handwash units in AWCs and schools have been completed in a given year, for a given block?',
            'How many toilets and handwash units in AWCs and schools have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-015': {
        "abstract_question": 'What is the expenditure on toilets and handwash units in AWCs and schools in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'toilets and handwash units in AWCs and schools' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(toilet|handwash).*(anganwadi|awc|school)|(anganwadi|awc|school).*(toilet|handwash)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on toilets and handwash units in AWCs and schools in 2024-2025?',
            'What is the expenditure on construction of toilets / handwash units in Anganwadi Centres (AWCs) and schools in a given year?',
            'What is the expenditure on toilets and handwash units in AWCs and schools in a given year?',
            'What is the expenditure on toilets and handwash units in AWCs and schools in a given year, for a given district?',
            'What is the expenditure on toilets and handwash units in AWCs and schools in a given year, for a given block?',
            'What is the expenditure on toilets and handwash units in AWCs and schools in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-016': {
        "abstract_question": 'How many single-pit to twin-pit toilet retrofits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'single-pit to twin-pit toilet retrofits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'retrofit.*(twin|single)|twin pit|single pit')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many single-pit to twin-pit toilet retrofits have been planned in 2024-2025?',
            'How many single-pit to twin-pit toilet retrofits have been planned in a given year?',
            'How many single-pit to twin-pit toilet retrofits have been planned in a given year, for a given district?',
            'How many single-pit to twin-pit toilet retrofits have been planned in a given year, for a given block?',
            'How many single-pit to twin-pit toilet retrofits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-017': {
        "abstract_question": 'How many single-pit to twin-pit toilet retrofits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'single-pit to twin-pit toilet retrofits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'retrofit.*(twin|single)|twin pit|single pit')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many single-pit to twin-pit toilet retrofits have been approved in 2024-2025?',
            'How many single-pit to twin-pit toilet retrofits have been approved in a given year?',
            'How many single-pit to twin-pit toilet retrofits have been approved in a given year, for a given district?',
            'How many single-pit to twin-pit toilet retrofits have been approved in a given year, for a given block?',
            'How many single-pit to twin-pit toilet retrofits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-018': {
        "abstract_question": 'How many single-pit to twin-pit toilet retrofits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'single-pit to twin-pit toilet retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'retrofit.*(twin|single)|twin pit|single pit')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many single-pit to twin-pit toilet retrofits are ongoing in 2024-2025?',
            'How many single-pit to twin-pit toilet retrofits are ongoing in a given year?',
            'How many single-pit to twin-pit toilet retrofits are ongoing in a given year, for a given district?',
            'How many single-pit to twin-pit toilet retrofits are ongoing in a given year, for a given block?',
            'How many single-pit to twin-pit toilet retrofits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-019': {
        "abstract_question": 'How many single-pit to twin-pit toilet retrofits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'single-pit to twin-pit toilet retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'retrofit.*(twin|single)|twin pit|single pit')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many single-pit to twin-pit toilet retrofits have been completed in 2024-2025?',
            'How many single-pit to twin-pit toilet retrofits have been completed in a given year?',
            'How many single-pit to twin-pit toilet retrofits have been completed in a given year, for a given district?',
            'How many single-pit to twin-pit toilet retrofits have been completed in a given year, for a given block?',
            'How many single-pit to twin-pit toilet retrofits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-020': {
        "abstract_question": 'What is the expenditure on single-pit to twin-pit toilet retrofits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'single-pit to twin-pit toilet retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'retrofit.*(twin|single)|twin pit|single pit')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on single-pit to twin-pit toilet retrofits in 2024-2025?',
            'What is the expenditure on retrofitting single-pit toilets to twin-pit in a given year?',
            'What is the expenditure on single-pit to twin-pit toilet retrofits in a given year?',
            'What is the expenditure on single-pit to twin-pit toilet retrofits in a given year, for a given district?',
            'What is the expenditure on single-pit to twin-pit toilet retrofits in a given year, for a given block?',
            'What is the expenditure on single-pit to twin-pit toilet retrofits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-021': {
        "abstract_question": 'How many septic-tank-with-soak-pit retrofits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'septic-tank-with-soak-pit retrofits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'septic')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many septic-tank-with-soak-pit retrofits have been planned in 2024-2025?',
            'How many septic-tank-with-soak-pit retrofits have been planned in a given year?',
            'How many septic-tank-with-soak-pit retrofits have been planned in a given year, for a given district?',
            'How many septic-tank-with-soak-pit retrofits have been planned in a given year, for a given block?',
            'How many septic-tank-with-soak-pit retrofits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-022': {
        "abstract_question": 'How many septic-tank-with-soak-pit retrofits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'septic-tank-with-soak-pit retrofits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'septic')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many septic-tank-with-soak-pit retrofits have been approved in 2024-2025?',
            'How many septic-tank-with-soak-pit retrofits have been approved in a given year?',
            'How many septic-tank-with-soak-pit retrofits have been approved in a given year, for a given district?',
            'How many septic-tank-with-soak-pit retrofits have been approved in a given year, for a given block?',
            'How many septic-tank-with-soak-pit retrofits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-023': {
        "abstract_question": 'How many septic-tank-with-soak-pit retrofits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'septic-tank-with-soak-pit retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'septic')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many septic-tank-with-soak-pit retrofits are ongoing in 2024-2025?',
            'How many septic-tank-with-soak-pit retrofits are ongoing in a given year?',
            'How many septic-tank-with-soak-pit retrofits are ongoing in a given year, for a given district?',
            'How many septic-tank-with-soak-pit retrofits are ongoing in a given year, for a given block?',
            'How many septic-tank-with-soak-pit retrofits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-024': {
        "abstract_question": 'How many septic-tank-with-soak-pit retrofits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'septic-tank-with-soak-pit retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'septic')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many septic-tank-with-soak-pit retrofits have been completed in 2024-2025?',
            'How many septic-tank-with-soak-pit retrofits have been completed in a given year?',
            'How many septic-tank-with-soak-pit retrofits have been completed in a given year, for a given district?',
            'How many septic-tank-with-soak-pit retrofits have been completed in a given year, for a given block?',
            'How many septic-tank-with-soak-pit retrofits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SI-025': {
        "abstract_question": 'What is the expenditure on septic-tank-with-soak-pit retrofits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'septic-tank-with-soak-pit retrofits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'septic')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Sanitation Infrastructure',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on septic-tank-with-soak-pit retrofits in 2024-2025?',
            'What is the expenditure on retrofitting septic-tank toilets with soak pits in a given year?',
            'What is the expenditure on septic-tank-with-soak-pit retrofits in a given year?',
            'What is the expenditure on septic-tank-with-soak-pit retrofits in a given year, for a given district?',
            'What is the expenditure on septic-tank-with-soak-pit retrofits in a given year, for a given block?',
            'What is the expenditure on septic-tank-with-soak-pit retrofits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-001': {
        "abstract_question": 'How many Solid Waste Management activities have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Solid Waste Management activities' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'solid waste|waste management|compost|segregat|gobardhan|plastic waste')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Solid Waste Management activities have been planned in 2024-2025?',
            'How many activities fall under Solid Waste Management (SWM) in a given year?',
            'How many Solid Waste Management activities have been planned in a given year?',
            'How many Solid Waste Management activities have been planned in a given year, for a given district?',
            'How many Solid Waste Management activities have been planned in a given year, for a given block?',
            'How many Solid Waste Management activities have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-002': {
        "abstract_question": 'How many community compost pits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community compost pits have been planned in 2024-2025?',
            'How many community compost pits have been planned in a given year?',
            'How many community compost pits have been planned in a given year, for a given district?',
            'How many community compost pits have been planned in a given year, for a given block?',
            'How many community compost pits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-003': {
        "abstract_question": 'How many community compost pits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community compost pits have been approved in 2024-2025?',
            'How many community compost pits have been approved in a given year?',
            'How many community compost pits have been approved in a given year, for a given district?',
            'How many community compost pits have been approved in a given year, for a given block?',
            'How many community compost pits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-004': {
        "abstract_question": 'How many community compost pits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community compost pits are ongoing in 2024-2025?',
            'How many community compost pits are ongoing in a given year?',
            'How many community compost pits are ongoing in a given year, for a given district?',
            'How many community compost pits are ongoing in a given year, for a given block?',
            'How many community compost pits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-005': {
        "abstract_question": 'How many community compost pits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community compost pits have been completed in 2024-2025?',
            'How many community compost pits have been completed in a given year?',
            'How many community compost pits have been completed in a given year, for a given district?',
            'How many community compost pits have been completed in a given year, for a given block?',
            'How many community compost pits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-006': {
        "abstract_question": 'What is the expenditure on community compost pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(community|group|cluster)|(community|group|cluster).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on community compost pits in 2024-2025?',
            'What is the expenditure on construction of community compost pits in a given year?',
            'What is the expenditure on community compost pits in a given year?',
            'What is the expenditure on community compost pits in a given year, for a given district?',
            'What is the expenditure on community compost pits in a given year, for a given block?',
            'What is the expenditure on community compost pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-007': {
        "abstract_question": 'How many household compost pits have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household compost pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(household|individual|hh)|(household|individual|hh).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household compost pits have been planned in 2024-2025?',
            'How many household compost pits have been planned in a given year?',
            'How many household compost pits have been planned in a given year, for a given district?',
            'How many household compost pits have been planned in a given year, for a given block?',
            'How many household compost pits have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-008': {
        "abstract_question": 'How many household compost pits have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household compost pits' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(household|individual|hh)|(household|individual|hh).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household compost pits have been approved in 2024-2025?',
            'How many household compost pits have been approved in a given year?',
            'How many household compost pits have been approved in a given year, for a given district?',
            'How many household compost pits have been approved in a given year, for a given block?',
            'How many household compost pits have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-009': {
        "abstract_question": 'How many household compost pits are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(household|individual|hh)|(household|individual|hh).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household compost pits are ongoing in 2024-2025?',
            'How many household compost pits are ongoing in a given year?',
            'How many household compost pits are ongoing in a given year, for a given district?',
            'How many household compost pits are ongoing in a given year, for a given block?',
            'How many household compost pits are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-010': {
        "abstract_question": 'How many household compost pits have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(household|individual|hh)|(household|individual|hh).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household compost pits have been completed in 2024-2025?',
            'How many household compost pits have been completed in a given year?',
            'How many household compost pits have been completed in a given year, for a given district?',
            'How many household compost pits have been completed in a given year, for a given block?',
            'How many household compost pits have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-011': {
        "abstract_question": 'What is the expenditure on household compost pits in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household compost pits' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(compost).*(household|individual|hh)|(household|individual|hh).*(compost)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on household compost pits in 2024-2025?',
            'What is the expenditure on creation of household compost pits in a given year?',
            'What is the expenditure on household compost pits in a given year?',
            'What is the expenditure on household compost pits in a given year, for a given district?',
            'What is the expenditure on household compost pits in a given year, for a given block?',
            'What is the expenditure on household compost pits in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-012': {
        "abstract_question": 'How many segregation sheds have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation sheds have been planned in 2024-2025?',
            'How many segregation sheds have been planned in a given year?',
            'How many segregation sheds have been planned in a given year, for a given district?',
            'How many segregation sheds have been planned in a given year, for a given block?',
            'How many segregation sheds have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-013': {
        "abstract_question": 'How many segregation sheds have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation sheds have been approved in 2024-2025?',
            'How many segregation sheds have been approved in a given year?',
            'How many segregation sheds have been approved in a given year, for a given district?',
            'How many segregation sheds have been approved in a given year, for a given block?',
            'How many segregation sheds have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-014': {
        "abstract_question": 'How many segregation sheds are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation sheds are ongoing in 2024-2025?',
            'How many segregation sheds are ongoing in a given year?',
            'How many segregation sheds are ongoing in a given year, for a given district?',
            'How many segregation sheds are ongoing in a given year, for a given block?',
            'How many segregation sheds are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-015': {
        "abstract_question": 'How many segregation sheds have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation sheds have been completed in 2024-2025?',
            'How many segregation sheds have been completed in a given year?',
            'How many segregation sheds have been completed in a given year, for a given district?',
            'How many segregation sheds have been completed in a given year, for a given block?',
            'How many segregation sheds have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-016': {
        "abstract_question": 'What is the expenditure on segregation sheds in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation sheds' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'segregation shed|sorting shed|waste.*shed')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on segregation sheds in 2024-2025?',
            'What is the expenditure on construction of segregation sheds in a given year?',
            'What is the expenditure on segregation sheds in a given year?',
            'What is the expenditure on segregation sheds in a given year, for a given district?',
            'What is the expenditure on segregation sheds in a given year, for a given block?',
            'What is the expenditure on segregation sheds in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-017': {
        "abstract_question": 'How many segregation bins have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation bins' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'bin|dustbin|dust bin')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation bins have been planned in 2024-2025?',
            'How many segregation bins (total) have been planned in a given year?',
            'How many segregation bins have been planned in a given year?',
            'How many segregation bins have been planned in a given year, for a given district?',
            'How many segregation bins have been planned in a given year, for a given block?',
            'How many segregation bins have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-018': {
        "abstract_question": 'How many segregation bins have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation bins' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'bin|dustbin|dust bin')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation bins have been approved in 2024-2025?',
            'How many segregation bins (total) have been approved in a given year?',
            'How many segregation bins have been approved in a given year?',
            'How many segregation bins have been approved in a given year, for a given district?',
            'How many segregation bins have been approved in a given year, for a given block?',
            'How many segregation bins have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-019': {
        "abstract_question": 'How many segregation bins are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation bins' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'bin|dustbin|dust bin')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation bins are ongoing in 2024-2025?',
            'How many segregation bins (total) are ongoing in a given year?',
            'How many segregation bins are ongoing in a given year?',
            'How many segregation bins are ongoing in a given year, for a given district?',
            'How many segregation bins are ongoing in a given year, for a given block?',
            'How many segregation bins are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-020': {
        "abstract_question": 'How many segregation bins have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation bins' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'bin|dustbin|dust bin')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many segregation bins have been completed in 2024-2025?',
            'How many segregation bins (total) have been delivered in a given year?',
            'How many segregation bins have been completed in a given year?',
            'How many segregation bins have been completed in a given year, for a given district?',
            'How many segregation bins have been completed in a given year, for a given block?',
            'How many segregation bins have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-021': {
        "abstract_question": 'How many household segregation bins have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'household segregation bins' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(bin|dustbin).*(household|individual|hh)|(household|individual|hh).*(bin|dustbin)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many household segregation bins have been planned in 2024-2025?',
            'How many segregation bins have been purchased for households in a given year?',
            'How many household segregation bins have been planned in a given year?',
            'How many household segregation bins have been planned in a given year, for a given district?',
            'How many household segregation bins have been planned in a given year, for a given block?',
            'How many household segregation bins have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-022': {
        "abstract_question": 'How many community segregation bins have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'community segregation bins' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, '(bin|dustbin).*(community|group|cluster|public)|(community|group|cluster|public).*(bin|dustbin)')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many community segregation bins have been planned in 2024-2025?',
            'How many segregation bins have been purchased at community level in a given year?',
            'How many community segregation bins have been planned in a given year?',
            'How many community segregation bins have been planned in a given year, for a given district?',
            'How many community segregation bins have been planned in a given year, for a given block?',
            'How many community segregation bins have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-023': {
        "abstract_question": 'What is the expenditure on segregation bins in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'segregation bins' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'bin|dustbin|dust bin')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on segregation bins in 2024-2025?',
            'What is the expenditure on purchase of segregation bins in a given year?',
            'What is the expenditure on segregation bins in a given year?',
            'What is the expenditure on segregation bins in a given year, for a given district?',
            'What is the expenditure on segregation bins in a given year, for a given block?',
            'What is the expenditure on segregation bins in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-024': {
        "abstract_question": 'How many Gobardhan units have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gobardhan units have been planned in 2024-2025?',
            'How many Gobardhan units (community / cluster level) have been planned in a given year?',
            'How many Gobardhan units have been planned in a given year?',
            'How many Gobardhan units have been planned in a given year, for a given district?',
            'How many Gobardhan units have been planned in a given year, for a given block?',
            'How many Gobardhan units have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-025': {
        "abstract_question": 'How many Gobardhan units have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gobardhan units have been approved in 2024-2025?',
            'How many Gobardhan units (community / cluster level) have been approved in a given year?',
            'How many Gobardhan units have been approved in a given year?',
            'How many Gobardhan units have been approved in a given year, for a given district?',
            'How many Gobardhan units have been approved in a given year, for a given block?',
            'How many Gobardhan units have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-026': {
        "abstract_question": 'How many Gobardhan units are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gobardhan units are ongoing in 2024-2025?',
            'How many Gobardhan units (community / cluster level) are ongoing in a given year?',
            'How many Gobardhan units are ongoing in a given year?',
            'How many Gobardhan units are ongoing in a given year, for a given district?',
            'How many Gobardhan units are ongoing in a given year, for a given block?',
            'How many Gobardhan units are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-027': {
        "abstract_question": 'How many Gobardhan units have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many Gobardhan units have been completed in 2024-2025?',
            'How many Gobardhan units (community / cluster level) have been completed in a given year?',
            'How many Gobardhan units have been completed in a given year?',
            'How many Gobardhan units have been completed in a given year, for a given district?',
            'How many Gobardhan units have been completed in a given year, for a given block?',
            'How many Gobardhan units have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-028': {
        "abstract_question": 'What is the expenditure on Gobardhan units in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'Gobardhan units' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'gobardhan|bio.?gas')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on Gobardhan units in 2024-2025?',
            'What is the expenditure on construction of Gobardhan units at community / cluster level in a given year?',
            'What is the expenditure on Gobardhan units in a given year?',
            'What is the expenditure on Gobardhan units in a given year, for a given district?',
            'What is the expenditure on Gobardhan units in a given year, for a given block?',
            'What is the expenditure on Gobardhan units in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-029': {
        "abstract_question": 'How many door-to-door waste-collection vehicles have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'door-to-door waste-collection vehicles' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many door-to-door waste-collection vehicles have been planned in 2024-2025?',
            'How many door-to-door waste-collection vehicles (tricycle / battery-operated, including for Gobardhan units) have been planned in a given year?',
            'How many door-to-door waste-collection vehicles have been planned in a given year?',
            'How many door-to-door waste-collection vehicles have been planned in a given year, for a given district?',
            'How many door-to-door waste-collection vehicles have been planned in a given year, for a given block?',
            'How many door-to-door waste-collection vehicles have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-030': {
        "abstract_question": 'How many door-to-door waste-collection vehicles have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'door-to-door waste-collection vehicles' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many door-to-door waste-collection vehicles have been approved in 2024-2025?',
            'How many such vehicles have been approved in a given year?',
            'How many door-to-door waste-collection vehicles have been approved in a given year?',
            'How many door-to-door waste-collection vehicles have been approved in a given year, for a given district?',
            'How many door-to-door waste-collection vehicles have been approved in a given year, for a given block?',
            'How many door-to-door waste-collection vehicles have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-031': {
        "abstract_question": 'How many door-to-door waste-collection vehicles are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'door-to-door waste-collection vehicles' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many door-to-door waste-collection vehicles are ongoing in 2024-2025?',
            'How many such vehicles are ongoing (in procurement) in a given year?',
            'How many door-to-door waste-collection vehicles are ongoing in a given year?',
            'How many door-to-door waste-collection vehicles are ongoing in a given year, for a given district?',
            'How many door-to-door waste-collection vehicles are ongoing in a given year, for a given block?',
            'How many door-to-door waste-collection vehicles are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-032': {
        "abstract_question": 'How many door-to-door waste-collection vehicles have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'door-to-door waste-collection vehicles' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many door-to-door waste-collection vehicles have been completed in 2024-2025?',
            'How many such vehicles have been procured in a given year?',
            'How many door-to-door waste-collection vehicles have been completed in a given year?',
            'How many door-to-door waste-collection vehicles have been completed in a given year, for a given district?',
            'How many door-to-door waste-collection vehicles have been completed in a given year, for a given block?',
            'How many door-to-door waste-collection vehicles have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-034': {
        "abstract_question": 'What is the expenditure on door-to-door waste-collection vehicles in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'door-to-door waste-collection vehicles' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'tricycle|vehicle|rickshaw|e-?cart|pushcart|collection cart')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on door-to-door waste-collection vehicles in 2024-2025?',
            'What is the expenditure on purchase and repair of door-to-door waste-collection vehicles in a given year?',
            'What is the expenditure on door-to-door waste-collection vehicles in a given year?',
            'What is the expenditure on door-to-door waste-collection vehicles in a given year, for a given district?',
            'What is the expenditure on door-to-door waste-collection vehicles in a given year, for a given block?',
            'What is the expenditure on door-to-door waste-collection vehicles in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-035': {
        "abstract_question": 'How many weighing machines have been planned in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'weighing machines' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) AS planned_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'weighing')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many weighing machines have been planned in 2024-2025?',
            'How many weighing machines for Solid Waste Management (SWM) a given subject have been planned in a given year?',
            'How many weighing machines have been planned in a given year?',
            'How many weighing machines have been planned in a given year, for a given district?',
            'How many weighing machines have been planned in a given year, for a given block?',
            'How many weighing machines have been planned in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-036': {
        "abstract_question": 'How many weighing machines have been approved in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'weighing machines' AS item,
       COUNT(*) AS matching_activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 1) AS approved_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'weighing')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many weighing machines have been approved in 2024-2025?',
            'How many weighing machines have been approved in a given year?',
            'How many weighing machines have been approved in a given year, for a given district?',
            'How many weighing machines have been approved in a given year, for a given block?',
            'How many weighing machines have been approved in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-037': {
        "abstract_question": 'How many weighing machines are ongoing in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'weighing machines' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_ongoing) AS ongoing_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'weighing')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many weighing machines are ongoing in 2024-2025?',
            'How many weighing machines are ongoing (in procurement) in a given year?',
            'How many weighing machines are ongoing in a given year?',
            'How many weighing machines are ongoing in a given year, for a given district?',
            'How many weighing machines are ongoing in a given year, for a given block?',
            'How many weighing machines are ongoing in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-038': {
        "abstract_question": 'How many weighing machines have been completed in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'weighing machines' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.is_completed) AS completed_activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'weighing')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones. Only 17 activities database-wide are marked WORK COMPLETED, so 'completed' counts will be near zero. 'Approved' uses admin_approved_cost > 0.",
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Count',
        "answerable": 'Partial',
        "paraphrases": [
            'How many weighing machines have been completed in 2024-2025?',
            'How many weighing machines have been procured in a given year?',
            'How many weighing machines have been completed in a given year?',
            'How many weighing machines have been completed in a given year, for a given district?',
            'How many weighing machines have been completed in a given year, for a given block?',
            'How many weighing machines have been completed in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'SBM-SWM-039': {
        "abstract_question": 'What is the expenditure on weighing machines in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT 'weighing machines' AS item,
       COUNT(*) AS matching_activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(v.total_expenditure)      AS total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND regexp_matches(v.search_text, 'weighing')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'SBM activity types are not coded anywhere in the database - asset_subcategory is missing on two-thirds of asset rows and asset_name is 100% NULL. These queries therefore identify the activity by matching activity_name and activity_desc against the regular expression shown in the SQL. Review and tune the pattern before relying on the number: it can both miss differently-worded activities and pick up unrelated ones.',
        "bracket": 'Sanitation (SBM)',
        "module": 'SBM',
        "submodule": 'Solid Waste Management',
        "question_type": 'Aggregation',
        "answerable": 'Partial',
        "paraphrases": [
            'What is the expenditure on weighing machines in 2024-2025?',
            'What is the expenditure on purchase of weighing machines for Solid Waste Management (SWM) a given subject in a given year?',
            'What is the expenditure on weighing machines in a given year?',
            'What is the expenditure on weighing machines in a given year, for a given district?',
            'What is the expenditure on weighing machines in a given year, for a given block?',
            'What is the expenditure on weighing machines in a given year, for a given gram panchayat (GP)?',
        ],
    },

    'TRD-010': {
        "abstract_question": 'Compare planned expenditure, actual expenditure and completion rate between {gp_name} and {gp_name_2} for {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.gp_lgd_code IN ($gp_name, $gp_name_2)
GROUP BY 1,2,3
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'gp_name', 'entity_type': 'gp', 'bind': 'code'},
            {'name': 'gp_name_2', 'entity_type': 'gp_2', 'bind': 'code'},
        ],
        "grouped_geo": [
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Both $gp_name and $gp_name_2 must be supplied (no NULL skip here).',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Entity Comparison',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'Compare Andhrua and Balianta on plan, spend and completion in 2024-2025.',
            'Compare planned expenditure, actual expenditure, and completion rate between a given GP Name and a given GP Name 2 for a given Financial Year.',
            'Compare planned expenditure, actual expenditure and completion rate between a given gram panchayat and a second gram panchayat for a given year.',
        ],
    },

    'TRD-011': {
        "abstract_question": 'Compare activity counts, expenditure and completion rates between {block_name} and {block_name_2} for {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(DISTINCT v.gp_lgd_code) AS gps,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS actual_expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.block_name IN ($block_name, $block_name_2)
GROUP BY 1,2
ORDER BY actual_expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block'},
            {'name': 'block_name_2', 'entity_type': 'block_2'},
        ],
        "grouped_geo": [
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Both block parameters must be supplied.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Entity Comparison',
        "question_type": 'Comparison',
        "answerable": 'Yes',
        "paraphrases": [
            'Compare Bhubaneswar and Barpali in 2024-2025.',
            'Compare activity counts, expenditure, and completion rates between a given Block and a given Block 2 for a given Plan Year.',
            'Compare activity counts, expenditure and completion rates between a given block and a second block for a given year.',
        ],
    },

    'TRD-012': {
        "abstract_question": 'How does {district_name} compare with the state average on expenditure per GP and completion rate for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH per_district AS (
  SELECT v.district_name,
         COUNT(DISTINCT v.gp_lgd_code) AS gps,
         COUNT(*) AS activities,
         SUM(v.total_expenditure) AS expenditure,
         SUM(v.is_completed) AS completed
  FROM v_activity v
  WHERE v.fiscal_year = $date_range
  GROUP BY 1)
SELECT district_name,
       gps, activities,
       expenditure,
       ROUND(expenditure / NULLIF(gps,0), 2) AS expenditure_per_gp,
       ROUND(100.0 * completed / NULLIF(activities,0), 2) AS completion_rate_pct,
       ROUND(AVG(expenditure / NULLIF(gps,0)) OVER (), 2) AS state_avg_expenditure_per_gp,
       ROUND(100.0 * SUM(completed) OVER () / NULLIF(SUM(activities) OVER (),0), 2) AS state_completion_rate_pct
FROM per_district
WHERE $district_name IS NULL OR district_name = $district_name OR TRUE
ORDER BY expenditure_per_gp DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Every district is returned alongside the state benchmark so the chosen district can be read in context. 'State' means the 9 districts loaded.",
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Entity Comparison',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'How does Khordha compare with the state average in 2024-2025?',
            'How does a given District compare with the state average on expenditure per GP and completion rate for a given Plan Year?',
            'How does a given district compare with the state average on expenditure per GP and completion rate for a given year?',
        ],
    },

    'TRD-007': {
        "abstract_question": 'What are the approved cost, expenditure and status counts theme-wise for {gp_name} in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(v.is_started)   AS started,
       SUM(v.is_ongoing)   AS ongoing,
       SUM(v.is_completed) AS completed,
       SUM(v.is_abandoned) AS abandoned
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Physical vs Financial',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            "What is Andhrua's theme-wise physical-financial picture in 2024-2025?",
            'What are the approved cost, expenditure, and activity status counts theme-wise for a given GP Name in a given Financial Year?',
            'What are the approved cost, expenditure and status counts theme-wise for a given gram panchayat in a given year?',
            'What are the approved cost, expenditure and status counts theme-wise for a given district in a given year?',
            'What are the approved cost, expenditure and status counts theme-wise for a given block in a given year?',
        ],
    },

    'TRD-008': {
        "abstract_question": 'What are the approved cost and expenditure sector-wise in {district_name} for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name AS sector,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Sector' is read as focus area, the closest sectoral classification in the data.",
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Physical vs Financial',
        "question_type": 'Comparison',
        "answerable": 'Yes',
        "paraphrases": [
            "What is Khordha's focus-area-wise cost and spend in 2024-2025?",
            'What are the approved cost and expenditure sector-wise in a given District for a given Financial Year?',
            'What are the approved cost and expenditure sector-wise in a given district for a given year?',
            'What are the approved cost and expenditure sector-wise in a given block for a given year?',
            'What are the approved cost and expenditure sector-wise in a given gram panchayat for a given year?',
        ],
    },

    'TRD-009': {
        "abstract_question": 'Which themes in {block_name} show high expenditure but low activity completion in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING SUM(v.total_expenditure) > 0
ORDER BY expenditure DESC, completion_rate_pct ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are undefined; ordered by spend with completion rate shown beside it.",
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Physical vs Financial',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar themes spend a lot but complete little in 2024-2025?',
            'Which themes in a given Block show high expenditure but low activity completion in a given Financial Year?',
            'Which themes in a given block show high expenditure but low activity completion in a given year?',
            'Which themes in a given district show high expenditure but low activity completion in a given year?',
            'Which themes in a given gram panchayat show high expenditure but low activity completion in a given year?',
        ],
    },

    'TRD-001': {
        "abstract_question": 'Compare the activities planned and started theme-wise between {date_range_2} and {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS planned_year1,
       COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)   AS planned_year2,
       SUM(v.is_started) FILTER (WHERE v.fiscal_year = $date_range_2) AS started_year1,
       SUM(v.is_started) FILTER (WHERE v.fiscal_year = $date_range)   AS started_year2
FROM v_activity v
WHERE v.fiscal_year IN ($date_range, $date_range_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY planned_year2 DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'date_range_2', 'entity_type': 'fiscal_year_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping covers 17 of 30 focus areas.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'Compare theme-wise planned and started activities between 2023-2024 and 2024-2025.',
            'Compare the number of activities planned and started theme-wise between a given Plan Year and a given Plan Year 2.',
            'Compare the activities planned and started theme-wise between a second year and a given year.',
            'Compare the activities planned and started theme-wise between a second year and a given year, for a given district?',
            'Compare the activities planned and started theme-wise between a second year and a given year, for a given block?',
            'Compare the activities planned and started theme-wise between a second year and a given year, for a given gram panchayat (GP)?',
        ],
    },

    'TRD-002': {
        "abstract_question": 'Compare the approved cost and expenditure theme-wise between {date_range_2} and {date_range}.',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.theme,
       SUM(COALESCE(v.approved_cost_action_plan,0)) FILTER (WHERE v.fiscal_year = $date_range_2) AS approved_cost_year1,
       SUM(COALESCE(v.approved_cost_action_plan,0)) FILTER (WHERE v.fiscal_year = $date_range)   AS approved_cost_year2,
       SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range_2) AS expenditure_year1,
       SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range)   AS expenditure_year2
FROM v_activity v
WHERE v.fiscal_year IN ($date_range, $date_range_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY expenditure_year2 DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'date_range_2', 'entity_type': 'fiscal_year_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Theme mapping is partial.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Comparison',
        "answerable": 'Partial',
        "paraphrases": [
            'Compare theme-wise cost and spend between 2023-2024 and 2024-2025.',
            'Compare the approved cost and expenditure theme-wise between a given Plan Year and a given Plan Year 2.',
            'Compare the approved cost and expenditure theme-wise between a second year and a given year.',
            'Compare the approved cost and expenditure theme-wise between a second year and a given year, for a given district?',
            'Compare the approved cost and expenditure theme-wise between a second year and a given year, for a given block?',
            'Compare the approved cost and expenditure theme-wise between a second year and a given year, for a given gram panchayat (GP)?',
        ],
    },

    'TRD-003': {
        "abstract_question": 'What is the year-wise expenditure of {gp_name} against the plan of each year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.fiscal_year,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY 1 DESC
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Expenditure is recorded against the year of the plan it belongs to; there is no separate cash-year column, so cross-year carry-over cannot be traced.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            "How does Andhrua's spend compare with its plan each year?",
            'What is the current-year expenditure of a given GP Name against the plans of each of the last three years?',
            'What is the year-wise expenditure of a given gram panchayat against the plan of each year?',
            'What is the year-wise expenditure of a given district against the plan of each year?',
            'What is the year-wise expenditure of a given block against the plan of each year?',
        ],
    },

    'TRD-004': {
        "abstract_question": 'How did the total expenditure of {block_name} change between {date_range_2} and {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range_2) AS expenditure_year1,
       SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range)   AS expenditure_year2,
       SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range)
       - SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range_2) AS change_amount,
       ROUND(100.0 * (SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range)
                    - SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range_2))
             / NULLIF(SUM(v.total_expenditure) FILTER (WHERE v.fiscal_year = $date_range_2),0), 2) AS change_pct
FROM v_activity v
WHERE v.fiscal_year IN ($date_range, $date_range_2)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'date_range_2', 'entity_type': 'fiscal_year_2'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Comparison',
        "answerable": 'Yes',
        "paraphrases": [
            "How did Bhubaneswar's expenditure change from 2023-2024 to 2024-2025?",
            'How did the total expenditure of a given Block change between a given Financial Year and a given Financial Year 2?',
            'How did the total expenditure of a given block change between a second year and a given year?',
            'How did the total expenditure of a given district change between a second year and a given year?',
            'How did the total expenditure of a given gram panchayat change between a second year and a given year?',
        ],
    },

    'TRD-005': {
        "abstract_question": 'How has the activity completion rate of {district_name} changed over the years?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.fiscal_year,
       COUNT(*) AS activities,
       SUM(v.is_started)   AS started,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct,
       ROUND(100.0 * SUM(v.is_started)   / NULLIF(COUNT(*),0), 2) AS initiation_rate_pct
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
ORDER BY 1
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Only 17 activities in the whole database are marked WORK COMPLETED, so completion rates are near zero throughout.',
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Trend',
        "answerable": 'Partial',
        "paraphrases": [
            "How has Khordha's completion rate moved year on year?",
            'How has the activity completion rate of a given District changed over a given Date Range?',
            'How has the activity completion rate of a given district changed over the years?',
            'How has the activity completion rate of a given block changed over the years?',
            'How has the activity completion rate of a given gram panchayat changed over the years?',
        ],
    },

    'TRD-006': {
        "abstract_question": 'What is the year-wise total expenditure of {gp_name}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.fiscal_year,
       COUNT(*) AS activities,
       SUM(v.total_expenditure) AS expenditure
FROM v_activity v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY v.gp_name, v.fiscal_year
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Trends & Comparison',
        "module": 'Trends & Comparison',
        "submodule": 'Year-on-Year',
        "question_type": 'Trend',
        "answerable": 'Yes',
        "paraphrases": [
            "What is Andhrua's year-wise expenditure?",
            'What is the year-wise total expenditure of a given GP Name over a given Date Range?',
            'What is the year-wise total expenditure of a given gram panchayat?',
            'What is the year-wise total expenditure of a given district?',
            'What is the year-wise total expenditure of a given block?',
        ],
    },

    'ALR-001': {
        "abstract_question": 'Which administratively approved activities in {block_name} still have zero expenditure {threshold} days after sanction?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.sanction_day, v.sanction_authority,
       v.admin_approved_cost, v.total_expenditure,
       DATE_DIFF('day', v.sanction_day, CURRENT_DATE) AS days_since_sanction,
       v.status_label
FROM v_activity v
WHERE v.is_admin_approved = 1
  AND COALESCE(v.total_expenditure,0) = 0
  AND DATE_DIFF('day', v.sanction_day, CURRENT_DATE) > $threshold
  AND ($date_range IS NULL OR v.fiscal_year = $date_range)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY days_since_sanction DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'date_range', 'entity_type': 'fiscal_year', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Unblocked by the sanction date. Measured against today's date, so results move as time passes. Pass $date_range = NULL to sweep every year. Administrative approval now comes from the admin_approval table: 2,101 of 12,704 activities (17%) have a sanction record. A further 140 activities carry an admin_approved_cost with no approval row - v_activity.has_approval_cost_only flags those.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities have spent nothing 180 days after sanction?',
            'Which administratively approved activities in a given Block have zero expenditure a given Threshold days after sanction in a given year?',
            'Which administratively approved activities in a given block still have zero expenditure a given threshold days after sanction?',
            'Which administratively approved activities in a given district still have zero expenditure a given threshold days after sanction?',
            'Which administratively approved activities in a given gram panchayat still have zero expenditure a given threshold days after sanction?',
        ],
    },

    'ALR-002': {
        "abstract_question": 'Which activities in {district_name} have expenditure exceeding their administratively approved cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.admin_approved_cost, v.total_expenditure,
       v.total_expenditure - v.admin_approved_cost AS overrun_amount,
       ROUND(100.0 * (v.total_expenditure - v.admin_approved_cost)
             / NULLIF(v.admin_approved_cost,0), 2) AS overrun_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.admin_approved_cost,0) > 0
  AND v.total_expenditure > v.admin_approved_cost
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY overrun_amount DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha activities overshot their sanction in 2024-2025?',
            'Which activities in a given District have expenditure exceeding their administratively approved cost in a given year?',
            'Which activities in a given block have expenditure exceeding their administratively approved cost in a given year?',
            'Which activities in a given gram panchayat have expenditure exceeding their administratively approved cost in a given year?',
        ],
    },

    'ALR-003': {
        "abstract_question": 'Which activities in {block_name} have expenditure more than {threshold} percent above estimated cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost AS estimated_cost, v.total_expenditure,
       ROUND(100.0 * (v.total_expenditure - v.total_cost)
             / NULLIF(v.total_cost,0), 2) AS overrun_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.total_cost,0) > 0
  AND v.total_expenditure > v.total_cost * (1 + $threshold / 100.0)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY overrun_pct DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities exceed their estimate by 50% in 2024-2025?',
            'Which activities in a given Block have expenditure more than a given Threshold percent above estimated cost in a given year?',
            'Which activities in a given district have expenditure more than a given threshold percent above estimated cost in a given year?',
            'Which activities in a given gram panchayat have expenditure more than a given threshold percent above estimated cost in a given year?',
        ],
    },

    'ALR-004': {
        "abstract_question": 'Which activities in {district_name} have a technically approved cost higher than the administratively approved cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.technical_approved_cost, v.admin_approved_cost,
       v.technical_approved_cost - v.admin_approved_cost AS difference
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.technical_approved_cost,0) > 0
  AND COALESCE(v.admin_approved_cost,0) > 0
  AND v.technical_approved_cost > v.admin_approved_cost
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY difference DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha activities have TS above AS in 2024-2025?',
            'Which activities in a given District have a technically approved cost higher than the administratively approved cost in a given year?',
            'Which activities in a given block have a technically approved cost higher than the administratively approved cost in a given year?',
            'Which activities in a given gram panchayat have a technically approved cost higher than the administratively approved cost in a given year?',
        ],
    },

    'ALR-005': {
        "abstract_question": 'Which abandoned activities in {district_name} had expenditure incurred, and how much in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.admin_approved_cost, v.total_expenditure, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_abandoned = 1
  AND v.total_expenditure > 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "There is no abandonment date, so 'before abandonment' cannot be tested; all expenditure on abandoned activities is returned.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Financial Exceptions',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which abandoned Khordha activities still spent money in 2024-2025?',
            'Which abandoned activities in a given District had expenditure incurred before abandonment, and how much in a given year?',
            'Which abandoned activities in a given district had expenditure incurred, and how much in a given year?',
            'Which abandoned activities in a given block had expenditure incurred, and how much in a given year?',
            'Which abandoned activities in a given gram panchayat had expenditure incurred, and how much in a given year?',
        ],
    },

    'ALR-012': {
        "abstract_question": 'Which GPs in {block_name} recorded no activity in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT g.gp_name, g.block_name, g.zp_name AS district_name,
       (SELECT COUNT(*) FROM v_activity a
         WHERE a.gp_lgd_code = g.gp_lgd_code AND a.fiscal_year = $date_range) AS activities,
       (SELECT COUNT(*) FROM v_voucher vv
         WHERE vv.gp_lgd_code = g.gp_lgd_code AND vv.fiscal_year = $date_range) AS vouchers
FROM gram_panchayat g
WHERE ($block_name    IS NULL OR g.block_name = $block_name)
  AND ($district_name IS NULL OR g.zp_name = $district_name)
  AND NOT EXISTS (SELECT 1 FROM v_activity a
                  WHERE a.gp_lgd_code = g.gp_lgd_code AND a.fiscal_year = $date_range)
  AND NOT EXISTS (SELECT 1 FROM v_voucher vv
                  WHERE vv.gp_lgd_code = g.gp_lgd_code AND vv.fiscal_year = $date_range)
ORDER BY g.zp_name, g.block_name, g.gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": "'Last N days' cannot be evaluated - activities carry no dates. Rewritten as 'no activity and no voucher in the given year'.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Inactivity',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs recorded nothing in 2024-2025?',
            'Which GPs in a given Block have recorded no new activities, sanctions, or payments in the last a given Threshold days?',
            'Which GPs in a given block recorded no activity in a given year?',
            'Which GPs in a given district recorded no activity in a given year?',
        ],
    },

    'ALR-013': {
        "abstract_question": 'Which GPs in {district_name} have no data entry for {date_range} in any module?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
WITH gp_counts AS (
  SELECT g.gp_name, g.block_name, g.zp_name AS district_name,
         (SELECT COUNT(*) FROM plan p
           WHERE p.gp_lgd_code = g.gp_lgd_code AND p.fiscal_year = $date_range) AS plans,
         (SELECT COUNT(*) FROM v_activity a
           WHERE a.gp_lgd_code = g.gp_lgd_code AND a.fiscal_year = $date_range) AS activities,
         (SELECT COUNT(*) FROM v_voucher vv
           WHERE vv.gp_lgd_code = g.gp_lgd_code AND vv.fiscal_year = $date_range) AS vouchers
  FROM gram_panchayat g
  WHERE ($district_name IS NULL OR g.zp_name = $district_name)
    AND ($block_name    IS NULL OR g.block_name = $block_name))
SELECT * FROM gp_counts
WHERE plans = 0 AND activities = 0 AND vouchers = 0
ORDER BY district_name, block_name, gp_name
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Checks the three modules that hold GP-level data: plan, activities and vouchers.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Inactivity',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha GPs have no data at all for 2024-2025?',
            'Which GPs in a given District have no data entry for a given Plan Year in any module?',
            'Which GPs in a given district have no data entry for a given year in any module?',
            'Which GPs in a given block have no data entry for a given year in any module?',
        ],
    },

    'ALR-008': {
        "abstract_question": 'Which activities approved more than {threshold} days ago in {block_name} are still not started?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name, v.fiscal_year,
       v.sanction_day, v.sanction_authority, v.status_label,
       v.admin_approved_cost, v.total_expenditure,
       DATE_DIFF('day', v.sanction_day, CURRENT_DATE) AS days_since_sanction
FROM v_activity v
WHERE v.is_admin_approved = 1
  AND v.is_started = 0
  AND DATE_DIFF('day', v.sanction_day, CURRENT_DATE) > $threshold
  AND ($date_range IS NULL OR v.fiscal_year = $date_range)
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY days_since_sanction DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'date_range', 'entity_type': 'fiscal_year', 'optional': True},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Unblocked by the sanction date. 'Not started' means the status is not WORK ONGOING or WORK COMPLETED.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Progress Exceptions',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities sanctioned over 180 days ago have not started?',
            'Which activities approved more than a given Threshold days ago in a given Block are still marked Not Started?',
            'Which activities approved more than a given threshold days ago in a given block are still not started?',
            'Which activities approved more than a given threshold days ago in a given district are still not started?',
            'Which activities approved more than a given threshold days ago in a given gram panchayat are still not started?',
        ],
    },

    'ALR-009': {
        "abstract_question": 'Which GPs in {block_name} have an approved plan but no administratively approved activities in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT p.gp_name, p.block_name, p.district_name,
       COUNT(DISTINCT p.plan_code) AS approved_plans,
       COALESCE(SUM(a.is_admin_approved),0) AS admin_approved_activities,
       COUNT(a.activity_code) AS total_activities
FROM v_plan p
LEFT JOIN v_activity a ON a.gp_lgd_code = p.gp_lgd_code AND a.fiscal_year = p.fiscal_year
WHERE p.fiscal_year = $date_range
  AND p.is_approved = 1
  AND ($district_name IS NULL OR p.district_name = $district_name)
  AND ($block_name    IS NULL OR p.block_name    = $block_name)
GROUP BY 1,2,3
HAVING COALESCE(SUM(a.is_admin_approved),0) = 0
ORDER BY total_activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Administrative approval proxied by admin_approved_cost > 0.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Progress Exceptions',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs have a plan but no sanctions in 2024-2025?',
            'Which GPs in a given Block have an approved plan but no administratively approved activities in a given Plan Year?',
            'Which GPs in a given block have an approved plan but no administratively approved activities in a given year?',
            'Which GPs in a given district have an approved plan but no administratively approved activities in a given year?',
        ],
    },

    'ALR-011': {
        "abstract_question": 'Which blocks in {district_name} are below {threshold} percent activity completion in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(v.is_completed) AS completed,
       SUM(v.is_started)   AS started,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
HAVING 100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0) < $threshold
ORDER BY completion_rate_pct ASC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'threshold', 'entity_type': 'threshold'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'There is no mid-year cut-off in the data, so the whole year is measured. Only 17 activities database-wide are marked complete, so nearly every block will qualify.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Alerts & Exceptions',
        "submodule": 'Progress Exceptions',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Khordha blocks sit below 50% completion in 2024-2025?',
            'Which blocks in a given District are below a given Threshold percent activity completion at mid-year of a given Plan Year?',
            'Which blocks in a given district are below a given threshold percent activity completion in a given year?',
        ],
    },

    'DQY-006': {
        "abstract_question": 'Which activities in {block_name} are marked completed or ongoing but have no progress evidence in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.status_label, v.evidence_uploads,
       v.admin_approved_cost, v.total_expenditure
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_started = 1
  AND v.has_progress_evidence = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Rewritten: the original compared status against asset stages, which do not exist. This instead flags activities reported as started or completed that have no geotagged upload behind them.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar activities claim progress with no evidence in 2024-2025?',
            'Which activities in a given Block are marked completed in the status report but have incomplete asset stages in a given year?',
            'Which activities in a given block are marked completed or ongoing but have no progress evidence in a given year?',
            'Which activities in a given district are marked completed or ongoing but have no progress evidence in a given year?',
            'Which activities in a given gram panchayat are marked completed or ongoing but have no progress evidence in a given year?',
        ],
    },

    'DQY-007': {
        "abstract_question": 'Which activities in {district_name} have a zero or negative estimated cost recorded in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_cost, v.approved_cost_action_plan, v.total_expenditure,
       v.is_costless_activity, v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND COALESCE(v.total_cost,0) <= 0
  AND COALESCE(v.is_costless_activity,0) <> 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Activities flagged is_costless_activity = 1 are excluded, since a zero cost is legitimate for those. Verified clean: all 7,074 zero-cost activities carry the costless flag, so this returns no rows in every year.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha activities have a zero or negative cost in 2024-2025?',
            'Which activities in a given District have a zero or negative estimated cost recorded in a given year?',
            'Which activities in a given block have a zero or negative estimated cost recorded in a given year?',
            'Which activities in a given gram panchayat have a zero or negative estimated cost recorded in a given year?',
        ],
    },

    'DQY-008': {
        "abstract_question": 'Which activities within {gp_name} share identical descriptions in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.activity_name,
       COUNT(*) AS duplicate_count,
       STRING_AGG(v.activity_code, ', ') AS activity_codes,
       SUM(COALESCE(v.total_cost,0)) AS combined_planned_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": 'Exact string match on activity_name within one GP and year. Legitimate repeats (e.g. several IHHLs) will appear here too.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Andhrua activities have duplicate descriptions in 2024-2025?',
            'Which activities within a given GP Name share identical descriptions in a given Plan Year?',
            'Which activities within a given gram panchayat share identical descriptions in a given year?',
            'Which activities within a given district share identical descriptions in a given year?',
            'Which activities within a given block share identical descriptions in a given year?',
        ],
    },

    'DQY-009': {
        "abstract_question": 'For which activities in {block_name} does the sanctioned scheme funding not equal the approved cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.scheme_rows AS scheme_allocation_rows,
       v.fund_sanctioned_total,
       v.admin_approved_cost,
       v.work_proposed_cost,
       v.fund_sanctioned_total - COALESCE(v.admin_approved_cost,0) AS difference
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND v.fund_sanctioned_total IS NOT NULL
  AND ABS(v.fund_sanctioned_total - COALESCE(v.admin_approved_cost,0)) > 1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY ABS(v.fund_sanctioned_total - COALESCE(v.admin_approved_cost,0)) DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Unblocked by admin_approval_scheme. Compares the sum of scheme-wise sanctioned funds against the administratively approved cost for the same activity. A tolerance of 1 rupee absorbs rounding.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities have a scheme-funding mismatch in 2024-2025?',
            'For which activities in a given Block does the sum of scheme-wise fund allocations not equal the total activity cost in a given year?',
            'For which activities in a given block does the sanctioned scheme funding not equal the approved cost in a given year?',
            'For which activities in a given district does the sanctioned scheme funding not equal the approved cost in a given year?',
            'For which activities in a given gram panchayat does the sanctioned scheme funding not equal the approved cost in a given year?',
        ],
    },

    'DQY-010': {
        "abstract_question": 'Which GPs in {district_name} show all-zero values in the physical-financial comparison for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name, v.district_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.total_cost,0)) AS planned_cost,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(v.is_started) AS started
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2,3
HAVING COALESCE(SUM(COALESCE(v.total_cost,0)),0) = 0
   AND COALESCE(SUM(v.total_expenditure),0) = 0
ORDER BY activities DESC
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "grouped_geo": [
    'district_name',
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Khordha GPs are all-zero in 2024-2025?',
            'Which GPs in a given District show all-zero values in the physical-financial comparison for a given Financial Year?',
            'Which GPs in a given district show all-zero values in the physical-financial comparison for a given year?',
            'Which GPs in a given block show all-zero values in the physical-financial comparison for a given year?',
            'Which GPs in a given gram panchayat show all-zero values in the physical-financial comparison for a given year?',
        ],
    },

    'DQY-011': {
        "abstract_question": 'Which activities in {block_name} report expenditure but have no payment vouchers in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.total_expenditure,
       COALESCE(av.voucher_count, 0) AS vouchers,
       COALESCE(av.voucher_total, 0) AS voucher_total
FROM v_activity v
LEFT JOIN (SELECT expenditure_id, COUNT(*) AS voucher_count,
                  SUM(voucher_cost) AS voucher_total
           FROM activity_voucher GROUP BY expenditure_id) av
       ON av.expenditure_id = v.expenditure_id
WHERE v.fiscal_year = $date_range
  AND v.total_expenditure > 0
  AND COALESCE(av.voucher_count,0) = 0
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Verified clean: all 1,911 activities with expenditure above zero have at least one linked voucher, so this query correctly returns no rows in every year. It is worth keeping as an ongoing check.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Inconsistencies',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities spent money with no voucher in 2024-2025?',
            'Which activities in a given Block report expenditure but have zero payment vouchers in a given year?',
            'Which activities in a given block report expenditure but have no payment vouchers in a given year?',
            'Which activities in a given district report expenditure but have no payment vouchers in a given year?',
            'Which activities in a given gram panchayat report expenditure but have no payment vouchers in a given year?',
        ],
    },

    'DQY-001': {
        "abstract_question": 'How many activities in {district_name} have no focus area recorded for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE v.focus_area_name LIKE 'Code %') AS undecoded_focus_area,
       COUNT(*) FILTER (WHERE v.focus_area IS NULL) AS missing_focus_area,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.focus_area IS NULL OR v.focus_area_name LIKE 'Code %')
             / NULLIF(COUNT(*),0), 2) AS pct_unusable
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Separates genuinely missing focus areas from codes that exist but are not in the decoder.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Missing Fields',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Khordha activities lack a focus area in 2024-2025?',
            'How many activities in a given District have no focus area recorded for a given Plan Year?',
            'How many activities in a given district have no focus area recorded for a given year?',
            'How many activities in a given block have no focus area recorded for a given year?',
            'How many activities in a given gram panchayat have no focus area recorded for a given year?',
        ],
    },

    'DQY-002': {
        "abstract_question": 'Which asset-creating activities in {block_name} have no asset details recorded in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.asset_category_label, v.asset_subcategory_label, v.total_expenditure
FROM v_asset v
WHERE v.fiscal_year = $date_range
  AND v.asset_category IS NULL
  AND v.asset_subcategory IS NULL
  AND v.main_asset_category IS NULL
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
ORDER BY v.total_expenditure DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'This is the single biggest data-quality gap: asset detail is missing on roughly two-thirds of asset rows.',
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Missing Fields',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar activities have no asset detail in 2024-2025?',
            'Which asset-creating activities in a given Block have no asset details recorded in a given year?',
            'Which asset-creating activities in a given district have no asset details recorded in a given year?',
            'Which asset-creating activities in a given gram panchayat have no asset details recorded in a given year?',
        ],
    },

    'DQY-003': {
        "abstract_question": 'Which administratively approved activities in {block_name} have a missing sanction order date or authority in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.adm_approval_no, v.sanction_day, v.sanction_authority_raw,
       v.tec_approval_order_no, v.tec_approval_order_date,
       v.admin_approved_cost
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_admin_approved = 1
  AND (v.sanction_day IS NULL
       OR v.sanction_authority_raw IS NULL
       OR TRIM(v.sanction_authority_raw) = ''
       OR UPPER(TRIM(v.sanction_authority_raw)) IN ('NR','NA','N/A','-')
       OR UPPER(TRIM(COALESCE(v.tec_approval_order_no,''))) = 'NR')
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.admin_approved_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "Unblocked by the new approval tables. Sanction dates are 100% populated, so this mostly surfaces the 'NR' placeholder in technical order numbers (3.5% of rows) and stray authority values.",
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Missing Fields',
        "question_type": 'Listing',
        "answerable": 'Yes',
        "paraphrases": [
            'Which Bhubaneswar sanctions are missing their date or authority in 2024-2025?',
            'Which administratively approved activities in a given Block have a missing sanction order date in a given year?',
            'Which administratively approved activities in a given block have a missing sanction order date or authority in a given year?',
            'Which administratively approved activities in a given district have a missing sanction order date or authority in a given year?',
            'Which administratively approved activities in a given gram panchayat have a missing sanction order date or authority in a given year?',
        ],
    },

    'DQY-004': {
        "abstract_question": 'How many activities in {district_name} have no funding scheme recorded for {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT COUNT(*) AS total_activities,
       COUNT(*) FILTER (WHERE v.scheme_name IS NULL) AS missing_scheme,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.scheme_name IS NULL)
             / NULLIF(COUNT(*),0), 2) AS pct_missing_scheme
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
        ],
        "result_ttl_seconds": 600,
        "bracket": 'Monitoring, Alerts & Data Quality',
        "module": 'Data Quality',
        "submodule": 'Missing Fields',
        "question_type": 'Count',
        "answerable": 'Yes',
        "paraphrases": [
            'How many Khordha activities lack a scheme in 2024-2025?',
            'Which activities in a given District have no funding scheme recorded for a given Plan Year?',
            'How many activities in a given district have no funding scheme recorded for a given year?',
            'How many activities in a given block have no funding scheme recorded for a given year?',
            'How many activities in a given gram panchayat have no funding scheme recorded for a given year?',
        ],
    },

    'DSS-001': {
        "abstract_question": 'Which focus areas in {gp_name} have high approved cost but completion below {threshold} percent in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.focus_area_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.admin_approved_cost,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(v.is_completed) AS completed,
       ROUND(100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0), 2) AS completion_rate_pct
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1
HAVING 100.0 * SUM(v.is_completed) / NULLIF(COUNT(*),0) < $threshold
ORDER BY approved_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Only 17 activities database-wide are complete, so almost every focus area falls below any threshold.',
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Andhrua focus areas are costly but under 50% complete in 2024-2025?',
            'Which focus areas in a given GP Name have high approved cost but completion below a given Threshold percent in a given Plan Year?',
            'Which focus areas in a given gram panchayat have high approved cost but completion below a given threshold percent in a given year?',
            'Which focus areas in a given district have high approved cost but completion below a given threshold percent in a given year?',
            'Which focus areas in a given block have high approved cost but completion below a given threshold percent in a given year?',
        ],
    },

    'DSS-002': {
        "abstract_question": 'Which blocks in {district_name} combine high pending sanctions with low expenditure in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.block_name, v.district_name,
       COUNT(*) AS activities,
       COUNT(*) FILTER (WHERE v.is_admin_approved = 0) AS pending_sanctions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_admin_approved = 0)
             / NULLIF(COUNT(*),0), 2) AS pct_pending,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS planned_cost,
       SUM(v.total_expenditure) AS expenditure,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
GROUP BY 1,2
ORDER BY pct_pending DESC, pct_utilised ASC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'district_name',
],
        "result_ttl_seconds": 600,
        "caveat": "'High' and 'low' are undefined; blocks are ranked by share pending then by utilisation.",
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Khordha blocks have many pending sanctions and little spend in 2024-2025?',
            'Which blocks in a given District combine high pending sanctions with low expenditure in a given Plan Year?',
            'Which blocks in a given district combine high pending sanctions with low expenditure in a given year?',
        ],
    },

    'DSS-003': {
        "abstract_question": 'Which asset sub-categories in {block_name} show the highest repeat-maintenance frequency in a given year?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.asset_subcategory_label,
       COUNT(*) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_activities,
       COUNT(DISTINCT v.fiscal_year) FILTER (WHERE v.work_type_label = 'Maintenance') AS years_with_maintenance,
       COUNT(*) AS total_asset_rows,
       SUM(v.total_expenditure) FILTER (WHERE v.work_type_label = 'Maintenance') AS maintenance_expenditure
FROM v_asset v
WHERE 1=1
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name))
GROUP BY 1
HAVING COUNT(*) FILTER (WHERE v.work_type_label = 'Maintenance') > 0
ORDER BY years_with_maintenance DESC, maintenance_activities DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": 'Pooled across all years because a single year cannot show repeat maintenance. asset_subcategory is missing on two-thirds of rows.',
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar asset sub-categories need repeat maintenance most?',
            'Which asset sub-categories in a given Block show the highest repeat-maintenance frequency and should be prioritised for replacement budgeting in a given year?',
            'Which asset sub-categories in a given block show the highest repeat-maintenance frequency in a given year?',
            'Which asset sub-categories in a given district show the highest repeat-maintenance frequency in a given year?',
            'Which asset sub-categories in a given gram panchayat show the highest repeat-maintenance frequency in a given year?',
        ],
    },

    'DSS-005': {
        "abstract_question": 'Which ongoing activities in {block_name} have spent less than {threshold} percent of their sanctioned cost in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.activity_code, v.activity_name, v.gp_name, v.block_name,
       v.admin_approved_cost, v.total_expenditure,
       ROUND(100.0 * v.total_expenditure
             / NULLIF(v.admin_approved_cost,0), 2) AS pct_of_sanction_spent,
       v.status_label
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND v.is_ongoing = 1
  AND COALESCE(v.admin_approved_cost,0) > 0
  AND 100.0 * v.total_expenditure / NULLIF(v.admin_approved_cost,0) < $threshold
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
ORDER BY v.admin_approved_cost DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'threshold', 'entity_type': 'threshold'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "result_ttl_seconds": 600,
        "caveat": "There is no date on activities, so 'with one quarter left' cannot be evaluated; the whole year is used.",
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "question_type": 'Listing',
        "answerable": 'Partial',
        "paraphrases": [
            'Which ongoing Bhubaneswar activities are under 50% spent in 2024-2025?',
            'Which ongoing activities in a given Block have spent less than a given Threshold percent of sanctioned cost with one quarter left in a given Plan Year?',
            'Which ongoing activities in a given block have spent less than a given threshold percent of their sanctioned cost in a given year?',
            'Which ongoing activities in a given district have spent less than a given threshold percent of their sanctioned cost in a given year?',
            'Which ongoing activities in a given gram panchayat have spent less than a given threshold percent of their sanctioned cost in a given year?',
        ],
    },

    'DSS-006': {
        "abstract_question": 'Which GPs in {block_name} have the largest unspent balance in {date_range}?',
        "date_filter": None,
        "date_kind": None,
        "sql_template": """
SELECT v.gp_name, v.block_name,
       COUNT(*) AS activities,
       SUM(COALESCE(v.approved_cost_action_plan,0)) AS approved_cost,
       SUM(v.total_expenditure) AS expenditure,
       SUM(COALESCE(v.approved_cost_action_plan,0)) - SUM(v.total_expenditure) AS unspent_balance,
       ROUND(100.0 * SUM(v.total_expenditure)
             / NULLIF(SUM(COALESCE(v.approved_cost_action_plan,0)),0), 2) AS pct_utilised
FROM v_activity v
WHERE v.fiscal_year = $date_range
  AND ($district_name IS NULL OR v.district_name = $district_name)
  AND ($block_name    IS NULL OR v.block_name    = $block_name)
  AND ($gp_name       IS NULL OR v.gp_lgd_code   = $gp_name)
GROUP BY 1,2
ORDER BY unspent_balance DESC
LIMIT $top_n
""",
        "param_slots": [
            {'name': 'date_range', 'entity_type': 'fiscal_year'},
            {'name': 'district_name', 'entity_type': 'district', 'optional': True},
            {'name': 'block_name', 'entity_type': 'block', 'optional': True},
            {'name': 'gp_name', 'entity_type': 'gp', 'optional': True, 'bind': 'code'},
            {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
        ],
        "grouped_geo": [
    'block_name',
    'gp_name',
],
        "result_ttl_seconds": 600,
        "caveat": "There is no resource-envelope table, so 'unprogrammed envelope balance' is approximated by approved plan cost minus actual expenditure.",
        "bracket": 'Decision Support',
        "module": 'Decision Support',
        "submodule": 'Prioritisation',
        "question_type": 'Ranking',
        "answerable": 'Partial',
        "paraphrases": [
            'Which Bhubaneswar GPs have the most unspent money in 2024-2025?',
            'Which GPs in a given Block have large unprogrammed envelope balances that could absorb additional activities in a given Plan Year?',
            'Which GPs in a given block have the largest unspent balance in a given year?',
            'Which GPs in a given district have the largest unspent balance in a given year?',
            'Which GPs in a given gram panchayat have the largest unspent balance in a given year?',
        ],
    },
}


ALL_TEMPLATES: dict[str, dict] = TEMPLATE_CATALOG


def bind(template_id: str, values: dict):
    """Return (sql, params) for a template and a {slot_name: value} dict.

    Every PR&DW template is NAMED, so this returns a DICT with one entry per
    slot name however often that name occurs in the statement — which is the
    normal case here, since `($p IS NULL OR col = $p)` writes each parameter
    twice. The positional branch is kept because `sql_params.param_style` still
    detects positional SQL and the engine must not silently mis-bind it.

    Slots marked {"optional": True} may be absent from `values`; they bind None
    (SQL NULL). Missing REQUIRED slots still raise.
    """
    from .sql_params import NAMED, param_style

    t = ALL_TEMPLATES[template_id]
    slots = t['param_slots']
    optional = {s['name'] for s in slots if s.get('optional')}
    missing = {s['name'] for s in slots} - set(values) - optional
    if missing:
        raise KeyError(f'{template_id} missing slot values: {sorted(missing)}')

    if param_style(t) == NAMED:
        return t['sql_template'], {s['name']: values.get(s['name']) for s in slots}

    ordered = sorted(slots, key=lambda s: s['position'])
    return t['sql_template'], [values.get(s['name']) for s in ordered]


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


def family_of(template_id: str) -> tuple[str, str, str]:
    """(bracket, module, submodule) — the grouping rerank_context.py families on."""
    t = ALL_TEMPLATES[template_id]
    return (t['bracket'], t['module'], t['submodule'])

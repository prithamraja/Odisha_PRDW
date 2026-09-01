#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4b -- constants for the insight-prose build step (phase5e).

This module exists because the constants outgrew the step (the brief allows it
on exactly that condition). It carries four things and no logic:

  1. the instantiated Appendix A context -- the WP-D4 template, verbatim
  2. the one-line variable definitions -- transcribed from the SIGNED glossary
  3. the ceilings, the model pins and the spend guard
  4. the token/name tables the nothing-invented checks match against

Nothing here is edited at run time and nothing here is interpretive.

PORTED, NOT IMPORTED. Every value below is a fresh transcription of the frozen
trial record in `Insights/prose_trial/` (context.py, glossary.py, checks.py,
llm.py, verify.py). The trial directory is the frozen evidence of the accepted
design and this WP may not edit or import from it, so the logic is re-expressed
here. Divergences from the trial are marked `WPD4b:` and every one of them is
in the WP-D4b report's decision journal.
"""
import os

# ---------------------------------------------------------------------------
# Paths.
#
# BASE_DIR is the `Insights` directory -- the same convention phase5b_report and
# phase4a_engine already use, which is why the checker's flag reads
# `--base Insights`. Every path below hangs off it, and `--base` overrides it, so
# the step runs identically in the Drive tree and in the local mirror.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_HERE)


def paths(base_dir=None):
    """Every path this step reads or writes, resolved against one base."""
    b = base_dir or BASE_DIR
    meta = os.path.join(b, "metainsights")
    return {
        "base": b,
        "src": os.path.join(b, "src"),
        "metainsights": meta,
        "feed": os.path.join(meta, "global_feed.json"),
        "source_set": os.path.join(meta, "global_feed_source_set.json"),
        "sidecar": os.path.join(meta, "insight_prose.json"),
        # WP-D4d. The deterministic markdown rendering of the sidecar, emitted
        # by phase5e --emit-feed-md and copied into the frontend's drop-in
        # folder. It is a RENDERING, never a source: nothing reads it back.
        "feed_md": os.path.join(meta, "insight_feed.md"),
        "run_log_dir": os.path.join(b, "reports_prdw", "wpd4c_run"),
        # The API key lives in Insights/.env and is loaded FROM THERE, in place
        # -- never copied into the mirror, never printed, never written. WPD3
        # section 4.4 bug 1 was exactly this path being wrong and the load
        # silently doing nothing, so it is derived, not guessed, and the loader
        # asserts the file exists before it claims to have loaded anything.
        "env": os.path.join(b, ".env"),
    }

# ---------------------------------------------------------------------------
# Models. The writer is pinned by D17 through discover_config -- imported by
# phase5e, never duplicated here, so an env-var flip moves this step and the
# executive report together.
#
# VERIFIER: changed from `gpt-5.5` to `gpt-5.6-luna` on 2026-09-01, on the
# operator's instruction, for cost. THIS WEAKENS T4 AND THE CHANGE IS NOT
# COSMETIC -- record it as such rather than restating the old claim:
#
#   * WP-D4 T4 asks for a DIFFERENT model than the writer. Until now that was
#     read as a different GENERATION (`gpt-5.5` judging `gpt-5.6-sol`), and
#     both WPD4_REPORT sec.4 and WPD4b_REPORT sec.4 certify it in those words.
#   * `luna` is a SIBLING of the writer, not a different generation. Per
#     discover_config's pin note, luna/sol/terra were created within eleven
#     minutes of each other, carry no distinguishing metadata beyond the name,
#     and sol won the pin on the prose of a single probe. So this is much
#     closer to self-review than the accepted design intended.
#   * The verifier is the only layer that caught the three real drifts no
#     mechanical check could see (WPD4_REPORT sec.3). Treat its verdicts as a
#     weaker signal until a run measures whether it still catches them.
#
# Both reports' "different model generation, as the design requires" lines are
# now stale, and the D40 item 11 gate is reopened on this point.
#
# Same vendor remains true and remains disclosed: Insights/.env serves one
# vendor's completion key and a cross-vendor judge needs a new credential.
#
# NOT RE-PROBED. The 4,000 ceiling below was sized against gpt-5.5's reasoning
# behaviour. `verifier_budget_check` in phase5e probes the real prompt at the
# real ceiling before the loop -- read its output on the first luna run before
# trusting the verdicts.
# ---------------------------------------------------------------------------
VERIFIER_MODEL = os.getenv("DISCOVER_VERIFIER_MODEL", "gpt-5.6-luna")

# ---------------------------------------------------------------------------
# Spend guard and ceilings (brief: 16k in / 8k writer / 4k verifier, 120 calls).
#
# WPD4b: the cap is enforced on TWO counters, not the trial's one. The trial
# counted lines in a single append-only log, which makes a second run of the
# same build impossible -- and the T2 gate requires exactly that. So:
#   MAX_CALLS_PER_RUN  guards one invocation
#   MAX_CALLS_TOTAL    guards the WP, counted across every run log in RUN_LOG_DIR
# The brief's 120 is the WP-wide number; both counters are checked before a call.
# ---------------------------------------------------------------------------
# WP-D4c raises the WP-wide cap to 150 (one build is ~55, leaving
# headroom for a second if a defect forces one -- D44 ruling 4).
MAX_CALLS_TOTAL = 150
MAX_CALLS_PER_RUN = 150
MAX_INPUT_TOKENS = 16000
WRITER_MAX_COMPLETION = 8000
# 16,000, raised from 4,000 on 2026-09-01 on the operator's instruction, at the
# same time as the luna pin above. 4,000 was sized against gpt-5.5 and it was
# already tight there -- WP-D4 round 2 starved once in nineteen calls at it,
# spending the whole budget on reasoning and returning an empty string, which
# silently downgraded a sound rendering (D43's retry-on-empty treats that
# symptom). luna's reasoning behaviour on this prompt shape is UNMEASURED, so
# the ceiling is raised rather than re-probed.
#
# A ceiling is not a target: a healthy call still stops at `stop` and is charged
# for what it used, so this costs nothing on the calls that work. What it does
# change is the cost of a call that runs away -- a starving verifier now burns
# up to 16,000 completion tokens before it gives up instead of 4,000, twice over
# given VERIFIER_RETRY_ON_EMPTY. Watch `verifier_budget_check` headroom on the
# first luna run; if the real spend is nowhere near this, bring it back down.
VERIFIER_MAX_COMPLETION = 16000

# WPD4b: the batch PLANNER aims below the hard cap by this margin; the guard in
# the call path still refuses anything over MAX_INPUT_TOKENS. Two reasons. The
# local estimate is tiktoken's and the API's count runs a little higher (the
# trial measured 14,391 estimated against 14,397 charged), and a batch that
# overshoots mid-run is a hard STOP that wastes every call already spent. With
# no margin, the view1 batch of 15 packets plans at 15,886 -- 114 tokens of
# headroom, which is not headroom. This changes only WHERE a size split falls;
# it is still purely a size rule and curates nothing.
BATCH_PLAN_MARGIN = 500

# WPD4b addition (D43): a verifier call that returns nothing PARSEABLE is retried
# once at the same ceiling before it counts as fail-to-verify. Round 2 lost a
# sound rendering to a one-off token starvation. "Retryable" means the response
# could not be parsed at all (empty completion, no JSON object, JSON that does
# not decode); a parsed-but-downgraded verdict -- the rubber-stamp guard, a vague
# verdict -- is NOT retried, because the judge did judge.
VERIFIER_RETRY_ON_EMPTY = 1

# ---------------------------------------------------------------------------
# Appendix A of the WP-D4 brief -- the reusable template, instantiated.
#
# The writer receives the INSTANTIATED text verbatim and never the slot names.
# Two punctuation-only fixes are applied at the DATA_DESCRIPTION splice, exactly
# as the accepted trial applied them (WP-D4 report, journal 3): the slot's
# em-dash parenthetical is closed before the template's "and surfaces ...", and
# the slot's second sentence is placed after the template sentence closes.
# No word of the template or of any slot value is added, changed or dropped.
#
# There is no background-facts block and no caution layer (D40 items 7 and 9).
# ---------------------------------------------------------------------------
AUDIENCE = ("government officials in Odisha's Department of Panchayati Raj & "
            "Drinking Water")

DATA_DESCRIPTION_MAIN = (
    "village-level planning and spending records — development plans, "
    "sanctions, payments, works and photo evidence from Gram Panchayats, "
    "blocks, and districts")
DATA_DESCRIPTION_TAIL = (
    "The current data is a 20-Gram-Panchayat sample; percentages describe the "
    "sample, not the state.")

READERS = "busy block-, district- and state-level officials"

ATTENTION_EXAMPLES = ("which districts to question, which records to reconcile, "
                      "which local practices to check at the next review")

CONTEXT = (
    "You are writing for a decision-aid system used by " + AUDIENCE + ". The "
    "system automatically analyses " + DATA_DESCRIPTION_MAIN + " — and "
    "surfaces patterns worth an official's attention. " + DATA_DESCRIPTION_TAIL
    + "\n\nYour readers are " + READERS + ", not data analysts. They read these "
    "insights to decide where to direct attention: " + ATTENTION_EXAMPLES + "."
    + "\n\nBelow are findings from the analysis engine, each written in the "
    "engine's internal style — accurate but full of database language "
    "— along with reference figures for each. Rewrite each finding as an "
    "insight a senior officer would find clear and actionable:"
    + "\n\n- a one-to-two-sentence lead the officer sees first. This should be "
    "interesting enough to catch a reader's attention and easy enough to "
    "understand that the officer doesn't need to read the subsequent paragraph "
    "simply to understand it. Lead with what the officer would act on — "
    "usually the size and direction of the issue — rather than with the "
    "statistical pattern."
    + "\n- a short detail paragraph explaining what was found, which places are "
    "exceptions and in what way, and what is worth checking or asking at the "
    "next review."
    + "\n\nWrite naturally, in plain English. Use the reference figures where "
    "they strengthen the point; use no number that is not provided. Be direct "
    "about what the data can and cannot establish — an insight that "
    "overstates certainty could send an official after the wrong problem."
)

SLOT_VALUES = {
    "AUDIENCE": AUDIENCE,
    "DATA_DESCRIPTION": DATA_DESCRIPTION_MAIN + ". " + DATA_DESCRIPTION_TAIL,
    "READERS": READERS,
    "ATTENTION_EXAMPLES": ATTENTION_EXAMPLES,
}

# ---------------------------------------------------------------------------
# Variable definitions.
#
# Source: the SIGNED glossary -- handoffs/WPD2_mining_calibration.md Appendix A,
# transcribed verbatim into
# phase5b_report.VIEW_DESCRIPTIONS[view]["column_glossary"] -- with units
# cross-checked against phase5b_report._UNITS.
#
# A definition says what a variable IS: unit, money basis (planned / sanctioned /
# spent / cashbook), sign convention where it is signed, and what the values are.
# It never says how much to trust it (WP-D4 T1). The glossary's trust sentences
# -- "completion is near-degenerate", "a near-zero here is data coverage, not a
# finding" -- are therefore NOT transcribed. Existence conditions ARE ("present
# only where a sanction record exists"), because they say what the values are;
# that is the accepted trial's own line on overspend_vs_sanction.
# ---------------------------------------------------------------------------
GLOSSARY_PROVENANCE = (
    "signed glossary: handoffs/WPD2_mining_calibration.md Appendix A "
    "(= phase5b_report.VIEW_DESCRIPTIONS column_glossary); units cross-checked "
    "against phase5b_report._UNITS")

# Keyed (view, measure): a name can mean different things in different views.
MEASURES = {
    ("view1", "overspend_vs_plan"):
        "rupees, totalled, SIGNED (money spent minus money planned). A positive "
        "figure is spending above the plan; a negative figure is planned money "
        "not spent.",
    ("view3", "overspend_vs_plan"):
        "rupees, totalled, SIGNED (money spent minus money planned), aggregated "
        "per Gram Panchayat per year. Positive is spending above the plan; "
        "negative is planned money not spent.",
    ("view1", "overspend_vs_sanction"):
        "rupees, totalled, SIGNED (money spent minus money sanctioned). Positive "
        "is spending above the sanctioned amount; negative is sanctioned money "
        "not spent. It exists only where a sanction record exists.",
    ("view3", "overspend_vs_sanction"):
        "rupees, totalled, SIGNED (money spent minus money sanctioned), "
        "aggregated per Gram Panchayat per year.",
    ("view1", "fund_untied_total"):
        "rupees, totalled, PLANNED basis -- the untied part of the planned "
        "funding. Untied is the discretionary grant (components 4211 and 4250), "
        "as against the tied grant, which is earmarked (component 4249).",
    ("view1", "fund_tied_total"):
        "rupees, totalled, PLANNED basis -- the tied, earmarked part of the "
        "planned funding (component 4249).",
    ("view1", "total_cost"):
        "rupees, totalled, PLANNED basis -- the action-plan cost. Empty for "
        "costless activities.",
    ("view1", "total_expenditure"):
        "rupees, totalled, SPENT basis -- voucher-linked actual spending.",
    ("view1", "n_activities"):
        "activities, counted -- one per planned activity.",
    ("view3", "n_activities"):
        "activities, counted -- one per planned activity, per Gram Panchayat "
        "per year.",
    ("view1", "gen_amount"):
        "rupees, totalled, SPENT basis -- voucher-linked spending recorded "
        "against the General social-category component (the other two "
        "components are SC and ST).",
    ("view1", "beneficiaries_expected"):
        "people, totalled -- the beneficiaries an activity records as expected. "
        "Recorded by the activities that carry community-service detail, 763 of "
        "them in this sample.",
    ("view1", "trainees_total"):
        "people, totalled -- recorded by the 1,034 activities that carry "
        "training detail.",
    ("view1", "evidence_uploads"):
        "geotagged photo uploads, counted -- 8,267 uploads across 1,675 "
        "activities in this sample.",
    ("view3", "evidence_uploads"):
        "geotagged photo uploads, counted, per Gram Panchayat per year.",
    ("view2", "activity_linked_expenditure"):
        "rupees, totalled, SPENT basis -- the part of the month's cashbook "
        "payments that is linked to a planned activity.",
    ("view2", "payment_count"):
        "vouchers, counted, CASHBOOK basis -- every payment voucher the Gram "
        "Panchayat recorded in the month, whether or not it is tied to a "
        "planned activity.",
    ("view2", "payment_amount"):
        "rupees, totalled, CASHBOOK basis -- all outflows recorded in the month.",
    ("view2", "receipt_amount"):
        "rupees, totalled, CASHBOOK basis -- all inflows recorded in the month.",
    ("view2", "receipt_count"):
        "vouchers, counted, CASHBOOK basis -- inflow vouchers recorded in the "
        "month.",
    ("view2", "sanctioned_amount"):
        "rupees, totalled, SANCTIONED basis, counted by the month the sanction "
        "is dated.",
    ("view2", "sanctions_count"):
        "sanctions, counted, by the month the sanction is dated.",
    ("view3", "sanctioned_total"):
        "rupees, totalled, SANCTIONED basis -- the approval amounts recorded "
        "for a Gram Panchayat in a fiscal year.",
    ("view3", "planned_cost"):
        "rupees, totalled, PLANNED basis, per Gram Panchayat per year.",
    ("view3", "expenditure_total"):
        "rupees, totalled, SPENT basis, per Gram Panchayat per year.",
    ("view3", "n_admin_approvals"):
        "sanction records, counted -- administrative approvals per Gram "
        "Panchayat per year.",
    ("view3", "n_tech_approvals"):
        "sanction records, counted -- technical approvals per Gram Panchayat "
        "per year.",

    # ---- WPD4b: transcribed for the variables ranks 16-32 add. Same signed
    # source, same rule (unit / basis / sign / what the values are; no trust
    # sentence, no reader guidance).
    ("view1", "fund_sanctioned_total"):
        "rupees, totalled, SANCTIONED basis -- the approved amount recorded "
        "against the activity. It exists only where a sanction record exists, "
        "which is about one activity in six.",
    ("view2", "payment_amount_mean"):
        "rupees, AVERAGED per Gram-Panchayat-month, CASHBOOK basis -- the same "
        "rupee column as payment_amount, divided by the number of "
        "Gram-Panchayat-months in the group: the typical monthly outflow of one "
        "Gram Panchayat, independent of how many Gram Panchayats or months the "
        "group contains.",
    ("view2", "receipt_amount_mean"):
        "rupees, AVERAGED per Gram-Panchayat-month, CASHBOOK basis -- the same "
        "figure as payment_amount_mean, for inflows.",
    ("view3", "n_plans"):
        "GPDP plans, counted (Main and Supplementary), per Gram Panchayat per "
        "year.",
    ("view3", "n_costless"):
        "activities, counted -- those planned without a cost. Recorded only "
        "from 2023-2024 onward.",
    ("view3", "n_costed"):
        "activities, counted -- those planned with a cost.",
    # The signed lines for the three status counts below are bare ("UNIT:
    # activities, COUNTED"), so each carries a name-derived clause naming the
    # status it counts. The statuses themselves are the ones status_label's own
    # definition lists. Disclosed in the WP-D4b report's decision journal.
    ("view3", "n_ongoing"):
        "activities, counted -- those whose recorded status is work ongoing.",
    ("view3", "n_abandoned"):
        "activities, counted -- those whose recorded status is work abandoned.",
    ("view3", "n_completed"):
        "activities, counted -- those whose recorded status is work completed.",
    ("view3", "n_with_evidence"):
        "activities, counted -- those with at least one geotagged photo upload.",
    ("view3", "payment_amount"):
        "rupees, totalled, CASHBOOK basis -- all outflows recorded for a Gram "
        "Panchayat in a fiscal year.",
    ("view3", "receipt_amount"):
        "rupees, totalled, CASHBOOK basis -- all inflows recorded for a Gram "
        "Panchayat in a fiscal year.",
}

DIMENSIONS = {
    "gp_name": "the Gram Panchayat, from the LGD-coded government roster. 20 of them in this sample.",
    "block_name": "the Block, from the LGD-coded government roster. 16 of them in this sample.",
    "district_name": "the District, from the LGD-coded government roster. 9 of them in this sample.",
    "fiscal_year": "the April-to-March year, written in full, for example 2024-2025. Six years run from 2020-2021 to 2025-2026.",
    "quarter": "the calendar quarter, for example 2024-Q1.",
    "month": "the calendar month, for example 2024-03.",
    "temporal_grain": "which time unit the pattern was measured over: month, quarter or fiscal year. Its three values are the three time units, not places or categories.",
    "theme": "the LSDG theme the activity's focus area maps to. 6 themes; 'Unmapped theme' means the focus area has no theme mapping on file.",
    "focus_area_name": "the plan's focus area: 30 values, such as roads, drinking water, sanitation and education.",
    "asset_category_label": "the asset the work creates. 27 named categories reach this view; 'Uncategorised' means no asset category was recorded against the work, and is not itself a kind of asset.",
    "status_label": "the activity's current recorded status. The values are Activity Approved, WORK ONGOING, WORK ABANDONED, UNDER APPROVAL and WORK COMPLETED; 'Buildings' is a known mis-coding on 13 rows.",
    "output_type_label": "the activity's output-type code. No output-type code has a description on file, so every value reads 'Code 101' through 'Code 110' -- eight codes with nothing recorded about what they contain.",
    "work_type_label": "the decoded kind of work, 4 values; 'Unknown' means the code has no decode on file.",
    "activity_type_label": "the decoded kind of activity, 2 values.",
    "activity_for_label": "the decoded purpose the activity is for, 4 values.",
    "is_costless": "whether the activity was planned with a cost ('Costed') or without one ('Costless' -- training, campaigns and services).",
    "tied_untied": "whether the sanctioned grant is Tied (earmarked, component 4249) or Untied (discretionary, components 4211 and 4250); 'Other' is any other component.",
    "sanction_authority": "the sanctioning office, cleaned of spelling variants: Sarpanch, BDO, Engineer, Gram Panchayat, Panchayat Samiti, plus ten low-count free-text residues -- 14 distinct values in all.",
    "sanctioned_scheme_name": "the scheme behind the sanction; 'Code N' means the code has no description on file.",
    "fund_component_name": "the funding component behind the sanction; 'Code N' means the code has no description on file.",
    "planned_fund_scheme_name": "the scheme behind the planned funding; 'Code N' means the code has no description on file.",
    "planned_fund_component_name": "the component behind the planned funding; 'Code N' means the code has no description on file.",

    # WPD4b: `measure` is not a data column -- it is the engine's own axis, the
    # one a measure-extending finding compares along. Ranks 16, 25, 27, 28 and 31
    # use it and the signed glossary has no line for it, because it describes no
    # column. The line below is STRUCTURAL and is AUTHORED here rather than
    # transcribed -- disclosed in the WP-D4b report. It is the same class of
    # authored structural line the accepted trial already carried for "(varies)".
    "measure": "which quantity the pattern was measured on: this finding compares the same pattern across several different measures rather than across places or time.",
}

VIEW_ROW = {
    "view1": "one row per planned activity -- 12,704 activities planned by the 20 Gram Panchayats between 2020-2021 and 2025-2026.",
    "view2": "one row per Gram Panchayat per calendar month -- 1,440 rows covering April 2020 to March 2026, months with no transactions included as zeros.",
    "view3": "one row per Gram Panchayat per fiscal year -- 120 rows, all 20 Gram Panchayats across all 6 years, including years with nothing recorded.",
}

# ---------------------------------------------------------------------------
# WP-D4c (D45): plain names for the CLEANED-TEMPLATE FALLBACK.
#
# When both writing attempts fail, the record carries a deterministic cleaned
# rendering of the engine's own sentence instead of the raw one. These are the
# translation tables that rendering uses. They are DELIBERATELY SEPARATE from
# the MEASURES / DIMENSIONS definition tables above: a definition explains what
# a variable IS, in a sentence; this is the short noun phrase that replaces the
# column name inside a sentence. Same signed source, different job.
#
# The rule for every entry: say the same thing the column name says, in words an
# officer uses. Never add a unit, a judgement, or a fact the finding did not
# state. Codes stay codes -- no output-type code has a decode on file, and
# inventing one here would be the worst possible place to do it.
# ---------------------------------------------------------------------------

# Keyed (view, measure), like MEASURES. Used as the SUBJECT of a sentence, so
# each is a noun phrase that reads correctly after "..., " and before a verb.
MEASURE_PLAIN = {
    ("view1", "overspend_vs_plan"): "spending against planned cost",
    ("view3", "overspend_vs_plan"): "spending against planned cost",
    ("view1", "overspend_vs_sanction"): "spending against the sanctioned amount",
    ("view3", "overspend_vs_sanction"): "spending against the sanctioned amount",
    ("view1", "fund_untied_total"): "planned untied funding",
    ("view1", "fund_tied_total"): "planned tied funding",
    ("view1", "fund_sanctioned_total"): "the sanctioned amount on record",
    ("view1", "total_cost"): "planned cost",
    ("view1", "total_expenditure"): "recorded spending",
    ("view1", "n_activities"): "the number of planned activities",
    ("view3", "n_activities"): "the number of planned activities",
    ("view1", "gen_amount"): "the spending recorded against the General social-category component",
    ("view1", "beneficiaries_expected"): "the number of expected beneficiaries",
    ("view1", "trainees_total"): "the number of trainees",
    ("view1", "evidence_uploads"): "the number of geotagged photo uploads",
    ("view3", "evidence_uploads"): "the number of geotagged photo uploads",
    ("view2", "activity_linked_expenditure"): "spending linked to planned activities",
    ("view2", "payment_count"): "the number of payment vouchers",
    ("view2", "payment_amount"): "total payments out",
    ("view2", "receipt_amount"): "total receipts in",
    ("view2", "receipt_count"): "the number of receipt vouchers",
    ("view2", "sanctioned_amount"): "the sanctioned amount",
    ("view2", "sanctions_count"): "the number of sanctions",
    ("view2", "payment_amount_mean"): "the average monthly payments out per Gram Panchayat",
    ("view2", "receipt_amount_mean"): "the average monthly receipts in per Gram Panchayat",
    ("view3", "sanctioned_total"): "the total sanctioned amount on record",
    ("view3", "planned_cost"): "planned cost",
    ("view3", "expenditure_total"): "recorded spending",
    ("view3", "n_admin_approvals"): "the number of administrative approvals",
    ("view3", "n_tech_approvals"): "the number of technical approvals",
    ("view3", "n_plans"): "the number of plans",
    ("view3", "n_costless"): "the number of activities planned without a cost",
    ("view3", "n_costed"): "the number of activities planned with a cost",
    ("view3", "n_ongoing"): "the number of works ongoing",
    ("view3", "n_abandoned"): "the number of works abandoned",
    ("view3", "n_completed"): "the number of completed works",
    ("view3", "n_with_evidence"): "the number of activities with photo evidence",
}

# Per dimension: the plural group noun, the singular, and the form that follows
# "over" / "across" in a time or category phrase.
DIMENSION_PLAIN = {
    "gp_name": ("Gram Panchayats", "Gram Panchayat", "Gram Panchayat"),
    "block_name": ("blocks", "block", "block"),
    "district_name": ("districts", "district", "district"),
    "fiscal_year": ("years", "year", "the years"),
    "quarter": ("quarters", "quarter", "the quarters"),
    "month": ("months", "month", "the months"),
    "temporal_grain": ("time views", "time view", "the time views"),
    "measure": ("measures", "measure", "the measures"),
    "theme": ("themes", "theme", "theme"),
    "focus_area_name": ("focus areas", "focus area", "focus area"),
    "asset_category_label": ("asset categories", "asset category", "asset category"),
    "status_label": ("recorded work statuses", "recorded work status", "recorded work status"),
    "output_type_label": ("output-type codes", "output-type code", "output-type code"),
    "work_type_label": ("kinds of work", "kind of work", "kind of work"),
    "activity_type_label": ("kinds of activity", "kind of activity", "kind of activity"),
    "activity_for_label": ("activity purposes", "activity purpose", "activity purpose"),
    "is_costless": ("costed and costless activities", "activity cost type", "activity cost type"),
    "tied_untied": ("grant types", "grant type", "grant type"),
    "sanction_authority": ("sanctioning offices", "sanctioning office", "sanctioning office"),
    "sanctioned_scheme_name": ("schemes", "scheme", "scheme"),
    "fund_component_name": ("funding components", "funding component", "funding component"),
    "planned_fund_scheme_name": ("planned schemes", "planned scheme", "planned scheme"),
    "planned_fund_component_name": ("planned funding components", "planned funding component",
                                    "planned funding component"),
}

# The three values of temporal_grain, said the way the target example says them.
TEMPORAL_GRAIN_PLAIN = {"month": "by month", "quarter": "by quarter",
                        "fiscal_year": "by year"}

# For "and five others" -- the brief's grammar fix. Beyond twelve, the digits
# read better than the word.
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
                12: "twelve"}

# ---------------------------------------------------------------------------
# Check tables.
# ---------------------------------------------------------------------------

# Keys `enrich_candidates_with_stats` attaches that are imperative PROMPT RULES,
# not figures ("LEAD WITH THE PERCENTAGE ..."). Never in a packet: WP-D4's whole
# design is that no rule constrains the writer. (Logged as a defect in the
# WP-D4 report section 5 note 3 -- `stats` mixes instructions into data.)
RULE_KEYS = {"evenness_framing", "linkage_framing", "earmark_framing",
             "reporting_caveat", "count_caveat", "linkage_note"}

# Columns carrying human-readable NAMES, for check (b)'s roster. Codes and time
# labels are excluded: they are not the "place / person / category" of that check.
NAME_COLUMNS = [
    "gp_name", "block_name", "district_name", "theme", "focus_area_name",
    "work_type_label", "activity_for_label", "activity_type_label",
    "output_type_label", "status_label", "asset_category_label",
    "asset_type_label", "tied_untied", "sanction_authority",
    "sanctioned_scheme_name", "fund_component_name",
    "planned_fund_scheme_name", "planned_fund_component_name",
    "training_category_label", "training_organiser_label",
    "community_service_label", "is_costless",
]

# Engine pattern-type enums and other raw database tokens -- check (c).
# WPD4b adds the two enums ranks 16-32 introduce: LAST_TWO and OTHER_PATTERN.
ENGINE_ENUMS = [
    "EVENNESS", "TREND", "TOP_TWO", "LAST_TWO", "OUTSTANDING_1",
    "OUTSTANDING_LAST", "ATTRIBUTION", "SEASONALITY", "NO_PATTERN",
    "OTHER_PATTERN", "TYPE_CHANGE", "HIGHLIGHT_CHANGE", "CHANGE_POINT",
    "OUTLIER", "UNIMODALITY", "INCREASING", "DECREASING", "EVEN",
]

# Detail-length tolerance for the brief's "<= ~200 words". The "~" is
# approximate; the raw count is recorded on every record regardless.
DETAIL_WORD_LIMIT = 220
LEAD_SENTENCE_LIMIT = 2

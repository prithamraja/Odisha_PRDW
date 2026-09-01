#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# Phase 5e: Insight prose for the global feed (WP-D4b)
# =============================================================================
# Productionizes the WP-D4 design accepted by the operator on 2026-08-31
# (D40 item 11, D43): a writer given NO writing rules, only the instantiated
# Appendix A context and one deterministic packet per finding, followed by a
# safety net the writer never sees -- mechanical nothing-invented checks, then a
# different-model verifier. A failure regenerates that one finding once with the
# reason fed back; a second failure falls back to the finding's current feed
# sentence, marked `fell-back` (ratified behaviour, D40 item 11).
#
# Covers ALL 32 feed findings, not the trial's 15.
#
# Inputs (read-only):
#   metainsights/global_feed.json            the 32 findings, in feed order
#   metainsights/global_feed_source_set.json the candidate_set_id
#   views_prdw/*.parquet                     via phase5b_report's enrichment
#
# Output:
#   metainsights/insight_prose.json          the sidecar (deleted before write)
#   metainsights/insight_feed.md             the sidecar rendered for Discover
#   reports_prdw/wpd4b_run/calls_<stamp>.jsonl   every call, with `usage`
#
# The feed JSON stays frozen by D16 and the sidecar is still a sidecar -- but as
# of WP-D4d this prose IS the published Discover surface: --emit-feed-md renders
# the shipped sidecar into the markdown the frontend parses, and that rendering
# is what sits in frontend/ab-dashboard-main/src/data/insights/. Emitted, never
# hand-written, so the page cannot drift from the checked artifact.
#
# Run (one command, from anywhere):
#   python Insights/src/phase5e_insight_prose.py
#   python Insights/src/phase5e_insight_prose.py --dry-run   # no API calls
#   python Insights/src/phase5e_insight_prose.py --emit-feed-md --no-reading-notes
#                                                            # no API calls
#
# This file EDITS NO EXISTING PIPELINE FILE. It imports from phase5b_report and
# discover_config and writes only its own sidecar and its own run log.
# =============================================================================
"""WP-D4b -- the insight-prose build step."""
import os
import re
import sys
import ast
import copy
import json
import time
import hashlib
import argparse
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import insight_prose_config as CFG


# =============================================================================
# STEP 0: environment, the one logged and capped call path
# =============================================================================
# Every call in this step goes through `Caller.call`, so the spend guard and the
# usage record cannot be bypassed by any code path -- writer, verifier, retry or
# regeneration.

class StopRun(SystemExit):
    """A precondition or guard failure. Stops the build; never caught."""


def _load_key(env_path):
    """Load the API key from Insights/.env, in place.

    Asserts the file exists first: WPD3 section 4.4's first bug was a wrong
    `.env` path where `load_dotenv` returned quietly and the key silently came
    from nowhere. The key is never printed, copied or written.
    """
    if not os.path.exists(env_path):
        raise StopRun("STOP: no .env at %s (precondition 4)" % env_path)
    from dotenv import load_dotenv
    load_dotenv(env_path)
    if not os.getenv("OPENAI_API_KEY"):
        raise StopRun("STOP: .env at %s provides no OPENAI_API_KEY" % env_path)


def count_tokens(text):
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:
        return len(text) // 4


class Caller(object):
    """Capped, logged completions. One instance per run."""

    def __init__(self, log_path, run_log_dir, dry_run=False):
        self.log_path = log_path
        self.run_log_dir = run_log_dir
        self.dry_run = dry_run
        self.calls = []
        self._client = None
        os.makedirs(run_log_dir, exist_ok=True)

    # -- the two spend counters (see insight_prose_config for why there are two)
    def calls_this_run(self):
        return len(self.calls)

    def calls_all_runs(self):
        n = 0
        for name in sorted(os.listdir(self.run_log_dir)):
            if not (name.startswith("calls_") and name.endswith(".jsonl")):
                continue
            with open(os.path.join(self.run_log_dir, name), encoding="utf-8") as fh:
                n += sum(1 for line in fh if line.strip())
        return n

    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def call(self, model, prompt, max_completion, purpose, rank=None, attempt=None):
        if self.dry_run:
            raise StopRun("STOP: --dry-run made an API call (%s); the "
                          "deterministic stage must not need one" % purpose)

        n_run, n_all = self.calls_this_run(), self.calls_all_runs()
        if n_run >= CFG.MAX_CALLS_PER_RUN:
            raise StopRun("STOP: spend guard -- %d calls this run, per-run cap %d"
                          % (n_run, CFG.MAX_CALLS_PER_RUN))
        if n_all >= CFG.MAX_CALLS_TOTAL:
            raise StopRun("STOP: spend guard -- %d calls across all runs in %s, "
                          "WP cap %d" % (n_all, self.run_log_dir, CFG.MAX_CALLS_TOTAL))

        tok_in = count_tokens(prompt)
        if tok_in > CFG.MAX_INPUT_TOKENS:
            # Brief T2/T1: a packet overflow means the batching went wrong.
            raise StopRun("STOP: input %d tokens > %d cap (%s)"
                          % (tok_in, CFG.MAX_INPUT_TOKENS, purpose))

        t0 = time.time()
        resp = self.client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_completion,
        )
        dt = time.time() - t0

        choice = resp.choices[0]
        text = choice.message.content or ""
        u = resp.usage
        details = getattr(u, "completion_tokens_details", None)
        reasoning = getattr(details, "reasoning_tokens", None) if details else None

        rec = {
            "call_index": n_run + 1,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "purpose": purpose,
            "rank": rank,
            "attempt": attempt,
            "model": model,
            "max_completion_tokens": max_completion,
            "seconds": round(dt, 1),
            "input_tokens_estimated": tok_in,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt": prompt,
            "finish_reason": choice.finish_reason,
            "response_text": text,
            "response_chars": len(text),
            "usage": {
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
                "reasoning_tokens": reasoning,
            },
        }
        self.calls.append(rec)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def usage_totals(self):
        out = {"calls": len(self.calls), "prompt_tokens": 0,
               "completion_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}
        by_purpose = {}
        for rec in self.calls:
            u = rec["usage"]
            out["prompt_tokens"] += u["prompt_tokens"] or 0
            out["completion_tokens"] += u["completion_tokens"] or 0
            out["total_tokens"] += u["total_tokens"] or 0
            out["reasoning_tokens"] += u["reasoning_tokens"] or 0
            key = rec["purpose"].split("_")[0] if rec["purpose"].startswith("writer") \
                else rec["purpose"]
            b = by_purpose.setdefault(key, {"calls": 0, "prompt_tokens": 0,
                                            "completion_tokens": 0,
                                            "reasoning_tokens": 0,
                                            "model": rec["model"]})
            b["calls"] += 1
            b["prompt_tokens"] += u["prompt_tokens"] or 0
            b["completion_tokens"] += u["completion_tokens"] or 0
            b["reasoning_tokens"] += u["reasoning_tokens"] or 0
        out["by_purpose"] = dict(sorted(by_purpose.items()))
        return out


# =============================================================================
# STEP 1 (T1): deterministic finding packets
# =============================================================================
# A packet is STRUCTURE, FIGURES and DEFINITIONS, and nothing else. No caution
# layer, no scope note, nothing interpretive (D40 item 9).
#
#   structure   the current feed sentence verbatim; which analysis table and
#               what one row of it is; the records in scope; which members
#               follow the pattern; each exception named with its kind in words
#   figures     computed by REUSING phase5b_report.enrich_candidates_with_stats,
#               never reinvented, carried as DISPLAY STRINGS because the checks
#               match text (no raw floats ever reach a packet)
#   definitions one line per variable the finding uses, from the signed glossary
#               -- unit, money basis, sign convention, what the values are

PROV_FEED = ("global_feed.json feed[rank] (pinned candidate set, WPD3b report "
             "section 4 hashes)")
PROV_STATS = ("computed by phase5b_report.enrich_candidates_with_stats over "
              "Insights/views_prdw/*.parquet, rebuilt from Data/ via "
              "domain_pack_prdw (calibration README step 1)")
PROV_GRAIN = ("computed by phase5b_report.enrich_candidates_with_stats on the "
              "same view, measure and filter, with the breakdown set to the "
              "fiscal-year grain this finding covers")

_PERIOD_TOKEN = re.compile(r"^PERIOD_(\d+)$")

# The time unit one step of a breakdown covers. Used only to say a repeating
# cycle's length in words instead of leaving the engine's PERIOD_<lag> token in
# a packet; `lag` is defined by phase4a_engine.evaluate_seasonality as the
# autocorrelation lag in steps of the breakdown.
_BREAKDOWN_STEP = {"month": "months", "quarter": "quarters",
                   "fiscal_year": "years"}


def _period_in_words(token, breakdown):
    m = _PERIOD_TOKEN.match(str(token))
    if not m:
        return None
    lag = m.group(1)
    unit = _BREAKDOWN_STEP.get(breakdown, "steps of the breakdown")
    return "a cycle that repeats every %s %s" % (lag, unit)


def highlight_values(raw):
    """The engine stores a highlight as the repr of a tuple. Return it as a
    list of plain strings, or [] when there is none."""
    try:
        hl = ast.literal_eval(raw) if isinstance(raw, str) else raw
    except (ValueError, SyntaxError):
        return []
    if isinstance(hl, tuple):
        return [str(x) for x in hl]
    return [str(hl)] if hl else []


def words_for_exception(exc, common_highlight, breakdown):
    """The engine's exception category, in words: opposite-direction,
    different-pattern or no-clear-pattern, plus what differs."""
    cat = exc.get("category")
    hl_vals = highlight_values(exc.get("highlight"))

    if cat == "NO_PATTERN":
        return "no clear pattern", "the engine found no clear pattern here"
    if cat == "TYPE_CHANGE":
        return "different pattern", "the engine found a different kind of pattern here"
    if cat == "HIGHLIGHT_CHANGE":
        directional = {"INCREASING", "DECREASING"}
        if hl_vals and set(hl_vals) & directional:
            common = set(common_highlight or [])
            if common & directional and not (set(hl_vals) & common):
                other = "increasing" if "INCREASING" in hl_vals else "decreasing"
                theirs = "decreasing" if "INCREASING" in hl_vals else "increasing"
                return ("opposite direction",
                        "moves in the opposite direction: %s, where most are %s"
                        % (other, theirs))
            return "different pattern", "direction here is %s" % hl_vals[0].lower()
        if hl_vals:
            # WPD4b: ranks 16-32 add seasonality exceptions whose highlight is
            # the engine's PERIOD_<lag> token. Said in words rather than left as
            # a raw database token in the packet.
            worded = [_period_in_words(v, breakdown) or v for v in hl_vals]
            return ("different pattern",
                    "a different one leads here: " + ", ".join(worded))
        return "different pattern", "the engine recorded a different highlight here"
    return "different pattern", "engine category %s" % cat


def words_for_common_highlight(hl_vals, breakdown):
    """The shared highlight, in words, for the members that follow the pattern.
    Returns None when there is nothing worth saying beyond the feed sentence."""
    if not hl_vals:
        return None
    worded = [_period_in_words(v, breakdown) for v in hl_vals]
    if any(worded):
        return ", ".join(w or v for w, v in zip(worded, hl_vals))
    return None


def flatten_figures(obj, path, out, provenance):
    """Every display string in the stats tree becomes one labelled figure.

    RULE_KEYS are dropped by name: `enrich_candidates_with_stats` mixes
    imperative prompt rules into its data, and no rule may reach this writer.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CFG.RULE_KEYS:
                continue
            flatten_figures(v, path + [str(k)], out, provenance)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_figures(v, path + [str(i)], out, provenance)
    else:
        out.append({"label": " / ".join(path), "display": str(obj),
                    "provenance": provenance})


def scope_in_words(base_subspace):
    if not base_subspace:
        return "all records in this view"
    return "; ".join("%s = %s" % (d, v) for d, v in base_subspace)


def year_forms(text):
    """Every fiscal year in BOTH display forms, so a rendering that writes
    2020-21 for a packet's 2020-2021 is not failed on formatting alone."""
    out = {}
    for y in re.findall(r"\b(\d{4})-(\d{4})\b", text):
        out["%s-%s" % (y[0], y[1])] = "%s-%s" % (y[0], y[1][2:])
    return dict(sorted(out.items()))


def measure_definition(view, measure):
    if measure == "(varies)":
        return ("this finding compares several measures at once, so it carries "
                "no single unit of its own.")
    return CFG.MEASURES.get((view, measure))


def dimension_definition(dim):
    if dim == "(varies)":
        return ("this finding compares several breakdowns at once rather than "
                "one fixed breakdown.")
    return CFG.DIMENSIONS.get(dim)


def definitions_for(row):
    """One line per variable the finding uses. Order: measure, breakdown,
    extending dimension, each filter dimension, then -- for a finding that
    compares MEASURES -- each member measure it compares.

    The last clause is a WPD4b addition. Ranks 16, 25, 27, 28 and 31 extend
    along `measure`, so the variables those findings actually use are their
    member measures; without their definitions the packet defines nothing the
    finding is about. Same signed source, same one-line rule.
    """
    view = row["view"]
    defs, seen = [], set()

    def add(name, kind, text):
        if not name or name in seen or not text:
            return
        seen.add(name)
        defs.append({"variable": name, "role": kind, "definition": text,
                     "provenance": CFG.GLOSSARY_PROVENANCE})

    add(row["measure"], "the measure", measure_definition(view, row["measure"]))
    add(row["breakdown"], "the breakdown", dimension_definition(row["breakdown"]))
    add(row["extending_dimension"], "compared across",
        dimension_definition(row["extending_dimension"]))
    for dim, _val in (row.get("base_subspace") or []):
        add(dim, "filter", dimension_definition(dim))

    if row.get("extending_dimension") == "measure":
        for name in member_measures(row):
            add(name, "one of the measures compared",
                measure_definition(view, name))
    return defs


def member_measures(row):
    """For a measure-extending finding: every measure it compares, in the
    engine's own order -- the members that follow the pattern, then the
    exceptions. Deterministic, and read straight off the feed row."""
    if row.get("extending_dimension") != "measure":
        return []
    out = []
    for cs in (row.get("commonness_sets") or []):
        for m in (cs.get("members") or []):
            if m not in out:
                out.append(str(m))
    for exc in (row.get("exceptions") or []):
        m = str(exc.get("member_label"))
        if m and m not in out:
            out.append(m)
    return out


def variables_used(row):
    """Every variable a definition is expected for -- the completeness test."""
    used = [row["measure"], row["breakdown"], row["extending_dimension"]]
    used += [d for d, _ in (row.get("base_subspace") or [])]
    used += member_measures(row)
    return [u for u in used if u]


def missing_definitions(row, defs):
    have = {d["variable"] for d in defs}
    return sorted({u for u in variables_used(row) if u not in have})


def grain_figures(p5b, row, config):
    """For a finding whose BREAKDOWN is '(varies)', the enrichment declines to
    aggregate across three different time units and returns a bare note. Rather
    than ship an empty packet, run the SAME enrichment function on the SAME
    view, measure and filter with the breakdown set to `fiscal_year` -- one of
    the three grains the finding itself covers. No new calculation: only the
    breakdown argument changes, and the packet says in words that the figures
    are that one grain's, not the finding's.

    (The accepted trial's own handling of its ranks 2 and 9 -- WP-D4 report
    journal 5. Seven of the 32 findings need it.)
    """
    probe = copy.deepcopy(row)
    probe["breakdown"] = "fiscal_year"
    probe.pop("commonness_sets", None)
    out = p5b.enrich_candidates_with_stats(row["view"], [probe], config)[0]
    stats = {k: v for k, v in (out.get("stats") or {}).items() if k != "note"}
    figures = []
    flatten_figures(stats, [], figures, PROV_GRAIN)
    return figures


# WP-D4c (D44 ruling 5). `enrich_candidates_with_stats` takes dist.head(5) and
# dist.tail(2) unconditionally, so any breakdown with 7 or fewer groups emits at
# least one group as BOTH a top value and a bottom value. WP-D4b measured it on
# 8 of the 32 findings, and on rank 21 -- 3 groups -- both "bottom" values were
# top values, making the block entirely redundant. It wastes prompt tokens and
# invites a reader, human or model, to treat one group as simultaneously highest
# and lowest.
#
# The fix is applied HERE, on the packet, not in phase5b_report: that file is
# not this WP's to edit, and its other consumers (the executive report) may want
# both lists. Nothing is recomputed -- a redundant key is dropped.
BOTTOM_VALUES_MIN_GROUPS = 8


def _drop_degenerate_bottom(stats):
    """`stats` without `note`, and without `bottom_values` when the breakdown is
    too small for a bottom to mean anything distinct from the top."""
    out = {k: v for k, v in stats.items() if k != "note"}
    n = out.get("count_breakdown_values")
    if isinstance(n, int) and n < BOTTOM_VALUES_MIN_GROUPS:
        out.pop("bottom_values", None)
    return out


def build_packets(p5b, feed):
    """One packet per feed row, all 32, in feed order."""
    by_view = {}
    for row in feed:
        by_view.setdefault(row["view"], []).append(row)

    enriched = {}
    for view, rows in sorted(by_view.items()):
        for e in p5b.enrich_candidates_with_stats(view, rows, p5b.VIEW_CONFIGS[view]):
            enriched[e["rank"]] = e

    packets = []
    for row in feed:
        e = enriched[row["rank"]]
        stats = e.get("stats", {}) or {}
        note = stats.get("note")

        figures = []
        flatten_figures(_drop_degenerate_bottom(stats), [], figures, PROV_STATS)

        grain = []
        if not figures and row["breakdown"] == "(varies)":
            grain = grain_figures(p5b, row, p5b.VIEW_CONFIGS[row["view"]])

        thin = not figures and not grain
        thin_reason = None
        if thin:
            # Brief T1 escalate clause: a finding whose figures cannot come from
            # an existing enrichment path is marked thin and the run continues.
            # Nothing is improvised to fill it.
            thin_reason = (
                "the engine compares several measures at once, so the "
                "enrichment declines to aggregate them into one figure, and "
                "this breakdown has no size or utilisation companion either"
                if row["measure"] == "(varies)" else (note or "no figures available"))

        cs = (row.get("commonness_sets") or [{}])[0]
        common_hl = highlight_values(cs.get("highlight"))

        exceptions = []
        for exc in row.get("exceptions", []):
            kind, detail = words_for_exception(exc, common_hl, row["breakdown"])
            exceptions.append({"name": exc["member_label"], "kind": kind,
                               "in_words": detail, "provenance": PROV_FEED})

        defs = definitions_for(row)

        packet = {
            "rank": row["rank"],
            "view": row["view"],
            "view_title": row["view_title"],
            "view_row": CFG.VIEW_ROW.get(row["view"]),
            "pattern_type": row["pattern_type"],
            "measure": row["measure"],
            "breakdown": row["breakdown"],
            "compared_across": row["extending_dimension"],
            "scope": scope_in_words(row["base_subspace"]),
            "feed_sentence": row["summary"],
            "feed_sentence_provenance": PROV_FEED,
            "members_following_the_pattern": [str(m) for m in cs.get("members", [])],
            "members_count": cs.get("count"),
            "members_out_of": row.get("hdp_size"),
            "shared_pattern_in_words": words_for_common_highlight(
                common_hl, row["breakdown"]),
            "exceptions": exceptions,
            "definitions": defs,
            "definitions_missing": missing_definitions(row, defs),
            "reference_figures": figures,
            "grain_figures": grain,
            "thin": thin,
            "thin_reason": thin_reason,
        }
        packet["year_forms"] = year_forms(json.dumps(packet, ensure_ascii=False))
        # D45. NOT rendered into the writer's prompt -- render_packet never
        # reads this key. It is the fallback text, and showing a writer the
        # sentence it would fall back to would bias the writing it is meant to
        # replace.
        packet["cleaned_sentence"] = cleaned_sentence(row)
        packets.append(packet)
    return packets


# =============================================================================
# STEP 1b (WP-D4c T1): the cleaned-template fallback renderer
# =============================================================================
# D45. When both writing attempts fail, the record used to carry the engine's
# RAW sentence -- accurate, and full of database language:
#
#   "Across most measure values (10/18), (varies) is evenly distributed across
#    gp_name values. Uneven only in: n_plans (not evenly spread); ..."
#
# It now carries a deterministic CLEANED rendering of that same sentence. This
# is pure code -- no model call -- so the fallback keeps the one property that
# makes it a safe last resort: it cannot be wrong about anything the engine did
# not already say.
#
# THE RULE, and it is the brief's trap: clean the WORDS, never the FACTS. Same
# counts, same members, same claim, same scope. Nothing is added -- no figure,
# no interpretation, no "so what". Codes stay codes: no output-type code has a
# decode on file and inventing one here would be the worst place to do it.
#
# The rendering is rebuilt from the finding's own FIELDS, not by regexing the
# raw sentence -- it mirrors phase5_ranking.generate_nl_summary /
# _pattern_type_to_text clause for clause, so the claim is reproduced rather
# than reinterpreted.

_SIGNED_MONEY = {"overspend_vs_plan", "overspend_vs_sanction"}

# Reader-facing cleaned prose uses the em dash, like the model-written prose it
# stands in for; the engine's raw sentences use "--".
_DASH = "—"


def _measure_subject(view, measure):
    """The measure as a sentence SUBJECT -- carrying its article where the noun
    phrase needs one ("the number of payment vouchers", but "planned cost")."""
    if measure == "(varies)":
        return "values"
    plain = CFG.MEASURE_PLAIN.get((view, measure))
    if plain:
        return plain
    # Never a raw column name, even for a measure the table has not met.
    return measure.replace("_", " ")


def _measure_bare(view, measure):
    """The same phrase without its leading article, for slots that supply their
    own ("has the highest <bare>", not "has the highest the number of ...")."""
    subj = _measure_subject(view, measure)
    return subj[4:] if subj.startswith("the ") else subj


def _plural_subject(measure):
    """`(varies)` renders as the plural subject "values", so the verbs around it
    have to agree. Everything else is a singular noun phrase."""
    return measure == "(varies)"


def _v(plural, singular_form, plural_form):
    return plural_form if plural else singular_form


def _dim_plain(dim, form=0):
    """form 0 = plural group noun, 1 = singular, 2 = the 'over/across' form."""
    if dim == "(varies)":
        return "several breakdowns"
    got = CFG.DIMENSION_PLAIN.get(dim)
    if got:
        return got[form]
    return dim.replace("_", " ")


def _member_plain(view, member, extending_dimension):
    """One HDP member, said plainly. On a measure-extending finding a member is
    a MEASURE; on a temporal_grain one it is a time view; otherwise it is a data
    value (a place, a category, a code) and is left exactly as recorded."""
    if extending_dimension == "measure":
        return _measure_subject(view, member)
    if extending_dimension == "temporal_grain":
        return CFG.TEMPORAL_GRAIN_PLAIN.get(member, member)
    return str(member)


def _join(items, conj="and"):
    items = [str(i) for i in items if str(i).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return "%s %s %s" % (items[0], conj, items[1])
    return "%s %s %s" % (", ".join(items[:-1]), conj, items[-1])


def _count_word(n):
    return CFG.NUMBER_WORDS.get(n, str(n))


def _cycle_words(token, breakdown):
    """The engine's PERIOD_<lag> highlight, in words.

    phase4a_engine.evaluate_seasonality defines lag as an autocorrelation lag in
    STEPS OF THE BREAKDOWN, so on a month breakdown 12 means twelve months. When
    the breakdown itself varies there is no one unit to name, and the honest
    phrasing says the length without claiming a unit.
    """
    m = _PERIOD_TOKEN.match(str(token))
    if not m:
        return None
    lag = m.group(1)
    unit = _BREAKDOWN_STEP.get(breakdown)
    if unit:
        return "a cycle that repeats every %s %s" % (lag, unit)
    return "a repeating %s-period cycle" % lag


def _pattern_clause(view, pattern_type, hl_vals, measure, breakdown,
                    extending_dimension, subjectless=False):
    """The engine's pattern, in plain words. Mirrors
    phase5_ranking._pattern_type_to_text clause for clause.

    `subjectless` drops the leading measure phrase, for an exception whose
    subject is the same measure the parent sentence already named.
    """
    subj = _measure_subject(view, measure)
    bare = _measure_bare(view, measure)
    plural = _plural_subject(measure)
    over = _dim_plain(breakdown, 2) if breakdown != "(varies)" else None
    grp = _dim_plain(breakdown, 0)
    one = _dim_plain(breakdown, 1)
    h0 = hl_vals[0] if hl_vals else None
    h1 = hl_vals[1] if len(hl_vals) > 1 else None

    def lead(verb_clause, participle=None):
        """With a subject, the finite verb; without one, the participle form --
        an exception reads "(rising over the years)", never "(is rising ...)"."""
        if subjectless:
            return participle if participle is not None else verb_clause
        return "%s %s" % (subj, verb_clause)

    if pattern_type == "OUTSTANDING_1":
        return "%s has the highest %s of any %s" % (h0, bare, one)
    if pattern_type == "OUTSTANDING_LAST":
        return "%s has the lowest %s of any %s" % (h0, bare, one)
    if pattern_type == "TOP_TWO":
        return "%s and %s lead on %s among the %s" % (h0, h1, subj, grp)
    if pattern_type == "LAST_TWO":
        return "%s and %s are lowest on %s among the %s" % (h0, h1, subj, grp)
    if pattern_type == "EVENNESS":
        clause = "%s spread evenly across the %s" % (_v(plural, "is", "are"), grp)
        out = lead(clause)
        if measure in _SIGNED_MONEY:
            # The engine's own signed-money wording (WP-D2c A3), kept: a
            # systemic shortfall must not read as neutral.
            out += (" %s it belongs to all of them and no single %s accounts "
                    "for it" % (_DASH, one))
        return out
    if pattern_type == "ATTRIBUTION":
        return "%s accounts for most of %s among the %s" % (h0, subj, grp)
    if pattern_type == "TREND":
        direction = {"INCREASING": "rising", "DECREASING": "falling"}.get(
            (h0 or "").upper(), (h0 or "").lower())
        tail = " over %s" % over if over else ""
        return lead("%s %s%s" % (_v(plural, "is", "are"), direction, tail),
                    participle="%s%s" % (direction, tail))
    if pattern_type == "SEASONALITY":
        worded = _cycle_words(h0, breakdown) if h0 else None
        cyc = worded or "a repeating cycle"
        return lead("%s %s" % (_v(plural, "follows", "follow"), cyc),
                    participle="following %s" % cyc)
    if pattern_type == "CHANGE_POINT":
        tail = " in %s" % over if over else ""
        return lead("%s sharply at %s%s" % (_v(plural, "shifts", "shift"), h0, tail),
                    participle="shifting sharply at %s%s" % (h0, tail))
    if pattern_type == "UNIMODALITY":
        tail = " over %s" % over if over else ""
        return lead("%s at %s%s" % (_v(plural, "peaks", "peak"), h1 or h0, tail),
                    participle="peaking at %s%s" % (h1 or h0, tail))
    if pattern_type == "OUTLIER":
        tail = " in %s" % over if over else ""
        return lead("%s an unusual value at %s%s" % (_v(plural, "has", "have"), h0, tail),
                    participle="showing an unusual value at %s%s" % (h0, tail))
    # Unknown pattern type: say the structure, never the enum.
    return lead("%s a pattern the engine does not describe in words"
                % _v(plural, "shows", "show"))


# Patterns whose highlight names a DIFFERENT member (a leader), so an exception
# reads correctly only if it keeps its subject. Everything else repeats the
# parent's own measure and is rendered subject-less.
_KEEPS_SUBJECT = {"OUTSTANDING_1", "OUTSTANDING_LAST", "TOP_TWO", "LAST_TWO",
                  "ATTRIBUTION"}


def _exception_clause(view, row, is_even):
    """The exception list, with the grammar fixed.

    The engine writes at most three and then "and N others" -- which produced
    the ungrammatical "and 1 others" on ranks 3 and 20. Here a single remainder
    is NAMED rather than counted, and a real remainder is written with a number
    word.
    """
    excs = row.get("exceptions") or []
    if not excs:
        return ""
    named, rest = (excs, []) if len(excs) <= 4 else (excs[:3], excs[3:])
    ext = row["extending_dimension"]

    descs = []
    for e in named:
        label = _member_plain(view, e.get("member_label"), ext)
        cat = e.get("category")
        if cat == "HIGHLIGHT_CHANGE":
            ptype = e.get("pattern_type")
            hl = highlight_values(e.get("highlight"))
            # On a measure-extending finding the exception IS a measure, so the
            # clause speaks about that member, not the parent's "(varies)".
            exc_measure = (e.get("member_label") if ext == "measure"
                           else row["measure"])
            clause = _pattern_clause(view, ptype, hl, exc_measure,
                                     row["breakdown"], ext,
                                     subjectless=ptype not in _KEEPS_SUBJECT)
            descs.append("%s (%s)" % (label, clause))
        elif cat == "TYPE_CHANGE":
            descs.append("%s (%s)" % (label, "a different shape of distribution"
                                      if is_even else "a different pattern"))
        elif is_even:
            # "Banking Facilities (not evenly spread)" under a heading that
            # already says "Not evenly spread in" is the engine repeating itself.
            descs.append(label)
        else:
            descs.append("%s (no clear pattern)" % label)

    tail = "; and %s others" % _count_word(len(rest)) if rest else ""
    if is_even:
        label = "Not evenly spread in"
    else:
        label = "The exception is" if (len(named) == 1 and not rest) else "The exceptions are"
    return "%s: %s%s" % (label, "; ".join(descs), tail)


def _scope_clause(base_subspace):
    """The finding's filter, in words. Values are data values and are never
    translated -- only the dimension name is."""
    if not base_subspace:
        return ""
    bits = ["%s: %s" % (_dim_plain(d, 1), v) for d, v in base_subspace]
    return " (%s)" % _join(bits)


def cleaned_sentence(row):
    """A finding's engine sentence, cleaned. Deterministic; no model involved.

    `row` is a feed row, or any dict carrying the same keys.
    """
    view = row["view"]
    cs = (row.get("commonness_sets") or [{}])[0]
    hl = highlight_values(cs.get("highlight"))
    pattern_type = cs.get("pattern_type") or row.get("pattern_type")
    is_even = pattern_type == "EVENNESS"

    count = cs.get("count")
    hdp = row.get("hdp_size")
    ext = row["extending_dimension"]
    members = [str(m) for m in (cs.get("members") or [])]
    scope = _scope_clause(row.get("base_subspace"))

    pattern = _pattern_clause(view, pattern_type, hl, row["measure"],
                              row["breakdown"], ext)

    # Coverage, and how the sentence opens. Three shapes, one per finding class,
    # chosen by which axis the engine could not fix.
    if ext == "temporal_grain":
        # The pattern holds across time views; name them -- there are only three.
        named = _join([_member_plain(view, m, ext) for m in members])
        cover = ("in all %s time views" % _count_word(hdp) if count == hdp
                 else "in %s of the %s time views" % (count, hdp))
        head = "%s %s%s" % (pattern, cover, scope)
        if named:
            head += " %s %s" % (_DASH, named)
        sentence = head[0].upper() + head[1:] + "."
    elif ext == "measure":
        cover = ("For all %s measures" % _count_word(hdp) if count == hdp
                 else "For %s of %s measures" % (count, hdp))
        sentence = "%s%s, %s." % (cover, scope, pattern)
    else:
        grp = _dim_plain(ext, 0)
        cover = ("Across every %s" % _dim_plain(ext, 1) if count == hdp
                 else "In %s of the %s %s" % (count, hdp, grp))
        sentence = "%s%s, %s." % (cover, scope, pattern)

    exc = _exception_clause(view, row, is_even)
    if exc:
        sentence += " " + exc + "."
    if is_even:
        sentence += (" This is about how totals are spread, not about how much "
                     "any one of them spends.")
    return re.sub(r"\s+", " ", sentence).strip()



# =============================================================================
# STEP 2 (T2): the prompts
# =============================================================================
# The instantiated Appendix A goes in VERBATIM. Nothing is added to it, nothing
# is paraphrased, and no writing rule of any kind is appended: the accepted
# design is that the writer is unconstrained and every safety check lives after.

OUTPUT_FORMAT = """Give your answer for each finding below, in order. Delimit each one exactly like this:

===FINDING 1===
LEAD: <the lead>
DETAIL: <the detail paragraph>
===FINDING 2===
LEAD: ...
DETAIL: ...

...and so on, one block per finding."""


def render_packet(p):
    """One finding packet, exactly as the writer and the verifier see it."""
    L = []
    L.append("===FINDING %d===" % p["rank"])
    L.append("Engine sentence: %s" % p["feed_sentence"])
    L.append("Analysis table: %s -- %s" % (p["view_title"], p["view_row"]))
    L.append("Records covered: %s" % p["scope"])

    if p.get("definitions"):
        L.append("What the variables mean:")
        for d in p["definitions"]:
            L.append("  - %s (%s): %s" % (d["variable"], d["role"], d["definition"]))

    members = p.get("members_following_the_pattern") or []
    if members:
        L.append("Follows the pattern (%s of %s): %s"
                 % (p.get("members_count"), p.get("members_out_of"),
                    ", ".join(map(str, members))))
    if p.get("shared_pattern_in_words"):
        L.append("The shared pattern, in words: %s" % p["shared_pattern_in_words"])
    if p["exceptions"]:
        L.append("Exceptions:")
        for e in p["exceptions"]:
            L.append("  - %s: %s -- %s" % (e["name"], e["kind"], e["in_words"]))
    else:
        L.append("Exceptions: none recorded.")

    if p["reference_figures"]:
        L.append("Reference figures:")
        for f in p["reference_figures"]:
            L.append("  - %s: %s" % (f["label"], f["display"]))
    elif p.get("grain_figures"):
        L.append("Reference figures. The engine cannot total this finding across "
                 "its three time units, so the figures below are for the "
                 "fiscal-year unit only, not for the finding as a whole:")
        for f in p["grain_figures"]:
            L.append("  - %s: %s" % (f["label"], f["display"]))
    else:
        L.append("Reference figures: none available for this finding.")

    if p.get("year_forms"):
        L.append("Year labels -- the same year in either form, both correct: "
                 + "; ".join("%s = %s" % (a, b) for a, b in p["year_forms"].items()))
    return "\n".join(L)


def build_writer_prompt(packets):
    return (CFG.CONTEXT + "\n\n" + OUTPUT_FORMAT + "\n\n"
            + "\n\n".join(render_packet(p) for p in packets))


def build_single_prompt(packet, reason):
    return (CFG.CONTEXT + "\n\n"
            + "Give your answer for this one finding only, delimited exactly "
              "like this:\n\n===FINDING %d===\nLEAD: <the lead>\nDETAIL: <the "
              "detail paragraph>\n\nA previous attempt at this finding was "
              "rejected. The reason given was:\n%s\n\n" % (packet["rank"], reason)
            + render_packet(packet))


_BLOCK = re.compile(
    r"===\s*FINDING\s*(\d+)\s*===(.*?)(?====\s*FINDING\s*\d+\s*===|\Z)", re.S | re.I)


def parse_renderings(text):
    """{rank: (lead, detail)} from the delimited writer output."""
    out = {}
    for m in _BLOCK.finditer(text or ""):
        body = m.group(2)
        lm = re.search(r"LEAD:\s*(.*?)(?=\n\s*DETAIL:|\Z)", body, re.S | re.I)
        dm = re.search(r"DETAIL:\s*(.*)", body, re.S | re.I)
        if lm and dm:
            out[int(m.group(1))] = (lm.group(1).strip(), dm.group(1).strip())
    return out


def plan_batches(packets):
    """One batch of all 32 unless the input cap would be exceeded; then split by
    view so same-view findings stay together; and if one view still will not
    fit, split that view into contiguous rank-ordered chunks that do.

    Every level is a SIZE rule. Nothing is curated by content, and the rank
    order inside a batch is the feed's own. (Decide-and-document, brief T2 /
    escalation protocol: 32 packets cannot fit one 16k prompt, and the trial's
    15 already measured 14.4k.)

    The planner aims at MAX_INPUT_TOKENS - BATCH_PLAN_MARGIN; the hard cap is
    still enforced in the call path.
    """
    target = CFG.MAX_INPUT_TOKENS - CFG.BATCH_PLAN_MARGIN

    if count_tokens(build_writer_prompt(packets)) <= target:
        return [("all%d" % len(packets), packets)]

    by_view = {}
    for p in packets:
        by_view.setdefault(p["view"], []).append(p)

    batches = []
    for view, ps in sorted(by_view.items()):
        if count_tokens(build_writer_prompt(ps)) <= target:
            batches.append((view, ps))
            continue
        # Split into the fewest EQUAL-SIZED contiguous chunks that fit. Equal
        # rather than greedy-fill: greedy leaves a 14 + 1 tail, which spends a
        # whole call on one finding and gives the big batch no output headroom.
        # Still a pure size rule -- rank order is the feed's own and nothing is
        # chosen by content.
        n = 2
        while True:
            size = -(-len(ps) // n)
            chunks = [ps[i:i + size] for i in range(0, len(ps), size)]
            if all(count_tokens(build_writer_prompt(c)) <= target for c in chunks):
                break
            n += 1
            if n > len(ps):
                raise StopRun("STOP: a single packet exceeds the input target "
                              "(%s) -- T1 went wrong" % view)
        for i, c in enumerate(chunks, 1):
            batches.append(("%s_part%d" % (view, i), c))
    return batches


# =============================================================================
# STEP 3 (T3): mechanical nothing-invented checks
# =============================================================================
# Four checks per finding, over lead and detail together:
#   (a) every numeral appears verbatim in that finding's packet or the context
#   (b) every place / person / category name appears in that finding's packet
#   (c) no raw database token
#   (d) shape: lead <= 2 sentences, detail <= ~200 words -- and non-empty
#
# NO STYLE CHECKS. Whether the prose reads well or took the angle you would have
# taken is the operator's call at the gate, not code's.
#
# Normalization is deliberately TIGHT. Numerals are compared as whole TOKENS
# against the token set of the finding's own packet plus the context, so "893"
# cannot match inside "6,893" and commas are never stripped ("5,196" never
# matches "51.96"). The one allowed variant is a dropped trailing ".0".

_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_PERIOD_ANY = re.compile(r"PERIOD_\d+")
_VARIES = "(varies)"
_NUM = re.compile(r"\d{4}-\d{2,4}|\d+(?:[.,]\d+)*")


def numerals(text):
    return _NUM.findall(text)


def _num_variants(tok):
    """The value, plus the formatting-only variants that are the SAME claim.

    WP-D4c (D44 ruling 2): a dropped trailing ".0" or ".00" is formatting --
    "Rs 14.00 lakh" and "Rs 14 lakh" are one number, and WP-D4b measured the
    ".00" case as a false positive that cost a regeneration. Rounding is still
    NOT allowed: 48.3 -> 48 changes the claim, and commas are never stripped, so
    "5,196" can never match "51.96".
    """
    out = {tok}
    for suffix in (".0", ".00"):
        if tok.endswith(suffix) and set(tok[:-len(suffix)]) - set("-"):
            out.add(tok[:-len(suffix)])
    return out


def build_name_roster(p5b):
    """Every human-readable place / category name in the three views.

    Generic proper-noun detection false-positives on "March", "Odisha" and
    "Gram Panchayat"; a roster asks the precise question. Rebuilt every run and
    shipped inside the sidecar, so check (b) replays without the parquet views.
    """
    import pandas as pd
    roster = set()
    for cfg in p5b.VIEW_CONFIGS.values():
        df = pd.read_parquet(cfg.parquet_path)
        for c in CFG.NAME_COLUMNS:
            if c in df.columns:
                for v in df[c].dropna().unique():
                    s = str(v).strip()
                    if s and not s.isdigit():
                        roster.add(s)
    return sorted(roster)


def _sentences(text):
    """Sentence split that does not break on the '.' inside 'Rs 1.24 crore'."""
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", protected) if p.strip()]
    return [p.replace("\x00", ".") for p in parts]


def check_finding(packet, lead, detail, roster):
    packet_text = render_packet(packet)
    allowed_text = packet_text + "\n" + CFG.CONTEXT
    allowed_nums = set()
    for t in numerals(allowed_text):
        allowed_nums |= _num_variants(t)

    body = (lead + "\n" + detail).strip()
    results = {}

    # (a) every numeral traces to the packet or the instantiated context
    bad_nums = []
    for t in numerals(body):
        if not (_num_variants(t) & allowed_nums):
            bad_nums.append(t)
    results["a_numerals"] = {"pass": not bad_nums,
                             "unsupported": sorted(set(bad_nums)),
                             "checked": len(numerals(body))}

    # (b) every roster name used must be in THIS finding's packet
    bad_names = []
    packet_lower = packet_text.lower()
    for name in roster:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", body):
            # WP-D4c (D44 ruling 2): case-insensitive containment. WP-D4b flagged
            # "Tied" -- a `tied_untied` value that is also an ordinary adjective,
            # and the packet's own definition of fund_tied_total contains it in
            # lower case. A name the packet already carries is not an invention.
            if name not in packet_text and name.lower() not in packet_lower:
                bad_names.append(name)
    results["b_names"] = {"pass": not bad_names, "not_in_packet": sorted(bad_names)}

    # (c) no raw database token
    hits = list(_SNAKE.findall(body)) + _PERIOD_ANY.findall(body)
    if _VARIES in body.lower():
        hits.append(_VARIES)
    for enum in CFG.ENGINE_ENUMS:
        if re.search(r"\b" + enum + r"\b", body):
            hits.append(enum)
    results["c_db_tokens"] = {"pass": not hits, "tokens": sorted(set(hits))}

    # (d) shape. WPD4b tightens the EMPTY end: the trial's version passed an
    # empty rendering on all four checks (0 numerals, 0 names, 0 tokens, 0
    # words), which matters here because 32 findings arrive across several
    # batches and a batch can drop a rank. A missing rendering is a check
    # failure, not a silent pass.
    n_sent = len(_sentences(lead))
    n_words = len(detail.split())
    results["d_shape"] = {
        "pass": (1 <= n_sent <= CFG.LEAD_SENTENCE_LIMIT
                 and 1 <= n_words <= CFG.DETAIL_WORD_LIMIT),
        "lead_sentences": n_sent,
        "detail_words": n_words,
    }

    results["all_pass"] = all(v["pass"] for k, v in results.items() if k != "all_pass")
    return results


def failure_reason(res):
    """Plain-English reason, fed back on the single regeneration."""
    bits = []
    if not res["a_numerals"]["pass"]:
        bits.append("It used numbers that were not in the reference figures or "
                    "the context: " + ", ".join(res["a_numerals"]["unsupported"])
                    + ". Use only figures that were given to you, exactly as written.")
    if not res["b_names"]["pass"]:
        bits.append("It named places or categories that do not belong to this "
                    "finding: " + ", ".join(res["b_names"]["not_in_packet"])
                    + ". Only name the ones listed for this finding.")
    if not res["c_db_tokens"]["pass"]:
        bits.append("It contained raw database wording: "
                    + ", ".join(res["c_db_tokens"]["tokens"])
                    + ". Write it the way an official would say it.")
    if not res["d_shape"]["pass"]:
        d = res["d_shape"]
        if d["lead_sentences"] == 0 or d["detail_words"] == 0:
            bits.append("Nothing usable came back for this finding: write both "
                        "the lead and the detail paragraph.")
        else:
            bits.append("Length: the lead ran to %d sentences (at most 2) and "
                        "the detail to %d words (at most about 200)."
                        % (d["lead_sentences"], d["detail_words"]))
    return " ".join(bits)


# =============================================================================
# STEP 4 (T4): the AI verifier
# =============================================================================
# A DIFFERENT model from the writer, seeing the packet, the instantiated context
# and the rendering -- never the writing task's output format, never the code
# checks, never the other findings.
#
# The question is split, as round 1 measured it had to be. FACTUAL CLAIMS must
# each be supported and are judged strictly. SUGGESTED ACTIONS and review
# questions are judged for consistency only: they must not assert new facts and
# must not contradict the sources, but they need no source that recommends them,
# because the context itself asks for them.
#
# A vague verdict is a fail-to-verify, never a pass. A pass without a complete
# claim mapping is a fail-to-verify too -- the rubber-stamp guard.

VERIFIER_TEMPLATE = """You are checking one short piece of writing against the source material it was written from. You are not judging its style, its tone, or the order it makes its points in. You are judging one thing only: whether it is supported.

SOURCE MATERIAL 1 -- the finding, its variable definitions and its reference figures:
{packet}

SOURCE MATERIAL 2 -- the context the writer was given:
{context}

THE WRITING TO CHECK:
LEAD: {lead}
DETAIL: {detail}

Sort what the writing says into two kinds, and judge each kind by its own standard.

FACTUAL CLAIMS -- anything the writing states about the data: a number, a place, a category, a comparison, a scope, a direction, a cause, or a degree of certainty. Every factual claim must be supported by SOURCE MATERIAL 1 or 2. Judge these strictly. A figure attached to the wrong group, a scope quietly widened or narrowed, a limitation the sources state that the writing drops or weakens, a cause asserted where the sources show only a pattern -- each of those is a failure even when every digit is correct.

SUGGESTED ACTIONS AND REVIEW QUESTIONS -- what the writing proposes an official should check, ask, reconcile or look into. The writer was asked to end with what is worth checking or asking at the next review, so a suggestion is expected and is NOT an unsupported claim merely because no source recommends it. Do not fail the writing for proposing something. Judge a suggestion on consistency only: it fails if it asserts a new fact ("payments are missing", "statuses are not being updated") or if it contradicts the sources. A suggestion that asserts a fact is making that factual claim, and you check it like any other.

Then answer:
1. Does the writing make any factual claim the source material does not support?
2. Does any suggested action assert a new fact or contradict the sources?

Reply with JSON only, no other text, in exactly this shape:

{{"verdict": "pass", "claim_map": [{{"claim": "<a core factual claim from the writing, quoted>", "supported_by": "<the exact packet line or context sentence that supports it>"}}]}}

or

{{"verdict": "fail", "problems": [{{"drifted_claim": "<the unsupported, misattributed or weakened claim, quoted exactly from the writing>", "missing_or_contradicted_fact": "<what the source says instead, or what is absent from it>"}}]}}

Rules for your reply:
- If you answer "pass", claim_map must list EVERY core factual claim the writing makes, each mapped to a specific source line. A pass with an empty or partial claim_map is not acceptable.
- If anything is unclear or you cannot map a factual claim, answer "fail" and say so in missing_or_contradicted_fact. Do not guess.
"""


def build_verifier_prompt(packet, lead, detail):
    return VERIFIER_TEMPLATE.format(packet=render_packet(packet),
                                    context=CFG.CONTEXT, lead=lead, detail=detail)


def _unparseable(why, raw):
    """A verdict the judge never delivered. `retryable` is the D43 flag: this
    is the class -- and only this class -- that gets one retry at the same
    ceiling before it counts as a fail-to-verify."""
    return {"verdict": "fail_to_verify", "retryable": True, "reason_class": why,
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact": raw[:200]}]}


def parse_verdict(text):
    """Parse the verifier's JSON. Anything unparseable or vague is a
    FAIL-TO-VERIFY, never a pass."""
    raw = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    if not raw:
        return _unparseable("empty_completion",
                            "verifier returned an empty completion")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return _unparseable("no_json",
                            "verifier returned no parseable JSON: " + raw)
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        return _unparseable("bad_json",
                            "verifier JSON did not parse (%s): %s" % (e, raw))

    # Past this point the judge DID answer, so nothing below is retryable: a
    # downgrade here is a judgement about the reply, not a starved call.
    v = str(obj.get("verdict", "")).lower().strip()
    if v == "pass":
        cm = obj.get("claim_map") or []
        if not cm or not all(c.get("claim") and c.get("supported_by") for c in cm):
            return {"verdict": "fail_to_verify", "retryable": False,
                    "reason_class": "rubber_stamp", "claim_map": cm,
                    "problems": [{"drifted_claim": "(none quoted)",
                                  "missing_or_contradicted_fact":
                                  "verifier passed without a complete claim mapping"}]}
        return {"verdict": "pass", "retryable": False, "claim_map": cm}
    if v == "fail":
        probs = obj.get("problems") or []
        if not probs or not all(p.get("drifted_claim") for p in probs):
            return {"verdict": "fail_to_verify", "retryable": False,
                    "reason_class": "unquoted_fail",
                    "problems": probs or [{"drifted_claim": "(none quoted)",
                                           "missing_or_contradicted_fact":
                                           "verifier failed without quoting a claim"}]}
        return {"verdict": "fail", "retryable": False, "problems": probs}
    return {"verdict": "fail_to_verify", "retryable": False,
            "reason_class": "no_verdict",
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact":
                          "verifier gave no clear verdict: %r" % v}]}


def verifier_reason(res):
    """The reason fed back to the writer on a regeneration.

    A quoted claim is fed back as the drift it is. A fail-to-verify has no
    quoted claim, and the trial's version fed the writer the literal string
    'A reviewer flagged this claim: "(none quoted)"' -- asking it to fix
    nothing in particular (WP-D4 report section 5 note 5). This step's D43
    retry-on-empty removes most of that class; where one survives, the reason
    says plainly what happened instead of inventing a claim.
    """
    bits = []
    for p in res.get("problems", []):
        claim = p.get("drifted_claim")
        if not claim or claim == "(none quoted)":
            continue
        bits.append('A reviewer flagged this claim: "%s". The source says: %s'
                    % (claim, p.get("missing_or_contradicted_fact")))
    if not bits and res.get("verdict") == "fail_to_verify":
        bits.append("An automated reviewer could not complete its check of the "
                    "previous version, so it was not accepted. Write this "
                    "finding again from the same sources.")
    return " ".join(bits)


def run_verifier(caller, packet, lead, detail, attempt):
    """One verdict, with the D43 retry-on-empty.

    A call whose reply cannot be parsed at all is retried ONCE at the same
    ceiling before the verdict counts. Round 2 condemned a sound rendering to a
    one-off token starvation at this exact ceiling. Both calls are logged and
    both verdicts are kept on the record.
    """
    prompt = build_verifier_prompt(packet, lead, detail)
    tries = []
    res = None
    for i in range(CFG.VERIFIER_RETRY_ON_EMPTY + 1):
        rec = caller.call(CFG.VERIFIER_MODEL, prompt, CFG.VERIFIER_MAX_COMPLETION,
                          "verifier" if i == 0 else "verifier_retry_on_empty",
                          rank=packet["rank"], attempt=attempt)
        res = parse_verdict(rec["response_text"])
        tries.append({
            "try": i + 1,
            "purpose": rec["purpose"],
            "model": rec["model"],
            "finish_reason": rec["finish_reason"],
            "response_chars": rec["response_chars"],
            "usage": rec["usage"],
            "verdict": res["verdict"],
            "reason_class": res.get("reason_class"),
        })
        if not res.get("retryable"):
            break
    res["tries"] = tries
    res["retried_on_empty"] = len(tries) > 1
    return res


# =============================================================================
# STEP 5 (T2 / T5): the build
# =============================================================================

def _sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def budget_check(caller, writer_model, packets):
    """D17. These are reasoning models: reasoning tokens are drawn from the same
    completion budget as the visible answer, so a budget that looks generous can
    return an EMPTY string with finish_reason='length' and nothing failing
    loudly -- the failure that shipped an executive report with nine blank
    sections. Probe the real prompt shape at the real ceiling before the batch.
    """
    rec = caller.call(writer_model, build_writer_prompt(packets[:1]),
                      CFG.WRITER_MAX_COMPLETION, "budget_check",
                      rank=packets[0]["rank"], attempt=1)
    u = rec["usage"]
    out = {"model": rec["model"], "finish_reason": rec["finish_reason"],
           "reasoning_tokens": u["reasoning_tokens"],
           "visible_chars": rec["response_chars"],
           "completion_tokens": u["completion_tokens"],
           "ceiling": CFG.WRITER_MAX_COMPLETION,
           "headroom": CFG.WRITER_MAX_COMPLETION - u["completion_tokens"],
           "prompt_tokens": u["prompt_tokens"]}
    print("budget check: model=%s finish=%s reasoning=%s visible_chars=%d "
          "completion=%d of %d, headroom=%d"
          % (out["model"], out["finish_reason"], out["reasoning_tokens"],
             out["visible_chars"], out["completion_tokens"], out["ceiling"],
             out["headroom"]))
    if not rec["response_text"].strip():
        raise StopRun("STOP: budget check returned EMPTY prose (D17 failure mode)")
    if rec["finish_reason"] != "stop":
        raise StopRun("STOP: budget check finish_reason=%s" % rec["finish_reason"])
    return out


def verifier_budget_check(caller, packet, lead, detail):
    """D17 discipline, applied to the JUDGE (D44 ruling 5).

    The writer path has had a budget probe since D17; the verifier ceiling was a
    bare literal with nothing behind it, and in WP-D4's round 2 it starved once
    in nineteen calls -- returning zero characters after spending all 4,000
    completion tokens on reasoning, which silently downgraded a sound rendering.
    WP-D4b added a retry, which treats the symptom. This probes the real prompt
    shape at the real ceiling before the verification loop, so starvation is
    PREVENTED rather than merely retried.

    Runs after the writer pass because a verifier prompt needs a real rendering.
    """
    rec = caller.call(CFG.VERIFIER_MODEL,
                      build_verifier_prompt(packet, lead, detail),
                      CFG.VERIFIER_MAX_COMPLETION, "verifier_budget_check",
                      rank=packet["rank"], attempt=1)
    u = rec["usage"]
    out = {"model": rec["model"], "finish_reason": rec["finish_reason"],
           "reasoning_tokens": u["reasoning_tokens"],
           "visible_chars": rec["response_chars"],
           "completion_tokens": u["completion_tokens"],
           "ceiling": CFG.VERIFIER_MAX_COMPLETION,
           "headroom": CFG.VERIFIER_MAX_COMPLETION - u["completion_tokens"],
           "prompt_tokens": u["prompt_tokens"],
           "parsed_verdict": parse_verdict(rec["response_text"])["verdict"]}
    print("verifier budget check: model=%s finish=%s reasoning=%s visible_chars=%d "
          "completion=%d of %d, headroom=%d, verdict=%s"
          % (out["model"], out["finish_reason"], out["reasoning_tokens"],
             out["visible_chars"], out["completion_tokens"], out["ceiling"],
             out["headroom"], out["parsed_verdict"]))
    if not rec["response_text"].strip():
        raise StopRun("STOP: verifier budget check returned an EMPTY completion "
                      "(D17 failure mode on the judge)")
    if rec["finish_reason"] != "stop":
        raise StopRun("STOP: verifier budget check finish_reason=%s"
                      % rec["finish_reason"])
    return out


def writer_pass(caller, writer_model, packets):
    renderings, structure = {}, []
    for name, batch in plan_batches(packets):
        prompt = build_writer_prompt(batch)
        tok_in = count_tokens(prompt)
        rec = caller.call(writer_model, prompt, CFG.WRITER_MAX_COMPLETION,
                          "writer_batch_" + name, attempt=1)
        got = parse_renderings(rec["response_text"])
        want = [p["rank"] for p in batch]
        structure.append({
            "batch": name, "ranks_sent": want,
            "input_tokens_estimated": tok_in,
            "finish_reason": rec["finish_reason"],
            "usage": rec["usage"],
            "ranks_returned": sorted(got),
            "missing": [r for r in want if r not in got],
        })
        print("batch %-12s ranks %s -> got %s, finish=%s, in=%d out=%d reasoning=%s"
              % (name, want, sorted(got), rec["finish_reason"],
                 rec["usage"]["prompt_tokens"], rec["usage"]["completion_tokens"],
                 rec["usage"]["reasoning_tokens"]))
        if structure[-1]["missing"]:
            print("  WARNING: batch dropped ranks %s -- they regenerate singly"
                  % structure[-1]["missing"])
        renderings.update(got)
    return renderings, structure


def batch_plan_only(packets):
    """The deterministic half of the batch structure, for --dry-run."""
    return [{"batch": name, "ranks_sent": [p["rank"] for p in batch],
             "input_tokens_estimated": count_tokens(build_writer_prompt(batch))}
            for name, batch in plan_batches(packets)]


def build_records(caller, writer_model, packets, renderings, roster,
                  stamp, candidate_set_id):
    records = []
    for packet in packets:
        rank = packet["rank"]
        lead, detail = renderings.get(rank, ("", ""))
        record = {
            "rank": rank,
            "run_stamp": stamp,
            "candidate_set_id": candidate_set_id,
            "view": packet["view"],
            "view_title": packet["view_title"],
            "pattern_type": packet["pattern_type"],
            "measure": packet["measure"],
            "breakdown": packet["breakdown"],
            "extending_dimension": packet["compared_across"],
            "feed_sentence": packet["feed_sentence"],
            "thin_packet": packet["thin"],
            "attempts": [],
        }
        status = None
        for attempt in (1, 2):
            chk = check_finding(packet, lead, detail, roster)
            # The verifier runs whether or not the code checks passed, so the
            # two layers stay independently measurable -- short-circuiting hides
            # the overlap the quality profile is meant to report.
            ver = run_verifier(caller, packet, lead, detail, attempt)
            ok = chk["all_pass"] and ver["verdict"] == "pass"
            record["attempts"].append({"attempt": attempt, "lead": lead,
                                       "detail": detail, "checks": chk,
                                       "verifier": ver, "ok": ok})
            if ok:
                status = "first-pass" if attempt == 1 else "regenerated"
                break
            if attempt == 2:
                status = "fell-back"
                break

            reason = " ".join(x for x in [
                failure_reason(chk) if not chk["all_pass"] else "",
                verifier_reason(ver) if ver["verdict"] != "pass" else ""] if x).strip()
            record["regeneration_reason"] = reason
            rec = caller.call(writer_model, build_single_prompt(packet, reason),
                              CFG.WRITER_MAX_COMPLETION, "regenerate",
                              rank=rank, attempt=2)
            lead, detail = parse_renderings(rec["response_text"]).get(rank, ("", ""))

        if status == "fell-back":
            # Ratified fallback (D40 item 11), upgraded by D45: not the engine's
            # RAW sentence any more, but a deterministic CLEANED rendering of it.
            # Pure code, no model call, so the fallback keeps the property that
            # makes it a safe last resort -- it cannot be wrong about anything
            # the engine did not already say. No detail paragraph is invented.
            record["lead"] = packet["cleaned_sentence"]
            record["detail"] = ""
            record["fallback_text_is_cleaned_sentence"] = True
        else:
            last = record["attempts"][-1]
            record["lead"], record["detail"] = last["lead"], last["detail"]
            record["fallback_text_is_cleaned_sentence"] = False
        record["status"] = status
        record["packet"] = packet
        records.append(record)

        last = record["attempts"][-1]
        print("rank %2d: %-11s checks=%s verifier=%-14s attempts=%d%s"
              % (rank, status, "PASS" if last["checks"]["all_pass"] else "FAIL",
                 last["verifier"]["verdict"], len(record["attempts"]),
                 "  [verifier retried on empty]"
                 if any(a["verifier"].get("retried_on_empty")
                        for a in record["attempts"]) else ""))
    return records


# =============================================================================
# STEP 6 (WP-D4d T1): the feed markdown emitter
# =============================================================================
# The Discover tab renders one markdown file dropped into
# frontend/ab-dashboard-main/src/data/insights/, parsed at build time by
# src/lib/insights-report.ts. Until WP-D4d that file was a committed copy of the
# gamma 0.5 executive report. This renders THE SIDECAR into that same contract
# instead, so what an officer reads is the checked prose and cannot drift from
# it: the file is emitted, never hand-written, and the checker regenerates it
# byte-for-byte from insight_prose.json.
#
# The parser recognises two insight shapes. This uses ONE of them and invents
# none:
#
#     **<the record's lead>**
#
#     1. <the record's detail>
#
# which the parser reads back as leadline == lead and bullets == [detail]. The
# detail is NOT split into sentences: the shape does not need it, and one
# verbatim string is a stronger guarantee than n verbatim fragments. A record
# whose detail is empty -- a fallback -- renders as the leadline alone, which
# the parser reads back as an insight with no bullets.
#
# The other shape ("### " heading + paragraph) is deliberately not used. Its
# collector runs to the next "## ", "### " or "---" and silently swallows
# everything else on the way, INCLUDING a reading-note blockquote; the
# bold-leadline collector stops at the first non-numbered line, so a note that
# follows a finding is still parsed as a note. With reading notes on, only this
# shape is safe.
#
# Nothing here calls a model, and with reading notes off nothing here reads a
# parquet view either, so the default mode runs on the Drive copy.

# The one header line the checker reads back: it records the mode the file was
# emitted in, so a regeneration cannot silently use the other one.
FEED_MD_NOTES_LINE = {
    True: "*Reading notes: included, verbatim from "
          "`phase5b_report.reading_note_block`.*",
    False: "*Reading notes: omitted (`--no-reading-notes`).*",
}


def _feed_md_reject(rank, field, why):
    raise StopRun(
        "cannot emit rank %d: its %s %s. The frontend parser is the contract "
        "and this WP may not adjust it, so the emitter stops rather than write "
        "markdown that does not round-trip." % (rank, field, why))


def _check_renderable(rec):
    """Refuse to emit prose the parser would hand back changed.

    Every rule here is a property of `insights-report.ts`, not a style
    preference:

      * a leadline is ONE line -- the parser is line-based;
      * `stripOuterBold` returns the line UNCHANGED when the text inside the
        outer pair carries its own "**", so a lead containing a bold span would
        come back still wrapped in the markers it went in with;
      * `tidy` rewrites " -- " to " -- "(em dash) in leadlines and bullets, so
        text carrying the spaced double hyphen cannot survive verbatim;
      * a lead opening with "#", ">", "- " or "1. " is a different construct to
        the parser before it is ever a lead.

    None of these fires on the shipped sidecar. They exist so that "leadline ==
    the record's lead" is a structural guarantee rather than an observation
    about one file.
    """
    rank = rec["rank"]
    lead, detail = rec["lead"], rec["detail"]

    if not lead.strip():
        _feed_md_reject(rank, "lead", "is empty")
    for field, text in (("lead", lead), ("detail", detail)):
        if text != text.strip():
            _feed_md_reject(rank, field, "carries leading or trailing whitespace")
        if "\n" in text or "\r" in text:
            _feed_md_reject(rank, field, "spans more than one line")
        if " -- " in text:
            _feed_md_reject(rank, field,
                            "carries a spaced double hyphen, which the parser "
                            "rewrites to an em dash")
    if "**" in lead:
        _feed_md_reject(rank, "lead", "carries a bold span, which stops "
                                      "`stripOuterBold` unwrapping the line")
    if re.match(r"^(#|>|- |\d+\.\s)", lead):
        _feed_md_reject(rank, "lead", "opens with a markdown construct the "
                                      "parser reads before it reads a leadline")


def render_feed_markdown(sidecar, notes_by_view=None):
    """The sidecar as the markdown the Discover feed parses. Deterministic.

    `notes_by_view` is `{view: note_text}`, or None for no reading notes.
    Building a note needs the parquet views, so the caller builds it and hands
    it in -- this function reads nothing off disk and has no clock, which is
    what makes two runs byte-identical.
    """
    records = sidecar["records"]
    run = sidecar["run"]
    reading_notes = notes_by_view is not None

    # Section order is first-appearance in feed order, and findings keep feed
    # order inside their section. Both come free from walking the records once.
    order = []
    by_view = {}
    titles = {}
    for rec in records:
        view = rec["view"]
        if view not in by_view:
            by_view[view] = []
            order.append(view)
            titles[view] = rec["view_title"]
        elif titles[view] != rec["view_title"]:
            raise StopRun("view %s carries two titles in the sidecar: %r and %r"
                          % (view, titles[view], rec["view_title"]))
        by_view[view].append(rec)

    stamps = sorted({rec["run_stamp"] for rec in records})
    if len(stamps) != 1:
        raise StopRun("the sidecar carries %d run stamps: %s"
                      % (len(stamps), stamps))

    out = []
    out.append("# Odisha PR&DW Decision Aid -- the insight feed")
    out.append("")
    out.append("*Department of Panchayati Raj & Drinking Water, "
               "Government of Odisha*")
    out.append("")
    out.append("*Every finding in `metainsights/global_feed.json`, written as "
               "checked prose by the insight-prose step: one section per view, "
               "findings in feed order, %d in all.*" % len(records))
    out.append("")
    out.append("*Prose run %s from candidate set `%s`.*"
               % (stamps[0], run["candidate_set_id"]))
    out.append("")
    out.append(FEED_MD_NOTES_LINE[reading_notes])
    out.append("")
    out.append("*Generated from `metainsights/insight_prose.json` -- do not "
               "hand-edit; regenerate via `python "
               "Insights/src/phase5e_insight_prose.py --emit-feed-md%s`.*"
               % ("" if reading_notes else " --no-reading-notes"))
    out.append("")
    out.append("---")

    for view in order:
        out.append("")
        out.append("## %s" % titles[view])
        for rec in by_view[view]:
            _check_renderable(rec)
            out.append("")
            out.append("**%s**" % rec["lead"])
            if rec["detail"].strip():
                out.append("")
                out.append("1. %s" % rec["detail"])
        if reading_notes:
            note = notes_by_view.get(view, "")
            if note:
                out.append("")
                out.append(note)

    out.append("")
    return "\n".join(out)


def build_reading_notes(p5b, feed):
    """`{view: the "> **Reading note:** ..." line}` for every view that has one.

    Verbatim from phase5b's machinery, never re-worded here. The block is built
    from the ENRICHED feed rows, exactly as the executive report builds it, so
    the sentences `reading_note_block` appends off the findings -- the count
    caveat, the linkage sentence, the earmark figures, the dated-event citations
    -- are the ones this feed's own findings earn. That enrichment reads
    views_prdw/*.parquet, which is why reading notes need a mirror.
    """
    by_view = {}
    for row in feed:
        by_view.setdefault(row["view"], []).append(row)

    notes = {}
    for view, rows in sorted(by_view.items()):
        enriched = p5b.enrich_candidates_with_stats(view, rows,
                                                    p5b.VIEW_CONFIGS[view])
        block = p5b.reading_note_block(view, enriched)
        if block.strip():
            notes[view] = block.strip()
    return notes


def emit_feed_markdown(P, reading_notes):
    """--emit-feed-md. Sidecar (+ the views, if notes are on) -> insight_feed.md."""
    if not os.path.exists(P["sidecar"]):
        raise StopRun("no sidecar at %s -- there is nothing to render"
                      % P["sidecar"])
    sidecar = json.load(open(P["sidecar"], encoding="utf-8"))

    notes_by_view = None
    if reading_notes:
        if P["src"] not in sys.path:
            sys.path.insert(0, P["src"])
        import phase5b_report as p5b
        feed = json.load(open(P["feed"], encoding="utf-8"))["feed"]
        notes_by_view = build_reading_notes(p5b, feed)

    text = render_feed_markdown(sidecar, notes_by_view)

    # The sidecar's stale-suite rule, applied here too: the old rendering goes
    # before the new one is written, so a failed run cannot leave behind a file
    # that reads as current.
    if os.path.exists(P["feed_md"]):
        os.remove(P["feed_md"])
    with open(P["feed_md"], "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print("wrote %s" % P["feed_md"])
    print("  %d findings, %d sections, reading notes %s"
          % (len(sidecar["records"]),
             len({r["view"] for r in sidecar["records"]}),
             ("on (%d emitted)" % len(notes_by_view or {})) if reading_notes
             else "off"))
    print("  sidecar   sha256 %s" % _sha256_file(P["sidecar"]))
    print("  rendering sha256 %s" % _sha256_text(text))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None,
                    help="the Insights directory (default: the one holding this file)")
    ap.add_argument("--env", default=None,
                    help="path to the .env holding the API key (default: "
                         "<base>/.env). D6 runs this step in the local mirror, "
                         "but the key must never be copied there -- point this "
                         "at the Drive tree's Insights/.env and it is read in "
                         "place, never copied, printed or written")
    ap.add_argument("--dry-run", action="store_true",
                    help="build packets, roster and batch plan; make no API call")
    # WP-D4d. Rendering the shipped sidecar is not part of building one, so it
    # exits before the key is loaded and before a Caller exists -- there is no
    # code path from this flag to an API call.
    ap.add_argument("--emit-feed-md", action="store_true",
                    help="render the SHIPPED sidecar to metainsights/insight_feed.md "
                         "-- the markdown the Discover feed parses -- and exit. "
                         "Deterministic; no API call, no rebuild of the sidecar")
    ap.add_argument("--no-reading-notes", action="store_true",
                    help="--emit-feed-md only: omit each view's deterministic "
                         "reading note. With notes ON (the default) the emitter "
                         "enriches the feed rows to build them, so it needs a "
                         "mirror carrying views_prdw/*.parquet; with them off it "
                         "reads only the sidecar and runs anywhere")
    args = ap.parse_args(argv)

    P = CFG.paths(os.path.abspath(args.base) if args.base else None)
    if args.env:
        P["env"] = os.path.abspath(args.env)

    # Before the phase5b import: with reading notes off the emitter needs
    # nothing but the sidecar, and pulling in the enrichment stack to render a
    # markdown file would make the Drive copy unable to run it.
    if args.emit_feed_md:
        return emit_feed_markdown(P, reading_notes=not args.no_reading_notes)

    if P["src"] not in sys.path:
        sys.path.insert(0, P["src"])
    import phase5b_report as p5b
    from discover_config import DISCOVER_PROSE_MODEL

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    stamp_slug = stamp.replace(":", "").replace("-", "")

    feed_doc = json.load(open(P["feed"], encoding="utf-8"))
    feed = feed_doc["feed"]
    source_set = json.load(open(P["source_set"], encoding="utf-8"))
    candidate_set_id = source_set["candidate_set_id"]

    print("feed: %d findings, candidate set %s" % (len(feed), candidate_set_id))

    # ---- T1
    packets = build_packets(p5b, feed)
    roster = build_name_roster(p5b)
    thin = [p["rank"] for p in packets if p["thin"]]
    missing_defs = {p["rank"]: p["definitions_missing"]
                    for p in packets if p["definitions_missing"]}
    print("packets: %d; thin %s; roster %d names; definitions missing %s"
          % (len(packets), thin or "none", len(roster), missing_defs or "none"))

    plan = batch_plan_only(packets)
    print("batch plan: " + ", ".join("%s(%d ranks, ~%d tok)"
                                     % (b["batch"], len(b["ranks_sent"]),
                                        b["input_tokens_estimated"]) for b in plan))

    deterministic = {
        "candidate_set_id": candidate_set_id,
        "feed_sha256": _sha256_file(P["feed"]),
        "source_set_sha256": _sha256_file(P["source_set"]),
        "context": CFG.CONTEXT,
        "context_sha256": _sha256_text(CFG.CONTEXT),
        "context_slot_values": CFG.SLOT_VALUES,
        "ceilings": {"max_input_tokens": CFG.MAX_INPUT_TOKENS,
                     "writer_max_completion": CFG.WRITER_MAX_COMPLETION,
                     "verifier_max_completion": CFG.VERIFIER_MAX_COMPLETION,
                     "max_calls_per_run": CFG.MAX_CALLS_PER_RUN,
                     "max_calls_total": CFG.MAX_CALLS_TOTAL,
                     "verifier_retry_on_empty": CFG.VERIFIER_RETRY_ON_EMPTY},
        "writer_model": DISCOVER_PROSE_MODEL,
        "verifier_model": CFG.VERIFIER_MODEL,
        "batch_plan": plan,
        "name_roster": roster,
        "packets": packets,
    }

    if args.dry_run:
        out = os.path.join(P["run_log_dir"], "dry_run_%s.json" % stamp_slug)
        os.makedirs(P["run_log_dir"], exist_ok=True)
        json.dump(deterministic, open(out, "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False, sort_keys=False)
        print("\n--dry-run: wrote the deterministic stage to %s (no API call)" % out)
        return 0

    # ---- T2-T5
    _load_key(P["env"])
    caller = Caller(os.path.join(P["run_log_dir"], "calls_%s.jsonl" % stamp_slug),
                    P["run_log_dir"])
    print("spend guard: %d calls already logged in %s; WP cap %d, per-run cap %d"
          % (caller.calls_all_runs(), P["run_log_dir"], CFG.MAX_CALLS_TOTAL,
             CFG.MAX_CALLS_PER_RUN))

    budget = budget_check(caller, DISCOVER_PROSE_MODEL, packets)
    renderings, structure = writer_pass(caller, DISCOVER_PROSE_MODEL, packets)

    # D44 ruling 5: probe the judge's ceiling on a real prompt before the loop.
    probe_rank = sorted(renderings)[0] if renderings else packets[0]["rank"]
    probe_packet = next(p for p in packets if p["rank"] == probe_rank)
    probe_lead, probe_detail = renderings.get(probe_rank, ("", ""))
    verifier_budget = verifier_budget_check(caller, probe_packet, probe_lead,
                                            probe_detail)

    records = build_records(caller, DISCOVER_PROSE_MODEL, packets, renderings,
                            roster, stamp, candidate_set_id)

    payload = {
        "what_this_is":
            "Checked insight prose for every finding in global_feed.json, one "
            "record per feed rank. Produced by Insights/src/phase5e_insight_prose.py "
            "(WP-D4b) under the design accepted on 2026-08-31 (D40 item 11, D43). "
            "This is a SIDECAR: global_feed.json is frozen by D16 and nothing "
            "here is wired to any display. Where this prose appears is the "
            "queued contract-v2 conversation.",
        "run": dict(deterministic, **{
            "stamp": stamp,
            "budget_check": budget,
            "verifier_budget_check": verifier_budget,
            "batch_structure": structure,
            "usage_totals": caller.usage_totals(),
            "call_log": os.path.relpath(caller.log_path, P["base"]).replace("\\", "/"),
        }),
        "records": records,
    }

    # The stale-suite rule, in code: the previous sidecar is deleted before the
    # new one is written, so a half-written or skipped run cannot leave a stale
    # file that reads as current.
    if os.path.exists(P["sidecar"]):
        os.remove(P["sidecar"])
    json.dump(payload, open(P["sidecar"], "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    counts = {}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\nwrote %s" % P["sidecar"])
    print("status: " + ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts)))
    print("calls this run %d (WP total %d of %d); tokens %d"
          % (caller.calls_this_run(), caller.calls_all_runs(),
             CFG.MAX_CALLS_TOTAL, caller.usage_totals()["total_tokens"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

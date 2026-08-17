# =============================================================================
# Phase 5c: Generate Five Gamma-Level Reports
# =============================================================================
# Produces one markdown report per gamma value (0.1, 0.3, 0.5, 0.7, 0.9),
# each covering the top 30 ranked findings per view, using the actionable
# format (bold leadline + numbered bullets).
#
# Gamma is the actionability penalty in the conciseness formula:
#   s_reg = S + gamma * I(no_exceptions)
# Higher gamma penalises "universal" findings (those with no exceptions) and
# pushes exception-carrying findings up the ranking. Everything needed to
# recompute conciseness is stored in the candidate JSONs, so no re-mining is
# needed: these reports are a re-scoring and a re-ranking of a completed run.
#
# The view registry is DISCOVERED, not hardcoded: every VIEW<n>_CONFIG exported
# by phase4a_engine that has both a mined candidate file and a phase5b
# VIEW_DESCRIPTIONS entry is included, in view-number order. A view added to
# the engine is picked up here as soon as it has been mined.
#
# Outputs:
#   reports_prdw/gamma_0.1_report.md
#   reports_prdw/gamma_0.3_report.md
#   reports_prdw/gamma_0.5_report.md
#   reports_prdw/gamma_0.7_report.md
#   reports_prdw/gamma_0.9_report.md
#
# Run from the repo root:
#   python Insights/src/phase5c_gamma_reports.py        # the whole suite
#   python Insights/src/phase5c_gamma_reports.py 0.5    # one edition
#
# A full-suite run deletes the previous suite first, and a single-gamma run warns
# about the editions it is leaving stale: D24's all-together rule is enforced in
# main() rather than left to whoever remembers it.
# =============================================================================

import os
import re
import sys
import json
import copy
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from openai import OpenAI

import phase4a_engine
from phase2_engine import load_candidates
# WP-D3b §4.3: the ONE ranking path, imported rather than reassembled here. The
# three steps used to be spelled out below as prefilter + rank, which silently
# dropped the A2 twin merge the executive path runs -- see `merge_prefilter_rank`.
from phase5_ranking import merge_prefilter_rank
# The run identity is defined ONCE, in the feed writer, and imported here: the
# whole point of it is that the feed and the editions agree, and two
# implementations of "which candidate set is this" would eventually not.
from phase5c_global_feed import source_set_identity, identity_header_line
from phase5b_report import (
    VIEW_DESCRIPTIONS, enrich_candidates_with_stats, POPULATION_SHARE_RULE,
    # WP-D3 T0: the two session-2 framing rules travel with the stats keys they
    # name, so the gamma editions cannot describe the same findings differently
    # from the executive report.
    UTILIZATION_RULE, EARMARK_PROMPT_RULE,
    NO_METHODOLOGY_NOTE_RULE, vocabulary_rule, reading_note_block,
)
from discover_config import (
    DISCOVER_PROSE_MODEL, DISCOVER_MAX_COMPLETION_TOKENS,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The key lives in `Insights/.env`, beside the views and the reports. This read
# the REPO ROOT's `.env` until WP-D3 — an AP path, where BASE_DIR was a
# subdirectory of the repo rather than the deployment root. There is no
# repo-root `.env` in this deployment, so every edition would have failed on the
# first call with an authentication error. Same path phase5b_report uses.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# The editions land beside the executive report, not in the AP deployment's
# `reports/` — this deployment's reports directory is `reports_prdw/` and the
# operator reviews the suite next to the report it is an alternative rendering of.
REPORTS_DIR = os.path.join(BASE_DIR, "reports_prdw")

GAMMA_VALUES = [0.1, 0.3, 0.5, 0.7, 0.9]
K_PER_VIEW = 30

MODEL = DISCOVER_PROSE_MODEL

# WP-D3 T2. This was a literal 9000 sitting next to a model constant imported
# from `discover_config`, which is exactly the one-path-under-budgeted failure
# the shared constant exists to prevent: a model swap that raised the budget in
# `discover_config` would have left this path on the old number, and these are
# reasoning models whose reasoning tokens come out of the same budget as the
# visible answer. A too-small budget here does not error — it returns an empty
# string, and the edition ships hollow. See discover_config for the measurement.
MAX_COMPLETION_TOKENS = DISCOVER_MAX_COMPLETION_TOKENS

# Conciseness parameters. r and k are fixed by the paper's formulation
# (k = the three exception categories); tau is read off each view's own config.
R = 1.0
K = 3


def gammas_from_argv(argv: list) -> list:
    """The gammas to write: all of them, or the ones named on the command line.

    The suite is 45 LLM calls and about two hours, and a change to the prompt or
    to the section scaffolding usually wants checking against one edition before
    the other four are worth paying for. Naming a gamma regenerates only that
    file and leaves the rest of the suite on disk untouched.
    """
    if not argv:
        return GAMMA_VALUES

    chosen = []
    for arg in argv:
        try:
            gamma = float(arg)
        except ValueError:
            raise SystemExit(f"{arg!r} is not a gamma. Choose from {GAMMA_VALUES}.")
        if gamma not in GAMMA_VALUES:
            raise SystemExit(f"gamma={gamma} was never mined. Choose from {GAMMA_VALUES}.")
        chosen.append(gamma)
    return chosen


# =============================================================================
# VIEW REGISTRY (discovered)
# =============================================================================

_VIEW_CONFIG_RE = re.compile(r"^VIEW(\d+)_CONFIG$")


def candidates_path(view_name: str) -> str:
    return os.path.join(BASE_DIR, "metainsights", f"{view_name}_candidates.json")


def _read_head(path: str, nbytes: int = 4096) -> str:
    """The first few KB of a file, for the stale-edition check. The identity line
    is in the header, so there is no reason to read a whole report to find it."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(nbytes)
    except OSError:
        return ""


def discover_views() -> tuple[list, list]:
    """Enumerate the reportable views from the engine, in view-number order.

    Returns (views, skipped). Each entry of `views` is
    (view_name, config, title, candidates_path). A view is skipped when it has
    no mined candidate file (it exists in the engine but the latest run did not
    cover it) or no phase5b description -- without one there is no title, no
    glossary and no units to write prose from.
    """
    found = []
    for attr in dir(phase4a_engine):
        match = _VIEW_CONFIG_RE.match(attr)
        if match:
            found.append((int(match.group(1)), f"view{match.group(1)}",
                          getattr(phase4a_engine, attr)))
    found.sort()

    views, skipped = [], []
    for _, view_name, config in found:
        path = candidates_path(view_name)
        if not os.path.exists(path):
            skipped.append((view_name, "not mined in the latest run"))
        elif view_name not in VIEW_DESCRIPTIONS:
            skipped.append((view_name, "no VIEW_DESCRIPTIONS entry in phase5b_report"))
        else:
            views.append((view_name, config, VIEW_DESCRIPTIONS[view_name]["title"], path))
    return views, skipped


# =============================================================================
# RESCORE
# =============================================================================

def compute_s_star(tau: float) -> float:
    """S* upper bound (Lemma 4.1) for this view's tau, with r = 1 and k = 3."""
    tau_r = tau ** (1.0 / R)
    threshold = (1 - tau) * math.e / tau_r
    if K >= threshold:
        return -tau * math.log2(tau) - R * (1 - tau) * math.log2((1 - tau) / K)
    return (-math.log2(tau)
            + R * (K * tau_r / math.e) * math.log2(math.e / (K * tau_r)))


def rescore_candidates(candidates: list, gamma: float, s_star: float) -> list:
    """Deep-copy candidates and recompute conciseness + score with a new gamma.

    Impact is a property of the data and does not move; only the conciseness
    term does, so the whole re-ranking rides on the gamma penalty.
    """
    rescored = []
    for c in candidates:
        c2 = copy.deepcopy(c)
        n = c2.hdp_size

        alphas = [cs["proportion"] for cs in c2.commonness_sets]

        exc_cats: dict = {}
        for exc in c2.exceptions:
            exc_cats[exc["category"]] = exc_cats.get(exc["category"], 0) + 1
        betas = [count / n for count in exc_cats.values()] if n > 0 else []

        s = 0.0
        for a in alphas:
            if a > 0:
                s -= a * math.log2(a)
        for b in betas:
            if b > 0:
                s -= R * b * math.log2(b)

        has_exc = len(c2.exceptions) > 0
        s_reg = s + gamma * (0.0 if has_exc else 1.0)
        c2.conciseness = max(0.0, 1.0 - s_reg / s_star) if s_star > 0 else 1.0
        c2.score = c2.conciseness * c2.impact
        rescored.append(c2)
    return rescored


# =============================================================================
# LLM PROMPT
# =============================================================================

def build_finding_dict(candidate) -> dict:
    c = candidate if isinstance(candidate, dict) else candidate.to_dict()
    finding = {
        "pattern_type":        c["pattern_type"],
        "extending_dimension": c["extending_dimension"],
        "breakdown":           c["breakdown"],
        "measure":             c["measure"],
        "base_subspace":       c["base_subspace"],
        "hdp_size":            c["hdp_size"],
        "commonness_sets":     c["commonness_sets"],
        "exceptions":          c["exceptions"],
    }
    if "stats" in c:
        finding["stats"] = c["stats"]
    return finding


def build_prompt(view_name: str, ranked_candidates: list, gamma: float) -> str:
    view_info = VIEW_DESCRIPTIONS[view_name]
    findings_json = json.dumps(
        [build_finding_dict(c) for c in ranked_candidates],
        indent=2, default=str,
    )

    # The ranking has already done the work of the gamma setting. This only
    # tells the writer what kind of list they have been handed.
    if gamma <= 0.3:
        tone = ("broad programme patterns -- what holds across the Gram "
                "Panchayats, blocks and districts in this data")
        headline_guidance = (
            "For universal patterns (no exceptions), the headline states what holds "
            "everywhere and carries the figure that makes it matter. Where exceptions "
            "exist, name them."
        )
    elif gamma <= 0.5:
        tone = "a mix of broad programme patterns and targeted anomalies"
        headline_guidance = (
            "Balance broad patterns against exception-focused findings. Where "
            "exceptions exist, name the specific Gram Panchayats, blocks or "
            "districts."
        )
    else:
        tone = "specific anomalies and deviations -- where delivery breaks from the norm"
        headline_guidance = (
            "Focus on where the pattern breaks. The headline must name the exception "
            "and state what is different there. Universal patterns (no exceptions) are "
            "still included, framed around the figure that makes them worth knowing."
        )

    return f"""You are writing a findings section of an analytical report on Gram Panchayat development planning and spending in Odisha, India, for the Department of Panchayati Raj & Drinking Water. The data covers the Gram Panchayat Development Plan (GPDP): the works and services a Gram Panchayat plans each year, the administrative and technical sanctions that approve them, the money actually paid out of the Gram Panchayat cashbook, and the geotagged photographs recorded as evidence.

## Your Audience
An officer of the Department of Panchayati Raj & Drinking Water who takes these findings into the departmental review meeting, where district and block officials are held to account for how their Gram Panchayats plan, sanction and spend. They are non-technical -- they understand the GPDP cycle, sanctioning authority and grant components, but not data science terminology. They want to know: what did the data reveal, why does it matter for delivery, and what should they put to the district and block officials in front of them.

## Tone
This edition of the report focuses on {tone}.

## This Section: {view_info['title']}

{view_info['description']}

{view_info['audience_context']}

## Column Glossary
{json.dumps(view_info['column_glossary'], indent=2)}

## Findings (ranked by importance)

Each finding is a pattern that holds across most subgroups, with any exceptions named.
- "commonness" = the pattern holds for the majority of subgroups
- "exceptions" = the specific subgroups where it breaks
- "HIGHLIGHT_CHANGE" exception = the same kind of pattern, but a different leading value
- "TYPE_CHANGE" exception = a different pattern applies there
- "NO_PATTERN" exception = no clear pattern in that subgroup

{findings_json}

## Instructions

Write findings for ALL {len(ranked_candidates)} findings provided. Follow this exact format:

1. STRUCTURE: present each finding (or a closely related group of 2-3 findings) as:
   - A **one-line headline** in bold that tells the whole story in one sentence. The reader should understand the finding completely from that line alone.
   - **Numbered bullets** (markdown 1. 2. 3.) with 3-5 items of supporting evidence and context.

2. NUMBERS -- READ THIS BEFORE YOU WRITE ANY FIGURE:
   Every number in the 'stats' field has ALREADY been formatted for print, with its unit attached. Your job is to choose which figures to quote and to explain what they mean. It is NOT to do arithmetic.
   - Copy each formatted string VERBATIM, exactly as it appears -- the same digits, the same grouping, the same unit word. "Rs 20.25 crore" is written "Rs 20.25 crore"
   - NEVER convert between units. Do not turn rupees into lakh or crore yourself, do not turn a percentage into a fraction, do not turn a count of activities into a share. The conversion has been done
   - NEVER re-derive, add, subtract, average, or compute a percentage of your own from the figures given. If a number you want is not in the stats, do not produce it -- write around it
   - Digit grouping is Indian throughout (12,34,567 -- not 1,234,567) and it is already applied. Do not re-group anything, and keep one style across the whole section
   - Each measure's stats carry 'measure_unit' and 'how_aggregated'. Use them: a TOTALLED figure is an absolute that grows with the size of the group, an AVERAGED figure is a per-unit rate that does not. Never describe a total as though it were a rate, or a rate as though it were a total
   - Where 'rows_behind_each_average' is given, it is the number of records behind each average. If it is small, say so when you quote the average

{POPULATION_SHARE_RULE}

{UTILIZATION_RULE}

{EARMARK_PROMPT_RULE}

3. HEADLINE RULES -- one sentence, easy to grasp, and interesting enough to make the reader pause:

   a. **Tell a mini-story.** The strongest headlines set up a pattern with a figure, then name the break:
      "[subject + verb + scope with a figure] -- except [named entity], where [what is different, in 3-6 words]."
      The reader should finish the sentence curious about the exception.

   b. **No throat-clearing.** Drop dead openers like "Across the sample,", "At the district level,", "In approved records,". Start with the actual subject doing something.
      - BAD:  "Across the Gram Panchayats studied, most planned works carry no sanction record, but one block trails the rest."
      - GOOD: "Planned works reach sanction in 14 of 16 blocks -- except Kalimela, where one in twenty does."
      (Both figures above are illustrations of the SHAPE of a headline. They are invented. Never reproduce them: every figure you write must come from the stats.)

   c. **One concrete figure in the headline**, copied verbatim from the stats. Never a vague evaluation -- the figure is what makes the pattern feel real.

   d. **No vague evaluators.** Banned in headlines: *remarkably, broadly, fairly, consistently, generally, very, slightly, modestly, somewhat, important, material, notable, significant, substantial, dominated by, a small but X, an important Y*. Replace with the actual figure, or drop the word.

   e. **One main clause plus one exception clause. Maximum ~20 words.** Two main clauses is one too many -- pick the more interesting angle and let the bullets carry the rest.

   f. **Plain English over programme jargon.** Prefer "money paid out" to "total expenditure", "works planned" to "activity count", "approved on paper" to "administratively sanctioned". If a term needs decoding, give a one-word hint ("tied grant, earmarked by rule", "geotagged photo evidence").

   g. **Name at most 2 entities.** Never roll-call five Gram Panchayats. Summarise as "4 Gram Panchayats (incl. Chikilli and Kuluma)" and list the rest in the bullets.

   h. **For universal patterns (no exception), lead with the figure.** Without a contrast, the figure alone has to do the work.

   i. {headline_guidance}

4. BULLET RULES:
   - Every bullet must carry a specific figure, copied verbatim from the stats per rule 2
   - Keep each bullet to one line where possible
   - The last bullet of each group is the OPERATIONAL bullet: what the officer should do about it or ask at the next district review. Write it as an action or a question, never as an explanation of the cause

5. NEVER INVENT A CAUSE. This is the hardest rule here and the easiest to break by accident. The findings tell you WHAT is happening, WHERE, and HOW MUCH. They contain no information whatever about WHY. You must not supply one.
   - Do not write that something happened "because", "due to", "driven by", "as a result of", "reflecting", or "explained by" anything. Those are claims about causation that the analysis did not make
   - Do not reach for a plausible mechanism to tidy up a finding. Do not attribute a pattern to administrative capacity, staffing, awareness, monsoon or terrain, contractor availability, election years, or any other unstated factor
   - Where a cause matters -- and it usually does -- write it as a QUESTION FOR THE OFFICER, not as a statement. "Chikilli has 640 activities and no administrative approvals on record; is nothing being sanctioned, or is nothing being entered?" is correct. "Chikilli is not sanctioning because the block office is understaffed" is not, and neither is "likely reflecting staffing pressure"
   - Hedging does not make an invented cause acceptable. "Possibly", "may reflect", "suggests that", "appears to be driven by" are the same violation in softer words
   - A recorded zero is the sharpest case of this rule. This data cannot tell you whether nothing happened or whether nothing was entered, and those call for different action from the officer. Where a zero or a near-zero is the finding, say that both readings are open and put the question
   - The one thing you MAY state as fact is what the glossary or the section description explicitly tells you (for example, that a code has no description on file, or that sanction records cover about one activity in six). Those are established by the data build, not inferred by you

5b. {NO_METHODOLOGY_NOTE_RULE}

{vocabulary_rule(view_name, "5c")}6. LANGUAGE:
   - Write in English. Plain English, no jargon
   - NEVER print a raw code or an internal column name in the prose. Use the Column Glossary to translate every value into words: name Gram Panchayats, blocks and districts in full, give a grant component and a scheme its full name, and say "administrative sanction" or "technical sanction" rather than an approval flag's column name
   - Several dimensions in this data are UNDECODED and reach you as literal code strings -- 'Code 101', 'Code 1518', 'Code 3880'. Do not print them, and do not invent a meaning for them. If a finding rests on one, say that the category has no description on file and that the department has to supply the decode before the finding can be read
   - The unit is already inside every formatted figure. Do not add a second unit word after it, and do not strip the one that is there
   - Never print a personal name, an Aadhaar number, a bank account or any other personal identifier. One dimension, the sanctioning authority, is free text and could in principle carry one; if a value looks like a person's name rather than an office, do not print it -- say "an uncleaned sanctioning-authority value"

7. DO NOT:
   - Mention scores, conciseness, impact, gamma, HDP, extending strategies, or any other technical MetaInsight terminology
   - Invent figures that are not in the stats
   - Skip findings -- cover all {len(ranked_candidates)}. You may group 2-3 very closely related findings under one headline
"""


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main(argv: list | None = None):
    gammas = gammas_from_argv(argv or [])

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # THE STALE-EDITIONS RULE, ENFORCED HERE. D24: whatever is published always
    # regenerates together from one candidate set, and the failure the rule
    # exists to stop is a directory holding four editions from Tuesday and one
    # from Friday, with nothing on any of them saying which. So a full-suite run
    # DELETES every edition already on disk before it writes any, and a
    # single-gamma run refuses to leave a mixed set behind silently: it says
    # which editions it is about to orphan, by candidate-set id.
    identity = source_set_identity()
    if not identity["files"]:
        raise SystemExit(
            f"No candidate files in {os.path.join(BASE_DIR, 'metainsights')} — "
            "mine before generating editions."
        )
    existing = {g: os.path.join(REPORTS_DIR, f"gamma_{g}_report.md")
                for g in GAMMA_VALUES}
    if gammas == GAMMA_VALUES:
        for gamma, path in existing.items():
            if os.path.exists(path):
                os.remove(path)
                print(f"  removed the previous gamma {gamma} edition")
    else:
        orphans = [g for g, path in existing.items()
                   if g not in gammas and os.path.exists(path)
                   and identity["candidate_set_id"] not in _read_head(path)]
        if orphans:
            print("  WARNING: these editions are on disk from an EARLIER "
                  f"candidate set and are not being regenerated: {orphans}. "
                  "They are now stale relative to what this run writes. Do not "
                  "publish a mixed suite (D24) — re-run without a gamma "
                  "argument to regenerate all five.")

    print(f"Candidate set {identity['candidate_set_id']}, stamped "
          f"{identity['generated_at']} (from {identity['stamp_source']})")

    client = OpenAI()

    views, skipped = discover_views()
    if not views:
        raise SystemExit(
            "No view has both a mined candidate file and a phase5b description. "
            "Run the engine first."
        )
    print(f"Views: {', '.join(name for name, _, _, _ in views)}")
    for view_name, reason in skipped:
        print(f"  skipped {view_name}: {reason}")

    print("\nLoading candidates ...")
    raw_candidates = {}
    s_stars = {}
    for view_name, config, _, path in views:
        raw_candidates[view_name] = load_candidates(path)
        s_stars[view_name] = compute_s_star(config.tau)
        print(f"  {view_name}: {len(raw_candidates[view_name]):,} candidates "
              f"(tau={config.tau}, S*={s_stars[view_name]:.4f})")

    for gamma in gammas:
        print(f"\n{'='*60}")
        print(f"GAMMA = {gamma}")
        print(f"{'='*60}")

        # Step 1: rescore + rank. `rescore_candidates` deep-copies, so the merge
        # inside `merge_prefilter_rank` cannot leak its `merged_twins` annotation
        # back into `raw_candidates` and reach the next gamma.
        ranked = {}
        for view_name, _, _, _ in views:
            rescored = rescore_candidates(
                raw_candidates[view_name], gamma, s_stars[view_name]
            )
            ranked[view_name], n_merged, _ = merge_prefilter_rank(
                rescored, k=K_PER_VIEW, max_candidates=5000)
            n_exc = sum(1 for c in ranked[view_name] if c.exceptions)
            print(f"  {view_name}: {len(ranked[view_name])} ranked, "
                  f"{n_exc} with exceptions, {n_merged:,} twins merged (A2)")

        # Step 2: enrich with the printable figures
        print("  Enriching with stats ...")
        enriched = {}
        for view_name, config, _, _ in views:
            as_dicts = [c.to_dict() if hasattr(c, "to_dict") else c
                        for c in ranked[view_name]]
            enriched[view_name] = enrich_candidates_with_stats(
                view_name, as_dicts, config
            )

        # Step 3: write the report
        print("  Generating report ...")
        sections = [
            f"# Odisha PR&DW Decision Aid -- Findings at Gamma {gamma}\n\n"
            "*Department of Panchayati Raj & Drinking Water, Government of "
            "Odisha*\n\n"
            "*Automated MetaInsight analysis. Gamma sets how hard the ranking "
            "pushes findings that carry named exceptions above findings that hold "
            f"everywhere; this edition uses gamma = {gamma}.*\n\n"
            # Facts 6 / T3: the gamma AND the shared candidate-set identity, on
            # every edition, so a reader can see at a glance that the five
            # editions are five renderings of one run and not a mixed suite.
            f"{identity_header_line(identity)}\n\n"
            f"*This is one of {len(GAMMA_VALUES)} editions "
            f"({', '.join(str(g) for g in GAMMA_VALUES)}) generated together "
            "from that candidate set. None is designated the published edition "
            "until the operator picks one; whatever is published regenerates "
            "with the whole suite (D24).*\n\n---\n"
        ]

        for view_name, _, view_title, _ in views:
            print(f"    {view_title} ...")
            prompt = build_prompt(view_name, enriched[view_name], gamma)
            response = client.chat.completions.create(
                model=MODEL,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError(
                    f"{view_name} at gamma={gamma} returned no text "
                    f"(finish_reason={response.choices[0].finish_reason}). "
                    "Raise DISCOVER_MAX_COMPLETION_TOKENS in discover_config -- "
                    "not a literal here, or this path drifts from the others."
                )
            sections.append(f"\n## {view_title}\n\n")
            sections.append(content)
            # WP-D3: `enriched` is passed, where this used to call with the view
            # name alone. Without it the note is the view's STANDING sentences
            # only, and every per-finding deterministic caveat — the FY 2023-24
            # reporting artifact, the A6 linkage figures, the A5 event citations,
            # the A9 earmark — is silently absent from the editions while being
            # present in the executive report. Same findings, two different sets
            # of caveats, which is the failure Facts 8 names.
            sections.append(reading_note_block(view_name, enriched[view_name]))
            sections.append("\n\n---\n")

        report_path = os.path.join(REPORTS_DIR, f"gamma_{gamma}_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("".join(sections))
        print(f"  -> {report_path}")

    print(f"\nDone. Generated {len(gammas)} gamma report(s) over "
          f"{len(views)} views: gamma {', '.join(str(g) for g in gammas)}.")


if __name__ == "__main__":
    main(sys.argv[1:])

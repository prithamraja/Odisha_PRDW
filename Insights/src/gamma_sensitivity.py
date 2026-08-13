# =============================================================================
# Gamma Sensitivity Analysis
# =============================================================================
# Re-scores every MetaInsight candidate at each gamma value and compares how
# the top-15 ranked list changes per view. The operator reads this to choose
# which of the five gamma reports to work from.
#
# Gamma is the actionability penalty in the conciseness formula:
#   s_reg = S + gamma * I(no_exceptions)
# Higher gamma penalises "universal" findings (no exceptions) and boosts
# findings that name specific exceptions.
#
# No engine re-run is needed -- everything required to recompute conciseness is
# stored in the candidate JSONs. The view registry, the gamma ladder and the
# rescoring itself are shared with phase5c_gamma_reports so the sensitivity
# analysis and the reports it is read against can never drift apart.
#
# Outputs:
#   reports/gamma_sensitivity_report.md
#
# Run from Metainsights_anomalies/:
#   python src/gamma_sensitivity.py
# =============================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from openai import OpenAI

from phase2_engine import MetaInsightCandidate, load_candidates
from phase5_ranking import (
    rank_metainsights, generate_nl_summary, compute_total_use_approx,
)
from phase5c_gamma_reports import (
    GAMMA_VALUES, MODEL, compute_s_star, discover_views, rescore_candidates,
)
from discover_config import DISCOVER_MAX_COMPLETION_TOKENS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))

K_PER_VIEW = 15
BASELINE_GAMMA = GAMMA_VALUES[0]


# =============================================================================
# CANDIDATE FINGERPRINT (for diffing ranked lists)
# =============================================================================

def fingerprint(c: MetaInsightCandidate) -> str:
    """Short unique-ish key for a candidate."""
    return (f"{c.pattern_type}|{c.extending_strategy}|{c.extending_dimension}"
            f"|{c.breakdown}|{c.measure}|{c.base_subspace}")


# =============================================================================
# REPORT GENERATION
# =============================================================================

def build_structured_report(all_results: dict) -> str:
    """Build the markdown comparing the top-15 across gamma values."""
    lines = [
        "# Gamma Sensitivity Analysis",
        "",
        "*AP RTGS Decision Aid -- Department of Agriculture, "
        "Government of Andhra Pradesh*",
        "",
        "Each view's top-15 is re-ranked at every gamma value. "
        "*Universal* findings hold across every subgroup; *actionable* findings "
        "name the subgroups where the pattern breaks. Gamma is the penalty "
        "applied to a universal finding, so raising it trades coverage of the "
        "programme for findings an officer can act on district by district.",
        "",
    ]

    for view_title, gamma_data in all_results.items():
        lines += [f"## {view_title}", ""]

        lines.append("| Gamma | Universal | Actionable | TotalUse | Top Score |")
        lines.append("|-------|-----------|------------|----------|-----------|")
        for gamma, ranked in gamma_data["ranked"].items():
            n_uni = sum(1 for c in ranked if not c.exceptions)
            n_act = sum(1 for c in ranked if c.exceptions)
            tu = compute_total_use_approx(ranked)
            top = ranked[0].score if ranked else 0
            lines.append(f"| {gamma} | {n_uni} | {n_act} | {tu:.4f} | {top:.4f} |")
        lines.append("")

        for gamma, ranked in gamma_data["ranked"].items():
            lines.append(f"### gamma = {gamma}")
            lines.append("")
            for rank, c in enumerate(ranked, 1):
                tag = "[actionable]" if c.exceptions else "[universal]"
                lines.append(
                    f"{rank}. (score={c.score:.4f}) {tag} {generate_nl_summary(c)}"
                )
            lines.append("")

        baseline_fps = set(
            fingerprint(c) for c in gamma_data["ranked"][BASELINE_GAMMA]
        )
        lines.append(f"### Changes vs baseline (gamma={BASELINE_GAMMA})")
        lines.append("")
        for gamma in GAMMA_VALUES[1:]:
            ranked = gamma_data["ranked"][gamma]
            current_fps = set(fingerprint(c) for c in ranked)
            entered = current_fps - baseline_fps
            exited = baseline_fps - current_fps
            if not entered and not exited:
                lines.append(f"**gamma={gamma}**: No change from baseline.")
            else:
                lines.append(
                    f"**gamma={gamma}**: {len(entered)} entered, {len(exited)} exited"
                )
                for c in ranked:
                    if fingerprint(c) in entered:
                        tag = "[actionable]" if c.exceptions else "[universal]"
                        lines.append(f"  + {tag} {c.pattern_type} on {c.measure} "
                                     f"via {c.extending_dimension}")
                for c in gamma_data["ranked"][BASELINE_GAMMA]:
                    if fingerprint(c) in exited:
                        tag = "[actionable]" if c.exceptions else "[universal]"
                        lines.append(f"  - {tag} {c.pattern_type} on {c.measure} "
                                     f"via {c.extending_dimension}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_llm_prompt(structured_report: str) -> str:
    """Prompt for the executive summary of the sensitivity analysis."""
    ladder = ", ".join(str(g) for g in GAMMA_VALUES)
    return f"""You are writing an analytical note for the analyst tuning the actionability parameter (gamma) of the MetaInsight ranking system behind the AP RTGS Decision Aid. The system mines the farmer welfare programmes run by the Department of Agriculture, Government of Andhra Pradesh -- PM-KISAN, Agriculture input subsidy, Horticulture APMIP, Fisheries, Sericulture, MARKFED procurement and RySS Rythu Sadhikara -- across the thirteen districts of the state.

## Background

The system discovers patterns across the programme data and ranks them. Every finding is one of two kinds:
- **Universal**: the pattern holds for ALL subgroups, with no exceptions
- **Actionable**: the pattern holds for MOST subgroups but breaks in named ones worth investigating

Gamma is the penalty applied to a universal finding. At gamma={GAMMA_VALUES[0]} universal findings are barely penalised; at gamma={GAMMA_VALUES[-1]} they are penalised hard and actionable findings are pushed to the top. The reader's decision is which gamma the published report should use.

## The Data

Below is the top-15 for every view at gamma = {ladder}, with a summary table per view. "TotalUse" is the combined usefulness of the selected set after overlap between findings is deducted; it is a diagnostic, not a quality score.

{structured_report}

## Instructions

Write a concise (400-600 word) note addressing:

1. At what gamma do the rankings start to move meaningfully? Is the shift gradual or abrupt?
2. Which views are most sensitive to gamma, and which barely move? Refer to views by the section titles used above, never by internal names like "view3".
3. What kind of finding gets promoted as gamma rises, and what gets displaced?
4. Give 2-3 concrete examples of actionable findings that enter a top-15 at higher gamma -- say what each one reveals and why a programme officer would want it in front of them.
5. Recommend a gamma value or range, and say plainly what the reader gives up by choosing it.

Rules:
- Plain English, no jargon, no bullet points for the main narrative. Use ### headers for sections. Be direct and advisory
- Do NOT invent a cause for any pattern. The findings say WHAT, WHERE and HOW MUCH; they carry no information about WHY. Do not write that something happens "because", "due to", "driven by" or "reflecting" anything, and do not soften an invented cause with "may", "likely" or "suggests"
- Quote figures only as they appear above. Do no arithmetic of your own
- Internal column names (for example `total_benefit_amount`, `unpaid_share`) appear in the finding summaries above. Translate them into plain words when you quote a finding
"""


def generate_llm_summary(structured_report: str) -> str:
    """Produce the executive summary."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=DISCOVER_MAX_COMPLETION_TOKENS,
        messages=[{"role": "user", "content": build_llm_prompt(structured_report)}],
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError(
            "Executive summary returned no text "
            f"(finish_reason={response.choices[0].finish_reason})."
        )
    return content


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    views, skipped = discover_views()
    if not views:
        raise SystemExit(
            "No view has both a mined candidate file and a phase5b description. "
            "Run the engine first."
        )
    print(f"Views: {', '.join(name for name, _, _, _ in views)}")
    for view_name, reason in skipped:
        print(f"  skipped {view_name}: {reason}")

    all_results = {}
    for view_name, config, view_title, path in views:
        print(f"\nLoading {view_name} ({view_title}) ...")
        candidates = load_candidates(path)
        s_star = compute_s_star(config.tau)
        print(f"  {len(candidates):,} candidates (tau={config.tau}, S*={s_star:.4f})")

        gamma_ranked = {}
        for gamma in GAMMA_VALUES:
            rescored = rescore_candidates(candidates, gamma, s_star)
            ranked = rank_metainsights(rescored, k=K_PER_VIEW)
            gamma_ranked[gamma] = ranked
            n_act = sum(1 for c in ranked if c.exceptions)
            print(f"  gamma={gamma}: top score={ranked[0].score:.4f}, "
                  f"actionable={n_act}/{len(ranked)}")

        all_results[view_title] = {"ranked": gamma_ranked}

    print("\nBuilding report ...")
    structured_report = build_structured_report(all_results)

    print("Generating executive summary ...")
    llm_summary = generate_llm_summary(structured_report)

    final_report = (
        structured_report
        + "\n\n# Executive Summary\n\n"
        + llm_summary
    )

    output_path = os.path.join(BASE_DIR, "reports", "gamma_sensitivity_report.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_report)
    print(f"\nReport -> {output_path}")

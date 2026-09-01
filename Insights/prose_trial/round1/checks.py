#!/usr/bin/env python
"""WP-D4 T3 -- mechanical nothing-invented checks.

Four checks per finding, over lead and detail. NO STYLE CHECKS -- the brief
forbids them; whether the prose reads well is the operator's call at the gate.

The normalizations are deliberately TIGHT (brief trap: "51.96" must not match
"5,196"). Numerals are compared as whole TOKENS against the token set of the
finding's own packet plus Appendix A -- not as raw substrings, so "893" cannot
match inside "6,893" either.
"""
import os, re, sys, json
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(BASE, "Insights", "src"))
sys.path.insert(0, HERE)

from prompts import APPENDIX_A, render_packet

# Columns that carry human-readable NAMES. Codes (LGD, block_code) and time
# labels are excluded: they are not the "place/person/category" of check (b).
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
ENGINE_ENUMS = [
    "EVENNESS", "TREND", "TOP_TWO", "OUTSTANDING_1", "OUTSTANDING_LAST",
    "ATTRIBUTION", "SEASONALITY", "NO_PATTERN", "TYPE_CHANGE",
    "HIGHLIGHT_CHANGE", "CHANGE_POINT", "OUTLIER", "UNIMODALITY",
    "INCREASING", "DECREASING", "EVEN",
]

_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_PERIOD = re.compile(r"PERIOD_\d+")
_VARIES = "(varies)"

# A numeral token: a fiscal-year span, or a digit run with internal , or .
# Kept whole so grouping and decimals are part of the identity of the token.
_NUM = re.compile(r"\d{4}-\d{2,4}|\d+(?:[.,]\d+)*")


def numerals(text: str) -> list:
    return _NUM.findall(text)


def _num_variants(tok: str) -> set:
    """Exact value, plus the one formatting-only variant we allow: a trailing
    '.0' dropped (100.0 -> 100). Rounding is NOT allowed -- 48.3 -> 48 changes
    the claim -- and commas are never stripped (that is the stated trap)."""
    out = {tok}
    if tok.endswith(".0"):
        out.add(tok[:-2])
    return out


def build_name_roster() -> set:
    import phase5b_report as p5b
    roster = set()
    for cfg in p5b.VIEW_CONFIGS.values():
        df = pd.read_parquet(cfg.parquet_path)
        for c in NAME_COLUMNS:
            if c in df.columns:
                for v in df[c].dropna().unique():
                    s = str(v).strip()
                    if s and not s.isdigit():
                        roster.add(s)
    return roster


def _sentences(text: str) -> list:
    """Sentence split that does not break on the '.' inside 'Rs 1.24 crore'."""
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", protected) if p.strip()]
    return [p.replace("\x00", ".") for p in parts]


def check_finding(packet: dict, lead: str, detail: str, roster: set) -> dict:
    packet_text = render_packet(packet)
    allowed_text = packet_text + "\n" + APPENDIX_A
    allowed_nums = set()
    for t in numerals(allowed_text):
        allowed_nums |= _num_variants(t)

    body = (lead + "\n" + detail).strip()
    results = {}

    # (a) every numeral traces to the packet or Appendix A
    bad_nums = []
    for t in numerals(body):
        if not (_num_variants(t) & allowed_nums):
            bad_nums.append(t)
    results["a_numerals"] = {
        "pass": not bad_nums,
        "unsupported": sorted(set(bad_nums)),
        "checked": len(numerals(body)),
    }

    # (b) every roster name used must be in THIS finding's packet
    bad_names = []
    for name in roster:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", body):
            if name not in packet_text:
                bad_names.append(name)
    results["b_names"] = {"pass": not bad_names, "not_in_packet": sorted(bad_names)}

    # (c) no raw database token
    hits = []
    hits += [m for m in _SNAKE.findall(body)]
    hits += _PERIOD.findall(body)
    if _VARIES in body.lower():
        hits.append(_VARIES)
    for e in ENGINE_ENUMS:
        if re.search(r"\b" + e + r"\b", body):
            hits.append(e)
    results["c_db_tokens"] = {"pass": not hits, "tokens": sorted(set(hits))}

    # (d) shape: lead <= 2 sentences, detail <= ~200 words (10% tolerance)
    n_sent = len(_sentences(lead))
    n_words = len(detail.split())
    results["d_shape"] = {
        "pass": n_sent <= 2 and n_words <= 220,
        "lead_sentences": n_sent,
        "detail_words": n_words,
    }

    results["all_pass"] = all(v["pass"] for k, v in results.items() if k != "all_pass")
    return results


def failure_reason(res: dict) -> str:
    """Plain-English reason, fed back on the single regeneration (T5)."""
    bits = []
    if not res["a_numerals"]["pass"]:
        bits.append("It used numbers that were not in the reference figures or the "
                    "background: " + ", ".join(res["a_numerals"]["unsupported"])
                    + ". Use only figures that were given to you.")
    if not res["b_names"]["pass"]:
        bits.append("It named places or categories that do not belong to this finding: "
                    + ", ".join(res["b_names"]["not_in_packet"])
                    + ". Only name the ones listed for this finding.")
    if not res["c_db_tokens"]["pass"]:
        bits.append("It contained raw database wording: "
                    + ", ".join(res["c_db_tokens"]["tokens"])
                    + ". Write it the way an official would say it.")
    if not res["d_shape"]["pass"]:
        bits.append(f"Length: the lead ran to {res['d_shape']['lead_sentences']} sentences "
                    f"(at most 2) and the detail to {res['d_shape']['detail_words']} words "
                    f"(at most about 200).")
    return " ".join(bits)

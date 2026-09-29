"""Side-by-side of runs: python compare.py <tag> <tag> ...

Reads results_<tag>.jsonl + summary_<tag>.json written by bench.py.
"""
import io, json, statistics, sys
from collections import Counter
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
# Same definition as Ask/triage_replays.py
PASSING = {"hit", "partial", "clarify_as_ratified", "clarify_gold_offered", "excluded"}
WRONG = {"wrong_template", "wrong_direction", "wrong_entities", "wrong_refusal",
         "refusal_with_rows"}   # answered, but with the wrong thing

# Runs are looked up beside this script and in runs/ (where committed sets live).
DIRS = [HERE, HERE / "runs"]


def find(name):
    for d in DIRS:
        if (d / name).exists():
            return d / name
    raise SystemExit(f"{name} not found in {[str(d) for d in DIRS]}")


TAGS = sys.argv[1:] or sorted({p.stem.removeprefix("summary_")
                               for d in DIRS for p in d.glob("summary_*.json")})
R = {t: {r["n"]: r for r in map(json.loads, find(f"results_{t}.jsonl")
                                .read_text(encoding="utf-8").splitlines())} for t in TAGS}
S = {t: json.loads(find(f"summary_{t}.json").read_text(encoding="utf-8")) for t in TAGS}
LABELS = {t: S[t]["model"].split("/")[-1].removesuffix("-it")
             + (f" @{S[t]['provider_pin']}" if S[t].get("provider_pin") else "")
          for t in TAGS}
ns = [n for n in R[TAGS[0]] if all(n in R[t] for t in TAGS)]
W = 20

ok = lambda r: r["verdict"] in PASSING
bad = lambda r: r["verdict"] in WRONG


def pct(recs, test):
    recs = list(recs)
    return f"{sum(map(test, recs)) / len(recs):.1%}" if recs else "n/a"


def row(label, cells):
    print(f"{label:34}" + "".join(f"{c!s:>{W}}" for c in cells))


print(f"questions compared: {len(ns)}\n")
row("", [LABELS[t] for t in TAGS])
row("behaving correctly", [pct((R[t][n] for n in ns), ok) for t in TAGS])
row("confidently wrong answer", [pct((R[t][n] for n in ns), bad) for t in TAGS])
row("strict hit (right template)",
    [pct((R[t][n] for n in ns), lambda r: r["verdict"] == "hit") for t in TAGS])
for key in ("lang", "case_type"):
    print(f"\n by {key}:")
    for val, cnt in Counter(R[TAGS[0]][n][key] for n in ns).most_common():
        sel = [n for n in ns if R[TAGS[0]][n][key] == val]
        row(f"   {val} (n={cnt})", [pct((R[t][n] for n in sel), ok) for t in TAGS])

print("\n verdict counts:")
for v in sorted({R[t][n]["verdict"] for t in TAGS for n in ns}):
    row(f"   {v}", [sum(R[t][n]["verdict"] == v for n in ns) for t in TAGS])

print("\n speed / reliability:")
# Wall time includes any stall outside the chat calls, so the fair speed
# figure is time spent inside the model calls per question.
row("   model time per question, median",
    [f"{statistics.median(sum(c['s'] for c in R[t][n]['llm_calls']) for n in ns):.1f}s"
     for t in TAGS])
row("   questions stalled > 30 s", [sum(R[t][n]["wall_s"] > 30 for n in ns) for t in TAGS])
for label, k in (("   whole run (s)", "run_wall_s"),
                 ("   seconds per LLM call, median", "chat_call_s_median"),
                 ("   LLM calls", "chat_calls"),
                 ("   transport errors (retried)", "transport_errors"),
                 ("   empty responses", "empty_responses"),
                 ("   cut off at max_tokens", "truncated")):
    row(label, [S[t].get(k, "-") for t in TAGS])
for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
    row(f"   {k}", [f"{S[t]['usage']['totals'][k]:,}" for t in TAGS])
row("   cached input tokens",
    [f"{S[t]['usage']['totals'].get('cached_prompt_tokens', 0):,}" for t in TAGS])
row("   OpenRouter cost (USD)", [S[t]["openrouter_cost_usd"] or "-" for t in TAGS])
for t in TAGS:
    print(f"   {LABELS[t]}: providers {S[t]['providers'] or '-'}")

base = TAGS[0]
for t in TAGS[1:]:
    for a, b in ((base, t), (t, base)):
        diff = [n for n in ns if ok(R[a][n]) and not ok(R[b][n])]
        print(f"\n-- right on {LABELS[a]}, wrong on {LABELS[b]}: {len(diff)} --")
        for n in diff:
            print(f"  #{n} [{R[a][n]['lang']}] gold={R[a][n]['gold']} "
                  f"{LABELS[b]}={R[b][n]['verdict']}/{R[b][n].get('query_id')}  "
                  f"{R[a][n]['q'][:66]}")
allbad = [n for n in ns if not any(ok(R[t][n]) for t in TAGS)]
print(f"\n-- wrong on every run: {len(allbad)} --")
for n in allbad:
    print(f"  #{n} gold={R[base][n]['gold']} "
          + " ".join(f"{LABELS[t]}={R[t][n]['verdict']}/{R[t][n].get('query_id')}"
                     for t in TAGS) + f"  {R[base][n]['q'][:50]}")

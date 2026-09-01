# DiscoverChat

Conversational access to the MetaInsight findings the Discover pipeline has
already mined. **It computes nothing, mines nothing, and never writes a number
of its own.** Every sentence an officer reads about the data is
`phase5_ranking.generate_nl_summary` output, taken verbatim from the corpus; the
model writes only the prose around those sentences, and only under a safety net
that can throw its work away.

It is a **separate product from Ask** (D42 ruling 1). Ask answers questions about
the records — figures, counts, lists. DiscoverChat reports patterns the analysis
has already found. A question of Ask's kind is declined and routed, never
proxied. The one thing taken from Ask is its entity registry, read-only, so the
two products cannot disagree about what a place is called.

## The three moves

| move | what happens |
|---|---|
| **retrieve** | pool everything above the candidate floor (0.50), hand the top 100 to a **relevance judge**, and show what it keeps. A few findings render directly; a larger set gets connective prose around them. |
| **navigate** | a follow-up walks finding structure — an exception member, a shared measure, a sibling finding. No free exploration. |
| **decline** | a number-lookup routes to Ask; a *why* question gets a scope-honest reframe (D41: correlations only, no causal analysis). |

If the judge keeps nothing, the answer is *"the current analysis has nothing on
this."* The judge may only **reject** — it selects by id from the pool, cannot
reach anything below the floor, and cannot write a finding sentence — so a weak
match is still never stretched into an answer. Set `DISCOVERCHAT_USE_JUDGE=0` to
fall back to the plain 0.62 threshold path, which is also what runs when the
judge cannot be reached.

## Running it

Everything runs from the repo root, in a **local mirror** — never against the
Drive path (D6).

```bash
# 1. build the corpus (D5.0). Reads the pinned candidate files, writes three
#    new sidecars. Two consecutive builds are byte-identical apart from the
#    timestamp, because vectors are reused from the previous build by text hash.
python Insights/src/phase5d_retrieval_corpus.py

# 2. the gate (D5.2) — one command, deterministic, no model calls
python DiscoverChat/gates.py
python DiscoverChat/gates.py --live      # plus real turns through writer+verifier

# 3. the tests, by module name (this project's venvs have no pytest)
python -m unittest DiscoverChat.tests.test_retrieval DiscoverChat.tests.test_behaviour

# 4. the service
python -m uvicorn DiscoverChat.main:app --host 127.0.0.1 --port 8100
```

`GET /health`, `POST /chat`, `GET /finding/{id}`, `GET /ask-route`.

## The D5.1 experiment

The retrieval design was decided by measurement, not argument (D42 ruling 4).

```bash
python DiscoverChat/experiments/run_arms.py      # three arms, threshold sweep
python DiscoverChat/experiments/sweep_boost.py   # how heavy should the boost be
python DiscoverChat/experiments/run_judge_arm.py # arm D: the judged path
python DiscoverChat/experiments/label_sheet.py   # the operator's labelling sheet
python DiscoverChat/experiments/measure_prose.py # writer/verifier behaviour
```

Three of the six question kinds carry a gold set that is a property of the
corpus rather than of anyone's opinion, so they score automatically. The other
three need the operator's labels, and `label_sheet.py` emits them pooled across
arms so the labelling is arm-blind.

## Layout

| file | what it is |
|---|---|
| `config.py` | every knob, and the assertion that the corpus was embedded under the pin we query with |
| `corpus.py` | the corpus, read-only |
| `slots.py` | query expansion, then geography and measure slots — deterministic |
| `retrieval.py` | `score()` (threshold path) and `pool()` (candidate pool for the judge): cosine + structural boost, floor, diversity |
| `judge.py` | the relevance judge — which pooled candidates actually answer the question |
| `classifier.py` | the turn decision, rules first, logged per turn |
| `writer.py` | free writer + the WP-D4 safety net |
| `checks.py` | mechanical nothing-invented checks |
| `causal_gate.py` | the causal-verb ban (D41) |
| `verifier.py` | different-model verifier, retry-on-empty |
| `assemble.py` | the three moves; renders findings from the corpus |
| `navigate.py` | the three structural walks |
| `gates.py` | the D5.2 behaviour suite |
| `query_expansion.json`, `measure_keywords.json` | authored **data**, on the SBM-dictionary precedent — the operator grows these from query logs without a code change |

## Two things to know before changing anything

**The knobs are provisional.** `RELEVANCE_THRESHOLD`, `QUALITY_FLOOR` and the
boost weights carry the values the D5.1 experiment measured. They become
ratified numbers at the D5.3 operator gate, not before. Every one is an
environment override, so moving one for a pilot needs no code change.

**The embedding pin travels with the corpus.** Model id, dimension count and the
query instruction are pinned together and copied into
`retrieval_corpus_stamp.json`. Startup compares them and refuses to serve a
corpus embedded under a different pin — a mismatch there produces plausible
nonsense rather than an error, which is the worst failure mode available.

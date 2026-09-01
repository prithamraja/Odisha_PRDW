# WP-D5 report — findings-retrieval chatbot (v1)

**Workstream:** Discover. **Executed:** 2026-09-01, against
`handoffs/WPD5_retrieval_chatbot.md` (D41/D42). **Stages D5.0, D5.1 and D5.2
are built and their gates are green.** D5.3 is an operator gate and is prepared,
not claimed.

**Headline.** The corpus is 4,239 findings, wide by design. The retrieval design
was decided by measurement and the measurement was decisive: the enriched
retrieval text and the structural boost each earn their place, and the boost
earns it only up to a weight the experiment also pins. A fourth arm, proposed by
the operator mid-review and adopted — floor 0.50, top 100 candidates, an LLM
judge choosing among them — took the place-question hit rate from **52.9% to
91.2% with no loss of precision and no false answers**. The D5.2 behaviour suite
is 13/13 green as one command plus 4 live checks, with 43/43 unit tests beside
it. The free writer invented **0 numerals out of 11 written**, and the binding
constraint on it turned out to be the new causal-verb ban, not invention.

**Six defects were found and fixed during the work, five of them mine**, and
each is written up below where it was found rather than only in a list — they
are the most useful part of this report for whoever runs the next stage.

---

## §0 Preconditions

| # | precondition | result |
|---|---|---|
| 1 | committed tree | **PASS with the concurrency exception.** At start the only dirty path was `handoffs/WPD4b_prose_production.md`, the PM's brief for the concurrent WP. No tracked file was modified. |
| 2 | local-mirror execution (D6) | **PASS.** Everything ran in `C:\dev\odisha-d5`. Nothing was executed against the Drive path; artefacts were copied back and SHA-compared. |
| 3 | pinned candidate set intact | **PASS.** All six files match WPD3b §4 exactly, before and after. Re-verified at close (§6). |
| 4 | `Insights/.env` keys | **PASS.** `NOVITA_API_KEY` (embeddings) and `OPENAI_API_KEY` (writer/verifier/classifier) both present. Never printed, copied or written. |

**WP-D4b ran concurrently and the file sets stayed disjoint.** Their files
appeared in `git status` as expected and none was touched: `phase5e_insight_prose.py`,
`insight_prose_config.py`, `insight_prose.json`, `check_insight_prose.py`,
`wpd4b_run/`, `WPD4b_REPORT.md`.

---

## §1 D5.0 — the retrieval corpus  ·  GATE GREEN

`Insights/src/phase5d_retrieval_corpus.py` builds three new sidecars. The feed's
JSON was not touched (D16).

### 1.1 What is in it

| view | raw candidates | twin merges | **corpus** | ranked | in feed |
|---|---:|---:|---:|---:|---:|
| view1 | 5,000 | 884 | **4,116** | 15 | 15 |
| view2 | 122 | 1 | **121** | 15 | 15 |
| view3 | 2 | 0 | **2** | 2 | 2 |
| **total** | **5,124** | **885** | **4,239** | 32 | **32** |

All 32 feed rows and all 32 ranked rows matched a corpus record by
`canonical_key` — an independent check that the corpus is a superset of the
published cut rather than a parallel construction of it. The 4,116 figure
reproduces WPD2c §4.1's "4,116 after 884 twin merges" exactly.

### 1.2 The enrichment is not decoration — it is measured

**4,239 records carry only 1,775 distinct sentences.** `generate_nl_summary`
never mentions the base subspace, so eight findings about eight different slices
of the data — costed works, maintenance works, one asset category — render as
one identical string. Embedding the bare sentence gives 2,464 records a vector
another record already owns, and retrieval cannot separate what the text does
not separate.

The enriched retrieval text (sentence + view title + glossary-expanded measure +
breakdown/subspace labels + named members) yields **4,239 distinct texts from
4,239 records** — complete separation. This is asserted as a standing test
(`test_enrichment_separates_what_the_sentence_does_not`), so a future change to
the recipe that reintroduces collisions fails loudly.

**No shared domain preamble** is prepended to any vector (D42 ruling 7). The
field labels are the minimum scaffolding and are kept short.

### 1.3 The embedding pin, verified live rather than guessed

D17 discipline was applied to the embedder, and the probe mattered:

| id probed | result |
|---|---|
| `qwen/qwen3-embedding-8b` | 200, native 4,096 dims — **the pin** |
| `qwen/qwen3-embedding-0.6b` | 200, native 1,024 dims |
| `qwen/qwen3-embedding-4b` | **404 MODEL_NOT_FOUND** — it is not served on this key |
| `Qwen/Qwen3-Embedding-8B` | **404** — the id is lower-case and vendor-prefixed |

Pinned together, and copied into the stamp with a fingerprint the service
compares at startup: model `qwen/qwen3-embedding-8b`, **1,024 dims** by
Matryoshka truncation (the endpoint honours `dimensions`; probed at 1,024 and
2,048), base URL `https://api.novita.ai/openai`, and one fixed query
instruction. Documents are embedded plain. Native 4,096 dims would have made the
vector sidecar 84 MB; 1,024 makes it 17 MB.

**Two endpoint facts worth carrying forward.** The API is **not
bit-deterministic** — two calls on the same string differ by up to 1.2e-3 per
component, measured. And it publishes **50 requests per minute**; a 429 is
waited out with exponential backoff, because the alternative is a corpus quietly
missing a few hundred vectors with no symptom.

### 1.4 The gate: two consecutive builds

| artefact | build A | build B | |
|---|---|---|---|
| `retrieval_corpus.json` | `d08bae06f9f2065b` | `d08bae06f9f2065b` | **identical** |
| `retrieval_corpus.npy` | `e1158e411529e21f` | `e1158e411529e21f` | **identical** |
| `retrieval_corpus_stamp.json` | — | — | **one line differs: `generated_at`** |

Byte-identity rests on the vector cache, not on the endpoint: a rebuild
re-embeds only texts whose SHA-256 is new. `build_seconds` is a second timing
field that may differ between runs; it happened to round the same here.

> **Defect 1, mine, found by this gate and fixed.** The first attempt failed:
> 0 texts re-embedded and a different `.npy` anyway. Cause: I re-normalised
> cached vectors on every build, and float32 L2-normalisation is **not
> idempotent** — a second pass over already-unit vectors moves the last bit of
> some components. Normalisation now happens once, at the moment of embedding.

### 1.5 Geography resolves through Ask's registry, and that caught a real error

Geography travels as **LGD codes** for Gram Panchayats, resolved through Ask's
`EntityValidator` — imported, never copied (D42 risk note), and matched on codes
rather than on transliterated text (WP-4a). **466 records name a
registry-confirmed Gram Panchayat**; all 20 GPs, all 16 blocks and all 9
districts are reachable.

> **Defect 2, mine, found by inspecting the first build and fixed.** Reading the
> column a value sits under is not enough to know it is a place. An EVENNESS
> finding broken down by `gp_name` carries the highlight `('EVEN',)` — the
> engine describing a shape — and the first build put the token **`EVEN` in the
> geography of 1,125 records**. The fix has two parts, and the second is the
> important one: a closed list of the engine's shape vocabulary is excluded
> (it cannot be "every ALL-CAPS token" — `WORK ONGOING`, `BDO` and
> `5TH STATE FINANCE COMMISSION` are all genuine values), and then **every
> surviving candidate must resolve through the registry or it is dropped**.
> After the fix: 0 rejected candidates, because the shape filter removes them
> before validation. A standing test asserts no `EVEN` in any geography.

**A limitation, stated rather than hidden:** `gram_panchayat` carries
`gp_lgd_code` and no block or district code, so blocks and districts resolve to
the registry's canonical **string**, reached through the same validator and
alias table. It is not string similarity on user input, but it is not a code
either.

**A missing registry is a hard STOP,** not a degradation. Ask's own bootstrap
lesson is that a view-less adapter loads registries empty and everything
downstream passes vacuously; here that would mean a corpus that builds, embeds
and answers no own-GP question.

### 1.6 The view1 cap, as the brief asked

**view1's raw pre-cap count is 65,488 scored candidates; 5,000 were kept and
60,488 dropped at `RANKING_PREFILTER_CAP`** (WPD2c §, confirmed by WPD3 §1.1).
So the "wide" corpus is wide within the ranker's own bound and is **92.4%
truncated** relative to everything the engine scored. WPD2c's losslessness
argument holds for the *ranked* list — the prefilter would have dropped the same
candidates one step later — but it does **not** transfer to retrieval, which
shows things the ranker never would. If D5.3 turns up retrieval misses that look
cap-related, raising the cap in a future mining run is the lever.

---

## §2 D5.1 — retrieval and the experiment that decided it  ·  GATE GREEN

### 2.1 What was measured, and what needs the operator

60 questions in six kinds. Three kinds carry a gold set that is a **property of
the corpus rather than of anyone's opinion**, so they are scored automatically
and the numbers below stand on their own:

- **geo** (34 questions, all 20 GPs, 8 blocks, 6 districts) — *hit-rate*: does
  the answer contain a finding where the officer's own place is the subject in
  its own right (its slice, its highlight, or its exception), not merely one of
  twenty members following a pattern? And *place-named precision*: what share of
  what was shown names the place at all?
- **measure** (10) — what share of what was shown was actually mined on the
  measure asked about.
- **none** (5) — anything returned is a false answer.

The other three kinds — **vague** (6), **open** (3), **why** (3) — have no
mechanical right answer, and the brief is explicit that the operator labels the
full relevant set. `DiscoverChat/experiments/LABEL_SHEET.md` emits those 12
questions with candidates **pooled across all three arms and sorted by finding
id**, so the labelling is arm-blind; a sheet ordered by the hybrid arm's ranking
would collect labels that agree with the hybrid arm.

### 2.2 The three arms

Every arm calls the shipped `Retriever.score` with a different document matrix
and the boost on or off, so what was measured is the code that runs in
production, not a second implementation of it. One query vector per question is
shared across arms, so the endpoint's own 1.2e-3 noise does not enter the
comparison.

| threshold | arm | geo hit | place-named | measure prec | false answers | shown/q |
|---|---|---:|---:|---:|---:|---:|
| 0.58 | A bare | 8.8% | 90.0% | 60.0% | 0.0% | 0.6 |
| 0.58 | B enriched | 32.4% | 90.1% | 83.5% | 0.0% | 2.7 |
| 0.58 | C hybrid | **79.4%** | 99.2% | 94.8% | 40.0% | 7.3 |
| 0.60 | A bare | 5.9% | 100.0% | 50.0% | 0.0% | 0.4 |
| 0.60 | B enriched | 23.5% | 98.0% | 82.1% | 0.0% | 1.4 |
| 0.60 | C hybrid | 64.7% | 98.9% | 94.7% | 20.0% | 5.1 |
| **0.62** | A bare | 2.9% | 100.0% | 0.0% | 0.0% | 0.2 |
| **0.62** | B enriched | 14.7% | 100.0% | 78.1% | 0.0% | 0.8 |
| **0.62** | **C hybrid** | **52.9%** | **98.5%** | **94.1%** | **0.0%** | **4.0** |
| 0.65 | C hybrid | 29.4% | 100.0% | 91.8% | 0.0% | 1.9 |

**Arm A is beaten everywhere**, which is the enrichment result restated in
retrieval terms: at 0.62 the bare-sentence arm reaches a place-specific finding
for **1 of 34** place questions. **Arm C beats arm B by 3.6× on geo hit-rate at
the operating point** and does not pay for it in precision.

### 2.3 The circularity, addressed rather than ignored

Arm C boosts findings whose geography matches, and the geo gold is "findings
whose geography matches". Arm C winning the hit-rate is arithmetic, not
evidence. The evidence is in the two numbers beside it:

- **arm B does not already get there.** 14.7% at the operating point. If cosine
  on the enriched text had reached the place-specific findings on its own, D42
  says drop the boost; it does not.
- **the boost costs nothing in precision.** 98.5% of what arm C shows names the
  place, against 100.0% for arm B on a set one fifth the size. The boost is not
  flooding the answer with findings that merely mention the place.

### 2.4 How heavy should the boost be? The sweep answers, and bounds it

The obvious follow-up — 47% of place questions still get nothing place-specific,
so use a heavier boost — is answered **no**, by measurement:

| geo boost | highest safe threshold | geo hit | place-named | measure prec |
|---:|---:|---:|---:|---:|
| 0.00 | 0.56 | 41.2% | 87.0% | 94.8% |
| 0.03 | 0.59 | 47.1% | 98.5% | 94.8% |
| **0.06** | **0.62** | **52.9%** | **98.5%** | **94.1%** |
| 0.09 | 0.65 | 52.9% | 98.5% | 91.4% |
| 0.12 | 0.68 | 52.9% | 98.5% | 87.8% |
| 0.16 | — | *no safe threshold exists* | | |

The boost cannot separate a legitimate place question from an out-of-scope one
that merely names a place, because it lifts both by the same amount. The binding
case is real and is in the question set: **"Who is the current Sarpanch of
Chikilli?"** — the analysis has nothing on it, and it names a Gram Panchayat.
Every point of boost raises it in lockstep with "How is Chikilli doing?", so the
safe threshold rises with the boost and the hit-rate plateaus at 0.06. Past
0.12, measure precision degrades; past 0.16 no threshold keeps the out-of-scope
questions silent at all.

**Decision, from the numbers: keep the boost, at `GEO_BOOST = 0.06` /
`MEASURE_BOOST = 0.03`, with `RELEVANCE_THRESHOLD = 0.62`.** D42 ruling 4 is
satisfied by measurement, not by argument.

**What raises hit-rate is the classifier, not the boost.** "Who is the current
Sarpanch of Chikilli?" is a *record lookup*, and D5.2's rule layer routes it to
Ask before retrieval runs. The floor decides relevance; the classifier decides
intent. Separating those two jobs is what would let the threshold come down —
worth putting to the operator at D5.3, with the 0.60 row (64.7% hit-rate) as the
prize and the classifier as the thing that has to be trusted to earn it.

### 2.4a D5.1b — arm D: the judged path (operator proposal, adopted)

§2.4 ends by saying the classifier, not the boost, is what would let the
threshold come down. The operator proposed the sharper version of that:
**drop the floor to 0.50, take the top 100 candidates, and let an LLM decide
which of them actually answer the question.** Measured before anything was
built, then built, then measured again.

**Why a flat threshold cannot do this job.** The relevant findings for the 15
failing place questions sit at cosine **0.54–0.61** — just under the bar. The
bar cannot simply come down, because a flat floor cannot tell "How is Chikilli
doing?" from "Who is the Sarpanch of Chikilli?": both name a Gram Panchayat,
both take the same structural boost, and they land in the same band.

**Sizing it, before building.** At floor 0.50, near-duplicates collapsed first
and *then* truncated to 100, **all 34 place questions have at least one
genuinely relevant finding in the pool** (against 19 answered under the 0.62
threshold). The candidate list costs a median 8,589 tokens, max 9,826, against
the 16k input cap. Without the top-100 cut this does not fit at all: the median
question has 212 candidates above 0.50 and the worst has 1,603.

**The result, on the same 60 questions and the same mechanical gold:**

| | arm C (threshold 0.62) | **arm D (0.50 → top 100 → judged)** |
|---|---:|---:|
| geo hit rate | 52.9% | **91.2%** |
| place-named precision | 98.5% | 98.3% |
| measure precision | 94.1% | **97.1%** |
| **false-answer rate** | 0.0% | **0.0%** |
| findings shown per place question | 4.0 | 3.5 |
| judge fell back to the threshold | — | **0 of 61 turns** |
| ids invented by the judge | — | **0** |

**Selectivity was a second measured pass, not a guess.** The judge's first
version kept a median of 8 but a maximum of **74** findings, and 25 of 61
answers would have hit `ANSWER_CAP`. The prompt now says in as many words that
near-repetition over overlapping slices is not extra evidence and that the
smallest sufficient set is the goal. After that change: **median 3, max 6, and
the cap binds on nothing.** Geo hit-rate cost 2.9 points (94.1% → 91.2%) for an
answer a busy officer can actually read.

**The safety property, checked with repeats.** The floor used to reject every
out-of-scope question by arithmetic. At 0.50, four of those five reach the judge
with pools of 65, 38, 17 and 8 candidates, so **the judge is now the only guard**.
It kept nothing from any of them across **four independent runs (20
question-runs)**, and the live gate repeats it on every run.

**The judge is stricter than the mechanical gold, defensibly.** "Is spending on
track?" now returns nothing, where arm C returned 12 findings — *"they only
describe distributions or relative rankings of overspending"*. That is correct,
and arm C was quietly wrong. The two place questions arm D still misses are the
same kind of disagreement, not failures to retrieve.

**What it may not do, structurally.** The judge selects by id from the pool. It
cannot promote anything below 0.50, cannot write a finding sentence, and ids not
in the pool are dropped and counted — so **D42 ruling 5 still holds**: there is
still a floor, nothing below it is reachable, and a weak match is still never
stretched. What moved is the last step of "is this an answer?", from a
comparison to a judgement, which is the shape of that question.

**Adopted as the production path** (`USE_JUDGE` defaults on). The threshold path
remains as the fallback when the judge cannot be reached or parsed, and as what
the offline gate runs.

**Costs, stated.** Every retrieve turn now carries a ~10k-token judge call where
arm C's path was free vector arithmetic. And the `no-match-honest` guarantee
moves from an offline comparison to a live, repeated check — the offline suite
still pins it on the threshold path, but production's version of it is now
model-dependent. The four-run stability result is what justifies that; it is not
a property the code can prove on its own.

### 2.5 Presentation

The **diversity rule** collapses findings whose *displayed sentence* is
identical, keeping the best-scoring one and carrying the others' ids. It is
identity of the sentence, not vector proximity, for two reasons: the sentence is
what the reader sees, so two records sharing one are the same answer printed
twice; and a cosine-radius rule would need a radius, which is one more
unratified constant between the corpus and the officer. On "Is spending on
track?" it collapses **493** near-duplicates.

---

## §3 D5.2 — the chatbot service  ·  GATE GREEN (13/13 offline + 4 live), TESTS 43/43

`DiscoverChat/` — FastAPI, Ask's conventions, tests runnable by module name.

### 3.1 The gate, as one command

```
python DiscoverChat/gates.py          ->  13/13 checks green
python DiscoverChat/gates.py --live   ->  13/13 + 4 live checks green
python -m unittest DiscoverChat.tests.test_retrieval \
                  DiscoverChat.tests.test_behaviour  ->  Ran 43 tests  OK
```

| check | what it proves |
|---|---|
| corpus-pin | the corpus is served under the pin it was embedded with |
| corpus-deterministic-text | 4,239 sentences all in the engine's template form |
| lookup-declines | 6 lookup questions, all declined **by rule** and naming Ask |
| lookup-never-proxied | no numeral of any kind in the decline text |
| why-reframes | 6 why-questions, all reframed **by rule**, limit stated |
| no-match-honest | 4 out-of-scope questions, none answered |
| floor-not-topn | best cosine 0.490 < threshold 0.62, zero shown |
| numerals-traceable | **339 numerals across 20 answers, all traceable** |
| causal-scan | 19 answers scanned, none causal |
| causal-gate-catches | 6 causal constructions caught, 4 honest sentences passed |
| run-stamp | `as of 2026-08-17` on every answer |
| findings-verbatim | every shown sentence identical to the corpus record |
| coverage-stated | every unranked finding shown carries its coverage line |

**The default suite makes no model calls, and that is deliberate.** Routing is
nondeterministic — the bootstrap's own lesson is that identical replays flip
about 3% of questions — so a gate whose green depends on a model call goes red
for reasons nobody changed. Every behaviour the brief gates on is therefore
decided on a deterministic path: the **rule layer** routes lookups and
why-questions, the floor is a comparison, the causal scan is a word list.
`--live` runs real turns through the JUDGED path — the production one — with the
writer and verifier. It carries the check the offline suite can no longer make
on production's behalf: **out-of-scope questions stay silent**, repeated across
runs (10 runs, 0 answered). It is the pre-deploy mode, not what keeps the suite
green.

`causal-gate-catches` is there because **a gate that never fires proves
nothing**: it asserts six causal constructions are caught *and* four honest
statements of limits are not.

### 3.2 The causal-verb ban (D41)

Written in `DiscoverChat/causal_gate.py`, **not** in `Insights/src/prose_gate.py`,
which this WP may import but not edit. A negation guard lets an honest limit
through — "the analysis cannot say what causes this" is a statement of a limit,
not a claim — because a ban that fires on hedging would push the writer away
from stating exactly the limits D41 wants stated.

> **Defect 3, mine, found by my own gate and fixed by rewording.** The
> why-reframe I wrote said "not reliable enough to carry a **causal** claim",
> and the ban fired: the denial sat 66 characters back, outside the 60-character
> negation window. Widening the window would have loosened the guard for every
> real claim too, so the sentence was reworded instead — which is what the ban
> is for. The same run caught numbered list markers putting digits into answers
> that belonged to no finding; findings are now bulleted, so the
> "every numeral traces to a corpus sentence" check needs no exception carved
> into it.

### 3.3 The writer under the net — measured, not asserted

`DiscoverChat/experiments/measure_prose.py`, 8 turns, 5 of which reach the
writer:

| | |
|---|---|
| reached the writer | 5 of 8 (the other 3 had ≤4 findings and render directly) |
| **fell back to bare sentences** | **1 of 5** |
| **numerals written / invented** | **11 / 0** |
| attempts using causal wording | 3 of 9 |
| verifier verdicts | 3 pass, 1 fail-then-pass, 1 fail |

**The WP-D4 result replicates: the free writer invents nothing.** Zero numerals,
zero out-of-finding names, zero database tokens across the accepted renderings.
**The binding constraint is the new causal ban** — the writer reaches for
"driven by", "because", "therefore" unprompted, in a third of attempts. This is
the first measurement of the D41 ban against a free writer and it is the number
to watch at D5.3.

The first measurement run gave **5 fallbacks out of 5**. Diagnosing that rather
than reporting it found two defects:

> **Defect 4, mine, and the most consequential.** The verifier starved on 4 of 6
> calls: `finish_reason='length'`, all 4,000 completion tokens spent on
> reasoning, empty string returned, no error. D43's retry-on-empty fired and the
> retry starved too. The cause was not flakiness — **WP-D4's 4,000-token
> verifier ceiling was sized for one rewritten finding, and this verifier reads
> a whole answer of up to twelve findings plus the writer's context and must map
> every claim to a source line.** Raised to 9,000, with the evidence in the
> comment: the two calls that did return used 1,305 and 1,400 tokens, so the
> budget is not marginal at 9,000, it was simply wrong at 4,000. This is exactly
> the failure D17's budget note describes, in a new place — the lesson
> generalises from *model swap* to *task-size change*.

> **Defect 5, mine.** The "no name that isn't in these findings" check was
> failing prose for the phrase **"Gram Panchayat"** — which is a value of
> `sanction_authority`, so it sits in the corpus roster as a category name. A
> check that forbids the subject's own name is catching English, not invention.
> Fixed by exempting names the context brief itself uses, the same rule numerals
> already had.

After both fixes the fallback rate went from 5/5 to **1/5**.

The accepted prose is scope-honest without being told to be. From the run:
*"These exceptions do not establish that they have the largest amounts or
explain why the pattern occurred"* and *"They cannot by themselves establish
year-end bursting."*

> **Defect 6, in my authored data, found by a unit test.** "Where is money
> planned but not spent?" did not reach `overspend_vs_plan`: `measure_keywords.json`
> had "money not spent" but not "not spent". Fixed, and the three-arm experiment
> was **re-run** afterwards so the reported table matches the shipped data file.
> The conclusion did not move.

### 3.4 The three moves, end to end

A live multi-turn check through the HTTP service:

| turn | message | move | behaviour |
|---|---|---|---|
| 1 | "How is Chikilli doing?" | `retrieve` (model) | 4 findings, stamped |
| 2 | "How much did Chikilli spend last year?" | `lookup` (rule) | declines, names Ask, no figure |
| 3 | "Why is that?" | `why` (rule) | reframe, limit stated, next steps offered |

Every routing decision is logged with its **source** (`rule` / `model` /
`default`) and its reason, so a turn decided by rules and a turn decided by a
model are told apart in the log rather than blended.

**Ambiguity resolves toward the honest answer, not the impressive one.** An
unclear classifier verdict becomes RETRIEVE — the move that can end in "the
analysis has nothing on this". Defaulting to LOOKUP would route a real question
away to another product; defaulting to WHY would refuse one that could have been
answered.

---

## §4 Bugs found in existing code — logged, not fixed

Per the brief, these are reported and left alone.

1. **`generate_nl_summary` never mentions the base subspace**, so 2,464 of 4,239
   candidates render as a sentence some other candidate already owns (§1.2).
   Harmless for the ranked feed, which is diversity-selected; load-bearing for
   anything that shows more than the top cut. `Insights/src/phase5_ranking.py`.

2. **Two different titles for the same view, in two files.** `phase5c_global_feed.VIEW_TITLES`
   says `Geo-Month Cash Cube` and `GP Performance`; `phase5b_report.VIEW_DESCRIPTIONS`
   says `Monthly Money Flows by Gram Panchayat` and `Gram Panchayat Report Card
   by Year`. DiscoverChat uses the descriptive titles for retrieval (an officer
   may type "monthly money flows"; nobody will type "Geo-Month Cash Cube") and
   carries the feed's short title unchanged on the record. Worth reconciling
   before either surfaces to an officer.

3. **`prose_gate.py`'s entry point does not carry the causal-verb ban**, so the
   executive and gamma **reports are not covered by D41** — only DiscoverChat
   is. `Insights/src/prose_gate.py` is outside this WP's writable set; folding
   `DiscoverChat/causal_gate.py`'s vocabulary into it is a one-function change
   for whoever owns that file next. **This is the one item here with a live
   consequence** and it is a PM decision, not an implementation one.

4. **`status_label` contains `Buildings`** (13 rows, an asset category). Already
   known — WP-D4 report, and Ask's validator logs and excludes it. Restated only
   because it is in the retrieval corpus too, undisturbed.

---

## §5 Operator decisions

### 5.1 The brief's five, as they now stand

1. **D-numbers** — already assigned by the PM (D41, D42, D43). Nothing needed.
2. **v1 audience** — still open. Sets how hard the D5.3 gate is.
3. **Free writer + safety net for connective prose** — implemented as the brief
   assumed. §3.3 is the evidence: 0 invented numerals, 1 fallback in 5.
4. **Quality-floor policy** — implemented as the brief's default: index
   everything, `QUALITY_FLOOR = 0.0`, and **every finding shown states its
   coverage** ("not in the ranked shortlist — one of the wider set of patterns
   the analysis found but did not promote"), gate-checked. On a broad question
   this means all 12 shown findings can be unranked ones. **Confirm that is
   acceptable**, because it is what an officer will usually see.
5. **Deploy target** — not deployed. Recommendation: **local-only until D5.3
   passes.** Nothing in the build assumes a host.

### 5.2 New ones this work raises

6. **Ratify the knobs.** `CANDIDATE_FLOOR = 0.50`, `CANDIDATE_POOL = 100`,
   `GEO_BOOST = 0.06`, `MEASURE_BOOST = 0.03`, `QUALITY_FLOOR = 0.0`,
   `ANSWER_CAP = 12`, and `RELEVANCE_THRESHOLD = 0.62` for the fallback path.
   All are provisional and all are environment overrides.

7. **RESOLVED in review — the judged path (§2.4a).** The threshold/classifier
   trade was settled by the operator's arm-D proposal rather than by picking a
   threshold: floor 0.50, top 100, judged. What remains open is whether the
   **live** out-of-scope check is run often enough to trust, since that
   guarantee is no longer arithmetic.

8. **Whether the corpus sidecars are committed.** `retrieval_corpus.json`
   (17.9 MB) + `.npy` (17.4 MB) is **35 MB into a Drive-synced git repo**. They
   are deterministic build outputs and could be gitignored and rebuilt (~8
   minutes, ~640k embedding tokens) instead. Left uncommitted for the operator
   to decide.

9. **The D41 gap in the reports path** — §4 item 3.

10. **Raising `RANKING_PREFILTER_CAP`** if D5.3 shows cap-related misses (§1.6).

### 5.3 What D5.3 needs from the operator

- **`DiscoverChat/experiments/LABEL_SHEET.md`** — 12 questions, pooled
  candidates, arm-blind. Mark every finding that belongs in a good answer, not
  just the best one; a question that should return nothing is a real and useful
  label.
- **Free interaction** against the service, graded Ask-style: answered-well,
  declined-correctly, **confidently-wrong** (the one that matters — the Ask bar
  is low single digits).

---

## §6 Self-audit

**Files I created** — every one inside the brief's writable set:

```
Insights/src/phase5d_retrieval_corpus.py
Insights/metainsights/retrieval_corpus.json  .npy  _stamp.json
DiscoverChat/**            (20 modules incl. judge.py, 2 data files,
                            2 test modules, 6 experiment scripts + outputs,
                            README, requirements.txt, .env.example, .gitignore)
handoffs/WPD5_REPORT.md
```

**Files I did not touch.** Every existing file under `Insights/src/` (imported
only), the candidate/ranked/feed JSONs, `Ask/**` (imported read-only),
`PROJECT_PLAN.md`, domain packs, `Data/`, reports, every `.env`. No git
operation beyond `status` / `log` / `rev-parse`.

**Not mine, seen in `git status`, untouched** — WP-D4b's concurrent set:
`Insights/src/phase5e_insight_prose.py`, `Insights/src/insight_prose_config.py`,
`Insights/metainsights/insight_prose.json`,
`Insights/reports_prdw/check_insight_prose.py`,
`Insights/reports_prdw/wpd4b_run/`, `handoffs/WPD4b_REPORT.md`,
`handoffs/WPD4b_prose_production.md`. Also PM-modified:
`handoffs/PROJECT_PLAN.md`, `handoffs/WPD5_retrieval_chatbot.md`.

**Pinned files, re-verified at close — all unchanged:**

| file | sha256 (first 24) |
|---|---|
| `view1_candidates.json` | `890767085988a6c7b61b1694` |
| `view2_candidates.json` | `5796d3c8029c5f06efe71fa5` |
| `view3_candidates.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `view1_ranked.json` | `182ff833849488cad3a15c0c` |
| `view2_ranked.json` | `44c9638c450d29af03e29818` |
| `view3_ranked.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `global_feed.json` | `3da40edae324f917ce8fd511` |

**Mirror/Drive parity:** `retrieval_corpus.json` and `.npy` are byte-identical
between `C:\dev\odisha-d5` and the Drive repo.

**What I did not do.** D5.3 is not claimed — it is an operator gate and the
labelling sheet is the deliverable. Nothing was deployed. `prose_gate.py` was
not extended (outside the writable set; §4 item 3). The two operator questions
that gate scope — v1 audience and the threshold/classifier trade — are left
open rather than answered by assumption.

---

## §7 Reproducing this

From a local mirror, at the repo root:

```bash
python Insights/src/phase5d_retrieval_corpus.py     # D5.0, ~8 min cold, ~1 s cached
python DiscoverChat/gates.py                        # D5.2, 13/13, no model calls
python -m unittest DiscoverChat.tests.test_retrieval DiscoverChat.tests.test_behaviour
python DiscoverChat/experiments/run_arms.py         # D5.1 three arms
python DiscoverChat/experiments/sweep_boost.py      # D5.1 boost weight
python DiscoverChat/experiments/run_judge_arm.py    # D5.1b arm D, the judged path
python DiscoverChat/experiments/label_sheet.py      # the operator's sheet
python DiscoverChat/experiments/measure_prose.py    # writer/verifier behaviour
python -m uvicorn DiscoverChat.main:app --port 8100
```

Call log for every model call made during this work:
`DiscoverChat/experiments/logs/calls.jsonl`.

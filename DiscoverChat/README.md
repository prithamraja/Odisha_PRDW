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
| **retrieve** | pool everything above the candidate floor (0.50), hand the top 100 to a **relevance judge**, and show what it keeps. The judge's selection is turned into **one consolidated narrative** by the writer (WP-D7), every figure citing the finding it came from. |
| **navigate** | a follow-up walks finding structure — an exception member, a shared measure, a sibling finding. No free exploration. |
| **decompose** | *"where does the gap sit"*, *"which blocks account for the shortfall"*, *"break it down by fiscal year"*. Retrieved exactly as a retrieve turn is, over the same corpus; what the move records is the intent. |
| **decline** | a number-lookup routes to Ask; a *why* question gets a scope-honest reframe (D41: correlations only, no causal analysis). |

The turn classifier runs on `gpt-5.4-nano` (WP-D7 D7.0; `gpt-5.5-nano` in the
brief was unavailable on the account, and the operator chose the nearest nano).
Rules decide every unambiguous route first; the model is asked only about what
is left. Revert with `DISCOVERCHAT_CLASSIFIER_MODEL=gpt-5.5`.

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

# 1b. build the decomposition sidecar (D6.0). Needs the Parquet views first.
python Insights/src/build_views.py --pack Insights/domain_pack_prdw \
       --data-dir Data --views-dir Insights/views_prdw \
       --reports-dir Insights/reports_prdw --strict
python Insights/src/phase5f_decompose.py

# 2. the gate (D5.2 + D6.1) — one command, deterministic, no model calls
python DiscoverChat/gates.py
python DiscoverChat/gates.py --live      # plus real turns through writer+verifier

# 3. the tests, by module name (this project's venvs have no pytest)
python -m unittest DiscoverChat.tests.test_retrieval DiscoverChat.tests.test_behaviour

# 4. the service
python -m uvicorn DiscoverChat.main:app --host 127.0.0.1 --port 8100
```

`GET /health`, `POST /chat`, `GET /finding/{id}`, `GET /record/{id}`,
`GET /ask-route`.

## Fast answers: the consolidating writer, provenance, and the audit (WP-D7)

Three changes, all reachable through config so any one can be reverted without a
redeploy.

**The writer consolidates (D7.3).** Before WP-D7 the model wrote only connective
prose and the finding sentences were shown verbatim beneath it. Now the judge's
selected findings go to the writer as one narrative: overlapping findings merged
into a small number of patterns, told for a senior official. The finding
sentences are no longer printed — the narrative is the answer. Three guards make
that safe without an inline verifier, and they are the reason the citations have
to be checkable rather than decorative:

1. **Citations.** Every figure and claim tags the finding id it came from,
   `[1-00235]`. The tags are plumbing and are stripped before an officer sees
   the text.
2. **The citation check (`checks.check_citations`), blocking, four steps:**
   every cited id is in the answer set; every numeral appears in the *stored
   sentence of a finding cited in the same sentence* (an uncited numeral, or one
   cited to a finding that does not contain it, fails); the causal scan; every
   selected finding is cited at least once. On failure the writer regenerates
   once, then falls back to the bare glossary-translated sentences — the pre-D7
   text, ratified as designed behaviour, not a defect. The fallback rate is
   reported.
3. **No derived figures.** The writer may not compute a percentage, sum or
   difference; a computed number is in no finding's stored sentence, so step 2
   catches it.

**Hover-to-source (D7.2/D7.3).** The number itself is the hover target.
`GET /record/{id}` returns the stored record — the sentence as stored and as
glossary-translated, its coordinates, values, engine score and run stamp — as
JSON, or `?format=html` for a readable view. An unknown id 404s. `POST /chat`
returns the prose with its tags (`answer_tagged`), a per-id record map
(`citations`), and a reference HTML render (`answer_html`) that binds each
numeral to its record with the same function the citation check uses. The hover
UI in the Discover tab is the front end's to build; the service ships the
reference render so the behaviour suite can exercise it end to end.

**The verifier moved offline (D7.1).** Inline verification is off for turn prose
(`DISCOVERCHAT_INLINE_VERIFY=1` restores it) — it cost a median ~28 s of a ~60 s
turn. `verifier.py` is unchanged; `experiments/run_prose_audit.py` runs it over
logged writer output and reports a **drift rate** for the operator to judge —
not a pass/fail.

> **The audit is the only check on qualitative drift.** The citation check
> covers numbers, not meaning. A limitation quietly narrowed, a subset total
> generalised to the whole, a hedge dropped — every one of those passes the
> citation check with every digit correct, and with D7.3's consolidating writer
> the model now restates findings rather than only introducing them, so that
> class of error is if anything more reachable than before. WP-D4 measured it at
> 3 in 15 packets and the inline verifier was what caught it. Nothing catches it
> inline any more. Read the audit's drift rate as the price of the latency.

```bash
# D7.0 — qualify the nano classifier (4 runs, gates on zero null classifications)
python DiscoverChat/experiments/run_classifier_nano.py --repeats 4
# D7.1 — the offline drift audit over logged writer calls
python DiscoverChat/experiments/run_prose_audit.py
# D7.3 — before/after over 15 answers, with latency (writes answer_compare.md)
python DiscoverChat/experiments/run_answer_compare.py
```

## The front end

The Discover tab's question box — *"Ask a question to generate an insight
report"* — posts to `/chat` here, not to Ask. It is its own base URL
(`VITE_DISCOVER_API_BASE_URL`, default `http://localhost:8100`) because the two
products are two services; one shared variable would silently send Discover
questions to Ask's `/query` the first time either moved.

| front-end file | what it does |
|---|---|
| `src/services/discover-api.ts` | the `/chat` client and the response types |
| `src/lib/discover-answer.ts` | splits one answer into findings, prose and the run stamp — presentational only, nothing rewritten or dropped |
| `src/components/insights/InsightSearchBar.tsx` | the question box above the category chips |
| `src/components/insights/InsightReport.tsx` | the report card, including the handover on a decline |

Two behaviours the front end owns rather than the service:

**The handover.** A `lookup` move is the D42 decline — the service will not
proxy a records question. The card then offers *"Put this question to Ask"*,
which switches tabs and re-sends the officer's own words, unchanged.

**The run stamp is always shown.** Every answer ends in one; the card pins it
under the report, because a pattern read without the date it was mined on reads
as today's.

CORS is open (`allow_origins=["*"]`, credentials off) so the browser can reach
this from the dev server's port. Nothing here is per-user and everything it
serves is already-published findings.

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
| `causal_gate.py` | a thin adapter over `Insights/src/prose_gate.py`, which holds the one copy of the causal-verb ban (D41) |
| `glossary.py` | render-time column translation — `fund_untied_total` becomes "untied grant planned". A dictionary, no model |
| `verifier.py` | different-model verifier, retry-on-empty |
| `assemble.py` | the three moves; renders findings from the corpus |
| `navigate.py` | the three structural walks |
| `gates.py` | the D5.2 behaviour suite |
| `query_expansion.json`, `measure_keywords.json`, `decompose_triggers.json` | authored **data**, on the SBM-dictionary precedent — the operator grows these from query logs without a code change |

## Decompositions (WP-D6)

Alongside the 4,239 mined findings the service serves 36,218 **decompositions** —
precomputed answers to *"where does this amount sit"*. Each one splits a
measure's total across one dimension inside one slice, and its members add up to
that total. They are built by `Insights/src/phase5f_decompose.py`, embedded
under the same pin, and retrieved through the same machinery; the chatbot
computes nothing at question time.

Two things about how they are served:

**Both kinds reach the judge.** The candidate pool reserves up to half its 100
slots for each corpus. Without that reservation the pool was measured at **100%
decompositions and zero findings** on four of five test questions — 36,218
records simply crowding out 4,239 at the cut, not out-ranking them. Ranking
itself is untouched: one score, one list, and the judge is never told which file
a candidate came from.

**The threshold path does not serve them.** `RELEVANCE_THRESHOLD` is 0.62
because D5.1 measured it over the findings corpus, and the property it buys is
that an out-of-scope question clears nothing. That does not survive the sidecar:
*"What is the price of onions in Cuttack market?"* reaches cosine 0.6256 against
a decomposition that opens *"Within district Cuttack, …"*, where over findings
alone it reached 0.488. So `score()` keeps the corpus its number was fitted on
and `pool()` — the judged path, which is production — searches everything. When
the judge is unreachable a decompose question degrades to findings only. The
judged path was re-measured with the sidecar loaded: **0.0% false-answer rate
over 20 runs** (`experiments/run_decompose_oos.py`).

Set `DISCOVERCHAT_USE_DECOMPOSE=0` to serve findings alone.

## Requalifying the judge

The out-of-scope guarantee is a property of **one model id**, not of the code.
At `CANDIDATE_FLOOR=0.50` four of the five out-of-scope questions reach the judge
with a non-empty pool, so it is the only thing standing between them and a
confidently-wrong answer, and its 0.0% false-answer rate was measured on
`gpt-5.6-sol` and on nothing else.

`gates.py` therefore fails red when `DISCOVERCHAT_JUDGE_MODEL` is not the id the
evidence was measured on. The evidenced id is read out of
`experiments/judge_arm_results.json` rather than restated as a constant, because
a constant can be edited in the same commit that swaps the model — which is
exactly the drift the check exists to catch.

To qualify a different judge, re-run the battery on it and let the run files
record the new id:

```bash
DISCOVERCHAT_JUDGE_MODEL=<new-id> python DiscoverChat/experiments/run_judge_arm.py
DISCOVERCHAT_JUDGE_MODEL=<new-id> python DiscoverChat/experiments/run_decompose_oos.py --repeats 4
```

The first rewrites `judge_arm_results.json`, which is what the gate reads; the
second repeats the out-of-scope battery with the decomposition sidecar loaded.
**Both must come back at a 0.0% false-answer rate before the id is trusted.**

### The prompt is qualified too, not just the id (WP-D9)

The guarantee belongs to the model **and the words it was given**, together.
Until WP-D9 the gate pinned only the id, so the judge's instruction could be
rewritten — loosened, tightened, or helpfully tidied — while every check stayed
green and the evidence quietly stopped describing the running system.

`judge-prompt-evidenced` closes that. The evidence files record
`judge_prompt_sha256`, the SHA-256 of the prompt **template** (not a rendered
prompt: a rendered one carries the question and 100 candidates, so its hash
changes every call). The check fails red on any change to the template and
names the requalification, exactly as a model swap does.

**So a prompt edit is requalified the same way a model swap is** — re-run both
scripts above without the `DISCOVERCHAT_JUDGE_MODEL` override; they stamp the
new hash into the run files as they go.

Two instructions ship, and both stay reachable so the wording can be reverted
by configuration rather than by a revert commit:

| `DISCOVERCHAT_JUDGE_PROMPT` | the instruction |
|---|---|
| `complete` | keep every finding that adds distinct information; drop near-repeats |
| `minimal` | the pre-D9 "keep the smallest set that fully answers the question" |

Switching the variant moves the hash, so it goes red until the battery is
re-run on it. That is the intended workflow, not a nuisance: an unmeasured
judge instruction is exactly what the check is for.

## Two things to know before changing anything

**The knobs are provisional.** `RELEVANCE_THRESHOLD`, `QUALITY_FLOOR` and the
boost weights carry the values the D5.1 experiment measured. They become
ratified numbers at the D5.3 operator gate, not before. Every one is an
environment override, so moving one for a pilot needs no code change.

**The embedding pin travels with the corpus.** Model id, dimension count, the
query instruction and the storage dtype are pinned together and copied into
`retrieval_corpus_stamp.json`. Startup compares them and refuses to serve a
corpus embedded under a different pin — a mismatch there produces plausible
nonsense rather than an error, which is the worst failure mode available.

## How the corpus is stored, and how to read what was embedded (WP-D10)

The two sidecars are **90 MB on disk, down from 345 MB**, and nothing about what
they retrieve changed. Three things make the difference, each measured before it
was adopted:

| | |
|---|---|
| **gzip, level 6** | the record files are `retrieval_corpus.json.gz` and `decompose_corpus.json.gz`, compact (unindented) JSON. 10.9x smaller, 0.15 s to decompress. Written with `mtime=0` so two builds are byte-identical. |
| **float16 vectors** | the `.npy` files are half the size. Every loader upcasts to float32 at load, so the matrix, the cosines and the floor are float32 exactly as before — the storage width stops at `corpus._read`. |
| **no stored `embed_text`** | the enriched text that was embedded is no longer kept in the file. Its SHA-256 is. |

The vectors are deliberately **not** gzipped: floats compress 1.09x, which buys
nothing and costs a decompress on every start.

**WP-D5 ruling 7 is amended by D10 ruling 3.** It used to read "the exact
embedded text is stored"; it now reads "the exact embedded text is
**reproducible and hash-pinned**". The reproduction is a command:

```bash
# regenerate one record's embedded text from its stored fields and check it
# against embed_text_sha256 — prints the text, then MATCH or MISMATCH
python Insights/src/phase5d_retrieval_corpus.py --embed-text 1-00042
python Insights/src/phase5f_decompose.py --embed-text d1-00042

# the whole corpus at once; exits non-zero if any record fails
python Insights/src/phase5f_decompose.py --embed-text ALL
```

MISMATCH means the record and its vector have stopped describing each other and
the corpus needs rebuilding. All 40,457 records report MATCH as of WP-D10.

One shape to know: a decomposition's `members` are stored **columnar** —
`{"member": [...], "value": [...], "rows": [...], "share": [...],
"null_index": [...]}` — because one dict per member was the largest single thing
in the sidecar. Never read that layout directly; `corpus.members_of(record)`
hands back the list of dicts and accepts a pre-D10 file unchanged.

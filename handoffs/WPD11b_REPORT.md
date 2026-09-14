# WP-D11b report — split vectors, causal wording, unit labels, averaged twins

**Workstream:** Discover. **Nature:** BUILD, gated. **Executed:** 2026-09-11 by the
implementation agent, against `handoffs/WPD11b_profile_followon.md` (D61).
Mirror: `C:\dev\odisha-d11b` (a copy of WP-D11's `C:\dev\odisha-d11`, which is
left untouched as the WP-D11 record). Code was edited on the Drive tree and
copied into the mirror; build output comes back through
`handoffs/WPD11b_calibration/sync_back.sh`.

Nothing is committed and nothing is pushed. No Railway operation was performed.
`Data/`, the pack and `Insights/DISCOVER_VIEW_MAPPING.md` were not written to.

---

## §0 Status — the six gate items

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | Both corpora load from parts, byte-identical to unsplit; every vector file < 100 MB; zero embedding calls on an unchanged rebuild | **PASS** | `t1_split_proof_output.txt` 22/22; parts 9.0 / 68.4 / 68.4 MB; two consecutive rebuilds byte-identical, 0 calls both — §1 |
| 2 | Prompt gate green on the operator's wording; D41 scan runs on the feed; editions gate outcome reported | **PASS, with two results reported red** | `consolidation-prompt-is-the-operators` green, gates 34/34 offline and live. The feed scan runs and gates: **3 hits (was 12) — red**. Editions: **13 hits across five (was 21) — `check_editions` red on the prose gate only**. The general sentence roughly halved the word-scan hits and did not clear it. One unit test still pins the old line (red, §2) — §2 |
| 3 | No bare size-band label on a regenerated prose surface; numeral and verifier checks pass on the unit form | **PARTIAL** | No engine label reaches any writer or reader bare, and numeral/verifier checks pass on the unit form; the chat answer and the executive report carry 0 bare labels. But the writers shorten their own second mentions ("those under 2,500", "the 5,000 to 10,000 band"): 1 in the feed, 36 across the gamma editions. `global_feed.md` (29) is the deterministic engine-sentence table, not prose. Size-band fallback **57% → 27%** — §3 |
| 4 | view3/view4 re-mined with averaged twins; view1/view2 candidates unchanged; regression gate 0 failures; `_mean` findings in both top-15s | **PASS** | view1/view2 SHA-256 unchanged; regression gate 0 failures; twins in 11/15 (view3) and 11/13 (view4) — §4 |
| 5 | One candidate set across every artefact; calibration package refreshed; size-band fallback rate reported against 57% | **PASS** | `610cb3d26dff7bf3` in the feed sidecar, the prose sidecar, both corpus stamps and every edition header (`check_editions`' sidecar comparison passes); package in `handoffs/WPD11b_calibration/` (58-row labelling sheet, four findings sheets, both diffs); fallback reported — §3, §5 |
| 6 | Operator calibration session on the refreshed top-15s | **PENDING — operator** | `handoffs/WPD11b_calibration/` |

**One unbriefed change, on an operator ruling made during the WP: the embedding
provider moved from Novita to OpenRouter** (§1b). Novita changed behaviour
between WP-D11 and this WP and stopped accepting the pinned request.

---

## §1 The split (T1)

### Layout

Every vector matrix is written as `<name>.part<N>.npy`: consecutive row slices of
one C-contiguous fp16 array, **sized evenly** (ceil(rows / n) each) under a
95,000,000-byte budget, listed in the stamp's new `vector_storage` block with a
SHA-256 per part and `matrix_sha256`, the hash of the whole matrix's bytes. The
findings matrix fits in one part and is still written as `.part0.npy`, so there
is one layout and one loader. The unsplit spelling is never written; it is
retired only **after** the stamp naming the parts is on disk, so a kill mid-build
leaves the previous build readable.

| corpus | shape | parts | sizes | part SHA-256 | matrix SHA-256 |
|---|---|---|---|---|---|
| retrieval (WP-D11 set) | 4,397 x 1,024 | 1 | 9.0 MB | `4e9e99acb79705ba…` | `36683d5cacf00901…` |
| decompose (WP-D11 set) | 66,779 x 1,024 | 2 | 68.4 + 68.4 MB | `6ff9e3f1bf9988cb…`, `3ddec5cbbcf91ed4…` | `76eb1f2a85d6da7c…` |

The single findings part is byte-identical to WP-D11's `retrieval_corpus.npy`
file (same SHA-256 `4e9e99ac…`): one part of one array is the same file.

### Loader

`phase5d.load_vectors(path, manifest)` reads the parts in order, refuses a part
that is missing, whose SHA-256 differs from the stamp, or whose concatenation is
not the recorded shape (`VectorPartsError`), and returns fp32. `DiscoverChat/corpus.py`
passes each corpus's stamp and turns a refusal into a STOP. The builders' cache
reader (`load_previous_vectors`) reads a split build through its stamp or a
pre-split build through its single file, which is what let the first split
build reuse every vector.

`embedding_pin()` gains `storage_layout` (loader guard, as `storage_dtype` did in
WP-D10); `semantic_pin()` is unchanged by the split. New gate check
`vector-parts-under-limit`: every part named by either stamp exists and is under
100,000,000 bytes, no `.npy` in `metainsights/` is unnamed or over the limit, and
the unsplit spellings are absent. `.gitignore` now ignores the unsplit spellings
(they were tracked; the adopting commit must record their deletion).

### Proof

Run on the WP-D11 candidate set `d619a72e4fe98d5f`, before anything else in this
WP changed, so the only variable was the layout:

| check | result |
|---|---|
| first split rebuild | **0 embedding calls**; 4,397 + 66,779 vectors reused from the unsplit files |
| second rebuild | **byte-identical** on both `.json.gz` and all three parts; stamps differ only in `generated_at` / `build_seconds`; 0 calls |
| parts concatenated vs the unsplit fp16 arrays (sha256 of `.tobytes()`) | **identical**, both corpora; dtype and shape equal; equal to the stamp's `matrix_sha256` |
| loader output vs unsplit array upcast | `np.array_equal`, both corpora |
| altered part / missing part | both **refused**, both corpora (scratch copies) |
| `semantic_pin()` vs the pin WP-D11 embedded under | equal |

`handoffs/WPD11b_calibration/t1_split_proof.py` (re-runnable), output in
`t1_split_proof_output.txt`; rebuild logs `t1_rebuild{1,2}_*.log`, hashes
`t1_rebuild{1,2}_hashes.txt`.

Pool overlap was not measured separately: the served matrix is byte-identical,
so every cosine, and therefore every pool, is identical by construction.

## §1b The embedding provider: Novita → OpenRouter (operator ruling, this WP)

**What happened.** The precondition probe found Novita's key live but the pinned
request refused: `dimensions=1024` → HTTP 400 "dimensions 1024 is not
supported", and the OpenAI client's default base64 encoding → HTTP 400. Without
`dimensions` Novita returns native 4,096-dim vectors. WP-D11 embedded ~28,000
texts with this exact request on 2026-09-08, so **the change is on Novita's
side, between 09-08 and 09-11.** The operator's suggested `max_tokens=1024`
was also tried: on the chat endpoint the model is refused ("not an chat model");
on the embeddings endpoint `max_tokens`, `dimension` and `output_dimension` are
all ignored (4,096 returned) — `embedding_probe_maxtokens.txt`.

**Consequence beyond this WP:** the deployed `discover-api` embeds every question
through the same request, so **its question retrieval has very likely been
failing since the change.** Not verified against production (no Railway
operation); the operator should check.

**Measured before switching** (`openrouter_probe.py`, output alongside; 16
findings + 16 decompositions, two calls each):

| comparison | cosine min / median |
|---|---|
| Novita vs OpenRouter, full 4,096, same text | 0.99985 / 0.99996 |
| OpenRouter `dimensions=1024` (DeepInfra) vs stored | 0.99984 / 0.99994 |
| OpenRouter `dimensions=1024` (Nebius) vs stored | 0.99984 / 0.99994 |
| Novita native, first 1,024, vs stored | 0.99986 / 0.99996 |
| OpenRouter server 1,024 vs its own native first 1,024 | 0.99992 / 1.0 |

The last line confirms the server's Matryoshka truncation is the prefix
(`embedding_probe.py`: the last 1,024 dims score 0.02 against stored).

**The change** (`phase5d_retrieval_corpus.py`, outside this WP's declared scope
for that file — operator-approved in session): base URL
`https://openrouter.ai/api/v1`, key `OPENROUTER_API_KEY` (Drive `Insights/.env`),
`encoding_format="float"` explicitly, OpenRouter routing
`{"order": ["DeepInfra"], "allow_fallbacks": true}` (`DISCOVER_EMBED_PROVIDER`
overrides), and a STOP on a vector of the wrong length. **`base_url` moved out of
`semantic_pin()`** into the full pin with `provider_route`
(`SERVICE_PIN_FIELDS`): it no longer decides what a vector means (measured
above), and leaving it in would have re-embedded all ~71,000 texts. The cache
now strips `NON_SEMANTIC_PIN_FIELDS` (storage + service). Checked through the
production code path: cache reusable against the Novita-built corpora (4,397/4,397),
`Embedder.documents` on 3 stored texts cos 0.99992–0.99996, `Embedder.query`
returns a unit vector (`openrouter_switch_check.txt`). Pin fingerprint now
`c2f9779ab6cf29d6`.

**Deploy note:** `discover-api` needs `OPENROUTER_API_KEY` in its Railway
variables before this code is deployed, or it will fail at the first question.
**The operator set it on 2026-09-11, during this WP** (reported in session; not
verified by the agent, which performs no Railway operation). Until this work is
committed and deployed, the running service still has the Novita-era code and
its question retrieval stays broken. `deploy/RAILWAY.md` still documents
`NOVITA_API_KEY` (out of scope here).

---

## §2 Causal wording (T2)

### The three prompts as changed

1. **Chat writer** (`DiscoverChat/context_brief.py`) — the operator's edit
   stands; typo fixed: *"It is very important that you do not make causal claims -
   none of our data can be used to determine causality."* The gate
   `consolidation-prompt-is-the-operators` now asserts that sentence in place of
   "Do not make causal claims ever".
2. **Gamma editions writer** (`phase5c_gamma_reports.build_prompt`, rule 5) —
   the same sentence, verbatim, as the rule's second sentence. **Nothing
   removed.** Rule 5 already carried a list of connectives ("because", "due to",
   "driven by", …) from WP-D3; ruling 2 forbids ADDING a word list and the brief
   says ADD the sentence, so the existing text was left — see §7.
3. **Feed writer** (`insight_prose_config.CONTEXT`) — the same sentence,
   appended to the context paragraph. `run_log_dir` is now `wpd11b_run`.

### The D41 scan on the feed

`check_insight_prose.py` now runs `prose_gate.check_causal_lines` — imported, the
same compiled patterns, denial window and request exemption as the editions —
over the shipped `insight_feed.md` as a **gating** check, printing every hit with
its line and attributing each to model prose or fallback text. A `--scan-causal`
mode runs it alone over any markdown (used for the baseline). There is **no
build-time hook** in phase5e: regenerating on a D41 hit would be the reroll the
ruling forbids (§6).

### Hit counts

| surface | WP-D11 (`d619a72e`) | WP-D11b (`610cb3d2`) |
|---|---|---|
| `insight_feed.md` | **12** | **3** — ranks 6 ('therefore'), 24 ('Because'), 34 ('because'); all model prose, none in fallback text |
| gamma 0.1 / 0.3 / 0.5 / 0.7 / 0.9 | 3 / 1 / 4 / 6 / 7 = **21** | 3 / 2 / 3 / 2 / 3 = **13** |
| executive report (not a ruling-2 target) | 12 | 4 |
| `global_feed.md` | 1 | 1 |

By word across the seven report files: 'therefore' 8, 'consequently' 4,
'because' 3, 'explain(s)' 3 (`d41_editions_after.txt`).

**Did the general sentence clear the word scan? No — it roughly halved it.**
Feed 12 → 3, editions 21 → 13. The executive report, whose prompt this WP did
not change, also fell 12 → 4, so part of the drop is the new candidate set and
not the sentence: the editions and the feed cannot be read as a clean test of
the wording alone. The residue is almost entirely the two connectives WP-D11
named — "therefore" and "consequently" — joining a size or composition figure to
its consequence. Per ruling 2 nothing was rerolled and no word was added; this is
the result for the operator.

**Gate results:** `gates.py` offline 34/34 and `--live` 34/34 (the operator's
sentence asserted; 0.0% false answers over 10 out-of-scope runs; 6 narratives,
0 fallbacks, 189 numerals bound, 0 uncited). `check_insight_prose`: 31 checks,
**1 failed — the new D41 check**. `check_editions_prdw`: **1 failure — "prose
gate clean on all editions"**. DiscoverChat unit tests: **92/93 — 1 failure,
`test_citations.WriterPromptTests.test_the_prompt_is_the_operators_text`**, which
asserts the old line "Do not make causal claims ever" (`test_citations.py:216`).
It is the unit-test twin of the gate assertion the brief told me to update; the
test file is outside this WP's writable set, so it is reported, not changed —
§7.

---

## §3 Unit labels (T3)

**One map**, `phase5b_report.BAND_DISPLAY` + `display_band_labels()` (idempotent;
never matches inside a larger figure), imported by all three surfaces:

| surface | where applied |
|---|---|
| gamma editions + executive report | the end of `enrich_candidates_with_stats` (stats, commonness sets, exceptions, slice — on copies, after every figure is computed on the bare labels); and the whole prompt string of `build_view_prompt` and `build_global_feed_prompt` |
| feed (phase5e) | every packet field the writer and verifier read (engine sentence, members, exceptions, scope, figures) and the deterministic fallback `cleaned_sentence` |
| chat | `DiscoverChat/glossary.render`, in the same single pass as the column names |

No pack file, view, categorical domain, candidate or embed text changed.

**The glossary entry for `gp_size` stays bare, on a measurement.** A first draft
passed it through the map; the column glossary is quoted into the EMBEDDED text of
every record touching `gp_size` (`phase5d.glossary_snippet`, phase5f), and the
change altered the embed-text hash of **917 findings and 3,623 decompositions** —
4,540 re-embeddings, forbidden by the brief and outside ruling 3's "prose time
only". Reverted to WP-D11's bytes; both corpora back to 0 mismatches. The unit
reaches the writers at the prompt boundary instead. Consequence: the gamma
prompt's Column Glossary (built in phase5c, outside scope) lists the bands bare
while every finding and figure in the same prompt carries the unit — §7.

Micro-choice: "Under 2,500 **people**" keeps the stored capital (a category name
beside 'Mixed'), where the brief wrote "under"; "10,000 people and above".

### Outcome

**Prose fallback, WP-D11 → WP-D11b** (`insight_prose.json` of each set; a record
counts as size-band when `gp_size` is its breakdown or extending dimension):

| class | WP-D11 first / regen / fell back | WP-D11b first / regen / fell back |
|---|---|---|
| all findings | 16 / 22 / 12 of 50 (24%) | **22 / 18 / 6 of 46 (13%)** |
| size-band (`gp_size`) | 4 / 3 / 8 of 15 (53%; WP-D11 reported 8 of 14 = **57%**) | **4 / 4 / 3 of 11 (27%)** |
| social composition | 9 / 8 / 0 of 17 (0%) | 10 / 6 / 1 of 17 (6%) |
| no profile dimension | 3 / 10 / 4 of 17 | 8 / 8 / 2 of 18 |

**None of the three size-band fallbacks is the WP-D11 cause.** Rank 26 fell back on
a year numeral ("2021" not in the packet); rank 42 on a claim about
`fund_sanctioned_total` whose definition the packet lacks (§5, §7 D); rank 45 on
"larger GPs lead ... per GP" against a total. No verifier rejection in this run
names "people" or "population". The packet the verifier reads carries the unit
form (checked on rank 3; no bare label in it).

**Numeral and verifier checks on the unit form:** `check_insight_prose` replays
every shipped rendering check-green (its one failure is the D41 check); the chat
answer's citation check passed with every numeral bound — "2,500" binds to its
source sentence exactly as before, "people" being a word.

**Bare-label scan** (`t3_label_scan.py`, case-insensitive, a band not followed by
"people"):

| surface | bare | with unit | what the bare ones are |
|---|---|---|---|
| chat answer (production writer over 5 size-band records) | **0** | 4 | — |
| executive report | **0** | 18 | — |
| `insight_feed.md` | 1 | 13 | "followed by those under 2,500 at Rs 6.08 lakh" — a second mention |
| gamma 0.1 / 0.3 / 0.5 / 0.7 / 0.9 | 2 / 1 / 17 / 12 / 4 | 33 / 47 / 28 / 45 / 24 | writer shorthand after a first mention with the unit: "the 5,000 to 10,000 band paid ...", "those under 2,500 hold ..." |
| `global_feed.md` | 29 | 0 | the deterministic table of raw engine sentences (its column names are raw too: `fiscal_year`, `payment_amount`); written by `phase5c_global_feed`, outside scope — not prose |

So the map did what it can do: every label a writer is given carries the unit,
and the one surface with no writer in the loop between map and reader (chat)
shows none bare. What it cannot do is stop a writer abbreviating its own
sentence, and ruling 2's logic applies — no rule was added to stop it. The
gamma prompts' own Column Glossary is the one place a bare label still reaches a
writer on the committed code (§3 above, §7 C).

Chat answer, verbatim excerpt: *"GPs with 2,500 to 5,000 people account for 40.8%
(5,182 activities), while those with 5,000 to 10,000 people account for 37.0% ...
GPs with under 2,500 people and those with 10,000 people and above have the
lowest sanctioned amounts across all fiscal years."* (`t3_label_scan_output.txt`)

---

## §4 Mining (T4)

### The twins

`MeasureConfig(f"{m}_mean", "avg", column=m)`: 10 on view3 (per Gram
Panchayat-year), 14 on view4 (per Gram Panchayat), exactly the brief's lists.
Units are derived from the total's ("rupees, averaged per Gram Panchayat-year")
with new formatters — averaged counts keep one decimal, two below 1, so an
average can never print as a false zero. Glossary entries are generated in the
WP-D2c appendix form from each total's own entry (basis, sign and coverage
inherited by reference). `activity_count_measures` reads the unit's first clause,
so the FY 2023-24 caveat still scopes `n_activities_mean`.

**Rule 2b / 2c.** A twin is never A2-merged with its total: `_twin_key` includes
the measure name (checked in the config gate). The intensity companion was
view2-only; the registry is now derived from the configs for views 3 and 4 so
rule 2c fires for every new pair, with each view's own grain words (view2's
strings byte-for-byte unchanged), and rule 2c's text was generalised from "per
month" to "per month, per year or over the whole window, as its 'what_this_is'
says" (§6). The regression gate's size-share check skips AVG measures by design.

### Gates

| gate | result |
|---|---|
| config gate (`WPD11b_calibration/verify_configs_prdw_d11b.py`, WP-D11 copy + §5b) | **245 checks, 0 failures** |
| view1 / view2 candidates, SHA-256 before vs after | **unchanged** (`1335f437…`, `602ff52e…`) |
| view3 / view4 mined | drained; 45 and 31 candidates; 144 s wall for both, 6 workers, cache flags as WP-D11 |
| regression gate (WP-D2c), four views | **0 failures** |

The candidate set id changes because it is computed over all four files:
**`d619a72e4fe98d5f` → `610cb3d26dff7bf3`**. The global feed now carries 46
findings (was 50).

### What the twins did to the top-15s

`twin_diff.py`; full lists in `diff_vs_d619a72e.md` and `diff_vs_a7f991c1.md`.

| view | ranked | unchanged vs WP-D11 | new | rest on a twin | band-headcount before → now | displaced |
|---|---|---|---|---|---|---|
| view1 | 15 | 15 | 0 | 0 | 1 → 1 | 0 |
| view2 | 15 | 15 | 0 | 5 (WP-D2c's own) | 7 → 7 | 0 |
| view3 | 15 | 3 | 12 | **11** | **14 → 4** | 11 |
| view4 | **13** (was 15) | 8 | 5 | **11** | **15 → 2** | 7 |

"Band-headcount" = breaks down or varies along a profile band while measuring a
TOTAL. The WP-D11 artefact is largely displaced on both views. view4 now ranks
13, not 15: 31 candidates, and the greedy ranker stopped when no remaining
candidate improved total usefulness.

---

## §5 Editions and spend

Every artefact carries candidate set **`610cb3d26dff7bf3`**; run stamp
`2026-09-11T09:31:44Z` (stage A, re-used by stage B).

| artefact | result |
|---|---|
| `view{1,2,3,4}_ranked.json` | 15 / 15 / 15 / **13** |
| `global_feed.json` + source-set sidecar | **46** findings (was 50) |
| five gamma editions | written (the orphan run; see §6 item 13) |
| executive report + PDF | written, from the final code |
| `insight_prose.json` + `insight_feed.md` | 46 findings, 4 sections, reading notes off (D48-1); sidecar sha256 `5d53cff1…`, rendering `535007c0…` |
| `retrieval_corpus.json.gz` / `.part0.npy` / stamp | **4,404** records; **56 embedded through OpenRouter in 1 call**, 4,348 reused; 9.0 MB part |
| `decompose_corpus.json.gz` / `.part{0,1}.npy` / stamp | 66,779 records, **0 embedded** (the twins are AVG; decompositions are SUM-only); parts byte-identical to the T1 build |
| pin fingerprint on both stamps | `c2f9779ab6cf29d6`, base URL OpenRouter |

| gate | result |
|---|---|
| `check_feed_contract --base Insights` | **PASS** |
| `check_editions_prdw --base Insights` | **1 failure: the D41 prose gate** (one candidate set, reading notes, earmark carriers all pass) |
| `check_insight_prose --rebuild-roster` | 31 checks, **1 failed: D41** |
| DiscoverChat `gates.py` / `--live` | **34/34 / 34/34** (incl. `vector-parts-under-limit`) |
| DiscoverChat unit tests | **92/93** — the old-sentence assertion (§2) |

The first stage-B run called `check_editions_prdw.py` and `check_feed_contract.py`
without their required `--base`, and both exited 2 on argparse having checked
nothing — my script's error, fixed in `run_t5_stage_b.sh` and re-run by hand;
the results above are the re-run.

**Spend.** Prose: **100 calls, 334,553 tokens** (cap 150, per-WP log
`wpd11b_run/`), plus the **30 wasted** calls of the failed build (archived,
below) = 130. Gamma editions (20 writer calls) and the executive report are not
metered by those scripts. Chat live gate and the T3 chat answer: a handful of
calls. Embeddings: 1 OpenRouter call for the corpus (56 texts), plus the probes
(Novita ~12 calls, OpenRouter ~20).

### The failed prose build, set aside

The first prose build under this WP (10:29:53Z) made **30 calls** and wrote ranks
1–13 of 46 before OpenAI returned HTTP 500 on the rank-14 regeneration (after the
client's two built-in retries). A one-call probe to each model afterwards
succeeded, so the error was transient. **On the operator's ruling ("set aside
and rerun all") its call log was moved to
`reports_prdw/wpd11b_run/archive_failed_run/` with a README**, so the 150-call
cap covers the re-run alone — the WP-D11 procedure. The 30 calls are spent and
bought nothing. `run_log_dir` being per-WP is what made this a clean move rather
than an untangling of two WPs' logs.

### Found during the failed build, not fixed: the writer renumbers a batch

The view1 writer batch was sent ranks [1, 5, 7, 9, 11, 14, 16, 20, 22, 24, 25,
27, 32, 35, 42] and answered with blocks numbered **1–15**. `parse_renderings`
keys each block by the number the writer wrote, so the answer to the 5th packet
(rank 11) was filed under rank 5, and so on; ranks 16–42 got nothing and
regenerate singly. The nothing-invented checks and the verifier caught every
misfiled rendering (ranks 5, 7, 9, 11 regenerated), so **no wrong prose
shipped** — but every misfile costs a verifier call and a regeneration, and it
is a plausible contributor to WP-D11's 22 regenerations. The fix belongs in
phase5e's batch parsing (match by position within the batch, or refuse a batch
whose numbers are not the ranks sent); outside this WP's phase5e scope — §7.

### Packets still missing variable definitions (pre-existing)

`insight_prose_config.MEASURES` / `DIMENSIONS` carry no view4 entries and no
profile dimension, so packets for findings on them go to the writer and the
verifier with those variables undefined (`definitions missing` in the build
log: `gp_size`, `social_composition`, every view4 measure on the measure-
extending findings, and the new `_mean` measures). The unit now travels in the
LABEL for gp_size (T3) and in `measure_unit` / `how_aggregated` for the twins;
the definitions themselves are a WP-D11 omission in a file this WP may edit only
for `CONTEXT` and `run_log_dir` — §7.

---

## §6 Decision journal

Decision / choice and reason / reversal cost.

1. **Vector parts sized evenly, not filled to 95 MB.** Two 68.4 MB parts share the
   headroom; a fill-first split would put the next mining run's growth into a part
   already at 95 MB. *Reversal: one line.*
2. **The findings matrix is `.part0.npy` although it fits in one file.** One
   layout, one loader, and the unsplit spelling is never written. *Trivial.*
3. **`storage_layout` added to the full pin (the brief allowed it).** Stops an old
   stamp being served by the new loader, as `storage_dtype` did. *One field.*
4. **The unsplit file is retired after the stamp is written, not before.** Kill
   safety. *None.*
5. **Embedding provider switched to OpenRouter; `base_url` moved out of the
   semantic pin** — operator ruling in session after the Novita refusal (§1b).
   Outside the file scope the brief gave phase5d. *Revert: two constants and the
   pin split; forces a full re-embed if the URL goes back into the semantic pin.*
6. **Rule 5's existing connective list was left in place.** The brief says add
   the sentence; ruling 2 forbids adding a list, and deleting WP-D3's text was
   not asked for. So the editions test "general sentence + old list", not "general
   sentence alone" — §7. *Reversal: delete two bullets.*
7. **No D41 hook in the prose build.** A build-time scan that regenerated on a
   hit would be a reroll to clear a gate. The scan is post-hoc in the checker.
8. **The `gp_size` glossary entry stays bare** — measured: 4,540 embed-text
   changes (§3).
9. **"Under" keeps its capital** in the displayed label. *One string.*
10. **Intensity-companion registry extended to views 3/4 and rule 2c
    generalised** — outside the literal "_UNITS and glossary" scope for
    phase5b, but fact 5 asks for the rule to fire for the new pairs, and 2c's
    "per month" would have been false for them. *Reversal: one loop, one
    paragraph.*
11. **Averaged-count formatter: one decimal, two below 1.** "0.0 approval
    records" is the false-zero rule 4b forbids. *One function.*
12. **Plain-English phrases for the twins are DERIVED** from the total's authored
    phrase at the view's grain (phase5e fallback sentences; DiscoverChat glossary
    for views 3/4 only, so the gate's declared view2 gaps are unchanged). *Two
    small functions.*
13. **A stage-A run was stopped and a gamma process outlived the stop.** The
    orphan produced all five gamma editions while the `gp_size` glossary entry
    still carried the unit form (the draft later reverted — §3). **They ship as
    written, on the operator's ruling (2026-09-11: "skip it")**, rather than
    being regenerated for ~50 minutes and ~20 calls. Consequence, stated
    plainly: the committed code does not reproduce those five editions byte for
    byte — re-running it would give their prompts a Column Glossary that lists
    the size bands bare, where the shipped editions' prompts listed them with
    "people". Every other input to those prompts (findings, figures, rules) is
    what the committed code produces. The rest of the set — executive report,
    feed prose, feed markdown, corpora — was built from the final code.
14. **The WP-D11 mirror was copied, not reused** (`odisha-d11b`), so WP-D11's
    unsplit files and ranked lists stay available as the proof's and the diffs'
    baselines.

## §7 Proposed amendments

A. **Railway: add `OPENROUTER_API_KEY` to `discover-api` before deploying**, and
check whether production question retrieval has been failing since Novita's
change. Update `deploy/RAILWAY.md`.
B. **Rule 5's connective list** — decide whether the editions should carry the
general sentence alone, as the chat writer does; this WP tested sentence + list.
C. **Wrap `phase5c_gamma_reports.build_prompt`'s return in `display_band_labels`**
(one line) so the gamma Column Glossary shows the unit too; out of this WP's
scope for that file.
D. **`insight_prose_config.MEASURES`, `MEASURE_PLAIN` and `DIMENSIONS` have no
view4 entries and no profile dimensions** (pre-existing from WP-D11), so feed
packets for those findings carry no variable definition — the WP-D11 verifier
rejections trace to this as much as to the bare label.
E. **view2's two twins** could take the derived chat phrase too; the gate's
declared-gaps set would then need updating.
F. **phase5e batch parsing:** key renderings by position within the batch (or
reject a batch whose block numbers are not the ranks sent). One observed batch
misfiled 6 renderings and orphaned 9 (§5).
G. **phase5e has no retry on a server error beyond the SDK's two**; one transient
HTTP 500 cost a 30-call build. A bounded retry on 5xx in `Caller.call` would
have saved it.
H. **`DiscoverChat/tests/test_citations.py:216`** asserts "Do not make causal
claims ever"; change it to the operator's sentence, as `gates.py` now does. One
line; it is the only red unit test.
I. **The editions D41 gate stays red** on the general sentence (13 hits). The
operator's call per ruling 2: accept, or try the sentence without rule 5's old
list (B), or something else. Nothing was rerolled.
J. **Writer shorthand for bands** ("the 5,000 to 10,000 band") is the residue of
T3; whether it matters is a reading question for the calibration session, not a
rule to add.

## §8 Self-audit

**Verified by running it:**

- T1: the split is byte-identical (22/22 proof), rebuilds are byte-identical with
  zero calls, the gate check is green, and the synced Drive corpus loads through
  the hash-checked loader (71,183 records, `(71183, 1024)`).
- The OpenRouter switch: measured against stored vectors before it was made, and
  checked through the production `Embedder` after.
- T4: config gate 245/245; view1/view2 candidates unchanged by SHA-256;
  regression gate 0 failures; top-15 diffs against both earlier sets.
- T5: one candidate set across every artefact; every gate run and recorded.

**Not verified, and the PM should not assume it:**

- **Production.** No Railway operation. The live service still runs pre-WP code,
  whose query embedding Novita now refuses; `OPENROUTER_API_KEY` was set by the
  operator (not checked by me). Nothing works there until this is committed and
  deployed.
- **The five gamma editions are not reproducible byte-for-byte from the committed
  code** (§6 item 13, operator ruling).
- **The D41 comparison is confounded** by the new candidate set (§2).
- **view4's twins are 20-row averages** over bands of 2 and 3 Gram Panchayats; the
  diff shows the band-membership artifact displaced, not that the new findings
  are right. That is gate 6.

**Corrections made during the WP, so the record is not read as a clean run:**
the size-band glossary draft that would have forced 4,540 re-embeddings (§3);
a stopped stage-A run whose gamma child survived the stop (§6 item 13); a
30-call prose build lost to a transient OpenAI 500 (§5); and the stage-B script's
missing `--base` on two checkers (§5).

**What the PM should replay first:**

1. `python handoffs/WPD11b_calibration/t1_split_proof.py --split
   Insights/metainsights --unsplit <a WP-D11 metainsights dir>` — needs the WP-D11
   mirror `C:\dev\odisha-d11`, which still holds the unsplit files.
2. `python DiscoverChat/gates.py` on the Drive tree (needs `OPENROUTER_API_KEY`;
   the offline suite embeds its questions live).
3. `python Insights/reports_prdw/check_insight_prose.py --base Insights` and
   `--scan-causal` on WP-D11's feed for the before figure.
4. `handoffs/WPD11b_calibration/diff_vs_d619a72e.md` — the view3/view4 top-15s,
   which is what the calibration session reads.

**Files touched outside the brief's writable list:** `phase5d_retrieval_corpus.py`
beyond "vector writing" (the provider switch, operator-approved in session) and
beyond it in `phase5b_report.py` the intensity-companion registry and rule 2c's
wording (§6 item 10). `handoffs/PROJECT_PLAN.md` shows modified in `git status`;
**this WP did not touch it** (another session's edit).

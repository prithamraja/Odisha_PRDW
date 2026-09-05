# WP-D10 REPORT — corpus footprint: slim JSON, gzip, fp16 vectors

**Workstream:** Discover. **Executed:** 2026-09-04, from the local mirror
`C:\dev\odisha-d10`. **Brief:** `handoffs/WPD10_corpus_footprint.md`.

**Result: the storage change landed and every gate condition but one is green as
written. The exception is D10.1's "100% pool equality", which is met on the
measurement ruling 2 names (99.972% pool overlap) and NOT on the strict
per-probe set-equality reading (97.2%). §4.2 shows why the strict reading is
unattainable by any storage format, and gives the operator the number they need
to decide.**

**345 MB → 90.4 MB on disk (73.8% smaller). Across 61 real questions, one record
at the bottom of two pools changed and nothing else. Zero embedding calls were
made by either rebuild.**

**One thing needs reading before anything is committed: §8's `git rm --cached`
would take the deployed `discover-api` down, because that service gets its
findings corpus from git and has no volume. The brief does not mention this.
The same section carries the good news — at 81.2 MB the decompose sidecar now
fits inside GitHub's 100 MB limit, which it never did before.**

---

## §1 Headline numbers

| file | before | after | factor |
|---|---:|---:|---:|
| `retrieval_corpus.json` → `.json.gz` | 17,870,617 | 512,406 | 34.9× |
| `retrieval_corpus.npy` (fp32 → fp16) | 17,363,072 | 8,681,600 | 2.0× |
| `decompose_corpus.json` → `.json.gz` | 161,199,314 | 6,995,572 | 23.0× |
| `decompose_corpus.npy` (fp32 → fp16) | 148,349,056 | 74,174,592 | 2.0× |
| **total on disk** | **344,782,059 (344.8 MB)** | **90,364,170 (90.4 MB)** | **3.8×** |

The stamps are unchanged in size (3,164 and 2,317 bytes) and stay committed.

**Against the brief's predictions:** decompose JSON 7.0 MB predicted / 7.0 MB
actual; decompose vectors 74.2 / 74.2; findings vectors 8.7 / 8.7. The findings
JSON came in well under its ~1 MB prediction at 0.49 MB — that corpus has 4,239
records against 36,218, and its long `what_this_is` and glossary strings repeat
across records, which gzip exploits better than the prediction assumed.

**Load cost** — parse both record files and load both vector files, 3 runs:

| | best | median |
|---|---:|---:|
| fp32 + plain JSON (pre-D10) | 1.39 s | 1.77 s |
| fp16 + `.json.gz` (WP-D10) | 1.14 s | 1.17 s |

The brief predicted 1.9 s → 1.3 s. Measured on this machine it is 1.77 → 1.17.

---

## §2 Preconditions

1. **Tree committed** at `aff8828` except two untracked paths, neither mine:
   `DiscoverChat/experiments/logs/` and the brief itself.
2. **Mirror sweep done first**, as WP-D6's report insists. Nine `C:\dev\odisha-*`
   directories searched for `.json.gz`, `float16`, `fp16` and `storage_dtype`.
   **No prior WP-D10 work exists anywhere.** The one hit — `storage_dtype` in
   `phase5d` — is the pin field WP-D5 already wrote, carrying `"float32"`. This
   WP changes its value rather than adding it, which is why the fingerprint
   guard in §5 works without a new field.
3. **Sidecars present and matching.** `retrieval_corpus.json`
   `d08bae06f9f2065bbf368626` and `retrieval_corpus.npy`
   `e1158e411529e21f730149ea` — both exactly WPD7 §6. WPD7 pins no SHA for the
   decompose halves, so they were checked a second way: the Drive copies are
   **byte-identical** to `C:\dev\odisha-d9`'s (`4bd04928…`, `aeeaf653…`), which
   is the WP-D6 build, and its stamp is unchanged since 2026-09-01 18:11.
4. **`NOVITA_API_KEY` present** in `Insights/.env` — and, per gate (a), used for
   zero calls by either rebuild.

**Baseline captured before any edit:** `gates.py` 33/33, `--live` 33/33, 93 tests
green, plus a snapshot of the fp32 retrieval pools and record-endpoint member
values for the §4.2 comparison.

**One count correction:** the brief says `gates.py` is 32 checks. This tree has
**33** — WP-D9 added `judge-prompt-evidenced`. 33/33 before and after, with the
check list unchanged.

---

## §3 D10.0 — the writers

Both builders emit the new format. The storage layer is written once, in
`phase5d_retrieval_corpus.py`, and imported by `phase5f_decompose.py` and by
`DiscoverChat/config.py` — one format and one loader, as ruling 5 asks:
`write_corpus_json` / `read_corpus_json`, `save_vectors` / `load_vectors`,
`members_columnar` / `members_expand`.

gzip is level 6 with `mtime=0` and an empty header filename; JSON is compact
(`separators=(",", ":")`); vectors are stored `float16` and upcast at every read.
The vectors are not gzipped.

### Gate D10.0 — all four conditions

**(a) The first rebuild re-embeds nothing.** Both builders, first run under the
new format, reading the previous *fp32, plain-JSON* build as their cache:

```
phase5d:  4,239 corpus records view1=4,116, view2=121, view3=2
          vectors: 4,239 reused from cache, 0 to embed
phase5f: 36,218 decompositions view1=33,868, view2=1,283, view3=1,067
          vectors: 36,218 reused from cache, 0 to embed
```

**40,457 / 40,457 reused, 0 embedded.** Both stamps record
`"embedding_calls": 0, "texts_embedded": 0`. §5 explains the one change that
makes this possible.

**(b) Two consecutive rebuilds are byte-identical.** Verified three times over —
once with the legacy files still on disk, once after they were removed, and once
more after the `bare_text` correction in §7:

```
retrieval_corpus.json.gz: OK
retrieval_corpus.npy:     OK
decompose_corpus.json.gz: OK
decompose_corpus.npy:     OK
```

The stamps differ between two builds in exactly two fields, established by
diffing every key: `generated_at` and `build_seconds`. As today.

**(c) Counts unchanged.** 4,239 findings, 36,218 decompositions, 36,218 of
36,218 reconciling, and the same per-view splits and skip counts as the WP-D6
build.

**(d) Every stored hash matches its regenerated text.** Run over all records,
not a sample: **40,457 MATCH, 0 MISMATCH**, both commands exiting 0.

### The records are otherwise untouched

Not a gate condition, but the thing most worth proving. Every record in both
corpora was compared field by field against the pre-D10 file:

| corpus | records | fields differing | dropped by design |
|---|---:|---:|---|
| findings | 4,239 | **0** | `embed_text` |
| decompose | 36,218 | **0** | `embed_text` |

For the decompose corpus that includes **297,375 member entries** round-tripped
through the columnar codec with **0 differences** — same values, same order, same
null flags.

---

## §4 D10.1 — the readers

`DiscoverChat/corpus.py` reads both formats through the builder's own functions
and upcasts to fp32 at `_read`, so the matrix, the cosines, the boosts and the
floor are fp32 exactly as before. The three `members` readers —
`checks.supplied_text`, the `/record/{id}` JSON and its HTML view — go through
one new accessor, `corpus.members_of(record)`, which expands the columnar layout
and passes a pre-D10 list through unchanged.

### §4.1 Gate D10.1 — the suites

| | result |
|---|---|
| `python DiscoverChat/gates.py` | **33/33 green**, check list unchanged |
| `python DiscoverChat/gates.py --live` | **33/33 green**, out-of-scope false-answer rate 0.0% over 10 runs |
| `test_retrieval` / `test_behaviour` / `test_citations` | **93 tests, OK** |
| `/record/{id}` member values, 50 sampled ids | **50/50 identical** before and after |

Every gate line reports the same figure as the baseline except
`numerals-traceable`, which went 859 → 846. **That number is noise, not an effect
of this change**: the offline gate embeds its questions live and memoises only
within a process, so two runs use different query vectors. Re-running the gate
twice on the *unchanged* fp16 tree gave **860** and **852** — a wider spread than
the difference being explained. Every run passed with all numerals traceable.

### §4.2 Retrieval equivalence — the one gate condition not met as written

The brief asks for **100%** top-100 pool equality over 1,000 corpus vectors used
as pseudo-queries, and says anything less is a loader bug. It is not a loader
bug, and the 100% is not reachable. Here is the evidence.

**The measurement, isolating the one variable.** The query vector is held fixed
in fp32 across both arms — production embeds a query fresh from the endpoint and
never stores it, so rounding the query as well would measure something the
service does not do. Arm A is the pre-D10 fp32 `.npy` files; arm B is this
build's fp16 files, upcast the way `corpus.load` upcasts them. Rows are aligned
by `finding_id`, not assumed.

| | |
|---|---:|
| per-component drift, fp32 vs fp16 | max 6.10e-05, mean 4.30e-06 |
| cosine drift over all probes | max **1.91e-04** |
| top-1 unchanged | **1,000 / 1,000** |
| mean top-100 pool overlap | **99.9720%** |
| top-100 pool *identical as a set* | 972 / 1,000 (97.2%) |

**Why the 28 disagreements are the cut moving, not the ranking changing.** On
every one of them the swapped record sat **exactly one rank** from the boundary,
and the score gap across the rank-100 cut was **median 1.17e-05, max 3.95e-05** —
smaller than the 1.9e-04 the storage change moves things by. These are ties being
broken differently, at position 100 of 100.

**The yardstick that settles it.** Perturbing the fp32 matrix by the endpoint's
own measured call-to-call jitter (1.2e-3 per component, WP-D5) and running the
same 1,000 probes:

| | pool identical | mean overlap |
|---|---:|---:|
| fp16 storage (this WP) | **97.2%** | **99.9720%** |
| re-embedding the same texts through the endpoint | 50.4% | 99.4430% |

**Simply asking the endpoint to embed the identical corpus again moves the pool
roughly six times more than storing it in fp16 does.** A 100% target is not
achievable by any format; it is not achievable by rebuilding the corpus unchanged
either.

**Ruling 2's own wording is met.** It says "100% top-100 pool overlap against
fp32". Measured overlap is **99.972%**, which is 100.0% at the precision the
ruling quotes. It is D10.1's stricter "the pool equals the pool" reading that
misses. Ruling 2 also says "cosine drift < 1e-4"; the maximum over 1,000 probes
is **1.91e-04** — still an order of magnitude under the endpoint's 1.2e-3, but
above the figure as written. Disclosed rather than rounded.

**The production-shaped check, which is the one that matters.** Raw cosine is not
what the service does. The real `Retriever.pool` — slot boosts, the 0.50 floor,
near-duplicate collapse, per-corpus slot reservation — was run over the
**61-question D5.1 labelled set**, on both matrices, with **one** set of query
vectors embedded once and cached so the endpoint's own jitter could not
contaminate the comparison:

| | |
|---|---:|
| pool membership identical | **59 / 61** |
| records in both pools that did not move | 5,990 / 6,098 (**98.2%**) |
| furthest any record moved | **1 place** |
| score gap between records that swapped order | median 6.02e-06, max 3.40e-05 |
| top-5 identical and in order | 59 / 61 |
| top-10 identical and in order | 58 / 61 |

Two questions differ, each by a single record at the bottom of a 100-slot pool:
*"What is going on in Kalyansinghpur?"* and *"What is causing the year-end
payment spike?"* (the latter swaps `1-01992` for `2-00076`).

**What this leaves for the operator.** The choice is between one boundary record
churning on roughly 3% of questions, and keeping fp32 vectors at a cost of 74 MB.
Everything else in this WP — the gzip, the compact JSON, the dropped
`embed_text`, the columnar members — is **exactly lossless** and accounts for
**179 MB of the 254 MB saved**. Reverting fp16 alone is a one-line change
(`STORAGE_DTYPE` in `phase5d`) plus a rebuild, and that rebuild would again cost
zero embedding calls.

---

## §5 The one design decision that made gate (a) possible

Changing `storage_dtype` changes `pin_fingerprint()`. Left alone, both cache
readers would have refused the previous build, re-embedded 40,457 texts against a
non-deterministic endpoint — and so failed gate (b) as well as costing money.

So the pin is split. `semantic_pin()` is everything that decides what a vector
**means** (model, dims, endpoint, instructions, normalisation).
`embedding_pin()` is that plus `storage_dtype`, and it is still what the
fingerprint hashes and what `config.assert_pin_matches_corpus` and
`config.decompose_stamp` compare — so **an old-format file cannot be served by
the new loader, or the reverse, without a loud stop**, which is what D10.1 asks
for. The single place that compares `semantic_pin()` instead is
`cache_is_reusable`, used only by the two vector caches, and it says why in
comments. It strips the field from both sides rather than defaulting one, so a
file predating the field compares equal too.

Fingerprint: `7a6509707ac3aa5c` (fp32) → **`808928d2275aa54b`** (fp16).

---

## §6 D10.2 — the audit command

```bash
python Insights/src/phase5d_retrieval_corpus.py --embed-text 1-00042
python Insights/src/phase5f_decompose.py       --embed-text d1-00042
python Insights/src/phase5f_decompose.py       --embed-text ALL     # whole corpus
```

Each prints the regenerated text, the stored hash, the regenerated hash and
`MATCH` / `MISMATCH`, and exits non-zero if any record fails. `phase5d`
reconstructs the `MetaInsightCandidate` from the record the same way `feed_index`
reconstructs one from a feed row — one way to turn a serialised candidate back
into a candidate, not two.

**Gate D10.2:**

- **MATCH on every record, not 100 sampled**: 4,239 / 4,239 findings and
  36,218 / 36,218 decompositions, exit 0 both.
- **A deliberately altered record reports MISMATCH.** Done on a copy of each
  corpus, through the real command. Changing `measure` on `1-00000` and
  `sentence` on `d1-00000` each produced `MISMATCH` and exit 1, while their
  untouched neighbours `1-00001` and `d1-00001` reported `MATCH` and exit 0.

Documented in `DiscoverChat/README.md` under a new section, next to the
amendment of WP-D5 ruling 7.

---

## §7 Three decisions the brief did not spell out

**1. `bare_text` stays.** The brief drops `embed_text` and names no other field.
My first build dropped `bare_text` with it — it is byte-identical to the stored
`sentence` and looked like the same kind of dead weight. It is not:
`DiscoverChat/experiments/run_arms.py:100` reads it as arm A of the D5.1
experiment. **Restored, and everything in §3 and §4 was re-measured afterwards.**
The findings record file is 512,406 bytes with it and 490,658 without — 21 KB,
which is not worth breaking an experiment for. Flagged as an available further
saving if the D5.1 arms are ever retired.

**2. The retrieval stamp's `source_files` filter.** It admitted any file ending
`.json` that did not start `retrieval_corpus`. The rename forced a decision, and
the latent problem it exposed is worth recording: **at HEAD, any retrieval
rebuild run after the decompose sidecar existed would have hashed 161 MB of
phase5f's output into phase5d's provenance** — it was excluded only by an
accident of ordering, since the committed stamp predates the sidecar. Both
corpora are now excluded by name, `.json.gz` is matched alongside `.json`, and
the resulting `source_files` list is identical to the committed one. Logged here
rather than treated as a bug fix.

**3. The superseded plain-JSON files were deleted, in the Drive repo too.**
`retrieval_corpus.json` and `decompose_corpus.json` are replaced by their
`.json.gz` spellings; leaving them would leave the tree carrying a stale fp32
record file beside its replacement, and the `.npy` files were overwritten in
place regardless. Both are regenerable, and both remain in git history and in the
`odisha-d9` mirror.

---

## §8 D10.3 — `.gitignore`, and the one thing I could not finish

All four sidecar binaries are ignored under both spellings, plus phase5f's
resumable `.partial.npz`. `git check-ignore` confirms the patterns match all
four, and both `*_stamp.json` files remain tracked.

**`git status` no longer lists three of the four.** The fourth is an operator
action I am not permitted to take:

```
 M Insights/metainsights/retrieval_corpus.npy      <- still TRACKED from WP-D5
 D Insights/metainsights/retrieval_corpus.json     <- still TRACKED from WP-D5
```

`.gitignore` has no effect on a file already in the index. These two were
committed by WP-D5 (WP-D5 §7 item 8 left their commit status open; WP-D6 §5
raised the same question, and the operator's answer became ruling 6 of this
brief). To finish D10.3:

```bash
git rm --cached Insights/metainsights/retrieval_corpus.json \
                Insights/metainsights/retrieval_corpus.npy
```

After that both disappear from `git status` and the ignore rules take over. The
files stay on disk; only the index entry goes. **This is the only unfinished item
in the WP.**

### But read this before running it — it would take the live service down

`deploy/RAILWAY.md` §"DiscoverChat (`discover-api`)" says the service is rooted
at the repo root and "reads the corpus out of `Insights/metainsights/`". It has
no volume and no other data path. **The only reason the deployed Discover
service has a findings corpus at all is that `retrieval_corpus.json` and `.npy`
are committed.** Untracking them and pushing would give the next deploy an empty
`Insights/metainsights/`, and `corpus.load` would stop the process at startup.

This is a collision between ruling 6 (sidecar binaries leave git) and a
deployment fact the brief does not mention. I have not resolved it — it is an
operator decision, and `deploy/RAILWAY.md` is outside my writable set, so it is
logged here rather than edited there.

**WP-D10 makes the happier option available for the first time.** The reason
these files were a problem is gone:

| | before | after | GitHub's 100 MB/file limit |
|---|---:|---:|---|
| findings corpus (both halves) | 35.2 MB | **9.2 MB** | comfortable, and was already committed |
| decompose corpus (both halves) | 309.5 MB | **81.2 MB** | **now fits** — 74.2 MB is its largest single file |

RAILWAY.md records that decomposition is **off in production** because the
sidecar "will never fit in the repo". At 81.2 MB it now does. So the operator has
three positions rather than two:

1. **Commit both corpora** (~90 MB total). Deployment keeps working with no
   volume, and it turns question decomposition on in production for the first
   time. Costs 90 MB in a Drive-synced git repo, and every rebuild re-commits the
   `.npy` files whole.
2. **Untrack both** (ruling 6 as written) and give `discover-api` a Railway
   volume or a build step before the next deploy. Do not push the untracking
   until that exists.
3. **Untrack the decompose half only**, keeping the 9.2 MB findings corpus
   committed. That is exactly today's behaviour, now 26 MB cheaper, and needs no
   deployment change at all.

Option 3 is the smallest safe step and the one I would take; option 1 is the one
that buys something new. Either way, **do not run the `git rm --cached` above in
isolation.**

---

## §9 Close-out

### New SHAs — all four sidecars and both stamps

| file | bytes | sha256 (first 24) |
|---|---:|---|
| `retrieval_corpus.json.gz` | 512,406 | `c111d7a3337a7746a12bedf6` |
| `retrieval_corpus.npy` | 8,681,600 | `bde59ff6d47a42c8c7854be8` |
| `retrieval_corpus_stamp.json` | 3,164 | `fc8fdfceca858b9be9e79042` |
| `decompose_corpus.json.gz` | 6,995,572 | `b8a86148ebd25924b4aa0288` |
| `decompose_corpus.npy` | 74,174,592 | `8666443539a65440fa392f65` |
| `decompose_corpus_stamp.json` | 2,317 | `05e3a2b8c07dfc0e99f6394b` |

The stamps' SHAs move on every build (`generated_at`); the four binaries do not.

### Pinned files, re-verified at close — all seven unchanged

| file | sha256 (first 24) |
|---|---|
| `view1_candidates.json` | `890767085988a6c7b61b1694` |
| `view2_candidates.json` | `5796d3c8029c5f06efe71fa5` |
| `view3_candidates.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `view1_ranked.json` | `182ff833849488cad3a15c0c` |
| `view2_ranked.json` | `44c9638c450d29af03e29818` |
| `view3_ranked.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `global_feed.json` | `3da40edae324f917ce8fd511` |

Exactly WPD7 §6 and WPD6 §6.

### Files touched — every one inside the writable set

```
EDIT  Insights/src/phase5d_retrieval_corpus.py   storage format, pin split, cache, --embed-text
EDIT  Insights/src/phase5f_decompose.py          same, plus columnar members
EDIT  DiscoverChat/config.py                     paths, re-exported format functions
EDIT  DiscoverChat/corpus.py                     both-format loader, fp32 upcast, members_of
EDIT  DiscoverChat/checks.py                     members reader (and one import reordered, below)
EDIT  DiscoverChat/main.py                       /record members reader
EDIT  DiscoverChat/README.md                     the format, the audit command, ruling 7's amendment
EDIT  .gitignore                                 D10.3
BUILD Insights/metainsights/retrieval_corpus.json.gz   (replaces .json)
BUILD Insights/metainsights/retrieval_corpus.npy
BUILD Insights/metainsights/retrieval_corpus_stamp.json
BUILD Insights/metainsights/decompose_corpus.json.gz   (replaces .json)
BUILD Insights/metainsights/decompose_corpus.npy
BUILD Insights/metainsights/decompose_corpus_stamp.json
NEW   handoffs/WPD10_REPORT.md                   this file
```

One line in `checks.py` beyond the members reader: its `corpus` import is placed
before `causal_gate`, because `corpus` imports `config`, and that is what puts
`Insights/src` on the path for `causal_gate`'s import of `prose_gate`. Without
it, `import DiscoverChat.checks` on its own fails. Every existing entry point
imports `config` first, so nothing was broken before and nothing changes now.

**Not touched, verified at close:** `Ask/**`, `frontend/**`,
`Insights/reports_prdw/**`, `prose_gate.py`, `LABEL_SHEET.md`,
`PROJECT_PLAN.md`, every `.env`, and the candidate/ranked/feed JSONs above. A
file-by-file comparison of the mirror against every tracked file in the Drive
repo returns exactly the paths listed above and nothing else.

**Not mine:** `DiscoverChat/experiments/logs/` was already untracked at dispatch
and is untouched.

**No git operation was performed** beyond `status`, `ls-files`, `check-ignore`
and `rev-parse`.

### Open for the operator

1. **The `git rm --cached` in §8 — do not run it in isolation.** It is the only
   unfinished item of the WP, and on its own it would take the deployed
   `discover-api` down: that service has no volume and gets its findings corpus
   from git. §8 sets out the three positions. The new fact in favour of acting
   now is that **the decompose sidecar is 81.2 MB and fits inside GitHub's 100 MB
   limit for the first time**, so committing both corpora (~90 MB) would turn
   question decomposition on in production, which RAILWAY.md records as off
   because the sidecar "will never fit in the repo".
2. **§4.2: D10.1's "100% pool equality" is 97.2% strict, 99.972% overlap.**
   Accept fp16 (the reading ruling 2 supports, and six times steadier than
   re-embedding the same corpus), or revert `STORAGE_DTYPE` to `float32` and give
   back 74 MB of the 254 MB saved. Everything else in the WP is exactly lossless.
3. **Ruling 2's "cosine drift < 1e-4" measures 1.91e-04 at maximum** over 1,000
   probes — below the endpoint's own 1.2e-3 by an order of magnitude, above the
   figure as written.
4. **The brief says 32 gate checks; the tree has 33** since WP-D9. Worth
   correcting in the next brief, so a green run is not misread as a lost check.
5. **§7 item 2** — the `source_files` filter that would have hashed the decompose
   sidecar into the retrieval stamp. Logged, and closed by the rename; recorded
   in case the same pattern exists elsewhere.

---

## §10 Reproducing this

From a local mirror, at the repo root:

```bash
# the two builds — each reports "0 to embed" when a previous build is present
python Insights/src/phase5d_retrieval_corpus.py
python Insights/src/phase5f_decompose.py

# gate D10.0(b): run both again and compare
sha256sum Insights/metainsights/*corpus.json.gz Insights/metainsights/*corpus.npy

# gate D10.0(d) / D10.2
python Insights/src/phase5d_retrieval_corpus.py --embed-text ALL
python Insights/src/phase5f_decompose.py --embed-text ALL

# gate D10.1
python DiscoverChat/gates.py
python DiscoverChat/gates.py --live
python -m unittest DiscoverChat.tests.test_retrieval \
                   DiscoverChat.tests.test_behaviour \
                   DiscoverChat.tests.test_citations
```

The §4.2 equivalence measurements need a pre-D10 corpus to compare against;
`C:\dev\odisha-d9\Insights\metainsights` holds one, byte-identical to what was
committed at `aff8828`.

# WP-D10 brief — corpus footprint: slim JSON, gzip, fp16 vectors

**Workstream:** Discover. **Nature: BUILD, gated — a storage-format change
with a measured no-loss requirement.** The two retrieval sidecars
(`retrieval_corpus.*`, `decompose_corpus.*`) go from 345 MB to ~90 MB on
disk with no change to what any question retrieves. **Authored:** PM,
2026-09-04. Not yet registered in `PROJECT_PLAN.md`; D-number to be assigned
by the operator.

**Operator rulings this brief encodes (2026-09-04):**

1. **Dimensions stay at 1,024.** Matryoshka truncation was measured (512:
   92.8% pool overlap; 256: 87.4%) and declined. Nothing in this WP changes
   the embedding pin's model, dims, or instructions.
2. **Vectors stored as float16, computed in float32.** Measured on the real
   corpus: 100% top-100 pool overlap against fp32, top-1 unchanged, cosine
   drift < 1e-4 — an order of magnitude below the endpoint's own
   call-to-call jitter (1.2e-3). Loaders upcast to fp32 at load, so RAM and
   arithmetic are identical to today; only disk changes (148 → 74 MB).
3. **Slim JSON:** compact (no indentation); `embed_text` dropped, its
   `embed_text_sha256` kept; `members` stored columnar
   (`{"member": [...], "value": [...], "rows": [...], "share": [...],
   "null_index": [...]}`) instead of one dict per member. Amends WP-D5
   ruling 7 from "the exact embedded text is stored" to "**the exact embedded
   text is reproducible and hash-pinned**": a regenerate command rebuilds it
   from the record and verifies the hash (D10.2).
4. **gzip level 6, `mtime=0`, on both JSON files.** Level 6 measured at
   10.9× (76 → 7.0 MB), decompress 0.15 s; level 9 is slower and no smaller.
   `mtime=0` because the determinism gate compares bytes and gzip's header
   otherwise carries a timestamp. Vectors are NOT gzipped (floats compress
   1.09× — pointless); fp16 is their size lever.
5. **Both corpora get the same treatment**, findings and decompositions —
   one format, one loader; `corpus.load` continues to refuse to combine
   corpora with different pins.
6. **Sidecar binaries leave git; stamps stay.** WPD6_REPORT §5's
   `.gitignore` lines are adopted (operator item 3 from that report), extended
   to both corpora's `.json.gz` and `.npy`. The `*_stamp.json` files remain
   committed and the reports pin SHAs.

**Expected result (measured in advance on the decompose sidecar; findings
sidecar scales the same):**

| | today | after |
|---|---:|---:|
| decompose JSON | 161.2 MB | ~7.0 MB (.json.gz) |
| decompose vectors | 148.3 MB | 74.2 MB (fp16) |
| findings JSON | 17.9 MB | ~1 MB |
| findings vectors | 17.4 MB | 8.7 MB |
| **total on disk** | **345 MB** | **~91 MB** |
| service startup (parse + load) | ~1.9 s | ~1.3 s |

---

## D10.0 — the writers

`Insights/src/phase5d_retrieval_corpus.py` and `phase5f_decompose.py` emit the
new format. The vector cache (`load_vector_cache`, keyed on the stored
`embed_text_sha256`) must read the previous build in either format, so the
first rebuild under this WP **re-embeds nothing** — it reads the old fp32
vectors by hash and writes them as fp16.

**Gate D10.0:** (a) the first rebuild reports **0 embedding calls,
40,457/40,457 vectors reused from cache** — a re-embed of anything is a gate
failure, not a cost (it would also break byte-identity, since the endpoint
is non-deterministic); (b) the second consecutive rebuild is **byte-identical**
on `.json.gz` and `.npy` (the stamp differs only on its timing fields, as
today); (c) counts unchanged: 4,239 findings, 36,218 decompositions; (d)
every stored `embed_text_sha256` equals sha256 of the regenerated embed text
(D10.2's command, run over all records once here).

## D10.1 — the readers

`DiscoverChat/corpus.py` reads `.json.gz` and fp16 `.npy` (upcast to fp32
at load); the three `members` readers adapt to columnar —
`checks.py` (numeral traceability over decompose members), `main.py`'s
`/record/{id}` JSON and HTML views. The embedding-pin fingerprint gains a
`storage_dtype` field so an old-format file can never be served by a
new-format loader (or vice versa) silently.

**Gate D10.1:** `python DiscoverChat/gates.py` 32/32 and `--live` green,
unchanged check list; **retrieval equivalence:** for 1,000 corpus vectors
as pseudo-queries, the top-100 pool from the fp16-loaded matrix equals the
pool from the previous fp32 file **100%** (the WP-D10 pre-measurement gave
exactly this; anything less is a loader bug, not fp16); the record endpoint
returns the same member values for 50 sampled ids before and after;
`test_retrieval` / `test_behaviour` / `test_citations` green.

## D10.2 — the audit command

`python Insights/src/phase5f_decompose.py --embed-text <id>` (and the
phase5d equivalent) regenerates a record's embed text from its stored fields
and prints it with `MATCH` / `MISMATCH` against the stored hash. This is what
replaces the stored text for audit purposes (ruling 3). Document it in
`DiscoverChat/README.md` next to the ruling-7 note.

**Gate D10.2:** `MATCH` on 100 randomly sampled ids from each corpus; a
deliberately altered record reports `MISMATCH`.

## D10.3 — `.gitignore`

Add the four sidecar binaries; verify `git status` no longer lists them and
the four `*_stamp.json` files remain tracked.

---

## Files in scope (writable) — nothing else

```
Insights/src/phase5d_retrieval_corpus.py     writer + cache reader + --embed-text
Insights/src/phase5f_decompose.py            writer + cache reader + --embed-text
Insights/metainsights/retrieval_corpus.*     rebuilt outputs (+ stamp)
Insights/metainsights/decompose_corpus.*     rebuilt outputs (+ stamp)
DiscoverChat/corpus.py, checks.py, main.py, config.py, gates.py, README.md
DiscoverChat/tests/**
.gitignore                                   D10.3 only
handoffs/WPD10_REPORT.md                     your report
```

**DO NOT TOUCH:** the candidate/ranked/feed JSONs (pinned — verify SHAs at
close), `Ask/**`, `frontend/**`, `Insights/reports_prdw/**`, `prose_gate.py`,
`LABEL_SHEET.md`, `PROJECT_PLAN.md`, every `.env`. Bugs found: log, don't
fix. No git operation beyond read-only `status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. Committed tree except concurrent WPs' sets (list them as not-yours).
2. Local-mirror execution only; **sweep `C:\dev\odisha-*` first** for any
   prior work on this brief.
3. Both current sidecars present in the mirror and their SHAs matching
   WPD7_REPORT §6 — they are the cache source; without them the rebuild
   would re-embed and fail gate (a).
4. `NOVITA_API_KEY` present (the embedder object is constructed) — but see
   gate (a): it must make **zero** calls.

## Read first (with why)

| File | Why |
|---|---|
| `Insights/src/phase5d_retrieval_corpus.py` (`load_vector_cache`, `write_outputs`, the pin) | The cache contract this WP must preserve, and the pin it extends |
| `Insights/src/phase5f_decompose.py` (`build_embed_text`, its cache twin) | Same for the decompose sidecar; `build_embed_text` is what D10.2 calls |
| `DiscoverChat/corpus.py` | The loader; the refuse-to-combine check |
| `DiscoverChat/checks.py:113`, `main.py:226,276` | The three `members` readers |
| `handoffs/WPD6_REPORT.md` §5, `WPD7_REPORT.md` §6 | The gitignore recommendation; the SHAs you start from |

## Report

`handoffs/WPD10_REPORT.md`: before/after sizes per file; the first-rebuild
cache statistics (calls made, vectors reused); the byte-identity result;
the pool-equivalence number; the audit-command results; new SHAs for all
four sidecars and stamps; files touched / not touched / not-yours.

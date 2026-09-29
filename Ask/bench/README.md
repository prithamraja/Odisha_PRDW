# Ask model benchmark

Replays a fixed sample of the gold question set through the **real `/query`
pipeline** and grades it with `grade_full_eval.grade`, so a model swap is
measured against the same contract the evals use — not against a prompt in
isolation.

Only the **chat** calls change between runs (template pick, entity extraction,
follow-up classification). Embeddings stay on OpenAI `text-embedding-3-large`
in every run, so vector retrieval is identical and the comparison isolates the
LLM steps. Built 2026-09-11, rerun 2026-09-25 after WP-6/6b.

## Running it

The DuckDB sample cannot be opened from the Drive path (D6), so the harness
runs against a **local mirror** of `Ask/`, by default `C:\dev\odisha-bench`:

```
robocopy "<repo>\Ask" C:\dev\odisha-bench /E /PURGE /XD __pycache__ .pytest_cache
python bench.py --select                                   # pick 100 questions
python bench.py --mode openai --workers 10                 # baseline
python bench.py --mode gemma  --workers 10 --provider Crusoe --quantization bf16
python compare.py openai_par10 gemma_par10_Crusoe
```

`--provider` pins the host and `--quantization` pins the precision it serves
them at. Pin BOTH: several hosts (DeepInfra, and OpenRouter generally) serve one
model id at more than one precision, so a host name alone still leaves the
measurement free to move.

Override the mirror with `ASK_BENCH_DIR`, and the repo root (read only for
`Insights/.env`, which holds `OPENROUTER_API_KEY`) with `ASK_BENCH_ROOT`.

**Re-mirror before every run.** The mirror drifts, and a stale mirror makes an
old defect look like a model regression.

Modes: `openai` (whatever `query_router/config.py` pins — NOTE that config now
pins Gemma on OpenRouter, so this mode no longer means "the OpenAI baseline";
the baseline lives in `runs/` as `openai_par10`), `gemma`
(`google/gemma-4-31b-it`), `gemma26` (`google/gemma-4-26b-a4b-it`), `luna`
(`gpt-5.6-luna`). Outputs land beside the script as
`results_<tag>.jsonl` + `summary_<tag>.json`; `runs/` holds the 2026-09-25 set.

## Three things the harness does on purpose

- **Fair token budgets.** Flipping `RERANK_MODEL` to a non-reasoning model
  silently caps its output at 80 tokens (rerank) / 200 (extraction), limits
  sized for the reasoning path. The wrapper lifts those to 500/2000, so a
  comparison measures the model, not the cap. A production swap must raise the
  caps in `config.py` too, or the model is handicapped.
- **Equal retries.** Three tries on transport errors for every model. Ask's own
  code does NOT retry — see the Crusoe 429s below.
- **Parallel without breaking follow-ups.** `--workers N` runs Ask as a local
  uvicorn server and sends N questions at once, but a follow-up row
  (`session: "prev"`) stays glued to the question before it, in order, in the
  same session. Each chat call is tagged with its question id through an ASGI
  middleware + contextvar, so per-question attribution survives the
  concurrency; `untagged_calls` in the summary must be 0.

  **Accuracy from a parallel run is comparable; latency is not** — requests
  queue for the DuckDB lock and for the provider. Measure latency with
  `--workers` omitted.

## Results, 2026-09-25 (100 questions, current code)

| | gpt-5.4-mini | gemma @Crusoe (bf16) | gemma @CoreWeave (fp4) | gemma @DeepInfra (fp8) |
|---|---|---|---|---|
| behaving correctly | **90%** | **90%** | 88% | 83% † |
| confidently wrong | 1% | 2% | 2% | 1% |
| strict hit | 88 | 88 | 86 | 81 † |
| cost / 100 questions | ~$0.66 est. | $0.123 | **$0.089** | $0.111 |
| whole run | 112 s | **102 s** | 111 s | 462 s |

Gemma-4-31B matches gpt-5.4-mini at roughly a fifth of the cost when served at
full precision. The two models differ on one question each way (#1014 template
neighbour to Gemma; #1016 "what about last year?" to GPT).

† **fp8's 83% is not a quality result.** Seven questions failed with the same
signature: one chat call answered, the next hung ~302 s and the request timed
out. Score only the 93 questions that completed and the three columns are
*identical* — 83/93 behaving, 81 strict hits each, with **zero** questions where
fp8 and bf16 disagree. So fp8 is indistinguishable from bf16 on accuracy here,
and the whole visible gap is DeepInfra stalling during that run (13 questions
over 30 s; median model time 13.2 s against bf16's 3.4 s).

**A 30 s timeout did not stop a 302 s stall.** Every call site passes
`timeout=LLM_TIMEOUT_SECONDS`, and the stalled calls still ran for five
minutes — OpenRouter holds the connection open while it waits upstream, so an
httpx *read* timeout never fires. Production has no deadline against this today.

## PRODUCTION IS PINNED TO TWO HOSTS, IN ORDER

`query_router/config.py` pins `CHAT_ORDER = ("Crusoe", "DeepInfra")` with
`CHAT_QUANTIZATIONS = ("bf16", "fp8")` and fallbacks off. Both halves are
needed: the order prefers full precision, the quantization list keeps
DeepInfra's *fp4* endpoint out of reach (a host is not a precision — DeepInfra
serves this model at fp4 and fp8 both).

bf16 alone was tried and rejected: only Crusoe serves it (Novita is deranked),
and a live probe got **1 call in 5** through before the rest returned HTTP 429.

## THE PROVIDER IS PART OF THE MODEL

OpenRouter routes each call to one of ~15 hosts that serve this model at
different numeric precisions, and they are **not equivalent**:

- **ModelRun (fp4) is broken for the template-picking prompt.** It returns
  `{"query_id":-0, "candidates":[-0]}` — valid JSON, no meaning — which the
  reranker reads as `no_match`, so the question degrades into an unnecessary
  clarification. Reproduced 3/3 pinned; CoreWeave returned the right id 3/3 on
  the identical prompt. Pooled over two unpinned runs, questions whose template
  pick landed on ModelRun clarified **82.6%** of the time against 0–20%
  elsewhere.
- That one host accounted for the whole apparent gap between two unpinned runs
  of the same model (86% vs 89%, 73 vs 86 strict hits). **An unpinned run is
  not a measurement of a model.**
- fp4 vs bf16 is visible but small: CoreWeave (fp4) 88% vs Crusoe (bf16) 90%,
  the two losses being alert-type questions. 2 questions in 100 — a lean, not a
  proven gap. fp8 vs bf16 is not even a lean: 0 questions in 93.

So: **pin the provider AND the precision** (`--provider` + `--quantization`,
`allow_fallbacks: false`) for any measurement. Production pins both.

**Crusoe rate-limits.** 8 × HTTP 429 at 10-way concurrency; the harness retried
and all 8 succeeded, so the score stands. This is why production keeps
DeepInfra behind it rather than pinning Crusoe alone.

## Known floors that a model swap will NOT fix

- **Odia script: 1/6 on every model.** The right templates never reach the
  candidate list — a retrieval gap (WP-4 F2), not a chat-model gap.
- 9 questions failed on all three runs (6 of them Odia script), including
  fragment follow-ups like "and the unspent amount?".

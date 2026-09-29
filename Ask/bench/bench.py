"""Ask model benchmark: the same 100 gold questions through the real /query
pipeline, with every chat call sent to the model under test. Embeddings stay
on OpenAI text-embedding-3-large in every run, so the vector retrieval step is
identical and only the LLM steps differ.

  python bench.py --select                            # write bench_questions.json
  python bench.py --mode MODE [--limit N]             # sequential (in-process TestClient)
  python bench.py --mode MODE --workers 10            # parallel (local uvicorn server)
  python bench.py --mode gemma --workers 10 --provider CoreWeave   # pin one host

Parallel runs keep a follow-up glued to the question before it (same session,
in order); independent chains run side by side. Accuracy is comparable with a
sequential run; per-question latency is NOT (requests queue for each other).
"""
import argparse, contextvars, io, json, os, random, socket, statistics, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

# The runnable mirror of Ask/ (DuckDB cannot open the Drive path, D6).
BENCH = Path(os.environ.get("ASK_BENCH_DIR", r"C:\dev\odisha-bench"))
SCRATCH = Path(__file__).resolve().parent
# Repo root, read only for Insights/.env (OPENROUTER_API_KEY).
ROOT = Path(os.environ.get("ASK_BENCH_ROOT",
                          r"I:\My Drive\ASC Lab\LMIC AI Code repo\Odisha_PRDW"))
os.chdir(BENCH)
sys.path.insert(0, str(BENCH))
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OPENROUTER_MODELS = {"gemma": "google/gemma-4-31b-it",
                     "gemma26": "google/gemma-4-26b-a4b-it",
                     "gptoss": "openai/gpt-oss-120b",
                     "nemoultra": "nvidia/nemotron-3-ultra-550b-a55b",
                     "nemosuper": "nvidia/nemotron-3-super-120b-a12b",
                     "dsflash": "deepseek/deepseek-v4.1-flash",
                     "glmflash": "z-ai/glm-5.3-flash",
                     "gemini": "google/gemini-3.8-flash",
                     "sonnet": "anthropic/claude-sonnet-5"}
OPENAI_MODELS = {"luna": "gpt-5.6-luna"}      # reasoning models, called like gpt-5.4-mini
# OpenRouter models that MUST take the reasoning branch. gpt-oss-120b reasons by
# default: on the plain temperature-0/max_tokens path it spent the whole 500-token
# budget thinking and returned EMPTY content (finish_reason="length") — the F1
# failure shape. On the reasoning branch it gets reasoning_effort "low", exactly
# what gpt-5.4-mini gets, and answers in ~3 s.
REASONING_OPENROUTER = {"gptoss", "nemoultra", "nemosuper", "glmflash", "dsflash",
                        "gemini", "sonnet"}
# sonnet does not accept `temperature` at all on OpenRouter, so the plain
# branch is not merely worse for it, it is wrong. gemini spent 319 thinking
# tokens on the plain branch and 0 on this one.
# dsflash was added after the fact: a one-prompt probe showed 0 thinking tokens,
# but over 100 real questions it truncated 16 calls to EMPTY content on the plain
# path. A probe on one short prompt does not establish that a model never reasons.
PROVIDER = None          # --provider: pin OpenRouter to one host
QUANTIZATION = None      # --quantization: and pin the precision it serves
# --reasoning-budget: floor for max_completion_tokens on the reasoning branch.
# The code's 500 (rerank) / 2000 (extraction) were sized against gpt-5.4-mini at
# effort "low". A model that thinks more verbosely hits the ceiling and returns
# finish_reason="length" with NO content, which the router reads as a failed
# step -- not a wrong answer, a missing one. Nemotron 3 Super truncated 38 calls
# in 100 questions at the stock budget.
REASONING_BUDGET = None
QFILE = SCRATCH / "bench_questions.json"

# Which question a chat call belongs to. Set per request by the parallel
# runner's middleware; FastAPI runs the sync endpoint in a worker thread with
# a copy of the request's context, so the value reaches the chat wrapper.
CURRENT_N = contextvars.ContextVar("bench_n", default=None)


# -- question selection ------------------------------------------------------
def units_of(specs):
    """Follow-up rows (session == "prev") glued to the row before them."""
    units = []
    for s in specs:
        if s.get("session") == "prev" and units:
            units[-1].append(s)
        else:
            units.append([s])
    return units


def select(n=100, seed=7):
    """Stratified sample of the gold set; follow-up chains sampled as units."""
    specs = json.loads((BENCH / "eval_questions_full.json").read_text(encoding="utf-8"))
    units = units_of(specs)
    strata = {}
    for u in units:
        key = ("followup_chain",) if len(u) > 1 else (u[0]["case_type"], u[0]["lang"])
        strata.setdefault(key, []).append(u)
    rng, frac = random.Random(seed), n / len(specs)
    chosen = []
    for key in sorted(strata):
        pool = strata[key][:]
        rng.shuffle(pool)
        quota, got = round(frac * sum(len(u) for u in pool)), 0
        for u in pool:
            if got >= quota:
                break
            chosen.append(u)
            got += len(u)
    ids = {id(u) for u in chosen}
    rest = [u for u in units if id(u) not in ids]
    rng.shuffle(rest)
    total = sum(len(u) for u in chosen)
    while total < n:
        u = next((x for x in rest if len(x) <= n - total), None)
        if u is None:
            break
        rest.remove(u)
        chosen.append(u)
        total += len(u)
    while total > n:
        u = next(x for x in reversed(chosen)
                 if len(x) == 1 and x[0]["case_type"] == "standard")
        chosen = [c for c in chosen if c is not u]
        total -= 1
    order = {s["n"]: i for i, s in enumerate(specs)}
    rows = [s for u in sorted(chosen, key=lambda u: order[u[0]["n"]]) for s in u]
    QFILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"wrote {QFILE} ({len(rows)} questions out of {len(specs)})")
    print(" case_type:", dict(Counter(r["case_type"] for r in rows)))
    print(" lang:     ", dict(Counter(r["lang"] for r in rows)))


# -- the chat wrapper (same for every run) -----------------------------------
def _env(path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


class Completions:
    """Retries transport errors (3 tries), logs latency/provider per call, and
    lifts the non-reasoning max_tokens caps (80/200/250) to the budgets the
    reasoning path gets (500/2000/500) so an answer is never cut short by a
    limit that was sized for a different code path."""

    def __init__(self, backend, log, provider=None, quantization=None):
        self.backend, self.log, self.provider = backend, log, provider
        self.quantization = quantization

    def create(self, **kw):
        if "max_tokens" in kw:
            kw["max_tokens"] = 2000 if kw["max_tokens"] == 200 else max(kw["max_tokens"], 500)
        if REASONING_BUDGET and "max_completion_tokens" in kw:
            kw["max_completion_tokens"] = max(kw["max_completion_tokens"], REASONING_BUDGET)
        if self.provider:
            # Pin OpenRouter to ONE host. Some hosts serve the same model badly:
            # ModelRun returns {"query_id":-0} for the template-picking prompt,
            # which the router reads as no_match. Fallbacks off, so a pinned run
            # is really that host; the retry loop below covers a transient miss.
            #
            # A HOST IS NOT A PRECISION. DeepInfra serves this model at fp4 and
            # at fp8, so pinning the name alone leaves the measurement free to
            # land on either — which is the very confound this flag exists to
            # remove. `--quantization` pins the second half.
            pref = {"order": [self.provider], "allow_fallbacks": False}
            if self.quantization:
                pref["quantizations"] = [self.quantization]
            kw.setdefault("extra_body", {})["provider"] = pref
        n, last = CURRENT_N.get(), None
        for attempt in range(3):
            t0 = time.time()
            try:
                r = self.backend.chat.completions.create(**kw)
                extra = getattr(r, "model_extra", None) or {}
                ch = r.choices[0] if r.choices else None
                self.log.append({"n": n, "s": round(time.time() - t0, 2), "attempt": attempt,
                                 "provider": extra.get("provider"),
                                 "finish": getattr(ch, "finish_reason", None),
                                 "empty": not (ch and (ch.message.content or "").strip()),
                                 "cost": getattr(r.usage, "cost", None) if r.usage else None})
                return r
            except Exception as ex:          # transport / HTTP errors only
                last = ex
                self.log.append({"n": n, "s": round(time.time() - t0, 2), "attempt": attempt,
                                 "error": f"{type(ex).__name__}: {str(ex)[:160]}"})
                # BACKOFF ON 429, because an instant retry cannot clear a
                # per-MINUTE cap. OpenRouter meters some models on shared
                # capacity (glm-5.3-flash: 20 requests/min for the whole
                # account), so a burst of workers exhausts it and three
                # immediate retries simply fail three times.
                if "429" in str(ex) or "RateLimit" in type(ex).__name__:
                    time.sleep(5 * (attempt + 1))
        raise last


class Hybrid:
    """Embeddings from the real OpenAI client; chat from `chat_backend`."""

    def __init__(self, oai, chat_backend, log, provider=None, quantization=None):
        self._oai = oai
        self.embeddings = oai.embeddings
        self.chat = SimpleNamespace(
            completions=Completions(chat_backend, log, provider, quantization))

    def __getattr__(self, name):
        return getattr(self._oai, name)


def use_model(model, reasoning=False):
    """Point every chat call site at `model`. The modules import the model names
    by value, so each module's own binding is patched. A non-reasoning model
    goes down the code's temperature-0/max_tokens branch; a reasoning model is
    added to REASONING_MODELS (one shared set object) so it gets exactly the
    gpt-5.4-mini treatment: max_completion_tokens + reasoning_effort "low"."""
    import query_router.config as c
    import query_router.reranker as rr
    import query_router.followup_classifier as fc
    import query_router.entity_extractor as ee
    import query_router.intent_classifier as ic
    for mod, names in ((c, ("ABSTRACTION_MODEL", "EXTRACTION_MODEL", "RERANK_MODEL")),
                       (rr, ("RERANK_MODEL",)), (fc, ("RERANK_MODEL",)),
                       (ee, ("EXTRACTION_MODEL",)), (ic, ("ABSTRACTION_MODEL",))):
        for name in names:
            if hasattr(mod, name):
                setattr(mod, name, model)
    if reasoning:
        c.REASONING_MODELS.add(model)


def configure(mode):
    """(model label, chat backend or None for the app's own OpenAI client)."""
    from openai import OpenAI
    if mode in OPENROUTER_MODELS:
        model = OPENROUTER_MODELS[mode]
        use_model(model, reasoning=mode in REASONING_OPENROUTER)
        key = _env(ROOT / "Insights" / ".env")["OPENROUTER_API_KEY"]
        return model, OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    if mode in OPENAI_MODELS:
        model = OPENAI_MODELS[mode]
        use_model(model, reasoning=True)
        return model, None
    import query_router.config as c
    return c.RERANK_MODEL, None


# -- records -----------------------------------------------------------------
def base_record(spec):
    rec = {k: spec.get(k) for k in ("n", "q", "gold", "lang", "case_type", "bracket")}
    rec.update(acc=spec.get("acc", []), partial=spec.get("partial", False),
               excluded=spec.get("excluded", False))
    if spec.get("expected_clarification"):
        rec["expected_clarification"] = spec["expected_clarification"]
    return rec


def fill_record(rec, resp):
    if resp.status_code != 200:
        rec["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        return
    d = resp.json()
    rows = d.get("result")
    clar = d.get("clarification")
    rec.update(
        tier=d.get("tier"), query_id=d.get("query_id"),
        answer=(d.get("answer") or "")[:400], entities=d.get("entities"),
        n_rows=None if rows is None else len(rows),
        rows_sample=None if rows is None else rows[:3],
        date_range=d.get("date_range"),
        clarification=({"reason": clar.get("reason"),
                        "prompt": (clar.get("prompt") or "")[:200],
                        "options": [{k: v for k, v in (o or {}).items()
                                     if k in ("label", "query", "query_id", "message")}
                                    for o in (clar.get("options") or [])]}
                       if clar else None))


def payload_for(spec, sid):
    """(payload, session id). A follow-up reuses `sid`; anything else starts fresh."""
    if spec.get("session") == "prev" and sid:
        return {"message": spec["q"], "session_id": sid}, sid
    sid = str(uuid4())
    return {"message": spec["q"], "session_id": sid, "reset_context": True}, sid


def write_outputs(tag, mode, model, records, call_log, extra=None):
    from query_router.llm_usage import meter
    out_path = SCRATCH / f"results_{tag}.jsonl"
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n"
                                for r in records), encoding="utf-8")
    lat = [c["s"] for c in call_log if "error" not in c]
    summary = {
        "mode": mode, "model": model, "questions": len(records),
        "verdicts": {v: sum(r["verdict"] == v for r in records)
                     for v in sorted({r["verdict"] for r in records})},
        "wall_s_median": statistics.median(r["wall_s"] for r in records),
        "wall_s_p90": sorted(r["wall_s"] for r in records)[int(0.9 * (len(records) - 1))],
        "wall_s_total": round(sum(r["wall_s"] for r in records), 1),
        "chat_calls": len(lat), "chat_call_s_median": statistics.median(lat) if lat else None,
        "transport_errors": sum("error" in c for c in call_log),
        "empty_responses": sum(c.get("empty", False) for c in call_log),
        "truncated": sum(c.get("finish") == "length" for c in call_log),
        "providers": {p: sum(c.get("provider") == p for c in call_log)
                      for p in {c.get("provider") for c in call_log if "error" not in c}},
        "openrouter_cost_usd": round(sum(c.get("cost") or 0 for c in call_log), 5),
        **(extra or {}),
        "usage": meter().snapshot(),
    }
    (SCRATCH / f"summary_{tag}.json").write_text(json.dumps(summary, indent=1, default=str),
                                                  encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "usage"}, indent=1, default=str))
    print(meter().report(f"{tag}: token spend"))


def load_questions(limit):
    questions = json.loads(QFILE.read_text(encoding="utf-8"))
    return questions[:limit] if limit else questions


# -- sequential replay (in-process TestClient) -------------------------------
def run(mode, limit=None):
    from fastapi.testclient import TestClient
    import main
    from query_router.llm_usage import meter
    from grade_full_eval import grade

    questions = load_questions(limit)
    tag = (mode + (f"_{PROVIDER}" if PROVIDER else "")
           + (f"_{QUANTIZATION}" if QUANTIZATION else "")
           + (f"_rb{REASONING_BUDGET}" if REASONING_BUDGET else "")
           + (f"_smoke{limit}" if limit else ""))
    model, backend = configure(mode)
    call_log = []
    meter().reset()
    records = []
    with TestClient(main.app) as client:
        real = main._openai_client
        main._openai_client = Hybrid(real, backend or real, call_log, PROVIDER, QUANTIZATION)
        sid = None
        for i, spec in enumerate(questions, 1):
            payload, sid = payload_for(spec, sid)
            rec = base_record(spec)
            n_calls0 = len(call_log)
            t0 = time.time()
            try:
                fill_record(rec, client.post("/query", json=payload, timeout=180))
            except Exception as ex:
                rec["error"] = f"{type(ex).__name__}: {ex}"
            rec["wall_s"] = round(time.time() - t0, 2)
            rec["llm_calls"] = call_log[n_calls0:]
            rec["verdict"] = grade(dict(rec))
            records.append(rec)
            print(f"[{i:>3}/{len(questions)}] {rec['verdict']:<20} {rec['wall_s']:>6.1f}s "
                  f"{(rec.get('query_id') or rec.get('tier') or '-')!s:<10} {spec['q'][:60]}",
                  flush=True)
    write_outputs(tag, mode, model, records, call_log)


# -- parallel replay (local uvicorn server, N worker threads) ----------------
def run_parallel(mode, workers, limit=None):
    import httpx
    import uvicorn
    import main
    from query_router.llm_usage import meter
    from grade_full_eval import grade

    questions = load_questions(limit)
    tag = (f"{mode}_par{workers}" + (f"_{PROVIDER}" if PROVIDER else "")
           + (f"_{QUANTIZATION}" if QUANTIZATION else "")
           + (f"_rb{REASONING_BUDGET}" if REASONING_BUDGET else "")
           + (f"_smoke{limit}" if limit else ""))
    model, backend = configure(mode)
    call_log = []

    class TagRequests:
        """Pure ASGI middleware: X-Bench-N header -> CURRENT_N for this request."""

        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                value = dict(scope.get("headers") or []).get(b"x-bench-n")
                if value:
                    CURRENT_N.set(int(value))
            await self.app(scope, receive, send)

    main.app.add_middleware(TagRequests)

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port,
                                           log_level="warning"))
    server.install_signal_handlers = lambda: None    # not the main thread
    threading.Thread(target=server.run, daemon=True).start()
    t_wait = time.time()
    while not server.started:
        if time.time() - t_wait > 600:
            raise RuntimeError("local server did not start within 10 minutes")
        time.sleep(0.2)
    real = main._openai_client
    main._openai_client = Hybrid(real, backend or real, call_log, PROVIDER, QUANTIZATION)
    meter().reset()

    units = units_of(questions)
    records, lock, done = {}, threading.Lock(), [0]

    def run_unit(unit):
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=300) as http:
            sid = None
            for spec in unit:
                payload, sid = payload_for(spec, sid)
                rec = base_record(spec)
                t0 = time.time()
                try:
                    fill_record(rec, http.post("/query", json=payload,
                                               headers={"x-bench-n": str(spec["n"])}))
                except Exception as ex:
                    rec["error"] = f"{type(ex).__name__}: {ex}"
                rec["wall_s"] = round(time.time() - t0, 2)
                with lock:
                    records[spec["n"]] = rec
                    done[0] += 1
                    print(f"[{done[0]:>3}/{len(questions)}] #{spec['n']} {rec['wall_s']:>6.1f}s "
                          f"{(rec.get('query_id') or rec.get('tier') or rec.get('error', '-'))!s:<12} "
                          f"{spec['q'][:55]}", flush=True)

    print(f"running {len(questions)} questions as {len(units)} independent units, "
          f"{workers} at a time" + (f", pinned to {PROVIDER}" if PROVIDER else ""))
    t_run = time.time()
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(run_unit, units))
    run_wall = round(time.time() - t_run, 1)
    server.should_exit = True

    by_n = {}
    for c in call_log:
        by_n.setdefault(c.get("n"), []).append(c)
    ordered = []
    for spec in questions:
        rec = records[spec["n"]]
        rec["llm_calls"] = by_n.get(spec["n"], [])
        rec["verdict"] = grade(dict(rec))
        ordered.append(rec)
    print(f"\nwhole run took {run_wall}s; untagged chat calls: {len(by_n.get(None, []))}")
    write_outputs(tag, mode, model, ordered, call_log,
                  extra={"workers": workers, "run_wall_s": run_wall, "provider_pin": PROVIDER,
                         "quantization_pin": QUANTIZATION,
                         "untagged_calls": len(by_n.get(None, []))})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true")
    ap.add_argument("--mode", choices=("openai", *OPENROUTER_MODELS, *OPENAI_MODELS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, help="run in parallel on a local server")
    ap.add_argument("--provider", help="pin OpenRouter to one host, e.g. CoreWeave")
    ap.add_argument("--reasoning-budget", type=int,
                    help="floor for max_completion_tokens on the reasoning branch")
    ap.add_argument("--quantization",
                    help="and pin the precision that host serves, e.g. fp8")
    a = ap.parse_args()
    PROVIDER, QUANTIZATION = a.provider, a.quantization
    REASONING_BUDGET = a.reasoning_budget
    if a.select:
        select()
    elif a.workers:
        run_parallel(a.mode, a.workers, a.limit)
    else:
        run(a.mode, a.limit)

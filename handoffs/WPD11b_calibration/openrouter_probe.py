"""WP-D11b: Novita vs OpenRouter for qwen/qwen3-embedding-8b, on the same texts,
and both against the vectors the corpus already stores.

Same 16 findings + 16 decompositions (seed 11) as embedding_probe.py. Keys read
from the Drive Insights/.env (NOVITA_API_KEY, OPENROUTER_API_KEY); never printed.
OpenRouter routes one model to several hosts, so each host is pinned in turn
(`provider.order` + `allow_fallbacks: false`) and measured separately.

For each source, cosine against the stored fp16 vectors (min / median), and
cosine between two identical calls (run-to-run noise). Plus the direct
comparison the operator asked for: Novita's full 4,096-number vector against
OpenRouter's, text by text.
"""
import hashlib, json, os, random, sys, time
MIRROR = r"C:\dev\odisha-d11b"
sys.path.insert(0, os.path.join(MIRROR, "Insights", "src")); os.chdir(MIRROR)
import numpy as np, httpx
from dotenv import dotenv_values
import phase5d_retrieval_corpus as p5d
import phase5f_decompose as p5f

ENV = dotenv_values(r"I:/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW/Insights/.env")
MODEL = "qwen/qwen3-embedding-8b"
SRC = {
    "novita":  ("https://api.novita.ai/openai/embeddings", ENV["NOVITA_API_KEY"], {}),
    "or_deepinfra": ("https://openrouter.ai/api/v1/embeddings", ENV["OPENROUTER_API_KEY"],
                     {"provider": {"order": ["DeepInfra"], "allow_fallbacks": False}}),
    "or_nebius": ("https://openrouter.ai/api/v1/embeddings", ENV["OPENROUTER_API_KEY"],
                  {"provider": {"order": ["Nebius"], "allow_fallbacks": False}}),
}


def call(src, texts, **extra):
    url, key, route = SRC[src]
    r = httpx.post(url, headers={"Authorization": "Bearer " + key},
                   json={"model": MODEL, "input": texts, "encoding_format": "float",
                         **route, **extra}, timeout=600)
    d = r.json()
    if r.status_code != 200 or not d.get("data"):
        raise RuntimeError(f"{src} HTTP {r.status_code}: {json.dumps(d)[:200]}")
    rows = sorted(d["data"], key=lambda x: x["index"])
    return np.array([x["embedding"] for x in rows], dtype=np.float32), d.get("provider")


def l2(m): return m / np.linalg.norm(m, axis=1, keepdims=True)
def cos(a, b): return (l2(a) * l2(b)).sum(1)
def mm(x): return [round(float(x.min()), 6), round(float(np.median(x)), 6)]


out = {}
for name, mod in (("findings", p5d), ("decompose", p5f)):
    payload = mod.read_corpus_json(mod.CORPUS_PATH)
    stamp = json.load(open(mod.STAMP_PATH, encoding="utf-8"))
    vecs = mod.load_vectors(mod.VECTORS_PATH, stamp["vector_storage"])
    recs = payload["records"]
    random.seed(11); idx = random.sample(range(len(recs)), 16)
    texts = []
    for i in idx:
        t = mod.regenerate_embed_text(recs[i])
        assert hashlib.sha256(t.encode()).hexdigest() == recs[i]["embed_text_sha256"], recs[i]["finding_id"]
        texts.append(t)
    stored = vecs[idx]
    res, full = {}, {}
    for src in SRC:
        a, prov = call(src, texts); b, _ = call(src, texts)
        full[src] = a
        res[src + " native, first 1024"] = {
            "host": prov, "native_dims": int(a.shape[1]),
            "cos_vs_stored": mm(cos(stored, a[:, :1024])),
            "cos_call_vs_call": mm(cos(a[:, :1024], b[:, :1024]))}
        if src != "novita":
            s, prov = call(src, texts, dimensions=1024); s2, _ = call(src, texts, dimensions=1024)
            res[src + " server dimensions=1024"] = {
                "host": prov, "dims": int(s.shape[1]),
                "cos_vs_stored": mm(cos(stored, s)),
                "cos_call_vs_call": mm(cos(s, s2)),
                "cos_vs_own_native_prefix": mm(cos(s, a[:, :1024]))}
    for src in ("or_deepinfra", "or_nebius"):
        res[f"novita vs {src}, full 4096, same text"] = mm(cos(full["novita"], full[src]))
    out[name] = res
print(json.dumps(out, indent=2))

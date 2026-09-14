"""Diagnostic: does client-side prefix truncation (4096 -> 1024, L2) reproduce
the stored vectors that were embedded with server-side dimensions=1024?"""
import hashlib, json, os, random, sys, time
MIRROR = r"C:\dev\odisha-d11b"
sys.path.insert(0, os.path.join(MIRROR, "Insights", "src"))
os.chdir(MIRROR)
import numpy as np, httpx
import phase5d_retrieval_corpus as p5d
import phase5f_decompose as p5f

p5d._load_env()
KEY = os.environ["NOVITA_API_KEY"]


def embed(texts):
    t0 = time.time()
    r = httpx.post(p5d.EMBED_BASE_URL + "/embeddings",
                   headers={"Authorization": "Bearer " + KEY},
                   json={"model": p5d.EMBED_MODEL, "input": texts,
                         "encoding_format": "float"}, timeout=600)
    r.raise_for_status()
    d = sorted(r.json()["data"], key=lambda x: x["index"])
    print(f"    call {len(texts)} texts in {time.time()-t0:.1f}s", flush=True)
    return np.array([x["embedding"] for x in d], dtype=np.float32)


def trunc(v, n=1024):
    t = v[:, :n]
    return t / np.linalg.norm(t, axis=1, keepdims=True)


out = {}
for name, mod in (("findings", p5d), ("decompose", p5f)):
    payload = mod.read_corpus_json(mod.CORPUS_PATH)
    vecs = mod.load_vectors(mod.VECTORS_PATH)
    recs = payload["records"]
    random.seed(11)
    idx = random.sample(range(len(recs)), 16)
    texts = []
    for i in idx:
        t = mod.regenerate_embed_text(recs[i])
        assert hashlib.sha256(t.encode()).hexdigest() == recs[i]["embed_text_sha256"], i
        texts.append(t)
    stored = vecs[idx]
    a = embed(texts)
    b = embed(texts)
    ta, tb = trunc(a), trunc(b)
    cos_stored = (stored * ta).sum(1)
    cos_jitter = (ta * tb).sum(1)
    maxabs_stored = np.abs(stored - ta).max(1)
    maxabs_jitter = np.abs(ta - tb).max(1)
    out[name] = {
        "n": len(idx), "native_dims": int(a.shape[1]),
        "cos_stored_vs_truncated": [float(cos_stored.min()), float(np.median(cos_stored))],
        "cos_call_vs_call_truncated": [float(cos_jitter.min()), float(np.median(cos_jitter))],
        "maxabs_component_stored_vs_truncated": [float(np.median(maxabs_stored)), float(maxabs_stored.max())],
        "maxabs_component_call_vs_call": [float(np.median(maxabs_jitter)), float(maxabs_jitter.max())],
    }
    # Sanity: is the stored vector closer to a DIFFERENT prefix scheme? (e.g. last 1024)
    tl = a[:, -1024:]; tl = tl / np.linalg.norm(tl, axis=1, keepdims=True)
    out[name]["cos_stored_vs_last1024"] = float(np.median((stored * tl).sum(1)))
print(json.dumps(out, indent=2))

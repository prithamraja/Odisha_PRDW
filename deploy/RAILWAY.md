# Deploying Odisha PR&DW on Railway

Two services off one GitHub repo (`prithamraja/Odisha_PRDW`), each with its own
root directory and its own `railway.json`:

| Service   | Root Directory                 | Build   | Start                                       |
|-----------|--------------------------------|---------|---------------------------------------------|
| `ask-api` | `Ask`                          | Nixpacks (Python 3.11, `requirements.txt`) | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| `ask-web` | `frontend/ab-dashboard-main`   | Nixpacks (Node ≥20, `npm run build`)       | `npx vite preview --host :: --port $PORT`      |

## Before anything else

Railway builds **what is on GitHub**, not what is on your disk. Today the
pushed tree still has `Chatbot/`; the local rename to `Ask/` is uncommitted, and
`.gitignore` still names `Chatbot/...` paths (so a commit would sweep in the
eval artefacts and `__pycache__` now sitting under `Ask/`). Fix the ignore
rules, commit the rename, push — then `preflight` will pass.

## Order matters

The frontend bakes the backend URL into its bundle at build time, so:

1. Deploy `ask-api`, give it a domain, confirm `GET /health` returns `status: ok`.
2. Set `VITE_API_BASE_URL` on `ask-web` to that domain.
3. `ask-web` rebuilds and now talks to the real backend.

Doing it in the other order produces a site that loads and answers nothing.

## Scripted path

```bash
railway login                              # in your own terminal, once
./deploy/railway-deploy.sh preflight
./deploy/railway-deploy.sh bootstrap       # creates project + both services
#   -> set both Root Directories in the dashboard when it tells you to
./deploy/railway-deploy.sh secret          # OPENAI_API_KEY, read from stdin
./deploy/railway-deploy.sh domains
./deploy/railway-deploy.sh wire https://<backend>.up.railway.app
```

## Dashboard path

New Project → Deploy from GitHub repo → pick the repo. Then, twice (once per
service): Settings → Source → Root Directory, Variables → paste from
`deploy/railway.env.example`, Settings → Networking → Generate Domain.

## Things that will bite

- **Cold start is slow and costs money.** `Ask/main.py:162` seeds 36 dashboard
  queries and builds catalog embeddings on every boot. The embedding cache goes
  to `Ask/.tmp/` (gitignored, and Railway's filesystem is ephemeral), so every
  restart re-embeds against the OpenAI API. `healthcheckTimeout` is set to 300s
  to survive it. To fix properly: commit `.tmp/catalog_index.json`, or attach a
  Railway volume at `Ask/.tmp`.
- **The database is a 24 MB file in git**, opened read-only
  (`Ask/data/panchayat_1.duckdb`). Nothing is written to it, so no volume is
  needed — but every data refresh is a commit and a redeploy.
- **CORS is wide open** (`allow_origins=["*"]`, `Ask/main.py:142`). Fine for a
  demo; narrow it to the `ask-web` domain before this is public.
- **No auth on `/query`.** Anyone with the backend URL spends your OpenAI
  credit. Worth a shared secret or Railway private networking if the API does
  not need to be public.

# Deploying Odisha PR&DW on Railway

Three services off one GitHub repo (`prithamraja/Odisha_PRDW`), each with its own
root directory and its own `railway.json`:

| Service   | Root Directory                 | Build   | Start                                       |
|-----------|--------------------------------|---------|---------------------------------------------|
| `ask-api` | `Ask`                          | Nixpacks (Python 3.11, `requirements.txt`) | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| `ask-web` | `frontend/ab-dashboard-main`   | Nixpacks (Node ≥20, `npm run build`)       | `npx vite preview --host :: --port $PORT`      |
| `discover-api` | **repo root** (`/`)       | Nixpacks (Python 3.11, root `requirements.txt`) | `uvicorn DiscoverChat.main:app --host 0.0.0.0 --port $PORT` |

## Live deployment (as of 2026-09-03)

| | |
|---|---|
| Project | `OdishaPRDW` — `693ae217-d644-417f-903a-35c2385ff2e2` |
| Environment | `production` — `e140f86c-181e-4600-b16f-f9f9cce50539` |
| Backend | service `Odisha_PRDW` — https://odishaprdw-production.up.railway.app |
| Frontend | service `ask-web` — https://ask-web-production.up.railway.app |
| Discover | service `discover-api` — https://discover-api-production-1154.up.railway.app |

Railway builds **what is on GitHub**, not what is on your disk. The `Ask/`
restructure is pushed as of `6565737`, so both roots resolve.

## Root Directory IS scriptable — correction

An earlier version of this file said Root Directory could only be set in the
dashboard, because the CLI has no flag for it. The CLI doesn't, but the GraphQL
API does, and a **project token is enough** for it:

```
POST https://backboard.railway.com/graphql/v2
Header: Project-Access-Token: <RAILWAY_TOKEN from Insights/.env>
Header: User-Agent: curl/8.4.0      # python-urllib's default UA is blocked by
                                    # Cloudflare with error 1010 before it ever
                                    # reaches the API

mutation($serviceId: String!, $environmentId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
}
variables: { "input": { "rootDirectory": "Ask" } }
```

`serviceCreate`, `serviceDomainCreate` and `serviceInstanceDeployV2` all accept
the project token too — the CLI refuses these ("Unauthorized") because of its
own account-level preflight, not because the API rejects them.

## What a project token CANNOT do

`deploymentTriggerCreate` returns **Bad Access**: wiring a GitHub auto-deploy
trigger needs the GitHub app's user-level authorization. Consequence today:

- **backend** auto-deploys on push to `master` (trigger created when the service
  was first connected in the dashboard),
- **ask-web** does **not** — it was created via the API, so a push does not
  rebuild it. Either connect the repo once in the dashboard (Settings → Source),
  or redeploy it explicitly with `serviceInstanceDeployV2`.

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

## DiscoverChat (`discover-api`), added 2026-09-03

Deployed after the Discover tab's question box shipped in `023b49f` with no
service behind it. Three things about it differ from `ask-api`, and each one
broke a deploy attempt before it was fixed:

- **Root Directory is the repo root, not `DiscoverChat/`.** `config.py` puts
  `Insights/src` and `Ask/` on `sys.path` and reads the corpus out of
  `Insights/metainsights/`. A service rooted at `DiscoverChat/` cannot see any
  of it. Nixpacks only detects Python if a requirements file sits at the root it
  is given, which is what the root `requirements.txt` is for — it does nothing
  but re-export `DiscoverChat/requirements.txt`.
- **It needs `NOVITA_API_KEY` as well as `OPENAI_API_KEY`.** The retrieval pin
  embeds the user's question through Qwen on Novita
  (`phase5d_retrieval_corpus.EMBED_API_KEY_VAR`), not through OpenAI. With only
  `OPENAI_API_KEY` set it boots fine and then fails on the first question, which
  is the worst possible way for this to be wrong.
- **`scipy` was missing from `DiscoverChat/requirements.txt`.** `glossary.py`
  imports `phase4a_engine`, which does `from scipy import stats` at module
  scope, so `import DiscoverChat.main` fails outright without it. It went
  unnoticed because every dev venv already had scipy from Insights work. Before
  changing these requirements again, test in a venv built from them alone.

**Question decomposition is OFF in production.** The WP-D6 sidecar
(`decompose_corpus.json` / `.npy`, ~310 MB) is a build output and is not in git,
so the deployed service runs without it. `config.py` tolerates that by design.
If decomposition is meant to be live, the sidecar needs a Railway volume or some
other way in — it will never fit in the repo.

## Correction: a variable change DOES rebuild a service

The note above says `ask-web` has no GitHub trigger and a push will not rebuild
it. That is still true, and is why the frontend sat on an 18 August build until
3 September while the backend kept auto-deploying.

What was not known then: writing a variable with `variableUpsert` triggers a
redeploy on its own. Setting `VITE_DISCOVER_API_BASE_URL` on `ask-web` rebuilt
it from current `master` without any explicit deploy call. Useful as a way to
force a frontend rebuild, but do not rely on it as the fix — connect the repo in
the dashboard (Settings → Source) so ordinary code pushes reach `ask-web` too.

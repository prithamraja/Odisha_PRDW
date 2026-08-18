#!/usr/bin/env bash
#
# Odisha PR&DW — Railway deploy driver.
#
# Run from the repo root, in Git Bash:
#
#     ./deploy/railway-deploy.sh preflight    # check login, CLI, pushed tree
#     ./deploy/railway-deploy.sh bootstrap    # create project + both services
#     ./deploy/railway-deploy.sh secret       # set OPENAI_API_KEY (reads stdin)
#     ./deploy/railway-deploy.sh domains      # generate public domains
#     ./deploy/railway-deploy.sh wire         # point the frontend at the backend
#     ./deploy/railway-deploy.sh status       # deployment status for both
#     ./deploy/railway-deploy.sh logs api     # tail one service
#
# It never takes a token as an argument. Authenticate once with `railway login`
# in your own terminal; the CLI keeps the credential in ~/.railway/.
#
# One step CANNOT be scripted: the Root Directory of each service is only
# settable in the Railway dashboard (the CLI has no flag for it). `bootstrap`
# stops and tells you exactly what to click.

set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-odisha-prdw}"
BACKEND_SVC="${BACKEND_SVC:-ask-api}"
FRONTEND_SVC="${FRONTEND_SVC:-ask-web}"
REPO="${REPO:-prithamraja/Odisha_PRDW}"
BACKEND_ROOT="Ask"
FRONTEND_ROOT="frontend/ab-dashboard-main"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m!! %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31mxx %s\033[0m\n' "$*" >&2; exit 1; }

# ── preflight ────────────────────────────────────────────────────────────────
cmd_preflight() {
  command -v railway >/dev/null || die "railway CLI not found. https://docs.railway.com/guides/cli"
  say "CLI: $(railway --version)"

  railway whoami >/dev/null 2>&1 \
    || die "Not logged in. Run 'railway login' in your terminal, then re-run this."
  say "Logged in as: $(railway whoami 2>&1 | tail -1)"

  # Railway builds what is on GitHub, not what is on disk. Both service roots
  # must exist on the pushed branch or the build fails with "no such directory".
  local branch remote_ref
  branch="$(git rev-parse --abbrev-ref HEAD)"
  remote_ref="origin/${branch}"
  git rev-parse --verify --quiet "$remote_ref" >/dev/null \
    || die "No $remote_ref — push the branch first."

  local missing=0
  for root in "$BACKEND_ROOT" "$FRONTEND_ROOT"; do
    if git cat-file -e "${remote_ref}:${root}" 2>/dev/null; then
      say "OK  ${root}/ exists on ${remote_ref}"
    else
      warn "MISSING  ${root}/ is not on ${remote_ref} — Railway cannot build it"
      missing=1
    fi
  done

  if ! git diff-index --quiet HEAD -- 2>/dev/null || [ -n "$(git status --porcelain)" ]; then
    warn "Working tree is dirty. Railway deploys the pushed commit, not your disk."
    git status --short | head -10
  fi

  [ "$missing" -eq 0 ] || die "Fix the missing root dir(s), commit, push, then re-run."
  say "Preflight passed."
}

# ── bootstrap ────────────────────────────────────────────────────────────────
cmd_bootstrap() {
  cmd_preflight

  if railway status >/dev/null 2>&1; then
    say "Already linked to a project — skipping 'railway init'."
  else
    say "Creating project '${PROJECT_NAME}'"
    railway init -n "$PROJECT_NAME"
  fi

  # DB_ENGINE is not optional: the default 'pandas' engine reads Ask/stub_data/,
  # which does not exist in this repo, and the container would crash on boot.
  say "Creating backend service '${BACKEND_SVC}' from ${REPO}"
  railway add \
    --service "$BACKEND_SVC" \
    --repo "$REPO" \
    --variables "DB_ENGINE=duckdb_file" \
    --variables "DB_PATH=data/panchayat_1.duckdb" \
    --variables "NGROK_ENABLED=false" \
    --variables "PYTHONUNBUFFERED=1"

  say "Creating frontend service '${FRONTEND_SVC}' from ${REPO}"
  # VITE_API_BASE_URL is deliberately left unset here — Vite inlines it at BUILD
  # time, so it can only be set once the backend has a domain. `wire` does that
  # and the change triggers a rebuild.
  railway add \
    --service "$FRONTEND_SVC" \
    --repo "$REPO"

  cat <<MANUAL

  ────────────────────────────────────────────────────────────────────────
  MANUAL STEP — the CLI has no flag for this. In the Railway dashboard, for
  each service open Settings → Source and set:

      ${BACKEND_SVC}   Root Directory:  ${BACKEND_ROOT}
      ${FRONTEND_SVC}  Root Directory:  ${FRONTEND_ROOT}

  Each root already contains its own railway.json (build + start command), so
  nothing else needs configuring there.
  ────────────────────────────────────────────────────────────────────────

  Then:  ./deploy/railway-deploy.sh secret
MANUAL
}

# ── secret ───────────────────────────────────────────────────────────────────
cmd_secret() {
  say "Setting OPENAI_API_KEY on '${BACKEND_SVC}'"
  echo "Paste the key and press Enter (it is read from stdin, so it does not"
  echo "land in your shell history or in any file):"
  railway variable set OPENAI_API_KEY --stdin --service "$BACKEND_SVC"
  say "Set. The backend will redeploy."
}

# ── domains ──────────────────────────────────────────────────────────────────
cmd_domains() {
  say "Generating domain for '${BACKEND_SVC}'"
  railway domain --service "$BACKEND_SVC" || warn "Backend may already have a domain."
  say "Generating domain for '${FRONTEND_SVC}'"
  railway domain --service "$FRONTEND_SVC" || warn "Frontend may already have a domain."
  say "Copy the backend URL, then run:  ./deploy/railway-deploy.sh wire"
}

# ── wire ─────────────────────────────────────────────────────────────────────
# Vite reads VITE_API_BASE_URL at build time (src/services/api.ts falls back to
# http://localhost:8000 if it is absent — which silently produces a frontend
# that talks to nothing). Setting it triggers a frontend rebuild.
cmd_wire() {
  local url="${BACKEND_URL:-${1:-}}"
  if [ -z "$url" ]; then
    warn "No backend URL given."
    echo "Usage:  ./deploy/railway-deploy.sh wire https://<backend>.up.railway.app"
    echo "Find it with:  railway domain --service ${BACKEND_SVC}"
    exit 1
  fi
  url="${url%/}"                      # trailing slash would double up on /query
  case "$url" in https://*) ;; *) die "Backend URL must be https:// — got '$url'";; esac

  say "Pointing '${FRONTEND_SVC}' at ${url}"
  railway variable set "VITE_API_BASE_URL=${url}" --service "$FRONTEND_SVC"
  say "Set. The frontend will rebuild with the URL baked in."
  echo "Verify the backend first:  curl ${url}/health"
}

# ── status / logs ────────────────────────────────────────────────────────────
cmd_status() {
  railway status
  railway service status || true
}

cmd_logs() {
  local which="${1:-api}"
  case "$which" in
    api|backend)  railway logs --service "$BACKEND_SVC" ;;
    web|frontend) railway logs --service "$FRONTEND_SVC" ;;
    *) die "Usage: logs [api|web]" ;;
  esac
}

case "${1:-}" in
  preflight) cmd_preflight ;;
  bootstrap) cmd_bootstrap ;;
  secret)    cmd_secret ;;
  domains)   cmd_domains ;;
  wire)      shift; cmd_wire "$@" ;;
  status)    cmd_status ;;
  logs)      shift; cmd_logs "$@" ;;
  *)
    awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"
    exit 1
    ;;
esac

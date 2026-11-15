#!/usr/bin/env bash
# Start the deployed site: seed the demo club, then serve the frontend and the API (under /api) on one port.
# Settings come from the environment (Replit secrets): DATABASE_URL, AI_MODE, ANTHROPIC_API_KEY, USG_REVIEWER_KEY, ...
set -euo pipefail
cd "$(dirname "$0")/../.."

PYTHON=.venv-deploy/bin/python
[ -x "$PYTHON" ] || PYTHON=python3

if [ -z "${DATABASE_URL:-}" ]; then
  echo "WARNING: DATABASE_URL is not set; using a local SQLite file that is lost on every redeploy." >&2
fi

# Safe to repeat: the demo club is replaced, nothing else is touched. A failure here must not stop the site.
"$PYTHON" scripts/seed_demo.py || echo "WARNING: the demo club could not be seeded." >&2

export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${PORT:-${BACKEND_PORT:-5000}}"
cd backend
exec "../$PYTHON" -m app --site --no-reload

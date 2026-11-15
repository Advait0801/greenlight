#!/usr/bin/env bash
# Build Greenlight for deployment (Replit's build step; also works on any Linux or macOS machine).
# Installs the backend into .venv-deploy/ and builds the frontend into frontend/dist/.
set -euo pipefail
cd "$(dirname "$0")/../.."

# Replit sets PIP_USER, which a virtual environment refuses.
export PIP_USER=0
python3 -m venv .venv-deploy
.venv-deploy/bin/python -m pip install --quiet --upgrade pip
.venv-deploy/bin/python -m pip install --quiet -r backend/requirements.txt

cd frontend
npm ci --no-audit --no-fund
npm run build

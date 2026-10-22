#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -x "$ROOT/.tools/node/bin/node" ]; then
  export PATH="$ROOT/.tools/node/bin:$PATH"
fi

PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi
chmod 600 .env

if grep -q '^ANTHROPIC_API_KEY=replace-with-your-own-key$' .env || ! grep -q '^ANTHROPIC_API_KEY=.\+' .env; then
  echo "Add your Anthropic API key to $ROOT/.env before chatting."
  echo "The key stays local and is excluded from Git."
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 18+ and npm are required for the frontend. Install Node.js and rerun setup." >&2
  exit 1
fi

cd frontend
npm install
cd "$ROOT"
cd mcp-server
npm install
cd "$ROOT"
make test

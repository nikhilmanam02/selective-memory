#!/usr/bin/env bash
# make check: tells you, piece by piece, whether everything is ready and how to fix what isn't.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OK="  [ok]  "; BAD="  [!!]  "; INFO="  [--]  "
problems=0
bad() { echo "$BAD$1"; echo "        fix: $2"; problems=$((problems + 1)); }

echo ""
echo "Selective Memory: checking everything"
echo ""
echo "Installed"
[ -x .venv/bin/python ] && echo "${OK}Python environment" || bad "Python environment missing" "make setup"
[ -d frontend/node_modules ] && echo "${OK}Web app packages" || bad "Web app packages missing" "make setup"
[ -d mcp-server/node_modules ] && echo "${OK}MCP server packages" || bad "MCP server packages missing" "make setup"

echo ""
echo "Claude API key"
KEY="$(grep -E '^ANTHROPIC_API_KEY=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
if [ -z "$KEY" ] || [ "$KEY" = "replace-with-your-own-key" ]; then
  bad "No key in .env" "open .env and set ANTHROPIC_API_KEY=sk-ant-..."
else
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://api.anthropic.com/v1/models \
    -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01")"
  case "$code" in
    200) echo "${OK}Key works" ;;
    401) bad "Anthropic rejected the key" "create a new key at console.anthropic.com and put it in .env" ;;
    000) bad "Couldn't reach Anthropic" "check your internet connection" ;;
    *) bad "Anthropic answered $code" "check billing/credits at console.anthropic.com" ;;
  esac
fi

echo ""
echo "Running (needs 'make dev' in another terminal)"
health="$(curl -s --max-time 3 http://127.0.0.1:8000/api/health)"
if [ -n "$health" ]; then
  echo "${OK}Backend      http://localhost:8000"
  case "$health" in *'"configured":false'*) bad "Backend started before the key was added" "stop make dev (Ctrl+C) and run it again" ;; esac
else
  bad "Backend not running" "make dev"
fi
curl -s --max-time 3 http://127.0.0.1:5173 >/dev/null && echo "${OK}Web app      http://localhost:5173" || bad "Web app not running" "make dev"
curl -s --max-time 3 http://127.0.0.1:8001/health >/dev/null && echo "${OK}MCP server   http://localhost:8001" || bad "MCP server not running" "make dev"

echo ""
echo "Claude Desktop"
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ ! -d "$(dirname "$CONFIG")" ]; then
  echo "${INFO}Not installed (optional). Get it at claude.ai/download"
else
  token="$(python3 - "$CONFIG" <<'PY' 2>/dev/null
import json, sys
try:
    cfg = json.load(open(sys.argv[1]))
    print(cfg["mcpServers"]["selective-memory"]["env"]["SELECTIVE_MEMORY_TOKEN"])
except Exception:
    pass
PY
)"
  if [ -z "$token" ]; then
    bad "Not connected yet" "app -> AI apps -> Connect an app -> Claude Desktop -> Add to Claude Desktop"
  else
    status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 -H "Authorization: Bearer $token" http://127.0.0.1:8000/api/mcp/profile)"
    case "$status" in
      200) echo "${OK}Connected (restart Claude Desktop with Cmd+Q if you just added it)" ;;
      401) bad "Its key was disconnected in the app" "connect Claude Desktop again in AI apps, then restart Claude" ;;
      *) echo "${INFO}Configured; start make dev to verify the key" ;;
    esac
  fi
fi

echo ""
echo "ChatGPT / claude.ai (optional)"
if ! command -v cloudflared >/dev/null 2>&1 && [ ! -x .tools/cloudflared ]; then
  echo "${INFO}Tunnel tool not downloaded yet. 'make tunnel' gets it automatically (only needed for ChatGPT / claude.ai)"
elif [ -f backend/data/public_url.txt ]; then
  url="$(cat backend/data/public_url.txt)"
  if curl -s --max-time 8 "$url/health" | grep -q '"ok":true'; then
    echo "${OK}Public link works: $url"
  else
    bad "Public link isn't reachable yet: $url" "wait 20 seconds, or restart make tunnel"
  fi
else
  echo "${INFO}Tunnel not running. Start it with: make tunnel"
fi

echo ""
if [ "$problems" -eq 0 ]; then
  echo "All good. Open http://localhost:5173"
else
  echo "$problems thing(s) to fix above."
fi
echo ""

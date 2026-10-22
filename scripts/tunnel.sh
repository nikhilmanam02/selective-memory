#!/usr/bin/env bash
# Gives your MCP server a public https link so ChatGPT and claude.ai (which run in
# the cloud) can reach it. The link is handed to the app automatically.
# Usage: make tunnel   (MCP server, for ChatGPT / claude.ai)
#        make share    (the web app itself, password-protected, for judges)
# Keep `make dev` running in another terminal.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-mcp}"
if [ "$MODE" = "share" ]; then
  PORT=8000
  OUT="$ROOT/backend/data/share_url.txt"
  PW="$(grep -E '^APP_PASSWORD=' "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
  if [ -z "$PW" ]; then
    echo "Note: no APP_PASSWORD set, so anyone with the link can open the app and chat on your Claude credits."
    echo "      Keep the link to yourself. (To add a password: APP_PASSWORD=... in .env, restart make dev.)"
  fi
else
  PORT=8001
  OUT="$ROOT/backend/data/public_url.txt"
fi

# Use an installed cloudflared, or download Cloudflare's official one into .tools/ (no Homebrew needed).
CF="$(command -v cloudflared 2>/dev/null || true)"
if [ -z "$CF" ]; then
  CF="$ROOT/.tools/cloudflared"
  if [ ! -x "$CF" ]; then
    case "$(uname -m)" in
      arm64) ARCH=arm64 ;;
      *) ARCH=amd64 ;;
    esac
    URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$ARCH.tgz"
    echo "Downloading cloudflared (one time, ~20 MB) from Cloudflare's GitHub..."
    mkdir -p "$ROOT/.tools"
    TMP="$(mktemp -d)"
    if ! curl -fL --progress-bar -o "$TMP/cf.tgz" "$URL" || ! tar -xzf "$TMP/cf.tgz" -C "$TMP"; then
      echo "Download failed. Check your internet connection and try again."
      rm -rf "$TMP"
      exit 1
    fi
    mv "$TMP/cloudflared" "$CF"
    chmod +x "$CF"
    rm -rf "$TMP"
    echo "Installed: $CF"
  fi
fi
if ! curl -s --max-time 2 "http://127.0.0.1:$PORT/" >/dev/null; then
  echo "Heads up: nothing is running on port $PORT yet. Start 'make dev' in another terminal."
fi

rm -f "$OUT"
LOG="$(mktemp)"
"$CF" tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" >"$LOG" 2>&1 &
CF_PID=$!
TIMER_PID=""
cleanup() {
  kill "$CF_PID" 2>/dev/null
  [ -n "$TIMER_PID" ] && kill "$TIMER_PID" 2>/dev/null
  rm -f "$OUT" "$LOG"
  echo ""
  echo "Public link stopped. It no longer works."
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# The shared web app link switches itself off after SHARE_MINUTES (default 120).
LIMIT_SECONDS=""
if [ "$MODE" = "share" ]; then
  LIMIT_SECONDS="${SHARE_SECONDS:-$(( ${SHARE_MINUTES:-120} * 60 ))}"
  ( sleep "$LIMIT_SECONDS"; echo "" ; echo "Time's up: the link has expired."; kill "$CF_PID" 2>/dev/null ) &
  TIMER_PID=$!
fi

echo "Starting a public link (takes ~10-20 seconds)..."
shown=""
waited=0
while kill -0 "$CF_PID" 2>/dev/null; do
  if [ -z "$shown" ]; then
    url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1)"
    if [ -n "$url" ]; then
      shown=1
      expires=""
      if [ -n "$LIMIT_SECONDS" ]; then
        expires="$(date -v+"${LIMIT_SECONDS}"S '+%-I:%M %p' 2>/dev/null || date -d "+${LIMIT_SECONDS} seconds" '+%-I:%M %p' 2>/dev/null)"
      fi
      printf '%s\n' "$url" > "$OUT"
      [ -n "$expires" ] && printf 'expires %s\n' "$expires" >> "$OUT"
      echo ""
      echo "  Public link ready: $url"
      if [ "$MODE" = "share" ]; then
        [ -n "$expires" ] && echo "  It switches off automatically at $expires (in $(( LIMIT_SECONDS / 60 )) minutes)."
        if [ -n "$PW" ]; then
          echo "  Login: any username, password = APP_PASSWORD from .env."
        else
          echo "  Keep it private: it isn't password-protected."
        fi
      else
        echo "  The app already has it: AI apps -> Connect an app -> ChatGPT or Claude (web)."
      fi
      echo "  Keep this terminal open. Ctrl+C stops the link now."
      echo ""
    else
      waited=$((waited + 1))
      if [ "$waited" -eq 45 ]; then
        echo "Still waiting for Cloudflare. Last messages:"
        tail -5 "$LOG"
      fi
    fi
  fi
  sleep 1
done

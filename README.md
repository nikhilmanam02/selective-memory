# Selective Memory

**One memory for all your AIs. Your rules.**

Selective Memory is a personal memory hub. You chat with it (powered by Claude), and it decides what to
remember the way a thoughtful assistant would. It saves simple things quietly, asks about sensitive
things, and uses secrets once and then deletes them. Other AI apps (Claude Desktop, Cursor, VS Code)
connect to the same memory through MCP, and each app only sees the zone you give it.

Built for super{set} hackathon, Track 2: personal agents, data privacy and user consent.

---

## Run it in VS Code (Mac)

**You need:** Python 3.9+ (already on your Mac) and an Anthropic API key from
[console.anthropic.com](https://console.anthropic.com). Node.js is bundled in `.tools/node`.

1. **Open the folder.** In VS Code: File → Open Folder → `selective-memory`.
2. **Open a terminal.** Terminal → New Terminal (or `` Ctrl+` ``).
3. **Install everything (first time only):**
   ```bash
   make setup
   ```
4. **Add your key.** Open `.env` in the sidebar and set:
   ```dotenv
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
   Save the file. Never commit or share it (it's already in `.gitignore`).
5. **Start the app:**
   ```bash
   make dev
   ```
   In a second terminal, `make check` tells you if anything is missing and how to fix it.
   This starts three things together: the backend (port 8000), the web app (port 5173) and the
   MCP server (port 8001). Leave this terminal running.
6. **Open the app:** <http://localhost:5173>. The header should say **Claude connected**.

To stop the app, press `Ctrl+C` in that terminal. If you change `.env`, stop it and run `make dev` again.

> **Shortcut:** VS Code → Terminal → Run Task… → **Start Selective Memory** does step 5 for you.

### If something goes wrong

| You see | Fix |
| --- | --- |
| "Claude not set up" banner | `.env` still has no real key. Add it, then restart `make dev`. |
| "Backend isn't running" banner | The `make dev` terminal stopped. Check the error there and run it again. |
| `Address already in use` | An old copy is still running. Run `lsof -ti:8000,8001,5173 \| xargs kill`, then `make dev`. |
| Claude replies "rejected the API key" | The key is wrong or has no credit. Check it in the Anthropic console. |

---

## How it decides what to remember

The LLM only *proposes* facts. Plain Python (`backend/app/policy.py`) makes the decision, so every
decision is predictable, testable and explained in the UI.

| You say | What happens |
| --- | --- |
| "I'm vegetarian" | Saved quietly. A **Noted** chip appears with **Undo**. |
| "I'm in Seattle until Sunday" | Saved with an expiry, then deleted automatically. |
| "My card is 4111…" | Hidden from Claude, used once for this reply, then hard-deleted. |
| "I got diagnosed with ADHD" | Asked first: Remember forever / Only in Health / Just this chat / Don't remember. |
| "What's the weather?" | Nothing saved. |
| "Remember this", "Don't remember this", "Forget my Seattle trip", "Keep this in health only" | Followed exactly. |

**It learns.** Pick the same answer 3 times for a kind of fact and it stops asking. Undo twice and it
starts asking again. You can see and change all of this in **Settings** (sliders icon).

**Zones.** Personal, Work, Health, Finance. Memories marked "Everywhere" are usable in every zone;
the rest only in their own zone. Health details are hidden from Claude unless you're chatting in Health.

**Deletion you can prove.** Deletes are real `DELETE`s. Each one leaves a receipt with only a
SHA-256 fingerprint. **Verify deletion** searches every memory and every stored chat message.

---

## Connect other AI apps (MCP)

Open the **AI apps** page → **Connect an app** → pick the app, tick which zones it may read, choose
whether it may save new memories → follow the steps it shows.

| App | How it connects | Extra step |
| --- | --- | --- |
| Claude Desktop | Runs our `mcp-server/stdio.js` on your Mac | Click "Add to Claude Desktop for me", then restart Claude (⌘Q) |
| Cursor, VS Code | `http://127.0.0.1:8001/mcp` + a key header | Paste the config |
| ChatGPT (Plus/Pro, Developer mode) | Public link `https://…/mcp/<key>` | Run `make tunnel` first |
| Claude on the web (claude.ai) | Public link `https://…/mcp/<key>`, as a custom connector | Run `make tunnel` first |

ChatGPT and claude.ai run in the cloud, so they can't see `localhost`. `make tunnel` (downloads Cloudflare's
`cloudflared` tool the first time, no Homebrew needed) prints an address like `https://quiet-river.trycloudflare.com`,
and the connect form picks it up automatically. Keep both `make dev` and `make tunnel` running. The address changes each
time you restart the tunnel, so reconnect the web apps after a restart.

**Control what each AI has**, on the **Your data** home page:
- Every memory is **Open to AIs** (all connected AIs), **Sensitive** (no AI ever sees it), or **Choose AIs** (tick e.g. ChatGPT yes, Claude no).
- Health, money and similar facts start as **Sensitive**. You open them up if you want.
- Click **What ChatGPT has** / **What Claude has** to see exactly what that AI gets when it asks about you.
- **Add** anything yourself with the box at the top.
- On **AI apps**: connect apps, switch off "Can save new memories" to make one read-only, and watch the live **Activity** list.

**The proof demo:** add *"I'm vegetarian and I love Japanese food"* (Open to AIs). Then in ChatGPT or
Claude ask *"Suggest a few restaurants for dinner tonight."* It calls `recall_memories` first and should
only suggest vegetarian-friendly Japanese places. Mark "vegetarian" Sensitive, ask again, and the answer changes.

Tools the connected AI gets: `recall_memories`, `remember_fact`, `forget_memory`, `import_memories`.

**Moving memories in:** the connect screen has a ready-made prompt. The AI lists what it remembers,
you approve, and it sends only those. Then turn off that app's own memory so this hub is the only copy.
(Connecting can't read or delete what an AI company stores on its own servers. That's done in each
app's settings.)

## Which address is which

| Address | What it is |
| --- | --- |
| <http://localhost:5173> | **The app. Use this one.** Live-reloads while you edit code. |
| <http://localhost:8000> | The backend. It also serves a built copy of the app, so it looks the same. API docs: <http://localhost:8000/docs> |
| <http://localhost:8001> | The MCP server for AI apps. Its page just says it's running. |
| `backend/data/memory.db` | The database (SQLite). Open it with the VS Code "SQLite Viewer" extension. |

## Commands

```bash
make setup   # install Python + Node dependencies, run tests
make dev     # run backend + web app + MCP server
make test    # backend tests (no API calls)
make clear   # delete all memories and chat history (backend must be running)
make check   # checks every piece (key, servers, Claude Desktop, tunnel) and says how to fix it
make tunnel  # public https link so ChatGPT / claude.ai can reach your MCP server
make serve   # production build served at http://localhost:8000
```

## Project layout

```
backend/app/
  policy.py         decision rules (save / ask / use once / ignore)
  learning.py       learns your answers, per category
  memory_store.py   SQLite storage, zones, expiry, receipts, verify-deletion
  extractor.py      local secret + sensitive detection, then Claude extraction
  llm.py            Claude adapter (strict tool schemas)
  chat_service.py   one chat turn, end to end
  hub_service.py    what connected AI apps can recall / remember / forget
  main.py           REST API
backend/data/memory.db   your memories (created on first run, git-ignored)
mcp-server/
  tools.js          MCP tools (shared)
  stdio.js          for Claude Desktop
  index.js          HTTP for Cursor / VS Code at http://127.0.0.1:8001/mcp
frontend/src/       React + Tailwind UI
```

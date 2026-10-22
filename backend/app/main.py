from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import chat_service, connections, hub_service, learning, memory_store
from app.config import settings
from app.db import get_db
from app.models import (
    AnswerRequest,
    ChatRequest,
    ConnectionCreate,
    ConnectionUpdate,
    ManualMemoryCreate,
    MCPImportRequest,
    MCPRecallRequest,
    MCPRememberRequest,
    MemoryPatch,
    PreferenceUpdate,
    VerifyDeletionRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app):
    with get_db() as connection:
        # Creates the database on first start, and removes the sample rows an
        # earlier version inserted automatically.
        connection.execute(
            "DELETE FROM memories WHERE decision_reason = 'Seeded demo memory'"
        )
    yield


app = FastAPI(title="Selective Memory", version="0.1.0", lifespan=lifespan)


PUBLIC_HEADERS = ("cf-connecting-ip", "x-forwarded-for", "x-forwarded-host")


@app.middleware("http")
async def password_for_public_visitors(request, call_next):
    """If APP_PASSWORD is set, visitors arriving through a public link must log in;
    you on localhost never do. Without a password the link opens straight away.
    MCP calls carry their own per-app key, so they are exempt."""
    from fastapi.responses import Response

    from_tunnel = any(h in request.headers for h in PUBLIC_HEADERS)
    if not from_tunnel or request.url.path.startswith("/api/mcp/"):
        return await call_next(request)
    password = settings.app_password
    if not password:
        # No password chosen: the random public link itself is the only key.
        return await call_next(request)
    import base64
    import secrets as _secrets

    supplied = ""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            supplied = base64.b64decode(header[6:]).decode("utf-8").split(":", 1)[-1]
        except Exception:  # noqa: BLE001
            supplied = ""
    if not _secrets.compare_digest(supplied.encode(), password.encode()):
        return Response(
            "Password required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Selective Memory"'},
        )
    return await call_next(request)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORIES = chat_service.CATEGORIES
ZONES = {"global", "personal", "work", "health", "finance"}
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _key_configured():
    key = settings.anthropic_api_key or ""
    return bool(key) and key != "replace-with-your-own-key"


@app.get("/api/health")
def health():
    configured = _key_configured()
    return {
        "ok": True,
        "configured": configured,
        "model": settings.anthropic_model if configured else None,
    }


PUBLIC_URL_FILE = PROJECT_ROOT / "backend" / "data" / "public_url.txt"
CLAUDE_DESKTOP_CONFIG = (
    Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
)


def _node_path():
    bundled = PROJECT_ROOT / ".tools" / "node" / "bin" / "node"
    return str(bundled) if bundled.exists() else "node"


def _public_url():
    """Written by `make tunnel` while it runs, removed when it stops."""
    if PUBLIC_URL_FILE.exists():
        url = PUBLIC_URL_FILE.read_text().strip()
        if url.startswith("https://"):
            return url
    return settings.public_mcp_url or None


class ClaudeDesktopInstall(BaseModel):
    token: str = Field(min_length=20, max_length=200)


@app.post("/api/claude-desktop/install")
def install_claude_desktop(payload: ClaudeDesktopInstall):
    """Adds Selective Memory to Claude Desktop's config file on this Mac (keeps a backup)."""
    import json
    import shutil

    folder = CLAUDE_DESKTOP_CONFIG.parent
    if not folder.exists():
        raise HTTPException(
            status_code=404,
            detail="Claude Desktop doesn't seem to be installed on this Mac. Install it from claude.ai/download, open it once, then try again.",
        )
    config = {}
    if CLAUDE_DESKTOP_CONFIG.exists():
        try:
            config = json.loads(CLAUDE_DESKTOP_CONFIG.read_text() or "{}")
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail="Claude Desktop's config file isn't valid JSON, so I didn't touch it. Use Copy config and paste it in manually.",
            ) from error
        shutil.copy2(CLAUDE_DESKTOP_CONFIG, CLAUDE_DESKTOP_CONFIG.with_suffix(".json.bak"))
    config.setdefault("mcpServers", {})["selective-memory"] = {
        "command": _node_path(),
        "args": [str(PROJECT_ROOT / "mcp-server" / "stdio.js")],
        "env": {"SELECTIVE_MEMORY_TOKEN": payload.token},
    }
    CLAUDE_DESKTOP_CONFIG.write_text(json.dumps(config, indent=2))
    return {"ok": True, "path": str(CLAUDE_DESKTOP_CONFIG)}


@app.get("/api/setup")
def setup_info():
    """Paths the UI needs to show copy-paste MCP configs for this computer."""
    return {
        "project_root": str(PROJECT_ROOT),
        "node_path": _node_path(),
        "stdio_script": str(PROJECT_ROOT / "mcp-server" / "stdio.js"),
        "mcp_url": "http://127.0.0.1:8001/mcp",
        "public_url": _public_url(),
        "claude_desktop_installed": CLAUDE_DESKTOP_CONFIG.parent.exists(),
    }


@app.get("/api/connections")
def list_connections():
    with get_db() as connection:
        return {"connections": connections.list_connections(connection)}


@app.post("/api/connections")
def add_connection(payload: ConnectionCreate):
    zones = payload.zones if payload.zone is None else [payload.zone]
    with get_db() as connection:
        return connections.create_connection(
            connection, payload.name, zones, payload.can_write
        )


@app.patch("/api/connections/{connection_id}")
def edit_connection(connection_id: int, payload: ConnectionUpdate):
    with get_db() as connection:
        updated = connections.update_connection(
            connection, connection_id, payload.zones, payload.can_write
        )
        if not updated:
            raise HTTPException(status_code=404, detail="AI app not found.")
        return updated


@app.get("/api/connections/{connection_id}/preview")
def preview_connection(connection_id: int):
    """Exactly what this AI app would receive from recall_memories right now."""
    with get_db() as connection:
        profile = connections.get_connection(connection, connection_id)
        if not profile:
            raise HTTPException(status_code=404, detail="AI app not found.")
        visible = memory_store.visible_to_app(connection, profile["id"])
        return {"memories": visible}


@app.get("/api/activity")
def activity(limit: int = Query(default=60, ge=1, le=200)):
    with get_db() as connection:
        return {"activity": memory_store.list_activity(connection, limit)}


@app.delete("/api/connections/{connection_id}")
def delete_connection(connection_id: int):
    with get_db() as connection:
        connection.execute("DELETE FROM memory_access WHERE connection_id = ?", (connection_id,))
        if not connections.revoke_connection(connection, connection_id):
            raise HTTPException(status_code=404, detail="MCP connection not found.")
        return {"revoked": True}


def _mcp_profile(authorization):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    with get_db() as connection:
        profile = connections.authenticate(connection, token)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid or revoked hub connection token.")
    return profile


@app.get("/api/mcp/profile")
def mcp_profile(authorization: Optional[str] = Header(default=None)):
    return _mcp_profile(authorization)


@app.post("/api/mcp/recall")
def mcp_recall(
    payload: MCPRecallRequest,
    authorization: Optional[str] = Header(default=None),
):
    profile = _mcp_profile(authorization)
    with get_db() as connection:
        return hub_service.recall(connection, profile, payload.query)


@app.post("/api/mcp/remember")
def mcp_remember(
    payload: MCPRememberRequest,
    authorization: Optional[str] = Header(default=None),
):
    profile = _mcp_profile(authorization)
    with get_db() as connection:
        return hub_service.remember(connection, profile, payload.fact, profile["name"])


@app.post("/api/mcp/forget")
def mcp_forget(
    payload: MCPRecallRequest,
    authorization: Optional[str] = Header(default=None),
):
    profile = _mcp_profile(authorization)
    with get_db() as connection:
        return hub_service.forget(connection, profile, payload.query)


@app.post("/api/mcp/import")
def mcp_import(
    payload: MCPImportRequest,
    authorization: Optional[str] = Header(default=None),
):
    profile = _mcp_profile(authorization)
    with get_db() as connection:
        return hub_service.import_facts(
            connection, profile, payload.source, payload.facts
        )


@app.post("/api/chat")
def chat(payload: ChatRequest):
    try:
        with get_db() as connection:
            return chat_service.handle_message(
                connection, payload.session_id, payload.zone, payload.message
            )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Chat turn failed")
        raise HTTPException(status_code=500, detail="The chat turn failed safely.") from error


@app.get("/api/memories")
def memories(
    status: Optional[str] = Query(default=None, pattern="^(active|pending)$"),
    rule: Optional[str] = Query(
        default=None, pattern="^(forever|temporary|zone_only|one_time|session)$"
    ),
    zone: Optional[str] = Query(default=None, pattern="^(global|personal|work|health|finance)$"),
):
    with get_db() as connection:
        return {"memories": memory_store.list_memories(connection, status, rule, zone)}


@app.post("/api/memories")
def add_manual_memory(payload: ManualMemoryCreate):
    """You typed it in yourself, so it is saved directly (no approval step)."""
    with get_db() as connection:
        record = memory_store.insert_memory(
            connection,
            content=payload.content.strip(),
            short=payload.short.strip(),
            category=payload.category,
            zone=payload.zone,
            rule="forever" if payload.zone == "global" else "zone_only",
            sensitivity=payload.sensitivity,
            reason="You added this yourself.",
            source="You",
            visibility=payload.visibility,
        )
        return {"status": "saved", "memory": record}


@app.post("/api/memories/{memory_id}/answer")
def answer_memory(memory_id: int, payload: AnswerRequest):
    with get_db() as connection:
        memory = memory_store.get_memory(connection, memory_id)
        if not memory or memory["status"] != "pending":
            raise HTTPException(status_code=404, detail="Pending memory not found.")
        if payload.choice == "decline":
            receipt = memory_store.delete_memory(connection, memory_id, "user_declined")
            learning.record_choice(connection, memory["category"], "decline", memory["zone"])
            return {"deleted": receipt, "learned": None}

        rule = payload.choice
        zone = "global" if rule == "forever" else (
            payload.zone or memory["zone"] if rule == "zone_only" else memory["zone"]
        )
        connection.execute(
            """
            UPDATE memories SET status='active', rule=?, zone=?, session_id=?
            WHERE id=?
            """,
            (rule, zone, memory["session_id"], memory_id),
        )
        if payload.visibility:
            memory_store.set_access(connection, memory_id, payload.visibility)
        learned = learning.record_choice(
            connection, memory["category"], payload.choice, zone
        )
        return {
            "memory": memory_store.get_memory(connection, memory_id),
            "learned": learned,
        }


@app.post("/api/memories/{memory_id}/undo")
def undo_memory(memory_id: int):
    with get_db() as connection:
        memory = memory_store.get_memory(connection, memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found.")
        receipt = memory_store.delete_memory(connection, memory_id, "user_undo")
        learned = learning.record_choice(
            connection, memory["category"], "undo", memory["zone"]
        )
        return {"deleted": receipt, "learned": learned}


@app.patch("/api/memories/{memory_id}")
def update_memory(memory_id: int, payload: MemoryPatch):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide a memory field to update.")
    with get_db() as connection:
        memory = memory_store.get_memory(connection, memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found.")
        changes = {key: value for key, value in changes.items() if value is not None}
        if not changes:
            raise HTTPException(status_code=400, detail="No valid changes were provided.")
        if changes.get("rule", memory["rule"]) == "temporary" and not (
            changes.get("expires_at", memory["expires_at"])
        ):
            raise HTTPException(status_code=400, detail="Temporary memories need an expiry.")
        if "visibility" in changes or "apps" in changes:
            memory_store.set_access(
                connection,
                memory_id,
                changes.pop("visibility", None) or memory["visibility"],
                changes.pop("apps", None),
            )
            if not changes:
                return {"memory": memory_store.get_memory(connection, memory_id)}
        if changes.get("rule") and changes["rule"] not in ("temporary",):
            changes["expires_at"] = None  # e.g. temporary -> forever keeps it for good
        if changes.get("rule") in ("forever", "zone_only"):
            changes["session_id"] = None
        assignments = ", ".join(f"{key} = ?" for key in changes)
        connection.execute(
            f"UPDATE memories SET {assignments} WHERE id = ?",
            (*changes.values(), memory_id),
        )
        return {"memory": memory_store.get_memory(connection, memory_id)}


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: int):
    with get_db() as connection:
        receipt = memory_store.delete_memory(connection, memory_id, "user_deleted")
        if not receipt:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"deleted": receipt}


@app.post("/api/zones/{zone}/wipe")
def wipe_zone(zone: str):
    if zone not in ZONES:
        raise HTTPException(status_code=404, detail="Unknown zone.")
    with get_db() as connection:
        rows = connection.execute("SELECT id FROM memories WHERE zone = ?", (zone,)).fetchall()
        deleted = [
            receipt
            for row in rows
            if (receipt := memory_store.delete_memory(connection, row["id"], "zone_wiped"))
        ]
        return {"deleted": len(deleted), "zone": zone}


@app.post("/api/sessions/{session_id}/end")
def end_session(session_id: str):
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id FROM memories WHERE session_id = ? AND rule IN ('one_time', 'session')",
            (session_id,),
        ).fetchall()
        deleted = [
            receipt
            for row in rows
            if (receipt := memory_store.delete_memory(connection, row["id"], "session_ended"))
        ]
        return {"deleted": len(deleted)}


@app.get("/api/prefs")
def preferences():
    with get_db() as connection:
        return {"preferences": learning.get_all_preferences(connection, CATEGORIES)}


@app.put("/api/prefs/{category}")
def update_preference(category: str, payload: PreferenceUpdate):
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail="Unknown memory category.")
    if category == "secret" and payload.behavior != "use_once":
        raise HTTPException(status_code=400, detail="Secrets can only be used once.")
    with get_db() as connection:
        learning.set_manual_preference(
            connection, category, payload.behavior, payload.zone
        )
        return {"preferences": learning.get_all_preferences(connection, CATEGORIES)}


@app.post("/api/prefs/reset")
def reset_preferences():
    with get_db() as connection:
        connection.execute("DELETE FROM learned_prefs")
        connection.execute("DELETE FROM ask_answers")
        return {"ok": True}


@app.get("/api/receipts")
def get_receipts():
    with get_db() as connection:
        return {"receipts": memory_store.receipts(connection)}


@app.post("/api/verify-deletion")
def verify_deletion(payload: VerifyDeletionRequest):
    with get_db() as connection:
        return memory_store.verify_deletion(connection, payload.text)


@app.post("/api/data/clear")
def clear_all_data():
    """Delete every memory and chat message (keeps hash-only receipts and AI connections)."""
    with get_db() as connection:
        rows = connection.execute("SELECT id FROM memories").fetchall()
        for row in rows:
            memory_store.delete_memory(connection, row["id"], "user_deleted")
        connection.execute("DELETE FROM messages")
        connection.execute("DELETE FROM activity")
        connection.execute("DELETE FROM memory_access")
        return {"ok": True, "deleted": len(rows)}


if FRONTEND_DIST.is_dir():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

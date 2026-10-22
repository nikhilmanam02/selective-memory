import hashlib
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def insert_memory(
    connection,
    *,
    content,
    short,
    source="You",
    category,
    zone,
    rule,
    sensitivity,
    status="active",
    reason=None,
    session_id=None,
    expires_at=None,
    source_text=None,
    visibility=None,
):
    if visibility not in ("open", "sensitive"):
        # Private by default for anything sensitive; the user can open it up.
        visibility = "sensitive" if sensitivity == "high" else "open"
    cursor = connection.execute(
        """
        INSERT INTO memories(
          content, short, source, category, zone, rule, sensitivity, status,
          decision_reason, session_id, expires_at, source_text, created_at,
          visibility, shared
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content,
            short,
            source,
            category,
            zone,
            rule,
            sensitivity,
            status,
            reason,
            session_id,
            expires_at,
            source_text if category != "secret" else None,
            now_iso(),
            visibility,
            0 if visibility == "sensitive" else 1,
        ),
    )
    return get_memory(connection, cursor.lastrowid)


def _with_access(connection, memory):
    memory["apps"] = [
        r["connection_id"]
        for r in connection.execute(
            "SELECT connection_id FROM memory_access WHERE memory_id = ?", (memory["id"],)
        )
    ]
    return memory


def get_memory(connection, memory_id):
    row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return _with_access(connection, dict(row)) if row else None


def set_access(connection, memory_id, visibility, app_ids=None):
    """open = all connected AIs, sensitive = none, custom = only app_ids."""
    connection.execute("DELETE FROM memory_access WHERE memory_id = ?", (memory_id,))
    if visibility == "custom":
        app_ids = sorted(set(int(i) for i in (app_ids or [])))
        if not app_ids:
            visibility = "sensitive"
        for app_id in app_ids:
            connection.execute(
                "INSERT INTO memory_access(memory_id, connection_id) VALUES (?, ?)",
                (memory_id, app_id),
            )
    connection.execute(
        "UPDATE memories SET visibility = ?, shared = ? WHERE id = ?",
        (visibility, 0 if visibility == "sensitive" else 1, memory_id),
    )
    return get_memory(connection, memory_id)


def list_memories(connection, status=None, rule=None, zone=None):
    clauses, values = [], []
    for column, value in (("status", status), ("rule", rule), ("zone", zone)):
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM memories{where} ORDER BY created_at DESC, id DESC", values
    ).fetchall()
    access = {}
    for r in connection.execute("SELECT memory_id, connection_id FROM memory_access"):
        access.setdefault(r["memory_id"], []).append(r["connection_id"])
    return [{**dict(row), "apps": access.get(row["id"], [])} for row in rows]


def allowed_for(connection, zone, session_id):
    current_time = now_iso()
    rows = connection.execute(
        """
        SELECT * FROM memories
        WHERE status = 'active'
          AND (expires_at IS NULL OR expires_at > ?)
          AND (
            rule = 'forever'
            OR (rule = 'temporary' AND (zone = 'global' OR zone = ?))
            OR (rule = 'zone_only' AND zone = ?)
            OR (rule IN ('one_time', 'session') AND session_id = ?)
          )
        ORDER BY created_at, id
        """,
        (current_time, zone, zone, session_id),
    )
    return [dict(row) for row in rows]


def withheld_counts(connection, zone, session_id):
    allowed_ids = {
        memory["id"] for memory in allowed_for(connection, zone, session_id)
    }
    rows = connection.execute(
        "SELECT id, zone FROM memories WHERE status = 'active'"
    ).fetchall()
    counts = {}
    for row in rows:
        if row["id"] not in allowed_ids:
            counts[row["zone"]] = counts.get(row["zone"], 0) + 1
    return counts


def delete_memory(connection, memory_id, reason):
    memory = get_memory(connection, memory_id)
    if not memory:
        return None
    digest = hashlib.sha256(memory["content"].encode("utf-8")).hexdigest()
    connection.execute(
        """
        INSERT INTO deletion_receipts(
          memory_id, content_hash, category, rule, zone, reason, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            memory["id"],
            digest,
            memory["category"],
            memory["rule"],
            memory["zone"],
            reason,
            now_iso(),
        ),
    )
    connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    connection.execute("DELETE FROM memory_access WHERE memory_id = ?", (memory_id,))
    return {
        "memory_id": memory["id"],
        "content_hash": digest[:12],
        "reason": reason,
        "short": memory["short"],
    }


STOP_WORDS = {
    "the", "a", "an", "that", "this", "my", "i", "im", "am", "is", "was", "about",
    "what", "said", "me", "user", "users", "to", "of", "and", "in", "on", "for",
    "please", "it", "everything",
}


def _words(text):
    return {
        word for word in re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
        if word not in STOP_WORDS and len(word) > 1
    }


def find_matching(connection, target):
    """Active memories that clearly match a phrase like 'my Seattle trip'."""
    wanted = _words(target)
    if not wanted:
        return []
    rows = connection.execute(
        "SELECT id, content, short FROM memories WHERE status = 'active'"
    ).fetchall()
    matches = []
    for row in rows:
        have = _words(row["content"]) | _words(row["short"])
        overlap = len(wanted & have) / len(wanted)
        similarity = SequenceMatcher(
            None, " ".join(sorted(wanted)), " ".join(sorted(have))
        ).ratio()
        if overlap >= 0.5 or similarity >= 0.8:
            matches.append(dict(row))
    return matches


def delete_matching(connection, target, reason="user_command"):
    deleted = []
    for row in find_matching(connection, target):
        receipt = delete_memory(connection, row["id"], reason)
        if receipt:
            deleted.append(receipt)
    return deleted


def sweep_expired(connection):
    rows = connection.execute(
        """
        SELECT id FROM memories
        WHERE rule = 'temporary' AND status = 'active'
          AND expires_at IS NOT NULL AND expires_at <= ?
        """,
        (now_iso(),),
    ).fetchall()
    return [delete_memory(connection, row["id"], "expired") for row in rows]


def mark_used(connection, memory_ids):
    now = now_iso()
    for memory_id in set(memory_ids):
        connection.execute(
            "UPDATE memories SET last_used_at = ?, use_count = use_count + 1 WHERE id = ? AND status = 'active'",
            (now, memory_id),
        )


def add_message(connection, session_id, zone, role, content):
    connection.execute(
        "INSERT INTO messages(session_id, zone, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, zone, role, content, now_iso()),
    )


def recent_history(connection, session_id, limit=12):
    rows = connection.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def scrub_text(connection, session_id, sensitive_span):
    if not sensitive_span:
        return
    rows = connection.execute(
        "SELECT id, content FROM messages WHERE session_id = ?", (session_id,)
    ).fetchall()
    for row in rows:
        if sensitive_span in row["content"]:
            connection.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (row["content"].replace(sensitive_span, "[forgotten]"), row["id"]),
            )


def receipts(connection):
    rows = connection.execute(
        "SELECT * FROM deletion_receipts ORDER BY id DESC LIMIT 100"
    )
    return [dict(row) for row in rows]


def verify_deletion(connection, text):
    term = text.casefold()
    memory_matches = connection.execute(
        """
        SELECT COUNT(*) FROM memories
        WHERE instr(lower(content), lower(?)) > 0
           OR instr(lower(COALESCE(source_text, '')), lower(?)) > 0
        """,
        (term, term),
    ).fetchone()[0]
    message_matches = connection.execute(
        "SELECT COUNT(*) FROM messages WHERE instr(lower(content), lower(?)) > 0",
        (term,),
    ).fetchone()[0]
    return {
        "matches": memory_matches + message_matches,
        "tables_checked": ["memories.content", "memories.source_text", "messages.content"],
    }


def visible_to_app(connection, app_id):
    """What one connected AI app may read: active, not expired, not chat-only, and
    either open to all AIs or specifically shared with this app. Sensitive = never."""
    rows = connection.execute(
        """
        SELECT * FROM memories m
        WHERE m.status = 'active'
          AND m.rule NOT IN ('one_time', 'session')
          AND (m.expires_at IS NULL OR m.expires_at > ?)
          AND (
            m.visibility = 'open'
            OR (m.visibility = 'custom' AND EXISTS (
                SELECT 1 FROM memory_access a WHERE a.memory_id = m.id AND a.connection_id = ?))
          )
        ORDER BY m.created_at, m.id
        """,
        (now_iso(), app_id),
    )
    return [dict(row) for row in rows]


def log_activity(connection, profile, action, memory_ids=(), note=None):
    ids = [int(i) for i in memory_ids]
    connection.execute(
        """
        INSERT INTO activity(connection_id, app, action, memory_ids, count, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (profile.get("id"), profile.get("name", "AI app"), action, json.dumps(ids), len(ids), note, now_iso()),
    )


def list_activity(connection, limit=60):
    """Activity stores memory ids only (never text), so deleted memories stay deleted."""
    rows = connection.execute(
        "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    items = []
    for row in rows:
        ids = json.loads(row["memory_ids"] or "[]")
        names = {}
        if ids:
            marks = ",".join("?" for _ in ids)
            for mem in connection.execute(
                f"SELECT id, content FROM memories WHERE id IN ({marks})", ids
            ):
                names[mem["id"]] = mem["content"]
        items.append(
            {
                "id": row["id"],
                "connection_id": row["connection_id"],
                "app": row["app"],
                "action": row["action"],
                "count": row["count"],
                "note": row["note"],
                "created_at": row["created_at"],
                "memories": [names[i] for i in ids if i in names],
                "deleted_count": sum(1 for i in ids if i not in names),
            }
        )
    return items

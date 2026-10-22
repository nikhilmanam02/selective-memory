"""What connected AI apps (Claude, ChatGPT, Cursor...) can do through MCP.

Every call is checked against the permissions the user set for that app on the
AI apps page, and written to the activity log so the user can see it.
"""
from datetime import datetime, timedelta, timezone

from app import learning, memory_store
from app.models import CandidateFact
from app.policy import decide

RECALL_NOTE = (
    "These are the only facts about the user you may rely on. Apply them to your answer: "
    "for recommendations, only suggest options that fit every relevant preference here "
    "(for example diet AND cuisine), and briefly say which preferences you applied. "
    "Facts the user hasn't shared with you are hidden on purpose; never guess them."
)


def recall(connection, profile, query):
    memories = memory_store.visible_to_app(connection, profile["id"])
    memory_store.mark_used(connection, [memory["id"] for memory in memories])
    memory_store.log_activity(
        connection, profile, "read", [m["id"] for m in memories], note=query[:200]
    )
    return {
        "app": profile["name"],
        "memories": [
            {"content": memory["content"], "category": memory["category"]}
            for memory in memories
        ],
        "count": len(memories),
        "instructions": RECALL_NOTE,
    }


def _target_zone(profile, item):
    """Where a new fact is filed (zones organise your data; access is set per memory)."""
    return item.suggested_zone or "global"


def remember(connection, profile, item, source, log=True):
    if not profile.get("can_write", True):
        if log:
            memory_store.log_activity(connection, profile, "blocked", note="Tried to save a memory")
        return {
            "status": "not_saved",
            "reason": "The user hasn't allowed this app to save memories. They can turn it on in Selective Memory → AI apps.",
        }
    if item.category == "secret":
        return {"status": "not_saved", "reason": "Secrets are never stored in the hub."}
    target_zone = _target_zone(profile, item)
    fact = CandidateFact(
        content=item.content,
        short=item.short,
        category=item.category,
        sensitivity=item.sensitivity,
        confidence=item.confidence,
        is_about_user=True,
        is_temporary=item.is_temporary,
        expires_in_hours=item.expires_in_hours,
        suggested_zone=target_zone,
    )
    decision = decide(fact, target_zone if target_zone != "global" else "personal", learning.get_preferences(connection))
    if decision.action in {"IGNORE", "USE_ONCE"}:
        return {"status": "not_saved", "reason": decision.reason}

    expiry = None
    if decision.action != "ASK":
        if decision.expires_in_hours is not None:
            expiry = (datetime.now(timezone.utc) + timedelta(hours=decision.expires_in_hours)).isoformat()
        duplicate = connection.execute(
            "SELECT id FROM memories WHERE status='active' AND lower(content)=lower(?)",
            (item.content.strip(),),
        ).fetchone()
        if duplicate:
            return {"status": "already_saved", "memory_id": duplicate["id"]}

    record = memory_store.insert_memory(
        connection,
        content=item.content.strip(),
        short=item.short.strip(),
        category=item.category,
        zone=decision.zone or target_zone,
        rule=decision.rule or "forever",
        sensitivity=item.sensitivity,
        status="pending" if decision.action == "ASK" else "active",
        reason=decision.reason,
        expires_at=expiry,
        source_text=None,
        source=source,
    )
    if log:
        action = "asked" if record["status"] == "pending" else "saved"
        memory_store.log_activity(connection, profile, action, [record["id"]])
    if record["status"] == "pending":
        return {
            "status": "needs_approval",
            "reason": decision.reason,
            "message": "Saved as pending. Tell the user to approve it in the Selective Memory app.",
        }
    return {"status": "saved", "rule": record["rule"], "zone": record["zone"], "reason": decision.reason}


def forget(connection, profile, query):
    """Delete memories this app can see that match the query (hard delete + receipt)."""
    if not profile.get("can_write", True):
        memory_store.log_activity(connection, profile, "blocked", note="Tried to delete a memory")
        return {"count": 0, "reason": "This app isn't allowed to change memories."}
    visible_ids = {m["id"] for m in memory_store.visible_to_app(connection, profile["id"])}
    matches = [m for m in memory_store.find_matching(connection, query) if m["id"] in visible_ids]
    receipts = [memory_store.delete_memory(connection, m["id"], "user_command") for m in matches]
    memory_store.log_activity(connection, profile, "forgot", note=f"{len(receipts)} deleted")
    return {"forgotten": [r["short"] for r in receipts if r], "count": len(receipts)}


def import_facts(connection, profile, source, facts):
    origin = profile["name"]
    results = [remember(connection, profile, item, origin, log=False) for item in facts]
    saved = sum(r["status"] == "saved" for r in results)
    pending = sum(r["status"] == "needs_approval" for r in results)
    memory_store.log_activity(connection, profile, "imported", note=f"{saved} saved, {pending} waiting for approval")
    return {
        "source": origin,
        "imported": saved,
        "pending_approval": pending,
        "not_saved": sum(r["status"] in {"not_saved", "already_saved"} for r in results),
        "results": results,
    }

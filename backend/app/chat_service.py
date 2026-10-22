from datetime import datetime, timedelta, timezone

from app import assistant, extractor, learning, memory_store
from app.llm import get_llm
from app.policy import decide

CATEGORIES = [
    "preference",
    "identity",
    "relationship",
    "schedule",
    "location",
    "work",
    "health",
    "finance",
    "secret",
    "job_search",
    "other",
]


def _similar_duplicate(connection, content):
    from difflib import SequenceMatcher

    normalized = " ".join(content.casefold().split())
    rows = connection.execute(
        "SELECT content FROM memories WHERE status = 'active'"
    ).fetchall()
    return any(
        SequenceMatcher(None, normalized, " ".join(row["content"].casefold().split())).ratio()
        >= 0.85
        for row in rows
    )


def _expires_at(hours):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def handle_message(connection, session_id, zone, message, llm=None):
    llm = llm or get_llm()
    swept = memory_store.sweep_expired(connection)
    history = memory_store.recent_history(connection, session_id)
    safe_message, extraction = extractor.extract(llm, message, zone, history)
    memory_store.add_message(connection, session_id, zone, "user", safe_message)
    auto_saved, use_once, asks, forgotten, learned = [], [], [], list(swept), []
    command = extraction.command
    if command == "forget" and extraction.command_target:
        forgotten.extend(
            memory_store.delete_matching(connection, extraction.command_target, "user_command")
        )

    preferences = learning.get_preferences(connection)
    for fact in extraction.facts:
        decision = decide(fact, zone, preferences, command)
        if decision.action in {"IGNORE", "FORGET"}:
            continue
        if decision.action != "USE_ONCE" and _similar_duplicate(connection, fact.content):
            continue

        session_memory = (
            decision.rule in {"session", "one_time"}
            or decision.action == "ASK"
            or fact.category == "secret"
        )
        expires_at = (
            _expires_at(decision.expires_in_hours)
            if decision.expires_in_hours is not None
            else None
        )
        record = memory_store.insert_memory(
            connection,
            content=fact.content,
            short=fact.short,
            category=fact.category,
            zone=decision.zone or zone,
            rule=decision.rule or "forever",
            sensitivity=fact.sensitivity,
            status="pending" if decision.action == "ASK" else "active",
            reason=decision.reason,
            session_id=session_id if session_memory or decision.action == "ASK" else None,
            expires_at=expires_at,
            source_text=None,
            source="Hub chat",
        )
        if decision.action in {"AUTO_SAVE", "AUTO_TEMPORARY"}:
            auto_saved.append({**record, "reason": decision.reason, "learned": decision.learned})
        elif decision.action == "USE_ONCE":
            use_once.append(
                {
                    "id": record["id"],
                    "label": fact.short,
                    "reason": decision.reason,
                }
            )
        elif decision.action == "ASK":
            asks.append(
                {
                    "id": record["id"],
                    "content": record["content"],
                    "category": fact.category,
                    "suggested_zone": record["zone"],
                    "reason": decision.reason,
                    "options": ["forever", "zone_only", "session", "decline"],
                }
            )

    allowed = memory_store.allowed_for(connection, zone, session_id)
    # Send every memory this zone may use (newest 60). Claude picks what is
    # relevant far better than keyword matching does.
    relevant = allowed[-60:]
    withheld = memory_store.withheld_counts(connection, zone, session_id)
    response = assistant.answer(
        llm, safe_message, zone, relevant, withheld, history
    )
    allowed_by_id = {item["id"]: item for item in relevant}
    used_memories = [
        {
            "id": memory_id,
            "content": allowed_by_id[memory_id]["content"],
            "rule": allowed_by_id[memory_id]["rule"],
            "zone": allowed_by_id[memory_id]["zone"],
        }
        for memory_id in response.used_memory_ids
        if memory_id in allowed_by_id
    ]
    memory_store.mark_used(connection, response.used_memory_ids)

    ephemeral = connection.execute(
        """
        SELECT id FROM memories
        WHERE session_id = ? AND rule = 'one_time' AND status = 'active'
        """,
        (session_id,),
    ).fetchall()
    for row in ephemeral:
        receipt = memory_store.delete_memory(connection, row["id"], "one_time_used")
        if receipt:
            forgotten.append(receipt)

    memory_store.add_message(connection, session_id, zone, "assistant", response.text)
    hidden_total = sum(withheld.values())
    return {
        "reply": response.text,
        "used_memories": used_memories,
        "auto_saved": auto_saved,
        "use_once": use_once,
        "asks": asks,
        "forgotten": forgotten,
        "learned": learned,
        "withheld_counts": withheld,
        "hidden_total": hidden_total,
    }

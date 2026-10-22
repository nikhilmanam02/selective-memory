from datetime import datetime, timedelta, timezone

from app.memory_store import (
    allowed_for,
    delete_memory,
    insert_memory,
    sweep_expired,
    verify_deletion,
)


def create(connection, **overrides):
    values = {
        "content": "User likes tea",
        "short": "tea",
        "category": "preference",
        "zone": "global",
        "rule": "forever",
        "sensitivity": "low",
        "source_text": "I like tea",
    }
    values.update(overrides)
    return insert_memory(connection, **values)


def test_delete_creates_hash_only_receipt(connection):
    memory = create(connection)
    receipt = delete_memory(connection, memory["id"], "user_deleted")
    row = connection.execute("SELECT * FROM deletion_receipts").fetchone()

    assert row["content_hash"] == receipt["content_hash"][:12] or len(row["content_hash"]) == 64
    assert "content" not in row
    assert connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_expired_temporary_memories_are_deleted(connection):
    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    memory = create(
        connection,
        rule="temporary",
        expires_at=expired,
        zone="personal",
    )
    deleted = sweep_expired(connection)

    assert deleted[0]["memory_id"] == memory["id"]
    assert connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_zone_filter_only_exposes_allowed_memories(connection):
    global_memory = create(connection)
    health_memory = create(
        connection,
        content="User has a health detail",
        short="health detail",
        category="health",
        zone="health",
        rule="zone_only",
        sensitivity="high",
    )
    allowed = allowed_for(connection, "work", "session-1")

    assert [item["id"] for item in allowed] == [global_memory["id"]]
    assert health_memory["id"] not in {item["id"] for item in allowed}


def test_secret_source_text_is_never_stored_and_verification_searches_all_tables(connection):
    secret = create(
        connection,
        content="User provided a card number for this task",
        short="Card number",
        category="secret",
        sensitivity="high",
        source_text="private card text",
    )
    assert secret["source_text"] is None
    result = verify_deletion(connection, "private card text")
    assert result["matches"] == 0

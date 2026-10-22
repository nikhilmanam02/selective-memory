from app.chat_service import handle_message
from app.llm import MockLLM
from app.memory_store import verify_deletion


def test_secret_is_redacted_then_hard_deleted(connection):
    secret = "4111 1111 1111 1111"
    result = handle_message(
        connection,
        "session-secret",
        "personal",
        f"Book this with my card number {secret}",
        MockLLM(),
    )

    assert result["use_once"][0]["label"] == "Card number"
    assert any(item["reason"] == "one_time_used" for item in result["forgotten"])
    assert connection.execute("SELECT COUNT(*) FROM memories WHERE category='secret'").fetchone()[0] == 0
    assert verify_deletion(connection, secret)["matches"] == 0
    stored = connection.execute("SELECT content FROM messages").fetchall()
    assert all(secret not in row["content"] for row in stored)

from app.chat_service import handle_message
from app.llm import MockLLM


def test_preference_saves_without_prompt_and_is_used(connection):
    result = handle_message(
        connection,
        "session-chat",
        "personal",
        "I love spicy food",
        MockLLM(),
    )

    assert len(result["auto_saved"]) == 1
    assert result["asks"] == []
    dinner = handle_message(
        connection,
        "session-chat",
        "personal",
        "Suggest a dinner spot for tonight",
        MockLLM(),
    )
    assert dinner["used_memories"][0]["content"].lower().endswith("spicy food")


def test_sensitive_health_fact_creates_pending_ask(connection):
    result = handle_message(
        connection,
        "session-health",
        "health",
        "I just got diagnosed with ADHD",
        MockLLM(),
    )
    assert result["asks"][0]["category"] == "health"
    assert result["asks"][0]["options"] == ["forever", "zone_only", "session", "decline"]


def test_dont_remember_overrides_auto_save(connection):
    result = handle_message(
        connection,
        "session-no-save",
        "personal",
        "I love spicy food. Don't remember this.",
        MockLLM(),
    )
    assert result["auto_saved"] == []
    assert connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_forgotten_command_hard_deletes_matching_fact(connection):
    handle_message(connection, "session-forget", "personal", "I love spicy food", MockLLM())
    result = handle_message(
        connection,
        "session-forget",
        "personal",
        "forget spicy food",
        MockLLM(),
    )
    assert result["forgotten"]
    assert connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_forget_only_deletes_matching_memory(connection):
    handle_message(connection, "s-f2", "personal", "I love spicy food", MockLLM())
    handle_message(connection, "s-f2", "personal", "I'm in Seattle until Sunday", MockLLM())
    result = handle_message(connection, "s-f2", "personal", "forget my Seattle trip", MockLLM())
    assert [item["short"] for item in result["forgotten"]] == ["Seattle trip"]
    remaining = [row[0] for row in connection.execute("SELECT short FROM memories")]
    assert len(remaining) == 1 and "spicy" in remaining[0]


def test_conversation_history_is_passed_to_the_model(connection):
    class Spy(MockLLM):
        seen = None

        def answer(self, message, zone, allowed, withheld_counts, history):
            Spy.seen = history
            return super().answer(message, zone, allowed, withheld_counts, history)

    handle_message(connection, "s-h", "personal", "Hello there", Spy())
    handle_message(connection, "s-h", "personal", "And again", Spy())
    assert [item["content"] for item in Spy.seen][:1] == ["Hello there"]

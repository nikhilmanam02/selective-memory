from app.extractor import extract
from app.llm import MockLLM


class CapturingLLM(MockLLM):
    def __init__(self):
        self.received_message = None
        self.received_history = None

    def extract(self, message, zone, history):
        self.received_message = message
        self.received_history = history
        return super().extract(message, zone, history)


def test_sensitive_health_text_is_redacted_before_llm():
    llm = CapturingLLM()
    original = "I was diagnosed with ADHD and I'm seeing Dr. Example."

    safe_message, result = extract(llm, original, "personal", [])

    assert original not in llm.received_message
    assert "ADHD" not in llm.received_message
    assert "Example" not in llm.received_message
    assert "[private detail withheld until you approve]" in safe_message
    assert result.facts[0].category == "health"
    assert "ADHD" in result.facts[0].content
    assert llm.received_history == []


def test_password_is_redacted_before_llm_and_never_becomes_source_text():
    llm = CapturingLLM()
    _, result = extract(llm, "My password is correct-horse-123", "personal", [])

    assert "correct-horse-123" not in llm.received_message
    assert result.facts[0].category == "secret"
    assert result.facts[0].sensitive_span == "correct-horse-123"


def test_sensitive_sentence_with_name_abbreviation_is_fully_redacted():
    llm = CapturingLLM()
    original = "I was diagnosed with ADHD and I'm seeing Dr. Example."

    _safe_message, result = extract(llm, original, "personal", [])

    assert "Example" not in llm.received_message
    assert "ADHD" not in llm.received_message
    assert result.facts[0].category == "health"
    assert "Dr. Example" in result.facts[0].content


def test_explicit_memory_command_is_read_locally():
    llm = CapturingLLM()
    _, result = extract(
        llm,
        "I was diagnosed with ADHD. Remember this.",
        "work",
        [],
    )

    assert result.command == "remember"
    assert "ADHD" not in llm.received_message


def test_health_detail_is_visible_to_claude_inside_the_health_zone():
    llm = CapturingLLM()
    safe_message, result = extract(llm, "I was diagnosed with ADHD.", "health", [])

    assert "ADHD" in llm.received_message
    assert result.facts[0].category == "health"

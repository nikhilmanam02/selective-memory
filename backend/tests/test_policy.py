from app.models import CandidateFact
from app.policy import decide


def fact(**overrides):
    values = {
        "content": "User likes tea",
        "short": "tea",
        "category": "preference",
        "sensitivity": "low",
        "confidence": 0.9,
        "is_about_user": True,
        "is_temporary": False,
        "suggested_zone": "global",
    }
    values.update(overrides)
    return CandidateFact(**values)


def test_explicit_commands_have_priority():
    assert decide(fact(), "personal", {}, "dont_remember").action == "IGNORE"
    remembered = decide(fact(category="health", sensitivity="high"), "health", {}, "remember")
    assert (remembered.action, remembered.rule, remembered.zone) == (
        "AUTO_SAVE",
        "zone_only",
        "health",
    )
    assert decide(fact(), "personal", {}, "use_once").rule == "one_time"
    assert decide(fact(), "personal", {}, "zone_only:work").zone == "work"
    assert decide(fact(), "personal", {}, "forget").action == "IGNORE"


def test_ignores_non_user_facts_and_uses_secrets_once():
    assert decide(fact(is_about_user=False), "personal", {}).action == "IGNORE"
    secret = decide(fact(category="secret", sensitivity="high"), "personal", {})
    assert (secret.action, secret.rule) == ("USE_ONCE", "one_time")


def test_learned_preferences_apply_before_sensitive_ask():
    learned = {"health": {"behavior": "zone_only", "zone": "health"}}
    result = decide(
        fact(category="health", sensitivity="high", suggested_zone="health"),
        "health",
        learned,
    )
    assert result.action == "AUTO_SAVE"
    assert result.learned
    assert result.zone == "health"
    assert decide(
        fact(category="finance", sensitivity="high"),
        "finance",
        {"finance": {"behavior": "never"}},
    ).action == "IGNORE"


def test_sensitive_and_uncertain_facts_ask():
    health = decide(
        fact(category="health", sensitivity="high", suggested_zone="health"),
        "personal",
        {},
    )
    uncertain = decide(fact(confidence=0.4), "personal", {})
    assert health.action == "ASK"
    assert health.zone == "health"
    assert uncertain.action == "ASK"


def test_temporary_expiry_is_clamped_and_work_is_zone_only():
    temporary = decide(
        fact(is_temporary=True, expires_in_hours=900, suggested_zone="personal"),
        "personal",
        {},
    )
    work = decide(fact(category="work", suggested_zone="work"), "personal", {})
    assert temporary.expires_in_hours == 720
    assert (work.rule, work.zone) == ("zone_only", "work")


def test_simple_preferences_save_and_unknown_high_sensitivity_asks():
    assert decide(fact(), "personal", {}).rule == "forever"
    assert decide(fact(category="other", sensitivity="high"), "personal", {}).action == "ASK"

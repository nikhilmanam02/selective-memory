from app.learning import get_preferences, record_choice


def test_three_identical_answers_learn_zone_only(connection):
    for _ in range(3):
        learned = record_choice(connection, "health", "zone_only", "health")

    assert learned["behavior"] == "zone_only"
    assert get_preferences(connection)["health"]["zone"] == "health"


def test_three_declines_learn_never_even_across_zones(connection):
    for zone in ("health", "personal", "work"):
        learned = record_choice(connection, "finance", "decline", zone)

    assert learned["behavior"] == "never"


def test_two_undos_switch_category_to_ask(connection):
    record_choice(connection, "preference", "undo", "personal")
    learned = record_choice(connection, "preference", "undo", "personal")

    assert learned["behavior"] == "ask"


def test_secrets_are_never_learned(connection):
    for _ in range(5):
        assert record_choice(connection, "secret", "forever", "global") is None
    assert "secret" not in get_preferences(connection)

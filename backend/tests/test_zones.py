from app.memory_store import allowed_for, insert_memory, withheld_counts


def test_health_memory_never_leaks_to_work(connection):
    health = insert_memory(
        connection,
        content="User has a private appointment",
        short="appointment",
        category="health",
        zone="health",
        rule="zone_only",
        sensitivity="high",
    )
    work = insert_memory(
        connection,
        content="User is a designer",
        short="designer",
        category="work",
        zone="work",
        rule="zone_only",
        sensitivity="medium",
    )

    visible = allowed_for(connection, "work", "session-a")
    assert health["id"] not in {item["id"] for item in visible}
    assert work["id"] in {item["id"] for item in visible}
    assert withheld_counts(connection, "work", "session-a")["health"] == 1

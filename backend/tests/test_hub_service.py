from app import connections, hub_service
from app.models import MCPFact


def test_sensitive_mcp_import_waits_for_approval_and_secret_is_not_saved(connection):
    profile = connections.create_connection(connection, "Personal assistant", "personal")
    result = hub_service.import_facts(
        connection,
        profile,
        "AI provider",
        [
            MCPFact(
                content="User takes medication for anxiety",
                short="health detail",
                category="health",
                sensitivity="high",
                suggested_zone="health",
            ),
            MCPFact(
                content="User provided a password",
                short="Password",
                category="secret",
                sensitivity="high",
            ),
        ],
    )
    assert result["pending_approval"] == 1
    assert result["not_saved"] == 1
    assert connection.execute("SELECT COUNT(*) FROM memories WHERE category='secret'").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM memories WHERE status='pending'").fetchone()[0] == 1
    pending = connection.execute(
        "SELECT source FROM memories WHERE status='pending'"
    ).fetchone()
    assert pending["source"] == "Personal assistant"

import sqlite3

from fastapi.testclient import TestClient

from app import chat_service
from app.config import settings
from app.llm import MockLLM, get_llm
from app.main import app


def test_api_demo_chat_and_deletion_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "api.db"))
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(chat_service, "get_llm", lambda: MockLLM())
    with TestClient(app) as client:
        status = client.get("/api/health")
        assert status.status_code == 200
        assert status.json()["configured"] is False

        assert client.get("/api/memories").json()["memories"] == []

        response = client.post(
            "/api/chat",
            json={
                "session_id": "api-demo",
                "zone": "personal",
                "message": "I love spicy food",
            },
        )
        assert response.status_code == 200
        assert response.json()["auto_saved"][0]["rule"] == "forever"

        sensitive = client.post(
            "/api/chat",
            json={
                "session_id": "api-demo",
                "zone": "health",
                "message": "I just got diagnosed with ADHD",
            },
        )
        assert sensitive.status_code == 200
        ask = sensitive.json()["asks"][0]
        saved = client.post(
            f"/api/memories/{ask['id']}/answer",
            json={"choice": "zone_only", "zone": "health"},
        )
        assert saved.status_code == 200

        secret = "4111 1111 1111 1111"
        used = client.post(
            "/api/chat",
            json={
                "session_id": "api-demo",
                "zone": "personal",
                "message": f"Use this card number {secret}",
            },
        )
        assert used.status_code == 200
        verification = client.post("/api/verify-deletion", json={"text": secret})
        assert verification.json()["matches"] == 0

        cleared = client.post("/api/data/clear")
        assert cleared.json()["ok"] is True
        assert client.get("/api/memories").json()["memories"] == []


def test_chat_requires_real_anthropic_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "no-key.db"))
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(chat_service, "get_llm", get_llm)
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"session_id": "missing-key", "zone": "personal", "message": "Hi"},
        )
    assert response.status_code == 503
    assert "API key" in response.json()["detail"]


def test_configured_key_uses_anthropic_adapter_not_mock(monkeypatch):
    from app.llm import AnthropicLLM

    monkeypatch.setattr(settings, "anthropic_api_key", "test-key-not-used-for-network")
    assert isinstance(get_llm(), AnthropicLLM)


def test_mcp_connection_is_zone_scoped_and_token_is_one_time(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "mcp.db"))
    with TestClient(app) as client:
        client.post(
            "/api/memories",
            json={
                "content": "User works as a product designer at Northwind",
                "short": "work details",
                "category": "work",
                "sensitivity": "medium",
                "zone": "work",
            },
        )
        client.post(
            "/api/memories",
            json={
                "content": "User has an anxiety-related doctor appointment",
                "short": "appointment",
                "category": "health",
                "sensitivity": "high",
                "zone": "health",
            },
        )
        for pending in client.get("/api/memories?status=pending").json()["memories"]:
            client.post(
                f"/api/memories/{pending['id']}/answer",
                json={"choice": "zone_only", "zone": "health"},
            )
        created = client.post(
            "/api/connections",
            json={"name": "Work assistant", "zone": "work"},
        )
        assert created.status_code == 200
        connection = created.json()
        token = connection["token"]
        assert len(token) > 32
        assert "token" not in client.get("/api/connections").json()["connections"][0]
        with sqlite3.connect(tmp_path / "mcp.db") as stored:
            token_hash = stored.execute(
                "SELECT token_hash FROM connections WHERE id = ?",
                (connection["id"],),
            ).fetchone()[0]
        assert token_hash != token
        assert len(token_hash) == 64

        invalid = client.post("/api/mcp/recall", json={"query": "email"})
        assert invalid.status_code == 401

        profile = client.get(
            "/api/mcp/profile", headers={"Authorization": f"Bearer {token}"}
        )
        assert profile.json()["zone"] == "work"
        assert client.get("/api/connections").json()["connections"][0]["last_used_at"]

        recalled = client.post(
            "/api/mcp/recall",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "email to my manager"},
        )
        contents = [item["content"] for item in recalled.json()["memories"]]
        assert "User works as a product designer at Northwind" in contents
        assert all("anxiety" not in item.casefold() for item in contents)

        pending = client.post(
            "/api/mcp/remember",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "fact": {
                    "content": "User was diagnosed with ADHD",
                    "short": "health detail",
                    "category": "health",
                    "sensitivity": "high",
                    "suggested_zone": "health",
                }
            },
        )
        assert pending.json()["status"] == "needs_approval"
        pending_memory = client.get("/api/memories?status=pending").json()["memories"][0]
        assert pending_memory["source"] == "Work assistant"

        forgot = client.post(
            "/api/mcp/forget",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "product designer"},
        )
        assert forgot.json()["count"] == 1
        setup = client.get("/api/setup").json()
        assert setup["stdio_script"].endswith("stdio.js")

        assert client.delete(f"/api/connections/{connection['id']}").status_code == 200
        revoked = client.get(
            "/api/mcp/profile", headers={"Authorization": f"Bearer {token}"}
        )
        assert revoked.status_code == 401

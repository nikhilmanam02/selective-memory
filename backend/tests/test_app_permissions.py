from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def add(client, content, zone, category="preference"):
    return client.post(
        "/api/memories",
        json={"content": content, "short": content[:20], "category": category,
              "sensitivity": "low", "zone": zone},
    ).json()["memory"]


def test_each_memory_can_be_open_sensitive_or_for_chosen_ais(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "perm.db"))
    with TestClient(app) as client:
        veg = add(client, "User is vegetarian", "global")
        jp = add(client, "User loves Japanese food", "global")
        health = add(client, "User has an anxiety appointment Friday", "health", "health")
        assert (veg["visibility"], health["visibility"]) == ("open", "open")  # low sensitivity -> open

        chatgpt = client.post("/api/connections", json={"name": "ChatGPT"}).json()
        claude = client.post("/api/connections", json={"name": "Claude", "can_write": False}).json()
        auth = lambda c: {"Authorization": f"Bearer {c['token']}"}
        recall = lambda c: sorted(m["content"] for m in client.post(
            "/api/mcp/recall", headers=auth(c), json={"query": "restaurants"}).json()["memories"])

        assert recall(chatgpt) == sorted([veg["content"], jp["content"], health["content"]])
        seen = client.post("/api/mcp/recall", headers=auth(chatgpt), json={"query": "x"}).json()
        assert "only suggest options that fit every relevant preference" in seen["instructions"]

        # Sensitive: no AI sees it.
        client.patch(f"/api/memories/{health['id']}", json={"visibility": "sensitive"})
        assert health["content"] not in recall(chatgpt) and health["content"] not in recall(claude)

        # Chosen AIs: only ChatGPT gets "vegetarian".
        updated = client.patch(f"/api/memories/{veg['id']}", json={"visibility": "custom", "apps": [chatgpt["id"]]}).json()["memory"]
        assert updated["apps"] == [chatgpt["id"]]
        assert recall(chatgpt) == sorted([veg["content"], jp["content"]])
        assert recall(claude) == [jp["content"]]
        preview = client.get(f"/api/connections/{claude['id']}/preview").json()["memories"]
        assert [m["content"] for m in preview] == [jp["content"]]

        # Read-only app can't save.
        blocked = client.post(
            "/api/mcp/remember", headers=auth(claude),
            json={"fact": {"content": "User likes tabs", "short": "tabs", "category": "preference"}},
        ).json()
        assert blocked["status"] == "not_saved"

        log = client.get("/api/activity").json()["activity"]
        assert ("Claude", "blocked") in [(i["app"], i["action"]) for i in log]
        first_read = next(i for i in reversed(log) if i["app"] == "ChatGPT")
        assert sorted(first_read["memories"]) == sorted([veg["content"], jp["content"], health["content"]])

        # Deleting removes it everywhere, including its name from the activity log.
        client.delete(f"/api/memories/{veg['id']}")
        assert recall(chatgpt) == [jp["content"]]
        first_read = next(i for i in reversed(client.get("/api/activity").json()["activity"]) if i["app"] == "ChatGPT")
        assert first_read["deleted_count"] == 1


def test_import_from_an_app_lands_in_the_right_zone_and_is_manageable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "import.db"))
    with TestClient(app) as client:
        chatgpt = client.post("/api/connections", json={"name": "ChatGPT"}).json()
        claude = client.post("/api/connections", json={"name": "Claude"}).json()
        result = client.post(
            "/api/mcp/import",
            headers={"Authorization": f"Bearer {chatgpt['token']}"},
            json={"source": "ChatGPT", "facts": [
                {"content": "User is vegetarian", "short": "vegetarian", "category": "preference", "suggested_zone": "global"},
                {"content": "User loves Japanese food", "short": "Japanese food", "category": "preference", "suggested_zone": "global"},
                {"content": "User takes melatonin", "short": "melatonin", "category": "health", "sensitivity": "high", "suggested_zone": "health"},
                {"content": "User's card PIN is 1234", "short": "PIN", "category": "secret"},
            ]},
        ).json()
        assert (result["imported"], result["pending_approval"], result["not_saved"]) == (2, 1, 1)

        memories = client.get("/api/memories").json()["memories"]
        assert {m["source"] for m in memories} == {"ChatGPT"}
        pending = [m for m in memories if m["status"] == "pending"]
        assert pending[0]["zone"] == "health"  # filed in Health, waiting for the user's OK
        assert pending[0]["visibility"] == "sensitive"  # private by default
        assert not any("1234" in m["content"] for m in memories)

        # Another app immediately sees the imported preferences (not the pending health fact).
        seen = client.post("/api/mcp/recall", headers={"Authorization": f"Bearer {claude['token']}"}, json={"query": "restaurants"}).json()
        assert sorted(m["content"] for m in seen["memories"]) == ["User is vegetarian", "User loves Japanese food"]

        # The user manages it in one place: delete it here, and every app loses it.
        veg = next(m for m in memories if m["content"] == "User is vegetarian")
        client.delete(f"/api/memories/{veg['id']}")
        seen = client.post("/api/mcp/recall", headers={"Authorization": f"Bearer {claude['token']}"}, json={"query": "food"}).json()
        assert [m["content"] for m in seen["memories"]] == ["User loves Japanese food"]


def test_claude_desktop_install_merges_config(tmp_path, monkeypatch):
    import json

    from app import main

    monkeypatch.setattr(settings, "db_path", str(tmp_path / "cd.db"))
    config = tmp_path / "Claude" / "claude_desktop_config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "keep": True}))
    monkeypatch.setattr(main, "CLAUDE_DESKTOP_CONFIG", config)
    with TestClient(app) as client:
        assert client.get("/api/setup").json()["claude_desktop_installed"] is True
        result = client.post("/api/claude-desktop/install", json={"token": "t" * 40})
        assert result.status_code == 200
    saved = json.loads(config.read_text())
    assert saved["keep"] is True and "other" in saved["mcpServers"]
    entry = saved["mcpServers"]["selective-memory"]
    assert entry["args"][0].endswith("mcp-server/stdio.js")
    assert entry["env"]["SELECTIVE_MEMORY_TOKEN"] == "t" * 40
    assert config.with_suffix(".json.bak").exists()


def test_approving_a_sensitive_fact_can_open_it_to_ais(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "approve.db"))
    with TestClient(app) as client:
        gpt = client.post("/api/connections", json={"name": "ChatGPT"}).json()
        client.post("/api/mcp/remember", headers={"Authorization": f"Bearer {gpt['token']}"}, json={"fact": {
            "content": "User takes melatonin", "short": "melatonin", "category": "health", "sensitivity": "high", "suggested_zone": "health"}})
        pending = client.get("/api/memories?status=pending").json()["memories"][0]
        client.post(f"/api/memories/{pending['id']}/answer", json={"choice": "zone_only", "zone": "health", "visibility": "open"})
        seen = client.post("/api/mcp/recall", headers={"Authorization": f"Bearer {gpt['token']}"}, json={"query": "sleep"}).json()
        assert [m["content"] for m in seen["memories"]] == ["User takes melatonin"]


def test_optional_password_for_public_link_visitors(tmp_path, monkeypatch):
    import base64

    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pw.db"))
    with TestClient(app) as client:
        assert client.get("/api/memories").status_code == 200  # you, on localhost
        public = {"cf-connecting-ip": "203.0.113.9"}
        monkeypatch.setattr(settings, "app_password", "")
        assert client.get("/api/memories", headers=public).status_code == 200  # no password chosen
        monkeypatch.setattr(settings, "app_password", "demo-pass")
        assert client.get("/api/memories", headers=public).status_code == 401
        good = {**public, "Authorization": "Basic " + base64.b64encode(b"judge:demo-pass").decode()}
        bad = {**public, "Authorization": "Basic " + base64.b64encode(b"judge:wrong").decode()}
        assert client.get("/api/memories", headers=good).status_code == 200
        assert client.get("/api/memories", headers=bad).status_code == 401
        # MCP keeps using its own per-app keys
        assert client.post("/api/mcp/recall", headers=public, json={"query": "x"}).status_code == 401
        assert "WWW-Authenticate" not in client.post("/api/mcp/recall", headers=public, json={"query": "x"}).headers

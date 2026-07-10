from pathlib import Path

from fastapi.testclient import TestClient

from main import create_app


def test_health_route_works_when_static_is_mounted(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>Static Root</h1>", encoding="utf-8")
    app = create_app(str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pm-backend"}


def test_root_serves_static_index_when_dist_exists(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>Kanban Studio</h1>", encoding="utf-8")
    app = create_app(str(tmp_path))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Kanban Studio" in response.text


def test_root_is_not_available_when_static_dist_missing(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "missing"))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 404


def test_board_read_and_write_roundtrip(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    read_response = client.get("/api/board")
    assert read_response.status_code == 200
    body = read_response.json()
    assert body["username"] == "user"
    assert "columns" in body["board"]
    assert "cards" in body["board"]

    updated_board = {
        "columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": []}],
        "cards": {},
    }
    write_response = client.put("/api/board", json={"board": updated_board})
    assert write_response.status_code == 200
    assert write_response.json()["board"] == updated_board

    verify_response = client.get("/api/board")
    assert verify_response.status_code == 200
    assert verify_response.json()["board"] == updated_board


def test_board_routes_return_404_for_unknown_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    read_response = client.get("/api/board", params={"username": "missing"})
    assert read_response.status_code == 404

    write_response = client.put(
        "/api/board",
        params={"username": "missing"},
        json={"board": {"columns": [], "cards": {}}},
    )
    assert write_response.status_code == 404


def test_ai_test_route_ready_mode(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    response = client.get("/api/ai/test")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "live=true" in body["message"]


def test_ai_test_route_missing_key_returns_503(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    response = client.get("/api/ai/test", params={"live": "true"})

    assert response.status_code == 503


def test_ai_test_route_live_mode_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "demo-key")

    def fake_connectivity_test(_: str, model: str) -> dict[str, object]:
        return {
            "model": model,
            "prompt": "What is 2+2? Reply with only the final numeric answer.",
            "answer": "4",
            "containsFour": True,
        }

    monkeypatch.setattr("main.run_connectivity_test", fake_connectivity_test)
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    response = client.get("/api/ai/test", params={"live": "true"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["answer"] == "4"
    assert body["containsFour"] is True


def test_ai_board_route_no_operations_leaves_board_unchanged(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "demo-key")

    def fake_ai(*, api_key: str, user_prompt: str, board: dict[str, object], model: str) -> dict[str, object]:
        del api_key, user_prompt, model
        return {
            "model": "qwen/qwen3-coder:free",
            "requestedModel": "qwen/qwen3-coder:free",
            "fallbackUsed": False,
            "payload": {
                "assistantMessage": "No changes needed.",
                "operations": [],
            },
        }

    monkeypatch.setattr("main.run_board_action_prompt", fake_ai)
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    before = client.get("/api/board").json()["board"]
    response = client.post("/api/ai/board", json={"prompt": "Do nothing"})

    assert response.status_code == 200
    body = response.json()
    assert body["assistantMessage"] == "No changes needed."
    assert body["operationsApplied"] == []
    assert body["board"] == before


def test_ai_board_route_applies_valid_operations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "demo-key")

    def fake_ai(*, api_key: str, user_prompt: str, board: dict[str, object], model: str) -> dict[str, object]:
        del api_key, user_prompt, board, model
        return {
            "model": "qwen/qwen3-coder:free",
            "requestedModel": "qwen/qwen3-coder:free",
            "fallbackUsed": False,
            "payload": {
                "assistantMessage": "Updated backlog and added a card.",
                "operations": [
                    {
                        "type": "rename_column",
                        "columnId": "col-backlog",
                        "title": "Ideas",
                    },
                    {
                        "type": "create_card",
                        "columnId": "col-backlog",
                        "cardId": "card-101",
                        "title": "Plan onboarding checklist",
                        "details": "Draft checklist and owners.",
                    },
                ],
            },
        }

    monkeypatch.setattr("main.run_board_action_prompt", fake_ai)
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    response = client.post("/api/ai/board", json={"prompt": "Update board"})

    assert response.status_code == 200
    body = response.json()
    assert body["assistantMessage"] == "Updated backlog and added a card."
    columns = body["board"]["columns"]
    backlog = [c for c in columns if c["id"] == "col-backlog"][0]
    assert backlog["title"] == "Ideas"
    assert "card-101" in body["board"]["cards"]


def test_ai_board_route_rejects_invalid_operations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "demo-key")

    def fake_ai(*, api_key: str, user_prompt: str, board: dict[str, object], model: str) -> dict[str, object]:
        del api_key, user_prompt, board, model
        return {
            "model": "qwen/qwen3-coder:free",
            "requestedModel": "qwen/qwen3-coder:free",
            "fallbackUsed": False,
            "payload": {
                "assistantMessage": "I tried something unsupported.",
                "operations": [{"type": "unknown_operation"}],
            },
        }

    monkeypatch.setattr("main.run_board_action_prompt", fake_ai)
    app = create_app(str(tmp_path / "missing"), str(tmp_path / "pm.db"))
    client = TestClient(app)

    response = client.post("/api/ai/board", json={"prompt": "Break it"})

    assert response.status_code == 422
    assert "Invalid AI operations" in response.json()["detail"]

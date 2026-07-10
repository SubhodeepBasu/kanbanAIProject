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

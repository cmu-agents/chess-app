from fastapi.testclient import TestClient

from chess_app.game import ChessGame
from chess_app.server import create_app


def make_client() -> TestClient:
    return TestClient(create_app(ChessGame()))


def test_browser_entry_point_is_served():
    with make_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Sandbox Chess" in response.text
    assert 'id="game-result"' in response.text
    assert 'id="play-again"' in response.text


def test_state_and_move_api_share_one_game():
    with make_client() as client:
        initial = client.get("/api/state")
        moved = client.post("/api/move", json={"move": "e2e4"})
        current = client.get("/api/state")

    assert initial.status_code == 200
    assert moved.status_code == 200
    assert moved.json()["engine_move"] == "e7e5"
    assert moved.json()["human_state"]["squares"]["e4"] == "P"
    assert current.json()["fen"] == moved.json()["fen"]


def test_illegal_move_returns_a_useful_error():
    with make_client() as client:
        response = client.post("/api/move", json={"move": "e2e5"})

    assert response.status_code == 400
    assert "not legal" in response.json()["detail"]


def test_reset_endpoint_starts_a_new_game():
    with make_client() as client:
        client.post("/api/move", json={"move": "d2d4"})
        reset = client.post("/api/reset")

    assert reset.status_code == 200
    assert reset.json()["history"] == []

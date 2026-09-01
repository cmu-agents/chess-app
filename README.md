# chess-app

A small playable chess game: a `ChessGame` engine, a FastAPI wrapper around it, and a browser
frontend. You play White; a deterministic built-in opponent replies.

## Install

```
pip install -e ".[dev]"
```

## Run

```
chess-server                      # http://127.0.0.1:8000
chess-server --host 0.0.0.0 --port 8000
```

`--host` and `--port` also read the `CHESS_HOST` and `PORT` environment variables.

The browser polls the current game every 1.5 seconds, so it can be used to
monitor an external agent. The top-right button refreshes the board without
resetting the server-side game; a new game can be started after a terminal
result.

## Test

```
python -m pytest
```

## HTTP API

The browser UI and any programmatic client use the same endpoints:

- `GET /health` — readiness check, returns `{"status": "ok"}`.
- `GET /api/state` — board state, legal moves, history, and game result.
- `POST /api/move` — play a UCI move, for example `{"move": "e2e4"}`. Returns the new state with
  `human_move`, `human_state`, and the opponent's `engine_move`. An illegal or malformed move
  returns HTTP 400.
- `POST /api/reset` — start a new game.

## Layout

- `src/chess_app/game.py` — game rules, engine replies, and state serialization.
- `src/chess_app/server.py` — FastAPI app and the `chess-server` entry point.
- `src/chess_app/static/` — browser frontend.

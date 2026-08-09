"""HTTP API and browser entry point for the Assignment 1 chess game."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from assignment.chess_app.game import ChessGame, InvalidMoveError


STATIC_DIR = Path(__file__).with_name("static")


class MoveRequest(BaseModel):
    move: str = Field(description="A chess move in UCI notation, such as e2e4", min_length=4, max_length=5)


def create_app(game: ChessGame | None = None) -> FastAPI:
    chess_game = game or ChessGame()
    app = FastAPI(title="Assignment Chess", version="0.1.0")
    app.state.chess_game = chess_game
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/state")
    def get_state() -> dict:
        return chess_game.state()

    @app.post("/api/reset")
    def reset_game() -> dict:
        return chess_game.reset()

    @app.post("/api/move")
    def play_move(request: MoveRequest) -> dict:
        try:
            return chess_game.play_human_move(request.move)
        except InvalidMoveError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Assignment 1 chess game")
    parser.add_argument("--host", default=os.getenv("CHESS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

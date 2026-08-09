"""Stateful chess game and a small deterministic computer opponent."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CENTER_SQUARES = {chess.D4, chess.E4, chess.D5, chess.E5}
OPENING_PREFERENCES = ("e7e5", "d7d5", "c7c5", "g8f6")


class InvalidMoveError(ValueError):
    """Raised when a requested move cannot be played in the current position."""


@dataclass(frozen=True)
class PlayedMove:
    color: str
    san: str
    uci: str

    def as_dict(self, ply: int) -> dict[str, Any]:
        return {"ply": ply, "color": self.color, "san": self.san, "uci": self.uci}


class ChessGame:
    """One human-vs-computer chess game.

    The human always plays White in the starter version. The class owns all
    state so the browser UI and an agent tool can share exactly the same API.
    """

    def __init__(self, engine_depth: int = 2):
        self.engine_depth = engine_depth
        self._lock = Lock()
        self._board = chess.Board()
        self._history: list[PlayedMove] = []
        self._last_move: chess.Move | None = None

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._board.reset()
            self._history.clear()
            self._last_move = None
            return self._state_unlocked()

    def state(self) -> dict[str, Any]:
        with self._lock:
            return self._state_unlocked()

    def play_human_move(self, move_text: str) -> dict[str, Any]:
        """Play a White move and, unless the game ends, the computer reply."""

        with self._lock:
            if self._board.outcome(claim_draw=True) is not None:
                raise InvalidMoveError("The game is over. Start a new game to continue.")
            if self._board.turn != chess.WHITE:
                raise InvalidMoveError("It is not White's turn.")

            move = self._parse_move(move_text)
            self._record_and_push(move)
            human_state = self._state_unlocked()

            engine_move: str | None = None
            reply = self._choose_engine_move()
            engine_move = reply.uci()
            self._record_and_push(reply)

            state = self._state_unlocked()
            state["human_move"] = move.uci()
            state["human_state"] = human_state
            state["engine_move"] = engine_move
            return state

    def _parse_move(self, move_text: str) -> chess.Move:
        normalized = move_text.strip().lower()
        try:
            move = chess.Move.from_uci(normalized)
        except ValueError as exc:
            raise InvalidMoveError("Moves must use UCI notation, for example e2e4.") from exc

        # Clicking a pawn onto the final rank defaults to queen promotion.
        piece = self._board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(move.to_square) in {0, 7}:
            if move.promotion is None:
                move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)

        if move not in self._board.legal_moves:
            raise InvalidMoveError(f"{normalized} is not legal in the current position.")
        return move

    def _record_and_push(self, move: chess.Move) -> None:
        color = "white" if self._board.turn == chess.WHITE else "black"
        san = self._board.san(move)
        self._board.push(move)
        self._history.append(PlayedMove(color=color, san=san, uci=move.uci()))
        self._last_move = move

    def _choose_engine_move(self) -> chess.Move:
        legal_moves = sorted(self._board.legal_moves, key=lambda move: move.uci())
        if not legal_moves:
            raise RuntimeError("The engine was asked to move in a terminal position.")

        if self._board.fullmove_number == 1:
            by_uci = {move.uci(): move for move in legal_moves}
            for preferred in OPENING_PREFERENCES:
                if preferred in by_uci:
                    return by_uci[preferred]

        best_move = legal_moves[0]
        best_score = float("-inf")
        for move in legal_moves:
            self._board.push(move)
            score = self._minimax(self.engine_depth - 1)
            self._board.pop()
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    def _minimax(self, depth: int) -> float:
        outcome = self._board.outcome(claim_draw=True)
        if depth <= 0 or outcome is not None:
            return self._evaluate(outcome)

        scores: list[float] = []
        for move in sorted(self._board.legal_moves, key=lambda item: item.uci()):
            self._board.push(move)
            scores.append(self._minimax(depth - 1))
            self._board.pop()
        return max(scores) if self._board.turn == chess.BLACK else min(scores)

    def _evaluate(self, outcome: chess.Outcome | None) -> float:
        if outcome is not None:
            if outcome.winner == chess.BLACK:
                return 100_000
            if outcome.winner == chess.WHITE:
                return -100_000
            return 0

        score = 0.0
        for square, piece in self._board.piece_map().items():
            value = PIECE_VALUES[piece.piece_type]
            score += value if piece.color == chess.BLACK else -value
            if square in CENTER_SQUARES:
                score += 12 if piece.color == chess.BLACK else -12

        if self._board.is_check():
            score += 25 if self._board.turn == chess.WHITE else -25
        return score

    def _state_unlocked(self) -> dict[str, Any]:
        outcome = self._board.outcome(claim_draw=True)
        squares = {
            chess.square_name(square): piece.symbol()
            for square, piece in self._board.piece_map().items()
        }
        legal_moves = []
        if outcome is None and self._board.turn == chess.WHITE:
            legal_moves = sorted(move.uci() for move in self._board.legal_moves)

        return {
            "fen": self._board.fen(),
            "squares": squares,
            "turn": "white" if self._board.turn == chess.WHITE else "black",
            "legal_moves": legal_moves,
            "history": [move.as_dict(ply=index) for index, move in enumerate(self._history, start=1)],
            "last_move": self._last_move.uci() if self._last_move else None,
            "in_check": self._board.is_check(),
            "game_over": outcome is not None,
            "status": self._status(outcome),
        }

    def _status(self, outcome: chess.Outcome | None) -> str:
        if outcome is None:
            if self._board.is_check():
                return "Your king is in check" if self._board.turn == chess.WHITE else "Black is in check"
            return "Your turn" if self._board.turn == chess.WHITE else "Black is thinking"
        if outcome.winner == chess.WHITE:
            return "White wins"
        if outcome.winner == chess.BLACK:
            return "Black wins"
        return "Draw"

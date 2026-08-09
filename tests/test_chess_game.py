import chess
import pytest

from chess_app.game import ChessGame, InvalidMoveError


def test_initial_state_is_standard_white_position():
    game = ChessGame()

    state = game.state()

    assert state["turn"] == "white"
    assert state["status"] == "Your turn"
    assert state["squares"]["e1"] == "K"
    assert state["squares"]["e8"] == "k"
    assert len(state["legal_moves"]) == 20
    assert state["history"] == []


def test_human_move_is_followed_by_legal_engine_reply():
    game = ChessGame()

    state = game.play_human_move("e2e4")

    assert state["engine_move"] == "e7e5"
    assert state["human_move"] == "e2e4"
    assert state["human_state"]["squares"]["e4"] == "P"
    assert state["human_state"]["turn"] == "black"
    assert state["turn"] == "white"
    assert [move["uci"] for move in state["history"]] == ["e2e4", "e7e5"]
    assert chess.Board(state["fen"]).is_valid()


def test_illegal_move_does_not_change_game():
    game = ChessGame()

    with pytest.raises(InvalidMoveError, match="not legal"):
        game.play_human_move("e2e5")

    assert game.state()["history"] == []


def test_reset_restores_initial_position():
    game = ChessGame()
    game.play_human_move("d2d4")

    state = game.reset()

    assert state["fen"] == chess.STARTING_FEN
    assert state["history"] == []


def test_checkmate_is_immediately_reported_as_game_over():
    game = ChessGame()
    game._board = chess.Board("8/8/8/8/8/1k6/1q6/K7 w - - 0 1")

    state = game.state()

    assert state["in_check"] is True
    assert state["game_over"] is True
    assert state["legal_moves"] == []
    assert state["status"] == "Black wins"

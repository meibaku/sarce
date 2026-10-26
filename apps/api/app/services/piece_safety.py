"""Conservative LE2 piece-safety detector over already-computed, versioned engine rows."""

from __future__ import annotations

import hashlib

import chess

from app.config import settings
from app.services.ep import is_decided
from app.services.patterns import prepare_candidate

DETECTOR_VERSION = 1
CONCEPT = "piece_safety.hanging_piece"
MIN_MATERIAL_CP = 100
MIN_EP_LOSS = 0.10
PIECE_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}


def _captured(board: chess.Board, move: chess.Move) -> tuple[chess.Square, chess.Piece] | None:
    if not board.is_capture(move):
        return None
    square = move.to_square
    if board.is_en_passant(move):
        square += -8 if board.turn == chess.WHITE else 8
    piece = board.piece_at(square)
    return (square, piece) if piece else None


def _legal_recapture(board: chess.Board, capture: chess.Move) -> chess.Move | None:
    """Cheapest legal recapture of the capturing piece, enough for a conservative material screen."""
    after = board.copy()
    after.push(capture)
    replies = [move for move in after.legal_moves if after.is_capture(move) and move.to_square == capture.to_square]
    return min(replies, key=lambda move: PIECE_CP[(after.piece_at(move.from_square) or chess.Piece(chess.QUEEN, after.turn)).piece_type], default=None)


def capture_fact(board: chess.Board, move: chess.Move) -> dict | None:
    captured = _captured(board, move)
    attacker = board.piece_at(move.from_square)
    if not captured or not attacker or move.promotion:
        return None
    square, victim = captured
    recapture = _legal_recapture(board, move)
    gain = PIECE_CP[victim.piece_type] if recapture is None else PIECE_CP[victim.piece_type] - PIECE_CP[attacker.piece_type]
    return {
        "moveUci": move.uci(),
        "victimSquare": chess.square_name(square),
        "victim": chess.piece_name(victim.piece_type),
        "attacker": chess.piece_name(attacker.piece_type),
        "materialGainCp": gain,
        "recaptureUci": recapture.uci() if recapture else None,
    }


def classify_position(board: chess.Board, lines: list[dict], player_ep_before: float) -> dict:
    """Classify the position after the player's move; never starts or depends on a live engine."""
    if board.is_game_over() or is_decided(player_ep_before, settings.ep_decided_low, settings.ep_decided_high):
        return {"eligible": False, "reason": "terminal_or_decided"}
    if not lines or not lines[0].get("move_uci") or lines[0].get("ep") is None:
        return {"eligible": False, "reason": "missing_engine_contract"}

    captures = []
    for move in board.legal_moves:
        fact = capture_fact(board, move)
        if fact:
            captures.append(fact)
    best = lines[0]
    best_fact = next((fact for fact in captures if fact["moveUci"] == best["move_uci"]), None)
    player_ep_after = 1.0 - float(best["ep"])
    ep_loss = max(0.0, player_ep_before - player_ep_after)
    positive = bool(best_fact and best_fact["materialGainCp"] >= MIN_MATERIAL_CP and ep_loss >= MIN_EP_LOSS)

    if positive:
        label, relation, squares = "positive", "material_winning_capture", [best_fact["victimSquare"]]
    elif captures:
        apparent = max(captures, key=lambda fact: fact["materialGainCp"])
        if apparent["recaptureUci"]:
            relation = "recapture"
        elif ep_loss < MIN_EP_LOSS:
            relation = "adequate_compensation"
        else:
            relation = "capture_not_engine_sound"
        label, squares = "near_miss", []
    else:
        label, relation, squares = "control", "no_immediate_capture", []

    return {
        "eligible": True,
        "label": label,
        "relation": relation,
        "target": {"squares": squares, "noImmediateDanger": not positive},
        "verification": {
            "bestMoveUci": best["move_uci"],
            "bestEpForOpponent": round(float(best["ep"]), 6),
            "playerEpBefore": round(player_ep_before, 6),
            "playerEpAfter": round(player_ep_after, 6),
            "epLoss": round(ep_loss, 6),
            "captures": captures,
            "relation": relation,
        },
    }


def candidate_after_move(
    *,
    board_before: chess.Board,
    played: chess.Move,
    player_ep_before: float,
    evaluation: dict,
    owner_id: str,
    game_id: str,
    ply: int,
    difficulty_context: dict | None = None,
) -> dict | None:
    """Build a private reviewer candidate from one completed-game move and its cached post-move search."""
    if played not in board_before.legal_moves:
        raise ValueError("played move is illegal in board_before")
    if evaluation.get("nodes") != settings.analysis_nodes or not evaluation.get("engine_version"):
        raise ValueError("evaluation does not match the fixed search contract")
    board = board_before.copy()
    board.push(played)
    result = classify_position(board, evaluation.get("lines") or [], player_ep_before)
    if not result.get("eligible"):
        return None
    exact_family = hashlib.sha256(board.board_fen().encode()).hexdigest()[:24]
    return prepare_candidate(
        fen=board.fen(),
        family_key=f"exact:{exact_family}",
        visibility="private",
        owner_id=owner_id,
        source_type="own_game",
        source_game_id=game_id,
        source_ply=ply,
        label=result["label"],
        target=result["target"],
        verification=result["verification"],
        difficulty_context=difficulty_context,
        stockfish_version=evaluation["engine_version"],
        analysis_nodes=evaluation["nodes"],
        detector_version=DETECTOR_VERSION,
        concept_key=CONCEPT,
    )

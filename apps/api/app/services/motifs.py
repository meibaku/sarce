"""
Tactical motif detectors — Chaos Lens M7 (docs/CHAOS_PLAN.md).

Rule-based, engine-free tags for a single move: fork, pin, skewer, discovered attack,
sacrifice, hanging piece. Written from scratch for this repo; Lichess's AGPL
`lichess-puzzler` was a reference for *which* motifs matter only, not for code.
These are heuristics for describing ideas, not verdicts on move quality.
"""

from __future__ import annotations

import chess

from app.services.brilliant import PIECE_VALUES, material_sacrifice, piece_value

KING_VALUE = 100  # only for ordering: the king outranks every piece
ROOK_VALUE = PIECE_VALUES[chess.ROOK]


def _value(piece: chess.Piece | None) -> int:
    if piece is not None and piece.piece_type == chess.KING:
        return KING_VALUE
    return piece_value(piece)


def _is_loose(board: chess.Board, square: chess.Square, attacker_value: int) -> bool:
    """A piece worth going after: undefended, or worth more than the piece attacking it."""
    piece = board.piece_at(square)
    if piece is None:
        return False
    return not board.attackers(piece.color, square) or _value(piece) > attacker_value


def hanging_pieces(board: chess.Board, color: chess.Color) -> list[chess.Square]:
    """Non-king pieces of `color` that are attacked and not defended."""
    squares = []
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        if board.attackers(not color, square) and not board.attackers(color, square):
            squares.append(square)
    return sorted(squares)


def is_fork(after: chess.Board, move: chess.Move) -> bool:
    """The moved piece attacks two or more enemy pieces that are loose or more valuable."""
    mover = after.piece_at(move.to_square)
    if mover is None:
        return False
    targets = [
        square
        for square in after.attacks(move.to_square)
        if (piece := after.piece_at(square)) is not None
        and piece.color != mover.color
        and (piece.piece_type == chess.KING or _is_loose(after, square, _value(mover)))
    ]
    return len(targets) >= 2


def _ray_pieces(board: chess.Board, origin: chess.Square, through: chess.Square) -> list[chess.Square]:
    """Occupied squares on the line from `origin` through `through`, nearest first."""
    file_step = (chess.square_file(through) > chess.square_file(origin)) - (
        chess.square_file(through) < chess.square_file(origin)
    )
    rank_step = (chess.square_rank(through) > chess.square_rank(origin)) - (
        chess.square_rank(through) < chess.square_rank(origin)
    )
    found = []
    file, rank = chess.square_file(origin) + file_step, chess.square_rank(origin) + rank_step
    while 0 <= file <= 7 and 0 <= rank <= 7:
        square = chess.square(file, rank)
        if board.piece_at(square) is not None:
            found.append(square)
        file, rank = file + file_step, rank + rank_step
    return found


def _line_targets(after: chess.Board, square: chess.Square) -> list[tuple[chess.Piece, chess.Piece]]:
    """For a slider on `square`: (front, behind) enemy pairs lined up on one of its rays."""
    slider = after.piece_at(square)
    if slider is None or slider.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return []
    pairs = []
    for target in after.attacks(square):
        front = after.piece_at(target)
        if front is None or front.color == slider.color:
            continue
        line = _ray_pieces(after, square, target)
        if len(line) >= 2 and line[0] == target:
            behind = after.piece_at(line[1])
            if behind is not None and behind.color != slider.color:
                pairs.append((front, behind))
    return pairs


def is_pin(after: chess.Board, move: chess.Move) -> bool:
    """The moved slider lines up a lesser enemy piece in front of a rook, queen or king."""
    return any(
        _value(behind) > _value(front) and _value(behind) >= ROOK_VALUE
        for front, behind in _line_targets(after, move.to_square)
    )


def is_skewer(after: chess.Board, move: chess.Move) -> bool:
    """The moved slider attacks a valuable enemy piece with a lesser one behind it."""
    return any(
        _value(front) > _value(behind) and _value(front) >= ROOK_VALUE
        for front, behind in _line_targets(after, move.to_square)
    )


def is_discovered_attack(before: chess.Board, move: chess.Move) -> bool:
    """Moving the piece uncovers a friendly slider's attack on a loose or more valuable enemy piece."""
    color = before.turn
    after = before.copy()
    after.push(move)
    for square, piece in after.piece_map().items():
        if piece.color != color or square == move.to_square:
            continue
        if piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        for target in after.attacks(square) & ~before.attacks(square):
            victim = after.piece_at(target)
            if victim is None or victim.color == color:
                continue
            # Only attacks opened by the vacated square count as discovered.
            if move.from_square not in chess.SquareSet(chess.between(square, target)):
                continue
            if victim.piece_type == chess.KING or _is_loose(after, target, _value(piece)):
                return True
    return False


def move_motifs(before: chess.Board, move: chess.Move) -> list[str]:
    """All motif tags for playing `move` in `before` (the board is not modified)."""
    after = before.copy()
    after.push(move)
    tags = []
    if material_sacrifice(before, move) > 0:
        tags.append("sacrifice")
    if is_fork(after, move):
        tags.append("fork")
    if is_pin(after, move):
        tags.append("pin")
    if is_skewer(after, move):
        tags.append("skewer")
    if is_discovered_attack(before, move):
        tags.append("discovered_attack")
    # The mover left something en prise that was not hanging before the move.
    if set(hanging_pieces(after, before.turn)) - set(hanging_pieces(before, before.turn)) - {move.from_square}:
        tags.append("hanging_piece")
    return tags

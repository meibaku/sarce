"""Sacrifice library helpers (app/services/library.py)."""

import chess

from app.services import library


def board_with(fen):
    return chess.Board(fen)


def test_offered_exchange_piece_queen_pawn():
    b = board_with("6k1/8/8/4n3/8/8/8/4R1K1 w - - 0 1")
    assert library.offered(b, chess.Move.from_uci("e1e5")) == ("Exchange", 2)
    b = board_with("6k1/7p/8/8/8/3B4/8/6K1 w - - 0 1")
    assert library.offered(b, chess.Move.from_uci("d3h7")) == ("Piece", 2)
    b = board_with("6k1/8/8/8/8/8/8/3Q2K1 w - - 0 1")
    assert library.offered(b, chess.Move.from_uci("d1h5")) == ("Queen", 9)
    b = board_with("6k1/8/8/8/8/8/6P1/6K1 w - - 0 1")
    assert library.offered(b, chess.Move.from_uci("g2g4")) == ("Pawn storm", 1)


def test_boards_before_follows_the_mainline():
    plies = library.boards_before("1. e4 e5 2. Nf3 *")
    assert len(plies) == 3
    board, move = plies[2]
    assert move.uci() == "g1f3" and board.piece_at(chess.G1) is not None


def test_glyphs_never_red_words():
    assert library.sacrifice_glyph({"is_brilliant": True}, None) == "!!"
    assert library.sacrifice_glyph({"quality": "good"}, "calculated_risk") == "!?"
    assert library.sacrifice_glyph({"quality": "best"}, None) == "✓"
    assert library.sacrifice_glyph({"quality": "mistake"}, None) == "?"


def test_real_offer_ignores_defended_pieces_only_taken_by_equals():
    # Qe2 defended by the king, attacked only by the enemy queen: not on offer.
    b = board_with("4k3/8/8/8/8/8/4q3/3QK3 w - - 0 1")
    assert library.real_offer(b, chess.Move.from_uci("d1d2")) == 0
    # Rook takes a knight, recapturable by a pawn: the exchange is on offer.
    b = board_with("6k1/5p2/4n3/8/8/8/8/4R1K1 w - - 0 1")
    assert library.real_offer(b, chess.Move.from_uci("e1e6")) == 2
    # Bishop left hanging and undefended.
    b = board_with("6k1/8/7p/8/8/8/8/2B3K1 w - - 0 1")
    assert library.real_offer(b, chess.Move.from_uci("c1g5")) == 3


def test_offers_are_parsed_once_per_finished_game(monkeypatch):
    from app.services import library

    pgn = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7 *"
    calls = []
    real = library.boards_before
    monkeypatch.setattr(library, "boards_before", lambda text: calls.append(1) or real(text))
    monkeypatch.setattr(library, "_OFFERS", {})
    first = library.offers_in("g1", pgn, [10, 0])
    assert first[10] == ("Piece", 2) and first[0] is None  # Nxf7 offers the knight for a pawn; 1.e4 offers nothing
    library.offers_in("g1", pgn, [10])
    assert len(calls) == 1

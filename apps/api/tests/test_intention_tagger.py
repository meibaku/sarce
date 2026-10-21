"""Intention tagger — motifs and idea windows, Chaos Lens M7. Engine-free."""

from pathlib import Path
from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from app.main import app
from app.services.ideas import (
    PlyState,
    build_ply_states,
    find_gambits,
    find_ideas,
    find_king_attacks,
    find_squeezes,
    king_zone,
)
from app.services.motifs import hanging_pieces, move_motifs
from app.services.tagger import tag_game_data

client = TestClient(app)
MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261010003000_intention_tags.sql"


def motifs(fen: str, uci: str) -> list[str]:
    board, move = chess.Board(fen), chess.Move.from_uci(uci)
    assert board.is_valid() and move in board.legal_moves
    return move_motifs(board, move)


class TestMotifs:
    def test_knight_fork_of_king_and_rook(self):
        assert motifs("r3k3/8/8/1N6/8/8/8/4K3 w - - 0 1", "b5c7") == ["fork"]

    def test_bishop_pins_knight_to_king(self):
        assert motifs("4k3/8/2n5/8/8/8/8/4KB2 w - - 0 1", "f1b5") == ["pin"]

    def test_rook_skewers_king_and_queen(self):
        assert motifs("4q3/8/8/4k3/8/8/8/R5K1 w - - 0 1", "a1e1") == ["skewer"]

    def test_knight_move_uncovers_rook_attack_on_queen(self):
        assert "discovered_attack" in motifs("4k3/4q3/8/8/4N3/8/8/4R1K1 w - - 0 1", "e4c5")

    def test_piece_left_en_prise_is_a_sacrifice_and_hanging(self):
        assert motifs("4k3/8/3p4/8/8/5N2/8/4K3 w - - 0 1", "f3e5") == ["sacrifice", "hanging_piece"]

    def test_quiet_developing_move_has_no_motif(self):
        assert motifs(chess.STARTING_FEN, "g1f3") == []

    def test_hanging_pieces_ignores_defended_and_kings(self):
        board = chess.Board("4k3/8/3p4/4N3/8/8/8/4K3 w - - 0 1")
        assert hanging_pieces(board, chess.WHITE) == [chess.E5]
        assert hanging_pieces(board, chess.BLACK) == []

    def test_board_is_not_modified(self):
        board = chess.Board()
        move_motifs(board, chess.Move.from_uci("e2e4"))
        assert board.fen() == chess.STARTING_FEN


def state(ply, material=0, mobility=30, entered=False, ep=0.5):
    by_user = ply % 2 == 0
    return PlyState(ply, by_user, material, mobility if by_user else None, entered, ep if by_user else None)


class TestIdeaWindows:
    def test_gambit_needs_a_sustained_deficit(self):
        long = [state(i, material=-1 if 4 <= i <= 11 else 0) for i in range(18)]
        short = [state(i, material=-1 if 4 <= i <= 7 else 0) for i in range(18)]
        assert find_gambits(long) == [(4, 11)]
        assert find_gambits(short) == []

    def test_being_lost_is_not_a_gambit(self):
        losing = [state(i, material=-1 if i >= 4 else 0, ep=0.2) for i in range(18)]
        assert find_gambits(losing) == []

    def test_king_attack_needs_three_pieces_within_the_window(self):
        quick = [state(i, entered=i in (10, 12, 16)) for i in range(24)]
        slow = [state(i, entered=i in (2, 12, 22)) for i in range(24)]
        assert find_king_attacks(quick) == [(10, 16)]
        assert find_king_attacks(slow) == []

    def test_squeeze_needs_less_mobility_and_more_ep(self):
        squeeze = [state(i, mobility=30 if i < 8 else 18, ep=0.5 if i < 8 else 0.65) for i in range(20)]
        flat = [state(i, mobility=30 if i < 8 else 18) for i in range(20)]
        assert find_squeezes(squeeze) == [(0, 8)]
        assert find_squeezes(flat) == []


class TestVerdictsAndPivots:
    def test_gambit_that_gains_ep_worked(self):
        states = [state(i, material=-1 if 4 <= i <= 11 else 0, ep=0.5 if i < 12 else 0.7) for i in range(18)]
        assert find_ideas(states) == [
            {"family": "gambit", "start_ply": 4, "end_ply": 11, "verdict": "worked", "is_pivot": False}
        ]

    def test_gambit_that_loses_ep_is_refuted(self):
        states = [state(i, material=-1 if 4 <= i <= 11 else 0, ep=0.5 if i < 10 else 0.42 if i < 12 else 0.3) for i in range(18)]
        assert [i["verdict"] for i in find_ideas(states)] == ["refuted"]

    def test_flat_ep_fizzles(self):
        states = [state(i, material=-1 if 4 <= i <= 11 else 0) for i in range(18)]
        assert [i["verdict"] for i in find_ideas(states)] == ["fizzled"]

    def test_new_family_after_a_refutation_is_a_pivot(self):
        def ep(i):
            return 0.5 if i < 10 else 0.42 if i < 12 else 0.3

        states = [
            state(i, material=-1 if 4 <= i <= 11 else 0, entered=i in (14, 16, 18), ep=ep(i))
            for i in range(26)
        ]
        ideas = find_ideas(states)
        assert [(i["family"], i["verdict"], i["is_pivot"]) for i in ideas] == [
            ("gambit", "refuted", False),
            ("king_attack", "fizzled", True),
        ]


class TestReplay:
    KINGS_GAMBIT = "e2e4 e7e5 f2f4 e5f4 g1f3 g7g5 f1c4 g5g4 e1g1 g4f3 d1f3"

    def test_material_and_mobility_from_a_real_game(self):
        moves = [chess.Move.from_uci(u) for u in self.KINGS_GAMBIT.split()]
        states = build_ply_states(chess.Board(), moves, "white", {i: 0.2 for i in range(0, 11, 2)})
        assert [s.material_diff for s in states][-3:] == [-1, -4, -3]
        assert states[0].by_user and states[0].opponent_mobility == 20
        assert states[1].opponent_mobility is None and states[1].user_ep is None

    def test_king_zone_covers_the_ring_and_the_squares_in_front(self):
        zone = king_zone(chess.Board(), chess.BLACK)
        assert {chess.square_name(s) for s in zone} == {
            "d8", "e8", "f8", "d7", "e7", "f7", "d6", "e6", "f6",
        }


class TestTagGame:
    PGN = "1. e4 e5 2. f4 exf4 3. Nf3 g5 4. Bc4 g4 5. O-O gxf3 6. Qxf3 *"

    def test_tags_both_players_and_finds_ideas(self):
        rows = [{"ply": ply, "eval_after": 0.2} for ply in range(0, 11, 2)]
        result = tag_game_data(self.PGN, "white", rows)
        assert {"ply": 2, "by_user": True, "tag": "sacrifice"} in result["tags"]
        assert all(set(tag) == {"ply", "by_user", "tag"} for tag in result["tags"])
        assert [i["family"] for i in result["ideas"]] == ["gambit"]

    def test_unparseable_pgn(self):
        assert tag_game_data("", "white", []) == {"tags": [], "ideas": []}


class TestRouteAndMigration:
    @patch("app.routers.games.tagger_service.get_game_ideas", return_value={"gameId": "abc", "tags": [], "ideas": []})
    def test_game_ideas(self, _mock):
        res = client.get("/games/abc/ideas")
        assert res.status_code == 200
        assert res.json() == {"gameId": "abc", "tags": [], "ideas": []}

    @patch("app.routers.games.tagger_service.tag_game", return_value=None)
    def test_refresh_unknown_game_is_404(self, _mock):
        assert client.get("/games/abc/ideas?refresh=true").status_code == 404

    def test_both_tables_enable_rls(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        for table in ("move_tags", "game_ideas"):
            assert f"alter table public.{table} enable row level security" in sql
        assert sql.count("create policy") == 2

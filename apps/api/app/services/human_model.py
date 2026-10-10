"""
Human move model — P(move | position, Elo) for the Chaos Lens (docs/CHAOS_PLAN.md, M2).

Models sit behind `HumanModel` so the implementation can be swapped (see
docs/adr/0002-human-model.md). Output is raw data cached in `human_probs`; lenses only
read it (rule 3).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Protocol

import chess

from app.db.supabase import get_supabase
from app.services.position_evals import fen_key

TABLE = "human_probs"
ELO_LADDER = [800, 1200, 1600, 2000, 2400]

PIECE_VALUE = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.0,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}


def elo_ladder(opponent_rating: int | None = None) -> list[int]:
    """The fixed ladder plus the opponent's actual rating rounded to the nearest 100."""
    elos = set(ELO_LADDER)
    if opponent_rating:
        elos.add(int(round(opponent_rating / 100.0)) * 100)
    return sorted(elos)


class HumanModel(ABC):
    """A rating-conditioned move predictor."""

    name: str
    version: str

    @property
    def model_version(self) -> str:
        """Cache identity — bump `version` whenever outputs change."""
        return f"{self.name}-{self.version}"

    @abstractmethod
    def move_probs(self, board: chess.Board, elo: int) -> dict[str, float]:
        """Probability for **every** legal move (UCI → p), summing to 1. Empty if none."""


class HeuristicHumanModel(HumanModel):
    """
    Engine-free findability heuristic: captures, checks, promotions and forward moves
    are more likely to be played, more sharply so at higher ratings.

    This is the interim model and the M4 comparison baseline — **not** a trained human
    model. It exists so the pipeline and lenses can be built and tested before the
    Maia decision in docs/adr/0002-human-model.md.
    """

    name = "heuristic"
    version = "1"

    def _score(self, board: chess.Board, move: chess.Move) -> float:
        score = 0.0
        if board.is_capture(move):
            captured = board.piece_type_at(move.to_square) or chess.PAWN  # en passant
            score += 1.0 + 0.2 * PIECE_VALUE[captured]
        if board.gives_check(move):
            score += 1.0
        if move.promotion:
            score += 2.0
        if board.is_castling(move):
            score += 0.5
        rank_delta = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
        forward = rank_delta if board.turn == chess.WHITE else -rank_delta
        score += 0.15 * max(-2, min(2, forward))
        return score

    def move_probs(self, board: chess.Board, elo: int) -> dict[str, float]:
        moves = list(board.legal_moves)
        if not moves:
            return {}
        # Stronger players concentrate more of their choices on the "natural" moves.
        sharpness = 0.6 + 0.6 * (min(max(elo, 800), 2400) - 800) / 1600
        weights = [math.exp(sharpness * self._score(board, m)) for m in moves]
        total = sum(weights)
        return {m.uci(): w / total for m, w in zip(moves, weights)}


class ProbStore(Protocol):
    def get(self, key: str, elo: int, model_version: str) -> dict | None: ...

    def put(self, row: dict) -> None: ...


class SupabaseProbStore:
    """`human_probs` rows keyed by (fen_key, elo, model_version)."""

    def get(self, key: str, elo: int, model_version: str) -> dict | None:
        res = (
            get_supabase()
            .table(TABLE)
            .select("*")
            .eq("fen_key", key)
            .eq("elo", elo)
            .eq("model_version", model_version)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def put(self, row: dict) -> None:
        get_supabase().table(TABLE).upsert(
            row, on_conflict="fen_key,elo,model_version"
        ).execute()


def cached_move_probs(
    board: chess.Board, elo: int, model: HumanModel, store: ProbStore
) -> dict[str, float]:
    """Move probabilities for `board` at `elo`, calling the model only on a cache miss."""
    key = fen_key(board)
    cached = store.get(key, elo, model.model_version)
    if cached is not None:
        return cached["probs"]
    probs = model.move_probs(board, elo)
    if probs:
        store.put(
            {"fen_key": key, "elo": elo, "model_version": model.model_version, "probs": probs}
        )
    return probs


def get_human_model(name: str) -> HumanModel:
    """Resolve the configured model (`HUMAN_MODEL`): `heuristic` (default) or `maia2` (optional)."""
    if name == HeuristicHumanModel.name:
        return HeuristicHumanModel()
    if name == "maia2":
        # Imported here so the optional adapter is only touched when selected.
        from app.services.maia_model import Maia2HumanModel

        return Maia2HumanModel()
    raise ValueError(f"Unknown human model {name!r}; available: ['heuristic', 'maia2']")

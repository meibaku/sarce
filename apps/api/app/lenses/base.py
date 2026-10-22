"""Lens protocol and the stored-data context every lens scores from."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PositionData:
    """Stored raw data for one position, from the side to move's perspective."""

    # position_evals.lines — best first: [{move_uci, cp, mate, wdl, ep}]
    lines: list[dict]
    # position_evals.safe_set_complete — False means `lines` may miss safe replies.
    safe_set_complete: bool
    # human_probs by Elo: {elo: {uci: probability}}
    probs_by_elo: dict[int, dict[str, float]] = field(default_factory=dict)
    # Clock of the player to move, as a bucket, and the P_fail multiplier that goes with it.
    clock_bucket: str | None = None
    p_fail_multiplier: float = 1.0
    # The position's cache key (FEN without the move number), so a lens can rebuild the board.
    key: str | None = None
    # position_threats row for a position the user faced: the opponent's move and score if the user passed.
    threat: dict | None = None


@dataclass(frozen=True)
class PlyContext:
    """Everything known about one **user** move, built only from stored data."""

    ply: int
    uci: str
    quality: str | None = None
    # Mover's EP before the move and EP given up versus the engine's best move.
    ep_before: float | None = None
    objective_cost: float | None = None
    # Position the user faced (after the opponent's previous move); None at ply 0 or if not stored.
    faced: PositionData | None = None
    # Position the user left for the opponent; None if not stored.
    left: PositionData | None = None
    opponent_elo: int | None = None
    # The opponent's actual reply (None when the game ended on this move), for lenses that ask "did it work?".
    reply_uci: str | None = None
    # The user's clock before the move and the time spent on it (increment included), when the PGN has clocks.
    clock_ms: int | None = None
    spent_ms: int | None = None
    # Starting clock of the game, so time thresholds scale from 1+0 to rapid.
    initial_ms: int | None = None


@dataclass(frozen=True)
class LensResult:
    score: float | None
    verdict: str | None
    details: dict = field(default_factory=dict)


class Lens(Protocol):
    """A lens scores one move from stored data, or returns None when it has nothing to say."""

    name: str
    version: str

    def score(self, ctx: PlyContext) -> LensResult | None: ...

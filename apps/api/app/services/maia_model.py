"""
Maia-2 human move model — optional (docs/adr/0002-human-model.md).

Select with `HUMAN_MODEL=maia2` after `pip install -r requirements-maia.txt`. The
package (and PyTorch behind it) is imported only when the model is first used, so the
API runs without it and Phase 1 never touches it. This model predicts opponents'
replies; move classification stays rule-based.
"""

from __future__ import annotations

import chess

from app.config import settings
from app.services.human_model import HumanModel

INSTALL_HINT = (
    "HUMAN_MODEL=maia2 needs the optional Maia-2 package: "
    "pip install -r requirements-maia.txt (about 1.6 GB with PyTorch)."
)


class Maia2HumanModel(HumanModel):
    """Rating-conditioned move probabilities from the published Maia-2 weights (CPU)."""

    name = "maia2"

    def __init__(self) -> None:
        self._model = None
        self._prepared = None
        self._inference = None

    @property
    def version(self) -> str:
        # The checkpoint type changes the output, so it is part of the cache identity.
        return f"0.11-{settings.maia2_model_type}"

    def _load(self) -> None:
        try:
            from maia2 import inference, model
        except ImportError as exc:
            raise RuntimeError(INSTALL_HINT) from exc
        # Downloads the checksum-pinned weights on first use (about 280 MB), then caches them.
        self._model = model.from_pretrained(
            type=settings.maia2_model_type, device="cpu", save_root=settings.maia2_cache_dir
        )
        self._prepared = inference.prepare()
        self._inference = inference

    def move_probs(self, board: chess.Board, elo: int) -> dict[str, float]:
        legal = {move.uci() for move in board.legal_moves}
        if not legal:
            return {}
        if self._model is None:
            self._load()
        # Both players are given the same rating: the lens asks "how would a player of this
        # strength reply", and the opponent's own rating is not known for ladder rows.
        raw, _win = self._inference.inference_each(self._model, self._prepared, board.fen(), elo, elo)
        probs = {uci: float(p) for uci, p in raw.items() if uci in legal}
        for uci in legal - probs.keys():
            probs[uci] = 0.0
        total = sum(probs.values())
        if total <= 0:
            return {uci: 1.0 / len(legal) for uci in legal}
        return {uci: p / total for uci, p in probs.items()}


_shared: dict[str, Maia2HumanModel] = {}


def shared_maia2_model() -> Maia2HumanModel:
    """
    One instance per checkpoint type for the whole process.

    Loading the weights takes seconds and a few hundred MB, so a batch of games must not
    reload them for every game. Inference is read-only, so sharing the instance is safe.
    """
    model_type = settings.maia2_model_type
    if model_type not in _shared:
        _shared[model_type] = Maia2HumanModel()
    return _shared[model_type]

"""Lens registry — add a lens here and it is scored from data that is already stored."""

from __future__ import annotations

from app.lenses.base import Lens, LensResult, PlyContext
from app.lenses.chaos import ChaosLens
from app.lenses.clock import ClockLens
from app.lenses.prophylaxis import ProphylaxisLens
from app.lenses.soundness import SoundnessLens
from app.lenses.squeeze import SqueezeLens
from app.lenses.swindle import SwindleLens
from app.lenses.survival import SurvivalLens

_LENSES: dict[str, Lens] = {}


def register(lens: Lens) -> None:
    _LENSES[lens.name] = lens


def unregister(name: str) -> None:
    _LENSES.pop(name, None)


def all_lenses() -> list[Lens]:
    return list(_LENSES.values())


def score_ply(ctx: PlyContext) -> dict[str, tuple[Lens, LensResult]]:
    """Run every registered lens on one move; lenses with nothing to say are omitted."""
    results = {}
    for lens in all_lenses():
        result = lens.score(ctx)
        if result is not None:
            results[lens.name] = (lens, result)
    return results


for _lens in (SoundnessLens(), ChaosLens(), SurvivalLens(), SqueezeLens(), SwindleLens(), ClockLens(), ProphylaxisLens()):
    register(_lens)

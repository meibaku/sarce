"""Soundness lens — the Phase 1 result re-expressed as a lens (no new judgement)."""

from __future__ import annotations

from app.lenses.base import LensResult, PlyContext


class SoundnessLens:
    name = "soundness"
    version = "1"

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.quality is None:
            return None
        score = None if ctx.objective_cost is None else round(1.0 - ctx.objective_cost, 4)
        return LensResult(score, ctx.quality, {"objective_cost": ctx.objective_cost})

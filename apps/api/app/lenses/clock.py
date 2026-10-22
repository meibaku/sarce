"""
Clock lens — time as part of style, built for 1+0: did you play the easy moves fast and keep your time for the
moments that needed it?

A position is critical when one move is clearly best (CLOCK_CRITICAL_CP over the second). Verdicts:
- found: critical, and the move was sound;
- rushed: critical, played fast, and not sound — the one place a second's thought pays;
- missed: critical, thought about, and not sound (not a time slip);
- quick: easy position, played fast;
- lingered: easy position, a lot of time spent (time that a later critical move may lack);
- steady: anything else.
Thresholds scale with the starting clock (config.CLOCK_*_FRACTION).
"""

from __future__ import annotations

from app.lenses import config
from app.lenses.base import LensResult, PlyContext
from app.lenses.squeeze import line_cp


class ClockLens:
    name = "clock"
    version = "1"

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.spent_ms is None or not ctx.initial_ms or ctx.faced is None or ctx.left is None:
            return None
        lines = [s for s in (line_cp(ln) for ln in ctx.faced.lines) if s is not None]
        reply = line_cp(ctx.left.lines[0]) if ctx.left.lines else None
        if not lines or reply is None:
            return None
        critical = len(lines) > 1 and lines[0] - lines[1] >= config.CLOCK_CRITICAL_CP
        sound = lines[0] - (-reply) <= config.CLOCK_SOUND_CP
        quick = ctx.spent_ms <= ctx.initial_ms * config.CLOCK_QUICK_FRACTION
        if critical:
            verdict = "found" if sound else ("rushed" if ctx.spent_ms < ctx.initial_ms * config.CLOCK_THINK_FRACTION else "missed")
        elif quick:
            verdict = "quick"
        elif ctx.spent_ms >= ctx.initial_ms * config.CLOCK_SLOW_FRACTION:
            verdict = "lingered"
        else:
            verdict = "steady"
        well = verdict in ("found", "quick", "steady", "missed")
        return LensResult(
            1.0 if well else 0.0,
            verdict,
            {"spent_ms": ctx.spent_ms, "clock_ms": ctx.clock_ms, "critical": critical, "sound": sound},
        )

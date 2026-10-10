"""
Lens thresholds — one place, tuned from data in M4 (docs/CHAOS_PLAN.md).

All values are expected points (EP) unless noted. They are provisional until validated.
"""

# Replies within this much EP of the best reply are "safe".
SAFE_TOL = 0.05

# Chaos (P_fail x Stake) at or above this flags a move.
CHAOS_THRESHOLD = 0.10

# Chaos is zero when the mover's EP before the move is outside this band (game decided).
DECIDED_LOW = 0.10
DECIDED_HIGH = 0.90

# Objective cost bounds for the verdict: at most REAL -> real chaos, above CHEAP -> cheap chaos.
REAL_CHAOS_MAX_COST = 0.05
CHEAP_CHAOS_MIN_COST = 0.10

# Elo used for the headline score when the opponent's rating is unknown.
DEFAULT_ELO = 1600

# Clock multipliers for P_fail, per human model, from the M4 validation
# (docs/VALIDATION.md, 10 Oct 2026: 4,820 positions from four months of Lichess 1+0 games,
# fit on the tuning set). Keyed by the clock of the player who has to reply. A model with
# no entry is left unadjusted. Provisional: the "<5s" bucket rests on 384 positions.
CLOCK_MULTIPLIERS = {
    "maia2": {"<5s": 1.2849, "5-15s": 1.0285, "15s+": 0.9113},
}

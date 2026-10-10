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

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

# Clock multipliers for P_fail, per human model, from the full M4 validation
# (docs/VALIDATION.md, 11 Oct 2026: 50,516 positions from twelve months of Lichess 1+0 games,
# fit on the 34,429-position tuning set). Keyed by the clock of the player who has to reply.
# A model with no entry is left unadjusted. Fit on one-minute games only.
CLOCK_MULTIPLIERS = {
    "maia2": {"<5s": 1.2294, "5-15s": 0.9797, "15s+": 0.9317},
}

# Squeeze (converting an advantage). Centipawns, from the user's side.
# Only moves made at or above this edge count: clearly winning, about two pawns.
SQUEEZE_MIN_CP = 200
# Opponent replies within this of their best still "hold" (they have room).
SQUEEZE_REPLY_CP = 50
# Giving back more than this is "gave_air": the opponent got counterplay back.
SQUEEZE_AIR_CP = 100
# At most this many holding replies left, with the edge kept, is a squeeze.
SQUEEZE_TIGHT_REPLIES = 2
# Holding replies beyond the tight count over which the "kept" score falls from 1 to 0.
SQUEEZE_ROOM_SPAN = 5

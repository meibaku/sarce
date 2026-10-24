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

# The four style lenses below judge edges and costs in EP like chaos (review F8, CHAOS_PLAN rule 4): a pawn given
# back at +5 costs almost nothing, at +1 a lot, and centipawns treated both the same. Values match the old
# centipawn thresholds in a level position (cp_to_ep(100) - 0.5 ≈ 0.09). The one exception is squeeze's room count.

# Squeeze (converting an advantage). Only moves made with at least this EP count: clearly winning (≈ +2 pawns).
SQUEEZE_MIN_EP = 0.675
# Giving back at most this EP keeps the squeeze (the same tolerance as a safe reply).
SQUEEZE_KEEP_EP = SAFE_TOL
# Giving back more than this EP is "gave_air": the opponent got counterplay back.
SQUEEZE_AIR_EP = 0.10
# Opponent replies within this many centipawns of their best still "hold" (they have room). Centipawns on purpose:
# the opponent is losing here, where EP compresses (0.07 vs 0.02) and would hide which replies still hold.
SQUEEZE_REPLY_CP = 50
# At most this many holding replies left, with the edge kept, is a squeeze.
SQUEEZE_TIGHT_REPLIES = 2
# Holding replies beyond the tight count over which the "kept" score falls from 1 to 0.
SQUEEZE_ROOM_SPAN = 5

# Swindle (fighting back). Only moves made with at most this EP count: clearly losing (≈ -2 pawns).
SWINDLE_MAX_EP = 0.325

# Clock (time use). A position is critical when the best move is this much EP better than the second: finding the
# one move is worth thinking for (≈ a pawn when level; a won position stays won, so it isn't critical).
CLOCK_CRITICAL_EP = 0.08
# A move costing at most this EP versus the best counts as sound.
CLOCK_SOUND_EP = SAFE_TOL
# Time thresholds as fractions of the starting clock (1+0: quick ≤ 2 s, slow ≥ 5 s, a real think ≥ 3 s).
CLOCK_QUICK_FRACTION = 1 / 30
CLOCK_SLOW_FRACTION = 1 / 12
CLOCK_THINK_FRACTION = 1 / 20

# Prophylaxis (stopping the opponent's idea). A threat counts when the opponent's best move after a pass beats
# their normal standing by this much EP (≈ 1.5 pawns when level).
PROPH_THREAT_EP = 0.13
# The user's move kept the position (stopped or met the threat) when it cost at most this EP.
PROPH_SOUND_EP = SAFE_TOL
# The threat came through when the move cost at least this EP and the threat was their best reply or what they played.
PROPH_LET_EP = 0.13

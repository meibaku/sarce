from app.services.distraction import flagged_plies, move_times, parse_time_control
from app.services.home import pick_moments


def _game(spent_s: list[float], base: int = 600, extra: dict | None = None) -> tuple[dict, list[dict]]:
    """White's moves spend `spent_s` seconds each; Black always spends 1 s."""
    clocks, white, black = [], base * 1000, base * 1000
    for s in spent_s:
        white -= int(s * 1000)
        black -= 1000
        clocks += [white, black]
    moves = [{"ply": 2 * i, "san": "e4", "quality": "good"} for i in range(len(spent_s))]
    for ply, quality in (extra or {}).items():
        moves[ply // 2]["quality"] = quality
    return {"time_control": str(base), "clocks_ms": clocks}, moves


def test_parse_time_control():
    assert parse_time_control("180+2") == (180_000, 2_000)
    assert parse_time_control("60") == (60_000, 0)
    assert parse_time_control("1/86400") is None
    assert parse_time_control(None) is None


def test_move_times_uses_own_previous_clock_and_increment():
    times = move_times([59_000, 58_000, 55_000, 57_000], [0, 2], 60_000, 1_000)
    assert times == {0: (2_000, 60_000), 2: (5_000, 59_000)}


def test_rushed_costly_move_is_flagged_first():
    spent = [2] * 8 + [10] * 10 + [1, 10, 10, 60, 10]
    game, moves = _game(spent, extra={36: "blunder"})
    flags = flagged_plies(game, moves, [])
    assert flags[0] == 36
    assert 42 in flags  # the long pause in a quiet position


def test_long_pause_in_a_chaotic_position_is_not_drift():
    game, moves = _game([2] * 8 + [10] * 10 + [60])
    assert flagged_plies(game, moves, [{"ply": 36, "lens": "chaos", "verdict": "real_chaos"}]) == []


def test_time_trouble_and_daily_games_are_never_flagged():
    game, moves = _game([1] * 8 + [4] * 11 + [0.6], base=60, extra={38: "blunder"})  # 8 s left
    assert flagged_plies(game, moves, []) == []
    game, moves = _game([2] * 20, extra={36: "blunder"})
    game["time_control"] = "1/86400"
    assert flagged_plies(game, moves, []) == []


def test_flagged_ply_takes_a_moment_slot_as_checkin():
    moves = [{"ply": p, "san": "x", "is_brilliant": p == 4} for p in range(0, 12, 2)]
    lens = {p: {"chaos": {"verdict": "real_chaos", "score": 0.5}} for p in (0, 2, 6)}
    picked = pick_moments(moves, lens, limit=3, checkin=[10])
    assert [m["ply"] for m in picked][-1] == 10 and picked[-1]["glyph"] == "?!"
    assert len(picked) == 3 and any(m["glyph"] == "!!" for m in picked)

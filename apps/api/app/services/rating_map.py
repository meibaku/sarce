"""
Site rating → human-model Elo (review F1).

Maia-2 is conditioned on Lichess ratings, but most games come from Chess.com, whose pools sit far lower (a
Chess.com 10-minute 660 plays like a Lichess rapid ~1,170). Feeding raw Chess.com ratings to the model put every
opponent on the bottom rung. Every place a rating meets the human model (lens ladder, find-rate rung, chaos map,
review lines) converts it here first.

Source: ChessGoals rating comparison survey (chessgoals.com/rating-comparison, updated July 2026; players with
RD < 150; Chess.com bullet N=9,345, rapid N=10,156; Lichess blitz N=1,935, bullet N=1,455, rapid N=1,066).
Both tables are keyed on Chess.com blitz: a Chess.com rating is first taken to its blitz equivalent, then to the
Lichess pool of the same speed. Below and above the survey (500–3,000 blitz) the end slopes are extended, and the
result is clamped to Lichess's range. Bump VERSION when the table or the method changes.
"""

from __future__ import annotations

VERSION = 1

# Chess.com blitz → (Chess.com bullet, Chess.com rapid).
CHESSCOM = [
    (500, 550, 815), (600, 615, 905), (700, 685, 995), (800, 760, 1085), (900, 840, 1170), (1000, 920, 1255),
    (1100, 1010, 1340), (1200, 1100, 1420), (1300, 1195, 1500), (1400, 1290, 1580), (1500, 1385, 1655),
    (1600, 1485, 1730), (1700, 1590, 1800), (1800, 1690, 1870), (1900, 1795, 1935), (2000, 1900, 1995),
    (2100, 2005, 2055), (2200, 2110, 2110), (2300, 2215, 2165), (2400, 2320, 2215), (2500, 2425, 2260),
    (2600, 2530, 2300), (2700, 2630, 2340), (2800, 2725, 2375), (2900, 2825, 2405), (3000, 2915, 2430),
]
# Chess.com blitz → Lichess (blitz, bullet, rapid, classical).
LICHESS = [
    (500, 1090, 1060, 1290, 1505), (600, 1160, 1120, 1360, 1540), (700, 1225, 1180, 1425, 1575),
    (800, 1290, 1240, 1490, 1610), (900, 1360, 1305, 1555, 1650), (1000, 1425, 1375, 1615, 1690),
    (1100, 1490, 1445, 1680, 1730), (1200, 1555, 1515, 1740, 1770), (1300, 1620, 1585, 1795, 1815),
    (1400, 1685, 1660, 1850, 1860), (1500, 1755, 1735, 1905, 1900), (1600, 1820, 1815, 1960, 1945),
    (1700, 1885, 1890, 2015, 1990), (1800, 1950, 1970, 2065, 2035), (1900, 2015, 2050, 2115, 2080),
    (2000, 2080, 2135, 2165, 2120), (2100, 2145, 2215, 2215, 2165), (2200, 2210, 2300, 2260, 2205),
    (2300, 2275, 2380, 2310, 2245), (2400, 2340, 2465, 2355, 2280), (2500, 2410, 2550, 2400, 2320),
    (2600, 2475, 2635, 2445, 2350), (2700, 2540, 2715, 2490, 2385), (2800, 2610, 2800, 2530, 2415),
    (2900, 2675, 2885, 2575, 2440), (3000, 2745, 2970, 2615, 2465),
]
CHESSCOM_COLUMN = {"blitz": 0, "bullet": 1, "rapid": 2}
LICHESS_COLUMN = {"blitz": 1, "bullet": 2, "rapid": 3, "classical": 4}
LICHESS_MIN, LICHESS_MAX = 400, 3000


def interpolate(xs: list[float], ys: list[float], x: float) -> float:
    """Piecewise-linear y(x) over increasing xs, extending the end segments outside the table."""
    i = 1
    while i < len(xs) - 1 and x > xs[i]:
        i += 1
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def speed(source: str | None, time_control: str | None) -> str:
    """The site's speed class for a PGN time control ("600", "180+2", "1/86400"); rapid when unknown."""
    tc = (time_control or "").strip()
    if not tc or tc == "-":
        return "rapid"
    if "/" in tc:  # Chess.com daily: no survey column; its pool is closest to rapid
        return "rapid"
    base, _, inc = tc.partition("+")
    try:
        estimate = float(base) + 40 * float(inc or 0)
    except ValueError:
        return "rapid"
    if source == "lichess":
        return "bullet" if estimate < 180 else "blitz" if estimate < 480 else "rapid" if estimate < 1500 else "classical"
    return "bullet" if estimate < 180 else "blitz" if estimate < 600 else "rapid"


def to_model_elo(source: str | None, time_control: str | None, rating: int | float | None) -> int | None:
    """The Lichess-scale Elo the human model expects for a rating on `source` at that time control; None if unknown."""
    if not rating:
        return None
    if source not in (None, "chess_com"):  # Lichess and Sarce bots are already on the model's scale
        return int(round(rating))
    kind = speed(source, time_control)
    blitz_scale = [row[0] for row in CHESSCOM]
    as_blitz = interpolate([row[CHESSCOM_COLUMN[kind]] for row in CHESSCOM], blitz_scale, float(rating))
    column = LICHESS_COLUMN.get(kind, LICHESS_COLUMN["rapid"])
    lichess = interpolate([row[0] for row in LICHESS], [row[column] for row in LICHESS], as_blitz)
    return int(round(min(LICHESS_MAX, max(LICHESS_MIN, lichess))))


def opponent_model_elo(game: dict) -> int | None:
    """The opponent's rating on the human model's scale, from a `games` row (needs source and time_control)."""
    return to_model_elo(game.get("source"), game.get("time_control"), game.get("opponent_rating"))


def user_model_elo(game: dict) -> int | None:
    """Your own rating in that game on the human model's scale (`games.user_rating`, read from the PGN)."""
    return to_model_elo(game.get("source"), game.get("time_control"), game.get("user_rating"))

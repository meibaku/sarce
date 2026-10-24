"""
Rating-band trap atlas — Chaos Lens M6 (docs/CHAOS_PLAN.md): "ideas that work at your level."

A trap is a position where the reply most often played at a rating band loses a lot of
expected points. Built from observations collected by scripts/validate_chaos.py on
finished public games; it never stores who played them.

Traps are ranked by expected loss times a cautious share: the Wilson lower bound of how often the common reply is
played (review F7), so a position seen three times can't top the list on luck alone.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.db.supabase import get_supabase
from app.services.uncertainty import wilson

TABLE = "trap_atlas"
MIN_EP_LOSS = 0.20  # the common reply must lose at least this much
MIN_FREQUENCY = 3  # times the position was seen at the band


def build_traps(
    observations: list[dict],
    min_ep_loss: float = MIN_EP_LOSS,
    min_frequency: int = MIN_FREQUENCY,
) -> list[dict]:
    """
    Aggregate reply observations into trap rows. Pure.

    Each observation needs: fen_key, fen, band, speed, reply_uci, reply_ep_loss,
    best_reply_uci, p_fail, stake, eco.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for obs in observations:
        groups[(obs["fen_key"], obs["band"], obs["speed"])].append(obs)

    traps = []
    for (key, band, speed), members in groups.items():
        if len(members) < min_frequency:
            continue
        common_uci, common_count = Counter(m["reply_uci"] for m in members).most_common(1)[0]
        losses = [m["reply_ep_loss"] for m in members if m["reply_uci"] == common_uci]
        ep_loss = sum(losses) / len(losses)
        if ep_loss < min_ep_loss:
            continue
        first = members[0]
        traps.append(
            {
                "fen_key": key,
                "fen": first["fen"],
                "band": band,
                "speed": speed,
                "frequency": len(members),
                "common_reply_uci": common_uci,
                "common_reply_share": round(common_count / len(members), 4),
                "ep_loss": round(ep_loss, 4),
                "best_reply_uci": first.get("best_reply_uci"),
                "p_fail": _mean(m.get("p_fail") for m in members),
                "stake": _mean(m.get("stake") for m in members),
                "eco": first.get("eco"),
            }
        )
    return sorted(traps, key=lambda t: (-rank_score(t), t["fen_key"]))


def rank_score(trap: dict) -> float:
    """Expected loss times the Wilson lower bound of the common reply's share (seen `frequency` times)."""
    n = int(trap["frequency"])
    interval = wilson(round(float(trap["common_reply_share"]) * n), n)
    return float(trap["ep_loss"]) * (interval[0] if interval else 0.0)


def _mean(values) -> float | None:
    known = [float(v) for v in values if v not in (None, "")]
    return round(sum(known) / len(known), 4) if known else None


def to_api(row: dict) -> dict:
    return {
        "fen": row["fen"],
        "band": row["band"],
        "speed": row["speed"],
        "frequency": row["frequency"],
        "seen": row["frequency"],  # "seen n times", next to the share (review F7)
        "commonReplyUci": row["common_reply_uci"],
        "commonReplyShare": float(row["common_reply_share"]),
        "epLoss": float(row["ep_loss"]),
        "bestReplyUci": row.get("best_reply_uci"),
        "pFail": None if row.get("p_fail") is None else float(row["p_fail"]),
        "stake": None if row.get("stake") is None else float(row["stake"]),
        "eco": row.get("eco"),
    }


class TrapAtlasService:
    def save(self, traps: list[dict]) -> int:
        """Upsert trap rows; returns how many were written."""
        for start in range(0, len(traps), 200):
            get_supabase().table(TABLE).upsert(
                traps[start : start + 200], on_conflict="fen_key,band,speed"
            ).execute()
        return len(traps)

    def list_traps(self, band: int | None = None, eco: str | None = None, limit: int = 50) -> list[dict]:
        query = get_supabase().table(TABLE).select("*")
        if band is not None:
            query = query.eq("band", band)
        if eco:
            query = query.ilike("eco", f"{eco}%")
        # Over-fetch by loss, then rank by the shrunk score so rare positions don't win on luck (review F7).
        res = query.order("ep_loss", desc=True).limit(limit * 4).execute()
        rows = sorted(res.data or [], key=lambda r: (-rank_score(r), r["fen_key"]))[:limit]
        return [to_api(row) for row in rows]

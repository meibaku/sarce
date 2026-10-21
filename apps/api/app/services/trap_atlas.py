"""
Rating-band trap atlas — Chaos Lens M6 (docs/CHAOS_PLAN.md): "ideas that work at your level."

A trap is a position where the reply most often played at a rating band loses a lot of
expected points. Built from observations collected by scripts/validate_chaos.py on
finished public games; it never stores who played them.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.db.supabase import get_supabase

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
    return sorted(traps, key=lambda t: (-t["ep_loss"] * t["common_reply_share"], t["fen_key"]))


def _mean(values) -> float | None:
    known = [float(v) for v in values if v not in (None, "")]
    return round(sum(known) / len(known), 4) if known else None


def to_api(row: dict) -> dict:
    return {
        "fen": row["fen"],
        "band": row["band"],
        "speed": row["speed"],
        "frequency": row["frequency"],
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
        res = query.order("ep_loss", desc=True).limit(limit).execute()
        return [to_api(row) for row in res.data or []]

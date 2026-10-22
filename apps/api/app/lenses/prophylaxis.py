"""
Prophylaxis lens — stopping the opponent's idea before it happens (Nimzowitsch, Petrosian, Karpov).

Reads the stored threat for the position the user faced (`position_threats`: the opponent's best move if the user
passed). When that threat was real (worth PROPH_THREAT_CP or more to the opponent), the user's move is:
- stopped: a quiet move (no capture, no check) that kept the position — the idea was taken away calmly;
- met: kept the position with a capture or check — answered by force rather than prevented;
- let_through: the move cost PROPH_LET_CP or more and the threat was the opponent's best reply (or what they played).
"""

from __future__ import annotations

import chess

from app.lenses import config
from app.lenses.base import LensResult, PlyContext
from app.lenses.squeeze import line_cp


class ProphylaxisLens:
    name = "prophylaxis"
    version = "1"

    def score(self, ctx: PlyContext) -> LensResult | None:
        faced, left = ctx.faced, ctx.left
        if faced is None or left is None or not faced.threat or not faced.key or not faced.lines or not left.lines:
            return None
        edge = line_cp(faced.lines[0])
        reply = line_cp(left.lines[0])
        if edge is None or reply is None:
            return None
        threat_gain = float(faced.threat["threat_cp"]) + edge  # the opponent's gain over their normal standing
        if threat_gain < config.PROPH_THREAT_CP:
            return None
        try:
            board = chess.Board(f"{faced.key} 1")
            move = chess.Move.from_uci(ctx.uci)
            passed = board.copy(stack=False)
            passed.push(chess.Move.null())
            threat_san = passed.san(chess.Move.from_uci(faced.threat["threat_uci"]))
        except ValueError:
            return None
        cost = max(0.0, edge - (-reply))
        quiet = not board.is_capture(move) and not board.gives_check(move)
        details = {"threat": threat_san, "threat_uci": faced.threat["threat_uci"], "threat_gain_cp": round(threat_gain), "cost_cp": round(cost), "quiet": quiet}
        if cost <= config.PROPH_SOUND_CP:
            return LensResult(1.0 if quiet else 0.5, "stopped" if quiet else "met", details)
        came = left.lines[0].get("move_uci") == faced.threat["threat_uci"] or ctx.reply_uci == faced.threat["threat_uci"]
        if cost >= config.PROPH_LET_CP and came:
            return LensResult(0.0, "let_through", details)
        return None

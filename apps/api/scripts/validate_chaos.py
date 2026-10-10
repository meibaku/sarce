"""
Chaos validation on real bullet games — Chaos Lens M4 (docs/CHAOS_PLAN.md).

Usage:
    cd apps/api
    python -m scripts.validate_chaos lichess_db.pgn --positions 2000
    zstdcat lichess_db_standard_rated_2026-08.pgn.zst | python -m scripts.validate_chaos - --positions 50000

Reads a Lichess open-database PGN (CC0; decompress it yourself — no extra dependency),
keeps 1+0 games with clocks, samples positions stratified by rating band and the
replier's clock, and checks whether predicted P_fail matches how often the actual
reply left the safe set. Thresholds and the clock multiplier are fit on a tuning set
and scored on held-out games. Outputs land in scripts/out/ (gitignored).

Needs a local Stockfish (STOCKFISH_PATH). Finished games only (rule 6).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.lenses import PositionData
from app.lenses import config as lens_config
from app.lenses.chaos import position_chaos, split_safe
from app.services import chaos_validation as cv
from app.services.human_model import HeuristicHumanModel, get_human_model
from app.services.position_evals import fen_key, safe_set_complete
from app.services.stockfish import StockfishEngine

OUT_DIR = Path(__file__).resolve().parent / "out"


class Cached:
    """Memoise engine searches and model calls by position, so repeated openings cost nothing."""

    def __init__(self, engine=None, model=None):
        self.engine, self.model, self.memo = engine, model, {}
        self.model_version = getattr(model, "model_version", None)

    def analyse(self, board, nodes, multipv):
        key = (fen_key(board), nodes, multipv)
        if key not in self.memo:
            self.memo[key] = self.engine.analyse(board, nodes=nodes, multipv=multipv)
        return self.memo[key]

    def move_probs(self, board, elo):
        key = (fen_key(board), elo)
        if key not in self.memo:
            self.memo[key] = self.model.move_probs(board, elo)
        return self.memo[key]


def reply_ep_loss(engine, board, reply, lines, nodes) -> float | None:
    """Expected points the reply actually played gave up versus the best reply."""
    best = lines[0]["ep"]
    for line in lines:
        if line["move_uci"] == reply.uci():
            return max(0.0, best - line["ep"])
    # Not among the stored lines: evaluate the position it leads to.
    after = board.copy()
    after.push(reply)
    if after.is_game_over():
        return max(0.0, best - (1.0 if after.is_checkmate() else 0.5))
    reply_lines = engine.analyse(after, nodes=nodes, multipv=1)
    if not reply_lines or reply_lines[0]["ep"] is None:
        return None
    return max(0.0, best - (1.0 - reply_lines[0]["ep"]))


def sample_game(game, engine, model, heuristic, nodes, quota, per_cell, min_ply=8, max_ply=None) -> list[dict]:
    """Samples from one game; `quota` counts samples per (band, clock) cell."""
    headers = game.headers
    game_id = headers.get("Site", "") or headers.get("GameId", "")
    try:
        ratings = {chess.WHITE: int(headers["WhiteElo"]), chess.BLACK: int(headers["BlackElo"])}
    except (KeyError, ValueError):
        return []
    clocks = [
        None if node.clock() is None else round(node.clock() * 1000)
        for node in game.mainline()
    ]
    moves = list(game.mainline_moves())
    if len(moves) < 12 or not any(c is not None for c in clocks):
        return []

    samples, board = [], game.board()
    for ply, move in enumerate(moves[:-1]):
        board.push(move)
        replier = board.turn
        clock = cv.clock_bucket(cv.decider_clock_ms(clocks, ply, 60_000))
        band = cv.rating_band(ratings[replier])
        if max_ply is not None and ply > max_ply:
            break
        if ply < min_ply or clock is None or quota[(band, clock)] >= per_cell:
            continue
        # Widen like the app does (position_evals.evaluate_position): a safe reply outside
        # the first few lines must not be counted as a predicted failure.
        legal = board.legal_moves.count()
        width = min(settings.analysis_multipv, legal)
        cap = min(max(settings.analysis_multipv, settings.analysis_multipv_cap), legal)
        lines = engine.analyse(board, nodes=nodes, multipv=width)
        while width < cap and not safe_set_complete(lines, lens_config.SAFE_TOL):
            width = min(width * 2, cap)
            lines = engine.analyse(board, nodes=nodes, multipv=width)
        if len(lines) < 2 or lines[0]["ep"] is None:
            continue
        if not lens_config.DECIDED_LOW <= 1.0 - lines[0]["ep"] <= lens_config.DECIDED_HIGH:
            continue  # the mover's game was already decided
        loss = reply_ep_loss(engine, board, moves[ply + 1], lines, nodes)
        if loss is None:
            continue
        failed = int(loss > lens_config.SAFE_TOL)

        elo = int(round(ratings[replier] / 100.0)) * 100
        safe, _ = split_safe(lines, lens_config.SAFE_TOL)
        safe_moves = {line["move_uci"] for line in safe}

        def p_fail(human_model) -> float:
            probs = human_model.move_probs(board, elo)
            return max(0.0, 1.0 - sum(probs.get(uci, 0.0) for uci in safe_moves))

        data = position_chaos(
            PositionData(lines=lines, safe_set_complete=True, probs_by_elo={elo: model.move_probs(board, elo)})
        )
        quota[(band, clock)] += 1
        samples.append(
            {
                "game_id": game_id,
                "ply": ply,
                "band": band,
                "clock": clock,
                "failed": failed,
                "p_fail": p_fail(model),
                "chaos": data["chaos"][elo] if data else None,
                "baseline_cliff": cv.raw_cliff(lines),
                "baseline_heuristic": p_fail(heuristic),
                # Trap atlas inputs (scripts/build_trap_atlas.py); no player identity is kept.
                "fen_key": fen_key(board),
                "fen": board.fen(),
                "speed": "bullet",
                "reply_uci": moves[ply + 1].uci(),
                "reply_ep_loss": round(loss, 4),
                "best_reply_uci": lines[0]["move_uci"],
                "stake": data["stake"][elo] if data else None,
                "eco": headers.get("ECO"),
            }
        )
    return samples


def write_outputs(
    samples: list[dict], summary: dict, model_version: str, runtime: float, out_dir: Path = OUT_DIR
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if samples:
        with open(out_dir / "chaos_samples.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
            writer.writeheader()
            writer.writerows(samples)
    with open(out_dir / "chaos_calibration.csv", "w", newline="", encoding="utf-8") as handle:
        fields = ["band", "clock", "bin_low", "n", "predicted", "observed"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary["calibration"])
    report = {**summary, "model_version": model_version, "runtime_seconds": round(runtime, 1)}
    (out_dir / "chaos_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate chaos scores on Lichess bullet games")
    parser.add_argument("pgn", help="Path to a decompressed Lichess PGN, or - for stdin")
    parser.add_argument("--positions", type=int, default=2000, help="Target sample size")
    parser.add_argument("--per-cell", type=int, default=200, help="Max samples per rating band x clock bucket")
    parser.add_argument("--nodes", type=int, default=settings.analysis_nodes)
    parser.add_argument("--min-ply", type=int, default=8, help="Skip earlier plies (lower it for the trap atlas)")
    parser.add_argument("--max-ply", type=int, default=None, help="Stop after this ply (openings only, for the trap atlas)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="Where to write the CSV/JSON outputs")
    args = parser.parse_args()

    model, heuristic = Cached(model=get_human_model(settings.human_model)), Cached(model=HeuristicHumanModel())
    if model.model_version == heuristic.model_version:
        print("NOTE: the configured human model is the heuristic baseline, so the model cannot beat it.")

    stream = sys.stdin if args.pgn == "-" else open(args.pgn, encoding="utf-8", errors="replace")
    samples, quota, started, games = [], Counter(), time.time(), 0
    # Long runs save as they go: a partial file survives an interrupted run.
    args.out_dir.mkdir(parents=True, exist_ok=True)
    partial = open(args.out_dir / "chaos_samples.partial.csv", "w", newline="", encoding="utf-8")
    partial_writer = None
    with StockfishEngine() as raw_engine:
        engine = Cached(engine=raw_engine)
        while len(samples) < args.positions:
            game = chess.pgn.read_game(stream)
            if game is None:
                break
            if not cv.is_bullet_1_0(game.headers.get("TimeControl")):
                continue
            games += 1
            new = sample_game(game, engine, model, heuristic, args.nodes, quota, args.per_cell, args.min_ply, args.max_ply)
            samples.extend(new)
            if new:
                if partial_writer is None:
                    partial_writer = csv.DictWriter(partial, fieldnames=list(new[0]))
                    partial_writer.writeheader()
                partial_writer.writerows(new)
                partial.flush()
            if games % 50 == 0:
                print(f"{games} games, {len(samples)} samples, {time.time() - started:.0f}s")

    partial.close()
    tuning = [s for s in samples if not cv.is_held_out(s["game_id"])]
    held_out = [s for s in samples if cv.is_held_out(s["game_id"])]
    summary = cv.summarize_validation(tuning, held_out)
    runtime = time.time() - started
    write_outputs(samples, summary, model.model_version, runtime, args.out_dir)

    print(f"\n{len(samples)} samples from {games} games in {runtime:.0f}s -> {args.out_dir}")
    print(f"Brier (held-out): {summary['brier']}")
    print(f"Clock multipliers (tuning set): {summary['clock_multipliers']}")
    print("GO: chaos beats both baselines" if summary["beats_baselines"] else "NO-GO: chaos does not beat both baselines — rethink before M5+")


if __name__ == "__main__":
    main()

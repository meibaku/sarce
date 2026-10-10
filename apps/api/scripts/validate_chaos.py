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
from app.services.stockfish import StockfishEngine

OUT_DIR = Path(__file__).resolve().parent / "out"


def reply_left_safe_set(engine, board, reply, lines, nodes) -> int | None:
    """1 when the reply actually played lost more than SAFE_TOL EP, else 0."""
    best = lines[0]["ep"]
    for line in lines:
        if line["move_uci"] == reply.uci():
            return int(best - line["ep"] > lens_config.SAFE_TOL)
    # Not among the stored lines: evaluate the position it leads to.
    after = board.copy()
    after.push(reply)
    if after.is_game_over():
        return int(not after.is_checkmate())
    reply_lines = engine.analyse(after, nodes=nodes, multipv=1)
    if not reply_lines or reply_lines[0]["ep"] is None:
        return None
    return int(best - (1.0 - reply_lines[0]["ep"]) > lens_config.SAFE_TOL)


def sample_game(game, engine, model, heuristic, nodes, quota, per_cell) -> list[dict]:
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
        if ply < 8 or clock is None or quota[(band, clock)] >= per_cell:
            continue
        lines = engine.analyse(board, nodes=nodes, multipv=settings.analysis_multipv)
        if len(lines) < 2 or lines[0]["ep"] is None:
            continue
        if not lens_config.DECIDED_LOW <= 1.0 - lines[0]["ep"] <= lens_config.DECIDED_HIGH:
            continue  # the mover's game was already decided
        failed = reply_left_safe_set(engine, board, moves[ply + 1], lines, nodes)
        if failed is None:
            continue

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
            }
        )
    return samples


def write_outputs(samples: list[dict], summary: dict, model_version: str, runtime: float) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if samples:
        with open(OUT_DIR / "chaos_samples.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
            writer.writeheader()
            writer.writerows(samples)
    with open(OUT_DIR / "chaos_calibration.csv", "w", newline="", encoding="utf-8") as handle:
        fields = ["band", "clock", "bin_low", "n", "predicted", "observed"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary["calibration"])
    report = {**summary, "model_version": model_version, "runtime_seconds": round(runtime, 1)}
    (OUT_DIR / "chaos_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate chaos scores on Lichess bullet games")
    parser.add_argument("pgn", help="Path to a decompressed Lichess PGN, or - for stdin")
    parser.add_argument("--positions", type=int, default=2000, help="Target sample size")
    parser.add_argument("--per-cell", type=int, default=200, help="Max samples per rating band x clock bucket")
    parser.add_argument("--nodes", type=int, default=settings.analysis_nodes)
    args = parser.parse_args()

    model, heuristic = get_human_model(settings.human_model), HeuristicHumanModel()
    if model.model_version == heuristic.model_version:
        print("NOTE: the configured human model is the heuristic baseline, so the model cannot beat it.")

    stream = sys.stdin if args.pgn == "-" else open(args.pgn, encoding="utf-8", errors="replace")
    samples, quota, started, games = [], Counter(), time.time(), 0
    with StockfishEngine() as engine:
        while len(samples) < args.positions:
            game = chess.pgn.read_game(stream)
            if game is None:
                break
            if not cv.is_bullet_1_0(game.headers.get("TimeControl")):
                continue
            games += 1
            samples.extend(sample_game(game, engine, model, heuristic, args.nodes, quota, args.per_cell))
            if games % 50 == 0:
                print(f"{games} games, {len(samples)} samples, {time.time() - started:.0f}s")

    tuning = [s for s in samples if not cv.is_held_out(s["game_id"])]
    held_out = [s for s in samples if cv.is_held_out(s["game_id"])]
    summary = cv.summarize_validation(tuning, held_out)
    runtime = time.time() - started
    write_outputs(samples, summary, model.model_version, runtime)

    print(f"\n{len(samples)} samples from {games} games in {runtime:.0f}s -> {OUT_DIR}")
    print(f"Brier (held-out): {summary['brier']}")
    print(f"Clock multipliers (tuning set): {summary['clock_multipliers']}")
    print("GO: chaos beats both baselines" if summary["beats_baselines"] else "NO-GO: chaos does not beat both baselines — rethink before M5+")


if __name__ == "__main__":
    main()

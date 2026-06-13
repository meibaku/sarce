"""
Reference player benchmarks — Tal corpus and future Phase 2 idols.

One-time batch jobs cache results in reference_benchmarks.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import chess
import chess.pgn
import httpx

from app.db.supabase import get_supabase
from app.services.analysis import build_style_vector_v1
from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION
from app.services.move_classifier import MoveClassifier

logger = logging.getLogger(__name__)

TAL_PGN_URL = "https://www.pgnmentor.com/players/Tal.zip"
TAL_PLAYER_NAME = "Mikhail Tal"


class ReferenceService:
    """Fetch, analyze, and cache reference player benchmarks."""

    async def get_tal_benchmark(self) -> dict:
        """Return cached Tal benchmark or empty placeholder."""
        sb = get_supabase()
        player_res = (
            sb.table("reference_players")
            .select("id, name, games_sampled")
            .eq("source_identifier", "pgnmentor-tal")
            .maybe_single()
            .execute()
        )
        if not player_res.data:
            return self._empty_benchmark(TAL_PLAYER_NAME)

        bench_res = (
            sb.table("reference_benchmarks")
            .select("*")
            .eq("reference_player_id", player_res.data["id"])
            .maybe_single()
            .execute()
        )
        if not bench_res.data:
            return {
                "playerName": player_res.data["name"],
                "brilliantPct": 0,
                "distribution": {**EMPTY_DISTRIBUTION},
                "gamesSampled": 0,
                "status": "pending",
            }

        row = bench_res.data
        return {
            "playerName": player_res.data["name"],
            "brilliantPct": float(row.get("brilliant_pct", 0)),
            "distribution": row.get("distribution", EMPTY_DISTRIBUTION),
            "gamesSampled": player_res.data.get("games_sampled", 0),
            "status": "complete",
        }

    async def process_tal_benchmark(
        self,
        max_games: int = 20,
        cache_dir: Path | None = None,
    ) -> dict:
        """
        Download Tal PGN corpus, classify sample, cache benchmark.

        Args:
            max_games: Limit games for local dev speed.
            cache_dir: Where to store downloaded ZIP.
        """
        cache_dir = cache_dir or Path(__file__).resolve().parents[2] / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        zip_path = cache_dir / "tal.zip"

        if not zip_path.exists():
            logger.info("Downloading Tal PGN corpus from %s", TAL_PGN_URL)
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.get(TAL_PGN_URL)
                res.raise_for_status()
                zip_path.write_bytes(res.content)

        pgns = self._extract_pgns(zip_path, max_games)
        classifier = MoveClassifier()
        merged = {**EMPTY_DISTRIBUTION}
        analyzed = 0

        for pgn_text in pgns:
            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if not game:
                continue
            board = game.board()
            moves = list(game.mainline_moves())
            # Tal played both colors in corpus — classify white moves as proxy
            classified = classifier.classify_game(board, moves, "white")
            dist = BaselineService.compute_distribution([m["quality"] for m in classified])
            for k in merged:
                merged[k] += dist.get(k, 0)
            analyzed += 1

        brilliant_pct = BaselineService.brilliant_pct(merged)
        style_vector = build_style_vector_v1(merged, brilliant_pct)

        sb = get_supabase()
        player_res = (
            sb.table("reference_players")
            .select("id")
            .eq("source_identifier", "pgnmentor-tal")
            .maybe_single()
            .execute()
        )
        if player_res.data:
            pid = player_res.data["id"]
            sb.table("reference_players").update(
                {"games_sampled": analyzed, "benchmark_status": "complete"}
            ).eq("id", pid).execute()
            sb.table("reference_benchmarks").upsert(
                {
                    "reference_player_id": pid,
                    "distribution": merged,
                    "brilliant_pct": brilliant_pct,
                    "style_vector": style_vector,
                },
                on_conflict="reference_player_id",
            ).execute()

        return {
            "playerName": TAL_PLAYER_NAME,
            "brilliantPct": brilliant_pct,
            "distribution": merged,
            "gamesSampled": analyzed,
            "status": "complete",
        }

    @staticmethod
    def _extract_pgns(zip_path: Path, max_games: int) -> list[str]:
        """Extract individual game PGNs from pgnmentor ZIP."""
        pgns: list[str] = []
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.endswith(".pgn"):
                    continue
                content = zf.read(name).decode("utf-8", errors="replace")
                # Split multi-game PGN files
                chunks = content.split("\n\n[")
                for i, chunk in enumerate(chunks):
                    if i > 0:
                        chunk = "[" + chunk
                    chunk = chunk.strip()
                    if chunk.startswith("["):
                        pgns.append(chunk)
                        if len(pgns) >= max_games:
                            return pgns
        return pgns

    @staticmethod
    def _empty_benchmark(name: str) -> dict:
        return {
            "playerName": name,
            "brilliantPct": 0,
            "distribution": {**EMPTY_DISTRIBUTION},
            "gamesSampled": 0,
            "status": "pending",
        }

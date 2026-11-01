"""Prewarm and prove the engine/model identities baked into the pilot image."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.services.maia_model import Maia2HumanModel  # noqa: E402
from app.services.runtime_identity import (  # noqa: E402
    BRILLIANT_V4_THRESHOLDS,
    SHA_PATTERN,
)


def stockfish_version(executable: str) -> str:
    result = subprocess.run(
        [executable], input="uci\nquit\n", text=True, capture_output=True, timeout=15, check=True
    )
    match = re.search(r"\bStockfish\s+(\d+(?:\.\d+)*)\b", result.stdout)
    if not match:
        raise RuntimeError("Stockfish did not report a parseable version")
    return match.group(1)


def prove_checkpoint(checkpoint: str) -> dict[str, int | bool]:
    board = chess.Board()
    probabilities = Maia2HumanModel(checkpoint).move_probs(board, 1800)
    legal = {move.uci() for move in board.legal_moves}
    normalized = set(probabilities) == legal and abs(sum(probabilities.values()) - 1.0) < 1e-6
    if not normalized or any(value < 0 or value > 1 for value in probabilities.values()):
        raise RuntimeError(f"Maia-2 {checkpoint} returned invalid legal-move probabilities")
    return {"legalMoves": len(legal), "normalized": True}


def build_evidence(artifact_sha: str, image_digest: str, verified_by: str) -> dict:
    checks: dict[str, bool] = {}
    evidence: dict = {
        "schemaVersion": 1,
        "artifactSha": artifact_sha,
        "imageDigest": image_digest,
        "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verifiedBy": verified_by,
        "brilliantV4": BRILLIANT_V4_THRESHOLDS,
    }
    try:
        checks["artifactSha"] = bool(SHA_PATTERN.fullmatch(artifact_sha))
        evidence["stockfishVersion"] = stockfish_version(settings.stockfish_executable)
        checks["stockfishVersion"] = (
            evidence["stockfishVersion"] == settings.pilot_expected_stockfish_version
        )
        evidence["maiaVersion"] = importlib.metadata.version("maia2")
        checks["maiaVersion"] = evidence["maiaVersion"] == settings.pilot_expected_maia_version
        evidence["maiaCheckpoints"] = {
            checkpoint: prove_checkpoint(checkpoint) for checkpoint in ("blitz", "rapid")
        }
        checks["maiaCheckpoints"] = True
        checks["brilliantV4"] = True
    except Exception as exc:
        evidence["error"] = type(exc).__name__
        checks.setdefault("runtime", False)
    evidence["checks"] = checks
    evidence["status"] = "passed" if checks and all(checks.values()) else "failed"
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--artifact-sha", default=os.getenv("PILOT_ARTIFACT_SHA", ""))
    parser.add_argument("--image-digest", default=os.getenv("PILOT_IMAGE_DIGEST", "unavailable"))
    parser.add_argument("--verified-by", default="pilot-runtime-check")
    args = parser.parse_args()
    evidence = build_evidence(args.artifact_sha, args.image_digest, args.verified_by)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

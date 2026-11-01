"""Fail-closed identity checks for the exact pilot analysis runtime."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import Settings
from app.services.brilliant import ALTERNATIVE_EP, FIND_RATE_MAX, LOST_EP, SOUND_EP_LOSS


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
BRILLIANT_V4_THRESHOLDS = {
    "soundEpLoss": SOUND_EP_LOSS,
    "lostEp": LOST_EP,
    "alternativeEp": ALTERNATIVE_EP,
    "findRateMax": FIND_RATE_MAX,
}


def load_runtime_manifest(path: str) -> dict:
    """Read the image-baked proof; malformed or absent evidence is never ready."""
    if not path or not Path(path).is_file():
        return {}
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def runtime_identity_checks(config: Settings) -> dict[str, bool]:
    """Return non-sensitive booleans suitable for the public readiness endpoint."""
    manifest = load_runtime_manifest(config.pilot_runtime_manifest_path)
    artifact = manifest.get("artifactSha")
    checkpoints = manifest.get("maiaCheckpoints") or {}
    return {
        "artifact_identity": bool(
            SHA_PATTERN.fullmatch(config.pilot_artifact_sha)
            and artifact == config.pilot_artifact_sha
        ),
        "runtime_manifest": (
            manifest.get("schemaVersion") == 1
            and manifest.get("status") == "passed"
            and bool(manifest.get("checkedAt"))
        ),
        "stockfish_version": manifest.get("stockfishVersion")
        == config.pilot_expected_stockfish_version,
        "maia_checkpoints": (
            manifest.get("maiaVersion") == config.pilot_expected_maia_version
            and set(checkpoints) == {"blitz", "rapid"}
            and all(bool(item.get("normalized")) for item in checkpoints.values())
        ),
        "brilliant_v4_thresholds": manifest.get("brilliantV4")
        == BRILLIANT_V4_THRESHOLDS,
    }

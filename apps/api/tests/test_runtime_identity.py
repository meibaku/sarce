import json

from app.config import Settings
from app.services.runtime_identity import BRILLIANT_V4_THRESHOLDS, runtime_identity_checks


ARTIFACT_SHA = "a" * 40


def write_manifest(path, **updates):
    manifest = {
        "schemaVersion": 1,
        "status": "passed",
        "artifactSha": ARTIFACT_SHA,
        "checkedAt": "2026-11-01T00:00:00Z",
        "stockfishVersion": "19",
        "maiaVersion": "0.11.0",
        "maiaCheckpoints": {
            "blitz": {"normalized": True},
            "rapid": {"normalized": True},
        },
        "brilliantV4": BRILLIANT_V4_THRESHOLDS,
    }
    manifest.update(updates)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def config(path):
    return Settings(
        pilot_artifact_sha=ARTIFACT_SHA,
        pilot_runtime_manifest_path=str(path),
        pilot_expected_stockfish_version="19",
        pilot_expected_maia_version="0.11.0",
    )


def test_exact_runtime_manifest_passes(tmp_path):
    manifest = tmp_path / "runtime.json"
    write_manifest(manifest)
    assert all(runtime_identity_checks(config(manifest)).values())


def test_manifest_fails_closed_on_checkpoint_or_threshold_drift(tmp_path):
    manifest = tmp_path / "runtime.json"
    write_manifest(
        manifest,
        maiaCheckpoints={"blitz": {"normalized": True}},
        brilliantV4={**BRILLIANT_V4_THRESHOLDS, "findRateMax": 0.25},
    )
    checks = runtime_identity_checks(config(manifest))
    assert checks["maia_checkpoints"] is False
    assert checks["brilliant_v4_thresholds"] is False


def test_missing_or_malformed_manifest_never_passes(tmp_path):
    manifest = tmp_path / "runtime.json"
    assert not any(runtime_identity_checks(config(manifest)).values())
    manifest.write_text("not json", encoding="utf-8")
    assert not any(runtime_identity_checks(config(manifest)).values())

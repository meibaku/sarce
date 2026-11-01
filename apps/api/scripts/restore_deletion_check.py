"""Export or reapply deletion tombstones around a database restore."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.privacy import PrivacyService


def owner_counts_match(source: dict, restored: dict) -> bool:
    """Require the same named owner tables and exact row counts before re-deletion."""
    return bool(source) and source == restored and all(
        isinstance(value, int) and value >= 0 for value in source.values()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--export", type=Path, metavar="LEDGER")
    action.add_argument("--apply", type=Path, metavar="LEDGER")
    parser.add_argument("--result", type=Path, help="Required readiness result path when applying")
    parser.add_argument("--artifact-sha")
    parser.add_argument("--image-digest")
    parser.add_argument("--backup-id")
    parser.add_argument("--restore-project-id")
    parser.add_argument("--source-counts", type=Path)
    parser.add_argument("--restored-counts", type=Path)
    parser.add_argument("--verified-by", default="restore-rehearsal")
    args = parser.parse_args()
    service = PrivacyService()
    if args.export:
        payload = {"schemaVersion": 1, "tombstones": service.tombstones()}
        args.export.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Exported {len(payload['tombstones'])} deletion tombstones to {args.export}")
        return 0
    if not args.result:
        parser.error("--result is required with --apply")
    required = (
        args.artifact_sha, args.image_digest, args.backup_id, args.restore_project_id,
        args.source_counts, args.restored_counts,
    )
    if any(not value for value in required) or len(args.artifact_sha) != 40:
        parser.error("apply requires artifact SHA, image digest, backup id and restore project id")
    payload = json.loads(args.apply.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("tombstones"), list):
        raise ValueError("Unsupported deletion tombstone ledger")
    result = service.restore_check(payload["tombstones"])
    source_counts = json.loads(args.source_counts.read_text(encoding="utf-8"))
    restored_counts = json.loads(args.restored_counts.read_text(encoding="utf-8"))
    counts_match = owner_counts_match(source_counts, restored_counts)
    if not counts_match:
        result["status"] = "failed"
    result.update({
        "schemaVersion": 1,
        "artifactSha": args.artifact_sha,
        "imageDigest": args.image_digest,
        "backupId": args.backup_id,
        "restoreProjectId": args.restore_project_id,
        "verifiedBy": args.verified_by,
        "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": {
            "ownerTableCountsMatch": counts_match,
            "deletedOwnerRowsRemaining": result["remaining"] == 0,
        },
    })
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

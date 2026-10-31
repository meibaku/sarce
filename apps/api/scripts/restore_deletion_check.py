"""Export or reapply deletion tombstones around a database restore."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.privacy import PrivacyService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--export", type=Path, metavar="LEDGER")
    action.add_argument("--apply", type=Path, metavar="LEDGER")
    parser.add_argument("--result", type=Path, help="Required readiness result path when applying")
    args = parser.parse_args()
    service = PrivacyService()
    if args.export:
        payload = {"schemaVersion": 1, "tombstones": service.tombstones()}
        args.export.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Exported {len(payload['tombstones'])} deletion tombstones to {args.export}")
        return 0
    if not args.result:
        parser.error("--result is required with --apply")
    payload = json.loads(args.apply.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("tombstones"), list):
        raise ValueError("Unsupported deletion tombstone ledger")
    result = service.restore_check(payload["tombstones"])
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

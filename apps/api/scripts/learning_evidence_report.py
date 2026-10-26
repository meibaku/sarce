"""Print the frozen LE2 primary report from append-only attempts. Run from `apps/api`."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.supabase import get_supabase
from app.services.learning_evidence import BOOTSTRAP_RESAMPLES, primary_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen Learning Evidence Phase 2 outcome report")
    parser.add_argument("--protocol-version", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()
    rows = (
        get_supabase().table("learning_attempts").select("*")
        .eq("protocol_version", args.protocol_version).in_("phase", ["baseline", "day7"])
        .order("participant_key").order("responded_at").execute().data or []
    )
    frozen = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str).encode()
    report = primary_report(rows, resamples=args.resamples)
    report.update({
        "protocolVersion": args.protocol_version,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "sourceSha256": hashlib.sha256(frozen).hexdigest(),
    })
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


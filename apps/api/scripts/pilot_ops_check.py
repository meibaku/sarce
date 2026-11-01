"""Write secret-free operational evidence from the SGP1 pilot host."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def request_json(url: str, token: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def memory_used_percent(meminfo: str) -> float:
    values = {}
    for line in meminfo.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
    total, available = values["MemTotal"], values["MemAvailable"]
    return round((total - available) / total * 100, 2)


def recent_5xx(path: Path, limit: int = 1000) -> int:
    if not path.is_file():
        return 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    count = 0
    for line in lines:
        try:
            status = int(json.loads(line).get("status", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
        count += status >= 500
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-url", default=os.getenv("PILOT_API_URL", ""))
    parser.add_argument("--artifact-sha", default=os.getenv("PILOT_ARTIFACT_SHA", ""))
    parser.add_argument("--image-digest", default=os.getenv("PILOT_IMAGE_DIGEST", ""))
    parser.add_argument("--operator-token", default=os.getenv("PILOT_OPERATOR_ACCESS_TOKEN", ""))
    parser.add_argument("--caddy-log", type=Path, default=Path("/var/log/caddy/sarce-pilot-access.json"))
    parser.add_argument("--max-oldest-queue-minutes", type=int, default=30)
    parser.add_argument("--verified-by", default="sgp1-ops-check")
    args = parser.parse_args()
    if not args.api_url or len(args.artifact_sha) != 40 or not args.image_digest or not args.operator_token:
        parser.error("API URL, artifact SHA, image digest and operator token are required")

    ready = request_json(f"{args.api_url.rstrip('/')}/health/ready")
    monitor = request_json(f"{args.api_url.rstrip('/')}/monitor/snapshot", args.operator_token)
    disk = shutil.disk_usage("/")
    disk_free = round(disk.free / disk.total * 100, 2)
    memory = memory_used_percent(Path("/proc/meminfo").read_text(encoding="utf-8"))
    oldest = monitor.get("oldestPendingAt")
    oldest_age = 0.0
    if oldest:
        queued_at = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        oldest_age = (datetime.now(timezone.utc) - queued_at).total_seconds() / 60
    failures = recent_5xx(args.caddy_log)
    checks = {
        "readiness": ready.get("status") == "ready" and all(ready.get("checks", {}).values()),
        "queue_age": oldest_age <= args.max_oldest_queue_minutes,
        "failed_queue_empty": monitor.get("queue", {}).get("failed", 0) == 0,
        "monitor_alerts_empty": not monitor.get("alerts"),
        "disk_free": disk_free >= 15,
        "memory_available": memory <= 90,
        "recent_5xx": failures == 0,
    }
    evidence = {
        "schemaVersion": 1,
        "artifactSha": args.artifact_sha,
        "imageDigest": args.image_digest,
        "status": "passed" if all(checks.values()) else "failed",
        "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verifiedBy": args.verified_by,
        "checks": checks,
        "metrics": {
            "oldestQueueMinutes": round(oldest_age, 2), "failedJobs": monitor.get("queue", {}).get("failed", 0),
            "diskFreePercent": disk_free, "memoryUsedPercent": memory, "recent5xx": failures,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

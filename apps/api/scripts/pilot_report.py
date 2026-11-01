"""Produce the predeclared, pseudonymous first-ten pilot outcome report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import create_client  # noqa: E402

from app.services.uncertainty import wilson  # noqa: E402

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def occurred_by(value: str | None, cutoff: str) -> bool:
    if not value:
        return False
    at = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    end = datetime.fromisoformat(cutoff.replace("Z", "+00:00")).astimezone(timezone.utc)
    return at <= end


def pseudonym(user_id: str, salt: str) -> str:
    return hashlib.sha256(f"pilot-report:{salt}:{user_id}".encode()).hexdigest()[:20]


def build_report(consents: list[dict], feedback: list[dict], surveys: list[dict], as_of: str, salt: str) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in feedback:
        if occurred_by(row.get("created_at"), as_of):
            grouped[row["user_id"]].append(row)
    survey_by_user = {
        row["user_id"]: row for row in surveys if occurred_by(row.get("submitted_at"), as_of)
    }
    participants = []
    complete_rates = []
    for consent in sorted(consents, key=lambda row: row["user_id"]):
        rows = sorted(grouped[consent["user_id"]], key=lambda row: (row["created_at"], row["id"]))[:10]
        counts = {answer: sum(row["resonance"] == answer for row in rows) for answer in ("yes", "partly", "no")}
        interval = wilson(counts["yes"], len(rows))
        rate = counts["yes"] / len(rows) if rows else None
        complete = len(rows) == 10
        if complete:
            complete_rates.append(rate)
        participants.append({
            "participant": pseudonym(consent["user_id"], salt),
            "reads": len(rows),
            "answers": counts,
            "feelsLikeMeRate": rate,
            "wilson95": None if interval is None else {"low": interval[0], "high": interval[1]},
            "withdrawn": occurred_by(consent.get("withdrawn_at"), as_of),
            "continueUsing": (survey_by_user.get(consent["user_id"]) or {}).get("continue_using"),
        })
    exit_rows = list(survey_by_user.values())
    continue_fraction = (
        sum(row["continue_using"] == "yes" for row in exit_rows) / len(exit_rows) if exit_rows else None
    )
    median_rate = statistics.median(complete_rates) if complete_rates else None
    return {
        "asOf": as_of,
        "participants": participants,
        "summary": {
            "consentedParticipants": len(consents),
            "completeParticipants": len(complete_rates),
            "medianFeelsLikeMeRate": median_rate,
            "continueRespondents": len(exit_rows),
            "continueFraction": continue_fraction,
            "resonanceThresholdMet": median_rate is not None and median_rate >= 0.70,
            "continueThresholdMet": continue_fraction is not None and continue_fraction >= 0.50,
        },
        "claimBoundary": "Descriptive pilot evidence only; not chess improvement, objective strength, or population generalizability.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-sha", default=os.getenv("PILOT_ARTIFACT_SHA", ""))
    parser.add_argument("--image-digest", default=os.getenv("PILOT_IMAGE_DIGEST", ""))
    parser.add_argument("--verified-by", default="pilot-outcome-report")
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
    if not SHA.fullmatch(args.artifact_sha) or not DIGEST.fullmatch(args.image_digest) or not os.getenv("PILOT_REPORT_SALT"):
        parser.error("artifact SHA, image digest and PILOT_REPORT_SALT are required")
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    cutoff = as_of.isoformat().replace("+00:00", "Z")
    consents = sb.table("pilot_consents").select("user_id,consented_at,withdrawn_at").lte("consented_at", cutoff).execute().data or []
    feedback = sb.table("pilot_read_feedback").select("id,user_id,resonance,created_at").lte("created_at", cutoff).execute().data or []
    surveys = sb.table("pilot_exit_surveys").select("user_id,continue_using,submitted_at").lte("submitted_at", cutoff).execute().data or []
    report = build_report(consents, feedback, surveys, cutoff, os.environ["PILOT_REPORT_SALT"])
    report.update({
        "schemaVersion": 1, "artifactSha": args.artifact_sha, "imageDigest": args.image_digest,
        "status": "passed", "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verifiedBy": args.verified_by,
        "checks": {"firstTenOnly": True, "pseudonymous": True, "claimBoundaryRecorded": True},
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

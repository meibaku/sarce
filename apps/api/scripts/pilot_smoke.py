"""Run the destructive, two-user pilot rehearsal against the deployed candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from supabase import create_client


FORBIDDEN_PILOT_FIELDS = {
    "chaos", "survival", "squeeze", "swindle", "clock", "prophylaxis",
    "questions", "intentions", "p_fail", "idea_arcs", "references",
}


def contains_forbidden(value) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN_PILOT_FIELDS.intersection(value)) or any(
            contains_forbidden(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(contains_forbidden(item) for item in value)
    return False


def pseudonym(user_id: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:20]


def clone_game(row: dict, owner: str, sequence: int) -> dict:
    """Create an owned disposable read without copying generated relationship fields."""
    clone = {key: value for key, value in row.items() if key not in {"id", "created_at", "updated_at"}}
    clone.update(
        id=str(uuid.uuid4()),
        user_id=owner,
        external_id=f"https://chess.com/game/live/sarce-smoke-{sequence}-{uuid.uuid4().hex[:8]}",
    )
    return clone


class Rehearsal:
    def __init__(self, args) -> None:
        self.args = args
        self.admin = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
        self.anon = os.environ["SUPABASE_ANON_KEY"]
        self.operator = os.environ["PILOT_OPERATOR_ACCESS_TOKEN"]
        self.client = httpx.Client(base_url=args.api_url.rstrip("/"), timeout=30)
        self.salt = secrets.token_hex(16)
        self.users = []
        self.checks: dict[str, bool] = {}

    def check(self, name: str, condition: bool) -> None:
        self.checks[name] = bool(condition)
        print(f"{'PASS' if condition else 'FAIL'}  {name}")

    @staticmethod
    def auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def create_user(self) -> tuple[str, str]:
        email = f"pilot-smoke-{secrets.token_hex(6)}@sarce.test"
        password = secrets.token_urlsafe(24)
        user = self.admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        ).user
        token = create_client(os.environ["SUPABASE_URL"], self.anon).auth.sign_in_with_password(
            {"email": email, "password": password}
        ).session.access_token
        self.users.append(user.id)
        return user.id, token

    def admit(self, token: str) -> None:
        invitation = self.client.post(
            "/pilot/invitations", headers=self.auth(self.operator), json={"hours": 2}
        )
        invitation.raise_for_status()
        redeemed = self.client.post(
            "/pilot/invitations/redeem", headers=self.auth(token),
            json={"token": invitation.json()["token"]},
        )
        redeemed.raise_for_status()
        consent = self.client.post(
            "/pilot/consent", headers=self.auth(token), json={
                "adultConfirmed": True,
                "protocolVersion": self.args.protocol_version,
                "privacyVersion": self.args.privacy_version,
            },
        )
        consent.raise_for_status()

    def wait_for_game(self, token: str) -> dict:
        imported = self.client.post(
            "/games/import", headers=self.auth(token), json={
                "username": self.args.username, "max_games": 1, "analyze": True,
            },
        )
        imported.raise_for_status()
        self.check("one_finished_game_imported", imported.json().get("imported") == 1)
        deadline = time.monotonic() + self.args.analysis_timeout
        latest = None
        while time.monotonic() < deadline:
            games = self.client.get("/games?limit=1", headers=self.auth(token))
            games.raise_for_status()
            rows = games.json().get("games", [])
            latest = rows[0] if rows else None
            if latest and latest.get("analysisStatus") in {"ready", "completed"}:
                return latest
            time.sleep(3)
        raise RuntimeError("analysis did not complete before the rehearsal deadline")

    def run(self) -> dict:
        first_id, first_token = self.create_user()
        second_id, second_token = self.create_user()
        self.check("distinct_authenticated_users", first_id != second_id)
        self.admit(first_token)
        self.admit(second_token)
        consent_rows = self.admin.table("pilot_consents").select(
            "user_id,protocol_version,privacy_version"
        ).in_("user_id", [first_id, second_id]).execute().data or []
        self.check("exact_consent_versions", len(consent_rows) == 2 and all(
            row["protocol_version"] == self.args.protocol_version
            and row["privacy_version"] == self.args.privacy_version for row in consent_rows
        ))

        game = self.wait_for_game(first_token)
        game_id = game["id"]
        queued_before = self.admin.table("analysis_jobs").select("id,game_id,status").eq(
            "game_id", game_id
        ).execute().data or []
        if self.args.restart_command:
            subprocess.run(shlex.split(self.args.restart_command), check=True, timeout=120)
            time.sleep(5)
        queued_after = self.admin.table("analysis_jobs").select("id,game_id,status").eq(
            "game_id", game_id
        ).execute().data or []
        self.check("restart_preserved_single_job", len(queued_before) == len(queued_after) == 1)

        denied = self.client.get(f"/games/{game_id}", headers=self.auth(second_token))
        self.check("cross_tenant_game_denied", denied.status_code in {403, 404})
        denied_feedback = self.client.get(
            f"/pilot/games/{game_id}/feedback", headers=self.auth(second_token)
        )
        self.check("cross_tenant_feedback_denied", denied_feedback.status_code in {403, 404})
        self.check(
            "participant_operator_route_denied",
            self.client.get("/monitor", headers=self.auth(first_token)).status_code == 403,
        )

        read = self.client.get(f"/pilot/games/{game_id}/read", headers=self.auth(first_token))
        self.check("pilot_read_available", read.status_code == 200)
        if read.status_code == 200:
            self.check("brilliant_only_dto", not contains_forbidden(read.json()))

        original = self.admin.table("games").select("*").eq("id", game_id).single().execute().data
        clones = [clone_game(original, first_id, number) for number in range(2, 12)]
        self.admin.table("games").insert(clones).execute()
        game_ids = [game_id, *[row["id"] for row in clones]]
        for index, owned_game in enumerate(game_ids[:10]):
            response = self.client.put(
                f"/pilot/games/{owned_game}/feedback", headers=self.auth(first_token),
                json={"resonance": ("yes", "partly", "no")[index % 3], "comment": f"read {index}"},
            )
            self.check(f"feedback_{index + 1}_saved", response.status_code == 200)
        eleventh = self.client.put(
            f"/pilot/games/{game_ids[10]}/feedback", headers=self.auth(first_token),
            json={"resonance": "yes", "comment": "must be rejected"},
        )
        self.check("eleventh_answer_rejected", eleventh.status_code == 422)
        edited = self.client.put(
            f"/pilot/games/{game_id}/feedback", headers=self.auth(first_token),
            json={"resonance": "partly", "comment": "edited canonically"},
        )
        restored = self.client.get(
            f"/pilot/games/{game_id}/feedback", headers=self.auth(first_token)
        )
        self.check("feedback_edit_is_idempotent", edited.status_code == 200 and restored.json() == edited.json())
        status = self.client.get("/pilot/status", headers=self.auth(first_token)).json()
        self.check("first_ten_aggregation", status.get("completedReads") == 10 and status.get("state") == "complete")

        exported = self.client.get("/privacy/me/export", headers=self.auth(first_token))
        self.check("complete_export_available", exported.status_code == 200 and "pilot" in exported.text)
        withdrawn = self.client.post("/pilot/withdraw", headers=self.auth(second_token))
        denied_import = self.client.post(
            "/games/import", headers=self.auth(second_token),
            json={"username": self.args.username, "max_games": 1},
        )
        self.check("withdrawal_is_read_only", withdrawn.status_code == 200 and denied_import.status_code in {403, 422})

        deletion = self.client.delete("/privacy/me?confirm=DELETE", headers=self.auth(first_token))
        self.check("typed_deletion_started", deletion.status_code in {200, 202})
        return {
            "schemaVersion": 1,
            "artifactSha": self.args.artifact_sha,
            "imageDigest": self.args.image_digest,
            "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verifiedBy": self.args.verified_by,
            "participants": [pseudonym(user_id, self.salt) for user_id in self.users],
            "checks": self.checks,
            "status": "passed" if self.checks and all(self.checks.values()) else "failed",
        }

    def cleanup(self) -> None:
        for user_id in self.users:
            try:
                self.admin.auth.admin.delete_user(user_id)
            except Exception:
                pass
        self.client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-url", default=os.getenv("PILOT_API_URL", ""))
    parser.add_argument("--artifact-sha", default=os.getenv("PILOT_ARTIFACT_SHA", ""))
    parser.add_argument("--image-digest", default=os.getenv("PILOT_IMAGE_DIGEST", ""))
    parser.add_argument("--username", default=os.getenv("PILOT_SMOKE_CHESSCOM_USERNAME", ""))
    parser.add_argument("--protocol-version", default=os.getenv("PILOT_PROTOCOL_VERSION", "style-v1"))
    parser.add_argument("--privacy-version", default=os.getenv("PILOT_PRIVACY_VERSION", "pilot-privacy-v1"))
    parser.add_argument("--restart-command", default=os.getenv("PILOT_RESTART_COMMAND", ""))
    parser.add_argument("--analysis-timeout", type=int, default=900)
    parser.add_argument("--verified-by", default="production-rehearsal")
    args = parser.parse_args()
    if not args.api_url or not args.username or len(args.artifact_sha) != 40 or not args.image_digest:
        parser.error("API URL, smoke username, 40-character artifact SHA and image digest are required")
    rehearsal = Rehearsal(args)
    try:
        evidence = rehearsal.run()
    except Exception as exc:
        evidence = {
            "schemaVersion": 1, "artifactSha": args.artifact_sha,
            "imageDigest": args.image_digest, "status": "failed",
            "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verifiedBy": args.verified_by, "checks": rehearsal.checks,
            "error": type(exc).__name__,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rehearsal.cleanup()  # cleanup happens only after durable evidence is written
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
Sign-in smoke test against a real Supabase Auth (CHAOS_PLAN M8: "sign-in untested against a live Auth").

Usage (from apps/api, against a local `supabase start` stack or a staging project):
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... SUPABASE_ANON_KEY=... python -m scripts.auth_smoke

Creates a throwaway confirmed user with a random password (admin API), signs in with the password to get a
genuine access token, then runs the API in-process with AUTH_REQUIRED on and checks:
  1. no token → 401;  2. a forged token → 401;  3. the real token → 200;
  4. the signed-in user sees only their own data (no one else's games), even when asking for another user_id;
  5. settings written while signed in land on that user's profile.
The user is deleted at the end, whatever happens. Never point this at production.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from supabase import create_client  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> int:
    url, service, anon = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"], os.environ["SUPABASE_ANON_KEY"]
    admin = create_client(url, service)
    email = f"smoke-{secrets.token_hex(4)}@sarce.test"
    password = secrets.token_urlsafe(18)
    user = admin.auth.admin.create_user({"email": email, "password": password, "email_confirm": True}).user
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")
        if not ok:
            failures.append(name)

    try:
        token = create_client(url, anon).auth.sign_in_with_password({"email": email, "password": password}).session.access_token
        settings.auth_required = True
        from app.main import app

        client = TestClient(app)
        r = client.get("/users/home")
        check("no token is refused", r.status_code == 401, str(r.status_code))
        r = client.get("/users/home", headers={"Authorization": "Bearer not-a-real-token"})
        check("a forged token is refused", r.status_code == 401, str(r.status_code))

        auth = {"Authorization": f"Bearer {token}"}
        r = client.get("/users/home", headers=auth)
        check("the real token is accepted", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        check("a new user sees no one else's games", r.is_success and r.json().get("latest") is None, r.text[:120])

        # Asking for someone else's data by id must still return only the signed-in user's.
        r = client.get(f"/users/sacrifices?user_id={settings.local_user_id}", headers=auth)
        check("another user's id is ignored when signed in", r.is_success and r.json().get("sacrifices") == [], r.text[:120])

        r = client.put("/users/settings", headers=auth, json={"questionBudget": 2})
        row = admin.table("profiles").select("settings").eq("id", user.id).limit(1).execute().data
        check("settings land on the signed-in user's profile", r.is_success and bool(row) and row[0]["settings"].get("questionBudget") == 2, r.text[:120])
    finally:
        admin.auth.admin.delete_user(user.id)
        print(f"cleaned up {email}")
    print("OK" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from supabase import Client

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        # Imported here, not at module load: a Sarce Node runs the engine modules that import this file but never
        # opens the database, so it needn't install the client (ADR 0010, offline kit).
        from supabase import create_client

        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client

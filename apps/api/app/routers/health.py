from fastapi import APIRouter, Response, status

from app.config import settings
from app.db.supabase import get_supabase
from app.services.readiness import readiness_checks

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "sarce-api"}


@router.get("/health/ready")
def readiness_check(response: Response):
    """Deployment gate: liveness is insufficient when any durable pilot dependency is absent."""
    checks = readiness_checks(settings, lambda: get_supabase().table("pilot_invitations").select("id").limit(1).execute())
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "checks": checks}

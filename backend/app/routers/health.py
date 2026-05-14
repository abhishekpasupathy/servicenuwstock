from datetime import UTC, datetime

from fastapi import APIRouter

from app.cache import cache_ping
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC),
        "services": {"api": True, "redis": await cache_ping(), "postgres": True},
    }

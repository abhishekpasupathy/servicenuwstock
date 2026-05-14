from datetime import UTC, datetime

from fastapi import APIRouter

from app.cache import cache_ping
from app.core.config import get_settings
from app.services.data_fetcher import get_quote

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


@router.get("/health/diagnostics")
async def health_diagnostics():
    settings = get_settings()
    quote_ok = False
    provider = "unknown"
    degraded = False
    message = None

    try:
        quote = await get_quote(settings.default_ticker)
        quote_ok = bool(quote.get("price", 0) and quote.get("price", 0) > 0)
        provider = str(quote.get("source", "unknown"))
        degraded = bool(quote.get("stale") or quote.get("is_degraded"))
    except Exception as exc:
        message = str(exc)

    return {
        "status": "ok" if quote_ok else "degraded",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC),
        "api_prefix": settings.api_prefix,
        "default_ticker": settings.default_ticker,
        "checks": {
            "api": True,
            "redis": await cache_ping(),
            "market_data": quote_ok,
            "market_provider": provider,
            "market_data_degraded": degraded,
        },
        "message": message,
    }

from contextlib import asynccontextmanager
from typing import AsyncIterator
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.routers import alerts, backtest, health, insights, market, portfolio, quant, risk, websocket
from app.services.realtime_feed import feed

settings = get_settings()
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.app_env)
    logger.info("Starting %s", settings.app_name)
    await feed.connect()
    try:
        yield
    finally:
        await feed.stop()
        logger.info("Stopping %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Stock dashboard API using free public market data sources.",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "code": "RATE_LIMITED", "request_id": request.headers.get("x-request-id", "")},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled request error")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "code": "INTERNAL_ERROR", "request_id": request.headers.get("x-request-id", "")},
        )

    app.include_router(websocket.router)

    routers = (health.router, market.router, quant.router, risk.router, insights.router, portfolio.router, backtest.router, alerts.router, websocket.router)
    for router in routers:
        app.include_router(router, prefix=settings.api_prefix)

    if settings.api_prefix.rstrip("/") != "/api/v1":
        for router in routers:
            app.include_router(router, prefix="/api/v1")
    return app


app = create_app()

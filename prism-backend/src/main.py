"""FastAPI application factory: routers, middleware, exception handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.config.database import close_db, get_pool, init_db
from src.config.redis_client import close_redis, init_redis, redis_available
from src.config.settings import get_settings
from src.middleware.rate_limit import limiter
from src.middleware.request_logging import RequestLoggingMiddleware
from src.routers import (
    accounts,
    alerts,
    api_keys,
    auth,
    business_metrics,
    caps,
    commitments,
    costs,
    forecasts,
    llm,
    notifications,
    orgs,
    recommendations,
    reports,
    resources,
    scorecard,
    slack_actions,
    team,
    teams_actions,
    virtual_tags,
    webhooks,
)
from src.utils.errors import AppError
from src.utils.logger import configure_logging, get_logger
from src.ws.ws_manager import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_db()
    # Redis is optional — API + DB work without it (cache/queues degrade).
    await init_redis()
    logger.info("app_started", redis=redis_available())
    yield
    await close_redis()
    await close_db()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PRISM API", version="1.0.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Outermost: request_id + http_request access log (binds contextvars for the request).
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        body: dict = {"error": exc.message}
        if exc.code:
            body["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
            details.append({"field": loc, "message": err.get("msg", "invalid")})
        return JSONResponse(
            status_code=400,
            content={"error": "Validation failed", "details": details},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "unhandled_error",
            error=str(exc),
            path=request.url.path,
            method=request.method,
            request_id=request_id,
        )
        body = {"error": "Internal server error"}
        headers = {"X-Request-Id": request_id} if request_id else None
        return JSONResponse(status_code=500, content=body, headers=headers)

    @app.get("/health")
    async def health() -> JSONResponse:
        from src.config.redis_client import get_redis_client
        from src.utils.date_utils import utc_now

        db_ok = False
        redis_ok = False
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
        except Exception as exc:
            logger.debug("health_db_check_failed", error=str(exc))
        try:
            redis = get_redis_client()
            if redis is not None:
                redis_ok = bool(await redis.ping())
        except Exception as exc:
            logger.debug("health_redis_check_failed", error=str(exc))
            redis_ok = False
        # DB is required; Redis optional. Frontend can run against degraded.
        if not db_ok:
            status, code = "down", 503
        elif not redis_ok:
            status, code = "degraded", 200
        else:
            status, code = "ok", 200
        return JSONResponse(
            status_code=code,
            content={
                "status": status,
                "db": db_ok,
                "redis": redis_ok,
                "ts": utc_now().isoformat(),
            },
        )

    app.include_router(auth.router)
    app.include_router(orgs.router)
    app.include_router(team.router)
    app.include_router(accounts.router)
    app.include_router(costs.router)
    app.include_router(caps.router)
    app.include_router(alerts.router)
    app.include_router(reports.router)
    app.include_router(recommendations.router)
    app.include_router(forecasts.router)
    app.include_router(commitments.router)
    app.include_router(scorecard.router)
    app.include_router(notifications.router)
    app.include_router(virtual_tags.router)
    app.include_router(webhooks.router)
    app.include_router(llm.router)
    app.include_router(business_metrics.router)
    app.include_router(resources.router)
    app.include_router(api_keys.router)
    app.include_router(teams_actions.router)
    app.include_router(slack_actions.router)
    app.include_router(ws_router)

    return app


app = create_app()

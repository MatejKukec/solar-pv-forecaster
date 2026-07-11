"""Solar PV Forecaster API entrypoint."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.api.routes import ai, analytics, calibration, forecast, past
from backend.config import settings
from backend.db import engine, init_db
from backend.schemas import ErrorDetail, ErrorResponse
from backend.seed import seed_demo_data

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create SQLite tables and seed demo data if they don't exist yet, then run."""
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
    yield


app = FastAPI(title="Solar PV Forecaster API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Attach a correlation ID to every request for log tracing."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map validation-style ValueErrors to a structured 400 response."""
    logger.warning("value_error", path=request.url.path, error=str(exc))
    body = ErrorResponse(error=ErrorDetail(code="invalid_input", message=str(exc)))
    return JSONResponse(status_code=400, content=body.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Map raised HTTPExceptions (502s from upstream failures, etc.) to the same
    {error: {...}} shape as every other error response — without this, they fall
    through to FastAPI's default {"detail": ...} shape, which the frontend's
    error parsing doesn't look for, silently discarding the real message."""
    logger.warning("http_exception", path=request.url.path, status_code=exc.status_code, detail=str(exc.detail))
    body = ErrorResponse(error=ErrorDetail(code="request_failed", message=str(exc.detail)))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check, plus which AI provider is currently active."""
    return {"status": "ok", "ai_provider": "gemini" if settings.gemini_api_key else "mock"}


app.include_router(forecast.router)
app.include_router(ai.router)
app.include_router(past.router)
app.include_router(calibration.router)
app.include_router(analytics.router)

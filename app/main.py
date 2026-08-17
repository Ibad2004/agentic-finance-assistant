"""FastAPI main application entry point."""

from __future__ import annotations

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.accounts import router as accounts_router
from app.api.routes.auth import router as auth_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Finance and Tax Assistant API",
    description="Deterministic and Agentic Finance & Tax Assistant for England Income Tax (2026/27).",
    version="0.1.0",
)

# Mount API routers
app.include_router(auth_router)
app.include_router(accounts_router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Sanitize database exceptions to prevent leaking internal database schemas or credentials."""
    logger.error(f"Database error during request {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. The operation could not be completed safely."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled application errors and return sanitized response."""
    logger.error(f"Unhandled error during request {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

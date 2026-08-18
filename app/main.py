"""FastAPI main application entry point."""

from __future__ import annotations

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.accounts import router as accounts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.reports import router as reports_router
from app.api.routes.tax import router as tax_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Agentic Finance & Tax Assistant",
    description=(
        "An AI-powered agentic finance and tax assistant for England Income Tax estimation "
        "(Tax Year 2026/27). Features include user authentication, financial account management, "
        "CSV transaction import with AI-powered categorization, deterministic income tax calculation, "
        "budget tracking with spending analysis, and PDF financial report generation.\n\n"
        "**Architecture**: All financial calculations are deterministic Python code using fixed-precision "
        "Decimal arithmetic. The LLM (Groq) is used only for natural-language transaction categorization. "
        "All data is scoped to the authenticated user via JWT Bearer tokens."
    ),
    version="0.1.0",
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User registration and JWT token authentication. All protected endpoints require a valid Bearer token obtained from the login endpoint.",
        },
        {
            "name": "Financial Accounts",
            "description": "Manage user-owned GBP financial accounts and import transactions from UK bank CSV files.",
        },
        {
            "name": "Transactions",
            "description": "List, filter, and AI-categorize financial transactions within an account.",
        },
        {
            "name": "Budgets",
            "description": "Set spending budgets by category and date range with real-time spending analysis and status tracking.",
        },
        {
            "name": "Tax",
            "description": "Deterministic England Income Tax (2026/27) estimation engine. Calculations use official GOV.UK rates and are not official HMRC determinations.",
        },
        {
            "name": "Reports",
            "description": "Generate and retrieve PDF financial summary reports with income, expense, and category breakdowns.",
        },
        {
            "name": "Health",
            "description": "Application health check endpoint.",
        },
    ],
)

# Mount API routers
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(budgets_router)
app.include_router(reports_router)
app.include_router(tax_router)


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
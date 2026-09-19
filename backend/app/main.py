"""FastAPI application entrypoint — wires every module's router under /api/v1, configures
CORS, structured logging, and the global exception handlers that produce the standard error
envelope from docs/api-contract.md."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.allowances.router import router as allowances_router
from app.analytics.router import router as analytics_router
from app.attachments.router import router as attachments_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.banks.router import router as banks_router
from app.common.config import get_settings
from app.common.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.common.logging import configure_logging
from app.distribution.distributions_router import router as distributions_router
from app.distribution.router import router as distribution_router
from app.expenses.router import router as expenses_router
from app.financial_periods.router import router as financial_periods_router
from app.income.router import router as income_router
from app.reports.router import router as reports_router
from app.salary.router import router as salary_router
from app.savings.router import router as savings_router
from app.transactions.router import router as transactions_router
from app.users.router import router as users_router

configure_logging()
settings = get_settings()

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Sutura API",
    description="Personal finance and salary distribution backend.",
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get(f"{API_PREFIX}/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


routers = [
    auth_router,
    users_router,
    financial_periods_router,
    salary_router,
    allowances_router,
    income_router,
    expenses_router,
    distribution_router,
    distributions_router,
    savings_router,
    banks_router,
    transactions_router,
    reports_router,
    analytics_router,
    attachments_router,
    audit_router,
]

for r in routers:
    app.include_router(r, prefix=API_PREFIX)

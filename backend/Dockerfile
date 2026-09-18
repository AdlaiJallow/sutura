# Sutura backend — FastAPI + SQLAlchemy + Alembic
# Python 3.12: the current LTS-grade version with mature wheel coverage for every pinned
# dependency (psycopg[binary], pydantic-core, bcrypt, etc.). Do not bump to a brand-new
# CPython release until upstream wheels exist for the full dependency set (rule 13: no
# speculative complexity / avoid unverified toolchains in the image that serves production).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq is needed at runtime by psycopg; build-essential only for any sdist fallback.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install -r requirements/base.txt

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

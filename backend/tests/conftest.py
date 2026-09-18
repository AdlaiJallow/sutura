"""Shared pytest fixtures.

Uses a real Postgres database (settings.test_database_url) — never SQLite — because NUMERIC/DECIMAL
rounding and constraint behavior must match production exactly (CLAUDE.md, rule 4/9). Each test gets
its own outer transaction that is rolled back at teardown; service-layer `session.commit()` calls are
downgraded to a SAVEPOINT release via `join_transaction_mode="create_savepoint"` so no test's data
ever leaks into another test, and the DB is never left dirty after a run.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.base import Base
from app.common.config import get_settings
from app.common.database import get_db

# Import every model module so its tables register on Base.metadata before create_all runs.
# NOTE: these must be imported (and must NOT be plain `import app.xxx` statements) before
# `from app.main import app` below — a bare `import app.xxx.models` rebinds the local name
# `app` to the top-level package module, silently shadowing the FastAPI instance imported next.
from app.users import models as _users_models  # noqa: F401
from app.auth import models as _auth_models  # noqa: F401
from app.financial_periods import models as _financial_periods_models  # noqa: F401
from app.salary import models as _salary_models  # noqa: F401
from app.allowances import models as _allowances_models  # noqa: F401
from app.income import models as _income_models  # noqa: F401
from app.distribution import models as _distribution_models  # noqa: F401
from app.expenses import models as _expenses_models  # noqa: F401
from app.savings import models as _savings_models  # noqa: F401
from app.banks import models as _banks_models  # noqa: F401
from app.transactions import models as _transactions_models  # noqa: F401
from app.attachments import models as _attachments_models  # noqa: F401
from app.audit import models as _audit_models  # noqa: F401
from app.main import app

settings = get_settings()


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.test_database_url, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    connection = db_engine.connect()
    trans = connection.begin()
    session_factory = sessionmaker(
        bind=connection, future=True, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, email: str, password: str = "correct-horse-1") -> str:
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test User"}
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers_factory(client: TestClient):
    """Returns a callable that registers+logs in a fresh unique user and returns auth headers."""

    def _make(prefix: str = "user") -> dict[str, str]:
        email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
        token = _register_and_login(client, email)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def auth_headers(auth_headers_factory) -> dict[str, str]:
    return auth_headers_factory("user")

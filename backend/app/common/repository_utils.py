"""Tiny shared repository helpers — count-for-pagination and the optimistic-locking update
primitive (D-018). Not a generic base-repository abstraction on purpose (rule 13: no
premature abstraction); each module's repository still writes its own explicit, readable
queries scoped by user_id (D-020)."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def count_query(db: Session, stmt: Select) -> int:
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()


def conditional_update(
    db: Session,
    model: type,
    *,
    record_id: uuid.UUID,
    user_id: uuid.UUID,
    expected_updated_at: datetime,
    values: dict[str, Any],
) -> int:
    """Atomically applies `values` to a single row iff it is owned by `user_id`, not
    soft-deleted, and its `updated_at` still matches `expected_updated_at` (D-018's
    optimistic-locking convention: the client sends back the `updated_at` it last read).

    The concurrency guard lives entirely inside this single UPDATE statement's WHERE clause,
    evaluated atomically by Postgres against the row's current committed state — there is no
    prior Python-side "fetch, compare, then write" step that could race with a concurrent
    writer (no TOCTOU gap). Returns the number of rows updated (0 or 1); 0 means either the
    record doesn't exist/isn't owned by this user, or `updated_at` no longer matches (a
    concurrent edit happened) — the caller distinguishes those cases by having already done an
    ownership-scoped read before calling this (404) vs. treating a 0-row result here as a
    stale write (409).
    """
    if not values:
        return 0
    stmt = (
        update(model)
        .where(
            model.id == record_id,
            model.user_id == user_id,
            model.updated_at == expected_updated_at,
            model.deleted_at.is_(None),
        )
        .values(**values)
    )
    result = db.execute(stmt)
    return result.rowcount

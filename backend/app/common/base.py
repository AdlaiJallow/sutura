"""Shared SQLAlchemy declarative base and reusable column mixins (D-015, D-016, D-019)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Column type aliases enforcing NUMERIC everywhere money/percentages appear (D-019).
Money = Numeric(14, 4)
Percentage = Numeric(5, 2)


class Base(DeclarativeBase):
    """Declarative base shared by every model in the app."""

    pass


class UUIDPKMixin:
    """UUIDv4 primary key, defense-in-depth alongside mandatory ownership filtering (D-015)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at/updated_at for tables that are mutated in place (not append-only).

    `updated_at`'s `onupdate` deliberately uses `clock_timestamp()`, not `now()`: Postgres's
    `now()`/`CURRENT_TIMESTAMP` is fixed to the *transaction's* start time (constant across every
    statement in that transaction), while `clock_timestamp()` returns the true wall-clock instant
    of each individual statement. D-018's optimistic-locking convention depends on `updated_at`
    actually advancing on every write the row participates in — with `now()`, two writes to the
    same row inside one transaction (e.g. create-then-update, which is exactly what happens
    inside this test suite's savepoint-per-test harness, and could happen in a single request
    handler) would otherwise produce an identical, indistinguishable `updated_at`, silently
    defeating the whole mechanism. This has no DDL/migration impact: `onupdate` is a
    SQLAlchemy-side directive for what expression to embed in future UPDATE statements, not a
    stored column default.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.clock_timestamp(),
        nullable=False,
    )


class CreatedAtOnlyMixin:
    """created_at only, for append-only tables (BankTransaction, AuditLog) — no updated_at (D-016)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Nullable deleted_at for soft-deletable financial event tables (D-016)."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

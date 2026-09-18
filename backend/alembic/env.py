"""Alembic environment — wired to app.common.base.Base's metadata (every model module is
imported below so it registers with that metadata before autogenerate runs) and to
app.common.config.Settings for the connection string (never a second hardcoded DB URL).
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.common.base import Base
from app.common.config import get_settings

# Import every model module so its tables register on Base.metadata. This is the single place
# that must be kept in sync with app/*/models.py (one import per module, not a wildcard, so a
# missing import is obvious in review).
import app.users.models  # noqa: F401
import app.auth.models  # noqa: F401
import app.financial_periods.models  # noqa: F401
import app.salary.models  # noqa: F401
import app.allowances.models  # noqa: F401
import app.income.models  # noqa: F401
import app.distribution.models  # noqa: F401
import app.expenses.models  # noqa: F401
import app.savings.models  # noqa: F401
import app.banks.models  # noqa: F401
import app.transactions.models  # noqa: F401
import app.attachments.models  # noqa: F401
import app.audit.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a real DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Alembic async-aware environment.

Usage:
  alembic revision --autogenerate -m "describe your change"
  alembic upgrade head
  alembic downgrade -1
  alembic history
"""
import asyncio
import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# ── Path bootstrap ────────────────────────────────────────────────────────────
# Make "api/" importable so `from core.xxx import yyy` works inside migrations.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import Base + every model module so metadata is fully populated ───────────
from core.database import Base  # noqa: E402
from core.config import settings as app_settings  # noqa: E402

import apps.auth.models      # noqa: F401, E402
import apps.blog.models      # noqa: F401, E402
import apps.seo.models       # noqa: F401, E402
import apps.settings.models  # noqa: F401, E402

target_metadata = Base.metadata


# ── DB URL helper ─────────────────────────────────────────────────────────────
def _get_url() -> str:
    url = app_settings.DATABASE_URL or f"sqlite+aiosqlite:///{app_settings.DB_PATH}"
    # Normalise to async driver variants expected by SQLAlchemy
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+aiomysql://", 1)
    return url


# ── Offline mode (generates SQL without connecting) ──────────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to the real DB) ─────────────────────────────────────
def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

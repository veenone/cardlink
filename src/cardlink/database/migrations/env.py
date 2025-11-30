"""Alembic environment configuration for GP OTA Tester.

This module configures the Alembic migration environment,
setting up the database connection and model metadata.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add src to path for model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from cardlink.database.config import DatabaseConfig
from cardlink.database.models import Base

# Alembic Config object
config = context.config

# Configure logging from alembic.ini if available
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or config.

    Priority:
    1. DATABASE_URL environment variable
    2. sqlalchemy.url from alembic.ini
    3. Default SQLite database

    Returns:
        Database connection URL.
    """
    # Check environment variable first
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Check alembic.ini setting
    url = config.get_main_option("sqlalchemy.url")
    if url and url != "driver://user:pass@localhost/dbname":
        return url

    # Use default from DatabaseConfig
    db_config = DatabaseConfig()
    return db_config.url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Get configuration
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    # Determine pool class based on backend
    url = configuration["sqlalchemy.url"]
    if url.startswith("sqlite"):
        poolclass = pool.NullPool
    else:
        poolclass = pool.QueuePool

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=poolclass,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Render as batch for SQLite ALTER TABLE support
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

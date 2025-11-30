"""Migration utilities for GP OTA Tester database.

This module provides programmatic access to Alembic migrations,
allowing migrations to be run from code or CLI.

Example:
    >>> from cardlink.database.migrate import run_migrations
    >>> run_migrations("head")
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to migrations directory
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_alembic_config(database_url: Optional[str] = None) -> "AlembicConfig":
    """Get Alembic configuration.

    Args:
        database_url: Database URL to use. If None, uses default.

    Returns:
        Alembic Config object.
    """
    from alembic.config import Config

    # Find alembic.ini
    alembic_ini = Path(__file__).parent.parent.parent.parent.parent / "alembic.ini"

    if not alembic_ini.exists():
        # Create minimal config programmatically
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
    else:
        config = Config(str(alembic_ini))

    # Override URL if provided
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)

    return config


def run_migrations(
    revision: str = "head",
    database_url: Optional[str] = None,
) -> None:
    """Run database migrations.

    Args:
        revision: Target revision (default: "head" for latest).
        database_url: Database URL to use.

    Raises:
        Exception: If migration fails.
    """
    from alembic import command

    config = get_alembic_config(database_url)

    logger.info("Running migrations to revision: %s", revision)
    command.upgrade(config, revision)
    logger.info("Migrations completed successfully")


def downgrade(
    revision: str = "-1",
    database_url: Optional[str] = None,
) -> None:
    """Downgrade database migrations.

    Args:
        revision: Target revision (default: "-1" for one step back).
        database_url: Database URL to use.

    Raises:
        Exception: If downgrade fails.
    """
    from alembic import command

    config = get_alembic_config(database_url)

    logger.info("Downgrading to revision: %s", revision)
    command.downgrade(config, revision)
    logger.info("Downgrade completed successfully")


def get_current_revision(database_url: Optional[str] = None) -> Optional[str]:
    """Get current database revision.

    Args:
        database_url: Database URL to use.

    Returns:
        Current revision string, or None if not initialized.
    """
    from alembic import command
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    if database_url is None:
        from cardlink.database.config import DatabaseConfig

        database_url = DatabaseConfig().url

    engine = create_engine(database_url)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        return context.get_current_revision()


def get_pending_revisions(database_url: Optional[str] = None) -> list:
    """Get list of pending (unapplied) revisions.

    Args:
        database_url: Database URL to use.

    Returns:
        List of pending revision IDs.
    """
    from alembic.script import ScriptDirectory

    config = get_alembic_config(database_url)
    script = ScriptDirectory.from_config(config)

    current = get_current_revision(database_url)
    head = script.get_current_head()

    if current == head:
        return []

    # Get all revisions between current and head
    pending = []
    for rev in script.iterate_revisions(head, current):
        if rev.revision != current:
            pending.append(rev.revision)

    return list(reversed(pending))


def create_revision(
    message: str,
    autogenerate: bool = True,
    database_url: Optional[str] = None,
) -> str:
    """Create a new migration revision.

    Args:
        message: Revision message.
        autogenerate: Whether to autogenerate from model changes.
        database_url: Database URL to use.

    Returns:
        New revision ID.
    """
    from alembic import command

    config = get_alembic_config(database_url)

    logger.info("Creating new revision: %s", message)
    script = command.revision(
        config,
        message=message,
        autogenerate=autogenerate,
    )
    logger.info("Created revision: %s", script.revision)
    return script.revision


def stamp(
    revision: str = "head",
    database_url: Optional[str] = None,
) -> None:
    """Stamp the database with a revision without running migrations.

    Useful for marking an existing database as being at a specific
    revision without actually running the migration scripts.

    Args:
        revision: Revision to stamp.
        database_url: Database URL to use.
    """
    from alembic import command

    config = get_alembic_config(database_url)

    logger.info("Stamping database with revision: %s", revision)
    command.stamp(config, revision)
    logger.info("Database stamped successfully")


def get_migration_history(database_url: Optional[str] = None) -> list:
    """Get migration history.

    Args:
        database_url: Database URL to use.

    Returns:
        List of revision dictionaries with revision, description, etc.
    """
    from alembic.script import ScriptDirectory

    config = get_alembic_config(database_url)
    script = ScriptDirectory.from_config(config)

    current = get_current_revision(database_url)

    history = []
    for rev in script.walk_revisions():
        history.append({
            "revision": rev.revision,
            "down_revision": rev.down_revision,
            "description": rev.doc,
            "is_current": rev.revision == current,
        })

    return list(reversed(history))

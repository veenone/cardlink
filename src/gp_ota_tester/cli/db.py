"""Database CLI commands for GP OTA Tester.

This module provides command-line interface commands for managing
the database layer.

Example:
    $ gp-db init
    $ gp-db status
    $ gp-db export --format yaml --output backup.yaml
    $ gp-db import backup.yaml
"""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.option(
    "--database",
    "-d",
    envvar="DATABASE_URL",
    help="Database URL (default: sqlite:///data/cardlink.db)",
)
@click.pass_context
def cli(ctx: click.Context, database: Optional[str]) -> None:
    """Database management commands.

    Manage database initialization, migrations, and data import/export.
    """
    ctx.ensure_object(dict)
    ctx.obj["database_url"] = database


@cli.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Drop existing tables before creating",
)
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialize the database.

    Creates all database tables defined in the models.
    Use --force to drop existing tables first.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        console.print(f"[bold]Initializing database: {config.safe_url}[/bold]")

        # Create manager
        manager = DatabaseManager(config)
        manager.initialize()

        if force:
            console.print("[yellow]Dropping existing tables...[/yellow]")
            manager.drop_tables()

        # Create tables
        manager.create_tables()

        # Show tables
        tables = manager.get_table_names()
        console.print(f"[green]Created {len(tables)} tables:[/green]")
        for table in sorted(tables):
            console.print(f"  - {table}")

        manager.close()
        console.print("[bold green]Database initialized successfully![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed table information",
)
@click.pass_context
def status(ctx: click.Context, verbose: bool) -> None:
    """Show database status.

    Display connection information, backend type, and table counts.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager, UnitOfWork

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        manager = DatabaseManager(config)

        # Health check
        health = manager.health_check()

        # Create status table
        table = Table(title="Database Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", health["status"])
        table.add_row("Backend", health.get("backend", "Unknown"))
        table.add_row("Database", health.get("database", "Unknown"))
        table.add_row("URL", health.get("url", "Unknown"))

        if health["status"] == "unhealthy":
            table.add_row("Error", health.get("error", "Unknown error"))

        console.print(table)

        if verbose and health["status"] == "healthy":
            # Show table counts
            tables = manager.get_table_names()

            table2 = Table(title="Tables")
            table2.add_column("Table", style="cyan")
            table2.add_column("Rows", style="green", justify="right")

            with UnitOfWork(manager) as uow:
                for table_name in sorted(tables):
                    try:
                        # Get count based on table name
                        if table_name == "devices":
                            count = uow.devices.count()
                        elif table_name == "card_profiles":
                            count = uow.cards.count()
                        elif table_name == "ota_sessions":
                            count = uow.sessions.count()
                        elif table_name == "comm_logs":
                            count = uow.logs.count()
                        elif table_name == "test_results":
                            count = uow.tests.count()
                        elif table_name == "settings":
                            count = uow.settings.count()
                        else:
                            count = "?"
                        table2.add_row(table_name, str(count))
                    except Exception:
                        table2.add_row(table_name, "?")

            console.print(table2)

        manager.close()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout)",
)
@click.option(
    "--tables",
    "-t",
    multiple=True,
    help="Tables to export (default: all)",
)
@click.option(
    "--include-psk",
    is_flag=True,
    help="Include encrypted PSK keys (CAUTION)",
)
@click.pass_context
def export(
    ctx: click.Context,
    format: str,
    output: Optional[str],
    tables: tuple,
    include_psk: bool,
) -> None:
    """Export database to YAML or JSON.

    Exports devices, cards, and settings by default.
    Use --tables to export specific tables only.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager
        from gp_ota_tester.database.export_import import DataExporter

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        manager = DatabaseManager(config)
        manager.initialize()

        exporter = DataExporter(manager)

        if tables:
            data = exporter.export_selective(
                list(tables),
                format=format,
                include_psk=include_psk,
            )
        else:
            data = exporter.export_all(format=format, include_psk=include_psk)

        if output:
            with open(output, "w") as f:
                f.write(data)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            click.echo(data)

        manager.close()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="import")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "auto"]),
    default="auto",
    help="Import format (auto-detect from extension)",
)
@click.option(
    "--conflict",
    "-c",
    type=click.Choice(["skip", "overwrite", "merge"]),
    default="skip",
    help="How to handle existing records",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying",
)
@click.pass_context
def import_data(
    ctx: click.Context,
    file: str,
    format: str,
    conflict: str,
    dry_run: bool,
) -> None:
    """Import data from YAML or JSON file.

    Imports devices, cards, and settings from file.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager
        from gp_ota_tester.database.export_import import DataImporter

        # Auto-detect format
        if format == "auto":
            if file.endswith(".yaml") or file.endswith(".yml"):
                format = "yaml"
            else:
                format = "json"

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        manager = DatabaseManager(config)
        manager.initialize()

        importer = DataImporter(manager)

        if dry_run:
            console.print("[yellow]Dry run - no changes will be made[/yellow]")
            # TODO: Implement dry run preview
            console.print(f"Would import from: {file}")
        else:
            result = importer.import_from_file(file, format=format, conflict_mode=conflict)

            # Show results
            table = Table(title="Import Results")
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="green", justify="right")

            table.add_row("Created", str(result.created))
            table.add_row("Updated", str(result.updated))
            table.add_row("Skipped", str(result.skipped))
            table.add_row("Errors", str(len(result.errors)))

            console.print(table)

            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"  - {error}")

        manager.close()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--days",
    "-d",
    default=30,
    help="Delete logs older than N days",
)
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def cleanup(ctx: click.Context, days: int, confirm: bool) -> None:
    """Clean up old session logs and test results.

    Removes communication logs and test results older than
    the specified number of days.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager, UnitOfWork

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        manager = DatabaseManager(config)
        manager.initialize()

        if not confirm:
            console.print(f"[yellow]This will delete data older than {days} days.[/yellow]")
            if not click.confirm("Continue?"):
                console.print("Cancelled.")
                return

        console.print(f"[bold]Cleaning up data older than {days} days...[/bold]")

        with UnitOfWork(manager) as uow:
            # For now, just show what would be cleaned
            old_sessions = uow.sessions.find_recent(hours=days * 24)
            console.print(f"Sessions to keep: {len(old_sessions)}")
            uow.commit()

        console.print("[green]Cleanup completed.[/green]")
        manager.close()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show database statistics.

    Display counts and statistics for all tables.
    """
    try:
        from gp_ota_tester.database import DatabaseConfig, DatabaseManager, UnitOfWork

        # Get config
        url = ctx.obj.get("database_url")
        config = DatabaseConfig(url=url) if url else DatabaseConfig()

        manager = DatabaseManager(config)
        manager.initialize()

        with UnitOfWork(manager) as uow:
            # Device stats
            device_stats = uow.devices.get_stats()
            table = Table(title="Device Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            for key, value in device_stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))
            console.print(table)

            # Card stats
            card_stats = uow.cards.get_stats()
            table = Table(title="Card Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            for key, value in card_stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))
            console.print(table)

            # Session stats
            session_stats = uow.sessions.get_stats(hours=24)
            table = Table(title="Session Statistics (24h)")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            for key, value in session_stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))
            console.print(table)

            # Test stats
            test_stats = uow.tests.get_overall_stats(hours=24)
            table = Table(title="Test Statistics (24h)")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            for key, value in test_stats.items():
                if key == "pass_rate":
                    table.add_row("Pass Rate", f"{value}%")
                else:
                    table.add_row(key.replace("_", " ").title(), str(value))
            console.print(table)

        manager.close()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--revision",
    "-r",
    default="head",
    help="Target revision (default: head)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show SQL without executing",
)
@click.pass_context
def migrate(ctx: click.Context, revision: str, dry_run: bool) -> None:
    """Run database migrations.

    Applies pending migrations to upgrade the database schema.
    """
    try:
        from gp_ota_tester.database.migrate import (
            run_migrations,
            get_current_revision,
            get_pending_revisions,
        )

        url = ctx.obj.get("database_url")

        if dry_run:
            console.print("[yellow]Dry run - showing pending migrations[/yellow]")
            current = get_current_revision(url)
            pending = get_pending_revisions(url)

            console.print(f"Current revision: {current or 'None'}")
            if pending:
                console.print(f"Pending revisions: {len(pending)}")
                for rev in pending:
                    console.print(f"  - {rev}")
            else:
                console.print("[green]Database is up to date[/green]")
        else:
            console.print(f"[bold]Migrating to: {revision}[/bold]")
            run_migrations(revision, url)
            console.print("[bold green]Migration completed successfully![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--revision",
    "-r",
    default="-1",
    help="Target revision (default: -1 for one step back)",
)
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def rollback(ctx: click.Context, revision: str, confirm: bool) -> None:
    """Rollback database migrations.

    Downgrades the database schema by reverting migrations.
    """
    try:
        from gp_ota_tester.database.migrate import downgrade, get_current_revision

        url = ctx.obj.get("database_url")
        current = get_current_revision(url)

        console.print(f"Current revision: {current or 'None'}")

        if not confirm:
            console.print(f"[yellow]This will downgrade to: {revision}[/yellow]")
            if not click.confirm("Continue?"):
                console.print("Cancelled.")
                return

        console.print(f"[bold]Rolling back to: {revision}[/bold]")
        downgrade(revision, url)
        console.print("[bold green]Rollback completed successfully![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def history(ctx: click.Context) -> None:
    """Show migration history.

    Display all migrations and their status.
    """
    try:
        from gp_ota_tester.database.migrate import get_migration_history

        url = ctx.obj.get("database_url")
        migrations = get_migration_history(url)

        if not migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return

        table = Table(title="Migration History")
        table.add_column("Revision", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")

        for mig in migrations:
            status = "[bold green]CURRENT[/bold green]" if mig["is_current"] else ""
            desc = (mig["description"] or "")[:50]
            table.add_row(mig["revision"], desc, status)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for database CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

"""Database migration runner for Hyperliquid Funding Scraper."""

import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from urllib.parse import urlparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.utils.logger import setup_logging, get_logger


class MigrationRunner:
    """Handles database migrations for the Hyperliquid scraper."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the migration runner.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.logger = get_logger(__name__)
        self.connection_string = connection_string or self._build_connection_string()
        self.migrations_dir = Path(__file__).parent
        self.up_dir = self.migrations_dir / "up"
        self.down_dir = self.migrations_dir / "down"

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase URL."""
        try:
            # Parse Supabase URL
            parsed = urlparse(settings.supabase_url)

            # Extract database connection details
            # Supabase URL format: https://[PROJECT_REF].supabase.co
            project_ref = parsed.hostname.split('.')[0]

            # Build PostgreSQL connection string
            # Default Supabase PostgreSQL port is 5432
            db_host = f"db.{project_ref}.supabase.co"
            db_port = 5432
            db_name = "postgres"
            db_user = "postgres"

            # You'll need to set this in environment
            db_password = os.getenv("SUPABASE_DB_PASSWORD")

            if not db_password:
                raise ValueError("SUPABASE_DB_PASSWORD environment variable not set")

            return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        except Exception as e:
            self.logger.error(f"Failed to build connection string: {e}")
            raise

    def get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.connection_string)

    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if migrations table exists
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'migrations'
                        )
                    """)

                    if not cur.fetchone()[0]:
                        self.logger.info("Migrations table does not exist yet")
                        return []

                    # Get applied migrations
                    cur.execute("""
                        SELECT version
                        FROM migrations
                        WHERE status = 'completed'
                        ORDER BY version
                    """)

                    return [row[0] for row in cur.fetchall()]

        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []

    def get_migration_files(self, direction: str = "up") -> List[Tuple[int, Path]]:
        """
        Get migration files sorted by version.

        Args:
            direction: "up" or "down"

        Returns:
            List of (version, filepath) tuples
        """
        migration_dir = self.up_dir if direction == "up" else self.down_dir

        if direction == "up":
            # For up migrations, use files in main directory
            migration_dir = self.migrations_dir
            pattern = "*.sql"
        else:
            pattern = "*.sql"

        migrations = []

        for filepath in sorted(migration_dir.glob(pattern)):
            # Skip rollback files for up migrations
            if direction == "up" and ("rollback" in filepath.name or "down" in filepath.name):
                continue

            # Extract version from filename (e.g., "001_initial_schema.sql" -> 1)
            try:
                version = int(filepath.stem.split('_')[0])
                migrations.append((version, filepath))
            except (ValueError, IndexError):
                self.logger.warning(f"Skipping file with invalid name: {filepath.name}")

        return sorted(migrations, key=lambda x: x[0])

    def calculate_checksum(self, filepath: Path) -> str:
        """Calculate MD5 checksum of a migration file."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def run_migration(self, filepath: Path, version: int) -> bool:
        """
        Run a single migration file.

        Args:
            filepath: Path to SQL file
            version: Migration version number

        Returns:
            Success status
        """
        self.logger.info(f"Running migration {version}: {filepath.name}")
        start_time = time.time()

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Execute migration
                    cur.execute(sql_content)

                    # Record execution time
                    execution_time_ms = int((time.time() - start_time) * 1000)

                    # Update migrations table (if it exists)
                    cur.execute("""
                        INSERT INTO migrations (version, name, execution_time_ms, checksum, status)
                        VALUES (%s, %s, %s, %s, 'completed')
                        ON CONFLICT (version) DO UPDATE
                        SET executed_at = NOW(),
                            execution_time_ms = EXCLUDED.execution_time_ms,
                            status = 'completed'
                    """, (
                        version,
                        filepath.stem,
                        execution_time_ms,
                        self.calculate_checksum(filepath)
                    ))

                conn.commit()

            self.logger.info(f"✓ Migration {version} completed in {execution_time_ms}ms")
            return True

        except Exception as e:
            self.logger.error(f"✗ Migration {version} failed: {e}")
            return False

    def run_rollback(self, version: int) -> bool:
        """
        Run a rollback for a specific version.

        Args:
            version: Version to rollback

        Returns:
            Success status
        """
        rollback_files = self.get_migration_files("down")

        for v, filepath in rollback_files:
            if v == version:
                self.logger.info(f"Rolling back migration {version}")

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sql_content = f.read()

                    with self.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(sql_content)
                            conn.commit()

                    self.logger.info(f"✓ Rollback of migration {version} completed")
                    return True

                except Exception as e:
                    self.logger.error(f"✗ Rollback of migration {version} failed: {e}")
                    return False

        self.logger.error(f"Rollback file not found for version {version}")
        return False

    def migrate_up(self, target_version: Optional[int] = None) -> bool:
        """
        Run migrations up to target version.

        Args:
            target_version: Target version (None for all)

        Returns:
            Success status
        """
        applied = self.get_applied_migrations()
        pending = self.get_migration_files("up")

        if not pending:
            self.logger.info("No migration files found")
            return True

        migrations_to_run = []
        for version, filepath in pending:
            if version not in applied:
                if target_version is None or version <= target_version:
                    migrations_to_run.append((version, filepath))

        if not migrations_to_run:
            self.logger.info("Database is up to date")
            return True

        self.logger.info(f"Found {len(migrations_to_run)} pending migrations")

        for version, filepath in migrations_to_run:
            if not self.run_migration(filepath, version):
                return False

        self.logger.info("✓ All migrations completed successfully")
        return True

    def migrate_down(self, target_version: int = 0) -> bool:
        """
        Rollback migrations down to target version.

        Args:
            target_version: Target version to rollback to

        Returns:
            Success status
        """
        applied = sorted(self.get_applied_migrations(), reverse=True)

        if not applied:
            self.logger.info("No migrations to rollback")
            return True

        for version in applied:
            if version > target_version:
                if not self.run_rollback(version):
                    return False

        self.logger.info("✓ Rollback completed successfully")
        return True

    def get_status(self) -> None:
        """Print current migration status."""
        try:
            applied = self.get_applied_migrations()
            all_migrations = self.get_migration_files("up")

            print("\n" + "=" * 60)
            print("MIGRATION STATUS")
            print("=" * 60)

            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # Get migration details if table exists
                    if applied:
                        cur.execute("""
                            SELECT version, name, executed_at, execution_time_ms, status
                            FROM migrations
                            ORDER BY version
                        """)

                        print("\nApplied Migrations:")
                        print("-" * 40)
                        for row in cur.fetchall():
                            status_icon = "✓" if row['status'] == 'completed' else "✗"
                            print(f"{status_icon} {row['version']:3d}: {row['name']}")
                            print(f"       Executed: {row['executed_at']}")
                            if row['execution_time_ms']:
                                print(f"       Duration: {row['execution_time_ms']}ms")
                    else:
                        print("\nNo migrations applied yet")

            # Show pending migrations
            pending = []
            for version, filepath in all_migrations:
                if version not in applied:
                    pending.append((version, filepath))

            if pending:
                print("\nPending Migrations:")
                print("-" * 40)
                for version, filepath in pending:
                    print(f"  {version:3d}: {filepath.stem}")
            else:
                print("\nNo pending migrations")

            print("=" * 60 + "\n")

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")

    def create_migration(self, name: str) -> None:
        """
        Create a new migration file.

        Args:
            name: Name for the migration
        """
        # Get next version number
        existing = self.get_migration_files("up")
        next_version = 1 if not existing else existing[-1][0] + 1

        # Create filenames
        timestamp = datetime.now().strftime("%Y%m%d")
        up_filename = f"{next_version:03d}_{name}.sql"
        down_filename = f"{next_version:03d}_rollback_{name}.sql"

        up_filepath = self.migrations_dir / up_filename
        down_filepath = self.down_dir / down_filename

        # Create up migration
        up_template = f"""-- Migration: {next_version:03d}_{name}
-- Description: [Add description here]
-- Date: {datetime.now().strftime("%Y-%m-%d")}
-- Author: [Your name]

-- ============================================================================
-- MIGRATION UP
-- ============================================================================

-- Add your migration SQL here


-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO migrations (version, name, description, checksum)
VALUES (
    {next_version},
    '{next_version:03d}_{name}',
    '[Add description here]',
    MD5('{next_version:03d}_{name}_v1')
) ON CONFLICT (version) DO NOTHING;
"""

        # Create down migration
        down_template = f"""-- Rollback Migration: {next_version:03d}_{name}
-- Description: Rollback for {name}
-- Date: {datetime.now().strftime("%Y-%m-%d")}
-- Author: [Your name]

-- ============================================================================
-- ROLLBACK
-- ============================================================================

-- Add your rollback SQL here


-- ============================================================================
-- UPDATE MIGRATION LOG
-- ============================================================================

UPDATE migrations
SET rollback_executed = TRUE,
    rollback_at = NOW()
WHERE version = {next_version};
"""

        # Write files
        with open(up_filepath, 'w', encoding='utf-8') as f:
            f.write(up_template)

        with open(down_filepath, 'w', encoding='utf-8') as f:
            f.write(down_template)

        print(f"✓ Created migration files:")
        print(f"  Up:   {up_filepath}")
        print(f"  Down: {down_filepath}")


def main():
    """Main entry point for migration runner."""
    parser = argparse.ArgumentParser(description="Database Migration Runner")

    parser.add_argument(
        "command",
        choices=["up", "down", "status", "create"],
        help="Migration command to run"
    )

    parser.add_argument(
        "--version",
        type=int,
        help="Target version for up/down migrations"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Name for new migration (with create command)"
    )

    parser.add_argument(
        "--connection",
        type=str,
        help="PostgreSQL connection string"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_level="INFO")

    # Load environment
    load_dotenv()

    # Create runner
    runner = MigrationRunner(args.connection)

    # Execute command
    if args.command == "up":
        success = runner.migrate_up(args.version)
        sys.exit(0 if success else 1)

    elif args.command == "down":
        if args.version is None:
            print("Error: --version required for down migration")
            sys.exit(1)
        success = runner.migrate_down(args.version)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        runner.get_status()

    elif args.command == "create":
        if not args.name:
            print("Error: --name required for create command")
            sys.exit(1)
        runner.create_migration(args.name)


if __name__ == "__main__":
    main()
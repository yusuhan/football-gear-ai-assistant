"""Safe reset utilities for restoring a clean local demo environment."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import Settings
from app.db.database import initialize_database


RESET_TABLES = (
    "channel_conversations",
    "tool_call_logs",
    "agent_events",
    "handoff_tickets",
    "messages",
    "conversations",
    "operations_sessions",
    "audit_logs",
    "operations_users",
)


@dataclass(frozen=True)
class DemoDataResetResult:
    """Summary returned after a demo database reset."""

    database_path: Path
    backup_path: Optional[Path]
    cleared_rows: dict[str, int]
    product_count: int
    operations_user_count: int


class DemoDataService:
    """Back up and restore the SQLite database to its seeded demo state."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database_path = settings.database_path.resolve()

    def reset(self, create_backup: bool = True) -> DemoDataResetResult:
        """Clear runtime records, then restore catalog data and bootstrap users."""

        self._initialize_at_resolved_path()
        backup_path = self._create_backup() if create_backup else None

        with sqlite3.connect(self.database_path) as connection:
            cleared_rows = {
                table: self._count_rows(connection, table)
                for table in RESET_TABLES
            }
            connection.execute("PRAGMA foreign_keys = OFF")
            for table in RESET_TABLES:
                connection.execute(f"DELETE FROM {table}")

        self._initialize_at_resolved_path()
        with sqlite3.connect(self.database_path) as connection:
            product_count = self._count_rows(connection, "products")
            operations_user_count = self._count_rows(connection, "operations_users")

        return DemoDataResetResult(
            database_path=self.database_path,
            backup_path=backup_path,
            cleared_rows=cleared_rows,
            product_count=product_count,
            operations_user_count=operations_user_count,
        )

    def _initialize_at_resolved_path(self) -> None:
        settings = self.settings.model_copy(update={"database_path": self.database_path})
        initialize_database(settings)

    def _create_backup(self) -> Path:
        backup_directory = self.database_path.parent / "backups"
        backup_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_directory / f"{self.database_path.stem}-{timestamp}.db"

        with sqlite3.connect(self.database_path) as source:
            with sqlite3.connect(backup_path) as target:
                source.backup(target)
        return backup_path

    @staticmethod
    def _count_rows(connection: sqlite3.Connection, table: str) -> int:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0

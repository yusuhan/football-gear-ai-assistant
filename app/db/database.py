"""SQLite bootstrap utilities.

The database is generated from JSON seed files so a fresh clone can run without
manual SQL setup. This keeps interview demos reproducible.
"""

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from app.core.config import Settings
from app.core.security import hash_password


def initialize_database(settings: Settings) -> None:
    """Create tables and seed demo data on application startup."""

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.database_path) as connection:
        _create_tables(connection)
        for table, path in [
            ("products", settings.products_path),
            ("inventory", settings.inventory_path),
            ("size_guide", settings.size_guide_path),
        ]:
            _replace_rows(connection, table, _read_json(path))
        _seed_operations_users(connection, settings)


def _create_tables(connection: sqlite3.Connection) -> None:
    """Create the small product, inventory and size guide schema."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL,
            surface TEXT NOT NULL,
            description TEXT NOT NULL,
            recommended_position TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory (
            product_id TEXT NOT NULL,
            size INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            PRIMARY KEY (product_id, size),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS size_guide (
            foot_length REAL PRIMARY KEY,
            recommended_size INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT,
            route TEXT,
            confidence REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS tool_call_logs (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        CREATE TABLE IF NOT EXISTS handoff_tickets (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            assigned_to TEXT,
            resolution_note TEXT,
            resolved_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS agent_events (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            message_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        CREATE TABLE IF NOT EXISTS channel_conversations (
            channel TEXT NOT NULL,
            external_conversation_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (channel, external_conversation_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS operations_users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS operations_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES operations_users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            actor_user_id TEXT,
            actor_username TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (actor_user_id) REFERENCES operations_users(id)
        );
        """
    )
    _ensure_columns(
        connection,
        "handoff_tickets",
        {
            "assigned_to": "TEXT",
            "resolution_note": "TEXT",
            "resolved_at": "TEXT",
        },
    )


def _seed_operations_users(connection: sqlite3.Connection, settings: Settings) -> None:
    """Create bootstrap accounts once without overwriting managed passwords."""

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    users = [
        ("ops_admin", settings.admin_username, settings.admin_password, "admin"),
        ("ops_support", settings.support_username, settings.support_password, "support"),
    ]
    for user_id, username, password, role in users:
        connection.execute(
            """
            INSERT OR IGNORE INTO operations_users (
                id, username, password_hash, role, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            [user_id, username, hash_password(password), role, now, now],
        )


def _read_json(path: Path) -> list[dict]:
    """Read a JSON seed file."""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _ensure_columns(connection: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    """Add missing columns for simple local schema migrations."""

    existing_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")


def _replace_rows(connection: sqlite3.Connection, table: str, rows: Iterable[dict]) -> None:
    """Replace all rows in a table with the supplied dictionaries."""

    row_list = list(rows)
    connection.execute(f"DELETE FROM {table}")
    if not row_list:
        return

    columns = list(row_list[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    connection.executemany(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        [[row[column] for column in columns] for row in row_list],
    )

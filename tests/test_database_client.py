"""Tests for the SQLite and PostgreSQL compatibility adapter."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.db.client import DatabaseConnection, connect_database, is_postgres


class DatabaseClientTest(unittest.TestCase):
    """Validate backend selection and shared query behavior."""

    def test_postgres_urls_are_detected(self) -> None:
        self.assertTrue(is_postgres("postgresql://user:secret@example.test/app"))
        self.assertTrue(is_postgres("postgres://user:secret@example.test/app"))
        self.assertFalse(is_postgres(Path("data/local.db")))

    def test_sqlite_adapter_returns_dictionary_compatible_rows(self) -> None:
        with TemporaryDirectory() as directory:
            with connect_database(Path(directory) / "adapter.db") as connection:
                connection.execute("CREATE TABLE sample (id TEXT PRIMARY KEY, value INTEGER)")
                connection.execute("INSERT INTO sample (id, value) VALUES (?, ?)", ["one", 1])
                row = connection.execute("SELECT id, value FROM sample WHERE id = ?", ["one"]).fetchone()

            self.assertEqual(dict(row), {"id": "one", "value": 1})

    def test_postgres_placeholders_are_adapted(self) -> None:
        connection = DatabaseConnection.__new__(DatabaseConnection)
        connection.postgres = True

        self.assertEqual(
            connection._adapt_query("SELECT * FROM products WHERE id = ? AND price <= ?"),
            "SELECT * FROM products WHERE id = %s AND price <= %s",
        )


if __name__ == "__main__":
    unittest.main()

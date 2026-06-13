"""Tests for safely restoring the SQLite demo environment."""

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import Settings
from app.db.database import initialize_database
from app.services.demo_data_service import DemoDataService


class DemoDataServiceTest(unittest.TestCase):
    """Verify backups and deterministic seed restoration."""

    def test_reset_backs_up_and_clears_runtime_data(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "demo.db"
            settings = Settings(database_url="", database_path=database_path)
            initialize_database(settings)

            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO conversations (id, user_id, channel, status, created_at, updated_at)
                    VALUES ('conv_test', 'user_test', 'web', 'active', 'now', 'now')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO operations_users (
                        id, username, password_hash, role, is_active, created_at, updated_at
                    ) VALUES ('ops_test', 'temporary', 'hash', 'support', 1, 'now', 'now')
                    """
                )

            result = DemoDataService(settings).reset()

            self.assertIsNotNone(result.backup_path)
            self.assertTrue(result.backup_path.exists())
            self.assertEqual(result.cleared_rows["conversations"], 1)
            self.assertEqual(result.cleared_rows["operations_users"], 3)
            self.assertEqual(result.product_count, 16)
            self.assertEqual(result.operations_user_count, 2)

            with sqlite3.connect(database_path) as connection:
                conversation_count = connection.execute(
                    "SELECT COUNT(*) FROM conversations"
                ).fetchone()[0]
                usernames = {
                    row[0]
                    for row in connection.execute("SELECT username FROM operations_users")
                }

            self.assertEqual(conversation_count, 0)
            self.assertEqual(usernames, {settings.admin_username, settings.support_username})


if __name__ == "__main__":
    unittest.main()

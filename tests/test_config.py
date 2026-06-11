"""Tests for environment-dependent application configuration."""

import unittest

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    """Ensure local convenience does not weaken production CORS rules."""

    def test_local_cors_includes_both_localhost_forms(self) -> None:
        settings = Settings(app_env="local", backend_cors_origin="http://localhost:3000")

        self.assertEqual(
            settings.cors_origins(),
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )

    def test_production_cors_supports_multiple_explicit_origins(self) -> None:
        settings = Settings(
            app_env="production",
            backend_cors_origin="https://app.example.com/, https://admin.example.com",
        )

        self.assertEqual(
            settings.cors_origins(),
            ["https://app.example.com", "https://admin.example.com"],
        )


if __name__ == "__main__":
    unittest.main()

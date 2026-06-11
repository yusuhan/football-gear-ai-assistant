"""Application settings for the Football Gear AI Assistant."""

import os
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_ADMIN_PASSWORD = "local-admin-change-me"
DEFAULT_SUPPORT_PASSWORD = "local-support-change-me"


class Settings(BaseModel):
    """Runtime configuration for the API service."""

    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    database_path: Path = Field(default_factory=lambda: Path(os.getenv("DATABASE_PATH", "data/football_gear.db")))
    products_path: Path = Field(default_factory=lambda: Path(os.getenv("PRODUCTS_PATH", "data/products.json")))
    inventory_path: Path = Field(default_factory=lambda: Path(os.getenv("INVENTORY_PATH", "data/inventory.json")))
    size_guide_path: Path = Field(default_factory=lambda: Path(os.getenv("SIZE_GUIDE_PATH", "data/size_guide.json")))
    faq_path: Path = Field(default_factory=lambda: Path(os.getenv("FAQ_PATH", "data/faq.json")))
    use_openai: bool = Field(default_factory=lambda: os.getenv("USE_OPENAI", "false").lower() == "true")
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    backend_cors_origin: str = Field(
        default_factory=lambda: os.getenv("BACKEND_CORS_ORIGIN", "http://localhost:3000")
    )
    admin_username: str = Field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    admin_password: str = Field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD))
    support_username: str = Field(default_factory=lambda: os.getenv("SUPPORT_USERNAME", "support"))
    support_password: str = Field(default_factory=lambda: os.getenv("SUPPORT_PASSWORD", DEFAULT_SUPPORT_PASSWORD))
    operations_session_hours: int = Field(
        default_factory=lambda: int(os.getenv("OPERATIONS_SESSION_HOURS", "8"))
    )
    min_rag_score: float = Field(default_factory=lambda: float(os.getenv("MIN_RAG_SCORE", "0.12")))

    def cors_origins(self) -> list[str]:
        """Return configured origins, adding local development URLs only locally."""

        origins = [origin.strip().rstrip("/") for origin in self.backend_cors_origin.split(",") if origin.strip()]
        if self.app_env == "local":
            origins.extend(["http://127.0.0.1:3000", "http://localhost:3000"])
        return list(dict.fromkeys(origins))

"""
LogSense AI – Configuration
============================
Single source of truth for all settings.
"""

import logging
import sys
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite
    sqlite_db_path: str = "/app/data/logsense.db"

    # AI Provider: "perplexity" or "openrouter"
    ai_provider: str = "perplexity"

    # Perplexity AI (Primary)
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar"

    # OpenRouter (Fallback)
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-r1-0528:free"

    # CORS – comma-separated origins, e.g. "http://localhost:3000,https://myapp.com"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    # Processing
    batch_window_seconds: int = 3
    max_batch_size: int = 10

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Host machine IP (for QR codes – must be reachable from phone)
    host_ip: str = ""

    # Docker watcher
    enable_docker_watcher: bool = True

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_api_key(cls, v: str) -> str:
        if not v:
            print("WARNING: OPENROUTER_API_KEY is empty", file=sys.stderr)
        return v

    @field_validator("perplexity_api_key")
    @classmethod
    def validate_perplexity_api_key(cls, v: str) -> str:
        if not v:
            print("WARNING: PERPLEXITY_API_KEY is empty", file=sys.stderr)
        return v

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

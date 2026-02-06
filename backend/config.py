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
    # Firebase
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = ""  # MUST be set via env var FIREBASE_PROJECT_ID

    # OpenRouter AI (DeepSeek R1)
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

    @field_validator("firebase_project_id")
    @classmethod
    def validate_firebase_project_id(cls, v: str) -> str:
        if not v:
            print("FATAL: FIREBASE_PROJECT_ID environment variable must be set!", file=sys.stderr)
            sys.exit(1)
        return v

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_api_key(cls, v: str) -> str:
        if not v:
            print("WARNING: OPENROUTER_API_KEY is empty – AI analysis will NOT work!", file=sys.stderr)
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

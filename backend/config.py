"""
LogSense AI – Configuration
============================
Single source of truth for all settings.
"""

import logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Firebase
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = "montgomery-415113"

    # OpenRouter AI (DeepSeek R1)
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-r1-0528:free"

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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

"""
LogSense AI – AI Analysis Service
===================================
⚠️  DEPRECATED: This micro-service is no longer used.
All functionality is now handled by the single backend monolith (../backend/).
The backend uses OpenRouter (DeepSeek) for AI analysis.

This file is kept for reference only.
"""

import asyncio
import json
import logging
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from pydantic_settings import BaseSettings

from models import AnalysisResult

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = "montgomery-415113"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-r1-0528:free"
    batch_window_seconds: int = 5
    max_batch_size: int = 10
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ai-analysis")

logger.warning(
    "⚠️  This service is DEPRECATED. "
    "All AI analysis is handled by the main backend service. "
    "Use 'docker compose up backend' instead."
)


class AIAnalysisService:
    """Main service orchestrator. DEPRECATED - use backend instead."""

    def __init__(self):
        self.db = None
        self.running = False

    async def setup(self):
        logger.info("Initializing Firebase...")
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.firebase_project_id,
            })
            logger.info("✓ Firebase Firestore connected")
        except Exception as e:
            logger.error(f"✗ Firebase initialization failed: {e}")
            raise

        logger.info("✓ AI Analysis Service ready (DEPRECATED)")

    async def run(self):
        """Main loop - DEPRECATED"""
        self.running = True
        logger.warning("This service is deprecated. Use the main backend instead.")

        while self.running:
            await asyncio.sleep(settings.batch_window_seconds)

    async def shutdown(self):
        self.running = False
        logger.info("AI Analysis Service stopped")


async def main():
    service = AIAnalysisService()
    await service.setup()

    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())

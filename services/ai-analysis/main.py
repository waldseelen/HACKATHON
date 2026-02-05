"""
LogSense AI – AI Analysis Service (Firebase Edition)
=====================================================
Watches Firestore logs collection → analyzes with Gemini AI → stores alerts
"""

import asyncio
import json
import logging
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from pydantic_settings import BaseSettings

from gemini_client import GeminiAnalyzer
from models import AnalysisResult

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = "montgomery-415113"
    gemini_api_key: str = ""
    batch_window_seconds: int = 5
    max_batch_size: int = 10
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ai-analysis")


class AIAnalysisService:
    """Main service orchestrator."""

    def __init__(self):
        self.gemini = GeminiAnalyzer(api_key=settings.gemini_api_key)
        self.db: firestore.AsyncClient | None = None
        self.running = False

    async def setup(self):
        logger.info("Initializing Firebase...")
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.firebase_project_id,
            })
            self.db = firestore.AsyncClient()
            logger.info("✓ Firebase Firestore connected")
        except Exception as e:
            logger.error(f"✗ Firebase initialization failed: {e}")
            raise

        logger.info("✓ AI Analysis Service ready")

    async def run(self):
        """Main loop: poll Firestore for unprocessed logs"""
        self.running = True
        logger.info("Starting Firestore log watcher...")

        while self.running:
            try:
                # Query unprocessed logs
                logs_ref = (
                    self.db.collection('logs')
                    .where('processed', '==', False)
                    .limit(settings.max_batch_size)
                )

                docs = await logs_ref.get()

                if not docs:
                    await asyncio.sleep(settings.batch_window_seconds)
                    continue

                logger.info(f"Processing {len(docs)} logs...")

                # Batch logs for analysis
                log_entries = []
                log_ids = []

                for doc in docs:
                    data = doc.to_dict()
                    log_entries.append(data.get('raw_log', ''))
                    log_ids.append(doc.id)

                # Analyze with Gemini
                logs_text = "\n".join(log_entries)
                try:
                    result = await self.gemini.analyze(logs_text, len(log_entries))
                    await self._store_alert(result, log_ids)

                    # Mark logs as processed
                    for doc_id in log_ids:
                        await self.db.collection('logs').document(doc_id).update({'processed': True})

                    logger.info(f"✓ Analyzed batch: {result.category} ({result.severity})")

                except Exception as e:
                    logger.error(f"Analysis failed: {e}")
                    # Use fallback
                    result = self.gemini.fallback_analysis(logs_text)
                    await self._store_alert(result, log_ids)

            except asyncio.CancelledError:
                logger.info("AI Analysis Service stopping...")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

    async def _store_alert(self, result: AnalysisResult, log_ids: list):
        """Store alert in Firestore"""
        alert_doc = {
            "category": result.category,
            "severity": result.severity,
            "confidence": result.confidence,
            "summary": result.summary,
            "root_cause": result.root_cause,
            "solution": result.solution,
            "action_required": result.action_required,
            "log_ids": log_ids,
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        await self.db.collection('alerts').add(alert_doc)
        logger.info(f"Alert stored: {result.summary[:50]}...")

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

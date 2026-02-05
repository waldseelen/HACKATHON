"""
LogSense AI – AI Analysis Service
===================================
Consumes logs from RabbitMQ → deduplicates/batches →
analyzes with Gemini AI → stores alerts → publishes to alert queue.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

import aio_pika
import asyncpg
from pydantic_settings import BaseSettings

from gemini_client import GeminiAnalyzer
from deduplication import DeduplicationService
from models import AnalysisResult

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_user: str = "logsense"
    rabbitmq_password: str = "changeme"
    postgres_host: str = "postgres"
    postgres_db: str = "logsense"
    postgres_user: str = "logsense"
    postgres_password: str = "changeme"
    gemini_api_key: str = ""
    batch_window_seconds: int = 2
    max_batch_size: int = 50
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
        self.dedup = DeduplicationService(
            window_seconds=settings.batch_window_seconds,
            max_batch_size=settings.max_batch_size,
            on_flush=self._on_batch_ready,
        )
        self.db_pool: asyncpg.Pool | None = None
        self.rmq_connection: aio_pika.RobustConnection | None = None
        self.rmq_channel: aio_pika.Channel | None = None
        self.alert_exchange: aio_pika.Exchange | None = None

    # ── lifecycle ─────────────────────────────────────────

    async def setup(self):
        logger.info("Connecting to PostgreSQL…")
        self.db_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=3,
            max_size=15,
        )

        logger.info("Connecting to RabbitMQ…")
        self.rmq_connection = await aio_pika.connect_robust(
            f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
            f"@{settings.rabbitmq_host}/"
        )
        self.rmq_channel = await self.rmq_connection.channel()
        await self.rmq_channel.set_qos(prefetch_count=20)

        # Input: consume from logs.raw exchange
        exchange = await self.rmq_channel.declare_exchange(
            "logs.raw", aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self.rmq_channel.declare_queue(
            "logs.analysis", durable=True
        )
        await queue.bind(exchange, routing_key="log.#")

        # Output: publish analysed alerts
        self.alert_exchange = await self.rmq_channel.declare_exchange(
            "alerts.ready", aio_pika.ExchangeType.DIRECT, durable=True
        )

        # Start dedup flush loop
        await self.dedup.start()

        logger.info("✓ AI Analysis Service ready")
        return queue

    async def shutdown(self):
        await self.dedup.stop()
        if self.db_pool:
            await self.db_pool.close()
        if self.rmq_connection and not self.rmq_connection.is_closed:
            await self.rmq_connection.close()
        logger.info("AI Analysis Service stopped")

    # ── message handler ───────────────────────────────────

    async def on_message(self, message: aio_pika.IncomingMessage):
        """Handle an incoming log message from RabbitMQ."""
        async with message.process():
            try:
                log_data = json.loads(message.body.decode())
                await self.dedup.add(log_data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    # ── batch analysis ────────────────────────────────────

    async def _on_batch_ready(self, logs: List[Dict[str, Any]]):
        """Called by DeduplicationService when a batch is ready for analysis."""
        try:
            # Build combined log text for Gemini
            combined = "\n---\n".join(
                f"[{log.get('service', '?')}] [{log.get('severity', '?')}] {log.get('raw_log', '')}"
                for log in logs
            )

            # AI analysis
            try:
                result = await self.gemini.analyze(combined, count=len(logs))
            except Exception as e:
                logger.error(f"Gemini failed, using fallback: {e}")
                result = self.gemini.fallback_analysis(combined)

            # Persist alert to PostgreSQL
            log_ids = [log.get("log_id") for log in logs if log.get("log_id")]
            alert_id = await self._store_alert(result, log_ids)

            # Publish to alert queue for Alert Composer
            alert_payload = {
                "alert_id": str(alert_id),
                "service": logs[0].get("service", "unknown"),
                "category": result.category,
                "severity": result.severity,
                "confidence": result.confidence,
                "summary": result.summary,
                "root_cause": result.root_cause,
                "solution": result.solution,
                "action_required": result.action_required,
                "log_count": len(logs),
            }

            await self.alert_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(alert_payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key="alert.send",
            )
            logger.info(
                f"Alert {alert_id} → {result.category}/{result.severity} "
                f"(confidence={result.confidence:.0%}, logs={len(logs)})"
            )

        except Exception as e:
            logger.error(f"Batch analysis error: {e}", exc_info=True)

    async def _store_alert(self, result: AnalysisResult, log_ids: list) -> str:
        """Insert an alert record and return its UUID."""
        async with self.db_pool.acquire() as conn:
            alert_id = await conn.fetchval(
                """
                INSERT INTO alerts
                    (log_ids, category, severity, confidence,
                     summary, root_cause, solution, action_required)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                log_ids,
                result.category,
                result.severity,
                result.confidence,
                result.summary,
                result.root_cause,
                result.solution,
                result.action_required,
            )
        return alert_id

    # ── run ───────────────────────────────────────────────

    async def run(self):
        queue = await self.setup()
        await queue.consume(self.on_message)
        logger.info("Consuming from queue 'logs.analysis'…")

        try:
            await asyncio.Future()  # run forever
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()


# ── entrypoint ────────────────────────────────────────────

async def main():
    service = AIAnalysisService()
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")

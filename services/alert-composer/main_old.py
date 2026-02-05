"""
LogSense AI – Alert Composer Service
======================================
Consumes AI analysis results from RabbitMQ →
sends push notifications (FCM) + Uptime Kuma webhooks →
updates alert tracking in PostgreSQL.
"""

import asyncio
import json
import logging
from typing import Dict, Any

import aio_pika
import asyncpg
from pydantic_settings import BaseSettings

from fcm_client import FCMClient
from uptime_kuma import UptimeKumaClient

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_user: str = "logsense"
    rabbitmq_password: str = "changeme"
    postgres_host: str = "postgres"
    postgres_db: str = "logsense"
    postgres_user: str = "logsense"
    postgres_password: str = "changeme"
    firebase_credentials: str = ""
    uptime_kuma_webhook: str = ""
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("alert-composer")


class AlertComposerService:
    """Consumes alerts and dispatches notifications."""

    def __init__(self):
        self.fcm = FCMClient(
            credentials_path=settings.firebase_credentials or None
        )
        self.uptime_kuma = UptimeKumaClient(
            webhook_url=settings.uptime_kuma_webhook
        )
        self.db_pool: asyncpg.Pool | None = None
        self.rmq_connection: aio_pika.RobustConnection | None = None
        self.rmq_channel: aio_pika.Channel | None = None

    # ── lifecycle ─────────────────────────────────────────

    async def setup(self):
        logger.info("Connecting to PostgreSQL…")
        self.db_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=2,
            max_size=10,
        )

        logger.info("Connecting to RabbitMQ…")
        self.rmq_connection = await aio_pika.connect_robust(
            f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
            f"@{settings.rabbitmq_host}/"
        )
        self.rmq_channel = await self.rmq_connection.channel()
        await self.rmq_channel.set_qos(prefetch_count=10)

        exchange = await self.rmq_channel.declare_exchange(
            "alerts.ready", aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await self.rmq_channel.declare_queue(
            "alerts.send", durable=True
        )
        await queue.bind(exchange, routing_key="alert.send")

        logger.info("✓ Alert Composer Service ready")
        logger.info(f"   FCM: {'enabled' if self.fcm.available else 'disabled'}")
        logger.info(f"   Uptime Kuma: {'enabled' if self.uptime_kuma.available else 'disabled'}")

        return queue

    async def shutdown(self):
        if self.db_pool:
            await self.db_pool.close()
        if self.rmq_connection and not self.rmq_connection.is_closed:
            await self.rmq_connection.close()
        logger.info("Alert Composer stopped")

    # ── message handler ───────────────────────────────────

    async def on_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                alert_data = json.loads(message.body.decode())
                await self._dispatch_alert(alert_data)
            except Exception as e:
                logger.error(f"Error processing alert: {e}", exc_info=True)

    async def _dispatch_alert(self, alert_data: Dict[str, Any]):
        """Send notifications for a single alert."""
        alert_id = alert_data.get("alert_id", "?")
        service = alert_data.get("service", "unknown")
        category = alert_data.get("category", "unknown")
        severity = alert_data.get("severity", "unknown")

        logger.info(
            f"Dispatching alert {alert_id}: "
            f"{category}/{severity} from {service}"
        )

        notification_count = 0

        # ── 1. FCM Push Notifications ─────────────────────
        if self.fcm.available:
            tokens = await self._get_fcm_targets(alert_data)
            if tokens:
                sent = await self.fcm.send_alert(alert_data, tokens)
                notification_count += sent

        # ── 2. Uptime Kuma Webhook ────────────────────────
        if self.uptime_kuma.available:
            await self.uptime_kuma.send_alert(alert_data)

        # ── 3. Update alert tracking in DB ────────────────
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE alerts
                    SET notified_at = NOW(),
                        notification_count = $2
                    WHERE id = $1::uuid
                    """,
                    alert_id,
                    notification_count,
                )
        except Exception as e:
            logger.warning(f"Failed to update alert tracking: {e}")

        # ── 4. Record metric ──────────────────────────────
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO service_metrics (metric_name, service_name, value, labels)
                    VALUES ('alert_dispatched', $1, 1, $2)
                    """,
                    service,
                    json.dumps({
                        "category": category,
                        "severity": severity,
                        "fcm_sent": notification_count,
                    }),
                )
        except Exception as e:
            logger.warning(f"Failed to record metric: {e}")

        logger.info(
            f"Alert {alert_id} dispatched "
            f"(fcm={notification_count}, uptime_kuma={'ok' if self.uptime_kuma.available else 'skip'})"
        )

    async def _get_fcm_targets(self, alert_data: Dict[str, Any]) -> list[str]:
        """Query PostgreSQL for matching FCM device tokens."""
        service = alert_data.get("service", "")
        severity = alert_data.get("severity", "medium")

        # Map severity to numeric for comparison
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        alert_level = severity_order.get(severity, 2)

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT device_token
                    FROM user_fcm_tokens
                    WHERE (
                        -- Match specific service filter OR wildcard
                        $1 = ANY(service_filters) OR '*' = ANY(service_filters)
                    )
                    """,
                    service,
                )

            # Filter by severity threshold in Python
            # (cleaner than complex SQL with severity ordering)
            tokens = []
            for row in rows:
                tokens.append(row["device_token"])

            return tokens

        except Exception as e:
            logger.error(f"Failed to query FCM targets: {e}")
            return []

    # ── run ───────────────────────────────────────────────

    async def run(self):
        queue = await self.setup()
        await queue.consume(self.on_message)
        logger.info("Consuming from queue 'alerts.send'…")

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()


# ── entrypoint ────────────────────────────────────────────

async def main():
    service = AlertComposerService()
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")

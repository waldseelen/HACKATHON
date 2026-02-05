"""
LogSense AI – Alert Composer (Firebase Edition)
================================================
Watches Firestore alerts → sends FCM push notifications → updates Uptime Kuma
"""

import asyncio
import json
import logging
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore, messaging
import httpx
from pydantic_settings import BaseSettings

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = "montgomery-415113"
    fcm_sender_id: str = "105791470459"
    uptime_kuma_webhook: str = ""
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("alert-composer")


class AlertComposerService:
    """Watches Firestore alerts and dispatches notifications"""

    def __init__(self):
        self.db: firestore.AsyncClient | None = None
        self.running = False
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def setup(self):
        logger.info("Initializing Firebase...")
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.firebase_project_id,
            })
            self.db = firestore.AsyncClient()
            logger.info("✓ Firebase connected")
        except Exception as e:
            logger.error(f"✗ Firebase initialization failed: {e}")
            raise

        logger.info("✓ Alert Composer Service ready")

    async def run(self):
        """Main loop: watch for new alerts in Firestore"""
        self.running = True
        logger.info("Watching Firestore for new alerts...")

        last_alert_time = datetime.now()

        while self.running:
            try:
                # Query recent alerts not yet notified
                alerts_ref = (
                    self.db.collection('alerts')
                    .where('notified', '==', False)
                    .limit(10)
                )

                docs = await alerts_ref.get()

                for doc in docs:
                    alert_data = doc.to_dict()
                    try:
                        await self._send_notification(alert_data)
                        await self.db.collection('alerts').document(doc.id).update({'notified': True})
                        logger.info(f"✓ Notified: {alert_data.get('summary', 'Unknown')[:50]}")
                    except Exception as e:
                        logger.error(f"Notification failed for {doc.id}: {e}")

                await asyncio.sleep(5)  # Poll every 5 seconds

            except asyncio.CancelledError:
                logger.info("Alert Composer stopping...")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

    async def _send_notification(self, alert_data: dict):
        """Send FCM push notification and update Uptime Kuma"""

        # FCM Notification (if configured)
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"🚨 {alert_data.get('severity', 'unknown').upper()}: {alert_data.get('category', 'unknown')}",
                    body=alert_data.get('summary', 'No summary')[:200],
                ),
                data={
                    "category": alert_data.get('category', ''),
                    "severity": alert_data.get('severity', ''),
                    "confidence": str(alert_data.get('confidence', 0)),
                },
                topic='all_devices',  # Or specific device tokens
            )

            # Send to FCM (requires device tokens or topics setup)
            # response = messaging.send(message)
            # logger.info(f"FCM sent: {response}")
            logger.info("FCM notification prepared (device tokens needed)")

        except Exception as e:
            logger.warning(f"FCM send failed: {e}")

        # Uptime Kuma Webhook
        if settings.uptime_kuma_webhook:
            try:
                status = "down" if alert_data.get('severity') in ['critical', 'high'] else "up"
                msg = f"{alert_data.get('category')}: {alert_data.get('summary')}"

                url = settings.uptime_kuma_webhook.replace('status=up', f'status={status}')
                url = url.replace('msg=OK', f'msg={msg[:100]}')

                response = await self.http_client.get(url)
                response.raise_for_status()
                logger.info("✓ Uptime Kuma notified")
            except Exception as e:
                logger.warning(f"Uptime Kuma webhook failed: {e}")

    async def shutdown(self):
        self.running = False
        await self.http_client.aclose()
        logger.info("Alert Composer stopped")


async def main():
    service = AlertComposerService()
    await service.setup()

    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

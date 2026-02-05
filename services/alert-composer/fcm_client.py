"""
Firebase Cloud Messaging (FCM) client – sends push notifications.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("alert-composer.fcm")

# Firebase is optional (may not have credentials in dev)
_firebase_available = False
try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    _firebase_available = True
except ImportError:
    logger.warning("firebase-admin not installed — FCM disabled")


class FCMClient:
    """Send push notifications via Firebase Cloud Messaging."""

    def __init__(self, credentials_path: Optional[str] = None):
        self._initialized = False

        if not _firebase_available:
            logger.warning("FCM client: firebase-admin not available")
            return

        if not credentials_path:
            logger.warning("FCM client: no credentials path — disabled")
            return

        try:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
            self._initialized = True
            logger.info("FCM client initialized")
        except Exception as e:
            logger.warning(f"FCM init failed (notifications disabled): {e}")

    @property
    def available(self) -> bool:
        return self._initialized

    async def send_alert(
        self,
        alert_data: Dict[str, Any],
        device_tokens: List[str],
    ) -> int:
        """Send a multicast push notification. Returns count of successes."""
        if not self._initialized or not device_tokens:
            return 0

        # Severity → emoji
        emoji = {
            "critical": "🔥",
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️",
        }.get(alert_data.get("severity", ""), "📢")

        title = (
            f"{emoji} {alert_data['category'].upper()} — "
            f"{alert_data.get('service', 'unknown')}"
        )
        body = alert_data.get("summary", "New alert")[:100]

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={
                    "alert_id": str(alert_data.get("alert_id", "")),
                    "category": alert_data.get("category", ""),
                    "severity": alert_data.get("severity", ""),
                    "root_cause": alert_data.get("root_cause", "")[:500],
                    "solution": alert_data.get("solution", "")[:500],
                },
                tokens=device_tokens,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="logsense_alerts",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1),
                    )
                ),
            )

            response = messaging.send_multicast(message)
            logger.info(
                f"FCM sent: {response.success_count} ok, "
                f"{response.failure_count} failed"
            )
            return response.success_count

        except Exception as e:
            logger.error(f"FCM send error: {e}")
            return 0

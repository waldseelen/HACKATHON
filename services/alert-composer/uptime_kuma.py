"""
Uptime Kuma webhook client – sends alerts to Push Monitor.
"""

import logging
from typing import Dict, Any

import httpx

logger = logging.getLogger("alert-composer.uptime-kuma")


class UptimeKumaClient:
    """Send alerts to Uptime Kuma via Push Monitor webhook."""

    def __init__(self, webhook_url: str = ""):
        self._url = webhook_url.strip()
        if self._url:
            logger.info(f"Uptime Kuma client ready (url ends with …{self._url[-20:]})")
        else:
            logger.warning("Uptime Kuma webhook URL not set — disabled")

    @property
    def available(self) -> bool:
        return bool(self._url)

    async def send_alert(self, alert_data: Dict[str, Any]):
        """POST/GET to Uptime Kuma Push Monitor."""
        if not self._url:
            return

        severity = alert_data.get("severity", "medium")
        is_down = severity in ("critical", "high")

        msg = (
            f"[{alert_data.get('category', 'unknown').upper()}] "
            f"{alert_data.get('summary', 'Alert')}"
        )

        # Uptime Kuma push URL format:
        # http://host:3001/api/push/<token>?status=up&msg=OK&ping=
        try:
            url = self._url
            # Replace status placeholder
            if "status=up" in url:
                url = url.replace("status=up", f"status={'down' if is_down else 'up'}")

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    url,
                    params={"msg": msg[:255], "ping": ""},
                )

            if response.status_code == 200:
                logger.info(f"Uptime Kuma notified (status={'down' if is_down else 'up'})")
            else:
                logger.warning(
                    f"Uptime Kuma returned {response.status_code}: {response.text[:100]}"
                )

        except Exception as e:
            logger.error(f"Uptime Kuma error: {e}")

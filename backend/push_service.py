"""
LogSense AI – Push Notification Service
=========================================
Sends push notifications via Expo Push API.
Works with Expo Go — no native build required.
"""

import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("logsense.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}


async def send_push_notifications(
    tokens: List[str],
    alert_data: Dict[str, Any],
    alert_id: str,
) -> int:
    """
    Send push notifications to all registered Expo devices.
    Returns number of successfully sent notifications.
    """
    if not tokens:
        logger.debug("No push tokens registered — skipping notification")
        return 0

    severity = alert_data.get("severity", "unknown")
    category = alert_data.get("category", "unknown")
    emoji = SEVERITY_EMOJI.get(severity, "⚪")

    messages = [
        {
            "to": token,
            "sound": "default",
            "priority": "high" if severity in ("critical", "high") else "default",
            "title": f"{emoji} {severity.upper()}: {category}",
            "body": (alert_data.get("title") or alert_data.get("summary", "New alert detected"))[:200],
            "data": {
                "alertId": alert_id,
                "category": category,
                "severity": severity,
                "summary": alert_data.get("summary", ""),
                "root_cause": alert_data.get("root_cause", ""),
                "solution": alert_data.get("solution", ""),
                "confidence": str(alert_data.get("confidence", 0)),
                "action_required": str(alert_data.get("action_required", True)),
                "title": alert_data.get("title", ""),
                "dedupe_key": alert_data.get("dedupe_key", ""),
                "impact": alert_data.get("impact", ""),
                "context_for_chat": alert_data.get("context_for_chat", ""),
            },
            "channelId": "alerts",
        }
        for token in tokens
    ]

    sent = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Expo Push API supports batches up to 100
            for i in range(0, len(messages), 100):
                batch = messages[i:i + 100]
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=batch,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    tickets = result.get("data", [])
                    for ticket in tickets:
                        if ticket.get("status") == "ok":
                            sent += 1
                        else:
                            error = ticket.get("message", "unknown")
                            logger.warning(f"Push ticket error: {error}")
                else:
                    logger.error(f"Expo Push API error: {response.status_code} {response.text[:200]}")

    except Exception as e:
        logger.error(f"Push notification failed: {e}")

    logger.info(f"Push notifications sent: {sent}/{len(tokens)}")
    return sent

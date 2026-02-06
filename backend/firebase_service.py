"""
LogSense AI – Firebase Service
================================
All Firestore operations in one place.
"""

import logging
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore  # type: ignore[import-untyped]
from google.oauth2 import service_account as sa

from config import settings

logger = logging.getLogger("logsense.firebase")

# Module-level state
_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.AsyncClient] = None


def _get_db() -> firestore.AsyncClient:
    """Return the Firestore client, raising if not initialized."""
    if _db is None:
        raise RuntimeError("Firebase not initialized. Call init() first.")
    return _db


async def init() -> None:
    """Initialize Firebase Admin SDK and Firestore client."""
    global _app, _db

    if _app is not None:
        return

    logger.info("Initializing Firebase...")
    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred, {
            "projectId": settings.firebase_project_id,
        })

        # Create Firestore client with explicit credentials
        scopes = [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/datastore",
        ]
        google_creds = sa.Credentials.from_service_account_file(
            settings.firebase_credentials_path,
            scopes=scopes,
        )
        _db = firestore.AsyncClient(
            project=settings.firebase_project_id,
            credentials=google_creds,
        )
        logger.info("Firebase Firestore connected")
    except Exception as e:
        logger.error(f"Firebase init failed: {e}")
        raise


def is_ready() -> bool:
    return _db is not None


# ── Log operations ────────────────────────────────────────

async def store_log(parsed: Dict[str, Any]) -> str:
    """Store a parsed log entry. Returns document ID."""
    doc = {
        "container": parsed["container"],
        "service": parsed["service"],
        "severity": parsed["severity"],
        "raw_log": parsed["raw_log"],
        "fingerprint": parsed.get("fingerprint"),
        "timestamp": parsed.get("timestamp"),
        "created_at": firestore.SERVER_TIMESTAMP,
        "processed": False,
    }
    db = _get_db()
    _, ref = await db.collection("logs").add(doc)
    logger.debug(f"Stored log: {ref.id}")
    return ref.id


async def get_unprocessed_logs(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch unprocessed log entries."""
    db = _get_db()
    query = (
        db.collection("logs")
        .where("processed", "==", False)
        .limit(limit)
    )
    docs = await query.get()  # type: ignore[misc]
    return [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]


async def get_logs_by_ids(log_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch specific log entries by their document IDs."""
    db = _get_db()
    results = []
    for log_id in log_ids:
        doc = await db.collection("logs").document(log_id).get()  # type: ignore[misc]
        if doc.exists:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
    return results


async def mark_logs_processed(log_ids: List[str]) -> None:
    """Mark logs as processed after AI analysis."""
    db = _get_db()
    batch = db.batch()
    for log_id in log_ids:
        ref = db.collection("logs").document(log_id)
        batch.update(ref, {"processed": True})
    await batch.commit()


async def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Get most recent logs."""
    db = _get_db()
    query = (
        db.collection("logs")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    docs = await query.get()  # type: ignore[misc]
    result = []
    for doc in docs:
        data = doc.to_dict() or {}
        # Convert Firestore timestamps to ISO strings for JSON serialization
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()  # type: ignore[attr-defined]
        data["id"] = doc.id
        result.append(data)
    return result


# ── Alert operations ──────────────────────────────────────

async def store_alert(alert_data: Dict[str, Any]) -> str:
    """Store an AI analysis alert. Returns document ID."""
    db = _get_db()
    alert_data["created_at"] = firestore.SERVER_TIMESTAMP
    alert_data["notified"] = False
    _, ref = await db.collection("alerts").add(alert_data)
    logger.info(f"Alert stored: {ref.id}")
    return ref.id


async def mark_alert_notified(alert_id: str) -> None:
    """Mark alert as notification-sent."""
    db = _get_db()
    await db.collection("alerts").document(alert_id).update({
        "notified": True,
    })


async def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent alerts for mobile app."""
    db = _get_db()
    query = (
        db.collection("alerts")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    docs = await query.get()  # type: ignore[misc]
    result = []
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()  # type: ignore[attr-defined]
        data["id"] = doc.id
        result.append(data)
    return result


async def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Get a single alert by ID."""
    db = _get_db()
    doc = await db.collection("alerts").document(alert_id).get()  # type: ignore[misc]
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    if data.get("created_at"):
        data["created_at"] = data["created_at"].isoformat()  # type: ignore[attr-defined]
    data["id"] = doc.id
    return data


# ── Device token operations ──────────────────────────────

async def register_push_token(token: str, device_name: str = "unknown", platform: str = "expo") -> None:
    """Register an Expo/FCM push token."""
    db = _get_db()
    await db.collection("device_tokens").document(token).set({
        "token": token,
        "device_name": device_name,
        "platform": platform,
        "active": True,
        "registered_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info(f"Push token registered: {device_name} ({platform})")


async def unregister_push_token(token: str) -> None:
    """Remove a push token."""
    db = _get_db()
    await db.collection("device_tokens").document(token).delete()
    logger.info(f"Push token removed: {token[:20]}...")


async def get_active_push_tokens() -> List[str]:
    """Get all active Expo push tokens."""
    db = _get_db()
    query = db.collection("device_tokens").where("active", "==", True)
    docs = await query.get()  # type: ignore[misc]
    return [t for doc in docs if (data := doc.to_dict() or {}) and (t := data.get("token"))]


# ── Cleanup operations ───────────────────────────────────

async def delete_all_documents(collection_name: str) -> int:
    """Delete all documents in a collection. Returns count deleted."""
    db = _get_db()
    docs = await db.collection(collection_name).limit(500).get()  # type: ignore[misc]
    count = 0
    while docs:
        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)  # type: ignore[attr-defined]
            count += 1
        await batch.commit()
        if len(docs) < 500:
            break
        docs = await db.collection(collection_name).limit(500).get()  # type: ignore[misc]
    return count

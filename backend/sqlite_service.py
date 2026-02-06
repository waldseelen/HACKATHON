"""
LogSense AI – SQLite Storage Service
======================================
Drop-in replacement for firebase_service.py.
Same async interface, backed by local SQLite — zero external deps, zero quotas.
"""

import aiosqlite
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("logsense.sqlite")

_db: Optional[aiosqlite.Connection] = None


def _get_db_path() -> str:
    try:
        from config import settings
        return settings.sqlite_db_path
    except Exception:
        return "/app/data/logsense.db"


async def init() -> None:
    """Initialize SQLite database and create tables."""
    global _db
    if _db is not None:
        return

    import os
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    logger.info(f"Initializing SQLite at {db_path}")
    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row

    # WAL mode for better concurrent read/write
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=NORMAL")

    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            container TEXT,
            service TEXT,
            severity TEXT,
            raw_log TEXT,
            fingerprint TEXT,
            timestamp TEXT,
            created_at TEXT,
            processed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            data TEXT,
            severity TEXT,
            category TEXT,
            title TEXT,
            created_at TEXT,
            notified INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS device_tokens (
            token TEXT PRIMARY KEY,
            device_name TEXT,
            platform TEXT,
            active INTEGER DEFAULT 1,
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            alert_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_logs_processed ON logs(processed);
        CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_alert ON chat_messages(alert_id, created_at);
    """)
    await _db.commit()
    logger.info("SQLite ready")


def is_ready() -> bool:
    return _db is not None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:20]


# ── Log operations ────────────────────────────────────────

async def store_log(parsed: Dict[str, Any]) -> str:
    doc_id = _new_id()
    await _db.execute(
        "INSERT INTO logs (id, container, service, severity, raw_log, fingerprint, timestamp, created_at, processed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (doc_id, parsed["container"], parsed["service"], parsed["severity"],
         parsed["raw_log"], parsed.get("fingerprint"), parsed.get("timestamp"), _now_iso()),
    )
    await _db.commit()
    return doc_id


async def get_unprocessed_logs(limit: int = 10) -> List[Dict[str, Any]]:
    cursor = await _db.execute(
        "SELECT * FROM logs WHERE processed = 0 ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_logs_by_ids(log_ids: List[str]) -> List[Dict[str, Any]]:
    if not log_ids:
        return []
    placeholders = ",".join("?" for _ in log_ids)
    cursor = await _db.execute(f"SELECT * FROM logs WHERE id IN ({placeholders})", log_ids)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def mark_logs_processed(log_ids: List[str]) -> None:
    if not log_ids:
        return
    placeholders = ",".join("?" for _ in log_ids)
    await _db.execute(f"UPDATE logs SET processed = 1 WHERE id IN ({placeholders})", log_ids)
    await _db.commit()


async def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]:
    cursor = await _db.execute(
        "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ── Alert operations ──────────────────────────────────────

async def store_alert(alert_data: Dict[str, Any]) -> str:
    doc_id = _new_id()
    now = _now_iso()
    alert_data["created_at"] = now
    alert_data["notified"] = False
    await _db.execute(
        "INSERT INTO alerts (id, data, severity, category, title, created_at, notified) "
        "VALUES (?, ?, ?, ?, ?, ?, 0)",
        (doc_id, json.dumps(alert_data, default=str),
         alert_data.get("severity", "medium"),
         alert_data.get("category", "unknown"),
         alert_data.get("title", ""),
         now),
    )
    await _db.commit()
    logger.info(f"Alert stored: {doc_id}")
    return doc_id


async def mark_alert_notified(alert_id: str) -> None:
    await _db.execute("UPDATE alerts SET notified = 1 WHERE id = ?", (alert_id,))
    await _db.commit()


async def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    cursor = await _db.execute(
        "SELECT id, data FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        data = json.loads(row["data"])
        data["id"] = row["id"]
        result.append(data)
    return result


async def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    cursor = await _db.execute("SELECT id, data FROM alerts WHERE id = ?", (alert_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    data = json.loads(row["data"])
    data["id"] = row["id"]
    return data


# ── Device token operations ──────────────────────────────

async def register_push_token(token: str, device_name: str = "unknown", platform: str = "expo") -> None:
    await _db.execute(
        "INSERT OR REPLACE INTO device_tokens (token, device_name, platform, active, registered_at) "
        "VALUES (?, ?, ?, 1, ?)",
        (token, device_name, platform, _now_iso()),
    )
    await _db.commit()
    logger.info(f"Push token registered: {device_name} ({platform})")


async def unregister_push_token(token: str) -> None:
    await _db.execute("DELETE FROM device_tokens WHERE token = ?", (token,))
    await _db.commit()


async def get_active_push_tokens() -> List[str]:
    cursor = await _db.execute("SELECT token FROM device_tokens WHERE active = 1")
    rows = await cursor.fetchall()
    return [row["token"] for row in rows]


# ── Chat operations ──────────────────────────────────────

async def store_chat_message(alert_id: str, role: str, content: str) -> str:
    doc_id = _new_id()
    await _db.execute(
        "INSERT INTO chat_messages (id, alert_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (doc_id, alert_id, role, content, _now_iso()),
    )
    await _db.commit()
    return doc_id


async def get_chat_history(alert_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    cursor = await _db.execute(
        "SELECT * FROM chat_messages WHERE alert_id = ? ORDER BY created_at ASC LIMIT ?",
        (alert_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ── Cleanup operations ───────────────────────────────────

async def delete_all_documents(collection_name: str) -> int:
    table_map = {"alerts": "alerts", "logs": "logs", "chat_messages": "chat_messages"}
    table = table_map.get(collection_name, collection_name)
    cursor = await _db.execute(f"SELECT COUNT(*) as cnt FROM {table}")
    row = await cursor.fetchone()
    count = row["cnt"] if row else 0
    await _db.execute(f"DELETE FROM {table}")
    await _db.commit()
    return count

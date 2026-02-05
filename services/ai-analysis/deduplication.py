"""
Deduplication + Batch Service
=============================
Groups similar logs (by fingerprint) within a time window,
then emits a single representative batch for AI analysis.
"""

import asyncio
import hashlib
import logging
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger("ai-analysis.dedup")


class DeduplicationService:
    """
    Accumulates incoming logs by fingerprint.
    Flushes a batch when the time window expires or the batch is full.
    """

    def __init__(
        self,
        window_seconds: int = 2,
        max_batch_size: int = 50,
        on_flush: Optional[Callable[[List[Dict[str, Any]]], Coroutine]] = None,
    ):
        self.window = window_seconds
        self.max_batch = max_batch_size
        self._on_flush = on_flush

        # fingerprint → {"first_seen": float, "logs": [...]}
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the periodic flush loop."""
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"Dedup started (window={self.window}s, max_batch={self.max_batch})"
        )

    async def stop(self):
        if self._flush_task:
            self._flush_task.cancel()
        # Flush remaining
        await self._flush_all()

    async def add(self, log_data: Dict[str, Any]):
        """Add a log entry. May trigger an immediate flush."""
        fp = log_data.get("fingerprint", _compute_fingerprint(log_data["raw_log"]))

        async with self._lock:
            now = time.time()

            if fp not in self._buckets:
                self._buckets[fp] = {"first_seen": now, "logs": []}

            bucket = self._buckets[fp]
            bucket["logs"].append(log_data)

            # Immediate flush if batch is full
            if len(bucket["logs"]) >= self.max_batch:
                logs = self._buckets.pop(fp)["logs"]
                asyncio.create_task(self._emit(logs))

    # ── internal ──────────────────────────────────────────

    async def _flush_loop(self):
        """Periodically check for expired windows."""
        try:
            while True:
                await asyncio.sleep(0.5)  # check every 500ms
                await self._flush_expired()
        except asyncio.CancelledError:
            pass

    async def _flush_expired(self):
        """Flush buckets whose time window has elapsed."""
        now = time.time()
        to_flush: List[List[Dict[str, Any]]] = []

        async with self._lock:
            expired_keys = [
                fp
                for fp, bucket in self._buckets.items()
                if (now - bucket["first_seen"]) >= self.window
            ]
            for fp in expired_keys:
                to_flush.append(self._buckets.pop(fp)["logs"])

        for logs in to_flush:
            await self._emit(logs)

    async def _flush_all(self):
        """Flush every remaining bucket (shutdown)."""
        async with self._lock:
            all_logs = [b["logs"] for b in self._buckets.values()]
            self._buckets.clear()

        for logs in all_logs:
            await self._emit(logs)

    async def _emit(self, logs: List[Dict[str, Any]]):
        """Send a batch to the registered callback."""
        if not logs:
            return

        count = len(logs)
        # Augment representative log with dedup metadata
        logs[0]["_dedup_count"] = count

        logger.info(
            f"Flush batch: {count} log(s), fingerprint={logs[0].get('fingerprint','?')[:8]}"
        )

        if self._on_flush:
            try:
                await self._on_flush(logs)
            except Exception as e:
                logger.error(f"Flush callback error: {e}")


# ── helper ────────────────────────────────────────────────

_STRIP_PATTERNS = [
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?"), ""),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "IP"),
    (re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I), "UUID"),
    (re.compile(r"\b\d+\b"), "NUM"),
]


def _compute_fingerprint(text: str) -> str:
    normalized = text
    for pat, repl in _STRIP_PATTERNS:
        normalized = pat.sub(repl, normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

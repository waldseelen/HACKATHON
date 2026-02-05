"""
Log Parser – filtering + normalization
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Any


class LogParser:
    """Parse and filter log lines."""

    # Patterns that mark a log as interesting (ERROR / WARN)
    _SEVERITY_PATTERNS = [
        (re.compile(r"\b(FATAL|CRITICAL)\b", re.I), "fatal"),
        (re.compile(r"\b(ERROR|ERR|Exception|Traceback)\b", re.I), "error"),
        (re.compile(r"\b(WARN|WARNING)\b", re.I), "warn"),
    ]

    # Dynamic parts to strip when computing fingerprint
    _FINGERPRINT_STRIP = [
        (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?"), ""),
        (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "IP"),
        (re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I), "UUID"),
        (re.compile(r"\b\d+\b"), "NUM"),
    ]

    # ──────────────────────────────────────────────

    def should_process(self, line: str) -> bool:
        """Return True if the line contains an error or warning."""
        if not line or not line.strip():
            return False
        for pattern, _ in self._SEVERITY_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def detect_severity(self, line: str) -> str:
        for pattern, level in self._SEVERITY_PATTERNS:
            if pattern.search(line):
                return level
        return "unknown"

    def extract_timestamp(self, line: str) -> str:
        m = re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", line)
        if m:
            return m.group(1)
        return datetime.now(timezone.utc).isoformat()

    def compute_fingerprint(self, line: str) -> str:
        """Produce a hash ignoring dynamic values (timestamps, IPs, etc)."""
        normalized = line
        for pattern, repl in self._FINGERPRINT_STRIP:
            normalized = pattern.sub(repl, normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def parse(self, raw_log: str, container_name: str = "unknown") -> Dict[str, Any]:
        """Parse a raw log line into a structured dict."""
        raw_log = raw_log.strip()
        severity = self.detect_severity(raw_log)
        timestamp = self.extract_timestamp(raw_log)
        fingerprint = self.compute_fingerprint(raw_log)

        # Service name: derive from container name (strip random suffix)
        service = re.sub(r"[-_]\d+$", "", container_name)

        return {
            "timestamp": timestamp,
            "severity": severity,
            "service": service,
            "container": container_name,
            "raw_log": raw_log,
            "fingerprint": fingerprint,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

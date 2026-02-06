"""
LogSense AI – Log Parser
=========================
Filters ERROR/WARN logs and normalizes them.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict


class LogParser:
    """Parse, filter and normalize log lines."""

    _SEVERITY_PATTERNS = [
        (re.compile(r"\b(FATAL|CRITICAL)\b", re.I), "critical"),
        (re.compile(r"\b(ERROR|ERR|Exception|Traceback)\b", re.I), "error"),
        (re.compile(r"\b(WARN|WARNING)\b", re.I), "warn"),
    ]

    _FINGERPRINT_STRIP = [
        (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?"), ""),
        (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "IP"),
        (re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I), "UUID"),
        (re.compile(r"\b\d+\b"), "N"),
    ]

    _SERVICE_PATTERN = re.compile(r"[\[\s]?(\w[\w\-\.]+)[\]:\s]")

    def should_process(self, line: str) -> bool:
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
        return m.group(1) if m else datetime.now(timezone.utc).isoformat()

    def extract_service(self, line: str, container: str) -> str:
        m = self._SERVICE_PATTERN.search(line)
        if m:
            candidate = m.group(1).lower()
            if candidate not in ("error", "warn", "fatal", "critical", "info", "debug"):
                return candidate
        return container.split("-")[0] if "-" in container else container

    def compute_fingerprint(self, line: str) -> str:
        normalized = line
        for pattern, repl in self._FINGERPRINT_STRIP:
            normalized = pattern.sub(repl, normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def parse(self, raw_log: str, container_name: str = "unknown") -> Dict[str, Any]:
        severity = self.detect_severity(raw_log)
        service = self.extract_service(raw_log, container_name)
        timestamp = self.extract_timestamp(raw_log)
        fingerprint = self.compute_fingerprint(raw_log)

        return {
            "container": container_name,
            "service": service,
            "severity": severity,
            "raw_log": raw_log.strip(),
            "timestamp": timestamp,
            "fingerprint": fingerprint,
        }

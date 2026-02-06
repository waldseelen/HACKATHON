"""
LogSense AI – Cascade Failure Detector
========================================
Detects production cascade failure patterns by correlating multiple
error signals across time windows. Generates severity escalation
and triggers automated runbook suggestions.

Supported cascade patterns:
  • OOM Kill Loop        – Repeated OOMKilled + container restarts
  • Database Cascade     – Connection pool exhaustion + timeouts + refused
  • Disk Pressure        – High disk usage + write failures + log rotation
  • Network Cascade      – SSL failures + upstream errors + connection resets
  • Resource Exhaustion  – File descriptors + max connections + GC overhead
  • Full Cascade         – Multiple subsystems failing simultaneously
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger("logsense.cascade")


# ── Signal Types ─────────────────────────────────────────

class SignalType(str, Enum):
    # Memory / OOM
    OOM_KILLED = "oom_killed"
    OOM_LOG = "oom_log"
    GC_OVERHEAD = "gc_overhead"
    HEAP_EXHAUSTION = "heap_exhaustion"
    SIGKILL = "sigkill"

    # Disk
    DISK_HIGH_USAGE = "disk_high_usage"
    DISK_FULL = "disk_full"
    TOO_MANY_OPEN_FILES = "too_many_open_files"

    # Database
    DB_CONNECTION_REFUSED = "db_connection_refused"
    DB_TIMEOUT = "db_timeout"
    DB_MAX_CONNECTIONS = "db_max_connections"
    DB_POOL_EXHAUSTED = "db_pool_exhausted"

    # Network
    SSL_HANDSHAKE_FAILED = "ssl_handshake_failed"
    CERTIFICATE_EXPIRED = "certificate_expired"
    CONNECTION_RESET = "connection_reset"
    UPSTREAM_ERROR = "upstream_error"
    HTTP_503 = "http_503"
    HTTP_502 = "http_502"

    # Infrastructure
    CONTAINER_RESTART = "container_restart"
    NGINX_ERROR = "nginx_error"
    RUNTIME_PANIC = "runtime_panic"
    KUBECTL_RESTART = "kubectl_restart"

    # Messaging / Cache
    REDIS_CONNECTION_ERROR = "redis_connection_error"
    KAFKA_NO_BROKERS = "kafka_no_brokers"


# ── Signal Detection Patterns ────────────────────────────

SIGNAL_PATTERNS: list[tuple[re.Pattern, SignalType]] = [
    # Memory / OOM
    (re.compile(r"OOMKilled|OOM\s*Kill", re.I), SignalType.OOM_KILLED),
    (re.compile(r"OOM\s*(killed|killer|memory)", re.I), SignalType.OOM_LOG),
    (re.compile(r"gc\s+overhead\s+limit\s+exceeded", re.I), SignalType.GC_OVERHEAD),
    (re.compile(r"(java\.lang\.OutOfMemoryError|heap\s+space|Cannot allocate memory)", re.I), SignalType.HEAP_EXHAUSTION),
    (re.compile(r"SIGKILL\s+received|signal:\s*killed|kill\s+-9", re.I), SignalType.SIGKILL),

    # Disk
    (re.compile(r"disk\s+usage\s+(\d{2,3})%", re.I), SignalType.DISK_HIGH_USAGE),
    (re.compile(r"(No space left on device|disk\s+full|ENOSPC)", re.I), SignalType.DISK_FULL),
    (re.compile(r"Too\s+many\s+open\s+files|EMFILE|ENFILE|ulimit", re.I), SignalType.TOO_MANY_OPEN_FILES),

    # Database
    (re.compile(r"Connection\s+refused\s*:?\s*5432|ECONNREFUSED.*5432|postgres.*refused", re.I), SignalType.DB_CONNECTION_REFUSED),
    (re.compile(r"(Connection\s+timeout|TimeoutException|db.*timeout|database.*timeout)", re.I), SignalType.DB_TIMEOUT),
    (re.compile(r"max_connections\s+reached|too\s+many\s+connections|connection\s+limit", re.I), SignalType.DB_MAX_CONNECTIONS),
    (re.compile(r"(connection\s+pool\s+(exhausted|full|depleted)|pool.*capacity|no\s+available\s+connection)", re.I), SignalType.DB_POOL_EXHAUSTED),

    # Network
    (re.compile(r"SSL\s+handshake\s+failed|SSL_ERROR|TLS\s+handshake", re.I), SignalType.SSL_HANDSHAKE_FAILED),
    (re.compile(r"certificate\s+has\s+expired|X509.*expired|cert.*expir", re.I), SignalType.CERTIFICATE_EXPIRED),
    (re.compile(r"ECONNRESET|Connection\s+reset\s+by\s+peer", re.I), SignalType.CONNECTION_RESET),
    (re.compile(r"upstream\s+(timed\s+out|error|unavailable)|nginx:\s*\[error\]\s*upstream", re.I), SignalType.UPSTREAM_ERROR),
    (re.compile(r"HTTP\s+503|503\s+Service\s+Unavailable|ServiceUnavailable", re.I), SignalType.HTTP_503),
    (re.compile(r"HTTP\s+502|502\s+Bad\s+Gateway", re.I), SignalType.HTTP_502),

    # Infrastructure
    (re.compile(r"container.*restart|restart\s+loop|CrashLoopBackOff", re.I), SignalType.CONTAINER_RESTART),
    (re.compile(r"nginx:\s*\[error\]", re.I), SignalType.NGINX_ERROR),
    (re.compile(r"panic:\s+runtime\s+error|goroutine.*panic|SIGSEGV", re.I), SignalType.RUNTIME_PANIC),
    (re.compile(r"kubectl\s+rollout\s+restart|deployment.*restart", re.I), SignalType.KUBECTL_RESTART),

    # Messaging / Cache
    (re.compile(r"redis\.exceptions\.ConnectionError|redis.*ECONNREFUSED|redis.*connection\s+refused", re.I), SignalType.REDIS_CONNECTION_ERROR),
    (re.compile(r"kafka\.errors\.NoBrokersAvailable|kafka.*no\s+broker|kafka.*disconnect", re.I), SignalType.KAFKA_NO_BROKERS),
]


# ── Cascade Pattern Definitions ──────────────────────────

@dataclass
class CascadePattern:
    """Defines a known cascade failure pattern."""
    name: str
    description: str
    required_signals: set[SignalType]  # ALL must be present
    optional_signals: set[SignalType]  # Any of these boost confidence
    min_required: int  # Minimum number of required signals to trigger
    severity: str  # critical / high / medium
    phase: str  # Which recovery phase applies first
    runbook_id: str  # Links to RunbookEngine


CASCADE_PATTERNS: list[CascadePattern] = [
    CascadePattern(
        name="OOM Kill Loop",
        description="Tekrarlayan OOMKilled → container restart döngüsü. Memory limitleri yetersiz veya memory leak mevcut.",
        required_signals={SignalType.OOM_KILLED, SignalType.SIGKILL},
        optional_signals={SignalType.GC_OVERHEAD, SignalType.HEAP_EXHAUSTION, SignalType.CONTAINER_RESTART},
        min_required=1,
        severity="critical",
        phase="PHASE_1_EMERGENCY_STOP",
        runbook_id="oom_kill_loop",
    ),
    CascadePattern(
        name="Database Cascade Failure",
        description="Veritabanı bağlantı havuzu tükendi → timeout → connection refused zinciri. Tüm DB-bağımlı servisler etkileniyor.",
        required_signals={SignalType.DB_CONNECTION_REFUSED, SignalType.DB_TIMEOUT, SignalType.DB_MAX_CONNECTIONS},
        optional_signals={SignalType.DB_POOL_EXHAUSTED, SignalType.HTTP_503},
        min_required=2,
        severity="critical",
        phase="PHASE_2_RESOURCE_CLEANUP",
        runbook_id="database_cascade",
    ),
    CascadePattern(
        name="Disk Pressure Crisis",
        description="Disk dolmak üzere (%95+) → loglama durmuş → yeni yazma işlemleri başarısız. Veri kaybı riski.",
        required_signals={SignalType.DISK_HIGH_USAGE, SignalType.DISK_FULL},
        optional_signals={SignalType.TOO_MANY_OPEN_FILES, SignalType.CONTAINER_RESTART},
        min_required=1,
        severity="critical",
        phase="PHASE_2_RESOURCE_CLEANUP",
        runbook_id="disk_pressure",
    ),
    CascadePattern(
        name="Network / TLS Cascade",
        description="SSL sertifika süresi dolmuş veya TLS handshake başarısız → upstream 502/503 → tüm HTTPS trafiği kesik.",
        required_signals={SignalType.SSL_HANDSHAKE_FAILED, SignalType.CERTIFICATE_EXPIRED},
        optional_signals={SignalType.UPSTREAM_ERROR, SignalType.HTTP_503, SignalType.HTTP_502, SignalType.NGINX_ERROR},
        min_required=1,
        severity="critical",
        phase="PHASE_3_SERVICE_RESTART",
        runbook_id="network_tls_cascade",
    ),
    CascadePattern(
        name="Resource Exhaustion Storm",
        description="Birden fazla kaynak limiti aşıldı: file descriptor, connection, memory. Sistem genelinde servis durması riski.",
        required_signals={SignalType.TOO_MANY_OPEN_FILES, SignalType.DB_MAX_CONNECTIONS},
        optional_signals={SignalType.GC_OVERHEAD, SignalType.OOM_KILLED, SignalType.DISK_HIGH_USAGE},
        min_required=2,
        severity="high",
        phase="PHASE_2_RESOURCE_CLEANUP",
        runbook_id="resource_exhaustion",
    ),
    CascadePattern(
        name="Full Production Cascade",
        description="⚠️ ÇOKLU SUBSYSTEM ÇÖKMESI: OOM + DB + Disk + Network eş zamanlı başarısız. Tam incident yönetimi gerekli.",
        required_signals={SignalType.OOM_KILLED, SignalType.DB_TIMEOUT, SignalType.HTTP_503},
        optional_signals={
            SignalType.DISK_HIGH_USAGE, SignalType.SSL_HANDSHAKE_FAILED,
            SignalType.REDIS_CONNECTION_ERROR, SignalType.KAFKA_NO_BROKERS,
            SignalType.TOO_MANY_OPEN_FILES, SignalType.GC_OVERHEAD,
        },
        min_required=3,
        severity="critical",
        phase="PHASE_1_EMERGENCY_STOP",
        runbook_id="full_cascade",
    ),
    CascadePattern(
        name="Messaging Infrastructure Down",
        description="Redis ve/veya Kafka erişilemez → async işlemler birikti → backpressure cascade.",
        required_signals={SignalType.REDIS_CONNECTION_ERROR, SignalType.KAFKA_NO_BROKERS},
        optional_signals={SignalType.HTTP_503, SignalType.CONNECTION_RESET},
        min_required=1,
        severity="high",
        phase="PHASE_3_SERVICE_RESTART",
        runbook_id="messaging_down",
    ),
    CascadePattern(
        name="Upstream 503 Storm",
        description="Nginx upstream servislere ulaşamıyor → 503 dalgası → client-side retry trafiği artırıyor → cascade.",
        required_signals={SignalType.UPSTREAM_ERROR, SignalType.HTTP_503},
        optional_signals={SignalType.NGINX_ERROR, SignalType.CONNECTION_RESET, SignalType.HTTP_502},
        min_required=2,
        severity="high",
        phase="PHASE_1_EMERGENCY_STOP",
        runbook_id="upstream_storm",
    ),
]


# ── Detection Result ─────────────────────────────────────

@dataclass
class CascadeDetectionResult:
    """Result of cascade failure detection."""
    is_cascade: bool = False
    cascade_type: str = ""
    severity: str = "medium"
    confidence: float = 0.0
    detected_signals: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    phase: str = ""
    runbook_id: str = ""
    description: str = ""
    signal_count: int = 0
    total_patterns_checked: int = 0

    def to_dict(self) -> dict:
        return {
            "is_cascade": self.is_cascade,
            "cascade_type": self.cascade_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "detected_signals": self.detected_signals,
            "matched_patterns": self.matched_patterns,
            "phase": self.phase,
            "runbook_id": self.runbook_id,
            "description": self.description,
            "signal_count": self.signal_count,
        }


# ── Cascade Detector ─────────────────────────────────────

class CascadeDetector:
    """
    Detect cascade failure patterns from log signals.

    Usage:
        detector = CascadeDetector()
        result = detector.analyze(log_text)
        # or analyze multiple logs:
        result = detector.analyze_multiple(list_of_log_texts)
    """

    # Time-windowed signal buffer for correlation
    _signal_buffer: list[tuple[float, SignalType]] = []
    SIGNAL_WINDOW_SECONDS = 300  # 5-minute correlation window

    def __init__(self):
        self._signal_buffer = []

    def detect_signals(self, text: str) -> list[SignalType]:
        """Extract all matching signals from a log text."""
        signals = []
        for pattern, signal_type in SIGNAL_PATTERNS:
            if pattern.search(text):
                signals.append(signal_type)
        return list(set(signals))  # deduplicate

    def add_signals(self, signals: list[SignalType]) -> None:
        """Add signals to the time-windowed buffer."""
        now = time.time()
        for sig in signals:
            self._signal_buffer.append((now, sig))
        # Prune old signals
        cutoff = now - self.SIGNAL_WINDOW_SECONDS
        self._signal_buffer = [(t, s) for t, s in self._signal_buffer if t >= cutoff]

    def get_active_signals(self) -> set[SignalType]:
        """Get all signals within the current time window."""
        now = time.time()
        cutoff = now - self.SIGNAL_WINDOW_SECONDS
        return {s for t, s in self._signal_buffer if t >= cutoff}

    def analyze(self, text: str) -> CascadeDetectionResult:
        """Analyze a single log text for cascade patterns."""
        signals = self.detect_signals(text)
        self.add_signals(signals)
        return self._evaluate()

    def analyze_multiple(self, texts: list[str]) -> CascadeDetectionResult:
        """Analyze multiple log texts together for cascade patterns."""
        all_signals = []
        for text in texts:
            all_signals.extend(self.detect_signals(text))
        self.add_signals(all_signals)
        return self._evaluate()

    def analyze_signals_only(self, signals: list[SignalType]) -> CascadeDetectionResult:
        """Analyze pre-extracted signals (used by AI analysis post-processing)."""
        self.add_signals(signals)
        return self._evaluate()

    def _evaluate(self) -> CascadeDetectionResult:
        """Evaluate current signal buffer against cascade patterns."""
        active_signals = self.get_active_signals()

        if not active_signals:
            return CascadeDetectionResult(total_patterns_checked=len(CASCADE_PATTERNS))

        best_match: Optional[CascadePattern] = None
        best_score: float = 0.0
        all_matched: list[str] = []

        for pattern in CASCADE_PATTERNS:
            # Count matching required signals
            required_hits = active_signals & pattern.required_signals
            optional_hits = active_signals & pattern.optional_signals

            if len(required_hits) < pattern.min_required:
                continue

            # Score: required matches weighted 2x, optional 1x
            score = (len(required_hits) * 2 + len(optional_hits)) / (
                len(pattern.required_signals) * 2 + len(pattern.optional_signals)
            )

            all_matched.append(pattern.name)

            if score > best_score:
                best_score = score
                best_match = pattern

        if not best_match:
            # No cascade pattern matched, but we have signals
            return CascadeDetectionResult(
                is_cascade=False,
                detected_signals=[s.value for s in active_signals],
                signal_count=len(active_signals),
                total_patterns_checked=len(CASCADE_PATTERNS),
            )

        # Calculate confidence based on signal coverage
        confidence = min(0.99, best_score * 0.85 + (len(active_signals) / 10) * 0.15)

        # Severity escalation: if multiple patterns match, escalate
        severity = best_match.severity
        if len(all_matched) >= 3:
            severity = "critical"
        elif len(all_matched) >= 2 and severity != "critical":
            severity = "high"

        result = CascadeDetectionResult(
            is_cascade=True,
            cascade_type=best_match.name,
            severity=severity,
            confidence=round(confidence, 3),
            detected_signals=[s.value for s in active_signals],
            matched_patterns=all_matched,
            phase=best_match.phase,
            runbook_id=best_match.runbook_id,
            description=best_match.description,
            signal_count=len(active_signals),
            total_patterns_checked=len(CASCADE_PATTERNS),
        )

        logger.warning(
            f"🚨 CASCADE DETECTED: {best_match.name} | severity={severity} | "
            f"signals={len(active_signals)} | patterns={len(all_matched)} | "
            f"confidence={confidence:.0%}"
        )

        return result

    def clear(self):
        """Clear signal buffer (for testing or after incident resolution)."""
        self._signal_buffer.clear()

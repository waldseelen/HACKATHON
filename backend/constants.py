"""
LogSense AI – Constants
========================
Centralized constants — no more magic numbers scattered across codebase.
"""

# ── In-Memory Dedup Cache ────────────────────────────────
MAX_PROCESSED_CACHE = 5000

# ── SSE ──────────────────────────────────────────────────
SSE_KEEPALIVE_SECONDS = 30
SSE_MAX_QUEUE_SIZE = 50
SSE_MAX_CLIENTS = 100

# ── Alerts / Logs Query Limits ───────────────────────────
DEFAULT_ALERTS_LIMIT = 50
MAX_ALERTS_LIMIT = 200
DEFAULT_LOGS_LIMIT = 20
MAX_LOGS_LIMIT = 100

# ── Batch Ingestion ──────────────────────────────────────
MAX_BATCH_SIZE = 500  # Max number of log entries in a single /ingest/batch call

# ── Firestore Timeout (seconds) ─────────────────────────
FIRESTORE_TIMEOUT = 8.0

# ── Rate Limiting ────────────────────────────────────────
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW_SECONDS = 60  # window duration

# ── Log Sanitization ────────────────────────────────────
MAX_LOG_LINE_LENGTH = 10_000  # max characters per log line

# ── QR Code ──────────────────────────────────────────────
QR_BOX_SIZE = 10
QR_BORDER = 4

# ── Chat ─────────────────────────────────────────────────
CHAT_CONCURRENCY_LIMIT = 5       # Max concurrent chat requests to AI
CHAT_COOLDOWN_SECONDS = 1        # Min seconds between chat requests per user
CHAT_MAX_MESSAGE_LENGTH = 2000   # Max characters per chat message
CHAT_TIMEOUT_SECONDS = 180       # Hard timeout for AI chat response (longer for rate-limited free tier)

# ── In-Memory Cache ──────────────────────────────────────
ALERTS_CACHE_TTL_SECONDS = 10    # Cache alerts for N seconds
STATS_CACHE_TTL_SECONDS = 15     # Cache stats for N seconds

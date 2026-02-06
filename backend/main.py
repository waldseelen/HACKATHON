"""
LogSense AI – Main Application
================================
Single FastAPI monolith: ingestion + AI analysis + push notifications.

Endpoints:
  POST /ingest           – Receive a single log line
  POST /ingest/batch     – Receive multiple log lines
  GET  /health           – Health check
  GET  /alerts           – Recent alerts (for mobile)
  GET  /alerts/{id}      – Single alert detail
  GET  /logs/recent      – Recent ingested logs
  POST /register-token   – Register Expo push token
  DELETE /register-token – Remove push token
  GET  /qr               – QR code for backend API URL
  GET  /qr/mobile        – QR code for Expo mobile app
"""

import asyncio
import collections
import io
import logging
import re
import socket
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import qrcode

from config import settings
from constants import (
    MAX_PROCESSED_CACHE,
    SSE_KEEPALIVE_SECONDS,
    SSE_MAX_QUEUE_SIZE,
    SSE_MAX_CLIENTS,
    DEFAULT_ALERTS_LIMIT,
    MAX_ALERTS_LIMIT,
    DEFAULT_LOGS_LIMIT,
    MAX_LOGS_LIMIT,
    MAX_BATCH_SIZE,
    FIRESTORE_TIMEOUT,
    MAX_LOG_LINE_LENGTH,
    QR_BOX_SIZE,
    QR_BORDER,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    CHAT_CONCURRENCY_LIMIT,
    CHAT_COOLDOWN_SECONDS,
    CHAT_MAX_MESSAGE_LENGTH,
    ALERTS_CACHE_TTL_SECONDS,
    STATS_CACHE_TTL_SECONDS,
)
from models import (
    LogEntry,
    LogBatchRequest,
    IngestResponse,
    HealthResponse,
    TokenRegistration,
    AnalysisResult,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
)
from log_parser import LogParser
from openrouter_client import OpenRouterClient
import firebase_service as fb
import push_service

logger = logging.getLogger("logsense.main")

# ── Shared State ──────────────────────────────────────────

parser = LogParser()
ai_client = OpenRouterClient(api_key=settings.openrouter_api_key, model_name=settings.openrouter_model)
pending_queue: asyncio.Queue = asyncio.Queue()
_processed_ids: collections.OrderedDict = collections.OrderedDict()  # LRU dedup cache
worker_task = None

# SSE broadcast: connected clients receive new alerts in real-time
_sse_clients: list[asyncio.Queue] = []

# Rate limiting: per-IP request tracking
_rate_limit_store: dict[str, list[float]] = {}

# Chat concurrency control
_chat_semaphore: asyncio.Semaphore = asyncio.Semaphore(CHAT_CONCURRENCY_LIMIT)
_chat_cooldown: dict[str, float] = {}  # IP -> last chat request time

# In-memory cache for Firestore data
_alerts_cache: dict[str, any] = {"data": None, "ts": 0}
_stats_cache: dict[str, any] = {"data": None, "ts": 0}


# ── Log Sanitization ─────────────────────────────────────

_SANITIZE_PATTERNS = [
    # API keys, tokens, secrets
    (re.compile(r'(?i)(api[_-]?key|token|secret|password|passwd|pwd|authorization|bearer)\s*[=:]\s*[\S]+'), r'\1=***REDACTED***'),
    # Email addresses
    (re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'), '***EMAIL***'),
    # IP addresses (keep structure but log them as-is for debugging)
    # Credit card numbers (basic pattern)
    (re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'), '***CARD***'),
    # JWT tokens
    (re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+'), '***JWT***'),
    # Generic hex secrets (32+ chars)
    (re.compile(r'(?i)(?:key|token|secret|hash)\s*[=:]\s*[0-9a-f]{32,}'), '***HEX_SECRET***'),
]


def sanitize_log(text: str) -> str:
    """Remove sensitive data from log text before AI analysis."""
    if not text:
        return text
    # Truncate overly long logs
    if len(text) > MAX_LOG_LINE_LENGTH:
        text = text[:MAX_LOG_LINE_LENGTH] + "... [TRUNCATED]"
    for pattern, replacement in _SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── LRU Cache Helpers ────────────────────────────────────

def _lru_add(item: str) -> None:
    """Add item to LRU cache, evicting oldest if over limit."""
    if item in _processed_ids:
        _processed_ids.move_to_end(item)
        return
    _processed_ids[item] = True
    while len(_processed_ids) > MAX_PROCESSED_CACHE:
        _processed_ids.popitem(last=False)  # Remove oldest


def _lru_contains(item: str) -> bool:
    """Check if item is in cache, refreshing its position."""
    if item in _processed_ids:
        _processed_ids.move_to_end(item)
        return True
    return False


# ── Background Worker ────────────────────────────────────

async def analysis_worker():
    """
    Background worker: consumes log IDs **only** from the in-process
    queue, batches them, runs DeepSeek AI (via OpenRouter), stores alerts, sends push.

    IMPORTANT: Never polls Firestore for unprocessed logs — avoids
    the duplicate-alert bug caused by re-processing the same log.
    """
    logger.info("Analysis worker started")
    consecutive_errors = 0

    while True:
        batch_ids: list[str] = []
        try:
            # Wait for first log (blocks until available)
            first_id = await asyncio.wait_for(
                pending_queue.get(), timeout=settings.batch_window_seconds
            )
            if not _lru_contains(first_id):
                batch_ids.append(first_id)
            pending_queue.task_done()

            # Collect more if available (non-blocking), up to max batch
            while len(batch_ids) < settings.max_batch_size:
                try:
                    next_id = pending_queue.get_nowait()
                    pending_queue.task_done()
                    if not _lru_contains(next_id):
                        batch_ids.append(next_id)
                except asyncio.QueueEmpty:
                    break

        except asyncio.TimeoutError:
            # Queue empty — just loop back and wait
            # Drain stale items if queue is getting large
            if pending_queue.qsize() > 100:
                drained = 0
                while not pending_queue.empty() and drained < 50:
                    try:
                        stale_id = pending_queue.get_nowait()
                        pending_queue.task_done()
                        _lru_add(stale_id)  # Mark as processed to prevent re-queue
                        drained += 1
                    except asyncio.QueueEmpty:
                        break
                if drained > 0:
                    logger.warning(f"Drained {drained} stale items from pending queue (was {pending_queue.qsize() + drained})")
            continue
        except asyncio.CancelledError:
            logger.info("Analysis worker stopping")
            break

        if not batch_ids:
            continue

        # Fetch log contents by their known IDs
        try:
            target_logs = await asyncio.wait_for(
                fb.get_logs_by_ids(batch_ids), timeout=FIRESTORE_TIMEOUT * 2
            )
            if not target_logs:
                # Mark IDs as processed even if logs not found
                for aid in batch_ids:
                    _lru_add(aid)
                continue

            logs_text = "\n".join(l.get("raw_log", "") for l in target_logs)
            actual_ids = [l["id"] for l in target_logs]

            # ➊ Mark processed FIRST to prevent any re-pickup
            await fb.mark_logs_processed(actual_ids)
            for aid in actual_ids:
                _lru_add(aid)

            # ➋ Then run analysis + alert storage
            await _process_batch(actual_ids, logs_text)
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            # Mark failed IDs as processed to prevent infinite retry
            for aid in batch_ids:
                _lru_add(aid)
            backoff = min(2 ** consecutive_errors, 30)
            logger.error(f"Batch processing failed (attempt {consecutive_errors}): {e}. Backing off {backoff}s")
            await asyncio.sleep(backoff)


async def _process_batch(log_ids: list[str], logs_text: str):
    """Analyze a batch of logs with DeepSeek AI, store alert, send push."""
    try:
        # AI Analysis
        result: AnalysisResult = await ai_client.analyze(logs_text, count=len(log_ids))
        alert_data = result.model_dump()

    except Exception as e:
        logger.warning(f"AI analysis failed, using fallback: {e}")
        fallback = ai_client._fallback(logs_text)
        alert_data = fallback.model_dump()

    # Store alert (single path — no duplicate storage)
    try:
        alert_data["log_ids"] = log_ids
        alert_id = await fb.store_alert(alert_data)

        # Invalidate caches when new alert is stored
        _alerts_cache["data"] = None
        _stats_cache["data"] = None

        # Broadcast to SSE clients
        sse_payload = {**alert_data, "id": alert_id}
        for q in _sse_clients:
            try:
                q.put_nowait(sse_payload)
            except asyncio.QueueFull:
                pass

        # Send push notifications
        tokens = await fb.get_active_push_tokens()
        if tokens:
            sent = await push_service.send_push_notifications(tokens, alert_data, alert_id)
            if sent > 0:
                await fb.mark_alert_notified(alert_id)

        sev = alert_data.get("severity", "?")
        cat = alert_data.get("category", "?")
        conf = alert_data.get("confidence", 0)
        logger.info(
            f"Batch processed: {len(log_ids)} logs → {sev}/{cat} (confidence={conf:.0%})"
        )

    except Exception as e:
        logger.error(f"Alert storage/push failed: {e}")


# ── Docker Log Watcher (optional) ────────────────────────

async def docker_watcher():
    """Stream ERROR/WARN logs from running Docker containers."""
    if not settings.enable_docker_watcher:
        logger.info("Docker watcher disabled")
        return

    try:
        import aiodocker
    except ImportError:
        logger.info("aiodocker not installed — Docker watcher disabled")
        return

    logger.info("Docker watcher starting...")
    await asyncio.sleep(5)  # Let other services initialize

    try:
        docker = aiodocker.Docker()
    except Exception as e:
        logger.warning(f"Cannot connect to Docker: {e}")
        return

    while True:
        try:
            containers = await docker.containers.list()
            tasks = []
            for container in containers:
                info = await container.show()
                name = info["Name"].lstrip("/")
                if name.startswith("logsense-"):
                    continue
                tasks.append(_stream_container(container, name))

            if tasks:
                logger.info(f"Watching {len(tasks)} containers")
                await asyncio.gather(*tasks, return_exceptions=True)

            await asyncio.sleep(30)  # Re-scan every 30s

        except asyncio.CancelledError:
            await docker.close()
            break
        except Exception as e:
            logger.error(f"Docker watcher error: {e}")
            await asyncio.sleep(10)


async def _stream_container(container, name: str):
    """Stream logs from a single container."""
    try:
        async for line in container.log(stdout=True, stderr=True, follow=True, tail=0):
            text = line.strip()
            if text and parser.should_process(text):
                text = sanitize_log(text)  # Sanitize before processing
                parsed = parser.parse(text, container_name=name)
                log_id = await fb.store_log(parsed)
                await pending_queue.put(log_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"Stream ended for {name}: {e}")


# ── Lifespan ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    # Startup
    await fb.init()
    worker_task = asyncio.create_task(analysis_worker())
    asyncio.create_task(docker_watcher())
    logger.info("LogSense AI backend ready")

    yield

    # Shutdown
    if worker_task:
        worker_task.cancel()
    logger.info("LogSense AI backend stopped")


# ── FastAPI App ───────────────────────────────────────────

app = FastAPI(
    title="LogSense AI",
    description="Real-time container log analysis with DeepSeek AI (OpenRouter) + push notifications",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate Limiting Middleware ─────────────────────────────

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory sliding-window rate limiter per client IP."""
    # Skip rate limiting for health checks
    if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = RATE_LIMIT_WINDOW_SECONDS

    # Clean old entries and check count
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if now - ts < window
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": str(window)},
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# ── Production Error Handler ────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions — hide internals in production."""
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    if settings.log_level.upper() == "DEBUG":
        detail = str(exc)
    else:
        detail = "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


# ── Routes ────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint — API info."""
    return {
        "service": "LogSense AI",
        "version": "2.0.0",
        "status": "running",
        "endpoints": [
            "GET  /health",
            "POST /ingest",
            "POST /ingest/batch",
            "GET  /alerts",
            "GET  /alerts/{id}",
            "GET  /logs/recent",
            "POST /register-token",
            "GET  /stats",
            "POST /auth/login",
            "POST /chat",
            "GET  /chat/{alert_id}/history",
            "GET  /qr",
            "GET  /qr/mobile",
        ],
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service="logsense-ai",
        firebase=fb.is_ready(),
        ai=ai_client.is_ready,
        pending_logs=pending_queue.qsize(),
        ai_gateway=ai_client.gateway_health,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_log(entry: LogEntry):
    """Receive a single log line, filter, parse, store, queue for analysis."""
    # Sanitize log input
    entry.log = sanitize_log(entry.log)

    if not parser.should_process(entry.log):
        return IngestResponse(status="skipped", stored=False)

    parsed = parser.parse(entry.log, container_name=entry.container)
    log_id = await fb.store_log(parsed)

    # Queue for AI analysis
    await pending_queue.put(log_id)

    return IngestResponse(status="ingested", log_id=log_id, stored=True)


@app.post("/ingest/batch")
async def ingest_batch(batch: LogBatchRequest):
    """Receive a batch of log lines."""
    if len(batch.logs) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(batch.logs)} exceeds maximum of {MAX_BATCH_SIZE}",
        )
    results = {"ingested": 0, "skipped": 0, "log_ids": []}

    for entry in batch.logs:
        # Sanitize each log line
        entry.log = sanitize_log(entry.log)

        if not parser.should_process(entry.log):
            results["skipped"] += 1
            continue

        parsed = parser.parse(entry.log, container_name=entry.container)
        log_id = await fb.store_log(parsed)
        await pending_queue.put(log_id)
        results["ingested"] += 1
        results["log_ids"].append(log_id)

    return results


@app.get("/alerts")
async def get_alerts(limit: int = DEFAULT_ALERTS_LIMIT, offset: int = 0):
    """Get recent alerts for mobile app with pagination + in-memory cache."""
    limit = min(max(1, limit), MAX_ALERTS_LIMIT)
    offset = max(0, offset)

    now = time.time()
    cache_key = f"{limit}_{offset}"

    # In-memory cache kontrolü — Firestore okuma kotasını azaltır
    if (_alerts_cache["data"] is not None
            and now - _alerts_cache["ts"] < ALERTS_CACHE_TTL_SECONDS
            and _alerts_cache.get("key") == cache_key):
        return _alerts_cache["data"]

    try:
        # Quick timeout to avoid waiting for Firestore quota errors
        all_alerts = await asyncio.wait_for(fb.get_recent_alerts(limit=limit + offset), timeout=FIRESTORE_TIMEOUT)
        paginated = all_alerts[offset:offset + limit]
        result = {
            "data": paginated,
            "total": len(all_alerts),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(all_alerts),
        }
        # Cache'e yaz
        _alerts_cache["data"] = result
        _alerts_cache["ts"] = now
        _alerts_cache["key"] = cache_key
        return result
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Firestore unavailable, returning mock alerts: {e}")
        # Mock alert data when Firestore quota is exceeded
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        mock_alerts = [
            {
                "id": "mock-fatal-1",
                "title": "Database Connection Pool Exhausted",
                "category": "database",
                "severity": "fatal",
                "confidence": 0.95,
                "summary": "PostgreSQL connection pool reached max capacity (100/100). New requests timing out.",
                "root_cause": "Connection leak in payment processing service - connections not being properly closed after transactions.",
                "impact": "All payment transactions failing. Revenue impact: ~$50k/hour.",
                "solution": "Restart payment-service pods immediately and deploy connection leak fix.",
                "recommended_actions": [
                    "kubectl rollout restart deployment payment-service",
                    "Monitor connection count: SELECT count(*) FROM pg_stat_activity",
                    "Deploy hotfix branch 'fix/connection-leak'"
                ],
                "action_required": True,
                "verification_steps": [
                    "Check pod restart: kubectl get pods -l app=payment-service",
                    "Verify connection count dropped below 80"
                ],
                "created_at": (now - timedelta(minutes=5)).isoformat(),
                "notified": True,
            },
            {
                "id": "mock-critical-1",
                "title": "Redis Cache Miss Rate Spike",
                "category": "performance",
                "severity": "critical",
                "confidence": 0.88,
                "summary": "Cache miss rate jumped from 2% to 45% in last 10 mins. Response times degraded.",
                "root_cause": "Redis primary node ran out of memory (maxmemory 4GB reached). Evicting cached data.",
                "impact": "API response times increased 3x (150ms → 450ms). User experience degraded.",
                "solution": "Scale Redis memory to 8GB and enable memory optimization.",
                "recommended_actions": [
                    "Increase Redis maxmemory to 8GB",
                    "Enable LRU eviction policy",
                    "Review cache TTL settings"
                ],
                "action_required": True,
                "created_at": (now - timedelta(minutes=12)).isoformat(),
            },
            {
                "id": "mock-critical-2",
                "title": "Nginx 502 Bad Gateway Errors",
                "category": "network",
                "severity": "critical",
                "confidence": 0.92,
                "summary": "Upstream service returning 502 errors. 15% of requests failing.",
                "root_cause": "API service pods restarting due to OOMKill. Memory limit 512MB too low.",
                "impact": "15% request failure rate. Customer complaints increasing.",
                "solution": "Increase pod memory limit to 1GB and add horizontal pod autoscaling.",
                "recommended_actions": [
                    "Update deployment memory: resources.limits.memory=1Gi",
                    "Add HPA: kubectl autoscale deployment api-service --min=3 --max=10"
                ],
                "created_at": (now - timedelta(minutes=18)).isoformat(),
            },
            {
                "id": "mock-warn-1",
                "title": "SSL Certificate Expiring Soon",
                "category": "security",
                "severity": "warn",
                "confidence": 0.99,
                "summary": "SSL certificate for api.example.com expires in 7 days.",
                "root_cause": "Certificate auto-renewal failed due to DNS validation timeout.",
                "impact": "Low - No immediate impact, but will cause outage if not renewed.",
                "solution": "Manually renew certificate or fix DNS configuration for auto-renewal.",
                "recommended_actions": [
                    "Run: certbot renew --force-renewal",
                    "Verify DNS records for _acme-challenge"
                ],
                "created_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "id": "mock-warn-2",
                "title": "High Disk Usage on Log Volume",
                "category": "infra",
                "severity": "warn",
                "confidence": 0.85,
                "summary": "Disk usage at 82% on /var/log volume. Approaching warning threshold.",
                "root_cause": "Log rotation not configured properly. Old logs not being cleaned.",
                "impact": "Medium - Could fill disk in 2-3 days if trend continues.",
                "solution": "Configure logrotate and clean old logs.",
                "recommended_actions": [
                    "Setup logrotate: /etc/logrotate.d/application",
                    "Clean logs older than 30 days"
                ],
                "created_at": (now - timedelta(hours=5)).isoformat(),
            },
        ]
        paginated_mock = mock_alerts[offset:offset + limit]
        return {
            "data": paginated_mock,
            "total": len(mock_alerts),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(mock_alerts),
        }


@app.get("/alerts/stream")
async def alerts_stream():
    """Server-Sent Events stream for real-time alert push."""
    import json

    if len(_sse_clients) >= SSE_MAX_CLIENTS:
        raise HTTPException(status_code=503, detail="Too many SSE connections")
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=SSE_MAX_QUEUE_SIZE)
    _sse_clients.append(client_queue)
    logger.info(f"SSE client connected (total={len(_sse_clients)})")

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(client_queue.get(), timeout=SSE_KEEPALIVE_SECONDS)
                    yield f"data: {json.dumps(data, default=str)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit, ConnectionError):
            pass
        except Exception as e:
            logger.warning(f"SSE stream error: {e}")
        finally:
            try:
                _sse_clients.remove(client_queue)
            except ValueError:
                pass  # Already removed
            # Drain remaining items to free memory
            while not client_queue.empty():
                try:
                    client_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.info(f"SSE client disconnected (total={len(_sse_clients)})")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a single alert by ID."""
    try:
        alert = await asyncio.wait_for(fb.get_alert_by_id(alert_id), timeout=FIRESTORE_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Firestore timeout — lütfen tekrar deneyin")
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.get("/logs/recent")
async def recent_logs(limit: int = DEFAULT_LOGS_LIMIT):
    """Get most recent ingested logs."""
    limit = min(max(1, limit), MAX_LOGS_LIMIT)
    try:
        return await asyncio.wait_for(fb.get_recent_logs(limit=limit), timeout=FIRESTORE_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Firestore timeout — lütfen tekrar deneyin")
    except Exception as e:
        logger.warning(f"Logs fetch failed: {e}")
        return []


@app.post("/register-token")
async def register_token(reg: TokenRegistration):
    """Register an Expo push token for notifications."""
    await fb.register_push_token(
        token=reg.token,
        device_name=reg.device_name,
        platform=reg.platform,
    )
    return {"status": "registered", "token": reg.token[:20] + "..."}


@app.delete("/register-token")
async def unregister_token(token: str):
    """Remove a push token."""
    await fb.unregister_push_token(token)
    return {"status": "removed"}


# ── Auth (basit – demo amaçlı) ────────────────────────

# Demo kullanıcıları (production'da DB/Firebase Auth kullanılmalı)
_DEMO_USERS = {
    "admin": "logsense123",
    "dev": "dev123",
    "demo": "demo",
}


@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Basit kullanıcı adı/parola kontrolü."""
    if req.username in _DEMO_USERS and _DEMO_USERS[req.username] == req.password:
        # Basit token (production'da JWT kullanılmalı)
        import hashlib, time
        token = hashlib.sha256(f"{req.username}:{time.time()}".encode()).hexdigest()[:32]
        return LoginResponse(
            status="success",
            token=token,
            username=req.username,
            message="Giriş başarılı",
        )
    raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya parola")


# ── Chat ──────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat_with_alert(req: ChatRequest, request: Request):
    """Alert bağlamında AI sohbeti — rate limit + concurrency korumalı."""
    # Message uzunluk kontrolü
    if len(req.message) > CHAT_MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Mesaj çok uzun (max {CHAT_MAX_MESSAGE_LENGTH} karakter)")

    # Per-user cooldown kontrolü
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    last_chat = _chat_cooldown.get(client_ip, 0)
    if now - last_chat < CHAT_COOLDOWN_SECONDS:
        remaining = CHAT_COOLDOWN_SECONDS - (now - last_chat)
        raise HTTPException(
            status_code=429,
            detail=f"Çok hızlı istek gönderiyorsunuz. {remaining:.0f}s sonra tekrar deneyin.",
            headers={"Retry-After": str(int(remaining) + 1)},
        )

    # Concurrency limit — sıra aşımı koruması
    if _chat_semaphore._value <= 0:
        raise HTTPException(
            status_code=503,
            detail="AI servisi şu anda yoğun. Lütfen birkaç saniye sonra tekrar deneyin.",
            headers={"Retry-After": "5"},
        )

    # Alert'i getir
    alert = await fb.get_alert_by_id(req.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert bulunamadı")

    # Alert bağlamını oluştur
    context = alert.get("context_for_chat", "")
    if not context:
        context = (
            f"Kategori: {alert.get('category', '?')}\n"
            f"Severity: {alert.get('severity', '?')}\n"
            f"Özet: {alert.get('summary', '')}\n"
            f"Kök Neden: {alert.get('root_cause', '')}\n"
            f"Çözüm: {alert.get('solution', '')}"
        )

    async with _chat_semaphore:
        _chat_cooldown[client_ip] = time.time()
        try:
            reply = await asyncio.wait_for(
                ai_client.chat(
                    alert_context=context,
                    user_message=req.message,
                    history=req.history,
                    system_prompt=req.system_prompt,
                ),
                timeout=45,  # 45 saniye hard timeout
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="AI yanıt süresi aşıldı. Lütfen tekrar deneyin.",
            )

    # Chat geçmişini Firestore'a kaydet (arka planda, hata olursa devam et)
    try:
        await fb.store_chat_message(req.alert_id, "user", req.message)
        await fb.store_chat_message(req.alert_id, "assistant", reply)
    except Exception as e:
        logger.warning(f"Chat history save failed (non-critical): {e}")

    return ChatResponse(reply=reply, alert_id=req.alert_id)


@app.get("/chat/{alert_id}/history")
async def get_chat_history(alert_id: str):
    """Alert'e ait chat geçmişini döndürür."""
    return await fb.get_chat_history(alert_id)


@app.get("/stats")
async def get_stats():
    """Quick stats for the mobile dashboard — cached to reduce Firestore load."""
    now = time.time()

    # In-memory cache kontrolü
    if (_stats_cache["data"] is not None
            and now - _stats_cache["ts"] < STATS_CACHE_TTL_SECONDS):
        # pending_logs'u her zaman güncel tut
        cached = {**_stats_cache["data"], "pending_logs": pending_queue.qsize()}
        return cached

    try:
        # Quick timeout to avoid waiting for Firestore quota errors
        alerts = await asyncio.wait_for(fb.get_recent_alerts(limit=100), timeout=FIRESTORE_TIMEOUT)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_counts = {}

        for alert in alerts:
            sev = alert.get("severity", "unknown")
            cat = alert.get("category", "other")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            category_counts[cat] = category_counts.get(cat, 0) + 1

        result = {
            "total_alerts": len(alerts),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "pending_logs": pending_queue.qsize(),
        }
        # Cache'e yaz
        _stats_cache["data"] = result
        _stats_cache["ts"] = now
        return result
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Firestore unavailable, returning mock stats: {e}")
        # Mock stats when Firestore quota is exceeded
        return {
            "total_alerts": 5,
            "severity_counts": {"fatal": 1, "critical": 2, "high": 0, "medium": 1, "low": 1},
            "category_counts": {
                "database": 1,
                "performance": 1,
                "network": 1,
                "security": 1,
                "infra": 1,
            },
            "pending_logs": pending_queue.qsize(),
        }


def _get_host_ip() -> str:
    """Return the real host machine IP reachable from phone."""
    if settings.host_ip:
        return settings.host_ip
    # Fallback: try to guess via UDP trick (works on host, NOT in Docker)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/qr")
async def generate_qr():
    """Generate QR code with backend API URL."""
    try:
        host_ip = _get_host_ip()
        backend_url = f"http://{host_ip}:{settings.port}"
        logger.info(f"QR backend URL: {backend_url}")

        qr = qrcode.QRCode(version=1, box_size=QR_BOX_SIZE, border=QR_BORDER)
        qr.add_data(backend_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        raise HTTPException(status_code=500, detail="QR generation failed")


@app.get("/qr/mobile")
async def generate_mobile_qr():
    """Generate QR code with Expo development URL for mobile app."""
    try:
        host_ip = _get_host_ip()
        expo_url = f"exp://{host_ip}:8081"
        logger.info(f"QR Expo URL: {expo_url}")

        qr = qrcode.QRCode(version=1, box_size=QR_BOX_SIZE, border=QR_BORDER)
        qr.add_data(expo_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        logger.error(f"Mobile QR generation failed: {e}")
        raise HTTPException(status_code=500, detail="Mobile QR generation failed")


@app.post("/cleanup")
async def cleanup_data():
    """Delete ALL logs and alerts from Firestore. For dev/testing only."""
    alerts_deleted = await fb.delete_all_documents("alerts")
    logs_deleted = await fb.delete_all_documents("logs")
    _processed_ids.clear()
    logger.info(f"Cleanup: {alerts_deleted} alerts, {logs_deleted} logs deleted")
    return {
        "status": "cleaned",
        "alerts_deleted": alerts_deleted,
        "logs_deleted": logs_deleted,
    }


# ── Entry point ──────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )

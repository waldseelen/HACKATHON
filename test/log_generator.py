"""
LogSense AI – Test Log Generator
==================================
Generates realistic error/warning logs and sends them to the
Log Ingestion service via HTTP POST.

Usage:
  LOGS_PER_SECOND=10 INGESTION_URL=http://log-ingestion:8000 python log_generator.py
"""

import asyncio
import os
import random
import time
from datetime import datetime, timezone

import httpx

INGESTION_URL = os.getenv("INGESTION_URL", "http://log-ingestion:8000")
LOGS_PER_SECOND = int(os.getenv("LOGS_PER_SECOND", "10"))

# ── Realistic log templates ──────────────────────────────

ERROR_TEMPLATES = [
    # Database
    "ERROR: Database connection timeout after {num}s (host=db-prod-{num2}, pool=exhausted)",
    "FATAL: Deadlock detected in transaction {uuid} on table 'orders'",
    "ERROR: Query failed: SELECT * FROM users WHERE id={num} — relation does not exist",
    "ERROR: PostgreSQL connection pool exhausted (active={num}, max=20)",
    "WARN: Slow query detected: UPDATE inventory SET stock=stock-1 took {num}ms",
    # Network
    "ERROR: Connection refused to upstream service auth-service:8080",
    "ERROR: HTTP 503 Service Unavailable from payment-gateway after {num} retries",
    "WARN: Request timeout after {num}s — GET /api/v2/products",
    "ERROR: DNS resolution failed for cache.internal.svc.cluster.local",
    "WARN: TLS handshake timeout connecting to external-api.example.com:{num2}",
    # Memory / Crash
    "FATAL: Out of memory error — killed process PID {num} (RSS={num2}MB)",
    "ERROR: Java heap space exhausted: java.lang.OutOfMemoryError",
    "WARN: Container memory usage at {num}% of limit (512Mi)",
    "ERROR: Segmentation fault in worker thread {num}",
    # Auth
    "ERROR: Invalid JWT token — signature verification failed for user {uuid}",
    "WARN: Failed login attempt #{num} from IP {ip} — account locked",
    "ERROR: OAuth2 token expired for service-account-{num}",
    # Performance
    "WARN: High CPU usage detected: {num}% on node worker-{num2}",
    "WARN: Event loop blocked for {num}ms in handler /api/search",
    "ERROR: Request queue full — dropping incoming requests (queue={num})",
    # Security
    "WARN: Potential SQL injection attempt detected in parameter 'id'={num}",
    "ERROR: Rate limit exceeded for API key sk-{uuid} ({num} requests/min)",
    # Config
    "ERROR: Missing required environment variable STRIPE_SECRET_KEY",
    "WARN: Config file /etc/app/config.yaml not found — using defaults",
    "ERROR: Invalid REDIS_URL format: expected redis://host:port",
]

SERVICES = [
    "nginx", "api-gateway", "auth-service", "payment-service",
    "user-service", "order-service", "notification-service",
    "postgres", "search-service", "worker",
]


def _random_ip():
    return f"{random.randint(10,192)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _random_uuid():
    import uuid
    return str(uuid.uuid4())[:8]


def generate_log_line() -> tuple[str, str]:
    """Return (log_line, service_name)."""
    template = random.choice(ERROR_TEMPLATES)
    service = random.choice(SERVICES)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] {service}: {template.format(num=random.randint(1, 999), num2=random.randint(1, 100), uuid=_random_uuid(), ip=_random_ip())}"
    return line, service


async def run_generator():
    interval = 1.0 / LOGS_PER_SECOND
    url = f"{INGESTION_URL}/ingest"

    print(f"🚀 Log Generator started")
    print(f"   Target: {url}")
    print(f"   Rate:   {LOGS_PER_SECOND} logs/sec")
    print()

    total_sent = 0
    total_errors = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Wait for ingestion service to be ready
        for attempt in range(30):
            try:
                r = await client.get(f"{INGESTION_URL}/health")
                if r.status_code == 200:
                    print(f"✓ Ingestion service is healthy")
                    break
            except Exception:
                pass
            print(f"  Waiting for ingestion service… ({attempt + 1}/30)")
            await asyncio.sleep(2)
        else:
            print("✗ Ingestion service not available after 60s")
            return

        print(f"\n--- Generating logs ---\n")

        while True:
            log_line, service = generate_log_line()

            try:
                response = await client.post(
                    url,
                    json={
                        "log": log_line,
                        "source": "test-generator",
                        "container": f"{service}-1",
                    },
                )
                total_sent += 1

                if total_sent % 50 == 0:
                    print(
                        f"  [{datetime.now().strftime('%H:%M:%S')}] "
                        f"Sent: {total_sent} | Errors: {total_errors} | "
                        f"Last: {response.json().get('status', '?')}"
                    )

            except Exception as e:
                total_errors += 1
                if total_errors % 10 == 1:
                    print(f"  ✗ Send error: {e}")

            await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        asyncio.run(run_generator())
    except KeyboardInterrupt:
        print("\nGenerator stopped")

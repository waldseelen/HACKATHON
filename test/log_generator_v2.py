"""
LogSense AI – Test Log Generator
==================================
Generates realistic error/warning logs and POSTs them to the backend.
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timezone

import httpx

INGESTION_URL = os.getenv("INGESTION_URL", "http://backend:8000")
LOGS_PER_SECOND = int(os.getenv("LOGS_PER_SECOND", "2"))

ERROR_TEMPLATES = [
    # Database
    "ERROR: Database connection timeout after {num}s (host=db-prod-{num2}, pool=exhausted)",
    "FATAL: Deadlock detected in transaction {uuid} on table 'orders'",
    "ERROR: PostgreSQL connection pool exhausted (active={num}, max=20)",
    "WARN: Slow query detected: UPDATE inventory SET stock=stock-1 took {num}ms",
    # Network
    "ERROR: Connection refused to upstream service auth-service:8080",
    "ERROR: HTTP 503 Service Unavailable from payment-gateway after {num} retries",
    "WARN: Request timeout after {num}s — GET /api/v2/products",
    "ERROR: DNS resolution failed for cache.internal.svc.cluster.local",
    # Crash
    "FATAL: Out of memory error — killed process PID {num} (RSS={num2}MB)",
    "ERROR: Java heap space exhausted: java.lang.OutOfMemoryError",
    "WARN: Container memory usage at {num}% of limit (512Mi)",
    # Auth
    "ERROR: Invalid JWT token — signature verification failed for user {uuid}",
    "WARN: Failed login attempt #{num} from IP {ip} — account locked",
    # Performance
    "WARN: High CPU usage detected: {num}% on node worker-{num2}",
    "WARN: Event loop blocked for {num}ms in handler /api/search",
    # Security
    "WARN: Potential SQL injection attempt detected in parameter 'id'={num}",
    "ERROR: Rate limit exceeded for API key sk-{uuid} ({num} requests/min)",
    # Config
    "ERROR: Missing required environment variable STRIPE_SECRET_KEY",
    "WARN: Config file /etc/app/config.yaml not found — using defaults",
]

SERVICES = [
    "nginx", "api-gateway", "auth-service", "payment-service",
    "user-service", "order-service", "search-service", "worker",
]


def random_ip():
    return f"{random.randint(10,192)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def generate_log():
    template = random.choice(ERROR_TEMPLATES)
    service = random.choice(SERVICES)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] {service}: {template.format(num=random.randint(1, 999), num2=random.randint(1, 100), uuid=str(uuid.uuid4())[:8], ip=random_ip())}"
    return line, service


async def main():
    interval = 1.0 / LOGS_PER_SECOND
    url = f"{INGESTION_URL}/ingest"

    print(f"Log Generator started")
    print(f"  Target: {url}")
    print(f"  Rate:   {LOGS_PER_SECOND} logs/sec")

    # Wait for backend to be ready
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(30):
            try:
                r = await client.get(f"{INGESTION_URL}/health")
                if r.status_code == 200:
                    print("Backend is ready!")
                    break
            except Exception:
                pass
            print(f"  Waiting for backend... ({attempt + 1}/30)")
            await asyncio.sleep(2)
        else:
            print("Backend not reachable after 60s, starting anyway...")

    # Generate logs
    total = 0
    errors = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            log_line, service = generate_log()

            try:
                response = await client.post(url, json={
                    "log": log_line,
                    "source": "test-generator",
                    "container": f"{service}-1",
                })
                if response.status_code == 200:
                    total += 1
                    data = response.json()
                    if data.get("stored"):
                        print(f"  [{total}] {data.get('status')}: {log_line[:80]}")
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                if errors % 10 == 0:
                    print(f"  Error: {e}")

            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())

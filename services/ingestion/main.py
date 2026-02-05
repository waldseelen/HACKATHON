"""
LogSense AI - Log Ingestion Service
====================================
FastAPI service that:
  1. Receives logs via POST /ingest endpoint
  2. Streams Docker container logs (ERROR/WARN only)
  3. Normalizes and publishes to RabbitMQ
  4. Stores raw logs in PostgreSQL
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import aio_pika
import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from log_parser import LogParser
from rabbitmq_client import RabbitMQPublisher

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_user: str = "logsense"
    rabbitmq_password: str = "changeme"
    postgres_host: str = "postgres"
    postgres_db: str = "logsense"
    postgres_user: str = "logsense"
    postgres_password: str = "changeme"
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ingestion")

# ── Shared state ──────────────────────────────────────────

rabbitmq: Optional[RabbitMQPublisher] = None
db_pool: Optional[asyncpg.Pool] = None
docker_task: Optional[asyncio.Task] = None

# ── Lifespan ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rabbitmq, db_pool, docker_task

    # Startup
    logger.info("Connecting to RabbitMQ…")
    rabbitmq = RabbitMQPublisher(
        host=settings.rabbitmq_host,
        user=settings.rabbitmq_user,
        password=settings.rabbitmq_password,
    )
    await rabbitmq.connect()

    logger.info("Connecting to PostgreSQL…")
    db_pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=2,
        max_size=10,
    )

    # Start background Docker log streamer
    docker_task = asyncio.create_task(stream_docker_logs())

    logger.info("✓ Ingestion service ready")
    yield

    # Shutdown
    if docker_task:
        docker_task.cancel()
    if db_pool:
        await db_pool.close()
    if rabbitmq:
        await rabbitmq.close()
    logger.info("Ingestion service stopped")


app = FastAPI(
    title="LogSense AI – Log Ingestion",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Request / Response models ─────────────────────────────

class LogEntry(BaseModel):
    log: str
    source: str = "api"
    container: str = "unknown"
    timestamp: Optional[str] = None

class LogBatchRequest(BaseModel):
    logs: list[LogEntry]

class IngestResponse(BaseModel):
    status: str
    log_id: Optional[int] = None
    queued: bool = False

# ── Routes ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "log-ingestion",
        "rabbitmq": rabbitmq is not None and rabbitmq.connected,
        "postgres": db_pool is not None,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_log(entry: LogEntry):
    """Receive a single log line, filter/parse, store and queue."""
    parser = LogParser()

    if not parser.should_process(entry.log):
        return IngestResponse(status="skipped", queued=False)

    parsed = parser.parse(entry.log, container_name=entry.container)

    # Store in PostgreSQL
    log_id = await _store_log(parsed)
    parsed["log_id"] = log_id

    # Publish to RabbitMQ
    await rabbitmq.publish_log(parsed)

    return IngestResponse(status="ingested", log_id=log_id, queued=True)


@app.post("/ingest/batch")
async def ingest_batch(batch: LogBatchRequest):
    """Receive a batch of log lines."""
    parser = LogParser()
    results = {"ingested": 0, "skipped": 0}

    for entry in batch.logs:
        if not parser.should_process(entry.log):
            results["skipped"] += 1
            continue

        parsed = parser.parse(entry.log, container_name=entry.container)
        log_id = await _store_log(parsed)
        parsed["log_id"] = log_id
        await rabbitmq.publish_log(parsed)
        results["ingested"] += 1

    return results


@app.get("/logs/recent")
async def recent_logs(limit: int = 20):
    """Get most recent ingested logs."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, ingested_at, container_name, service_name,
                   severity, LEFT(raw_log, 200) AS raw_log_preview
            FROM logs
            ORDER BY ingested_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


@app.get("/alerts")
async def get_alerts(limit: int = 20):
    """Get most recent alerts from AI analysis."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, created_at, category, severity, confidence,
                   summary, root_cause, solution, action_required,
                   notification_count
            FROM alerts
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]

# ── Helpers ───────────────────────────────────────────────

async def _store_log(parsed: dict) -> int:
    """Insert a parsed log into PostgreSQL and return its id."""
    async with db_pool.acquire() as conn:
        log_id = await conn.fetchval(
            """
            INSERT INTO logs (container_name, service_name, severity,
                              raw_log, normalized, fingerprint)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            parsed["container"],
            parsed["service"],
            parsed["severity"],
            parsed["raw_log"],
            json.dumps(parsed),
            parsed.get("fingerprint"),
        )
    return log_id

# ── Docker log streamer (background) ─────────────────────

async def stream_docker_logs():
    """Stream logs from all running Docker containers (best-effort)."""
    try:
        import aiodocker

        docker = aiodocker.Docker()
        parser = LogParser()
        logger.info("Docker log streamer started")

        while True:
            try:
                containers = await docker.containers.list()
                logger.info(f"Streaming logs from {len(containers)} containers")

                async def _stream_one(container):
                    info = await container.show()
                    name = info["Name"].lstrip("/")

                    # Skip our own infrastructure containers
                    if name.startswith("logsense-"):
                        return

                    try:
                        async for line in container.log(
                            stdout=True, stderr=True, follow=True, tail=10
                        ):
                            if parser.should_process(line):
                                parsed = parser.parse(line, container_name=name)
                                log_id = await _store_log(parsed)
                                parsed["log_id"] = log_id
                                await rabbitmq.publish_log(parsed)
                    except Exception as e:
                        logger.warning(f"Stream error [{name}]: {e}")

                await asyncio.gather(
                    *[_stream_one(c) for c in containers],
                    return_exceptions=True,
                )

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Docker streamer error: {e}")
                await asyncio.sleep(10)

    except ImportError:
        logger.warning("aiodocker not available – Docker streaming disabled")
    except asyncio.CancelledError:
        logger.info("Docker log streamer stopped")
    except Exception as e:
        logger.error(f"Docker streamer fatal: {e}")

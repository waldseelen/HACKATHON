"""
LogSense AI - Log Ingestion Service (Firebase Edition)
=======================================================
FastAPI service that:
  1. Receives logs via POST /ingest endpoint
  2. Streams Docker container logs (ERROR/WARN only)
  3. Normalizes and stores to Firebase Firestore
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from log_parser import LogParser

# ── Settings ──────────────────────────────────────────────

class Settings(BaseSettings):
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    firebase_project_id: str = "montgomery-415113"
    log_level: str = "INFO"

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ingestion")

# ── Shared state ──────────────────────────────────────────

db: Optional[firestore.AsyncClient] = None
docker_task: Optional[asyncio.Task] = None

# ── Lifespan ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, docker_task

    # Startup
    logger.info("Initializing Firebase...")
    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred, {
            'projectId': settings.firebase_project_id,
        })
        db = firestore.AsyncClient()
        logger.info("✓ Firebase Firestore connected")
    except Exception as e:
        logger.error(f"✗ Firebase initialization failed: {e}")
        raise

    # Start background Docker log streamer
    docker_task = asyncio.create_task(stream_docker_logs())

    logger.info("✓ Ingestion service ready")
    yield

    # Shutdown
    if docker_task:
        docker_task.cancel()
    logger.info("Ingestion service stopped")


app = FastAPI(
    title="LogSense AI – Log Ingestion (Firebase)",
    version="0.2.0",
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
    log_id: Optional[str] = None
    stored: bool = False

# ── Routes ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "log-ingestion-firebase",
        "firestore": db is not None,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_log(entry: LogEntry):
    """Receive a single log line, filter/parse, store in Firestore."""
    parser = LogParser()

    if not parser.should_process(entry.log):
        return IngestResponse(status="skipped", stored=False)

    parsed = parser.parse(entry.log, container_name=entry.container)

    # Store in Firestore
    log_id = await _store_log(parsed)

    return IngestResponse(status="ingested", log_id=log_id, stored=True)


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
        await _store_log(parsed)
        results["ingested"] += 1

    return results


@app.get("/logs/recent")
async def recent_logs(limit: int = 20):
    """Get most recent ingested logs from Firestore."""
    logs_ref = db.collection('logs').order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
    docs = await logs_ref.get()

    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.get("/alerts")
async def get_alerts(limit: int = 20):
    """Get most recent alerts from AI analysis."""
    alerts_ref = db.collection('alerts').order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
    docs = await alerts_ref.get()

    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

# ── Helpers ───────────────────────────────────────────────

async def _store_log(parsed: dict) -> str:
    """Insert a parsed log into Firestore and return its document ID."""
    log_doc = {
        "container": parsed["container"],
        "service": parsed["service"],
        "severity": parsed["severity"],
        "raw_log": parsed["raw_log"],
        "normalized": json.dumps(parsed),
        "fingerprint": parsed.get("fingerprint"),
        "created_at": firestore.SERVER_TIMESTAMP,
        "processed": False,  # AI analysis flag
    }

    _, doc_ref = await db.collection('logs').add(log_doc)
    logger.debug(f"Stored log: {doc_ref.id}")
    return doc_ref.id

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
                                await _store_log(parsed)
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

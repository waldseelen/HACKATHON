# 🧠 LogSense AI

Real-time container log analysis powered by **Google Gemini AI**. Automatically categorizes errors, diagnoses root causes, recommends solutions, and sends push notifications to developers.

## Architecture

```
┌─────────────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Docker Containers  │────▶│ RabbitMQ     │────▶│  Alert Composer  │
│  (stdout/stderr)    │     │              │     │  (FCM + Kuma)    │
└────────┬────────────┘     └──────┬───────┘     └────────┬─────────┘
         │                         │                      │
         ▼                         ▼                      ▼
┌─────────────────────┐     ┌──────────────┐     ┌────────────────┐
│  Log Ingestion      │     │ AI Analysis  │     │  📱 Mobile App │
│  (FastAPI)          │     │ (Gemini 2.0) │     │  Push Alerts   │
└─────────────────────┘     └──────────────┘     └────────────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │ PostgreSQL   │
                            │ (logs+alerts)│
                            └──────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Log Ingestion** | 8000 | FastAPI – receives logs, filters ERROR/WARN, queues to RabbitMQ |
| **AI Analysis** | — | Consumes queue → Gemini AI categorization + root cause analysis |
| **Alert Composer** | 8001 | Dispatches FCM push notifications + Uptime Kuma webhooks |
| **Dozzle** | 8080 | Real-time Docker log viewer UI |
| **Uptime Kuma** | 3001 | Uptime monitoring dashboard |
| **Grafana** | 3000 | Metrics & alert dashboards |
| **RabbitMQ** | 15672 | Message queue management UI |
| **PostgreSQL** | 5432 | Log & alert storage |

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Google Gemini API key → [Get one here](https://aistudio.google.com/apikey)
- (Optional) Firebase project for push notifications

### 2. Setup

```bash
cd logsense-ai

# Copy and edit environment variables
cp .env.example .env
# Edit .env → set GEMINI_API_KEY at minimum
```

### 3. Start

```bash
# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f ai-analysis alert-composer
```

### 4. Test

```bash
# Start the test log generator (10 logs/second)
docker-compose --profile test up log-generator

# Or send a single log manually
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "log": "[2026-02-05 10:30:15] ERROR api-gateway: Database connection timeout after 30s",
    "source": "manual",
    "container": "api-gateway-1"
  }'
```

### 5. View Results

```bash
# Recent alerts (AI analysis results)
curl http://localhost:8000/alerts | python -m json.tool

# Recent raw logs
curl http://localhost:8000/logs/recent | python -m json.tool

# Or query PostgreSQL directly
docker exec -it logsense-postgres psql -U logsense -d logsense -c \
  "SELECT id, category, severity, confidence, summary FROM alerts ORDER BY created_at DESC LIMIT 5;"
```

## API Endpoints

### Log Ingestion (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Submit a single log entry |
| `POST` | `/ingest/batch` | Submit multiple log entries |
| `GET` | `/logs/recent` | Get recent ingested logs |
| `GET` | `/alerts` | Get recent AI analysis alerts |
| `GET` | `/health` | Service health check |

### Request: POST /ingest

```json
{
  "log": "[2026-02-05 14:23:45] ERROR api-gateway: Connection pool exhausted",
  "source": "fluentbit",
  "container": "api-gateway-1"
}
```

### Response

```json
{
  "status": "ingested",
  "log_id": 42,
  "queued": true
}
```

### Alert Format (AI Analysis Output)

```json
{
  "id": "a1b2c3d4-...",
  "category": "database",
  "severity": "high",
  "confidence": 0.92,
  "summary": "Database connection pool exhausted due to query backlog",
  "root_cause": "Slow queries are holding connections longer than expected, causing the pool to fill up. The max pool size (20) is insufficient for current traffic.",
  "solution": "Immediate: Restart the service to reset connections. Long-term: Optimize slow queries, increase pool size to 50, add connection timeout.",
  "action_required": true
}
```

## Monitoring

- **Dozzle**: http://localhost:8080 — Live container log viewer
- **Uptime Kuma**: http://localhost:3001 — Service uptime monitoring
- **Grafana**: http://localhost:3000 — Custom dashboards (admin/admin)
- **RabbitMQ**: http://localhost:15672 — Queue management (logsense/password)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `RABBITMQ_PASSWORD` | ✅ | RabbitMQ password |
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL password |
| `UPTIME_KUMA_WEBHOOK_URL` | ❌ | Uptime Kuma Push Monitor URL |
| `FIREBASE_CREDENTIALS_PATH` | ❌ | Path to Firebase service account JSON |
| `GRAFANA_PASSWORD` | ❌ | Grafana admin password (default: admin) |

## Project Structure

```
logsense-ai/
├── docker-compose.yml          # All services orchestration
├── .env.example                # Environment template
├── database/
│   └── init.sql                # PostgreSQL schema
├── services/
│   ├── ingestion/              # Log Ingestion Service
│   │   ├── main.py             # FastAPI app + Docker log streamer
│   │   ├── log_parser.py       # Parsing + filtering + fingerprinting
│   │   └── rabbitmq_client.py  # RabbitMQ publisher
│   ├── ai-analysis/            # AI Analysis Service
│   │   ├── main.py             # RabbitMQ consumer + orchestrator
│   │   ├── gemini_client.py    # Gemini API client + fallback
│   │   ├── deduplication.py    # Log dedup + time-window batching
│   │   └── models.py           # Pydantic models
│   └── alert-composer/         # Alert Composer Service
│       ├── main.py             # RabbitMQ consumer + dispatcher
│       ├── fcm_client.py       # Firebase Cloud Messaging
│       └── uptime_kuma.py      # Uptime Kuma webhook
├── test/
│   ├── log_generator.py        # High-volume test log generator
│   └── Dockerfile.generator
└── grafana/
    └── dashboards/
```

## License

MIT

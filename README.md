# LogSense AI v2

Docker container log'larından ERROR/WARN yakalayıp, Deepseek AI ile analiz edip, Expo Go mobil uygulamaya push notification gönderen sistem.

## Mimari

```
┌─────────────────────┐     ┌────────────────────────┐     ┌──────────────┐
│  Docker Containers  │────▶│  Backend (FastAPI)      │────▶│  Firebase    │
│  (stdout/stderr)    │     │  • Log Ingestion        │     │  Firestore   │
└─────────────────────┘     │  • Deepseek AI Analysis   │     └──────┬───────┘
                            │  • Push Notification    │            │
       ┌───────────┐        └────────────────────────┘            │
       │ Test Gen  │────▶  POST /ingest                           │
       └───────────┘                                              ▼
                                                          ┌──────────────┐
                                                          │ Expo Push API│
                                                          └──────┬───────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │ 📱 Expo Go   │
                                                          │ Mobile App   │
                                                          └──────────────┘
```

## Hızlı Başlangıç

### 1. Backend (Docker)

```bash
# Backend'i başlat
docker compose up -d --build

# Log'ları izle
docker compose logs -f backend

# Test log generator'ı çalıştır
docker compose --profile test up -d
```

### 2. Mobil Uygulama (Expo Go)

```bash
cd mobile
npm install
npx expo start
```

Expo Go uygulamasını telefonuna indir, QR kodu tara.

### 3. Test İsteği Gönder

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "log": "[2026-02-06 10:30:15] ERROR api-gateway: Database connection timeout after 30s",
    "source": "manual",
    "container": "api-gateway-1"
  }'
```

## API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/health` | GET | Sistem sağlık kontrolü |
| `/ingest` | POST | Tek log gönder |
| `/ingest/batch` | POST | Toplu log gönder |
| `/alerts` | GET | Son alertleri listele (mobil için) |
| `/alerts/{id}` | GET | Alert detayı |
| `/logs/recent` | GET | Son loglar |
| `/register-token` | POST | Expo push token kaydet |
| `/stats` | GET | Dashboard istatistikleri |

## Gereksinimler

- Docker & Docker Compose
- Node.js 18+ (mobil için)
- Expo Go (telefon uygulaması)
- Gemini API Key
- Firebase projesi (Firestore + FCM)
- `alerts` collection - AI analysis results

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
  "log": "[2026-02-06 14:23:45] ERROR api-gateway: Connection pool exhausted",
  "source": "test",
  "container": "api-gateway-1"
}
```

### Response

```json
{
  "status": "ingested",
  "log_id": "abc123",
  "stored": true
}
```

### Alert Format (AI Analysis Output)

```json
{
  "id": "abc123",
  "category": "database",
  "severity": "high",
  "confidence": 0.92,
  "summary": "Database connection pool exhausted due to query backlog",
  "root_cause": "Slow queries holding connections, pool size insufficient.",
  "solution": "Restart service to reset. Long-term: optimize queries, increase pool.",
  "action_required": true
}
```

## Proje Yapısı

```
HACKATHON/
├── docker-compose.yml          # Tek backend + test generator
├── .env                        # Environment variables
├── firebase-credentials.json   # Firebase service account
├── backend/                    # FastAPI monolith
│   ├── main.py                 # API + background worker
│   ├── config.py               # Settings
│   ├── models.py               # Pydantic models
│   ├── log_parser.py           # Log parsing + fingerprinting
│   ├── firebase_service.py     # Firestore operations
│   ├── push_service.py         # Expo push notifications
│   ├── Dockerfile
│   └── requirements.txt
├── mobile/                     # Expo Go React Native app
│   ├── App.js                  # Entry point + navigation
│   ├── app.json                # Expo config
│   ├── package.json
│   └── src/
│       ├── screens/
│       │   ├── AlertsScreen.js
│       │   └── AlertDetailScreen.js
│       ├── components/
│       │   └── AlertCard.js
│       ├── services/
│       │   └── api.js
│       └── utils/
│           └── notifications.js
└── test/
    ├── log_generator_v2.py
    └── Dockerfile.v2
```

## License

MIT

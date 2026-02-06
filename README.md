# LogSense AI v2

Docker container log'larından ERROR/WARN yakalayıp, DeepSeek AI (OpenRouter) ile analiz edip, Next.js mobil web uygulamasına real-time push eden sistem.

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
| `/ingest/batch` | POST | Toplu log gönder (max 500) |
| `/alerts` | GET | Son alertleri listele (pagination destekli) |
| `/alerts/{id}` | GET | Alert detayı |
| `/alerts/stream` | GET | SSE real-time alert stream |
| `/logs/recent` | GET | Son loglar |
| `/register-token` | POST | Push token kaydet |
| `/stats` | GET | Dashboard istatistikleri |
| `/auth/login` | POST | Kullanıcı girişi |
| `/chat` | POST | Alert hakkında AI sohbet |
| `/chat/{id}/history` | GET | Sohbet geçmişi |
| `/qr` | GET | Backend URL QR kodu |
| `/docs` | GET | Swagger/OpenAPI dokümantasyonu |

## Gereksinimler

- Docker & Docker Compose
- Node.js 18+ (frontend geliştirme için)
- Firebase projesi (Firestore + FCM)
- OpenRouter API Key ([openrouter.ai](https://openrouter.ai))

## Güvenlik Özellikleri

- **Rate Limiting**: IP bazlı istek sınırlaması (100 req/dk)
- **Log Sanitization**: API key, token, şifre, JWT, kredi kartı gibi hassas verilerin otomatik maskelenmesi
- **CORS**: Yapılandırılabilir origin kısıtlaması
- **Error Boundary**: Frontend crash koruması
- **Production Error Handler**: Debug bilgilerinin production'da gizlenmesi

## Production Deployment

```bash
# Production config ile çalıştır
docker compose -f docker-compose.prod.yml up -d --build

# Resource limitleri, log rotation ve güvenlik ayarları dahil
```

## Proje Yapısı

```
HACKATHON/
├── docker-compose.yml          # Development ortamı
├── docker-compose.prod.yml     # Production ortamı (resource limits, log rotation)
├── .env                        # Environment variables
├── .env.example                # Örnek env dosyası
├── firebase-credentials.json   # Firebase service account
├── backend/                    # FastAPI monolith
│   ├── main.py                 # API + background worker + rate limiting
│   ├── config.py               # Pydantic settings
│   ├── constants.py            # Merkezi sabitler
│   ├── models.py               # Pydantic models
│   ├── log_parser.py           # Log parsing + fingerprinting
│   ├── openrouter_client.py    # DeepSeek AI (OpenRouter) client
│   ├── firebase_service.py     # Firestore operations
│   ├── push_service.py         # Push notifications
│   ├── Dockerfile
│   └── requirements.txt
├── mobile_nextjs/              # Next.js mobile-first web app
│   ├── src/
│   │   ├── app/                # Next.js app router
│   │   ├── components/         # React components + ErrorBoundary
│   │   ├── lib/                # API client, auth, utils
│   │   └── types/              # TypeScript type definitions
│   ├── Dockerfile
│   └── package.json
├── services/                   # (Legacy) Microservices – artık kullanılmıyor
│   └── ...                     # Monolith mimarisine geçildi
└── test/
    ├── log_generator_v2.py     # Test log üretici
    └── Dockerfile.v2
```

## Mimari Kararlar

Bu proje **monolith mimari** kullanmaktadır (`backend/` dizini).
`services/` dizinindeki microservice kodu eski versiyondandır ve aktif olarak kullanılmamaktadır.
Tüm iş mantığı (ingestion, AI analizi, push notification, SSE) `backend/main.py` içinde birleştirilmiştir.

## License

MIT

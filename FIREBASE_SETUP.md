# 🔥 Firebase Setup Instructions

## ✅ Firebase Credentials Downloaded

Your Firebase project is configured:
- **Project ID**: montgomery-415113
- **Project Name**: HEYY
- **Service Account**: firebase-adminsdk-svz6o@montgomery-415113.iam.gserviceaccount.com
- **Firestore**: Active (Native mode, nam5 US region)
- **FCM Sender ID**: 105791470459

## 📥 Next Steps

### 1. Save Firebase Credentials JSON

You need to save the downloaded JSON file to the project root:

```bash
# Make sure you're in the project directory
cd c:\Users\bugra\ML\HACKATHON

# Save the downloaded JSON file as:
firebase-credentials.json
```

**File location**: `c:\Users\bugra\ML\HACKATHON\firebase-credentials.json`

### 2. Verify .env Configuration

The `.env` file has been automatically configured with:

```env
FIREBASE_PROJECT_ID=montgomery-415113
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
FCM_SENDER_ID=105791470459
GEMINI_API_KEY=AIzaSyDTABZVj6RY8wmz7eiLI-g4IcVvoGYfvik
```

### 3. Start Containers

```bash
# Stop old containers
docker-compose down

# Build and start with Firebase
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

### 4. Test the System

```bash
# Send a test log
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "log": "[ERROR] Test log message",
    "source": "test",
    "container": "test-container"
  }'
```

### 5. Verify in Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/project/montgomery-415113/firestore)
2. Check **Firestore Database** → Collections
3. You should see:
   - `logs` collection (raw log entries)
   - `alerts` collection (AI analysis results)

## 🔐 Security Notes

- ✅ `.env` is in `.gitignore` (credentials safe)
- ✅ `firebase-credentials.json` should also be in `.gitignore`
- ⚠️ Never commit credentials to Git
- ⚠️ Keep Service Account JSON secure

## 🎯 Firestore Collections Structure

### `logs` Collection
```json
{
  "id": "auto-generated",
  "log": "error message",
  "container": "container-name",
  "source": "docker",
  "severity": "ERROR",
  "timestamp": "2026-02-05T10:30:00Z",
  "created_at": "Firestore timestamp"
}
```

### `alerts` Collection
```json
{
  "id": "auto-generated",
  "category": "database",
  "severity": "high",
  "confidence": 0.95,
  "summary": "Database connection timeout",
  "root_cause": "Network latency...",
  "solution": "Check network config...",
  "action_required": true,
  "log_ids": ["log-id-1", "log-id-2"],
  "created_at": "Firestore timestamp"
}
```

## 🚀 Ready to Go!

Once you save `firebase-credentials.json`, run:
```bash
docker-compose up -d --build
```

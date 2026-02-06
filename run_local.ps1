# LogSense AI – Local Runner
# Backend'i Docker yerine dogrudan makinede calistirir.
# WiFi IP otomatik algilanlir, telefon erisimi sorunsuz olur.

$ErrorActionPreference = "Stop"
$HACKATHON = "C:\Users\bugra\ML\HACKATHON"
$BACKEND   = "$HACKATHON\backend"

# WiFi IP'yi bul
$WIFI_IP = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -eq 'Wi-Fi' }).IPAddress

if (-not $WIFI_IP) {
    Write-Host "HATA: WiFi baglantisi bulunamadi!" -ForegroundColor Red
    exit 1
}
Write-Host "`n=== LogSense AI Local Runner ===" -ForegroundColor Cyan
Write-Host "WiFi IP: $WIFI_IP" -ForegroundColor Green

# Ortam degiskenleri
$env:FIREBASE_CREDENTIALS_PATH = "$HACKATHON\firebase-credentials.json"
$env:FIREBASE_PROJECT_ID       = "montgomery-415113"
$env:OPENROUTER_API_KEY        = "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"
$env:OPENROUTER_MODEL          = "deepseek/deepseek-r1-0528:free"
$env:HOST_IP                   = $WIFI_IP
$env:LOG_LEVEL                 = "DEBUG"
$env:ENABLE_DOCKER_WATCHER     = "false"
$env:BATCH_WINDOW_SECONDS      = "30"
$env:MAX_BATCH_SIZE            = "3"

Write-Host "Backend: http://${WIFI_IP}:8000" -ForegroundColor Green
Write-Host "QR Page: http://${WIFI_IP}:8000/qr/mobile" -ForegroundColor Green
Write-Host ""

# venv aktive et
& "$HACKATHON\.venv\Scripts\Activate.ps1"

# Backend'i baslat
Set-Location $BACKEND
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

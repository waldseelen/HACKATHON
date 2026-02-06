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

# Ortam degiskenleri (.env dosyasindan yukle)
$envFile = "$HACKATHON\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
    Write-Host ".env dosyasi yuklendi" -ForegroundColor Green
} else {
    Write-Host "HATA: .env dosyasi bulunamadi! .env.example'dan kopyalayin." -ForegroundColor Red
    exit 1
}

$env:FIREBASE_CREDENTIALS_PATH = "$HACKATHON\firebase-credentials.json"
$env:HOST_IP                   = $WIFI_IP
$env:LOG_LEVEL                 = "DEBUG"
$env:ENABLE_DOCKER_WATCHER     = "false"

Write-Host "Backend: http://${WIFI_IP}:8000" -ForegroundColor Green
Write-Host "QR Page: http://${WIFI_IP}:8000/qr/mobile" -ForegroundColor Green
Write-Host ""

# venv aktive et
& "$HACKATHON\.venv\Scripts\Activate.ps1"

# Backend'i baslat
Set-Location $BACKEND
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

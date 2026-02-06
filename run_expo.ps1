# LogSense AI – Expo Starter
# Expo'yu dogru WiFi IP ile baslatir.

$ErrorActionPreference = "Stop"
$MOBILE = "C:\Users\bugra\ML\HACKATHON\mobile"

$WIFI_IP = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -eq 'Wi-Fi' }).IPAddress

if (-not $WIFI_IP) {
    Write-Host "HATA: WiFi baglantisi bulunamadi!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== LogSense AI Expo Starter ===" -ForegroundColor Cyan
Write-Host "WiFi IP: $WIFI_IP" -ForegroundColor Green
Write-Host "Expo URL: exp://${WIFI_IP}:8081" -ForegroundColor Green
Write-Host "Backend: http://${WIFI_IP}:8000" -ForegroundColor Green
Write-Host ""

$env:REACT_NATIVE_PACKAGER_HOSTNAME = $WIFI_IP

Set-Location $MOBILE
npx expo start --host lan --clear

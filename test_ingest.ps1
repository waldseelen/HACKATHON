$body = @{
    log = "2025-01-15T10:30:00Z ERROR [payment-service] Connection timeout to database server after 30s retry"
    source = "api-test"
    container = "payment-svc-1"
    timestamp = "2025-01-15T10:30:00Z"
} | ConvertTo-Json

Write-Host "=== Sending test log ==="
$result = Invoke-RestMethod -Uri http://localhost:8000/ingest -Method Post -Body $body -ContentType 'application/json'
Write-Host "Ingest response:"
$result | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "=== Waiting 8 seconds for analysis worker ==="
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "=== Checking alerts ==="
$alerts = Invoke-RestMethod -Uri http://localhost:8000/alerts
Write-Host "Total alerts found: $($alerts.Count)"
$alerts | ConvertTo-Json -Depth 10

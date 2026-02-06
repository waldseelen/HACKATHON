Write-Host "=============================================="
Write-Host "  LOGSENSE AI - MOBIL APP API TEST"
Write-Host "=============================================="
Write-Host ""

# 1) /alerts endpoint
Write-Host "--- /alerts ---"
$alerts = Invoke-RestMethod -Uri http://localhost:8000/alerts
Write-Host "Alert sayisi: $($alerts.Count)"
foreach ($alert in $alerts) {
    $severityEmoji = switch ($alert.severity) {
        "critical" { [char]0x1F534 }  # Red circle
        "high"     { [char]0x1F7E0 }  # Orange circle
        "medium"   { [char]0x1F7E1 }  # Yellow circle
        default    { [char]0x1F7E2 }  # Green circle
    }
    Write-Host ""
    Write-Host "  $severityEmoji [$($alert.severity.ToUpper())] $($alert.category)"
    Write-Host "  Ozet: $($alert.summary.Substring(0, [Math]::Min(80, $alert.summary.Length)))..."
    Write-Host "  Root Cause: $($alert.root_cause)"
    Write-Host "  Solution: $($alert.solution)"
    Write-Host "  Confidence: $([math]::Round($alert.confidence * 100))%"
    Write-Host "  Action Required: $($alert.action_required)"
    Write-Host "  Alert ID: $($alert.id)"
}

# 2) /stats endpoint
Write-Host ""
Write-Host "--- /stats ---"
$stats = Invoke-RestMethod -Uri http://localhost:8000/stats
$stats | ConvertTo-Json -Depth 5

# 3) /logs/recent endpoint
Write-Host ""
Write-Host "--- /logs/recent ---"
$logs = Invoke-RestMethod -Uri http://localhost:8000/logs/recent
Write-Host "Recent log sayisi: $($logs.Count)"
foreach ($log in $logs) {
    Write-Host "  [$($log.severity)] $($log.service): $($log.raw_log.Substring(0, [Math]::Min(60, $log.raw_log.Length)))..."
}

# 4) /alerts/{id} detail
if ($alerts.Count -gt 0) {
    $firstId = $alerts[0].id
    Write-Host ""
    Write-Host "--- /alerts/$firstId (Detail) ---"
    $detail = Invoke-RestMethod -Uri "http://localhost:8000/alerts/$firstId"
    $detail | ConvertTo-Json -Depth 5
}

Write-Host ""
Write-Host "=============================================="
Write-Host "  TAMAMLANDI - Tum API endpointleri calisiyor"
Write-Host "=============================================="

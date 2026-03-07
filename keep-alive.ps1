# IDNA Keep-Alive Script
# Pings Railway production every 5 minutes to prevent container sleep

$url = "https://idna-tutor-mvp-production.up.railway.app/ping"
$logFile = "$PSScriptRoot\keep-alive.log"

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 30
        $status = $response.status
        Add-Content -Path $logFile -Value "$timestamp - OK: $status"
        Write-Host "$timestamp - Pinged: $status"
    } catch {
        Add-Content -Path $logFile -Value "$timestamp - ERROR: $_"
        Write-Host "$timestamp - Error: $_"
    }
    Start-Sleep -Seconds 300  # 5 minutes
}

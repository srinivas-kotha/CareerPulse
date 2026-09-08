$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'CareerPulse\background'
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python environment missing: $pythonPath"
}
if (Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8085 is already in use. Stop the existing CareerPulse terminal with Ctrl+C first.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$stdoutPath = Join-Path $runtimeRoot "$stamp-out.log"
$stderrPath = Join-Path $runtimeRoot "$stamp-error.log"
$serverProcess = Start-Process -FilePath $pythonPath `
    -ArgumentList '-m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8085' `
    -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

@{ processId = $serverProcess.Id; startedAt = $serverProcess.StartTime.ToUniversalTime().ToString('o');
   stdout = $stdoutPath; stderr = $stderrPath } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'process.json')

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $serverProcess.Refresh()
    if ($serverProcess.HasExited) { throw "Server exited. Read $stderrPath" }
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8085/api/health' -TimeoutSec 2
        if ($health.db -eq 'ok') {
            Write-Host 'CareerPulse is running at http://127.0.0.1:8085. You can close PowerShell.'
            Write-Host "Logs: $runtimeRoot"
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 1
}
throw "Started but health check timed out. Inspect $stderrPath before retrying."

$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'CareerPulse\background'
$recordPath = Join-Path $runtimeRoot 'process.json'
if (-not (Test-Path -LiteralPath $recordPath)) { throw 'No background launch record found.' }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$serverProcess = Get-Process -Id $record.processId -ErrorAction SilentlyContinue
if (-not $serverProcess) { Write-Host 'Recorded background process is already stopped.'; exit 0 }
if ($serverProcess.StartTime.ToUniversalTime().ToString('o') -ne $record.startedAt) {
    throw 'Process identity changed; refusing to stop an unrelated process.'
}
if ($record.multiProfile) {
    $progress = Invoke-RestMethod 'http://127.0.0.1:8085/api/runtime/progress' -TimeoutSec 10
    if ($progress.active) { throw 'Candidate work is active. Wait for it to finish before stopping.' }
} else { foreach ($kind in @('scrape', 'score')) {
    $progress = Invoke-RestMethod "http://127.0.0.1:8085/api/$kind/progress" -TimeoutSec 5
    if ($progress.active) { throw "$kind is active. Wait for it to finish before stopping." }
}
}
# Windows virtual environments may launch a child Python interpreter.
$listeners = @(Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue)
foreach ($listener in $listeners) {
    if ($listener.OwningProcess -ne $serverProcess.Id) {
        $child = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
        if ($child.ParentProcessId -ne $serverProcess.Id) {
            throw 'Port belongs to another process; refusing to stop it.'
        }
        Stop-Process -Id $child.ProcessId -ErrorAction Stop
    }
}
if (Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue) {
    Stop-Process -Id $serverProcess.Id -ErrorAction Stop
}
Write-Host 'CareerPulse background process stopped.'

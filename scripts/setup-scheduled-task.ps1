# Setup persistent scheduled tasks for Claude Bridge on Windows.
# This creates two tasks that auto-start on login:
#   1. Relay server (HTTP inbox on port 9111)
#   2. Watcher (auto-processes incoming prompts via claude -p)
#
# Usage (run as Administrator):
#   cd \path\to\claude-bridge
#   powershell -ExecutionPolicy Bypass -File scripts\setup-scheduled-task.ps1

$BridgeDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonBin = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonBin) { $PythonBin = "python" }

Write-Host "Claude Bridge — Windows Scheduled Task Setup"
Write-Host "Bridge directory: $BridgeDir"
Write-Host "Python: $PythonBin"
Write-Host ""

# Relay server task
$relayAction = New-ScheduledTaskAction `
    -Execute $PythonBin `
    -Argument "$BridgeDir\relay\server.py" `
    -WorkingDirectory $BridgeDir

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName "ClaudeBridgeRelay" `
    -Action $relayAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Claude Bridge relay server (port 9111)" `
    -Force

Write-Host "Created scheduled task: ClaudeBridgeRelay"

# Watcher task
$watcherAction = New-ScheduledTaskAction `
    -Execute $PythonBin `
    -Argument "$BridgeDir\relay\watcher.py" `
    -WorkingDirectory $BridgeDir

Register-ScheduledTask `
    -TaskName "ClaudeBridgeWatcher" `
    -Action $watcherAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Claude Bridge watcher (auto-processes incoming prompts)" `
    -Force

Write-Host "Created scheduled task: ClaudeBridgeWatcher"

# Start both now
Start-ScheduledTask -TaskName "ClaudeBridgeRelay"
Start-ScheduledTask -TaskName "ClaudeBridgeWatcher"

Write-Host ""
Write-Host "Both tasks started. Verify with:"
Write-Host "  curl http://localhost:9111/ping"
Write-Host "  Get-ScheduledTask -TaskName 'ClaudeBridge*'"

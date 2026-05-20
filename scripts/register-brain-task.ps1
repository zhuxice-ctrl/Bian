param(
    [string]$TaskName = "TradingLearningBrain",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [string]$AllowedUserId = "owner"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "start-brain.ps1"
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -HostAddress $HostAddress -Port $Port -AllowedUserId $AllowedUserId"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Start the local Trading Learning brain service at user logon." -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Output "Registered and started scheduled task $TaskName"

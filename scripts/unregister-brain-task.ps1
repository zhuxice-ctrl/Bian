param(
    [string]$TaskName = "TradingLearningBrain"
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Unregistered scheduled task $TaskName"
} else {
    Write-Output "Scheduled task $TaskName was not found"
}

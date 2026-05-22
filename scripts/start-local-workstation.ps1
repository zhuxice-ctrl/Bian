param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BrainPort = 8765,
    [int]$DashboardPort = 8780,
    [string]$ServerUrl = "http://127.0.0.1:8765",
    [string]$RunnerId = "local-pc"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $Root "logs"
# Default dashboard URL: http://127.0.0.1:8780/
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

& (Join-Path $PSScriptRoot "start-brain.ps1") -HostAddress $HostAddress -Port $BrainPort

$runnerToken = [Environment]::GetEnvironmentVariable("TRADING_LEARNING_RUNNER_TOKEN", "User")
if ($runnerToken) {
    Start-Process powershell.exe `
        -WindowStyle Hidden `
        -WorkingDirectory $Root `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", (Join-Path $PSScriptRoot "start-quant-runner.ps1"),
            "-ServerUrl", $ServerUrl,
            "-RunnerId", $RunnerId
        )
} else {
    Write-Host "TRADING_LEARNING_RUNNER_TOKEN is not configured; quant runner was not started."
}

$dashboardLog = Join-Path $Logs "dashboard.log"
Start-Process powershell.exe `
    -WindowStyle Hidden `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $dashboardLog `
    -RedirectStandardError $dashboardLog `
    -ArgumentList @(
        "-NoProfile",
        "-Command",
        "trading-learning dashboard-serve --host $HostAddress --port $DashboardPort"
    )

trading-learning health-check
Write-Host "Dashboard: http://127.0.0.1:$DashboardPort/"

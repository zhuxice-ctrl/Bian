param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [string]$AllowedUserId = "owner"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot "logs"
$logPath = Join-Path $logDir "brain-service.log"
$errPath = Join-Path $logDir "brain-service.err.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $repoRoot

$existingListener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    exit 0
}

"$(Get-Date -Format o) starting brain service on $HostAddress`:$Port" | Add-Content -Path $logPath -Encoding UTF8

& trading-learning brain-serve --host $HostAddress --port $Port --allowed-user-id $AllowedUserId `
    1>> $logPath `
    2>> $errPath

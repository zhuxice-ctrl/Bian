param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [string]$AllowedUserId = "owner",
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$stopScript = Join-Path $PSScriptRoot "stop-brain.ps1"
$startScript = Join-Path $PSScriptRoot "start-brain.ps1"

& $stopScript -HostAddress $HostAddress -Port $Port

Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $startScript,
    "-HostAddress",
    $HostAddress,
    "-Port",
    $Port,
    "-AllowedUserId",
    $AllowedUserId
) -WindowStyle Hidden

$url = "http://$HostAddress`:$Port/brain/command"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Milliseconds 500
    try {
        $body = @{
            text = "/status"
            user_id = $AllowedUserId
        } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body | Out-Null
        Write-Output "Restarted brain service on $HostAddress`:$Port"
        exit 0
    } catch {
        if ((Get-Date) -ge $deadline) {
            throw "Brain service did not become ready within $TimeoutSeconds seconds"
        }
    }
} while ($true)

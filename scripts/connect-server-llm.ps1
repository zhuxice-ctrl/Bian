param(
    [string]$ServerUser = "ubuntu",
    [string]$ServerHost = "152.136.204.41",
    [string]$KeyPath = (Join-Path $env:USERPROFILE ".ssh\bian_server_codex_ed25519"),
    [int]$LocalPort = 61771,
    [int]$RemotePort = 61771
)

$ErrorActionPreference = "Stop"

# Default target: ubuntu@152.136.204.41
$target = "$ServerUser@$ServerHost"
# Default tunnel shape: 127.0.0.1:61771:127.0.0.1:61771
$reverse = "127.0.0.1:$RemotePort`:127.0.0.1:$LocalPort"

Write-Host "Opening SSH reverse tunnel: server $reverse -> local Codex API"
ssh -i $KeyPath -N -R $reverse $target

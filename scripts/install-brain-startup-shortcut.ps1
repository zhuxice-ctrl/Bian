param(
    [string]$ShortcutName = "TradingLearningBrain.lnk",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [string]$AllowedUserId = "owner"
)

$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir $ShortcutName
$scriptPath = Join-Path $PSScriptRoot "start-brain.ps1"
$argument = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -HostAddress $HostAddress -Port $Port -AllowedUserId $AllowedUserId"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = $argument
$shortcut.WorkingDirectory = Split-Path -Parent $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "Start the local Trading Learning brain service at user logon."
$shortcut.Save()

Write-Output "Installed startup shortcut $shortcutPath"

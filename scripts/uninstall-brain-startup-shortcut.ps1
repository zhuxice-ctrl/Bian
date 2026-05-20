param(
    [string]$ShortcutName = "TradingLearningBrain.lnk"
)

$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir $ShortcutName

if (Test-Path $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath
    Write-Output "Removed startup shortcut $shortcutPath"
} else {
    Write-Output "Startup shortcut $shortcutPath was not found"
}

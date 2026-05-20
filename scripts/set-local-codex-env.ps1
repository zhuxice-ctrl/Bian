param(
    [string]$BaseUrl = "http://127.0.0.1:61771/v1",
    [string]$Model = "gpt-5.4-mini"
)

$ErrorActionPreference = "Stop"

$secureKey = Read-Host "Enter LOCAL_CODEX_API_KEY" -AsSecureString
$plainKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
)

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    throw "LOCAL_CODEX_API_KEY cannot be empty"
}

[Environment]::SetEnvironmentVariable("LOCAL_CODEX_BASE_URL", $BaseUrl, "User")
[Environment]::SetEnvironmentVariable("LOCAL_CODEX_MODEL", $Model, "User")
[Environment]::SetEnvironmentVariable("LOCAL_CODEX_API_KEY", $plainKey, "User")

Write-Output "Saved local Codex settings to the current Windows user environment."
Write-Output "Restart the Brain service with scripts/restart-brain.ps1."

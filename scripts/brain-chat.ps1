param(
    [string]$Command,
    [string]$UserId = "owner",
    [string]$Url = "http://127.0.0.1:8765/brain/command"
)

$ErrorActionPreference = "Stop"

function Send-BrainCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $body = @{
        text = $Text
        user_id = $UserId
    } | ConvertTo-Json -Compress

    Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body $body |
        ConvertTo-Json -Depth 10
}

if ($Command) {
    Send-BrainCommand -Text $Command
    exit 0
}

Write-Output "Local Brain chat. Type /quit to exit."
while ($true) {
    $line = Read-Host "brain"
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }
    if ($line -eq "/quit") {
        break
    }
    Send-BrainCommand -Text $line
}

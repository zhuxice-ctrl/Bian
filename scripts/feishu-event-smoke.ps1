param(
    [string]$Url = "http://127.0.0.1:8765/feishu/events",
    [string]$VerificationToken = [Environment]::GetEnvironmentVariable("FEISHU_VERIFICATION_TOKEN", "User"),
    [string]$EncryptKey = [Environment]::GetEnvironmentVariable("FEISHU_ENCRYPT_KEY", "User"),
    [string]$OpenId = "owner",
    [string]$Command = "/status"
)

$ErrorActionPreference = "Stop"

function New-FeishuHeaders {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Body
    )

    if (-not $EncryptKey) {
        return @{}
    }

    $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
    $nonce = [guid]::NewGuid().ToString("N")
    $prefixBytes = [Text.Encoding]::UTF8.GetBytes("$timestamp$nonce$EncryptKey")
    $bodyBytes = [Text.Encoding]::UTF8.GetBytes($Body)
    $allBytes = New-Object byte[] ($prefixBytes.Length + $bodyBytes.Length)
    [Array]::Copy($prefixBytes, 0, $allBytes, 0, $prefixBytes.Length)
    [Array]::Copy($bodyBytes, 0, $allBytes, $prefixBytes.Length, $bodyBytes.Length)
    $sha = [Security.Cryptography.SHA256]::Create()
    $signature = [BitConverter]::ToString($sha.ComputeHash($allBytes)).Replace("-", "").ToLowerInvariant()
    return @{
        "X-Lark-Request-Timestamp" = $timestamp
        "X-Lark-Request-Nonce" = $nonce
        "X-Lark-Signature" = $signature
    }
}

if (-not $VerificationToken) {
    $VerificationToken = "local-smoke-token"
}

$verificationBody = @{
    type = "url_verification"
    token = $VerificationToken
    challenge = "local-smoke-challenge"
} | ConvertTo-Json -Depth 10

$verification = Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body $verificationBody
Write-Output ($verification | ConvertTo-Json -Depth 10)

$messageContent = @{
    text = $Command
} | ConvertTo-Json -Compress

$messageBody = @{
    schema = "2.0"
    header = @{
        event_type = "im.message.receive_v1"
        token = $VerificationToken
    }
    event = @{
        sender = @{
            sender_id = @{
                open_id = $OpenId
            }
        }
        message = @{
            chat_id = "local-smoke-chat"
            message_type = "text"
            content = $messageContent
        }
    }
} | ConvertTo-Json -Depth 10

$messageHeaders = New-FeishuHeaders -Body $messageBody
$message = Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Headers $messageHeaders -Body $messageBody
Write-Output ($message | ConvertTo-Json -Depth 10)

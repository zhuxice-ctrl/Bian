$ErrorActionPreference = "Stop"

function ConvertFrom-SecureStringToPlainText {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecureValue)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

$verificationToken = Read-Host "Enter FEISHU_VERIFICATION_TOKEN (optional, press Enter if Feishu does not show one)"
$encryptKeySecure = Read-Host "Enter FEISHU_ENCRYPT_KEY (optional, press Enter to skip)" -AsSecureString
$userMap = Read-Host "Enter FEISHU_USER_MAP, example: ou_xxx:owner"
$appId = Read-Host "Enter FEISHU_APP_ID"
$appSecretSecure = Read-Host "Enter FEISHU_APP_SECRET" -AsSecureString

$encryptKey = ConvertFrom-SecureStringToPlainText $encryptKeySecure
$appSecret = ConvertFrom-SecureStringToPlainText $appSecretSecure

if (-not $userMap) {
    throw "FEISHU_USER_MAP cannot be empty"
}
if (-not $appId) {
    throw "FEISHU_APP_ID cannot be empty"
}
if (-not $appSecret) {
    throw "FEISHU_APP_SECRET cannot be empty"
}

[Environment]::SetEnvironmentVariable("FEISHU_VERIFICATION_TOKEN", $verificationToken, "User")
[Environment]::SetEnvironmentVariable("FEISHU_ENCRYPT_KEY", $encryptKey, "User")
[Environment]::SetEnvironmentVariable("FEISHU_USER_MAP", $userMap, "User")
[Environment]::SetEnvironmentVariable("FEISHU_APP_ID", $appId, "User")
[Environment]::SetEnvironmentVariable("FEISHU_APP_SECRET", $appSecret, "User")

Write-Output "Saved Feishu configuration to Windows user environment. Restart Brain for changes to take effect."

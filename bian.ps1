#!/usr/bin/env pwsh
# Bian daily paper trading: update data + run signals + show status
Set-Location F:\Bian
$env:HTTPS_PROXY = "http://127.0.0.1:37830"
$env:HTTP_PROXY = "http://127.0.0.1:37830"
py -3.11 scripts/daily_update.py --trade --status --push

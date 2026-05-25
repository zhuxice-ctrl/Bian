#!/usr/bin/env pwsh
# Bian daily paper trading: update data + run signals + show status
Set-Location F:\Bian
py -3.11 scripts/daily_update.py --trade --status

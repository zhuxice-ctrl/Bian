param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ServerUrl = "https://dl.zeroxcore.tech",
    [string]$RunnerId = "local-windows-pc",
    [int]$IntervalSeconds = 10
)

$ErrorActionPreference = "Stop"

$runnerToken = [Environment]::GetEnvironmentVariable("TRADING_LEARNING_RUNNER_TOKEN", "User")
if ([string]::IsNullOrWhiteSpace($runnerToken)) {
    $runnerToken = [Environment]::GetEnvironmentVariable("TRADING_LEARNING_RUNNER_TOKEN", "Process")
}
if ([string]::IsNullOrWhiteSpace($runnerToken)) {
    throw "TRADING_LEARNING_RUNNER_TOKEN is required in the user or process environment."
}

$env:TRADING_LEARNING_RUNNER_TOKEN = $runnerToken
Set-Location $ProjectRoot

trading-learning quant-runner `
    --server-url $ServerUrl `
    --runner-id $RunnerId `
    --interval-seconds $IntervalSeconds

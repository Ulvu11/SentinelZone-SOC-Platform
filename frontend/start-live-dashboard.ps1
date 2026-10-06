$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Remove-Item Env:SOC_ALERTS_URL -ErrorAction SilentlyContinue
npm.cmd run dev -- --hostname 127.0.0.1 --port 3001

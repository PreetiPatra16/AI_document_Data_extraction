$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
docker compose down
exit $LASTEXITCODE

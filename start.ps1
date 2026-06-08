$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or is not available on PATH."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is installed but the Docker engine is not running."
}

Set-Location $PSScriptRoot
docker compose up --build --wait
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

Write-Host ""
Write-Host "DocuExtract is ready:"
Write-Host "  Frontend: http://localhost:$FrontendPort"
Write-Host "  API docs: http://localhost:$ApiPort/docs"

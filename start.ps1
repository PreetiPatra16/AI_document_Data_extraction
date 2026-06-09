$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available on PATH. Install and start Docker Desktop, then open a new PowerShell window."
}

function Test-DockerEngine {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & docker info *> $null
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousErrorActionPreference
    return $ExitCode -eq 0
}

function Show-ComposeDiagnostics {
    Write-Host ""
    Write-Host "Docker Compose status:" -ForegroundColor Yellow
    & docker compose ps -a
    Write-Host ""
    Write-Host "Recent startup logs:" -ForegroundColor Yellow
    & docker compose logs --tail 100 model-init api frontend
}

$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

if (-not (Test-DockerEngine)) {
    throw "Docker is installed but the Docker engine is not running. Start Docker Desktop and wait until it reports that the engine is running."
}

Push-Location $PSScriptRoot
try {
    & docker compose version
    if ($LASTEXITCODE -ne 0) {
        throw "The Docker Compose plugin is unavailable. Update Docker Desktop and confirm that 'docker compose version' works."
    }

    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "compose.yaml is invalid."
    }

    & docker compose up --build --wait
    if ($LASTEXITCODE -ne 0) {
        Show-ComposeDiagnostics
        throw "Docker Compose startup failed. Review the status and logs above."
    }

    try {
        $ProxyHealth = Invoke-RestMethod `
            -Uri "http://localhost:$FrontendPort/api/v1/health/ready" `
            -TimeoutSec 30
        if ($ProxyHealth.status -ne "ready") {
            throw "The proxied API returned status '$($ProxyHealth.status)'."
        }
    }
    catch {
        Show-ComposeDiagnostics
        throw "The frontend is running but its /api proxy cannot reach the backend. $($_.Exception.Message)"
    }

    Write-Host ""
    Write-Host "DocuExtract is ready:"
    Write-Host "  Frontend: http://localhost:$FrontendPort"
    Write-Host "  API docs: http://localhost:$ApiPort/docs"
    Write-Host "  Frontend-to-API proxy: verified"
}
finally {
    Pop-Location
}

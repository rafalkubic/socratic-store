param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Test-DockerEngine {
    & docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Path $PythonExe)) {
    throw "Python virtualenv not found: $PythonExe"
}

Write-Host "[1/5] Docker Desktop..." -ForegroundColor Cyan
if (-not (Test-DockerEngine)) {
    Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
    & docker desktop start | Out-Host

    $DockerReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        if (Test-DockerEngine) {
            $DockerReady = $true
            break
        }
    }

    if (-not $DockerReady) {
        throw "Docker Engine did not become ready in time."
    }
}
Write-Host "Docker: OK" -ForegroundColor Green

Push-Location $ProjectRoot
try {
    Write-Host "[2/5] MySQL..." -ForegroundColor Cyan
    & docker compose up -d mysql | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed."
    }

    Write-Host "[3/5] Waiting for MySQL..." -ForegroundColor Cyan
    $DbReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        $Health = (& docker inspect --format "{{.State.Health.Status}}" socratic-store-mysql 2>$null)
        if ($LASTEXITCODE -eq 0 -and $Health -and $Health.Trim() -eq "healthy") {
            $DbReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $DbReady) {
        throw "MySQL did not reach healthy status."
    }
    Write-Host "MySQL: OK" -ForegroundColor Green

    Write-Host "[4/5] Database seed..." -ForegroundColor Cyan
    & $PythonExe (Join-Path $ProjectRoot "seed.py")
    if ($LASTEXITCODE -ne 0) {
        throw "seed.py failed."
    }

    Write-Host "[5/5] Flask..." -ForegroundColor Cyan
    $ExistingFlask = Get-CimInstance Win32_Process |
        Where-Object { $_.Name -match "python" -and $_.CommandLine -match "run\.py" } |
        Select-Object -First 1

    if (-not $ExistingFlask) {
        $RunPy = Join-Path $ProjectRoot "run.py"
        $Command = "& '$PythonExe' '$RunPy'"
        Start-Process powershell.exe -WorkingDirectory $ProjectRoot -ArgumentList @(
            "-NoExit",
            "-ExecutionPolicy", "Bypass",
            "-Command", $Command
        ) | Out-Null
    }
    else {
        Write-Host "Flask already running: PID $($ExistingFlask.ProcessId)"
    }

    if ($OpenBrowser) {
        Start-Sleep -Seconds 3
        Start-Process "http://localhost:5000"
    }

    Write-Host ""
    Write-Host "Socratic Store: http://localhost:5000" -ForegroundColor Green
}
finally {
    Pop-Location
}

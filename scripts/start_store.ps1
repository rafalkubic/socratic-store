$ErrorActionPreference = "Stop"

$ProjectPath = "C:\Users\rkubic\socratic_store\socratic_store"
$PythonExe = Join-Path $ProjectPath ".venv\Scripts\python.exe"
$DockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$MySqlContainer = "socratic-store-mysql"

Write-Host ""
Write-Host "====================================" -ForegroundColor Yellow
Write-Host " SOCRATIC STORE - START" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
Write-Host ""

# --------------------------------------------------
# 0. Sprawdzenie projektu i Pythona
# --------------------------------------------------

if (-not (Test-Path $ProjectPath)) {
    throw "Nie znaleziono katalogu projektu: $ProjectPath"
}

if (-not (Test-Path $PythonExe)) {
    throw "Nie znaleziono virtualenv Python: $PythonExe"
}

Set-Location $ProjectPath

# --------------------------------------------------
# 1. Docker
# --------------------------------------------------

Write-Host "[1/5] Sprawdzam Docker..." -ForegroundColor Cyan

$DockerReady = $false

cmd.exe /d /c "docker info >nul 2>&1"

if ($LASTEXITCODE -eq 0) {
    $DockerReady = $true
}

if (-not $DockerReady) {

    Write-Host "Docker Engine nie dziala. Uruchamiam Docker Desktop..." -ForegroundColor Yellow

    if (-not (Test-Path $DockerDesktopExe)) {
        throw "Nie znaleziono Docker Desktop: $DockerDesktopExe"
    }

    Start-Process $DockerDesktopExe | Out-Null

    Write-Host "Czekam na uruchomienie Docker Engine..." -ForegroundColor Yellow

    for ($i = 1; $i -le 60; $i++) {

        Start-Sleep -Seconds 2

        cmd.exe /d /c "docker info >nul 2>&1"

        if ($LASTEXITCODE -eq 0) {
            $DockerReady = $true
            break
        }

        Write-Host "  Docker jeszcze startuje... ($i/60)"
    }
}

if (-not $DockerReady) {
    throw "Docker Engine nie uruchomil sie w wymaganym czasie."
}

Write-Host "Docker OK." -ForegroundColor Green

# --------------------------------------------------
# 2. MySQL
# --------------------------------------------------

Write-Host ""
Write-Host "[2/5] Uruchamiam MySQL..." -ForegroundColor Cyan

docker compose up -d mysql

if ($LASTEXITCODE -ne 0) {
    throw "Nie udalo sie uruchomic kontenera MySQL."
}

# --------------------------------------------------
# 3. Oczekiwanie na healthcheck MySQL
# --------------------------------------------------

Write-Host ""
Write-Host "[3/5] Czekam na MySQL..." -ForegroundColor Cyan

$MySQLReady = $false

for ($i = 1; $i -le 60; $i++) {

    $Health = ""

    try {
        $Health = (
            docker inspect `
                --format "{{.State.Health.Status}}" `
                $MySqlContainer `
                2>$null
        ).Trim()
    }
    catch {
        $Health = ""
    }

    if ($Health -eq "healthy") {
        $MySQLReady = $true
        break
    }

    if ($Health) {
        Write-Host "  MySQL status: $Health ($i/60)"
    }
    else {
        Write-Host "  Czekam na kontener MySQL... ($i/60)"
    }

    Start-Sleep -Seconds 2
}

if (-not $MySQLReady) {

    Write-Host ""
    Write-Host "Aktualny status kontenera:" -ForegroundColor Yellow

    docker compose ps

    throw "MySQL nie osiagnal statusu healthy."
}

Write-Host "MySQL OK." -ForegroundColor Green

# --------------------------------------------------
# 4. Baza danych / seed
# --------------------------------------------------

Write-Host ""
Write-Host "[4/5] Sprawdzam strukture i dane bazy..." -ForegroundColor Cyan

& $PythonExe "$ProjectPath\seed.py"

if ($LASTEXITCODE -ne 0) {
    throw "Seed bazy danych zakonczyl sie bledem."
}

Write-Host "Baza danych OK." -ForegroundColor Green

# --------------------------------------------------
# 5. Flask
# --------------------------------------------------

Write-Host ""
Write-Host "[5/5] Uruchamiam Socratic Store..." -ForegroundColor Cyan

# Zatrzymujemy ewentualna stara instancje Flask
$OldFlaskProcesses = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match "^python" -and
        $_.CommandLine -match "run\.py"
    }

foreach ($Process in $OldFlaskProcesses) {

    Write-Host "  Zatrzymuje poprzedni Flask PID $($Process.ProcessId)" -ForegroundColor DarkYellow

    Stop-Process `
        -Id $Process.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

# Uruchom Flask w osobnym oknie PowerShell
$FlaskCommand = "& `"$PythonExe`" `"$ProjectPath\run.py`""

Start-Process `
    powershell.exe `
    -WorkingDirectory $ProjectPath `
    -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $FlaskCommand
    ) | Out-Null

Write-Host "Czekam na Flask..." -ForegroundColor Yellow

$FlaskReady = $false

for ($i = 1; $i -le 20; $i++) {

    Start-Sleep -Seconds 1

    try {
        $Response = Invoke-WebRequest `
            -Uri "http://127.0.0.1:5000" `
            -UseBasicParsing `
            -TimeoutSec 2 `
            -ErrorAction Stop

        if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
            $FlaskReady = $true
            break
        }
    }
    catch {
        Write-Host "  Flask jeszcze startuje... ($i/20)"
    }
}

if (-not $FlaskReady) {
    Write-Host ""
    Write-Host "Flask nie odpowiedzial jeszcze na porcie 5000." -ForegroundColor Yellow
    Write-Host "Sprawdz nowe okno PowerShell z logami Flask." -ForegroundColor Yellow
}
else {
    Write-Host "Flask OK." -ForegroundColor Green
}

# --------------------------------------------------
# Otworzenie sklepu
# --------------------------------------------------

if ($FlaskReady) {
    Start-Process "http://localhost:5000"
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host " SOCRATIC STORE URUCHOMIONY" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Sklep:  http://localhost:5000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Docker: OK"
Write-Host "MySQL:  OK"

if ($FlaskReady) {
    Write-Host "Flask:  OK"
}
else {
    Write-Host "Flask:  sprawdz logi" -ForegroundColor Yellow
}

Write-Host ""
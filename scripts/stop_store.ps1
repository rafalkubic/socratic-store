$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "Stopping Flask..." -ForegroundColor Yellow
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match "python" -and $_.CommandLine -match "run\.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Stopping MySQL container..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    & docker compose stop mysql | Out-Host
}
finally {
    Pop-Location
}

Write-Host "Store stopped." -ForegroundColor Green

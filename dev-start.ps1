# Lutum Veritas - Development Launcher
# =====================================
# Startet Backend und Frontend für Entwicklung.

Write-Host "=== Lutum Veritas Dev Environment ===" -ForegroundColor Cyan
Write-Host ""

# 1. Backend starten (im Hintergrund)
Write-Host "[1/2] Starting Backend on port 8420..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "lutum-backend"
Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $backendPath -WindowStyle Normal

# Warten bis Backend bereit
Write-Host "      Waiting for backend..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 2. Frontend starten
Write-Host "[2/2] Starting Frontend (Tauri Dev)..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "lutum-desktop"
Set-Location $frontendPath
npm run tauri dev

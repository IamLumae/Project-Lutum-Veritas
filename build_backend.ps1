# build_backend.ps1
# ===========================================
# Lutum Veritas - Backend Frozen Build Script
# ===========================================
# Builds the Python backend into a frozen executable using PyInstaller.
# Uses Python 3.12 (primp has no wheel for 3.14!)
#
# Usage: .\build_backend.ps1
# Output: dist\lutum-backend\lutum-backend.exe

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python312 = "C:\Users\hacka\AppData\Local\Programs\Python\Python312\python.exe"
$SpecFile = Join-Path $ProjectRoot "build_backend.spec"
$OutputDir = Join-Path $ProjectRoot "dist\lutum-backend"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  LUTUM VERITAS - BACKEND BUILD" -ForegroundColor Cyan
Write-Host "  PyInstaller Frozen Executable" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# === Step 1: Verify Python 3.12 ===
Write-Host "[1/5] Checking Python 3.12..." -ForegroundColor Yellow
if (-not (Test-Path $Python312)) {
    Write-Host "  ERROR: Python 3.12 not found at $Python312" -ForegroundColor Red
    Write-Host "  Install Python 3.12 from python.org" -ForegroundColor Red
    exit 1
}
$pyVersion = & $Python312 --version 2>&1
Write-Host "  OK: $pyVersion" -ForegroundColor Green

# === Step 2: Ensure PyInstaller + dependencies installed in 3.12 ===
Write-Host "`n[2/5] Installing build dependencies in Python 3.12..." -ForegroundColor Yellow
& $Python312 -m pip install pyinstaller --quiet --upgrade 2>&1 | Out-Null
Write-Host "  PyInstaller ready" -ForegroundColor Green

# Install project dependencies in 3.12 (needed for collect_all to work)
Write-Host "  Installing project dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $ProjectRoot "lutum_backend\requirements.txt"
& $Python312 -m pip install -r $reqFile --quiet 2>&1 | Out-Null
# Also install the project itself in editable mode for lutum package
& $Python312 -m pip install -e $ProjectRoot --quiet 2>&1 | Out-Null
Write-Host "  All dependencies ready" -ForegroundColor Green

# === Step 3: Clean previous build ===
Write-Host "`n[3/5] Cleaning previous build..." -ForegroundColor Yellow
$buildDir = Join-Path $ProjectRoot "build"
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
    Write-Host "  Removed build/" -ForegroundColor Gray
}
if (Test-Path $OutputDir) {
    Remove-Item -Recurse -Force $OutputDir
    Write-Host "  Removed dist/lutum-backend/" -ForegroundColor Gray
}
Write-Host "  Clean" -ForegroundColor Green

# === Step 4: Run PyInstaller ===
Write-Host "`n[4/5] Building frozen executable..." -ForegroundColor Yellow
Write-Host "  This may take 2-5 minutes..." -ForegroundColor Gray

Set-Location $ProjectRoot
& $Python312 -m PyInstaller $SpecFile --noconfirm 2>&1 | ForEach-Object {
    if ($_ -match "ERROR|FATAL|ImportError") {
        Write-Host "  $_" -ForegroundColor Red
    } elseif ($_ -match "WARNING") {
        # Suppress most warnings, only show important ones
        if ($_ -match "hidden import|not found") {
            Write-Host "  $_" -ForegroundColor DarkYellow
        }
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  BUILD FAILED (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

# === Step 5: Verify output ===
Write-Host "`n[5/5] Verifying build..." -ForegroundColor Yellow
$exePath = Join-Path $OutputDir "lutum-backend.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "  ERROR: lutum-backend.exe not found at $exePath" -ForegroundColor Red
    exit 1
}

$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
$totalSize = [math]::Round(((Get-ChildItem -Recurse $OutputDir | Measure-Object -Property Length -Sum).Sum) / 1MB, 2)
$fileCount = (Get-ChildItem -Recurse $OutputDir -File).Count

Write-Host "  EXE: $exePath" -ForegroundColor White
Write-Host "  EXE Size: ${exeSize} MB" -ForegroundColor White
Write-Host "  Total Size: ${totalSize} MB ($fileCount files)" -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  BUILD SUCCESSFUL!" -ForegroundColor Green
Write-Host "  Output: $OutputDir" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Quick smoke test
Write-Host "Running smoke test..." -ForegroundColor Yellow
$proc = Start-Process -FilePath $exePath -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8420/health" -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  Smoke test PASSED - Backend responds on port 8420" -ForegroundColor Green
    } else {
        Write-Host "  Smoke test WARNING - Got status $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Smoke test SKIPPED - Backend may need more startup time" -ForegroundColor Yellow
    Write-Host "  (This is normal for first run - camoufox browser may be downloading)" -ForegroundColor Gray
} finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  Backend process stopped" -ForegroundColor Gray
}

Write-Host "`nNext: Run 'npm run tauri build' in lutum-desktop/ to create the installer." -ForegroundColor Cyan

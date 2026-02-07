# archive-build.ps1
# =========================================================
# LUTUM VERITAS - Full Build Pipeline
# =========================================================
# Step 1: Archive previous builds
# Step 2: Build frozen backend (PyInstaller)
# Step 3: Build Tauri installer (NSIS)
# =========================================================

$ErrorActionPreference = "Continue"

$projectRoot = "C:\Users\hacka\Desktop\Neuer-Main-Server\new-server\Project Lutum Veritas"
$lutumDesktopPath = Join-Path $projectRoot "lutum-desktop"
$buildOutputPath = Join-Path $lutumDesktopPath "src-tauri\target\release\bundle\nsis"
$archivePath = Join-Path $lutumDesktopPath "dist\archive\exe"
$dateFolder = Get-Date -Format "yyyy-MM-dd"
$targetPath = Join-Path $archivePath $dateFolder

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  LUTUM VERITAS - FULL BUILD PIPELINE" -ForegroundColor Cyan
Write-Host "  Date: $dateFolder" -ForegroundColor Cyan
Write-Host "==========================================`n" -ForegroundColor Cyan

# ==========================
# STEP 1: Archive old builds
# ==========================
Write-Host "=== STEP 1: ARCHIVING PREVIOUS BUILDS ===" -ForegroundColor Cyan

$existingBuilds = @(Get-ChildItem -Path $buildOutputPath -Filter "*.exe" -ErrorAction SilentlyContinue)

if ($existingBuilds.Count -gt 0) {
    Write-Host "Found $($existingBuilds.Count) existing build(s) to archive:" -ForegroundColor Yellow

    New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
    Write-Host "Created archive directory: $targetPath" -ForegroundColor Green

    foreach ($build in $existingBuilds) {
        $timestamp = Get-Date -Format "HHmmss"
        $archiveFileName = $build.Name -replace "\.exe$", "-$timestamp.exe"
        $archiveFilePath = Join-Path $targetPath $archiveFileName

        try {
            Copy-Item -Path $build.FullName -Destination $archiveFilePath -Force
            $sizeMB = [math]::Round($build.Length / 1MB, 2)
            Write-Host "  [OK] Archived: $($build.Name) -> $archiveFileName (${sizeMB} MB)" -ForegroundColor Green
        } catch {
            Write-Host "  [FAIL] Failed to archive $($build.Name): $_" -ForegroundColor Red
        }
    }

    Write-Host "Archive complete!`n" -ForegroundColor Green
} else {
    Write-Host "No existing builds found. Fresh build.`n" -ForegroundColor Yellow
}

# =======================================
# STEP 2: Build frozen backend (PyInstaller)
# =======================================
Write-Host "=== STEP 2: BUILDING FROZEN BACKEND ===" -ForegroundColor Cyan
Write-Host "Running: build_backend.ps1`n" -ForegroundColor White

$buildBackendScript = Join-Path $projectRoot "build_backend.ps1"

if (-not (Test-Path $buildBackendScript)) {
    Write-Host "  ERROR: build_backend.ps1 not found at $buildBackendScript" -ForegroundColor Red
    exit 1
}

# Run backend build
& $buildBackendScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n=== BACKEND BUILD FAILED ===" -ForegroundColor Red
    Write-Host "Fix the errors above and retry." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Verify backend output exists
$backendExe = Join-Path $projectRoot "dist\lutum-backend\lutum-backend.exe"
if (-not (Test-Path $backendExe)) {
    Write-Host "  ERROR: Backend EXE not found at $backendExe" -ForegroundColor Red
    exit 1
}
Write-Host "Backend build OK`n" -ForegroundColor Green

# ====================================
# STEP 3: Build Tauri installer (NSIS)
# ====================================
Write-Host "=== STEP 3: BUILDING TAURI INSTALLER ===" -ForegroundColor Cyan
Write-Host "Running: npm run tauri build`n" -ForegroundColor White

Set-Location $lutumDesktopPath

try {
    npm run tauri build

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=== BUILD SUCCESSFUL ===" -ForegroundColor Green
        Write-Host "New build available in: $buildOutputPath" -ForegroundColor White

        $newBuilds = @(Get-ChildItem -Path $buildOutputPath -Filter "*.exe" -ErrorAction SilentlyContinue)
        if ($newBuilds.Count -gt 0) {
            Write-Host "`nNew build files:" -ForegroundColor Green
            foreach ($build in $newBuilds) {
                $sizeMB = [math]::Round($build.Length / 1MB, 2)
                Write-Host "  - $($build.Name) (${sizeMB} MB)" -ForegroundColor White
            }
        }
    } else {
        Write-Host "`n=== TAURI BUILD FAILED ===" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "`n=== BUILD ERROR ===" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  FULL BUILD PIPELINE COMPLETE!" -ForegroundColor Green
Write-Host "==========================================`n" -ForegroundColor Green

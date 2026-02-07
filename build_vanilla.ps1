# build_vanilla.ps1
# =========================================================
# LUTUM VERITAS - Vanilla Build (System Python)
# =========================================================
# Swaps in vanilla configs, builds Tauri, restores originals.
# Result: ~5-7 MB installer (no bundled Python).
# =========================================================

$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\hacka\Desktop\Neuer-Main-Server\new-server\Project Lutum Veritas"
$tauriDir = Join-Path $projectRoot "lutum-desktop\src-tauri"
$desktopDir = Join-Path $projectRoot "lutum-desktop"
$vanillaDir = Join-Path $tauriDir "vanilla"

# Files to swap
$filesToSwap = @(
    @{ Original = Join-Path $tauriDir "src\lib.rs";      Vanilla = Join-Path $vanillaDir "lib.rs" },
    @{ Original = Join-Path $tauriDir "tauri.conf.json";  Vanilla = Join-Path $vanillaDir "tauri.conf.json" },
    @{ Original = Join-Path $tauriDir "nsis-hooks.nsh";   Vanilla = Join-Path $vanillaDir "nsis-hooks.nsh" }
)

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  LUTUM VERITAS - VANILLA BUILD" -ForegroundColor Cyan
Write-Host "  (System Python, no bundled runtime)" -ForegroundColor Cyan
Write-Host "==========================================`n" -ForegroundColor Cyan

# ========================
# STEP 1: Backup originals
# ========================
Write-Host "=== STEP 1: BACKING UP ORIGINALS ===" -ForegroundColor Yellow

foreach ($file in $filesToSwap) {
    $backup = "$($file.Original).full-backup"
    Copy-Item $file.Original $backup -Force
    Write-Host "  Backed up: $(Split-Path $file.Original -Leaf)" -ForegroundColor Gray
}
Write-Host "  Backups created`n" -ForegroundColor Green

# ===========================
# STEP 2: Swap vanilla configs
# ===========================
Write-Host "=== STEP 2: SWAPPING VANILLA CONFIGS ===" -ForegroundColor Yellow

foreach ($file in $filesToSwap) {
    if (-not (Test-Path $file.Vanilla)) {
        Write-Host "  ERROR: Vanilla file not found: $($file.Vanilla)" -ForegroundColor Red
        # Restore backups
        foreach ($f in $filesToSwap) {
            $backup = "$($f.Original).full-backup"
            if (Test-Path $backup) {
                Copy-Item $backup $f.Original -Force
                Remove-Item $backup -Force
            }
        }
        exit 1
    }
    Copy-Item $file.Vanilla $file.Original -Force
    Write-Host "  Swapped: $(Split-Path $file.Original -Leaf)" -ForegroundColor Gray
}
Write-Host "  Vanilla configs active`n" -ForegroundColor Green

# ========================
# STEP 3: Build Tauri
# ========================
Write-Host "=== STEP 3: BUILDING TAURI (VANILLA) ===" -ForegroundColor Yellow

$buildSuccess = $false
try {
    Set-Location $desktopDir
    npm run tauri build 2>&1
    if ($LASTEXITCODE -eq 0) {
        $buildSuccess = $true
    }
} catch {
    Write-Host "  Build error: $_" -ForegroundColor Red
}

# ============================
# STEP 4: ALWAYS restore originals
# ============================
Write-Host "`n=== STEP 4: RESTORING ORIGINALS ===" -ForegroundColor Yellow

foreach ($file in $filesToSwap) {
    $backup = "$($file.Original).full-backup"
    if (Test-Path $backup) {
        Copy-Item $backup $file.Original -Force
        Remove-Item $backup -Force
        Write-Host "  Restored: $(Split-Path $file.Original -Leaf)" -ForegroundColor Gray
    }
}
Write-Host "  Originals restored`n" -ForegroundColor Green

Set-Location $projectRoot

# ========================
# STEP 5: Copy result
# ========================
if ($buildSuccess) {
    $nsisDir = Join-Path $desktopDir "src-tauri\target\release\bundle\nsis"
    $sourceExe = Get-ChildItem -Path $nsisDir -Filter "*.exe" | Select-Object -First 1

    if ($sourceExe) {
        $destDir = Join-Path $projectRoot "dist"
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        $destName = "Lutum Veritas Vanilla_1.3.1_x64-setup.exe"
        $destPath = Join-Path $destDir $destName
        Copy-Item $sourceExe.FullName $destPath -Force

        $sizeMB = [math]::Round($sourceExe.Length / 1MB, 1)
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host "  VANILLA BUILD SUCCESSFUL!" -ForegroundColor Green
        Write-Host "  Output: $destPath" -ForegroundColor White
        Write-Host "  Size: $sizeMB MB" -ForegroundColor White
        Write-Host "==========================================`n" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: No installer EXE found in $nsisDir" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "  VANILLA BUILD FAILED!" -ForegroundColor Red
    Write-Host "  Originals have been restored." -ForegroundColor Yellow
    Write-Host "==========================================`n" -ForegroundColor Red
    exit 1
}

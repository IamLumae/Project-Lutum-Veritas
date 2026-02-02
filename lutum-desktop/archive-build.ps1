# archive-build.ps1
# Archives current build before creating new one

$ErrorActionPreference = "Continue"

$lutumDesktopPath = "C:\Users\hacka\Desktop\Neuer-Main-Server\new-server\Project Lutum Veritas\lutum-desktop"
$buildOutputPath = Join-Path $lutumDesktopPath "src-tauri\target\release\bundle\nsis"
$archivePath = Join-Path $lutumDesktopPath "dist\archive\exe"
$dateFolder = Get-Date -Format "yyyy-MM-dd"
$targetPath = Join-Path $archivePath $dateFolder

Write-Host "`n=== LUTUM VERITAS BUILD ARCHIVE SCRIPT ===" -ForegroundColor Cyan
Write-Host "Date: $dateFolder`n" -ForegroundColor Cyan

# Check if previous build exists
$existingBuilds = @(Get-ChildItem -Path $buildOutputPath -Filter "*.exe" -ErrorAction SilentlyContinue)

if ($existingBuilds.Count -gt 0) {
    Write-Host "Found $($existingBuilds.Count) existing build(s) to archive:" -ForegroundColor Yellow

    # Create archive folder structure
    New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
    Write-Host "Created archive directory: $targetPath" -ForegroundColor Green

    # Archive each EXE
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

    Write-Host "`nArchive complete! Files saved to:" -ForegroundColor Green
    Write-Host "  $targetPath`n" -ForegroundColor White
} else {
    Write-Host "No existing builds found in:" -ForegroundColor Yellow
    Write-Host "  $buildOutputPath" -ForegroundColor White
    Write-Host "Proceeding with fresh build...`n" -ForegroundColor Yellow
}

# Now run the build
Write-Host "=== STARTING BUILD PROCESS ===" -ForegroundColor Cyan
Write-Host "Running: npm run tauri build`n" -ForegroundColor White

Set-Location $lutumDesktopPath

try {
    # Run the actual Tauri build
    npm run tauri build

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=== BUILD SUCCESSFUL ===" -ForegroundColor Green
        Write-Host "New build available in: $buildOutputPath" -ForegroundColor White

        # List new builds
        $newBuilds = @(Get-ChildItem -Path $buildOutputPath -Filter "*.exe" -ErrorAction SilentlyContinue)
        if ($newBuilds.Count -gt 0) {
            Write-Host "`nNew build files:" -ForegroundColor Green
            foreach ($build in $newBuilds) {
                $sizeMB = [math]::Round($build.Length / 1MB, 2)
                Write-Host "  - $($build.Name) (${sizeMB} MB)" -ForegroundColor White
            }
        }
    } else {
        Write-Host "`n=== BUILD FAILED ===" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "`n=== BUILD ERROR ===" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== SCRIPT COMPLETE ===`n" -ForegroundColor Cyan

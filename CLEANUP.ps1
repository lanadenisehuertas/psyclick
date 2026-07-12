###############################################################
#  PsyClick — Space Cleanup Script
#  Deletes all regenerable build artifacts, caches, logs,
#  old releases, and dead-weight files.
#  Run as: Right-click > Run with PowerShell
#  (or from an elevated PowerShell terminal)
###############################################################

$root    = $PSScriptRoot   # the psyclick-1 folder
$clin    = Join-Path $root "psyclick-clinical"
$front   = Join-Path $root "frontend"
$cfront  = Join-Path $clin  "frontend"

function Remove-Safely {
    param ([string]$path)
    if (Test-Path $path) {
        Write-Host "  Removing: $path"
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  PsyClick Cleanup"
Write-Host "============================================================"
Write-Host ""

# ── 1. Build artifacts (fully regenerable) ───────────────────
#  NOTE: dist-electron / dist-electron-clinical are KEPT — they contain your
#        current installer EXEs. Only the intermediate build/ and dist-python/
#        folders (PyInstaller temp files) and the Vite frontend/dist are removed.
Write-Host "[1/5] Build artifacts (keeping installer EXEs)..."
Remove-Safely (Join-Path $root "build")
Remove-Safely (Join-Path $root "dist-python")
Remove-Safely (Join-Path $front "dist")
# KEPT: (Join-Path $front "dist-electron")          -- Standard installer lives here
Remove-Safely (Join-Path $clin  "build")
Remove-Safely (Join-Path $clin  "dist-python")
Remove-Safely (Join-Path $cfront "dist")
# KEPT: (Join-Path $cfront "dist-electron-clinical") -- Clinical installer lives here
Write-Host "  Done."

# ── 2. node_modules (regenerable with npm install) ────────────
Write-Host ""
Write-Host "[2/5] node_modules..."
Remove-Safely (Join-Path $front  "node_modules")
Remove-Safely (Join-Path $cfront "node_modules")
Remove-Safely (Join-Path $root   "Website")   # no source files, just dead node_modules
Write-Host "  Done."

# ── 3. Old release archives (~300 MB) ─────────────────────────
Write-Host ""
Write-Host "[3/5] Old release archives..."
Remove-Safely (Join-Path $root "psyclick-releases")
Write-Host "  Done."

# ── 4. Python caches ─────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] Python __pycache__..."
Remove-Safely (Join-Path $root  "__pycache__")
Remove-Safely (Join-Path $clin  "__pycache__")
Write-Host "  Done."

# ── 5. Junk files ────────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Logs, fix scripts, thesis docs, dead code..."

$junkFiles = @(
    # Logs
    (Join-Path $root   "api_stderr.log"),
    (Join-Path $root   "api_stdout.log"),
    (Join-Path $root   "build_log.txt"),
    (Join-Path $front  "installer-build.log"),
    (Join-Path $front  "vite-landing.log"),
    # One-time fix scripts (already applied)
    (Join-Path $root   "fix.py"),
    (Join-Path $root   "fix_backend.py"),
    (Join-Path $root   "fix_hitboxes.py"),
    (Join-Path $root   "fix_listeners.py"),
    # Old tkinter prototype (replaced by Electron)
    (Join-Path $root   "app.py"),
    # Database migration utilities
    (Join-Path $root   "migrate_sqlite_to_supabase.py"),
    (Join-Path $root   "migrate_supabase_to_supabase.py"),
    # Thesis documents (not part of the app)
    (Join-Path $root   "PsyClick_Thesis_Chapters3-4_UPDATED.docx"),
    (Join-Path $root   "chapter_4_revised.md"),
    (Join-Path $root   "thesis_corrections.md"),
    # Verification / notes files
    (Join-Path $root   "CRITICAL_FIX_LOG.txt"),
    (Join-Path $root   "OFFLINE_BUILD_SUMMARY.txt"),
    (Join-Path $root   "OFFLINE_FILES_REFERENCE.txt"),
    (Join-Path $root   "OFFLINE_VERIFICATION_REPORT.txt"),
    # Cowork metadata
    (Join-Path $root   "skills-lock.json"),
    # Dev utility
    (Join-Path $root   "test_connection.py"),
    # Empty folder
    (Join-Path $root   "docx_rendered")
)

foreach ($f in $junkFiles) {
    if (Test-Path $f) {
        Write-Host "  Removing: $f"
        Remove-Item -LiteralPath $f -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "  Done."

Write-Host ""
Write-Host "============================================================"
Write-Host "  Cleanup complete!"
Write-Host ""
Write-Host "  To rebuild:"
Write-Host "    Standard:  run BUILD_STANDARD.bat"
Write-Host "    Clinical:  cd psyclick-clinical && run BUILD_CLINICAL.bat"
Write-Host "    Offline:   cd psyclick-clinical && run BUILD_OFFLINE.bat"
Write-Host ""
Write-Host "  To restore node_modules:"
Write-Host "    cd frontend && npm install"
Write-Host "    cd psyclick-clinical\frontend && npm install"
Write-Host "============================================================"
Write-Host ""
pause

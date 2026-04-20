# ============================================================
# Build script for 360-to-RealityScan Windows executables
# Usage: .\Build\build.ps1
#        .\Build\build.ps1 -CondaEnv myenv
#        .\Build\build.ps1 -Target metashape -CondaEnv myenv
#        .\Build\build.ps1 -Target spheresfm
# ============================================================

param(
    [ValidateSet("all", "metashape", "spheresfm")]
    [string]$Target = "all",

    [string]$CondaEnv = "gs_env"
)

$BuildDir = $PSScriptRoot
$DistDir  = Join-Path $BuildDir "dist"

# ── Auto-detect conda executable ──
function Find-Conda {
    $inPath = Get-Command conda -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    $candidates = @(
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\anaconda3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\anaconda3\Scripts\conda.exe",
        "C:\ProgramData\miniconda3\Scripts\conda.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$CondaExe = Find-Conda
if (-not $CondaExe) {
    Write-Error "conda not found. Install Anaconda/Miniconda or add conda to your PATH."
    exit 1
}

Write-Host "🐍 conda  : $CondaExe" -ForegroundColor DarkGray
Write-Host "🌐 env    : $CondaEnv" -ForegroundColor DarkGray

# ── Check / install PyInstaller ──
Write-Host "🔍 Checking PyInstaller..." -ForegroundColor Cyan
& $CondaExe run -n $CondaEnv python -m PyInstaller --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "📦 Installing PyInstaller..." -ForegroundColor Yellow
    & $CondaExe run -n $CondaEnv pip install pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "Failed to install PyInstaller" }
}
Write-Host "✅ PyInstaller ready" -ForegroundColor Green

# ── Build function ──
function Build-Exe {
    param(
        [string]$ScriptName,
        [string]$ExeName
    )
    $ScriptPath = Join-Path $BuildDir $ScriptName
    Write-Host ""
    Write-Host "🔨 Building $ExeName from $ScriptName ..." -ForegroundColor Cyan

    & $CondaExe run -n $CondaEnv python -m PyInstaller `
        "--onefile" `
        "--windowed" `
        "--name" $ExeName `
        "--distpath" $DistDir `
        "--workpath" (Join-Path $BuildDir "build_tmp") `
        "--specpath" (Join-Path $BuildDir "spec") `
        "--clean" `
        $ScriptPath

    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ PyInstaller exited with code $LASTEXITCODE"
        return
    }

    $ExePath = Join-Path $DistDir "$ExeName.exe"
    if (Test-Path $ExePath) {
        $size = [math]::Round((Get-Item $ExePath).Length / 1MB, 1)
        Write-Host "✅ $ExeName.exe built successfully ($size MB)" -ForegroundColor Green
        Write-Host "   → $ExePath"
    } else {
        Write-Error "❌ Build failed: $ExePath not found"
    }
}

# ── Run builds ──
Push-Location $BuildDir
try {
    if ($Target -eq "all" -or $Target -eq "metashape") {
        Build-Exe -ScriptName "metashape_to_realityscan.py" -ExeName "MetashapeToRS"
    }
    if ($Target -eq "all" -or $Target -eq "spheresfm") {
        Build-Exe -ScriptName "spheresfm_to_realityscan.py" -ExeName "SphereSfMToRS"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "🎉 Build complete! Output: $DistDir" -ForegroundColor Green

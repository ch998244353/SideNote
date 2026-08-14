$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Join-Path $projectRoot "src"
$assetsDir = Join-Path $projectRoot "assets"
$distDir = Join-Path $projectRoot "dist"
$workDir = Join-Path $projectRoot "build"

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($pythonVersion -ne "3.14") {
    throw "SideNote currently requires Python 3.14; found Python $pythonVersion."
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "SideNote" `
    --icon "$(Join-Path $assetsDir 'sidenote-icon.ico')" `
    --distpath $distDir `
    --workpath $workDir `
    --specpath $projectRoot `
    --add-data "$(Join-Path $sourceDir 'original_side_note.marshal');." `
    --add-data "$assetsDir;assets" `
    (Join-Path $sourceDir "side_note.pyw")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Built: $(Join-Path $distDir 'SideNote.exe')"

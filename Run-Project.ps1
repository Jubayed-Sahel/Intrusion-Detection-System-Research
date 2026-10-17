# Run from PowerShell using: .\Run-Project.ps1
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv-reproduction\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    $projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Python environment missing. Follow the environment setup in README.md.'
}
& $projectPython (Join-Path $PSScriptRoot 'run_project.py') @args
if ($LASTEXITCODE -ne 0) { throw "Project run failed (exit code $LASTEXITCODE)." }

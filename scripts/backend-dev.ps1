$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"

if (-not (Test-Path $backendPath)) {
    throw "Khong tim thay thu muc backend: $backendPath"
}

$activeVenvPython = $null
if ($env:VIRTUAL_ENV) {
    $candidate = Join-Path $env:VIRTUAL_ENV "Scripts\\python.exe"
    if (Test-Path $candidate) {
        $activeVenvPython = $candidate
    }
}

$pythonCandidates = @(
    $activeVenvPython,
    (Join-Path $backendPath "venv\\Scripts\\python.exe"),
    (Join-Path $backendPath ".venv\\Scripts\\python.exe"),
    (Join-Path $projectRoot ".venv\\Scripts\\python.exe")
) | Where-Object { $_ }

$pythonExe = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$pythonArgs = @()

if (-not $pythonExe) {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $pythonExe = $pyCommand.Source
        $pythonArgs = @("-3")
    }
    else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $pythonExe = $pythonCommand.Source
        }
    }
}

if (-not $pythonExe) {
    throw "Khong tim thay Python. Hay tao venv trong backend\\venv hoac .venv truoc."
}

Write-Host "Using Python: $pythonExe"

Push-Location $backendPath
try {
    & $pythonExe @pythonArgs -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}
finally {
    Pop-Location
}

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendScript = Join-Path $PSScriptRoot "backend-dev.ps1"

if (-not (Test-Path $backendScript)) {
    throw "Khong tim thay script backend: $backendScript"
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
}

if (-not $npmCommand) {
    throw "Khong tim thay npm. Hay cai Node.js truoc."
}

$backendArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $backendScript
)

$backendProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $backendArgs `
    -WorkingDirectory $projectRoot `
    -PassThru

Write-Host "Backend started (PID: $($backendProcess.Id)). Frontend dang khoi dong..."

Push-Location $projectRoot
try {
    & $npmCommand.Source "--prefix" "frontend" "run" "dev"
}
finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Write-Host "Stopping backend (PID: $($backendProcess.Id))..."
        Stop-Process -Id $backendProcess.Id -Force
    }

    Pop-Location
}

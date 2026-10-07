# Start the PRISM Engine backend (port 8000) and frontend (port 5173) on Windows.
# Usage: powershell -ExecutionPolicy Bypass -File dev.ps1   (Ctrl+C stops both)

$root = $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"

$backend = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory (Join-Path $root "backend") -NoNewWindow -PassThru

try {
    Push-Location (Join-Path $root "frontend")
    npm run dev
}
finally {
    Pop-Location
    if (-not $backend.HasExited) {
        taskkill /PID $backend.Id /T /F | Out-Null
    }
}

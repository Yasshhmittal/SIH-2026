<#
.SYNOPSIS
    Start PRAHARI and open an interactive prompt.

.DESCRIPTION
    Checks Ollama, starts the backend if it is not already listening, then
    drops into a loop where you type tasks and watch the agent work.

.EXAMPLE
    .\prahari.ps1
    .\prahari.ps1 -Once "Draft an approval note for elbow E-14"
#>
param(
    [string]$Once = "",
    [int]$Port = 8077
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $root "backend"

function Write-Step($text) { Write-Host "  $text" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "  PRAHARI" -ForegroundColor Cyan -NoNewline
Write-Host "  -  sovereign on-premise agentic AI workbench"
Write-Host ("  " + ("-" * 60)) -ForegroundColor DarkGray

# --- prerequisites --------------------------------------------------------

if (-not (Test-Path $python)) {
    Write-Host "  ERROR: no virtualenv at .venv" -ForegroundColor Red
    Write-Host "  Run:  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "        .venv\Scripts\python -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

try {
    $tags = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    Write-Step "ollama    up ($($tags.models.Count) models pulled)"
} catch {
    Write-Host "  ERROR: Ollama is not responding on 127.0.0.1:11434" -ForegroundColor Red
    Write-Host "  Start it, then run this again." -ForegroundColor Yellow
    exit 1
}

# --- backend --------------------------------------------------------------

$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($listening) {
    Write-Step "backend   already running on port $Port"
} else {
    Write-Step "backend   starting on port $Port ..."
    Start-Process -FilePath $python `
        -ArgumentList "-m","uvicorn","prahari.main:app","--host","127.0.0.1","--port","$Port","--log-level","warning" `
        -WorkingDirectory $root `
        -RedirectStandardOutput (Join-Path $env:TEMP "prahari_out.log") `
        -RedirectStandardError  (Join-Path $env:TEMP "prahari_err.log") `
        -WindowStyle Hidden

    $ready = $false
    foreach ($i in 1..30) {
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
            if ($health.status -eq "ok") { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 700
    }

    if (-not $ready) {
        Write-Host "  ERROR: backend did not come up" -ForegroundColor Red
        Get-Content (Join-Path $env:TEMP "prahari_err.log") -ErrorAction SilentlyContinue |
            Select-Object -Last 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
        exit 1
    }
}

$h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 5
Write-Step "profile   $($h.profile.name) - budget $($h.profile.budget_mb) MB - $($h.models.available.Count) models"
Write-Step "api       http://127.0.0.1:$Port/docs"
Write-Host ""

# --- single task and exit -------------------------------------------------

if ($Once) {
    & $python (Join-Path $root "scripts\run_task.py") $Once
    exit $LASTEXITCODE
}

# --- interactive ----------------------------------------------------------

Write-Host "  Type a task and press Enter. Blank line runs the flagship demo." -ForegroundColor DarkGray
Write-Host "  'quit' to exit." -ForegroundColor DarkGray
Write-Host ""

while ($true) {
    Write-Host "prahari> " -ForegroundColor Cyan -NoNewline
    $task = Read-Host

    if ($task -in @("quit", "exit", "q")) {
        Write-Host "  backend left running on port $Port" -ForegroundColor DarkGray
        break
    }

    & $python (Join-Path $root "scripts\run_task.py") $task
    Write-Host ""
}

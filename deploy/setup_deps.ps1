# ================================================================
#  SUSTech RAG - Worker environment check & dependency setup (Windows)
#  Prerequisite: repo cloned, model files placed in backend\data\models\
#  Usage:
#    .\deploy\install_worker.ps1
# ================================================================
param()

$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Green
Write-Host "  SUSTech RAG - Worker Installer (Windows)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

$WorkerDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# ---- Step 1: Python ----
Write-Host "[1/4] Checking Python..." -ForegroundColor Cyan
$python = $null
foreach ($py in @("python3.11", "python3.12", "python3", "python")) {
    $result = Get-Command $py -ErrorAction SilentlyContinue
    if ($result) {
        try {
            $ver = & $py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -and [version]$ver -ge [version]"3.11") { $python = $py; break }
        } catch {}
    }
}

if (-not $python) {
    Write-Host "Python 3.11+ not found." -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Check 'Add Python to PATH' then re-run." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Python: $(& $python --version)" -ForegroundColor Green

# ---- Step 2: uv ----
Write-Host "[2/4] Checking uv..." -ForegroundColor Cyan
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    $uvDir = "$env:USERPROFILE\.local\bin"
    New-Item -ItemType Directory -Path $uvDir -Force | Out-Null
    $uvZip = "$env:TEMP\uv.zip"
    Invoke-WebRequest -Uri "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -OutFile $uvZip
    Expand-Archive -Path $uvZip -DestinationPath $uvDir -Force
    $env:Path = "$uvDir;$env:Path"
}
Write-Host "  uv: $(uv --version)" -ForegroundColor Green

# ---- Step 3: Install dependencies ----
Write-Host "[3/4] Installing Python packages..." -ForegroundColor Cyan
Set-Location "$WorkerDir\backend"
$syncOutput = uv sync 2>&1
$syncOutput | Select-Object -Last 5
Write-Host "  Done." -ForegroundColor Green

# ---- Step 4: Check models ----
Write-Host "[4/4] Checking models..." -ForegroundColor Cyan
if (-not (Test-Path "data\models\llm\qwen\Qwen3-8B-Q4_K_M.gguf")) {
    Write-Host "Model file not found: backend\data\models\llm\qwen\Qwen3-8B-Q4_K_M.gguf" -ForegroundColor Red
    Write-Host "Please download the model first, then re-run this script:" -ForegroundColor Yellow
    Write-Host "  cd $WorkerDir\backend" -ForegroundColor Gray
    Write-Host "  uv run sustech-rag download-model" -ForegroundColor Gray
    Write-Host "  uv run sustech-rag download-llama" -ForegroundColor Gray
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Model OK." -ForegroundColor Green

Write-Host ""
Write-Host "Environment ready. Start:" -ForegroundColor Green
Write-Host "  cd $WorkerDir\backend" -ForegroundColor Gray
Write-Host "  uv run sustech-rag worker --relay wss://<relay-host>/ws/worker    # relay worker" -ForegroundColor Gray
Write-Host "  uv run sustech-rag serve                                         # local API server" -ForegroundColor Gray

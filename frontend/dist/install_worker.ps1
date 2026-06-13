# ================================================================
#  SUSTech RAG - Worker 一键安装 & 启动 (Windows)
#  用法:
#    irm https://urjjlhfvjzyi.sealosgzg.site/install_worker.ps1 | iex
#    .\install_worker.ps1 -Relay wss://xx/ws/worker
#  环境变量: $env:RELAY_URL, $env:WORKER_ID
# ================================================================
param(
    [string]$Relay = $env:RELAY_URL,
    [string]$WorkerId = $env:WORKER_ID,
    [string]$Config = ""
)

$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Green
Write-Host "  SUSTech RAG - Worker Installer (Windows)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# ---- Step 1: Python ----
Write-Host "[1/5] Checking Python..." -ForegroundColor Cyan
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
    Write-Host "Python 3.11+ not found." -ForegroundColor Yellow
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Check 'Add Python to PATH' then re-run." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Python: $(& $python --version)" -ForegroundColor Green

# ---- Step 2: uv ----
Write-Host "[2/5] Installing uv..." -ForegroundColor Cyan
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

# ---- Step 3: 下载代码 ----
Write-Host "[3/5] Downloading worker code..." -ForegroundColor Cyan
$workerDir = "$env:USERPROFILE\sustech-rag-worker"
if (-not (Test-Path "$workerDir\backend")) {
    New-Item -ItemType Directory -Path $workerDir -Force | Out-Null
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        $null = git clone --depth 1 https://github.com/dove667/SUSTech-RAG.git $workerDir 2>&1
    }
    if (-not (Test-Path "$workerDir\backend")) {
        Write-Host "  Downloading zip..." -ForegroundColor Gray
        $zipPath = "$env:TEMP\sustech-rag.zip"
        Invoke-WebRequest -Uri "https://github.com/dove667/SUSTech-RAG/archive/refs/heads/main.zip" -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
        Move-Item "$env:TEMP\SUSTech-RAG-main" $workerDir -Force
    }
}
Set-Location "$workerDir\backend"

# ---- Step 4: 安装依赖 ----
Write-Host "[4/5] Installing Python packages (5-15 min)..." -ForegroundColor Cyan
$syncOutput = uv sync 2>&1
$syncOutput | Select-Object -Last 5
Write-Host "  Done." -ForegroundColor Green

# ---- Step 5: 模型提示 ----
Write-Host "[5/5] Checking models..." -ForegroundColor Cyan
if (-not (Test-Path "data\models\llm\qwen\Qwen3-8B-Q4_K_M.gguf")) {
    Write-Host "  Models not downloaded. Run:" -ForegroundColor Yellow
    Write-Host "    cd $workerDir\backend" -ForegroundColor Gray
    Write-Host "    uv run sustech-rag download-model" -ForegroundColor Gray
    Write-Host "    uv run sustech-rag download-llama" -ForegroundColor Gray
}

# ---- 启动 ----
if (-not $Relay) {
    Write-Host ""
    Write-Host "No relay specified. Start manually:" -ForegroundColor Yellow
    Write-Host "  cd $workerDir\backend" -ForegroundColor Gray
    Write-Host "  uv run sustech-rag worker --relay wss://xxx/ws/worker" -ForegroundColor Gray
    Read-Host "Press Enter to exit"
    exit 0
}

Write-Host ""
Write-Host "Starting worker -> $Relay" -ForegroundColor Green
$uvArgs = @("run", "sustech-rag", "worker", "--relay", $Relay)
if ($WorkerId) { $uvArgs += "--worker-id"; $uvArgs += $WorkerId }
if ($Config)   { $uvArgs += "--config"; $uvArgs += $Config }
uv $uvArgs

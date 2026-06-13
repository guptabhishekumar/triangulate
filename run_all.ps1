# Set up the three isolated environments and run the full pipeline end-to-end.
# Windows PowerShell. Requires the Python 3.12 launcher (`py -3.12`).
#
#   powershell -ExecutionPolicy Bypass -File run_all.ps1
#
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function New-Venv($name, $req) {
    $py = Join-Path $root "$name\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Write-Host "Creating $name ..." -ForegroundColor Cyan
        py -3.12 -m venv (Join-Path $root $name)
        & $py -m pip install --upgrade pip -q
    }
    & $py -m pip install -q -r (Join-Path $root $req)
    return $py
}

# 1. Environments
$vbt  = New-Venv ".venv-vectorbt" "01_vectorbt\requirements.txt"
& $vbt -m pip install -q -r (Join-Path $root "data\requirements.txt")
$naut = New-Venv ".venv-nautilus" "02_nautilus\requirements.txt"
$mt5  = New-Venv ".venv-mt5"      "03_mt5\requirements.txt"

# 2. Data (only if missing)
if (-not (Test-Path (Join-Path $root "data\eurusd_h1.csv"))) {
    Write-Host "Pulling data ..." -ForegroundColor Cyan
    & $vbt (Join-Path $root "data\get_data.py") --source dukascopy
}

# 3. Tests
Write-Host "`nRunning tests ..." -ForegroundColor Cyan
& $vbt -m pytest (Join-Path $root "tests") -q

# 4. The three legs
Write-Host "`n=== vectorbt ===" -ForegroundColor Green
& $vbt  (Join-Path $root "01_vectorbt\run.py")
Write-Host "`n=== nautilus ===" -ForegroundColor Green
& $naut (Join-Path $root "02_nautilus\run.py")
Write-Host "`n=== mt5 (python api) ===" -ForegroundColor Green
& $mt5  (Join-Path $root "03_mt5\run.py")

# 5. Comparison table
Write-Host "`n=== comparison ===" -ForegroundColor Green
& $vbt (Join-Path $root "compare.py")

Write-Host "`nDone. See results/metrics.csv and results/comparison.md." -ForegroundColor Cyan
Write-Host "For the official MT5 result, run the EA in the Strategy Tester (03_mt5/README.md)."

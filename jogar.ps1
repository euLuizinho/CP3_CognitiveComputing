# jogar.ps1 - Launcher do Muro Humano para PowerShell
# Usa diretamente o Python do venv (sem precisar ativar)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERRO] Venv nao encontrado! Rode primeiro:" -ForegroundColor Red
    Write-Host "  cd $ProjectRoot" -ForegroundColor Yellow
    Write-Host "  uv venv" -ForegroundColor Yellow
    Write-Host "  uv pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Set-Location $ProjectRoot
Write-Host "=============================================="
Write-Host "      MURO HUMANO - INICIANDO O JOGO"
Write-Host "=============================================="
& $VenvPython main.py @args

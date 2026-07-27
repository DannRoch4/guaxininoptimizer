# Guaxinim Optimizer — instalador de um comando so.
# Uso (comprador cola isso no PowerShell):
#   irm https://raw.githubusercontent.com/DannRoch4/guaxininoptimizer/main/install.ps1 | iex
#
# IMPORTANTE: troque a URL abaixo pelo link de download DIRETO do .exe que o Kiwify
# entrega pra quem comprou (ou outro link privado seu). NAO aponte pra dentro deste
# repositorio publico — qualquer um acharia o .exe so navegando aqui, e o gate de
# compra do Kiwify deixaria de valer pra alguma coisa.

$ErrorActionPreference = "Stop"

$url  = "https://SUBSTITUA-PELO-LINK-DIRETO-DO-EXE-AQUI.exe"
$dest = Join-Path $env:TEMP "GuaxinimOptimizer.exe"

Write-Host "Baixando Guaxinim Optimizer..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
} catch {
    Write-Host "Falha ao baixar: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Abrindo Guaxinim Optimizer..." -ForegroundColor Cyan
Start-Process -FilePath $dest

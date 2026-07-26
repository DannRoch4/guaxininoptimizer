@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Guaxinim Optimizer - Build do .exe
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado no PATH.
    pause
    exit /b 1
)

echo Instalando/atualizando dependencias (pyinstaller, pillow)...
python -m pip install --upgrade pyinstaller pillow >nul
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist GuaxinimOptimizer.spec del /q GuaxinimOptimizer.spec

echo Gerando icone/logo atualizados...
python assets\generate_icon.py
if errorlevel 1 (
    echo [ERRO] Falha ao gerar o icone.
    pause
    exit /b 1
)

echo Atualizando numero da build...
python bump_version.py
if errorlevel 1 (
    echo [ERRO] Falha ao atualizar o numero da build.
    pause
    exit /b 1
)

echo.
echo Compilando o executavel (pega todos os .py atuais da pasta)...
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin ^
    --name "GuaxinimOptimizer" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERRO] O build falhou. Veja o log acima.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build concluido: dist\GuaxinimOptimizer.exe
echo ============================================
pause

@echo off
title ISO 5167-2 — Calculadora Placa de Orificio

echo.
echo  ===================================================
echo   ISO 5167-2  Placa de Orificio - Calculadora
echo  ===================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado. Instale em https://python.org
    pause
    exit /b 1
)

echo  [1/3] Verificando/instalando dependencias...
pip install -r requirements.txt --quiet

echo  [2/3] Iniciando servidor Flask na porta 5167...
echo  [3/3] Abrindo navegador em http://localhost:5167
echo.
echo  Pressione Ctrl+C para encerrar o servidor.
echo.

python app.py

pause

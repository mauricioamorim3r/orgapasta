@echo off
rem If using a virtual environment, activate it first before running this script.
rem Example: call .venv\Scripts\activate.bat
setlocal
cd /d "%~dp0"
start "" python app.py
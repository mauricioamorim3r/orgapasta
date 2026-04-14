@echo off
rem If using a virtual environment, activate it first before running this script.
rem Example: call .venv\Scripts\activate.bat
cd /d %~dp0
start "" pythonw app.py

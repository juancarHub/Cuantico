@echo off
setlocal
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"
set "VENV_PYTHON=%BASE_DIR%.venv\Scripts\python.exe"

"%VENV_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo Primero ejecuta Run_Cuanti.bat para preparar el entorno virtual.
    pause
    exit /b 1
)

"%VENV_PYTHON%" src\server_main.py

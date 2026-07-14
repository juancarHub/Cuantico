@echo off
setlocal

REM Obtener la carpeta donde está el script
set BASE_DIR=%~dp0

:: Cambiar a esa carpeta
cd /d "%BASE_DIR%"

set "VENV_PYTHON=%BASE_DIR%.venv\Scripts\python.exe"
"%VENV_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo El entorno virtual no funciona en este equipo. Reconstruyendolo...
    if exist "%BASE_DIR%.venv" rmdir /s /q "%BASE_DIR%.venv"
    set "BASE_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if not exist "%BASE_PYTHON%" (
        echo No encuentro Python 3. Instala Python 3.10 o superior desde python.org.
        pause
        exit /b 1
    )
    "%BASE_PYTHON%" -m venv "%BASE_DIR%.venv"
    "%VENV_PYTHON%" -m pip install --upgrade pip
    "%VENV_PYTHON%" -m pip install -r "%BASE_DIR%requirements.txt"
)

start "CUANTICO" cmd /k ""%VENV_PYTHON%" "src\main_minimal.py""
timeout /t 5

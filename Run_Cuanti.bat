@echo off

REM Obtener la carpeta donde está el script
set BASE_DIR=%~dp0

:: Cambiar a esa carpeta
cd /d "%BASE_DIR%"
 

REM set BASE_DIR=D:\JUAN CARLOS\7 - IA Develop\Luna_mpv


start "SUMMARY-W" cmd /k "cd /d %BASE_DIR% && .\.venv\Scripts\activate && python src/main_minimal.py
timeout /t 5

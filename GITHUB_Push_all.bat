@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo.
@echo off
setlocal EnableExtensions

echo.
echo ==============================
echo   GIT AUTO ADD+COMMIT+PUSH
echo ==============================
echo.

cd /d "%~dp0"
echo Carpeta actual: %CD%
echo.

REM 1) Comprobar Git
where git >nul 2>&1
if errorlevel 1 goto NO_GIT

REM 2) Comprobar repo
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto NO_REPO

echo Repo top-level:
git rev-parse --show-toplevel
echo.

echo === STATUS (ANTES) ===
git status -sb
echo.

set "MSG="
set /p MSG=Mensaje de commit (Enter = Update): 
if "%MSG%"=="" set "MSG=Update"

echo.
echo === GIT ADD -A ===
git add -A
if errorlevel 1 goto ADD_FAIL

echo.
echo === GIT COMMIT ===
git commit -m "%MSG%"
REM si no hay nada que commitear, Git devuelve errorlevel 1. No pasa nada, seguimos.

echo.
echo === GIT PUSH ===
git push
if errorlevel 1 goto PUSH_FAIL

echo.
echo === OK: Subido a GitHub ===
goto END

:NO_GIT
echo [ERROR] Git no esta instalado o no esta en el PATH.
goto END

:NO_REPO
echo [ERROR] Esta carpeta NO es un repositorio Git.
echo         Pon este .bat en la raiz del repo (donde exista .git).
goto END

:ADD_FAIL
echo [ERROR] Fallo en git add.
goto END

:PUSH_FAIL
echo [ERROR] Fallo en git push.
echo         Puede que necesites git pull, o haya conflictos, o no haya remoto configurado.
goto END

:END
echo.
pause
endlocal
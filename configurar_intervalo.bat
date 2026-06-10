@echo off
cd /d "%~dp0"
echo ============================================
echo  Definir a frequencia de atualizacao do status
echo ============================================
echo.
echo  Quantos segundos entre cada atualizacao do Discord?
echo  Permitido: 2 a 3600.   Maior = mais seguro.   Padrao: 5.
echo.
set "SEG="
set /p "SEG=Digite o numero de segundos: "
if "%SEG%"=="" ( echo. & echo Nada digitado. Nenhuma alteracao. & echo. & pause & exit /b )
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% lyrics.py --set-interval %SEG%
echo.
pause

@echo off
cd /d "%~dp0"
echo ============================================
echo  Ativar inicio automatico com o Windows
echo  (roda escondido, sem janela)
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_autostart.ps1"
echo.
pause

@echo off
cd /d "%~dp0"
echo ============================================
echo  Instalando as dependencias do Python...
echo ============================================
echo.
REM usa o "py" launcher se existir (acha o Python real, nao o atalho da Store)
where py >nul 2>nul
if %errorlevel%==0 (
    py -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt
)
echo.
if %errorlevel%==0 (
    echo Pronto! Dependencias instaladas com sucesso.
) else (
    echo Algo deu errado. Verifique se o Python esta instalado
    echo ^(python.org^) e marcado em "Add python.exe to PATH".
)
echo.
pause

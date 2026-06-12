@echo off
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo ============================================
echo  Escolher o idioma da interface
echo ============================================
echo.
echo  Idiomas disponiveis:
%PY% -c "import lang; print('   ' + ' '.join(lang.available()))"
echo.
echo  (deixe vazio para deteccao automatica do Windows)
echo.
set "L="
set /p "L=Digite o codigo do idioma: "
if "%L%"=="" (
  if exist lang.txt del lang.txt
  echo.
  echo Idioma: deteccao automatica.
) else (
  %PY% lyrics.py --set-lang %L%
)
echo.
pause

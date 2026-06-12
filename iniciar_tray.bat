@echo off
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
where pyw >nul 2>nul && (set "PYW=pyw") || (set "PYW=pythonw")
REM instala pystray/pillow na primeira vez, se faltar
%PY% -c "import pystray, PIL" 2>nul || %PY% -m pip install pystray pillow
REM abre o app de bandeja sem janela de console
start "" %PYW% "%~dp0tray.py"

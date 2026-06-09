@echo off
cd /d "%~dp0"
echo ============================================
echo  MODO TESTE (preview)
echo  Mostra a letra aqui no terminal, SEM mexer
echo  no Discord e SEM precisar de token.
echo ============================================
echo.
echo Toque uma musica e veja a letra aparecer abaixo.
echo Feche esta janela (ou aperte Ctrl+C) para sair.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py lyrics.py --preview
) else (
    python lyrics.py --preview
)
pause

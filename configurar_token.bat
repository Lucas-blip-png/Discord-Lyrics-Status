@echo off
cd /d "%~dp0"
echo ============================================
echo  Configurar token do Discord (salva token.txt)
echo  O token NAO sera enviado a lugar nenhum, so
echo  salvo neste PC, na pasta do projeto.
echo ============================================
powershell -NoProfile -Command "$t = Read-Host 'Cole seu token e tecle Enter'; $t = $t.Trim(); if ($t) { Set-Content -Path 'token.txt' -Value $t -NoNewline -Encoding ascii; Write-Host 'Salvo em token.txt com sucesso!' } else { Write-Host 'Nada foi informado. Nenhuma alteracao.' }"
echo.
pause

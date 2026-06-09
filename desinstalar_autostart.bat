@echo off
echo ============================================
echo  Desativar inicio automatico com o Windows
echo ============================================
echo.
powershell -NoProfile -Command "$v = Join-Path ([Environment]::GetFolderPath('Startup')) 'DiscordLyricsStatus.vbs'; if (Test-Path $v) { Remove-Item $v -Force; Write-Host 'Autostart REMOVIDO. Nao vai mais iniciar com o Windows.' } else { Write-Host 'Autostart nao estava instalado (nada a fazer).' }"
echo.
echo (Isso nao para o programa que ja estiver rodando. Use parar.bat para isso.)
echo.
pause

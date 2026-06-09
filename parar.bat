@echo off
echo Encerrando o Discord Lyrics Status...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*lyrics.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host 'Pronto (se estava rodando, foi encerrado).'"
echo.
pause

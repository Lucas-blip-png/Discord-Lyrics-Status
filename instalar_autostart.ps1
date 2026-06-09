# Cria um atalho na pasta de Inicializacao do Windows para o programa
# iniciar sozinho (escondido) toda vez que voce ligar o PC.
$ErrorActionPreference = 'Stop'

$proj = $PSScriptRoot
if (-not $proj) { $proj = (Get-Location).Path }

# Localiza o pythonw.exe CERTO perguntando ao proprio Python.
# Usa o "py" launcher primeiro (acha o Python instalado de verdade, nao o
# atalho da Microsoft Store em WindowsApps, que e so um stub de 0 bytes).
$pyw = $null
foreach ($cmd in @('py', 'python')) {
    try {
        $exe = (& $cmd -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1)
    } catch {
        $exe = $null
    }
    if ($exe -and (Test-Path $exe) -and ($exe -notmatch 'WindowsApps')) {
        $cand = Join-Path (Split-Path $exe) 'pythonw.exe'
        if (Test-Path $cand) { $pyw = $cand; break }
    }
}
if (-not $pyw) {
    Write-Host ''
    Write-Host 'ERRO: nao encontrei o pythonw.exe do seu Python.'
    Write-Host 'Instale o Python em python.org marcando "Add python.exe to PATH" e tente de novo.'
    Write-Host '(Evite a versao da Microsoft Store.)'
    exit 1
}

$lyrics  = Join-Path $proj 'lyrics.py'
$startup = [Environment]::GetFolderPath('Startup')
$vbs     = Join-Path $startup 'DiscordLyricsStatus.vbs'

$content = @"
' Inicia o Discord Lyrics Status escondido (sem janela) no logon do Windows.
' Para desativar: rode desinstalar_autostart.bat OU apague este arquivo
' (Win+R -> shell:startup).
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$proj"
sh.Run """$pyw"" ""$lyrics""", 0, False
"@

Set-Content -Path $vbs -Value $content -Encoding ascii

Write-Host ''
Write-Host 'Autostart INSTALADO com sucesso!'
Write-Host ('  Python : ' + $pyw)
Write-Host ('  Script : ' + $lyrics)
Write-Host ('  Atalho : ' + $vbs)
Write-Host ''
Write-Host 'Vai iniciar sozinho toda vez que voce ligar o PC.'
Write-Host 'Para comecar AGORA sem reiniciar, de dois cliques no atalho acima.'
Write-Host '(Lembre de salvar seu token antes, com configurar_token.bat)'

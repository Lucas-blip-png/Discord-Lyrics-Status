# 📱 Discord Lyrics — app Android (nativo)

App Android que lê a música tocando em **qualquer** player (Spotify, YouTube
Music, etc.) e sincroniza a letra com o seu **status do Discord** — sem precisar
de Termux nem de login do Spotify.

> ⚠️ **EXPERIMENTAL.** Este app foi escrito mas **ainda não foi testado num
> aparelho real** — pode precisar de ajustes. Veja "Status" abaixo.

## ⚠️ Aviso (igual ao resto do projeto)
É um **selfbot**: usa o seu *token*, **viola os Termos do Discord** e pode dar
**ban**. O token fica salvo **só no aparelho**. Use por sua conta e risco.

## Como funciona
- Pede **"acesso a notificações"** (Notification Listener) — é isso que permite
  ler a sessão de mídia ativa (título, artista, posição) de qualquer app.
- Busca a letra sincronizada no **lrclib.net**.
- Faz `PATCH` no `users/@me/settings` do Discord com o seu token.
- Roda como **serviço em primeiro plano** (notificação fixa) para não morrer.

## Como obter o APK
Não precisa de Android Studio — o **GitHub Actions** compila pra você:
1. Aba **Actions** → workflow **Build Android APK** → último run → baixe o
   artifact `DiscordLyrics-debug-apk` (ou pegue o `.apk` anexado numa Release).
2. No celular, ative **"Instalar apps desconhecidos"** e instale o `app-debug.apk`.

(Quem tiver Android Studio pode abrir a pasta `android/` e rodar direto.)

## Como usar
1. Abra o app, **cole o token** do Discord e o **intervalo** (segundos).
2. Toque em **"Conceder acesso a notificações"** e ative o app na lista.
3. Toque em **"Salvar e iniciar"**. Toque uma música. 🎶
4. Para parar: botão **Parar** (ou desligue o acesso a notificações).

### Iniciar sozinho quando ligar o celular
Marque **"Iniciar automaticamente quando ligar o celular"**. Aí ele sobe sozinho
no boot, sem você abrir o app.

> ⚠️ Em vários celulares (Xiaomi/MIUI, Samsung, Oppo, etc.) o Android bloqueia
> apps de iniciarem no boot até você liberar manualmente. Se não subir sozinho:
> - Ative **"Autostart" / "Inicialização automática"** para o app nas configurações.
> - Tire o app da **otimização de bateria** (deixe "sem restrições").
>
> Se mesmo assim não subir após reiniciar, é só abrir o app uma vez.

## Status / o que falta
- [ ] Testar num aparelho real e ajustar (detecção de mídia varia por fabricante).
- [ ] Tratar melhor múltiplos players tocando ao mesmo tempo.
- [ ] Ícone/UI mais caprichados; i18n (hoje os textos estão em PT).
- [ ] Build assinado de release (hoje é APK de **debug**).

## Estrutura
- `app/src/main/java/.../` — `MainActivity` (UI), `LyricsService` (loop em
  primeiro plano), `MediaListenerService` (habilita a leitura de mídia),
  `Net` (lrclib + Discord), `Prefs` (token/intervalo).
- Build: Gradle (AGP 8.5 / Kotlin 1.9 / compileSdk 34, minSdk 26).

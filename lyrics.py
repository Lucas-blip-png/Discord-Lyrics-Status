import argparse
import asyncio
import os
import sys
import re
import time

import requests
import syncedlyrics
from datetime import datetime, timezone

# winrt foi dividido em vários pacotes; "winsdk" empacota tudo num só.
# Tentamos os dois para facilitar a instalacao.
try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
except ImportError:  # pragma: no cover
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------
def load_token():
    """Le o token do ambiente (DISCORD_TOKEN) ou de um token.txt ao lado do script.

    NUNCA cole seu token direto no codigo: assim ele nao vaza se voce
    compartilhar/subir o arquivo pra algum lugar.
    """
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if token:
        return token

    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "token.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""


DISCORD_TOKEN = load_token()

# Modo preview: mostra a letra no terminal sem tocar no Discord.
PREVIEW = False

# True so quando ha um terminal real. Fica False ao rodar via pythonw
# (escondido) ou com a saida redirecionada -> evita lixo no terminal e o
# "flash" de janela do cls no boot. As atualizacoes do Discord continuam.
try:
    INTERACTIVE = bool(sys.stdout) and sys.stdout.isatty()
except Exception:
    INTERACTIVE = False


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------
def hide_cursor():
    if not INTERACTIVE:
        return
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    if not INTERACTIVE:
        return
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def clear_line_area():
    if not INTERACTIVE:
        return
    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Lyric cleanup
# ---------------------------------------------------------------------------
def clean_lyric(text):
    if not text:
        return None

    text = text.replace("\r", "").strip()

    # descarta linhas que parecem metadata/credito
    if "/" in text and len(text) > 40:
        return None

    if re.search(r"[a-z][A-Z][a-z]", text):
        return None

    if len(text) > 80:
        return None

    # descarta se mais de 40% for simbolo/numero
    if len(re.sub(r"[a-zA-Z ]", "", text)) > len(text) * 0.4:
        return None

    return text


def fix_joined_words(text):
    if not text:
        return text
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def trim(text, max_len=70):
    if not text:
        return text
    return text[:max_len]


def parse_lrc(lrc_string):
    """Converte uma string .lrc em lista (timestamp_segundos, texto) ordenada."""
    lyrics = []
    if not lrc_string:
        return lyrics

    for line in lrc_string.splitlines():
        match = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)", line)
        if match:
            m = int(match.group(1))
            s = float(match.group(2))
            text = match.group(3).strip()
            lyrics.append((m * 60 + s, text))

    return sorted(lyrics, key=lambda x: x[0])


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------
_SETTINGS_URL = "https://discord.com/api/v9/users/@me/settings"


def update_discord_status(text):
    """Atualiza (ou limpa) o status customizado da conta.

    Respeita rate-limit basico: se levar 429, espera o tempo pedido.
    """
    if PREVIEW:
        return

    headers = {
        "authorization": DISCORD_TOKEN,
        "content-type": "application/json",
    }

    data = (
        {"custom_status": {"text": text}} if text
        else {"custom_status": None}
    )

    try:
        resp = requests.patch(_SETTINGS_URL, headers=headers, json=data, timeout=5)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 1)
            time.sleep(float(retry_after) + 0.5)
        elif resp.status_code == 401:
            # token invalido — avisa uma vez e segue (loop trata)
            print("\n[erro] Token invalido (401). Verifique seu DISCORD_TOKEN.")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Windows media
# ---------------------------------------------------------------------------
async def get_media_info():
    try:
        sessions = await MediaManager.request_async()
        session = sessions.get_current_session()

        if session:
            playback = session.get_playback_info()
            props = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()

            now = datetime.now(timezone.utc)
            diff = (now - timeline.last_updated_time).total_seconds()

            return {
                "title": props.title,
                "artist": props.artist,
                "position": timeline.position.total_seconds() + diff,
                "status": playback.playback_status,
            }
    except Exception:
        pass

    return {"status": None}


def render(song, artist, pos, lyric):
    if not INTERACTIVE:
        return

    m, s = divmod(int(pos), 60)

    if PREVIEW:
        print("[ MODO PREVIEW - o status do Discord nao sera alterado ]\n")

    print(f"Song   : {song}")
    print(f"Artist : {artist}")
    print(f"Time   : {m:02d}:{s:02d}")
    print(f"Lyrics : {trim(lyric) if lyric else '...'}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def main_loop(min_interval):
    current_song = None
    current_lyrics = []
    current_line = None      # ultima linha mostrada no terminal

    desired_text = None      # status que queremos no Discord
    sent_text = None         # ultimo status realmente enviado
    last_sent = 0.0          # time.monotonic() do ultimo envio
    send_task = None         # envio em andamento (para nao sobrepor)

    update_discord_status(None)

    if INTERACTIVE:
        os.system("cls" if os.name == "nt" else "clear")
        hide_cursor()
        print("Detectando musica...")

    try:
        while True:
            info = await get_media_info()
            status = info.get("status")
            playing = status == PlaybackStatus.PLAYING

            if not playing:
                # pausado, parado ou nada tocando -> queremos limpar o status
                desired_text = None
                current_line = None
            else:
                song_id = f"{info['title']} {info['artist']}"

                if song_id != current_song:
                    current_song = song_id
                    current_line = None

                    lrc = await asyncio.to_thread(syncedlyrics.search, song_id)
                    current_lyrics = parse_lrc(lrc) if lrc else []

                pos = info["position"]

                active = None
                for t, txt in current_lyrics:
                    if t <= pos + 0.5:
                        active = txt
                    else:
                        break

                active = fix_joined_words(clean_lyric(active))

                # O terminal acompanha em tempo real (so o envio ao Discord
                # e que respeita o limitador de frequencia, mais abaixo).
                if active != current_line:
                    current_line = active
                    clear_line_area()
                    render(info["title"], info["artist"], pos, current_line)

                desired_text = f"\U0001f3b5 {current_line}" if current_line else None

            # ---- limitador de frequencia ----
            # Atualiza o Discord no maximo 1x a cada `min_interval` segundos,
            # sempre com o texto mais recente, sem sobrepor um envio no outro.
            now = time.monotonic()
            free = send_task is None or send_task.done()
            if desired_text != sent_text and free and (now - last_sent) >= min_interval:
                sent_text = desired_text
                last_sent = now
                send_task = asyncio.create_task(
                    asyncio.to_thread(update_discord_status, desired_text)
                )

            await asyncio.sleep(0.3 if playing else 1)

    finally:
        show_cursor()
        update_discord_status(None)


def main():
    global PREVIEW

    # Evita travar ao imprimir letras com emoji/acentos fora do cp1252 em
    # consoles do Windows (e mostra os caracteres certos no Windows Terminal).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Sincroniza a letra da musica que esta tocando com o status do Discord."
    )
    parser.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="Mostra a letra no terminal sem mexer no Discord (nao precisa de token).",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=5.0,
        help="Segundos minimos entre atualizacoes do status no Discord "
             "(padrao: 5). Maior = menos requisicoes e menos risco de deteccao.",
    )
    args = parser.parse_args()
    PREVIEW = args.preview
    min_interval = max(1.0, args.interval)  # piso de 1s por seguranca

    if not PREVIEW and not DISCORD_TOKEN:
        print(
            "Nenhum token encontrado.\n"
            "Defina a variavel de ambiente DISCORD_TOKEN ou crie um arquivo\n"
            "token.txt (na mesma pasta) com o seu token dentro.\n"
            "\n"
            "Dica: rode com --preview para testar sem token.\n"
        )
        sys.exit(1)

    try:
        asyncio.run(main_loop(min_interval))
    except KeyboardInterrupt:
        show_cursor()
        update_discord_status(None)
        sys.exit(0)


if __name__ == "__main__":
    main()

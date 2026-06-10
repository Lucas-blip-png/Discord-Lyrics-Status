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
def _app_dir():
    """Pasta do programa: ao lado do .exe quando empacotado (PyInstaller),
    senao ao lado do proprio lyrics.py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _token_file():
    return os.path.join(_app_dir(), "token.txt")


def load_token():
    """Le o token do ambiente (DISCORD_TOKEN) ou de um token.txt ao lado do app.

    NUNCA cole seu token direto no codigo: assim ele nao vaza se voce
    compartilhar/subir o arquivo pra algum lugar.
    """
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if token:
        return token

    path = _token_file()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""


def save_token(token):
    with open(_token_file(), "w", encoding="ascii", errors="ignore") as f:
        f.write(token.strip())


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
# Intervalo de atualizacao (limitador de frequencia)   <- EDITE AQUI SE QUISER
# ---------------------------------------------------------------------------
# Trava de seguranca: o status NUNCA e atualizado mais rapido que MIN_INTERVAL
# (evita rate-limit/ban) nem mais devagar que MAX_INTERVAL. Dentro dessa faixa
# voce escolhe o valor com --interval, com configurar_intervalo.bat, ou editando
# o arquivo interval.txt (ao lado do programa).
MIN_INTERVAL = 2.0        # mais rapido permitido, em segundos (menor = mais risco)
MAX_INTERVAL = 3600.0     # mais devagar permitido, em segundos
DEFAULT_INTERVAL = 5.0


def _interval_file():
    return os.path.join(_app_dir(), "interval.txt")


def clamp_interval(value):
    return max(MIN_INTERVAL, min(MAX_INTERVAL, value))


def load_interval():
    """Le o intervalo salvo (interval.txt), sempre dentro da faixa permitida."""
    path = _interval_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return clamp_interval(float(f.read().strip().replace(",", ".")))
        except Exception:
            pass
    return DEFAULT_INTERVAL


def save_interval(value):
    with open(_interval_file(), "w", encoding="ascii", errors="ignore") as f:
        f.write(f"{clamp_interval(value):g}")


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
        default=None,
        help=f"Segundos entre atualizacoes do status (entre {MIN_INTERVAL:g} e "
             f"{MAX_INTERVAL:g}; padrao {DEFAULT_INTERVAL:g}). Maior = mais seguro. "
             "Quando informado, fica salvo para as proximas execucoes.",
    )
    parser.add_argument(
        "--set-interval",
        type=float,
        default=None,
        metavar="SEGUNDOS",
        help="Apenas salva o intervalo (em segundos) e sai, sem iniciar.",
    )
    args = parser.parse_args()
    PREVIEW = args.preview

    # --set-interval: so grava o valor e sai (usado pelo configurar_intervalo.bat)
    if args.set_interval is not None:
        v = clamp_interval(args.set_interval)
        try:
            save_interval(v)
            print(f"Intervalo definido para {v:g}s "
                  f"(permitido: {MIN_INTERVAL:g}-{MAX_INTERVAL:g}s).")
        except Exception as e:
            print(f"Nao consegui salvar: {e}")
        return

    # intervalo desta execucao: --interval (e persiste) ou o valor salvo
    if args.interval is not None:
        min_interval = clamp_interval(args.interval)
        if min_interval != args.interval:
            print(f"Intervalo fora da faixa; ajustei para {min_interval:g}s "
                  f"(min {MIN_INTERVAL:g}s / max {MAX_INTERVAL:g}s).")
        try:
            save_interval(min_interval)
            print(f"Intervalo: {min_interval:g}s (salvo para as proximas vezes).")
        except Exception:
            pass
    else:
        min_interval = load_interval()

    global DISCORD_TOKEN

    # Primeira execucao sem token: se houver terminal, pede e salva.
    if not PREVIEW and not DISCORD_TOKEN:
        can_ask = INTERACTIVE and getattr(sys.stdin, "isatty", lambda: False)()
        if can_ask:
            print("Nenhum token salvo ainda.")
            print("Cole seu token do Discord e tecle Enter (ou deixe vazio p/ sair).")
            print("(O token fica salvo so neste PC, em token.txt. NUNCA compartilhe.)")
            try:
                entered = input("> ").strip()
            except EOFError:
                entered = ""
            if entered:
                try:
                    save_token(entered)
                    DISCORD_TOKEN = entered
                    print("Token salvo! Iniciando...\n")
                except Exception as e:
                    print(f"Nao consegui salvar o token: {e}")

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

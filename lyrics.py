import argparse
import asyncio
import os
import sys
import re
import threading
import time

import requests
import syncedlyrics
from datetime import datetime, timezone

import lang
from lang import t

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

# Controles usados pelo tray app (tray.py): pausar limpa o status sem sair;
# STOP_EVENT encerra o main_loop (que limpa o status no finally).
PAUSED = False
STOP_EVENT = threading.Event()

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


def _lang_file():
    return os.path.join(_app_dir(), "lang.txt")


def load_lang_pref():
    path = _lang_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def save_lang_pref(code):
    with open(_lang_file(), "w", encoding="ascii", errors="ignore") as f:
        f.write(code)


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
            print("\n" + t("token_invalid_401"))
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
        print(t("preview_banner") + "\n")

    print(f"{t('lbl_song')}: {song}")
    print(f"{t('lbl_artist')}: {artist}")
    print(f"{t('lbl_time')}: {m:02d}:{s:02d}")
    print(f"{t('lbl_lyrics')}: {trim(lyric) if lyric else '...'}")


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
        print(t("detecting_music"))

    try:
        while not STOP_EVENT.is_set():
            if PAUSED:
                if sent_text is not None:
                    update_discord_status(None)
                    sent_text = None
                current_line = None
                await asyncio.sleep(0.5)
                continue

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
                for ts, txt in current_lyrics:
                    if ts <= pos + 0.5:
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

                # Fallback: sem letra (ou entre linhas) mostra musica - artista.
                if current_line:
                    desired_text = f"\U0001f3b5 {current_line}"
                else:
                    desired_text = trim(
                        f"\U0001f3b5 {info['title']} - {info['artist']}", 100
                    )

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

    # Resolve o idioma cedo (antes do parser), para a ajuda ja sair traduzida:
    # preferencia salva (lang.txt) > variavel de ambiente > auto-deteccao.
    # Um --lang/--set-lang no argv tem prioridade.
    pref = load_lang_pref() or os.environ.get("DISCORD_LYRICS_LANG", "")
    if pref:
        lang.set_lang(pref)
    for i, a in enumerate(sys.argv):
        if a in ("-L", "--lang", "--set-lang") and i + 1 < len(sys.argv):
            lang.set_lang(sys.argv[i + 1])
        elif a.startswith("--lang=") or a.startswith("--set-lang="):
            lang.set_lang(a.split("=", 1)[1])

    parser = argparse.ArgumentParser(description=t("arg_desc"))
    parser.add_argument("-p", "--preview", action="store_true",
                        help=t("arg_preview_win"))
    parser.add_argument(
        "-i", "--interval", type=float, default=None,
        help=t("arg_interval", min=f"{MIN_INTERVAL:g}", max=f"{MAX_INTERVAL:g}",
               default=f"{DEFAULT_INTERVAL:g}"),
    )
    parser.add_argument("--set-interval", type=float, default=None,
                        metavar="SEGUNDOS", help=t("arg_set_interval"))
    parser.add_argument("-L", "--lang", default=None, metavar="CODIGO",
                        help=t("arg_lang"))
    parser.add_argument("--set-lang", default=None, metavar="CODIGO",
                        help=t("arg_set_lang"))
    args = parser.parse_args()
    PREVIEW = args.preview

    # --set-lang: salva o idioma e sai
    if args.set_lang is not None:
        lang.set_lang(args.set_lang)
        try:
            save_lang_pref(lang.get_lang())
        except Exception:
            pass
        print(t("lang_set", lang=lang.get_lang()))
        return

    # --lang: usa neste run e fica salvo
    if args.lang is not None:
        lang.set_lang(args.lang)
        try:
            save_lang_pref(lang.get_lang())
        except Exception:
            pass

    # --set-interval: so grava o valor e sai (usado pelo configurar_intervalo.bat)
    if args.set_interval is not None:
        v = clamp_interval(args.set_interval)
        try:
            save_interval(v)
            print(t("interval_saved_exit", v=f"{v:g}",
                    min=f"{MIN_INTERVAL:g}", max=f"{MAX_INTERVAL:g}"))
        except Exception as e:
            print(t("interval_save_failed", error=e))
        return

    # intervalo desta execucao: --interval (e persiste) ou o valor salvo
    if args.interval is not None:
        min_interval = clamp_interval(args.interval)
        if min_interval != args.interval:
            print(t("interval_out_of_range", v=f"{min_interval:g}",
                    min=f"{MIN_INTERVAL:g}", max=f"{MAX_INTERVAL:g}"))
        try:
            save_interval(min_interval)
            print(t("interval_set_running", v=f"{min_interval:g}"))
        except Exception:
            pass
    else:
        min_interval = load_interval()

    global DISCORD_TOKEN

    # Primeira execucao sem token: se houver terminal, pede e salva.
    if not PREVIEW and not DISCORD_TOKEN:
        can_ask = INTERACTIVE and getattr(sys.stdin, "isatty", lambda: False)()
        if can_ask:
            print(t("token_none_yet"))
            print(t("token_paste_prompt"))
            print(t("token_local_note"))
            try:
                entered = input("> ").strip()
            except EOFError:
                entered = ""
            if entered:
                try:
                    save_token(entered)
                    DISCORD_TOKEN = entered
                    print(t("token_saved_starting") + "\n")
                except Exception as e:
                    print(t("token_save_failed", error=e))

    if not PREVIEW and not DISCORD_TOKEN:
        print(t("token_not_found"))
        sys.exit(1)

    try:
        asyncio.run(main_loop(min_interval))
    except KeyboardInterrupt:
        show_cursor()
        update_discord_status(None)
        sys.exit(0)


if __name__ == "__main__":
    main()

"""
Discord Lyrics Status - app de bandeja (system tray) para Windows.

Coloca um icone perto do relogio com Pausar/Retomar e Sair, em vez de
processo escondido + parar.bat. Reaproveita o lyrics.py.

Precisa de: pip install pystray pillow   (o iniciar_tray.bat instala sozinho)
"""
import asyncio
import sys
import threading

from PIL import Image, ImageDraw
import pystray

import lang
from lang import t
import lyrics


def make_icon(paused=False):
    """Desenha um iconezinho de nota musical (cinza quando pausado)."""
    color = (114, 118, 125, 255) if paused else (88, 101, 242, 255)  # blurple
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((12, 38, 30, 56), fill=color)          # cabeca da nota
    d.rectangle((27, 14, 31, 48), fill=color)         # haste
    d.polygon([(31, 14), (31, 26), (46, 20), (46, 10)], fill=color)  # bandeira
    return img


def run_loop():
    try:
        asyncio.run(lyrics.main_loop(lyrics.load_interval()))
    except Exception:
        pass


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # idioma salvo / auto
    pref = lyrics.load_lang_pref()
    if pref:
        lang.set_lang(pref)

    # roda o loop de letras numa thread separada
    threading.Thread(target=run_loop, daemon=True).start()

    def title():
        base = t("tray_paused") if lyrics.PAUSED else t("tray_running")
        if not lyrics.DISCORD_TOKEN:
            return t("tray_no_token")
        return base

    def toggle(icon, item):
        lyrics.PAUSED = not lyrics.PAUSED
        icon.icon = make_icon(lyrics.PAUSED)
        icon.title = title()
        icon.update_menu()

    def quit_app(icon, item):
        lyrics.STOP_EVENT.set()
        try:
            lyrics.update_discord_status(None)
        except Exception:
            pass
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: t("tray_resume") if lyrics.PAUSED else t("tray_pause"),
            toggle,
        ),
        pystray.MenuItem(t("tray_quit"), quit_app),
    )

    icon = pystray.Icon("DiscordLyrics", make_icon(), title(), menu)
    icon.run()


if __name__ == "__main__":
    main()

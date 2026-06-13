"""
Discord Lyrics Status - versao via API do Spotify (multiplataforma).

Funciona em Windows, Linux, macOS e tambem no Android (via Termux), porque usa
SO requisicoes HTTP - nada de APIs do Windows.

Detecta a musica pela API do Spotify, busca a letra sincronizada e atualiza o
seu status do Discord, linha por linha. Configure antes com:  setup_spotify.py
"""
import argparse
import json
import os
import re
import sys
import time

import requests
import syncedlyrics

import lang
from lang import t

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_NOW_PLAYING = "https://api.spotify.com/v1/me/player/currently-playing"
DISCORD_SETTINGS = "https://discord.com/api/v9/users/@me/settings"

POLL_INTERVAL = 4.0   # segundos entre chamadas a API do Spotify
TICK = 0.4            # segundos entre verificacoes de linha (interpolado)

# Limitador de frequencia: faixa permitida para o intervalo entre updates do
# Discord. O valor escolhido fica salvo no config.json (campo "interval") ou
# pode ser passado em --interval. Sempre travado nessa faixa.
MIN_INTERVAL = 2.0        # mais rapido permitido, em segundos
MAX_INTERVAL = 3600.0     # mais devagar permitido, em segundos
DEFAULT_INTERVAL = 5.0


def clamp_interval(value):
    return max(MIN_INTERVAL, min(MAX_INTERVAL, value))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(t("config_not_found"))
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Letra (mesma logica da versao Windows)
# ---------------------------------------------------------------------------
def clean_lyric(text):
    if not text:
        return None
    text = text.replace("\r", "").strip()
    if "/" in text and len(text) > 40:
        return None
    if re.search(r"[a-z][A-Z][a-z]", text):
        return None
    if len(text) > 80:
        return None
    if len(re.sub(r"[a-zA-Z ]", "", text)) > len(text) * 0.4:
        return None
    return text


def fix_joined_words(text):
    if not text:
        return text
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def parse_lrc(lrc_string):
    lyrics = []
    if not lrc_string:
        return lyrics
    for line in lrc_string.splitlines():
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)", line)
        if m:
            lyrics.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return sorted(lyrics, key=lambda x: x[0])


_NOISE = re.compile(
    r"(official|videoclip|video|audio|lyric|lyrics|letra|legendado|legenda|"
    r"sub\s*espanol|tradu[cç][aã]o|m/?v|\bhd\b|\bhq\b|\b4k\b|\b8k\b|"
    r"visuali[sz]er|explicit|clean\s*version|remaster(ed)?|color\s*coded|"
    r"nightcore|slowed|reverb|sped\s*up|extended\s*mix|free\s*download|"
    r"download|prod\.?)",
    re.IGNORECASE,
)


def _strip_noise_brackets(text):
    for pat in (r"\([^()]*\)", r"\[[^\[\]]*\]", r"【[^】]*】"):
        text = re.sub(pat, lambda m: "" if _NOISE.search(m.group(0)) else m.group(0), text)
    return text


def clean_for_search(title, artist):
    """Limpa titulo/artista e devolve (titulo, artista, busca)."""
    title = _strip_noise_brackets(title or "")
    title = re.sub(r"\b(feat\.?|ft\.?|featuring)\b.*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\|.*$", "", title)
    title = re.sub(
        r"\s*\b(official|music|lyric|lyrics|video|audio|mv|visualizer|hd|hq|4k)\b"
        r"(\s+\b(official|music|lyric|lyrics|video|audio|mv|visualizer|hd|hq|4k)\b)*\s*$",
        "", title, flags=re.IGNORECASE,
    )
    artist = re.sub(r"\s*-\s*topic\s*$", "", artist or "", flags=re.IGNORECASE)
    artist = re.sub(r"\b(vevo|official)\b", "", artist, flags=re.IGNORECASE).strip()
    title = re.sub(r"\s+", " ", title).strip(" -–—\t'\"")
    if " - " in title:
        left, right = title.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if left and right:
            artist, title = left, right
    title = title.strip(" -–—'\"")
    artist = re.sub(r"\s+", " ", artist).strip(" -–—'\"")
    return title, artist, (title + " " + artist).strip()


# ---------------------------------------------------------------------------
# Spotify
# ---------------------------------------------------------------------------
class Spotify:
    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._access = None
        self._expires_at = 0.0

    def _refresh(self):
        resp = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            auth=(self.client_id, self.client_secret),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access = data["access_token"]
        # renova 60s antes de expirar (expires_in normalmente = 3600)
        self._expires_at = time.monotonic() + data.get("expires_in", 3600) - 60
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]

    def access_token(self):
        if not self._access or time.monotonic() >= self._expires_at:
            self._refresh()
        return self._access

    def now_playing(self):
        """(title, artist, progress_s, is_playing) ou None se nada estiver tocando."""
        try:
            resp = requests.get(
                SPOTIFY_NOW_PLAYING,
                headers={"Authorization": f"Bearer {self.access_token()}"},
                timeout=10,
            )
        except Exception:
            return None

        if resp.status_code == 401:
            self._access = None  # forca refresh na proxima
            return None
        if resp.status_code == 204 or not resp.content or resp.status_code != 200:
            return None

        data = resp.json()
        item = data.get("item")
        if not item:
            return None
        title = item.get("name", "")
        artist = ", ".join(a.get("name", "") for a in item.get("artists", []))
        progress = data.get("progress_ms", 0) / 1000.0
        return title, artist, progress, bool(data.get("is_playing"))


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------
def update_discord_status(discord_token, text):
    data = {"custom_status": {"text": text}} if text else {"custom_status": None}
    try:
        resp = requests.patch(
            DISCORD_SETTINGS,
            headers={"authorization": discord_token, "content-type": "application/json"},
            json=data,
            timeout=10,
        )
        if resp.status_code == 429:
            time.sleep(float(resp.json().get("retry_after", 1)) + 0.5)
        elif resp.status_code == 401:
            print("\n" + t("discord_401"))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def main():
    # idioma cedo (para a ajuda): --lang no argv tem prioridade
    for i, a in enumerate(sys.argv):
        if a in ("-L", "--lang") and i + 1 < len(sys.argv):
            lang.set_lang(sys.argv[i + 1])
        elif a.startswith("--lang="):
            lang.set_lang(a.split("=", 1)[1])

    parser = argparse.ArgumentParser(description=t("sp_arg_desc"))
    parser.add_argument("-p", "--preview", action="store_true", help=t("arg_preview"))
    parser.add_argument("-i", "--interval", type=float, default=None,
                        help=t("sp_arg_interval", min=f"{MIN_INTERVAL:g}",
                               max=f"{MAX_INTERVAL:g}", default=f"{DEFAULT_INTERVAL:g}"))
    parser.add_argument("-L", "--lang", default=None, metavar="CODE", help=t("arg_lang"))
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    cfg = load_config()

    # idioma final: --lang > config.json "lang" > auto-deteccao
    if args.lang:
        lang.set_lang(args.lang)
    elif cfg.get("lang"):
        lang.set_lang(cfg.get("lang"))

    sp = Spotify(cfg["spotify_client_id"], cfg["spotify_client_secret"],
                 cfg["spotify_refresh_token"])

    # intervalo: --interval (se passado) ou o salvo no config.json, sempre travado
    if args.interval is not None:
        min_interval = clamp_interval(args.interval)
    else:
        try:
            min_interval = clamp_interval(float(cfg.get("interval", DEFAULT_INTERVAL)))
        except Exception:
            min_interval = DEFAULT_INTERVAL
    discord_token = cfg.get("discord_token", "")
    if not args.preview and not discord_token:
        print(t("discord_token_missing_cfg"))
        sys.exit(1)

    current_song = None
    lyrics = []
    current_line = None
    disp_title = ""
    disp_artist = ""
    sent_text = None
    last_sent = 0.0

    last_poll = 0.0
    base_progress = 0.0   # progresso (s) no ultimo poll
    base_time = 0.0       # monotonic no ultimo poll
    playing = False
    title = artist = ""

    interactive = bool(sys.stdout) and sys.stdout.isatty()
    print(t("detecting_spotify"))
    if not args.preview:
        update_discord_status(discord_token, None)

    try:
        while True:
            now = time.monotonic()

            # poll periodico a API do Spotify
            if now - last_poll >= POLL_INTERVAL:
                last_poll = now
                info = sp.now_playing()
                if info is None:
                    playing = False
                else:
                    title, artist, base_progress, playing = info
                    base_time = now

            # posicao estimada entre polls (interpola com o relogio local)
            pos = base_progress + (now - base_time) if playing else 0.0

            if not playing:
                desired = None
                current_song = None
                current_line = None
            else:
                song_id = f"{title} {artist}"
                if song_id != current_song:
                    current_song = song_id
                    current_line = None
                    disp_title, disp_artist, query = clean_for_search(title, artist)
                    lrc = syncedlyrics.search(query)
                    lyrics = parse_lrc(lrc) if lrc else []

                active = None
                for ts, txt in lyrics:
                    if ts <= pos + 0.5:
                        active = txt
                    else:
                        break
                active = fix_joined_words(clean_lyric(active))

                if active != current_line:
                    current_line = active
                    if interactive:
                        m, s = divmod(int(pos), 60)
                        print(f"\n{title} - {artist}  [{m:02d}:{s:02d}]")
                        print(f"  > {current_line or '...'}")
                # Fallback: sem letra (ou entre linhas) mostra musica - artista.
                if current_line:
                    desired = f"\U0001f3b5 {current_line}"
                elif disp_artist:
                    desired = (f"\U0001f3b5 {disp_title} - {disp_artist}")[:100]
                else:
                    desired = (f"\U0001f3b5 {disp_title or title}")[:100]

            # limitador de frequencia (envia no maximo 1x a cada min_interval)
            if not args.preview and desired != sent_text and (now - last_sent) >= min_interval:
                sent_text = desired
                last_sent = now
                update_discord_status(discord_token, desired)

            time.sleep(TICK)
    except KeyboardInterrupt:
        if not args.preview:
            update_discord_status(discord_token, None)
        print("\n" + t("exiting"))


if __name__ == "__main__":
    main()

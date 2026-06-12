"""
Configuracao da versao Spotify. Cria o config.json com:
- Spotify Client ID + Secret (do dashboard de desenvolvedor do Spotify)
- refresh_token do Spotify (via login OAuth)
- token do Discord

Rode uma vez:  python setup_spotify.py
"""
import json
import os
import sys
import urllib.parse

import requests

import lang
from lang import t

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-currently-playing"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

MIN_INTERVAL = 2.0
MAX_INTERVAL = 3600.0
DEFAULT_INTERVAL = 5.0


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Pergunta o idioma primeiro, para o resto do assistente sair traduzido.
    chosen_lang = ask(t("setup_lang_prompt"))
    if chosen_lang:
        lang.set_lang(chosen_lang)

    print("=" * 62)
    print(" " + t("setup_title"))
    print("=" * 62)
    print()
    print(t("setup_step1"))
    print(t("setup_step1_a"))
    print(t("setup_step1_b"))
    print(f"        {REDIRECT_URI}")
    print(t("setup_step1_c"))
    print()
    client_id = ask(t("prompt_client_id"))
    client_secret = ask(t("prompt_client_secret"))
    if not client_id or not client_secret:
        print(t("client_required"))
        sys.exit(1)

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    })
    print()
    print(t("setup_step2"))
    print()
    print("   " + url)
    print()
    print(t("setup_step2_a"))
    print(f"        {REDIRECT_URI}?code=XXXXXXXX")
    print(t("setup_step2_b"))
    print(t("setup_step2_c"))
    print()
    redirected = ask(t("setup_step3"))
    code = redirected
    if "code=" in redirected:
        q = urllib.parse.urlparse(redirected).query
        code = urllib.parse.parse_qs(q).get("code", [redirected])[0]
    if not code:
        print(t("code_not_found"))
        sys.exit(1)

    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        auth=(client_id, client_secret),
        timeout=15,
    )
    if resp.status_code != 200:
        print(t("token_exchange_failed"), resp.status_code)
        print(resp.text)
        sys.exit(1)
    refresh_token = resp.json().get("refresh_token")
    if not refresh_token:
        print(t("no_refresh_token"), resp.json())
        sys.exit(1)
    print(t("spotify_connected"))
    print()

    print(t("setup_step4"))
    print(t("setup_step4_a"))
    discord_token = ask(t("prompt_discord_token"))
    if not discord_token:
        print(t("discord_required"))
        sys.exit(1)

    print()
    print(t("setup_step5", min=f"{MIN_INTERVAL:g}", max=f"{MAX_INTERVAL:g}"))
    print(t("setup_step5_a", default=f"{DEFAULT_INTERVAL:g}"))
    raw = ask(t("prompt_interval"))
    interval = DEFAULT_INTERVAL
    if raw:
        try:
            interval = max(MIN_INTERVAL, min(MAX_INTERVAL, float(raw.replace(",", "."))))
        except ValueError:
            print(t("invalid_using_default", default=f"{DEFAULT_INTERVAL:g}"))
    print(t("interval_arrow", v=f"{interval:g}"))

    cfg = {
        "spotify_client_id": client_id,
        "spotify_client_secret": client_secret,
        "spotify_refresh_token": refresh_token,
        "discord_token": discord_token,
        "interval": interval,
        "lang": lang.get_lang(),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print()
    print(t("saved_to", path=CONFIG_PATH))
    print(t("secrets_warning"))
    print()
    print(t("now_run"))


if __name__ == "__main__":
    main()

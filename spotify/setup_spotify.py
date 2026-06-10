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

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-currently-playing"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def main():
    print("=" * 62)
    print(" Configuracao - Discord Lyrics Status (versao Spotify)")
    print("=" * 62)
    print()
    print("PASSO 1) Crie um app em: https://developer.spotify.com/dashboard")
    print("   - Clique em 'Create app'.")
    print("   - Em 'Redirect URIs' adicione EXATAMENTE este endereco:")
    print(f"        {REDIRECT_URI}")
    print("   - Salve e copie o 'Client ID' e o 'Client Secret'.")
    print()
    client_id = ask("Client ID: ")
    client_secret = ask("Client Secret: ")
    if not client_id or not client_secret:
        print("Client ID/Secret sao obrigatorios.")
        sys.exit(1)

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    })
    print()
    print("PASSO 2) Abra este link no navegador, faca login e clique em 'Agree':")
    print()
    print("   " + url)
    print()
    print("   Voce sera redirecionado para algo como:")
    print(f"        {REDIRECT_URI}?code=XXXXXXXX")
    print("   A pagina pode mostrar 'nao foi possivel acessar' - tudo bem!")
    print("   O que importa e a URL inteira que ficou na barra de endereco.")
    print()
    redirected = ask("PASSO 3) Cole aqui a URL completa pra onde voce foi redirecionado: ")
    code = redirected
    if "code=" in redirected:
        q = urllib.parse.urlparse(redirected).query
        code = urllib.parse.parse_qs(q).get("code", [redirected])[0]
    if not code:
        print("Nao consegui encontrar o 'code' na URL.")
        sys.exit(1)

    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        auth=(client_id, client_secret),
        timeout=15,
    )
    if resp.status_code != 200:
        print("Falha ao trocar o code por token:", resp.status_code)
        print(resp.text)
        sys.exit(1)
    refresh_token = resp.json().get("refresh_token")
    if not refresh_token:
        print("O Spotify nao retornou um refresh_token:", resp.json())
        sys.exit(1)
    print("Spotify conectado com sucesso!")
    print()

    print("PASSO 4) Cole o seu token do Discord.")
    print("   (Como pegar: veja o README. NUNCA compartilhe esse token.)")
    discord_token = ask("Token do Discord: ")
    if not discord_token:
        print("O token do Discord e obrigatorio.")
        sys.exit(1)

    cfg = {
        "spotify_client_id": client_id,
        "spotify_client_secret": client_secret,
        "spotify_refresh_token": refresh_token,
        "discord_token": discord_token,
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print()
    print(f"Tudo salvo em: {CONFIG_PATH}")
    print("Esse arquivo guarda seus segredos - NAO compartilhe e NAO suba pro git.")
    print()
    print("Agora e so rodar:  python lyrics_spotify.py")


if __name__ == "__main__":
    main()

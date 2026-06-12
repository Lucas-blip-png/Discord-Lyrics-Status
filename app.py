"""
Discord Lyrics Status - tudo em um (menu).

Ao abrir SEM argumentos, mostra um menu para configurar tudo (token, intervalo,
idioma, inicio automatico) e iniciar - sem precisar de Python nem dos .bat.
E este o arquivo empacotado no .exe.

Modos:
  (sem args)     menu interativo
  --run-hidden   roda a sincronizacao escondida (usado pelo inicio automatico)
  --preview      roda em modo preview (sem mexer no Discord)
"""
import asyncio
import os
import sys

import lyrics
import lang
from lang import t


# ---------------------------------------------------------------------------
# Inicio automatico (cria/remove um atalho .vbs na pasta de Inicializacao)
# ---------------------------------------------------------------------------
def _startup_dir():
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                        "Start Menu", "Programs", "Startup")


def _vbs_path():
    return os.path.join(_startup_dir(), "DiscordLyricsStatus.vbs")


def _hidden_target():
    """(programa, argumentos) para rodar escondido no boot."""
    if getattr(sys, "frozen", False):
        return sys.executable, "--run-hidden"
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    # aspas DOBRADAS porque isto vai dentro de uma string do VBScript
    return pyw, '""' + os.path.abspath(__file__) + '"" --run-hidden'


def autostart_enabled():
    return os.path.exists(_vbs_path())


def enable_autostart():
    target, extra = _hidden_target()
    content = (
        "' Discord Lyrics Status - inicio automatico (escondido)\r\n"
        'Set sh = CreateObject("WScript.Shell")\r\n'
        'sh.Run """' + target + '"" ' + extra + '", 0, False\r\n'
    )
    with open(_vbs_path(), "w", encoding="ascii", errors="ignore") as f:
        f.write(content)


def disable_autostart():
    p = _vbs_path()
    if os.path.exists(p):
        os.remove(p)


# ---------------------------------------------------------------------------
# Sincronizacao
# ---------------------------------------------------------------------------
def run_sync(preview=False):
    lyrics.PREVIEW = preview
    lyrics.STOP_EVENT.clear()
    try:
        asyncio.run(lyrics.main_loop(lyrics.load_interval()))
    except KeyboardInterrupt:
        lyrics.update_discord_status(None)


# ---------------------------------------------------------------------------
# Acoes do menu
# ---------------------------------------------------------------------------
def action_token():
    print(t("token_paste_prompt"))
    print(t("token_local_note"))
    tok = input("> ").strip()
    if tok:
        lyrics.save_token(tok)
        lyrics.DISCORD_TOKEN = tok
        print(t("token_saved_starting"))


def action_interval():
    print(t("setup_step5", min=f"{lyrics.MIN_INTERVAL:g}", max=f"{lyrics.MAX_INTERVAL:g}"))
    raw = input(t("prompt_interval")).strip().replace(",", ".")
    try:
        v = lyrics.clamp_interval(float(raw))
    except ValueError:
        return
    lyrics.save_interval(v)
    print(t("interval_saved_exit", v=f"{v:g}",
            min=f"{lyrics.MIN_INTERVAL:g}", max=f"{lyrics.MAX_INTERVAL:g}"))


def action_lang():
    print("  " + " ".join(lang.available()))
    code = input(t("setup_lang_prompt")).strip()
    if code:
        lang.set_lang(code)
        lyrics.save_lang_pref(lang.get_lang())
        print(t("lang_set", lang=lang.get_lang()))


def action_autostart():
    if autostart_enabled():
        disable_autostart()
        print(t("menu_autostart_done_off"))
    else:
        enable_autostart()
        print(t("menu_autostart_done_on"))


def menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 50)
        print("  Discord Lyrics Status")
        print("=" * 50)
        tok = t("menu_token_ok") if lyrics.DISCORD_TOKEN else t("menu_token_missing")
        astate = t("menu_autostart_on") if autostart_enabled() else t("menu_autostart_off")
        print("  " + tok + "   |   " + astate)
        print()
        print("  1) " + t("menu_opt_token"))
        print("  2) " + t("menu_opt_interval"))
        print("  3) " + t("menu_opt_lang"))
        print("  4) " + t("menu_opt_autostart"))
        print("  5) " + t("menu_opt_start"))
        print("  6) " + t("menu_opt_test"))
        print("  0) " + t("menu_opt_exit"))
        print()
        choice = input(t("menu_choose")).strip()

        if choice == "1":
            action_token()
        elif choice == "2":
            action_interval()
        elif choice == "3":
            action_lang()
        elif choice == "4":
            action_autostart()
        elif choice == "5":
            if not lyrics.DISCORD_TOKEN:
                print(t("menu_need_token"))
            else:
                print(t("menu_start_hint"))
                run_sync(preview=False)
        elif choice == "6":
            print(t("menu_start_hint"))
            run_sync(preview=True)
        elif choice == "0":
            break
        else:
            continue

        try:
            input("\n" + t("menu_back"))
        except EOFError:
            break


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    pref = lyrics.load_lang_pref() or os.environ.get("DISCORD_LYRICS_LANG", "")
    if pref:
        lang.set_lang(pref)

    args = sys.argv[1:]
    if "--run-hidden" in args:
        run_sync(preview=False)
    elif "--preview" in args:
        run_sync(preview=True)
    else:
        menu()


if __name__ == "__main__":
    main()

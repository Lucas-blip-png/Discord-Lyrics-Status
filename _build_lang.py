"""Gera lang.py (catalogo i18n + logica) a partir de _i18n/base.json (en, pt)
e de _i18n/<codigo>.json (demais idiomas). Tambem copia para spotify/lang.py."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
I18N = os.path.join(HERE, "_i18n")

base = json.load(open(os.path.join(I18N, "base.json"), encoding="utf-8"))
langs = {code: dict(d) for code, d in base.items()}  # en, pt

for fn in os.listdir(I18N):
    if fn.endswith(".json") and fn != "base.json":
        code = fn[:-5]
        langs[code] = json.load(open(os.path.join(I18N, fn), encoding="utf-8"))

KEYS = list(base["en"].keys())
order = ["en", "pt"] + sorted(c for c in langs if c not in ("en", "pt"))


def s(x):
    return json.dumps(x, ensure_ascii=False)


LOGIC = '''

_LANG = "en"


def detect_lang():
    """Descobre o idioma do sistema (Windows/Unix). Cai para 'en' se nao houver."""
    code = ""
    try:
        if os.name == "nt":
            import ctypes
            import locale
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            code = locale.windows_locale.get(lcid, "")
    except Exception:
        code = ""
    if not code:
        for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
            code = os.environ.get(var, "")
            if code:
                break
    code = (code or "en").lower().replace("-", "_")
    base = code.split("_")[0].split(".")[0].split(":")[0]
    return base if base in STRINGS else "en"


def set_lang(lang):
    """Define o idioma se suportado; retorna o idioma em uso."""
    global _LANG
    if lang:
        base = str(lang).lower().replace("-", "_").split("_")[0]
        if base in STRINGS:
            _LANG = base
    return _LANG


def get_lang():
    return _LANG


def available():
    return list(STRINGS.keys())


def t(key, **kw):
    """Texto traduzido para a chave; cai para ingles, depois para a propria chave."""
    text = STRINGS.get(_LANG, {}).get(key) or STRINGS["en"].get(key) or key
    if kw:
        try:
            return text.format(**kw)
        except Exception:
            return text
    return text


_LANG = detect_lang()
'''

out = []
out.append('"""Catalogo de textos da interface em varios idiomas (i18n).')
out.append("GERADO AUTOMATICAMENTE por _build_lang.py - nao edite a mao;")
out.append('edite _i18n/*.json e rode: python _build_lang.py"""')
out.append("import os")
out.append("")
out.append("SUPPORTED = " + s(order))
out.append("")
out.append("STRINGS = {")
for code in order:
    out.append("    " + s(code) + ": {")
    for key in KEYS:
        val = langs.get(code, {}).get(key) or base["en"][key]
        out.append("        " + s(key) + ": " + s(val) + ",")
    out.append("    },")
out.append("}")
out.append(LOGIC.rstrip())
out.append("")

content = "\n".join(out)
for path in (os.path.join(HERE, "lang.py"), os.path.join(HERE, "spotify", "lang.py")):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("escrito:", path, f"({len(order)} idiomas, {len(KEYS)} chaves)")

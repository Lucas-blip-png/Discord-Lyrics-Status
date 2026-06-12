"""Valida as traducoes em _i18n/<lang>.json contra a fonte _i18n/base.json (en):
chaves completas e placeholders {..} identicos."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
I18N = os.path.join(HERE, "_i18n")
en = json.load(open(os.path.join(I18N, "base.json"), encoding="utf-8"))["en"]


def ph(s):
    return sorted(re.findall(r"{[a-zA-Z_]+}", s))


codes = sorted(f[:-5] for f in os.listdir(I18N)
               if f.endswith(".json") and f != "base.json")
problems = 0
for code in codes:
    try:
        d = json.load(open(os.path.join(I18N, code + ".json"), encoding="utf-8"))
    except Exception as e:
        print(f"[{code}] JSON INVALIDO: {e}")
        problems += 1
        continue
    missing = [k for k in en if k not in d]
    extra = [k for k in d if k not in en]
    if missing:
        print(f"[{code}] faltando {len(missing)} chave(s): {missing[:6]}")
        problems += 1
    if extra:
        print(f"[{code}] chave(s) extra(s): {extra[:6]}")
        problems += 1
    for k in en:
        if k in d and ph(en[k]) != ph(d[k]):
            print(f"[{code}] placeholders diferentes em '{k}': "
                  f"en={ph(en[k])} vs {code}={ph(d[k])}")
            problems += 1

print(f"\nidiomas verificados: {codes}")
print("OK - todas as traducoes validas" if problems == 0 else f"{problems} problema(s) encontrados")

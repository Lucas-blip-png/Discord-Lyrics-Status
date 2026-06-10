# 🎵 Discord Lyrics Status — versão Spotify (multiplataforma)

Esta versão pega a música pela **API do Spotify** (em vez das APIs do Windows),
então é **Python puro** e roda em **Windows, Linux, macOS e Android (via Termux)**.

> **Diferenças da versão principal:**
> - ✅ Funciona no **celular** (Android/Termux).
> - ⚠️ Só detecta o que toca no **Spotify** (não pega YouTube, navegador, etc.).
> - ⚙️ Precisa de uma configuração inicial (criar um "app" grátis no Spotify).

Continua sendo um **selfbot** (usa seu token do Discord) → mesmo risco de
**banimento**. Use por sua conta e risco. O token é como a senha da conta —
**nunca compartilhe**, e **nunca suba o `config.json`** pra lugar nenhum.

---

## 🖥️ No PC (Windows / Linux / Mac)

```bash
pip install -r requirements.txt
python setup_spotify.py     # configuracao (uma vez so)
python lyrics_spotify.py    # rodar
```

Para testar sem mexer no Discord: `python lyrics_spotify.py --preview`
Para atualizar mais devagar (mais seguro): `python lyrics_spotify.py --interval 8`

---

## 📱 No Android (Termux)

1. Instale o **Termux** pelo **[F-Droid](https://f-droid.org/packages/com.termux/)**
   (a versão da Play Store é antiga/quebrada).
2. Abra o Termux e rode:
   ```bash
   pkg update -y && pkg install -y python
   pip install requests syncedlyrics
   ```
3. Copie os arquivos `setup_spotify.py` e `lyrics_spotify.py` para o celular
   (ex.: pasta Download). Para acessá-los no Termux:
   ```bash
   termux-setup-storage          # autorize o acesso ao armazenamento
   cd ~/storage/downloads        # ou a pasta onde voce colocou os arquivos
   ```
4. Configure e rode:
   ```bash
   python setup_spotify.py       # cole o link no navegador do proprio celular
   python lyrics_spotify.py
   ```
5. Para ele não ser morto pela economia de bateria:
   ```bash
   termux-wake-lock
   ```
   E desative a otimização de bateria do Termux nas configurações do Android.

> 💡 A API do Spotify reporta o que está tocando **em qualquer aparelho** da sua
> conta. Então funciona mesmo se o Spotify estiver tocando no PC e o script
> rodando no celular.

---

## 🔧 Configuração (o que o `setup_spotify.py` faz)

1. **Cria um app no Spotify** (grátis): https://developer.spotify.com/dashboard
   → *Create app* → em **Redirect URIs** coloque **exatamente**:
   ```
   http://127.0.0.1:8888/callback
   ```
   Copie o **Client ID** e o **Client Secret**.
2. O script te dá um **link** → você abre, faz login, clica em *Agree*.
3. Você será redirecionado para `http://127.0.0.1:8888/callback?code=...`
   (a página pode dar erro de conexão — **tudo bem**, copie a URL da barra de
   endereço e cole de volta no script).
4. Por fim, cole o **token do Discord**.

Tudo é salvo em `config.json` (que fica **só no seu aparelho**).

### Como pegar o token do Discord

Pelo **navegador** (computador): entre em `discord.com/app`, aperte **F12** →
aba **Network** → filtre por **Fetch/XHR** → clique numa requisição
`discord.com/api/...` → em **Request Headers**, copie o valor de `authorization`.
**Nunca** cole código no Console que mandarem — é golpe de roubo de token.

---

## ❓ Problemas comuns

- **Não detecta música:** confira se está tocando **no Spotify** (não em outro
  app) e se você autorizou o escopo `user-read-currently-playing` no passo 2.
- **`invalid_grant` / erro de token:** o `code` só vale uma vez — refaça o
  `setup_spotify.py` gerando um link novo.
- **Redirect URI mismatch:** o endereço no dashboard do Spotify tem que ser
  idêntico a `http://127.0.0.1:8888/callback`.
- **401 do Discord:** token inválido/expirado — rode o setup de novo.

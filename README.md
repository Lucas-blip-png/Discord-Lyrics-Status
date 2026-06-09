# Discord Lyrics Status

Pega a música que está tocando no Windows (Spotify, etc.) e atualiza o seu
**status customizado do Discord** com a letra sincronizada, linha por linha,
em tempo real. Quando você pausa ou fecha o player, o status é limpo sozinho.

> Versão recriada e limpa do conceito original, com o token fora do código.

---

## ⚠️ Aviso importante — leia antes de usar

Isto é um **selfbot**: ele usa o seu *user token* para automatizar a sua conta.
**Isso viola os Termos de Serviço do Discord** e pode resultar em
**banimento da conta**. Não há roubo de dados aqui — o token só é enviado para a
API oficial do Discord — mas o risco para a sua conta é real.

- Use **por sua conta e risco**.
- De preferência, use numa **conta secundária**.
- **Nunca compartilhe seu token** com ninguém.

---

## Requisitos

- **Windows 10 ou 11** (usa as APIs de mídia do Windows; não funciona em Mac/Linux)
- **Python 3.8+**
- Um **user token** do Discord

## Instalação

```bash
pip install -r requirements.txt
```

## Configurando o token (sem deixar no código)

Escolha **uma** das opções:

**Opção A — variável de ambiente (recomendado)**

```powershell
# PowerShell (sessão atual)
$env:DISCORD_TOKEN = "seu_token_aqui"
python lyrics.py
```

**Opção B — arquivo `token.txt`**

Crie um arquivo chamado `token.txt` na mesma pasta do `lyrics.py` e cole o
token dentro. Ele já está no `.gitignore`, então não vai vazar pro git.

## Uso

```bash
python lyrics.py
```

Toque uma música. O terminal mostra um painelzinho com a música atual e a
letra; o status do Discord acompanha. `Ctrl+C` para sair (limpa o status).

### Modo preview (sem token, sem mexer no Discord)

Quer só ver a letra sincronizando no terminal, sem tocar na sua conta? Use
`--preview`. Nesse modo **nenhuma** requisição é feita ao Discord e o token
**não** é necessário — ótimo pra testar com segurança:

```bash
python lyrics.py --preview
```

## Como funciona

1. Lê a sessão de mídia ativa do Windows (`winrt`/`winsdk`) para saber o que
   está tocando e a posição atual.
2. Busca a letra sincronizada (`.lrc`) via [`syncedlyrics`](https://pypi.org/project/syncedlyrics/).
3. Faz `PATCH` em `users/@me/settings` para definir o `custom_status`.
4. Quando a linha da letra muda, atualiza o status.

## Notas

- Atualizar o status com muita frequência pode bater no rate-limit do Discord;
  o script já espera quando recebe `429`.
- Se aparecer `401`, seu token está inválido/expirado.

---
name: rodar-e-verificar
description: Como subir o Panóptico localmente no Windows (Postgres, API FastAPI e site Next.js), conferir de ponta a ponta e tirar screenshots em tamanho de celular, com os contornos para os problemas desta máquina (uvicorn órfão segurando a porta, build com o servidor rodando, conversão de caminho do Git Bash). Use sempre que precisar rodar, testar manualmente, ver uma tela, reiniciar servidores, depurar "a página não mostra dados" ou confirmar que uma mudança funciona no app de verdade, não só nos testes.
---

# Rodar e verificar localmente

## Ambiente desta máquina

- Windows 11; shells Bash (Git Bash) e PowerShell.
- `uv` instalado via pip: chame **`python -m uv ...`** (o executável `uv` não está no PATH).
- PostgreSQL 18 nativo (serviço `postgresql-x64-18`); `psql` em `/c/Program Files/PostgreSQL/18/bin/psql.exe`. Bancos `panoptico` e `panoptico_test`, usuário/senha `panoptico` (só local). Não use a senha do superusuário `postgres`.
- Sem Docker.
- `backend/.env` aponta para o banco local; `frontend/.env.local` tem `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## Subir

API (sem `--reload`: no Windows o reloader deixa um processo filho órfão segurando a porta 8000 e servindo código velho):

```bash
cd backend && python -m uv run uvicorn app.main:app --port 8000      # em background
```

Site (build de produção; é o que mais se parece com a Vercel):

```bash
cd frontend && npm run build && npm run start -- -p 3000             # start em background
```

**Antes de `npm run build`, pare o `next start`** — o build sobrescreve `.next` com o servidor rodando e ele passa a servir lixo. Se um build de teste usou `NEXT_OUTPUT=standalone`, refaça o build normal.

## Parar / destravar portas (PowerShell)

```powershell
foreach ($p in 8000,3000) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*spawn_main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Sintoma de órfão: "error while attempting to bind on address ... 10048", ou uma rota nova respondendo 404 depois de reiniciar.

## Conferir de ponta a ponta

Espere a API e o site responderem (laço com `curl` até 200, não `sleep` fixo) e então:

```bash
curl -s localhost:8000/saude                                   # {"status":"ok","banco":"ok"}
curl -s "localhost:8000/representantes?cep=01310-100"          # SP: 70 deputados, 3 senadores
curl -s "localhost:8000/representantes?cep=77001-002"          # Palmas/TO: 8 deputados, bom para tela curta
curl -s localhost:8000/parlamentares/518/presenca              # um senador com ausências justificadas
curl -s localhost:8000/municipios/1721000/emendas              # Palmas
```

No HTML do site, os textos aparecem intercalados com `<!-- -->`; procure por pedaços (`grep -o "Você está em"`). Páginas com `Suspense` respondem 200 mesmo quando o conteúdo é "não encontrado" (limitação conhecida do streaming).

Para ver o que robôs (WhatsApp) recebem: `curl -A "WhatsApp/2.23" localhost:3000/parlamentar/518 | grep og:`.

## Screenshot em tamanho de celular

```bash
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
"$EDGE" --headless=new --disable-gpu --hide-scrollbars --window-size=520,2600 \
  --virtual-time-budget=10000 --screenshot="<scratchpad>/tela.png" "http://localhost:3000/parlamentar/518"
```

Depois leia o PNG com a ferramenta Read. Use largura **≥ 500**: com 390 o Edge headless mantém a viewport mais larga e corta a imagem à direita, o que parece um bug de layout mas não é. A imagem Open Graph sai em `/parlamentar/<id>/opengraph-image`.

## Testes automáticos

```bash
cd backend && python -m uv run pytest -q && python -m uv run ruff check . && python -m uv run ruff format --check .
cd frontend && npx tsc --noEmit && npm run lint
```

## Armadilhas do Git Bash

- Caminhos que começam com `/` em argumentos viram caminhos do Windows (`/v11/projects` → `C:/Program Files/Git/v11/projects`). Prefixe o comando com `MSYS_NO_PATHCONV=1`.
- Comandos de shell muito longos com heredocs aninhados às vezes quebram com "unexpected EOF". Prefira criar arquivos com a ferramenta Write e rodar comandos curtos.
- O console mostra acentos como `�`; é só exibição, os dados estão certos.

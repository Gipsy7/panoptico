---
name: operar-producao
description: Como operar o Panóptico em produção — Vercel (site e API), Neon (Postgres) e GitHub Actions (ingestão diária e CI) — pela linha de comando, sem manipular segredos. Use sempre que a tarefa envolver deploy, redeploy, variáveis de ambiente da Vercel, domínios e DNS (Registro.br), disparar ou acompanhar a ingestão no GitHub Actions, investigar o site ou a API fora do ar ou com dados desatualizados, ou checar o CI, mesmo que o pedido seja só "o site não está funcionando" ou "atualiza os dados".
---

# Operar produção

## Mapa

| Parte | Onde | Endereço |
|---|---|---|
| Site | Vercel, projeto `panoptico` (root `frontend`) | https://panoptico.social.br · https://panoptico.vercel.app |
| API | Vercel, projeto `panoptico-api` (root `backend`, FastAPI em `app/main.py`) | https://api.panoptico.social.br · https://panoptico-api.vercel.app |
| Banco | Neon (plano Launch, pago por uso; ver travas de custo no README) | — |
| Ingestão diária | `.github/workflows/ingestao.yml`, 6h de Brasília | Actions do repo `Gipsy7/panoptico` |
| CI | `.github/workflows/ci.yml` (pytest com Postgres, ruff, lint e build) | a cada push |
| Cloudflare | DNS da zona (plano Free, CNAME com proxy), cache e firewall da API; nameservers `olga`/`steven.ns.cloudflare.com` no Registro.br | painel Cloudflare |
| Netlify | Reserva do site (site `panoptico`, `frontend/netlify.toml`), deploy só pelo `reserva-netlify.yml` | https://panoptico.netlify.app |
| Oracle | VM `panoptico-reserva-micro` (IP 163.176.196.22), reserva da API em docker compose + túnel (`deploy/reserva`) | `api-reserva.panoptico.social.br` |
| Worker `panoptico-troca` | `infra/cloudflare/troca`: troca o CNAME do site e da api entre principal e reserva | https://panoptico-troca.mikael-dev.workers.dev |

Conta Vercel: `gipsy7` (time `gipsy7s-projects`, plano Hobby). Repositório público. Guia humano completo: `docs/DEPLOY_GRATUITO.md`.

## Publicar código: sempre pelo branch `dev`

Nunca faça push direto no `main`. Envie para o `dev` (`git push origin dev`; se estiver no `main` local, `git push origin main:dev` ou mude de branch antes de commitar). O workflow **Publicar** roda os testes, aplica as migrações e recarrega os dados federais (~20 min) só se uma migração declarar `RECARREGAR_DADOS = True` (tabelas que a ingestão diária preenche); senão, publica em poucos minutos. Cada carga tem a sua fila de execução (ver "Filas no banco" em `docs/DEPLOY_GRATUITO.md`); disparar outra execução na mesma fila cancela a pendente. Só então avança o `main`, e a Vercel publica. Isso evita o site no ar com código que espera tabelas ou dados que ainda não existem.

- Acompanhe com `gh run list --workflow publicar.yml --limit 1` e `gh run watch <id> --exit-status` em background.
- Forçar recarga sem migração: `gh workflow run publicar.yml --ref dev -f recarregar=true`.
- Migrações só podem acrescentar (tabela nova, coluna opcional); remoções em duas publicações.
- Se o passo "Avançar o main" falhar, o `main` tem commits que o `dev` não tem: traga-os para o `dev` (merge/rebase) e envie de novo. Nunca use `--force`.

## Segredos: nunca passe por eles

A URL do banco existe em dois lugares: secret `DATABASE_URL` do GitHub (string **direta** do Neon) e variável `DATABASE_URL` do projeto `panoptico-api` na Vercel (string **com pooling**, host com `-pooler`). Quem coloca é o usuário. Não leia, não imprima, não copie esses valores (ao listar variáveis, mostre só os nomes). Se uma tarefa exigir o valor, peça para o usuário configurar no painel. O mesmo vale para a chave do Portal da Transparência no `backend/.env`.

## Vercel pela CLI

Login é interativo: rode `npx vercel@latest login` em background, leia a saída e passe ao usuário o link `https://vercel.com/oauth/device?user_code=...`. Confira com `npx vercel@latest whoami`.

Use `vercel api` (chamadas autenticadas sem tocar no token) e **sempre com `MSYS_NO_PATHCONV=1`** no Git Bash:

```bash
export MSYS_NO_PATHCONV=1
npx vercel@latest api /v9/projects/panoptico                          # detalhes (link.repoId = 1408082606)
npx vercel@latest api /v10/projects/panoptico-api/env                 # variáveis (mostre só key/target)
npx vercel@latest api /v9/projects/<proj>/env/<id> -X PATCH --input arq.json   # {"value": "..."}
npx vercel@latest api /v10/projects/<proj>/env -X POST --input arq.json        # nova variável
npx vercel@latest api /v10/projects/<proj>/domains -X POST -f name=<dominio>
npx vercel@latest api /v6/domains/<dominio>/config                    # registros DNS recomendados
npx vercel@latest api /v13/deployments -X POST --input dep.json       # deploy de produção
npx vercel@latest api /v13/deployments/<id>                           # readyState: QUEUED/BUILDING/READY/ERROR
```

Corpo do deploy de produção a partir do `main`:

```json
{"name": "panoptico-api", "project": "panoptico-api", "target": "production",
 "gitSource": {"type": "github", "repoId": 1408082606, "ref": "main"}}
```

Pontos que pegam:
- O `main` (avançado pelo Publicar) dispara deploy dos dois projetos; o `dev` gera só deploys de preview. Deploy manual só é necessário depois de **mudar variáveis**, porque elas só valem a partir do próximo build.
- `NEXT_PUBLIC_*` entram no build do site: mudou, redeploy do `panoptico`.
- A API na Vercel roda sem pool (`settings.serverless`, ativado por `VERCEL=1`) e sem prepared statements, por causa do pooler do Neon.
- `CORS_ORIGINS` é uma lista JSON (`["https://panoptico.social.br","https://www.panoptico.social.br"]`).
- A raiz da API (`/`) responde 404 de propósito (não há página inicial); a documentação interativa está em `/docs`. Para testar se a API está no ar, use `/saude`.

## Ingestão no GitHub Actions

```bash
gh workflow run ingestao.yml                          # atualização normal
gh workflow run ingestao.yml -f carga_inicial=true    # também projetos da Câmara desde 2023 (~25 min)
gh run list --workflow ingestao.yml --limit 3
gh run watch <id> --exit-status --interval 30         # rode em background e espere a notificação
gh run view <id> --log | grep -E "\[ok\]|\[erro\]|Traceback"
```

Uma rodada completa leva ~23 min (as emendas são a parte lenta). Os brutos ficam 7 dias como artefato da execução. Em repositório público, o GitHub **desativa agendamentos após 60 dias sem commits**; se a data em `/fontes` parar, verifique isso primeiro.

## Diagnóstico rápido

```bash
curl -s https://panoptico-api.vercel.app/saude        # banco ok?
curl -s https://panoptico-api.vercel.app/fontes       # datas da última carga de cada fonte
curl -s "https://dns.google/resolve?name=api.panoptico.social.br&type=CNAME"
```

- `"banco":"indisponivel"`: `DATABASE_URL` ausente ou errado na Vercel, ou deploy anterior à variável (redeploy).
- Site abre sem dados: o domínio da API não resolve (DNS) ou o `NEXT_PUBLIC_API_URL` está errado.
- Dados velhos: veja a última execução do `ingestao.yml` e o `fonte_ingestao` via `/fontes`.

## DNS (Registro.br, modo avançado)

Zona atual: `A` da raiz → `216.198.79.1` e `64.29.17.1`; `CNAME www` e `CNAME api` → valores `*.vercel-dns-017.com` mostrados pela Vercel; três `TXT _vercel` de verificação. O DNS fica no próprio Registro.br — não mude os servidores DNS nem ative DNSSEC sem combinar com o usuário. Valores atuais sempre em `/v6/domains/<dominio>/config`.

## Reserva e troca

Detalhes e o porquê em `docs/DEPLOY_GRATUITO.md` ("Reserva e troca automática") e `infra/cloudflare/troca/LEIAME.md`. Nunca leia nem imprima `CF_TOKEN`, `CHAVE_PAINEL` (`~/.panoptico/chave_painel`), `TUNNEL_TOKEN` nem o `.env` da VM.

```bash
# Estado do Worker (a chave vai na URL; leia do arquivo sem imprimir)
curl -s "https://panoptico-troca.mikael-dev.workers.dev/estado?chave=$(cat ~/.panoptico/chave_painel)"   # também /dns e /diagnostico; POST /preparar e /configurar
# Forçar o modo (auto|principal|reserva|observar): wrangler kv key put (formato em infra/cloudflare/troca/LEIAME.md)
cd infra/cloudflare/troca && npx wrangler deploy
# VM de reserva
ssh -i ~/.ssh/panoptico_oracle ubuntu@163.176.196.22
journalctl -u panoptico-atualizar        # na VM: atualização a cada 10 min a partir do main
docker compose ps                        # na VM, em /opt/panoptico/deploy/reserva
# OCI CLI (sem instalar): python -m uv tool run --from oci-cli oci ...   ou   ~/.local/bin/oci ...
```

O Worker troca sozinho (2 falhas seguidas, reserva; 10 sucessos, volta). Para manutenção, ponha em `observar` ou `principal` antes. A reserva nunca roda migração.

## Alternativa

Alternativa ao Neon e à Vercel: `deploy/` tem uma VPS completa (docker compose com Postgres, API, site, Caddy e ingestão por cron) e o guia `docs/DEPLOY.md`. Nada disso está em uso hoje.

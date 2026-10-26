---
name: operar-producao
description: Como operar o Panóptico em produção — VPS Locaweb (banco, API, site e ingestão), Cloudflare, Worker de troca, reservas (Vercel, Neon, Netlify, Oracle) e GitHub Actions (Publicar, CI) — pela linha de comando, sem manipular segredos. Use sempre que a tarefa envolver deploy, logs, backup, disco, domínios e DNS, disparar ou acompanhar cargas, investigar o site ou a API fora do ar ou com dados desatualizados, ou checar o CI, mesmo que o pedido seja só "o site não está funcionando" ou "atualiza os dados".
---

# Operar produção

Desde 26/10/2026 a produção é uma VPS Locaweb. Vercel e Neon deixaram de ser produção (CPU da Vercel esgotada pelo robô da Meta; latência de 114 ms até o Neon nos EUA; custo). Guia completo: `deploy/vps/LEIAME.md`; o porquê em `docs/DECISOES.md` (2026-10-26).

## Mapa

| Parte | Onde | Endereço |
|---|---|---|
| Produção (Postgres 18, API, site, túnel, ingestão) | VPS Locaweb, São Paulo, Ubuntu 24.04, 2 vCPU, 4 GB, 70 GB; `deploy/vps/` em `/opt/panoptico/deploy/vps`; túnel Cloudflare `panoptico-vps`, sem portas abertas além do SSH | https://panoptico.social.br · https://api.panoptico.social.br (teste direto: `vps.` e `api-vps.`) |
| Agenda das cargas | timers systemd em `deploy/vps/agenda/` (diária, PNCP, justiça, câmaras, mensal); trava `federal` no flock | `systemctl list-timers 'panoptico-*'` |
| Atualização | `atualizar.sh` a cada 10 min, a partir do `main` | — |
| Backup | `backup.sh` diário para o bucket Oracle `panoptico-backups`, nomes que se repetem (dia da semana e mês) | — |
| Cloudflare | DNS e proxy; cache da API (respeita `s-maxage`) e das páginas (30 min), em camadas; firewall só contra coletores em massa e robôs de SEO (robôs de pesquisa e de treino de IA liberados) | painel Cloudflare |
| Worker `panoptico-troca` | `infra/cloudflare/troca`: VPS principal; vai para a reserva com 3 falhas seguidas e volta com 10 sucessos; grava no KV só quando o estado muda; `/configurar` e `/trafego` | https://panoptico-troca.mikael-dev.workers.dev |
| Reserva do site | Netlify (`frontend/netlify.toml`), deploy só pelo `reserva-netlify.yml` | https://panoptico.netlify.app |
| Reserva da API | VM Oracle micro `panoptico-reserva-micro` (163.176.196.22), docker compose + túnel (`deploy/reserva`), lê o Neon | `api-reserva.panoptico.social.br` |
| Neon | Só reserva: segue recebendo a ingestão do GitHub Actions por uma semana de teste (desde 26/10) e depois será cancelado | — |
| Vercel | Pausada; reserva antiga | panoptico.vercel.app |
| Oracle ARM grátis | 2 OCPU, 12 GB, para virar a reserva completa com réplica lógica (pendente); orçamento `panoptico-gasto-zero` com alerta, trava de cotas `panoptico-so-gratis` | — |
| CI e Publicar | `.github/workflows/ci.yml`, `publicar.yml` | Actions do repo `Gipsy7/panoptico` |

As travas de custo do Neon/Vercel caíram. Recarga completa e dados do acervo são possíveis na VPS, respeitando disco (70 GB) e RAM (4 GB): cargas pesadas de madrugada e em sequência. Fontes só-Brasil podem rodar lá. Bloqueio deliberado nunca é contornado.

## Publicar código: sempre pelo branch `dev`

Nunca push direto no `main`, nunca `--force`. `git push origin dev` dispara o **Publicar**: testa, migra e avança o `main`; a VPS puxa o `main` sozinha em até 10 min (`atualizar.sh`). O limite de 100 deploys/dia vale só para a Vercel, hoje reserva.

- Acompanhe: `gh run list --workflow publicar.yml --limit 1` e `gh run watch <id> --exit-status` em background.
- Migrações só acrescentam (tabela nova, coluna opcional); remoção em duas publicações. A API aplica as migrações ao subir na VPS.
- Se "Avançar o main" falhar, o `main` tem commits que o `dev` não tem: traga-os para o `dev` e envie de novo.
- Enquanto a semana de teste durar, o Publicar ainda migra o Neon; confira o workflow antes de contar com ele para o banco da VPS.

## Segredos: nunca passe por eles

Não leia nem imprima o `.env` da VPS (`POSTGRES_PASSWORD`, `BACKUP_PAR_URL`, `DATAJUD_CHAVE`), `DATABASE_URL`, `CF_TOKEN`, `CHAVE_PAINEL` (`~/.panoptico/chave_painel`), `TUNNEL_TOKEN` nem a chave do Portal da Transparência. Ao listar variáveis, mostre só os nomes. Se a tarefa exigir o valor, peça ao usuário.

## VPS: comandos de diagnóstico

```bash
ssh -i ~/.ssh/panoptico_vps root@<IP da VPS: painel da Locaweb ou ACOMPANHAMENTO.md local>
cd /opt/panoptico/deploy/vps
docker compose ps                         # banco, api, web, túnel
docker compose logs --tail 100 api        # ou web, db, cloudflared
journalctl -u 'panoptico-*' --since today # cargas, atualização, backup
journalctl -u panoptico-atualizar -n 50   # última atualização a partir do main
systemctl list-timers 'panoptico-*'       # próximas execuções
df -h / /opt/backups; docker system df    # espaço em disco (70 GB)
free -h                                   # RAM (4 GB)
ls -lh /opt/backups | tail                # backups recentes
sudo systemctl start panoptico-<carga>.service   # disparo manual de uma carga
```

De fora:

```bash
curl -s https://api.panoptico.social.br/saude      # banco ok?
curl -s https://api-vps.panoptico.social.br/saude  # direto na VPS, sem passar pelo Worker
curl -s https://api.panoptico.social.br/fontes     # data da última carga de cada fonte
```

- `"banco":"indisponivel"`: contêiner `db` parado ou disco cheio; veja `docker compose ps` e `df -h`.
- Site abre sem dados: API fora, ou o Worker mandou para a reserva (veja o estado abaixo).
- Dados velhos: `journalctl -u 'panoptico-*'` e `/fontes`. As cargas pesadas rodam em sequência pela trava `federal`; uma presa segura as seguintes.
- Backups: confira a data dos arquivos em `/opt/backups` e no bucket `panoptico-backups`; restauração em `deploy/vps/LEIAME.md` (seção 4).

## Cloudflare e Worker de troca

Detalhes em `deploy/vps/LEIAME.md`, `infra/cloudflare/troca/LEIAME.md` e `docs/DEPLOY_GRATUITO.md` ("Reserva e troca automática").

```bash
# Estado do Worker (a chave vai na URL; leia do arquivo sem imprimir)
curl -s "https://panoptico-troca.mikael-dev.workers.dev/estado?chave=$(cat ~/.panoptico/chave_painel)"   # também /dns, /diagnostico e /trafego; POST /preparar e /configurar
# Forçar o modo (auto|principal|reserva|observar): wrangler kv key put (formato em infra/cloudflare/troca/LEIAME.md)
cd infra/cloudflare/troca && npx wrangler deploy
```

Para manutenção da VPS, ponha o Worker em `observar` ou `principal` antes, para ele não trocar à toa. A reserva nunca roda migração.

```bash
# VM Oracle de reserva da API
ssh -i ~/.ssh/panoptico_oracle ubuntu@163.176.196.22
journalctl -u panoptico-atualizar        # na VM: atualização a cada 10 min a partir do main
docker compose ps                        # na VM, em /opt/panoptico/deploy/reserva
# OCI CLI (sem instalar): python -m uv tool run --from oci-cli oci ...   ou   ~/.local/bin/oci ...
```

## Ingestão no GitHub Actions (alimenta o Neon durante o teste)

```bash
gh workflow run ingestao.yml                          # atualização normal
gh workflow run ingestao.yml -f carga_inicial=true    # também projetos da Câmara desde 2023 (~25 min)
gh run list --workflow ingestao.yml --limit 3
gh run watch <id> --exit-status --interval 30         # rode em background e espere a notificação
gh run view <id> --log | grep -E "\[ok\]|\[erro\]|Traceback"
```

Na produção as cargas rodam pela agenda systemd da VPS (ver diagnóstico acima). Em repositório público, o GitHub desativa agendamentos após 60 dias sem commits.

## Vercel pela CLI (reserva; pausada)

Só se a reserva da Vercel for retomada. Login é interativo: `npx vercel@latest login` em background e passe ao usuário o link `https://vercel.com/oauth/device?user_code=...`. Use `vercel api` (sem tocar no token), **sempre com `MSYS_NO_PATHCONV=1`** no Git Bash:

```bash
export MSYS_NO_PATHCONV=1
npx vercel@latest api /v9/projects/panoptico                          # link.repoId = 1408082606
npx vercel@latest api /v10/projects/panoptico-api/env                 # mostre só key/target
npx vercel@latest api /v13/deployments -X POST --input dep.json       # deploy de produção
npx vercel@latest api /v13/deployments/<id>                           # readyState
```

Corpo do deploy a partir do `main`: `{"name": "panoptico-api", "project": "panoptico-api", "target": "production", "gitSource": {"type": "github", "repoId": 1408082606, "ref": "main"}}`. Conta `gipsy7` (Hobby). Variáveis só valem no próximo build; `NEXT_PUBLIC_*` entram no build do site. A API lá roda sem pool (`VERCEL=1`). A raiz da API responde 404 de propósito; teste com `/saude`.

## DNS

A zona está no Cloudflare (nameservers no Registro.br) e os registros de produção apontam para o túnel `panoptico-vps`. Não mude os servidores DNS nem ative DNSSEC sem combinar com o usuário. Os valores da Vercel (A da raiz, CNAME `*.vercel-dns-017.com`) só voltam se a reserva dela for retomada.

## Alternativa

`docs/DEPLOY.md` descreve uma VPS genérica com Caddy; a produção atual usa `deploy/vps/` com túnel Cloudflare.

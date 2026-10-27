# Produção numa VPS única (Locaweb, Ubuntu 24.04, 2 vCPUs, 4 GB)

Banco, API, site e túnel da Cloudflare no mesmo `docker-compose.yml`, sem nenhuma porta aberta além do SSH. O banco daqui é o único: a API aplica as migrações ao subir, e toda carga que rodava no GitHub Actions passa a rodar aqui, pelos timers do systemd (pasta `agenda/`). Nada de segredo vai para o git: `.env` e `/opt/cloudflared` ficam só na VPS.

## 1. Instalação

1. Docker e código (como root ou com sudo):
   ```bash
   curl -fsSL https://get.docker.com | sh
   apt-get install -y git curl python3   # flock já vem no util-linux; python3 serve ao IndexNow
   git clone --branch main https://github.com/Gipsy7/panoptico /opt/panoptico
   git config --system --add safe.directory /opt/panoptico
   ```
2. `.env`: `cd /opt/panoptico/deploy/vps && cp .env.exemplo .env` e preencha `POSTGRES_PASSWORD` (e, se quiser, `BACKUP_PAR_URL`, `DATAJUD_CHAVE`). Grave os valores por um comando que não os exiba; ninguém imprime o arquivo.
3. Túnel: crie o túnel nomeado no painel Zero Trust da Cloudflare e baixe as credenciais. Em `/opt/cloudflared/` ficam `<ID>.json` (credenciais) e `config.yml`:
   ```yaml
   tunnel: <ID-DO-TUNEL>
   credentials-file: /etc/cloudflared/<ID-DO-TUNEL>.json
   ingress:
     - hostname: panoptico.social.br
       service: http://web:3000
     - hostname: api.panoptico.social.br
       service: http://api:8000
     - hostname: vps.panoptico.social.br        # endereço de teste, direto na VPS
       service: http://web:3000
     - hostname: api-vps.panoptico.social.br
       service: http://api:8000
     - service: http_status:404
   ```
   Aponte cada hostname para o túnel no DNS da Cloudflare (CNAME para `<ID>.cfargotunnel.com`). O compose monta `/opt/cloudflared` somente leitura em `/etc/cloudflared`.
4. Suba: `cd /opt/panoptico/deploy/vps && docker compose up -d --build`. Confira: `docker compose ps` e `https://api-vps.panoptico.social.br/saude`.
5. Agenda, backup e atualização automática: `sudo bash /opt/panoptico/deploy/vps/agenda/instalar-agenda.sh`.
6. Pasta de backups: `sudo mkdir -p /opt/backups` (o próprio script também cria).

## 2. Agenda das cargas

Os horários são os mesmos dos workflows do Actions, escritos em UTC no `OnCalendar` (não dependem do fuso da VPS).

| Timer | Quando (UTC / Brasília) | O que roda |
|---|---|---|
| `panoptico-diaria` | todo dia 09:00 / 6h | `ingestion.run_all` |
| `panoptico-pncp` | todo dia 05:30 / 2h30 | contratos do PNCP (recorte da produção) |
| `panoptico-justica` | terça 13:00 / 10h | pessoas, sanções, TCU, CPIs, DataJud, sócios... |
| `panoptico-camaras` | domingo 11:00 / 8h | câmaras, assembleias, catálogo de canais |
| `panoptico-mensal` | dia 15, 10:00 / 7h | SICONFI, Portal, TSE contas, TCE-SP e TCE-RS, Tesouro, empresas |
| `panoptico-backup` | todo dia 12:00 / 9h | `pg_dump` (seção 4) |
| `panoptico-atualizar` | a cada 10 min | `git fetch`; se o `main` mudou, reconstrói API e site |

- Travas (`/var/lock/panoptico-*.lock`, com `flock`): `federal` é comum à diária, justiça, câmaras, mensal e às cargas manuais de TSE e discursos (escrevem nas mesmas tabelas, e a VPS tem 4 GB: nunca duas juntas; quem chega depois espera); `pncp` é só do PNCP (diário e pacote). Se a mensal (horas) estiver rodando, a diária espera e roda em seguida.
- Cada passo roda mesmo que o anterior falhe; o serviço termina com erro se algum falhou (`systemctl status panoptico-diaria`).
- Rodar à mão (mesmo script do timer): `sudo systemctl start panoptico-diaria` (acompanhe com `journalctl -fu panoptico-diaria`).
- Cargas manuais (sem timer, eram `workflow_dispatch`): `bash agenda/tse.sh --so-candidaturas -- "2026"`, `bash agenda/discursos-historico.sh 2025-01-01`, `DE=2025-01-01 ATE=2025-03-21 bash agenda/pncp.sh`, `bash agenda/pncp-pacote.sh pacote.zip manifesto.json`, `CARGA_INICIAL=1 bash agenda/diaria.sh`, `ANOS="2019 2020" bash agenda/mensal.sh`. Qualquer módulo avulso: `docker compose --profile ingestao run --rm ingestao python -m ingestion.<módulo> ...`.
- Bloqueio de um órgão (captcha, 403, `robots.txt`) não se contorna: o passo falha, e o caso vira pedido em `docs/pedidos/`.

## 3. Atualização automática

`atualizar.sh` (timer de 10 em 10 min): `git fetch`; se `origin/main` mudou, `git reset --hard origin/main` e `docker compose up -d --build api web` (a API roda `alembic upgrade head` ao subir). Se algo em `agenda/` mudou, reinstala os timers. Só o `main` publica, como antes (`git push origin dev` roda o Publicar, que avança o `main`). Logs: `journalctl -u panoptico-atualizar`.

Na troca do site, duas proteções contra página velha (27/10/2026: a home guardada no Cloudflare apontava para um CSS que o build novo tinha apagado, e o site abriu sem estilo):

- **Estáticos antigos:** antes de trocar, o script guarda o CSS e o JS do contêiner atual em `/opt/panoptico-estaticos` e devolve ao contêiner novo os dos últimos 2 dias. Uma página velha (cache ou aba aberta) continua achando os arquivos dela.
- **Limpeza do cache:** com o site novo respondendo, o script limpa o cache do Cloudflare (`purge_everything`), se `CF_PURGE_TOKEN` e `CF_ZONE_ID` estiverem no `.env`. O token deve ter só a permissão "Zone > Cache Purge > Purge" na zona. Sem eles, o cache expira sozinho em até 30 min.

## 4. Backup e restauração

`backup.sh` (diário, 12:00 UTC): `pg_dump --format=custom` do serviço `db` para `/opt/backups/panoptico_AAAA-MM-DD_HHMM.dump`, guarda 7 dias no disco e, se `BACKUP_PAR_URL` estiver no `.env`, envia o arquivo com `curl -T arquivo "$BACKUP_PAR_URL$nome"` (URL pré-autenticada do armazenamento externo; vazia = só local). A URL nunca é impressa. Falha no envio faz o serviço terminar com erro; o arquivo local fica.

Restaurar (banco novo ou acidente; para API e site antes):
```bash
cd /opt/panoptico/deploy/vps
docker compose stop api web
docker compose exec -T db pg_restore -U panoptico -d panoptico --clean --if-exists --no-owner \
  < /opt/backups/panoptico_AAAA-MM-DD_HHMM.dump
docker compose up -d api web      # a API confere/aplica as migrações ao subir
```
Em máquina nova: instale (seção 1), suba só o banco (`docker compose up -d db`), restaure como acima e suba o resto. Teste a restauração num banco descartável de vez em quando.

## 5. De onde veio cada carga (Actions para a VPS)

| Workflow (cron UTC) | Vira | Ambiente |
|---|---|---|
| `ingestao.yml` (`0 9 * * *`) | `diaria.sh` | `DATABASE_URL`; carga inicial por `CARGA_INICIAL=1`; os brutos ficam no volume `raw` (sem artefato) |
| `ingestao-pncp.yml` (`30 5 * * *`) | `pncp.sh` | `DATABASE_URL`; `DE`/`ATE` manuais |
| `ingestao-justica.yml` (`0 13 * * 2`) | `justica.sh` | `DATABASE_URL`; `SOCIOS_MAX`, `SOCIOS_REFAZER`; `DATAJUD_CHAVE` opcional |
| `ingestao-camaras.yml` (`0 11 * * 0`) | `camaras.sh` (a matriz por estado e os jobs do runner no Brasil viram passos em sequência) | `DATABASE_URL` |
| `ingestao-mensal.yml` (`0 10 15 * *`) | `mensal.sh` (inclui Tesouro, TCE-RS e empresas, do runner no Brasil) | `DATABASE_URL`; `ANOS` manual |
| `ingestao-tse.yml`, `ingestao-discursos.yml`, `pncp-pacote.yml` (só manuais) | `tse.sh`, `discursos-historico.sh`, `pncp-pacote.sh` (sem timer) | pacote do PNCP copiado à mão em vez de `gh release download` |
| `indexnow.yml` (depois de diária, câmaras, mensal, TSE) | última linha dos scripts (`scripts/indexnow.py`) | nenhum segredo |

Não migram: o passo de migrações de cada workflow (a API migra ao subir), `publicar.yml` (testes, migração, recarga e avanço do `main`: o `ci.yml` segue valendo no GitHub, e o avanço do `main` continua pelo Publicar sem os jobs `migracoes` e `recarga`), o upload de artefatos de brutos e `varredura-canais.yml` (gera o catálogo `data/canais_oficiais.csv` e abre um PR no GitHub, não grava no banco; continua no Actions, que não precisa de `DATABASE_URL`).

Na virada, desligar no Actions (só depois de confirmar uma rodada na VPS): os `schedule` de `ingestao.yml`, `ingestao-pncp.yml`, `ingestao-justica.yml`, `ingestao-camaras.yml` e `ingestao-mensal.yml`, os jobs `migracoes` e `recarga` do `publicar.yml`, o runner do PC no Brasil, e o secret `DATABASE_URL` (do Neon). A recarga após migração (`RECARREGAR_DADOS = True`) passa a ser manual: `sudo systemctl start panoptico-diaria` depois da atualização.

## 6. Logs

```bash
journalctl -u 'panoptico-*' --since today          # todas as cargas, backup e atualização
journalctl -fu panoptico-mensal                    # acompanhar uma carga ao vivo
systemctl list-timers 'panoptico-*'                # próxima execução de cada uma
docker compose logs -f --tail=100 api web cloudflared
```
O disco guarda os brutos das cargas no volume `raw`; confira com `docker system df` e `df -h` de vez em quando.

## 7. Reserva congelada (Vercel + Neon)

A reserva é uma versão fixa do site, da API e do banco na Vercel e no Neon. Ela não recebe cargas nem deploys automáticos: se a VPS cair, o Worker `panoptico-troca` põe essa versão no ar como está. Código e dados ficam congelados **juntos**, para a API da reserva nunca esperar uma coluna que o banco dela não tem.

**Atualizar a reserva** (manual, quando o dono quiser):
1. Escolha o commit do `main` que vai para a reserva (em geral o atual) e confira que a VPS está nele (`git -C /opt/panoptico log -1`).
2. Na VPS, faça o dump do banco: `docker compose exec -T db pg_dump -U panoptico -d panoptico --format=custom > /opt/backups/para_reserva.dump`.
3. Restaure no Neon, com a string **direta** (sem `-pooler`) gravada pelo dono em `/root/.neon_url` (nunca impressa): `docker compose exec -T db pg_restore --clean --if-exists --no-owner --no-acl -d "$(cat /root/.neon_url)" < /opt/backups/para_reserva.dump`. Confira a contagem de linhas das tabelas nos dois lados.
4. Na Vercel, publique os projetos `panoptico` e `panoptico-api` a partir desse commit (deploy manual pela API, ver skill `operar-producao`). Os deploys automáticos continuam desligados.
5. Teste `https://panoptico.vercel.app/` e `https://panoptico-api.vercel.app/saude` antes de considerar concluído.

**Custo:** com o Neon parado, só armazenamento (~US$ 0,75 por mês) e o processamento nas horas em que a reserva estiver no ar.


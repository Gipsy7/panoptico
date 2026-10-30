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
     - hostname: release.panoptico.social.br    # release (homologação), seção 8
       service: http://web-release:3000
     - hostname: api-release.panoptico.social.br
       service: http://api-release:8000
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
| `panoptico-atualizar` | a cada 10 min | `git fetch`; se o `main` mudou, reconstrói API e site; depois, se o `release` mudou, reconstrói o release (seção 8) |

- Travas (`/var/lock/panoptico-*.lock`, com `flock`): `federal` é comum à diária, justiça, câmaras, mensal e às cargas manuais de TSE e discursos (escrevem nas mesmas tabelas, e a VPS tem 4 GB: nunca duas juntas; quem chega depois espera); `pncp` é só do PNCP (diário e pacote). Se a mensal (horas) estiver rodando, a diária espera e roda em seguida.
- Cada passo roda mesmo que o anterior falhe; o serviço termina com erro se algum falhou (`systemctl status panoptico-diaria`).
- Rodar à mão (mesmo script do timer): `sudo systemctl start panoptico-diaria` (acompanhe com `journalctl -fu panoptico-diaria`).
- Cargas manuais (sem timer, eram `workflow_dispatch`): `bash agenda/tse.sh --so-candidaturas -- "2026"`, `bash agenda/discursos-historico.sh 2025-01-01`, `DE=2025-01-01 ATE=2025-03-21 bash agenda/pncp.sh`, `bash agenda/pncp-pacote.sh pacote.zip manifesto.json`, `CARGA_INICIAL=1 bash agenda/diaria.sh`, `ANOS="2019 2020" bash agenda/mensal.sh`. Qualquer módulo avulso: `docker compose --profile ingestao run --rm ingestao python -m ingestion.<módulo> ...`.
- Bloqueio de um órgão (captcha, 403, `robots.txt`) não se contorna: o passo falha, e o caso vira pedido em `docs/pedidos/`.

## 3. Atualização automática

`atualizar.sh` (timer de 10 em 10 min): `git fetch`; se `origin/main` mudou, `git reset --hard origin/main` e `docker compose up -d --build api web` (a API roda `alembic upgrade head` ao subir). Se algo em `agenda/` mudou, reinstala os timers. Depois, sob a mesma trava, atualiza o release (seção 8). A produção só muda quando o `main` muda: pelo workflow manual **Promover para produção** ou por uma **Correção urgente** (`git push origin dev` roda o Publicar, que avança só o `release`). Logs: `journalctl -u panoptico-atualizar`.

Desde o release, o banco da VPS é migrado pela API do release (seção 8), antes de o `main` receber o código. Se a API de produção reiniciar nesse intervalo, o `alembic upgrade head` dela falha (o banco está numa versão que o código do `main` não conhece): ela deixa um aviso no log e sobe assim mesmo, porque as migrações só acrescentam.

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

Não migram: o passo de migrações de cada workflow (a API migra ao subir), `publicar.yml` (desde 30/10 só testa e avança o `release`, sem os jobs `migracoes` e `recarga`; seção 8), o upload de artefatos de brutos e `varredura-canais.yml` (gera o catálogo `data/canais_oficiais.csv` e abre um PR no GitHub, não grava no banco; continua no Actions, que não precisa de `DATABASE_URL`).

Na virada, desligar no Actions (só depois de confirmar uma rodada na VPS): os `schedule` de `ingestao.yml`, `ingestao-pncp.yml`, `ingestao-justica.yml`, `ingestao-camaras.yml` e `ingestao-mensal.yml`, o runner do PC no Brasil, e o secret `DATABASE_URL` (do Neon). Os jobs `migracoes` e `recarga` do `publicar.yml` já saíram (30/10). A recarga após migração (`RECARREGAR_DADOS = True`) passa a ser manual: `sudo systemctl start panoptico-diaria` depois da atualização.

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

## 8. Release (homologação)

O que chega ao `dev` passa primeiro pelo release, um site de teste aberto a quem tiver o link e fora dos buscadores: https://release.panoptico.social.br (API em https://api-release.panoptico.social.br). A produção só muda quando o dono promove.

```
push no dev -> Publicar (só testa) -> branch release -> VPS: release.panoptico.social.br (a api-release migra o banco ao subir)
Promover para produção (manual) -> main (fast-forward até o release) -> VPS: panoptico.social.br
Correção urgente (manual, branch correcao/*) -> testa -> main (a API de produção migra ao subir) -> merge do main no dev -> Publicar -> release
```

- **Mesmo banco da produção** (serviço `db`). A API do release aplica as migrações ao subir (`alembic upgrade head || aviso`, mesmo padrão da produção): é por ela que as migrações novas entram no banco da VPS. Na correção urgente, quem migra é a API de produção, ao subir. Nenhum workflow da publicação usa banco: o secret `DATABASE_URL` (Neon, gravado em 07/10) não é mais usado por eles, e o dono pode apagá-lo depois de desligar as ingestões antigas do Actions que ainda o leem (seção 5).
- **Recarga após migração:** o `atualizar.sh` guarda a versão do banco antes de trocar a API (do release ou da produção) e, depois que ela responde, roda `ingestion.precisa_recarga`. Se alguma migração aplicada declara `RECARREGAR_DADOS = True`, escreve `AVISO ... sudo systemctl start panoptico-diaria` no log. Ele não dispara a carga: quem roda é o operador (`journalctl -u panoptico-atualizar | grep AVISO`). Roda com 1 worker e `mem_limit` de 512 MB; o site do release também tem 512 MB. Sem ingestão no release. CORS da API do release só para `https://release.panoptico.social.br`.
- **Serviços** `api-release` e `web-release` no `docker-compose.yml`, perfil `release`, com contexto de build em `/opt/panoptico-release` (variável `RELEASE_DIR`). A definição dos serviços vem do compose do `main`: o release troca o código, não a infraestrutura. Mudança no compose (variável nova, memória) só vale para o release depois de promovida.
- **Checkout separado:** `atualizar.sh` cria `/opt/panoptico-release` uma vez, como `git worktree` do `/opt/panoptico` em HEAD destacado (idempotente: só cria se não existir). O `main` em `/opt/panoptico` nunca é tocado pelo release.
- **Atualização:** a cada 10 min, depois da produção e sob a mesma trava (`/var/lock/panoptico-atualizar.lock`), se `origin/release` estiver num commit ainda não publicado: `checkout` do commit, `nice -n 19 docker compose --profile release build api-release web-release` e `up -d --no-deps --no-build` (nunca mexe em `db`, `api` ou `web`). O commit publicado fica em `/var/lib/panoptico/release-publicado`; um commit que falhou fica em `release-falhou` e só é tentado de novo quando o release mudar (ou apagando o arquivo). Falha do release não afeta a produção: ela já terminou quando o release começa, e a falha só deixa uma linha no log. Para tentar de novo o mesmo commit: `rm /var/lib/panoptico/release-falhou`.
- **Cache do Cloudflare:** as regras de cache da zona (Worker, `/configurar`) valem só para `panoptico.social.br` e `api.panoptico.social.br`. As páginas do release não ficam na borda (os estáticos têm hash no nome), então o release não limpa cache nenhum.
- **Fora da troca:** o Worker `panoptico-troca` não tem rotas (não intercepta tráfego) e recusa configuração com endereço de release (`enderecosDeRelease`): o release não tem reserva nem entra no failover. Se a VPS cair, o release cai junto.
- **Fora dos buscadores:** o build do release tem `NEXT_PUBLIC_AMBIENTE=release`: `robots.txt` com `Disallow: /` (sem mapa do site), meta `noindex, nofollow`, cabeçalho `X-Robots-Tag: noindex, nofollow` e uma faixa no topo, "Versão de teste — o site oficial é panoptico.social.br". Canônicas e Open Graph apontam para `https://panoptico.social.br`; os links de compartilhar usam o endereço do release.
- **Memória:** o release soma no máximo 1 GB (na prática, 300 a 400 MB: 1 worker da API e o servidor do Next). Se a VPS apertar numa carga pesada, pare o release: `docker compose --profile release stop api-release web-release` (o próximo release publicado sobe de novo).

**Ver o release:**
```bash
curl -s https://api-release.panoptico.social.br/saude
curl -s https://release.panoptico.social.br/robots.txt        # Disallow: /
cat /var/lib/panoptico/release-publicado; git -C /opt/panoptico-release log -1 --oneline
cd /opt/panoptico/deploy/vps && docker compose --profile release ps api-release web-release
docker compose --profile release logs --tail 100 api-release web-release
journalctl -u panoptico-atualizar -n 50                       # linhas "release ..."
```

**Promover para produção** (só o dono decide): Actions > "Promover para produção" > Run workflow, ou `gh workflow run promover-producao.yml` (opcional `-f commit=<sha>`, que precisa estar no release). Faz fast-forward do `main` até a ponta do release (ou até o commit escolhido), sem `--force`, e mostra no resumo da execução o commit promovido e a lista de commits. Falha se o `main` tiver algo que o release não tem (veja "Correção urgente"). A VPS publica a produção em até 10 min.

**Correção urgente** (produção com problema e o release com coisas que ainda não podem subir):
1. `git fetch origin && git switch -c correcao/<nome> origin/main`; corrija, commite e `git push origin correcao/<nome>` (o `ci.yml` testa).
2. `gh workflow run correcao-urgente.yml --ref correcao/<nome>` (ou Actions > "Correção urgente", escolhendo o branch em "Use workflow from"). O workflow confere que o branch é `correcao/*` e saiu do `main` atual, testa e avança o `main` (fast-forward). A VPS publica em até 10 min; a API de produção aplica as migrações ao subir (recarga, se pedida, é o aviso no log e o `systemctl start` manual).
3. O mesmo workflow faz o merge do `main` no `dev` (commit de merge, sem `--force`), envia o `dev` e dispara o Publicar (push feito pelo `GITHUB_TOKEN` não dispara workflows; o disparo por `gh workflow run` dispara), que leva a correção ao release. Com conflito, não força: falha e abre uma issue com os comandos para o merge à mão.
4. Enquanto o merge não chegar ao release, o Promover recusa (o release não contém o `main`) e diz para fazer o merge do `main` no `dev` primeiro.

Publicar, Promover e Correção urgente estão no mesmo grupo de concorrência (`publicacao`): nunca rodam juntos, um espera o outro. O GitHub guarda só uma execução esperando por grupo: se duas ficarem na fila, a mais antiga é cancelada (por exemplo, um Promover disparado durante uma Correção urgente pode ser cancelado pelo Publicar que ela dispara). Se aparecer "cancelado", rode de novo.

**Ativação (uma vez), na ordem:**
1. Push do `dev` com este código. O Publicar (já o novo, lido do `dev`) testa e cria o branch `release`, sem tocar em banco. A VPS ainda não sabe do release: o `atualizar.sh` que roda lá é o do `main` antigo, e a produção não muda.
2. Levar o `main` até o `release` uma vez. O GitHub só lista no Actions os workflows manuais que já estão no branch padrão (`main`), então o "Promover para produção" ainda não tem botão. Tente `gh workflow run promover-producao.yml --ref release`; se o GitHub responder que o workflow não existe, o dono faz o fast-forward à mão, uma única vez (sem `--force`; falha se não for fast-forward): `git fetch origin && git push origin origin/release:refs/heads/main`. Daí em diante os dois workflows manuais aparecem no Actions.
3. Em até 10 min a VPS atualiza a produção (esse ciclo ainda roda o `atualizar.sh` antigo, já carregado na memória). No ciclo seguinte, o novo `atualizar.sh` cria `/opt/panoptico-release` e sobe `api-release` e `web-release` (o primeiro build leva alguns minutos, com prioridade mínima). Até o passo 4, os endereços do release não respondem, e nada mais muda.
4. Operador, com o ok do dono (fora do git): ponha o Worker em `observar`; na VPS, acrescente ao `/opt/cloudflared/config.yml` as duas entradas do release antes do `http_status:404` (seção 1, passo 3) e reinicie o túnel (`docker compose restart cloudflared`, segundos fora do ar); no DNS da Cloudflare, crie `release` e `api-release` como CNAME com proxy para `781d882f-d05b-49f6-b059-638092923fc5.cfargotunnel.com` (túnel `panoptico-vps`, o mesmo de `vps` e `api-vps`). Volte o Worker para `auto`.
5. Conferir: `curl -s https://api-release.panoptico.social.br/saude`; `https://release.panoptico.social.br/` com a faixa de teste; `robots.txt` com `Disallow: /`; `curl -sI https://release.panoptico.social.br/ | grep -i x-robots-tag`; `journalctl -u panoptico-atualizar -n 50`.

## Registros do Argos (chat)

A API grava, sem identificar ninguém, frases que o Argos não entendeu, avaliações e conversas consentidas (migração `0057_argos_registros`; ver `docs/DECISOES.md`, 30/10/2026). Não precisa de variável nova: `ARGOS_REGISTRO=0` no ambiente da API desliga a gravação (as rotas seguem em 204). Os POSTs em `/argos/*` dependem de `CORS_ORIGINS` (produção e release já estão no `docker-compose.yml`) e passam pelo Cloudflare sem cache. O prazo de 180 dias é aplicado pela própria API ao gravar; não há tarefa na agenda. Para ler: `docker compose exec api python -m app.argos_relatorio` (ou `--exportar PASTA`, `--apagar-antigos`).

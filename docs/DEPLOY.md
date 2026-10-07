# Deploy numa VPS

Tudo roda numa máquina só, com Docker:

| Serviço | O que faz |
|---|---|
| `caddy` | Recebe o tráfego nas portas 80/443, emite o certificado HTTPS sozinho e encaminha `/api/*` para a API e o resto para o site |
| `web` | Site Next.js |
| `api` | FastAPI; aplica as migrações ao subir |
| `db` | PostgreSQL 18 |
| `ingestao` | Mesma imagem da API, roda `ingestion.run_all` e sai. Chamado pelo cron |

Arquivos em [deploy/](../deploy/).

## 1. Servidor

- VPS com **2 GB de RAM** e **40 GB de disco** (Ubuntu 24.04). Exemplos: Hetzner CX22, Contabo VPS S.
  - Banco hoje: ~260 MB. Brutos: ~200 MB por dia, podados para os 7 mais recentes de cada fonte.
  - A ingestão das emendas lê um arquivo de ~180 MB; com menos de 2 GB de RAM ela pode faltar memória.
- Abra no firewall só as portas 22, 80 e 443.

## 2. DNS

No registro do domínio (Registro.br), crie dois registros **A** apontando para o IP da VPS:

| Nome | Tipo | Valor |
|---|---|---|
| `panoptico.social.br` | A | IP da VPS |
| `www.panoptico.social.br` | A | IP da VPS |

O Caddy só consegue emitir o certificado depois que o DNS estiver respondendo com o IP certo.

## 3. Instalação

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Código
sudo mkdir -p /opt/panoptico && sudo chown "$USER" /opt/panoptico
git clone <url-do-repositorio> /opt/panoptico
cd /opt/panoptico/deploy

# Configuração
cp .env.exemplo .env
nano .env        # DOMINIO, POSTGRES_PASSWORD (openssl rand -hex 24) e, se tiver, CONTATO_EMAIL

# Subir
docker compose up -d --build
docker compose ps    # todos "running"; a api aplica as migrações na primeira subida
```

Teste: `https://panoptico.social.br/api/saude` deve responder `{"status":"ok","banco":"ok"}`.

## 4. Carga inicial

A primeira carga demora alguns minutos. Os projetos de lei da Câmara precisam dos anos da legislatura inteira, o que o `run_all` não faz sozinho:

```bash
cd /opt/panoptico/deploy
docker compose --profile ingestao run --rm ingestao
docker compose --profile ingestao run --rm ingestao \
  python -m ingestion.camara.proposicoes --ano 2023 2024 2025 2026
```

## 5. Atualização diária e backup

```bash
chmod +x /opt/panoptico/deploy/ingestao_diaria.sh
crontab -e
# adicione:
0 6 * * * /opt/panoptico/deploy/ingestao_diaria.sh >> /var/log/panoptico-ingestao.log 2>&1
```

O script roda a ingestão e grava um backup do banco em `deploy/backups/` (mantém 14 dias). Copie os backups para fora do servidor de vez em quando.

Restaurar um backup:

```bash
docker compose exec -T db pg_restore -U panoptico -d panoptico --clean < backups/panoptico_AAAA-MM-DD.dump
```

## 6. Atualizar o código

```bash
cd /opt/panoptico && git pull
cd deploy && docker compose up -d --build
```

## Problemas comuns

- **Certificado não sai:** o DNS ainda não propagou ou as portas 80/443 estão fechadas. Veja `docker compose logs caddy`.
- **Site no ar mas sem dados:** falta a carga inicial (passo 4).
- **Mudou o `CONTATO_EMAIL` ou o domínio:** rode `docker compose up -d --build web`, porque esses valores entram no build do site.
- **Ingestão falhou numa fonte:** as outras continuam. O erro fica no log e em `fonte_ingestao` (status `erro`); a próxima execução tenta de novo.

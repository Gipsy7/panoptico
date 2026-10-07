#!/usr/bin/env sh
# Atualiza os dados e faz backup do banco. Agende no cron da VPS, por exemplo às 6h:
#   0 6 * * * /opt/panoptico/deploy/ingestao_diaria.sh >> /var/log/panoptico-ingestao.log 2>&1
set -eu

cd "$(dirname "$0")"
DIAS_DE_BACKUP=14

echo "== $(date -Iseconds) ingestão =="
# Uma falha numa fonte não impede as outras (run_all continua e devolve erro no fim).
docker compose --profile ingestao run --rm ingestao || echo "ingestão terminou com erro"

echo "== $(date -Iseconds) backup =="
mkdir -p backups
docker compose exec -T db pg_dump -U panoptico -d panoptico --format=custom \
  > "backups/panoptico_$(date +%F).dump"
find backups -name 'panoptico_*.dump' -mtime +"$DIAS_DE_BACKUP" -delete

echo "== $(date -Iseconds) fim =="

#!/usr/bin/env bash
# Backup diário do banco: pg_dump em formato custom para /opt/backups (7 dias locais) e, se
# BACKUP_PAR_URL estiver preenchida no .env, envio por URL de upload pré-autenticada (PUT).
# O pg_dump usa um retrato consistente: pode rodar durante uma ingestão. A URL nunca é impressa.
set -euo pipefail

DESTINO=/opt/backups
DIAS=7
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p "$DESTINO"

nome="panoptico_$(date -u +%F_%H%M).dump"
echo "[$(date -u +%FT%TZ)] backup: $nome"
docker compose exec -T db pg_dump -U panoptico -d panoptico --format=custom >"$DESTINO/$nome.parcial"
mv "$DESTINO/$nome.parcial" "$DESTINO/$nome"
echo "tamanho: $(du -h "$DESTINO/$nome" | cut -f1)"

find "$DESTINO" -name 'panoptico_*.dump' -mtime +"$DIAS" -delete
find "$DESTINO" -name '*.parcial' -mtime +1 -delete

par=""
if [ -f .env ]; then
  par=$(grep -E '^BACKUP_PAR_URL=' .env | head -n 1 | cut -d= -f2- || true)
fi
if [ -z "$par" ]; then
  echo "BACKUP_PAR_URL vazia: sem envio externo"
  exit 0
fi
# Nomes que se repetem, para o bucket grátis (20 GB) nunca encher sem precisar de regra de
# limpeza: um por dia da semana (sobrescrito na semana seguinte) e um por mês (um ano de
# histórico). São no máximo 19 arquivos. O endereço termina em "/o/": o nome é acrescentado.
falhou=0
for remoto in "panoptico_dia-$(date -u +%u).dump" "panoptico_mes-$(date -u +%m).dump"; do
  if curl -fsS --retry 3 --retry-delay 30 -T "$DESTINO/$nome" "$par$remoto" >/dev/null; then
    echo "enviado ao armazenamento externo: $remoto"
  else
    echo "ERRO: o envio de $remoto falhou (o backup local ficou em $DESTINO/$nome)"
    falhou=1
  fi
done
exit "$falhou"

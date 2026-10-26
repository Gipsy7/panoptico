#!/usr/bin/env bash
# Atualiza a reserva se o main mudou. Roda pelo timer panoptico-atualizar.
set -euo pipefail
cd /opt/panoptico
git fetch --quiet origin main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
  exit 0
fi
echo "main mudou: atualizando para $(git rev-parse --short origin/main)"
git reset --hard origin/main
cd deploy/reserva
[ -f .env ] || { echo ".env ausente; nada a subir"; exit 1; }
docker compose up -d --build
echo "atualizacao concluida"

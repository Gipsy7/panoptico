#!/usr/bin/env bash
# Instala os units do systemd (cargas, backup, atualização) e habilita os timers. Idempotente.
# Uso, na VPS: sudo bash /opt/panoptico/deploy/vps/agenda/instalar-agenda.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "rode como root (sudo)"; exit 1; }

aqui=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
destino=/etc/systemd/system
timers=(diaria pncp justica camaras mensal backup)

for nome in "${timers[@]}"; do
  install -m 0644 "$aqui/panoptico-$nome.service" "$aqui/panoptico-$nome.timer" "$destino/"
done
install -m 0644 "$aqui/../panoptico-atualizar.service" "$aqui/../panoptico-atualizar.timer" "$destino/"
systemctl daemon-reload

for nome in "${timers[@]}" atualizar; do
  systemctl enable --now "panoptico-$nome.timer"
done
echo "Timers ativos:"
systemctl list-timers 'panoptico-*' --no-pager

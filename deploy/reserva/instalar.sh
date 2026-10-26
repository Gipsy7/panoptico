#!/usr/bin/env bash
# Instala a reserva na VM (Ubuntu 24.04 ARM64), como usuário ubuntu. Idempotente.
set -euo pipefail
DESTINO=/opt/panoptico

# Swap de 2 GB, se não houver
if ! swapon --show | grep -q .; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# Docker Engine + compose plugin (repositório oficial)
if ! command -v docker >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

# Código
if [ ! -d "$DESTINO/.git" ]; then
  sudo git clone --branch main https://github.com/Gipsy7/panoptico "$DESTINO"
fi
sudo chown -R "$USER":"$USER" "$DESTINO"
chmod +x "$DESTINO"/deploy/reserva/*.sh

# Timer de atualização a cada 10 min (serviço roda como root: usa o docker sem novo login)
sudo git config --system --replace-all safe.directory "$DESTINO" || true
sudo tee /etc/systemd/system/panoptico-atualizar.service >/dev/null <<UNIT
[Unit]
Description=Atualiza a reserva do Panoptico se o main mudou
After=docker.service network-online.target

[Service]
Type=oneshot
ExecStart=$DESTINO/deploy/reserva/atualizar.sh
UNIT
sudo tee /etc/systemd/system/panoptico-atualizar.timer >/dev/null <<UNIT
[Unit]
Description=Verifica atualizacoes da reserva a cada 10 minutos

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now panoptico-atualizar.timer

echo "Pronto. Falta criar $DESTINO/deploy/reserva/.env (veja LEIAME.md)."

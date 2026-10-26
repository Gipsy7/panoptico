#!/usr/bin/env bash
# Atualiza a VPS se o main mudou. Roda pelo timer panoptico-atualizar (a cada 10 min), como root.
# A API aplica as migrações ao subir. Tudo fica dentro de main(): o "git reset --hard" pode
# reescrever este arquivo enquanto o bash o lê, e a função inteira já está na memória.
set -euo pipefail

main() {
  local raiz=/opt/panoptico
  cd "$raiz"
  exec 8>/var/lock/panoptico-atualizar.lock
  flock -n 8 || { echo "outra atualizacao em andamento"; return 0; }

  git fetch --quiet origin main
  local antes depois
  antes=$(git rev-parse HEAD)
  depois=$(git rev-parse origin/main)
  [ "$antes" != "$depois" ] || return 0

  echo "main mudou: atualizando de ${antes:0:7} para ${depois:0:7}"
  git reset --hard origin/main
  cd "$raiz/deploy/vps"
  [ -f .env ] || { echo ".env ausente; nada a subir"; return 1; }

  # Imagem da API e do site; a API aplica as migrações ao subir. A imagem da ingestão sai do
  # mesmo contexto (camadas em cache), assim as cargas agendadas nao compilam na hora.
  # Primeiro só constrói, com o site antigo no ar (o build do Next ocupa os 2 núcleos por minutos);
  # depois troca os contêineres, o que leva segundos. Construir e trocar juntos derrubava os testes
  # do Worker de troca e mandava o tráfego para a reserva.
  nice -n 10 docker compose build api web
  docker compose --profile ingestao build ingestao
  docker compose up -d --no-build api web
  docker image prune -f >/dev/null

  # Se os units ou os scripts da agenda mudaram, reinstala (copia os units e recarrega o systemd).
  if ! git diff --quiet "$antes" "$depois" -- deploy/vps/agenda; then
    echo "agenda mudou: reinstalando os timers"
    bash "$raiz/deploy/vps/agenda/instalar-agenda.sh"
  fi
  echo "atualizacao concluida"
}

main "$@"
exit $?

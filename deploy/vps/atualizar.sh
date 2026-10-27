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
  guardar_estaticos
  docker compose up -d --no-build api web
  devolver_estaticos
  docker image prune -f >/dev/null
  esperar_site
  limpar_cache_cloudflare

  # Se os units ou os scripts da agenda mudaram, reinstala (copia os units e recarrega o systemd).
  if ! git diff --quiet "$antes" "$depois" -- deploy/vps/agenda; then
    echo "agenda mudou: reinstalando os timers"
    bash "$raiz/deploy/vps/agenda/instalar-agenda.sh"
  fi
  echo "atualizacao concluida"
}

# Arquivos estáticos dos builds anteriores (CSS e JS com hash no nome). Uma página guardada no
# cache do Cloudflare (30 min) ou aberta num celular aponta para eles; sem eles o site abre sem
# estilo. Antes da troca, guarda os do contêiner atual (com a data da troca); depois, devolve ao
# novo contêiner os dos últimos 2 dias.
ESTATICOS=/opt/panoptico-estaticos

guardar_estaticos() {
  local tmp
  # Nada aqui pode interromper a atualização: falhou, segue sem os estáticos antigos.
  tmp=$(mktemp -d) || return 0
  if mkdir -p "$ESTATICOS" && docker compose cp web:/app/.next/static/. "$tmp/" >/dev/null 2>&1; then
    { find "$tmp" -type f -exec touch {} + && cp -a "$tmp/." "$ESTATICOS/"; } \
      || echo "falha ao guardar os estaticos do site anterior"
  else
    echo "sem estaticos do site anterior para guardar"
  fi
  rm -rf "$tmp" || true
  find "$ESTATICOS" -type f -mtime +2 -delete 2>/dev/null || true
}

devolver_estaticos() {
  docker compose cp "$ESTATICOS/." web:/app/.next/static/ >/dev/null \
    || echo "falha ao devolver os estaticos antigos ao site"
}

esperar_site() {
  local i
  for i in $(seq 1 30); do
    docker compose exec -T web node -e \
      "fetch('http://localhost:3000/').then(r=>process.exit(r.ok?0:1),()=>process.exit(1))" \
      2>/dev/null && return 0
    sleep 2
  done
  echo "site nao respondeu em 60 s"
}

# Limpa o cache do Cloudflare para a versão nova valer na hora (senão a borda serve a antiga por
# até 30 min). Precisa de CF_PURGE_TOKEN (permissão só de "Cache Purge" na zona) e CF_ZONE_ID no
# .env; o token vai num cabeçalho lido de um descritor, nunca na linha de comando nem no log.
limpar_cache_cloudflare() {
  local token zona
  token=$(grep -E '^CF_PURGE_TOKEN=' .env | cut -d= -f2- || true)
  zona=$(grep -E '^CF_ZONE_ID=' .env | cut -d= -f2- || true)
  if [ -z "$token" ] || [ -z "$zona" ]; then
    echo "sem CF_PURGE_TOKEN ou CF_ZONE_ID no .env: cache do Cloudflare nao foi limpo"
    return 0
  fi
  if curl -fsS -o /dev/null -X POST "https://api.cloudflare.com/client/v4/zones/$zona/purge_cache" \
      -H @<(printf 'Authorization: Bearer %s\n' "$token") \
      -H "Content-Type: application/json" --data '{"purge_everything":true}'; then
    echo "cache do Cloudflare limpo"
  else
    echo "falha ao limpar o cache do Cloudflare"
  fi
}

main "$@"
exit $?

#!/usr/bin/env bash
# Atualiza a VPS. Roda pelo timer panoptico-atualizar (a cada 10 min), como root.
#   1. Produção: se o main mudou, reconstrói API e site a partir de /opt/panoptico.
#   2. Release (homologação, release.panoptico.social.br): se o branch release mudou, reconstrói
#      api-release e web-release a partir de /opt/panoptico-release (git worktree criado aqui).
# Os dois passos rodam sob a mesma trava, um depois do outro, nunca em paralelo. Falha no release
# não derruba nem impede a produção (que já terminou quando ele começa).
# As duas APIs aplicam as migrações ao subir (a do release primeiro: é por ela que as migrações
# novas entram no banco da VPS). Tudo fica dentro de
# funções chamadas pela última linha: o "git reset --hard" pode reescrever este arquivo enquanto o
# bash o lê, e as funções já estão na memória.
set -euo pipefail

RAIZ=/opt/panoptico
RELEASE_DIR=${RELEASE_DIR:-/opt/panoptico-release}
ESTADO_RELEASE=/var/lib/panoptico
PRODUCAO_MUDOU=0

main() {
  cd "$RAIZ"
  exec 8>/var/lock/panoptico-atualizar.lock
  flock -n 8 || { echo "outra atualizacao em andamento"; return 0; }

  atualizar_producao
  # Chamada num "||": o set -e não vale lá dentro, por isso cada passo do release confere o próprio erro.
  atualizar_release || echo "release: falhou (a producao nao foi afetada; tenta de novo quando o release mudar)"
}

atualizar_producao() {
  local raiz=$RAIZ
  cd "$raiz"
  git fetch --quiet origin main
  local antes depois
  antes=$(git rev-parse HEAD)
  depois=$(git rev-parse origin/main)
  [ "$antes" != "$depois" ] || return 0
  PRODUCAO_MUDOU=1

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
  local versao_antes
  versao_antes=$(versao_do_banco api)
  docker compose up -d --no-build api web
  devolver_estaticos
  docker image prune -f >/dev/null
  esperar_site
  avisar_recarga api "$versao_antes"
  limpar_cache_cloudflare

  # Se os units ou os scripts da agenda mudaram, reinstala (copia os units e recarrega o systemd).
  if ! git diff --quiet "$antes" "$depois" -- deploy/vps/agenda; then
    echo "agenda mudou: reinstalando os timers"
    bash "$raiz/deploy/vps/agenda/instalar-agenda.sh"
  fi
  echo "atualizacao concluida"
}

# Release: publica a ponta do origin/release se ela ainda não foi publicada. O último commit
# publicado e o último que falhou ficam em $ESTADO_RELEASE; um commit que falhou não é tentado de
# novo a cada 10 min (só quando o release mudar, ou apagando release-falhou). Sem limpeza de cache
# do Cloudflare: as regras de cache da zona valem só para os endereços de produção, então as
# páginas do release não ficam guardadas na borda (os estáticos têm hash no nome).
atualizar_release() {
  local vps="$RAIZ/deploy/vps" rel=$RELEASE_DIR alvo publicado falhou
  cd "$RAIZ" || return 1
  # Sem branch release no GitHub (ainda): nada a fazer, em silêncio.
  git fetch --quiet origin release 2>/dev/null || return 0
  alvo=$(git rev-parse --verify --quiet origin/release) || return 0
  [ -f "$vps/.env" ] || return 0

  # Checkout separado, criado uma vez (idempotente): o main de /opt/panoptico nunca é tocado.
  if [ ! -e "$rel/.git" ]; then
    if [ -e "$rel" ] && [ -n "$(ls -A "$rel" 2>/dev/null)" ]; then
      echo "release: $rel existe e nao e um checkout; nada feito"
      return 1
    fi
    echo "release: criando o checkout em $rel"
    git worktree prune || return 1
    git worktree add --detach "$rel" "$alvo" >/dev/null || return 1
    git config --system --get-all safe.directory 2>/dev/null | grep -qxF "$rel" \
      || git config --system --add safe.directory "$rel" || return 1
  fi

  mkdir -p "$ESTADO_RELEASE" || return 1
  publicado=$(cat "$ESTADO_RELEASE/release-publicado" 2>/dev/null || true)
  falhou=$(cat "$ESTADO_RELEASE/release-falhou" 2>/dev/null || true)
  cd "$vps" || return 1
  export RELEASE_DIR="$rel"
  local dc=(docker compose --profile release)

  if [ "$alvo" = "$publicado" ] || [ "$alvo" = "$falhou" ]; then
    # Nada novo no release. Se o compose do main mudou agora, reaplica a definição dos serviços
    # do release (o compose só recria o que mudou).
    if [ "$PRODUCAO_MUDOU" = 1 ] && [ -n "$publicado" ]; then
      "${dc[@]}" up -d --no-deps --no-build api-release web-release || return 1
    fi
    return 0
  fi

  echo "release mudou: publicando ${alvo:0:7} (antes: ${publicado:0:7})"
  git -C "$rel" checkout --quiet --detach --force "$alvo" || return 1
  # Prioridade mínima: a produção (site no ar, cargas) passa na frente. --no-deps: nunca mexe em
  # db, api ou web da produção.
  if ! nice -n 19 "${dc[@]}" build api-release web-release; then
    echo "$alvo" > "$ESTADO_RELEASE/release-falhou"
    return 1
  fi
  local versao_antes
  versao_antes=$(versao_do_banco api-release)
  # Primeiro release: sem api-release no ar, a versão vem da API de produção.
  [ -n "$versao_antes" ] || versao_antes=$(versao_do_banco api)
  if ! "${dc[@]}" up -d --no-deps --no-build api-release web-release; then
    echo "$alvo" > "$ESTADO_RELEASE/release-falhou"
    return 1
  fi
  docker image prune -f >/dev/null || true
  esperar_site web-release
  avisar_recarga api-release "$versao_antes"
  echo "$alvo" > "$ESTADO_RELEASE/release-publicado" || return 1
  rm -f "$ESTADO_RELEASE/release-falhou"
  echo "release publicado em ${alvo:0:7}"
}

# Versão do banco (alembic current) vista por um contêiner de API em execução; vazio se não der
# para saber (contêiner parado, ou banco numa versão que o código dele não conhece). Nunca falha.
versao_do_banco() {
  docker compose --profile release exec -T "$1" alembic current 2>/dev/null     | awk 'NF && $1 ~ /^[0-9A-Za-z_]+$/ {v=$1} END {print v}' || true
}

# A API migra ao subir. Depois que ela responde (o alembic já terminou), compara a versão do banco
# com a de antes; se mudou e alguma migração aplicada declara RECARREGAR_DADOS = True
# (ingestion.precisa_recarga), só AVISA no log: a recarga é manual. Nunca falha nem dispara nada.
avisar_recarga() {
  local servico=$1 antes=$2 depois i precisa
  for i in $(seq 1 45); do
    docker compose --profile release exec -T "$servico" python -c       "import urllib.request as u; u.urlopen('http://localhost:8000/saude', timeout=4)"       >/dev/null 2>&1 && break
    sleep 2
  done
  depois=$(versao_do_banco "$servico")
  if [ -z "$antes" ] || [ -z "$depois" ] || [ "$antes" = "$depois" ]; then
    return 0
  fi
  echo "$servico: banco migrado de $antes para $depois"
  precisa=$(docker compose --profile release exec -T "$servico"     python -m ingestion.precisa_recarga "$antes" "$depois" 2>/dev/null | tail -n 1) || true
  if [ "$precisa" = "true" ]; then
    echo "$servico: AVISO: migracao com RECARREGAR_DADOS = True; rode a recarga a mao: sudo systemctl start panoptico-diaria"
  fi
  return 0
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
  local servico=${1:-web} i
  for i in $(seq 1 30); do
    # O perfil "release" deixa o compose achar o web-release; para o web não muda nada.
    docker compose --profile release exec -T "$servico" node -e \
      "fetch('http://localhost:3000/').then(r=>process.exit(r.ok?0:1),()=>process.exit(1))" \
      2>/dev/null && return 0
    sleep 2
  done
  echo "$servico nao respondeu em 60 s"
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

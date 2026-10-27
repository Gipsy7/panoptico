# Funções comuns das cargas. Use com: . "$(dirname "$0")/_comum.sh"
# Cada carga roda pelo serviço "ingestao" do compose (mesma imagem da API, mesmo banco).
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ/deploy/vps"
FALHAS=0

log() { echo "[$(date -u +%FT%TZ)] $*"; }

# travar <nome>: espera a trava de arquivo (fica aberta até o script acabar).
# Cargas que escrevem nas mesmas tabelas usam a mesma trava e nunca rodam juntas.
travar() {
  exec 9>"/var/lock/panoptico-$1.lock"
  log "aguardando a trava $1"
  flock 9
  log "trava $1 obtida"
}

# ingestao <comando...>: roda dentro do contêiner; LIMITE=<tempo> (ex.: 40m) encerra se passar.
ingestao() {
  if [ -n "${LIMITE:-}" ]; then
    timeout "$LIMITE" docker compose --profile ingestao run --rm -T ingestao "$@"
  else
    docker compose --profile ingestao run --rm -T ingestao "$@"
  fi
}

# py <módulo> [args]: python -m <módulo> no contêiner.
py() { ingestao python -m "$@"; }

# passo <título> <comando...>: uma falha não impede os passos seguintes (como "!cancelled()" no Actions).
passo() {
  local titulo=$1
  shift
  log "inicio: $titulo"
  if "$@"; then
    log "ok: $titulo"
  else
    log "ERRO: $titulo"
    FALHAS=$((FALHAS + 1))
  fi
}

# passo_tolerante: igual, mas o erro não reprova a carga (continue-on-error do Actions).
passo_tolerante() {
  local titulo=$1
  shift
  log "inicio: $titulo"
  if "$@"; then log "ok: $titulo"; else log "aviso (tolerado): $titulo falhou"; fi
}

# Avisa os buscadores das páginas que mudaram (só stdlib, sem segredo); falha não reprova a carga.
indexnow() { python3 "$RAIZ/scripts/indexnow.py" "$@" || log "indexnow falhou (ignorado)"; }

# fim: resumo e código de saída (aparece no systemd/journalctl).
fim() {
  log "fim: $FALHAS passo(s) com erro"
  [ "$FALHAS" -eq 0 ]
}

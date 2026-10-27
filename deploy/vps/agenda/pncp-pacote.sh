#!/usr/bin/env bash
# Manual (era pncp-pacote.yml): carga histórica do PNCP a partir de um pacote gerado no acervo.
# Uso: bash pncp-pacote.sh /caminho/pncp-pacote.zip /caminho/pncp-pacote.manifesto.json
# (copie os dois arquivos da release do GitHub para a VPS antes). Trava "pncp".
set -eu
. "$(dirname "$0")/_comum.sh"
[ $# -eq 2 ] || { echo "uso: $0 pacote.zip manifesto.json"; exit 2; }
zip=$(readlink -f "$1")
manifesto=$(readlink -f "$2")
esperado=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["arquivo_sha256"])' "$manifesto")
real=$(sha256sum "$zip" | cut -d' ' -f1)
if [ -z "$esperado" ] || [ "$esperado" != "$real" ]; then
  echo "sha256 do zip não confere com o manifesto"
  exit 1
fi
travar pncp
# Os dois arquivos entram no contêiner por volumes avulsos, só leitura.
docker compose --profile ingestao run --rm -T \
  -v "$zip":/pacote/pncp-pacote.zip:ro -v "$manifesto":/pacote/manifesto.json:ro ingestao \
  python -m ingestion.pncp.pacote carregar --arquivo /pacote/pncp-pacote.zip --manifesto /pacote/manifesto.json

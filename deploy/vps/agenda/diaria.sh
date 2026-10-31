#!/usr/bin/env bash
# Ingestão diária (era ingestao.yml, 6h de Brasília). CARGA_INICIAL=1 baixa também os projetos
# de lei da Câmara desde 2023. Trava "federal": também vale para a recarga após migração.
set -eu
. "$(dirname "$0")/_comum.sh"
travar federal
if [ "${CARGA_INICIAL:-}" = "1" ]; then
  anos=$(seq 2023 "$(date +%Y)" | tr '\n' ' ')
  # shellcheck disable=SC2086
  passo "Projetos de lei da Câmara desde 2023" py ingestion.camara.proposicoes --ano $anos
fi
LIMITE=90m passo "Ingestão de todas as fontes" py ingestion.run_all
indexnow --padrao '^https://[^/]+/?$' --padrao '/parlamentar/'
# Resumo diário dos avisos. Roda o código do release; na promoção, troca para a api.
passo_tolerante "Avisos (release)" timeout 15m \
  docker compose --profile release exec -T api-release python -m app.avisos_diario
fim

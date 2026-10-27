#!/usr/bin/env bash
# Contratos do PNCP, recorte da produção (era ingestao-pncp.yml, 2h30 de Brasília). Trava "pncp".
# Manual com janela: DE=2025-01-01 ATE=2025-03-21 bash pncp.sh (em branco: continua do cursor).
set -eu
. "$(dirname "$0")/_comum.sh"
travar pncp
args=(--producao --releitura 3)
[ -z "${DE:-}" ] || args+=(--de "$DE")
[ -z "${ATE:-}" ] || args+=(--ate "$ATE")
LIMITE=${LIMITE:-120m} passo "Contratos do PNCP" py ingestion.pncp.contratos "${args[@]}"
fim

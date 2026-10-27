#!/usr/bin/env bash
# Manual (era discursos-historico, workflow_dispatch): ~11 mil pedidos, algumas horas.
# Uso: bash discursos-historico.sh [AAAA-MM-DD]   (padrão 2025-01-01). Trava "federal".
set -eu
. "$(dirname "$0")/_comum.sh"
travar federal
passo "Discursos da Câmara (histórico)" py ingestion.camara.discursos --desde "${1:-2025-01-01}"
fim

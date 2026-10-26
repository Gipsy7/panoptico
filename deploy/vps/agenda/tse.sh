#!/usr/bin/env bash
# Manual (era ingestao-tse.yml, workflow_dispatch): uma vez por eleição ou para reprocessar.
# Uso: bash tse.sh [--so-candidaturas [--com-votos]] [--so-fotos] [--fotos] [-- "2018 2022 2024"]
#   Padrão de anos: "2018 2022 2024". Fotos: FOTOS_ANOS="2022 2024" FOTOS_UFS="SC RS".
# Trava "federal".
set -eu
. "$(dirname "$0")/_comum.sh"
so_candidaturas=0 com_votos=0 fotos=0 so_fotos=0
while [ $# -gt 0 ]; do
  case "$1" in
    --so-candidaturas) so_candidaturas=1 ;;
    --com-votos) com_votos=1 ;;
    --fotos) fotos=1 ;;
    --so-fotos) so_fotos=1 ;;
    --)
      shift
      break
      ;;
    *)
      echo "opção desconhecida: $1"
      exit 2
      ;;
  esac
  shift
done
anos=${1:-"2018 2022 2024"}
fotos_anos=${FOTOS_ANOS:-"2022 2024"}
fotos_ufs=${FOTOS_UFS:-}
travar federal

# shellcheck disable=SC2086
if [ "$so_fotos" = 0 ]; then
  passo "Candidaturas" py ingestion.tse.candidaturas --ano $anos
  if [ "$so_candidaturas" = 0 ]; then
    passo "Bens declarados" py ingestion.tse.bens --ano $anos
    passo "Contas de campanha" py ingestion.tse.campanha --ano $anos
    passo "Redes sociais" py ingestion.tse.redes --ano $anos
  fi
  if [ "$so_candidaturas" = 0 ] || [ "$com_votos" = 1 ]; then
    passo "Votos recebidos" py ingestion.tse.votos --ano $anos
  fi
fi
# shellcheck disable=SC2086
if [ "$fotos" = 1 ] || [ "$so_fotos" = 1 ]; then
  if [ -n "$fotos_ufs" ]; then
    passo "Fotos dos eleitos" py ingestion.tse.fotos --ano $fotos_anos --uf $fotos_ufs
  else
    passo "Fotos dos eleitos" py ingestion.tse.fotos --ano $fotos_anos
  fi
fi
indexnow --padrao '/eleito/'
fim

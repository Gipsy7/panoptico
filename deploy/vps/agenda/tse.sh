#!/usr/bin/env bash
# Manual (era ingestao-tse.yml, workflow_dispatch): uma vez por eleição ou para reprocessar.
# Uso: bash tse.sh [--so-candidaturas [--com-votos]] [--so-fotos] [--fotos] [--resultado-2-turno] [-- "2018 2022 2024"]
#   --resultado-2-turno: só o resultado do 2º turno de presidente e governador (divulgação do TSE,
#   na noite da votação, antes dos dados abertos); grava só disputa totalizada.
#   Padrão de anos: "2018 2022 2024". Fotos: FOTOS_ANOS="2022 2024" FOTOS_UFS="SC RS".
# Trava "federal".
set -eu
. "$(dirname "$0")/_comum.sh"
so_candidaturas=0 com_votos=0 fotos=0 so_fotos=0 resultado_2t=0
while [ $# -gt 0 ]; do
  case "$1" in
    --so-candidaturas) so_candidaturas=1 ;;
    --com-votos) com_votos=1 ;;
    --fotos) fotos=1 ;;
    --so-fotos) so_fotos=1 ;;
    --resultado-2-turno) resultado_2t=1 ;;
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

if [ "$resultado_2t" = 1 ]; then
  # Saída 3 = nada totalizado ainda (não é falha): tenta de novo na próxima rodada.
  log "inicio: Resultado do 2o turno"
  if py ingestion.tse.resultado_2_turno --ano "${RESULTADO_ANO:-2026}"; then
    log "ok: Resultado do 2o turno"
  else
    log "aviso: Resultado do 2o turno sem gravação (ainda não totalizado ou erro; veja acima)"
  fi
  indexnow --padrao '/segundo-turno'
  fim
  exit 0
fi

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

#!/usr/bin/env bash
# Alertas de operacao por e-mail ao dono (fluxo grande, cargas com erro, API ou site sem
# responder, disco cheio). Roda a cada 5 minutos, sem trava: so le o banco e grava o que enviou.
# Regras em backend/app/services/alertas.py. Se a VPS inteira cair, quem avisa e o Worker de troca.
set -eu
. "$(dirname "$0")/_comum.sh"
LIMITE=3m py app.alertas

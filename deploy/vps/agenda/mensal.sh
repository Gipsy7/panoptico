#!/usr/bin/env bash
# Ingestão mensal (era ingestao-mensal.yml, dia 15, 7h de Brasília). Trava "federal".
# Na VPS (Brasil) o Tesouro, o TCE-RS e o cadastro de empresas, que no Actions rodavam no
# runner do PC, entram aqui. ANOS="2024 2025" restringe os anos (vazio = padrão de cada fonte).
set -eu
. "$(dirname "$0")/_comum.sh"
travar federal
ANOS=${ANOS:-}
ano=$(date +%Y)
anos_contas=${ANOS:-"$((ano - 2)) $((ano - 1))"}
anos_atual=${ANOS:-"$((ano - 1)) $ano"}

# Um ano por vez: se um falhar, o outro já ficou gravado.
for a in $anos_contas; do passo "Contas dos municípios $a (SICONFI)" py ingestion.siconfi.contas --ano "$a"; done
# shellcheck disable=SC2086
passo "Contas dos estados (SICONFI)" py ingestion.siconfi.contas_estados --ano $anos_contas
passo "Agenda de autoridades (e-Agendas)" py ingestion.executivo.eagendas
passo "Arrecadação federal por estado" py ingestion.receita.arrecadacao_uf
passo "População (IBGE)" py ingestion.ibge.populacao
# O WAF do Portal responde 403/405 a quem pede demais: a carga para no primeiro bloqueio e a
# próxima execução retoma. Nunca se contorna.
if [ -n "$ANOS" ]; then
  # shellcheck disable=SC2086
  passo_tolerante "Transferências da União (Portal)" py ingestion.portal.transferencias --ano $ANOS
else
  passo_tolerante "Transferências da União (Portal)" py ingestion.portal.transferencias
fi
for a in $anos_atual; do passo "Contas dos partidos $a (TSE)" py ingestion.tse.contas_partidarias --ano "$a"; done
passo "Fundos por gênero e raça (TSE)" py ingestion.tse.fefc_fp --ano 2024
for a in $anos_contas; do passo "Despesas por fornecedor $a (TCE-SP)" py ingestion.tce.sp --ano "$a"; done
# shellcheck disable=SC2086
passo "Transferências obrigatórias (Tesouro)" py ingestion.tesouro.transferencias --ano $anos_atual
for a in $anos_contas; do passo "Despesas por fornecedor $a (TCE-RS)" py ingestion.tce.rs --ano "$a"; done

# Cadastro de empresas: base de ~7,8 GB lida em fluxo; o servidor da Receita já travou uma vez
# sem erro, então até três tentativas (a seguinte pula os zips já lidos).
empresas() {
  local t
  for t in 1 2 3; do
    if LIMITE=210m py ingestion.receita.empresas --brasilapi --limite-brasilapi 100; then return 0; fi
    log "tentativa $t falhou; recomeçando pelos arquivos que faltam"
    sleep 60
  done
  return 1
}
passo "Cadastro de empresas (Receita)" empresas
indexnow --padrao '/cidade/'
fim

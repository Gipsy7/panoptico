#!/usr/bin/env bash
# Câmaras e assembleias (era ingestao-camaras.yml, domingo 8h de Brasília). Trava "federal":
# grava mandato_local e votacao_local, de que a identidade (justica.sh) depende.
# Na VPS (Brasil) caem aqui também as fontes que o Actions mandava para o runner do PC
# (geobloqueio): Roraima, Porto Velho, Búzios, ALMG, ALEPE, CLDF, ALRS, ALBA, ALES, ALEMA, ALESE, ALAP.
set -eu
. "$(dirname "$0")/_comum.sh"
travar federal

passo "Catálogo de canais oficiais" py ingestion.canais.catalogo
passo "Câmaras com SAPL (todos os estados)" py ingestion.camaras.sapl
passo "Câmaras no portal da Cittatec" py ingestion.camaras.cittatec
for m in portal_php cr2 portal_modelo aos sistemas fornecedores_alfred fornecedores_batgirl \
  nucleogov fornecedores_robin; do
  passo "Câmaras: $m" py ingestion.camaras."$m"
done
passo "Assembleias com SAPL" py ingestion.assembleias.sapl --uf AC AL AM PB PI RO TO RR
for m in almg alesp alepe cldf alesc; do
  passo "Assembleia: $m" py ingestion.assembleias."$m"
done
# Depois da ALESC, para ligar os autores das emendas.
passo "Emendas estaduais de SC" py ingestion.emendas_estaduais.sc
for m in alerj alep alrs alba ales alece alepa almt alema alems alrn alese alap alego; do
  passo "Assembleia: $m" py ingestion.assembleias."$m"
done
# Emendas estaduais das outras UFs com dado aberto, depois de todas as assembleias (liga os
# autores aos deputados). Uma transação por UF; a falha de uma não apaga nem para as outras.
passo "Emendas estaduais (MG, BA, PE, MA, ES, AL, SE, AC)" \
  py ingestion.emendas_estaduais.registro --uf MG BA PE MA ES AL SE AC
indexnow --padrao '/deputado-estadual/'
fim

#!/usr/bin/env bash
# Justiça e identidade (era ingestao-justica.yml, terça 10h de Brasília). Trava "federal":
# lê candidatura, parlamentar e mandato_local, que a diária e as câmaras escrevem.
# SOCIOS_MAX (padrão 250) e SOCIOS_REFAZER=1 vêm do ambiente, se quiser mudar à mão.
set -eu
. "$(dirname "$0")/_comum.sh"
travar federal
socios_max=${SOCIOS_MAX:-250}
refazer=()
[ "${SOCIOS_REFAZER:-}" != "1" ] || refazer=(--refazer)
ano=$(date +%Y)

passo "Pessoas (identidade única)" py ingestion.pessoas
passo "Cassações do TSE" py ingestion.tse.cassacoes --ano 2016 2018 2020 2022 2024 2026
passo "Sanções (CGU)" py ingestion.transparencia.sancoes
passo "Cargos federais (servidores)" py ingestion.transparencia.servidores
for a in $((ano - 1)) "$ano"; do
  passo "Viagens a serviço $a" py ingestion.transparencia.viagens --ano "$a"
done
# Espera: o Portal pede verificação humana (405) depois de ~15 pedidos seguidos do mesmo IP.
# Se pedir, o passo falha sem efeito e nada se contorna (ver docs/pedidos/).
log "espera de 300 s antes do cartão de pagamento"
sleep 300
passo "Cartão de pagamento (CPGF)" py ingestion.transparencia.cpgf
LIMITE=60m passo "Sócios das empresas" py ingestion.receita.socios --max "$socios_max" --minutos 40 "${refazer[@]}"
passo "Condenações do TCU" py ingestion.tcu.condenacoes
passo "Conselho de Ética da Câmara" py ingestion.camara.etica
passo "Conselho de Ética do Senado" py ingestion.senado.etica
passo "CPIs e CPMIs" py ingestion.congresso.cpis
passo "Cargos partidários (TSE)" py ingestion.tse.orgaos_partidarios
passo "Curadoria" py ingestion.curadoria
LIMITE=40m passo "Situação dos processos (DataJud)" py ingestion.cnj.datajud
fim

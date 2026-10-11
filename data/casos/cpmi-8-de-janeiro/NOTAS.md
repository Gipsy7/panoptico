# Notas da curadoria: CPMI do 8 de Janeiro (rascunho)

Conferido em 2026-10-11 (uma requisição por vez, User-Agent do projeto): página oficial da comissão e página da 23ª Reunião (HTTP 200).

## Limites encontrados
- **PDF do Relatório Final** (https://legis.senado.leg.br/sdleg-getter/documento?dm=9484688&ts=1697682413143&disposition=inline) e os anexos da reunião (pauta, ata, resultado): todos respondem "Verificação de segurança". Não contornei. Por isso a carga automática não extraiu a seção de indiciamentos (`cpi_indiciamento_sugestao` não tem a CPMI) e **nenhuma pessoa foi ligada**.
- A página da reunião registra "Aprovado o Relatório Final da comissão"; não registra placar nem a lista de indiciados.

## Falta conferir à mão
- Baixar o PDF pelo navegador, ler a seção de indiciamentos e, com `python -m ingestion.congresso.cpi_indiciamentos --pdf arquivo.pdf --cpi congresso:2606`, extrair a fila; ligar só quem estiver na base com vínculo forte e citado no texto aprovado. Ver se há votos em separado (não vencidos): não valem como conclusão da CPMI.
- Encaminhamentos ao MPF/PGR e ao STF e o desfecho de cada um: situação não confirmada em documento oficial para todas as pessoas.
- Os processos do STF sobre os atos de 8 de janeiro (denúncias da PGR, ações penais) são outro conjunto de documentos; só entram aqui se um documento oficial ligar a pessoa a este caso.

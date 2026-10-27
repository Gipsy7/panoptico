# Emendas parlamentares estaduais: levantamento das 27 UFs

Levantamento feito de 21 a 27/10/2026 (DF, GO, PB, PI, RO e SP revistos em 27/10/2026), a partir do Brasil, com o User-Agent do projeto. Para cada UF: onde o governo (ou a Assembleia) publica as emendas de deputados estaduais, em que formato, com que campos e se é possível ler sem truque. Bloqueio deliberado (captcha, 403 proposital, `robots.txt` que veda) não foi contornado; painel sem arquivo não foi raspado. Contexto: desde a ADPF 854 (decisão de 23/10/2025), estados e DF devem seguir o modelo federal de transparência e rastreabilidade a partir do orçamento de 2026; o índice da Transparência Internacional (2025) apontava só AC, DF e MG com divulgação completa, 14 estados sem beneficiário e 17 sem localidade.

Situação: **implementada** (carga no Panóptico), **aberta, não carregada** (arquivo ou API aberta, com o motivo de ainda não estar carregada), **painel** (só visualização, sem arquivo), **bloqueada**, **a verificar** (não achamos a publicação ou ela não abriu). Campos: A = autor, M = município, F = favorecido, P/E/Pg = previsto, empenhado, pago.

| UF | Situação | Onde | Formato | Campos | Período | Observação |
|---|---|---|---|---|---|---|
| SP | aberta, não carregada | transparencia.sp.gov.br/EmendasParlamentares ("Dados Abertos/Emendas/emendas.zip" e "Exportar CSV" de Concedidas) | CSV | A, M (nome), F (nome), E, Pg | 2022-2026 | Linhas de execução sem chave, repetidas (empenho × liquidação): uma emenda tem 44 mil linhas e o empenhado de 2024 somaria bilhões. Sem previsto. Números não fecham: pedido de correção. Conferido de novo em 27/10: o zip foi republicado em 23/10/2026, mas o CSV dentro tem data de 29/05/2026 e a mesma estrutura (238.420 linhas). |
| MG | **implementada** | dados.mg.gov.br/dataset/portal_emendas_estaduais (SEGOV) | CSV (CKAN) | A, M (IBGE), F (nome, CNPJ), P, E, Pg | 2023-2026 | 37.200 indicações. Inclui blocos e bancadas. |
| RJ | painel | transparencia.rj.gov.br/emendas-parlamentares (Qlik); dadosabertos.rj.gov.br só aponta para os painéis | painel | — | 2024- | Pedido. |
| BA | **implementada** (parcial) | dados.ba.gov.br/dataset/emendas-parlamentares (SEFAZ, FIPLAN) | zip de CSV (CKAN) | A, P, E, Pg (sem M e sem F) | 2017-2026 | Sem cidade: só na página do deputado. Cadeia TLS incompleta no servidor (intermediário baixado do endereço do certificado; verificação não desligada). |
| PR | painel | fazenda.pr.gov.br "Consulta de Emendas Parlamentares" (Power BI); TCE-PR "Informação para Todos" | painel | — | — | Pedido. |
| RS | painel | transparencia.rs.gov.br/emendas-parlamentares (Power BI; o FAQ diz que os "dados abertos" são o próprio painel); TCE-RS painel Qlik | painel | — | — | Pedido. |
| PE | **implementada** (parcial) | dados.pe.gov.br/dataset/emendasparlamentaresestaduais (SEPLAG) | CSV (CKAN) | A, M (nome), F, P, E, Pg | 2026 | Arquivos 2012-2025 do mesmo conjunto são empenhos sem autor nem município. |
| CE | painel | cearatransparente.ce.gov.br/portal-da-transparencia/despesas/emendas-parlamentares | página HTML paginada | A, M, valores | — | A API de dados abertos (api-dados-abertos.cearatransparente) não tem emendas. Emendas não impositivas no CE. Pedido. |
| PA | a verificar | transparencia.pa.gov.br (não respondeu em 21 e 27/10); módulo de emendas do SIGPLAN (SEPLAD) | — | — | — | Pedido. |
| SC | **implementada** (parcial) | SC Transferências (CGE/SC) | CSV | A, M, F, P, E, Pg | 2022- | Só convênios e termos de fomento (ver DECISOES, 19/10/2026). |
| GO | **implementada** (parcial, só 2023) | dadosabertos.go.gov.br/dataset/emendas-parlamentares; EmendasGO (sislog.go.gov.br) | CSV/zip por ano (CKAN) | A, M, F (nome, CNPJ), P, E, Pg | 2023 | Só 2023 tem chave, CNPJ e município íntegros (soma conferida com o "Total" do arquivo). 2024 e 2025 (até julho): empenho, processo e CNPJ em notação científica ("2,02419E+15"; o empenho tem 5 valores distintos em 2.594 linhas) e o de 2025 repete o empenho por parcela sem chave; 2021-2022 sem município e com posição de execução de 2022/2023; 2019-2020 sem execução. A consulta EmendasGO exige captcha (não contornado). Pedido dos arquivos corrigidos. |
| MA | **implementada** (parcial) | transparencia.ma.gov.br/app/v2/emendasestaduais ("Exportar CSV") | CSV | A, M, F (nome, CNPJ), P, E, Pg | 2026 | O filtro de ano só oferece 2026. |
| AM | a verificar | transparencia.am.gov.br/emendas-parlamentares → sistemas.sefaz.am.gov.br/transparencia (aplicação; dados abertos /dadosabertos/emenda) | — | — | — | O portal carrega reCAPTCHA; a aplicação não entregou dados sem navegador. Pedido. |
| ES | **implementada** | dados.es.gov.br, "[Portal da Transparência] Emendas Parlamentares do Estado" (SEFAZ) | CSV por ano (CKAN) | A, M (IBGE 6 díg.), F (nome, CNPJ), P, E, Pg | 2021-2026 | Linhas repetidas com outro nome de ação em 2023 e 2025 (tratadas). |
| PB | **implementada** (parcial) | API de dados abertos (api.dados.pb.gov.br, `/orcamento/execucao_emendas`), a mesma base de transparencia.pb.gov.br/emendas-parlamentares | JSON | A, P, E, Pg (sem M e sem F) | 2021-2026 | Sem cidade nem favorecido estruturados: só na página do deputado. O proxy da página (`/api/execucao-emendas`) responde 403 à leitura automática e não é usado. |
| RN | painel | transparencia.rn.gov.br/emendas-estado (Power BI); API SIPAC sem emendas | painel | — | — | Pedido. |
| MT | a verificar | transparencia.mt.gov.br (rota de emendas 404, página com captcha) | — | — | — | Pedido. |
| AL | **implementada** (parcial) | transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais (JSON `/despesa/json-emendas-parlamentares/`) | JSON | A, M, F (nome), P, E, Pg | 2026 | Só 2026 na consulta. |
| PI | aberta, não carregada | api.transparencia.pi.gov.br (`/api/v1/emendas-estaduais/2025-e-anteriores/{ano}/` e `/emendas-estaduais/{ano}/`) | JSON | 2021-2025: A, F (credor no texto), E, Pg por nota de empenho, sem previsto; 2026: A, M (localidade), F, P | 2021-2026 | Duas séries que não se juntam: até 2025 sem valor da emenda; 2026 com a execução só no detalhe de cada emenda, lançada à mão (com contas bancárias). Pedido de série única. |
| DF | **implementada** (parcial) | transparencia.df.gov.br (API `/api/despesa/emendas-parlamentares`, cabeçalho `x-client-id` que a página sorteia); painel da CLDF (Siggo) | JSON | A, P (autorizado), E, Pg; sem F; M = Brasília | 2016-2026 | Uma linha por autor e programa de trabalho. A região administrativa só no nome do subtítulo. Emendas de vários autores juntos ficam como coletivas. |
| MS | a verificar | transparencia.ms.gov.br (aplicação; emendas não localizadas) | — | — | — | Citado como portal completo em petição ao STF; não achamos o caminho. Pedido. |
| SE | **implementada** (parcial) | transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais (API `api.transparencia.se.gov.br/api/emendas-estaduais`) | JSON | A, M, F (executor, CNPJ), P, Pg (sem E) | 2022-2025 | Sem número da emenda nem empenhado. |
| RO | aberta, não carregada | transparencia.ro.gov.br/emenda (POST `/Emenda/Filtrar`, token antifalsificação lido da página, sem captcha) | JSON | A, M (localidade), F, P, E, Pg | 2023-2026 | Empenhado, liquidado e pago zerados em 2023-2025 (R$ 0 pago de R$ 489 mi previstos em 2025) em empenhos com número emitido; base "atualizada em 25/03/2026". Números não fecham: pedido de correção. Traz conta bancária (não seria lida). |
| TO | a verificar | transparencia.to.gov.br (aplicação; emendas não localizadas) | — | — | — | Pedido. |
| AC | **implementada** | seplan.ac.gov.br/.../emendas-parlamentares-estaduais (planilha publicada em CSV) | CSV | A, M, F (nome, CNPJ), P, E, Pg | 2023-2026 | A planilha traz conta bancária do beneficiário: não guardada. |
| AP | a verificar | transparencia.ap.gov.br ("Emendas Parlamentares Federais e Estaduais", rota não encontrada) | — | — | — | Pedido. |
| RR | a verificar | transparencia.rr.gov.br (aplicação; emendas não localizadas) | — | — | — | Pedido. |

## Totais pagos carregados no acervo (27/10/2026)

Soma literal do campo "pago" de cada fonte, por ano da emenda (R$). A esfera estadual nunca se soma às emendas federais.

| UF | até 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| MG | — | — | 1.152.536.915,75 | 1.627.138.593,00 | 2.123.963.559,26 | 68.708.173,28 |
| BA | 104.933.771,59 (2017-2021) | 42.384.363,87 | 96.764.747,83 | 310.307.542,13 | 415.903.981,35 | 323.913.944,47 |
| PE | — | — | — | — | — | 102.120.942,90 |
| SC | — | 50.280.148,63 | 52.771.003,85 | 80.672.883,35 | 97.885.249,09 | 17.421.545,04 |
| MA | — | — | — | — | — | 337.444.987,70 |
| ES | 17.037.550,89 (2021) | 22.813.410,86 | 28.372.234,63 | 45.278.741,30 | 64.517.152,50 | 104.567.705,67 |
| AL | — | — | — | — | — | 184.560.128,18 |
| SE | — | 33.634.901,00 | 39.221.972,00 | 55.606.290,00 | 33.824.000,00 | — |
| AC | — | — | 44.462.136,75 | 69.500.263,03 | 90.043.920,61 | 55.823.646,40 |

2026 é o ano em curso (pago até a data da carga). Tabela `emenda_estadual` no acervo: 62.752 linhas, 37 MB.

Já sem as linhas repetidas pela exportação (ES 2023 e 2025, PE 2026; ver `docs/DECISOES.md`, 27/10/2026).

## Ordem para o que falta

1. **SP**: pedir a correção do arquivo (uma linha por emenda ou por evento com chave) e carregar quando fechar.
2. **GO**: pedir os arquivos de 2024 e 2025 sem notação científica e atualizados; quando vierem, ampliar `go.py` (hoje só 2023).
3. **RO**: pedir a correção da execução (empenhado e pago zerados em 2023-2025); a leitura já está mapeada (ver `docs/FONTES_DE_DADOS.md`).
4. **PI**: pedir uma série única com valor da emenda e execução contábil; com ela, adaptador sobre a API pública.
5. **DF, PB, BA**: pedir município e favorecido em campo próprio.
6. Painéis (**RJ, PR, RS, RN, CE**) e não localizados (**PA, AM, MT, MS, TO, AP, RR**): pedido (`docs/pedidos/emendas_estaduais_27_ufs.md`, tabela de controle preenchida).

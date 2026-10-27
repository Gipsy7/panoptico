# Emendas parlamentares estaduais: levantamento das 27 UFs

Levantamento feito de 21 a 27/10/2026, a partir do Brasil, com o User-Agent do projeto. Para cada UF: onde o governo (ou a Assembleia) publica as emendas de deputados estaduais, em que formato, com que campos e se é possível ler sem truque. Bloqueio deliberado (captcha, 403 proposital, `robots.txt` que veda) não foi contornado; painel sem arquivo não foi raspado. Contexto: desde a ADPF 854 (decisão de 23/10/2025), estados e DF devem seguir o modelo federal de transparência e rastreabilidade a partir do orçamento de 2026; o índice da Transparência Internacional (2025) apontava só AC, DF e MG com divulgação completa, 14 estados sem beneficiário e 17 sem localidade.

Situação: **implementada** (carga no Panóptico), **aberta, não carregada** (arquivo ou API aberta, com o motivo de ainda não estar carregada), **painel** (só visualização, sem arquivo), **bloqueada**, **a verificar** (não achamos a publicação ou ela não abriu). Campos: A = autor, M = município, F = favorecido, P/E/Pg = previsto, empenhado, pago.

| UF | Situação | Onde | Formato | Campos | Período | Observação |
|---|---|---|---|---|---|---|
| SP | aberta, não carregada | transparencia.sp.gov.br/EmendasParlamentares ("Dados Abertos/Emendas/emendas.zip" e "Exportar CSV" de Concedidas) | CSV | A, M (nome), F (nome), E, Pg | 2022-2026 | Linhas de execução sem chave, repetidas (empenho × liquidação): uma emenda tem 25 mil linhas e o empenhado de 2024 somaria R$ 12 bi. Sem previsto. Números não fecham: pedido de correção. **Prioridade 1.** |
| MG | **implementada** | dados.mg.gov.br/dataset/portal_emendas_estaduais (SEGOV) | CSV (CKAN) | A, M (IBGE), F (nome, CNPJ), P, E, Pg | 2023-2026 | 37.200 indicações. Inclui blocos e bancadas. |
| RJ | painel | transparencia.rj.gov.br/emendas-parlamentares (Qlik); dadosabertos.rj.gov.br só aponta para os painéis | painel | — | 2024- | Pedido. |
| BA | **implementada** (parcial) | dados.ba.gov.br/dataset/emendas-parlamentares (SEFAZ, FIPLAN) | zip de CSV (CKAN) | A, P, E, Pg (sem M e sem F) | 2017-2026 | Sem cidade: só na página do deputado. Cadeia TLS incompleta no servidor (intermediário baixado do endereço do certificado; verificação não desligada). |
| PR | painel | fazenda.pr.gov.br "Consulta de Emendas Parlamentares" (Power BI); TCE-PR "Informação para Todos" | painel | — | — | Pedido. |
| RS | painel | transparencia.rs.gov.br/emendas-parlamentares (Power BI; o FAQ diz que os "dados abertos" são o próprio painel); TCE-RS painel Qlik | painel | — | — | Pedido. |
| PE | **implementada** (parcial) | dados.pe.gov.br/dataset/emendasparlamentaresestaduais (SEPLAG) | CSV (CKAN) | A, M (nome), F, P, E, Pg | 2026 | Arquivos 2012-2025 do mesmo conjunto são empenhos sem autor nem município. |
| CE | painel | cearatransparente.ce.gov.br/portal-da-transparencia/despesas/emendas-parlamentares | página HTML paginada | A, M, valores | — | A API de dados abertos (api-dados-abertos.cearatransparente) não tem emendas. Emendas não impositivas no CE. Pedido. |
| PA | a verificar | transparencia.pa.gov.br (não respondeu em 21 e 27/10); módulo de emendas do SIGPLAN (SEPLAD) | — | — | — | Pedido. |
| SC | **implementada** (parcial) | SC Transferências (CGE/SC) | CSV | A, M, F, P, E, Pg | 2022- | Só convênios e termos de fomento (ver DECISOES, 19/10/2026). |
| GO | aberta, não carregada | dadosabertos.go.gov.br/dataset/emendas-parlamentares; EmendasGO (sislog.go.gov.br) | CSV/zip por ano (CKAN) | A, M, F, E, Pg | 2020-jul/2025 | Exportação de planilha: CNPJ e nº de empenho em notação científica ("3,76E+13"), delimitador muda entre anos, só até julho de 2025. A consulta EmendasGO exige captcha (bloqueio, não contornado). Pedido do arquivo corrigido. **Prioridade 2.** |
| MA | **implementada** (parcial) | transparencia.ma.gov.br/app/v2/emendasestaduais ("Exportar CSV") | CSV | A, M, F (nome, CNPJ), P, E, Pg | 2026 | O filtro de ano só oferece 2026. |
| AM | a verificar | transparencia.am.gov.br/emendas-parlamentares → sistemas.sefaz.am.gov.br/transparencia (aplicação; dados abertos /dadosabertos/emenda) | — | — | — | O portal carrega reCAPTCHA; a aplicação não entregou dados sem navegador. Pedido. |
| ES | **implementada** | dados.es.gov.br, "[Portal da Transparência] Emendas Parlamentares do Estado" (SEFAZ) | CSV por ano (CKAN) | A, M (IBGE 6 díg.), F (nome, CNPJ), P, E, Pg | 2021-2026 | Linhas repetidas com outro nome de ação em 2023 e 2025 (tratadas). |
| PB | a verificar | transparencia.pb.gov.br/emendas-parlamentares ("Execução de emendas parlamentares impositivas", aplicação) | — | — | — | Aplicação de página única; API não identificada. **Prioridade 4.** |
| RN | painel | transparencia.rn.gov.br/emendas-estado (Power BI); API SIPAC sem emendas | painel | — | — | Pedido. |
| MT | a verificar | transparencia.mt.gov.br (rota de emendas 404, página com captcha) | — | — | — | Pedido. |
| AL | **implementada** (parcial) | transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais (JSON `/despesa/json-emendas-parlamentares/`) | JSON | A, M, F (nome), P, E, Pg | 2026 | Só 2026 na consulta. |
| PI | a verificar | transparencia.pi.gov.br (aplicação; as despesas têm marcação de emenda parlamentar) | — | — | — | **Prioridade 4.** |
| DF | aberta, não carregada | transparencia.df.gov.br (aplicação com API `/despesa/emendas-parlamentares/*`: por autor, notas de empenho, lançamento e ordem bancária); painel da CLDF (Siggo) | JSON | A, valores por empenho | — | Implementável. **Prioridade 3.** |
| MS | a verificar | transparencia.ms.gov.br (aplicação; emendas não localizadas) | — | — | — | Citado como portal completo em petição ao STF; não achamos o caminho. Pedido. |
| SE | **implementada** (parcial) | transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais (API `api.transparencia.se.gov.br/api/emendas-estaduais`) | JSON | A, M, F (executor, CNPJ), P, Pg (sem E) | 2022-2025 | Sem número da emenda nem empenhado. |
| RO | aberta, não carregada | transparencia.ro.gov.br/emenda (consulta com JSON, formulário com token antifalsificação) | JSON | A, M (localidade), F, P, E, Pg | — | Implementável (consulta por exercício). **Prioridade 3.** |
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
2. **GO**: pedir o arquivo sem notação científica e atualizado; avaliar carga parcial 2020-jul/2025.
3. **DF** e **RO**: APIs/consultas abertas; implementar.
4. **PB** e **PI**: identificar a API das aplicações; se não houver, pedido.
5. Painéis (**RJ, PR, RS, RN, CE**) e não localizados (**PA, AM, MT, MS, TO, AP, RR**): pedido (`docs/pedidos/emendas_estaduais_27_ufs.md`, tabela de controle preenchida).

# Fontes de dados

Endpoints conferidos em 2026-10-06.

## Câmara dos Deputados: deputados em exercício

- **URL:** `GET https://dadosabertos.camara.leg.br/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=nome`
- **Formato:** JSON `{dados: [...], links: [{rel, href}]}`. Paginado: seguir o link `rel="next"`.
- **Campos usados:** `id`, `nome`, `siglaPartido`, `siglaUf`, `urlFoto`, `email`.
- **Sem parâmetros**, a API retorna só quem está em exercício.
- **Perfil público:** `https://www.camara.leg.br/deputados/{id}`
- **Telefone e nome civil** só existem no detalhe (`/deputados/{id}`). Ficam para a Fase 4.
- **Frequência sugerida:** diária.

## Senado Federal: senadores em exercício

- **URL:** `GET https://legis.senado.leg.br/dadosabertos/senador/lista/atual` com `Accept: application/json`
- **Formato:** `ListaParlamentarEmExercicio.Parlamentares.Parlamentar[].IdentificacaoParlamentar`
- **Campos usados:** `CodigoParlamentar`, `NomeParlamentar`, `NomeCompletoParlamentar`, `SiglaPartidoParlamentar`, `UfParlamentar`, `UrlFotoParlamentar`, `UrlPaginaParlamentar`, `EmailParlamentar`, `Telefones.Telefone[].NumeroTelefone`.
- **Atenção:** listas com um só item podem vir como objeto em vez de array. Normalizar.
- **Frequência sugerida:** diária.

## ViaCEP

- **URL:** `GET https://viacep.com.br/ws/{cep8}/json/`
- **Campos usados:** `uf`, `localidade`, `ibge` (código do município).
- **CEP inexistente:** retorna `{"erro": "true"}` (string). CEP mal formado retorna HTTP 400.

## Câmara: gastos da cota parlamentar (CEAP)

- **URL:** `GET https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip` (CSV `;`, UTF-8 com BOM)
- **Use o CSV, não o JSON:** só o CSV traz `ideCadastro`, que é o id do deputado na API. O `numeroDeputadoID`/`nuDeputadoId` é outro identificador.
- **Campos usados:** `ideCadastro`, `numMes`, `txtDescricao`, `txtFornecedor`, `txtCNPJCPF`, `vlrLiquido` (pode ser negativo: restituição), `datEmissao`, `urlDocumento`, `ideDocumento`.
- Linhas sem `ideCadastro` são lideranças e órgãos (ignoradas).
- **Atualização:** diária, e o ano inteiro muda retroativamente. Recarregamos o ano todo.

## Senado: gastos da cota parlamentar (CEAPS)

- **URL:** `GET https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}` (JSON, lista)
- **Campos usados:** `codSenador`, `mes`, `tipoDespesa` (pode vir nulo), `fornecedor`, `cpfCnpj`, `valorReembolsado`, `data`, `id`.
- Não há link para o comprovante por despesa.

## Câmara: projetos de lei e autores

- **URLs:** `https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv` e `.../proposicoesAutores/csv/proposicoesAutores-{ano}.csv` (50 MB e 40 MB por ano)
- O arquivo de cada ano traz as proposições apresentadas naquele ano, com `ultimoStatus_descricaoSituacao`.
- **Autores:** `codTipoAutor = 10000` é deputado. `ordemAssinatura = 1` é o autor principal.
- **Atualização:** diária, todos os anos. O bruto é gravado em `.csv.gz`.
- **Página pública:** `https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}`

## Senado: projetos de lei por senador

- **URL:** `GET https://legis.senado.leg.br/dadosabertos/processo?codigoParlamentarAutor={codigo}` (JSON)
- **Campos usados:** `identificacao` ("PL 2036/2023"), `codigoMateria`, `casaIdentificadora` (só `SF`), `dataApresentacao`, `ementa`, `situacaoAtual`, `autoria`.
- **Autor principal:** o primeiro nome em `autoria`. Os demais são coautores (PECs exigem 27 assinaturas).
- **Página pública:** `https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigoMateria}`

## Câmara: votações nominais do Plenário

- **URLs:** `https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv` e `.../votacoesVotos/csv/votacoesVotos-{ano}.csv`
- Filtro: `siglaOrgao = PLEN` e votação com votos registrados (as simbólicas não têm).
- O arquivo de votos **só lista quem votou**. Não há registro de ausência nem de justificativa.
- Códigos de voto: Sim, Não, Abstenção, Obstrução, "Artigo 17" (presidente da sessão) e vazio.
- Também `votacoesProposicoes-{ano}.csv` (liga a votação à proposição; quando há duas, uma é REQ/REC sobre a outra, e usamos a principal) e `votacoesOrientacoes-{ano}.csv` (orientação por bancada). Os blocos vêm com nome truncado ("Bl UniPpPsd..."), então só guardamos Governo, Maioria, Minoria e Oposição.
- O arquivo de votos traz `deputado_siglaPartido` no dia da votação.
- Os quatro CSVs são gravados juntos num `.zip` bruto.

## Câmara: temas das proposições

- **URLs:** `https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/csv/proposicoesTemas-{ano}.csv` (~5 MB/ano) e, para matérias votadas de anos antigos, `GET /api/v2/proposicoes/{id}/temas`.
- 32 temas oficiais (`/referencias/proposicoes/codTema`), entre eles "Homenagens e Datas Comemorativas". Uma proposição pode ter mais de um tema.

## Câmara: representações no Conselho de Ética

- **API:** `GET /api/v2/proposicoes?siglaTipo=REP&ano={ano}&itens=100` (cabeçalho `x-total-count`; 29 em 2023, 5 em 2024, 28 em 2025, 10 em 2026 até outubro) e o detalhe em `/api/v2/proposicoes/{id}` (`statusProposicao`: `descricaoSituacao`, `descricaoTramitacao`, `dataHora`, `despacho`).
- **Não há campo com o deputado representado:** ele só aparece na ementa, às vezes em maiúsculas ("Deputado DELEGADO RAMAGEM"), às vezes não ("Deputado Gilvan da Federal"), às vezes pelo nome civil completo ("ANDRÉ LUIS GASPAR JANONES"), às vezes em lista ("Deputadas CÉLIA NUNES CORREA, ÉRIKA JUCÁ KOKAY…").
- **Link público:** `https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}`.

## Câmara: detalhe do deputado

- **URL:** `GET https://dadosabertos.camara.leg.br/api/v2/deputados/{id}` (513 chamadas, 8 em paralelo)
- Usado para `nomeCivil`, `ultimoStatus.gabinete.telefone` e `ultimoStatus.data` (início do exercício atual: posse, posse de suplente ou retorno).

## Senado: votações nominais do Plenário

- **URL:** `GET https://legis.senado.leg.br/dadosabertos/votacao?dataInicio={ano}-01-01&dataFim={ano}-12-31`
- Cada votação lista **todos os senadores** com `siglaVotoParlamentar`: Sim, Não, Abstenção, Votou (secreta), Presidente (art. 51 RISF), P-NRV (presente, não registrou voto), AP (atividade parlamentar), LS (licença saúde), MIS (missão), LP (licença particular), LAP (licença paternidade), NCom (não compareceu), NA (dispositivo não citado, fora da conta).
- O início do exercício atual vem de `Mandato.Exercicios.Exercicio[]` (o que não tem `DataFim`) na lista de senadores.

## Senado: temas e orientação das lideranças

- **Temas:** `GET /dadosabertos/processo?codigoMateria={codigo}` (para obter o `id` do processo) e `GET /dadosabertos/processo/{id}` → `classificacoes[].descricaoHierarquia` ("Política Social / Educação / Educação Básica"). A API devolve **429** se houver muitas chamadas em paralelo.
- **Orientações:** `GET /dadosabertos/plenario/votacao/orientacaoBancada/{AAAAMMDD}` → `votacoes[].orientacoesLideranca[]` com `partido` ("Governo", "Maioria", "Minoria", "Oposição" ou o nome do partido) e `voto` (SIM, NÃO, LIVRE). Liga com a API de votações pelo `sequencialVotacao` do mesmo dia. O `codigoVotacaoSve` é outro identificador e não casa com o `codigoSessaoVotacao`.

## Portal da Transparência: emendas parlamentares

- **URL (lote, sem chave):** `https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO` (zip de ~32 MB com três CSVs em latin-1, separador `;`)
- `EmendasParlamentares.csv`: uma linha por emenda × localidade × ação. O **código da emenda se repete**. Localidade com código IBGE só em ~16% das linhas; o resto é "MÚLTIPLO", UF ou "Nacional".
- `EmendasParlamentares_PorFavorecido.csv` (~180 MB): quem recebeu, com natureza jurídica, UF e **nome** do município (sem código IBGE). Há linhas com código da emenda "Sem informação".
- Autor: código do sistema de orçamento + nome em maiúsculas. Não há id da Câmara ou do Senado.
- A API (`api.portaldatransparencia.gov.br`, exige chave em `PORTAL_TRANSPARENCIA_CHAVE`) pagina de 15 em 15. Por isso usamos o lote.
- **Remuneração:** a API de remuneração do Portal cobre servidores do Executivo, não parlamentares. O subsídio vem do Decreto Legislativo 172/2022.

## IBGE: municípios

- **URL:** `GET https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado` (5.571 municípios)
- Usado para ligar o município do favorecido (nome + UF) ao código IBGE, o mesmo que o ViaCEP devolve.

## TSE: candidaturas, bens e contas de campanha

- **URLs (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/` + `consulta_cand/consulta_cand_{ano}.zip`, `bem_candidato/bem_candidato_{ano}.zip` e `prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip`. Os dados ficam catalogados em `dadosabertos.tse.jus.br`.
- **Formato:** zip com um CSV por UF (`;`, latin-1, decimal com vírgula). O arquivo `_BRASIL` junta todos os estados e fica de fora, para não contar em dobro. O `_BR` traz os candidatos a presidente.
- **Turnos:** quem disputou o segundo turno aparece duas vezes em `consulta_cand`. Fica a linha do último turno.
- **CPF:** presente em 2018 e 2022. Em 2024, vem mascarado (`-4`) em todas as linhas, então as candidaturas municipais não se ligam aos parlamentares pelo CPF.
- **Ligação aos parlamentares:**
  - deputados: pelo CPF do detalhe do deputado na API da Câmara (a planilha `deputados.csv` traz o CPF vazio para muitos);
  - senadores: o Senado não publica CPF, então a ligação é por nome civil + UF entre candidatos a senador ou suplente, só quando é exata e única. Os 82 casaram.
- **Contas:** 300 MB em 2018, 475 MB em 2022 e 1,3 GB em 2024. Baixadas em fluxo para o disco. Usamos `receitas_candidatos_*` (`DS_FONTE_RECEITA` separa fundo eleitoral e fundo partidário; `DS_ORIGEM_RECEITA` dá a origem) e `despesas_contratadas_candidatos_*` (`DS_ORIGEM_DESPESA`).
- **Fotos:** a URL de fotos do DivulgaCandContas recusa acesso automatizado (403), mas os zips por UF em `cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_{UF}_div.zip` funcionam. O arquivo se chama `F{UF}{SQ}_div.jpg`. Os federais usam as fotos da Câmara e do Senado.
- **Frequência:** só muda quando há eleição. Carga manual pelo workflow "Ingestão TSE".
- **Situação da candidatura em 2024:** `DS_SITUACAO_CANDIDATURA` vem `#NE` (não existe) em todas as linhas, e não há coluna de detalhe da situação. A cassação e o indeferimento vêm do arquivo de motivos (abaixo).
- **Data da eleição:** `DT_ELEICAO` é a data do turno da linha. Como fica a linha do último turno, é a data do turno que definiu o resultado (`candidatura.data_eleicao`).

## TSE: cassações e julgamentos de candidatura (motivo_cassacao)

- **URL (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/motivo_cassacao/motivo_cassacao_{ano}.zip`. É pequeno: 160–760 KB por eleição. Existe para 2018, 2020, 2022 e 2024 e é regenerado com frequência (`DT_GERACAO`; o de 2024 foi gerado em 08/10/2026).
- **Formato:** o mesmo dos outros arquivos do TSE (um CSV por UF + `_BRASIL`, `;`, latin-1). Campos usados: `ANO_ELEICAO`, `SQ_CANDIDATO`, `NR_PROCESSO` (número único do CNJ, 20 dígitos, sempre preenchido), `DS_TP_MOTIVO`, `DS_MOTIVO` e `DT_GERACAO`.
- **Uma linha por fundamento:** a mesma candidatura e o mesmo processo se repetem com cada fundamento ("Abuso de poder econômico", "Abuso de poder político"). Agrupamos por candidatura, processo e tipo.
- **Dois tipos em `DS_TP_MOTIVO`:**
  - "Fundamentos legais de cassação": cassação do registro ou do diploma (abuso de poder, compra de voto, fraude à cota de gênero, conduta vedada…);
  - "Fundamentos legais de julgamento": julgamento sobre o registro (ausência de condição de elegibilidade, inelegibilidade, falta de quitação eleitoral, partido ou coligação indeferidos…).
  - Em 2022, todas as linhas são do segundo tipo, inclusive "Abuso de poder político". Por isso o texto do site repete "julgamento" e não afirma indeferimento.
- **Conferência (base local):** dos 23 eventos ligados a pessoas que temos, os de 2022 são Deltan Dallagnol (PR, Ficha limpa, processo 0601407-70.2022.6.16.0000) e Carla Zambelli (SP, abuso de poder político e uso indevido de meios de comunicação, 0601390-55.2022.6.26.0000), coerentes com os julgamentos noticiados.
- **Cobre todos os candidatos, não só eleitos.** Em 2024 são 12.088 linhas e 10.705 candidaturas, a maioria de não eleitos. Pela coleta mínima, guardamos só as candidaturas de pessoas que já temos (eleitos e parlamentares).
- **Não traz a data da decisão nem se cabe recurso.** O evento diz o que o TSE registra, com a data de geração do arquivo, e fica sem data na linha do tempo.
- **Número do processo:** conferido pelo dígito verificador (módulo 97) e formatado como `NNNNNNN-DD.AAAA.J.TR.OOOO`. O `J` = 6 indica a Justiça Eleitoral, e o `TR` o tribunal regional.

## TSE: órgãos partidários

- **URL (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/orgao_partidario/orgao_partidario.zip` (219 MB; um CSV por partido, 40 arquivos, o do MDB com 317 MB aberto). No catálogo do TSE (`dadosabertos.tse.jus.br`, conjunto "delegados-partidarios") estão também `delegado_partidario.zip` e `perfil_filiacao_partidaria.zip` (só estatística).
- **Uma linha por membro e cargo:** partido, tipo do órgão (definitivo, provisório), abrangência (municipal, estadual, nacional), município e UF, cargo (`DS_CARGO_MEMBRO`), nome, **título de eleitor** (`NR_TITULO_ELEITORAL_MEMBRO`; às vezes `#NULO`), início e fim do exercício, situação do membro e do órgão (`VIGENTE` / `NÃO VIGENTE`).
- **Armadilhas:** datas com o ano truncado ("16/03/0208", "07/06/0011"); telefones `-1` e e-mails `#NULO`; o arquivo tem o histórico inteiro, então é preciso filtrar pelo que está vigente.
- **Catálogo do TSE:** a API CKAN (`/api/3/action/package_list`) lista 184 conjuntos. A busca `package_search` não devolve nada; use `package_list` e `package_show`.

## CGU: sanções (CEIS, CNEP e CEAF)

- **URL (lote diário, sem chave):** `https://portaldatransparencia.gov.br/download-de-dados/{ceis|cnep|ceaf}/{AAAAMMDD}`, que redireciona para `dadosabertos-download.cgu.gov.br/.../{AAAAMMDD}_{CEIS|CNEP|CEAF}.zip`. Também há `cepim` e `acordos-leniencia` (só empresas e entidades; catalogados, sem coleta).
- **Tamanho (08/10/2026):** CEIS 3,4 MB (23.721 sanções, 9.092 a pessoas físicas), CNEP 0,2 MB (1.827; 28 a pessoas físicas), CEAF 0,5 MB (4.066 expulsões).
- **Formato:** um CSV por zip, `;`, latin-1. Colunas com acento ("CÓDIGO DA SANÇÃO", "NÚMERO DO PROCESSO"...); CEIS e CNEP com as mesmas colunas (o CNEP tem "VALOR DA MULTA"); o CEAF tem cargo e órgão de lotação. "Sem Informação" significa vazio.
- **CPF:** completo no CEIS e no CNEP (pessoa física, `TIPO DE PESSOA` = F); mascarado no CEAF (`***.918.517-**`).
- **Origem:** 7.075 das 9.092 sanções a pessoas físicas no CEIS vêm do CNJ: são condenações por improbidade (Lei 8.429), registradas como "Impedimento/proibição de contratar".
- **Fundamentação legal:** texto longo de cada norma, vários itens separados por `;` ou `;;`. Guardamos só "norma - artigo" de cada item.
- **Número do processo:** pode ser número único do CNJ (formatado) ou número de processo administrativo (ex.: `10768.000360/2014-05`), guardado como veio.
- **Páginas de detalhe** (`/sancoes/ceis/{código}`) recusam acesso automático (405). O link da fonte é a página de download do cadastro, e o código da sanção vai no texto.

## TCU: contas julgadas irregulares e inabilitados

- **Contas julgadas irregulares:** a lista pública de responsáveis (a mesma da emissão de certidões), obtida pela API do aplicativo de certidões. A busca na web não achou um conjunto de dados aberto para essa lista.
  - Chamada: `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-contas-irregulares-com-paginacao?paginaAtual={n}&tamanhoPagina=1000`, com corpo `{}`.
  - Sem chave e sem CAPTCHA (as certidões individuais têm CAPTCHA, e não as usamos).
  - Volume: 47.963 registros de 28.549 responsáveis, em 48 páginas, menos de 1 s cada.
  - Campos: número do processo (TC), nome, tipo e número do registro (**CPF completo** ou CNPJ), município e UF, data do trânsito em julgado, acórdão (`4206/2023-2C`; PL = Plenário, 1C e 2C = Câmaras) e link oficial para a deliberação (`linkDeliberacoesProcesso`).
- **Inabilitados para cargo em comissão ou função de confiança:** `GET https://contas.tcu.gov.br/ords/condenacao/consulta/inabilitados?limit=500&offset={n}` (Oracle ORDS, no máximo 500 por página, `hasMore` diz se há mais). CPF completo, processo, deliberação (`AC-000738/2022-PL`), trânsito em julgado e data final.
- **Inidôneos para licitar** (`.../consulta/inidoneos`): 94, todos empresas. Catalogados, sem coleta.
- O catálogo do ORDS (`/ords/condenacao/metadata-catalog/`) lista só essas rotas.
- **Escopo da lista**, segundo o TCU: não inclui processos arquivados por decisão terminativa, responsáveis ainda não notificados, decisões não transitadas em julgado, transitadas há mais de 20 anos, anuladas ou suspensas.
- **Bruto:** as duas listas num JSON comprimido, 2,7 MB.

## CNJ: DataJud (situação de processos)

- **API pública:** `POST https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search` (Elasticsearch), com o cabeçalho `Authorization: APIKey {chave}`. A chave é pública, publicada em `https://datajud-wiki.cnj.jus.br/api-publica/acesso/` e trocada de tempos em tempos. A lista de tribunais (91 índices) está em `.../api-publica/endpoints/`: STJ, TSE, TST, STM, TRFs, TJs, TREs, TRTs e TJMs. **O STF não está.**
- **Consulta:** só por número, sem pontuação (`{"query": {"terms": {"numeroProcesso": [...]}}}`, até 50 por chamada). Não busca por nome de parte.
- **Tribunal pelo número único:** segmento `J` (3 = STJ, 4 = Federal, 6 = Eleitoral, 8 = Estadual) e `TR`. Na Estadual e na Eleitoral, `TR` segue a ordem das UFs da Resolução CNJ 65/2008 (01 AC … 14 PA … 26 SP, 27 TO); `TR` 00 na Eleitoral é o TSE. O DF tem índices próprios (`tjdft`, `tre-dft`).
- **Campos usados:** `classe.nome`, `orgaoJulgador.nome`, `dataAjuizamento` (`AAAAMMDDhhmmss`), `nivelSigilo`, `movimentos[]` (`dataHora`, `nome`) e `dataHoraUltimaAtualizacao`. O mesmo processo pode aparecer uma vez por grau (G1, G2): fica o atualizado por último.
- **Instabilidade:** alguns índices respondem 504 de vez em quando. A carga tenta de novo e deixa os números do tribunal para a próxima.

## Tesouro Nacional: SICONFI (contas anuais dos municípios)

- **API:** `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio={ano}&no_anexo={anexo}&id_ente={ibge}`. Exige `id_ente`: não há consulta em lote, então é uma por município, anexo e ano (cerca de 0,8 s cada, a partir do Brasil).
- **Anexos usados:** `DCA-Anexo I-C` (receitas; `cod_conta = TotalReceitas`, coluna "Receitas Brutas Realizadas") e `DCA-Anexo I-E` (despesa por função; coluna "Despesas Pagas", só as linhas de função no formato "10 - Saúde").
- **Armadilhas:**
  - o código `TotalDespesas` se repete em várias linhas, por isso o total é a soma das funções;
  - texto em UTF-8 com alguns caracteres quebrados;
  - nem todo município entrega: em 2024, 5.326 de 5.571 tinham declaração;
  - a API limita a taxa de consultas (responde 429; cerca de 1 em cada 5 consultas a partir do GitHub). A carga espera o tempo do `Retry-After` e tenta de novo; um ano completo leva uns 65 minutos.
- **Frequência:** anual, entregue até abril. Carga mensal.

## TCE-SP: despesas das prefeituras e câmaras paulistas

- **URL (lote, sem chave):** `https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ano}.zip`. Em 2024 o arquivo é um CSV de 15 GB descompactado; o zip de 2025 tem 2,1 GB.
- **Formato:** `;`, latin-1, decimal com vírgula. Uma linha por evento de despesa: `tp_despesa` = Empenhado, Valor Liquidado, Valor Pago, Anulação ou Reforço. Usamos só "Valor Pago".
- **Campos:**
  - `codigo_municipio_ibge` e `ds_orgao` (prefeitura, câmara, autarquias e fundos);
  - `tp_identificador_despesa` (CNPJ, pessoa física ou especial) e `nr_identificador_despesa`;
  - `ds_despesa` (nome do credor) e `vl_despesa`.
- **Armadilhas:**
  - a pessoa física vem com nome: somamos sem guardar o nome;
  - o órgão é texto livre, e classificamos por "CÂMARA" e "PREFEITURA";
  - o ano corrente só sai no ano seguinte;
  - a capital não está no arquivo: é fiscalizada pelo TCM-SP;
  - a folha de salários aparece como pagamento ao próprio órgão ("CAMARA MUNICIPAL DE CAMPINAS") ou a um credor "FOLHA DE PAGAMENTO", e vira uma linha "Folha de pagamento (salários)".
- **Outros TCEs:** RS (`dados.tce.rs.gov.br`) e MG (`dadosabertos.tce.mg.gov.br`) têm portais de dados abertos; a examinar.
- **Portais de fornecedores (Betha, CR2...):** não servem para carga automática. O Betha exige reCAPTCHA nas consultas, e o CR2 é um app sem API pública. Não contornamos captcha.

## SAPL (Interlegis): câmaras municipais e assembleias

- **Endereço:** em geral `https://sapl.{câmara}/api/`, vindo do catálogo de canais (tipo `sapl`). É a mesma API REST em todas as câmaras (Django REST, paginada; `page_size` até 100).
- **Rotas usadas:**
  - `parlamentares/legislatura/`, `parlamentares/mandato/?legislatura={id}`, `parlamentares/parlamentar/{id}/`, `parlamentares/filiacao/` e `parlamentares/partido/`;
  - `base/tipoautor/` e `base/autor/?tipo={id do tipo "Parlamentar"}` (o id muda de uma instalação para outra);
  - `materia/autoria/?autor={id}&o=-id` (do mais novo para o mais velho, até a primeira página toda anterior ao período);
  - `materia/tipomaterialegislativa/` e `materia/materialegislativa/?ano={ano}&tipo={id}` (os projetos do período em lote; `materia/materialegislativa/{id}/` só para o que não veio no lote);
  - votações: `sessao/registrovotacao/?data_hora__year={ano}` (matéria, placar e resultado no `__str__`) e `sessao/votoparlamentar/?data_hora__year={ano}` (voto de cada parlamentar: "Sim", "Não", "Abstenção", "Não Votou");
  - presença: `sessao/sessaoplenaria/?data_inicio__year={ano}` e `sessao/sessaoplenariapresenca/?parlamentar={id}&o=-id` (para quando a página toda tem `data_sessao` anterior ao período).
- **Armadilhas:**
  - links de foto e de documento vêm com `http://` (forçamos `https`);
  - `materia/autoria/?materia__ano=` não filtra (devolve tudo); `?autor=` filtra, e `o=-id` ordena. Sem a ordem, a autoria de cada vereador vinha desde sempre (até 3.800 itens por vereador em João Pessoa). Se uma instalação ignorar a ordem (página fora de ordem decrescente), a lista é lida inteira;
  - `materia/materialegislativa/?ano=&tipo=` filtra (João Pessoa: 203 mil matérias no total, 718 projetos de lei ordinária em 2026). A carga confere a primeira página e, se o filtro for ignorado, busca projeto a projeto;
  - o texto da autoria ("Requerimento nº 324 de 2026") já traz tipo e ano, o que evita baixar cada matéria;
  - votações nominais: cerca de 60% das câmaras da amostra registram; as simbólicas não têm voto por parlamentar;
  - na lista de presença, o filtro por ano da sessão (`sessao_plenaria__data_inicio__year`) é ignorado e devolve tudo; o filtro por parlamentar funciona;
  - nem toda sessão tem a lista de presença lançada: contamos só as sessões com alguma presença registrada.
- **Assembleias com SAPL** (levantamento das 27 casas em 2026-10-08): AC, AL, AM, PB, PI, RO, RR e TO, em `https://sapl.al.{uf}.leg.br/`. O de MT existe, mas parou em 2018 (só a legislatura 2015–2018) e não é usado. O de RR recusa acesso a partir do GitHub Actions (403), embora responda de fora. As demais (AP, BA, CE, DF, ES, GO, MA, MG, MS, PA, PE, PR, RJ, RN, RS, SC, SE e SP) usam sistemas próprios; ALMG e ALESP têm dados abertos próprios, a examinar.
- **Frequência:** semanal, um estado por máquina, uma requisição por vez em cada câmara; as assembleias numa máquina à parte.

## ALMG: Assembleia Legislativa de Minas Gerais

- **Endereço:** `https://dadosabertos.almg.gov.br/api/v2/` (acrescentar `formato=json`). A lista de rotas fica em `api/ajuda/swagger/endpoints/lastest`; os parâmetros só aparecem nos exemplos das descrições.
- **Rotas usadas:**
  - `deputados/em_exercicio` e `deputados/{id}` (situação, tipo de mandato, e-mail);
  - `proposicoes/pesquisa/direcionada?tipo={sigla}&ano={ano}&tp=100&p={página}` (PL, PLC, PEC, PRE, RQN e IND);
  - `prestacao_contas/verbas_indenizatorias/deputados/{id}/datas` (meses fechados) e `.../{id}/{ano}/{mês}` (total por categoria, com notas).
- **Armadilhas:**
  - página de no máximo 100 itens; a resposta vem em `resultado` (não `resultadoPesquisa`, como diz a documentação);
  - autoria em texto e em `matricula` (ids separados por quebra de linha, na mesma ordem); a matrícula é o id do deputado na API;
  - a pesquisa de reuniões de Plenário usa `ini` e `fim` (AAAAMMDD); outros nomes são ignorados e devolvem as 7 mil reuniões desde 1995;
  - os detalhes das reuniões (desde maio de 2023) trazem a pauta e o resultado de cada matéria, mas não o voto de cada deputado nem a presença;
  - datas às vezes vêm como objeto (`{"@class": "sql-timestamp", "$": "2025-02-03"}`).
- **Volume:** cerca de 120 requisições de proposições por carga e uma por mês fechado de cada deputado nos gastos; a carga leva uns 11 minutos.
- **Frequência:** semanal, junto com as câmaras.

## ALESP: Assembleia Legislativa de São Paulo

- **Endereço:** arquivos em `https://www.al.sp.gov.br/repositorioDados/`, listados no catálogo `https://www.al.sp.gov.br/dados-abertos/` (cada recurso traz a URL do "arquivo completo"). Atualização diária.
- **Arquivos usados:**
  - `deputados/deputados.xml` (só quem está em exercício: `Situacao` = `EXE`);
  - `processo_legislativo/proposituras.zip` (130 MB descompactado, desde 1996) e `documento_autor.zip` (145 MB);
  - `processo_legislativo/naturezasSpl.xml` (código da natureza: 1 PL, 2 PLC, 3 PR, 4 PDL, 5 PEC, 6 moção, 7 requerimento, 8 requerimento de informação, 9 indicação);
  - `deputados/despesas_gabinetes.xml` (164 MB, sem compactação, desde 2015).
- **Armadilhas:**
  - a autoria usa o `IdSPL` do deputado (casa 94 de 94); `IdDeputado` casa só em parte; os gastos usam a `Matricula`;
  - a categoria do gasto vem com uma letra na frente ("A - COMBUSTÍVEIS E LUBRIFICANTES");
  - a rota `/api/deputadoPresenca` citada no catálogo responde 404; a presença em Plenário só existe num formulário do site, e a página de votações em Plenário responde 403 a acesso automatizado;
  - há presença e votações das **comissões** (`comissoes_permanentes_presencas.xml`, `comissoes_permanentes_votacoes.xml`, 65 MB), ainda não usadas.
- **Frequência:** semanal, junto com as câmaras.

## ALEPE: Assembleia Legislativa de Pernambuco

- **API (sem chave):** `https://dadosabertos.alepe.pe.gov.br/api/v1/` (documentação em `/?documentacao=...`). Rotas: `parlamentares/` (JSON: `nomeParlamentar`, `partido`; 49, todas as cadeiras), `proposicoes/{projetos|indicacoes|requerimentos}/?ano=` (XML), `cargos`, `contratos`, `licitacoes`, `lotacoes`, `remuneracao` e `servidores`. **Sem** votações, presença ou gastos do gabinete (testado: `votacoes`, `presenca`, `despesas` dão 404).
- **Proposições (XML):** `docid`, `numero`, `ano`, `tipo` ("PROJETO DE LEI ORDINÁRIA", "PROPOSTA DE EMENDA A CONSTITUIÇÃO"…), `ementa`, `dataPublicacao` (`dd/mm/aaaa`) e `<autores>` com `nome` e `tipo` (`DEPUTADO`, `EXTERNO` para o Executivo, `COMISSAO`). O autor deputado vem pelo **mesmo nome parlamentar** da lista de deputados. Em 2026 (até outubro): 629 projetos, 1,7 MB de indicações e 1,4 MB de requerimentos.
- **Armadilhas:** a ementa das indicações e dos requerimentos vem em HTML escapado duas vezes (`&lt;p&gt;Indicamos &amp;agrave;…`). A rota sem o tipo (`proposicoes/`) devolve erro em XML com as rotas válidas.
- **Link de cada proposição:** `https://www.alepe.pe.gov.br/proposicao-texto-completo/?docid={docid}`.
- **Levantamento das outras assembleias** (09/10/2026): ALERJ, ALRS, ALEP e ALBA não têm portal de dados abertos achável (endereços testados dão 404, 500 ou não conectam). Um estudo de 2025 ("Democracia em Formato JSON", preprint SciELO) compara as APIs das 26 assembleias e da CLDF; é o ponto de partida do levantamento casa a casa.

## Canais oficiais dos municípios (varredura do Panóptico)

- **O que é:** varredura dos domínios oficiais de cada cidade: prefeitura em `{cidade}.{uf}.gov.br`; câmara em `{cidade}.{uf}.leg.br`, `camara{cidade}...` e `cm{cidade}...`; e os links do próprio site da prefeitura. Confere se a página é da cidade e reconhece o sistema (SAPL; fornecedores de transparência como Betha, IPM, CR2, Fiorilli e Elotech).
- **Resultado:**
  - `data/canais_oficiais.csv`, versionado e revisado por pull request;
  - `data/canais_curados.csv`, com as correções feitas à mão (capitais), que substituem a varredura.
- **Armadilhas:**
  - muitas cidades dividem o mesmo servidor, que bloqueia rajadas (resposta 444; visto em SC): uma requisição por vez por servidor;
  - certificados vencidos;
  - links malformados (`http://[facebook_entidade]`);
  - modelos de site de fornecedor apontando para o portal de outra cidade.
- **Portal da transparência por sonda:** quando o link não está no HTML, testa `transparencia.{domínio}`, `/portal-da-transparencia`, `/transparencia` e `/portaltransparencia`, e só aceita página com "transparência" no título (muitos sites devolvem a página inicial, status 200, para qualquer endereço). `python -m ingestion.canais.varredura --completar` faz só essa sonda nas cidades do catálogo sem portal.
- **Santa Catarina bloqueada:** o servidor compartilhado da maioria das prefeituras de SC responde 403 (nginx) a qualquer acesso automatizado, mesmo com identificação de navegador. Não contornamos.
- **Frequência:** varredura inicial única; depois, revisão pontual quando uma carga falhar.

## A confirmar (fases seguintes)

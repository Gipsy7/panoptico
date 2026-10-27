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
- **Autor que não é deputado (desde 21/10/2026):** o arquivo de proposições já traz todo PL/PLP/PEC/PDL de qualquer autor; só falta saber quem apresentou. No arquivo de autores, `nomeAutor` das linhas que não são deputado ("Poder Executivo", "Comissão de Desenvolvimento Urbano", "Senado Federal - Rogério Carvalho") vira `proposicao.autor_descricao`, só para quem não tem nenhum deputado autor (2.773 de 25.775). Tipos de autor vistos em 2025: `10000` deputado, `2` comissão permanente, `30000` Poder Executivo, `20000` senador, `40000` órgão do Poder Legislativo, `1` Comissão Diretora, `12000` órgão da Câmara, `81001` Plenário Virtual do CN, entre outros. A linha de um senador autor traz `idDeputadoAutor` vazio. `origem = "legislatura"`.
- **Proposições votadas fora do recorte (`camara_proposicoes_votadas`):** as citadas em `votacao.proposicao_id_externo` que não estão na tabela (anteriores a 2023, MPV e outras siglas; ~78). A ficha vem de `GET https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}` (`{"dados": {...}}`): `siglaTipo`, `numero`, `ano`, `ementa`, `dataApresentacao` e `statusProposicao.descricaoSituacao`. Uma chamada por proposição, pausa de 0,3 s; ficha 404 é pulada. `origem = "votada"`; a linha nunca sobrescreve uma de legislatura. Rode depois das cargas anuais: `python -m ingestion.camara.proposicoes --votadas` (aceita `--de-raw`).

## Senado: projetos de lei por senador

- **URL:** `GET https://legis.senado.leg.br/dadosabertos/processo?codigoParlamentarAutor={codigo}` (JSON)
- **Campos usados:** `identificacao` ("PL 2036/2023"), `codigoMateria`, `casaIdentificadora` (só `SF`), `dataApresentacao`, `ementa`, `situacaoAtual`, `autoria`.
- **Autor principal:** o primeiro nome em `autoria`. Os demais são coautores (PECs exigem 27 assinaturas).
- **Página pública:** `https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigoMateria}`
- **Lista geral (desde 21/10/2026):** `GET /processo?sigla={PL|PLP|PEC|PDL}&ano={2023..}` devolve todos os processos da sigla e do ano, de qualquer autor (5.089 em 2023–2026; a carga por senador cobre os senadores em exercício). Entram os que ainda não estão na tabela, apresentados desde 01/02/2023 (PL 74/2023 foi apresentado em 27/12/2022 e fica de fora), `casaIdentificadora = SF`. `autoria` sem "Senador" é a Câmara dos Deputados (1.920), uma comissão ou CPI; o texto vira `autor_descricao` (até 300 caracteres) e a proposição fica sem `Autoria`. Dezesseis chamadas, pausa de 0,3 s. O bruto traz `__geral` e `__votadas` ao lado dos códigos dos senadores; bruto antigo (sem essas chaves) continua valendo.
- **Votadas fora do recorte:** `GET /processo?codigoMateria={codigo}` devolve o mesmo objeto da lista (uma lista com um item), sem filtro de sigla nem de data: entram PEC antiga, MPV (`casaIdentificadora = CN`, autoria "Presidência da República") e outras siglas, com `origem = "votada"`, só as citadas em `votacao.proposicao_id_externo` que a tabela não tem (~18).

## Câmara: votações nominais do Plenário

- **URLs:** `https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv` e `.../votacoesVotos/csv/votacoesVotos-{ano}.csv`
- Filtro: `siglaOrgao = PLEN` e votação com votos registrados (as simbólicas não têm).
- O arquivo de votos **só lista quem votou**. Não há registro de ausência nem de justificativa.
- Códigos de voto: Sim, Não, Abstenção, Obstrução, "Artigo 17" (presidente da sessão) e vazio.
- Também `votacoesProposicoes-{ano}.csv` (liga a votação à proposição; quando há duas, uma é REQ/REC sobre a outra, e usamos a principal) e `votacoesOrientacoes-{ano}.csv` (orientação por bancada: `siglaBancada`, `uriBancada`, `orientacao`).
- **Orientações (desde 18/10/2026 guardamos todas, com `orientacao.tipo`):** lideranças (Governo, Maioria, Minoria, Oposição); partidos, que trazem `uriBancada` com o id do partido, mas a sigla às vezes vem cortada em 10 letras ("Solidaried") ou com outra grafia ("Novo", "Missão"): a sigla certa sai do id pelo arquivo de votos (`deputado_uriPartido` → `deputado_siglaPartido`); federações ("Fdr PT-PCdoB-PV", "Fdr PSDB-CIDADAN", cortada) e blocos ("Bl UniPpPsd...", "Bl AvanSolidPrd...", truncados e sem id). Orientação em branco = o líder não orientou (só lideranças continuam gravadas em branco).
- **Composição de blocos e federações:** `GET /api/v2/blocos?idLegislatura={57}` e `/api/v2/blocos/{id}/partidos` (siglas). Só traz a composição **atual**, sem datas; bloco já desfeito vem com a lista de partidos vazia, mas o nome é a própria lista ("AVANTE, SOLIDARIEDADE, PRD"). A API `/votacoes/{id}/orientacoes` não ajuda: traz `siglaPartidoBloco` igualmente truncado e `codPartidoBloco` nulo para blocos. Os blocos vão para `blocos.json` dentro do mesmo zip bruto.
- `votacoes-{ano}.csv` traz `aprovacao` (1/0/vazio) e `votosSim`/`votosNao`/`votosOutros` (o placar publicado, que inclui deputados que já deixaram o cargo). Votação secreta (ex.: escolha de ministro do TCU) aparece com **o voto em branco para todos** os que votaram; só o placar diz o resultado.
- O arquivo de votos traz `deputado_siglaPartido` no dia da votação.
- Os quatro CSVs são gravados juntos num `.zip` bruto.

## Câmara: temas das proposições

- **URLs:** `https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/csv/proposicoesTemas-{ano}.csv` (~5 MB/ano) e, para matérias votadas de anos antigos, `GET /api/v2/proposicoes/{id}/temas`.
- 32 temas oficiais (`/referencias/proposicoes/codTema`), entre eles "Homenagens e Datas Comemorativas". Uma proposição pode ter mais de um tema.

## Câmara: representações no Conselho de Ética

- **API:** `GET /api/v2/proposicoes?siglaTipo=REP&ano={ano}&itens=100` (cabeçalho `x-total-count`; 29 em 2023, 5 em 2024, 28 em 2025, 10 em 2026 até outubro) e o detalhe em `/api/v2/proposicoes/{id}` (`statusProposicao`: `descricaoSituacao`, `descricaoTramitacao`, `dataHora`, `despacho`).
- **Não há campo com o deputado representado:** ele só aparece na ementa, às vezes em maiúsculas ("Deputado DELEGADO RAMAGEM"), às vezes não ("Deputado Gilvan da Federal"), às vezes pelo nome civil completo ("ANDRÉ LUIS GASPAR JANONES"), às vezes em lista ("Deputadas CÉLIA NUNES CORREA, ÉRIKA JUCÁ KOKAY…").
- **Link público:** `https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}`.

## Senado: representações no Conselho de Ética

- **API:** `GET https://legis.senado.leg.br/dadosabertos/processo?sigla=REP&dataInicioApresentacao=2019-01-01` (JSON). Substitui `/materia/pesquisa/lista`, que avisa estar descontinuada (desativação prevista em 01/02/2026, mas ainda respondia em 09/10/2026, sem as REP recentes).
- O parâmetro `ano` não filtra nessa rota; use `dataInicioApresentacao`. Sem filtro de data, a lista começa em 1947 (representações de sindicatos e cidadãos, de outra natureza).
- **Campos:** `identificacao` ("REP 1/2024"), `dataApresentacao`, `autoria`, `ementa` (com o nome do senador: "em face do Senador Flávio Bolsonaro"), `situacaoAtual`, `codigoMateria` (link: `www25.senado.leg.br/web/atividade/materias/-/materia/{codigo}`).

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
- O nome do partido na orientação é o de uso ("Progressistas", "Podemos", "Republicanos"), diferente da sigla dos votos ("PP", "PODE", "REPUBLICANOS"). A mesma resposta traz `votosParlamentar[]` (nome do senador e esse nome de partido); casamos pelo nome do senador com a lista de votos para achar a sigla. "B.Feminina"/"Banc Fem" (bancada feminina) fica como `outra`.
- `resultadoVotacao` (A/R) e `totalVotosSim`/`totalVotosNao`/`totalVotosAbstencao`, preenchidos nas votações secretas (sem voto nominal).

## Câmara: discursos em Plenário (reconhecimento de 21/10/2026, ainda sem ingestão)

- **Duas rotas, mesmo conteúdo:**
  - API v2, por deputado: `GET https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/discursos?dataInicio=AAAA-MM-DD&dataFim=AAAA-MM-DD&itens=100&pagina=N&ordenarPor=dataHoraInicio&ordem=ASC`. Campos: `dataHoraInicio`, `faseEvento.titulo` ("Ordem do Dia", "Breves Comunicações", "Encerramento", "Homenagem", "Comissão Geral"), `tipoDiscurso` ("PELA ORDEM", "DISCUSSÃO", "ENCAMINHAMENTO DE VOTAÇÃO", "COMO LÍDER", "PARECER", "ORIENTAÇÃO DE BANCADA"...), `sumario`, `keywords`, `urlTexto`, `urlVideo`, `urlAudio`, `transcricao` (texto inteiro, ~3 KB por discurso; não guardar).
  - Webservice antigo, por período (todos os oradores numa chamada): `GET https://www.camara.leg.br/SitCamaraWS/SessoesReunioes.asmx/ListarDiscursosPlenario?dataIni=DD/MM/AAAA&dataFim=DD/MM/AAAA&codigoSessao=&parteNomeParlamentar=&siglaPartido=&siglaUF=` (XML). Por discurso: sessão (`codigo` "160.2026"), fase (código e descrição), orador (nome, partido, UF, **sem id**), `horaInicioDiscurso`, `txtIndexacao`, `numeroQuarto`, `numeroInsercao`, `sumario`. Um mês inteiro numa chamada (~1,4 MB).
- **Não há ligação direta com a votação.** `uriEvento` vem sempre vazio na API (0 de 358 numa amostra); `/eventos/{id}/discursos` não existe (405). `faseEvento` só traz o título. A ligação é pelo **sumário**, que cita a matéria por extenso ("Projeto de Lei Complementar nº 74, de 2026"; às vezes "PL nº&nbsp;5.063 de 2023", "Projeto de Decreto Legislativo (PDL) nº 214", "Projeto de Complementar nº 235", número com ponto de milhar).
- **Volume (Plenário, todos os tipos):** 16.810 discursos em 2025 e 7.430 em 2026 até 20/10. Sumário + indexação: ~716 caracteres em média. 855 sem sumário (sessões recentes ainda sem indexação).
- **Armadilhas:**
  - a orientação de bancada vem como `tipoDiscurso` "PELA ORDEM" (sumário "O Deputado orientou a bancada na votação..."); só 7 de 4.041 vieram como "ORIENTAÇÃO DE BANCADA". Filtrar por tipo perde a maior parte das falas sobre a votação;
  - a **fase do webservice não bate com a da API** (Chico Alencar 2025: 235 discursos na Ordem do Dia pela API, 40 pelo webservice, que põe a maioria em "Breves Comunicações"); o tipo da sessão vem sempre "Ordinária - CD";
  - `horaInicioDiscurso` às vezes vem só com a data (25 de 24.240);
  - `urlTexto` da API aponta para a página do Diário da Câmara e vem nulo nas sessões recentes (301 de 323 preenchidos em 2025 para um deputado; nulo em 09/2026); `urlVideo` veio nulo em todos. O texto taquigráfico abre por `https://www.camara.leg.br/internet/sitaqweb/TextoHTML.asp?etapa=5&nuSessao={sessão}&nuQuarto={quarto}&nuOrador={n}&nuInsercao={inserção}&dtHorarioQuarto=HH:MM&sgFaseSessao={fase}&Data=DD/MM/AAAA` (respondeu 200);
  - o webservice não traz id do deputado: o nome casa exato e único com `deputado_nome` do arquivo de votos em 99,9% dos discursos ligados a votações (6.965 de 6.973); quem não casa é senador, ministro ou governador em Comissão Geral.
- **Requisições:** API, ~2 por deputado-ano (30 deputados, 2025: 62 chamadas, 4.041 discursos) → carga de 2 anos ≈ 1.200–1.500 chamadas; diária ≈ 513 (uma por deputado em exercício). Webservice: 1 chamada por mês (22 para 2025–2026, 30 MB de XML).
- **robots.txt** (www.camara.leg.br): veda rotas de busca do site, não `SitCamaraWS` nem `sitaqweb`.

## Senado: discursos em Plenário (reconhecimento de 21/10/2026, ainda sem ingestão)

- **Por período (todas as sessões):** `GET https://legis.senado.leg.br/dadosabertos/plenario/lista/discursos/{AAAAMMDD}/{AAAAMMDD}` (JSON com `Accept: application/json`). `Sessoes.Sessao[]` (`CodigoSessao`, `TipoSessao`, `DataSessao`, `SiglaCasa` SF ou CN) → `Pronunciamentos.Pronunciamento[]`: `CodigoPronunciamento`, `TipoUsoPalavra.Descricao`, `Data` (sem hora), `Resumo`, `Indexacao`, `TextoIntegral` (página), `TextoIntegralTxt`, `CodigoParlamentar`, `NomeAutor`, `Partido`, `UF`, `TipoAutor`, `Publicacoes` (página do Diário).
- **Por senador:** `GET /dadosabertos/senador/{codigo}/discursos?dataInicio=AAAAMMDD&dataFim=AAAAMMDD` (sem período, últimos 30 dias); traz também a `SessaoPlenaria.CodigoSessao`.
- **Ligação direta (sem resumo):** `GET /dadosabertos/plenario/encontro/{codigoSessao}` (~250 KB) traz `encontroRealizado.usosPalavra.usoPalavra[]` com `codItemPauta`, tipo, parlamentar e hora (`evento.dthEvento`), e `itensPauta.itemPauta[]` com `codMateria`. O `codigoSessao` é o mesmo da API de votações. Nas 57 sessões com votação nominal de 2025–2026: 3.307 usos da palavra, 1.580 com item da pauta (quase todas as orientações e discussões), só 30 com resumo.
- **Volume:** 6.868 pronunciamentos em 2025–2026 (4.396 e 2.472), 1.293 de autor externo (sem `CodigoParlamentar`); 22 chamadas mensais, 12 MB.
- **Armadilhas:**
  - o `Resumo` das falas de votação é **descritivo, não traz o argumento**: "Orientação à bancada, pelo Partido PL, sobre o Projeto de Lei Complementar (PLP) n° 128, de 2025, que ...". O argumento só está no texto integral (link);
  - defasagem de ~1 semana: as sessões de 14 e 15/10/2026 ainda não tinham pronunciamentos em 21/10, embora o encontro já listasse os usos da palavra;
  - juntar pronunciamento e uso da palavra por (sessão, parlamentar, tipo) é único em 1.834 de 2.768 casos, ambíguo em 775;
  - `identificacao` das votações com sufixo ("PLP 235/2019 (Substitutivo-CD)", "PEC 66/2023 (fase 2)"); usar `sigla`, `numero` e `ano`;
  - MPV votada como PLV: o resumo cita "Projeto de Lei de Conversão nº 4, de 2025", não a MPV 1.300;
  - `https://legis.senado.leg.br/robots.txt` responde 403 ("Request forbidden by administrative rules"); a API de dados abertos responde normalmente.

## Câmara e Senado: pauta do Plenário (reconhecimento de 21/10/2026)

- **Câmara:** `GET /api/v2/eventos?idOrgao=180&dataInicio=AAAA-MM-DD&dataFim=AAAA-MM-DD&itens=100` (sessões do Plenário; `descricaoTipo` "Sessão Deliberativa", "Sessão Não Deliberativa Solene"...; `situacao` "Convocada", "Encerrada") e `GET /api/v2/eventos/{id}/pauta`: `ordem`, `topico`, `regime`, `titulo` ("MPV 1357/2026"), `proposicao_` (id, siglaTipo, numero, ano, ementa), `proposicaoRelacionada_`, `relator`, `uriVotacao`, `situacaoItem`.
  - **Armadilhas:** o item se repete uma vez por votação (mesmo `ordem`, `uriVotacao` diferente); em MPV o `proposicao_` é o **parecer** (`siglaTipo` "PAR", `ano` 0) e a matéria está em `proposicaoRelacionada_`. Em 21/10/2026 (período eleitoral) os próximos 14 dias só tinham uma sessão solene.
  - Há também `https://dadosabertos.camara.leg.br/arquivos/eventos/csv/eventos-{ano}.csv` (1 MB); não há arquivo de pautas (`eventosPautas` dá 404).
- **Senado:** `GET /dadosabertos/plenario/agenda/mes/{AAAAMMDD}` (da data até o fim do mês) ou `/plenario/agenda/dia/{AAAAMMDD}`. `Sessoes.Sessao[]` (`CodigoSessao`, `TipoSessao`, `SituacaoSessao` "Agendada"/"Encerrada"/"Sessão não realizada") → `Materias.Materia[]`: `CodigoMateria` (o mesmo `proposicao_id_externo` das votações), `DescricaoIdentificacaoMateria` ("PEC 221/2019"), `NumeroMateria` com zeros ("00221"), `Ementa`, `Parecer` (com o relator, em texto), `Apreciacao`, `DescricaoTipoPauta`. `/plenario/agenda/cn/{data}` (Congresso) veio vazio.
- **Frequência sugerida:** diária, janela de 14 dias (a Câmara convoca com poucos dias de antecedência).

## Câmara: tramitação das proposições (reconhecimento de 21/10/2026)

- **API:** `GET /api/v2/proposicoes/{id}/tramitacoes` (todas numa resposta, sem paginação): `dataHora`, `sequencia`, `siglaOrgao`, `descricaoTramitacao`, `descricaoSituacao`, `despacho` (o texto que explica), `regime`, `apreciacao`, `uriUltimoRelator`, `url`. `GET /api/v2/proposicoes/{id}` traz `statusProposicao` (situação e `uriUltimoRelator`), inclusive de projetos antigos (PL 2694/2015, PEC 302/2017).
- **Relator sem chamada extra:** `proposicoes-{ano}.csv` já traz `ultimoStatus_uriRelator`, `ultimoStatus_descricaoSituacao`, `ultimoStatus_despacho` e `ultimoStatus_dataHora` (este serve para a carga incremental: só rebuscar quem mudou).
- **Volume (amostra de 30):** projetos com votação nominal: média 45 linhas (mediana 37); projetos quaisquer desde 2023: média 10,9 (mediana 5). ~690 bytes por linha no JSON; ~130 caracteres de texto (despacho + descrição).
- **Armadilhas:**
  - o arquivo em lote `arquivos/proposicoesTramitacoes/csv/proposicoesTramitacoes-{ano}.csv` (35–52 MB/ano; o ano é o da tramitação, não o do projeto) **não bate com a API**: PL 2528559 tem 32 linhas na API e 1 no arquivo; 2461480 tem 22 e 24; `idTramitacao` não é identificador (603 valores distintos em 500 mil linhas) e há 436 pares (proposição, sequência) repetidos. Não usar;
  - `sequencia` tem buracos (não é contagem de linhas);
  - `descricaoTramitacao` às vezes não descreve o ato (última linha de um projeto que virou lei: "Apresentação de Proposição" com despacho "Remessa do Ofício... informando restituição de autógrafo sancionado"): mostrar o `despacho`.
- **Textos reais (para o mapa de etapas):** "Apresentação de Proposição", "Recebimento - Relator(a)", "Designação de Relator(a)", "Parecer do(a) Relator(a)", "Aprovação de Urgência (154, 155 ou 64 CF)", "Votação (Plenário)", "Aprovação de Proposição (Plenário)", "Rejeição de Proposição (Plenário)", "Remessa ao Senado Federal" (no despacho), situações "Aguardando Designação de Relator(a)", "Tramitando em Conjunto", "Pronta para Pauta", "Aguardando Apreciação pelo Senado Federal", "Transformado em Norma Jurídica", "Transformado em Norma Jurídica com Veto Parcial", "Arquivada", "Retirado pelo(a) Autor(a)".

## Senado: tramitação dos processos e relatorias (reconhecimento de 21/10/2026)

- **Processo:** `GET /dadosabertos/processo/{idProcesso}` (~50 KB): `autuacoes[].informesLegislativos[]` (data, colegiado, `descricao`: o texto da tramitação), `autuacoes[].situacoes[]` (sigla, descrição, início e fim), `deliberacao`, `normaGerada`, `outrosNumeros[]` (o processo da outra Casa, ex.: PEC 22/2025 na Câmara), `ordensDoDia[]` (sessões em que entrou na pauta), `codigoMateria`, `dthUltimaAtualizacao`.
- **Relatoria:** `GET /dadosabertos/processo/relatoria?idProcesso={id}`: `nomeParlamentar`, `codigoParlamentar`, `nomeColegiado`, `dataDesignacao`, `dataDestituicao`, `descricaoTipoEncerramento`.
- **Lista:** `GET /dadosabertos/processo?sigla={PL|PLP|PEC|PDL}&ano={ano}` (aqui `ano` filtra): 5.089 processos numerados no Senado em 2023–2026 (PL 3.524, PDL 1.206, PLP 225, PEC 134), com `autoria`, `objetivo` (Iniciadora/Revisora), `situacaoAtual`, `dataUltimaAtualizacao` (para carga incremental).
- **Volume (amostra de 30):** votados: média 34 informes (mediana 24) e 14,6 situações; quaisquer: média 24 (mediana 6). ~196 caracteres por informe.
- **Textos reais:** situações "AGUARDANDO DESIGNAÇÃO DO RELATOR", "MATÉRIA COM A RELATORIA", "PRONTA PARA A PAUTA NA COMISSÃO", "APROVADO PARECER NA COMISSÃO", "INCLUÍDA EM ORDEM DO DIA", "PRONTO PARA DELIBERAÇÃO DO PLENÁRIO", "APROVADA", "REMETIDA À CÂMARA DOS DEPUTADOS", "REMETIDA À SANÇÃO", "TRANSFORMADA EM NORMA JURÍDICA (COM VETO PARCIAL)", "APRECIADA EM DECISÃO TERMINATIVA PELAS COMISSÕES", "ARQUIVADA AO FINAL DA LEGISLATURA"; informes como "Distribuído à Senadora Leila Barros, para emitir relatório." e "Remetido Ofício SF nº 289 ... encaminhando autógrafo do projeto para revisão".
- **Numeração única desde 2019:** PL que vem da Câmara mantém o número (PL 2159/2021 nas duas Casas), o que permite ligar as duas fichas pelo rótulo ou por `outrosNumeros`.

## Votações locais: a matéria votada (reconhecimento de 21/10/2026)

- **SAPL:** `sessao/registrovotacao/` traz o campo `materia` (id da matéria) em 100% das votações nominais medidas (ALEAC: 42 de 42 em 2025–2026; Rio Branco: 1.270 de 1.270). A ficha vem por `materia/materialegislativa/{id}/` (todas com ementa na amostra). O conector já lê o id (`materia_id`), mas só o usa para montar o link.
- **O que é votado nominalmente** (pelo `__str__`): ALEAC, 36 vetos, 3 PDL, 2 PEC, 1 PLC; Rio Branco, 401 requerimentos, 233 projetos de lei, 193 atas, 177 emendas, 107 PDL, 41 PLC, 38 vetos, 37 projetos de resolução. Na amostra das fichas, a maior parte é do Executivo (vetos, PEC) ou requerimento: **casar com `projeto_local` (só projetos de autoria dos vereadores/deputados em exercício) cobre a minoria**; a ementa da matéria votada precisa vir da própria ficha.
- **Armadilhas:** em Rio Branco quase todo registro tem voto por parlamentar (1.270 de 1.271), inclusive atas; Cruzeiro do Sul não tem nenhum registro; João Pessoa respondeu 503 na hora do teste (falha passageira, não bloqueio).
- **Conectores próprios das assembleias:** ALEP (título e ementa no texto de `materia`, sem id), ALESC (link `/proposicoes/{id}` e ementa no cartão da Ordem do Dia; o id está no HTML, hoje não guardado), ALRS (sigla, número/ano e assunto no texto), ALESP (votos de comissão, com o código do documento). As demais não publicam votação nominal em formato aberto.

## Portal da Transparência: emendas parlamentares

- **URL (lote, sem chave):** `https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO` (zip de ~32 MB com três CSVs em latin-1, separador `;`)
- `EmendasParlamentares.csv`: uma linha por emenda × localidade × ação. O **código da emenda se repete**. Localidade com código IBGE só em ~16% das linhas; o resto é "MÚLTIPLO", UF ou "Nacional".
- `EmendasParlamentares_PorFavorecido.csv` (~180 MB): quem recebeu, com natureza jurídica, UF e **nome** do município (sem código IBGE). Há linhas com código da emenda "Sem informação".
- Autor: código do sistema de orçamento + nome em maiúsculas. Não há id da Câmara ou do Senado.
- A API (`api.portaldatransparencia.gov.br`, exige chave em `PORTAL_TRANSPARENCIA_CHAVE`) pagina de 15 em 15. Por isso usamos o lote.
- **Medido em 18/10/2026 (arquivo de 09/10/2026):** `EmendasParlamentares.csv` 94.663 linhas (2014–2026); `PorFavorecido` 827.457 linhas, tipos "Emenda Individual - Transferências com Finalidade Definida" (415.761), "Emenda de Relator" (207.282), "Emenda de Bancada" (108.339), "Emenda Individual - Transferências Especiais" (52.147, os Pix **pagos**) e "Emenda de Comissão" (43.928); 67.046 linhas com código "Sem informação" (sem autor nem ano; desde 20/10/2026 vão para `emenda_pagamento_sem_codigo`, ver a armadilha abaixo). Prefeituras, fundos municipais e entidades: ~308 mil linhas.
- **Armadilha: pagamento sem código de emenda (medido em 20/10/2026, arquivo de 19/10/2026).** No `PorFavorecido`, 29.175 linhas de prefeitura, fundo municipal ou entidade (R$ 6,44 bi) têm código da emenda "Sem informação" e número da emenda "S/I". O **tipo de emenda vem preenchido** em todas (com destino definido R$ 3,68 bi; relator R$ 1,40 bi; comissão R$ 0,70 bi; bancada R$ 0,66 bi; nenhuma Pix); o **autor não**: "S/I / Sem informação", exceto nas de comissão, que trazem o marcador "-99 / RELATOR GERAL" (o mesmo código genérico que o arquivo usa nas emendas de relator de 2020 a 2022 com código), que não é o autor de uma emenda de comissão. O "Ano/Mês" é o do **pagamento** (2015 a 2026, 85% do valor até 2019; os de 2021 em diante, R$ 0,45 bi, só podem ser restos a pagar, porque as emendas sem código vão até 2020); o ano da emenda não vem. No `EmendasParlamentares.csv` as emendas sem código são todas de 2014 a 2020 (individuais quase só de 2014), com município e ação, mas sem chave que ligue a linha de pagamento à linha da emenda: casar por município + tipo seria palpite. O `_Convenios.csv` tem 9.190 linhas sem código (convênios de 1999 a 2024), também sem chave para o pagamento. O arquivo por favorecido não tem ação, programa, função nem número de documento. A API do Portal (com chave) não foi usada. Tratamento: tipo da fonte, sem autor (decisão de 20/10/2026).
- **Armadilha: nome de município antigo ou com grafia diferente (medido em 20/10/2026).** O `PorFavorecido` traz o nome do cadastro do favorecido: Embu (hoje Embu das Artes), Itapagé (Itapajé), Presidente Juscelino (Serra Caiada), Augusto Severo (Campo Grande/RN), Fortaleza do Tabocão (Tabocão), Iguaraci (Iguaracy), Seridó (São Vicente do Seridó), Florínea (Florínia), mais São Luiz/RR, Açu/RN e Arês/RN. Sem tratar, 716 linhas (R$ 465 mi) ficavam sem cidade. Tabela oficial: alterações toponímicas do IBGE em `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/alteracoes_toponimicas_municipais/` (xls de 2014 e 2024), versionada em `data/municipios_nomes_anteriores.csv`; grafias que o IBGE não registra, em `data/municipios_nomes_extra.csv` com prova por linha. A carga conta o que sobrar, por nome, com valor.
- **Armadilha: código de autor que muda de dono.** Desde a LOA 2025 o arquivo reatribui emendas de ex-parlamentares ao sucessor no mesmo código, com o nome "TIAGO DIMAS (EX-PARLAMENTAR LAZARO BOTELHO, NOS TERMOS ART. 78 LDO 2025 ...)" ou "(... DECISAO ADPF 854 ...)". 47 códigos têm mais de um nome; a maioria é grafia ("AUREO" → "AUREO RIBEIRO"). A ligação ao parlamentar é por par (código, nome); o nome antes do parêntese é o autor.
- **Armadilha: pessoas físicas e empresário individual** aparecem como favorecidos (17 linhas só em Gaspar). Ficam fora pela natureza jurídica.
- **Mapa CNPJ → município:** API de entes do SICONFI, `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes` (uma chamada, 5.598 entes, campos `cod_ibge`, `cnpj`, `uf`, `esfera` M/E/D/U). Para fundos municipais e entidades vale o próprio `PorFavorecido` (CNPJ → município já resolvido, só quando o CNPJ aparece num município só).
- **Remuneração:** a API de remuneração do Portal cobre servidores do Executivo, não parlamentares. O subsídio vem do Decreto Legislativo 172/2022.

### O que aconteceu com o dinheiro: convênios e transferências especiais

- **Ligação:** `EmendasParlamentares_Convenios.csv` (no mesmo zip das emendas) traz código da emenda + **número do convênio** (76.152 pares e 72.492 convênios em todos os anos, 2015–2026; 17.855 linhas desde 2023; 9.190 no arquivo todo têm código "Sem informação" e não ligam a nenhuma emenda). Vai para `emenda_convenio`.
- **Convênios (situação, valores, vigência):** `https://portaldatransparencia.gov.br/download-de-dados/convenios/{AAAAMMDD}` (zip de ~67 MB, CSV de 347 MB em latin-1, 622 mil convênios; o servidor responde 403 para dia sem arquivo; a página `/download-de-dados/convenios` lista o último dia). Colunas usadas: `NÚMERO CONVÊNIO`, `SITUAÇÃO CONVÊNIO` (mistura execução e prestação de contas: "Em execução", "Prestação de contas enviada para análise", "aprovada", "rejeitada", "Adimplente", "Normal"...), `NOME/CÓDIGO CONVENENTE` (CNPJ), objeto, valor do convênio, `VALOR LIBERADO`, contrapartida, vigência, e desde 18/10/2026 `NOME MUNICÍPIO` e `TIPO CONVENENTE` (município do convenente; só vale para "Administração Pública Municipal", "Administração Pública" e "Entidades Sem Fins Lucrativos": governo estadual, agente intermediário e pessoa física ficam sem município pelo nome). Convênio com Caixa como mandatária aparece também como pagamento ao município no `PorFavorecido` (em Gaspar, todos os convênios de emenda): por isso a deduplicação. Todos os 16.937 convênios das emendas desde 2023 estão no arquivo. Não há link por convênio verificável (o portal é protegido por WAF): o site liga à consulta do Portal e mostra o número.
- **Transferências especiais ("emendas Pix"):** API aberta do TransfereGov, `https://api.transferegov.gestao.gov.br/transferenciasespeciais/` (PostgREST, sem chave, 1.000 linhas por página, filtro `campo=eq.valor`, `Prefer: count=exact` dá o total, Swagger na raiz). Em 18/10/2026: 57.827 planos (desde 2020), 57.374 executores, 60.322 empenhos, 5.362 relatórios de gestão; desde então baixamos todos. O plano traz dados bancários (banco, agência, conta): não são guardados. Situação "CIENTE" = o beneficiário tomou ciência; as outras duas, IMPEDIDO e IMPEDIDO_REJEICAO_PLANO_TRABALHO (medido em 20/10/2026), são planos que não seguem e ficam fora do previsto no site, contados à parte; o valor do plano é **previsto**, o pago está no `PorFavorecido` (Pix pago aparece lá como "Transferências Especiais"). Há também `ordem_pagamento_ordem_bancaria_especial` (55 mil ordens), não usada. `plano_acao_especial.numero_emenda_parlamentar_plano_acao` é o mesmo código de 12 dígitos de `emenda.codigo` (3.425 de 3.425 emendas especiais da base têm plano; 42.891 planos, um por beneficiário); `executor_especial` traz o objeto, `empenho_especial` (situação 4, "Enviado") o valor empenhado e `relatorio_gestao_especial` a situação do relatório de gestão. O link oficial por plano é a própria consulta da API (`?codigo_plano_acao=eq.…`).
- **Fora do recorte:** o SICONV completo (`repositorio.dados.gov.br/seges/detru/siconv.zip`, 3,3 GB, aceita `Range`) tem prazos e a prestação de contas em detalhe, mas a situação do arquivo da CGU já cobre o essencial e é atualizada todo dia útil (o SICONV foi gerado em 17/07/2026).

## IBGE: municípios

- **URL:** `GET https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado` (5.571 municípios)
- Usado para ligar o município do favorecido (nome + UF) ao código IBGE, o mesmo que o ViaCEP devolve.

## TSE: candidaturas, bens e contas de campanha

- **URLs (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/` + `consulta_cand/consulta_cand_{ano}.zip`, `bem_candidato/bem_candidato_{ano}.zip` e `prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip`. Os dados ficam catalogados em `dadosabertos.tse.jus.br`.
- **Formato:** zip com um CSV por UF (`;`, latin-1, decimal com vírgula). O arquivo `_BRASIL` junta todos os estados e fica de fora, para não contar em dobro. O `_BR` traz os candidatos a presidente.
- **Turnos:** quem disputou o segundo turno aparece duas vezes em `consulta_cand`. Fica a linha do último turno.
- **2º turno de 2026 (presidente e governador):** em 18/10/2026 o `consulta_cand_2026` traz a linha do turno 2 com resultado `#NULO` (ainda sem apuração) e a do turno 1 com `DS_SIT_TOT_TURNO = "2º TURNO"`; a ordem das linhas no arquivo varia. Se o último turno não tem resultado, `normalizar` mantém o "2º TURNO" do 1º turno. Em 2026 a carga guarda, além de eleitos e parlamentares, as chapas (titular e vice) de presidente e governador nessa situação (`disputa_2_turno`): 2 chapas à presidência e 12 candidaturas de governador em 6 estados (AC, AM, DF, ES, RN, TO). O vice não tem prestação de contas nem votos próprios (vêm no titular da chapa). Quando o TSE publicar o resultado do 2º turno, recarregar `tse_candidaturas` 2026 atualiza a situação. A prestação de contas e os votos do 1º turno de 2026 já estão publicados (arquivos de 187 MB e 457 MB, gerados em 18/10/2026); `tse_bens`, `tse_campanha` e `tse_votos` entram em 2026 sem mudança de código, pois se penduram nas candidaturas guardadas.
- **Resultado do 2º turno na noite da votação (`tse_resultado_2_turno`):** os dados abertos de 2026 ficaram em 25/10 12h37, antes da apuração, e levam dias. O sistema de divulgação de resultados do TSE (o do site e do app "Resultados", sem captcha nem chave) publica JSON na hora. Caminhos reais de 2026 (os de 2022 em `dados-simplificados/.../-r.json` dão 404 em 2026):
  - config: `https://resultados.tse.jus.br/oficial/comum/config/ele-c.json`. Lista os pleitos (`pl[].c` = `ele2026`) e as eleições (`e[]`: `cd`, `t` = turno, `abr[].cd` = UF, `abr[].cp[]` = cargos). 2026: `6258` presidente 2º turno (`br`) e `6260` governador 2º turno (`am rn df es ac to`). O arquivo traz um `dg/hg` de geração; o JSON é UTF-8 com espaços estranhos antes dos `:`.
  - disputa: `/oficial/ele2026/{cd}/dados/{uf}/{uf}-c{cargo:04}-e{cd:06}-u.json`, por exemplo `.../ele2026/6258/dados/br/br-c0001-e006258-u.json` (presidente; governador é `c0003`, em `6260`). Há ainda `br-e006258-ab.json` (abrangências, por UF) e `config/mun-e006258-cm.json` (municípios), não usados.
  - campos usados: `and` ("f" = finalizado), `s.pstn` (% de seções totalizadas), `dt`/`ht` (data e hora da totalização, horário de Brasília), `carg[].agr[].par[].cand[]`: `sqcand` (igual ao `SQ_CANDIDATO` dos dados abertos), `n`, `e` ("s" eleito, "n" não eleito), `vap` (votos nominais válidos) e `vs[]` (o vice, com o próprio `sqcand`).
  - regra: só grava a disputa totalizada (`and = "f"`, 100% das seções, todos os candidatos com `e` = s/n); senão avisa e não grava (saída 3, sem registro em `fonte_ingestao`). Atualiza só candidaturas já guardadas (`situacao_turno`, `votos` do 2º turno, `data_eleicao`; vice herda a situação, sem votos). A carga fica em `fonte_ingestao` com `concluido_em` = momento da totalização do JSON, e o site (`/segundo-turno`: `resultado_fonte_url`, `resultado_atualizado_em`) mostra isso com o link do TSE.
  - convivência com os dados abertos: `tse_candidaturas`/`tse_votos` de 2026 que ainda tragam "2º TURNO" ou votos do 1º turno NÃO desfazem o resultado (mantêm situação, data e votos); quando os arquivos trouxerem o resultado, sobrescrevem com os mesmos valores. Rode `python -m ingestion.tse.resultado_2_turno` (ou `deploy/vps/agenda/tse.sh --resultado-2-turno`). Frequência: manual, na noite da eleição e até os dados abertos saírem.
- **Eleições antigas (1994 a 2014):** o `consulta_cand_{ano}.zip` existe para 1994, 1998, 2002, 2006, 2010 e 2014 (1 a 5 MB cada), com as mesmas colunas. De 1982 a 1990 o `consulta_cand` dá 404; para 1989 só há `votacao_candidato_uf_1989.zip` (TXT sem cabeçalho, 671 linhas, só presidente, sem nascimento nem título) e `consulta_legendas_1989.zip`, e não são lidos. Armadilhas:
  - **1994 não tem CPF nem título** (`-3`/`#NE`), mas tem data de nascimento. Entra só quem tem nome completo e nascimento idênticos aos de uma única pessoa já guardada e único no arquivo; a candidatura herda o título e o CPF dessa pessoa (`escolher_por_nome`). Cerca de 340 de 12 mil linhas.
  - **1998 a 2014 trazem o título** em quase todas as linhas: entra só quem tem título já presente em outra eleição guardada (mesmo filtro de 2016 e 2020). Rode da mais recente para a mais antiga.
  - **`SQ_CANDIDATO` se repete em 2002 e 2006** (é sequencial por UF): a chave da candidatura nesses anos é `<UF>-<SQ>`, igual nos arquivos de candidaturas e de votação (`comum_tse.sq_candidato`). Em 2002 a coluna `SG_UE` do arquivo de votação traz o município; por isso a chave usa `SG_UF`.
  - **Situação vazia (`#NULO`/`#NULO#`)** em 1994 a 2014 (3 a 8% das linhas; em 2006 o Lula e o Alckmin do 2º turno). `votos.py` preenche só as vazias com a situação do último turno do arquivo de votação (mesma chave); se lá também é `#NULO`, fica vazia. O TSE publica `#NULO` no 2º turno de 2006 (presidente) nos dois arquivos; `votos.py` aplica a regra do 2º turno (art. 77, §3º): com exatamente 2 candidatos na disputa, o mais votado é ELEITO e o outro NÃO ELEITO (empate ou mais de 2: vazio). Vices sem situação herdam a do titular da chapa. No arquivo de votação de 2006 as linhas de presidente trazem em `SG_UF` o estado da zona e o `BR` só em `SG_UE`; a chave usa `comum_tse.uf_da_disputa`.
  - **Rótulos antigos:** "MÉDIA" (1998, 2006, 2010) vira "ELEITO POR MÉDIA"; "RENÚNCIA/FALECIMENTO/CASSAÇÃO ANTES/APÓS DA ELEIÇÃO" (46 caracteres) é abreviado para caber na coluna (`SITUACOES_ANTIGAS`).
  - **Votação de 1998 (presidente):** os candidatos a presidente só aparecem no arquivo `_BRASIL` de `votacao_candidato_munzona_1998`, que a leitura ignora; ficam sem votos nesse ano.
- **CPF:** presente em 2018 e 2022. Em 2024, vem mascarado (`-4`) em todas as linhas, então as candidaturas municipais não se ligam aos parlamentares pelo CPF.
- **Ligação aos parlamentares:**
  - deputados: pelo CPF do detalhe do deputado na API da Câmara (a planilha `deputados.csv` traz o CPF vazio para muitos);
  - senadores: o Senado não publica CPF, então a ligação é por nome civil + UF entre candidatos a senador ou suplente, só quando é exata e única. Os 82 casaram.
- **Contas:** 300 MB em 2018, 475 MB em 2022 e 1,3 GB em 2024. Baixadas em fluxo para o disco. Usamos `receitas_candidatos_*` (`DS_FONTE_RECEITA` separa fundo eleitoral e fundo partidário; `DS_ORIGEM_RECEITA` dá a origem) e `despesas_contratadas_candidatos_*` (`DS_ORIGEM_DESPESA`).
- **Fotos:** a URL de fotos do DivulgaCandContas recusa acesso automatizado (403), mas os zips por UF em `cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_{UF}_div.zip` funcionam. O arquivo se chama `F{UF}{SQ}_div.jpg`. Os federais usam as fotos da Câmara e do Senado, exceto as chapas do 2º turno de 2026 (presidente, governador e vices), que têm foto da candidatura mesmo sendo parlamentares.
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
- **2016 tem formato antigo:** colunas até `SQ_CANDIDATO` e só `DS_MOTIVO_CASSACAO` (sem `NR_PROCESSO` nem `DS_TP_MOTIVO`). São 18.029 linhas, geradas em 18/02/2021.
- **Número do processo:** conferido pelo dígito verificador (módulo 97) e formatado como `NNNNNNN-DD.AAAA.J.TR.OOOO`. O `J` = 6 indica a Justiça Eleitoral, e o `TR` o tribunal regional.

## TSE: órgãos partidários

- **URL (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/orgao_partidario/orgao_partidario.zip` (219 MB; um CSV por partido, 40 arquivos, o do MDB com 317 MB aberto). No catálogo do TSE (`dadosabertos.tse.jus.br`, conjunto "delegados-partidarios") estão também `delegado_partidario.zip` e `perfil_filiacao_partidaria.zip` (só estatística).
- **Uma linha por membro e cargo:** partido, tipo do órgão (definitivo, provisório), abrangência (municipal, estadual, nacional), município e UF, cargo (`DS_CARGO_MEMBRO`), nome, **título de eleitor** (`NR_TITULO_ELEITORAL_MEMBRO`; às vezes `#NULO`), início e fim do exercício, situação do membro e do órgão (`VIGENTE` / `NÃO VIGENTE`).
- **Armadilhas:** datas com o ano truncado ("16/03/0208", "07/06/0011"); telefones `-1` e e-mails `#NULO`; o arquivo tem o histórico inteiro, então é preciso filtrar pelo que está vigente.
- **Catálogo do TSE:** a API CKAN (`/api/3/action/package_list`) lista 184 conjuntos. A busca `package_search` não devolve nada; use `package_list` e `package_show`.

## TSE: contas anuais dos partidos

- **URL (lote, sem chave):** `https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas_anual_partidaria/prestacao_contas_anual_partidaria_{ano}.zip`, exercícios de 2017 a 2026 (o corrente é parcial). O de 2024 tem 60 MB compactado e 944 MB aberto.
- **Arquivos:** `receita_anual_{ano}_{UF}.csv` e `despesa_anual_{ano}_{UF}.csv` por UF, mais `_BR` (diretório nacional) e `_BRASIL` (todos juntos). **Não some o `_BRASIL` com os outros.** Conferido em 2024: UFs + `_BR` = `_BRASIL` (receita R$ 8.729.070.518,00; despesa R$ 7.973.896.273,29). A carga lê todos menos o `_BRASIL`.
- **Formato:** CSV com `;`, latin-1, decimal com vírgula; nulos como `#NULO#` e `-1`. Há uma linha zerada, tudo nulo, para cada prestador sem movimento (ignoradas).
- **Receita:** esfera (`DS_TP_ESPERA_PARTIDARIA`, com o erro de grafia do arquivo), UF, município, partido, origem (`DS_TP_ORIGEM_DOACAO`), fonte do recurso, data, descrição e valor. Traz o **CPF completo e o nome** do doador pessoa física: nunca guardamos.
- **Despesa:** esfera (`DS_TP_ESFERA_PARTIDARIA`), partido, fornecedor (CPF ou CNPJ completo e nome), `DS_GASTO`, data, `VR_PAGAMENTO` e fonte da despesa (`DS_FONTE_DESPESA`).
- **Armadilhas:**
  - **Dupla contagem.** Das despesas de 2024, R$ 6,3 bi são "Transferências financeiras efetuadas" (para diretórios e candidaturas) e entram de novo como receita do outro lado. Em `partido_conta_soma.natureza` ficam separadas: despesa `gasto` (R$ 1,66 bi), `transferencia_diretorio` (R$ 1,54 bi) e `transferencia_candidato` (R$ 4,78 bi); receita `cota_tse`, `transferencia_partidaria`, `recurso_candidato` e `outra`.
  - **Caixa dos rótulos:** "Fundo Partidário" e "FUNDO PARTIDÁRIO" no mesmo arquivo; normalizados.
  - **`DS_GASTO` tem 321 variações** ("GRUPO - SUBGRUPO - FINALIDADE"). Ficamos com o grupo (72 categorias).
  - **A cota do FEFC na receita (R$ 4.953.833.495,86) difere em R$ 0,8 mi do total por partido do arquivo `fefc_fp` (R$ 4.954.676.301,46)**: são prestações diferentes; não forçamos a igualdade.
- **Conferência de 2024** (cotas do TSE ao diretório nacional): Fundo Partidário R$ 1.265.998.940,46 (PL 235,1 mi, PT 146,3 mi, União 116,6 mi) e FEFC R$ 4.953.833.495,86, em 12 meses.
- **O que se guarda** (coleta mínima, `guarda = "somas"`, `bruto = "recorte"`): `partido_conta_soma` (partido × esfera × UF × ano × fonte do recurso × natureza × categoria; 31,8 mil linhas, 11 MB em 2024), `partido_cota_mensal` (cotas do TSE por partido e mês) e `partido_despesa_vinculada` (despesas pagas a CNPJ que está em `sancao_empresa` ou `socio_pessoa`, ou a pessoa da base ligada pelo CPF; o CPF não é gravado). O zip vira manifesto.
- **Frequência:** mensal; exercícios 2023 a 2026. Exercício ainda não publicado (404) não é erro.

## TSE: FEFC e Fundo Partidário por gênero e cor ou raça

- **URL:** `https://cdn.tse.jus.br/estatistica/sead/odsele/fefc_fp/fefc_fp_{ano}.zip`, com 2020, 2022 e 2024 (2018 e 2026 dão 404). Quatro CSVs: `fefc_genero`, `fefc_cor_raca`, `fp_genero` e `fp_cor_raca` (os de FP têm 91 mil e 182 mil linhas, uma por diretório).
- **Armadilha:** `VR_PARTIDO_FEFC` e `VR_DESPESA_DIRETORIO_FP` são o total do partido (ou do diretório) e **se repetem** em cada linha de gênero ou cor. Somar a coluna conta em dobro. Guardamos `valor_recebido` (aditivo) e, no FEFC, o `valor_partido` (um valor por partido; ver `partido_fefc_fp`). O total do diretório no FP não é guardado.
- **Conferência de 2024:** `VR_PARTIDO_FEFC` por partido soma R$ 4.954.676.301,46; recebido por gênero R$ 4.781.075.707,10; FP recebido R$ 245.144.288,35.
- **O que se guarda:** FEFC como vem (partido × gênero, e × cor ou raça); FP somado por partido × esfera × gênero (× cor). 696 linhas em 2024.

## CGU: sanções (CEIS, CNEP e CEAF)

- **URL (lote diário, sem chave):** `https://portaldatransparencia.gov.br/download-de-dados/{ceis|cnep|ceaf}/{AAAAMMDD}`, que redireciona para `dadosabertos-download.cgu.gov.br/.../{AAAAMMDD}_{CEIS|CNEP|CEAF}.zip`. Também há `cepim` e `acordos-leniencia` (só empresas e entidades; catalogados, sem coleta).
- **Tamanho (08/10/2026):** CEIS 3,4 MB (23.721 sanções, 9.092 a pessoas físicas), CNEP 0,2 MB (1.827; 28 a pessoas físicas), CEAF 0,5 MB (4.066 expulsões).
- **Formato:** um CSV por zip, `;`, latin-1. Colunas com acento ("CÓDIGO DA SANÇÃO", "NÚMERO DO PROCESSO"...); CEIS e CNEP com as mesmas colunas (o CNEP tem "VALOR DA MULTA"); o CEAF tem cargo e órgão de lotação. "Sem Informação" significa vazio.
- **CPF:** completo no CEIS e no CNEP (pessoa física, `TIPO DE PESSOA` = F); mascarado no CEAF (`***.918.517-**`).
- **Origem:** 7.075 das 9.092 sanções a pessoas físicas no CEIS vêm do CNJ: são condenações por improbidade (Lei 8.429), registradas como "Impedimento/proibição de contratar".
- **Fundamentação legal:** texto longo de cada norma, vários itens separados por `;` ou `;;`. Guardamos só "norma - artigo" de cada item.
- **Número do processo:** pode ser número único do CNJ (formatado) ou número de processo administrativo (ex.: `10768.000360/2014-05`), guardado como veio.
- **Arquivo do dia ainda não publicado:** o servidor de download responde 403 (não 404). A carga tenta os dias anteriores, até 7.
- **Páginas de detalhe** (`/sancoes/ceis/{código}`) recusam acesso automático (405). O link da fonte é a página de download do cadastro, e o código da sanção vai no texto.

## Portal da Transparência: servidores federais (cargos de confiança) e viagens a serviço

Reconhecimento de 11/10/2026. As duas fontes são arquivos em lote, sem chave (a chave da API do Portal não é usada).

- **Servidores (mensal):** `https://portaldatransparencia.gov.br/download-de-dados/servidores/{AAAAMM}_{origem}`, que redireciona para `dadosabertos-download.cgu.gov.br/.../servidores/{AAAAMM}_{origem}.zip`. As origens são `Servidores_SIAPE`, `Servidores_BACEN`, `Militares`, `Aposentados_*`, `Pensionistas_*` e outras; usamos só `Servidores_SIAPE`. O mês mais recente sai da própria página de downloads (`arquivos.push({"ano","mes","origem"})`); agosto/2026 foi publicado em 09/10/2026. **O nome sem a origem (`servidores/202608`) responde 403.**
- **Tamanho (agosto/2026):** ZIP de 83 MB com `Cadastro` (446 MB descompactado, 780.670 linhas), `Remuneracao` (169 MB), `Afastamentos` e `Observacoes`. Lido em fluxo (~9 s).
- **Formato do Cadastro:** `;`, latin-1. Colunas usadas: `Id_SERVIDOR_PORTAL`, `NOME`, `CPF` (**mascarado, `***.123.456-**`**; 35.607 linhas sem CPF), `SIGLA_FUNCAO`, `NIVEL_FUNCAO`, `FUNCAO`, `ATIVIDADE`, `ORG_EXERCICIO`, `ORGSUP_EXERCICIO`, `UF_EXERCICIO`, `SITUACAO_VINCULO`, `DATA_INGRESSO_CARGOFUNCAO`, `DATA_NOMEACAO_CARGOFUNCAO`. Uma linha por vínculo.
- **Cargo de confiança** é a linha com `SIGLA_FUNCAO` em `CCX` (cargo comissionado executivo, o antigo DAS/CCE), `FEX` (função comissionada executiva, o antigo FCPE/FCE), `CD` (cargo de direção das universidades), `CGE`, `CCT`, `CCD`, `CCH`, `CTE`, `CA`, `PCC`, `EC`, `PFC`, `DAS`, `FCE`, `FCPE`, `CCE`, `NE` e `FAA`. Ficam de fora as funções gratificadas (`FG`, `GF`, `FGR`...), as coordenações de curso (`FUC`) e as gratificações de gabinete militar. 640 mil linhas não têm função (`-1`).
- **Armadilha: ministros e secretários de Estado não aparecem como cargo de confiança no cadastro.** Camilo Santana, por exemplo, consta só com o cargo de carreira (analista ambiental). Nas viagens, o mesmo ministro vem com `Função = CNE-0001` ("Cargo de Natureza Especial"). O evento de cargo do SIAPE cobre os cargos de 2º escalão para baixo; o de ministro vem das viagens (seção abaixo).
- **Viagens (anual):** `https://portaldatransparencia.gov.br/download-de-dados/viagens/{AAAA}`, que redireciona para `.../viagens/{AAAA}_{AAAAMMDD}_Viagens.zip` (a data é a da última atualização: 20/09/2026). 2025: ZIP de 156 MB com `Viagem` (496 MB), `Pagamento`, `Passagem` e `Trecho`; 814.395 viagens (805.628 realizadas, 8.767 não realizadas). Só o `Viagem.csv` é lido (~10 s). Colunas: `Situação`, `CPF viajante` (`***.123.456-**`; estrangeiros vêm como `ID123456789`), `Nome`, `Cargo`, `Função`, `Período - Data de início`, `Valor diárias`, `Valor passagens`, `Valor devolução`, `Valor outros gastos`. Os nomes de coluna têm acento e variam de capitalização; a leitura os normaliza.
- **Bloqueio:** o Portal tem um WAF (AWS) que, depois de poucas dezenas de requisições seguidas ao mesmo IP, passa a responder 405 com a página "Human Verification" a qualquer download e a qualquer página interna, por alguns minutos. Não se contorna: a carga falha sem alterar nada e roda de novo na semana seguinte.
- **Ligação:** os 6 dígitos do meio do CPF mascarado + nome (`chave_nome`) igual, e uma única pessoa para a chave (regra forte `cpf_parcial_nome`, a mesma do CEAF). Pessoa sem CPF completo no banco não liga.
- **Link oficial:** o cargo aponta para `portaldatransparencia.gov.br/servidores/{Id_SERVIDOR_PORTAL}`; as viagens, para `portaldatransparencia.gov.br/viagens/consulta` (a página de detalhe da viagem não pôde ser verificada por causa do WAF).

### Cargo de natureza especial (ministros) pelas viagens

- **Onde está:** o cadastro SIAPE não traz o ministro como cargo de confiança, mas o `Viagem.csv` traz `Função = CNE-0001` ("Cargo de Natureza Especial") com o `Nome do órgão superior` (o ministério; o sufixo " - Unidades com vínculo direto" sai). Nenhum outro arquivo do Portal serve melhor: as origens de `download-de-dados/servidores` são só SIAPE, BACEN, militares, aposentados, pensionistas e honorários, sem agentes políticos. O `Cargo` da viagem é o cargo de carreira da pessoa (um diplomata vem como "Ministro de primeira classe"), não o de ministro: não é usado.
- **O que gravamos:** por pessoa x órgão superior, o período observado (primeira e última viagem realizada com a função), em `servidor_federal` com `origem = "viagens"` (`primeiro_mes` e `ultimo_mes` guardam essas duas datas; `id_portal` fica vazio). Acumula entre os anos carregados. Evento `cargo_federal` (fonte `cgu_viagens_cne`): "Exerceu cargo de natureza especial em <órgão> (registro de viagens a serviço, de <data> a <data>)", com a data da primeira viagem e o link `portaldatransparencia.gov.br/viagens/consulta`.
- **Limites:** o período é o das viagens, não o da posse nem o da saída (quem não viajou não aparece; quem viajou pouco tem período curto). O órgão é o do Portal hoje: ministérios extintos aparecem no sucessor (o Ministério do Trabalho e Previdência de 2021 consta como Fazenda; a Cidadania, como Desenvolvimento e Assistência Social).
- **Carga local (viagens de 2019 a 2026):** 55 registros de 44 pessoas da base, 55 eventos. Conferência à mão de cinco casos com o que a imprensa registrou: Sergio Moro (Justiça, 20/01/2019 a 23/03/2020; saiu em 24/04/2020), Marcos Pontes (Ciência e Tecnologia, 2019 a 03/2022), Tereza Cristina (Agricultura, 2019 a 03/2022; depois senadora), Flávio Dino (Justiça, 02/2023 a 01/2024; foi para o STF) e Rui Costa (Casa Civil, 01/2023 a 03/2026).

## Portal da Transparência: cartão de pagamento do governo federal (CPGF)

- **Arquivo (mensal):** `https://portaldatransparencia.gov.br/download-de-dados/cpgf/{AAAAMM}`, que redireciona para `dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/cpgf/{AAAAMM}_CPGF.zip`. ZIP de ~300 KB com um CSV (`;`, latin-1, 10 a 22 mil transações por mês). A página `download-de-dados/cpgf` lista os meses publicados (de 01/2013 a 08/2026 em 11/10/2026, com atraso de ~2 meses); pedir um mês não publicado devolve 405, igual ao bloqueio anti-robô.
- **Colunas:** órgão superior, órgão, unidade gestora, `ANO EXTRATO`, `MÊS EXTRATO`, `CPF PORTADOR` (`***.123.456-**`, ou `-2` / vazio), `NOME PORTADOR`, `CNPJ OU CPF FAVORECIDO`, `NOME FAVORECIDO`, `TRANSAÇÃO` ("COMPRA A/V - R$ - APRES", "SAQUE CASH/ATM BB"...), `DATA TRANSAÇÃO`, `VALOR TRANSAÇÃO` (decimal com vírgula, sem separador de milhar; estornos vêm negativos).
- **Ligação:** só o PORTADOR, pelos 6 dígitos do meio do CPF + nome igual e único na base (`cpf_parcial_nome`). **Portador sem CPF parcial (só o nome) não liga:** nome sozinho não é ligação forte (em 3 meses de 2025, 27 nomes de portadores igualam nomes da base e todos têm outros dígitos do meio: são homônimos). O favorecido (empresa ou pessoa que recebeu) não é lido.
- **O que gravamos:** `cpgf_portador_mes` (pessoa x órgão x ano x mês: transações, total e parte sacada em dinheiro; sem favorecido nem transação) e um evento `cartao_corporativo` por pessoa x órgão x ano na linha do tempo, com link `portaldatransparencia.gov.br/cartoes/consulta`. A carga troca o mês inteiro (idempotente).
- **Carga local (01/2023 a 08/2026):** 8 somas mensais de **2 portadores da base**, R$ 10,5 mil no total, 3 eventos. Cartão corporativo é de servidor, e a base é de políticos: poucos casos são esperados.
- **Bloqueio:** o WAF devolveu 405 depois de ~15 downloads seguidos, mesmo nesses arquivos pequenos; a carga espera alguns minutos e retoma (`--a-partir-de MÊS`). Sem argumento, a carga lê só os 3 últimos meses publicados.

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

## CGU: e-Agendas (agenda pública de agentes federais)

- **URL (lote, sem token):** `https://dadosabertos-download.cgu.gov.br/dados_e-agendas/dados_e-agendas.zip` (~205 MB, atualizado todo mês; verificado em 19/10/2026: 48 CSVs, `2022-10.csv` a `2026-09.csv`, 1.330.600 linhas). A API `eagendas.cgu.gov.br/api/v2` exige token gov.br e **não é necessária**; o catálogo antigo (`acesso = "pedido"`) estava errado.
- **Formato:** CSV UTF-8, tudo entre aspas, datas `dd-mm-aaaa`, horas `HH:MM`, ausência escrita `ND`. Colunas: Nome, Cargo/Função, Tipo de exercício (Titular, Eventual, "Em substituição - X"), Órgão/Entidade, Tipo de registro, ID do registro, Data/Hora de início e término, Origem, Destino, Forma de realização, Data da publicação, Última modificação, Assunto do Compromisso, Local, Participantes, Vinculações, Objetivos, Informações complementares, Detalhes.
- **Tipos de registro (arquivo todo):** Reunião 955.887; Evento 297.988; Audiência 33.626; Audiência pública 20.114; Afastamento 19.731 (só "fulano substitui sicrano": não carregamos); Viagem 2.992; Presentes e hospitalidades 262.
- **Uma linha por registro x agente:** o mesmo `ID do registro` se repete para cada agente que o declarou, e a coluna `Participantes` traz todos. O ID só é único junto com o tipo.
- **CPF só dentro de `Participantes`:** `NOME (CPF: ***.827.438-**) / CARGO / ÓRGÃO`, separados por ` | `; seções por ` || ` ("Agentes públicos participantes", "Agentes privados participantes", "Representantes de governo estrangeiro..."). Viagem, presente e afastamento não têm `Participantes`: a ligação do agente vem do mesmo nome visto com CPF em outro registro (duas passadas no arquivo).
- **Participantes privados:** texto livre, `Fulano representando FENATRAD`, `Fulano representando Presidente - Chevron Brasil`, `... representando - Presidente - Representando - Instituto X`, ou só um nome/"Solicitante". Guardamos só a entidade (último trecho depois de "representando" e do último " - "), nunca o nome da pessoa física.
- **Viagem/presente:** `Detalhes` traz "Hospitalidade(s) recebida(s)": tipo, item, valor e `Ofertante: Nome (CNPJ: ...)`. Ofertante com CPF vira "pessoa física". Há entidades HTML (`&gt;` em "REC&gt;POA").
- **Quem consta:** ministros, secretários, dirigentes de autarquias e reitores. O presidente da República não consta (nenhuma linha "Luiz Inácio"); o vice-presidente aparece como ministro do MDIC (2.338 linhas).
- **Ligação a `pessoa`:** CPF mascarado (6 dígitos do meio) + nome igual, único (regra forte `cpf_parcial_nome`, igual aos servidores). Em 19/10/2026, no banco de dev (72 mil pessoas, 54 mil com CPF): 534 nomes ligados, 70 pessoas com registro, 75.106 registros (reunião 49.026; evento 24.623; audiência 939; audiência pública 424; viagem 76; presente 18).
- **Frequência:** mensal (recarga integral).

## Tesouro Nacional: SICONFI (contas anuais dos municípios e dos estados)

- **API:** `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio={ano}&no_anexo={anexo}&id_ente={ibge}`. Exige `id_ente`: não há consulta em lote, então é uma por município, anexo e ano (cerca de 0,8 s cada, a partir do Brasil).
- **Anexos usados:** `DCA-Anexo I-C` (receitas; `cod_conta = TotalReceitas`, coluna "Receitas Brutas Realizadas") e `DCA-Anexo I-E` (despesa por função; coluna "Despesas Pagas", só as linhas de função no formato "10 - Saúde").
- **Armadilhas:**
  - o código `TotalDespesas` se repete em várias linhas, por isso o total é a soma das funções;
  - texto em UTF-8 com alguns caracteres quebrados;
  - nem todo município entrega: em 2024, 5.326 de 5.571 tinham declaração;
  - a API limita a taxa de consultas (responde 429; cerca de 1 em cada 5 consultas a partir do GitHub). A carga espera o tempo do `Retry-After` e tenta de novo; um ano completo leva uns 65 minutos.
  - **falha da API não é "sem despesa"**: até out/2026 a consulta que falhava (timeout, 5xx) virava lista vazia e a despesa ficava nula (em 2024: 405 municípios, São Paulo entre eles, apesar de a API ter a despesa paga). Agora a consulta distingue falha (None) de anexo vazio, refaz até 4 vezes e repete em até 3 rodadas só os municípios que falharam. Nulo que sobra é ausência real: 3 municípios de 2024 (2904902, 2930808, 4209508) entregaram o Anexo I-E sem a coluna "Despesas Pagas" (só empenhada/liquidada) ou vazio, e o site não mostra valor por habitante para eles (nunca R$ 0);
- **Estados (governador):** a mesma API e os mesmos anexos, com `id_ente` de 2 dígitos (código IBGE da UF: 35 = SP, 53 = DF); 27 entes, 54 consultas por ano, sem paginação (`hasMore` falso mesmo com 600+ itens). Mesmas regras: despesa paga "exceto intraorçamentárias" = soma das funções (SP 2024: R$ 312,0 bi, igual à linha "Despesas Exceto Intraorçamentárias"; as intraorçamentárias, R$ 16,9 bi, ficam de fora, como nos municípios), receita "Receitas Brutas Realizadas" do total. Em 2023 e 2024 os 27 estados entregaram, todos com despesa paga. Tabela `contas_estado`; fonte `siconfi_contas_estados`.
- **Receita própria e transferências da União (desde out/2026):** do mesmo Anexo I-C, coluna "Receitas Brutas Realizadas" (antes de qualquer dedução): `receita_propria` = `RO1.1.0.0.00.0.0` (Impostos, Taxas e Contribuições de Melhoria); `transf_uniao` = `RO1.7.1.0.00.0.0` (transferências correntes da União) + `RO2.4.1.0.00.0.0` (de capital; muitos municípios não têm a linha). Nulo (nunca zero) quando a conta não veio; a soma da União vale se ao menos uma das duas veio. São valores do município (regime de competência), não batem com o caixa do Tesouro, e o FPM/FPE aqui é bruto, antes da retenção do Fundeb.
- **Frequência:** anual, entregue até abril. Carga mensal.

## Receita Federal: arrecadação por estado

- **URL (lote, sem chave):** `https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv` (~2,4 MB, CSV de 2000 até o mês corrente). Guardamos de 2019 em diante em `arrecadacao_uf` (uf, ano, mês, `total`, `previdencia`). Módulo `ingestion/receita/arrecadacao_uf.py`; incremental (só baixa de novo se o arquivo mudou); apaga e reinsere os anos do arquivo.
- **Formato:** latin-1, `;`, colunas `Ano;Mês;UF;<44 tributos>`; mês por extenso com acento ("Março"); decimal com vírgula; célula vazia = zero; pode haver negativo.
- **Cálculo:** `total` = soma de todas as colunas de tributo (inclui RECEITA PREVIDENCIÁRIA, CPSSS e "ADMINISTRADAS POR OUTROS ÓRGÃOS"); `previdencia` = coluna RECEITA PREVIDENCIÁRIA. As colunas "- PRÓPRIA" e "- DEMAIS" da previdência vêm zeradas.
- **Conferência:** soma do Brasil em 2024 = R$ 2,651 tri (balanço da Receita: R$ 2,652 tri) e em 2023 = R$ 2,318 tri (idem). 2019: 1,537; 2022: 2,218; 2025: 2,856 tri.
- **Armadilhas:**
  - o servidor responde 401 a `Accept: application/json` (o padrão do nosso cliente); é negociação de conteúdo, não bloqueio, e o módulo pede `text/csv`;
  - arrecadação por **domicílio fiscal** do contribuinte (onde a empresa ou a pessoa declara), não onde a atividade acontece: SP, RJ e DF concentram sedes;
  - **DF entre fev/2025 e jan/2026:** a Receita registrou no DF boa parte da arrecadação do país (receita previdenciária do DF de ~R$ 2,5 bi/mês para ~R$ 18 bi/mês; DF 2024: R$ 184 bi, 2025: R$ 583 bi; total do Brasil 2025: R$ 2,856 tri). O número bate com a fonte e não é ajustado; qualquer tela por estado precisa dizer isso;
  - o ano corrente é parcial (2026 até julho em out/2026).
- **Frequência:** mensal.

## IBGE: população (estimativas e Censo)

- **API SIDRA (sem chave):** `https://apisidra.ibge.gov.br/values/t/6579/{n1|n3|n6}/all/v/9324/p/{ano}` (estimativa da população residente; Brasil, UF e município). 2022 vem do Censo: `.../t/9514/{nível}/all/v/93/p/2022/c2/6794/c287/100362/c286/113635` (total de sexo, idade e forma de declaração). Módulo `ingestion/ibge/populacao.py`, tabela `populacao_ibge` (código de 1, 2 ou 7 dígitos; origem `estimativa` ou `censo`).
- **Anos:** 2019, 2020, 2021, 2022 (Censo), 2024, 2025 e 2026 (publicado em out/2026). **2023 não existe** (o IBGE foi do Censo 2022 para a estimativa de 2024): fica sem valor, não se interpola. Ano ainda não publicado vem só com o cabeçalho e é ignorado.
- **Formato:** JSON, a primeira linha é o cabeçalho; `V` é texto; ausentes vêm como `...`, `-` ou `X` e não são guardados. O código `D1C` é o IBGE de 7 dígitos (município), 2 (UF) ou 1 (Brasil).
- **Conferência (aborta a carga se falhar):** soma das 27 UFs = Brasil e soma dos municípios = Brasil, em cada ano. Brasil: 2019 210.147.125; 2020 211.755.692; 2021 213.317.639; 2022 203.080.756 (Censo); 2024 212.583.750; 2025 213.421.037; 2026 214.211.951. Municípios: 5.570 até 2024 e 5.571 em 2025 e 2026.
- **Armadilha:** as estimativas de 2019 a 2021 usam outra base que o Censo 2022, então a série tem queda em 2022 (213 mi para 203 mi); não é erro.
- **Frequência:** mensal (ano novo aparece quando o IBGE publica).

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
- **Outros TCEs:** RS (abaixo, carregado) e MG (abaixo, bloqueado por reCAPTCHA).
- **Portais de fornecedores (Betha, CR2...):** não servem para carga automática. O Betha exige reCAPTCHA nas consultas, e o CR2 é um app sem API pública. Não contornamos captcha.

## TCE-RS: despesas das prefeituras e câmaras gaúchas

- **Portal:** `https://dados.tce.rs.gov.br/` (CKAN; a API `api/3/action/package_search` lista os conjuntos). Conjunto "Despesa orçamentária por empenhos", um por ano.
- **URL (lote, sem chave):** `https://dados.tce.rs.gov.br/dados/municipal/empenhos/{ano}.csv.zip` (também em `.7z`). O zip de 2025 tem 1,35 GB e um CSV de 14,7 GB (27 milhões de linhas); o de 2024, 1,28 GB. O download é rápido (cerca de 1 minuto) e a leitura em fluxo leva uns 5 minutos.
- **Formato:** `,`, UTF-8 com BOM, decimal com ponto, zip64. Uma linha por operação: `tipo_operacao` = `E` (empenho), `L` (liquidação) ou `P` (pagamento). Usamos só `P`.
- **Campos:**
  - `cd_orgao` e `nome_orgao` ("PM DE AGUDO", "CM DE AGUDO"); o arquivo **não traz código IBGE**;
  - `ano_empenho`, `ano_operacao`, `dt_operacao`;
  - `nm_credor`, `tp_pessoa` (`PJ` ou `PF`), `cnpj_cpf`;
  - `vl_pagamento`.
- **Cadastro de órgãos:** `https://dados.tce.rs.gov.br/dados/auxiliar/orgaos_auditados_rs.csv` liga `CD_ORGAO` a `CD_MUNICIPIO_IBGE`, com `ESFERA`, `SETOR_GOVERNAMENTAL` (EXECUTIVO, LEGISLATIVO, AUTARQUIA, FUNDAÇÃO, CONSÓRCIO ADMINISTRATIVO...) e o `CNPJ` do órgão. Vai junto no bruto (acrescentado ao zip baixado).
- **Armadilhas:**
  - o arquivo do ano traz o **histórico inteiro dos empenhos de anos anteriores** que ainda têm restos a pagar, inclusive pagamentos antigos (no de 2025, 700 mil pagamentos de 2024 e outros desde 2004). Filtramos `ano_operacao` igual ao ano do arquivo;
  - o total pago inclui os restos a pagar pagos no ano. Para conferir com o balancete de despesa do TCE-RS (`dados/municipal/balancete-despesa/{ano}/{cd_orgao}.csv`, coluna `VL_PAGO`), separe os pagamentos de empenhos do próprio ano (`ano_empenho` = ano): batem centavo a centavo;
  - **CNPJ sem zeros à esquerda** ("360305129220" é 00.360.305/1292-20, da Caixa; o Banco do Brasil chega a vir como "191"). Completamos com zeros e validamos os dígitos;
  - CPF com `tp_pessoa = PJ` (raro): quando o número é um CPF válido e não um CNPJ válido, vai para a linha das pessoas físicas;
  - a **folha de salários** aparece como credor PJ sem CNPJ ("FOLHA DE PAGAMENTO", "SERVIDORES MUNICIPAIS", "INATIVOS", "VEREADORES 17 LEGISLATURA", "F U N C I O N A R I O S") ou como pagamento ao CNPJ do próprio órgão ("MUNICIPIO DE PORTO ALEGRE" na prefeitura de Porto Alegre). Vira a linha "Folha de pagamento (salários)". Credores sem CNPJ com outros nomes ("PASEP", "INSS") ficam como fornecedores, sem documento;
  - há **estornos com valor negativo** em `vl_pagamento`; entram na soma;
  - consórcios intermunicipais estão cadastrados na cidade-sede; ficam de fora (R$ 729 milhões pagos em 2025).
- **Frequência:** o órgão envia por bimestre; o arquivo do ano é atualizado ao longo do ano seguinte (o de 2025 foi gerado em abril de 2026). Carga mensal.

> **CPF no nome (TCE-SP e TCE-RS):** MEI vem com o CNPJ correto e o CPF dentro do nome do credor ("FULANO 00594280079"). O dado tratado passa por `app.textos.sem_cpf` (a mesma limpeza vale para a cota parlamentar e o PNCP); o bruto fica como veio. Ver DECISOES, "CPF no nome de fornecedor".

## TCE-MG: despesas das prefeituras e câmaras mineiras (bloqueado)

- **Portal:** `https://dadosabertos.tce.mg.gov.br/` é um app Angular. Os arquivos saem da API `https://arabiasaudita.tce.mg.gov.br:8443/TCEMG-proxy-web/publico/apimoci/dados-abertos/dadosAbertos/...` (`buscarMunicipios`, `buscarOrgaos`, `baixarArquivo/{id}`).
- **Bloqueio:** toda chamada sem sessão responde **401**, e o app então manda o usuário para `TCEMG-proxy-web/login/captcha.jsf` (reCAPTCHA). O "Fiscalizando com o TCE" (`fiscalizandocomtce.tce.mg.gov.br`) usa o mesmo proxy, também com 401 e reCAPTCHA (`captcha_simples.jsf`). Testado em 09/10/2026.
- **Canais alternativos testados em 09/10/2026 (nenhum serve):**
  - `https://www.tce.mg.gov.br/Dados-abertos` só leva a `dadosabertos.tce.mg.gov.br` e ao Portal SICOM; `https://portalsicom1.tce.mg.gov.br/` (WordPress, robots.txt só veda `/wp-admin/`) é documentação do sistema, sem dados. `sicom.tce.mg.gov.br` não resolve e `ftp.tce.mg.gov.br` recusa a conexão.
  - `https://dadosabertos.tce.mg.gov.br/robots.txt` responde 404 (Tomcat). O certificado de `dadosabertos` e de `arabiasaudita:8443` vem sem a cadeia completa (o httpx recusa); `buscarMunicipios` sem sessão responde 401 sem corpo.
  - Portal de dados abertos do Estado (`dados.mg.gov.br`, CKAN 2.9.5, API `package_search`): 23 conjuntos achados por busca de "empenho", "despesa", "municípios", "pagamento", "credor" etc., todos do **Poder Executivo estadual** (CGE: despesa por empenho do Estado, restos a pagar, diárias, repasses do Estado aos municípios; SEPLAG: SISOR). Nenhum traz empenho ou pagamento dos municípios; nenhum conjunto do TCE-MG. (Com `curl` puro o site responde 403; com o User-Agent do projeto, 200.)
  - Base dos Dados (GraphQL público, 1.291 conjuntos varridos): não existe `br_tce_mg`; o que há é SICONFI (sem credor), `despesas_publicas` (só federal, CGU), `receitas_e_despesas_dos_municipios_de_sao_paulo` e `rs_tce_iegm`. Nada de municípios mineiros por credor.
  - Brasil.IO: nenhum conjunto de despesa municipal (`gastos-diretos` é do governo federal; `gastos-deputados` é da Câmara). A API do Brasil.IO exige token.
  - SICONFI/Tesouro: dados por conta e função, sem credor.
  - Portais municipais em lote: sem padrão comum aos 853 municípios (fornecedores de sistemas diferentes); não avaliado município a município.
- **Pedido:** redigido em `docs/pedidos/tce_mg.md` (LAI ao TCE-MG), a enviar.
- **Situação:** não contornamos captcha. A fonte fica catalogada em `fontes.toml` (`tce_mg`, `acesso = "pedido"`) até o TCE-MG oferecer acesso sem captcha ou responder a um pedido.

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
- **Matéria das votações (desde 21/10/2026):** `registrovotacao.materia` traz o id da matéria em 100% das nominais medidas. Guardamos `votacao_local.materia_id_externo` e a ementa da ficha `materia/materialegislativa/{id}/` (`materia_ementa`; uma chamada por matéria dentro da carga, com cache; as matérias que o lote de projetos já leu não pedem nova chamada; ficha 404/5xx ou fechada deixa a votação sem ementa). O rótulo só é trocado pelo `__str__` da ficha quando o texto do registro não segue o padrão. `projeto_local_id` liga à linha de `projeto_local` da mesma casa com o mesmo `id_externo` (a menor, se vários vereadores assinam); a maioria das matérias votadas nominalmente é veto, requerimento ou projeto do Executivo e fica sem vínculo. O SAPL não guarda bruto por casa hoje (`arquivo_raw = "(não guardado)"`), então as fichas não têm `data/raw/`.
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
  - `deputados/despesas_gabinetes.xml` (164 MB, sem compactação, desde 2015);
  - `processo_legislativo/comissoes_permanentes_votacoes.xml` (65 MB, sem compactação, desde 2005; 226 mil votos): um voto por linha, com `IdReuniao`, `IdPauta`, `IdComissao`, `IdDocumento` (a matéria), `IdDeputado`, `Deputado` (nome), `Voto` (texto livre, às vezes com espaço no fim) e `TipoVoto` (F favorável ao parecer, P favorável à proposição, C contrário ao parecer, T contrário à proposição, S voto em separado, A abstenção, B em branco);
  - `processo_legislativo/comissoes_permanentes_reunioes.xml` (3 MB): `IdReuniao`, `Data`, `IdComissao`, `Situacao` (REALIZADA, SEM QUORUM, CANCELADA...);
  - `processo_legislativo/comissoes.xml`: `IdComissao`, `NomeComissao`, `SiglaComissao`.
- **Armadilhas:**
  - a autoria usa o `IdSPL` do deputado (casa 94 de 94); `IdDeputado` casa só em parte; os gastos usam a `Matricula`;
  - a categoria do gasto vem com uma letra na frente ("A - COMBUSTÍVEIS E LUBRIFICANTES");
  - a rota `/api/deputadoPresenca` citada no catálogo responde 404; a presença em Plenário só existe num formulário do site, e a página de votações em Plenário responde 403 a acesso automatizado;
  - nos votos de comissão, o campo `IdDeputado` traz o `IdSPL`, não o `IdDeputado` de `deputados.xml` (casa 83 dos 88 votantes de 2025–2026 pelo `IdSPL` e só 1 pelo `IdDeputado`; os 5 restantes não estão mais no cargo);
  - o arquivo de votos não tem data: ela vem da reunião. 3 reuniões citadas nos votos (antigas) não estão no arquivo de reuniões;
  - "Não registrou voto" vem com `TipoVoto` F (favorável): não pode ser contado como voto;
  - uma votação é a matéria (`IdDocumento`) numa reunião (`IdReuniao`); a mesma matéria pode ser votada em várias reuniões e comissões. Em 2025–2026 (até 21/07/2026): 2.769 votações e 22.287 votos; 93 dos 2.467 documentos votados não estão em `proposituras.zip`;
  - uma reunião marcada "SEM QUORUM" (29/04/2026, comissão 12451) tem 313 votos registrados;
  - a presença nas reuniões das comissões está em `comissoes_permanentes_presencas.xml` (8 MB, `IdReuniao`, `DataReuniao`, `IdDeputado`, `SiglaComissao`; não aparece no catálogo, mas existe no repositório) e a composição das comissões em `comissoes_membros.xml`; ainda não usadas.
- **Frequência:** semanal, junto com as câmaras.

## ALEPE: Assembleia Legislativa de Pernambuco

- **API (sem chave):** `https://dadosabertos.alepe.pe.gov.br/api/v1/` (documentação em `/?documentacao=...`). Rotas: `parlamentares/` (JSON: `nomeParlamentar`, `partido`; 49, todas as cadeiras), `proposicoes/{projetos|indicacoes|requerimentos}/?ano=` (XML), `cargos`, `contratos`, `licitacoes`, `lotacoes`, `remuneracao` e `servidores`. **Sem** votações, presença ou gastos do gabinete (testado: `votacoes`, `presenca`, `despesas` dão 404).
- **Proposições (XML):** `docid`, `numero`, `ano`, `tipo` ("PROJETO DE LEI ORDINÁRIA", "PROPOSTA DE EMENDA A CONSTITUIÇÃO"…), `ementa`, `dataPublicacao` (`dd/mm/aaaa`) e `<autores>` com `nome` e `tipo` (`DEPUTADO`, `EXTERNO` para o Executivo, `COMISSAO`). O autor deputado vem pelo **mesmo nome parlamentar** da lista de deputados. Em 2026 (até outubro): 629 projetos, 1,7 MB de indicações e 1,4 MB de requerimentos.
- **Armadilhas:** a ementa das indicações e dos requerimentos vem em HTML escapado duas vezes (`&lt;p&gt;Indicamos &amp;agrave;…`). A rota sem o tipo (`proposicoes/`) devolve erro em XML com as rotas válidas.
- **Link de cada proposição:** `https://www.alepe.pe.gov.br/proposicao-texto-completo/?docid={docid}`.
- **Levantamento das outras assembleias** (09/10/2026): ALERJ, ALRS e ALBA não têm portal de dados abertos achável (endereços testados dão 404, 500 ou não resolvem). A API da ALEP (`webservices.assembleia.pr.leg.br/api/public/`) usa certificado HTTPS autoassinado: desligar a verificação tiraria a garantia de que o dado vem da Assembleia. (Atualização de 19/10/2026: a API só tem proposições; deputados, presença e votos vêm do site e do Portal da Transparência, ver "ALEP" abaixo.) Um estudo de 2025 ("Democracia em Formato JSON", preprint SciELO) compara as APIs das 26 assembleias e da CLDF; é o ponto de partida do levantamento casa a casa.

## CLDF: Câmara Legislativa do Distrito Federal

- **Catálogo (CKAN):** `https://dados.cl.df.gov.br/api/3/action/package_list`: 28 conjuntos, entre eles `proposicoes`, `relacao-nominal-de-deputados-e-servidores`, `verbas-indenizatorias` (XLSX por ano; 2026 até agosto), `emendas-parlamentares` e `empresas-sancionadas`.
- **API pública do Processo Legislativo Eletrônico** (documentada no conjunto `proposicoes`): `https://ple.cl.df.gov.br/pleservico/api/public`, sem autenticação.
  - `GET /autor/listar`: 227 autores; 154 do tipo PARLAMENTAR, 24 com situação ATIVO, com o nome como "Deputado Fábio Felix" (às vezes com espaço no fim). O partido não vem preenchido.
  - `POST /proposicao/filter?page=&size=&sort=`, com corpo `{"ano", "dataInicio", "dataFim", "tipoProposicao", "autoria"...}`. A autoria vem em texto ("Deputado X, Deputada Y", às vezes repetida). O campo `last` não indica de forma confiável a última página: usamos `totalPages`. Consultamos mês a mês; a soma dos meses bate com o total do ano (4.921 em 2025).
  - `GET /proposicao/{id}`, `/autores`, `/tramitacoes` e `/documentos`.
- **Sem votos e sem presença** na API.
- **Verbas indenizatórias** (`verbas-indenizatorias` no catálogo): um XLSX por ano (até 2024 também em CSV). Cada linha é um comprovante: deputado, **CPF do deputado**, fornecedor (nome, CNPJ ou CPF), número do comprovante, data, valor, classificação e observação.
  - Em 2026: colunas `NOME_PARLAMENTAR`, `CPF_PARLAMENTAR`, `DATA_COMPROVANTE` (número de série do Excel), `VALOR_DESPESA`, `CLASSIFICACAO`.
  - Em 2025: `Nome do(a) Deputado(a)`, `CPF do(a) Deputado(a)`, `Data do Recibo/NF` (mês/dia/ano), `Valor`, `Classificação`.
  - Só 10 a 11 dos 24 deputados aparecem nos arquivos (11 em 2025, 10 em 2026); 9 entram na soma por mês, porque Fábio Felix não tem data em nenhuma linha e Robério Negreiros em 2025 vem com colunas deslocadas. O CPF do XLSX de 2025 é corrompido em parte das linhas (12 dígitos, sequências); ver DECISOES (20/10/2026).
  - **Armadilha (20/10/2026): o rótulo do catálogo mente.** O recurso de 2026 ("Até Agosto") está como `XLSX`, mas o arquivo é `ckan_csv_corrigido.csv`: CSV UTF-8 com BOM, `;`, com coluna extra `ID_REGISTRO`, valor `R$ 5.600,00` e data `02/01/2026 00:00`. O conector tratava tudo como XLSX e o job caiu com `BadZipFile`. Agora o formato vem do conteúdo (zip `PK` = XLSX; senão CSV; HTML ou vazio = erro). Um ano ilegível vira aviso e os outros carregam; se nenhum ano vier, a carga aborta. O bruto de cada ano fica em `data/raw/cldf/verbas_AAAA_*` e `python -m ingestion.assembleias.cldf --de-raw data/raw/cldf` reprocessa as verbas sem baixá-las (deputados e proposições ainda vêm da rede).
  - **Sujeira do CSV de 2026:** 58 de 276 linhas sem data (ficam de fora, pois o gasto é por mês); datas misturadas no mesmo arquivo (`02/01/2026` dia/mês e `8/20/2026` mês/dia: vale a outra ordem quando a primeira é impossível); 5 valores digitados como `R$ 5,500,00` (lidos como 5.500,00). Os arquivos de 2024 e 2025 também existem em XLSX; o de 2024 tem ainda um CSV "até maio".

## ALESC: Assembleia Legislativa de Santa Catarina

- **Sem API nem exportação.** Lemos as páginas públicas, uma por vez, com pausa:
  - deputados: `https://www.alesc.sc.gov.br/deputados` (cartões com nome, partido e foto; 40);
  - proposições: o e-Legis, `https://portalelegis.alesc.sc.gov.br/proposicoes/processo-legislativo` (projetos) e `/proposicoes/atividade-parlamentar` (requerimentos, indicações, moções, pedidos de informação…), 10 por página, `?inicio=AAAA-MM-DD&fim=AAAA-MM-DD&page=N`. O parâmetro `ano` é ignorado: o formulário converte o ano em `inicio` e `fim` no navegador.
- **Volume (2025 e 2026 até outubro):** ~1.760 proposições do processo legislativo e ~11.900 da atividade parlamentar, ou cerca de 1.370 páginas.
- **Cada cartão:** número ("PL./0640/2026", "RQS/0012/2026"), ementa, data de entrada, autoria ("Deputado Altair Silva", às vezes vários), setor e situação atual.
- **Siglas** (conferidas pelo filtro de tipo do próprio e-Legis): PL. projeto de lei, PLC complementar, PEC, PRS resolução, PDL decreto legislativo, RQS requerimento, RCC requerimento de comissões, RQC requerimento de frente/fórum/CPI/comissão mista, IND indicação, MOC moção, PIC pedido de informação, OFL ofício legislativo, PSA proposta de sustação de ato.
- **Gastos do gabinete (CSV anual, 19/10/2026):** `https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/AAAA` (o endereço antigo `gabinetes_csv.php?ano=AAAA` responde 301 para ele). O `robots.txt` da Transparência permite (só veda os endpoints AJAX `/deputados/contracheque/`, `/pagamentos/view/`, `/gabinetes-parlamentares/view/`). UTF-8 com BOM, separador `;`, valor com vírgula decimal e ponto de milhar.
  - Colunas: `Verba`, `Descrição`, `Conta`, `Favorecido`, `Trecho`, `Data de Referência` (dd/mm/aaaa), `Valor`. Uma linha por pagamento; 2025 tem 15.620 linhas e R$ 19,49 mi.
  - **Verba** são 12 grupos (Diárias, Reembolsos, Passagens, Telefone, Veículos, Almoxarifado, TV a cabo, Aluguel, Correspondência, Gráfica, Combustíveis, Inscrição); **Descrição** tem ~40 (ex.: "Diárias - Funcionários", "Devolução Diária Deputado"). Guardamos a Descrição como categoria.
  - **Conta** é o nome do deputado (às vezes com apelido entre parênteses, "Ana Paula da Silva (Paulinha)", ou espaço sobrando). Há 46 contas em 2025: os 40 em exercício e ex-deputados/suplentes. Em 2025 ligaram 37 contas (R$ 17,90 mi); 9 ficam de fora (Carlos Henrique Lima, Emerson Stein, Marquito, Adilson Girardi, Dirce Heiderscheidt, Thiago Morastoni, Jeferson Cardozo, Janice Krasniack, Edilson Massocco) e 3 deputados atuais não têm conta no ano (Carolline Sardá e Jerry Comper, que assumiram depois, e Sargento Lima, cujo nome civil não é seguro ligar).
  - **Armadilhas:** devolução de diária vem com valor **negativo** (478 linhas em 2025) e é somada; "Diárias - Funcionários" são 7.437 das 15.620 linhas (diárias de servidores do gabinete, não do deputado); `Favorecido` e `Trecho` trazem nomes de pessoas físicas e destinos de viagem e **não são guardados** (coleta mínima). Janeiro de 2025 tem poucas linhas (455).
- **Presença em plenário (e-Legis):** `https://portalelegis.alesc.sc.gov.br/sessoes-plenarias?page=N` lista as sessões (10 por página, da mais recente para a mais antiga, 623 desde 2023) com data e situação ("Realizada", "Agendada", "Horário regimental"); `/sessoes-plenarias/{id}/presenca` traz uma tabela nome x situação ("Presente" ou "Ausência justificada"), 40 linhas por sessão (menos nas antigas). Só conta a sessão "Realizada" (uma "Agendada" já veio com a lista preenchida, e a de "Horário regimental" veio vazia). Guardamos o total de sessões em que o deputado constava e as presenças; em 2025 e 2026 (até 19/10): 310 sessões, 308 realizadas, 40 de 40 deputados com presença (Carolline Sardá, que assumiu há pouco, 14 de 15).
- **Votos nominais (20/10/2026):** `https://portalelegis.alesc.sc.gov.br/sessoes-plenarias/{id}/ordem-do-dia` lista os itens votados, cada um com o selo "Votação nominal" ou "Votação simbólica" e o resultado (Aprovado/Rejeitado); nos nominais o botão "Extrato de votação" chama `GET /extrato-votacao/{código}` (htmx), que devolve um fragmento HTML com deputado e voto (Sim/Não/…). Essa rota responde **405 a um GET comum e 200 à chamada AJAX** com o cabeçalho `X-Requested-With: XMLHttpRequest`, que o script do próprio site (`ajax-header.js`) põe em toda chamada; não há captcha, login nem robots (`/robots.txt` é 404). Mantemos o User-Agent do projeto. Em 2025-2026: 310 sessões, 50 com votação nominal, 101 votações lidas (96 aprovadas, 5 rejeitadas), 2.623 votos ligados. O extrato lista só quem votou (sem "ausente"); o título dele mostra a situação atual da matéria, não o resultado, que vem do cartão da Ordem do Dia. Voto só vai ao deputado de nome igual ao do site ou do TSE. Bruto: zip com as ordens do dia e os extratos em `data/raw/alesc/votacoes_*.zip` (`--votos-de-raw`). Custo: ~310 + ~100 requisições por carga. **Matéria votada (21/10/2026):** o cartão da Ordem do Dia liga a proposição por `<a href="/proposicoes/{código}">`; esse código (5 caracteres, ex. `KgRaQ`) é o mesmo `id_externo` do projeto na lista de proposições, então vira `votacao_local.materia_id_externo` e liga a `projeto_local` quando o deputado atual é autor. A ementa vem do próprio cartão (sem requisição extra). ALEP e ALRS só dão número e ementa em texto: sem id.

## SC Transferências (CGE/SC): emendas impositivas da ALESC

- **Fonte:** Controladoria-Geral do Estado de Santa Catarina, sistema SC Transferências. Página: `https://consultas.sctransferencias.cge.sc.gov.br/pesquisa-detalhada/emendas` (aplicação React; a mesma API GraphQL `sctransf-api.prod.okd4.ciasc.sc.gov.br/graphql`, consulta `dadosEmendas`, alimenta a tela). Público, sem login nem captcha; o User-Agent do projeto é aceito. Módulo `ingestion.emendas_estaduais.sc`, fonte `sctransferencias_emendas`.
- **Arquivos usados (um pedido cada, com pausa de 1 s):**
  - emendas: `GET https://sctransf-api.prod.okd4.ciasc.sc.gov.br/csv/emendas` (o botão "Baixar CSV"; sem parâmetros = todas). CSV UTF-8 **com BOM**, `;`, vírgula decimal, ~1,1 MB; 2.490 linhas em 19/10/2026 (2022: 290, 2023: 260, 2024: 588, 2025: 795, 2026: 557). Colunas: `Número Unidade Gestora`, `Concedente` ("Fundo Estadual de Saúde (FES) (480091)"), `Nº Transferência` ("2024TR002516", vazio sem transferência), `Número Processo SGPe`, `Beneficiário` ("NOME (82.804.642/0001-08)"), `Natureza Jurídica Proponente`, `Instrumento` (Termo de Fomento, Convênio, Termo de Colaboração), `Município`, `Situação Proposta`, `Situação Transferência`, `Nº Programa Transferência`, `Nº Proposta`, `Valor da Transferência` (inclui contrapartida), `Valor da Contrapartida`, `Valor de Outros Recursos`, `Valor Repassado`, `Valor a Repassar`, `Nº Emenda` ("2024EP002132"), `Valor Emenda`, `Valor Atualizado`, `Deputado`, `Objeto Emenda`, `Ano`.
  - razão financeiro: `https://arquivos.transparencia.sc.gov.br/sctransferencias/dados-abertos/dados_financeiros_AAAA.zip` (página "Dados abertos" do sistema; existe de 2019 em diante; usamos 2022 a ano atual). Um CSV latin-1, `;`, ~15 mil linhas e ~17 MB por ano (1 MB zipado), de **todas** as transferências voluntárias, uma linha por movimento: empenho, liquidação ou pagamento em linhas separadas (`vlempenho`, `vlliquidacao`, `vlpago`), anulações e estornos com valor negativo. Traz `nuemenda`, `vlemenda` e `nmdeputado` quando há emenda, mas sem CNPJ do beneficiário.
- **Armadilhas:**
  - a chave é `Nº Proposta`: o `Nº Emenda` se repete em 65 emendas (proposta refeita, cancelada ou dividida, até 4 propostas). O valor da emenda se repete nessas linhas: some uma vez por emenda;
  - `Valor Atualizado` difere de `Valor Emenda` em 11 linhas (remanejamento; ex.: 2023EP001646, de 200 mil para 800 mil): usamos o atualizado;
  - `Valor Repassado` vazio quando ainda não há transferência; a soma de `vlpago` do razão difere do repassado em 111 de 1.515 transferências conferidas (devoluções e estornos): o pago é o repassado; 118 transferências não têm linha no razão (empenhado nulo);
  - `Município` é o do **beneficiário**, em maiúsculas e sem acento ("BRACO DO NORTE", "GRAO-PARA", "HERVAL DOESTE"); 5 nomes são de fora de SC (São José dos Campos, Candói, Brasília, Guaratinguetá, São Joaquim da Barra; 21 propostas, R$ 4,64 mi pagos) e ficam sem código IBGE;
  - `Deputado` traz o nome civil em maiúsculas, às vezes o nome de urna ("PAULINHA"), apelido entre parênteses ("MARCOS JOSÉ ABREU ( MARQUITO)") e cinco bancadas regionais ("BANCADA DO OESTE");
  - só entram emendas executadas por transferência voluntária no sistema (entidades sem fins lucrativos 1.965 linhas, APAEs 442, consórcios 58, administração indireta 21; prefeituras só 2). Repasses fundo a fundo e às prefeituras não estão aqui.
- **Conferência (carga no acervo, 19/10/2026):** 2.490 propostas, 2.420 emendas; pago R$ 299,03 mi (2022: 50,28; 2023: 52,77; 2024: 80,67; 2025: 97,89; 2026: 17,42); 53 de 59 autores individuais ligados a pessoa. Gaspar (4205902): R$ 1.000.000 pagos em 5 emendas de 2023–2024 (Romildo Titon 500 mil ao Clube Atlético Tupi; Jerry Comper 150 mil ao Clube de Bocha Belchior; Maurício Eskudlark 150 mil e Napoleão Bernardes 100 mil à APAE de Gaspar; Nilso Berlanda 100 mil à Rede Feminina de Combate ao Câncer); o valor repassado de 3 delas foi conferido também na API da própria tela (`dadosEmendas`).
- **Frequência:** o sistema muda todo dia, mas pouco; carga semanal, incremental (sha256).
- **Outras fontes de SC avaliadas:** Painel de Emendas do TCE/SC (Farol, Qlik Sense, 403 ao User-Agent do projeto, sem exportação; pedido em `docs/pedidos/tcesc_painel_emendas.md`); `dados.sc.gov.br` (sem conjunto de emendas); portarias da SEF em PDF com repasses às prefeituras (não lidas). Ver `docs/DECISOES.md`, 19/10/2026.


## Emendas estaduais das outras UFs (MG, BA, PE, MA, ES, AL, SE, AC)

Um módulo por fonte em `backend/ingestion/emendas_estaduais/` (a docstring de cada um traz URL, campos e armadilhas medidas na amostra de 21/10/2026); levantamento das 27 UFs em `docs/emendas_estaduais_levantamento.md`. Frequência semanal (`deploy/vps/agenda/camaras.sh`). Resumo:

| UF | Fonte (`fontes.toml`) | Endereço | Formato | Armadilhas principais |
|---|---|---|---|---|
| MG | `segov_mg_emendas` | dados.mg.gov.br/dataset/portal_emendas_estaduais, "Indicações" | CSV ~30 MB, `;`, UTF-8 BOM | IBGE e CNPJ como decimal ("3147006,0"); CNPJ sem zero à esquerda; caixas escolares sem IBGE; blocos e bancadas; `valor_pago` acumulado (não `valor_pago_ano`) |
| BA | `sefaz_ba_emendas` | dados.ba.gov.br/dataset/emendas-parlamentares | zip de CSV (usa `VW_PAINEL_EMENDAS_PARLAMENTARES_DESPESAS`) | sem município e sem favorecido; nome com espaços à esquerda; cadeia TLS incompleta; "Transferências Especiais" do mesmo portal são federais |
| PE | `seplag_pe_emendas` | dados.pe.gov.br/dataset/emendasparlamentaresestaduais (Tabela Completa GTV, DIRETA, PIX) | CSV `;`, registros em CRLF | LF solto dentro do objeto; `;` entre aspas; empenho repetido por chamamento; 2012-2025 sem autor |
| MA | `transparencia_ma_emendas` | transparencia.ma.gov.br/app/v2/emendasestaduais/export?formato=csv | CSV `,` | só 2026; ponto decimal |
| ES | `sefaz_es_emendas` | dados.es.gov.br (CSV por ano, lidos pelo `package_show`) | CSV `;` | link assinado no S3 que expira; linha repetida com outro nome de ação (2023, 2025); IBGE de 6 dígitos; previsto repetido por instrumento |
| AL | `transparencia_al_emendas` | transparencia.al.gov.br/despesa/json-emendas-parlamentares/ | JSON paginado | só 2026; CNPJ só no texto do objeto |
| SE | `transparencia_se_emendas` | api.transparencia.se.gov.br/api/emendas-estaduais?ano=&page=&limit=100 | JSON paginado | sem número da emenda nem empenhado (chave: ano + sha1 da linha); " -   " no pago |
| AC | `seplan_ac_emendas` | planilha publicada em CSV que a página da SEPLAN/AC usa | CSV `,` | números em dois formatos; linhas em branco no fim; conta bancária na planilha (não lida) |

## ALEP: Assembleia Legislativa do Paraná

- **A API de dados abertos não serve (testado em 19/10/2026).** `webservices.assembleia.pr.leg.br/api/public` (documentada em `transparencia.assembleia.pr.leg.br/servicos/dados-abertos`, com base `http://`) só tem **proposições** (`GET /proposicao/campos`, `POST /proposicao/filtrar`, `GET /proposicao/{código}`) e **normas legais** (`/norma-legal/...`); não há deputados, votos, presença nem gastos. O endereço HTTPS apresenta um certificado autoassinado de assunto `CN=BLACKHOLE` (RSA 2048, válido de 03/08/2026 a 03/08/2027, **SHA-256 `ae0f3aedfaa3bf2c17c9a37386a4faf21ca86354d27b885b68cd1a47c8ff903c`**), respondeu **403** a toda rota (inclusive `/robots.txt`) e logo depois passou a recusar conexões (HTTPS e HTTP). Um certificado genérico de firewall não prova que o servidor é da Assembleia, então **não fixamos esse certificado** e não desligamos a verificação; o 403 é bloqueio e não se contorna. Fica em `docs/pedidos/alep_certificado.md`.
- **Fontes usadas (certificado válido, `robots.txt` liberado):**
  - deputados: `https://www.assembleia.pr.leg.br/deputados/conheca` (54 cartões `deputado-card` com slug do perfil, nome em maiúsculas, partido e foto; o presidente e a Mesa trazem o cargo no lugar de "Deputado"). O `robots.txt` do site pede no máximo um pedido a cada 10 s só a robôs de IA e buscadores nomeados; usamos pausa de 2 s e identificamos o robô.
  - presença: `GET https://transparencia.assembleia.pr.leg.br/api/presenca/ano?ano=AAAA` (JSON, ~100 KB por ano): `sessoes[]` com `data` (dd/mm/aaaa) e `linhas`: cabeçalho `PRESENTES | JUSTIFICADOS | AUSENTES | TOTAL` e uma linha por posição com o nome parlamentar em cada coluna; a última linha traz os totais. Os nomes têm espaço sobrando e pequenas diferenças em relação ao cartão ("MARLI PAULINO", "DEL. JACOVÓS", "DR. ANTENOR"): ligamos pelo mesmo critério do TSE (idêntico, sem partículas, ou todas as palavras contidas, só se único).
  - votos: `GET /api/votacoes/meses?ano=`, `/api/votacoes/datas?ano=&mes=`, `/api/votacoes/sessoes?ano=&mes=&data=` e `/api/votacoes/dados-abertos?sessao=ID`, que devolve `{"arquivo": ".../dados_abertos_..._ID.zip"}` (404 quando a sessão não tem votação nominal publicada). O zip tem uma planilha `.xlsx` por item (`..._ITEM-192-33609-PROJETO DE LEI.xlsx`: item, código, tipo).
- **Planilha de votação:** linhas 1 a ~15 em pares rótulo/valor (item, matéria, autores, sessão, `DATA`, `TIPO VOTAÇÃO` NOMINAL, `QUORUM`, `ASSUNTO`, `EMENTA`, presidência e secretários), depois `RESULTADO DA VOTAÇÃO`, `VOTOS SIM`, `VOTO NÃO`, `VOTO ABSTER`, `TOTAL DE VOTOS`, e a tabela `PARLAMENTAR | PARTIDO | VOTO` com **o nome civil** (ex.: "ADAO FERNANDES DA SILVA"), os 54 deputados por item.
  - **Armadilhas:** o voto "NÃO VOTOU" mistura quem estava ausente e quem estava presente e não votou (no exemplo, 43 presentes, 38 votos e 16 "não votou"): guardamos como "Não votou" e a tela não conta como voto; o nome da planilha é o **civil**, o do site é o de urna ("AD�O LITRO"), então a ligação passa pela tabela de candidaturas do TSE (nome de urna casa com o do site, nome civil casa com o da planilha); quem não casa fica sem voto, não ligamos por sobrenome; a ementa vem em maiúsculas (passamos a título com inicial maiúscula e palavras pequenas em minúscula); o nome do arquivo dentro do zip tem acentos mal codificados (usamos só o código do item).
- **Fica de fora, sem contornar:** `api/votacoes?...` (busca de votações) e `api/ressarcimento` (verba de ressarcimento da atividade parlamentar, POST) exigem `X-Recaptcha-Token`; `api/votacoes?sessao=` sem token responde 403; a pesquisa legislativa do portal `consultas.assembleia.pr.leg.br` (JHipster) usa reCAPTCHA. Proposições e gastos viram pedido. As diárias (`transparencia.../api/diarias?ano=&mes=`, citada pelo OPS) vêm emitidas a servidores e deputados misturados, sem como separar a verba do deputado; não entram.
- **Referência:** o importador da OPS (Apache-2.0, `OPS.Importador/Assembleias/Parana`) usa só o site para deputados (`/deputados/conheca`) e `consultas.assembleia.pr.leg.br/api/` para o ressarcimento, e descarta as respostas `invalid-recaptcha`. Só serviu de pista de endereço.
- **Frequência:** semanal. O robô pausa 2 s entre pedidos; uma carga com dois anos faz centenas de pedidos (lista de datas, sessões, `dados-abertos` e um zip por sessão com votação): vários minutos a dezenas de minutos.

## ALERJ: Assembleia Legislativa do Rio de Janeiro

- **Sem API nem dados abertos.** `robots.txt` inexistente (404). Lemos páginas públicas do site, uma por vez, com pausa:
  - lista: `https://www.alerj.rj.gov.br/Deputados/RepresentacaoPartidaria` (cartões `controle_deputado` com partido, nome, foto e o código do perfil; 70 deputados em exercício);
  - ficha: `https://www.alerj.rj.gov.br/Deputados/PerfilDeputado/{id}` (nome parlamentar com a caixa certa, telefone e e-mail do gabinete). A página diz UTF-8, mas partes antigas vêm em Windows-1252: decodificamos com os dois.
- **Proposições: sem canal aproveitável.** Testado em 09/10/2026:
  - o processo legislativo está num Lotus Notes (`alerjln1.alerj.rj.gov.br/scpro2327.nsf`, legislatura 2023-2027). A visão de cada deputado (`/{slug}int?OpenForm&ExpandView`) mostra só as primeiras linhas;
  - qualquer chamada com `Start=`, `Count=` ou `ReadViewEntries` recebe resposta vazia (conexão fechada pelo servidor). Não contornamos;
  - a busca por texto (POST do formulário público de busca) devolve no máximo 1.000 resultados, ordenados por relevância, misturando proposições, distribuições, despachos e pareceres. Não dá para saber se uma lista está completa.
- **Sem votos nominais, presença e gastos** em formato aproveitável (a Ordem do Dia é um sistema à parte).

## ALRS: Assembleia Legislativa do Rio Grande do Sul

- **Sem arquivos em lote nem documentação**, mas os portais alimentam as próprias telas por endereços abertos (os `robots.txt` só bloqueiam áreas administrativas do Drupal):
  - deputados: `GET https://ww4.al.rs.gov.br:5000/listarDestaqueDeputados` (JSON `{"lista": [...]}` com `idDeputado`, `nomeDeputado` (às vezes com espaço no fim), `siglaPartido`, `emailDeputado`, `telefoneDeputado`, `fotoGrandeDeputado`, `codStatus`; 55);
  - proposições: `GET https://ww4.al.rs.gov.br/legislativo/pesquisa/dados?anoProposicao=AAAA` (JSON com todas as proposições do ano, sem paginação: ~1.100 em 2026, 950 KB, **cerca de 4 minutos** para responder). Campos: `siglaTipoProposicao`, `nroProposicao`, `nomeProponente` ("Deputado(a) Nome", "Deputado(a) Nome + 3 Deputado(s)" quando há coautores sem nome, "Poder Executivo"…), `dthProtocolo`, `ementa`, `descricao` (situação), `proposicaoId`;
  - votos em plenário: `GET https://transparencia.al.rs.gov.br/parlamentares/votos-plenario/pesquisa?solicitante={idDeputado}&ano=AAAA`. HTML com um `data-item='{...}'` (JSON escapado) por voto: `dataVotacao`, `tipoProjeto`, `numProposicao`, `anoProposicao`, `materia`, `voto` ("Sim", "Não"…), `resultadoVotacao`. Não traz os totais da votação nem um identificador: montamos a votação por (data, tipo, número, ano) e contamos os votos dos deputados em exercício;
  - presença: `.../presencas-plenario/pesquisa?solicitante=&ano=` (sem `mes`, devolve o ano inteiro, um `data-item` por mês com `presenca`, licenças, `faltaJustificada` e `faltaNaoJustificada`);
  - cota parlamentar: `.../gastos/pesquisa?solicitante=&ano=&mes=` (obrigatório o mês; sem ele, "não foram encontradas ocorrências"). Despesas do mês por categoria ("Telefones: - R$1.097,00"), mais saldo anterior, cota e total, que ignoramos.
- **Armadilhas:** a página de gastos escreve a classe CSS com dois espaços (`responsive-value  justify-content-center`); o endereço da proposição precisa do UUID (`/proposicao/PL/1/2026/{proposicaoId}`).
- **Volume por carga:** 55 deputados x (2 anos de votos + 2 de presença + ~22 meses de cota) = ~1.450 requisições, uma por vez, mais as 2 consultas de proposições.

## ALBA: Assembleia Legislativa da Bahia

- **API pública** do Processo Legislativo Eletrônico, documentada em `https://albalegis.nopapercloud.com.br/dados-abertos.aspx` (`robots.txt`: `Allow: /`). JSON, sem chave:
  - `GET /api/publico/parlamentar/?pag=1&qtd=200`: 72 registros (63 `Ativo`, 9 `Inativo` da legislatura 20), com `parlamentarNome`, `parlamentarRazaoSocial` (nome civil), `partidoSigla`, `parlamentarFoto`, `parlamentarEmail`, `autorID` e `frequenciaPlenario` (por situação e ano: Presente, Falta, Falta Justificada, Licenciado, Afastado, Governador Interino). A resposta tem 770 KB por causa do currículo em HTML;
  - `GET /api/publico/proposicao/?pag=&qtd=100&ano=AAAA`: ~1.900 proposições em 2026, com `sigla`, `numero`, `assunto` (ementa), `data`, `situacao`, `arquivo` (PDF) e `AutorRequerenteDados`. Atenção: o autor traz o **CPF**, que não guardamos. O `autorId` da proposição nem sempre é o `autorID` do parlamentar (casa em 416 de 500 no teste); o nome civil (`nomeRazao`) casa com a razão social em todos os deputados, e é a chave principal;
  - `GET /api/publico/spl/sessoes/` (redireciona sem a barra final): sessões, com pauta, oradores e presenças por sessão em `?id=`; não usamos, porque a frequência por ano já vem no parlamentar;
  - outras: comissões, mesa, lideranças, partidos, reuniões de comissão.
- **Tipos:** PL, PLC, PEC, PDL e PRS (projeto de resolução) guardam a ementa; IND (indicação), MOC (moção), REQ (requerimento) e UP (utilidade pública) viram contagem. OF, MSG e outros ficam de fora.
- **Sem votos nominais** na API (as sessões trazem pauta e presenças, não o voto de cada deputado) e **sem verba de gabinete** nos dados abertos.
- **Acesso (27/10/2026):** o site só responde a IP do Brasil (no GitHub Actions dava tempo esgotado). Agora a carga roda na VPS de São Paulo (`deploy/vps/agenda/camaras.sh`, semanal), sem contorno; `acesso = "aberto"` em `fontes.toml`. Carga completa conferida do Brasil: 63 deputados ativos.

## Câmaras que saíram do SAPL (levantamento de 09/10/2026)

- **Por quê:** 66 câmaras têm o SAPL parado na legislatura 2021–2024 (trocaram de sistema), e a cidade ficava sem vereadores no site. `data/sistemas_camaras.csv` registra, para cada uma, o sistema atual: a página inicial foi aberta uma única vez (uma requisição por vez, pausa, `User-Agent` do Panóptico, sem contornar bloqueios) e o fornecedor reconhecido por marcas no HTML (domínios de links, `meta generator`, rodapé). A câmara de União (PI) não abriu: o certificado TLS do site não valida, e não contornamos.
- **Distribuição** (66 câmaras): Cittatec 6; modelo de site PHP com `vereadores.php` (AP e CE) 5; CR2 4; Nucleogov/7Focus 4; site próprio sem fornecedor reconhecido 4; Betha, Megasoft e AOS Software 2 cada; os demais 1 cada (NoPaperCloud/PLE, Siscam, IPM, Fiorilli, Instar, Legislador, Nexlegis, Cespro, SGP Cloud, Publicsoft...). Outras 18 ainda mostram o **Portal Modelo do Interlegis (Plone)**, que é só a casca: a lista de parlamentares dele é lida do SAPL parado, e o sistema legislativo de verdade não aparece na página.
- **Cittatec (Citta Conecta), o maior com API:** o portal (`cm<cidade>.cittatec.com.br`) é Angular, mas a página lê uma API JSON pública (descoberta no código da própria página; o cabeçalho `ID-Tenant` é o nome do subdomínio):
  - `GET /api/conecta/public/clientes/<base64 do nome>/tenant` devolve `{"ID-Tenant": ...}`;
  - `GET /api/open-data-leg/public/legislaturas`: legislaturas, uma com `legislaturaAtual`;
  - `GET /api/open-data-leg/public/parlamentares/legislaturas/<id>`: **um registro por período de exercício** (nome de urna, nome civil, partido, e-mail, datas, `ativo`, `evento: SUBSTITUICAO`). A mesma pessoa pode aparecer em vários registros (Pelotas: 31 registros, 21 em exercício);
  - `GET /api/open-data-leg/public/mandatos/proposicoes/parlamentares/<pessoa>?periodoMandato=<início>,<fim>`: quantidade de proposições por tipo.
- **Armadilhas:** o endereço da foto embute o **CPF em base64** (`.../conecta/<CPF em base64>`), então a foto não é guardada. A lista de proposições mistura pareceres, memorandos, recursos e justificativas de ausência com as proposições do vereador; esses ficam de fora da contagem. Não há texto das proposições, votos nominais nem presença na API pública (os projetos individuais só pelo GraphQL de uso interno, que não usamos).
- **Modelo de site PHP com `vereadores.php` (5: Amapá, Ferreira Gomes e Tartarugalzinho, no AP; Fortim e Poranga, no CE).** Só HTML renderizado no servidor, sem API; o `robots.txt` está vazio. `/vereadores.php` redireciona para `/vereadores` (cartões com o id de cada pessoa) e `/vereadores/<id>` é a ficha. Conector `ingestion.camaras.portal_php`, uma requisição por vez com pausa (1 da lista + 1 por pessoa, ~70 no total):
  - a lista **inclui ex-vereadores** (Poranga: 23 cartões para 9 cadeiras; Fortim: 12 para 11);
  - a ficha traz o rótulo `LEGISLATURA ATUAL - 2025/2028` só para quem tem vínculo nela, a tabela "Informações dos mandatos" (cargo, vínculo, legislatura, período; vínculo encerrado tem "à <data>") e `Partido: PL`, com a "Filiação partidária" de reserva. Em exercício = vínculo da legislatura atual sem data de fim e sem licença (Fortim: quem só teve um cargo de mesa que acabou em 30/09/2025 fica de fora);
  - a ficha tem e-mail/telefone só em alguns casos (não guardados); a foto é um arquivo público em `/imagens/`;
  - **de fora:** projetos (a ficha traz só as últimas matérias; a listagem completa não tem autoria confiável por linha), votos e presença. A contagem por tipo da ficha é da legislatura inteira, não do ano atual e anterior, e não foi misturada com as demais câmaras.
- **CR2 (4: Beruri, Itamarandiba, Benevides, São Miguel do Guamá).** Os sites só redirecionam ao Portal da Transparência (`portalcr2.com.br`), uma aplicação Bubble que não mostra dados no HTML. O próprio portal oferece dados abertos: `GET /api/1.1/meta` lista os tipos e `GET /api/1.1/obj/parlamentares` (leitura pública, `limit` e `cursor`) traz um registro por vereador de todas as câmaras do portal (milhares). A câmara é o apelido (`cm-beruri`) no início ou no fim do `Slug`; o filtro `contains` casa por palavra, então a busca usa a última palavra e o resto é conferido no conector (`ingestion.camaras.cr2`):
  - só entra quem tem `ativo` e não está `deletado`, uma vez por pessoa (Benevides tem "Bizinho" duas vezes, uma apagada);
  - o partido vem como "MDB", "Movimento Democrático Brasileiro (MDB)", "PDT (Partido ...)", e também "Sem partido", "Aguardando Informação" e "*";
  - o `_id` do Bubble tem 33 caracteres (a coluna tem 20): ficam o carimbo de criação e 6 dígitos do sufixo;
  - **de fora:** `materias_legislativas` são pacotes mensais com um documento e uma lista de autores, não projetos individuais; votos e presença não existem na API.
- **Nucleogov / 7Focus (5: Pirenópolis e Campos Belos, no GO; Cariri do Tocantins, Figueirópolis e Santa Rita do Tocantins, no TO).** Portal WordPress que o levantamento dizia ter "sem lista de vereadores no HTML inicial": a página inicial tem, sim, um link `/vereador/<slug>/` por vereador (menu "Vereadores" e cartões da Mesa), e a ficha tem nome e partido. Sem API (o `wp-json` não expõe o tipo). `robots.txt` com `Crawl-Delay: 5` (respeitado), só `/wp-admin/`, `/wp-includes/` e `/*.html$` proibidos. Conector `ingestion.camaras.nucleogov`, 1 + ~10 requisições por câmara. Dois leiautes de tema: `<h1>` com rótulos `Partido:` (Pirenópolis, Campos Belos, Cariri, Figueirópolis) e o tema "araguaia" de Santa Rita (título `Ver. Fulano` / `Verª. Fulana`, campos "nome civil" e "partido" em blocos `wp-block-nwe-acf`).
  - **armadilhas:** o partido é o que o site informa e pode estar velho (Cariri ainda mostra "DEM") ou por extenso ("Partido Democrático Trabalhista – PDT", "AGIR – Agir"; a coluna tem 30 caracteres, então fica a sigla); os slugs passam de 20 caracteres (`id_externo`), então ganham sufixo de hash (`sapl.id_curto`); o prefixo "Ver." do título sai, mas "Vera Lúcia" não;
  - Campos Belos aparecia como Megasoft: Megasoft é só o portal de transparência (JSF); o site é Nucleogov;
  - **de fora:** projetos, votos e presença (ficam no portal `acessoainformacao.<câmara>`, sem formato estruturado reconhecido).
- **Portal Modelo do Interlegis (Plone) com parlamentares cadastrados (Imbuia, SC; Santana do Piauí, PI).** Imbuia aparecia como Betha (só o portal de transparência) e Santana como AOS. A página `/processo-legislativo/parlamentares` tem um `<select id="legislatures">`; com a legislatura marcada "(Atual)" a lista vem de `.../@@legislature-members?legislature=<id>` (seção "Ativos"; apelido e partido), e a ficha de cada um traz o nome civil (`form-widgets-full_name`) e o partido (`memberOf`). Santana não tem o seletor: os parlamentares são conteúdos da pasta (publicados em 2025). Conector `ingestion.camaras.portal_modelo`, pausa de 1 s. Carolina (MA) tem o mesmo portal com o seletor vazio (a lista dependia do SAPL parado): sem canal. 
- **Portal Modelo, segunda varredura (10/10/2026): das 16 câmaras Plone restantes, 2 entram.** Vila Flores (RS): a pasta `/processo-legislativo/legislaturas` tem uma página por legislatura; a "10 (2025 - 2028) (Atual)" traz a tabela de membros (nome completo, nome, partido, situação) e só os "Ativo" entram. Campo Novo de Rondônia (RO): a pasta `/processo-legislativo/parlamentares` dá 404, e a capa `/institucional/legislatura/9a-legislatura-1/capa` (a que a pasta de legislaturas marca com `title="2025-2028"`) tem um bloco `<div class="vereador">` por pessoa, com nome civil abreviado e partido; o título da ficha é o nome de urna. Os 9 de cada uma batem com os eleitos de 2024 do TSE. Ficam de fora, por motivo: lista e pasta de legislaturas vazias (Ipueiras, Irauçuba, Morada Nova, Duque Bacelar, Bambuí, Presidente Castelo Branco, Bocaina do Sul, Gravatal, Carolina); exigem login (Uauá, Olinda Nova do Maranhão, Espírito Santo do Turvo); páginas de vereadores que são o SAPL parado em iframe (Tanque do Piauí, Santo Antônio do Monte); Ourinhos (legislatura 2021–2024 sem membros); Cerrito (a câmara mudou para cmcerrito.rs.gov.br); São Sebastião da Boa Vista (só nomes na navegação, sem partido, e a maioria não é eleita em 2024: lista antiga). Todas com robots.txt sem bloqueio; uma requisição por vez, pausa de 1 s.
- **AOS Software (Queimada Nova, PI).** Site próprio (`adtrcloud`): `/vereadores` tem um cartão por vereador em exercício (foto com `alt` = nome civil, apelido em `<h3>`, `(PARTIDO)`, link `/vereador/<nome-civil>`). Uma requisição por câmara, `robots.txt` inexistente. Conector `ingestion.camaras.aos`.
- **Sites próprios com leitor pequeno (11/10/2026): Palmas, Teófilo Otoni e Frutal.** Cada fornecedor tem uma só câmara, então o conector `ingestion.camaras.sistemas` junta três leitores curtos, escolhidos pelo `sistema` do catálogo. Palmas (`nexlegis`, WordPress): a capa traz um cartão por vereador (o rótulo SUPLENTE fica de fora) e a ficha dá nome civil e partido, uma ficha por vez com a pausa de 5 s do `robots.txt`. Teófilo Otoni (`digitaliza`): `/vereadores` lista só quem está no cargo, com nome civil, apelido entre parênteses e partido por extenso (vira sigla por uma tabela pequena). Frutal (`siscam`): `<cidade>.siscam.com.br/Vereadores` é a legislatura atual (as anteriores ficam noutro link) com a sigla cortada em 10 letras. Fora, com o motivo em `data/pendencias_cobertura.csv`: Praia Grande (e-Solution/IPM, página montada por JavaScript sem rota pública), Cachoeiro de Itapemirim (NoPaperCloud responde 521) e Aracruz (Câmara Sem Papel recusa a conexão), ambos fora do ar na data; Ourinhos e Morada Nova (Portal Modelo vazio). Carga real no banco local: Palmas 23 (23 ligados ao TSE), Teófilo Otoni 19 (19), Frutal 15 (15).
- **Betha e Megasoft:** nos dois casos o fornecedor é só do portal de transparência. Senador Guiomard (AC) tem site Wix (lista de vereadores em markup gerado, sem estrutura estável) e Carolina (MA) o Portal Modelo vazio: **sem canal viável**, seguem pendentes em `data/pendencias_cobertura.csv`.
- **Resultado (carga real no banco local, 10/10/2026):** Nucleogov 49 vereadores (Pirenópolis 11, Campos Belos 11, Cariri 9, Figueirópolis 9, Santa Rita 9), 45 ligados ao TSE; Portal Modelo 36 (Imbuia 9, Santana do Piauí 9, Vila Flores 9, Campo Novo de Rondônia 9), 35 ligados; AOS 9 (Queimada Nova), 9 ligados. Todos em exercício e com partido. Sem ligação: Pedro Francisco d'Abadia (Pirenópolis), Profº Vanderly (Campos Belos), Dalmi Alves de Matos e Maurio Moreno Pinto (Figueirópolis), Claudio (Imbuia).
- **Resultado (carga real no banco local):** modelo PHP 47 vereadores (Amapá 9, Ferreira Gomes 9, Tartarugalzinho 9, Fortim 11, Poranga 9), todos com partido e ligados ao eleito do TSE; CR2 52 (Beruri 11, Itamarandiba 13, Benevides 13, São Miguel do Guamá 15), todos com partido, 50 ligados ao TSE (em Itamarandiba, 2 de 13 não ligaram: Márcio Daniel Morais e Nelson Alves Correira).
- **Senador Guiomard (AC, Wix) e Praia Grande (SP, e-Solution/IPM), `ingestion.camaras.fornecedores_robin` (17/10/2026).** Senador Guiomard: o site é feito no Wix (o "Betha" do levantamento é só o portal de transparência) e `/vereadores` já traz os cartões no HTML (`wixui-repeater__item`: `<h2>` com o nome civil e o apelido entre parênteses, cargo, partido e o link `/vereadores/<slug>`); o slug vem com acento codificado (`jo%C3%A3o-...`) e o primeiro cartão pode ter a imagem padrão do Wix (`Image-empty-state`), que não vira foto. O `robots.txt` só limita bots de SEO. Praia Grande: a "onepage" é montada no navegador com o JSON público `/publico/service/onepage/select.geral.bandeiras.php` (o mesmo que a página chama; o `robots.txt` veta `/e-solution/`, `/datafiles/`, `/ws/` e outros, não `/publico/service/`). O bloco `ban_nome = "VEREADORES"` tem um item por vereador em atividade (`ban_codigo` é o id, `ban_nome` o nome de urna, `ban_texto` o partido, `ban_descricao` o slug da ficha); a foto fica em `/datafiles/` (vetado), então não é guardada. Uma requisição por câmara. Carga real no banco local: Senador Guiomard 11 (11 ligados ao eleito do TSE), Praia Grande 23 (21 ligados; sem ligação: Martins e Natanael De Oliveira). Conferido com o TSE 2024: nomes e partidos batem (ex.: Beto Rossi e Renata Zabeu, PSD; Lenon e Tammy, PP).
- **Fora (pendências em `data/pendencias_cobertura.csv`):** Garopaba (SC): as páginas "Parlamentares" e "Legislaturas" do portal da câmara são a lista de 2021–2024 (publicada em 2023) ou um `iframe` do SAPL parado, e o `atende.net` (IPM) é uma página só de JavaScript cujo `robots.txt` veta as rotas de dados (`Disallow: *?*rot=*`, `*?*aca=*`). Itatuba (PB): `/processo-legislativo/parlamentares` e `/legislaturas` exigem login (não contornamos) e `/legislaturas-1` é o `iframe` do SAPL parado. São Raimundo das Mangabeiras (MA): a capa mostra a imagem "site fora do ar", as notícias param em 2023 e `/processo-legislativo/parlamentares` responde 404. Carolina (MA): Portal Modelo com a pasta de legislaturas vazia ("Atualmente não existem itens nessa pasta"). Imbuia (SC, Portal Modelo) e Campos Belos (GO, Nucleogov) já têm leitor; Imbuia e Campos Belos conferidos de novo em 17/10/2026 (9 e 11 vereadores).

- **Sites próprios e de fornecedores, terceira leva (17/10/2026): Aracruz, Cachoeiro de Itapemirim, Varjão de Minas, Nortelândia, Santa Maria do Cambucá e Alvorada** (`ingestion.camaras.fornecedores_alfred`, lista de câmaras no próprio módulo). Todos com `robots.txt` lido (nada vedado), uma requisição por vez, pausa de 3 s e User-Agent do Panóptico. Câmara Sem Papel / NoPaperCloud (Aracruz, Cachoeiro; voltaram ao ar): `parlamentares.aspx` na raiz do portal do fornecedor, cabeçalho com as datas da legislatura (exigimos "01/01/2025 a ...") e blocos Ativo, Suplente e Licença; só os Ativos entram (Aracruz 17, Cachoeiro 19; o resto: 3 suplentes e 1 licença). As páginas declaram UTF-8 e mandam cp1252 (o leitor tenta UTF-8 e cai para cp1252). Varjão de Minas (Weblinesistemas): a página Vereadores (`?pag=` em base64) lista "Nome civil - SIGLA" da legislatura (o site a chama de "8ª legislatura de 2025/2026"); 9. Nortelândia: `/camara/vereadores`, cartão com nome civil, nome de urna (vazio em todos) e "SIGLA - Nome do partido"; a página tem `<base href="/">`, então a foto é relativa à raiz; 9. Santa Maria do Cambucá: a tabela é montada por JavaScript a partir de `vereadoresClass.php?legislatura=<id>&current=1&rowCount=100` (parâmetros na URL, não no corpo; `rowCount=-1` quebra o SQL do site); o JSON traz data de nascimento, telefone, e-mail e biografia (não lidos) e o partido vem vazio, então a câmara entra sem partido; 9. Alvorada (BMF Assessoria): `/transparencia/vereador` (Composição da Casa Legislativa), nome em maiúsculas com apelido entre parênteses e, na mesa, o cargo depois de " - " (cortado); partido "UNIÃO BRASIL" vira "UNIÃO"; 9. Dados pessoais dos cartões (nascimento, estado civil, ocupação) ficam de fora. Resultado (leitura real, sem gravar no banco): 17 + 19 + 9 + 9 + 9 + 9 = 72 vereadores.
- **Rechecagem em 17/10/2026.** União (PI): o certificado do site continua sem validar (a verificação de TLS não foi desligada); segue pendência. As 16 câmaras do Portal Modelo (uma requisição à lista de parlamentares cada): nenhuma passou a mostrar os vereadores atuais; só Tanque do Piauí mostra uma pasta, com 10 fichas, todas "Inativo" (legislatura anterior); `portal_modelo.py` não mudou.

- **Sites de fornecedor lidos pelo `fornecedores_batgirl` (17/10/2026): Pimenta Bueno, Perdões e Santa Cruz.** Cada modelo de página tem um leitor curto, uma requisição por vez com pausa de 3 s e `User-Agent` do Panóptico; o `robots.txt` de cada site foi conferido antes (Pimenta Bueno veda só `/arquivos/`, `/fotos/` e semelhantes; Perdões não tem; Santa Cruz veda só áreas de administração). Pimenta Bueno (Instar): a lista de `/portal/vereadores` é montada por script, então se lê a capa, que traz o bloco "Legislatura 01/01/2025 - 31/12/2028" e um cartão por vereador (id da ficha, foto, nome civil no `alt`, partido); a capa abrevia o nome de urna, então ele vem de `/portal/dados-abertos/vereadores/<ano>` (JSON do próprio site), ligado pelo nome civil. Perdões (Legislador): a capa do site da câmara tem um `<h3>` e um link `...WCI=Vereador&ID=67&ver=N` por vereador; o partido só aparece na biografia em texto livre (fica vazio) e a foto vem com endereço assinado que vence em 20 minutos (não é guardada). Santa Cruz (WordPress, tipo "vereador"): o menu da capa lista os 9 vereadores (um deles com link `https` e classe `custom`), e a ficha traz o nome civil em negrito e `Partido: X` no texto; o formato da ficha varia (o negrito às vezes é mais curto que o menu, e então não vira nome completo). Fora, com o motivo em `data/pendencias_cobertura.csv`: Riozinho (login do Plone), Manoel Vitorino e Ibotirama (iframes do SAPL parado, só com a legislatura 2021–2024), Leópolis (pasta de parlamentares vazia), Estiva (fichas todas "Inativo", 6 com data recente para 9 cadeiras) e São José da Varginha (`robots.txt` veda tudo). Leitura real em 17/10/2026: Pimenta Bueno 10 vereadores, Perdões 9, Santa Cruz 9; sem carga no banco de produção.

## ALES: Assembleia Legislativa do Espírito Santo

- **Mesma API da ALBA** (Processo Legislativo Eletrônico da Nopapercloud), em `https://www3.al.es.gov.br/api/publico/` (o link "Dados Abertos" do portal aponta para `dados-abertos.aspx`, que o `www.al.es.gov.br` não serve). `robots.txt` inexistente (404). JSON, sem chave:
  - `GET parlamentar/?pag=1&qtd=200`: 35 registros: 30 com situação `Ativos` (as 30 cadeiras), 3 suplentes e 2 titulares que saíram. Campos como os da ALBA, com `autorID`, `parlamentarRazaoSocial` e `frequenciaPlenario`. Diferenças: a situação é `Ativos` (plural) e a paginação vem como `paginacao`;
  - `GET proposicao/?pag=&qtd=100&ano=AAAA&sigla=XX`: a API aceita filtrar por `sigla`, `tipoId` e `autorId`. **Sem filtro, o ano tem ~5.400 documentos** (ofícios de comenda, justificativas de ausência, atas, pautas...) e cada página de 100 leva cerca de 12 segundos; por isso o conector pede só os tipos que interessam. Em 2025: PL 925, PLC 45, PEC 4, PDL 156, PR 29, REQ 64, RQI 172, IND 1.704;
  - **Frequência:** os nomes são `Presente`, `Ausência`, `Ausência Justificada`, `Falta`, `Licenciado`, `Afastado` e `Governador Interino`. Sessões = presenças + faltas + ausências (justificadas ou não), como na ALBA.
- **Armadilhas:** o autor da proposição traz o nome digitado à mão (ex.: "Engenherio José Esmeraldo"), então o nome nem sempre casa com a razão social do deputado; o `autorId` da proposição casa com o `autorID` do parlamentar e serve de segunda chave. O autor traz CPF/CNPJ e endereço, que não guardamos.
- **Sem votos nominais** (só o "Boletim de Votação Nominal" em PDF) e **sem verba de gabinete** nos dados abertos. O portal de transparência tem cotas parlamentares (`/Transparencia/CotasParlamentares`), não lidas.
- **Acesso (27/10/2026):** o site só responde a IP do Brasil (no GitHub Actions dava tempo esgotado). Agora a carga roda na VPS de São Paulo (`deploy/vps/agenda/camaras.sh`, semanal), sem contorno; `acesso = "aberto"` em `fontes.toml`. Carga completa conferida do Brasil: 30 deputados ativos (a carga leva ~21 min por causa das proposições, página a página, com pausa; sem limite de tempo na VPS).

## ALECE: Assembleia Legislativa do Ceará

- **Sem dados abertos legislativos.** `robots.txt` do site libera tudo menos downloads de imagens. A API do portal da transparência (`transparencia.al.ce.gov.br/api`, OpenAPI em `/docs?api-docs.json`) só tem contratos, empenhos, licitações, pagamentos e termos de credenciamento. Lemos páginas públicas, uma por vez:
  - lista: `https://www.al.ce.gov.br/deputados`: cartões `deputado_card` (classe `licenciado` para os 6 titulares afastados) e, depois do título "Suplentes em Exercício", os 6 suplentes. Em exercício: 40 + 6 = 46;
  - ficha: `https://www.al.ce.gov.br/deputados/{slug}` (e-mail e telefones do gabinete);
  - projetos: o sistema antigo `https://www2.al.ce.gov.br/legislativo/proposicoes/ano.php?nome=31_legislatura&tabela={projeto_lei|projeto_compl|projeto_emen|projeto_decre|projeto_reso}&opcao=T&absolutepage=N`, 15 registros por página, ordem aproximadamente cronológica (a mais recente no fim). Campos: número/ano (`572/26`), autor, data de entrada, ementa (com link do texto), situação (`OBS`). **Armadilhas:** o autor vem em formatos diferentes (`AUTORIA: DEPUTADO FULANO.`, `Autoria: Deputado Fulano.`, só o nome); a página mistura UTF-8 e Windows-1252; há linhas tortas (`572/256`), ignoradas; nem todo projeto tem o texto publicado (usamos o endereço da listagem);
  - votação nominal: `transparencia.al.ce.gov.br/consultas-gerais/votacao-nominal` lista as matérias e dá um PDF e uma planilha por matéria, mas a planilha é o relatório de impressão (títulos, mesclas e o voto espalhado por colunas de partido): não lemos;
  - **Gastos (verba de desempenho parlamentar, 20/10/2026):** CSV mensal `https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar/csv?mes=MM&ano=AAAA` (robots livre; 60 a 120 KB por mês; mês futuro vem só com cabeçalho). UTF-8 com BOM, `;`; a 1ª linha é `;;;` e o cabeçalho vem na 2ª: `DEPUTADO;PERIODO;EMPENHO;DESCRICAO;CNPJ;CREDOR;VALOR`. São **empenhos** (valor `1.000,00`; anulação vem negativa: 390 linhas em 2025-26) e somamos líquido por deputado e mês. **Não há coluna de tipo de gasto**: o tipo sai de palavras do texto livre (benefício de alimentação, combustível, consultoria, divulgação, locação…; o que não casa vira "Outros", ~1,2% do valor). **Armadilhas:** o nome do deputado vem como `DEP SERGIO AGUIAR.` com muitos erros de digitação (84 grafias para ~50 pessoas: `SERGIO AHUIAR`, `EMIILA PESSOA`); ligamos só por nome exato (site ou TSE) e as demais ficam de fora, listadas em `fonte_ingestao.alertas` (2025-26: 401 lançamentos, R$ 2,80 mi de R$ 36,70 mi, 30 nomes); `CNPJ` traz CPF de pessoa física nos reembolsos e `CREDOR` o nome dela: **nenhum dos dois é guardado**. Bruto: zip com um CSV por mês em `data/raw/alece/gastos_*.zip`; `--de-raw` reprocessa.
  - votação nominal: PDF/planilha de impressão, não lemos (acima).
- Indicações, moções e requerimentos não entram (milhares de páginas de listagem).

## ALEPA: Assembleia Legislativa do Pará

- **Sem API.** `robots.txt` inexistente (404). O portal (`www.alepa.pa.gov.br`, ASP.NET MVC com DevExpress, da Quartertec) lista os 41 deputados em `/Home/Page/Deputados` com nome, partido e foto já no HTML (`card-info`); a foto fica em `alepa.quartertec.com.br` com barras invertidas no endereço.
- **Proposições e votações nominais: sem canal aproveitável.** Testado em 09/10/2026: `Proposicoes` e `VotacoesNominais` carregam o resultado por chamadas de retorno DevExpress (`POST /Legislativo/CallbackPanelProposicoes` com `__DXCallbackName=cbpProposicoes`). O filtro funciona (`model.Ano=2025` devolve 2.809 itens), mas a lista vem 10 por página e o pedido de outras páginas (`PAGERONCLICK`) devolve sempre a primeira. Reproduzir o estado do componente fora do navegador seria depender do formato interno da biblioteca, e não achamos a forma estável. Voltar a olhar se a ALEPA publicar dados abertos.

## ALMT: Assembleia Legislativa de Mato Grosso

- **O SAPL (`sapl.al.mt.leg.br`) parou em 2018.** O sistema atual é próprio: site `www.al.mt.gov.br` e API `api.al.mt.gov.br`.
- **API fechada.** `api.al.mt.gov.br` documenta os serviços (`ssl/parlamentar`, `ssl/proposicao`, `ssl/sessao-plenaria/proposicao-votada`, `ssl/ordem-dia`, `sgp/servidor`...), mas exige OAuth 2.0 (`401 access_denied`), e a página diz que é para os fornecedores da instituição. Limite: 10 requisições por segundo. Não usamos.
- **`robots.txt`** veda `/proposicao?` (pesquisa e paginação), `/parlamento/ordem-do-dia?`, `/parlamento/documentos/parlamentares?`, `/transparencia/pesquisa/` e as páginas de mídia com parâmetros. A lista de proposições sem parâmetros mostra só as mais recentes. Respeitamos.
- **O que lemos:** `https://www.al.mt.gov.br/parlamento/deputados` (24 cartões: nome, partido, foto e código do perfil) e `/parlamento/deputados/{id}/perfil` (nome civil).

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
- **Segunda varredura (10/10/2026), só das 904 cidades sem canal:** `python -m ingestion.canais.segunda_varredura --ibge-raw <json do IBGE>`. Testa o que a primeira não testou: nome sem "de/do/da", `cm`/`camara`/`camaramunicipal` em `.{uf}.gov.br`, `.{uf}.leg.br`, `.org.br` e `.com.br`, `camara.{cidade}.{uf}.gov.br` e o `sapl.` de cada variante. Só aceita página com status 200 que traga o nome da cidade e "câmara" no título (ou "Câmara Municipal" no texto), sem sinal de domínio parado; em `.com.br`/`.org.br` a página também tem de citar o estado. Respeita o `robots.txt`, uma requisição por vez por servidor, 8 cidades em paralelo. Resultado: 7 câmaras novas, nenhuma com SAPL; 897 cidades continuam sem canal, listadas em `data/cidades_sem_canal.csv` (com a data da busca). A maioria dessas cidades parece não ter site próprio ou usa endereço fora do padrão (a conferência fica para quem conhecer a cidade, por pull request).
- **Frequência:** varredura inicial única; depois, revisão pontual quando uma carga falhar.

## PNCP: contratos (Portal Nacional de Contratações Públicas)

- **URL (sem chave):** `https://pncp.gov.br/api/consulta/v1/contratos` (por data de publicação) e `/v1/contratos/atualizacao` (por data de atualização, para pegar aditivos). Parâmetros obrigatórios: `dataInicial`, `dataFinal` (AAAAMMDD) e `pagina`; `tamanhoPagina` de 10 a 500 (501 dá 400; menos de 10 também dá 400).
- **Limites:** período máximo de 365 dias (mais dá 422); página profunda dá 500 (ex.: a 4.000ª de um ano), então a coleta lê **um dia por vez**. Há limite de requisições: depois de uma rajada, a API responde 429 (página HTML "Limite de Requisições Excedido") por algum tempo. A coleta faz uma requisição por vez, com pausa, e espera com recuo crescente no 429 e no 5xx. Dia sem registros pode responder 204 sem corpo.
- **Tamanho:** um dia típico tem ~8.400 contratos em 17 páginas de 500 (~0,8 MB cada, ~1,8 s). Por ano: 2023, 243 mil; 2024, 1,09 mi; 2025, 2,02 mi; 2026 (até 09/10), 1,63 mi.
- **Sem filtro por fornecedor:** `niFornecedor` na consulta é ignorado; para achar os contratos de uma empresa é preciso ler tudo.
- **Campos usados:** `numeroControlePNCP` (chave), `orgaoEntidade` (`cnpj`, `razaoSocial`, `poderId`, `esferaId`: F, E, M e também N, consórcios), `unidadeOrgao` (`ufSigla`, `municipioNome`, `codigoIbge`), `tipoPessoa` (PJ, PF, PE), `niFornecedor`, `nomeRazaoSocialFornecedor`, `tipoContrato` e `categoriaProcesso` (objetos `{id, nome}`), `objetoContrato`, `valorInicial`, `valorGlobal`, `valorAcumulado`, `dataAssinatura`, `dataVigenciaInicio/Fim`, `dataPublicacaoPncp`, `dataAtualizacaoGlobal`, `receita`, `numeroControlePncpCompra`, `processo`.
- **Armadilhas:**
  - **Empenho não é contrato:** ~37-40% dos registros têm `tipoContrato` "Empenho" (os demais: Contrato (termo inicial), Outros, Carta Contrato, Termo de Adesão, Comodato, Concessão). Ficam separados pelo tipo.
  - **`receita` = true é alienação** (o órgão vende, não gasta): fora das somas.
  - **CPF:** pessoa física traz o CPF completo em `niFornecedor`, e MEI (PJ) traz o CPF dentro da razão social. O CPF nunca é lido para o banco: PF e estrangeiro (`PE`) entram nas somas sem identificador, e CPF no nome dos contratos guardados inteiros é removido.
  - **`valorGlobal` muda com aditivos:** o mesmo contrato volta com outro valor. A coleta relê os últimos 7 dias e, pela rota de atualização, os dias antigos com contrato alterado.
  - A lista anda enquanto é lida (contrato novo empurra outro para a página seguinte): repetidos dentro do dia contam uma vez.
  - Um `tipoPessoa` PE pode vir com número de 14 dígitos; sem confirmação de que é CNPJ brasileiro, fica sem identificador.
- **O que guardamos (coleta mínima):** somas por dia de publicação × órgão (CNPJ) × município (IBGE) × tipo de pessoa × fornecedor (CNPJ) × tipo de contrato (`pncp_soma`; nome e esfera dos órgãos em `pncp_orgao`), e o contrato inteiro (`pncp_contrato`) só quando o fornecedor é CNPJ de `socio_pessoa` ou `sancao_empresa`. `pncp_dia` é o cursor e a conferência (total da API contra o lido, por dia). Do bruto fica só o manifesto de cada execução (`data/raw/pncp_contratos/*.manifesto.json`: total da API, páginas, bytes e sha256 por dia).
- **Valores digitados errado:** a API repassa o `valorGlobal` do órgão (centavos, dígitos a mais, `999999999999`). Valor acima do menor entre a despesa paga anual do município (SICONFI) e R$ 50 bilhões é tratado como suspeito: fora das somas e do ranking, guardado à parte (`pncp_suspeito`, `pncp_contrato.valor_suspeito`) e exibido com aviso, sem correção. Detalhes e números em `docs/DECISOES.md`.
- **Conferência:** quantidade somada + alienações = contratos lidos = `totalRegistros` da API no dia (`pncp_dia.lidos` contra `pncp_dia.total_api`; a coleta avisa quando diferem).
- **Frequência:** diária (incremental). Primeira carga: de 2023 até hoje; `python -m ingestion.pncp.contratos --de AAAA-MM-DD --ate AAAA-MM-DD` faz cargas parciais.
- **Uso:** quanto cada órgão contratou de cada fornecedor, e os contratos de empresas sancionadas e de empresas de sócios que acompanhamos. Se o conjunto-alvo crescer, os dias já lidos não têm as linhas novas: releia o período com `--de/--ate`.

## Querido Diário: atos de nomeação e exoneração nos diários municipais (querido_diario_atos)

- **O que é:** API aberta da Open Knowledge Brasil (`https://api.queridodiario.org.br`, documentação em `/docs`, versão 0.19.0) que reúne e indexa os diários oficiais municipais. Sem chave. Degrau "espelho" da escada de acesso: o texto vem da OKBR; o link guardado é o `url` do diário (PDF, em `data.queridodiario.ok.org.br`, cópia do diário oficial coletado).
- **Rotas usadas:** `GET /cities?city_name=` (lista os 5.570 municípios; 510 têm `availability_date`, ou seja, diário já coletado) e `GET /gazettes` com `territory_ids` (IBGE de 7 dígitos), `querystring` (sintaxe "simple query string" do OpenSearch), `published_since`, `excerpt_size`, `number_of_excerpts`, `size`, `offset`, `sort_by` (`descending_date`). A resposta traz `total_gazettes` e, por diário, `date`, `url`, `txt_url`, `is_extra_edition` e `excerpts` (trechos).
- **Limites:** a API não declara limite de taxa nem devolve cabeçalhos de limite (está atrás da Cloudflare); usamos 1 requisição a cada 2 segundos, o User-Agent do projeto (`comum.criar_cliente`) e as novas tentativas de `comum.get_json` (429 e 5xx, respeitando `Retry-After`). Sem contorno de bloqueio.
- **Armadilhas:**
  - **Trecho bagunçado.** O texto vem de PDF: as palavras saem fora de ordem e coladas ("Praça daDESIGNA", o verbo do ato longe do nome). O verbo em maiúsculas pode vir colado depois de minúsculas; a detecção aceita isso, mas só procura o verbo numa janela de 230 caracteres em volta do nome.
  - **`+` não restringe o trecho.** `"Nome" +exonera` filtra os diários (os que têm as duas coisas), mas os trechos devolvidos são os do verbo, não os do nome. Por isso a busca é só pela frase do nome e a conferência do verbo é local.
  - **Frase com aspas** casa o nome completo, sem diferença de caixa; sem aspas casaria qualquer parte do nome.
  - **Assinatura não é ato.** O prefeito (e secretários) aparece em milhares de decretos, contratos e extratos só como signatário ("representado pelo Prefeito Sr. Fulano"). A busca por nome devolve esses diários primeiro; sem palavra de ato junto ao nome, o trecho é descartado.
  - **Homônimos.** Nome comum num município grande pode ser de outra pessoa. É por isso que o achado é só sugestão.
  - **Latência.** Uma busca nova leva de 6 a 40 segundos (a mesma busca repetida volta em décimos de segundo, do cache da API). Na amostra, 182 buscas levaram cerca de 90 minutos, ou seja, ~30 s por pessoa, não os 2 s da pausa. Uma passada nas ~7,6 mil pessoas elegíveis levaria dias; a carga semanal deve ser feita em fatias (`--limite`).
  - **Título e assinatura.** O nome de um vereador aparece como lotação ("Gabinete Parlamentar do Vereador Fulano") em quase todo ato de pessoal da câmara dele, e o de secretários e do prefeito como signatários. Esses casos são descartados (nome logo depois de "Vereador", "Prefeito", "Secretário", "diária" etc. ou logo antes de "Presidente", "Secretário"...).
- **Cobertura.** 510 municípios (SP 112, AL 94, BA 66, SE 29, MA 28, TO 26, RJ 26, PR 23...). A maioria dos 5.570 não tem diário na base.
- **Campos usados:** `date`, `url`, `excerpts`; do município, `territory_id` e `availability_date`.
- **O que guardamos (coleta mínima):** só pessoas que já acompanhamos (prefeitos, vice-prefeitos e vereadores eleitos em 2024 e vereadores em exercício, em municípios cobertos), nome com 3 palavras ou mais, diários desde 2025-01-01. Por diário, uma linha em `diario_ato` (pessoa sugerida, município, data, tipo detectado, trecho de até 500 caracteres em volta do nome, link do diário, `revisado = false`). O cache da busca fica em `diario_consulta` (30 dias por pessoa). Do bruto fica só o recorte: as sugestões de cada execução, em `data/raw/querido_diario_atos/`.
- **Regra crítica:** nome em texto nunca vira vínculo nem evento publicável. Os achados esperam revisão humana.
- **Frequência:** semanal, com cache de 30 dias por pessoa (~7,6 mil pessoas elegíveis, na prática ~30 s por pessoa, por causa da latência da API: carga em fatias). Carga parcial: `python -m ingestion.diarios.atos --municipios 4314902 --limite 50`.
- **Uso:** fila de revisão de atos de pessoal (nomeação, exoneração, designação) ligados a quem acompanhamos.

## Plataformas compartilhadas de diário municipal: SIGPub (sigpub_atos) e DOM/SC pelos dados abertos do CIGA (domsc_ciga_atos)

Mesma regra do Querido Diário: nome achado em texto nunca é vínculo; os achados entram em `diario_ato` (`revisado = false`) e esperam a fila `python -m ingestion.revisar --tipo diario`. Diferença: aqui o diário é baixado por plataforma (uma edição traz dezenas ou centenas de prefeituras) e cada matéria é atribuída ao município (IBGE) pelo cabeçalho; só as matérias do município da pessoa são lidas. Levantamento de todas as plataformas, com as bloqueadas: `docs/diarios_plataformas_levantamento.md`.

### SIGPub (diariomunicipal.com.br)

- **O que é:** sistema da Vox Tecnologia que hospeda o Diário Oficial dos Municípios de associações e federações estaduais: AMM-MG, AMUPE (PE), FAMUP (PB), FEMURN (RN), APRECE (CE), AMP (PR), FAMURS (RS), AMM-MT, FAMEP (PA), AROM (RO), AAM (AM), AMA (AL), AGM e FGM (GO), AEMERJ (RJ), APPM (PI), AMR (RR), Sergipe, APM (SP) e instâncias da Bahia. Uma edição em PDF com texto por dia e instância, mais edições extraordinárias.
- **Acesso:** aberto. `robots.txt` do site é `Disallow:` vazio; o host dos PDFs (`www-storage.voxtecnologia.com.br`) não tem `robots.txt` (404). A "busca avançada" tem reCAPTCHA e **não é usada**.
- **Como lê:** `GET /<instância>/` devolve o token CSRF do formulário do calendário (`#calendar__token`) e o cookie de sessão; `POST /<instância>/materia/calendario` (e `/materia/calendario/extra`) com `calendar[day|month|year|_token]` devolve `{"edicao": [{numero_edicao, link_diario}], "url_arquivos"}` ou `{"error": ...}` quando não há edição; o PDF é `url_arquivos + link_diario + ".pdf"`. Lógica do calendário do raspador do Querido Diário (`gazette/spiders/base/sigpub.py`, MIT).
- **Texto:** PyMuPDF (grupo `acervo` do `pyproject.toml`; ~100 vezes mais rápido que o pypdf: 419 páginas em 1,7 s contra ~200 s). Normaliza ligaduras (NFKC).
- **Separação por município:** cada matéria termina em `Código Identificador:XXXXXXXX` e começa com `ESTADO DE <UF>` / órgão (`PREFEITURA MUNICIPAL DE <CIDADE>`, `CÂMARA MUNICIPAL DE ...`). O município é o maior nome do IBGE (da UF da instância) que vem depois de "DE/DO/DA" e de uma palavra de órgão municipal; sem cabeçalho, tenta o início do texto. Associações, consórcios e secretarias sem cidade no cabeçalho ficam de fora (numa edição da AMM-MG: 208 municípios em 949 matérias, 68 matérias sem município).
- **Armadilhas:** (1) o `link_diario` traz a data de geração, não a de circulação; usamos a data pedida no calendário. (2) O endpoint "extra" devolve a edição regular em alguns dias: deduplicamos pela URL. (3) O servidor perde cerca de 1 conexão em 6 por tempo esgotado (não é bloqueio): repetimos com espera crescente e limitamos a 2 chamadas a cada ~1 s. (4) Instâncias inativas: `ms` (última edição em 2020) e, nos 5 dias medidos, `amm-mt`, `appm`, `sergipe`, `pmmasp`, `amurc`, `bahia`; a instância `ma` não existe (redireciona para a página inicial). (5) Quem assina o ato ("O PREFEITO MUNICIPAL DE X, Fulano, no uso das atribuições...") não é alvo dele: essas ocorrências são apagadas antes da busca (`_ASSINA` em `plataformas.py`), além das regras de título e assinatura de `atos.py`.
- **O que guardamos:** o texto de cada edição, em `data/raw/sigpub_atos/<instância>/AAAA-MM-DD_<nº>[_extra].json.gz` (`--de-raw` reprocessa sem rede), e as sugestões em `diario_ato` (link = URL do PDF da edição + `#` + código da matéria). Recorte: últimos 90 dias na primeira carga; depois a partir da última varredura completa (`.ate`, com 3 dias de folga). A evidência de cobertura (plataforma × município × última edição) vai para `data/diarios_plataformas_municipios.csv`.
- **Frequência:** semanal, só no acervo (PyMuPDF fora da imagem de produção; sem agenda em `deploy/vps/agenda/`). Para agendar na VPS: `pymupdf` na imagem e um passo em `camaras.sh`.
- **Uso:** `python -m ingestion.diarios.sigpub [--instancias amm-mg amupe] [--dias 90] [--de-raw data/raw/sigpub_atos]`.

### DOM/SC (Diário Oficial dos Municípios de Santa Catarina), pelos dados abertos do CIGA

- **O que é:** o diário de ~290 prefeituras e câmaras catarinenses, do Consórcio de Inovação na Gestão Pública (CIGA). **O site `diariomunicipal.sc.gov.br` veda rastreadores** (`robots.txt`: `User-agent: *` / `Disallow: /`, `Crawl-delay: 10`; só Googlebot e Bingbot têm permissão), então ele **não é rastreado**. O CIGA publica, para reúso, o mesmo conteúdo em dados abertos (`https://dados.ciga.sc.gov.br`, CKAN): conjuntos mensais `domsc-publicacoes-de-MM-AAAA`, com um ZIP de JSON por dia e faixa de horário (`cigadados_publicacoes_AAAA_MM_DD_HHMM_HHMM.zip`), publicações de 04/2022 em diante (também `domsc-edicoes-de-MM-AAAA`, com o PDF inteiro de cada edição desde 2009, até ~50 MB, não usado).
- **Acesso:** o `robots.txt` do portal de dados veda `/api/` (não usada) e pede `Crawl-Delay: 10`, respeitado (1 requisição a cada 10 s). Lemos a página do conjunto mensal (links de download) e os ZIPs.
- **Campos do JSON** (`autopublicacoes`): `codigo`, `titulo`, `data`, `municipio` (nome; nulo em consórcios), `entidade`, `categoria` (Portarias, Decretos, Leis, Licitações, Contratos, Ata de registro de preços, Outras publicações, Extratos Diversos...), `link` (página da publicação no DOM/SC), `texto` (HTML gerado pelo Apache Tika, com metadados no `<head>`) e `url` (PDF do ato).
- **Armadilhas:** (1) o município vem só como nome: resolvemos pelo `nome_chave` do IBGE em SC (229 de ~295 municípios apareceram em 3 dias). (2) Um lote do dia 07/10/2026 tinha 3.433 publicações, 2.890 delas "Ata de registro de preços" do consórcio CISAMVE (Blumenau) e 1.356 do CINCATARINA, sem município de prefeitura: filtramos por categoria de ato, por entidade (prefeitura, câmara, fundo, SAMAE...) e tiramos títulos de compras (homologação, licitação, contrato, pregão...), que citam o nome de quem contrata. (3) O texto das homologações cita "designado/nomeado" para comissões e dá falsos achados; o filtro de títulos reduziu isso. (4) Faixas do dia corrente ainda estão incompletas: os últimos 2 dias são baixados de novo.
- **O que guardamos:** só o recorte por lote (categorias de ato de prefeituras e câmaras) em `data/raw/domsc_ciga_atos/*.json.gz`, e as sugestões em `diario_ato` (link = PDF do ato). Últimos 90 dias na primeira carga.
- **Frequência:** semanal, só no acervo; sem agenda na VPS.
- **Uso:** `python -m ingestion.diarios.domsc [--dias 90] [--de-raw data/raw/domsc_ciga_atos]`.

### Plataformas que não conseguimos ler

FAMEM/SigaNet (MA), AMUNES (ES), DOEM e DOSP: bloqueio deliberado ou falha de segurança do servidor; nada é contornado. Pedidos em `docs/pedidos/diario_famem_ma.md`, `diario_amunes_es.md` e `diario_doem_dosp.md`. Motivos no levantamento.

## Diário Oficial da União, Seção 2: atos de pessoal (dou_atos)

- **O que é:** a "Base de Dados de Publicações do DOU" da Imprensa Nacional (`https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados`). **Acesso aberto, sem cadastro:** um ZIP por mês e seção (`S01MMAAAA.zip`, `S02MMAAAA.zip`, `S03MMAAAA.zip`), com um XML por matéria. Publicado, em tese, na primeira terça-feira do mês seguinte (em 2026-10-10 o de agosto existia e o de setembro ainda não). A Seção 2 é a de "atos de pessoal relativos aos servidores públicos". O XML não substitui a versão certificada (PDF).
- **Acesso, passo a passo:** a página da base escolhe ano e mês por parâmetro (`?ano=2025&mes=Março`, o mês em português, codificado em UTF-8; sem codificar dá 400). A resposta traz os três links de download no formato `https://www.in.gov.br/documents/49035712/<pasta>/S02032025.zip/<uuid>?version=1.0&t=<carimbo>&download=true`. O uuid e o carimbo mudam a cada publicação, então o link é lido da página a cada carga (`url_do_mes`), não montado.
- **O que NÃO usamos:** o INLABS (`https://inlabs.in.gov.br`, o diário do dia em XML) exige cadastro com e-mail e senha. Não foi contornado; o canal mensal aberto basta para o recorte e dá o histórico.
- **Tamanho:** a Seção 2 de agosto de 2026 tem 20,7 MB zipados e 16.368 matérias; a de março de 2025, 16,7 MB, 13.334 XML e algumas imagens (`.jpg`) que são ignoradas. Cada carga mensal é um download; o `download_cache` (incremental de `comum`, chave por mês) evita rebaixar o mês que não mudou.
- **Campos do XML** (`<article>`): `idMateria` (id da matéria), `id`, `name`, `pubName` (`DO2`), `artType` (Portaria, Despacho, Ato...), `pubDate` (dd/mm/aaaa), `artCategory` (o órgão, em hierarquia: "Poder Judiciário/Tribunal Regional do Trabalho da 4ª Região/Presidência"), `pdfPage` (link para a página da edição certificada), `editionNumber`, `numberPage`; e `<body><Texto>` com o HTML da matéria (parágrafos `<p>`, assinatura em `<p class="assina">`, cargo em `class="cargo"`).
- **Link oficial guardado:** o `pdfPage` (`pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp?data=...&jornal=529&pagina=...`), que abre a página da edição certificada onde o ato foi publicado. O endereço bonito da matéria (`/web/dou/-/portaria-n-424-de-...-615770827`) usa um id que **não** está no XML, então não dá para montá-lo (testado: 404). Várias matérias dividem a mesma página, por isso a chave do ato é `idMateria`, não a URL.
- **Armadilhas:**
  - BOM no início do XML (`utf-8-sig`) e XML ocasionalmente inválido (contado e ignorado).
  - **Nome dentro de nome maior.** Um nome de 3 palavras casa com um pedaço de outro ("Marcelo de Oliveira" em "Augusto Marcelo de Oliveira Santos"; "Ana Paula Ferreira" em "Ana Paula Ferreira de Carvalho"). A primeira versão tinha 475 achados em agosto de 2026; o filtro de vizinhança (palavra colada antes ou depois no mesmo estilo de caixa, pulando "de", "da"...) derrubou para 136.
  - **Assinatura e lotação.** A autoridade que assina (`class="assina"`) é descartada, e linha só com o nome (assinatura de decreto, ex.: o Presidente) também. Parlamentar como lotação ("no gabinete do(a) Deputado(a) Fulano") não é o alvo: o nomeado é o secretário parlamentar.
  - **Verbo de outro ato.** "Autorizar afastamento", "penalidade", "pensão", "prorrogar a designação", "vaga decorrente da exoneração de Fulano", "férias da titular": a palavra de ato existe, o ato sobre a pessoa não. O verbo tem de vir até 150 caracteres antes do nome (ou 60 depois), sem esses atos no meio.
  - **Homônimos.** O DOU traz servidores de todo o país; um nome comum ("Carlos Cezar da Silva") pode ser de outra pessoa que não a da base. O texto não traz CPF completo (vem mascarado). Por isso o achado é só sugestão.
- **O que guardamos (coleta mínima):** só Seção 2, desde 2025-01-01, só quando o texto cita o nome completo (3 palavras ou mais e único na base: nomes de duas pessoas são descartados) de uma pessoa da base numa matéria com palavra de ato (nomear, exonerar, designar, dispensar e flexões). Por achado, uma linha em `dou_ato`: pessoa sugerida, `idMateria`, data, tipo, órgão, tipo da matéria, trecho de até 500 caracteres, link oficial e `revisado = false`. O ZIP é lido em fluxo (um XML por vez) e não fica: o bruto é o recorte (as sugestões do mês, em JSON) mais o manifesto (URL, tamanho, sha256).
- **Regra crítica:** nome em texto nunca vira vínculo nem evento publicável. Fila: `python -m ingestion.revisar --tipo dou` (decisões em `data/dou_revisados.csv`, reaplicadas a cada carga e a cada carga de pessoas); aceito vira evento `ato_pessoal` com o link do DOU.
- **Frequência:** mensal. `python -m ingestion.dou.atos` (todos os meses desde 2025-01), `--mes 2026-08` (um mês), `--desde 2025-06`, `--de-raw arquivo.zip --mes AAAA-MM`.
- **Uso:** fila de revisão de atos de pessoal federais (nomeação, exoneração, designação, dispensa) ligados a quem acompanhamos.

## CPIs e CPMIs da Câmara, do Senado e do Congresso (cpis, cpi_indiciamentos)

- **O que é:** as comissões parlamentares de inquérito criadas desde 2019 (7 na Câmara, 10 no Senado, 3 mistas no Congresso Nacional), com objeto, datas, situação, presidente, vice-presidentes, relator, titulares e suplentes, e o link do relatório final quando a casa o publica. Tabelas `cpi`, `cpi_participacao` e, só como fila de revisão, `cpi_indiciamento_sugestao`.
- **Câmara (CPIs):**
  - `https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json`, com `codTipoOrgao` 4 (Comissão Parlamentar de Inquérito) e início desde 2019; `arquivos/orgaosDeputados/json/orgaosDeputados-L56.json` e `-L57.json` trazem os membros, com cargo (`Presidente`, `1º Vice-Presidente`, `Relator`, `Titular`, `Suplente`) e datas.
  - **O endpoint `/orgaos` da API não serve:** `?codTipoOrgao=4` devolve vazio, a lista paginada não traz as CPIs de 2019 a 2023 e `/orgaos/{id}/membros` vem vazio. Os arquivos em lote têm tudo.
  - O arquivo repete órgãos antigos com ids diferentes (as CPIs de 2003 a 2018 aparecem 2 e 3 vezes); de 2019 em diante, um id por CPI. O texto do objeto é o campo `nome` do órgão.
  - Relatório: a API não liga a CPI ao relatório. Achamos nas tramitações do requerimento de criação (`/proposicoes?siglaTipo=RCP`, 36 desde 2019, e `/proposicoes/{id}/tramitacoes`) a última apresentada na própria CPI (`siglaOrgao` = sigla da CPI, dentro da vida dela) cujo texto diz "relatório final", "relatório do relator" ou "parecer do relator"; diligências e requerimentos ficam de fora. É o relatório **do relator**: só a situação "Parecer aprovado" do órgão diz que a comissão o adotou (CPI do BNDES e de Brumadinho, 2019); nas outras ("Extinta") o relatório do relator foi rejeitado ou não votado.
- **Senado e Congresso (CPIs e CPMIs):**
  - Os endpoints de lista (`/comissao/lista/CPI`, `/comissao/lista/colegiados`) trazem só as **em atividade** (hoje: CPI da Violência Doméstica e CPI da Pedofilia, as duas criadas e "aguardando instalação", sem membros), e `/comissao/{codigo}` e `composicao/comissao/atual/mista/{codigo}` devolvem vazio para as encerradas. A forma de achar as encerradas é pelas comissões de cada senador: `/senador/lista/legislatura/{56,57}` (~330 senadores) e `/senador/{codigo}/comissoes` (sem `ativo`, vêm as atuais e as encerradas), filtrando as de nome ou sigla de inquérito com participação desde 2019 (`SiglaCasaComissao` SF = CPI, CN = CPMI).
  - A composição da API (`/composicao/comissao/{codigo}?ativas=N`) traz titular e suplente mas **não traz presidente nem relator**, e para CPMI só dá a legislatura atual. As páginas oficiais da comissão trazem tudo: `https://legis.senado.leg.br/comissoes/comissao?codcol={codigo}` (situação, finalidade, eventos com data de designação/instalação/prazo final e o link do relatório final) e `.../composicao_comissao?codcol={codigo}` (PRESIDENTE, VICE-PRESIDENTE, RELATOR/RELATORA e as vagas por bloco, com o link do perfil do senador ou do deputado). É HTML, lido por expressões regulares sobre a estrutura (`sf-atv-cmss-composicao-membro`); se o Senado trocar a página, os testes com recortes reais acusam.
  - **A composição é a última posição de cada vaga:** quem saiu no meio da CPI pode não constar. O prazo final registrado nem sempre é o encerramento.
- **Ligação à pessoa:** o id é o da casa de origem do parlamentar (link `deputados/{id}` na Câmara, perfil do senador no Senado; as CPMIs trazem os dois). 727 das 771 participações ligam a uma pessoa: pelo cadastro de parlamentares em exercício (`origem`, id oficial) e, para quem já saiu, pelo nome parlamentar ou de urna exato e único entre os eleitos para deputado federal e senador, **desde que a UF coincida** (`nome_parlamentar`). Ficam sem pessoa 44 (3 em cargos de direção: Rose de Freitas, Dário Berger e João H. Campos, ex-parlamentares fora do cadastro e sem nome único entre os eleitos).
- **Armadilhas:**
  - o Senado devolve objeto, e não lista, quando há um item só (um senador com uma comissão, uma CPI na lista);
  - a situação de CPI não instalada vem com defeito de acentuação ("Aguardando Instalac?o", corrigido na leitura), e a página de uma CPMI antiga pode trazer "Presidente: vago" no cabeçalho enquanto a composição mostra o presidente;
  - `Accept: application/json` faz a API do Senado devolver JSON; para as páginas HTML, o cabeçalho é trocado só nas duas requisições;
  - os links dos PDFs do relatório no Senado (`sdleg-getter/documento/download/...`) às vezes respondem com uma página de **verificação de segurança com prova de trabalho no navegador**. Não contornamos (docs/DECISOES.md): quando a resposta não é um PDF, a CPI é registrada como bloqueada. Na nossa carga, os da CPI da Pandemia e do BNDES vieram como PDF e o da CPMI do 8 de Janeiro não.
- **Linha do tempo:** um evento `cpi` por pessoa e comissão, com o maior papel (presidente, relator, vice-presidente, membro titular, membro suplente), a data de instalação, o objeto como a comissão o escreveu (até 400 caracteres) e o link da fonte. Sem juízo: ser membro de CPI não é fato sobre a pessoa além da participação. 655 eventos, 401 pessoas.
- **Indiciamentos (`cpi_indiciamentos`, manual):** pedido de indiciamento em relatório de CPI não é acusação formal nem condenação, e nome achado em PDF não é vínculo. Por isso **nenhum evento é gerado**: a extração (`pypdf`, texto do PDF) grava em `cpi_indiciamento_sugestao` o nome como está no relatório, o trecho (até 600 caracteres), a página e o link do PDF, com `revisado = false` e sem ligação a pessoa. Só entram relatórios adotados pela comissão (Câmara: parecer aprovado; Senado/Congresso: rótulo "aprovado"). Reconhece o título que termina em "indiciamento(s)" seguido de lista numerada (Brumadinho: `1) Vale S.A: art. ...`; Pandemia: `1) JAIR MESSIAS BOLSONARO – cargo - art. ...`) ou de marcadores com nomes em maiúsculas (BNDES). O nome sai como o PDF o extrai, inclusive com espaços no meio de palavras ("Figueir edo"), e a revisão corrige.
- **Resultado medido:**

| CPI | PDF | Sugestões | Conferência |
|---|---|---|---|
| Rompimento da Barragem de Brumadinho (Câmara, 2019) | 24 MB, 2.287 páginas (~50 s) | 24 (22 pessoas, 2 empresas) | lista numerada do item 10.4.3, 1 a 24 |
| Práticas ilícitas no BNDES (Câmara, 2019) | 7 MB, 395 páginas | 60 | marcadores do item 12.2.1; o relatório mistura "indiciamento" e "aprofundamento", e o trecho mostra qual |
| Pandemia (Senado, 2021) | 38 MB, 1.288 páginas | 80 (78 pessoas, 2 empresas) | resumo 13.27, 1 a 80, o total que o relatório indica |
| CPMI do 8 de Janeiro (2023) | resposta não era PDF | 0 | bloqueada pela verificação de segurança; com o PDF baixado à mão: `--pdf arquivo.pdf --cpi congresso:2606` |

- **Fora do recorte e por quê:** CPIs sem relatório adotado pela comissão (CPI do MST, Americanas, Pirâmides, Manipulação de Resultado em Partidas de Futebol e Óleo no Nordeste, na Câmara) não têm indiciamentos da comissão; no Senado, só relatório com rótulo "aprovado" (o da CPI do Crime Organizado diz "apresentado pelo relator" e ficou fora). O que o site mostra delas é só a participação.
- **Próximo passo (não feito):** a fila de revisão humana das sugestões, nos moldes de `python -m ingestion.revisar --tipo diario`: uma pessoa vê nome, trecho, página e PDF, liga o nome a uma pessoa por chave forte (homônimos!) ou recusa, e só então um evento descrevendo o ato ("citado em pedido de indiciamento no relatório final da CPI X, sem que isso signifique denúncia ou condenação", com o desfecho judicial quando houver) pode ser gerado. A decisão ficaria num CSV versionado (`data/indiciamentos_revisados.csv`) e reaplicada a cada carga.
- **Frequência:** `cpis` semanal (~330 consultas à API do Senado com pausa de 0,2 s e ~40 requisições à da Câmara; ~6 minutos); `cpi_indiciamentos` manual (baixa PDFs de dezenas de MB). Ambas rodam no acervo local, como `camara_etica` e `senado_etica`; não estão no `run_all` nem nos workflows de produção.
- **Tamanho:** `cpi` 104 kB, `cpi_participacao` 440 kB, `cpi_indiciamento_sugestao` 104 kB (164 linhas); bruto de ~3 MB (as páginas HTML das comissões ficam nele).

## ALEMA: Assembleia Legislativa do Maranhão

- **O SAPL (`sapl.al.ma.leg.br`) redireciona para o ALEMALEGIS** (`alemalegis.al.ma.leg.br`), um aplicativo Angular com API própria. Não é PLE/Nopapercloud.
- **API pública.** O script do aplicativo mostra as rotas `/api/v1/public/*` (sem login): `parliamentary`, `legislature`, `legislative-matter/filter/access?year=&page=&size=` (matérias com tipo, ementa, data e `authorNames`), `parliamentary-vote`, `plenary-session-presence`, `votes`. O servidor não publica `robots.txt` (a rota devolve a página do aplicativo).
- **Quem está no cargo:** a lista da API traz 155 registros de quatro legislaturas e um `ACTIVE` que não diz quem está em exercício; a lista do site (`www.al.ma.leg.br/sitealema/deputados/`, 41 cartões acima do título "Deputados licenciados") é a usada. O partido do site é o atual (a API guarda a filiação antiga de alguns).
- **Autoria** por nome exato: o autor da matéria é texto ("Dra Vivianne", "PODER EXECUTIVO"); ligamos pelo nome do site, pelo nome parlamentar ou civil do cadastro e por um apelido conferido. Matérias de 2026: 1.351 (634 indicações, 267 projetos de lei, 252 requerimentos...).
- **Não coletado:** votos nominais e presença (rotas existem; fora da coleta mínima).

## ALEMS: Assembleia Legislativa de Mato Grosso do Sul

- **Sem SAPL e sem API de proposições aberta.** O sistema de proposições (`sgpl.consulta.al.ms.gov.br/sgpl-publico`) mostra "Validando acesso..." (prova de trabalho contra automação, `sg-pow-captcha`). Não contornamos.
- **Deputados:** `al.ms.gov.br/Partidos/Lista` (24, agrupados por partido; o menu do site vem de `/api/v2/menu`). O `robots.txt` do site dá 404; o do portal da transparência libera tudo.
- **Gastos (CEAP):** `transparencia2.al.ms.gov.br/ceap/notas/exportar-csv?ano=AAAA`, o "Exportar todos os lançamentos (CSV)" do portal: 4 linhas de identificação, uma em branco e o cabeçalho (`Deputado;Ano;Mês;Categoria;CPF/CNPJ;Fornecedor;Documento;Emissão;"Valor (R$)";Comprovante`); valores como `R$ 4.669,65`; deputado como `Dep. Cel. David`. Somamos por deputado, mês e categoria. Nomes diferentes da lista de partidos (cinco) ficam em uma tabela de apelidos; sobram só lançamentos de quem saiu (ex.: Neno Razuk).

## ALRN: Assembleia Legislativa do Rio Grande do Norte

- **Sem SAPL** (`sapl.al.rn.leg.br` não resolve). O processo legislativo (`legispad.al.rn.leg.br`) pede login; o portal de Transparência Legislativa (`transparencialegislativa.al.rn.leg.br`, React) chama uma API aberta.
- **API:** `api-transparencialegislativa.al.rn.leg.br/elegis-api-transp-legislativa/`: `parlamentar/` (24 em exercício; traz CPF, que não guardamos), `processo?iniciativa=ID&pagina=&tamanhoPagina=` (da mais nova para a mais antiga), `processo/ultimas-votacoes`, `reuniao/presenca/ID`. Cada página de 100 leva ~5 s.
- **Deputados:** cartões de `al.rn.leg.br/deputados` (nome, partido, foto); `robots.txt` do site libera tudo. Projetos: tipos `PL`, `PLC`, `PEC`, `PDL`, `PR`; requerimentos e pedidos de informação só em contagem.
- **Gastos (verbas de ressarcimento, 20/10/2026):** `https://www.al.rn.leg.br/portal/verbas` é um formulário (Laravel) com `_token` na própria página e cookie de sessão; `POST /portal/verbas/busca` com `mes_id` (vazio = todos os meses) e `deputado_id` devolve uma tabela `Data da nota; Título (fornecedor); Deputado; Valor` (valor `3500.00`, às vezes `.01`), com todas as notas desde 2009 (200 KB por deputado). Sem tipo de gasto: categoria única; fornecedor (pode ser pessoa) não é guardado. O seletor tem 47 deputados (ex-deputados incluídos); buscamos os que casam por nome exato com a lista de hoje (24). Dados até 30/09/2026. **Armadilha:** há nota com data de 25/09/2029 (erro da fonte, R$ 1.520): vai para `gasto_local_fora`, não vira gasto de 2029. Bruto: zip (formulário + uma página por deputado) em `data/raw/alrn/verbas_*.zip`; `--de-raw` reprocessa.

## ALESE: Assembleia Legislativa de Sergipe

- **Sem SAPL.** O Processo Legislativo (SPL, ASP.NET) está em `aleselegis.al.se.leg.br/spl/`; `robots.txt` libera tudo. A consulta de proposições só responde a envio de formulário com `__VIEWSTATE`, sem rota de listagem; não coletamos.
- **Deputados:** `al.se.leg.br/deputados/` (24 cartões com partido, foto e o código do SPL). **Presença:** a aba "Frequência em Plenário" de `parlamentar.aspx?id=` traz presente/falta/falta justificada/licenciado do ano corrente.
- **Acesso (27/10/2026):** geobloqueio de fora do Brasil; a carga roda na VPS de São Paulo (`camaras.sh`), sem contorno. Carga conferida do Brasil: 24 deputados (as 24 cadeiras).

## ALAP: Assembleia Legislativa do Amapá

- **Sem SAPL.** Site `al.ap.leg.br` (o `robots.txt` responde 403 a qualquer cliente; as páginas públicas respondem normalmente) e o portal do eLegis `elegis.al.ap.leg.br/portal` (robots libera tudo), que avisa estar migrando o processo legislativo.
- **Deputados:** `pagina.php?pg=exibir_legislatura` (24; nome, nome completo e partido na dica da foto). **Gastos (CEAP): não coletados.** A tela `transparencia/gabinete_ceap_json.php` / `pagina.php?pg=ceap` existe, mas o `robots.txt` responde 403 (também ao User-Agent do projeto): não confirmamos permissão e não lemos. Pedido em `docs/pedidos/alap_gastos_ceap.md`. **Projetos:** `portal/proposicoes?tipo_proposicao=T&ano=AAAA&page=N` (GET, 50 por página; códigos 1 lei ordinária, 2 complementar, 4 PEC, 10 decreto legislativo, 9 resolução).

## ALEGO: Assembleia Legislativa de Goiás

- **A página de dados abertos** (`transparencia.al.go.leg.br/dados-abertos`, AngularJS) tem as rotas JSON listadas no script `application.transparencia-*.js`: diárias, servidores, execução orçamentária, licitações, contratos, **verba indenizatória** (`api/transparencia/verbas_indenizatorias.json?ano=&mes=&todos=true`; `verbas_indenizatorias/periodos` lista os meses), entre outras. Não há rota de proposições, votos ou presença (o item "Requerimentos" aponta para a página inicial).
- **Deputados em exercício:** `portal.al.go.leg.br/deputados/em-exercicio` (tabela no servidor; 42 linhas, nome, partido, telefones, e-mail). O portal responde 500 a `Accept: application/json` puro. O código do deputado é o mesmo nas duas bases. Verba: valor apresentado e valor indenizado por mês (usamos o indenizado).

## Receita Federal: cadastro de empresas por CNPJ (receita_empresas)

- **URL:** `https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/AAAA-MM/` (compartilhamento `index.php/s/gn672Ad4CF8N6TK`; WebDAV com o token como usuário e senha vazia; `PROPFIND` lista as pastas). Dados abertos, sem cadastro. 2026-10: 7,8 GB (Empresas0-9 ~1,4 GB, Estabelecimentos0-9 ~5,7 GB, Socios, Simples, tabelas de códigos).
- **Formato:** zip com um CSV sem cabeçalho, latin-1, separador `;` e aspas. Empresas: raiz (8), razão social, natureza jurídica, qualificação, capital, porte, ente federativo. Estabelecimentos: raiz, ordem (4), dígitos (2), matriz/filial, nome fantasia, situação (01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada), ..., UF (coluna 20), município (coluna 21, código da Receita). Municipios.zip e Naturezas.zip traduzem os códigos.
- **Armadilhas:** o município é código da Receita, não IBGE (liga por nome + UF com `municipio`); a razão social de MEI traz o CPF do titular ("NOME 12345678901"); algumas trazem a raiz do CNPJ no lugar do CPF; o arquivo Estabelecimentos0 tem 2,3 GB e o servidor é lento (~3 MB/s), e a conexão pode travar sem erro; o CNPJ passa a ter letras (alfanumérico) desde julho de 2026.
- **O que guardamos (coleta mínima):** só os CNPJs que aparecem em tabelas do projeto (ver DECISOES.md, 18/10/2026): razão social (omitida se MEI com CPF), nome fantasia, natureza jurídica, situação, UF, município IBGE. Tabela `empresa`; bruto = recorte em `data/raw/receita_empresas/`.
- **Frequência:** mensal (a Receita publica uma pasta por mês). Fallback `--brasilapi` para CNPJ novo (`https://brasilapi.com.br/api/cnpj/v1/{cnpj}`, 1,5 s entre consultas).

## Tesouro Nacional: transferências obrigatórias da União (tesouro_transferencias)

- **URL:** CKAN do Tesouro Transparente, `https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id=...`, três conjuntos (nomes de arquivo estáveis; a URL de download sai do `package_show`): `transferencias-obrigatorias-da-uniao` (um CSV por tributo, linhas = estados, colunas = meses `janeiro/24`, desde 1991), `transferencias-obrigatorias-da-uniao-por-municipio` (linha = município x mês, colunas = anos) e `lista-de-municipios-do-siafi` (`tabmun.csv`).
- **Formato:** CSV latin-1 (a leitura tenta UTF-8 antes), `;`, cabeçalhos antes da tabela nos arquivos por estado, decimal com vírgula, milhar com ponto, `-` = vazio.
- **Campos usados:** por estado: `fpe`, `ipi-exp`, `cideest`, `iofest`, `lc176est` (e `fpm`, só para conferir a soma dos municípios); por município: `fpm`, `cide`, `iof`, `itr`, `lc-176`. Código do município (SIAFI), UF, mês, ano e valor.
- **Blocos (tabela `transferencia_uniao`, `fonte = "tesouro"`):** FPE e IPI_EXP só por UF; FPM só por município (a soma da UF é conferida contra `fpm.csv`); OUTRAS_OBRIG (CIDE, IOF-Ouro, ITR, LC 176) com a parte dos estados (sem município) e a dos municípios, sem sobreposição. Nunca os dois níveis para o mesmo bloco, para somar por UF não contar em dobro. FEX e Kandir estão zerados desde 2019 e não são lidos; o `fundeb-por-municipio` é o fundo inteiro (impostos de estados e municípios), não repasse da União, e também não entra.
- **Valores líquidos do Fundeb:** FPE, FPM e IPI-Exp vêm descontados da retenção de 20% do Fundeb. O município contabiliza mais (FPM de 2024: R$ 177 bi aqui; ~R$ 214 bi brutos na contabilidade dele). A complementação da União ao Fundeb entra à parte (Portal, abaixo).
- **Ligação SIAFI para IBGE:** o código da cidade é o do SIAFI (4 dígitos), não o do IBGE. Liga só pela tabela oficial `tabmun.csv` (SIAFI;CNPJ;nome;UF;IBGE), nunca pelo nome. Código fora da tabela ou com UF diferente fica sem município (o valor continua na UF) e entra nos alertas da carga.
- **Ano com 2 dígitos** nos arquivos por estado (`janeiro/24`; 51 a 99 = 1951 a 1999). IPI-Exp: só a parte dos estados.
- **Coleta mínima:** o bruto é um recorte em zip (colunas de 2019 em diante, linhas de UF e município) em `data/raw/tesouro_transferencias/`; `--de-raw` reprocessa sem rede. A carga sincroniza por diferença (insere o novo, corrige o que mudou, apaga o que sumiu).
- **Frequência:** mensal. Sem `--ano`, relê o ano anterior e o atual; a carga inicial passa todos (`--ano 2019 2020 ...`).

## Portal da Transparência: transferências (portal_transferencias)

- **URL:** `https://portaldatransparencia.gov.br/download-de-dados/transferencias/AAAAMM`, que redireciona para o zip em `dadosabertos-download.cgu.gov.br`. A página `.../download-de-dados/transferencias` lista os meses publicados (`arquivos.push({"ano","mes","origem"})`; em 20/10/2026 ia até 2026-10).
- **Formato:** zip com um CSV, `;`, latin-1, 2 a 7 MB por mês (200 a 500 mil linhas). Uma linha por favorecido x ação x localizador; guardamos só a soma por UF x município x bloco x mês. Nome de coluna com acento. Decimal com vírgula e sem milhar.
- **Campos usados:** `ANO / MÊS`, `UF`, `CÓDIGO MUNICÍPIO SIAFI`, `NOME MUNICÍPIO`, `TIPO TRANSFERÊNCIA`, `AÇÃO`, `NOME AÇÃO`, `VALOR TRANSFERIDO`.
- **Blocos (`fonte = "portal"`):** FUNDEB_UNIAO (complementação da União ao Fundeb: ação 0E36 até 2020, 00SB desde 2022); ROYALTIES (ações 0A53 petróleo e gás, 0547 recursos minerais, 0546 recursos hídricos, 0223 Itaipu); LEGAIS_VOLUNTARIAS (toda a categoria "Legais, Voluntárias e Específicas": convênios, mas também fundo a fundo do SUS, PNAE, salário-educação, auxílios da LC 173/2020 e transferências especiais; não é só convênio).
- **Ficam de fora, de propósito:** FPE, FPM, IPI-Exp e as demais obrigatórias (valem pelo Tesouro); a transferência ao Fundeb de estados e municípios (ação 0C33, o fundo inteiro); e as ações constitucionais que não são nenhuma das acima.
- **Ligação ao IBGE:** código SIAFI pela mesma tabela oficial do Tesouro (`tabmun.csv`, lida do último recorte do Tesouro carregado), nunca pelo nome. Favorecido estadual vem sem município.
- **`uf = "ND"`:** linha sem UF válida entra como "não regionalizada", para o total fechar com o Portal (2024: ~R$ 5,3 bi em LEGAIS_VOLUNTARIAS). O significado exato não está documentado na fonte. O site soma o valor no Brasil (campo `brasil.sem_estado` da API) e nunca o atribui a estado ou cidade.
- **Ação "-1" (Sem informação)** na categoria constitucional: em 2021 são R$ 23,1 bi que o Portal não classifica, entre eles a complementação ao Fundeb. Não se adivinha: o Fundeb de 2021 fica sem valor (nunca zero) e o total sem ação entra nos alertas da carga.
- **Diferenças Portal x Tesouro:** 2020 (MP 938, auxílio financeiro de compensação a estados e municípios); 2023 (compensação do ICMS, ação 00VP); 2025 (parcela adicional do FPM). Cada número bate com a fonte de origem e não se ajusta; o recorte por bloco (acima) define em qual fonte cada valor entra, e o que ficou sem bloco é dito no site.
- **WAF e pausa:** depois de algumas dezenas de pedidos seguidos ao mesmo IP o Portal responde 405 ("Human Verification"), e 403/405 também valem para mês não publicado. Um download por vez, `PAUSA` de 20 s entre meses; no primeiro bloqueio a carga PARA e registra erro em `fonte_ingestao`. Sem repetir, trocar de IP ou disfarçar o cliente. Mês fora da lista da página nem é pedido.
- **Tamanho:** `transferencia_uniao` (Tesouro e Portal) tem ~1,2 milhão de linhas mensais no acervo, ~137 MB com índices.
- **Coleta mínima:** o bruto é o recorte do mês (CSV gz com a soma por UF x município x bloco) em `data/raw/portal_transferencias/AAAAMM_*`; `--de-raw` reprocessa um mês.
- **Frequência:** mensal. Sem `--ano`, baixa de novo os 3 últimos meses publicados (o Portal os corrige); mês antigo já carregado é pulado (`--refazer` força).

## Acervo: cargas incrementais e conferência

- **Arquivos que mudam pouco** (TSE, CGU, TCU, TCE-SP, TCE-RS) não são baixados nem recarregados quando nada mudou: o acervo guarda ETag, Last-Modified e sha256 do último download (tabela `download_cache`) e pergunta ao servidor antes. Sem mudança, `fonte_ingestao` ganha uma linha com status `sem_mudanca` e o bruto não se repete. `python -m ingestion.acervo rodar --forcar` ignora o cache.
- **Conferência por carga:** `fonte_ingestao.total_fonte` (total informado pela fonte ou linhas do arquivo) e `alertas` (campo-chave vazio, repetidos, total que não bate). Aparecem no `python -m ingestion.acervo relatorio` e como `[alerta]` ao rodar.
- Detalhes e motivos em [DECISOES.md](DECISOES.md), "carga incremental e conferência da carga".

## A confirmar (fases seguintes)

### Emendas de relator-geral (RP9, "orçamento secreto") e de comissão (RP8) — Congresso / CMO

Reconhecimento (2026-10-11):

- **Portal da Transparência (arquivo de emendas que já carregamos):** traz RP9 como "Emenda de Relator" (2016–2022; 2020: R$ 21,2 bi, 2021: R$ 16,7 bi, 2022: R$ 8,6 bi empenhados) e RP8 como "Emenda de Comissão". **O autor é sempre "RELATOR GERAL" (ou "Sem informação") nas de relator e o nome da comissão nas de comissão**: não há o parlamentar que pediu. Por isso o carregamento das emendas (a partir de 2023) nunca ligou essas linhas a ninguém.
- **Siga Brasil (Senado):** painéis de execução orçamentária; a classificação RP9 aparece, mas sem solicitante (o relator-geral era o autor formal; o Senado declarou ao STF não ter banco com os solicitantes). Sem fonte aberta de solicitante ali.
- **CMO (Comissão Mista de Orçamento), páginas "Indicações para execução orçamentária em RP9" (Câmara dos Deputados, `www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/`):**
  - **LOA 2022 (usada):** `…/EXECUCAO-RP9/LOA-2022/Relacao-de-indicacoes-Consolidado.xlsx` (xlsx de 2,9 MB, 16.636 indicações, publicado por força do Ato Conjunto das Mesas 1/2021 e da decisão do STF na ADPF 854). Colunas: Número, Ano, Data de cadastro, **Autor** (nome civil), **Tipo autor** (Deputado 11.026, Senador 2.403, "Usuario Externo" 3.207), CNPJ, nome e UF do beneficiário, órgão, unidade, ação, objeto, justificativa, GND, **Valor Solicitado**, Etapa ("Com indicação"). Mesmas linhas divididas em 56 listas (`…/LOA-2022/<data>/1-0NN-Relacao-de-indicacoes.xlsx`) e ofícios OFINDRP9.
  - **LOA 2021 (não usada):** 34 listas com xlsx de beneficiários **sem autor** (código CMO, órgão, ação, favorecido, CNPJ, valor) e um PDF de "solicitações" com 11 MB de cartas escaneadas/texto livre (ofício de prefeito a "Senador Márcio Bittar, Relator-Geral"), sem tabela que ligue cada carta a uma linha da relação. A maioria é de prefeitos, não de parlamentares. Sem estrutura, o vínculo seria palpite.
  - **LOA 2020:** só os anexos do Ato Conjunto (execução por emenda, beneficiário e objeto, autor "Relator Geral"); sem solicitante.
- **Emendas de comissão (RP8):** nenhum registro aberto que nomeie o parlamentar que pediu; o autor oficial é a comissão. Não implementado.

Armadilhas do xlsx: cabeçalho com erro de digitação ("Cnpj beneficário"; o leitor acha a coluna pelo prefixo); datas em número serial do Excel; autor em **nome civil** ("Iraja Silvestre Filho"), diferente do nome parlamentar; vários autores da legislatura passada que não estão na base; valor é o **solicitado** (não há empenho nem pagamento por indicação); servidor da Câmara responde 406 a `Accept: application/json` (a carga manda `*/*`). O servidor informa ETag/Last-Modified (arquivo de 24/10/2022), então o download incremental só baixa de novo se mudar.

Coleta: só Deputado e Senador (usuário externo = prefeito, entidade ou particular, fica de fora), ligados à base pelo nome civil ou parlamentar sem acentos, **na mesma Casa, correspondência exata e única**. Resultado: 13.429 indicações de parlamentares → 7.918 ligadas a 235 parlamentares da base (R$ 5,07 bi indicados), 5.511 de autores fora da base (deputados e senadores da legislatura anterior), 0 ambíguas. Tabela `emenda_relator_indicacao` (4,7 MB). Módulo `ingestion/congresso/emendas_relator.py` (xlsx lido com zip + xml da biblioteca padrão).

## Discursos em Plenário: o que a ingestão guarda (21/10/2026)

Aplica-se às seções "Câmara: discursos em Plenário" e "Senado: discursos em Plenário" do reconhecimento.

- **Câmara (`camara_discursos`):** API por deputado, 100 itens por página (`links` com `rel=next`), pausa de 0,3 s. O bruto (`data/raw/camara_discursos/*.json`) guarda `dataHoraInicio`, fase (`faseEvento.titulo`), `tipoDiscurso`, `urlTexto`, `urlVideo`, `keywords` e `sumario`; a `transcricao` é descartada no download. `urlVideo` e `urlTexto` vêm nulos com frequência.
- **Senado (`senado_discursos`):** a resposta pode trazer `Sessao` e `Pronunciamento` como objeto (item único) ou lista; as sessões do Congresso (`SiglaCasa` CN) e os pronunciamentos sem `CodigoParlamentar` (autoridades, convidados) ficam de fora. `Data` só tem o dia.
- A resposta do período é guardada no bruto como veio, junto com a janela (`inicio`, `fim`, `completa`).

## Pauta e tramitação: como o conector lê (21/10/2026)

Detalhes do que o reconhecimento achou estão nas seções "pauta do Plenário" e "tramitação" desta data; aqui, só o que a carga real acrescentou.

- **Módulos:** `ingestion/camara/pauta.py`, `senado/pauta.py`, `camara/tramitacoes.py`, `senado/tramitacoes.py` (peças comuns em `ingestion/pauta_comum.py`). Fontes `camara_pauta`, `senado_pauta`, `camara_tramitacoes`, `senado_tramitacoes`, diárias, no `run_all` e no `fontes.toml`. Bruto em `data/raw/<fonte>/*.json` (pauta: a resposta das duas Casas; tramitação: só as proposições que mudaram, com a ficha, a tramitação e o relator). `--de-raw` reprocessa sem rede; `--todas` (tramitação) é só do acervo.
- **Câmara, pauta:** o campo `relator` do item é um objeto com `nome`; `proposicao_` pode ser PAR ou PEP (parecer de plenário), não só nas MPV, e então a matéria vem em `proposicaoRelacionada_`.
- **Câmara, ficha:** `statusProposicao.sequencia` pode ser maior que a última `sequencia` de `/tramitacoes` e a `dataHora` do status é só a data (00:00) enquanto a linha tem hora; a marca do incremental usa o status da ficha.
- **Câmara, relator:** a ficha só traz `uriUltimoRelator`; o nome vem de `/deputados/{id}` (`ultimoStatus.nomeEleitoral`).
- **Senado, ponte de ids:** `/processo?codigoMateria={codigo}` devolve uma lista com o `id` do processo (idProcesso), o `codigoMateria` e `dataUltimaAtualizacao`. Para uma parte dos processos (27 de 167 das votadas) esse campo vem ausente.
- **Senado, informes:** `autuacoes[].informesLegislativos[]` tem `data` com hora ("2025-05-08 17:40:03"), `colegiado.sigla` e `descricao`; `documentosAssociados` é o grosso do peso (50 KB por processo) e não é usado. A situação de cada linha é a de `autuacoes[].situacoes[]` vigente na data (início e fim).
- **Senado, agenda:** `Materias` é objeto (não lista) quando a sessão tem uma matéria só; `SequenciaOrdem` repete em sessões com extrapauta; `DescricaoIdentificacaoMateria` para requerimento de comissão vem como "REQ 341/2026 - CDIR".
- **Textos reais de tramitação** (para o mapa de etapas): ver o relatório da onda 2; os mais frequentes na Câmara são "Apresentação de Requerimento", "Recebimento - Relator(a)", "Encerramentos", "Parecer do(a) Relator(a)", "Designação de Relator(a)", "Encaminhamento da Votação", "Aprovação de Proposição (Plenário)", "Votação (Plenário)", "Distribuição", "Apensação"; no Senado não há tipo, só o texto do informe ("Recebido, nesta data, na Comissão.", "A matéria vai à Comissão de ...", "Concluída a instrução ...", "Incluída em Ordem do Dia da Sessão ...").

## Câmaras de fornecedores com muitas cidades pequenas (`fornecedores_cobertura_camaras`, 27/10/2026)

Módulo `ingestion.camaras.fornecedores_cobertura`; as cidades vêm do catálogo (`tipo = sistema_legislativo`, coluna `sistema`). Frequência semanal (`camaras.sh`). Só vereadores em exercício e partido; projetos, votos e presença não têm formato aberto nesses portais. Pausa de 2 s, `robots.txt` conferido, resposta tem de ficar no mesmo site.

| Sistema | Cidades | Onde está o dado | Armadilhas |
|---|---|---|---|
| `webservicesistemas` | MA, 15 | `GET /api/vereadores` (JSON do próprio site Nuxt): `nome`, `nome_eleicao`, `partido.sigla`, `status` | só `status = published`; `descricao`/`biografia` são HTML longo e e-mail/telefone ficam de fora |
| `sts` (STS Informática) | PI, 9 | `/<câmara>/acessoinformacao/parlamentares`: tabela nome civil, nome parlamentar, partido | o link da ficha é `parlamentar?id=` ou `parlamentar/?id=`; o nome parlamentar às vezes vem em caixa alta com "VEREADOR " na frente |
| `cespro` (modelo `/site`) | RS, 19 | `/site/vereadores`: links `/site/vereadores/<id>-<slug>` com o nome (muitas vezes com a sigla entre parênteses); a ficha tem `Partido:` | o slug pode vir vazio (`<id>-`); a lista traz comissões, bancadas e "Mesa Diretora" como se fossem vereadores (filtrados); sigla colada ("Joel Welter-pt"); "LICENCIADO" no nome; a ficha traz data de nascimento (não lida) |
| `icamaras` | RS, 6 | `/vereadores`: cartões `<!-- VEREADOR -->` com partido no `title` da imagem | titulares e suplentes sem rótulo: em exercício só quem casa com um eleito vereador da cidade no TSE 2024 (`confirmar_pelo_tse`) |
| `portalfacil` (Actcon) | MG, 6 | capa leva a `/parlamentares/legislatura/<id>-2025-2028/3` (ou `/parlamentares`): `divparlamentar` com a legenda da bandeira = partido | cada vereador aparece em várias abas; o partido só está na aba "Partido político"; páginas em cp1252 |
| `ingadigital` | PR, 9 | capa tem o link "VEREADORES" com `?sessao=<código>` (muda); a página lista nomes por legislatura | sem partido na maioria; algumas escrevem "Nome - MDB - PRESIDENTE"; um domínio passou a redirecionar para outro site (recusado) |

Descoberta dos sistemas: `ingestion.canais.descobrir_sistemas` (assinaturas no HTML, DNS antes de abrir o site) e `data/cidades_sem_canal_sistemas.csv`.


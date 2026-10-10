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
- **Levantamento das outras assembleias** (09/10/2026): ALERJ, ALRS e ALBA não têm portal de dados abertos achável (endereços testados dão 404, 500 ou não resolvem). A API da ALEP (`webservices.assembleia.pr.leg.br/api/public/`) usa certificado HTTPS autoassinado: desligar a verificação tiraria a garantia de que o dado vem da Assembleia, então fica pendente. Um estudo de 2025 ("Democracia em Formato JSON", preprint SciELO) compara as APIs das 26 assembleias e da CLDF; é o ponto de partida do levantamento casa a casa.

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
  - Só 8 a 9 dos 24 deputados aparecem nos arquivos.

## ALESC: Assembleia Legislativa de Santa Catarina

- **Sem API nem exportação.** Lemos as páginas públicas, uma por vez, com pausa:
  - deputados: `https://www.alesc.sc.gov.br/deputados` (cartões com nome, partido e foto; 40);
  - proposições: o e-Legis, `https://portalelegis.alesc.sc.gov.br/proposicoes/processo-legislativo` (projetos) e `/proposicoes/atividade-parlamentar` (requerimentos, indicações, moções, pedidos de informação…), 10 por página, `?inicio=AAAA-MM-DD&fim=AAAA-MM-DD&page=N`. O parâmetro `ano` é ignorado: o formulário converte o ano em `inicio` e `fim` no navegador.
- **Volume (2025 e 2026 até outubro):** ~1.760 proposições do processo legislativo e ~11.900 da atividade parlamentar, ou cerca de 1.370 páginas.
- **Cada cartão:** número ("PL./0640/2026", "RQS/0012/2026"), ementa, data de entrada, autoria ("Deputado Altair Silva", às vezes vários), setor e situação atual.
- **Siglas** (conferidas pelo filtro de tipo do próprio e-Legis): PL. projeto de lei, PLC complementar, PEC, PRS resolução, PDL decreto legislativo, RQS requerimento, RCC requerimento de comissões, RQC requerimento de frente/fórum/CPI/comissão mista, IND indicação, MOC moção, PIC pedido de informação, OFL ofício legislativo, PSA proposta de sustação de ato.
- **Sem votos, presença nem gastos** nessas páginas.

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
- **Resultado (carga real no banco local):** modelo PHP 47 vereadores (Amapá 9, Ferreira Gomes 9, Tartarugalzinho 9, Fortim 11, Poranga 9), todos com partido e ligados ao eleito do TSE; CR2 52 (Beruri 11, Itamarandiba 13, Benevides 13, São Miguel do Guamá 15), todos com partido, 50 ligados ao TSE (em Itamarandiba, 2 de 13 não ligaram: Márcio Daniel Morais e Nelson Alves Correira).

## ALES: Assembleia Legislativa do Espírito Santo

- **Mesma API da ALBA** (Processo Legislativo Eletrônico da Nopapercloud), em `https://www3.al.es.gov.br/api/publico/` (o link "Dados Abertos" do portal aponta para `dados-abertos.aspx`, que o `www.al.es.gov.br` não serve). `robots.txt` inexistente (404). JSON, sem chave:
  - `GET parlamentar/?pag=1&qtd=200`: 35 registros: 30 com situação `Ativos` (as 30 cadeiras), 3 suplentes e 2 titulares que saíram. Campos como os da ALBA, com `autorID`, `parlamentarRazaoSocial` e `frequenciaPlenario`. Diferenças: a situação é `Ativos` (plural) e a paginação vem como `paginacao`;
  - `GET proposicao/?pag=&qtd=100&ano=AAAA&sigla=XX`: a API aceita filtrar por `sigla`, `tipoId` e `autorId`. **Sem filtro, o ano tem ~5.400 documentos** (ofícios de comenda, justificativas de ausência, atas, pautas...) e cada página de 100 leva cerca de 12 segundos; por isso o conector pede só os tipos que interessam. Em 2025: PL 925, PLC 45, PEC 4, PDL 156, PR 29, REQ 64, RQI 172, IND 1.704;
  - **Frequência:** os nomes são `Presente`, `Ausência`, `Ausência Justificada`, `Falta`, `Licenciado`, `Afastado` e `Governador Interino`. Sessões = presenças + faltas + ausências (justificadas ou não), como na ALBA.
- **Armadilhas:** o autor da proposição traz o nome digitado à mão (ex.: "Engenherio José Esmeraldo"), então o nome nem sempre casa com a razão social do deputado; o `autorId` da proposição casa com o `autorID` do parlamentar e serve de segunda chave. O autor traz CPF/CNPJ e endereço, que não guardamos.
- **Sem votos nominais** (só o "Boletim de Votação Nominal" em PDF) e **sem verba de gabinete** nos dados abertos. O portal de transparência tem cotas parlamentares (`/Transparencia/CotasParlamentares`), não lidas.

## ALECE: Assembleia Legislativa do Ceará

- **Sem dados abertos legislativos.** `robots.txt` do site libera tudo menos downloads de imagens. A API do portal da transparência (`transparencia.al.ce.gov.br/api`, OpenAPI em `/docs?api-docs.json`) só tem contratos, empenhos, licitações, pagamentos e termos de credenciamento. Lemos páginas públicas, uma por vez:
  - lista: `https://www.al.ce.gov.br/deputados`: cartões `deputado_card` (classe `licenciado` para os 6 titulares afastados) e, depois do título "Suplentes em Exercício", os 6 suplentes. Em exercício: 40 + 6 = 46;
  - ficha: `https://www.al.ce.gov.br/deputados/{slug}` (e-mail e telefones do gabinete);
  - projetos: o sistema antigo `https://www2.al.ce.gov.br/legislativo/proposicoes/ano.php?nome=31_legislatura&tabela={projeto_lei|projeto_compl|projeto_emen|projeto_decre|projeto_reso}&opcao=T&absolutepage=N`, 15 registros por página, ordem aproximadamente cronológica (a mais recente no fim). Campos: número/ano (`572/26`), autor, data de entrada, ementa (com link do texto), situação (`OBS`). **Armadilhas:** o autor vem em formatos diferentes (`AUTORIA: DEPUTADO FULANO.`, `Autoria: Deputado Fulano.`, só o nome); a página mistura UTF-8 e Windows-1252; há linhas tortas (`572/256`), ignoradas; nem todo projeto tem o texto publicado (usamos o endereço da listagem);
  - votação nominal: `transparencia.al.ce.gov.br/consultas-gerais/votacao-nominal` lista as matérias e dá um PDF e uma planilha por matéria, mas a planilha é o relatório de impressão (títulos, mesclas e o voto espalhado por colunas de partido): não lemos;
  - verba de desempenho parlamentar: `/despesas/verba-desempenho-parlamentar` lista os deputados e abre um modal por mês com o detalhe em PDF: não lemos.
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

## ALESE: Assembleia Legislativa de Sergipe

- **Sem SAPL.** O Processo Legislativo (SPL, ASP.NET) está em `aleselegis.al.se.leg.br/spl/`; `robots.txt` libera tudo. A consulta de proposições só responde a envio de formulário com `__VIEWSTATE`, sem rota de listagem; não coletamos.
- **Deputados:** `al.se.leg.br/deputados/` (24 cartões com partido, foto e o código do SPL). **Presença:** a aba "Frequência em Plenário" de `parlamentar.aspx?id=` traz presente/falta/falta justificada/licenciado do ano corrente.

## ALAP: Assembleia Legislativa do Amapá

- **Sem SAPL.** Site `al.ap.leg.br` (o `robots.txt` responde 403 a qualquer cliente; as páginas públicas respondem normalmente) e o portal do eLegis `elegis.al.ap.leg.br/portal` (robots libera tudo), que avisa estar migrando o processo legislativo.
- **Deputados:** `pagina.php?pg=exibir_legislatura` (24; nome, nome completo e partido na dica da foto). **Projetos:** `portal/proposicoes?tipo_proposicao=T&ano=AAAA&page=N` (GET, 50 por página; códigos 1 lei ordinária, 2 complementar, 4 PEC, 10 decreto legislativo, 9 resolução).

## ALEGO: Assembleia Legislativa de Goiás

- **A página de dados abertos** (`transparencia.al.go.leg.br/dados-abertos`, AngularJS) tem as rotas JSON listadas no script `application.transparencia-*.js`: diárias, servidores, execução orçamentária, licitações, contratos, **verba indenizatória** (`api/transparencia/verbas_indenizatorias.json?ano=&mes=&todos=true`; `verbas_indenizatorias/periodos` lista os meses), entre outras. Não há rota de proposições, votos ou presença (o item "Requerimentos" aponta para a página inicial).
- **Deputados em exercício:** `portal.al.go.leg.br/deputados/em-exercicio` (tabela no servidor; 42 linhas, nome, partido, telefones, e-mail). O portal responde 500 a `Accept: application/json` puro. O código do deputado é o mesmo nas duas bases. Verba: valor apresentado e valor indenizado por mês (usamos o indenizado).

## Acervo: cargas incrementais e conferência

- **Arquivos que mudam pouco** (TSE, CGU, TCU, TCE-SP, TCE-RS) não são baixados nem recarregados quando nada mudou: o acervo guarda ETag, Last-Modified e sha256 do último download (tabela `download_cache`) e pergunta ao servidor antes. Sem mudança, `fonte_ingestao` ganha uma linha com status `sem_mudanca` e o bruto não se repete. `python -m ingestion.acervo rodar --forcar` ignora o cache.
- **Conferência por carga:** `fonte_ingestao.total_fonte` (total informado pela fonte ou linhas do arquivo) e `alertas` (campo-chave vazio, repetidos, total que não bate). Aparecem no `python -m ingestion.acervo relatorio` e como `[alerta]` ao rodar.
- Detalhes e motivos em [DECISOES.md](DECISOES.md), "carga incremental e conferência da carga".

## A confirmar (fases seguintes)

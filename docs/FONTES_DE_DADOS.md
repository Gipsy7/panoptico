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

## A confirmar (fases seguintes)

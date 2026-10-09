# Registro de decisões

## 2026-10-06: stack inicial

| Tema | Escolha | Motivo |
|---|---|---|
| Postgres em dev | PostgreSQL 18 nativo, banco `panoptico` e usuário `panoptico` | Já instalado na máquina; Docker não está. `docker-compose.yml` fica como alternativa |
| Python | `uv` com `pyproject.toml` e `uv.lock` | Rápido e com lockfile |
| ORM / migrações | SQLAlchemy 2.x + Alembic + psycopg 3 | Padrão maduro |
| Config | `pydantic-settings` lendo `.env` | Validação tipada |
| HTTP | `httpx` | Ingestão e ViaCEP |
| Testes | `pytest` + `respx` + banco `panoptico_test` | Mock de HTTP e banco real |
| Front | Next.js (App Router, TS) + Tailwind + shadcn/ui | Ver seção 8 do PLANO_MVP |
| Lint | `ruff` e `eslint` | |

## 2026-10-06: ingestão em duas etapas

Baixar (grava JSON em `backend/data/raw/<fonte>/`) e processar (lê o JSON e faz upsert) são etapas separadas. Assim dá para reprocessar sem rede (`--de-raw`). Cada execução fica registrada em `fonte_ingestao`.

## 2026-10-06: escopo do modelo

Na Fase 2 existem só `parlamentar` e `fonte_ingestao`. `despesa` (4a) e `proposicao`/`autoria` (4b) entraram na Fase 4. `mandato` ainda não foi necessário.

## 2026-10-06: gastos do gabinete

- Recarga do ano inteiro por casa (apaga e insere numa transação), porque os arquivos oficiais mudam retroativamente.
- Ficam só as despesas de quem está na base, ou seja, dos parlamentares em exercício.
- A "média da Casa" é a média do total por parlamentar em exercício, com quem não gastou contando como zero. Quem assumiu no meio do ano puxa a média para baixo; isso é um fato do dado, não um ajuste.

## 2026-10-06: projetos de lei

- Tipos considerados: PL, PLP, PEC e PDL. Requerimentos, pareceres e emendas ficam de fora.
- Período: desde 1º/fev/2023 (legislatura atual), igual para as duas casas.
- Separamos autor principal de coautor. O número de destaque e a média da Casa usam só o autor principal, para não inflar com coautorias em massa de PECs.
- "Virou lei ou norma" = situação contém "norma jurídica". "Transformado em nova proposição" não conta.
- Carga inicial da Câmara: `python -m ingestion.camara.proposicoes --ano 2023 2024 2025 2026`. O `run_all` atualiza só o ano anterior e o atual.

## 2026-10-06: presença em votações

- Métrica comum às duas casas: "votou em X de Y votações nominais do Plenário" no ano.
- O período começa no início do ano ou no início do exercício atual, o que vier depois. Quem assumiu no meio do ano não é comparado com votações de antes.
- Quem preside a sessão conta como presente que votou ("Artigo 17" na Câmara, "Presidente" no Senado).
- O Senado informa justificativas (missão, licença, atividade parlamentar) e elas aparecem separadas. A Câmara não publica ausências, então lá aparece só "sem registro de voto", com essa ressalva no texto.
- A média da Casa é a média dos percentuais dos parlamentares em exercício.

## 2026-10-06: salário

O subsídio é igual para deputados e senadores e é fixado por decreto legislativo. Não há ingestão: `app/services/remuneracao.py` transcreve o art. 1º do DL 172/2022, com o link da norma.

## 2026-10-06: emendas por município

- "Dinheiro enviado para a cidade" é o que **prefeitura, fundos municipais e entidades sem fins lucrativos** da cidade receberam de emendas **individuais** desde o orçamento de 2023 (arquivo por favorecido). Isso cobre cerca de 61% do valor pago a favorecidos com prefeituras e fundos, e mais as entidades.
- Ficam de fora: bancos intermediários (Caixa e BB aparecem como "Sociedade de Economia Mista", cerca de R$ 20 bi), empresas (podem ser sediadas numa cidade e executar em outra) e emendas de bancada, comissão e relator (sem autor individual).
- Autor → parlamentar: o nome mais recente de cada código de autor, comparado sem acentos e sem pontuação, só com correspondência exata. Nome que bate com mais de um parlamentar fica sem vínculo. Correspondências aproximadas foram testadas e estavam todas erradas ("Camilo Santana" → "Alex Santana").
- Município do favorecido → IBGE: nome + UF exato (99,6%), depois aproximação dentro da UF (corte 0,88). Sobram cerca de 200 pagamentos sem município, contados no log.
- Autores sem vínculo (ex-parlamentares, licenciados) aparecem pelo nome em "outros autores".

## 2026-10-07: hospedagem gratuita

- Por enquanto o projeto fica em planos gratuitos: Vercel (site e API, em dois projetos), Neon (Postgres, 0,5 GB) e GitHub Actions (ingestão diária e CI). Repositório público.
- A API roda como função Python na Vercel, sem pool de conexões e sem prepared statements, usando o pooler do Neon. A ingestão e as migrações usam a conexão direta.
- Os arquivos de deploy em VPS (`deploy/`) ficam prontos para quando houver orçamento.
- `pandas` saiu das dependências: não era usado e pesava no pacote da função.

## 2026-10-07: tabelas ordenáveis em vez de ranking

- O pedido de um "ranking por trabalho" virou uma lista ordenável por **um critério factual por vez** (gastos, presença, projetos, normas, emendas, alinhamento com o Governo), cada um com a definição visível e a média da Casa.
- Não há nota composta (os pesos seriam opinião nossa), não há número de posição e a ordem padrão é alfabética. Estamos entre o 1º e o 2º turno de 2026, e essa neutralidade importa.
- "Projetos" na lista e no comparador contam só o autor principal e, na Câmara, excluem o tema oficial "Homenagens e Datas Comemorativas" (que aparece à parte).
- Os números ficam pré-calculados em `resumo_parlamentar`, recalculado ao fim de cada ingestão.

## 2026-10-07: alinhamento, maioria do partido e convergência

- **Voto efetivo:** Sim, Não, Abstenção ou Obstrução. Ausências, "presente sem voto", o voto de quem preside e votações secretas ficam fora das comparações.
- **Alinhamento com o Governo (Câmara):** votações em que o Governo orientou Sim, Não ou Obstrução e o deputado deu voto efetivo. "Liberado" e orientação em branco ficam fora. A orientação vem do arquivo oficial de orientações.
- **Orientação de partido não é usada:** os blocos vêm com nome truncado ("Bl UniPpPsd...") e não dá para ligá-los aos partidos com segurança. No lugar, "votou como a maioria do seu partido": o voto mais comum entre os **outros** deputados do mesmo partido naquele dia (pelo menos 2), com empate fora da conta.
- **Convergência entre dois parlamentares:** votações em que os dois deram voto efetivo; percentual de votos iguais, no total e por tema oficial.
- **Temas:** classificação oficial da Câmara (uma proposição pode ter vários). Não rotulamos ninguém como "a favor" ou "contra" um tema: um "Sim" pode endurecer ou suavizar uma lei.

## 2026-10-07: publicar sem deixar o site sem dados

- Publicar (deploy) nunca regenera o banco; só a ingestão escreve, uma transação por fonte. O "buraco" visto na publicação do comparador veio de o código novo entrar no ar antes das migrações e dos dados novos.
- Agora o trabalho vai para o branch `dev`, e o workflow **Publicar** roda testes, migrações e, se o banco mudou, a recarga completa, e só então avança o `main` (que a Vercel publica). Nenhum segredo novo foi necessário.
- Migrações precisam ser só aditivas, para o código antigo continuar funcionando durante a recarga.

## 2026-10-07: perfil inexistente responde 200

- Com o carregamento em partes (streaming), o status já foi enviado quando o "não encontrado" é detectado. O Next injeta `noindex` nessas páginas, então buscadores não as indexam.
- Devolver um 404 de verdade exigiria consultar a API antes de toda renderização de perfil (via `proxy`), deixando todos os perfis mais lentos. Ficou como está.

## 2026-10-07: temas e alinhamento com o Governo no Senado

- **Temas:** o Senado classifica cada processo numa hierarquia própria ("Política Social / Educação / Educação Básica"). Usamos o 2º nível, de granularidade parecida com os temas da Câmara, e o 1º quando só ele existe. "Honorífico / Homenagem" recebe o mesmo rótulo da Câmara ("Homenagens e Datas Comemorativas"), para a exclusão das homenagens valer igual nas duas casas.
- A classificação só vem no detalhe de cada processo (duas chamadas por matéria). A carga `senado_temas` é **incremental**: só busca matérias ainda sem tema. Matéria sem classificação fica marcada como "Sem classificação", que não aparece no site. A API limita a taxa (429): duas conexões em paralelo, novas tentativas com `Retry-After`, e falhas ficam para a próxima carga.
- **Orientação do Governo:** vem de `/plenario/votacao/orientacaoBancada/{data}` e é ligada à votação pelo `sequencialVotacao`. Só existe em parte das votações abertas (em 2026, 11 de 19), e votações secretas não têm. O alinhamento dos senadores usa a mesma regra da Câmara, sobre uma base menor; o site avisa isso.

## 2026-10-07: gastos zerados

- Em 2025, 21 deputados e 9 senadores em exercício aparecem sem nenhum reembolso da cota. Conferimos cada caso no arquivo bruto e, para deputados, na API da Câmara: nenhum é falha de carga.
- A maioria tem despesas só em 2026, porque em 2025 eram ministros ou estavam licenciados, ou porque assumiram o mandato depois. Os demais (por exemplo, Jorge Kajuru, Priscila Costa e Gilmar Machado) não têm nenhum reembolso registrado na fonte em nenhum dos dois anos.
- No site, zero aparece como "Nenhum reembolso", e o perfil explica as causas possíveis. Não escrevemos "economizou", porque a fonte não diz o motivo.

## 2026-10-07: bens e campanha (TSE)

- **Que candidaturas entram:** todas as candidaturas de cada parlamentar em 2018 e 2022 com o mesmo CPF, em qualquer cargo. Um senador eleito em 2018 que disputou o governo em 2022 tem a declaração de bens mais recente nessa candidatura. É ela que aparece, comparada com a anterior.
- **Campanha mostrada:** a que deu o mandato atual, ou seja, a candidatura mais recente ao cargo da Casa (deputado federal; senador ou suplente).
- **Origem do dinheiro:** "Fundo eleitoral" (FEFC) e "Fundo partidário" vêm de `DS_FONTE_RECEITA` e são dinheiro público. O resto é agrupado pela origem declarada (pessoas físicas, recursos próprios, partido, outros candidatos).
- **Doadores:** não mostramos nomes de doadores pessoas físicas. São cidadãos comuns, e o dado completo continua no arquivo oficial. Mostramos quantos foram.
- **Bens:** valor como declarado, sem correção. A página avisa que bens costumam ser declarados pelo valor de compra. Sem palavras como "enriqueceu": mostramos os dois totais e o ano.
- **2024:** o TSE passou a mascarar o CPF, então as candidaturas municipais de 2024 não se ligam aos parlamentares federais.

## 2026-10-09: condenações do TCU na linha do tempo

- **Contas julgadas irregulares e inabilitação** entram como eventos (`tcu_contas_irregulares` e `tcu_inabilitacao`), ligadas só por CPF completo.
- **Texto:** "O TCU julgou irregulares contas sob responsabilidade desta pessoa (processo TC 001.825/2015-1, Acórdão 4206/2023 – 2ª Câmara), com trânsito em julgado em 02/08/2023."
  - A data do evento é a do trânsito em julgado.
  - O link é o da deliberação no site do TCU.
  - A situação diz em que dia a pessoa estava na lista, porque o TCU acrescenta e retira nomes.
- **Na base local:** 41.914 registros de pessoas físicas; 320 ligados, de 206 pessoas que acompanhamos (319 de contas irregulares e 1 de inabilitação).
- **A carga recusa uma lista incompleta:** se o número de registros lidos não bater com o total informado pelo TCU, nada é alterado.

## 2026-10-09: sanções da CGU e eleição de 2020 como histórico

- **Sanções (CEIS, CNEP, CEAF)** entram como eventos da linha do tempo. Só pessoas físicas ligadas a pessoas que temos, e só por chave forte:
  - CPF completo (CEIS e CNEP);
  - os 6 dígitos visíveis do CPF mascarado + nome igual (CEAF).

  Sem CPF, o nome sozinho não liga. Empresas sancionadas ficam para a fase de fornecedores e sócios.
- **Texto:** categoria da sanção, órgão que aplicou, norma e artigo, e o número do registro no cadastro. Situação "vigente até", "encerrada em" ou "sem data final informada", calculada no dia da carga.
- **Problema:** em 2024 o TSE mascarou o CPF, e os ~70 mil políticos municipais vinham dessa eleição. Só ~2.300 pessoas tinham CPF, e só 7 sanções ligavam.
- **Solução: a eleição de 2020 entra só como histórico** de quem já temos. Ficam as candidaturas cujo título de eleitor já aparece em outra eleição guardada (`SO_CONHECIDOS` em `ingestion/tse/candidaturas.py`, também para 2016). Ela traz o CPF completo.
  - Na base local: 49.222 candidaturas de 2020, nenhuma pessoa nova.
  - Pessoas com CPF passaram de ~2.300 para 50.782 (71%).
  - Sanções ligadas: de 7 para 39.
  - Julgamentos de candidatura na linha do tempo: de 23 para 566.
- 2020 roda por último na carga do TSE, depois das eleições mais recentes, porque depende dos títulos delas.

## 2026-10-09: cassações e julgamentos de candidatura do TSE na linha do tempo

- **Fonte:** o arquivo `motivo_cassacao` do TSE, com número do processo e fundamentos (ver FONTES_DE_DADOS). É a primeira fonte da fase de Justiça e controle.
- **Gravado como evento**, sem tabela própria: tipo `cassacao` ou `julgamento_candidatura`, com o número do processo e os fundamentos.
- **Texto factual, na linguagem do TSE:**
  - "O TSE registra a cassação do registro ou do diploma da candidatura de 2024. Fundamento: Abuso de poder econômico.";
  - "O TSE registra julgamento sobre o registro da candidatura de 2022, com fundamento em: Ficha limpa (LC 64/90)."
  - Não escrevemos "indeferimento": em 2022 todas as linhas vêm como "fundamentos legais de julgamento", inclusive abuso de poder político, que é fundamento de cassação, e o arquivo não diz qual foi a decisão.
  - A situação diz a data do dado ("segundo o TSE em 08/10/2026").
  - A fonte não traz a data da decisão nem se ainda cabe recurso, e o texto não afirma nenhuma das duas.
- **Recorte:** só candidaturas de pessoas que já temos. Para isso, a carga de candidaturas passa a guardar **todos os eleitos**, inclusive deputados federais e senadores. Antes, os federais entravam só se estivessem em exercício, e quem foi eleito e perdeu o mandato (o caso típico de cassação) não estava no banco. São ~1.200 candidaturas a mais.
- **2020 fica de fora** até as candidaturas de 2020 serem carregadas: sem elas o arquivo não ligaria ninguém.
- **Número de processo inválido** (dígito verificador do CNJ não confere) não é publicado: o evento entra sem número.

## 2026-10-09: pessoa pública única e linha do tempo

- **Tabela `pessoa`:** a mesma pessoa em todas as fontes. Cada registro de fonte (candidatura, parlamentar federal, mandato na câmara ou assembleia) entra em `pessoa_vinculo` com a regra que o ligou. Carga: `python -m ingestion.pessoas`, que lê o banco e não baixa nada.
- **Como liga, em duas fases:**
  1. Chaves fortes formam blocos:
     - CPF igual;
     - título de eleitor igual;
     - ligação já feita pela carga do TSE.
  2. A ligação por nome (vereador ou deputado estadual da casa ↔ eleito do TSE) une blocos inteiros. Todos os registros do bloco menor recebem a regra média (`nome_casa`), porque a ligação deles à pessoa depende dela.
- **Conflito de CPF:** duas pessoas com CPFs diferentes nunca são fundidas, mesmo com título ou nome igual. A carga conta e informa essas recusas.
- **Na base local:** 73.438 registros viraram 71.370 pessoas, sem nenhuma recusa. Regras: 1.099 pela carga do TSE, 601 por CPF, 124 por título e 244 por nome (média).
- **Ids estáveis:** um registro já ligado mantém a pessoa. Quando duas pessoas passam a ser a mesma, fica a de menor id e vínculos e eventos migram. A chave de cada registro é estável entre recargas (ex.: candidatura = `ano:sq_candidato`), não o id interno, que muda quando a carga do SAPL apaga e reinsere.
- **Publicação:** a API só mostra o que veio por vínculo forte ou revisado à mão (`revisado`). O mandato na casa ligado pelo nome fica de fora até a revisão. A regra está num lugar só (`app/services/pessoas.py`, `publicavel`).
- **Linha do tempo** (`/pessoas/{id}/eventos`):
  - os eventos de eleição não são gravados; são montados na hora a partir das candidaturas ligadas (coleta mínima: 72 mil eventos duplicariam a tabela de candidaturas);
  - a tabela `evento` fica para fatos que não existem em outra tabela (sanções, processos, cassações).
- **Data da eleição:**
  - a candidatura passa a guardar a data do turno que definiu o resultado (`data_eleicao`, do `DT_ELEICAO` do TSE);
  - até a próxima carga do TSE, os cargos de turno único usam a data do 1º turno;
  - os cargos com 2º turno ficam sem data, em vez de arriscar a errada.
- **Recarga sem mudança não regrava nada.** A primeira versão reescrevia as 71 mil linhas a cada execução e chegava a 103 MB com o espaço morto; agora são 27 MB.

## 2026-10-08: coleta mínima

Juntar as bases inteiras (CNPJ, PNCP, TSE, Portal da Transparência) levaria o acervo a 90–200 GB, e a maior parte nunca seria usada. A regra passa a ser pegar aos poucos, só o necessário, no formato mais compacto. Meta: ~10–30 GB.

- **Só entra com uso.** Cada fonte declara em `ingestion/fontes.toml` a pergunta do cidadão ou a seção do site que alimenta (`uso`). Sem uso, fica `situacao = "catalogada"`: conhecida e documentada, mas o acervo não a coleta. A carga recusa fonte ativa sem uso.
- **Parte das pessoas, não das bases.** O universo são as pessoas públicas (eleitos, ministros, magistrados de tribunais superiores, nomeados de alto escalão). De bases grandes guarda-se só o que se liga a elas (`recorte`). Exemplos:
  - CNPJ: empresas com sócio político e fornecedores dos contratos, não as 60 milhões;
  - PNCP: contratos inteiros só quando o fornecedor tem ligação com político, sanção ou doação; o resto em somas.
- **Somas em vez de linhas** quando o site mostra somas (`guarda = "somas"`), como já é no SICONFI, nos gastos da ALESP e nas contas de campanha. O detalhe fica a um link da fonte oficial.
- **Bruto completo só de fontes pequenas ou instáveis** (páginas de processo, PDFs de casos, SAPL). Dos arquivos grandes que o órgão mantém no ar, guarda-se o recorte em Parquet compactado e o manifesto (URL, data, sha256); para refazer, baixa-se de novo (`bruto = "recorte"`).
- **Incremental:** pedir só o que mudou desde a última carga e não gravar de novo um arquivo igual ao anterior.
- **Janela de tempo:** mandato atual e anterior por padrão. O histórico longo fica só onde ele é a informação (processos, casos, bens).

## 2026-10-08: acervo local e regras para Justiça e controle

O plano é juntar tudo o que é público sobre quem exerce função pública: processos, sanções, contas julgadas pelo TCU, cassações, partidos, contratos e empresas. Isso passa de dezenas de GB e não cabe na produção atual.

- **Acervo local primeiro.** As fontes novas rodam numa máquina local, num banco à parte (`panoptico_acervo`, criado por `scripts/criar_acervo.sql`, com as mesmas migrações), com os brutos preservados (`PRESERVAR_RAW=true`) num diretório configurável (`RAW_DIR`, que pode ser um HD externo).
  - A produção continua como está.
  - A infraestrutura de produção será decidida com os volumes medidos por `python -m ingestion.acervo relatorio`.
- **Registro das fontes** em `backend/ingestion/fontes.toml`: módulo, frequência, anos, dependências e degrau de acesso.
  - `python -m ingestion.acervo rodar --vencidas` roda o que passou da frequência, em ordem de dependência.
  - Quem depende de uma fonte que falhou é pulado.
  - TOML porque o Python lê sem dependência nova.
- **Só registros oficiais.** Processos, investigações e sanções entram só se vierem de órgão oficial (tribunal, TCU, CGU, TSE, CNJ, casas legislativas), com número, data, situação e link. Imprensa e comunicados de operação policial não são fonte.
- **Presunção de inocência.**
  - O texto descreve o ato processual ("parte como investigado no Inquérito nº X no STF, aberto em…; situação: em andamento"), sem adjetivos.
  - Arquivamento, absolvição, anulação e prescrição têm o mesmo destaque da acusação.
  - Delação aparece como "citado em colaboração premiada homologada", nunca como prova.
- **Escândalos viram "casos"** montados só com documentos oficiais: processos, denúncias do MPF, acórdãos, relatórios de CPI, delações tornadas públicas e sanções. Cada pessoa é ligada ao caso pelo papel que um documento lhe dá. A curadoria fica em CSVs versionados (`data/casos/`), revisados por pull request.
- **Pessoas privadas não aparecem:** doadores, filiados comuns, sócios que não são políticos e partes privadas de processos. Servem só para ligação interna. Processos em segredo de justiça e envolvendo menores ficam de fora.
- **Ligação de pessoas entre fontes:** só vínculo por chave forte é publicado:
  - CPF;
  - título de eleitor;
  - CPF mascarado + nome;
  - nome + data de nascimento.

  Vínculo por nome com UF e cargo vai para revisão manual. A decisão humana fica num CSV versionado e é reaplicada a cada carga.
- **Fontes que bloqueiam o acesso automático.** Não contornamos barreira deliberada: nada de rodízio de IP, User-Agent falso, CAPTCHA ou automação de navegador para passar por proteção. A escada, em ordem:
  1. diagnosticar;
  2. rodar do Brasil quando é geobloqueio (caso de Roraima);
  3. ir mais devagar e usar cache;
  4. buscar o mesmo dado num canal oficial alternativo ou num espelho confiável, conferido por amostra;
  5. pedir acesso ao órgão;
  6. fazer pedido pela Lei de Acesso à Informação;
  7. registrar publicamente que o órgão não publica o dado.

  O degrau de cada fonte fica no registro (`acesso`).

## 2026-10-08: carga do SAPL mais rápida e sem itens perdidos

- **Paginação sempre ordenada (`o=id`).** Sem ordem, o SAPL pagina de forma instável e a mesma lista repete itens e perde outros: na Assembleia do Acre, 5 projetos recentes de 434 ficavam de fora. Votos, presença e o resto da casa saíram iguais na comparação.
- **Autoria e presença do mais novo para o mais velho (`o=-id`)**, parando na primeira página toda anterior ao período. Antes vinha o histórico inteiro de cada vereador (até 3.800 autorias em João Pessoa). Se a instalação ignorar a ordem, a lista é lida inteira, como antes.
- **Projetos em lote:** a lista de matérias filtrada por ano e tipo, em vez de uma requisição por projeto. João Pessoa sozinha segurava o job da Paraíba por 4h30, pedindo projeto a projeto a um servidor que respondia 503. O que não vier no lote é buscado sozinho.
- **Mais tentativas (5) nos erros 5xx**, para um 503 no meio de uma paginação longa não derrubar a casa (Assembleia do Amazonas). Instalação sem a rota de autores (404) entra sem projetos.
- **Roraima fora do Actions:** o SAPL da assembleia responde 403 aos endereços do GitHub e 200 a partir do Brasil. Não é falha da carga; o job só ficava verde antes porque não checava.
- Na Assembleia do Acre, a coleta caiu de 380 s para 148 s.

## 2026-10-08: cargas do SAPL mais robustas

- **Só a legislatura em vigor** (com 90 dias de folga depois do fim). Sem ela, a casa não é carregada e os dados antigos são removidos: o SAPL da Assembleia de Mato Grosso parou em 2018 e, antes da correção, a carga mostraria deputados de 2015–2018 como se estivessem no cargo.
- **Um item com erro não derruba a casa:** parlamentar ou matéria que sumiu (404) ou deu erro no servidor é pulado, com registro no log; página que some no meio da paginação encerra a lista ali; falha só nos votos ou na presença deixa a casa sem esses dados, mas com o resto. Na primeira carga com votos, 46 de 982 câmaras e 7 de 9 assembleias tinham falhado por um desses motivos ou por um texto de resultado longo demais (corrigido).
- **Job vermelho quando a assembleia não carrega**, para a falha não passar despercebida.

## 2026-10-08: Assembleia de São Paulo (ALESP)

- Conector pelos arquivos XML de dados abertos da ALESP (atualizados todo dia), nas mesmas tabelas das outras casas: os 94 deputados em exercício, projetos (PL, PLC, PR, PDL e PEC, com ementa) e moções, requerimentos e indicações (contagem), do ano atual e do anterior, e os gastos do gabinete somados por mês e categoria.
- **Sem votos e sem presença em Plenário:** não estão nos dados abertos. O site da ALESP mostra a presença num formulário e recusa acesso automatizado à página de votações; não contornamos. O perfil diz que a assembleia não publica isso em dados abertos.
- **Suplentes:** o arquivo não diz se o deputado é titular ou suplente; todos aparecem como no cargo.
- **Ligação ao eleito do TSE (vale para todas as casas):** além do nome idêntico, aceita o mesmo nome sem partículas e títulos ("Alex Madureira" e "Alex de Madureira") e um nome de ao menos duas palavras contido no outro ("Valdomiro Lopes" e "Dr Valdomiro Lopes"), sempre só quando a correspondência é única. Sobrenome solto nunca basta. Na ALESP, a ligação passou de 76 para 87 dos 94 deputados.
- Os arquivos grandes (até 164 MB) são baixados para o disco, lidos em fluxo e apagados.

## 2026-10-08: Assembleia de Minas Gerais (ALMG)

- Conector próprio pela API de dados abertos da ALMG, gravando nas mesmas tabelas das outras casas: deputados em exercício, projetos (PL, PLC, PEC e projetos de resolução, com ementa) e requerimentos e indicações (contagem), do ano atual e do anterior.
- **Gastos do gabinete (verba indenizatória):** total reembolsado por mês e categoria, guardado em `gasto_local`. O perfil mostra o ano mais recente com a média da casa (entre quem está no cargo; quem não pediu reembolso entra com zero), como nos federais.
- **Sem votos e sem presença:** a API da ALMG não traz o voto de cada deputado nem a lista de presença (as reuniões de Plenário só têm o resultado de cada matéria). O perfil diz que a assembleia não publica isso em dados abertos.
- **Autoria:** o primeiro da lista é o autor principal; os demais contam como coautores. Proposições do Governador e de tribunais não têm deputado autor.
- **Foto:** a do TSE, pela ligação ao eleito (72 dos 77 ligados; os outros 5 são, em geral, suplentes que assumiram e não constam como eleitos no TSE).
- Conferido: o reembolso de combustível do deputado Adalclever Lopes em maio de 2025 (R$ 1.978,65) e os links dos projetos (`almg.gov.br/projetos-de-lei/PL/{número}/{ano}`).

## 2026-10-08: comparação de vereadores e deputados estaduais

- **Só na mesma casa** (dois vereadores da mesma câmara, dois deputados da mesma assembleia), por decisão do projeto: só aí a pauta e as votações são as mesmas e os números se comparam. Casas diferentes respondem 422 com a explicação.
- Lado a lado: projetos, proposições (também por tipo), presença, votações nominais, votos recebidos, idade, escolaridade e ocupação.
- **Votos em comum:** só as votações nominais em que os dois registraram voto ("Não votou" fica de fora); o fato aparece como "votaram igual em X de Y", com a lista das divergências mais recentes.
- Entrada pelo perfil ("Comparar com outro vereador desta câmara"), escolhendo da lista dos colegas em exercício.

## 2026-10-08: votações e presença nas câmaras e assembleias (SAPL)

- **Só votações nominais.** Votações simbólicas não anotam o voto de cada um e não entram. Um registro de votação sem nenhum voto nominal é tratado como simbólico.
- **"Não votou" não é voto.** O SAPL lista quem estava na votação e não votou ("Não Votou"). O perfil diz "registrou voto em X das Y votações nominais em que aparece na lista", e a contagem de votos não inclui essas linhas.
- **Presença:** contam só as sessões plenárias com a lista de presença lançada no sistema (nem toda sessão tem), dentro do mandato de cada um (um suplente que assumiu em julho não é cobrado pelas sessões de março). Se a casa não lança presença no SAPL, o perfil diz isso em vez de mostrar zero.
- **Média da casa:** média do percentual de presença entre quem está em exercício e teve sessão no período.
- **Período:** ano atual e anterior, como os projetos. Só os votos de quem está no cargo hoje são guardados.
- Numa amostra de 40 câmaras com SAPL, 24 registram votos nominais. Na Assembleia do Acre, a carga conferiu com a fonte: 709 votos (o total da API), 42 votações nominais e 160 sessões com presença.

## 2026-10-08: perfis com a mesma estrutura

- Federais, estaduais, vereadores e Executivo seguem a mesma ordem: cabeçalho, números-chave, "Quem é" (dados declarados ao TSE e votos recebidos), atividade e, por fim, "Eleição" (bens e campanha). Antes, nos federais, os dados pessoais ficavam no fim da página, dentro de "Eleição", e pareciam não existir.
- **Um perfil por pessoa:** quando a câmara ou a assembleia lista a pessoa no cargo (`mandato_local` ligado à candidatura), o perfil do TSE redireciona para o perfil da casa, que tem a atividade e também mostra a eleição.
- **Sem dado da casa:** o perfil diz o motivo como fato. Se a câmara não usa SAPL, "não publica votações e projetos num formato de dados abertos que o Panóptico consiga ler", com os canais oficiais da cidade. Se usa SAPL mas o nome não está na lista dela, a pessoa pode ter deixado o cargo ou usar lá outro nome.

## 2026-10-08: licença AGPL-3.0

- O código é AGPL-3.0, e não MIT: quem publicar um site derivado precisa abrir o código também, o que protege um projeto cívico contra versões fechadas. Os dados continuam sob as regras de cada fonte oficial.

## 2026-10-08: busca por nome em todos os níveis

- A busca da página inicial (`/busca?nome=`) procura parlamentares federais em exercício, quem está no cargo hoje nas câmaras e assembleias com SAPL e os eleitos do TSE na eleição mais recente de cada cargo (presidente, governadores, deputados estaduais, prefeitos, vereadores e vices).
- **Sem repetir:** um eleito que a própria casa lista como no cargo aparece pelo dado da casa, que é o atual. Federais vêm só da Câmara e do Senado.
- **Nome de urna e nome completo:** procura nos dois, sem diferença de acento, com todas as palavras digitadas. Quando o nome completo é diferente, aparece embaixo, para ninguém estranhar um "Batista Torres" na busca por "João Silva".
- **Ordem:** Congresso, depois Executivo, assembleias, prefeituras e câmaras; até 20 resultados.
- O comparador continua buscando só parlamentares federais, porque só eles têm os números comparáveis.

## 2026-10-08: assembleias legislativas (SAPL) e portais da transparência

- **Assembleias:** levantamento das 27 casas. Nove têm SAPL (AC, AL, AM, MT, PB, PI, RO, RR e TO), mas o de Mato Grosso parou em 2018 (só a legislatura 2015–2018 cadastrada) e ficou de fora; entram oito e entram com o mesmo conector das câmaras: deputados estaduais no cargo hoje (inclusive suplentes que assumiram), partido atual, contato, projetos e proposições do ano atual e do anterior. As outras 18 publicam em sistemas próprios e ficam com a lista de eleitos do TSE até ganharem conector, uma a uma.
- **Mesma tabela:** os deputados estaduais ficam em `mandato_local` com `casa = "assembleia"` e a UF, sem município. A ligação ao eleito do TSE usa a eleição estadual mais recente, porque o mesmo nome aparece em 2018 e 2022.
- **Tipo de autor "Parlamentar" no SAPL:** é procurado pelo nome. O id 1 é o mais comum, mas na Assembleia de Roraima o 1 é "Bloco Parlamentar". Com o id fixo, a contagem de projetos vinha zerada nessas instalações (câmaras inclusive).
- **Propostas de emenda à Constituição estadual** contam como projeto.
- **Portais da transparência:** quando a página inicial não tem o link no HTML (menus montados por JavaScript), a varredura sonda `transparencia.{domínio}`, `/portal-da-transparencia`, `/transparencia` e `/portaltransparencia`. Só aceita página com "transparência" no título, porque muitos sites devolvem a página inicial para qualquer endereço. Achou 224 portais em 679 sites sem; uma amostra de 12 conferida à mão acertou todos.
- **Santa Catarina:** o servidor que hospeda a maioria dos sites municipais de SC recusa acesso automatizado (403), qualquer que seja a identificação. Não contornamos o bloqueio; as cidades de SC ficam com o que a varredura conseguiu antes e com correções curadas.

## 2026-10-08: para quem a cidade pagou (Tribunais de Contas)

- Os portais de transparência dos fornecedores (Betha, CR2, Pronim...) foram feitos para pessoas: o Betha exige reCAPTCHA nas consultas e o CR2 é um app sem API pública. Não contornamos captcha, então o detalhe das despesas vem dos **Tribunais de Contas estaduais**, que recebem os dados de todas as prefeituras e câmaras e publicam em lote.
- **Primeiro: TCE-SP** (644 municípios). Do arquivo anual (15 GB descompactado), guardamos só o **total pago por fornecedor**, por município e órgão (prefeitura, câmara, outros), e só os 25 maiores de cada órgão; o restante vira "Demais fornecedores". Pagamentos a **pessoas físicas** são somados sem nomes, e a **folha de salários** (o órgão pagando a si mesmo) vira uma linha própria, para não parecer fornecedor. Guardamos o ano atual publicado e o anterior. A capital fica de fora: é fiscalizada pelo TCM-SP. Resultado de 2024: 644 municípios, 41,5 mil linhas, 6,5 MB.
- **Folha da prefeitura:** a prefeitura pagando ao próprio "MUNICÍPIO DE X" (com o CNPJ da prefeitura) também é folha. Em Campinas, R$ 1,88 bilhão aparecia como o maior "fornecedor" antes da correção. O instituto de previdência municipal continua como fornecedor, porque é outro órgão.

## 2026-10-08: contas dos municípios (SICONFI) e câmaras (SAPL)

- **SICONFI:** da Declaração de Contas Anuais, guardamos por município e ano a receita realizada, a despesa paga e a despesa paga por função de governo (só o primeiro nível, ex.: "Saúde"). A despesa total é a soma das funções, porque o código "TotalDespesas" se repete em várias linhas do anexo. A função "Legislativa" é o custo da câmara. A API não tem consulta em lote: é uma por município, por isso a carga é mensal. Guardamos o ano atual fechado e o anterior.
- **SAPL:** um conector para todas as câmaras que usam o sistema do Interlegis (`sapl.{câmara}`).
  - **Vereadores:** os da legislatura atual, com titular ou suplente, em exercício, partido pela filiação ativa, foto e contato.
  - **Proposições:** requerimentos, indicações e moções viram só contagem por tipo, lida do próprio texto da autoria, sem baixar cada uma. Os projetos (de lei, resolução, decreto legislativo, emenda à Lei Orgânica) do ano atual e do anterior são guardados com a ementa.
  - **Ligação ao TSE:** cada vereador é ligado ao eleito do TSE por nome exato e único.
- **Na página da cidade:** onde há SAPL, a câmara mostra quem está no cargo hoje, e a lista de eleitos do TSE fica recolhida.

## 2026-10-08: canais oficiais dos municípios

- Não existe lista nacional dos sites de prefeituras, câmaras e portais da transparência. Uma **varredura inicial** (`ingestion/canais/varredura.py`, workflow manual) testa os endereços padrão (`{cidade}.{uf}.gov.br`, `{cidade}.{uf}.leg.br`, `camara{cidade}...`), aproveita os links do próprio site da prefeitura, confere se a página é daquela cidade e reconhece o sistema usado (SAPL, fornecedores de transparência).
- O resultado vira o **catálogo versionado** `data/canais_oficiais.csv`, revisado por pull request. As cargas seguintes vão direto aos endereços dele, sem varrer de novo. Qualquer pessoa pode corrigir uma cidade.
- **Educação com os servidores:** uma requisição por vez por servidor, com pausa, e identificação do Panóptico. Muitas cidades dividem o mesmo servidor, que bloqueia rajadas (visto em SC, com resposta 444). Só domínios oficiais como ponto de partida; um site oficial pode redirecionar para outro domínio `.br`.
- No teste com 40 cidades do RS: 33 prefeituras, 24 câmaras e 31 portais da transparência encontrados.
- **Primeira varredura nacional (8/10/2026):** 4.661 das 5.571 cidades com algum canal; 3.810 prefeituras, 3.738 câmaras, **982 câmaras com SAPL**, 3.510 portais da câmara e 3.458 da prefeitura.
  - Na conferência manual de 20 cidades, os sites da prefeitura e da câmara estavam certos. Dois links de transparência estavam errados: um portal de outra cidade (modelo de site do fornecedor) e uma notícia. Os dois tipos de erro viraram filtros, que tiraram 127 links do catálogo.
  - SC teve poucas prefeituras (54), porque o servidor que hospeda a maioria delas bloqueia as máquinas da varredura.
- **Capitais e correções manuais:** `data/canais_curados.csv` substitui o canal da varredura do mesmo tipo na mesma cidade. As capitais usam endereços fora do padrão (`pbh.gov.br`, `prefeitura.rio`, `cmc.pr.gov.br`...), por isso foram conferidas uma a uma. A varredura tinha achado o site do governo do estado no lugar da prefeitura de São Paulo.

## 2026-10-08: fotos dos eleitos (TSE)

- Os eleitos que só existem no TSE (vereadores, prefeitos, deputados estaduais, governadores, presidente) ganham a foto da candidatura. Ela vem dos zips de fotos do TSE por UF (`cdn.tse.jus.br/.../fotos/foto_cand{ano}_{UF}_div.zip`): a URL do DivulgaCandContas recusa acesso automático, o CDN de arquivos não.
- Os zips trazem todos os candidatos (552 MB só SC em 2024). Cada um é baixado, só as fotos dos eleitos guardados são lidas (o nome do arquivo traz o SQ), reduzidas para WebP de 240 px (cerca de 4,5 KB) e gravadas no banco, e o zip é apagado antes do próximo.
- As fotos são servidas por `/fotos/{id}.webp` com cache de um ano na CDN, porque a foto de uma eleição não muda. Parlamentares federais continuam com a foto oficial da Câmara e do Senado.
- A carga das fotos é opcional no workflow "Ingestão TSE", porque baixa cerca de 15 GB.

## 2026-10-08: dados pessoais, votos e redes (TSE)

- **Dados pessoais:** idade, escolaridade, ocupação, gênero, cor ou raça e estado civil, como o candidato declarou ao TSE na candidatura mais recente. Gênero e cor ou raça são autodeclarados, e a página diz isso. O e-mail de campanha não é exibido.
- **Título de eleitor:** guardado só para ligar candidaturas entre eleições, nunca exibido. Em 2024 o TSE mascarou o CPF, mas não o título. Com ele, a candidatura municipal de 2024 de um parlamentar federal se liga ao perfil, e um eleito aparece com "eleito depois para…" (ex.: deputado estadual de 2022 eleito prefeito em 2024).
- **Votos recebidos:** votos nominais válidos somados de todas as zonas, no último turno disputado.
- **Redes:** só endereços web informados ao TSE, sem repetição.

## 2026-10-08: Executivo (presidente, governadores, prefeitos)

- Vêm do TSE, como os vereadores: os eleitos para presidente e governador (2022) e prefeito (2024), com o vice. O vice é ligado ao titular pela chapa: mesmo ano, mesma disputa (UF e unidade) e mesmo número.
- Quem disputou o segundo turno fica com o resultado final.
- A campanha aparece no titular. Nas eleições majoritárias, as contas são prestadas pela chapa.
- Mudanças depois da eleição (renúncia, cassação, posse do vice) ainda não aparecem. A página avisa.

## 2026-10-07: votos nas comissões

- Votações nominais de comissão ficam em tabelas próprias (`votacao_comissao`, `voto_comissao`), separadas do Plenário. **Presença, alinhamento com o Governo, maioria do partido e convergência continuam contando só o Plenário**, onde todos votam a mesma pauta. Nas comissões, cada parlamentar vota só nas que integra, então um percentual ou uma média enganariam.
- **Câmara:** os mesmos arquivos anuais de votações, filtrando o que não é `PLEN`. O nome da comissão vem de `orgaos.csv`. São poucas: cerca de 140 votações nominais em 2025, porque a maioria das decisões de comissão é simbólica.
- **Senado:** endpoint `votacaoComissao/parlamentar/{codigo}`, consultado para cada senador em exercício e juntado pelo código da votação. Se mais da metade das consultas falhar, a carga aborta para não apagar o ano.
- No perfil aparecem só os fatos: em quantas votações de comissão votou, em quais comissões e a lista dos votos.

## 2026-10-07: vereadores e deputados estaduais (TSE)

- **Quem entra:** só os **eleitos** para câmaras municipais (2024) e assembleias (2022), segundo o resultado do TSE. Os suplentes ficam de fora: são dezenas por vaga, e o TSE não informa quem assumiu depois. A página avisa que um suplente pode estar no exercício.
- **Quem hoje está em outro cargo:** um eleito deputado estadual que hoje é deputado federal (ligado pelo CPF) aparece na lista com "Hoje é deputado federal" e o link para o perfil federal.
- **Município:** o TSE usa um código próprio de município. A ligação ao IBGE é por nome + UF, como nas emendas, mais uma pequena tabela de nomes que mudaram (Boa Saúde/RN virou Januário Cicco; São Luiz/RR é São Luiz do Anauá). Em 2024, todos os 5.545 municípios com vereadores eleitos casaram.
- **Sem fotos:** o TSE não libera as fotos para uso automático, então os cartões mostram as iniciais.
- **Atividade (gastos, votos):** fica para a etapa seguinte, câmara por câmara, porque cada uma publica de um jeito.

## 2026-10-07: emendas por área e por quem recebeu

- **Área:** é a função orçamentária da emenda. O arquivo de pagamentos não traz a área, então ela vem do cadastro da emenda, pelo código.
  - Um mesmo código pode ter linhas com áreas diferentes (53 casos), uma por localidade. Nesse caso vale a área da linha do próprio município.
  - Sem essa linha, vale a área única do código. Se ainda houver mais de uma, o valor fica em "Mais de uma área", em vez de ser atribuído por palpite.
- **"Encargos especiais"** inclui as transferências especiais ("emendas Pix"), que chegam ao caixa da prefeitura sem área definida. A página diz isso.
- **"Quem recebeu"** lista prefeitura, fundos e entidades pelo CNPJ, com quem enviou. Não colocamos link para o Portal da Transparência, porque a página do favorecido recusa acesso automatizado e não conseguimos garantir que o link funcione.

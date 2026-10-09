# Panóptico

**Quem te representa, às claras.**

Digite o seu CEP e veja quem representa você no Congresso Nacional: quanto cada deputado federal e senador gasta, quanto participa das votações, quais projetos apresenta e quanto dinheiro de emendas mandou para a sua cidade. Tudo com dados oficiais e link para a fonte.

🌐 [panoptico.social.br](https://panoptico.social.br) · 📚 [Sobre as fontes](https://panoptico.social.br/sobre-as-fontes) · 🔌 [API](https://api.panoptico.social.br/docs)

---

## Por que existe

O panóptico é uma prisão imaginada no século XVIII em que um vigia, de uma torre central, observa todos os presos sem ser visto. O projeto inverte essa lógica: **em vez de o poder observar o cidadão, o cidadão passa a enxergar o poder público.**

Os dados sobre o trabalho dos parlamentares já são públicos, mas estão espalhados em portais diferentes, em formatos técnicos e com nomes como "CEAP", "proposição" ou "emenda individual de transferência especial". O Panóptico junta essas informações num lugar só e as apresenta em linguagem do dia a dia, pensado para quem abre um link no celular, vindo de um grupo de WhatsApp, e quer entender em menos de um minuto quem é seu representante e o que ele tem feito.

## O que dá para ver

- **Seus representantes pelo CEP** (ou escolhendo estado e cidade):
  - o **presidente, o governador e o prefeito** eleitos, cada um com o vice;
  - os 3 senadores e os deputados federais do estado;
  - os **deputados estaduais** eleitos;
  - os **vereadores** eleitos da cidade.
- **Perfil de cada parlamentar federal**, com os números principais no topo e os detalhes abaixo:
  - **Gastos do gabinete** (cota parlamentar): total do ano, média da Casa, gastos por categoria e os maiores gastos. Quando não há nenhum reembolso, o site diz isso e explica as causas possíveis.
  - **Presença em votações**: em quantas votações nominais do Plenário votou, desde o início do mandato atual.
  - **Como votou**: cada votação do Plenário, por tema oficial, com a orientação do Governo e a maioria do partido ao lado.
  - **Votos nas comissões**: as votações nominais de comissão de que participou.
  - **Projetos de lei** desde 2023: autor principal e coautor, os que viraram lei e os temas.
  - **Eleição** (TSE): votos recebidos, idade, escolaridade, ocupação e redes declaradas, bens declarados na eleição mais recente comparados com a anterior, e de onde veio e para onde foi o dinheiro da campanha que deu o mandato.
  - **Salário**: o subsídio, igual para todos, com a norma que o fixa.
- **Perfil de vereadores, deputados estaduais, prefeitos, governadores e presidente**, com a foto da candidatura e dados do TSE (votos recebidos, dados pessoais declarados, redes sociais, bens e contas de campanha), e quando a pessoa foi eleita depois para outro cargo.
- **Todos os perfis têm a mesma ordem**: cabeçalho, números-chave, "Quem é" (dados declarados ao TSE e votos recebidos), atividade no cargo e, por fim, a eleição (bens e campanha). Quando a câmara ou a assembleia publica a pessoa no cargo, o perfil do TSE leva ao perfil da casa, com a atividade; quando a câmara não publica dados abertos, o perfil diz isso e mostra os canais oficiais da cidade.
- **Busca por nome** em todos os níveis, na página inicial: parlamentares federais, presidente, governadores, prefeitos, deputados estaduais e vereadores (sem diferença de acento; também pelo nome completo).
- **Comparador**: dois parlamentares lado a lado, com números, votos em comum por tema e projetos assinados juntos.
- **Comparador na mesma casa** (`/comparar/local`): dois vereadores da mesma câmara, ou dois deputados da mesma assembleia, com projetos, proposições, presença, votos em comum e dados declarados ao TSE.
- **Lista de todos os parlamentares federais**, ordenável por um critério factual de cada vez (gastos, presença, projetos, emendas, alinhamento com o Governo). Não há nota nem ranking.
- **Dinheiro enviado para a sua cidade**: emendas individuais pagas à prefeitura, aos fundos municipais e a entidades, com:
  - quem enviou;
  - para quais áreas (saúde, educação…);
  - quem recebeu, com o CNPJ.
- **Contas da sua cidade** (SICONFI, Tesouro Nacional): quanto a prefeitura arrecadou e gastou no ano, em que áreas e quanto custou a câmara municipal.
- **Para quem a cidade pagou** (por enquanto, cidades de SP, pelo TCE-SP): os maiores fornecedores da prefeitura e da câmara no ano.
- **Câmara municipal hoje** (nas câmaras que usam o SAPL): quem está no cargo agora, inclusive suplentes, com partido atual, contato, projetos, quantos requerimentos, indicações e moções apresentou, presença nas sessões (com a média da câmara) e como votou nas votações nominais, onde a câmara registra.
- **Assembleia legislativa hoje** (nas que usam o SAPL: AC, AL, AM, PB, PI, RO e TO; a de RR bloqueia o acesso a partir do GitHub Actions): o mesmo para os deputados estaduais, com perfil em `/deputado-estadual/{id}`.
- **Assembleia de São Paulo** (dados abertos da ALESP): deputados no cargo, projetos, moções, requerimentos e indicações, e **gastos do gabinete**, com a média da assembleia. Votos e presença em Plenário não estão nos dados abertos.
- **Assembleia de Minas Gerais** (dados abertos da ALMG): deputados no cargo, projetos, requerimentos e **gastos do gabinete** (verba indenizatória), com a média da assembleia. A ALMG não publica o voto de cada deputado nem a presença.
- **Canais oficiais da sua cidade**: sites da prefeitura e da câmara e os portais da transparência, num catálogo aberto (`data/canais_oficiais.csv`, gerado pela varredura, e `data/canais_curados.csv`, com as correções feitas à mão) que qualquer pessoa pode corrigir por pull request.
- **Compartilhamento**: perfis e comparações têm imagem de pré-visualização e botão de WhatsApp.

## Princípios

1. **Toda informação tem fonte e data de atualização.** Cada seção do site leva ao dado original.
2. **Linguagem estritamente factual.** Sem notas, rankings, selos ou adjetivos. Mostramos o número e, ao lado, a média da Casa para comparação.
3. **Dado bruto separado do tratado.** O arquivo baixado da fonte é guardado como veio, e o processamento pode ser refeito a partir dele.
4. **Privacidade por padrão.** Não há cadastro, login nem cookies de rastreamento. O CEP é usado só para descobrir a cidade e não é gravado.
5. **Processos e investigações só com fonte oficial**, número do processo, data e status atual. Ainda não estão no site e só entrarão com curadoria cuidadosa.

## Projeto aberto

O Panóptico é **público e aberto a contribuições**. O código está todo neste repositório, os dados vêm de fontes públicas e a metodologia de cada número está documentada em [docs/DECISOES.md](docs/DECISOES.md) e na página [Sobre as fontes](https://panoptico.social.br/sobre-as-fontes).

Você pode ajudar de várias formas, mesmo sem programar:

- **Achou um número diferente da fonte oficial?** Abra uma [issue](https://github.com/Gipsy7/panoptico/issues) com o link do perfil e da fonte.
- **Algo confuso no site?** Sugestões de texto e de usabilidade são muito bem-vindas, principalmente vindas de quem não acompanha política.
- **Conhece uma fonte de dados boa?** Conte para a gente numa issue.
- **Programa?** Veja [Como contribuir](#como-contribuir).
- **Quer ajudar com os custos?** O site é gratuito e sem anúncios; a página [Apoie](https://panoptico.social.br/apoie) mostra quanto custa mantê-lo no ar e aceita doações por Pix. Doações não mudam nada no que o site mostra, e não aceitamos doações de partidos, mandatos ou campanhas.

<p align="center">
  <img src="frontend/public/pix-qr.svg" alt="QR code Pix para apoiar o Panóptico" width="180"><br>
  <sub>Pix (chave aleatória): <code>4c02a34c-095e-4990-9bdb-0fe161608f8c</code></sub>
</p>

---

## Como funciona

```mermaid
flowchart LR
    subgraph fontes [Fontes oficiais]
        CD[Câmara dos Deputados]
        SF[Senado Federal]
        CGU[Portal da Transparência]
        IBGE[IBGE]
    end
    CD & SF & CGU & IBGE -->|todo dia, 6h| ING[Ingestão<br/>Python · GitHub Actions]
    ING -->|bruto| RAW[(Arquivos brutos)]
    ING -->|tratado| DB[(PostgreSQL)]
    DB --> API[API<br/>FastAPI]
    API --> WEB[Site<br/>Next.js]
    VIACEP[ViaCEP] -.->|CEP → cidade, na hora| API
    WEB --> U((Você))
```

1. **Ingestão** ([backend/ingestion/](backend/ingestion/)): todo dia, um workflow do GitHub Actions baixa os dados de cada fonte. Cada execução:
   - grava o arquivo bruto como veio (`data/raw/<fonte>/`);
   - normaliza os dados e carrega no banco numa transação;
   - registra a execução em `fonte_ingestao` (de onde veio, quando, quantos registros, se deu certo).

   Uma falha numa fonte não impede as outras. Qualquer carga pode ser refeita a partir do bruto com `--de-raw`, sem rede.
2. **Banco** (PostgreSQL): parlamentares, despesas, votações e votos (Plenário e comissões), proposições, autorias e temas, emendas e pagamentos, municípios, e as candidaturas, os bens e as contas de campanha do TSE. As migrações ficam em [backend/alembic/](backend/alembic/).
3. **API** ([backend/app/](backend/app/)): FastAPI, só leitura, com respostas que já trazem a fonte e a data de cada dado. Documentação interativa em `/docs`.
4. **Site** ([frontend/](frontend/)): Next.js com renderização no servidor e carregamento em partes, para abrir rápido em conexão fraca. Pensado primeiro para o celular.

### Fontes de dados

| Dado | Fonte | Como é obtido |
|---|---|---|
| Deputados federais em exercício | [Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/) | API REST |
| Senadores em exercício | [Dados Abertos do Senado](https://legis.senado.leg.br/dadosabertos/) | API REST |
| Gastos do gabinete (CEAP / CEAPS) | Câmara e Senado | Arquivo anual (CSV) e API |
| Votações nominais (Plenário e comissões) e orientação do Governo | Câmara e Senado | Arquivos anuais e API |
| Projetos de lei e autores | Câmara e Senado | Arquivos anuais e API |
| Emendas parlamentares e quem recebeu | [Portal da Transparência (CGU)](https://portaldatransparencia.gov.br/emendas) | Arquivo em lote |
| Candidaturas (inclusive presidente, governadores e prefeitos), bens declarados e contas de campanha (2018, 2022 e 2024) | [Dados abertos do TSE](https://dadosabertos.tse.jus.br/) | Arquivos em lote, carga manual por eleição |
| Sites oficiais dos municípios | Varredura dos domínios `.gov.br` e `.leg.br` de cada cidade | Catálogo versionado, revisado por PR |
| Contas anuais dos municípios | [SICONFI (Tesouro Nacional)](https://siconfi.tesouro.gov.br/) | API, uma consulta por município, mensal |
| Pagamentos das prefeituras e câmaras por fornecedor (SP) | [TCE-SP](https://transparencia.tce.sp.gov.br/conjunto-de-dados) | Arquivo anual em lote, mensal |
| Vereadores e deputados estaduais no cargo, projetos, votações nominais e presença | SAPL (Interlegis) de cada câmara e de sete assembleias | API, semanal, endereços do catálogo de canais |
| Deputados estaduais de SP: projetos e gastos do gabinete | [Dados abertos da ALESP](https://www.al.sp.gov.br/dados-abertos/) | Arquivos XML, semanal |
| Deputados estaduais de MG: projetos e gastos do gabinete | [Dados abertos da ALMG](https://dadosabertos.almg.gov.br/) | API, semanal |
| Municípios | [IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) | API REST |
| CEP → cidade e estado | [ViaCEP](https://viacep.com.br/) | Consulta na hora, sem gravar |
| Salário (subsídio) | [Decreto Legislativo nº 172/2022](https://www2.camara.leg.br/legin/fed/decleg/2022/decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html) | Transcrito no código |

Endereços, formatos e armadilhas de cada fonte estão em [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md). Um exemplo de armadilha: o JSON de gastos da Câmara usa um id de deputado diferente do resto da API, e só o CSV traz o id certo.

### Como os números são calculados

O resumo está abaixo; o detalhe e o porquê de cada escolha estão em [docs/DECISOES.md](docs/DECISOES.md).

- **Média da Casa**: média entre os parlamentares em exercício. Quem não gastou ou não apresentou nada entra com zero.
- **Presença**: o período começa no início do ano ou do mandato atual, o que vier depois, para não comparar um suplente com votações de antes da posse. Quem preside a sessão conta como presente.
- **Projetos**: PL, PLP, PEC e PDL desde fevereiro de 2023. O número principal conta só os projetos em que o parlamentar é o autor principal, porque PECs costumam ter dezenas de coautores.
- **Emendas na cidade**: valores pagos a favorecidos da própria cidade (prefeitura, fundos municipais e entidades sem fins lucrativos). Bancos intermediários e empresas ficam de fora, porque ficam sediados numa cidade e executam em outra. A área é a função orçamentária da emenda.
- **Votos**: presença, alinhamento com o Governo e com a maioria do partido contam só o Plenário. As comissões aparecem como lista, sem percentual, porque cada parlamentar vota só nas comissões de que faz parte.
- **TSE**: bens pelo valor declarado, sem correção. Os parlamentares federais são ligados às candidaturas pelo CPF e pelo título de eleitor (em 2024 o TSE mascarou o CPF), que nunca são exibidos. Vereadores e deputados estaduais são os eleitos segundo o TSE; suplentes que assumiram depois não aparecem. Nomes de doadores pessoas físicas não são mostrados.

### Stack

| Camada | Tecnologia |
|---|---|
| Ingestão | Python 3.12, httpx, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL (Neon em produção) |
| API | FastAPI, Pydantic |
| Site | Next.js 16 (App Router, Cache Components), React 19, Tailwind CSS 4, shadcn/ui |
| Testes e qualidade | pytest, respx, ruff, ESLint, TypeScript |
| Infra | Vercel (site e API), Neon (banco), GitHub Actions (ingestão e CI) |

### Estrutura

```
panoptico/
├── backend/
│   ├── app/              # API: rotas (api/), modelos (models/), schemas e regras (services/)
│   ├── ingestion/        # baixar e processar cada fonte: camara/, senado/, transparencia/, ibge/
│   ├── alembic/          # migrações do banco
│   ├── data/raw/         # arquivos brutos (fora do git)
│   └── tests/
├── frontend/
│   ├── app/              # páginas: início, representantes, parlamentar, fontes, privacidade
│   ├── components/       # seções do perfil, cards, formulário de CEP
│   └── lib/              # cliente da API e formatação
├── deploy/               # deploy alternativo numa VPS (docker compose + Caddy)
├── docs/                 # plano, fontes, decisões e guias de deploy
└── .github/workflows/    # CI e ingestão diária
```

---

## Rodando localmente

**Requisitos:** Python 3.12 com [uv](https://docs.astral.sh/uv/), Node 20 ou superior e PostgreSQL 16 ou superior (nativo, ou `docker compose up -d` na raiz).

```bash
# 1. Banco
psql -U postgres -f scripts/criar_banco.sql

# 2. API
cd backend
cp ../.env.example .env              # ajuste se necessário
uv sync
uv run alembic upgrade head
uv run python -m ingestion.run_all   # baixa todas as fontes (alguns minutos)
uv run python -m ingestion.camara.proposicoes --ano 2023 2024 2025 2026   # projetos desde 2023
uv run uvicorn app.main:app --reload # http://localhost:8000/docs

# 3. Site
cd ../frontend
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm install
npm run dev                          # http://localhost:3000
```

### Ingestão

| Comando | O que faz |
|---|---|
| `uv run python -m ingestion.run_all` | Atualiza tudo (ano anterior e atual) e apaga brutos antigos |
| `uv run python -m ingestion.camara.despesas --ano 2025` | Uma fonte e um ano específicos |
| `uv run python -m ingestion.camara.deputados --de-raw data/raw/camara_deputados/<arquivo>.json` | Reprocessa um bruto sem rede |

### Acervo local

As fontes novas (Justiça, órgãos de controle, partidos, contratos) são juntadas primeiro num **acervo local**: um banco à parte, sem os limites da produção, com os brutos preservados. O registro das fontes fica em [backend/ingestion/fontes.toml](backend/ingestion/fontes.toml).

A regra é a **coleta mínima**: uma fonte só é coletada quando declara para que serve no site (as outras ficam só catalogadas), e das bases grandes guarda-se só o que se liga às pessoas públicas, em somas quando o site mostra somas. Ver [docs/DECISOES.md](docs/DECISOES.md), "coleta mínima".

```bash
psql -U postgres -f scripts/criar_acervo.sql         # uma vez
cd backend
export DATABASE_URL=postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_acervo
export PRESERVAR_RAW=true RAW_DIR=/e/panoptico/raw     # RAW_DIR é opcional (padrão: data/raw)
uv run alembic upgrade head
uv run python -m ingestion.acervo rodar --vencidas     # o que passou da frequência
uv run python -m ingestion.acervo rodar --fonte tse_bens sapl_assembleias
uv run python -m ingestion.acervo relatorio            # volume por fonte e últimas cargas
```

### API

| Rota | Retorna |
|---|---|
| `GET /representantes?cep=` · `?uf=` · `?municipio=` | Localização, deputados e senadores |
| `GET /parlamentares/{id}` | Perfil, contato e salário |
| `GET /parlamentares/{id}/gastos?ano=` | Gastos do gabinete e média da Casa |
| `GET /parlamentares/{id}/presenca?ano=` | Participação em votações nominais |
| `GET /parlamentares/{id}/projetos` | Projetos de lei desde 2023 |
| `GET /municipios?uf=` | Municípios de um estado |
| `GET /municipios/{ibge}/emendas` | Emendas recebidas pela cidade e quem enviou |
| `GET /pessoas/{id}` | A mesma pessoa em todas as fontes e os perfis dela no site (acervo) |
| `GET /pessoas/{id}/eventos?tipo=&de=&ate=` | Linha do tempo da pessoa, com a fonte de cada fato (acervo) |
| `GET /casos` · `GET /casos/{slug}` | Casos montados com documentos oficiais e o papel de cada pessoa (acervo) |
| `GET /fontes` | Fontes e data da última atualização |
| `GET /saude` | Situação da API e do banco |

### Testes

```bash
cd backend && uv run pytest && uv run ruff check && uv run ruff format --check
cd frontend && npm run lint && npm run build
```

Os testes do backend usam um banco `panoptico_test` (criado pelo `scripts/criar_banco.sql`) e simulam as APIs externas com `respx`, a partir de amostras reais em `backend/tests/fixtures/`. O CI roda tudo a cada push.

## Deploy

- **Hoje:** Vercel no plano gratuito (site e API), Neon no plano Launch, pago por uso (banco), e GitHub Actions (atualização diária). Ver [docs/DEPLOY_GRATUITO.md](docs/DEPLOY_GRATUITO.md).
- **Travas de custo.** O plano gratuito do Neon foi trocado pelo pago depois que a cota mensal de transferência estourou. Para o custo não disparar com muito acesso ou um ataque:
  - as respostas da API ficam em cache na CDN (`s-maxage` de 1 hora), então a mesma consulta chega ao banco no máximo uma vez por hora;
  - a base da lista de parlamentares fica 10 minutos em memória;
  - o firewall da Vercel limita a API a 120 requisições por minuto por IP;
  - o banco está travado em 0,25 CU e desliga quando fica ocioso, o que põe um teto de cerca de US$ 19 por mês no processamento;
  - há um spending limit com alerta por e-mail.

  O custo esperado é de R$ 5 a 20 por mês, detalhado na página [Apoie](https://panoptico.social.br/apoie).
- **Alternativa:** VPS única com docker compose e HTTPS automático. Ver [docs/DEPLOY.md](docs/DEPLOY.md).

---

## Como contribuir

1. Abra uma [issue](https://github.com/Gipsy7/panoptico/issues) descrevendo o problema ou a ideia antes de começar algo grande.
2. Faça um fork, crie um branch a partir de `dev` e envie um pull request para o `dev`. O `main` é só o que está no ar: ele é atualizado pelo workflow "Publicar" depois que os testes, as migrações e os dados estão prontos.
3. Antes de enviar, rode os testes e os linters (veja [Testes](#testes)). O CI precisa passar.

**Combinados do projeto:**

- **Fonte sempre.** Dado novo só entra com fonte oficial, link e data de atualização visíveis no site.
- **Sem juízo de valor.** Nada de notas, rankings, cores de "bom" e "ruim" ou adjetivos. Na dúvida, mostre o número e a média.
- **Linguagem do dia a dia** no site ("gastos do gabinete", não "CEAP"); o termo oficial aparece em letra menor, junto à fonte.
- **Bruto e tratado separados.** Uma nova fonte deve gravar o bruto e poder ser reprocessada com `--de-raw`.
- **Decisões de metodologia** (o que entra numa média, o que fica de fora) vão para [docs/DECISOES.md](docs/DECISOES.md) com o motivo.
- **Testes** para regras de normalização e cálculo, com amostras reais da fonte.
- O código, os comentários e os textos são em português.

### Próximos passos

O plano completo, com a ordem das fases, está em [docs/DECISOES.md](docs/DECISOES.md) ("acervo local e regras para Justiça e controle"). Em resumo:

- Acervo local com identidade única de pessoa pública e linha do tempo de eventos
- Justiça e controle, só com registros oficiais: cassações e indeferimentos no TSE, sanções da CGU, contas julgadas pelo TCU, processos no STF e no STJ (status pelo DataJud do CNJ), conselhos de ética e CPIs, e casos de corrupção montados só com documentos oficiais
- Partidos (diretórios, contas, fundos) e as eleições de 2016, 2020 e 2026
- Contratos públicos (PNCP), convênios, empresas e sócios (CNPJ)
- As 66 câmaras cujo SAPL parou e as 910 cidades sem canal oficial encontrado
- Conectores próprios para as 16 assembleias sem SAPL que faltam, depois de um levantamento casa a casa do que cada uma publica
- Votos e presença nas comissões da ALESP (já publicados em dados abertos)
- Despesas por fornecedor de outros Tribunais de Contas (RS e MG têm dados abertos)
- Teste com pessoas reais e auditoria de acessibilidade

## Licença

O código é livre, sob a [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). Qualquer pessoa pode usar, estudar, modificar e redistribuir. Quem publicar um site com uma versão modificada precisa oferecer o código-fonte dessa versão aos usuários, sob a mesma licença. Assim, as melhorias de um projeto de transparência continuam abertas para todos.

Os dados exibidos vêm de fontes públicas oficiais e seguem as regras de cada fonte (ver [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md)).

<h1 align="center">Panóptico</h1>

<p align="center">
  <b>Quem te representa, às claras.</b><br>
  Digite o seu CEP e veja quem representa você, do presidente ao vereador:<br>
  o que cada um faz, gasta, vota e recebe, com dado oficial, link da fonte e data.
</p>

<p align="center">
  <a href="https://panoptico.social.br"><b>🌐 Abrir o site</b></a> ·
  <a href="https://panoptico.social.br/sobre-as-fontes">📚 Sobre as fontes</a> ·
  <a href="https://api.panoptico.social.br/docs">🔌 API</a> ·
  <a href="https://panoptico.social.br/apoie">💛 Apoie</a>
</p>

<p align="center">
  <a href="https://github.com/Gipsy7/panoptico/actions/workflows/publicar.yml"><img alt="Publicar" src="https://github.com/Gipsy7/panoptico/actions/workflows/publicar.yml/badge.svg"></a>
  <a href="https://github.com/Gipsy7/panoptico/actions/workflows/ingestao.yml"><img alt="Ingestão diária" src="https://github.com/Gipsy7/panoptico/actions/workflows/ingestao.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença AGPL-3.0" src="https://img.shields.io/badge/c%C3%B3digo-AGPL--3.0-informational"></a>
  <a href="LICENCA-DADOS.md"><img alt="Dados CC BY 4.0" src="https://img.shields.io/badge/dados-CC%20BY%204.0-informational"></a>
</p>

---

**Pule para:** [Por que existe](#-por-que-existe) · [O que dá para ver](#-o-que-dá-para-ver) · [Princípios](#-princípios) · [Como ajudar](#-como-ajudar) · [Como funciona](#-como-funciona) · [Rodar localmente](#-rodar-localmente) · [Próximos passos](#-próximos-passos)

---

## 👁 Por que existe

O panóptico é uma prisão imaginada no século XVIII: um vigia, numa torre central, observa todos sem ser visto. **Aqui a lógica se inverte: o cidadão é quem enxerga o poder público.**

Os dados já são públicos, mas estão espalhados em dezenas de portais e escondidos atrás de siglas como "CEAP" ou "emenda de transferência especial". O Panóptico junta tudo num lugar só, em linguagem do dia a dia.

> 🎯 **Meta:** quem abre um link no celular, vindo do WhatsApp, acha o seu representante e entende o número **em menos de um minuto**.

## 🔎 O que dá para ver

```mermaid
flowchart LR
    CEP["📮 Seu CEP"] --> R["👥 Seus representantes<br/>presidente → vereador"]
    R --> P["👤 Perfil<br/>gastos · votos · projetos · eleição"]
    R --> C["🏙 Sua cidade<br/>emendas · contas · fornecedores"]
    P --> V["🗳 Cada votação<br/>placar e voto de cada um"]
    PJ["📜 Projetos e votações<br/>busca · quem votou · o que disseram"] --> V
    P --> CMP["⚖️ Comparar<br/>2 a 4 lado a lado"]
```

| | O quê | Exemplo do que aparece |
|---|---|---|
| 👥 | **Seus representantes pela localização, CEP ou cidade** | A localização é usada só no celular para achar a cidade (não é enviada). Presidente, governador e prefeito (com vices), senadores, deputados federais e estaduais, vereadores. Eleitos de 2026 que ainda não tomaram posse aparecem à parte. A página abre com um desenho dos prédios do poder, de Brasília até a cidade ("De Brasília até a sua rua"): tocar num prédio mostra quem trabalha lá, o que faz e leva à lista completa; uma mãozinha animada indica onde tocar (também no mapa e no botão de localização da home). Ao achar a cidade, a home mostra um número sorteado dela (com a média do estado) e um exemplo de comparação com parlamentares do estado; sem localização, a dupla do exemplo é sorteada. |
| 💸 | **Gastos do gabinete** | Total do ano, por categoria, maiores gastos, sempre com a média da Casa ao lado. |
| 🗳 | **Votos e presença** | "Votou em 31 de 59 votações", como votou em cada uma, orientação do Governo e do partido, votos por tema e nas comissões. |
| 📝 | **Projetos de lei** | Desde 2023: autor principal ou coautor, temas e os que viraram lei. |
| 📜 | **Projetos e votações** | Busca pelo número ("PL 2338/2023") ou por palavra, com ou sem acento, no Congresso, nas assembleias e nas câmaras. Em cada projeto: do que se trata, todas as votações nominais, quem votou Sim e quem votou Não (com filtro do seu estado e placar por estado), o que disseram os parlamentares no dia da votação (resumo oficial e link, agrupado pelo voto de quem falou), o caminho do projeto e a pauta da semana. A lista começa pelos projetos com mais informação publicada (votação nominal, discursos, caminho), e a cidade sem dados diz por quê. |
| 🧾 | **Eleição (TSE)** | Votos, bens declarados (comparados com a eleição anterior), de onde veio e para onde foi o dinheiro da campanha, todas as eleições que disputou desde 1994 (o TSE não publica o cadastro de candidaturas mais antigo). |
| 🕰 | **Linha do tempo** | Cassações, sanções da CGU, contas reprovadas no TCU, Conselho de Ética, cargos no governo federal, viagens, cartão corporativo, CPIs. Só com vínculo seguro e link oficial. |
| 🏙 | **Sua cidade** | Emendas recebidas e quem mandou, contas da prefeitura e da câmara, maiores fornecedores, contratos no PNCP, canais oficiais. |
| 🗺 | **Impostos e repasses** | Quanto a União arrecadou e repassou a cada estado e cidade (2019 a 2026), por habitante, em mapa. |
| ⚖️ | **Comparadores** | Até 4 parlamentares lado a lado, vereadores da mesma câmara, e os candidatos do 2º turno com os mesmos campos. |
| 🏛 | **Partidos** | Fundo Partidário, fundo eleitoral, receitas, gastos e repasses (TSE). |
| 🔍 | **Busca por nome** | Todos os níveis e partidos, sem diferença de acento. |
| 💡 | **A ideia e as dúvidas** | [O que é o Panóptico](https://panoptico.social.br/o-panoptico) (história ao rolar: de Bentham e Foucault à inversão que dá nome ao projeto), [Perguntas frequentes](https://panoptico.social.br/perguntas) e [Apoiadores](https://panoptico.social.br/apoiadores) (um raio do sol da marca por pessoa; só quem autorizou o nome, lista em `frontend/lib/apoiadores.ts`). Ficam no rodapé; "Fontes" saiu do menu do topo. |

E mais: **modo escuro** (segue o aparelho; um ícone troca), **filtros** com o mesmo padrão em todo o site (painel no celular, filtros ativos removíveis, link compartilhável), **cartões de prévia** com botão de WhatsApp e telas em três camadas (número → pergunta que explica → detalhe completo).

<details>
<summary><b>🏛 Cobertura de assembleias estaduais</b> (clique para abrir)</summary>

<br>

| Casa | Deputados | Projetos | Presença | Votos | Gastos |
|---|:-:|:-:|:-:|:-:|:-:|
| SAPL: AC, AL, AM, PB, PI, RO, TO | ✅ | ✅ | ✅ | ✅ ¹ | — |
| SP (ALESP) | ✅ | ✅ | — | comissões | ✅ |
| RS (ALRS) | ✅ | ✅ | ✅ | ✅ | ✅ |
| MG (ALMG) | ✅ | ✅ | — | — | ✅ |
| SC (ALESC) | ✅ | ✅ | ✅ | — | ✅ |
| PR (ALEP) | ✅ | — ² | ✅ | ✅ | — ² |
| DF (CLDF) | ✅ | ✅ | — | — | ✅ |
| BA, ES | ✅ | ✅ | ✅ | — | — |
| PE, CE, MA, RN, AP | ✅ | ✅ | — | — | — |
| MS, GO | ✅ | — ³ | — | — | ✅ |
| SE | ✅ | — ³ | ✅ | — | — |
| RJ, PA, MT | ✅ | — | — | — | — |
| RR | bloqueia acesso do GitHub Actions | | | | |

¹ onde a Casa registra votação nominal. ² API com certificado autoassinado e 403, verba atrás de reCAPTCHA; pedido em [docs/pedidos/](docs/pedidos/). ³ sistema bloqueia automação; não contornamos.

Emendas estaduais: SC (SC Transferências), por enquanto só na API. O que falta em cada Casa está em [data/pendencias_cobertura.csv](data/pendencias_cobertura.csv).

</details>

<details>
<summary><b>🏘 Cobertura de câmaras municipais</b></summary>

<br>

- **Câmaras com SAPL** (Interlegis): vereadores no cargo, suplentes, projetos, requerimentos, presença e votos nominais.
- **Câmaras que saíram do SAPL** (39 de 66 já com conector): portais Cittatec, CR2, Nucleogov/7Focus, Portal Modelo, AOS Software, modelo PHP e sites próprios. Mostram os vereadores no cargo; a Cittatec também conta proposições.
- Qual sistema cada câmara usa hoje: [data/sistemas_camaras.csv](data/sistemas_camaras.csv). Por que as outras 27 ainda não têm: [data/pendencias_cobertura.csv](data/pendencias_cobertura.csv).
- Pagamentos a fornecedores: SP (TCE-SP) no site; RS (TCE-RS) só no acervo local, porque o tribunal não responde fora do Brasil; MG aguarda pedido (reCAPTCHA).

</details>

> ♿ **Acessível:** meta WCAG 2.2 nível AA e eMAG 3.1; uso só pelo teclado (com atalhos Alt+1, 2 e 3), leitor de tela, letra até 200% e telas a partir de 320 px; testes automáticos todos os dias. Detalhes e limitações em [/acessibilidade](https://panoptico.social.br/acessibilidade).

## 📏 Princípios

| | |
|---|---|
| 🔗 **Fonte e data em tudo** | Cada seção leva ao dado original e diz quando foi atualizada. |
| 🧊 **Sem juízo de valor** | Nada de nota, ranking, selo ou adjetivo. O número e a média da Casa ao lado. |
| 🗣 **Linguagem do dia a dia** | "Gastos do gabinete", não "CEAP". O termo oficial vem em letra menor. |
| 🔒 **Privacidade** | Sem cadastro, login ou cookie de rastreamento. O CEP não é gravado. Nada de CPF, título ou data de nascimento. |
| 🚧 **Bloqueio não se contorna** | Captcha, 403 ou `robots.txt` que veda vira pedido de acesso ou LAI ([docs/pedidos/](docs/pedidos/)), e o site diz o que falta. |
| 📦 **Bruto separado do tratado** | O arquivo da fonte é guardado como veio; tudo pode ser reprocessado a partir dele. |

## 🤝 Como ajudar

Não precisa programar:

- ✉️ **Contato:** [contato@panoptico.social.br](mailto:contato@panoptico.social.br) (imprensa, órgãos públicos, correções e dúvidas sobre dados).

- 🐛 **Número diferente da fonte?** Abra uma [issue](https://github.com/Gipsy7/panoptico/issues) com o link do perfil e da fonte.
- 💬 **Algo confuso no site?** Sugestões de texto são muito bem-vindas, principalmente de quem não acompanha política.
- 📡 **Conhece uma fonte boa?** Conte numa issue.
- 🗂 **Site oficial da sua cidade errado?** Corrija [data/canais_curados.csv](data/canais_curados.csv) por pull request.
- 💻 **Programa?** Veja [Como contribuir](#-como-contribuir).
- 💛 **Quer ajudar com os custos?** O site é gratuito e sem anúncios. A página [Apoie](https://panoptico.social.br/apoie) mostra quanto custa mantê-lo no ar. Doação não muda nada no que o site mostra, e não aceitamos dinheiro de partidos, mandatos ou campanhas.

<p align="center">
  <img src="frontend/public/pix-qr.svg" alt="QR code Pix para apoiar o Panóptico" width="160"><br>
  <sub>Pix (chave aleatória): <code>4c02a34c-095e-4990-9bdb-0fe161608f8c</code></sub>
</p>

---

## ⚙ Como funciona

```mermaid
flowchart LR
    subgraph fontes [Fontes oficiais]
        CD[Câmara e Senado]
        CGU[Portal da Transparência]
        TSE[TSE]
        LOC[Assembleias, câmaras,<br/>TCEs, SICONFI, IBGE...]
    end
    fontes -->|GitHub Actions<br/>diário/semanal/mensal| ING[Ingestão<br/>Python]
    ING -->|como veio| RAW[(Brutos)]
    ING -->|tratado| DB[(PostgreSQL)]
    DB --> API[API<br/>FastAPI]
    API --> WEB[Site<br/>Next.js]
    VIACEP[ViaCEP] -.->|CEP → cidade, sem gravar| API
    WEB --> U((Você))
```

1. **Ingestão** ([backend/ingestion/](backend/ingestion/)): grava o bruto em `data/raw/<fonte>/`, carrega no banco numa transação e registra em `fonte_ingestao`. Uma fonte com falha não derruba as outras.
2. **Banco**: PostgreSQL ([migrações](backend/alembic/)).
3. **API** ([backend/app/](backend/app/)): só leitura; cada resposta traz a fonte e a data.
4. **Site** ([frontend/](frontend/)): renderizado no servidor, pensado primeiro para celular e conexão fraca. Para buscadores e IAs: `/sitemap.xml` com os perfis, `/robots.txt`, `/llms.txt`, endereço canônico e dados estruturados (JSON-LD de perfil e de conjunto de dados).

<details>
<summary><b>🧮 Como os números são calculados</b></summary>

<br>

- **Média da Casa**: entre os parlamentares em exercício; quem não gastou ou não apresentou nada entra com zero.
- **Presença**: conta a partir do início do ano ou do mandato, o que vier depois. Quem preside a sessão conta como presente. Votação secreta conta presença sem revelar o voto.
- **Projetos**: PL, PLP, PEC e PDL desde fev/2023. O número principal conta só autoria principal (PECs têm dezenas de coautores).
- **Emendas na cidade**: pagas a favorecidos da própria cidade (prefeitura, fundos, entidades). Bancos intermediários e empresas ficam de fora.
- **Votos**: percentuais só do Plenário; comissões aparecem como lista.
- **TSE**: bens pelo valor declarado, sem correção. Ligação por CPF e título, nunca exibidos. Doador pessoa física não tem nome exibido.
- **Valor que parece digitado errado** (ex.: contrato maior que a despesa anual do município) fica fora das somas, com aviso, sem correção.

O porquê de cada escolha: [docs/DECISOES.md](docs/DECISOES.md).

</details>

<details>
<summary><b>📡 Fontes de dados</b></summary>

<br>

| Área | Fontes |
|---|---|
| Congresso | [Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/), [do Senado](https://legis.senado.leg.br/dadosabertos/), [CMO (RP9 2022)](https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/Indicacoes-para-execucao-orcamentaria-em-RP9_LOA-2022) |
| Dinheiro federal | [Portal da Transparência](https://portaldatransparencia.gov.br/), [TransfereGov](https://www.gov.br/transferegov/pt-br), Tesouro Nacional, Receita Federal, [PNCP](https://pncp.gov.br/) |
| Eleições e partidos | [Dados abertos do TSE](https://dadosabertos.tse.jus.br/) (2018, 2022, 2024 e 2026) |
| Controle e Justiça | CGU (CEIS, CNEP, CEAF), TCU, DataJud (CNJ), Conselhos de Ética, CPIs |
| Estados e cidades | Assembleias, câmaras (SAPL e outros), [SICONFI](https://siconfi.tesouro.gov.br/), [TCE-SP](https://transparencia.tce.sp.gov.br/conjunto-de-dados), [TCE-RS](https://dados.tce.rs.gov.br/), [SC Transferências](https://consultas.sctransferencias.cge.sc.gov.br/pesquisa-detalhada/emendas) |
| Executivo | e-Agendas (CGU): agenda de ministros e do vice |
| Apoio | [IBGE](https://servicodados.ibge.gov.br/api/docs/localidades), [ViaCEP](https://viacep.com.br/), base aberta do CNPJ, [Decreto Legislativo 172/2022](https://www2.camara.leg.br/legin/fed/decleg/2022/decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html) (salário) |

Endereço, formato, frequência e armadilhas de cada uma: [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md).

</details>

<details>
<summary><b>🔌 Rotas da API</b></summary>

<br>

Documentação interativa: [api.panoptico.social.br/docs](https://api.panoptico.social.br/docs).

| Rota | Retorna |
|---|---|
| `GET /representantes?cep=` · `?uf=` · `?municipio=` | Quem representa a localidade |
| `GET /parlamentares/{id}` | Perfil, contato e salário |
| `GET /parlamentares/{id}/gastos?ano=` | Gastos do gabinete e média da Casa |
| `GET /parlamentares/{id}/presenca?ano=` | Participação em votações nominais |
| `GET /parlamentares/{id}/projetos` | Projetos de lei desde 2023 |
| `GET /parlamentares/{id}/votos-por-tema?ano=` | Votações por tema, com a média da Casa |
| `GET /parlamentares/{id}/emendas-destino` | Situação dos convênios e transferências das emendas |
| `GET /votacoes/{casa}/{id}` | Placar, orientações, voto de cada parlamentar, placar por estado e discursos do dia |
| `GET /projetos?q=&esfera=&uf=&municipio=&tema=&ano=&votacao=&ordem=` | Busca de projetos e votações (Congresso, assembleias e câmaras); por padrão, primeiro os com mais informação publicada; `cobertura` diz quando a câmara ou a assembleia não tem dados aqui |
| `GET /projetos/{casa}/{id}` · `GET /projetos/local/{id}` | Projeto: ficha, votações, quem votou, discursos e caminho |
| `GET /votacoes/local/{id}` · `GET /pauta?casa=&dias=` · `GET /projetos/temas` | Votação local, pauta do Plenário e temas |
| `GET /municipios?uf=` · `GET /municipios/{ibge}/emendas` | Municípios e emendas recebidas |
| `GET /pessoas/de?tipo=&id=` · `GET /pessoas/{id}` | A pessoa por trás de um perfil |
| `GET /pessoas/{id}/eventos` · `/eventos.rss` | Linha do tempo (JSON ou feed Atom) |
| `GET /pessoas/{id}/sancoes` · `/servico-federal` · `/carreira` | Sanções, governo federal e eleições disputadas |
| `GET /segundo-turno?cep=` | Candidatos do 2º turno da localidade |
| `GET /partidos?ano=` · `GET /partidos/{sigla}` | Finanças dos partidos |
| `GET /estados/{uf}/contas` · `GET /executivo/{id}/painel` · `/agenda` | Contas estaduais e Executivo |
| `GET /casos` · `GET /casos/{slug}` | Casos montados com documentos oficiais |
| `GET /fontes` · `GET /saude` | Última atualização de cada fonte e saúde da API |

</details>

<details>
<summary><b>🧱 Stack e estrutura de pastas</b></summary>

<br>

| Camada | Tecnologia |
|---|---|
| Ingestão | Python 3.12, httpx, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL 18 (na VPS, em produção) |
| API | FastAPI, Pydantic |
| Site | Next.js 16 (App Router, Cache Components), React 19, Tailwind CSS 4, shadcn/ui |
| Qualidade | pytest, respx, Vitest, ruff, ESLint, TypeScript |
| Infra | VPS Locaweb, Docker Compose, Cloudflare, GitHub Actions |

```
panoptico/
├── backend/
│   ├── app/          # API: rotas, schemas e regras de cálculo
│   ├── ingestion/    # uma pasta por órgão; fontes.toml registra o acervo
│   ├── exportar/     # dumps abertos (Parquet e CSV.gz)
│   ├── analises/     # cruzamentos em SQL
│   ├── alembic/      # migrações
│   └── tests/
├── frontend/         # Next.js: app/, components/, lib/
├── data/             # CSVs versionados: canais oficiais, curadoria, atos revisados
├── docs/             # decisões, fontes, design, deploy e pedidos de acesso
├── deploy/           # alternativa em VPS (docker compose + Caddy)
└── .github/workflows # CI, publicação e ingestões
```

</details>

---

## 💻 Rodar localmente

**Precisa de:** Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 20+, PostgreSQL 16+ (nativo ou `docker compose up -d`).

```bash
# 1. Banco
psql -U postgres -f scripts/criar_banco.sql

# 2. API → http://localhost:8000/docs
cd backend
cp ../.env.example .env
uv sync
uv run alembic upgrade head
uv run python -m ingestion.run_all     # baixa as fontes (alguns minutos)
uv run uvicorn app.main:app

# 3. Site → http://localhost:3000
cd ../frontend
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm install && npm run dev
```

<details>
<summary><b>🧪 Testes</b></summary>

<br>

```bash
cd backend && uv run pytest && uv run ruff check && uv run ruff format --check
cd frontend && npm test && npm run lint && npm run build
# acessibilidade (axe, teclado, 320 px, 200%) contra um site no ar ou local:
cd frontend && E2E_BASE_URL=http://localhost:3000 npm run e2e
```

O backend usa o banco `panoptico_test` e simula as APIs externas com `respx`, a partir de amostras reais em `backend/tests/fixtures/`. O CI roda tudo a cada push; teste falhando impede a publicação.

</details>

<details>
<summary><b>📥 Ingestão avulsa</b></summary>

<br>

| Comando | O que faz |
|---|---|
| `uv run python -m ingestion.run_all` | Atualiza tudo (ano anterior e atual) |
| `uv run python -m ingestion.camara.despesas --ano 2025` | Uma fonte, um ano |
| `uv run python -m ingestion.camara.proposicoes --ano 2023 2024 2025 2026` | Projetos desde 2023 |
| `uv run python -m ingestion.camara.deputados --de-raw data/raw/camara_deputados/<arquivo>.json` | Reprocessa um bruto sem rede |

</details>

<details>
<summary><b>🗄 Acervo local</b> (fontes novas, sem os limites da produção)</summary>

<br>

Fontes novas (Justiça, controle, partidos, contratos) entram primeiro num banco local à parte, com todos os brutos. Registro em [backend/ingestion/fontes.toml](backend/ingestion/fontes.toml). Regra da **coleta mínima**: só se coleta o que tem uso declarado no site, e das bases grandes só o que se liga a pessoas públicas.

```bash
psql -U postgres -f scripts/criar_acervo.sql          # uma vez
cd backend
export DATABASE_URL=postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_acervo
export PRESERVAR_RAW=true RAW_DIR=/e/panoptico/raw     # RAW_DIR opcional
uv run alembic upgrade head

uv run python -m ingestion.acervo rodar --vencidas      # o que passou da frequência
uv run python -m ingestion.acervo rodar --fonte tse_bens sapl_assembleias
uv run python -m ingestion.acervo relatorio             # volume, últimas cargas e alertas
uv run python -m analises                               # lista os cruzamentos
```

Atualização diária no Windows: [scripts/acervo_diario.ps1](scripts/acervo_diario.ps1).

**Revisão humana** (nada sugerido vai ao site sem ela):

| Comando | Revisa |
|---|---|
| `uv run python -m ingestion.revisar` | Vínculos por nome aproximado |
| `uv run python -m ingestion.revisar_web` | O mesmo, numa página local com botões (http://127.0.0.1:8765) |
| `uv run python -m ingestion.revisar --tipo diario` | Nomeações e exonerações dos diários municipais |
| `uv run python -m ingestion.revisar --tipo dou` | Atos de pessoal do Diário Oficial da União |
| `uv run python -m ingestion.revisar --tipo cpi` | Pedidos de indiciamento das CPIs |

</details>

<details>
<summary><b>📤 Dados abertos</b> (Parquet e CSV.gz para pesquisa e jornalismo)</summary>

<br>

Um arquivo por conjunto (parlamentares, vereadores, eleitos, bens e campanha, linha do tempo, processos, CPIs, cota, partidos, PNCP, TCEs), com `LEIAME.md` e `dicionario.json` (colunas, fonte, data da carga, SHA-256).

```bash
cd backend
uv sync --group acervo
uv run python -m exportar --listar
uv run python -m exportar --destino saida --conjunto eventos pessoas_publicas
```

Nunca saem CPF, título, data de nascimento, pessoa sem vínculo publicável, sugestão não revisada nem caso em rascunho; os testes procuram esses dados nos arquivos gerados. Licença: [CC BY 4.0](LICENCA-DADOS.md).

</details>

<details>
<summary><b>🚀 Deploy e custo</b></summary>

<br>

- **Hoje (desde 26/10/2026):** uma VPS Locaweb em São Paulo (2 vCPU, 4 GB, 70 GB) com banco, API, site e ingestão, atrás do Cloudflare por túnel, sem portas abertas além do SSH. Push no `dev` → Publicar → `main` → a VPS se atualiza em até 10 min. Backup diário em bucket Oracle. Detalhes em [deploy/vps/LEIAME.md](deploy/vps/LEIAME.md).
- **Ingestões:** agenda systemd na VPS (diária, PNCP, justiça, câmaras, mensal).
- **Reserva congelada:** uma versão fixa do site, da API e do banco na Vercel e no Neon, que entra no ar sozinha se a VPS cair (o Worker `panoptico-troca` troca o DNS com 3 falhas seguidas e volta com 10 sucessos). Ela só é atualizada de propósito ([deploy/vps/LEIAME.md](deploy/vps/LEIAME.md), "Reserva congelada"). Backup diário do banco no Oracle Cloud (grátis). Histórico em [docs/DEPLOY_GRATUITO.md](docs/DEPLOY_GRATUITO.md).
- **Cloudflare:** DNS, proxy e cache (API por `s-maxage`, páginas 30 min); o firewall bloqueia só coletores em massa e robôs de SEO e libera os robôs de pesquisa e de treino das grandes IAs.
- **Custo:** VPS R$ 79,90/mês; reserva Vercel + Neon parada, cerca de R$ 5/mês; Cloudflare e Oracle no grátis (orçamento com alerta e trava de cotas); domínio cerca de R$ 40/ano. Veja a página [Apoie](https://panoptico.social.br/apoie).
- **Alternativa:** VPS genérica com docker compose e HTTPS automático ([docs/DEPLOY.md](docs/DEPLOY.md)).

</details>

---

## 🧑‍💻 Como contribuir

1. Abra uma [issue](https://github.com/Gipsy7/panoptico/issues) antes de algo grande.
2. Fork → branch a partir de `dev` → pull request para o `dev`. O `main` é só o que está no ar (avança pelo workflow **Publicar**).
3. Rode os [testes](#-rodar-localmente) antes de enviar; o CI precisa passar.

**Combinados:** fonte oficial com link e data · sem juízo de valor · linguagem do dia a dia · bruto separado do tratado (`--de-raw`) · decisão de metodologia vai para [docs/DECISOES.md](docs/DECISOES.md) · testes com amostras reais · tudo em português.

Leitura útil: [docs/DESIGN.md](docs/DESIGN.md) (padrões visuais), [docs/USABILIDADE.md](docs/USABILIDADE.md) (roteiro de teste com pessoas), [CLAUDE.md](CLAUDE.md) (regras e comandos para agentes de código).

## 🗺 Próximos passos

- [x] Identidade única de pessoa pública e linha do tempo
- [x] Sanções (CGU), TCU, cassações (TSE), Conselhos de Ética e CPIs na linha do tempo
- [x] Página de finanças dos partidos
- [x] Contratos do PNCP no perfil e na cidade
- [ ] Revisar as 164 sugestões de indiciamento das CPIs (Brumadinho, BNDES, Pandemia)
- [ ] Revisar os atos dos diários municipais e do DOU (cerca de 57 sugestões por mês desde 2025)
- [ ] Publicar os casos em rascunho (Mensalão, Sanguessugas, Zelotes) depois de revisão humana
- [ ] Partidos: pagamentos a fornecedores ligados à base, diretórios e eleições de 2016, 2020 e 2026
- [ ] Conectores para as 27 câmaras que saíram do SAPL e ainda não têm
- [ ] Proposições e gastos da ALEP, presença nas comissões da ALESP, tela das emendas estaduais de SC
- [ ] Fornecedores de outros Tribunais de Contas (MG exige reCAPTCHA; falta pedir acesso)
- [ ] Teste com pessoas reais e auditoria de acessibilidade

O plano completo está em [docs/DECISOES.md](docs/DECISOES.md) ("acervo local e regras para Justiça e controle").

## 📜 Licença

- **Código:** [AGPL-3.0](LICENSE). Quem publicar uma versão modificada precisa abrir o código dela, para que as melhorias de um projeto de transparência continuem abertas.
- **Dados abertos:** [CC BY 4.0](LICENCA-DADOS.md). Os dados de origem seguem as regras de cada fonte ([docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md)).

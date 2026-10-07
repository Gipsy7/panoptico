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

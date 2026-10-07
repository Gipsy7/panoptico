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

# Panóptico

Quem te representa, às claras. Digite o CEP e veja seus deputados federais e senadores, com dados oficiais e link para a fonte.

Plano e decisões em [docs/](docs/).

## Requisitos

- Python 3.12 e [uv](https://docs.astral.sh/uv/)
- Node 20 ou superior
- PostgreSQL 16 ou superior (nativo ou via `docker compose up -d`)

## Primeira configuração

```bash
# 1. Banco (Postgres nativo)
psql -U postgres -f scripts/criar_banco.sql

# 2. Backend
cd backend
cp ../.env.example .env        # ajuste se necessário
uv sync
uv run alembic upgrade head
uv run python -m ingestion.run_all   # baixa deputados e senadores
uv run uvicorn app.main:app --reload # http://localhost:8000/docs

# 3. Frontend
cd ../frontend
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm install
npm run dev                          # http://localhost:3000
```

## Testes

```bash
cd backend && uv run pytest && uv run ruff check
cd frontend && npm run lint
```

## Ingestão

- `uv run python -m ingestion.run_all` baixa e processa tudo.
- `uv run python -m ingestion.camara.deputados --de-raw data/raw/camara_deputados/<arquivo>.json` reprocessa um arquivo bruto sem rede.

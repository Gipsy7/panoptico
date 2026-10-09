-- Cria o banco do acervo local (dados de todas as fontes, sem os limites da produção).
-- Uso: psql -U postgres -f scripts/criar_acervo.sql
-- Depois: cd backend && DATABASE_URL=postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_acervo uv run alembic upgrade head
--
-- Para guardar as tabelas num HD externo, crie antes um tablespace (a pasta precisa existir
-- e pertencer ao serviço do Postgres) e troque a última linha:
--   CREATE TABLESPACE acervo OWNER panoptico LOCATION 'E:/panoptico/pg';
--   CREATE DATABASE panoptico_acervo OWNER panoptico ENCODING 'UTF8' TABLESPACE acervo;

CREATE DATABASE panoptico_acervo OWNER panoptico ENCODING 'UTF8';

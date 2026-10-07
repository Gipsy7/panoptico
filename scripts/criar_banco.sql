-- Cria o usuário e os bancos do Panóptico no PostgreSQL local.
-- Uso: psql -U postgres -f scripts/criar_banco.sql
-- A senha abaixo é só para desenvolvimento local.

CREATE ROLE panoptico WITH LOGIN PASSWORD 'panoptico';
CREATE DATABASE panoptico OWNER panoptico ENCODING 'UTF8';
CREATE DATABASE panoptico_test OWNER panoptico ENCODING 'UTF8';

"""Executa uma consulta SQL de leitura no banco do DATABASE_URL e imprime as linhas."""

import os
import sys

from sqlalchemy import create_engine, text

with create_engine(os.environ["DATABASE_URL"]).connect() as c:
    for r in c.execute(text(sys.argv[1])):
        print(tuple(r))

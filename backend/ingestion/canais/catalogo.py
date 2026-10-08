"""Carrega o catálogo versionado data/canais_oficiais.csv na tabela canal_oficial.

O catálogo é a fonte da verdade (revisado por pull request); esta carga só o copia para o
banco. Roda na ingestão diária, é rápida e não acessa nenhum site.
"""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import delete, insert, select

from app.db import SessionLocal
from app.models import CanalOficial, FonteIngestao, Municipio
from ingestion.canais.varredura import CATALOGO

FONTE = "canais_oficiais"


def ler(caminho: Path = CATALOGO) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {
                "municipio_ibge": linha["ibge"],
                "tipo": linha["tipo"],
                "url": linha["url"],
                "sistema": linha["sistema"] or None,
                "verificado_em": date.fromisoformat(linha["verificado_em"])
                if linha["verificado_em"]
                else None,
            }
            for linha in csv.DictReader(arquivo)
        ]


def executar(caminho: Path = CATALOGO) -> int:
    linhas = ler(caminho)
    if not linhas:
        return 0  # sem catálogo ainda: não apaga o que existe
    with SessionLocal() as session:
        validos = set(session.scalars(select(Municipio.ibge)))
        linhas = [linha for linha in linhas if linha["municipio_ibge"] in validos]
        session.execute(delete(CanalOficial))
        for inicio in range(0, len(linhas), 5000):
            session.execute(insert(CanalOficial), linhas[inicio : inicio + 5000])
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="data/canais_oficiais.csv",
                arquivo_raw=str(caminho),
                registros=len(linhas),
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    return len(linhas)


if __name__ == "__main__":
    print(f"{FONTE}: {executar()} canais")

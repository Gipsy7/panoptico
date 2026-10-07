"""Temas oficiais das proposições da Câmara.

Duas origens, gravadas juntas num .zip bruto:
- os arquivos anuais `proposicoesTemas-{ano}.csv`, da legislatura atual em diante
  (cobrem os projetos apresentados no período);
- a API `/proposicoes/{id}/temas` para as proposições votadas no Plenário que não estão
  nesses arquivos (matérias antigas, como um PL de 2015 votado em 2025).

A carga substitui todos os temas da Câmara.
"""

import argparse
import csv
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, ProposicaoTema, Votacao
from ingestion import comum
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE = "camara_temas"
CASA = "camara"
URL_ANO = (
    "https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/csv/proposicoesTemas-{ano}.csv"
)
URL_API = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/temas"
API_JSON = "api.json"


def _anos() -> list[int]:
    return list(range(INICIO_LEGISLATURA.year, comum.anos_padrao()[-1] + 1))


def _id_da_uri(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _ler_csv(conteudo: bytes):
    return csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig")), delimiter=";")


def _proposicoes_votadas() -> set[str]:
    with SessionLocal() as session:
        ids = session.scalars(
            select(Votacao.proposicao_id_externo)
            .where(Votacao.casa == CASA, Votacao.proposicao_id_externo.is_not(None))
            .distinct()
        )
        return set(ids)


def baixar(client: httpx.Client) -> bytes:
    arquivos = {
        f"temas_{ano}.csv": comum.get_bytes(client, URL_ANO.format(ano=ano)) for ano in _anos()
    }
    cobertos = {
        _id_da_uri(linha["uriProposicao"])
        for conteudo in arquivos.values()
        for linha in _ler_csv(conteudo)
    }
    faltando = sorted(_proposicoes_votadas() - cobertos)
    with ThreadPoolExecutor(max_workers=8) as pool:
        respostas = pool.map(
            lambda i: comum.get_json(client, URL_API.format(id=i))["dados"], faltando
        )
        api = dict(zip(faltando, respostas, strict=True))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
        z.writestr(API_JSON, json.dumps(api, ensure_ascii=False))
    return buffer.getvalue()


def normalizar(conteudo: bytes) -> list[dict[str, Any]]:
    registros: set[tuple[str, str]] = set()
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in z.namelist():
            if nome.endswith(".csv"):
                for linha in _ler_csv(z.read(nome)):
                    if linha["tema"].strip():
                        registros.add((_id_da_uri(linha["uriProposicao"]), linha["tema"].strip()))
            elif nome == API_JSON:
                for id_, temas in json.loads(z.read(nome)).items():
                    registros.update((id_, t["tema"].strip()) for t in temas if t.get("tema"))
    return [
        {"casa": CASA, "proposicao_id_externo": id_, "tema": tema}
        for id_, tema in sorted(registros)
    ]


def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    registros = normalizar(conteudo)
    if not registros:
        raise ValueError("Nenhum tema no arquivo; abortando para não zerar os temas.")
    session.execute(delete(ProposicaoTema).where(ProposicaoTema.casa == CASA))
    for inicio in range(0, len(registros), 5000):
        session.execute(insert(ProposicaoTema), registros[inicio : inicio + 5000])
    return len(registros)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(
        FONTE, URL_ANO.format(ano="{ano}"), baixar, carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} temas")

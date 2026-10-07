"""Projetos de lei de autoria dos senadores em exercício (API de processos do Senado).

A API é consultada senador a senador. O primeiro nome do campo `autoria` é o
primeiro autor; os demais são coautores (comum em PECs, que exigem 27 assinaturas).
"""

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, Parlamentar
from ingestion import comum
from ingestion import proposicoes_comum as pc

CASA = "senado"
FONTE = "senado_proposicoes"
URL = "https://legis.senado.leg.br/dadosabertos/processo"
URL_PAGINA = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo}"
IDENTIFICACAO = re.compile(r"^(?P<sigla>[A-Z]+) (?P<numero>\d+)/(?P<ano>\d{4})$")


def primeiro_autor(autoria: str | None) -> str:
    """'Senador Fulano (PL/RJ), Senadora Beltrana (...)' -> 'Fulano'."""
    primeiro = (autoria or "").split(",")[0]
    primeiro = re.sub(r"^Senador(a)?\s+", "", primeiro.strip())
    return re.sub(r"\s*\(.*$", "", primeiro).strip()


def baixar(client: httpx.Client, codigos: list[str]) -> dict[str, list]:
    return {
        codigo: comum.get_json(client, URL, params={"codigoParlamentarAutor": codigo})
        for codigo in codigos
    }


def normalizar(payload: dict[str, list], nomes: dict[str, str]) -> tuple[list, list]:
    """Devolve (proposições únicas, autorias por código de senador)."""
    proposicoes: dict[str, dict[str, Any]] = {}
    autorias = []
    for codigo, processos in payload.items():
        for p in processos:
            m = IDENTIFICACAO.match(p.get("identificacao") or "")
            if not m or m["sigla"] not in pc.TIPOS or p.get("casaIdentificadora") != "SF":
                continue
            apresentacao = date.fromisoformat(p["dataApresentacao"][:10])
            if apresentacao < pc.INICIO_LEGISLATURA:
                continue
            id_externo = str(p["codigoMateria"])
            proposicoes[id_externo] = {
                "id_externo": id_externo,
                "sigla_tipo": m["sigla"],
                "numero": int(m["numero"]),
                "ano": int(m["ano"]),
                "ementa": " ".join((p.get("ementa") or "").split()),
                "data_apresentacao": apresentacao,
                "situacao": (p.get("situacaoAtual") or "").capitalize() or None,
                "virou_lei": pc.virou_lei(p.get("situacaoAtual")),
                "url": URL_PAGINA.format(codigo=id_externo),
            }
            autorias.append(
                {
                    "id_externo": id_externo,
                    "codigo_senador": codigo,
                    "primeiro_autor": primeiro_autor(p.get("autoria")) == nomes.get(codigo),
                }
            )
    return list(proposicoes.values()), autorias


def _senadores(session: Session) -> dict[str, str]:
    linhas = session.execute(
        select(Parlamentar.id_externo, Parlamentar.nome_parlamentar).where(
            Parlamentar.casa == CASA, Parlamentar.em_exercicio.is_(True)
        )
    )
    return {id_externo: nome for id_externo, nome in linhas}


def carregar(session: Session, payload: dict[str, list], ingestao: FonteIngestao) -> int:
    registros, autorias = normalizar(payload, _senadores(session))
    if not registros:
        raise ValueError("Nenhuma proposição do Senado; abortando.")
    proposicoes = pc.upsert_proposicoes(session, CASA, registros, ingestao)
    senadores = comum.mapa_parlamentares(session, CASA)
    linhas = [
        {
            "proposicao_id": proposicoes[a["id_externo"]],
            "parlamentar_id": senadores[a["codigo_senador"]],
            "primeiro_autor": a["primeiro_autor"],
        }
        for a in autorias
        if a["codigo_senador"] in senadores
    ]
    return pc.substituir_autorias(session, list(proposicoes.values()), linhas)


def executar(de_raw: Path | None = None) -> int:
    with SessionLocal() as session:
        codigos = list(_senadores(session))
    return comum.executar_ingestao(
        FONTE, URL, lambda client: baixar(client, codigos), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} autorias")

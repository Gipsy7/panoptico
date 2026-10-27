"""Projetos de lei de autoria dos senadores em exercício (API de processos do Senado).

A API é consultada senador a senador. O primeiro nome do campo `autoria` é o
primeiro autor; os demais são coautores (comum em PECs, que exigem 27 assinaturas).

Além disso, a lista geral (`/processo?sigla=&ano=`) traz os PL/PLP/PEC/PDL desde 2023 que
nenhum senador em exercício assinou (vindos da Câmara, de comissões e CPIs): entram sem
autoria, com `autor_descricao`. E as matérias citadas em votações nominais que a tabela não
tem (anteriores a 2023, MPV...) entram como "votadas" (`/processo?codigoMateria=`).
O bruto é um dicionário: um item por senador (chave = código) mais `__geral` e `__votadas`.
"""

import argparse
import re
import time
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
CHAVE_GERAL = "__geral"
CHAVE_VOTADAS = "__votadas"
PAUSA = 0.3
IDENTIFICACAO = re.compile(r"^(?P<sigla>[A-Z]+) (?P<numero>\d+)/(?P<ano>\d{4})$")


def primeiro_autor(autoria: str | None) -> str:
    """'Senador Fulano (PL/RJ), Senadora Beltrana (...)' -> 'Fulano'."""
    primeiro = (autoria or "").split(",")[0]
    primeiro = re.sub(r"^Senador(a)?\s+", "", primeiro.strip())
    return re.sub(r"\s*\(.*$", "", primeiro).strip()


def baixar(
    client: httpx.Client, codigos: list[str], votadas: list[str] | None = None
) -> dict[str, list]:
    payload: dict[str, list] = {
        codigo: comum.get_json(client, URL, params={"codigoParlamentarAutor": codigo})
        for codigo in codigos
    }
    geral: list = []
    for sigla in sorted(pc.TIPOS):
        for ano in range(pc.INICIO_LEGISLATURA.year, date.today().year + 1):
            time.sleep(PAUSA)
            geral += comum.get_json(client, URL, params={"sigla": sigla, "ano": ano})
    payload[CHAVE_GERAL] = geral
    votadas_fichas: list = []
    for codigo in votadas or []:
        time.sleep(PAUSA)
        votadas_fichas += comum.get_json(client, URL, params={"codigoMateria": codigo})
    payload[CHAVE_VOTADAS] = votadas_fichas
    return payload


def _registro(p: dict[str, Any], m: re.Match[str], apresentacao: date) -> dict[str, Any]:
    id_externo = str(p["codigoMateria"])
    return {
        "id_externo": id_externo,
        "sigla_tipo": m["sigla"],
        "numero": int(m["numero"]),
        "ano": int(m["ano"]),
        "ementa": " ".join((p.get("ementa") or "").split()),
        "data_apresentacao": apresentacao,
        "situacao": (p.get("situacaoAtual") or "").capitalize() or None,
        "virou_lei": pc.virou_lei(p.get("situacaoAtual")),
        "url": URL_PAGINA.format(codigo=id_externo),
        "autor_descricao": None,
    }


def _descricao_autoria(autoria: str | None) -> str | None:
    return " ".join((autoria or "").split())[:300] or None


def normalizar_geral(payload: list[dict], ja_tem: set[str]) -> list[dict[str, Any]]:
    """PL/PLP/PEC/PDL desde 2023 da lista geral que a carga por senador não trouxe."""
    novos: dict[str, dict[str, Any]] = {}
    for p in payload:
        m = IDENTIFICACAO.match(p.get("identificacao") or "")
        if not m or m["sigla"] not in pc.TIPOS or p.get("casaIdentificadora") != "SF":
            continue
        if not p.get("dataApresentacao") or str(p["codigoMateria"]) in ja_tem:
            continue
        apresentacao = date.fromisoformat(p["dataApresentacao"][:10])
        if apresentacao < pc.INICIO_LEGISLATURA:
            continue
        registro = _registro(p, m, apresentacao)
        registro["autor_descricao"] = _descricao_autoria(p.get("autoria"))
        registro["origem"] = pc.ORIGEM_LEGISLATURA
        novos[registro["id_externo"]] = registro
    return list(novos.values())


def normalizar_votadas(payload: list[dict]) -> list[dict[str, Any]]:
    """Fichas das matérias votadas (qualquer sigla, qualquer ano; MPV vem como "CN")."""
    votadas: dict[str, dict[str, Any]] = {}
    for p in payload:
        m = IDENTIFICACAO.match(p.get("identificacao") or "")
        if not m or not p.get("dataApresentacao"):
            continue
        registro = _registro(p, m, date.fromisoformat(p["dataApresentacao"][:10]))
        registro["autor_descricao"] = _descricao_autoria(p.get("autoria"))
        votadas[registro["id_externo"]] = registro
    return list(votadas.values())


def normalizar(payload: dict[str, list], nomes: dict[str, str]) -> tuple[list, list]:
    """Devolve (proposições únicas, autorias por código de senador)."""
    proposicoes: dict[str, dict[str, Any]] = {}
    autorias = []
    for codigo, processos in payload.items():
        if codigo.startswith("__"):
            continue
        for p in processos:
            m = IDENTIFICACAO.match(p.get("identificacao") or "")
            if not m or m["sigla"] not in pc.TIPOS or p.get("casaIdentificadora") != "SF":
                continue
            apresentacao = date.fromisoformat(p["dataApresentacao"][:10])
            if apresentacao < pc.INICIO_LEGISLATURA:
                continue
            registro = _registro(p, m, apresentacao)
            registro["origem"] = pc.ORIGEM_LEGISLATURA
            id_externo = registro["id_externo"]
            proposicoes[id_externo] = registro
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
    gerais = normalizar_geral(payload.get(CHAVE_GERAL, []), {r["id_externo"] for r in registros})
    proposicoes = pc.upsert_proposicoes(session, CASA, registros + gerais, ingestao)
    pc.inserir_votadas(
        session,
        CASA,
        [
            r
            for r in normalizar_votadas(payload.get(CHAVE_VOTADAS, []))
            if r["id_externo"] not in proposicoes
        ],
        ingestao,
    )
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
    # Só as proposições dos senadores têm autoria a trocar; as da lista geral não têm autor.
    deles = [proposicoes[r["id_externo"]] for r in registros]
    return pc.substituir_autorias(session, deles, linhas)


def executar(de_raw: Path | None = None) -> int:
    with SessionLocal() as session:
        codigos = list(_senadores(session))
        votadas = pc.ids_votados_faltantes(session, CASA)
    return comum.executar_ingestao(
        FONTE, URL, lambda client: baixar(client, codigos, votadas), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} autorias")

"""Representações no Conselho de Ética do Senado (processos do tipo REP), como eventos da
linha do tempo do senador representado.

O representado vem na ementa ("Requer a abertura de procedimento disciplinar
(Representação) em face do Senador Chico Rodrigues com fundamento..."). A ligação segue a
mesma regra da Câmara (ingestion.camara.etica): nome exato e único num conjunto fechado
(senadores no cadastro do Senado e senadores eleitos). Rota: /dadosabertos/processo, que
substitui a pesquisa de matérias descontinuada.
"""

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, PessoaVinculo
from ingestion import comum
from ingestion.camara.etica import deputados_por_nome

FONTE = "senado_etica"
URL = "https://legis.senado.leg.br/dadosabertos/processo"
URL_PROCESSO = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo}"
DESDE = "2019-01-01"
NOME = re.compile(
    r"Senador[a]?\s+(.+?)(?:,|\s+com\s+fundamento|\s+por\s|\s+pela\s|\s+em\s+raz|\.\s|\.$|$)",
    re.I,
)


def nomes_na_ementa(ementa: str) -> list[str]:
    nomes = []
    for trecho in NOME.findall(" ".join((ementa or "").split())):
        nome = trecho.strip(" .,;")
        if len(nome) > 2 and nome not in nomes:
            nomes.append(nome)
    return nomes


def eventos(representacoes: list[dict], senadores: dict[str, int]) -> tuple[list[dict], int]:
    linhas, sem = [], 0
    for r in representacoes:
        ligados = {senadores.get(comum.chave_nome(n)) for n in nomes_na_ementa(r.get("ementa"))}
        ligados.discard(None)
        if not ligados:
            sem += 1
            continue
        for pessoa in sorted(ligados):
            linhas.append(
                {
                    "pessoa_id": pessoa,
                    "id_externo": f"{r['id']}:{pessoa}",
                    "data": date.fromisoformat(r["dataApresentacao"])
                    if r.get("dataApresentacao")
                    else None,
                    "tipo": "conselho_etica",
                    "descricao": (
                        f"{r['identificacao']} no Conselho de Ética do Senado, de autoria de "
                        f"{r.get('autoria') or 'autor não informado'}: "
                        f'"{" ".join((r.get("ementa") or "").split())}"'
                    ),
                    "orgao": "Senado Federal – Conselho de Ética",
                    "numero_processo": r["identificacao"][:40],
                    "situacao": (r.get("situacaoAtual") or "").capitalize()[:80] or None,
                    "fonte_url": URL_PROCESSO.format(codigo=r["codigoMateria"]),
                }
            )
    return linhas, sem


def gravar(session: Session, representacoes: list[dict], ingestao_id: int | None) -> int:
    linhas, sem = eventos(representacoes, deputados_por_nome(session, "senado", "SENADOR"))
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))
    for linha in linhas:
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=linha["pessoa_id"], fonte=FONTE, id_externo=linha["id_externo"],
                    regra="nome_parlamentar")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        session.execute(
            insert(Evento).values(
                **linha, vinculo_id=vinculo_id, fonte=FONTE, ingestao_id=ingestao_id
            )
        )
    print(f"  {len(representacoes)} representações; {len(linhas)} ligações; {sem} sem senador")
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Any:
        return comum.get_json(client, URL, params={"sigla": "REP", "dataInicioApresentacao": DESDE})

    def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
        return gravar(session, payload, ingestao.id)

    return comum.executar_ingestao(FONTE, URL + "?sigla=REP", baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    print(f"{FONTE}: {executar(parser.parse_args().de_raw)} representações ligadas")

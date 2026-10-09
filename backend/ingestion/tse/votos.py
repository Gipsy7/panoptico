"""Votos recebidos por candidatura (votacao_candidato_munzona), somados de todas as zonas.

O arquivo traz uma linha por candidato × município × zona × turno (575 MB em 2022): é
baixado para o disco e lido em fluxo. Guardamos os votos nominais válidos do último turno
que o candidato disputou, que é o que definiu o resultado.
"""

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import bindparam, select, update
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_votos"
URL = f"{comum_tse.BASE}/votacao_candidato_munzona/votacao_candidato_munzona_{{ano}}.zip"


def somar(linhas: Any, interesse: set[str]) -> dict[str, int]:
    """SQ -> votos válidos no último turno disputado."""
    por_turno: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for linha in linhas:
        sq = linha["SQ_CANDIDATO"].strip()
        if sq not in interesse:
            continue
        turno = int(linha.get("NR_TURNO") or 1)
        valor = linha.get("QT_VOTOS_NOMINAIS_VALIDOS") or linha.get("QT_VOTOS_NOMINAIS") or "0"
        por_turno[sq][turno] += int(valor) if valor.lstrip("-").isdigit() and int(valor) > 0 else 0
    return {sq: turnos[max(turnos)] for sq, turnos in por_turno.items()}


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        candidaturas = dict(
            session.execute(
                select(Candidatura.sq_candidato, Candidatura.id).where(
                    Candidatura.ano_eleicao == ano
                )
            ).all()
        )
        if not candidaturas:
            return 0
        votos = somar(
            comum_tse.linhas(payload, f"votacao_candidato_munzona_{ano}_"), set(candidaturas)
        )
        if not votos:
            raise ValueError(f"Nenhum voto encontrado em {ano}; abortando.")
        parametros = [{"id_": candidaturas[sq], "valor": v} for sq, v in votos.items()]
        stmt = (
            update(Candidatura)
            .where(Candidatura.id == bindparam("id_"))
            .values(votos=bindparam("valor"))
        )
        for inicio in range(0, len(parametros), 5000):
            session.connection().execute(stmt, parametros[inicio : inicio + 5000])
        return len(parametros)

    return comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(
            sonda=URL.format(ano=ano), contexto=comum.contexto_candidaturas(ano)
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2018, 2022, 2024])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} candidaturas com votos")

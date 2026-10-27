"""Votos recebidos por candidatura (votacao_candidato_munzona), somados de todas as zonas.

O arquivo traz uma linha por candidato × município × zona × turno (575 MB em 2022): é
baixado para o disco e lido em fluxo. Guardamos os votos nominais válidos do último turno
que o candidato disputou, que é o que definiu o resultado.
"""

import argparse
from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import bindparam, extract, select, update
from sqlalchemy.orm import Session, aliased

from app.models import Candidatura, FonteIngestao
from ingestion import comum
from ingestion.tse import comum_tse
from ingestion.tse.candidaturas import ANOS_SITUACAO_PELA_VOTACAO, situacao_final

FONTE = "tse_votos"
URL = f"{comum_tse.BASE}/votacao_candidato_munzona/votacao_candidato_munzona_{{ano}}.zip"


# Em 1998 os candidatos a presidente só aparecem no arquivo "_BRASIL" (que nos outros anos
# repete os estados e fica de fora); dele lemos só as linhas de presidente.
PRESIDENTE_SO_NO_BRASIL = {1998}


def presidente(linhas: Any) -> Any:
    return (linha for linha in linhas if linha["DS_CARGO"].strip().upper() == "PRESIDENTE")


CARGOS_2_TURNO = {"PRESIDENTE", "GOVERNADOR"}


def vencedores_2_turno(disputas: dict[str, list[Any]]) -> dict[str, str]:
    """SQ -> "ELEITO"/"NÃO ELEITO" no 2º turno de presidente e governador quando o TSE
    publica a situação vazia (#NULO, caso de 2006). É a regra do 2º turno (Constituição,
    art. 77, §3º, e art. 28): com exatamente 2 candidatos, vence o mais votado. Mais de 2,
    situação já informada para algum deles ou empate: não decide.
    `disputas`: SQ -> [cargo, UF, votos, situação informada] das linhas do 2º turno."""
    grupos: dict[tuple[str, str], list[str]] = defaultdict(list)
    for sq, (cargo, uf, *_) in disputas.items():
        grupos[(cargo, uf)].append(sq)
    resultado = {}
    for sqs in grupos.values():
        if len(sqs) != 2 or any(disputas[sq][3] for sq in sqs):
            continue
        a, b = sqs
        if disputas[a][2] == disputas[b][2]:
            continue
        ganhou, perdeu = (a, b) if disputas[a][2] > disputas[b][2] else (b, a)
        resultado[ganhou], resultado[perdeu] = "ELEITO", "NÃO ELEITO"
    return resultado


def resumir(
    linhas: Any, interesse: set[str], disputas: dict[str, list[Any]] | None = None
) -> tuple[dict[str, int], dict[str, str]]:
    """(SQ -> votos válidos no último turno disputado, SQ -> situação final desse turno).
    A situação só existe quando o arquivo a traz (em 2006 o 2º turno vem como #NULO)."""
    por_turno: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    situacao_do_turno: dict[str, dict[int, str | None]] = defaultdict(dict)
    for linha in linhas:
        sq = comum_tse.sq_candidato(linha)
        turno = int(linha.get("NR_TURNO") or 1)
        valor = linha.get("QT_VOTOS_NOMINAIS_VALIDOS") or linha.get("QT_VOTOS_NOMINAIS") or "0"
        n = int(valor) if valor.lstrip("-").isdigit() and int(valor) > 0 else 0
        cargo = (linha.get("DS_CARGO") or "").strip().upper()
        if disputas is not None and turno == 2 and cargo in CARGOS_2_TURNO:
            disputa = disputas.setdefault(sq, [cargo, comum_tse.uf_da_disputa(linha), 0, False])
            disputa[2] += n
            disputa[3] = disputa[3] or situacao_final(linha) is not None
        if sq not in interesse:
            continue
        situacao_do_turno[sq][turno] = situacao_final(linha)
        por_turno[sq][turno] += n
    votos = {sq: turnos[max(turnos)] for sq, turnos in por_turno.items()}
    situacoes = {
        sq: turnos[max(turnos)] for sq, turnos in situacao_do_turno.items() if turnos[max(turnos)]
    }
    return votos, situacoes


def somar(linhas: Any, interesse: set[str]) -> dict[str, int]:
    """SQ -> votos válidos no último turno disputado."""
    return resumir(linhas, interesse)[0]


def herdar_situacao_dos_vices(session: Session, ano: int) -> None:
    """Vice sem situação herda a do titular da chapa (se ele tiver)."""
    titular = aliased(Candidatura)
    session.execute(
        update(Candidatura)
        .where(
            Candidatura.ano_eleicao == ano,
            Candidatura.situacao_turno.is_(None),
            Candidatura.chapa_titular_id == titular.id,
            titular.situacao_turno.is_not(None),
        )
        .values(situacao_turno=titular.situacao_turno)
    )


def resultado_ja_gravado(
    session: Session, ano: int, candidaturas: dict[str, int], disputas: dict[str, list[Any]]
) -> set[str]:
    """SQ cujos votos do 2º turno já vieram da divulgação do TSE (tse_resultado_2_turno) e que o
    arquivo ainda não traz votos de 2º turno (versão de antes da apuração: sem linha do 2º
    turno ou com zero voto). Nesse caso a carga não troca os votos do 2º turno pelos do 1º."""
    gravados = session.scalars(
        select(Candidatura.sq_candidato).where(
            Candidatura.ano_eleicao == ano,
            Candidatura.cargo.in_(CARGOS_2_TURNO),
            Candidatura.situacao_turno.in_(("ELEITO", "NÃO ELEITO")),
            Candidatura.votos.is_not(None),
            extract("month", Candidatura.data_eleicao) == 10,
            extract("day", Candidatura.data_eleicao) >= 25,
        )
    )
    return {sq for sq in gravados if sq in candidaturas and not disputas.get(sq, [0, 0, 0])[2]}


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
        prefixo = f"votacao_candidato_munzona_{ano}_"
        linhas = comum_tse.linhas(payload, prefixo)
        if ano in PRESIDENTE_SO_NO_BRASIL:
            linhas = chain(linhas, presidente(comum_tse.linhas(payload, prefixo, so_brasil=True)))
        disputas: dict[str, list[Any]] = {}
        votos, situacoes = resumir(linhas, set(candidaturas), disputas)
        if ano in ANOS_SITUACAO_PELA_VOTACAO:
            # Só para o 2º turno de presidente e governador (ver vencedores_2_turno).
            situacoes.update(vencedores_2_turno(disputas))
        if not votos:
            raise ValueError(f"Nenhum voto encontrado em {ano}; abortando.")
        for sq in resultado_ja_gravado(session, ano, candidaturas, disputas):
            votos.pop(sq, None)
        parametros = [{"id_": candidaturas[sq], "valor": v} for sq, v in votos.items()]
        stmt = (
            update(Candidatura)
            .where(Candidatura.id == bindparam("id_"))
            .values(votos=bindparam("valor"))
        )
        for inicio in range(0, len(parametros), 5000):
            session.connection().execute(stmt, parametros[inicio : inicio + 5000])
        if ano in ANOS_SITUACAO_PELA_VOTACAO:
            # Só preenche o que veio vazio; nunca troca um resultado que o TSE já informou.
            preencher = [
                {"id_": candidaturas[sq], "valor": s}
                for sq, s in situacoes.items()
                if sq in candidaturas
            ]
            stmt_situacao = (
                update(Candidatura)
                .where(Candidatura.id == bindparam("id_"), Candidatura.situacao_turno.is_(None))
                .values(situacao_turno=bindparam("valor"))
            )
            for inicio in range(0, len(preencher), 5000):
                session.connection().execute(stmt_situacao, preencher[inicio : inicio + 5000])
            herdar_situacao_dos_vices(session, ano)
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

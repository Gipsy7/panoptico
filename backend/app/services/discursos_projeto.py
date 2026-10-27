"""Discursos em Plenário de um projeto, agrupados pelo voto que o orador registrou.

Regras (docs/DECISOES.md, 2026-10-21):
- A ligação guardada é projeto + dia (`discurso.proposicao_id_externo` e a data), nunca uma
  votação específica.
- Cada discurso é agrupado pelo voto do orador na última votação nominal do projeto naquele
  dia. Grupos fixos, sempre nesta ordem: "votou Sim", "votou Não", "outro registro" (qualquer
  outro registro da votação: abstenção, obstrução, ausência, voto secreto) e "falou e não
  registrou voto" (sem registro na votação, ou dia sem votação nominal do projeto).
- Dentro do grupo, ordem cronológica. Nunca inferimos posição pelo texto do discurso."""

import re
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Discurso, Parlamentar, Votacao, Voto

GRUPOS = [
    ("sim", "votou Sim"),
    ("nao", "votou Não"),
    ("outro", "outro registro"),
    ("sem_voto", "falou e não registrou voto"),
]


def ordem_da_votacao(votacao: Votacao) -> tuple:
    """Ordem cronológica de votações: a data e, no mesmo dia, o número do id da fonte
    (Câmara "2645346-18", Senado "7104"), que cresce no tempo."""
    numeros = tuple(int(n) for n in re.findall(r"\d+", votacao.id_externo))
    return (votacao.data, numeros, votacao.id)


def votacoes_do_projeto(session: Session, casa: str, proposicao_id_externo: str) -> list[Votacao]:
    """Todas as votações nominais do projeto, da mais antiga para a mais recente."""
    votacoes = session.scalars(
        select(Votacao).where(
            Votacao.casa == casa, Votacao.proposicao_id_externo == proposicao_id_externo
        )
    ).all()
    return sorted(votacoes, key=ordem_da_votacao)


def final_de_cada_dia(votacoes: list[Votacao]) -> dict[date, Votacao]:
    """A última votação nominal do projeto em cada dia (`votacoes` já em ordem)."""
    return {v.data: v for v in votacoes}


def _chave_do_voto(voto: str | None) -> str:
    if voto is None:
        return "sem_voto"
    if voto == "Sim":
        return "sim"
    if voto == "Não":
        return "nao"
    return "outro"


def discursos_por_dia(
    session: Session,
    casa: str,
    proposicao_id_externo: str,
    votacoes: list[Votacao],
    apenas_dia: date | None = None,
) -> list[dict]:
    """Um item por dia com discurso: `data`, `votacao_id_externo` (a final do dia, se houver),
    `total` e os quatro `grupos`."""
    consulta = (
        select(Discurso, Parlamentar.nome_parlamentar, Parlamentar.partido, Parlamentar.uf)
        .outerjoin(Parlamentar, Parlamentar.id == Discurso.parlamentar_id)
        .where(Discurso.casa == casa, Discurso.proposicao_id_externo == proposicao_id_externo)
        .order_by(Discurso.data, Discurso.data_hora, Discurso.id)
    )
    if apenas_dia is not None:
        consulta = consulta.where(Discurso.data == apenas_dia)
    linhas = [r for r in session.execute(consulta).all() if r[1] is not None]

    finais = final_de_cada_dia(votacoes)
    votos: dict[tuple[int, int], str] = {}
    ids = [v.id for v in finais.values()]
    pessoas = {d.parlamentar_id for d, *_ in linhas if d.parlamentar_id is not None}
    if ids and pessoas:
        votos = {
            (votacao_id, pid): voto
            for votacao_id, pid, voto in session.execute(
                select(Voto.votacao_id, Voto.parlamentar_id, Voto.voto).where(
                    Voto.votacao_id.in_(ids), Voto.parlamentar_id.in_(pessoas)
                )
            )
        }

    por_dia: dict[date, dict[str, list[dict]]] = defaultdict(lambda: {k: [] for k, _ in GRUPOS})
    for discurso, nome, partido, uf in linhas:
        final = finais.get(discurso.data)
        voto = votos.get((final.id, discurso.parlamentar_id)) if final else None
        por_dia[discurso.data][_chave_do_voto(voto)].append(
            {
                "parlamentar_id": discurso.parlamentar_id,
                "nome": nome,
                "partido": partido,
                "uf": uf,
                "data": discurso.data,
                "data_hora": discurso.data_hora,
                "fase": discurso.fase,
                "tipo": discurso.tipo,
                "sumario": discurso.sumario,
                "url_texto": discurso.url_texto,
                "url_video": discurso.url_video,
            }
        )
    dias = []
    for dia in sorted(por_dia):
        grupos = [
            {
                "chave": chave,
                "rotulo": rotulo,
                "quantidade": len(por_dia[dia][chave]),
                "discursos": por_dia[dia][chave],
            }
            for chave, rotulo in GRUPOS
        ]
        dias.append(
            {
                "data": dia,
                "votacao_id_externo": finais[dia].id_externo if dia in finais else None,
                "total": sum(g["quantidade"] for g in grupos),
                "grupos": grupos,
            }
        )
    return dias


def nao_atribuidos(session: Session, casa: str, votacoes: list[Votacao]) -> int:
    """Discursos de Plenário nos dias de votação do projeto que a ingestão não ligou a nenhum
    projeto (citam 3 ou mais matérias, ou duas votadas no mesmo dia, ou nenhuma). Não são
    atribuídos ao projeto; só contados."""
    dias = {v.data for v in votacoes}
    if not dias:
        return 0
    return len(
        session.scalars(
            select(Discurso.id).where(
                Discurso.casa == casa,
                Discurso.data.in_(dias),
                Discurso.proposicao_id_externo.is_(None),
            )
        ).all()
    )

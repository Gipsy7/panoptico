"""Calendário das votações nominais do Plenário (GET /votacoes/calendario): quantas votações houve
em cada dia de um mês, numa Casa, e a lista das votações do mês ou de um dia, com o recorte por
tipo (app/services/tipo_votacao.py). Só conta o que está em `votacao`: dia sem número pode ter
tido sessão sem votação nominal, votação simbólica ou reunião de comissão.
"""

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Votacao, Voto
from app.services.presenca import FONTES
from app.services.tipo_votacao import MERITO, PROCEDIMENTO
from app.services.votos import filtro_tipo

POR_PAGINA = 20
CASAS = ("camara", "senado")


def _mes_mais_recente(session: Session, casa: str) -> date | None:
    return session.scalar(select(func.max(Votacao.data)).where(Votacao.casa == casa))


def _vizinho(session: Session, casa: str, antes: date | None, depois: date | None) -> dict | None:
    """Mês com votação mais próximo antes de `antes` ou depois de `depois`."""
    if antes is not None:
        d = session.scalar(
            select(func.max(Votacao.data)).where(Votacao.casa == casa, Votacao.data < antes)
        )
    else:
        d = session.scalar(
            select(func.min(Votacao.data)).where(Votacao.casa == casa, Votacao.data > depois)
        )
    return {"ano": d.year, "mes": d.month} if d else None


def _placares(session: Session, ids: list[int]) -> dict[int, Counter]:
    resultado: dict[int, Counter] = defaultdict(Counter)
    if not ids:
        return resultado
    for votacao_id, voto, n in session.execute(
        select(Voto.votacao_id, Voto.voto, func.count())
        .where(Voto.votacao_id.in_(ids), Voto.voto.in_(("Sim", "Não", "Abstenção")))
        .group_by(Voto.votacao_id, Voto.voto)
    ):
        resultado[votacao_id][voto] = n
    return resultado


def calendario(
    session: Session,
    casa: str,
    ano: int | None,
    mes: int | None,
    dia: date | None,
    tipo: str | None,
    pagina: int,
) -> dict | None:
    """Dias do mês com o número de votações (todas, sobre o texto, de procedimento) e a lista
    do mês, ou do `dia`, no recorte `tipo`. Sem `ano`/`mes`, o mês mais recente com votação na
    Casa. None quando a Casa não tem votação carregada."""
    if ano is None or mes is None:
        recente = _mes_mais_recente(session, casa)
        if recente is None:
            return None
        ano, mes = recente.year, recente.month
    inicio, fim = date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1])

    tipo_col = func.coalesce(Votacao.tipo_votacao, PROCEDIMENTO)
    por_dia: dict[date, dict[str, int]] = {}
    for d, t, n in session.execute(
        select(Votacao.data, tipo_col, func.count())
        .where(Votacao.casa == casa, Votacao.data.between(inicio, fim))
        .group_by(Votacao.data, tipo_col)
    ):
        contagem = por_dia.setdefault(d, {"todas": 0, MERITO: 0, PROCEDIMENTO: 0})
        contagem[t] += n
        contagem["todas"] += n
    totais = {"todas": 0, MERITO: 0, PROCEDIMENTO: 0}
    for contagem in por_dia.values():
        for chave in totais:
            totais[chave] += contagem[chave]

    por_casa = dict(
        session.execute(
            select(Votacao.casa, func.count())
            .where(Votacao.data.between(inicio, fim))
            .group_by(Votacao.casa)
        ).all()
    )

    # Lista: o dia escolhido (se for do mês) ou o mês inteiro.
    if dia is not None and not inicio <= dia <= fim:
        dia = None
    de, ate = (dia, dia) if dia else (inicio, fim)
    filtro = [Votacao.casa == casa, Votacao.data.between(de, ate), *filtro_tipo(tipo)]
    contagem_lista = (
        por_dia.get(dia, {"todas": 0, MERITO: 0, PROCEDIMENTO: 0}) if dia else dict(totais)
    )
    total = session.scalar(select(func.count()).select_from(Votacao).where(*filtro)) or 0
    votacoes = session.scalars(
        select(Votacao)
        .where(*filtro)
        .order_by(Votacao.data.desc(), Votacao.id.desc())
        .limit(POR_PAGINA)
        .offset((pagina - 1) * POR_PAGINA)
    ).all()
    contados = _placares(session, [v.id for v in votacoes if v.placar_sim is None])

    def placar(v: Votacao) -> dict:
        if v.placar_sim is not None or v.placar_nao is not None:
            return {"sim": v.placar_sim, "nao": v.placar_nao, "abstencao": v.placar_abstencao}
        c = contados.get(v.id, Counter())
        return {"sim": c["Sim"], "nao": c["Não"], "abstencao": c["Abstenção"]}

    fonte = FONTES[casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )
    return {
        "casa": casa,
        "ano": ano,
        "mes": mes,
        "mes_anterior": _vizinho(session, casa, antes=inicio, depois=None),
        "mes_seguinte": _vizinho(session, casa, antes=None, depois=fim),
        "dias": [{"data": d, **contagem} for d, contagem in sorted(por_dia.items())],
        "totais": totais,
        "por_casa": {c: por_casa.get(c, 0) for c in CASAS},
        "dia": dia,
        "tipo": tipo or "todas",
        "lista": {
            "total": total,
            "contagem_tipos": contagem_lista,
            "pagina": pagina,
            "por_pagina": POR_PAGINA,
            "itens": [
                {
                    "id_externo": v.id_externo,
                    "data": v.data,
                    "descricao": v.descricao,
                    "tipo": v.tipo_votacao or PROCEDIMENTO,
                    "proposicao": v.proposicao,
                    "proposicao_id_externo": v.proposicao_id_externo,
                    "proposicao_ementa": v.proposicao_ementa,
                    "resultado": v.resultado,
                    "secreta": v.secreta,
                    "placar": placar(v),
                    "link": f"/votacao/{casa}/{v.id_externo}",
                }
                for v in votacoes
            ],
        },
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }

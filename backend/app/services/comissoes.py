"""Votos do parlamentar nas votações nominais das comissões.

Só a lista, sem percentuais: presença e alinhamento contam o Plenário, onde todos votam a
mesma pauta. Nas comissões, cada parlamentar participa só das que integra.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Parlamentar, VotacaoComissao, VotoComissao
from app.services.votos import url_votacao

POR_PAGINA = 20
FONTES = {
    "camara": (
        "Votações nominais das comissões (Dados Abertos da Câmara)",
        "https://dadosabertos.camara.leg.br/",
    ),
    "senado": (
        "Votações das comissões (Dados Abertos do Senado)",
        "https://legis.senado.leg.br/dadosabertos/",
    ),
}


def lista(session: Session, parlamentar: Parlamentar, pagina: int = 1) -> dict:
    dele = VotoComissao.parlamentar_id == parlamentar.id
    total = session.scalar(select(func.count()).select_from(VotoComissao).where(dele)) or 0
    linhas = session.execute(
        select(VotacaoComissao, VotoComissao.voto)
        .join(VotoComissao, VotoComissao.votacao_id == VotacaoComissao.id)
        .where(dele)
        .order_by(VotacaoComissao.data.desc(), VotacaoComissao.id.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    ).all()
    comissoes = session.execute(
        select(VotacaoComissao.orgao_sigla, func.min(VotacaoComissao.orgao_nome), func.count())
        .join(VotoComissao, VotoComissao.votacao_id == VotacaoComissao.id)
        .where(dele)
        .group_by(VotacaoComissao.orgao_sigla)
        .order_by(func.count().desc())
    ).all()
    fonte = "camara_votacoes" if parlamentar.casa == "camara" else "senado_votacoes_comissoes"
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )
    nome, url = FONTES[parlamentar.casa]
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "comissoes": [{"sigla": s, "nome": n, "votacoes": c} for s, n, c in comissoes],
        "itens": [
            {
                "data": v.data,
                "orgao_sigla": v.orgao_sigla,
                "orgao_nome": v.orgao_nome,
                "descricao": v.descricao,
                "proposicao": v.proposicao,
                "proposicao_ementa": v.proposicao_ementa,
                "voto": voto,
                "url": url_votacao(v),
            }
            for v, voto in linhas
        ],
        "fonte_nome": nome,
        "fonte_url": url,
        "atualizado_em": atualizado_em,
    }

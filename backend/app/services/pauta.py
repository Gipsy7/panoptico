"""Pauta do Plenário (GET /pauta): itens de `pauta_item` nos próximos dias, por data.

A janela é a que a ingestão guarda (hoje a +14 dias). Quando o projeto existe aqui (tabela de
proposições ou de votações), o item traz o link interno. Pauta vazia é um fato legítimo
(recesso e período eleitoral): a resposta diz isso, sem inventar itens."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PautaItem, Proposicao, Votacao
from app.services import projeto_fontes


def pauta(session: Session, casa: str | None, dias: int, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    consulta = select(PautaItem).where(
        PautaItem.data >= hoje, PautaItem.data <= hoje + timedelta(days=dias)
    )
    if casa:
        consulta = consulta.where(PautaItem.casa == casa)
    itens = session.scalars(
        consulta.order_by(PautaItem.data, PautaItem.casa, PautaItem.sessao, PautaItem.ordem)
    ).all()

    chaves = {(i.casa, i.proposicao_id_externo) for i in itens if i.proposicao_id_externo}
    existentes: set[tuple[str, str]] = set()
    if chaves:
        ids = {pid for _, pid in chaves}
        existentes |= {
            tuple(r)
            for r in session.execute(
                select(Proposicao.casa, Proposicao.id_externo).where(Proposicao.id_externo.in_(ids))
            )
        }
        existentes |= {
            tuple(r)
            for r in session.execute(
                select(Votacao.casa, Votacao.proposicao_id_externo)
                .where(Votacao.proposicao_id_externo.in_(ids))
                .distinct()
            )
        }

    if casa:
        fonte = projeto_fontes.fonte_do_bloco(session, "pauta", casa)
    else:
        fonte = {
            "fonte_nome": "Pauta e agenda do Plenário (Câmara dos Deputados e Senado Federal)",
            "fonte_url": "https://dadosabertos.camara.leg.br/",
            "atualizado_em": projeto_fontes.atualizado_em(
                session, ["camara_pauta", "senado_pauta"]
            ),
        }
    return {
        "casa": casa,
        "dias": dias,
        "itens": [
            {
                "casa": i.casa,
                "data": i.data,
                "sessao": i.sessao,
                "ordem": i.ordem,
                "proposicao": i.proposicao,
                "proposicao_id_externo": i.proposicao_id_externo,
                "ementa": i.ementa,
                "url_oficial": i.url,
                "link": f"/projeto/{i.casa}/{i.proposicao_id_externo}"
                if (i.casa, i.proposicao_id_externo) in existentes
                else None,
            }
            for i in itens
        ],
        "aviso": None
        if itens
        else (
            f"Não há itens de pauta publicados para os próximos {dias} dias. Em recesso e em "
            "período eleitoral o Plenário pode não ter sessões marcadas."
        ),
        **fonte,
    }

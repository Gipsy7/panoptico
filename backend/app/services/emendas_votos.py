"""Emendas e votos na mesma cidade: os deputados federais em exercício mais votados no município
e quanto cada um enviou a ele em emendas individuais pagas (docs/DECISOES.md, 2026-11-14).

Dois números lado a lado, da mesma cidade: votos (TSE) e emendas pagas (Portal da Transparência).
A rota não diz que um explica o outro. Quem não enviou nada entra com zero.

A ligação entre o candidato e o parlamentar é a do cadastro (`candidatura.parlamentar_id`), nunca
o nome. Só entra quem está em exercício: quem se elegeu e saiu do cargo fica de fora, e a
resposta diz quantos dos mais votados ficaram fora por isso.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    EmendaPagamento,
    Municipio,
    Parlamentar,
    ResultadoCandidato,
)
from app.services import emendas, resultados_eleicao

CARGO = "DEPUTADO FEDERAL"
LIMITE = 5


def ano_da_legislatura(session: Session, ibge: str, hoje: date) -> int | None:
    """A eleição mais recente cujos eleitos já tomaram posse (1º de fevereiro do ano seguinte)."""
    anos = session.scalars(
        select(func.distinct(ResultadoCandidato.ano)).where(
            ResultadoCandidato.cargo == CARGO,
            ResultadoCandidato.abrangencia == "municipio",
            ResultadoCandidato.municipio_ibge == ibge,
        )
    ).all()
    empossados = [a for a in anos if date(a + 1, 2, 1) <= hoje]
    return max(empossados) if empossados else None


def do_municipio(
    session: Session, ibge: str, hoje: date | None = None, limite: int = LIMITE
) -> dict | None:
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        return None
    ano = ano_da_legislatura(session, ibge, hoje or date.today())
    if ano is None:
        return None

    # Todos os candidatos a deputado federal na cidade, na ordem dos votos: a posição é a geral.
    linhas = session.execute(
        select(ResultadoCandidato, Parlamentar)
        .outerjoin(
            Candidatura,
            (Candidatura.ano_eleicao == ResultadoCandidato.ano)
            & (Candidatura.sq_candidato == ResultadoCandidato.sq_candidato),
        )
        .outerjoin(
            Parlamentar,
            (Parlamentar.id == Candidatura.parlamentar_id)
            & Parlamentar.em_exercicio.is_(True)
            & (Parlamentar.casa == "camara"),
        )
        .where(
            ResultadoCandidato.ano == ano,
            ResultadoCandidato.cargo == CARGO,
            ResultadoCandidato.abrangencia == "municipio",
            ResultadoCandidato.municipio_ibge == ibge,
        )
        .order_by(ResultadoCandidato.votos.desc(), ResultadoCandidato.nome_urna)
    ).all()
    if not linhas:
        return None

    pagas: dict[int, Decimal] = dict(
        session.execute(
            select(EmendaPagamento.parlamentar_id, func.sum(EmendaPagamento.valor))
            .where(
                EmendaPagamento.municipio_ibge == ibge,
                EmendaPagamento.parlamentar_id.is_not(None),
                emendas._individual(),
            )
            .group_by(EmendaPagamento.parlamentar_id)
        ).all()
    )
    total_cidade = session.scalar(
        select(func.coalesce(func.sum(EmendaPagamento.valor), 0)).where(
            EmendaPagamento.municipio_ibge == ibge, emendas._individual()
        )
    )
    periodo = session.execute(
        select(func.min(EmendaPagamento.ano_emenda), func.max(EmendaPagamento.ano_emenda)).where(
            emendas._individual()
        )
    ).one()

    itens: list[dict] = []
    fora = 0  # mais votados que ficaram fora da lista por não estarem em exercício
    for posicao, (r, p) in enumerate(linhas, start=1):
        if len(itens) >= limite:
            break
        if p is None:
            fora += 1
            continue
        itens.append(
            {
                "posicao": posicao,
                "parlamentar_id": p.id,
                "nome": p.nome_parlamentar,
                "partido": p.partido,
                "uf": p.uf,
                "votos": r.votos,
                "emendas_pagas": float(pagas.get(p.id, Decimal(0))),
            }
        )
    if not itens:
        return None
    soma = sum(i["emendas_pagas"] for i in itens)
    return {
        "municipio": {"ibge": municipio.ibge, "nome": municipio.nome, "uf": municipio.uf},
        "ano_eleicao": ano,
        "itens": itens,
        "fora_por_nao_estar_em_exercicio": fora,
        "emendas_dos_listados": round(soma, 2),
        "emendas_individuais_da_cidade": float(total_cidade or 0),
        "emendas_de": periodo[0],
        "emendas_ate": periodo[1],
        "recorte": (
            "Deputados federais em exercício, na ordem dos votos que tiveram na cidade. "
            "Candidatos mais votados que não estão no cargo hoje ficam de fora. Emendas "
            "individuais pagas à prefeitura, a fundos municipais e a entidades da cidade; "
            "emendas de bancada, de comissão e de relator não têm um autor só e não entram. "
            "Quem não enviou nada aparece com zero."
        ),
        "votos_fonte_nome": resultados_eleicao._fonte(session)["fonte_nome"],
        "emendas_fonte_nome": emendas.FONTE_NOME,
        "emendas_fonte_url": emendas.FONTE_URL,
        "atualizado_em": emendas._atualizado(session, "transparencia_emendas"),
    }

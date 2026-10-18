"""Emendas individuais recebidas por um município."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ContasMunicipio,
    Emenda,
    EmendaPagamento,
    FonteIngestao,
    Municipio,
    Parlamentar,
)
from app.textos import sem_cpf
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE_NOME = "Emendas parlamentares por favorecido (Portal da Transparência, CGU)"
FONTE_URL = "https://portaldatransparencia.gov.br/emendas"


SEM_AREA = "Área não informada"
VARIAS_AREAS = "Mais de uma área"


def _areas(session: Session, pagamentos: list[EmendaPagamento]) -> list[dict]:
    """Soma o pago por área (função orçamentária da emenda).

    O pagamento não traz a área; ela vem da emenda. Um mesmo código de emenda pode ter
    linhas com áreas diferentes (uma por localidade), então vale a área da linha do próprio
    município; sem ela, a área única do código; e, se ainda houver mais de uma, o valor fica
    em "Mais de uma área" em vez de ser atribuído a uma delas por palpite.
    """
    codigos = {p.emenda_codigo for p in pagamentos}
    linhas = session.execute(
        select(Emenda.codigo, Emenda.municipio_ibge, Emenda.funcao).where(
            Emenda.codigo.in_(codigos)
        )
    ).all()
    por_codigo: dict[str, set[str]] = {}
    por_codigo_e_municipio: dict[tuple[str, str | None], set[str]] = {}
    for codigo, ibge, funcao in linhas:
        area = funcao or SEM_AREA
        por_codigo.setdefault(codigo, set()).add(area)
        por_codigo_e_municipio.setdefault((codigo, ibge), set()).add(area)

    somas: dict[str, Decimal] = {}
    for p in pagamentos:
        candidatas = por_codigo_e_municipio.get(
            (p.emenda_codigo, p.municipio_ibge)
        ) or por_codigo.get(p.emenda_codigo, {SEM_AREA})
        area = next(iter(candidatas)) if len(candidatas) == 1 else VARIAS_AREAS
        somas[area] = somas.get(area, Decimal(0)) + p.valor
    total = sum(somas.values(), start=Decimal(0))
    return [
        {"area": area, "total": valor, "percentual": round(100 * valor / total, 1) if total else 0}
        for area, valor in sorted(somas.items(), key=lambda item: item[1], reverse=True)
    ]


def _favorecidos(pagamentos: list[EmendaPagamento], limite: int) -> tuple[list[dict], int]:
    """Quem recebeu (prefeitura, fundos, entidades), do maior para o menor, com quem enviou."""
    grupos: dict[str, dict] = {}
    for p in pagamentos:
        g = grupos.setdefault(
            p.favorecido_codigo,
            {
                "nome": sem_cpf(p.favorecido),
                "cnpj": p.favorecido_codigo,
                "grupo": p.grupo,
                "total": Decimal(0),
                "autores": {},
            },
        )
        g["total"] += p.valor
        autor = g["autores"].setdefault(
            p.autor_nome, {"autor_nome": p.autor_nome, "parlamentar_id": None}
        )
        if p.parlamentar_id:
            autor["parlamentar_id"] = p.parlamentar_id
    ordenados = sorted(grupos.values(), key=lambda g: g["total"], reverse=True)
    for g in ordenados:
        g["autores"] = sorted(g["autores"].values(), key=lambda a: a["autor_nome"])
    return ordenados[:limite], len(ordenados)


MEDIA_UF_DESCRICAO = (
    "Média simples, entre os municípios do estado com população conhecida, das emendas "
    "recebidas desde {desde} divididas pela população; quem não recebeu entra com zero. "
    "Ficam de fora os municípios sem população nas contas do Tesouro."
)


def _populacao_e_media_uf(
    session: Session, municipio: Municipio
) -> tuple[int | None, float | None, int]:
    """População do município e média por habitante dos municípios da UF, em uma consulta."""
    ultimo = (
        select(
            ContasMunicipio.municipio_ibge.label("ibge"),
            func.max(ContasMunicipio.ano).label("ano"),
        )
        .where(ContasMunicipio.populacao > 0)
        .group_by(ContasMunicipio.municipio_ibge)
        .subquery()
    )
    pago = (
        select(
            EmendaPagamento.municipio_ibge.label("ibge"),
            func.sum(EmendaPagamento.valor).label("total"),
        )
        .group_by(EmendaPagamento.municipio_ibge)
        .subquery()
    )
    razao = func.coalesce(pago.c.total, 0) / ContasMunicipio.populacao
    media, n = session.execute(
        select(func.avg(razao), func.count())
        .select_from(Municipio)
        .join(ultimo, ultimo.c.ibge == Municipio.ibge)
        .join(
            ContasMunicipio,
            (ContasMunicipio.municipio_ibge == ultimo.c.ibge)
            & (ContasMunicipio.ano == ultimo.c.ano),
        )
        .outerjoin(pago, pago.c.ibge == Municipio.ibge)
        .where(Municipio.uf == municipio.uf)
    ).one()
    populacao = session.scalar(
        select(ContasMunicipio.populacao)
        .where(ContasMunicipio.municipio_ibge == municipio.ibge, ContasMunicipio.populacao > 0)
        .order_by(ContasMunicipio.ano.desc())
        .limit(1)
    )
    return populacao, (round(float(media), 2) if media is not None else None), n


def resumo_municipio(
    session: Session, municipio: Municipio, limite_outros: int = 10, limite_favorecidos: int = 15
) -> dict:
    do_municipio = EmendaPagamento.municipio_ibge == municipio.ibge

    por_grupo = dict(
        session.execute(
            select(EmendaPagamento.grupo, func.sum(EmendaPagamento.valor))
            .where(do_municipio)
            .group_by(EmendaPagamento.grupo)
        ).all()
    )
    por_ano = session.execute(
        select(EmendaPagamento.ano_emenda, func.sum(EmendaPagamento.valor))
        .where(do_municipio)
        .group_by(EmendaPagamento.ano_emenda)
        .order_by(EmendaPagamento.ano_emenda)
    ).all()

    total = func.sum(EmendaPagamento.valor).label("total")
    # Parlamentares em exercício (com vínculo): todos, para marcar os cards.
    com_vinculo = session.execute(
        select(Parlamentar, total)
        .join(EmendaPagamento, EmendaPagamento.parlamentar_id == Parlamentar.id)
        .where(do_municipio)
        .group_by(Parlamentar.id)
        .order_by(total.desc())
    ).all()
    # Autores sem vínculo (ex-parlamentares ou nome não identificado): os maiores.
    sem_vinculo = session.execute(
        select(EmendaPagamento.autor_nome, total)
        .where(do_municipio, EmendaPagamento.parlamentar_id.is_(None))
        .group_by(EmendaPagamento.autor_nome)
        .order_by(total.desc())
        .limit(limite_outros)
    ).all()
    n_autores = session.scalar(
        select(func.count(func.distinct(EmendaPagamento.autor_codigo))).where(do_municipio)
    )

    pagamentos = session.scalars(select(EmendaPagamento).where(do_municipio)).all()
    favorecidos, numero_favorecidos = _favorecidos(pagamentos, limite_favorecidos)

    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "transparencia_emendas", FonteIngestao.status == "ok"
        )
    )
    total_geral = sum(por_grupo.values(), start=0)
    populacao, media_uf, n_media = _populacao_e_media_uf(session, municipio)
    return {
        "municipio": {"ibge": municipio.ibge, "nome": municipio.nome, "uf": municipio.uf},
        "desde": INICIO_LEGISLATURA.year,
        "total": total_geral,
        "populacao": populacao,
        "por_habitante": round(float(total_geral) / populacao, 2) if populacao else None,
        "media_uf_por_habitante": media_uf,
        "municipios_na_media": n_media,
        "media_uf_descricao": MEDIA_UF_DESCRICAO.format(desde=INICIO_LEGISLATURA.year),
        "total_prefeitura": por_grupo.get("prefeitura", 0),
        "total_entidades": por_grupo.get("entidade", 0),
        "por_ano": [{"ano": a, "total": t} for a, t in por_ano],
        "parlamentares": [
            {"parlamentar": p, "total": t, "do_estado": p.uf == municipio.uf}
            for p, t in com_vinculo
        ],
        "outros_autores": [{"autor_nome": n, "total": t} for n, t in sem_vinculo],
        "numero_autores": n_autores or 0,
        "por_area": _areas(session, pagamentos) if pagamentos else [],
        "favorecidos": favorecidos,
        "numero_favorecidos": numero_favorecidos,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }

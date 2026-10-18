"""Contas anuais do município (SICONFI): quanto arrecadou e em que áreas gastou."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContasMunicipio, FonteIngestao, Municipio

FONTE_NOME = "Declaração de Contas Anuais (SICONFI, Tesouro Nacional)"
FONTE_URL = "https://siconfi.tesouro.gov.br/"
AREAS_MOSTRADAS = 8


MEDIA_UF_DESCRICAO = (
    "Média simples, entre os municípios do estado que entregaram as contas do mesmo ano, "
    "da despesa paga dividida pela população de cada um. Ficam de fora os municípios sem "
    "população ou sem despesa informada."
)


def _media_uf(session: Session, ibge: str, ano: int) -> tuple[float | None, int]:
    razao = ContasMunicipio.despesa_paga / ContasMunicipio.populacao
    media, n = session.execute(
        select(func.avg(razao), func.count())
        .select_from(ContasMunicipio)
        .join(Municipio, Municipio.ibge == ContasMunicipio.municipio_ibge)
        .where(
            Municipio.uf == select(Municipio.uf).where(Municipio.ibge == ibge).scalar_subquery(),
            ContasMunicipio.ano == ano,
            ContasMunicipio.populacao > 0,
            ContasMunicipio.despesa_paga.is_not(None),
        )
    ).one()
    return (round(float(media), 2) if media is not None else None), n


def resumo(session: Session, ibge: str) -> dict | None:
    anos = session.scalars(
        select(ContasMunicipio)
        .where(ContasMunicipio.municipio_ibge == ibge)
        .order_by(ContasMunicipio.ano.desc())
    ).all()
    if not anos:
        return None
    atual, anterior = anos[0], anos[1] if len(anos) > 1 else None
    # Nulo é "a fonte não informou", nunca zero: sem despesa não há valor por habitante.
    informada = atual.despesa_paga is not None
    total = float(atual.despesa_paga) if informada else 0.0
    areas = sorted(atual.despesa_por_area.items(), key=lambda item: item[1], reverse=True)
    principais = areas[:AREAS_MOSTRADAS]
    resto = sum(v for _, v in areas[AREAS_MOSTRADAS:])
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "siconfi_contas", FonteIngestao.status == "ok"
        )
    )
    media_uf, n_media = _media_uf(session, ibge, atual.ano)
    return {
        "ano": atual.ano,
        "populacao": atual.populacao,
        "receita_total": atual.receita_total,
        "despesa_paga": atual.despesa_paga,
        "despesa_por_habitante": round(total / atual.populacao, 2)
        if informada and atual.populacao
        else None,
        "media_uf_despesa_por_habitante": media_uf,
        "municipios_na_media": n_media,
        "media_uf_descricao": MEDIA_UF_DESCRICAO,
        "camara": atual.despesa_por_area.get("Legislativa"),
        "por_area": [
            {
                "nome": nome,
                "valor": valor,
                "percentual": round(100 * valor / total, 1) if total else 0,
            }
            for nome, valor in principais
        ]
        + (
            [{"nome": "Outras áreas", "valor": resto, "percentual": round(100 * resto / total, 1)}]
            if resto and total
            else []
        ),
        "anterior": {
            "ano": anterior.ano,
            "despesa_paga": anterior.despesa_paga,
            "receita_total": anterior.receita_total,
        }
        if anterior
        else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }

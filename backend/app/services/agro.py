"""Lavouras de um município (IBGE, Produção Agrícola Municipal): o valor da produção no último
ano publicado e os produtos que mais pesam, cada um com a parte do total da cidade. Ao lado, o
total do estado, para dar o tamanho."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgroLavoura, AgroPecuaria, FonteIngestao
from app.services.pib import CODIGO_UF

FONTE = "ibge_pam"
FONTE_NOME = "IBGE (Produção Agrícola Municipal, tabela 5457 do SIDRA)"
FONTE_URL = "https://sidra.ibge.gov.br/tabela/5457"
PRODUTOS = 8


def atualizado_em(session: Session, fonte: str = FONTE) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )


def _pecuaria(session: Session, ibge: str) -> dict | None:
    """Rebanhos (cabeças) e produção de origem animal (reais) da PPM."""
    linhas = session.scalars(select(AgroPecuaria).where(AgroPecuaria.codigo == ibge)).all()
    if not linhas:
        return None
    produtos = [r for r in linhas if r.categoria == "produto"]
    total = next((r for r in produtos if r.item == "Total"), None)
    return {
        "ano": linhas[0].ano,
        "rebanhos": [
            {"item": r.item.replace(" - total", ""), "cabecas": int(r.valor)}
            for r in sorted((r for r in linhas if r.categoria == "rebanho"), key=lambda r: -r.valor)
        ],
        "valor_origem_animal": float(total.valor) * 1000 if total else None,
        "produtos": [
            {
                "produto": r.item,
                "valor": float(r.valor) * 1000,
                "percentual": float(100 * r.valor / total.valor) if total else None,
            }
            for r in sorted((r for r in produtos if r.item != "Total"), key=lambda r: -r.valor)
        ],
        "fonte_nome": "IBGE (Pesquisa da Pecuária Municipal, tabelas 3939 e 74 do SIDRA)",
        "fonte_url": "https://sidra.ibge.gov.br/pesquisa/ppm/tabelas",
        "atualizado_em": atualizado_em(session, "ibge_ppm"),
    }


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    linhas = session.scalars(select(AgroLavoura).where(AgroLavoura.codigo == ibge)).all()
    total = next((r for r in linhas if r.produto == "Total"), None)
    uf_total = session.scalar(
        select(AgroLavoura.valor).where(
            AgroLavoura.codigo == CODIGO_UF.get(uf, ""), AgroLavoura.produto == "Total"
        )
    )
    produtos = sorted((r for r in linhas if r.produto != "Total"), key=lambda r: -r.valor)
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "ano": total.ano if total else None,
        "valor_total": float(total.valor) * 1000 if total else None,
        "uf_valor_total": float(uf_total) * 1000 if uf_total else None,
        "produtos": [
            {
                "produto": r.produto,
                "valor": float(r.valor) * 1000,
                "percentual": float(100 * r.valor / total.valor) if total else None,
            }
            for r in produtos[:PRODUTOS]
        ],
        "outros_produtos": max(len(produtos) - PRODUTOS, 0),
        "pecuaria": _pecuaria(session, ibge),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }

"""Para quem a prefeitura e a câmara pagaram (dados abertos dos Tribunais de Contas)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DespesaFornecedor, FonteIngestao

FONTES = {
    "tce_sp": (
        "Despesas municipais (Tribunal de Contas do Estado de São Paulo)",
        "https://transparencia.tce.sp.gov.br/conjunto-de-dados",
    ),
}
ORGAOS = ("prefeitura", "camara", "outros")


def resumo(session: Session, ibge: str) -> dict | None:
    ano = session.scalar(
        select(func.max(DespesaFornecedor.ano)).where(DespesaFornecedor.municipio_ibge == ibge)
    )
    if ano is None:
        return None
    linhas = session.scalars(
        select(DespesaFornecedor)
        .where(DespesaFornecedor.municipio_ibge == ibge, DespesaFornecedor.ano == ano)
        .order_by(DespesaFornecedor.valor_pago.desc())
    ).all()
    fonte = linhas[0].fonte
    orgaos = []
    for orgao in ORGAOS:
        do_orgao = [x for x in linhas if x.orgao == orgao]
        if not do_orgao:
            continue
        orgaos.append(
            {
                "orgao": orgao,
                "total_pago": sum(x.valor_pago for x in do_orgao),
                "itens": [
                    {
                        "fornecedor": x.fornecedor,
                        "documento": x.documento,
                        "valor_pago": x.valor_pago,
                        "pagamentos": x.pagamentos,
                    }
                    for x in do_orgao
                ],
            }
        )
    nome, url = FONTES.get(fonte, (fonte, ""))
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )
    return {
        "ano": ano,
        "orgaos": orgaos,
        "fonte_nome": nome,
        "fonte_url": url,
        "atualizado_em": atualizado_em,
    }

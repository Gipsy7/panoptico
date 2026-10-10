"""Contratos públicos (PNCP): das empresas de que uma pessoa é sócia e dos maiores fornecedores
de um município.

Ser sócio de empresa que contrata com o poder público não é irregularidade: o dado só mostra
que o contrato existe, com o link da fonte. Os contratos inteiros vêm de `pncp_contrato`
(fornecedores do conjunto-alvo); a soma por município, de `pncp_anual`.
"""

import re
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Pessoa, PncpAnual, PncpContrato, PncpDia, SocioPessoa

FONTE_NOME = "Portal Nacional de Contratações Públicas (PNCP)"
FONTE_URL = "https://pncp.gov.br/app/contratos"
LIMITE_CONTRATOS = 50
MAIORES_NO_SITE = 10

# numeroControlePNCP: CNPJ do órgão - 2 (contrato) - sequencial / ano
CONTROLE = re.compile(r"^(\d{14})-\d+-(\d+)/(\d{4})$")


def link_pncp(numero_controle: str) -> str | None:
    """Página do contrato no portal do PNCP, ou None se o número não tem o formato esperado."""
    m = CONTROLE.match(numero_controle or "")
    if not m:
        return None
    cnpj, sequencial, ano = m.groups()
    return f"https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{int(sequencial)}"


def _atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "pncp_contratos", FonteIngestao.status == "ok"
        )
    )


def da_pessoa(session: Session, pessoa_id: int) -> dict | None:
    """Empresas de que a pessoa é sócia e os contratos delas no PNCP (alienações fora),
    do mais recente para o mais antigo. None se a pessoa não existe."""
    if session.get(Pessoa, pessoa_id) is None:
        return None
    socios = session.scalars(select(SocioPessoa).where(SocioPessoa.pessoa_id == pessoa_id)).all()
    cnpjs = {s.cnpj for s in socios}
    vazio = {
        "pessoa_id": pessoa_id,
        "empresas": [],
        "total_contratos": 0,
        "valor_total": Decimal(0),
        "itens": [],
        "cobertura_desde": None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": None,
    }
    if not cnpjs:
        return vazio
    contratos = (
        PncpContrato.fornecedor_cnpj.in_(cnpjs),
        PncpContrato.receita.is_(False),
    )
    total, valor = session.execute(
        select(func.count(), func.coalesce(func.sum(PncpContrato.valor_global), 0)).where(
            *contratos
        )
    ).one()
    if total == 0:
        return vazio
    por_empresa = {
        cnpj: (n, nome)
        for cnpj, n, nome in session.execute(
            select(
                PncpContrato.fornecedor_cnpj, func.count(), func.max(PncpContrato.fornecedor_nome)
            )
            .where(*contratos)
            .group_by(PncpContrato.fornecedor_cnpj)
        )
    }
    empresas = [
        {
            "cnpj": s.cnpj,
            "nome": por_empresa[s.cnpj][1],
            "qualificacao": s.qualificacao,
            "contratos": por_empresa[s.cnpj][0],
        }
        for s in sorted(socios, key=lambda s: -por_empresa.get(s.cnpj, (0, None))[0])
        if s.cnpj in por_empresa
    ]
    linhas = session.scalars(
        select(PncpContrato)
        .where(*contratos)
        .order_by(PncpContrato.publicado_em.desc(), PncpContrato.numero_controle)
        .limit(LIMITE_CONTRATOS)
    ).all()
    itens = [
        {
            "fornecedor_cnpj": c.fornecedor_cnpj,
            "fornecedor_nome": c.fornecedor_nome,
            "orgao": c.orgao_nome,
            "municipio": c.municipio_nome,
            "uf": c.uf,
            "objeto": c.objeto,
            "valor": c.valor_global,
            "vigencia_inicio": c.vigencia_inicio,
            "vigencia_fim": c.vigencia_fim,
            "publicado_em": c.publicado_em,
            "url": link_pncp(c.numero_controle) or FONTE_URL,
        }
        for c in linhas
    ]
    return {
        **vazio,
        "empresas": empresas,
        "total_contratos": total,
        "valor_total": valor,
        "itens": itens,
        "cobertura_desde": session.scalar(select(func.min(PncpDia.dia))),
        "atualizado_em": _atualizado_em(session),
    }


def maiores_do_municipio(session: Session, ibge: str) -> dict | None:
    """Maiores fornecedores dos órgãos municipais no PNCP, no ano mais recente com dados.
    None se o município não tem soma anual."""
    ano = session.scalar(select(func.max(PncpAnual.ano)).where(PncpAnual.municipio_ibge == ibge))
    if ano is None:
        return None
    linhas = session.scalars(
        select(PncpAnual)
        .where(PncpAnual.municipio_ibge == ibge, PncpAnual.ano == ano)
        .order_by(PncpAnual.valor_global.desc(), PncpAnual.fornecedor_cnpj)
        .limit(MAIORES_NO_SITE)
    ).all()
    ate: date | None = session.scalar(
        select(func.max(PncpDia.dia)).where(PncpDia.compactado.is_(True))
    )
    return {
        "ano": ano,
        "itens": [
            {
                "fornecedor_cnpj": x.fornecedor_cnpj,
                "fornecedor": x.fornecedor_nome,
                "valor": x.valor_global,
                "contratos": x.quantidade,
            }
            for x in linhas
        ],
        "soma_ate": ate,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }

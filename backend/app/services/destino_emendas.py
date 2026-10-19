"""O que aconteceu com o dinheiro das emendas individuais de um parlamentar: convênios
(Portal da Transparência) e transferências especiais (TransfereGov), com a situação
oficial e o andamento da prestação de contas. Só descreve a situação registrada."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.models import Emenda, EmendaTransferencia, FonteIngestao, Parlamentar
from app.services import empresas as empresas_servico
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE_NOME = "Convênios (Portal da Transparência, CGU) e transferências especiais (TransfereGov)"
FONTE_URL = "https://portaldatransparencia.gov.br/convenios/consulta"
LINK_CONVENIO = FONTE_URL
LINK_ESPECIAL = (
    "https://api.transferegov.gestao.gov.br/transferenciasespeciais/"
    "plano_acao_especial?codigo_plano_acao=eq.{codigo}"
)
LIMITE = 100


def _link(tipo: str, identificador: str) -> str:
    if tipo == "especial":
        return LINK_ESPECIAL.format(codigo=identificador)
    return LINK_CONVENIO


def _beneficiario(item: EmendaTransferencia, cadastro: dict) -> dict:
    """O nome da fonte (sem CPF) e, se faltar, a razão social do cadastro de empresas."""
    nome, omitido = empresas_servico.nome_da_empresa(
        item.beneficiario, item.beneficiario_cnpj, cadastro
    )
    return {"beneficiario": nome, "nome_omitido": omitido}


def resumo(session: Session, parlamentar: Parlamentar) -> dict | None:
    codigos = (
        select(Emenda.codigo)
        .where(
            Emenda.parlamentar_id == parlamentar.id,
            Emenda.individual,
            # A tabela tem todos os anos desde a migração 0047; a seção é da legislatura.
            Emenda.ano >= INICIO_LEGISLATURA.year,
        )
        .distinct()
    )
    base = EmendaTransferencia.emenda_codigo.in_(codigos)
    # Um mesmo convênio pode nascer de mais de uma emenda: conta uma vez só.
    unicos = (
        select(EmendaTransferencia)
        .where(base)
        .ext(distinct_on(EmendaTransferencia.tipo, EmendaTransferencia.identificador))
        .order_by(EmendaTransferencia.tipo, EmendaTransferencia.identificador)
        .subquery()
    )
    por_situacao = session.execute(
        select(
            unicos.c.tipo,
            unicos.c.situacao,
            func.count(),
            func.coalesce(func.sum(unicos.c.valor_total), 0),
        )
        .group_by(unicos.c.tipo, unicos.c.situacao)
        .order_by(unicos.c.tipo, func.count().desc())
    ).all()
    if not por_situacao:
        return None
    por_relatorio = session.execute(
        select(unicos.c.relatorio_gestao, func.count())
        .where(unicos.c.tipo == "especial")
        .group_by(unicos.c.relatorio_gestao)
        .order_by(func.count().desc())
    ).all()
    totais = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(unicos.c.valor_total), 0),
            func.coalesce(func.sum(unicos.c.valor_repassado), 0),
        )
    ).one()
    itens = session.scalars(
        select(EmendaTransferencia)
        .where(base)
        .order_by(EmendaTransferencia.valor_total.desc().nulls_last(), EmendaTransferencia.id)
        .limit(LIMITE)
    ).all()

    cadastro = empresas_servico.nomes(session, [i.beneficiario_cnpj for i in itens])

    ingestoes = session.scalars(
        select(func.max(FonteIngestao.concluido_em))
        .where(
            FonteIngestao.fonte.in_(("transferegov_convenios", "transferegov_especiais")),
            FonteIngestao.status.in_(("ok", "sem_mudanca")),
        )
        .group_by(FonteIngestao.fonte)
    ).all()
    atualizado_em: datetime | None = min(ingestoes) if ingestoes else None
    return {
        "desde": INICIO_LEGISLATURA.year,
        "quantidade": totais[0],
        "valor_total": totais[1],
        "valor_repassado": totais[2],
        "por_situacao": [
            {"tipo": t, "situacao": s, "quantidade": n, "valor_total": v}
            for t, s, n, v in por_situacao
        ],
        "relatorios_de_gestao": [{"situacao": s, "quantidade": n} for s, n in por_relatorio],
        "itens": [
            {
                "emenda_codigo": i.emenda_codigo,
                "ano_emenda": i.ano_emenda,
                "tipo": i.tipo,
                "identificador": i.identificador,
                "situacao": i.situacao,
                "relatorio_gestao": i.relatorio_gestao,
                **_beneficiario(i, cadastro),
                "beneficiario_cnpj": i.beneficiario_cnpj,
                "uf": i.uf,
                "orgao_concedente": i.orgao_concedente,
                "objeto": i.objeto,
                "valor_total": i.valor_total,
                "valor_repassado": i.valor_repassado,
                "valor_contrapartida": i.valor_contrapartida,
                "inicio_vigencia": i.inicio_vigencia,
                "fim_vigencia": i.fim_vigencia,
                "fonte_url": _link(i.tipo, i.identificador),
            }
            for i in itens
        ],
        "limite": LIMITE,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }

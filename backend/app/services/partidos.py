"""Finanças dos partidos: o que declararam ao TSE na prestação de contas anual.

Só leitura das somas (`partido_conta_soma`, `partido_cota_mensal`, `partido_fefc_fp`).
Transferências entre diretórios e repasses a candidaturas ficam separadas do gasto e da receita
própria, para o mesmo dinheiro não ser contado duas vezes. Os pagamentos ligados a pessoas ou
empresas da base (`partido_despesa_vinculada`) não são expostos aqui: dependem de revisão."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PartidoContaSoma, PartidoCotaMensal, PartidoFefcFp

FONTE_NOME = "Prestação de contas anual dos partidos (TSE, dados abertos)"
FONTE_URL = "https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-partidarias-{ano}"
FONTE_FEFC_NOME = "Distribuição do FEFC e do Fundo Partidário por gênero e raça (TSE)"
# O arquivo fefc_fp é um recurso do conjunto da prestação de contas eleitorais do ano.
FONTE_FEFC_URL = "https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-{ano}"

ZERO = Decimal(0)
RECEITAS_PROPRIAS = ("cota_tse", "recurso_candidato", "outra")


def _atualizado_em(session: Session, fonte: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )


def anos_disponiveis(session: Session, sigla: str | None = None) -> list[int]:
    consulta = select(PartidoContaSoma.ano).distinct().order_by(PartidoContaSoma.ano.desc())
    if sigla is not None:
        consulta = consulta.where(PartidoContaSoma.partido == sigla)
    return list(session.scalars(consulta))


def _soma(tipo: str, natureza: str | None = None):
    """Soma condicional do valor, para pivotar numa só consulta."""
    condicao = PartidoContaSoma.tipo == tipo
    if natureza:
        condicao = condicao & (PartidoContaSoma.natureza == natureza)
    return func.coalesce(func.sum(PartidoContaSoma.valor).filter(condicao), ZERO)


def listar(session: Session, ano: int) -> dict:
    cotas = {
        (partido, fundo): total
        for partido, fundo, total in session.execute(
            select(
                PartidoCotaMensal.partido,
                PartidoCotaMensal.fundo,
                func.sum(PartidoCotaMensal.valor),
            )
            .where(PartidoCotaMensal.ano == ano)
            .group_by(PartidoCotaMensal.partido, PartidoCotaMensal.fundo)
        )
    }
    linhas = session.execute(
        select(
            PartidoContaSoma.partido,
            _soma("receita"),
            _soma("despesa", "gasto"),
            _soma("despesa", "transferencia_candidato"),
        )
        .where(PartidoContaSoma.ano == ano)
        .group_by(PartidoContaSoma.partido)
    ).all()
    partidos = [
        {
            "sigla": sigla,
            "cota_fundo_partidario": cotas.get((sigla, "Fundo Partidário"), ZERO),
            "cota_fefc": cotas.get((sigla, "FEFC"), ZERO),
            "receita_total": receita,
            "gasto": gasto,
            "repasse_candidatos": repasse,
        }
        for sigla, receita, gasto, repasse in linhas
    ]
    partidos.sort(key=lambda p: p["sigla"])
    return {
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(session),
        "partidos": partidos,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL.format(ano=ano),
        "atualizado_em": _atualizado_em(session, "tse_contas_partidarias"),
    }


def _fefc_fp(session: Session, ano: int, sigla: str) -> dict | None:
    linhas = session.scalars(
        select(PartidoFefcFp).where(PartidoFefcFp.ano == ano, PartidoFefcFp.partido == sigla)
    ).all()
    if not linhas:
        return None

    def agrupar(fundo: str, por_cor: bool) -> list[dict]:
        soma: dict[str, list] = {}
        for linha in linhas:
            if linha.fundo != fundo or bool(linha.cor_raca) != por_cor:
                continue
            nome = linha.cor_raca if por_cor else linha.genero
            item = soma.setdefault(nome, [0, ZERO])
            item[0] += linha.candidatos
            item[1] += linha.valor_recebido
        return [
            {"nome": nome, "candidatos": c, "valor": v}
            for nome, (c, v) in sorted(soma.items(), key=lambda i: i[1][1], reverse=True)
        ]

    # `valor_partido` se repete em cada linha do FEFC: um valor por partido, não a soma.
    totais_partido = {x.valor_partido for x in linhas if x.fundo == "FEFC" and x.valor_partido}
    return {
        "ano": ano,
        "fefc_total_partido": max(totais_partido) if totais_partido else None,
        "fefc_por_genero": agrupar("FEFC", False),
        "fefc_por_cor_raca": agrupar("FEFC", True),
        "fp_por_genero": agrupar("FP", False),
        "fp_por_cor_raca": agrupar("FP", True),
        "fonte_nome": FONTE_FEFC_NOME,
        "fonte_url": FONTE_FEFC_URL.format(ano=ano),
        "atualizado_em": _atualizado_em(session, "tse_fefc_fp"),
    }


def detalhe(session: Session, sigla: str, ano: int) -> dict | None:
    """Devolve None se o partido não tem contas no ano. `sigla` já vem na grafia do banco."""
    base = (PartidoContaSoma.ano == ano, PartidoContaSoma.partido == sigla)

    def agrupar(tipo: str, coluna, naturezas: tuple[str, ...]) -> list[dict]:
        linhas = session.execute(
            select(coluna, func.sum(PartidoContaSoma.valor).label("total"))
            .where(*base, PartidoContaSoma.tipo == tipo, PartidoContaSoma.natureza.in_(naturezas))
            .group_by(coluna)
            .order_by(func.sum(PartidoContaSoma.valor).desc())
        ).all()
        return [{"nome": nome, "valor": valor} for nome, valor in linhas]

    por_natureza = dict(
        session.execute(
            select(PartidoContaSoma.natureza, func.sum(PartidoContaSoma.valor))
            .where(*base)
            .group_by(PartidoContaSoma.natureza)
        ).all()
    )
    if not por_natureza:
        return None
    receitas = agrupar("receita", PartidoContaSoma.fonte_recurso, RECEITAS_PROPRIAS)
    despesas = agrupar("despesa", PartidoContaSoma.categoria, ("gasto",))

    meses: dict = {}
    for mes, fundo, valor in session.execute(
        select(PartidoCotaMensal.mes, PartidoCotaMensal.fundo, PartidoCotaMensal.valor)
        .where(PartidoCotaMensal.ano == ano, PartidoCotaMensal.partido == sigla)
        .order_by(PartidoCotaMensal.mes)
    ):
        item = meses.setdefault(mes, {"mes": mes, "fundo_partidario": ZERO, "fefc": ZERO})
        item["fundo_partidario" if fundo == "Fundo Partidário" else "fefc"] += valor

    return {
        "sigla": sigla,
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(session, sigla),
        "cota_fundo_partidario": sum((m["fundo_partidario"] for m in meses.values()), ZERO),
        "cota_fefc": sum((m["fefc"] for m in meses.values()), ZERO),
        "cotas_mensais": list(meses.values()),
        "receita_total": sum(
            (por_natureza.get(n, ZERO) for n in (*RECEITAS_PROPRIAS, "transferencia_partidaria")),
            ZERO,
        ),
        "gasto": por_natureza.get("gasto", ZERO),
        "receitas_por_fonte": receitas,
        "despesas_por_categoria": despesas,
        "transferencias": {
            "recebidas_de_outros_diretorios": por_natureza.get("transferencia_partidaria", ZERO),
            "enviadas_a_outros_diretorios": por_natureza.get("transferencia_diretorio", ZERO),
            "repassadas_a_candidatos": por_natureza.get("transferencia_candidato", ZERO),
            "outras_enviadas": por_natureza.get("transferencia_outra", ZERO),
        },
        "fefc_fp": _fefc_fp(session, ano, sigla),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL.format(ano=ano),
        "atualizado_em": _atualizado_em(session, "tse_contas_partidarias"),
    }


def sigla_do_banco(session: Session, sigla: str) -> str | None:
    """Acha a sigla como está no banco, sem diferenciar caixa ('pl' -> 'PL')."""
    return session.scalar(
        select(PartidoContaSoma.partido)
        .where(func.upper(PartidoContaSoma.partido) == sigla.strip().upper())
        .limit(1)
    )

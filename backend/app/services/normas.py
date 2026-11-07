"""Projetos que viraram lei: leis ordinárias, leis complementares e emendas constitucionais
(tabela `norma`, carga congresso_normas) e o projeto de origem (`norma_proposicao`).

Três usos: o filtro "Virou lei" de /projetos (normas agrupadas pelo ano da lei, com a contagem
de cada ano), o "Viraram lei" do perfil (projetos da pessoa, como autor ou coautor, que viraram
norma) e o "Resultado" do Caminho do projeto. Decisões em docs/DECISOES.md, "Projetos que viraram
lei"."""

import re
from collections import defaultdict
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Autoria, Norma, NormaProposicao, Parlamentar, Proposicao
from app.services import projeto_fontes, texto_busca

FONTE = "congresso_normas"
FONTE_NOME = "Legislação federal e processos (Dados Abertos do Senado); texto em normas.leg.br"
FONTE_URL = "https://legis.senado.leg.br/dadosabertos/docs/"
POR_PAGINA = 20
# "14.133", "Lei 14.133/2021", "lei complementar nº 214, de 2025": busca pelo número da norma.
_NUMERO = re.compile(
    r"^(?:(?:lei|lc|ec|emenda)(?:\s+(?:complementar|constitucional))?\s*)?(?:n\S?\s*)?"
    r"(\d{1,3}(?:\.\d{3})+|\d{1,6})\s*(?:(?:/|,?\s*de\s+)\s*(\d{4}))?$",
    re.IGNORECASE,
)
NOME = {"LEI": "Lei", "LCP": "Lei Complementar", "EMC": "Emenda Constitucional"}
MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro",
)  # fmt: skip


def numero_formatado(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def nome_curto(n: Norma) -> str:
    """ "Lei 14.133/2021", "Lei Complementar 214/2025", "Emenda Constitucional 132/2023"."""
    return f"{NOME[n.tipo]} {numero_formatado(n.numero)}/{n.ano}"


def nome_oficial(n: Norma) -> str:
    """ "Lei nº 14.133, de 1º de abril de 2021", como a norma se apresenta."""
    dia = "1º" if n.data.day == 1 else str(n.data.day)
    return (
        f"{NOME[n.tipo]} nº {numero_formatado(n.numero)}, de {dia} de "
        f"{MESES[n.data.month - 1]} de {n.data.year}"
    )


def fonte(session: Session) -> dict:
    return {
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": projeto_fontes.atualizado_em(session, [FONTE]),
    }


def _projetos_das_normas(session: Session, ids: list[int]) -> dict[int, list[dict]]:
    """Projetos de origem de cada norma, com o link interno quando o projeto está no site."""
    if not ids:
        return {}
    linhas = session.execute(
        select(
            NormaProposicao.norma_id,
            NormaProposicao.casa,
            NormaProposicao.proposicao_id_externo,
            NormaProposicao.identificacao,
            Proposicao.id.is_not(None).label("no_site"),
        )
        .outerjoin(
            Proposicao,
            (Proposicao.casa == NormaProposicao.casa)
            & (Proposicao.id_externo == NormaProposicao.proposicao_id_externo),
        )
        .where(NormaProposicao.norma_id.in_(ids))
        .order_by(NormaProposicao.norma_id, NormaProposicao.casa, NormaProposicao.id)
    ).all()
    saida: dict[int, list[dict]] = defaultdict(list)
    for norma_id, casa, pid, ident, no_site in linhas:
        saida[norma_id].append(
            {
                "casa": casa,
                "id_externo": pid,
                "identificacao": ident,
                "link": f"/projeto/{casa}/{pid}" if no_site else None,
            }
        )
    return saida


def item(n: Norma, projetos: list[dict] | None = None) -> dict:
    return {
        "tipo": n.tipo,
        "numero": n.numero,
        "ano": n.ano,
        "nome": nome_curto(n),
        "nome_oficial": nome_oficial(n),
        "data": n.data,
        "data_publicacao": n.data_publicacao,
        "ementa": n.ementa,
        "url": n.url,
        "projetos": projetos or [],
    }


def por_ano(
    session: Session, q: str | None = None, ano: int | None = None, pagina: int = 1
) -> dict:
    """Filtro "Virou lei" de /projetos: contagem por ano da lei (do mais recente ao mais antigo)
    e, só do `ano` pedido, as normas da página (20 por página, da mais recente)."""
    condicoes = []
    termo = (q or "").strip()
    numero = _NUMERO.match(termo)
    if numero:
        condicoes.append(Norma.numero == int(numero[1].replace(".", "")))
        if numero[2]:
            condicoes.append(Norma.ano == int(numero[2]))
    elif termo:
        condicoes.append(
            sa.literal_column(texto_busca.sql_tsvector("norma.ementa")).op("@@")(
                func.plainto_tsquery(sa.literal_column("'portuguese'"), texto_busca.palavras(termo))
            )
        )
    contagens = session.execute(
        select(Norma.ano, Norma.tipo, func.count())
        .where(*condicoes)
        .group_by(Norma.ano, Norma.tipo)
    ).all()
    anos: dict[int, dict] = {}
    for a, tipo, n in contagens:
        linha = anos.setdefault(a, {"ano": a, "total": 0, "LEI": 0, "LCP": 0, "EMC": 0})
        linha["total"] += n
        linha[tipo] += n
    lista_anos = [
        {
            "ano": a["ano"],
            "total": a["total"],
            "leis": a["LEI"],
            "leis_complementares": a["LCP"],
            "emendas_constitucionais": a["EMC"],
        }
        for a in sorted(anos.values(), key=lambda x: -x["ano"])
    ]
    itens: list[dict] = []
    total_ano = 0
    if ano is not None and ano in anos:
        total_ano = anos[ano]["total"]
        normas = session.scalars(
            select(Norma)
            .where(Norma.ano == ano, *condicoes)
            .order_by(Norma.data.desc(), Norma.tipo, Norma.numero.desc())
            .limit(POR_PAGINA)
            .offset((max(pagina, 1) - 1) * POR_PAGINA)
        ).all()
        projetos = _projetos_das_normas(session, [n.id for n in normas])
        itens = [item(n, projetos.get(n.id)) for n in normas]
    return {
        "total": sum(a["total"] for a in lista_anos),
        "desde": min(anos) if anos else None,
        "anos": lista_anos,
        "ano": ano if ano in anos else None,
        "total_ano": total_ano,
        "pagina": max(pagina, 1),
        "por_pagina": POR_PAGINA,
        "itens": itens,
        **fonte(session),
    }


def da_proposicao(session: Session, casa: str, id_externo: str) -> dict | None:
    """A norma que o projeto virou (a mais recente, se houver mais de uma), com fonte e data."""
    norma = session.scalars(
        select(Norma)
        .join(NormaProposicao, NormaProposicao.norma_id == Norma.id)
        .where(NormaProposicao.casa == casa, NormaProposicao.proposicao_id_externo == id_externo)
        .order_by(Norma.data.desc())
        .limit(1)
    ).first()
    if norma is None:
        return None
    return {**item(norma), **fonte(session)}


def _autorias_com_norma():
    """(parlamentar_id, proposicao_id) de autorias cujo projeto virou norma."""
    return (
        select(Autoria.parlamentar_id, Autoria.proposicao_id, Autoria.primeiro_autor)
        .join(Proposicao, Proposicao.id == Autoria.proposicao_id)
        .where(
            select(NormaProposicao.id)
            .where(
                NormaProposicao.casa == Proposicao.casa,
                NormaProposicao.proposicao_id_externo == Proposicao.id_externo,
            )
            .exists()
        )
    )


def media_casa(session: Session, casa: str) -> Decimal:
    """Média de projetos (como autor ou coautor) que viraram lei por parlamentar em exercício da
    Casa, zeros incluídos."""
    com_norma = _autorias_com_norma().subquery()
    contagens = (
        select(func.count(com_norma.c.proposicao_id).label("n"))
        .select_from(Parlamentar)
        .outerjoin(com_norma, com_norma.c.parlamentar_id == Parlamentar.id)
        .where(Parlamentar.casa == casa, Parlamentar.em_exercicio.is_(True))
        .group_by(Parlamentar.id)
        .subquery()
    )
    return Decimal(session.scalar(select(func.coalesce(func.avg(contagens.c.n), 0)))).quantize(
        Decimal("0.1")
    )


def do_parlamentar(session: Session, parlamentar: Parlamentar) -> dict:
    """ "Viraram lei" do perfil: projetos da pessoa (autor ou coautor) que viraram norma, da lei
    mais recente para a mais antiga, com a média da Casa."""
    linhas = session.execute(
        select(Proposicao, Autoria.primeiro_autor, Norma)
        .join(Autoria, Autoria.proposicao_id == Proposicao.id)
        .join(
            NormaProposicao,
            (NormaProposicao.casa == Proposicao.casa)
            & (NormaProposicao.proposicao_id_externo == Proposicao.id_externo),
        )
        .join(Norma, Norma.id == NormaProposicao.norma_id)
        .where(Autoria.parlamentar_id == parlamentar.id)
        .order_by(Norma.data.desc(), Proposicao.id)
    ).all()
    vistos: set[int] = set()
    itens = []
    for proposicao, primeiro, norma in linhas:
        if proposicao.id in vistos:
            continue
        vistos.add(proposicao.id)
        itens.append(
            {
                "projeto": f"{proposicao.sigla_tipo} {proposicao.numero}/{proposicao.ano}",
                "projeto_link": f"/projeto/{proposicao.casa}/{proposicao.id_externo}",
                "primeiro_autor": primeiro,
                "norma": item(norma),
            }
        )
    return {
        "total": len(itens),
        "primeiro_autor": sum(1 for i in itens if i["primeiro_autor"]),
        "media_casa": media_casa(session, parlamentar.casa),
        "itens": itens,
        **fonte(session),
    }

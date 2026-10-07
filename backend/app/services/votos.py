"""Como cada parlamentar votou: alinhamento com o Governo e com o próprio partido,
lista de votos e convergência entre dois parlamentares.

Definições (registradas em docs/DECISOES.md):
- Voto efetivo: Sim, Não, Abstenção ou Obstrução. Ausência, "presente sem voto" e o
  voto de quem preside não entram nas comparações. Votações secretas também não.
- Alinhamento com o Governo: votações em que o Governo orientou Sim, Não ou Obstrução
  e o parlamentar deu voto efetivo; conta quantas vezes o voto foi igual à orientação.
  "Liberado" e orientação em branco ficam fora.
- Maioria do partido: o voto mais comum entre os OUTROS deputados do mesmo partido
  (no dia) que deram voto efetivo, desde que sejam pelo menos 2; empate fica fora.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Orientacao, Parlamentar, ProposicaoTema, Votacao, Voto

VOTO_EFETIVO = ("Sim", "Não", "Abstenção", "Obstrução")
ORIENTACAO_VALIDA = ("Sim", "Não", "Obstrução")
MINIMO_OUTROS_DO_PARTIDO = 2
POR_PAGINA = 20


@dataclass
class Placar:
    iguais: int = 0
    total: int = 0

    @property
    def percentual(self) -> float | None:
        return round(100 * self.iguais / self.total, 1) if self.total else None


def maioria_dos_outros(contagem: Counter, voto_proprio: str) -> str | None:
    """Voto mais comum do partido tirando o próprio parlamentar; None se não houver
    gente suficiente ou se houver empate."""
    outros = contagem.copy()
    outros[voto_proprio] -= 1
    outros = +outros  # remove zeros
    if sum(outros.values()) < MINIMO_OUTROS_DO_PARTIDO:
        return None
    (primeiro, n1), *resto = outros.most_common(2)
    if resto and resto[0][1] == n1:
        return None
    return primeiro


def _votos_do_ano(session: Session, casa: str, ano: int):
    return session.execute(
        select(Voto.votacao_id, Voto.parlamentar_id, Voto.partido, Voto.voto)
        .join(Votacao, Votacao.id == Voto.votacao_id)
        .where(
            Votacao.casa == casa,
            func.extract("year", Votacao.data) == ano,
            Votacao.secreta.is_(False),
            Voto.voto.in_(VOTO_EFETIVO),
        )
    ).all()


def _orientacoes_governo(session: Session, casa: str, ano: int) -> dict[int, str]:
    linhas = session.execute(
        select(Orientacao.votacao_id, Orientacao.orientacao)
        .join(Votacao, Votacao.id == Orientacao.votacao_id)
        .where(
            Votacao.casa == casa,
            func.extract("year", Votacao.data) == ano,
            Orientacao.bancada == "Governo",
            Orientacao.orientacao.in_(ORIENTACAO_VALIDA),
        )
    )
    return {votacao_id: orientacao for votacao_id, orientacao in linhas}


def alinhamentos(session: Session, casa: str, ano: int) -> dict[int, dict[str, Placar]]:
    """Placar de alinhamento (Governo e partido) de todos os parlamentares da casa no ano."""
    votos = _votos_do_ano(session, casa, ano)
    governo = _orientacoes_governo(session, casa, ano)
    por_partido: dict[tuple[int, str], Counter] = defaultdict(Counter)
    for votacao_id, _, partido, voto in votos:
        if partido:
            por_partido[(votacao_id, partido)][voto] += 1

    placares: dict[int, dict[str, Placar]] = defaultdict(
        lambda: {"governo": Placar(), "partido": Placar()}
    )
    for votacao_id, parlamentar_id, partido, voto in votos:
        p = placares[parlamentar_id]
        if votacao_id in governo:
            p["governo"].total += 1
            p["governo"].iguais += voto == governo[votacao_id]
        if partido:
            maioria = maioria_dos_outros(por_partido[(votacao_id, partido)], voto)
            if maioria is not None:
                p["partido"].total += 1
                p["partido"].iguais += voto == maioria
    return dict(placares)


def _temas_por_proposicao(session: Session, casa: str, ids: set[str]) -> dict[str, list[str]]:
    if not ids:
        return {}
    temas: dict[str, list[str]] = defaultdict(list)
    for id_externo, tema in session.execute(
        select(ProposicaoTema.proposicao_id_externo, ProposicaoTema.tema)
        .where(ProposicaoTema.casa == casa, ProposicaoTema.proposicao_id_externo.in_(ids))
        .order_by(ProposicaoTema.tema)
    ):
        temas[id_externo].append(tema)
    return dict(temas)


def lista_votos(
    session: Session, parlamentar: Parlamentar, ano: int, tema: str | None, pagina: int
) -> dict:
    """Votações nominais em que o parlamentar votou, com a orientação do Governo e a
    maioria do partido em cada uma. Mais recentes primeiro."""
    casa = parlamentar.casa
    filtro = [
        Voto.parlamentar_id == parlamentar.id,
        Votacao.casa == casa,
        func.extract("year", Votacao.data) == ano,
    ]
    if tema:
        filtro.append(
            Votacao.proposicao_id_externo.in_(
                select(ProposicaoTema.proposicao_id_externo).where(
                    ProposicaoTema.casa == casa, ProposicaoTema.tema == tema
                )
            )
        )
    base = select(Votacao, Voto.voto, Voto.partido).join(Voto, Voto.votacao_id == Votacao.id)
    total = session.scalar(select(func.count()).select_from(base.where(*filtro).subquery()))
    linhas = session.execute(
        base.where(*filtro)
        .order_by(Votacao.data.desc(), Votacao.id.desc())
        .limit(POR_PAGINA)
        .offset((pagina - 1) * POR_PAGINA)
    ).all()

    ids = [v.id for v, _, _ in linhas]
    governo = dict(
        session.execute(
            select(Orientacao.votacao_id, Orientacao.orientacao).where(
                Orientacao.votacao_id.in_(ids), Orientacao.bancada == "Governo"
            )
        ).all()
    )
    # Contagem por voto dos deputados do mesmo partido, em cada votação da página.
    partidos = {partido for _, _, partido in linhas if partido}
    contagens: dict[tuple[int, str], Counter] = defaultdict(Counter)
    for votacao_id, partido, voto, n in session.execute(
        select(Voto.votacao_id, Voto.partido, Voto.voto, func.count())
        .where(Voto.votacao_id.in_(ids), Voto.partido.in_(partidos), Voto.voto.in_(VOTO_EFETIVO))
        .group_by(Voto.votacao_id, Voto.partido, Voto.voto)
    ):
        contagens[(votacao_id, partido)][voto] = n
    temas = _temas_por_proposicao(
        session, casa, {v.proposicao_id_externo for v, _, _ in linhas if v.proposicao_id_externo}
    )

    itens = []
    for votacao, voto, partido in linhas:
        efetivo = voto in VOTO_EFETIVO
        maioria = (
            maioria_dos_outros(contagens[(votacao.id, partido)], voto)
            if efetivo and partido and not votacao.secreta
            else None
        )
        itens.append(
            {
                "data": votacao.data,
                "descricao": votacao.descricao,
                "proposicao": votacao.proposicao,
                "proposicao_ementa": votacao.proposicao_ementa,
                "temas": temas.get(votacao.proposicao_id_externo or "", []),
                "voto": voto,
                "orientacao_governo": governo.get(votacao.id),
                "maioria_partido": maioria,
                "partido": partido,
                "url": url_votacao(votacao),
            }
        )
    return {"total": total or 0, "pagina": pagina, "por_pagina": POR_PAGINA, "itens": itens}


def url_votacao(votacao: Votacao) -> str | None:
    """Página oficial da proposição votada (onde fica o histórico das votações)."""
    if not votacao.proposicao_id_externo:
        return None
    if votacao.casa == "camara":
        return (
            "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao="
            f"{votacao.proposicao_id_externo}"
        )
    return (
        "https://www25.senado.leg.br/web/atividade/materias/-/materia/"
        f"{votacao.proposicao_id_externo}"
    )


def temas_disponiveis(session: Session, parlamentar: Parlamentar, ano: int) -> list[str]:
    return list(
        session.scalars(
            select(ProposicaoTema.tema)
            .join(
                Votacao,
                and_(
                    Votacao.proposicao_id_externo == ProposicaoTema.proposicao_id_externo,
                    Votacao.casa == ProposicaoTema.casa,
                ),
            )
            .join(Voto, Voto.votacao_id == Votacao.id)
            .where(
                Voto.parlamentar_id == parlamentar.id,
                func.extract("year", Votacao.data) == ano,
            )
            .distinct()
            .order_by(ProposicaoTema.tema)
        )
    )


def convergencia(session: Session, a: Parlamentar, b: Parlamentar, ano: int) -> dict:
    """Em quantas votações (em que os dois deram voto efetivo) votaram igual, no total e
    por tema, e as divergências mais recentes."""
    va, vb = aliased(Voto), aliased(Voto)
    linhas = session.execute(
        select(Votacao, va.voto, vb.voto)
        .join(va, and_(va.votacao_id == Votacao.id, va.parlamentar_id == a.id))
        .join(vb, and_(vb.votacao_id == Votacao.id, vb.parlamentar_id == b.id))
        .where(
            func.extract("year", Votacao.data) == ano,
            Votacao.secreta.is_(False),
            va.voto.in_(VOTO_EFETIVO),
            vb.voto.in_(VOTO_EFETIVO),
        )
        .order_by(Votacao.data.desc(), Votacao.id.desc())
    ).all()
    temas = _temas_por_proposicao(
        session, a.casa, {v.proposicao_id_externo for v, _, _ in linhas if v.proposicao_id_externo}
    )

    total = Placar()
    por_tema: dict[str, Placar] = defaultdict(Placar)
    divergencias = []
    for votacao, voto_a, voto_b in linhas:
        igual = voto_a == voto_b
        total.total += 1
        total.iguais += igual
        for tema in temas.get(votacao.proposicao_id_externo or "", []):
            por_tema[tema].total += 1
            por_tema[tema].iguais += igual
        if not igual and len(divergencias) < 20:
            divergencias.append(
                {
                    "data": votacao.data,
                    "proposicao": votacao.proposicao,
                    "proposicao_ementa": votacao.proposicao_ementa,
                    "descricao": votacao.descricao,
                    "voto_a": voto_a,
                    "voto_b": voto_b,
                    "url": url_votacao(votacao),
                }
            )
    return {
        "votacoes_em_comum": total.total,
        "iguais": total.iguais,
        "percentual": total.percentual,
        "por_tema": sorted(
            (
                {"tema": t, "iguais": p.iguais, "total": p.total, "percentual": p.percentual}
                for t, p in por_tema.items()
            ),
            key=lambda x: -x["total"],
        ),
        "divergencias": divergencias,
    }

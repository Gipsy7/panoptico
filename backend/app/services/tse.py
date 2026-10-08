"""Dados do TSE: candidaturas, bens declarados e campanha.

Servem dois públicos: o perfil dos parlamentares federais (todas as candidaturas ligadas
pelo CPF) e os eleitos para câmaras municipais e assembleias, que só existem no TSE.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BemDeclarado,
    CampanhaResumo,
    Candidatura,
    FonteIngestao,
    Parlamentar,
    RedeSocial,
)

FONTE_NOME = "Tribunal Superior Eleitoral (dados abertos)"
FONTE_URL = "https://dadosabertos.tse.jus.br/"
URL_CANDIDATOS = "https://dadosabertos.tse.jus.br/dataset/candidatos-{ano}"
URL_CONTAS = "https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-{ano}"

# Cargos que dão o mandato atual em cada Casa (suplentes assumem no lugar do titular).
CARGOS_DO_MANDATO = {
    "camara": {"DEPUTADO FEDERAL"},
    "senado": {"SENADOR", "1º SUPLENTE", "2º SUPLENTE"},
}
CARGOS_ESTADUAIS = ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")
CARGOS_EXECUTIVO = (
    "PRESIDENTE",
    "VICE-PRESIDENTE",
    "GOVERNADOR",
    "VICE-GOVERNADOR",
    "PREFEITO",
    "VICE-PREFEITO",
)
CARGOS_COM_PERFIL = ("VEREADOR", *CARGOS_ESTADUAIS, *CARGOS_EXECUTIVO)
ITENS_DE_BENS = 30
SITUACOES = {
    "ELEITO POR QP": "Eleito pelo quociente partidário",
    "ELEITO POR MÉDIA": "Eleito pela média (sobra de vagas)",
}


def _situacao(texto: str | None) -> str | None:
    if not texto:
        return None
    return SITUACOES.get(texto, texto.capitalize())


def _candidatura(c: Candidatura) -> dict:
    return {
        "ano": c.ano_eleicao,
        "cargo": c.cargo.capitalize(),
        "unidade": c.unidade,
        "partido": c.partido,
        "numero": c.numero,
        "situacao": _situacao(c.situacao_turno),
    }


def _total_bens(session: Session, candidatura_id: int) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(BemDeclarado.valor), 0)).where(
            BemDeclarado.candidatura_id == candidatura_id
        )
    )


def _tem_bens(session: Session, candidatura_id: int) -> bool:
    return bool(
        session.scalar(select(func.count()).where(BemDeclarado.candidatura_id == candidatura_id))
    )


def _bens(session: Session, atual: Candidatura, anterior: Candidatura | None) -> dict:
    itens = session.scalars(
        select(BemDeclarado)
        .where(BemDeclarado.candidatura_id == atual.id)
        .order_by(BemDeclarado.valor.desc())
    ).all()
    return {
        "candidatura": _candidatura(atual),
        "total": _total_bens(session, atual.id),
        "quantidade": len(itens),
        "itens": [
            {"tipo": b.tipo, "descricao": b.descricao, "valor": b.valor}
            for b in itens[:ITENS_DE_BENS]
        ],
        "anterior": (
            {"candidatura": _candidatura(anterior), "total": _total_bens(session, anterior.id)}
            if anterior
            else None
        ),
        "fonte_url": URL_CANDIDATOS.format(ano=atual.ano_eleicao),
    }


def _campanha(session: Session, c: Candidatura) -> dict | None:
    contas = session.get(CampanhaResumo, c.id)
    if contas is None:
        return None
    return {
        "candidatura": _candidatura(c),
        "receitas_total": contas.receitas_total,
        "receitas_por_origem": [
            {"nome": k, "valor": v} for k, v in contas.receitas_por_origem.items()
        ],
        "despesas_total": contas.despesas_total,
        "despesas_por_tipo": [{"nome": k, "valor": v} for k, v in contas.despesas_por_tipo.items()],
        "numero_doadores": contas.numero_doadores,
        "fonte_url": URL_CONTAS.format(ano=c.ano_eleicao),
    }


def _atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(["tse_candidaturas", "tse_bens", "tse_campanha"]),
            FonteIngestao.status == "ok",
        )
    )


def resumo(session: Session, parlamentar: Parlamentar) -> dict:
    """Perfil do parlamentar federal: bens da candidatura mais recente (comparados com a
    anterior) e a campanha que deu o mandato atual."""
    candidaturas = session.scalars(
        select(Candidatura)
        .where(Candidatura.parlamentar_id == parlamentar.id)
        .order_by(Candidatura.ano_eleicao.desc())
    ).all()
    com_bens = [c for c in candidaturas if _tem_bens(session, c.id)]
    do_mandato = next(
        (c for c in candidaturas if c.cargo in CARGOS_DO_MANDATO[parlamentar.casa]), None
    )
    return {
        "candidaturas": [_candidatura(c) for c in candidaturas],
        "bens": _bens(session, com_bens[0], com_bens[1] if len(com_bens) > 1 else None)
        if com_bens
        else None,
        "campanha": _campanha(session, do_mandato) if do_mandato else None,
        "pessoais": _pessoais(session, list(candidaturas)),
        "votos": {"ano": do_mandato.ano_eleicao, "total": do_mandato.votos}
        if do_mandato and do_mandato.votos is not None
        else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }


def _eleito(c: Candidatura, depois: Candidatura | None = None) -> dict:
    return {
        "id": c.id,
        "nome_urna": c.nome_urna,
        "partido": c.partido,
        "numero": c.numero,
        "situacao": _situacao(c.situacao_turno),
        "uf": c.uf,
        "parlamentar_id": c.parlamentar_id,
        "votos": c.votos,
        # Eleito depois para outro cargo (ligado pelo título de eleitor), ex.: deputado
        # estadual de 2022 eleito prefeito em 2024.
        "depois": {
            "id": depois.id,
            "cargo": depois.cargo.capitalize(),
            "unidade": depois.unidade,
            "ano": depois.ano_eleicao,
        }
        if depois
        else None,
    }


def _idade(nascimento: date | None, hoje: date | None = None) -> int | None:
    if nascimento is None:
        return None
    hoje = hoje or date.today()
    return (
        hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    )


def _texto(valor: str | None) -> str | None:
    return valor.capitalize() if valor else None


def _pessoais(session: Session, candidaturas: list[Candidatura]) -> dict | None:
    """Dados pessoais declarados ao TSE na candidatura mais recente, e as redes informadas
    em qualquer uma delas."""
    if not candidaturas:
        return None
    c = candidaturas[0]
    redes = session.scalars(
        select(RedeSocial.url)
        .where(RedeSocial.candidatura_id.in_([x.id for x in candidaturas]))
        .distinct()
    ).all()
    return {
        "ano": c.ano_eleicao,
        "idade": _idade(c.data_nascimento),
        "genero": _texto(c.genero),
        "cor_raca": _texto(c.cor_raca),
        "grau_instrucao": _texto(c.grau_instrucao),
        "ocupacao": _texto(c.ocupacao),
        "estado_civil": _texto(c.estado_civil),
        "redes": sorted(redes),
    }


def _eleitos_depois(session: Session, candidaturas: list[Candidatura]) -> dict[int, Candidatura]:
    """Para cada candidatura, a primeira eleição vencida depois dela pela mesma pessoa."""
    por_titulo = {c.titulo: c for c in candidaturas if c.titulo}
    if not por_titulo:
        return {}
    depois = session.scalars(
        select(Candidatura)
        .where(
            Candidatura.titulo.in_(list(por_titulo)),
            Candidatura.situacao_turno.like("ELEITO%"),
        )
        .order_by(Candidatura.ano_eleicao)
    ).all()
    resultado: dict[int, Candidatura] = {}
    for d in depois:
        origem = por_titulo[d.titulo]
        if d.ano_eleicao > origem.ano_eleicao and origem.id not in resultado:
            resultado[origem.id] = d
    return resultado


def _lista(session: Session, *condicoes) -> tuple[int | None, list[dict]]:
    """Eleitos da eleição mais recente que atende às condições. Guardamos eleições
    anteriores (ex.: deputados estaduais de 2018), mas a lista mostra só o mandato atual."""
    eleitos = Candidatura.situacao_turno.like("ELEITO%")
    ano = session.scalar(select(func.max(Candidatura.ano_eleicao)).where(*condicoes, eleitos))
    if ano is None:
        return None, []
    lista = session.scalars(
        select(Candidatura)
        .where(*condicoes, eleitos, Candidatura.ano_eleicao == ano)
        .order_by(Candidatura.nome_urna)
    ).all()
    depois = _eleitos_depois(session, list(lista))
    return ano, [_eleito(c, depois.get(c.id)) for c in lista]


def _resposta_lista(session: Session, ano: int | None, itens: list[dict], ano_padrao: int) -> dict:
    return {
        "ano_eleicao": ano,
        "itens": itens,
        "fonte_nome": FONTE_NOME,
        "fonte_url": URL_CANDIDATOS.format(ano=ano or ano_padrao),
        "atualizado_em": _atualizado_em(session),
    }


def vereadores(session: Session, municipio_ibge: str) -> dict:
    ano, itens = _lista(
        session, Candidatura.cargo == "VEREADOR", Candidatura.municipio_ibge == municipio_ibge
    )
    return _resposta_lista(session, ano, itens, 2024)


def deputados_estaduais(session: Session, uf: str) -> dict:
    ano, itens = _lista(
        session, Candidatura.cargo.in_(CARGOS_ESTADUAIS), Candidatura.uf == uf.upper()
    )
    return _resposta_lista(session, ano, itens, 2022)


def eleito(session: Session, candidatura: Candidatura) -> dict:
    """Perfil de um eleito que só existe no TSE (vereador, deputado estadual)."""
    return {
        **_eleito(candidatura, _eleitos_depois(session, [candidatura]).get(candidatura.id)),
        "pessoais": _pessoais(session, [candidatura]),
        "cargo": candidatura.cargo.capitalize(),
        "unidade": candidatura.unidade,
        "municipio_ibge": candidatura.municipio_ibge,
        "ano_eleicao": candidatura.ano_eleicao,
        "bens": _bens(session, candidatura, None) if _tem_bens(session, candidatura.id) else None,
        "campanha": _campanha(session, candidatura),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }


def _chapa(session: Session, titular: Candidatura | None) -> dict | None:
    if titular is None:
        return None
    vice = session.scalars(
        select(Candidatura).where(Candidatura.chapa_titular_id == titular.id)
    ).first()
    return {
        "cargo": titular.cargo.capitalize(),
        "unidade": titular.unidade,
        "ano_eleicao": titular.ano_eleicao,
        "titular": _eleito(titular),
        "vice": _eleito(vice) if vice else None,
    }


def _eleito_para(session: Session, *condicoes) -> Candidatura | None:
    return session.scalars(
        select(Candidatura)
        .where(*condicoes, Candidatura.situacao_turno == "ELEITO")
        .order_by(Candidatura.ano_eleicao.desc())
    ).first()


def executivo(session: Session, uf: str, municipio_ibge: str | None) -> dict:
    """Presidente, governador do estado e prefeito da cidade, cada um com o vice."""
    return {
        "presidente": _chapa(session, _eleito_para(session, Candidatura.cargo == "PRESIDENTE")),
        "governador": _chapa(
            session,
            _eleito_para(session, Candidatura.cargo == "GOVERNADOR", Candidatura.uf == uf.upper()),
        ),
        "prefeito": _chapa(
            session,
            _eleito_para(
                session,
                Candidatura.cargo == "PREFEITO",
                Candidatura.municipio_ibge == municipio_ibge,
            ),
        )
        if municipio_ibge
        else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }
